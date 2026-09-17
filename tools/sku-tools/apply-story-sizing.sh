#!/usr/bin/env bash
#
# apply-story-sizing.sh — install the agent-loop planning law into a BMad project.
#
# Writes _bmad/custom/bmad-create-epics-and-stories.toml, which appends three
# families of structural rules to bmad-create-epics-and-stories:
#   A. STORY SIZE  — how much work rides on one context reload
#   B. EPIC ORDER  — headless epics first, presentation epics last
#   C. COMPLETION  — no story whose criteria need a human or a device
# They need no calibration and no measurement: they are tests a planner applies
# while writing the epic. Safe to re-run — identical content is a no-op.
# (Filename kept for continuity; it now installs more than sizing.)
#
# Usage:
#   apply-story-sizing.sh [TARGET_PROJECT_ROOT] [options]
#
#   TARGET_PROJECT_ROOT   defaults to the current directory
#
#   --force      overwrite an existing, different file (a .bak copy is kept)
#   --dry-run    show what would happen, write nothing
#   --print      print the file content to stdout and exit
#   -h, --help   this text
#
set -euo pipefail

TARGET=""
FORCE=0
DRY=0
PRINT=0

# Print the header comment block (everything between the shebang and `set -euo`),
# skipping the GENERATED stamp the sync adds. Not line-number based: a stamped
# copy in a SKU has one extra line at the top.
usage() { awk 'NR==1{next} /^set -euo/{exit} /^# GENERATED/{next} /^#/{sub(/^# ?/,""); print}' "$0"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --force)   FORCE=1 ;;
    --dry-run) DRY=1 ;;
    --print)   PRINT=1 ;;
    -h|--help) usage; exit 0 ;;
    -*)        echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
    *)         if [ -n "$TARGET" ]; then echo "too many arguments" >&2; exit 2; fi; TARGET="$1" ;;
  esac
  shift
done

