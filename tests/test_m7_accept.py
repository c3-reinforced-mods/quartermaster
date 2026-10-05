"""Offline gates for tools/m7accept.py, the acceptance runner of M7.

The runs themselves are in-game. Here a run folder is made up the way hrun
leaves one - summary.json, the copied logs, qm_save, qm_mod, the SelfTest's
output - from what the twin says the game does with the fixtures, and the
checker must accept it; each test then breaks one fact and the checker must
name it. The twin (ref/validate.py) is tested on its own elsewhere; what is
tested here is that the checker reads the logs and the files right.
"""
import json
import os
import re
import shlex

import pytest

import hbuild
import m4cases
import m5cases
import m6cases
import m7accept as A
from ref import conflicts as CF
from ref import manifest as MF
from ref import order as O
from ref import report as RP
from ref import selftest as S
from ref import validate as V

REPO = hbuild.REPO
FIXTURES = os.path.join(REPO, "fixtures")
QM = b"mods\\Quartermaster"
CAMSPEED = b"mods\\QMTestCamSpeed"
WASD = b"mods\\QMTestWASD"

needs_fixtures = pytest.mark.skipif(
    not (os.path.isdir(os.path.join(FIXTURES, "QMTestWASD"))
         and os.path.isdir(os.path.join(hbuild.GAME, "data"))),
    reason="fixtures not built (python tools/fixtures.py) or the game is not installed")


# ------------------------------------------------------------ plan / prepare
def test_the_plan_lists_every_scenario_in_order_with_its_check():
    lines = []
    assert A.plan("CASES", "LOGS", lines.append, expect_broken=["qmVal3"]) == 0
    text = "\n".join(lines)
    heads = [m.group(1) for m in (re.match(r"^\d+\. m7(\w+) - ", ln) for ln in lines) if m]
    assert heads == list(A.NAMES)
    assert "python tools/hrun.py --logs-dir LOGS --run-id m7vanilla --no-quartermaster" in text
    assert "--expect-compile-error qmVal3" in text
    assert "--state %s" % os.path.join("LOGS", "m7i2", "qm_save") in text
    assert "--case %s" % os.path.join("CASES", "qm_case_ui9.cfg") in text
    for n in A.NAMES:
        assert "python tools/m7accept.py check %s --scenario %s" % (
            os.path.join("LOGS", "m7" + n), n) in text
    # Lives and restarts per run, as the milestone asks.
    restarts = dict((a.name, a.s.restarts) for a in A.scenarios(expect_broken=[]))
    assert restarts == {"vanilla": 0, "i1": 1, "i2": 1, "i3": 1, "i4": 1, "i5": 1, "i6": 1,
                        "i7": 3, "i8": 1, "i9": 2, "order": 2, "saved": 3}


def test_the_vanilla_run_ends_on_the_last_line_of_the_games_log():
    # Until 2026-10-05 it waited out a 90 s timeout; the log is complete after
    # ~5 s, ending with Steam's achievement callback.
    s = A.by_name("vanilla", expect_broken=[]).s
    cmd = m5cases.command(s, "C", "L", prefix="m7")
    assert "--no-quartermaster" in cmd and '--until "SteamwrapGetNumAchievements"' in cmd
    assert "--timeout 60" in cmd


def test_every_planned_command_parses_as_hrun_options():
    import hrun
    for a in A.scenarios(expect_broken=["qmVal3"]):
        cmd = m5cases.command(a.s, "C", "L", prefix="m7")
        # As cmd.exe splits it: the quoted marker is one argument.
        argv = [x.strip('"') for x in shlex.split(cmd, posix=False)][2:]
        _recover, opts = hrun.parse_args(argv)
        assert opts.run_id == "m7" + a.name
        assert opts.quartermaster == a.s.quartermaster
        assert opts.timeout == a.s.timeout and opts.until == (a.s.until or None)
        assert opts.until_log == a.s.until_log
        assert opts.expect_compile_errors == a.s.expect


