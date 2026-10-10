"""Offline gates for the manager window (docs/plan.md G15, docs/ui.md).

The window is two GUI states added to the GUI machine at run time
(`src/screens/*.pas`, the `screen` template kind of tools/hbuild.py, emitted
into data/quartermaster/ui/) and the controller states that run in
Quartermaster's trigger manager (`src/states/qmui*.pas`, in core.aix). The
EventMainMenu hook (`src/hooks/eventmainmenu.pas`) opens the window, and the
CameraControl hook ensures its states on every DoCreate. Everything here is
built through hbuild itself; nothing is written.

Tests that need the installed game (read-only) skip when it is absent.
"""
import os
import re

import pytest

import hbuild
from hbuild import gscript
from ref import inc

REPO = hbuild.REPO
SCREENS = os.path.join(REPO, "src", "screens")
STATES = os.path.join(REPO, "src", "states")
HOOK = os.path.join(REPO, "src", "hooks", "eventmainmenu.pas")
CC_HOOK = os.path.join(REPO, "src", "hooks", "cameracontrol.pas")
MENU_REL = "data/gui/menu.inc/eventmainmenu.inc"
UI_DOC = os.path.join(REPO, "docs", "ui.md")
GAME = hbuild.GAME
HAVE_GAME = os.path.isfile(os.path.join(GAME, "cossacks.exe"))
needs_game = pytest.mark.skipif(not HAVE_GAME, reason="installed game not found")

_SCREEN_NAME = re.compile(r"^(Show|Event)(Qm[A-Za-z0-9]+)$")


def screen_templates():
    states, _helpers = hbuild.load_sources()
    return [t for t in states if t.kind == "screen"]


def ui_state_templates():
    states, helpers = hbuild.load_sources()
    return [s for s in states if s.kind == "state" and s.name.lower().startswith("qmui")], helpers


def build_screen(t, helpers, env=None):
    """`(bytes, findings)` of one screen, the way hbuild.build emits it."""
    code = hbuild.state_code(t, helpers)
    data = hbuild.assemble_inc(t.name.encode("ascii"), code)
    findings = hbuild.lint_state(t.into, t.name, data, 0, env)
    findings += hbuild.lint_file(t.into, data)
    return data, findings


def build_ui_state(t, helpers, env=None):
    """`(bytes, findings)` of one controller state, as a section of core.aix."""
    section = hbuild.aix_section(t.name.encode("ascii"), hbuild.state_code(t, helpers))
    return section, hbuild.lint_state(t.into, t.name, section, 0, env)


def unit_of(data, where="x"):
    return gscript.parse(where, data)


def code_text(data):
    """The code of an emitted file: string bodies and comments blanked."""
    return unit_of(data).code.decode("ascii")


def literal_code(data):
    """The code half of every `[*] = ;` line, literals intact, comments kept."""
    out = []
    for line in data.split(hbuild.CRLF):
        if line.startswith(hbuild.PREFIX):
            out.append(line[len(hbuild.PREFIX):].decode("ascii"))
    return out


@pytest.fixture(scope="module")
def env():
    if not HAVE_GAME:
        pytest.skip("installed game not found")
    return hbuild.LintEnv.from_game(GAME)


@pytest.fixture(scope="module")
def screens():
    return screen_templates()


@pytest.fixture(scope="module")
def built(screens):
    """`{name: emitted bytes}` for both screens and every qmUi state."""
    ui, helpers = ui_state_templates()
    out = {}
    for t in screens:
        out[t.name] = build_screen(t, helpers)[0]
    for t in ui:
        out[t.name] = build_ui_state(t, helpers)[0]
    return out


# --------------------------------------------------------------- the files
def test_the_window_is_one_show_event_pair(screens):
    names = sorted(t.name for t in screens)
    assert names == ["EventQmManager", "ShowQmManager"]
    roots = set(_SCREEN_NAME.match(n).group(2) for n in names)
    assert roots == {"QmManager"}


def test_controller_states_go_into_core_aix():
    ui, _helpers = ui_state_templates()
    assert sorted(t.name for t in ui) == ["qmUiAct", "qmUiApply", "qmUiDetails",
                                          "qmUiEnsure", "qmUiModel", "qmUiOrder"]
    assert set(t.into for t in ui) == {"data/quartermaster/core.aix"}


