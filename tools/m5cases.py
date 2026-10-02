r"""The boot milestone's in-game runs (plan G1, G5, G14; docs/plan.md section 4,
I1 and I5-I8): case files, the fixture and seed they need, the run requests
in order, and the checks of a finished run.

    python tools/m5cases.py prepare --out DIR
        the SelfTest case files (kind m5, ref/selftest.py), the fixture
        fixtures\m5\QMTestNew, the I7 seed (a known.cfg that lists every
        mod of the installed mods.ini and Quartermaster, but not QMTestNew)
        and the saved-order seed (that known.cfg and an order.cfg with the
        installed mods in reverse canonical order: a manual order)
    python tools/m5cases.py plan --out DIR --logs LOGS
        print every run request in order: the hrun command, the marker the run
        waits for, and what the logs must show
    python tools/m5cases.py check RUN --scenario NAME
        check a finished hrun run folder against its scenario; exit 0 when it
        holds, 1 when something differs, 2 when the run folder is incomplete

The harness never writes mods.ini (decided 2026-09-28): every change of it in
these runs is made by Quartermaster's own writer in the game - the boot's
load order (mods.ini's own with Quartermaster last), or the SelfTest
case's shuffle / disable (qmCaseM5), under the same refusals. A SelfTest run keeps one life unless the case file
qm_m5_restart.cfg is there (qmBoot); I1, I5 and I7 ship it.

Scenarios (restarts = lives - 1, as hrun's summary counts them):
  compile  Quartermaster alone, case compile: every new state and hook
           compiles, qmRestart runs dry; 0 restarts
  i1       Quartermaster alone, cases relife + restart: the first boot changes
           nothing (the shipped copies carry the generation constant of
           Quartermaster alone), a test restart gives a second life, whose boot
           is stable; 1 restart; mods.ini in its own order, Quartermaster last
  i5       Quartermaster alone, cases unstable + restart: the fingerprint moves
           every boot and CameraControl's generation constant with it; life 1
           restarts automatically, life 2 refuses (loop) and reports FAIL;
           1 restart
  i6a      Quartermaster + QMTestWASD + QMTestCamSpeed, no SelfTest: the merge
           restarts once, the second life is stable; 1 restart
  i6b      the same, seeded with i6a's <save>\quartermaster: a fresh deploy
           restores the shipped copies (a Workshop update), the boot finds the
           outputs damaged, regenerates and restarts once; 1 restart
  i7       Quartermaster + QMTestNew, seeded known.cfg, cases shuffle + restart:
           the engine lists the fresh QMTestNew after Quartermaster, so life 1
           moves Quartermaster last, marks QMTestNew new and restarts
           (automatic) while the shuffle waits; life 2 needs no restart,
           which ends the chain, and the shuffle writes Quartermaster first
           and restarts (test); life 3 restores the order and restarts
           (automatic, allowed: the chain was clear); life 4 has the order
           back and still reports QMTestNew new; 3 restarts
  i8       Quartermaster alone, case disable: life 1 switches Quartermaster off
           in mods.ini and restarts (test); life 2 has no [qm] line; 1 restart

The load order the player sets in the manager (plan S11; the
rules are in ref/order.py):
  order    QMTestWASD + QMTestConflict, cases uiorder + restart: life 1 merges
           in mods.ini's order - the installed one has QMTestConflict before
           QMTestWASD - (WASD wins the conflict) and restarts
           (automatic); in life 2 the case drives the manager's controller -
           open, select WASD, up, Apply, confirm - and qmTick's Apply writes
           mods.ini and order.cfg in the new order, regenerates (now the
           Conflict mod wins) and restarts (apply); life 3 boots stable with
           the saved order and reports that it is not canonical (MP note);
           2 restarts
  saved    Quartermaster + QMTestNew, seeded known.cfg and a manual order.cfg,
           cases shuffle (reverse 1) + restart: i7's lives with the saved
           order instead of mods.ini's own - life 1 places QMTestNew after
           the saved mods, before Quartermaster; the shuffle writes
           Quartermaster first and every other row reversed; life 3 puts the
           saved order back and says mods.ini was reordered outside; 3
           restarts
"""
import argparse
import glob
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from ref import boot as B  # noqa: E402
from ref import order as O  # noqa: E402
from ref import selftest as S  # noqa: E402

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Cossacks 3"
#: Where `prepare` wrote the cases and `hrun --logs-dir` keeps its run
#: folders; the run requests name the real folders.
OUT = "CASES"
LOGS = "LOGS"
FIXTURES_M5 = os.path.join("fixtures", "m5")
NEW_FIXTURE = "QMTestNew"
#: The vanilla file QMTestNew ships (merge class: the index reads it).
NEW_SHIPS = "gui\\common.inc\\onhint.inc"
QM = b"mods\\Quartermaster"
SEED_I7 = "seed_i7"
SEED_SAVED = "seed_saved"
UIORDER_MOD = b"mods\\QMTestWASD"

