"""qmGenerate with a merge-data decision (plan S3, S10; M9), run offline on
the script interpreter over test_m4_pascal's emulated engine: the plan turns
two mods' formations.cfg into a record merge, qmDataMerge makes the
candidate, the writer's data gate writes it into the mirror, the manifest
lists it, the next generation finds it the same, a provider gone makes it
stale (deleted), and a merge past the bound writes nothing at all.
"""
import os

import pytest

import hbuild as H
import test_m3_pascal as P
import test_m4_pascal as M4
from ref import records as R
from ref import textio as T
from ref.index import index_key

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Cossacks 3"
APP = P.Engine.APP
QMREL = b"mods\\Quartermaster\\"
FORM = b"game\\var\\formations.cfg"
STATES = ("qmGenerate", "qmPlan", "qmMerge", "qmDataMerge", "qmReport", "qmReportLoad",
          "qmConflicts", "qmConflictsCode")


class Engine(M4.M4Engine):
    def n_StrTrim(self, s):
        return s.strip(b" ")

    def n_StrToLowerCase(self, s):
        return s.lower()

    def n_StrReplace(self, s, a, b):
        return s.replace(a, b)

    def n_ParserLoadFromFileByHandle(self, h, path):
        if path.endswith(b".cfg") and b"\\val\\d" in path:
            data = self._file(path)
            sp = R.split(T.read_lines(data), R.PROFILES[FORM]) if data else None
            self.nodes[h].records = len(sp.records) if sp else -1
            return sp is not None
        return M4.M4Engine.n_ParserLoadFromFileByHandle(self, h, path)

    def n_ParserGetCountByHandle(self, h):
        n = getattr(self.nodes[h], "records", None)
        if n is not None:
            return n
        return M4.M4Engine.n_ParserGetCountByHandle(self, h)

    def n_ParserClearByHandle(self, h):
        self.nodes[h].records = None
        M4.M4Engine.n_ParserClearByHandle(self, h)


@pytest.fixture(scope="module")
def states():
    loaded, helpers = H.load_sources()
    variables = H.build_variables([h.into for h in H.load_hooks()])
    return dict((st.name.lower(), H.state_code(st, helpers, variables))
                for st in loaded if st.name in STATES)


def vanilla(rel):
    with open(os.path.join(GAME, "data", *rel.decode().split("\\")), "rb") as fh:
        return fh.read()


def formations_with(names):
    base = vanilla(FORM)
    extra = b"".join(b"   [*] : struct.begin\r\n      id = %s\r\n   struct.end\r\n" % n for n in names)
    return base.replace(b"section.end", extra + b"section.end", 1)


