r"""Phase B in-game runs of the data merge (M9; plan S3, S10).

    python tools/m9cases.py case --out DIR
        write DIR\qm_case_data.cfg (the `data` SelfTest case,
        src/states/qmcasedata.pas) and DIR\qm_m5_restart.cfg (lets the run
        restart once, so the life after the merge reads the merged files)
    python tools/m9cases.py check merged RUN
        run A: QMTestDataA + QMTestDataB merged
    python tools/m9cases.py check bound RUN
        run B: QMTestDataA6 + QMTestDataB6 past the formation bound

RUN is an hrun run folder (tools/hrun.py): qm_test_out\ (the case's dumps,
one per life), the game logs and qm_mod\ (Quartermaster's folder as the run
left it). Exit status 0 when everything holds, 1 when something differs,
2 when the output is missing.

Run A: the first life generates - formations.cfg and objcustom.cfg merged by
records, validated, written - and restarts; the last life's case dump reads,
through the engine's parser and the mod overlay, 151 formations with both
added ones and both decal changes (ausbar 17.0, swetem 21).
Run B: the merge of formations.cfg fails its bound (161 > 160) and writes
nothing; the game reads B6's file, the winner's: 155 formations, B6's six;
its loader logs no "greater then gc_formation_maxcount".
"""
import argparse
import glob
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [REPO, os.path.join(REPO, "tools")]

import m5cases  # noqa: E402
from ref import selftest as S  # noqa: E402

CASE = "qm_case_data.cfg"
RESTART_CASE = "qm_m5_restart.cfg"


def case_files():
    return {CASE: S.render_case(b"data", []),
            RESTART_CASE: m5cases.case_bytes(RESTART_CASE)}


def dumps(run):
    out = {}
    for path in glob.glob(os.path.join(run, "qm_test_out", "qm_case_data_*.txt")):
        life = int(os.path.basename(path)[len("qm_case_data_"):-4])
        with open(path, "rb") as fh:
            out[life] = [ln for ln in fh.read().replace(b"\r", b"").split(b"\n") if ln]
    return out


def log_text(run):
    text = b""
    for path in sorted(glob.glob(os.path.join(run, "*.log"))):
        with open(path, "rb") as fh:
            text += fh.read()
    return text


def check(kind, run):
    d = dumps(run)
    if not d:
        print("no dump in %s" % run)
        return 2
    last = d[max(d)]
    text = log_text(run)
    problems = []
    if b"Compile script error" in text:
        problems.append("log: Compile script error")
    if b"greater then gc_formation_maxcount" in text:
        problems.append("log: the formation loader refused the file")
    mod = os.path.join(run, "qm_mod", "data", "game", "var")
    if kind == "merged":
        want = [b"formations|151|1|1|0|0", b"objcustom|244|17.0|21"]
        for w in (b"data merge game\\var\\formations.cfg parts=2 records=151 status=OK",
                  b"data merge game\\var\\objcustom.cfg parts=2 records=244 status=OK",
                  b"write data game\\var\\formations.cfg result=1",
                  b"write data game\\var\\objcustom.cfg result=1"):
            if w not in text:
                problems.append("log: no %r" % w.decode())
        for f in ("formations.cfg", "objcustom.cfg"):
            if not os.path.isfile(os.path.join(mod, f)):
                problems.append("qm_mod: no merged %s" % f)
    else:
        want = [b"formations|155|0|0|0|6"]
        w = (b"data merge game\\var\\formations.cfg parts=2 records=161 status=FAIL "
             b"161 records, the game loads none above 160")
        if w not in text:
            problems.append("log: no %r" % w.decode())
        if os.path.isfile(os.path.join(mod, "formations.cfg")):
            problems.append("qm_mod: a formations.cfg was written")
    for w in want:
        if w not in last:
            problems.append("last life %d: no %r" % (max(d), w.decode()))
    for life in sorted(d):
        for ln in d[life]:
            print("  life %d: %s" % (life, ln.decode("latin-1")))
    for p in problems:
        print("FAIL " + p)
    print("m9 run %s: %s" % (kind, "OK" if not problems else "%d problem(s)" % len(problems)))
    return 1 if problems else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("case")
    c.add_argument("--out", required=True)
    k = sub.add_parser("check")
    k.add_argument("kind", choices=("merged", "bound"))
    k.add_argument("run")
    a = ap.parse_args(argv)
    if a.cmd == "case":
        os.makedirs(a.out, exist_ok=True)
        for name, data in case_files().items():
            with open(os.path.join(a.out, name), "wb") as fh:
                fh.write(data)
            print("wrote %s" % os.path.join(a.out, name))
        return 0
    return check(a.kind, a.run)


if __name__ == "__main__":
    sys.exit(main())
