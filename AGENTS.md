# Agent Working Memory

CrackPy uses `docs/exploration/` as the shared working memory for architectural planning and refactor work.

Current phase: architectural mapping and planning only. Do not perform real refactoring or restructuring until the general specifications are clearly defined and explicitly approved.

## Before Refactoring

Read these notes first:

- `docs/exploration/README.md` for the map of the knowledge base.
- `docs/exploration/system-map.md` for package-level flow.
- `docs/exploration/coupling-map.md` for current coupling and side effects.
- `docs/exploration/glossary.md` for shared domain vocabulary.
- `docs/exploration/refactor-notes.md` for future architecture candidates.

## Memory Discipline

Keep three layers separate:

- Observed reality: document how the code currently works.
- Shared language: update glossary terms when naming becomes clearer.
- Future architecture: keep proposed designs and refactor ideas in separate notes.

Do not mix proposed architecture into observed-system notes. If a design decision becomes stable, record it separately rather than rewriting history.

## Refactor Rule

Until the planning phase is complete, limit work to exploration notes, glossary updates, decision framing, and architecture proposals. When later changing architecture, preserve the current exploration notes as the baseline. Update them only when the code reality changes or when new facts are discovered.