#: case file -> directives (after `kind m5`)
CASES = {
    "qm_m5_compile.cfg": [(b"step", b"compile")],
    "qm_m5_relife.cfg": [(b"step", b"relife")],
    "qm_m5_restart.cfg": [(b"step", b"restart")],
    "qm_m5_unstable.cfg": [(b"step", b"unstable")],
    "qm_m5_shuffle.cfg": [(b"step", b"shuffle"), (b"new", b"mods\\" + NEW_FIXTURE.encode())],
    "qm_m5_disable.cfg": [(b"step", b"disable")],
    "qm_m5_uiorder.cfg": [(b"step", b"uiorder"), (b"mod", UIORDER_MOD), (b"cmd", b"up")],
    "qm_m5_shufflex.cfg": [(b"step", b"shuffle"), (b"reverse", b"1"),
                           (b"new", b"mods\\" + NEW_FIXTURE.encode())],
}

COMPILE_ERROR = re.compile(r"Compile script error: (\w+)")
#: The first main-menu frame after the second start-up DoCreate: the hooks
#: ran as often as the capability probes counted (CameraControl 2,
#: InitMinimap 4; probe 11). Waiting for it also lets the tick confirm the
#: start (state.cfg booted) before the harness ends the run. Whether a frame
#: also comes between the two DoCreates depends on how long the first one
#: takes (probe 11: yes; run m5compile, with a boot of 1.1 s: no), so no
#: scenario waits for `cc=1 im=2`.
TICK_START = "[qm] hooks cc=2 im=4"
CONFIRMED = "[qm] tick: the start reached the main menu; marker booted"


class Scenario(object):
    """One run request. `expect`: validation states whose compile error the run
    provokes on purpose (hrun --expect-compile-error); `quartermaster`: False
    runs the game without it (--no-quartermaster); `until` empty with no
    Quartermaster waits for the timeout; `ini_check`: what mods.ini.during must
    be - "kept" (the order the run started with, Quartermaster last),
    "qm-off" (Quartermaster switched off) or None for no rule (the default
    rule goes by the scenario name)."""

    def __init__(self, name, what, cases=(), fixtures=(), fixtures_dir=None, state=None,
                 until="", until_log=None, timeout=300, restarts=0, lives=None, expect=(),
                 quartermaster=True, ini_check=None):
        self.name, self.what, self.cases, self.fixtures = name, what, list(cases), list(fixtures)
        self.fixtures_dir, self.state, self.until, self.until_log = (
            fixtures_dir, state, until, until_log)
        self.timeout, self.restarts = timeout, restarts
        #: per life: substrings its log must hold (a leading "!" = must not)
        self.lives = lives or []
        self.expect, self.quartermaster = list(expect), quartermaster
        self.ini_check = ini_check or {"i8": "qm-off", "compile": "kept",
                                       "i1": "kept", "i7": "kept",
                                       "order": "uiorder", "saved": "saved"}.get(name)


