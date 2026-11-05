"""Measuring, wrapping and cutting a text with characters written as escapes
(src/lib/qmwide.pas), over the emulated font of test_m6_show (a byte 8 wide, a
line 17 high), and the texts a list draws in a language drawn from wide fonts.
"""
import hbuild as H
import test_m3_pascal as PAS
import test_m6_show as S

PAS.BYREF_NATIVES["getguilistboxtabproperty"] = (2, 3, 4, 5, 6)

BS = chr(92)
ESC = BS + "u4E2D" + BS + "u6587"            # two characters written as escapes


class WideScreen(S.Screen):
    """The emulated window with fonts that have names, as the engine's do."""

    def n_qmxuiconstfont(self):
        return PAS.Arr(0, [b"serif%d" % k for k in range(32)])


def run_wide(body):
    """The qmwide helpers, then `body`; what it stores in the parser `r` comes back."""
    _states, helpers = H.load_sources()
    code = H.render_lines(helpers["qmwide"], {}) + [b""] + [
        l.encode("ascii") for l in body.strip().splitlines()]
    code = [l.replace(b"gUIConst.font[", b"qmxuiconstfont[") for l in code]
    eng = WideScreen()
    eng.n_ParserCreate(b"r")
    PAS.State(code, eng).run()
    h = eng.named[b"r"]
    return lambda key: eng.n_ParserGetValueByKeyByHandle(h, key)


def test_an_escape_is_one_character_and_a_cut_never_splits_it():
    r = run_wide("""
var qmTs : String;
var p : Integer = ParserSelectByKey('r');
ParserSetIntValueByKeyByHandle(p, 'len', qmCharLen('ab%s'));
ParserSetIntValueByKeyByHandle(p, 'has', qmWideHas('ab%s'));
ParserSetIntValueByKeyByHandle(p, 'no', qmWideHas('a%su12 plain %su'));
qmHead('ab%s', 3, qmTs);
ParserSetValueByKeyByHandle(p, 'head', qmTs);
qmHead('plain', 3, qmTs);
ParserSetValueByKeyByHandle(p, 'plain', qmTs);
""" % (ESC, ESC, BS, BS, ESC))
    assert r(b"len") == b"4" and r(b"has") == b"1" and r(b"no") == b"0"
    assert r(b"head") == ("ab" + BS + "u4E2D").encode() and r(b"plain") == b"pla"


def test_a_plain_text_is_measured_and_wrapped_by_the_engine_as_before():
    r = run_wide("""
var qmTs : String;
var w : Integer;
var h : Integer;
var p : Integer = ParserSelectByKey('r');
qmRect(gc_font_serif_13, 'abcd', w, h);
ParserSetIntValueByKeyByHandle(p, 'w', w);
ParserSetIntValueByKeyByHandle(p, 'h', h);
qmWrap(gc_font_serif_13, 'some plain words', 50, qmTs);
ParserSetValueByKeyByHandle(p, 'wrap', qmTs);
""")
    assert r(b"w") == b"32" and r(b"h") == b"17" and r(b"wrap") == b"some plain words"


def test_a_wide_text_is_wrapped_between_characters_and_measured_by_its_characters():
    # the wide font is 17 high here: a character takes 17*23/20 = 19, a space 5, a word 5/4 of the engine's
    r = run_wide("""
var qmTs : String;
var w : Integer;
var h : Integer;
var p : Integer = ParserSelectByKey('r');
qmRect(gc_font_serif_13, '%s', w, h);
ParserSetIntValueByKeyByHandle(p, 'w', w);
qmWrap(gc_font_serif_13, '%s%s%s', 50, qmTs);
ParserSetValueByKeyByHandle(p, 'wrap', qmTs);
""" % (ESC, ESC, ESC, ESC))
    assert r(b"w") == b"38"                                     # two characters, 19 each
    lines = r(b"wrap").split(b"\r\n")
    assert len(lines) == 3 and all(l.count(BS.encode() + b"u") <= 2 for l in lines)
    assert b"".join(lines).decode("ascii") == ESC * 3           # nothing lost, nothing cut in two


