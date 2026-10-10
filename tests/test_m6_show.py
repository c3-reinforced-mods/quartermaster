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
        self.x = self.y = 0


class Screen(PAS5.Engine):
    """An element tree the state builds; each element knows its parent."""

    def __init__(self):
        PAS5.Engine.__init__(self)
        self.els = {TOP: El(TOP, "top", b"", 0)}
        self.urls, self.did = [], []
        #: (font, text) of every width the state measured
        self.measured = []
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
        h_ = self._add("image", name, parent, tag=tag, w=w, h=h)
        self.els[h_].x, self.els[h_].y = x, y
        self.els[h_].hint, self.els[h_].event = hint, event
        return h_

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
        self.els[h_].x, self.els[h_].y = x, y
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

    def n_qmxuiconstfontstyle(self):
        return PAS.Arr(0, [b"<f%d>" % k for k in range(32)])

    def n_GetGUIElementFontTextRect(self, font, text, w, h):
        self.measured.append((font, text))
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


def window_code():
    """ShowQmManager's lines, the record fields the interpreter does not
    have made natives (gUIConst.font, gUIConst.fontstyle)."""
    return [l.replace(b"gUIConst.font[", b"qmxuiconstfont[")
             .replace(b"gUIConst.fontstyle[", b"qmxuiconstfontstyle[")
            for l in PAS5.sources()["showqmmanager"]]


def show(ui, rt=None, report=None, answer=True, takes_open=True):
    """ShowQmManager over qm_ui = `ui` (and qm_rt, qm_report); the event state
    answers the ping unless `answer` is False, the controller takes `open`
    (clears cmd) unless `takes_open` is False."""
    eng = Screen()
    eng.states["showqmmanager"] = PAS.State(window_code(), eng)
    for name, keys in ((b"qm_ui", ui), (b"qm_rt", rt), (b"qm_report", report)):
        if keys is not None:
            put(eng, name, keys)
    eng.answer = answer

    eng.order = []

    def act():
        eng.order.append("open")
        if takes_open:
            eng.n_ParserSetValueByKeyByHandle(eng.named[b"qm_ui"], b"cmd", b"")
    eng.states["qmuiact"] = PAS5.Fake(act)
    eng.states["qmpump"] = PAS5.Fake(lambda: eng.order.append("pump"))
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
    # A clash only asks since 0.1.3 (orange; red and a refused Apply before).
    (dict(pcn=2, pc0=b"A and B both ship lib\\unit.script"),
     b"May clash: A and B both ship lib\\unit.script. If the game does not start with both, "
     b"Quartermaster switches back. (1 more)", b"FFA500"),
    # An about.cfg FAIL, which stops the Apply, comes before a clash.
    (dict(pcn=1, pc0=b"A and B both ship lib\\unit.script", pan=1, pa0=b"C rules out D",
          pat0=b"FAIL"), b"C rules out D.", b"FF0000"),
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


def test_a_fresh_open_runs_the_pump_before_it_asks_for_the_model():
    # A restart the boot asked for is owed when no frame runs the tick
    # (qmpump.pas): it runs before the window is built, not at the first click.
    eng = show(model(ROWS))
    assert eng.order == ["pump", "open"]
    # a redraw of the open window is not an open
    eng.order[:] = []
    eng.states["showqmmanager"].run()
    assert eng.order == []


