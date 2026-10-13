"""Mod settings (plan G16, M10) and the about.cfg rules in the manager window
(plan G15b, M8), run offline on the script interpreter: qmAbout and
qmSettings as the boot runs them, then the window's controller (qmUiAct and
the states it runs) driven by commands, and qmTick's save.

The emulated engine adds what these states use beyond the window tests':
named children of a parser (ParserAddChildByIndex / ParserSelectByHandleByKey,
the layout vanilla keeps its hotkeys in, eventsettings.inc:702-729), a
settings file that round-trips them, and hotkeys.cfg loaded as its `[*]`
records (registershortcuts.inc:187-198 reads it that way). The file format
the engine writes is not modelled - only that what is saved loads back; the
in-game run shows the real file.
"""
import copy
import random

import pytest

import test_m5_pascal as PAS5
import test_m6_window as W6
from ref import about as A

QM = PAS5.QM
SAVE = PAS5.SAVE
WASD = b"mods\\QMTestWASD"
CAM2 = b"mods\\QMTestCam2"
REQ = b"mods\\QMTestNeedsWasd"
SETTINGS = SAVE + b"quartermaster\\settings.cfg"
HOTKEYS = b".\\data\\game\\var\\hotkeys.cfg"
PLAYER_HOTKEYS = SAVE + b"hotkeys\\hotkeys.cfg"
SHORTCUTS = b".\\data\\gui\\menu.inc\\registershortcuts.inc"

WASD_ABOUT = (b"id = qmtestwasd\r\nname = WASD camera\r\nexclusive = camera\r\n"
              b"setting = camera_left;key;A;Camera left\r\n"
              b"setting = camera_right;key;D;Camera right\r\n"
              b"setting = smooth;bool;1;Smooth scrolling\r\n"
              b"setting = speed;int;6;Speed;1..8..2\r\n"
              b"setting = zoom;float;1.5;Zoom;0.5..2..0.25\r\n"
              b"setting = mode;choice;fast;Mode;slow|fast|off\r\n"
              b"setting = tag;text;qm;Tag;5\r\n")
FILES = {
    WASD + b"\\about.cfg": WASD_ABOUT,
    CAM2 + b"\\about.cfg": b"exclusive = camera\r\n",
    REQ + b"\\about.cfg": b"requires = qmtestwasd\r\nsetting = x;key;F;X key\r\n",
    QM + b"\\data\\quartermaster\\core.aix": b"x",
    HOTKEYS: (b"section.begin\r\n   [*] : struct.begin\r\n      Key = J\r\n      Action = build|%nat%tem\r\n"
              b"   struct.end\r\n   [*] : struct.begin\r\n      Key = C\r\n      AlternativeKey = Q\r\n"
              b"      Action = build|%nat%cen\r\n   struct.end\r\n   [*] : struct.begin\r\n      Key = V\r\n"
              b"      Action = event|nextmsg\r\n   struct.end\r\nsection.end\r\n"),
    SHORTCUTS: (b"section.begin\r\n   Name = RegisterShortcuts\r\n   Code : struct.begin\r\n"
                b"      [*] = ;RegisterGUIShortcutIgnoreShift(False, 'myname', 'K', 'Shift+Ctrl+Alt', 'spiDown', 'OnShortcut', 0);\r\n"
                b"      [*] = ;// RegisterGUIShortcut(False, 'old', 'U', 'spiDown', 'OnShortcut', 0);\r\n"
                b"      [*] = ;RegisterGUIShortcut(False, 'qmwasdleftr', qmKey, 'spiDown', 'OnCamera', 20);\r\n"
                b"   struct.end\r\nsection.end\r\n"),
}


class Kid(object):
    """A named child of a parser node."""

    def __init__(self, name, handle):
        self.name, self.handle = name, handle


