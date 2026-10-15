"""The load order (plan S11) run offline: qmOrder, qmUiOrder, the
boot's report lines about the order, qmFingerprint over a load order and the
SelfTest steps of qmCaseM5 that exercise them, as the build emits them, in the
interpreter of tests/test_m3_pascal.py over the emulated engine of
tests/test_m5_pascal.py. They must decide and write exactly what ref/order.py
(load_order, apply_order, load_rows, order_file_after, ui_move) and
ref/fingerprint.py say.
"""
import itertools
import random

import pytest

import test_m5_pascal as M5
from ref import boot as B
from ref import fingerprint as FP
from ref import inc as I
from ref import order as O
from ref import textio as T

QM = M5.QM
W = M5.W
INI = M5.INI
SAVE = M5.SAVE
ORDER = SAVE + b"quartermaster\\order.cfg"
SWFP = b"mods\\SW_Frontline_Protocol"
WS = W + b"873048118"
WASD = b"mods\\QMTestWASD"
CONF = b"mods\\QMTestConflict"
CAM = b"mods\\QMTestCamSpeed"
NEW = b"mods\\QMTestNew"
POOL = [SWFP, WS, W + b"77", WASD, CONF, CAM, NEW]


class Engine(M5.Engine):
    """test_m5_pascal's engine with DeleteFileStream (M0: works, silent on a
    missing file) and the file it deletes gone for FileAge and the parser."""

    def __init__(self, *args, **kw):
        self.deleted = set()
        M5.Engine.__init__(self, *args, **kw)

    def _file(self, path):
        if path in self.deleted:
            return None
        return M5.Engine._file(self, path)

    def n_DeleteFileStream(self, path):
        self.written.pop(path, None)
        self.deleted.add(path)

    def n_OpenFileStreamForWrite(self, path):
        self.deleted.discard(path)
        return M5.Engine.n_OpenFileStreamForWrite(self, path)

    def n_SameText(self, a, b):
        # Equal but for ASCII case (as tests/test_m6_selftest.py has it).
        return O.ascii_lower(a) == O.ascii_lower(b)


def rows_of(mods):
    return [(d, O.FALSE if e else O.TRUE) for d, e, _t in mods]


# ------------------------------------------------------------- qmOrder
def order_run(mods, saved=None, flags=None, order=None, sync=False):
    """qmModList + qmOrder (+ qmModsIni) over `mods` = [(dir, enabled, tag)]
    in mods.ini order; `saved` = order.cfg's bytes (None: no file); `flags`
    = an Apply's [(dir, off)] (None: a boot); `order` = the Apply's dirs."""
    files = {INI: O.render_mods_ini(rows_of(mods)),
             QM + b"\\data\\quartermaster\\core.aix": b"x"}
    if saved is not None:
        files[ORDER] = saved
    eng = Engine(files, mods=mods)
    M5.load(eng, "qmModList", "qmOrder", "qmModsIni")
    kw = {}
    if flags is not None:
        kw = dict(runmode=b"apply", uiapplyn=len(flags))
        for j, (d, off) in enumerate(flags):
            kw["uiapplydir%d" % j] = d
            kw["uiapplydis%d" % j] = 1 if off else 0
        if order is not None:
            kw["uiapplyorder"] = 1
            kw["uiapplyordn"] = len(order)
            for k, d in enumerate(order):
                kw["uiapplyord%d" % k] = d
    eng.set("qm_rt", sync=1 if sync else 0, **kw)
    M5.run(eng, "qmModList")
    M5.run(eng, "qmOrder")
    return eng


def twin(mods, saved=None, flags=None, order=None):
    dirs = [d for d, _e, _t in mods]
    intent = None if flags is None else dict((O.norm_dir(d), off) for d, off in flags)
    on = [e for _d, e, _t in mods]
    if intent:
        on = [(not intent[O.norm_dir(d)]) if O.norm_dir(d) in intent and d != QM else e
              for d, e, _t in mods]
    have = O.parse_order(saved)
    if flags is None:
        lo = O.load_order(dirs, QM, have, on)
    else:
        lo = O.apply_order(dirs, QM, have, order, on)
    return lo, on, intent


def _keys(eng, parser, fmt, n):
    return [eng.key(parser, fmt % k) for k in range(n)]


