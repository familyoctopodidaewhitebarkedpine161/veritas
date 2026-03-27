# Veritas Research: Landscape Analysis

**Date:** 2026-03-27
**Purpose:** Comprehensive analysis of the AI output verification space to identify gaps and novel positioning for Veritas.

---

## 1. The Problem Space

LLMs hallucinate. They generate confident, fluent text that is factually wrong, logically inconsistent, or unsupported by evidence. The problem is worse than it appears because:

- Hallucinations are often **indistinguishable from correct output** without external verification
- Models are **systematically overconfident** (ICLR 2025, KDD 2025 surveys)
- Self-evaluation is unreliable — "An LLM can fool itself" (ICLR 2024)
- In clinical settings, models repeat planted errors **83% of the time** (Nature Communications Medicine 2025)

The verification problem: how do you know if an AI output is correct **without already knowing the answer**?

---

## 2. Existing Academic Systems

### 2.1 Self-Consistency Methods

**SelfCheckGPT** (Manakul et al., EMNLP 2023)
- Generates multiple stochastic samples, checks consistency across them
- Zero-resource (no ground truth needed)
- Limitations: multiple forward passes; fails when model confidently hallucinates the same thing consistently; sentence-level only; tells you *that* something is wrong but not *what* is wrong
- GitHub: potsawee/selfcheckgpt

**Semantic Entropy** (Farquhar et al., Nature 2024, Oxford)
- Clusters sampled answers by meaning, computes entropy in meaning-space
- Low semantic entropy = confident about meaning
- Limitations: needs multiple samples; partial logit access needed; detects uncertainty, not necessarily errors

### 2.2 Retrieval-Based Verification

**FactScore** (Min et al., EMNLP 2023)
- Decomposes text into atomic facts, verifies each against Wikipedia
- `pip install factscore`
- Limitations: Wikipedia-centric; biography-focused; expensive for long texts

**SAFE** (Wei et al., Google DeepMind, NeurIPS 2024)
- Atomic decomposition + iterative Google Search per fact
- Agrees with human annotators 72%; wins 76% of disagreements
- 20x cheaper than human annotation
- Limitations: search-quality dependent; slow; struggles with obscure/recent facts

**FacTool** (Chern et al., 2023)
- Tool-augmented: Google Search, Scholar, code interpreters, Wolfram Alpha
- Covers: knowledge QA, code, math, scientific literature
- Limitations: heavy GPT-4 dependency; slow; domain-limited

**OpenFactCheck** (EMNLP 2024)
- Modular pipeline: ResponseEval, LLMEval, CheckerEval
- `pip install openfactcheck`
- Limitations: framework for building checkers, not a checker itself

**MiniCheck** (Tang et al., EMNLP 2024)
- Small fine-tuned models with GPT-4-level performance at 400x lower cost
- Limitations: document-grounded only; requires source documents

### 2.3 Chain-of-Thought Polling

**ChainPoll** (Friel et al., 2023 / Galileo)
- CoT prompting + multiple polling iterations + aggregation
- Outperforms SelfCheckGPT, GPTScore, G-Eval, TRUE
- Limitations: multiple LLM calls; evaluator biases propagate; commercial platform

### 2.4 Multi-Agent Debate

**Du et al. (ICML 2024)** — "Improving Factuality and Reasoning through Multiagent Debate"
- 3-6 LLM instances debate over multiple rounds
- 3 agents x 2 rounds often sufficient; diminishing returns beyond
- ~15% improvement in mathematical reasoning over single-agent
- Limitations: shared context; expensive; agents can reinforce errors; no convergence guarantee

**A-HMAD (2025)** — Adaptive Heterogeneous Multi-Agent Debate
- Diverse specialized agents + dynamic debate mechanisms
- Limitations: shared context still; academic prototype

**Tool-MAD (2025)** — Multi-Agent Debate with External Tools
- Iterative retrieval + dynamic agent interactions for claim verification
- Limitations: research code only; not packaged

**MADR (2024)** — Multi-Agent Debate Refinement for Fact-Checking
- Multiple LLMs in iterative refining with role diversity
- Limitations: focuses on explanation faithfulness, not general verification

---

## 3. Production Tools

