"""Additive, reproducible benchmark helpers for CrackPy."""

from crackpy.benchmarking.ctd_baseline import (
    ResolutionMode,
    build_b2_result,
    classify_b2_correction_status,
    decode_historical_tip,
    evaluate_b2_example,
    evaluate_crackmnist,
    evaluate_repository_fixtures,
    load_repository_fixtures,
    map_legacy_decoder_point_to_original,
    map_model_index_point_to_original,
    measure_inference_contracts,
    prepare_crackmnist_inputs,
)
from crackpy.benchmarking.ctd_metrics import DistributionSummary, TipMetrics
from crackpy.benchmarking.ctd_p0_runtime import (
    measure_b0_b1_fixture_phases,
    measure_first_in_process_model_loading,
)
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
    "build_b2_result",
    "classify_b2_correction_status",
    "collect_run_metadata",
    "configure_deterministic_execution",
    "decode_historical_tip",
    "evaluate_b2_example",
    "evaluate_crackmnist",
    "evaluate_repository_fixtures",
    "load_repository_fixtures",
    "map_legacy_decoder_point_to_original",
    "map_model_index_point_to_original",
    "measure_b0_b1_fixture_phases",
    "measure_first_in_process_model_loading",
    "measure_inference_contracts",
    "prepare_crackmnist_inputs",
    "sha256_file",
]
