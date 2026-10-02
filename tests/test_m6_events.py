"""EventQmManager, run offline: the GUI state that turns the window's events
into commands, on the script interpreter of tests/test_m3_pascal.py over an
emulated GUI (element names and handles, texts, the event values, the mouse,
the clock). The controller qmUiAct is stood in by a recorder, so each test
sees exactly the command, row, place and text the event state sends.

What it must do (docs/ui.md, the hands-on check of 2026-09-28):
  * the filter follows every keystroke: a key's release sends `filter` when
    the box's text changed, and nothing when it did not;
  * Esc / Enter by key release count only while an edit control has the
    focus, and one key arriving both as shortcut and as key release is
    taken once - two presses by the same way are two;
  * a list event only selects: drag was tried and dropped;
  * `rename` sets the main menu button's caption the vanilla way;
  * `verline` adds Quartermaster's version line to the main menu's corner.
This pins what the state does with the events the engine sends.
"""
import pytest

import test_m3_pascal as PAS
import test_m5_pascal as PAS5

PAS.BYREF_NATIVES["_misc_getguishoweventstatenames"] = (1, 2, 3)
PAS.BYREF_NATIVES["getguicurrentmousecoord"] = (0, 1)
PAS.BYREF_NATIVES["_gui_converthextotcolor"] = (1,)

TOP = 1
FILTER = 11
ACTIVE = 12
INSTALLED = 13
BUTTON = 14
MENU_CAPTION = 15
VERSION = 16
FRAME = 17                 # the main menu's left frame, wnewgame (showmainmenu.inc:93)
PATHS = {b"QmManager.fbox.filter.text": FILTER, b"QmManager.main.wnd.act.active": ACTIVE,
         b"QmManager.main.wnd.inst.installed": INSTALLED,
         b"MainMenu.col1.row1.wnewgame.bmodman.txtbtn": MENU_CAPTION,
         b"MainMenu.col1.row1.wnewgame.ver": VERSION}
NAMES = {FILTER: b"text", ACTIVE: b"active", INSTALLED: b"installed", BUTTON: b"bapply",
         MENU_CAPTION: b"txtbtn", VERSION: b"ver"}
#: The game's version text as showmainmenu.inc:151-173 makes it (a build, the
#: checksum in its grey), at its y above the frame's bottom, one line high.
GAME_VERSION = b"Version 1.0.0.123 %color(999999)% (B3CA)"
VER_X, VER_Y, LINE = -8, -16, 17