def test_screen_names_collide_with_no_vanilla_or_own_state(screens, game_dir):
    with open(os.path.join(game_dir, "data", "gui", "menu.aix"), "rb") as fh:
        vanilla = set(n.lower() for n in re.findall(rb"^\s*Name = (\w+)\s*$",
                                                   fh.read(), re.M))
    states, _helpers = hbuild.load_sources()
    # Only trigger-manager states: once hbuild reads src/screens itself, its
    # list holds the screens too.
    own = set(s.name.lower().encode() for s in states if s.path.startswith("src/states/"))
    for t in screens:
        low = t.name.lower().encode()
        assert low not in vanilla, "%s is a vanilla GUI state" % t.name
        assert low not in own, "%s is also a trigger-manager state" % t.name
    assert b"showmainmenu" in vanilla          # the parse found the GUI states


# --------------------------------------------------------------- the lints
def test_screens_pass_the_structural_lints(screens):
    _ui, helpers = ui_state_templates()
    for t in screens:
        _data, findings = build_screen(t, helpers)
        assert findings == [], "\n".join(str(f) for f in findings)


@needs_game
def test_screens_pass_every_lint_against_the_installed_game(screens, env):
    _ui, helpers = ui_state_templates()
    for t in screens:
        _data, findings = build_screen(t, helpers, env)
        assert findings == [], "\n".join(str(f) for f in findings)


@needs_game
def test_controller_states_pass_every_lint(env):
    ui, helpers = ui_state_templates()
    for t in ui:
        _data, findings = build_ui_state(t, helpers, env)
        assert findings == [], "\n".join(str(f) for f in findings)


def test_the_build_emits_the_screens_as_tested_here(built, screens):
    outputs = hbuild.build(offline=True).outputs
    for t in screens:
        assert outputs[t.into] == built[t.name], t.into
    assert sorted(k for k in outputs if k.startswith("data/quartermaster/ui/")) == [
        "data/quartermaster/ui/eventqmmanager.inc", "data/quartermaster/ui/showqmmanager.inc"]


def test_emitted_screens_have_the_vanilla_one_state_shape(built):
    for name in ("ShowQmManager", "EventQmManager"):
        data = built[name]
        assert data.startswith(b"section.begin\r\n   Name = " + name.encode()
                               + b"\r\n   Code : struct.begin\r\n")
        assert data.endswith(b"   struct.end\r\nsection.end\r\n\r\n")
        body = data.split(b"\r\n")[3:-4]
        assert body and all(line.startswith(hbuild.PREFIX) for line in body)


_FORBIDDEN = [
    (re.compile(r"\bfunction\s+\w+\s*\([^)]*\)\s*:\s*String\b", re.I),
     "a nested function returning String does not compile (capability probes)"),
    (re.compile(r"\barray\s+of\b", re.I), "open arrays do not compile"),
    (re.compile(r"\b(SetLength|High|Length)\s*\(", re.I), "not in the dialect"),
    (re.compile(r"\bChr\s*\(", re.I), "Chr does not compile"),
    (re.compile(r"\bIsFileExists\s*\(", re.I), "logs an ERROR for a missing file; use FileAge"),
    (re.compile(r"\b_gui_ShowModalMessage\s*\(", re.I),
     "its buttons go to EventModalMessage, not to Quartermaster"),
    (re.compile(r"\bParserCreate\s*\(\s*'qm_rt'", re.I),
     "qm_rt is the boot's once-per-process flag; only the hook creates it"),
    (re.compile(r"\bTriggerManagerAdd\s*\(", re.I),
     "a live name makes a second, empty manager; the hook owns qm_core"),
]


def test_no_forbidden_construct(built):
    for name, data in built.items():
        code = code_text(data)
        # The masked code keeps the quotes; put the literals back for the
        # checks that are about a literal argument.
        text = "\n".join(literal_code(data))
        for rx, why in _FORBIDDEN:
            hay = text if "'" in rx.pattern else code
            m = rx.search(hay)
            assert not m, "%s: %r - %s" % (name, m.group(0), why)


