"""Offline gates for tools/hbuild.py.

Tests that read the installed game (read-only) skip when it is absent. Deploy
and undeploy run only against a fake game folder under tmp_path.
"""
import hashlib
import os
import re
import shutil

import pytest

import hbuild
from hbuild import (BuildError, CRLF, DeployError, PREFIX, TemplateError,
                    assemble_aix, assemble_inc, parse_template, render_lines)

GAME = hbuild.GAME
HAVE_GAME = os.path.isfile(os.path.join(GAME, "cossacks.exe"))
needs_game = pytest.mark.skipif(not HAVE_GAME, reason="installed game not found")
REF_MOD_INI = os.path.join(GAME, "mods", "SW_Frontline_Protocol", "mod.ini")


def tpl(text, kind="state", path="src/states/t.pas"):
    return parse_template(path, text.encode("ascii") if isinstance(text, str) else text,
                          kind)


STATE_HEAD = "state: qmT\ninto: data/quartermaster/t.aix\nhelpers:\nrequires:\n---\n"


@pytest.fixture(scope="module")
def env():
    if not HAVE_GAME:
        pytest.skip("installed game not found")
    return hbuild.LintEnv.from_game(GAME)


# ------------------------------------------------------------- templates
@pytest.mark.parametrize("text, needle", [
    ("state: qmT\ninto: data/quartermaster/t.aix\nhelpers:\nrequires:\nx := 1;\n", "no front matter"),
    ("state: qmT\ninto: data/quartermaster/t.aix\nhelpers:\n---\nx;\n", "no 'requires'"),
    (STATE_HEAD.replace("---", "wrap: line\n---"), "unknown front-matter key"),
    ("state: qmT\nstate: qmU\ninto: data/quartermaster/t.aix\nhelpers:\nrequires:\n---\nx;\n",
     "duplicate front-matter key"),
    (STATE_HEAD + "qmX := 1; \n", "trailing whitespace"),
    (STATE_HEAD.replace("state: qmT", "state: Hello"), "starting with 'qm'"),
    (STATE_HEAD.replace("data/quartermaster/t.aix", "data/gui/menu.aix"), "data/quartermaster/"),
    (STATE_HEAD.replace("data/quartermaster/t.aix", "data/quartermaster/t.txt"), "data/quartermaster/"),
    (STATE_HEAD.replace("requires:", "requires: a, A"), "named twice"),
])
def test_template_front_matter_is_strict(text, needle):
    with pytest.raises(TemplateError, match=re.escape(needle)):
        tpl(text)


def test_template_refuses_non_ascii():
    with pytest.raises(TemplateError, match="not printable ASCII"):
        tpl(STATE_HEAD.encode() + "qmLog('\u00e9');\n".encode("latin-1"))


def test_helper_takes_no_state_keys():
    with pytest.raises(TemplateError, match="unknown front-matter key"):
        tpl(STATE_HEAD + "x;\n", kind="helper", path="src/lib/qmx.pas")


@pytest.mark.parametrize("body, variables, needle", [
    ("qmLog(${ v});\n", {}, "not a placeholder"),
    ("qmLog($(v));\n", {}, "not a placeholder"),
    ("qmLog(${v});\n", {"v": b"1"}, "without declaring"),
])
def test_placeholder_errors(body, variables, needle):
    t = tpl(STATE_HEAD + body)
    with pytest.raises(TemplateError, match=needle):
        render_lines(t, variables)


def test_declared_variables_must_be_used_supplied_and_nothing_else():
    t = tpl(STATE_HEAD.replace("requires:", "requires: v") + "qmX := ${v};\n")
    with pytest.raises(TemplateError, match="no value for v"):
        render_lines(t, {})
    with pytest.raises(TemplateError, match="was passed but"):
        render_lines(t, {"v": b"1", "w": b"2"})
    unused = tpl(STATE_HEAD.replace("requires:", "requires: v") + "qmX := 1;\n")
    with pytest.raises(TemplateError, match="does not use"):
        render_lines(unused, {"v": b"1"})


def test_render_drops_notes_keeps_comments_and_indents_blocks():
    t = tpl(STATE_HEAD.replace("requires:", "requires: block, one")
            + "//! a note\n// kept\nif (qmX=$FF) then\nbegin\n   ${block}\nend;\nqmY := ${one};\n\n")
    out = render_lines(t, {"block": [b"qmA := 1;", b"", b"qmB := 2;"], "one": 7})
    assert out == [b"// kept", b"if (qmX=$FF) then", b"begin", b"   qmA := 1;", b"",
                   b"   qmB := 2;", b"end;", b"qmY := 7;", b""]


def test_inline_placeholder_must_be_one_line():
    t = tpl(STATE_HEAD.replace("requires:", "requires: v") + "qmX := ${v};\n")
    with pytest.raises(TemplateError, match="inside a line"):
        render_lines(t, {"v": [b"1", b"2"]})


def test_crlf_template_renders_like_lf():
    text = STATE_HEAD + "qmX := 1;\n// c\n"
    lf = render_lines(tpl(text), {})
    crlf = render_lines(tpl(text.replace("\n", "\r\n")), {})
    assert lf == crlf == [b"qmX := 1;", b"// c"]


def test_qstr_doubles_quotes_and_refuses_what_a_literal_cannot_hold():
    assert hbuild.qstr("it's") == b"'it''s'"
    assert hbuild.qstr("") == b"''"
    for bad in ("a\nb", "\u00e9"):
        with pytest.raises((BuildError, UnicodeEncodeError)):
            hbuild.qstr(bad)


# --------------------------------------------------------------- helpers
def write_src(root, states=(), helpers=(), hooks=(), screens=(), guards=()):
    for sub, items in (("states", states), ("lib", helpers), ("hooks", hooks),
                       ("screens", screens), ("guard", guards)):
        os.makedirs(os.path.join(root, sub), exist_ok=True)
        for name, text in items:
            with open(os.path.join(root, sub, name), "wb") as fh:
                fh.write(text.encode("ascii"))
    return str(root)


def helper(needs=""):
    return "helpers: %s\nrequires:\n---\n" % needs


def test_helpers_are_inlined_dependencies_first_each_once(tmp_path):
    src = write_src(tmp_path / "src",
                    states=[("a.pas", STATE_HEAD.replace("helpers:", "helpers: qmb, qma")
                             + "qmB2;\n")],
                    helpers=[("qma.pas", helper() + "procedure qmA1;\nbegin\nend;\n"),
                             ("qmb.pas", helper("qma") + "procedure qmB2;\nbegin\n   qmA1;\nend;\n")])
    states, helpers = hbuild.load_sources(src)
    code = hbuild.state_code(states[0], helpers, {})
    assert code == [b"procedure qmA1;", b"begin", b"end;", b"",
                    b"procedure qmB2;", b"begin", b"   qmA1;", b"end;", b"", b"qmB2;"]