| Tool | Approach | Open Source | Model-Agnostic | Evidence Chains |
|------|----------|-----------|----------------|----------------|
| ThoughtProof MCP | Multi-model adversarial critique | No (paywalled, x402 USDC) | Yes | Partial (3 objections) |
| Galileo (ChainPoll) | CoT polling + Luna model | No | Yes | Yes |
| Guardrails AI | Pluggable validators | Yes (core) | Yes | Partial |
| NeMo Guardrails | Colang DSL guardrails | Yes | Yes | Configurable |
| RAGAS | RAG evaluation metrics | Yes | Yes | Yes (per-claim) |
| DeepEval | Unit-test-like LLM eval | Yes | Yes | Yes |
| TruLens | Feedback functions for groundedness | Yes | Yes | Yes |
| Vectara HHEM | Cross-encoder hallucination model | Yes (model) | Yes | No (score only) |
| Cleanlab TLM | Confidence scoring | Partial | Partial | Partial |
| Patronus AI / Lynx | Enterprise eval + open model | Partial | Yes | Yes |
| Azure Groundedness | Cloud API grounding check | No | Yes | Partial |
| Factiverse | Real-time fact-checking API | No | Yes | Yes |
| OpenAI Guardrails | FileSearch-based hallucination check | Yes | No (OpenAI only) | Partial |

### Key Observation
Every production tool falls into one of:
1. **RAG faithfulness checkers** (RAGAS, DeepEval, TruLens) — only check against provided context
2. **Search-augmented verifiers** (SAFE, FacTool, Factiverse) — slow, search-dependent
3. **Single-model confidence** (Cleanlab, HHEM) — no adversarial challenge
4. **Paywalled services** (ThoughtProof, Galileo, Patronus) — closed, no evidence chains

**Nobody offers: open-source + adversarial multi-agent + evidence chains + no ground truth + pip-installable.**

---

## 4. Multi-Agent Orchestration Frameworks

| Feature | Overstory | CrewAI | AutoGen | LangGraph | MetaGPT |
|---------|-----------|--------|---------|-----------|---------|
| Agent Isolation | Git worktrees (filesystem) | None (shared process) | Separate objects | Graph nodes, shared state | Global message pool |
| Process Isolation | tmux sessions | None | Docker (optional) | None | None |
| Communication | Typed SQLite mail | Task output chain | Conversation | State graph edges | Global broadcast |
| Adversarial Support | Architecture supports it | None | Informal two-agent | Debate cycles via graph | None |
| Conflict Resolution | 4-tier merge | None | Group chat manager | State reducers | Role authority |
| Parallel Execution | Yes (worktrees) | Limited | Group chat | Fan-out/fan-in | No |

### Why Overstory Is Uniquely Suited
- **Git worktree isolation** = agents literally cannot see each other's in-progress work
- **SQLite typed mail** = structured, auditable inter-agent communication
- **tmux process isolation** = true parallel execution
- **4-tier merge** = sophisticated synthesis of parallel outputs

No other framework provides filesystem-level isolation between agents.

---

## 5. The Conformity Bias Problem

This is the critical research gap that Veritas addresses.

### Evidence That Shared Context Causes Groupthink

**"Emergent social conventions and collective bias in LLM populations"** (Science Advances, 2025)
- Even unbiased-in-isolation models develop collective bias through repeated interaction
- Bias emerges from agent-to-agent communication creating diverse memory states

**"Silence is Not Consensus"** (2025)
- Multi-agent LLMs exhibit "agreement bias" — agents converge on superficial consensus
- Mirrors human groupthink: individuals suppress dissent

**"Cross-Context Verification"** (2026)
- "Session isolation, not structural complexity, is the necessary condition for effective verification"
- Hierarchical multi-agent analysis (HCCA) prevents confirmation bias through intentional information restriction

**"Conformity bias in multi-agent systems"** (2025)
- Conformity bias drives agents to reinforce each other's errors rather than independent evaluation
- Creates dangerous false consensus

### The Gap
Every multi-agent debate system (Du et al., A-HMAD, Tool-MAD, MADR) uses shared conversation context. Papers repeatedly identify this as a problem, but no system enforces true isolation until synthesis.

---

## 6. Calibration: The Meta-Verification Problem

### The State of LLM Confidence

- LLMs are **systematically overconfident** (multiple 2024-2025 surveys)
- Verbalized confidence **consistently overestimates** model confidence
- Token-level entropy helps but requires logit access
- Multi-generation consistency is better but expensive

### What's Missing
- No verification system has a **dedicated calibration agent** that audits confidence-evidence alignment
- The meta-verification problem (who verifies the verifier?) is identified as open in multiple surveys
- Multi-agent confidence calibration is virtually unstudied

---

## 7. Adversarial Robustness of Verification Systems

### Known Vulnerabilities
- **PromptAttack** (ICLR 2024): LLMs can generate adversarial samples against themselves
- **Clinical vignettes** (Nature Comms Medicine 2025): Models repeat planted errors 83% of the time
- Hallucination signals exist in internal states **before generation** — but no system exploits this for pre-emptive verification

### The Gap
No verification system tests its own robustness to adversarial inputs. A dedicated adversary agent that actively tries to break claims is structurally different from (and stronger than) debate-style argumentation.

---

## 8. Identified Research Gaps

