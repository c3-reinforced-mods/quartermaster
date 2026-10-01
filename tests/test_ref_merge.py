"""Gates for ref.merge: merge properties, the classifier rules, the probe-5 case
measured in-game, and the fixture combinations of docs/plan.md section 4."""
import hashlib
import random

import pytest

from conftest import vanilla_bytes
from ref import inc as I
from ref import merge as M
from ref.order import canonical_order

ONCAMERA = "gui/menu.inc/oncamera.inc"


# ------------------------------------------------------------------ properties
def unique_base(rng, n):
    return [b";v%d" % i for i in range(n)]


def random_edit(rng, base, tag, lo=0, hi=None):
    """`base` with 1-3 edits inside [lo, hi): fresh unique lines, so the diff of
    the result against `base` is exactly these edits."""
    hi = len(base) if hi is None else hi
    out = list(base)
    spots = sorted(rng.sample(range(lo, hi), min(hi - lo, rng.randint(1, 3))),
                   reverse=True)
    for k, pos in enumerate(spots):
        op = rng.random()
        new = [b";%s%d_%d" % (tag, pos, j) for j in range(rng.randint(1, 3))]
        if op < 0.33:
            out[pos:pos] = new                     # insertion
        elif op < 0.66:
            out[pos:pos + 1] = new                 # replacement
        else:
            del out[pos]                           # deletion
    return out


def test_merge_with_an_unchanged_side_gives_the_changed_side():
    rng = random.Random(1)
    for _ in range(2000):
        v = unique_base(rng, rng.randint(1, 30))
        a = random_edit(rng, v, b"a")
        r = M.merge(v, [(b"A", a), (b"B", list(v))])       # merge(v, A, v) = A
        assert r.mode == "merged" and r.lines == a and r.conflicts == 0
        r = M.merge(v, [(b"B", list(v)), (b"A", a)])       # either order
        assert r.lines == a


def test_merge_of_identical_sides_gives_that_side_once():
    rng = random.Random(2)
    for _ in range(2000):
        v = unique_base(rng, rng.randint(1, 30))
        a = random_edit(rng, v, b"a")
        r = M.merge(v, [(b"A", a), (b"A2", list(a))])      # merge(v, A, A) = A
        assert r.lines == a and r.conflicts == 0 and r.status == M.OK
        assert all(h.status in (M.IDENTICAL, M.DUPLICATE) for h in r.hunks)


def test_non_overlapping_edits_of_both_sides_survive():
    rng = random.Random(3)
    for _ in range(2000):
        # At least 12 lines: 3 deletions at most per side stay under the
        # replacement share, which would otherwise (rightly) end the merge.
        n = rng.randint(12, 40)
        v = unique_base(rng, n)
        cut = rng.randint(2, n - 2)
        a = random_edit(rng, v, b"a", 0, cut - 1)            # A edits [0, cut-1)
        b = random_edit(rng, v, b"b", cut, n)                # B edits [cut, n)
        r = M.merge(v, [(b"A", a), (b"B", b)])
        assert r.mode == "merged" and r.conflicts == 0
        # Both edits survive: A's edited part, the untouched line cut-1, B's part.
        want = a[:len(a) - (n - cut + 1)] + [v[cut - 1]] + b[cut:]
        assert r.lines == want


def test_merge_of_nothing_changed_is_vanilla():
    v = [b";a", b";b"]
    r = M.merge(v, [(b"A", [b";a", b";b  "]), (b"B", [b";a\t", b";b"])])
    assert r.mode == "vanilla" and r.lines == v and r.status == M.OK


# ------------------------------------------------------------------ classifier
V10 = [b";v%d" % i for i in range(10)]


def edited(repl):
    out = list(V10)
    for i, line in sorted(repl.items(), reverse=True):
        if line is None:
            del out[i]
        else:
            out[i] = line
    return out


