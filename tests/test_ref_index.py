"""Gates for ref.index: mod list, canonical positions, the scan list, the key
encoding, the index itself and its stamps.

Two tests replay the game side's own algorithm (src/states/qmmodlist.pas's
insertion sort, src/states/qmindexbegin.pas's line filter) in Python, statement
for statement, and compare them with the twin: the in-game code cannot run
offline, but its logic can."""
import itertools
import os
import random
import time

import pytest

import hbuild
from ref import fingerprint as FP
from ref import index as X
from ref import order as O
from ref import planner as P

W = b"..\\..\\workshop\\content\\333420\\"
QM = b"mods\\Quartermaster"
FIXTURES = os.path.join(hbuild.REPO, "fixtures")


def entries():
    with open(os.path.join(hbuild.DIST_MOD, *hbuild.IDX_REL.split("/")), "rb") as fh:
        _h, rows = hbuild.parse_vanilla_idx(fh.read())
    return [(p.encode(), s, n, c.encode()) for p, s, n, c in rows]


# ---------------------------------------------------------------- mod list
def test_origin():
    assert X.origin(X.Mod(W + b"873048118", True, b"873048118")) == b"w"
    assert X.origin(X.Mod(b"mods\\SW_Frontline_Protocol", False, b"0")) == b"l"
    assert X.origin(X.Mod(b"mods\\CopyOfZoomOut", True, b"873048118")) == b"c"
    assert X.origin(X.Mod(b"mods\\Plain", True, b"")) == b"l"
    assert X.origin(X.Mod(b"C:\\elsewhere", True)) == b"o"
    assert X.origin(X.Mod(QM, True), is_self=True) == b"s"


def test_find_self_is_the_last_enabled_mod_with_core_aix():
    mods = [X.Mod(b"mods\\A", True), X.Mod(QM, True), X.Mod(b"mods\\QmCopy", False),
            X.Mod(b"mods\\B", True)]
    has = {QM, b"mods\\QmCopy"}
    assert X.find_self(mods, lambda d: d in has) == 1
    assert X.find_self(mods, lambda d: d in has | {b"mods\\B"}) == 3
    assert X.find_self(mods, lambda d: False) == -1


def test_canonical_positions_follow_ref_order():
    dirs = [QM, b"mods\\zeta", W + b"1000", b"mods\\Alpha", W + b"0999", b"odd\\place",
            b"mods\\beta"]
    mods = [X.Mod(d, True) for d in dirs]
    pos = X.canonical_positions(mods, 0)
    by_pos = [d for _p, d in sorted(zip(pos, dirs))]
    assert by_pos == O.canonical_order(dirs, self_dir=QM)
    assert pos[0] == len(dirs) - 1


# The game side's canonical order (src/states/qmmodlist.pas), statement for
# statement: ASCII fold by table, / to \, trailing \ stripped, the Workshop
# prefix test, zero padding, then an insertion sort that moves an entry only
# past strictly greater ones.
def _game_lower(s):
    up, low = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ", b"abcdefghijklmnopqrstuvwxyz"
    return bytes(low[up.index(c)] if c in up else c for c in s)


def _game_cmp(a, b):
    for x, y in zip(a, b):
        if x != y:
            return -1 if x < y else 1
    return (len(a) > len(b)) - (len(a) < len(b))


