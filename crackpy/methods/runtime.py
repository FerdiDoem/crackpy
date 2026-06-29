"""Reusable method-run identity helpers.

These helpers own generic ID and imported-crack-tip projection policy. They do
not call numerical methods and do not expand method-specific quantities.
"""

from __future__ import annotations

from dataclasses import dataclass

from crackpy.results.result_data import CrackTipEstimateResult, CrackTipFrame


@dataclass(frozen=True, slots=True)
class MethodRunIdentityPolicy:
    """Deterministic ID policy for method run, result, and configuration records.

    `method_key` is the compact method-family key embedded in generated IDs,
    such as `williams_fit` or `cjp_fit`. `short_hash()` extracts the stable
    12-character hash suffix from a parameter hash. `run_id()` and
    `result_id()` support optional variants for method families such as CJP
    that emit multiple runs/results from one source.
    """

    method_key: str

    def __post_init__(self) -> None:
        self._require_non_empty("method_key", self.method_key)

    def short_hash(self, parameter_hash: str) -> str:
        """Return the first 12 hash characters after an optional `sha256:` prefix."""
        self._require_non_empty("parameter_hash", parameter_hash)
        return parameter_hash.removeprefix("sha256:")[:12]

    def configuration_id(self, parameter_hash: str) -> str:
        """Return a deterministic configuration ID from a parameter hash."""
        return f"configuration:{self.method_key}:{self.short_hash(parameter_hash)}"

    def run_id(self, *, stem: str, side: str, short_hash: str, variant: str | None = None) -> str:
        """Return a deterministic analysis-run ID for one method execution."""
        return ":".join(self._id_parts("run", stem=stem, side=side, short_hash=short_hash, variant=variant))

    def result_id(self, *, stem: str, side: str, short_hash: str, variant: str | None = None) -> str:
        """Return a deterministic result ID for one method result record."""
        return ":".join(self._id_parts("result", stem=stem, side=side, short_hash=short_hash, variant=variant))

    def _id_parts(self, prefix: str, *, stem: str, side: str, short_hash: str, variant: str | None) -> list[str]:
        self._require_non_empty("stem", stem)
        self._require_non_empty("side", side)
        self._require_non_empty("short_hash", short_hash)
        if variant is not None:
            self._require_non_empty("variant", variant)
        parts = [prefix, self.method_key]
        if variant is not None:
            parts.append(variant)
        parts.extend([stem, side, short_hash])
        return parts

    @staticmethod
    def _require_non_empty(name: str, value: str) -> None:
        if not value:
            raise ValueError(f"MethodRunIdentityPolicy requires a non-empty {name}.")


def build_manual_crack_tip_estimate(
        *,
        stem: str,
        side: str,
        input_id: str,
        method_id: str,
        configuration_id: str,
        frame: CrackTipFrame,
) -> CrackTipEstimateResult:
    """Project a legacy/manual crack-tip frame into a shared estimate record.

    The estimate represents an imported crack tip rather than a detector or
    correction output. `observed_mm` and `corrected_mm` therefore both point to
    the frame origin, while `correction_delta_mm` is an explicit zero shift.
    """
    for name, value in {
        "stem": stem,
        "side": side,
        "input_id": input_id,
        "method_id": method_id,
        "configuration_id": configuration_id,
    }.items():
        if not value:
            raise ValueError(f"build_manual_crack_tip_estimate() requires a non-empty {name}.")

    return CrackTipEstimateResult(
        estimate_id=f"crack_tip_estimate:{stem}:{side}",
        input_id=input_id,
        method_id=method_id,
        configuration_id=configuration_id,
        frame_id=frame.frame_id,
        source="manual import",
        observed_mm=frame.origin_mm,
        corrected_mm=frame.origin_mm,
        correction_delta_mm={"x": 0.0, "y": 0.0},
    )
