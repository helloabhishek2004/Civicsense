"""CivicSense Controlled Training Pipeline for MobileNetV3-Small.

Executes controlled transfer learning and fine-tuning experiments:
  - Experiment A: Frozen backbone, train classification head only.
  - Experiment B: Differential fine-tuning unfreezing last 3 residual blocks.

Calculates accuracy, macro precision/recall/F1, and per-class metrics at every epoch.
Saves checkpoints, metadata, and history under models/mobilenet_v3_small_v1/.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from sklearn.metrics import (  # type: ignore[import-untyped]
    accuracy_score,
    precision_recall_fscore_support,
)
from torch import nn
from torch.utils.data import DataLoader

# Add repo root to sys.path
repo_root = Path(__file__).resolve().parents[2]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from scripts.training.dataset import (
    CANONICAL_CLASSES,
    CivicSenseDataset,
)
from scripts.training.model import (
    build_mobilenet_v3_small,
    get_model_parameter_stats,
    save_checkpoint,
)


def set_seed(seed: int = 42) -> None:
    """Set random seeds for deterministic reproducibility where supported."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def evaluate_model(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> dict[str, Any]:
    """Evaluate model on a dataset, returning loss, overall metrics, and per-class stats."""
    model.eval()
    total_loss = 0.0
    all_preds: list[int] = []
    all_targets: list[int] = []
    all_probs: list[list[float]] = []

    with torch.no_grad():
        for images, targets, _ in dataloader:
            images = images.to(device)
            targets = targets.to(device)

            logits = model(images)
            loss = criterion(logits, targets)
            total_loss += loss.item() * images.size(0)

            probs = torch.softmax(logits, dim=-1)
            preds = torch.argmax(probs, dim=-1)

            all_preds.extend(preds.cpu().tolist())
            all_targets.extend(targets.cpu().tolist())
            all_probs.extend(probs.cpu().tolist())

    n_samples = len(all_targets)
    avg_loss = total_loss / max(1, n_samples)
    acc = accuracy_score(all_targets, all_preds)
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(
        all_targets, all_preds, average="macro", zero_division=0
    )
    p_per, r_per, f1_per, sup_per = precision_recall_fscore_support(
        all_targets, all_preds, average=None, labels=list(range(len(CANONICAL_CLASSES))), zero_division=0
    )

    per_class_metrics = {}
    for idx, cat in enumerate(CANONICAL_CLASSES):
        per_class_metrics[cat] = {
            "precision": round(float(p_per[idx]), 4),
            "recall": round(float(r_per[idx]), 4),
            "f1_score": round(float(f1_per[idx]), 4),
            "support": int(sup_per[idx]),
        }

    return {
        "loss": round(avg_loss, 4),
        "accuracy": round(float(acc), 4),
        "macro_precision": round(float(p_macro), 4),
        "macro_recall": round(float(r_macro), 4),
        "macro_f1": round(float(f1_macro), 4),
        "per_class": per_class_metrics,
        "predictions": all_preds,
        "targets": all_targets,
    }


