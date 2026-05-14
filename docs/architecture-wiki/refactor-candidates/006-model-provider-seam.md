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

## Seams / Interfaces / Adapters

- Seam: model provision.
- Interface: model role/name, weights source, device behavior.
- Adapters: local weights, Zenodo cache/download, test double, future workflow-managed provider.

## Consequences

- Detection algorithms become less coupled to filesystem and network policy.
- Tests can avoid network and cache side effects.
- Current public model names must remain stable or be migrated deliberately.

## Open Questions

- OQ-009: Should `UNetPath` remain a model role/name while the implementation class is `UNet`?

## Decision State

Not decided. No implementation approved.