class Gui(PAS5.Engine):
    def __init__(self):
        PAS5.Engine.__init__(self)
        self.values = {}
        self.texts = {FILTER: b"", MENU_CAPTION: b"Warsztat mod\xf3w", VERSION: GAME_VERSION}
        # the frame's children: their y (bottom-anchored), height, visibility
        self.frame = [VERSION]
        self.ys = {VERSION: VER_Y}
        self.heights = {VERSION: LINE}
        self.hidden = set()
        self.named = {}            # name -> handle of the frame's children made here
        self.made = []
        self.widths = {}
        self.focused = 0
        self.lbutton = False
        self.mouse = (400, 100)
        self.items = {ACTIVE: (0, []), INSTALLED: (0, [])}   # (index, [tags])
        self.did = []
        self.sent = []

    # event values and names
    def n_GetIntValueByName(self, k):
        return self.values.get(k.lower(), 0)

    def n_GetValueByName(self, k):
        return self.values.get(k.lower(), b"")

    def n__misc_GetGUIShowEventStateNames(self, state, elm, show, event):
        elm.v, show.v, event.v = b"QmManager", b"ShowQmManager", b"EventQmManager"

    # elements
    def n__gui_GetTop(self):
        return TOP

    def n_GetGUIElementIndexByNameParent(self, path, parent):
        if parent == FRAME:
            return self.named.get(path, 0)
        return PATHS.get(path, 0) if parent == TOP else 0

    def n_GetGUIElementParentByIndex(self, h):
        return FRAME if h in self.frame else 0

    def n_GetGUIElementChildrenCount(self, h):
        return len(self.frame) if h == FRAME else 0

    def n_GetGUIElementChildrenByIndex(self, h, k):
        return self.frame[k]

    def n_GetGUIElementVisible(self, h):
        return h not in self.hidden

    def n_GetGUIElementPositionX(self, h):
        return VER_X

    def n_GetGUIElementPositionY(self, h):
        return self.ys.get(h, 0)

    def n_GetGUIElementWidth(self, h):
        return 400

    def n__gui_ConvertHexToTColor(self, hexcode, color):
        color.v = hexcode

    def n__gui_CreateText(self, name, parent, text, hal, val, x, y, w, h, thal, tval, font,
                          color, update):
        handle = 30 + len(self.made)
        self.made.append(dict(name=name, parent=parent, text=text, x=x, y=y, w=w, h=h,
                              font=font, color=color, update=update))
        self.frame.append(handle)
        self.named[name] = handle
        self.texts[handle] = text
        return handle

    def n_gc_halParentRightWidth(self):
        return 3

    def n_gc_valParentBottomHeight(self):
        return 3

    def n_gc_halRight(self):
        return 2

    def n_gc_valMiddle(self):
        return 1

    def n_gc_font_serif_10(self):
        return 10

    def n_GetGUIElementNameByIndex(self, h):
        return NAMES.get(h, b"")

    def n_IsElementByHandle(self, h):
        return h in NAMES

    def n_GetGUIElementText(self, h):
        return self.texts.get(h, b"")

    def n_SetGUIElementText(self, h, t):
        self.texts[h] = t

    def n_SetGUIElementWidth(self, h, w):
        self.widths[h] = w

    def n_GetGUIElementHeight(self, h):
        return self.heights.get(h, LINE)

    def n_SetGUIElementLogicWidth(self, h, w):
        self.did.append(("logicwidth", h, w))

    def n__gui_GetFontTextWidth(self, text, font):
        return 8 * len(text)

    def n_gc_font_serif_15(self):
        return 15

    def n_GetGUIFocusedElementHandle(self):
        return self.focused

    def n_GetGUIListBoxItemIndex(self, h):
        return self.items[h][0]

    def n_GetGUIListBoxItemTag(self, h, i):
        return self.items[h][1][i]

    def n_GetGUIListBoxTopIndex(self, h):
        return 0

    def n_GetGUIListBoxRowHeight(self, h):
        return 20

    def n__gui_GetAbsScaleByDPI(self, x, y):
        return 1.0

    def n_Round(self, f):
        return int(round(f))

    # the mouse
    def n_GetGUICurrentMouseCoord(self, x, y):
        x.v, y.v = self.mouse

    def n_IsGUIShortcutPressed(self, name):
        return name == b"LButton" and self.lbutton

    # what the state does to the GUI
    def n_OpenURL(self, url):
        self.did.append(("url", url))

    def n__gui_SetGUIElementVisibleByName(self, name, v):
        self.did.append(("visible", name, v))

    def n_SetGUIEventStateOnKeyDown(self, s):
        self.did.append(("keystate", s))

    def n_ExecuteState(self, s):
        self.did.append(("execute", s))

    # the vanilla constants the state names
    def n_gc_gui_event_tagClose(self):
        return 8003

    def n_gc_gui_hotkey_btnEscape(self):
        return 9001

    def n_gc_gui_hotkey_btnEnter(self):
        return 9002


def gui(n=4, ords=(0, 1, 2, 3), pe=(1, 1, 1, 1)):
    eng = Gui()
    PAS5.load(eng, "EventQmManager")
    ui = {"n": n, "sel": -1}
    for k, i in enumerate(ords):
        ui["ord%d" % k] = i
    for i, v in enumerate(pe):
        ui["pe%d" % i] = v
    eng.set("qm_ui", **ui)

    def controller():
        h = eng.named[b"qm_ui"]
        get = lambda k: eng.n_ParserGetValueByKeyByHandle(h, k)   # noqa: E731
        eng.sent.append((get(b"cmd"), int(get(b"arg")), int(get(b"argside")),
                         int(get(b"argto") or b"-1"), get(b"argtext")))
        # argto is only written for a `move`, which the window no longer sends.
        eng.n_ParserSetValueByKeyByHandle(h, b"cmd", b"")
    eng.states["qmuiact"] = PAS5.Fake(controller)
    return eng


def event(eng, status=b"", press=b"", tag=0, elm=0):
    eng.values = {b"status": status, b"press": press, b"tag": tag, b"elementhandle": elm}
    eng.states["eventqmmanager"].run()     # not PAS5.run: a missing native must fail here


