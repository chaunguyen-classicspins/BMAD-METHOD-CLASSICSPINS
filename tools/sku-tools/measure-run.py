#!/usr/bin/env python3
"""Đo một dev session của bmad-loop: cost thật + per-actor + calls/turn.

Usage:
  measure-run.py [SESSION]            SESSION = a transcript path, or a session-id prefix,
                                      or nothing (newest session of THIS project wins)
  measure-run.py --project <dir>      measure another project instead of the cwd's
  measure-run.py --slug <slug>        pin the transcript directory name directly
  measure-run.py --where              print how the project/transcript dir was resolved, then exit

The project is derived from the working directory: Claude Code stores a session
under a directory named after the project's absolute path with every character
outside [A-Za-z0-9] replaced by '-'. So
  /Users/me/Working/Goods Puzzle 3  ->  -Users-me-Working-Goods-Puzzle-3
Never hardcode that slug: a copy of this file in another SKU would then silently
measure the first SKU's sessions and report numbers that look perfectly fine.
"""
import json, sys, glob, os, re, collections, subprocess

# Transcripts live under a ccs instance (bmad-loop runs) or ~/.claude (a direct
# `claude` session running the skill by hand). Search both; newest wins.
CCS_BASES = sorted(glob.glob(os.path.expanduser("~/.ccs/instances/*/projects")))
ALL_BASES = CCS_BASES + [os.path.expanduser("~/.claude/projects")]


def slugify(path):
    """Claude Code's project-directory name for an absolute path."""
    return re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(path))


def transcript_dirs(slug):
    return [d for d in (os.path.join(b, slug) for b in ALL_BASES) if os.path.isdir(d)]