class Engine(W6.Engine):
    def __init__(self, files, mods):
        W6.Engine.__init__(self, files, mods=mods)
        self.kids = {}          # parent handle -> [Kid]
        self.saved = {}         # path -> a copy of the saved tree

    def _tree(self, h):
        n = self.nodes[h]
        return (dict(n.keys), [(k.name, self._tree(k.handle)) for k in self.kids.get(h, [])])

    def _plant(self, h, tree):
        keys, kids = tree
        self.nodes[h].keys = dict(keys)
        self.kids[h] = []
        for name, sub in kids:
            c = self._node()
            self.kids[h].append(Kid(name, c.handle))
            self._plant(c.handle, sub)

    def n_ParserAddChildByIndex(self, h, name):
        c = self._node()
        self.kids.setdefault(h, []).append(Kid(name.strip().lower(), c.handle))
        return c.handle

    def n_ParserSelectByHandleByKey(self, h, key):
        for k in self.kids.get(h, []):
            if k.name == key.strip().lower():
                return k.handle
        if key.strip().lower() != b"code" and not getattr(self.nodes[h], "inc", None):
            return 0
        return W6.Engine.n_ParserSelectByHandleByKey(self, h, key)

    def n_ParserGetCountByHandle(self, h):
        if self.kids.get(h):
            return len(self.kids[h])
        return W6.Engine.n_ParserGetCountByHandle(self, h)

    def n_ParserSelectByHandleByIndex(self, h, i):
        kids = self.kids.get(h, [])
        return kids[i].handle if 0 <= i < len(kids) else 0

    def n_ParserClearByHandle(self, h):
        self.kids[h] = []
        W6.Engine.n_ParserClearByHandle(self, h)

    def n_ParserSaveToFileByHandle(self, h, path):
        if path == SETTINGS:
            self.saved[path] = copy.deepcopy(self._tree(h))
            self.written[path] = b"saved"
            return True
        return W6.Engine.n_ParserSaveToFileByHandle(self, h, path)

    def n_ParserLoadFromFileByHandle(self, h, path):
        if path == SETTINGS and path in self.saved:
            self._plant(h, copy.deepcopy(self.saved[path]))
            return True
        if path in (HOTKEYS, PLAYER_HOTKEYS):
            data = self._file(path)
            if data is None:
                return False
            self.kids[h] = []
            cur = None
            for line in data.replace(b"\r", b"").split(b"\n"):
                s = line.strip()
                if s == b"[*] : struct.begin":
                    cur = self.n_ParserAddChildByIndex(h, b"*")
                elif s == b"struct.end":
                    cur = None
                elif cur and b" = " in s:
                    k, v = s.split(b" = ", 1)
                    self.nodes[cur].keys[k.lower()] = v
            return True
        return W6.Engine.n_ParserLoadFromFileByHandle(self, h, path)

    def n_StrToLowerCase(self, s):
        return s.lower()


def mods(wasd=True, cam2=False, req=True):
    return [(WASD, wasd, b""), (CAM2, cam2, b""), (REQ, req, b""), (QM, True, b"0")]


def booted(files=None, mod_list=None, saved=None):
    """The boot's part (qmAbout, qmSettings, qmModList for the canonical
    order) and a window opened on it."""
    fs = dict(FILES)
    fs.update(files or {})
    eng = Engine(fs, mod_list or mods())
    if saved is not None:
        eng.saved[SETTINGS] = saved
        eng.fs[SETTINGS] = b"saved"
    PAS5.load(eng, "qmAbout", "qmSettings", "qmModList", "qmUiAct", "qmUiModel", "qmUiDetails",
              "qmUiApply", "qmUiOrder", "qmAbRules")
    PAS5.run(eng, "qmAbout")
    PAS5.run(eng, "qmSettings")
    PAS5.run(eng, "qmModList")
    # qmOrder keeps the canonical order as cord<k> (the window's Auto-sort).
    n = int(eng.key(b"qm_mods", b"n"))
    for k in range(n):
        eng.set("qm_mods", **{"cord%d" % k: int(eng.key(b"qm_mods", b"ord%d" % k))})
    eng.set("qm_rt", uiapply=0, uiapplyseq=0)
    W6.cmd(eng, "open")
    return eng


def ui(eng, key):
    return eng.key(b"qm_ui", key.encode())


def setting(eng, mod, key):
    h = eng.n_ParserSelectByHandleByKey(eng.named[b"qm_settings"], mod)
    return eng.n_ParserGetValueByKeyByHandle(h, key) if h else None


# ------------------------------------------------------------ the store
def test_the_boot_fills_every_declared_setting_with_its_default():
    eng = booted()
    assert setting(eng, b"qmtestwasd", b"camera_left") == b"A"
    assert setting(eng, b"qmtestwasd", b"zoom") == b"1.50"
    assert setting(eng, b"qmtestwasd", b"mode") == b"fast"
    # a mod without an id keeps its settings under its folder's name
    assert setting(eng, b"qmtestneedswasd", b"x") == b"F"
    assert eng.key(b"qm_about", b"mid2") == b"qmtestneedswasd"


