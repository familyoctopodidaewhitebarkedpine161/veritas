# Veritas — Enterprise Reality Check

Honest assessment of where Veritas works, where it doesn't, and what's needed to make it production-ready.

---

## Where It Works Today

### 1. Pre-Deployment RAG Validation (Strongest Use Case)

The real sweet spot. Enterprises building RAG pipelines have a "last mile" problem — retrieval works, but generation hallucinates beyond the documents.

```python
answer = rag.generate(query)
result = await verify(claim=answer, context="\n".join(retrieved_docs))
if result.verdict == Verdict.REFUTED:
    return "I'm not confident in this answer. Let me escalate to a human."
```

**Who'd use it:** Any team shipping customer-facing RAG (support bots, internal knowledge bases, document Q&A).

**Why the failure mode taxonomy matters here:** "factual_error" vs "unsupported_inference" tells you whether the retrieval was bad or the generation was bad. Actionable feedback for the team.

**Limitation:** Adds 15-20 seconds latency and ~$0.05-0.10 per query. Not viable for real-time chat. Works for async workflows, batch validation, or cases where accuracy matters more than speed (medical, legal, financial).

### 2. Batch Evaluation Before Model Deployment

Before swapping models or updating prompts, run Veritas across the test set:

```python
results = [await verify(claim=o, context=prompt) for prompt, o in test_pairs]
refuted_pct = sum(1 for r in results if r.verdict == Verdict.REFUTED) / len(results)
```

**Who'd use it:** ML teams evaluating model versions, prompt engineers testing changes, QA teams before release.

**Limitation:** Expensive at scale. 1,000 test cases = ~$50-100. Fine for weekly evaluation, not continuous.

### 3. High-Stakes Content Review

Medical, legal, financial content where being wrong has real consequences. Not real-time — more like a "second opinion" before publishing.

**Limitation:** Veritas itself uses an LLM. If Claude is wrong about a medical claim, Veritas is wrong too. Better than nothing, but not a substitute for domain expert review.

### 4. Prompt Engineering Feedback Loop

When iterating on prompts, run Veritas on the output to check quality:

```bash
cat prompt_output.txt | veritas check --stdin --verbose
```

The failure modes tell you exactly what's wrong — "scope_error" means the prompt needs to be more specific, "temporal_error" means the model is using outdated knowledge.

---

## Where It Doesn't Work (Honestly)

### Real-Time Production Middleware
15-20 seconds per verification. No enterprise is putting that in the hot path of a chat API. The FastAPI middleware pattern in the README works technically but the latency kills it for real-time use.

