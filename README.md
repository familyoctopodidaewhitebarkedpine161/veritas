# Veritas

**Adversarial parallel verification of AI outputs.**

No ground truth required. Model-agnostic interface. pip-installable.

```python
from veritas import verify

result = await verify("The first iPhone was released in 2006")
# REFUTED (0.98) — The first iPhone was released June 2007, not 2006.
```

---

## Table of Contents

- [How It Works](#how-it-works)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
  - [Python Library](#python-library)
  - [CLI](#cli)
  - [Claude Code Skill](#claude-code-skill)
  - [MCP Server](#mcp-server)
- [Integration Patterns](#integration-patterns)
- [Verdicts & Failure Modes](#verdicts--failure-modes)
- [Architecture](#architecture)
- [Benchmark Results](#benchmark-results)
- [Configuration](#configuration)
- [Links & Docs](#links--docs)

---

## How It Works

Veritas runs 5 independent AI agents **in parallel with zero shared context** to verify any claim. This isolation prevents conformity bias — agents can't influence each other's findings.

```
                        ┌─────────────────┐
                        │  claim + context │
                        └────────┬────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                   │
              ▼                  ▼                   ▼
   ┌──────────────────┐ ┌──────────────┐ ┌──────────────────┐
   │  Logic Verifier  │ │   Source     │ │    Adversary     │
   │                  │ │  Verifier   │ │                  │
   │ Checks internal  │ │ Cross-refs  │ │ Constructs       │
   │ consistency &    │ │ against web │ │ counterexamples  │
   │ reasoning        │ │ search &    │ │ & edge cases     │
   │                  │ │ documents   │ │                  │
   └────────┬─────────┘ └──────┬──────┘ └────────┬─────────┘
            │                  │                  │
            │    ┌─────────────────────┐          │
            │    │ Calibration Agent   │          │
            │    │                     │          │
            │    │ Audits confidence   │          │
            │    │ vs evidence         │          │
            │    │ alignment           │          │
            │    └──────────┬──────────┘          │
            │               │                     │
            └───────────────┼─────────────────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │    Synthesiser      │
                 │                     │
                 │ Aggregates all      │
                 │ findings into       │
                 │ structured verdict  │
                 └──────────┬──────────┘
                            │
                   ┌────────┴────────┐
                   │                 │
                   ▼                 ▼
            No conflicts?      Conflicts?
                   │                 │
                   ▼                 ▼
              Return verdict   Challenge Round
                               (Adversary re-examines
                                contested points)
                                     │
                                     ▼
                               Final verdict
```

**Key design principle:** Agents run in separate execution contexts with NO shared state. This prevents the conformity bias documented in shared-context debate systems ([Science Advances 2025](https://www.science.org/doi/10.1126/sciadv.adu9368), [Cross-Context Verification 2026](https://arxiv.org/abs/2603.21454)).

---

## Quick Start

```bash
# Install
pip install git+ssh://git@github.com/yourorg/veritas.git

# Set API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Verify a claim
veritas check "The Great Wall of China is visible from space"
# REFUTED (0.95) — This is a common misconception...
```

---

## Installation

### From Private Git Repo

```bash
# SSH (recommended)
pip install git+ssh://git@github.com/yourorg/veritas.git

# HTTPS with token
pip install git+https://<token>@github.com/yourorg/veritas.git

# In requirements.txt
git+ssh://git@github.com/yourorg/veritas.git@main#egg=veritas-verify
```

### Environment Variables

```bash
# Required
export ANTHROPIC_API_KEY="sk-ant-..."

# Optional — improves source verification with live web search
export BRAVE_API_KEY="..."       # Brave Search API
# or
export TAVILY_API_KEY="..."      # Tavily Search API

# Optional — override default model
export VERITAS_MODEL="claude-sonnet-4-6"
```

### Verify Installation

```bash
veritas --help
```

---

## Usage

### Python Library

The core interface — same three lines for every use case:

```python
from veritas import verify, Verdict

result = await verify(
    claim="Your AI output or claim to verify",
    context="Optional: source documents, retrieved context, system prompt",
    domain="technical",  # technical | scientific | medical | legal | general
)
```

#### Reading Results

```python
# Quick summary
print(result)
# REFUTED (0.95) — The claim contains a factual error about the release date.

# Structured access
result.verdict          # Verdict.REFUTED
result.confidence       # 0.95
result.summary          # "The claim contains a factual error..."
result.failure_modes    # [FailureMode(type="factual_error", detail="...", agent="source_verifier")]
result.evidence         # [AgentFinding(...), ...] — one per agent

# Full output
result.report()         # Markdown report with all evidence
result.to_dict()        # JSON-serializable dict
```

### CLI

```bash
# Inline verification
veritas check "The Earth is the largest planet in the solar system"

# Verbose — show full evidence chain from all agents
veritas check "..." --verbose

# JSON output — pipe to jq or save to file
veritas check "..." --json

# Read from stdin — verify output from another command
cat ai_output.txt | veritas check --stdin

# With domain hint and reference document
veritas check "..." --domain medical --ref guidelines.pdf

# Interactive shell — verify claims conversationally
veritas shell
```

**Shell commands:**
```
$ veritas shell
Veritas v0.1.0 — Type a claim to verify. /help for commands.

veritas> Humans only use 10% of their brains
REFUTED (0.99) — Neuroscience shows we use virtually all of our brain.

veritas> /verbose
Verbose mode on.

veritas> /quit
```

### Claude Code Skill

Drop the `skills/verify/` folder into your project or `~/.claude/` directory:

```
/verify The RAG pipeline says our refund window is 90 days
```

Returns verdict, confidence, failure modes, and evidence chain inline in your coding session.

### MCP Server

For any MCP-compatible AI tool (Claude Desktop, Cursor, Windsurf, etc.):

Add to `.mcp.json` in your project root:
```json
{
  "mcpServers": {
    "veritas": {
      "command": "python",
      "args": ["-m", "veritas.mcp_server"],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-..."
      }
    }
  }
}
```

The AI tool auto-discovers `verify` as a callable tool. No code changes needed.

---

## Integration Patterns

The interface is **identical** regardless of architecture. Only `claim` and `context` change.

### RAG Applications

```python
# Verify RAG output against retrieved documents
answer = rag_pipeline.generate(query)
docs = rag_pipeline.get_retrieved_documents(query)

result = await verify(
    claim=answer,
    context="\n\n".join(docs),
)

if result.verdict == Verdict.REFUTED:
    print(f"Hallucination detected: {result.failure_modes[0].detail}")
```

Works with LangChain, LlamaIndex, Haystack, or any RAG framework.

### Agentic Pipelines

```python
# Gate agent actions behind verification
agent_output = agent.run(task)

result = await verify(claim=agent_output, domain="technical")

if result.verdict in (Verdict.VERIFIED, Verdict.PARTIAL):
    execute(agent_output)
elif result.verdict == Verdict.REFUTED:
    agent.retry(task, feedback=result.summary)
else:
    flag_for_human_review(agent_output, result)
```

Works with CrewAI, AutoGen, LangGraph, or any agent framework.

### CI/CD Quality Gate

```yaml
# .github/workflows/verify.yml
- name: Verify AI content
  run: |
    for file in $(git diff --name-only origin/main -- docs/); do
      veritas check "$(cat $file)" --domain technical --json
    done
```

### Production Middleware

```python
# FastAPI — verify before serving to users
@app.post("/api/ask")
async def ask(query: str):
    response = model.generate(query)
    result = await verify(claim=response, context=query)

    if result.verdict == Verdict.REFUTED:
        return {"error": result.summary}, 422

    return {"answer": response, "confidence": result.confidence}
```

### Batch Evaluation

```python
# Evaluate a model's outputs before deployment
results = [await verify(claim=o) for o in model_outputs]
accuracy = sum(1 for r in results if r.verdict == Verdict.VERIFIED) / len(results)
print(f"Model accuracy: {accuracy:.0%}")
```

See [docs/USAGE.md](docs/USAGE.md) for the complete pattern reference (15+ examples).

---

## Verdicts & Failure Modes

### Verdicts

| Verdict | Meaning | What to do |
|---------|---------|------------|
| `VERIFIED` | All agents agree, evidence supports the claim | Safe to use |
| `PARTIAL` | Some parts correct, some not | Review failure modes for specifics |
| `UNCERTAIN` | Not enough evidence either way | Get more context or human review |
| `DISPUTED` | Agents disagree, couldn't resolve | Flag for human review |
| `REFUTED` | Evidence actively contradicts the claim | Do not use — check failure modes |

### Failure Modes

When something is wrong, Veritas classifies the TYPE of error — not just "wrong":

| Type | What It Means | Example |
|------|--------------|---------|
| `factual_error` | A fact is incorrect | "Released in 2006" when it was 2007 |
| `logical_inconsistency` | The reasoning contradicts itself | Premises don't support the conclusion |
| `unsupported_inference` | Claim goes beyond the evidence | Correlation stated as causation |
| `temporal_error` | Information is outdated | Using 2020 data for a 2026 claim |
| `scope_error` | Too broad or too narrow | "All X do Y" when only some do |
| `source_conflict` | Sources disagree with each other | Two credible sources give different answers |

This failure taxonomy is unique to Veritas — no other verification tool classifies error types.

---

## Architecture

```
veritas/
  __init__.py              # Public API: verify(), Verdict, VerificationResult
  core/
    verify.py              # Main verify() entry point
    result.py              # Data models (Verdict, FailureMode, AgentFinding, etc.)
    config.py              # Configuration with env var support
  agents/
    base.py                # Abstract base agent
    logic.py               # Logic Verifier — internal consistency
    source.py              # Source Verifier — web search cross-reference
    adversary.py           # Adversary — counterexample construction
    calibration.py         # Calibration Agent — confidence audit
    synthesiser.py         # Synthesiser — verdict aggregation
  orchestration/
    runner.py              # Parallel async runner (isolation mode)
    debate_runner.py       # Sequential shared-context runner (debate mode)
    overstory_runner.py    # Git-worktree isolation via Overstory
    challenge.py           # Challenge round for contested claims
    messaging.py           # Message bus abstraction
  providers/
    base.py                # LLMProvider + SearchProvider protocols
    claude.py              # Claude/Anthropic implementation
    search.py              # Brave + Tavily search providers
  cli/
    main.py                # CLI (check, shell, benchmark, compare)
    shell.py               # Interactive REPL
  mcp_server.py            # MCP server for AI tool integration
  benchmarks/              # Evaluation harnesses
```

### Key Design Decisions

| Decision | Why |
|----------|-----|
| **Agents run in isolation** | Prevents conformity bias (Science Advances 2025). Shared context causes agents to reinforce errors instead of catching them. |
| **Hybrid topology** | Fast path (no conflicts) returns immediately. Challenge round only triggers when agents disagree. |
| **Dedicated adversary** | Not debate — structured red-teaming. The adversary's only job is to disprove. |
| **Dedicated calibration agent** | LLMs are systematically overconfident (ICLR 2025). A separate agent audits confidence-evidence alignment. |
| **Claude-first, pluggable** | Ships with Claude via Anthropic SDK. Provider protocol makes adding OpenAI/Ollama trivial. |

### Tech Stack

- **Python 3.10+** — async/await, type hints
- **Pydantic v2** — structured data models
- **Anthropic SDK** — Claude API integration
- **Typer + Rich** — CLI with color output
- **httpx** — async HTTP for search providers
- **Overstory** — git-worktree agent isolation (optional)
- **72 tests** — full coverage with pytest

---

## Benchmark Results

Veritas was evaluated across 3 benchmarks comparing **isolation mode** (agents verify independently) vs **debate mode** (agents share context, standard multi-agent approach).

### FaithBench (NAACL 2025 — Hard Hallucination Detection)

The standard benchmark for hallucination detectors. Best published detector (o3-mini) scores 58% balanced accuracy.

| Metric | Isolation | Debate | Delta |
|--------|-----------|--------|-------|
| **Balanced Accuracy** | **58.0%** | 48.0% | **+10.0%** |
| Precision | **60.0%** | 48.4% | +11.6% |
| F1 | 53.3% | 53.6% | Tied |
| Speed | 805s | 1,940s | **2.4x faster** |

Veritas isolation **matches o3-mini's published balanced accuracy** while providing structured failure modes and evidence chains that single-model detectors don't offer.

### RAG Grounding (Document Faithfulness)

Tests whether Veritas catches unfaithful RAG outputs — answers that hallucinate facts not in the source documents.

| Metric | Isolation | Debate | Delta |
|--------|-----------|--------|-------|
| **F1** | **89.7%** | 81.3% | **+8.4%** |
| Precision | **81.3%** | 68.4% | **+12.8%** |
| Recall | 100% | 100% | Tied |
| False Positives | 3 | 6 | **Half the false alarms** |
| Speed | 483s | 1,229s | **2.5x faster** |

Both modes catch every hallucination (100% recall), but **debate wrongly flags twice as many faithful answers**. Shared context makes agents overly suspicious.

### Adversarial Claims (Conformity Bias Test)

50 claims with planted subtle errors — off-by-one dates, overgeneralizations, confident misconceptions.

| Metric | Isolation | Debate | Delta |
|--------|-----------|--------|-------|
| Detection Rate | 100% | 100% | Tied |
| Calibration (ECE) | **0.029** | 0.037 | Isolation |
| Speed | 244s | 648s | **2.7x faster** |

### Summary

| What We Proved | Evidence |
|---------------|----------|
| Isolation is **2.4-2.7x faster** than debate | Consistent across all 3 benchmarks |
| Isolation has **higher precision** | +12.8% on RAG, +11.6% on FaithBench |
| Isolation has **fewer false positives** | Half the false alarms on RAG grounding |
| Isolation matches **SOTA balanced accuracy** | 58% on FaithBench (= o3-mini) |
| Debate over-flags faithful content | Shared context makes agents overly suspicious |

> Full benchmark methodology, datasets, and raw results available on the [`research` branch](../../tree/research).

---

## Configuration

### Python

```python
from veritas import Config, verify

config = Config(
    model="claude-sonnet-4-6",       # LLM model
    search_provider="brave",          # "brave" or "tavily"
    challenge_round=True,             # Challenge round for conflicts
    timeout_seconds=30,               # Per-agent timeout
    max_search_results=5,             # Web search results per query
)

result = await verify("claim", config=config)
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `BRAVE_API_KEY` | No | Enables web search (Brave) |
| `TAVILY_API_KEY` | No | Enables web search (Tavily) |
| `VERITAS_MODEL` | No | Override default model |
| `VERITAS_SEARCH_PROVIDER` | No | Default search provider |

---

## Performance

| Metric | Value |
|--------|-------|
| **Agents per verification** | 5 (4 parallel + 1 synthesiser) |
| **Time per claim (isolation)** | ~15-20 seconds |
| **Time per claim (debate)** | ~40-45 seconds |
| **API calls per verification** | ~5 |
| **Cost per verification** | ~$0.05-0.10 (Sonnet 4.6) |
| **Works without search key** | Yes (LLM knowledge only) |

---

## Links & Docs

### Usage & Integration
- [Usage Guide](docs/USAGE.md) — complete integration patterns for RAG, agentic, CI/CD, production, batch eval

### Research & Benchmarks
> Available on the [`research` branch](../../tree/research)

- [Landscape Analysis](../../blob/research/docs/research/landscape-analysis.md) — comprehensive review of 40+ existing tools and the gaps Veritas fills
- [Design Spec](../../blob/research/docs/superpowers/specs/2026-03-27-veritas-design.md) — full technical specification
- [Evaluation Methodology](../../blob/research/docs/research/benchmarks/methodology.md) — why each benchmark, dataset design, metrics
- [Benchmark Results](../../blob/research/docs/research/benchmark-results.md) — isolation vs debate comparison data
- [Adversarial Dataset](../../blob/research/docs/research/benchmarks/adversarial-dataset.md) — 50-claim adversarial robustness dataset

### Novel Contributions

1. **Isolation-divergent verification** — first system enforcing zero shared context between verification agents
2. **Failure mode taxonomy** — classifies HOW claims fail (6 types), not just binary true/false
3. **Calibration-as-verification** — dedicated agent auditing confidence vs evidence alignment
4. **Structural adversary** — dedicated counterexample constructor, not debate-style argumentation
5. **Production-ready packaging** — pip-installable library, CLI, Claude Code skill, MCP server

### Key References

- Du et al. "Improving Factuality through Multiagent Debate" (ICML 2024) — [arxiv](https://arxiv.org/abs/2305.14325)
- "Emergent social conventions and collective bias in LLM populations" (Science Advances 2025) — [paper](https://www.science.org/doi/10.1126/sciadv.adu9368)
- "Cross-Context Verification" (2026) — [arxiv](https://arxiv.org/abs/2603.21454)
- FaithBench (NAACL 2025) — [github](https://github.com/vectara/FaithBench)
- Farquhar et al. "Semantic Entropy" (Nature 2024) — [paper](https://www.nature.com/articles/s41586-024-07421-0)

---

## License

MIT