def test_overlap_is_a_conflict_and_the_later_participant_wins():
    a = edited({4: b";A4"})
    b = edited({4: b";B4"})
    r = M.merge(V10, [(b"A", a), (b"B", b)])
    assert r.conflicts == 1 and r.status == M.WARN
    assert [h.status for h in r.hunks] == [M.CONFLICT_LOST, M.CONFLICT_WON]
    assert r.lines == b


def test_same_start_counts_as_overlap():
    a = list(V10)
    a.insert(4, b";A-inserted")                   # insertion at 4
    b = edited({4: b";B4"})                       # replacement [4,5)
    r = M.merge(V10, [(b"A", a), (b"B", b)])
    assert r.conflicts == 1


def test_identical_edits_are_deduplicated():
    a = edited({4: b";X"})
    r = M.merge(V10, [(b"A", a), (b"B", list(a)), (b"C", list(a))])
    assert r.conflicts == 0 and r.status == M.OK and r.lines == a
    assert [h.status for h in r.hunks] == [M.IDENTICAL, M.DUPLICATE, M.DUPLICATE]


def test_identical_is_judged_on_normalised_keys():
    r = M.merge(V10, [(b"A", edited({4: b";X"})), (b"B", edited({4: b";X \t"}))])
    assert r.conflicts == 0 and r.lines == edited({4: b";X"})


@pytest.mark.parametrize("gap, near", [(0, True), (1, True), (3, True), (4, False)])
def test_proximity_window_is_three_vanilla_lines(gap, near):
    a = edited({2: b";A2"})                       # hunk [2,3)
    b = edited({3 + gap: b";B"})                  # hunk [3+gap, 4+gap)
    r = M.merge(V10, [(b"A", a), (b"B", b)])
    assert r.conflicts == 0
    assert (r.proximity_pairs == 1) is near
    assert r.status == (M.WARN if near else M.OK)
    assert all(h.status == (M.PROXIMITY if near else M.CLEAN) for h in r.hunks)


def test_proximity_is_only_between_different_participants():
    a = edited({2: b";A2", 4: b";A4"})
    r = M.merge(V10, [(b"A", a), (b"B", list(V10))])
    assert r.proximity_pairs == 0 and r.status == M.OK


def test_replacement_with_another_changer_is_winner_takes_all():
    rewrite = [b";R%d" % i for i in range(8)] + V10[8:]   # 8 of 10 lines replaced
    small = edited({9: b";S9"})
    r = M.merge(V10, [(b"R", rewrite), (b"S", small)])
    assert r.mode == "winner" and r.reason == "replacement" and r.status == M.WARN
    assert r.winner == 1 and r.participants[0].replacement
    # Alone, the replacement is simply that participant's file.
    r = M.merge(V10, [(b"R", rewrite), (b"U", list(V10))])
    assert r.mode == "merged" and r.lines == rewrite and r.status == M.OK


def test_replacement_is_counted_on_the_diff_not_on_the_trimmed_region():
    # First and last line changed: the trimmed region is the whole file, but the
    # diff replaces 2 of 10 lines - no replacement (the probe-5 mod B shape).
    a = edited({0: b";A0", 9: b";A9"})
    r = M.merge(V10, [(b"A", a), (b"B", edited({5: b";B5"}))])
    assert r.mode == "merged" and not r.participants[0].replacement
    # Many inserted lines replace nothing either.
    big = V10[:5] + [b";I%d" % i for i in range(50)] + V10[5:]
    r = M.merge(V10, [(b"A", big), (b"B", edited({9: b";B9"}))])
    assert r.mode == "merged" and r.conflicts == 0


def test_six_of_ten_deleted_is_a_replacement_five_is_not():
    five = edited({i: None for i in range(5)})
    six = edited({i: None for i in range(6)})
    other = edited({9: b";B9"})
    assert M.merge(V10, [(b"A", five), (b"B", other)]).mode == "merged"
    assert M.merge(V10, [(b"A", six), (b"B", other)]).reason == "replacement"