def scenarios(out=OUT, logs=LOGS):
    return [
        Scenario("compile", "every new state and hook compiles (Quartermaster alone)",
                 cases=["qm_m5_compile.cfg"], until=TICK_START, timeout=240, restarts=0,
                 lives=[["[qm] boot version", "[qm] guard plan regen=1 mode=normal why=first",
                         "[qm] gen done status=ok", "changed=0",
                         "[qm] guard restart=False", "[qm] marker saved phase=booted gen=1",
                         "[qm] m5 case compile|qmRestart|True", "[qm] boot done regen=True",
                         TICK_START,
                         "![qm] restart now"]]),
        Scenario("i1", "Quartermaster alone: last in mods.ini, stable after the first boot",
                 cases=["qm_m5_relife.cfg", "qm_m5_restart.cfg"], until=TICK_START,
                 until_log=2, timeout=420, restarts=1,
                 lives=[["why=first", "changed=0", "[qm] guard restart=False",
                         "[qm] m5 case restart|test|selftest-relife",
                         "[qm] restart now kind=test"],
                        ["[qm] marker 1 gen=1", "rk=test", "why=stable",
                         "[qm] guard restart=False kind=- why=nothing-changed",
                         "[qm] boot stable gen=1", TICK_START, "![qm] restart now"]]),
        Scenario("i5", "forced unstable fingerprint: one automatic restart, then FAIL",
                 cases=["qm_m5_unstable.cfg", "qm_m5_restart.cfg"], until=TICK_START,
                 until_log=2, timeout=420, restarts=1,
                 lives=[["|unstable 1", "why=first", "[qm] guard restart=True kind=auto",
                         "[qm] restart now kind=auto"],
                        ["|unstable 2", "why=inputs-changed", "refused=loop",
                         "[qm] boot report FAIL No automatic restart: the mods changed again",
                         TICK_START, "![qm] restart now"]]),
        Scenario("i6a", "WASD + CamSpeed: the merge restarts once, then stable (I6, part 1)",
                 fixtures=["QMTestWASD", "QMTestCamSpeed"], until=TICK_START,
                 until_log=2, timeout=420, restarts=1,
                 lives=[["why=first", "[qm] guard restart=True kind=auto why=outputs-changed",
                         "[qm] restart now kind=auto"],
                        ["why=stable", "[qm] boot stable", CONFIRMED, TICK_START,
                         "![qm] restart now"]]),
        Scenario("i6b", "shipped hook copies restored (fresh deploy): regenerated (I6, part 2)",
                 fixtures=["QMTestWASD", "QMTestCamSpeed"],
                 state=os.path.join(logs, "m5i6a", "qm_save"), until=TICK_START,
                 until_log=2, timeout=420, restarts=1,
                 lives=[["[qm] guard: output ", "why=damaged",
                         "[qm] boot report OK Quartermaster's files were changed from outside",
                         "[qm] guard restart=True kind=auto why=outputs-changed"],
                        ["why=stable", "[qm] boot stable", CONFIRMED, TICK_START,
                         "![qm] restart now"]]),
        # One automatic restart per fingerprint in a chain (plan S8), and the
        # shuffle keeps the fingerprint: so it may only come in a life that
        # ended the chain of life 1 (run m5i7 of 2026-09-28 shuffled in life
        # 1, and life 2 refused per-hash). The marker lines prove the chain.
        # No order.cfg in the seed: mods.ini's own order (ref/order.py rule 1).
        Scenario("i7", "shuffled mods.ini + a new folder: order restored, folder new",
                 cases=["qm_m5_shuffle.cfg", "qm_m5_restart.cfg"], fixtures=[NEW_FIXTURE],
                 fixtures_dir=FIXTURES_M5, state=os.path.join(out, SEED_I7),
                 until=TICK_START, until_log=4, timeout=600, restarts=3,
                 lives=[["[qm] order: src=ini canon=", " ext=0 unseen=0 dropped=0 "
                         "order.cfg=same",
                         "[qm] mods.ini moved: ", "[qm] known: new mod mods\\" + NEW_FIXTURE,
                         "[qm] guard restart=True kind=auto why=mods-ini-changed refused= ",
                         "[qm] m5 case wait|restart=1|rows=1|rcount=1",
                         "[qm] restart now kind=auto", "![qm] m5 case wrote|"],
                        ["rcount=1 rk=auto boots=1", "[qm] mods.ini same",
                         "[qm] guard restart=False kind=- why=nothing-changed refused= ",
                         "[qm] m5 case wrote|written|1",
                         "[qm] m5 case restart|test|selftest-shuffle",
                         "[qm] restart now kind=test"],
                        ["rows=0 rhash=- rcount=0 rk=test boots=2", "[qm] mods.ini written",
                         "[qm] guard restart=True kind=auto why=mods-ini-changed refused= ",
                         "[qm] m5 case done|0", "[qm] restart now kind=auto",
                         "![qm] m5 case wrote|"],
                        ["rcount=1 rk=auto boots=3", "[qm] mods.ini same",
                         "[qm] guard restart=False kind=- why=nothing-changed refused= ",
                         "[qm] m5 case new|mods\\" + NEW_FIXTURE,
                         "[qm] m5 case done|1", "[qm] m5 i7 done", TICK_START,
                         "![qm] restart now", "![qm] m5 case wrote|"]]),
        order_scenario(),
        saved_scenario(out),
        Scenario("i8", "Quartermaster disabled in mods.ini: no Quartermaster line",
                 cases=["qm_m5_disable.cfg"], until="InitMap finished", until_log=2,
                 timeout=420, restarts=1,
                 lives=[["[qm] m5 case wrote|written", "[qm] m5 case restart|test|selftest-disable",
                         "[qm] restart now kind=test"],
                        ["!" + "[qm]", "InitMap finished"]]),
    ]


