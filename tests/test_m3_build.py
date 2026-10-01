"""Gates for the game-side diff and merge sources (src/lib/qmdiff*.pas,
src/lib/qmmerge*.pas, src/states/qmm3*.pas): they lint clean the way the build
lints them, stay inside the array budget, carry ref's constants, keep to the
dialect, and touch files only through their two seams."""
import os
import re

import pytest

import hbuild as H
from ref import diff as D
from ref.merge import PROXIMITY_LINES

LIB = os.path.join(H.SRC, "lib")
MINE_LIB = ("qmdiff.pas", "qmdiffsrc.pas", "qmmerge.pas", "qmmergeout.pas")
MINE_STATES = ("qmMerge", "qmCaseMerge")


def source(name):
    with open(os.path.join(LIB, name), "rb") as fh:
        return fh.read().decode("ascii")


def body(name):
    """Code lines only: notes (`//!`) and comments dropped."""
    out = []
    for line in source(name).split("---\n", 1)[1].splitlines():
        if not line.strip().startswith("//"):
            out.append(line)
    return "\n".join(out)


@pytest.fixture(scope="module")
def emitted():
    states, helpers = H.load_sources()
    mine = [s for s in states if s.name in MINE_STATES]
    assert sorted(s.name for s in mine) == sorted(MINE_STATES)
    out = {}
    for st in mine:
        code = H.state_code(st, helpers, H.BUILD_VARIABLES)
        out[st.name] = (st, H.aix_section(st.name.encode(), code))
    return out


def test_the_states_go_where_the_runner_and_the_boot_find_them(emitted):
    assert emitted["qmMerge"][0].into == "data/quartermaster/core.aix"
    assert emitted["qmCaseMerge"][0].into == "data/quartermaster/selftest.aix"


def test_lint_offline_finds_nothing(emitted):
    for name, (st, section) in emitted.items():
        assert H.lint_state(st.into, name, section, 0, None) == [], name


def test_lint_against_the_installed_game_finds_nothing(emitted, game_dir):
    env = H.LintEnv.from_game(game_dir)
    for name, (st, section) in emitted.items():
        found = H.lint_state(st.into, name, section, 0, env)
        assert found == [], "\n".join(str(f) for f in found)


def array_totals(section, where):
    unit = H.gscript.parse(where, section)
    byref = H._by_reference_arrays(unit.code)
    consts = {m.group(1).lower(): m.group(2) for m in H._LOCAL_CONST.finditer(unit.code)}
    totals = {"integer": 0, "string": 0}
    for offset, dims, element in H.declared_arrays(unit.code):
        if offset in byref:
            continue
        count = 1
        for dim in dims:
            lo, hi = dim.split(b"..")
            count *= H.eval_int(hi, consts) - H.eval_int(lo, consts) + 1
        totals["string" if element.lower() == b"string" else "integer"] += count
    return totals


def test_array_budget(emitted):
    """One String array only - the read pool: a String array costs ~4.6 us
    per element on every call, so the merge state has no other."""
    merge = array_totals(emitted["qmMerge"][1], "core.aix")
    pool = H.RAW_CAP + 1
    heads = 3 * (H.INC_HEAD + 1)
    assert merge == {"integer": 883310, "string": pool + heads}   # the report's figures
    assert merge["integer"] <= H.INTEGER_BUDGET and merge["string"] <= H.STRING_BUDGET
    case = array_totals(emitted["qmCaseMerge"][1], "selftest.aix")
    assert case == {"integer": 0, "string": 20}


def rendered(emitted):
    return emitted["qmMerge"][1].decode("ascii")


def bound(text, name):
    m = re.search(r"var %s : array \[0\.\.(\d+)(-1)?\] of Integer;" % name, text)
    assert m, name
    return int(m.group(1)) + (0 if m.group(2) else 1)


def const(text, name):
    m = re.search(r"const %s = (\d+);" % name, text)
    assert m, name
    return int(m.group(1))


