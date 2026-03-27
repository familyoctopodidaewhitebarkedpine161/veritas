"""RAG Grounding Benchmark — tests whether Veritas catches unfaithful RAG outputs.

Tests the core RAG use case: given a SOURCE DOCUMENT and a GENERATED ANSWER,
does Veritas correctly identify when the answer hallucinates facts not in the document?

Each item has a document and two versions of an answer:
- Faithful: grounded in the document
- Hallucinated: adds, changes, or fabricates information

Error types tested:
- fabricated_fact: invents information not in the document
- wrong_number: changes a number (revenue, date, count)
- entity_swap: replaces one entity with another
- unsupported_claim: makes a causal/evaluative claim the document doesn't support
- scope_expansion: broadens a specific claim to a general one
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field

from veritas.core.config import Config
from veritas.core.result import Verdict, VerificationResult
from veritas.orchestration.runner import VerificationRunner
from veritas.orchestration.debate_runner import DebateRunner
from veritas.providers.claude import ClaudeProvider
from veritas.providers.base import SearchResult


@dataclass
class RAGItem:
    document: str
    answer: str
    is_faithful: bool
    error_type: str  # "faithful", "fabricated_fact", "wrong_number", "entity_swap", "unsupported_claim", "scope_expansion"
    domain: str


# ── Dataset ──────────────────────────────────────────────────────────

RAG_DATASET = [
    # --- Financial Reports ---
    RAGItem(
        document="Acme Corp reported Q3 2025 revenue of $4.2 billion, up 12% year-over-year. Operating expenses were $3.1 billion. The company has 15,000 employees across 23 countries. CEO Jane Smith noted cautious optimism for Q4.",
        answer="Acme Corp's Q3 2025 revenue was $4.2 billion, a 12% year-over-year increase. The company has 15,000 employees operating in 23 countries.",
        is_faithful=True, error_type="faithful", domain="financial",
    ),
    RAGItem(
        document="Acme Corp reported Q3 2025 revenue of $4.2 billion, up 12% year-over-year. Operating expenses were $3.1 billion. The company has 15,000 employees across 23 countries. CEO Jane Smith noted cautious optimism for Q4.",
        answer="Acme Corp's Q3 2025 revenue was $4.8 billion, a 15% year-over-year increase. The company has 18,000 employees operating in 23 countries.",
        is_faithful=False, error_type="wrong_number", domain="financial",
    ),
    RAGItem(
        document="Acme Corp reported Q3 2025 revenue of $4.2 billion, up 12% year-over-year. Operating expenses were $3.1 billion. The company has 15,000 employees across 23 countries. CEO Jane Smith noted cautious optimism for Q4.",
        answer="Acme Corp's Q3 2025 revenue was $4.2 billion. CEO John Miller expressed strong confidence in exceeding Q4 targets by a significant margin.",
        is_faithful=False, error_type="entity_swap", domain="financial",
    ),

    # --- Medical Guidelines ---
    RAGItem(
        document="The WHO recommends adults engage in at least 150 minutes of moderate-intensity aerobic activity per week. For additional health benefits, adults should increase to 300 minutes. Muscle-strengthening activities should be done 2 or more days per week.",
        answer="According to WHO guidelines, adults should perform at least 150 minutes of moderate-intensity aerobic activity weekly, with muscle-strengthening activities recommended on 2 or more days per week.",
        is_faithful=True, error_type="faithful", domain="medical",
    ),
    RAGItem(
        document="The WHO recommends adults engage in at least 150 minutes of moderate-intensity aerobic activity per week. For additional health benefits, adults should increase to 300 minutes. Muscle-strengthening activities should be done 2 or more days per week.",
        answer="The WHO recommends 150 minutes of moderate activity weekly. Research has shown this reduces cardiovascular disease risk by 40% and significantly lowers all-cause mortality.",
        is_faithful=False, error_type="fabricated_fact", domain="medical",
    ),

    # --- Technical Documentation ---
    RAGItem(
        document="PostgreSQL 16 introduced parallel execution of FULL and RIGHT OUTER joins. The COPY command now supports a DEFAULT option. The query planner was improved to use incremental sort in more cases. Logical replication now supports replication from standby servers.",
        answer="PostgreSQL 16 added support for parallel execution of FULL and RIGHT OUTER joins, and the COPY command gained a new DEFAULT option.",
        is_faithful=True, error_type="faithful", domain="technical",
    ),
    RAGItem(
        document="PostgreSQL 16 introduced parallel execution of FULL and RIGHT OUTER joins. The COPY command now supports a DEFAULT option. The query planner was improved to use incremental sort in more cases. Logical replication now supports replication from standby servers.",
        answer="PostgreSQL 16 introduced parallel execution of all join types including CROSS joins. It also added native support for horizontal sharding and automatic partitioning.",
        is_faithful=False, error_type="fabricated_fact", domain="technical",
    ),

    # --- Legal Policy ---
    RAGItem(
        document="Under the company's return policy, customers may return unused items within 30 days of purchase with original receipt. Electronics have a 15-day return window. Sale items are final sale and cannot be returned. Refunds are processed to the original payment method within 5-7 business days.",
        answer="The return policy allows unused items to be returned within 30 days with a receipt. Electronics must be returned within 15 days. Sale items are final sale.",
        is_faithful=True, error_type="faithful", domain="legal",
    ),
    RAGItem(
        document="Under the company's return policy, customers may return unused items within 30 days of purchase with original receipt. Electronics have a 15-day return window. Sale items are final sale and cannot be returned. Refunds are processed to the original payment method within 5-7 business days.",
        answer="The return policy allows all items including sale items to be returned within 60 days. Refunds are issued immediately as store credit.",
        is_faithful=False, error_type="wrong_number", domain="legal",
    ),

    # --- Scientific Research ---
    RAGItem(
        document="The study examined 500 participants over 12 months. Group A received the treatment (n=250) and Group B received placebo (n=250). The treatment group showed a 23% reduction in symptoms compared to 8% in placebo. Side effects included headache (12%) and nausea (7%). The p-value was 0.003.",
        answer="The study of 500 participants over 12 months found the treatment group (n=250) achieved a 23% symptom reduction versus 8% in the placebo group (p=0.003). Common side effects were headache (12%) and nausea (7%).",
        is_faithful=True, error_type="faithful", domain="scientific",
    ),
    RAGItem(
        document="The study examined 500 participants over 12 months. Group A received the treatment (n=250) and Group B received placebo (n=250). The treatment group showed a 23% reduction in symptoms compared to 8% in placebo. Side effects included headache (12%) and nausea (7%). The p-value was 0.003.",
        answer="The study conclusively proves this treatment is the most effective therapy available, virtually eliminating symptoms in the majority of patients with minimal side effects.",
        is_faithful=False, error_type="unsupported_claim", domain="scientific",
    ),

    # --- Company Internal Docs ---
    RAGItem(
        document="The engineering team completed 47 story points in Sprint 23. Three critical bugs were fixed: AUTH-401 (login timeout), DB-892 (connection pool leak), and API-156 (rate limiter bypass). The team velocity has been stable at 45-50 points for the last 4 sprints.",
        answer="In Sprint 23, the engineering team completed 47 story points and resolved three critical bugs: AUTH-401, DB-892, and API-156. Team velocity has been stable at 45-50 points over the past 4 sprints.",
        is_faithful=True, error_type="faithful", domain="technical",
    ),
    RAGItem(
        document="The engineering team completed 47 story points in Sprint 23. Three critical bugs were fixed: AUTH-401 (login timeout), DB-892 (connection pool leak), and API-156 (rate limiter bypass). The team velocity has been stable at 45-50 points for the last 4 sprints.",
        answer="The engineering team delivered 62 story points in Sprint 23, a significant improvement. Five critical bugs were resolved, and team velocity has been trending upward over the past 6 sprints.",
        is_faithful=False, error_type="wrong_number", domain="technical",
    ),

    # --- Product Specifications ---
    RAGItem(
        document="The XR-500 drone has a flight time of 35 minutes, maximum speed of 72 km/h, and a range of 10 km. It weighs 249 grams, making it exempt from registration in most jurisdictions. Camera resolution is 48MP with 4K video at 60fps.",
        answer="The XR-500 drone offers 35 minutes of flight time, reaches speeds up to 72 km/h, and has a 10 km range. At 249 grams, it falls below registration thresholds in most jurisdictions.",
        is_faithful=True, error_type="faithful", domain="technical",
    ),
    RAGItem(
        document="The XR-500 drone has a flight time of 35 minutes, maximum speed of 72 km/h, and a range of 10 km. It weighs 249 grams, making it exempt from registration in most jurisdictions. Camera resolution is 48MP with 4K video at 60fps.",
        answer="The XR-500 drone has a 45-minute flight time and can reach 95 km/h. Its 8K camera with 120fps video recording makes it the best drone in its class.",
        is_faithful=False, error_type="wrong_number", domain="technical",
    ),

    # --- HR Policy ---
    RAGItem(
        document="Employees accrue 15 days of PTO annually during their first 3 years. After 3 years, accrual increases to 20 days. After 7 years, accrual increases to 25 days. Unused PTO carries over up to a maximum of 10 days. PTO requests require manager approval 2 weeks in advance.",
        answer="New employees receive 15 PTO days annually for the first 3 years, increasing to 20 days after 3 years and 25 days after 7 years. Up to 10 unused days carry over. Requests need manager approval 2 weeks ahead.",
        is_faithful=True, error_type="faithful", domain="legal",
    ),
    RAGItem(
        document="Employees accrue 15 days of PTO annually during their first 3 years. After 3 years, accrual increases to 20 days. After 7 years, accrual increases to 25 days. Unused PTO carries over up to a maximum of 10 days. PTO requests require manager approval 2 weeks in advance.",
        answer="All employees receive unlimited PTO from day one. The company's generous policy allows full carryover of unused days with no cap.",
        is_faithful=False, error_type="scope_expansion", domain="legal",
    ),

    # --- Research Paper Abstract ---
    RAGItem(
        document="We present BERT-Verify, a fine-tuned model for claim verification achieving 89.3% accuracy on the FEVER dataset. The model was trained on 185,000 labeled examples with a learning rate of 2e-5 for 3 epochs. Inference time is 12ms per claim on an A100 GPU.",
        answer="BERT-Verify achieves 89.3% accuracy on the FEVER dataset. The model was trained on 185,000 labeled examples for 3 epochs with a learning rate of 2e-5.",
        is_faithful=True, error_type="faithful", domain="scientific",
    ),
    RAGItem(
        document="We present BERT-Verify, a fine-tuned model for claim verification achieving 89.3% accuracy on the FEVER dataset. The model was trained on 185,000 labeled examples with a learning rate of 2e-5 for 3 epochs. Inference time is 12ms per claim on an A100 GPU.",
        answer="BERT-Verify achieves state-of-the-art 95.1% accuracy on FEVER, surpassing all previous methods. The model also demonstrated strong zero-shot transfer to other verification benchmarks.",
        is_faithful=False, error_type="wrong_number", domain="scientific",
    ),

    # --- Meeting Notes ---
    RAGItem(
        document="Q2 planning meeting notes: The marketing budget was set at $2.3M for Q2. Three campaigns were approved: summer sale (June), back-to-school (August), and brand awareness (ongoing). The team agreed to hire 2 additional content writers. Next review is scheduled for April 15.",
        answer="The Q2 marketing budget is $2.3M, covering three approved campaigns: summer sale in June, back-to-school in August, and an ongoing brand awareness campaign. Two content writers will be hired.",
        is_faithful=True, error_type="faithful", domain="general",
    ),
    RAGItem(
        document="Q2 planning meeting notes: The marketing budget was set at $2.3M for Q2. Three campaigns were approved: summer sale (June), back-to-school (August), and brand awareness (ongoing). The team agreed to hire 2 additional content writers. Next review is scheduled for April 15.",
        answer="The Q2 marketing budget of $3.5M will fund five major campaigns. The team plans to hire a full creative department of 8 people to support the expanded initiative.",
        is_faithful=False, error_type="wrong_number", domain="general",
    ),

    # --- API Documentation ---
    RAGItem(
        document="The /users endpoint supports GET (list users, paginated, max 100 per page), POST (create user, requires email and name), and DELETE (soft-delete, requires admin role). Rate limit is 1000 requests per minute. Authentication via Bearer token.",
        answer="The /users endpoint supports GET for listing users (paginated, max 100/page), POST for creating users (requires email and name), and DELETE for soft-deleting users (admin role required). Rate limit: 1000 req/min with Bearer token auth.",
        is_faithful=True, error_type="faithful", domain="technical",
    ),
    RAGItem(
        document="The /users endpoint supports GET (list users, paginated, max 100 per page), POST (create user, requires email and name), and DELETE (soft-delete, requires admin role). Rate limit is 1000 requests per minute. Authentication via Bearer token.",
        answer="The /users endpoint supports all CRUD operations including PATCH for partial updates. Hard-delete is available for all authenticated users. The endpoint has no rate limiting for premium tier accounts.",
        is_faithful=False, error_type="fabricated_fact", domain="technical",
    ),

    # --- Climate Report ---
    RAGItem(
        document="Global average temperature in 2025 was 1.45°C above the pre-industrial baseline. Arctic sea ice extent reached a record low of 3.74 million km² in September. CO2 concentration averaged 427 ppm. The report notes that current pledges are insufficient to meet the 1.5°C target.",
        answer="In 2025, global temperatures reached 1.45°C above pre-industrial levels. Arctic sea ice hit a record low of 3.74 million km² in September, with CO2 at 427 ppm.",
        is_faithful=True, error_type="faithful", domain="scientific",
    ),
    RAGItem(
        document="Global average temperature in 2025 was 1.45°C above the pre-industrial baseline. Arctic sea ice extent reached a record low of 3.74 million km² in September. CO2 concentration averaged 427 ppm. The report notes that current pledges are insufficient to meet the 1.5°C target.",
        answer="Global temperatures in 2025 exceeded 2.0°C above pre-industrial levels for the first time. Scientists confirmed the 1.5°C target is now impossible to achieve under any scenario.",
        is_faithful=False, error_type="unsupported_claim", domain="scientific",
    ),
]


# ── Results ──────────────────────────────────────────────────────────

@dataclass
class RAGResult:
    mode: str
    total: int
    tp: int
    tn: int
    fp: int
    fn: int
    duration_seconds: float
    per_item: list[dict] = field(default_factory=list)

    @property
    def precision(self) -> float:
        d = self.tp + self.fp
        return self.tp / d if d else 0.0

    @property
    def recall(self) -> float:
        d = self.tp + self.fn
        return self.tp / d if d else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    def summary(self) -> str:
        return (
            f"RAG Grounding ({self.mode}) — {self.total} items\n"
            f"  Precision: {self.precision:.2%} | Recall: {self.recall:.2%} | F1: {self.f1:.2%}\n"
            f"  TP: {self.tp} | TN: {self.tn} | FP: {self.fp} | FN: {self.fn}\n"
            f"  Duration: {self.duration_seconds:.0f}s"
        )


class NoSearch:
    async def search(self, q: str, n: int = 5) -> list[SearchResult]:
        return []


async def _run_rag_mode(runner, items: list[RAGItem], mode: str) -> RAGResult:
    tp = tn = fp = fn = 0
    per_item = []
    start = time.monotonic()

    for i, item in enumerate(items):
        try:
            result = await runner.run(
                claim=item.answer,
                context=item.document,
                domain=item.domain,
                references=[],
            )
            detected = result.verdict in (Verdict.REFUTED, Verdict.PARTIAL, Verdict.DISPUTED)
            if not item.is_faithful and detected: tp += 1
            elif item.is_faithful and not detected: tn += 1
            elif item.is_faithful and detected: fp += 1
            else: fn += 1

            cls = "TP" if (not item.is_faithful and detected) else "TN" if (item.is_faithful and not detected) else "FP" if (item.is_faithful and detected) else "FN"
            print(f"  [{cls}] {mode} {i+1}/{len(items)}: {result.verdict.value} ({result.confidence:.2f}) | faithful={item.is_faithful} type={item.error_type}", flush=True)

            per_item.append({
                "domain": item.domain, "error_type": item.error_type,
                "is_faithful": item.is_faithful, "verdict": result.verdict.value,
                "confidence": result.confidence, "classification": cls,
                "failure_modes": [fm.type.value for fm in result.failure_modes],
            })
        except Exception as e:
            per_item.append({"error": str(e), "error_type": item.error_type})

    return RAGResult(
        mode=mode, total=len(items), tp=tp, tn=tn, fp=fp, fn=fn,
        duration_seconds=time.monotonic() - start, per_item=per_item,
    )


async def run_rag_benchmark(config: Config | None = None) -> dict:
    """Run RAG grounding benchmark."""
    if config is None:
        config = Config()
    config.validate()

    llm = ClaudeProvider(model=config.model, api_key=config.anthropic_api_key)
    search = NoSearch()
    iso = VerificationRunner(llm_provider=llm, search_provider=search, config=config)
    deb = DebateRunner(llm_provider=llm, search_provider=search, config=config)

    items = RAG_DATASET
    print(f"RAG Grounding Benchmark: {len(items)} items ({sum(1 for i in items if i.is_faithful)} faithful, {sum(1 for i in items if not i.is_faithful)} hallucinated)\n")

    print("--- Isolation Mode ---", flush=True)
    iso_result = await _run_rag_mode(iso, items, "ISO")

    print("\n--- Debate Mode ---", flush=True)
    deb_result = await _run_rag_mode(deb, items, "DEB")

    return {"isolation": iso_result, "debate": deb_result}