def test_helper_cycle_and_unknown_helper_are_errors(tmp_path):
    src = write_src(tmp_path / "src",
                    states=[("a.pas", STATE_HEAD.replace("helpers:", "helpers: qma") + "qmA1;\n")],
                    helpers=[("qma.pas", helper("qmb") + "procedure qmA1;\nbegin\nend;\n"),
                             ("qmb.pas", helper("qma") + "procedure qmB1;\nbegin\nend;\n")])
    states, helpers = hbuild.load_sources(src)
    with pytest.raises(BuildError, match="helper cycle"):
        hbuild.state_code(states[0], helpers, {})
    src2 = write_src(tmp_path / "src2",
                     states=[("a.pas", STATE_HEAD.replace("helpers:", "helpers: qmnope") + "x;\n")])
    states, helpers = hbuild.load_sources(src2)
    with pytest.raises(BuildError, match="not in src/lib"):
        hbuild.state_code(states[0], helpers, {})


HOOK_HEAD = "hook: data/gui/menu.inc/cameracontrol.inc\nrequires:\n---\n"
HOOK_BODY = "var qmH : Integer = GetTriggerManagerStateMachineHandle('qm_core');\n"


def test_hook_targets_come_from_the_planners_s5_list():
    assert hbuild.HOOK_FILES == tuple(
        "data/" + h.decode().replace("\\", "/") for h in hbuild._planner.HOOK_FILES)
    with pytest.raises(TemplateError, match="hook files of plan S5"):
        tpl(HOOK_HEAD.replace("cameracontrol", "oncamera") + HOOK_BODY, kind="hook",
            path="src/hooks/x.pas")
    with pytest.raises(TemplateError, match="unknown front-matter key"):
        tpl(HOOK_HEAD.replace("requires:", "helpers: qmlog\nrequires:") + HOOK_BODY,
            kind="hook", path="src/hooks/x.pas")


def test_one_hook_per_file(tmp_path):
    src = write_src(tmp_path / "src", hooks=[("a.pas", HOOK_HEAD + HOOK_BODY),
                                             ("b.pas", HOOK_HEAD + HOOK_BODY)])
    with pytest.raises(BuildError, match="already has a hook"):
        hbuild.load_hooks(src)


@needs_game
def test_hook_goes_in_front_of_its_anchor_and_leaves_every_vanilla_byte(tmp_path):
    src = write_src(tmp_path / "src", hooks=[("cc.pas", HOOK_HEAD + "//! note\n" + HOOK_BODY
                                              + "qmH := 0;\n")])
    result = hbuild.build(src, offline=True)
    data = result.outputs["data/gui/menu.inc/cameracontrol.inc"]
    with open(os.path.join(GAME, "data", "gui", "menu.inc", "cameracontrol.inc"), "rb") as fh:
        vanilla = fh.read()
    hook = (PREFIX + HOOK_BODY.strip().encode() + CRLF + PREFIX + b"qmH := 0;" + CRLF)
    anchor = PREFIX + b"const cTagLeft = 20;" + CRLF
    assert data == vanilla.replace(anchor, hook + anchor)
    assert data.replace(hook, b"", 1) == vanilla
    assert result.findings == []


@needs_game
def test_hook_place_is_the_rule_of_ref_inc(tmp_path):
    """The static copy uses ref.inc.hook_index, the rule merged output uses:
    no anchor text in the template can disagree with it."""
    from ref import inc as I
    with open(os.path.join(GAME, "data", "gui", "menu.inc", "cameracontrol.inc"), "rb") as fh:
        vanilla = fh.read()
    values = I.parse(vanilla).values
    assert I.hook_index(values) == 8 and values[8] == b";const cTagLeft = 20;"
    with pytest.raises(TemplateError, match="unknown front-matter key"):
        tpl(HOOK_HEAD.replace("requires:", "before: x\nrequires:") + HOOK_BODY, kind="hook",
            path="src/hooks/x.pas")
    # The built file is the vanilla values with the hook inserted by the rule.
    src = write_src(tmp_path / "src", hooks=[("cc.pas", HOOK_HEAD + HOOK_BODY)])
    data = hbuild.build(src, offline=True).outputs["data/gui/menu.inc/cameracontrol.inc"]
    assert I.parse(data).values == I.insert_at_hook(values, [b";" + HOOK_BODY.strip().encode()])


@needs_game
def test_hook_lints(tmp_path, env):
    def findings(body):
        src = write_src(tmp_path / ("s%d" % len(os.listdir(tmp_path))),
                        hooks=[("cc.pas", HOOK_HEAD + body)])
        return hbuild.build(src, GAME).findings

    assert findings(HOOK_BODY) == []
    # Eleven lines are one too many (plan S5).
    assert kinds(findings(HOOK_BODY + "qmH := 1;\n" * 10)) == ["hook-size"]
    # A library routine is not the engine's API, even though it resolves.
    f = findings("var qmT : Float = _misc_GetRealTime;\n")
    assert kinds(f) == ["hook-api"] and "_misc_GetRealTime" in f[0].message
    # Hook names carry the prefix; vanilla's own names are not the hook's business.
    assert kinds(findings("var hookVar : Integer = 0;\n")) == ["prefix"]
    # A hook name that collides with a vanilla one, case-insensitively.
    assert kinds(findings("var NAME : Integer = 0;\n")) == ["duplicate", "prefix"]
    assert kinds(findings("global qmG : Integer;\n")) == ["hook-global"]


@needs_game
def test_hook_offline_still_needs_the_vanilla_file(tmp_path):
    src = write_src(tmp_path / "src", hooks=[("cc.pas", HOOK_HEAD + HOOK_BODY)])
    with pytest.raises(BuildError, match="needs the installed game"):
        hbuild.build(src, str(tmp_path / "nogame"), offline=True)


def test_states_of_one_aix_are_sorted_and_an_inc_holds_one_state(tmp_path):
    src = write_src(tmp_path / "src", states=[
        ("z.pas", STATE_HEAD.replace("qmT", "qmZed") + "qmLog2;\n"),
        ("a.pas", STATE_HEAD.replace("qmT", "qmAlpha") + "qmLog1;\n")])
    result = hbuild.build(src, offline=True)
    data = result.outputs["data/quartermaster/t.aix"]
    assert data.index(b"Name = qmAlpha") < data.index(b"Name = qmZed")
    src2 = write_src(tmp_path / "src2", states=[
        ("a.pas", STATE_HEAD.replace("t.aix", "t.inc") + "qmX := 1;\n"),
        ("b.pas", STATE_HEAD.replace("qmT", "qmU").replace("t.aix", "t.inc") + "qmX := 1;\n")])
    with pytest.raises(BuildError, match="holds exactly one"):
        hbuild.build(src2, offline=True)


def test_state_names_are_unique_case_insensitively(tmp_path):
    src = write_src(tmp_path / "src", states=[
        ("a.pas", STATE_HEAD + "qmX := 1;\n"),
        ("b.pas", STATE_HEAD.replace("qmT", "QMT") + "qmX := 1;\n")])
    with pytest.raises(BuildError, match="unique case-insensitively"):
        hbuild.load_sources(src)


# ---------------------------------------------------------------- screens
SCREEN_HEAD = ("screen: ShowQmT\ninto: data/quartermaster/ui/showqmt.inc\nhelpers:\n"
               "requires:\n---\n")


