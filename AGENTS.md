# Agent Working Memory

CrackPy uses `docs/architecture-wiki/` as the shared working memory for architectural planning and refactor work.

Current phase: architectural mapping and planning only. Do not perform real refactoring or restructuring until the general specifications are clearly defined and explicitly approved.

## Before Refactoring

Read these notes first:

- `docs/architecture-wiki/README.md` for the map of the knowledge base.
- `docs/architecture-wiki/system-map.md` for package-level flow.
- `docs/architecture-wiki/coupling-map.md` for current coupling and side effects.
- `docs/architecture-wiki/glossary.md` for shared domain vocabulary.
- `docs/architecture-wiki/open-questions.md` for unresolved terminology and architecture questions.
- `docs/architecture-wiki/decision-log.md` for accepted or rejected planning decisions.
- `docs/architecture-wiki/refactor-notes.md` for the future architecture candidate index.

## Memory Discipline

Keep three layers separate:

- Observed reality: document how the code currently works.
- Shared language: update glossary terms when naming becomes clearer.
- Future architecture: keep proposed designs and refactor ideas in separate notes.

Do not mix proposed architecture into observed-system notes. If a design decision becomes stable, record it separately rather than rewriting history.

When proposing future containers, dataclasses, configuration objects, protocols, or complex functions/classes in architecture notes, document the fields or parameters at the point of introduction. Explain both what each field means and why it exists; names and type hints alone are not sufficient for planning documents.

## Subagent Discipline

Use subagents to inspect the architecture wiki when the task touches architecture planning, terminology, refactor candidates, or documentation consolidation. Prefer multiple narrow, read-only subagents over one broad scan when the work spans distinct areas such as observed-system notes, glossary/terminology, and refactor planning.

The parent agent owns synthesis and edits. Subagents should normally return findings only and should not mutate files unless explicitly assigned a bounded write scope.

Choose subagent models by task depth. Use smaller or faster models for bounded read-only scans, checklist audits, link checks, documentation audits, and summarization. Reserve GPT-5.5-class models for ambiguous architecture synthesis, scientific reasoning, high-risk integration decisions, or cases where cheaper-model findings conflict. For well-defined coding tasks with clear files, tests, acceptance criteria, and limited design ambiguity, Codex Spark-class workers are acceptable; keep broader design, decomposition, final synthesis, and integration responsibility with the parent agent or a stronger model.

Adjust reasoning effort dynamically as well as model. Use low reasoning for mechanical scans, link checks, inventory extraction, and simple summarization. Use medium reasoning for subsystem audits, bounded bug localization, and straightforward implementation. Use high reasoning for architecture tradeoffs, scientific-method interpretation, cross-module coupling analysis, or when cheaper subagents disagree. Avoid high reasoning on routine helpers unless the result will drive an important decision.

Subagents should not spawn further subagents by default. Allow nested subagents only for explicitly requested deep exploration, with a narrow read-only scope, a clear expected output, and no recursive delegation beyond that extra level.

## Refactor Rule

Until the planning phase is complete, limit work to architecture wiki notes, glossary updates, decision framing, and architecture proposals. When later changing architecture, preserve the current architecture wiki notes as the baseline. Update them only when the code reality changes or when new facts are discovered.

## Agent skills

### Issue tracker

Issues and PRDs are tracked as local markdown files under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Triage uses the default five-label vocabulary. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context repo using `docs/architecture-wiki/` as the domain and architecture working memory. See `docs/agents/domain.md`.
