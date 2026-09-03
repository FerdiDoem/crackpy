"""Run the canonical frozen-model CTD P2 adaptive-ROI benchmark."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Sequence

import torch

from crackpy.benchmarking.ctd_p2_runner import (
    P2FullRunConfig,
    run_p2_full_benchmark,
)


def build_parser() -> argparse.ArgumentParser:
    """Define reproducible P2 inputs with the verified local cache as default."""

    repository_root = Path(__file__).resolve().parents[2]
    optimization_root = repository_root / "docs" / "ctd-optimization"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--device",
        default="cuda:0" if torch.cuda.is_available() else "cpu",
        help="Torch device for the persistent frozen P1 tip model.",
    )
    parser.add_argument(
        "--p0-results",
        type=Path,
        default=optimization_root / "p0-results.json",
        help="Frozen P0 evidence artifact used by the P2 report.",
    )
    parser.add_argument(
        "--p1-results",
        type=Path,
        default=optimization_root / "p1-results.json",
        help="Verified full-split P1 artifact supplying the frozen decoder policy.",
    )
    parser.add_argument(
        "--mendeley-cache-root",
        type=Path,
        default=repository_root / ".downloads" / "mendeley-dywwnjv22h-v1",
        help="Local cache for the Mendeley dywwnjv22h/1 evidence files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=optimization_root / "p2-results.json",
        help="Strict JSON P2 result artifact.",
    )
    parser.add_argument(
        "--expanded-scale",
        type=_expanded_scale,
        default=55.0 / 40.0,
        help="P2.2 expanded-ROI factor; must stay strictly between 1 and 1.75.",
    )
    parser.add_argument(
        "--skip-mendeley-hash-verification",
        action="store_true",
        help="Explicitly bypass the normally mandatory Mendeley cache hash checks.",
    )
    return parser


def run(args: argparse.Namespace) -> dict[str, object]:
    """Translate CLI arguments into one immutable canonical P2 run."""

    repository_root = Path(__file__).resolve().parents[2]
    return run_p2_full_benchmark(
        P2FullRunConfig(
            repository_root=repository_root,
            p1_results_path=args.p1_results,
            p0_results_path=args.p0_results,
            mendeley_cache_root=args.mendeley_cache_root,
            device=args.device,
            expanded_scale=args.expanded_scale,
            verify_mendeley_hashes=(
                not args.skip_mendeley_hash_verification
            ),
        )
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Execute P2 and persist only finite, standards-compliant JSON."""

    args = build_parser().parse_args(argv)
    result = run(args)
    serialized = json.dumps(
        result,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialized, encoding="utf-8")
    print(f"Wrote canonical CTD P2 results to {args.output}")
    return 0


def _expanded_scale(value: str) -> float:
    """Parse a finite expanded ROI that remains distinct from full search."""

    parsed = float(value)
    if not math.isfinite(parsed) or not 1.0 < parsed < 70.0 / 40.0:
        raise argparse.ArgumentTypeError(
            "value must be finite and strictly between 1 and 1.75"
        )
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
