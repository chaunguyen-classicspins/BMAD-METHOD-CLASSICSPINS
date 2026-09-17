---
title: '{title}'
type: 'feature' # feature | bugfix | refactor | chore
kind: 'function' # function | finish — function builds behaviour and structure; finish makes an already-built surface look right
created: '{date}'
status: 'draft' # draft | ready-for-dev | in-progress | in-review | done | blocked
route: '' # oneshot | full — set by step-02
route_source: '' # pinned | auto — set with route by step-02
review: '' # none | quick | thorough — set by step-04
review_source: '' # pinned | auto — set with review by step-04
lenses_ran: [] # ids of the lenses launched, set by step-04
review_loop_iteration: 0 # incremented by step-04 before each review loopback
followup_review_recommended: false # set by step-04 on status: done — true if the LLM decided another review pass is worthwhile
context: [] # optional: `{project-root}/`-prefixed paths to project-wide standards/docs the implementation agent should load. Keep short — only what isn't already distilled into the spec body.
warnings: [] # optional: machine-readable warnings for orchestration, e.g. oversized, multiple-goals
deferred: [] # append-only machine-readable deferred review findings; each item carries summary/evidence and optional location/severity
---

<!-- Target: 900–1300 tokens (less if route is oneshot). Above 1600 = high risk of context rot;
     add `oversized` to frontmatter `warnings` and continue.
     Never over-specify "how" — use boundaries + examples instead.
     Cohesive cross-layer stories (DB+BE+UI) stay in ONE file.
     IMPORTANT: Remove all HTML comments when filling this template. -->

<intent-contract>

## Intent

<!-- What is broken or missing, and why it matters. Then the high-level approach — the "what", not the "how". -->

**Problem:** ONE_TO_TWO_SENTENCES

**Approach:** ONE_TO_TWO_SENTENCES

## Boundaries & Constraints

<!-- Two tiers: Always = invariant rules. Never = out of scope + forbidden approaches.
     Delete this section if route is oneshot. -->

**Always:** INVARIANT_RULES

**Never:** NON_GOALS_AND_FORBIDDEN_APPROACHES

## I/O & Edge-Case Matrix

<!-- If no meaningful I/O scenarios exist, delete this section. Do not write "N/A" or "None".
     Delete this section if route is oneshot. -->

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| HAPPY_PATH | INPUT | OUTCOME | No error expected |
| ERROR_CASE | INPUT | OUTCOME | ERROR_HANDLING |

## Render Floor

<!-- `kind: function` ONLY, and only when the story draws something. If it draws nothing,
     DELETE THIS ENTIRE SECTION. Do not write "N/A" or "None". A `kind: finish` story has a
     Visual Contract instead and no Render Floor.

     THE DIVIDING TEST, applied to every claim you are about to write:
       Can this claim be settled by looking at ONE capture of THIS story's fixture alone,
       WITHOUT knowing what the finished screen is supposed to look like?
       Yes -> it belongs here.
       No  -> it is an aesthetic claim. It belongs to the finish epic. Do not write it here,
              and do not water it down until it fits — that is how an unsatisfiable row is born.

     Floor claims are settled deterministically and WITHOUT a vision model: a variance check
     (a capture that is one flat colour is a broken capture, not a failed claim), pixel probes at
     points whose expected colour is known from the design tokens, and field assertions. Never a
     coordinate, a hex value, a scale factor or a z-order in the table — those are field
     assertions in Tasks & Acceptance. -->

**Surface:** SURFACE_NAME · **Fixture on screen:** FIXTURE_AND_WHAT_IT_PUTS_THERE
**Out of scope — absent is correct:** WHAT_LATER_WORK_OWNS

| # | Floor claim | Settled by |
|---|-------------|------------|
| F1 | WHAT_MUST_BE_PRESENT_OR_ABSENT | pixel probe / field assertion |
| F2 | WHAT_MUST_BE_PRESENT_OR_ABSENT | pixel probe / field assertion |