def _game_positions(dirs, self_index):
    wdir = b"..\\..\\workshop\\content\\333420\\"
    norm = []
    for d in dirs:
        n = d.replace(b"/", b"\\")
        while n.endswith(b"\\"):
            n = n[:-1]
        norm.append(n)
    self_low = _game_lower(norm[self_index]) if self_index >= 0 else b""
    org, key = [], []
    for i, d in enumerate(dirs):
        low = _game_lower(norm[i])
        o, k = 2, _game_lower(d)
        if self_index >= 0 and low == self_low:
            o, k = 3, b""
        elif low[:len(wdir)] == wdir:
            rest = norm[i][len(wdir):]
            if rest and all(c in b"0123456789" for c in rest):
                o = 0
                while rest[:1] == b"0":
                    rest = rest[1:]
                k = rest.rjust(20, b"0")
        elif low[:5] == b"mods\\":
            rest = norm[i][5:]
            if rest and b"\\" not in rest:
                o, k = 1, _game_lower(rest)
        org.append(o)
        key.append(k)
    order = []
    for i in range(len(dirs)):
        j = i
        order.append(None)
        while j > 0:
            k = order[j - 1]
            c = (org[i] > org[k]) - (org[i] < org[k])
            if c == 0:
                c = _game_cmp(key[i], key[k])
            if c == 0:
                c = _game_cmp(dirs[i], dirs[k])
            if c < 0:
                order[j] = k
                j -= 1
            else:
                break
        order[j] = i
    pos = [0] * len(dirs)
    for rank, i in enumerate(order):
        pos[i] = rank
    return pos


def test_game_side_canonical_sort_equals_the_twin():
    rng = random.Random(20260928)
    pool = [QM, b"MODS\\quartermaster\\", b"mods\\zeta", b"mods\\Zeta", b"mods/zeta/",
            W + b"1000", W + b"0999", W + b"999", W + b"12ab", b"..\\..\\WORKSHOP\\content\\333420\\5",
            b"mods\\a\\b", b"mods\\", b"odd\\place", b"Odd\\Place", b"mods\\\xe9t\xe9",
            b"mods\\SW_Frontline_Protocol", b"mods\\QMTestWASD", b"mods\\QMTestCamSpeed"]
    for _ in range(400):
        dirs = rng.sample(pool, rng.randint(1, len(pool)))
        self_index = rng.randrange(-1, len(dirs))
        mods = [X.Mod(d, True) for d in dirs]
        assert _game_positions(dirs, self_index) == X.canonical_positions(mods, self_index), dirs
    for perm in itertools.permutations([QM, b"mods\\QMTestWASD", b"mods\\QMTestCamSpeed",
                                        W + b"873048118"]):
        dirs = list(perm)
        s = dirs.index(QM)
        assert _game_positions(dirs, s) == X.canonical_positions([X.Mod(d, True) for d in dirs], s)


# -------------------------------------------------------------------- scan
def test_scan_list_is_the_merge_class_plus_named_paths():
    rows = entries()
    scan = X.scan_entries(rows)
    assert len(rows) == 17001
    assert len(scan) == 316
    paths = [e[0] for e in scan]
    assert sum(1 for e in scan if e[3] == b"merge") == 311
    for p in P.HOOK_FILES + P.PHASE_B_DATA + (P.ADDITIVE_GLOBAL,):
        assert p in paths
    assert paths == sorted(paths)                       # vanilla.idx order


def test_game_side_scan_filter_equals_the_twin():
    """src/states/qmindexbegin.pas reads each Code value `;path|size|lines|class`,
    keeps it when it ends in `|merge` or its path is in `${scannamed}`."""
    named = b"|" + b"|".join(list(P.HOOK_FILES) + list(P.PHASE_B_DATA) + [P.ADDITIVE_GLOBAL]) + b"|"
    with open(os.path.join(hbuild.DIST_MOD, *hbuild.IDX_REL.split("/")), "rb") as fh:
        values = [line[len(hbuild.PREFIX) - 1:] for line in fh.read().split(b"\r\n")
                  if line.startswith(hbuild.PREFIX)]
    got = []
    for s in values:
        if s[:1] == b";":
            s = s[1:]
        p = s.find(b"|") + 1
        if p > 1:
            path = s[:p - 1]
            if s[len(s) - 6:] == b"|merge" or (b"|" + path + b"|") in named:
                rest = s[p:]
                rest = rest[rest.find(b"|") + 1:]
                q = rest.find(b"|") + 1
                got.append((path, int(rest[:q - 1]), rest[q:]))
    assert got == [(e[0], e[2], e[3]) for e in X.scan_entries(entries())]