def check_order(mods, saved=None, flags=None, order=None, sync=False):
    eng = order_run(mods, saved, flags, order, sync)
    lo, on, intent = twin(mods, saved, flags, order)
    n = len(mods)
    where = (mods, saved, flags, order, sync)
    assert [int(v) for v in _keys(eng, b"qm_mods", b"ord%d", n)] == lo.rows, where
    assert [int(eng.key(b"qm_mods", b"pos%d" % i)) for i in range(n)] == [
        lo.rows.index(i) for i in range(n)], where
    canon = O.canonical_indices([d for d, _e, _t in mods], QM)
    assert [int(v) for v in _keys(eng, b"qm_mods", b"cord%d", n)] == canon, where
    assert [int(eng.key(b"qm_mods", b"cpos%d" % i)) for i in range(n)] == [
        canon.index(i) for i in range(n)], where
    en = int(eng.key(b"qm_mods", b"en"))
    assert [int(v) for v in _keys(eng, b"qm_mods", b"e%d", en)] == [
        i for i in lo.rows if on[i] and mods[i][0] != QM], where
    assert eng.key(b"qm_order", b"src") == lo.src, where
    assert eng.key(b"qm_order", b"canon") == (b"1" if lo.canon else b"0"), where
    assert eng.key(b"qm_order", b"ext") == (b"1" if lo.ext else b"0"), where
    assert eng.key(b"qm_order", b"why") == lo.why, where
    un = int(eng.key(b"qm_order", b"unseen"))
    assert _keys(eng, b"qm_order", b"u%d", un) == [mods[i][0] for i in lo.unseen], where
    dr = int(eng.key(b"qm_order", b"dropped"))
    assert _keys(eng, b"qm_order", b"d%d", dr) == lo.dropped, where
    action, data = O.order_file_after(lo, saved, sync)
    assert eng.key(b"qm_order", b"file") == action, where
    if action == b"written":
        assert eng.written[ORDER] == data, where
    elif action == b"deleted":
        assert ORDER in eng.deleted, where
    else:
        assert ORDER not in eng.written and ORDER not in eng.deleted, where
    # mods.ini: the load order's rows, through the same writer and checks.
    ini = eng.key(b"qm_ini", b"action")
    if sync:
        assert ini == b"skipped" and INI not in eng.written, where
    else:
        plan = O.mods_ini_plan([(d, e) for d, e, _t in mods], O.render_mods_ini(rows_of(mods)),
                               O.load_rows(rows_of(mods), QM, lo, intent))
        assert ini == {b"same": b"same", b"write": b"written"}[plan.action], where
        assert eng.key(b"qm_ini", b"effective") == (b"1" if plan.effective else b"0"), where
        if plan.action == b"write":
            assert eng.written[INI] == O.render_mods_ini(plan.rows), where
    return eng, lo


def random_case(rng):
    k = rng.randint(1, 6)
    dirs = rng.sample(POOL, k) + [QM]
    rng.shuffle(dirs)
    mods = [(d, d == QM or rng.random() < 0.7, b"0") for d in dirs]
    saved = None
    r = rng.random()
    if r < 0.6:
        pick = rng.sample(dirs, rng.randint(0, len(dirs)))
        if rng.random() < 0.3:
            pick.append(b"mods\\Gone%d" % rng.randint(1, 3))
        if rng.random() < 0.2 and pick:
            j = rng.randrange(len(pick))
            pick[j] = pick[j].upper()
        rng.shuffle(pick)
        saved = O.render_order(pick) if pick else None
    elif r < 0.7:
        # A state file that is not an order.cfg: no format line.
        saved = T.write_file(I.layout_lines(O.ORDER_KEYS, [b";o~124" + dirs[0], b";x"]))
    flags = order = None
    if rng.random() < 0.4:
        flags = [(d, rng.random() < 0.3) for d in dirs]
        r = rng.random()
        if r < 0.5:
            order = list(dirs)
            rng.shuffle(order)
        elif r < 0.6:
            order = list(dirs)[:-1] + [rng.choice([b"mods\\Other", dirs[0]])]
    return mods, saved, flags, order, rng.random() < 0.1