@pytest.mark.parametrize("text, needle", [
    (SCREEN_HEAD.replace("ShowQmT", "ShowT"), "Show<Qm...> or Event<Qm...>"),
    (SCREEN_HEAD.replace("ShowQmT", "qmT"), "Show<Qm...> or Event<Qm...>"),
    (SCREEN_HEAD.replace("ShowQmT", "HideQmT"), "Show<Qm...> or Event<Qm...>"),
    (SCREEN_HEAD.replace("ui/showqmt.inc", "ui/other.inc"), "a screen is emitted into"),
    (SCREEN_HEAD.replace("ui/showqmt.inc", "showqmt.inc"), "a screen is emitted into"),
    (SCREEN_HEAD.replace("ui/showqmt.inc", "ui/showqmt.aix"), "a screen is emitted into"),
    (SCREEN_HEAD.replace("screen:", "state:"), "unknown front-matter key"),
    (SCREEN_HEAD.replace("helpers:\n", ""), "no 'helpers'"),
])
def test_screen_front_matter_is_strict(text, needle):
    with pytest.raises(TemplateError, match=re.escape(needle)):
        tpl(text + "qmX := 1;\n", kind="screen", path="src/screens/t.pas")


def test_screen_template_names_a_gui_state():
    t = tpl(SCREEN_HEAD.replace("ShowQmT", "EventQmT").replace("showqmt", "eventqmt")
            + "qmX := 1;\n", kind="screen", path="src/screens/t.pas")
    assert (t.kind, t.name, t.into) == ("screen", "EventQmT",
                                        "data/quartermaster/ui/eventqmt.inc")


def test_screens_are_emitted_as_one_state_inc_files(tmp_path):
    src = write_src(tmp_path / "src",
                    states=[("a.pas", STATE_HEAD + "qmX := 1;\n")],
                    screens=[("s.pas", SCREEN_HEAD.replace("helpers:", "helpers: qma")
                              + "//! a note\nqmA1;\n")],
                    helpers=[("qma.pas", helper() + "procedure qmA1;\nbegin\nend;\n")])
    result = hbuild.build(src, offline=True)
    assert result.findings == []
    assert ("ShowQmT", "data/quartermaster/ui/showqmt.inc", "src/screens/s.pas") in result.states
    data = result.outputs["data/quartermaster/ui/showqmt.inc"]
    assert data == assemble_inc(b"ShowQmT", [b"procedure qmA1;", b"begin", b"end;", b"",
                                             b"qmA1;"])
    # The state beside it is untouched by the screen.
    assert b"ShowQmT" not in result.outputs["data/quartermaster/t.aix"]


def test_screens_are_linted_like_states(tmp_path):
    src = write_src(tmp_path / "src", screens=[
        ("s.pas", SCREEN_HEAD + "var badName : Integer = Chr(65);\n")])
    assert kinds(hbuild.build(src, offline=True).findings) == ["chr", "prefix"]


def test_screen_names_join_the_uniqueness_check(tmp_path):
    src = write_src(tmp_path / "src", screens=[
        ("a.pas", SCREEN_HEAD + "qmX := 1;\n"),
        ("b.pas", SCREEN_HEAD.replace("screen: ShowQmT", "screen: ShowQmt") + "qmX := 1;\n")])
    with pytest.raises(BuildError, match="unique case-insensitively"):
        hbuild.load_sources(src)


def test_screens_are_read_from_their_folder_only(tmp_path):
    """Only `src/screens/*.pas`: a subfolder or another extension is not a screen."""
    src = write_src(tmp_path / "src", screens=[("s.pas", SCREEN_HEAD + "qmX := 1;\n"),
                                               ("notes.txt", "not a template\n")])
    os.makedirs(os.path.join(src, "screens", "old"))
    with open(os.path.join(src, "screens", "old", "x.pas"), "wb") as fh:
        fh.write(b"not a template\n")
    states, _helpers = hbuild.load_sources(src)
    assert [(t.kind, t.name) for t in states] == [("screen", "ShowQmT")]


# ------------------------------------------------------------ containers
def _split(data):
    lines = data.split(CRLF)
    assert lines[-1] == b""
    return lines[:-1]


@needs_game
def test_inc_container_rebuilds_vanilla_cameracontrol_byte_for_byte():
    with open(os.path.join(GAME, "data", "gui", "menu.inc", "cameracontrol.inc"), "rb") as fh:
        vanilla = fh.read()
    code = [line[len(PREFIX):] for line in _split(vanilla) if line.startswith(PREFIX)]
    assert len(code) == 32
    assert assemble_inc(b"CameraControl", code) == vanilla


@needs_game
def test_inc_container_rebuilds_every_vanilla_inc_of_the_standard_shape():
    rebuilt = 0
    for root, _dirs, files in os.walk(os.path.join(GAME, "data")):
        for fn in files:
            if not fn.lower().endswith(".inc"):
                continue
            with open(os.path.join(root, fn), "rb") as fh:
                data = fh.read()
            lines = data.split(CRLF)
            if (len(lines) < 6 or lines[0] != b"section.begin"
                    or not lines[1].startswith(b"   Name = ")
                    or lines[2] != b"   Code : struct.begin"
                    or lines[-4:] != [b"   struct.end", b"section.end", b"", b""]
                    or not all(x.startswith(PREFIX) for x in lines[3:-4])):
                continue
            code = [x[len(PREFIX):] for x in lines[3:-4]]
            assert assemble_inc(lines[1][len(b"   Name = "):], code) == data, fn
            rebuilt += 1
    # 272 open this way and 278 close this way; the files doing both, with every
    # code line spelled with the six-space prefix, are the ones rebuilt here.
    assert rebuilt >= 250, rebuilt


@needs_game
def test_aix_container_rebuilds_vanilla_rusmis1_byte_for_byte():
    with open(os.path.join(GAME, "data", "maps", "missions", "rusmis1.aix"), "rb") as fh:
        vanilla = fh.read()
    states, name, code = [], None, None
    for line in _split(vanilla):
        if line.startswith(b"   Name = "):
            name, code = line[len(b"   Name = "):], []
        elif line.startswith(PREFIX):
            code.append(line[len(PREFIX):])
        elif line == b"   struct.end":
            states.append((name, code))
    assert [s[0] for s in states] == [b"rusmis1", b"ach"]
    assert assemble_aix(states) == vanilla


def test_aix_container_shape():
    data = assemble_aix([(b"qmA", [b"qmX := 1;", b""])])
    assert data == (b"section.begin\r\n   Name = qmA\r\n   UsedFileName = \r\n"
                    b"   Code : struct.begin\r\n      [*] = ;qmX := 1;\r\n      [*] = ;\r\n"
                    b"   struct.end\r\nsection.end\r\n\r\n"
                    b"section.begin\r\n   CurrentState = \r\n   SaveVariables = False\r\n"
                    b"section.end\r\n\r\n")


# ------------------------------------------------------------------ lints
def lint(lines, env=None):
    code = [line.encode("ascii") for line in lines]
    return hbuild.lint_state("data/quartermaster/t.inc", "qmT",
                             assemble_inc(b"qmT", code), 0, env)


