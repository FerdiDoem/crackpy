# Glossary

Status: living glossary
Role: Canonical vocabulary layer for current CrackPy architecture wiki notes. Naming debates and unresolved alternatives live in [[terminology-report]] and [[open-questions]].

## Fracture Mechanics Terms

These terms describe the scientific and methodological language of fracture mechanics. They should stay separate from CrackPy implementation containers and file-format terms.

### Crack Tip And Crack Tip Detection

#### Crack tip
Physical crack-front endpoint in the analyzed 2D field. CrackPy often transforms data so the crack tip lies at `(0, 0)` before fracture-mechanics evaluation.

#### Crack-tip-centered coordinates
Fracture-analysis coordinate frame where the crack tip is shifted to `(0, 0)` and the local crack direction is aligned by the crack angle. In the current implementation this frame is produced by `InputData.transform_data(x_shift, y_shift, angle)`.

#### Crack-tip coordinate system
Proposed internal coordinate-system concept for future architecture planning. Local x is the crack-extension direction, local y is the crack-opening direction for mode I, and local z is aligned with the crack front or, for the current straight-surface approximation, the surface normal. This is broader than the current `side` convention and should support arbitrary 2D crack orientation, multiple crack tips, and later 3D crack-front or 3D-surface descriptions.

#### Crack-tip correction
Post-detection refinement of the crack-tip position. In CrackPy, correction methods generally re-evaluate Williams fitting after shifting the candidate crack tip.

#### Rethore correction
Iterative crack-tip correction method based on Williams coefficients, using `dx = -2*a_-1/a_1` and keeping `dy = 0`.

#### Symbolic-regression correction
Crack-tip correction method using learned formulas based on Williams coefficients. The current implementation uses `dx = -a_-1/a_1` and `dy = -b_-1/a_1`.

#### Custom-function correction
Crack-tip correction path where caller-provided formulas define the x/y correction. The implementation supports string-based custom formulas and lambdified symbolic functions.

#### Williams-fit-error optimization correction
Crack-tip correction method that treats the tip shift as an optimization variable and minimizes the Williams fitting error, or the squared `a_-1`/`b_-1` terms.

#### Differential-evolution correction
Global optimization variant of Williams-fit-error correction using SciPy differential evolution over a bounded x/y shift domain.

#### Grid-search correction
Brute-force crack-tip correction method that evaluates Williams fitting error over an x/y shift grid and selects the lowest-error candidate.

### Fracture Analysis

#### Material
Mechanical material description used for elastic fracture-mechanics calculations, including Young's modulus `E`, Poisson ratio `nu_xy`, yield stress `sig_yield`, shear modulus `G`, stiffness matrix, inverse stiffness matrix, plane-stress or plane-strain assumption, and `kappa`.

#### Plane stress / plane strain
Mechanical assumptions for reducing the elastic constitutive relation. The package README states that input data should fulfill the plane-stress condition, while `Material(plane_strain=True)` is also available.

#### Von Mises strain (`eps_vm`)
Equivalent strain measure. In the current implementation it is computed by `InputData.calc_eps_vm()`, using `nu = 0.5` internally for the out-of-plane strain term.

#### Von Mises stress (`sig_vm`)
Equivalent stress computed from `sig_x`, `sig_y`, and `sig_xy`. Used scientifically as a stress-intensity indicator and operationally for automatic integral-path detection.

#### SIF
Stress intensity factor. CrackPy reports `K_I`, `K_II`, `K_III`, CJP-specific `K_F`, `K_R`, `K_S`, and integral-derived variants. Internal calculations are often in `MPa*sqrt(mm)` and converted to `MPa*sqrt(m)`.

#### J-integral
Path-independent fracture-mechanics integral. Implemented in `LineIntegral.integrate_j()` and aggregated across multiple paths.

#### Mode decomposition
Separation of the J-integral into mode I, mode II, and mode III contributions. Implemented in `LineIntegral.integrate_j_decompose()` by constructing symmetric/antisymmetric displacement fields on a regular grid and recomputing mode-specific strains, stresses, J values, and SIF estimates.

#### Interaction integral
Integral method used to derive mode I and mode II SIFs and T-stress using auxiliary crack-tip fields.

#### Bueckner-Chen integral
Path-independent integral used here to recover Williams coefficients and T-stress. Implemented in `LineIntegral.integrate_buckner_chen()`.

#### Williams coefficients
Crack-tip expansion coefficients `a_n`, `b_n`, and `c_n`. `a_1` and `b_1` map to mode I/II SIFs, `a_2` maps to T-stress, and `c_1` maps to mode III SIF.

