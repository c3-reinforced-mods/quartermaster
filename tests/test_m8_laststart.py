"""qmLastStart (src/states/qmlaststart.pas) run offline on the script
interpreter against its twin ref/laststart.py: the previous start's log, the
failed start's mods from compile.prev.cfg, the vanilla dmscript.source and
the libraries in effect give the Boot line, byte for byte the twin's."""
import test_m5_pascal as PAS5
from ref import laststart as L
from ref import report as RP

APP, SAVE = PAS5.APP, PAS5.SAVE
PREV = SAVE + b"quartermaster\\compile.prev.cfg"
LOG = SAVE + b"log\\"

SOURCE = (b"section.begin\r\n   Code : struct.begin\r\n      [*] = ;a\r\n      [*] = ;b\r\n"
          b"      [*] = ;c\r\n   struct.end\r\n   Files : struct.begin\r\n"
          b"      [*] = .\\data\\scripts\\lib\\one.script\r\n"
          b"      [*] = .\\data\\scripts\\lib\\two.script\r\n"
          b"      [*] = .\\data\\scripts\\lib\\three.script\r\n   struct.end\r\nsection.end\r\n")


def lines(n, end=b"\r\n"):
    return b"".join(b"x%d;\r\n" % i for i in range(n - 1)) + b"last;" + end


def flat(keys):
    return (b"section.begin\r\n" + b"".join(b"   %s = %s\r\n" % kv for kv in keys)
            + b"section.end\r\n")


class Engine(PAS5.Engine):
    """compile.prev.cfg is the engine parser's flat file (the guard saves it)."""
    def n_ParserLoadFromFileByHandle(self, h, path):
        if path == PREV:
            data = self._file(path)
            if data is None:
                return False
            n = self.nodes[h]
            n.keys, n.code, n.inc = dict(RP.parser_read_flat(data)), None, None
            return True
        return PAS5.Engine.n_ParserLoadFromFileByHandle(self, h, path)


def run(fs, ages):
    eng = Engine(fs, ages)
    PAS5.load(eng, "qmLastStart")
    PAS5.run(eng, "qmLastStart")
    return eng


def base(error_line):
    fs = {APP + b"data\\scripts\\dmscript.source": SOURCE,
          APP + b"data\\scripts\\lib\\one.script": lines(10),
          APP + b"data\\scripts\\lib\\two.script": lines(20),
          APP + b"data\\scripts\\lib\\three.script": lines(5, end=b""),
          APP + b"mods\\Mine\\data\\scripts\\lib\\two.script": lines(30),
          PREV: flat([(b"n", b"2"), (b"d0", b"mods\\Mine"), (b"t0", b"My Mod"),
                      (b"d1", b"mods\\Quartermaster"), (b"t1", b"Quartermaster")]),
          LOG + b"cos_260930_080225.log": (b"TIMER|  0 |start\r\nLOG|  4 |[qm-guard] clean\r\n"
                                          + error_line + b"\r\nLOG| 11 |more\r\n"),
          LOG + b"cos_260930_080300.log": b"LOG|  0 |this start\r\n"}
    ages = {LOG + b"cos_260930_080225.log": 100, LOG + b"cos_260930_080300.log": 200}
    return fs, ages


def twin(fs, n_line):
    code, names = L.source_layout(fs[APP + b"data\\scripts\\dmscript.source"])
    libs = []
    for name in names:
        owner, data = b"the game itself", fs[APP + b"data\\scripts\\lib\\" + name]
        mine = APP + b"mods\\Mine\\data\\scripts\\lib\\" + name
        if mine in fs:
            owner, data = b"My Mod", fs[mine]
        libs.append((name, L.line_count(data), owner))
    err = L.parse_error(n_line)
    return L.boot_line(err, L.locate(err[0], code, libs))


def err(n, col=13):
    return (b"ERROR|  5 |CompileFramework() - compile global script error: Syntax error: "
            b"Line: %d, Column: %d: Unknown Name" % (n, col))


def test_the_failed_start_is_named_as_the_twin_names_it():
    # code 3 -> one.script is framework lines 5..14 (and 15), two.script (My Mod's,
    # 30 lines) from 16: line 27 is its line 12; 15 back is the end of one.script.
    fs, ages = base(err(27))
    eng = run(fs, ages)
    key = lambda k: eng.key(b"qm_ls", k)
    assert (key(b"prev"), key(b"found"), key(b"n"), key(b"col")) == (
        b"cos_260930_080225.log", b"1", b"27", b"13")
    assert (key(b"lib"), key(b"owner"), key(b"lo"), key(b"hi")) == (b"two.script", b"My Mod", b"1", b"12")
    assert (key(b"olib"), key(b"oown")) == (b"one.script", b"the game itself")
    assert key(b"line") == twin(fs, err(27))
    assert key(b"line").startswith(b"The last start stopped at \"Error compiling scripts\" (Unknown Name)")


def test_a_line_deep_in_a_library_names_it_alone():
    fs, ages = base(err(40))
    eng = run(fs, ages)
    assert eng.key(b"qm_ls", b"line") == twin(fs, err(40))
    assert eng.key(b"qm_ls", b"olib") == b""
    assert b"two.script of My Mod, lines 10-25." in eng.key(b"qm_ls", b"line")


def test_without_the_error_or_the_record_it_says_what_it_knows():
    fs, ages = base(b"LOG|  5 |...DoCreate started...")
    eng = run(fs, ages)
    assert (eng.key(b"qm_ls", b"found"), eng.key(b"qm_ls", b"line")) == (b"0", b"")
    fs, ages = base(err(27))
    del fs[PREV]
    eng = run(fs, ages)
    assert eng.key(b"qm_ls", b"line") == L.boot_line(L.parse_error(err(27)), None)
    # no earlier log at all
    fs, ages = base(err(27))
    del fs[LOG + b"cos_260930_080225.log"]
    eng = run(fs, ages)
    assert (eng.key(b"qm_ls", b"prev"), eng.key(b"qm_ls", b"line")) == (b"", b"")
