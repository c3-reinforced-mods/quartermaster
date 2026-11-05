"""The texts a mod declares for other languages (docs/localisation.md):
`name.<code>`, `group.<code>` and `label.<code>` rows of about.cfg. qmAbout
ignores them; qmAboutLoc checks every row and applies the ones of the game's
language. The state is run on the script interpreter and compared, key by key,
with its twin ref/about.py (the rest of qm_about is test_m8_about's).
"""
import pytest

import test_m5_pascal as PAS5
import test_m8_about as AB
from ref import about as A
from ref import textio as T

QM = PAS5.QM

ABOUT = (
    "id = loc\n"
    "name = WASD camera\n"
    "name.pl = Kamera WASD z klawiszami żółć\n"
    "name.de = WASD-Kamera\n"
    "name.zh = WASD 相机\n"
    "name.ru = Камера WASD\n"
    "group = Camera keys\n"
    "group.pl = Camera keys;Klawisze kamery\n"
    "group.zh = Camera keys;相机按键\n"
    "group.ko = Camera keys;카메라 키\n"
    "setting = left;key;A;Camera left\n"
    "group = Speed\n"
    "setting = speed;int;6;Speed;1..20\n"
    "setting = smooth;bool;1;Smooth scrolling\n"
    "label.pl = left;Kamera w lewo\n"
    "label.PL = SPEED;Szybkość kamery\n"
    "label.zh = left;向左移动 \\ 按键\n"
    "label.tu = left;Kamera sola ğış İ\n"
    "label.hu = left;őű kamera\n"
    "label.ru = speed;Скорость\n"
    "label.fr = smooth;Défilement fluide — œ\n"
    "label.de = smooth;Ł\n"
    "label.pl = smooth;中文\n"
    "label.pl = nosuch;x\n"
    "label.pl = speed\n"
    "label.pl = ;x\n"
    "label.pl = speed;\n"
    "group.pl = Nope;x\n"
    "name.xx = no such language\n"
    "name.de =\n"
    "label.pl = speed;Szybkość kamery 2\n"
).encode("utf-8")

BAD_UTF8 = b"id = bad\nname.pl = \xff\xfe\nname.de = ok \xc3\n"

FILES = {b"mods\\Loc": ABOUT, b"mods\\Bad": BAD_UTF8, b"mods\\Plain": b"id = plain\nname = Plain\nname.pl = Zwyk\xc5\x82y\n"}
MODS = [(b"mods\\Loc", True, b""), (b"mods\\Bad", True, b""), (b"mods\\Plain", True, b""), (QM, True, b"")]


def compare(code):
    eng = AB.engine(MODS, FILES, locale=code)
    want = AB.expected(MODS, FILES, lang=code)
    got = {k: eng.key(b"qm_about", k) for k in want}
    return [(k, got[k], want[k]) for k in sorted(want) if got[k] != want[k]]


@pytest.mark.parametrize("code", [b"en", b"pl", b"de", b"fr", b"hu", b"tu", b"ru", b"zh", b"ko", b"ja", b"xx"])
def test_qm_about_with_the_texts_of_a_language_equals_the_twin(code):
    assert compare(code) == []


def test_the_rows_of_the_language_replace_the_name_the_group_and_the_label():
    a = A.parse(ABOUT, b"pl")
    assert T.unescape(a.name) == "Kamera WASD z klawiszami żółć".encode("cp1250")
    left, speed, smooth = a.settings
    assert T.unescape(left.label) == "Kamera w lewo".encode("cp1250")
    assert T.unescape(left.group) == b"Klawisze kamery"
    assert T.unescape(speed.group) == b"Speed"            # no row for that group in pl
    assert T.unescape(speed.label) == "Szybkość kamery 2".encode("cp1250")   # the last row counts


def test_chinese_is_ascii_with_escapes_and_a_backslash_is_u005c():
    a = A.parse(ABOUT, b"zh")
    # a name and a group's title stand in lists, which a wide language cannot draw: as declared
    assert T.unescape(a.name) == b"WASD camera" and T.unescape(a.settings[0].group) == b"Camera keys"
    assert T.unescape(a.settings[0].label) == b"\\u5411\\u5DE6\\u79FB\\u52A8 \\u005C \\u6309\\u952E"


def test_without_a_language_the_rows_are_skipped_without_a_warning():
    a = A.parse(ABOUT)
    assert not any(p.code.startswith(b"l10n") or p.code == b"unknown" for p in a.problems)
    assert T.unescape(a.name) == b"WASD camera"


def test_each_wrong_row_is_a_warning_in_file_order():
    a = A.parse(ABOUT, b"en")
    found = [(p.code, p.text.split(b":")[0]) for p in a.problems if p.code.startswith(b"l10n")]
    assert found == [(b"l10n-target", b"line 24"), (b"l10n-fields", b"line 25"),
                     (b"l10n-fields", b"line 26"), (b"l10n-fields", b"line 27"),
                     (b"l10n-target", b"line 28"), (b"l10n-lang", b"line 29"),
                     (b"l10n-fields", b"line 30")]


def test_a_text_the_language_cannot_show_leaves_the_declared_one():
    a = A.parse(ABOUT, b"pl")
    assert [p.code for p in a.problems if p.code == b"l10n-chars"] == [b"l10n-chars"]   # label.pl = smooth;<Chinese>
    assert T.unescape(a.settings[2].label) == b"Smooth scrolling"
    b = A.parse(BAD_UTF8, b"pl")
    assert [p.code for p in b.problems] == [b"l10n-chars"] and b.name == b""


def test_an_older_quartermaster_would_warn_but_this_one_does_not_call_the_rows_unknown():
    eng = AB.engine(MODS, FILES)
    n = int(eng.key(b"qm_about", b"pn0"))
    kinds = [eng.key(b"qm_about", b"pc0_%d" % k) for k in range(n)]
    assert b"unknown" not in kinds
