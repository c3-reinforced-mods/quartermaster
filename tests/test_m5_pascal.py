"""The boot's states run offline: qmMarkerLoad, qmGuard, qmMarkerSave, qmKnown,
qmModList + qmOrder + qmModsIni, qmTick and qmBoot as the build emits them,
executed by the script interpreter of tests/test_m3_pascal.py over an emulated
engine, must decide and write exactly what ref/boot.py and ref/order.py say.

A desk check, not a model of the compiler (the lints and the in-game runs do
that). The emulated engine adds to test_m3_pascal's what these states use: a
file system with FileAge values, the mod list (ModLibraryGetData), mods.ini
as the parser's tree (a `mods` node of entries with dir / dis), and a clock.
A file the raw writer padded after its last line is loaded like any other
(the engine's parser did so in SelfTest run m2a3). The dotted engine
globals the states read (gMap.gamestage) are replaced by natives before
parsing, since the interpreter has no records.
"""
import copy
import itertools
import random

import pytest

import hbuild as H
import test_m3_pascal as PAS
from ref import boot as B
from ref import inc as I
from ref import index as IDX
from ref import order as O
from ref import textio as T

APP = PAS.Engine.APP
SAVE = PAS.Engine.SAVE
STATE = SAVE + b"quartermaster\\state.cfg"
KNOWN = SAVE + b"quartermaster\\known.cfg"
INI = b"mods\\mods.ini"
QM = b"mods\\Quartermaster"
W = b"..\\..\\workshop\\content\\333420\\"

PAS.BYREF_NATIVES["modlibrarygetdata"] = tuple(range(1, 16))

DOTTED = ((b"gMap.gamestage", b"qmxgmapgamestage"),)


class IniNode(object):
    """A parser node with children by index (mods.ini's tree)."""

    def __init__(self, handle, keys=None):
        self.handle = handle
        self.keys = keys if keys is not None else []   # [(key, value)] in order
        self.children = []
        self.values = None
        self.code = None
        self.inc = None
        self.appended = False


