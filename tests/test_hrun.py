"""Offline gates for tools/hrun.py.

Everything runs against a fake game folder and a fake save folder under
tmp_path. The process table and the launch are a `FakeGame`; an autouse fixture
makes any real tasklist, launch or taskkill fail the test instead of running.
"""
import hashlib
import json
import os
from types import SimpleNamespace

import pytest

import hbuild
import hrun
from ref import order

# Every byte a text-mode round trip would change: a tab, a trailing space, a bare
# LF, a lone CR, bytes above 127 (0x81 does not even decode as cp1252), and no
# final CRLF. Only a binary copy restores this.
ODD_MODS_INI = (b"section.begin\r\n   mods : struct.begin\r\n\t[*] : struct.begin \r\n"
                b"         dir = mods\\SW_Frontline_Protocol\n         dis = True\r"
                b"      struct.end\r\n   // \xb3\x81\r\n   struct.end\r\nsection.end")


@pytest.fixture(autouse=True)
def no_real_processes(monkeypatch):
    def forbidden(*_a, **_k):
        raise AssertionError("a test reached the real process table")

    class NoSystem(object):
        def __init__(self):
            forbidden()

    monkeypatch.setattr(hrun, "System", NoSystem)
    monkeypatch.setattr(hbuild, "running_images", forbidden)
    monkeypatch.delenv(hrun.LOGS_ENV, raising=False)


class FakeGame(object):
    """cossacks.exe as the harness sees it: an image name, logs and mods.ini.

    Each life writes one cos_*.log. Like the engine it rewrites mods.ini on start,
    registering every folder in mods\\ it did not list. A life other than the
    last ends by itself after `life_s` (Quartermaster's restart) and the next
    starts `gap_s` later.
    """

    def __init__(self, w, lives, life_s=10.0, gap_s=4.0, running=(), on_launch=None,
                 on_sleep=None):
        self.w = w
        self.lives = lives
        self.life_s, self.gap_s = life_s, gap_s
        self.extra = set(running)
        self.on_launch, self.on_sleep = on_launch, on_sleep
        self.t = 1000.0
        self.alive = False
        self.life = -1
        self.gone_at = None
        self.launched = []
        self.killed = []
        self.listing_at_launch = None
        self.ini_during = None

    def running(self):
        return set(self.extra) | ({"cossacks.exe"} if self.alive else set())

    def launch(self, exe, cwd):
        assert os.path.basename(exe) in hbuild.GAME_IMAGES and cwd == self.w.game
        self.launched.append(exe)
        self.listing_at_launch = sorted(os.listdir(os.path.join(self.w.game, "mods")))
        if self.on_launch:
            self.on_launch(self)
        self._start(0)

    def _start(self, i):
        self.life, self.alive, self.started = i, True, self.t
        ini = os.path.join(self.w.game, "mods", "mods.ini")
        with open(ini, "rb") as fh:
            data = fh.read()
        for name in sorted(os.listdir(os.path.join(self.w.game, "mods"))):
            if os.path.isdir(os.path.join(self.w.game, "mods", name)) and name.encode() not in data:
                data += (b"\r\n      [*] : struct.begin\r\n         dir = mods\\%s\r\n"
                         b"         dis = False\r\n      struct.end" % name.encode())
        with open(ini, "wb") as fh:
            fh.write(data)
        self.ini_during = data
        log = os.path.join(self.w.save, "log", "cos_260928_1000%02d.log" % i)
        with open(log, "wb") as fh:
            fh.write(b"".join(line.encode("latin-1") + b"\r\n" for line in self.lives[i]))

    def sleep(self, seconds):
        self.t += seconds
        if self.on_sleep:
            self.on_sleep(self)
        if self.alive and self.life < len(self.lives) - 1 and self.t - self.started >= self.life_s:
            self.alive, self.gone_at = False, self.t
        if (not self.alive and self.gone_at is not None and self.life < len(self.lives) - 1
                and self.t - self.gone_at >= self.gap_s):
            self._start(self.life + 1)

    def kill(self, image):
        self.killed.append(image)
        if image == "cossacks.exe":
            self.alive = False
            self.gone_at = None
            self.lives = self.lives[:self.life + 1]
        self.extra.discard(image)

    def now(self):
        return self.t


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)


@pytest.fixture
def w(tmp_path):
    game = tmp_path / "game"
    save = tmp_path / "save"
    ns = SimpleNamespace(root=str(tmp_path), game=str(game), save=str(save),
                         dist=str(tmp_path / "dist" / "Quartermaster"),
                         fixtures=str(tmp_path / "fixtures"), logs=str(tmp_path / "logs"))
    write(os.path.join(ns.game, "cossacks.exe"), b"MZ")
    write(os.path.join(ns.game, "modman.exe"), b"MZ")
    write(os.path.join(ns.game, "mods", "mods.ini"), ODD_MODS_INI)
    write(os.path.join(ns.game, "mods", "SW_Frontline_Protocol", "mod.ini"), b"swfp\r\n")
    for rel in ("gui/menu.inc/cameracontrol.inc", "gui/menu.inc/doprogress.inc",
                "gui/menu.inc/docreate.inc", "gui/common.inc/a.inc", "scripts/units/unit.inc/x.inc",
                "scripts/common.inc/initmap.inc", "gui/menu.aix", "game/var/objcustom.cfg"):
        write(os.path.join(ns.game, "data", *rel.split("/")), b"%s\r\n" % rel.encode())
    write(os.path.join(ns.save, "log", "cos_260927_120000.log"), b"LOG| 1 |old run\r\n")
    write(os.path.join(ns.dist, "mod.ini"), hbuild.mod_ini())
    write(os.path.join(ns.dist, "data", "quartermaster", "core.aix"), b"x\r\n")
    write(os.path.join(ns.fixtures, "QMTestWASD", "data", "gui", "menu.inc", "oncamera.inc"),
          b"wasd\r\n")
    write(os.path.join(ns.root, "case1.cfg"), b"case bytes\r\n\x00\xff")
    return ns


