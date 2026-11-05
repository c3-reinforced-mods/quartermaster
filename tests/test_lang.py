"""The languages of Quartermaster's own texts (docs/localisation.md, plan G19):
the source files and their checks (ref/lang.py), the qmT macro of the build,
and the files the build writes. Nothing here reads the game.
"""
import os

import pytest

import hbuild
from ref import lang

SRC_TEXT = os.path.join(hbuild.SRC, "text")


SAMPLE = {"ru": "hello = Привет %1\nsave = Сохранить игру сейчас\n",
          "uk": "hello = Привіт %1\nsave = Зберегти гру зараз\n",
          "zh": "hello = 你好 %1\nsave = 现在保存游戏\n",
          "ja": "hello = こんにちは %1\nsave = 今すぐゲームを保存\n",
          "ko": "hello = 안녕 %1\nsave = 지금 게임 저장\n"}


def sources(**kw):
    """A complete set: English and a made-up text in each language's script."""
    base = {"en": b"hello = Hello %1\nsave = Save the game now\n"}
    for code in lang.CODES[1:]:
        base[code] = SAMPLE.get(code, "hello = Hola %1\nsave = Guardar el juego ahora\n").encode("utf-8")
    base.update({k: v.encode("utf-8") if isinstance(v, str) else v for k, v in kw.items()})
    return base


# ----------------------------------------------------------------- parsing
def test_parse_reads_keys_values_and_skips_comments_and_blank_lines():
    entries, problems = lang.parse(b"# a comment\r\n\r\nlast_one = a = b\r\nnext = x\r\n")
    assert problems == []
    assert entries == [("last_one", "a = b"), ("next", "x")]


@pytest.mark.parametrize("data,word", [
    (b"Key = x\n", "not a-z"),
    (b"a = x\na = y\n", "twice"),
    (b"a = x \n", "space at an end"),
    (b"a = \n", "empty"),
    (b"a = back\\slash\n", "backslash"),
    (b"a b\n", "no ' = '"),
    (b"a = \xff\n", "not UTF-8"),
    (b"\xef\xbb\xbfa = x\n", "byte order mark"),
])
def test_parse_names_what_is_wrong(data, word):
    assert any(word in p for p in lang.parse(data)[1])


# ---------------------------------------------------------------- encoding
def test_a_code_page_language_is_written_in_its_code_page_with_the_section():
    data = lang.encode("pl", [("a", "Zażółć")])
    assert data == b"section.begin\r\n   a = Za\xbf\xf3\xb3\xe6\r\nsection.end\r\n"
    assert lang.encode("ru", [("a", "Да")]) == b"section.begin\r\n   a = \xc4\xe0\r\nsection.end\r\n"
    assert lang.encode("tu", [("a", "ığ")]) == b"section.begin\r\n   a = \xfd\xf0\r\nsection.end\r\n"


def test_a_cjk_language_is_ascii_with_escapes():
    data = lang.encode("zh", [("a", "关闭 X")])
    assert data == b"section.begin\r\n   a = \\u5173\\u95ED X\r\nsection.end\r\n"
    data.decode("ascii")


def test_english_is_ascii_and_every_file_ends_in_crlf():
    for code in lang.CODES:
        data = lang.encode(code, [("a", "x")])
        assert data.endswith(b"\r\n") and data.count(b"\n") == data.count(b"\r\n")


# ------------------------------------------------------------------ checks
def test_a_complete_set_has_no_problems():
    assert lang.check(sources()) == []


def test_a_missing_key_a_foreign_key_and_a_wrong_order_are_found():
    found = lang.check(sources(pl="save = Zapisz grę teraz\nhello = Cześć %1\nextra = x\n"))
    texts = [t for c, t in found if c == "pl"]
    assert any("order" in t for t in texts) and any("extra" in t for t in texts)
    found = lang.check(sources(pl="hello = Cześć %1\n"))
    assert ("pl", "missing key save") in found


def test_placeholders_and_numbers_must_be_the_same():
    found = lang.check(sources(pl="hello = Cześć\nsave = Zapisz grę teraz\n"))
    assert ("pl", "hello: placeholders differ from English") in found
    en = dict(sources(), en=b"hello = Hello %1\nsave = Save the game 3 times now\n")
    found = lang.check(dict(en, pl="hello = Cześć %1\nsave = Zapisz grę raz teraz\n".encode()))
    assert ("pl", "save: numbers differ from English") in found


def test_a_text_left_in_english_is_found_but_a_short_one_may_stay():
    found = lang.check(sources(pl=b"hello = Hello %1\nsave = Save the game now\n"))
    assert ("pl", "save: left in English") in found
    assert not any("hello" in t for c, t in found if c == "pl")


def test_a_character_the_code_page_cannot_show_is_found():
    found = lang.check(sources(pl=b"hello = \xd0\x96 %1\nsave = Zapisz gr\xc4\x99 teraz\n"))
    assert any("cannot show" in t for c, t in found if c == "pl")


def test_the_script_of_the_language_is_checked():
    assert any("Cyrillic" in t for c, t in lang.check(sources(ru=b"hello = Hi %1\nsave = Zapisz gre teraz\n")) if c == "ru")
    assert any("script" in t for c, t in lang.check(sources(zh=b"hello = Hi %1\nsave = Zapisz gre teraz\n")) if c == "zh")
    assert any("script" in t for c, t in lang.check(sources(ko=b"hello = Hi %1\nsave = Zapisz gre teraz\n")) if c == "ko")
    assert not any(c == "ja" for c, t in lang.check(sources(ja="hello = こんにちは %1\nsave = 今すぐゲームを保存\n".encode())))