def test_prepare_writes_every_case_the_runs_name(tmp_path, monkeypatch):
    monkeypatch.setattr(m5cases, "installed_dirs", lambda game=None: [b"mods\\SW_Frontline_Protocol"])
    out = tmp_path / "cases"
    said = []
    # QMTestNew ships the game's own copy of one file the index reads.
    vanilla = tmp_path.joinpath("G", "data", *m5cases.NEW_SHIPS.split("\\"))
    vanilla.parent.mkdir(parents=True)
    vanilla.write_bytes(b"section.begin\r\nsection.end\r\n")
    assert A.prepare(str(out), str(tmp_path / "fixtures"), str(tmp_path / "G"), said.append) == 0
    names = set(os.listdir(out))
    for a in A.scenarios(str(out), "L", expect_broken=[]):
        for c in a.s.cases:
            assert os.path.basename(c) in names, c
    assert (out / "qm_case_ui9.cfg").read_bytes() == m6cases.i9_case_files()["qm_case_ui9.cfg"]
    assert (tmp_path / "fixtures" / "m5" / "QMTestNew" / "readme.txt").is_file()


# ------------------------------------------------------------ the log reader
def test_blocks_read_a_boot_and_an_apply():
    log = b"\r\n".join([
        b"LOG| 1 |[qm] boot version 0.0.0 hook=cameracontrol hookgen=1-2-3",
        b"LOG| 2 |[qm] mod 1 pos=0 on=1 origin=l dir=mods\\QMTestCamSpeed tag=0 ini=5 "
        b"tit=Camera speed test",
        b"LOG| 3 |[qm] mod 0 pos=1 on=1 origin=s dir=mods\\Quartermaster tag=0 ini=5",
        b"LOG| 4 |[qm] plan gui\\menu.inc\\oncamera.inc skip (merge-inc, merge-allow-list) "
        b"winner=0 providers=0",
        b"LOG| 5 |[qm] boot report OK The game restarted to load the new files (x).",
        b"LOG| 5 |[qm] boot clash|mods\\QMTestCamSpeed|mods\\Two Words|lib\\unit.script",
        b"LOG| 6 |[qm] boot version 0.0.0 apply seq=1",
        b"LOG| 7 |[qm] mod 1 pos=0 on=1 origin=l dir=mods\\QMTestCamSpeed tag=0 ini=5",
        b"LOG| 8 |[qm] order: apply sets on=0 for mods\\QMTestCamSpeed",
        b"LOG| 9 |[qm] gen start sandbox= decisions=1 merges=0 previous files=2",
        b"LOG| 10 |[qm] gen stale gui\\menu.inc\\oncamera.inc deleted",
        b"LOG| 11 |[qm] known: new mod mods\\QMTestNew"])
    boot, apply_ = A.blocks([("0.log", log)])
    assert (boot.apply, boot.hookgen, boot.box) == (None, b"1-2-3", None)
    # A log written before the title came in ends at ini=; its title reads as empty.
    assert boot.mods == {1: [0, True, b"l", CAMSPEED, b"Camera speed test"],
                         0: [1, True, b"s", QM, b""]}
    assert [(d.path, d.action, d.winner, d.providers) for d in boot.plan] == [
        (b"gui\\menu.inc\\oncamera.inc", b"skip", 0, [0])]
    assert boot.boot_lines == [b"OK The game restarted to load the new files (x)."]
    assert boot.clashes == [(CAMSPEED, b"mods\\Two Words", b"lib\\unit.script")]
    assert apply_.clashes == []
    assert (apply_.apply, apply_.box) == (b"1", b"")
    assert apply_.mods[1][1] is False
    assert apply_.stale == [(b"gui\\menu.inc\\oncamera.inc", b"deleted")]
    assert apply_.new == [b"mods\\QMTestNew"]


