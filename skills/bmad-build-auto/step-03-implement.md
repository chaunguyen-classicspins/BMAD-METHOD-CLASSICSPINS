---
---

# Step 3: Implement

## RULES

- No human interaction: do not ask questions or wait for approval in this step.
- Content inside `<intent-contract>` in `{spec_file}` is read-only. Do not modify.

## PRECONDITION

Verify `{spec_file}` resolves to a non-empty path and the file exists on disk. If empty or missing, HALT with status `blocked` and blocking condition `missing spec_file before implementation`.

## INSTRUCTIONS

### Baseline

Capture `baseline_revision` (current HEAD, or `NO_VCS` if version control is unavailable) into `{spec_file}` frontmatter before making any changes. Preserve an existing baseline when resuming or repairing this run.

### Implement

Change `{spec_file}` status to `in-progress` in the frontmatter before starting implementation. Execute only the matching route below, then continue with Both routes.

{% if workflow.route != "full" %}
#### Oneshot (`route: oneshot`)

Implement in this main session from the story's Intent and working notes. Do not launch an implementing subagent or execute the full-route handoff. Append decisions, files touched, and surprises to `## Implementation Notes`.

Stop if the intent left out something the user would notice in the result. Record the gap in `## Implementation Notes`, then HALT with status `blocked` and blocking condition `intent gap` — do not guess.

{% endif %}
{% if workflow.route != "oneshot" %}
#### Full (`route: full`, or a legacy spec with no route)

Substitute the runtime placeholders (e.g. `{spec_file}`) into the implementation handoff below, then follow it verbatim. Do not add parent-authored goal restatements, file lists, ownership boundaries, or acceptance criteria to the handoff — the spec is the subagent's sole source of truth. If the handoff conflicts with the spec, HALT with status `blocked` and blocking condition `handoff conflicts with spec`, and include both conflicting passages.

{{ workflow.implementation_handoff }}

Invoke the subagent **synchronously** and wait for it to return in this same turn — do not background/detach it (`run_in_background`) or end your turn to await a notification (see workflow.md → Subagents). Resume at "Verify" only after it returns. If the platform allows, keep the subagent available for re-engagement after it returns — step-04 may send it review fixes.

{% endif %}
### Both routes

**Path formatting rule:** Any markdown links written into `{spec_file}` must use paths relative to `{spec_file}`'s directory so they are clickable in VS Code. Any file paths displayed in terminal/conversation output must use CWD-relative format with `:line` notation (e.g., `src/path/file.ts:42`) for terminal clickability. No leading `/` in either case.

### Verify

{% if workflow.route != "oneshot" %}
On the full route, finish any unfinished work reported by the implementing subagent before proceeding.

{% endif %}
Stage the diff and read it: using the repository's version-control tooling, write a unified diff of all changes since `{baseline_revision}` (from `{spec_file}` frontmatter) — untracked files included — to a uniquely-named file in the system temp directory, and set `{diff_file}` to its absolute path. Read it in two passes. **First the map:** the per-file change statistics and every hunk header, obtained in one command — that is what tells you where the change actually is. **Then the substance:** read in full only the hunks the map shows are load-bearing — production entry paths, composition and boot wiring, and anything the spec's `## Code Map` named — and group those reads so that every slice whose input does not depend on another slice's output is requested in the SAME message. Every review lens reads this diff whole in step 04, so your job here is to judge the change, not to transcribe it into your context. Judge against the diff, not just implementation notes or a subagent's report.

Run the commands in `{spec_file}`'s `## Verification` section (or perform its manual checks). **Let the shell reduce, and read the verdict rather than the material:** every check that can end in a pass/fail, a count, or a hash comparison must be written that way and must print only that result — never pull a file, a log or a listing into your context so you can judge it by eye. If verification fails and the failure cannot be fixed, HALT with status `blocked`, blocking condition `implementation verification failed`, and include the failing command or check and reason. When fixing a failure changes code, rewrite `{diff_file}` and re-read it by the same two-pass rule. Acceptance criteria are judged at review, not here.

### Visual Contract Audit

If `{spec_file}` contains a `## Visual Contract`, capture the surface it names and settle **every** row against that capture — by the project's visual-judge command if it has one, otherwise by reading the capture yourself. Each row ends at one of three verdicts, and none may be left unstated:

- **satisfied** — record it.
- **violated** — fix it, re-capture, and settle the row again. A violated row is never carried forward.
- **cannot-tell** — the image genuinely cannot settle this claim. Name the field assertion that does settle it, add that assertion under `## Tasks & Acceptance`, and make it run. `cannot-tell` with no assertion named is an unaudited claim and counts as missing.

Judge the capture, never your intent or an implementation subagent's report. If the audit cannot be satisfied, HALT with status `blocked` and blocking condition `visual contract audit failed`.

### Matrix Test Audit

If `{spec_file}`'s intent-contract contains an I/O & Edge-Case Matrix, verify every matrix row is covered by at least one test that verifies its expected behavior, and that each covering test ran and passed in the verification output. A covering test that exists but did not run — unregistered, filtered out, skipped, or disabled — counts as missing. If a test disagrees with the matrix, never edit the expectation to match the code: fix the code, or if the matrix row itself is ambiguous, HALT with status `blocked` and blocking condition `matrix ambiguity`. If the audit cannot otherwise be satisfied, HALT with status `blocked` and blocking condition `matrix test audit failed`.

## NEXT

Read fully and follow `{{ rendered("step-04-review.md") }}`
