r"""Line diff: trim the common prefix and suffix, then greedy Myers O(ND).

Why not the LCS table the probe-5 merge used: an (n+1)(m+1) Integer table is fine
for oncamera.inc (73 lines) and hopeless for doprogress.inc (1735) or
progresswarai.inc (4261), and a 4M-element local array crashes the whole game
(docs/research/context-2026-09-27.md section 3). Myers needs memory for its trace
only, which grows with the number of edits D, not with the file.

THE TRACE. Round d of Myers keeps, for every diagonal k = x - y in -d, -d+2, .., d,
the furthest x a d-edit path reaches on it. Only those d+1 diagonals have the
parity of d, so round d is stored as d+1 Integers and the whole trace up to round
D fits one flat array of (D+1)(D+2)/2 Integers:

    T[d*(d+1)/2 + j] = x of diagonal k = -d + 2j,   j = 0..d

The game side allocates that array once (`budget` Integers, <= ~500k per
docs/plan.md section 1) and gives up as soon as the next round would not fit:
the result is "too different" and the caller falls back to winner-takes-all.
`trace_cells(d)` is the figure a test compares against the budget.

TIE-BREAK (deterministic, and the game side must copy it exactly). On diagonal k
of round d the path either comes down from k+1 (an insertion from the mod) or
right from k-1 (a deletion from vanilla):

    j == 0              -> down            (k == -d, nothing to the left)
    j == d              -> right           (k == d, nothing to the right)
    T'[j-1] <  T'[j]    -> down            (k+1 reached further)
    otherwise           -> right           (equal reach: delete first)

where T' is round d-1. Backtracking re-applies the same rule, so no direction bits
are stored. With several shortest scripts this one is chosen; which one is only a
matter of which equal lines are matched, the edit count D is always minimal
(proven against a DP LCS in tests/test_ref_diff.py).

Coordinates: x counts vanilla lines (deletions), y mod lines (insertions). A hunk
replaces vanilla lines [start, end) with mod lines [mod_start, mod_end); an
insertion has start == end. Consecutive edits with no matched line between them
form one hunk, which is exactly what the probe-5 merge called a hunk.
"""

__all__ = ["DEFAULT_BUDGET", "MAX_LINES", "Hunk", "DiffResult", "trace_cells",
           "d_cap", "diff", "apply_hunks"]

#: Integers the trace may use. docs/plan.md: "memory ~ D^2, <= ~500k Integers".
DEFAULT_BUDGET = 500_000

#: Files longer than this are not diffed (docs/plan.md S14: > 60k lines ->
#: winner-takes-all). pattern.lib has 1.17M lines, objcustom.cfg 51.6k.
MAX_LINES = 60_000


class Hunk(object):
    """Vanilla lines [start, end) become mod lines [mod_start, mod_end)."""

    __slots__ = ("start", "end", "mod_start", "mod_end")

    def __init__(self, start, end, mod_start, mod_end):
        self.start = start
        self.end = end
        self.mod_start = mod_start
        self.mod_end = mod_end

    def __eq__(self, other):
        return isinstance(other, Hunk) and self.astuple() == other.astuple()

    def __hash__(self):
        return hash(self.astuple())

    def astuple(self):
        return (self.start, self.end, self.mod_start, self.mod_end)

    def __repr__(self):
        return "Hunk(%d, %d, %d, %d)" % self.astuple()


class DiffResult(object):
    """ok       False when the diff was given up (`reason` says why)
    reason   None, 'too-different' (D over the cap) or 'too-many-lines'
    hunks    list of Hunk, in file order (only when ok)
    d        the edit count D = deleted + inserted (only when ok)
    deleted  vanilla lines deleted or replaced
    inserted mod lines inserted
    prefix   common leading lines trimmed before Myers ran
    suffix   common trailing lines trimmed
    cells    trace Integers used (<= budget)
    """

    def __init__(self, ok, reason, hunks, d, deleted, inserted, prefix, suffix,
                 cells):
        self.ok = ok
        self.reason = reason
        self.hunks = hunks
        self.d = d
        self.deleted = deleted
        self.inserted = inserted
        self.prefix = prefix
        self.suffix = suffix
        self.cells = cells

    def __repr__(self):
        if not self.ok:
            return "DiffResult(%s, cells=%d)" % (self.reason, self.cells)
        return "DiffResult(d=%d, %d hunks, prefix=%d, suffix=%d, cells=%d)" % (
            self.d, len(self.hunks), self.prefix, self.suffix, self.cells)