def test_blocks_map_positions_by_the_load_order_the_boot_logged():
    # qmModList logs canonical positions, qmOrder the load positions after
    # them (plan S11): the replay must use the latter.
    log = b"\r\n".join([
        b"LOG| 1 |[qm] boot version 0.0.0 hook=cameracontrol hookgen=1-2-3",
        b"LOG| 2 |[qm] mod 0 pos=0 on=1 origin=l dir=mods\\QMTestConflict tag=0 ini=5",
        b"LOG| 3 |[qm] mod 1 pos=1 on=1 origin=l dir=mods\\QMTestWASD tag=0 ini=5",
        b"LOG| 4 |[qm] mod 2 pos=2 on=1 origin=s dir=mods\\Quartermaster tag=0 ini=5",
        b"LOG| 5 |[qm] order: mod 1 pos=0 (canonical 1)",
        b"LOG| 6 |[qm] order: mod 0 pos=1 (canonical 0)",
        b"LOG| 7 |[qm] order: src=saved canon=0 ext=0 unseen=0 dropped=0 order.cfg=same"])
    boot, = A.blocks([("0.log", log)])
    dirs, enabled, self_pos = A._view(boot)
    assert dirs == {0: WASD, 1: b"mods\\QMTestConflict", 2: QM}
    assert sorted(enabled) == [0, 1, 2] and self_pos == 2


