r"""Phase B in-game runs of the manager window: the about.cfg rules (M8) and
the Options view with its key capture (M10).

    python tools/m10cases.py case --out DIR
        write DIR\qm_case_opt.cfg, the `opt` SelfTest case (src/states/qmcaseopt.pas)
    python tools/m10cases.py check RUN
        run A: the case's dump and the log rules below
    python tools/m10cases.py keys RUN
        run B: the next start with run A's settings.cfg - the keys the fixture
        registered, before and after Quartermaster's boot

RUN is an hrun run folder (tools/hrun.py): `qm_test_out\` (the SelfTest's
output), the copied game logs (`<n>.cos_*.log`) and `qm_save\` (the run's
<save>\quartermaster as it ended). Exit status 0 when everything holds, 1
when something differs, 2 when the output is missing.

Run A: QMTestWASD2 and QMTestCam2 (tools/fixtures.py), both enabled by the
harness, Quartermaster as QMTestQM, the case file, an empty state seed.
  * the boot reports the camera clash of the two (qmAbRules);
  * the case: Cam2 off, then on again - refused, WASD2 takes the slot; the
    Options view of WASD2 with its four keys; Change + key J (74) - taken by
    the game's build hotkey; Q (81) - taken by a hotkey (the fixture's attack,
    or the player's saved hotkeys.cfg, which the game reads first); Escape (27)
    - the old key stays; Y (89) - taken; Accept;
  * the fixture's RegisterShortcuts logs its keys: Y D W S when
    Quartermaster registered the shortcuts again after Accept (the start's own
    registration runs after Quartermaster's boot, run m10a);
  * qmTick saves settings.cfg on the next main-menu frame.
The keys come from the fixture's files: every letter but A, D, S, W and Y is
bound in its hotkeys.cfg to an action that is not an event one.

More than 32 settings and the groups (0.1.6), with QMTestMany alone:

    python tools/m10cases.py manycase --out DIR
        write DIR\a\qm_case_opt.cfg and DIR\b\qm_case_opt.cfg
    python tools/m10cases.py many RUN_A RUN_B
        run A: the Options view of 40 settings in five groups - a group
        picked in the list, a search, all settings and their pages; setting
        33 switched and setting 1 stepped by their buttons' tags, Accept, the
        file saved; run B: the next start with run A's state - the values
        read back from settings.cfg
"""
import argparse
import glob
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from ref import selftest as S  # noqa: E402

CASE = "qm_case_opt.cfg"
DUMP = "qm_case_opt.txt"
MOD = b"mods\\QMTestWASD2"
CLASH = b"mods\\QMTestCam2"
#: The key names are GetKeyNameByCode's, as run m10a logged them (Escape is ESCAPE).
KEYS = ((74, b"J"), (81, b"Q"), (27, b"ESCAPE"), (89, b"Y"))

EXPECTED = [
    b"rows|<mod>|<clash>|1|4",
    b"status|mod|FAIL|about|QMTestCam2 and QMTestWASD2 both take the camera slot; only one can be active",
    b"status|clash|OK",
    b"rule|deactivate|0",
    b"rule|activate|0|Not activated: QMTestCam2 and QMTestWASD2 both take the camera slot; only one can be active.",
    b"opt|2|4|A|D|W|S",
    b"cap|74|0|-1|A|Key J not taken: the game's hotkey build|%nat%tem uses it.",
    b"cap|81|0|-1|A|Key Q not taken: the game's hotkey ",
    b"cap|27|0|-1|A|Key not changed.",
    b"cap|89|0|-1|Y|",
    b"acc|0|Options saved: 1 changed.|1|1|Y",
    b"end|0",
]


def case_bytes():
    directives = [(b"mod", MOD), (b"clash", CLASH)]
    directives += [(b"key", b"%d" % code) for code, _name in KEYS]
    directives.append((b"accept", b"1"))
    return S.render_case(b"opt", directives)


def read_logs(run):
    out = []
    for path in sorted(glob.glob(os.path.join(run, "*.log"))):
        with open(path, "rb") as fh:
            out.append((os.path.basename(path), fh.read().splitlines()))
    return out


def dump_lines(run):
    path = os.path.join(run, "qm_test_out", DUMP)
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        return [ln for ln in fh.read().replace(b"\r", b"").split(b"\n") if ln]


def check_dump(lines):
    """Problems of the case's dump against EXPECTED; `rows` and `status|clash`
    are matched by their fixed parts (rows depend on mods.ini)."""
    problems = []
    got = [ln for ln in lines if not ln.startswith((b"ensure|", b"selectvia|"))]
    if not any(ln.startswith(b"ensure|1|") for ln in lines):
        problems.append("the window's screens were not ready")
    for want in EXPECTED:
        if want.startswith(b"rows|"):
            hit = [g for g in got if g.startswith(b"rows|")]
            ok = bool(hit) and hit[0].split(b"|")[3:] == [b"1", b"4"] and \
                all(int(x) >= 0 for x in hit[0].split(b"|")[1:3])
        elif want.startswith(b"cap|81|"):
            # Q is bound by whichever hotkeys.cfg is in effect: the fixture's
            # unit|attack, or the player's saved file (this machine's binds
            # interface|viewcollision) - which the game reads first.
            ok = any(g.startswith(want) and g.endswith(b" uses it.") for g in got)
        elif want == b"status|clash|OK":
            # a mod the player has not seen before reads NEW (qmKnown)
            ok = any(g.startswith((b"status|clash|OK|", b"status|clash|NEW|")) for g in got)
        else:
            ok = want in got
        if not ok:
            problems.append("dump: missing %r" % want.decode("latin-1"))
    return problems


