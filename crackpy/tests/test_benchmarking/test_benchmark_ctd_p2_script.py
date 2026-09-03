"""CLI contract tests for the canonical CTD P2 benchmark entry point."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from crackpy.benchmarking.ctd_p2_runner import P2FullRunConfig
from scripts.crack_detection import benchmark_ctd_p2


def test_parser_defaults_to_canonical_inputs_cache_output_and_available_device(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_root = Path(benchmark_ctd_p2.__file__).resolve().parents[2]
    monkeypatch.setattr(benchmark_ctd_p2.torch.cuda, "is_available", lambda: True)

    cuda = benchmark_ctd_p2.build_parser().parse_args([])

    assert cuda.device == "cuda:0"
    assert cuda.p0_results == repository_root / "docs/ctd-optimization/p0-results.json"
    assert cuda.p1_results == repository_root / "docs/ctd-optimization/p1-results.json"
    assert cuda.mendeley_cache_root == (
        repository_root / ".downloads/mendeley-dywwnjv22h-v1"
    )
    assert cuda.output == repository_root / "docs/ctd-optimization/p2-results.json"
    assert cuda.expanded_scale == pytest.approx(55.0 / 40.0)
    assert cuda.skip_mendeley_hash_verification is False

    monkeypatch.setattr(benchmark_ctd_p2.torch.cuda, "is_available", lambda: False)
    cpu = benchmark_ctd_p2.build_parser().parse_args([])
    assert cpu.device == "cpu"


def test_parser_exposes_only_valid_expansion_and_explicit_hash_bypass() -> None:
    parser = benchmark_ctd_p2.build_parser()

    arguments = parser.parse_args(
        [
            "--expanded-scale",
            "1.5",
            "--skip-mendeley-hash-verification",
        ]
    )

    assert arguments.expanded_scale == pytest.approx(1.5)
    assert arguments.skip_mendeley_hash_verification is True
    with pytest.raises(SystemExit):
        parser.parse_args(["--expanded-scale", "1"])
    with pytest.raises(SystemExit):
        parser.parse_args(["--expanded-scale", "1.75"])


def test_run_builds_one_full_config_and_delegates_to_the_orchestrator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[P2FullRunConfig] = []
    expected = {"schema_version": "ctd-p2-v1", "finite": 1.0}
    monkeypatch.setattr(
        benchmark_ctd_p2,
        "run_p2_full_benchmark",
        lambda config: captured.append(config) or expected,
    )
    arguments = benchmark_ctd_p2.build_parser().parse_args(
        [
            "--device",
            "cpu",
            "--p0-results",
            str(tmp_path / "p0.json"),
            "--p1-results",
            str(tmp_path / "p1.json"),
            "--mendeley-cache-root",
            str(tmp_path / "mendeley"),
            "--expanded-scale",
            "1.5",
            "--skip-mendeley-hash-verification",
        ]
    )

    result = benchmark_ctd_p2.run(arguments)

    assert result is expected
    assert len(captured) == 1
    config = captured[0]
    assert isinstance(config, P2FullRunConfig)
    assert config.repository_root == Path(benchmark_ctd_p2.__file__).resolve().parents[2]
    assert config.p0_results_path == tmp_path / "p0.json"
    assert config.p1_results_path == tmp_path / "p1.json"
    assert config.mendeley_cache_root == tmp_path / "mendeley"
    assert config.device == "cpu"
    assert config.pixels == 256
    assert config.expanded_scale == pytest.approx(1.5)
    assert config.verify_mendeley_hashes is False


def test_main_writes_strict_sorted_json_and_creates_the_output_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "nested" / "p2.json"
    monkeypatch.setattr(
        benchmark_ctd_p2,
        "run_p2_full_benchmark",
        lambda config: {
            "schema_version": "ctd-p2-v1",
            "device": config.device,
            "finite": 1.0,
        },
    )

    exit_code = benchmark_ctd_p2.main(
        ["--device", "cpu", "--output", str(output)]
    )

    assert exit_code == 0
    text = output.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert json.loads(text) == {
        "device": "cpu",
        "finite": 1.0,
        "schema_version": "ctd-p2-v1",
    }
    assert text.index('"device"') < text.index('"schema_version"')


def test_main_refuses_nonfinite_results_before_creating_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "p2.json"
    monkeypatch.setattr(
        benchmark_ctd_p2,
        "run_p2_full_benchmark",
        lambda config: {"invalid": float("nan")},
    )

    with pytest.raises(ValueError, match="Out of range float values"):
        benchmark_ctd_p2.main(["--output", str(output)])

    assert not output.exists()