def test_nothing_writes_a_file(built):
    """This pass writes no file at all: mods.ini is the boot milestone's."""
    writers = re.compile(r"\b(ParserSaveToFileByHandle|FileStreamWrite\w*|OpenFileWrite|"
                         r"CopyFileStream|MoveFileStream|RenameFileStream|DeleteFileStream|"
                         r"ModLibrarySetData|RestartApplicationParam)\b")
    for name, data in built.items():
        m = writers.search(code_text(data))
        assert not m, "%s calls %s" % (name, m.group(0))


# ------------------------------------------------------ names that must agree
_TAG_CONST = re.compile(r"^const (qmTag\w+) = (\d+);$")


def _tags(data):
    return dict((m.group(1), int(m.group(2))) for m in
                (_TAG_CONST.match(line) for line in literal_code(data)) if m)


def test_show_and_event_agree_on_every_tag(built):
    show, event = _tags(built["ShowQmManager"]), _tags(built["EventQmManager"])
    assert show and show == event
    values = sorted(show.values())
    assert len(values) == len(set(values)), "two tags share a value"
    # Vanilla's own event tags live at 8001-8003 and 9001-9011
    # (dmscript.global:1178-1186); ours stay clear of them.
    assert all(v < 8000 for v in values)


def test_every_tag_the_event_state_handles_is_on_a_button(built):
    show = "\n".join(literal_code(built["ShowQmManager"]))
    event = "\n".join(literal_code(built["EventQmManager"]))
    for tag in _tags(built["EventQmManager"]):
        if tag == "qmTagMask":
            assert re.search(r"_gui_CreateImageActive\([^;]*qmTagMask", show)
            continue
        assert re.search(r"qmSmButton\([^;]*\b%s\b" % tag, show), \
            "%s has no button in ShowQmManager" % tag
        assert re.search(r"\(qmEmTag=%s\)" % tag, event), \
            "%s is not handled in EventQmManager" % tag


_CREATE = re.compile(r"(?:var (\w+) : \w+ = |(\w+) := |^)"
                     r"(?:_gui_Create(\w+)|qmSmButton)\('([^']*)', (\w+)")


def _element_tree(show_lines):
    """`({handle variable: (element name, parent variable)}, input boxes, names)`."""
    handles, inputs, names = {}, set(), []
    for line in show_lines:
        for m in _CREATE.finditer(line.strip()):
            var = m.group(1) or m.group(2)
            names.append(m.group(4))
            if var:
                handles[var] = (m.group(4), m.group(5))
                if m.group(3) == "InputBox":
                    inputs.add(var)
    return handles, inputs, names


def _resolve(handles, inputs, path, root_var):
    """True when the dotted `path` walks down created elements from `root_var`."""
    parts = path.split(".")
    current = root_var
    for i, part in enumerate(parts):
        children = [v for v, (n, p) in handles.items() if p == current and n == part]
        if children:
            current = children[0]
            continue
        # _gui_CreateInputBox makes its edit control as the child `text`
        # (data/scripts/lib/gui.script:1621).
        return part == "text" and i == len(parts) - 1 and current in inputs
    return True


def test_every_element_the_event_state_looks_up_is_created(built):
    handles, inputs, names = _element_tree(literal_code(built["ShowQmManager"]))
    assert handles["qmSmMain"] == ("main", "qmSmParent")
    event = "\n".join(literal_code(built["EventQmManager"]))
    paths = re.findall(r"qmEmElmname\+'\.([\w.]+)'", event)
    # The filter box lives in its own layer, updated in place (not rebuilt),
    # so its edit control keeps the caret through a keystroke's redraw.
    assert sorted(set(paths)) == ["fbox.filter.text", "main.wnd.act.active",
                                  "main.wnd.inst.installed", "nbox.nname.text", "obox.otext.text"]
    for p in paths:
        assert _resolve(handles, inputs, p, "qmSmParent"), \
            "%s is not created by ShowQmManager" % p
    for list_name in re.findall(r"qmEmList='(\w+)'", event):
        assert list_name in names, "list %s is not created" % list_name
    # Element names with a dot cannot be found by name again
    # (gui.script:213 logs an ERROR for them).
    assert all("." not in n for n in names), names


_WND_CHILD = re.compile(r"(?:_gui_Create\w+|qmSmButton)\('(\w+)', qmSmWnd\b")


