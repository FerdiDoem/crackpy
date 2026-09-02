"""Additive, reproducible benchmark helpers for CrackPy."""

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
    "RunMetadata",
    "RuntimeBenchmark",
    "TipMetrics",
    "benchmark_phases",
    "collect_run_metadata",
    "configure_deterministic_execution",
    "sha256_file",
]