def test_the_load_order_equals_ref_over_random_mod_sets():
    rng = random.Random(28)
    kinds = set()
    for _ in range(160):
        mods, saved, flags, order, sync = random_case(rng)
        _eng, lo = check_order(mods, saved, flags, order, sync)
        kinds.add((lo.src, lo.ext, lo.canon, bool(lo.unseen), bool(lo.dropped), lo.why))
    srcs = set(k[0] for k in kinds)
    assert srcs == {b"ini", b"saved", b"apply"}
    assert any(k[1] for k in kinds) and any(not k[2] for k in kinds)
    assert any(k[3] for k in kinds) and any(k[4] for k in kinds)
    assert any(k[5] for k in kinds)


@pytest.mark.parametrize("saved, flags, order, want_file", [
    (None, None, None, b"same"),                                           # rule 1
    ([CONF, WASD, SWFP, WS], None, None, b"same"),                         # already so
    ([CONF, b"mods\\Gone", WASD, SWFP], None, None, b"written"),           # dropped + unseen
    ([b"mods\\Gone"], None, None, b"deleted"),                             # nothing placed
    (None, [], [WASD, CONF, SWFP, QM, WS], b"written"),                    # an Apply's order
    ([CONF, WASD, SWFP, WS], [], None, b"same"),                           # an Apply of flags
])
def test_order_cfg_is_written_only_when_its_content_changes(saved, flags, order, want_file):
    mods = [(SWFP, False, b"0"), (WS, False, b"873048118"), (WASD, True, b"0"), (QM, True, b"0"),
            (CONF, True, b"0")]
    data = O.render_order(saved) if saved is not None else None
    eng, _lo = check_order(mods, data, flags, order)
    assert eng.key(b"qm_order", b"file") == want_file


def test_mods_ini_s_own_order_through_an_apply_deletes_the_saved_one():
    mods = [(SWFP, False, b"0"), (WASD, True, b"0"), (QM, True, b"0"), (CONF, True, b"0")]
    eng, lo = check_order(mods, O.render_order([WASD, CONF, SWFP]), [], [SWFP, WASD, CONF, QM])
    assert lo.src == b"apply" and eng.key(b"qm_order", b"file") == b"deleted"
    assert ORDER in eng.deleted
    # Auto-sort's canonical order is an order like any other: saved.
    canon = O.canonical_order([d for d, _e, _t in mods], QM)
    eng, lo = check_order(mods, O.render_order([WASD, CONF, SWFP]), [], canon)
    assert eng.key(b"qm_order", b"file") == b"written" and lo.canon


def test_an_mp_sync_writes_neither_mods_ini_nor_order_cfg():
    mods = [(WASD, True, b"0"), (QM, True, b"0"), (CONF, True, b"0")]
    eng, lo = check_order(mods, O.render_order([b"mods\\Gone", WASD]), sync=True)
    assert lo.dropped and eng.key(b"qm_order", b"file") == b"same"
    assert b"[qm] order: mods.ini and order.cfg left alone during an MP mod sync" in eng.log


def test_the_load_positions_are_logged_for_the_replay():
    mods = [(CONF, True, b"0"), (WASD, True, b"0"), (QM, True, b"0")]
    eng, _lo = check_order(mods, O.render_order([WASD, CONF]))
    assert b"[qm] order: mod 1 pos=0 (canonical 1)" in eng.log
    assert b"[qm] order: mod 0 pos=1 (canonical 0)" in eng.log
    assert any(l.startswith(b"[qm] order: src=saved canon=0 ext=1 unseen=0 dropped=0")
               for l in eng.log)


@pytest.mark.parametrize("old, new", [
    (b"(qmOrRow[qmOrK]<qmOrRow[qmOrK-1])", b"(qmOrRow[qmOrK]>qmOrRow[qmOrK-1])"),
    (b"(qmOrTaken[qmOrI]=0) and (qmOrIsSelf[qmOrI]=0) then", b"(qmOrIsSelf[qmOrI]=0) then"),
    (b"qmOrDelete := (qmOrHave=1)", b"qmOrDelete := False"),
    (b"'cpos'+IntToStr(qmOrCan[qmOrK]), qmOrK", b"'cpos'+IntToStr(qmOrK), qmOrK"),
])
def test_a_wrong_load_order_is_caught(old, new):
    """The gate has teeth: each mutation changes some decision."""
    M5.PATCH["qmorder"] = (old, new)
    try:
        with pytest.raises(AssertionError):
            rng = random.Random(28)
            for _ in range(160):
                check_order(*random_case(rng))
    finally:
        M5.PATCH.clear()


