"""tools/pascov.py and the interpreter's statement trace behind it: every
emitted line maps back to the src line it came from, and a run records the
lines whose statement ran."""
import os

import pascov as P
import test_m3_pascal as PAS

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_every_emitted_line_maps_back_to_its_source_line():
    units = P.units()        # stops when a unit's lines and origins disagree in number
    names = set(n for n, _c, _w in units)
    assert {"qmBoot", "qmGuard", "ShowQmManager", "cameracontrol"} <= names
    sources = {}
    for name, code, where in units:
        for line, origin in zip(code, where):
            if origin is None:
                continue
            path, n = origin
            if path not in sources:
                with open(os.path.join(REPO, *path.split("/")), "rb") as fh:
                    sources[path] = [l.rstrip(b"\r") for l in fh.read().split(b"\n")]
            raw = sources[path][n - 1]
            if b"${" not in raw:
                assert line == raw, (name, path, n)


def test_statement_lines_count_what_does_something():
    lines, flat = P.statement_lines("var a: integer;\nif a = 0 then\n  a := 1;\nLog('x');")
    assert lines == {2, 3, 4} and not flat
    # A record field the interpreter cannot read: counted, and said so.
    lines, flat = P.statement_lines("if gGame.gamemode = 1 then\n  Log('x');")
    assert lines == {1, 2} and flat


def test_the_interpreter_records_the_lines_that_ran(monkeypatch):
    monkeypatch.setattr(PAS, "PASCOV", "on")
    monkeypatch.setattr(PAS, "COVERAGE", {})
    code = [b"var a: integer;", b"if a = 1 then", b"  Log('no');", b"Log('yes');",
            b"procedure p; begin Log('never'); end;"]
    PAS.State(code, PAS.Engine(lambda path: None)).run()
    [(lines, ran)] = PAS.COVERAGE.values()
    assert lines == {2, 3, 4, 5} and ran == {2, 4}


def test_a_state_built_from_fewer_lines_is_aligned_to_its_unit():
    units = [(n, P.text_of(c), w, P.text_of(c).split("\n")) for n, c, w in P.units()]
    name, text, _where, lines = next(u for u in units if u[0] == "qmModFiles")
    part = lines[40:]                 # as if the first helpers were left out
    hit = P.match("\n".join(part), {}, {}, units)
    assert hit is not None
    unit, mapping = hit
    assert unit[0] == name and mapping[1] == 41 and mapping[len(part)] == len(lines)