def options(w, **kw):
    base = dict(game_dir=w.game, save_dir=w.save, dist_mod=w.dist, fixtures_dir=w.fixtures,
                logs_dir=w.logs, run_id="t1", poll=2.0, settle=1.0, startup_grace=30.0,
                exit_grace=10.0, timeout=120.0)
    base.update(kw)
    return hrun.Options(**base)


def snapshot(root):
    out = {}
    for dirpath, dirs, files in os.walk(root):
        for d in dirs:
            out[os.path.relpath(os.path.join(dirpath, d), root)] = "dir"
        for f in files:
            with open(os.path.join(dirpath, f), "rb") as fh:
                out[os.path.relpath(os.path.join(dirpath, f), root)] = hashlib.sha256(fh.read()).hexdigest()
    return out


def mods(w):
    return sorted(os.listdir(os.path.join(w.game, "mods")))


def ini_bytes(w):
    with open(os.path.join(w.game, "mods", "mods.ini"), "rb") as fh:
        return fh.read()


def lock(w):
    return os.path.join(w.save, hbuild.LOCK_NAME)


def journal(w):
    return os.path.join(w.logs, hrun.JOURNAL_NAME)


BOOTS = [["LOG|  7 |...DoCreate started..."],
         ["LOG|  7 |...DoCreate started...", "LOG|  9 |[qm] booted gen=1"]]


# ------------------------------------------------------------ full cycle
def test_full_cycle_follows_a_restart_and_puts_everything_back(w):
    game = FakeGame(w, BOOTS)
    lines = []
    code, summary = hrun.run(options(w, fixtures=["QMTestWASD"],
                                     cases=[os.path.join(w.root, "case1.cfg")]),
                             game, lines.append)
    assert code == 0, "\n".join(lines)
    # During the run: both folders deployed, the engine rewrote mods.ini.
    assert game.listing_at_launch == ["QMTestWASD", "Quartermaster", "SW_Frontline_Protocol",
                                      "mods.ini"]
    assert b"mods\\Quartermaster" in game.ini_during and game.ini_during != ODD_MODS_INI
    # The marker was only in the second life's log: the wait spanned the restart.
    assert summary["state"] == "reached" and summary["restarts"] == 1
    assert summary["boot_seen"] and not summary["brick_suspected"]
    assert [os.path.basename(p) for p in summary["logs"]] == ["0.cos_260928_100000.log",
                                                              "1.cos_260928_100001.log"]
    assert game.killed == ["cossacks.exe"]
    # Afterwards: byte-identical mods.ini, same listing, nothing of ours left.
    assert ini_bytes(w) == ODD_MODS_INI
    assert mods(w) == ["SW_Frontline_Protocol", "mods.ini"]
    assert summary["sweep"]["ok"] and "SWEEP OK" in lines
    assert not os.path.exists(lock(w)) and not os.path.exists(journal(w))
    assert not os.path.exists(os.path.join(w.save, "qm_autotest.cfg"))
    assert not os.path.exists(os.path.join(w.save, "qm_test"))
    run_dir = os.path.join(w.logs, "t1")
    with open(os.path.join(run_dir, "summary.json"), encoding="utf-8") as fh:
        assert json.load(fh)["sweep"]["ok"] is True
    with open(os.path.join(run_dir, "mods.ini.backup"), "rb") as fh:
        assert fh.read() == ODD_MODS_INI


def test_case_files_arrive_verbatim_during_the_run(w):
    seen = {}

    def look(game):
        cfg = os.path.join(w.save, "qm_autotest.cfg")
        case = os.path.join(w.save, "qm_test", "cases", "case1.cfg")
        with open(case, "rb") as fh:
            seen["case"] = fh.read()
        seen["cfg"] = os.path.getsize(cfg)

    code, _ = hrun.run(options(w, cases=[os.path.join(w.root, "case1.cfg")]),
                       FakeGame(w, BOOTS[1:], on_launch=look), lambda *_: None)
    assert code == 0
    assert seen == {"case": b"case bytes\r\n\x00\xff", "cfg": 0}


def test_selftest_results_are_collected_then_removed(w):
    def selftest(game):
        # What the game's SelfTest does: write its results under qm_test\out.
        write(os.path.join(w.save, "qm_test", "out", "done.txt"), b"done|1|0\r\n")
        write(os.path.join(w.save, "qm_test", "out", "qm_case1.txt"), b"raw|x\r\n")

    lines = []
    code, summary = hrun.run(options(w, cases=[os.path.join(w.root, "case1.cfg")]),
                             FakeGame(w, BOOTS[1:], on_launch=selftest), lines.append)
    assert code == 0, "\n".join(lines)
    copy = os.path.join(w.logs, "t1", hrun.SELFTEST_COPY)
    with open(os.path.join(copy, "done.txt"), "rb") as fh:
        assert fh.read() == b"done|1|0\r\n"
    assert sorted(os.path.basename(p) for p in summary["selftest_out"]) == [
        "done.txt", "qm_case1.txt"]
    # Nothing of the run is left in the save folder.
    assert not os.path.exists(os.path.join(w.save, "qm_test"))
    assert not os.path.exists(os.path.join(w.save, "qm_autotest.cfg"))


