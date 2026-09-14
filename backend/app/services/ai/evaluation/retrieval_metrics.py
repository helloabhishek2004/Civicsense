"""Visual Retrieval Evaluation Scaffold.

Provides structured evaluation for CivicSense visual similarity quality.

Required metrics:
  - Precision@1, Precision@5
  - Recall@5
  - Pairwise ROC-AUC or PR-AUC
  - False-positive rate, False-negative rate
  - Similarity distribution for positive/negative pairs

Pair relationship types:
  1. SAME_PHYSICAL: Same physical issue (different photos of the same pothole)
  2. SAME_CATEGORY: Same category but different issue (two different potholes)
  3. DIFFERENT_CATEGORY: Different categories (pothole vs garbage)
  4. VISUALLY_SIMILAR: Visually similar but geographically distant
  5. SAME_ISSUE_DIFFERENT_VIEW: Different images of the same issue

This module requires labeled pairs to compute any metrics.
No metrics are computed without ground truth labels.

Usage:
    from app.services.ai.evaluation.retrieval_metrics import (
        PairLabel,
        RetrievalEvaluator,
        compute_pairwise_metrics,
    )

    evaluator = RetrievalEvaluator()
    evaluator.add_pair(
        anchor_id="img_001",
        candidate_id="img_002",
        similarity=0.85,
        label=PairLabel.SAME_PHYSICAL,
    )
    results = evaluator.compute()
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PairLabel(str, Enum):
    """Relationship type between two images."""

    SAME_PHYSICAL = "same_physical"
    SAME_CATEGORY = "same_category"
    DIFFERENT_CATEGORY = "different_category"
    VISUALLY_SIMILAR = "visually_similar"
    SAME_ISSUE_DIFFERENT_VIEW = "same_issue_different_view"


@dataclass
class EvalPair:
    """A labeled image pair with computed similarity."""

    anchor_id: str
    candidate_id: str
    similarity: float
    label: PairLabel


@dataclass
class RetrievalMetrics:
    """Computed retrieval evaluation metrics."""

    precision_at_1: float = 0.0
    precision_at_5: float = 0.0
    recall_at_5: float = 0.0
    roc_auc: float | None = None
    pr_auc: float | None = None
    false_positive_rate: float = 0.0
    false_negative_rate: float = 0.0
    total_pairs: int = 0
    positive_pairs: int = 0
    negative_pairs: int = 0
    mean_positive_similarity: float = 0.0
    mean_negative_similarity: float = 0.0
    std_positive_similarity: float = 0.0
    std_negative_similarity: float = 0.0
    positive_similarities: list[float] = field(default_factory=list)
    negative_similarities: list[float] = field(default_factory=list)


class RetrievalEvaluator:
    """Collects labeled pairs and computes retrieval metrics.

    No metrics are computed without explicit ground truth labels.
    """

    def __init__(self) -> None:
        self._pairs: list[EvalPair] = []

    def add_pair(
        self,
        anchor_id: str,
        candidate_id: str,
        similarity: float,
        label: PairLabel,
    ) -> None:
        """Add a labeled pair for evaluation."""
        self._pairs.append(EvalPair(
            anchor_id=anchor_id,
            candidate_id=candidate_id,
            similarity=similarity,
            label=label,
        ))

    def add_pairs_from_dicts(self, pairs: list[dict[str, Any]]) -> None:
        """Add pairs from a list of dicts with keys: anchor_id, candidate_id, similarity, label."""
        for p in pairs:
            self.add_pair(
                anchor_id=p["anchor_id"],
                candidate_id=p["candidate_id"],
                similarity=p["similarity"],
                label=PairLabel(p["label"]),
            )

    def compute(self) -> RetrievalMetrics:
        """Compute all retrieval metrics from labeled pairs.

        Returns RetrievalMetrics. If fewer than 2 pairs exist, returns zero metrics.
        """
        if len(self._pairs) < 2:
            return RetrievalMetrics(total_pairs=len(self._pairs))

        positive_sims = [p.similarity for p in self._pairs if self._is_positive(p.label)]
        negative_sims = [p.similarity for p in self._pairs if not self._is_positive(p.label)]

        metrics = RetrievalMetrics(
            total_pairs=len(self._pairs),
            positive_pairs=len(positive_sims),
            negative_pairs=len(negative_sims),
        )

        if positive_sims:
            metrics.mean_positive_similarity = sum(positive_sims) / len(positive_sims)
            metrics.positive_similarities = positive_sims
            if len(positive_sims) > 1:
                metrics.std_positive_similarity = _stddev(positive_sims)

        if negative_sims:
            metrics.mean_negative_similarity = sum(negative_sims) / len(negative_sims)
            metrics.negative_similarities = negative_sims
            if len(negative_sims) > 1:
                metrics.std_negative_similarity = _stddev(negative_sims)

        # Precision@1: fraction of top-1 matches that are positive
        sorted_pairs = sorted(self._pairs, key=lambda p: p.similarity, reverse=True)
        if sorted_pairs:
            metrics.precision_at_1 = 1.0 if self._is_positive(sorted_pairs[0].label) else 0.0

        # Precision@5 and Recall@5
        top_5 = sorted_pairs[:5]
        if top_5:
            tp_at_5 = sum(1 for p in top_5 if self._is_positive(p.label))
            metrics.precision_at_5 = tp_at_5 / len(top_5)
            if metrics.positive_pairs > 0:
                metrics.recall_at_5 = tp_at_5 / metrics.positive_pairs

        # ROC-AUC (simple trapezoidal approximation)
        if positive_sims and negative_sims:
            metrics.roc_auc = _compute_roc_auc(positive_sims, negative_sims)

        # False positive/negative rates at threshold 0.5
        if positive_sims and negative_sims:
            threshold = 0.5
            fp = sum(1 for s in negative_sims if s >= threshold)
            fn = sum(1 for s in positive_sims if s < threshold)
            metrics.false_positive_rate = fp / len(negative_sims) if negative_sims else 0.0
            metrics.false_negative_rate = fn / len(positive_sims) if positive_sims else 0.0

        return metrics

    @staticmethod
    def _is_positive(label: PairLabel) -> bool:
        """Positive pairs: same physical issue or same issue different view."""
        return label in (PairLabel.SAME_PHYSICAL, PairLabel.SAME_ISSUE_DIFFERENT_VIEW)


def _stddev(values: list[float]) -> float:
    """Population standard deviation."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    var = sum((x - mean) ** 2 for x in values) / len(values)
    return math.sqrt(var)


def _compute_roc_auc(positive_sims: list[float], negative_sims: list[float]) -> float:
    """Simple ROC-AUC via trapezoidal rule."""
    all_sims = sorted(set(positive_sims + negative_sims), reverse=True)
    if not all_sims:
        return 0.5

    tp_total = len(positive_sims)
    fp_total = len(negative_sims)
    if tp_total == 0 or fp_total == 0:
        return 0.5

    auc = 0.0
    prev_tpr = 0.0
    prev_fpr = 0.0

    for threshold in all_sims:
        tp = sum(1 for s in positive_sims if s >= threshold)
        fp = sum(1 for s in negative_sims if s >= threshold)
        tpr = tp / tp_total
        fpr = fp / fp_total
        auc += (fpr - prev_fpr) * (tpr + prev_tpr) / 2.0
        prev_tpr = tpr
        prev_fpr = fpr

    return max(0.0, min(1.0, auc))


def compute_pairwise_metrics(pairs: list[dict[str, Any]]) -> RetrievalMetrics:
    """Convenience function: compute metrics from a list of pair dicts."""
    evaluator = RetrievalEvaluator()
    evaluator.add_pairs_from_dicts(pairs)
    return evaluator.compute()
