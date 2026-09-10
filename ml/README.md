# CivicSense ML & Research Pipeline

This directory is the dedicated space for machine learning experiments, dataset curation, model training, evaluation benchmarks, and artifact registries.

## Directory Structure

- [`datasets/`](./datasets/README.md): Specifications, download scripts, and licenses for public civic datasets (e.g. RDD2022, TACO).
- [`preprocessing/`](./preprocessing/README.md): Image normalization, augmentation, feature extraction, and text cleaning pipelines.
- [`training/`](./training/README.md): Training scripts for vision baselines, text classifiers, and multimodal fusion architectures.
- [`evaluation/`](./evaluation/README.md): Standard evaluation harnesses, confusion matrices, latency benchmarks, and error analysis.
- [`experiments/`](./experiments/README.md): Hyperparameter logs, ablation studies, and comparative experimental results.

## Current Stage: Phase 0 (Bootstrap)

> [!NOTE]
> In Phase 0, heavy ML libraries (PyTorch, Ultralytics, Transformers, OpenCV, Sentence-Transformers) and large datasets/weights are **deliberately NOT installed or committed**.
> Concrete ML components will be introduced starting in Sprint 3 (Vision baseline) and Sprint 4 (Text baseline).
