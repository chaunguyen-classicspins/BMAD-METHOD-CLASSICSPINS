# Step 2: Plan

## RULES

- No intermediate approvals.
- **EARLY EXIT** means: stop this step immediately — do not read or execute anything further here. Read and fully follow the target file instead. Return here ONLY if a later step explicitly says to loop back.

## INSTRUCTIONS

1. Draft resume check. If `{spec_file}` exists with `status: draft`, read it and capture the verbatim `<frozen-after-approval>...</frozen-after-approval>` block as `preserved_intent`. Otherwise `preserved_intent` is empty.
2. Investigate the codebase.

   **Write the question list first.** Before reading anything, list the questions the spec must answer. Any question you can settle yourself in two commands or fewer, settle it yourself — do not spend a subagent on it.

   **Read in batches, not in a trickle.** For what you read yourself, write the read plan — file path plus the exact range or pattern for each entry — then execute it in as few messages as the plan allows: every entry whose input does not depend on another entry's output goes in the SAME message. Take a new turn only when the next command's input is a value you do not have yet (a compile result, a test result, a path you must first discover). Locating and reading are one command, not two — prefer a single range-matching command over a search followed by a separate slice of the same file.

   **Isolate deep exploration in synchronous subagents** — launched all in ONE message, at most five, each running on the Sonnet model (pass the host's per-subagent model override; in Claude Code that is the Agent tool's `model: "sonnet"` parameter). Prefer the host's read-only exploration agent type for mapping and inventory work; use a general agent only when the question needs reasoning rather than reading. Every brief states, verbatim: the exact numbered questions, nothing open-ended; the output shape — `path:line` plus exact signatures and a one-line finding each, no code dumps and no file contents; and the budget — "Use at most 20 tool calls. When you reach it, report what you have and name what is still open. Do not keep going." Never launch a second wave for a question a first wave already covered, and never launch a subagent for something you have already found while waiting. Plan from the returned summaries.

   Keep only what the work needs: the specific files, symbols or lines, what to reuse, and what not to change. Write that into the Code Map. Do not retell the investigation when implementation starts — the spec already has it.

   Do not ask the human during investigation. When something is unclear, look in the repository, planning artifacts, or history first. Keep looking until you know, or until those sources have nothing more to say. Leave any remaining choice for the next step.
{% if workflow.route == "oneshot" %}
3. Read `{{ rendered("spec-template.md") }}` fully and write `{spec_file}`.
   Set `route: 'oneshot'`, `route_source: 'pinned'`, and `status: 'in-progress'`, resolving `date` to the current system date.
   If `preserved_intent` is non-empty, use it as the frozen block.
   **EARLY EXIT** → `{{ rendered("step-oneshot.md") }}`.
{% elif workflow.route == "full" %}
3. Set `route: 'full'` and `route_source: 'pinned'`, then continue.
{% else %}
3. {{ workflow.route_selection }}

   For oneshot: read `{{ rendered("spec-template.md") }}` fully and write `{spec_file}`.
   Set `route: 'oneshot'`, `route_source: 'auto'`, and `status: 'in-progress'`, resolving `date` to the current system date.
   If `preserved_intent` is non-empty, use it as the frozen block.
   **EARLY EXIT** → `{{ rendered("step-oneshot.md") }}`.

   For full, set `route: 'full'` and `route_source: 'auto'`, then continue.
{% endif %}
{% if workflow.route != "oneshot" %}
4. Read `{{ rendered("spec-template.md") }}` fully. Fill it out from the intent and investigation, resolving the template's `date` field to the current system date. Put the investigation into `## Code Map`: paths, symbols or lines, what to reuse, and what not to change. Implementation should work from the spec without being told the investigation again. If there are intent gaps, add a `## Open Questions` section with one entry per gap: the choice, the options, and what each option means. Never write an intent gap into the frozen block as an assumption. If `preserved_intent` is non-empty, replace the `<frozen-after-approval>` block with it before writing. Write the result to `{spec_file}`.

   **If this story renders a surface a person looks at,** fill `## Visual Contract`: name the surface, name the fixture that will be on screen and what it puts there, name what later work owns so its absence is not read as a defect, and write each claim as something settleable by **looking at one capture** — never a coordinate, a hex value, a scale factor or a z-order, which an image cannot settle and which belong in `## Tasks & Acceptance` as field assertions. Transcribe the claims from the design sources the intent names; do not invent them. If the story renders nothing, delete the section outright and say so rather than leaving it empty.
5. Self-review against READY FOR DEVELOPMENT standard. For anything important that's missing: if the repository can tell you, go look and fix the spec; if a human has to decide, add an `## Open Questions` entry. Do not invent the answer.
6. Resolve the gates before the checkpoint. Two things must be settled, in whatever order the conversation makes natural; combine them in one message when both apply.
   - **Token count** (see SCOPE STANDARD). If the spec exceeds 1600 tokens, show the count and give the user a choice:
     - **Split** — carve off secondary goals. Propose the split — name each secondary goal. For each deferred goal, append one new entry to `{{ config.implementation_artifacts }}/deferred-work.md` using the format below. Do not modify existing entries or look for duplicates. Rewrite the current spec to cover only the main goal — do not surgically carve sections out; regenerate the spec for the narrowed scope.
     - **Keep full spec** — accept the risks.
     ```markdown
     - source_spec: `{spec_file}`
       summary: <one sentence naming the deferred goal>
       evidence: <why this was split from the current spec>
     ```
   - **Open Questions.** Present every entry as a numbered question with its options and what each option means, and HALT for the human's answers. Write each answer into the `<frozen-after-approval>` block as a decision and delete the entry. An answer may expose a new intent gap — add it and ask again. When the last entry is gone, delete the section.

### CHECKPOINT 1

Only when Open Questions is empty.

Present summary. Display the spec file path in whatever form is clickable where you are presenting it (e.g. code citation in chat, CWD-relative path with no leading `/` in terminal). If unsure, use CWD-relative path.

If token count exceeded 1600 and the user chose to keep the full spec, include the token count and explain why it may be a problem.

After presenting the summary, display this note:

---

Before approving, you can open the spec file in an editor or ask me questions and tell me what to change. You can also use `bmad-advanced-elicitation` or `bmad-party-mode`, ideally in another session to avoid context bloat.

---

HALT and give the user a choice:

- **Approve and continue** — approve the spec and proceed to implementation in this session.
- **Approve and stop** — approve the spec, leave it `ready-for-dev`, and stop so a fresh `bmad-build` session can resume at implementation.
- **Review spec** — review the spec, use a subagent if available, and discuss the findings and revisions with the user until the user is ready to approve, then either stop or continue.

Before acting on approval, re-read `{spec_file}` from disk. If it is missing, HALT without recreating it, changing status, or proceeding. If it changed, acknowledge the external edits and continue with the updated version. Set status `ready-for-dev`; everything inside `<frozen-after-approval>` is then locked and only the human can change it.

## NEXT

Read fully and follow `{{ rendered("step-03-implement.md") }}`
{% endif %}
