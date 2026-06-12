---
name: grill-me
description: Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when user wants to stress-test a plan, get grilled on their design, or mentions "grill me".
---

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask the questions one at a time.

Enricht your questionaire with context. Use subagent for gathering context when asking questions from open-questions.md.

If a question can be answered by exploring the codebase, explore the codebase instead. Use subagents for exploring the codebase because otherwise your context window fills up too fast.

Add an extra thinking step on how many subagents you have to spawn. You might need more than one because the wiki has become significantly large. Use at least one per file.

When working on files, commit after a question is resolved. This is important for tracking diffs in the docs and help the human-in-the-loop to understand which docs have been updated and where.