def order_scenario():
    """(a) of the load-order check: a reorder through the manager's controller and Apply."""
    return Scenario(
        "order", "a mod moved up in the manager + Apply: mods.ini and order.cfg in the new "
        "order, regenerated (the conflict's winner changes), one Apply restart, then stable",
        cases=["qm_m5_uiorder.cfg", "qm_m5_restart.cfg"],
        fixtures=["QMTestWASD", "QMTestConflict"], until=TICK_START, until_log=3,
        timeout=600, restarts=2,
        lives=[["why=first", "[qm] order: src=ini",
                "[qm] guard restart=True kind=auto why=outputs-changed",
                "[qm] m5 case wait|regen=1|restart=1", "[qm] restart now kind=auto"],
               ["why=stable", "[qm] m5 case order|ini|",
                "[qm] ui order up row=", " moved=1 ordchg=1 ", "[qm] m5 case kept|1|1|",
                "[qm] tick: running the Apply of the manager window",
                "[qm] order: src=apply canon=0 ext=0 unseen=0 dropped=0 order.cfg=written",
                "[qm] mods.ini written", "[qm] mods.ini moved: ",
                "[qm] boot report OK mods.ini was put into the load order chosen in the manager",
                "[qm] boot report OK Multiplayer: every player needs the same mods",
                "[qm] guard restart=True kind=apply why=outputs-changed",
                "[qm] restart now kind=apply"],
               ["why=stable", "[qm] order: src=saved canon=0 ext=0 unseen=0 dropped=0 "
                "order.cfg=same", "[qm] mods.ini same",
                "[qm] guard restart=False kind=- why=nothing-changed",
                "[qm] boot report OK Multiplayer: every player needs the same mods",
                "[qm] m5 case done|1", "[qm] m5 uiorder done", CONFIRMED, TICK_START,
                "![qm] restart now"]])


def saved_scenario(out=OUT):
    """(b) of the load-order check: an outside shuffle of a saved order, and a new folder."""
    new = "mods\\" + NEW_FIXTURE
    return Scenario(
        "saved", "a saved load order, mods.ini shuffled outside + a new folder: the saved "
        "order put back, the new folder placed before Quartermaster",
        cases=["qm_m5_shufflex.cfg", "qm_m5_restart.cfg"], fixtures=[NEW_FIXTURE],
        fixtures_dir=FIXTURES_M5, state=os.path.join(out, SEED_SAVED),
        until=TICK_START, until_log=4, timeout=600, restarts=3,
        lives=[["[qm] order: src=saved", "[qm] order: %s is not in the saved order yet; "
                "placed before Quartermaster" % new, "order.cfg=written",
                "[qm] mods.ini moved: ", "[qm] known: new mod " + new,
                "[qm] boot report OK Not in the saved load order yet, so placed after it, "
                "before Quartermaster: %s." % new,
                "[qm] guard restart=True kind=auto why=mods-ini-changed refused= ",
                "[qm] m5 case wait|restart=1|rows=1|rcount=1",
                "[qm] restart now kind=auto", "![qm] m5 case wrote|"],
               ["rcount=1 rk=auto boots=1", "[qm] order: src=saved", "unseen=0",
                "order.cfg=same", "[qm] mods.ini same",
                "[qm] guard restart=False kind=- why=nothing-changed refused= ",
                "[qm] m5 case wrote|written|1",
                "[qm] m5 case restart|test|selftest-shuffle",
                "[qm] restart now kind=test"],
               ["rows=0 rhash=- rcount=0 rk=test boots=2", "[qm] order: src=saved canon=",
                " ext=1 unseen=0 dropped=0 order.cfg=same", "[qm] mods.ini written",
                "[qm] boot report OK mods.ini was reordered outside Quartermaster",
                "[qm] guard restart=True kind=auto why=mods-ini-changed refused= ",
                "[qm] m5 case done|0", "[qm] restart now kind=auto",
                "![qm] m5 case wrote|"],
               ["rcount=1 rk=auto boots=3", " ext=0 unseen=0 dropped=0 order.cfg=same",
                "[qm] mods.ini same",
                "[qm] guard restart=False kind=- why=nothing-changed refused= ",
                "[qm] m5 case new|" + new,
                "[qm] m5 case done|1", "[qm] m5 i7 done", TICK_START,
                "![qm] restart now", "![qm] m5 case wrote|"]])


