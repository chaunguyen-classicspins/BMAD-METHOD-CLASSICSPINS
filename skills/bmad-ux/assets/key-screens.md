# Key Screens Renderer

Subagent prompt. Fired at Finalize (or during late Discovery once layout decisions firm up). Produces 1:1 HTML mocks of the load-bearing surfaces so the spine can link to them as visual reference. Spine remains the contract; mocks illustrate.

## Inputs

`.memlog.md`, the current drafts `DESIGN.md` and `EXPERIENCE.md`, `.working/` (especially the chosen color-theme and direction mocks), source PRD, the settled form-factor and its capture resolution from `{workflow.capture_profiles}`. The user names which surfaces to render — typically 2-4: the canonical entry surface, the most complex flow's hero screen, any load-bearing overlay/modal, and (when present) the Week / list / dashboard view.

## What to render

One HTML file per screen, at `.working/key-{slug}.html` — `{slug}` is the surface key from the EXPERIENCE.md IA table, used verbatim. Each file: realistic device frame (phone or browser), real product content from the conversation (no lorem), every visible string voice-checked against `.memlog.md`, all decided tokens applied. Show one canonical state per screen; if a surface has a load-bearing alternate state (focus, error, crisis-card-present), render it as a second column or section in the same file.

The canonical panel carries `id="capture"` and is exactly the capture resolution in CSS pixels at scale 1 — no `transform: scale`, no cropping frame around it. Load-bearing alternate states get `id="capture-{state}"` at the same size.

Inline CSS, system fonts, no JS, no network. The mock must render fully offline. Comment block at the top of the `<style>` notes which spine sections govern this screen so a future reader knows what to check.

## What to capture

Export one PNG per capture panel, headless, screenshotting the element rather than the page: `.working/key-{slug}.png` (`-{state}` suffixed for alternates). Measure each export's real pixel dimensions and report them — a half-scale PNG is worthless to the vision referee that later diffs it against a product screenshot. Command and element-screenshot snippet: `references/finish-handoff.md`.

## What to return

A compact summary to the parent:
- HTML and PNG path per screen, plus the PNG's measured pixel size
- one-line caption per screen ("Today picker at rest; accent on Thought record")
- which spine sections each mock illustrates (Component Patterns rows, State Patterns rows, Flow steps)
- the elements a reviewer can point at in each capture, and any place the mock knowingly departs from how the product will render it (stretched art the product 9-slices, frozen animation, placeholder content) — these seed `SURFACES.md` and `DIVERGENCES.md`

The parent, at Finalize "Layout extracted, artifacts promoted," uses this summary to number the promoted pairs, write those two files, and insert inline `mockups/...` links into the relevant spine sections.

## Anti-patterns

- Do not invent layout — every composition decision must trace to a `.working/` artifact or a confirmation in `.memlog.md`. If a layout question is open, the mock is premature.
- Do not show every screen of every flow — 2-4 load-bearing surfaces, not 14.
- Do not stage marketing copy. Strings come from `.memlog.md` and voice rules.
- Do not introduce a new pattern not in the spine's Component Patterns table. If you need one, log it and ask before rendering.
- Do not hand-edit an exported PNG, and do not let one drift from its HTML — the HTML is the source; re-export instead.
- Do not leave a deliberate mock-vs-product shortcut unreported. Undeclared, it reads later as a build defect.