def test_stale_selftest_results_refuse_the_run(w):
    write(os.path.join(w.save, "qm_test", "out", "done.txt"), b"old\r\n")
    lines = []
    code, _ = hrun.run(options(w, cases=[os.path.join(w.root, "case1.cfg")]),
                       FakeGame(w, BOOTS), lines.append)
    assert code == 2
    assert any("qm_test" in l and "earlier SelfTest" in l for l in lines)
    with open(os.path.join(w.save, "qm_test", "out", "done.txt"), "rb") as fh:
        assert fh.read() == b"old\r\n"


# ----------------------------------------------------------------- dry run
def test_dry_run_prints_the_full_plan_and_touches_nothing(w):
    before = snapshot(w.root)
    lines = []
    code, summary = hrun.run(options(w, dry_run=True, fixtures=["QMTestWASD"],
                                     cases=[os.path.join(w.root, "case1.cfg")]),
                             FakeGame(w, BOOTS), lines.append)
    assert code == 0 and summary is None
    text = "\n".join(lines)
    for step in ("preflight", "lock", "baseline", "backup", "journal", "deploy", "cases",
                 "launch", "wait", "kill", "collect", "undeploy", "restore", "cleanup",
                 "sweep", "unlock"):
        assert " %s " % step in text, step
    assert "QMTestWASD" in text and "case1.cfg" in text
    assert snapshot(w.root) == before


def test_dry_run_reports_what_it_would_refuse(w):
    write(lock(w), b"SWFP session")
    lines = []
    code, _ = hrun.run(options(w, dry_run=True), FakeGame(w, BOOTS, running={"modman.exe"}),
                       lines.append)
    assert code == 2
    assert any("would refuse" in l and "modman.exe" in l for l in lines)
    assert any("would refuse" in l and "lock" in l for l in lines)


# ---------------------------------------------------------------- refusals
def test_a_preexisting_lock_refuses_the_run_and_stays(w):
    write(lock(w), b"SWFP session 2026-09-28")
    before = snapshot(w.root)
    game = FakeGame(w, BOOTS)
    code, _ = hrun.run(options(w), game, lambda *_: None)
    assert code == 2 and game.launched == []
    assert snapshot(w.root) == before


@pytest.mark.parametrize("image", ["cossacks.exe", "modman.exe"])
def test_a_running_game_refuses_the_run(w, image):
    before = snapshot(w.root)
    game = FakeGame(w, BOOTS, running={image})
    lines = []
    code, _ = hrun.run(options(w), game, lines.append)
    assert code == 2 and game.launched == [] and game.killed == []
    assert any(image in l for l in lines)
    assert snapshot(w.root) == before


def test_a_real_run_needs_a_logs_dir(w):
    code, _ = hrun.run(options(w, logs_dir=None), FakeGame(w, BOOTS), lambda *_: None)
    assert code == 2 and not os.path.exists(lock(w))


def test_a_folder_already_in_mods_is_never_overwritten(w):
    os.makedirs(os.path.join(w.game, "mods", "QMTestWASD"))
    code, _ = hrun.run(options(w, fixtures=["QMTestWASD"]), FakeGame(w, BOOTS), lambda *_: None)
    assert code == 2 and not os.path.exists(lock(w))
    assert mods(w) == ["QMTestWASD", "SW_Frontline_Protocol", "mods.ini"]


# ------------------------------------------------------------------- sweep
def test_sweep_fails_on_a_folder_left_in_mods(w):
    def stray(_game):
        os.makedirs(os.path.join(w.game, "mods", "Stray"))

    lines = []
    code, summary = hrun.run(options(w), FakeGame(w, BOOTS[1:], on_launch=stray), lines.append)
    assert code == 1
    assert "SWEEP FAILED" in lines and not summary["sweep"]["ok"]
    assert summary["sweep"]["problems"] == ["mods\\Stray/ is new"]
    # hrun removes only what it created; the stray folder is reported, not deleted.
    assert mods(w) == ["SW_Frontline_Protocol", "Stray", "mods.ini"]
    assert ini_bytes(w) == ODD_MODS_INI
    assert not os.path.exists(lock(w)) and not os.path.exists(journal(w))


def test_sweep_fails_when_vanilla_data_changes(w):
    def scribble(_game):
        write(os.path.join(w.game, "data", "gui", "menu.inc", "cameracontrol.inc"), b"changed")

    code, summary = hrun.run(options(w), FakeGame(w, BOOTS[1:], on_launch=scribble),
                             lambda *_: None)
    assert code == 1
    assert summary["sweep"]["problems"] == ["vanilla data\\gui\\menu.inc\\cameracontrol.inc changed"]


def test_sweep_fails_when_a_mod_that_was_there_changes(w):
    def touch_swfp(_game):
        write(os.path.join(w.game, "mods", "SW_Frontline_Protocol", "data", "new.inc"), b"x")

    lines = []
    code, summary = hrun.run(options(w), FakeGame(w, BOOTS[1:], on_launch=touch_swfp),
                             lines.append)
    assert code == 1 and "SWEEP FAILED" in lines
    assert summary["sweep"]["problems"] == [
        "mods\\SW_Frontline_Protocol changed: 1 file(s), first data\\new.inc"]
    # Reported, never repaired: hrun does not touch a folder it did not create.
    assert os.path.isfile(os.path.join(w.game, "mods", "SW_Frontline_Protocol", "data", "new.inc"))


def test_a_mods_own_tooling_is_not_what_the_sweep_compares(w):
    """Only what the engine reads from a mod folder: another session may work
    in a mod's own working copy (its .git, tools, docs) while a run waits."""
    def work_in_swfp(_game):
        write(os.path.join(w.game, "mods", "SW_Frontline_Protocol", ".git", "index"), b"i")
        write(os.path.join(w.game, "mods", "SW_Frontline_Protocol", "tools", "x.py"), b"x")

    code, summary = hrun.run(options(w), FakeGame(w, BOOTS[1:], on_launch=work_in_swfp),
                             lambda *_: None)
    assert code == 0 and summary["sweep"]["ok"]


