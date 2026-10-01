"""The emitted M4 states, run offline: qmCaseM4 drives qmValFiles, qmPlan,
qmGenerate, qmMerge and qmReport exactly as hbuild emits them, on the small
interpreter of the script dialect in test_m3_pascal.py, over an emulated
engine; tools/m4cases.py check_dump must then find nothing to complain about
- the same comparison the in-game run gets.

The emulated validator stands in for the engine's compiler: a validation copy
that the offline oracle (m4cases.duplicate_var_oracle) accepts runs its first
Code line - the flag line, interpreted like any other code - and one it
rejects sets nothing, as "Compile script error" does in game (probe 3). The
dialect's own acceptance of the Pascal is the lints' and the in-game run's
job; this is a desk check of what the states do.

The emulated parser saves a flat parser in the layout the game wrote in run
m4a, and a load drops the spaces a value starts or ends with, as the
engine's parser does (run m4a for the leading spaces, run m2a for the
trailing ones). So report.cfg's round trip is checked against the engine's
behaviour, not a lossless stand-in.

Every SelfTest generation here runs with a qm_boot block present, the way
qmBoot leaves it before it runs the SelfTest: a sandbox report must not
take it (runs m4a, m4c).

The interpreter reads every file a byte at a time, so a generation costs
about 20 s here: the five generations of qm_m4b.cfg (stale cleanup,
determinism) run with --runslow; ref/validate.py's own tests cover the same
rules in the default run.
"""
import gc
import os
import re

import pytest

import hbuild as H
import m4cases as C
import test_m3_pascal as P
from ref import inc as I
from ref import report as RP
from ref import textio as T
from ref import validate as V
from ref.index import index_key

M4_STATES = ("qmGenerate", "qmReport", "qmValFiles", "qmCaseM4", "qmMerge", "qmPlan",
             "qmReportLoad", "qmConflicts", "qmConflictsCode")


class M4Engine(P.Engine):
    """The natives the M4 states use on top of the merge's."""

    VALTM = 91

    def __init__(self, read, compiles, undeletable=()):
        P.Engine.__init__(self, read)
        self.compiles = compiles
        self.undeletable = set(undeletable)
        self.managers = {b"qm_core": 7, b"qm_test": 8}
        self.loaded = {}
        self.deleted = set()
        self.natives = dict((n[2:].lower(), getattr(self, n)) for n in dir(self)
                            if n.startswith("n_"))

    def _file(self, path):
        if path in self.deleted:
            return None
        return P.Engine._file(self, path)

    def n_OpenFileStreamForWrite(self, path):
        self.deleted.discard(path)
        return P.Engine.n_OpenFileStreamForWrite(self, path)

    def n_ParserSetIntValueByKeyByHandle(self, h, key, v):
        self.nodes[h].keys[key.strip().lower()] = b"%d" % v

    def n_DeleteFileStream(self, path):
        if path in self.undeletable:
            return
        self.written.pop(path, None)
        self.deleted.add(path)

    def n_ParserSaveToFileByHandle(self, h, path):
        n = self.nodes[h]
        if n.inc is not None:
            return P.Engine.n_ParserSaveToFileByHandle(self, h, path)
        # A flat parser, keys in the order they were set: the layout of the
        # report.cfg the game wrote in run m4a.
        self.deleted.discard(path)
        self.written[path] = b"".join(
            line + b"\r\n" for line in [b"section.begin"]
            + [b"   " + k + b" = " + v for k, v in n.keys.items()] + [b"section.end", b""])
        return True

    def n_ParserLoadFromFileByHandle(self, h, path):
        data = self._file(path)
        lines = data.split(b"\r\n") if data is not None else []
        inner = lines[1:lines.index(b"section.end")] if b"section.end" in lines else []
        if lines[:1] == [b"section.begin"] and inner and all(
                _FLAT_LINE.match(line) for line in inner):
            # The engine's parser drops the spaces a value starts with (run
            # m4a: the 34 of 72 report.cfg values that began with a space read
            # back different) and those it ends with (run m2a).
            n = self.nodes[h]
            n.keys, n.inc, n.code = {}, None, None
            for line in inner:
                key, _eq, value = line[3:].partition(b" = ")
                n.keys[key.lower()] = value.strip(b" ")
            return True
        return P.Engine.n_ParserLoadFromFileByHandle(self, h, path)

    def n_GetTriggerManagerStateMachineHandle(self, name):
        return self.managers.get(name.lower(), 0)

    def n_TriggerManagerAdd(self, name):
        if name.lower() in self.managers:
            raise P.RunError("TriggerManagerAdd on a live name makes a second, empty "
                             "manager (probe 3)")
        self.managers[name.lower()] = self.VALTM

    def n_StateMachineLoadFromFile(self, h, path):
        self.loaded[h] = self._file(path)

    def n_StateMachineExecuteState(self, h, name, arg):
        if h != self.VALTM:
            return P.Engine.n_StateMachineExecuteState(self, h, name, arg)
        data = self.loaded.get(h)
        if data is None:
            return
        values = _state_values(data, name)
        if values is None:
            self.log.append(b"ERROR IndexOfState(" + name + b")")
            return
        cand = V.Candidate(b"", b"", 0, b"", b"", False, [], [T.escape(v) for v in values[2:]])
        if not self.compiles(cand):
            self.log.append(b"Compile script error: " + name)
            return
        P.State([values[0][1:]], self).run()


#: One `   <key> = <value>` line of a flat parser file (an .inc's
#: `   Code : struct.begin` is not one).
_FLAT_LINE = re.compile(rb"^   [^ =]+ = ")