def test_too_different_is_winner_takes_all_fail():
    a = [b";A%d" % i for i in range(10)]
    r = M.merge(V10, [(b"A", a), (b"B", edited({1: b";B"}))], budget=20)
    assert r.mode == "winner" and r.status == M.FAIL and r.reason == "too-different"
    assert r.winner == 1


def test_describe_prints_every_hunk():
    r = M.merge(V10, [(b"A", edited({4: b";A4"})), (b"B", edited({4: b";B4"}))])
    text = "\n".join(M.describe(r))
    assert "1 conflicts" in text and "conflict-lost" in text and "conflict-won" in text


# ----------------------------------------------------------- probe 5, in-game
#: sha256 of vanilla oncamera.inc as of 2026-09-28, and of the file the game
#: itself wrote for this merge in probe 5 (r5c_merged_oncamera.inc). If a GSC
#: patch changes oncamera.inc the second hash no longer applies.
ONCAMERA_SHA = "79632567b94ddf19367c0fc331068a472ea6ee7ebb3078ae66d57fcf21a5a17e"
PROBE5_MERGED_SHA = "4e2517dd38e5c66088132cbd30509d4164d6b2862808f0830829b9f7d1e06bde"
P = b"      [*] = ;"


def probe5_mods(vanilla):
    """Mods A and B exactly as probe 5 built them from vanilla oncamera.inc."""
    lines = vanilla.split(b"\r\n")
    first = next(i for i, l in enumerate(lines) if l.startswith(P))
    ks = lines.index(P + b"var keySpeed : Float = gProfile.keyscrollspeed*4;")
    last = max(i for i, l in enumerate(lines) if l.startswith(P))
    a = list(lines)
    a[ks] = P + b"var keySpeed : Float = gProfile.keyscrollspeed*5;"
    a.insert(first, P + b"Log('HPROBE merge: change from A (line inserted at top)');")
    b = list(lines)
    b[first + 1] = P + b"begin Log('HPROBE merge: change from B (exit line replaced)'); exit; end;"
    b[ks] = P + b"var keySpeed : Float = gProfile.keyscrollspeed*6;"
    b[last] = P + b"SetCameraElasticMoveTurnOff(); // B changed the last line"
    return b"\r\n".join(a), b"\r\n".join(b)


def test_probe5_case_matches_the_game(game_dir):
    vanilla = vanilla_bytes(ONCAMERA)
    if hashlib.sha256(vanilla).hexdigest() != ONCAMERA_SHA:
        pytest.skip("oncamera.inc changed since probe 5")
    a, b = probe5_mods(vanilla)
    r, out = M.merge_inc(vanilla, [(b"mods\\HProbeMergeA", a), (b"mods\\HProbeMergeB", b)])
    # r5c.0.log:25-26: prefix/suffix of each mod
    assert (r.participants[0].d, r.participants[1].d) == (3, 6)
    # r5c.0.log:27-34: 5 hunks, 1 conflict, B wins [6,7), 74 result lines
    assert [(h.mod_id, h.start, h.end, len(h.lines)) for h in r.hunks] == [
        (b"mods\\HProbeMergeA", 0, 0, 1), (b"mods\\HProbeMergeA", 6, 7, 1),
        (b"mods\\HProbeMergeB", 1, 2, 1), (b"mods\\HProbeMergeB", 6, 7, 1),
        (b"mods\\HProbeMergeB", 72, 73, 1)]
    assert r.conflicts == 1
    assert r.hunks[1].status == M.CONFLICT_LOST and r.hunks[3].status == M.CONFLICT_WON
    assert len(r.lines) == 74
    # The two hunks at the top are one vanilla line apart: proximity.
    assert r.hunks[0].status == r.hunks[2].status == M.PROXIMITY
    # Byte for byte what the game wrote.
    assert hashlib.sha256(out).hexdigest() == PROBE5_MERGED_SHA


# ---------------------------------------------------------------- the fixtures
@pytest.fixture(scope="module")
def fixture_mods(game_dir, reference_dir):
    import fixtures as F
    return F, F.build_all(game_dir, reference_dir)


