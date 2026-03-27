# Veritas Design Spec

**Date:** 2026-03-27
**Status:** Approved
**Research:** [docs/research/landscape-analysis.md](../../research/landscape-analysis.md)

---

## Overview

Veritas is a standalone open-source Python library for adversarial parallel verification of AI outputs. No ground truth required. Model-agnostic interface. pip-installable.

The core innovation is **isolation-divergent verification**: agents run in separate git worktrees with zero shared context, preventing the conformity bias documented in shared-context debate systems (Science Advances 2025, Cross-Context Verification 2026). Findings merge only at synthesis.

---

## Core API

```python
from veritas import verify

# Simple
result = verify("The first iPhone was released in 2006")

# Full options
result = verify(
    claim="React uses a virtual DOM for performance",
    context="From a blog post about web frameworks...",
    domain="technical",
    references=["path/to/doc.pdf"],
    model="claude-sonnet-4-6",
)
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `claim` | `str` | Yes | The claim to verify |
| `context` | `str` | No | Surrounding text or source context |
| `domain` | `str` | No | Domain hint: `technical`, `scientific`, `medical`, `legal`, `general` |
| `references` | `list[str]` | No | Paths to reference documents for grounding |
| `model` | `str` | No | LLM model to use (default: `claude-sonnet-4-6`) |

### Result Object — Layered Access

```python
# Print — human summary
print(result)
# REFUTED (0.91) — The first iPhone was released June 2007, not 2006.

# Properties
result.verdict          # Verdict.REFUTED
result.confidence       # 0.91
result.summary          # "The first iPhone was released June 2007, not 2006."
result.failure_modes    # [FailureMode(type="factual_error", detail="...", agent="source_verifier")]
result.evidence         # [AgentFinding(...), ...]
result.contested        # False
result.challenge_round  # None (or ChallengeResult if triggered)
result.metadata         # {"duration_ms": 4200, "agents_used": 5, "model": "claude-sonnet-4-6"}

# Serialization
result.to_dict()        # Full JSON dict
result.report()         # Human-readable markdown report
```

---

## Verdicts

| Verdict | Meaning | When |
|---------|---------|------|
| `VERIFIED` | Evidence supports the claim | All agents agree, evidence aligns |
| `PARTIAL` | Some parts verified, some not | Compound claims with mixed support |
| `UNCERTAIN` | Insufficient evidence either way | Cannot confirm or deny |
| `DISPUTED` | Agents disagree, unresolved | Conflicting findings after challenge round |
| `REFUTED` | Evidence contradicts the claim | Active contradiction found |

---

## Failure Mode Taxonomy

| Type | Description | Example |
|------|-------------|---------|
| `factual_error` | Wrong fact | "Released in 2006" when it was 2007 |
| `logical_inconsistency` | Self-contradiction | Premises contradict conclusion |
| `unsupported_inference` | Claim exceeds evidence | "X causes Y" with only correlation data |
| `temporal_error` | Outdated information | Using pre-2024 data for a 2026 claim |
| `scope_error` | Too broad or too narrow | "All X do Y" when only some do |
| `source_conflict` | Sources disagree | Two credible sources give different answers |

---

## Agent Architecture

### Hybrid Isolation Topology

**Phase 1 — Parallel, Fully Isolated**

All 4 verification agents run simultaneously in separate Overstory git worktrees. Zero shared context. Communication only via structured SQLite mail to the Synthesiser.

| Agent | Role | Isolation | Output |
|-------|------|-----------|--------|
| **Logic Verifier** | Internal consistency, contradictions, logical fallacies | Full (own worktree) | `LogicFinding` |
| **Source Verifier** | Factual cross-reference via web search + references | Full (own worktree) | `SourceFinding` |
| **Adversary** | Construct counterexamples, edge cases, attempts to disprove | Full (own worktree) | `AdversaryFinding` |
| **Calibration Agent** | Confidence vs evidence alignment audit | Full (own worktree) | `CalibrationFinding` |

**Synthesiser**

Receives all 4 findings via SQLite mail. Produces:
- Verdict (one of 5)
- Confidence score (0.0-1.0)
- Evidence chain (all agent findings, structured)
- Failure modes (typed, from taxonomy)
- Summary (one-sentence human-readable)

**Optional Challenge Round**

If the Synthesiser detects conflicting findings between agents:
1. Identifies the contested points
2. Sends contested points to the Adversary for targeted re-examination
3. Adversary produces a `ChallengeResult`
4. Synthesiser incorporates challenge findings into final verdict

If no conflicts, the fast path returns immediately.

### Agent Definitions (Overstory)

Each agent is defined as an Overstory agent spec in `.overstory/agent-defs/`:

- `veritas-logic.md` — Logic Verifier
- `veritas-source.md` — Source Verifier
- `veritas-adversary.md` — Adversary
- `veritas-calibration.md` — Calibration Agent
- `veritas-synthesiser.md` — Synthesiser

Each agent writes its structured finding as JSON to a known output path in its worktree. The orchestrator collects findings via SQLite mail.

### Agent Input/Output Schema

Each agent receives:
```json
{
  "claim": "string",
  "context": "string | null",
  "domain": "string | null",
  "references": ["string"]
}
```

Each agent outputs a typed finding:
```json
{
  "agent": "logic_verifier",
  "finding": "inconsistency | consistent | insufficient_info",
  "confidence": 0.85,
  "details": [
    {
      "type": "logical_inconsistency",
      "description": "Premise A contradicts conclusion B",
      "evidence": "..."
    }
  ]
}
```

---

## CLI Interface

### Commands

```bash
# Inline verification
veritas check "The Great Wall is visible from space"

