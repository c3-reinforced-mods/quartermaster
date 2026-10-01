"""qmDataMerge (src/states/qmdatamerge.pas) run offline on the script
interpreter against its twin ref/records.py: the same records, decisions,
report lines, checks and output bytes, on the installed game's data files
and edits of them. objcustom.cfg is cut to its first records for the
interpreter's sake (the game reads the whole file; the in-game run has it).

The emulated engine: files by path, the raw reader and writer of the other
desk checks, StrTrim, and the engine's parser loading a staged data file as
its records (the trial load, plan S10) - the in-game run checks the real one.
"""
import os

import pytest

import test_m5_pascal as PAS5
from ref import records as R
from ref import textio as T

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Cossacks 3"
VAR = os.path.join(GAME, "data", "game", "var")
APP = PAS5.APP
WORK = PAS5.SAVE + b"quartermaster\\val\\"


class Engine(PAS5.Engine):
    def n_StrTrim(self, s):
        return s.strip(b" ")

    def n_ParserLoadFromFileByHandle(self, h, path):
        data = self._file(path)
        if data is None:
            return False
        if path.startswith(WORK):
            sp = R.split(T.read_lines(data), R.PROFILES[self.profile_path])
            self.nodes[h].records = len(sp.records) if sp else -1
            return sp is not None
        return PAS5.Engine.n_ParserLoadFromFileByHandle(self, h, path)

    def n_ParserGetCountByHandle(self, h):
        n = getattr(self.nodes[h], "records", None)
        if n is not None:
            return n
        return PAS5.Engine.n_ParserGetCountByHandle(self, h)

    def n_ParserClearByHandle(self, h):
        self.nodes[h].records = None
        PAS5.Engine.n_ParserClearByHandle(self, h)


def raw(name):
    with open(os.path.join(VAR, name), "rb") as fh:
        return fh.read()


def lines_of(data):
    return T.read_lines(data)


def crlf(lines):
    return b"".join(T.unescape(ln) + b"\r\n" for ln in lines)


def run_job(path, base, mods, names=None, glob=None):
    """The game side on `base` + `mods` (bytes), and the twin on the same."""
    names = names or [b"Mod%d" % i for i in range(len(mods))]
    files = {APP + b"data\\" + path: base}
    keys = {"jobs": 1, "j0path": path, "j0base": APP + b"data\\" + path, "j0parts": len(mods),
            "j0out": WORK + b"d0.cfg"}
    for i, data in enumerate(mods):
        p = APP + b"mods\\M%d\\data\\" % i + path
        files[p] = data
        keys["j0p%d" % i] = p
        keys["j0n%d" % i] = names[i]
    gpath = APP + b"data\\scripts\\dmscript.global"
    files[gpath] = glob if glob is not None else b"   gc_formation_maxcount = 160;\r\n"
    keys["j0glob"] = gpath
    eng = Engine(files)
    eng.profile_path = path
    eng.set("qm_dm_in", **keys)
    PAS5.load(eng, "qmDataMerge")
    PAS5.run(eng, "qmDataMerge")
    limits = R.limits_from_global(lines_of(files[gpath]))
    m = R.merge(lines_of(base), [lines_of(d) for d in mods], R.PROFILES[path], names, limits)
    got_notes = [(eng.key(b"qm_dm", b"j0t%d" % k), eng.key(b"qm_dm", b"j0x%d" % k))
                 for k in range(int(eng.key(b"qm_dm", b"j0nl")))]
    return eng, m, got_notes


def check_parity(eng, m, got):
    assert eng.key(b"qm_dm", b"j0done") == b"1"
    assert got == m.lines_out
    assert eng.key(b"qm_dm", b"j0st") == m.status
    if m.status != R.FAIL:
        assert eng.written[WORK + b"d0.cfg"] == T.write_file(m.lines)
        tok = eng.key(b"qm_dm", b"j0tok")
        seq = eng.key(b"qm_dm", b"j0seq")
        assert tok and eng.key(b"qm_val", b"d" + seq) == tok
    else:
        assert WORK + b"d0.cfg" not in eng.written
        assert eng.key(b"qm_dm", b"j0err") == next(t for g, t in m.lines_out if g == R.FAIL)


