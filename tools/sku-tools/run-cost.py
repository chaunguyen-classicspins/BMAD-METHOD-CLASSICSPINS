#!/usr/bin/env python3
"""What one bmad-loop story run cost, in wall-clock and in tokens.

    python3 Tools/bmad/run-cost.py 7-1                 # by story number, newest matching run
    python3 Tools/bmad/run-cost.py 7-1-the-game-opens  # by slug prefix
    python3 Tools/bmad/run-cost.py --list              # every story run this machine still has

Why a tool and not a one-off analysis: a pipeline change is only worth anything if the *next* run is
measured the same way the baseline was, and re-deriving it by hand each time is how two runs end up
measured by two different definitions. `measure-run.py` beside this one measures ONE session and its
actors; this measures a whole story run and scores it against the project's baseline.

THE BASELINE IS THE PROJECT'S DATA, not this tool's. It is read from
`_bmad-output/implementation-artifacts/run-cost-baseline.json` (override: RUN_COST_BASELINE), written
by pasting what this script printed for the baseline story. Without one, the SCORECARD block is
skipped and everything else still prints. Hand-edited numbers silently invalidate every comparison.

WHERE THE DATA IS. Claude Code writes one JSONL transcript per session under the profile's own
config root — this project launches through `ccs classicspins`, so that root is
`~/.ccs/instances/classicspins`, NOT `~/.claude`. Subagent transcripts live in a sibling directory
named after the parent session id. Everything here is read-only.

WHAT IS MEASURED.
  * wall      — first to last timestamp across the whole session tree.
  * tool wait — result timestamp minus the timestamp of the assistant message that called the tool.
                Summed per class it OVERLAPS (parallel subagents, parallel tool blocks); the
                union figure is the honest wall-clock one and both are printed.
  * cost      — list API prices, applied to the usage block of every distinct assistant message.
                A session on a subscription is not billed this way; it is a comparable unit of
                work, and cache-read is what dominates it, which is the point.
"""

import argparse
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime

PROJECT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SLUG = re.sub(r"[^A-Za-z0-9]+", "-", PROJECT).rstrip("-")
ROOTS = sorted(glob.glob(os.path.expanduser("~/.ccs/instances/*/projects/" + SLUG))) + [
    os.path.expanduser("~/.claude/projects/" + SLUG)
]

# input $/M, output $/M, cache-write $/M, cache-read $/M
PRICE = {"opus": (15.0, 75.0, 18.75, 1.50),
         "sonnet": (3.0, 15.0, 3.75, 0.30),
         "haiku": (1.0, 5.0, 1.25, 0.10)}

# The project's baseline run, produced by THIS script at these definitions. Keys: story, wall_min,
# cost, sleep_s, unity_calls, unity_min, suites, gates, legs, longest_min, legs_union_min,
# cache_read_share. Re-baseline only by re-running this script on the baseline story.
BASELINE_PATH = os.environ.get("RUN_COST_BASELINE") or os.path.join(
    PROJECT, "_bmad-output", "implementation-artifacts", "run-cost-baseline.json")