def test_a_stored_value_that_does_not_fit_becomes_the_default():
    saved = ({}, [(b"qmtestwasd", ({b"speed": b"99", b"zoom": b"1.5", b"mode": b"off",
                                     b"tag": b"toolong", b"camera_left": b"L"}, []))])
    eng = booted(saved=saved)
    assert setting(eng, b"qmtestwasd", b"speed") == b"6"       # off its range
    assert setting(eng, b"qmtestwasd", b"zoom") == b"1.50"     # not its places
    assert setting(eng, b"qmtestwasd", b"mode") == b"off"      # a choice: kept
    assert setting(eng, b"qmtestwasd", b"tag") == b"qm"        # too long
    assert setting(eng, b"qmtestwasd", b"camera_left") == b"L"  # kept


# ------------------------------------------------------ rules in the window
def test_a_second_camera_mod_cannot_be_activated():
    eng = booted()
    W6.cmd(eng, "select", arg=1)
    W6.cmd(eng, "activate")
    assert ui(eng, "pe1") == b"0"
    # Cam2 loads first in canonical order, so it is named first.
    assert ui(eng, "msg") == b"Not activated: QMTestCam2 and QMTestWASD both take the camera slot; only one can be active."


def test_deactivating_a_requirement_blocks_apply_and_names_it():
    eng = booted()
    W6.cmd(eng, "select", arg=0)
    W6.cmd(eng, "deactivate")
    assert ui(eng, "pafail") == b"1" and ui(eng, "pat0") == b"FAIL"
    assert ui(eng, "pa0") == b"QMTestNeedsWasd needs QMTestWASD, which is not active"
    W6.cmd(eng, "apply")
    assert ui(eng, "mode") == b"1" and ui(eng, "confblk") == b"1" and ui(eng, "confbrule") == b"1"
    W6.cmd(eng, "confirm")
    assert ui(eng, "mode") == b"0" and eng.key(b"qm_rt", b"uiapply") == b"0"
    assert ui(eng, "msg") == b"Not applied: first fix what the list showed."


def test_a_loaded_row_that_breaks_a_rule_reads_fail():
    eng = booted(mod_list=mods(wasd=False))
    assert (ui(eng, "st2"), ui(eng, "stsrc2")) == (b"FAIL", b"about")
    assert ui(eng, "why2") == b"QMTestNeedsWasd needs QMTestWASD, which is not active"


def test_auto_sort_puts_the_canonical_order_in_the_pending_one():
    eng = booted()
    W6.cmd(eng, "select", arg=0, side=1)
    W6.cmd(eng, "down", arg=0)
    assert ui(eng, "ordchg") == b"1"
    W6.cmd(eng, "autosort")
    assert ui(eng, "ordchg") == b"0"
    assert [ui(eng, "ord%d" % k) for k in range(4)] == [ui(eng, "cord%d" % k) for k in range(4)]


# ------------------------------------------------------------- the Options view
def opened():
    eng = booted()
    W6.cmd(eng, "select", arg=0)
    assert ui(eng, "abs0") == b"7"
    W6.cmd(eng, "options")
    assert ui(eng, "panel") == b"2" and ui(eng, "optn") == b"7"
    return eng


def button(eng, k, action=0):
    W6.cmd(eng, "optbtn", arg=k, to=action)


def test_every_type_changes_the_way_its_buttons_say():
    eng = opened()
    button(eng, 2)                       # bool: switch
    assert ui(eng, "ov2") == b"0"
    button(eng, 3)                       # int 6 + 2 = 8, then clamped at 8
    button(eng, 3)
    assert ui(eng, "ov3") == b"8"
    button(eng, 3, 1)
    assert ui(eng, "ov3") == b"6"
    button(eng, 4, 1)                    # float 1.50 - 0.25
    assert ui(eng, "ov4") == b"1.25"
    button(eng, 5)                       # choice: fast -> off -> slow
    button(eng, 5)
    assert ui(eng, "ov5") == b"slow"
    button(eng, 5, 1)
    assert ui(eng, "ov5") == b"off"
    # nothing is stored before Accept
    assert setting(eng, b"qmtestwasd", b"speed") == b"6"