def test_the_baseline_lists_the_files_of_the_mods_already_there(w):
    base = hrun.capture_baseline(w.game)
    assert list(base["mods_trees"]) == ["SW_Frontline_Protocol"]
    assert list(base["mods_trees"]["SW_Frontline_Protocol"]) == ["mod.ini"]
    size, _mtime = base["mods_trees"]["SW_Frontline_Protocol"]["mod.ini"]
    assert size == len(b"swfp\r\n")
    code, summary = hrun.run(options(w), FakeGame(w, BOOTS[1:]), lambda *_: None)
    assert code == 0 and summary["sweep"]["mods_trees_checked"] == {"SW_Frontline_Protocol": 1}


def test_what_quartermaster_generated_in_its_folder_is_collected(w):
    def generate(_game):
        write(os.path.join(w.game, "mods", "Quartermaster", "data", "gui", "menu.inc",
                           "oncamera.inc"), b"merged\r\n")

    lines = []
    code, summary = hrun.run(options(w, fixtures=["QMTestWASD"]),
                             FakeGame(w, BOOTS[1:], on_launch=generate), lines.append)
    assert code == 0, "\n".join(lines)
    copy = os.path.join(w.logs, "t1", hrun.QM_COPY)
    assert summary["quartermaster_copy"] == copy
    with open(os.path.join(copy, "data", "gui", "menu.inc", "oncamera.inc"), "rb") as fh:
        assert fh.read() == b"merged\r\n"
    with open(os.path.join(copy, "data", "quartermaster", "core.aix"), "rb") as fh:
        assert fh.read() == b"x\r\n"
    # The fixture is not copied, and the game folder ends as it began.
    assert not os.path.exists(os.path.join(w.logs, "t1", "QMTestWASD"))
    assert mods(w) == ["SW_Frontline_Protocol", "mods.ini"] and summary["sweep"]["ok"]


def test_nothing_is_collected_from_mods_without_quartermaster(w):
    code, summary = hrun.run(options(w, quartermaster=False, until="DoCreate"),
                             FakeGame(w, BOOTS[:1]), lambda *_: None)
    assert code == 0 and summary["quartermaster_copy"] is None
    assert not os.path.exists(os.path.join(w.logs, "t1", hrun.QM_COPY))


def test_the_manifest_covers_hooks_and_the_merge_allow_list_only(w):
    assert hrun.touchable_files(w.game) == ["gui/common.inc/a.inc",
                                            "gui/menu.inc/cameracontrol.inc",
                                            "gui/menu.inc/doprogress.inc",
                                            "scripts/units/unit.inc/x.inc"]


# ------------------------------------------------------------------- bricks
def test_a_brick_line_ends_the_wait_and_is_reported(w):
    lives = [["LOG|  6 |...DoCreate started...", "ERROR|  7 |Compile script error: DoCreate"]]
    code, summary = hrun.run(options(w), FakeGame(w, lives), lambda *_: None)
    assert code == 1
    assert summary["state"] == "brick" and summary["brick_suspected"]
    assert "ERROR|  7 |Compile script error: DoCreate" in summary["brick_lines"]
    assert summary["sweep"]["ok"] and ini_bytes(w) == ODD_MODS_INI


def test_an_expected_validation_compile_error_is_not_a_brick(w):
    lives = [["ERROR|  5 |Compile script error: qmValProbe", "LOG|  6 |[qm] validated"]]
    code, summary = hrun.run(options(w, expect_compile_errors=["qmValProbe"]),
                             FakeGame(w, lives), lambda *_: None)
    assert code == 0 and not summary["brick_suspected"]


def test_no_boot_line_is_a_suspected_brick(w):
    lives = [["LOG|  7 |...DoCreate started..."]]
    code, summary = hrun.run(options(w, timeout=40.0), FakeGame(w, lives), lambda *_: None)
    assert code == 1 and summary["state"] == "timeout"
    assert summary["brick_suspected"]
    assert summary["brick_lines"] == ["no '[qm]' line before the wait ended"]
    assert summary["sweep"]["ok"]


def test_the_wait_ends_when_the_game_is_gone(w):
    game = FakeGame(w, [["LOG| 1 |a"], ["LOG| 1 |b"]], life_s=5.0, gap_s=10000.0)
    code, summary = hrun.run(options(w, quartermaster=False), game, lambda *_: None)
    assert summary["state"] == "game exited" and summary["elapsed_s"] < 120
    assert code == 0 and not summary["brick_suspected"]


# ------------------------------------------------------------ crash, recover
class Died(BaseException):
    """The harness process is killed: no `finally` of its own ever finishes."""