def kinds(findings):
    return sorted(set(f.lint for f in findings))


CLEAN = ["procedure qmLog(qmMsg : String);", "begin", "   Log('[qm] '+qmMsg);", "end;", "",
         "var qmN : Integer = 3;", "qmLog('n='+IntToStr(qmN));"]


def test_clean_state_has_no_findings_offline():
    assert lint(CLEAN) == []


def test_clean_state_has_no_findings_with_the_game(env):
    assert lint(CLEAN, env) == []


def test_chr_is_forbidden_in_any_spelling():
    for spelling in ("Chr(65)", "chr (65)", "CHR(65)"):
        f = lint(["var qmS : String = %s;" % spelling])
        assert kinds(f) == ["chr"], (spelling, f)
    # Inside a string literal or a comment it is text, not a call.
    assert lint(["var qmS : String = 'Chr(65)'; // Chr(66)"]) == []


def test_duplicate_identifiers_are_case_insensitive():
    f = lint(["var qmM : array [0..9] of Integer;", "var qmm : Integer;"])
    assert kinds(f) == ["duplicate"]
    assert "qmm" in f[0].message and "line 4" in f[0].message
    assert f[0].where == "data/quartermaster/t.inc:5"


def test_parameters_and_function_results_are_not_duplicates_of_themselves():
    f = lint(["function qmF(var qmA : Integer) : Integer;", "begin", "   Result := qmA;", "end;",
              "function qmG(qmB : Integer) : Integer;", "begin", "   Result := qmB;", "end;"])
    assert f == []


def test_prefix_is_required_for_every_declaration():
    f = lint(["var total : Integer = 1;"])
    assert kinds(f) == ["prefix"]


def test_var_array_parameters_allocate_nothing():
    # The caller's array, passed by reference (verified in-game): not counted.
    assert lint(["procedure qmP(var qmA : array [0..199999] of String; const qmN : Integer);",
                 "begin", "end;", "var qmB : array [0..199999] of String;", "qmP(qmB, 1);"]) == []
    # A value parameter would be a copy, so it still counts.
    f = lint(["procedure qmP(const qmA : array [0..199999] of String);", "begin", "end;",
              "var qmB : array [0..199999] of String;"])
    assert kinds(f) == ["array-budget"]


def test_string_function_does_not_compile_in_state_code():
    f = lint(["function qmF(const qmA : Integer) : String;", "begin", "   Result := '';", "end;"])
    assert kinds(f) == ["string-function"] and "qmF" in f[0].message
    assert kinds(lint(["function qmG : string;", "begin", "   Result := '';", "end;"])) == [
        "string-function"]
    # Returning through a var parameter, other result types, text in a comment: fine.
    assert lint(["procedure qmP(var qmOut : String);", "begin", "   qmOut := '';", "end;",
                 "function qmI(const qmA : String) : Integer;", "begin", "   Result := 1;", "end;",
                 "{ function qmX(a : String) : String; }"]) == []


def test_char_literals_are_joined_with_plus():
    for bad in ("var qmS : String = ';a'+#13#10+'b';", "var qmS : String = #13#10;",
                "var qmS : String = 'a'#9'b';", "var qmS : String = 'a'#9;"):
        f = lint([bad])
        assert kinds(f) == ["char-join"], (bad, f)
    # Vanilla's own spelling, and a # inside a string or a comment.
    assert lint(["var qmS : String = ';a'+#13+#10+'b';", "var qmT : String = #34+qmS+#34;",
                 "var qmU : String = 'x#13#10';  // #13#10"]) == []


def test_open_arrays_do_not_compile():
    f = lint(["procedure qmP(const qmA : array of Integer);", "begin", "end;"])
    assert kinds(f) == ["open-array"]
    assert kinds(lint(["var qmD : array of Integer;"])) == ["open-array"]


def test_high_length_setlength_do_not_compile():
    for call in ("High(qmA)", "Length(qmA)", "SetLength(qmA, 3)", "length (qmA)"):
        f = lint(["var qmA : array [0..3] of Integer;", "var qmN : Integer = 0;",
                  "qmN := %s;" % call if not call.startswith("SetLength") else call + ";"])
        assert kinds(f) == ["no-routine"], (call, f)
    f = lint(["var qmS : String = 'x';", "var qmN : Integer = Length(qmS);"])
    assert "StrLength" in f[0].message
    # The String length the engine has.
    assert lint(["var qmS : String = 'x';", "var qmN : Integer = StrLength(qmS);"]) == []


def test_integer_array_budget():
    assert lint(["var qmA : array [0..999999] of Integer;"]) == []
    f = lint(["var qmA : array [0..1000000] of Integer;"])
    assert kinds(f) == ["array-budget"] and "1000001" in f[0].message
    f = lint(["var qmA : array [0..599999] of Integer;", "var qmB : array [0..399999] of Float;",
              "var qmC : array [0..0] of Boolean;"])
    assert kinds(f) == ["array-budget"] and f[0].where.endswith(":6")


def test_string_array_budget():
    assert lint(["var qmS : array [0..199999] of String;"]) == []
    f = lint(["var qmS : array [0..200000] of String;"])
    assert kinds(f) == ["array-budget"] and "String" in f[0].message


def test_array_budget_follows_nesting_and_constants():
    f = lint(["var qmA : array [0..999] of array [0..1000] of Integer;"])
    assert kinds(f) == ["array-budget"] and "1001000" in f[0].message
    assert lint(["const qmN = 1000;", "var qmA : array [0..qmN*qmN-1] of Integer;"]) == []
    f = lint(["const qmN = 1000;", "var qmA : array [0..qmN*qmN] of Integer;"])
    assert kinds(f) == ["array-budget"]
    assert lint(["var qmA : array [1..10, 0..99999] of Integer;"]) == []    # exactly 1M
    f = lint(["var qmA : array [0..10, 0..99999] of Integer;"])
    assert kinds(f) == ["array-budget"]


def test_unevaluable_array_bound_is_a_finding():
    f = lint(["var qmA : array [0..qmUnknown] of Integer;"])
    assert kinds(f) == ["array-budget"] and "cannot be evaluated" in f[0].message


def test_array_bounds_may_use_game_constants(env):
    # gc_MaxPlayerCount = 12 (dmscript.global:97).
    assert lint(["var qmA : array [0..gc_MaxPlayerCount-1] of Integer;"], env) == []


def test_gscript_balance_and_const_order_fire():
    f = lint(["if (1=1) then", "begin", "   Log('x');"])
    assert "gscript-balance" in kinds(f)
    f = lint(["var qmX : Integer = qmK;", "const qmK = 5;"])
    assert "gscript-const-order" in kinds(f)


def test_unresolved_identifier_fires_with_the_game(env):
    f = lint(["qmNotDeclaredAnywhere(1);"], env)
    assert kinds(f) == ["gscript-unresolved"]


