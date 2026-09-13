"""CivicSense Phase 4A: Semantic Text Encoder using MiniLM-L6-v2.

Encapsulates offline transformer loading, tokenization, attention-mask-aware mean pooling,
and embedding extraction.
"""

from pathlib import Path
from typing import Any

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

from app.services.ai.text_interface import TextModelStatus


class MiniLMTextEncoder:
    """Offline semantic encoder wrapping all-MiniLM-L6-v2."""

    DEFAULT_MODEL_DIR = Path("models/all_minilm_l6_v2")
    EMBEDDING_DIM = 384
    MAX_SEQUENCE_LENGTH = 256

    def __init__(self, model_dir: str | Path | None = None) -> None:
        self.model_dir = Path(model_dir) if model_dir else self.DEFAULT_MODEL_DIR
        self.tokenizer: Any = None
        self.model: Any = None
        self._status = TextModelStatus.UNAVAILABLE
        self._load_error: str | None = None

        self._load_offline()

    def _load_offline(self) -> None:
        """Load tokenizer and transformer model strictly offline."""
        if not self.model_dir.exists():
            self._status = TextModelStatus.UNAVAILABLE
            self._load_error = f"Model directory not found: {self.model_dir}"
            return

        safetensors_path = self.model_dir / "model.safetensors"
        config_path = self.model_dir / "config.json"
        if not safetensors_path.exists() or not config_path.exists():
            self._status = TextModelStatus.UNAVAILABLE
            self._load_error = f"Required model files missing in: {self.model_dir}"
            return

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                str(self.model_dir),
                local_files_only=True,
            )
            self.model = AutoModel.from_pretrained(
                str(self.model_dir),
                local_files_only=True,
            )
            self.model.eval()
            self._status = TextModelStatus.READY
            self._load_error = None
        except Exception as e:
            self._status = TextModelStatus.LOADING_FAILED
            self._load_error = str(e)
            self.tokenizer = None
            self.model = None

    @property
    def status(self) -> TextModelStatus:
        """Return readiness status."""
        return self._status

    @property
    def load_error(self) -> str | None:
        """Return error message if loading failed."""
        return self._load_error

    def embed(self, text: str, normalize: bool = True) -> np.ndarray:
        """Compute 384-dimensional dense sentence embedding for a single text.

        Args:
            text: Input citizen description or query.
            normalize: If True, applies L2 normalization (unit norm).

        Returns:
            1D numpy array of shape (384,) with float32 values.
        """
        batch_embeddings = self.embed_batch([text], normalize=normalize)
        return batch_embeddings[0]

    def embed_batch(self, texts: list[str], normalize: bool = True) -> np.ndarray:
        """Compute dense sentence embeddings for a batch of texts.

        Args:
            texts: List of input strings.
            normalize: If True, applies L2 normalization.

        Returns:
            2D numpy array of shape (N, 384) with float32 values.
        """
        if self._status != TextModelStatus.READY or self.model is None or self.tokenizer is None:
            raise RuntimeError(f"MiniLM encoder is not ready: {self._load_error}")

        if not texts:
            return np.empty((0, self.EMBEDDING_DIM), dtype=np.float32)

        # Sanitize empty / whitespace strings
        cleaned_texts = [t.strip() if t and t.strip() else "" for t in texts]

        # Fast tokenization
        encoded = self.tokenizer(
            cleaned_texts,
            padding=True,
            truncation=True,
            max_length=self.MAX_SEQUENCE_LENGTH,
            return_tensors="pt",
        )

        with torch.no_grad():
            outputs = self.model(**encoded)
            token_embeddings = outputs.last_hidden_state  # [B, SeqLen, HiddenDim]
            attention_mask = encoded["attention_mask"]  # [B, SeqLen]

            # Attention-mask-aware mean pooling:
            # sum(token_embeddings * mask) / clamp(sum(mask), min=1e-9)
            mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
            sum_embeddings = torch.sum(token_embeddings * mask_expanded, dim=1)
            sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
            pooled = sum_embeddings / sum_mask  # [B, 384]

            if normalize:
                pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)

        return pooled.cpu().numpy().astype(np.float32)
