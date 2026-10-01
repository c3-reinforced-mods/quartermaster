"""Gates for the twins of the validator, writer, manifest and report
(ref/validate.py, ref/manifest.py, ref/report.py) and for tools/m4cases.py."""
import os
import re

import pytest

import hbuild as H
import m4cases as C
from ref import inc as I
from ref import manifest as MF
from ref import report as RP
from ref import selftest as S
from ref import validate as V
from ref.fingerprint import qhash
from ref.planner import HOOK_FILES
from ref.textio import escape, read_lines, write_file


@pytest.fixture(scope="module")
def fixture_dir(game_dir, reference_dir, tmp_path_factory):
    import fixtures as F
    out = str(tmp_path_factory.mktemp("m4reffixtures"))
    F.write(F.build_all(game_dir, reference_dir), out, game_dir)
    C.write_hook_fixture(out, game_dir)
    return out


@pytest.fixture(scope="module")
def entries():
    return C.idx_entries()


# ------------------------------------------------------------ the copy
def test_the_validation_copy_is_hbuilds_machine_file_shape():
    """The wrapper is exactly what tools/hbuild.py writes for core.aix (the
    shape probe 3 loaded) with the flag line and exit; first, padded as the
    raw writer pads."""
    values = [b";var qmX : Integer = 1;", b";if (qmX=1) then", b";qmX := 2;"]
    tok = V.token([b"   Name = X"], values)
    code = [V.flag_line(7, tok)[1:], b"exit;"] + [v[1:] for v in values]
    shape = H.assemble_aix([(b"qmVal7", code)])
    assert V.wrapper_bytes(7, tok, values) == shape + b" " * ((-len(shape)) % 4)
    lines = V.wrapper_lines(7, tok, values)
    assert lines[2] == b"   UsedFileName = " and lines[-4] == b"   CurrentState = "
    assert V.flag_line(7, tok) == (b";ParserSetValueByKeyByHandle(ParserSelectByKey("
                                   b"'qm_val'), 'f7', '" + tok + b"');")


def test_the_copy_of_a_vanilla_file_keeps_every_value(game_dir):
    """Values go in unchanged: those of vanilla cameracontrol.inc, after the
    flag line and exit;, byte for byte, the nested procedure included."""
    data = C.vanilla_reader(game_dir)(b"gui\\menu.inc\\cameracontrol.inc")
    keys, values = V.inc_lines(data)
    tok = V.token(keys, values)
    body = V.wrapper_bytes(3, tok, values).split(b"\r\n")
    assert body[1] == b"   Name = qmVal3"
    code = [line[len(I.CODE_PREFIX):] for line in body if line.startswith(I.CODE_PREFIX)]
    assert code[0] == V.flag_line(3, tok) and code[1] == b";exit;"
    assert code[2:] == I.parse(data).values
    assert I.hook_index(I.parse(data).values) == 8


def test_the_token_is_qhash_of_counted_key_lines_and_values():
    keys = [b"   Name = OnCamera", b"UsedFileName = "]
    values = [b";a", b";b~009"]
    assert V.token(keys, values) == qhash(b"2\nName = OnCamera\nUsedFileName = \n;a\n;b~009\n")
    # Key indentation does not count (qmIncBegin writes three spaces anyway).
    assert V.token([b"Name = OnCamera", b"   UsedFileName = "], values) == V.token(keys, values)
    # Moving a line from the keys to the values changes it.
    assert V.token(keys[:1], [keys[1]] + values) != V.token(keys, values)
    gen = [V.gen_line(b"1-2-3")]
    assert V.token(keys, values + gen, skip_gen=True) == V.token(keys, values)
    assert V.token(keys, values + gen) != V.token(keys, values)


def test_the_generation_line_is_replaced_whatever_its_value():
    vals = [b";a", b";const qmHookGen = '0';", b";b"]
    assert V.with_generation(vals, b"9-9-9") == [b";a", b";const qmHookGen = '9-9-9';", b";b"]
    assert V.is_gen_line(V.gen_line(b"x")) and not V.is_gen_line(b";const qmHookGens = 1;")


