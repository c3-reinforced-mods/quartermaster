"""The index (plan G3) run offline: qmIndex, qmIndexBegin and qmIndexStep as
the build emits them, after qmModList and qmOrder, in the interpreter of
tests/test_m3_pascal.py over the emulated engine of tests/test_m5_pascal.py.

They must find what ref/index.py build_index finds from the same mods and
files: the scan list out of vanilla.idx, each path's providers by load
position with their FileAge, every scanned mod's stamp and the number of
FileAge calls - in one step or spread over many (`indexbatch`), with
Quartermaster's own folder and any other copy of it never asked.
"""
import functools
import random

import pytest

import hbuild as H
import test_m3_pascal as PAS
import test_m5_pascal as M5
from ref import index as X
from ref import order as O
from ref import planner as P

QM, W, INI = M5.QM, M5.W, M5.INI
CORE = b"\\data\\quartermaster\\core.aix"
IDX = QM + b"\\data\\quartermaster\\vanilla.idx"
DEFAULT_AGE = 1564229335            # test_m5_pascal's FileAge for a file it has no age for
SHIPPED = [H._vanilla_rel(h.into) for h in H.load_hooks()]

#: vanilla.idx rows (hbuild.render_vanilla_idx): the merge class, the named
#: paths of every other class (hook files, Phase B data, dmscript.global) and
#: rows the index leaves out.
ENTRIES = [("game\\var\\formations.cfg", 9, 120, "wta"),
           ("game\\var\\hotkeys.cfg", 9, 243, "wta"),
           ("game\\var\\units.cfg", 9, 999, "wta"),
           ("gui\\menu.inc\\cameracontrol.inc", 9, 38, "merge"),
           ("gui\\menu.inc\\doprogress.inc", 9, 1744, "wta"),
           ("gui\\menu.inc\\eventmainmenu.inc", 9, 180, "merge"),
           ("gui\\menu.inc\\oncamera.inc", 9, 76, "merge"),
           ("gui\\menu.inc\\zz.inc", 9, 5, "merge"),
           ("scripts\\dmscript.global", 9, 900, "wta"),
           ("scripts\\lib\\unit.script", 9, 4000, "never"),
           ("textures\\a.dds", 9, -1, "never")]
ROWS = [(p.encode(), s, n, c.encode()) for p, s, n, c in ENTRIES]
SCANNED = [e[0] for e in X.scan_entries(ROWS)]

WASD, CAM, OFF = b"mods\\QMTestWASD", b"mods\\QMTestCamSpeed", b"mods\\Off"
COPY = b"mods\\QmCopy"


@functools.lru_cache(maxsize=None)
def index_states(batch=None):
    loaded, helpers = H.load_sources()
    variables = H.build_variables([h.into for h in H.load_hooks()])
    if batch is not None:
        variables["indexbatch"] = batch
    return dict((st.name.lower(), H.state_code(st, helpers, variables)) for st in loaded
                if st.name in ("qmIndex", "qmIndexBegin", "qmIndexStep"))


class Engine(M5.Engine):
    """FileAge of a data file must never be asked of Quartermaster's folder, of
    another copy of it or of a mod that is off: the index scans none of them."""

    def __init__(self, *args, **kw):
        self.never = set()
        M5.Engine.__init__(self, *args, **kw)

    def n_FileAge(self, p):
        if not p.endswith(CORE) and b"\\data\\quartermaster\\" not in p:
            for d in self.never:
                assert not p.startswith(d + b"\\data\\"), "asked %s" % p
        return M5.Engine.n_FileAge(self, p)


def world(mods, ships, idx_at="own"):
    """`mods` = [(dir, enabled, tag)] in mods.ini order; `ships` = {dir: {path: age}}.
    Quartermaster and COPY get core.aix; vanilla.idx sits next to each core.aix
    (`own`: a copy of Quartermaster has one too, and the last enabled one is
    the folder the index reads it from), at `idx_at`, or nowhere (None)."""
    files, ages = {INI: O.render_mods_ini([(d, O.FALSE if e else O.TRUE) for d, e, _t in mods])}, {}
    for d, _e, _t in mods:
        if d in (QM, COPY):
            files[d + CORE] = b"x"
            if idx_at == "own":
                files[d + b"\\data\\quartermaster\\vanilla.idx"] = H.render_vanilla_idx(ENTRIES)
    if idx_at not in (None, "own"):
        files[idx_at] = H.render_vanilla_idx(ENTRIES)
    for d, paths in ships.items():
        for p, a in paths.items():
            files[d + b"\\data\\" + p] = b"x"
            if a is not None:
                ages[d + b"\\data\\" + p] = a
    return files, ages


