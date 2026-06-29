# Candidate 006: Crack-Detection Method And Pretrained Artifact Seam

Status: proposed
Role: Future architecture candidate for separating crack-detection method identity, neural-network architecture, pretrained artifacts, and download/cache policy.

## Observed Evidence

- [[crack-detection]] documents neural-network detection, line-intercept detection, correction methods, `get_model()`, supported model names, and download behavior.
- [[results-io-workflows]] documents scripts that use pretrained models.
- [[coupling-map]] records side effects such as directory creation and model downloads.

## Problem

The legacy `get_model()` path combines detector selection, network architecture construction, local cache policy, network download, weights loading, and device behavior. The term `model` is too broad for this seam because it can mean a method family, crack-detection task, network architecture, pretrained weights artifact, cache identity, or loaded PyTorch object.

Looking from the method side makes the problem wider than `UNetPath` and `ParallelNets`. CrackPy currently has or plans around several crack-tip and crack-path methods:

- neural-network crack-tip detection with `ParallelNets`;
- neural-network crack-path segmentation with the `UNetPath` compatibility selector;
- line-intercept crack-tip detection from displacement/strain profiles;
- Williams-series crack-tip correction/refinement methods, including Rethore-style correction and symbolic-regression correction;
- search or optimization methods over candidate crack-tip positions, including grid search, differential evolution, and Williams-fit-error minimization;
- image-processing and edge/contour based methods seen in the literature, such as Sobel/Canny-style crack edge extraction or displacement-field discontinuity detection;
- manual or externally imported crack-tip estimates used as workflow inputs.

These should not all be called "models". The architecture needs to name the method output and method family first, then the implementation artifact.

## Method-Side Vocabulary

- `CrackTipLocalizationMethod`: method that estimates a crack-tip position or crack-tip frame. Literature also uses crack-tip detection, identification, localization, position estimation, and tracking; CrackPy should reserve the internal method category for the output: a crack-tip estimate.
- `CrackPathSegmentationMethod`: method that identifies a crack path or crack-line mask. This is distinct from crack-tip localization even when both are performed by related networks.
- `CrackTipCorrectionMethod`: method that refines an existing crack-tip estimate and should expose both the corrected estimate and correction delta.
- `CrackGrowthTrackingMethod`: method that links crack-tip estimates over frames, stages, cycles, or time to produce crack length or propagation curves.
- `CrackDetectionMethod`: broad umbrella term only. Avoid using it when the method output is specifically a tip estimate, path mask, correction delta, or growth track.
- `DetectionTask`: implementation-facing task label such as `crack_tip_localization`, `crack_path_segmentation`, `crack_tip_correction`, or `crack_growth_tracking`.
- `ImplementationFamily`: algorithm family such as neural network, line intercept, image edge detection, Williams-series fit, symbolic regression, grid search, differential evolution, manual import, or external provider.
- `NetworkArchitecture`: neural-network architecture such as `UNet` or `ParallelNets`; this is not a method identity by itself.
- `PretrainedWeightsArtifact`: concrete file or external artifact, such as `UNetPath.pth`; this is not a method identity by itself.
- `CompatibilitySelector`: current public string accepted by legacy APIs, such as `UNetPath` or `ParallelNets`.

Literature terminology is not fully uniform, but the recurring split is stable enough for architecture planning: papers distinguish crack-tip position/location/localization/identification from crack-path detection/segmentation/tracking, and mechanics-based methods often localize or correct the crack tip by fitting Williams fields or minimizing residuals rather than by loading a neural-network artifact.

## Future Direction

First define method-side metadata, then introduce a provider interface for implementation artifacts. A future provider should not own method identity by itself; it should provide implementation assets for a method that has already declared its output task and method family.

Future metadata should not rely on the current `model_name` string alone. It should split:

- stable `method_id`, preferably linked to the method, paper, or registered method family;
- `detection_task`, such as `crack_tip_localization` or `crack_path_segmentation`;
- `implementation_family`, such as neural network, line intercept, Williams-series correction, grid search, or manual import;
- network `architecture`, such as `UNet`;
- `weights_id`, such as the current `UNetPath.pth`;
- aliases for compatibility selectors such as `UNetPath`.

First implemented metadata slice:

