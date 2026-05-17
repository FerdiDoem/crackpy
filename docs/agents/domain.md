# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Layout

This is a single-context repo. CrackPy uses `docs/architecture-wiki/` as the shared working memory for domain vocabulary, architecture mapping, unresolved questions, lightweight decisions, and future refactor planning.

There is no `docs/adr/` directory in the current planning phase. Use `docs/architecture-wiki/decision-log.md` for accepted or rejected planning decisions until ADRs are explicitly introduced.

## Before Exploring

Read `AGENTS.md` first, then start with:

- `docs/architecture-wiki/README.md`
- `docs/architecture-wiki/glossary.md`
- `docs/architecture-wiki/system-map.md`
- `docs/architecture-wiki/coupling-map.md`
- `docs/architecture-wiki/open-questions.md`
- `docs/architecture-wiki/decision-log.md`
- `docs/architecture-wiki/refactor-notes.md`
- `docs/architecture-wiki/refactor-roadmap.md`

For implementation reality, use the observed-system notes under `docs/architecture-wiki/`. For future architecture, use `refactor-notes.md`, `refactor-roadmap.md`, and the files under `docs/architecture-wiki/refactor-candidates/`.

## Vocabulary Discipline

Use `docs/architecture-wiki/glossary.md` for project vocabulary. Do not replace stable terms with synonyms unless the user is explicitly discussing a naming change.

Keep these layers separate:

- observed reality: how the current code works;
- shared language: glossary terms and terminology decisions;
- future architecture: proposals, roadmap items, candidate notes, and approval gates.

## Decision Conflicts

If an output contradicts `docs/architecture-wiki/decision-log.md` or the planning rules in `AGENTS.md`, surface the conflict explicitly instead of silently overriding it.
