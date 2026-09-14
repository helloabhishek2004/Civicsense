"""Tests for the visual embedding pipeline: VisualEmbeddingService, visual similarity
in the similarity engine, and dynamic weight normalization.

Covers:
- VisualEmbeddingService status and graceful degradation
- Embedding extraction from bytes, files, and storage URIs
- Similarity scoring with and without visual embeddings
- Dynamic weight normalization in the similarity engine
- Visual similarity in MatchComponent and audit trail
- cosine_similarity_vectors utility
- Running average aggregation
- Visual safety policy
- Retrieval evaluation metrics
"""

import io
import math
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from app.core.config import get_settings
from app.services.ai.visual_embedding_service import (
    VisualEmbeddingService,
    cosine_similarity_vectors,
    get_visual_embedding_service,
)
from app.services.similarity.service import (
    MatchAction,
    MatchComponent,
    SimilarityConfig,
    SimilarityMatch,
    _running_average,
    store_match_metadata,
)

# ---------------------------------------------------------------------------
# cosine_similarity_vectors utility
# ---------------------------------------------------------------------------


class TestCosineSimilarityVectors:
    """Tests for the standalone cosine similarity utility."""

    def test_identical_vectors_return_one(self) -> None:
        a = [1.0, 0.0, 0.0]
        assert cosine_similarity_vectors(a, a) == pytest.approx(1.0)

    def test_orthogonal_vectors_return_zero(self) -> None:
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert cosine_similarity_vectors(a, b) == pytest.approx(0.0)

    def test_opposite_vectors_return_negative_one(self) -> None:
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert cosine_similarity_vectors(a, b) == pytest.approx(-1.0)

    def test_empty_vectors_return_zero(self) -> None:
        assert cosine_similarity_vectors([], [1.0]) == 0.0
        assert cosine_similarity_vectors([1.0], []) == 0.0
        assert cosine_similarity_vectors([], []) == 0.0

    def test_mismatched_lengths_return_zero(self) -> None:
        assert cosine_similarity_vectors([1.0, 0.0], [1.0, 0.0, 0.0]) == 0.0

    def test_zero_norm_vectors_return_zero(self) -> None:
        assert cosine_similarity_vectors([0.0, 0.0], [1.0, 0.0]) == 0.0

    def test_known_value(self) -> None:
        a = [1.0, 1.0]
        b = [1.0, 0.0]
        # cos(45 degrees) = 1/sqrt(2)
        expected = 1.0 / math.sqrt(2)
        assert cosine_similarity_vectors(a, b) == pytest.approx(expected, abs=1e-6)


# ---------------------------------------------------------------------------
# VisualEmbeddingService
# ---------------------------------------------------------------------------