# -------------------------------------------------------------------- keys
def test_index_keys_are_identifier_like_and_distinct():
    rows = entries()
    keys = [X.index_key(e[0]) for e in rows]
    for k in keys:
        assert k[:1] == b"k" and all(c == 95 or 48 <= c <= 57 or 97 <= c <= 122 for c in k)
    # The parser folds case and trims, so distinct must hold after folding.
    assert len(set(k.lower() for k in keys)) == len(rows)
    assert X.index_key(b"gui\\menu.inc\\oncamera.inc") == b"kgui_smenu_dinc_soncamera_dinc"
    tricky = [b"a_b", b"a\\b", b"a.b", b"a_sb", b"a__b", b"A", b"a", b"_", b" x", b"x ", b""]
    assert len(set(X.index_key(t) for t in tricky)) == len(tricky)


# ------------------------------------------------------------------- index
def _mods():
    return [X.Mod(b"mods\\QMTestWASD", True), X.Mod(W + b"5", True, b"5"),
            X.Mod(b"mods\\Off", False), X.Mod(QM, True), X.Mod(b"mods\\QMTestCamSpeed", True)]


ROWS = [(b"game\\var\\hotkeys.cfg", 1, 243, b"wta"),
        (b"gui\\menu.inc\\cameracontrol.inc", 1, 38, b"merge"),
        (b"gui\\menu.inc\\oncamera.inc", 1, 76, b"merge"),
        (b"gui\\menu.inc\\zz.inc", 1, 5, b"merge"),
        (b"textures\\a.dds", 1, -1, b"never")]

SHIPS = {b"mods\\QMTestWASD": {b"game\\var\\hotkeys.cfg": 101, b"gui\\menu.inc\\oncamera.inc": 102},
         b"mods\\QMTestCamSpeed": {b"gui\\menu.inc\\oncamera.inc": 201, b"textures\\a.dds": 202},
         b"mods\\Off": {b"gui\\menu.inc\\oncamera.inc": 301},
         W + b"5": {b"gui\\menu.inc\\zz.inc": 501}}


def _age(d, path):
    assert d != QM, "Quartermaster's own folder is never asked"
    assert d != b"mods\\Off", "a disabled mod is never scanned"
    return SHIPS.get(d, {}).get(path, -1)


def test_index_providers_ages_and_stamps():
    mods = _mods()
    idx = X.build_index(mods, 3, ROWS, _age, shipped_hooks=[b"gui\\menu.inc\\cameracontrol.inc"])
    # 4 scanned paths (the .dds is not on the scan list) x 3 scanned mods.
    assert idx.scanned == [r[0] for r in ROWS[:4]] and idx.calls == 12
    by = idx.by_dir(mods)
    assert by == {b"game\\var\\hotkeys.cfg": [b"mods\\QMTestWASD"],
                  b"gui\\menu.inc\\cameracontrol.inc": [QM],
                  b"gui\\menu.inc\\oncamera.inc": [b"mods\\QMTestCamSpeed", b"mods\\QMTestWASD"],
                  b"gui\\menu.inc\\zz.inc": [W + b"5"]}
    assert idx.ages[b"gui\\menu.inc\\cameracontrol.inc"] == [None]
    assert idx.ages[b"gui\\menu.inc\\oncamera.inc"] == [201, 102]
    assert idx.stamps[0] == FP.qhash(b"game\\var\\hotkeys.cfg 101\ngui\\menu.inc\\oncamera.inc 102\n")
    assert idx.stamps[4] == FP.qhash(b"gui\\menu.inc\\oncamera.inc 201\n")
    assert sorted(idx.stamps) == [0, 1, 4]


