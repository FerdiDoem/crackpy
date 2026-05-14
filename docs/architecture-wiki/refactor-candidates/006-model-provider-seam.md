# Candidate 006: Model Provider Seam

Status: proposed
Role: Future architecture candidate for separating model construction and download/cache policy from detection algorithms.

## Observed Evidence

- [[crack-detection]] documents `get_model()`, supported model names, and download behavior.
- [[results-io-workflows]] documents scripts that use pretrained models.
- [[coupling-map]] records side effects such as directory creation and model downloads.

## Problem

Model loading combines model construction, local cache policy, network download, weight loading, and device behavior.

## Future Direction

Introduce a `ModelProvider` interface with adapters for local weights, Zenodo download/cache, test doubles, and future service/workflow providers.

Future model metadata should not rely on the current `model_name` string alone. It should split:

- stable `model_id`, preferably linked to the method, paper, or registered model family;
- `model_role`, such as `crack_path_detector`;
- `architecture`, such as `UNet`;
- `weights_id`, such as the current `UNetPath.pth`;
- aliases for compatibility selectors such as `UNetPath`.

## Seams / Interfaces / Adapters

- Seam: model provision.
- Interface: model role/name, weights source, device behavior.
- Adapters: local weights, Zenodo cache/download, test double, future workflow-managed provider.

## Consequences

- Detection algorithms become less coupled to filesystem and network policy.
- Tests can avoid network and cache side effects.
- Current public model names must remain stable or be migrated deliberately.
- `UNetPath` can remain readable as a compatibility alias while future provenance and orchestration use a more explicit model ID.

## Open Questions

- OQ-009 is resolved: `UNetPath` is current compatibility vocabulary for the crack-path detector selector, weights file, and local cache identity. Future architecture should introduce explicit model metadata fields instead of renaming the selector directly.

## Decision State

OQ-009 accepted for planning in [[decision-log#2026-05-14-model-names-bueckner-spelling-and-fixture-keys-use-explicit-naming-boundaries]]. No implementation approved.