def run_index(mods, files, ages, batch=None, step=None):
    eng = Engine(files, ages, mods=mods)
    M5.load(eng, "qmModList", "qmOrder", "qmModsIni")
    eng.set("qm_rt", sync=0)
    for name, code in index_states(batch).items():
        eng.states[name] = PAS.State(code, eng)
    if step is not None:
        eng.states["qmindexstep"] = step
    M5.run(eng, "qmModList")
    M5.run(eng, "qmOrder")
    on = dict((d, e) for d, e, _t in mods)
    eng.never = set(d for d, e, _t in mods if d in (QM, COPY) or not on[d])
    M5.run(eng, "qmIndex")
    return eng


def twin(mods, files, ages):
    xm = [X.Mod(d, e, t) for d, e, t in mods]

    def has_core(d):
        return d + CORE in files

    def age(d, path):
        f = d + b"\\data\\" + path
        return ages.get(f, DEFAULT_AGE) if f in files else -1

    self_index = X.find_self(xm, has_core)
    lo = O.load_order([d for d, _e, _t in mods], xm[self_index].dir if self_index >= 0 else None,
                      None, [e for _d, e, _t in mods])
    pos = X.load_positions(xm, self_index, lo.rows)
    return X.build_index(xm, self_index, ROWS, age, SHIPPED, has_core, pos), pos, self_index


def check(mods, ships, batch=None):
    files, ages = world(mods, ships)
    eng = run_index(mods, files, ages, batch)
    idx, pos, self_index = twin(mods, files, ages)
    key = functools.partial(eng.key, b"qm_index")
    n = int(key(b"n"))
    assert n == len(idx.scanned) and int(key(b"total")) == len(ROWS)
    assert [key(b"p%d" % k) for k in range(n)] == idx.scanned
    lines = dict((e[0], e) for e in ROWS)
    for k, path in enumerate(idx.scanned):
        assert key(b"l%d" % k) == b"%d" % lines[path][2]
        assert key(b"c%d" % k) == lines[path][3]
        got = idx.providers.get(path)
        want_v = b";".join(b"%d" % pos[i] for i in got) if got else b"-"
        want_a = b";".join(b"-" if a is None else b"%d" % a for a in idx.ages[path]) if got else b"-"
        assert (key(b"v%d" % k), key(b"a%d" % k)) == (want_v, want_a), path
        assert eng.key(b"qm_index_keys", X.index_key(path)) == b"%d" % k
    for i, stamp in idx.stamps.items():
        assert key(b"st%d" % pos[i]) == stamp, mods[i][0]
    assert int(key(b"calls")) == idx.calls and key(b"done") == b"1"
    assert int(key(b"cur")) == n
    return eng, idx


MODS = [(WASD, True, b"0"), (W + b"5", True, b"5"), (OFF, False, b"0"), (COPY, True, b"0"),
        (QM, True, b"0"), (CAM, True, b"0")]
SHIPS = {WASD: {b"game\\var\\hotkeys.cfg": 101, b"gui\\menu.inc\\oncamera.inc": 102,
                b"gui\\menu.inc\\cameracontrol.inc": 103},
         CAM: {b"gui\\menu.inc\\oncamera.inc": 201, b"textures\\a.dds": 202,
               b"scripts\\dmscript.global": None},
         OFF: {b"gui\\menu.inc\\oncamera.inc": 301},
         COPY: {b"gui\\menu.inc\\zz.inc": 401},
         QM: {b"gui\\menu.inc\\cameracontrol.inc": 1, b"gui\\menu.inc\\doprogress.inc": 1},
         W + b"5": {b"gui\\menu.inc\\zz.inc": 501, b"game\\var\\units.cfg": 502}}