read -r -d '' CONTENT <<'TOML_EOF' || true
# Planning rules for an autonomous single-agent loop.
# Project override for bmad-create-epics-and-stories, merged over the skill's own
# customize.toml (base < this file < *.user.toml). persistent_facts and the
# activation_steps_* arrays APPEND to the base lists; on_complete is a scalar and
# overrides. Installed by Tools/bmad/apply-story-sizing.sh.
#
# Four rule families, all aimed at the same execution model: a sequential loop of
# fresh agent sessions, one per story, with no human watching.
#
#   A. STORY SIZE      — how much work rides on one context reload.
#   B. EPIC ORDER      — headless work first, presentation work last.
#   C. COMPLETION      — a story is done when the session can prove it alone.
#   D. VISUAL GATES    — a function story proves its floor; one finish epic owns the look.
#
# WHY (A) STORY SIZE
# The shipped skill sizes stories for a human sprint team. Its only sizing rule is
# step-03-create-stories.md "Are sized for single dev agent completion" — an upper
# bound with no lower bound — and its bad-example list punishes the merged shape.
# It carries a consolidation rule for work that churns the same files (step-02)
# but applies it only at EPIC level.
#
# Nothing in it knows that every story is executed by a FRESH agent session that
# must re-load its whole context before doing any work. That reload is a fixed
# cost paid once per story, so a story smaller than the reload pays full price for
# half a story. Observed on a real run: the cheapest story in an epic — one method
# added to an existing class — still cost as much as a mid-sized one, while in the
# other direction a story bundling four unknowns took two sessions and a human
# escalation, and its follow-up blocked outright. Too big fails harder than too
# small; both failures are avoidable at planning time.
#
# WHY (B) EPIC ORDER
# step-02 forbids organising by technical layers, and for a human team that is
# right: a database epic delivers nothing anyone can use. For this loop it is
# half right. A headless story is verified by a test the session runs itself and
# is finished when the test is green. A presentation story needs a scene, an
# editor, a rig and usually an eye, and is finished when somebody looks.
# Interleaving them makes every rules story pay for a presentation context it does
# not need, and makes every presentation story re-derive a rule that was never
# frozen. So: user value still binds INSIDE an epic and every epic still states
# the outcome it delivers, but the epic AXIS is ordered by layer.
#
# WHY (C) COMPLETION
# A story whose acceptance criteria need a device, a store account or a human
# eyeball cannot be closed by the session that implements it. In a loop it does
# not fail loudly — it stalls, or worse, the session marks it done on a promise.
# Human work is real and must be recorded, but it is a checklist beside the epics,
# never a story inside them, and never a completion criterion.
#
# WHY (D) VISUAL GATES
# A design token file names colours, spacings, radii and type sizes; it does not
# name what a person must be able to SEE at rest on a given surface. Between the
# token and the pixel sits an abstraction gap: the wrong material or shader, MSAA
# left on, a colour-space mistake, a renderer disabled, a sorting order right in
# the field and wrong on screen — and the whole class no field assertion is aimed
# at, which is what a looker notices first. Field assertions (R2) close half the
# gap; the other half is a checklist a vision model can score against one still
# capture. Observed on a real run: story 1.5's fourth attempt spent 62 min and
# $18.46 on a sample-point verification that certified two real defects as
# correct, both of which one vision pass over the same capture found in 23
# seconds. Every project that renders anything pays this cost once unless the
# planner writes the section at planning time, where the epic-wide context needed
# for the "what later stories own so its absence is not read as a defect" line
# actually exists.
#
# RETARGETED 2026-09-17. The first version of this family put a `## Visual
# Contract` on every story that rendered a surface. That failed for a structural
# reason, twice on the same story: such a story renders a HALF-BUILT screen — the
# board exists, the booster bar does not yet — so a claim about how the finished
# composition reads cannot be settled against it. Story 1.5's V7 asked for "one
# cabinet of paired columns" on a fixture whose own grid rule renders a single
# column: VIOLATED seven times, unsatisfiable by construction, and unfixable
# because the row sat inside `<intent-contract>`. Its V3 ("the shadow reads as
# grounding") burned four rounds of blind parameter tuning. Both are the same
# defect — a composition question asked of an incomplete composition. So the
# family now splits by story kind: a `kind: function` story carries a
# `## Render Floor` settled deterministically with no model, and one
# `kind: finish` epic, placed after the last epic that introduces a surface,
# owns every aesthetic claim on every surface and produces the reference
# captures. Of the two halves of the abstraction gap above, the floor closes the
# mechanical half (did it render, is it the right colour at a known point) and
# the finish epic closes the half only a looker can judge.
#
# PORTABLE BY DESIGN
# The rules below are structural, not numeric: tests a planner applies while
# writing the epic, with no measurement and no project-specific thresholds. Copy
# into any project whose stories are run by a sequential single-agent loop; no
# calibration, works before the first story has ever run.
#
# WHEN THEY STOP APPLYING
# A human team, several agents in parallel, or a loop that keeps one context
# across stories all remove the reload cost, and family A's defaults become right
# again. Family B relaxes when a human is driving and wants something to look at
# early. Family C survives all three: an acceptance criterion nobody can evaluate
# is a defect under any execution model. The SEAM and UNKNOWN tests survive too.
# Family D survives every execution model — the abstraction gap between token and
# pixel is not about who runs the session — but its shape is project-local: a
# project whose R3/R4 rungs are not judge-based (no `visual-judge.sh`, no vision
# model in the build workflow) still writes the contract, and reads it back as
# structured claims a human reviewer can walk instead of judge automation.

[workflow]

