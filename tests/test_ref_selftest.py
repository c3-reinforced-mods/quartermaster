"""Gates for ref.selftest (case files, dumps, expectations) and tools/qmtest.py.

The SelfTest's dumps are written by game-side code that cannot run offline, so
these tests hold the Python side to the documented formats: a dump built the
way the game side builds it (field by field, as in src/states/qmcase*.pas)
must pass the check, and a changed field must fail it."""
import os

import pytest

import hbuild
import qmtest
from conftest import DATA_DIR
from ref import fingerprint as FP
from ref import inc as I
from ref import index as X
from ref import selftest as S
from ref import textio as T

QM = b"mods\\Quartermaster"


# ------------------------------------------------------------ case files
def test_case_file_is_a_one_state_inc_in_engine_layout():
    data = S.render_case(b"readdump", [(b"raw", b"game\\var\\hotkeys.cfg"),
                                       (b"incw", b"gui\\menu.inc\\oncamera.inc", b"incw0.inc", b"70")])
    assert I.is_engine_layout(data)
    f = I.parse(data)
    assert f.name == S.CASE_STATE and f.values[0] == b";kind readdump"
    assert S.parse_case(data) == (b"readdump", [(b"raw", b"game\\var\\hotkeys.cfg"),
                                                (b"incw", b"gui\\menu.inc\\oncamera.inc",
                                                 b"incw0.inc", b"70")])


@pytest.mark.parametrize("kind, directives", [
    (b"nope", []), (b"plan", [(b"a  b",)]), (b"plan", [(b"a\tb",)]), (b"plan", [(b"x ",)])])
def test_case_file_refuses_what_the_game_could_misread(kind, directives):
    with pytest.raises(ValueError):
        S.render_case(kind, directives)


def test_parse_case_needs_a_kind_first():
    data = S.render_case(b"plan", [])
    with pytest.raises(ValueError):
        S.parse_case(data.replace(b";kind plan", b";plan"))


# ------------------------------------------------------------------ dumps
def test_dump_bytes_are_what_the_raw_writer_makes():
    lines = [b"raw|a\\b.cfg|3|1-2-3", b"x~y{z}", b""]
    data = S.dump_bytes(lines)
    body = b"raw|a\\b.cfg|3|1-2-3\r\nx~y{z}\r\n\r\n"
    assert data == body + b" " * ((-len(body)) % 4) and len(body) % 4 == 3
    # Read back exactly, the padding is one more line of spaces; dump_lines
    # drops it: no dump line ends in a space.
    assert T.read_raw_lines(data) == lines + [b" "]
    assert S.dump_lines(data) == lines
    assert S.parse_dump(data)[0] == (b"raw", b"a\\b.cfg", b"3", b"1-2-3")
    assert S.unhex(S.hexs(b"mods\\\xe9|x")) == b"mods\\\xe9|x"


