"""Reproducibility and phase-level runtime measurements for CTD P0.

This module is deliberately independent from CrackPy's detector classes.
It measures the unmodified inference functions supplied by a benchmark runner,
and represents all persisted values with JSON-native finite values.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version as package_version
import math
from pathlib import Path
import platform
import random
import subprocess
import sys
import time
from typing import Any, TypeVar

import numpy as np

T = TypeVar("T")


@dataclass(frozen=True)
class PhaseStatistics:
    """Measured duration samples and their finite descriptive statistics."""

    samples_ms: tuple[float, ...]
    mean_ms: float
    median_ms: float
    p95_ms: float
    minimum_ms: float
    maximum_ms: float

    def to_dict(self) -> dict[str, object]:
        """Return only JSON-native numeric values."""

        return asdict(self)


@dataclass(frozen=True)
class RuntimeBenchmark:
    """Phase timings, throughput, and memory captured after warm-up.

    ``total_measured_ms`` is the sum of all phase timings, and throughput is
    therefore end-to-end iterations per second for the supplied phase set.
    """

    warmup_iterations: int
    measured_iterations: int
    phases: dict[str, PhaseStatistics]
    total_measured_ms: float
    throughput_per_second: float
    process_rss_after_bytes: int | None
    process_peak_rss_bytes: int | None
    gpu_peak_memory_bytes: int | None

    def to_dict(self) -> dict[str, object]:
        """Return a strict-JSON-compatible representation."""

        return {
            "warmup_iterations": self.warmup_iterations,
            "measured_iterations": self.measured_iterations,
            "phases": {name: summary.to_dict() for name, summary in self.phases.items()},
            "total_measured_ms": self.total_measured_ms,
            "throughput_per_second": self.throughput_per_second,
            "process_rss_after_bytes": self.process_rss_after_bytes,
            "process_peak_rss_bytes": self.process_peak_rss_bytes,
            "gpu_peak_memory_bytes": self.gpu_peak_memory_bytes,
        }


@dataclass(frozen=True)
class DeterministicExecution:
    """The seed and deterministic execution choices used for a benchmark."""

    seed: int
    torch_deterministic_algorithms: bool
    cudnn_benchmark: bool | None
    cudnn_deterministic: bool | None

    def to_dict(self) -> dict[str, int | bool | None]:
        """Return a JSON-compatible representation."""

        return asdict(self)


@dataclass(frozen=True)
class RunMetadata:
    """Immutable provenance needed to reproduce a CTD P0 result artifact."""

    seed: int
    git_commit: str | None
    device: str
    device_name: str | None
    cuda_available: bool
    cuda_version: str | None
    python_version: str
    platform: str
    crackpy_version: str | None
    numpy_version: str
    torch_version: str | None
    artifact_sha256: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        """Return a strict-JSON-compatible representation."""

        return asdict(self)


def configure_deterministic_execution(seed: int, *, torch_module: Any | None = None) -> DeterministicExecution:
    """Seed Python, NumPy, and Torch while preferring deterministic kernels.

    Torch is injected for lightweight tests and imported only when the caller
    does not supply it. Unsupported nondeterministic operations fail loudly so
    a reference run cannot silently weaken its reproducibility contract.
    """

    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ValueError("seed must be a non-negative integer")

    random.seed(seed)
    np.random.seed(seed)
    torch_module = _resolve_torch(torch_module)
    if torch_module is None:
        return DeterministicExecution(seed, False, None, None)

    torch_module.manual_seed(seed)
    cuda_available = _cuda_available(torch_module)
    if cuda_available:
        torch_module.cuda.manual_seed_all(seed)
    torch_module.use_deterministic_algorithms(True, warn_only=False)

    cudnn = getattr(getattr(torch_module, "backends", None), "cudnn", None)
    if cudnn is None:
        return DeterministicExecution(seed, True, None, None)
    cudnn.benchmark = False
    cudnn.deterministic = True
    return DeterministicExecution(seed, True, False, True)


def sha256_file(path: str | Path) -> str:
    """Return a content SHA-256 digest without loading a model artifact at once."""

    digest = sha256()
    with Path(path).open("rb") as artifact:
        for block in iter(lambda: artifact.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def collect_run_metadata(
    *,
    seed: int,
    device: str,
    artifact_paths: Mapping[str, str | Path],
    git_root: str | Path | None = None,
    torch_module: Any | None = None,
) -> RunMetadata:
    """Capture software, Git, device, and artifact provenance for one run."""

    torch_module = _resolve_torch(torch_module)
    cuda_available = _cuda_available(torch_module)
    is_cuda = _is_cuda_device(device)
    device_name = None
    cuda_version = None
    torch_version = None
    if torch_module is not None:
        torch_version = _optional_text(getattr(torch_module, "__version__", None))
        cuda_version = _optional_text(getattr(getattr(torch_module, "version", None), "cuda", None))
        if is_cuda and cuda_available:
            device_name = _optional_text(torch_module.cuda.get_device_name(device))

    return RunMetadata(
        seed=seed,
        git_commit=_git_commit(git_root),
        device=str(device),
        device_name=device_name,
        cuda_available=cuda_available,
        cuda_version=cuda_version,
        python_version=platform.python_version(),
        platform=platform.platform(),
        crackpy_version=_installed_version("crackpy"),
        numpy_version=np.__version__,
        torch_version=torch_version,
        artifact_sha256={name: sha256_file(path) for name, path in artifact_paths.items()},
    )


def benchmark_phases(
    phases: Mapping[str, Callable[[], T]],
    *,
    warmup_iterations: int = 0,
    measured_iterations: int = 1,
    device: str = "cpu",
    torch_module: Any | None = None,
    clock_ns: Callable[[], int] = time.perf_counter_ns,
    process: Any | None = None,
) -> RuntimeBenchmark:
    """Measure ordered phases with warm-up excluded from time and memory.

    CUDA is synchronized after warm-up, before and after each measured phase.
    This makes host wall-clock samples represent completed GPU work, while
    allowing the CUDA implementation to be injected and mocked in unit tests.
    """

    _validate_phases(phases)
    _validate_iteration_count("warmup_iterations", warmup_iterations, minimum=0)
    _validate_iteration_count("measured_iterations", measured_iterations, minimum=1)
    torch_module = _resolve_torch(torch_module)
    synchronize = _cuda_synchronizer(device, torch_module)

    for _ in range(warmup_iterations):
        for phase in phases.values():
            phase()
    synchronize()
    gpu_peak_memory_bytes = _reset_gpu_peak_memory(device, torch_module)

    samples_by_phase: dict[str, list[float]] = {name: [] for name in phases}
    for _ in range(measured_iterations):
        for name, phase in phases.items():
            synchronize()
            started_ns = clock_ns()
            phase()
            synchronize()
            elapsed_ns = clock_ns() - started_ns
            if elapsed_ns < 0:
                raise RuntimeError("clock_ns must be monotonic")
            samples_by_phase[name].append(elapsed_ns / 1_000_000.0)

    if _is_cuda_device(device) and _cuda_available(torch_module):
        gpu_peak_memory_bytes = int(torch_module.cuda.max_memory_allocated(device))
    process_rss_after_bytes, process_peak_rss_bytes = _process_memory_bytes(process)
    phase_statistics = {name: _phase_statistics(samples) for name, samples in samples_by_phase.items()}
    total_measured_ms = float(sum(sum(samples) for samples in samples_by_phase.values()))
    if total_measured_ms <= 0:
        raise RuntimeError("total measured duration must be greater than zero")
    throughput_per_second = measured_iterations / (total_measured_ms / 1000.0)

    return RuntimeBenchmark(
        warmup_iterations=warmup_iterations,
        measured_iterations=measured_iterations,
        phases=phase_statistics,
        total_measured_ms=total_measured_ms,
        throughput_per_second=float(throughput_per_second),
        process_rss_after_bytes=process_rss_after_bytes,
        process_peak_rss_bytes=process_peak_rss_bytes,
        gpu_peak_memory_bytes=gpu_peak_memory_bytes,
    )


def _phase_statistics(samples_ms: list[float]) -> PhaseStatistics:
    """Create finite descriptive statistics for at least one duration sample."""

    values = np.asarray(samples_ms, dtype=float)
    if values.size == 0 or not np.all(np.isfinite(values)):
        raise ValueError("phase duration samples must be finite and non-empty")
    return PhaseStatistics(
        samples_ms=tuple(float(value) for value in values),
        mean_ms=float(np.mean(values)),
        median_ms=float(np.median(values)),
        p95_ms=float(np.percentile(values, 95)),
        minimum_ms=float(np.min(values)),
        maximum_ms=float(np.max(values)),
    )


def _resolve_torch(torch_module: Any | None) -> Any | None:
    """Import Torch only when it is available and has not been injected."""

    if torch_module is not None:
        return torch_module
    try:
        import torch
    except ImportError:
        return None
    return torch


def _is_cuda_device(device: str) -> bool:
    """Treat standard CUDA device strings case-insensitively."""

    return str(device).lower().startswith("cuda")


def _cuda_available(torch_module: Any | None) -> bool:
    """Return CUDA availability without requiring Torch in CPU-only tests."""

    return bool(torch_module is not None and getattr(torch_module, "cuda", None) is not None and torch_module.cuda.is_available())


def _cuda_synchronizer(device: str, torch_module: Any | None) -> Callable[[], None]:
    """Return a no-op or a device-specific CUDA synchronization callable."""

    if not _is_cuda_device(device) or not _cuda_available(torch_module):
        return lambda: None
    return lambda: torch_module.cuda.synchronize(device)


def _reset_gpu_peak_memory(device: str, torch_module: Any | None) -> int | None:
    """Reset GPU peak accounting only for a usable CUDA device."""

    if not _is_cuda_device(device) or not _cuda_available(torch_module):
        return None
    torch_module.cuda.reset_peak_memory_stats(device)
    return 0


def _process_memory_bytes(process: Any | None) -> tuple[int | None, int | None]:
    """Read current and peak resident memory when the platform exposes them."""

    if process is None:
        try:
            import psutil
        except ImportError:
            return None, _resource_peak_rss_bytes()
        process = psutil.Process()
    memory_info = process.memory_info()
    rss = int(memory_info.rss)
    peak = getattr(memory_info, "peak_wset", None)
    peak_bytes = int(peak) if peak is not None else _resource_peak_rss_bytes()
    return rss if rss >= 0 else None, peak_bytes if peak_bytes is None or peak_bytes >= 0 else None


def _resource_peak_rss_bytes() -> int | None:
    """Return the Unix process peak RSS with its platform-specific unit."""

    try:
        import resource
    except ImportError:
        return None
    peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return peak if sys.platform == "darwin" else peak * 1024


def _git_commit(git_root: str | Path | None) -> str | None:
    """Return HEAD when available, without making Git a runtime dependency."""

    if git_root is None:
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(git_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    commit = result.stdout.strip()
    return commit or None


def _optional_text(value: object) -> str | None:
    """Normalize optional metadata to a non-empty string."""

    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _installed_version(distribution: str) -> str | None:
    """Return an installed distribution version without requiring packaging."""

    try:
        return package_version(distribution)
    except PackageNotFoundError:
        return None


def _validate_phases(phases: Mapping[str, Callable[[], T]]) -> None:
    """Reject empty, ambiguous, or invalid phase contracts before timing."""

    if not phases:
        raise ValueError("at least one phase is required")
    for name, phase in phases.items():
        if not isinstance(name, str) or not name:
            raise ValueError("phase names must be non-empty strings")
        if not callable(phase):
            raise TypeError("each phase must be callable")


def _validate_iteration_count(name: str, value: int, *, minimum: int) -> None:
    """Validate an explicit, integer iteration count."""

    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ValueError(f"{name} must be an integer greater than or equal to {minimum}")
