"""qmAbout (src/states/qmabout.pas) run offline on the script interpreter,
against its twin ref/about.py: every registered mod's about.cfg read into
qm_about exactly as the twin parses it - values, problems, settings, names
and the load-order constraints."""
import pytest

import test_m5_pascal as PAS5
from ref import about as A
from ref import textio as T

QM = PAS5.QM
W = PAS5.W

FILES = {
    b"mods\\QMTestWASD": (b"\xef\xbb\xbf# WASD camera\r\n  ID = QMTestWASD\r\nname = WASD camera\t\r\n"
                          b"version=1.2\r\nType = Mod\r\nexclusive = camera; hotkeys;\r\n"
                          b"requires = 1325221799 ; base >= 2.0\r\nloadAfter = a\r\nloadafter = b; a\r\n"
                          b"setting = camera_left;key;A;Camera left\r\n"
                          b"setting = smooth;bool;yes;Smooth scrolling\r\n"
                          b"setting = speed;int;6;Speed;1..20\r\n"
                          b"setting = zoom;float;1.5;Zoom;0.5..3..0.25\r\n"
                          b"setting = mode;choice;fast;Mode;slow|fast|off\r\n"
                          b"setting = tag;text;qm;Tag;8;host\r\n"
                          b"setting = label;bool;1;Pr\xc4\x99dko\xc5\x9b\xc4\x87\r\n"),
    b"mods\\Bad": (b"type = overhaul\nexclusive = weather\nrequires = x>=one\nid = bad id\n"
                   b"colour = red\nversion = 1.x\njust a line\nname = a\nname = b\n"
                   b"loadBefore = ok; b@d\nincompatibleWith = qmtestwasd\n"),
    b"mods\\Settings": (b"setting = a;key\nsetting = b c;bool;1;B\nsetting = c;colour;1;C\n"
                        b"setting = d;int;5;D;9..1\nsetting = e;int;50;E;1..9\n"
                        b"setting = f;choice;x;F;\nsetting = g;choice;x;G;a|b\n"
                        b"setting = e;bool;1;E again\nsetting = h;int;1;H;1..2..3..4\n"
                        b"setting = i;text;toolong;I;3\nsetting = j;text;x;J;-2\n"
                        b"setting = k;float;-1.25;K;-5..5\nsetting = l;choice;b;L; a |b~|\n"),
    W + b"1325221799": b"id = svc\nversion = 2.5\nloadBefore = qmtestwasd\n",
    b"mods\\Addon": b"extends = svc\ntype=totalconversion\nloadAfter = quartermaster\n",
}

MODS = [(b"mods\\QMTestWASD", True, b""), (W + b"1325221799", True, b"1325221799"),
        (b"mods\\Bad", False, b""), (b"mods\\Settings", True, b""), (b"mods\\Addon", True, b""),
        (b"mods\\Plain", True, b""), (QM, True, b"")]


def engine(mods=MODS, files=FILES):
    fs = {QM + b"\\data\\quartermaster\\core.aix": b"x"}
    for d, data in files.items():
        fs[d + b"\\about.cfg"] = data
    eng = PAS5.Engine(fs, mods=mods)
    PAS5.load(eng, "qmAbout")
    PAS5.run(eng, "qmAbout")
    return eng


def pipe(items):
    return b"|" + b"|".join(items) + b"|" if items else b""


