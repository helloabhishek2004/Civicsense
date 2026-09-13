"""CivicSense MobileNetV3-Small Model Architecture & Checkpoint Management.

Configures MobileNetV3-Small with an adapted 6-class head for civic issue detection.
Supports backbone freezing, selective layer unfreezing, and structured metadata saving.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import torch
from torch import nn
from torchvision.models import (  # type: ignore[import-untyped]
    MobileNet_V3_Small_Weights,
    mobilenet_v3_small,
)

from scripts.training.dataset import (
    CANONICAL_CLASSES,
    CLASS_TO_IDX,
    IDX_TO_CLASS,
    IMAGENET_MEAN,
    IMAGENET_STD,
)


def build_mobilenet_v3_small(
    num_classes: int = 6,
    pretrained: bool = True,
    freeze_backbone: bool = False,
    unfreeze_last_blocks: int = 0,
) -> nn.Module:
    """Construct MobileNetV3-Small with 6-class linear classifier."""
    weights = MobileNet_V3_Small_Weights.DEFAULT if pretrained else None
    model = mobilenet_v3_small(weights=weights)

    # In MobileNetV3-Small, classifier structure:
    # (0): Linear(576, 1024)
    # (1): Hardswish()
    # (2): Dropout(p=0.2)
    # (3): Linear(1024, 1000)
    in_features = model.classifier[3].in_features
    model.classifier[3] = nn.Linear(in_features, num_classes)

    # Xavier initialization for the new classification head
    nn.init.xavier_uniform_(model.classifier[3].weight)
    nn.init.zeros_(model.classifier[3].bias)

    if freeze_backbone:
        for param in model.features.parameters():
            param.requires_grad = False

        if unfreeze_last_blocks > 0:
            # Unfreeze the last N blocks of the feature extractor
            total_blocks = len(model.features)
            start_unfreeze = max(0, total_blocks - unfreeze_last_blocks)
            for i in range(start_unfreeze, total_blocks):
                for param in model.features[i].parameters():
                    param.requires_grad = True

    return model


def get_model_parameter_stats(model: nn.Module) -> dict[str, int]:
    """Calculate parameter counts."""
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    frozen_params = total_params - trainable_params
    return {
        "total_parameters": total_params,
        "trainable_parameters": trainable_params,
        "frozen_parameters": frozen_params,
    }


def save_checkpoint(
    model: nn.Module,
    optimizer: torch.optim.Optimizer | None,
    epoch: int,
    best_metric: float,
    experiment_name: str,
    output_dir: Path,
    training_config: dict[str, Any],
) -> Path:
    """Save PyTorch checkpoint and JSON metadata."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = output_dir / f"{experiment_name}_best.pt"

    checkpoint_data = {
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict() if optimizer else None,
        "epoch": epoch,
        "best_macro_f1": best_metric,
        "experiment_name": experiment_name,
        "saved_at": datetime.now(UTC).isoformat(),
        "canonical_classes": list(CANONICAL_CLASSES),
        "class_to_idx": dict(CLASS_TO_IDX),
        "idx_to_class": dict(IDX_TO_CLASS),
        "input_resolution": [224, 224],
        "normalization": {
            "mean": IMAGENET_MEAN,
            "std": IMAGENET_STD,
        },
        "training_config": training_config,
    }
    torch.save(checkpoint_data, checkpoint_path)

    # Save human-readable metadata JSON alongside checkpoint
    metadata_path = output_dir / f"{experiment_name}_metadata.json"
    metadata_json = {
        "model_name": "mobilenet_v3_small",
        "experiment_name": experiment_name,
        "epoch": epoch,
        "best_macro_f1": round(best_metric, 4),
        "checkpoint_file": checkpoint_path.name,
        "num_classes": len(CANONICAL_CLASSES),
        "canonical_classes": list(CANONICAL_CLASSES),
        "input_resolution": [224, 224],
        "normalization_mean": IMAGENET_MEAN,
        "normalization_std": IMAGENET_STD,
        "parameters": get_model_parameter_stats(model),
        "saved_at": datetime.now(UTC).isoformat(),
        "training_config": training_config,
    }
    metadata_path.write_text(json.dumps(metadata_json, indent=2), encoding="utf-8")
    return checkpoint_path


def load_checkpoint(
    checkpoint_path: str | Path,
    device: str = "cpu",
) -> tuple[nn.Module, dict[str, Any]]:
    """Load model and metadata from saved checkpoint."""
    path_obj = Path(checkpoint_path).resolve()
    if not path_obj.exists():
        raise FileNotFoundError(f"Checkpoint not found at: {path_obj}")

    checkpoint = torch.load(path_obj, map_location=device)
    model = build_mobilenet_v3_small(num_classes=len(CANONICAL_CLASSES), pretrained=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device)
    model.eval()

    meta = {
        "epoch": checkpoint.get("epoch", -1),
        "best_macro_f1": checkpoint.get("best_macro_f1", 0.0),
        "canonical_classes": checkpoint.get("canonical_classes", CANONICAL_CLASSES),
        "class_to_idx": checkpoint.get("class_to_idx", CLASS_TO_IDX),
        "idx_to_class": checkpoint.get("idx_to_class", IDX_TO_CLASS),
        "training_config": checkpoint.get("training_config", {}),
    }
    return model, meta
