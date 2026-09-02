"""Additive, reproducible benchmark helpers for CrackPy."""

from crackpy.benchmarking.ctd_baseline import (
    ResolutionMode,
    decode_historical_tip,
    evaluate_crackmnist,
    evaluate_repository_fixtures,
    load_repository_fixtures,
    measure_inference_contracts,
    prepare_crackmnist_inputs,
)
from crackpy.benchmarking.ctd_metrics import DistributionSummary, TipMetrics
from crackpy.benchmarking.ctd_runtime import (
    DeterministicExecution,
    PhaseStatistics,
    RunMetadata,
    RuntimeBenchmark,
    benchmark_phases,
    collect_run_metadata,
    configure_deterministic_execution,
    sha256_file,
)

__all__ = [
    "DeterministicExecution",
    "DistributionSummary",
    "PhaseStatistics",
    "ResolutionMode",
    "RunMetadata",
    "RuntimeBenchmark",
    "TipMetrics",
    "benchmark_phases",
    "collect_run_metadata",
    "configure_deterministic_execution",
    "decode_historical_tip",
    "evaluate_crackmnist",
    "evaluate_repository_fixtures",
    "load_repository_fixtures",
    "measure_inference_contracts",
    "prepare_crackmnist_inputs",
    "sha256_file",
]