# ------------------------------------------------------------- the filter
def test_a_key_release_sends_the_filter_only_when_the_text_changed():
    eng = gui()
    eng.texts[FILTER] = b"w"
    event(eng, b"key", b"u", 87)
    assert eng.sent == [(b"filter", -1, 0, -1, b"w")]
    assert ("execute", b"ShowQmManager") in eng.did
    eng.set("qm_ui", filter=b"w")
    event(eng, b"key", b"u", 39)            # an arrow key: the text is the same
    event(eng, b"key", b"d", 88)            # a key press: only releases count
    assert len(eng.sent) == 1


# ------------------------------------------------------------ Esc and Enter
def test_esc_by_key_release_counts_only_with_an_edit_control_focused():
    eng = gui()
    event(eng, b"key", b"u", 27)
    assert eng.sent == []
    eng.focused = FILTER
    event(eng, b"key", b"u", 27)
    assert [s[0] for s in eng.sent] == [b"esc"]


def test_one_key_by_both_ways_is_taken_once_and_two_presses_twice():
    eng = gui()
    eng.focused = FILTER
    event(eng, b"shortcut", b"c", 9001)
    event(eng, b"key", b"u", 27)            # the same keystroke's release
    assert [s[0] for s in eng.sent] == [b"esc"]
    event(eng, b"shortcut", b"c", 9001)     # a second press
    event(eng, b"shortcut", b"c", 9001)     # and a third, as quick
    assert [s[0] for s in eng.sent] == [b"esc", b"esc", b"esc"]
    eng.now += 1.0                          # a release long after is its own key
    event(eng, b"key", b"u", 27)
    assert len(eng.sent) == 4


# ---------------------------------------------------------------- no drag
def test_a_select_and_a_release_never_move_a_row():
    # Drag was dropped (2026-09-28): in the hands-on check every select
    # came with the button already up, so a list event only ever selects.
    eng = gui()
    eng.items[ACTIVE] = (1, [0, 1, 2, 3])
    eng.lbutton, eng.mouse = True, (400, 100)
    event(eng, b"select", b"c", 0, ACTIVE)
    eng.lbutton, eng.mouse = False, (400, 160)
    event(eng, b"", b"u", 0, ACTIVE)
    assert [s[0] for s in eng.sent] == [b"select"]
    assert not any(b"ui drag" in l for l in eng.log)


# ------------------------------------------------------------ the buttons
def test_up_and_down_send_the_selected_row():
    eng = gui()
    eng.set("qm_ui", sel=2)
    event(eng, b"button", b"c", 110)
    event(eng, b"button", b"c", 111)
    assert [s[:2] for s in eng.sent] == [(b"up", 2), (b"down", 2)]


# ------------------------------------------------------------ the rename
def test_rename_sets_the_menu_caption_width_first_and_counts():
    eng = gui()
    eng.set("qm_ui", rename=1)
    event(eng)
    assert eng.texts[MENU_CAPTION] == b"Mod Manager"
    assert eng.widths[MENU_CAPTION] == 8 * len(b"Mod Manager")
    assert (eng.key(b"qm_ui", b"rename"), eng.key(b"qm_ui", b"renames"),
            eng.key(b"qm_ui", b"renameoff")) == (b"0", b"1", b"")
    assert eng.sent == []                   # nothing else happens on that run


# ------------------------------------------------------ the version line
QM_LINE = b"Quartermaster " + PAS5.H.QM_VERSION.encode()


def test_the_version_line_is_a_text_of_its_own_a_line_above_the_game_s():
    eng = gui()
    eng.set("qm_ui", verline=1)
    event(eng)
    assert len(eng.made) == 1
    made = eng.made[0]
    assert (made["name"], made["parent"], made["text"]) == (b"qmver", FRAME, QM_LINE)
    assert (made["x"], made["y"], made["h"], made["color"]) == (VER_X, VER_Y - LINE, 0, b"FFDFAF")
    assert eng.texts[VERSION] == GAME_VERSION               # the game's text as it was
    assert (eng.key(b"qm_ui", b"verline"), eng.key(b"qm_ui", b"vers"),
            eng.key(b"qm_ui", b"veroff")) == (b"0", b"1", b"")
    assert eng.sent == []
    # Asked again while the text is there: nothing is made.
    eng.set("qm_ui", verline=1)
    event(eng)
    assert len(eng.made) == 1 and eng.key(b"qm_ui", b"vers") == b"1"