def check_logs(logs):
    problems = []
    text = [ln for _n, lines in logs for ln in lines]
    joined = b"\n".join(text)
    for bad in (b"Compile script error", b"Error compiling scripts"):
        if bad in joined:
            problems.append("log: %s" % bad.decode())
    # The start's own RegisterShortcuts runs after Quartermaster's boot (run
    # m10a: no QMTEST line before the case), so the first registration may
    # already be the one after Accept.
    wants = [b"QMTEST wasd2 keys Y D W S",
             b"[qm] ui shortcuts registered again after new keys, reregs=1",
             b"[qm] tick: settings saved=True",
             b"both take the camera slot; only one can be active."]
    for code, name in KEYS:
        wants.append(b"[qm] ui key capture code=%d name=%s" % (code, name))
    for w in wants:
        if w not in joined:
            problems.append("log: no %r" % w.decode("latin-1"))
    return problems


def check(run):
    lines = dump_lines(run)
    if lines is None:
        print("no dump %s in %s" % (DUMP, run))
        return 2
    problems = check_dump(lines) + check_logs(read_logs(run))
    for p in problems:
        print("FAIL " + p)
    for ln in lines:
        print("  " + ln.decode("latin-1"))
    print("m10 run A: %s" % ("OK" if not problems else "%d problem(s)" % len(problems)))
    return 1 if problems else 0


def keys(run):
    """Run B: the next start with run A's settings file."""
    logs = read_logs(run)
    if not logs:
        print("no logs in %s" % run)
        return 2
    text = b"\n".join(ln for _n, lines in logs for ln in lines)
    problems = []
    for w in (b"QMTEST wasd2 keys Y D W S", b"[qm] settings loaded=1 mods=1"):
        if w not in text:
            problems.append("log: no %r" % w.decode())
    if b"QMTEST wasd2 keys A D W S" in text:
        problems.append("log: the fixture registered its default keys")
    for p in problems:
        print("FAIL " + p)
    print("m10 run B: %s" % ("OK" if not problems else "%d problem(s)" % len(problems)))
    return 1 if problems else 0


# ----------------------------------------------- more than 32 settings (0.1.6)
MANY = b"mods\\QMTestMany"
MANY_GROUP = b"Past the old limit of 32"
#: The view opens on the first entry of the list of groups (the two settings
#: under no group); entry 4 is the group past the old limit, entry 5 - the
#: last - all settings: 58 rows, seven pages of nine.
MANY_A = [(b"mod", MANY), (b"val", b"33"), (b"group", b"4"), (b"page", b"1"), (b"btn", b"66"),
          (b"find", b"camera"), (b"find",), (b"group", b"5"), (b"page", b"1"), (b"page", b"1"),
          (b"page", b"-1"), (b"btn", b"3"), (b"find", b"SETTING 33"), (b"val", b"33"),
          (b"accept", b"1")]
MANY_B = [(b"mod", MANY), (b"val", b"33"), (b"val", b"1"), (b"val", b"39"),
          (b"find", b"setting 33"), (b"accept", b"1")]


def many_values(changed):
    """`id=value` of QMTestMany's forty settings, `changed` over the defaults
    (tools/fixtures.py many_about)."""
    out = []
    for k in range(40):
        default = b"3" if k % 10 == 1 else b"mid" if k % 10 == 7 else b"1"
        out.append(b"s%d=%s" % (k, changed.get(k, default)))
    return b"|".join(out)