def by_name(name, out=OUT, logs=LOGS):
    for s in scenarios(out, logs):
        if s.name == name:
            return s
    raise KeyError(name)


# ------------------------------------------------------------- prepare
def case_bytes(name):
    return S.render_case(b"m5", CASES[name])


def installed_dirs(game=GAME):
    """The dirs of the mods a composed run starts with: every Workshop item
    Steam has installed and every folder in mods\\ (hrun composed_rows), so
    the seeds know the same mods. Not the installed mods.ini: an item the
    engine has not registered is missing there, and every check that read it
    then failed on a mod the run had (m12full runs of 2026-10-02: the
    published Quartermaster, held out of mods.ini by its own local copy)."""
    import hrun
    path = os.path.join(game, "mods")
    dirs = [hrun.WORKSHOP_DIR + n.encode("ascii") for n in hrun.installed_workshop(game)]
    dirs += [b"mods\\" + n.encode("ascii") for n in sorted(os.listdir(path))
             if os.path.isdir(os.path.join(path, n))]
    return dirs


def seed_known(dirs):
    """known.cfg for I7: every installed mod and Quartermaster known."""
    entries = [(d, False) for d in dirs]
    if all(O.norm_dir(d) != O.norm_dir(QM) for d in dirs):
        entries.append((QM, False))
    return B.render_known(entries)


def seed_order(dirs):
    """order.cfg for the saved-order run: the installed mods (Quartermaster
    left out) in reverse canonical order - a manual order, not the canonical
    one, whenever two or more mods are installed."""
    others = [d for d in dirs if O.norm_dir(d) != O.norm_dir(QM)]
    return O.render_order(list(reversed(O.canonical_order(others))))


def prepare(out=OUT, fixtures=FIXTURES_M5, game=GAME, echo=print):
    os.makedirs(out, exist_ok=True)
    for name in sorted(CASES):
        with open(os.path.join(out, name), "wb") as fh:
            fh.write(case_bytes(name))
        echo("wrote %s" % os.path.join(out, name))
    new = os.path.join(fixtures, NEW_FIXTURE)
    os.makedirs(new, exist_ok=True)
    # A folder with no mod.ini: the game registers it anyway (M0). It ships
    # the installed game's own copy of one file the index reads (NEW_SHIPS),
    # byte for byte: Quartermaster moving last past a mod with no such file
    # and none of its own asks no restart since 2026-10-01 (ref/order.py
    # needs_restart), and these runs test the restart chain of plan S8.
    with open(os.path.join(new, "readme.txt"), "wb") as fh:
        fh.write(b"Quartermaster test fixture: a new mod folder (plan I7).\r\n")
    ships = os.path.join(new, "data", *NEW_SHIPS.split("\\"))
    os.makedirs(os.path.dirname(ships), exist_ok=True)
    shutil.copyfile(os.path.join(game, "data", *NEW_SHIPS.split("\\")), ships)
    echo("wrote %s" % new)
    seed = os.path.join(out, SEED_I7)
    os.makedirs(seed, exist_ok=True)
    with open(os.path.join(seed, "known.cfg"), "wb") as fh:
        fh.write(seed_known(installed_dirs(game)))
    echo("wrote %s" % os.path.join(seed, "known.cfg"))
    seed = os.path.join(out, SEED_SAVED)
    os.makedirs(seed, exist_ok=True)
    for name, data in (("known.cfg", seed_known(installed_dirs(game))),
                       ("order.cfg", seed_order(installed_dirs(game)))):
        with open(os.path.join(seed, name), "wb") as fh:
            fh.write(data)
        echo("wrote %s" % os.path.join(seed, name))
    return 0