persistent_facts = [

  # ---------- A. STORY SIZE ----------

  "Each story in this project is implemented by a fresh agent session that must re-load its entire context — the relevant spec sections, the architecture decisions, the source files it will touch, the project's agent instructions — before it can do any new work. That reload is the dominant fixed cost of a story, so story size is decided by how much useful work rides on one reload, not by how small a unit of user value can be demonstrated.",

  "CONTEXT TEST. If two candidate stories would make the agent load the same context set — the same spec sections, the same source files, the same architectural decisions — they are one story. Split only where the context set genuinely changes. Apply the step-02 'File Churn on Same Component' rule at STORY level, not only at epic level: consecutive stories that modify the same view, the same pool, the same tuning table or the same scaffold are one story.",

  "SEAM TEST. A story boundary must be a contract the next story can consume without reopening it: a public interface, a file format, a port, a finished rendered surface. If completing story B would require editing code story A just wrote, the seam is wrong and the two are one story. A 'Depends on / Leaves to' line that hands over an unfinished surface is the symptom.",

  "UNKNOWN TEST. Every story carries exactly one unknown — one thing whose answer cannot be written down at planning time: an algorithm, a calibration, an integration with something the project has never touched, a platform or build gate. Two unknowns in one story is what stalls a session, burns its budget and escalates to a human. Zero unknowns means it is not a story at all: a pool, a DI registration, a boot prewarm, a badge, one more HUD element, a second dialog of the same shape as the first is mechanical work, and it rides along with the story that owns its surface.",

  "PATTERN TEST. The first instance of a repeated pattern is a story, because it establishes the scaffold. Instances 2..N of that same pattern are acceptance criteria of that story, never stories of their own.",

  "NAME TEST. No story is named after a file, a class, a folder, a module, a manifest, a layer or a registration — 'the codec', 'the pool wiring', 'the tokens file', 'the DI setup', 'the scene manifest row'. A title like that is the symptom that the split followed the source tree instead of the work, and it is exactly how a plan grows twenty stories that each reload the same context. Rename the story after the contract it freezes or the capability it finishes. If it cannot be renamed that way, it has no unknown of its own and belongs inside a neighbour.",

  "The step-02 'clear user value' rule binds at EPIC level. Inside an epic, a technical slice is a legitimate story when it is what one agent session can own end to end. When the tests above leave a genuine tie, merge mechanical work and split risky work: an oversized mechanical story costs one long session, an oversized risky story costs a human.",

  "SELF-CHECK before presenting an epic's story list. For each story, state in one line: (a) the context set it loads, (b) its single unknown, (c) the contract it freezes for the next story, (d) the one verification that proves it, runnable unattended. A story that cannot fill all four is not a story — merge it into a neighbour. Two stories that answer (a) or (d) identically are one story.",

  # ---------- B. EPIC ORDER ----------

  "LAYER ORDER. Order the epic list so that everything provable without a rendered surface ships first and everything that only exists on screen ships last. Early epics: the domain rules, the data formats and codecs, the generators and solvers, the persistence, the lifecycle, the telemetry — anything a headless test can close. Late epics: the views, the screens, the HUD, the dialogs, the art placement, the motion and the visual gates. This deliberately overrides step-02's 'Organize by USER VALUE, not technical layers' on the EPIC AXIS ONLY. Inside every epic, user value still binds and every epic still states the outcome it delivers.",

  "LAYER ORDER IS NOT AN EXCUSE FOR A SETUP EPIC. step-02's real target — 'Epic 1: Database Setup', 'Epic 2: API Development' — stays forbidden. The difference is that a layer-ordered epic still finishes a capability end to end within its layer and freezes a contract the next epic consumes: 'the board obeys its rules and proves it headless' is an epic, 'create all the models' is not. If an early epic cannot state what is now true that was not true before, it is a setup epic wearing a new name.",

  "LAYER ORDER EXCEPTION. At most ONE presentation epic may come early, and only when the project cannot answer its central question without looking at the thing — a game's readability, a chart's legibility, a physical layout, anything where the risk being retired is visual. Name it as such ('the thin playable spine'), keep it to the thinnest surface that answers that one question, and leave the full presentation epics at the end. State the claim out loud when presenting the epic list, with the question it retires. If no such question exists, there is no exception and every view ships late.",

  "PRESENTATION EPICS INHERIT, THEY DO NOT DISCOVER. Because the rules are frozen and tested before the first view exists, a presentation story reads its numbers rather than choosing them, and a rule change costs a test rather than a re-layout. When a late UI story finds itself deciding a rule — a threshold, a legality check, a score — that is a defect in an early epic, not a decision for the UI story to make.",

  # ---------- C. COMPLETION ----------

  "UNATTENDED TEST. A story's completion criteria must be decidable by the session that implements it: a test it can run, a file it can read, an assertion that fails on its own. Anything needing a person, a physical device, a store or platform account, a live third-party service, or a judgement made by eye is NOT an acceptance criterion and NOT a story. Never write a story whose deliverable is 'verify on device', 'profile a release build', 'run a manual QA pass', 'review the art', 'confirm the copy reads well', 'playtest the feel' or 'measure the touch target on hardware'.",

  "SPLIT THE CHECK BEFORE MOVING IT. Most device or human checks have a half a machine can do, and that half is usually the half that catches regressions. Before relocating one, ask what part is an assertion — a memory figure read from a profiler API, an atlas page count, a glyph-coverage table lookup, a generated layout measured in code, a contrast ratio computed from two tokens — and keep that half as an acceptance criterion in the owning story. Only the irreducibly human half moves. A story that gives up the whole check because part of it needs hardware has given up the part that would have failed first.",

  "WHERE THE HUMAN WORK GOES. Collect the irreducibly human work in ONE appendix — a Human Verification Checklist — outside every epic. Each row names the check, when it becomes worth running, and what a failure reopens. The appendix states plainly that none of it is a completion criterion for any story and none of it blocks the loop. Where a check would invalidate a planning assumption rather than merely report on it, mark that row BLOCKING and name the story whose assumption it tests — that is a flag raised for the human, still not a story.",

  "CONFIRM, NEVER DROP SILENTLY. When a source document — a spec, a PRD, an architecture decision, an acceptance-criteria list, a UX handoff — asks for a device verification, a manual QA pass, a hardware profiling run or any other human-gated check, do NOT quietly convert it into an appendix row. STOP and ask the developer: name the requirement and where it came from, say which half you believe is machine-checkable and where you would put it, say what would move to the checklist, and get an explicit answer before writing the story. A requirement its author wrote on purpose is theirs to relocate, not the planner's. Batch these into one question rather than interrupting per requirement, and never treat silence or a general approval as the answer.",

  # ---------- D. VISUAL CONTRACT ----------

  "TWO SECTIONS, ONE PER STORY KIND. Both live inside a story's `<intent-contract>`, therefore read-only to the implementer, and both name (a) the surface id — a stable slug like `gameplay-board`, `level-complete`, `booster-bar-stocked` — that the harness will capture; (b) the fixture that will be on screen when the capture is taken, named as a file path plus what that fixture puts on the surface; and (c) what LATER stories own on this same surface, so its absence in the capture is not read as a defect. They differ in what they claim and in who settles it. A `kind: function` story carries a `## Render Floor`: claims settled DETERMINISTICALLY and with no model — a variance check that a capture rendered at all, a pixel probe at a point whose colour the design tokens already fix, a field assertion. A `kind: finish` story carries a `## Visual Contract`: numbered rows, each a claim settleable by looking at ONE still capture against the approved mockup the contract names, phrased so a vision judge can answer SATISFIED, VIOLATED or CANNOT-TELL. A CANNOT-TELL row names the R2 field assertion that settles it instead — that is how R2's list is DERIVED from R3, not invented alongside.",

  "PRESENCE TEST. Any `kind: function` story that renders a distinct SURFACE — a board, a screen, a HUD, a dialog, a map node treatment, a loading state, a background wall — carries exactly one `## Render Floor` per distinct surface it FREEZES. Every `kind: finish` story carries exactly one `## Visual Contract` per surface it takes to its approved look. A story that renders no surface — a domain rule, a codec, a solver, a generator, a persistence layer, a telemetry forwarder, a scaffold — carries neither, and must not, because the gates read their presence. A story that touches an already-frozen surface without freezing a new one carries neither either; it inherits the earlier story's section and cites it. Multi-surface stories carry ONE section per surface, each in its own block, each with its own surface id, fixture and claims.",
  "THE DIVIDING TEST, applied to every claim before it is written into any story. Ask: can this claim be settled by looking at ONE capture of THIS story's fixture alone, WITHOUT knowing what the finished screen is supposed to look like? Yes — it is a floor claim and belongs to the `kind: function` story that renders the surface. No — it is an aesthetic claim and belongs to the finish epic; strike it from the function story rather than weakening it until it fits. Floor: the backdrop rendered and is not one flat fill, three slots are present, the badge sits in row 0, no element belonging to a later story leaked in, every label fits inside its control in the longest locale. Ceiling: the shadow reads as the goods sitting on the shelf, the HUD reads as loose items on the illustrated wall with no panel behind them, the locked node and the current node are two different treatments rather than one treatment at two opacities. An aesthetic claim placed in a function story is a planning defect with a known failure mode: its fixture renders a half-built screen, so the claim is either unanswerable or answerable and wrong, and no later stage is permitted to relax it.",

  "STATES ARE NOT SURFACES. Interaction states that only exist during a gesture or animation — drag ghosts, hover feedback, selection highlights, in-flight tweens, match-clear particles, layer-rise motion — are R2 field assertions in the story that owns the interaction. They are not VC rows in the story that owns the resting surface, because a VC is judged on ONE still capture, and a state that requires input or motion to see cannot be settled that way. When the interaction story lands, the resting surface's VC does not gain rows — the interaction is proven by its own field assertions plus, if the end state is itself a new resting surface (e.g. a cleared compartment), that story writes its own VC for the new resting state.",

  "WRITE THE CONTRACT AT PLANNING TIME, NOT AT IMPLEMENTATION TIME. The `what LATER stories own` line requires epic-wide knowledge — only the planner knows what story 1.8's HUD will overlay or what story 1.9's booster bar will occupy at the bottom. A dev session running one story alone cannot write that line without guessing, and either guess fails: a permissive section mutes the gate, a strict one flags every later story that legitimately adds to the surface as a defect. Every `## Render Floor` and every `## Visual Contract` belongs in the story's spec as first authored, not added by a post-hoc correction after a gate has failed. The planner is the only role with the context to write it correctly. The planner also owes each claim the SATISFIABILITY check: a claim that cannot hold on the fixture the same section declares is an intent gap, and it is never repaired later by rewording the claim to match whatever happened to render.",

  "SURFACE OWNERSHIP MAP. When Step 2 presents the epic list, alongside LAYER ORDER, produce a Surface Ownership Map: one row per distinct surface the plan will render, naming the surface id, the `kind: function` story that FIRST renders it (owns its `## Render Floor`), every LATER function story that adds to that same surface (cites the floor, does not rewrite it), the `kind: finish` story that takes it to its approved look (owns its `## Visual Contract` AND produces its reference capture), and the story that closes any regression gate over it. A surface with no first-render story is a defect in the plan. A surface with no finish story is a defect in the plan. Two stories claiming to first-render the same surface is a defect. A LATER story adding to a surface without a cite line is a defect. Reference captures are an OUTPUT of the finish epic, never of a function story: a function story has nothing approved to be a reference against.",
]

