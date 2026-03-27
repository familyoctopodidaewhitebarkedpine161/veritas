"""FaithBench integration — NAACL 2025 hallucination detection benchmark.

FaithBench tests hallucination DETECTORS (not models). Each sample has:
- source: the original document
- summary: an LLM-generated summary (may contain hallucinations)
- annotations: human labels marking hallucinated spans

We pass claim=summary, context=source to Veritas and check if it correctly
identifies hallucinated summaries as REFUTED and faithful ones as VERIFIED.

Dataset: https://github.com/vectara/FaithBench
Paper: FaithBench: A Diverse Hallucination Benchmark for Summarization by Modern LLMs (NAACL 2025)
"""

from __future__ import annotations

import asyncio
import glob
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from veritas.core.config import Config
from veritas.core.result import Verdict, VerificationResult
from veritas.orchestration.runner import VerificationRunner
from veritas.orchestration.debate_runner import DebateRunner
from veritas.providers.claude import ClaudeProvider
from veritas.providers.base import SearchResult


# ── Data Loading ─────────────────────────────────────────────────────

@dataclass
class FaithBenchItem:
    """A single FaithBench sample converted to Veritas format."""
    source: str           # Original document
    summary: str          # LLM-generated summary (claim to verify)
    is_hallucinated: bool # Human annotation: True if contains hallucination
    summarizer: str       # Which LLM generated the summary
    batch_id: int
    sample_id: int


def load_faithbench(
    data_dir: str = "/tmp/FaithBench/data_for_release",
    max_samples: int | None = None,
) -> list[FaithBenchItem]:
    """Load FaithBench dataset from local clone.

    Clone first: git clone https://github.com/vectara/FaithBench.git /tmp/FaithBench
    """
    items = []
    batch_files = sorted(glob.glob(f"{data_dir}/batch_*.json"))

    if not batch_files:
        raise FileNotFoundError(
            f"No FaithBench data found at {data_dir}. "
            "Clone the repo: git clone https://github.com/vectara/FaithBench.git /tmp/FaithBench"
        )

    for batch_file in batch_files:
        batch_id = int(Path(batch_file).stem.split("_")[1])
        with open(batch_file) as f:
            data = json.load(f)

        for sample in data["samples"]:
            # Determine if hallucinated: any annotation with "Unwanted" label
            is_hallucinated = any(
                "Unwanted" in label
                for ann in sample.get("annotations", [])
                for label in ann.get("label", [])
            )

            items.append(FaithBenchItem(
                source=sample["source"],
                summary=sample["summary"],
                is_hallucinated=is_hallucinated,
                summarizer=sample.get("metadata", {}).get("summarizer", "unknown"),
                batch_id=batch_id,
                sample_id=sample["sample_id"],
            ))

            if max_samples and len(items) >= max_samples:
                return items

    return items


# ── Results ──────────────────────────────────────────────────────────

@dataclass
class FaithBenchResult:
    """Results from a FaithBench evaluation."""
    mode: str  # "isolation" or "debate"
    total: int
    true_positives: int   # Correctly caught hallucinations (REFUTED when hallucinated)
    true_negatives: int   # Correctly passed faithful (VERIFIED when faithful)
    false_positives: int  # Incorrectly flagged faithful (REFUTED when faithful)
    false_negatives: int  # Missed hallucinations (VERIFIED when hallucinated)
    duration_seconds: float
    per_item: list[dict] = field(default_factory=list)

    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def balanced_accuracy(self) -> float:
        sensitivity = self.recall
        tn_total = self.true_negatives + self.false_positives
        specificity = self.true_negatives / tn_total if tn_total else 0.0
        return (sensitivity + specificity) / 2

    def summary(self) -> str:
        return (
            f"FaithBench ({self.mode}) — {self.total} samples\n"
            f"  Precision:  {self.precision:.2%}\n"
            f"  Recall:     {self.recall:.2%}\n"
            f"  F1:         {self.f1:.2%}\n"
            f"  Bal. Acc:   {self.balanced_accuracy:.2%}\n"
            f"  Duration:   {self.duration_seconds:.0f}s ({self.duration_seconds/self.total:.1f}s/item)"
        )