def capture(eng, k, key):
    button(eng, k)
    assert ui(eng, "optcap") == b"%d" % k
    W6.cmd(eng, "optkey", text=key)
    assert ui(eng, "optcap") == b"-1"
    return ui(eng, "msg")


def test_a_key_already_taken_is_refused_with_the_reason():
    eng = opened()
    assert capture(eng, 0, b"P") == b"Key P not taken: the game does not let a hotkey use it."
    assert capture(eng, 0, b"Ctrl+S") == b"Key Ctrl+S not taken: the game does not let a hotkey use it."
    assert capture(eng, 0, b"D") == b"Key D not taken: it is Camera right already."
    assert capture(eng, 0, b"F") == b"Key F not taken: QMTestNeedsWasd uses it for X key."
    assert capture(eng, 0, b"J") == b"Key J not taken: the game's hotkey build|%nat%tem uses it."
    assert capture(eng, 0, b"Q") == b"Key Q not taken: the game's hotkey build|%nat%cen uses it."
    assert capture(eng, 0, b"K") == b"Key K not taken: the game's shortcut myname uses it."
    assert ui(eng, "ov0") == b"A"
    assert capture(eng, 0, b"") == b"Key not changed."
    # a commented-out line and a key from a variable register nothing
    assert capture(eng, 0, b"U") == b"" and ui(eng, "ov0") == b"U"
    assert capture(eng, 0, b"A") == b"" and ui(eng, "ov0") == b"A"     # its own default
    # an `event` hotkey does not meet a key that works everywhere (vanilla's
    # interface rule, hotkeysettings.inc:210-216)
    assert capture(eng, 0, b"V") == b"" and ui(eng, "ov0") == b"V"


def test_the_player_s_saved_hotkeys_are_the_ones_checked():
    player = FILES[HOTKEYS].replace(b"Key = J", b"Key = L")
    eng = booted(files={PLAYER_HOTKEYS: player})
    W6.cmd(eng, "select", arg=0)
    W6.cmd(eng, "options")
    assert capture(eng, 0, b"J") == b""
    assert capture(eng, 0, b"L") == b"Key L not taken: the game's hotkey build|%nat%tem uses it."


def test_accept_stores_the_copy_asks_for_the_file_and_the_new_keys():
    eng = opened()
    capture(eng, 0, b"L")
    button(eng, 2)
    W6.cmd(eng, "optacc")
    assert ui(eng, "panel") == b"0" and ui(eng, "rereg") == b"1"
    assert ui(eng, "msg") == b"Options saved: 2 changed."
    assert setting(eng, b"qmtestwasd", b"camera_left") == b"L"
    assert setting(eng, b"qmtestwasd", b"smooth") == b"0"
    assert eng.key(b"qm_rt", b"setsave") == b"1" and SETTINGS not in eng.written
    # the file comes from qmTick
    PAS5.load(eng, "qmTick", "qmRestart", "qmMarkerSave", "qmSetSave")
    PAS5.run(eng, "qmTick")
    assert eng.key(b"qm_rt", b"setsave") == b"0" and SETTINGS in eng.saved
    # ... and the next boot loads it back
    again = booted(saved=eng.saved[SETTINGS])
    assert setting(again, b"qmtestwasd", b"camera_left") == b"L"


def test_accept_refuses_two_settings_on_one_key_and_cancel_drops_the_copy():
    eng = opened()
    capture(eng, 1, b"L")
    # camera_left's own stored key is A; put camera_right's default D there
    eng.set("qm_ui", ov0=b"L")
    W6.cmd(eng, "optacc")
    assert ui(eng, "msg") == b"Not saved: Camera left and Camera right are both L."
    assert ui(eng, "panel") == b"2"
    W6.cmd(eng, "optdef")
    assert ui(eng, "ov0") == b"A" and ui(eng, "ov1") == b"D"
    button(eng, 3)
    W6.cmd(eng, "esc")                   # Esc in the view is Cancel
    assert ui(eng, "panel") == b"0" and ui(eng, "msg") == b"Options not changed."
    assert setting(eng, b"qmtestwasd", b"speed") == b"6"


def test_esc_while_waiting_for_a_key_keeps_the_old_key():
    eng = opened()
    button(eng, 0)
    W6.cmd(eng, "esc")
    assert ui(eng, "panel") == b"2" and ui(eng, "optcap") == b"-1"
    assert ui(eng, "msg") == b"Key not changed." and ui(eng, "ov0") == b"A"