class Engine(PAS.Engine):
    def __init__(self, files=None, ages=None, mods=()):
        self.fs = dict(files or {})
        self.ages = dict(ages or {})
        self.mods = list(mods)          # [(dir, enabled, tag)]
        self.titles = {}                # {dir: the title its mod.ini gives}
        # The engine gives a folder without mod.ini no title, `last` or text
        # fields: the variables keep what they held (run b4, 2026-09-29).
        self.keep_without_ini = False
        self.now = 1000.0
        self.gamestage = 0
        self.restarted = []
        self.calls = []
        self.register7 = b""
        PAS.Engine.__init__(self, self._read)
        self.states = {}

    def _read(self, path):
        return self.fs.get(path)

    def _file(self, path):
        if path in self.written:
            return self.written[path]
        return self.fs.get(path)

    # time, globals, strings
    def n__misc_GetRealTime(self):
        return self.now

    def n_Floor(self, f):
        return int(f // 1)

    def n_qmxgmapgamestage(self):
        return self.gamestage

    def n_gc_map_gamestage_none(self):
        return 0

    # LAN (qmTick's host settings; classes.script:7557-7558): no session
    # unless a test sets `lanmode` / `lanclients`; the last message received
    # is `lanmsg` = (number, parser handle); sends are recorded.
    def n_gc_lanmode_server(self):
        return 2

    def n_gc_lanmode_client(self):
        return 1

    def n_GetLanMode(self):
        return getattr(self, "lanmode", 0)

    def n_LanGetClientsCount(self):
        return getattr(self, "lanclients", 0)

    def n_LanGetParserID(self):
        return getattr(self, "lanmsg", (0, 0))[0]

    def n_LanSelectParser(self):
        return getattr(self, "lanmsg", (0, 0))[1]

    def n_LanSendParser(self, aid, h):
        self.__dict__.setdefault("lansent", []).append((aid, dict(self.nodes[h].keys)))

    # The OnLanEvent hook's engine names: the event being handled (`lanevent`)
    # and the number of a received parser. The engine's own value of
    # leParser is not ours to know; any number stands in for it here.
    def n_gLanEvent(self):
        return getattr(self, "lanevent", 0)

    def n_leParser(self):
        return 29

    def n_StringRegister7(self):
        return self.register7

    def n_StrReplace(self, s, a, b):
        return s.replace(a, b)

    def n_FileAge(self, p):
        if self._file(p) is None:
            return -1
        return self.ages.get(p, 1564229335)

    # global scripts (qmGlobals, qmUiModel; ref/guard.py): the file list of
    # ParserGetFilesInRoot goes into the selected parser as its values
    def n_ParserGetFilesInRoot(self, pattern):
        folder = pattern[:pattern.rfind(b"\\") + 1].lower()
        ext = pattern[pattern.rfind(b"*") + 1:].lower()
        n = self.nodes[self.active]
        n.values = sorted(p[len(folder):] for p in self.fs
                          if p.lower().startswith(folder) and p.lower().endswith(ext)
                          and b"\\" not in p[len(folder):])
        n.files = True
        return True

    def n_ParserClearByHandle(self, h):
        n = self.nodes[h]
        if getattr(n, "files", False):
            n.values, n.files = None, False
        PAS.Engine.n_ParserClearByHandle(self, h)

    def n_ModLibGetFileExist(self, i, f):
        return self._file(self.mods[i][0] + b"\\" + f) is not None

    def n_StrToLowerCase(self, s):
        return s.lower()

    # ParserSelectByHandle(dst), then ParserCopyFromByHandle(src): the
    # selected parser becomes a copy of src - how vanilla keeps its record
    # manager aside and puts it back (initmapgen.inc:70-71, :248-250).
    def n_ParserCopyFromByHandle(self, src):
        s, d = self.nodes[src], self.nodes[self.active]
        d.keys, d.inc, d.code = dict(s.keys), s.inc, s.code
        d.values = list(s.values) if s.values is not None else None
        return True

    # the mod list
    def n_ModLibraryGetCount(self):
        return len(self.mods)

    def n_ModLibraryGetIniFile(self):
        return INI

    def n_ModLibraryGetData(self, i, tag, d, last, tit, own, desc, tags, url, note, numf,
                            vis, dis, acc, ban, root):
        md, enabled, t = self.mods[i]
        tag.v, d.v = t, md
        dis.v, acc.v, ban.v, root.v = (not enabled), False, False, False
        if self.keep_without_ini and self._file(md + b"\\mod.ini") is None:
            return
        last.v, tit.v = md.rsplit(b"\\", 1)[-1], self.titles.get(md, b"")
        own.v = desc.v = tags.v = url.v = note.v = b""
        numf.v, vis.v = 0, 0

    # parsers: mods.ini as a tree, padded .inc files loaded
    def n_ParserLoadFromFileByHandle(self, h, path):
        data = self._file(path)
        if data is None:
            return False
        n = self.nodes[h]
        if path == INI:
            entries, problem = O._ini_entries(data)
            n.keys, n.code, n.inc = {}, None, None
            n.ini = None
            if problem is None:
                mods = IniNode(self._next())
                self.nodes[mods.handle] = mods
                for keys in entries:
                    e = IniNode(self._next(), list(keys))
                    self.nodes[e.handle] = e
                    mods.children.append(e.handle)
                n.ini = mods.handle
            return True
        # The raw writer pads the last Integer with spaces after the final
        # CR LF; the engine's parser loads such a file (run m2a3).
        if data.endswith(b" ") and data.rstrip(b" ").endswith(b"\r\n"):
            data = data.rstrip(b" ")
        return self._load_inc(n, data)

    def _next(self):
        self.handle += 1
        return self.handle

    def _load_inc(self, n, data):
        n.inc = I.parse(data)
        c = self._node()
        c.values = [v.rstrip(b" ") for v in n.inc.values]
        n.code = c.handle
        n.ini = None
        return True

    def n_ParserSelectByHandleByKey(self, h, key):
        n = self.nodes[h]
        if key.strip().lower() == b"mods":
            return getattr(n, "ini", None) or 0
        return PAS.Engine.n_ParserSelectByHandleByKey(self, h, key)

    def n_ParserGetCountByHandle(self, h):
        n = self.nodes[h]
        if isinstance(n, IniNode):
            return len(n.children) if n.children else len(n.keys)
        return PAS.Engine.n_ParserGetCountByHandle(self, h)

    def n_ParserSelectByHandleByIndex(self, h, i):
        n = self.nodes[h]
        return n.children[i] if isinstance(n, IniNode) and 0 <= i < len(n.children) else 0

    def n_ParserGetValueByKeyByHandle(self, h, key):
        n = self.nodes[h]
        if isinstance(n, IniNode):
            k = key.strip().lower()
            return next((v for kk, v in n.keys if kk == k), b"")
        return PAS.Engine.n_ParserGetValueByKeyByHandle(self, h, key)

    def n_ParserSetValueByKeyByHandle(self, h, key, v):
        n = self.nodes[h]
        if isinstance(n, IniNode):
            k = key.strip().lower()
            for j, (kk, _v) in enumerate(n.keys):
                if kk == k:
                    n.keys[j] = (kk, v)
                    return
            n.keys.append((k, v))
            return
        PAS.Engine.n_ParserSetValueByKeyByHandle(self, h, key, v)

    def n_ParserSetIntValueByKeyByHandle(self, h, key, v):
        self.n_ParserSetValueByKeyByHandle(h, key, b"%d" % v)

    def n_ParserGetIntValueByKeyByHandle(self, h, key):
        v = self.n_ParserGetValueByKeyByHandle(h, key)
        try:
            return int(v)
        except ValueError:
            return 0

    def n_ParserSaveToFileByHandle(self, h, path):
        n = self.nodes[h]
        if path == INI and getattr(n, "ini", None):
            rows = []
            for c in self.nodes[n.ini].children:
                rows.append(dict(self.nodes[c].keys))
            self.written[path] = O.render_mods_ini([(r[b"dir"], r[b"dis"]) for r in rows])
            return True
        return PAS.Engine.n_ParserSaveToFileByHandle(self, h, path)

    # state machines, restart
    def n_StateMachineExecuteState(self, h, name, arg):
        self.calls.append(name.decode("ascii"))
        state = self.states.get(name.decode("ascii").lower())
        if state is None:
            raise PAS.RunError("no state %s" % name)
        state.run()

    def n_TriggerManagerAdd(self, name):
        pass

    def n_StateMachineLoadFromFile(self, h, path):
        pass

    def n_LanShutdown(self):
        self.restarted.append("lan")

    def n_SteamwrapFree(self):
        self.restarted.append("steam")

    def n_RestartApplicationParam(self, p):
        self.restarted.append("restart")

    def rt(self, name):
        h = self.named.get(name)
        return self.nodes[h] if h else None

    def key(self, parser, key):
        h = self.named[parser]
        return self.n_ParserGetValueByKeyByHandle(h, key)

    def set(self, parser, **kw):
        h = self.named.get(parser.encode()) or self.n_ParserCreate(parser.encode())
        for k, v in kw.items():
            self.n_ParserSetValueByKeyByHandle(h, k.encode(), v if isinstance(v, bytes) else b"%d" % v)
        return h


class Fake(object):
    """A state stood in by Python (another milestone's, or one outside the
    desk check)."""

    def __init__(self, fn):
        self.fn = fn

    def run(self):
        self.fn()


_SOURCES = None


def sources():
    global _SOURCES
    if _SOURCES is None:
        loaded, helpers = H.load_sources()
        _SOURCES = dict((st.name.lower(), H.state_code(st, helpers, H.BUILD_VARIABLES))
                        for st in loaded)
    return _SOURCES


_PARSED = {}
#: {state: (old, new)}: a mutation the gate must catch (parsed afresh).
PATCH = {}


def load(eng, *names):
    """The states, parsed once per session and bound to `eng`."""
    for name in names:
        key = name.lower()
        if key in PATCH:
            old, new = PATCH[key]
            code = [line.replace(old, new) for line in sources()[key]]
            if code == sources()[key]:
                raise RuntimeError("the mutation %r matched nothing in %s" % (old, name))
            eng.states[key] = PAS.State(code, eng)
            continue
        if key not in _PARSED:
            code = sources()[key]
            for a, b in DOTTED:
                code = [line.replace(a, b) for line in code]
            try:
                _PARSED[key] = PAS.State(code, eng)
            except PAS.Unsupported as exc:
                pytest.skip("the interpreter does not cover %s: %s" % (name, exc))
        state = copy.copy(_PARSED[key])
        state.engine = eng
        eng.states[key] = state


def run(eng, name):
    try:
        eng.states[name.lower()].run()
    except PAS.Unsupported as exc:
        pytest.skip("the interpreter does not cover a native of %s: %s" % (name, exc))


# ------------------------------------------------------------ the guard
OUTS = [(b"gui\\menu.inc\\oncamera.inc", b"1564229335"),
        (b"quartermaster\\state\\manifest.cfg", b"1564229400")]
PLAN_PATHS = [b"gui\\menu.inc\\cameracontrol.inc", b"gui\\menu.inc\\oncamera.inc"]


def guard_markers():
    yield None
    rng = random.Random(5)
    for phase, mode, rk in itertools.product((B.WRITTEN, B.BOOTING, B.BOOTED),
                                             (B.NORMAL, B.WTA), (B.AUTO, B.APPLY, B.NONE)):
        for _ in range(2):
            yield B.Marker(gen=rng.randint(0, 5), hash=rng.choice([b"1-2-3", b"4-5-6"]),
                           phase=phase, mode=mode, rows=rng.randint(0, 3),
                           rhash=rng.choice([b"1-2-3", b"4-5-6", b"-"]),
                           rcount=rng.randint(0, 2), rk=rk, boots=rng.randint(0, 9),
                           outs=list(OUTS))


def guard_case(marker, fp, sync, damaged, changed, mods, apply, gen_ok, fpold=None):
    """One boot's guard in the interpreter; returns (engine, qm_guard node).
    `fpold`: qmFingerprint's fingerprint without the mods registered at this
    start (None: qm_rt has none)."""
    files = {}
    ages = {}
    base = QM + b"\\data\\"             # relative to the game folder, as the engine lists it
    if marker is not None:
        files[STATE] = B.render_marker(marker)
    for path, age in OUTS:
        files[base + path] = b"x"
        ages[base + path] = int(age) + (2 if damaged and path == OUTS[0][0] else 0)
    for p in PLAN_PATHS:
        files[base + p] = b"x"
        ages.setdefault(base + p, 1564229500)
    eng = Engine(files, ages)
    load(eng, "qmMarkerLoad", "qmGuard", "qmMarkerSave")
    eng.set("qm_rt", fp=fp, sync=1 if sync else 0, qmdir=QM,
            runmode=b"apply" if apply else b"", **({} if fpold is None else {"fpold": fpold}))
    run(eng, "qmMarkerLoad")
    g = eng.set("qm_guard", step=b"plan")
    run(eng, "qmGuard")
    early = None
    if not apply:
        run(eng, "qmMarkerSave")
        early = eng.written.get(STATE)
    regen = eng.key(b"qm_guard", b"regen") == b"1"
    if regen:
        w = {0: b"yes", 1: b"same"}
        eng.set("qm_gen", status=b"ok" if gen_ok else b"fatal", gen=7, changed=changed, sn=0,
                **dict((("w%d" % m), w[m]) for m in range(2)))
    eng.set("qm_plan", n=2, path0=PLAN_PATHS[0], path1=PLAN_PATHS[1])
    eng.set("qm_ini", action=b"written" if mods else b"same", effective=1 if mods else 0)
    eng.n_ParserSetValueByKeyByHandle(g, b"step", b"restart")
    run(eng, "qmGuard")
    run(eng, "qmMarkerSave")
    return eng, early


def guard_combos(every=1):
    """Markers x inputs; `every` > 1 takes every n-th combination."""
    k = 0
    for marker in guard_markers():
        for fp, sync, damaged, changed, mods, apply, gen_ok in itertools.product(
                (b"1-2-3", b"4-5-6"), (False, True), (False, True), (0, 2), (False, True),
                (False, True), (True, False)):
            if not gen_ok and (sync or apply):
                continue
            k += 1
            if k % every == 0:
                yield marker, fp, sync, damaged, changed, mods, apply, gen_ok


def test_the_guard_and_the_marker_files_equal_ref():
    assert check_guard(guard_combos(every=7)) > 400


@pytest.mark.slow
def test_the_guard_and_the_marker_files_equal_ref_everywhere():
    assert check_guard(guard_combos()) > 2500


def check_guard(combos):
    base = QM + b"\\data\\"             # relative to the game folder, as the engine lists it
    count = 0
    for marker, fp, sync, damaged, changed, mods, apply, gen_ok in combos:
        if True:
            eng, early = guard_case(marker, fp, sync, damaged, changed, mods, apply, gen_ok)
            plan = B.boot_plan(marker, fp, sync, damaged, apply=apply)
            ch = changed if plan.regen else 0
            rplan = B.restart_plan(marker, plan, fp, ch, mods)
            outs = [(p, b"%d" % eng.ages[base + p]) for p in PLAN_PATHS]
            outs.append((OUTS[1][0], b"%d" % eng.ages[base + OUTS[1][0]]))
            want = B.next_marker(marker, plan, rplan, fp, 7, gen_ok, ch, outs)
            where = (marker, fp, sync, damaged, changed, mods, apply, gen_ok)
            assert eng.key(b"qm_guard", b"regen") == (b"1" if plan.regen else b"0"), where
            assert eng.key(b"qm_guard", b"mode") == plan.mode, where
            assert eng.key(b"qm_guard", b"why") == plan.why, where
            assert eng.key(b"qm_guard", b"restart") == (b"1" if rplan.restart else b"0"), where
            assert eng.key(b"qm_guard", b"kind") == rplan.kind, where
            assert eng.key(b"qm_guard", b"refused") == (rplan.refused or b""), where
            assert eng.written[STATE] == B.render_marker(want), where
            assert B.parse_marker(eng.written[STATE]) == want, where
            if early is not None:
                pre = marker.copy() if marker else B.Marker()
                pre.phase, pre.boots, pre.rk = plan.phase, plan.boots, B.NONE
                assert early == B.render_marker(pre), where
            count += 1
    return count


@pytest.mark.parametrize("rk, rows", [(B.APPLY, 0), (B.AUTO, 0), (B.TEST, 0), (B.AUTO, 2),
                                      (B.NONE, 0)])
@pytest.mark.parametrize("fpold", [None, b"1-2-3", b"7-8-9"])
@pytest.mark.parametrize("changed, mods", [(0, True), (2, False), (2, True)])
def test_mods_registered_at_this_start_are_not_a_loop_as_ref_says(rk, rows, fpold, changed,
                                                                   mods):
    marker = B.Marker(gen=1, hash=b"1-2-3", phase=B.BOOTED, rk=rk, rows=rows, outs=list(OUTS))
    eng, _early = guard_case(marker, b"4-5-6", False, False, changed, mods, False, True, fpold)
    plan = B.boot_plan(marker, b"4-5-6", False, False)
    rplan = B.restart_plan(marker, plan, b"4-5-6", changed, mods, fp_known=fpold)
    got = tuple(eng.key(b"qm_guard", k) for k in (b"restart", b"kind", b"refused"))
    assert got == (b"1" if rplan.restart else b"0", rplan.kind, rplan.refused or b"")
    said = any(b"only mods registered at this start" in l for l in eng.log)
    assert said == (plan.followed and fpold == b"1-2-3")


def test_the_i5_salt_salts_the_fingerprint_without_the_new_mods_too():
    eng = Engine()
    load(eng, "qmMarkerLoad", "qmGuard")
    eng.set("qm_rt", fp=b"1-2-3", fpold=b"4-5-6", sync=0, qmdir=QM, unstable=1)
    run(eng, "qmMarkerLoad")
    eng.set("qm_guard", step=b"plan")
    run(eng, "qmGuard")
    assert eng.key(b"qm_guard", b"fpold") == B.unstable_fp(b"4-5-6", 1)


def test_the_i5_salt_changes_the_fingerprint_every_boot():
    eng = Engine()
    load(eng, "qmMarkerLoad", "qmGuard")
    eng.set("qm_rt", fp=b"1-2-3", sync=0, qmdir=QM, unstable=1)
    run(eng, "qmMarkerLoad")
    eng.set("qm_guard", step=b"plan")
    run(eng, "qmGuard")
    assert eng.key(b"qm_rt", b"fp") == B.unstable_fp(b"1-2-3", 1)
    assert eng.key(b"qm_rt", b"fpinputs") == b"1-2-3"


# ----------------------------------------------------------- known.cfg
def known_case(known, dirs, apply=False):
    files = {} if known is None else {KNOWN: B.render_known(known)}
    eng = Engine(files)
    load(eng, "qmKnown")
    eng.set("qm_rt", runmode=b"apply" if apply else b"")
    kw = dict(("dir%d" % i, d) for i, d in enumerate(dirs))
    eng.set("qm_mods", n=len(dirs), **kw)
    run(eng, "qmKnown")
    return eng


@pytest.mark.parametrize("known, dirs, apply", [
    (None, [b"mods\\A", b"mods\\B"], False),
    ([(b"mods\\A", False)], [b"mods\\a", b"mods\\QMTestNew"], False),
    ([(b"mods\\A", False), (b"mods\\QMTestNew", True)], [b"mods\\A", b"mods\\QMTestNew"], False),
    ([(b"mods\\A", False), (b"mods\\QMTestNew", True)], [b"mods\\A", b"mods\\QMTestNew",
                                                         b"mods\\\xd0\x9c"], True),
    ([(b"mods\\Gone", True)], [b"mods\\A"], False),
    ([], [b"mods\\A"], False),
])
def test_known_cfg_equals_ref(known, dirs, apply):
    eng = known_case(known, dirs, apply)
    entries, new, changed = B.update_known(known, dirs)
    if apply:
        entries, ch = B.acknowledge(entries)
        changed = changed or ch
        new = []
    if changed:
        assert eng.written[KNOWN] == B.render_known(entries)
    else:
        assert KNOWN not in eng.written
    n = int(eng.key(b"qm_known", b"newn"))
    assert [eng.key(b"qm_known", b"new%d" % k) for k in range(n)] == new
    fresh = [eng.key(b"qm_known", b"fr%d" % i) == b"1" for i in range(len(dirs))]
    assert fresh == B.fresh(known, dirs)
    assert eng.key(b"qm_known", b"frn") == b"%d" % sum(fresh)


# ------------------------------------------------------------- mods.ini
def order_case(mods, ini_rows, intent=None, sync=False, ini_data=None, cores=()):
    """qmModList + qmOrder (+ qmModsIni) over `mods` = [(dir, enabled, tag)];
    `cores`: other dirs that ship data\\quartermaster\\core.aix."""
    files = {INI: ini_data if ini_data is not None else O.render_mods_ini(ini_rows)}
    for d, _e, _t in mods:
        if d == QM or d in cores:
            # qmModList asks FileAge by the dir as the engine lists it,
            # relative to the game folder (the working directory).
            files[d + b"\\data\\quartermaster\\core.aix"] = b"x"
    eng = Engine(files, mods=mods)
    load(eng, "qmModList", "qmOrder", "qmModsIni")
    kw = {}
    if intent is not None:
        kw = dict(runmode=b"apply", uiapplyn=len(intent))
        for j, (d, off) in enumerate(intent):
            kw["uiapplydir%d" % j] = d
            kw["uiapplydis%d" % j] = 1 if off else 0
    eng.set("qm_rt", sync=1 if sync else 0, **kw)
    run(eng, "qmModList")
    run(eng, "qmOrder")
    return eng


def ref_order(mods, ini_rows, intent=None, ini_data=None):
    data = ini_data if ini_data is not None else O.render_mods_ini(ini_rows)
    self_dir = QM if any(d == QM and e for d, e, _t in mods) else None
    have, _p = O.parse_mods_ini(data)
    engine_rows = [(d, e) for d, e, _t in mods]
    wanted_intent = None if intent is None else dict((O.norm_dir(d), off) for d, off in intent)
    # qmOrder asks for the engine's dirs in mods.ini's order, Quartermaster
    # moved last (no saved order), with True/False.
    flags = dict((O.norm_dir(d), e) for d, e in engine_rows)
    if wanted_intent:
        for k, off in wanted_intent.items():
            if k in flags and k != O.norm_dir(self_dir or b""):
                flags[k] = not off
    dirs = [d for d, _e in engine_rows]
    wanted = [(dirs[i], O.FALSE if flags[O.norm_dir(dirs[i])] else O.TRUE)
              for i in O.load_order(dirs, self_dir).rows]
    return O.mods_ini_plan(engine_rows, data, wanted, self_dir=self_dir), have


def game_over(eng):
    """qm_ini selfonly / over<j> as ref/order.py IniPlan.over has it."""
    if eng.key(b"qm_ini", b"selfonly") != b"1":
        return None
    return [O.norm_dir(eng.key(b"qm_mods", b"dir" + eng.key(b"qm_ini", b"over%d" % j)))
            for j in range(int(eng.key(b"qm_ini", b"overn")))]


ORDER_MODS =[(b"mods\\SW_Frontline_Protocol", False, b"0"), (W + b"873048118", False, b"873048118"),
              (b"mods\\QMTestWASD", True, b"0"), (QM, True, b"0"), (b"mods\\QMTestCamSpeed", True, b"0")]


def rows_of(mods):
    return [(d, O.FALSE if e else O.TRUE) for d, e, _t in mods]


@pytest.mark.parametrize("mods, intent, data", [
    (ORDER_MODS, None, None),
    (sorted(ORDER_MODS), None, None),
    (ORDER_MODS, [(b"mods\\QMTestCamSpeed", True), (QM, True)], None),
    (ORDER_MODS, [(b"mods\\sw_frontline_protocol", False)], None),
    (ORDER_MODS, None, b"garbage\r\n"),
    (ORDER_MODS, None, O.render_mods_ini(rows_of(ORDER_MODS)).replace(
        b"         dis = True\r\n", b"         dis = True\r\n         x = 1\r\n", 1)),
    (ORDER_MODS, None, O.render_mods_ini(rows_of(ORDER_MODS)[:-1])),
    (ORDER_MODS, None, O.render_mods_ini(rows_of(ORDER_MODS)).replace(b"QMTestWASD", b"Other")),
])
def test_order_and_mods_ini_equal_ref(mods, intent, data):
    eng = order_case(mods, rows_of(mods), intent, ini_data=data)
    plan, _have = ref_order(mods, rows_of(mods), intent, ini_data=data)
    action = {b"same": b"same", b"write": b"written", b"refused": b"refused"}[plan.action]
    assert eng.key(b"qm_ini", b"action") == action
    if plan.action == b"refused":
        assert eng.key(b"qm_ini", b"why") == plan.why
        assert INI not in eng.written
    else:
        assert eng.key(b"qm_ini", b"effective") == (b"1" if plan.effective else b"0")
        assert game_over(eng) == plan.over
        if plan.action == b"write":
            assert eng.written[INI] == O.render_mods_ini(plan.rows)
        else:
            assert INI not in eng.written


def test_mods_ini_is_left_alone_during_an_mp_sync():
    eng = order_case(ORDER_MODS, rows_of(ORDER_MODS), sync=True)
    assert eng.key(b"qm_ini", b"action") == b"skipped" and INI not in eng.written


def test_an_apply_changes_the_scan_list_for_the_generation():
    eng = order_case(ORDER_MODS, rows_of(ORDER_MODS), [(b"mods\\QMTestCamSpeed", True)])
    mods = eng.named[b"qm_mods"]
    en = eng.n_ParserGetIntValueByKeyByHandle(mods, b"en")
    scanned = [eng.key(b"qm_mods", b"dir" + eng.key(b"qm_mods", b"e%d" % j)) for j in range(en)]
    assert scanned == [b"mods\\QMTestWASD"]


def _scan_list(eng):
    mods = eng.named[b"qm_mods"]
    en = eng.n_ParserGetIntValueByKeyByHandle(mods, b"en")
    return [eng.key(b"qm_mods", b"dir" + eng.key(b"qm_mods", b"e%d" % j)) for j in range(en)]


@pytest.mark.parametrize("intent", [None, [(b"mods\\QMTestCamSpeed", True)]])
def test_a_second_quartermaster_copy_is_left_out_of_the_scan_list(intent):
    """ref/index.py scanned_mods: another folder with core.aix is never indexed,
    in a boot and in an Apply (qmOrder rebuilds the list)."""
    copy = W + b"77"
    mods = ORDER_MODS[:1] + [(copy, True, b"77")] + ORDER_MODS[1:]
    eng = order_case(mods, rows_of(mods), intent, cores=(copy,))
    assert eng.key(b"qm_mods", b"self") == b"4"                 # mods\Quartermaster
    assert [eng.key(b"qm_mods", b"core%d" % i) for i in range(len(mods))] == [
        b"0", b"1", b"0", b"0", b"1", b"0"]
    want = [b"mods\\QMTestWASD"] if intent else [b"mods\\QMTestWASD", b"mods\\QMTestCamSpeed"]
    assert _scan_list(eng) == want
    wanted = [IDX.Mod(d, e and not (intent and d == b"mods\\QMTestCamSpeed"), t)
              for d, e, t in mods]
    pos = IDX.load_positions(wanted, 4, O.load_order([d for d, _e, _t in mods], QM).rows)
    assert [mods[i][0] for i in IDX.scanned_mods(wanted, 4, lambda d: d in (QM, copy),
                                                  pos)] == want
    assert (b"[qm] mods: " + copy + b" is another copy of Quartermaster (it ships "
            b"data\\quartermaster\\core.aix); not indexed") in eng.log


def test_every_order_of_a_mod_set_is_kept_with_quartermaster_last_in_one_write():
    # No saved order keeps mods.ini's order; only Quartermaster moves.
    for perm in itertools.permutations(ORDER_MODS):
        eng = order_case(list(perm), rows_of(perm))
        plan, _h = ref_order(list(perm), rows_of(perm))
        written = eng.written.get(INI, O.render_mods_ini(rows_of(perm)))
        rows, _p = O.parse_mods_ini(written)
        assert rows == [r for r in rows_of(perm) if r[0] != QM] + [(QM, O.FALSE)]
        assert (INI in eng.written) == (perm[-1][0] != QM)
        assert eng.key(b"qm_ini", b"effective") == (b"1" if plan.effective else b"0")
        assert game_over(eng) == plan.over, perm


@pytest.mark.parametrize("ships_index, ships_own", [(False, False), (True, False),
                                                    (False, True), (True, True)])
def test_no_restart_when_quartermaster_only_moved_past_mods_without_its_files(ships_index,
                                                                              ships_own):
    """qmGuard as ref/order.py needs_restart: Quartermaster moved past
    mods\\Testowy only; that costs a restart only when Testowy ships a path
    the index read or a file of Quartermaster's the index does not read."""
    new = b"mods\\Testowy"
    files, ages = {}, {}
    if ships_own:
        files[new + b"\\data\\scripts\\resource.script"] = b"x"
        ages[new + b"\\data\\scripts\\resource.script"] = 1564229500
    eng = Engine(files, ages)
    load(eng, "qmMarkerLoad", "qmGuard", "qmMarkerSave")
    eng.set("qm_rt", fp=b"1-2-3", sync=0, qmdir=QM)
    eng.fs[STATE] = B.render_marker(B.Marker(gen=1, hash=b"1-2-3", phase=B.BOOTED))
    run(eng, "qmMarkerLoad")
    g = eng.set("qm_guard", step=b"plan")
    run(eng, "qmGuard")
    ml = eng.set("qm_mods", n=2, dir0=new, pos0=0, dir1=QM, pos1=1)
    eng.n_ParserSetIntValueByKeyByHandle(ml, b"self", 1)
    eng.set("qm_index", n=2, p0=b"gui\\menu.inc\\cameracontrol.inc", v0=b"1",
            p1=b"gui\\menu.inc\\oncamera.inc", v1=b"0" if ships_index else b"-")
    eng.set("qm_ini", action=b"written", effective=1, selfonly=1, overn=1, over0=0)
    eng.set("qm_plan", n=0)
    eng.n_ParserSetValueByKeyByHandle(g, b"step", b"restart")
    run(eng, "qmGuard")
    plan = O.IniPlan(b"write", b"-", [], True, [O.norm_dir(new)])
    want = O.needs_restart(plan, lambda d: ships_index or ships_own)
    assert eng.key(b"qm_guard", b"restart") == (b"1" if want else b"0")
    said = any(b"only moved Quartermaster past 1 mod(s)" in l for l in eng.log)
    assert said == (not want)


# ----------------------------------------------------------------- tick
def tick_engine(**rt):
    eng = Engine()
    load(eng, "qmTick", "qmRestart", "qmMarkerSave")
    eng.set("qm_rt", **rt)
    return eng


def test_the_tick_is_idle_without_work():
    eng = tick_engine(tick=0, uiapply=0)
    run(eng, "qmTick")
    assert eng.calls == [] and eng.log == []


def test_the_restart_waits_a_second_after_the_last_write_and_the_menu():
    eng = tick_engine(tick=1, rs=1, rsdue=10011, rskind=b"auto", sync=0)
    eng.now = 1001.0                 # 10010 tenths
    run(eng, "qmTick")
    assert eng.restarted == []
    eng.now = 1001.1
    eng.gamestage = 1                # a map is loaded
    run(eng, "qmTick")
    assert eng.restarted == []
    eng.gamestage = 0
    run(eng, "qmTick")
    assert eng.restarted == ["lan", "steam", "restart"]
    assert eng.key(b"qm_rt", b"rs") == b"2" and eng.key(b"qm_rt", b"tick") == b"0"


def test_a_restart_never_runs_during_an_mp_sync_and_is_dropped_later():
    eng = tick_engine(tick=1, rs=1, rsdue=10011, sync=1)
    eng.now = 1002.0
    run(eng, "qmTick")
    assert eng.restarted == []
    eng.now = 1002.0 + (B.WINDOW_TENTHS + 1) / 10.0
    run(eng, "qmTick")
    assert eng.restarted == [] and eng.key(b"qm_rt", b"rs") == b"0"


def test_the_first_menu_frame_confirms_the_start_and_moves_the_restart():
    eng = tick_engine(tick=1, confirm=1, rs=1, rsdue=10011, sync=0)
    eng.set("qm_state", phase=b"booting", gen=2, hash=b"1-2-3", mode=b"normal", rows=0,
            rhash=b"-", rcount=0, rk=b"-", boots=3, on=0)
    eng.now = 1001.2
    run(eng, "qmTick")
    assert eng.restarted == []                                   # the confirm wrote a file
    assert B.parse_marker(eng.written[STATE]).phase == B.BOOTED
    assert eng.key(b"qm_rt", b"rsdue") == b"%d" % (10012 + 11)
    eng.now = 1002.3
    run(eng, "qmTick")
    assert eng.restarted == ["lan", "steam", "restart"]


def test_the_tick_runs_a_confirmed_apply_through_the_boot():
    eng = tick_engine(tick=0, uiapply=1, uiapplyseq=1)
    ran = []

    def boot():
        ran.append(eng.key(b"qm_rt", b"runmode"))
    eng.states["qmboot"] = Fake(boot)
    run(eng, "qmTick")
    assert ran == [b"apply"] and eng.key(b"qm_rt", b"uiapply") == b"0"
    assert eng.key(b"qm_rt", b"runmode") == b""


def test_the_tick_logs_the_hook_counts_when_they_move():
    eng = tick_engine(tick=0, uiapply=0, hook=b"cameracontrol")
    eng.set("qm_hk", cc=1, im=2)
    run(eng, "qmTick")
    run(eng, "qmTick")
    eng.set("qm_hk", cc=2, im=4)
    run(eng, "qmTick")
    assert [l for l in eng.log if b"hooks" in l] == [
        b"[qm] hooks cc=1 im=2 booted by cameracontrol",
        b"[qm] hooks cc=2 im=4 booted by cameracontrol"]


# ----------------------------------------------------------------- boot
CASES = SAVE + b"qm_test\\cases\\"


def boot_engine(marker=None, changed=0, mods=None, hook=b"", autotest=None, known=None,
                switches=()):
    mods = mods or [(QM, True, b"0")]
    files = {INI: O.render_mods_ini(rows_of(mods)),
             QM + b"\\data\\quartermaster\\core.aix": b"x"}
    if marker is not None:
        files[STATE] = B.render_marker(marker)
    if known is not None:
        files[KNOWN] = B.render_known(known)
    if autotest is not None:
        files[SAVE + b"qm_autotest.cfg"] = autotest
    for name in switches:
        files[CASES + b"qm_m5_%s.cfg" % name] = b"case\r\n"
    eng = Engine(files, mods=mods)
    load(eng, "qmBoot", "qmMarkerLoad", "qmMarkerSave", "qmModList", "qmOrder", "qmModsIni",
         "qmKnown", "qmGlobals", "qmGuard", "qmAbout", "qmAbRules", "qmSettings", "qmLastStart")

    def fingerprint():
        eng.set("qm_rt", fp=b"1-2-3")
        eng.set("qm_plan", n=0)

    def generate():
        eng.set("qm_gen", status=b"ok", gen=1, changed=changed, sn=0)
    for name, fn in (("qmIndex", lambda: None), ("qmPlan", lambda: None),
                     ("qmFingerprint", fingerprint), ("qmGenerate", generate),
                     ("qmReport", lambda: None), ("qmReportLoad", lambda: None),
                     ("qmSelfTest", lambda: None)):
        eng.states[name.lower()] = Fake(fn)
    rt = eng.set("qm_rt", hook=hook)
    return eng, rt


def test_a_first_boot_alone_writes_its_marker_and_needs_no_restart():
    eng, _rt = boot_engine()
    run(eng, "qmBoot")
    m = B.parse_marker(eng.written[STATE])
    assert (m.gen, m.hash, m.phase, m.rk, m.boots) == (1, b"1-2-3", B.BOOTED, B.NONE, 1)
    assert eng.key(b"qm_rt", b"rs") == b"" and eng.key(b"qm_rt", b"busy") == b"0"
    assert eng.calls.index("qmGenerate") < eng.calls.index("qmReport")
    assert any(l.startswith(b"[qm] boot done regen=True why=first restart=-") for l in eng.log)
    assert KNOWN in eng.written


def test_a_boot_that_changed_a_file_schedules_the_restart():
    eng, _rt = boot_engine(changed=2)
    eng.now = 500.04
    run(eng, "qmBoot")
    assert eng.key(b"qm_rt", b"rs") == b"1" and eng.key(b"qm_rt", b"rskind") == b"auto"
    assert eng.key(b"qm_rt", b"rsdue") == b"%d" % (5000 + 11)
    assert B.parse_marker(eng.written[STATE]).phase == B.WRITTEN
    assert "qmSelfTest" not in eng.calls


def test_a_stable_boot_loads_the_last_report_and_logs_stable():
    marker = B.Marker(gen=1, hash=b"1-2-3", phase=B.WRITTEN, rk=B.AUTO, rows=1, rhash=b"1-2-3",
                      rcount=1, boots=1)
    eng, _rt = boot_engine(marker, known=[(QM, False)])
    run(eng, "qmBoot")
    assert "qmGenerate" not in eng.calls and "qmReportLoad" in eng.calls
    assert eng.key(b"qm_rt", b"confirm") == b"1" and eng.key(b"qm_rt", b"tick") == b"1"
    assert any(l.startswith(b"[qm] boot stable gen=1") for l in eng.log)
    m = B.parse_marker(eng.written[STATE])
    assert (m.phase, m.rows, m.rk) == (B.BOOTING, 0, B.NONE)


def test_a_fallback_hook_is_reported():
    eng, _rt = boot_engine(hook=b"initminimap")
    run(eng, "qmBoot")
    assert eng.key(b"qm_boot", b"st") == b"WARN"
    assert eng.key(b"qm_boot", b"l0").startswith(b"WARN Quartermaster was started by its initminimap hook")


def test_the_i5_switch_and_the_loop_guard_in_the_boot():
    eng, _rt = boot_engine(changed=1, autotest=b"", switches=(b"unstable", b"restart"))
    run(eng, "qmBoot")
    assert eng.key(b"qm_gen_in", b"gensalt") == b"1"
    assert eng.key(b"qm_rt", b"rs") == b"1"
    first = eng.written[STATE]
    # The next start: the fingerprint moved with the salt - no second restart.
    eng2, _rt = boot_engine(B.parse_marker(first), changed=1, autotest=b"",
                            switches=(b"unstable", b"restart"))
    eng2.fs[KNOWN] = eng.written[KNOWN]
    run(eng2, "qmBoot")
    assert eng2.key(b"qm_guard", b"refused") == b"loop"
    assert eng2.key(b"qm_rt", b"rs") == b""
    assert eng2.key(b"qm_boot", b"st") == b"FAIL"


@pytest.mark.parametrize("fpold, index, restart", [(b"1-2-3", False, True),
                                                   (b"7-8-9", False, False),
                                                   (b"7-8-9", True, None)])
def test_a_folder_made_before_the_apply_restart_is_not_a_loop_in_the_boot(fpold, index,
                                                                          restart):
    """Logs of 2026-10-01: New mod made mods\\Testowy, the Apply
    restarted the game, and the engine registered the folder after
    Quartermaster. Its boot puts Quartermaster last again (mods.ini changed);
    the loop rule refused that restart with a FAIL, though only the new folder
    had moved the inputs. With the index's answer (`index`: Testowy ships no
    path it read) no restart is asked at all; without it (no qm_index, the
    guard cannot tell) the restart is not a loop either."""
    new = b"mods\\Testowy"
    marker = B.Marker(gen=2, hash=b"1-2-3", phase=B.BOOTED, rk=B.APPLY, boots=37)
    eng, _rt = boot_engine(marker, mods=[(QM, True, b"0"), (new, True, b"0")],
                           known=[(QM, False)])

    def fingerprint():
        eng.set("qm_rt", fp=b"4-5-6", fpold=fpold)
        eng.set("qm_plan", n=0)
        if index:
            eng.set("qm_index", n=0)
    eng.states["qmfingerprint"] = Fake(fingerprint)
    run(eng, "qmBoot")
    assert eng.key(b"qm_known", b"fr1") == b"1" and eng.key(b"qm_ini", b"effective") == b"1"
    assert eng.key(b"qm_ini", b"selfonly") == b"1"
    fail = eng.key(b"qm_boot", b"st") == b"FAIL"
    if restart is None:
        assert eng.key(b"qm_guard", b"rwhy") == B.NOTHING and eng.key(b"qm_rt", b"rs") == b""
        assert not fail and any(b"only moved Quartermaster past 1 mod(s)" in l for l in eng.log)
    elif restart:
        assert (eng.key(b"qm_guard", b"kind"), eng.key(b"qm_guard", b"refused")) == (B.AUTO, b"")
        assert eng.key(b"qm_rt", b"rs") == b"1" and not fail
    else:
        assert eng.key(b"qm_guard", b"refused") == B.LOOP and eng.key(b"qm_rt", b"rs") == b""
        assert fail


@pytest.mark.parametrize("state, old, new", [
    ("qmGuard", b"(qmGdRows>=2)", b"(qmGdRows>=3)"),
    ("qmGuard", b"(qmGdRcount>=1)", b"(qmGdRcount>=2)"),
    ("qmGuard", b"(qmGdSuspect) and (qmGdFp=qmGdHash)", b"(qmGdSuspect) and (qmGdFp<>qmGdHash)"),
    ("qmGuard", b"qmGdNewPhase := 'booting'", b"qmGdNewPhase := 'booted'"),
    ("qmMarkerLoad", b"'rows', StrToInt(qmMkVal)", b"'rcount', StrToInt(qmMkVal)"),
])
def test_a_wrong_guard_is_caught(state, old, new):
    """The gate has teeth: each of these mutations changes some decision."""
    PATCH[state.lower()] = (old, new)
    try:
        with pytest.raises(AssertionError):
            check_guard(guard_combos(every=3))
    finally:
        PATCH.clear()


def test_a_selftest_run_holds_the_restart_in_the_guard():
    eng = Engine()
    load(eng, "qmMarkerLoad", "qmGuard")
    eng.set("qm_rt", fp=b"1-2-3", sync=0, qmdir=QM, norestart=1)
    run(eng, "qmMarkerLoad")
    g = eng.set("qm_guard", step=b"plan")
    run(eng, "qmGuard")
    eng.set("qm_gen", status=b"ok", gen=1, changed=1, sn=0)
    eng.set("qm_plan", n=0)
    eng.set("qm_ini", action=b"same", effective=0)
    eng.n_ParserSetValueByKeyByHandle(g, b"step", b"restart")
    run(eng, "qmGuard")
    assert (eng.key(b"qm_guard", b"restart"), eng.key(b"qm_guard", b"refused")) == (
        b"0", B.HELD)


def test_what_mods_ini_moves_is_said_in_words():
    mods = [(b"mods\\SW_Frontline_Protocol", False, b"0"), (QM, True, b"0"),
            (W + b"873048118", False, b"873048118")]
    eng = order_case(mods, rows_of(mods))
    lo = O.load_order([d for d, _e, _t in mods], QM)
    moves, flags = O.ini_changes(rows_of(mods), O.load_rows(rows_of(mods), QM, lo))
    assert moves == (W + b"873048118 3->2; " + QM + b" 2->3")
    assert eng.key(b"qm_ini", b"moves") == moves and eng.key(b"qm_ini", b"flags") == flags == b""
    assert b"[qm] mods.ini moved: " + moves in eng.log


def test_what_an_apply_changes_in_mods_ini_is_said_in_words():
    eng = order_case(ORDER_MODS, rows_of(ORDER_MODS), [(b"mods\\QMTestCamSpeed", True)])
    plan, _h = ref_order(ORDER_MODS, rows_of(ORDER_MODS), [(b"mods\\QMTestCamSpeed", True)])
    moves, flags = O.ini_changes(rows_of(ORDER_MODS), plan.rows)
    assert flags == b"mods\\QMTestCamSpeed dis False->True"
    assert (eng.key(b"qm_ini", b"moves"), eng.key(b"qm_ini", b"flags")) == (moves, flags)


# ------------------------------------------------------------ SelfTest m5
def case_engine(step, new=b"", mods=None, boots=1, restart=0, rows=0, rcount=0):
    """The engine after a boot: `restart` is qm_guard's (the boot's own
    restart pending), `rows` / `rcount` the marker's chain it saved."""
    mods = mods or [(b"mods\\QMTestNew", True, b"0"), (QM, True, b"0")]
    eng = order_case(mods, rows_of(mods))
    load(eng, "qmCaseM5", "qmModsIni", "qmMarkerSave", "qmRestart")
    out = SAVE + b"qm_test\\out\\"
    eng.set("qm_case_rt", outdir=out, out=out + b"qm_m5.txt", status=b"started")
    case = eng.n_ParserCreate(b"qm_case")
    lines = [b";kind m5", b";step " + step] + ([b";new " + new] if new else [])
    eng.fs[SAVE + b"case.cfg"] = T.write_file(I.layout_lines([b"Name = qmCase"], lines))
    eng.n_ParserLoadFromFileByHandle(case, SAVE + b"case.cfg")
    eng.set("qm_state", boots=boots, phase=b"booted", gen=1, hash=b"1-2-3", mode=b"normal",
            rows=rows, rhash=b"1-2-3" if rcount else b"-", rcount=rcount, rk=b"-", on=0)
    eng.set("qm_guard", why=b"stable", kind=b"auto" if restart else b"-", refused=b"",
            restart=restart)
    eng.set("qm_known", newn=1 if new else 0, new0=new)
    return eng, out


def test_the_compile_step_runs_the_restart_state_dry():
    eng, out = case_engine(b"compile")
    run(eng, "qmCaseM5")
    assert eng.restarted == [] and eng.key(b"qm_case_rt", b"status") == b"ok"
    assert eng.key(b"qm_rt", b"rsdry") == b"0"
    assert b"compile|qmRestart|True\r\n" in eng.written[out + b"m5_compile_1.txt"]


def test_the_shuffle_step_writes_quartermaster_first_and_asks_for_a_test_restart():
    eng, out = case_engine(b"shuffle", new=b"mods\\QMTestNew")
    eng.fs[INI] = eng.written.pop(INI, eng.fs[INI])        # the boot's file
    run(eng, "qmCaseMods" if False else "qmCaseM5")
    rows, _p = O.parse_mods_ini(eng.written[INI])
    assert rows[0] == (QM, b"False") and eng.key(b"qm_ini", b"effective") == b"1"
    assert eng.key(b"qm_rt", b"rs") == b"1" and eng.key(b"qm_rt", b"rskind") == b"test"
    assert B.parse_marker(eng.written[STATE]).rk == B.TEST
    assert out + b"m5_shuffle.done" in eng.written
    assert eng.key(b"qm_case_rt", b"status") == b"ok"


@pytest.mark.parametrize("restart,rows,rcount", [(1, 1, 1), (0, 1, 1), (0, 0, 1), (0, 1, 0)])
def test_the_shuffle_waits_until_the_boot_left_the_restart_chain_clear(restart, rows, rcount):
    # A pending restart of the boot would load the shuffle instead of the
    # boot's order; a chain left by a refused restart would refuse the next.
    eng, out = case_engine(b"shuffle", new=b"mods\\QMTestNew", restart=restart, rows=rows,
                           rcount=rcount)
    eng.fs[INI] = eng.written.pop(INI, eng.fs[INI])        # the boot's file
    run(eng, "qmCaseM5")
    assert INI not in eng.written
    assert out + b"m5_shuffle.done" not in eng.written and STATE not in eng.written
    assert eng.key(b"qm_rt", b"rs") == b"" and eng.key(b"qm_case_rt", b"status") == b"ok"
    assert (b"wait|restart=%d|rows=%d|rcount=%d\r\n" % (restart, rows, rcount)
            in eng.written[out + b"m5_shuffle_1.txt"])


def test_a_later_life_of_the_shuffle_says_done_when_the_order_is_back():
    eng, out = case_engine(b"shuffle", new=b"mods\\QMTestNew", boots=3)
    eng.fs[out + b"m5_shuffle.done"] = b"shuffle|1\r\n"
    eng.set("qm_ini", action=b"same", effective=0)
    run(eng, "qmCaseM5")
    assert b"done|1\r\n" in eng.written[out + b"m5_shuffle_3.txt"]
    assert any(l.startswith(b"[qm] m5 i7 done") for l in eng.log)
    assert eng.key(b"qm_rt", b"rs") == b""


def test_the_disable_step_switches_quartermaster_off_by_its_own_writer():
    eng, out = case_engine(b"disable")
    eng.fs[INI] = eng.written.pop(INI, eng.fs[INI])
    run(eng, "qmCaseM5")
    rows, _p = O.parse_mods_ini(eng.written[INI])
    assert dict(rows)[QM] == b"True" and len(rows) == 2
    assert eng.key(b"qm_rt", b"rskind") == b"test"


def test_a_selftest_switch_without_restart_keeps_one_life():
    eng, _rt = boot_engine(changed=1, autotest=b"", switches=(b"unstable",))
    run(eng, "qmBoot")
    assert eng.key(b"qm_rt", b"norestart") == b"1" and eng.key(b"qm_rt", b"unstable") == b"1"
    assert eng.key(b"qm_guard", b"refused") == b"selftest" and eng.key(b"qm_rt", b"rs") == b""
    empty, _rt = boot_engine(changed=1, autotest=b"")
    run(empty, "qmBoot")
    assert empty.key(b"qm_guard", b"refused") == b"selftest"
    assert "qmSelfTest" in empty.calls


def test_the_report_says_exactly_what_the_first_boot_moved():
    """The first boot keeps mods.ini's order and moves only Quartermaster."""
    mods = [(b"mods\\SW_Frontline_Protocol", False, b"0"), (QM, True, b"0"),
            (W + b"873048118", False, b"873048118")]
    eng, _rt = boot_engine(mods=mods)
    run(eng, "qmBoot")
    moves = W + b"873048118 3->2; " + QM + b" 2->3"
    lines = [eng.key(b"qm_boot", b"l%d" % k) for k in range(int(eng.key(b"qm_boot", b"n")))]
    assert (b"OK Your load order is kept; Quartermaster moved itself to the end. Moved: " + moves
            + b".") in lines
    assert b"[qm] mods.ini moved: " + moves in eng.log
    assert eng.key(b"qm_guard", b"restart") == b"0"          # disabled mods decide nothing
    # The player's baseline, Quartermaster last already: mods.ini is left alone.
    base = [(b"mods\\SW_Frontline_Protocol", False, b"0"), (W + b"873048118", False, b"873048118"),
            (QM, True, b"0")]
    eng, _rt = boot_engine(mods=base)
    run(eng, "qmBoot")
    assert INI not in eng.written and eng.key(b"qm_ini", b"action") == b"same"