def test_a_crashed_run_is_undone_by_recover(w, monkeypatch):
    game = FakeGame(w, BOOTS)

    def die(*_a, **_k):
        raise Died()

    monkeypatch.setattr(hrun, "finish", die)
    with pytest.raises(Died):
        hrun.run(options(w, fixtures=["QMTestWASD"], cases=[os.path.join(w.root, "case1.cfg")]),
                 game, lambda *_: None)
    monkeypatch.undo()
    monkeypatch.setattr(hrun, "System", None)
    monkeypatch.setattr(hbuild, "running_images", None)
    # The wreck: our lock, the journal, both folders, the engine's mods.ini.
    assert hrun.read_lock(lock(w)) is not None and os.path.isfile(journal(w))
    assert "Quartermaster" in mods(w) and "QMTestWASD" in mods(w)
    assert ini_bytes(w) != ODD_MODS_INI
    # A new run refuses while the wreck is there.
    code, _ = hrun.run(options(w, run_id="t2"), FakeGame(w, BOOTS), lambda *_: None)
    assert code == 2
    # Recovery refuses while the game still runs.
    lines = []
    assert hrun.recover(options(w, logs_dir=None), game, lines.append) == 2
    assert any("close the game" in l for l in lines)
    game.kill("cossacks.exe")
    # The lock names the journal, so --recover finds it without --logs-dir.
    lines = []
    assert hrun.recover(options(w, logs_dir=None), game, lines.append) == 0, "\n".join(lines)
    assert "SWEEP OK" in lines
    assert ini_bytes(w) == ODD_MODS_INI
    assert mods(w) == ["SW_Frontline_Protocol", "mods.ini"]
    assert not os.path.exists(lock(w)) and not os.path.exists(journal(w))
    assert not os.path.exists(os.path.join(w.save, "qm_autotest.cfg"))
    assert os.path.isfile(os.path.join(w.logs, "t1", "recover.json"))


def test_the_lock_names_an_absolute_journal_even_for_a_relative_logs_dir(w, monkeypatch):
    monkeypatch.chdir(w.root)
    game = FakeGame(w, BOOTS)
    monkeypatch.setattr(hrun, "finish", lambda *_a, **_k: (_ for _ in ()).throw(Died()))
    with pytest.raises(Died):
        hrun.run(options(w, logs_dir="logs"), game, lambda *_: None)
    held = hrun.read_lock(lock(w))
    assert os.path.isabs(held["journal"]) and os.path.isfile(held["journal"])
    monkeypatch.chdir(w.save)
    game.kill("cossacks.exe")
    assert hrun.recover(options(w, logs_dir=None), game, lambda *_: None) == 0
    assert ini_bytes(w) == ODD_MODS_INI


def test_recover_through_the_cli(w, monkeypatch):
    game = FakeGame(w, BOOTS)
    monkeypatch.setattr(hrun, "finish", lambda *_a, **_k: (_ for _ in ()).throw(Died()))
    with pytest.raises(Died):
        hrun.run(options(w), game, lambda *_: None)
    game.kill("cossacks.exe")
    lines = []
    assert hrun.main(["--recover", "--game-dir", w.game, "--save-dir", w.save,
                      "--logs-dir", w.logs], system=game, out=lines.append) == 0
    assert ini_bytes(w) == ODD_MODS_INI and mods(w) == ["SW_Frontline_Protocol", "mods.ini"]


def test_recover_with_nothing_to_do_leaves_a_foreign_lock_alone(w):
    write(lock(w), b"SWFP session")
    assert hrun.recover(options(w), FakeGame(w, BOOTS), lambda *_: None) == 0
    with open(lock(w), "rb") as fh:
        assert fh.read() == b"SWFP session"


def test_recover_removes_our_lock_when_the_run_died_before_its_journal(w):
    hrun.take_lock(lock(w), "t9:1:x", os.path.join(w.logs, hrun.JOURNAL_NAME))
    assert hrun.recover(options(w), FakeGame(w, BOOTS), lambda *_: None) == 0
    assert not os.path.exists(lock(w))


def test_undeploy_never_removes_a_folder_that_was_there_before(w):
    j = hrun.Journal(journal(w), {"game_dir": w.game, "baseline": {
        "mods_listing": ["SW_Frontline_Protocol/", "mods.ini"]}})
    lines = []
    assert hrun.remove_deployed(j, "SW_Frontline_Protocol", lines.append) is False
    assert "SW_Frontline_Protocol" in mods(w) and "REFUSED" in lines[0]
    with pytest.raises(hbuild.DeployError):
        hrun.remove_deployed(j, "..\\game", lines.append)


# ------------------------------------------------------------------- the lock
def test_the_lock_is_exclusive_and_removed_only_when_ours(w):
    path = lock(w)
    hrun.take_lock(path, "a", "j")
    with pytest.raises(FileExistsError):
        hrun.take_lock(path, "b", "j")
    assert hrun.release_lock(path, "b") is False and os.path.exists(path)
    assert hrun.release_lock(path, "a") is True and not os.path.exists(path)


def test_a_lock_replaced_mid_run_is_not_removed(w):
    def steal(game):
        if game.t > 1003 and os.path.exists(lock(w)):
            with open(lock(w), "wb") as fh:
                fh.write(b"another session")

    code, summary = hrun.run(options(w), FakeGame(w, BOOTS, on_sleep=steal), lambda *_: None)
    assert summary["lock_released"] is False
    with open(lock(w), "rb") as fh:
        assert fh.read() == b"another session"


# ------------------------------------------------------------ keep deployed
def test_keep_deployed_leaves_the_folders_and_says_how_to_remove_them(w):
    lines = []
    code, summary = hrun.run(options(w, fixtures=["QMTestWASD"], keep_deployed=True),
                             FakeGame(w, BOOTS[1:]), lines.append)
    assert code == 0 and summary["sweep"]["ok"]
    assert summary["kept_deployed"] == ["Quartermaster", "QMTestWASD"]
    assert mods(w) == ["QMTestWASD", "Quartermaster", "SW_Frontline_Protocol", "mods.ini"]
    assert ini_bytes(w) == ODD_MODS_INI
    text = "\n".join(lines)
    assert "python tools/hbuild.py --undeploy" in text
    assert 'rmdir /S /Q "%s"' % os.path.join(w.game, "mods", "QMTestWASD") in text
    assert not os.path.exists(journal(w)) and not os.path.exists(lock(w))