def test_a_text_setting_is_edited_in_the_box_and_cut_to_its_length():
    eng = opened()
    button(eng, 6)
    assert ui(eng, "optsel") == b"6" and ui(eng, "typed") == b"qm"
    W6.cmd(eng, "filter", text=b"abcdefg")
    assert ui(eng, "ov6") == b"abcde" and ui(eng, "msg") == b"At most 5 characters."
    assert ui(eng, "filter") == b""                      # the list filter is untouched
    W6.cmd(eng, "optacc")
    assert setting(eng, b"qmtestwasd", b"tag") == b"abcde"
    assert ui(eng, "typed") == b""


# ------------------------------------------- more than 32 settings, and groups
def many_about(sizes):
    """An about.cfg of bool settings s0, s1, ... in groups: `(title, count)`
    each, an empty title for settings before any `group` line."""
    out, k = [b"id = qmtestwasd\r\n"], 0
    for title, count in sizes:
        if title:
            out.append(b"group = " + title + b"\r\n")
        for _ in range(count):
            out.append(b"setting = s%d;bool;1;Setting %d\r\n" % (k, k))
            k += 1
    return b"".join(out)


def opened_on(data):
    eng = booted(files={WASD + b"\\about.cfg": data})
    W6.cmd(eng, "select", arg=0)
    W6.cmd(eng, "options")
    assert ui(eng, "panel") == b"2"
    return eng


def rows_of(eng):
    return [(int(ui(eng, "orw%d" % j)), int(ui(eng, "orh%d" % j)))
            for j in range(int(ui(eng, "optrows")))]


def twin_rows(data, group=0, query=b""):
    kind = {b"set": 0, b"head": 1, b"more": 2, b"none": 0}
    return [(k, kind[what]) for what, k in A.option_view(A.parse(data).settings, group, query)]


def groups_of(eng):
    return [(ui(eng, "ogt%d" % g), int(ui(eng, "ogc%d" % g))) for g in range(int(ui(eng, "ogn")))]


def _shapes():
    fixed = [[(b"", 7)], [(b"", 10)], [(b"", 11)], [(b"", 23)], [(b"", 3), (b"A", 5)], [(b"A", 4), (b"B", 4), (b"C", 4)],
             [(b"A", 6), (b"B", 5)], [(b"", 9), (b"A", 1)], [(b"A", 12), (b"B", 2)],
             [(b"", 2), (b"A", 12)], [(b"A", 19)], [(b"A", 2), (b"A", 2), (b"B", 1), (b"A", 1)],
             [(b"A", 9), (b"B", 9), (b"C", 9)], [(b"A", 10)], [(b"A", 1)] * 3 + [(b"B", 1)] * 12,
             [(b"Match interface", 30), (b"Camera | keys", 30), (b"Economy", 40)]]
    rnd = random.Random(11)
    for _ in range(16):
        shape = [(rnd.choice([b"A", b"B", b"C"]), rnd.randint(1, 13)) for _ in range(rnd.randint(1, 8))]
        if rnd.random() < 0.5:
            shape.insert(0, (b"", rnd.randint(1, 11)))
        fixed.append(shape)
    return fixed


@pytest.mark.parametrize("shape", _shapes())
def test_the_rows_of_the_options_view_equal_the_twin(shape):
    data = many_about(shape)
    st = A.parse(data).settings
    eng = opened_on(data)
    assert int(ui(eng, "optn")) == len(st) == sum(c for _t, c in shape) <= A.MAX_SETTINGS
    groups = A.option_groups(st)
    assert groups_of(eng) == groups
    assert (ui(eng, "optstrip"), ui(eng, "optper")) == (
        (b"1", b"9") if A.option_strip(st) else (b"0", b"10"))
    # it opens on the first group; without groups that is every setting
    assert ui(eng, "optgrp") == b"0" and rows_of(eng) == twin_rows(data, 0)
    if not groups:
        # no group line: row j is setting j, as before 0.1.6
        assert rows_of(eng) == [(k, 0) for k in range(len(st))]
    if not A.option_strip(st):
        return
    # every group alone, then - the list's last entry - all under their titles
    for g in range(len(groups) + 1):
        W6.cmd(eng, "optgroup", arg=g)
        assert ui(eng, "optgrp") == b"%d" % g and rows_of(eng) == twin_rows(data, g)
        assert int(ui(eng, "optshown")) == sum(1 for k, h in rows_of(eng) if h == 0 and k >= 0)
    assert int(ui(eng, "optshown")) == len(st)
    # a search goes over every group, whatever the list shows
    W6.cmd(eng, "optgroup", arg=0)
    for q in (b"setting 1", b"SETTING 2", b"a", b"camera", b"g 1", b"no such"):
        W6.cmd(eng, "optfind", text=q)
        assert ui(eng, "optq") == q and rows_of(eng) == twin_rows(data, 0, q)
    W6.cmd(eng, "optfind", text=b"")
    assert rows_of(eng) == twin_rows(data, 0)


