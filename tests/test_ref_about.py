"""Gates for ref.about: the about.cfg grammar v1, the rules (M8 task 3) and
canonical order v2 (M8 task 2), on the fixtures the milestone names."""
from ref import about as A

WS = b"..\\..\\workshop\\content\\333420\\"
QMDIR = b"mods\\Quartermaster"


def about(text):
    return A.parse(text.replace(b"\n", b"\r\n"))


def row(d, text=None, on=True, title=None):
    return A.Row(d, title or d.split(b"\\")[-1], about(text) if text else None, on)


QM = A.Row(QMDIR, b"Quartermaster", None, True, True)


def test_the_grammar_keys_lists_comments_and_case():
    a = about(b"\xef\xbb\xbf# WASD camera\n"
              b"  ID = QMTestWASD\n"
              b"name = WASD camera\t\n"
              b"version=1.2\n"
              b"Type = Mod\n"
              b"exclusive = camera; hotkeys;\n"
              b"requires = 1325221799 ; base >= 2.0\n"
              b"loadAfter = a\n"
              b"loadafter = b; a\n"
              b"\n")
    assert a.present and a.problems == []
    assert (a.id, a.name, a.version, a.type) == (b"qmtestwasd", b"WASD camera", b"1.2", b"mod")
    assert a.exclusive == [b"camera", b"hotkeys"]
    assert a.requires == [(b"1325221799", b""), (b"base", b"2.0")]
    assert a.loadafter == [b"a", b"b"]


def test_values_quartermaster_must_trust_fail_and_the_rest_warn():
    a = about(b"type = overhaul\nexclusive = weather\nrequires = x>=one\nid = bad id\n"
              b"colour = red\nversion = 1.x\njust a line\nname = a\nname = b\n")
    fails = sorted(p.code for p in a.problems if p.tag == b"FAIL")
    warns = sorted(p.code for p in a.problems if p.tag == b"WARN")
    assert fails == [b"exclusive", b"id", b"requires", b"type"]
    assert warns == [b"line", b"repeated", b"unknown", b"version"]
    assert a.fail and a.name == b"b" and a.type == b"mod"


def test_no_file_is_an_empty_about():
    a = A.parse(None)
    assert not a.present and a.problems == [] and a.type == b"mod"


def test_settings_of_every_type():
    a = about(b"setting = camera_left;key;A;Camera left\n"
              b"setting = smooth;bool;yes;Smooth scrolling\n"
              b"setting = speed;int;6;Speed;1..20\n"
              b"setting = zoom;float;1.5;Zoom;0.5..3..0.25\n"
              b"setting = mode;choice;fast;Mode;slow|fast|off\n"
              b"setting = tag;text;qm;Tag;8;host\n")
    s = {x.id: x for x in a.settings}
    assert [x.id for x in a.settings] == [b"camera_left", b"smooth", b"speed", b"zoom", b"mode", b"tag"]
    assert s[b"camera_left"].default == b"A" and s[b"smooth"].default == b"1"
    assert (s[b"speed"].lo, s[b"speed"].hi, s[b"speed"].step, s[b"speed"].default) == (1, 20, 1, b"6")
    z = s[b"zoom"]
    assert (z.decimals, z.lo, z.hi, z.step, z.default) == (2, 50, 300, 25, b"1.50")
    assert s[b"mode"].options == [b"slow", b"fast", b"off"]
    assert s[b"tag"].maxlen == 8 and s[b"tag"].scope == b"host"
    assert a.problems == []


def test_bad_settings_are_dropped_with_a_warning():
    a = about(b"setting = a;key\n"
              b"setting = b c;bool;1;B\n"
              b"setting = c;colour;1;C\n"
              b"setting = d;int;5;D;9..1\n"
              b"setting = e;int;50;E;1..9\n"
              b"setting = f;choice;x;F;\n"
              b"setting = g;choice;x;G;a|b\n"
              b"setting = e;bool;1;E again\n")
    assert [x.id for x in a.settings] == [b"e", b"g"]
    assert a.settings[0].default == b"9" and a.settings[1].default == b"a"
    assert all(p.tag == b"WARN" for p in a.problems)
    assert [p.code for p in a.problems] == [
        b"setting-fields", b"setting-id", b"setting-type", b"setting-range",
        b"setting-default", b"setting-options", b"setting-default", b"setting-twice"]


def many(n):
    return about(b"".join(b"setting = s%d;bool;1;Setting %d\n" % (k, k) for k in range(n)))