def test_the_staged_candidate_is_the_engine_layout_by_value_count():
    keys = [b"   Name = X"]
    assert V.candidate_bytes(keys, []) == write_file([b"section.begin", b"   Name = X",
                                                      b"section.end", b""])
    assert b"   Code[*] = ;a\r\n" in V.candidate_bytes(keys, [b";a"])
    assert V.inc_lines(V.candidate_bytes(keys, [b";a", b";b  "])) == (keys, [b";a", b";b  "])


# ------------------------------------------------------------ the paths
def test_the_writer_takes_the_merge_allow_list_and_nothing_else(entries):
    """Every merge-class path is writable; nothing of the never-generate list
    (plan S2), no other class, nothing outside data\\ or spelt otherwise."""
    for path, _size, _lines, cls in entries:
        assert V.writable(path, cls) == (cls == b"merge"), path
    for rel in H.S2_FILES:
        path = rel.replace("/", "\\").encode()
        assert not V.writable(path, b"merge"), rel
    for path in V.NEVER_INC:
        assert H.s2_reason(path.decode().replace("\\", "/"))
        assert not V.writable(path, b"merge")
    for bad in (b"scripts\\dmscript.global", b"gui\\menu.inc\\..\\x.inc", b"\\gui\\x.inc",
                b"GUI\\MENU.INC\\ONCAMERA.INC", b"quartermaster\\x.inc", b"scripts\\\\x.inc",
                b"gui\\menu.inc\\oncamera.inc ", b"gui\\menu.inc\\a|b.inc"):
        assert not V.writable(bad, b"merge"), bad
    assert sum(1 for e in entries if V.writable(e[0], e[3])) == 311


def test_hook_files_are_written_but_never_deleted(entries):
    cls = dict((e[0], e[3]) for e in entries)
    for path in HOOK_FILES:
        assert V.writable(path, cls[path]) and not V.deletable(path, cls[path])
    assert V.deletable(b"gui\\menu.inc\\oncamera.inc", b"merge")


# ------------------------------------------------------------ manifest
def test_the_manifest_reads_back_as_written():
    out = [MF.Output(b"gui\\menu.inc\\oncamera.inc", b"1-2-3", b"merged",
                     (b"merged", b"ok", b"-", 2, 0, 0), [(0, b"l", b"QMTestA", 1234)])]
    data = MF.render(4, b"5-6-7", b"8-9-10", out, [(b"scripts\\x.inc", b"1-1-1")])
    assert len(data) % 4 == 0 and data.count(b"\r\n") == data.count(b"\n")
    m = MF.parse(data)
    assert (m.gen, m.outhash, m.fp) == (4, b"5-6-7", b"8-9-10")
    assert m.paths() == [b"gui\\menu.inc\\oncamera.inc", b"scripts\\x.inc"]
    assert b";src|gui\\menu.inc\\oncamera.inc|0|l|" + b"QMTestA".hex().encode() + b"|1234\r\n" in data
    assert I.parse(data).name == b"qmManifest"


def test_the_generation_number_moves_only_with_the_outputs():
    m = MF.Manifest()
    m.gen, m.outhash = 3, b"1-2-3"
    assert MF.next_generation(None, b"x") == 1
    assert MF.next_generation(m, b"1-2-3") == 3
    assert MF.next_generation(m, b"4-5-6") == 4


# --------------------------------------------------------- generations
def _run(fixtures, fixture_dir, entries, dropped=(), compiles=C.duplicate_var_oracle,
         mirror=None, **kw):
    inp = C.offline_inputs(fixtures, fixtures_dir=fixture_dir, entries=entries)
    decisions = C.decisions_for(inp, entries, dropped)
    mirror = {} if mirror is None else mirror
    if kw:
        classes = dict((p, c[0]) for p, c in inp.idx.items())
        g = V.generate(decisions, inp.self_pos, inp.read_vanilla, inp.read_mod,
                       lambda p: inp.hooks.get(p.decode().rsplit("\\", 1)[-1]), compiles,
                       prev_manifest=mirror.get(MF.MANIFEST_REL), classes=C._Classes(classes),
                       srcs=inp.srcs, existing=mirror.get, **kw)
    else:
        g = C.run_generation(inp, decisions, compiles, mirror)
    return inp, g


