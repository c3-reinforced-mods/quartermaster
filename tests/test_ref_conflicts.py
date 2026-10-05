"""ref/conflicts.py: the conflict report, offline. Real mods are read where
Steam installed them and the test is skipped without them; nothing of theirs
is copied into the repository."""
import os

import pytest

import hbuild as H
import m4cases as C
from conftest import GAME_DIR, vanilla_bytes
from ref import about as AB
from ref import conflicts as CF
from ref import report as RP
from ref import validate as V
from ref.merge import MergeHunk

VERSION = H.QM_VERSION.encode("ascii")
ONCAMERA = b"gui\\menu.inc\\oncamera.inc"
WS = b"..\\..\\workshop\\content\\333420\\"
WS_DIR = os.path.normpath(os.path.join(GAME_DIR, "..", "..", "workshop", "content", "333420"))


@pytest.fixture(scope="module")
def fixture_dir(game_dir, reference_dir, tmp_path_factory):
    import fixtures as F
    out = str(tmp_path_factory.mktemp("crfixtures"))
    F.write(F.build_all(game_dir, reference_dir), out, game_dir)
    C.write_hook_fixture(out, game_dir)
    return out


@pytest.fixture(scope="module")
def entries():
    return C.idx_entries()


def _report(inp, entries, compiles=C.duplicate_var_oracle, boot=None):
    g = C.run_generation(inp, C.decisions_for(inp, entries), compiles, {})
    c = CF.build(g, inp.dir_of(), inp.enabled(), inp.self_pos, inp.read_vanilla, boot)
    return g, c, CF.report_lines(c, g, VERSION)


# ------------------------------------------------------------ the rules
def test_the_kind_of_a_file_comes_from_its_folder():
    assert CF.kind(b"scripts\\lib\\unit.script") == b"core script, whole game"
    assert CF.kind(b"scripts\\dmscript.global") == b"core script, whole game"
    assert CF.kind(b"scripts\\units\\unit.inc\\ontagstates.inc") == b"script, gameplay"
    assert CF.kind(b"gui\\menu.inc\\oncamera.inc") == b"script, interface"
    assert CF.kind(b"gui\\common.inc\\x.inc") == b"script, interface"
    assert CF.kind(b"gui\\menu.aix") == b"interface layout"
    assert CF.kind(b"hud\\hud.mat") == b"graphics"
    assert CF.kind(b"images\\a.bmp") == b"graphics"
    assert CF.kind(b"game\\var\\objcustom.cfg") == b"data, gameplay"
    assert CF.kind(b"maps\\x.map") == b"data, content"


def test_routines_follow_the_bodies_and_skip_comments_and_strings():
    values = [b";procedure LoadIt;", b";begin", b";   if x then begin y; end;", b";end;",
              b";x := 1;", b";function Count : Integer;", b";var s : String = 'begin';",
              b";begin // end", b";   { end", b";   begin }", b";   Result := 0;", b";end;",
              b";z := 2;"]
    rt = CF.routines(values)
    a, b = (b"procedure", b"LoadIt"), (b"function", b"Count")
    assert rt == [a, a, a, a, None, b, b, b, b, b, b, b, None]
    assert CF.where(rt, 4, 5) == b"main code"
    assert CF.where(rt, 0, 4) == b"procedure LoadIt"
    assert CF.where(rt, 3, 6) == b"procedure LoadIt, main code, function Count"
    # An insertion is placed by the line before it; past the end, by the last.
    assert CF.where(rt, 5, 5) == b"main code"
    assert CF.where(rt, 1, 1) == b"procedure LoadIt"
    assert CF.where(rt, 13, 13) == b"main code"
    assert CF.where([], 0, 0) == b"main code"


def test_at_is_the_vanilla_line_cut_and_trimmed():
    long = b";" + b"x" * 70
    values = [b";   const cmargin = 7;  ", b";\tvar a : Integer;\t", long, b"plain"]
    assert CF.at_text(values, 0) == b"const cmargin = 7;"
    assert CF.at_text(values, 1) == b"var a : Integer;"
    assert CF.at_text(values, 2) == b"x" * 57 + b"..." and len(CF.at_text(values, 2)) == 60
    assert CF.at_text(values, 3) == b"plain"
    assert CF.at_text(values, 4) == b"(end of file)"