def test_opening_the_window_in_a_start_without_a_tick_runs_the_owed_restart():
    # The start of 2026-10-10 from the boot on: outputs made with a mod that
    # was then switched off outside Quartermaster, DoProgress did not compile,
    # the boot regenerated and asked for its restart (rs = 1), and no frame
    # ran the tick. The real pump, tick and restart under the real window.
    eng = Screen()
    eng.states["showqmmanager"] = PAS.State(window_code(), eng)
    PAS5.load(eng, "qmPump", "qmTick", "qmRestart", "qmMarkerSave")
    put(eng, b"qm_ui", dict(model(ROWS), ready=1))
    put(eng, b"qm_rt", dict(tick=1, rs=1, rsdue=9000, rskind=b"auto",
                            rswhy=b"outputs-changed", sync=0, busy=0))
    eng.answer = True
    eng.states["qmuiact"] = PAS5.Fake(
        lambda: eng.n_ParserSetValueByKeyByHandle(eng.named[b"qm_ui"], b"cmd", b""))
    eng.now = 1000.0
    eng.states["showqmmanager"].run()
    assert eng.restarted == ["lan", "steam", "restart"]
    assert eng.key(b"qm_rt", b"rs") == b"2" and eng.key(b"qm_rt", b"pumps") == b"1"
    # the same open in a start whose frames tick: the restart is the tick's
    put(eng, b"qm_rt", dict(rs=1, tkat=9995, pumps=0))
    eng.restarted[:] = []
    eng.find(b"QmManager").visible = False          # closed: the next show is an open
    eng.states["showqmmanager"].run()
    assert eng.restarted == [] and eng.key(b"qm_rt", b"pumps") == b"0"


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
    # 410 wide at 8 per byte: 51 bytes a line, broken at the last space before
    assert texts[b"olb2"] == (b"Camera speed when the mouse wheel scrolls (the host" + BR +
                              b"decides in multiplayer)")
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


def options(labels):
    """The Options view over bool settings with `labels`; {name: element} of
    its label texts, and the engine."""
    ui = model(ROWS, panel=2, opt=1, optn=len(labels), optpg=0, optcap=-1, optsel=-1)
    for k, label in enumerate(labels):
        ui.update({"oty%d" % k: b"bool", "olb%d" % k: label, "ov%d" % k: b"1",
                   "ovs%d" % k: b"1"})
    eng = show(ui)
    opts = win(eng, b"main.wnd.opts")
    return dict((t.name, t) for t in eng.under(opts.handle, "text")
                if t.name.startswith(b"olb")), eng


def test_a_long_label_takes_a_second_line_and_is_cut_only_after_it():
    # Hands-on, 2026-10-10: three labels of Reinforced - Core lost
    # their ends at the value column, without a `...`.
    fleet = (b"Fleet in a new skirmish (game keeps all ships, nowarships keeps "
             b"transports and fishing boats, noships keeps none of them at all)")
    labels, eng = options([b"Record replays of single player games", fleet,
                           b"A" * 60, b"Short one"])
    lh = LINE_H + 3
    one, two, word = labels[b"olb0"], labels[b"olb1"], labels[b"olb2"]
    assert one.text == b"Record replays of single player games"
    assert (one.y, one.h) == (14, 36)
    # 51 bytes fit a line: the break is at the last space before, the second
    # line keeps 48 bytes and says `...`
    first = b"Fleet in a new skirmish (game keeps all ships,"
    rest = fleet[len(first) + 1:]
    assert two.text == first + BR + rest[:48] + b"..."
    assert all(CHAR_W * len(l) <= 410 for l in two.text.split(BR))
    # two lines around the middle of the row, the height of two list lines
    assert (two.x, two.w) == (16, 420)
    assert (two.y, two.h) == (14 + 48 + 18 - lh, 2 * lh + 4)
    # a label without a space cannot break: one line, cut
    assert word.text == b"A" * 48 + b"..." and (word.y, word.h) == (14 + 2 * 48, 36)
    assert labels[b"olb3"].y == 14 + 3 * 48


def test_a_cut_label_says_the_rest_in_a_hint_and_only_a_cut_one():
    # Two lines first; what they cannot hold is in a hint over the label, as
    # vanilla hangs one on an icon (a blank image, no event state).
    fleet = (b"Fleet in a new skirmish (game keeps all ships, nowarships keeps "
             b"transports and fishing boats, noships keeps none of them at all)")
    camera = b"Camera distance (game is the height of the game, 58, far is 80, very far is 100)"
    labels, eng = options([b"Short one", fleet, b"A" * 60, camera])
    opts = win(eng, b"main.wnd.opts")
    hints = dict((i.name, i) for i in eng.under(opts.handle, "image")
                 if i.name.startswith(b"olh"))
    assert sorted(hints) == [b"olh1", b"olh2"]
    assert BR in labels[b"olb3"].text and b"..." not in labels[b"olb3"].text
    style = b"<f%d>" % CONST["gc_font_serif_13"] + W
    assert hints[b"olh1"].hint == style + fleet and hints[b"olh2"].hint == style + b"A" * 60
    # over the label and not past it: the value and the buttons stay free
    h = hints[b"olh1"]
    assert (h.x, h.w) == (16, 420) and (h.y, h.h) == (14 + 48 - 4, 44)
    assert h.event == b"" and h.tag == 0