def test_the_index_finds_what_the_twin_finds():
    eng, idx = check(MODS, SHIPS)
    # Quartermaster provides the hook files it ships, without a FileAge.
    k = SCANNED.index(b"gui\\menu.inc\\cameracontrol.inc")
    assert eng.key(b"qm_index", b"a%d" % k).endswith(b";-")
    assert idx.providers[b"gui\\menu.inc\\doprogress.inc"] == [4]
    # A path outside the scan list is never asked, whoever ships it.
    assert b"textures\\a.dds" not in SCANNED and b"game\\var\\units.cfg" not in SCANNED
    text = b"\n".join(eng.log)
    assert b"[qm] index scan list %d of %d vanilla.idx entries from %s" % (
        len(SCANNED), len(ROWS), IDX) in text
    provided = sum(1 for p in SCANNED if p in idx.providers)
    assert b"[qm] index scanned=%d provided=%d fileage calls=%d steps=1 " % (
        len(SCANNED), provided, idx.calls) in text


@pytest.mark.parametrize("batch", [1, 2, 3, 7])
def test_a_scan_spread_over_steps_finds_the_same(batch):
    """`indexbatch` paths per call: the cursor moves on, the stamps carry over
    from call to call, and the driver calls until done."""
    eng, _idx = check(MODS, SHIPS, batch=batch)
    steps = -(-len(SCANNED) // batch)
    assert eng.calls.count("qmIndexStep") == steps
    assert b"steps=%d " % steps in b"\n".join(eng.log)


def test_random_worlds_agree_with_the_twin():
    rng = random.Random(20261002)
    pool = [WASD, CAM, OFF, W + b"5", W + b"77", b"mods\\Alpha", b"mods\\zeta", COPY]
    paths = [e[0] for e in ROWS]
    for _ in range(25):
        dirs = rng.sample(pool, rng.randint(1, len(pool)))
        mods = [(d, rng.random() < 0.8, d.rsplit(b"\\", 1)[1] if d.startswith(W) else b"0")
                for d in dirs]
        mods.insert(rng.randint(0, len(mods)), (QM, True, b"0"))
        ships = dict((d, dict((p, rng.choice([None, rng.randint(1, 10 ** 9)]))
                              for p in rng.sample(paths, rng.randint(0, 5))))
                     for d in dirs)
        check(mods, ships, batch=rng.choice([None, 1, 4]))


def test_a_step_that_makes_no_progress_ends_the_scan():
    """A qmIndexStep that did not compile leaves the cursor where it was: the
    driver says so and stops instead of hanging the game."""
    files, ages = world(MODS, SHIPS)
    eng = run_index(MODS, files, ages, step=M5.Fake(lambda: None))
    text = b"\n".join(eng.log)
    assert b"[qm] index step made no progress at 0; scan abandoned" in text
    assert b"[qm] index scanned=%d provided=0 fileage calls=0 steps=2 " % len(SCANNED) in text
    assert eng.key(b"qm_index", b"done") == b"0"


def test_without_vanilla_idx_the_scan_list_is_empty():
    files, ages = world(MODS, SHIPS, idx_at=None)
    eng = run_index(MODS, files, ages)
    assert eng.key(b"qm_index", b"n") == b"0" and eng.key(b"qm_index", b"total") == b"0"
    assert eng.key(b"qm_index", b"done") == b"1" and eng.key(b"qm_index", b"calls") == b"0"


def test_without_its_own_folder_the_index_reads_vanilla_idx_through_the_overlay():
    """No enabled mod ships core.aix (qmModList found no folder of its own):
    vanilla.idx comes from .\\data\\quartermaster\\, and no mod provides a
    path for Quartermaster."""
    mods = [(WASD, True, b"0"), (CAM, True, b"0")]
    files, ages = world(mods, SHIPS, idx_at=b".\\data\\quartermaster\\vanilla.idx")
    eng = run_index(mods, files, ages)
    idx, pos, self_index = twin(mods, files, ages)
    assert self_index == -1 and eng.key(b"qm_rt", b"qmdir") == b""
    n = int(eng.key(b"qm_index", b"n"))
    assert n == len(SCANNED)
    for k, path in enumerate(SCANNED):
        got = idx.providers.get(path)
        assert eng.key(b"qm_index", b"v%d" % k) == (
            b";".join(b"%d" % pos[i] for i in got) if got else b"-")
