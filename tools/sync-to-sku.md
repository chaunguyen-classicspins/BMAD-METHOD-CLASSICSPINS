# Syncing this fork into a SKU

This fork is the source of truth for the BMAD method in the ClassicSpins projects
("SKUs"). `tools/sync-to-sku.sh` pushes it into one.

The script lives **here**, in the source repo. A SKU copies nothing and holds no
sync script of its own, so onboarding a new project is one command with no
bootstrap step. It replaces the old `scripts/sync-bmad-from-fork.sh`, which lived
inside each SKU and hardcoded the fork's path.

## Usage

```bash
cd /Users/nc981/Working/ClassicSpins/BMAD-METHOD
tools/sync-to-sku.sh --root "/Users/nc981/Working/ClassicSpins/GoodsPuzzle 4"
```

`--root` names the project to sync into; it defaults to `$PWD`, and the script
refuses to run with the fork itself as the root. Useful flags:

| flag | effect |
| --- | --- |
| `--skills-only` | mirror skills, leave `Tools/bmad/` alone |
| `--tools-only` | mirror `Tools/bmad/` only; skips skills and `bmad doctor` |
| `--no-doctor` | mirror both channels, skip `bmad doctor` |
| `--codex-mirror <mode>` | what to publish to `.codex/skills/`: `bmad` (default), `all`, `none` |
| `--no-codex` | alias for `--codex-mirror none` |
| `--dry-run` | report what would change, write nothing |

`uv` is required — `bmad doctor` runs through it.

## The three channels

| source | destination in the SKU |
| --- | --- |
| this fork's `skills/*` | `<root>/.claude/skills/` |
| the SKU's `.claude/skills/*` | `<root>/.codex/skills/` (symlinks) |
| this fork's `tools/sku-tools/*` | `<root>/Tools/bmad/` |

Skills matching `bmad-loop-*` are skipped by the first channel: they come from a
different repo. A skill that exists in the SKU but not in the fork is never
deleted — that is how a SKU's non-bmad skills survive a sync.

After the channels are mirrored the script runs `bmad doctor` in the SKU to
reconcile `_bmad/scripts`.

On a SKU that consumes PrototypeFramework it then checks for `_bmad/custom/*.pf.toml` — the
framework's layer for the build skills, written by the framework's agent-doc sync only where `_bmad/`
already exists — and prints a NOTE to run `Framework/Agent Docs/Sync` when there is none (the usual
case for a SKU whose BMAD was installed after its Setup Wizard ran).

## `.codex/skills/` — the same method, for Codex CLI

Codex CLI discovers project skills under `<root>/.codex/skills/` (and
`<root>/.agents/skills/`). It does **not** read `.claude/skills/`, so a SKU that
only has the Claude Code layout gives a Codex session no BMAD skills at all.

The format itself needs no translation: a Codex skill is the same
`<name>/SKILL.md` folder with `name` and `description` frontmatter, which is
exactly what these skills already are. So the second channel publishes the tree
rather than converting it, as **relative symlinks** — `.codex/skills/bmad-build`
-> `../../.claude/skills/bmad-build`. One payload, two front doors, and no way
for the two catalogs to drift apart. Git stores the symlinks, so a teammate's
clone gets Codex support without running anything.

`--codex-mirror` chooses what is published:

- `bmad` (default) — every `bmad*` skill in `.claude/skills/`, `bmad-loop-*`
  included. Those are BMAD too, even though a different repo installs them.
- `all` — every skill directory in `.claude/skills/`, `pf-*` and the generated
  Unity MCP skills included. Worth knowing before you reach for it: a skill's
  name and description sit in the model's context from the start of every
  session, so mirroring ~130 skills costs context in exchange for reach.
- `none` (or `--no-codex`) — leave `.codex/skills/` alone entirely.

Switching mode is safe in both directions: links this channel owns (the ones
pointing at `../../.claude/skills/`) are pruned when they fall outside the
current mode or lose their target. Nothing else in the directory is touched — a
real skill directory the SKU keeps under `.codex/skills/`, or a symlink pointing
anywhere else, survives every sync.

The skills' own scripts resolve their skill root before reading anything under
it, so being entered through a symlink changes nothing at runtime, and
`bmad doctor` still finds its siblings.

### What does not carry over

The skills are portable; two things around them are not.

- **`.claude/settings.json` hooks** (the `bmad-loop` SessionStart/Stop hooks)
  are Claude Code's. Codex has its own hooks under `.codex/hooks`; the loop is
  installed separately and is not part of this sync.
- **Subagent wording.** Skills that fan work out to subagents describe Claude
  Code's Task tool. Codex has its own subagents, so the work still happens —
  the prose just names the wrong doorbell.

**`_bmad/custom/` has three owners.** The fork's `apply-story-sizing.sh` owns
`bmad-create-epics-and-stories.toml`; the PrototypeFramework agent-doc sync owns every
`<skill>.pf.toml` (the layer between a skill's shipped `customize.toml` and the SKU's
own file); the SKU owns everything else there. `sync-to-sku.sh` writes into
`_bmad/custom/` only by running `apply-story-sizing.sh` for that one file, and never
touches a `*.pf.toml` or a SKU-owned override.

## `tools/sku-tools/` — shared method tooling

Scripts here are method tooling, not fork tooling: they are useless inside this
repo and only do their job once they sit in a project. Edit them **here**; the
copy in a SKU is generated.

- `apply-story-sizing.sh` — installs the agent-loop planning law into
  `<root>/_bmad/custom/bmad-create-epics-and-stories.toml`. Takes the target
  directory as an argument, is idempotent, and refuses to overwrite a file that
  differs without `--force`.
- `measure-run.py` — measures the cost, turns, batching and context amplification
  of a BMAD run from its Claude Code transcript. Derives the project from the
  working directory; `--project <dir>` measures another one and `--where` shows
  how the transcript directory was resolved.

Every file distributed through this channel gets a provenance header stamped in
after its shebang, in the same shape the PrototypeFramework uses for its
generated `Tools/pf/*` files:

```
# GENERATED by BMAD fork 6.13.0-next from tools/sku-tools/measure-run.py — do not edit here. …
```

The stamp is worth the noise because the failure it prevents is silent: the SKU
copy looks like an ordinary editable script, and an edit made there is thrown
away without warning by the next sync. The stamp is inserted on copy and any
previous stamp is dropped first, so re-syncing never stacks them, and the fork's
own source files stay unstamped. `apply-story-sizing.sh` prints its usage by
scanning its header block rather than by line number, so the extra line does not
shift `--help`.

The version in the stamp is read from `skills/bmad/module-manifest.toml`.

## Adding a new tool to the channel

Drop an executable file in `tools/sku-tools/`. Nothing else is registered; the
next sync distributes it and preserves its executable bit.
