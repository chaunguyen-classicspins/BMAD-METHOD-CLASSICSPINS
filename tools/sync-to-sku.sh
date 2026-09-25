#!/usr/bin/env bash
#
# sync-to-sku.sh — push this fork's BMAD skills and shared tools into a consuming
# project (a "SKU"), then run `bmad doctor` there to reconcile `_bmad/scripts`.
#
# The script lives in the SOURCE repo, not in the consumer: a new SKU copies
# nothing. You `cd` into this fork and point the script at the target.
#
# Three channels, one run:
#   skills/*          ->  <root>/.claude/skills/      (bmad-loop-* excluded)
#   .claude/skills/*  ->  <root>/.codex/skills/       (symlinks, for Codex CLI)
#   tools/sku-tools/* ->  <root>/Tools/bmad/          (stamped as generated)
#
# Skills present in the SKU but absent from the fork are left alone — that is how
# non-bmad skills and the separately-managed bmad-loop-* skills survive a sync.
#
# Codex CLI reads project skills from <root>/.codex/skills/ and does NOT look in
# .claude/skills/, so the same skill tree is published there as relative symlinks
# rather than copied: one payload, two front doors, no drift between them. Only
# symlinks that point back into .claude/skills/ are ever removed, so a real skill
# directory a SKU keeps under .codex/skills/ survives a sync untouched.
#
# Usage:
#   tools/sync-to-sku.sh --root <path-to-sku>
#   tools/sync-to-sku.sh                        # --root defaults to $PWD
#
#   --root <path>          the project to sync into (default: the current directory)
#   --skills-only          mirror skills, skip Tools/bmad
#   --tools-only           mirror Tools/bmad, skip skills and `bmad doctor`
#   --codex-only           only publish .codex/skills from what the SKU already has
#   --no-doctor            mirror everything, skip `bmad doctor`
#   --codex-mirror <mode>  what to publish to .codex/skills: bmad (default, every
#                          bmad* skill including the separately-managed bmad-loop-*),
#                          all (every skill in .claude/skills), or none
#   --no-codex             alias for --codex-mirror none
#   --dry-run              report what would change, write nothing
#   -h, --help             this text
#
set -euo pipefail

FORK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FORK_SKILLS="$FORK_ROOT/skills"
FORK_TOOLS="$FORK_ROOT/tools/sku-tools"

ROOT=""
DO_SKILLS=1
DO_TOOLS=1
DO_DOCTOR=1
DO_CODEX=1
CODEX_ONLY=0
CODEX_MIRROR="bmad"
DRY=0

usage() { awk 'NR==1{next} /^set -euo/{exit} /^#/{sub(/^# ?/,""); print}' "$0"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --root)        shift; [ $# -gt 0 ] || { echo "error: --root needs a path" >&2; exit 2; }; ROOT="$1" ;;
    --root=*)      ROOT="${1#--root=}" ;;
    --skills-only) DO_TOOLS=0 ;;
    --tools-only)  DO_SKILLS=0; DO_DOCTOR=0; DO_CODEX=0 ;;
    --codex-only)  CODEX_ONLY=1 ;;
    --no-doctor)   DO_DOCTOR=0 ;;
    --codex-mirror)   shift; [ $# -gt 0 ] || { echo "error: --codex-mirror needs a mode" >&2; exit 2; }; CODEX_MIRROR="$1" ;;
    --codex-mirror=*) CODEX_MIRROR="${1#--codex-mirror=}" ;;
    --no-codex)    CODEX_MIRROR="none" ;;
    --dry-run)     DRY=1 ;;
    -h|--help)     usage; exit 0 ;;
    *)             echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

# --codex-only wins over the other channel switches; a `none` mirror wins over
# everything, including --codex-only, which then has nothing left to do.
if [ "$CODEX_ONLY" = "1" ]; then
  DO_SKILLS=0
  DO_TOOLS=0
  DO_DOCTOR=0
  DO_CODEX=1
fi
if [ "$CODEX_MIRROR" = "none" ]; then DO_CODEX=0; fi

case "$CODEX_MIRROR" in
  bmad|all|none) ;;
  *) echo "error: --codex-mirror must be bmad, all or none (got: $CODEX_MIRROR)" >&2; exit 2 ;;
esac

ROOT="${ROOT:-$PWD}"
[ -d "$ROOT" ] || { echo "error: --root is not a directory: $ROOT" >&2; exit 1; }
ROOT="$(cd "$ROOT" && pwd)"

if [ "$ROOT" = "$FORK_ROOT" ]; then
  echo "error: --root is the fork itself ($FORK_ROOT)." >&2
  echo "       Pass the SKU you want to sync into: --root <path-to-sku>" >&2
  exit 1
fi