def test_readdump_expectation_on_small_files():
    files = {b"a.cfg": b"one\r\ntwo \t\r\n\r\n",            # 12 bytes: mod 4, final LF
             b"b.cfg": b"\xef\xbb\xbfx\ty",                   # BOM, tab, no final LF
             b"c.inc": (b"section.begin\r\n   Name = X\r\n   Code : struct.begin\r\n"
                        b"      [*] = ;a\r\n      [*] = ;b\r\n   struct.end\r\nsection.end\r\n\r\n")}
    size = dict((k, b"%d" % len(v)) for k, v in files.items())
    directives = [(b"raw", b"a.cfg", size[b"a.cfg"]), (b"raw", b"b.cfg", size[b"b.cfg"]),
                  (b"inc", b"c.inc"), (b"incraw", b"c.inc", size[b"c.inc"]),
                  (b"rt", b"a.cfg", b"rt0.txt", size[b"a.cfg"]),
                  (b"norm", b"b.cfg", b"norm0.txt", size[b"b.cfg"]),
                  (b"incw", b"c.inc", b"w0.inc", b"1", size[b"c.inc"]),
                  (b"incw", b"c.inc", b"w1.inc", b"3", size[b"c.inc"]),
                  (b"incw", b"c.inc", b"w2.inc", b"0", size[b"c.inc"])]
    lines, out = S.readdump_expected(directives, files.__getitem__)
    raw_a = T.read_lines(files[b"a.cfg"])
    assert raw_a == [b"one", b"two ~009", b""]
    assert lines[0] == b"|".join([b"raw", b"a.cfg", b"3", S.lines_hash(raw_a),
                                  S.lines_hash([b"one", b"two", b""]),
                                  S.lines_hash([b"one", b"two"]), b"2"])
    assert lines[1].split(b"|")[6] == b"1"                  # BOM and tab normalised away
    assert lines[2] == b"inc|c.inc|2|" + S.lines_hash([b";a", b";b"])
    assert lines[3] == b"incraw|c.inc|2|1|2|" + S.lines_hash([b";a", b";b"])
    # 12 bytes read, 16 written (2 of padding), read back with that size: the
    # padding is one more line, which the compared form does not count.
    assert lines[4] == b"rt|a.cfg|rt0.txt|3|4|1|16"
    assert T.read_lines(out[b"rt0.txt"])[-1] == b"  "
    assert out[b"norm0.txt"] == T.write_file([b"x y"])
    # The .inc writer: one value is the Code[*] form, three a struct, none no
    # Code at all; each read back as the values written.
    assert out[b"w0.inc"].startswith(b"section.begin\r\n   Name = X\r\n   Code[*] = ;a\r\n")
    assert lines[6] == b"incw|c.inc|w0.inc|1|%d|1|1" % len(out[b"w0.inc"])
    assert I.values_from_lines(T.read_lines(out[b"w1.inc"]))[2] == [
        b";a", b";b", b";// qm appended 0"]
    assert out[b"w2.inc"] == T.write_file([b"section.begin", b"   Name = X", b"section.end", b""])
    for name in (b"w0.inc", b"w1.inc", b"w2.inc"):
        assert len(out[name]) % 4 == 0


def test_incprobe_predicts_every_form_as_run_m2a_saw_it(game_dir):
    read = qmtest.vanilla_reader(game_dir)
    got = S.incprobe_expected([(b"probe", b"gui\\menu.inc\\oncamera.inc"),
                               (b"probe", b"gui\\menu.inc\\initprofile.inc"),
                               (b"probe", b"gui\\menu.inc\\eventhud.inc"),
                               S.synth_directive(b"synth0.inc")], read)
    (p0, f0, row0, rt0, ed0), (_p1, f1, row1, rt1, ed1), (_p2, f2, row2, rt2, ed2), synth = got
    assert (f0, f1, f2) == ("struct", "single", "none")
    assert rt0 == read(p0) and I.parse(ed0).values[0] == b";// qm edited"
    assert I.parse(ed0).values[-1] == b";// qm appended" and len(I.parse(ed0).values) == 74
    assert row0[3:7] == [b"1", b"73", b"2", b"74"]
    # The m2a rows and files of the other two forms, as the engine wrote them.
    assert row1 == [b"probe", b"1", b"gui\\menu.inc\\initprofile.inc", b"1", b"1", b"2", b"2",
                    S.hexs(b";_control_SetGameSpeedByMode(gProfile.igamespeed, True);")]
    assert b"   Code : struct.begin\r\n      [*] = ;// qm edited\r\n" in ed1
    assert row2 == [b"probe", b"2", b"gui\\menu.inc\\eventhud.inc", b"0", b"-1", b"1", b"1", b""]
    assert ed2 == (b"section.begin\r\n   Name = EventHUD\r\n   Code.[*] = ;// qm appended\r\n"
                   b"section.end\r\n\r\n")
    assert synth is None
    assert S.probe_names(3) == (b"probe3_rt.inc", b"probe3_ed.inc")


def test_synth_directive_has_no_space_and_writes_the_synthetic_file():
    verb, name, text = S.synth_directive(b"synth0.inc")
    assert b" " not in text and T.write_file([text])[:len(S.SYNTH)] == S.SYNTH
    assert S.render_case(b"incprobe", [(verb, name, text)])


# ------------------------------------------------------------------ plan
W = b"..\\..\\workshop\\content\\333420\\"
MODS = [X.Mod(b"mods\\SW_Frontline_Protocol", False, b"0", b"SWFP", b"SW_Frontline_Protocol"),
        X.Mod(W + b"873048118", False, b"873048118", b"ZoomOut!", b""),
        X.Mod(b"mods\\QMTestWASD", True), X.Mod(b"mods\\QMTestCamSpeed", True),
        X.Mod(QM, True, b"0", b"Quartermaster", b"Quartermaster")]