# ------------------------------------------------------ a run, made up
class FakeRun(object):
    """A run folder the way hrun leaves it, with what the twin says the game
    does: one generation per `gen(...)`, one log per life."""

    def __init__(self, root, fixtures):
        self.root = str(root)
        self.files = A.Files(hbuild.GAME, FIXTURES, hbuild.DIST_MOD)
        self.inp = m4cases.offline_inputs(fixtures)
        self.inp.hooks = dict((n, self.files.hook_file(b"x\\" + n.encode()))
                              for n in os.listdir(os.path.join(hbuild.DIST_MOD, "data",
                                                               "quartermaster", "hooks")))
        self.entries = m4cases.idx_entries()
        self.mirror = self.files.dist_data()
        self.lives = []
        self.last = None
        self.hookgen = self.files.shipped_hookgen()

    def life(self):
        self.lives.append([])

    def put(self, *texts):
        self.lives[-1] += [b"[qm] " + t if not t.startswith(b"QMTEST") else t for t in texts]

    def gen(self, apply_seq=None, dropped=()):
        inp = self.inp
        d = self.inp.dir_of()
        self.put(b"boot version 0.0.0 apply seq=%s" % apply_seq if apply_seq else
                 b"boot version 0.0.0 hook=cameracontrol hookgen=" + self.hookgen)
        for i, m in enumerate(inp.mods):
            self.put(b"mod %d pos=%d on=1 origin=%s dir=%s tag=0 ini=1" % (
                i, inp.pos[i], b"s" if i == inp.self_index else b"l", m.dir))
        for x in dropped:
            self.put(b"order: apply sets on=0 for " + next(v for v in d.values() if v.lower() == x))
        decisions = m4cases.decisions_for(inp, self.entries, dropped)
        self.put(b"fingerprint - lines=7",
                 b"guard plan regen=1 mode=normal why=%s phase=booted" % (
                     b"apply" if apply_seq else b"first"))
        for dd in decisions:
            self.put(b"plan %s %s (%s, %s) winner=%d providers=%s" % (
                dd.path, dd.action, dd.strategy, dd.reason, dd.winner,
                b";".join(b"%d" % p for p in dd.providers)))
        self.put(b"gen start sandbox= decisions=%d merges=0 previous files=0" % len(decisions))
        g = m4cases.run_generation(inp, decisions, m4cases.duplicate_var_oracle, self.mirror)
        for c in g.candidates:
            self.put(b"gen candidate %s %s seq=%d ok=%d" % (c.path, c.tier, c.seq, c.ok))
        for r in g.paths:
            if r.written in (b"yes", b"same"):
                one = r.written == b"yes"
                self.put(b"write %s result=%d before abs=1 dst=1 old=abs:1:- staged=9:%s flag=1 "
                         b"end=1 bytes=1 after abs=2 dst=2 back=%s to x" % (
                             r.path, 1 if one else 2, r.chosen.tok,
                             b"9:" + r.chosen.tok if one else b"-3:-"))
        for s in g.stale:
            self.put(b"gen stale %s %s" % (s.path, s.result))
        self.put(b"gen done status=ok generation=%d outputs hash=%s written=%d same=%d "
                 b"changed=%d failed=%d removed=%d" % (
                     g.gen, g.outhash, sum(r.written == b"yes" for r in g.paths),
                     sum(r.written == b"same" for r in g.paths), g.changed,
                     sum(r.status in (V.FAIL, V.FATAL) for r in g.paths),
                     sum(s.result in (b"deleted", b"overwritten") for s in g.stale)))
        boot = [b"OK The game restarted to load the new files (outputs-changed)."]
        for ln in boot:
            self.put(b"boot report " + ln)
        self.last = (g, inp.dir_of(), inp.enabled(dropped), inp.self_pos,
                     RP.Boot(boot, RP.OK, []))
        self.hookgen = g.outhash
        return g

    def boot_stable(self):
        self.put(b"boot version 0.0.0 hook=cameracontrol hookgen=" + self.hookgen,
                 b"guard plan regen=0 mode=normal why=stable phase=written->booting",
                 b"boot stable gen=1", b"tick: the start reached the main menu; marker booted")

    def write(self, restarts, ini_rows=None):
        os.makedirs(self.root, exist_ok=True)
        for k, lines in enumerate(self.lives):
            with open(os.path.join(self.root, "%d.cos_2609281200%02d.log" % (k, k)), "wb") as fh:
                fh.write(b"".join(b"LOG| %d |%s\r\n" % (n, t) for n, t in enumerate(lines)))
        summary = {"state": "reached", "restarts": restarts, "brick_suspected": False,
                   "sweep": {"ok": True, "problems": [],
                             "mods_trees_checked": {"SW_Frontline_Protocol": 3717}},
                   "dist": hbuild.DIST_MOD}
        with open(os.path.join(self.root, "summary.json"), "w", encoding="utf-8") as fh:
            json.dump(summary, fh)
        rows = ini_rows or [(m.dir, O.FALSE) for m in self.inp.mods]
        # hrun backs these rows up (the player's file) and composes the start
        # in canonical order (--canonical, as m5cases.command asks); the boot
        # keeps that order with Quartermaster last.
        with open(os.path.join(self.root, "mods.ini.backup"), "wb") as fh:
            fh.write(O.render_mods_ini(rows))
        start = [rows[i] for i in O.canonical_indices([d for d, _dis in rows], QM)]
        lo = O.load_order([d for d, _dis in start], QM)
        with open(os.path.join(self.root, "mods.ini.during"), "wb") as fh:
            fh.write(O.render_mods_ini(O.load_rows(start, QM, lo)))
        save = os.path.join(self.root, "qm_save")
        os.makedirs(save, exist_ok=True)
        g, dirs, enabled, self_pos, boot = self.last
        lines = RP.report_lines(g, dirs, enabled, self_pos, boot)
        cf = CF.build(g, dirs, enabled, self_pos, self.inp.read_vanilla, boot)
        with open(os.path.join(save, "report.txt"), "wb") as fh:
            fh.write(RP.report_bytes(lines))
        with open(os.path.join(save, "report.cfg"), "wb") as fh:
            fh.write(RP.report_cfg(RP.qm_report(g, lines, dirs, enabled, self_pos, boot,
                                                window=CF.window(cf))))
        with open(os.path.join(save, "conflicts.txt"), "wb") as fh:
            fh.write(CF.conflicts_bytes(CF.report_lines(cf, g, hbuild.QM_VERSION.encode())))
        for path, data in self.mirror.items():
            full = os.path.join(self.root, A.QM_COPY, "data", *path.decode().split("\\"))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "wb") as fh:
                fh.write(data)
        return self.root