def test_a_change_is_said_in_words():
    def h(start, end, n):
        return MergeHunk(0, 0, 0, start, end, [b";x"] * n, [b"x"] * n)
    assert CF.change(h(3, 3, 1)) == b"adds 1 line"
    assert CF.change(h(3, 3, 11)) == b"adds 11 lines"
    assert CF.change(h(3, 5, 0)) == b"removes 2 lines"
    assert CF.change(h(3, 4, 1)) == b"changes 1 line"
    assert CF.change(h(3, 19, 4)) == b"replaces 16 lines with 4"


# ------------------------------------------------------------ the fixtures
def test_a_conflict_and_a_near_pair_of_the_m4_fixtures(fixture_dir, entries):
    """WASD + Conflict + M4Near on oncamera.inc (case C): one conflict that
    QMTestConflict loses to QMTestWASD, one pair close together, the place
    in the code and the vanilla line taken from vanilla itself."""
    inp = C.offline_inputs(C.RUN_C, fixtures_dir=fixture_dir, entries=entries)
    g, c, lines = _report(inp, entries)
    r = next(x for x in g.paths if x.path == ONCAMERA)
    state, values = CF._code(inp.read_vanilla, ONCAMERA)
    assert state == b"OnCamera" and values == V.code_values(inp.read_vanilla(ONCAMERA))
    h = next(x for x in r.merge.hunks if x.status == "conflict-lost")
    by = r.merge.hunks[h.conflict_with[-1]]
    s, e = min(h.start, by.start), max(h.end, by.end)
    head = b"C1 gui\\menu.inc\\oncamera.inc, " + RP.rng(s, e, r.first_line, r.vanilla_n)
    k = lines.index(next(x for x in lines if x.startswith(b"C1 ")))
    assert lines[k].startswith(head + b", state OnCamera, ")
    assert lines[k + 1] == b"   at: " + CF.at_text(values, s)
    assert lines[k + 2] == (b"   active: 3. mods\\QMTestWASD: " + CF.change(by)
                            + b"   dropped: 1. mods\\QMTestConflict: " + CF.change(h))
    assert lines[k + 3] == b"   why: 3 is later in the load order"
    assert lines[k + 4] == b"   kind: script, interface (by folder)"
    assert b"  1 <-> 3: 1 conflict - mods\\QMTestWASD active in 1, mods\\QMTestConflict " \
           b"active in 0; 0 close together (both active); 0 whole files" in lines
    near = [x for x in lines if x.startswith(b"N")]
    assert len(near) == len(r.merge.pairs) == 1
    assert b"  2 <-> 3: 0 conflicts; 1 close together (both active); 0 whole files" in lines
    # The window: the pair lines, and a sentence for each side of the conflict.
    pairs, said = CF.window(c)
    assert pairs == CF.pair_lines(c)
    pos = dict((inp.dir_of()[p], p) for p in inp.enabled())
    assert said[pos[b"mods\\QMTestConflict"]] == b"Loses 1 conflict to mods\\QMTestWASD"
    assert said[pos[b"mods\\QMTestWASD"]] == b"Wins 1 conflict over mods\\QMTestConflict"
    assert pos[b"mods\\" + H.MOD_NAME.encode()] not in said


def test_reversing_the_order_of_a_pair_moves_every_conflict(fixture_dir, entries):
    pair = [b"mods\\QMTestConflict", b"mods\\QMTestWASD"]
    _g, c1, l1 = _report(C.ordered_inputs(pair, fixtures_dir=fixture_dir, entries=entries),
                         entries)
    _g, c2, l2 = _report(C.ordered_inputs(pair[::-1], fixtures_dir=fixture_dir,
                                          entries=entries), entries)
    assert [x[4] for x in c1.conflicts] == [1] * len(c1.conflicts) and c1.conflicts
    assert [x[4] for x in c2.conflicts] == [1] * len(c2.conflicts)
    assert len(c1.conflicts) == len(c2.conflicts)
    a1 = [x for x in l1 if x.startswith(b"   active: ")]
    a2 = [x for x in l2 if x.startswith(b"   active: ")]
    assert a1 and len(a1) == len(a2)
    assert all(x.startswith(b"   active: 2. mods\\QMTestWASD: ")
               and b"   dropped: 1. mods\\QMTestConflict: " in x for x in a1)
    assert all(x.startswith(b"   active: 2. mods\\QMTestConflict: ")
               and b"   dropped: 1. mods\\QMTestWASD: " in x for x in a2)


