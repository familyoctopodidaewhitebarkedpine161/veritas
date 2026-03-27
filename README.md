# Veritas

Adversarial parallel verification of AI outputs. No ground truth required. Model-agnostic interface.

```python
from veritas import verify

result = await verify("The first iPhone was released in 2006")
# REFUTED (0.98) — The first iPhone was released June 2007, not 2006.
```

## What It Does

Veritas runs 5 independent AI agents in parallel to verify any claim:

- **Logic Verifier** — checks internal consistency and reasoning
- **Source Verifier** — cross-references against web search and provided documents
- **Adversary** — actively tries to disprove the claim with counterexamples
- **Calibration Agent** — audits whether confidence matches evidence strength
- **Synthesiser** — aggregates all findings into a structured verdict

Agents run in **isolation** (no shared context) to prevent conformity bias. Findings merge only at synthesis.

## Install

```bash
# From private repo
pip install git+ssh://git@github.com/yourorg/veritas.git

# Required env var
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Use

### Python

```python
from veritas import verify, Verdict

result = await verify(
    claim="Your AI output here",
    context="Optional source documents",
    domain="technical",  # technical | scientific | medical | legal | general
)

result.verdict          # Verdict.VERIFIED / PARTIAL / UNCERTAIN / DISPUTED / REFUTED
result.confidence       # 0.0 - 1.0
result.failure_modes    # [FailureMode(type="factual_error", detail="...")]
result.report()         # Full markdown report
```

### CLI

```bash
veritas check "The Great Wall is visible from space"
veritas check "..." --verbose --json
cat output.txt | veritas check --stdin
veritas shell
```

### Claude Code Skill

```
/verify The RAG pipeline says our refund window is 90 days
```

### MCP Server

Add to `.mcp.json`:
```json
{
  "mcpServers": {
    "veritas": {
      "command": "python",
      "args": ["-m", "veritas.mcp_server"],
      "env": { "ANTHROPIC_API_KEY": "sk-ant-..." }
    }
  }
}
```

## Verdicts

| Verdict | Meaning |
|---------|---------|
| VERIFIED | Evidence supports the claim |
| PARTIAL | Some parts correct, some not |
| UNCERTAIN | Insufficient evidence |
| DISPUTED | Conflicting evidence |
| REFUTED | Evidence contradicts the claim |

## Failure Modes

When something is wrong, Veritas tells you WHY:

| Type | Meaning |
|------|---------|
| `factual_error` | A fact is wrong |
| `logical_inconsistency` | Reasoning contradicts itself |
| `unsupported_inference` | Claim exceeds the evidence |
| `temporal_error` | Information is outdated |
| `scope_error` | Overgeneralization |
| `source_conflict` | Sources disagree |

## Integration

Same interface for every architecture:

```python
# RAG
result = await verify(claim=rag_answer, context="\n".join(retrieved_docs))

# Agentic pipeline
result = await verify(claim=agent_output, domain="technical")
if result.verdict == Verdict.REFUTED:
    agent.retry(feedback=result.summary)

# Batch evaluation
results = [await verify(claim=o) for o in model_outputs]
```

See [docs/USAGE.md](docs/USAGE.md) for detailed patterns (CI/CD, production middleware, etc.)

## Benchmarks

```bash
veritas benchmark --dataset sample
veritas compare --dataset sample  # isolation vs debate comparison
```

## Architecture

- **Python 3.10+** with Pydantic, Anthropic SDK, Typer
- **Claude Sonnet 4.6** as default LLM (pluggable provider interface)
- **Overstory** integration for true git-worktree agent isolation
- **75 tests** passing

## Docs

- [Usage Guide](docs/USAGE.md) — integration patterns for every architecture
- [Design Spec](docs/superpowers/specs/2026-03-27-veritas-design.md) — full technical spec
- [Research](docs/research/landscape-analysis.md) — landscape analysis and novel positioning
- [Benchmark Results](docs/research/benchmark-results.md) — isolation vs debate comparison
- [Methodology](docs/research/benchmarks/methodology.md) — evaluation design and rationale