### Gap 1: Isolation-First Verification (PRIMARY NOVEL CONTRIBUTION)
No system enforces true agent isolation during verification. All debate approaches share context. Research proves shared context causes conformity bias. Overstory's git worktrees enable what no other framework can.

### Gap 2: No pip-installable Adversarial Verification Library
Academic debate code is research scripts. ThoughtProof is paywalled. Guardrails/NeMo are safety rails, not claim verification. Nothing provides `from veritas import verify` with multi-agent adversarial checking.

### Gap 3: Calibration Agent as First-Class Component
No production system audits confidence-evidence alignment. Multi-agent calibration is virtually unstudied.

### Gap 4: Structured Failure Mode Taxonomy
Existing systems return binary factual/not-factual. Nobody categorizes HOW something fails:
- Logical inconsistency (self-contradiction)
- Factual error (wrong fact)
- Unsupported inference (claim exceeds evidence)
- Temporal error (outdated information)
- Scope error (claim too broad/narrow)

### Gap 5: Adversary as Structural Component
A dedicated agent whose job is constructing counterexamples is structurally stronger than debate-style argumentation. Closer to formal verification red-teaming than conversational debate.

---

## 9. Veritas Novel Positioning

**Thesis:** Adversarial parallel verification with enforced agent isolation produces more reliable verdicts than shared-context debate, and can be packaged as a practical, model-agnostic library.

### Five Novel Claims

1. **Isolation-first architecture prevents conformity bias** — backed by Cross-Context Verification (2026), Science Advances groupthink findings (2025)
2. **Adversary agent as structural component** — dedicated counterexample constructor, not debate participant
3. **Calibration-as-verification** — dedicated agent auditing confidence-evidence alignment
4. **Structured failure mode output** — taxonomy of failure types, not binary verdicts
5. **Production-ready open-source packaging** — `pip install veritas` with one-line API

### Benchmarks to Beat
- SelfCheckGPT on WikiBio (hallucination detection baseline)
- SAFE on LongFact (Google's SOTA for long-form factuality)
- Du et al. multi-agent debate on TruthfulQA, MMLU

### Paper-Worthy Experiment
Same 5-agent verification with:
1. Shared context (standard debate)
2. Isolated context with synthesis (Veritas approach)

Measure: accuracy, calibration error (ECE), failure mode diversity, adversarial robustness.

---

## 10. Key References

### Multi-Agent Debate
- Du et al. "Improving Factuality and Reasoning through Multiagent Debate" (ICML 2024) — arxiv.org/abs/2305.14325
- Liang et al. "Encouraging Divergent Thinking in LLMs through Multi-Agent Debate" (2023) — arxiv.org/abs/2305.19118
- Irving et al. "AI Safety via Debate" (2018) — arxiv.org/abs/1805.00899

### Hallucination Detection
- Manakul et al. "SelfCheckGPT" (EMNLP 2023) — arxiv.org/abs/2303.08896
- Farquhar et al. "Semantic Entropy" (Nature 2024) — nature.com/articles/s41586-024-07421-0
- Friel et al. "ChainPoll" (2023) — arxiv.org/abs/2310.18344

### Fact Verification
- Min et al. "FactScore" (EMNLP 2023) — arxiv.org/abs/2305.14251
- Chern et al. "FacTool" (2023) — arxiv.org/abs/2307.13528
- Wei et al. "SAFE / Long-form Factuality" (NeurIPS 2024) — arxiv.org/abs/2403.18802
- Wang et al. "OpenFactCheck" (EMNLP 2024) — arxiv.org/abs/2405.05583

### Conformity Bias / Groupthink
- "Emergent social conventions and collective bias in LLM populations" (Science Advances 2025)
- "Silence is Not Consensus" (2025) — arxiv.org/abs/2505.21503
- "Cross-Context Verification" (2026) — arxiv.org/abs/2603.21454

### LLM-as-Judge Limitations
- "Self-Preference Bias in LLM-as-a-Judge" (2024) — arxiv.org/abs/2410.21819
- "A Survey on LLM-as-a-Judge" (2024) — arxiv.org/abs/2411.15594
- "Justice or Prejudice? Quantifying Biases in LLM-as-a-Judge" (2024)

### Calibration & Uncertainty
- "Uncertainty Quantification and Confidence Calibration in LLMs: A Survey" (KDD 2025) — arxiv.org/abs/2503.15850
- "Do LLMs Estimate Uncertainty Well?" (ICLR 2025)
- Xiong et al. "Can LLMs Express Their Uncertainty?" (2023) — arxiv.org/abs/2306.13063

### Adversarial Robustness
- "An LLM Can Fool Itself" (ICLR 2024)
- "Multi-model assurance analysis: LLMs vulnerable to adversarial hallucination attacks" (Nature Comms Medicine 2025)
- Bai et al. "Constitutional AI" (Anthropic, 2022) — arxiv.org/abs/2212.08073