# ------------------------------------------------------------ qmUiOrder
MSG = {None: b"", O.UI_UNKNOWN: b"Unknown order command.",
       O.UI_SELECT: b"Select a mod in the Active list first.",
       O.UI_SELF: b"Quartermaster always loads last.",
       O.UI_INACTIVE: b"Only an active mod has a place in the load order.",
       O.UI_FIRST: b"This mod loads first already.",
       O.UI_LAST: b"This mod loads last already; only Quartermaster comes after it."}


def ui_run(order, oord, pending, self_row, row, cmd, to):
    eng = Engine()
    M5.load(eng, "qmUiOrder")
    kw = dict(n=len(order), ocmd=cmd, arg=row, argto=to)
    for k, i in enumerate(order):
        kw["ord%d" % k] = i
        kw["oord%d" % k] = oord[k]
    for i, p in enumerate(pending):
        kw["pe%d" % i] = 1 if p else 0
        kw["dir%d" % i] = b"mods\\m%d" % i
    ui = eng.set("qm_ui", **kw)
    eng.n_ParserSetValueByKeyByHandle(ui, b"self", b"%d" % self_row)
    M5.run(eng, "qmUiOrder")
    return eng


def test_the_window_moves_equal_ref():
    rng = random.Random(11)
    seen = set()
    for _ in range(300):
        n = rng.randint(2, 6)
        order = list(range(n))
        rng.shuffle(order)
        self_row = order[-1]
        pending = [rng.random() < 0.7 or i == self_row for i in range(n)]
        oord = list(order) if rng.random() < 0.6 else rng.sample(order, n)
        row = rng.randrange(-1, n + 1)
        cmd = rng.choice([b"up", b"down", b"move", b"move", b"sideways"])
        to = rng.randint(-2, n + 2)
        eng = ui_run(order, oord, pending, self_row, row, cmd, to)
        new, moved, why = O.ui_move(order, pending, self_row, row, cmd, to)
        where = (order, oord, pending, self_row, row, cmd, to)
        assert [int(eng.key(b"qm_ui", b"ord%d" % k)) for k in range(n)] == new, where
        assert eng.key(b"qm_ui", b"omoved") == (b"1" if moved else b"0"), where
        assert eng.key(b"qm_ui", b"ordchg") == (b"1" if new != oord else b"0"), where
        assert eng.key(b"qm_ui", b"msg") == MSG[why], where
        assert any(l.startswith(b"[qm] ui order " + cmd + b" row=%d to=%d moved=%d"
                                % (row, to, moved)) for l in eng.log), where
        seen.add(why)
    assert seen == set(MSG)


def test_a_move_back_clears_the_pending_change():
    order = [0, 1, 2]
    eng = ui_run(order, order, [True, True, True], 2, 1, b"up", 0)
    assert eng.key(b"qm_ui", b"ordchg") == b"1"
    moved = [int(eng.key(b"qm_ui", b"ord%d" % k)) for k in range(3)]
    eng2 = ui_run(moved, order, [True, True, True], 2, 1, b"down", 0)
    assert [int(eng2.key(b"qm_ui", b"ord%d" % k)) for k in range(3)] == order
    assert eng2.key(b"qm_ui", b"ordchg") == b"0"


# ------------------------------------------------- the boot's report lines
def boot_lines(mods, saved=None, marker=None):
    eng, _rt = M5.boot_engine(marker, mods=mods)
    eng.__class__ = Engine
    eng.deleted = set()
    if saved is not None:
        eng.fs[ORDER] = saved
    M5.run(eng, "qmBoot")
    return [eng.key(b"qm_boot", b"l%d" % k) for k in range(int(eng.key(b"qm_boot", b"n")))], eng


