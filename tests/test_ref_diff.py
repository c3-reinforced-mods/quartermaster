"""Gates for ref.diff: trim + Myers finds a minimal edit script, proven against a
plain DP LCS, and never uses more trace than its budget."""
import random

import pytest

from conftest import vanilla_bytes
from ref import diff as D
from ref import inc as I
from ref.merge import keys_of


def lcs_length(a, b):
    """The oracle: the textbook O(nm) DP table. Test-only, never ported."""
    n, m = len(a), len(b)
    row = [0] * (m + 1)
    for i in range(n - 1, -1, -1):
        prev = row
        row = [0] * (m + 1)
        for j in range(m - 1, -1, -1):
            if a[i] == b[j]:
                row[j] = prev[j + 1] + 1
            else:
                row[j] = max(prev[j], row[j + 1])
    return row[0]


def check_script(a, b, r):
    """`r` is a valid, minimal, well-formed edit script from `a` to `b`."""
    assert r.ok
    assert D.apply_hunks(a, b, r.hunks) == b
    assert r.d == r.deleted + r.inserted
    assert r.deleted == sum(h.end - h.start for h in r.hunks)
    assert r.inserted == sum(h.mod_end - h.mod_start for h in r.hunks)
    assert r.d == len(a) + len(b) - 2 * lcs_length(a, b)
    for h in r.hunks:
        assert h.end > h.start or h.mod_end > h.mod_start
    for x, y in zip(r.hunks, r.hunks[1:]):
        # Hunks are ordered and separated by at least one matched line.
        assert y.start > x.end and y.mod_start > x.mod_end
        assert y.start - x.end == y.mod_start - x.mod_end
    assert r.cells <= D.trace_cells(r.d)


def test_ten_thousand_seeded_random_cases_match_the_dp_lcs():
    rng = random.Random(20260928)
    cases = 0
    for _ in range(10000):
        n, m = rng.randint(0, 30), rng.randint(0, 30)
        alphabet = rng.randint(1, 8)          # small alphabets force ties
        a = [rng.randint(0, alphabet) for _ in range(n)]
        if rng.random() < 0.5:
            b = [rng.randint(0, alphabet) for _ in range(m)]
        else:                                 # an edited copy, like a real mod
            b = list(a)
            for _e in range(rng.randint(0, 5)):
                op = rng.random()
                pos = rng.randint(0, len(b))
                if op < 0.4:
                    b.insert(pos, rng.randint(0, alphabet + 3))
                elif op < 0.7 and pos < len(b):
                    del b[pos]
                elif pos < len(b):
                    b[pos] = rng.randint(0, alphabet + 3)
        check_script(a, b, D.diff(a, b))
        cases += 1
    assert cases == 10000


def test_larger_seeded_cases_match_the_dp_lcs():
    rng = random.Random(4261)
    for _ in range(40):
        n = rng.randint(100, 300)
        a = [rng.randint(0, 40) for _ in range(n)]
        b = list(a)
        for _e in range(rng.randint(0, 30)):
            pos = rng.randint(0, len(b) - 1)
            b[pos:pos + rng.randint(0, 3)] = [rng.randint(0, 60)
                                              for _ in range(rng.randint(0, 3))]
        check_script(a, b, D.diff(a, b))


def test_trim_counts_common_prefix_and_suffix():
    r = D.diff(list("abcXdef"), list("abcYdef"))
    assert (r.prefix, r.suffix, r.d) == (3, 3, 2)
    assert r.hunks == [D.Hunk(3, 4, 3, 4)]
    r = D.diff(list("aaa"), list("aaaa"))
    assert r.prefix == 3 and r.suffix == 0 and r.hunks == [D.Hunk(3, 3, 3, 4)]
    r = D.diff([], [])
    assert r.ok and r.d == 0 and r.hunks == [] and r.cells == 0


def test_tie_break_deletes_before_it_inserts():
    # Equal reach on both neighbours: the documented rule moves right (delete).
    r = D.diff(list("ab"), list("ba"))
    assert r.d == 2
    assert r.hunks == [D.Hunk(0, 1, 0, 0), D.Hunk(2, 2, 1, 2)]


def test_budget_and_cap():
    assert D.trace_cells(0) == 1 and D.trace_cells(3) == 10
    assert D.d_cap(D.DEFAULT_BUDGET) == 998
    assert D.trace_cells(998) <= D.DEFAULT_BUDGET < D.trace_cells(999)
    assert D.d_cap(10) == 3


def test_over_the_cap_reports_too_different_within_budget():
    budget = 55                                # d_cap(55) == 9
    a = ["v%d" % i for i in range(20)]
    for edits, ok in ((4, True), (5, False)):  # replacing k lines costs D = 2k
        b = list(a)
        for i in range(edits):
            b[2 + 3 * i] = "m%d" % i
        r = D.diff(a, b, budget=budget)
        assert r.ok is ok, edits
        assert r.cells <= budget
        if not ok:
            assert r.reason == "too-different"
    exact = D.diff(["x"] * 9, [], budget=55)    # D == 9 == cap: still fits
    assert exact.ok and exact.d == 9


def test_line_cap():
    r = D.diff(["a"] * 11, ["a"], max_lines=10)
    assert not r.ok and r.reason == "too-many-lines"


def test_real_files_diff_minimally(game_dir):
    """oncamera.inc (73 values) against itself edited in four places."""
    v = I.parse(vanilla_bytes("gui/menu.inc/oncamera.inc")).values
    m = list(v)
    m[1] = b";begin exit; end;"
    m[6] = m[6].replace(b"*4", b"*6")
    m.insert(20, b";// added")
    del m[40]
    a, b = keys_of(v), keys_of(m)
    r = D.diff(a, b)
    check_script(a, b, r)
    assert r.d == 6 and len(r.hunks) == 4


def test_largest_vanilla_inc_with_fifty_edits(game_dir):
    """progresswarai.inc is the longest vanilla .inc (4261 lines)."""
    v = I.parse(vanilla_bytes("scripts/units/global.inc/progresswarai.inc")).values
    rng = random.Random(50)
    m = list(v)
    for i in range(50):
        m[rng.randrange(len(m))] = b";// edit %d" % i
    a, b = keys_of(v), keys_of(m)
    r = D.diff(a, b)
    assert r.ok and r.d <= 100 and D.apply_hunks(a, b, r.hunks) == b
    assert r.cells <= D.trace_cells(100)