def test_the_main_window_s_elements_have_unique_names(built):
    """A second element of the same name under one parent would be found
    instead of the first by every name lookup. The one name made twice is
    `breport`, in the two arms of one if (Report / Back)."""
    lines = [ln.strip() for ln in literal_code(built["ShowQmManager"])]
    names = [m.group(1) for ln in lines for m in _WND_CHILD.finditer(ln)]
    assert "tmsg" in names
    twice = sorted(set(n for n in names if names.count(n) > 1))
    assert twice == ["breport"], twice
    at = [i for i, ln in enumerate(lines) if "qmSmButton('breport', qmSmWnd" in ln]
    assert len(at) == 2 and lines[at[0] - 1] == "if (qmSmPanel=1) then" \
        and lines[at[0] + 1] == "else" and at[1] == at[0] + 2


def test_the_window_draws_no_custom_order_footer(built):
    """The multiplayer footer of 2026-09-28 went with the default order of 2026-09-30: with
    mods.ini's own order as the default it would show nearly always. The
    report's Boot block and the lobby line keep the multiplayer note."""
    lines = [ln.strip() for ln in literal_code(built["ShowQmManager"])]
    assert not any("'tfoot'" in ln or "'ordcustom'" in ln or "qmSmFootColor" in ln
                   for ln in lines)


def test_the_ensure_adds_the_screens_under_their_own_names(built, screens):
    ensure = "\n".join(literal_code(built["qmUiEnsure"]))
    added = re.findall(r"qmUeAdd\(qmUeSm, '(\w+)', qmUeBase\+'([\w.]+)'\)", ensure)
    want = sorted((t.name, os.path.basename(t.into)) for t in screens)
    assert sorted(added) == want
    for t in screens:
        assert t.into.startswith("data/quartermaster/ui/")
    assert "'.\\data\\quartermaster\\ui\\'" in ensure


def test_every_state_run_by_name_exists(built):
    """A missing state name costs an IndexOfState ERROR per call (probe 10)."""
    states, _helpers = hbuild.load_sources()
    known = set(s.name for s in states)
    for name, data in built.items():
        for target in re.findall(r"StateMachineExecuteState\(\w+, '(\w+)', 0\)",
                                 "\n".join(literal_code(data))):
            assert target in known, "%s runs %s, which src/states does not define" % (name, target)
    gui = "\n".join(literal_code(built["EventQmManager"]))
    assert "ExecuteState(qmEmShowstate)" in gui


def test_every_command_sent_is_handled(built):
    act = "\n".join(literal_code(built["qmUiAct"]))
    handled = set(re.findall(r"\(qmUaCmd='(\w+)'\)", act))
    sent = set(re.findall(r"qmEmCmd := '(\w+)'", "\n".join(literal_code(built["EventQmManager"]))))
    sent |= set(re.findall(r"'cmd', '(\w+)'", "\n".join(literal_code(built["ShowQmManager"]))))
    assert sent, "no command found"
    # esc / enter are rewritten into cancel / close / confirm / filter first.
    assert {"esc", "enter"} <= handled
    missing = sorted(sent - handled)
    assert not missing, "qmUiAct does not handle %s" % missing


def test_open_workshop_is_the_vanilla_call(built, game_dir):
    with open(os.path.join(game_dir, "data", "gui", "menu.inc", "eventmainmenu.inc"), "rb") as fh:
        vanilla = fh.read().split(b"\r\n")
    # eventmainmenu.inc:155 is the arm of cTagModManager.
    call = vanilla[154].split(b";", 1)[1].strip().decode("ascii")
    assert call == "OpenURL('http://steamcommunity.com/app/333420/workshop/');"
    for name in ("ShowQmManager", "EventQmManager"):
        urls = [ln.strip() for ln in literal_code(built[name]) if "OpenURL(" in ln]
        assert urls and all(u == call for u in urls), urls


# ------------------------------------------------------------ texts and keys
def test_no_placeholder_mark_is_left_in_what_ships():
    """Until 2026-09-30 every visible text carried a TODO(owner) note (a
    placeholder); the texts were made final that day, so no source that
    ships, and nothing the build emits, may still carry one."""
    for root in (os.path.join(REPO, "src"), os.path.join(REPO, "ref")):
        for base, _dirs, names in os.walk(root):
            for n in names:
                if n.endswith((".pas", ".py")):
                    with open(os.path.join(base, n), "rb") as fh:
                        assert b"TODO(owner)" not in fh.read(), os.path.join(base, n)
    assert b"TODO(owner)" not in hbuild.mod_ini()
    with open(os.path.join(REPO, "README.md"), "rb") as fh:
        assert b"TODO(owner)" not in fh.read()


