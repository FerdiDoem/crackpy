# Scientific And Methodological Context

Status: observed scientific context
Role: Preserve scientific assumptions, literature references, numerical methods, validation strategies, and domain scope separately from implementation inventory and architecture planning.

## Package Scope

CrackPy targets automatic detection and fracture-mechanical analysis of fatigue cracks using DIC or simulation nodemap data.

README-level scope statements:

- methods are intended for research, not production/specification use;
- package functionality is prototype-level;
- input methods are intended to be source-independent if displacement/strain format matches and plane-stress assumptions hold;
- tested material scope is mainly aluminium alloys and ductile fatigue cracks.

## Bibliography Signals

The README is the main bibliography. It references:

- ASTM E-647 fatigue crack growth measurement;
- Roux et al. 2006 on DIC SIF measurement;
- Rethore et al. 2005 on mixed-mode SIF estimation by DIC and interaction integral;
- Melching et al. 2022 on explainable ML for crack-tip detection;
- Becker et al. 2012 on J-integral calculation from DIC;
- Chen 1985 on path-independent integrals in LEFM;
- Williams 1961 on crack-tip stress distributions;
- Yang et al. 2021 on optimized CJP fitting;
- Strohmann et al. 2021 on CNN crack-path detection;
- Rice 1968 on the J-integral;
- Stern et al. 1976 on contour-integral mixed-mode SIFs;
- Breitbarth et al. 2019 on SIF and J-integral from DIC;
- Christopher et al. 2007 and 2013 on CJP crack-tip fields;
- Melching et al. 2023 on conjugate work integrals;
- Melching et al. 2024 on symbolic-regression crack-tip correction;
- Molteno and Becker 2015 on mode I-III J-integral decomposition.

Additional code-level references:

- Meinhard Kuna formulas for Williams fields and Bueckner-Chen coefficient recovery;
- Sladek et al. 1997 for crack near-field auxiliary formulas;
- Zhao et al. 2001 for T-stress auxiliary fields;
- Cardew 1985 and Kfouri 1986 for T-stress references in line integration;
- Camacho-Reyes et al. 2023 for CJP Mode-I formulas;
- Natekar et al. 2020 and Vinogradova et al. for Seg-Grad-CAM.

## Numerical Methods

### Williams Expansion

CrackPy implements analytical Williams stress and displacement fields in 2D and 3D, fits Williams coefficients by least-squares displacement matching, and derives SIF/T-stress values from selected coefficients.

Scientific assumptions:

- crack-tip local polar coordinates;
- linear elastic material law;
- angular crack-path exclusion through `angle_gap`;
- selected terms drive interpretability and derived values.

### CJP Model

CrackPy implements CJP mixed-mode and mode-I stress/displacement fields. Fitting uses nonlinear least squares over displacement fields.

Code-level warning: CJP fitting is explicitly marked experimental and most reliable for Mode-I-dominated load cases.

### Line Integrals

CrackPy implements:

- J-integral;
- J-integral mode decomposition;
- interaction integrals for SIFs;
- interaction integral and stress-difference method for T-stress;
- Bueckner-Chen integral for Williams coefficients.

Integration paths are rectangular/open contours around a transformed crack tip. Automatic path selection uses a Von Mises stress threshold near the crack tip, typically material yield stress.

### Crack Detection

Two detection methodologies coexist:

- neural-network detection using DIC displacement fields and trained U-Net-style models;
- line-intercept detection using fitted displacement discontinuity profiles and equivalent-strain thresholding.

Optional correction methods use Williams coefficients and include Rethore-style iterative correction, symbolic-regression formulas, direct optimization, differential evolution, and grid search.

## Validation Strategy

Observed validation is regression-oriented:

- fixed expected numerical values for integrals, SIFs, T-stress, CJP outputs, and Williams fits;
- synthetic Williams fields used to verify coefficient recovery;
- reusable interpolation checked against SciPy `griddata`;
- crack-detection pipeline output checked against fixture crack-info files;
- package tests and integration-like `test_scripts` both present.

## Domain Assumptions

- Main coordinate and geometry unit is millimeter.
- Stress is generally MPa.
- SIF output is reported in `MPa*sqrt(m)`.
- DIC input is assumed compatible with CrackPy's nodemap schema.
- Header metadata supplies optional force/cycle information for stage filtering.
- Crack side is represented by strings and has repeated orientation logic.
- Plane stress is the documented operating assumption, even though plane strain support exists in `Material`.