def i2_run(root):
    run = FakeRun(root, ("QMTestWASD", "QMTestCamSpeed"))
    run.life()
    run.gen()
    run.put(b"guard restart=True kind=auto why=outputs-changed", b"restart now kind=auto")
    run.life()
    run.boot_stable()
    run.put(b"QMTEST camspeed registershortcuts", b"QMTEST wasd", b"hooks cc=2 im=4 booted by x")
    return run.write(restarts=1)


def problems_of(run_dir, name="i2"):
    problems, _facts = A.check_run(run_dir, A.by_name(name, expect_broken=[]), A.Files())
    return problems


@needs_fixtures
def test_a_run_as_the_twin_says_passes(tmp_path):
    run_dir = i2_run(tmp_path / "m7i2")
    assert problems_of(run_dir) == []
    said = []
    assert A.main(["check", run_dir, "--scenario", "i2"], echo=said.append) == 0, said
    assert said[-1] == "m7 i2: OK"


def _edit(path, old, new):
    with open(path, "rb") as fh:
        data = fh.read()
    assert old in data, (path, old)
    with open(path, "wb") as fh:
        fh.write(data.replace(old, new, 1))


def _log(run_dir, k):
    return next(os.path.join(run_dir, n) for n in sorted(os.listdir(run_dir))
                if n.startswith("%d.cos_" % k))


@needs_fixtures
@pytest.mark.parametrize("what, change, needle", [
    ("outputs hash", lambda d: _edit(_log(d, 0), b"outputs hash=", b"outputs hash=9"),
     "gen done"),
    ("a token", lambda d: _edit(_log(d, 0), b"back=9:", b"back=9:1"), "write gui"),
    ("a candidate", lambda d: _edit(_log(d, 0), b" merged seq=", b" winner seq="), "candidates"),
    ("the loaded constant", lambda d: _edit(_log(d, 1), b"hookgen=", b"hookgen=0"),
     "loaded CameraControl constant"),
    ("an output", lambda d: _edit(os.path.join(d, A.QM_COPY, "data", "gui", "menu.inc",
                                               "oncamera.inc"), b"[*] = ;", b"[*] =  ;"),
     "oncamera.inc differs"),
    ("a stray file", lambda d: open(os.path.join(d, A.QM_COPY, "data", "stray.inc"), "wb").close(),
     "stray.inc is there"),
    ("the report", lambda d: _edit(os.path.join(d, "qm_save", "report.txt"), b"Files:",
                                   b"Files!"), "report.txt differs"),
    ("the report cfg", lambda d: _edit(os.path.join(d, "qm_save", "report.cfg"), b" = ;", b" = "),
     "report.cfg differs"),
    ("a marker", lambda d: _edit(_log(d, 1), b"QMTEST wasd", b"QMTEST wa"), "QMTEST wasd"),
])
def test_the_checker_names_what_differs(tmp_path, what, change, needle):
    run_dir = i2_run(tmp_path / "m7i2")
    change(run_dir)
    found = problems_of(run_dir)
    assert any(needle in p for p in found), (what, found)


