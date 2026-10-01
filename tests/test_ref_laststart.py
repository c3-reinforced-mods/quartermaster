"""ref/laststart.py: the CompileFramework error line, the dmscript.source
layout, and where a framework line falls - on the numbers probe_lines and
the Renaissance + Cannons start gave (docs/research/context-2026-09-27.md)."""
import os

import pytest

from ref import laststart as L

LINE = (b"ERROR|  5 |CompileFramework() - compile global script error: Syntax error: "
        b"Line: 39434, Column: 13: Unknown Name")


def test_the_error_line_is_read():
    assert L.parse_error(LINE) == (39434, 13, b"Unknown Name")
    assert L.parse_error(b"LOG|  4 |[qm-guard] clean mods=37") is None
    assert L.parse_error(b"CompileFramework() - compile global script error: no numbers") is None


def test_the_layout_counts_code_lines_and_lists_the_files():
    src = (b"section.begin\r\n   Code : struct.begin\r\n      [*] = ;a\r\n      [*] = ;b\r\n"
           b"   struct.end\r\n   Files : struct.begin\r\n      [*] = .\\data\\scripts\\lib\\x.script\r\n"
           b"      [*] = .\\data\\scripts\\lib\\y.script\r\n   struct.end\r\nsection.end\r\n")
    assert L.source_layout(src) == (2, [b"x.script", b"y.script"])
    assert L.line_count(b"a\r\nb\r\n") == 2 and L.line_count(b"a\r\nb") == 2


def test_a_line_falls_into_its_library_with_a_range():
    libs = [(b"classes.script", 8123, b"the game itself"), (b"parser.script", 99, b"M")]
    # probe_lines: line 1 of classes.script is 69, of parser.script 8193.
    assert L.locate(69, 67, libs)[:4] == (b"classes.script", b"the game itself", 1, 1)
    name, owner, lo, hi, other = L.locate(8193, 67, libs)
    assert (name, owner, hi) == (b"parser.script", b"M", 1)
    # 15 lines back is the end of classes.script: named too.
    assert other == (b"classes.script", b"the game itself") and lo == 1
    assert L.locate(20, 67, libs) is None and L.locate(99999, 67, libs) is None


def test_the_boot_line():
    err = L.parse_error(LINE)
    where = (b"player.script", b"Renaissance", 1414, 1429, None)
    assert L.boot_line(err, where) == (
        b"The last start stopped at \"Error compiling scripts\" (Unknown Name): most likely "
        b"scripts\\lib\\player.script of Renaissance, lines 1414-1429.")
    assert L.boot_line(err, None).endswith(b"; where in the global scripts is not known.")


@pytest.mark.slow
def test_the_renaissance_and_cannons_start_is_found(game_dir):
    """Run ren0-3398700006 (Renaissance, then Cannons): Line 39434 is
    Renaissance's player.script line 1420 (the first use of a name Cannons'
    unit.script does not declare, column 13)."""
    ws = os.path.join(os.path.dirname(os.path.dirname(game_dir)), "workshop", "content", "333420")
    order = [(os.path.join(ws, "3398700006"), b"Renaissance"),
             (os.path.join(ws, "1450025705"), b"Cannons Attack Automatically")]
    if not all(os.path.isdir(d) for d, _t in order):
        pytest.skip("Renaissance and Cannons are not installed")
    van = os.path.join(game_dir, "data", "scripts")
    code, names = L.source_layout(open(os.path.join(van, "dmscript.source"), "rb").read())
    libs = []
    for name in names:
        owner, path = b"the game itself", os.path.join(van, "lib", name.decode())
        for d, title in order:
            p = os.path.join(d, "data", "scripts", "lib", name.decode())
            if os.path.isfile(p):
                owner, path = title, p
        libs.append((name, L.line_count(open(path, "rb").read()), owner))
    name, owner, lo, hi, other = L.locate(39434, code, libs)
    assert (name, owner, other) == (b"player.script", b"Renaissance", None)
    assert lo <= 1420 <= hi