def test_no_glyph_outside_printable_ascii(built):
    for name, data in built.items():
        assert all(32 <= c <= 126 or c in (9, 10, 13) for c in data), name


_HANDLE = re.compile(r"var (\w+) : Integer = ParserSelectByKey\('(\w+)'\);")
_KEY_USE = re.compile(r"Parser(?:Get|Set)(?:Int)?ValueByKeyByHandle\((\w+), '(\w+)'")


def parser_keys(built):
    """`{parser name: {key}}` for every literal key the window reads or writes."""
    out = {}
    for data in built.values():
        lines = literal_code(data)
        handles = {}
        for ln in lines:
            for var, parser in _HANDLE.findall(ln):
                handles[var] = parser
        for ln in lines:
            for var, key in _KEY_USE.findall(ln):
                if var in handles:
                    out.setdefault(handles[var], set()).add(key)
    return out


def test_every_parser_key_is_documented(built):
    with open(UI_DOC, "rb") as fh:
        doc = fh.read().decode("ascii")
    keys = parser_keys(built)
    assert set(keys) >= {"qm_ui", "qm_rt", "qm_report", "qm_mods", "qm_index"}
    for parser, names in sorted(keys.items()):
        assert "`%s`" % parser in doc, "docs/ui.md does not name %s" % parser
        for key in sorted(names):
            assert re.search(r"`%s(<\w+>)?(_<\w+>)?`" % re.escape(key), doc), \
                "docs/ui.md does not document %s key %s" % (parser, key)


def test_keys_are_identifier_like(built):
    """Named-parser keys are case-folded and trimmed (probe 4): lower case only."""
    for parser, names in parser_keys(built).items():
        for key in names:
            assert re.match(r"^[a-z][a-z0-9_]*$", key), (parser, key)


def test_qm_rt_is_only_read_or_extended_with_ui_keys(built):
    keys = parser_keys(built)["qm_rt"]
    # `rs` is read only: a restart notice whose restart is gone is stale.
    # `setsave`, `setsaveseq` (M10): accepted options, written by qmTick;
    # `mf*` (M11): Create mod / about.cfg / Edit game file, done by qmTick;
    # `tr*` (M8 task 4): the activation check, run by qmTick; `trat` is when
    # it was asked, for the window's own timeout.
    assert keys == {"qmdir", "uiapply", "uiapplyseq", "uiapplyn", "uiapplydir",
                    "uiapplydis", "uiapplychg", "uiregen", "uiapplyordn", "uiapplyord",
                    "uiapplyorder", "rs", "setsave", "setsaveseq", "mfreq", "mffolder",
                    "mftitle", "mftype", "mfexcl", "mfdir", "mftags", "mfcam", "mfrel",
                    "trq", "trrow", "trsig", "trdone", "trat"}


# ---------------------------------------------------------------- the hooks
def _hook_template():
    hooks = [h for h in hbuild.load_hooks() if h.into == MENU_REL]
    assert len(hooks) == 1 and hooks[0].path == "src/hooks/eventmainmenu.pas"
    return hooks[0]


def test_the_menu_hook_is_a_hook_template():
    t = _hook_template()
    code = hbuild.render_lines(t, {})
    assert 0 < len(code) <= hbuild.HOOK_MAX_LINES
    assert sum(b"ExecuteState('ShowQmManager');" in c for c in code) == 1


@needs_game
def test_the_menu_hook_passes_the_hook_lints(env):
    rel, _data, findings = hbuild.build_hook(_hook_template(), GAME, {}, env)
    assert rel == MENU_REL
    assert findings == [], "\n".join(str(f) for f in findings)


def _vanilla_menu():
    with open(os.path.join(GAME, "data", "gui", "menu.inc", "eventmainmenu.inc"), "rb") as fh:
        return fh.read()


