# Module Inventory

Status: observed package inventory from local AST pass

This note maps package modules, classes, functions, and key dependencies. It excludes tests and scripts; workflows outside the installed package are mapped in [[results-io-workflows]].

## Root

### `crackpy/__init__.py`

Imports:

- `crackpy.crack_detection`
- `crackpy.crack_detection.utils`
- `crackpy.fracture_analysis`
- `crackpy.structure_elements`
- `setup_logging`

Side effect: calls logging setup during package import.

### `crackpy/logging_config.py`

Functions:

- `_prepare_file_handlers`
- `setup_logging`

Dependencies: `logging.config`, `yaml`, `importlib`, `datetime`, `pathlib`.

## Input

### `crackpy/input/input_data.py`

Classes:

- `InputData`

Important methods:

- `set_nodemap_file`
- `set_connection_file`
- `read_nodemap_file`
- `read_header`
- `require_fields`
- `to_vtk`
- `set_data_manually`
- `transform_data`
- `calc_eps_vm`
- `calc_stresses`
- `get_facet_size`

Functions:

- `apply_mask`
- `calculate_principal_tensor_components`

Key dependencies:

- `numpy`
- `pyvista`
- `crackpy.structure_elements.data_files`
- `crackpy.structure_elements.material.Material`

### `crackpy/input/crack_tip_info.py`

Classes:

- `CrackTipInfo`

Important methods:

- `set_manually`

## Structure Elements

### `crackpy/structure_elements/data_files.py`

Classes:

- `FileStructure`
- `NodemapStructure`
- `DataFile`
- `Nodemap`

Purpose:

- lightweight descriptors for file naming, folders, and nodemap column schema.

### `crackpy/structure_elements/material.py`

Classes:

- `Material`

Internal methods:

- `_stiffness_matrix`
- `_stiffness_matrix_plane_strain`
- `_inverse_stiffness_matrix`

Purpose:

- elastic material parameters, stiffness matrices, shear modulus, yield stress, `kappa`.

## Fracture Analysis

### `crackpy/fracture_analysis/analysis.py`

Classes:

- `FractureAnalysis`

Important methods:

- `run`
- `_run_cjp_optimization_modeI`
- `_run_cjp_optimization_mixedmode`
- `_run_williams_optimization`
- `_run_line_integrals`
- `_aggregate_integral_results`
- `mean_wo_outliers`

Key dependencies:

- `line_integration.LineIntegral`
- `optimization.Optimization`
- `InputData`
- `CrackTipInfo`
- `Material`

### `crackpy/fracture_analysis/optimization.py`

Constants:

- `DEFAULT_WILLIAMS_OPT_TERMS = [-1, 1, 2, 3, 4, 5]`

Classes:

- `OptimizationProperties`
- `Optimization`

Important methods:

- `optimize_cjp_displacements_modeI`
- `optimize_cjp_displacements_mixedmode`
- `optimize_williams_displacements_xy`
- `optimize_williams_displacements_z`
- `residuals_cjp_displacements_modeI`
- `residuals_cjp_displacements_mixedmode`
- `residuals_williams_displacements`
- `residuals_williams_displacements_z`
- `make_cartesian`
- `ensure_defaults_williams`

Key dependencies:

- `scipy.optimize`
- analytical fields from `crack_tip.py`
- `ReusableLinearInterpolator`
- `InputData`
- `Material`

### `crackpy/fracture_analysis/line_integration.py`

Constants:

- `DEFAULT_BUCKNER_CHEN_TERMS = [1, 2, 3, 4, 5]`

Classes:

- `IntegralProperties`
- `PathProperties`
- `IntegrationPath`
- `LineIntegral`

Important methods:

- `IntegralProperties.set_automatically`
- `IntegrationPath.get_integration_points`
- `LineIntegral.integrate_all`
- `LineIntegral.integrate_j`
- `LineIntegral.integrate_j_decompose`
- `LineIntegral.integrate_i_k1_k2`
- `LineIntegral.integrate_i_t`
- `LineIntegral.integrate_t_sdm`
- `LineIntegral.integrate_buckner_chen`
- `LineIntegral.ensure_defaults_buckner_chen`

Key dependencies:

- `scipy.interpolate.griddata`
- `scipy.ndimage.label`
- `InputData`
- `Material`
- `ReusableLinearInterpolator`
- analytical crack-tip auxiliary fields.

### `crackpy/fracture_analysis/crack_tip.py`

Functions:

- `williams_stress_field`
- `williams_displ_field_xy`
- `williams_stress_field_3d`
- `williams_displ_field_z`
- `cjp_stress_field_mixedmode`
- `cjp_displ_field_mixedmode`
- `cjp_stress_field_modeI`
- `cjp_displ_field_modeI`
- `eigenfunction`
- `get_crack_nearfield`
- `get_zhao_solutions`
- `unit_of_williams_coefficients`

Purpose:

- analytical Williams, CJP, near-field, eigenfunction, and auxiliary solutions.

### `crackpy/fracture_analysis/pipeline.py`

Functions:

- `single_run`

Classes:

- `FractureAnalysisPipeline`

Important methods:

- `set_integral_props_manually`
- `find_max_force_stages`
- `find_integral_props`
- `run`

Key dependencies:

- `FractureAnalysis`
- `IntegralProperties`
- `OptimizationProperties`
- `CrackTipInfo`
- `InputData`
- `OutputWriter`
- `Plotter`
- `Material`
- `ProcessPoolExecutor`
- `rich.progress`

### `crackpy/fracture_analysis/utils.py`

Classes:

- `ReusableLinearInterpolator`

Purpose:

