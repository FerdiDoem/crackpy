# Open Questions

Status: planning question index
Role: Track unresolved terminology and architecture questions with stable IDs. These questions are not decisions; resolved items should be summarized in [[decision-log]].

## Question Index

| ID | Question | Status | Related notes | Blocks |
| --- | --- | --- | --- | --- |
| OQ-001 | Should `side` remain the public term, or should future architecture split specimen side, nominal crack-growth direction, and algorithmic mirroring? | resolved | [[glossary#Side]], [[terminology-report#Side And Orientation]], [[refactor-candidates/005-side-orientation-module]], [[decision-log#2026-05-14-side-is-not-a-sustainable-internal-crack-orientation-model]] | C-002, C-005 |
| OQ-002 | Should `stage` remain public vocabulary, or become source-specific metadata behind a more general sequence index? | resolved | [[glossary#Stage]], [[glossary#Sequence index]], [[terminology-report#Stage And Sequence Index]], [[refactor-candidates/009-sequence-index-vocabulary]], [[decision-log#2026-05-14-stage-is-source-metadata-sequence-index-is-internal-ordering]] | C-002, C-009 |
| OQ-003 | Which meanings currently bundled into `side` must become separate vocabulary? | resolved | [[terminology-report#Ambiguous Or Overloaded Terms]], [[refactor-candidates/005-side-orientation-module]], [[decision-log#2026-05-14-side-is-not-a-sustainable-internal-crack-orientation-model]] | C-005 |
| OQ-004 | Should line-intercept `window_size` be renamed conceptually to `threshold_run_length`? | open | [[glossary#Threshold window]], [[terminology-report#Window, Size, And Offset]] | Terminology cleanup |
| OQ-005 | Should result files receive an explicit schema or format version? | open | [[results-io-workflows]], [[terminology-report#Fracture Result Names]], [[refactor-candidates/008-result-tag-schema]] | C-001, C-008 |
| OQ-006 | Which result names are public schema and which are legacy implementation names? | open | [[glossary#Result tag]], [[results-io-workflows]], [[terminology-report#Fracture Result Names]] | C-001, C-008 |
| OQ-007 | Should crack-tip correction return values consistently mean relative shifts or absolute corrected crack-tip coordinates? | open | [[crack-detection]], [[terminology-report#Unresolved Terminology Questions]], [[refactor-candidates/003-self-contained-williams-fit-interface]] | C-003 |
| OQ-008 | Which pipeline side effects are user-facing behavior and which are adapter policy? | open | [[crack-detection]], [[fracture-analysis]], [[results-io-workflows]], [[refactor-candidates/004-separate-orchestration-from-adapters]] | C-004 |
| OQ-009 | Should `UNetPath` remain a model role/name while the implementation class is `UNet`? | open | [[glossary#UNetPath]], [[terminology-report#Models And Deep Learning]], [[refactor-candidates/006-model-provider-seam]] | C-006 |
| OQ-010 | Which current option defaults are public behavior and which are incidental implementation defaults? | open | [[fracture-analysis]], [[coupling-map]], [[refactor-candidates/007-defaults-and-options-cleanup]] | C-007 |
| OQ-011 | Should public result naming standardize on Roman mode labels or numeric suffixes? | open | [[terminology-report#Fracture Result Names]], [[results-io-workflows]] | Result schema planning |
| OQ-012 | Should `Bueckner-Chen` remain the canonical spelling everywhere, with `buckner_*` treated as implementation legacy? | open | [[glossary#Bueckner-Chen integral]], [[terminology-report#Fracture Result Names]] | Terminology cleanup |
| OQ-013 | Should the 256-sample / 255-interval pixel-to-millimeter convention be named explicitly? | open | [[glossary#Detection window]], [[crack-detection]], [[terminology-report#Unresolved Terminology Questions]] | Detection terminology |
| OQ-014 | Are fixture names such as `Dummy2`, `EBr10`, and `Aramis_in_line` supported workflow vocabulary or legacy test data names? | open | [[glossary#Dummy2 / EBr10 / Aramis_in_line]], [[terminology-report#Unresolved Terminology Questions]] | Workflow terminology |
| OQ-015 | Which provenance metadata must be preserved across input loading, detection, fracture analysis, text/JSON output, CSV flattening, and plots? | resolved | [[glossary#Provenance metadata]], [[results-io-workflows]], [[refactor-candidates/010-provenance-metadata-architecture]], [[decision-log#2026-05-14-provenance-uses-a-minimal-traceability-chain]] | C-001, C-002, C-008, C-010 |
| OQ-016 | How should CrackPy define a stable method identity and method-level revision? | resolved | [[glossary#Method ID]], [[glossary#Method revision]], [[refactor-candidates/010-provenance-metadata-architecture]], [[decision-log#2026-05-14-method-id-is-stable-provenance-vocabulary]] | C-003, C-010 |
| OQ-017 | Should method implementation traceability be computed automatically, declared manually, generated at build time, or handled as a hybrid? | resolved | [[glossary#Method ID]], [[glossary#Method revision]], [[glossary#Implementation fingerprint]], [[glossary#Dependency scope]], [[refactor-candidates/010-provenance-metadata-architecture]], [[decision-log#2026-05-14-method-revision-is-manual-and-implementation-fingerprint-is-build-validated]] | C-010 |
| OQ-018 | Should method references live in Python metadata, YAML/JSON, BibTeX, or a hybrid registry? | resolved | [[glossary#Method reference]], [[glossary#Method reference registry]], [[scientific-context]], [[refactor-candidates/010-provenance-metadata-architecture]], [[decision-log#2026-05-14-method-references-use-a-hybrid-registry]] | C-010 |
| OQ-019 | Which metadata belongs in the compact knowledge-graph export and which belongs only in an optional detailed provenance artifact? | open | [[glossary#Compact knowledge-graph export]], [[glossary#Detailed provenance artifact]], [[refactor-candidates/010-provenance-metadata-architecture]] | C-010 |
| OQ-020 | What is the minimal internal `CrackTipFrame` model needed to support arbitrary 2D cracks, multiple crack tips, tilted cracks, top-to-bottom cracks, and future 3D crack fronts? | resolved | [[glossary#CrackTipFrame]], [[glossary#Geometry profile]], [[refactor-candidates/005-side-orientation-module]], [[decision-log#2026-05-14-cracktipframe-is-the-planning-target-for-internal-crack-tip-orientation]] | C-005 |

## Rules

- Add new questions here instead of scattering unresolved questions across subsystem notes.
- Keep question IDs stable even if wording is refined.
- Link questions from refactor candidates when a question blocks a decision.
- When a question is resolved, keep the row and change status to `resolved`; record the decision in [[decision-log]].