# Surfaced at activation so the ordering claim and the human-gated inventory are
# made before Step 2 proposes structure, not discovered in Step 4.
activation_steps_append = [
  "While reading the input documents in Step 1, keep a running list of every requirement worded as a device check, a hardware profiling run, a manual QA pass, a playtest or a review by eye — with the document and section each came from. That list is the input to the CONFIRM, NEVER DROP SILENTLY rule, and it must be raised with the developer as one batched question before Step 3 writes any story.",

  "When Step 2 presents the epic list, present the LAYER ORDER with it: mark each epic headless or presentation, show that no presentation epic precedes a headless one, and if you are claiming the LAYER ORDER EXCEPTION, say which epic it is and which visual question it retires. The ordering is part of the structure being approved, not an implementation detail decided later.",

  "When Step 2 presents the epic list, present the SURFACE OWNERSHIP MAP alongside LAYER ORDER: one row per distinct surface the plan will render, naming the surface id, the FIRST-render story that will own its `## Visual Contract` and reference capture, every LATER story that adds to that surface, and the story that closes any regression gate over it. This is the input to family D at Step 3 and Step 4's audit; it must be shown before Step 3 writes any story.",
]

# Runs at Step 4 once the user confirms [C] Complete.
on_complete = """
Run four audits over the saved epics.md and FIX what you find, then report in one short block — findings only, no restatement of the plan.

1. UNATTENDED. Grep every story's acceptance criteria for human-gated language: 'on device', 'on a real', 'on hardware', 'profile', 'by eye', 'review', 'playtest', 'manually', 'confirm with', 'looks right', 'feels'. Every hit that sits in a completion criterion is a defect. Apply SPLIT THE CHECK BEFORE MOVING IT: keep the machine-checkable half as an assertion in the owning story, move the human half to the Human Verification Checklist, and list which stories changed. If any hit came from a source document that was never confirmed with the developer, say so and ask now.

2. LAYER ORDER. List the epics in order, each marked headless or presentation. Report any presentation epic preceding a headless one and either justify it as the declared LAYER ORDER EXCEPTION or reorder. Report any early epic that cannot state what is now true that was not true before — that is a setup epic.

3. FRAGMENTATION. For every story print one line: context set / single unknown / contract frozen / unattended verification. Report any story that cannot fill all four, any pair whose context set or verification is identical, and any title that names a file, class, module or registration (NAME TEST). These are merges and renames to apply, not observations to file.

4. VISUAL CONTRACT. Walk the Surface Ownership Map presented at Step 2. For every story marked first-render of a surface, confirm its spec carries a `## Visual Contract` block per distinct surface it freezes, each naming (a) surface id, (b) fixture and what it puts on screen, (c) what LATER stories own so their absence is not a defect, (d) numbered rows settleable by looking at one capture — a block missing any of the four is not a Visual Contract, add the missing part or flag the row. Report any first-render story missing a VC and add one from the Ownership Map. Report any VC in a non-rendering story and remove it — VC in a headless or interaction-only story is a defect. Report any VC row that describes an interaction state (drag, hover, in-flight animation, transient particle) rather than the resting surface, and move it to the interaction-owning story's R2 assertions. Report any LATER-render story that rewrites a VC instead of citing the first-render story's VC, and rewrite it as a cite. Report any surface named in the Ownership Map whose first-render story has no VC, and any VC whose surface id does not appear in the Ownership Map — these are two symptoms of the same drift.
"""
TOML_EOF

