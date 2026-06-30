"""Shared constants for Layer 2.5 window export and validation."""

WINDOW_MATRIX_FILE = "window_jvcpca_matrix.parquet"
WINDOW_MANIFEST_FILE = "window_export_manifest.json"

MATRIX_IDENTITY_COLUMNS = ["session_id", "run_label", "frame", "time_sec"]
MATRIX_SOURCE_COLUMNS = [
    "rx_filtered_analysis",
    "ry_filtered_analysis",
    "rz_filtered_analysis",
]
FEATURE_AXES = ("rx", "ry", "rz")
