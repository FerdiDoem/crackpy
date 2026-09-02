"""Contract tests for reproducible CTD P0 runtime measurements."""

from __future__ import annotations

import json
import random

import numpy as np
import pytest

from crackpy.benchmarking.ctd_runtime import (
    benchmark_phases,
    collect_run_metadata,
    configure_deterministic_execution,
    sha256_file,
)


class _FakeCuda:
    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self.synchronizations: list[str | None] = []
        self.reset_devices: list[str | None] = []
        self.manual_seeds: list[int] = []

    def is_available(self) -> bool:
        return self.available

    def synchronize(self, device=None) -> None:
        self.synchronizations.append(device)

    def reset_peak_memory_stats(self, device=None) -> None:
        self.reset_devices.append(device)

    def max_memory_allocated(self, device=None) -> int:
        return 4096

    def get_device_name(self, device=None) -> str:
        return "mock-gpu"

    def manual_seed_all(self, seed: int) -> None:
        self.manual_seeds.append(seed)


class _FakeCudnn:
    benchmark = True
    deterministic = False


class _FakeBackends:
    cudnn = _FakeCudnn()


class _FakeTorch:
    def __init__(self, *, cuda_available: bool = True) -> None:
        self.cuda = _FakeCuda(available=cuda_available)
        self.backends = _FakeBackends()
        self.manual_seeds: list[int] = []
        self.deterministic_calls: list[tuple[bool, bool]] = []
        self.version = type("Version", (), {"cuda": "13.0"})()
        self.__version__ = "fake-torch"

    def manual_seed(self, seed: int) -> None:
        self.manual_seeds.append(seed)

    def use_deterministic_algorithms(self, enabled: bool, *, warn_only: bool) -> None:
        self.deterministic_calls.append((enabled, warn_only))

class _FakeProcess:
    class _MemoryInfo:
        rss = 8192

    def memory_info(self):
        return self._MemoryInfo()


def _clock_from_nanoseconds(values: list[int]):
    iterator = iter(values)
    return lambda: next(iterator)


def test_benchmark_phases_excludes_warmups_and_retains_separate_phase_statistics():
    calls: list[str] = []

    def prepare():
        calls.append("prepare")

    def inference():
        calls.append("inference")

    result = benchmark_phases(
        {"prepare": prepare, "inference": inference},
        warmup_iterations=1,
        measured_iterations=2,
        clock_ns=_clock_from_nanoseconds(
            [
                0,
                1_000_000,
                2_000_000,
                5_000_000,
                6_000_000,
                8_000_000,
                10_000_000,
                14_000_000,
            ]
        ),
        process=_FakeProcess(),
    )

    assert calls == ["prepare", "inference"] * 3
    assert result.warmup_iterations == 1
    assert result.measured_iterations == 2
    assert result.phases["prepare"].samples_ms == (1.0, 2.0)
    assert result.phases["inference"].samples_ms == (3.0, 4.0)
    assert result.phases["inference"].p95_ms == pytest.approx(3.95)
    assert result.process_rss_bytes == 8192


def test_benchmark_phases_reports_throughput_and_mockable_cuda_synchronization():
    torch_module = _FakeTorch()

    result = benchmark_phases(
        {"inference": lambda: None},
        warmup_iterations=1,
        measured_iterations=2,
        device="cuda:0",
        torch_module=torch_module,
        clock_ns=_clock_from_nanoseconds([0, 10_000_000, 10_000_000, 20_000_000]),
        process=_FakeProcess(),
    )

    assert result.total_measured_ms == 20.0
    assert result.throughput_per_second == 100.0
    assert result.gpu_peak_memory_bytes == 4096
    assert torch_module.cuda.reset_devices == ["cuda:0"]
    assert torch_module.cuda.synchronizations == ["cuda:0"] * 5


def test_deterministic_execution_controls_all_random_sources_and_cuda_settings():
    torch_module = _FakeTorch()

    configuration = configure_deterministic_execution(1234, torch_module=torch_module)
    first_python = random.random()
    first_numpy = float(np.random.random())
    configure_deterministic_execution(1234, torch_module=torch_module)

    assert configuration.seed == 1234
    assert random.random() == first_python
    assert float(np.random.random()) == first_numpy
    assert torch_module.manual_seeds == [1234, 1234]
    assert torch_module.cuda.manual_seeds == [1234, 1234]
    assert torch_module.deterministic_calls == [(True, True), (True, True)]
    assert torch_module.backends.cudnn.benchmark is False
    assert torch_module.backends.cudnn.deterministic is True


def test_hash_and_metadata_are_strict_json_compatible_and_capture_device(tmp_path):
    artifact = tmp_path / "weights.pt"
    artifact.write_bytes(b"original-weights")
    torch_module = _FakeTorch()

    metadata = collect_run_metadata(
        seed=17,
        device="cuda:0",
        artifact_paths={"tip_model": artifact},
        torch_module=torch_module,
        git_root=tmp_path,
    )

    assert sha256_file(artifact) == metadata.artifact_sha256["tip_model"]
    assert metadata.device == "cuda:0"
    assert metadata.device_name == "mock-gpu"
    assert metadata.git_commit is None
    encoded = json.dumps(metadata.to_dict(), allow_nan=False)
    assert json.loads(encoded)["seed"] == 17


def test_benchmark_result_is_strict_json_compatible():
    result = benchmark_phases(
        {"inference": lambda: None},
        measured_iterations=1,
        clock_ns=_clock_from_nanoseconds([0, 1_000_000]),
        process=_FakeProcess(),
    )

    assert json.loads(json.dumps(result.to_dict(), allow_nan=False))["phases"]["inference"]["mean_ms"] == 1.0