def test_wasd_and_broken_write_the_winners_copy_and_report_fail(fixture_dir, entries):
    inp, g = _run(C.RUN_A, fixture_dir, entries)
    r = next(x for x in g.paths if x.path == b"gui\\menu.inc\\registershortcuts.inc")
    assert [(c.tier, c.ok) for c in r.tries] == [(V.TIER_MERGED, False), (V.TIER_WINNER, True)]
    assert (r.code, r.status, r.written) == (b"fallback", V.FAIL, b"yes")
    wasd = inp.read_mod(r.winner, r.path)
    assert I.parse(g.outputs[r.path]).values == I.parse(wasd).values
    lines, rep, qmr = C.report_of(g, inp)
    assert b"FAIL gui\\menu.inc\\registershortcuts.inc" in lines
    assert b"  candidate merged: does not compile" in lines
    assert lines[2].startswith(b"status FAIL: ")
    # QMTestBroken's change is gone (FAIL); QMTestWASD's own copy is the one
    # written, so it lost nothing (OK - ref/report.py mod_status).
    assert [qmr[b"st%d" % j] for j in range(3)] == [V.FAIL, V.OK, V.OK]
    assert rep == RP.report_bytes(lines) and rep.count(b"\n") == rep.count(b"\r\n")
    # Every hook file is vanilla plus its hook lines, and nothing else changed.
    for h in HOOK_FILES:
        x = next(p for p in g.paths if p.path == h)
        assert x.code == b"hooked" and x.chosen.tier == V.TIER_VANILLA_HOOK


def test_a_second_run_writes_the_same_bytes_and_a_dropped_mod_goes_stale(fixture_dir,
                                                                          entries):
    mirror = {}
    _inp, g1 = _run(C.RUN_B, fixture_dir, entries, mirror=mirror)
    merged = [r.path for r in g1.paths if r.code == b"merged"]
    assert merged == [b"gui\\menu.inc\\oncamera.inc", b"gui\\menu.inc\\registershortcuts.inc"]
    first = dict(mirror)
    inp, g2 = _run(C.RUN_B, fixture_dir, entries, mirror=mirror)
    assert mirror == first and g2.changed == 0 and g2.gen == g1.gen == 1
    assert all(r.written in (b"same", b"-") for r in g2.paths)
    assert C.report_of(g1, inp)[1] == C.report_of(g2, inp)[1]
    _inp, g3 = _run(C.RUN_B, fixture_dir, entries, dropped=[C.DROP.lower()], mirror=mirror)
    assert [(s.path, s.result) for s in g3.stale] == [(p, b"deleted") for p in merged]
    assert all(p not in mirror for p in merged) and g3.gen == 2
    cam = next(r for r in g3.paths if r.path == V.CAMERA)
    assert cam.written == b"yes"      # the generation constant moved
    cold = {}
    _run(C.RUN_B, fixture_dir, entries, mirror=cold)
    assert cold == first


def test_a_hook_file_a_mod_changes_merges_under_the_hook_lines(fixture_dir, entries):
    inp, g = _run(C.RUN_B, fixture_dir, entries)
    r = next(x for x in g.paths if x.path == b"gui\\menu.inc\\eventmainmenu.inc")
    assert (r.code, r.status) == (b"hooked", V.OK)
    assert [c.tier for c in r.tries] == [V.TIER_MERGED_HOOK]
    mod = I.parse(inp.read_mod(r.winner, r.path)).values
    hook = V.inc_lines(inp.hooks["eventmainmenu.inc"])[1]
    assert r.chosen.values == I.insert_at_hook([escape(v) for v in mod], hook)
    assert b";const cTagCredits = 111; // QMTEST m4hook" in r.chosen.values

    def refuse(c):
        return b";const cTagCredits = 111; // QMTEST m4hook" not in c.values
    _inp, f = _run(C.RUN_B, fixture_dir, entries, compiles=refuse)
    r = next(x for x in f.paths if x.path == b"gui\\menu.inc\\eventmainmenu.inc")
    # winner+hook has the very tokens of merged+hook (one participant), so it
    # is not tried again; vanilla+hook is.
    assert [(c.tier, c.ok) for c in r.tries] == [(V.TIER_MERGED_HOOK, False),
                                                 (V.TIER_VANILLA_HOOK, True)]
    assert (r.code, r.status) == (b"fallback", V.FAIL)