def expected(mods=MODS, files=FILES):
    self_row = max(i for i, (d, on, _t) in enumerate(mods) if on and d == QM)
    rows, abouts = [], []
    for i, (d, on, _t) in enumerate(mods):
        a = A.parse(files.get(d))
        abouts.append(a)
        rows.append(A.Row(d, d.rsplit(b"\\", 1)[-1], a, on, i == self_row))
    keys = {b"n": b"%d" % len(mods), b"self": b"%d" % self_row}
    pre = {i: set() for i in range(len(mods))}
    for b, a in A.edges(rows):
        pre[a].add(b)
    for i, (d, on, _t) in enumerate(mods):
        a, s = abouts[i], b"%d" % i
        keys[b"tit" + s] = rows[i].title
        keys[b"nm" + s] = pipe(rows[i].names) or b"|"
        keys[b"pre" + s] = pipe([b"%d" % j for j in sorted(pre[i])]) or b"|"
        keys[b"has" + s] = b"1" if a.present else b"0"
        keys[b"type" + s] = a.type
        keys[b"pn" + s] = b"%d" % len(a.problems)
        keys[b"sn" + s] = b"%d" % len(a.settings)
        if not a.present:
            continue
        keys[b"id" + s] = a.id
        keys[b"name" + s] = T.unescape(a.name)
        keys[b"ver" + s] = a.version
        keys[b"qmv" + s] = a.quartermaster
        keys[b"ext" + s] = a.extends
        keys[b"excl" + s] = pipe(a.exclusive)
        keys[b"aft" + s] = pipe(a.loadafter)
        keys[b"bef" + s] = pipe(a.loadbefore)
        keys[b"inc" + s] = pipe(a.incompatiblewith)
        keys[b"cmp" + s] = pipe(a.compatiblewith)
        keys[b"rqn" + s] = b"%d" % len(a.requires)
        for k, (rid, ver) in enumerate(a.requires):
            keys[b"rqi%s_%d" % (s, k)], keys[b"rqv%s_%d" % (s, k)] = rid, ver
        for k, p in enumerate(a.problems):
            keys[b"pt%s_%d" % (s, k)], keys[b"pc%s_%d" % (s, k)] = p.tag, p.code
            keys[b"px%s_%d" % (s, k)] = p.text
        for k, st in enumerate(a.settings):
            sk = b"%s_%d" % (s, k)
            keys[b"sid" + sk], keys[b"sty" + sk] = st.id, st.kind
            keys[b"sdf" + sk], keys[b"slb" + sk] = T.unescape(st.default), T.unescape(st.label)
            keys[b"ssc" + sk] = st.scope
            num = st.kind in (b"int", b"float")
            keys[b"slo" + sk] = b"%d" % (st.lo if num else 0)
            keys[b"shi" + sk] = b"%d" % (st.hi if num else 0)
            keys[b"sst" + sk] = b"%d" % (st.step if num else 0)
            keys[b"sdc" + sk] = b"%d" % st.decimals
            keys[b"sop" + sk] = b"|" + b"".join(T.unescape(o) + b"|" for o in st.options)
            keys[b"smx" + sk] = b"%d" % st.maxlen
            keys[b"sgr" + sk] = T.unescape(st.group)
    return keys


def test_qm_about_equals_the_twin_key_by_key():
    eng = engine()
    want = expected()
    got = {k: eng.key(b"qm_about", k) for k in want}
    diff = [(k, got[k], want[k]) for k in sorted(want) if got[k] != want[k]]
    assert diff == []


def test_quartermasters_list_stands_in_for_a_missing_about_cfg():
    """A Workshop mod without about.cfg reads Quartermaster's list entry
    (src/known/<number>.cfg) with the same grammar - kn = 1, has stays 0; a
    mod that ships its own about.cfg is read from it, the entry is ignored."""
    import os
    import hbuild as H
    ren, svc = W + b"3398700006", W + b"1325221799"
    mods = [(ren, True, b"3398700006"), (svc, True, b"1325221799"),
            (b"mods\\Plain", True, b""), (QM, True, b"")]
    listed = dict((rel.rsplit("/", 1)[1].encode(), data) for rel, data in H.load_known())
    assert A.known_name(ren) == b"3398700006.cfg" and A.known_name(b"mods\\Plain") is None
    own = {svc: b"id = svc\ntype = mod\n"}
    fs = {QM + b"\\data\\quartermaster\\core.aix": b"x"}
    for d, data in own.items():
        fs[d + b"\\about.cfg"] = data
    for name, data in listed.items():
        fs[QM + b"\\" + A.KNOWN_DIR + name] = data
    eng = PAS5.Engine(fs, mods=mods)
    PAS5.load(eng, "qmAbout")
    PAS5.run(eng, "qmAbout")
    key = lambda k: eng.key(b"qm_about", k)
    want_ren = A.parse(listed[b"3398700006.cfg"])
    assert (key(b"kn0"), key(b"has0"), key(b"type0")) == (b"1", b"0", want_ren.type)
    assert want_ren.type == b"totalconversion" and key(b"pn0") == b"0"
    assert (key(b"kn1"), key(b"has1"), key(b"id1"), key(b"type1")) == (b"", b"1", b"svc", b"mod")
    assert (key(b"kn2"), key(b"has2")) == (b"", b"0")
    # Every entry of the list parses without a problem and names a Workshop mod.
    assert listed and all(A.parse(d).problems == [] for d in listed.values())
    assert all(n[:-4].isdigit() for n in listed)


