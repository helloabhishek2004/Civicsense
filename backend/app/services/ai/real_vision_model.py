"""CivicSense Real Vision Model Adapter (Phase 3.4).

Implements the canonical VisionModel interface by wrapping a trained
MobileNetV3-Small checkpoint for server-side visual defect classification.
Explicitly distinguishes real Other predictions from errors or unavailable states.
"""

from __future__ import annotations

import io
import math
import sys
import time
from pathlib import Path
from typing import Any

import torch
import torchvision.transforms as T  # type: ignore[import-untyped]
from PIL import Image

from app.services.ai.vision_interface import (
    CANONICAL_VISION_CATEGORIES,
    VisionInferenceOutcome,
    VisionModel,
    VisionModelMetadata,
    VisionModelStatus,
    VisionPrediction,
)

# Ensure repository root is in sys.path when running from backend directory
_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path and (_REPO_ROOT / "scripts").exists():
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from scripts.training.dataset import IMAGENET_MEAN, IMAGENET_STD
    from scripts.training.model import build_mobilenet_v3_small
except ModuleNotFoundError:
    # Standalone fallbacks if scripts directory is absent in isolated deployment environments
    IMAGENET_MEAN = [0.485, 0.456, 0.406]  # type: ignore[no-redef]
    IMAGENET_STD = [0.229, 0.224, 0.225]  # type: ignore[no-redef]

    import torch.nn as _nn
    from torchvision.models import (  # type: ignore[import-untyped]
        MobileNet_V3_Small_Weights,
        mobilenet_v3_small,
    )

    def build_mobilenet_v3_small(  # type: ignore[no-redef]
        num_classes: int = 6,
        pretrained: bool = False,
    ) -> _nn.Module:
        weights = MobileNet_V3_Small_Weights.DEFAULT if pretrained else None
        model = mobilenet_v3_small(weights=weights)
        in_features = model.classifier[3].in_features
        model.classifier[3] = _nn.Linear(in_features, num_classes)
        _nn.init.xavier_uniform_(model.classifier[3].weight)
        _nn.init.zeros_(model.classifier[3].bias)
        return model



def validate_class_probabilities(
    probs: dict[str, float],
    canonical_classes: list[str] | None = None,
    tolerance: float = 0.02,
) -> tuple[bool, str | None]:
    """Validate that class probabilities strictly conform to the 6-class contract.

    Guarantees:
    - All canonical categories present.
    - No negative values.
    - Sum is approximately 1.0 (within tolerance).
    - Preserves stable ordering.
    """
    classes = canonical_classes or CANONICAL_VISION_CATEGORIES
    if not isinstance(probs, dict):
        return False, f"Expected dict, got {type(probs).__name__}"

    missing = set(classes) - set(probs.keys())
    if missing:
        return False, f"Missing canonical classes: {sorted(missing)}"

    extra = set(probs.keys()) - set(classes)
    if extra:
        return False, f"Unexpected classes: {sorted(extra)}"

    for c, val in probs.items():
        if not isinstance(val, (int, float)):
            return False, f"Non-numeric probability for class '{c}': {val}"
        if val < 0.0:
            return False, f"Negative probability for class '{c}': {val}"

    tot = sum(probs.values())
    if abs(tot - 1.0) > tolerance:
        return False, f"Probabilities do not sum to ~1.0: sum={tot:.4f}"

    return True, None