# ----------------------------------------------------------------- I9
def i9_run(root, stale_left=False):
    run = FakeRun(root, ("QMTestWASD", "QMTestCamSpeed"))
    run.life()
    run.gen()
    run.put(b"guard restart=True kind=auto why=outputs-changed",
            b"ui case life|1|wait|regen=1|restart=1", b"restart now kind=auto")
    run.life()
    run.boot_stable()
    row = next(i for i, m in enumerate(run.inp.mods) if m.dir == CAMSPEED)
    run.put(b"QMTEST camspeed registershortcuts", b"QMTEST wasd", b"ui case life|2|go",
            b"ui apply change seq=1 row=%d dis=0->1 dir=%s" % (row, CAMSPEED),
            b"ui case kept|1|1", b"tick: running the Apply of the manager window, seq=1")
    run.gen(apply_seq=b"1", dropped=[CAMSPEED.lower()])
    run.put(b"mods.ini written: 1 of 3 entries changed, effective=1, read back equal",
            b"guard restart=True kind=apply why=outputs-changed", b"restart now kind=apply")
    run.life()
    run.boot_stable()
    run.put(b"QMTEST wasd", b"ui case life|3|later|on=0|why=stable", b"hooks cc=2 im=4 booted by x")
    rows = [(m.dir, O.TRUE if m.dir == CAMSPEED else O.FALSE) for m in run.inp.mods]
    run_dir = run.write(restarts=2, ini_rows=rows)
    out = os.path.join(run_dir, "qm_test_out")
    os.makedirs(out)
    dumps = {1: S.ui_keep_wait(1, 1, 1), 2: S.ui_keep_go(m6cases.TOGGLE, row, 2),
             3: S.ui_keep_later(3, b"0", b"stable")}
    for k, lines in dumps.items():
        with open(os.path.join(out, "qm_case_ui9_%d.txt" % k), "wb") as fh:
            fh.write(S.dump_bytes(lines))
    with open(os.path.join(out, "qm_case_ui9.done"), "wb") as fh:
        fh.write(b"ui|2\r\n")
    with open(os.path.join(out, "done.txt"), "wb") as fh:
        fh.write(S.dump_bytes(S.done_expected([(b"qm_case_ui9.cfg", b"ui"),
                                               (b"qm_m5_restart.cfg", b"m5")])))
    if stale_left:
        with open(os.path.join(run_dir, A.QM_COPY, "data", "gui", "menu.inc", "oncamera.inc"),
                  "wb") as fh:
            fh.write(b"the merged file, left behind\r\n")
    return run_dir


@needs_fixtures
def test_i9_as_the_twin_says_passes_both_checkers(tmp_path):
    run_dir = i9_run(tmp_path / "m7i9")
    assert problems_of(run_dir, "i9") == []
    said = []
    assert m6cases.main(["i9check", run_dir], out=said.append) == 0, said
    assert said[-1] == "ui run I9: OK"
    # The apply's generation deleted the two merged files, and the twin knew.
    rp = A.replay(A._log_bytes(run_dir), A.Files())
    assert [b.apply for b, *_ in rp.gens] == [None, b"1"]
    assert rp.deleted == set(m6cases.MERGED)


@needs_fixtures
def test_i9_catches_a_stale_file_left_behind(tmp_path):
    run_dir = i9_run(tmp_path / "m7i9", stale_left=True)
    found = problems_of(run_dir, "i9")
    assert any("oncamera.inc is there" in p and "deleted as stale" in p for p in found), found
    assert any("still in Quartermaster's folder" in p for p in found), found


@needs_fixtures
def test_i9_catches_camspeed_left_on(tmp_path):
    run_dir = i9_run(tmp_path / "m7i9")
    during = os.path.join(run_dir, "mods.ini.during")
    _edit(during, b"QMTestCamSpeed\r\n         dis = True", b"QMTestCamSpeed\r\n         dis = False")
    found = problems_of(run_dir, "i9")
    assert any("must be off" in p for p in found), found