def test_launching_modman_kills_modman_too(w):
    game = FakeGame(w, BOOTS[1:])
    code, _ = hrun.run(options(w, launch="modman.exe"), game, lambda *_: None)
    assert code == 0 and game.killed == ["cossacks.exe", "modman.exe"]


def test_recover_collects_and_removes_the_selftest_output(w, monkeypatch):
    def selftest(game):
        write(os.path.join(w.save, "qm_test", "out", "done.txt"), b"done|0|0\r\n")

    def die(*_a, **_k):
        raise Died()

    monkeypatch.setattr(hrun, "finish", die)
    with pytest.raises(Died):
        hrun.run(options(w, cases=[os.path.join(w.root, "case1.cfg")]),
                 FakeGame(w, BOOTS[1:], on_launch=selftest), lambda *_: None)
    monkeypatch.undo()
    monkeypatch.setattr(hrun, "System", None)
    monkeypatch.setattr(hbuild, "running_images", None)
    game = FakeGame(w, BOOTS)
    lines = []
    assert hrun.recover(options(w, logs_dir=None), game, lines.append) == 0, "\n".join(lines)
    with open(os.path.join(w.logs, "t1", hrun.SELFTEST_COPY, "done.txt"), "rb") as fh:
        assert fh.read() == b"done|0|0\r\n"
    assert not os.path.exists(os.path.join(w.save, "qm_test"))


# ------------------------------------------- <save>\quartermaster and lives
def qm_state(w, *parts):
    return os.path.join(w.save, hrun.STATE_DIR, *parts)


def test_the_players_state_folder_is_moved_aside_and_put_back(w):
    write(qm_state(w, "state.cfg"), b"the player's marker\r\n")
    write(qm_state(w, "val", "0.aix"), b"old candidate\r\n")
    before = snapshot(os.path.join(w.save, hrun.STATE_DIR))
    seen = {}

    def boot(game):
        # The run starts without it; the game makes its own.
        seen["at_launch"] = os.path.exists(qm_state(w))
        write(qm_state(w, "state.cfg"), b"this run's marker\r\n")

    lines = []
    code, summary = hrun.run(options(w), FakeGame(w, BOOTS[1:], on_launch=boot), lines.append)
    assert code == 0, "\n".join(lines)
    assert seen == {"at_launch": False}
    assert snapshot(os.path.join(w.save, hrun.STATE_DIR)) == before
    assert not os.path.exists(os.path.join(w.save, hrun.STATE_ASIDE))
    with open(os.path.join(summary["state_copy"], "state.cfg"), "rb") as fh:
        assert fh.read() == b"this run's marker\r\n"
    assert summary["sweep"]["ok"]


def test_a_state_seed_is_what_the_game_finds_and_the_run_leaves_nothing(w):
    seed = os.path.join(w.root, "seed")
    write(os.path.join(seed, "known.cfg"), b"known\r\n")
    seen = {}

    def boot(game):
        with open(qm_state(w, "known.cfg"), "rb") as fh:
            seen["known"] = fh.read()

    code, summary = hrun.run(options(w, state=seed), FakeGame(w, BOOTS[1:], on_launch=boot),
                             lambda *_: None)
    assert code == 0 and seen == {"known": b"known\r\n"}
    assert not os.path.exists(qm_state(w))            # there was none before
    assert summary["state_seed"] == seed and summary["sweep"]["ok"]


def test_a_leftover_aside_folder_refuses_the_run(w):
    write(os.path.join(w.save, hrun.STATE_ASIDE, "state.cfg"), b"x")
    lines = []
    code, _ = hrun.run(options(w), FakeGame(w, BOOTS), lines.append)
    assert code == 2 and any("--recover" in l and hrun.STATE_ASIDE in l for l in lines)


def test_a_missing_seed_refuses_the_run(w):
    lines = []
    code, _ = hrun.run(options(w, state=os.path.join(w.root, "nope")), FakeGame(w, BOOTS),
                       lines.append)
    assert code == 2 and any("--state" in l for l in lines)


def test_recover_puts_the_state_folder_back(w, monkeypatch):
    write(qm_state(w, "state.cfg"), b"the player's marker\r\n")

    def boot(game):
        write(qm_state(w, "state.cfg"), b"this run's marker\r\n")

    def die(*_a, **_k):
        raise Died()

    monkeypatch.setattr(hrun, "finish", die)
    with pytest.raises(Died):
        hrun.run(options(w), FakeGame(w, BOOTS[1:], on_launch=boot), lambda *_: None)
    monkeypatch.undo()
    monkeypatch.setattr(hrun, "System", None)
    monkeypatch.setattr(hbuild, "running_images", None)
    assert os.path.isdir(os.path.join(w.save, hrun.STATE_ASIDE))
    lines = []
    assert hrun.recover(options(w, logs_dir=None), FakeGame(w, BOOTS), lines.append) == 0, \
        "\n".join(lines)
    with open(qm_state(w, "state.cfg"), "rb") as fh:
        assert fh.read() == b"the player's marker\r\n"
    assert not os.path.exists(os.path.join(w.save, hrun.STATE_ASIDE))
    with open(os.path.join(w.logs, "t1", hrun.STATE_COPY, "state.cfg"), "rb") as fh:
        assert fh.read() == b"this run's marker\r\n"


def test_until_log_waits_for_the_marker_in_that_life(w):
    lives = [["LOG|  1 |[qm] boot done", "TIM|  2 |...InitMap finished..."],
             ["LOG|  1 |[qm] boot done", "TIM|  2 |...InitMap finished..."],
             ["TIM|  2 |...InitMap finished..."]]
    game = FakeGame(w, lives)
    code, summary = hrun.run(options(w, until="InitMap finished", until_log=3), game,
                             lambda *_: None)
    assert code == 0 and summary["state"] == "reached" and summary["restarts"] == 2
    assert summary["until_log"] == 3


