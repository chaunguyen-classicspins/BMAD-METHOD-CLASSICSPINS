#!/usr/bin/env python3
# A module, not a command: the shebang is only there so the sync can stamp it as generated.
"""List API prices per Claude model, for the bmad-loop cost tools (run-cost.py, measure-run.py).

One table, so the two tools can never price the same transcript two different ways. Prices are USD
per million tokens at Anthropic's first-party list rates (checked 2026-09). A subscription session
is not billed this way. The dollar figure is a comparable unit of work, not an invoice.

  * input, output and cache read are per model.
  * a cache WRITE is priced from the input rate by its TTL: 5 minutes = 1.25x, 1 hour = 2x. A
    transcript's `usage.cache_creation` splits the two; a usage block without the split is taken as
    5-minute writes, the API default.

A model id is matched by its LONGEST listed prefix, so a dated id (`claude-haiku-4-5-20251001`)
prices as its family, and `claude-opus-5-5` is never mistaken for `claude-opus-5`. An id that matches
nothing is UNPRICED: `cost()` returns None for it, and a caller must say so rather than fold it into
another model's rate. Pricing Opus 5.5 at the Opus 4 rate once inflated a story's cost ~3.75x.
"""

# (model-id prefix, input, output, cache read) — USD per million tokens.
PRICES = (
    ("claude-fable-5-1", 10.0, 50.0, 0.25),
    ("claude-fable-5", 10.0, 50.0, 1.00),
    ("claude-opus-5-5", 4.0, 20.0, 0.20),
    ("claude-opus-5", 5.0, 25.0, 0.50),
    ("claude-opus-4-8", 5.0, 25.0, 0.50),
    ("claude-opus-4-7", 5.0, 25.0, 0.50),
    ("claude-opus-4-6", 5.0, 25.0, 0.50),
    ("claude-sonnet-5", 2.0, 10.0, 0.20),
    ("claude-sonnet-4-6", 3.0, 15.0, 0.30),
    ("claude-haiku-4-5", 1.0, 5.0, 0.10),
)

CACHE_WRITE_5M = 1.25
CACHE_WRITE_1H = 2.0

_BY_LENGTH = sorted(PRICES, key=lambda p: len(p[0]), reverse=True)


def rate(model):
    """(prefix, input, output, cache_read) for a model id, or None when it is not listed."""
    m = (model or "").lower()
    return next((p for p in _BY_LENGTH if m.startswith(p[0])), None)


def split(usage):
    """(input, output, cache_write_5m, cache_write_1h, cache_read) tokens of one usage block."""
    cc = usage.get("cache_creation") or {}
    w5, w1 = cc.get("ephemeral_5m_input_tokens"), cc.get("ephemeral_1h_input_tokens")
    total_w = usage.get("cache_creation_input_tokens", 0) or 0
    if w5 is None and w1 is None:
        w5, w1 = total_w, 0
    return (usage.get("input_tokens", 0) or 0, usage.get("output_tokens", 0) or 0,
            w5 or 0, w1 or 0, usage.get("cache_read_input_tokens", 0) or 0)


def cost(model, usage):
    """USD for one usage block, or None when the model is unpriced (the caller reports it)."""
    r = rate(model)
    if r is None:
        return None
    _, inp, out, read = r
    i, o, w5, w1, cr = split(usage)
    return (i * inp + o * out + w5 * inp * CACHE_WRITE_5M + w1 * inp * CACHE_WRITE_1H + cr * read) / 1e6


def cache_read_cost(model, usage):
    """The cache-read share of cost(), USD; None when unpriced."""
    r = rate(model)
    return None if r is None else split(usage)[4] * r[3] / 1e6