def test_the_fixtures_exercise_what_the_twin_checks():
    want = expected()
    # Every problem code of the grammar shows up at least once.
    codes = {v for k, v in want.items() if k.startswith(b"pc")}
    assert {b"line", b"repeated", b"unknown", b"version", b"type", b"exclusive", b"requires",
            b"id", b"list", b"setting-fields", b"setting-id", b"setting-type", b"setting-range",
            b"setting-default", b"setting-options", b"setting-twice"} <= codes
    # Non-ASCII survives as the bytes it stands for; a choice keeps its order.
    assert want[b"slb0_6"] == b"Pr\xc4\x99dko\xc5\x9b\xc4\x87"
    assert want[b"sop0_4"] == b"|slow|fast|off|"
    # SvC loads before WASD (loadBefore) and WASD's own loadAfter names are
    # not installed; the Addon's base is SvC; nothing comes after Quartermaster.
    assert want[b"pre0"] == b"|1|" and want[b"pre4"] == b"|1|" and want[b"pre6"] == b"|"


def test_a_mod_list_without_any_about_file():
    mods = [(b"mods\\A", True, b""), (W + b"12", False, b"12"), (QM, True, b"")]
    eng = engine(mods, {})
    want = expected(mods, {})
    assert {k: eng.key(b"qm_about", k) for k in want} == want
    assert eng.key(b"qm_about", b"files") == b"0"


def test_a_folder_without_mod_ini_is_named_by_its_dir():
    # The engine leaves the title of a folder without mod.ini untouched; read
    # into the same variables it named the row before's mod (run b4,
    # 2026-09-29: "QMTestConflict and QMTestConflict are both total
    # conversions" for QMTestTC1 and QMTestTC2).
    mods = [(b"mods\\Named", True, b""), (b"mods\\TC1", True, b""), (b"mods\\TC2", True, b""),
            (QM, True, b"")]
    fs = {QM + b"\\data\\quartermaster\\core.aix": b"x", b"mods\\Named\\mod.ini": b"x",
          b"mods\\TC1\\about.cfg": b"type = totalConversion\r\n",
          b"mods\\TC2\\about.cfg": b"type = totalConversion\r\n"}
    eng = PAS5.Engine(fs, mods=mods)
    eng.keep_without_ini = True
    eng.titles = {b"mods\\Named": b"Named title"}
    for state in ("qmAbout", "qmGlobals"):
        PAS5.load(eng, state)
        PAS5.run(eng, state)
    assert [eng.key(b"qm_about", b"tit%d" % i) for i in range(3)] == [
        b"Named title", b"mods\\TC1", b"mods\\TC2"]
    assert [eng.key(b"qm_glob", b"tit%d" % i) for i in range(3)] == [
        b"Named title", b"mods\\TC1", b"mods\\TC2"]