def merge_fixtures(F, mods, names, game_dir):
    """Merge every file of the named fixtures, in canonical order, per path."""
    dirs = canonical_order([b"mods\\" + n.encode("ascii") for n in names])
    order = [d[len(b"mods\\"):].decode("ascii") for d in dirs]
    results = {}
    paths = sorted({rel for n in names for rel in mods[n] if rel != "mod.ini"})
    for rel in paths:
        parts = [(n.encode("ascii"), mods[n][rel]) for n in order if rel in mods[n]]
        vanilla = F.vanilla(game_dir, rel)
        fn = M.merge_inc if rel.endswith(".inc") else M.merge_text
        results[rel] = fn(vanilla, parts)
    return results


def test_wasd_and_camspeed_merge_clean_on_all_four_files(fixture_mods, game_dir):
    F, mods = fixture_mods
    results = merge_fixtures(F, mods, [F.WASD, F.CAMSPEED], game_dir)
    assert sorted(results) == sorted([F.REGISTERSHORTCUTS, F.ONCAMERA,
                                      F.HOTKEYSETTINGS, F.HOTKEYS_CFG])
    for rel, (r, _out) in results.items():
        assert r.mode == "merged", (rel, M.describe(r))
        assert r.conflicts == 0 and r.proximity_pairs == 0 and r.status == M.OK, (
            rel, M.describe(r))
    # Both mods' changes are in the merged files.
    oc = I.parse(results[F.ONCAMERA][1]).values
    assert b";begin Log('QMTEST camspeed'); exit; end;" in oc
    assert b";var keySpeed : Float = gProfile.keyscrollspeed*6;" in oc
    assert b";var bLeft : Boolean = IsKeyDownByName('Left') or IsKeyDownByName('A');" in oc
    rs = I.parse(results[F.REGISTERSHORTCUTS][1]).values
    assert b";Log('QMTEST camspeed registershortcuts');" in rs
    assert b";   Log('QMTEST wasd');" in rs
    assert sum(1 for v in rs if b"qmwasd" in v) == 8


def test_wasd_and_conflict_have_exactly_one_conflict(fixture_mods, game_dir):
    F, mods = fixture_mods
    results = merge_fixtures(F, mods, [F.WASD, F.CONFLICT], game_dir)
    conflicts = {rel: r.conflicts for rel, (r, _out) in results.items()}
    assert sum(conflicts.values()) == 1 and conflicts[F.ONCAMERA] == 1
    r, out = results[F.ONCAMERA]
    # QMTestConflict < QMTestWASD canonically, so WASD is later and wins.
    lost = [h for h in r.hunks if h.status == M.CONFLICT_LOST]
    assert [h.mod_id for h in lost] == [F.CONFLICT.encode("ascii")]
    assert I.parse(out).values == I.parse(mods[F.WASD][F.ONCAMERA]).values


def test_wasd_and_broken_merge_clean_but_declare_one_name_twice(fixture_mods, game_dir):
    """The classifier finds nothing; the union has two declarations of one
    case-insensitive identifier, which only the validator (M4) can reject."""
    import re
    F, mods = fixture_mods
    results = merge_fixtures(F, mods, [F.WASD, F.BROKEN], game_dir)
    r, out = results[F.REGISTERSHORTCUTS]
    assert r.mode == "merged" and r.conflicts == 0 and r.status == M.OK

    def declared(values):
        names = re.findall(rb"\bvar\s+([A-Za-z_]\w*)", b"\n".join(values))
        return [n.lower() for n in names]

    union = declared(I.parse(out).values)
    assert union.count(b"swfp_seat") == 2
    for name in (F.WASD, F.BROKEN):
        alone = declared(I.parse(mods[name][F.REGISTERSHORTCUTS]).values)
        assert alone.count(b"swfp_seat") == 1, name
        assert len(alone) == len(set(alone)), name
