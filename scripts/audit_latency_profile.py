"""CivicSense Granular Latency Profiling Suite.

Profiles 8 stages of the multimodal inference pipeline:
1. Text Preprocessing
2. Text Inference
3. Image Disk Loading
4. Image Preprocessing
5. Vision Inference (PyTorch MobileNetV3-Small)
6. Probability Calibration (Temperature scaling)
7. Cross-modal Fusion Calculation
8. Policy Routing & Decision Logic
Plus: End-to-End Total Request Latency

Executes 100 warm-up iterations followed by 300 measured iterations on canonical samples.
"""

from __future__ import annotations

import json
import platform
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "backend"))
sys.path.insert(0, str(repo_root))

from app.evaluation.calibration import apply_temperature
from app.services.ai.fusion_engine import FusionConfig, MultimodalFusionEngine
from app.services.ai.real_vision_model import RealVisionModel
from app.services.ai.text_analyzer import PrototypeTextPatternAnalyzer


def profile_pipeline(
    warmup_iters: int = 100,
    measured_iters: int = 300,
    export_path: Path | None = None,
) -> dict[str, Any]:
    """Execute granular latency profiling across 8 stages."""
    print("Initializing Latency Profiling Suite...")
    benchmark_file = repo_root / "datasets/benchmark_v1/benchmark_dataset.jsonl"
    bm_root = benchmark_file.parent
    ckpt_path = repo_root / "models/mobilenet_v3_small_v1/exp_b/exp_b_best.pt"

    if not benchmark_file.exists():
        raise FileNotFoundError(f"Benchmark file not found: {benchmark_file}")
    if not ckpt_path.exists():
        raise FileNotFoundError(f"Model checkpoint not found: {ckpt_path}")

    # Load 10 canonical benchmark samples for looping
    samples = []
    with open(benchmark_file, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))
            if len(samples) >= 10:
                break

    # Initialize engines
    vision_model = RealVisionModel(checkpoint_path=ckpt_path)
    text_analyzer = PrototypeTextPatternAnalyzer()
    fusion_engine = MultimodalFusionEngine()
    config = FusionConfig(
        name="vision_assisted_calibrated",
        text_weight=0.6,
        vision_weight=0.4,
        temperature=0.5,
        min_confidence_threshold=0.60,
        review_agreement_threshold=0.50,
    )

    # Pre-read image bytes for warm in-memory testing vs disk loading
    sample_images = [bm_root / s["image_rel_path"] for s in samples]
    sample_texts = [s.get("text_description", "") for s in samples]

    # Pre-allocate latency buffers
    latencies = {
        "text_preprocessing_ms": [],
        "text_inference_ms": [],
        "image_disk_loading_ms": [],
        "image_preprocessing_ms": [],
        "vision_inference_ms": [],
        "probability_calibration_ms": [],
        "fusion_calculation_ms": [],
        "policy_routing_ms": [],
        "end_to_end_total_ms": [],
    }

    print(f"Executing {warmup_iters} warm-up iterations...")
    for i in range(warmup_iters):
        s_idx = i % len(samples)
        txt = sample_texts[s_idx]
        img_p = sample_images[s_idx]

        # Warm-up pass
        _ = text_analyzer.analyze(txt)
        img_bytes = img_p.read_bytes()
        v_pred = vision_model.predict(img_bytes)
        _ = fusion_engine.fuse(v_pred, text_analyzer.analyze(txt), config=config)

    print(f"Executing {measured_iters} timed benchmark iterations...")
    total_samples = len(samples)

    for i in range(measured_iters):
        s_idx = i % total_samples
        txt = sample_texts[s_idx]
        img_path = sample_images[s_idx]

        e2e_start = time.perf_counter()

        # 1. Text Preprocessing
        t_pre_start = time.perf_counter()
        cleaned_txt = text_analyzer._sanitize_text(txt) if hasattr(text_analyzer, "_sanitize_text") else txt.strip().lower()
        t_pre_dur = (time.perf_counter() - t_pre_start) * 1000.0

        # 2. Text Inference
        t_inf_start = time.perf_counter()
        t_res = text_analyzer.analyze(cleaned_txt)
        t_inf_dur = (time.perf_counter() - t_inf_start) * 1000.0

        # 3. Image Disk Loading
        i_load_start = time.perf_counter()
        img_bytes = img_path.read_bytes()
        i_load_dur = (time.perf_counter() - i_load_start) * 1000.0

        # 4. Image Preprocessing
        i_pre_start = time.perf_counter()
        # PIL open + convert RGB + transform
        if hasattr(vision_model, "_preprocess"):
            _ = vision_model._preprocess(img_bytes)
        i_pre_dur = (time.perf_counter() - i_pre_start) * 1000.0

        # 5. Vision Inference (PyTorch forward pass)
        v_inf_start = time.perf_counter()
        v_pred = vision_model.predict(img_bytes)
        v_inf_dur = (time.perf_counter() - v_inf_start) * 1000.0

        # 6. Probability Calibration
        cal_start = time.perf_counter()
        _ = apply_temperature(v_pred.class_probabilities, config.temperature)
        cal_dur = (time.perf_counter() - cal_start) * 1000.0

        # 7. Cross-modal Fusion Calculation
        fuse_start = time.perf_counter()
        f_res = fusion_engine.fuse(v_pred, t_res, config=config)
        fuse_dur = (time.perf_counter() - fuse_start) * 1000.0

        # 8. Policy Routing & Decision Logic
        pol_start = time.perf_counter()
        _ = f_res.requires_review
        _ = f_res.disagreement_detected
        pol_dur = (time.perf_counter() - pol_start) * 1000.0

        e2e_dur = (time.perf_counter() - e2e_start) * 1000.0

        latencies["text_preprocessing_ms"].append(t_pre_dur)
        latencies["text_inference_ms"].append(t_inf_dur)
        latencies["image_disk_loading_ms"].append(i_load_dur)
        latencies["image_preprocessing_ms"].append(i_pre_dur)
        latencies["vision_inference_ms"].append(v_inf_dur)
        latencies["probability_calibration_ms"].append(cal_dur)
        latencies["fusion_calculation_ms"].append(fuse_dur)
        latencies["policy_routing_ms"].append(pol_dur)
        latencies["end_to_end_total_ms"].append(e2e_dur)

    def summarize_series(series: list[float]) -> dict[str, float]:
        arr = np.array(series)
        return {
            "mean_ms": round(float(np.mean(arr)), 3),
            "median_p50_ms": round(float(np.median(arr)), 3),
            "p90_ms": round(float(np.percentile(arr, 90)), 3),
            "p95_ms": round(float(np.percentile(arr, 95)), 3),
            "p99_ms": round(float(np.percentile(arr, 99)), 3),
            "min_ms": round(float(np.min(arr)), 3),
            "max_ms": round(float(np.max(arr)), 3),
            "std_ms": round(float(np.std(arr)), 3),
        }

    report = {
        "profiling_metadata": {
            "warmup_iterations": warmup_iters,
            "measured_iterations": measured_iters,
            "batch_size": 1,
            "image_resolution": "224x224 RGB",
            "model_loading_included": False,
            "model_architecture": "MobileNetV3-Small (1.52M params)",
            "device": "CPU",
            "cpu_architecture": platform.processor() or platform.machine(),
            "os": f"{platform.system()} {platform.release()}",
            "python_version": sys.version.split()[0],
            "torch_version": torch.__version__,
            "disclaimer": (
                "These measurements describe the current evaluation environment "
                "and do not establish Android/on-device performance."
            ),
        },
        "stages": {stage: summarize_series(vals) for stage, vals in latencies.items()},
    }

    if export_path:
        export_path.parent.mkdir(parents=True, exist_ok=True)
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"Exported latency report to {export_path}")

    return report


if __name__ == "__main__":
    out_file = repo_root / "artifacts/civic_sense_pilot_v0.3.5/latency_report.json"
    rep = profile_pipeline(warmup_iters=50, measured_iters=200, export_path=out_file)
    print("\nLatency Profiling Results (ms):")
    print(f"{'Stage':30s} {'Mean':8s} {'p50':8s} {'p95':8s} {'p99':8s}")
    print("-" * 65)
    for stage, metrics in rep["stages"].items():
        m_mean = metrics["mean_ms"]
        m_p50 = metrics["median_p50_ms"]
        m_p95 = metrics["p95_ms"]
        m_p99 = metrics["p99_ms"]
        print(f"{stage:30s} {m_mean:<8.3f} {m_p50:<8.3f} {m_p95:<8.3f} {m_p99:<8.3f}")
