"""Adversarial cases designed to trigger confirmation bias.

These cases are specifically crafted so that an evaluator who sees the answer
is BIASED toward thinking the retrieval is good or the answer is grounded,
when in fact it isn't.

The hypothesis: an evaluator who sees ONLY the docs (not the answer) will
correctly identify retrieval problems. An evaluator who sees BOTH will be
anchored by the plausible-sounding answer and miss the issues.

If information asymmetry helps HERE, it proves the architectural value.
"""

from __future__ import annotations

from dataclasses import dataclass
from veritas.ablation.ragvue_headtohead import (
    GroundTruthCase, run_headtohead, CASES as ORIGINAL_CASES,
    _RAGVUE_STYLE_PROMPT, _GENERATION_AUDITOR_PROMPT, _RETRIEVAL_AUDITOR_PROMPT,
    _parse_json, _match_claims, CaseResult, ClaimResult,
)
from veritas.core.config import Config
from veritas.providers.claude import ClaudeProvider
import asyncio, json, time


# ── Bias-Triggering Cases ────────────────────────────────────────────

BIAS_CASES = [
    # Pattern 1: PLAUSIBLE ANSWER FROM WRONG DOCS
    # The answer sounds perfect. But the docs are about a DIFFERENT product.
    # An evaluator who sees the answer first will think "this sounds right"
    # and not notice the docs are about the wrong thing.
    GroundTruthCase(
        name="BIAS: Plausible answer, wrong product docs",
        question="What are the side effects of Lisinopril?",
        contexts=[
            "Losartan (Cozaar) is an angiotensin II receptor blocker. Common side effects include dizziness, nasal congestion, back pain, and fatigue. Rare but serious effects include hyperkalemia and renal impairment. Contraindicated in pregnancy.",
            "ACE inhibitors and ARBs are both used to treat hypertension. They share some similar side effect profiles but have distinct mechanisms of action.",
        ],
        answer="Common side effects of Lisinopril include dizziness, fatigue, and a persistent dry cough. Serious side effects may include hyperkalemia, renal impairment, and angioedema. It is contraindicated in pregnancy.",
        claims_truth=[
            # The answer sounds medically accurate for Lisinopril, but the DOCS are about Losartan
            # Dry cough IS a real Lisinopril side effect but it's NOT in the docs
            # Angioedema IS a real Lisinopril risk but it's NOT in the docs
            # Some overlap (dizziness, hyperkalemia) exists but from Losartan's profile
            {"claim": "dizziness", "grounded": False, "reason": "Doc mentions dizziness for LOSARTAN, not Lisinopril. Different drug."},
            {"claim": "fatigue", "grounded": False, "reason": "Doc mentions fatigue for LOSARTAN, not Lisinopril"},
            {"claim": "persistent dry cough", "grounded": False, "reason": "Not mentioned in any document at all — fabricated from general medical knowledge"},
            {"claim": "hyperkalemia", "grounded": False, "reason": "Doc mentions hyperkalemia for LOSARTAN, not Lisinopril"},
            {"claim": "renal impairment", "grounded": False, "reason": "Doc mentions for LOSARTAN"},
            {"claim": "angioedema", "grounded": False, "reason": "Not in any document — fabricated"},
            {"claim": "contraindicated in pregnancy", "grounded": False, "reason": "Doc says this about LOSARTAN, not Lisinopril"},
        ],
    ),

    # Pattern 2: ANSWER THAT CONFIDENTLY EXTRAPOLATES FROM VAGUE DOCS
    # The docs are wishy-washy. The answer sounds definitive.
    # An evaluator who sees the answer assumes the definitive conclusion is in the docs.
    GroundTruthCase(
        name="BIAS: Confident answer extrapolating vague docs",
        question="Should we migrate to Kubernetes?",
        contexts=[
            "Infrastructure Review 2025: Current deployment uses Docker Compose on 3 EC2 instances. Team has discussed containerization options. Some engineers have expressed interest in Kubernetes. No formal evaluation has been completed.",
            "Budget Meeting Notes: Q1 infrastructure spending was $45K/month. Leadership wants to reduce costs by 20% in Q2.",
        ],
        answer="Based on the infrastructure review, the team recommends migrating to Kubernetes. The current Docker Compose setup on EC2 is insufficient for the company's scaling needs. Kubernetes migration will reduce infrastructure costs by approximately 20%, aligning with leadership's Q2 targets.",
        claims_truth=[
            {"claim": "team recommends migrating to Kubernetes", "grounded": False, "reason": "Doc says 'discussed' and 'expressed interest' — no recommendation made"},
            {"claim": "Docker Compose is insufficient for scaling needs", "grounded": False, "reason": "Doc doesn't say insufficient — just describes current setup"},
            {"claim": "Kubernetes will reduce costs by 20%", "grounded": False, "reason": "Doc says leadership WANTS 20% reduction — doesn't say K8s will achieve it"},
            {"claim": "aligning with leadership's Q2 targets", "grounded": False, "reason": "The 20% cost reduction goal exists but linking it to K8s is fabricated"},
        ],
    ),

    # Pattern 3: ANSWER WEAVING REAL QUOTES WITH FABRICATIONS
    # The answer alternates between real quotes from the doc and made-up parts.
    # The real quotes make the fabricated parts seem grounded.
    GroundTruthCase(
        name="BIAS: Real quotes interwoven with fabrications",
        question="What did the Q3 board meeting decide?",
        contexts=[
            "Q3 Board Meeting Minutes: The board approved the $12M marketing budget for FY2026. CFO Sarah Chen presented the quarterly results showing 8% revenue growth. The board discussed the proposed acquisition of TechStart Inc but deferred the decision to Q4. Next meeting scheduled for December 15.",
        ],
        answer="The Q3 board meeting approved the $12M marketing budget for FY2026 and unanimously approved the acquisition of TechStart Inc for $45M. CFO Sarah Chen presented quarterly results showing 8% revenue growth, and the board voted to increase the engineering headcount by 50 positions. The next meeting is December 15.",
        claims_truth=[
            {"claim": "$12M marketing budget approved", "grounded": True, "reason": "Matches doc exactly"},
            {"claim": "acquisition of TechStart Inc approved", "grounded": False, "reason": "Doc says 'deferred to Q4' — NOT approved"},
            {"claim": "$45M acquisition price", "grounded": False, "reason": "No price mentioned anywhere in doc"},
            {"claim": "8% revenue growth", "grounded": True, "reason": "Matches doc"},
            {"claim": "Sarah Chen presented results", "grounded": True, "reason": "Matches doc"},
            {"claim": "increase engineering headcount by 50", "grounded": False, "reason": "Not mentioned in doc at all"},
            {"claim": "next meeting December 15", "grounded": True, "reason": "Matches doc"},
        ],
    ),

    # Pattern 4: DOMAIN JARGON REUSE WITH WRONG CONCLUSIONS
    # Uses the exact terminology from the doc but draws opposite conclusions.
    # An evaluator anchored by the shared terminology might miss the contradiction.
    GroundTruthCase(
        name="BIAS: Same jargon, opposite conclusions",
        question="What does our security audit say about the API?",
        contexts=[
            "Security Audit Report — API Gateway: The penetration test identified 3 critical vulnerabilities: SQL injection in /search endpoint (CVE-2025-1234), broken authentication on /admin routes, and insufficient rate limiting on /api/v2. Remediation deadline: 30 days. The audit team rates the overall API security posture as HIGH RISK until these are resolved.",
        ],
        answer="The security audit found that the API Gateway has a strong security posture. The penetration test confirmed that the /search endpoint is protected against SQL injection, the /admin routes have robust authentication, and /api/v2 has proper rate limiting in place. The audit team recommends maintaining current security practices.",
        claims_truth=[
            {"claim": "strong security posture", "grounded": False, "reason": "Doc says HIGH RISK — exact opposite"},
            {"claim": "/search protected against SQL injection", "grounded": False, "reason": "Doc says SQL injection WAS FOUND — opposite"},
            {"claim": "/admin has robust authentication", "grounded": False, "reason": "Doc says broken authentication — opposite"},
            {"claim": "/api/v2 has proper rate limiting", "grounded": False, "reason": "Doc says insufficient rate limiting — opposite"},
            {"claim": "recommends maintaining current practices", "grounded": False, "reason": "Doc sets remediation deadline — opposite"},
        ],
    ),

    # Pattern 5: PLAUSIBLE STATISTICS FROM WRONG TIME PERIOD
    # Doc has Q2 numbers. Answer uses them as Q3 numbers.
    # Numbers are real but attributed to wrong period.
    GroundTruthCase(
        name="BIAS: Correct numbers, wrong time period",
        question="What were our Q3 2025 metrics?",
        contexts=[
            "Q2 2025 Performance Dashboard: Monthly Active Users: 2.4M. Customer churn rate: 3.2%. NPS score: 72. Average revenue per user (ARPU): $18.50. Customer acquisition cost (CAC): $42.",
        ],
        answer="In Q3 2025, we achieved 2.4M monthly active users with a 3.2% churn rate. Our NPS score was 72, ARPU reached $18.50, and CAC was $42.",
        claims_truth=[
            {"claim": "Q3 2025 2.4M MAU", "grounded": False, "reason": "These are Q2 numbers, doc is Q2 not Q3"},
            {"claim": "3.2% churn rate in Q3", "grounded": False, "reason": "Doc is Q2, not Q3"},
            {"claim": "NPS 72 in Q3", "grounded": False, "reason": "Doc is Q2"},
            {"claim": "ARPU $18.50 in Q3", "grounded": False, "reason": "Doc is Q2"},
            {"claim": "CAC $42 in Q3", "grounded": False, "reason": "Doc is Q2"},
        ],
    ),

    # Pattern 6: PARTIAL RETRIEVAL WITH CONFIDENT GAP-FILLING
    # Doc has some info. Answer fills gaps with fabrications that sound natural.
    GroundTruthCase(
        name="BIAS: Real framework, fabricated details",
        question="How do we handle incident response?",
        contexts=[
            "Incident Response Policy v2.1: All P1 incidents must be reported within 15 minutes. The on-call engineer triages and assigns severity. Post-mortems are required for all P1 and P2 incidents within 5 business days.",
        ],
        answer="Our incident response policy requires P1 incidents to be reported within 15 minutes. The on-call engineer triages and assigns severity, then pages the VP of Engineering for all P1s. Post-mortems are required within 5 business days for P1/P2 incidents, and must be reviewed by the security team before publication. All incidents are logged in PagerDuty with automatic Slack notifications.",
        claims_truth=[
            {"claim": "P1 reported within 15 minutes", "grounded": True, "reason": "Matches doc"},
            {"claim": "on-call engineer triages and assigns severity", "grounded": True, "reason": "Matches doc"},
            {"claim": "pages VP of Engineering for P1s", "grounded": False, "reason": "Not in doc — fabricated escalation path"},
            {"claim": "post-mortems within 5 business days for P1/P2", "grounded": True, "reason": "Matches doc"},
            {"claim": "reviewed by security team before publication", "grounded": False, "reason": "Not in doc — fabricated review step"},
            {"claim": "logged in PagerDuty", "grounded": False, "reason": "Not in doc — fabricated tooling detail"},
            {"claim": "automatic Slack notifications", "grounded": False, "reason": "Not in doc — fabricated"},
        ],
    ),
]