def run_training(
    experiment: str = "exp_a",
    epochs: int = 20,
    batch_size: int = 16,
    lr: float = 1e-3,
    weight_decay: float = 1e-4,
    seed: int = 42,
    patience: int = 7,
    train_manifest: str = "datasets/training_v1/splits/train.jsonl",
    val_manifest: str = "datasets/training_v1/splits/validation.jsonl",
    output_dir: str = "models/mobilenet_v3_small_v1",
) -> dict[str, Any]:
    """Execute complete training experiment."""
    set_seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[{experiment.upper()}] Execution device: {device}")

    train_path = (repo_root / train_manifest).resolve()
    val_path = (repo_root / val_manifest).resolve()
    out_path = (repo_root / output_dir / experiment).resolve()
    out_path.mkdir(parents=True, exist_ok=True)

    # 1. Datasets & Loaders
    train_dataset = CivicSenseDataset(train_path, split="train", repo_root=repo_root)
    val_dataset = CivicSenseDataset(val_path, split="val", repo_root=repo_root)

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0,
        pin_memory=(device.type == "cuda"),
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0,
        pin_memory=(device.type == "cuda"),
    )

    print(f"[{experiment.upper()}] Train samples: {len(train_dataset)}, Val samples: {len(val_dataset)}")
    print(f"[{experiment.upper()}] Train batches: {len(train_loader)}, Val batches: {len(val_loader)}")

    # 2. Build Model
    if experiment == "exp_a":
        # Frozen backbone, train only classification head
        model = build_mobilenet_v3_small(
            num_classes=len(CANONICAL_CLASSES),
            pretrained=True,
            freeze_backbone=True,
            unfreeze_last_blocks=0,
        )
        param_groups = [{"params": [p for p in model.parameters() if p.requires_grad], "lr": lr}]
    elif experiment == "exp_b":
        # Unfreeze last 3 blocks of feature extractor with lower lr, classifier head with standard lr
        model = build_mobilenet_v3_small(
            num_classes=len(CANONICAL_CLASSES),
            pretrained=True,
            freeze_backbone=True,
            unfreeze_last_blocks=3,
        )
        features_mod: Any = model.features
        classifier_mod: Any = model.classifier
        backbone_params = [p for p in features_mod.parameters() if p.requires_grad]
        head_params = [p for p in classifier_mod.parameters() if p.requires_grad]
        param_groups = [
            {"params": backbone_params, "lr": lr * 0.1},
            {"params": head_params, "lr": lr},
        ]
    else:
        raise ValueError(f"Unknown experiment '{experiment}'. Use 'exp_a' or 'exp_b'.")

    model = model.to(device)
    param_stats = get_model_parameter_stats(model)
    print(f"[{experiment.upper()}] Model parameter stats: {param_stats}")

    # 3. Loss & Optimizer & Scheduler
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(param_groups, lr=lr, weight_decay=weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-6)

    training_config = {
        "experiment": experiment,
        "epochs": epochs,
        "batch_size": batch_size,
        "initial_lr": lr,
        "weight_decay": weight_decay,
        "seed": seed,
        "patience": patience,
        "device": str(device),
        "cuda_available": torch.cuda.is_available(),
        "train_samples": len(train_dataset),
        "val_samples": len(val_dataset),
        "parameter_stats": param_stats,
    }

    # 4. Training Loop
    history: list[dict[str, Any]] = []
    best_macro_f1 = -1.0
    best_epoch = 0
    epochs_no_improve = 0
    start_time = time.time()

    print(f"[{experiment.upper()}] Beginning {epochs} epochs of training...")

    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        ep_start = time.time()

        for images, targets, _ in train_loader:
            images = images.to(device)
            targets = targets.to(device)

            optimizer.zero_grad()
            logits = model(images)
            loss = criterion(logits, targets)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * images.size(0)

        scheduler.step()
        ep_train_loss = round(train_loss / len(train_dataset), 4)

        # Validation
        val_metrics = evaluate_model(model, val_loader, criterion, device)
        val_macro_f1 = val_metrics["macro_f1"]
        val_acc = val_metrics["accuracy"]
        ep_dur = round(time.time() - ep_start, 2)

        epoch_record = {
            "epoch": epoch,
            "train_loss": ep_train_loss,
            "val_loss": val_metrics["loss"],
            "val_accuracy": val_acc,
            "val_macro_precision": val_metrics["macro_precision"],
            "val_macro_recall": val_metrics["macro_recall"],
            "val_macro_f1": val_macro_f1,
            "epoch_duration_sec": ep_dur,
            "learning_rates": [group["lr"] for group in optimizer.param_groups],
        }
        history.append(epoch_record)

        print(
            f"  Epoch {epoch:02d}/{epochs:02d} [{ep_dur}s] - "
            f"Train Loss: {ep_train_loss:.4f} | Val Loss: {val_metrics['loss']:.4f} | "
            f"Val Acc: {val_acc*100:.2f}% | Val Macro F1: {val_macro_f1:.4f}"
        )

        # Checkpoint Best Model
        if val_macro_f1 > best_macro_f1:
            best_macro_f1 = val_macro_f1
            best_epoch = epoch
            epochs_no_improve = 0
            save_checkpoint(
                model=model,
                optimizer=optimizer,
                epoch=epoch,
                best_metric=best_macro_f1,
                experiment_name=experiment,
                output_dir=out_path,
                training_config=training_config,
            )
            print(f"    --> Best model updated: Val Macro F1 = {best_macro_f1:.4f} (Epoch {epoch})")
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= patience:
                print(f"[{experiment.upper()}] Early stopping triggered after {epoch} epochs (patience={patience}).")
                break

    total_duration = round(time.time() - start_time, 2)

    # Save training history
    history_file = out_path / f"{experiment}_history.json"
    history_data = {
        "experiment": experiment,
        "best_epoch": best_epoch,
        "best_macro_f1": round(best_macro_f1, 4),
        "total_duration_sec": total_duration,
        "training_config": training_config,
        "history": history,
    }
    history_file.write_text(json.dumps(history_data, indent=2), encoding="utf-8")

    print(
        f"[{experiment.upper()}] Complete! Best Epoch: {best_epoch} | "
        f"Best Val Macro F1: {best_macro_f1:.4f} | Total Time: {total_duration}s"
    )
    return history_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CivicSense MobileNetV3-Small Training Runner")
    parser.add_argument("--experiment", choices=["exp_a", "exp_b"], default="exp_a", help="Experiment type")
    parser.add_argument("--epochs", type=int, default=20, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-3, help="Initial learning rate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--patience", type=int, default=7, help="Early stopping patience")
    args = parser.parse_args()

    run_training(
        experiment=args.experiment,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        seed=args.seed,
        patience=args.patience,
    )