def test_findings_point_at_lines_of_the_emitted_aix(tmp_path):
    src = write_src(tmp_path / "src", states=[
        ("a.pas", STATE_HEAD.replace("qmT", "qmA") + "qmX := 1;\n"),
        ("b.pas", STATE_HEAD.replace("qmT", "qmB") + "var qmY : String = '';\nqmY := Chr(65);\n")])
    result = hbuild.build(src, offline=True)
    data = result.outputs["data/quartermaster/t.aix"]
    lines = data.split(CRLF)
    [f] = [f for f in result.findings if f.lint == "chr"]
    line = int(f.where.rsplit(":", 1)[1])
    assert b"Chr(65)" in lines[line - 1] and f.state == "qmB"


def test_emitted_files_are_crlf_ascii():
    assert hbuild.lint_file("a.inc", b"x\r\ny\r\n") == []
    assert [f.lint for f in hbuild.lint_file("a.inc", b"x\ny\r\n")] == ["container"]
    assert [f.lint for f in hbuild.lint_file("a.inc", b"x\r\n\xe9\r\n")] == ["container"]


# ------------------------------------------------------------- skeleton
@needs_game
def test_a_list_entry_with_a_problem_or_a_wrong_name_stops_the_build(tmp_path):
    (tmp_path / "known").mkdir()
    (tmp_path / "known" / "123.cfg").write_bytes(b"type = overhaul\r\n")
    with pytest.raises(hbuild.BuildError, match="123.cfg"):
        hbuild.load_known(str(tmp_path))
    (tmp_path / "known" / "123.cfg").write_bytes(b"type = totalConversion\r\n")
    assert hbuild.load_known(str(tmp_path)) == [(hbuild.KNOWN_DIR + "123.cfg",
                                                 b"type = totalConversion\r\n")]
    (tmp_path / "known" / "renaissance.cfg").write_bytes(b"type = mod\r\n")
    with pytest.raises(hbuild.BuildError, match="Workshop number"):
        hbuild.load_known(str(tmp_path))


def test_quartermaster_builds_with_zero_findings_offline():
    result = hbuild.build(offline=True)
    assert result.findings == []
    # Quartermaster's own list: one entry per src/known/<Workshop number>.cfg.
    known = sorted(hbuild.KNOWN_DIR + fn for fn in os.listdir(os.path.join(hbuild.SRC, "known")))
    assert known and all(r in result.outputs for r in known)
    assert sorted(r for r in result.outputs if r not in known) == ["data/gui/menu.inc/cameracontrol.inc",
                                      "data/gui/menu.inc/doprogress.inc",
                                      "data/gui/menu.inc/eventmainmenu.inc",
                                      "data/gui/menu.inc/initminimap.inc",
                                      "data/gui/menu.inc/onlanevent.inc",
                                      "data/quartermaster/core.aix",
                                      "data/quartermaster/hooks/cameracontrol.inc",
                                      "data/quartermaster/hooks/doprogress.inc",
                                      "data/quartermaster/hooks/eventmainmenu.inc",
                                      "data/quartermaster/hooks/initminimap.inc",
                                      "data/quartermaster/hooks/onlanevent.inc",
                                      "data/quartermaster/selftest.aix",
                                      "data/quartermaster/ui/eventqmmanager.inc",
                                      "data/quartermaster/ui/showqmmanager.inc",
                                      "data/scripts/resource.script", "mod.ini"]
    core = result.outputs["data/quartermaster/core.aix"]
    for state in (b"qmBoot", b"qmModList", b"qmIndexBegin", b"qmIndexStep", b"qmIndex",
                  b"qmPlan", b"qmFingerprint"):
        assert b"   Name = %s\r\n" % state in core
    assert PREFIX + b"   Log('[qm] '+qmMsg);\r\n" in core
    assert PREFIX + b"qmLog('boot version '+'0.1.2'+' hook='" in core
    # 0.1.0, the v0.1 beta (2026-09-30); 0.1.1 and 0.1.2, the first Workshop
    # updates, no change in behaviour (2026-10-02)
    assert hbuild.QM_VERSION == "0.1.2"
    # Build variables arrive as literals: the S5 list, the hash constants.
    assert (b"'|gui\\menu.inc\\cameracontrol.inc|gui\\menu.inc\\doprogress.inc|"
            b"gui\\menu.inc\\eventmainmenu.inc|gui\\menu.inc\\initminimap.inc|"
            b"gui\\menu.inc\\onlanevent.inc|'") in core
    assert b"mod 8355967" in core and b"*263+" in core
    hook = result.outputs["data/gui/menu.inc/cameracontrol.inc"]
    assert hook.count(b"qm_core") == 3 and b"'qmBoot'" in hook
    # The manager window's states are ensured on every DoCreate (docs/ui.md).
    assert hook.count(PREFIX + b"StateMachineExecuteState(qmHookSm, 'qmUiEnsure', 0);"
                      + CRLF) == 1
    menu = result.outputs["data/gui/menu.inc/eventmainmenu.inc"]
    assert menu.count(b"ExecuteState('ShowQmManager');") == 1


@needs_game
def test_skeleton_builds_with_zero_findings_against_the_game():
    assert hbuild.build(hbuild.SRC, GAME).findings == []


def test_dist_is_up_to_date_with_the_sources():
    assert hbuild.diff_dist(hbuild.build(offline=True).outputs) == []


# -------------------------------------------------------------- S2 / S4
S2_REFUSED = ["data/gui/menu.aix", "data/gui/menu.cfg", "data/gui/menu.inc/docreate.inc",
              "data/scripts/lib/init.script", "data/scripts/dmscript.source",
              "data/scripts/common.aix", "data/scripts/common.inc/initmap.inc",
              "data/scripts/units/unit.aix", "data/objects/objects.lib",
              "data/units/foo.prop", "data/hud/font1250.lib", "data/locale/en/table.lng",
              "data/projects/project.main.prj", "data/resources/resource.lib",
              "data/scripts/dmscript.global"]
# data/scripts/resource.script is the one exception: the guard of plan S17
# (test_the_guard_goes_into_resource_script_only).


@pytest.mark.parametrize("rel", S2_REFUSED)
def test_never_generate_paths_are_refused(rel, tmp_path):
    with pytest.raises(BuildError, match="plan S[24]"):
        hbuild.check_output_path(rel)
    with pytest.raises(BuildError):
        hbuild.write_dist({"mod.ini": b"x\r\n", rel: b"x\r\n"}, str(tmp_path / "dist"))
    assert not (tmp_path / "dist").exists()


@pytest.mark.parametrize("rel", ["../escape.inc", "data/../x", "Data/Quartermaster/a.aix",
                                 "C:/x.inc", "other/file.txt", "data//x.inc"])
def test_paths_outside_the_mod_or_not_normalised_are_refused(rel):
    with pytest.raises(BuildError):
        hbuild.check_output_path(rel)


def test_own_aix_and_merge_paths_are_allowed():
    for rel in ("mod.ini", "data/quartermaster/core.aix", "data/gui/menu.inc/cameracontrol.inc",
                "data/quartermaster/vanilla.idx"):
        hbuild.check_output_path(rel)


