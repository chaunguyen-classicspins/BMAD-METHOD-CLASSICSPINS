# Step 2: Plan

## RULES

- No human interaction: do not ask questions or wait for approval in this step.

## INSTRUCTIONS

1. Draft resume check. If `{spec_file}` exists with `status: draft`, read it and capture the verbatim `<intent-contract>...</intent-contract>` block as `preserved_intent_contract`. Otherwise `preserved_intent_contract` is empty.
2. Investigate codebase.

   **Write the question list first.** Before reading anything, list the questions the spec must answer. Any question you can settle yourself in two commands or fewer, settle it yourself — do not spend a subagent on it.

   **Read in batches, not in a trickle.** For what you read yourself, write the read plan — file path plus the exact range or pattern for each entry — then execute it in as few messages as the plan allows: every entry whose input does not depend on another entry's output goes in the SAME message. Take a new turn only when the next command's input is a value you do not have yet (a compile result, a test result, a path you must first discover). Locating and reading are one command, not two — prefer a single range-matching command over a search followed by a separate slice of the same file.

   **A chain is batching, but the weak form.** Joining reads with `&&` puts them in one turn, and that is already most of the win — but the chain has no per-item cap, so one fat `cat` is re-sent on every later turn for the rest of the session, and the first non-zero exit kills every entry behind it. When the project's agent contract names a batched-inspection tool with a per-item cap (`pf-exec` in a PrototypeFramework SKU), put the whole read plan through it in one call instead: each entry labelled, each output capped, a failing entry never aborting the others. The shape to aim for is the read plan in one or two calls — not three files joined by `&&`, and not one call per pair of files. Do not spend a turn checking whether it exists — run it; if the shell says command not found, that one failed call is your answer and you fall back to several reads in one message.

   **Isolate deep exploration in synchronous subagents** — launched all in ONE message, at most five, each running on the Sonnet model (pass the host's per-subagent model override; in Claude Code that is the Agent tool's `model: "sonnet"` parameter). Prefer the host's read-only exploration agent type for mapping and inventory work; use a general agent only when the question needs reasoning rather than reading. Every brief states, verbatim: the exact numbered questions, nothing open-ended; the output shape — `path:line` plus exact signatures and a one-line finding each, no code dumps and no file contents; the budget — "Use at most 20 tool calls. When you reach it, report what you have and name what is still open. Do not keep going."; and the batching paragraph, which the brief carries in full because a subagent starts with an empty context and will otherwise read one file per turn — "**Batch your reading.** Every turn re-sends your whole context, so N reads in N turns bill that context N times. You inspect and report — nothing you read depends on a previous result: put every independent read or grep of one round into ONE call. Use `Tools/pf/pf-exec` where the repo ships it (heredoc of `label : command` lines, run in parallel, each output capped, `read FILE:L1-L2` for a slice); otherwise put several reads in one message. Do not spend a turn checking whether it exists — run it; if the shell says command not found, that one failed call is your answer and you fall back to several reads in one message." A contract the brief does not carry is a contract the subagent does not act on: measured on this project, the same exploration brief ran 8 model turns with 0 batched calls without that paragraph and 6 turns with 25 commands in 5 batched calls with it — 42% less context re-sent. Never launch a second wave for a question a first wave already covered, and never launch a subagent for something you have already found while waiting. Plan from the returned summaries.

   Decide which findings actually matter for execution — the specific files, symbols/lines, reuse points, and read-only constraints — and carry those forward for the Code Map. This is where the investigation lands: the spec preserves it so it is never re-narrated to the implementer at dispatch time.
{% if workflow.route == "oneshot" or workflow.route == "full" %}
3. The route is `{{ workflow.route }}`; `route_source` is `pinned`.
{% else %}
3. {{ workflow.route_selection }}

   `route_source` is `auto`.
{% endif %}
4. Read `{{ rendered("spec-template.md") }}` fully, preserving all frontmatter fields and resolving `date` to the current system date.
   - **Oneshot:** set `route: 'oneshot'`.
   - **Full:** set `route: 'full'`. Put what you learned into `## Code Map`: paths, symbols or lines, what to reuse, and what not to change. The subagent should be able to work from the spec without being told any of it again.

   Set `route_source` from step 3.


   **Set `kind`** from the story's own intent: `finish` if the work is to make an already-built surface look right against an approved mockup, `function` for everything else — behaviour, logic, and the structural build of a surface. A story carrying both is two stories; split it rather than picking one.

   **If this story draws something,** fill the section its `kind` calls for and delete the other outright, saying so in your output rather than leaving it empty. A story that draws nothing deletes both.

   - **`kind: function` → `## Render Floor`.** Name the surface, the fixture that will be on screen and what it puts there, and what later work owns so its absence is not read as a defect. Apply the dividing test to every claim before you write it: *can this be settled by looking at one capture of this fixture alone, without knowing what the finished screen is supposed to look like?* If no, it is aesthetic — it belongs to the finish epic, and you leave it out rather than weakening it until it fits. Floor claims are settled by pixel probe or field assertion, never by a vision model.
   - **`kind: finish` → `## Visual Contract`.** Name the approved mockup and its version, the declared divergences file if the design package produced one, the fixture, and the round budget. Transcribe the claims from the approved design sources; do not invent them.

   In either case, do not resolve a missing or self-contradictory design source here — that is an intent gap. Before writing the section, check every row against the fixture you just declared: a row that cannot hold on that fixture is an intent gap, not a drafting problem, and is never repaired by rewording it.

   If `{preserved_intent_contract}` is non-empty, substitute it for the `<intent-contract>` block before writing `{spec_file}`. Self-check against the route's READY FOR DEVELOPMENT standard.
5. If intent gaps exist, do not fantasize and do not leave open questions. Multiple defensible readings of the intent that lead to observably different outcomes, with nothing in the intent to select between them, are an intent gap — do not resolve one by picking a reading. HALT with status `blocked`, blocking condition `intent gap`, and include the unanswered questions and evidence gathered.
6. Warning check. If step-01 carried `multiple-goals`, add it to `{spec_file}` frontmatter `warnings`. If `{spec_file}` exceeds 1600 tokens, add `oversized` to frontmatter `warnings`. Continue either way.

### READY-FOR-DEVELOPMENT GATE

Re-read `{{ rendered("workflow.md") }}`, then re-read `{spec_file}` from disk and verify the spec meets the READY FOR DEVELOPMENT standard.

- **If the file is missing:** HALT with status `blocked` and blocking condition `planned spec file disappeared before implementation`.
- **If the spec meets the standard:** set `{spec_file}` frontmatter status to `ready-for-dev`. If the invocation prompt directs a halt after planning (standard phrasing: `Halt after planning.` — accept any clear equivalent), HALT with status `ready-for-dev`; otherwise continue to step 3.
- **If the spec does not meet the standard:** repair it once, then re-read it from disk and verify again. If it now meets the standard, apply the **If the spec meets the standard** handling above, including the halt-after-planning check. If it still does not meet the standard, HALT with status `blocked`, blocking condition `spec failed ready-for-development standard`, and include the failing criteria and evidence gathered.

## NEXT

Read fully and follow `{{ rendered("step-03-implement.md") }}`
