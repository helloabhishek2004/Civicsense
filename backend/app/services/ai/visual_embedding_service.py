"""CivicSense Visual Embedding Service.

Provides server-side visual embedding generation from report evidence images.
Wraps RealVisionModel with graceful degradation, lazy loading, and
deterministic embedding extraction for similarity comparison.

Architecture:
  - Lazy model loading on first request (not at import time)
  - Graceful degradation: returns None when model unavailable
  - Reads evidence images from disk via storage_uri
  - 576-dim L2-normalized embeddings from MobileNetV3-Small penultimate layer
  - Deterministic: same image + same model = same embedding

Model quality note:
  The current MobileNetV3-Small model is trained for classification (66.4% validation,
  43.3% benchmark). The penultimate-layer embedding is a transfer-learning byproduct,
  not a similarity-optimized representation. Retrieval quality (precision@k, recall@k)
  has not been empirically validated. Visual similarity is an auxiliary signal only.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Module-level singleton (lazy loaded)
_visual_service: VisualEmbeddingService | None = None


class VisualEmbeddingService:
    """Service for generating visual embeddings from evidence images."""

    def __init__(self) -> None:
        self._model: Any = None  # RealVisionModel instance, lazy loaded
        self._loaded = False
        self._load_error: str | None = None

    def _ensure_model_loaded(self) -> None:
        """Lazy-load the vision model on first use."""
        if self._loaded:
            return

        settings = get_settings()
        if not settings.VISION_ENABLED:
            self._loaded = True
            self._load_error = "Vision processing disabled via VISION_ENABLED=false"
            logger.info("Visual embedding service: disabled via config")
            return

        checkpoint_path = settings.vision_model_path
        if not checkpoint_path.exists():
            self._loaded = True
            self._load_error = f"Checkpoint not found: {checkpoint_path}"
            logger.warning("Visual embedding service: checkpoint not found at %s", checkpoint_path)
            return

        try:
            from app.services.ai.real_vision_model import RealVisionModel

            self._model = RealVisionModel(
                checkpoint_path=str(checkpoint_path),
                confidence_threshold=settings.VISION_CONFIDENCE_THRESHOLD,
            )
            if self._model.status.value == "READY":
                self._loaded = True
                logger.info(
                    "Visual embedding service: loaded checkpoint %s (dim=%d)",
                    checkpoint_path.name,
                    settings.VISION_EMBEDDING_DIM,
                )
            else:
                self._loaded = True
                self._load_error = f"Model load failed: status={self._model.status.value}"
                logger.warning(
                    "Visual embedding service: model load failed with status %s",
                    self._model.status.value,
                )
        except Exception as exc:
            self._loaded = True
            self._load_error = f"Model initialization error: {exc}"
            logger.warning("Visual embedding service: initialization failed: %s", exc)

    @property
    def is_ready(self) -> bool:
        """Whether the vision model is loaded and ready for inference."""
        self._ensure_model_loaded()
        return self._model is not None and self._model.status.value == "READY"

    @property
    def status(self) -> dict[str, Any]:
        """Return service status for health checks."""
        self._ensure_model_loaded()
        settings = get_settings()
        return {
            "vision_enabled": settings.VISION_ENABLED,
            "model_ready": self.is_ready,
            "load_error": self._load_error,
            "checkpoint_path": str(settings.vision_model_path),
            "embedding_dim": settings.VISION_EMBEDDING_DIM if self.is_ready else None,
        }

    def extract_embedding_from_bytes(self, image_bytes: bytes) -> list[float] | None:
        """Extract a visual embedding from raw image bytes.

        Returns a 576-dim L2-normalized vector, or None on failure.
        """
        self._ensure_model_loaded()

        if not self.is_ready or self._model is None:
            return None

        if not image_bytes:
            return None

        try:
            embedding = self._model.extract_embedding(image_bytes)
            return embedding
        except Exception as exc:
            logger.debug("Visual embedding extraction failed: %s", exc)
            return None

    def extract_embedding_from_file(self, file_path: Path) -> list[float] | None:
        """Extract a visual embedding from an image file on disk."""
        if not file_path.exists():
            logger.debug("Image file not found: %s", file_path)
            return None

        try:
            image_bytes = file_path.read_bytes()
            return self.extract_embedding_from_bytes(image_bytes)
        except Exception as exc:
            logger.debug("Failed to read image file %s: %s", file_path, exc)
            return None

    def extract_embedding_from_storage_uri(
        self, storage_uri: str, uploads_dir: str = "uploads"
    ) -> list[float] | None:
        """Extract a visual embedding from a report's evidence storage URI.

        Handles both absolute paths and relative /uploads/... URIs.
        """
        if not storage_uri:
            return None

        # Resolve relative URIs
        if storage_uri.startswith("/uploads/"):
            file_path = Path(uploads_dir) / storage_uri.removeprefix("/uploads/")
        elif storage_uri.startswith("uploads/"):
            file_path = Path(storage_uri)
        else:
            file_path = Path(storage_uri)

        return self.extract_embedding_from_file(file_path)


def get_visual_embedding_service() -> VisualEmbeddingService:
    """Return the singleton VisualEmbeddingService instance."""
    global _visual_service
    if _visual_service is None:
        _visual_service = VisualEmbeddingService()
    return _visual_service


def cosine_similarity_vectors(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors. Returns 0.0 for invalid inputs."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a < 1e-9 or norm_b < 1e-9:
        return 0.0
    return max(-1.0, min(1.0, dot / (norm_a * norm_b)))