- `method_spec`: the shared method metadata shape used by Williams-fit and CJP-fit provenance specs. It carries `method_id`, `display_name`, `kind`, `method_revision`, `implementation_ref`, `aliases`, and `references`. It exists so crack detection does not grow a parallel method registry vocabulary.
- `method_id`: durable method identity inside `method_spec`, such as `crackpy.detection.parallel_nets_crack_tip_localization`. It exists so future results and frontend views do not depend on a Python import path or legacy selector.
- `display_name`: human-facing method label inside `method_spec` for reports and UI. It exists so callers do not derive readable names from IDs.
- `kind`: generic method category inside `method_spec`, such as `crack_tip_estimate` or `crack_path_segmentation`. It exists so detection methods can sit beside analysis methods such as Williams fit or CJP fit.
- `detection_task`: detection-specific declared method output, such as `crack_tip_localization` or `crack_path_segmentation`. It exists to separate crack-tip localization from crack-path segmentation even when both are neural workflows.
- `implementation_family`: detection-specific algorithm family, such as `neural_network` or `line_intercept`. It exists so non-neural methods are not forced into network vocabulary.
- `method_revision`: maintainer-controlled revision of method meaning inside `method_spec`. It exists as the future stale-result and provenance marker for method semantics.
- `aliases`: current public selectors or aliases inside `method_spec`, such as `ParallelNets`, `UNetPath`, `line_intercept`, or `CrackDetectionLineIntercept`. They exist to keep legacy callers readable during migration.
- `implementation_ref`: current code location inside `method_spec` for maintainers. It exists for traceability but is not the durable method identity.
- `network_architecture`: optional detection-specific architecture name, such as `UNet` or `ParallelNets`. It exists only for neural-network methods.
- `weights_artifact_id`: optional detection-specific artifact name, such as `UNetPath.pth`. It exists only when a pretrained weights artifact affects the implementation.

First generic method-definition slice:

- `MethodDefinition`: importable wrapper around `MethodSpec`, a package domain, method-level tasks, and declared artifact roles.
It exists so detection methods can be listed beside Williams-fit and CJP-fit metadata without moving numerical runners or source adapters into a registry.
- `MethodArtifactDefinition`: declared method artifact dependency or output, currently used by detection metadata for pretrained weights such as `ParallelNets.pth` or `UNetPath.pth`.
It records artifact role and requiredness without loading files, choosing devices, creating cache folders, or downloading from Zenodo.
- `known_crack_detection_method_definitions()`: detection adapter that returns the current detection metadata in the generic `MethodDefinition` shape.
It is not a provider seam and does not replace `get_model()`.

## Seams / Interfaces / Adapters

- Seam: crack-detection method metadata and implementation artifact provision.
- Interface: method identity, detection task, implementation family, optional network architecture, optional weights source, device behavior for neural-network implementations.
- Adapters: local weights, Zenodo cache/download, test double, manual/imported estimate provider, future workflow-managed provider.

## Consequences

- Detection algorithms become less coupled to filesystem and network policy.
- Tests can avoid network and cache side effects.
- Current public detector selectors must remain stable or be migrated deliberately.
- `UNetPath` can remain readable as a compatibility alias while future provenance and orchestration use explicit method/task/artifact metadata.
- Non-neural methods such as line intercept, Williams correction, grid search, and manual import can be registered without pretending to have a network architecture or weights artifact.

## Open Questions

- OQ-009 is resolved: `UNetPath` is current compatibility vocabulary for the crack-path detector selector, weights file, and local cache identity. Future architecture should introduce explicit method/task/artifact metadata fields instead of renaming the selector directly.

## Decision State

OQ-009 accepted for planning in [[decision-log#2026-05-14-model-names-bueckner-spelling-and-fixture-keys-use-explicit-naming-boundaries]].
The first method-side metadata slice is implemented in `crackpy/crack_detection/method_metadata.py` and deliberately starts from the method categories above rather than from a generic `ModelProvider`.
It reuses the shared `MethodSpec` shape already used by Williams-fit and CJP-fit provenance definitions.
Detection metadata can now also be exported as generic `MethodDefinition` records through `known_crack_detection_method_definitions()`.
Provider loading, cache/download policy, and device behavior remain in the legacy `get_model()` compatibility path until a later approved slice.

## Literature Signals For Naming

- Owens and Tippur, ["An Image Processing Technique to Identify Crack Tip Position and Automate Fracture Parameter Extraction Using DIC"](https://www.eng.auburn.edu/~htippur/papers/Owens-Tippur-EM2023.pdf), describe an image-processing method to identify crack-tip position from DIC displacement fields and emphasize that crack-tip position and propagation direction affect fracture-parameter extraction.
- Lopez-Crespo et al., ["Study of a crack at a fastener hole by digital image correlation"](https://research.manchester.ac.uk/en/publications/study-of-a-crack-at-a-fastener-hole-by-digital-image-correlation/), discuss using Sobel edge finding on DIC displacement fields to establish crack-tip location for SIF evaluation.
- Williams-series DIC work and recent regional-search work describe locating or localizing the crack tip by fitting displacement fields and minimizing residuals; see ["Crack tip localization method based on Williams series and digital image correlation method"](https://rockmech.whrsm.ac.cn/EN/10.3724/1000-6915.jrme.2025.0075).
- CrackPy-related symbolic-regression work frames the mechanics-based step as crack-tip correction/refinement using Williams coefficients and correction formulas: ["A universal crack tip correction algorithm discovered by physical deep symbolic regression"](https://arxiv.org/abs/2403.10320).
- CrackPy-related neural-network work distinguishes crack-tip coordinate detection/regression from U-Net-style path segmentation: ["Explainable machine learning for precise fatigue crack tip detection"](https://www.nature.com/articles/s41598-022-13275-1).

Planning implication: C-006 should not equate "method" with "pretrained network". A provider seam is only one adapter under a broader crack-detection method taxonomy.