# ------------------------------------------------------- scenario rules
def test_the_conflict_rule_wants_one_conflict_the_later_mod_wins(tmp_path):
    save = tmp_path / "qm_save"
    save.mkdir()
    good = (b"  conflict: vanilla line 18 of 2. mods\\QMTestConflict lost to "
            b"3. mods\\QMTestWASD\r\n")
    (save / "report.txt").write_bytes(b"x\r\n" + good)
    assert A._conflict_rules(str(tmp_path), None) == []
    (save / "report.txt").write_bytes(b"x\r\n" + good + good)
    assert A._conflict_rules(str(tmp_path), None)
    (save / "report.txt").write_bytes(good.replace(b"QMTestWASD", b"QMTestOther"))
    assert A._conflict_rules(str(tmp_path), None)
    # The report names a mod by its title with the dir beside it (2026-09-30);
    # the rule goes by the dirs, on the right sides of `lost to`.
    titled = (b"  conflict: vanilla line 18 of 1. QMTestConflict (mods\\QMTestConflict) lost "
              b"to 2. QMTestWASD (mods\\QMTestWASD)\r\n")
    (save / "report.txt").write_bytes(b"x\r\n" + titled)
    assert A._conflict_rules(str(tmp_path), None) == []
    assert A._reorder_rules(str(tmp_path), None)
    swapped = (b"  conflict: vanilla lines 18-21 of 1. QMTestWASD (mods\\QMTestWASD) lost to "
               b"2. QMTestConflict (mods\\QMTestConflict)\r\n")
    (save / "report.txt").write_bytes(b"x\r\n" + swapped + b"  OK Multiplayer: every player "
                                      b"needs the same mods in the same load order.\r\n")
    assert A._reorder_rules(str(tmp_path), None) == []
    assert A._conflict_rules(str(tmp_path), None)


def test_the_broken_rule_wants_the_fail_and_both_candidates(tmp_path):
    save = tmp_path / "qm_save"
    save.mkdir()
    text = [b"FAIL gui\\menu.inc\\registershortcuts.inc", b"  candidate merged: does not compile",
            b"  candidate winner: compiles"]
    (save / "report.txt").write_bytes(b"\r\n".join(text) + b"\r\n")
    assert A._broken_rules(str(tmp_path), None) == []
    (save / "report.txt").write_bytes(b"\r\n".join(text[:2]) + b"\r\n")
    assert A._broken_rules(str(tmp_path), None)


def test_the_vanilla_rules_want_the_menu_and_the_swfp_comparison(tmp_path):
    log = b"TIM| 8 |...InitMap finished...\r\nTIM| 12 |...InitMap finished...\r\n"
    (tmp_path / "0.cos_1.log").write_bytes(log)
    (tmp_path / "summary.json").write_text(json.dumps(
        {"sweep": {"mods_trees_checked": {"SW_Frontline_Protocol": 3717}}}))
    assert A._vanilla_rules(str(tmp_path), None) == []
    (tmp_path / "0.cos_1.log").write_bytes(log.split(b"\r\n")[0] + b"\r\n")
    (tmp_path / "summary.json").write_text(json.dumps({"sweep": {}}))
    assert len(A._vanilla_rules(str(tmp_path), None)) == 2


def test_a_run_without_quartermaster_that_reached_its_last_line_is_complete(tmp_path):
    (tmp_path / "0.cos_1.log").write_bytes(
        b"LOG| 7 |...DoCreate started...\r\nTIM| 8 |...InitMap finished...\r\n" * 2
        + b"LOG| 15 | :: STEAM CALLBACK :: SteamwrapGetNumAchievements()=103\r\n")
    summary = {"state": "reached", "restarts": 0, "brick_suspected": False,
               "sweep": {"ok": True, "problems": [],
                         "mods_trees_checked": {"SW_Frontline_Protocol": 1}}}
    (tmp_path / "summary.json").write_text(json.dumps(summary))
    said = []
    assert A.main(["check", str(tmp_path), "--scenario", "vanilla"], echo=said.append) == 0, said
    # Since 2026-10-05 a timeout is no longer the expected end.
    (tmp_path / "summary.json").write_text(json.dumps(dict(summary, state="timeout")))
    assert A.main(["check", str(tmp_path), "--scenario", "vanilla"], echo=lambda s: None) == 1
    (tmp_path / "summary.json").write_text(json.dumps(summary))
    (tmp_path / "0.cos_1.log").write_bytes(b"LOG| 9 |[qm] boot version 0.0.0 hook=x\r\n")
    assert A.main(["check", str(tmp_path), "--scenario", "vanilla"], echo=lambda s: None) == 1