# ---------------------------------------------------------------- plan
def command(s, out=OUT, logs=LOGS, prefix="m5"):
    parts = ["python tools/hrun.py", "--logs-dir %s" % logs, "--run-id %s%s" % (prefix, s.name)]
    if not s.quartermaster:
        parts.append("--no-quartermaster")
    if s.fixtures_dir:
        parts.append("--fixtures-dir %s" % s.fixtures_dir)
    parts += ["--fixture %s" % f for f in s.fixtures]
    parts += ["--case %s" % os.path.join(out, c) for c in s.cases]
    if s.state:
        parts.append("--state %s" % s.state)
    parts += ["--expect-compile-error %s" % e for e in s.expect]
    if s.until:
        parts.append('--until "%s"' % s.until)
    if s.until_log:
        parts.append("--until-log %d" % s.until_log)
    parts.append("--timeout %d" % s.timeout)
    return " ".join(parts)


def plan(out=OUT, logs=LOGS, echo=print):
    echo("Run requests, in this order (each after `python tools/hbuild.py --check` and "
         "`python tools/m5cases.py prepare`):")
    for n, s in enumerate(scenarios(out, logs), 1):
        echo("")
        echo("%d. m5%s - %s" % (n, s.name, s.what))
        echo("   " + command(s, out, logs))
        echo("   expect: %d restart(s), %d log(s); then python tools/m5cases.py check %s "
             "--scenario %s" % (s.restarts, s.restarts + 1, os.path.join(logs, "m5" + s.name),
                                s.name))
        for k, want in enumerate(s.lives, 1):
            echo("   log %d: %s" % (k, "; ".join(want)))
    return 0


# --------------------------------------------------------------- check
def _read(path):
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def run_logs(run_dir):
    """`[(name, text lines)]` of the copied game logs, oldest first."""
    out = []
    for path in sorted(glob.glob(os.path.join(run_dir, "*cos_*.log")),
                       key=lambda p: int(os.path.basename(p).split(".", 1)[0])):
        out.append((os.path.basename(path), _read(path).decode("latin-1").splitlines()))
    return out


#: The writer's line per output (src/lib/qmwrite.pas): result 1 = written,
#: 2 = equal and left alone; FileAge of the relative spelling before and after.
WRITE = re.compile(r"\[qm\] write (\S+) result=(-?\d+) before abs=(-?\d+) dst=(-?\d+) "
                   r".* after abs=(-?\d+) dst=(-?\d+) ")


def stamp_problems(logs, state_cfg):
    """The marker's output stamps against the writer's own FileAge lines.

    The stamps come from the last life that generated (the last log with
    write lines): a file left alone (result 2) keeps its FileAge from before
    the write, a written one (result 1) has the one after it. The manifest has
    no write line and is not compared here."""
    lines = []
    for _name, log in logs:
        found = [m for m in map(WRITE.search, log) if m]
        if found:
            lines = found
    if not lines or state_cfg is None:
        return []
    marker = B.parse_marker(state_cfg)
    if marker is None:
        return ["qm_save\\state.cfg is not a marker"]
    stamps = dict((p.decode("latin-1"), a.decode("latin-1")) for p, a in marker.outs)
    problems = []
    for m in lines:
        path, result = m.group(1), m.group(2)
        want = {"1": m.group(6), "2": m.group(4)}.get(result)
        if want is None:
            continue                      # refused or failed: not an output
        if stamps.get(path) != want:
            problems.append("state.cfg stamp of %s is %s, the writer saw %s (result=%s)"
                            % (path, stamps.get(path), want, result))
    return problems


