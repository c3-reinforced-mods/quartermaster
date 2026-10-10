"""qmTrial (src/states/qmtrial.pas), the activation check, run offline on the
script interpreter with the pipeline it drives stood in by Python: which
rows it is about, the pending set it hands the index, what counts as a FAIL
or a WARN, the own files it validates, the mod's own check - and that the
boot's parsers are exactly what they were afterwards."""
import test_m5_pascal as PAS5

QM = PAS5.QM
WASD, BROKEN, VAL, LIBBY = (b"mods\\QMTestWASD", b"mods\\QMTestBroken", b"mods\\QMTestVal",
                            b"mods\\QMTestLibby")
DIRS = [WASD, BROKEN, VAL, LIBBY, QM]
RS = b"gui\\menu.inc\\registershortcuts.inc"
OC = b"gui\\menu.inc\\oncamera.inc"
HK = b"gui\\menu.inc\\hotkeysettings.inc"
DOC = b"gui\\menu.inc\\docreate.inc"


class TrialEngine(PAS5.Engine):
    def n_GetTriggerManagerStateMachineHandle(self, name):
        return {b"qm_core": 7, b"qm_modvaltm": 9}.get(name.lower(), 0)


def setk(eng, parser, keys):
    """eng.set for a dict of keys (`self` is one of qm_mods' keys)."""
    h = eng.named.get(parser.encode()) or eng.n_ParserCreate(parser.encode())
    for k, v in keys.items():
        eng.n_ParserSetValueByKeyByHandle(h, k.encode(), v if isinstance(v, bytes) else b"%d" % v)


def engine(pe, en, compiles=(), files=()):
    """Five rows in this load order, WASD active; `pe` / `en` the window's
    pending and engine flags; `compiles`: the own files qmValFiles passes;
    `files`: extra (relative) files that exist."""
    fs = {QM + b"\\data\\quartermaster\\core.aix": b"x"}
    for f in files:
        fs[f] = b"x"
    eng = TrialEngine(fs, mods=[(d, e == 1, b"") for d, e in zip(DIRS, en)])
    PAS5.load(eng, "qmTrial")
    ui = {"n": 5}
    mods = {"n": 5, "self": 4, "en": 1, "e0": 0}
    for i, d in enumerate(DIRS):
        ui["dir%d" % i], ui["name%d" % i], ui["abid%d" % i] = d, d[5:], d[5:].lower()
        ui["pe%d" % i], ui["en%d" % i], ui["ord%d" % i] = pe[i], en[i], i
        mods["dir%d" % i], mods["ord%d" % i], mods["pos%d" % i] = d, i, i
        mods["on%d" % i], mods["core%d" % i] = en[i], 1 if d == QM else 0
    setk(eng, "qm_ui", ui)
    setk(eng, "qm_mods", mods)
    eng.set("qm_glob", gl0=b"|", gl1=b"|", gl2=b"|", gl3=b"|unit.script|", gl4=b"|")
    eng.set("qm_index", n=3, p0=RS, p1=OC, p2=HK)
    eng.set("qm_plan", n=1, path0=b"boot's plan")
    eng.set("qm_gen", status=b"ok", s0=b"OK")
    eng.seen = {}

    def index():
        m = eng.named[b"qm_mods"]
        eng.seen["on"] = [eng.nodes[m].keys.get(b"on%d" % i) for i in range(5)]
        eng.seen["e"] = [eng.nodes[m].keys.get(b"e%d" % j)
                         for j in range(int(eng.nodes[m].keys[b"en"]))]
        eng.set("qm_index", n=0, cur=9)

    def plan():
        # The decisions a boot of the pending set would take: WASD + Broken
        # merge registershortcuts.inc (positions 0 and 1); Broken alone
        # brings oncamera.inc, Libby hotkeysettings.inc; WASD alone keeps a
        # third file.
        h = eng.named[b"qm_plan"]
        eng.nodes[h].keys = {}
        eng.set("qm_plan", n=4, path0=RS, act0=b"merge-inc", prov0=b"0;1", win0=b"1",
                path1=OC, act1=b"skip", prov1=b"1", win1=b"1",
                path2=HK, act2=b"skip", prov2=b"3", win2=b"3",
                path3=b"gui\\menu.inc\\oninput.inc", act3=b"skip", prov3=b"0", win3=b"0")

    def generate():
        eng.seen["box"] = eng.key(b"qm_gen_in", b"sandbox")
        eng.seen["hooks"] = eng.key(b"qm_gen_in", b"hookdir")
        eng.set("qm_gen", status=b"ok", s0=b"FAIL", x0=b"fallback", s1=b"OK", s2=b"OK",
                s3=b"OK")

    def valfiles():
        n = int(eng.key(b"qm_gen_in", b"vn"))
        eng.seen["own"] = [eng.key(b"qm_gen_in", b"v%d" % k) for k in range(n)]
        eng.seen["vs"] = [eng.key(b"qm_gen_in", b"vs%d" % k) for k in range(n)]
        eng.seen["vbox"] = eng.key(b"qm_gen_in", b"vbox")
        eng.set("qm_gen_v", vn=n, **dict(
            ("vr%d" % k, b"%d|t|%d" % (k, 1 if eng.seen["own"][k].endswith(tuple(compiles)) else 0))
            for k in range(n)))

    def validate():
        eng.seen["modval"] = dict(eng.nodes[eng.named[b"qm_modval"]].keys)
        eng.set("qm_modval", done=1, pn=1, pt0=b"FAIL", px0=b"it needs QMTestWASD2")

    for name, fn in (("qmIndex", index), ("qmPlan", plan), ("qmGenerate", generate),
                     ("qmValFiles", valfiles), ("Validate", validate)):
        eng.states[name.lower()] = PAS5.Fake(fn)
    return eng