class RealVisionModel(VisionModel):
    """Server-side production adapter for trained MobileNetV3-Small models."""

    def __init__(
        self,
        checkpoint_path: str | Path | None = None,
        confidence_threshold: float = 0.60,
        device: str = "cpu",
    ) -> None:
        self.confidence_threshold = confidence_threshold
        self.device = torch.device(device)
        self.checkpoint_path = Path(checkpoint_path).resolve() if checkpoint_path else None
        self._model: torch.nn.Module | None = None
        self._metadata_dict: dict[str, Any] = {}
        self._status = VisionModelStatus.UNAVAILABLE
        self._error_init_message: str | None = None

        self._transform = T.Compose(
            [
                T.Resize((256, 256)),
                T.CenterCrop(224),
                T.ToTensor(),
                T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
            ]
        )

        if self.checkpoint_path and self.checkpoint_path.exists():
            self._load_checkpoint()
        else:
            self._status = VisionModelStatus.UNAVAILABLE
            self._error_init_message = (
                f"Checkpoint file not found: {self.checkpoint_path}"
                if self.checkpoint_path
                else "No checkpoint path provided."
            )

        self._metadata = VisionModelMetadata(
            model_name="mobilenet_v3_small",
            model_version=str(self._metadata_dict.get("epoch", "1.0.0")),
            architecture_family="MobileNetV3",
            input_resolution=(224, 224),
            num_classes=len(CANONICAL_VISION_CATEGORIES),
            canonical_classes=list(CANONICAL_VISION_CATEGORIES),
            device=str(self.device),
            runtime="pytorch_cpu" if self.device.type == "cpu" else "pytorch_cuda",
            quantization="none",
        )

    def _load_checkpoint(self) -> None:
        """Load and validate PyTorch checkpoint weights."""
        assert self.checkpoint_path is not None
        try:
            ckpt = torch.load(self.checkpoint_path, map_location=self.device)
            model = build_mobilenet_v3_small(
                num_classes=len(CANONICAL_VISION_CATEGORIES),
                pretrained=False,
            )
            model.load_state_dict(ckpt["model_state_dict"])
            model.to(self.device)
            model.eval()
            self._model = model
            self._metadata_dict = {
                "epoch": ckpt.get("epoch", 1),
                "best_macro_f1": ckpt.get("best_macro_f1", 0.0),
                "experiment_name": ckpt.get("experiment_name", "pilot"),
                "saved_at": ckpt.get("saved_at", ""),
            }
            self._status = VisionModelStatus.READY
        except Exception as exc:
            self._status = VisionModelStatus.LOADING_FAILED
            self._error_init_message = f"Failed to load checkpoint: {exc}"
            self._model = None

    @property
    def metadata(self) -> VisionModelMetadata:
        return self._metadata

    @property
    def status(self) -> VisionModelStatus:
        return self._status

    def predict(self, image_bytes: bytes) -> VisionPrediction:
        """Execute inference against raw image bytes."""
        prep_start = time.perf_counter()

        if self._status != VisionModelStatus.READY or self._model is None:
            outcome = (
                VisionInferenceOutcome.MODEL_UNAVAILABLE
                if self._status == VisionModelStatus.UNAVAILABLE
                else VisionInferenceOutcome.INFERENCE_ERROR
            )
            return VisionPrediction(
                outcome=outcome,
                predicted_category=None,
                confidence=0.0,
                class_probabilities={},
                model_name=self._metadata.model_name,
                model_version=self._metadata.model_version,
                inference_time_ms=0.0,
                preprocessing_time_ms=0.0,
                requires_review=True,
                error_message=self._error_init_message or "Model is not operational.",
            )

        if not image_bytes:
            return VisionPrediction(
                outcome=VisionInferenceOutcome.PREPROCESSING_ERROR,
                predicted_category=None,
                confidence=0.0,
                class_probabilities={},
                model_name=self._metadata.model_name,
                model_version=self._metadata.model_version,
                inference_time_ms=0.0,
                preprocessing_time_ms=0.0,
                requires_review=True,
                error_message="Image buffer is empty or missing.",
            )

        try:
            with Image.open(io.BytesIO(image_bytes)) as pil_img:
                rgb_img = pil_img.convert("RGB")
                tensor = self._transform(rgb_img).unsqueeze(0).to(self.device)
        except Exception as exc:
            prep_dur = round((time.perf_counter() - prep_start) * 1000, 2)
            return VisionPrediction(
                outcome=VisionInferenceOutcome.PREPROCESSING_ERROR,
                predicted_category=None,
                confidence=0.0,
                class_probabilities={},
                model_name=self._metadata.model_name,
                model_version=self._metadata.model_version,
                inference_time_ms=0.0,
                preprocessing_time_ms=prep_dur,
                requires_review=True,
                error_message=f"Image preprocessing/decoding failed: {exc}",
            )

        prep_dur = round((time.perf_counter() - prep_start) * 1000, 2)
        inf_start = time.perf_counter()

        try:
            with torch.no_grad():
                logits = self._model(tensor)
                probs_tensor = torch.softmax(logits, dim=-1).squeeze(0)
                conf_val, pred_idx = torch.max(probs_tensor, dim=-1)

            inf_dur = round((time.perf_counter() - inf_start) * 1000, 2)
            pred_category = CANONICAL_VISION_CATEGORIES[int(pred_idx.item())]

            # Enforce strict normalization to sum to 1.0 exactly
            raw_p = [
                float(probs_tensor[idx].item()) for idx in range(len(CANONICAL_VISION_CATEGORIES))
            ]
            tot_p = sum(raw_p)
            if tot_p > 0:
                norm_p = [p / tot_p for p in raw_p]
            else:
                norm_p = [1.0 / len(CANONICAL_VISION_CATEGORIES)] * len(CANONICAL_VISION_CATEGORIES)

            class_probs = {
                cat: round(norm_p[idx], 4) for idx, cat in enumerate(CANONICAL_VISION_CATEGORIES)
            }
            # Adjust minor floating point rounding delta on Other
            diff = round(1.0 - sum(class_probs.values()), 4)
            class_probs["Other"] = round(class_probs["Other"] + diff, 4)
            confidence = round(float(class_probs[pred_category]), 4)

            # Validate output probabilities before returning
            is_valid, val_err = validate_class_probabilities(class_probs)
            if not is_valid:
                return VisionPrediction(
                    outcome=VisionInferenceOutcome.INFERENCE_ERROR,
                    predicted_category=None,
                    confidence=0.0,
                    class_probabilities={},
                    model_name=self._metadata.model_name,
                    model_version=self._metadata.model_version,
                    inference_time_ms=inf_dur,
                    preprocessing_time_ms=prep_dur,
                    requires_review=True,
                    error_message=f"Model output probability validation failed: {val_err}",
                )

            is_low_conf = confidence < self.confidence_threshold
            outcome = (
                VisionInferenceOutcome.LOW_CONFIDENCE
                if is_low_conf
                else VisionInferenceOutcome.SUCCESS
            )

            return VisionPrediction(
                outcome=outcome,
                predicted_category=pred_category,
                confidence=confidence,
                class_probabilities=class_probs,
                model_name=self._metadata.model_name,
                model_version=self._metadata.model_version,
                inference_time_ms=inf_dur,
                preprocessing_time_ms=prep_dur,
                requires_review=is_low_conf,
                metadata={
                    "checkpoint_epoch": self._metadata_dict.get("epoch"),
                    "best_val_macro_f1": self._metadata_dict.get("best_macro_f1"),
                    "device": str(self.device),
                },
            )
        except Exception as exc:
            inf_dur = round((time.perf_counter() - inf_start) * 1000, 2)
            return VisionPrediction(
                outcome=VisionInferenceOutcome.INFERENCE_ERROR,
                predicted_category=None,
                confidence=0.0,
                class_probabilities={},
                model_name=self._metadata.model_name,
                model_version=self._metadata.model_version,
                inference_time_ms=inf_dur,
                preprocessing_time_ms=prep_dur,
                requires_review=True,
                error_message=f"Model forward pass failed: {exc}",
            )

    def predict_probabilities(
        self, image_bytes: bytes
    ) -> tuple[dict[str, float], VisionInferenceOutcome]:
        """Convenience method returning class probabilities and inference outcome."""
        pred = self.predict(image_bytes)
        return pred.class_probabilities, pred.outcome

    def extract_embedding(self, image_bytes: bytes) -> list[float] | None:
        """Extract a 576-dimensional visual feature embedding from raw image bytes.

        Returns a L2-normalized feature vector extracted from the penultimate layer
        (after adaptive average pooling, before the classifier head). Returns None
        if the model is unavailable, the image is invalid, or extraction fails.

        The embedding is suitable for cosine similarity comparison between images.
        """
        if self._status != VisionModelStatus.READY or self._model is None:
            return None

        if not image_bytes:
            return None

        try:
            with Image.open(io.BytesIO(image_bytes)) as pil_img:
                rgb_img = pil_img.convert("RGB")
                tensor = self._transform(rgb_img).unsqueeze(0).to(self.device)
        except Exception:
            return None

        try:
            with torch.no_grad():
                # Run through features + avgpool only (skip classifier)
                model = self._model
                assert model is not None
                features = model.features(tensor)  # type: ignore[union-attr]
                pooled = model.avgpool(features)  # type: ignore[union-attr]
                flattened = pooled.flatten(start_dim=1)
                embedding = flattened.squeeze(0).cpu().tolist()

                # L2-normalize for cosine similarity compatibility
                norm = math.sqrt(sum(x * x for x in embedding))
                if norm < 1e-9:
                    return None
                embedding = [x / norm for x in embedding]
                return embedding
        except Exception:
            return None
