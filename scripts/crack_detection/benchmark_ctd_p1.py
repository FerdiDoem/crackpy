"""Run frozen-model CTD P1 calibration, test, runtime, and interpolation sweeps."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

import torch

from crackpy.benchmarking.ctd_p1 import P1RunConfig, run_p1_benchmark


def build_parser() -> argparse.ArgumentParser:
    """Define a full-split default and an explicit ``--limit`` smoke control."""

    repository_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--device",
        default="cuda:0" if torch.cuda.is_available() else "cpu",
        help="Torch device shared by the persistent frozen model pair.",
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=Path.home() / ".crackmnist",
        help="Directory containing the official CrackMNIST artifacts.",
    )
    parser.add_argument(
        "--p0-results",
        type=Path,
        default=repository_root / "docs" / "ctd-optimization" / "p0-results.json",
        help="Frozen P0 result used to derive the P1 accuracy gates.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repository_root / "docs" / "ctd-optimization" / "p1-results.json",
        help="Strict JSON P1 result artifact.",
    )
    parser.add_argument(
        "--limit",
        type=_positive_integer,
        default=None,
        help="Optional per-split smoke limit; omitted means full validation and test.",
    )
    parser.add_argument("--calibration-batch-size", type=_positive_integer, default=8)
    parser.add_argument("--runtime-warmup-iterations", type=_non_negative_integer, default=1)
    parser.add_argument("--runtime-measured-iterations", type=_positive_integer, default=3)
    parser.add_argument(
        "--interpolation-warmup-iterations",
        type=_non_negative_integer,
        default=1,
    )
    parser.add_argument(
        "--interpolation-measured-iterations",
        type=_positive_integer,
        default=3,
    )
    return parser


def run(args: argparse.Namespace) -> dict[str, object]:
    """Translate CLI arguments into one immutable P1 run configuration."""

    repository_root = Path(__file__).resolve().parents[2]
    return run_p1_benchmark(
        P1RunConfig(
            repository_root=repository_root,
            dataset_root=args.dataset_root,
            p0_results_path=args.p0_results,
            device=args.device,
            limit=args.limit,
            calibration_batch_size=args.calibration_batch_size,
            runtime_warmup_iterations=args.runtime_warmup_iterations,
            runtime_measured_iterations=args.runtime_measured_iterations,
            interpolation_warmup_iterations=args.interpolation_warmup_iterations,
            interpolation_measured_iterations=args.interpolation_measured_iterations,
        )
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Execute P1 and persist only finite, standards-compliant JSON."""

    args = build_parser().parse_args(argv)
    result = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote frozen CTD P1 results to {args.output}")
    return 0


def _positive_integer(value: str) -> int:
    """Parse a strictly positive CLI integer."""

    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def _non_negative_integer(value: str) -> int:
    """Parse a non-negative CLI integer."""

    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be greater than or equal to zero")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