def test_a_tag_has_no_width_and_a_word_of_ascii_goes_with_the_text():
    r = run_wide("""
var w : Integer;
var h : Integer;
var p : Integer = ParserSelectByKey('r');
qmRect(gc_font_serif_13, '%%color(red)%%%s ab', w, h);
ParserSetIntValueByKeyByHandle(p, 'w', w);
""" % ESC)
    # two characters (19 each), a space (5), 'ab' 16 wide in the engine and a quarter more
    assert r(b"w") == b"%d" % (19 * 2 + 5 + (16 * 5) // 4)


# ------------------------------------------------------------ lists and a button
class ListScreen(WideScreen):
    """The list natives a wide list uses: what the state gave each item and the mode."""

    locale = b"zh"

    def __init__(self):
        WideScreen.__init__(self)
        self.items, self.wide_items, self.wide_mode, self.font = [], {}, False, b"serif12"
        self.coded = []

    def n_GUIListBoxAddItem(self, lb, text, tag):
        self.items.append((text, tag))

    def n_GetGUIListBoxItemsCount(self, lb):
        return len(self.items)

    def n_GetGUIListBoxWideMode(self, lb):
        return self.wide_mode

    def n_SetGUIListBoxWideMode(self, lb, on):
        self.wide_mode = on

    def n_GetGUIElementFont(self, el):
        return self.font

    def n_SetGUIElementFont(self, el, name):
        self.font = name

    def n_GetGUIListBoxTabsCount(self, lb):
        return 2

    def n_GetGUIListBoxTabProperty(self, lb, i, r, g, b, a, w):
        w.v = 40

    def n_WideStringAssignStringCoded(self, slot, code):
        self.coded.append((slot, code))

    def n_SetGUIListBoxItemWideValue(self, lb, i, slot):
        self.wide_items[i] = self.coded[-1][1]

    def n_SetGUIListBoxItemValue(self, lb, i, text):
        pass

    def n_GetViewerHeight(self):
        return 1080

    def n_SetGUIElementText(self, el, text):
        self.text = text

    def n_SetGUIElementWideText(self, el, slot):
        self.wide_text = self.coded[-1][1]


def run_list(body, locale=b"zh"):
    _states, helpers = H.load_sources()
    code = (H.render_lines(helpers["qmtext"], {}) + [b""] + H.render_lines(helpers["qmwide"], {})
            + [b""] + [l.encode("ascii") for l in body.strip().splitlines()])
    code = [l.replace(b"gUIConst.font[", b"qmxuiconstfont[") for l in code]
    eng = ListScreen()
    eng.locale = locale
    PAS.State(code, eng).run()
    return eng


def test_in_a_wide_language_a_list_with_an_escape_becomes_a_wide_list():
    eng = run_list("qmListAdd(5, '%s', 7);\nqmListAdd(5, 'plain', 8);" % ESC)
    assert eng.items == [(ESC.encode(), 7), (b"plain", 8)]
    assert eng.wide_mode and eng.font == b"wz_serif12"        # the wide font of the list's bitmap font
    assert eng.wide_items == {0: b"4E2D6587"}                  # two characters, four hex digits each


def test_the_cells_of_a_row_are_set_apart_to_the_columns_of_the_list():
    # the first cell is one character (19 wide) and the first column 40 wide, a space 5:
    # four spaces bring the second cell to where its column starts
    eng = run_list("qmListAdd(5, '%s'+#9+'%s', 1);" % (ESC[:6], ESC[6:]))
    assert eng.wide_items[0] == b"4E2D" + b"0020" * 4 + b"6587"


def test_another_language_and_a_plain_text_go_the_way_they_always_went():
    eng = run_list("qmListAdd(5, '%s', 7);" % ESC, locale=b"pl")
    assert eng.items == [(ESC.encode(), 7)] and not eng.wide_mode and eng.wide_items == {}
    eng = run_list("qmListAdd(5, 'plain', 7);")
    assert eng.items == [(b"plain", 7)] and not eng.wide_mode


def test_a_button_text_with_an_escape_is_drawn_from_the_wide_font_and_a_plain_one_is_set_as_before():
    eng = run_list("qmSetText(9, '%%color(red)%%%s ab');" % ESC)
    assert eng.text == b"" and eng.font == b"wz_serif12" and eng.wide_text == b"4E2D6587" + b"00200061" + b"0062"
    eng = run_list("qmSetText(9, 'Mod Manager');")
    assert eng.text == b"Mod Manager" and eng.font == b"serif12"