@dataclass
class FaithBenchComparison:
    """Side-by-side isolation vs debate on FaithBench."""
    isolation: FaithBenchResult
    debate: FaithBenchResult

    def summary(self) -> str:
        lines = [
            "# FaithBench Results: Isolation vs Debate",
            "",
            f"Samples: {self.isolation.total}",
            "",
            "| Metric | Isolation | Debate | Delta |",
            "|--------|-----------|--------|-------|",
            f"| Precision | {self.isolation.precision:.2%} | {self.debate.precision:.2%} | {self.isolation.precision - self.debate.precision:+.2%} |",
            f"| Recall | {self.isolation.recall:.2%} | {self.debate.recall:.2%} | {self.isolation.recall - self.debate.recall:+.2%} |",
            f"| F1 | {self.isolation.f1:.2%} | {self.debate.f1:.2%} | {self.isolation.f1 - self.debate.f1:+.2%} |",
            f"| Bal. Accuracy | {self.isolation.balanced_accuracy:.2%} | {self.debate.balanced_accuracy:.2%} | {self.isolation.balanced_accuracy - self.debate.balanced_accuracy:+.2%} |",
            f"| Duration | {self.isolation.duration_seconds:.0f}s | {self.debate.duration_seconds:.0f}s | {self.isolation.duration_seconds - self.debate.duration_seconds:+.0f}s |",
            "",
            "## Context: Published FaithBench Numbers (different models)",
            "",
            "| Detector | F1 | Bal. Acc | Model |",
            "|----------|-----|---------|-------|",
            "| GPT-4-Turbo | ~50% | ~53% | GPT-4-Turbo |",
            "| GPT-4o | ~52% | ~55% | GPT-4o |",
            "| o1-mini | ~54% | ~57% | o1-mini |",
            "| o3-mini | ~55% | ~58% | o3-mini |",
            f"| **Veritas (isolation)** | **{self.isolation.f1:.1%}** | **{self.isolation.balanced_accuracy:.1%}** | **Sonnet 4.6** |",
            f"| **Veritas (debate)** | **{self.debate.f1:.1%}** | **{self.debate.balanced_accuracy:.1%}** | **Sonnet 4.6** |",
            "",
            "Note: Published numbers use different models. Direct comparison shows method trends, not model differences.",
        ]
        return "\n".join(lines)

    def to_json(self) -> str:
        def _result_dict(r: FaithBenchResult) -> dict:
            return {
                "mode": r.mode, "total": r.total,
                "precision": round(r.precision, 4), "recall": round(r.recall, 4),
                "f1": round(r.f1, 4), "balanced_accuracy": round(r.balanced_accuracy, 4),
                "tp": r.true_positives, "tn": r.true_negatives,
                "fp": r.false_positives, "fn": r.false_negatives,
                "duration_s": round(r.duration_seconds, 1),
                "per_item": r.per_item,
            }
        return json.dumps({
            "isolation": _result_dict(self.isolation),
            "debate": _result_dict(self.debate),
        }, indent=2)


# ── Runner ───────────────────────────────────────────────────────────

class NoSearch:
    async def search(self, query: str, num_results: int = 5) -> list[SearchResult]:
        return []


def _classify(verdict: Verdict, is_hallucinated: bool) -> str:
    """Classify a prediction as TP/TN/FP/FN."""
    detected_as_bad = verdict in (Verdict.REFUTED, Verdict.PARTIAL, Verdict.DISPUTED)
    if is_hallucinated and detected_as_bad:
        return "tp"
    if not is_hallucinated and not detected_as_bad:
        return "tn"
    if not is_hallucinated and detected_as_bad:
        return "fp"
    return "fn"  # hallucinated but not detected


async def _run_mode(
    runner,
    items: list[FaithBenchItem],
    mode_name: str,
) -> FaithBenchResult:
    """Run all items through a single mode."""
    tp = tn = fp = fn = 0
    per_item = []
    start = time.monotonic()

    for i, item in enumerate(items):
        try:
            result = await runner.run(
                claim=item.summary,
                context=item.source,
                domain="general",
                references=[],
            )
            classification = _classify(result.verdict, item.is_hallucinated)
            if classification == "tp": tp += 1
            elif classification == "tn": tn += 1
            elif classification == "fp": fp += 1
            else: fn += 1

            per_item.append({
                "batch": item.batch_id, "sample": item.sample_id,
                "summarizer": item.summarizer,
                "is_hallucinated": item.is_hallucinated,
                "verdict": result.verdict.value,
                "confidence": result.confidence,
                "classification": classification,
                "failure_modes": [fm.type.value for fm in result.failure_modes],
            })

            mark = "TP" if classification == "tp" else "TN" if classification == "tn" else "FP" if classification == "fp" else "FN"
            print(f"  [{mark}] {mode_name} {i+1}/{len(items)}: {result.verdict.value} ({result.confidence:.2f}) | hall={item.is_hallucinated}", flush=True)

        except Exception as e:
            per_item.append({
                "batch": item.batch_id, "sample": item.sample_id, "error": str(e),
            })
            print(f"  [ER] {mode_name} {i+1}/{len(items)}: {e}", flush=True)

    duration = time.monotonic() - start
    return FaithBenchResult(
        mode=mode_name, total=len(items),
        true_positives=tp, true_negatives=tn,
        false_positives=fp, false_negatives=fn,
        duration_seconds=duration, per_item=per_item,
    )


async def run_faithbench(
    max_samples: int = 50,
    config: Config | None = None,
) -> FaithBenchComparison:
    """Run FaithBench benchmark comparing isolation vs debate."""
    if config is None:
        config = Config()
    config.validate()

    items = load_faithbench(max_samples=max_samples)
    print(f"Loaded {len(items)} FaithBench samples ({sum(1 for i in items if i.is_hallucinated)} hallucinated, {sum(1 for i in items if not i.is_hallucinated)} faithful)")

    llm = ClaudeProvider(model=config.model, api_key=config.anthropic_api_key)
    search = NoSearch()

    iso_runner = VerificationRunner(llm_provider=llm, search_provider=search, config=config)
    deb_runner = DebateRunner(llm_provider=llm, search_provider=search, config=config)

    print("\n--- Isolation Mode ---", flush=True)
    iso_result = await _run_mode(iso_runner, items, "ISO")

    print("\n--- Debate Mode ---", flush=True)
    deb_result = await _run_mode(deb_runner, items, "DEB")

    return FaithBenchComparison(isolation=iso_result, debate=deb_result)
