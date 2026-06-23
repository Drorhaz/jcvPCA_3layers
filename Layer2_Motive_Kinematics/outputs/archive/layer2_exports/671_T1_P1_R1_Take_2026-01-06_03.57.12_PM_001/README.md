# Layer 2 per-session export

This folder is a per-session Layer 2 export package for the post–Layer 2 segmentation notebook (`notebooks/post_layer2_segmentation_review.ipynb`).

## Files

- **Main signal parquet:** `layer2_session_filtered_rotvecs.parquet`
- **Link manifest:** `layer2_session_link_manifest.csv`
- **Session summary (JSON):** `layer2_session_summary.json`
- **Human report:** `layer2_session_report.md`
- **Integrity audit:** `layer2_session_integrity_audit.csv`

## External input

Provide the matching Layer 1 raw QC mask for this session separately when running the segmentation notebook.

This export does not combine sessions and is not Layer 3-ready.