def test_a_hint_is_wrapped_at_the_labels_width(monkeypatch):
    monkeypatch.setattr(Screen, "n_GetGUIWrappedTextByFont", _wrapped)
    labels, eng = options([b"Camera on W A S D (W A S D move the camera like the arrow keys, "
                           b"the hotkeys on A, S and D work as Shift+A, Shift+S and Shift+D)"])
    opts = win(eng, b"main.wnd.opts")
    hint = next(i for i in eng.under(opts.handle, "image") if i.name == b"olh0").hint
    body = hint[len(b"<f%d>" % CONST["gc_font_serif_13"] + W):]
    assert BR in body and all(CHAR_W * len(l) <= 420 for l in body.split(BR))
    assert body.replace(BR, b" ").endswith(b"Shift+S and Shift+D)")


def test_a_label_is_measured_in_the_font_it_is_drawn_in():
    # Until 0.1.4 the Options view measured in serif 12 and drew in serif 13,
    # so what it measured as fitting did not fit.
    labels, eng = options([b"Automatic map size in a new skirmish (follows the number of "
                           b"players)"])
    fonts = set(f for f, t in eng.measured if t.startswith(b"Automatic"))
    assert fonts == {1000 + CONST["gc_font_serif_13"]}
    eng = show(model([dict(name=b"Cannons Attack Automatically", dir=b"mods\\c", org=b"Local",
                           st=b"OK")]))
    fonts = set(f for f, t in eng.measured if t.startswith(b"Cannons"))
    assert fonts == {1000 + CONST["gc_font_serif_12"]}


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
    # Not "new mods" since 0.1.3: a mod switched on in modman is judged too,
    # and only against mods it has not started with.
    assert texts[b"gtext"] == b"Quartermaster switched off clashing mods"
    assert texts[b"gwhy"] == (
        b"Each of them replaces a core script that another active mod replaces too, and they"
        b" have not started together before. With both, the game may stop at \"Error compiling"
        b" scripts\", so Quartermaster switched these mods off and restarted the game:")
    assert texts[b"glist"] == b"Cannons (lib\\unit.script, State vs Country)" + BR + \
        b"Other (dmscript.global, Patrol)"
    # A set the player applies in the window is trusted for one start
    # (chosen.cfg), so the way to run such a pair anyway is to activate it.
    assert texts[b"gnote"] == (
        b"If they do work together, activate them here: Quartermaster lets them start once and"
        b" switches back if the game does not start.")
    assert buttons(eng, b"gnotice")[b"bok"] == (b"OK", True)
    assert win(eng, b"gnotice").visible


def _wrapped(self, font, text, width):
    """GetGUIWrappedTextByFont over the emulated font: a break wherever a
    line would run past `width`, at a space."""
    lines, line = [], b""
    for word in text.split(b" "):
        if line and CHAR_W * len(line + b" " + word) > width:
            lines.append(line)
            line = word
        else:
            line = word if not line else line + b" " + word
    return BR.join(lines + [line])


