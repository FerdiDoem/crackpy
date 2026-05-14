# CrackPy Core Code Style

Status: observed style map and future implementation guide

Scope: `crackpy/` core package, with tests and project configuration used only as supporting evidence.

This note records the code style that is already present in the CrackPy core and turns it into guidance for later implementation work. It is not a refactor plan and does not claim that every observed pattern should be copied blindly.

## Existing Style Material

No dedicated code-style document was found under `docs/` before this note was created.

The only formal style configuration found in the repository is `.pylintrc`. It sets a Pylint threshold, disables missing docstring checks, allows long lines up to 150 characters, and encodes broad naming expectations such as `snake_case` for functions, methods, variables, and modules and `PascalCase` for classes.

`pyproject.toml` is packaging-focused. It does not define Black, Ruff, isort, pytest, or mypy settings.

Tests are written mostly as `unittest.TestCase` classes and are run through pytest in CI-style workflows. They use `setUp()` methods, `self.assert*` assertions, and direct fixture paths derived from `Path(__file__).resolve().parents[...]`.

## How This Was Mapped

The style map is based on parallel read-only scans of:

- `crackpy/input` and `crackpy/structure_elements`
- `crackpy/fracture_analysis`
- `crackpy/crack_detection`
- `crackpy/results`, package initialization, and logging
- project style configuration and tests

The repeated findings were synthesized here by separating observed reality from future consistency guidance.

## Reasoned Interpretation Of The Style

CrackPy's core style is best understood as research-pipeline pragmatism rather than generic application style.

The code is close to the scientific workflow: load nodemap data, mutate a data carrier, transform coordinates, run detection or fracture analysis, then write plots and result files. This explains why many classes are plain mutable objects, why numerical formulas are often written inline, and why domain notation such as `K_I`, `eps_vm`, `sig_xy`, `a_n`, and `b_n` is preserved instead of being normalized into generic software names.

The main peculiarity is that several things that would often be separated in a service-style codebase are intentionally or historically combined here:

- data containers also perform loading and derived-field calculation;
- pipelines combine orchestration, algorithm selection, progress reporting, plotting, and file output;
- result schemas are encoded through attribute names, text tags, JSON keys, and CSV column construction;
- units and scientific assumptions live in docstrings, variable names, comments, result labels, and output metadata rather than in a centralized unit system;
- failure handling mixes exceptions, warnings, NaN sentinels, and fallback result values.

For later implementation, consistency means fitting this style where compatibility matters while avoiding new ambiguity where the current code already shows risk. In other words: keep domain notation and direct numerical readability, but make new mutability, units, side effects, schemas, and failure modes explicit.

## Core Style Rules

### 1. Prefer Domain-Readable Names

Use names that match CrackPy's mechanics vocabulary and existing shorthand. The core uses compact scientific names heavily:

- coordinates and displacement: `coor_x`, `coor_y`, `coor_z`, `disp_x`, `disp_y`, `disp_z`
- strain and stress: `eps_x`, `eps_y`, `eps_xy`, `eps_vm`, `sig_x`, `sig_y`, `sig_xy`, `sig_vm`
- fracture results: `K_I`, `K_II`, `K_III`, `T`, `J`, `a_n`, `b_n`, `c_n`
- crack detection: `crack_tip_x`, `crack_tip_y`, `crack_tip_angle`, `crack_path`, `crack_tip_pixels`

Keep `snake_case` for Python functions, methods, variables, and modules. Keep `PascalCase` for classes. Preserve exact public result keys and serialized labels when touching output formats.

Example:

```python
crack_tip = CrackTipInfo(
    crack_tip_x=crack_tip_x,
    crack_tip_y=crack_tip_y,
    crack_tip_angle=angle,
    left_or_right=side,
)
```

Use compatibility vocabulary such as `side`, `left`, `right`, and `left_or_right` when interacting with existing APIs and file formats. In new planning docs or new internal architecture notes, link that vocabulary to the glossary so it is clear when a term is compatibility language rather than the long-term model.

### 2. Make Mutable Workflows Explicit

The core commonly uses mutable stateful objects. `InputData` reads nodemaps, stores arrays, calculates derived fields, and transforms arrays in place. `FractureAnalysis` initializes many result attributes and fills them during `run()`. `OutputWriter` reads those attributes after analysis has completed.

When adding code in this style, make mutation obvious in the method name and docstring. Use verbs such as `set_*`, `calc_*`, `transform_*`, `read_*`, `write_*`, and `run_*` consistently.

Good style for a new mutating method:

```python
def calc_example_quantity(self, material: Material) -> None:
    """Calculate and attach example_quantity in MPa."""
    self.require_fields("eps_x", "eps_y", "eps_xy")
    self.example_quantity = ...
```

Avoid a method that silently mutates state while looking like a pure helper:

```python
def example_quantity(self, material: Material):
    self.example_quantity = ...
    return self.example_quantity
```