def test_vanilla_stamp_and_fingerprint():
    mods = _mods()
    idx = X.build_index(mods, 3, ROWS, _age, shipped_hooks=[b"gui\\menu.inc\\cameracontrol.inc"])
    v = X.vanilla_stamp(idx, lambda p: len(p), 777)
    text = b"".join(p + b" %d\n" % len(p) for p in idx.scanned if p in idx.providers)
    assert v == FP.qhash(text + b"exe 777\n")
    fp_text, fp = X.fingerprint(mods, 3, idx, v, b"0.0.0")
    assert fp == FP.qhash(fp_text)
    lines = fp_text.split(b"\n")
    assert lines[:3] == [b"qm-fingerprint 1", b"qm 0.0.0", b"vanilla " + v]
    assert lines[3:] == [b"w 5 on " + idx.stamps[1], b"l Off off",
                         b"l QMTestCamSpeed on " + idx.stamps[4],
                         b"l QMTestWASD on " + idx.stamps[0], b""]
    assert b"Quartermaster" not in fp_text


@pytest.mark.parametrize("fresh", [[], [1], [4], [1, 4], [2], [0, 1, 2, 4]])
@pytest.mark.parametrize("rows", [None, [4, 0, 2, 1, 3]])
def test_the_known_fingerprint_is_the_one_before_the_fresh_mods(fresh, rows):
    """known_fingerprint over a world with `fresh` registered now is the
    fingerprint of the same world built without them: W 5 alone ships zz.inc
    (gone from the vanilla stamp), CamSpeed shares oncamera.inc with WASD
    (stays)."""
    mods = _mods()
    hooks = [b"gui\\menu.inc\\cameracontrol.inc"]
    pos = X.load_positions(mods, 3, rows)
    idx = X.build_index(mods, 3, ROWS, _age, shipped_hooks=hooks, pos=pos)
    _t, got = X.known_fingerprint(mods, 3, idx, len, 777, b"0.0.0", fresh, pos)
    rest = [i for i in range(len(mods)) if i not in fresh]
    world = [mods[i] for i in rest]
    order = sorted(rest, key=lambda i: pos[i])
    pos2 = [order.index(i) for i in rest]
    idx2 = X.build_index(world, rest.index(3), ROWS, _age, shipped_hooks=hooks, pos=pos2)
    _t2, want = X.fingerprint(world, rest.index(3), idx2, X.vanilla_stamp(idx2, len, 777),
                              b"0.0.0", pos2)
    assert got == want
    if not fresh:
        assert got == X.fingerprint(mods, 3, idx, X.vanilla_stamp(idx, len, 777), b"0.0.0",
                                    pos)[1]


def test_a_second_quartermaster_copy_is_not_indexed():
    """A Workshop copy of Quartermaster next to the local one ships the same hook
    files; as an ordinary mod its hook lines would be merged in a second time.
    It is not scanned, and stays in the fingerprint without a stamp."""
    copy = W + b"77"
    mods = _mods() + [X.Mod(copy, True, b"77")]
    ships = dict(SHIPS)
    ships[copy] = {b"gui\\menu.inc\\cameracontrol.inc": 701, b"gui\\menu.inc\\oncamera.inc": 702}
    cores = {QM, copy}

    def age(d, path):
        assert d != copy, "another Quartermaster copy is never scanned"
        return _age(d, path)

    # Quartermaster itself is found as before: the last enabled mod with core.aix.
    assert X.find_self(mods, lambda d: d in cores) == 5
    idx = X.build_index(mods, 3, ROWS, age, [b"gui\\menu.inc\\cameracontrol.inc"],
                        has_core=lambda d: d in cores)
    assert X.scanned_mods(mods, 3, lambda d: d in cores) == [1, 4, 0]
    by = idx.by_dir(mods)
    assert by[b"gui\\menu.inc\\cameracontrol.inc"] == [QM]
    assert by[b"gui\\menu.inc\\oncamera.inc"] == [b"mods\\QMTestCamSpeed", b"mods\\QMTestWASD"]
    assert 5 not in idx.stamps and idx.calls == 12
    decisions = P.plan(by, ROWS, QM)
    assert all(copy not in d.providers for d in decisions)
    text, _fp = X.fingerprint(mods, 3, idx, b"v", b"0.0.0")
    assert b"w 77 on \n" in text
    # Without the rule the copy would be an ordinary provider of the hook file.
    loose = X.build_index(mods, 3, ROWS, lambda d, p: ships.get(d, {}).get(p, -1),
                          [b"gui\\menu.inc\\cameracontrol.inc"])
    assert loose.by_dir(mods)[b"gui\\menu.inc\\cameracontrol.inc"] == [copy, QM]