def _state_values(data, name):
    """Code values of state `name` in a machine file, or None."""
    lines = data.split(b"\r\n")
    for i, line in enumerate(lines):
        if line == b"   Name = " + name:
            out = []
            j = i + 1
            while not lines[j].startswith(b"   Code : struct.begin"):
                j += 1
            j += 1
            while lines[j] != b"   struct.end":
                out.append(lines[j][len(I.CODE_PREFIX):])
                j += 1
            return out
    return None


@pytest.fixture(scope="module")
def fixture_dir(game_dir, reference_dir, tmp_path_factory):
    import fixtures as F
    out = str(tmp_path_factory.mktemp("m4fixtures"))
    F.write(F.build_all(game_dir, reference_dir), out, game_dir)
    C.write_hook_fixture(out, game_dir)
    return out


@pytest.fixture(scope="module")
def states():
    loaded, helpers = H.load_sources()
    variables = H.build_variables([h.into for h in H.load_hooks()])
    return dict((st.name.lower(), H.state_code(st, helpers, variables))
                for st in loaded if st.name in M4_STATES)


def _setup(eng, inp, entries, titles=None):
    """The boot pipeline's parsers, as qmModList and qmIndex leave them;
    `titles` ({dir: title}) are the mods' ModLibraryGetData titles."""
    mods = eng.n_ParserCreate(b"qm_mods")
    for key, v in ((b"n", len(inp.mods)), (b"self", inp.self_index)):
        eng.n_ParserSetIntValueByKeyByHandle(mods, key, v)
    for i, m in enumerate(inp.mods):
        s = b"%d" % i
        eng.n_ParserSetValueByKeyByHandle(mods, b"dir" + s, m.dir)
        if titles and m.dir in titles:
            eng.n_ParserSetValueByKeyByHandle(mods, b"tit" + s, titles[m.dir])
        eng.n_ParserSetIntValueByKeyByHandle(mods, b"on" + s, 1 if m.enabled else 0)
        eng.n_ParserSetIntValueByKeyByHandle(mods, b"pos" + s, inp.pos[i])
        eng.n_ParserSetIntValueByKeyByHandle(mods, b"ord%d" % inp.pos[i], i)
        eng.n_ParserSetValueByKeyByHandle(mods, b"fo" + s, inp.fo[i])
        eng.n_ParserSetValueByKeyByHandle(mods, b"id" + s, inp.ident[i])
    idx = eng.n_ParserCreate(b"qm_index")
    keys = eng.n_ParserCreate(b"qm_index_keys")
    from ref.index import scan_entries
    scanned = scan_entries(entries)
    eng.n_ParserSetIntValueByKeyByHandle(idx, b"n", len(scanned))
    for k, (path, _size, lines, cls) in enumerate(scanned):
        s = b"%d" % k
        eng.n_ParserSetValueByKeyByHandle(idx, b"p" + s, path)
        eng.n_ParserSetValueByKeyByHandle(idx, b"l" + s, b"%d" % lines)
        eng.n_ParserSetValueByKeyByHandle(idx, b"c" + s, cls)
        got = inp.idx.get(path)
        eng.n_ParserSetValueByKeyByHandle(idx, b"v" + s, b";".join(
            b"%d" % p for p in got[1]) if got else b"-")
        eng.n_ParserSetValueByKeyByHandle(idx, b"a" + s, b";".join(got[2]) if got else b"-")
        eng.n_ParserSetIntValueByKeyByHandle(keys, index_key(path), k)
    rt = eng.n_ParserCreate(b"qm_rt")
    eng.n_ParserSetValueByKeyByHandle(rt, b"fp", b"123-456-789")
    eng.n_ParserSetValueByKeyByHandle(rt, b"qmdir", b"mods\\Quartermaster")


#: qm_boot as qmBoot leaves it before it runs the SelfTest: lines of the kind
#: run m4a printed, a worst tag above every sandbox's own, and Quartermaster
#: listed as new (spelled in upper case, as the lookup ignores case).
BOOT_LINES = [b"OK mods.ini was put into canonical order, Quartermaster last. Moved: "
              b"mods\\QMTestBroken 5->2; mods\\Quartermaster 4->5.",
              b"FAIL No automatic restart: two in a row already. The new files load at "
              b"the next start."]


def _plant_boot(eng, st=V.FAIL, new=b"MODS\\QUARTERMASTER", clashes=()):
    boot = eng.n_ParserCreate(b"qm_boot")
    eng.n_ParserSetIntValueByKeyByHandle(boot, b"n", len(BOOT_LINES))
    for k, line in enumerate(BOOT_LINES):
        eng.n_ParserSetValueByKeyByHandle(boot, b"l%d" % k, line)
    eng.n_ParserSetValueByKeyByHandle(boot, b"st", st)
    eng.n_ParserSetIntValueByKeyByHandle(boot, b"newn", 1)
    eng.n_ParserSetValueByKeyByHandle(boot, b"new0", new)
    eng.n_ParserSetIntValueByKeyByHandle(boot, b"gcn", len(clashes))
    for k, (a, b, path) in enumerate(clashes):
        eng.n_ParserSetValueByKeyByHandle(boot, b"gca%d" % k, a)
        eng.n_ParserSetValueByKeyByHandle(boot, b"gcb%d" % k, b)
        eng.n_ParserSetValueByKeyByHandle(boot, b"gcf%d" % k, path)