def test_the_version_line_goes_above_a_mod_s_own_line_over_the_game_s():
    # New Terrain Mod's 'NT' a line above 'ver' (its showmainmenu.inc:174-175);
    # a hidden text and a text-less child in the way do not count.
    eng = gui()
    nt, hidden, box = 40, 41, 42
    eng.frame += [box, hidden, nt]
    eng.ys.update({nt: VER_Y - 30, hidden: VER_Y - 60, box: VER_Y - 10})
    eng.texts.update({nt: b"Ebel's New Terrain Mod v1.6.0.3", hidden: b"x", box: b""})
    eng.hidden.add(hidden)
    eng.set("qm_ui", verline=1)
    event(eng)
    assert eng.made[0]["y"] == VER_Y - 30 - LINE
    assert eng.texts[nt] == b"Ebel's New Terrain Mod v1.6.0.3"
    assert any(b"ui version line: made, vers=1 stack=2 " in ln for ln in eng.log)


def test_a_version_line_that_cannot_be_found_again_turns_itself_off():
    eng = gui()
    eng.natives["getguielementindexbynameparent"] = (
        lambda path, parent: PATHS.get(path, 0) if parent == TOP else 0)
    eng.set("qm_ui", verline=1)
    event(eng)
    assert eng.key(b"qm_ui", b"veroff") == b"1"


def test_ping_answers_and_does_nothing_else():
    eng = gui()
    eng.set("qm_ui", ping=1)
    event(eng, b"button", b"c", 103)
    assert (eng.key(b"qm_ui", b"pong"), eng.sent) == (b"1", [])


# -------------------------------------------- qmTick: the notice and the caption
class TickGui(Gui):
    def n_GUIExecuteState(self, s):
        self.did.append(("gui", s))


def tick(caption=b"Mod Manager", qmver=True, **rt):
    eng = TickGui()
    PAS5.load(eng, "qmTick", "qmRestart", "qmMarkerSave")
    eng.texts[MENU_CAPTION] = caption
    if qmver:
        eng.named[b"qmver"] = 30                   # the frame has Quartermaster's line
    eng.set("qm_ui", ready=1)
    eng.set("qm_rt", **rt)
    return eng


def test_the_tick_shows_the_restart_notice_a_frame_before_the_restart():
    eng = tick(tick=1, rs=1, rsdue=10015, rskind=b"auto", sync=0)
    eng.now = 1001.0
    PAS5.run(eng, "qmTick")
    assert ("gui", b"ShowQmManager") in eng.did and eng.key(b"qm_ui", b"mode") == b"2"
    assert eng.restarted == [] and eng.key(b"qm_rt", b"rsnote") == b"10010"
    eng.now = 1001.5
    PAS5.run(eng, "qmTick")
    assert eng.restarted == ["lan", "steam", "restart"]
    assert eng.did.count(("gui", b"ShowQmManager")) == 1


def test_a_restart_due_at_once_still_waits_one_frame_for_its_notice():
    eng = tick(tick=1, rs=1, rsdue=10000, rskind=b"apply", sync=0)
    eng.now = 1001.0
    PAS5.run(eng, "qmTick")
    assert eng.restarted == []
    PAS5.run(eng, "qmTick")                 # the same tenth: not yet
    assert eng.restarted == []
    eng.now = 1001.1
    PAS5.run(eng, "qmTick")
    assert eng.restarted == ["lan", "steam", "restart"]


def test_no_notice_during_an_mp_sync_or_without_the_screens():
    eng = tick(tick=1, rs=1, rsdue=10000, sync=1)
    eng.now = 1001.0
    PAS5.run(eng, "qmTick")
    assert ("gui", b"ShowQmManager") not in eng.did and eng.key(b"qm_rt", b"rsnote") == b""
    eng = tick(tick=1, rs=1, rsdue=10000, sync=0)
    eng.set("qm_ui", ready=0)
    eng.now = 1001.0
    PAS5.run(eng, "qmTick")
    assert ("gui", b"ShowQmManager") not in eng.did and eng.key(b"qm_rt", b"rsnote") == b"10010"


