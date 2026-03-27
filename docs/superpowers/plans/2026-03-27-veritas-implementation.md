# Veritas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Veritas — a pip-installable Python library for adversarial parallel verification of AI outputs using isolation-divergent multi-agent architecture powered by Overstory.

**Architecture:** Bottom-up build. Data models and config first (pure Python, no deps). Then provider interfaces and Claude implementation. Then individual agent modules. Then Overstory orchestration layer. Then CLI. Then benchmarks. Each layer only depends on layers below it.

**Tech Stack:** Python 3.10+, Pydantic v2, Anthropic SDK, Typer (CLI), httpx (search), pytest, Overstory (orchestration)

**Spec:** `docs/superpowers/specs/2026-03-27-veritas-design.md`

---

## File Map

```
veritas/
  __init__.py              # Public API exports
  core/
    __init__.py
    result.py              # Verdict, FailureModeType, FailureMode, AgentFinding, ChallengeResult, VerificationResult
    config.py              # Config, VeritasConfigError, env var loading
  providers/
    __init__.py
    base.py                # LLMProvider, SearchProvider, SearchResult protocols
    claude.py              # ClaudeProvider implementation
    search.py              # BraveSearchProvider, TavilySearchProvider
  agents/
    __init__.py
    base.py                # BaseAgent abstract class
    logic.py               # LogicVerifier
    source.py              # SourceVerifier
    adversary.py           # Adversary
    calibration.py         # CalibrationAgent
    synthesiser.py         # Synthesiser
  orchestration/
    __init__.py
    runner.py              # OverstoryRunner — spawns agents in worktrees
    messaging.py           # SQLite mail abstraction for agent communication
    challenge.py           # Challenge round logic
  cli/
    __init__.py
    main.py                # Typer app: check, shell, benchmark commands
    shell.py               # Interactive REPL
  benchmarks/
    __init__.py
    runner.py              # BenchmarkRunner
    datasets.py            # Dataset loaders (TruthfulQA, LongFact, WikiBio)
    metrics.py             # Accuracy, ECE, F1
tests/
  __init__.py
  conftest.py              # Shared fixtures
  test_result.py           # Data model tests
  test_config.py           # Config tests
  test_providers.py        # Provider tests
  test_agents/
    __init__.py
    test_logic.py
    test_source.py
    test_adversary.py
    test_calibration.py
    test_synthesiser.py
  test_orchestration.py    # Runner + messaging tests
  test_cli.py              # CLI tests
  test_benchmarks.py       # Benchmark tests
.overstory/
  agent-defs/
    veritas-logic.md       # Logic Verifier agent def
    veritas-source.md      # Source Verifier agent def
    veritas-adversary.md   # Adversary agent def
    veritas-calibration.md # Calibration Agent def
    veritas-synthesiser.md # Synthesiser agent def
pyproject.toml             # Package config, deps, entry points
```

---

### Task 1: Project Scaffold and pyproject.toml

**Files:**
- Create: `pyproject.toml`
- Create: `veritas/__init__.py`
- Create: `veritas/core/__init__.py`
- Create: `veritas/providers/__init__.py`
- Create: `veritas/agents/__init__.py`
- Create: `veritas/orchestration/__init__.py`
- Create: `veritas/cli/__init__.py`
- Create: `veritas/benchmarks/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "veritas-verify"
version = "0.1.0"
description = "Adversarial parallel verification of AI outputs"
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
dependencies = [
    "pydantic>=2.0",
    "anthropic>=0.40.0",
    "httpx>=0.27.0",
    "typer>=0.12.0",
    "rich>=13.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "pytest-mock>=3.14",
]
benchmarks = [
    "datasets>=2.0",
    "numpy>=1.26",
]

[project.scripts]
veritas = "veritas.cli.main:app"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Create all __init__.py files and conftest**

Create empty `__init__.py` in each package directory. Create `tests/conftest.py`:

```python
"""Shared test fixtures for Veritas."""
```

Create `veritas/__init__.py`:

```python
"""Veritas — Adversarial parallel verification of AI outputs."""

__version__ = "0.1.0"
```

- [ ] **Step 3: Verify project installs**

Run: `cd /Users/waqasriaz/Desktop/overstory && pip3 install -e ".[dev]"`
Expected: Successful install with all deps

- [ ] **Step 4: Run pytest to verify it finds tests directory**

Run: `cd /Users/waqasriaz/Desktop/overstory && python -m pytest --co -q`
Expected: "no tests ran" (no test files yet, but no errors)

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml veritas/ tests/
git commit -m "feat: scaffold veritas project structure"
```

---

### Task 2: Data Models — Verdict, FailureMode, AgentFinding, VerificationResult

**Files:**
- Create: `veritas/core/result.py`
- Create: `tests/test_result.py`

- [ ] **Step 1: Write failing tests for data models**

Create `tests/test_result.py`:

```python
"""Tests for Veritas data models."""

import json

from veritas.core.result import (
    AgentFinding,
    ChallengeResult,
    FailureMode,
    FailureModeType,
    Verdict,
    VerificationResult,
)


def test_verdict_enum_values():
    assert Verdict.VERIFIED == "VERIFIED"
    assert Verdict.PARTIAL == "PARTIAL"
    assert Verdict.UNCERTAIN == "UNCERTAIN"
    assert Verdict.DISPUTED == "DISPUTED"
    assert Verdict.REFUTED == "REFUTED"


def test_failure_mode_type_enum_values():
    assert FailureModeType.FACTUAL_ERROR == "factual_error"
    assert FailureModeType.LOGICAL_INCONSISTENCY == "logical_inconsistency"
    assert FailureModeType.UNSUPPORTED_INFERENCE == "unsupported_inference"
    assert FailureModeType.TEMPORAL_ERROR == "temporal_error"
    assert FailureModeType.SCOPE_ERROR == "scope_error"
    assert FailureModeType.SOURCE_CONFLICT == "source_conflict"


def test_failure_mode_creation():
    fm = FailureMode(
        type=FailureModeType.FACTUAL_ERROR,
        detail="Released in 2006, actually 2007",
        agent="source_verifier",
    )
    assert fm.type == FailureModeType.FACTUAL_ERROR
    assert fm.agent == "source_verifier"


def test_agent_finding_creation():
    finding = AgentFinding(
        agent="logic_verifier",
        finding="consistent",
        confidence=0.9,
        details=[{"type": "no_issues", "description": "Claim is internally consistent"}],
    )
    assert finding.agent == "logic_verifier"
    assert finding.confidence == 0.9
    assert finding.sources == []
    assert finding.reasoning == ""


def test_agent_finding_with_sources():
    finding = AgentFinding(
        agent="source_verifier",
        finding="supported",
        confidence=0.85,
        details=[],
        sources=["https://example.com/article"],
        reasoning="Found corroborating source",
    )
    assert len(finding.sources) == 1


def test_challenge_result_creation():
    cr = ChallengeResult(
        contested_points=["Date of release"],
        adversary_finding=AgentFinding(
            agent="adversary",
            finding="counterexample_found",
            confidence=0.8,
            details=[{"type": "factual_error", "description": "Wrong year"}],
        ),
        resolution="Adversary confirmed the date is incorrect",
    )
    assert len(cr.contested_points) == 1


def test_verification_result_creation():
    result = VerificationResult(
        verdict=Verdict.REFUTED,
        confidence=0.91,
        summary="The first iPhone was released June 2007, not 2006.",
        failure_modes=[
            FailureMode(
                type=FailureModeType.FACTUAL_ERROR,
                detail="Wrong release year",
                agent="source_verifier",
            )
        ],
        evidence=[
            AgentFinding(
                agent="source_verifier",
                finding="contradiction",
                confidence=0.95,
                details=[],
                sources=["https://en.wikipedia.org/wiki/IPhone"],
            )
        ],
        contested=False,
        challenge_round=None,
        metadata={"duration_ms": 4200, "agents_used": 5, "model": "claude-sonnet-4-6"},
    )
    assert result.verdict == Verdict.REFUTED
    assert result.confidence == 0.91
    assert len(result.failure_modes) == 1
    assert result.contested is False


def test_verification_result_str():
    result = VerificationResult(
        verdict=Verdict.REFUTED,
        confidence=0.91,
        summary="The first iPhone was released June 2007, not 2006.",
        failure_modes=[],
        evidence=[],
        contested=False,
        challenge_round=None,
        metadata={},
    )
    text = str(result)
    assert "REFUTED" in text
    assert "0.91" in text
    assert "2007" in text


def test_verification_result_to_dict():
    result = VerificationResult(
        verdict=Verdict.VERIFIED,
        confidence=0.95,
        summary="Claim is accurate.",
        failure_modes=[],
        evidence=[],
        contested=False,
        challenge_round=None,
        metadata={"duration_ms": 1000},
    )
    d = result.to_dict()
    assert d["verdict"] == "VERIFIED"
    assert d["confidence"] == 0.95
    # Must be JSON-serializable
    json.dumps(d)


def test_verification_result_report():
    result = VerificationResult(
        verdict=Verdict.PARTIAL,
        confidence=0.6,
        summary="Some parts verified.",
        failure_modes=[
            FailureMode(
                type=FailureModeType.TEMPORAL_ERROR,
                detail="Data from 2020, claim about 2026",
                agent="source_verifier",
            )
        ],
        evidence=[
            AgentFinding(
                agent="logic_verifier",
                finding="consistent",
                confidence=0.9,
                details=[],
            )
        ],
        contested=False,
        challenge_round=None,
        metadata={},
    )
    report = result.report()
    assert "PARTIAL" in report
    assert "temporal_error" in report
    assert "logic_verifier" in report
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_result.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'veritas.core.result'`

- [ ] **Step 3: Implement data models**

Create `veritas/core/result.py`:

```python
"""Veritas data models for verification results."""

from __future__ import annotations

import json
from enum import Enum

from pydantic import BaseModel


class Verdict(str, Enum):
    """Verification verdict categories."""

    VERIFIED = "VERIFIED"
    PARTIAL = "PARTIAL"
    UNCERTAIN = "UNCERTAIN"
    DISPUTED = "DISPUTED"
    REFUTED = "REFUTED"


class FailureModeType(str, Enum):
    """Types of claim failures."""

    FACTUAL_ERROR = "factual_error"
    LOGICAL_INCONSISTENCY = "logical_inconsistency"
    UNSUPPORTED_INFERENCE = "unsupported_inference"
    TEMPORAL_ERROR = "temporal_error"
    SCOPE_ERROR = "scope_error"
    SOURCE_CONFLICT = "source_conflict"


class FailureMode(BaseModel):
    """A specific failure identified in a claim."""

    type: FailureModeType
    detail: str
    agent: str


class AgentFinding(BaseModel):
    """Structured output from a verification agent."""

    agent: str
    finding: str
    confidence: float
    details: list[dict]
    sources: list[str] = []
    reasoning: str = ""


class ChallengeResult(BaseModel):
    """Result of the optional challenge round."""

    contested_points: list[str]
    adversary_finding: AgentFinding
    resolution: str


class VerificationResult(BaseModel):
    """Complete verification result with layered access."""

    verdict: Verdict
    confidence: float
    summary: str
    failure_modes: list[FailureMode]
    evidence: list[AgentFinding]
    contested: bool
    challenge_round: ChallengeResult | None
    metadata: dict

    def __str__(self) -> str:
        return f"{self.verdict.value} ({self.confidence:.2f}) — {self.summary}"

    def to_dict(self) -> dict:
        return json.loads(self.model_dump_json())

    def report(self) -> str:
        lines = [
            f"# Verification Report",
            f"",
            f"**Verdict:** {self.verdict.value}",
            f"**Confidence:** {self.confidence:.2f}",
            f"**Summary:** {self.summary}",
            f"",
        ]
        if self.failure_modes:
            lines.append("## Failure Modes")
            lines.append("")
            for fm in self.failure_modes:
                lines.append(f"- **{fm.type.value}** ({fm.agent}): {fm.detail}")
            lines.append("")
        if self.evidence:
            lines.append("## Evidence")
            lines.append("")
            for ev in self.evidence:
                lines.append(f"### {ev.agent}")
                lines.append(f"- Finding: {ev.finding}")
                lines.append(f"- Confidence: {ev.confidence:.2f}")
                if ev.reasoning:
                    lines.append(f"- Reasoning: {ev.reasoning}")
                if ev.sources:
                    lines.append(f"- Sources: {', '.join(ev.sources)}")
                lines.append("")
        if self.contested and self.challenge_round:
            lines.append("## Challenge Round")
            lines.append("")
            lines.append(f"Contested points: {', '.join(self.challenge_round.contested_points)}")
            lines.append(f"Resolution: {self.challenge_round.resolution}")
            lines.append("")
        return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_result.py -v`