def load_baseline():
    try:
        with open(BASELINE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def family(model):
    m = (model or "").lower()
    return next((k for k in PRICE if k in m), "opus")


def stamp(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def hhmm(t):
    return datetime.fromtimestamp(t).strftime("%H:%M")


def sessions():
    """Every main session transcript, newest first, with the story slug it ran."""
    out = []
    for root in ROOTS:
        for path in glob.glob(os.path.join(root, "*.jsonl")):
            slug = None
            with open(path, errors="replace") as fh:
                for i, line in enumerate(fh):
                    if i > 60:
                        break
                    m = re.search(r"command-args>([0-9]+-[0-9]+-[a-z0-9-]+)", line)
                    if m:
                        slug = m.group(1)
                        break
            if slug:
                out.append((os.path.getmtime(path), slug, path))
    return sorted(out, reverse=True)


def tree(main):
    """The main transcript plus every subagent transcript it spawned."""
    subs = sorted(glob.glob(os.path.join(main[:-6], "subagents", "*.jsonl")))
    return [("main", main)] + [(os.path.basename(p)[:-6], p) for p in subs]


# A command that RUNS the thing, not one that greps for its name: `grep -n gate.sh docs/*` is a
# 0.05 s read and must never land in the same bucket as a 96 s suite, or the scorecard counts
# reading about the gate as running it.
GATE_RUN = re.compile(r"(?:^|[;&|]\s*|\bpf-timeout\s+\d+\s+)(?:sh|bash)?\s*\S*gate\.sh\b")
SUITE_RUN = re.compile(r"run-tool\s+tests-run\b|^\s*tests-run\s*\{|\ntests-run\s*\{")


def bash_class(cmd):
    c = " ".join(cmd.split())
    if "pf-exec" in c:
        return "Bash: pf-exec (batched)"
    if "pf-mcp" in c or "unity-mcp-cli" in c:
        return "Bash: Unity (pf-mcp/cli)"
    if "pf-write" in c:
        return "Bash: pf-write"
    if GATE_RUN.search(c):
        return "Bash: gate.sh"
    if "dotnet test" in c:
        return "Bash: dotnet test"
    if re.search(r"dotnet build|typecheck", c):
        return "Bash: build/typecheck"
    if re.search(r"\bgit\b", c):
        return "Bash: git"
    if re.search(r"\b(rg|grep|find|ls)\b", c) and not re.search(r"\b(cat|sed -n|head|tail)\b", c):
        return "Bash: search"
    if re.search(r"\b(cat|head|tail|sed -n|jq)\b", c):
        return "Bash: read"
    if re.search(r"(<<'?EOF|>>|tee |sed -i|mv |cp |mkdir)", c):
        return "Bash: write via shell"
    return "Bash: other"


def collect(main):
    calls, usage, times = [], [], []
    for src, path in tree(main):
        pending = {}
        for line in open(path, errors="replace"):
            try:
                e = json.loads(line)
            except ValueError:
                continue
            ts = e.get("timestamp")
            if not ts:
                continue
            t = stamp(ts)
            times.append(t)
            msg = e.get("message") or {}
            body = msg.get("content")
            if e.get("type") == "assistant":
                if msg.get("usage"):
                    usage.append((src, msg.get("id"), msg.get("model"), msg["usage"]))
                for b in body if isinstance(body, list) else []:
                    if b.get("type") == "tool_use":
                        pending[b["id"]] = (b.get("name"), t, b.get("input") or {})
            elif e.get("type") == "user":
                for b in body if isinstance(body, list) else []:
                    if b.get("type") == "tool_result" and b.get("tool_use_id") in pending:
                        name, t0, inp = pending.pop(b["tool_use_id"])
                        payload = b.get("content")
                        calls.append(dict(
                            src=src, tool=name, t0=t0, t1=t, dur=t - t0,
                            size=len(payload if isinstance(payload, str) else json.dumps(payload or "")),
                            inp=inp))
        for name, t0, inp in pending.values():          # never answered (killed / aborted)
            calls.append(dict(src=src, tool=name, t0=t0, t1=None, dur=None, size=0, inp=inp))
    return calls, usage, (min(times), max(times))


def union(calls):
    """Wall-clock seconds in which at least one of these calls was running."""
    spans = sorted((c["t0"], c["t1"]) for c in calls if c["t1"])
    total, cur = 0.0, None
    for a, b in spans:
        if cur and a <= cur[1]:
            cur = (cur[0], max(cur[1], b))
        else:
            if cur:
                total += cur[1] - cur[0]
            cur = (a, b)
    return total + (cur[1] - cur[0] if cur else 0)


def classify(call):
    if call["tool"] == "Bash":
        return bash_class(call["inp"].get("command", ""))
    return call["tool"].replace("mcp__ai-game-developer__", "MCP: ")


def report(slug, path):
    calls, usage, (t0, t1) = collect(path)
    wall = t1 - t0
    answered = [c for c in calls if c["dur"] is not None]

    print(f"\n{'=' * 78}\n  {slug}\n  {path}\n{'=' * 78}")
    print(f"  {hhmm(t0)} -> {hhmm(t1)}   wall {wall / 60:.1f} min"
          f"   |  {len(calls)} tool calls  |  {len(set((s, i) for s, i, _, _ in usage))} model turns")

    # --- cost -----------------------------------------------------------------------------------
    seen, tok, cost_of = set(), defaultdict(lambda: [0, 0, 0, 0]), defaultdict(float)
    for src, mid, model, u in usage:
        if mid and (src, mid) in seen:
            continue
        seen.add((src, mid))
        fam = family(model)
        vals = (u.get("input_tokens", 0), u.get("output_tokens", 0),
                u.get("cache_creation_input_tokens", 0), u.get("cache_read_input_tokens", 0))
        for i, v in enumerate(vals):
            tok[fam][i] += v
        cost_of[src] += sum(v * p for v, p in zip(vals, PRICE[fam])) / 1e6

    total = sum(cost_of.values())
    print(f"\n  COST (list API prices)                                    ${total:,.2f}")
    print(f"    {'':14s}{'input':>12s}{'output':>12s}{'cache write':>14s}{'cache read':>14s}{'$':>10s}")
    for fam, (i, o, cw, cr) in tok.items():
        p = PRICE[fam]
        c = (i * p[0] + o * p[1] + cw * p[2] + cr * p[3]) / 1e6
        print(f"    {fam:14s}{i:12,d}{o:12,d}{cw:14,d}{cr:14,d}{c:10.2f}")
    opus = tok.get("opus", [0, 0, 0, 0])
    share = opus[3] * PRICE["opus"][3] / 1e6 / total if total else 0.0
    print(f"    cache read is {share:.0%} of spend   ({opus[3] / 1e6:.1f}M tokens re-sent)")
    print(f"    orchestrator ${cost_of.get('main', 0):,.2f}"
          f"  |  subagents ${total - cost_of.get('main', 0):,.2f}")

    # --- tool classes ---------------------------------------------------------------------------
    per = defaultdict(list)
    for c in answered:
        per[classify(c)].append(c)
    print(f"\n  TOOL CLASSES                     n     total_s    %wall   median      max")
    for name, group in sorted(per.items(), key=lambda kv: -sum(c["dur"] for c in kv[1])):
        ds = sorted(c["dur"] for c in group)
        s = sum(ds)
        print(f"    {name:28s}{len(ds):5d}{s:12.1f}{100 * s / wall:8.1f}%"
              f"{ds[len(ds) // 2]:9.1f}{ds[-1]:9.1f}")

    mainc = [c for c in answered if c["src"] == "main"]
    print(f"\n    orchestrator waited on tools {union(mainc) / 60:.1f} min of {wall / 60:.1f} min"
          f"  ({100 * union(mainc) / wall:.0f}%)")

    # --- the four counters the changelog is scored on -------------------------------------------
    sleeps = sum(int(m.group(1))
                 for c in calls
                 for m in re.finditer(r"\bsleep\s+(\d+)", c["inp"].get("command", "")))
    unity = [c for c in answered if classify(c) in ("Bash: Unity (pf-mcp/cli)",) or c["tool"].startswith("mcp__")]
    gates = [c for c in answered if classify(c) == "Bash: gate.sh"]
    # One "invocation" is one EditMode suite actually asked for: a direct MCP call, or one
    # `tests-run {…}` item inside a pf-mcp heredoc (a batch of three items is three).
    suites = [c for c in calls if c["tool"].endswith("tests-run")]
    suites += [c for c in calls for _ in SUITE_RUN.findall(c["inp"].get("command", ""))]
    agents = [c for c in answered if c["tool"] == "Agent"]
    b = load_baseline()
    unity_min = sum(c["dur"] for c in unity) / 60
    longest = max((c["dur"] for c in agents), default=0) / 60
    if not b:
        print(f"\n  SCORECARD skipped: no baseline at {os.path.relpath(BASELINE_PATH, PROJECT)}")
    else:
        rows = [("wall", wall / 60, b["wall_min"], "min"),
                ("cost", total, b["cost"], "$"),
                ("cache read share of cost", share * 100 if total else 0,
                 b["cache_read_share"] * 100, "%"),
                ("hand-written sleep", sleeps, b["sleep_s"], "s"),
                ("Unity round trips", len(unity), b["unity_calls"], "calls"),
                ("  their wall", unity_min, b["unity_min"], "min"),
                ("tests-run invocations", len(suites), b["suites"], ""),
                ("gate.sh runs", len(gates), b["gates"], ""),
                ("subagent legs", len(agents), b["legs"], ""),
                ("  longest leg", longest, b["longest_min"], "min"),
                ("  their wall (union)", union(agents) / 60, b["legs_union_min"], "min")]
        print(f"\n  SCORECARD vs. story {b['story']}   (definitions: optimize-changelog.md)")
        print(f"    {'':26s}{'this run':>12s}{'baseline':>12s}{'delta':>12s}")
        for label, now, was, unit in rows:
            d = now - was
            pct = f"{100 * d / was:+.0f}%" if was else "  n/a"
            print(f"    {label:26s}{now:12.1f}{was:12.1f}{pct:>8s} {unit}")
        if slug.startswith(b["story"]):
            print("    (this IS the baseline run — deltas must read 0)")

    if agents:
        print(f"\n  SUBAGENT LEGS")
        for c in sorted(agents, key=lambda c: c["t0"]):
            print(f"    {hhmm(c['t0'])}  {c['dur'] / 60:6.1f} min   "
                  f"{(c['inp'].get('description') or '?')[:44]}")

    repeats = Counter(classify(c) for c in calls)
    top = repeats.most_common(1)[0]
    print(f"\n  most-called class: {top[0]} ({top[1]}/{len(calls)} = {100 * top[1] / len(calls):.0f}%)")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("story", nargs="?", help="story number or slug prefix, e.g. 7-1")
    ap.add_argument("--list", action="store_true", help="list the story runs on this machine")
    a = ap.parse_args()

    found = sessions()
    if not found:
        sys.exit(f"run-cost: no story transcripts under any of:\n  " + "\n  ".join(ROOTS))
    if a.list or not a.story:
        for mtime, slug, path in found:
            print(f"{datetime.fromtimestamp(mtime):%Y-%m-%d %H:%M}  {slug}")
        return 0

    hits = [f for f in found if f[1].startswith(a.story)]
    if not hits:
        sys.exit(f"run-cost: no run matching '{a.story}'. Try --list.")
    report(hits[0][1], hits[0][2])
    return 0


if __name__ == "__main__":
    sys.exit(main())