def test_dos_age_rounds_up_to_the_even_second():
    # oncamera.inc: mtime 15:15:56.316 local (CEST) on 2026-08-24; the game read
    # FileAge 1561885181 for it in a probe run on 2026-09-27.
    cest = lambda s: time.gmtime(s + 7200)
    assert X.dos_age(1787577356.3162339, cest) == 1561885181
    assert X.dos_age(1787577356.0, cest) == 1561885180
    # Rounding up carries into the minute.
    assert X.dos_age(1787577359.5, cest) == 1561885181 - 29 + 32 + 0


@pytest.mark.skipif(not os.path.isdir(os.path.join(FIXTURES, "QMTestWASD")),
                    reason="fixtures not built (python tools/fixtures.py)")
def test_wasd_and_camspeed_fixtures_index_and_plan():
    """The run request (b) layout: WASD + CamSpeed + Quartermaster deployed."""
    mods = [X.Mod(b"mods\\SW_Frontline_Protocol", False), X.Mod(W + b"873048118", False, b"873048118"),
            X.Mod(b"mods\\QMTestWASD", True), X.Mod(b"mods\\QMTestCamSpeed", True), X.Mod(QM, True)]
    roots = {b"mods\\QMTestWASD": os.path.join(FIXTURES, "QMTestWASD"),
             b"mods\\QMTestCamSpeed": os.path.join(FIXTURES, "QMTestCamSpeed")}

    def age(d, path):
        full = os.path.join(roots[d], "data", *path.decode().split("\\"))
        return X.dos_age(os.stat(full).st_mtime) if os.path.isfile(full) else -1

    shipped = [hbuild._vanilla_rel(h.into) for h in hbuild.load_hooks()]
    idx = X.build_index(mods, 4, entries(), age, shipped)
    by = idx.by_dir(mods)
    assert by == {
        b"game\\var\\hotkeys.cfg": [b"mods\\QMTestWASD"],
        b"gui\\menu.inc\\cameracontrol.inc": [QM],
        b"gui\\menu.inc\\doprogress.inc": [QM],
        b"gui\\menu.inc\\eventmainmenu.inc": [QM],
        b"gui\\menu.inc\\hotkeysettings.inc": [b"mods\\QMTestWASD"],
        b"gui\\menu.inc\\initminimap.inc": [QM],
        b"gui\\menu.inc\\onlanevent.inc": [QM],
        b"gui\\menu.inc\\oncamera.inc": [b"mods\\QMTestCamSpeed", b"mods\\QMTestWASD"],
        b"gui\\menu.inc\\registershortcuts.inc": [b"mods\\QMTestCamSpeed", b"mods\\QMTestWASD"]}
    plan = dict((d.path, (d.action, d.strategy)) for d in P.plan(by, entries(), QM))
    assert plan == {
        b"game\\var\\hotkeys.cfg": (P.SKIP, P.MERGE_DATA),
        b"gui\\menu.inc\\cameracontrol.inc": (P.HOOK, P.HOOK),
        b"gui\\menu.inc\\doprogress.inc": (P.HOOK, P.HOOK),
        b"gui\\menu.inc\\eventmainmenu.inc": (P.HOOK, P.HOOK),
        b"gui\\menu.inc\\hotkeysettings.inc": (P.SKIP, P.MERGE_INC),
        b"gui\\menu.inc\\initminimap.inc": (P.HOOK, P.HOOK),
        b"gui\\menu.inc\\onlanevent.inc": (P.HOOK, P.HOOK),
        b"gui\\menu.inc\\oncamera.inc": (P.MERGE_INC, P.MERGE_INC),
        b"gui\\menu.inc\\registershortcuts.inc": (P.MERGE_INC, P.MERGE_INC)}
