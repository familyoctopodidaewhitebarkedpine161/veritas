"""Overstory-based runner — true worktree isolation via ov sling.

Spawns each verification agent in a separate git worktree using Overstory.
Agents communicate via SQLite mail. This provides the strongest isolation
primitive: filesystem-level separation with no shared state.

This is the research contribution — proving that isolation beats shared context.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

from veritas.agents.synthesiser import Synthesiser
from veritas.core.config import Config
from veritas.core.result import AgentFinding, VerificationResult
from veritas.orchestration.challenge import run_challenge_round
from veritas.agents.adversary import Adversary
from veritas.providers.base import LLMProvider

# Path to ov CLI — set via env or default
OV_CLI = os.environ.get("OV_CLI", "bun /tmp/overstory-cli/src/index.ts")
PROJECT_ROOT = os.environ.get("VERITAS_PROJECT_ROOT", str(Path(__file__).parent.parent.parent))


def _run_ov(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    """Run an ov CLI command."""
    cmd = OV_CLI.split() + args
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=PROJECT_ROOT,
    )


def _create_spec(claim: str, context: str | None, domain: str | None, references: list[str], agent_type: str) -> Path:
    """Create a task spec file for an agent."""
    spec = {
        "claim": claim,
        "context": context,
        "domain": domain,
        "references": references,
        "agent_type": agent_type,
        "output_format": "json",
    }
    spec_dir = Path(PROJECT_ROOT) / ".overstory" / "specs"
    spec_dir.mkdir(exist_ok=True)
    spec_path = spec_dir / f"veritas-{agent_type}-{int(time.time())}.json"
    spec_path.write_text(json.dumps(spec, indent=2))
    return spec_path


class OverstoryRunner:
    """Orchestrates verification using Overstory git worktrees.

    Each agent is spawned via `ov sling` in its own worktree.
    Findings are collected via `ov mail`.
    The synthesiser runs in the main process (it only reads, never generates).
    """

    AGENT_MAP = {
        "logic": {
            "capability": "builder",
            "files": "veritas/agents/logic.py",
            "def": "veritas-logic",
        },
        "source": {
            "capability": "builder",
            "files": "veritas/agents/source.py",
            "def": "veritas-source",
        },
        "adversary": {
            "capability": "builder",
            "files": "veritas/agents/adversary.py",
            "def": "veritas-adversary",
        },
        "calibration": {
            "capability": "builder",
            "files": "veritas/agents/calibration.py",
            "def": "veritas-calibration",
        },
    }

    def __init__(self, llm_provider: LLMProvider, config: Config):
        self.config = config
        self.llm_provider = llm_provider
        self.synthesiser = Synthesiser(provider=llm_provider)
        self.adversary = Adversary(provider=llm_provider)

    def _spawn_agent(self, agent_type: str, spec_path: Path, task_id: str) -> str:
        """Spawn an agent in a worktree via ov sling."""
        agent_config = self.AGENT_MAP[agent_type]
        name = f"veritas-{agent_type}-{int(time.time())}"

        result = _run_ov([
            "sling", task_id,
            "--capability", agent_config["capability"],
            "--name", name,
            "--spec", str(spec_path),
            "--files", agent_config["files"],
            "--skip-task-check",
            "--skip-scout-check" if "skip-scout-check" in "" else "--no-scout-check",
        ])

        if result.returncode != 0:
            raise RuntimeError(f"ov sling failed for {agent_type}: {result.stderr}")

        return name

    def _check_mail(self, agent_name: str, timeout: int = 60) -> list[dict]:
        """Poll for mail from an agent."""
        start = time.time()
        while time.time() - start < timeout:
            result = _run_ov(["mail", "check", "--json"], timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                try:
                    messages = json.loads(result.stdout)
                    agent_msgs = [m for m in messages if m.get("from") == agent_name]
                    if agent_msgs:
                        return agent_msgs
                except json.JSONDecodeError:
                    pass
            time.sleep(2)
        return []

    def _parse_agent_output(self, agent_type: str, output_path: Path) -> AgentFinding:
        """Read the agent's output JSON from its worktree."""
        try:
            data = json.loads(output_path.read_text())
            return AgentFinding(
                agent=f"{agent_type}_verifier" if agent_type != "adversary" else agent_type,
                finding=data.get("finding", "parse_error"),
                confidence=float(data.get("confidence", 0.0)),
                details=data.get("details", []),
                sources=data.get("sources", []),
                reasoning=data.get("reasoning", ""),
            )
        except (json.JSONDecodeError, FileNotFoundError) as e:
            return AgentFinding(
                agent=agent_type,
                finding="agent_error",
                confidence=0.0,
                details=[{"type": "error", "description": str(e)}],
            )

    async def run(
        self,
        claim: str,
        context: str | None,
        domain: str | None,
        references: list[str],
    ) -> VerificationResult:
        """Run verification with true worktree isolation.

        1. Create spec files for each agent
        2. Spawn 4 agents in parallel worktrees via ov sling
        3. Wait for all agents to complete
        4. Collect findings
        5. Synthesise verdict
        6. Optional challenge round
        """
        start = time.monotonic()

        # Create specs for each agent
        specs = {}
        for agent_type in self.AGENT_MAP:
            task_id = f"veritas-{agent_type}-{int(time.time())}"
            spec_path = _create_spec(claim, context, domain, references, agent_type)
            specs[agent_type] = {"spec_path": spec_path, "task_id": task_id}

        # Spawn all agents in parallel worktrees
        agent_names = {}
        for agent_type, spec_info in specs.items():
            try:
                name = self._spawn_agent(
                    agent_type, spec_info["spec_path"], spec_info["task_id"]
                )
                agent_names[agent_type] = name
            except RuntimeError as e:
                # If spawning fails, fall back to in-process for this agent
                agent_names[agent_type] = None

        # Wait for agents and collect findings
        # For now, use a polling approach on worktree output files
        findings: list[AgentFinding] = []
        worktree_base = Path(PROJECT_ROOT) / ".overstory" / "worktrees"

        for agent_type, name in agent_names.items():
            if name is None:
                # Fallback: agent failed to spawn, create a placeholder
                findings.append(AgentFinding(
                    agent=agent_type,
                    finding="agent_unavailable",
                    confidence=0.0,
                    details=[{"type": "error", "description": "Failed to spawn in worktree"}],
                ))
                continue

            # Look for output in the agent's worktree
            output_path = worktree_base / name / "veritas-output.json"
            deadline = time.time() + self.config.timeout_seconds
            while time.time() < deadline:
                if output_path.exists():
                    finding = self._parse_agent_output(agent_type, output_path)
                    findings.append(finding)
                    break
                await asyncio.sleep(2)
            else:
                findings.append(AgentFinding(
                    agent=agent_type,
                    finding="timeout",
                    confidence=0.0,
                    details=[{"type": "error", "description": f"Agent {name} timed out"}],
                ))

        # Synthesise (runs in main process — no isolation needed)
        result = await self.synthesiser.synthesise(claim=claim, findings=findings)

        # Optional challenge round
        if result.contested and self.config.challenge_round:
            result = await run_challenge_round(
                claim=claim,
                initial_result=result,
                adversary=self.adversary,
                synthesiser=self.synthesiser,
            )

        duration_ms = int((time.monotonic() - start) * 1000)
        result.metadata["total_duration_ms"] = duration_ms
        result.metadata["model"] = self.config.model
        result.metadata["mode"] = "overstory_worktree"
        result.metadata["agents_spawned"] = list(agent_names.keys())

        return result