def trace_cells(d):
    """Integers the trace holds after round d."""
    return (d + 1) * (d + 2) // 2


def d_cap(budget=DEFAULT_BUDGET):
    """The largest D whose trace fits `budget` Integers."""
    d = 0
    while trace_cells(d + 1) <= budget:
        d += 1
    return d


def diff(a, b, budget=DEFAULT_BUDGET, max_lines=MAX_LINES):
    """Diff line keys `a` (vanilla) against `b` (mod). Keys compare with `==`."""
    n, m = len(a), len(b)
    if n > max_lines or m > max_lines:
        return DiffResult(False, "too-many-lines", None, None, None, None, 0, 0, 0)

    p = 0
    while p < n and p < m and a[p] == b[p]:
        p += 1
    q = 0
    while q < n - p and q < m - p and a[n - 1 - q] == b[m - 1 - q]:
        q += 1
    big_n = n - p - q
    big_m = m - p - q

    if big_n == 0 and big_m == 0:
        return DiffResult(True, None, [], 0, 0, 0, p, q, 0)

    trace = []
    found = -1
    d = 0
    while found < 0:
        if trace_cells(d) > budget:
            return DiffResult(False, "too-different", None, None, None, None,
                              p, q, len(trace))
        base_prev = (d - 1) * d // 2
        for j in range(d + 1):
            k = -d + 2 * j
            if d == 0:
                x = 0
            elif j == 0:
                x = trace[base_prev + j]
            elif j == d:
                x = trace[base_prev + j - 1] + 1
            elif trace[base_prev + j - 1] < trace[base_prev + j]:
                x = trace[base_prev + j]
            else:
                x = trace[base_prev + j - 1] + 1
            y = x - k
            while x < big_n and y < big_m and a[p + x] == b[p + y]:
                x += 1
                y += 1
            trace.append(x)
            if x >= big_n and y >= big_m:
                # Only diagonal N-M can end at (N, M), so the first hit is the
                # only one and the rest of the round is not needed.
                found = j
                break
        if found < 0:
            d += 1

    # Backtrack from (D, found) to (0, 0), collecting one edit per round.
    edits = []
    j = found
    for dd in range(d, 0, -1):
        base_prev = (dd - 1) * dd // 2
        if j == 0:
            down = True
        elif j == dd:
            down = False
        else:
            down = trace[base_prev + j - 1] < trace[base_prev + j]
        jp = j if down else j - 1
        xp = trace[base_prev + jp]
        yp = xp - (-(dd - 1) + 2 * jp)
        edits.append((down, xp, yp))
        j = jp
    edits.reverse()

    hunks = []
    deleted = inserted = 0
    cur = None
    px = py = None
    for down, xp, yp in edits:
        if cur is not None and (xp, yp) == (px, py):
            pass
        else:
            if cur is not None:
                hunks.append(cur)
            cur = Hunk(p + xp, p + xp, p + yp, p + yp)
        if down:
            cur.mod_end += 1
            inserted += 1
            px, py = xp, yp + 1
        else:
            cur.end += 1
            deleted += 1
            px, py = xp + 1, yp
    if cur is not None:
        hunks.append(cur)
    return DiffResult(True, None, hunks, d, deleted, inserted, p, q, len(trace))


def apply_hunks(a, b, hunks):
    """Vanilla `a` with every hunk replaced by its mod lines from `b`."""
    out = []
    pos = 0
    for h in hunks:
        out.extend(a[pos:h.start])
        out.extend(b[h.mod_start:h.mod_end])
        pos = h.end
    out.extend(a[pos:])
    return out
