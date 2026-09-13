"""CivicSense Phase 4A: TF-IDF + Logistic Regression Text Control Baseline.

Implements a conventional, lightweight n-gram TF-IDF vectorizer paired with
multinomial logistic regression.
"""

import pickle
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from app.services.ai.text_interface import (
    CANONICAL_TEXT_CATEGORIES,
    TextInferenceOutcome,
    TextModel,
    TextModelMetadata,
    TextModelStatus,
    TextPrediction,
)


class TFIDFTextClassifier(TextModel):
    """Conventional TF-IDF + Logistic Regression text classification baseline."""

    DEFAULT_MODEL_PATH = Path("models/tfidf_baseline/tfidf_classifier.pkl")

    def __init__(
        self,
        model_path: str | Path | None = None,
        vectorizer: TfidfVectorizer | None = None,
        classifier: LogisticRegression | None = None,
    ) -> None:
        self.model_path = Path(model_path) if model_path else self.DEFAULT_MODEL_PATH
        self.vectorizer = vectorizer
        self.classifier = classifier
        self._status = TextModelStatus.UNAVAILABLE
        self._load_error: str | None = None

        self._metadata = TextModelMetadata(
            model_name="tfidf_logistic_regression",
            model_version="1.0.0",
            architecture_family="tfidf_linear",
            num_classes=6,
            canonical_classes=list(CANONICAL_TEXT_CATEGORIES),
            device="cpu",
            runtime="scikit_learn",
        )

        if self.vectorizer is not None and self.classifier is not None:
            self._status = TextModelStatus.READY
        else:
            self._load_offline()

    def _load_offline(self) -> None:
        """Load trained vectorizer and classifier from disk if available."""
        if not self.model_path.exists():
            self._status = TextModelStatus.UNAVAILABLE
            self._load_error = f"Model file not found: {self.model_path}"
            return

        try:
            with open(self.model_path, "rb") as f:
                payload = pickle.load(f)
                self.vectorizer = payload["vectorizer"]
                self.classifier = payload["classifier"]
            self._status = TextModelStatus.READY
            self._load_error = None
        except Exception as e:
            self._status = TextModelStatus.LOADING_FAILED
            self._load_error = str(e)
            self.vectorizer = None
            self.classifier = None

    def save(self, destination: str | Path | None = None) -> Path:
        """Save trained pipeline to disk."""
        target = Path(destination) if destination else self.model_path
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "wb") as f:
            pickle.dump(
                {
                    "vectorizer": self.vectorizer,
                    "classifier": self.classifier,
                    "canonical_classes": CANONICAL_TEXT_CATEGORIES,
                },
                f,
            )
        self.model_path = target
        self._status = TextModelStatus.READY
        return target

    def fit(
        self,
        train_texts: list[str],
        train_labels: list[str],
        max_features: int = 1000,
        ngram_range: tuple[int, int] = (1, 2),
        c_reg: float = 1.0,
    ) -> None:
        """Train TF-IDF vectorizer and Logistic Regression classifier strictly on training split."""
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            ngram_range=ngram_range,
            sublinear_tf=True,
            strip_accents="unicode",
            lowercase=True,
        )
        x_train = self.vectorizer.fit_transform(train_texts)

        self.classifier = LogisticRegression(
            C=c_reg,
            max_iter=1000,
            class_weight="balanced",
            random_state=42,
            solver="lbfgs",
        )
        self.classifier.fit(x_train, train_labels)
        self._status = TextModelStatus.READY

    def predict(self, text: str) -> TextPrediction:
        """Classify text using TF-IDF + Logistic Regression."""
        if (
            self._status != TextModelStatus.READY
            or self.vectorizer is None
            or self.classifier is None
        ):
            return TextPrediction(
                predicted_category="Other",
                confidence=0.1667,
                probabilities={c: 0.1667 for c in CANONICAL_TEXT_CATEGORIES},
                status=TextInferenceOutcome.MODEL_UNAVAILABLE,
                model_name=self._metadata.model_name,
                model_version=self._metadata.model_version,
                inference_metadata={"error": self._load_error or "Model not loaded"},
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
            x_feat = self.vectorizer.transform([text])
            raw_probs = self.classifier.predict_proba(x_feat)[0]
            classes = list(self.classifier.classes_)

            # Map to canonical 6 classes
            probs: dict[str, float] = {}
            for c in CANONICAL_TEXT_CATEGORIES:
                if c in classes:
                    idx = classes.index(c)
                    probs[c] = float(raw_probs[idx])
                else:
                    probs[c] = 0.0

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
                inference_metadata={"num_features": x_feat.shape[1]},
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
        return self._status