[ -d "$FORK_SKILLS" ] || { echo "error: fork skills directory not found: $FORK_SKILLS" >&2; exit 1; }

if ! command -v uv >/dev/null 2>&1; then
  echo "error: uv is required (https://docs.astral.sh/uv/)" >&2
  exit 1
fi

VERSION="$(sed -n 's/^version = "\(.*\)"/\1/p' "$FORK_SKILLS/bmad/module-manifest.toml" 2>/dev/null | head -1)"
VERSION="${VERSION:-unknown}"

echo "==> BMAD fork sync"
echo "    fork:    $FORK_ROOT  (version $VERSION)"
echo "    root:    $ROOT"
[ "$DRY" = "1" ] && echo "    MODE:    dry run, nothing is written"

SKILLS_DIR="$ROOT/.claude/skills"
CODEX_DIR="$ROOT/.codex/skills"
TOOLS_DIR="$ROOT/Tools/bmad"

# ---------------------------------------------------------------- skills ----
copied=0
skipped=0
if [ "$DO_SKILLS" = "1" ]; then
  echo ""
  echo "==> skills  $FORK_SKILLS -> $SKILLS_DIR"
  [ "$DRY" = "1" ] || mkdir -p "$SKILLS_DIR"
  for src in "$FORK_SKILLS"/*/; do
    name="$(basename "$src")"

    # Never touch bmad-loop-* — those come from a different external repo.
    if [[ "$name" == bmad-loop-* ]]; then
      skipped=$((skipped + 1))
      echo "    skip:   $name (bmad-loop-* is managed separately)"
      continue
    fi

    target="$SKILLS_DIR/$name"
    if [ "$DRY" = "0" ]; then
      rm -rf "$target"
      cp -R "$src" "$target"
    fi
    copied=$((copied + 1))
    echo "    synced: $name"
  done
  echo "==> $copied skill(s) synced, $skipped skipped"
fi

# ----------------------------------------------------------------- codex ----
# Codex CLI discovers project skills under <root>/.codex/skills/ and never looks
# at .claude/skills/, so the tree is published there a second time. Symlinks, not
# copies: a copy would be a second payload to keep in step, and the two would
# drift the first time anything wrote to one of them. Each link is relative, so
# it survives the project being moved or cloned elsewhere.
codex_linked=0
codex_pruned=0
if [ "$DO_CODEX" = "1" ]; then
  echo ""
  echo "==> codex   $SKILLS_DIR -> $CODEX_DIR  (mirror: $CODEX_MIRROR)"

  # Which skills belong in the Codex catalog. `bmad` keeps it to the method
  # itself — bmad-loop-* included, since those are BMAD too even though a
  # different repo owns them. `all` publishes whatever else the SKU installed.
  selected=""
  if [ -d "$SKILLS_DIR" ]; then
    for skill in "$SKILLS_DIR"/*/; do
      [ -d "$skill" ] || continue
      name="$(basename "$skill")"
      if [ "$CODEX_MIRROR" = "bmad" ]; then
        case "$name" in
          bmad|bmad-*) ;;
          *) continue ;;
        esac
      fi
      selected="$selected$name
"
    done
  fi

  if [ -z "$selected" ]; then
    echo "    note: no skills in $SKILLS_DIR match the mirror — nothing to publish"
  else
    [ "$DRY" = "1" ] || mkdir -p "$CODEX_DIR"
    while IFS= read -r name; do
      [ -n "$name" ] || continue
      link="$CODEX_DIR/$name"
      target="../../.claude/skills/$name"

      # A real directory here is the SKU's own Codex-only skill. Never clobber it.
      if [ -e "$link" ] && [ ! -L "$link" ]; then
        echo "    keep:   $name (not a symlink — left as the SKU has it)"
        continue
      fi
      if [ "$DRY" = "0" ]; then
        ln -snf "$target" "$link"
      fi
      codex_linked=$((codex_linked + 1))
      echo "    linked: $name"
    done <<EOF
