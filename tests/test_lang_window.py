"""The manager window in the language of the game (docs/localisation.md): the
same state, the same model, a different folder under data/locale. The language
files are the ones the build writes (tests/test_m5_pascal.py text_file); a
language the build has no file for reads English.
"""
import pytest

import test_m6_show as S


def captions(monkeypatch, locale):
    monkeypatch.setattr(S.Screen, "locale", locale)
    eng = S.show(S.model(S.ROWS))
    return eng, {n: c for n, (c, _e) in S.buttons(eng).items()}


def test_english_is_the_default(monkeypatch):
    _eng, caps = captions(monkeypatch, b"en")
    assert caps[b"bapply"] == b"Apply" and caps[b"bclose2"] == b"Close"


@pytest.mark.parametrize("locale,apply_,close", [
    (b"pl", b"Zastosuj", b"Zamknij"),
    (b"de", b"Anwenden", b"Schlie\xdfen"),
    (b"fr", b"Appliquer", b"Fermer"),
    (b"ru", b"\xcf\xf0\xe8\xec\xe5\xed\xe8\xf2\xfc", b"\xc7\xe0\xea\xf0\xfb\xf2\xfc"),
    (b"tu", b"Uygula", b"Kapat"),
    (b"hu", b"Alkalmaz", b"Bez\xe1r\xe1s"),
    (b"zh", b"\\u5E94\\u7528", b"\\u5173\\u95ED"),
    (b"ko", b"\\uC801\\uC6A9", b"\\uB2EB\\uAE30"),
])
def test_the_buttons_read_in_the_language_of_the_game(monkeypatch, locale, apply_, close):
    eng, caps = captions(monkeypatch, locale)
    assert caps[b"bapply"] == apply_ and caps[b"bclose2"] == close
    # one parser holds the language, filled once
    assert eng.named[b"qm_text"]


def test_a_language_the_build_has_no_file_for_reads_english(monkeypatch):
    _eng, caps = captions(monkeypatch, b"xx")
    assert caps[b"bapply"] == b"Apply"


def test_a_text_with_places_takes_its_numbers_where_the_language_puts_them(monkeypatch):
    monkeypatch.setattr(S.Screen, "locale", b"hu")
    eng = S.show(S.model(S.ROWS, ord=[5, 0, 1, 3, 2, 4]))
    # the message line of a pending change: the numbers stand in the sentence
    text = " ".join(t.text.decode("cp1250") for t in eng.els.values() if t.kind == "text")
    assert "mod" in text



def test_a_language_picked_in_the_running_game_is_read_at_once(monkeypatch):
    # Settings applies a pick without a restart: the parser that holds the texts must follow it,
    # or the window keeps the old language in the old code page (seen in the game, 2026-11-05)
    monkeypatch.setattr(S.Screen, "locale", b"pl")
    eng = S.show(S.model(S.ROWS))
    assert {n: c for n, (c, _e) in S.buttons(eng).items()}[b"bapply"] == b"Zastosuj"
    eng.locale = b"de"
    eng.states["showqmmanager"].run()
    assert {n: c for n, (c, _e) in S.buttons(eng).items()}[b"bapply"] == b"Anwenden"
    eng.locale = b"zh"
    eng.states["showqmmanager"].run()
    assert {n: c for n, (c, _e) in S.buttons(eng).items()}[b"bapply"] == b"\\u5E94\\u7528"