if [ "$PRINT" = "1" ]; then
  printf '%s\n' "$CONTENT"
  exit 0
fi

TARGET="${TARGET:-$PWD}"
if [ ! -d "$TARGET" ]; then
  echo "error: target is not a directory: $TARGET" >&2
  exit 1
fi
TARGET="$(cd "$TARGET" && pwd)"

# Sanity: does this look like a BMad project?
if [ ! -d "$TARGET/_bmad" ]; then
  if [ "$FORCE" = "1" ]; then
    echo "warning: no _bmad/ in $TARGET — continuing because --force"
  else
    echo "error: no _bmad/ directory in $TARGET — is this a BMad project?" >&2
    echo "       re-run with --force to install anyway." >&2
    exit 1
  fi
fi
SKILL_DIR=""
for d in "$TARGET/.claude/skills/bmad-create-epics-and-stories" "$TARGET/.agents/skills/bmad-create-epics-and-stories"; do
  [ -d "$d" ] && SKILL_DIR="$d" && break
done
[ -n "$SKILL_DIR" ] || echo "note: bmad-create-epics-and-stories is not installed here yet; the file will apply once it is."

DEST_DIR="$TARGET/_bmad/custom"
DEST="$DEST_DIR/bmad-create-epics-and-stories.toml"

if [ -f "$DEST" ]; then
  if printf '%s\n' "$CONTENT" | cmp -s - "$DEST"; then
    echo "already up to date: $DEST"
    exit 0
  fi
  if [ "$FORCE" != "1" ]; then
    echo "error: a different $DEST already exists." >&2
    echo "       It may hold your own persistent_facts — review before replacing:" >&2
    echo "         $0 --print | diff - \"$DEST\"" >&2
    echo "       Then re-run with --force (a timestamped .bak is kept)." >&2
    exit 1
  fi