# With options
veritas check "..." --verbose --json --domain medical --ref doc.pdf

# Pipe from stdin
cat llm_output.txt | veritas check --stdin

# Interactive shell
veritas shell

# Benchmark against standard datasets
veritas benchmark --dataset truthfulqa --output results.json
```

### CLI Flags

| Flag | Description |
|------|-------------|
| `--verbose` | Show full evidence chain |
| `--json` | Output as JSON |
| `--domain` | Domain hint |
| `--ref` | Reference document path (repeatable) |
| `--model` | Override LLM model |
| `--no-search` | Disable web search (offline mode) |
| `--stdin` | Read claim from stdin |

### Interactive Shell

```
$ veritas shell
Veritas v0.1.0 — Type a claim to verify. /help for commands.

veritas> The speed of light is 300,000 km/s
PARTIAL (0.78) — Approximately correct. Exact value is 299,792.458 km/s.

veritas> /verbose
Verbose mode on.

veritas> /quit
```

---

## Data Models (Pydantic)

```python
class Verdict(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIAL = "PARTIAL"
    UNCERTAIN = "UNCERTAIN"
    DISPUTED = "DISPUTED"
    REFUTED = "REFUTED"

class FailureModeType(str, Enum):
    FACTUAL_ERROR = "factual_error"
    LOGICAL_INCONSISTENCY = "logical_inconsistency"
    UNSUPPORTED_INFERENCE = "unsupported_inference"
    TEMPORAL_ERROR = "temporal_error"
    SCOPE_ERROR = "scope_error"
    SOURCE_CONFLICT = "source_conflict"

class FailureMode(BaseModel):
    type: FailureModeType
    detail: str
    agent: str

class AgentFinding(BaseModel):
    agent: str
    finding: str
    confidence: float
    details: list[dict]
    sources: list[str] = []
    reasoning: str = ""

class ChallengeResult(BaseModel):
    contested_points: list[str]
    adversary_finding: AgentFinding
    resolution: str

class VerificationResult(BaseModel):
    verdict: Verdict
    confidence: float
    summary: str
    failure_modes: list[FailureMode]
    evidence: list[AgentFinding]
    contested: bool
    challenge_round: ChallengeResult | None
    metadata: dict

    def report(self) -> str: ...
    def to_dict(self) -> dict: ...
    def __str__(self) -> str: ...
```

---

## LLM Provider Interface

Claude-first in v1. Pluggable interface for future providers.

```python
class LLMProvider(Protocol):
    async def generate(self, prompt: str, system: str = "") -> str: ...

class ClaudeProvider(LLMProvider):
    def __init__(self, model: str = "claude-sonnet-4-6", api_key: str | None = None): ...
    async def generate(self, prompt: str, system: str = "") -> str: ...
```

Future providers implement the same `LLMProvider` protocol. No changes needed to agent or verification code.

---

## Source Verification (Web Search)

v1 ships with web search via Brave Search API or Tavily. User-provided references also accepted.

```python
class SearchProvider(Protocol):
    async def search(self, query: str, num_results: int = 5) -> list[SearchResult]: ...

class BraveSearchProvider(SearchProvider): ...
class TavilySearchProvider(SearchProvider): ...
```

The Source Verifier agent:
1. Decomposes the claim into atomic checkable facts
2. Generates search queries for each fact
3. Retrieves results from search provider
4. Cross-references against user-provided references (if any)
5. Produces a `SourceFinding` with evidence chain

---

## Project Structure

```
veritas/
  __init__.py          # Public API: verify(), Verdict, VerificationResult
  core/
    verify.py          # Main verify() function, orchestration entry point
    result.py          # VerificationResult, Verdict, FailureMode models
    config.py          # Configuration and defaults
  agents/
    base.py            # Base agent interface
    logic.py           # Logic Verifier agent
    source.py          # Source Verifier agent
    adversary.py       # Adversary agent
    calibration.py     # Calibration Agent
    synthesiser.py     # Synthesiser agent
  orchestration/
    runner.py          # Overstory integration — spawns agents in worktrees
    messaging.py       # SQLite mail abstraction
    challenge.py       # Challenge round logic
  providers/
    base.py            # LLMProvider protocol
    claude.py          # Claude/Anthropic implementation
    search.py          # SearchProvider protocol + implementations
  cli/
    main.py            # CLI entry point (click/typer)
    shell.py           # Interactive REPL
  benchmarks/
    runner.py          # Benchmark harness
    datasets.py        # TruthfulQA, LongFact, WikiBio loaders
    metrics.py         # Accuracy, calibration error (ECE), F1
tests/
  test_verify.py
  test_agents/
  test_cli.py
  test_benchmarks.py
.overstory/
  agent-defs/
    veritas-logic.md
    veritas-source.md
    veritas-adversary.md
    veritas-calibration.md
    veritas-synthesiser.md
pyproject.toml
```

---

## Overstory Integration

### How Verification Runs

1. `verify()` called with claim + options
2. `runner.py` creates Overstory task specs for each agent
3. Overstory spawns 4 agents in parallel git worktrees via `ov sling`
4. Each agent receives the claim + context via SQLite mail
5. Each agent writes its finding JSON to its worktree
6. Findings collected via `ov mail check`
7. Synthesiser runs in the main process (no worktree needed — it only reads findings, never generates claims)
8. If conflicts detected, challenge round triggers Adversary re-run
9. Final `VerificationResult` returned

### Why Overstory, Not Just asyncio

- **True filesystem isolation** via git worktrees — agents can't accidentally share state
- **Process isolation** via tmux — one agent crashing doesn't take down others
- **Structured messaging** via SQLite mail — auditable, typed, durable
- **Built-in merge/conflict resolution** for challenge rounds
- The isolation property is the entire research contribution. asyncio with shared memory defeats the purpose.

---

## Benchmark Harness

```bash
veritas benchmark --dataset truthfulqa --output results.json
veritas benchmark --dataset longfact --model claude-sonnet-4-6
veritas benchmark --compare isolation-vs-debate --dataset truthfulqa
```

### Datasets
- **TruthfulQA** — 817 questions testing truthfulness vs common misconceptions
- **LongFact** — Google DeepMind's long-form factuality benchmark (38 topics)
- **WikiBio** — SelfCheckGPT's biography factuality dataset

### Metrics
- **Accuracy** — correct verdict rate
- **ECE** (Expected Calibration Error) — confidence alignment
- **F1** — precision/recall of failure mode detection
- **Isolation vs Debate** — comparative mode: same agents with shared context vs isolated

### The Paper Experiment
The `--compare isolation-vs-debate` flag runs the same verification twice:
1. Isolated (Veritas default) — agents in separate worktrees
2. Shared context (debate mode) — agents see each other's output

This directly tests the core thesis and produces publishable results.

---

## Configuration

```python
# veritas.config
from veritas import Config

config = Config(
    model="claude-sonnet-4-6",
    search_provider="brave",
    search_api_key="...",
    anthropic_api_key="...",
    challenge_round=True,      # Enable/disable challenge round
    max_search_results=5,
    timeout_seconds=30,
    verbose=False,
)

result = verify("...", config=config)
```

Environment variables:
- `ANTHROPIC_API_KEY` — Claude API key
- `BRAVE_API_KEY` or `TAVILY_API_KEY` — Search API key
- `VERITAS_MODEL` — Default model override
- `VERITAS_SEARCH_PROVIDER` — Default search provider

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Agent times out | Synthesiser proceeds with available findings, notes missing agent |
| Search API fails | Source Verifier reports `insufficient_info`, other agents unaffected |
| All agents fail | Returns `UNCERTAIN` with confidence 0.0 and error metadata |
| API key missing | Raises `VeritasConfigError` with clear message |
| Invalid claim (empty) | Raises `ValueError` |

---

## Non-Goals (v1)

- Multi-modal verification (images, audio, video)
- Real-time streaming verdicts
- Fine-tuned verification models
- Multi-language support
- Custom agent definitions by end users
- Provider support beyond Claude