def test_the_pages_follow_the_rows_not_the_settings():
    eng = opened_on(many_about([(b"A", 6), (b"B", 6), (b"C", 6)]))
    # the first group alone: one page, and Next stays on it
    assert ui(eng, "optn") == b"18" and ui(eng, "optrows") == b"6"
    W6.cmd(eng, "optpage", arg=1)
    assert ui(eng, "optpg") == b"0"
    # All settings, nine rows a page under the strip: a group of six with its
    # title does not fit the two rows left, so each group has a page
    W6.cmd(eng, "optgroup", arg=3)
    assert ui(eng, "optrows") == b"25" and rows_of(eng)[7:10] == [(-1, 0)] * 2 + [(6, 1)]
    W6.cmd(eng, "optpage", arg=-1)
    assert ui(eng, "optpg") == b"0"
    W6.cmd(eng, "optpage", arg=1)
    W6.cmd(eng, "optpage", arg=1)
    assert ui(eng, "optpg") == b"2"
    W6.cmd(eng, "optpage", arg=1)                         # the last page stays
    assert ui(eng, "optpg") == b"2"
    W6.cmd(eng, "optpage", arg=-1)
    assert ui(eng, "optpg") == b"1"
    # another group, a search and the view opened again start at the first page
    W6.cmd(eng, "optgroup", arg=1)
    assert ui(eng, "optpg") == b"0" and rows_of(eng) == [(k, 0) for k in range(6, 12)]
    W6.cmd(eng, "optgroup", arg=3)
    W6.cmd(eng, "optpage", arg=1)
    W6.cmd(eng, "optfind", text=b"setting 1")
    assert ui(eng, "optpg") == b"0"
    W6.cmd(eng, "optcancel")
    W6.cmd(eng, "options")
    assert (ui(eng, "optpg"), ui(eng, "optgrp"), ui(eng, "optq")) == (b"0", b"0", b"")
    assert ui(eng, "ogr6") == b"B" and ui(eng, "ogr0") == b"A" and ui(eng, "optrows") == b"6"


def test_a_group_is_picked_from_the_list_and_a_search_goes_over_all_of_them():
    data = many_about([(b"", 2), (b"Match interface", 3), (b"Camera", 6)])
    eng = opened_on(data)
    assert groups_of(eng) == [(b"", 2), (b"Match interface", 3), (b"Camera", 6)]
    assert rows_of(eng) == [(0, 0), (1, 0)]               # the settings under no group
    W6.cmd(eng, "optgroup", arg=2)
    assert rows_of(eng) == [(k, 0) for k in range(5, 11)] and ui(eng, "optshown") == b"6"
    # an entry the list does not have is its last one, All settings
    for g in (7, -1):
        W6.cmd(eng, "optgroup", arg=g)
        assert ui(eng, "optgrp") == b"3" and ui(eng, "optshown") == b"11"
    # a value changed in one view is the same setting's in every other
    W6.cmd(eng, "optgroup", arg=2)
    button(eng, 7)
    W6.cmd(eng, "optfind", text=b"setting 7")
    assert rows_of(eng) == [(7, 1), (7, 0)] and ui(eng, "ov7") == b"0"
    # a group is found by its title too
    W6.cmd(eng, "optfind", text=b"CAMERA")
    assert rows_of(eng) == [(5, 1)] + [(k, 0) for k in range(5, 11)]
    # picking a group ends the search
    W6.cmd(eng, "optgroup", arg=1)
    assert ui(eng, "optq") == b"" and rows_of(eng) == [(2, 0), (3, 0), (4, 0)]
    # nothing found: no row, one page; Esc empties the search first and only
    # the next one leaves the view
    W6.cmd(eng, "optfind", text=b"zzz")
    assert (ui(eng, "optrows"), ui(eng, "optshown")) == (b"0", b"0")
    W6.cmd(eng, "optpage", arg=1)
    assert ui(eng, "optpg") == b"0"
    W6.cmd(eng, "esc", text=b"zzz")                       # it comes with the box's text
    assert ui(eng, "panel") == b"2" and ui(eng, "optq") == b""
    assert rows_of(eng) == [(2, 0), (3, 0), (4, 0)]
    # Enter in the search box searches, and the lists' own filter stays
    W6.cmd(eng, "enter", text=b"setting 1")
    assert ui(eng, "optq") == b"setting 1" and ui(eng, "filter") == b""
    assert [k for k, h in rows_of(eng) if h == 0] == [1, 10]
    # Accept stores what was changed, whatever the view shows
    W6.cmd(eng, "optacc")
    assert ui(eng, "msg") == b"Options saved: 1 changed." and setting(eng, b"qmtestwasd", b"s7") == b"0"
    W6.cmd(eng, "options")
    W6.cmd(eng, "esc")                                    # no search: Esc leaves at once
    assert ui(eng, "panel") == b"0"


