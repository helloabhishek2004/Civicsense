# CivicSense Phase 4A — Model and Runtime Selection Audit Report

## Executive Summary

This report documents the architectural, licensing, and runtime evaluation of lightweight transformer encoders for Phase 4A Semantic Text Intelligence.

### Final Model Selection Decision
> **SELECTED MODEL**: `sentence-transformers/all-MiniLM-L6-v2`
- **Status**: Fully staged offline under `models/all_minilm_l6_v2/`.
- **Integrity Verification**: `model.safetensors` verified with SHA-256: `53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db`.
- **License**: Apache 2.0 (Permissive open-source, production safe).
- **Parameters**: 22,713,216 parameters (Locally measured).
- **Storage**: 90.87 MB FP32 safetensors (Locally measured); ~22.7 MB INT8 quantized (Estimated).
- **Inference Execution**: Fully offline execution via standard PyTorch and Transformers without remote dependencies.

---

## 1. Candidate Encoder Comparative Audit

| Attribute | `all-MiniLM-L6-v2` (Selected) | `paraphrase-MiniLM-L6-v2` | `bge-small-en-v1.5` | `all-MiniLM-L12-v2` |
| :--- | :---: | :---: | :---: | :---: |
| **Architecture** | 6-layer MiniLM Transformer | 6-layer MiniLM Transformer | 12-layer BGE Transformer | 12-layer MiniLM Transformer |
| **Parameters** | **22.7M** [Locally measured] | 22.7M [Published] | 33.5M [Published] | 33.4M [Published] |
| **Embedding Dim** | **384** [Locally measured] | 384 [Published] | 384 [Published] | 384 [Published] |
| **Weights Size** | **90.87 MB** [Locally measured] | ~90.9 MB [Estimated] | ~134 MB [Estimated] | ~134 MB [Estimated] |
| **INT8 Quantized Size** | **~22.7 MB** [Estimated] | ~22.7 MB [Estimated] | ~33.5 MB [Estimated] | ~33.5 MB [Estimated] |
| **License** | **Apache 2.0** | Apache 2.0 | MIT | Apache 2.0 |
| **Offline Loading** | **Verified** [Locally measured] | Supported [Published] | Supported [Published] | Supported [Published] |
| **Mobile Edge Feasibility** | **High** (<25MB APK footprint) | High | Moderate | Moderate |
| **Head Type** | Encoder Only | Encoder Only | Encoder Only | Encoder Only |

---

## 2. Local Staging & Hash Verification

All weights and tokenizer assets for `all-MiniLM-L6-v2` are staged under `models/all_minilm_l6_v2/`:

| File Name | Size (Bytes) | SHA-256 Hash |
| :--- | :---: | :--- |
| `config.json` | 612 | `953f9c0d463486b10a6871cc2fd59f223b2c70184f49815e7efbcab5d8908b41` |
| `model.safetensors` | 90,868,376 | `53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db` |
| `special_tokens_map.json` | 112 | `303df45a03609e4ead04bc3dc1536d0ab19b5358db685b6f3da123d05ec200e3` |
| `tokenizer.json` | 466,247 | `be50c3628f2bf5bb5e3a7f17b1f74611b2561a3a27eeab05e5aa30f411572037` |
| `tokenizer_config.json` | 350 | `acb92769e8195aabd29b7b2137a9e6d6e25c476a4f15aa4355c233426c61576b` |
| `vocab.txt` | 231,508 | `07eced375cec144d27c900241f3e339478dec958f92fddbc551f295c992038a3` |

---

## 3. Decoupled Architecture Design
- **Universal TextModel Interface**: Exposes `predict(text: str) -> TextPrediction` across canonical 6 classes.
- **Encoder/Classifier Separation**: `MiniLMTextEncoder` handles tokenization and mean-pooled embedding generation; `MiniLMTextClassifier` wraps the classification head.
- **Zero Internet Access at Runtime**: The system enforces `local_files_only=True`, completely preventing runtime HTTP requests to Hugging Face or external services.

---
*Report generated automatically by `scripts/audit_model_selection.py`.*