fi

if [ "$DRY" = "1" ]; then
  echo "[dry-run] would write $DEST ($(printf '%s\n' "$CONTENT" | wc -l | tr -d ' ') lines)"
  [ -f "$DEST" ] && echo "[dry-run] would back up the existing file first"
  exit 0
fi

mkdir -p "$DEST_DIR"
if [ -f "$DEST" ]; then
  BAK="$DEST.bak.$(date +%Y%m%d-%H%M%S)"
  cp "$DEST" "$BAK"
  echo "backed up existing file -> $BAK"
fi
printf '%s\n' "$CONTENT" > "$DEST"
echo "wrote $DEST"

# Validate TOML if python3 is around.
if command -v python3 >/dev/null 2>&1; then
  python3 - "$DEST" <<'PY' || { echo "error: the file written is not valid TOML" >&2; exit 1; }
import sys
try:
    import tomllib
except ModuleNotFoundError:
    sys.exit(0)  # python < 3.11: skip validation
with open(sys.argv[1], "rb") as fh:
    data = tomllib.load(fh)
w = data["workflow"]
print(
    f'valid TOML, {len(w["persistent_facts"])} persistent_facts, '
    f'{len(w.get("activation_steps_append", []))} activation_steps_append, '
    f'on_complete {"set" if w.get("on_complete") else "empty"}'
)
PY
fi

# Confirm the skill's resolver actually merges it, when both are present.
RESOLVER="$TARGET/_bmad/scripts/resolve_customization.py"
if [ -n "$SKILL_DIR" ] && [ -f "$RESOLVER" ] && command -v uv >/dev/null 2>&1; then
  if (cd "$TARGET" && uv run "$RESOLVER" --skill "$SKILL_DIR" --project-root "$TARGET" --key workflow >/dev/null 2>&1); then
    echo "resolver merge: OK"
  else
    echo "note: could not run the resolver to confirm the merge; the skill falls back to reading the file itself."
  fi
fi

cat <<'NEXT'

Done. The rules apply the next time bmad-create-epics-and-stories runs.

They do NOT auto-load in other skills. When re-planning with bmad-correct-course
or bmad-spec, tell that session:

  read _bmad/custom/bmad-create-epics-and-stories.toml and obey its
  persistent_facts; run its SELF-CHECK for every story you propose.
NEXT