def test_an_outside_reorder_is_put_back_and_said_with_the_mp_note():
    mods = [(CONF, True, b"0"), (WASD, True, b"0"), (QM, True, b"0")]
    lines, eng = boot_lines(mods, O.render_order([WASD, CONF]))
    moves = WASD + b" 2->1; " + CONF + b" 1->2"
    assert (b"OK mods.ini was reordered outside Quartermaster (in modman?): the saved load "
            b"order was put back, Quartermaster last. Moved: " + moves + b".") in lines
    assert (b"OK Multiplayer: every player needs the same mods in the same load order."
            in lines)
    rows, _p = O.parse_mods_ini(eng.written[INI])
    assert [d for d, _dis in rows] == [WASD, CONF, QM]


def test_a_new_mod_is_placed_after_the_saved_order_and_said():
    mods = [(WASD, True, b"0"), (CONF, True, b"0"), (QM, True, b"0"), (NEW, True, b"0")]
    lines, eng = boot_lines(mods, O.render_order([WASD, CONF]))
    assert (b"OK Not in the saved load order yet, so placed after it, before Quartermaster: "
            + NEW + b".") in lines
    assert (b"OK mods.ini was put into the saved load order, Quartermaster last. Moved: "
            + NEW + b" 4->3; " + QM + b" 3->4.") in lines
    assert O.parse_order(eng.written[ORDER]) == [WASD, CONF, NEW]


def test_the_canonical_order_says_nothing_about_mp():
    mods = [(CONF, True, b"0"), (WASD, True, b"0"), (QM, True, b"0")]
    lines, _eng = boot_lines(mods)
    assert not any(b"Multiplayer:" in l for l in lines)
    lines, _eng = boot_lines(mods, O.render_order([CONF, WASD]))
    assert lines == []


def test_the_apply_boot_says_the_order_was_chosen_in_the_manager():
    mods = [(CONF, True, b"0"), (WASD, True, b"0"), (QM, True, b"0")]
    eng, _rt = M5.boot_engine(B.Marker(gen=1, hash=b"1-2-3"), changed=1, mods=mods)
    eng.__class__ = Engine
    eng.deleted = set()
    # The Apply runs in the process whose boot loaded the marker.
    eng.set("qm_state", have=1, gen=1, hash=b"1-2-3", phase=b"booted", mode=b"normal", rows=0,
            rhash=b"-", rcount=0, rk=b"-", boots=1, on=0)
    eng.set("qm_rt", runmode=b"apply", uiapplyn=0, uiapplyorder=1, uiapplyordn=3,
            uiapplyord0=WASD, uiapplyord1=CONF, uiapplyord2=QM, uiapplyseq=1)
    M5.run(eng, "qmBoot")
    lines = [eng.key(b"qm_boot", b"l%d" % k) for k in range(int(eng.key(b"qm_boot", b"n")))]
    assert any(l.startswith(b"OK mods.ini was put into the load order chosen in the manager")
               for l in lines)
    assert eng.key(b"qm_guard", b"kind") == b"apply" and eng.key(b"qm_rt", b"rs") == b"1"
    # The Apply's restart is the tick's, after its notice: never the boot's.
    assert eng.restarted == []
    assert O.parse_order(eng.written[ORDER]) == [WASD, CONF]


# ------------------------------------------------------- the fingerprint
def test_the_fingerprint_lines_follow_the_load_order():
    mods = [(SWFP, False, b"0"), (WS, True, b"873048118"), (WASD, True, b"0"), (QM, True, b"0"),
            (CONF, True, b"0")]
    for saved in (None, [CONF, WASD, SWFP, WS]):
        eng = order_run(mods, O.render_order(saved) if saved else None)
        M5.load(eng, "qmFingerprint")
        idx = eng.set("qm_index", n=0)
        stamps = {}
        for k in range(len(mods)):
            eng.n_ParserSetValueByKeyByHandle(idx, b"st%d" % k, b"9-9-%d" % k)
        for i, (d, _e, _t) in enumerate(mods):
            stamps[d] = b"9-9-%d" % int(eng.key(b"qm_mods", b"pos%d" % i))
        M5.run(eng, "qmFingerprint")
        lines = [eng.key(b"qm_fp", b"l%d" % m) for m in range(int(eng.key(b"qm_fp", b"n")))]
        exe = b"exe %d\n" % eng.n_FileAge(eng.n_GetApplicationFileName())
        vstamp = FP.qhash(exe)
        order = [mods[int(eng.key(b"qm_mods", b"ord%d" % k))][0] for k in range(len(mods))]
        want = FP.fingerprint_text([(d, e, stamps[d]) for d, e, _t in mods], vstamp,
                                   M5.H.QM_VERSION.encode(), QM, order)
        assert b"".join(l + b"\n" for l in lines) == want
        assert eng.key(b"qm_fp", b"hash") == FP.qhash(want)