ROWS = [(b"game\\var\\hotkeys.cfg", 1, 243, b"wta"),
        (b"gui\\menu.inc\\cameracontrol.inc", 1, 38, b"merge"),
        (b"gui\\menu.inc\\oncamera.inc", 1, 76, b"merge"),
        (b"textures\\x.dds", 1, -1, b"never")]
FILES = {b"mods\\QMTestWASD": [b"game\\var\\hotkeys.cfg", b"gui\\menu.inc\\oncamera.inc"],
         b"mods\\QMTestCamSpeed": [b"gui\\menu.inc\\oncamera.inc"],
         QM: [b"gui\\menu.inc\\cameracontrol.inc"]}
SHIPPED = [b"gui\\menu.inc\\cameracontrol.inc"]


def _game_plan_dump(mods, self_index, rows, age, vage, exe, fresh=()):
    """The lines qmCasePlan writes, assembled the way the game side does it;
    `fresh`: the rows qm_known marks registered at this start."""
    pos = X.canonical_positions(mods, self_index)
    idx = X.build_index(mods, self_index, rows, age, SHIPPED)
    out = []
    for i, m in enumerate(mods):
        org = X.origin(m, i == self_index)
        out.append(b"|".join([b"mod", b"%d" % i, b"%d" % pos[i], b"1" if m.enabled else b"0", org,
                              S.hexs(m.dir), S.hexs(m.tag), S.hexs(m.last), S.hexs(m.title),
                              b"12345"]))
    out.append(b"self|%d" % self_index)
    out.append(b"scan|%d|%d" % (len(idx.scanned), idx.calls))
    for p in idx.scanned:
        if p in idx.providers:
            out.append(b"|".join([b"idx", p, b";".join(b"%d" % pos[i] for i in idx.providers[p]),
                                  b";".join(b"-" if a is None else b"%d" % a
                                            for a in idx.ages[p])]))
    for i in sorted(idx.stamps, key=lambda i: pos[i]):
        out.append(b"stamp|%d|%s" % (pos[i], idx.stamps[i]))
    for p in idx.scanned:
        if p in idx.providers:
            out.append(b"vage|%s|%d" % (p, vage(p)))
    out.append(b"exe|%d" % exe)
    v = X.vanilla_stamp(idx, vage, exe)
    out.append(b"vstamp|" + v)
    from ref import planner as P
    decisions = P.plan(idx.by_dir(mods), rows, mods[self_index].dir)
    dpos = dict((m.dir, pos[i]) for i, m in enumerate(mods))
    out += P.plan_lines(decisions, dpos.get)
    text, fp = X.fingerprint(mods, self_index, idx, v, b"0.0.0")
    out += [b"fpl|" + S.hexs(line) for line in text.split(b"\n")[:-1]]
    out.append(b"fp|" + fp)
    out.append(b"fresh|" + (b";".join(b"%d" % i for i in fresh) or b"-"))
    _t, old = X.known_fingerprint(mods, self_index, idx, vage, exe, b"0.0.0", list(fresh))
    out.append(b"fpold|" + old)
    return out


def _check(lines, tmp_path):
    for d, paths in FILES.items():
        for p in paths:
            full = os.path.join(str(tmp_path), d.decode(), "data", *p.decode().split("\\"))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            open(full, "wb").close()
    os.makedirs(os.path.join(str(tmp_path), "mods", "Quartermaster", "data", "quartermaster"),
                exist_ok=True)
    open(os.path.join(str(tmp_path), "mods", "Quartermaster", "data", "quartermaster",
                      "core.aix"), "wb").close()
    rows = S.parse_dump(S.dump_bytes(lines))
    return S.plan_check(rows, ROWS, lambda d: os.path.join(str(tmp_path), d.decode()), SHIPPED,
                        b"0.0.0")


def _age(d, p):
    return 1000 + len(d) + len(p) if p in FILES.get(d, []) else -1


def test_plan_check_accepts_what_the_game_side_writes(tmp_path):
    lines = _game_plan_dump(MODS, 4, ROWS, _age, len, 777)
    problems, notes = _check(lines, tmp_path)
    assert problems == [] and notes == []
    plan = [l for l in lines if l.startswith(b"plan|")]
    # Canonical positions: ZoomOut 0 (Workshop first), CamSpeed 1, WASD 2,
    # SW_Frontline_Protocol 3, Quartermaster 4.
    assert plan == [b"plan|game\\var\\hotkeys.cfg|skip|merge-data|record-profile|2|2",
                    b"plan|gui\\menu.inc\\cameracontrol.inc|hook|hook|quartermaster-hook|4|4",
                    b"plan|gui\\menu.inc\\oncamera.inc|merge-inc|merge-inc|merge-allow-list|2|1;2"]


