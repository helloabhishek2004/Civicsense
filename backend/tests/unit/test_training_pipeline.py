"""CivicSense Unit Tests for Model Training & Evaluation Pipeline (Phase 3.4)."""

import tempfile
from pathlib import Path
from typing import Any

import pytest
import torch
import torch.nn as nn

from scripts.training.dataset import (
    CANONICAL_CLASSES,
    CLASS_TO_IDX,
    IDX_TO_CLASS,
    CivicSenseDataset,
)
from scripts.training.evaluate import verify_benchmark_hash
from scripts.training.model import (
    build_mobilenet_v3_small,
    get_model_parameter_stats,
    load_checkpoint,
    save_checkpoint,
)

repo_root = Path(__file__).resolve().parents[3]


def test_class_mapping_stability() -> None:
    """Canonical categories must have exactly 6 stable, bidirectional classes."""
    assert len(CANONICAL_CLASSES) == 6
    assert len(CLASS_TO_IDX) == 6
    assert len(IDX_TO_CLASS) == 6
    for idx, name in enumerate(CANONICAL_CLASSES):
        assert CLASS_TO_IDX[name] == idx
        assert IDX_TO_CLASS[idx] == name


def test_dataset_manifest_missing_raises_error() -> None:
    """Missing manifest path must raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        CivicSenseDataset("non_existent_manifest.jsonl")


def test_dataset_loading_and_item_shapes() -> None:
    """CivicSenseDataset correctly loads images and transforms them into 3x224x224 tensors."""
    train_manifest = repo_root / "datasets" / "training_v1" / "splits" / "train.jsonl"
    assert train_manifest.exists()

    ds = CivicSenseDataset(train_manifest, split="eval", repo_root=repo_root)
    assert len(ds) == 473

    tensor, label_idx, sample_id = ds[0]
    assert isinstance(tensor, torch.Tensor)
    assert tensor.shape == (3, 224, 224)
    assert 0 <= label_idx < 6
    assert isinstance(sample_id, str) and len(sample_id) > 0


def test_model_construction_and_output_shape() -> None:
    """MobileNetV3-Small adapts head to 6 outputs and executes forward pass."""
    model = build_mobilenet_v3_small(num_classes=6, pretrained=False)
    assert isinstance(model, nn.Module)

    dummy_input = torch.randn(2, 3, 224, 224)
    outputs = model(dummy_input)
    assert outputs.shape == (2, 6)


def test_backbone_freezing_parameter_counts() -> None:
    """Backbone freezing sets requires_grad=False on all feature layers."""
    model = build_mobilenet_v3_small(num_classes=6, pretrained=False, freeze_backbone=True)
    stats = get_model_parameter_stats(model)

    assert stats["frozen_parameters"] > 0
    assert stats["trainable_parameters"] == 596998
    assert stats["total_parameters"] == stats["frozen_parameters"] + stats["trainable_parameters"]

    features_mod: Any = model.features
    for param in features_mod.parameters():
        assert not param.requires_grad


def test_unfreeze_last_blocks() -> None:
    """Unfreezing last 3 blocks makes more parameters trainable than fully frozen backbone."""
    frozen_model = build_mobilenet_v3_small(num_classes=6, pretrained=False, freeze_backbone=True, unfreeze_last_blocks=0)
    partial_model = build_mobilenet_v3_small(num_classes=6, pretrained=False, freeze_backbone=True, unfreeze_last_blocks=3)

    frozen_stats = get_model_parameter_stats(frozen_model)
    partial_stats = get_model_parameter_stats(partial_model)

    assert partial_stats["trainable_parameters"] > frozen_stats["trainable_parameters"]
    assert partial_stats["frozen_parameters"] < frozen_stats["frozen_parameters"]


def test_checkpoint_saving_and_loading_roundtrip() -> None:
    """Model checkpoint preserves weights, architecture metadata, and configuration."""
    model = build_mobilenet_v3_small(num_classes=6, pretrained=False)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        ckpt_path = save_checkpoint(
            model=model,
            optimizer=None,
            epoch=3,
            best_metric=0.68,
            experiment_name="test_exp",
            output_dir=tmp_path,
            training_config={"lr": 0.001, "batch_size": 16},
        )
        assert ckpt_path.exists()
        meta_path = tmp_path / "test_exp_metadata.json"
        assert meta_path.exists()

        loaded_model, loaded_meta = load_checkpoint(ckpt_path)
        assert isinstance(loaded_model, nn.Module)
        assert loaded_meta["epoch"] == 3
        assert loaded_meta["best_macro_f1"] == 0.68
        assert loaded_meta["canonical_classes"] == CANONICAL_CLASSES


def test_benchmark_hash_verification() -> None:
    """Benchmark hash checker validates the real benchmark and rejects mutated files."""
    bm_path = repo_root / "datasets" / "benchmark_v1" / "benchmark_dataset.jsonl"
    assert bm_path.exists()

    # Must pass on real benchmark
    assert verify_benchmark_hash(bm_path) is True

    # Must fail on mutated file
    with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
        tmp.write("corrupt data")
        tmp_name = tmp.name

    try:
        with pytest.raises(RuntimeError, match="BENCHMARK INTEGRITY VIOLATION"):
            verify_benchmark_hash(Path(tmp_name))
    finally:
        Path(tmp_name).unlink(missing_ok=True)