HK = b"game\\var\\hotkeys.cfg"
FORM = b"game\\var\\formations.cfg"
WALL = b"game\\var\\wallcustom.cfg"
OBJ = b"game\\var\\objcustom.cfg"


def edit(data, old, new):
    assert data.count(old) >= 1
    return data.replace(old, new, 1)


def test_hotkeys_two_mods_different_records():
    base = raw("hotkeys.cfg")
    a = edit(base, b"      Key = H\r\n", b"      Key = Y\r\n")
    b = edit(base, b"      Key = L\r\n", b"      Key = F6\r\n")
    check_parity(*run_job(HK, base, [a, b], [b"WASD", b"Other"]))


def test_hotkeys_conflict_removal_addition_and_a_new_collision():
    base = raw("hotkeys.cfg")
    # A: house on F6, barracks on F8; B: blacksmith on F6 (a new collision
    # with A's house), barracks on F9 (a conflict: B's wins), cen removed.
    a = edit(base, b"      Key = H\r\n", b"      Key = F6\r\n")
    a = edit(a, b"      Key = B\r\n", b"      Key = F8\r\n")
    b = edit(base, b"      Key = L\r\n", b"      Key = F6\r\n")
    b = edit(b, b"      Key = B\r\n", b"      Key = F9\r\n")
    first = b.index(b"   [*] : struct.begin")
    end = b.index(b"   struct.end\r\n", first) + len(b"   struct.end\r\n")
    b = b[:first] + b[end:]                          # a record removed
    c = edit(base, b"section.end", b"   [*] : struct.begin\r\n      Key = F9\r\n"
             b"      Action = event|qmtest\r\n   struct.end\r\nsection.end")
    eng, m, got = run_job(HK, base, [a, b, c], [b"A", b"B", b"C"])
    assert m.status == R.WARN
    assert any(b"are on it now" in t for _g, t in m.lines_out)
    check_parity(eng, m, got)


def test_formations_past_the_bound_and_a_total_conversion_s_bound():
    base = raw("formations.cfg")

    def plus(names):
        extra = b"".join(b"   [*] : struct.begin\r\n      id = %s\r\n   struct.end\r\n" % n for n in names)
        return edit(base, b"section.end", extra + b"section.end")
    a = plus([b"QMA%d" % i for i in range(6)])
    b = plus([b"QMB%d" % i for i in range(6)])
    eng, m, got = run_job(FORM, base, [a, b])
    assert m.status == R.FAIL
    check_parity(eng, m, got)
    glob = b"   gc_formation_maxcount = 203{188}; //165 158  140 awar\r\n"
    eng, m, got = run_job(FORM, base, [a, b], glob=glob)
    assert m.status == R.OK
    check_parity(eng, m, got)


def test_wallcustom_and_a_file_that_is_not_the_layout():
    base = raw("wallcustom.cfg")
    a = edit(base, b"      WallVariation = 1\r\n", b"      WallVariation = 1\r\n      // qm\r\n")
    check_parity(*run_job(WALL, base, [a, base[:-40]]))
    check_parity(*run_job(WALL, base, [a, edit(base, b"            y = 0.9\r\n", b"            y = 0.8\r\n")]))


def objcustom_head(n):
    """vanilla objcustom.cfg cut after its first n records."""
    data = raw("objcustom.cfg")
    lines = T.read_lines(data)
    sp = R.split(lines, R.PROFILES[OBJ])
    cut = R.Split(sp.header, sp.records[:n], sp.trailer)
    return crlf(R.join(cut))


def test_objcustom_records_and_the_exit_point_bound():
    base = objcustom_head(6)
    a = edit(base, b"            x = -0.04\r\n", b"            x = -0.05\r\n")          # ausbar
    b = edit(base, b"sid = swetem", b"sid = swetem\r\n      // qm edit")
    check_parity(*run_job(OBJ, base, [a, b]))
    point = b"         [*] : struct.begin\r\n            x = 0\r\n            y = 0\r\n            z = 0\r\n         struct.end\r\n"
    five = edit(base, b"      ExitPoints : struct.begin\r\n", b"      ExitPoints : struct.begin\r\n" + point * 3)
    eng, m, got = run_job(OBJ, base, [five, b])
    # the five points come from an input that already has them: allowed
    assert m.status == R.OK
    check_parity(eng, m, got)
