# External archive pointer

Heavy historical and scratch outputs live **outside** the repository:

```
../gaga_psylo_external_archive/
├── final_cleanup_2026-06-30/               # F2 (2026-06-30)
│   ├── layer3_workbench_scratch/           # L3 _workbench_* dirs
│   ├── layer3_early_validation/            # 671_g4_validation_001
│   ├── layer2_archive_zip/                 # Archive.zip
│   └── layer1_qc_outputs/                # L1 motive_qc/outputs tree
├── layer2_outputs_archive_2026-06-30/      # ~22 GB historical L2 outputs (Stage R1)
└── archive_2026-06-30_cleanup_stage_B/     # Superseded L3 batches, L2.5 scratch
    └── layer3_superseded_batches/
```

**Config keys:** `external_archive.*` in [`config/paths.yaml`](../../config/paths.yaml)

**Move log:** [`docs/research_recovery/FINAL_CLEANUP_MOVE_LOG.csv`](../research_recovery/FINAL_CLEANUP_MOVE_LOG.csv)

**Do not move back into the repo** without an explicit rollback plan.

**Not archived in F2:** canonical batch, smoke batch (on disk in repo), L2 sessions, L2.5 exports, poster figures/evidence, raw data.
