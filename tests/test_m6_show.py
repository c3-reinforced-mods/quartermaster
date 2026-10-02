"""ShowQmManager, run offline: the GUI state that draws the manager window
from qm_ui, on the script interpreter of tests/test_m3_pascal.py over an
emulated element tree (parents found by name, texts, buttons, list boxes and
their items, visibility, the enabled flag). The controller and the event
state are stood in by recorders.

The state decides nothing (docs/ui.md); what it must get right is that what
it draws says what qm_ui says: every Installed and Active row with its mark
and status word, the buttons enabled exactly when they would do something,
the message line's priority (clash, about.cfg rule, pending changes), the
Report, Options and Mod files views, the four dialogs (confirm, restart
notice, guard notice, New mod) and the fallbacks that open the Workshop page
when the controller cannot answer. How it looks is judged in game.
"""
import pytest

import test_m3_pascal as PAS
import test_m5_pascal as PAS5

PAS.BYREF_NATIVES["_misc_getguishoweventstatenames"] = (1, 2, 3)
PAS.BYREF_NATIVES["_gui_converthextotcolor"] = (1,)
PAS.BYREF_NATIVES["_gui_setuptcolorinteger"] = (5,)
PAS.BYREF_NATIVES["getguielementfonttextrect"] = (2, 3)
PAS.BYREF_NATIVES["getguielementfonttextformatrect"] = (2, 3)

TOP = 1
CHAR_W, LINE_H = 8, 17          # the emulated font: every byte 8 wide, a line 17 high
#: The vanilla constants the state names, as recognisable values.
CONST = {"gc_font_color_green": b"<g>", "gc_font_color_red": b"<r>",
         "gc_font_color_orange": b"<o>", "gc_font_color_white": b"<w>",
         "gc_font_color_lightgrey": b"<l>", "gc_font_color_default": b"<d>",
         "gc_gui_breakline": b"<br>", "gc_font_hex_color_red": b"FF0000",
         "gc_font_hex_color_orange": b"FFA500", "gc_gui_material_black": b"black",
         "gc_gui_charfilter_default": 0, "gc_gui_event_tagclose": 8003,
         "gc_font_serif_12": 12, "gc_font_serif_13": 13, "gc_font_serif_15": 15,
         "gc_font_serif_16": 16}
for _k in ("hal", "val"):
    for _w in ("left", "right", "top", "middle", "bottom", "parentleft", "parenttop",
               "parentmiddle", "parentrightwidth", "parentbottomheight"):
        CONST["gc_%s%s" % (_k, _w)] = 0
G, R, O, W, L, D, BR = (CONST[k] for k in (
    "gc_font_color_green", "gc_font_color_red", "gc_font_color_orange", "gc_font_color_white",
    "gc_font_color_lightgrey", "gc_font_color_default", "gc_gui_breakline"))
TAB = b"\t"


class El(object):
    def __init__(self, handle, kind, name, parent, text=b"", tag=None, w=0, h=0):
        self.handle, self.kind, self.name, self.parent = handle, kind, name, parent
        self.text, self.tag, self.w, self.h = text, tag, w, h
        self.children, self.items = [], []
        self.visible, self.enabled, self.sel, self.top, self.color = True, True, None, 0, None


