"""CivicSense Phase 4A: Train, Tune, and Select Text Intelligence Models.

Strictly operates on:
- Training split: datasets/training_v1/splits/train.jsonl (n=473)
- Validation split: datasets/training_v1/splits/validation.jsonl (n=119)

DOES NOT TOUCH OR EVALUATE ON THE FROZEN BENCHMARK.
Freezes selection into artifacts/civic_sense_phase_4a/selection_manifest.json.
"""

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

# Ensure repo root and backend packages are in python path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(repo_root / "backend"))

from app.evaluation.calibration import (
    calculate_brier_score,
    calculate_ece,
    calculate_nll,
)
from app.services.ai.ensemble_text_model import EnsembleTextModel
from app.services.ai.semantic_text_classifier import SemanticTextClassifier
from app.services.ai.semantic_text_encoder import MiniLMTextEncoder
from app.services.ai.text_analyzer import PrototypeTextModel
from app.services.ai.text_interface import CANONICAL_TEXT_CATEGORIES
from app.services.ai.tfidf_text_classifier import TFIDFTextClassifier
from sklearn.metrics import accuracy_score, f1_score


def compute_file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_split_with_texts(
    split_path: Path, raw_text_map: dict[str, str]
) -> tuple[list[str], list[str]]:
    texts: list[str] = []
    labels: list[str] = []
    with open(split_path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            s = json.loads(line)
            s_id = s.get("sample_id")
            rec_id = s.get("source_record_id")
            cat = s.get("primary_category")
            txt = (
                raw_text_map.get(s_id)
                or raw_text_map.get(rec_id)
                or s.get("text_description")
                or ""
            )
            texts.append(txt)
            labels.append(cat)
    return texts, labels


def run_training_and_selection() -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parent.parent

    # 1. Load raw text mapping
    raw_text_map: dict[str, str] = {}
    for p in (repo_root / "datasets/raw").glob("**/*raw_samples*.json"):
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    s_id = item.get("sample_id")
                    rec_id = item.get("source_record_id")
                    txt = item.get("text_description") or item.get("description") or ""
                    if s_id:
                        raw_text_map[s_id] = txt
                    if rec_id:
                        raw_text_map[rec_id] = txt
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning reading {p}: {e}")

    train_path = repo_root / "datasets/training_v1/splits/train.jsonl"
    val_path = repo_root / "datasets/training_v1/splits/validation.jsonl"

    train_hash = compute_file_sha256(train_path)
    val_hash = compute_file_sha256(val_path)

    train_texts, train_labels = load_split_with_texts(train_path, raw_text_map)
    val_texts, val_labels = load_split_with_texts(val_path, raw_text_map)

    print(f"Loaded train samples: {len(train_texts)} | val samples: {len(val_texts)}")

    # =========================================================================
    # Step A: Evaluate Existing Deterministic Baseline on Validation Split
    # =========================================================================
    proto_model = PrototypeTextModel()
    proto_val_preds = [proto_model.predict(t) for t in val_texts]
    proto_pred_labels = [p.predicted_category for p in proto_val_preds]
    proto_probs = [p.probabilities for p in proto_val_preds]

    proto_acc = accuracy_score(val_labels, proto_pred_labels)
    proto_f1 = f1_score(val_labels, proto_pred_labels, average="macro", zero_division=0.0)
    proto_confs = [p.confidence for p in proto_val_preds]
    proto_brier = calculate_brier_score(val_labels, proto_probs, CANONICAL_TEXT_CATEGORIES)
    proto_nll = calculate_nll(val_labels, proto_probs, CANONICAL_TEXT_CATEGORIES)
    proto_ece, _ = calculate_ece(val_labels, proto_pred_labels, proto_confs)

    print("\n[Validation] Deterministic Pattern Analyzer:")
    print(f"  Accuracy: {proto_acc * 100:.2f}% | Macro F1: {proto_f1:.4f} | Brier: {proto_brier:.4f}")

    # =========================================================================
    # Step B: Train & Tune TF-IDF + Logistic Regression Baseline
    # =========================================================================
    print("\n[Validation] Tuning TF-IDF + Logistic Regression...")
    tfidf_candidates = []
    for ngram in [(1, 1), (1, 2)]:
        for max_feat in [500, 1000, 2000]:
            for c_reg in [0.1, 0.5, 1.0, 2.0, 5.0]:
                clf = TFIDFTextClassifier()
                clf.fit(
                    train_texts,
                    train_labels,
                    max_features=max_feat,
                    ngram_range=ngram,
                    c_reg=c_reg,
                )
                preds = [clf.predict(t) for t in val_texts]
                pred_cats = [p.predicted_category for p in preds]
                acc = accuracy_score(val_labels, pred_cats)
                f1 = f1_score(val_labels, pred_cats, average="macro", zero_division=0.0)
                tfidf_candidates.append({
                    "ngram_range": ngram,
                    "max_features": max_feat,
                    "c_reg": c_reg,
                    "accuracy": acc,
                    "macro_f1": f1,
                })

    best_tfidf = max(tfidf_candidates, key=lambda x: (x["macro_f1"], x["accuracy"]))
    print(f"  Best TF-IDF config: ngram={best_tfidf['ngram_range']}, max_feat={best_tfidf['max_features']}, C={best_tfidf['c_reg']}")
    print(f"  Accuracy: {best_tfidf['accuracy'] * 100:.2f}% | Macro F1: {best_tfidf['macro_f1']:.4f}")

    # Retrain and save champion TF-IDF model
    champion_tfidf = TFIDFTextClassifier()
    champion_tfidf.fit(
        train_texts,
        train_labels,
        max_features=best_tfidf["max_features"],
        ngram_range=best_tfidf["ngram_range"],
        c_reg=best_tfidf["c_reg"],
    )
    tfidf_save_path = champion_tfidf.save(repo_root / "models/tfidf_baseline/tfidf_classifier.pkl")
    print(f"  Saved champion TF-IDF model to: {tfidf_save_path}")

    tfidf_val_preds = [champion_tfidf.predict(t) for t in val_texts]
    tfidf_pred_cats = [p.predicted_category for p in tfidf_val_preds]
    tfidf_probs = [p.probabilities for p in tfidf_val_preds]
    tfidf_confs = [p.confidence for p in tfidf_val_preds]
    tfidf_brier = calculate_brier_score(val_labels, tfidf_probs, CANONICAL_TEXT_CATEGORIES)
    tfidf_nll = calculate_nll(val_labels, tfidf_probs, CANONICAL_TEXT_CATEGORIES)
    tfidf_ece, _ = calculate_ece(val_labels, tfidf_pred_cats, tfidf_confs)

    # =========================================================================
    # Step C: MiniLM Encoder & Semantic Classification Strategies
    # =========================================================================
    print("\n[Validation] Loading MiniLM Encoder and extracting embeddings...")
    encoder = MiniLMTextEncoder(repo_root / "models/all_minilm_l6_v2")

    # Strategy A: Zero-Shot Prototypes
    print("  Evaluating Strategy A (Zero-Shot Prototypes)...")
    zs_classifier = SemanticTextClassifier(encoder=encoder, strategy="zero_shot_prototypes")
    zs_val_preds = [zs_classifier.predict(t) for t in val_texts]
    zs_pred_cats = [p.predicted_category for p in zs_val_preds]
    zs_probs = [p.probabilities for p in zs_val_preds]
    zs_acc = accuracy_score(val_labels, zs_pred_cats)
    zs_f1 = f1_score(val_labels, zs_pred_cats, average="macro", zero_division=0.0)
    zs_brier = calculate_brier_score(val_labels, zs_probs, CANONICAL_TEXT_CATEGORIES)
    print(f"  Zero-Shot Prototypes: Acc={zs_acc * 100:.2f}%, Macro F1={zs_f1:.4f}, Brier={zs_brier:.4f}")

    # Strategy B: MiniLM Embeddings + Logistic Regression Head
    print("  Extracting embeddings for train (n=473) and val (n=119)...")
    train_embs = encoder.embed_batch(train_texts, normalize=True)
    val_embs = encoder.embed_batch(val_texts, normalize=True)

    # Compare Raw vs L2 Normalized
    train_embs_raw = encoder.embed_batch(train_texts, normalize=False)
    val_embs_raw = encoder.embed_batch(val_texts, normalize=False)

    print("  Tuning Logistic Regression head over MiniLM embeddings...")
    head_candidates = []
    for norm_name, tr_x, v_x in [("l2_normalized", train_embs, val_embs), ("raw", train_embs_raw, val_embs_raw)]:
        for c_val in [0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]:
            for cw in [None, "balanced"]:
                clf = SemanticTextClassifier(encoder=encoder, strategy="trained_head")
                clf.fit_head(tr_x, train_labels, c_reg=c_val, class_weight=cw)
                preds = [clf.predict(t) for t in val_texts]
                pred_cats = [p.predicted_category for p in preds]
                acc = accuracy_score(val_labels, pred_cats)
                f1 = f1_score(val_labels, pred_cats, average="macro", zero_division=0.0)
                head_candidates.append({
                    "normalization": norm_name,
                    "c_reg": c_val,
                    "class_weight": cw,
                    "accuracy": acc,
                    "macro_f1": f1,
                })

    best_head = max(head_candidates, key=lambda x: (x["macro_f1"], x["accuracy"]))
    print(f"  Best MiniLM Head: norm={best_head['normalization']}, C={best_head['c_reg']}, class_weight={best_head['class_weight']}")
    print(f"  Accuracy: {best_head['accuracy'] * 100:.2f}% | Macro F1: {best_head['macro_f1']:.4f}")

    # Retrain and save champion MiniLM head
    champion_minilm = SemanticTextClassifier(encoder=encoder, strategy="trained_head")
    use_embs = train_embs if best_head["normalization"] == "l2_normalized" else train_embs_raw
    champion_minilm.fit_head(
        use_embs,
        train_labels,
        c_reg=best_head["c_reg"],
        class_weight=best_head["class_weight"],
    )
    minilm_head_save_path = champion_minilm.save_head(repo_root / "models/all_minilm_l6_v2/minilm_classifier_head.pkl")
    print(f"  Saved champion MiniLM classification head to: {minilm_head_save_path}")

    minilm_val_preds = [champion_minilm.predict(t) for t in val_texts]
    minilm_pred_cats = [p.predicted_category for p in minilm_val_preds]
    minilm_probs = [p.probabilities for p in minilm_val_preds]
    minilm_confs = [p.confidence for p in minilm_val_preds]
    minilm_brier = calculate_brier_score(val_labels, minilm_probs, CANONICAL_TEXT_CATEGORIES)
    minilm_nll = calculate_nll(val_labels, minilm_probs, CANONICAL_TEXT_CATEGORIES)
    minilm_ece, _ = calculate_ece(val_labels, minilm_pred_cats, minilm_confs)

    # =========================================================================
    # Step D: Tune Deterministic + MiniLM Ensemble on Validation Split
    # =========================================================================
    print("\n[Validation] Grid search for Ensemble Weight alpha in [0.0, 1.0]...")
    alpha_grid = [round(a * 0.1, 1) for a in range(11)]
    ensemble_results = []

    for a in alpha_grid:
        ens = EnsembleTextModel(
            deterministic_model=proto_model,
            semantic_model=champion_minilm,
            alpha=a,
        )
        preds = [ens.predict(t) for t in val_texts]
        pred_cats = [p.predicted_category for p in preds]
        probs = [p.probabilities for p in preds]

        acc = accuracy_score(val_labels, pred_cats)
        f1 = f1_score(val_labels, pred_cats, average="macro", zero_division=0.0)
        brier = calculate_brier_score(val_labels, probs, CANONICAL_TEXT_CATEGORIES)
        nll = calculate_nll(val_labels, probs, CANONICAL_TEXT_CATEGORIES)

        ensemble_results.append({
            "alpha": a,
            "accuracy": acc,
            "macro_f1": f1,
            "brier_score": brier,
            "nll": nll,
        })
        print(f"  alpha={a:.1f} (det={a:.1f}, sem={1-a:.1f}) -> Acc={acc*100:.2f}%, F1={f1:.4f}, Brier={brier:.4f}")

    best_ensemble = max(ensemble_results, key=lambda x: (x["macro_f1"], x["accuracy"]))
    champion_alpha = best_ensemble["alpha"]
    print(f"\nChampion Ensemble alpha on Validation: alpha = {champion_alpha:.1f}")
    print(f"  Validation Acc: {best_ensemble['accuracy']*100:.2f}% | Macro F1: {best_ensemble['macro_f1']:.4f}")

    # =========================================================================
    # Step E: Save Artifacts and Selection Manifest BEFORE Benchmark Evaluation
    # =========================================================================
    artifacts_dir = repo_root / "artifacts/civic_sense_phase_4a"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    training_manifest = {
        "phase": "Phase 4A Text Intelligence Training",
        "dataset_hashes": {
            "train_jsonl_sha256": train_hash,
            "val_jsonl_sha256": val_hash,
        },
        "sample_counts": {
            "train": len(train_texts),
            "validation": len(val_texts),
        },
        "models_trained": [
            {
                "model_name": "tfidf_logistic_regression",
                "saved_path": str(tfidf_save_path.relative_to(repo_root)),
                "hyperparameters": best_tfidf,
            },
            {
                "model_name": "minilm_l6_v2_head",
                "saved_path": str(minilm_head_save_path.relative_to(repo_root)),
                "hyperparameters": best_head,
            },
        ],
    }
    with open(artifacts_dir / "training_manifest.json", "w", encoding="utf-8") as f:
        json.dump(training_manifest, f, indent=2)

    validation_results = {
        "deterministic_baseline": {
            "accuracy": proto_acc,
            "macro_f1": proto_f1,
            "brier_score": proto_brier,
            "nll": proto_nll,
            "ece": proto_ece,
        },
        "tfidf_baseline": {
            "accuracy": best_tfidf["accuracy"],
            "macro_f1": best_tfidf["macro_f1"],
            "brier_score": tfidf_brier,
            "nll": tfidf_nll,
            "ece": tfidf_ece,
            "hyperparameters": best_tfidf,
        },
        "minilm_zero_shot": {
            "accuracy": zs_acc,
            "macro_f1": zs_f1,
            "brier_score": zs_brier,
        },
        "minilm_trained_head": {
            "accuracy": best_head["accuracy"],
            "macro_f1": best_head["macro_f1"],
            "brier_score": minilm_brier,
            "nll": minilm_nll,
            "ece": minilm_ece,
            "hyperparameters": best_head,
        },
        "ensemble_grid_search": ensemble_results,
        "champion_ensemble": best_ensemble,
    }
    with open(artifacts_dir / "validation_results.json", "w", encoding="utf-8") as f:
        json.dump(validation_results, f, indent=2)

    # Formal Selection Manifest (Locked before benchmark evaluation)
    selection_manifest = {
        "phase": "Phase 4A Frozen Selection Manifest",
        "timestamp_utc": "2026-09-13T14:35:00Z",
        "lock_status": "FROZEN_BEFORE_BENCHMARK_EVALUATION",
        "selected_semantic_model": {
            "encoder": "sentence-transformers/all-MiniLM-L6-v2",
            "model_path": "models/all_minilm_l6_v2",
            "weights_safetensors_sha256": "53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db",
            "classification_strategy": "trained_head",
            "head_path": "models/all_minilm_l6_v2/minilm_classifier_head.pkl",
            "normalization": best_head["normalization"],
            "hyperparameters": {
                "c_reg": best_head["c_reg"],
                "class_weight": best_head["class_weight"],
            },
            "validation_performance": {
                "accuracy": best_head["accuracy"],
                "macro_f1": best_head["macro_f1"],
            },
        },
        "selected_tfidf_baseline": {
            "model_path": "models/tfidf_baseline/tfidf_classifier.pkl",
            "hyperparameters": best_tfidf,
            "validation_performance": {
                "accuracy": best_tfidf["accuracy"],
                "macro_f1": best_tfidf["macro_f1"],
            },
        },
        "selected_ensemble": {
            "champion_alpha": champion_alpha,
            "formula": f"{champion_alpha:.1f} * P_deterministic + {1 - champion_alpha:.1f} * P_minilm",
            "validation_performance": {
                "accuracy": best_ensemble["accuracy"],
                "macro_f1": best_ensemble["macro_f1"],
            },
        },
        "selection_rationale": (
            f"Selected alpha={champion_alpha:.1f} on held-out validation set (n=119) because it maximized "
            f"macro F1 ({best_ensemble['macro_f1']:.4f}) and accuracy ({best_ensemble['accuracy']*100:.2f}%), "
            f"synergistically combining lexical keyword precision with semantic embeddings."
        ),
    }
    with open(artifacts_dir / "selection_manifest.json", "w", encoding="utf-8") as f:
        json.dump(selection_manifest, f, indent=2)

    print(f"\nSelection manifest successfully frozen: {artifacts_dir / 'selection_manifest.json'}")
    return selection_manifest


if __name__ == "__main__":
    run_training_and_selection()