def test_a_language_without_a_file_is_found():
    s = sources()
    del s["ko"]
    assert ("ko", "no source file") in lang.check(s)


# ------------------------------------------------------------------- macro
def test_a_text_becomes_a_lookup_in_the_language_parser():
    out = hbuild.expand_texts(b"x := qmT('Apply');")
    assert out == b"x := ParserGetValueByKeyByHandle(ParserSelectByKey('qm_text'), 't_apply');"


def test_arguments_replace_the_numbered_places_in_order():
    out = hbuild.expand_texts(b"x := qmT('%2 of %1', IntToStr(a), b[1]);")
    assert out.startswith(b"x := StrReplace(StrReplace(ParserGetValueByKeyByHandle(")
    assert out.endswith(b", '%1', IntToStr(a)), '%2', b[1]);")


def test_a_text_inside_an_argument_and_a_comment_line_are_handled():
    hbuild.TEXTS.clear()
    out = hbuild.expand_texts(b"x := qmT('Mod %1', qmT('Name'));")
    hbuild.TEXTS.clear()
    assert out.count(b"ParserGetValueByKeyByHandle") == 2
    assert hbuild.expand_texts(b"// qmT('Never')") == b"// qmT('Never')"


def test_a_key_is_the_words_of_the_english_and_a_long_one_ends_in_a_hash():
    assert hbuild.text_key("Open Workshop") == "t_open_workshop"
    assert hbuild.text_key("3 mods") == "t_3_mods"
    assert hbuild.text_key("...") == "t_%06x" % (__import__("zlib").crc32(b"...") & 0xFFFFFF)
    long = hbuild.text_key("The game closes and starts again by itself. This can take up to half a minute")
    assert len(long) <= 36 and long != hbuild.text_key("The game closes and starts again by itself. This can take a while")


@pytest.mark.parametrize("line,word", [
    (b"x := qmT(a);", "string literal"),
    (b"x := qmT('No place', a);", "argument"),
    (b"x := qmT('Place %1');", "argument"),
    (b"x := qmT('Open", "closing bracket"),
])
def test_a_misused_macro_stops_the_build(line, word):
    with pytest.raises(hbuild.BuildError, match=word):
        hbuild.expand_texts(line)


def test_two_texts_with_one_key_stop_the_build():
    hbuild.TEXTS.clear()
    hbuild.expand_texts(b"x := qmT('Open workshop');")
    with pytest.raises(hbuild.BuildError, match="same key"):
        hbuild.expand_texts(b"x := qmT('Open  Workshop!');")
    hbuild.TEXTS.clear()


# ------------------------------------------------- the real sources and files
def test_the_english_master_is_what_the_code_holds():
    english = hbuild.collect_english()
    assert english, "no qmT in the code"
    with open(os.path.join(SRC_TEXT, "en.cfg"), "rb") as fh:
        assert fh.read() == hbuild.english_source(english)


def test_every_language_is_complete_and_checked():
    found = {}
    for code in lang.CODES:
        with open(os.path.join(SRC_TEXT, code + ".cfg"), "rb") as fh:
            found[code] = fh.read()
    assert lang.check(found) == []


def test_the_build_writes_one_file_per_language_in_its_code_page():
    files = dict(hbuild.load_texts(hbuild.SRC))
    assert sorted(files) == sorted(lang.TEXT_DIR + c + ".cfg" for c in lang.CODES)
    assert b"   t_apply = Zastosuj\r\n" in files[lang.TEXT_DIR + "pl.cfg"]
    assert files[lang.TEXT_DIR + "zh.cfg"].decode("ascii").count("\\u") > 10
    assert b"   t_apply = Apply\r\n" in files[lang.TEXT_DIR + "en.cfg"]


def test_a_state_that_has_a_text_loads_the_language_first():
    states, helpers = hbuild.load_sources()
    st = next(s for s in states if s.name == "ShowQmManager")
    code = b"\n".join(hbuild.state_code(st, helpers, dict(hbuild.BUILD_VARIABLES, hookgen=b"''")))
    assert b"procedure qmTextLoad;" in code and b"qmTextLoad;\n" in code
    assert b"qmT(" not in code


def test_a_text_a_list_draws_reads_english_in_a_language_drawn_from_wide_fonts():
    files = dict(hbuild.load_texts(hbuild.SRC))
    de = files[lang.TEXT_DIR + "de.cfg"]
    zh = files[lang.TEXT_DIR + "zh.cfg"].decode("ascii")
    assert b"   l_general = Allgemein\r\n" in de and b"   t_general = Allgemein\r\n" in de
    assert "   l_general = General\r\n" in zh and "   t_general = \\u5E38\\u89C4\r\n" in zh
    # the caption of the main menu's button is such a text too: English in zh, ja and ko
    assert "   l_mod_manager = Mod Manager\r\n" in zh


def test_the_list_form_of_the_macro_looks_up_the_list_key():
    hbuild.TEXTS.clear()
    hbuild.LISTTEXTS.clear()
    out = hbuild.expand_texts(b"x := qmTL('General');")
    assert out.endswith(b"'qm_text'), 'l_general');") and "t_general" in hbuild.TEXTS
    hbuild.TEXTS.clear()
    hbuild.LISTTEXTS.clear()