# ----------------------------------------------------------- vanilla.idx
def make_data_tree(root):
    files = {
        "gui/menu.inc/cameracontrol.inc": b"section.begin\r\n   Name = CameraControl\r\n",
        "gui/menu.inc/docreate.inc": b"a\r\n",
        "gui/menu.aix": b"a\r\n",
        "gui/common.inc/x.inc": b"a\r\n",
        "scripts/lib/init.script": b"a\r\n",
        "scripts/common.inc/initmap.inc": b"a\r\n",
        "scripts/units/unit.inc/position.inc": b"a\r\nb\r\n",
        "scripts/units/unit.aix": b"a\r\n",
        "scripts/dmscript.global": b"section.begin\r\n",
        "Game/Var/ObjCustom.cfg": b"x\r\ny",
        "textures/a.dds": b"DDS \x00\x01",
        "hud/font1250.lib": b"a\r\n",
        "hud/ref/1250/reffont.lib": b"a\r\n",
        "units/x.prop": b"a\r\n",
        "locale/en/table.lng": b"\x00\x00",
        "maps/m.inc": b"a\r\n",
        "empty.txt": b"",
    }
    for rel, data in files.items():
        path = os.path.join(root, "data", *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)
    return str(root)


def test_vanilla_idx_on_a_fake_tree_is_exact(tmp_path):
    game = make_data_tree(tmp_path / "game")
    data = hbuild.render_vanilla_idx(hbuild.vanilla_entries(game))
    body = [
        "empty.txt|0|0|wta",
        "game\\var\\objcustom.cfg|4|2|wta",
        "gui\\common.inc\\x.inc|3|1|merge",
        "gui\\menu.aix|3|1|never",
        "gui\\menu.inc\\cameracontrol.inc|40|2|merge",
        "gui\\menu.inc\\docreate.inc|3|1|never",
        "hud\\font1250.lib|3|1|never",
        "hud\\ref\\1250\\reffont.lib|3|1|wta",
        "locale\\en\\table.lng|2|-1|never",
        "maps\\m.inc|3|1|wta",
        "scripts\\common.inc\\initmap.inc|3|1|never",
        "scripts\\dmscript.global|15|1|wta",
        "scripts\\lib\\init.script|3|1|never",
        "scripts\\units\\unit.aix|3|1|never",
        "scripts\\units\\unit.inc\\position.inc|6|2|merge",
        "textures\\a.dds|6|-1|never",
        "units\\x.prop|3|1|never",
    ]
    expected = ("section.begin\r\n   Name = qmVanillaIndex\r\n   Format = 1\r\n"
                "   Count = %d\r\n   Code : struct.begin\r\n" % len(body)
                + "".join("      [*] = ;%s\r\n" % e for e in body)
                + "   struct.end\r\nsection.end\r\n\r\n").encode("ascii")
    assert data == expected
    assert hbuild.render_vanilla_idx(hbuild.vanilla_entries(game)) == data   # deterministic


def test_vanilla_idx_refuses_a_path_it_cannot_carry(tmp_path):
    root = tmp_path / "game" / "data"
    root.mkdir(parents=True)
    (root / "a b.txt").write_bytes(b"x")
    with pytest.raises(BuildError, match="cannot carry"):
        hbuild.vanilla_entries(str(tmp_path / "game"))


def _dist_idx():
    path = os.path.join(hbuild.DIST_MOD, *hbuild.IDX_REL.split("/"))
    if not os.path.isfile(path):
        pytest.skip("dist has no vanilla.idx yet")
    with open(path, "rb") as fh:
        return fh.read()


def test_shipped_vanilla_idx_is_well_formed_and_never_merges_an_s2_path():
    data = _dist_idx()
    assert hbuild.lint_file(hbuild.IDX_REL, data) == []
    header, entries = hbuild.parse_vanilla_idx(data)
    assert header["Name"] == "qmVanillaIndex" and header["Format"] == "1"
    assert int(header["Count"]) == len(entries) > 10000
    paths = [e[0] for e in entries]
    assert paths == sorted(paths, key=lambda p: p.encode("ascii")) and len(set(paths)) == len(paths)
    table = {e[0]: e for e in entries}
    assert table["gui\\menu.inc\\cameracontrol.inc"] == ("gui\\menu.inc\\cameracontrol.inc",
                                                        2291, 38, "merge")
    for path in ("gui\\menu.aix", "gui\\menu.cfg", "gui\\menu.inc\\docreate.inc",
                 "scripts\\common.inc\\initmap.inc", "scripts\\dmscript.source",
                 "scripts\\lib\\init.script", "scripts\\common.aix", "objects\\objects.lib"):
        assert table[path][3] == "never", path
    assert table["scripts\\dmscript.global"][3] == "wta"
    assert table["game\\var\\objcustom.cfg"][3] == "wta"
    for path, _size, lines, cls in entries:
        rel = path.replace("\\", "/")
        if hbuild.s2_reason(rel) or lines < 0:
            assert cls == "never", path
        if cls == "merge":
            assert rel.endswith(".inc") and not hbuild.s2_reason(rel), path
    # Every hook file of plan S5 is mergeable.
    for hook in ("cameracontrol", "initminimap", "doprogress", "eventmainmenu"):
        assert table["gui\\menu.inc\\%s.inc" % hook][3] == "merge"


@needs_game
def test_shipped_vanilla_idx_matches_the_installed_game():
    fresh = hbuild.render_vanilla_idx(hbuild.vanilla_entries(GAME))
    assert fresh == _dist_idx(), "the game changed: run tools/hbuild.py --vanilla-idx"


# ---------------------------------------------------------------- mod.ini
def test_mod_ini_bytes():
    data = hbuild.mod_ini()
    assert hbuild.lint_file("mod.ini", data) == []
    lines = _split(data)
    assert lines[0] == b"section.begin" and lines[-2:] == [b"section.end", b""]
    assert b"   title = Quartermaster" in lines
    assert (b"   description[*] = ;Makes your mods work together: merges the game files two mods "
            b"both change, keeps a new subscription from breaking your start, and gives mods their "
            b"own settings. In the game, under Mod Manager in the main menu.") in lines
    assert b"   changenote[*] = ;v0.1 beta: first public version." in lines
    assert b"   contentfolder = mods\\Quartermaster" in lines


@pytest.mark.skipif(not os.path.isfile(REF_MOD_INI), reason="reference mod.ini not found")
def test_mod_ini_has_the_keys_of_an_existing_mod_ini_in_order():
    def keys(data):
        return [line.split(b"=", 1)[0].strip() for line in data.split(CRLF)
                if b"=" in line]
    with open(REF_MOD_INI, "rb") as fh:
        ref = fh.read()
    assert keys(hbuild.mod_ini()) == keys(ref)
    assert ref.endswith(b"section.end\r\n\r\n") and hbuild.mod_ini().endswith(b"section.end\r\n\r\n")


# ------------------------------------------------------ deploy / undeploy
def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


