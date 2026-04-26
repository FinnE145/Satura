## Overview
This repository contains a grid-based, turn-based competitive programming game where agents execute scripts to move, paint territory, and outmaneuver an opponent under strict resource constraints.

## How to Work in This Repo
- Code is written primarily in Python.
- You will typically be asked to implement or modify individual features, modules, or files.
- Favor clear, correct implementations over unnecessary abstraction.
- Do not invent mechanics — follow the spec exactly (specs can be found in /docs)

## Frontend
When working on any HTML, CSS, or UI:
- Always read and follow `docs/style_guide.md` before making changes.
- Before writing any new CSS, check `docs/css_classes.md` to see if an existing class already applies.
- Any new CSS class that could plausibly be reused elsewhere on the site must be written generically (not scoped to a single page or component).
- Update `docs/css_classes.md` whenever a class is added, changed, or removed.
- NEVER use inline styles to get around this rule. Do it right the first time.

## Expectations
- Follow all rules and constraints from the specs precisely.
- Do not assume behavior not explicitly defined.
- Keep implementations consistent with existing patterns in the repo.

## When Unsure
- Ask questions (using the built-in question tool if available) instead of guessing.
- Clarify ambiguities, edge cases, or missing details before implementing.
- It is better to pause and confirm than to proceed with incorrect assumptions.
- Ask me questions first; only read docs/game_guide.md or docs/language_spec.md if broader clarification is needed (they are large and token-expensive).

## Problem-Solving Limits
- If you have attempted or reasoned through a problem more than twice without landing on a clean solution, stop. Explain what the constraint is and ask for direction.
- Do not use hacky workarounds (excessive specificity, arbitrary overrides, layered fixes) to force something to work. If a clean solution isn't emerging, explain why and ask.
- The signal to stop is when you are layering fixes on top of fixes, or thinking in circles. Surface the problem instead of digging deeper.

## Graphify
This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, or **searching the codebase for files, functions, or other structures** read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- Navigate to graphify-out/wiki/index.md before reading any files (you may fallback to normal tools only if it does not exist)
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)

## End of Implementation
When I have completed all testing and say that a session is done, "looks good", or "finish up":
- Commit logically, and put separate features/fixes in their own commits (there may be leftover changes from past sessions).
- On average, each session will be 1-2 commits, but it depends on how much you were asked to do.
- If the session began with/included working on tasks from the Google Tasks list, each 'Quick Fix'-level task would roughly be one commit.
- If the changes made correlate to a Google Task (or the satura-tasks skill was used), you can take this instruction to "finish up and commit" to also mark the corresponding task as complete. This only applies to tasks that were explicitly being completed in that session.
- If it appears there are other tasks that were inadvertently completed by the session, suggest them but do not edit them automatically.
- Update graphify as mentioned above