class Screen(PAS5.Engine):
    """An element tree the state builds; each element knows its parent."""

    def __init__(self):
        PAS5.Engine.__init__(self)
        self.els = {TOP: El(TOP, "top", b"", 0)}
        self.urls, self.did = [], []
        for name, value in CONST.items():
            self.natives[name] = (lambda v: (lambda: v))(value)

    # the tree
    def _add(self, kind, name, parent, **kw):
        parent = parent or TOP
        p = self.els[parent]
        old = next((c for c in p.children if self.els[c].name == name), None)
        if old is not None:
            self._drop_children(old)
            p.children.remove(old)
            del self.els[old]
        self.handle += 1
        e = El(self.handle, kind, name, parent, **kw)
        self.els[e.handle] = e
        p.children.append(e.handle)
        return e.handle

    def _drop_children(self, h):
        for c in list(self.els[h].children):
            self._drop_children(c)
            del self.els[c]
        self.els[h].children = []

    def find(self, path, root=TOP):
        """The element at the dotted path of names under `root`, or None."""
        h = root
        for part in path.split(b"."):
            h = next((c for c in self.els[h].children if self.els[c].name == part), None)
            if h is None:
                return None
        return self.els[h]

    def under(self, root, kind=None):
        """Every element under `root`, depth first."""
        out = []
        for c in self.els[root].children:
            if kind is None or self.els[c].kind == kind:
                out.append(self.els[c])
            out += self.under(c, kind)
        return out

    def n__misc_GetGUIShowEventStateNames(self, state, elm, show, event):
        elm.v, show.v, event.v = b"QmManager", b"ShowQmManager", b"EventQmManager"

    def n__gui_GetTop(self):
        return TOP

    def n__gui_CreateParent(self, name, parent, hal, val, x, y, w, h, update):
        parent = parent or TOP
        p = self.els[parent]
        old = next((c for c in p.children if self.els[c].name == name), None)
        if old is not None:
            if not update:
                self._drop_children(old)
            return old
        return self._add("parent", name, parent, w=w, h=h)

    def n_GetGUIElementIndexByNameParent(self, path, parent):
        e = self.find(path, parent or TOP)
        return e.handle if e is not None else 0

    def n_GetGUIElementVisible(self, h):
        return self.els[h].visible

    def n_SetGUIElementVisible(self, h, v):
        self.els[h].visible = v

    def n_SetGUIElementEnabled(self, h, v):
        self.els[h].enabled = v

    def n_GetGUIElementChildrenCount(self, h):
        return len(self.els[h].children)

    def n_GetGUIElementChildrenByIndex(self, h, k):
        return self.els[h].children[k]

    def n_GetGUIElementNameByIndex(self, h):
        return self.els[h].name

    def n_GetGUIElementWidth(self, h):
        return self.els[h].w

    def n_GetGUIElementHeight(self, h):
        return self.els[h].h

    def n_SetGUIElementHeight(self, h, v):
        self.els[h].h = v

    def n_GetViewerWidth(self):
        return 1920

    def n_GetViewerHeight(self):
        return 1080

    def n__gui_AbsScaleByDPI(self, h):
        return 1.0

    def n_Round(self, f):
        return int(round(f))

    def n_Max(self, a, b):
        return max(a, b)

    def n_Min(self, a, b):
        return min(a, b)

    def n_GetGUITextureHeight(self, name):
        return 30

    # elements the state makes
    def n__gui_CreateImageActive(self, name, parent, material, hal, val, x, y, w, h, tag, event,
                                 hint, update):
        return self._add("image", name, parent, tag=tag, w=w, h=h)

    def n__gui_CreateMainWindow(self, name, parent, hal, val, x, y, w, h, skin, update):
        h_ = self._add("window", name, parent, w=w, h=h)
        head = self._add("image", b"head", h_)
        self._add("image", b"head", head)
        return h_

    def n__gui_CreateSkinWindow(self, name, parent, hal, val, x, y, w, h, skin, update):
        return self._add("skin", name, parent, w=w, h=h)

    def n__gui_CreateSkinHeadWindow(self, name, parent, hal, val, x, y, w, update):
        return self._add("head", name, parent, w=w, h=30)

    def n__gui_CreateScrollLayer(self, name, parent, hal, val, x, y, w, h, *rest):
        return self._add("layer", name, parent, w=self.els[parent].w, h=h)

    def n__gui_CreateButton(self, name, parent, texture, hal, val, x, y, w, h, event, hint, tag,
                            update):
        return self._add("button", name, parent, tag=tag)

    def n__gui_CreateText(self, name, parent, text, hal, val, x, y, w, h, thal, tval, font,
                          color, update):
        h_ = self._add("text", name, parent, text=text, w=w, h=h)
        self.els[h_].color = color
        return h_

    def n__gui_CreateInputBox(self, name, parent, text, *rest):
        return self._add("input", name, parent, text=text)

    def n__gui_CreateListBox(self, name, parent, *rest):
        return self._add("list", name, parent)

    def n_GUIListBoxClearSilent(self, h):
        self.els[h].items = []

    def n_GUIListBoxAddItem(self, h, text, tag):
        self.els[h].items.append((text, tag))

    def n_SetGUIListBoxItemIndexSilent(self, h, row):
        self.els[h].sel = row

    def n_SetGUIListBoxTopIndex(self, h, top):
        self.els[h].top = top

    def n__gui_SetListBoxHeight(self, h, rows):
        return len(self.els[h].items) > rows

    def n_GetGUIListBoxTabsCount(self, h):
        return 0

    # fonts and colours
    def n_qmxuiconstfont(self):
        return PAS.Arr(0, [1000 + k for k in range(32)])

    def n_GetGUIElementFontTextRect(self, font, text, w, h):
        lines = text.split(BR)
        w.v, h.v = CHAR_W * max(len(l) for l in lines), LINE_H * len(lines)

    def n_GetGUIElementFontTextFormatRect(self, font, text, w, h):
        self.n_GetGUIElementFontTextRect(font, text, w, h)

    def n_GetGUIElementFontHeight(self, font):
        return LINE_H

    def n_GetGUIWrappedTextByFont(self, font, text, width):
        return text

    def n__gui_SetupTColorInteger(self, r, g, b, a, f, color):
        color.v = (r, g, b)

    def n__gui_ConvertHexToTColor(self, hexcode, color):
        color.v = hexcode

    # what the state asks of the rest of the game
    def n_OpenURL(self, url):
        self.urls.append(url)

    def n_ExecuteState(self, s):
        self.did.append(("execute", s))
        if getattr(self, "answer", True):
            self.n_ParserSetIntValueByKeyByHandle(self.named[b"qm_ui"], b"pong", 1)