@pytest.mark.parametrize("n", [32, 33, 40, 128, 130, 999, 1000, 1001, 1023, 1024, 1030])
def test_setting_lines_past_the_cap(n):
    data = b"".join(b"setting = s%d;bool;1;S\r\n" % k for k in range(n))
    files = {b"mods\\Many": data}
    mods = [(b"mods\\Many", True, b""), (QM, True, b"")]
    eng = engine(mods, files)
    want = expected(mods, files)
    assert {k: eng.key(b"qm_about", k) for k in want} == want
    # A thousand settings a mod (32 until 0.1.5), the rest dropped one by
    # one; past 1024 setting lines a line is not even kept.
    kept, lines = min(n, A.MAX_SETTINGS), min(n, A.RAW_SETTINGS)
    assert A.MAX_SETTINGS == 1000 and eng.key(b"qm_about", b"sn0") == b"%d" % kept
    assert eng.key(b"qm_about", b"sid0_%d" % (kept - 1)) == b"s%d" % (kept - 1)
    assert eng.key(b"qm_about", b"sid0_%d" % kept) == b""
    codes = [eng.key(b"qm_about", b"pc0_%d" % k) for k in range(int(eng.key(b"qm_about", b"pn0")))]
    assert codes == [b"setting-lines"] * (n - lines) + [b"setting-many"] * (lines - kept)
    if n == 1001:
        assert eng.key(b"qm_about", b"px0_0") == b"more than 1000 settings; setting s1000 dropped"
    if n == 1030:
        assert eng.key(b"qm_about", b"px0_0") == b"line 1025: more than 1024 setting lines; ignored"


GROUPED = (b"setting = top;bool;1;Before any group\r\n"
           b"group = Match interface\r\n"
           b"setting = a;bool;1;A\r\n"
           b"setting = b;bool;1;B\r\n"
           b"group =\r\n"
           b"setting = c;bool;1;C\r\n"
           b"GROUP = \t Pr\xc4\x99dko\xc5\x9b\xc4\x87 | keys \r\n"
           b"setting = bad;colour;1;Bad\r\n"
           b"setting = d;key;F;D\r\n"
           b"group = Nothing under it\r\n"
           b"group = Last\r\n"
           b"setting = e;int;1;E;1..3\r\n")


def test_a_group_line_titles_the_settings_after_it():
    files = {b"mods\\Grouped": GROUPED, b"mods\\After": b"setting = x;bool;1;X\r\n"}
    mods = [(b"mods\\Grouped", True, b""), (b"mods\\After", True, b""), (QM, True, b"")]
    eng = engine(mods, files)
    want = expected(mods, files)
    assert {k: eng.key(b"qm_about", k) for k in want} == want
    # The title as the bytes it stands for; `|` in one is no separator.
    title = b"Pr\xc4\x99dko\xc5\x9b\xc4\x87 | keys"
    assert [want[b"sgr0_%d" % k] for k in range(6)] == [
        b"", b"Match interface", b"Match interface", b"Match interface", title, b"Last"]
    assert [want[b"pc0_%d" % k] for k in range(2)] == [b"group", b"setting-type"]
    assert want[b"px0_0"] == b"line 5: group needs a title; ignored"
    # A group ends with its file: the next mod's settings stand under none.
    assert want[b"sgr1_0"] == b"" and eng.key(b"qm_about", b"sgr1_0") == b""


# ------------------------------------------------------------------ rules
import random  # noqa: E402

import hbuild as H  # noqa: E402

RULE_FILES = {
    b"mods\\TC1": b"id = tc1\ntype = totalConversion\nversion = 1.0\n",
    b"mods\\TC2": b"type = totalconversion\n",
    b"mods\\AddOn": b"type = totalConversion\nextends = tc1\n",
    b"mods\\Cam1": b"exclusive = camera\n",
    b"mods\\Cam2": b"exclusive = camera; ui\nrequires = tc1>=1.5; cam1\n",
    b"mods\\Cam3": b"exclusive = ui; camera\ncompatibleWith = cam1; cam2\nquartermaster = 9.1\n",
    b"mods\\X": b"incompatibleWith = y; cam3\nloadAfter = y\nrequires = nothere; y>=1\n",
    b"mods\\Y": b"loadBefore = cam1\n",
}
RULE_DIRS = sorted(RULE_FILES) + [b"mods\\Plain"]


