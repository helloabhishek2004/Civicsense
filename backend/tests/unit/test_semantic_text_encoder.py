"""CivicSense Phase 4A: Unit Tests for MiniLM Semantic Text Encoder.

Validates:
1. Offline initialization from local weights without network dependency
2. Fixed 384-dimensional embedding output with L2 normalization
3. Batch encoding and empty input handling
4. Error state when directory or files are missing
5. Semantic similarity sanity checks between related civic issue texts
"""

from pathlib import Path

import numpy as np
import pytest

from app.services.ai.semantic_text_encoder import MiniLMTextEncoder
from app.services.ai.text_interface import TextModelStatus

REPO_ROOT = Path(__file__).resolve().parents[3]
MODEL_DIR = REPO_ROOT / "models" / "all_minilm_l6_v2"


def test_encoder_offline_loading() -> None:
    """Encoder loads strictly offline and reports READY status."""
    assert MODEL_DIR.exists(), f"Model directory {MODEL_DIR} must exist"
    encoder = MiniLMTextEncoder(model_dir=MODEL_DIR)
    assert encoder.status == TextModelStatus.READY
    assert encoder.load_error is None


def test_encoder_single_embedding_properties() -> None:
    """Embed produces 384-dim L2-normalized float32 vector."""
    encoder = MiniLMTextEncoder(model_dir=MODEL_DIR)
    emb = encoder.embed("Dangerous pothole near the school gate", normalize=True)
    assert isinstance(emb, np.ndarray)
    assert emb.shape == (384,)
    assert emb.dtype == np.float32
    norm = np.linalg.norm(emb)
    assert abs(norm - 1.0) < 1e-4


def test_encoder_batch_embedding() -> None:
    """Batch embed produces (N, 384) matrix."""
    encoder = MiniLMTextEncoder(model_dir=MODEL_DIR)
    texts = [
        "Pothole on the street",
        "Overflowing trash bin on corner",
        "Streetlight not working since yesterday",
    ]
    batch_emb = encoder.embed_batch(texts, normalize=True)
    assert isinstance(batch_emb, np.ndarray)
    assert batch_emb.shape == (3, 384)
    assert batch_emb.dtype == np.float32
    norms = np.linalg.norm(batch_emb, axis=1)
    for n in norms:
        assert abs(n - 1.0) < 1e-4


def test_encoder_empty_batch() -> None:
    """Empty batch returns (0, 384) array."""
    encoder = MiniLMTextEncoder(model_dir=MODEL_DIR)
    empty_emb = encoder.embed_batch([])
    assert empty_emb.shape == (0, 384)


def test_encoder_missing_directory() -> None:
    """Non-existent directory sets status UNAVAILABLE and raises error on embed."""
    non_existent = REPO_ROOT / "models" / "does_not_exist_minilm"
    encoder = MiniLMTextEncoder(model_dir=non_existent)
    assert encoder.status == TextModelStatus.UNAVAILABLE
    assert encoder.load_error is not None
    with pytest.raises(RuntimeError):
        encoder.embed("test text")


def test_encoder_semantic_similarity_sanity() -> None:
    """Semantically related phrases have higher cosine similarity than unrelated phrases."""
    encoder = MiniLMTextEncoder(model_dir=MODEL_DIR)
    emb1 = encoder.embed("Severe pothole and crater on the road", normalize=True)
    emb2 = encoder.embed("Deep hole in the street surface causing accidents", normalize=True)
    emb3 = encoder.embed("Street light pole bulb is dark and completely broken", normalize=True)

    sim_potholes = float(np.dot(emb1, emb2))
    sim_unrelated = float(np.dot(emb1, emb3))

    assert sim_potholes > 0.60
    assert sim_potholes > sim_unrelated