def test_a_mod_may_declare_a_thousand_settings_and_the_next_one_is_dropped():
    # Until 0.1.5 the limit was 32, which Reinforced - Core reached.
    a = many(40)
    assert len(a.settings) == 40 and a.problems == []
    assert A.MAX_SETTINGS == 1000 and A.RAW_SETTINGS == 1024
    a = many(A.MAX_SETTINGS)
    assert len(a.settings) == A.MAX_SETTINGS and a.problems == []
    a = many(A.MAX_SETTINGS + 2)
    assert [s.id for s in a.settings] == [b"s%d" % k for k in range(A.MAX_SETTINGS)]
    assert a.problems == [
        A.Problem(b"WARN", b"setting-many", b"more than 1000 settings; setting s1000 dropped"),
        A.Problem(b"WARN", b"setting-many", b"more than 1000 settings; setting s1001 dropped")]


def test_a_group_line_titles_the_settings_after_it():
    a = about(b"setting = top;bool;1;Before any group\n"
              b"group = Match interface\n"
              b"setting = a;bool;1;A\n"
              b"setting = b;bool;1;B\n"
              b"group =\n"
              b"setting = c;bool;1;C\n"
              b"GROUP =  Camera | keys \n"
              b"setting = bad;colour;1;Bad\n"
              b"setting = d;key;F;D\n"
              b"group = Nothing under it\n"
              b"group = Last\n"
              b"setting = e;int;1;E;1..3\n")
    assert [(s.id, s.group) for s in a.settings] == [
        (b"top", b""), (b"a", b"Match interface"), (b"b", b"Match interface"),
        (b"c", b"Match interface"), (b"d", b"Camera ~124 keys"), (b"e", b"Last")]
    assert a.problems == [
        A.Problem(b"WARN", b"group", b"line 5: group needs a title; ignored"),
        A.Problem(b"WARN", b"setting-type",
                  b"setting bad: type 'colour' is not one of bool, int, float, choice, key, text")]


def grouped(*sizes):
    """Settings in groups: `(title, count)` each, in order."""
    out = []
    for title, count in sizes:
        for _ in range(count):
            s = A.Setting(b"s%d" % len(out), b"bool", b"1", b"Setting")
            s.group = title
            out.append(s)
    return out


def layout(*sizes):
    """option_rows as one letter a row: s a setting, H a title, M a title
    again, . an empty row; a space between pages."""
    letter = {b"set": "s", b"head": "H", b"more": "M", b"none": "."}
    rows = "".join(letter[kind] for kind, _k in A.option_rows(grouped(*sizes)))
    return " ".join(rows[i:i + 10] for i in range(0, len(rows), 10))


def test_without_groups_the_rows_are_the_settings():
    for n in (0, 1, 10, 11, 40):
        assert A.option_rows(grouped((b"", n))) == [(b"set", k) for k in range(n)]


def test_a_group_starts_with_its_title_and_stays_on_one_page_when_it_can():
    assert layout((b"", 3), (b"A", 5)) == "sssHsssss"
    # the title and the group fill the page exactly: nothing is moved
    assert layout((b"A", 4), (b"B", 4), (b"C", 4)) == "HssssHssss Hssss"
    # six rows do not fit the three left: the group starts the next page
    assert layout((b"A", 6), (b"B", 5)) == "Hssssss... Hsssss"
    # a title never stands at the foot of a page
    assert layout((b"", 9), (b"A", 1)) == "sssssssss. Hs"
    assert layout((b"A", 8), (b"B", 1)) == "Hssssssss. Hs"
    # the rows name their settings
    assert A.option_rows(grouped((b"", 1), (b"A", 2))) == [
        (b"set", 0), (b"head", 1), (b"set", 1), (b"set", 2)]


def test_a_group_longer_than_a_page_runs_on_under_its_title():
    assert layout((b"A", 12), (b"B", 2)) == "Hsssssssss MsssHss"
    assert layout((b"", 2), (b"A", 12)) == "ss........ Hsssssssss Msss"
    assert layout((b"A", 19)) == "Hsssssssss Msssssssss Ms"
    rows = A.option_rows(grouped((b"A", 12)))
    assert rows[10] == (b"more", 9) and rows[11] == (b"set", 9)


def test_the_same_title_twice_in_a_row_is_one_group():
    assert layout((b"A", 2), (b"A", 2), (b"B", 1), (b"A", 1)) == "HssssHsHs"


def test_the_rows_keep_every_setting_once_and_no_title_alone():
    import random
    rnd = random.Random(7)
    for _ in range(300):
        st = grouped(*[(rnd.choice([b"A", b"B", b"C", b"D"]), rnd.randint(1, 14))
                       for _ in range(rnd.randint(1, 9))])
        # only the first settings can stand under no group
        for s in st[:rnd.randint(0, 12)]:
            s.group = b""
        rows = A.option_rows(st)
        assert [k for kind, k in rows if kind == b"set"] == list(range(len(st)))
        for j, (kind, k) in enumerate(rows):
            if kind in (b"head", b"more"):
                assert rows[j + 1] == (b"set", k) and j % 10 != 9
                assert st[k].group != b""
            if kind == b"none":
                assert j % 10 != 0
            if kind == b"set" and j % 10 == 0:
                assert st[k].group == b""
        assert rows[-1][0] == b"set"


