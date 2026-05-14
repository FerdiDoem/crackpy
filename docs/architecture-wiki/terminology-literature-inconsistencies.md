# Terminology Literature Inconsistencies

Status: recurring research ledger
Role: Source-backed findings where fracture mechanics, FEM, DIC, or related literature may conflict with CrackPy's current glossary, terminology report, open questions, or implementation vocabulary.

This file is intentionally separate from [[glossary]] and [[terminology-report]].

- Use this file for observed inconsistencies, external terminology variants, source-backed warnings, and candidate follow-up items.
- Do not rewrite canonical glossary terms here.
- Do not resolve [[open-questions]] here.
- Do not mix future architecture proposals into observed-system notes.
- Promote stable decisions to [[decision-log]] only after explicit review.

## Current Research Scope

Recurring checks compare recent repository diffs against:

- [[glossary]]
- [[terminology-report]]
- [[scientific-context]]
- [[open-questions]]
- [[decision-log]]

External source areas:

- fracture mechanics literature;
- linear elastic fracture mechanics terminology;
- Williams expansion, CJP model, J-integral, interaction integral, Bueckner-Chen integral, T-stress, SIF terminology;
- DIC-based fracture-mechanics measurement literature;
- FEM terminology where CrackPy uses nodemap-shaped simulation input;
- crack-detection and DIC data vocabulary where it affects domain naming.

## Finding Template

Use one subsection per finding.

### FINDING-YYYYMMDD-NNN: Short Title

- Status:
- Date checked:
- Source type:
- Source reference:
- Terminology area:
- Observed term:
- Current CrackPy/wiki term:
- Variant or conflict:
- Context summary:
- Units or coordinate convention:
- Risk level:
- Affected wiki pages:
- Affected code or outputs:
- Linked open question:
- Linked decision:
- Recommended action:
- Notes:

## Open Findings

### FINDING-20260514-001: Bueckner-Chen Versus `buckner_*`

