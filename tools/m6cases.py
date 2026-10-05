r"""The manager window's in-game runs: the SelfTest case and the checks of a run.

    python tools/m6cases.py case --out DIR [--cycles N] [--toggle DIR]
        write DIR\qm_case_ui.cfg, the `ui` SelfTest case (ref/selftest.py)
    python tools/m6cases.py check RUN [--cycles N] [--toggle DIR]
        run A: the case's dump against ref.selftest.ui_expected, done.txt, and
        the log rules below with no battle, the main menu button's caption
        among them
    python tools/m6cases.py log RUN [--battles N] [--closes N]
        run B (by hand): the log rules only, for N returns to the menu
        from a battle, and at least `--closes` window closes
    python tools/m6cases.py case --i9 --out DIR
        write DIR\qm_case_ui9.cfg (the `ui` case with `keep 1`) and
        DIR\qm_m5_restart.cfg (lets a SelfTest run restart, qmBoot)
    python tools/m6cases.py plan --i9 --out DIR --logs LOGS
        print the hrun command of run I9 and what each life must show
    python tools/m6cases.py i9check RUN
        run I9: the dumps of every life, done.txt, the logs, mods.ini as the
        game left it and - when hrun collected it - Quartermaster's folder

RUN is an hrun run folder: its `qm_test_out\` (the SelfTest's output) and its
copied game logs (`<n>.cos_*.log`). Exit status: 0 when everything holds, 1
when something differs, 2 when the output is missing.

Run I9 (docs/plan.md section 4: a mod disabled after a merge), through the
window: QMTestWASD + QMTestCamSpeed, no other switch than the two case files.
  life 1  the first boot merges oncamera.inc and registershortcuts.inc and
          restarts (auto); the case waits, since the merged files are not
          loaded yet
  life 2  stable: both fixtures' registershortcuts markers run. The case opens
          the window by the Mod manager tag, deactivates QMTestCamSpeed,
          Apply, Enter, and leaves the request. On the next main-menu frame
          qmTick runs the boot with runmode = apply: mods.ini with CamSpeed
          off (Quartermaster's own writer, never the harness), a generation
          without it - the two merged files are stale and deleted - and the
          restart (apply)
  life 3  CamSpeed is off: no CamSpeed marker, WASD's own files are in effect;
          the boot is stable and the case reports the flag
Lives 3, restarts 2. SelfTest holds every restart unless qm_m5_restart.cfg is
there, which is why the run ships it.

The log rules (docs/ui.md, "Adding the screens"):
  * no `Compile script error:` for the window's states or the case;
  * `TXStateMachine.IndexOfState(ShowQmManager|EventQmManager)` never (until
    0.1.3 once per return from a battle: the check looked the name up). The
    check now reads the name at the index it remembered, so a return from a
    battle costs no ERROR line at all: no `ERROR|` line may stand between
    that DoCreate's `...DoCreate started...` and its `screens gone` line,
    whatever it says (the engine answers
    silently for an index past the end: run g17b1, 2026-10-05; docs/ui.md,
    "Adding the screens");
  * one `screens gone` line per return from a battle, never otherwise;
  * both screen states added 1 + N times, and the last `ready=1 adds=` = 1 + N;
  * at least one `screens present` line: a DoCreate without a map load found
    them silently;
  * every `[qm] ui show` line says `windows=1`: however often the window was
    opened, one QmManager element exists;
  * run A only (`run_a`): a `[qm] ui rename:` line that reads the caption
    back as set (`off=0`) - the main menu button reads "Mod Manager" - and
    the confirmed Apply's restart notice (`[qm] ui show restart notice`).
The facts also count what the hands-on check needs to see: the restart
notices (`[qm] tick: restart notice shown`, `[qm] ui show restart notice`)
and what a drag in the Active list delivered (`ui drag start|none|end`,
`ui mouse d|u on ...`, `ui order move`).
"""
import argparse
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
for _p in (REPO, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import m5cases  # noqa: E402
from ref import order as O  # noqa: E402
from ref import selftest as S  # noqa: E402

CASE_FILE = "qm_case_ui.cfg"
DUMP_FILE = "qm_case_ui.txt"
CYCLES = 10
#: The fixture Deactivate and Apply work on: enabled in run A, never Quartermaster.
TOGGLE = b"mods\\QMTestCamSpeed"
WINDOW_STATES = ("ShowQmManager", "EventQmManager")
OWN_STATES = re.compile(r"Compile script error: (ShowQmManager|EventQmManager|qmUi\w*|qmCaseUi)")
MISSED = re.compile(r"TXStateMachine\.IndexOfState\((ShowQmManager|EventQmManager)\)")
ADDED = re.compile(r"\[qm\] ui ensure: added (ShowQmManager|EventQmManager) lines=(\d+)")
READY = re.compile(r"\[qm\] ui ensure: ready=(\d+) adds=(\d+)")
SHOW = re.compile(r"\[qm\] ui show .* windows=(\d+)")
CLOSES = re.compile(r"\[qm\] ui close closes=(\d+)")
RENAME = re.compile(r"\[qm\] ui rename: main menu button caption set, renames=(\d+) "
                    r"reads back=\[(.*)\] off=(\d)")
#: Log lines counted as facts only: the restart notice, the drag's evidence.
COUNTED = (("notice_tick", "[qm] tick: restart notice shown"),
           ("notice_window", "[qm] ui show restart notice"),
           ("drag_start", "[qm] ui drag start"), ("drag_none", "[qm] ui drag none"),
           ("drag_end", "[qm] ui drag end"), ("mouse_up_active", "[qm] ui mouse u on active"),
           ("mouse_down_active", "[qm] ui mouse d on active"),
           ("order_move", "[qm] ui order move"))


#: Run I9 through the window (the module docstring).
CASE_I9 = "qm_case_ui9.cfg"
RESTART_CASE = "qm_m5_restart.cfg"
I9_FIXTURES = ("QMTestWASD", "QMTestCamSpeed")
KEEPER = b"mods\\QMTestWASD"
#: The files QMTestWASD and QMTestCamSpeed both ship: merged in life 1, stale
#: once CamSpeed is off.
MERGED = (b"gui\\menu.inc\\oncamera.inc", b"gui\\menu.inc\\registershortcuts.inc")
#: hrun's copy of Quartermaster's folder as the run left it (tools/hrun.py).
QM_COPY = "qm_mod"
STALE = re.compile(r"\[qm\] gen stale (\S+) (\w+)")


def case_bytes(cycles=CYCLES, toggle=TOGGLE):
    return S.render_case(b"ui", S.ui_directives(cycles, toggle))


def i9_case_files(toggle=TOGGLE):
    """`{file name: bytes}` of run I9: the `keep` case and the restart switch."""
    return {CASE_I9: S.render_case(b"ui", S.ui_directives(0, toggle, keep=True)),
            RESTART_CASE: m5cases.case_bytes(RESTART_CASE)}


def i9_scenario(out="CASES", logs="LOGS", toggle=TOGGLE):
    """The run request of I9, in m5cases' shape (checked by its check_run)."""
    t = toggle.decode("latin-1")
    return m5cases.Scenario(
        "i9", "a mod switched off in the manager window after a merge (I9)",
        cases=[CASE_I9, RESTART_CASE], fixtures=list(I9_FIXTURES), until=m5cases.TICK_START,
        until_log=3, timeout=600, restarts=2, ini_check="canonical",
        lives=[["why=first", "[qm] guard restart=True kind=auto why=outputs-changed",
                "[qm] ui case life|1|wait|regen=1|restart=1", "[qm] restart now kind=auto",
                "![qm] ui apply change"],
               ["why=stable", "[qm] boot stable", "QMTEST camspeed registershortcuts",
                "QMTEST wasd", "[qm] ui case life|2|go",
                "[qm] ui apply change seq=1 row=", " dis=0->1 dir=" + t,
                "[qm] ui case kept|1|1",
                "[qm] tick: running the Apply of the manager window, seq=1",
                " apply seq=1", "[qm] order: apply sets on=0 for " + t,
                "[qm] guard plan regen=1 mode=normal why=apply", "[qm] mods.ini written",
                "[qm] guard restart=True kind=apply", "[qm] restart now kind=apply"],
               ["why=stable", "[qm] boot stable", "QMTEST wasd", "!QMTEST camspeed",
                "[qm] ui case life|3|later|on=0|why=stable", m5cases.TICK_START,
                "![qm] restart now", "![qm] ui apply change"]])


def i9_problems(run_dir, toggle=TOGGLE, fixtures_dir=None):
    """`(problems, facts)` of run I9 beyond m5cases.check_run: the case's dump
    of every life, done.txt, the flags in mods.ini.during, the stale files in
    the life that applied, and Quartermaster's folder when hrun kept a copy.
    Returns `(None, facts)` when the SelfTest output is missing."""
    out_dir = os.path.join(run_dir, "qm_test_out")
    stem = CASE_I9[:-4]
    dumps = [_read(os.path.join(out_dir, "%s_%d.txt" % (stem, k))) for k in (1, 2, 3)]
    done = _read(os.path.join(out_dir, "done.txt"))
    facts = {"dumps": [d is not None for d in dumps]}
    if done is None or dumps[1] is None:
        return None, facts
    problems = []
    want = {0: S.ui_keep_wait(1, 1, 1), 2: S.ui_keep_later(3, b"0", b"stable")}
    for k in (0, 2):
        got = S.dump_lines(dumps[k]) if dumps[k] is not None else None
        if got != want[k]:
            problems.append("%s_%d.txt: game %r, expected %r" % (stem, k + 1, got, want[k]))
    rows = S.parse_dump(dumps[1])
    body = [r for r in rows if r[0] not in (b"life", b"kept")]
    row = next((int(r[2]) for r in body if r[0] == b"row" and r[2].lstrip(b"-").isdigit()), -1)
    got = S.dump_lines(dumps[1])
    if got != S.ui_keep_go(toggle, row, 2):
        problems += ["%s_2.txt: %s" % (stem, p) for p in S.ui_check(body, 0, toggle)]
        if got[:1] != [b"life|2|go"] or got[-1:] != [b"kept|1|1"]:
            problems.append("%s_2.txt: first/last line %r / %r, expected life|2|go / kept|1|1"
                            % (stem, got[:1], got[-1:]))
    if _read(os.path.join(out_dir, stem + ".done")) is None:
        problems.append("%s.done missing: the window's flow never ran" % stem)
    want_done = S.done_expected([(CASE_I9.encode(), b"ui"), (RESTART_CASE.encode(), b"m5")])
    if S.dump_lines(done) != want_done:
        problems.append("done.txt %r, expected %r" % (S.dump_lines(done), want_done))
    during = _read(os.path.join(run_dir, "mods.ini.during"))
    if during is not None:
        flags = dict((O.norm_dir(d), dis) for d, dis in (O.parse_mods_ini(during)[0] or []))
        facts["flags"] = dict((d.decode("latin-1"), v.decode()) for d, v in flags.items())
        if flags.get(O.norm_dir(toggle)) != b"True" or flags.get(O.norm_dir(KEEPER)) != b"False":
            problems.append("mods.ini.during: %s must be off and %s on: %r"
                            % (toggle.decode(), KEEPER.decode(), facts["flags"]))
    logs = m5cases.run_logs(run_dir)
    if len(logs) >= 2:
        stale = dict((m.group(1).encode("latin-1"), m.group(2))
                     for m in map(STALE.search, logs[1][1]) if m)
        facts["stale"] = dict((p.decode(), r) for p, r in stale.items())
        for path in MERGED:
            if stale.get(path) not in ("deleted", "overwritten"):
                problems.append("life 2: the stale %s was not removed or overwritten (%r)"
                                % (path.decode(), stale.get(path)))
    problems += qm_folder_problems(run_dir, fixtures_dir)
    return problems, facts


def qm_folder_problems(run_dir, fixtures_dir=None):
    """Quartermaster's folder as the run left it (hrun's copy, if any): no
    merged file of the dropped mod; a file that could not be deleted must be
    QMTestWASD's own copy (plan S9: overwritten with the current winner's)."""
    copy = os.path.join(run_dir, QM_COPY)
    if not os.path.isdir(copy):
        return []
    fixtures_dir = fixtures_dir or os.path.join(REPO, "fixtures")
    problems = []
    for path in MERGED:
        rel = path.decode().split("\\")
        got = _read(os.path.join(copy, "data", *rel))
        if got is None:
            continue
        own = _read(os.path.join(fixtures_dir, KEEPER.decode()[5:], "data", *rel))
        if got != own:
            problems.append("%s: %s is still in Quartermaster's folder and is not %s's own "
                            "copy" % (QM_COPY, path.decode(), KEEPER.decode()))
    return problems


def i9_check(run_dir, toggle=TOGGLE, fixtures_dir=None, out=print):
    s = i9_scenario(toggle=toggle)
    problems, facts = m5cases.check_run(run_dir, s)
    if problems is None:
        out("incomplete: %s" % facts)
        return 2
    mine, more = i9_problems(run_dir, toggle, fixtures_dir)
    facts.update(more)
    if mine is None:
        out("incomplete: SelfTest output missing under %s: %s"
            % (os.path.join(run_dir, "qm_test_out"), more))
        return 2
    problems += mine
    out("facts: %s" % facts)
    for p in problems:
        out("DIFF " + p)
    out("ui run I9: %s" % ("OK" if not problems else "%d difference(s)" % len(problems)))
    return 0 if not problems else 1


def _read(path):
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def run_logs(run_dir):
    """The game-log lines of a run folder, oldest log first, as text."""
    lines = []
    for path in sorted(glob.glob(os.path.join(run_dir, "*cos_*.log"))):
        lines += _read(path).decode("latin-1").splitlines()
    return lines


def log_problems(lines, battles=0, closes=0, run_a=False):
    """`(problems, facts)` of the log rules above."""
    problems, facts = [], {}
    for key, needle in COUNTED:
        facts[key] = sum(needle in ln for ln in lines)
    renames = [RENAME.search(ln) for ln in lines if RENAME.search(ln)]
    facts["renames"] = [(m.group(2), m.group(3)) for m in renames]
    if run_a and (not renames or renames[-1].group(2) != "Mod Manager"
                  or renames[-1].group(3) != "0"):
        problems.append("the main menu button's caption was not set to 'Mod Manager': %r"
                        % facts["renames"])
    if run_a and facts["notice_window"] == 0:
        problems.append("no '[qm] ui show restart notice': the confirmed Apply did not show it")
    compile_errors = [ln for ln in lines if OWN_STATES.search(ln)]
    missed = [ln for ln in lines if MISSED.search(ln)]
    added = {}
    for ln in lines:
        m = ADDED.search(ln)
        if m:
            added[m.group(1)] = added.get(m.group(1), 0) + 1
    ready = [READY.search(ln) for ln in lines if READY.search(ln)]
    shows = [int(SHOW.search(ln).group(1)) for ln in lines if SHOW.search(ln)]
    closed = [int(CLOSES.search(ln).group(1)) for ln in lines if CLOSES.search(ln)]
    present = sum("[qm] ui ensure: screens present" in ln for ln in lines)
    gone = [k for k, ln in enumerate(lines) if "[qm] ui ensure: screens gone" in ln]
    # Every ERROR line of that DoCreate before `screens gone`: from the last
    # `...DoCreate started...` line before it (or the log's start).
    gone_errors = []
    for k in gone:
        top = next((t for t in range(k - 1, -1, -1) if "...DoCreate started..." in lines[t]), -1)
        gone_errors += [ln for ln in lines[top + 1:k] if ln.startswith("ERROR")]
    facts.update(compile_errors=len(compile_errors), missed_lookups=len(missed),
                 gone=len(gone), gone_errors=len(gone_errors),
                 added=added, shows=len(shows), closes=max(closed or [0]),
                 present_checks=present,
                 last_ready=ready[-1].group(0) if ready else None)
    if compile_errors:
        problems.append("compile errors: %s" % compile_errors)
    if missed:
        problems.append("%d IndexOfState lines for the window's states, expected none: %s"
                        % (len(missed), missed))
    if gone_errors:
        problems.append("%d ERROR lines in the DoCreate before a 'screens gone' line, expected none: %s"
                        % (len(gone_errors), gone_errors))
    if len(gone) != battles:
        problems.append("%d 'screens gone' lines, expected %d (one per return from a battle)"
                        % (len(gone), battles))
    for name in WINDOW_STATES:
        if added.get(name, 0) != 1 + battles:
            problems.append("%s added %d times, expected %d" % (name, added.get(name, 0),
                                                                1 + battles))
    if not ready or ready[-1].group(1) != "1" or int(ready[-1].group(2)) != 1 + battles:
        problems.append("last ensure line %r, expected ready=1 adds=%d"
                        % (facts["last_ready"], 1 + battles))
    if present == 0:
        problems.append("no 'screens present' line: no DoCreate found the states silently")
    bad = [w for w in shows if w != 1]
    if not shows or bad:
        problems.append("%d show lines, windows other than 1: %s" % (len(shows), bad))
    if facts["closes"] < closes:
        problems.append("the window was closed %d times, expected at least %d"
                        % (facts["closes"], closes))
    return problems, facts


def check(run_dir, cycles=CYCLES, toggle=TOGGLE, out=print):
    out_dir = os.path.join(run_dir, "qm_test_out")
    dump, done = _read(os.path.join(out_dir, DUMP_FILE)), _read(os.path.join(out_dir, "done.txt"))
    if dump is None or done is None:
        out("incomplete: %s or done.txt missing under %s" % (DUMP_FILE, out_dir))
        return 2
    problems = S.ui_check(S.parse_dump(dump), cycles, toggle)
    want_done = S.done_expected([(CASE_FILE.encode("ascii"), b"ui")])
    if S.dump_lines(done) != want_done:
        problems.append("done.txt %r, expected %r" % (S.dump_lines(done), want_done))
    log, facts = log_problems(run_logs(run_dir), battles=0, closes=cycles + 1, run_a=True)
    problems += log
    out("facts: %s" % facts)
    for p in problems:
        out("DIFF " + p)
    out("ui run A: %s" % ("OK" if not problems else "%d difference(s)" % len(problems)))
    return 0 if not problems else 1


def main(argv=None, out=print):
    p = argparse.ArgumentParser(prog="m6cases.py", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("case")
    c.add_argument("--out", required=True)
    c.add_argument("--i9", action="store_true")
    for q in (c, sub.add_parser("check")):
        q.add_argument("--cycles", type=int, default=CYCLES)
        q.add_argument("--toggle", default=TOGGLE.decode("ascii"))
    lg = sub.add_parser("log")
    lg.add_argument("--battles", type=int, default=1)
    lg.add_argument("--closes", type=int, default=0)
    pl = sub.add_parser("plan")
    pl.add_argument("--i9", action="store_true", required=True)
    pl.add_argument("--out", required=True)
    pl.add_argument("--logs", required=True)
    i9 = sub.add_parser("i9check")
    i9.add_argument("--fixtures-dir", default=None)
    for q in (sub.choices["check"], lg, i9):
        q.add_argument("run")
    a = p.parse_args(argv)
    if a.cmd == "case":
        os.makedirs(a.out, exist_ok=True)
        files = (i9_case_files(a.toggle.encode("ascii")) if a.i9 else
                 {CASE_FILE: case_bytes(a.cycles, a.toggle.encode("ascii"))})
        for name, data in sorted(files.items()):
            path = os.path.join(a.out, name)
            with open(path, "wb") as fh:
                fh.write(data)
            out("wrote %s" % path)
        return 0
    if a.cmd == "plan":
        s = i9_scenario(a.out, a.logs)
        out("Run I9 (after `python tools/fixtures.py` and `python tools/m6cases.py case --i9 "
            "--out %s`):" % a.out)
        out("   " + m5cases.command(s, a.out, a.logs, prefix="m6"))
        out("   expect: %d restart(s), %d log(s); then python tools/m6cases.py i9check %s"
            % (s.restarts, s.restarts + 1, os.path.join(a.logs, "m6" + s.name)))
        for k, want in enumerate(s.lives, 1):
            out("   log %d: %s" % (k, "; ".join(want)))
        return 0
    if a.cmd == "i9check":
        return i9_check(a.run, fixtures_dir=a.fixtures_dir, out=out)
    if a.cmd == "check":
        return check(a.run, a.cycles, a.toggle.encode("ascii"), out)
    lines = run_logs(a.run)
    if not lines:
        out("incomplete: no cos_*.log in %s" % a.run)
        return 2
    problems, facts = log_problems(lines, a.battles, a.closes)
    out("facts: %s" % facts)
    for pr in problems:
        out("DIFF " + pr)
    out("ui log: %s" % ("OK" if not problems else "%d difference(s)" % len(problems)))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