# Natives the state calls only for their effect on the screen.
for _name in ("SetGUIElementUserBlend", "SetGUIElementPressState", "SetGUIElementCursorByIndex",
              "SetGUIAllowEvents", "SetGUIEventStateOnKeyDown", "_gui_AddScroller",
              "_gui_UpdateListBoxScrollerPos", "_gui_InputBoxSetupStrCharFilter",
              "DeleteGUIListBoxTab", "AddGUIListBoxTabProperty"):
    setattr(Screen, "n_" + _name, lambda self, *a: None)


def put(eng, parser, keys):
    """Set `keys` in the named parser (eng.set cannot take the key `self`)."""
    h = eng.named.get(parser) or eng.n_ParserCreate(parser)
    for k, v in keys.items():
        eng.n_ParserSetValueByKeyByHandle(h, k.encode(), v if isinstance(v, bytes) else b"%d" % v)
    return h


def show(ui, rt=None, report=None, answer=True, takes_open=True):
    """ShowQmManager over qm_ui = `ui` (and qm_rt, qm_report); the event state
    answers the ping unless `answer` is False, the controller takes `open`
    (clears cmd) unless `takes_open` is False."""
    eng = Screen()
    code = [l.replace(b"gUIConst.font[", b"qmxuiconstfont[")
            for l in PAS5.sources()["showqmmanager"]]
    eng.states["showqmmanager"] = PAS.State(code, eng)
    for name, keys in ((b"qm_ui", ui), (b"qm_rt", rt), (b"qm_report", report)):
        if keys is not None:
            put(eng, name, keys)
    eng.answer = answer

    def act():
        if takes_open:
            eng.n_ParserSetValueByKeyByHandle(eng.named[b"qm_ui"], b"cmd", b"")
    eng.states["qmuiact"] = PAS5.Fake(act)
    eng.states["showqmmanager"].run()
    return eng


def win(eng, path):
    return eng.find(b"QmManager." + path)


def buttons(eng, root=b"main.wnd"):
    """{name: (caption, enabled)} of the buttons under `root`."""
    out = {}
    for b in eng.under(win(eng, root).handle, "button"):
        cap = next((t.text for t in eng.under(b.handle, "text")), None)
        out[b.name] = (cap, b.enabled)
    return out


def model(rows, sel=-1, side=0, self_=-1, **kw):
    """qm_ui for `rows` = [dict(name, dir, org, st, en, pe, tck)] in mods.ini
    order; `ord` (default: the rows' own order) the pending load order."""
    ui = {"n": len(rows), "sel": sel, "side": side, "self": self_, "mode": 0, "panel": 0}
    for k, i in enumerate(kw.pop("ord", range(len(rows)))):
        ui["ord%d" % k] = i
    for i, r in enumerate(rows):
        for key in ("name", "dir", "org", "st", "tck"):
            if key in r:
                ui["%s%d" % (key, i)] = r[key]
        ui["en%d" % i] = r.get("en", 1)
        ui["pe%d" % i] = r.get("pe", r.get("en", 1))
        ui["abs%d" % i] = r.get("abs", 0)
    ui.update(kw)
    return ui


ROWS = [dict(name=b"MGraphics - Lights", dir=b"..\\w\\1", org=b"Workshop", st=b"OK"),
        dict(name=b"ZoomOut!", dir=b"..\\w\\2", org=b"Workshop", st=b"WARN", en=0, pe=1,
             tck=b"OK"),
        dict(name=b"Broken", dir=b"mods\\QMTestBroken", org=b"Local", st=b"FAIL", en=1, pe=0),
        dict(name=b"Fresh", dir=b"mods\\Fresh", org=b"Local", st=b"NEW"),
        dict(name=b"Off", dir=b"mods\\Off", org=b"Local", st=b"-", en=0, pe=0),
        dict(name=b"Quartermaster", dir=b"mods\\Quartermaster", org=b"Quartermaster",
             st=b"OK")]


def installed_item(r):
    en, pe = r.get("en", 1), r.get("pe", r.get("en", 1))
    mark = G + b"+" if pe > en else (R + b"-" if pe < en else b"")
    st = r["st"]
    st = {b"OK": G, b"WARN": O, b"?": O, b"FAIL": R, b"NEW": W}.get(st, L) + st
    if mark:
        st = L + b"PENDING"
    if pe > en and r.get("tck") in (b"OK", b"WARN"):
        st = (G if r["tck"] == b"OK" else O) + r["tck"]
    return TAB + mark + D + TAB + r["name"] + TAB + r["org"] + TAB + st + D