def test_conflicts_and_near_edits_are_reported_by_vanilla_line(fixture_dir, entries):
    inp, g = _run(C.RUN_C, fixture_dir, entries)
    lines = C.report_of(g, inp)[0]
    at = lines.index(b"WARN gui\\menu.inc\\oncamera.inc")
    assert lines[at + 4:at + 7] == [
        b"  merge: merged, warn: 3 changes, 1 conflicts, 1 near each other",
        b"  conflict: vanilla line 18 of 1. mods\\QMTestConflict lost to 3. mods\\QMTestWASD",
        b"  near: vanilla line 14 of 2. mods\\QMTestM4Near and vanilla lines 18-21 of 3. "
        b"mods\\QMTestWASD"]


def test_a_mod_that_half_loses_is_left_out_and_the_rest_merges(fixture_dir, entries):
    """QMTestM4Split loses its first oncamera.inc edit to QMTestWASD, and its
    second does not compile without the first: the merged file is refused,
    the merge without QMTestM4Split compiles - written, WARN, and the report
    names who is left out (Renaissance + MGraphics - Main Menu, 2026-09-30)."""
    inp, g = _run(C.RUN_D, fixture_dir, entries, compiles=C.split_oracle)
    r = next(x for x in g.paths if x.path == b"gui\\menu.inc\\oncamera.inc")
    split = inp.dirs.index(b"mods\\" + C.SPLIT_FIXTURE.encode()) if hasattr(inp, "dirs") else None
    assert [(c.tier, c.ok) for c in r.tries] == [(V.TIER_MERGED, False), (V.TIER_SUBSET, True)]
    assert (r.code, r.status, r.written) == (b"partial", V.WARN, b"yes")
    assert len(r.left_out) == 1 and r.left_out[0] in r.participants
    assert r.left_out[0] != r.winner
    out = V.code_values(g.outputs[r.path])
    assert not any(b"QMTEST split" in v for v in out)
    assert any(b"QMTEST near" in v for v in out)
    wasd = V.code_values(inp.read_mod(r.winner, r.path))
    assert all(v in out for v in wasd if b"IsKeyDownByName" in v)
    lines = C.report_of(g, inp)[0]
    at = lines.index(b"WARN gui\\menu.inc\\oncamera.inc")
    block = lines[at:at + 12]
    assert b"  candidate merged: does not compile" in block
    assert b"  candidate subset: compiles" in block
    assert any(x.startswith(b"  left out: ") and C.SPLIT_FIXTURE.encode() in x for x in block)
    assert b"  result: " + RP.RESULT[b"partial"] in block
    if split is not None:
        assert r.left_out == [split]


def test_no_subset_when_one_participant_would_stay(fixture_dir, entries):
    """Two participants, the earlier one loses: what stays is the winner's own
    copy, the next tier anyway - no subset candidate, the fallback as before."""
    two = ("QMTestWASD", C.SPLIT_FIXTURE)
    _inp, g = _run(two, fixture_dir, entries, compiles=C.split_oracle)
    r = next(x for x in g.paths if x.path == b"gui\\menu.inc\\oncamera.inc")
    assert r.sub_merge is None and r.left_out == []
    assert [(c.tier, c.ok) for c in r.tries] == [(V.TIER_MERGED, False), (V.TIER_WINNER, True)]
    assert (r.code, r.status) == (b"fallback", V.FAIL)


def test_the_generation_constant_is_the_outputs_hash(fixture_dir, entries):
    _inp, g = _run(C.RUN_B, fixture_dir, entries)
    cam = next(r for r in g.paths if r.path == V.CAMERA)
    gen = [v for v in cam.chosen.values if V.is_gen_line(v)]
    assert gen == [V.gen_line(g.outhash)]
    assert MF.parse(g.manifest).outhash == g.outhash
    _inp, s = _run(C.RUN_B, fixture_dir, entries, gensalt=b"x7")
    cam = next(r for r in s.paths if r.path == V.CAMERA)
    assert [v for v in cam.chosen.values if V.is_gen_line(v)] == [V.gen_line(g.outhash + b"-x7")]
    assert s.outhash == g.outhash


