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

import test_m5_pascal as PAS5
import test_m6_window as W6

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