def active_item(row, r):
    st = r["st"]
    mark = b""
    if r.get("en", 1) == 0:
        mark, st = G + b"+", L + b"PENDING"
        if r.get("tck") in (b"OK", b"WARN"):
            st = (G if r["tck"] == b"OK" else O) + r["tck"]
    else:
        st = {b"OK": G, b"WARN": O, b"?": O, b"FAIL": R, b"NEW": W}.get(st, L) + st
    return TAB + b"%d" % (row + 1) + TAB + mark + D + TAB + r["name"] + TAB + st + D


# ----------------------------------------------------------------- browse
def test_the_lists_show_every_row_with_its_mark_and_status():
    order = [5, 0, 1, 3, 2, 4]          # the pending load order; Quartermaster first here
    eng = show(model(ROWS, ord=order))
    inst = win(eng, b"main.wnd.inst.installed")
    assert inst.items == [(installed_item(r), i) for i, r in enumerate(ROWS)]
    act = win(eng, b"main.wnd.act.active")
    want, row = [], 0
    for i in order:
        if ROWS[i].get("pe", ROWS[i].get("en", 1)) == 1:
            want.append((active_item(row, ROWS[i]), i))
            row += 1
    assert act.items == want
    assert eng.log[-1].startswith(b"[qm] ui show fresh=True rows=6 active=4 shown=6 ")
    assert eng.log[-1].endswith(b" windows=1")
    assert eng.urls == [] and ("execute", b"EventQmManager") in eng.did


def test_a_pending_deactivation_says_pending_and_an_activation_the_checks_word():
    eng = show(model(ROWS))
    items = dict((tag, text) for text, tag in win(eng, b"main.wnd.inst.installed").items)
    assert items[2].endswith(TAB + L + b"PENDING" + D)          # Broken, Apply turns it off
    assert items[1].endswith(TAB + G + b"OK" + D)               # ZoomOut!, checked OK
    rows = [dict(r) for r in ROWS]
    rows[1]["tck"] = b"WARN"
    eng = show(model(rows))
    assert dict((t, x) for x, t in win(eng, b"main.wnd.act.active").items)[1].endswith(
        TAB + O + b"WARN" + D)
    rows[1]["tck"] = b""
    eng = show(model(rows))
    assert dict((t, x) for x, t in win(eng, b"main.wnd.act.active").items)[1].endswith(
        TAB + L + b"PENDING" + D)


def test_the_filter_keeps_the_rows_whose_name_or_dir_holds_it():
    eng = show(model(ROWS, filter=b"MODS\\q", typed=b"MODS\\q"))
    assert [t for _x, t in win(eng, b"main.wnd.inst.installed").items] == [2, 5]
    assert win(eng, b"fbox.filter").text == b"MODS\\q"
    assert b" shown=2 " in eng.log[-1]


def test_a_long_name_is_cut_to_its_column():
    rows = [dict(name=b"Cannons Attack Automatically", dir=b"..\\w\\9", org=b"Workshop",
                 st=b"OK")]
    eng = show(model(rows))
    # 172 wide at 8 per byte: 18 bytes and `...`.
    assert win(eng, b"main.wnd.inst.installed").items[0][0].split(TAB)[2] == \
        b"Cannons Attack Aut..."
    # the Active column is 222 wide: 24 bytes and `...`
    assert win(eng, b"main.wnd.act.active").items[0][0].split(TAB)[3] == \
        b"Cannons Attack Automatic..."


@pytest.mark.parametrize("sel, side, want", [
    (-1, 0, dict(bact=False, bdeact=False, bup=False, bdown=False, bopt=False, bmodfiles=False)),
    (4, 0, dict(bact=True, bdeact=False, bup=False, bdown=False, bmodfiles=True)),
    (0, 1, dict(bact=False, bdeact=True, bup=False, bdown=True, bmodfiles=False)),
    (3, 1, dict(bact=False, bdeact=True, bup=True, bdown=False, bmodfiles=True)),
    (5, 1, dict(bact=False, bdeact=False, bup=False, bdown=False)),
    (1, 1, dict(bact=False, bdeact=True, bup=True, bdown=True, bopt=True)),
])
def test_the_move_buttons_are_enabled_only_when_they_would_do_something(sel, side, want):
    rows = [dict(r) for r in ROWS]
    rows[1]["abs"] = 2
    eng = show(model(rows, sel=sel, side=side, self_=5, abok=1, hascanon=1))
    got = buttons(eng)
    for name, enabled in want.items():
        assert got[name.encode()][1] is enabled, (name, got[name.encode()])
    assert got[b"bsort"] == (b"Auto-sort", True)
    assert got[b"bnewmod"] == (b"New mod", True)
    lst = win(eng, b"main.wnd.act.active" if side else b"main.wnd.inst.installed")
    assert lst.sel == (None if sel < 0 else [t for _x, t in lst.items].index(sel))