def test_quartermaster_alone_needs_nothing_new(fixture_dir, entries, game_dir):
    """alone_outputs_hash is what a generation with Quartermaster alone writes
    into the CameraControl constant (hbuild bakes it into the static copy)."""
    inp, g = _run((), fixture_dir, entries)
    assert [r.act for r in g.paths] == [b"hook"] * len(HOOK_FILES)
    hooks = dict((p, V.inc_lines(inp.hooks[p.decode().rsplit("\\", 1)[-1]])[1])
                 for p in HOOK_FILES)
    alone = V.alone_outputs_hash(sorted(HOOK_FILES), C.vanilla_reader(game_dir), hooks.get)
    assert alone == g.outhash


def test_a_fatal_hook_writes_nothing(fixture_dir, entries):
    def refuse(c):
        return c.path != b"gui\\menu.inc\\eventmainmenu.inc" and C.duplicate_var_oracle(c)
    inp, g = _run(C.RUN_B, fixture_dir, entries, compiles=refuse)
    assert g.status == b"fatal" and g.fatal == b"gui\\menu.inc\\eventmainmenu.inc"
    assert g.outputs == {} and g.manifest is None
    lines = C.report_of(g, inp)[0]
    assert lines[-1].startswith(b"FATAL: gui\\menu.inc\\eventmainmenu.inc: ")
    assert lines[2].startswith(b"status FATAL: ")


def test_an_undeletable_stale_file_is_overwritten_with_the_winners_copy(fixture_dir,
                                                                         entries):
    mirror = {}
    _run(C.RUN_B, fixture_dir, entries, mirror=mirror)
    inp = C.offline_inputs(C.RUN_B, fixtures_dir=fixture_dir, entries=entries)
    g = C.run_generation(inp, C.decisions_for(inp, entries, [C.DROP.lower()]),
                         C.duplicate_var_oracle, mirror,
                         deleted=lambda p: p != b"gui\\menu.inc\\oncamera.inc")
    s = next(x for x in g.stale if x.path == b"gui\\menu.inc\\oncamera.inc")
    assert (s.result, s.source) == (b"overwritten", b"winner")
    assert MF.parse(g.manifest).lefts == [(s.path, s.cand.tok)]
    lines = C.report_of(g, inp)[0]
    assert (b"  gui\\menu.inc\\oncamera.inc: could not be deleted; overwritten with the "
            b"winner's copy") in lines


def test_suspected_brick_merges_nothing(fixture_dir, entries):
    inp, g = _run(C.RUN_B, fixture_dir, entries, wta=True)
    for r in g.paths:
        if r.act == b"merge-inc":
            assert (r.code, r.status, r.chosen) == (b"wta", V.FAIL, None)
        if r.act == b"hook":
            assert r.code == b"wtahook" and r.status == V.FAIL and r.job == -1


def test_the_boot_block_and_new_mods_in_the_report(fixture_dir, entries):
    inp, g = _run(C.RUN_A, fixture_dir, entries)
    boot = RP.Boot([b"hook CameraControl ran"], V.WARN, [b"MODS\\QUARTERMASTER"])
    lines = RP.report_lines(g, inp.dir_of(), inp.enabled(), inp.self_pos, boot)
    assert lines[3:6] == [b"", b"Boot:", b"  hook CameraControl ran"]
    qmr = RP.qm_report(g, lines, inp.dir_of(), inp.enabled(), inp.self_pos, boot)
    # st1 is QMTestWASD, the winner whose own copy was written: OK for it.
    assert qmr[b"st2"] == RP.NEW and qmr[b"st1"] == V.OK and qmr[b"st0"] == V.FAIL