def check_run(run_dir, s):
    """`(problems, facts)` of a run folder against scenario `s`."""
    problems, facts = [], {}
    summary = _read(os.path.join(run_dir, "summary.json"))
    if summary is None:
        return None, {"missing": "summary.json"}
    summary = json.loads(summary.decode("utf-8"))
    logs = run_logs(run_dir)
    facts.update(state=summary.get("state"), restarts=summary.get("restarts"),
                 logs=[n for n, _l in logs], sweep=summary.get("sweep", {}).get("ok"))
    # A run with no marker to wait for (the game without Quartermaster) ends
    # at its timeout, which is then the expected end.
    want_state = "reached" if s.until else "timeout"
    if summary.get("state") != want_state:
        problems.append("the run ended %r, not %s" % (
            summary.get("state"), "at its marker" if s.until else "at its timeout"))
    if not summary.get("sweep", {}).get("ok"):
        problems.append("sweep: %s" % summary.get("sweep", {}).get("problems"))
    if summary.get("brick_suspected"):
        problems.append("brick suspected: %s" % summary.get("brick_lines"))
    if summary.get("restarts") != s.restarts:
        problems.append("%s restart(s), expected %d" % (summary.get("restarts"), s.restarts))
    expected = set(e.lower() for e in s.expect)
    for name, lines in logs:
        errors = [m.group(1) for m in map(COMPILE_ERROR.search, lines) if m]
        errors = [e for e in errors if e.lower() not in expected]
        if errors:
            problems.append("%s: Compile script error: %s" % (name, ", ".join(errors)))
        boots = sum(1 for ln in lines if "[qm] boot version" in ln and " hook=" in ln)
        if boots > 1:
            problems.append("%s: %d boots in one process (once per process, plan S5)"
                            % (name, boots))
    for k, want in enumerate(s.lives):
        if k >= len(logs):
            problems.append("log %d missing" % (k + 1))
            continue
        name, lines = logs[k]
        text = "\n".join(lines)
        for w in want:
            if w.startswith("!"):
                if w[1:] in text:
                    problems.append("%s holds %r" % (name, w[1:]))
            elif w not in text:
                problems.append("%s lacks %r" % (name, w))
    during = _read(os.path.join(run_dir, "mods.ini.during"))
    if during is not None:
        rows, problem = O.parse_mods_ini(during)
        facts["mods_ini_during"] = [(d.decode("latin-1"), dis.decode("latin-1"))
                                    for d, dis in rows or []]
        if problem is not None:
            problems.append("mods.ini.during: %s" % problem.decode())
        elif s.ini_check == "qm-off":
            if dict((O.norm_dir(d), dis) for d, dis in rows).get(O.norm_dir(QM)) != b"True":
                problems.append("mods.ini.during: Quartermaster is not switched off")
        elif s.ini_check == "kept":
            problems += kept_order_problems(run_dir, rows)
        elif s.ini_check in ("uiorder", "saved"):
            problems += load_order_problems(run_dir, s, rows)
    elif s.ini_check is not None:
        problems.append("mods.ini.during missing")
    problems += stamp_problems(logs, _read(os.path.join(run_dir, "qm_save", "state.cfg")))
    if s.name == "i7":
        state = _read(os.path.join(run_dir, "qm_save", "known.cfg"))
        known = B.parse_known(state) if state is not None else None
        want = b"mods\\" + NEW_FIXTURE.encode()
        if not known or (want, True) not in known:
            problems.append("known.cfg does not mark %s new: %s" % (want, known))
    return problems, facts


def kept_order_problems(run_dir, rows):
    """mods.ini as the game left it against the one the run started with: no
    saved order keeps mods.ini's own order, so every mod of the start
    keeps its place among the others, folders the engine registered during
    the run come after them, and Quartermaster is last.

    The run starts from what hrun composed (mods.ini.composed), not from its
    mods.ini.backup (the player's file). Until 2026-10-01 the check compared
    with the backup itself, and every M7 run of m12 failed on an order the
    game had kept (runs m12cri1-i7); then with the backup's rows in canonical
    order, which lacks an installed item the player's file does not list
    (runs m12fulli1-i7 of 2026-10-02). A run from before hrun kept the
    composed file falls back to that."""
    problems = []
    dirs = [d for d, _dis in rows]
    if not dirs or O.norm_dir(dirs[-1]) != O.norm_dir(QM):
        problems.append("mods.ini.during: Quartermaster is not last")
    composed = _read(os.path.join(run_dir, "mods.ini.composed"))
    if composed is not None:
        start, _p = O.parse_mods_ini(composed)
        if start is None:
            return problems + ["mods.ini.composed is not in the engine's layout"]
        start = [d for d, _dis in start]
    else:
        base, _p = O.parse_mods_ini(_read(os.path.join(run_dir, "mods.ini.backup")) or b"")
        if base is None:
            return problems + ["mods.ini.backup is missing or not in the engine's layout"]
        start = O.canonical_order([d for d, _dis in base])
    before = [O.norm_dir(d) for d in start if O.norm_dir(d) != O.norm_dir(QM)]
    now = [O.norm_dir(d) for d in dirs if O.norm_dir(d) != O.norm_dir(QM)]
    if now[:len(before)] != [d for d in before if d in now]:
        problems.append("mods.ini.during has not kept the order the run started with: %s"
                        % dirs)
    return problems


