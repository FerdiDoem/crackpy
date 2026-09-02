"""Run the frozen P0 B0/B1 baseline and optionally the B2 Williams correction."""

from __future__ import annotations

import argparse
from importlib import resources
import json
from pathlib import Path
from typing import Any, Sequence

import torch

from crackpy.benchmarking.ctd_baseline import (
    ResolutionMode,
    evaluate_b2_example,
    evaluate_crackmnist,
    evaluate_repository_fixtures,
    load_repository_fixtures,
    measure_inference_contracts,
)
from crackpy.benchmarking.ctd_p0_runtime import (
    measure_b0_b1_fixture_phases,
    measure_first_in_process_model_loading,
)
from crackpy.benchmarking.ctd_runtime import collect_run_metadata, configure_deterministic_execution
from crackpy.crack_detection.data.preprocess import normalize
from crackpy.crack_detection.model import get_model


def build_parser() -> argparse.ArgumentParser:
    """Define a full-split default plus an explicit fixture-only smoke mode."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--device",
        default="cuda:0" if torch.cuda.is_available() else "cpu",
        help="Torch device used for frozen inference.",
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=Path.home() / ".crackmnist",
        help="Directory containing the official CrackMNIST artifacts.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/ctd-optimization/p0-b0-b1-results.json"),
        help="Strict JSON result artifact.",
    )
    parser.add_argument(
        "--limit",
        type=_positive_integer,
        default=None,
        help="Optional CrackMNIST smoke-test limit; omitted means the full test split.",
    )
    parser.add_argument("--batch-size", type=_positive_integer, default=8)
    parser.add_argument(
        "--resolution-mode",
        choices=[mode.value for mode in ResolutionMode],
        default=ResolutionMode.TRAINED_256.value,
        help="trained-256 is primary; native-128 is a sensitivity analysis.",
    )
    parser.add_argument(
        "--fixture-only",
        action="store_true",
        help="Run only the three repository fixtures as a small integration smoke test.",
    )
    parser.add_argument(
        "--include-b2",
        action="store_true",
        help="Also run the stage-52 right-side Williams-correction example; disabled by default.",
    )
    parser.add_argument(
        "--b2-warmup-iterations",
        type=_non_negative_integer,
        default=1,
        help="Warm-up iterations for the optional B2 correction timing.",
    )
    parser.add_argument(
        "--b2-measured-iterations",
        type=_positive_integer,
        default=3,
        help="Measured iterations for the optional B2 correction timing.",
    )
    return parser


def run(args: argparse.Namespace) -> dict[str, Any]:
    """Load original weights and execute the requested frozen baseline scope."""

    repository_root = Path(__file__).resolve().parents[2]
    configure_deterministic_execution(0)
    cold_start, tip_model, path_model = measure_first_in_process_model_loading(
        lambda: (
            get_model("ParallelNets", map_location=torch.device(args.device)),
            get_model("UNetPath", map_location=torch.device(args.device)),
        ),
        device=args.device,
    )
    fixture_inputs, fixture_targets = load_repository_fixtures(repository_root)
    repository_result = evaluate_repository_fixtures(
        tip_model,
        path_model,
        inputs=fixture_inputs,
        targets=fixture_targets,
        device=args.device,
        batch_size=min(args.batch_size, len(fixture_inputs)),
    )
    phase_runtime = measure_b0_b1_fixture_phases(
        tip_model,
        path_model,
        fixture_inputs=fixture_inputs,
        device=args.device,
    )
    api_runtime = measure_inference_contracts(
        tip_model,
        path_model,
        normalized_inputs=normalize(fixture_inputs).to(dtype=torch.float32),
        device=args.device,
    )

    model_folder = Path(str(resources.files("crackpy").joinpath("crack_detection/models")))
    artifact_paths = {
        "ParallelNets": model_folder / "ParallelNets.pth",
        "UNetPath": model_folder / "UNetPath.pth",
    }
    result: dict[str, Any] = {
        "schema_version": "ctd-p0-b0-b1-v1",
        "scope": {
            "fixture_only": bool(args.fixture_only),
            "crackmnist_limit": args.limit,
            "batch_size": args.batch_size,
            "resolution_mode": args.resolution_mode,
            "include_b2": bool(args.include_b2),
        },
        "metadata": collect_run_metadata(
            seed=0,
            device=args.device,
            artifact_paths=artifact_paths,
            git_root=repository_root,
        ).to_dict(),
        "repository_fixtures": repository_result,
        "runtime": {
            "cold_start": cold_start,
            "phase_resolved_b0_b1": phase_runtime,
            "api_contracts": api_runtime,
        },
        "crackmnist": None,
        "b2": None,
    }
    if not args.fixture_only:
        from crackmnist import CrackMNIST

        dataset = CrackMNIST(
            split="test",
            size="S",
            pixels=128,
            task="crack_tip_segmentation",
            download_path=str(args.dataset_root),
        )
        result["crackmnist"] = evaluate_crackmnist(
            tip_model,
            dataset,
            device=args.device,
            batch_size=args.batch_size,
            resolution_mode=args.resolution_mode,
            limit=args.limit,
        )
    if args.include_b2:
        result["b2"] = evaluate_b2_example(
            tip_model,
            path_model,
            repository_root=repository_root,
            device=args.device,
            warmup_iterations=args.b2_warmup_iterations,
            measured_iterations=args.b2_measured_iterations,
        )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    """Persist one complete, strict-JSON-compatible B0/B1 result artifact."""

    args = build_parser().parse_args(argv)
    result = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote frozen CTD P0 baseline results to {args.output}")
    return 0


def _positive_integer(value: str) -> int:
    """Parse a strictly positive CLI integer."""

    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def _non_negative_integer(value: str) -> int:
    """Parse a non-negative CLI integer for an optional warm-up count."""

    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("value must be greater than or equal to zero")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