def test_report_cfg_keeps_the_leading_spaces_through_the_engines_parser(fixture_dir,
                                                                        entries):
    """report.cfg in the layout of run m4a, every text value behind the guard:
    what the engine's parser loads from it, guard taken off, is qm_report
    again. Without the guard exactly the values that start with a space come
    back different - the 34 of 72 of run m4a."""
    inp, g = _run(C.RUN_A, fixture_dir, entries)
    lines, _rep, qmr = C.report_of(g, inp)
    data = RP.report_cfg(qmr)
    rows = data.split(b"\r\n")
    assert rows[0] == b"section.begin" and rows[-3:] == [b"section.end", b"", b""]
    assert rows[1] == b"   lines = %d" % len(lines)
    assert rows[2] == b"   l0 = ;Quartermaster report"
    assert all(re.match(rb"^   [a-z0-9_]+ = ", r) for r in rows[1:-3])
    assert RP.read_report_cfg(data) == qmr
    spaced = set(k for k, v in qmr.items() if v.startswith(b" "))
    # The report's detail lines, by file (l<k>) and by mod (m<k>).
    assert spaced and all(k.startswith((b"l", b"m")) for k in spaced)
    assert any(k.startswith(b"m") for k in spaced)
    bare = b"".join(r + b"\r\n" for r in [b"section.begin"]
                    + [b"   " + k + b" = " + v for k, v in qmr.items()]
                    + [b"section.end", b""])
    back = RP.parser_read_flat(bare)
    assert set(k for k in qmr if back[k] != qmr[k]) == spaced
    # A file saved before the guard reads as it is (the next generation saves
    # it again); no file gives an empty qm_report.
    assert RP.read_report_cfg(bare) == back
    assert RP.read_report_cfg(None) == {}


def test_a_hook_file_whose_merge_gave_up_is_ok_alone_and_warn_with_others():
    """The winner's copy with the hook lines (SW_Frontline_Protocol's
    doprogress.inc, too different to merge): nothing is lost with one mod,
    the others' changes are with two; and nothing was merged, so the short
    text does not say a change was replaced."""
    from ref import merge as M
    from ref.planner import Decision
    gave_up = M.MergeResult("winner", M.FAIL, "too-different", 0, [], [], [])
    assert V._merge_status(b"hooked", gave_up, alone=True) == V.OK
    assert V._merge_status(b"hooked", gave_up, alone=False) == V.WARN
    merged = M.MergeResult("merged", M.WARN, None, None, [], [], [])
    assert V._merge_status(b"hooked", merged) == V.OK
    r = V.PathResult(0, Decision(b"gui\\menu.inc\\doprogress.inc", b"hook", b"hook",
                                 b"quartermaster-hook", 1, [0, 1]))
    r.code, r.merge = b"hooked", gave_up
    assert RP.mod_short(r, 0) == RP.SHORT[b"gaveup"]
    r.merge = merged
    assert RP.mod_short(r, 0) == RP.SHORT[b"hooked"]


def test_a_boot_clash_marks_both_mods_in_the_report_by_mod(fixture_dir, entries):
    """Each mod of a clash gets FAIL in its head and a line naming the file
    and the other mod (the dirs matched without case); without the clash
    neither block has it."""
    inp, g = _run(C.RUN_A, fixture_dir, entries)
    dirs, enabled, me = inp.dir_of(), inp.enabled(), inp.self_pos
    a, b = sorted(enabled)[:2]
    plain = RP.Boot([b"OK x"], V.OK, [])
    boot = RP.Boot([b"FAIL x"], V.FAIL, [], [(dirs[a], dirs[b].upper(), b"lib\\unit.script")])
    m = RP.mod_lines(g, RP.report_lines(g, dirs, enabled, me, boot), dirs, enabled, me, boot)
    for pos, other in ((a, b), (b, a)):
        head = next(k for k, line in enumerate(m)
                    if line.split(b" ", 1)[-1] == RP._row(pos, dirs, me))
        assert m[head].startswith(b"FAIL ")
        assert m[head + 2] == (b"  FAIL scripts\\lib\\unit.script: " + RP._who(other, dirs)
                               + b" ships it too: only one copy loads, and the game may not "
                               b"start with both")
    m0 = RP.mod_lines(g, RP.report_lines(g, dirs, enabled, me, plain), dirs, enabled, me, plain)
    assert not [line for line in m0 if b"ships it too" in line]
    assert len(m) == len(m0) + 2


