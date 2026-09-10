# CivicSense Research Documentation

This directory houses the academic, experimentation, and benchmarking foundations for CivicSense.

## Core Research Questions

- **RQ1 (Edge Feasibility)**: Can lightweight image processing and inference execute on consumer mobile devices with acceptable latency (<250ms) and power consumption for civic categories?
- **RQ2 (Multimodal Value)**: Does multimodal fusion (visual + textual + location features) achieve statistically significant improvements in civic classification accuracy compared to vision-only or text-only unimodal baselines?
- **RQ3 (Conflict & Disagreement)**: Can cross-modal divergence (e.g. text reports pothole, image classified as surface crack) reliably detect ambiguous reports that require human-in-the-loop review?
- **RQ4 (Geospatial & Historical Prioritization)**: Does incorporating historical recurrence, report density, and environmental context improve civic priority ranking accuracy over static severity scores?
- **RQ5 (Edge vs. Cloud Trade-off)**: What is the empirical trade-off between client-side bandwidth reduction and server-side inference workload in a hybrid architecture vs. a pure cloud architecture?

## Current Status (Phase 0)

All research datasets (e.g. RDD2022, TACO), model training pipelines, and benchmarking scripts are **PLANNED** for subsequent sprints. No datasets or model weights are stored in Phase 0.