def test_down_without_quartermaster_may_reach_the_last_row():
    rows = ROWS[:4]
    eng = show(model(rows, sel=1, side=1, self_=-1))
    assert buttons(eng)[b"bdown"][1] is True
    eng = show(model(rows, sel=3, side=1, self_=-1))
    assert buttons(eng)[b"bdown"][1] is False


@pytest.mark.parametrize("extra, text, hexcode", [
    (dict(msg=b"Done."), b"Done.", None),
    (dict(pcn=2, pc0=b"A and B both ship lib\\unit.script"),
     b"Clash: A and B both ship lib\\unit.script - the game may not start with both. "
     b"Deactivate one of them. (1 more)", b"FF0000"),
    (dict(pan=2, pa0=b"A needs B", pat0=b"WARN", pa1=b"C rules out D", pat1=b"FAIL"),
     b"C rules out D. (1 more)", b"FF0000"),
    (dict(pan=1, pa0=b"A loads after B", pat0=b"WARN"), b"A loads after B.", b"FFA500"),
    (dict(canapply=1, chg=2, ordchg=1),
     b"Pending changes: 2 mod(s), load order 1. Apply writes them and restarts the game.", None),
    (dict(), b"", None),
])
def test_the_message_line_says_the_most_urgent_thing(extra, text, hexcode):
    eng = show(model(ROWS, **extra))
    msg = win(eng, b"main.wnd.tmsg")
    assert msg.text == text
    assert msg.color == (hexcode if hexcode else (255, 220, 170))
    assert buttons(eng)[b"bapply"] == (b"Apply", extra.get("canapply") == 1)


def test_the_details_panel_shows_its_lines():
    eng = show(model(ROWS, sel=0, dn=2, d0=b"MGraphics - Lights, Workshop", d1=b"Loads 3rd"))
    texts = [t.text for t in eng.under(win(eng, b"main.wnd.descr").handle, "text")]
    assert b"MGraphics - Lights, Workshop" + BR + b"Loads 3rd" in texts


def test_drawing_again_rebuilds_the_window_in_place():
    eng = show(model(ROWS))
    eng.states["showqmmanager"].run()
    assert eng.log[-1].startswith(b"[qm] ui show fresh=False ")
    assert eng.log[-1].endswith(b" windows=1")
    assert len(eng.under(TOP, "list")) == 2


# ------------------------------------------------------------------ views
def test_the_report_view_lists_the_report_by_mod():
    eng = show(model(ROWS, panel=1))
    texts = [t.text for t in eng.under(win(eng, b"main.wnd.rep").handle, "text")]
    assert b"No report yet: Quartermaster has not generated anything in this installation." in texts
    assert buttons(eng)[b"breport"] == (b"Back", True)
    eng = show(model(ROWS, panel=1),
               report=dict(mlines=2, m0=b"1. MGraphics - Lights: OK", m1=b"2. ZoomOut!: WARN"))
    texts = [t.text for t in eng.under(win(eng, b"main.wnd.rep").handle, "text")]
    assert b"1. MGraphics - Lights: OK" + BR + b"2. ZoomOut!: WARN" in texts
    assert win(eng, b"fbox").visible is False


def test_the_options_view_draws_each_setting_by_its_type():
    ui = model(ROWS, panel=2, opt=1, optn=12, optpg=0, optcap=3, optsel=4)
    kinds = [b"bool", b"int", b"float", b"key", b"text", b"choice", b"bool", b"int", b"int",
             b"int", b"int", b"int"]
    for k, t in enumerate(kinds):
        ui.update({"oty%d" % k: t, "olb%d" % k: b"Setting %d" % k, "ov%d" % k: b"1",
                   "ovs%d" % k: b"1"})
    ui.update({"ov0": b"0", "ovs0": b"1", "osc1": b"host", "typed": b"abc", "ov4": b"",
               "olb2": b"Camera speed when the mouse wheel scrolls", "osc2": b"host"})
    eng = show(ui)
    opts = win(eng, b"main.wnd.opts")
    texts = dict((t.name, t.text) for t in eng.under(opts.handle, "text") if t.name != b"txtbtn")
    assert texts[b"olb0"] == b"Setting 0"
    assert texts[b"oval0"] == G + b"Off" + D                     # differs from the stored one
    assert texts[b"olb1"] == b"Setting 1 (the host decides in multiplayer)"
    # 410 wide at 8 per byte: 48 bytes and `...`
    assert texts[b"olb2"] == (b"Camera speed when the mouse wheel scrolls (the host decides "
                              b"in multiplayer)")[:48] + b"..."
    assert texts[b"oval3"] == b"press a key..."
    assert b"oval4" not in texts                                # the text box is drawn instead
    assert win(eng, b"obox.otext").text == b"abc" and win(eng, b"obox").visible
    assert texts[b"oval6"] == b"On"
    bs = buttons(eng, b"main.wnd.opts")
    assert bs[b"ob10"] == (b"Switch", True)
    assert bs[b"ob21"] == (b"-", True) and bs[b"ob11"] == (b"+", True)
    assert bs[b"ob13"] == (b"Change", False)                    # it waits for the key
    assert bs[b"ob14"] == (b"Edit", False)
    assert bs[b"ob25"] == (b"<", True) and bs[b"ob15"] == (b">", True)
    assert b"ob110" not in bs                                   # page 2 holds the rest
    head = next(t for t in eng.under(opts.handle, "text") if t.name == b"thead")
    assert head.text == b"Options: ZoomOut! (page 1 of 2)"
    page = buttons(eng)
    assert page[b"bprev"] == (b"Previous", False) and page[b"bnext"] == (b"Next", True)
    assert page[b"boacc"] == (b"Accept", True) and b"bapply" not in page