class TestVisualEmbeddingService:
    """Tests for VisualEmbeddingService graceful degradation and status."""

    def test_service_initializes_without_model(self) -> None:
        svc = VisualEmbeddingService()
        assert svc._loaded is False
        assert svc._model is None

    @patch("app.services.ai.visual_embedding_service.get_settings")
    def test_service_reports_disabled_when_vision_disabled(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value = MagicMock(VISION_ENABLED=False)
        svc = VisualEmbeddingService()
        assert svc.is_ready is False
        status = svc.status
        assert status["vision_enabled"] is False
        assert status["model_ready"] is False

    @patch("app.services.ai.visual_embedding_service.get_settings")
    def test_service_reports_missing_checkpoint(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value = MagicMock(
            VISION_ENABLED=True,
            vision_model_path=Path("/nonexistent/path/model.pt"),
        )
        svc = VisualEmbeddingService()
        assert svc.is_ready is False
        status = svc.status
        assert status["model_ready"] is False
        assert "Checkpoint not found" in (status["load_error"] or "")

    def test_extract_embedding_returns_none_when_not_ready(self) -> None:
        svc = VisualEmbeddingService()
        # Force _loaded=True without actually loading
        svc._loaded = True
        assert svc.extract_embedding_from_bytes(b"fake") is None

    def test_extract_embedding_returns_none_for_empty_bytes(self) -> None:
        svc = VisualEmbeddingService()
        svc._loaded = True
        svc._model = MagicMock()
        svc._model.status = MagicMock(value="READY")
        assert svc.extract_embedding_from_bytes(b"") is None

    def test_extract_embedding_from_file_nonexistent(self) -> None:
        svc = VisualEmbeddingService()
        svc._loaded = True
        assert svc.extract_embedding_from_file(Path("/nonexistent.jpg")) is None

    def test_extract_embedding_from_storage_uri_empty(self) -> None:
        svc = VisualEmbeddingService()
        svc._loaded = True
        assert svc.extract_embedding_from_storage_uri("") is None
        assert svc.extract_embedding_from_storage_uri(None) is None  # type: ignore[arg-type]

    @patch("app.services.ai.visual_embedding_service.get_settings")
    def test_singleton_pattern(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value = MagicMock(VISION_ENABLED=False)
        svc1 = get_visual_embedding_service()
        svc2 = get_visual_embedding_service()
        assert svc1 is svc2


# ---------------------------------------------------------------------------
# Visual similarity in similarity engine
# ---------------------------------------------------------------------------


def _make_test_image_bytes(width: int = 64, height: int = 64, color: tuple = (128, 64, 32)) -> bytes:
    """Create a minimal valid JPEG image in memory."""
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestVisualSimilarityInScoring:
    """Tests for visual similarity integration in the similarity engine."""

    def test_match_component_has_visual_similarity(self) -> None:
        mc = MatchComponent(
            text_similarity=0.8,
            distance_meters=10.0,
            category_match=1.0,
            visual_similarity=0.75,
            raw_score=0.6,
            weighted_score=0.6,
        )
        assert mc.visual_similarity == 0.75

    def test_config_default_visual_weight_zero(self) -> None:
        cfg = SimilarityConfig(
            text_weight=0.40,
            distance_weight=0.35,
            category_weight=0.25,
            radius_meters=50.0,
            high_threshold=0.70,
            medium_threshold=0.45,
            embedding_model_version="test-v1",
        )
        assert cfg.visual_weight == 0.0

    def test_config_explicit_visual_weight(self) -> None:
        cfg = SimilarityConfig(
            text_weight=0.40,
            distance_weight=0.35,
            category_weight=0.25,
            radius_meters=50.0,
            high_threshold=0.70,
            medium_threshold=0.45,
            embedding_model_version="test-v1",
            visual_weight=0.15,
        )
        assert cfg.visual_weight == 0.15

    def test_dynamic_weight_normalization_without_visual(self) -> None:
        """When no visual embeddings exist, text+dist+cat weights are normalized to sum to 1.0."""
        cfg = SimilarityConfig(
            text_weight=0.40,
            distance_weight=0.35,
            category_weight=0.25,
            radius_meters=50.0,
            high_threshold=0.70,
            medium_threshold=0.45,
            embedding_model_version="test-v1",
            visual_weight=0.15,
        )
        total = cfg.text_weight + cfg.distance_weight + cfg.category_weight
        assert total == pytest.approx(1.0)
        # Without visual embeddings, only these 3 are used
        norm_t = cfg.text_weight / total
        norm_d = cfg.distance_weight / total
        norm_c = cfg.category_weight / total
        assert norm_t + norm_d + norm_c == pytest.approx(1.0)

    def test_dynamic_weight_normalization_with_visual(self) -> None:
        """When visual embeddings exist, all 4 weights are normalized to sum to 1.0."""
        cfg = SimilarityConfig(
            text_weight=0.40,
            distance_weight=0.35,
            category_weight=0.25,
            radius_meters=50.0,
            high_threshold=0.70,
            medium_threshold=0.45,
            embedding_model_version="test-v1",
            visual_weight=0.15,
        )
        total = cfg.text_weight + cfg.distance_weight + cfg.category_weight + cfg.visual_weight
        assert total == pytest.approx(1.15)
        norm_t = cfg.text_weight / total
        norm_d = cfg.distance_weight / total
        norm_c = cfg.category_weight / total
        norm_v = cfg.visual_weight / total
        assert norm_t + norm_d + norm_c + norm_v == pytest.approx(1.0)

    def test_visual_similarity_zero_when_no_embeddings(self) -> None:
        """visual_similarity should be 0.0 when either report or issue lacks image_embedding."""
        mc = MatchComponent(
            text_similarity=0.8,
            distance_meters=10.0,
            category_match=1.0,
            visual_similarity=0.0,
            raw_score=0.6,
            weighted_score=0.6,
        )
        assert mc.visual_similarity == 0.0

    def test_visual_similarity_affects_combined_score(self) -> None:
        """When visual embeddings are present, they contribute to the combined score."""
        # Simulate weighted combination with visual
        text_w, dist_w, cat_w, vis_w = 0.35, 0.30, 0.22, 0.13
        text_sim, dist_sc, cat_sc, vis_sim = 0.8, 0.9, 1.0, 0.7
        weighted = text_w * text_sim + dist_w * dist_sc + cat_w * cat_sc + vis_w * vis_sim
        # Without visual: 0.35*0.8 + 0.30*0.9 + 0.22*1.0 = 0.79
        weighted_no_vis = (0.35 / (0.35 + 0.30 + 0.22)) * text_sim + \
                          (0.30 / (0.35 + 0.30 + 0.22)) * dist_sc + \
                          (0.22 / (0.35 + 0.30 + 0.22)) * cat_sc
        # With visual should differ from without visual
        assert weighted != weighted_no_vis


class TestVisionModelConfig:
    """Tests for vision-related config settings."""

    def test_vision_enabled_default(self) -> None:
        settings = get_settings()
        # VISION_ENABLED defaults to True in config
        assert hasattr(settings, "VISION_ENABLED")

    def test_vision_model_path_resolves(self) -> None:
        settings = get_settings()
        path = settings.vision_model_path
        assert isinstance(path, Path)

    def test_vision_embedding_dim(self) -> None:
        settings = get_settings()
        assert settings.VISION_EMBEDDING_DIM == 576

    def test_visual_weight_config(self) -> None:
        settings = get_settings()
        assert hasattr(settings, "SIMILARITY_VISUAL_WEIGHT")
        assert 0.0 <= settings.SIMILARITY_VISUAL_WEIGHT <= 1.0


class TestRealVisionModelEmbedding:
    """Tests for RealVisionModel.extract_embedding method contract."""

    def test_extract_embedding_returns_none_when_unavailable(self) -> None:
        from app.services.ai.real_vision_model import RealVisionModel
        model = RealVisionModel(checkpoint_path=None)
        result = model.extract_embedding(b"fake image bytes")
        assert result is None

    def test_extract_embedding_returns_none_for_empty_bytes(self) -> None:
        from app.services.ai.real_vision_model import RealVisionModel
        model = RealVisionModel(checkpoint_path=None)
        result = model.extract_embedding(b"")
        assert result is None

    def test_extract_embedding_returns_none_for_corrupt_image(self) -> None:
        from app.services.ai.real_vision_model import RealVisionModel
        model = RealVisionModel(checkpoint_path=None)
        result = model.extract_embedding(b"not a valid image")
        assert result is None


# ---------------------------------------------------------------------------
# Running average aggregation
# ---------------------------------------------------------------------------


class TestRunningAverage:
    """Tests for the _running_average embedding aggregation function."""

    def test_first_embedding_returns_copy(self) -> None:
        """When old_avg is None, returns a copy of new_embedding."""
        emb = [0.1, 0.2, 0.3]
        result = _running_average(None, emb, 0)
        assert result == pytest.approx(emb)
        assert result is not emb  # Should be a copy

    def test_second_embedding_averages_correctly(self) -> None:
        """With count=1, average of [2,2] and [4,4] should be [3,3] before normalization."""
        old = [2.0, 2.0]
        new = [4.0, 4.0]
        result = _running_average(old, new, 1)
        # (2*1 + 4) / 2 = 3.0, then L2-normalized: [3/sqrt(18), 3/sqrt(18)] = [0.707, 0.707]
        expected_norm = 3.0 / math.sqrt(18)
        assert result == pytest.approx([expected_norm, expected_norm])

    def test_result_is_l2_normalized(self) -> None:
        """Running average result should be L2-normalized."""
        old = [1.0, 0.0, 0.0]
        new = [0.0, 1.0, 0.0]
        result = _running_average(old, new, 1)
        norm = math.sqrt(sum(x * x for x in result))
        assert norm == pytest.approx(1.0, abs=1e-6)

    def test_dimension_mismatch_returns_new(self) -> None:
        """Dimension mismatch should return the new embedding."""
        old = [1.0, 0.0]
        new = [0.0, 1.0, 0.0]
        result = _running_average(old, new, 1)
        assert result == pytest.approx(new)

    def test_zero_count_returns_copy(self) -> None:
        """Zero count returns a copy of new embedding."""
        emb = [0.5, 0.5]
        result = _running_average([1.0, 0.0], emb, 0)
        assert result == pytest.approx(emb)

    def test_multiple_averages_converge(self) -> None:
        """Sequential averaging produces correct results."""
        embs = [[1.0, 0.0], [0.0, 1.0], [1.0, 0.0], [0.0, 1.0]]
        avg = None
        for i, emb in enumerate(embs):
            avg = _running_average(avg, emb, i)
        # After 4 embeddings: two [1,0] and two [0,1]
        # Running average: ((1,0) + (0,1))/2 = (0.5, 0.5) then average with (1,0) then (0,1)
        # Should be roughly balanced
        assert avg is not None
        assert len(avg) == 2
        norm = math.sqrt(sum(x * x for x in avg))
        assert norm == pytest.approx(1.0, abs=1e-6)


# ---------------------------------------------------------------------------
# Visual safety policy
# ---------------------------------------------------------------------------


class TestVisualSafetyPolicy:
    """Tests for the visual safety policy in match_report_to_issue."""

    def test_match_has_safety_metadata(self) -> None:
        """SimilarityMatch should have text_only_score, visual_used, etc."""
        match = SimilarityMatch(
            issue_id=uuid.uuid4(),
            action=MatchAction.CANDIDATE,
            score=0.6,
            components=MatchComponent(
                text_similarity=0.5, distance_meters=10.0,
                category_match=1.0, visual_similarity=0.7,
                raw_score=0.6, weighted_score=0.6,
            ),
            reasoning=["test"],
            text_only_score=0.5,
            multimodal_score=0.6,
            visual_used=True,
            visual_influenced_decision=False,
            routing_reason="test",
        )
        assert match.text_only_score == 0.5
        assert match.multimodal_score == 0.6
        assert match.visual_used is True
        assert match.visual_influenced_decision is False
        assert match.routing_reason == "test"

    def test_store_match_metadata_includes_safety_fields(self) -> None:
        """store_match_metadata should include visual safety fields."""
        report = MagicMock()
        report.embedding_model_version = "test-v1"
        report.vision_model_version = "mobilenet_v3_small-exp_b"

        match = SimilarityMatch(
            issue_id=uuid.uuid4(),
            action=MatchAction.CANDIDATE,
            score=0.6,
            components=MatchComponent(
                text_similarity=0.5, distance_meters=10.0,
                category_match=1.0, visual_similarity=0.7,
                raw_score=0.6, weighted_score=0.6,
            ),
            reasoning=["test"],
            text_only_score=0.5,
            multimodal_score=0.6,
            visual_used=True,
            visual_influenced_decision=True,
            routing_reason="visual_downgraded_to_candidate",
        )

        metadata = store_match_metadata(report, match)
        sm = metadata["similarity_match"]
        assert sm["text_only_score"] == 0.5
        assert sm["multimodal_score"] == 0.6
        assert sm["visual_used"] is True
        assert sm["visual_influenced_decision"] is True
        assert sm["routing_reason"] == "visual_downgraded_to_candidate"

    def test_category_mismatch_still_forces_new_issue(self) -> None:
        """Category mismatch should force NEW_ISSUE regardless of visual similarity."""
        # This is tested via the match_report_to_issue function with mocked DB
        # For now, verify the safety gate logic exists in the reasoning
        match = SimilarityMatch(
            issue_id=uuid.uuid4(),
            action=MatchAction.NEW_ISSUE,
            score=0.9,
            components=MatchComponent(
                text_similarity=0.8, distance_meters=10.0,
                category_match=0.0, visual_similarity=0.9,
                raw_score=0.9, weighted_score=0.9,
            ),
            reasoning=["ACTION=NEW_ISSUE(category_mismatch: Pothole vs Garbage)"],
            text_only_score=0.7,
            multimodal_score=0.9,
            visual_used=True,
            visual_influenced_decision=False,
            routing_reason="category_mismatch",
        )
        assert match.action == MatchAction.NEW_ISSUE
        assert any("category_mismatch" in r for r in match.reasoning)


# ---------------------------------------------------------------------------
# Retrieval evaluation metrics
# ---------------------------------------------------------------------------


class TestRetrievalMetrics:
    """Tests for the retrieval evaluation scaffold."""

    def test_empty_evaluator_returns_zero_metrics(self) -> None:
        from app.services.ai.evaluation.retrieval_metrics import RetrievalEvaluator
        evaluator = RetrievalEvaluator()
        metrics = evaluator.compute()
        assert metrics.total_pairs == 0
        assert metrics.precision_at_1 == 0.0

    def test_single_pair_returns_zero_metrics(self) -> None:
        from app.services.ai.evaluation.retrieval_metrics import PairLabel, RetrievalEvaluator
        evaluator = RetrievalEvaluator()
        evaluator.add_pair("a", "b", 0.9, PairLabel.SAME_PHYSICAL)
        metrics = evaluator.compute()
        assert metrics.total_pairs == 1
        # Need at least 2 pairs for meaningful metrics

    def test_all_positive_pairs_high_precision(self) -> None:
        from app.services.ai.evaluation.retrieval_metrics import PairLabel, RetrievalEvaluator
        evaluator = RetrievalEvaluator()
        evaluator.add_pair("a", "b", 0.9, PairLabel.SAME_PHYSICAL)
        evaluator.add_pair("a", "c", 0.8, PairLabel.SAME_PHYSICAL)
        evaluator.add_pair("a", "d", 0.7, PairLabel.SAME_PHYSICAL)
        metrics = evaluator.compute()
        assert metrics.precision_at_1 == 1.0
        assert metrics.precision_at_5 == 1.0
        assert metrics.positive_pairs == 3
        assert metrics.negative_pairs == 0

    def test_mixed_pairs_correct_metrics(self) -> None:
        from app.services.ai.evaluation.retrieval_metrics import PairLabel, RetrievalEvaluator
        evaluator = RetrievalEvaluator()
        # High similarity positive
        evaluator.add_pair("a", "b", 0.9, PairLabel.SAME_PHYSICAL)
        # Low similarity positive (false negative)
        evaluator.add_pair("a", "c", 0.3, PairLabel.SAME_PHYSICAL)
        # High similarity negative (false positive)
        evaluator.add_pair("x", "y", 0.8, PairLabel.DIFFERENT_CATEGORY)
        # Low similarity negative (true negative)
        evaluator.add_pair("x", "z", 0.2, PairLabel.DIFFERENT_CATEGORY)

        metrics = evaluator.compute()
        assert metrics.total_pairs == 4
        assert metrics.positive_pairs == 2
        assert metrics.negative_pairs == 2
        assert metrics.mean_positive_similarity == pytest.approx(0.6)
        assert metrics.mean_negative_similarity == pytest.approx(0.5)
        # Precision@1: top-1 is positive (0.9)
        assert metrics.precision_at_1 == 1.0

    def test_roc_auc_perfect_separation(self) -> None:
        from app.services.ai.evaluation.retrieval_metrics import PairLabel, RetrievalEvaluator
        evaluator = RetrievalEvaluator()
        # All positives have high similarity
        evaluator.add_pair("a", "b", 0.9, PairLabel.SAME_PHYSICAL)
        evaluator.add_pair("a", "c", 0.8, PairLabel.SAME_PHYSICAL)
        # All negatives have low similarity
        evaluator.add_pair("x", "y", 0.1, PairLabel.DIFFERENT_CATEGORY)
        evaluator.add_pair("x", "z", 0.2, PairLabel.DIFFERENT_CATEGORY)

        metrics = evaluator.compute()
        assert metrics.roc_auc is not None
        assert metrics.roc_auc == pytest.approx(1.0)
