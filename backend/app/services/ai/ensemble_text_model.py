"""CivicSense Phase 4A: Calibrated Lexical-Semantic Text Ensemble.

Combines deterministic keyword matching and semantic MiniLM classification via
calibrated probability pooling:
    P_ensemble = alpha * P_deterministic + (1 - alpha) * P_semantic
"""

from app.services.ai.semantic_text_classifier import SemanticTextClassifier
from app.services.ai.text_analyzer import PrototypeTextModel
from app.services.ai.text_interface import (
    CANONICAL_TEXT_CATEGORIES,
    TextInferenceOutcome,
    TextModel,
    TextModelMetadata,
    TextModelStatus,
    TextPrediction,
)


class EnsembleTextModel(TextModel):
    """Ensemble combining deterministic lexical rules and semantic transformer probabilities."""

    def __init__(
        self,
        deterministic_model: TextModel | None = None,
        semantic_model: TextModel | None = None,
        alpha: float = 0.5,
    ) -> None:
        if not (0.0 <= alpha <= 1.0):
            raise ValueError(f"Alpha must be in [0.0, 1.0], got {alpha}")

        self.deterministic_model = deterministic_model or PrototypeTextModel()
        self.semantic_model = semantic_model or SemanticTextClassifier()
        self.alpha = float(alpha)

        self._metadata = TextModelMetadata(
            model_name="ensemble_lexical_semantic_text",
            model_version="1.0.0",
            architecture_family="ensemble_linear_pooling",
            num_classes=6,
            canonical_classes=list(CANONICAL_TEXT_CATEGORIES),
            device="cpu",
            runtime="python_ensemble",
        )

    def predict(self, text: str) -> TextPrediction:
        """Ensemble classification via weighted probability pooling."""
        if not text or not text.strip():
            uniform = {
                c: round(1.0 / len(CANONICAL_TEXT_CATEGORIES), 4) for c in CANONICAL_TEXT_CATEGORIES
            }
            diff = round(1.0 - sum(uniform.values()), 4)
            uniform["Other"] = round(uniform["Other"] + diff, 4)
            return TextPrediction(
                predicted_category="Other",
                confidence=0.1667,
                probabilities=uniform,
                status=TextInferenceOutcome.EMPTY_OR_INVALID_INPUT,
                model_name=self._metadata.model_name,
                model_version=self._metadata.model_version,
                inference_metadata={"reason": "empty_input"},
            )

        det_pred = self.deterministic_model.predict(text)
        sem_pred = self.semantic_model.predict(text)

        # Fallback handling if one model is unavailable
        det_ok = det_pred.status in (
            TextInferenceOutcome.SUCCESS,
            TextInferenceOutcome.LOW_CONFIDENCE,
        )
        sem_ok = sem_pred.status in (
            TextInferenceOutcome.SUCCESS,
            TextInferenceOutcome.LOW_CONFIDENCE,
        )

        if det_ok and not sem_ok:
            effective_alpha = 1.0
        elif sem_ok and not det_ok:
            effective_alpha = 0.0
        elif not det_ok and not sem_ok:
            return TextPrediction(
                predicted_category="Other",
                confidence=0.1667,
                probabilities={c: 0.1667 for c in CANONICAL_TEXT_CATEGORIES},
                status=TextInferenceOutcome.MODEL_UNAVAILABLE,
                model_name=self._metadata.model_name,
                model_version=self._metadata.model_version,
                inference_metadata={"error": "Both sub-models unavailable"},
            )
        else:
            effective_alpha = self.alpha

        p_det = det_pred.probabilities
        p_sem = sem_pred.probabilities

        # Linear probability pooling
        probs: dict[str, float] = {}
        for c in CANONICAL_TEXT_CATEGORIES:
            probs[c] = (effective_alpha * p_det.get(c, 0.0)) + (
                (1.0 - effective_alpha) * p_sem.get(c, 0.0)
            )

        # Normalize strictly to sum to 1.0
        tot = sum(probs.values())
        if tot > 0:
            probs = {c: round(p / tot, 4) for c, p in probs.items()}
            diff = round(1.0 - sum(probs.values()), 4)
            probs["Other"] = round(probs["Other"] + diff, 4)

        best_cat = max(probs.keys(), key=lambda k: probs[k])
        conf = probs[best_cat]
        status = TextInferenceOutcome.SUCCESS
        if conf < 0.35:
            status = TextInferenceOutcome.LOW_CONFIDENCE

        return TextPrediction(
            predicted_category=best_cat,
            confidence=conf,
            probabilities=probs,
            status=status,
            model_name=self._metadata.model_name,
            model_version=self._metadata.model_version,
            inference_metadata={
                "effective_alpha": effective_alpha,
                "deterministic_pred": det_pred.predicted_category,
                "semantic_pred": sem_pred.predicted_category,
            },
        )

    def get_metadata(self) -> TextModelMetadata:
        return self._metadata

    def get_status(self) -> TextModelStatus:
        det_status = self.deterministic_model.get_status()
        sem_status = self.semantic_model.get_status()
        if det_status == TextModelStatus.READY or sem_status == TextModelStatus.READY:
            return TextModelStatus.READY
        return TextModelStatus.UNAVAILABLE