def git_toplevel(start):
    try:
        out = subprocess.run(["git", "-C", start, "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or None if out.returncode == 0 else None
    except Exception:
        return None


def find_project(explicit=None):
    """The project root whose transcripts we should read, and its slug.

    An explicit --project wins. Otherwise: the session may have been started at
    the repo root or at a subdirectory of it, so try the cwd, then each ancestor
    UP TO AND INCLUDING the git toplevel, and take the first that has transcripts.
    The walk never leaves the repo — climbing further would silently measure a
    parent directory's sessions (or a sibling project's) instead of admitting that
    this project has none yet.
    """
    if explicit:
        root = os.path.realpath(explicit)
        return root, slugify(root)
    cwd = os.path.realpath(os.getcwd())
    top = git_toplevel(cwd)
    top = os.path.realpath(top) if top else None

    candidates, d = [], cwd
    while True:
        candidates.append(d)
        if top is None or d == top or os.path.dirname(d) == d:
            break
        d = os.path.dirname(d)

    for c in candidates:
        if transcript_dirs(slugify(c)):
            return c, slugify(c)
    root = top or cwd
    return root, slugify(root)


ARGV = sys.argv[1:]
OPT_PROJECT = OPT_SLUG = None
WHERE = False
POS = []
i = 0
while i < len(ARGV):
    a = ARGV[i]
    if a in ("-h", "--help"):
        sys.exit(__doc__)
    elif a == "--where":
        WHERE = True
    elif a == "--project":
        i += 1; OPT_PROJECT = ARGV[i]
    elif a == "--slug":
        i += 1; OPT_SLUG = ARGV[i]
    elif a.startswith("--"):
        sys.exit(f"unknown option {a!r}\n\n{__doc__}")
    else:
        POS.append(a)
    i += 1
if len(POS) > 1:
    sys.exit(f"too many arguments: {POS}\n\n{__doc__}")

if OPT_SLUG:
    PROJECT, SLUG = None, OPT_SLUG
else:
    PROJECT, SLUG = find_project(OPT_PROJECT)
BASES = transcript_dirs(SLUG)

if WHERE:
    print(f"cwd:      {os.path.realpath(os.getcwd())}")
    print(f"project:  {PROJECT or '(pinned by --slug)'}")
    print(f"slug:     {SLUG}")
    if not BASES:
        print("transcript dirs: NONE — no session has been recorded for this project")
        for b in ALL_BASES:
            print(f"    miss: {os.path.join(b, SLUG)}")
    for b in BASES:
        n = len(glob.glob(b + "/*.jsonl"))
        newest = max(glob.glob(b + "/*.jsonl"), key=os.path.getmtime, default=None)
        print(f"    hit:  {b}  ({n} transcripts, newest {os.path.basename(newest or '-')})")
    sys.exit(0)


def resolve(arg):
    """A path, or a bare session id, or nothing (newest session wins)."""
    if arg and os.path.exists(arg):
        return arg
    pool = [f for b in BASES for f in glob.glob(b + "/*.jsonl")]
    if not pool:
        sys.exit(f"no transcripts for project {PROJECT or SLUG!r}\n"
                 f"  slug: {SLUG}\n"
                 f"  looked in: " + ", ".join(os.path.join(b, SLUG) for b in ALL_BASES) + "\n"
                 f"  (measure another project with --project <dir>, or pin one with --slug)")
    if arg:
        hit = [f for f in pool if os.path.basename(f).startswith(arg)]
        if not hit:
            sys.exit(f"no transcript matches {arg!r} in project {PROJECT or SLUG!r}")
        return max(hit, key=os.path.getmtime)
    return max(pool, key=os.path.getmtime)


SESS = resolve(POS[0] if POS else None)
# One price table for every bmad-loop cost tool. The old exact-id dict priced `claude-opus-5-5`
# (and every model it did not list) at ZERO, so an Opus 5.5 session measured as free.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import claude_prices  # noqa: E402
UNPRICED = collections.Counter()

def scan(path):
    order, msg = [], {}
    for line in open(path):
        try: d = json.loads(line)
        except: continue
        if d.get('type') == 'cost-state': msg['__cost__'] = d
        if d.get('type') != 'assistant': continue
        m = d['message']; mid = m['id']; u = m['usage']
        # A message is streamed as several entries; a subagent's FIRST one carries a partial output
        # count, so price the entry with the largest output (the final one), not the first.
        out = u.get('output_tokens', 0) or 0
        if mid not in msg or out >= msg[mid]['_out']:
            if mid not in msg:
                order.append(mid)
            c = claude_prices.cost(m.get('model'), u)
            prev = msg.get(mid, {})
            msg[mid] = dict(
                ctx=u.get('input_tokens', 0) + u.get('cache_read_input_tokens', 0) + u.get('cache_creation_input_tokens', 0),
                cost=c or 0.0, _out=out, _unpriced=(m.get('model') or '?') if c is None else None,
                _n=sum(claude_prices.split(u)), tools=prev.get('tools', []), cmds=prev.get('cmds', []))
        msg[mid]['tools'] += [p['name'] for p in m.get('content', []) if p.get('type') == 'tool_use']
        msg[mid]['cmds'] += [str(p['input'].get('command', p['input'].get('file_path', '')))
                             for p in m.get('content', []) if p.get('type') == 'tool_use']
    for m in order:
        if msg[m]['_unpriced'] and msg[m]['_n']:
            UNPRICED[msg[m]['_unpriced']] += msg[m]['_n']
    return [msg[m] for m in order], msg.get('__cost__')

RO = re.compile(r"^\s*(cd [^&|;]*&&\s*)?(grep|rg|sed -n|cat |ls |head |tail |wc |find |awk|shasum|git (log|diff|status|show)|echo )")
RW = ("dotnet test", "unity-mcp-cli", ">>", "sleep", "git add", "git commit", "sed -i")


def segments(t):
    """Split a turn list at context resets (a new leg, or a compaction)."""
    out, cur = [], [0]
    for i in range(1, len(t)):
        if t[i]['ctx'] < t[i - 1]['ctx'] - 50_000:
            out.append(cur); cur = []
        cur.append(i)
    out.append(cur)
    return out


def amplification(t):
    """billed input / content that ever entered context. 1x is the floor."""
    uniq = 0
    for seg in segments(t):
        uniq += t[seg[0]]['ctx'] + sum(max(0, t[seg[i]]['ctx'] - t[seg[i - 1]]['ctx'])
                                       for i in range(1, len(seg)))
    billed = sum(x['ctx'] for x in t)
    return billed / max(uniq, 1)


def read_only(x):
    """A turn that only inspects: it could have shared a message with its neighbours."""
    if not x['tools']:
        return False
    if all(n == 'Read' for n in x['tools']):
        return True
    if not all(n == 'Bash' for n in x['tools']):
        return False
    return all(RO.match(c) and not any(k in c for k in RW) for c in x['cmds'])


# --- shell-level batching -------------------------------------------------
# A turn is one tool call, but `a && b && c` is three inspections and
# `sed -n '1,5p;40,60p'` is two. `multi-call` counts CALLS and is blind to both:
# measured on story 1.1, MAIN scored 2% multi-call while actually running 2.19
# inspections per call — the best of any actor in that session. Counting calls
# alone therefore reports a good batcher as a trickler and inflates headroom.

OP = re.compile(r"^\s*(grep|rg|sed|cat|ls|head|tail|wc|find|awk|nl|jq|stat|diff|git)\b")
RANGE = re.compile(r"\d+,\d+p")
# A batched-inspection call carries its items in a heredoc, so the items never
# appear at the start of a segment and OP cannot see them. Counting such a call
# as one inspection under-reports exactly the tool this metric exists to reward.
PROBE_ITEM = re.compile(r"^\s*[\w.\-/]+\s*:\s*\S")           # pf-exec:  `label : command`
EXEC_NAMES = ('pf-exec', 'pf-probe')   # pf-probe is the pre-rename name, still shimmed
MCP_ITEM = re.compile(r"^\s*[a-z][a-z0-9-]*\s+\{")              # pf-mcp:   `tool-name {json}`


def batched_items(c):
    """Items inside a pf-exec / pf-mcp heredoc, or 0 when this is not one."""
    if any(n in c for n in EXEC_NAMES):
        return sum(1 for ln in c.splitlines() if PROBE_ITEM.match(ln))
    if 'pf-mcp' in c:
        return sum(1 for ln in c.splitlines() if MCP_ITEM.match(ln))
    return 0


def split_cmd(c):
    """Top-level `&&`, `||`, `;` and newline separators, ignoring quoted text.

    Pipes are deliberately NOT separators: `cat x | grep y` is one inspection
    that reduces in the shell, which is the behaviour we want to reward.
    """
    out, cur, quote, i = [], [], None, 0
    while i < len(c):
        ch = c[i]
        if quote:
            if ch == quote: quote = None
            cur.append(ch); i += 1; continue
        if ch in "'\"":
            quote = ch; cur.append(ch); i += 1; continue
        if c.startswith('&&', i) or c.startswith('||', i):
            out.append(''.join(cur)); cur = []; i += 2; continue
        if ch in ';\n':
            out.append(''.join(cur)); cur = []; i += 1; continue
        cur.append(ch); i += 1
    out.append(''.join(cur))
    return out


def ops(x):
    """Inspection operations in a turn, counting batching done in the shell.

    Non-Bash calls count one each. A Bash call counts its read-ish segments
    (`echo` labels do not count — they are captions, not inspections), plus one
    per extra range in a multi-range `sed -n`. A Bash call that inspects nothing
    still counts one, so a turn is never zero.
    """
    n = 0
    for name, c in zip(x['tools'], x['cmds']):
        if name != 'Bash':
            n += 1
            continue
        k = batched_items(c)
        if not k:
            for part in split_cmd(c):
                if OP.match(part.strip()):
                    k += 1 + max(0, len(RANGE.findall(part)) - 1)
        n += max(k, 1)
    return n


MCP_BASH = ("unity-mcp-cli",)


def mcp_turn(x):
    """A turn whose only calls go to the Unity Editor (direct MCP tools or the CLI door)."""
    if not x['tools']:
        return False
    for n, c in zip(x['tools'], x['cmds']):
        if n.startswith('mcp__'):
            continue
        if n == 'Bash' and any(k in c for k in MCP_BASH):
            continue
        return False
    return True


def run_lengths(t, pred):
    """Lengths of maximal consecutive runs of turns matching pred (only runs > 1)."""
    runs, cur = [], 0
    for x in t:
        if pred(x):
            cur += 1
        else:
            if cur > 1: runs.append(cur)
            cur = 0
    if cur > 1: runs.append(cur)
    return runs


def batch_stats(t):
    """Batching headroom. multi = share of tool turns carrying >1 call (prompting
    ceiling measured at 16%); saved = turns a perfect batcher would not have spent,
    i.e. every turn sitting inside a run of same-kind single-call turns."""
    tool_turns = [x for x in t if x['tools']]
    multi = sum(1 for x in tool_turns if len(x['tools']) > 1)
    total_ops = sum(ops(x) for x in tool_turns)
    # Trickling means ONE inspection in the turn — not one tool call. A single
    # Bash call running `a && b && c` is already batched; charging it as headroom
    # is what overstated the R5 figure (447 turns) that Round 4 was planned on.
    trickle = lambda p: lambda x: p(x) and ops(x) <= 1
    ro = run_lengths(t, trickle(read_only))
    mc = run_lengths(t, trickle(mcp_turn))
    saved = sum(n - 1 for n in ro) + sum(n - 1 for n in mc)
    billed_per_turn = sum(x['ctx'] for x in t) / max(len(t), 1)
    return dict(multi=multi, tool_turns=len(tool_turns), ro=ro, mc=mc,
                ops=total_ops, per_turn=total_ops / max(len(tool_turns), 1),
                saved=saved, headroom=saved * billed_per_turn / 1e6)


def runs_summary(t):
    """Consecutive read-only turns. Every run longer than 1 is a missed batch."""
    runs, cur = [], 0
    for x in t:
        if read_only(x):
            cur += 1
        else:
            if cur > 1: runs.append(cur)
            cur = 0
    if cur > 1: runs.append(cur)
    if not runs:
        return "none"
    return f"{len(runs)} runs, longest {max(runs)}, {sum(runs)} turns inside"


T, cost = scan(SESS)
print(f"project: {PROJECT or '(--slug)'}  [{SLUG}]")
print(f"session: {os.path.basename(SESS)}")
if cost:
    print(f"TOTAL ${cost['totalCostUSD']:.2f} | {cost['totalDuration']/3.6e6:.2f}h | "
          f"+{cost['totalLinesAdded']}/-{cost['totalLinesRemoved']} | "
          + " ".join(f"{k.split('-')[1]}=${v['costUSD']:.1f}" for k, v in cost['modelUsage'].items()))
rows = [("MAIN (orchestrator)", "-", T)]
for f in sorted(glob.glob(SESS[:-6] + "/subagents/*.jsonl")):
    meta = json.load(open(f.replace('.jsonl', '.meta.json')))
    rows.append((meta.get('description', '?')[:34], meta.get('model', 'opus'), scan(f)[0]))
print(f"\n{'actor':36s}{'mdl':8s}{'turns':>6}{'calls':>6}{'c/t':>6}{'billed':>9}{'peak ctx':>10}{'$':>8}")
for name, model, t in rows:
    if not t:
        print(f"{name:36s}{str(model)[:7]:8s}  (no assistant turns in this transcript)")
        continue
    calls = sum(len(x['tools']) for x in t)
    print(f"{name:36s}{str(model)[:7]:8s}{len(t):6d}{calls:6d}{calls/max(len(t),1):6.2f}"
          f"{sum(x['ctx'] for x in t)/1e6:8.1f}M{max(x['ctx'] for x in t):10,d}{sum(x['cost'] for x in t):8.2f}")
    print(f"    amplification {amplification(t):5.0f}x re-read per unique token"
          f"   | read-only runs: {runs_summary(t)}")
    b = batch_stats(t)
    pct = 100 * b['multi'] / max(b['tool_turns'], 1)
    print(f"    batching: {b['per_turn']:.2f} inspections/turn ({b['ops']} total)"
          f"  | {b['multi']}/{b['tool_turns']} tool turns multi-call ({pct:.0f}%)")
    print(f"    trickle runs (1 inspection): ro={sorted(b['ro'], reverse=True)[:5]} "
          f"mcp={sorted(b['mc'], reverse=True)[:5]}"
          f"  | headroom {b['saved']} turns / {b['headroom']:.1f}M billed")
    if 'Implement' in name or 'implement' in name:
        d = collections.Counter(len(x['tools']) for x in t)
        ts = collections.Counter(n for x in t for n in x['tools'])
        print(f"    calls/turn dist {dict(sorted(d.items()))}")
        print(f"    ToolSearch={ts['ToolSearch']}  turns-after-first-report: xem journal SendMessage")

for _model, _n in UNPRICED.items():
    print(f"UNPRICED {_model}: {_n:,d} tokens counted as $0 above — add the model to claude_prices.py")