def run_case(game_dir, fixture_dir, states, case_name, fixtures, tmp_path,
             compiles=C.duplicate_var_oracle, undeletable=(), titles=None):
    """qmSelfTest's part for one M4 case file, interpreted, after a boot that
    left its qm_boot block; the out folder is written to tmp_path. Returns
    (engine, dump bytes, status, out folder)."""
    entries = C.idx_entries()
    inp = C.offline_inputs(fixtures, game_dir, fixture_dir, entries=entries)
    inp.fp = b"123-456-789"
    cases = C.cases(entries)
    app, save = P.Engine.APP, P.Engine.SAVE
    cases_dir = save + b"qm_test\\cases\\"
    root_of = C.roots(game_dir, fixture_dir)

    def read(path):
        if path.startswith(cases_dir):
            return cases.get(path[len(cases_dir):].decode())
        if path.startswith(app + b"data\\"):
            return inp.read_vanilla(path[len(app) + 5:])
        if path.startswith(app + b"mods\\"):
            rest = path[len(app):]
            parts = rest.split(b"\\", 2)
            root = root_of(parts[0] + b"\\" + parts[1])
            if root is None or len(parts) < 3:
                return None
            full = os.path.join(root, *parts[2].decode().split("\\"))
            try:
                with open(full, "rb") as fh:
                    return fh.read()
            except OSError:
                return None
        return None

    eng = M4Engine(read, compiles, [save + b"qm_test\\out\\m4\\" + p for p in undeletable])
    try:
        for name, code in states.items():
            eng.states[name] = P.State(code, eng)
    except P.Unsupported as exc:
        pytest.skip("the interpreter does not cover the emitted source: %s" % exc)
    _setup(eng, inp, entries, titles)
    _plant_boot(eng)
    eng.states["qmplan"].run()
    out = save + b"qm_test\\out\\"
    rt = eng.n_ParserCreate(b"qm_case_rt")
    stem = case_name[:-4].encode()
    eng.n_ParserSetValueByKeyByHandle(rt, b"outdir", out)
    eng.n_ParserSetValueByKeyByHandle(rt, b"out", out + stem + b".txt")
    eng.n_ParserSetValueByKeyByHandle(rt, b"status", b"started")
    case = eng.n_ParserCreate(b"qm_case")
    eng.n_ParserLoadFromFileByHandle(case, cases_dir + case_name.encode())
    collecting = gc.isenabled()
    gc.disable()
    try:
        eng.states["qmcasem4"].run()
    except P.Unsupported as exc:
        pytest.skip("the interpreter does not cover a native: %s" % exc)
    finally:
        if collecting:
            gc.enable()
    folder = str(tmp_path)
    for path, data in eng.written.items():
        if path.startswith(out):
            full = os.path.join(folder, *path[len(out):].decode().split("\\"))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "wb") as fh:
                fh.write(data)
    return eng, eng.written.get(out + stem + b".txt"), eng.n_ParserGetValueByKeyByHandle(
        rt, b"status"), folder


def test_case_a_wasd_broken(game_dir, fixture_dir, states, tmp_path):
    """WASD + Broken: the merged registershortcuts.inc is rejected, the
    winner's copy written, FAIL; the vanilla files validate, the broken one
    does not, and the manager recovers; every byte equals the twin's."""
    eng, dump, status, folder = run_case(game_dir, fixture_dir, states, "qm_m4a.cfg",
                                         C.RUN_A, tmp_path)
    assert status == b"ok"
    lines = []
    problems = C.check_dump(folder, dump, C.cases(C.idx_entries())["qm_m4a.cfg"],
                            game_dir, fixture_dir, out=lines.append)
    assert problems == []
    compile_errors = [x for x in eng.log if x.startswith(b"Compile script error")]
    names = C.expected_failures(fixtures_dir=fixture_dir)["qm_m4a.cfg"]
    # The broken vanilla copy right after the eleven vanilla files, then the
    # merged registershortcuts.inc (its number depends on how many hook files
    # Quartermaster ships: they come first in plan order).
    assert len(names) == 2 and names[0] == "qmVal%d" % (C.SEQ_BASE + len(C.VAL_FILES))
    assert compile_errors == [b"Compile script error: " + n.encode() for n in names]
    report = open(os.path.join(folder, "m4", "a", "work", "report.txt"), "rb").read()
    assert b"FAIL gui\\menu.inc\\registershortcuts.inc\r\n" in report
    assert b"  candidate merged: does not compile\r\n" in report
    # The live boot's block stays out of the sandbox's report (runs m4a, m4c).
    assert b"\r\nBoot:\r\n" not in report and BOOT_LINES[0] not in report
    rload = next(r for r in C.S.parse_dump(dump) if r[0] == b"rload")
    assert int(rload[2]) > 0 and rload[3] == b"0"
    written = open(os.path.join(folder, "m4", "a", "qmdir", "data", "gui", "menu.inc",
                                "registershortcuts.inc"), "rb").read()
    wasd = open(os.path.join(fixture_dir, "QMTestWASD", "data", "gui", "menu.inc",
                             "registershortcuts.inc"), "rb").read()
    assert I.parse(written).values == I.parse(wasd).values


@pytest.mark.slow
def test_case_b_stale_and_determinism(game_dir, fixture_dir, states, tmp_path):
    """WASD + CamSpeed: both merges written and listed; with CamSpeed dropped
    both outputs are deleted as stale; two generations from the same inputs
    write the same bytes; a cold start too."""
    eng, dump, status, folder = run_case(game_dir, fixture_dir, states, "qm_m4b.cfg",
                                         C.RUN_B, tmp_path)
    assert status == b"ok"
    problems = C.check_dump(folder, dump, C.cases(C.idx_entries())["qm_m4b.cfg"],
                            game_dir, fixture_dir, out=lambda s: None)
    assert problems == []
    assert not [x for x in eng.log if x.startswith(b"Compile script error")]
    base = os.path.join(folder, "m4")
    for rel in (("qmdir", "data", "gui", "menu.inc", "oncamera.inc"),
                ("qmdir", "data", "gui", "menu.inc", "cameracontrol.inc"),
                ("qmdir", "data", "quartermaster", "state", "manifest.cfg"),
                ("work", "report.txt")):
        assert open(os.path.join(base, "c", *rel), "rb").read() == \
            open(os.path.join(base, "d", *rel), "rb").read()
    assert not os.path.exists(os.path.join(base, "b", "qmdir", "data", "gui", "menu.inc",
                                           "oncamera.inc"))