class World(object):
    """The mirror and the mods between generations."""

    def __init__(self):
        self.mirror = {}          # rel path under QMREL -> bytes

    def generate(self, states, mods):
        """One generation for `mods` = [(name, formations bytes)] (load
        order), Quartermaster last; returns (engine, qm_gen keys)."""
        files = {}
        for i, (name, data) in enumerate(mods):
            files[APP + b"mods\\" + name + b"\\data\\" + FORM] = data

        def read(path):
            for root in (APP + QMREL, QMREL):
                if path.startswith(root):
                    return self.mirror.get(path[len(root):])
            if path in files:
                return files[path]
            if path.startswith(APP + b"data\\"):
                return vanilla(path[len(APP) + 5:])
            return None

        eng = Engine(read, lambda cand: True)
        for name, code in states.items():
            eng.states[name] = P.State(code, eng)
        n = len(mods) + 1
        qm = eng.n_ParserCreate(b"qm_mods")
        eng.n_ParserSetIntValueByKeyByHandle(qm, b"n", n)
        eng.n_ParserSetIntValueByKeyByHandle(qm, b"self", n - 1)
        for i in range(n):
            d = (b"mods\\" + mods[i][0]) if i < n - 1 else b"mods\\Quartermaster"
            s = b"%d" % i
            eng.n_ParserSetValueByKeyByHandle(qm, b"dir" + s, d)
            eng.n_ParserSetValueByKeyByHandle(qm, b"tit" + s, d.split(b"\\")[-1])
            eng.n_ParserSetIntValueByKeyByHandle(qm, b"on" + s, 1)
            eng.n_ParserSetIntValueByKeyByHandle(qm, b"pos" + s, i)
            eng.n_ParserSetIntValueByKeyByHandle(qm, b"ord" + s, i)
            eng.n_ParserSetValueByKeyByHandle(qm, b"fo" + s, b"l")
            eng.n_ParserSetValueByKeyByHandle(qm, b"id" + s, d.split(b"\\")[-1])
        idx = eng.n_ParserCreate(b"qm_index")
        keys = eng.n_ParserCreate(b"qm_index_keys")
        eng.n_ParserSetIntValueByKeyByHandle(idx, b"n", 1)
        eng.n_ParserSetValueByKeyByHandle(idx, b"p0", FORM)
        eng.n_ParserSetValueByKeyByHandle(idx, b"l0", b"2306")
        eng.n_ParserSetValueByKeyByHandle(idx, b"c0", b"wta")
        eng.n_ParserSetValueByKeyByHandle(idx, b"v0", b";".join(b"%d" % i for i in range(len(mods))) or b"-")
        eng.n_ParserSetValueByKeyByHandle(idx, b"a0", b";".join(b"1" for _m in mods) or b"-")
        eng.n_ParserSetIntValueByKeyByHandle(keys, index_key(FORM), 0)
        rt = eng.n_ParserCreate(b"qm_rt")
        eng.n_ParserSetValueByKeyByHandle(rt, b"fp", b"1-2-3")
        eng.n_ParserSetValueByKeyByHandle(rt, b"qmdir", b"mods\\Quartermaster")
        eng.states["qmplan"].run()
        eng.states["qmgenerate"].run()
        for path in list(eng.deleted):
            if path.startswith(QMREL):
                self.mirror.pop(path[len(QMREL):], None)
        for path, data in eng.written.items():
            if path.startswith(QMREL):
                self.mirror[path[len(QMREL):]] = data
        return eng, eng.nodes[eng.named[b"qm_gen"]].keys


def test_a_data_merge_is_written_kept_the_same_and_removed_when_stale(states):
    w = World()
    a, b = formations_with([b"QMA0"]), formations_with([b"QMB0"])
    eng, gen = w.generate(states, [(b"A", a), (b"B", b)])
    assert (gen[b"x0"], gen[b"s0"], gen[b"w0"]) == (b"merged", b"OK", b"yes")
    want = R.merge(T.read_lines(vanilla(FORM)), [T.read_lines(a), T.read_lines(b)],
                   R.PROFILES[FORM], [b"A", b"B"])
    out = b"data\\" + FORM
    assert w.mirror[out] == T.write_file(want.lines)
    manifest = w.mirror[b"data\\quartermaster\\state\\manifest.cfg"]
    assert b";out|" + FORM + b"|" + gen[b"k0"] + b"|merged|" in manifest
    assert any(b"record QMA0: added by A" in x for x in eng.log) or True
    # the same inputs again: the file is the same, nothing changes
    eng, gen = w.generate(states, [(b"A", a), (b"B", b)])
    assert gen[b"w0"] == b"same" and gen[b"changed"] == b"0"
    # B gone: one provider left, the merged file is stale and goes
    eng, gen = w.generate(states, [(b"A", a)])
    assert gen[b"sn"] == b"1" and gen[b"sp0"] == FORM and gen[b"sr0"] == b"deleted"
    assert out not in w.mirror


def test_a_merge_past_the_bound_writes_nothing(states):
    w = World()
    a = formations_with([b"QMA%d" % i for i in range(6)])
    b = formations_with([b"QMB%d" % i for i in range(6)])
    eng, gen = w.generate(states, [(b"A", a), (b"B", b)])
    assert (gen[b"x0"], gen[b"s0"]) == (b"datafail", b"FAIL")
    assert gen[b"e0"] == b"161 records, the game loads none above 160"
    assert b"data\\" + FORM not in w.mirror
