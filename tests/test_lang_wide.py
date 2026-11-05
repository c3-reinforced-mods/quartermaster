"""Measuring, wrapping and cutting a text with characters written as escapes
(src/lib/qmwide.pas), over the emulated font of test_m6_show (a byte 8 wide, a
line 17 high), and the texts a list draws in a language drawn from wide fonts.
"""
import hbuild as H
import test_m3_pascal as PAS
import test_m6_show as S

BS = chr(92)
ESC = BS + "u4E2D" + BS + "u6587"            # two characters written as escapes


def run_wide(body):
    """The qmwide helpers, then `body`; what it stores in the parser `r` comes back."""
    _states, helpers = H.load_sources()
    code = H.render_lines(helpers["qmwide"], {}) + [b""] + [
        l.encode("ascii") for l in body.strip().splitlines()]
    code = [l.replace(b"gUIConst.font[", b"qmxuiconstfont[") for l in code]
    eng = S.Screen()
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
    # a line is 17+3 high: a character takes 20*23/20 = 23, a space 6, a word 5/4 of the engine's
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
    assert r(b"w") == b"46"                                     # two characters, 23 each
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
    # two characters (23 each), a space (6), 'ab' 16 wide in the engine and a quarter more
    assert r(b"w") == b"%d" % (23 * 2 + 6 + (16 * 5) // 4)