def run(eng, row, sig=b"s"):
    eng.set("qm_rt", trrow=row, trsig=sig)
    before = dict((p, dict(eng.nodes[eng.named[p]].keys))
                  for p in (b"qm_mods", b"qm_index", b"qm_plan", b"qm_gen"))
    PAS5.run(eng, "qmTrial")
    after = dict((p, dict(eng.nodes[eng.named[p]].keys)) for p in before)
    return before, after


def lines(eng):
    return [(eng.key(b"qm_ui", b"trt%d" % k), eng.key(b"qm_ui", b"tr%d" % k))
            for k in range(int(eng.key(b"qm_ui", b"trn")))]


def later(eng):
    """The check's LATER lines: what only a start with the row's own global
    scripts loaded can judge - logged and counted, no part of the status."""
    out = [l.split(b"trial LATER ", 1)[1] for l in eng.log if b"trial LATER " in l]
    assert eng.key(b"qm_ui", b"trlater") == b"%d" % len(out)
    return out


def test_a_merge_that_does_not_compile_refuses_the_mod_that_joins_it():
    eng = engine(pe=[1, 1, 0, 0, 1], en=[1, 0, 0, 0, 1], compiles=[b"oncamera.inc"])
    before, after = run(eng, 1)
    assert eng.key(b"qm_ui", b"trst") == b"FAIL"
    assert lines(eng) == [(b"FAIL", RS + b": the merged file does not compile")]
    # The index saw the pending set; the generation went to the sandbox with
    # Quartermaster's own hook lines.
    assert eng.seen["on"] == [b"1", b"1", b"0", b"0", b"1"] and eng.seen["e"] == [b"0", b"1"]
    assert (eng.seen["box"], eng.seen["hooks"]) == (b"*trial", b"qm")
    # Broken's own oncamera.inc was validated as it is, from its folder.
    assert eng.seen["own"] == [PAS5.Engine.APP + BROKEN + b"\\data\\" + OC]
    assert eng.seen["vbox"] == b"*trial"
    # Everything the boot left is back.
    assert before == after
    assert (eng.key(b"qm_ui", b"trrow"), eng.key(b"qm_ui", b"trsig")) == (b"1", b"s")


def test_a_merge_with_a_mod_that_brings_its_own_global_scripts_is_not_certain():
    # Hands-on, 2026-10-10: Reinforced - Core, switched off, could not be
    # activated again - its DoProgress calls its own library, which a game
    # running without it has not loaded, and the merge with the hook was a
    # FAIL. Libby (row 3) brings unit.script and joins the merge here.
    eng = engine(pe=[1, 0, 0, 1, 1], en=[1, 0, 0, 0, 1], compiles=[b"hotkeysettings.inc"])

    def plan():
        h = eng.named[b"qm_plan"]
        eng.nodes[h].keys = {}
        eng.set("qm_plan", n=2, path0=RS, act0=b"merge-inc", prov0=b"0;3", win0=b"3",
                path1=HK, act1=b"skip", prov1=b"3", win1=b"3")
    eng.states["qmplan"] = PAS5.Fake(plan)
    for x in (b"fallback", b"none"):
        eng.states["qmgenerate"] = PAS5.Fake(
            (lambda x: lambda: eng.set("qm_gen", status=b"ok", s0=b"FAIL", x0=x, s1=b"OK"))(x))
        del eng.log[:]
        run(eng, 3)
        # no warning either: the mod may be fine, and the next start tells
        assert eng.key(b"qm_ui", b"trst") == b"OK" and lines(eng) == []
        assert later(eng) == [RS + b" does not compile merged with the global scripts "
                              b"loaded now; a mod in it brings its own, so it is built again "
                              b"at the next start"]
    # a data merge that was refused is no question of scripts
    eng.states["qmgenerate"] = PAS5.Fake(lambda: eng.set(
        "qm_gen", status=b"ok", s0=b"FAIL", x0=b"datafail", e0=b"two records", s1=b"OK"))
    run(eng, 3)
    assert lines(eng) == [(b"FAIL", RS + b": two records")]