#### HOST / HORT
Higher order singular terms and higher order regular terms of the Williams expansion.

#### CJP model
Christopher-James-Patterson crack-tip field model. CrackPy includes mixed-mode and mode-I displacement/stress fields and fitting routines.

#### T-stress
Non-singular stress term. CrackPy derives it from Williams `a_2`, Bueckner-Chen, stress-difference method, and interaction-integral methods.

## Experimental And Data Terms

These terms describe experimental concepts, input data, and workflow labels. They are domain-facing, but not fracture-mechanics methods by themselves.

#### DIC nodemap
Digital image correlation data export. CrackPy assumes semicolon-delimited nodemap files with displacement and strain channels.

#### FEM nodemap
Simulation data using the nodemap-shaped interface. FEM stress columns are hard-coded in `InputData.read_nodemap_file()` when `NodemapStructure.is_fem` is true.

#### Facet ID
Node/facet identifier in nodemap data. Connectivity remapping assumes loaded `facet_id` values and effectively converts one-based IDs to zero-based node references. This is a downstream artifact from the maintainers' default image-correlation software ZEISS GOM INSPECT and relates to its nomenclature for a DIC subset: facet.

#### Connection file
Connectivity data used by `InputData.set_connection_file()` and `InputData.to_vtk()` to build a PyVista unstructured mesh. If missing, VTK export reconstructs mesh geometry using Delaunay triangulation. This is extracted from facet data when exported by the respective DIC software package; for the maintainers, this is ZEISS GOM INSPECT.

#### Coordinate system
Expected specimen coordinate convention for current CrackPy workflows. The x-axis is the nominal crack-growth axis. `right` corresponds to positive x-direction crack growth, and `left` corresponds to negative x-direction crack growth.

#### Stage
Status: overloaded current term

CrackPy's current DIC acquisition-order index, usually parsed from a nodemap filename suffix. A stage identifies one acquired image/nodemap; load/force and cycle count are metadata of that stage, not the stage itself.

#### Side
Status: overloaded current term

`left` or `right` label identifying which specimen notch/crack is being analyzed, expressed in CrackPy's current x-direction convention. For Middle Tension specimens, the two sides correspond to opposing notch sides. For CT specimens, a crack starting at the left and growing to the right is the `right` side; the opposite direction is the `left` side. Crack-tip detection models were trained on the right-side crack convention, so left-side data is mirrored into that convention before detection. This term is current compatibility vocabulary for file, legacy API, detector setup, and result-naming boundaries, not a sustainable internal orientation model. Future internal interfaces should prefer an explicit [[glossary#Crack-tip coordinate system]].

#### Acquisition metadata
Metadata describing an acquired image or nodemap in an experiment, such as acquisition index, stage label, force, cycle count, load, timestamp, image name, source file, and acquisition software context.

#### Source identifier
Stable or reproducible identifier for an input, output, software artifact, model artifact, or acquisition object. Examples include file path plus hash, image name, nodemap name, result ID, model weights hash, or external graph identifier.

## CrackPy Implementation Terms

These terms name current software modules, containers, and lifecycle conventions. They should not be confused with the fracture-mechanics concepts above.

### Core Containers And Package Initialization

#### CrackPy package import
Importing `crackpy` eagerly imports major subpackages and calls `setup_logging()`. This makes package import both an API entry point and a side-effect boundary.

#### setup_logging
Package logging bootstrap. It loads the package logging configuration, redirects relative file-handler paths into the user cache location, then applies Python logging configuration with a basic fallback.