def _expected_menu(vanilla):
    """Vanilla bytes with the hook's code lines in front of Code value 0.

    Built here from the raw bytes, independently of hbuild's assembly: the
    hook index of eventmainmenu.inc is 0, so the lines go right in front of
    the first `[*] = ;` line and every other byte stays where vanilla has it.
    """
    lines = b"".join(hbuild.PREFIX + c + hbuild.CRLF
                     for c in hbuild.render_lines(_hook_template(), {}))
    at = vanilla.index(hbuild.PREFIX)
    return vanilla[:at] + lines + vanilla[at:], lines


@needs_game
def test_the_built_menu_is_vanilla_plus_the_hook_lines():
    vanilla = _vanilla_menu()
    data = hbuild.build(offline=True).outputs[MENU_REL]
    want, lines = _expected_menu(vanilla)
    assert data == want
    # Taking the hook lines out again gives vanilla, byte for byte.
    assert data.replace(lines, b"", 1) == vanilla
    assert len(data) == len(vanilla) + len(lines)
    # The same place by the S5 rule (ref.inc.hook_index), which merged output
    # uses too, and the first line after the hook is vanilla's first
    # (eventmainmenu.inc:4).
    values = inc.parse(vanilla).values
    hook = [b";" + c for c in hbuild.render_lines(_hook_template(), {})]
    assert inc.hook_index(values) == 0
    assert inc.parse(data).values == inc.insert_at_hook(values, hook)
    assert values[0] == b";var elmHnd : Integer = GetIntValueByName('ElementHandle');"


@needs_game
def test_the_shipped_menu_in_dist_is_vanilla_plus_the_hook_lines():
    with open(os.path.join(hbuild.DIST_MOD, *MENU_REL.split("/")), "rb") as fh:
        shipped = fh.read()
    vanilla = _vanilla_menu()
    want, lines = _expected_menu(vanilla)
    assert shipped == want
    assert shipped.replace(lines, b"", 1) == vanilla


def test_the_hook_opens_the_state_the_ensure_adds(built):
    with open(HOOK, "rb") as fh:
        hook = fh.read().decode("ascii")
    ensure = "\n".join(literal_code(built["qmUiEnsure"]))
    opened = re.findall(r"ExecuteState\('(\w+)'\)", hook)
    assert opened == ["ShowQmManager"]
    assert "qmUeAdd(qmUeSm, 'ShowQmManager'" in ensure
    # The hook reads the flag the ensure writes.
    assert "'ready')=1" in hook
    assert "ParserSetIntValueByKeyByHandle(qmUeUi, 'ready', 1);" in ensure


def test_cameracontrol_ensures_the_screens_on_every_docreate():
    """The ensure line is unconditional and comes after the boot line."""
    hooks = [h for h in hbuild.load_hooks() if h.into == "data/gui/menu.inc/cameracontrol.inc"]
    # The hook carries the generation constant (${hookgen}, plan S6).
    code = [c.decode("ascii") for c in hbuild.render_lines(
        hooks[0], hbuild._vars_for(hooks[0], hbuild.BUILD_VARIABLES))]
    assert len(code) <= hbuild.HOOK_MAX_LINES
    ensure = "StateMachineExecuteState(qmHookSm, 'qmUiEnsure', 0);"
    assert code.count(ensure) == 1
    at = code.index(ensure)
    # Not inside an if or a begin block: every DoCreate reaches it.
    assert code[at - 1].startswith("begin ParserCreate('qm_rt');") and code[at - 1].endswith("end;")
    assert at == len(code) - 1
    assert "qmBoot" in code[at - 1]


def test_the_ensure_does_nothing_outside_the_main_menu(built):
    """CameraControl runs in a battle too: there the ensure returns before it
    looks anything up, touches a parser or logs a line."""
    body = literal_code(built["qmUiEnsure"])
    main = next(i for i, ln in enumerate(body) if ln.startswith("if (gInterface.gamemode"))
    assert body[main] == "if (gInterface.gamemode<>gc_gamemode_mainmenu) then"
    assert body[main + 1] == "exit;"
    # Everything above is the inlined helper, the two nested functions and
    # comments: no statement runs before the guard.
    top = [ln for ln in body[:main] if ln and not ln.startswith((" ", "//"))]
    assert all(ln.startswith(("procedure ", "function ", "begin", "end;")) for ln in top), top
