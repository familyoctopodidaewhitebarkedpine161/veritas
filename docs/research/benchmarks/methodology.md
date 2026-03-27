# Veritas Evaluation Methodology

**Date:** 2026-03-27
**Version:** 1.0
**Authors:** Waqas Riaz

---

## 1. What Veritas Is

Veritas is a multi-agent verification system with 5 novel capabilities:

1. **Isolation-divergent architecture** — agents verify in parallel with zero shared context
2. **Failure mode taxonomy** — classifies HOW claims fail (6 types), not just binary true/false
3. **Calibration-as-verification** — dedicated agent auditing confidence vs evidence alignment
4. **Structural adversary** — dedicated counterexample constructor (not debate participant)
5. **Hallucination detection** — catches wrong AI outputs (shared with existing tools)

Capabilities 1-4 are novel. No existing tool or benchmark tests for them. Our evaluation must prove each independently.

## 2. Why Not Compare Against Existing Tools

### The model confound
Existing tools (SelfCheckGPT, ChainPoll, SAFE, RefChecker) were evaluated with older models (GPT-3.5, GPT-4, Claude 2). Running Veritas with Claude Sonnet 4.6 and comparing raw numbers would conflate model improvement with method improvement. Reviewers would reject this.

### The scope mismatch
Existing tools are binary hallucination detectors (true/false). Veritas does 4 things they don't do at all. Reimplementing their methods with our model to create an apples-to-apples comparison would be valid but:
- Doesn't showcase our novel capabilities
- Repeats existing work
- Distracts from the actual contributions

### Our approach
We evaluate each novel capability in isolation using controlled experiments where the ONLY variable is the architectural choice (isolation vs debate, with vs without calibration agent, etc.). We cite published FaithBench numbers for context but don't rerun other tools.

## 3. Evaluation Design Principles

1. **Control for the model** — same Claude Sonnet 4.6 in all conditions
2. **One variable per experiment** — each benchmark isolates one capability
3. **Human-annotated ground truth** — expert labels for failure modes and correctness
4. **Ablation studies** — remove one component, measure the degradation
5. **Statistical validity** — enough samples for meaningful p-values

## 4. The Five Benchmarks

### Benchmark 1: Adversarial Robustness (Priority 1)

**Research question:** Does shared context cause agents to propagate planted errors (conformity bias), while isolation catches them?

**Why this matters:** The Cross-Context Verification paper (2026) proved session isolation is necessary for effective verification. The Science Advances 2025 paper showed collective bias emerges from shared context. But nobody has measured the QUANTITATIVE difference on a controlled dataset.