def test_the_mod_files_view_lists_the_game_files_and_how_they_are_treated():
    ui = model(ROWS, panel=3, mfrow=3, vn=2, vsel=1, mfhas=0, typed=b"onc",
               v0=b"gui\\menu.inc\\oncamera.inc", vc0=b"merge",
               v1=b"game\\var\\units.cfg", vc1=b"wta")
    eng = show(ui)
    lst = win(eng, b"main.wnd.vbox.vfiles")
    assert lst.items == [(TAB + b"gui\\menu.inc\\oncamera.inc" + TAB + b"merged with other mods", 0),
                         (TAB + b"game\\var\\units.cfg" + TAB +
                          b"not merged - the last mod's copy is used", 1)]
    assert lst.sel == 1
    bs = buttons(eng)
    assert bs[b"bmfabout"] == (b"Create about.cfg", True)
    assert bs[b"bmfcopy"] == (b"Copy into mod", True) and bs[b"bmfback"] == (b"Back", True)
    head = next(t for t in eng.under(win(eng, b"main.wnd.vbox").handle, "text"))
    assert head.text.startswith(b"Game files of mods\\Fresh ")
    eng = show(dict(ui, vsel=-1, mfhas=1))
    bs = buttons(eng)
    assert bs[b"bmfabout"][1] is False and bs[b"bmfcopy"][1] is False


# ---------------------------------------------------------------- dialogs
def test_the_confirm_dialog_lists_the_changes_and_the_load_order():
    ui = model(ROWS, mode=1, confn=2, conf0=b"+ ZoomOut!", conf1=b"- Broken", confon=3,
               confo0=b"1. MGraphics - Lights", confo1=b"2. ZoomOut!", confo2=b"3. Quartermaster",
               confordchg=1)
    eng = show(ui)
    texts = dict((t.name, t.text) for t in eng.under(win(eng, b"confirm.cwnd").handle, "text"))
    assert texts[b"ctext"] == b"Apply these changes and restart the game?"
    assert texts[b"clist"] == b"+ ZoomOut!" + BR + b"- Broken"
    assert texts[b"colist"] == b"1. MGraphics - Lights" + BR + b"2. ZoomOut!" + BR + \
        b"3. Quartermaster"
    assert texts[b"cohead"] == b"Load order (changed):"
    assert texts[b"cnote"] == b"Enter confirms, Esc cancels."
    assert buttons(eng, b"confirm")[b"byes"] == (b"Apply", True)
    assert win(eng, b"confirm").visible and not win(eng, b"notice").visible


@pytest.mark.parametrize("rule, head, note", [
    (0, b"These mods cannot be active together",
     b"Both mods of each pair replace the same core script."),
    (1, b"This set of mods cannot be applied",
     b"Their about.cfg rules, or core scripts both of them replace, rule it out:")])
def test_a_blocked_set_explains_itself_and_cannot_be_applied(rule, head, note):
    ui = model(ROWS, mode=1, confn=0, confon=0, confblk=1, confb0=b"A and B: lib\\unit.script",
               confbrule=rule)
    eng = show(ui)
    texts = dict((t.name, t.text) for t in eng.under(win(eng, b"confirm.cwnd").handle, "text"))
    assert texts[b"ctext"] == head
    assert texts[b"cblk"].startswith(R + note)
    assert texts[b"cblk"].endswith(BR + R + b"A and B: lib\\unit.script")
    assert texts[b"clist"] == b"no mod switched on or off" and texts[b"cohead"] == b"Load order:"
    assert texts[b"cnote"] == b"Esc goes back; deactivate one mod of each pair first."
    assert buttons(eng, b"confirm")[b"byes"] == (b"Apply", False)