def test_an_own_file_that_does_not_compile_is_a_fail():
    eng = engine(pe=[1, 1, 0, 0, 1], en=[1, 0, 0, 0, 1],
                 files=[BROKEN + b"\\data\\" + DOC])
    run(eng, 1)
    assert lines(eng) == [(b"FAIL", RS + b": the merged file does not compile"),
                          (b"FAIL", OC + b" does not compile"),
                          (b"FAIL", DOC + b" does not compile")]


def test_a_row_the_check_is_not_about_is_not_blamed():
    # WASD's own file and the merge Broken joins are not Libby's business.
    eng = engine(pe=[1, 1, 0, 1, 1], en=[1, 1, 0, 0, 1])
    run(eng, 3)
    # Libby brings its own global scripts: its file that does not compile
    # with the loaded ones is for the next start to judge. Until 0.1.4 that
    # was a WARN: Reinforced - Core, which is fine, showed WARN with 24 of
    # them and OK after the restart (hands-on, 2026-10-10).
    assert eng.key(b"qm_ui", b"trst") == b"OK" and lines(eng) == []
    assert len(later(eng)) == 1
    assert later(eng)[0].startswith(HK + b" does not compile with the global scripts")


def test_the_check_of_apply_is_about_every_row_it_switches_on():
    eng = engine(pe=[1, 1, 0, 1, 1], en=[1, 0, 0, 0, 1], compiles=[b"oncamera.inc"])
    run(eng, -1)
    assert [t for t, _x in lines(eng)] == [b"FAIL"] and len(later(eng)) == 1


def test_the_mods_own_check_sees_the_pending_set_and_can_refuse():
    eng = engine(pe=[1, 0, 1, 0, 1], en=[1, 0, 0, 0, 1],
                 files=[VAL + b"\\data\\quartermaster\\validate.aix"])
    # WASD declares an id in its about.cfg, the others have none.
    eng.set("qm_about", n=5, id0=b"mywasd")
    run(eng, 2)
    assert lines(eng) == [(b"FAIL", b"QMTestVal: it needs QMTestWASD2")]
    mv = eng.seen["modval"]
    assert mv[b"dir"] == VAL and mv[b"n"] == b"5"
    assert [mv[b"dir%d" % k] for k in range(5)] == DIRS
    assert [mv[b"on%d" % k] for k in range(5)] == [b"1", b"0", b"1", b"0", b"1"]
    assert mv[b"done"] == b"0"
    # The declared id, empty without one - never the folder the window falls
    # back to (abid): a folder named like a required id is not that mod.
    assert [mv.get(b"id%d" % k, b"") for k in range(5)] == [b"mywasd", b"", b"", b"", b""]


def test_rows_that_are_not_the_boots_skip_the_check():
    eng = engine(pe=[1, 1, 0, 0, 1], en=[1, 0, 0, 0, 1])
    eng.set("qm_ui", dir2=b"mods\\Other")
    before, after = run(eng, 1)
    assert eng.key(b"qm_ui", b"trst") == b"SKIP" and "on" not in eng.seen
    assert before == after


def test_global_scripts_are_compiled_against_the_loaded_ones_but_classes():
    # Libby brings lib\unit.script and lib\classes.script: unit.script is
    # validated as a script (vs = 1) and does not compile - for the next
    # start to judge, since it may need the mod's own other scripts;
    # classes.script cannot be compiled in a running game at all (probe
    # cls-111839), and a line says so. Neither is a warning.
    eng = engine(pe=[1, 0, 0, 1, 1], en=[1, 0, 0, 0, 1], compiles=[b"hotkeysettings.inc"])
    eng.set("qm_glob", gl3=b"|lib\\unit.script|lib\\classes.script|")
    run(eng, 3)
    assert eng.seen["own"] == [PAS5.Engine.APP + LIBBY + b"\\data\\" + HK,
                               PAS5.Engine.APP + LIBBY + b"\\data\\scripts\\lib\\unit.script"]
    assert eng.seen["vs"] == [b"0", b"1"]
    assert eng.key(b"qm_ui", b"trst") == b"OK" and lines(eng) == []
    texts = later(eng)
    assert texts[0] == b"scripts\\lib\\classes.script is not checked: a running game cannot compile it"
    assert texts[1].startswith(b"scripts\\lib\\unit.script does not compile with the global scripts")