@pytest.mark.parametrize("field", [b"plan|", b"idx|", b"stamp|", b"fp|", b"vstamp|", b"fpold|"])
def test_plan_check_notices_a_changed_line(field, tmp_path):
    lines = _game_plan_dump(MODS, 4, ROWS, _age, len, 777)
    k = next(i for i, l in enumerate(lines) if l.startswith(field))
    lines[k] = lines[k][:-1] + (b"9" if lines[k][-1:] != b"9" else b"8")
    problems, _notes = _check(lines, tmp_path)
    assert problems, field


@pytest.mark.parametrize("fresh", [(3,), (2, 3), (1,)])
def test_plan_check_checks_the_fingerprint_without_the_fresh_mods(fresh, tmp_path):
    lines = _game_plan_dump(MODS, 4, ROWS, _age, len, 777, fresh)
    problems, _notes = _check(lines, tmp_path)
    assert problems == []
    fp = next(l for l in lines if l.startswith(b"fp|"))[3:]
    assert next(l for l in lines if l.startswith(b"fpold|"))[6:] != fp
    # A game that marked other rows fresh than its hash was made without.
    k = next(i for i, l in enumerate(lines) if l.startswith(b"fresh|"))
    lines[k] = b"fresh|0"
    problems, _notes = _check(lines, tmp_path)
    assert any("fingerprint without" in p for p in problems)


def test_plan_check_notices_a_changed_mod_row(tmp_path):
    lines = _game_plan_dump(MODS, 4, ROWS, _age, len, 777)
    k = next(i for i, l in enumerate(lines) if l.startswith(b"mod|3|"))
    f = lines[k].split(b"|")
    f[2] = b"0"                                     # another canonical position
    lines[k] = b"|".join(f)
    problems, _notes = _check(lines, tmp_path)
    assert any("canonical positions" in p for p in problems)


def test_keys_and_done_expectations():
    assert S.keys_expected([1, 2, 3]) == [b"keys|3|0|3|0|0"]
    assert S.done_expected([(b"qm_case2.cfg", b"incprobe"), (b"qm_case1.cfg", b"readdump")]) == [
        b"case|qm_case1.cfg|readdump|ok", b"case|qm_case2.cfg|incprobe|ok", b"done|2|0"]


# ---------------------------------------------------------------- qmtest
def test_m2_cases_cover_every_vanilla_inc(game_dir):
    entries = qmtest.idx_entries()
    read = qmtest.vanilla_reader(game_dir)
    cases = qmtest.m2_cases(entries, read)
    assert sorted(cases) == ["qm_case%d.cfg" % k for k in range(1, 8)]
    kind, d1 = S.parse_case(cases["qm_case1.cfg"])
    verbs = [d[0] for d in d1]
    assert kind == b"readdump"
    assert verbs.count(b"inc") == verbs.count(b"incraw") == 313
    assert verbs.count(b"raw") == 313 + 20
    assert verbs.count(b"rt") == verbs.count(b"norm") == 10 and verbs.count(b"incw") == 4
    assert verbs.count(b"rawh") == 25 and verbs.count(b"incat") == 8
    assert verbs[-1] == b"incatend"
    kind, d7 = S.parse_case(cases["qm_case7.cfg"])
    assert kind == b"bisect" and [d[0] for d in d7] == [b"aix", b"state"] * len(qmtest.BISECT)
    kind, d2 = S.parse_case(cases["qm_case2.cfg"])
    assert kind == b"incprobe" and len(d2) == 19 + 3
    kind, d6 = S.parse_case(cases["qm_case6.cfg"])
    assert kind == b"eofprobe" and len(d6) == 6
    sizes = sorted(os.path.getsize(os.path.join(DATA_DIR, *d[1].decode().split("\\"))) % 4
                   for d in d6)
    assert sizes == [0, 0, 0, 0, 1, 3]
    for d in [d for d in d1 if d[0] != b"incatend"] + d2 + d6:
        full = os.path.join(DATA_DIR, *d[1].decode().split("\\"))
        assert os.path.isfile(full), d
        if d[0] in (b"raw", b"incraw", b"file"):
            assert int(d[2]) == os.path.getsize(full), d