def test_constants_are_refs(emitted):
    text = rendered(emitted)
    cap = D.d_cap(D.DEFAULT_BUDGET)
    assert const(text, "qmDfCap") == cap == 998
    # The parity-compact trace holds exactly rounds 0..cap.
    assert bound(text, "qmDfT") == D.trace_cells(cap) <= D.DEFAULT_BUDGET
    assert D.trace_cells(cap + 1) > D.DEFAULT_BUDGET
    assert const(text, "qmLnCap") == D.MAX_LINES
    assert bound(text, "qmLnVh") == bound(text, "qmLnPh") == D.MAX_LINES
    for name in ("qmDfEd", "qmDfEx", "qmDfEy", "qmDfHs", "qmDfHe", "qmDfHms", "qmDfHme"):
        assert bound(text, name) == cap + 1, name
    pmax, hcap = const(text, "qmMgPmax"), const(text, "qmMgHcap")
    assert hcap + 1 >= pmax * cap              # the hunk pool can never overflow
    for name in ("qmMgHp", "qmMgHs", "qmMgHe", "qmMgHms", "qmMgHme", "qmMgHk",
                 "qmMgHby", "qmMgHbk", "qmMgHwon", "qmMgHdup", "qmMgHprx", "qmMgHch"):
        assert bound(text, name) == hcap + 1, name
    for name in ("qmMgPc", "qmMgPm", "qmMgPok", "qmMgPwhy", "qmMgPd", "qmMgPdel",
                 "qmMgPins", "qmMgPcl", "qmMgPrep", "qmMgPsq", "qmMgPh0", "qmMgPh1",
                 "qmMgPtr"):
        assert bound(text, name) == pmax, name
    assert bound(text, "qmMgAt") == D.MAX_LINES + 1     # insertions at line n too
    assert const(text, "qmMgNear") == PROXIMITY_LINES


def test_the_limits_come_from_the_build():
    """One definition: the diff constants are the build's, taken from ref."""
    assert "const qmDfCap = ${dcap};" in source("qmdiff.pas")
    assert "const qmLnCap = ${maxlines};" in source("qmdiff.pas")
    assert H.BUILD_VARIABLES["dcap"] == D.d_cap() and H.BUILD_VARIABLES["maxlines"] == D.MAX_LINES


def test_the_dialect_rules_of_the_capability_probes():
    for name in MINE_LIB:
        code = body(name)
        assert not re.search(r"function\s+\w+\s*\([^)]*\)\s*:\s*String", code, re.I), name
        assert not re.search(r"function\s+\w+\s*\([^)]*\)\s*:\s*Boolean", code, re.I), name
        assert not re.search(r"\barray\s+of\b", code, re.I), name
        assert not re.search(r"\b(SetLength|High|Length|Chr)\s*\(", code, re.I), name
        assert not re.search(r"#\d+\s*#", code), name        # adjacent char literals


def test_diff_and_merge_touch_files_only_through_the_seams():
    """qmdiff and qmmerge read lines through qmdiffsrc and write the final line
    list through qmmergeout; only named parsers as key/value stores remain."""
    file_io = r"\b(ParserGetValueByIndex\w*|ParserSetValueByIndex|ParserLoadFromFile\w*|" \
              r"ParserSaveToFile\w*|ParserSelectByHandleByKey|ParserGetCountByHandle|" \
              r"qmIncLoad|qmIncReadAt|qmRawRead\w*|qmIncBegin|qmIncLine|qmIncEnd|" \
              r"qmIncRender|qmRawWrite\w*)\b"
    for name in ("qmdiff.pas", "qmmerge.pas"):
        assert not re.findall(file_io, body(name)), name
    assert "'[*]'" not in "".join(body(n) for n in MINE_LIB)


def test_the_seams_use_the_raw_reader_and_writer():
    """Lossless in, the engine's layout by count out - never the parser, which
    drops trailing spaces on load and appends one value only (run m2a)."""
    reader, writer = body("qmdiffsrc.pas"), body("qmmergeout.pas")
    assert "qmIncReadAt(" in reader and "qmIncLoad" not in reader
    assert "qmIncBegin(" in writer and "qmIncLine(" in writer and "qmIncEnd(" in writer
    assert not re.search(r"\bParser\w*\(", reader + writer)
    assert "qmIncHookIndex(qmLnPool" in body("qmmerge.pas")