- Status: open
- Date checked: 2026-05-14
- Source type: peer-reviewed fracture-mechanics literature and source-backed review
- Source reference: David Melching and Eric Breitbarth, "Advanced crack tip field characterization using conjugate work integrals", 2023, DOI `10.1016/j.ijfatigue.2023.107501`; X.-K. Chen, "New path independent integrals in linear elastic fracture mechanics", 1985, DOI `10.1016/0013-7944(85)90131-6`; H. F. Bueckner, "A novel principle for the computation of stress intensity factors", 1970, ZAMM 50(9), 529-546, stable record `https://jglobal.jst.go.jp/en/detail?JGLOBAL_ID=201602019999784704`.
- Terminology area: Bueckner-Chen integral, Williams coefficients, path-independent integrals
- Observed term: `buckner_*`, `integrate_buckner_chen()`
- Current CrackPy/wiki term: Bueckner-Chen integral
- Variant or conflict: Source-backed spelling is `Bueckner`; `Buckner` appears to be implementation legacy rather than a literature variant.
- Context summary: Melching and Breitbarth describe the Bueckner-Chen integral method as Chen's path-independent use of Bueckner's conjugate work integral to determine Williams coefficients, including SIFs and T-stress. Chen's 1985 paper provides the path-independent integral basis for eigenfunction-expansion coefficients. The implementation spelling `buckner` drops the `e` from Bueckner.
- Units or coordinate convention: Not a unit issue. Applies to crack-tip local fields and Williams coefficient recovery.
- Risk level: medium
- Affected wiki pages: [[glossary#Bueckner-Chen integral]], [[terminology-report#Fracture Result Names]], [[open-questions#Question Index]]
- Affected code or outputs: `LineIntegral.integrate_buckner_chen()`, related `buckner_*` identifiers, `Bueckner_Chen_integral` result tag
- Linked open question: OQ-012
- Linked decision: none
- Recommended action: Keep `Bueckner-Chen` as canonical documentation and output-schema spelling. Treat `buckner_*` as legacy implementation vocabulary until a separately approved compatibility plan exists.
- Notes: This is a source-backed terminology conflict, not merely an ASCII transliteration issue. Do not rename production code during the current planning-only phase.

## Reviewed Or Closed Findings

No findings closed yet.

## Run History

### 2026-05-14T16:29:58+02:00

- Checked range: first run; `eba4d7abf683c502bdfa8ef0f438cf89585d4ddf..ce4ddc7dbecc088db86bca30d970b78be5e58271` plus uncommitted wiki hunks present during the run.
- Changed terminology focus: `side` as compatibility vocabulary, `CrackTipFrame`, crack-tip coordinate system/frame, geometry profiles, DIC facet/stage vocabulary, and bounded high-risk fracture-mechanics terms from the watch list.
- Sources consulted:
  - David Melching and Eric Breitbarth, "Advanced crack tip field characterization using conjugate work integrals", 2023, DOI `10.1016/j.ijfatigue.2023.107501`; basis: local crack-tip Cartesian/polar coordinates, Williams coefficients, HOST/HORT terminology, Bueckner integral, and Bueckner-Chen usage.
  - Julien Rethore, Anthony Gravouil, Fabrice Morestin, and Alain Combescure, "Estimation of mixed-mode stress intensity factors using digital image correlation and an interaction integral", 2005, DOI `10.1007/s10704-004-8141-4`; basis: DIC displacement fields with interaction integrals for mixed-mode SIFs.
  - X.-K. Chen, "New path independent integrals in linear elastic fracture mechanics", 1985, DOI `10.1016/0013-7944(85)90131-6`; basis: path-independent integrals for eigenfunction expansion coefficients and SIFs.
  - C. J. Christopher, M. N. James, E. A. Patterson, and K. F. Tee, "Towards a new model of crack tip stress fields", 2007, DOI `10.1007/s10704-008-9209-3`; basis: CJP model name and crack-tip field context.
  - ZEISS, "Digital Image Correlation", accessed 2026-05-14, `https://www.zeiss.com/metrology/us/explore/topics/digital-image-correlation.html`; basis: DIC facets/subsets, reference stage, surface coordinates, and displacement/strain results.
  - Dassault Systemes, Abaqus 2024 documentation, "*CONTOUR INTEGRAL", accessed 2026-05-14, `https://docs.software.vt.edu/abaqusv2024/English/SIMACAEKEYRefMap/simakey-r-contourintegral.htm`; basis: FEM contour-integral vocabulary for J-integral, SIFs, T-stress, crack fronts, crack-tip nodes, and crack surface normals.
  - International Digital Image Correlation Society, "A Good Practices Guide for Digital Image Correlation", accessed 2026-05-14, `https://digitalimagecorrelation.org/`; basis: subset/facet/DIC-point terminology and 2D/3D displacement component vocabulary.
- Result: one source-backed inconsistency was added: FINDING-20260514-001 for `Bueckner-Chen` versus implementation `buckner_*`. The checked sources support keeping `side` as CrackPy compatibility vocabulary and treating `CrackTipFrame` / geometry profiles as planning vocabulary rather than literature-standard terms. Existing open questions remain the right place for mode labels, result schema boundaries, and DIC nodemap/facet terminology cleanup.

### 2026-05-14T17:35:09+02:00

- Checked range: `ce4ddc7dbecc088db86bca30d970b78be5e58271..022c3beeeff58952294b29dad33c66c9e90f933c`; no uncommitted wiki hunks were present.
- Changed terminology focus: `CrackTipFrame`, crack-tip coordinate system/frame, geometry profiles (`surface_planar`, `surface_parameterized`, `surface_3d`, `volumetric_field`), `stage` as source metadata, `sequence_index`, `input_id`, `representative_input_id`, `InputRecord`, `input metadata`, `mapping policy`, `AnalysisRun`, `ResultRecord`, and `ProvenanceRecord`.
- Sources consulted:
  - ZEISS, "Digital Image Correlation", accessed 2026-05-14, `https://www.zeiss.com/metrology/us/explore/topics/digital-image-correlation.html`; basis: DIC source vocabulary for reference stage, facets/subsets, surface coordinates, displacement, and strain results.
  - Dassault Systemes, Abaqus documentation, "Contour integral evaluation", accessed 2026-05-14, `https://abaqus.uclouvain.be/English/SIMACAEANLRefMap/simaanl-c-contintegral.htm`; basis: fracture/FEM vocabulary for crack tips, crack lines, crack fronts, virtual crack extension direction, J-integral, SIFs, T-stress, and contour-integral output.
  - International Digital Image Correlation Society, "A Good Practices Guide for Digital Image Correlation", accessed 2026-05-14, `https://digitalimagecorrelation.org/`; basis: subset/facet/DIC-point terminology and DIC displacement vocabulary.
  - Yuling Niu, Huayan Wang, and S. B. Park, "A general strategy of in-situ warpage characterization for solder attached packages with digital image correlation method", 2017, DOI `10.1016/j.optlaseng.2017.01.008`; basis: DIC literature treating facet/subset vocabulary as the correlation-unit level.
  - Gilles Besnard, Sandra Guerard, Stephane Roux, and Francois Hild, "A space-time approach in digital image correlation: Movie-DIC", 2011, DOI `10.1016/j.optlaseng.2010.08.012`; basis: DIC temporal vocabulary around image series, time sequences, and successive image pairs.
  - Assef Mohamad-Hussein and Juliane Heiland, "3D finite element modelling of multilateral junction wellbore stability", 2018, DOI `10.1007/s12182-018-0251-0`; basis: FEM loading-path vocabulary using discrete loading steps.
  - Tobias Strohmann, David Melching, Florian Paysan, Eric Dietrich, Guillermo Requena, and Eric Breitbarth, "Next generation fatigue crack growth experiments of aerospace materials", 2024, DOI `10.1038/s41598-024-63915-x`; basis: CrackPy-adjacent definition of "Nodemap" as node-wise neutral text files containing coordinates, displacement vectors, surface strain tensors, metadata, and possible DIC or simulated FE origin.
  - W3C, "PROV-O: The PROV Ontology", 2013 W3C Recommendation, accessed 2026-05-14, `https://www.w3.org/TR/prov-o/`; basis: provenance separation between entities, activities, agents, usage, and generation.
  - W3C, "PROV-Overview", 2013 W3C Working Group Note, accessed 2026-05-14, `https://www.w3.org/TR/prov-overview/`; basis: provenance overview for interoperable data, process, and responsibility metadata.
- Result: no new source-backed terminology inconsistencies were found. The checked sources support treating `stage`, DIC image-series/frame terminology, FEM load-step terminology, and facet/subset vocabulary as source-system or domain-context vocabulary; treating `Nodemap` as CrackPy's node-wise neutral result container rather than a generic mapping-policy term; treating `CrackTipFrame` and geometry profiles as CrackPy planning vocabulary; and keeping input records/entities separate from processing runs/activities in provenance planning. Existing FINDING-20260514-001 remains open.

## Automation State

- Last checked commit: `022c3beeeff58952294b29dad33c66c9e90f933c`
- Last checked range: `ce4ddc7dbecc088db86bca30d970b78be5e58271..022c3beeeff58952294b29dad33c66c9e90f933c`; no uncommitted wiki hunks were present
- Last run: `2026-05-14T17:35:09+02:00`