@pytest.mark.slow
def test_an_undeletable_stale_file_is_overwritten(game_dir, fixture_dir, states, tmp_path):
    """DeleteFileStream leaves the file: it is overwritten with the winner's
    validated copy and listed as `left` (plan S9)."""
    rel = b"b\\qmdir\\data\\gui\\menu.inc\\oncamera.inc"
    eng, dump, status, folder = run_case(game_dir, fixture_dir, states, "qm_m4b.cfg",
                                         C.RUN_B, tmp_path, undeletable=[rel])
    rows = [r for r in C.S.parse_dump(dump) if r[0] == b"stale"]
    assert (b"gui\\menu.inc\\oncamera.inc", b"overwritten", b"winner") in [r[3:6] for r in rows]
    manifest = open(os.path.join(folder, "m4", "b", "qmdir", "data", "quartermaster",
                                 "state", "manifest.cfg"), "rb").read()
    assert b";left|gui\\menu.inc\\oncamera.inc|" in manifest
    written = open(os.path.join(folder, "m4", "b", "qmdir", "data", "gui", "menu.inc",
                                "oncamera.inc"), "rb").read()
    wasd = open(os.path.join(fixture_dir, "QMTestWASD", "data", "gui", "menu.inc",
                             "oncamera.inc"), "rb").read()
    assert I.parse(written).values == I.parse(wasd).values


@pytest.mark.slow
def test_a_merged_hook_file_that_does_not_compile_falls_back(game_dir, fixture_dir, states,
                                                             tmp_path):
    """QMTestM4Hook's change to eventmainmenu.inc rejected: merged+hook fails,
    winner+hook is the same content and is not tried again, vanilla+hook is
    written - FAIL, and every byte still equals the twin's."""
    def refuse(cand):
        return (b";const cTagCredits = 111; // QMTEST m4hook" not in cand.values
                and C.duplicate_var_oracle(cand))

    eng, dump, status, folder = run_case(game_dir, fixture_dir, states, "qm_m4b.cfg",
                                         C.RUN_B, tmp_path, compiles=refuse)
    problems = C.check_dump(folder, dump, C.cases(C.idx_entries())["qm_m4b.cfg"],
                            game_dir, fixture_dir, out=lambda s: None)
    assert problems == []
    rows = C.S.parse_dump(dump)
    first = C._gen_block(rows, 0)
    plan_m = dict((r[3], r[2]) for r in first if r[0] == b"plan")
    m = plan_m[b"gui\\menu.inc\\eventmainmenu.inc"]
    assert [(r[3], r[6]) for r in first if r[0] == b"cand" and r[2] == m] == [
        (b"merged+hook", b"0"), (b"vanilla+hook", b"1")]
    path = next(r for r in first if r[0] == b"path" and r[2] == m)
    assert (path[3], path[4]) == (b"fallback", b"FAIL")


def test_case_c_conflict_and_near_edits_by_vanilla_line(game_dir, fixture_dir, states,
                                                         tmp_path):
    """WASD + Conflict + M4Near on oncamera.inc: the report's conflict and
    near lines, built from qmMerge's rows in game, equal the twin's."""
    eng, dump, status, folder = run_case(game_dir, fixture_dir, states, "qm_m4c.cfg",
                                         C.RUN_C, tmp_path)
    assert status == b"ok"
    problems = C.check_dump(folder, dump, C.cases(C.idx_entries())["qm_m4c.cfg"],
                            game_dir, fixture_dir, out=lambda s: None)
    assert problems == []
    report = open(os.path.join(folder, "m4", "x", "work", "report.txt"), "rb").read()
    assert (b"  conflict: vanilla line 18 of 1. mods\\QMTestConflict lost to 3. "
            b"mods\\QMTestWASD\r\n") in report
    assert (b"  near: vanilla line 14 of 2. mods\\QMTestM4Near and vanilla lines 18-21 of "
            b"3. mods\\QMTestWASD\r\n") in report
    # The game's conflicts.txt (check_dump compared it with the twin's, byte
    # for byte) has the conflict and the pair, and the Report view opens with
    # the pair lines.
    conf = open(os.path.join(folder, "m4", "x", "work", "conflicts.txt"), "rb").read()
    assert conf.startswith(b"Quartermaster conflict report\r\n")
    assert b"\r\nC1 gui\\menu.inc\\oncamera.inc, vanilla line" in conf
    assert b"\r\n   why: 3 is later in the load order\r\n" in conf
    rep = eng.named[b"qm_report"]
    m = [eng.nodes[rep].keys[b"m%d" % k] for k in range(int(eng.nodes[rep].keys[b"mlines"]))]
    assert m[3] == RP.CONFLICTS_HEAD and m[4].startswith(b"  1 <-> 3: 1 conflict - ")
    assert eng.nodes[rep].keys[b"cpd0"] == b"Loses 1 conflict to mods\\QMTestWASD"