def test_mods_ini_as_the_game_left_it_is_kept(w):
    game = FakeGame(w, BOOTS)
    code, summary = hrun.run(options(w, fixtures=["QMTestWASD"]), game, lambda *_: None)
    assert code == 0
    with open(summary["mods_ini_during"], "rb") as fh:
        assert fh.read() == game.ini_during
    assert ini_bytes(w) == ODD_MODS_INI


# ------------------------------------------------------- composed runs
@pytest.fixture(autouse=True)
def own_workshop(monkeypatch):
    # <game>\..\..\workshop would be the parent of tmp_path, shared by every
    # test; one level up keeps each test's Workshop inside its own tmp_path.
    monkeypatch.setattr(hrun, "WORKSHOP_REL", ("..", "workshop", "content", "333420"))


def workshop_items(w, *ids):
    root = os.path.normpath(os.path.join(w.game, *hrun.WORKSHOP_REL))
    for i in ids:
        write(os.path.join(root, i, "mod.ini"), b"item\r\n")


def test_a_composed_run_starts_from_the_chosen_mods_and_restores_the_owners_file(w):
    workshop_items(w, "111", "222", "333")
    seen = {}
    game = FakeGame(w, BOOTS, on_launch=lambda g: seen.setdefault("ini", ini_bytes(w)))
    code, summary = hrun.run(options(w, enable=["222"], unlisted=["333"]), game,
                             lambda *_: None)
    assert code == 0
    from ref.order import parse_mods_ini
    rows, problem = parse_mods_ini(seen["ini"])
    assert problem is None
    ws = b"..\\..\\workshop\\content\\333420\\"
    assert rows == [(ws + b"111", b"True"), (b"mods\\SW_Frontline_Protocol", b"True"),
                    (ws + b"222", b"False"), (b"mods\\Quartermaster", b"False")]
    # The start a check compares with: the composed file, kept in the run folder.
    with open(os.path.join(w.logs, "t1", hrun.INI_COMPOSED), "rb") as fh:
        assert fh.read() == seen["ini"]
    # Afterwards the player's bytes, whatever the run wrote.
    assert ini_bytes(w) == ODD_MODS_INI and summary["sweep"]["ok"]


def test_an_unlisted_fixture_is_left_for_the_engine_to_register(w):
    # The engine lists a folder new in mods\ after every registered one - the
    # start the load-order runs (I7) need even when the run composes mods.ini.
    workshop_items(w, "111")
    write(os.path.join(w.fixtures, "QMTestCamSpeed", "mod.ini"), b"camspeed\r\n")
    seen = {}
    game = FakeGame(w, BOOTS, on_launch=lambda g: seen.setdefault("ini", ini_bytes(w)))
    code, summary = hrun.run(options(w, fixtures=["QMTestWASD", "QMTestCamSpeed"],
                                     compose=True, unlisted=["QMTestCamSpeed"]),
                             game, lambda *_: None)
    assert code == 0
    from ref.order import parse_mods_ini
    rows, problem = parse_mods_ini(seen["ini"])
    assert problem is None
    assert [d for d, _dis in rows] == [b"..\\..\\workshop\\content\\333420\\111",
                                      b"mods\\SW_Frontline_Protocol", b"mods\\QMTestWASD",
                                      b"mods\\Quartermaster"]
    assert ini_bytes(w) == ODD_MODS_INI and summary["sweep"]["ok"]


def test_a_canonical_composition_is_quartermasters_own_order(w):
    workshop_items(w, "900", "1000")
    write(os.path.join(w.game, "mods", "Alpha", "mod.ini"), b"alpha\r\n")
    seen = {}
    game = FakeGame(w, BOOTS, on_launch=lambda g: seen.setdefault("ini", ini_bytes(w)))
    code, _summary = hrun.run(options(w, fixtures=["QMTestWASD"], enable=["Alpha"],
                                      canonical=True), game, lambda *_: None)
    assert code == 0
    from ref.order import parse_mods_ini
    rows, _problem = parse_mods_ini(seen["ini"])
    ws = b"..\\..\\workshop\\content\\333420\\"
    # Workshop ids by number, then the folders by name, Quartermaster last;
    # each row keeps the flag the composition gave it.
    assert rows == [(ws + b"900", b"True"), (ws + b"1000", b"True"),
                    (b"mods\\Alpha", b"False"), (b"mods\\QMTestWASD", b"False"),
                    (b"mods\\SW_Frontline_Protocol", b"True"), (b"mods\\Quartermaster", b"False")]
    assert ini_bytes(w) == ODD_MODS_INI


def test_a_folder_already_in_mods_can_be_unlisted(w):
    # A folder the player copied in and has not started the game with yet.
    write(os.path.join(w.game, "mods", "Fresh", "mod.ini"), b"fresh\r\n")
    seen = {}
    game = FakeGame(w, BOOTS, on_launch=lambda g: seen.setdefault("ini", ini_bytes(w)))
    code, summary = hrun.run(options(w, compose=True, unlisted=["Fresh"]), game,
                             lambda *_: None)
    assert code == 0
    from ref.order import parse_mods_ini
    rows, _problem = parse_mods_ini(seen["ini"])
    assert b"mods\\Fresh" not in [d for d, _dis in rows]
    assert ini_bytes(w) == ODD_MODS_INI and summary["sweep"]["ok"]


