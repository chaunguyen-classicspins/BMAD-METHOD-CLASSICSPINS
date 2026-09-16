{% if workflow.route != "oneshot" %}
---
---

# Step 3: Implement

## RULES

- No push. No remote ops.
- Sequential execution only.
- Content inside `<frozen-after-approval>` in `{spec_file}` is read-only. Do not modify.

## PRECONDITION

Verify `{spec_file}` resolves to a non-empty path and the file exists on disk. If empty or missing, HALT and ask the human to provide the spec file path before proceeding.

## INSTRUCTIONS

### Baseline

Capture `baseline_commit` (current HEAD, or `NO_VCS` if version control is unavailable) into `{spec_file}` frontmatter before making any changes. If the frontmatter already contains `baseline_commit` (resumed run), preserve the existing value — never overwrite it.

### Implement

Change `{spec_file}` status to `in-progress` in the frontmatter before starting implementation.

If `{story_key}` is not empty and `{{ config.implementation_artifacts }}/sprint-status.yaml` exists, read `{{ rendered("sync-sprint-status.md") }}` with `{target_status}` = `in-progress`.

Execute the implementation handoff below: substitute the runtime placeholders (e.g. `{spec_file}`) into it, then follow it verbatim.

{{ workflow.implementation_handoff }}

Do not add goal restatements, file lists, ownership boundaries, investigation detail, acceptance criteria, or CLAUDE.md/house-style rules to the dispatch — the spec is the subagent's sole source of truth, and that material already lives in it (investigation findings in its Code Map, the rest in the spec body). One line of sanctioned hedging belongs in the spec at planning time, not in the dispatch. If no subagents are available, implement directly from the spec. If the platform allows, keep the subagent available for re-engagement after it returns — step-04 may send it review fixes.

The handoff directs the subagent to load the spec's `context:` files itself, so never pre-load and paste those files into the dispatch. Only when you implement directly (no subagent available) do you load a non-empty `context:` list yourself before starting.

**Path formatting rule:** Any markdown links written into `{spec_file}` must use paths relative to `{spec_file}`'s directory so they are clickable in VS Code. No leading `/`. Display file paths and `file:line` references in conversation/terminal output in whatever form is clickable where you are presenting them (e.g. code citation in chat, CWD-relative path with no leading `/` in terminal). If unsure, use CWD-relative path.

### Stage the Diff

Stage the diff and read it first: using the repository's version-control tooling, write a unified diff of all changes since `{baseline_commit}` (from `{spec_file}` frontmatter) — untracked files included — to a uniquely-named file in the system temp directory, and set `{diff_file}` to its absolute path. Read it in two passes. **First the map:** the per-file change statistics and every hunk header, obtained in one command — that is what tells you where the change actually is. **Then the substance:** read in full only the hunks the map shows are load-bearing — production entry paths, composition and boot wiring, and anything the spec's `## Code Map` named — and group those reads so that every slice whose input does not depend on another slice's output is requested in the SAME message. Every review lens reads this diff whole in step 04, so your job here is to judge the change, not to transcribe it into your context. Judge against the diff, not just the implementation subagent's report.

If the implementer reported anything unfinished, finish it before proceeding — and when that changes code, rewrite `{diff_file}` and re-read it by the same two-pass rule. **Let the shell reduce, and read the verdict rather than the material:** for any verification you re-run here, every check that can end in a pass/fail, a count, or a hash comparison must be written that way and must print only that result — never pull a file, a log or a listing into your context so you can judge it by eye. Acceptance criteria are judged at review, not here.

### Visual Contract Audit

If `{spec_file}` contains a `## Visual Contract`, capture the surface it names and settle **every** row against that capture — by the project's visual-judge command if it has one, otherwise by reading the capture yourself. Each row ends at one of three verdicts, and none may be left unstated:

- **satisfied** — record it.
- **violated** — fix it, re-capture, and settle the row again. A violated row is never carried forward.
- **cannot-tell** — the image genuinely cannot settle this claim. Name the field assertion that does settle it, add that assertion under `## Tasks & Acceptance`, and make it run. `cannot-tell` with no assertion named is an unaudited claim and counts as missing.

Judge the capture, never your intent or an implementation subagent's report. If the audit cannot be satisfied, HALT with status `blocked` and blocking condition `visual contract audit failed`.

### Matrix Test Audit

If `{spec_file}`'s `<frozen-after-approval>` block contains an I/O & Edge-Case Matrix, verify every matrix row is covered by at least one test that verifies its expected behavior, and that each covering test ran and passed in the verification output. A covering test that exists but did not run — unregistered, filtered out, skipped, or disabled — counts as missing. If a test disagrees with the matrix, never edit the expectation to match the code: fix the code, or if the matrix row itself is ambiguous, HALT and ask the human. Fix any other audit failure before proceeding.

## NEXT

Read fully and follow `{{ rendered("step-04-review.md") }}`
{% endif %}