def test_conflicts_txt_in_a_file_full_of_routines_equals_the_twins(game_dir, states):
    """showcustomgame.inc has a dozen routines: conflicts and changes close
    together on the first and last lines of each and in the main code, an
    insertion, a removal, a duplicate - the merge rows planted as qmMerge
    leaves them (ref/merge.py result_rows) - and qmConflicts' conflicts.txt,
    pair lines and Details sentences equal ref/conflicts.py's byte for byte:
    the routine scanner, `at:` and the change words above all."""
    from conftest import vanilla_bytes
    from ref import conflicts as CF
    from ref import merge as MG
    from ref.planner import Decision
    path = b"gui\\menu.inc\\showcustomgame.inc"
    van = vanilla_bytes("gui/menu.inc/showcustomgame.inc")
    vinc = I.parse(van)
    base = V.code_values(van)
    rt = CF.routines(base)
    assert len(set(x for x in rt if x is not None)) > 10
    # The first and last line of every routine, and main code between them,
    # at least 8 lines apart so that no two edits meet by accident.
    picks, last = [], -100
    for k in range(1, len(rt) - 4):
        edge = rt[k] != rt[k - 1] or rt[k] != rt[k + 1]
        if (edge or k % 40 == 0) and k - last >= 8:
            picks.append(k)
            last = k
    assert len(picks) > 20
    mod_a, mod_b, mod_c = list(base), list(base), list(base)
    for x, k in enumerate(picks):
        how = x % 4
        if how == 0:                    # a conflict, B's change wins
            mod_a[k] = base[k] + b" // qm a"
            mod_b[k] = base[k] + b" // qm b"
        elif how == 1:                  # close together: 2 lines apart
            mod_a[k] = base[k] + b" // qm a"
            mod_b[k + 2] = base[k + 2] + b" // qm b"
        elif how == 2:                  # the same change: a duplicate
            mod_a[k] = mod_b[k] = base[k] + b" // qm same"
            mod_c[k] = base[k] + b" // qm c"
        else:                           # B removes the line A changes
            mod_a[k] = base[k] + b" // qm a"
            mod_b[k] = None
    mod_b = [v for v in mod_b if v is not None]
    mg = MG.merge(base, [(0, mod_a), (1, mod_b), (2, mod_c)])
    assert mg.mode == "merged" and mg.conflicts and mg.pairs
    assert any(h.status == MG.DUPLICATE for h in mg.hunks)
    rows = MG.result_rows(mg)
    d = Decision(path, b"merge-inc", b"merge-inc", b"merge-allow-list", 2, [0, 1, 2])
    r = V.PathResult(0, d)
    r.participants, r.winner, r.merge, r.job, r.code = [0, 1, 2], 2, mg, 0, b"merged"
    r.first_line, r.vanilla_n = len(vinc.keys) + 3, len(vinc.values)
    r.chosen = V.Candidate(path, V.TIER_MERGED, 0, b"t", b"t", True, [], [])
    # Whole files: the planner's winner, a fallback to the winner's copy, and
    # vanilla with the hook lines - three owners of one pair's whole files.
    hud = V.PathResult(1, Decision(b"hud\\hud.mat", b"winner", b"winner", b"not-on-allow-list",
                                   1, [0, 1]))
    hud.code = b"winner"
    fb = V.PathResult(2, Decision(b"gui\\menu.inc\\showsettings.inc", b"merge-inc",
                                  b"merge-inc", b"merge-allow-list", 2, [0, 2]))
    fb.participants, fb.winner, fb.merge, fb.job, fb.code = [0, 2], 2, mg, 1, b"fallback"
    fb.chosen = V.Candidate(fb.path, V.TIER_WINNER, 1, b"t", b"t", True, [], [])
    vh = V.PathResult(3, Decision(b"gui\\menu.inc\\doprogress.inc", b"hook", b"hook",
                                  b"quartermaster-hook", 3, [0, 1, 3]))
    vh.participants, vh.winner, vh.code = [0, 1], 1, b"fallback"
    vh.chosen = V.Candidate(vh.path, V.TIER_VANILLA_HOOK, 2, b"t", b"t", True, [], [])
    g = V.Generation()
    g.gen, g.outhash, g.paths = 7, b"1-2-3", [r, hud, fb, vh]
    qm = b"mods\\Quartermaster"
    dirs = RP.Dirs({0: b"mods\\QMTestA", 1: b"mods\\QMTestB", 2: b"mods\\QMTestC", 3: qm},
                   {1: b"B's title"})
    c = CF.build(g, dirs, [0, 1, 2, 3], 3, lambda p: van if p == path else None)
    want = CF.conflicts_bytes(CF.report_lines(c, g, H.QM_VERSION.encode("ascii")))
    assert b"procedure " in want and b"main code" in want and b"the same change" in want
    assert b"2 whole files (B's title 1, vanilla 1)" in want

    app = P.Engine.APP
    eng = M4Engine(lambda p: van if p == app + b"data\\" + path else None,
                   C.duplicate_var_oracle)
    for name, code in states.items():
        eng.states[name] = P.State(code, eng)
    mods = eng.n_ParserCreate(b"qm_mods")
    eng.n_ParserSetIntValueByKeyByHandle(mods, b"n", 4)
    eng.n_ParserSetIntValueByKeyByHandle(mods, b"self", 3)
    for i in range(4):
        eng.n_ParserSetValueByKeyByHandle(mods, b"dir%d" % i, dirs[i])
        eng.n_ParserSetValueByKeyByHandle(mods, b"tit%d" % i, dirs.titles.get(i, b""))
        for key in (b"on", b"pos", b"ord"):
            eng.n_ParserSetIntValueByKeyByHandle(mods, key + b"%d" % i, 1 if key == b"on" else i)
    plan = eng.n_ParserCreate(b"qm_plan")
    eng.n_ParserSetIntValueByKeyByHandle(plan, b"n", 4)
    for m, x in enumerate(g.paths):
        dx = x.decision
        for key, v in ((b"path", dx.path), (b"act", dx.action), (b"why", dx.reason),
                       (b"win", b"%d" % dx.winner),
                       (b"prov", b";".join(b"%d" % p for p in dx.providers))):
            eng.n_ParserSetValueByKeyByHandle(plan, key + b"%d" % m, v)
    gen = eng.n_ParserCreate(b"qm_gen")
    work = P.Engine.SAVE + b"quartermaster\\"
    for key, v in ((b"work", work), (b"outhash", b"1-2-3")):
        eng.n_ParserSetValueByKeyByHandle(gen, key, v)
    eng.n_ParserSetIntValueByKeyByHandle(gen, b"n", 4)
    eng.n_ParserSetIntValueByKeyByHandle(gen, b"gen", 7)
    for m, x in enumerate(g.paths):
        s = b"%d" % m
        for key, v in ((b"pp", b";".join(b"%d" % p for p in x.participants)),
                       (b"r", x.chosen.tier if x.chosen else b""), (b"x", x.code), (b"e", b""),
                       (b"pw", b"" if x.winner is None else b"%d" % x.winner)):
            eng.n_ParserSetValueByKeyByHandle(gen, key + s, v)
        for key, v in ((b"j", x.job), (b"vf", x.first_line), (b"vn", x.vanilla_n)):
            eng.n_ParserSetIntValueByKeyByHandle(gen, key + s, v)
    mgp = eng.n_ParserCreate(b"qm_mg")
    for job in (0, 1):
        js = b"j%d" % job
        eng.n_ParserSetIntValueByKeyByHandle(mgp, js + b"rows", len(rows))
        for k, row in enumerate(rows):
            eng.n_ParserSetValueByKeyByHandle(mgp, js + b"r%d" % k, row)
        eng.n_ParserSetValueByKeyByHandle(mgp, js + b"mode", b"merged")
        eng.n_ParserSetValueByKeyByHandle(mgp, js + b"reason", b"-")
    eng.states["qmconflicts"].run()
    got = eng.written.get(work + b"conflicts.txt")
    if got != want:
        g_lines, w_lines = (got or b"").split(b"\r\n"), want.split(b"\r\n")
        k = next(i for i, (x, y) in enumerate(zip(g_lines, w_lines)) if x != y)
        raise AssertionError("line %d: game %r, twin %r" % (k + 1, g_lines[k], w_lines[k]))
    conf = eng.nodes[eng.named[b"qm_conf"]].keys
    pairs, said = CF.window(c)
    assert [conf[b"w%d" % k] for k in range(int(conf[b"wn"]))] == pairs
    assert dict((p, conf[b"d%d" % p]) for p in said) == said


