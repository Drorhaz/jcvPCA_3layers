"""CLI entry point for stage-based pipeline execution."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from layer2_motive.batch import (
    batch_run_stage01,
    batch_run_stage02,
    batch_run_stage03,
    batch_run_stage04,
    batch_run_stage05,
    batch_run_stage06,
    batch_run_stage07,
    batch_run_stage08,
    discover_csv_inputs,
)
from layer2_motive.export_layer2 import export_layer2_sessions
from layer2_motive.stages.stage00 import run_stage_00
from layer2_motive.stages.stage01 import run_stage_01
from layer2_motive.stages.stage02 import run_stage_02
from layer2_motive.stages.stage03 import run_stage_03
from layer2_motive.stages.stage04 import run_stage_04
from layer2_motive.stages.stage05 import run_stage_05
from layer2_motive.stages.stage06 import run_stage_06
from layer2_motive.stages.stage07 import run_stage_07
from layer2_motive.stages.stage08 import run_stage_08
from layer2_motive.validation import HardStopError

STAGE_ORDER = ["00", "01", "02", "03", "04", "05", "06", "07", "08"]
IMPLEMENTED_STAGES = {"00", "01", "02", "03", "04", "05", "06", "07", "08"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="layer2-motive",
        description="Layer 2 Motive solved-skeleton kinematics pipeline",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("run-stage", "run-until", "run-all"):
        cmd = sub.add_parser(name, help=f"{name} pipeline stages")
        cmd.add_argument("--input", required=True, help="Path to Motive mixed CSV")
        cmd.add_argument("--output-dir", default="outputs", help="Output directory")
        cmd.add_argument("--stage", help="Stage id, e.g. 00 (run-stage / run-until only)")
        cmd.add_argument("--config", help="Path to Layer 2 YAML config")
        cmd.add_argument("--cutoff-hz", type=float, default=10.0)
        cmd.add_argument("--filter-order", type=int, default=4)
        cmd.add_argument(
            "--allow-short-gap-interpolation",
            action="store_true",
            help="Enable short-gap quaternion interpolation (off by default)",
        )

    batch = sub.add_parser(
        "batch-run",
        help="Run Stage 00–01 on multiple CSV files and write a generic index",
    )
    batch.add_argument(
        "--input",
        action="append",
        dest="inputs",
        help="Motive CSV path (repeatable)",
    )
    batch.add_argument(
        "--input-dir",
        help="Directory to scan for CSV files",
    )
    batch.add_argument(
        "--pattern",
        default="*.csv",
        help="Glob pattern when using --input-dir (default: *.csv)",
    )
    batch.add_argument(
        "--no-recursive",
        action="store_true",
        help="Do not scan --input-dir recursively",
    )
    batch.add_argument(
        "--output-root",
        default="outputs",
        help="Root directory for per-file output folders",
    )
    batch.add_argument(
        "--index",
        default="outputs/stage00_01_report_index",
        help="Index output path without extension (writes .md and .csv)",
    )
    batch.add_argument(
        "--force",
        action="store_true",
        help="Re-run even when Stage 01 report already exists",
    )
    batch.add_argument("--config", help="Path to Layer 2 YAML config")

    batch02 = sub.add_parser(
        "batch-run-stage02",
        help="Run Stage 02 on multiple CSV files with existing Stage 00–01 outputs",
    )
    batch02.add_argument(
        "--input",
        action="append",
        dest="inputs",
        help="Motive CSV path (repeatable)",
    )
    batch02.add_argument(
        "--input-dir",
        help="Directory to scan for CSV files",
    )
    batch02.add_argument(
        "--pattern",
        default="*.csv",
        help="Glob pattern when using --input-dir (default: *.csv)",
    )
    batch02.add_argument(
        "--no-recursive",
        action="store_true",
        help="Do not scan --input-dir recursively",
    )
    batch02.add_argument(
        "--output-root",
        default="outputs",
        help="Root directory for per-file output folders",
    )
    batch02.add_argument(
        "--index",
        default="outputs/stage02_component_order_index",
        help="Index output path without extension (writes .md and .csv)",
    )
    batch02.add_argument(
        "--force",
        action="store_true",
        help="Re-run Stage 02 even when report already exists",
    )

    batch03 = sub.add_parser(
        "batch-run-stage03",
        help="Run Stage 03 on multiple CSV files with existing Stage 00–02 outputs",
    )
    batch03.add_argument(
        "--input",
        action="append",
        dest="inputs",
        help="Motive CSV path (repeatable)",
    )
    batch03.add_argument(
        "--input-dir",
        help="Directory to scan for CSV files",
    )
    batch03.add_argument(
        "--pattern",
        default="*.csv",
        help="Glob pattern when using --input-dir (default: *.csv)",
    )
    batch03.add_argument(
        "--no-recursive",
        action="store_true",
        help="Do not scan --input-dir recursively",
    )
    batch03.add_argument(
        "--output-root",
        default="outputs",
        help="Root directory for per-file output folders",
    )
    batch03.add_argument(
        "--index",
        default="outputs/stage03_frame_time_index",
        help="Index output path without extension (writes .md and .csv)",
    )
    batch03.add_argument(
        "--force",
        action="store_true",
        help="Re-run Stage 03 even when report already exists",
    )
    batch03.add_argument("--config", help="Path to Layer 2 YAML config")

    batch04 = sub.add_parser(
        "batch-run-stage04",
        help="Run Stage 04 on multiple CSV files with existing Stage 00–03 outputs",
    )
    batch04.add_argument(
        "--input",
        action="append",
        dest="inputs",
        help="Motive CSV path (repeatable)",
    )
    batch04.add_argument(
        "--input-dir",
        help="Directory to scan for CSV files",
    )
    batch04.add_argument(
        "--pattern",
        default="*.csv",
        help="Glob pattern when using --input-dir (default: *.csv)",
    )
    batch04.add_argument(
        "--no-recursive",
        action="store_true",
        help="Do not scan --input-dir recursively",
    )
    batch04.add_argument(
        "--output-root",
        default="outputs",
        help="Root directory for per-file output folders",
    )
    batch04.add_argument(
        "--index",
        default="outputs/stage04_quaternion_qc_index",
        help="Index output path without extension (writes .md and .csv)",
    )
    batch04.add_argument(
        "--force",
        action="store_true",
        help="Re-run Stage 04 even when report already exists",
    )
    batch04.add_argument("--config", help="Path to Layer 2 YAML config")

    batch05 = sub.add_parser(
        "batch-run-stage05",
        help="Run Stage 05 on multiple CSV files with existing Stage 00–04 outputs",
    )
    batch05.add_argument(
        "--input",
        action="append",
        dest="inputs",
        help="Motive CSV path (repeatable)",
    )
    batch05.add_argument(
        "--input-dir",
        help="Directory to scan for CSV files",
    )
    batch05.add_argument(
        "--pattern",
        default="*.csv",
        help="Glob pattern when using --input-dir (default: *.csv)",
    )
    batch05.add_argument(
        "--no-recursive",
        action="store_true",
        help="Do not scan --input-dir recursively",
    )
    batch05.add_argument(
        "--output-root",
        default="outputs",
        help="Root directory for per-file output folders",
    )
    batch05.add_argument(
        "--index",
        default="outputs/stage05_sign_continuity_index",
        help="Index output path without extension (writes .md and .csv)",
    )
    batch05.add_argument(
        "--force",
        action="store_true",
        help="Re-run Stage 05 even when report already exists",
    )
    batch05.add_argument("--config", help="Path to Layer 2 YAML config")

    batch06 = sub.add_parser(
        "batch-run-stage06",
        help="Run Stage 06 on multiple CSV files with existing Stage 00–05 outputs",
    )
    batch06.add_argument(
        "--input",
        action="append",
        dest="inputs",
        help="Motive CSV path (repeatable)",
    )
    batch06.add_argument(
        "--input-dir",
        help="Directory to scan for CSV files",
    )
    batch06.add_argument(
        "--pattern",
        default="*.csv",
        help="Glob pattern when using --input-dir (default: *.csv)",
    )
    batch06.add_argument(
        "--no-recursive",
        action="store_true",
        help="Do not scan --input-dir recursively",
    )
    batch06.add_argument(
        "--output-root",
        default="outputs",
        help="Root directory for per-file output folders",
    )
    batch06.add_argument(
        "--index",
        default="outputs/stage06_relative_quaternion_index",
        help="Index output path without extension (writes .md and .csv)",
    )
    batch06.add_argument(
        "--force",
        action="store_true",
        help="Re-run Stage 06 even when report already exists",
    )
    batch06.add_argument("--config", help="Path to Layer 2 YAML config")

    batch07 = sub.add_parser(
        "batch-run-stage07",
        help="Run Stage 07 on multiple CSV files with existing Stage 00–06 outputs",
    )
    batch07.add_argument(
        "--input",
        action="append",
        dest="inputs",
        help="Motive CSV path (repeatable)",
    )
    batch07.add_argument(
        "--input-dir",
        help="Directory to scan for CSV files",
    )
    batch07.add_argument(
        "--pattern",
        default="*.csv",
        help="Glob pattern when using --input-dir (default: *.csv)",
    )
    batch07.add_argument(
        "--no-recursive",
        action="store_true",
        help="Do not scan --input-dir recursively",
    )
    batch07.add_argument(
        "--output-root",
        default="outputs",
        help="Root directory for per-file output folders",
    )
    batch07.add_argument(
        "--index",
        default="outputs/stage07_rotation_vector_index",
        help="Index output path without extension (writes .md and .csv)",
    )
    batch07.add_argument(
        "--force",
        action="store_true",
        help="Re-run Stage 07 even when report already exists",
    )
    batch07.add_argument("--config", help="Path to Layer 2 YAML config")

    batch08 = sub.add_parser(
        "batch-run-stage08",
        help="Run Stage 08 on multiple CSV files with existing Stage 00–07 outputs",
    )
    batch08.add_argument(
        "--input",
        action="append",
        dest="inputs",
        help="Motive CSV path (repeatable)",
    )
    batch08.add_argument(
        "--input-dir",
        help="Directory to scan for CSV files",
    )
    batch08.add_argument(
        "--pattern",
        default="*.csv",
        help="Glob pattern when using --input-dir (default: *.csv)",
    )
    batch08.add_argument(
        "--no-recursive",
        action="store_true",
        help="Do not scan --input-dir recursively",
    )
    batch08.add_argument(
        "--output-root",
        default="outputs",
        help="Root directory for per-file output folders",
    )
    batch08.add_argument(
        "--index",
        default="outputs/stage08_filtering_index",
        help="Index output path without extension (writes .md and .csv)",
    )
    batch08.add_argument(
        "--force",
        action="store_true",
        help="Re-run Stage 08 even when report already exists",
    )
    batch08.add_argument("--config", help="Path to Layer 2 YAML config")
    batch08.add_argument("--cutoff-hz", type=float, default=None)
    batch08.add_argument("--filter-order", type=int, default=None)

    export_sessions = sub.add_parser(
        "export-layer2-sessions",
        help="Package per-session Layer 2 exports from completed Stage 08 runs",
    )
    export_sessions.add_argument(
        "--output-root",
        default="outputs",
        help="Root directory containing per-run Stage 08 outputs",
    )
    export_sessions.add_argument(
        "--export-root",
        default="outputs/layer2_exports",
        help="Destination root for per-session Layer 2 export folders",
    )
    export_sessions.add_argument(
        "--run-pattern",
        default=None,
        help="Optional substring filter on run folder names (e.g. 671_T1_P1)",
    )
    export_sessions.add_argument(
        "--force",
        action="store_true",
        help="Re-export even when per-session export folder already exists",
    )

    return parser


def _normalize_stage(stage: str | None) -> str:
    if stage is None:
        raise HardStopError("--stage is required")
    stage = stage.strip()
    if len(stage) == 1:
        stage = f"0{stage}"
    if stage not in STAGE_ORDER:
        raise HardStopError(f"Unknown stage {stage!r}")
    return stage


def _run_until(
    stage: str,
    input_csv: Path,
    output_dir: Path,
    config: Path | None,
    *,
    cutoff_hz: float | None = None,
    filter_order: int | None = None,
) -> None:
    parsed = None
    for current in STAGE_ORDER:
        if current not in IMPLEMENTED_STAGES:
            if current <= stage:
                raise HardStopError(
                    f"Stage {current} is not implemented yet; cannot run until {stage}"
                )
            break
        if current == "00":
            parsed = run_stage_00(input_csv, output_dir)
        elif current == "01":
            run_stage_01(input_csv, output_dir, parsed=parsed, config_path=config)
        elif current == "02":
            run_stage_02(input_csv, output_dir, parsed=parsed)
        elif current == "03":
            run_stage_03(input_csv, output_dir, parsed=parsed, config_path=config)
        elif current == "04":
            run_stage_04(input_csv, output_dir, parsed=parsed, config_path=config)
        elif current == "05":
            run_stage_05(input_csv, output_dir, parsed=parsed, config_path=config)
        elif current == "06":
            run_stage_06(input_csv, output_dir, config_path=config)
        elif current == "07":
            run_stage_07(input_csv, output_dir, config_path=config)
        elif current == "08":
            run_stage_08(
                input_csv,
                output_dir,
                config_path=config,
                cutoff_hz=cutoff_hz,
                filter_order=filter_order,
            )
        if current == stage:
            break


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config = Path(args.config) if getattr(args, "config", None) else None

    try:
        if args.command == "batch-run":
            inputs = discover_csv_inputs(
                inputs=[Path(p) for p in args.inputs] if args.inputs else None,
                input_dir=Path(args.input_dir) if args.input_dir else None,
                pattern=args.pattern,
                recursive=not args.no_recursive,
            )
            rows = batch_run_stage01(
                inputs,
                Path(args.output_root),
                skip_existing=not args.force,
                config_path=config,
                index_path=Path(args.index),
            )
            print(
                f"batch-run completed for {len(rows)} file(s). "
                f"Index: {Path(args.index).with_suffix('.md')} "
                f"and {Path(args.index).with_suffix('.csv')}"
            )
            return 0

        if args.command == "batch-run-stage02":
            inputs = discover_csv_inputs(
                inputs=[Path(p) for p in args.inputs] if args.inputs else None,
                input_dir=Path(args.input_dir) if args.input_dir else None,
                pattern=args.pattern,
                recursive=not args.no_recursive,
            )
            rows = batch_run_stage02(
                inputs,
                Path(args.output_root),
                skip_existing=not args.force,
                index_path=Path(args.index),
            )
            print(
                f"batch-run-stage02 completed for {len(rows)} file(s). "
                f"Index: {Path(args.index).with_suffix('.md')} "
                f"and {Path(args.index).with_suffix('.csv')}"
            )
            return 0

        if args.command == "batch-run-stage03":
            inputs = discover_csv_inputs(
                inputs=[Path(p) for p in args.inputs] if args.inputs else None,
                input_dir=Path(args.input_dir) if args.input_dir else None,
                pattern=args.pattern,
                recursive=not args.no_recursive,
            )
            config = Path(args.config) if getattr(args, "config", None) else None
            rows = batch_run_stage03(
                inputs,
                Path(args.output_root),
                skip_existing=not args.force,
                index_path=Path(args.index),
                config_path=config,
            )
            print(
                f"batch-run-stage03 completed for {len(rows)} file(s). "
                f"Index: {Path(args.index).with_suffix('.md')} "
                f"and {Path(args.index).with_suffix('.csv')}"
            )
            return 0

        if args.command == "batch-run-stage04":
            inputs = discover_csv_inputs(
                inputs=[Path(p) for p in args.inputs] if args.inputs else None,
                input_dir=Path(args.input_dir) if args.input_dir else None,
                pattern=args.pattern,
                recursive=not args.no_recursive,
            )
            config = Path(args.config) if getattr(args, "config", None) else None
            rows = batch_run_stage04(
                inputs,
                Path(args.output_root),
                skip_existing=not args.force,
                index_path=Path(args.index),
                config_path=config,
            )
            print(
                f"batch-run-stage04 completed for {len(rows)} file(s). "
                f"Index: {Path(args.index).with_suffix('.md')} "
                f"and {Path(args.index).with_suffix('.csv')}"
            )
            return 0

        if args.command == "batch-run-stage05":
            inputs = discover_csv_inputs(
                inputs=[Path(p) for p in args.inputs] if args.inputs else None,
                input_dir=Path(args.input_dir) if args.input_dir else None,
                pattern=args.pattern,
                recursive=not args.no_recursive,
            )
            config = Path(args.config) if getattr(args, "config", None) else None
            rows = batch_run_stage05(
                inputs,
                Path(args.output_root),
                skip_existing=not args.force,
                index_path=Path(args.index),
                config_path=config,
            )
            print(
                f"batch-run-stage05 completed for {len(rows)} file(s). "
                f"Index: {Path(args.index).with_suffix('.md')} "
                f"and {Path(args.index).with_suffix('.csv')}"
            )
            return 0

        if args.command == "batch-run-stage06":
            inputs = discover_csv_inputs(
                inputs=[Path(p) for p in args.inputs] if args.inputs else None,
                input_dir=Path(args.input_dir) if args.input_dir else None,
                pattern=args.pattern,
                recursive=not args.no_recursive,
            )
            config = Path(args.config) if getattr(args, "config", None) else None
            rows = batch_run_stage06(
                inputs,
                Path(args.output_root),
                skip_existing=not args.force,
                index_path=Path(args.index),
                config_path=config,
            )
            print(
                f"batch-run-stage06 completed for {len(rows)} file(s). "
                f"Index: {Path(args.index).with_suffix('.md')} "
                f"and {Path(args.index).with_suffix('.csv')}"
            )
            return 0

        if args.command == "batch-run-stage07":
            inputs = discover_csv_inputs(
                inputs=[Path(p) for p in args.inputs] if args.inputs else None,
                input_dir=Path(args.input_dir) if args.input_dir else None,
                pattern=args.pattern,
                recursive=not args.no_recursive,
            )
            config = Path(args.config) if getattr(args, "config", None) else None
            rows = batch_run_stage07(
                inputs,
                Path(args.output_root),
                skip_existing=not args.force,
                index_path=Path(args.index),
                config_path=config,
            )
            print(
                f"batch-run-stage07 completed for {len(rows)} file(s). "
                f"Index: {Path(args.index).with_suffix('.md')} "
                f"and {Path(args.index).with_suffix('.csv')}"
            )
            return 0

        if args.command == "export-layer2-sessions":
            rows = export_layer2_sessions(
                Path(args.output_root),
                Path(args.export_root),
                force=args.force,
                run_pattern=args.run_pattern,
            )
            print(
                f"export-layer2-sessions completed for {len(rows)} session(s). "
                f"Index: {Path(args.export_root) / 'layer2_export_index.md'} "
                f"and {Path(args.export_root) / 'layer2_export_index.csv'}"
            )
            return 0

        if args.command == "batch-run-stage08":
            inputs = discover_csv_inputs(
                inputs=[Path(p) for p in args.inputs] if args.inputs else None,
                input_dir=Path(args.input_dir) if args.input_dir else None,
                pattern=args.pattern,
                recursive=not args.no_recursive,
            )
            config = Path(args.config) if getattr(args, "config", None) else None
            rows = batch_run_stage08(
                inputs,
                Path(args.output_root),
                skip_existing=not args.force,
                index_path=Path(args.index),
                config_path=config,
                cutoff_hz=getattr(args, "cutoff_hz", None),
                filter_order=getattr(args, "filter_order", None),
            )
            print(
                f"batch-run-stage08 completed for {len(rows)} file(s). "
                f"Index: {Path(args.index).with_suffix('.md')} "
                f"and {Path(args.index).with_suffix('.csv')}"
            )
            return 0

        input_csv = Path(args.input)
        output_dir = Path(args.output_dir)
        if not input_csv.exists():
            print(f"Input CSV not found: {input_csv}", file=sys.stderr)
            return 1

        if args.command == "run-stage":
            stage = _normalize_stage(args.stage)
            _run_until(
                stage,
                input_csv,
                output_dir,
                config,
                cutoff_hz=getattr(args, "cutoff_hz", None),
                filter_order=getattr(args, "filter_order", None),
            )
        elif args.command == "run-until":
            stage = _normalize_stage(args.stage)
            _run_until(
                stage,
                input_csv,
                output_dir,
                config,
                cutoff_hz=getattr(args, "cutoff_hz", None),
                filter_order=getattr(args, "filter_order", None),
            )
        elif args.command == "run-all":
            raise HardStopError("run-all is not implemented until Milestone 2+")
        print(f"Completed {args.command} successfully. Outputs in {output_dir}")
        return 0
    except HardStopError as exc:
        print(f"HARD STOP: {exc}", file=sys.stderr)
        return 2
    except NotImplementedError as exc:
        print(f"NOT IMPLEMENTED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
