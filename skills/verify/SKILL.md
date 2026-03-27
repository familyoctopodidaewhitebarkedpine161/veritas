---
name: verify
description: This skill should be used when the user asks to "verify a claim", "fact-check this", "check if this is true", "verify AI output", "check for hallucinations", "validate this response", "is this accurate", or wants to verify any AI-generated content, RAG output, agentic pipeline result, or factual claim before deployment or sharing.
---

# Verify — Adversarial Claim Verification

Multi-agent verification of any claim, AI output, or generated content. Returns a structured verdict with evidence chain and failure mode classification.

## Quick Start

To verify a claim inline:

```python
from veritas import verify
result = await verify("The claim to check", domain="technical")
```

Or via CLI:
```bash
veritas check "The claim to check"
```

## When To Use

- Before deploying RAG pipeline responses to production
- To validate agentic pipeline outputs before acting on them
- To fact-check AI-generated content before publishing
- To verify claims in code reviews, documentation, or reports
- As an automated quality gate in CI/CD for AI systems

## Core Interface

The interface is the SAME regardless of what is being verified:

```python
result = await verify(
    claim="<the text to verify>",
    context="<optional: surrounding context, source document, or system prompt>",
    domain="<optional: technical | scientific | medical | legal | general>",
    references=["<optional: paths to reference docs>"],
)
```

### Reading Results

```python
print(result)                # REFUTED (0.95) — One-line summary
result.verdict               # Verdict.REFUTED
result.confidence            # 0.95
result.failure_modes         # [FailureMode(type="factual_error", ...)]
result.evidence              # [AgentFinding(...), ...]
result.report()              # Full markdown report
```

### Verdicts

| Verdict | Meaning |
|---------|---------|
| VERIFIED | Evidence supports the claim |
| PARTIAL | Some parts verified, others not |
| UNCERTAIN | Insufficient evidence either way |
| DISPUTED | Conflicting evidence, unresolved |
| REFUTED | Evidence contradicts the claim |

### Failure Modes

When a claim fails, Veritas tells you WHY:
- `factual_error` — wrong fact
- `logical_inconsistency` — self-contradiction
- `unsupported_inference` — claim exceeds evidence
- `temporal_error` — outdated information
- `scope_error` — overgeneralization
- `source_conflict` — sources disagree

## Usage Patterns

Detailed patterns for different architectures are in `references/usage-patterns.md`. The key principle: **the interface is always the same** — only `claim` and `context` change.

### RAG Verification
```python
claim = rag_pipeline.generate(query)
context = "\n".join(retrieved_documents)
result = await verify(claim=claim, context=context)
```

### Agentic Pipeline Gate
```python
agent_output = agent.run(task)
result = await verify(claim=agent_output, domain="technical")
if result.verdict == Verdict.REFUTED:
    agent.retry(task, feedback=result.summary)
```

### Batch Verification
```python
from veritas import verify
outputs = [agent.run(task) for task in tasks]
results = [await verify(claim=o) for o in outputs]
flagged = [r for r in results if r.verdict in (Verdict.REFUTED, Verdict.DISPUTED)]
```

## Environment Setup

```bash
# Required
export ANTHROPIC_API_KEY="sk-ant-..."

# Optional (improves source verification)
export BRAVE_API_KEY="..."  # or TAVILY_API_KEY
```

## Additional Resources

### Reference Files
- **`references/usage-patterns.md`** — Detailed integration patterns for RAG, agentic, skills, CI/CD, and production deployments