def load_order_problems(run_dir, s, rows):
    """mods.ini as the game left it and qm_save\\order.cfg against the load
    order (ref/order.py): the saved order in mods.ini, Quartermaster last,
    order.cfg listing exactly mods.ini's other rows; `uiorder`: the moved mod
    before the one it passed and not the canonical order; `saved`: the seed's
    order with the new folder after it."""
    problems = []
    dirs = [d for d, _dis in rows]
    if not dirs or O.norm_dir(dirs[-1]) != O.norm_dir(QM):
        problems.append("mods.ini.during: Quartermaster is not last")
    saved = O.parse_order(_read(os.path.join(run_dir, "qm_save", "order.cfg")))
    others = [d for d in dirs if O.norm_dir(d) != O.norm_dir(QM)]
    if saved is None:
        problems.append("qm_save\\order.cfg is missing or not an order.cfg")
    elif saved != others:
        problems.append("qm_save\\order.cfg %r is not mods.ini's order %r" % (saved, others))
    if s.ini_check == "uiorder":
        low = [O.norm_dir(d) for d in dirs]
        wasd, conf = O.norm_dir(UIORDER_MOD), O.norm_dir(b"mods\\QMTestConflict")
        if wasd not in low or conf not in low or low.index(wasd) > low.index(conf):
            problems.append("mods.ini.during: QMTestWASD is not before QMTestConflict: %s"
                            % dirs)
        if others == O.canonical_order(others):
            problems.append("mods.ini.during is still in canonical order: %s" % dirs)
    else:
        # The seed the run started from: hrun's summary names it (the path
        # as given to --state), else the scenario's own.
        summary = _read(os.path.join(run_dir, "summary.json"))
        where = (json.loads(summary.decode("utf-8")).get("state_seed") if summary else None
                 ) or s.state
        seed = O.parse_order(_read(os.path.join(where, "order.cfg"))) if where else None
        if seed is None:
            problems.append("the seed's order.cfg (%s) cannot be read" % where)
        else:
            lo = O.load_order(dirs, QM, seed)
            want = [dirs[i] for i in lo.rows]
            if dirs != want:
                problems.append("mods.ini.during %r is not the saved order %r" % (dirs, want))
        new = O.norm_dir(b"mods\\" + NEW_FIXTURE.encode())
        if len(dirs) < 2 or O.norm_dir(dirs[-2]) != new:
            problems.append("mods.ini.during: the new folder is not right before Quartermaster")
    return problems


def check(run_dir, name, echo=print):
    s = by_name(name)
    problems, facts = check_run(run_dir, s)
    if problems is None:
        echo("incomplete: %s" % facts)
        return 2
    echo("facts: %s" % facts)
    for p in problems:
        echo("DIFF " + p)
    echo("m5 %s: %s" % (name, "OK" if not problems else "%d difference(s)" % len(problems)))
    return 0 if not problems else 1


def main(argv=None, echo=print):
    p = argparse.ArgumentParser(prog="m5cases.py", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("prepare")
    pr.add_argument("--out", required=True)
    pr.add_argument("--fixtures", default=FIXTURES_M5)
    pr.add_argument("--game-dir", default=GAME)
    pl = sub.add_parser("plan")
    pl.add_argument("--out", required=True)
    pl.add_argument("--logs", required=True)
    ch = sub.add_parser("check")
    ch.add_argument("run")
    ch.add_argument("--scenario", required=True, choices=[s.name for s in scenarios()])
    a = p.parse_args(argv)
    if a.cmd == "prepare":
        return prepare(a.out, a.fixtures, a.game_dir, echo)
    if a.cmd == "plan":
        return plan(a.out, a.logs, echo)
    return check(a.run, a.scenario, echo)


if __name__ == "__main__":
    sys.exit(main())