def test_the_restart_notice_stands_alone_while_its_restart_is_live():
    eng = show(model(ROWS, mode=2, msg=b"Quartermaster switched 2 mods."), rt=dict(uiapply=1))
    texts = dict((t.name, t.text) for t in eng.under(win(eng, b"notice.nwnd").handle, "text"))
    assert texts[b"ntext"] == b"Restarting the game"
    assert texts[b"nnote"].startswith(b"Quartermaster switched 2 mods." + BR + b"The game closes")
    assert win(eng, b"main").visible is False and buttons(eng, b"notice") == {}
    assert eng.log[-1] == b"[qm] ui show restart notice"
    assert ("execute", b"EventQmManager") not in eng.did       # no `open` before it
    eng = show(model(ROWS, mode=2), rt=dict(rs=2))
    assert next(t.text for t in eng.under(win(eng, b"notice.nwnd").handle, "text")
                if t.name == b"nnote").startswith(b"Quartermaster has written the new files.")


def test_a_stale_restart_notice_goes_back_to_browsing():
    eng = show(model(ROWS, mode=2), rt=dict(uiapply=0, rs=0))
    assert b"[qm] ui show: the restart notice is stale; back to browsing" in eng.log
    assert eng.key(b"qm_ui", b"mode") == b"0" and win(eng, b"main").visible


def test_the_guard_notice_lists_the_mods_it_switched_off():
    eng = show(model(ROWS, mode=3, gdln=2, gdl0=b"Cannons (lib\\unit.script, State vs Country)",
                     gdl1=b"Other (dmscript.global, Patrol)"))
    texts = dict((t.name, t.text) for t in eng.under(win(eng, b"gnotice.gwnd").handle, "text"))
    assert texts[b"gtext"] == b"Quartermaster switched off new mods"
    assert texts[b"glist"] == b"Cannons (lib\\unit.script, State vs Country)" + BR + \
        b"Other (dmscript.global, Patrol)"
    assert buttons(eng, b"gnotice")[b"bok"] == (b"OK", True)
    assert win(eng, b"gnotice").visible


@pytest.mark.parametrize("folder, typ, excl, slot", [
    (b"BetterCavalry", 0, 0, b"Slot: none"), (b"", 1, 3, b"Slot: ui")])
def test_the_new_mod_dialog_shows_the_folder_type_and_slot(folder, typ, excl, slot):
    eng = show(model(ROWS, mode=4, nmname=b"Better Cavalry", nmfolder=folder, nmtype=typ,
                     nmexcl=excl))
    texts = dict((t.name, t.text) for t in eng.under(win(eng, b"newmod.nwnd").handle, "text")
                 if t.name != b"txtbtn")
    assert texts[b"nfolder"] == b"Folder: mods\\" + folder
    assert win(eng, b"nbox.nname").text == b"Better Cavalry"
    bs = buttons(eng, b"newmod")
    assert bs[b"bnmtype"][0] == (b"Type: total conversion" if typ else b"Type: mod")
    assert bs[b"bnmslot"][0] == slot
    assert bs[b"bnmcreate"] == (b"Create", folder != b"")
    assert win(eng, b"newmod").visible and win(eng, b"fbox").visible is False


# -------------------------------------------------------------- fallbacks
def test_without_the_controller_the_button_opens_the_workshop_page():
    eng = show(None)
    assert eng.urls == [b"http://steamcommunity.com/app/333420/workshop/"]
    assert eng.log[-1].startswith(b"[qm] ui show: the controller is not loaded")


def test_an_event_state_that_does_not_answer_opens_the_workshop_page():
    eng = show(model(ROWS), answer=False)
    assert eng.urls == [b"http://steamcommunity.com/app/333420/workshop/"]
    assert eng.log[-1] == b"[qm] ui show: EventQmManager did not answer; opening the Workshop " \
        b"page instead"
    assert eng.key(b"qm_ui", b"ping") == b"0"


def test_a_controller_that_does_not_take_open_opens_the_workshop_page():
    eng = show(model(ROWS), takes_open=False)           # ran, but left `open` there
    assert eng.log[-1] == b"[qm] ui show: the controller qmUiAct did not run; opening the " \
        b"Workshop page instead"
    assert eng.urls == [b"http://steamcommunity.com/app/333420/workshop/"]
    assert eng.key(b"qm_ui", b"cmd") == b""


# -------------------------------------------------------- adding the screens
GUISM = 77
MAINMENU = 1
UI_DIR = PAS5.QM + b"\\data\\quartermaster\\ui\\"