def test_the_guard_notice_is_drawn_again_when_a_rebuilt_menu_took_its_window():
    """Run look-wsH: the game's second start-up DoCreate rebuilt the GUI right
    after qmTick had opened the notice, and the window was gone while qm_ui
    mode stayed 3. On a main-menu frame with nothing under way the notice is
    drawn again, when its window is missing or hidden - not when it is up,
    not in another mode, not while a restart is pending."""
    window = 60

    def runs(mode=3, present=False, hidden=False, **rt):
        eng = tick(tick=0, **rt)
        paths = dict(PATHS)
        paths[b"MainMenu"] = 50
        if present:
            paths[b"QmManager"] = window
        if hidden:
            eng.hidden.add(window)
        eng.natives["getguielementindexbynameparent"] = (
            lambda path, parent: paths.get(path, 0) if parent == TOP else eng.named.get(path, 0))
        eng.set("qm_ui", mode=mode)
        PAS5.run(eng, "qmTick")
        return eng, ("gui", b"ShowQmManager") in eng.did

    eng, again = runs()
    assert again and eng.key(b"qm_ui", b"gdagain") == b"1"
    assert any(b"tick: the guard notice shown again" in ln for ln in eng.log)
    assert runs(present=True, hidden=True)[1]
    assert not runs(present=True)[1]
    assert not runs(mode=0)[1]
    assert not runs(rs=1)[1]


def test_the_tick_asks_for_the_caption_only_when_the_menu_drew_it_again():
    eng = tick(caption=b"Warsztat mod\xf3w", tick=0, uiapply=0)
    PAS5.run(eng, "qmTick")
    assert eng.did == [("gui", b"EventQmManager")] and eng.key(b"qm_ui", b"rename") == b"1"
    eng = tick(tick=0, uiapply=0)
    PAS5.run(eng, "qmTick")
    assert eng.did == []
    # Turned off when a caption did not read back, and without the screens.
    for keys in ({"renameoff": 1}, {"ready": 0}):
        eng = tick(caption=b"Warsztat", tick=0, uiapply=0)
        eng.set("qm_ui", **keys)
        PAS5.run(eng, "qmTick")
        assert eng.did == []


def test_the_tick_asks_for_the_version_line_only_when_the_menu_drew_it_again():
    eng = tick(qmver=False, tick=0, uiapply=0)
    PAS5.run(eng, "qmTick")
    assert eng.did == [("gui", b"EventQmManager")] and eng.key(b"qm_ui", b"verline") == b"1"
    eng = tick(tick=0, uiapply=0)                     # the line is there
    PAS5.run(eng, "qmTick")
    assert eng.did == []
    # Turned off when a line did not read back, and without the screens.
    for keys in ({"veroff": 1}, {"ready": 0}):
        eng = tick(qmver=False, tick=0, uiapply=0)
        eng.set("qm_ui", **keys)
        PAS5.run(eng, "qmTick")
        assert eng.did == []


LOBBY = 70
WINDOW = 71


def tick_at(paths, hidden=(), **rt):
    """qmTick with the elements `paths` ({path: handle}) under the top, the
    screens ready, the caption and the version line in place; the states it
    runs are recorders."""
    eng = tick(tick=0, **rt)
    eng.hidden.update(hidden)
    have = dict(PATHS)
    have.update(paths)
    eng.natives["getguielementindexbynameparent"] = (
        lambda path, parent: have.get(path, 0) if parent == TOP else
        (have.get(b"qmlobby", 0) if parent == LOBBY else eng.named.get(path, 0)))
    for name in ("qmModFiles", "qmTrial", "qmUiAct", "qmSetSave"):
        eng.states[name.lower()] = PAS5.Fake((lambda n: lambda: eng.did.append(("run", n)))(name))
    return eng