def test_the_fingerprint_without_the_mods_registered_at_this_start():
    """qm_fp old / qm_rt fpold (ref/index.py known_fingerprint): NEW's line
    left out; a path only NEW ships leaves the vanilla stamp, one it shares
    with WASD stays. With none registered now it is the fingerprint."""
    mods = [(WASD, True, b"0"), (NEW, True, b"0"), (QM, True, b"0"), (CONF, False, b"0")]
    only, shared, none = b"gui\\menu.inc\\a.inc", b"gui\\menu.inc\\b.inc", b"gui\\menu.inc\\c.inc"
    for frn in (1, 0):
        eng = order_run(mods)
        M5.load(eng, "qmFingerprint")
        pos = dict((d, int(eng.key(b"qm_mods", b"pos%d" % i))) for i, (d, _e, _t) in
                   enumerate(mods))
        idx = eng.set("qm_index", n=3, p0=only, v0=b"%d" % pos[NEW], p1=shared,
                      v1=b"%d;%d" % (pos[WASD], pos[NEW]), p2=none, v2=b"-")
        for k in range(len(mods)):
            eng.n_ParserSetValueByKeyByHandle(idx, b"st%d" % k, b"9-9-%d" % k)
        eng.set("qm_known", frn=frn, fr0=0, fr1=frn, fr2=0, fr3=0)
        M5.run(eng, "qmFingerprint")
        app = eng.n_ExtractFilePath(eng.n_GetApplicationFileName()) + b"data\\"
        age = dict((p, eng.n_FileAge(app + p)) for p in (only, shared))
        exe = b"exe %d\n" % eng.n_FileAge(eng.n_GetApplicationFileName())
        order = [mods[int(eng.key(b"qm_mods", b"ord%d" % k))][0] for k in range(len(mods))]
        rows = [(d, e, b"9-9-%d" % pos[d]) for d, e, _t in mods]
        v = FP.qhash(b"".join(p + b" %d\n" % age[p] for p in (only, shared)) + exe)
        fp = FP.qhash(FP.fingerprint_text(rows, v, M5.H.QM_VERSION.encode(), QM, order))
        assert eng.key(b"qm_fp", b"hash") == fp == eng.key(b"qm_rt", b"fp")
        if frn:
            v_old = FP.qhash(shared + b" %d\n" % age[shared] + exe)
            old = FP.qhash(FP.fingerprint_text([r for r in rows if r[0] != NEW], v_old,
                                               M5.H.QM_VERSION.encode(), QM, order))
        else:
            old = fp
        assert eng.key(b"qm_fp", b"old") == old == eng.key(b"qm_rt", b"fpold")


# ------------------------------------------------------- SelfTest steps
def case_engine(lines, mods, boots=2, regen=0, restart=0, saved=None):
    """qmCaseM5 after a boot of `mods`, with the case's directive lines."""
    eng = order_run(mods, saved)
    eng.deleted = set()
    M5.load(eng, "qmCaseM5", "qmModsIni", "qmMarkerSave", "qmRestart")
    out = SAVE + b"qm_test\\out\\"
    eng.set("qm_case_rt", outdir=out, out=out + b"qm_m5.txt", status=b"started")
    case = eng.n_ParserCreate(b"qm_case")
    eng.fs[SAVE + b"case.cfg"] = T.write_file(I.layout_lines([b"Name = qmCase"],
                                                             [b";kind m5"] + lines))
    eng.n_ParserLoadFromFileByHandle(case, SAVE + b"case.cfg")
    eng.set("qm_state", boots=boots, phase=b"booted", gen=1, hash=b"1-2-3", mode=b"normal",
            rows=0, rhash=b"-", rcount=0, rk=b"-", on=0)
    eng.set("qm_guard", why=b"stable", kind=b"-", refused=b"", restart=restart, regen=regen)
    eng.set("qm_known", newn=0)
    if INI in eng.written:
        eng.fs[INI] = eng.written.pop(INI)          # the boot's file
    return eng, out