- Delaunay/barycentric interpolation reusable across several field arrays at fixed points.

## Crack Detection

### `crackpy/crack_detection/detection.py`

Classes:

- `CrackDetection`
- `CrackTipDetection`
- `CrackPathDetection`
- `CrackAngleEstimation`

Purpose:

- neural-network crack tip/path detection and crack-angle estimation.

Key dependencies:

- `torch`
- `scipy.ndimage`
- `skimage.morphology`
- `sklearn.linear_model`
- detection preprocessing/interpolation utilities
- `InputData`

### `crackpy/crack_detection/pipeline/pipeline.py`

Classes:

- `CrackDetectionSetup`
- `CrackDetectionPipeline`

Important methods:

- `filter_detection_stages`
- `run_detection`
- `assign_remaining_stages`
- `write_results`

Purpose:

- batch neural-network detection workflow and crack-tip-info output.

### `crackpy/crack_detection/line_intercept.py`

Classes:

- `CrackDetectionLineIntercept`

Functions:

- `plot_grid_errors`

Important methods:

- `run`
- `plot`

Purpose:

- displacement-slice line-intercept crack detection.

### `crackpy/crack_detection/correction.py`

Functions:

- `run_williams_optimization`

Classes:

- `CrackTipCorrection`
- `CrackTipCorrectionGridSearch`
- `CustomCorrection`

Important methods:

- `correct_crack_tip`
- `correct_crack_tip_optimization`
- `correct_crack_tip_differential_evolution`
- `correct_crack_tip_grid_search`
- `custom_correct_crack_tip`

Purpose:

- crack-tip correction using Williams fitting, Rethore-style updates, symbolic-regression formulas, optimization, differential evolution, and grid search.

### `crackpy/crack_detection/model.py`

Functions:

- `get_model`

Purpose:

- instantiate/load pretrained `ParallelNets` or `UNetPath`, downloading weights if absent.

## Crack Detection Data

### `crackpy/crack_detection/data/datapreparation.py`

Functions:

- `ground_truth_import`
- `import_data`

Purpose:

- import nodemaps and optional ground truth for training/test data.

### `crackpy/crack_detection/data/dataset.py`

Classes:

- `CrackTipDataset`

Important methods:

- `__len__`
- `__getitem__`
- `get_cracktips`
- `calculate_means_and_stds`

### `crackpy/crack_detection/data/interpolation.py`

Functions:

- `interpolate_on_array`
- `interpolate`

Purpose:

- map nodemap fields onto fixed-size NN arrays.

### `crackpy/crack_detection/data/preprocess.py`

Functions:

- `normalize`
- `target_to_crack_tip_position`

### `crackpy/crack_detection/data/transforms.py`

Classes:

- `AddZeroComponent`
- `CrackTipNormalization`
- `InputNormalization`
- `EnhanceTip`
- `EnhancePath`
- `RandomCrop`
- `RandomFlip`
- `RandomRotation`
- `Resize`
- `ToCrackTipMasks`
- `ToCrackTips`
- `ToCrackPathMasks`
- `ToCrackTipsAndMasks`

Functions:

- `denormalize_crack_tips`
- `rotate_point`
- `calculate_crop_size`

## Crack Detection Deep Learning

### `crackpy/crack_detection/deep_learning/nets.py`

Classes:

- `ParallelNets`
- `UNet`
- `DoubleConv`
- `Down`
- `Base`
- `Up`
- `OutConv`

### `crackpy/crack_detection/deep_learning/loss.py`

Classes:

- `DiceLoss`
- `MSELoss`

### `crackpy/crack_detection/deep_learning/train.py`

Classes:

- `TrainDocu`

Functions:

- `train_segmentation_model`
- `train_parallel_model`

### `crackpy/crack_detection/deep_learning/setup.py`

Classes:

- `Experiments`
- `Setup`

Important methods:

- `load_data`
- `set_model`
- `set_stages`
- `set_size`
- `set_if_target_exists`
- `set_visu_layers`
- `set_out_ids`
- `set_output_path`

### `crackpy/crack_detection/deep_learning/docu.py`

Classes:

- `Documentation`

Functions:

- `count_parameters`

### `crackpy/crack_detection/deep_learning/attention.py`

Classes:

- `UNetWithHooks`
- `ParallelNetsWithHooks`
- `SegGradCAM`

Functions:

- `plot_overview`

Purpose:

- feature/gradient hooks and Seg-Grad-CAM visualization for segmentation models.

## Crack Detection Utilities

### `crackpy/crack_detection/utils/basic.py`

Functions:

- `concatenate_np_dicts`
- `numpy_to_tensor`
- `dict_to_list`

### `crackpy/crack_detection/utils/evaluate.py`

Functions:

- `get_deviation`
- `get_segmentation_deviation`
- `get_reliability`

### `crackpy/crack_detection/utils/plot.py`

Functions:

- `plot_prediction`

### `crackpy/crack_detection/utils/utilityfunctions.py`

Functions:

- `get_nodemaps_and_stage_nums`
- `calculate_segmentation`
- `find_most_likely_tip_pos`

## Results

### `crackpy/results/write.py`

Classes:

- `OutputWriter`

Important methods:

- `write_header`
- `write_results`
- `write_json`

### `crackpy/results/read.py`

Classes:

- `OutputReader`

Functions:

- `is_stringfloat`

Important methods:

- `read_tag_data`
- `make_csv_from_results`

### `crackpy/results/plot.py`

Classes:

- `PlotSettings`
- `Plotter`

Important methods:

- `Plotter.plot`

### `crackpy/results/result_data.py`

Empty placeholder.

