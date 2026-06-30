# External archive pointer

Heavy historical outputs live **outside** the repository:

```
../gaga_psylo_external_archive/
├── layer2_outputs_archive_2026-06-30/          # ~22 GB historical Layer 2 outputs (Stage R1)
└── archive_2026-06-30_cleanup_stage_B/       # Superseded L3 batches, L2.5 scratch
    └── layer3_superseded_batches/              # 5 pre-193319 batch folders
```

**Config keys:** `external_archive.*` in [`config/paths.yaml`](../../config/paths.yaml)

**Do not move back into the repo** without an explicit rollback plan.

**Future W3b target (not executed):** `workspace_simplification_2026-06-30/` for L3 workbench scratch.