@pytest.fixture
def fake(tmp_path, monkeypatch):
    game = tmp_path / "game"
    (game / "mods" / "SW_Frontline_Protocol" / "data").mkdir(parents=True)
    (game / "mods" / "SW_Frontline_Protocol" / "mod.ini").write_bytes(b"ref\r\n")
    (game / "mods" / "mods.ini").write_bytes(b"section.begin\r\n\tdis = True \r\nsection.end")
    dist = tmp_path / "dist" / "Quartermaster"
    (dist / "data" / "quartermaster").mkdir(parents=True)
    (dist / "mod.ini").write_bytes(hbuild.mod_ini())
    (dist / "data" / "quartermaster" / "core.aix").write_bytes(b"a\r\n")
    save = tmp_path / "save"
    save.mkdir()
    monkeypatch.setattr(hbuild, "running_images", lambda: set())
    return str(game), str(dist), str(save)


def listing(game):
    return sorted(os.listdir(os.path.join(game, "mods")))


def test_deploy_dry_run_touches_nothing(fake):
    game, dist, save = fake
    before = listing(game)
    files = hbuild.deploy(dist, game, save, dry_run=True, out=lambda *_: None)
    assert files == ["data/quartermaster/core.aix", "mod.ini"]
    assert listing(game) == before


def test_deploy_copies_byte_for_byte_and_refuses_twice(fake):
    game, dist, save = fake
    hbuild.deploy(dist, game, save, out=lambda *_: None)
    target = os.path.join(game, "mods", "Quartermaster")
    for rel in ("mod.ini", os.path.join("data", "quartermaster", "core.aix")):
        assert sha(os.path.join(target, rel)) == sha(os.path.join(dist, rel))
    with pytest.raises(DeployError, match="already exists"):
        hbuild.deploy(dist, game, save, out=lambda *_: None)


def test_deploy_refuses_while_the_game_runs_or_the_lock_exists(fake, monkeypatch):
    game, dist, save = fake
    monkeypatch.setattr(hbuild, "running_images", lambda: {"cossacks.exe", "explorer.exe"})
    with pytest.raises(DeployError, match="cossacks.exe"):
        hbuild.deploy(dist, game, save, out=lambda *_: None)
    monkeypatch.setattr(hbuild, "running_images", lambda: set())
    with open(os.path.join(save, hbuild.LOCK_NAME), "w") as fh:
        fh.write("someone else")
    with pytest.raises(DeployError, match="lock"):
        hbuild.deploy(dist, game, save, out=lambda *_: None)
    assert listing(game) == ["SW_Frontline_Protocol", "mods.ini"]


def test_undeploy_removes_only_quartermaster(fake):
    game, dist, save = fake
    ini = os.path.join(game, "mods", "mods.ini")
    ini_before = sha(ini)
    hbuild.deploy(dist, game, save, out=lambda *_: None)
    assert hbuild.undeploy(game, save, dry_run=True, out=lambda *_: None) is False
    assert "Quartermaster" in listing(game)
    assert hbuild.undeploy(game, save, out=lambda *_: None) is True
    assert listing(game) == ["SW_Frontline_Protocol", "mods.ini"]
    assert sha(ini) == ini_before
    assert hbuild.undeploy(game, save, out=lambda *_: None) is False     # nothing left


@pytest.mark.parametrize("folder", ["SW_Frontline_Protocol", "..", "..\\mods", "a/b", "",
                                    "quartermaster ", "Quartermaster\\data"])
def test_undeploy_refuses_any_other_folder(fake, folder):
    game, _dist, save = fake
    with pytest.raises(DeployError):
        hbuild.undeploy(game, save, out=lambda *_: None, folder=folder)
    assert listing(game) == ["SW_Frontline_Protocol", "mods.ini"]


@pytest.mark.parametrize("name", ["..", "a\\b", "a/b", "C:x", " x", ""])
def test_mod_folder_accepts_one_plain_name_only(fake, name):
    game, _dist, _save = fake
    with pytest.raises(DeployError):
        hbuild.mod_folder(game, name)


PUBLISHED_INI = hbuild.mod_ini().replace(b"publishedfileid = 0", b"publishedfileid = 3600000001")


def _published(game):
    """A deployed Quartermaster whose mod.ini names a Workshop item, with an
    output the game wrote into the folder since (a merged .inc)."""
    target = os.path.join(game, "mods", "Quartermaster")
    with open(os.path.join(target, "mod.ini"), "wb") as fh:
        fh.write(PUBLISHED_INI)
    os.makedirs(os.path.join(target, "data", "gui", "menu.inc"))
    with open(os.path.join(target, "data", "gui", "menu.inc", "showunitcontrol.inc"), "wb") as fh:
        fh.write(b"merged\r\n")
    return target


def test_update_keeps_the_published_mod_ini_and_nothing_the_game_wrote(fake):
    game, dist, save = fake
    hbuild.deploy(dist, game, save, out=lambda *_: None)
    target = _published(game)
    with open(os.path.join(dist, "data", "quartermaster", "core.aix"), "wb") as fh:
        fh.write(b"b\r\n")                                   # the new build
    lines = []
    assert hbuild.update(dist, game, save, out=lines.append) == [
        "data/quartermaster/core.aix", "mod.ini"]
    with open(os.path.join(target, "mod.ini"), "rb") as fh:
        assert fh.read() == PUBLISHED_INI
    assert sha(os.path.join(target, "data", "quartermaster", "core.aix")) == sha(
        os.path.join(dist, "data", "quartermaster", "core.aix"))
    assert not os.path.exists(os.path.join(target, "data", "gui"))
    assert any("publishedfileid 3600000001" in ln for ln in lines)
    # While the folder names the item the game never registers the subscribed
    # copy (runs wsclaim1/wsplain1): the author is told.
    assert any("Workshop item 3600000001, the game does not load the subscribed copy" in ln
               for ln in lines)
    assert not os.path.exists(os.path.join(os.path.dirname(dist), "Quartermaster.update"))
    assert listing(game) == ["Quartermaster", "SW_Frontline_Protocol", "mods.ini"]


def test_update_says_when_no_workshop_item_is_named_yet(fake):
    game, dist, save = fake
    hbuild.deploy(dist, game, save, out=lambda *_: None)
    lines = []
    hbuild.update(dist, game, save, out=lines.append)
    assert any("names no Workshop item yet" in ln for ln in lines)
    assert not any("subscribed copy" in ln for ln in lines)


def test_update_takes_dists_mod_ini_while_no_workshop_item_is_named(fake):
    """publishedfileid 0: nothing in the installed mod.ini to keep, and an old
    build's placeholders must not stay in it (the installed copy on
    2026-10-01); a mod.ini without the key is kept, as an unknown one."""
    game, dist, save = fake
    hbuild.deploy(dist, game, save, out=lambda *_: None)
    target = os.path.join(game, "mods", "Quartermaster")
    with open(os.path.join(target, "mod.ini"), "wb") as fh:
        fh.write(hbuild.mod_ini().replace(b"title = Quartermaster", b"title = an old build"))
    lines = []
    hbuild.update(dist, game, save, out=lines.append)
    with open(os.path.join(target, "mod.ini"), "rb") as fh:
        assert fh.read() == open(os.path.join(dist, "mod.ini"), "rb").read()
    assert any("mod.ini from dist (publishedfileid 0)" in ln for ln in lines)
    keyless = b"section.begin\r\n   title = mine\r\nsection.end\r\n"
    with open(os.path.join(target, "mod.ini"), "wb") as fh:
        fh.write(keyless)
    hbuild.update(dist, game, save, out=lambda *_: None)
    with open(os.path.join(target, "mod.ini"), "rb") as fh:
        assert fh.read() == keyless


