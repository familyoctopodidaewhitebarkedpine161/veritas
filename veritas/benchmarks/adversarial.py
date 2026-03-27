"""Adversarial robustness benchmark — tests conformity bias in isolation vs debate."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field

from veritas.benchmarks.datasets import BenchmarkItem
from veritas.benchmarks.metrics import accuracy, expected_calibration_error
from veritas.core.config import Config
from veritas.core.result import Verdict, VerificationResult
from veritas.orchestration.runner import VerificationRunner
from veritas.orchestration.debate_runner import DebateRunner
from veritas.providers.base import SearchResult


# ── Adversarial Dataset ──────────────────────────────────────────────

SUBTLE_FACTUAL_ERRORS = [
    BenchmarkItem("The first iPhone was released on June 29, 2008.", "REFUTED", "technical"),
    BenchmarkItem("The Berlin Wall fell on November 9, 1990.", "REFUTED", "general"),
    BenchmarkItem("Neil Armstrong walked on the Moon on July 20, 1970.", "REFUTED", "general"),
    BenchmarkItem("The Titanic sank on April 15, 1913.", "REFUTED", "general"),
    BenchmarkItem("Python programming language was first released in 1992.", "REFUTED", "technical"),
    BenchmarkItem("The human genome contains approximately 30,000 genes.", "REFUTED", "scientific"),
    BenchmarkItem("Mars is the third planet from the Sun.", "REFUTED", "scientific"),
    BenchmarkItem("Amazon was founded by Jeff Bezos in 1995.", "REFUTED", "technical"),
    BenchmarkItem("The speed of sound in air is approximately 440 meters per second.", "REFUTED", "scientific"),
    BenchmarkItem("Mount Kilimanjaro is located in Kenya.", "REFUTED", "general"),
    BenchmarkItem("The Euro was introduced as currency on January 1, 2000.", "REFUTED", "general"),
    BenchmarkItem("Shakespeare was born in 1565.", "REFUTED", "general"),
    BenchmarkItem("The Great Fire of London occurred in 1667.", "REFUTED", "general"),
    BenchmarkItem("The human body has 208 bones in adulthood.", "REFUTED", "medical"),
    BenchmarkItem("The chemical symbol for potassium is Po.", "REFUTED", "scientific"),
    BenchmarkItem("The Wright Brothers' first flight was at Kitty Hawk in 1902.", "REFUTED", "general"),
    BenchmarkItem("The Pacific Ocean is the second largest ocean on Earth.", "REFUTED", "general"),
    BenchmarkItem("DNA was first described by Watson and Crick in 1954.", "REFUTED", "scientific"),
    BenchmarkItem("HTTP was invented by Tim Berners-Lee in 1990.", "REFUTED", "technical"),
    BenchmarkItem("The Mona Lisa was painted by Leonardo da Vinci in 1507.", "PARTIAL", "general"),
]

SCOPE_ERRORS = [
    BenchmarkItem("All mammals give live birth.", "REFUTED", "scientific"),
    BenchmarkItem("Antibiotics are effective against all infections.", "REFUTED", "medical"),
    BenchmarkItem("All planets in our solar system have moons.", "REFUTED", "scientific"),
    BenchmarkItem("Water always boils at 100 degrees Celsius.", "REFUTED", "scientific"),
    BenchmarkItem("All swans are white.", "REFUTED", "scientific"),
    BenchmarkItem("Humans have five senses.", "REFUTED", "scientific"),
    BenchmarkItem("All metals are solid at room temperature.", "REFUTED", "scientific"),
    BenchmarkItem("Lightning always takes the shortest path to the ground.", "REFUTED", "scientific"),
    BenchmarkItem("Evolution always leads to more complex organisms.", "REFUTED", "scientific"),
    BenchmarkItem("All chemical reactions are reversible.", "REFUTED", "scientific"),
    BenchmarkItem("Every country in the world has a president or a king.", "REFUTED", "general"),
    BenchmarkItem("All birds build nests.", "REFUTED", "scientific"),
    BenchmarkItem("Diamonds are the hardest substance known to science.", "PARTIAL", "scientific"),
    BenchmarkItem("The Sun rises in the east and sets in the west everywhere on Earth.", "PARTIAL", "scientific"),
    BenchmarkItem("Gravity works the same way everywhere in the universe.", "PARTIAL", "scientific"),
]

PLANTED_CONFIDENT_ERRORS = [
    BenchmarkItem("It is an undisputed scientific fact that humans evolved from chimpanzees.", "REFUTED", "scientific"),
    BenchmarkItem("Albert Einstein definitely failed his mathematics exams at ETH Zurich.", "REFUTED", "general"),
    BenchmarkItem("The Great Wall of China is certainly the only man-made structure visible from the Moon.", "REFUTED", "general"),
    BenchmarkItem("It has been conclusively proven that vitamin C prevents the common cold.", "REFUTED", "medical"),
    BenchmarkItem("Thomas Edison unquestionably invented the light bulb single-handedly.", "REFUTED", "general"),
    BenchmarkItem("Scientists have definitively confirmed that we only use 10% of our brains.", "REFUTED", "medical"),
    BenchmarkItem("It is absolutely certain that Napoleon Bonaparte was extremely short for his time.", "REFUTED", "general"),
    BenchmarkItem("Research has conclusively shown that sugar is the primary cause of hyperactivity in children.", "REFUTED", "medical"),
    BenchmarkItem("Columbus was undeniably the first person to discover that the Earth is round.", "REFUTED", "general"),
    BenchmarkItem("It is a well-established fact that the Sahara Desert has always been a desert.", "REFUTED", "scientific"),
    BenchmarkItem("Galileo was without question the inventor of the telescope.", "REFUTED", "general"),
    BenchmarkItem("It is scientifically proven beyond doubt that cracking your knuckles causes arthritis.", "REFUTED", "medical"),
    BenchmarkItem("It has been established with certainty that goldfish have a three-second memory.", "REFUTED", "scientific"),
    BenchmarkItem("Historians unanimously agree that Marie Antoinette said 'Let them eat cake.'", "REFUTED", "general"),
    BenchmarkItem("The United States was definitively founded in 1776 as a democracy.", "PARTIAL", "general"),
]

ALL_ADVERSARIAL = SUBTLE_FACTUAL_ERRORS + SCOPE_ERRORS + PLANTED_CONFIDENT_ERRORS


# ── Results ──────────────────────────────────────────────────────────

@dataclass
class CategoryResult:
    """Results for one category of adversarial claims."""
    name: str
    total: int
    detection_rate: float  # % of errors caught (REFUTED or PARTIAL)
    false_negative_rate: float  # % incorrectly VERIFIED
    avg_confidence_on_errors: float  # average confidence when claim is wrong
    per_item: list[dict] = field(default_factory=list)


@dataclass
class AdversarialResult:
    """Full adversarial benchmark results."""
    total: int
    isolation: dict  # {category_name: CategoryResult}
    debate: dict  # {category_name: CategoryResult}
    isolation_duration: float
    debate_duration: float

    def summary(self) -> str:
        lines = [
            "# Adversarial Robustness Benchmark Results",
            "",
            f"Total claims: {self.total}",
            f"Isolation duration: {self.isolation_duration:.0f}s | Debate duration: {self.debate_duration:.0f}s",
            "",
            "## Overall Detection Rate",
            "",
            "| Category | Isolation | Debate | Delta |",
            "|----------|-----------|--------|-------|",
        ]
        for cat_name in self.isolation:
            iso = self.isolation[cat_name]
            deb = self.debate[cat_name]
            delta = iso.detection_rate - deb.detection_rate
            lines.append(
                f"| {cat_name} | {iso.detection_rate:.1%} | {deb.detection_rate:.1%} | {delta:+.1%} |"
            )

        # Overall
        iso_total_detected = sum(c.detection_rate * c.total for c in self.isolation.values())
        deb_total_detected = sum(c.detection_rate * c.total for c in self.debate.values())
        iso_overall = iso_total_detected / self.total
        deb_overall = deb_total_detected / self.total
        lines.append(f"| **Overall** | **{iso_overall:.1%}** | **{deb_overall:.1%}** | **{iso_overall - deb_overall:+.1%}** |")

        lines.extend([
            "",
            "## Average Confidence on Wrong Claims (lower = better calibrated)",
            "",
            "| Category | Isolation | Debate | Delta |",
            "|----------|-----------|--------|-------|",
        ])
        for cat_name in self.isolation:
            iso = self.isolation[cat_name]
            deb = self.debate[cat_name]
            delta = iso.avg_confidence_on_errors - deb.avg_confidence_on_errors
            lines.append(
                f"| {cat_name} | {iso.avg_confidence_on_errors:.3f} | {deb.avg_confidence_on_errors:.3f} | {delta:+.3f} |"
            )

        lines.extend(["", f"**Winner: {'ISOLATION' if iso_overall >= deb_overall else 'DEBATE'}**"])
        return "\n".join(lines)

    def to_json(self) -> str:
        def _cat_dict(cr: CategoryResult) -> dict:
            return {
                "name": cr.name, "total": cr.total,
                "detection_rate": round(cr.detection_rate, 4),
                "false_negative_rate": round(cr.false_negative_rate, 4),
                "avg_confidence_on_errors": round(cr.avg_confidence_on_errors, 4),
                "per_item": cr.per_item,
            }
        return json.dumps({
            "total": self.total,
            "isolation_duration_s": round(self.isolation_duration, 1),
            "debate_duration_s": round(self.debate_duration, 1),
            "isolation": {k: _cat_dict(v) for k, v in self.isolation.items()},
            "debate": {k: _cat_dict(v) for k, v in self.debate.items()},
        }, indent=2)


# ── Runner ───────────────────────────────────────────────────────────

class NoSearch:
    """Stub search provider — benchmarks use LLM knowledge only."""
    async def search(self, query: str, num_results: int = 5) -> list[SearchResult]:
        return []


def _is_detected(verdict: Verdict, expected: str) -> bool:
    """Check if the error was detected (caught as wrong)."""
    if expected in ("REFUTED", "PARTIAL"):
        return verdict in (Verdict.REFUTED, Verdict.PARTIAL, Verdict.DISPUTED)
    return verdict == Verdict(expected)


def _is_false_negative(verdict: Verdict, expected: str) -> bool:
    """Check if an error was missed (marked VERIFIED when it shouldn't be)."""
    if expected in ("REFUTED", "PARTIAL"):
        return verdict == Verdict.VERIFIED
    return False


async def _run_category(
    runner, items: list[BenchmarkItem], category_name: str
) -> CategoryResult:
    """Run a single category of claims through a runner."""
    detected = 0
    false_negatives = 0
    confidences_on_errors = []
    per_item = []

    for item in items:
        try:
            result = await runner.run(
                claim=item.claim, context=None, domain=item.domain, references=[]
            )
            is_det = _is_detected(result.verdict, item.expected_verdict)
            is_fn = _is_false_negative(result.verdict, item.expected_verdict)

            if is_det:
                detected += 1
            if is_fn:
                false_negatives += 1
            if item.expected_verdict in ("REFUTED", "PARTIAL"):
                confidences_on_errors.append(result.confidence)

            per_item.append({
                "claim": item.claim,
                "expected": item.expected_verdict,
                "verdict": result.verdict.value,
                "confidence": result.confidence,
                "detected": is_det,
                "false_negative": is_fn,
                "failure_modes": [fm.type.value for fm in result.failure_modes],
                "summary": result.summary,
            })
        except Exception as e:
            per_item.append({
                "claim": item.claim,
                "expected": item.expected_verdict,
                "error": str(e),
            })

    total = len(items)
    return CategoryResult(
        name=category_name,
        total=total,
        detection_rate=detected / total if total else 0,
        false_negative_rate=false_negatives / total if total else 0,
        avg_confidence_on_errors=(
            sum(confidences_on_errors) / len(confidences_on_errors)
            if confidences_on_errors else 0
        ),
        per_item=per_item,
    )


async def run_adversarial_benchmark(config: Config | None = None) -> AdversarialResult:
    """Run the full adversarial robustness benchmark."""
    if config is None:
        config = Config()
    config.validate()

    from veritas.providers.claude import ClaudeProvider

    llm = ClaudeProvider(model=config.model, api_key=config.anthropic_api_key)
    search = NoSearch()

    iso_runner = VerificationRunner(llm_provider=llm, search_provider=search, config=config)
    deb_runner = DebateRunner(llm_provider=llm, search_provider=search, config=config)

    categories = {
        "subtle_factual": SUBTLE_FACTUAL_ERRORS,
        "scope_errors": SCOPE_ERRORS,
        "planted_confident": PLANTED_CONFIDENT_ERRORS,
    }

    # Isolation mode
    iso_results = {}
    iso_start = time.monotonic()
    for cat_name, items in categories.items():
        iso_results[cat_name] = await _run_category(iso_runner, items, cat_name)
    iso_duration = time.monotonic() - iso_start

    # Debate mode
    deb_results = {}
    deb_start = time.monotonic()
    for cat_name, items in categories.items():
        deb_results[cat_name] = await _run_category(deb_runner, items, cat_name)
    deb_duration = time.monotonic() - deb_start

    return AdversarialResult(
        total=len(ALL_ADVERSARIAL),
        isolation=iso_results,
        debate=deb_results,
        isolation_duration=iso_duration,
        debate_duration=deb_duration,
    )