def test_a_deployed_fixture_can_be_listed_off(w):
    write(os.path.join(w.fixtures, "QMTestCamSpeed", "mod.ini"), b"camspeed\r\n")
    seen = {}
    game = FakeGame(w, BOOTS, on_launch=lambda g: seen.setdefault("ini", ini_bytes(w)))
    code, _summary = hrun.run(options(w, fixtures=["QMTestWASD", "QMTestCamSpeed"],
                                      disable=["QMTestCamSpeed"]), game, lambda *_: None)
    assert code == 0
    from ref.order import parse_mods_ini
    rows, _problem = parse_mods_ini(seen["ini"])
    assert (b"mods\\QMTestCamSpeed", b"True") in rows and (b"mods\\QMTestWASD", b"False") in rows
    assert ini_bytes(w) == ODD_MODS_INI


def test_quartermaster_itself_cannot_be_unlisted(w):
    lines = []
    code, _summary = hrun.run(options(w, unlisted=["Quartermaster"]), FakeGame(w, BOOTS),
                              lines.append)
    assert code == 2
    assert "--unlisted Quartermaster" in "\n".join(lines)
    assert ini_bytes(w) == ODD_MODS_INI


def test_a_composed_run_refuses_a_mod_that_is_not_there(w):
    workshop_items(w, "111")
    lines = []
    code, _summary = hrun.run(options(w, enable=["999"], unlisted=["111", "888"]),
                              FakeGame(w, BOOTS), lines.append)
    assert code == 2
    text = "\n".join(lines)
    assert "--enable 999" in text and "--unlisted 888" in text
    assert ini_bytes(w) == ODD_MODS_INI


def test_a_dry_run_names_the_composed_load_order(w):
    workshop_items(w, "111", "222")
    lines = []
    code, _summary = hrun.run(options(w, dry_run=True, enable=["222", "111"]),
                              FakeGame(w, BOOTS), lines.append)
    assert code == 0
    compose = [l for l in lines if " compose " in l]
    assert compose and ("..\\..\\workshop\\content\\333420\\222, ..\\..\\workshop\\content"
                        "\\333420\\111, mods\\Quartermaster") in compose[0]
    assert ini_bytes(w) == ODD_MODS_INI


def test_first_lists_an_installed_mod_off_at_the_top_of_the_composed_file(w):
    workshop_items(w, "111", "222", "333")
    seen = {}
    game = FakeGame(w, BOOTS, on_launch=lambda g: seen.setdefault("ini", ini_bytes(w)))
    code, _summary = hrun.run(options(w, enable=["222"], first=["333"]), game, lambda *_: None)
    assert code == 0
    rows, problem = order.parse_mods_ini(seen["ini"])
    assert problem is None
    assert rows[0] == (b"..\\..\\workshop\\content\\333420\\333", b"True")
    assert [d for d, dis in rows if dis == b"False"][:1] == [b"..\\..\\workshop\\content\\333420\\222"]
    assert ini_bytes(w) == ODD_MODS_INI
    # A name that is not installed, or one also enabled, is refused.
    for kw in ({"first": ["999"]}, {"enable": ["222"], "first": ["222"]}):
        lines = []
        code, _summary = hrun.run(options(w, **kw), FakeGame(w, BOOTS), lines.append)
        assert code == 2 and any("--first" in ln for ln in lines)
        assert ini_bytes(w) == ODD_MODS_INI


def test_follow_bricks_waits_past_a_brick_line_for_the_next_life(w):
    lives = [["LOG|  4 |[qmg] life=1", "ERROR| 9 |CompileFramework() - compile global script error"],
             ["LOG|  4 |[qmg] life=2", "LOG|  5 |[qmg] done"]]
    code, summary = hrun.run(options(w, quartermaster=False, until="[qmg] done",
                                     boot_marker="[qmg]", follow_bricks=True),
                             FakeGame(w, lives), lambda *_: None)
    assert summary["state"] == "reached" and summary["restarts"] == 1
    assert summary["brick_suspected"] and code == 1
    # Without the flag the same lives end at the brick line
    # (test_a_brick_line_ends_the_wait_and_is_reported).


def test_quartermaster_can_go_in_as_a_qmtest_folder_and_loads_last(w):
    workshop_items(w, "111")
    seen = {}
    game = FakeGame(w, BOOTS, on_launch=lambda g: seen.setdefault("ini", ini_bytes(w)))
    code, summary = hrun.run(options(w, enable=["111"], qm_folder="QMTestQM"), game,
                             lambda *_: None)
    assert code == 0 and game.listing_at_launch == ["QMTestQM", "SW_Frontline_Protocol", "mods.ini"]
    from ref.order import parse_mods_ini
    rows, _p = parse_mods_ini(seen["ini"])
    assert rows[-1] == (b"mods" + bytes([92]) + b"QMTestQM", b"False")
    assert mods(w) == ["SW_Frontline_Protocol", "mods.ini"] and ini_bytes(w) == ODD_MODS_INI


def test_the_qm_folder_is_quartermaster_or_a_qmtest_name(w):
    lines = []
    code, _s = hrun.run(options(w, qm_folder="MyMod"), FakeGame(w, BOOTS), lines.append)
    assert code == 2 and any("--qm-folder" in l for l in lines)


def test_quartermasters_own_words_about_a_compile_error_are_not_a_brick(w):
    lives = [["LOG| 213 |[qm] boot report WARN ... the game stops at \"Error compiling scripts\".",
              "LOG|  9 |[qm] booted gen=1"]]
    code, summary = hrun.run(options(w, until="[qm] booted"), FakeGame(w, lives), lambda *_: None)
    assert summary["state"] == "reached" and not summary["brick_suspected"] and code == 0