def test_update_dry_run_touches_nothing(fake):
    game, dist, save = fake
    hbuild.deploy(dist, game, save, out=lambda *_: None)
    target = _published(game)
    before = sorted(hbuild._files_under(target))
    hbuild.update(dist, game, save, dry_run=True, out=lambda *_: None)
    assert sorted(hbuild._files_under(target)) == before


def test_update_refuses_what_it_must_not_touch(fake, monkeypatch):
    game, dist, save = fake
    with pytest.raises(DeployError, match="--deploy first"):
        hbuild.update(dist, game, save, out=lambda *_: None)
    other = os.path.join(game, "mods", "Quartermaster")
    os.makedirs(os.path.join(other, "data"))
    with open(os.path.join(other, "mod.ini"), "wb") as fh:
        fh.write(b"someone's own mod\r\n")
    with pytest.raises(DeployError, match="not Quartermaster"):
        hbuild.update(dist, game, save, out=lambda *_: None)
    shutil.rmtree(other)
    hbuild.deploy(dist, game, save, out=lambda *_: None)
    monkeypatch.setattr(hbuild, "running_images", lambda: {"cossacks.exe"})
    with pytest.raises(DeployError, match="cossacks.exe"):
        hbuild.update(dist, game, save, out=lambda *_: None)
    monkeypatch.setattr(hbuild, "running_images", lambda: set())
    os.makedirs(os.path.join(os.path.dirname(dist), "Quartermaster.update"))
    with pytest.raises(DeployError, match="left from an earlier update"):
        hbuild.update(dist, game, save, out=lambda *_: None)


def test_cli_deploy_and_undeploy_on_a_fake_game(fake):
    game, dist, save = fake
    lines = []
    args = ["--game-dir", game, "--save-dir", save, "--dist", dist]
    assert hbuild.main(["--deploy", "--dry-run"] + args, out=lines.append) == 0
    assert "Quartermaster" not in listing(game)
    assert hbuild.main(["--deploy"] + args, out=lines.append) == 0
    assert hbuild.main(["--deploy"] + args, out=lines.append) == 2
    assert hbuild.main(["--update"] + args, out=lines.append) == 0
    assert hbuild.main(["--update", "--deploy"] + args, out=lines.append) == 2
    assert hbuild.main(["--undeploy"] + args, out=lines.append) == 0
    assert listing(game) == ["SW_Frontline_Protocol", "mods.ini"]


# ------------------------------------------------------------ the guard
GUARD_HEAD = ("guard: QmGuard\ninto: data/scripts/resource.script\n"
              "requires: guardstamp, h1mul, h1mod, h2mul, h2mod\n---\n")
GUARD_BODY = ("var qmGdAge : Integer = FileAge('.\\data\\scripts\\resource.script');\n"
              "var qmGdR1 : Integer = (${h1mul}+${h2mul}) mod ${h1mod} mod ${h2mod};\n"
              "if (IntToStr(qmGdAge)<>${guardstamp}) then\n"
              "log('[qm-guard] game-version');\n")


@needs_game
def test_the_guard_is_the_vanilla_on_load_script_with_its_lines_after_it(tmp_path):
    src = write_src(tmp_path / "src", guards=[("resource.pas", GUARD_HEAD + GUARD_BODY)])
    r = hbuild.build(src, GAME)
    with open(os.path.join(GAME, "data", "scripts", "resource.script"), "rb") as fh:
        vanilla = fh.read()
    data = r.outputs[hbuild.GUARD_FILE]
    assert data.startswith(vanilla) and data.endswith(CRLF)
    tail = data[len(vanilla):]
    assert tail.startswith(CRLF + b"var qmGdAge : Integer = FileAge(")
    # The game it was built against, by content (ref/guard.py game_stamp), not
    # by the file's date: that is the day Steam wrote it on this machine.
    from ref.guard import game_stamp
    assert b"<>'" + game_stamp(vanilla) + b"') then" in tail
    assert r.findings == []


@needs_game
def test_guard_lints_allow_engine_natives_only(tmp_path, env):
    def findings(body):
        src = write_src(tmp_path / ("g%d" % len(os.listdir(tmp_path))),
                        guards=[("resource.pas", GUARD_HEAD + GUARD_BODY + body)])
        return hbuild.build(src, GAME).findings

    assert findings("") == []
    # A library routine resolves in a state, but not before the libraries compile.
    f = findings("var qmGdP : Integer = _parser_ParserTemporary(True);\n")
    assert kinds(f) == ["guard-api"] and "_parser_ParserTemporary" in f[0].message
    # Nor does a dmscript.global name.
    assert kinds(findings("var qmGdM : Integer = gc_MaxPlayerCount;\n")) == ["guard-api"]
    # Names are unique case-insensitively (a second qmGdAge) and carry the prefix.
    assert kinds(findings("var QMGDAGE : Integer = 0;\n")) == ["duplicate"]
    assert kinds(findings("var gdX : Integer = 0;\n")) == ["prefix"]


def test_the_guard_goes_into_resource_script_only():
    with pytest.raises(TemplateError, match="the guard goes into"):
        tpl(GUARD_HEAD.replace("data/scripts/resource.script", "data/scripts/other.script")
            + GUARD_BODY, kind="guard", path="src/guard/x.pas")
    # The one never-generate file that may be emitted, and only by that name.
    hbuild.check_output_path("data/scripts/resource.script")
    with pytest.raises(BuildError, match="never-generate"):
        hbuild.check_output_path("data/scripts/lib/unit.script")


def test_a_string_passed_by_value_and_as_var_is_a_finding():
    # The game gives such a variable back damaged (probe runs of 2026-09-29):
    # qmLowerAscii(qmAbRid, qmAbRid) turned `qmtestverbase` into `qmtestverbas`.
    code = (b"procedure qmL(const qmA : String; var qmB : String);\r\nbegin\r\nqmB := qmA;\r\n"
            b"end;\r\nprocedure qmI(const qmX : Boolean; var qmY : Boolean);\r\nbegin\r\nend;\r\n"
            b"qmL(qmZ, qmZ);\r\nqmL(qmZ, qmW);\r\nqmI(qmQ, qmQ);\r\nqmL(qmArr[2], qmArr[2]);\r\n")
    got = hbuild.alias_misuse(hbuild.gscript.parse("t", code))
    assert [(r, a) for _o, r, a in got] == [(b"qmL", b"qmz"), (b"qmL", b"qmarr[2]")]


def test_no_module_level_name_of_the_build_is_bound_twice():
    # A second `_ROUTINE_HEAD = ...` once rebound the pattern parameter_groups
    # (the array budget) reads, so the alias lint changed another lint.
    with open(hbuild.__file__, "rb") as f:
        names = re.findall(rb"(?m)^([A-Za-z_]\w*)\s*=[^=]", f.read())
    twice = sorted(set(n for n in names if names.count(n) > 1))
    assert twice == []
    assert not hbuild._ROUTINE_HEAD.flags & re.I