def test_a_mod_answers_to_its_id_and_its_folder():
    assert A.names(WS + b"1325221799", None) == [b"1325221799"]
    assert A.names(b"mods\\QMTestWASD", about(b"id = wasd\n")) == [b"wasd", b"qmtestwasd"]


def test_requires_missing_inactive_and_version():
    rows = [row(b"mods\\B", b"id = b\nversion = 1.5\n"),
            row(b"mods\\A", b"requires = b>=2.0\n"),
            row(b"mods\\C", b"requires = d\n"),
            row(b"mods\\D", on=False),
            row(b"mods\\E", b"requires = zz\n"), QM]
    got = [(p.row, p.tag, p.code) for p in A.rules(rows)]
    assert got == [(1, b"FAIL", b"version"), (2, b"FAIL", b"requires"), (4, b"FAIL", b"requires")]
    assert A.rules(rows)[1].other == 3 and b"not active" in A.rules(rows)[1].text
    assert b"not installed" in A.rules(rows)[2].text


def test_a_second_total_conversion_and_a_second_camera_mod_are_blocked():
    rows = [row(b"mods\\TC1", b"type = totalConversion\n"),
            row(b"mods\\TC2", b"type = totalconversion\n"),
            row(b"mods\\AddOn", b"type = totalConversion\nextends = tc1\n"),
            row(b"mods\\Cam1", b"exclusive = camera\n"),
            row(b"mods\\Cam2", b"exclusive = camera; ui\n"),
            row(b"mods\\Cam3", b"exclusive = camera\ncompatibleWith = cam1; cam2\n"), QM]
    got = [(p.row, p.code, p.other) for p in A.rules(rows)]
    # AddOn extends TC1, so only its clash with TC2 counts; Cam3 declares
    # itself compatible with both others.
    assert got == [(1, b"total", 0), (2, b"total", 1), (4, b"exclusive", 3)]


def test_incompatible_counts_from_the_side_that_declares_it():
    rows = [row(b"mods\\X", b"incompatibleWith = y\n"), row(b"mods\\Y"), QM]
    assert [(p.row, p.code, p.other) for p in A.rules(rows)] == [(0, b"incompatible", 1)]
    rows[1].on = False
    assert A.rules(rows) == []


def test_extends_implies_requires():
    rows = [row(b"mods\\AddOn", b"extends = base\n"), QM]
    assert [p.code for p in A.rules(rows)] == [b"requires"]


def test_order_a_requires_b_puts_b_first():
    dirs = [b"mods\\A", b"mods\\B", QMDIR]
    abouts = [about(b"requires = b\n"), A.About(), A.About()]
    plan = A.canonical_v2(dirs, abouts, 2)
    assert plan.order == [1, 0, 2] and plan.cycle == []


def test_order_without_about_files_is_phase_a_canonical():
    from ref import order as O
    dirs = [b"mods\\Zed", WS + b"99", b"mods\\alpha", QMDIR, WS + b"7"]
    plan = A.canonical_v2(dirs, [A.About()] * 5, 3)
    assert plan.order == O.canonical_indices(dirs, QMDIR)


def test_order_load_before_after_and_a_cycle():
    dirs = [b"mods\\A", b"mods\\B", b"mods\\C", QMDIR]
    abouts = [about(b"loadAfter = c\n"), about(b"loadBefore = a\n"), A.About(), A.About()]
    assert A.canonical_v2(dirs, abouts, 3).order == [1, 2, 0, 3]
    cyc = [about(b"loadAfter = b\n"), about(b"loadAfter = a\n"), A.About(), A.About()]
    plan = A.canonical_v2(dirs, cyc, 3)
    assert plan.order == [2, 0, 1, 3] and plan.cycle == [0]


def test_quartermaster_stays_last_whatever_a_mod_says():
    dirs = [b"mods\\A", QMDIR]
    abouts = [about(b"loadAfter = quartermaster\n"), A.About()]
    assert A.canonical_v2(dirs, abouts, 1).order == [0, 1]


def test_fixed_point_text():
    assert A.fixed_text(150, 2) == b"1.50" and A.fixed_text(-5, 1) == b"-0.5"
    assert A.fixed_text(7, 0) == b"7"


def test_draft():
    d = A.draft(b"qmtestwasd", b"QMTestWASD", camera=True)
    assert d.endswith(b"\r\n") and b"\nexclusive = camera\r\n" in d
    back = A.parse(d)
    assert (back.id, back.type, back.exclusive) == (b"qmtestwasd", b"mod", [b"camera"])
    assert back.problems == []