If a method both stores and returns a value for compatibility with nearby code, document that explicitly.

### 3. Preserve Numerical Readability

Fracture-analysis code often keeps formulas close to their mathematical notation. Compact variables are acceptable inside small numerical kernels when the surrounding function name, docstring, and result names make the meaning clear.

Good style:

```python
def unit_of_williams_coefficients(n: int) -> str:
    """Return the unit label for a Williams coefficient of order n."""
    return f"MPa*mm^{1 / 2 - n / 2}"
```

For long formulas, prefer an orienting comment that states the model, units, or source assumption. Do not add comments that merely restate each assignment.

When units are involved, write them down at the boundary where the value enters or leaves the method. CrackPy currently uses mm, MPa, N, and `MPa*m^{1/2}` in result outputs, while many internal calculations use millimeter-based data.

### 4. Treat Units As Part Of The Interface

Because there is no central unit type, unit consistency depends on names, docstrings, output labels, and tests.

For new or touched public code, include units in at least one of:

- argument docstrings;
- result dictionary metadata;
- output labels;
- variable names when the unit would otherwise be ambiguous.

Example style:

```python
json_dict["experiment_data"]["crack_tip_x"] = {
    "unit": "mm",
    "value": self.analysis.crack_tip.crack_tip_x,
}
```

Avoid introducing unlabeled generic fields such as `value`, `length`, `stress`, or `position` at public boundaries unless the containing object already fixes the unit.

### 5. Keep Result Schema Names Stable

Result I/O is schema-by-convention. Text tags, JSON keys, CSV column construction, tests, and plotting depend on exact strings.

Observed public-style names include:

- `Experiment_data`
- `CJP_results`
- `Williams_fit_results`
- `SIFs_integral`
- `Bueckner_Chen_integral`
- `Path_SIFs`
- `Path_Williams_a_n`
- `Path_Williams_b_n`
- `Path_Properties`

When adding new result data, keep the existing section style close to the neighboring writer code. If a name will be serialized, document the tag/key and unit at the point of introduction.

Example:

```python
json_dict["New_Result_Section"] = {}
json_dict["New_Result_Section"]["K_example"] = {
    "unit": "MPa*m^{1/2}",
    "value": k_example,
}
```

Do not rename existing tags or keys as a style cleanup without a separate schema compatibility decision.

### 6. Separate Compatibility Names From Preferred Vocabulary

Some names are known compatibility or legacy terms, but they are still part of current code style:

- `left_or_right` is the current crack-tip side field.
- `side` accepts `left` and `right` and also controls mirroring behavior.
- `stage` is a source-specific ordering label in nodemap workflows.
- `buckner_*` appears in implementation names even though the glossary uses `Bueckner-Chen`.

When writing new code against existing modules, use the existing compatibility names at public boundaries. When writing new docs or future architecture notes, call out the preferred vocabulary from the architecture wiki.

Example:

```python
# Compatibility boundary: existing result files store Side as "left" or "right".
side = crack_tip_info.left_or_right
```

### 7. Make Side And Orientation Conventions Visible

Crack detection currently encodes left/right behavior through sign and mirroring conventions. For example, the left side can negate offsets, use a negative interpolation size, mirror x coordinates, and negate x displacement.

Any new code that depends on side or orientation should state which convention it follows. Avoid burying sign changes inside unrelated arithmetic.

Good style:

```python
interp_size = window_size if side == "right" else -window_size
```

Better when the convention affects several values:

```python
if side == "left":
    # Current detector convention mirrors left-side cracks into the right-side model frame.
    offset_x *= -1
    interp_size = -window_size
else:
    interp_size = window_size
```

### 8. Be Direct About Side Effects

Side effects are normal in the current package:

- importing `crackpy` configures logging;
- importing `crackpy.results.plot` sets the matplotlib backend to `Agg`;
- `InputData(nodemap)` can read files during construction;
- detection and fracture-analysis pipelines create folders, write result files, and save plots;
- result writers serialize directly from live analysis objects.

New functions that read files, write files, create directories, configure global state, or mutate plotting state should say so in the docstring or method name.

Good style:

```python
def write_example_results(self, output_path: str | Path) -> None:
    """Write example results to output_path and create the folder if needed."""
```

Avoid hiding file creation in helpers whose names suggest a pure calculation.

### 9. Use Logging Like The Core

Core modules commonly create a module-level logger:

```python
import logging

logger = logging.getLogger(__name__)
```

Use `logger.debug()` for detailed calculation and data-flow state, `logger.info()` for pipeline progress, `logger.warning()` for recoverable degraded behavior, and exceptions for invalid caller input or impossible required state.

Prefer parameterized logging for values that do not need f-string formatting:

```python
logger.debug("Interpolated data on grid with shape %s", self.x_grid.shape)
```

F-strings are already common in the codebase, especially for formatted scientific values. Keep them when they improve readability:

