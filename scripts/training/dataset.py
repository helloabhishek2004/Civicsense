"""CivicSense PyTorch Dataset & Transforms for Civic Issue Classification.

Implements memory-safe, reproducible data loading for training, validation,
and benchmark evaluation across the 6 canonical civic categories.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import torch
import torchvision.transforms as T  # type: ignore[import-untyped]
from PIL import Image
from torch.utils.data import Dataset

# Protect against decompression bomb DOS attacks
Image.MAX_IMAGE_PIXELS = 30_000_000

CANONICAL_CLASSES: list[str] = [
    "Pothole",
    "Road Damage",
    "Garbage",
    "Water Leakage",
    "Streetlight",
    "Other",
]

CLASS_TO_IDX: dict[str, int] = {cat: idx for idx, cat in enumerate(CANONICAL_CLASSES)}
IDX_TO_CLASS: dict[int, str] = {idx: cat for idx, cat in enumerate(CANONICAL_CLASSES)}

# ImageNet standard normalization parameters
IMAGENET_MEAN: list[float] = [0.485, 0.456, 0.406]
IMAGENET_STD: list[float] = [0.229, 0.224, 0.225]


def get_transforms(split: str = "train", img_size: int = 224) -> T.Compose:
    """Return torchvision data transforms for the specified split."""
    if split == "train":
        return T.Compose([
            T.Resize((256, 256)),
            T.RandomResizedCrop(img_size, scale=(0.8, 1.0)),
            T.RandomHorizontalFlip(p=0.5),
            T.ColorJitter(brightness=0.1, contrast=0.1, saturation=0.1),
            T.ToTensor(),
            T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ])
    else:
        return T.Compose([
            T.Resize((256, 256)),
            T.CenterCrop(img_size),
            T.ToTensor(),
            T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ])


class CivicSenseDataset(Dataset):
    """PyTorch Dataset loading civic defect samples from JSONL split manifests."""

    def __init__(
        self,
        manifest_path: str | Path,
        split: str = "train",
        transform: T.Compose | None = None,
        repo_root: Path | None = None,
    ) -> None:
        self.manifest_path = Path(manifest_path).resolve()
        self.split = split
        self.repo_root = repo_root or self.manifest_path.parents[3]
        self.transform = transform or get_transforms(split=split)

        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest file not found: {self.manifest_path}")

        self.samples: list[dict[str, Any]] = []
        self._load_records()

    def _load_records(self) -> None:
        """Parse JSONL lines and resolve image paths."""
        raw_text = self.manifest_path.read_text(encoding="utf-8")
        for line_num, line in enumerate(raw_text.splitlines(), start=1):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                record = json.loads(line_str)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise ValueError(f"Corrupt JSON at line {line_num} in {self.manifest_path}: {exc}") from exc

            # Resolve category
            category = (
                record.get("primary_category")
                or record.get("canonical_category")
                or record.get("category")
            )
            if category not in CLASS_TO_IDX:
                raise ValueError(f"Invalid category '{category}' in record: {record.get('sample_id')}")

            # Resolve local image path
            local_path_str = (
                record.get("local_path")
                or record.get("image_path")
                or record.get("image_rel_path")
                or ""
            )
            img_path = Path(local_path_str)
            if not img_path.is_absolute():
                if (self.manifest_path.parent / img_path).exists():
                    img_path = (self.manifest_path.parent / img_path).resolve()
                else:
                    img_path = (self.repo_root / img_path).resolve()

            if not img_path.exists():
                raise FileNotFoundError(
                    f"Sample {record.get('sample_id')} image not found at {img_path}"
                )

            self.samples.append({
                "sample_id": record.get("sample_id", f"sample_{len(self.samples)}"),
                "image_path": str(img_path),
                "category": category,
                "label_idx": CLASS_TO_IDX[category],
                "group_id": record.get("group_id", "unknown"),
                "source_name": record.get("source_name", "unknown"),
            })

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, int, str]:
        item = self.samples[idx]
        img_path = item["image_path"]

        try:
            with Image.open(img_path) as pil_img:
                image = pil_img.convert("RGB")
        except (OSError, ValueError) as exc:
            raise RuntimeError(f"Failed to decode image at {img_path}: {exc}") from exc

        tensor = self.transform(image)
        return tensor, item["label_idx"], item["sample_id"]

    def get_class_counts(self) -> dict[str, int]:
        """Compute sample counts per category."""
        counts = {cat: 0 for cat in CANONICAL_CLASSES}
        for item in self.samples:
            counts[item["category"]] += 1
        return counts