def test_the_reverse_shuffle_reorders_the_placed_mods_too():
    mods = [(WASD, True, b"0"), (CONF, True, b"0"), (NEW, True, b"0"), (QM, True, b"0")]
    eng, out = case_engine([b";step shuffle", b";reverse 1", b";new " + NEW], mods,
                           saved=O.render_order([WASD, CONF, NEW]))
    M5.run(eng, "qmCaseM5")
    rows, _p = O.parse_mods_ini(eng.written[INI])
    assert [d for d, _dis in rows] == [QM, NEW, CONF, WASD]
    assert eng.key(b"qm_rt", b"rskind") == b"test" and out + b"m5_shuffle.done" in eng.written
    # The next boot puts the saved order back and says it was reordered outside.
    again = [(d, dis == O.FALSE, b"0") for d, dis in rows]
    lo = O.load_order([d for d, _e, _t in again], QM, [WASD, CONF, NEW])
    assert lo.ext and [again[i][0] for i in lo.rows] == [WASD, CONF, NEW, QM]


def _stand_in_controller(eng):
    """qmUiAct / qmUiModel / qmUiApply as docs/ui.md and the agreed contract
    describe them (the window's own states are desk-checked by its tests):
    open copies qm_mods' load order into ord<k> and oord<k>; up / down /
    move run the real qmUiOrder; apply asks for the dialog when a flag or
    the order changed; confirm records qm_rt uiapply*."""
    ui = eng.named[b"qm_ui"]

    def act():
        get = lambda k: eng.n_ParserGetValueByKeyByHandle(ui, k)
        put = lambda k, v: eng.n_ParserSetValueByKeyByHandle(ui, k, v if isinstance(v, bytes)
                                                             else b"%d" % v)
        cmd = get(b"cmd")
        put(b"cmd", b"")
        n = int(eng.key(b"qm_mods", b"n"))
        if cmd == b"open":
            put(b"n", n)
            put(b"self", int(eng.key(b"qm_mods", b"self")))
            for i in range(n):
                put(b"dir%d" % i, eng.key(b"qm_mods", b"dir%d" % i))
                put(b"en%d" % i, int(eng.key(b"qm_mods", b"on%d" % i)))
                put(b"pe%d" % i, int(eng.key(b"qm_mods", b"on%d" % i)))
            for k in range(n):
                put(b"ord%d" % k, int(eng.key(b"qm_mods", b"ord%d" % k)))
                put(b"oord%d" % k, int(eng.key(b"qm_mods", b"ord%d" % k)))
            put(b"ordchg", 0)
            put(b"sel", -1)
            put(b"mode", 0)
        elif cmd == b"select":
            put(b"sel", int(get(b"arg")))
        elif cmd in (b"up", b"down", b"move"):
            put(b"ocmd", cmd)
            M5.run(eng, "qmUiOrder")
        elif cmd == b"apply":
            chg = sum(1 for i in range(n) if get(b"pe%d" % i) != get(b"en%d" % i))
            if chg or get(b"ordchg") == b"1":
                put(b"mode", 1)
        elif cmd == b"confirm" and get(b"mode") == b"1":
            put(b"mode", 0)
            rt = {"uiapply": 1, "uiapplyseq": 1, "uiapplyn": n, "uiapplyordn": n,
                  "uiapplyorder": int(get(b"ordchg")), "uiregen": 1}
            for k in range(n):
                rt["uiapplyord%d" % k] = eng.key(b"qm_ui", b"dir" + get(b"ord%d" % k))
            eng.set("qm_rt", **rt)
    return act