$selected
EOF
  fi

  # Drop links we own that no longer name a skill — a skill dropped from the
  # fork, or one the current mirror mode excludes. Anything else in the
  # directory is somebody else's and is left where it is.
  if [ -d "$CODEX_DIR" ]; then
    for link in "$CODEX_DIR"/*; do
      [ -L "$link" ] || continue
      name="$(basename "$link")"
      dest="$(readlink "$link")"
      case "$dest" in
        ../../.claude/skills/*) ;;
        *) continue ;;
      esac
      if printf '%s' "$selected" | grep -qxF "$name"; then
        continue
      fi
      [ "$DRY" = "0" ] && rm -f "$link"
      codex_pruned=$((codex_pruned + 1))
      echo "    pruned: $name"
    done
  fi
  echo "==> $codex_linked skill(s) published to Codex, $codex_pruned pruned"
fi

# ------------------------------------------------------------- sku tools ----
# Stamp every distributed tool with a provenance header, in the same shape the
# PrototypeFramework uses for its generated Tools/pf/* files: the copy in the SKU
# has a source of truth elsewhere, and an edit made here is silently thrown away
# by the next sync. The stamp is inserted after the shebang and any previous
# stamp is dropped first, so re-running is idempotent.
tools_copied=0
if [ "$DO_TOOLS" = "1" ]; then
  echo ""
  echo "==> tools   $FORK_TOOLS -> $TOOLS_DIR"
  if [ ! -d "$FORK_TOOLS" ]; then
    echo "    note: $FORK_TOOLS does not exist — nothing to distribute"
  else
    [ "$DRY" = "1" ] || mkdir -p "$TOOLS_DIR"
    for src in "$FORK_TOOLS"/*; do
      [ -f "$src" ] || continue
      name="$(basename "$src")"
      dest="$TOOLS_DIR/$name"
      stamp="# GENERATED by BMAD fork $VERSION from tools/sku-tools/$name — do not edit here. Change it in the fork ($FORK_ROOT), then re-run tools/sync-to-sku.sh --root '$ROOT'"
      if [ "$DRY" = "0" ]; then
        awk -v stamp="$stamp" '
          NR==1 && /^#!/ { print; print stamp; next }
          NR<=2 && /^# GENERATED by BMAD fork/ { next }
          { print }
        ' "$src" > "$dest.tmp$$"
        # Keep the source bit-for-bit executable status.
        if [ -x "$src" ]; then chmod +x "$dest.tmp$$"; else chmod -x "$dest.tmp$$"; fi
        mv -f "$dest.tmp$$" "$dest"
      fi
      tools_copied=$((tools_copied + 1))
      echo "    synced: $name"
    done
    echo "==> $tools_copied tool(s) synced"
  fi
fi

# ----------------------------------------------------------------- doctor ----
if [ "$DO_DOCTOR" = "1" ] && [ "$DRY" = "0" ]; then
  BMAD_SKILL="$SKILLS_DIR/bmad"
  if [ ! -f "$BMAD_SKILL/scripts/setup.py" ]; then
    echo "error: bmad skill missing after sync at $BMAD_SKILL" >&2
    exit 1
  fi

  echo ""
  echo "==> Running \`bmad doctor\` to reconcile _bmad/scripts"
  uv run --no-cache "$BMAD_SKILL/scripts/setup.py" \
    --project-root "$ROOT" \
    --skill "$BMAD_SKILL" \
    --doctor
fi

# ------------------------------------------------------- planning law ----
# apply-story-sizing.sh writes _bmad/custom/bmad-create-epics-and-stories.toml,
# which has no project-specific content at all — it is generated, not authored.
# So run it here rather than leaving a step for a human to forget. It refuses to
# overwrite a file that differs from what it would write, which is exactly the
# behaviour we want: a SKU that has edited its own copy keeps it, and says so.
if [ "$DO_TOOLS" = "1" ] && [ "$DRY" = "0" ]; then
  LAW="$TOOLS_DIR/apply-story-sizing.sh"
  if [ -x "$LAW" ]; then
    echo ""
    echo "==> Installing the planning law"
    if "$LAW" "$ROOT" >/dev/null 2>&1; then
      echo "    _bmad/custom/bmad-create-epics-and-stories.toml is current"
    else
      echo "    SKIPPED — this SKU's copy differs from the fork's. Yours is kept."
      echo "    Compare, then re-run with --force if the fork's should win:"
      echo "      \"$LAW\" --print | diff - \"$ROOT/_bmad/custom/bmad-create-epics-and-stories.toml\""
    fi
  fi
fi

# ---------------------------------------------- PrototypeFramework layer ----
# A SKU on PrototypeFramework gets the framework's facts and lenses for the build skills as
# _bmad/custom/<skill>.pf.toml, written by the framework's agent-doc sync — not by this script. That
# sync only writes them where _bmad/ exists, so a SKU whose BMAD was installed AFTER the Setup Wizard
# ran has none until someone re-syncs. Say so rather than let the build skills run without them.
if [ -f "$ROOT/Packages/manifest.json" ] && grep -q '"com.classicspins.prototype-framework"' "$ROOT/Packages/manifest.json" \
   && ! ls "$ROOT"/_bmad/custom/*.pf.toml >/dev/null 2>&1; then
  echo ""
  echo "==> NOTE: this SKU consumes PrototypeFramework but has no _bmad/custom/*.pf.toml yet."
  echo "    Run Framework/Agent Docs/Sync in the Editor (or the framework's pf-build.sh agentdocs)"
  echo "    so the build skills get the framework's facts and the visual-gate lens."
fi

echo ""
echo "==> Sync complete"