Expected: All 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add veritas/core/result.py tests/test_result.py
git commit -m "feat: add verification result data models"
```

---

### Task 3: Configuration and Error Handling

**Files:**
- Create: `veritas/core/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests for config**

Create `tests/test_config.py`:

```python
"""Tests for Veritas configuration."""

import os

import pytest

from veritas.core.config import Config, VeritasConfigError


def test_config_defaults():
    config = Config()
    assert config.model == "claude-sonnet-4-6"
    assert config.challenge_round is True
    assert config.max_search_results == 5
    assert config.timeout_seconds == 30
    assert config.verbose is False


def test_config_custom_values():
    config = Config(
        model="claude-opus-4-6",
        search_provider="tavily",
        challenge_round=False,
        timeout_seconds=60,
    )
    assert config.model == "claude-opus-4-6"
    assert config.search_provider == "tavily"
    assert config.challenge_round is False
    assert config.timeout_seconds == 60


def test_config_from_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")
    monkeypatch.setenv("BRAVE_API_KEY", "brave-key-456")
    monkeypatch.setenv("VERITAS_MODEL", "claude-opus-4-6")
    config = Config()
    assert config.anthropic_api_key == "test-key-123"
    assert config.search_api_key == "brave-key-456"
    assert config.model == "claude-opus-4-6"


def test_config_tavily_env(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tavily-key-789")
    config = Config()
    assert config.search_api_key == "tavily-key-789"


def test_config_explicit_overrides_env(monkeypatch):
    monkeypatch.setenv("VERITAS_MODEL", "claude-opus-4-6")
    config = Config(model="claude-sonnet-4-6")
    assert config.model == "claude-sonnet-4-6"


def test_veritas_config_error():
    err = VeritasConfigError("Missing API key")
    assert str(err) == "Missing API key"
    assert isinstance(err, Exception)


def test_config_validate_raises_on_missing_anthropic_key():
    config = Config()
    with pytest.raises(VeritasConfigError, match="ANTHROPIC_API_KEY"):
        config.validate()


def test_config_validate_passes_with_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    config = Config()
    config.validate()  # Should not raise
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement config**

Create `veritas/core/config.py`:

```python
"""Veritas configuration and error handling."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


class VeritasConfigError(Exception):
    """Raised when Veritas configuration is invalid."""


@dataclass
class Config:
    """Veritas configuration with environment variable fallbacks."""

    model: str = ""
    search_provider: str = "brave"
    anthropic_api_key: str = ""
    search_api_key: str = ""
    challenge_round: bool = True
    max_search_results: int = 5
    timeout_seconds: int = 30
    verbose: bool = False

    def __post_init__(self):
        if not self.model:
            self.model = os.environ.get("VERITAS_MODEL", "claude-sonnet-4-6")
        if not self.anthropic_api_key:
            self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not self.search_api_key:
            self.search_api_key = os.environ.get(
                "BRAVE_API_KEY", os.environ.get("TAVILY_API_KEY", "")
            )

    def validate(self) -> None:
        """Validate that required configuration is present."""
        if not self.anthropic_api_key:
            raise VeritasConfigError(
                "ANTHROPIC_API_KEY is required. Set it as an environment variable "
                "or pass anthropic_api_key to Config()."
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_config.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add veritas/core/config.py tests/test_config.py
git commit -m "feat: add configuration with env var support"
```

---

### Task 4: Provider Interfaces and Claude Implementation

**Files:**
- Create: `veritas/providers/base.py`
- Create: `veritas/providers/claude.py`
- Create: `veritas/providers/search.py`
- Create: `tests/test_providers.py`

- [ ] **Step 1: Write failing tests for providers**

Create `tests/test_providers.py`:

```python
"""Tests for LLM and search provider interfaces."""

import pytest

from veritas.providers.base import LLMProvider, SearchProvider, SearchResult
from veritas.providers.claude import ClaudeProvider
from veritas.providers.search import BraveSearchProvider, TavilySearchProvider


def test_search_result_creation():
    sr = SearchResult(
        title="iPhone Wikipedia",
        url="https://en.wikipedia.org/wiki/IPhone",
        snippet="The iPhone was released on June 29, 2007.",
    )
    assert sr.title == "iPhone Wikipedia"
    assert "2007" in sr.snippet


def test_claude_provider_instantiation():
    provider = ClaudeProvider(model="claude-sonnet-4-6", api_key="test-key")
    assert provider.model == "claude-sonnet-4-6"


def test_claude_provider_implements_protocol():
    provider = ClaudeProvider(model="claude-sonnet-4-6", api_key="test-key")
    assert isinstance(provider, LLMProvider)


def test_brave_search_provider_instantiation():
    provider = BraveSearchProvider(api_key="test-key")
    assert isinstance(provider, SearchProvider)


def test_tavily_search_provider_instantiation():
    provider = TavilySearchProvider(api_key="test-key")
    assert isinstance(provider, SearchProvider)


@pytest.mark.asyncio
async def test_claude_provider_generate_requires_real_key():
    provider = ClaudeProvider(model="claude-sonnet-4-6", api_key="fake-key")
    with pytest.raises(Exception):
        await provider.generate("Hello")


@pytest.mark.asyncio
async def test_brave_search_requires_real_key():
    provider = BraveSearchProvider(api_key="fake-key")
    with pytest.raises(Exception):
        await provider.search("test query")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_providers.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement provider base**

Create `veritas/providers/base.py`:

```python
"""Provider protocols for LLM and search backends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class SearchResult:
    """A single search result."""

    title: str
    url: str
    snippet: str


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM backends."""

    async def generate(self, prompt: str, system: str = "") -> str: ...


@runtime_checkable
class SearchProvider(Protocol):
    """Protocol for web search backends."""

    async def search(self, query: str, num_results: int = 5) -> list[SearchResult]: ...
```

- [ ] **Step 4: Implement Claude provider**

Create `veritas/providers/claude.py`:

```python
"""Claude/Anthropic LLM provider."""

from __future__ import annotations

import anthropic

from veritas.providers.base import LLMProvider


class ClaudeProvider(LLMProvider):
    """Claude LLM provider using the Anthropic SDK."""

    def __init__(self, model: str = "claude-sonnet-4-6", api_key: str | None = None):
        self.model = model
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def generate(self, prompt: str, system: str = "") -> str:
        message = await self._client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system if system else "You are a verification agent.",
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
```

- [ ] **Step 5: Implement search providers**

Create `veritas/providers/search.py`:

```python
"""Web search providers for source verification."""

from __future__ import annotations

import httpx

from veritas.providers.base import SearchProvider, SearchResult


class BraveSearchProvider(SearchProvider):
    """Brave Search API provider."""

    def __init__(self, api_key: str, num_results: int = 5):
        self.api_key = api_key
        self.default_num_results = num_results

    async def search(self, query: str, num_results: int = 5) -> list[SearchResult]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": num_results},
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": self.api_key,
                },
            )
            response.raise_for_status()
            data = response.json()
            results = []
            for item in data.get("web", {}).get("results", []):
                results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        snippet=item.get("description", ""),
                    )
                )
            return results


class TavilySearchProvider(SearchProvider):
    """Tavily Search API provider."""

    def __init__(self, api_key: str, num_results: int = 5):
        self.api_key = api_key
        self.default_num_results = num_results

    async def search(self, query: str, num_results: int = 5) -> list[SearchResult]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "max_results": num_results,
                },
            )
            response.raise_for_status()
            data = response.json()
            results = []
            for item in data.get("results", []):
                results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        snippet=item.get("content", ""),
                    )
                )
            return results
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_providers.py -v`
Expected: All 7 tests PASS

- [ ] **Step 7: Commit**

```bash
git add veritas/providers/ tests/test_providers.py
git commit -m "feat: add LLM and search provider interfaces"
```

---

### Task 5: Base Agent Interface

**Files:**
- Create: `veritas/agents/base.py`
- Create: `tests/test_agents/__init__.py`
- Create: `tests/test_agents/test_base.py`

- [ ] **Step 1: Write failing tests for base agent**

Create `tests/test_agents/__init__.py` (empty) and `tests/test_agents/test_base.py`:

```python
"""Tests for base agent interface."""

import pytest

from veritas.agents.base import BaseAgent
from veritas.core.result import AgentFinding
from veritas.providers.base import LLMProvider


class MockProvider:
    """Mock LLM provider for testing."""

    def __init__(self, response: str = "mock response"):
        self.response = response
        self.calls: list[dict] = []

    async def generate(self, prompt: str, system: str = "") -> str:
        self.calls.append({"prompt": prompt, "system": system})
        return self.response


def test_base_agent_is_abstract():
    with pytest.raises(TypeError):
        BaseAgent(name="test", provider=MockProvider())


class ConcreteAgent(BaseAgent):
    @property
    def system_prompt(self) -> str:
        return "You are a test agent."

    def parse_response(self, response: str) -> AgentFinding:
        return AgentFinding(
            agent=self.name,
            finding="test",
            confidence=1.0,
            details=[],
        )


def test_concrete_agent_creation():
    provider = MockProvider()
    agent = ConcreteAgent(name="test_agent", provider=provider)
    assert agent.name == "test_agent"


@pytest.mark.asyncio
async def test_concrete_agent_verify():
    provider = MockProvider(response='{"finding": "consistent"}')
    agent = ConcreteAgent(name="test_agent", provider=provider)
    finding = await agent.verify(
        claim="test claim",
        context=None,
        domain=None,
        references=[],
    )
    assert finding.agent == "test_agent"
    assert finding.finding == "test"
    assert len(provider.calls) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_agents/test_base.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement base agent**

Create `veritas/agents/base.py`:

```python
"""Base agent interface for verification agents."""

from __future__ import annotations

from abc import ABC, abstractmethod

from veritas.core.result import AgentFinding
from veritas.providers.base import LLMProvider


class BaseAgent(ABC):
    """Abstract base for all verification agents."""

    def __init__(self, name: str, provider: LLMProvider):
        self.name = name
        self.provider = provider

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt for this agent."""

    @abstractmethod
    def parse_response(self, response: str) -> AgentFinding:
        """Parse LLM response into a structured finding."""

    def build_prompt(
        self,
        claim: str,
        context: str | None,
        domain: str | None,
        references: list[str],
    ) -> str:
        """Build the verification prompt for this agent."""
        parts = [f"## Claim to Verify\n{claim}"]
        if context:
            parts.append(f"\n## Context\n{context}")
        if domain:
            parts.append(f"\n## Domain\n{domain}")
        if references:
            parts.append(f"\n## References\n" + "\n".join(f"- {r}" for r in references))
        return "\n".join(parts)

    async def verify(
        self,
        claim: str,
        context: str | None,
        domain: str | None,
        references: list[str],
    ) -> AgentFinding:
        """Run verification and return structured finding."""
        prompt = self.build_prompt(claim, context, domain, references)
        response = await self.provider.generate(prompt, system=self.system_prompt)
        return self.parse_response(response)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_agents/test_base.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add veritas/agents/base.py tests/test_agents/
