# Refactor Notes

Status: future architecture index, not observed behavior
Role: Navigate proposed future architecture candidates. Detailed candidate notes live in [[refactor-candidates/index]]; unresolved questions live in [[open-questions]]; accepted or rejected planning decisions live in [[decision-log]].

These notes intentionally separate proposed future architecture from current system reality. No refactoring was performed in this architecture mapping phase.

## Candidate Index

| ID | Candidate | Status | Primary observed evidence | Blocking questions | Decision state |
| --- | --- | --- | --- | --- | --- |
| C-001 | [[refactor-candidates/001-explicit-analysis-result]] | proposed | [[fracture-analysis]], [[results-io-workflows]], [[coupling-map]] | None | Canonical result graph boundary accepted; implementation not approved |
| C-002 | [[refactor-candidates/002-input-loading-seam]] | proposed | [[data-model-input]], [[system-map]], [[coupling-map]] | OQ-015 | Stage/input-record planning vocabulary accepted |
| C-003 | [[refactor-candidates/003-self-contained-williams-fit-interface]] | proposed | [[fracture-analysis]], [[crack-detection]], [[coupling-map]] | None | Correction result vocabulary accepted |
| C-004 | [[refactor-candidates/004-separate-orchestration-from-adapters]] | proposed | [[system-map]], [[fracture-analysis]], [[crack-detection]], [[results-io-workflows]] | None | Domain runner and adapter boundary accepted; implementation not approved |
| C-005 | [[refactor-candidates/005-side-orientation-module]] | proposed | [[glossary]], [[crack-detection]], [[terminology-report]], [[coupling-map]] | OQ-001, OQ-003 | Not decided |
| C-006 | [[refactor-candidates/006-model-provider-seam]] | proposed | [[crack-detection]], [[results-io-workflows]], [[coupling-map]] | None | Model naming boundary accepted; implementation not approved |
| C-007 | [[refactor-candidates/007-defaults-and-options-cleanup]] | proposed | [[fracture-analysis]], [[data-model-input]], [[coupling-map]] | OQ-010 | Not decided |
| C-008 | [[refactor-candidates/008-result-tag-schema]] | proposed | [[results-io-workflows]], [[terminology-report]], [[coupling-map]] | None | Canonical result graph boundary accepted; symbols plus descriptions accepted for scalar quantities |
| C-009 | [[refactor-candidates/009-sequence-index-vocabulary]] | proposed | [[glossary]], [[terminology-report]], [[crack-detection]], [[data-model-input]] | None | Planning vocabulary accepted |
| C-010 | [[refactor-candidates/010-provenance-metadata-architecture]] | proposed | [[data-model-input]], [[results-io-workflows]], [[coupling-map]], provided metadata statement-bundle datapoint JSON | None | Planning vocabulary accepted; implementation not approved |

## How To Use This Index

- Use candidate notes for architecture proposals only.
- Link candidate evidence back to observed notes rather than copying observed-system descriptions.
- Move open design questions into [[open-questions]] with stable `OQ-*` IDs.
- Record settled planning decisions in [[decision-log]].
- Do not create architecture decision records in this phase; ADRs are deferred until explicitly approved.