class Machine(PAS5.Engine):
    """The GUI state machine as qmUiEnsure sees it: states by name, their code
    lines, and the engine's ERROR line for every lookup of a missing name
    (TXStateMachine.IndexOfState, capability probe 10)."""

    def __init__(self, files):
        PAS5.Engine.__init__(self, files)
        self.machine = {}                       # name -> code lines
        self.gamemode = MAINMENU

    def n_qmxgintgamemode(self):
        return self.gamemode

    def n_gc_gamemode_mainmenu(self):
        return MAINMENU

    def n_StateMachineGetGUISMHandle(self):
        return GUISM

    def n_StateMachineGetStateIndByName(self, sm, name):
        names = list(self.machine)
        if name not in names:
            self.log.append(b"ERROR| 9 |error (): TXStateMachine.IndexOfState(" + name + b")")
            return -1
        return 140 + names.index(name)

    def n_StateMachineGetStateNameByInd(self, sm, ind):
        return list(self.machine)[ind - 140]

    def n_SameText(self, a, b):
        return a.lower() == b.lower()

    def n_StateMachineStateAdd(self, sm, name):
        assert sm == GUISM and name not in self.machine, "added twice: %s" % name
        self.machine[name] = []

    def n_StateMachineStateAddCodeLine(self, sm, name, line):
        self.machine[name].append(line)


def screen_files(base=UI_DIR, without=()):
    """The two .inc files the build ships, from the states it emits."""
    import hbuild as H
    out = {}
    for name, fn in ((b"ShowQmManager", b"showqmmanager.inc"),
                     (b"EventQmManager", b"eventqmmanager.inc")):
        if name not in without:
            out[base + fn] = H.assemble_inc(name, PAS5.sources()[name.decode().lower()])
    return out


def ensure(eng, qmdir=PAS5.QM):
    """One DoCreate's qmUiEnsure (the record field made a name: gamemode)."""
    code = [l.replace(b"gInterface.gamemode", b"qmxgintgamemode")
            for l in PAS5.sources()["qmuiensure"]]
    eng.states["qmuiensure"] = PAS.State(code, eng)
    if qmdir is not None:
        eng.set("qm_rt", qmdir=qmdir)
    eng.states["qmuiensure"].run()


def test_the_first_main_menu_adds_both_screens_with_their_code():
    eng = Machine(screen_files())
    ensure(eng)
    for name in (b"ShowQmManager", b"EventQmManager"):
        want = [l.rstrip(b" ") for l in PAS5.sources()[name.decode().lower()]]
        assert eng.machine[name] == want
    assert (eng.key(b"qm_ui", b"ready"), eng.key(b"qm_ui", b"adds")) == (b"1", b"1")
    assert eng.log[-1] == b"[qm] ui ensure: ready=1 adds=1 from " + UI_DIR
    assert not [l for l in eng.log if l.startswith(b"ERROR")]       # no lookup at all
    # The next DoCreate in the menu: one lookup of a present name, silent.
    ensure(eng)
    assert eng.log[-1] == b"[qm] ui ensure: screens present checks=1 adds=1"
    assert not [l for l in eng.log if l.startswith(b"ERROR")]


def test_a_map_load_drops_the_screens_and_they_come_back_after_one_error_line():
    eng = Machine(screen_files())
    ensure(eng)
    eng.machine = {}                     # a battle reloaded the GUI machine from menu.aix
    eng.gamemode = 2
    n = len(eng.log)
    ensure(eng)                          # the battle's own DoCreate: nothing at all
    assert len(eng.log) == n and eng.machine == {}
    eng.gamemode = MAINMENU
    ensure(eng)
    assert [l for l in eng.log if l.startswith(b"ERROR")] == [
        b"ERROR| 9 |error (): TXStateMachine.IndexOfState(ShowQmManager)"]
    assert b"[qm] ui ensure: screens gone (a map load reloaded the GUI machine); adding them " \
        b"again" in eng.log
    assert set(eng.machine) == {b"ShowQmManager", b"EventQmManager"}
    assert eng.key(b"qm_ui", b"adds") == b"2" and eng.key(b"qm_ui", b"checks") == b"1"


def test_a_screen_without_its_file_is_added_once_its_file_is_there():
    files = screen_files(without=(b"EventQmManager",))
    eng = Machine(files)
    ensure(eng)
    assert list(eng.machine) == [b"ShowQmManager"] and eng.key(b"qm_ui", b"ready") != b"1"
    assert eng.key(b"qm_ui", b"show") == b"1"
    assert (b"[qm] ui ensure: no code lines in " + UI_DIR + b"eventqmmanager.inc; "
            b"EventQmManager not added") in eng.log
    eng.fs.update(screen_files(without=(b"ShowQmManager",)))
    ensure(eng)                          # ShowQmManager is not added a second time
    assert list(eng.machine) == [b"ShowQmManager", b"EventQmManager"]
    assert eng.key(b"qm_ui", b"ready") == b"1"


def test_without_its_own_folder_the_screens_come_through_the_overlay():
    base = b".\\data\\quartermaster\\ui\\"
    eng = Machine(screen_files(base=base))
    ensure(eng, qmdir=b"")
    assert eng.log[-1] == b"[qm] ui ensure: ready=1 adds=1 from " + base
    eng = Machine(screen_files(base=base))
    ensure(eng, qmdir=None)               # no qm_rt at all
    assert eng.key(b"qm_ui", b"ready") == b"1"