def test_the_report_names_a_mod_by_its_title(game_dir, fixture_dir, states, tmp_path):
    """Case C with titles for QMTestConflict and Quartermaster: the report
    names them by the title with the dir beside it, the untitled mods by dir,
    Quartermaster's titled row without the ` (Quartermaster)` mark, and every
    byte still equals the twin's (which reads the titles from the dump)."""
    titles = {b"mods\\QMTestConflict": b"Conflict test",
              b"mods\\Quartermaster": b"Quartermaster"}
    eng, dump, status, folder = run_case(game_dir, fixture_dir, states, "qm_m4c.cfg",
                                         C.RUN_C, tmp_path, titles=titles)
    assert status == b"ok"
    problems = C.check_dump(folder, dump, C.cases(C.idx_entries())["qm_m4c.cfg"],
                            game_dir, fixture_dir, out=lambda s: None)
    assert problems == []
    report = open(os.path.join(folder, "m4", "x", "work", "report.txt"), "rb").read()
    assert (b"  conflict: vanilla line 18 of 1. Conflict test (mods\\QMTestConflict) lost "
            b"to 3. mods\\QMTestWASD\r\n") in report
    assert b". Quartermaster (mods\\Quartermaster)\r\n" in report
    assert b"(Quartermaster) (Quartermaster)" not in report
    assert b"(mods\\Quartermaster) (Quartermaster)" not in report


def test_a_mod_that_half_loses_is_left_out_in_game(game_dir, fixture_dir, states, tmp_path):
    """WASD + M4Split + M4Near on oncamera.inc, M4Split's second edit refused
    without its first: the second qmMerge batch merges M4Near and WASD, that
    subset is written as `partial`, WARN, and every byte, row and report line
    equals the twin's (Renaissance + MGraphics - Main Menu, 2026-09-30)."""
    eng, dump, status, folder = run_case(game_dir, fixture_dir, states, "qm_m4c.cfg",
                                         C.RUN_D, tmp_path, compiles=C.split_oracle)
    assert status == b"ok"
    problems = C.check_dump(folder, dump, C.cases(C.idx_entries())["qm_m4c.cfg"],
                            game_dir, fixture_dir, out=lambda s: None)
    assert problems == []
    rows = C.S.parse_dump(dump)
    first = C._gen_block(rows, 0)
    plan_m = dict((r[3], r[2]) for r in first if r[0] == b"plan")
    m = plan_m[b"gui\\menu.inc\\oncamera.inc"]
    assert [(r[3], r[6]) for r in first if r[0] == b"cand" and r[2] == m] == [
        (b"merged", b"0"), (b"subset", b"1")]
    path = next(r for r in first if r[0] == b"path" and r[2] == m)
    assert (path[3], path[4]) == (b"partial", b"WARN")
    report = open(os.path.join(folder, "m4", "x", "work", "report.txt"), "rb").read()
    assert b"  candidate subset: compiles\r\n" in report
    assert b"mods\\QMTestM4Split\r\n" in report and b"  left out: " in report
    assert any(b"[qm] gen subset merges=1" in x for x in eng.log)


