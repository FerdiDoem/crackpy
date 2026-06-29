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

- Status: accepted for planning; implementation legacy remains
- Date checked: 2026-05-14
- Source type: peer-reviewed fracture-mechanics literature and source-backed review
- Source reference: David Melching and Eric Breitbarth, "Advanced crack tip field characterization using conjugate work integrals", 2023, DOI `10.1016/j.ijfatigue.2023.107501`; X.-K. Chen, "New path independent integrals in linear elastic fracture mechanics", 1985, DOI `10.1016/0013-7944(85)90131-6`; H. F. Bueckner, "A novel principle for the computation of stress intensity factors", 1970, ZAMM 50(9), 529-546, stable record `https://jglobal.jst.go.jp/en/detail?JGLOBAL_ID=201602019999784704`.
- Terminology area: Bueckner-Chen integral, Williams coefficients, path-independent integrals
- Observed term: `buckner_*`, `integrate_buckner_chen()`
- Current CrackPy/wiki term: Bueckner-Chen integral
- Variant or conflict: Source-backed spelling is `Bueckner`; `buckner` is implementation legacy rather than a literature variant.
- Context summary: Melching and Breitbarth describe the Bueckner-Chen integral method as Chen's path-independent use of Bueckner's conjugate work integral to determine Williams coefficients, including SIFs and T-stress. Chen's 1985 paper provides the path-independent integral basis for eigenfunction-expansion coefficients. The implementation spelling `buckner` drops the `e` from Bueckner.
- Units or coordinate convention: Not a unit issue. Applies to crack-tip local fields and Williams coefficient recovery.
- Risk level: medium
- Affected wiki pages: [[glossary#Bueckner-Chen integral]], [[terminology-report#Fracture Result Names]], [[open-questions#Question Index]]
- Affected code or outputs: `LineIntegral.integrate_buckner_chen()`, related `buckner_*` identifiers, `Bueckner_Chen_integral` result tag
- Linked question: OQ-012, resolved
- Linked decision: [[decision-log#2026-05-14-model-names-bueckner-spelling-and-fixture-keys-use-explicit-naming-boundaries]]
- Recommended action: Keep `Bueckner-Chen` as canonical documentation and output-schema spelling. Treat `buckner_*` as legacy implementation vocabulary. Future refactor naming should use ASCII `bueckner_chen_*` identifiers, with compatibility aliases or deprecations for existing `buckner_*` names.
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

### 2026-05-14T18:32:55+02:00

- Checked range: `022c3beeeff58952294b29dad33c66c9e90f933c..8d24a550515754e90734360bea39bc526dd46eb5`; no uncommitted wiki hunks were present.
- Changed terminology focus: provenance planning vocabulary around `InputRecord`, `AnalysisRun`, `ResultRecord`, `ProvenanceRecord`, `MethodMetadata`, `AnalysisExecutionMetadata`, `MethodReference`, generic metadata statement bundles, compact RDF/JSON export, optional PROV-O-like export, JSON-LD, RO-Crate, CodeMeta, CFF, RDFLib, Pydantic JSON Schema, method revision, implementation fingerprint, `run_id`, `result_id`, hashes, and result schema version.
- Sources consulted:
  - W3C, "PROV-Overview", 2013 W3C Working Group Note, accessed 2026-05-14, `https://www.w3.org/TR/prov-overview/`; basis: provenance as information about entities, activities, and people involved in producing data, plus the PROV family split between data model, serializations, constraints, and access.
  - Timothy Lebo, Satya Sahoo, and Deborah McGuinness, "PROV-O: The PROV Ontology", 2013 W3C Recommendation, accessed 2026-05-14, `https://www.w3.org/TR/2013/REC-prov-o-20130430/`; basis: `prov:Entity`, `prov:Activity`, `prov:Agent`, `prov:Bundle`, `prov:Plan`, `used`, `wasGeneratedBy`, and related RDF provenance vocabulary.
  - W3C JSON-LD Working Group, "JSON-LD 1.1", 2020 W3C Recommendation, accessed 2026-05-14, `https://www.w3.org/TR/json-ld/`; basis: JSON-LD as a JSON-based linked-data serialization that can be used as JSON and as RDF.
  - RO-Crate contributors, "RO-Crate 1.1 Specification", accessed 2026-05-14, `https://www.researchobject.org/ro-crate/specification/1.1/introduction.html`; basis: RO-Crate as JSON-LD metadata for aggregating and describing research data and contextual entities such as software and equipment.
  - CodeMeta Project, "The CodeMeta JSON-LD Representation" and "Crosswalks", accessed 2026-05-14, `https://codemeta.github.io/jsonld/` and `https://codemeta.github.io/crosswalk/`; basis: CodeMeta as JSON-LD software metadata and crosswalk vocabulary between software metadata standards.
  - Citation File Format project, "Citation File Format (CFF)", accessed 2026-05-14, `https://citation-file-format.github.io/`; basis: `CITATION.cff` as human- and machine-readable citation metadata for software and datasets.
  - RDFLib project documentation, "Navigating Graphs", accessed 2026-05-14, `https://rdflib.readthedocs.io/en/7.1.2/intro_to_graphs.html`; basis: RDFLib graph handling around RDF triples and graph operations.
  - Pydantic documentation, "JSON Schema", accessed 2026-05-14, `https://pydantic.dev/docs/validation/latest/concepts/json_schema/`; basis: Pydantic support for generating and customizing JSON Schema from models.
- Result: no new source-backed terminology inconsistencies were found. The checked sources support the wiki's current separation between compact CrackPy-specific metadata records and optional standards-oriented PROV-O/JSON-LD export. `InputRecord`, `AnalysisRun`, `ResultRecord`, `ProvenanceRecord`, method revision, implementation fingerprint, and metadata statement bundle remain local planning vocabulary rather than literature-standard names. Existing FINDING-20260514-001 remains the only open source-backed conflict in the ledger.

### 2026-05-14T22:21:55+02:00

- Checked range: `8d24a550515754e90734360bea39bc526dd46eb5..e418d1a961784e04f7c1f0219d33855d0e7fe8eb`; no uncommitted wiki hunks were present.
- Changed terminology focus: crack-tip estimate/result dependencies, physical crack tip versus method-specific estimate, corrected crack-tip estimate, correction delta, source crack-tip estimate, line-intercept evaluation-region/grid/threshold vocabulary, `UNetPath` as compatibility alias, `model_id`, `model_role`, `architecture`, `weights_id`, method identity and traceability vocabulary, method-reference registry, package citation, versioned main result JSON, optional result/export formats, compact KG grouping and URI policy, detailed provenance artifact, and standing high-risk `Bueckner-Chen` / `buckner_*` spelling.
- Sources consulted:
  - Timothy Lebo, Satya Sahoo, and Deborah McGuinness, "PROV-O: The PROV Ontology", 2013 W3C Recommendation, accessed 2026-05-14, `https://www.w3.org/TR/prov-o/`; basis: standards vocabulary for entities, activities, agents, bundles, plans, and RDF provenance relations.
  - W3C JSON-LD Working Group, "JSON-LD 1.1", 2020 W3C Recommendation, accessed 2026-05-14, `https://www.w3.org/TR/json-ld/`; basis: JSON-based linked-data serialization and RDF compatibility.
  - RO-Crate contributors, "RO-Crate 1.1 Specification", accessed 2026-05-14, `https://www.researchobject.org/ro-crate/specification/1.1/introduction.html`; basis: JSON-LD research-object packaging for data resources and contextual entities such as software and equipment.
  - CodeMeta Project, "The CodeMeta JSON-LD Representation" and "Crosswalks", accessed 2026-05-14, `https://codemeta.github.io/jsonld/` and `https://codemeta.github.io/crosswalk/`; basis: JSON-LD software metadata and crosswalk vocabulary across software metadata standards.
  - Citation File Format project, "Citation File Format (CFF)", accessed 2026-05-14, `https://citation-file-format.github.io/`; basis: `CITATION.cff` as human- and machine-readable citation metadata for software and datasets.
  - JSON Schema project, "Specification", accessed 2026-05-14, `https://json-schema.org/specification`; basis: JSON Schema core and validation specifications for validating JSON result envelopes.
  - Apache Parquet project, "Apache Parquet", accessed 2026-05-14, `https://parquet.apache.org/`; basis: Parquet as column-oriented data-file format.
  - The HDF Group, "HDF5 Data Model and File Structure", accessed 2026-05-14, `https://docs.hdfgroup.org/documentation/hdf5/latest/_h5_d_m__u_g.html`; basis: HDF5 abstract data model, storage model, and file structure.
  - NSF Unidata, "NetCDF", accessed 2026-05-14, `https://www.unidata.ucar.edu/software/netcdf/`; basis: netCDF as software libraries and machine-independent formats for array-oriented scientific data.
  - Zarr project, "Zarr", accessed 2026-05-14, `https://zarr.dev/`; basis: Zarr as a versioned format for chunked, compressed, N-dimensional arrays.
  - David Melching, Florian Paysan, Tobias Strohmann, and Eric Breitbarth, "An iterative crack tip correction algorithm discovered by physical deep symbolic regression", 2024, DOI `10.1016/j.ijfatigue.2024.108432`; basis: DIC-based crack-tip detection/correction formulas using Williams coefficients.
  - Tobias Strohmann, Denis Starostin-Penner, Eric Breitbarth, and Guillermo Requena, "Automatic detection of fatigue crack paths using digital image correlation and convolutional neural networks", 2021, DOI `10.1111/ffe.13433`; basis: CrackPy-adjacent DIC displacement-field crack-path and crack-tip detection using convolutional neural networks.
  - Dassault Systemes, Abaqus documentation, "Contour integral evaluation", accessed 2026-05-14, `https://docs.software.vt.edu/abaqusv2024/English/SIMACAEANLRefMap/simaanl-c-contintegral.htm`; basis: FEM contour-integral vocabulary for J-integral, SIFs, T-stress, crack tips, and crack fronts.
- Result: no new source-backed terminology inconsistencies were found. The checked standards support treating `method_id`, `method_revision`, `implementation_fingerprint`, `dependency_scope`, `result_schema_version`, compact KG grouping, URI policy, and detailed provenance artifacts as local CrackPy planning vocabulary that can map outward to PROV-O, JSON-LD, RO-Crate, CodeMeta, CFF, and JSON Schema concepts without needing to adopt their names internally. Scientific and CrackPy-adjacent sources support keeping crack-tip correction and model-name terms as local result/provenance vocabulary unless they become formal method-reference registry entries. Existing FINDING-20260514-001 remains the only open source-backed conflict.

### 2026-05-15T01:20:22+02:00

- Checked range: `e418d1a961784e04f7c1f0219d33855d0e7fe8eb..cb6b3694b2650f084ca6c1dd33bb127c5173cdd0`; uncommitted wiki hunks were also present in `docs/architecture-wiki/README.md`, `docs/architecture-wiki/refactor-notes.md`, and new `docs/architecture-wiki/refactor-roadmap.md`.
- Changed terminology focus: canonical result graph bundle, `ResultQuantity`, symbol/description quantity vocabulary, legacy result-tag aliases, `SoftwareConfiguration` content-addressing, normalized configuration, result-affecting default, derived default, workflow composition setting, domain workflow runner, adapter policy, compatibility facade, detection resampling grid, detection window extent, detection input resolution, detection grid spacing, endpoint-inclusive detection mapping, `256` samples / `255` intervals, and roadmap sequencing across already accepted refactor candidates.
- Read-only subagent checks:
  - Diff extraction found that the committed range and uncommitted wiki hunks are architecture-planning terminology consolidation, with only the standing high-risk fracture/DIC terms remaining literature-sensitive.
  - Glossary comparison found no new internal contradiction; the changed vocabulary is either local CrackPy planning vocabulary or compatibility vocabulary already settled by decision-log entries.
- Sources consulted:
  - Timothy Lebo, Satya Sahoo, and Deborah McGuinness, "PROV-O: The PROV Ontology", 2013 W3C Recommendation, accessed 2026-05-15, `https://www.w3.org/TR/2013/REC-prov-o-20130430/`; basis: `prov:Entity`, `prov:Activity`, `prov:Agent`, `prov:Plan`, qualified usage, association, and role vocabulary for mapping CrackPy graph-shaped provenance without adopting PROV-O names internally.
  - W3C JSON-LD Working Group, "JSON-LD 1.1", 2020 W3C Recommendation, accessed 2026-05-15, `https://www.w3.org/TR/json-ld/`; basis: JSON-LD as JSON-based linked-data serialization and a stable recommendation for optional linked-data export.
  - JSON Schema project, "Specification", accessed 2026-05-15, `https://json-schema.org/specification`; basis: current JSON Schema 2020-12 split between Core and Validation for future result-schema validation vocabulary.
  - RO-Crate contributors, "RO-Crate 1.1 Specification", accessed 2026-05-15, `https://www.researchobject.org/ro-crate/specification/1.1/introduction.html`; basis: JSON-LD research-object packaging that can describe data resources and contextual entities such as people, organizations, software, equipment, and workflows.
  - NumPy project, "`numpy.linspace`", accessed 2026-05-15, `https://numpy.org/doc/stable/reference/generated/numpy.linspace.html`; basis: endpoint-inclusive sampling over a closed interval when `endpoint=True`, supporting the wiki's `num_samples - 1` interval explanation for the current detection grid.
  - Pydantic project, "JSON Schema", accessed 2026-05-15, `https://pydantic.dev/docs/validation/dev/concepts/json_schema/`; basis: Pydantic model-level and field-level JSON Schema generation/customization for future configuration/result schema builders.
  - Software Heritage, "SoftWare Heritage persistent IDentifiers (SWHIDs)", accessed 2026-05-15, `https://docs.softwareheritage.org/devel/swh-model/persistent-identifiers.html`; basis: intrinsic content-derived identifiers as a source-backed analogy for content-addressed software/configuration traceability.
- Result: no new source-backed terminology inconsistency was found. The checked standards support treating `Canonical result graph bundle`, `ResultQuantity`, `SoftwareConfiguration`, `Normalized configuration`, `Domain workflow runner`, `Adapter policy`, `Compatibility facade`, and detection-grid terms as local CrackPy planning vocabulary that is compatible with external standards but not dictated by them. The endpoint-inclusive `256` sample / `255` interval wording is supported by NumPy's `linspace` semantics. Existing FINDING-20260514-001 remains the only open source-backed conflict.

### 2026-06-05T19:37:29+02:00

- Checked range: `cb6b3694b2650f084ca6c1dd33bb127c5173cdd0..e9ac1fff8d5a427ac58a8ec6e948ccbb278d4829`; no uncommitted wiki hunks were present.
- Changed terminology focus: agent/issue-tracker documentation vocabulary, `refactor-roadmap` sequencing, compact KG/exporter policy vocabulary, `Descriptor field`, `LiteralField`, `Subject identity policy`, `URI minting policy`, descriptor-field policy, datatype normalization, unit normalization, source-specific ontology names from an external Turtle sample, Prefect/GraphInsertion/orchestrator boundary vocabulary, content-addressed IDs, and standing `Bueckner-Chen` / `buckner_*` compatibility cleanup.
- Read-only subagent checks:
  - Diff extraction found the changed corpus was documentation and architecture-planning vocabulary, with no uncommitted wiki/doc hunks and no new fracture-mechanics method names beyond the standing Bueckner spelling issue.
  - Glossary comparison found no new glossary, terminology-report, open-question, or decision-log contradiction. The new terms are framed as exporter/profile or future-planning vocabulary, not CrackPy core result containers.
- Sources consulted:
  - Richard Cyganiak, David Wood, and Markus Lanthaler, "RDF 1.1 Concepts and Abstract Syntax", 2014 W3C Recommendation, accessed 2026-06-05, `https://www.w3.org/TR/rdf11-concepts/`; basis: RDF graphs as subject-predicate-object triples, RDF terms, literals with datatypes, IRIs, namespaces as syntactic convenience, and RDF documents including Turtle and JSON-LD serializations.
  - Timothy Lebo, Satya Sahoo, and Deborah McGuinness, "PROV-O: The PROV Ontology", 2013 W3C Recommendation, accessed 2026-06-05, `https://www.w3.org/TR/prov-o/`; basis: provenance vocabulary around entities, activities, agents, usage, generation, and association for optional detailed provenance mapping.
  - W3C JSON-LD Working Group, "JSON-LD 1.1", 2020 W3C Recommendation, accessed 2026-06-05, `https://www.w3.org/TR/json-ld/`; basis: JSON-based linked-data serialization and RDF graph/dataset serialization support.
  - Leo Sauermann and Richard Cyganiak, "Cool URIs for the Semantic Web", 2008 W3C Interest Group Note, accessed 2026-06-05, `https://www.w3.org/TR/cooluris/`; basis: stable URI/IRI design as an external web/semantic-web concern, supporting a separate URI minting policy instead of hard-coding namespaces in core records.
  - RO-Crate contributors, "RO-Crate 1.1 Specification", accessed 2026-06-05, `https://www.researchobject.org/ro-crate/specification/1.1/introduction.html`; basis: JSON-LD research-object packaging remains an optional export/package profile rather than the canonical CrackPy scalar result model.
  - Apache Jena project, "The core RDF API", accessed 2026-06-05, `https://jena.apache.org/documentation/rdf/`; basis: Jena models, resources, statements, and triples as RDF API/export concepts rather than CrackPy computational-core containers.
  - Pydantic project, "JSON Schema", accessed 2026-06-05, `https://docs.pydantic.dev/usage/schema/`; basis: Pydantic can generate JSON Schema from models, supporting future schema-builder tooling without forcing Pydantic naming into domain terminology.
- Result: no new source-backed terminology inconsistency was found. The checked sources support the wiki boundary that `Descriptor field`, `LiteralField`, subject identity policy, URI minting policy, datatype/unit normalization, Jena/RDF objects, and JSON-LD/RO-Crate forms are exporter/profile concerns, not mandatory CrackPy core record types. Existing FINDING-20260514-001 remains the only open source-backed conflict. Future specification work should cite additional sources only if KG descriptor-resource conventions, FAIR Digital Object vocabulary, FORCE11 software-citation principles, PROV-N syntax, or source-specific Turtle ontology classes become formal CrackPy claims.

### 2026-06-05T22:39:07+02:00

- Checked range: `e9ac1fff8d5a427ac58a8ec6e948ccbb278d4829..68d58f92b2164662f4ddba44d6106735b56d4b6b`; uncommitted wiki hunks were also present in `docs/architecture-wiki/decision-log.md`, `docs/architecture-wiki/glossary.md`, and `docs/architecture-wiki/refactor-candidates/010-provenance-metadata-architecture.md`.
- Changed terminology focus: Williams-fit result/provenance implementation vocabulary, first-slice schema-version strings, canonical angle unit, `Williams_fit_results` aliases, `ResultQuantity`, compact KG statement bundle, graph visualization kit, SHA-256 canonical JSON hashes, provenance slice spec, `MethodResultSource`, `SourceDependency`, source quantity, source adapter, Williams coefficient-series qualifiers, `coefficient_series`, `term_order`, `statistic`, `path_index`, and standing `Bueckner-Chen` / `buckner_*` compatibility cleanup.
- Read-only subagent checks:
  - Diff extraction found the main source-check risk in the Williams notation split: literature-facing `A_n`/`B_n` notation versus current CrackPy lower-case `a_n`/`b_n`/`c_n` result symbols.
  - Glossary comparison found no new source-backed conflict, but flagged that `williams_coefficient` plus qualifiers must remain the canonical source-quantity shape while `Williams_fit_results.a_n`, `Williams_fit_results.b_n`, and `Williams_fit_results.c_n` remain compatibility aliases.
  - Literature scoping found no new hard conflict if canonical JSON, SHA-256, RDF/KG, and provenance terms stay separated by role rather than being treated as synonyms.
- Sources consulted:
  - M. L. Williams, "On the Stress Distribution at the Base of a Stationary Crack", 1957, Journal of Applied Mechanics 24, 109-114; basis: origin reference for Williams crack-tip series terminology.
  - David Melching and Eric Breitbarth, "Advanced crack tip field characterization using conjugate work integrals", 2023, DOI `10.1016/j.ijfatigue.2023.107501`; basis: Williams coefficient notation, higher-order terms, SIF/T-stress context, and Bueckner-Chen coefficient recovery.
  - R. K. L. Su and W. J. Feng, "Accurate determination of mode I and II leading coefficients of the Williams expansion by finite element analysis", 2005, DOI `10.1016/j.finel.2004.11.006`; basis: lower-case `a_1`/`b_1` coefficient notation for SIF-related leading terms and `a_2` relation to T-stress in one common formulation.
  - Bureau International des Poids et Mesures, "The International System of Units (SI)", 9th edition, updated 2026, DOI `10.59161/AUEZ1291`; and NIST, "Guide for the Use of the International System of Units (SI)", SP 811, DOI `10.6028/NIST.SP.811e2008`; basis: radian as coherent SI plane-angle unit and degree as accepted non-SI plane-angle unit, supporting `degree` as explicit canonical display/storage vocabulary over ambiguous legacy `grad`.
  - Anders Rundgren, Bret Jordan, and Samuel Erdtman, "JSON Canonicalization Scheme (JCS)", RFC 8785, 2020, DOI `10.17487/RFC8785`; basis: deterministic JSON canonicalization as the serialization step before hashing.
  - National Institute of Standards and Technology, "Secure Hash Standard (SHS)", FIPS 180-4, 2015, DOI `10.6028/NIST.FIPS.180-4`; basis: SHA-256 as a secure hash algorithm distinct from JSON canonicalization.
  - Richard Cyganiak, David Wood, and Markus Lanthaler, "RDF 1.1 Concepts and Abstract Syntax", 2014 W3C Recommendation, `https://www.w3.org/TR/rdf11-concepts/`; basis: RDF graph, triple, IRI, literal, datatype, namespace, and graph vocabulary as exporter/profile concepts.
  - Timothy Lebo, Satya Sahoo, and Deborah McGuinness, "PROV-O: The PROV Ontology", 2013 W3C Recommendation, `https://www.w3.org/TR/prov-o/`; basis: provenance vocabulary around entities, activities, agents, usage, generation, and association.
  - W3C JSON-LD Working Group, "JSON-LD 1.1", 2020 W3C Recommendation, `https://www.w3.org/TR/json-ld/`; basis: JSON-based linked-data serialization and RDF compatibility.
  - RO-Crate contributors, "RO-Crate 1.1 Specification", DOI `10.5281/zenodo.7867028`, `https://www.researchobject.org/ro-crate/specification/1.1/introduction.html`; basis: JSON-LD research-object packaging as an optional export/package profile.
  - Pydantic project, "JSON Schema", accessed 2026-06-05, `https://docs.pydantic.dev/latest/concepts/json_schema/`; basis: Pydantic model-to-JSON-Schema generation for future spec validation tooling.
- Result: no new source-backed terminology inconsistency was found. Existing FINDING-20260514-001 remains the only open conflict. The current edits are source-compatible if the regular implementation agent keeps lower-case Williams `a`/`b`/`c` values and `Williams_fit_results.*` names framed as CrackPy compatibility aliases, treats `A_n`/`B_n`/`C_n` as display or literature notation in specs, keeps `degree` explicit for canonical angle records while `grad` remains legacy output vocabulary, and keeps canonical JSON, SHA-256, RDF/KG, PROV-O, JSON-LD, and RO-Crate terms in exporter/provenance roles rather than core fracture-mechanics terminology.

### 2026-06-28T22:25:31+02:00

- Checked range: `68d58f92b2164662f4ddba44d6106735b56d4b6b..3e8ee668b7d7db2ccf0f85a440bf7c1ba22f498c`; no uncommitted wiki hunks were present.
- Changed terminology focus: CJP result/provenance slice vocabulary, `CJP Mixed-Mode Fit`, `CJP Mode-I Fit`, `CJP_results`, `CJP_modeI_results`, CJP coefficient symbols `A_r`, `B_r`, `B_i`, `A`, `B`, `C`, `E`, `F`, CJP derived quantities `K_F`, `K_R`, `K_S`, `K_II`, `T`, `T_x`, and `T_y`, singular coefficient units `MPa*mm^{1/2}` versus `MPa*m^{1/2}`, crack-detection `MethodSpec` metadata, `ParallelNets`, `UNetPath`, input identity mapping, `input_id`, `representative_input_id`, `sequence_index`, `stage`, `ResultEnvelope`, `MethodResultSource`, `SourceQuantity`, and reusable artifact-writer vocabulary.
- Read-only subagent checks:
  - Diff extraction confirmed the checked range and found no uncommitted wiki hunks; the source-sensitive changes centered on CJP, Williams carry-forward notation, crack-detection metadata, input mapping, and provenance/export vocabulary.
  - Glossary comparison found no new scientific-context contradiction, but flagged internal documentation drift: some CJP/provenance slice pages now describe implemented behavior while older planning notes still call CJP not decided; some glossary provenance terms still read as future/proposed despite partial implementation; older detection metadata wording around `model_id`, `model_role`, and `weights_id` needs a supersession note if the new `method_id`, `detection_task`, `network_architecture`, and `weights_artifact_id` vocabulary remains accepted.
  - Literature scoping found no new hard conflict if CJP coefficient/output names remain method-specific CrackPy result vocabulary and units are explicit; the standing `Bueckner-Chen` versus `buckner_*` issue remains the only source-backed inconsistency.
- Sources consulted:
  - C. J. Christopher, M. N. James, E. A. Patterson, and K. F. Tee, "Towards a new model of crack tip stress fields", 2007/2008, DOI `10.1007/s10704-008-9209-3`; basis: CJP model name and crack-tip stress-field context.
  - C. J. Christopher, M. N. James, E. A. Patterson, and K. F. Tee, "Extension of the CJP model to mixed mode I and mode II", 2013, DOI `10.3221/IGF-ESIS.25.23`; basis: mixed-mode CJP extension terminology and the split from Mode-I CJP modeling.
  - B. Yang, S. Mall, and R. Ravi-Chandar, "A new algorithm for optimized fitting of the CJP model to experimental data", 2021, DOI `10.1016/j.tafmec.2021.102950`; basis: optimized CJP fitting terminology and CJP parameter/output context.
  - M. L. Williams, "On the Stress Distribution at the Base of a Stationary Crack", 1957, DOI `10.1115/1.4011454`; basis: Williams crack-tip expansion terminology used by the carried-forward Williams coefficient notes.
  - David Melching and Eric Breitbarth, "Advanced crack tip field characterization using conjugate work integrals", 2023, DOI `10.1016/j.ijfatigue.2023.107501`; basis: Williams coefficient notation, higher-order terms, SIF/T-stress context, and Bueckner-Chen coefficient recovery.
  - Julien Rethore, Anthony Gravouil, Fabrice Morestin, and Alain Combescure, "Estimation of mixed-mode stress intensity factors using digital image correlation and an interaction integral", 2005, DOI `10.1007/s10704-004-8141-4`; basis: DIC displacement-field interaction-integral terminology for mixed-mode SIFs.
  - J. R. Rice, "A Path Independent Integral and the Approximate Analysis of Strain Concentration by Notches and Cracks", 1968, DOI `10.1115/1.3601206`; basis: J-integral terminology.
  - Dassault Systemes, Abaqus 2024 documentation, "Contour integral evaluation", accessed 2026-06-28, `https://docs.software.vt.edu/abaqusv2024/English/SIMACAEANLRefMap/simaanl-c-contintegral.htm`; basis: FEM contour-integral vocabulary for J-integral, SIFs, T-stress, crack tips, and crack fronts.
  - International Digital Image Correlation Society, "A Good Practices Guide for Digital Image Correlation", accessed 2026-06-28, `https://digitalimagecorrelation.org/`; basis: DIC subset/facet/DIC-point and displacement vocabulary.
- Result: no new source-backed terminology inconsistency was found. Existing FINDING-20260514-001 remains the only open conflict. The current CJP slice is source-compatible if `CJP Mixed-Mode Fit` and `CJP Mode-I Fit` stay separate CrackPy method identities, CJP coefficient symbols and `K_*`/`T_*` outputs stay explicitly method-specific result quantities, singular coefficient unit conversion is kept visible, and `CJP_results` / `CJP_modeI_results` remain legacy alias scopes rather than literature names.
- Follow-up for the regular architecture agent: align planning status notes for the now-implemented CJP/provenance slices, clarify which provenance glossary terms are partially implemented versus future generalization, add a supersession note for detection metadata names if the `MethodSpec`-based vocabulary is now canonical, and clean stale blocker/status entries in `refactor-notes.md`.

### 2026-06-29T19:53:41+02:00

- Checked range: `3e8ee668b7d7db2ccf0f85a440bf7c1ba22f498c..63196551fd54f8b1703bee1d875e8eded3156210`; no uncommitted architecture-wiki hunks were present. Unrelated dirty files outside the checked corpus were `.gitignore`, `skills-lock.json`, and `.agents/skills/lavish/`.
- Changed terminology focus: only the prior terminology-watch ledger entry changed in the bounded corpus. It carried forward CJP method identity and coefficient vocabulary, CJP unit conversion, crack-detection `MethodSpec` metadata, input identity mapping, provenance/export vocabulary, DIC/FEM nodemap wording, and standing high-risk fracture-mechanics terms.
- Read-only subagent checks:
  - Diff extraction found that the only changed architecture-wiki file was this ledger and that the changed hunk added the previous watch run plus automation-state marker.
  - Glossary comparison found no new source-backed conflict. It preserved existing follow-up gaps around ASCII `Rethore` versus the diacritic source spelling, minimal HOST/HORT explanation, interaction-integral alias boundaries, CJP/provenance planning-status drift, and detection metadata supersession notes.
  - Literature scoping found no new hard conflict. The accented source spelling of `Rethore` is a diacritic/ASCII variant rather than a scientific conflict; `nodemap` and `FEM nodemap` remain CrackPy or exporter compatibility vocabulary unless a stronger official source defines them more broadly.
- Sources consulted:
  - H. F. Bueckner, "A novel principle for the computation of stress intensity factors", 1970, ZAMM 50(9), 529-546, stable record `https://jglobal.jst.go.jp/en/detail?JGLOBAL_ID=201602019999784704`; basis: canonical `Bueckner` spelling.
  - Y. Z. Chen, "New path independent integrals in linear elastic fracture mechanics", 1985, DOI `10.1016/0013-7944(85)90131-6`; basis: path-independent integral context for Bueckner-Chen coefficient recovery.
  - David Melching and Eric Breitbarth, "Advanced crack tip field characterization using conjugate work integrals", 2023, DOI `10.1016/j.ijfatigue.2023.107501`; basis: Bueckner-Chen, Williams coefficients, SIFs, T-stress, HOST/HORT context.
  - Julien Rethore, Anthony Gravouil, Fabrice Morestin, and Alain Combescure, "Estimation of mixed-mode stress intensity factors using digital image correlation and an interaction integral", 2005, DOI `10.1007/s10704-004-8141-4`; basis: DIC displacement-field interaction-integral terminology and author diacritic variant.
  - C. J. Christopher, M. N. James, E. A. Patterson, and K. F. Tee, "Towards a new model of crack tip stress fields", 2007/2008, DOI `10.1007/s10704-008-9209-3`; basis: CJP model name and crack-tip stress-field context.
  - J. R. Rice, "A Path Independent Integral and the Approximate Analysis of Strain Concentration by Notches and Cracks", 1968, DOI `10.1115/1.3601206`; basis: J-integral terminology.
  - M. Stern, E. B. Becker, and R. S. Dunham, "A contour integral computation of mixed-mode stress intensity factors", 1976, DOI `10.1007/BF00032831`; basis: interaction-integral mixed-mode SIF terminology.
  - ZEISS, "Digital Image Correlation", accessed 2026-06-29, `https://www.zeiss.com/metrology/en/explore/topics/digital-image-correlation.html`; basis: DIC coordinates, displacement, strain, and source-system vocabulary.
  - DLR-WF, `aramis-data-exporter`, accessed 2026-06-29, `https://github.com/dlr-wf/aramis-data-exporter`; basis: ARAMIS/GOM-style exported mesh, displacement, strain, and metadata wording around nodemap-like ASCII data.
- Result: no new source-backed terminology inconsistency was found. Existing FINDING-20260514-001 remains the only open conflict. The regular architecture agent should keep the already flagged documentation follow-ups separate from this literature ledger: CJP/provenance implementation-status cleanup, detection metadata supersession wording, interaction-integral result alias boundaries, and optional ASCII/diacritic policy for author-name terms such as `Rethore`.

## Automation State

- Last checked commit: `63196551fd54f8b1703bee1d875e8eded3156210`
- Last checked range: `3e8ee668b7d7db2ccf0f85a440bf7c1ba22f498c..63196551fd54f8b1703bee1d875e8eded3156210`; no uncommitted architecture-wiki hunks were present
- Last run: `2026-06-29T19:53:41+02:00`
