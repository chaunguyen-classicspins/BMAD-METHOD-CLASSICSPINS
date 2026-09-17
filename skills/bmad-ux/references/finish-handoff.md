# Finish Handoff

Downstream **finish** work (a `kind: finish` story, a visual-polish pass, any human doing the same by eye) judges a built screen by putting a screenshot of the real product next to the approved mock and naming the differences — often with a vision model as referee. A vision referee cannot read HTML, cannot guess which revision was approved, and cannot tell a deliberate mock shortcut from a build defect.

So this workflow emits, per surface: a **capture PNG**, a **version + approval record**, an **element inventory**, a **declared-divergence list**, and once per package a **finish bar**. HTML stays the mock source — editable, token-driven, diffable. PNGs are exports, never hand-edited.

## Surface keys

Key = the slug of the surface's row in EXPERIENCE.md Information Architecture (`gameplay`, `level-map`, `pause`). One key per IA surface, stable for the life of the package, used verbatim everywhere: `mockups/key-{surface}-{NN}.html`, `mockups/key-{surface}-{NN}.png`, the `SURFACES.md` record id, the `DIVERGENCES.md` heading. A filename a reader can't map back to an IA row is a broken handoff.

## Versions

- `{NN}` is a zero-padded per-surface revision, `01` first. Any change a reviewer would see earns the next number. **Never overwrite an approved pair** — superseded versions stay on disk.
- Drafts live unversioned in `.working/key-{surface}.html`; the number is assigned at promotion.
- Docs, stories and review notes cite the versioned filename (`key-gameplay-02.png`), never the bare key. Sessions that never meet still agree on which pixels are meant.
- Approval is **per surface** (`SURFACES.md` row). Revising one surface reopens that surface, not the package. DESIGN.md frontmatter `approval` covers the art direction, not per-screen sign-off.

## Capture

- Capture resolution follows the Foundation form-factor resolved in Discovery, matched against `{workflow.capture_profiles}`. Derive it; never hardcode. The mock PNG and the screenshot the finish story takes must be the same pixel size — a portrait mobile game on a 1080×1920 rig captures at 1080×1920; web captures at the breakpoint stated in Responsive & Platform.
- Each key-screen HTML marks its canonical panel `id="capture"`, sized to exactly those CSS pixels at scale 1 (no `transform: scale`). Load-bearing alternate states in the same file get `id="capture-{state}"` and their own PNG, suffixed `key-{surface}-{NN}-{state}.png`.
- Export by screenshotting the element, not the page — a file that also carries annotation or a second column would otherwise leak into the frame:

  ```js
  // .working/capture-surfaces.mjs — run with playwright or puppeteer, whichever is available
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  await page.goto(`file://${htmlAbsPath}`);
  await page.locator('#capture').screenshot({ path: pngPath });
  ```

  Fallback when the file renders exactly one panel at capture size: `chromium --headless --disable-gpu --hide-scrollbars --force-device-scale-factor=1 --window-size=W,H --screenshot="PATH.png" "file://ABS.html"`.
- Verify every export's actual pixel dimensions against the profile and report them; a silently half-scale PNG poisons every later comparison. When the package carries an asset manifest, add the captures with their SHA-256 like any other asset.

## SURFACES.md

One file, YAML frontmatter (machine-readable — the element claims and the approval state) plus a human table. Written at Finalize, updated on every promotion.

```markdown
---
capture_profile: mobile-portrait
capture: { width: 1080, height: 1920 }
surfaces:
  gameplay:
    version: '02'
    approved: 2026-09-14
    approved_by: Chau
    mock: mockups/key-gameplay-02.html
    capture: mockups/key-gameplay-02.png
    state: rest
    elements:
      - { id: hud.level-label, note: top-left, above the shelf stack }
      - { id: hud.timer }
      - { id: shelf.compartment, count: 8 }
      - { id: booster.bar }
    excludes: [map.level-node, pause.panel]
  blocked-board:
    capture: none
    reason: table-specified recovery dialog; no layout decision to see
---

| Surface | Version | Capture | Approved |
|---|---|---|---|
| Gameplay | 02 | `key-gameplay-02.png` | 2026-09-14 · Chau |
| Blocked board | — | spine-only | — |
```

- One record per IA surface row. Spine-only surfaces carry `capture: none` + `reason`; finish stories skip them.
- `elements` are dotted, stable ids for things a reviewer can point at — not DOM nodes. They become deterministic claims downstream ("this element is present"). `count` only where the number is load-bearing. `excludes` names elements owned by other surfaces that must not leak in.
- Derive both lists from the IA table and Component Patterns. Never invent a widget the spines don't define; if the mock needs one, log it and ask.

## DIVERGENCES.md

Every place the mock deliberately differs from what the product will render, per surface. Each row: what the mock does, what the product does, why, and the verdict the referee must not raise.

```markdown
## gameplay — key-gameplay-02

| Mock does | Product does | Why | Do not report |
|---|---|---|---|
| Stretches the 3.00:1 shelf master ~1.7× vertically into the 1.76:1 compartment | 9-slices it (borders ≈ L36/R35/T42/B64 at 480×160) | CSS mock has no 9-slice; production keeps rails and posts unstretched | Rail thickness, post proportion or wood-grain scale on the shelf frame |
```

- Sources: technique deltas (9-slice vs stretch, atlas vs single sprite), font rasterization, placeholder content, states the engine animates and the mock freezes, and anything sitting as production-preparation prose in an asset handoff — lift it here rather than leaving it buried.
- "None" is a claim: write it per captured surface rather than omitting the surface.
- Keep it narrow. A divergence is a technique or pipeline fact, declared once. It is never a licence for an unfinished screen — and declaring them is what keeps a later reader from banning mock comparison outright and throwing away the reference.

## Finish bar

- Lives in DESIGN.md §Do's and Don'ts as a `### Finish bar` subsection — hard visual rules, not a new spine section, so the canonical section order holds.
- **Elicit it, don't author it.** Ask what would make the user call a screen unfinished. Their rejections during this run are the best source — a scrapped panel, "this looks slapped together" — capture the wording and memlog the quote. Without it, the next session has no target.
- Every line judgeable from a screenshot alone and specific to this art direction: what an empty state must never be, the readability floor, how much of the frame the art must cover, what greybox looks like *here* (flat fills, default gaps, no depth, system font, unsized icons), which surfaces earn motion or juice.
- Weak: "polished, professional UI." Strong: "no empty slot is a flat rectangle of `{colors.ground}` — it shows the wood floor and the front lip."
- What isn't written here can't be asked for later: the finish story judges against this text and the approved capture, nothing else.