def test_report_ranges_name_vanilla_lines():
    assert RP.rng(0, 3, 4, 10) == b"vanilla lines 4-6"
    assert RP.rng(2, 3, 4, 10) == b"vanilla line 6"
    assert RP.rng(2, 2, 4, 10) == b"before vanilla line 6"
    assert RP.rng(10, 10, 4, 10) == b"after the last vanilla line"


def test_report_names_a_mod_by_title_and_workshop_number():
    """A title with the Workshop number (the prefix matched without case) or
    the local dir beside it; a mod without a title by its dir alone."""
    ws = b"..\\..\\workshop\\content\\333420\\855916926"
    dirs = RP.Dirs({0: ws, 1: b"mods\\Local", 2: b"mods\\Bare",
                    3: b"..\\..\\WORKSHOP\\Content\\333420\\1325221799"},
                   {0: b"MGraphics - Interface", 1: b"Local mod",
                    3: b"State vs Country"})
    assert RP._who(0, dirs) == b"1. MGraphics - Interface (855916926)"
    assert RP._who(1, dirs) == b"2. Local mod (mods\\Local)"
    assert RP._who(2, dirs) == b"3. mods\\Bare"
    assert RP._who(3, dirs) == b"4. State vs Country (1325221799)"
    assert RP._who(0, {0: ws}) == b"1. " + ws
    # Quartermaster's own row: the mark only where no title names it.
    assert RP._row(1, dirs, 1) == b"2. Local mod (mods\\Local)"
    assert RP._row(2, dirs, 2) == b"3. mods\\Bare (Quartermaster)"
    assert RP._row(2, dirs, 1) == b"3. mods\\Bare"


def test_a_mod_file_with_tab_led_code_lines_merges_like_the_game_reads_it(game_dir):
    """State vs Country (Workshop 1325221799) starts code lines with a tab
    (`\t  [*] = ;...`) in 33 files. The game side takes the text after the
    first `[*] = `; the twin did the same only since the Workshop dry run of
    2026-09-28 (before, ref.inc.parse refused the file and the twin raised)."""
    from conftest import vanilla_bytes
    from ref import merge as MG
    van = vanilla_bytes("gui/menu.inc/oncamera.inc")
    plain = van.replace(b";if (gInterface.gamemode=gc_gamemode_mainmenu) then",
                        b";if (gInterface.gamemode<>gc_gamemode_mainmenu) then", 1)
    assert plain != van
    tabbed = plain.replace(b"\r\n      [*] = ", b"\r\n\t  [*] = ")
    assert tabbed.count(b"\t  [*] = ") > 60
    with pytest.raises(I.IncFormatError):
        I.parse(tabbed)
    assert V.code_values(tabbed) == V.code_values(plain) == I.parse(plain).values
    got, err = V._merge_job(van, [(0, tabbed), (1, van)])
    want, _err = V._merge_job(van, [(0, plain), (1, van)])
    assert err == b"" and MG.final_lines(got) == MG.final_lines(want)
    assert got.mode == "merged"


# ------------------------------------------------------------ the tool
def test_the_case_files_parse_and_carry_every_hook(entries):
    cases = C.cases(entries)
    for name in ("qm_m4a.cfg", "qm_m4b.cfg", "qm_m4v.cfg"):
        kind, directives = S.parse_case(cases[name])
        assert kind == b"m4gen" and directives
    shipped = set(h.into.rsplit("/", 1)[-1] for h in H.load_hooks())
    assert shipped <= set(cases)
    for name in shipped:
        _k, values = V.inc_lines(cases[name])
        assert values and all(v.startswith(b";") for v in values)
    _k, cam = V.inc_lines(cases["cameracontrol.inc"])
    assert sum(1 for v in cam if V.is_gen_line(v)) == 1


def test_expected_compile_errors(entries, fixture_dir):
    names = C.expected_failures(entries, fixture_dir)
    assert names["qm_m4b.cfg"] == []
    first = "qmVal%d" % (C.SEQ_BASE + len(C.VAL_FILES))
    assert len(names["qm_m4a.cfg"]) == 2 and names["qm_m4a.cfg"][0] == first
    # A generation the boot runs first, from 0: the merged registershortcuts.inc.
    assert len(names["boot:qm_m4a.cfg"]) == 1 and names["boot:qm_m4b.cfg"] == []