def test_stored_readdump_expectation_matches_the_twin(game_dir):
    """tests/data/m2_readdump.expected is what the in-game dump of qm_case1 must
    say, computed by ref/ from the installed game. Stored so a change in ref/
    or in the game shows up here before a run, and so a run can be judged by
    reading one file."""
    with open(qmtest.EXPECTED, "rb") as fh:
        stored = fh.read().replace(b"\r\n", b"\n").split(b"\n")[:-1]
    lines, files = qmtest.readdump_expectation(qmtest.idx_entries(),
                                               qmtest.vanilla_reader(game_dir))
    assert stored == lines
    assert len(lines) == 1024 and len(files) == 24


def test_check_passes_on_an_emulated_run_and_fails_on_a_changed_byte(game_dir, tmp_path):
    read = qmtest.vanilla_reader(game_dir)
    entries = qmtest.idx_entries()
    cases = qmtest.m2_cases(entries, read)
    out_dir = tmp_path / "qm_test_out"
    out_dir.mkdir()
    _kind, d1 = S.parse_case(cases["qm_case1.cfg"])
    lines, files = S.readdump_expected(d1, read)
    (out_dir / "qm_case1.txt").write_bytes(S.dump_bytes(lines))
    for name, data in files.items():
        (out_dir / name.decode()).write_bytes(data)
    (out_dir / "qm_case4.txt").write_bytes(S.dump_bytes(S.keys_expected(X.scan_entries(entries))))
    (out_dir / "done.txt").write_bytes(S.dump_bytes(S.done_expected(
        [(b"qm_case1.cfg", b"readdump"), (b"qm_case4.cfg", b"keys")])))
    said = []
    assert qmtest.check(str(tmp_path), out=said.append) == 0, "\n".join(said)
    data = (out_dir / "rt0.txt").read_bytes()
    (out_dir / "rt0.txt").write_bytes(data[:-1] + b"x")
    said = []
    assert qmtest.check(str(out_dir), out=said.append) == 1
    assert any("rt0.txt" in s for s in said)


def test_check_says_incomplete_without_done(tmp_path):
    said = []
    assert qmtest.check(str(tmp_path), out=said.append) == 2


def test_the_check_command_exits_non_zero_on_a_difference(game_dir, tmp_path):
    """The exit status of the command itself, not of the function: a run's
    check is judged by it."""
    import subprocess
    import sys
    out_dir = tmp_path / "qm_test_out"
    out_dir.mkdir()
    (out_dir / "qm_case4.txt").write_bytes(S.dump_bytes([b"keys|316|1|316|0|0"]))
    (out_dir / "done.txt").write_bytes(S.dump_bytes(S.done_expected(
        [(b"qm_case4.cfg", b"keys")])))
    tool = os.path.join(os.path.dirname(qmtest.__file__), "qmtest.py")
    run = subprocess.run([sys.executable, tool, "check", str(tmp_path)],
                         capture_output=True, text=True)
    assert run.returncode == 1, run.stdout + run.stderr
    assert "problems: 1" in run.stdout
    (out_dir / "qm_case4.txt").write_bytes(S.dump_bytes([b"keys|316|0|316|0|0"]))
    run = subprocess.run([sys.executable, tool, "check", str(tmp_path)],
                         capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr


def test_bisect_candidates_are_the_constructs_the_lint_now_refuses():
    """The bisect settles in-game what the char-join lint assumes: the
    candidates it flags are the ones hrun is told may not compile."""
    import hbuild
    flagged = []
    for name, code in qmtest.BISECT:
        data = hbuild.assemble_inc(name.encode(), code)
        if any(f.lint == "char-join" for f in hbuild.lint_state("t.inc", name, data)):
            flagged.append(name)
    assert tuple(flagged) == qmtest.BISECT_MAY_FAIL
    # Each directive's text is exactly the .aix the build would assemble
    # (qmRawWriteStr writes it as it is, plus padding).
    directives = qmtest.bisect_directives()
    for (verb, name, text), (cand, code), (state_verb, state) in zip(
            directives[0::2], qmtest.BISECT, directives[1::2]):
        flag = b"ParserSetIntValueByKeyByHandle(ParserSelectByKey('qm_case_rt'), '%s', 1);"
        want = hbuild.assemble_aix([(cand.encode(), [flag % b"bs_ran"] + code + [flag % b"bs_done"])])
        assert (verb, state_verb, state) == (b"aix", b"state", cand.encode())
        assert T.unescape(text) == want and b" " not in text