git commit -m "feat: add abstract base agent interface"
```

---

### Task 6: Logic Verifier Agent

**Files:**
- Create: `veritas/agents/logic.py`
- Create: `tests/test_agents/test_logic.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_agents/test_logic.py`:

```python
"""Tests for logic verifier agent."""

import json

import pytest

from veritas.agents.logic import LogicVerifier
from veritas.core.result import AgentFinding


class MockProvider:
    def __init__(self, response: str):
        self.response = response

    async def generate(self, prompt: str, system: str = "") -> str:
        return self.response


def test_logic_verifier_system_prompt():
    provider = MockProvider("")
    agent = LogicVerifier(provider=provider)
    assert "logic" in agent.system_prompt.lower()
    assert "consistency" in agent.system_prompt.lower()


def test_logic_verifier_parse_consistent():
    provider = MockProvider("")
    agent = LogicVerifier(provider=provider)
    response = json.dumps({
        "finding": "consistent",
        "confidence": 0.9,
        "details": [],
    })
    finding = agent.parse_response(response)
    assert finding.agent == "logic_verifier"
    assert finding.finding == "consistent"
    assert finding.confidence == 0.9


def test_logic_verifier_parse_inconsistency():
    provider = MockProvider("")
    agent = LogicVerifier(provider=provider)
    response = json.dumps({
        "finding": "inconsistency",
        "confidence": 0.85,
        "details": [
            {
                "type": "logical_inconsistency",
                "description": "Premise A contradicts conclusion B",
            }
        ],
    })
    finding = agent.parse_response(response)
    assert finding.finding == "inconsistency"
    assert len(finding.details) == 1


def test_logic_verifier_parse_malformed_response():
    provider = MockProvider("")
    agent = LogicVerifier(provider=provider)
    finding = agent.parse_response("This is not JSON at all")
    assert finding.agent == "logic_verifier"
    assert finding.finding == "parse_error"
    assert finding.confidence == 0.0


@pytest.mark.asyncio
async def test_logic_verifier_verify():
    response = json.dumps({
        "finding": "consistent",
        "confidence": 0.95,
        "details": [],
    })
    provider = MockProvider(response)
    agent = LogicVerifier(provider=provider)
    finding = await agent.verify(
        claim="Water boils at 100C at sea level",
        context=None,
        domain="scientific",
        references=[],
    )
    assert finding.agent == "logic_verifier"
    assert finding.finding == "consistent"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_agents/test_logic.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement logic verifier**

Create `veritas/agents/logic.py`:

```python
"""Logic Verifier agent — checks internal consistency."""

from __future__ import annotations

import json

from veritas.agents.base import BaseAgent
from veritas.core.result import AgentFinding
from veritas.providers.base import LLMProvider


class LogicVerifier(BaseAgent):
    """Checks claims for internal consistency, contradictions, and logical fallacies."""

    def __init__(self, provider: LLMProvider):
        super().__init__(name="logic_verifier", provider=provider)

    @property
    def system_prompt(self) -> str:
        return """You are a logic verification agent. Your job is to analyze claims for internal consistency, logical fallacies, and contradictions.

You must respond with ONLY a JSON object in this exact format:
{
  "finding": "consistent" | "inconsistency" | "insufficient_info",
  "confidence": <float 0.0-1.0>,
  "details": [
    {
      "type": "logical_inconsistency" | "unsupported_inference" | "scope_error",
      "description": "<specific description of the issue>"
    }
  ]
}

Rules:
- Focus ONLY on logical structure, not factual accuracy
- Check if premises support the conclusion
- Look for self-contradictions within the claim
- Identify scope errors (overgeneralization, false dichotomies)
- If the claim is a single atomic fact, check if it's internally coherent
- Do NOT verify facts against external sources — that's another agent's job"""

    def parse_response(self, response: str) -> AgentFinding:
        try:
            # Handle markdown code blocks
            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            data = json.loads(text)
            return AgentFinding(
                agent=self.name,
                finding=data.get("finding", "parse_error"),
                confidence=float(data.get("confidence", 0.0)),
                details=data.get("details", []),
            )
        except (json.JSONDecodeError, ValueError, KeyError):
            return AgentFinding(
                agent=self.name,
                finding="parse_error",
                confidence=0.0,
                details=[{"type": "error", "description": f"Failed to parse: {response[:200]}"}],
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_agents/test_logic.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add veritas/agents/logic.py tests/test_agents/test_logic.py
git commit -m "feat: add logic verifier agent"
```

---

### Task 7: Source Verifier Agent

**Files:**
- Create: `veritas/agents/source.py`
- Create: `tests/test_agents/test_source.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_agents/test_source.py`:

```python
"""Tests for source verifier agent."""

import json

import pytest

from veritas.agents.source import SourceVerifier
from veritas.core.result import AgentFinding
from veritas.providers.base import SearchResult


class MockProvider:
    def __init__(self, response: str):
        self.response = response

    async def generate(self, prompt: str, system: str = "") -> str:
        return self.response


class MockSearchProvider:
    def __init__(self, results: list[SearchResult] | None = None):
        self.results = results or []
        self.queries: list[str] = []

    async def search(self, query: str, num_results: int = 5) -> list[SearchResult]:
        self.queries.append(query)
        return self.results


def test_source_verifier_system_prompt():
    agent = SourceVerifier(
        provider=MockProvider(""),
        search_provider=MockSearchProvider(),
    )
    assert "source" in agent.system_prompt.lower() or "factual" in agent.system_prompt.lower()


def test_source_verifier_parse_supported():
    agent = SourceVerifier(
        provider=MockProvider(""),
        search_provider=MockSearchProvider(),
    )
    response = json.dumps({
        "finding": "supported",
        "confidence": 0.9,
        "details": [],
        "sources": ["https://example.com"],
        "reasoning": "Found corroborating evidence",
    })
    finding = agent.parse_response(response)
    assert finding.finding == "supported"
    assert len(finding.sources) == 1


def test_source_verifier_parse_contradiction():
    agent = SourceVerifier(
        provider=MockProvider(""),
        search_provider=MockSearchProvider(),
    )
    response = json.dumps({
        "finding": "contradiction",
        "confidence": 0.85,
        "details": [{"type": "factual_error", "description": "Wrong date"}],
        "sources": ["https://example.com/correct"],
        "reasoning": "Source says 2007, claim says 2006",
    })
    finding = agent.parse_response(response)
    assert finding.finding == "contradiction"
    assert finding.reasoning == "Source says 2007, claim says 2006"


def test_source_verifier_parse_malformed():
    agent = SourceVerifier(
        provider=MockProvider(""),
        search_provider=MockSearchProvider(),
    )
    finding = agent.parse_response("not json")
    assert finding.finding == "parse_error"


@pytest.mark.asyncio
async def test_source_verifier_builds_search_context():
    search_results = [
        SearchResult(
            title="iPhone History",
            url="https://example.com/iphone",
            snippet="The iPhone was released June 29, 2007",
        )
    ]
    llm_response = json.dumps({
        "finding": "contradiction",
        "confidence": 0.9,
        "details": [{"type": "factual_error", "description": "Wrong year"}],
        "sources": ["https://example.com/iphone"],
        "reasoning": "2007 not 2006",
    })
    search = MockSearchProvider(search_results)
    agent = SourceVerifier(
        provider=MockProvider(llm_response),
        search_provider=search,
    )
    finding = await agent.verify(
        claim="The iPhone was released in 2006",
        context=None,
        domain=None,
        references=[],
    )
    assert finding.finding == "contradiction"
    assert len(search.queries) >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_agents/test_source.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement source verifier**

Create `veritas/agents/source.py`:

```python
"""Source Verifier agent — factual cross-reference via web search."""

from __future__ import annotations

import json

from veritas.agents.base import BaseAgent
from veritas.core.result import AgentFinding
from veritas.providers.base import LLMProvider, SearchProvider