def rule_case(on, order):
    mods = [(d, True, b"") for d in RULE_DIRS] + [(QM, True, b"")]
    eng = engine(mods, RULE_FILES)
    n = len(mods)
    keys = {"n": n}
    for i in range(n):
        keys["on%d" % i] = on[i]
        keys["ord%d" % i] = order[i]
    eng.set("qm_abin", **keys)
    PAS5.load(eng, "qmAbRules")
    PAS5.run(eng, "qmAbRules")
    got = []
    for k in range(int(eng.key(b"qm_abr", b"n"))):
        g = lambda f: eng.key(b"qm_abr", b"%s%d" % (f, k))
        got.append((int(g(b"row")), g(b"tag"), g(b"code"), g(b"text"), int(g(b"oth"))))
    rows = [A.Row(d, d.rsplit(b"\\", 1)[-1], A.parse(RULE_FILES.get(d)), bool(on[i]), i == n - 1)
            for i, (d, _o, _t) in enumerate(mods)]
    want = [(p.row, p.tag, p.code, p.text, p.other)
            for p in A.rules(rows, order, H.QM_VERSION.encode())][:64]
    fail = b"1" if any(p[1] == b"FAIL" for p in want) else b"0"
    return got, want, eng.key(b"qm_abr", b"fail"), fail


def test_the_rules_equal_the_twin_all_on_in_mods_ini_order():
    n = len(RULE_DIRS) + 1
    got, want, f1, f2 = rule_case([1] * n, list(range(n)))
    assert got == want and f1 == f2 == b"1"
    codes = {p[2] for p in want}
    assert codes == {b"requires", b"version", b"quartermaster", b"incompatible", b"total",
                     b"exclusive", b"order"}


def test_the_rules_equal_the_twin_on_random_sets_and_orders():
    rnd = random.Random(8)
    n = len(RULE_DIRS) + 1
    for _ in range(60):
        on = [rnd.randint(0, 1) for _ in range(n - 1)] + [1]
        order = list(range(n - 1))
        rnd.shuffle(order)
        got, want, f1, f2 = rule_case(on, order + [n - 1])
        assert got == want and f1 == f2


# ------------------------------------------------------- canonical order v2
ORDER_FILES = {
    b"mods\\A": b"requires = b\n",
    b"mods\\B": b"loadAfter = zz9\n",
    b"mods\\C": b"loadBefore = a\nloadAfter = d\n",
    b"mods\\D": b"loadAfter = c\n",
    W + b"5": b"id = five\nloadAfter = quartermaster; mods\n",
}


def order_case(mods, files):
    eng = engine(mods, files)
    PAS5.load(eng, "qmModList")
    PAS5.run(eng, "qmModList")
    got = [int(eng.key(b"qm_mods", b"ord%d" % k)) for k in range(len(mods))]
    cyc = [int(eng.key(b"qm_mods", b"cyc%d" % k)) for k in range(int(eng.key(b"qm_mods", b"cycn")))]
    self_row = max(i for i, (d, on, _t) in enumerate(mods) if on and d == QM)
    plan = A.canonical_v2([d for d, _o, _t in mods], [A.parse(files.get(d)) for d, _o, _t in mods],
                          self_row)
    return got, cyc, plan


def test_canonical_order_v2_equals_the_twin():
    rnd = random.Random(80)
    dirs = sorted(ORDER_FILES) + [b"mods\\Z", W + b"77"]
    for _ in range(30):
        pick = [d for d in dirs if rnd.random() < 0.8]
        rnd.shuffle(pick)
        mods = [(d, rnd.random() < 0.7, b"") for d in pick]
        mods.insert(rnd.randint(0, len(mods)), (QM, True, b""))
        got, cyc, plan = order_case(mods, ORDER_FILES)
        assert got == plan.order and cyc == plan.cycle
    # C and D name each other: one of them is placed by canonical order.
    mods = [(d, True, b"") for d in dirs] + [(QM, True, b"")]
    got, cyc, plan = order_case(mods, ORDER_FILES)
    assert len(cyc) == 1 and got == plan.order