```python
logger.info(f"Stage {stage}: crack tip at {crack_tip_x:.2f} mm, {crack_tip_y:.2f} mm")
```

### 10. Prefer Explicit Validation At Workflow Boundaries

Current validation is selective. Some modules raise `ValueError`, some use assertions, and numerical code sometimes records NaN fallback values.

For new public or boundary code:

- use `ValueError` for invalid values or unsupported options;
- use `TypeError` for wrong input types where the distinction helps callers;
- use `require_fields(...)` or equivalent checks before direct `InputData` attribute use;
- reserve `assert` for internal invariants and tests;
- document NaN fallback behavior when it is an intentional numerical result.

Example:

```python
if side not in ("left", "right"):
    raise ValueError("side must be 'left' or 'right'.")
```

Example for implicit `InputData` contracts:

```python
data.require_fields("coor_x", "coor_y", "disp_x", "disp_y", "eps_vm")
```

### 11. Avoid New Mutable Default Instances

The existing code contains mutable default object instances such as `OptimizationProperties()`, `IntegralProperties()`, `Material()`, and `NodemapStructure()` in public constructors. Treat this as observed compatibility, not a pattern to extend.

For new code, prefer `None` defaults and create the object inside the function:

```python
def __init__(self, options: OptimizationProperties | None = None) -> None:
    self.options = options if options is not None else OptimizationProperties()
```

When preserving or extending an existing public signature, avoid changing behavior without a separate compatibility decision.

### 12. Keep Type Hints Practical And Local

Typing is partial and uneven in the core. New code should use Python 3.12 style where practical:

```python
def read_tag_data(self, path: str | Path, filename: str, tag: str) -> pd.DataFrame:
    ...
```

Prefer:

```python
Material | None
list[int]
dict[str, np.ndarray]
```

over legacy or misleading forms such as:

```python
Material or None
list
dict
```

Do not introduce heavy typing abstractions into numerical kernels unless they make the interface clearer. For dense NumPy code, a precise docstring about shape, units, and coordinate order is often more useful than a broad `np.ndarray` annotation alone.

### 13. Follow Existing Import Shape, But Keep Heavy Dependencies Local When Sensible

Most files use grouped imports: standard library, third-party packages, then CrackPy imports. Ordering is manual rather than enforced.

Example:

```python
from pathlib import Path

import numpy as np
import pandas as pd

from crackpy.input.input_data import InputData
```

Core modules currently import heavy optional-feeling dependencies such as plotting or VTK at module level. When adding new code, prefer local imports for dependencies that are only needed by one output or visualization method, especially if importing the module would otherwise create global side effects.

### 14. Match Test Style Unless A Test Area Already Uses Another Pattern

Tests mostly use `unittest.TestCase` and pytest as the runner. For nearby consistency, add new tests in the same style as the surrounding test file.

Example:

```python
class TestInputData(unittest.TestCase):

    def setUp(self):
        self.data = InputData()

    def test_requires_missing_field(self):
        with self.assertRaises(ValueError):
            self.data.require_fields("coor_x")
```

For numerical arrays, prefer clear tolerances. Use `numpy.testing.assert_allclose` or `np.allclose` consistently inside one test file. Avoid broad `with self.assertRaises(...)` blocks that cover several independent calls.

## Short Checklist For Future Implementation

Before adding or changing core code, check:

- Does the name match CrackPy domain vocabulary and existing shorthand?
- Is mutation visible from the method name or docstring?
- Are units documented where values cross a boundary?
- Are side, stage, and schema strings compatibility names that must remain stable?
- Does the function perform I/O, plotting, directory creation, logging setup, or global configuration?
- Are invalid inputs rejected consistently, and are numerical fallbacks documented?
- Are new defaults safe from shared mutable state?
- Does the test match the nearby `unittest` style and numeric tolerance style?

## Examples Of Current Peculiarities To Respect

### Mutable Data Carrier

`InputData` is not just a passive array bundle. It loads nodemap content, stores metadata, calculates equivalent strain and stress fields, transforms coordinates, and exports VTK data. New code that consumes `InputData` should state the required fields before using direct attributes.

### Post-Run Analysis Object

`FractureAnalysis` exposes a broad post-run interface. Writers, plotters, and tests inspect attributes such as fitting results, integral results, path sizes, and crack-tip data after `run()`. New result-producing code should define which attributes are available before and after execution.

### String-Based Output Schema

Results are public through exact text tags, JSON keys, and CSV column names. These strings are part of the observed interface even when they look like implementation details.

### Distributed Orientation Logic

Left/right crack behavior is spread across detection setup, interpolation, pixel-to-mm conversion, plotting, and result writing. New code should not assume that `side` is just a label.

### Scientific Failure Values

Some numerical failures are represented as NaN results or zero correction shifts rather than exceptions. If new numerical code follows that pattern, document the fallback and log the reason.