class SourceVerifier(BaseAgent):
    """Cross-references claims against web search results and provided references."""

    def __init__(self, provider: LLMProvider, search_provider: SearchProvider):
        super().__init__(name="source_verifier", provider=provider)
        self.search_provider = search_provider

    @property
    def system_prompt(self) -> str:
        return """You are a source verification agent. Your job is to check factual claims against provided search results and references.

You must respond with ONLY a JSON object in this exact format:
{
  "finding": "supported" | "contradiction" | "insufficient_info",
  "confidence": <float 0.0-1.0>,
  "details": [
    {
      "type": "factual_error" | "temporal_error" | "source_conflict",
      "description": "<specific description>"
    }
  ],
  "sources": ["<url1>", "<url2>"],
  "reasoning": "<step-by-step reasoning about how sources support or contradict the claim>"
}

Rules:
- Compare EVERY factual element of the claim against the search results
- Cite specific sources for each finding
- If sources disagree with each other, note source_conflict
- If no relevant sources found, report insufficient_info
- Focus on FACTS, not opinions or interpretations"""

    async def verify(
        self,
        claim: str,
        context: str | None,
        domain: str | None,
        references: list[str],
    ) -> AgentFinding:
        search_results = await self.search_provider.search(claim)
        search_context = "\n\n".join(
            f"**{r.title}** ({r.url})\n{r.snippet}" for r in search_results
        )
        prompt_parts = [self.build_prompt(claim, context, domain, references)]
        prompt_parts.append(f"\n## Search Results\n{search_context}")
        full_prompt = "\n".join(prompt_parts)
        response = await self.provider.generate(full_prompt, system=self.system_prompt)
        return self.parse_response(response)

    def parse_response(self, response: str) -> AgentFinding:
        try:
            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            data = json.loads(text)
            return AgentFinding(
                agent=self.name,
                finding=data.get("finding", "parse_error"),
                confidence=float(data.get("confidence", 0.0)),
                details=data.get("details", []),
                sources=data.get("sources", []),
                reasoning=data.get("reasoning", ""),
            )
        except (json.JSONDecodeError, ValueError, KeyError):
            return AgentFinding(
                agent=self.name,
                finding="parse_error",
                confidence=0.0,
                details=[{"type": "error", "description": f"Failed to parse: {response[:200]}"}],
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_agents/test_source.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add veritas/agents/source.py tests/test_agents/test_source.py
git commit -m "feat: add source verifier agent with web search"
```

---

### Task 8: Adversary Agent

**Files:**
- Create: `veritas/agents/adversary.py`
- Create: `tests/test_agents/test_adversary.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_agents/test_adversary.py`:

```python
"""Tests for adversary agent."""

import json

import pytest

from veritas.agents.adversary import Adversary
from veritas.core.result import AgentFinding


class MockProvider:
    def __init__(self, response: str):
        self.response = response

    async def generate(self, prompt: str, system: str = "") -> str:
        return self.response


def test_adversary_system_prompt():
    agent = Adversary(provider=MockProvider(""))
    prompt = agent.system_prompt
    assert "counterexample" in prompt.lower() or "disprove" in prompt.lower()


def test_adversary_parse_no_counterexample():
    agent = Adversary(provider=MockProvider(""))
    response = json.dumps({
        "finding": "no_counterexample",
        "confidence": 0.8,
        "details": [],
        "reasoning": "Could not find any way to disprove this claim",
    })
    finding = agent.parse_response(response)
    assert finding.finding == "no_counterexample"


def test_adversary_parse_counterexample_found():
    agent = Adversary(provider=MockProvider(""))
    response = json.dumps({
        "finding": "counterexample_found",
        "confidence": 0.9,
        "details": [
            {
                "type": "factual_error",
                "description": "If claim were true, X would follow, but X is false",
            }
        ],
        "reasoning": "Constructed counterexample via reductio ad absurdum",
    })
    finding = agent.parse_response(response)
    assert finding.finding == "counterexample_found"
    assert len(finding.details) == 1


def test_adversary_parse_malformed():
    agent = Adversary(provider=MockProvider(""))
    finding = agent.parse_response("garbage")
    assert finding.finding == "parse_error"


@pytest.mark.asyncio
async def test_adversary_verify():
    response = json.dumps({
        "finding": "counterexample_found",
        "confidence": 0.85,
        "details": [{"type": "scope_error", "description": "Claim too broad"}],
        "reasoning": "Not all cases fit",
    })
    agent = Adversary(provider=MockProvider(response))
    finding = await agent.verify(
        claim="All birds can fly",
        context=None,
        domain=None,
        references=[],
    )
    assert finding.finding == "counterexample_found"


@pytest.mark.asyncio
async def test_adversary_challenge():
    response = json.dumps({
        "finding": "counterexample_found",
        "confidence": 0.9,
        "details": [{"type": "factual_error", "description": "Date is wrong"}],
        "reasoning": "Evidence confirms the date discrepancy",
    })
    agent = Adversary(provider=MockProvider(response))
    finding = await agent.challenge(
        claim="iPhone released in 2006",
        contested_points=["Release date conflicts between agents"],
        agent_findings=[],
    )
    assert finding.finding == "counterexample_found"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_agents/test_adversary.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement adversary**

Create `veritas/agents/adversary.py`:

```python
"""Adversary agent — constructs counterexamples and challenges claims."""

from __future__ import annotations

import json

from veritas.agents.base import BaseAgent
from veritas.core.result import AgentFinding
from veritas.providers.base import LLMProvider


class Adversary(BaseAgent):
    """Dedicated adversary that tries to disprove claims via counterexamples."""

    def __init__(self, provider: LLMProvider):
        super().__init__(name="adversary", provider=provider)

    @property
    def system_prompt(self) -> str:
        return """You are an adversary verification agent. Your ONLY job is to try to disprove the claim. You must actively construct counterexamples, find edge cases, and attempt to show the claim is false.

You must respond with ONLY a JSON object in this exact format:
{
  "finding": "counterexample_found" | "no_counterexample" | "insufficient_info",
  "confidence": <float 0.0-1.0>,
  "details": [
    {
      "type": "factual_error" | "logical_inconsistency" | "scope_error" | "temporal_error" | "unsupported_inference",
      "description": "<specific counterexample or challenge>"
    }
  ],
  "reasoning": "<step-by-step adversarial reasoning>"
}

Rules:
- Your DEFAULT stance is skepticism — assume the claim is wrong until proven right
- Try reductio ad absurdum: if the claim is true, what would necessarily follow? Is that true?
- Look for edge cases, exceptions, and boundary conditions
- Check if the claim overgeneralizes or makes unwarranted causal claims
- If you genuinely cannot find a counterexample, say so — but try hard first
- Do NOT be contrarian for its own sake — only raise substantive challenges"""

    def parse_response(self, response: str) -> AgentFinding:
        try:
            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            data = json.loads(text)
            return AgentFinding(
                agent=self.name,
                finding=data.get("finding", "parse_error"),
                confidence=float(data.get("confidence", 0.0)),
                details=data.get("details", []),
                reasoning=data.get("reasoning", ""),
            )
        except (json.JSONDecodeError, ValueError, KeyError):
            return AgentFinding(
                agent=self.name,
                finding="parse_error",
                confidence=0.0,
                details=[{"type": "error", "description": f"Failed to parse: {response[:200]}"}],
            )

    async def challenge(
        self,
        claim: str,
        contested_points: list[str],
        agent_findings: list[AgentFinding],
    ) -> AgentFinding:
        """Run a targeted challenge round on contested points."""
        findings_text = "\n".join(
            f"- {f.agent}: {f.finding} (confidence: {f.confidence})" for f in agent_findings
        )
        prompt = (
            f"## Claim\n{claim}\n\n"
            f"## Contested Points\n" + "\n".join(f"- {p}" for p in contested_points) + "\n\n"
            f"## Agent Findings\n{findings_text}\n\n"
            "Focus your adversarial analysis specifically on the contested points above. "
            "Try to resolve the disagreement by finding definitive evidence for or against."
        )
        response = await self.provider.generate(prompt, system=self.system_prompt)
        return self.parse_response(response)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_agents/test_adversary.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add veritas/agents/adversary.py tests/test_agents/test_adversary.py
git commit -m "feat: add adversary agent with challenge round support"
```

---

### Task 9: Calibration Agent

**Files:**
- Create: `veritas/agents/calibration.py`
- Create: `tests/test_agents/test_calibration.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_agents/test_calibration.py`:

```python
"""Tests for calibration agent."""

import json

import pytest

from veritas.agents.calibration import CalibrationAgent
from veritas.core.result import AgentFinding


class MockProvider:
    def __init__(self, response: str):
        self.response = response

    async def generate(self, prompt: str, system: str = "") -> str:
        return self.response


def test_calibration_agent_system_prompt():
    agent = CalibrationAgent(provider=MockProvider(""))
    prompt = agent.system_prompt
    assert "confidence" in prompt.lower()
    assert "calibrat" in prompt.lower()


def test_calibration_parse_well_calibrated():
    agent = CalibrationAgent(provider=MockProvider(""))
    response = json.dumps({
        "finding": "well_calibrated",
        "confidence": 0.85,
        "details": [],
        "reasoning": "Claim specificity matches expected confidence range",
    })
    finding = agent.parse_response(response)
    assert finding.finding == "well_calibrated"


def test_calibration_parse_overconfident():
    agent = CalibrationAgent(provider=MockProvider(""))
    response = json.dumps({
        "finding": "overconfident",
        "confidence": 0.4,
        "details": [
            {
                "type": "unsupported_inference",
                "description": "Claim stated with certainty but evidence is weak",
            }
        ],
        "reasoning": "Hedging language absent despite uncertain evidence base",
    })
    finding = agent.parse_response(response)
    assert finding.finding == "overconfident"
    assert finding.confidence == 0.4


@pytest.mark.asyncio
async def test_calibration_verify():
    response = json.dumps({
        "finding": "well_calibrated",
        "confidence": 0.9,
        "details": [],
        "reasoning": "Simple factual claim with clear verifiability",
    })
    agent = CalibrationAgent(provider=MockProvider(response))
    finding = await agent.verify(
        claim="Water boils at 100C at sea level",
        context=None,
        domain="scientific",
        references=[],
    )
    assert finding.agent == "calibration"
    assert finding.finding == "well_calibrated"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_agents/test_calibration.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement calibration agent**

Create `veritas/agents/calibration.py`:

```python
"""Calibration agent — audits confidence vs evidence alignment."""

from __future__ import annotations

import json

from veritas.agents.base import BaseAgent
from veritas.core.result import AgentFinding
from veritas.providers.base import LLMProvider


class CalibrationAgent(BaseAgent):
    """Audits whether the confidence level of a claim matches its evidence strength."""

    def __init__(self, provider: LLMProvider):
        super().__init__(name="calibration", provider=provider)

    @property
    def system_prompt(self) -> str:
        return """You are a calibration verification agent. Your job is to assess whether a claim's apparent confidence level is justified by the available evidence.

You must respond with ONLY a JSON object in this exact format:
{
  "finding": "well_calibrated" | "overconfident" | "underconfident" | "insufficient_info",
  "confidence": <float 0.0-1.0 — YOUR confidence in this calibration assessment>,
  "details": [
    {
      "type": "unsupported_inference" | "scope_error",
      "description": "<specific calibration concern>"
    }
  ],
  "reasoning": "<step-by-step analysis of confidence vs evidence>"
}

Rules:
- Analyze the LANGUAGE of the claim: absolute statements ("always", "never", "all") signal high confidence
- Compare claim confidence to its verifiability: can this claim even be checked?
- Hedged claims ("usually", "often", "approximately") are appropriately uncertain
- Specific numbers or dates signal high precision — are they justified?
- Claims about ongoing/changing situations should be less confident than established facts
- If the claim is about a well-established fact, high confidence is appropriate
- "overconfident" means the claim sounds more certain than evidence warrants
- "underconfident" means the claim hedges unnecessarily on well-established facts"""

    def parse_response(self, response: str) -> AgentFinding:
        try:
            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            data = json.loads(text)
            return AgentFinding(
                agent=self.name,
                finding=data.get("finding", "parse_error"),
                confidence=float(data.get("confidence", 0.0)),
                details=data.get("details", []),
                reasoning=data.get("reasoning", ""),
            )
        except (json.JSONDecodeError, ValueError, KeyError):
            return AgentFinding(
                agent=self.name,
                finding="parse_error",
                confidence=0.0,
                details=[{"type": "error", "description": f"Failed to parse: {response[:200]}"}],
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_agents/test_calibration.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add veritas/agents/calibration.py tests/test_agents/test_calibration.py
git commit -m "feat: add calibration agent"
```

---

### Task 10: Synthesiser Agent

**Files:**
- Create: `veritas/agents/synthesiser.py`
- Create: `tests/test_agents/test_synthesiser.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_agents/test_synthesiser.py`:

```python
"""Tests for synthesiser agent."""

import json

import pytest

from veritas.agents.synthesiser import Synthesiser
from veritas.core.result import AgentFinding, VerificationResult, Verdict


class MockProvider:
    def __init__(self, response: str):
        self.response = response

    async def generate(self, prompt: str, system: str = "") -> str:
        return self.response


def _make_finding(agent: str, finding: str, confidence: float, details: list | None = None) -> AgentFinding:
    return AgentFinding(
        agent=agent,
        finding=finding,
        confidence=confidence,
        details=details or [],
    )


def test_synthesiser_creation():
    agent = Synthesiser(provider=MockProvider(""))
    assert agent.name == "synthesiser"


@pytest.mark.asyncio
async def test_synthesiser_all_agree_verified():
    llm_response = json.dumps({
        "verdict": "VERIFIED",
        "confidence": 0.92,
        "summary": "All agents agree the claim is correct.",
        "failure_modes": [],
        "contested": False,
    })
    agent = Synthesiser(provider=MockProvider(llm_response))
    findings = [
        _make_finding("logic_verifier", "consistent", 0.95),
        _make_finding("source_verifier", "supported", 0.9),
        _make_finding("adversary", "no_counterexample", 0.85),
        _make_finding("calibration", "well_calibrated", 0.9),
    ]
    result = await agent.synthesise(
        claim="Water boils at 100C at sea level",
        findings=findings,
    )
    assert result.verdict == Verdict.VERIFIED
    assert result.confidence > 0.8
    assert result.contested is False


@pytest.mark.asyncio
async def test_synthesiser_refuted():
    llm_response = json.dumps({
        "verdict": "REFUTED",
        "confidence": 0.91,
        "summary": "The iPhone was released in 2007, not 2006.",
        "failure_modes": [
            {"type": "factual_error", "detail": "Wrong year", "agent": "source_verifier"}
        ],
        "contested": False,
    })
    agent = Synthesiser(provider=MockProvider(llm_response))
    findings = [
        _make_finding("logic_verifier", "consistent", 0.9),
        _make_finding("source_verifier", "contradiction", 0.95,
                      [{"type": "factual_error", "description": "Wrong year"}]),
        _make_finding("adversary", "counterexample_found", 0.9),
        _make_finding("calibration", "overconfident", 0.7),
    ]
    result = await agent.synthesise(claim="iPhone released in 2006", findings=findings)
    assert result.verdict == Verdict.REFUTED
    assert len(result.failure_modes) > 0


@pytest.mark.asyncio
async def test_synthesiser_detects_conflict():
    llm_response = json.dumps({
        "verdict": "DISPUTED",
        "confidence": 0.5,
        "summary": "Agents disagree on the claim.",
        "failure_modes": [],
        "contested": True,
    })
    agent = Synthesiser(provider=MockProvider(llm_response))
    findings = [
        _make_finding("logic_verifier", "consistent", 0.9),
        _make_finding("source_verifier", "supported", 0.8),
        _make_finding("adversary", "counterexample_found", 0.85),
        _make_finding("calibration", "overconfident", 0.6),
    ]
    result = await agent.synthesise(claim="Contested claim", findings=findings)
    assert result.contested is True


@pytest.mark.asyncio
async def test_synthesiser_handles_missing_agents():
    llm_response = json.dumps({
        "verdict": "UNCERTAIN",
        "confidence": 0.3,
        "summary": "Insufficient agent data.",
        "failure_modes": [],
        "contested": False,
    })
    agent = Synthesiser(provider=MockProvider(llm_response))
    findings = [
        _make_finding("logic_verifier", "consistent", 0.9),
    ]
    result = await agent.synthesise(claim="Some claim", findings=findings)
    assert result.verdict == Verdict.UNCERTAIN
    assert "agents_used" in result.metadata


@pytest.mark.asyncio
async def test_synthesiser_handles_malformed_llm_response():
    agent = Synthesiser(provider=MockProvider("not json at all"))
    findings = [_make_finding("logic_verifier", "consistent", 0.9)]
    result = await agent.synthesise(claim="test", findings=findings)
    assert result.verdict == Verdict.UNCERTAIN
    assert result.confidence == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_agents/test_synthesiser.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement synthesiser**

Create `veritas/agents/synthesiser.py`:

```python
"""Synthesiser agent — aggregates all findings into a structured verdict."""

from __future__ import annotations

import json
import time

from veritas.agents.base import BaseAgent
from veritas.core.result import (
    AgentFinding,
    FailureMode,
    FailureModeType,
    Verdict,
    VerificationResult,
)
from veritas.providers.base import LLMProvider

_FAILURE_TYPE_MAP = {v.value: v for v in FailureModeType}


class Synthesiser(BaseAgent):
    """Aggregates all agent findings into a final verdict."""

    def __init__(self, provider: LLMProvider):
        super().__init__(name="synthesiser", provider=provider)

    @property
    def system_prompt(self) -> str:
        return """You are a synthesis agent. You receive findings from multiple independent verification agents and must produce a final verdict.

You must respond with ONLY a JSON object in this exact format:
{
  "verdict": "VERIFIED" | "PARTIAL" | "UNCERTAIN" | "DISPUTED" | "REFUTED",
  "confidence": <float 0.0-1.0>,
  "summary": "<one-sentence human-readable summary>",
  "failure_modes": [
    {"type": "<failure_type>", "detail": "<description>", "agent": "<which agent found it>"}
  ],
  "contested": <true if agents significantly disagree, false otherwise>
}

Verdict rules:
- VERIFIED: All agents agree claim is supported, no counterexamples
- PARTIAL: Some parts verified, others not (compound claims)
- UNCERTAIN: Insufficient evidence to determine
- DISPUTED: Agents significantly disagree even after analysis
- REFUTED: Clear evidence contradicts the claim

failure_mode types: factual_error, logical_inconsistency, unsupported_inference, temporal_error, scope_error, source_conflict

Rules:
- Weight source_verifier highest for factual claims
- Weight logic_verifier highest for reasoning claims
- If adversary found a counterexample AND source_verifier supports the claim, mark as contested
- Calibration findings adjust your confidence, not the verdict
- Be precise in your summary — cite specific errors if found"""

    def parse_response(self, response: str) -> AgentFinding:
        # Not used directly — synthesise() handles parsing
        return AgentFinding(agent=self.name, finding="", confidence=0.0, details=[])

    async def synthesise(
        self,
        claim: str,
        findings: list[AgentFinding],
    ) -> VerificationResult:
        """Aggregate agent findings into a final VerificationResult."""
        start = time.monotonic()
        findings_text = "\n\n".join(
            f"### {f.agent}\n"
            f"- Finding: {f.finding}\n"
            f"- Confidence: {f.confidence}\n"
            f"- Details: {json.dumps(f.details)}\n"
            f"- Reasoning: {f.reasoning}"
            for f in findings
        )
        prompt = (
            f"## Claim\n{claim}\n\n"
            f"## Agent Findings\n{findings_text}\n\n"
            "Synthesise these findings into a single verdict."
        )
        response = await self.provider.generate(prompt, system=self.system_prompt)
        duration_ms = int((time.monotonic() - start) * 1000)

        try:
            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            data = json.loads(text)

            failure_modes = []
            for fm in data.get("failure_modes", []):
                fm_type = _FAILURE_TYPE_MAP.get(fm.get("type", ""))
                if fm_type:
                    failure_modes.append(
                        FailureMode(
                            type=fm_type,
                            detail=fm.get("detail", ""),
                            agent=fm.get("agent", "unknown"),
                        )
                    )

            return VerificationResult(
                verdict=Verdict(data["verdict"]),
                confidence=float(data.get("confidence", 0.0)),
                summary=data.get("summary", ""),
                failure_modes=failure_modes,
                evidence=findings,
                contested=data.get("contested", False),
                challenge_round=None,
                metadata={
                    "duration_ms": duration_ms,
                    "agents_used": len(findings),
                    "model": "synthesiser",
                },
            )
        except (json.JSONDecodeError, ValueError, KeyError):
            return VerificationResult(
                verdict=Verdict.UNCERTAIN,
                confidence=0.0,
                summary="Failed to synthesise agent findings.",
                failure_modes=[],
                evidence=findings,
                contested=False,
                challenge_round=None,
                metadata={
                    "duration_ms": duration_ms,
                    "agents_used": len(findings),
                    "error": f"Parse error: {response[:200]}",
                },
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_agents/test_synthesiser.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add veritas/agents/synthesiser.py tests/test_agents/test_synthesiser.py
git commit -m "feat: add synthesiser agent with verdict aggregation"
```

---

### Task 11: Orchestration — Runner and Messaging

**Files:**
- Create: `veritas/orchestration/runner.py`
- Create: `veritas/orchestration/messaging.py`
- Create: `veritas/orchestration/challenge.py`
- Create: `tests/test_orchestration.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_orchestration.py`:

```python
"""Tests for orchestration layer."""

import json

import pytest

from veritas.core.config import Config
from veritas.core.result import AgentFinding, Verdict
from veritas.orchestration.runner import VerificationRunner


class MockProvider:
    def __init__(self, responses: dict[str, str]):
        self.responses = responses
        self.call_count = 0

    async def generate(self, prompt: str, system: str = "") -> str:
        self.call_count += 1
        for key, response in self.responses.items():
            if key in system.lower():
                return response
        return json.dumps({"finding": "consistent", "confidence": 0.5, "details": []})


class MockSearchProvider:
    async def search(self, query: str, num_results: int = 5):
        from veritas.providers.base import SearchResult
        return [SearchResult(title="Test", url="https://test.com", snippet="Test result")]


def _mock_responses():
    return {
        "logic": json.dumps({"finding": "consistent", "confidence": 0.9, "details": []}),
        "source": json.dumps({
            "finding": "supported", "confidence": 0.85, "details": [],
            "sources": ["https://test.com"], "reasoning": "Found support",
        }),
        "adversary": json.dumps({
            "finding": "no_counterexample", "confidence": 0.8,
            "details": [], "reasoning": "Could not disprove",
        }),
        "calibrat": json.dumps({
            "finding": "well_calibrated", "confidence": 0.85,
            "details": [], "reasoning": "Appropriate confidence",
        }),
        "synthe": json.dumps({
            "verdict": "VERIFIED", "confidence": 0.88,
            "summary": "Claim is verified.", "failure_modes": [], "contested": False,
        }),
    }


@pytest.mark.asyncio
async def test_runner_runs_all_agents():
    provider = MockProvider(_mock_responses())
    search = MockSearchProvider()
    runner = VerificationRunner(
        llm_provider=provider,
        search_provider=search,
        config=Config(),
    )
    result = await runner.run(
        claim="Water boils at 100C at sea level",
        context=None,
        domain="scientific",
        references=[],
    )
    assert result.verdict == Verdict.VERIFIED
    assert len(result.evidence) == 4
    assert provider.call_count == 5  # 4 agents + synthesiser


@pytest.mark.asyncio
async def test_runner_with_challenge_round():
    responses = _mock_responses()
    # Make synthesiser report conflict first time, then resolve
    call_num = [0]
    original_synth = responses["synthe"]

    class ChallengeProvider:
        async def generate(self, prompt: str, system: str = "") -> str:
            for key, response in responses.items():
                if key in system.lower():
                    if key == "synthe":
                        call_num[0] += 1
                        if call_num[0] == 1:
                            return json.dumps({
                                "verdict": "DISPUTED", "confidence": 0.5,
                                "summary": "Agents disagree.",
                                "failure_modes": [], "contested": True,
                            })
                        return json.dumps({
                            "verdict": "VERIFIED", "confidence": 0.85,
                            "summary": "Resolved after challenge.",
                            "failure_modes": [], "contested": False,
                        })
                    return response
            return json.dumps({"finding": "consistent", "confidence": 0.5, "details": []})

    runner = VerificationRunner(
        llm_provider=ChallengeProvider(),
        search_provider=MockSearchProvider(),
        config=Config(challenge_round=True),
    )
    result = await runner.run(
        claim="Contested claim",
        context=None,
        domain=None,
        references=[],
    )
    assert result.challenge_round is not None or result.verdict in (Verdict.VERIFIED, Verdict.DISPUTED)


@pytest.mark.asyncio
async def test_runner_no_challenge_when_disabled():
    responses = _mock_responses()
    responses["synthe"] = json.dumps({
        "verdict": "DISPUTED", "confidence": 0.5,
        "summary": "Agents disagree.", "failure_modes": [], "contested": True,
    })
    runner = VerificationRunner(
        llm_provider=MockProvider(responses),
        search_provider=MockSearchProvider(),
        config=Config(challenge_round=False),
    )
    result = await runner.run(claim="test", context=None, domain=None, references=[])
    assert result.challenge_round is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_orchestration.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement messaging**

Create `veritas/orchestration/messaging.py`:

```python
"""Message passing abstraction for agent communication."""

from __future__ import annotations

from dataclasses import dataclass, field

from veritas.core.result import AgentFinding


@dataclass
class AgentMessage:
    """A message from an agent to the synthesiser."""

    agent_name: str
    finding: AgentFinding


class MessageBus:
    """In-process message bus for collecting agent findings.

    In Overstory mode, this would be backed by SQLite mail.
    For now, uses in-memory collection for the async runner.
    """

    def __init__(self):
        self._messages: list[AgentMessage] = []

    def send(self, agent_name: str, finding: AgentFinding) -> None:
        self._messages.append(AgentMessage(agent_name=agent_name, finding=finding))

    def collect(self) -> list[AgentFinding]:
        return [m.finding for m in self._messages]

    def clear(self) -> None:
        self._messages.clear()
```

- [ ] **Step 4: Implement challenge round**

Create `veritas/orchestration/challenge.py`:

```python
"""Challenge round logic for contested verifications."""

from __future__ import annotations

from veritas.agents.adversary import Adversary
from veritas.agents.synthesiser import Synthesiser
from veritas.core.result import (
    AgentFinding,
    ChallengeResult,
    VerificationResult,
)


async def run_challenge_round(
    claim: str,
    initial_result: VerificationResult,
    adversary: Adversary,
    synthesiser: Synthesiser,
) -> VerificationResult:
    """Run a challenge round when the synthesiser detects conflicts."""
    # Identify contested points from conflicting findings
    contested_points = _identify_contested_points(initial_result.evidence)
    if not contested_points:
        return initial_result

    # Adversary re-examines contested points
    challenge_finding = await adversary.challenge(
        claim=claim,
        contested_points=contested_points,
        agent_findings=initial_result.evidence,
    )

    # Re-synthesise with challenge finding included
    all_findings = list(initial_result.evidence) + [challenge_finding]
    final_result = await synthesiser.synthesise(claim=claim, findings=all_findings)

    # Attach challenge round info
    final_result.challenge_round = ChallengeResult(
        contested_points=contested_points,
        adversary_finding=challenge_finding,
        resolution=f"Challenge round completed. Final verdict: {final_result.verdict.value}",
    )
    return final_result


def _identify_contested_points(findings: list[AgentFinding]) -> list[str]:
    """Extract contested points from conflicting findings."""
    contested = []
    positive = {"supported", "consistent", "no_counterexample", "well_calibrated"}
    negative = {"contradiction", "inconsistency", "counterexample_found", "overconfident"}

    has_positive = any(f.finding in positive for f in findings)
    has_negative = any(f.finding in negative for f in findings)

    if has_positive and has_negative:
        for f in findings:
            if f.finding in negative:
                for detail in f.details:
                    desc = detail.get("description", "")
                    if desc:
                        contested.append(f"{f.agent}: {desc}")
                if not f.details:
                    contested.append(f"{f.agent} reports {f.finding}")

    return contested
```

- [ ] **Step 5: Implement runner**

Create `veritas/orchestration/runner.py`:

```python
"""Verification runner — orchestrates all agents."""

from __future__ import annotations

import asyncio
import time

from veritas.agents.adversary import Adversary
from veritas.agents.calibration import CalibrationAgent
from veritas.agents.logic import LogicVerifier
from veritas.agents.source import SourceVerifier
from veritas.agents.synthesiser import Synthesiser
from veritas.core.config import Config
from veritas.core.result import VerificationResult
from veritas.orchestration.challenge import run_challenge_round
from veritas.providers.base import LLMProvider, SearchProvider


class VerificationRunner:
    """Orchestrates parallel agent verification and synthesis.

    In v1, agents run as async tasks in the same process.
    Overstory integration (git worktree isolation) will wrap this
    with true process isolation in a future version.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        search_provider: SearchProvider,
        config: Config,
    ):
        self.config = config
        self.logic = LogicVerifier(provider=llm_provider)
        self.source = SourceVerifier(provider=llm_provider, search_provider=search_provider)
        self.adversary = Adversary(provider=llm_provider)
        self.calibration = CalibrationAgent(provider=llm_provider)
        self.synthesiser = Synthesiser(provider=llm_provider)

    async def run(
        self,
        claim: str,
        context: str | None,
        domain: str | None,
        references: list[str],
    ) -> VerificationResult:
        """Run all verification agents in parallel and synthesise results."""
        start = time.monotonic()

        # Phase 1: Run all 4 agents in parallel
        findings = await asyncio.gather(
            self.logic.verify(claim, context, domain, references),
            self.source.verify(claim, context, domain, references),
            self.adversary.verify(claim, context, domain, references),
            self.calibration.verify(claim, context, domain, references),
        )
        findings_list = list(findings)

        # Synthesise
        result = await self.synthesiser.synthesise(claim=claim, findings=findings_list)

        # Optional challenge round
        if result.contested and self.config.challenge_round:
            result = await run_challenge_round(
                claim=claim,
                initial_result=result,
                adversary=self.adversary,
                synthesiser=self.synthesiser,
            )

        # Update metadata with total duration
        duration_ms = int((time.monotonic() - start) * 1000)
        result.metadata["total_duration_ms"] = duration_ms
        result.metadata["model"] = self.config.model

        return result
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_orchestration.py -v`
Expected: All 3 tests PASS

- [ ] **Step 7: Commit**

```bash
git add veritas/orchestration/ tests/test_orchestration.py
git commit -m "feat: add orchestration runner with challenge round support"
```

---

### Task 12: Core verify() Function and Public API

**Files:**
- Create: `veritas/core/verify.py`
- Modify: `veritas/__init__.py`
- Create: `tests/test_verify.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_verify.py`:

```python
"""Tests for the public verify() API."""

import json
import os

import pytest

from veritas import VerificationResult, Verdict, verify
from veritas.core.config import Config, VeritasConfigError


def test_verify_rejects_empty_claim():
    with pytest.raises(ValueError, match="claim"):
        # Use asyncio to run
        import asyncio
        asyncio.run(verify(""))


def test_verify_rejects_missing_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(VeritasConfigError):
        import asyncio
        asyncio.run(verify("test claim"))


@pytest.mark.asyncio
async def test_verify_returns_verification_result(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    # Mock the runner to avoid real API calls
    from unittest.mock import AsyncMock, patch
    from veritas.core.result import VerificationResult, Verdict

    mock_result = VerificationResult(
        verdict=Verdict.VERIFIED,
        confidence=0.9,
        summary="Test passed.",
        failure_modes=[],
        evidence=[],
        contested=False,
        challenge_round=None,
        metadata={},
    )

    with patch("veritas.core.verify.VerificationRunner") as MockRunner:
        instance = MockRunner.return_value
        instance.run = AsyncMock(return_value=mock_result)
        result = await verify("Water boils at 100C")

    assert isinstance(result, VerificationResult)
    assert result.verdict == Verdict.VERIFIED


@pytest.mark.asyncio
async def test_verify_passes_all_options(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    from unittest.mock import AsyncMock, patch
    from veritas.core.result import VerificationResult, Verdict

    mock_result = VerificationResult(
        verdict=Verdict.VERIFIED, confidence=0.9, summary="OK",
        failure_modes=[], evidence=[], contested=False,
        challenge_round=None, metadata={},
    )

    with patch("veritas.core.verify.VerificationRunner") as MockRunner:
        instance = MockRunner.return_value
        instance.run = AsyncMock(return_value=mock_result)
        result = await verify(
            "Test claim",
            context="Some context",
            domain="technical",
            references=["doc.pdf"],
            model="claude-opus-4-6",
        )
        instance.run.assert_called_once_with(
            claim="Test claim",
            context="Some context",
            domain="technical",
            references=["doc.pdf"],
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_verify.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Implement verify()**

Create `veritas/core/verify.py`:

```python
"""Main verify() function — public entry point for Veritas."""

from __future__ import annotations

from veritas.core.config import Config, VeritasConfigError
from veritas.core.result import VerificationResult
from veritas.orchestration.runner import VerificationRunner
from veritas.providers.claude import ClaudeProvider
from veritas.providers.search import BraveSearchProvider, TavilySearchProvider


async def verify(
    claim: str,
    context: str | None = None,
    domain: str | None = None,
    references: list[str] | None = None,
    model: str | None = None,
    config: Config | None = None,
) -> VerificationResult:
    """Verify a claim using adversarial parallel verification.

    Args:
        claim: The claim to verify.
        context: Optional surrounding context.
        domain: Optional domain hint (technical, scientific, medical, legal, general).
        references: Optional list of reference document paths.
        model: Optional model override.
        config: Optional full configuration object.

    Returns:
        VerificationResult with verdict, confidence, evidence, and failure modes.

    Raises:
        ValueError: If claim is empty.
        VeritasConfigError: If required configuration is missing.
    """
    if not claim or not claim.strip():
        raise ValueError("claim must be a non-empty string")

    if config is None:
        config = Config()
    if model:
        config.model = model
    config.validate()

    llm_provider = ClaudeProvider(model=config.model, api_key=config.anthropic_api_key)

    if config.search_provider == "tavily":
        search_provider = TavilySearchProvider(api_key=config.search_api_key)
    else:
        search_provider = BraveSearchProvider(api_key=config.search_api_key)

    runner = VerificationRunner(
        llm_provider=llm_provider,
        search_provider=search_provider,
        config=config,
    )

    return await runner.run(
        claim=claim,
        context=context,
        domain=domain,
        references=references or [],
    )
```

- [ ] **Step 4: Update public API exports**

Modify `veritas/__init__.py`:

```python
"""Veritas — Adversarial parallel verification of AI outputs."""

__version__ = "0.1.0"

from veritas.core.config import Config, VeritasConfigError
from veritas.core.result import (
    AgentFinding,
    ChallengeResult,
    FailureMode,
    FailureModeType,
    Verdict,
    VerificationResult,
)
from veritas.core.verify import verify

__all__ = [
    "verify",
    "Config",
    "VeritasConfigError",
    "Verdict",
    "VerificationResult",
    "FailureMode",
    "FailureModeType",
    "AgentFinding",
    "ChallengeResult",
]
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_verify.py -v`
Expected: All 4 tests PASS

- [ ] **Step 6: Run all tests to verify nothing broke**

Run: `python -m pytest -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add veritas/__init__.py veritas/core/verify.py tests/test_verify.py
git commit -m "feat: add public verify() API and exports"
```

---

### Task 13: CLI — check and shell Commands

**Files:**
- Create: `veritas/cli/main.py`
- Create: `veritas/cli/shell.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_cli.py`:

```python
"""Tests for CLI interface."""

import pytest
from typer.testing import CliRunner

from veritas.cli.main import app

runner = CliRunner()


def test_cli_check_rejects_empty():
    result = runner.invoke(app, ["check", ""])
    assert result.exit_code != 0


def test_cli_check_missing_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = runner.invoke(app, ["check", "Test claim"])
    assert result.exit_code != 0
    assert "ANTHROPIC_API_KEY" in result.stdout or result.exit_code != 0


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "veritas" in result.stdout.lower() or "check" in result.stdout.lower()


def test_cli_check_help():
    result = runner.invoke(app, ["check", "--help"])
    assert result.exit_code == 0
    assert "--verbose" in result.stdout
    assert "--json" in result.stdout
    assert "--domain" in result.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement CLI main**

Create `veritas/cli/main.py`:

```python
"""Veritas CLI — command-line interface for claim verification."""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Optional

import typer
from rich.console import Console

from veritas.core.config import Config, VeritasConfigError
from veritas.core.verify import verify

app = typer.Typer(name="veritas", help="Adversarial parallel verification of AI outputs.")
console = Console()


@app.command()
def check(
    claim: str = typer.Argument("", help="The claim to verify"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full evidence chain"),
    output_json: bool = typer.Option(False, "--json", help="Output as JSON"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Domain hint"),
    ref: Optional[list[str]] = typer.Option(None, "--ref", "-r", help="Reference document path"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="LLM model to use"),
    no_search: bool = typer.Option(False, "--no-search", help="Disable web search"),
    stdin: bool = typer.Option(False, "--stdin", help="Read claim from stdin"),
):
    """Verify a claim for factual accuracy."""
    if stdin:
        claim = sys.stdin.read().strip()
    if not claim:
        console.print("[red]Error: claim must not be empty[/red]")
        raise typer.Exit(code=1)

    try:
        config = Config()
        if no_search:
            config.search_api_key = ""
        result = asyncio.run(
            verify(
                claim=claim,
                domain=domain,
                references=ref or [],
                model=model,
                config=config,
            )
        )

        if output_json:
            console.print_json(json.dumps(result.to_dict(), indent=2))
        elif verbose:
            console.print(result.report())
        else:
            console.print(str(result))

    except VeritasConfigError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def shell():
    """Start an interactive verification shell."""
    from veritas.cli.shell import run_shell
    run_shell()


if __name__ == "__main__":
    app()
```

- [ ] **Step 4: Implement interactive shell**

Create `veritas/cli/shell.py`:

```python
"""Interactive verification shell."""

from __future__ import annotations

import asyncio

from rich.console import Console

from veritas.core.config import Config, VeritasConfigError
from veritas.core.verify import verify

console = Console()


def run_shell():
    """Run the interactive Veritas shell."""
    console.print("[bold]Veritas v0.1.0[/bold] — Type a claim to verify. /help for commands.\n")

    verbose = False

    try:
        Config().validate()
    except VeritasConfigError as e:
        console.print(f"[red]{e}[/red]")
        return

    while True:
        try:
            line = console.input("[bold cyan]veritas>[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nBye!")
            break

        if not line:
            continue

        if line.startswith("/"):
            cmd = line.lower()
            if cmd == "/quit" or cmd == "/exit":
                console.print("Bye!")
                break
            elif cmd == "/verbose":
                verbose = not verbose
                console.print(f"Verbose mode {'on' if verbose else 'off'}.")
            elif cmd == "/help":
                console.print("Commands: /verbose, /quit, /help")
                console.print("Type any claim to verify it.")
            else:
                console.print(f"Unknown command: {line}")
            continue

        try:
            result = asyncio.run(verify(line))
            if verbose:
                console.print(result.report())
            else:
                console.print(str(result))
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

        console.print()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_cli.py -v`
Expected: All 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add veritas/cli/ tests/test_cli.py
git commit -m "feat: add CLI with check, shell commands"
```

---

### Task 14: Overstory Agent Definitions

**Files:**
- Create: `.overstory/agent-defs/veritas-logic.md`
- Create: `.overstory/agent-defs/veritas-source.md`
- Create: `.overstory/agent-defs/veritas-adversary.md`
- Create: `.overstory/agent-defs/veritas-calibration.md`
- Create: `.overstory/agent-defs/veritas-synthesiser.md`

- [ ] **Step 1: Create Logic Verifier agent def**

Create `.overstory/agent-defs/veritas-logic.md`:

```markdown
# Veritas Logic Verifier

## Identity
You are the Logic Verifier agent in the Veritas verification system. You analyze claims for internal consistency, logical fallacies, and contradictions.

## Scope
- Check if premises support conclusions
- Identify self-contradictions
- Find scope errors (overgeneralization, false dichotomies)
- Detect unsupported inferences

## Constraints
- Do NOT verify facts against external sources
- Do NOT access web search
- Focus ONLY on logical structure
- Output ONLY valid JSON

## Output Format
Write your finding as JSON to `veritas-output.json` in your worktree root.
```

- [ ] **Step 2: Create Source Verifier agent def**

Create `.overstory/agent-defs/veritas-source.md`:

```markdown
# Veritas Source Verifier

## Identity
You are the Source Verifier agent in the Veritas verification system. You cross-reference claims against web search results and provided reference documents.

## Scope
- Decompose claims into atomic checkable facts
- Search the web for each fact
- Cross-reference against user-provided references
- Cite specific sources for every finding

## Constraints
- Compare EVERY factual element against sources
- Report source_conflict when sources disagree
- Report insufficient_info when no sources found
- Output ONLY valid JSON

## Output Format
Write your finding as JSON to `veritas-output.json` in your worktree root.
```

- [ ] **Step 3: Create Adversary agent def**

Create `.overstory/agent-defs/veritas-adversary.md`:

```markdown
# Veritas Adversary

## Identity
You are the Adversary agent in the Veritas verification system. Your job is to try to DISPROVE the claim.

## Scope
- Construct counterexamples
- Find edge cases and exceptions
- Use reductio ad absurdum reasoning
- Challenge overgeneralizations and causal claims

## Constraints
- Default stance is SKEPTICISM
- Only raise substantive challenges, not contrarian noise
- If you cannot find a counterexample, say so honestly
- Output ONLY valid JSON

## Output Format
Write your finding as JSON to `veritas-output.json` in your worktree root.
```

- [ ] **Step 4: Create Calibration agent def**

Create `.overstory/agent-defs/veritas-calibration.md`:

```markdown
# Veritas Calibration Agent

## Identity
You are the Calibration agent in the Veritas verification system. You assess whether a claim's confidence level matches its evidence strength.

## Scope
- Analyze claim language for confidence signals
- Compare claim certainty to verifiability
- Flag overconfident claims (absolute language, weak evidence)
- Flag underconfident claims (unnecessary hedging on established facts)

## Constraints
- Do NOT verify facts — only assess calibration
- Focus on the GAP between confidence and evidence
- Output ONLY valid JSON

## Output Format
Write your finding as JSON to `veritas-output.json` in your worktree root.
```

- [ ] **Step 5: Create Synthesiser agent def**

Create `.overstory/agent-defs/veritas-synthesiser.md`:

```markdown
# Veritas Synthesiser

## Identity
You are the Synthesiser agent in the Veritas verification system. You aggregate findings from all verification agents into a final verdict.

## Scope
- Read all agent findings
- Determine verdict: VERIFIED, PARTIAL, UNCERTAIN, DISPUTED, REFUTED
- Identify failure modes from the taxonomy
- Produce human-readable summary

## Verdict Rules
- VERIFIED: All agents agree, evidence supports claim
- PARTIAL: Some parts verified, some not
- UNCERTAIN: Insufficient evidence
- DISPUTED: Agents significantly disagree
- REFUTED: Clear evidence contradicts claim

## Constraints
- Weight source_verifier highest for factual claims
- Weight logic_verifier highest for reasoning claims
- Calibration adjusts confidence, not verdict
- Output ONLY valid JSON
```

- [ ] **Step 6: Commit**

```bash
git add .overstory/agent-defs/veritas-*.md
git commit -m "feat: add Overstory agent definitions for all 5 Veritas agents"
```

---

### Task 15: Benchmark Harness

**Files:**
- Create: `veritas/benchmarks/runner.py`
- Create: `veritas/benchmarks/datasets.py`
- Create: `veritas/benchmarks/metrics.py`
- Create: `tests/test_benchmarks.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_benchmarks.py`:

```python
"""Tests for benchmark harness."""

import pytest

from veritas.benchmarks.metrics import accuracy, expected_calibration_error
from veritas.core.result import Verdict


def test_accuracy_all_correct():
    predictions = [Verdict.VERIFIED, Verdict.REFUTED, Verdict.PARTIAL]
    labels = [Verdict.VERIFIED, Verdict.REFUTED, Verdict.PARTIAL]
    assert accuracy(predictions, labels) == 1.0


def test_accuracy_none_correct():
    predictions = [Verdict.VERIFIED, Verdict.VERIFIED]
    labels = [Verdict.REFUTED, Verdict.REFUTED]
    assert accuracy(predictions, labels) == 0.0


def test_accuracy_partial():
    predictions = [Verdict.VERIFIED, Verdict.REFUTED, Verdict.VERIFIED]
    labels = [Verdict.VERIFIED, Verdict.REFUTED, Verdict.REFUTED]
    assert abs(accuracy(predictions, labels) - 2 / 3) < 0.01


def test_accuracy_empty():
    assert accuracy([], []) == 0.0


def test_ece_perfect_calibration():
    confidences = [0.9, 0.9, 0.1, 0.1]
    correct = [True, True, False, False]
    ece = expected_calibration_error(confidences, correct, n_bins=2)
    assert ece < 0.1


def test_ece_worst_calibration():
    confidences = [0.9, 0.9, 0.9, 0.9]
    correct = [False, False, False, False]
    ece = expected_calibration_error(confidences, correct, n_bins=1)
    assert ece > 0.8
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_benchmarks.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement metrics**

Create `veritas/benchmarks/metrics.py`:

```python
"""Benchmark metrics for verification evaluation."""

from __future__ import annotations

from veritas.core.result import Verdict


def accuracy(predictions: list[Verdict], labels: list[Verdict]) -> float:
    """Calculate accuracy: fraction of correct verdicts."""
    if not predictions:
        return 0.0
    correct = sum(1 for p, l in zip(predictions, labels) if p == l)
    return correct / len(predictions)


def expected_calibration_error(
    confidences: list[float],
    correct: list[bool],
    n_bins: int = 10,
) -> float:
    """Calculate Expected Calibration Error (ECE).

    Measures how well confidence scores align with actual accuracy.
    Lower is better. 0.0 = perfectly calibrated.
    """
    if not confidences:
        return 0.0

    bin_boundaries = [i / n_bins for i in range(n_bins + 1)]
    ece = 0.0
    total = len(confidences)

    for i in range(n_bins):
        lo, hi = bin_boundaries[i], bin_boundaries[i + 1]
        indices = [
            j for j, c in enumerate(confidences)
            if (lo <= c < hi) or (i == n_bins - 1 and c == hi)
        ]
        if not indices:
            continue

        bin_conf = sum(confidences[j] for j in indices) / len(indices)
        bin_acc = sum(1 for j in indices if correct[j]) / len(indices)
        ece += (len(indices) / total) * abs(bin_acc - bin_conf)

    return ece
```

- [ ] **Step 4: Implement dataset loaders**

Create `veritas/benchmarks/datasets.py`:

```python
"""Dataset loaders for benchmarking."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BenchmarkItem:
    """A single benchmark item."""

    claim: str
    expected_verdict: str
    domain: str = "general"
    source: str = ""


def load_truthfulqa() -> list[BenchmarkItem]:
    """Load TruthfulQA dataset.

    Requires: pip install datasets
    Returns list of claims with expected truthfulness labels.
    """
    try:
        from datasets import load_dataset
    except ImportError:
        raise ImportError(
            "TruthfulQA requires the 'datasets' package. "
            "Install with: pip install veritas-verify[benchmarks]"
        )

    ds = load_dataset("truthful_qa", "generation", split="validation")
    items = []
    for row in ds:
        items.append(
            BenchmarkItem(
                claim=row["question"],
                expected_verdict="VERIFIED",  # Will be compared against best_answer
                domain="general",
                source="truthfulqa",
            )
        )
    return items


def load_sample() -> list[BenchmarkItem]:
    """Load a small built-in sample dataset for quick testing."""
    return [
        BenchmarkItem(claim="Water boils at 100 degrees Celsius at sea level.", expected_verdict="VERIFIED", domain="scientific"),
        BenchmarkItem(claim="The Great Wall of China is visible from space.", expected_verdict="REFUTED", domain="general"),
        BenchmarkItem(claim="The first iPhone was released in 2006.", expected_verdict="REFUTED", domain="technical"),
        BenchmarkItem(claim="Python is a compiled language.", expected_verdict="REFUTED", domain="technical"),
        BenchmarkItem(claim="Light travels at approximately 300,000 km/s.", expected_verdict="PARTIAL", domain="scientific"),
        BenchmarkItem(claim="All birds can fly.", expected_verdict="REFUTED", domain="scientific"),
        BenchmarkItem(claim="The Earth is the third planet from the Sun.", expected_verdict="VERIFIED", domain="scientific"),
        BenchmarkItem(claim="JavaScript was created by Sun Microsystems.", expected_verdict="REFUTED", domain="technical"),
    ]
```

- [ ] **Step 5: Implement benchmark runner**

Create `veritas/benchmarks/runner.py`:

```python
"""Benchmark runner for evaluating Veritas against standard datasets."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field

from veritas.benchmarks.datasets import BenchmarkItem
from veritas.benchmarks.metrics import accuracy, expected_calibration_error
from veritas.core.config import Config
from veritas.core.result import Verdict, VerificationResult
from veritas.core.verify import verify


@dataclass
class BenchmarkResult:
    """Results from a benchmark run."""

    dataset: str
    total: int
    accuracy: float
    ece: float
    duration_seconds: float
    results: list[dict] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(
            {
                "dataset": self.dataset,
                "total": self.total,
                "accuracy": round(self.accuracy, 4),
                "ece": round(self.ece, 4),
                "duration_seconds": round(self.duration_seconds, 2),
                "results": self.results,
            },
            indent=2,
        )


async def run_benchmark(
    items: list[BenchmarkItem],
    dataset_name: str = "custom",
    config: Config | None = None,
) -> BenchmarkResult:
    """Run Veritas verification on a list of benchmark items."""
    start = time.monotonic()
    predictions: list[Verdict] = []
    labels: list[Verdict] = []
    confidences: list[float] = []
    correct: list[bool] = []
    per_item: list[dict] = []

    for item in items:
        try:
            result = await verify(
                claim=item.claim,
                domain=item.domain,
                config=config,
            )
            pred = result.verdict
            expected = Verdict(item.expected_verdict)

            predictions.append(pred)
            labels.append(expected)
            confidences.append(result.confidence)
            correct.append(pred == expected)

            per_item.append({
                "claim": item.claim,
                "expected": item.expected_verdict,
                "predicted": pred.value,
                "confidence": result.confidence,
                "correct": pred == expected,
                "summary": result.summary,
            })
        except Exception as e:
            per_item.append({
                "claim": item.claim,
                "expected": item.expected_verdict,
                "error": str(e),
            })

    duration = time.monotonic() - start

    return BenchmarkResult(
        dataset=dataset_name,
        total=len(items),
        accuracy=accuracy(predictions, labels),
        ece=expected_calibration_error(confidences, correct) if confidences else 0.0,
        duration_seconds=duration,
        results=per_item,
    )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_benchmarks.py -v`
Expected: All 6 tests PASS

- [ ] **Step 7: Commit**

```bash
git add veritas/benchmarks/ tests/test_benchmarks.py
git commit -m "feat: add benchmark harness with metrics and dataset loaders"
```

---

### Task 16: Wire Benchmark into CLI

**Files:**
- Modify: `veritas/cli/main.py`

- [ ] **Step 1: Add benchmark command to CLI**

Add this command to `veritas/cli/main.py` after the `shell` command:

```python
@app.command()
def benchmark(
    dataset: str = typer.Option("sample", "--dataset", "-d", help="Dataset: sample, truthfulqa"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    model_name: Optional[str] = typer.Option(None, "--model", "-m", help="LLM model to use"),
):
    """Run benchmarks against standard datasets."""
    from veritas.benchmarks.datasets import load_sample, load_truthfulqa
    from veritas.benchmarks.runner import run_benchmark

    loaders = {
        "sample": load_sample,
        "truthfulqa": load_truthfulqa,
    }

    if dataset not in loaders:
        console.print(f"[red]Unknown dataset: {dataset}. Available: {', '.join(loaders)}[/red]")
        raise typer.Exit(code=1)

    try:
        items = loaders[dataset]()
        console.print(f"Running benchmark on {len(items)} items from [bold]{dataset}[/bold]...")

        config = Config()
        if model_name:
            config.model = model_name

        result = asyncio.run(run_benchmark(items, dataset_name=dataset, config=config))

        console.print(f"\n[bold]Results:[/bold]")
        console.print(f"  Accuracy: {result.accuracy:.2%}")
        console.print(f"  ECE:      {result.ece:.4f}")
        console.print(f"  Duration: {result.duration_seconds:.1f}s")

        if output:
            with open(output, "w") as f:
                f.write(result.to_json())
            console.print(f"\nFull results written to {output}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)
```

- [ ] **Step 2: Test CLI benchmark help**

Run: `python -m pytest tests/test_cli.py -v`
Expected: All existing tests still PASS

- [ ] **Step 3: Commit**

```bash
git add veritas/cli/main.py
git commit -m "feat: add benchmark command to CLI"
```

---

### Task 17: Final Integration — Public API Exports and Full Test Suite

**Files:**
- Modify: `veritas/__init__.py` (already done in Task 12, verify it's correct)
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration test**

Create `tests/test_integration.py`:

```python
"""Integration tests for the full Veritas pipeline."""

import json

import pytest

from veritas import (
    Config,
    VerificationResult,
    Verdict,
    FailureMode,
    FailureModeType,
    AgentFinding,
    verify,
)
from veritas.orchestration.runner import VerificationRunner
from veritas.providers.base import SearchResult


class MockLLM:
    """Mock LLM that returns appropriate responses based on system prompt."""

    async def generate(self, prompt: str, system: str = "") -> str:
        if "logic" in system.lower():
            return json.dumps({
                "finding": "consistent",
                "confidence": 0.9,
                "details": [],
            })
        elif "source" in system.lower():
            return json.dumps({
                "finding": "contradiction",
                "confidence": 0.9,
                "details": [{"type": "factual_error", "description": "iPhone released 2007, not 2006"}],
                "sources": ["https://en.wikipedia.org/wiki/IPhone"],
                "reasoning": "Wikipedia confirms 2007 release",
            })
        elif "adversary" in system.lower():
            return json.dumps({
                "finding": "counterexample_found",
                "confidence": 0.85,
                "details": [{"type": "factual_error", "description": "2006 is incorrect"}],
                "reasoning": "Multiple sources confirm 2007",
            })
        elif "calibrat" in system.lower():
            return json.dumps({
                "finding": "overconfident",
                "confidence": 0.7,
                "details": [],
                "reasoning": "Claim states a specific date with certainty",
            })
        elif "synthe" in system.lower():
            return json.dumps({
                "verdict": "REFUTED",
                "confidence": 0.91,
                "summary": "The first iPhone was released June 2007, not 2006.",
                "failure_modes": [
                    {"type": "factual_error", "detail": "Wrong release year", "agent": "source_verifier"}
                ],
                "contested": False,
            })
        return json.dumps({"finding": "consistent", "confidence": 0.5, "details": []})


class MockSearch:
    async def search(self, query: str, num_results: int = 5) -> list[SearchResult]:
        return [SearchResult(
            title="iPhone - Wikipedia",
            url="https://en.wikipedia.org/wiki/IPhone",
            snippet="The iPhone was first released on June 29, 2007.",
        )]


@pytest.mark.asyncio
async def test_full_pipeline_refuted():
    """Test the complete verification pipeline with a known-false claim."""
    runner = VerificationRunner(
        llm_provider=MockLLM(),
        search_provider=MockSearch(),
        config=Config(),
    )
    result = await runner.run(
        claim="The first iPhone was released in 2006",
        context=None,
        domain="technical",
        references=[],
    )

    assert isinstance(result, VerificationResult)
    assert result.verdict == Verdict.REFUTED
    assert result.confidence > 0.8
    assert len(result.evidence) == 4
    assert len(result.failure_modes) == 1
    assert result.failure_modes[0].type == FailureModeType.FACTUAL_ERROR
    assert "2007" in result.summary

    # Test layered access
    text = str(result)
    assert "REFUTED" in text

    d = result.to_dict()
    assert d["verdict"] == "REFUTED"
    json.dumps(d)  # Must be serializable

    report = result.report()
    assert "factual_error" in report
    assert "source_verifier" in report


@pytest.mark.asyncio
async def test_full_pipeline_verified():
    """Test pipeline with a true claim."""

    class VerifiedMockLLM:
        async def generate(self, prompt: str, system: str = "") -> str:
            if "synthe" in system.lower():
                return json.dumps({
                    "verdict": "VERIFIED",
                    "confidence": 0.95,
                    "summary": "Claim is accurate.",
                    "failure_modes": [],
                    "contested": False,
                })
            return json.dumps({
                "finding": "consistent" if "logic" in system.lower() else
                           "supported" if "source" in system.lower() else
                           "no_counterexample" if "adversary" in system.lower() else
                           "well_calibrated",
                "confidence": 0.9,
                "details": [],
                "sources": [],
                "reasoning": "",
            })

    runner = VerificationRunner(
        llm_provider=VerifiedMockLLM(),
        search_provider=MockSearch(),
        config=Config(),
    )
    result = await runner.run(
        claim="Water boils at 100 degrees Celsius at sea level",
        context=None,
        domain="scientific",
        references=[],
    )

    assert result.verdict == Verdict.VERIFIED
    assert result.confidence > 0.9
    assert len(result.failure_modes) == 0
```

- [ ] **Step 2: Run integration tests**

Run: `python -m pytest tests/test_integration.py -v`
Expected: All 2 tests PASS

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest -v`
Expected: ALL tests PASS (should be ~50+ tests total)

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "feat: add integration tests for full verification pipeline"
```

---

### Task 18: Add .superpowers to .gitignore

**Files:**
- Modify or create: `.gitignore`

- [ ] **Step 1: Create .gitignore**

```
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.eggs/

# Env
.env
.venv/

# IDE
.idea/
.vscode/
*.swp

# Superpowers brainstorming sessions
.superpowers/

# Overstory runtime
.overstory/worktrees/
.overstory/logs/
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: add .gitignore"
```