@pytest.mark.slow
def test_a_hook_file_that_never_compiles_writes_nothing(game_dir, fixture_dir, states,
                                                        tmp_path):
    """vanilla+hook failing is FATAL: no output, no manifest, report FATAL."""
    def refuse_camera(cand):
        if any(V.is_gen_line(v) for v in cand.values):
            return False
        return C.duplicate_var_oracle(cand)

    eng, dump, status, folder = run_case(game_dir, fixture_dir, states, "qm_m4a.cfg",
                                         C.RUN_A, tmp_path, compiles=refuse_camera)
    gen = [r for r in C.S.parse_dump(dump) if r[0] == b"gen"][0]
    assert gen[2] == b"fatal" and gen[5] == b"gui\\menu.inc\\cameracontrol.inc"
    assert not os.path.exists(os.path.join(folder, "m4", "a", "qmdir"))
    report = open(os.path.join(folder, "m4", "a", "work", "report.txt"), "rb").read()
    assert b"\r\nFATAL: gui\\menu.inc\\cameracontrol.inc: " in report
    assert any(b"[qm] FATAL gui\\menu.inc\\cameracontrol.inc" in x for x in eng.log)


def test_check_path_refuses_what_the_twin_refuses(game_dir, states):
    """qmWrCheckPath, interpreted, over every merge-class path, the never-
    generate list, the hook files and the other classes: the same answer as
    ref/validate.py writable."""
    entries = C.idx_entries()
    loaded, helpers = H.load_sources()
    code = []
    for name in H.resolve_helpers(helpers["qmwrite"], helpers) + ["qmwrite"]:
        h = helpers[name]
        code += H.render_lines(h, H._vars_for(h, H.BUILD_VARIABLES))
    code.append(b"var qmTcR : Integer = qmWrCheckPath(ParserGetValueByKeyByHandle("
                b"ParserSelectByKey('qm_t'), 'rel'));")
    code.append(b"ParserSetIntValueByKeyByHandle(ParserSelectByKey('qm_t'), 'r', qmTcR);")
    eng = M4Engine(lambda p: None, C.duplicate_var_oracle)
    state = P.State(code, eng)
    from ref.index import scan_entries
    scanned = scan_entries(entries)
    idx = eng.n_ParserCreate(b"qm_index")
    keys = eng.n_ParserCreate(b"qm_index_keys")
    for k, (path, _s, _l, cls) in enumerate(scanned):
        eng.n_ParserSetValueByKeyByHandle(idx, b"p%d" % k, path)
        eng.n_ParserSetValueByKeyByHandle(idx, b"c%d" % k, cls)
        eng.n_ParserSetIntValueByKeyByHandle(keys, index_key(path), k)
    t = eng.n_ParserCreate(b"qm_t")
    cls = dict((e[0], e[3]) for e in scanned)
    never = [e for e in entries if e[3] == b"never"]
    wta = [e for e in entries if e[3] == b"wta"]
    probe = ([e[0] for e in entries if e[3] == b"merge"] + [e[0] for e in never[::40]]
             + [e[0] for e in wta[::20]] + [h.replace(b"/", b"\\") for h in V.NEVER_INC]
             + [b"gui\\menu.inc\\..\\menu.aix", b"\\gui\\menu.inc\\x.inc",
                b"scripts\\dmscript.global", b"quartermaster\\core.aix",
                b"GUI\\MENU.INC\\ONCAMERA.INC", b"gui\\menu.inc\\oncamera.inc~"])
    for path in probe:
        eng.n_ParserSetValueByKeyByHandle(t, b"rel", path)
        state.run()
        got = eng.n_ParserGetIntValueByKeyByHandle(t, b"r")
        assert got == (1 if V.writable(path, cls.get(path)) else 0), path
    assert sum(1 for p in probe if V.writable(p, cls.get(p))) == 311


def run_real(game_dir, states, gensalt=b""):
    """qmGenerate in production mode for Quartermaster alone: the mirror is
    dist/Quartermaster deployed as mods\\Quartermaster (read by absolute path,
    written by the relative one), the pristine hook lines are the dist's."""
    entries = C.idx_entries()
    inp = C.offline_inputs((), game_dir, entries=entries)
    app = P.Engine.APP
    dist = H.DIST_MOD
    roots = (app + b"mods\\Quartermaster\\", b"mods\\Quartermaster\\")

    def read(path):
        for root in roots:
            if path.startswith(root):
                full = os.path.join(dist, *path[len(root):].decode().split("\\"))
                try:
                    with open(full, "rb") as fh:
                        return fh.read()
                except OSError:
                    return None
        if path.startswith(app + b"data\\"):
            return inp.read_vanilla(path[len(app) + 5:])
        return None

    eng = M4Engine(read, C.duplicate_var_oracle)
    for name, code in states.items():
        eng.states[name] = P.State(code, eng)
    _setup(eng, inp, entries)
    eng.states["qmplan"].run()
    if gensalt:
        gin = eng.n_ParserCreate(b"qm_gen_in")
        eng.n_ParserSetValueByKeyByHandle(gin, b"gensalt", gensalt)
    eng.states["qmgenerate"].run()
    g = eng.named[b"qm_gen"]
    return eng, eng.nodes[g].keys


