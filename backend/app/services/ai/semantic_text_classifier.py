"""CivicSense Phase 4A: Semantic Text Classifier based on MiniLM-L6-v2.

Implements two classification strategies:
1. Strategy A: Zero-Shot Semantic Prototypes (Cosine Similarity against domain anchor texts)
2. Strategy B: MiniLM Embeddings + Multinomial Logistic Regression (Trained Head)
"""

import pickle
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

from app.services.ai.semantic_text_encoder import MiniLMTextEncoder
from app.services.ai.text_interface import (
    CANONICAL_TEXT_CATEGORIES,
    TextInferenceOutcome,
    TextModel,
    TextModelMetadata,
    TextModelStatus,
    TextPrediction,
)

DEFAULT_DOMAIN_ANCHORS: dict[str, str] = {
    "Pothole": (
        "A pothole, crater, pit, or hollow cavity in the asphalt road surface causing danger to "
        "vehicles."
    ),
    "Road Damage": (
        "Cracked pavement, broken asphalt surface, structural road cave-in, uneven road damage, "
        "or sinkhole."
    ),
    "Garbage": (
        "Accumulated garbage, overflowing trash bin, illegal dumping of waste, roadside litter, "
        "or rubbish debris."
    ),
    "Water Leakage": (
        "Water pipe leak, bursting pipeline, leaking potable water, flooding street, or "
        "continuous water flow."
    ),
    "Streetlight": (
        "Broken streetlight, dark street lamp, malfunctioning light pole, flickering light, or "
        "unlit streetlamp."
    ),
    "Other": (
        "General civic issue, damaged public facility, graffiti, broken public bench, or "
        "municipal issue."
    ),
}


class SemanticTextClassifier(TextModel):
    """Semantic text classifier combining MiniLM embeddings with a classification head."""

    DEFAULT_HEAD_PATH = Path("models/all_minilm_l6_v2/minilm_classifier_head.pkl")

    def __init__(
        self,
        encoder: MiniLMTextEncoder | None = None,
        head_path: str | Path | None = None,
        strategy: str = "trained_head",  # 'trained_head' or 'zero_shot_prototypes'
        temperature: float = 0.10,  # For zero-shot cosine softmax
        domain_anchors: dict[str, str] | None = None,
    ) -> None:
        self.encoder = encoder or MiniLMTextEncoder()
        self.head_path = Path(head_path) if head_path else self.DEFAULT_HEAD_PATH
        self.strategy = strategy
        self.temperature = max(0.01, temperature)
        self.domain_anchors = domain_anchors or dict(DEFAULT_DOMAIN_ANCHORS)

        self.classifier: LogisticRegression | None = None
        self._anchor_embeddings: dict[str, np.ndarray] | None = None

        self._metadata = TextModelMetadata(
            model_name="minilm_l6_v2_classifier",
            model_version="1.0.0",
            architecture_family="transformer_minilm",
            num_classes=6,
            canonical_classes=list(CANONICAL_TEXT_CATEGORIES),
            device="cpu",
            runtime="pytorch_cpu",
        )

        if self.strategy == "trained_head":
            self._load_head_offline()
        elif self.strategy == "zero_shot_prototypes":
            self._init_anchors()

    def _load_head_offline(self) -> None:
        """Load trained logistic regression head from disk."""
        if not self.head_path.exists():
            # Fall back to zero-shot if head not yet trained
            self.classifier = None
            return

        try:
            with open(self.head_path, "rb") as f:
                payload = pickle.load(f)
                self.classifier = payload["classifier"]
        except Exception:
            self.classifier = None

    def _init_anchors(self) -> None:
        """Precompute anchor embeddings for zero-shot prototype matching."""
        if self.encoder.status != TextModelStatus.READY:
            return

        self._anchor_embeddings = {}
        for cat in CANONICAL_TEXT_CATEGORIES:
            anchor_text = self.domain_anchors.get(cat, cat)
            emb = self.encoder.embed(anchor_text, normalize=True)
            self._anchor_embeddings[cat] = emb

    def fit_head(
        self,
        train_embeddings: np.ndarray,
        train_labels: list[str],
        c_reg: float = 1.0,
        class_weight: str | None = "balanced",
    ) -> None:
        """Train multinomial logistic regression head strictly on training embeddings."""
        self.classifier = LogisticRegression(
            C=c_reg,
            max_iter=1000,
            class_weight=class_weight,
            random_state=42,
            solver="lbfgs",
        )
        self.classifier.fit(train_embeddings, train_labels)

    def save_head(self, destination: str | Path | None = None) -> Path:
        """Save trained classification head to disk."""
        target = Path(destination) if destination else self.head_path
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as f:
            pickle.dump(
                {
                    "classifier": self.classifier,
                    "canonical_classes": CANONICAL_TEXT_CATEGORIES,
                    "strategy": "trained_head",
                },
                f,
            )
        self.head_path = target
        return target

    def predict(self, text: str) -> TextPrediction:
        """Classify text using semantic MiniLM representation."""
        if self.encoder.status != TextModelStatus.READY:
            return TextPrediction(
                predicted_category="Other",
                confidence=0.1667,
                probabilities={c: 0.1667 for c in CANONICAL_TEXT_CATEGORIES},
                status=TextInferenceOutcome.MODEL_UNAVAILABLE,
                model_name=self._metadata.model_name,
                model_version=self._metadata.model_version,
                inference_metadata={"error": self.encoder.load_error or "Encoder not available"},
            )

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

        try:
            emb = self.encoder.embed(text, normalize=True)

            if self.strategy == "trained_head" and self.classifier is not None:
                # Strategy B: Trained Logistic Regression Head
                raw_probs = self.classifier.predict_proba(emb.reshape(1, -1))[0]
                classes = list(self.classifier.classes_)
                probs: dict[str, float] = {}
                for c in CANONICAL_TEXT_CATEGORIES:
                    if c in classes:
                        probs[c] = float(raw_probs[classes.index(c)])
                    else:
                        probs[c] = 0.0
            else:
                # Strategy A: Zero-Shot Cosine Prototype Similarity
                if self._anchor_embeddings is None:
                    self._init_anchors()

                sims: dict[str, float] = {}
                for c in CANONICAL_TEXT_CATEGORIES:
                    a_emb = self._anchor_embeddings[c]
                    sims[c] = float(np.dot(emb, a_emb))

                # Softmax over temperature
                exp_sims = {c: np.exp(s / self.temperature) for c, s in sims.items()}
                sum_exp = sum(exp_sims.values())
                probs = {c: float(exp_sims[c] / sum_exp) for c in CANONICAL_TEXT_CATEGORIES}

            # Normalize to strictly sum to 1.0
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
                inference_metadata={"strategy": self.strategy},
            )
        except Exception as e:
            return TextPrediction(
                predicted_category="Other",
                confidence=0.1667,
                probabilities={c: 0.1667 for c in CANONICAL_TEXT_CATEGORIES},
                status=TextInferenceOutcome.INFERENCE_ERROR,
                model_name=self._metadata.model_name,
                model_version=self._metadata.model_version,
                inference_metadata={"error": str(e)},
            )

    def get_metadata(self) -> TextModelMetadata:
        return self._metadata

    def get_status(self) -> TextModelStatus:
        if self.encoder.status != TextModelStatus.READY:
            return self.encoder.status
        if self.strategy == "trained_head" and self.classifier is None:
            return TextModelStatus.UNAVAILABLE
        return TextModelStatus.READY
