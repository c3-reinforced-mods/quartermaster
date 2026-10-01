r"""SelfTest cases for the in-game runs, and the check of what they wrote.

    python tools/qmtest.py cases --out DIR        write the case files of M2 into DIR
    python tools/qmtest.py expected [--write]     the readdump expectation, as stored in
                                                  tests/data/m2_readdump.expected
    python tools/qmtest.py check DIR              compare a run's SelfTest output with ref/

The case files go to the game with `tools/hrun.py --case DIR\qm_case1.cfg ...`;
hrun copies the SelfTest's `<save>\qm_test\out\` into `<run folder>\qm_test_out\`,
which is the DIR `check` takes (a run folder is accepted too). Exit status of
`check`: 0 when every compared line and file is equal, 1 when something differs,
2 when the output is incomplete (no done.txt, a case that did not finish).

The cases (their format: ref/selftest.py):

  qm_case1.cfg  readdump  every vanilla .inc through the parser (its view: values
                          without trailing spaces) and through the raw reader +
                          the game's `.inc` line model; the raw reader on all
                          313 .inc and the 20 data files below, each with its
                          vanilla.idx size; a write/read-back round trip and
                          the compared form of ten files; four writes of
                          oncamera.inc through the raw `.inc` writer (0, 1, 70
                          and 76 values: each Code form, shorter, longer)
  qm_case2.cfg  incprobe  the parser on the 19 `.inc` of the `Code[*] = ` and
                          no-Code forms and 3 struct-form controls
  qm_case3.cfg  plan      mod list, index, plan, fingerprint
  qm_case4.cfg  keys      every scanned path as an encoded parser key
  qm_case5.cfg  incprobe  the synthetic parser probe (`synth`): tabs, leading
                          and trailing spaces, other bytes, four ways to append
  qm_case6.cfg  eofprobe  both integer readers at and past the end of six
                          small files
  qm_case7.cfg  bisect    which char-literal construct kept qmCaseIncProbe from
                          compiling in run m2a2 (candidates written at run time)

qm_case1 also reads the 20 data files and five `.inc` a second time without
their size (`rawh`, the handle-based reader), and eight `.inc` - the four hook
files among them - into one pool with qmIncReadAt, with qmIncHookIndex on each.

`check` compares qm_case1, qm_case2 and qm_case4 line for line and file for
file, qm_case3 with ref.selftest.plan_check (which mod provides which file is
recomputed from the folders the mods were deployed from: fixtures\ for the
QMTest mods, dist\Quartermaster for Quartermaster, the game folder for the
rest), the whole integers of qm_case6, and prints what qm_case5 and the ends
of qm_case6 found - that is what those two are for.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if REPO not in sys.path:
    sys.path.insert(0, REPO)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import hbuild  # noqa: E402
from ref import inc as I  # noqa: E402
from ref import selftest as S  # noqa: E402
from ref.index import scan_entries  # noqa: E402

GAME = hbuild.GAME
FIXTURES = os.path.join(REPO, "fixtures")
EXPECTED = os.path.join(REPO, "tests", "data", "m2_readdump.expected")

#: Twenty vanilla data files, chosen for what they exercise in the raw reader:
#: the four Phase B profiles and dmscript.global; libraries with `~` (126, always
#: escaped) and with bytes above 127, some of them in the top byte of an Integer
#: (a negative value from FileStreamReadInteger); a tab; a file of CR only
#: (read as one line); an empty file; lengths that are and are not multiples of
#: 4, with and without a final LF (where run m2a met the stale value); trailing
#: spaces.
DATA_FILES = (
    b"game\\var\\hotkeys.cfg", b"game\\var\\objcustom.cfg", b"game\\var\\formations.cfg",
    b"game\\var\\wallcustom.cfg", b"scripts\\dmscript.global", b"scripts\\lib\\init.script",
    b"scripts\\lib\\unit.script", b"locale\\po\\missions\\scemis11.txt", b"brushes\\arrow.cfg",
    b"locale\\pl\\new.txt", b"locale\\en\\style.txt", b"hud\\font.lib", b"game\\var\\random.cfg",
    b"hud\\bar.load.menu.cfg", b"video\\video.lib", b"scripts\\user\\user.aix", b"gui\\menu.cfg",
    b"animations\\aaf\\bui.aaf", b"locale\\uk\\missions\\scemis7.txt", b"resources\\servers.dat")

#: Written back and read again (`rt`), and written in the compared form (`norm`).
ROUND_TRIP = (
    b"brushes\\arrow.cfg", b"hud\\bar.load.menu.cfg", b"hud\\font.lib", b"game\\var\\random.cfg",
    b"video\\video.lib", b"animations\\aaf\\bui.aaf", b"locale\\po\\missions\\scemis11.txt",
    b"game\\var\\hotkeys.cfg", b"gui\\menu.inc\\oncamera.inc",
    b"gui\\menu.inc\\eventcustomgame.inc")

#: Writes through the raw `.inc` writer: oncamera.inc has 73 values, so 0 is the
#: no-Code form, 1 the `Code[*] = ` form, 70 a shorter struct, 76 a longer one
#: (the parser could only have appended one line).
INC_WRITES = ((b"gui\\menu.inc\\oncamera.inc", 0), (b"gui\\menu.inc\\oncamera.inc", 1),
              (b"gui\\menu.inc\\oncamera.inc", 70), (b"gui\\menu.inc\\oncamera.inc", 76))

#: Struct-form controls for incprobe: engine layout, one value in a struct
#: without final CRLF (the parser writes it as `Code[*] = `), the one five-space
#: indent (ref's census).
PROBE_CONTROLS = (b"gui\\menu.inc\\oncamera.inc", b"scripts\\units\\global.inc\\onafterload.inc",
                  b"gui\\menu.inc\\eventcustomgame.inc")

#: Read again without their size: the handle reader must give the same lines.
RAWH_INC = (b"gui\\common.inc\\onmousewheel.inc", b"gui\\menu.inc\\doprogress.inc",
            b"gui\\menu.inc\\oncamera.inc", b"gui\\menu.inc\\eventhud.inc",
            b"scripts\\units\\global.inc\\onafterload.inc")

#: Into one pool with qmIncReadAt: the four hook files, a struct with trailing
#: spaces, the five-space indent, a `Code[*] = ` file and a Code-less one.
INCAT_FILES = (b"gui\\menu.inc\\cameracontrol.inc", b"gui\\menu.inc\\initminimap.inc",
               b"gui\\menu.inc\\doprogress.inc", b"gui\\menu.inc\\eventmainmenu.inc",
               b"scripts\\env\\env.inc\\doextract.inc", b"gui\\menu.inc\\eventcustomgame.inc",
               b"gui\\menu.inc\\initprofile.inc", b"gui\\menu.inc\\eventhud.inc")

#: The bisect candidates: one construct each, between the two flags.
BISECT = (
    ("qmBsControl", [b"var qmBsA : Integer = 1;"]),
    ("qmBsCharOne", [b"var qmBsA : String = #9;"]),
    ("qmBsCharPlus", [b"var qmBsA : String = ';a'+#13+#10+'b';"]),
    ("qmBsCharAdj", [b"var qmBsA : String = ';a'+#13#10+'b';"]),
    ("qmBsCharPair", [b"var qmBsA : String = #13#10;"]),
    ("qmBsCharStr", [b"var qmBsA : String = 'a'#9'b';"]),
    ("qmBsLitPrefix", [b"var qmBsA : String = '      [*] = ;qc2';"]),
    ("qmBsOldLine", [b"var qmBsP : Integer = ParserCreate('qm_bs_p');",
                     b"ParserSetValueByKeyByHandle(qmBsP, '[*]', ';qc1'+#13#10+'      [*] = ;qc2');"]),
)
#: Candidates that may not compile: pass each to hrun as --expect-compile-error.
BISECT_MAY_FAIL = ("qmBsCharAdj", "qmBsCharPair", "qmBsCharStr", "qmBsOldLine")

#: eofprobe files: sizes 0, 28, 32, 64 (multiples of 4, where run m2a met the
#: stale value), 33 and 51 (a partial last Integer).
EOF_FILES = (b"hud\\bar.load.menu.cfg", b"animations\\aaf\\bui.aaf", b"hud\\font.lib",
             b"video\\video.lib", b"locale\\en\\style.txt", b"game\\var\\random.cfg")


def vanilla_reader(game_dir):
    data = os.path.join(game_dir, "data")

    def read(path):
        with open(os.path.join(data, *path.decode("ascii").split("\\")), "rb") as fh:
            return fh.read()
    return read


def idx_entries(dist_mod=hbuild.DIST_MOD):
    """vanilla.idx rows as `(path bytes, size, lines, class bytes)`."""
    with open(os.path.join(dist_mod, *hbuild.IDX_REL.split("/")), "rb") as fh:
        _header, rows = hbuild.parse_vanilla_idx(fh.read())
    return [(p.encode("ascii"), s, n, c.encode("ascii")) for p, s, n, c in rows]


def inc_forms(entries, vanilla):
    """`{path: form}` of every vanilla `.inc` in vanilla.idx."""
    return dict((e[0], I.parse(vanilla(e[0])).form) for e in entries
                if e[0].endswith(b".inc"))


def m2_cases(entries, vanilla):
    """`{file name: bytes}` of the six M2 case files."""
    size = dict((e[0], b"%d" % e[1]) for e in entries)
    forms = inc_forms(entries, vanilla)
    incs = sorted(forms)
    read = [(b"inc", p) for p in incs]
    read += [(b"incraw", p, size[p]) for p in incs]
    read += [(b"raw", p, size[p]) for p in incs + list(DATA_FILES)]
    read += [(b"rt", p, b"rt%d.txt" % k, size[p]) for k, p in enumerate(ROUND_TRIP)]
    read += [(b"norm", p, b"norm%d.txt" % k, size[p]) for k, p in enumerate(ROUND_TRIP)]
    read += [(b"incw", p, b"incw%d.inc" % k, b"%d" % n, size[p])
             for k, (p, n) in enumerate(INC_WRITES)]
    read += [(b"rawh", p) for p in list(DATA_FILES) + list(RAWH_INC)]
    read += [(b"incat", p, size[p]) for p in INCAT_FILES] + [(b"incatend",)]
    probes = [(b"probe", p) for p in incs if forms[p] != "struct"]
    probes += [(b"probe", p) for p in PROBE_CONTROLS]
    return {"qm_case1.cfg": S.render_case(b"readdump", read),
            "qm_case2.cfg": S.render_case(b"incprobe", probes),
            "qm_case3.cfg": S.render_case(b"plan", []),
            "qm_case4.cfg": S.render_case(b"keys", []),
            "qm_case5.cfg": S.render_case(b"incprobe", [S.synth_directive(b"synth0.inc")]),
            "qm_case6.cfg": S.render_case(b"eofprobe", [(b"file", p, size[p])
                                                        for p in EOF_FILES]),
            "qm_case7.cfg": S.render_case(b"bisect", bisect_directives())}


def bisect_directives():
    """One small .aix per candidate, then the state: a candidate that does not
    compile takes nothing else with it."""
    flag = b"ParserSetIntValueByKeyByHandle(ParserSelectByKey('qm_case_rt'), '%s', 1);"
    out = []
    for k, (name, code) in enumerate(BISECT):
        aix = hbuild.assemble_aix([(name.encode(), [flag % b"bs_ran"] + code + [flag % b"bs_done"])])
        out.append((b"aix", b"bisect%d.aix" % k, S.synth_directive(b"", aix)[2]))
        out.append((b"state", name.encode()))
    return out


def readdump_expectation(entries, vanilla):
    kind, directives = S.parse_case(m2_cases(entries, vanilla)["qm_case1.cfg"])
    return S.readdump_expected(directives, vanilla)


# ------------------------------------------------------------------ check
def _read(path):
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def _roots(game_dir, fixtures_dir, dist_mod):
    def root_of(d):
        text = d.decode("latin-1").replace("/", "\\").rstrip("\\")
        if text.lower().startswith("mods\\"):
            name = text[5:]
            if name.lower() == hbuild.MOD_NAME.lower():
                return dist_mod
            if os.path.isdir(os.path.join(fixtures_dir, name)):
                return os.path.join(fixtures_dir, name)
        path = os.path.normpath(os.path.join(game_dir, text))
        return path if os.path.isdir(path) else None
    return root_of


def check(out_dir, game_dir=GAME, fixtures_dir=FIXTURES, dist_mod=hbuild.DIST_MOD, out=print):
    """Compare a SelfTest out folder with ref/. Returns the exit status."""
    if os.path.isdir(os.path.join(out_dir, "qm_test_out")):
        out_dir = os.path.join(out_dir, "qm_test_out")
    vanilla = vanilla_reader(game_dir)
    entries = idx_entries(dist_mod)
    cases = m2_cases(entries, vanilla)
    done = _read(os.path.join(out_dir, "done.txt"))
    if done is None:
        out("no done.txt in %s: the SelfTest did not finish" % out_dir)
        return 2
    rows = S.parse_dump(done)
    ran = dict((r[1], (r[2], r[3])) for r in rows if r[0] == b"case")
    out("done.txt: %s" % b" ".join(b"|".join(r) for r in rows).decode("latin-1"))
    problems = 0
    incomplete = False
    for name in sorted(cases):
        key = name.encode("ascii")
        if key not in ran:
            continue
        kind, status = ran[key]
        stem = name[:-4]
        dump = _read(os.path.join(out_dir, stem + ".txt"))
        if status != b"ok" or dump is None:
            out("%s (%s): status %s, dump %s" % (name, kind.decode(), status.decode(),
                                                  "missing" if dump is None else "present"))
            incomplete = True
            if dump is None:
                continue
        _kind, directives = S.parse_case(cases[name])
        if kind == b"readdump":
            problems += _check_readdump(out_dir, dump, directives, vanilla, out)
        elif kind == b"incprobe":
            problems += _check_incprobe(name, out_dir, dump, directives, vanilla, out)
        elif kind == b"eofprobe":
            problems += _check_eofprobe(dump, directives, vanilla, out)
        elif kind == b"bisect":
            _report_bisect(dump, out)
        elif kind == b"plan":
            root_of = _roots(game_dir, fixtures_dir, dist_mod)
            shipped = [hbuild._vanilla_rel(h.into) for h in hbuild.load_hooks()]
            bad, notes = S.plan_check(S.parse_dump(dump), entries, root_of, shipped,
                                      hbuild.QM_VERSION.encode("ascii"),
                                      lambda p: os.stat(p).st_mtime)
            for line in bad:
                out("  plan: " + line)
            for line in notes[:20]:
                out("  plan note: " + line)
            out("%s (plan): %d problem(s), %d note(s)" % (name, len(bad), len(notes)))
            problems += len(bad)
        elif kind == b"keys":
            got = S.dump_lines(dump)
            want = S.keys_expected(scan_entries(entries))
            same = got == want
            out("%s (keys): %s %s" % (name, "equal" if same else "DIFFERENT",
                                      b" ".join(got).decode("latin-1")))
            problems += 0 if same else 1
    out("problems: %d%s" % (problems, ", output incomplete" if incomplete else ""))
    if incomplete:
        return 2
    return 0 if problems == 0 else 1


def _check_readdump(out_dir, dump, directives, vanilla, out):
    want_lines, want_files = S.readdump_expected(directives, vanilla)
    got = S.dump_lines(dump)
    bad = 0
    for k in range(max(len(got), len(want_lines))):
        a = got[k] if k < len(got) else b"<missing>"
        b = want_lines[k] if k < len(want_lines) else b"<missing>"
        if a != b:
            bad += 1
            if bad <= 20:
                out("  readdump line %d: game %s" % (k + 1, a.decode("latin-1")))
                out("  readdump line %d: ref  %s" % (k + 1, b.decode("latin-1")))
    whole = dump == S.dump_bytes(want_lines)
    for name, data in sorted(want_files.items()):
        got_file = _read(os.path.join(out_dir, name.decode("ascii")))
        if got_file != data:
            bad += 1
            out("  readdump file %s: %s" % (name.decode(), "missing" if got_file is None
                                             else "%d bytes, ref %d" % (len(got_file), len(data))))
    out("qm_case1 (readdump): %d lines, %d files, %d difference(s); dump file %s"
        % (len(want_lines), len(want_files), bad,
           "byte-identical" if whole else "NOT byte-identical"))
    return bad + (0 if whole else 1)


def _check_incprobe(name, out_dir, dump, directives, vanilla, out):
    predicted = S.incprobe_expected(directives, vanilla)
    rows = S.parse_dump(dump)
    probe_rows = dict((r[1], r) for r in rows if r[0] == b"probe")
    bad = 0
    for k, (d, want) in enumerate(zip(directives, predicted)):
        if want is None:
            _report_synth(out_dir, d, rows, out)
            continue
        path, form, row, rt, ed = want
        got_row = probe_rows.get(b"%d" % k)
        rt_name, ed_name = S.probe_names(k)
        got_rt = _read(os.path.join(out_dir, rt_name.decode()))
        got_ed = _read(os.path.join(out_dir, ed_name.decode()))
        same = (got_row == tuple(row), got_rt == rt, got_ed == ed)
        bad += same.count(False)
        verdict = "equal" if all(same) else "DIFFERENT (row %s, round trip %s, edit %s)" % tuple(
            "ok" if x else "differs" for x in same)
        out("  probe %d %s (%s): %s" % (k, path.decode(), form, verdict))
        if not all(same):
            out("    game row %s" % (b"|".join(got_row).decode("latin-1") if got_row else None))
            out("    ref  row %s" % b"|".join(row).decode("latin-1"))
            out("    rt.inc:   %r" % got_rt)
            out("    ed.inc:   %r" % got_ed)
    probes = sum(1 for w in predicted if w is not None)
    out("%s (incprobe): %d probe(s), %d difference(s) from ref/inc.py" % (name, probes, bad))
    return bad


def _report_synth(out_dir, d, rows, out):
    """What the parser did with the synthetic file: reported, not judged."""
    name = d[1]
    stem = name.split(b".")[0].decode()
    out("  synth %s, written as %r" % (name.decode(), S.SYNTH))
    for r in rows:
        if r[0].startswith(b"synth") and r[1] == name:
            if r[0] == b"synth":
                values = [S.unhex(v) for v in r[5].split(b";")] if r[5] else []
                out("    parser: root %s, Code found %s, %s values: %r"
                    % (r[2].decode(), r[3].decode(), r[4].decode(), values))
            else:
                out("    %s: count after %s" % (r[0].decode(), r[2].decode()))
    for suffix in ("rt", "a", "c", "d", "b"):
        data = _read(os.path.join(out_dir, "%s_%s.inc" % (stem, suffix)))
        out("    %s_%s.inc: %r" % (stem, suffix, data))


def _report_bisect(dump, out):
    """Which candidates compiled: reported, not judged (that is the question)."""
    for r in S.parse_dump(dump):
        if r[0] == b"bisect":
            ran = r[2] == b"1"
            out("  bisect %-14s %s" % (r[1].decode(), "compiled and ran" if ran and r[3] == b"1"
                                         else "compiled, stopped" if ran
                                         else "DID NOT COMPILE (or its file did not load)"))
        elif r[0] == b"aix":
            out("  bisect loaded %s into manager %s" % (r[1].decode(), r[2].decode()))


def _check_eofprobe(dump, directives, vanilla, out):
    rows = S.parse_dump(dump)
    bad = 0
    for path, size, ints in S.eofprobe_expected(directives, vanilla):
        for tag in (b"eofs", b"eofh"):
            row = next((r for r in rows if r[0] == tag and r[1] == path), None)
            if row is None:
                out("  %s %s: missing (the reads stopped the state?)" % (tag.decode(),
                                                                        path.decode()))
                continue
            got = [int(v) for v in row[-1].split(b";")] if row[-1] else []
            head_ok = got[:len(ints)] == ints
            bad += 0 if head_ok else 1
            out("  %s %s (%d bytes): whole integers %s; the rest %s%s"
                % (tag.decode(), path.decode(), size, "as in the file" if head_ok else "DIFFER",
                   ["0x%08X" % (v & 0xFFFFFFFF) for v in got[len(ints):]],
                   "; handle %s" % row[3].decode() if tag == b"eofh" else ""))
    return bad


# -------------------------------------------------------------------- CLI
def main(argv=None, out=print):
    p = argparse.ArgumentParser(prog="qmtest.py", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("cases")
    c.add_argument("--out", required=True)
    c.add_argument("--game-dir", default=GAME)
    e = sub.add_parser("expected")
    e.add_argument("--write", action="store_true")
    e.add_argument("--game-dir", default=GAME)
    k = sub.add_parser("check")
    k.add_argument("dir")
    k.add_argument("--game-dir", default=GAME)
    k.add_argument("--fixtures-dir", default=FIXTURES)
    k.add_argument("--dist", default=hbuild.DIST_MOD)
    a = p.parse_args(argv)
    vanilla = vanilla_reader(a.game_dir)
    if a.cmd == "cases":
        os.makedirs(a.out, exist_ok=True)
        for name, data in sorted(m2_cases(idx_entries(), vanilla).items()):
            with open(os.path.join(a.out, name), "wb") as fh:
                fh.write(data)
            out("wrote %s (%d bytes)" % (os.path.join(a.out, name), len(data)))
        return 0
    if a.cmd == "expected":
        lines, files = readdump_expectation(idx_entries(), vanilla)
        data = b"".join(line + b"\n" for line in lines)
        if a.write:
            os.makedirs(os.path.dirname(EXPECTED), exist_ok=True)
            with open(EXPECTED, "wb") as fh:
                fh.write(data)
            out("wrote %s: %d lines" % (EXPECTED, len(lines)))
        else:
            for line in lines:
                out(line.decode("latin-1"))
        return 0
    return check(a.dir, a.game_dir, a.fixtures_dir, a.dist, out)


if __name__ == "__main__":
    sys.exit(main())