def test_quartermaster_alone_finds_the_shipped_copies_current(game_dir, states):
    """The first boot of a fresh install: every hook output equals the shipped
    copy by token although the shipped copy is not padded - nothing is
    written, nothing changed, no restart (the evidence of run m5compile's
    `failed` lines is logged per write for the next run)."""
    eng, gen = run_real(game_dir, states)
    ws = [gen[b"w%d" % m] for m in range(int(gen[b"n"]))]
    hooks = len(H.HOOK_FILES)
    assert ws == [b"same"] * hooks and gen[b"changed"] == b"0" and gen[b"status"] == b"ok"
    lines = [x for x in eng.log if x.startswith(b"[qm] write ")]
    assert len(lines) == hooks and all(b" result=2 " in x for x in lines)
    assert not [p for p in eng.written if p.startswith(b"mods\\Quartermaster\\data\\gui")]
    # The manifest goes to the relative spelling, the one written by.
    assert b"mods\\Quartermaster\\data\\quartermaster\\state\\manifest.cfg" in eng.written


def test_a_changed_hook_output_is_written_by_the_relative_path(game_dir, states):
    eng, gen = run_real(game_dir, states, gensalt=b"7")
    ws = dict((eng.nodes[eng.named[b"qm_plan"]].keys[b"path%d" % m], gen[b"w%d" % m])
              for m in range(int(gen[b"n"])))
    assert ws[b"gui\\menu.inc\\cameracontrol.inc"] == b"yes"
    assert sorted(v for k, v in ws.items() if k != b"gui\\menu.inc\\cameracontrol.inc") == [b"same"] * (len(H.HOOK_FILES) - 1)
    data = eng.written[b"mods\\Quartermaster\\data\\gui\\menu.inc\\cameracontrol.inc"]
    assert b";const qmHookGen = '" + gen[b"outhash"] + b"-7';" in data
    line = next(x for x in eng.log if x.startswith(b"[qm] write gui\\menu.inc\\cameracontrol.inc"))
    assert b" result=1 " in line and line.endswith(
        b" to mods\\Quartermaster\\data\\gui\\menu.inc\\cameracontrol.inc")


def test_the_boots_own_report_keeps_its_boot_block_and_reads_back(game_dir, states):
    """The production generation (qm_gen box empty): the report takes the boot's
    block and NEW marks, laid out as ref/report.py lays them out; report.cfg is
    the twin's bytes, and qmReportLoad reads it back through the engine's
    parser as the same qm_report, leading spaces included."""
    eng, gen = run_real(game_dir, states)
    assert gen[b"box"] == b""
    eng.states["qmreport"].run()
    rep = eng.named[b"qm_report"]
    plain = dict(eng.nodes[rep].keys)
    lines = [plain[b"l%d" % k] for k in range(int(plain[b"lines"]))]
    _plant_boot(eng)
    eng.states["qmreport"].run()
    got = dict(eng.nodes[rep].keys)
    assert lines[2].startswith(b"status OK: ")
    want = ([lines[0], lines[1], b"status FAIL: " + lines[2][len(b"status OK: "):]]
            + [b"", b"Boot:"] + [b"  " + x for x in BOOT_LINES] + lines[3:])
    assert [got[b"l%d" % k] for k in range(int(got[b"lines"]))] == want
    assert (plain[b"dir0"], plain[b"st0"], got[b"st0"]) == (b"mods\\Quartermaster", V.OK, RP.NEW)
    work = P.Engine.SAVE + b"quartermaster\\"
    assert eng.written[work + b"report.txt"] == RP.report_bytes(want)
    assert eng.written[work + b"report.cfg"] == RP.report_cfg(got)
    assert any(v.startswith(b" ") for v in got.values())
    eng.states["qmreportload"].run()
    assert dict(eng.nodes[eng.named[b"qm_report"]].keys) == got


def test_a_clash_shows_in_the_blocks_of_both_mods(game_dir, states):
    """The boot's clash (qm_boot gc<k>) goes into the mod's own block of the
    report by mod: FAIL in its head and a line naming the file and the other
    mod, word for word the twin's (ref/report.py _clash_lines); the other mod
    here has no position, so it is named by its dir. Run look-wsZ showed both
    clashing mods as OK there while the window said FAIL."""
    eng, gen = run_real(game_dir, states)
    eng.states["qmreport"].run()
    rep = eng.named[b"qm_report"]
    _plant_boot(eng)
    eng.states["qmreport"].run()
    before = dict(eng.nodes[rep].keys)
    qm = b"mods\\Quartermaster"
    clashes = [(b"mods\\Gone", qm.upper(), b"lib\\unit.script")]
    _plant_boot(eng, clashes=clashes)
    eng.states["qmreport"].run()
    got = dict(eng.nodes[rep].keys)
    mlines = [before[b"m%d" % k] for k in range(int(before[b"mlines"]))]
    head = next(k for k, line in enumerate(mlines) if line.endswith(b"mods\\Quartermaster "
                                                                     b"(Quartermaster)"))
    want_line = RP._clash_lines(0, RP.Dirs({0: qm}), RP.Boot(BOOT_LINES, V.FAIL, [], clashes))
    assert want_line == [b"  FAIL scripts\\lib\\unit.script: mods\\Gone ships it too: only one "
                         b"copy loads, and the game may not start with both"]
    want = (mlines[:head] + [b"FAIL " + mlines[head].split(b" ", 1)[1], mlines[head + 1]]
            + want_line + mlines[head + 2:])
    assert [got[b"m%d" % k] for k in range(int(got[b"mlines"]))] == want
    # The window's status keys stay as they were: its model marks a clash FAIL
    # from qm_glob itself (qmUiModel, stsrc globals).
    assert (got[b"st0"], got[b"why0"]) == (before[b"st0"], before[b"why0"])
