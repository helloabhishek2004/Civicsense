"""Manually labeled pilot evaluation pairs.

These labels were created manually for initial retrieval evaluation.
They are NOT ground truth — they are expert-labeled estimates that
should be verified against actual ground truth in production.

Source images: datasets/benchmark_v1/images/

Label schema:
  - same_physical: Same physical defect, different photo
  - same_category: Same category, different defect instance
  - different_category: Different categories
  - visually_similar: Visually similar but geographically distant
  - same_issue_different_view: Different angles of the same defect
"""

# Manually labeled pairs from benchmark_v1
# Each pair is: (anchor_filename, candidate_filename, label)
MANUALLY_LABELED_PAIRS = [
    # Pothole pairs (same category)
    ("pilot_bost311_101006435365.jpg", "pilot_bost311_101006466867.jpg", "same_category"),
    ("pilot_bost311_101006435365.jpg", "pilot_bost311_101006508563.jpg", "same_category"),

    # Cross-category pairs
    ("pilot_bost311_101006435365.jpg", "pilot_bost311_101006512345.jpg", "different_category"),
]