## Visual Contract

<!-- `kind: finish` ONLY. A `kind: function` story never carries this section — DELETE IT.
     Do not write "N/A" or "None".

     A finish story judges a real capture against a mockup a person already approved, so name
     that mockup and its version. Every row is a claim a person (or a vision model) can settle by
     LOOKING — the aesthetic questions the floor deliberately refused: does this read as raised,
     as grounded, as deliberate furniture rather than a half-loaded row.

     Every row must be satisfiable on the surface as it will actually be built. A row that
     contradicts the approved mockup, or that describes a composition this surface cannot reach,
     is an intent gap — HALT, do not reword it to fit.

     Transcribe from the approved design sources; do not invent. Divergences the design package
     already declared (a mockup that stretches where production nine-slices, say) are passed to
     the judge as known and must never be reported as faults. -->

**Surface:** SURFACE_NAME · **Approved mockup:** PATH_AND_VERSION · **Declared divergences:** PATH_OR_NONE
**Fixture on screen:** FIXTURE_AND_WHAT_IT_PUTS_THERE
**Round budget:** N rounds — on exhaustion, HALT rather than continue tuning blind

| # | Observable claim | Source |
|---|------------------|--------|
| V1 | WHAT_A_LOOKER_MUST_BE_ABLE_TO_SEE | design source reference |
| V2 | WHAT_A_LOOKER_MUST_BE_ABLE_TO_SEE | design source reference |

</intent-contract>

## Code Map

<!-- Agent-populated during planning. Annotated paths prevent blind codebase searching.
     Delete this section if route is oneshot. -->

- `FILE` -- ROLE_OR_RELEVANCE
- `FILE` -- ROLE_OR_RELEVANCE

## Tasks & Acceptance

<!-- Tasks: backtick-quoted file path -- action -- rationale. Prefer one task per file; group tightly-coupled changes when splitting would be artificial. -->
<!-- If an I/O Matrix is present, include a task to unit-test its edge cases. -->
<!-- AC covers system-level behaviors not captured by the I/O Matrix. Do not duplicate I/O scenarios here. -->
<!-- Delete this section if route is oneshot. -->

**Execution:**
- [ ] `FILE` -- ACTION -- RATIONALE

**Acceptance Criteria:**
- Given PRECONDITION, when ACTION, then EXPECTED_RESULT

## Implementation Notes

<!-- Agent-owned. Append-only during implementation: decisions made, files touched, surprises
     encountered. Never delete this section. Leave empty at planning time, except on the
     oneshot route: start with a short explanation of why. -->

## Spec Change Log

<!-- Append-only. Populated by step-04 during review loops. Do not modify or delete existing entries.
     Each entry records: what finding triggered the change, what was amended, what known-bad state
     the amendment avoids, and any KEEP instructions (what worked well and must survive re-derivation).
     Empty until the first bad_spec loopback. -->

## Review Triage Log

<!-- Append-only. Populated by step-04 on EVERY review pass, including loopbacks and blocked exits.
     Each entry records verdict counts (high/medium/low/false/maybe-false) and one row per
     reviewer finding: verdict, route, and evidence — the refutation for false, what would settle
     it for maybe-false, the action taken for patches. Empty until the first review pass. -->

## Design Notes

<!-- If the approach is straightforward, delete this section. Do not write "N/A" or "None".
     Delete this section if route is oneshot. -->
<!-- Design rationale and golden examples only when non-obvious. Keep examples to 5–10 lines. -->

DESIGN_RATIONALE_AND_EXAMPLES

## Verification

<!-- If no build, test, or lint commands apply, delete this section. Do not write "N/A" or "None". -->
<!-- How the agent confirms its own work. Prefer CLI commands. When no CLI check applies, state what to inspect manually. -->

**Commands:**
- `COMMAND` -- expected: SUCCESS_CRITERIA

**Manual checks (if no CLI):**
- WHAT_TO_INSPECT_AND_EXPECTED_STATE