GROUPED_ABOUT = (b"id = qmtestwasd\r\ngroup = Keys\r\nsetting = left;key;A;Camera left\r\n"
                 b"setting = right;key;D;Camera right\r\ngroup = Other\r\n"
                 b"setting = tag;text;qm;Tag;5\r\nsetting = smooth;bool;1;Smooth scrolling\r\n")


def test_a_new_view_ends_a_key_capture_and_a_text_edit_and_keeps_what_was_typed():
    eng = opened_on(GROUPED_ABOUT)
    button(eng, 0)
    assert ui(eng, "optcap") == b"0"
    W6.cmd(eng, "optgroup", arg=1)
    assert ui(eng, "optcap") == b"-1" and rows_of(eng) == [(2, 0), (3, 0)] and ui(eng, "msg") == b""
    button(eng, 2)
    assert ui(eng, "optsel") == b"2" and ui(eng, "typed") == b"qm"
    W6.cmd(eng, "filter", text=b"abc")
    assert ui(eng, "ov2") == b"abc"
    W6.cmd(eng, "optfind", text=b"smooth")
    assert ui(eng, "optsel") == b"-1" and ui(eng, "ov2") == b"abc"
    assert rows_of(eng) == [(3, 1), (3, 0)]
    # while a text setting is edited, Enter is the edit's and no search
    W6.cmd(eng, "optfind", text=b"")
    button(eng, 2)
    W6.cmd(eng, "enter", text=b"xy")
    assert ui(eng, "ov2") == b"xy" and ui(eng, "optq") == b"" and ui(eng, "optsel") == b"2"


def test_a_small_mod_without_groups_has_no_strip_and_takes_none_of_its_commands():
    eng = opened()
    assert (ui(eng, "optstrip"), ui(eng, "optper"), ui(eng, "ogn")) == (b"0", b"10", b"0")
    before = rows_of(eng)
    W6.cmd(eng, "optfind", text=b"camera")
    assert rows_of(eng) == before == [(k, 0) for k in range(7)] and ui(eng, "optq") == b""
    W6.cmd(eng, "optgroup", arg=3)
    assert rows_of(eng) == before and ui(eng, "optgrp") == b"0"
    # Enter with no search box and no text being edited does nothing, as before
    W6.cmd(eng, "enter", text=b"zoom")
    assert (ui(eng, "optq"), ui(eng, "filter"), ui(eng, "panel")) == (b"", b"", b"2")
    # eleven settings are more than a page: the search box, nine rows a page
    eng = opened_on(many_about([(b"", 11)]))
    assert (ui(eng, "optstrip"), ui(eng, "optper"), ui(eng, "ogn")) == (b"1", b"9", b"0")
    W6.cmd(eng, "optfind", text=b"setting 10")
    assert rows_of(eng) == [(10, 0)]


