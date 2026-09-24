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

# One price table for every bmad-loop cost tool: claude_prices.py beside this file.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import claude_prices  # noqa: E402

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


def stamp(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def hhmm(t):
    return datetime.fromtimestamp(t).strftime("%H:%M")


STORY_COMMAND = re.compile(r"<command-name>/?bmad-(?:build|dev)-auto</command-name>")
STORY_ARGS = re.compile(r"<command-args>([0-9]+-[0-9]+-[a-z0-9-]+)")
# A resumed run (`/bmad-build-auto Resume review of the in-review spec at …/spec-<slug>.md`) names
# its story only through the spec path.
STORY_SPEC = re.compile(r"<command-args>[^<]*?spec-([0-9]+-[0-9]+-[a-z0-9-]+?)\.md")


def invoked_story(line):
    """The story a session was STARTED on: the slug in its own `/bmad-build-auto <slug>` prompt.

    Only a user prompt counts — a string, not a tool result. A session that merely READ another
    run's transcript carries the same `<command-args>…` text inside a tool result, and matching the
    raw line once made an unrelated chat session pass for that story's run.
    """
    try:
        entry = json.loads(line)
    except ValueError:
        return None
    if entry.get("type") != "user":
        return None
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, list):
        content = "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    if not isinstance(content, str) or not STORY_COMMAND.search(content):
        return None
    m = STORY_ARGS.search(content) or STORY_SPEC.search(content)
    return m.group(1) if m else None


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
                    slug = invoked_story(line)
                    if slug:
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


def tree_cost(path):
    """List-price USD of one session tree (main + subagents), final streamed entry per message."""
    _, usage, (t0, t1) = collect(path)
    final = {}
    for n, (src, mid, model, u) in enumerate(usage):
        key = (src, mid) if mid else (src, n)
        if key not in final or (u.get("output_tokens") or 0) >= (final[key][3].get("output_tokens") or 0):
            final[key] = (src, mid, model, u)
    return sum(claude_prices.cost(m, u) or 0.0 for _, _, m, u in final.values()), t0, t1


def report(slug, path):
    calls, usage, (t0, t1) = collect(path)
    wall = t1 - t0
    answered = [c for c in calls if c["dur"] is not None]

    print(f"\n{'=' * 78}\n  {slug}\n  {path}\n{'=' * 78}")
    print(f"  {hhmm(t0)} -> {hhmm(t1)}   wall {wall / 60:.1f} min"
          f"   |  {len(calls)} tool calls  |  {len(set((s, i) for s, i, _, _ in usage))} model turns")

    # --- cost -----------------------------------------------------------------------------------
    tok, cost_of = defaultdict(lambda: [0, 0, 0, 0, 0.0]), defaultdict(float)
    unpriced, read_cost = Counter(), 0.0
    # One assistant message is streamed as several transcript entries that all carry a usage
    # block. In a subagent transcript the FIRST one holds a partial output count (measured: 15k of
    # a leg's 224k output tokens), so keep the entry with the largest output, never the first.
    final = {}
    for n, (src, mid, model, u) in enumerate(usage):
        key = (src, mid) if mid else (src, n)
        if key not in final or (u.get("output_tokens") or 0) >= (final[key][3].get("output_tokens") or 0):
            final[key] = (src, mid, model, u)
    for src, mid, model, u in final.values():
        i, o, w5, w1, cr = claude_prices.split(u)
        c = claude_prices.cost(model, u)
        if c is None:
            if i + o + w5 + w1 + cr:
                unpriced[model or "?"] += i + o + w5 + w1 + cr
            continue
        key = claude_prices.rate(model)[0]
        for k, v in enumerate((i, o, w5 + w1, cr)):
            tok[key][k] += v
        tok[key][4] += c
        cost_of[src] += c
        read_cost += claude_prices.cache_read_cost(model, u)

    total = sum(cost_of.values())
    print(f"\n  COST (list API prices)                                    ${total:,.2f}")
    print(f"    {'':18s}{'input':>11s}{'output':>11s}{'cache write':>14s}{'cache read':>14s}{'$':>10s}")
    for key, (i, o, cw, cr, c) in sorted(tok.items(), key=lambda kv: -kv[1][4]):
        print(f"    {key:18s}{i:11,d}{o:11,d}{cw:14,d}{cr:14,d}{c:10.2f}")
    for model, n in unpriced.items():
        print(f"    UNPRICED {model}: {n:,d} tokens left out of the total — add it to claude_prices.py")
    share = read_cost / total if total else 0.0
    reread = sum(v[3] for v in tok.values())
    print(f"    cache read is {share:.0%} of spend   ({reread / 1e6:.1f}M tokens re-sent)")
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
    # A story that paused (an escalation) and resumed ran in more than one session. The report
    # above is the newest one; the story's total is every session that ran it.
    same = [f for f in hits if f[1] == hits[0][1]]
    if len(same) > 1:
        print(f"\n  THIS STORY RAN IN {len(same)} SESSIONS (the report above is the newest)")
        total = 0.0
        for _, _, path in sorted(same):
            c, t0, t1 = tree_cost(path)
            total += c
            print(f"    {datetime.fromtimestamp(t0):%m-%d %H:%M} -> {datetime.fromtimestamp(t1):%H:%M}"
                  f"   wall {(t1 - t0) / 60:6.1f} min   ${c:8.2f}   {os.path.basename(path)[:8]}")
        print(f"    story total ${total:,.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