MANY_EXPECTED = {
    "a": [b"opt|2|40|1|3|1|1",
          b"view|5|1|9|0|2|2",
          b"val|33|s33|1|1|" + MANY_GROUP,
          b"group|4|True|4|11|11|29",
          b"page|1|1|11",
          b"btn|66|0|-1|",
          b"find|camera|True|camera|9|11|20|1",
          b"find||True||11|11|29|0",
          b"group|5|True|5|40|58|0",
          b"page|1|1|58", b"page|1|2|58", b"page|-1|1|58",
          b"btn|3|2|-1|",
          b"find|SETTING 33|True|SETTING 33|1|2|33|1",
          b"val|33|s33|1|0|" + MANY_GROUP,
          b"acc|0|Options saved: 2 changed.|0|1|-",
          b"store|qmtestmany|" + many_values({33: b"0", 1: b"2"}),
          b"end|0"],
    "b": [b"opt|2|40|1|2|1|1",
          b"view|5|1|9|0|2|2",
          b"val|33|s33|0|0|" + MANY_GROUP,
          b"val|1|s1|2|2|",
          b"val|39|s39|1|1|" + MANY_GROUP,
          b"find|setting 33|True|setting 33|1|2|33|1",
          b"acc|0|Options saved: 0 changed.|0|1|-",
          b"store|qmtestmany|" + many_values({33: b"0", 1: b"2"}),
          b"end|0"],
}
MANY_LOGS = {
    "a": [b"[qm] ui options open row=", b" mod=qmtestmany settings=40 groups=5 rows=2 ",
          b"[qm] ui options view group=4 of 5 find=[] shown=11 rows=11",
          b"[qm] ui options view group=4 of 5 find=[camera] shown=9 rows=11",
          b"[qm] ui options view group=5 of 5 find=[] shown=40 rows=58",
          b"[qm] ui option s33 bool action=0 value=[0]",
          b"[qm] ui options saved mod=qmtestmany changed=2 ", b"[qm] tick: settings saved=True"],
    # every registered mod with settings counts in `mods`, enabled or not
    "b": [b"[qm] settings loaded=1 mods=", b" defaults=0 file=",
          b" mod=qmtestmany settings=40 groups=5 rows=2 stored="],
}


def many_check(run, step):
    """Problems of run `step` (a or b) of the many-settings pair."""
    lines = dump_lines(run)
    if lines is None:
        return ["%s: no dump %s in %s" % (step, DUMP, run)]
    problems = []
    if not any(ln.startswith(b"ensure|1|") for ln in lines):
        problems.append("%s: the window's screens were not ready" % step)
    if not any(ln.startswith(b"rows|") and ln.endswith(b"|-1|1|40") for ln in lines):
        problems.append("%s: dump: no rows line with 40 settings" % step)
    # each expected line once, in any place
    want, got = list(MANY_EXPECTED[step]), list(lines)
    for w in want:
        if w in got:
            got.remove(w)
        else:
            problems.append("%s: dump: missing %r" % (step, w.decode("latin-1")[:90]))
    text = b"\n".join(ln for _n, ls in read_logs(run) for ln in ls)
    for bad in (b"Compile script error", b"Error compiling scripts", b"more than"):
        if bad in text:
            problems.append("%s: log: %s" % (step, bad.decode()))
    for w in MANY_LOGS[step]:
        if w not in text:
            problems.append("%s: log: no %r" % (step, w.decode("latin-1")))
    # run A's settings.cfg is the file the next start reads: the mod's block
    # (`<id> : struct.begin`, a `key = value` line a setting, `struct.end` -
    # the layout of the files earlier runs left) holds every setting under its
    # id, the two changed ones with their new values
    if step == "a":
        path = os.path.join(run, "qm_save", "settings.cfg")
        data = open(path, "rb").read() if os.path.isfile(path) else b""
        text = [ln.strip() for ln in data.replace(b"\r", b"").split(b"\n")]
        block = []
        if b"qmtestmany : struct.begin" in text:
            at = text.index(b"qmtestmany : struct.begin") + 1
            block = text[at:text.index(b"struct.end", at)]
        if b"|".join(ln.replace(b" = ", b"=") for ln in block) != many_values({33: b"0", 1: b"2"}):
            problems.append("a: qm_save\\settings.cfg does not hold the forty values")
    return problems


def many(run_a, run_b):
    problems = many_check(run_a, "a") + many_check(run_b, "b")
    for p in problems:
        print("FAIL " + p)
    for step, run in (("a", run_a), ("b", run_b)):
        for ln in dump_lines(run) or []:
            print("  %s %s" % (step, ln.decode("latin-1")[:150]))
    print("many settings: %s" % ("OK" if not problems else "%d problem(s)" % len(problems)))
    return 1 if problems else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("case")
    c.add_argument("--out", required=True)
    k = sub.add_parser("check")
    k.add_argument("run")
    b = sub.add_parser("keys")
    b.add_argument("run")
    mc = sub.add_parser("manycase")
    mc.add_argument("--out", required=True)
    mm = sub.add_parser("many")
    mm.add_argument("run_a")
    mm.add_argument("run_b")
    a = ap.parse_args(argv)
    if a.cmd == "manycase":
        for step, directives in (("a", MANY_A), ("b", MANY_B)):
            os.makedirs(os.path.join(a.out, step), exist_ok=True)
            path = os.path.join(a.out, step, CASE)
            with open(path, "wb") as fh:
                fh.write(S.render_case(b"opt", directives))
            print("wrote %s" % path)
        return 0
    if a.cmd == "many":
        return many(a.run_a, a.run_b)
    if a.cmd == "case":
        os.makedirs(a.out, exist_ok=True)
        path = os.path.join(a.out, CASE)
        with open(path, "wb") as fh:
            fh.write(case_bytes())
        print("wrote %s" % path)
        return 0
    if a.cmd == "check":
        return check(a.run)
    return keys(a.run)


if __name__ == "__main__":
    sys.exit(main())