**Dataset design:** 50 claims in 3 categories:
- **Subtle factual errors** (20): Claims that are almost correct but off by one detail. "The iPhone was released June 29, 2008" (off by one year). These test whether agents independently catch small errors vs reinforce each other's priors.
- **Scope errors** (15): Claims that overgeneralize. "All mammals give live birth" (monotremes don't). Tests whether the adversary finds counterexamples independently.
- **Planted confident errors** (15): Claims stated with high certainty that are wrong. "Einstein definitely failed his math exams at ETH Zurich" (he didn't). Tests whether shared context amplifies false confidence.

**Why these categories:** They target the specific failure modes where conformity bias is most dangerous. A subtle one-year-off error is easy to miss if another agent already said "looks correct." An overgeneralization is easy to agree with if no one has independently looked for counterexamples.

**Conditions:**
1. Veritas isolation mode (agents run in parallel, no shared context)
2. Veritas debate mode (agents run sequentially, each sees prior findings)

**Metrics:**
- Detection rate: % of planted errors caught (REFUTED or PARTIAL)
- False negative rate: % of errors missed (incorrectly VERIFIED)
- Confidence on errors: average confidence when the claim IS wrong (lower = better calibrated)

**Expected result:** Isolation catches more errors because debate's shared context causes conformity — once logic_verifier says "consistent," subsequent agents are biased toward agreement.

---

### Benchmark 2: Isolation vs Debate on FaithBench (Priority 2)

**Research question:** On a standard, hard hallucination detection benchmark, does isolation outperform debate?

**Why FaithBench:**
- NAACL 2025 — the latest published benchmark for hallucination detectors
- Best existing detector achieves only 55% F1 — plenty of room
- Human-annotated ground truth from domain experts
- Curated from cases where GPT-4o-as-judge DISAGREED with humans — specifically hard
- Tests detectors, not models — exactly what Veritas is

**Dataset:** FaithBench's full dataset (summarization hallucinations from 10 LLMs, 8 families)

**Conditions:**
1. Veritas isolation mode
2. Veritas debate mode

**Metrics:**
- F1, precision, recall, balanced accuracy
- ECE (Expected Calibration Error)
- Speed (wall-clock time per claim)

**Context comparison:** We cite published FaithBench numbers for GPT-4o, o1-mini, o3-mini as context. We don't rerun them — we note the model difference and focus our analysis on isolation vs debate.

---

### Benchmark 3: Failure Mode Classification (Priority 3)

**Research question:** Can Veritas correctly identify the TYPE of failure in a claim, not just that it's wrong?

**Why this is novel:** Every existing tool returns binary (hallucinated / not hallucinated) or a score. Nobody classifies failure types. This is our unique contribution. No benchmark exists for this, so we create one.

**Dataset design:** 200 claims, expert-labeled with failure type:

| Category | Count | Example | Label |
|----------|-------|---------|-------|
| Factual error | 30 | "Python was created by James Gosling" | factual_error |
| Logical inconsistency | 30 | "All cats are animals. Some animals are dogs. Therefore all cats are dogs." | logical_inconsistency |
| Unsupported inference | 30 | "Countries with more ice cream sales have more drownings, so ice cream causes drowning" | unsupported_inference |
| Temporal error | 30 | "As of 2020, GPT-4 is the most advanced language model" | temporal_error |
| Scope error | 30 | "Antibiotics cure all infections" | scope_error |
| Source conflict | 30 | "The population of Tokyo is 14 million / 37 million" (city vs metro) | source_conflict |
| Correct claims | 20 | "Water freezes at 0°C at standard pressure" | none |

**Why these proportions:** Equal representation per failure type ensures we're not biased toward detecting one type. 20 correct claims prevent the model from learning to always find errors.

**Metrics:**
- Multi-class accuracy (correct failure type)
- Per-class F1 (which types does it get right/wrong?)
- Confusion matrix (does it confuse logical errors with scope errors?)

**Why this matters for users:** "Your claim is wrong" is useless feedback. "Your claim has a temporal error — the data is from 2020 but the claim is about 2026" is actionable. Nobody else provides this.

---

### Benchmark 4: Calibration Quality (Priority 4)

**Research question:** Does the dedicated calibration agent improve confidence-evidence alignment?

**Why this is novel:** LLMs are systematically overconfident (ICLR 2025, KDD 2025 surveys). No verification system has a dedicated component to audit this. We test whether adding one helps.

**Dataset design:** 100 claims with varying evidence strength:

| Category | Count | Characteristic |
|----------|-------|---------------|
| Well-established facts | 25 | Should have high confidence (>0.9) |
| Approximately correct | 25 | Should have moderate confidence (0.6-0.8) |
| Hedged/uncertain claims | 25 | Should have low confidence (0.3-0.5) |
| Confidently wrong | 25 | Should have low confidence despite strong language |

**Conditions (ablation study):**
1. Veritas with all 4 agents (including calibration)
2. Veritas without calibration agent (only logic, source, adversary)

**Metrics:**
- ECE (Expected Calibration Error) — primary metric
- Reliability diagram — visual calibration plot
- Overconfidence rate — % of wrong claims with confidence > 0.8

**Expected result:** The calibration agent reduces ECE by catching overconfident wrong claims and underconfident correct claims.

---

### Benchmark 5: Published Comparison Context

**Purpose:** One table placing Veritas results alongside published FaithBench numbers for context.

**Approach:** We do NOT rerun existing tools. We cite their published numbers and note:
- Different models (their GPT-4o/o3-mini vs our Sonnet 4.6)
- Same dataset, same metrics
- Focus is on our isolation vs debate comparison, not raw number comparison

**Why this is honest:** Reviewers know models matter. We're transparent about it. Our contribution isn't "we beat SelfCheckGPT" — it's "isolation beats debate, failure mode taxonomy works, calibration helps."

## 5. Statistical Methodology

- **Sample sizes:** Minimum 50 claims per benchmark condition for meaningful results
- **Confidence intervals:** Report 95% CI on all metrics
- **Effect size:** Report Cohen's d for isolation vs debate comparisons
- **Significance test:** McNemar's test for paired accuracy comparisons (same claims, different methods)

## 6. Reproducibility

- All datasets will be published with the library
- All benchmark code is in `veritas/benchmarks/`
- Random seeds fixed for reproducibility
- Full results (per-claim verdicts, confidence scores, failure mode predictions) saved as JSON
- Model version locked to `claude-sonnet-4-6`

## 7. Limitations We Acknowledge

1. **Single LLM family:** v1 uses Claude only. The isolation principle should be model-agnostic, but we haven't proven it across providers yet.
2. **No web search in benchmarks:** Source verifier operates on LLM knowledge only (no Brave/Tavily key in these runs). Results may improve with search enabled.
3. **Async isolation, not worktree isolation:** v1 runs agents as async tasks in the same process. True Overstory worktree isolation (process-level) is implemented but not benchmarked yet.
4. **English only:** All claims are in English.
5. **Custom datasets for novel benchmarks:** Benchmarks 1, 3, 4 use our own datasets since no existing benchmarks test these capabilities. We mitigate bias through expert annotation and balanced design.