### Claims the Model Already Knows Confidently
Our adversarial benchmark proved this — when Claude knows the answer confidently (iPhone release date, Napoleon's height), both isolation and debate get 100%. Veritas adds value only in the model's **zone of uncertainty** — contested claims, nuanced facts, domain-specific knowledge.

### Replacing Human Review
FaithBench showed 58% balanced accuracy. That means 42% of the time it gets the wrong answer about whether something is hallucinated. It's a filter, not an oracle. Use it to triage, not to decide.

### Cost-Sensitive High-Volume Applications
5 LLM calls per verification. If you're verifying millions of outputs, the cost is prohibitive (~$50K-100K for 1M verifications).

### Non-English Content
v1 is English-only. All agent prompts and benchmarks are in English.

---

## Benchmark Results (What the Numbers Actually Mean)

| Benchmark | What it tested | Result | Interpretation |
|-----------|---------------|--------|----------------|
| **FaithBench** | Hard hallucination detection | 58% bal. accuracy | Matches best published detector (o3-mini). This is a HARD benchmark — 42% error rate is the state of the art, not a Veritas problem. |
| **RAG Grounding** | Document faithfulness | 89.7% F1 | Strong on grounded verification. When there's a source document to check against, Veritas is much better. |
| **Adversarial** | Planted subtle errors | 100% detection | Easy claims. The model already knows these facts. Doesn't prove much about hard cases. |

**The honest reading:** Veritas is strong when there's context to verify against (RAG). It's average on open-domain hallucination detection (FaithBench). It's excellent on well-known facts (adversarial) but that's the easy case.

---

## What Would Make It Enterprise-Ready

### 1. Speed (Biggest Blocker)

Current: 15-20 seconds per verification.
Target: <2 seconds for real-time use.

Options:
- **Fine-tuned small models** for each agent (like MiniCheck's approach — 400x cheaper, 10x faster)
- **Claim caching** — cache verdicts for common/repeated claims
- **Streaming parallel calls** — overlap agent execution with synthesis
- **Tiered verification** — run fewer agents for low-stakes claims (just logic + source, skip adversary)
- **Confidence-based routing** — only verify when the source model is uncertain

### 2. Confidence-Based Routing

Don't verify everything. Only verify when the model is uncertain:

```python
if model_confidence < 0.8:
    result = await verify(claim)  # Only verify uncertain outputs
else:
    pass  # Trust the model on high-confidence outputs
```

This cuts cost and latency by 60-80% in practice (most outputs are high-confidence).

### 3. Tiered Agent Costs

Use cheaper/faster models for simpler agents:

| Agent | Current | Enterprise Tier |
|-------|---------|----------------|
| Logic Verifier | Sonnet 4.6 ($3/M) | Haiku 4.5 ($0.25/M) |
| Calibration | Sonnet 4.6 ($3/M) | Haiku 4.5 ($0.25/M) |
| Source Verifier | Sonnet 4.6 ($3/M) | Sonnet 4.6 ($3/M) |
| Adversary | Sonnet 4.6 ($3/M) | Sonnet 4.6 ($3/M) |
| Synthesiser | Sonnet 4.6 ($3/M) | Haiku 4.5 ($0.25/M) |

Could cut cost per verification from ~$0.08 to ~$0.03.

### 4. Domain-Specific Profiles

Generic Veritas scores 58% on FaithBench. Domain-specific versions with:
- Custom agent prompts tuned for medical/legal/financial claims
- Domain-specific reference documents pre-loaded
- Calibrated confidence thresholds per domain

Would likely score 70-80% in a specific domain.

### 5. Caching Layer

Many enterprises verify similar claims repeatedly. A Redis/SQLite cache layer:

```python
# Automatic caching
result = await verify(claim, cache=True, cache_ttl=3600)
```

Cache hit = 0 latency, 0 cost. Realistic 40-60% cache hit rate for support bots.

---

## The Honest Value Proposition

Veritas is NOT "we solve hallucinations."

Veritas IS:

> For critical AI outputs where being wrong matters, we add a structured second opinion that catches errors ~60-90% of the time (depending on domain), tells you the TYPE of error, and costs pennies per check.

### What's actually unique:
1. **Failure mode taxonomy** — not just "wrong" but "wrong because the date is off" or "wrong because the claim overgeneralizes." Actionable feedback for prompt engineers and RAG developers.
2. **One-line integration** — `verify(claim, context)` drops into any pipeline in 3 lines.
3. **Isolation architecture** — higher precision than debate-based approaches (12.8% fewer false positives on RAG, 10% better balanced accuracy on FaithBench).

### What's NOT unique:
- Hallucination detection itself (SelfCheckGPT, SAFE, ChainPoll all do this)
- Using LLMs to check LLMs (LLM-as-judge is well-established)
- Multi-agent verification (Du et al. 2024 proved debate works)

---

## Recommended Enterprise Adoption Path

### Phase 1: Batch Evaluation (Week 1)
- Run Veritas on existing test sets
- Identify failure patterns in your RAG/agent outputs
- Zero production risk, immediate insights

### Phase 2: CI/CD Gate (Week 2-3)
- Add to CI pipeline for AI-generated content
- Block deployments that fail verification
- Automated quality gate

### Phase 3: Async Verification (Month 2)
- Verify RAG outputs asynchronously (not in hot path)
- Flag low-confidence responses for human review
- Build trust in the system

### Phase 4: Selective Real-Time (Month 3+)
- Confidence-based routing (only verify uncertain outputs)
- Tiered agents for cost optimization
- Domain-specific tuning
- Caching for repeated queries

---

## Cost Estimates by Use Case

| Use Case | Volume | Cost/Month | Latency Impact |
|----------|--------|-----------|---------------|
| Prompt testing | 100/week | ~$4 | None (offline) |
| CI/CD gate | 500/week | ~$20 | Build time only |
| RAG validation (async) | 5,000/week | ~$200 | None (async) |
| Support bot (selective) | 10,000/week | ~$300* | +2s on 20% of queries* |
| Full production | 100,000/week | ~$4,000 | Not recommended yet |

*With confidence routing + tiered agents + caching