def test_a_setting_past_the_old_limit_is_stored_loaded_and_defaulted_like_the_rest():
    data = many_about([(b"", 40)]).replace(b"setting = s38;bool;1;", b"setting = s38;int;4;") \
        .replace(b"Setting 38\r\n", b"Setting 38;1..9\r\n")
    assert A.parse(data).problems == [] and len(A.parse(data).settings) == 40
    eng = opened_on(data)
    assert ui(eng, "optn") == b"40" and ui(eng, "abs0") == b"40"
    assert setting(eng, b"qmtestwasd", b"s39") == b"1" and setting(eng, b"qmtestwasd", b"s38") == b"4"
    button(eng, 33)                                       # Switch
    button(eng, 38)                                       # +
    button(eng, 39)
    button(eng, 39)                                       # off and on again: not a change
    assert (ui(eng, "ov33"), ui(eng, "ov38"), ui(eng, "ov39")) == (b"0", b"5", b"1")
    assert setting(eng, b"qmtestwasd", b"s33") == b"1"    # nothing is stored before Accept
    W6.cmd(eng, "optacc")
    assert ui(eng, "msg") == b"Options saved: 2 changed."
    assert setting(eng, b"qmtestwasd", b"s33") == b"0" and setting(eng, b"qmtestwasd", b"s38") == b"5"
    PAS5.load(eng, "qmTick", "qmRestart", "qmMarkerSave", "qmSetSave")
    PAS5.run(eng, "qmTick")
    keys, kids = eng.saved[SETTINGS]
    mine = dict(kids)[b"qmtestwasd"][0]
    # the file holds every setting under its id: the format did not change
    assert sorted(mine) == sorted(b"s%d" % k for k in range(40))
    assert (mine[b"s33"], mine[b"s38"], mine[b"s0"]) == (b"0", b"5", b"1")
    # the next start reads them back ...
    again = booted(files={WASD + b"\\about.cfg": data}, saved=eng.saved[SETTINGS])
    assert setting(again, b"qmtestwasd", b"s33") == b"0" and setting(again, b"qmtestwasd", b"s38") == b"5"
    W6.cmd(again, "select", arg=0)
    W6.cmd(again, "options")
    assert (ui(again, "ovs33"), ui(again, "ovs38"), ui(again, "ovs39")) == (b"0", b"5", b"1")
    # ... and a stored value that does not fit its declaration is the default
    bad = ({}, [(b"qmtestwasd", ({b"s38": b"77", b"s35": b"maybe", b"s33": b"0"}, []))])
    fixed = booted(files={WASD + b"\\about.cfg": data}, saved=bad)
    assert [setting(fixed, b"qmtestwasd", b"s%d" % k) for k in (33, 35, 38)] == [b"0", b"1", b"4"]


def test_a_thousand_settings_are_kept_edited_and_stored_by_their_own_numbers():
    # The keys of a setting end in its number: `ov1` + 23 must not be `ov12` + 3.
    data = many_about([(b"A", 400), (b"B", 600)])
    eng = opened_on(data)
    assert ui(eng, "optn") == b"1000" == ui(eng, "abs0")
    assert rows_of(eng) == twin_rows(data)
    assert (ui(eng, "oid999"), ui(eng, "ogr999"), ui(eng, "ogr399"), ui(eng, "ogr400")) == (
        b"s999", b"B", b"A", b"B")
    for k in (12, 123, 999):
        button(eng, k)
    off = {12, 123, 999}
    assert all(ui(eng, "ov%d" % k) == (b"0" if k in off else b"1") for k in range(1000))
    W6.cmd(eng, "optacc")
    assert ui(eng, "msg") == b"Options saved: 3 changed."
    assert all(setting(eng, b"qmtestwasd", b"s%d" % k) == (b"0" if k in off else b"1")
               for k in range(1000))
    # All settings: the last page is the hundred-and-somethingth, and Next
    # stays on it
    W6.cmd(eng, "select", arg=0)
    W6.cmd(eng, "options")
    W6.cmd(eng, "optgroup", arg=2)
    assert rows_of(eng) == twin_rows(data, 2) and ui(eng, "optper") == b"9"
    pages = (int(ui(eng, "optrows")) + 8) // 9
    for _ in range(pages + 3):
        W6.cmd(eng, "optpage", arg=1)
    assert int(ui(eng, "optpg")) == pages - 1 > 100
    # a search over a thousand
    W6.cmd(eng, "optfind", text=b"setting 99")
    assert [k for k, h in rows_of(eng) if h == 0 and k >= 0] == [99] + list(range(990, 1000))
    assert rows_of(eng) == twin_rows(data, 2, b"setting 99")