def _one_line_mod(root, name, old, new, crlf=True):
    """A mod folder of Quartermaster's own: vanilla oncamera.inc with one Code
    line changed (the bytes from the game's own copy, changed here)."""
    data = vanilla_bytes("gui/menu.inc/oncamera.inc")
    assert data.count(old) == 1
    data = data.replace(old, new)
    if not crlf:
        data = data.replace(b"\r\n", b"\n")
    folder = os.path.join(root, name, "data", "gui", "menu.inc")
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "oncamera.inc"), "wb") as fh:
        fh.write(data)
    return b"mods\\" + name.encode("ascii")


def _a_vanilla_line():
    """A Code line of vanilla oncamera.inc that is there once."""
    lines = vanilla_bytes("gui/menu.inc/oncamera.inc").split(b"\r\n")
    for line in lines:
        if b"[*] = ;" in line and b":=" in line and lines.count(line) == 1:
            return line
    raise AssertionError("no unique assignment line in oncamera.inc")


def test_a_duplicate_of_a_lost_change_is_named_as_dropped(game_dir, entries, tmp_path):
    """A and B make the same change, C a different one at the same line: B's
    copy is a duplicate of A's, A's loses to C - so B's is gone too, and the
    report says so (gap 6 of the conflict analysis)."""
    line = _a_vanilla_line()
    root = str(tmp_path)
    dirs = [_one_line_mod(root, "QMTestDupA", line, line + b" // same"),
            _one_line_mod(root, "QMTestDupB", line, line + b" // same"),
            _one_line_mod(root, "QMTestDupC", line, line + b" // other")]
    inp = C.ordered_inputs(dirs, fixtures_dir=root, entries=entries)
    _g, c, lines = _report(inp, entries)
    act = [x for x in lines if x.startswith(b"   active: ")]
    assert act == [b"   active: 3. mods\\QMTestDupC: changes 1 line   dropped: "
                   b"1. mods\\QMTestDupA: changes 1 line; 2. mods\\QMTestDupB: the same change"]
    assert b"  1 <-> 3: 1 conflict - mods\\QMTestDupC active in 1, mods\\QMTestDupA active " \
           b"in 0; 0 close together (both active); 0 whole files" in lines
    assert b"  2 <-> 3: 1 conflict - mods\\QMTestDupC active in 1, mods\\QMTestDupB active " \
           b"in 0; 0 close together (both active); 0 whole files" in lines
    assert CF.details(c, 1) == b"Loses 1 conflict to mods\\QMTestDupC"


def test_lf_and_crlf_copies_give_the_same_file_and_runs_the_same_bytes(game_dir, entries,
                                                                       tmp_path):
    line = _a_vanilla_line()
    out = []
    for crlf in (True, False):
        root = str(tmp_path / ("crlf" if crlf else "lf"))
        dirs = [_one_line_mod(root, "QMTestEolA", line, line + b" // a", crlf),
                _one_line_mod(root, "QMTestEolB", line, line + b" // b", crlf)]
        inp = C.ordered_inputs(dirs, fixtures_dir=root, entries=entries)
        g, _c, lines = _report(inp, entries)
        out.append(CF.conflicts_bytes(lines))
        again = _report(inp, entries)[2]
        assert CF.conflicts_bytes(again) == out[-1]
    assert out[0] == out[1]
    assert out[0].count(b"\r\n") == out[0].count(b"\n") and b"C1 " in out[0]