@pytest.mark.parametrize("canon, custom", [(0, b"1"), (1, b"0")])
def test_the_lobby_gets_its_line_once_the_order_is_known(canon, custom):
    shell = {b"InternetShell.backgroundparent.background": LOBBY}
    eng = tick_at(shell)
    eng.set("qm_order", src=b"ini", canon=canon)
    PAS5.run(eng, "qmTick")
    assert eng.did == [("gui", b"EventQmManager")]
    assert (eng.key(b"qm_ui", b"lobby"), eng.key(b"qm_ui", b"lobbycustom")) == (b"1", custom)
    # Not without the order, not twice, not once turned off, not outside the shell.
    for paths, order, ui in ((shell, None, {}), ({**shell, b"qmlobby": 80}, b"ini", {}),
                             (shell, b"ini", {"lobbyoff": 1}), ({}, b"ini", {})):
        eng = tick_at(paths)
        if order is not None:
            eng.set("qm_order", src=order, canon=canon)
        if ui:
            eng.set("qm_ui", **ui)
        PAS5.run(eng, "qmTick")
        assert eng.did == [], (paths, order, ui)


def test_the_guard_notice_opens_the_window_once_and_marks_the_note_shown():
    eng = tick_at({}, gdshow=1, busy=0, rs=0)

    def save_flat(h, path):             # guard.cfg is a flat parser file: its keys
        eng.written[path] = dict(eng.nodes[h].keys)
        return True
    eng.natives["parsersavetofilebyhandle"] = save_flat
    eng.set("qm_glob_note", n=1, shown=0, restarted=0)
    eng.set("qm_ui", gdln=1)
    PAS5.run(eng, "qmTick")
    assert eng.did == [("gui", b"ShowQmManager")]
    assert (eng.key(b"qm_rt", b"gdshow"), eng.key(b"qm_ui", b"gdopen")) == (b"0", b"1")
    assert eng.written[PAS5.SAVE + b"quartermaster\\guard.cfg"][b"shown"] == b"1"
    assert any(l.startswith(b"[qm] tick: the guard notice opened, mode=") and l.endswith(b"lines=1")
               for l in eng.log)
    PAS5.run(eng, "qmTick")                           # once
    assert eng.did == [("gui", b"ShowQmManager")]
    # Not while a restart is pending, a boot runs or a map is loaded.
    for rt, stage in (({"rs": 1}, 0), ({"busy": 1}, 0), ({}, 2)):
        eng = tick_at({}, gdshow=1, busy=0, rs=0)
        eng.set("qm_rt", **rt)
        eng.gamestage = stage
        PAS5.run(eng, "qmTick")
        assert ("gui", b"ShowQmManager") not in eng.did, (rt, stage)


def test_a_harness_runs_switch_opens_the_window_once():
    eng = tick_at({}, uishow=1, gdshow=0, busy=0, rs=0)
    PAS5.run(eng, "qmTick")
    assert eng.did == [("gui", b"ShowQmManager")] and eng.key(b"qm_rt", b"uishow") == b"0"
    assert b"[qm] tick: the window opened for the run (qm_show_ui.flag)" in eng.log


@pytest.mark.parametrize("shown", [True, False])
def test_a_mod_files_request_runs_and_an_open_window_says_how_it_went(shown):
    eng = tick_at({b"QmManager": WINDOW}, hidden=() if shown else (WINDOW,),
                  mfreq=b"create", busy=0)
    PAS5.run(eng, "qmTick")
    assert eng.did == [("run", "qmModFiles")] + ([("gui", b"ShowQmManager")] if shown else [])


@pytest.mark.parametrize("shown", [True, False])
def test_an_activation_check_runs_once_and_the_controller_takes_its_answer(shown):
    eng = tick_at({b"QmManager": WINDOW}, hidden=() if shown else (WINDOW,),
                  trq=2, trdone=1, busy=0)
    PAS5.run(eng, "qmTick")
    assert eng.did == [("run", "qmTrial"), ("run", "qmUiAct")] + (
        [("gui", b"ShowQmManager")] if shown else [])
    assert eng.key(b"qm_ui", b"cmd") == b"trialdone" and eng.key(b"qm_rt", b"trdone") == b"2"
    n = len(eng.did)
    PAS5.run(eng, "qmTick")                           # answered: not again
    assert len(eng.did) == n


def test_accepted_options_are_saved_once_and_nothing_runs_while_a_boot_does():
    eng = tick_at({}, setsave=1, busy=0)
    PAS5.run(eng, "qmTick")
    assert eng.did == [("run", "qmSetSave")] and eng.key(b"qm_rt", b"setsave") == b"0"
    eng = tick_at({}, setsave=1, mfreq=b"create", trq=1, busy=1)
    PAS5.run(eng, "qmTick")
    assert eng.did == []