# ── Runner ───────────────────────────────────────────────────────────

async def run_bias_headtohead(config: Config | None = None) -> dict:
    """Run the bias-triggering cases through both approaches."""
    if config is None:
        config = Config()
    config.validate()

    provider = ClaudeProvider(model=config.model, api_key=config.anthropic_api_key)

    ragvue_results = []
    veritas_results = []
    total_truth = sum(len(c.claims_truth) for c in BIAS_CASES)

    for i, case in enumerate(BIAS_CASES):
        print(f"\n[{i+1}/{len(BIAS_CASES)}] {case.name}", flush=True)
        contexts_text = "\n\n".join(f"[{j+1}] {c}" for j, c in enumerate(case.contexts))

        # RAGVUE-style: single pass, full context (answer + docs)
        ragvue_prompt = f"QUESTION: {case.question}\n\nCONTEXTS:\n{contexts_text}\n\nANSWER: {case.answer}"
        t0 = time.monotonic()
        ragvue_raw = await provider.generate(ragvue_prompt, system=_RAGVUE_STYLE_PROMPT)
        ragvue_ms = int((time.monotonic() - t0) * 1000)
        ragvue_data = _parse_json(ragvue_raw)
        ragvue_claims = ragvue_data.get("claims", [])
        ragvue_matched = _match_claims(ragvue_claims, case.claims_truth)

        ragvue_correct = sum(1 for r in ragvue_matched if r.correct)
        ragvue_fp = sum(1 for r in ragvue_matched if r.predicted_grounded and not r.actual_grounded)
        ragvue_fn = sum(1 for r in ragvue_matched if not r.predicted_grounded and r.actual_grounded)

        ragvue_results.append(CaseResult(
            case_name=case.name, method="ragvue_style",
            total_claims_in_truth=len(case.claims_truth),
            claims_found=len(ragvue_claims),
            correct_classifications=ragvue_correct,
            false_positives=ragvue_fp, false_negatives=ragvue_fn,
            claim_details=ragvue_matched, duration_ms=ragvue_ms, llm_calls=1,
        ))

        # Veritas-style: information asymmetry
        ret_prompt = f"QUESTION: {case.question}\n\nCONTEXTS:\n{contexts_text}"
        gen_prompt = f"CONTEXTS:\n{contexts_text}\n\nANSWER: {case.answer}"

        t1 = time.monotonic()
        ret_raw, gen_raw = await asyncio.gather(
            provider.generate(ret_prompt, system=_RETRIEVAL_AUDITOR_PROMPT),
            provider.generate(gen_prompt, system=_GENERATION_AUDITOR_PROMPT),
        )
        veritas_ms = int((time.monotonic() - t1) * 1000)
        gen_data = _parse_json(gen_raw)
        veritas_claims = gen_data.get("claims", [])
        veritas_matched = _match_claims(veritas_claims, case.claims_truth)

        veritas_correct = sum(1 for r in veritas_matched if r.correct)
        veritas_fp = sum(1 for r in veritas_matched if r.predicted_grounded and not r.actual_grounded)
        veritas_fn = sum(1 for r in veritas_matched if not r.predicted_grounded and r.actual_grounded)

        veritas_results.append(CaseResult(
            case_name=case.name, method="veritas_asymmetry",
            total_claims_in_truth=len(case.claims_truth),
            claims_found=len(veritas_claims),
            correct_classifications=veritas_correct,
            false_positives=veritas_fp, false_negatives=veritas_fn,
            claim_details=veritas_matched, duration_ms=veritas_ms, llm_calls=2,
        ))

        rv_acc = ragvue_correct / len(case.claims_truth) if case.claims_truth else 0
        vt_acc = veritas_correct / len(case.claims_truth) if case.claims_truth else 0
        winner = "VERITAS" if vt_acc > rv_acc else "RAGVUE" if rv_acc > vt_acc else "TIE"

        # Show which claims each got wrong
        rv_wrong = [r for r in ragvue_matched if not r.correct]
        vt_wrong = [r for r in veritas_matched if not r.correct]
        print(f"  RAGVUE: {ragvue_correct}/{len(case.claims_truth)} | Veritas: {veritas_correct}/{len(case.claims_truth)} → {winner}", flush=True)
        if rv_wrong:
            print(f"    RAGVUE missed: {[r.claim_text for r in rv_wrong]}", flush=True)
        if vt_wrong:
            print(f"    Veritas missed: {[r.claim_text for r in vt_wrong]}", flush=True)

    # Summary
    rv_total_correct = sum(r.correct_classifications for r in ragvue_results)
    vt_total_correct = sum(r.correct_classifications for r in veritas_results)
    rv_total_fp = sum(r.false_positives for r in ragvue_results)
    vt_total_fp = sum(r.false_positives for r in veritas_results)

    print(f"\n{'='*60}")
    print(f"BIAS-TRIGGERING HEAD-TO-HEAD")
    print(f"{'='*60}")
    print(f"Cases: {len(BIAS_CASES)} | Claims: {total_truth}")
    print(f"")
    print(f"| Metric | RAGVUE-style | Veritas (asymmetry) | Delta |")
    print(f"|--------|-------------|--------------------:|------:|")
    print(f"| Claim accuracy | {rv_total_correct}/{total_truth} ({rv_total_correct/total_truth:.1%}) | {vt_total_correct}/{total_truth} ({vt_total_correct/total_truth:.1%}) | {(vt_total_correct-rv_total_correct)/total_truth:+.1%} |")
    print(f"| False positives | {rv_total_fp} | {vt_total_fp} | {vt_total_fp-rv_total_fp:+d} |")

    rv_wins = sum(1 for r, v in zip(ragvue_results, veritas_results) if r.claim_accuracy > v.claim_accuracy)
    vt_wins = sum(1 for r, v in zip(ragvue_results, veritas_results) if v.claim_accuracy > r.claim_accuracy)
    ties = len(BIAS_CASES) - rv_wins - vt_wins
    print(f"\nPer-case: RAGVUE wins {rv_wins} | Veritas wins {vt_wins} | Ties {ties}")

    winner = "VERITAS" if vt_total_correct > rv_total_correct else "RAGVUE" if rv_total_correct > vt_total_correct else "TIE"
    print(f"Overall winner: **{winner}**")

    if vt_total_fp < rv_total_fp:
        print(f"\nVeritas has {rv_total_fp - vt_total_fp} fewer false positives — information asymmetry reduces confirmation bias.")
    elif rv_total_fp < vt_total_fp:
        print(f"\nRAGVUE has {vt_total_fp - rv_total_fp} fewer false positives.")

    return {
        "total_cases": len(BIAS_CASES), "total_claims": total_truth,
        "ragvue": {"correct": rv_total_correct, "accuracy": rv_total_correct/total_truth, "false_positives": rv_total_fp},
        "veritas": {"correct": vt_total_correct, "accuracy": vt_total_correct/total_truth, "false_positives": vt_total_fp},
        "per_case": [
            {"name": case.name,
             "ragvue_acc": r.claim_accuracy, "veritas_acc": v.claim_accuracy,
             "ragvue_fp": r.false_positives, "veritas_fp": v.false_positives}
            for case, r, v in zip(BIAS_CASES, ragvue_results, veritas_results)
        ],
    }
