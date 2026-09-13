"""CivicSense Dataset Curation & Benchmark Pipeline Tooling."""

from scripts.datasets.deduplicate_benchmark import (
    deduplicate_exact,
    deduplicate_perceptual,
    hamming_distance,
    run_deduplication,
)
from scripts.datasets.normalize_annotations import (
    MappingOutcome,
    NormalizedAnnotationRecord,
    normalize_annotation,
)
from scripts.datasets.source_registry import (
    DATASET_REGISTRY,
    SourceMetadata,
    get_source,
    list_sources,
)
from scripts.datasets.validate_images import (
    ImageValidationResult,
    compute_dhash,
    validate_image_file,
)

__all__ = [
    "DATASET_REGISTRY",
    "SourceMetadata",
    "get_source",
    "list_sources",
    "MappingOutcome",
    "NormalizedAnnotationRecord",
    "normalize_annotation",
    "ImageValidationResult",
    "validate_image_file",
    "compute_dhash",
    "deduplicate_exact",
    "deduplicate_perceptual",
    "hamming_distance",
    "run_deduplication",
]
