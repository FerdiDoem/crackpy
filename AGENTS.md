# Agent Guide

This file is the repo-level entrypoint for agents working in CrackPy. Codex reads `AGENTS.md` files before doing work, so keep durable project rules here.

Codex project configuration belongs in `.codex/config.toml`. Repo-local skills belong in `.agents/skills/`, which is the documented repository skill discovery path. Do not move skills under `.codex/skills/`; that is not a documented skill location. Shared issue-tracker, triage, and domain-doc configuration lives under `docs/agents/`.

## General Guidelines

*When making technical decisions, do not give much weight to development cost. Instead, prefer quality simplicity, robustness, scalability, and long term maintainability.
* When writing or substanitally editing long Markdown files, put ech full sentence on its own line. Preserve normal markdown structure, but avoid wrapping multiple sentences onto one physical line.
* When doing bug fixes, always start with reproducing the bug in an E2E setting as closely aligned with how an end user would experience as close as possible. This makes sure you find the real problem so your fix will actually solve it.
* When end-to-end testing a user-facing product, be picky about the UI/UX you see and be obsessed with pixel and experience perfection.
* If something is clearly looks or feels off, even if it is not directly related to what you are doing, try to get it fixed along the current task
* Apply the same highs tadnard to engineering excellence: lint, test failures, and test flakiness. If you see one, even if it is not cause by what your are working on right now, still get it fixed.

## Current Phase

CrackPy is in architectural mapping and planning. Do not perform real refactoring or restructuring until the general specifications are clearly defined and explicitly approved.

Allowed planning work includes:

- updating architecture-wiki notes with newly observed facts;
- clarifying glossary terms and unresolved terminology questions;
- framing future architecture candidates and decision options;
- documenting accepted or rejected planning decisions.

Keep proposed architecture separate from observed system behavior.

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

## Agent Skills

### Issue Tracker

Issues and PRDs are tracked as local markdown files under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Triage Labels

Triage uses the default five-label vocabulary. See `docs/agents/triage-labels.md`.

### Domain Docs

Single-context repo using `docs/architecture-wiki/` as the domain and architecture working memory. See `docs/agents/domain.md`.

### Local Skill Files

Repo-local skills are installed under `.agents/skills/`. Use them when the task matches their scope, especially for architecture review, diagnosis, TDD, issue generation, triage, PRD creation, and handoffs.

## Documentation Practice

- Prefer small, source-backed edits over broad rewrites.
- Preserve the current architecture wiki as the baseline for code reality.
- Update observed-system notes only when code reality changes or when new facts are discovered.
- Record stable decisions in `docs/architecture-wiki/decision-log.md` instead of silently folding them into older notes.
- Keep future architecture candidates in `docs/architecture-wiki/refactor-notes.md`, `docs/architecture-wiki/refactor-roadmap.md`, or `docs/architecture-wiki/refactor-candidates/`.

## Coding Practice

Coding changes are out of scope during the current planning phase unless the user explicitly approves implementation work.

When coding is approved:

- Preserve architectural intent close to the implementation.
- Add concise docstrings or inline comments where a design decision, dependency direction, import choice, validation rule, or naming choice would not be obvious from the code alone.
- Dataclasses that do not have field-level `Field(description=...)` metadata need class docstrings or nearby comments that explain what each field means and why it exists.
- Pydantic models should use `Field(description=...)` for every field unless the model has an explicit, documented reason not to.
- Keep comments decision-focused; do not narrate simple statements.
- When a code change reflects an architecture decision, update the relevant architecture-wiki note in the same pass.

## Subagent Practice

Use subagents to inspect the architecture wiki when the task touches architecture planning, terminology, refactor candidates, or documentation consolidation.

Prefer multiple narrow, read-only subagents over one broad scan when the work spans distinct areas such as observed-system notes, glossary/terminology, and refactor planning.

The parent agent owns synthesis and edits. Subagents should normally return findings only and should not mutate files unless explicitly assigned a bounded write scope.

Choose subagent models by task depth:

- Use smaller or faster models for bounded read-only scans, checklist audits, link checks, documentation audits, and summarization.
- Use medium reasoning for subsystem audits, bounded bug localization, and straightforward implementation.
- Use high reasoning for architecture tradeoffs, scientific-method interpretation, cross-module coupling analysis, or when cheaper subagents disagree.
- Reserve GPT-5.5-class models for ambiguous architecture synthesis, scientific reasoning, high-risk integration decisions, or cases where cheaper-model findings conflict.

For well-defined coding tasks with clear files, tests, acceptance criteria, and limited design ambiguity, Codex Spark-class workers are acceptable. Keep broader design, decomposition, final synthesis, and integration responsibility with the parent agent or a stronger model.

Subagents should not spawn further subagents by default. Allow nested subagents only for explicitly requested deep exploration, with a narrow read-only scope, a clear expected output, and no recursive delegation beyond that extra level.

## Repo Hygiene

- Check the worktree before editing and do not overwrite unrelated user changes.
- Use `rg` or `rg --files` for search when available.
- Keep edits scoped to the requested files and the relevant architecture notes.
- Prefer structured parsers and repo-local helpers over ad hoc text manipulation when changing code.
- Verify changes with the narrowest useful command before reporting completion.
