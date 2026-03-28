# Veritas — Honest Assessment (March 2026)

Fresh research as of today. No sugar-coating.

---

## The Bad News First: We Have Direct Competitors We Didn't Know About

### RAG Diagnostics — RAGVUE and RAG-X exist

**[RAGVUE](https://arxiv.org/abs/2601.04196)** (January 2026) does what our `diagnose_rag()` does:
- Claim-level faithfulness with strict evidence matching
- Separate retrieval quality, answer relevance, completeness scores
- Structured explanations for each metric
- Python API + CLI + Streamlit dashboard
- Open source on [GitHub](https://github.com/KeerthanaMurugaraj/RAGVue)
- Reference-free (no ground truth needed)
- **Explicitly claims to catch failures that RAGAS overlooks**

**[RAG-X](https://arxiv.org/abs/2603.03541)** (March 2026) also does RAG failure diagnosis:
- Evaluates retriever and generator independently
- Diagnoses whether error is from retrieval or generation
- Focused on medical QA but generalizable

**[RAGXplain](https://arxiv.org/html/2505.13538v2)** translates performance metrics into actionable guidance — similar to our "fix_suggestion."

**What this means:** Our claim that "nobody does RAG root-cause diagnosis" is wrong. At least 3 academic tools now do some version of this. RAGVUE in particular is very close to what we built.

### Pre-Action Verification — Superagent exists

**[Superagent](https://www.helpnetsecurity.com/2025/12/29/superagent-framework-guardrails-agentic-ai/)** (December 2025) has a "Safety Agent" that:
- Evaluates agent actions BEFORE execution
- Applies policies for data sensitivity, tool usage, operational boundaries
- Blocks, modifies, or logs actions that violate rules
- Open source
- Declarative policy engine

**What this means:** Our claim that "nobody has a pre-execution verification tool" is wrong. Superagent does this, though with a policy-based approach (rules) rather than our multi-agent LLM approach (reasoning).

### The Agent-as-a-Judge Paradigm Is Well-Established

**[Agent-as-a-Judge survey](https://arxiv.org/abs/2601.05111)** (January 2026, now ICML 2025 poster) defines exactly what Veritas does:
- Planning + tool-augmented verification + multi-agent collaboration + persistent memory
- This is a recognized paradigm shift from LLM-as-Judge
- Multiple implementations exist

**[Amazon research](https://assets.amazon.science/48/5d/20927f094559a4465916e28f41b5/enhancing-llm-as-a-judge-via-multi-agent-collaboration.pdf)** proves multi-agent debate improves alignment with human ratings (Spearman ρ up to 0.47 vs 0.15-0.36 for single-agent).

**What this means:** Multi-agent verification is validated by the literature. We're implementing a proven paradigm, not inventing one.

### Galileo Luna Is Faster and Production-Ready

**[Galileo Luna](https://galileo.ai/blog/galileo-luna-breakthrough-in-llm-evaluation-beating-gpt-3-5-and-ragas)** uses fine-tuned small models for hallucination detection:
- Millisecond inference (vs our 15-20 seconds)
- Outperforms GPT-3.5 and RAGAS
- Real-time guardrails in production
- Enterprise-grade

**What this means:** For pure hallucination detection speed, we can't compete. Luna is purpose-built and orders of magnitude faster.

---

## What IS Still Genuinely Different About Veritas

### 1. Information Asymmetry in Agent Design (Potentially Novel)

In our RAG diagnostics, the Retrieval Auditor sees query + docs but NOT the answer. The Generation Auditor sees docs + answer but doesn't know if retrieval was good. This information asymmetry prevents confirmation bias.

RAGVUE doesn't do this — it evaluates each metric with full context. RAG-X evaluates retriever and generator independently but doesn't use information isolation between evaluators.

**Strength: Moderate.** This is a real architectural choice that our ablation showed produces +1.6 completeness. But it hasn't been tested head-to-head against RAGVUE's approach.

### 2. Multi-Agent Action Verification (vs Superagent's Policy Engine)

Superagent uses **declarative rules** — you define policies and the Safety Agent checks compliance. Our `verify_action()` uses **LLM reasoning** — 4 agents independently analyze whether an action is correct.

These are fundamentally different approaches:
- Superagent: "Does this action violate policy X?" (fast, deterministic, but limited to pre-defined rules)
- Veritas: "Is the REASONING behind this action sound? Are the parameters correct? What risks exist?" (slow, expensive, but catches novel issues)

**Strength: Strong.** Policy engines can't catch a $500K-instead-of-$5K error unless someone wrote a rule for that specific case. Our reasoning-based approach caught it from first principles.

### 3. Three Capabilities in One Library

No single tool combines claim verification + RAG diagnostics + pre-action verification with the same `pip install`. RAGVUE is RAG-only. Superagent is agentic-only. Galileo is observability.

**Strength: Moderate.** Convenience, not novelty. But enterprises don't want 3 separate tools.

### 4. Proven Multi-Agent > Single-Prompt (Ablation)

Our ablation study with blind evaluation showed multi-agent beats single-prompt 7/9 cases on completeness and specificity. This specific result hasn't been published elsewhere.

**Strength: Moderate.** Small sample, LLM-as-evaluator circularity. But directionally valid.

---

## Where We're Objectively Weak

### 1. Speed
15-20 seconds per verification. Galileo Luna does milliseconds. RAGVUE with a single LLM call is ~3-5 seconds. We're 3-5x slower than direct competitors.

### 2. No Head-to-Head Comparison
We never tested Veritas against RAGVUE, RAG-X, or Superagent on the same dataset. We benchmarked against ourselves (isolation vs debate) and against a single-prompt baseline. Without head-to-head data, we can't claim superiority.

### 3. No Production Validation
Zero real-world deployments. Zero user feedback. Zero integration with actual RAG pipelines or agent frameworks. RAGVUE has a Streamlit dashboard. Galileo has enterprise customers. We have a library nobody has used yet.

### 4. The LLM-Checking-LLM Problem Remains
All our results come from Claude checking Claude. If Claude has systematic blind spots, Veritas inherits them. Galileo Luna at least uses fine-tuned models optimized for detection. We use general-purpose models with prompt engineering.

### 5. Academic Novelty is Limited
- RAG root-cause diagnosis: RAGVUE and RAG-X published first
- Multi-agent verification: Agent-as-a-Judge is a recognized paradigm
- Pre-action verification: Superagent exists
- We didn't invent any of these ideas. We combined them.

---

## Practical Applications — Where Veritas Actually Fits

### Strong Fit

**1. Development-Time RAG Debugging**
When your RAG pipeline gives a wrong answer and you need to figure out why. Not real-time — the dev runs `diagnose_rag()` and gets a diagnosis. The information asymmetry design and claim-level mapping make this useful for debugging sessions.

Competition: RAGVUE does similar. Our differentiation is the multi-agent isolation with information asymmetry.

**2. Pre-Deployment Action Review**
Before deploying an agentic pipeline, run `verify_plan()` on the agent's typical action sequences. Catches issues like missing validation steps, irreversible actions without confirmation, scope creep.

Competition: Superagent's policy engine. Our differentiation is reasoning-based (catches novel issues) vs rule-based (only catches pre-defined violations).

**3. Batch Evaluation of AI Outputs**
Run `verify()` across a test set before deploying model changes. The failure mode taxonomy (factual_error, logical_inconsistency, scope_error, etc.) gives structured feedback for prompt engineers.

Competition: Every evaluation tool. Our differentiation is the failure mode taxonomy and multi-agent thoroughness.

### Weak Fit

**1. Real-Time Production Filtering** — too slow (15-20s)
**2. High-Volume Automated Guardrails** — too expensive ($0.08/call)
**3. Pure Hallucination Detection** — Galileo Luna is faster and likely more accurate
**4. Simple RAG Evaluation Metrics** — RAGAS is simpler and sufficient for dashboards

---

## What We Need to Make It Stronger

### Must-Do (to be credible)

1. **Head-to-head against RAGVUE** on the same dataset. If we beat RAGVUE on claim-level accuracy with our information asymmetry design, that's a real contribution. If we don't, we need to pivot.

2. **Head-to-head against Superagent** on action verification. Our reasoning-based approach vs their policy engine on novel scenarios the policy engine hasn't seen rules for.

3. **Faster execution mode.** The single-prompt baseline from our ablation is 4x faster and gets the diagnosis right 9/9 times. Ship it as `Config(mode="fast")` and let users choose thoroughness vs speed.

4. **Real integration with LangChain/LlamaIndex.** Plug `diagnose_rag()` into an actual pipeline. Show it catching a real failure that RAGAS missed.

### Should-Do (to be competitive)

5. **Fine-tuned small models for speed-critical agents.** Logic verifier and calibration agent don't need Sonnet — train a small model like Galileo's Luna approach. Get per-verification latency under 3 seconds.

6. **Dashboard/observability layer.** RAGVUE has Streamlit. Galileo has a full platform. A simple web UI showing verification history, failure mode trends, and pipeline health would make Veritas usable by non-developers.

7. **Streaming/progressive results.** Return partial results as each agent completes, instead of waiting for all 5. User sees "Retrieval: OK" immediately, then "Generation: PROBLEM" seconds later.

### Nice-to-Have (differentiation)

8. **Cross-model verification.** Use different LLM families for different agents (Claude for source, GPT for adversary, Gemini for logic). True model diversity eliminates the LLM-checking-same-LLM circularity problem.

9. **Formal verification for code** (Option C). This remains genuinely novel and hard. Nobody has made proof-carrying code accessible.

---

## Honest Bottom Line

**Veritas is a well-engineered implementation of ideas that are now mainstream.** RAG diagnostics, multi-agent verification, and pre-action safety are all recognized problems with existing solutions. We're not first.

**What's genuinely ours:**
- Information asymmetry in agent design (architectural contribution)
- Multi-agent vs single-prompt ablation data (empirical contribution)
- Reasoning-based action verification vs policy-based (different approach, not clearly better yet)
- Three capabilities in one `pip install` (convenience)

**What would make us genuinely groundbreaking:**
- Prove information asymmetry beats RAGVUE head-to-head
- Prove reasoning-based catches things policy-based misses
- Ship the fast mode for production use
- Build real integrations that people actually use

The tool is good. The engineering is solid. The novelty claims need to be scaled back and focused on what's actually unique: the information asymmetry design and the reasoning-based action verification approach.

---

## Sources

- [RAGVUE paper](https://arxiv.org/abs/2601.04196) — Jan 2026
- [RAGVUE GitHub](https://github.com/KeerthanaMurugaraj/RAGVue)
- [RAG-X paper](https://arxiv.org/abs/2603.03541) — March 2026
- [RAGXplain](https://arxiv.org/html/2505.13538v2)
- [Agent-as-a-Judge survey](https://arxiv.org/abs/2601.05111) — ICML 2025
- [Amazon multi-agent judging](https://assets.amazon.science/48/5d/20927f094559a4465916e28f41b5/enhancing-llm-as-a-judge-via-multi-agent-collaboration.pdf)
- [Superagent framework](https://www.helpnetsecurity.com/2025/12/29/superagent-framework-guardrails-agentic-ai/)
- [Galileo Luna](https://galileo.ai/blog/galileo-luna-breakthrough-in-llm-evaluation-beating-gpt-3-5-and-ragas)
- [Agent-as-a-Judge GitHub](https://github.com/metauto-ai/agent-as-a-judge)
- [AI Agent Guardrails 2026](https://authoritypartners.com/insights/ai-agent-guardrails-production-guide-for-2026/)
- [Databricks DASF v3.0 Agentic AI](https://www.databricks.com/blog/agentic-ai-security-new-risks-and-controls-databricks-ai-security-framework-dasf-v30)
- [RAG Monitoring Benchmark 2026](https://research.aimultiple.com/rag-monitoring/)
- [Multi-Agent Debate with Adaptive Stability](https://openreview.net/forum?id=Vusd1Hw2D9)