@pytest.mark.parametrize("why, n", [(b"conflict", 1), (b"conflict", 4), (b"failed-names", 2)])
def test_the_guard_notice_makes_room_for_its_wrapped_texts(monkeypatch, why, n):
    """The body and the line under the list wrap at the body's width; each
    text goes under the one before, and the window ends far enough below the
    last for the OK button to stay clear of it - the conflict's line under
    the list takes two lines since 0.1.3."""
    monkeypatch.setattr(Screen, "n_GetGUIWrappedTextByFont", _wrapped)
    keys = dict(("gdl%d" % k, b"Mod %d - ships scripts\\lib\\unit.script, like Other" % k)
                for k in range(n))
    eng = show(model(ROWS, mode=3, gdln=n, gdwhy=why, **keys))
    wnd = win(eng, b"gnotice.gwnd")
    texts = dict((t.name, t) for t in eng.under(wnd.handle, "text"))
    why_, lst, note = texts[b"gwhy"], texts[b"glist"], texts[b"gnote"]
    for t in (why_, note):
        lines = t.text.split(BR)
        assert all(CHAR_W * len(l) <= 720 for l in lines) and t.w == 720
        assert t.h >= LINE_H * len(lines)
    if why == b"conflict":
        assert (why_.text.count(BR), note.text.count(BR)) == (2, 1)
    assert lst.h >= n * LINE_H
    assert why_.y + why_.h <= lst.y and lst.y + lst.h <= note.y
    # Under the last line at least the room the one-line note left above the
    # OK button until 0.1.3 (centred 76 above the window's bottom edge).
    assert wnd.h - (note.y + note.h) >= 76 - LINE_H // 2