def test_the_uiorder_step_moves_a_mod_and_leaves_the_apply_for_the_tick():
    mods = [(CONF, True, b"0"), (WASD, True, b"0"), (QM, True, b"0")]
    eng, out = case_engine([b";step uiorder", b";mod " + WASD, b";cmd up"], mods)
    M5.load(eng, "qmUiOrder")
    eng.n_ParserCreate(b"qm_ui")
    eng.states["qmuiact"] = M5.Fake(_stand_in_controller(eng))
    M5.run(eng, "qmCaseM5")
    dump = eng.written[out + b"m5_uiorder_2.txt"]
    assert b"order|ini|1|0|" + CONF + b" | " + WASD + b" | " + QM + b"\r\n" in dump
    assert b"ui|up|1|1|1|0|0|\r\n" in dump
    assert b"ui|confirm|1|0|1|0|1|\r\n" in dump
    assert b"kept|1|1|3|1\r\n" in dump
    assert b"apply|0|" + WASD + b"\r\n" in dump and b"apply|1|" + CONF + b"\r\n" in dump
    assert out + b"m5_uiorder.done" in eng.written
    assert eng.key(b"qm_case_rt", b"status") == b"ok"
    # What the tick's Apply boot then does with it (qmOrder, the twin).
    lo = O.apply_order([d for d, _e, _t in mods], QM, None, [WASD, CONF, QM])
    assert [mods[i][0] for i in lo.rows] == [WASD, CONF, QM] and not lo.canon


def test_the_uiorder_step_through_the_window_s_own_controller():
    """The same step with the window's real states (qmUiAct, qmUiModel,
    qmUiDetails, qmUiApply) in place of the stand-in: the contract agreed
    with the window holds end to end."""
    mods = [(CONF, True, b"0"), (WASD, True, b"0"), (QM, True, b"0")]
    eng, out = case_engine([b";step uiorder", b";mod " + WASD, b";cmd up"], mods)
    M5.load(eng, "qmUiOrder", "qmUiAct", "qmUiModel", "qmUiDetails", "qmUiApply", "qmAbRules")
    M5.run(eng, "qmCaseM5")
    dump = eng.written[out + b"m5_uiorder_2.txt"]
    assert b"ui|up|1|1|1|0|0|\r\n" in dump, dump
    assert b"kept|1|1|3|1\r\n" in dump, dump
    assert [eng.key(b"qm_rt", b"uiapplyord%d" % k) for k in range(3)] == [WASD, CONF, QM]
    assert eng.key(b"qm_rt", b"uiapplychg") == b"0"
    assert out + b"m5_uiorder.done" in eng.written
    assert eng.key(b"qm_rt", b"uiapplyorder") == b"1"
    # The tick's Apply boot takes that vector (qmOrder in runmode apply).
    got = order_run(mods, flags=[], order=[WASD, CONF, QM])
    assert [mods[int(got.key(b"qm_mods", b"ord%d" % k))][0] for k in range(3)] == [
        WASD, CONF, QM]
    assert got.key(b"qm_order", b"src") == b"apply"


@pytest.mark.parametrize("regen, restart", [(1, 1), (1, 0), (0, 1)])
def test_the_uiorder_step_waits_for_a_life_with_nothing_pending(regen, restart):
    mods = [(CONF, True, b"0"), (WASD, True, b"0"), (QM, True, b"0")]
    eng, out = case_engine([b";step uiorder", b";mod " + WASD, b";cmd up"], mods,
                           regen=regen, restart=restart)
    M5.run(eng, "qmCaseM5")
    assert (b"wait|regen=%d|restart=%d\r\n" % (regen, restart)
            in eng.written[out + b"m5_uiorder_2.txt"])
    assert out + b"m5_uiorder.done" not in eng.written and eng.key(b"qm_rt", b"uiapply") == b""


def test_a_later_life_of_the_uiorder_step_says_done_with_the_saved_order():
    mods = [(WASD, True, b"0"), (CONF, True, b"0"), (QM, True, b"0")]
    eng, out = case_engine([b";step uiorder", b";mod " + WASD, b";cmd up"], mods, boots=3,
                           saved=O.render_order([WASD, CONF]))
    eng.fs[out + b"m5_uiorder.done"] = b"uiorder|2\r\n"
    M5.run(eng, "qmCaseM5")
    dump = eng.written[out + b"m5_uiorder_3.txt"]
    assert b"order|saved|0|0|" in dump and b"done|1\r\n" in dump
    assert any(l.startswith(b"[qm] m5 uiorder done") for l in eng.log)
