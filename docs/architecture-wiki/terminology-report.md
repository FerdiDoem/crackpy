# Terminology Extraction Report

Status: architecture wiki snapshot  
Scope: implementation terminology discovered during the glossary-focused architecture wiki pass.
Role: Audit extracted terms, naming inconsistencies, ambiguous terms, and unresolved terminology questions. Stable definitions belong in [[glossary]], and resolved decisions belong in [[decision-log]].

This note separates observed terminology from proposed canonicalization. The stable definitions belong in [[glossary]]. The naming observations here are refactor-planning input, not a request to rename code during the current mapping phase.

## Newly Discovered Implementation Terms

### Core Architecture And Framework Terms

- `CrackPy package import`: package import side-effect boundary that initializes logging and imports major subpackages.
- `setup_logging`: package logging bootstrap.
- `InputData`: central mutable carrier for nodemap-derived arrays, metadata, transformations, derived fields, mechanics helpers, and export utilities.
- `Required field`: validation contract for attributes expected by downstream processing.
- `DataFile` / `FileStructure`: shallow file descriptor base classes.
- `left_or_right`: current `CrackTipInfo` attribute carrying the same conceptual value as [[glossary#Side]].
- `single_run`: fracture-analysis pipeline worker that combines row interpretation, loading, stress calculation, transformation, analysis, output, and plotting.

### Pipeline And Configuration Terms

- `CrackDetectionSetup`: batch detection configuration.
- `CrackDetectionPipeline`: batch neural-network detection orchestration.
- `FractureAnalysis`: single-nodemap analysis facade.
- `FractureAnalysisPipeline`: batch fracture-analysis orchestration.
- `OptimizationProperties`: fitting-domain configuration.
- `IntegralProperties`: multi-path line-integral configuration.
- `PathProperties`: single integration-path configuration.
- `PlotSettings`: plotting configuration.

### Crack Detection Terms

- `CrackDetection`: per-window detection context.
- `CrackTipDetection`: neural crack-tip detector wrapper.
- `CrackPathDetection`: neural crack-path detector wrapper.
- `CrackAngleEstimation`: local angle-estimation post-processing.
- `Detection window size`: physical side length of the neural-network field of view.
- `Interpolation size`: signed size used for side mirroring.
- `Offset` / `start offset`: moving millimeter offset of the detection window.
- `Right-side crack convention`: training/runtime orientation convention for crack-tip detection.
- `Crack tip pixel`: row/column grid coordinate before conversion into millimeters.
- `Crack tip in mm`: global x/y crack-tip coordinate after scaling, mirroring, and offset.
- `Crack path skeleton`: skeletonized path segmentation.
- `Angle detection radius`: radius used for local path-angle fitting.
- `Circular path mask`: angle-estimation mask around the crack tip.
- `Largest connected region`: path-segmentation cleanup step before angle fitting.
- `Model name`: logical model selector for `ParallelNets` and `UNetPath`.
- `ParallelNets`: crack-tip model name and architecture.
- `UNetPath`: crack-path model role/name.
- `UNet`: segmentation architecture used behind `UNetPath`.
- `Input channels`: neural-network channels, usually `ux` and `uy`.
- `Ground truth`: label grid with background, crack path, and crack tip labels.
- `CrackTipDataset`: training dataset wrapper.
- `Input normalization`: per-channel neural-network input normalization.
- `Crack tip normalization`: training coordinate normalization to approximately `[-1, 1]`.
- `EnhanceTip` / `EnhancePath`: label-thickening transforms.
- `Line-intercept detection`: tanh-fit crack-detection path.
- `Grid component`: displacement component used by line-intercept detection.
- `Threshold window`: line-intercept consecutive-point threshold count.
- `Crack-tip correction objective`: Williams-fit-based correction target.

### Fracture Analysis Terms

- `Optimization`: computational object for Williams and CJP least-squares fitting.
- `Williams fitting domain`: polar grid and angular gap used for displacement fitting.
- `Williams terms`: selected integer expansion orders.
- `IntegrationPath`: generated open rectangular contour.
- `LineIntegral`: computational object for J, mode decomposition, interaction, stress-difference, and Bueckner-Chen integrals.
- `Automatic integral path detection`: path geometry derived from `sig_vm` thresholding.
- `ReusableLinearInterpolator`: Delaunay/barycentric interpolation cache.
- `Path result arrays`: per-path attributes such as `path_results`, `path_sizes`, `integration_points`, `tick_sizes`, and `num_of_path_nodes`.
- `Aggregate result buckets`: summary buckets such as `mean`, `median`, and `rej_out_mean`.
- `sifs_int`: legacy fracture-analysis result bundle name that contains more than SIF values.

### IO, Workflow, Visualization, And Legacy Terms

- `OutputWriter`: adapter from `FractureAnalysis` internals to text/JSON files.
- `OutputReader`: parser from tagged text files to DataFrames and flattened CSV.
- `Result tag`: stringly typed result section key.
- `*_Output.txt`: fracture-analysis text output filename pattern.
- `Flattened result CSV`: tag/field-prefixed result table.
- `Workflow folders`: `txt-files`, `plots`, and `json`.
- `crack_info_by_nodemap.txt`: crack-detection to fracture-analysis handoff file.
- `plot_prediction`: crack-detection overlay plotting helper.
- `SegGradCAM`: segmentation attention visualization utility.
- `visu_layers`: setup field for attention visualization layers.
- `result_data.py`: currently empty result module placeholder.
- `Nodemaps`, `GroundTruth`, `Connections`, `interim`: test/data-preparation folder conventions.
- `Dummy2`, `EBr10`, `Aramis_in_line`: hard-coded experiment or fixture identifiers.
- `Coors`, `Disps`, `EpsVonMises`, `InterpOnArray`: legacy or documentation-facing names for current interpolation vocabulary.

## Naming Inconsistency Report

### Side And Orientation

- `side`, `sides`, and `left_or_right` all refer to left/right crack-side information.
- Documentation has mentioned short values `l`/`r`, while code and pipelines primarily use full strings `left`/`right`.
- The same value currently carries specimen side, nominal crack-growth direction, output filename suffix, and neural-network mirroring behavior.
- Canonical glossary wording now prefers [[glossary#Side]] with values `left` and `right`, while marking `left_or_right` as implementation-specific.
- Future planning now uses [[glossary#CrackTipFrame]] as the canonical internal orientation concept and [[glossary#Geometry profile]] to separate current surface-planar support from future parameterized-surface, 3D-surface, or volumetric capabilities.

### Stage And Sequence Index

- `stage` is used as a filename-derived source label, acquisition-order index, and stage selector for detection.
- Load/force and cycle are metadata of the stage, not the stage itself.
- OQ-002 resolved the future planning vocabulary: `stage` remains source-specific metadata, while [[glossary#Sequence index]] is the generic ordering key and [[glossary#Input ID]] is the stable identity.
- Matching should be modeled as an explicit [[glossary#Mapping policy]] over input metadata, with outputs such as `input_id -> representative_input_id`.

### Nodemap And Data Carrier

- `Nodemap` can mean a file descriptor, a file format, or loaded nodemap data in prose.
- The glossary now distinguishes `Nodemap` from `InputData`.
- Proposed canonical split for future planning: `nodemap file`, `Nodemap descriptor`, and `InputData`.

### Crack Tip And CrackTipInfo

- `Crack tip` is the physical point.
- `CrackTipInfo` is the implementation handoff container.
- `crack_tip_angle`, output `Crack Angle`, text `Crack_tip_phi`, and generic `angle`/`phi` names all describe related angle data, often without explicit unit naming.

### Window, Size, And Offset

- `window_size`, `detection_window_size`, `interp_size`, `size`, crop size, and line-intercept `window_size` are overloaded.
- The glossary now reserves `Detection window size` for physical millimeter size and `Interpolation size` for the signed mirroring value.
- Line-intercept `window_size` is really a consecutive fitted crack-path sample count. Future planning vocabulary should use [[glossary#Min consecutive strain exceedance count]] and keep `window_size` as a legacy implementation name.
- Related line-intercept constructor names also need more precise descriptions: `x_min`/`x_max`/`y_min`/`y_max` bound the line-intercept evaluation region, `tick_size_x`/`tick_size_y` are nominal interpolation-grid spacing controls, `grid_component` selects the fitted displacement component, `eps_vm_threshold` is applied along the fitted crack path, and `angle_estimation_mm_radius` selects samples for local angle fitting.

### Models And Deep Learning

- `ParallelNets` is both a public model-name string and a class name.
- `UNetPath` is a public model-name string but instantiates `UNet`.
- Resolved OQ-009: future model metadata should split stable `model_id`, `model_role`, `architecture`, `weights_id`, and aliases. `UNetPath` remains compatibility vocabulary for the current crack-path detector weights and selector.
- `model_name` can mean logical model name or weight-file stem.
- `target`, `label`, `ground_truth`, `mask`, and `segmentation` are related but not equivalent tensor terms.

### Coordinates, Displacements, Strains, And Stresses

- Pixel coordinates are often described as x/y but represented in row/column order.
- `coor_x`, `x_coordinates`, `x_mesh`, and output names such as `LineXL` mix coordinate naming styles.
- `disp_x`, `disp_y`, `ux`, `uy`, and analytical names such as `v_x_ana` mix displacement naming styles.
- `eps_x`, `eps_xx`, `eps_xy`, `eps_xz` and `sig_x`, `sigma_xz`, `sig_vm` mix compact and tensor-style conventions.

### Fracture Result Names

- `Bueckner-Chen` is the canonical scientific/domain spelling in glossary text, while code contains legacy `buckner_*` identifiers.
- Resolved OQ-012: future refactor vocabulary should use `bueckner_chen_*` identifiers and preserve `buckner_*` only as compatibility or deprecation vocabulary.
- `SIFs_integral`, `Path_SIFs`, and `sifs_int` are narrower names than the data they contain.
- Text output uses names such as `K_J-I`; JSON uses names such as `K_I_J`.
- Future planning accepts versioned JSON as the main scalar result output, but the current public-vs-legacy result-name boundary remains unresolved.
- `mean_wo_outliers` and `rej_out_mean` refer to the same aggregate result bucket.
- Some fixtures and current writer output differ on tags such as `CJP_modeI_results` and Williams error fields.

### Output And Workflow Folders

- The fracture-analysis pipeline writes to `txt-files`, `plots`, and `json`.
- Some scripts use `results` as an output folder.
- `Plotter` filenames and `OutputWriter` text filenames do not follow exactly the same suffix convention.
- Resolved OQ-014: `Dummy2`, `EBr10`, `Aramis_in_line`, and similar hard-coded preset names are fixture/workflow keys, not domain vocabulary.

## Ambiguous Or Overloaded Terms

- `side`: specimen side, crack-growth direction, model orientation, mirroring switch, and filename component.
- `stage`: source label, acquisition-order index, selected detection stage, max-force stage, and assigned surrogate stage.
- `path`: crack path, integration path, file path, model path, output path, and path detector.
- `window`: detection field, threshold count, crop size, and plot window.
- `size`: specimen size, detection-window size, interpolation size, crop size, and tensor resize target.
- `offset`: detection-window origin, experiment field-of-view offset, and moving pipeline state.
- `mask`: segmentation mask, circular angle mask, attention mask, and plot triangulation mask.
- `error`: fit cost, correction objective, contour value, and training loss.
- `tip`: physical crack tip, pixel label, regressor coordinate, corrected coordinate, and handoff value.
- `reliability`: crack-detection model metric, not a statistical reliability measure.

## Unresolved Terminology Questions

Unresolved questions are now centralized in [[open-questions]].

Related question IDs:

- OQ-001: `side` vocabulary and concept split.
- OQ-002: resolved `stage` as source-specific metadata and `sequence_index` as generic ordering vocabulary.
- OQ-004: resolved line-intercept `window_size` as [[glossary#Min consecutive strain exceedance count]] in future planning vocabulary.
- OQ-005: resolved result schema versioning and main JSON output.
- OQ-006: public result names versus legacy implementation names.
- OQ-007: resolved crack-tip correction return semantics; use `corrected_crack_tip_estimate`, `correction_delta`, and `source_crack_tip_estimate` in future planning vocabulary.
- OQ-009: resolved `UNetPath` as compatibility vocabulary for the current crack-path detector selector and weights; future metadata should use explicit model identity fields.
- OQ-011: Roman mode labels versus numeric suffixes.
- OQ-012: resolved `buckner` as legacy implementation spelling and `bueckner_chen_*` as future refactor vocabulary.
- OQ-013: 256-sample / 255-interval detection-grid convention.
- OQ-014: resolved fixture-name vocabulary as non-domain preset/test data keys.

## Documentation Files Updated

- [[glossary]]: expanded implementation glossary with core, pipeline, crack detection, fracture analysis, IO, visualization, and legacy terms.
- [[terminology-report]]: added this report with newly discovered terms, naming inconsistencies, ambiguous terms, and unresolved questions.
- [[README]]: added the terminology report to the exploration entry points.
- [[crack-detection]]: added terminology references for stable definitions and overloaded detection terms.
- [[fracture-analysis]]: added terminology references for fitting, integral, and result naming.
- [[results-io-workflows]]: added terminology references for result-tag, folder, and output-schema naming.
- [[scientific-context]]: aligned Bueckner-Chen wording with the glossary spelling.