def test_the_guard_notice_after_a_start_that_stopped_says_so():
    """0.1.3: a step after a start that stopped (qm_ui gdwhy failed-*) switches
    mods off without a clash; its lines are the titles alone."""
    eng = show(model(ROWS, mode=3, gdln=1, gdl0=b"Cannons Attack Automatically",
                     gdwhy=b"failed-revert"))
    texts = dict((t.name, t.text) for t in eng.under(win(eng, b"gnotice.gwnd").handle, "text"))
    assert texts[b"gtext"] == b"Quartermaster switched mods off"
    assert texts[b"gwhy"].startswith(b'The last start did not reach the main menu: it stopped at '
                                     b'"Error compiling scripts", or the menu did not compile.')
    assert texts[b"glist"] == b"Cannons Attack Automatically"
    assert b"one at a time" in texts[b"gnote"]


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
    (TXStateMachine.IndexOfState, capability probe 10). `past_end` is what
    the engine answers for an index past the end of the list when it is read
    by index: silent and empty (run g17b1, 2026-10-05, docs/ui.md); a test
    below shows what the check and the log rule do should an engine log
    there instead."""

    def __init__(self, files):
        PAS5.Engine.__init__(self, files)
        self.machine = {}                       # name -> code lines
        self.gamemode = MAINMENU
        self.past_end = b""
        self.past_end_logs = False

    def n_qmxgintgamemode(self):
        return self.gamemode

    def n_gc_gamemode_mainmenu(self):
        return MAINMENU

    def n_StateMachineGetGUISMHandle(self):
        return GUISM

    def n_StateMachineGetStateIndByName(self, sm, name):
        names = list(self.machine)
        if name in getattr(self, "blind_once", set()):
            self.blind_once.discard(name)
            return -1
        if name not in names:
            self.log.append(b"ERROR| 9 |error (): TXStateMachine.IndexOfState(" + name + b")")
            return -1
        return 140 + names.index(name)

    def n_StateMachineGetStateNameByInd(self, sm, ind):
        names = list(self.machine)
        if 0 <= ind - 140 < len(names):
            return names[ind - 140]
        if self.past_end_logs:
            self.log.append(b"ERROR| 9 |error (): TXStateMachine.GetStateName(%d)" % ind)
        return self.past_end

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
    # The next DoCreate in the menu: one read of the name at the remembered
    # index, silent.
    ensure(eng)
    assert eng.log[-1] == b"[qm] ui ensure: screens present checks=1 adds=1"
    assert not [l for l in eng.log if l.startswith(b"ERROR")]


def test_the_check_remembers_where_it_added_the_window():
    eng = Machine(screen_files())
    ensure(eng)
    assert eng.key(b"qm_ui", b"showidx") == b"140"            # ShowQmManager is first
    assert b"[qm] ui ensure: added ShowQmManager lines=" in b"\n".join(eng.log)
    assert b"index=140" in b"\n".join(eng.log)


def test_a_map_load_drops_the_screens_and_they_come_back_without_an_error_line():
    eng = Machine(screen_files())
    ensure(eng)
    eng.machine = {}                     # a battle reloaded the GUI machine from menu.aix
    eng.gamemode = 2
    n = len(eng.log)
    ensure(eng)                          # the battle's own DoCreate: nothing at all
    assert len(eng.log) == n and eng.machine == {}
    eng.gamemode = MAINMENU
    ensure(eng)
    assert not [l for l in eng.log if l.startswith(b"ERROR")]       # no lookup by name
    assert b"[qm] ui ensure: screens gone (a map load reloaded the GUI machine); adding them " \
        b"again" in eng.log
    assert set(eng.machine) == {b"ShowQmManager", b"EventQmManager"}
    assert eng.key(b"qm_ui", b"adds") == b"2" and eng.key(b"qm_ui", b"checks") == b"1"
    ensure(eng)                          # and the second life of the screens checks the same way
    assert eng.log[-1] == b"[qm] ui ensure: screens present checks=2 adds=2"


def test_a_state_whose_index_the_engine_did_not_give_is_never_added_twice():
    """Review fix (0.1.4): should the lookup right after the add miss, the
    state is in all the same - it counts as added, and the check falls back to
    the lookup by name of 0.1.3 (silent while present, one ERROR when gone)."""
    eng = Machine(screen_files())
    eng.blind_once = {b"ShowQmManager"}
    ensure(eng)
    assert (eng.key(b"qm_ui", b"show"), eng.key(b"qm_ui", b"showidx")) == (b"1", b"-1")
    assert eng.key(b"qm_ui", b"ready") == b"1"
    ensure(eng)                                       # present: found by name, silently
    assert eng.log[-1] == b"[qm] ui ensure: screens present checks=1 adds=1"
    assert not [l for l in eng.log if l.startswith(b"ERROR")]
    eng.machine = {}
    eng.gamemode = 2
    ensure(eng)
    eng.gamemode = MAINMENU
    ensure(eng)                                       # gone: one ERROR, then added once
    assert [l for l in eng.log if l.startswith(b"ERROR")] == [
        b"ERROR| 9 |error (): TXStateMachine.IndexOfState(ShowQmManager)"]
    assert set(eng.machine) == {b"ShowQmManager", b"EventQmManager"}
    assert eng.key(b"qm_ui", b"showidx") == b"140"


def test_another_state_at_the_remembered_index_counts_as_gone():
    """After a reload another mod may have added a state at that index: the
    name differs, so the window's states are added again, not trusted."""
    eng = Machine(screen_files())
    ensure(eng)
    eng.machine = {b"SomeoneElsesState": []}       # reloaded; a mod's state sits at index 140
    eng.gamemode = 2
    ensure(eng)
    eng.gamemode = MAINMENU
    ensure(eng)
    assert b"[qm] ui ensure: screens gone (a map load reloaded the GUI machine); adding them " \
        b"again" in eng.log
    assert set(eng.machine) == {b"SomeoneElsesState", b"ShowQmManager", b"EventQmManager"}
    assert eng.key(b"qm_ui", b"showidx") == b"141"


def test_if_the_engine_logs_for_an_index_past_the_end_the_error_is_what_the_run_catches():
    """Not what the game does (it is silent there): should an engine log for
    that index, the check still works - the states come back - and the log
    rule of tools/m6cases.py fails on the ERROR line before `screens gone`."""
    eng = Machine(screen_files())
    eng.past_end_logs = True
    ensure(eng)
    eng.machine = {}
    eng.gamemode = 2
    ensure(eng)
    eng.gamemode = MAINMENU
    ensure(eng)
    assert set(eng.machine) == {b"ShowQmManager", b"EventQmManager"}
    errors = [l for l in eng.log if l.startswith(b"ERROR")]
    assert errors == [b"ERROR| 9 |error (): TXStateMachine.GetStateName(140)"]
    import m6cases
    problems = m6cases.log_problems([l.decode("latin-1") for l in eng.log], battles=1)[0]
    assert any("in the DoCreate before a 'screens gone'" in p for p in problems)


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