def test_a_core_script_clash_has_its_section_and_pair_line(fixture_dir, entries):
    inp = C.offline_inputs(C.RUN_C, fixtures_dir=fixture_dir, entries=entries)
    dirs = inp.dir_of()
    pos = dict((dirs[p], p) for p in inp.enabled())
    boot = RP.Boot([b"FAIL x"], V.FAIL, [], [(b"MODS\\QMTESTWASD", b"mods\\QMTestConflict",
                                              b"lib\\unit.script")])
    _g, _c, lines = _report(inp, entries, boot=boot)
    k = lines.index(b"Core scripts (only one copy loads; the game may not start with both):")
    assert lines[k + 1] == b"  scripts\\lib\\unit.script: 1. mods\\QMTestConflict and " \
                           b"3. mods\\QMTestWASD"
    pair = next(x for x in lines if x.startswith(b"  1 <-> 3: "))
    assert pair.endswith(b"; FAIL 1 core script both ship")
    assert pos[b"mods\\QMTestConflict"] < pos[b"mods\\QMTestWASD"]


def test_the_window_shows_at_most_its_pair_lines():
    c = CF.Conflicts(RP.Dirs(dict((p, b"mods\\M%d" % p) for p in range(20))), range(20), 19)
    for a in range(18):
        c.pair(a, a + 1).near += 1
    pairs, said = CF.window(c)
    assert len(pairs) == CF.PAIR_LINES + 1 and said == {}
    assert pairs[-1] == b"  ... and 4 more pairs: see conflicts.txt"
    assert len(CF.pair_lines(c)) == 18


# ------------------------------------------------------------ the real set
REAL = [(WS + b"855863185", b"MGraphics - Main Menu", "855863185"),
        (b"mods\\UnofficialPatch", b"Cossacks 3 Unofficial Patch", None),
        (WS + b"3398700006", b"Renaissance", "3398700006")]
SHOWMAINMENU = b"gui\\menu.inc\\showmainmenu.inc"


def test_the_real_set_mgraphics_unofficial_patch_renaissance(game_dir, entries):
    """The analysis' measurement (CONFLICTS-2026-10-01.md), structurally: 6
    conflicts, every one won by Renaissance; showmainmenu.inc written without
    MGraphics - Main Menu, as the game refused the full merge (run
    ftB-withqm); Unofficial Patch and Renaissance: no conflict, 2 changes
    close together. The game's copies are read where they are installed."""
    for _d, _t, ws in REAL:
        where = (os.path.join(WS_DIR, ws) if ws else
                 os.path.join(GAME_DIR, "mods", "UnofficialPatch"))
        if not os.path.isdir(where):
            pytest.skip("not installed: %s" % where)
        about = os.path.join(where, "about.cfg")
        if not ws and os.path.isfile(about):
            with open(about, "rb") as fh:
                if AB.parse(fh.read()).id == b"reinforcedcore":
                    pytest.skip("mods\\UnofficialPatch is Reinforced Core now (2026-10-05, "
                                "more files); the numbers below are of the earlier patch")

    def compiles(cand):
        if cand.path == SHOWMAINMENU and cand.tier == b"merged":
            return False
        return C.duplicate_var_oracle(cand)

    inp = C.ordered_inputs([d for d, _t, _w in REAL], [t for _d, t, _w in REAL],
                           entries=entries)
    g, c, lines = _report(inp, entries, compiles)
    assert len(c.conflicts) == 6 and set(x[4] for x in c.conflicts) == {2}
    assert c.left == [(SHOWMAINMENU, 0, c.left[0][2])] and c.left[0][2] > 0
    assert b"  2 <-> 3: 0 conflicts; 2 close together (both active); 0 whole files" in lines
    assert next(x for x in lines if x.startswith(b"  1 <-> 3: ")).startswith(
        b"  1 <-> 3: 6 conflicts - Renaissance active in 6, MGraphics - Main Menu active in 0")
    assert (b"  gui\\menu.inc\\showmainmenu.inc: without 1. MGraphics - Main Menu (855863185) "
            b"(%d changes); the merged file does not compile, and it compiles without them"
            % c.left[0][2]) in lines
    assert CF.details(c, 0) == b"Left out of gui\\menu.inc\\showmainmenu.inc"
    assert CF.details(c, 2) == b"Wins 6 conflicts over MGraphics - Main Menu"
    assert CF.details(c, 1) == b""
    assert CF.conflicts_bytes(_report(inp, entries, compiles)[2]) == CF.conflicts_bytes(lines)