#### InputData
Central mutable data carrier for loaded nodemap arrays, metadata, derived fields, stress/strain helpers, coordinate transformation, masking, validation, and VTK export. See also [[glossary#Implicit InputData workflow]].

#### Required field
Attribute-level validation contract enforced by `InputData.require_fields()` and related shape validation. Many computational functions assume fields such as coordinates, displacements, strains, or stresses already exist.

#### Nodemap
CrackPy descriptor for a DIC or FEM text data file containing node or facet coordinates, displacements, strains, and optional metadata header lines. Represented by `crackpy.structure_elements.data_files.Nodemap`.

#### NodemapStructure
Column-index schema used by `InputData.read_nodemap_file()` to interpret nodemap columns. Defaults match the DIC layout.

#### DataFile / FileStructure
Shallow file and file-structure base descriptors in `crackpy.structure_elements.data_files`. They currently behave more like legacy or placeholder abstractions than deep modules.

#### Implicit InputData workflow
Observed call-order pattern around `InputData`: read nodemap data, compute equivalent strain, compute stresses when needed, run crack detection or transform into crack-tip-centered coordinates, then pass the mutated object into fracture analysis. This is not an explicit package abstraction; it is an implicit workflow enforced by caller convention.

#### CrackTipInfo
Implementation container for `crack_tip_x`, `crack_tip_y`, `crack_tip_angle`, and `left_or_right`. Used as the handoff from crack detection to fracture analysis. This is not the physical crack tip itself.

#### left_or_right
Current `CrackTipInfo` attribute name for the analyzed `side`. It carries the same conceptual value as `side`, but the naming should be treated as implementation-specific.

### Pipeline And Configuration Terms

#### CrackDetectionSetup
Batch crack-detection configuration object. It stores specimen size, sides, stage selection, detection window size, detection boundary, start offset, and angle detection radius.

#### CrackDetectionPipeline
Batch neural-network crack-detection orchestrator. It discovers nodemap stages, filters stages by force metadata, loops over sides, moves the detection window, runs tip/path/angle detection, writes plots, and writes `crack_info_by_nodemap.txt`.

#### FractureAnalysis
Single-nodemap fracture-analysis facade. It receives material, nodemap/input data, crack-tip information, and optional fitting/integral properties, then exposes results as post-run mutable attributes.

#### FractureAnalysisPipeline
Batch fracture-analysis orchestrator. It reads crack-tip rows, loads nodemaps, computes stresses, transforms data into crack-tip-centered coordinates, runs `FractureAnalysis`, and writes text, JSON, and plots.

#### single_run
Worker function used by the fracture-analysis pipeline. It combines CSV row interpretation, nodemap loading, stress calculation, coordinate transformation, analysis execution, result writing, and plotting for one nodemap/side case.

#### OptimizationProperties
Configuration object for Williams and CJP fitting. It controls angle gap, radial bounds, tick size, and Williams expansion terms.

#### IntegralProperties
Configuration object for multi-path line-integral evaluation. It controls number of paths, initial path dimensions, offsets, path spacing, mask tolerance, and Bueckner-Chen terms.

#### PathProperties
Configuration object for one generated integration path, usually derived from `IntegralProperties`.

### Crack Detection Implementation Terms

#### CrackDetection
Per-window detection context. It owns side handling, detection window size, offset, signed interpolation size, angle radius, device selection, interpolation, and preprocessing.

#### CrackTipDetection
Neural crack-tip detector wrapper around `ParallelNets`. It thresholds the tip segmentation mask and converts the selected tip pixel into global millimeter coordinates.

#### CrackPathDetection
Neural crack-path detector wrapper around the path detector model. It thresholds the predicted path mask and skeletonizes the crack path.

#### CrackAngleEstimation
Post-processing step that masks crack-path pixels near the detected crack tip, keeps the largest connected region, and fits a local line to estimate the crack angle.

#### Detection window
Status: qualified term

Square physical field of view mapped to `256 x 256` neural-network input pixels.

#### Detection window size
Physical side length of the square detection window in millimeters. This is named `window_size` in `CrackDetectionSetup` and `detection_window_size` in `CrackDetection`.

#### Interpolation size
Signed detection-window size used internally by neural crack detection. Positive values represent the right-side convention; negative values are used for left-side mirroring and displacement sign handling.

#### Offset / start offset
Status: overloaded current term

Millimeter shift of the detection window origin. Batch detection mutates the offset as the crack tip advances through stages.

#### Right-side crack convention
Neural-network orientation convention where the crack starts on the left side of the interpolated image and grows in positive x-direction. Left-side data is mirrored into this convention before inference. See also [[glossary#Side]] and [[glossary#Coordinate system]].

#### Crack tip pixel
Detected crack-tip position on the `256 x 256` neural-network grid. The implementation often stores this as row/column order before conversion into x/y millimeter coordinates.

#### Crack tip in mm
Global crack-tip coordinate after pixel-to-millimeter scaling, side mirroring, and window offset have been applied.

#### Crack tip mask
Status: qualified term

Binary neural-network segmentation for crack-tip pixels.

#### Crack path mask
Status: qualified term

Binary neural-network segmentation for crack-path pixels.

#### Crack path skeleton
One-pixel-wide path representation produced from the crack path mask with skeletonization.

#### Angle detection radius
Physical radius around the detected crack tip used to select nearby crack-path pixels for crack-angle estimation.

#### Circular path mask
Internal mask limiting crack-path pixels to the angle-detection radius around the detected crack tip.

#### Largest connected region
Crack-path post-processing step that keeps the largest connected pixel region before fitting the crack angle.

#### Model name
String passed to `get_model()`. The currently supported public names are `ParallelNets` and `UNetPath`.

#### ParallelNets
Crack-tip model architecture and model-name string. It combines segmentation with a parallel coordinate-regression branch, although runtime crack-tip detection primarily uses segmentation output.

#### UNetPath
Public model-name string for the crack-path detector. The instantiated implementation class is `UNet`, so this term currently names the model role rather than a distinct class.

#### UNet
Segmentation architecture used for crack-path prediction and related deep-learning utilities.

#### Input channels
Neural-network input fields. Runtime detection uses displacement channels `ux` and `uy`; training utilities can also include equivalent strain (`eps_vm`) as an additional channel.

#### Ground truth
Training label grid for crack detection. Current labels are `0` for background, `1` for crack path, and `2` for crack tip.

#### CrackTipDataset
Training dataset that loads serialized tensor samples and exposes input, target, and crack-tip coordinate data.

#### Input normalization
Per-channel normalization applied to neural-network inputs. Runtime detection uses NaN-aware mean and standard deviation.

#### Crack tip normalization
Training coordinate normalization that maps crack-tip pixel coordinates approximately into `[-1, 1]`.

#### EnhanceTip / EnhancePath
Training transforms that thicken crack-tip or crack-path labels so they survive interpolation, resizing, and augmentation.

#### Line-intercept detection
Independent crack-detection method fitting vertical displacement slices with a tanh-shaped function, deriving the crack path from the fitted transition coordinate, and locating the crack tip by equivalent-strain thresholding.

#### Grid component
Displacement component used by line-intercept detection, currently `ux` or `uy`.

#### Threshold window
Line-intercept setting for the number of consecutive path points whose `eps_vm` must exceed the threshold before the crack tip is accepted. Despite the name, this is a count, not a physical window.

#### Crack-tip correction objective
Optimization target used by correction methods. Current objectives include Williams fitting error and an `a_-1**2 + b_-1**2` objective.

### Fracture Analysis Implementation Terms

#### Optimization
Computational object that builds fitting grids, interpolates transformed `InputData`, and runs Williams or CJP displacement least-squares fits.

#### Williams fitting domain
Polar fitting region in crack-tip-centered coordinates, controlled by minimum radius, maximum radius, tick size, and crack-path angle gap.

#### Williams terms
Integer expansion orders used for Williams coefficients. Defaults include `[-1, 1, 2, 3, 4, 5]`; terms `1` and `2` are forced when needed for SIF and T-stress extraction.

#### IntegrationPath
Generated open rectangular contour around the crack tip, represented by path nodes and midpoint integration points.

#### LineIntegral
Computational object that interpolates fields onto an integration path and computes J-integral values, mode decomposition, interaction-integral SIFs, T-stress, stress-difference-method T-stress, and Bueckner-Chen Williams coefficients.

#### Automatic integral path detection
Workflow that derives integration-path geometry by thresholding mapped Von Mises stress (`sig_vm`) near the transformed crack tip.

#### ReusableLinearInterpolator
Interpolation utility that reuses Delaunay and barycentric weights for multiple field arrays at fixed query points.

#### Path result arrays
Fracture-analysis attributes that store per-path quantities, including `path_results`, `path_sizes`, `integration_points`, `tick_sizes`, and `num_of_path_nodes`.

#### Aggregate result buckets
Summary statistics written for path-based results, including `mean`, `median`, and `rej_out_mean` / `mean_wo_outliers`.

#### sifs_int
Legacy result bundle name on `FractureAnalysis`. Despite the name, it contains more than SIFs, including J values, T-stress values, Williams integral coefficients, and mode-decomposition results.

### Result, IO, And Visualization Terms

#### OutputWriter
Result adapter that serializes a live `FractureAnalysis` object to tagged text and JSON result files.

#### OutputReader
Result adapter that parses tagged text output into pandas DataFrames and can flatten result tags into CSV columns.

#### Result tag
Text/JSON section name used as a result schema key. Examples include `Experiment_data`, `CJP_results`, `CJP_modeI_results`, `Williams_fit_results`, `SIFs_integral`, `Bueckner_Chen_integral`, `Path_SIFs`, `Path_Williams_a_n`, `Path_Williams_b_n`, and `Path_Properties`.

#### `*_Output.txt`
Fracture-analysis text result file pattern, usually `<nodemap_stem>_<side>_Output.txt`.

#### Flattened result CSV
Tabular result summary generated by `OutputReader.make_csv_from_results()`, where tag names and field names become column prefixes.

#### Workflow folders
Conventional output folders used by the fracture-analysis pipeline: `txt-files`, `plots`, and `json`.

#### crack_info_by_nodemap.txt
CSV-like detection-to-fracture-analysis handoff file with columns `Filename`, `Crack Tip x [mm]`, `Crack Tip y [mm]`, `Crack Angle`, and `Side`.

#### PlotSettings
Plot configuration object for axis limits, background field, colorbar limits, and colorbar extension behavior.

#### Plotter
Visualization adapter that consumes `FractureAnalysis`, its `InputData`, and result attributes to write result, fitting, and integration-path plots.

#### plot_prediction
Crack-detection visualization helper that overlays crack-tip predictions, segmentation, labels, and crack-path scatter on an interpolated background.

#### SegGradCAM
Segmentation Grad-CAM attention utility for crack-detection models. The repository also uses the spelling `Seg-Grad-CAM` in prose.

#### visu_layers
Training/evaluation setup field listing model layers used for Grad-CAM-style visualization.

#### result_data.py
Currently empty module under `crackpy.results`. It is a placeholder name, not an implemented structured result container.

#### Provenance metadata
Structured metadata that records how a CrackPy result was produced, including software version, execution commit, analysis-function identity, configuration, inputs, outputs, method references, timestamps, and optional hashes.

#### Analysis function identity
Stable name for a computational analysis step such as Williams fitting, crack-tip detection, SIF evaluation, optimization, interpolation, or preprocessing. This should be distinct from incidental Python method names when used for provenance or orchestration.

#### Function-relevant commit
Commit identifier representing the latest relevant change to an analysis function or its declared dependency scope. This may differ from the execution commit when results are compared against newer CrackPy code.

#### Result schema version
Explicit version for a serialized result format, including text tags, JSON keys, units, and nested result structure.

#### Method reference
Structured reference to a paper, book, DOI, URL, or internal method note associated with a specific analysis function.

#### Compact knowledge-graph export
Reduced metadata export intended for the main RDF/JSON knowledge graph. It stores the facts needed for querying, traceability, and targeted re-analysis without modeling every internal helper call.

#### Detailed provenance artifact
Optional richer provenance document, potentially PROV-O-like or JSON-LD/RDF-based, that records execution activities, used entities, generated entities, and software/user/orchestrator agents outside the compact main graph.

### Legacy And Fixture Vocabulary

#### Nodemaps / GroundTruth / Connections / interim
Directory-name conventions used by tests and data-preparation workflows for nodemap files, crack-detection labels, mesh connectivity files, and serialized intermediate tensors.

#### Dummy2 / EBr10 / Aramis_in_line
Hard-coded experiment or fixture identifiers used in deep-learning setup utilities and tests. They should be treated as workflow-specific or legacy vocabulary unless the project decides they are supported public concepts.

#### Coors / Disps / EpsVonMises / InterpOnArray
Legacy or documentation-facing names for coordinate arrays, displacement arrays, equivalent-strain arrays, and interpolation helpers. Current implementation vocabulary more often uses `interp_coors`, `interp_disps`, `interp_eps_vm`, and `interpolate_on_array`.

### Overloaded Term Warnings

#### Path
Status: overloaded warning

Avoid using bare `path` as a canonical glossary term. Prefer qualified terms such as crack path, integration path, file path, model path, output path, or path detector.

#### Window
Status: overloaded warning

Avoid using bare `window` as a canonical glossary term. Prefer qualified terms such as detection window, detection window size, threshold window, crop window, or plot window.

#### Mask
Status: overloaded warning

Avoid using bare `mask` as a canonical glossary term. Prefer qualified terms such as crack tip mask, crack path mask, circular path mask, attention mask, or plot triangulation mask.

## Architecture Terms

#### Module
Anything with an interface and implementation: package, file, class, function, or pipeline slice.

#### Interface
Everything a caller must know to use a module correctly, including call order, required attributes, units, side effects, and error modes.

#### Seam
Where an interface lives and where behavior can vary without editing callers.

#### Adapter
Concrete implementation at a seam, such as a file loader, model provider, progress reporter, or result writer.

#### Depth
Leverage at the interface. A deep module hides significant behavior behind a small interface; a shallow module exposes nearly as much complexity as it contains.

#### Leverage
What callers gain from a deep module.

#### Locality
What maintainers gain when change and verification are concentrated in one module.
