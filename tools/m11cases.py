r"""Phase B in-game run of Create mod / Create about.cfg / Edit game file (M11).

    python tools/m11cases.py case --out DIR
        write DIR\qm_case_mod.cfg (the `mod` SelfTest case,
        src/states/qmcasemod.pas) and DIR\qm_m5_restart.cfg
    python tools/m11cases.py check RUN
        the dumps of both lives, the new mod's files against ref/createmod.py
    python tools/m11cases.py case --own --out DIR
    python tools/m11cases.py check --own RUN
        the run of a folder made before Quartermaster's own restart (below)

The run: QMTestDataA (a local mod without about.cfg) deployed, the case in
life 1 creates mods\QMTestCreated through the New mod dialog, writes
QMTestDataA's about.cfg and copies gui\menu.inc\oncamera.inc into it, then
schedules a restart; in life 2 the game has registered the new folder and
the boot has read its about.cfg. hrun --game-created QMTestCreated collects
the folder (RUN\created\) and removes it.

The --own run (a bug found 2026-10-01: New mod, then an Apply
restart, then a FAIL "the mods changed again across Quartermaster's own
restart"): Quartermaster alone, the case in life 1 only creates
mods\QMTestFresh and restarts as Quartermaster's own restart (`own 1`: the
marker's rk). Life 2: the engine registers the folder after Quartermaster,
the boot puts itself last again and asks no restart for that - the folder
ships none of its files (ref/order.py needs_restart) - and no FAIL.
hrun --game-created QMTestFresh --until-log 2.
"""
import argparse
import glob
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [REPO, os.path.join(REPO, "tools")]

import m5cases  # noqa: E402
from ref import createmod as CM  # noqa: E402
from ref import selftest as S  # noqa: E402

CASE = "qm_case_mod.cfg"
RESTART_CASE = "qm_m5_restart.cfg"
NAME = b"QMTestCreated"
LOCAL = b"mods\\QMTestDataA"
FIND = b"oncamera"
OWN_NAME = b"QMTestFresh"

#: The --own run, life by life: lines its log must hold (`!`: must not).
#: Life 2 puts Quartermaster last past the new folder only, which ships none
#: of its files: no restart for that (ref/order.py needs_restart), so the
#: run has two lives (run nmown1 of 2026-10-01, before that rule, had a
#: third: the restart the loop rule's exception let through).
OWN_LIVES = [
    ["[qm] mod case new|1|1|1|1|QMTestFresh", "[qm] mod case restart|scheduled",
     "[qm] restart now kind=test", "![qm] boot report FAIL"],
    [" rk=test ", "[qm] known: new mod mods\\QMTestFresh",
     "[qm] fingerprint without the 1 mod(s) registered at this start ",
     "[qm] guard: mods.ini only moved Quartermaster past 1 mod(s) that ship none of its "
     "files and no file the index reads: no restart for that",
     "[qm] guard restart=False kind=- why=nothing-changed refused= ",
     "[qm] mod case registered|", "![qm] boot report FAIL", "![qm] restart now"],
]


def case_files(own=False):
    if own:
        case = S.render_case(b"mod", [(b"name", OWN_NAME), (b"own", b"1")])
    else:
        case = S.render_case(b"mod", [(b"name", NAME), (b"local", LOCAL), (b"find", FIND)])
    return {CASE: case, RESTART_CASE: m5cases.case_bytes(RESTART_CASE)}


def check_own(run):
    logs = sorted(glob.glob(os.path.join(run, "*.cos_*.log")),
                  key=lambda p: int(os.path.basename(p).split(".")[0]))
    problems = []
    if len(logs) != len(OWN_LIVES):
        problems.append("%d lives, %d expected" % (len(logs), len(OWN_LIVES)))
    for life, (path, wants) in enumerate(zip(logs, OWN_LIVES), 1):
        with open(path, "rb") as fh:
            text = fh.read().decode("latin-1")
        for w in wants:
            if w.startswith("!"):
                if w[1:] in text:
                    problems.append("life %d: has %r" % (life, w[1:]))
            elif w not in text:
                problems.append("life %d: no %r" % (life, w))
        for ln in text.splitlines():
            if "[qm] guard " in ln or "[qm] boot report " in ln or "[qm] restart now" in ln:
                print("  life %d: %s" % (life, ln[ln.index("[qm]"):]))
    created = os.path.join(run, "created", OWN_NAME.decode())
    for rel, data in CM.files(OWN_NAME, OWN_NAME).items():
        path = os.path.join(created, *rel.decode().split("\\"))
        if not os.path.isfile(path):
            problems.append("created: no %s" % rel.decode())
            continue
        with open(path, "rb") as fh:
            if fh.read().rstrip(b" ") != data:
                problems.append("created: %s differs from ref/createmod.py" % rel.decode())
    for p in problems:
        print("FAIL " + p)
    print("m11 own run: %s" % ("OK" if not problems else "%d problem(s)" % len(problems)))
    return 1 if problems else 0


def dumps(run):
    out = {}
    for path in glob.glob(os.path.join(run, "qm_test_out", "qm_case_mod_*.txt")):
        life = int(os.path.basename(path)[len("qm_case_mod_"):-4])
        with open(path, "rb") as fh:
            out[life] = [ln for ln in fh.read().replace(b"\r", b"").split(b"\n") if ln.strip()]
    return out


def check(run):
    d = dumps(run)
    if len(d) < 2:
        print("dumps of %d life/lives in %s; two expected" % (len(d), run))
        return 2
    first, last = d[min(d)], d[max(d)]
    problems = []
    for w in (b"new|1|1|1|1|" + NAME, b"about|1|1", b"restart|scheduled"):
        if w not in first:
            problems.append("life %d: no %r" % (min(d), w.decode()))
    copy = [ln for ln in first if ln.startswith(b"copy|")]
    if not copy or not copy[0].startswith(b"copy|1|gui\\menu.inc\\oncamera.inc|1|"):
        problems.append("life %d: the copy is not vanilla's oncamera.inc: %r" % (min(d), copy))
    reg = [ln for ln in last if ln.startswith(b"registered|")]
    if not reg or not reg[0].endswith(b"|1|" + NAME.lower()):
        problems.append("life %d: the new mod is not registered and enabled with its id: %r"
                        % (max(d), reg))
    created = os.path.join(run, "created", NAME.decode())
    want = CM.files(NAME, NAME)
    for rel, data in want.items():
        path = os.path.join(created, *rel.decode().split("\\"))
        if not os.path.isfile(path):
            problems.append("created: no %s" % rel.decode())
            continue
        with open(path, "rb") as fh:
            got = fh.read()
        if got.rstrip(b" ") != data:
            problems.append("created: %s differs from ref/createmod.py" % rel.decode())
    for life in sorted(d):
        for ln in d[life]:
            print("  life %d: %s" % (life, ln.decode("latin-1")))
    for p in problems:
        print("FAIL " + p)
    print("m11 run: %s" % ("OK" if not problems else "%d problem(s)" % len(problems)))
    return 1 if problems else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("case")
    c.add_argument("--out", required=True)
    c.add_argument("--own", action="store_true")
    k = sub.add_parser("check")
    k.add_argument("run")
    k.add_argument("--own", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "case":
        os.makedirs(a.out, exist_ok=True)
        for name, data in case_files(a.own).items():
            with open(os.path.join(a.out, name), "wb") as fh:
                fh.write(data)
            print("wrote %s" % os.path.join(a.out, name))
        return 0
    return check_own(a.run) if a.own else check(a.run)


if __name__ == "__main__":
    sys.exit(main())
