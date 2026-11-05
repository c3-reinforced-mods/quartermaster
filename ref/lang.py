"""The languages of Quartermaster's own texts (docs/localisation.md, plan G19).

A source file is `src/text/<code>.cfg`: UTF-8, one `key = value` per line,
`#` comments and empty lines skipped. `en.cfg` is the master, extracted from the
defaults in the game-side code (`tools/qmtext.py --write`); every other
language holds the same keys in the same order. The build turns a source into
`data/quartermaster/text/<code>.cfg`, the file `qmText` (src/lib/qmtext.pas)
loads: the section the game's parser needs around a flat list, CRLF, and the
text in the code page of the language - for Chinese, Japanese and Korean
ASCII with `\\uXXXX` for each character outside ASCII (Core's wide-text path
turns such a text into a wide one; a backslash would be one, so a source never
holds a backslash).
"""
import re

#: The language folders of data/locale: the game's eleven, then the ones Core adds.
CODES = ("en", "cs", "de", "es", "fr", "it", "pl", "po", "ru", "tu", "uk",
         "hu", "nl", "zh", "ja", "ko")
#: How a language's text is written for the screen.
ENCODING = {"en": "ascii", "cs": "cp1250", "pl": "cp1250", "hu": "cp1250",
            "ru": "cp1251", "uk": "cp1251", "tu": "cp1254",
            "de": "cp1252", "es": "cp1252", "fr": "cp1252", "it": "cp1252",
            "po": "cp1252", "nl": "cp1252",
            "zh": "escaped", "ja": "escaped", "ko": "escaped"}
NAMES = {"en": "English", "cs": "Czech", "de": "German", "es": "Spanish",
         "fr": "French", "it": "Italian", "pl": "Polish", "po": "Portuguese",
         "ru": "Russian", "tu": "Turkish", "uk": "Ukrainian", "hu": "Hungarian",
         "nl": "Dutch", "zh": "Chinese (Simplified)", "ja": "Japanese",
         "ko": "Korean"}
#: Where the build puts the files, relative to the mod folder.
TEXT_DIR = "data/quartermaster/text/"

KEY = re.compile(r"[a-z][a-z0-9_]*\Z")
PLACEHOLDER = re.compile(r"%[1-9]")
NUMBER = re.compile(r"[0-9]+")
HAN = re.compile("[一-鿿]")
KANA = re.compile("[぀-ヿ]")
HANGUL = re.compile("[가-힣]")
CYRILLIC = re.compile("[Ѐ-ӿ]")
WORD = re.compile(r"[^\W\d_]{2,}", re.UNICODE)


def escape(text):
    """The ASCII form of an `escaped` language's text: `\\uXXXX` for every
    character outside ASCII (all of them are in the Basic Multilingual Plane)."""
    out = []
    for ch in text:
        if ord(ch) > 0xFFFF:
            raise ValueError("%r is outside the Basic Multilingual Plane" % ch)
        out.append(ch if ord(ch) < 0x80 else "\\u%04X" % ord(ch))
    return "".join(out)


def parse(data):
    """`(entries, problems)` of a source: entries `[(key, value)]` in file
    order, problems `[str]`."""
    entries, problems, seen = [], [], set()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        return entries, ["not UTF-8: %s" % exc]
    if text.startswith("﻿"):
        problems.append("starts with a byte order mark")
        text = text[1:]
    for n, line in enumerate(text.replace("\r\n", "\n").split("\n"), 1):
        if line == "" or line.startswith("#"):
            continue
        key, eq, value = line.partition(" = ")
        if not eq:
            problems.append("line %d: no ' = '" % n)
            continue
        if not KEY.match(key):
            problems.append("line %d: the key %r is not a-z, 0-9 and _" % (n, key))
        if key in seen:
            problems.append("line %d: the key %s twice" % (n, key))
        seen.add(key)
        if value != value.strip():
            problems.append("line %d: %s has a space at an end" % (n, key))
        if value == "":
            problems.append("line %d: %s is empty" % (n, key))
        if "\\" in value:
            problems.append("line %d: %s holds a backslash" % (n, key))
        if any(ord(c) < 32 for c in value):
            problems.append("line %d: %s holds a control character" % (n, key))
        entries.append((key, value))
    return entries, problems


def encode(code, entries):
    """The bytes of data/quartermaster/text/<code>.cfg."""
    enc = ENCODING[code]
    lines = ["section.begin"] + ["   %s = %s" % kv for kv in entries] + ["section.end", ""]
    text = "\r\n".join(lines)
    if enc == "escaped":
        return escape(text).encode("ascii")
    return text.encode(enc)


def _words(value):
    return WORD.findall(value)


def check(sources):
    """Problems of a set of sources `{code: bytes}`: `[(code, text)]`. English
    is the master; every other language must hold its keys in its order, its
    placeholders and numbers, text its code page can show, and the script of
    its language, and must not leave a text of three words or more in English."""
    problems = []
    parsed = {}
    for code in CODES:
        if code not in sources:
            problems.append((code, "no source file"))
            continue
        entries, found = parse(sources[code])
        problems += [(code, p) for p in found]
        parsed[code] = entries
    master = parsed.get("en")
    if master is None:
        return problems
    mkeys = [k for k, _v in master]
    for code, entries in parsed.items():
        if code == "en":
            continue
        keys = [k for k, _v in entries]
        for k in mkeys:
            if k not in keys:
                problems.append((code, "missing key %s" % k))
        for k in keys:
            if k not in mkeys:
                problems.append((code, "key %s is not in English" % k))
        if [k for k in keys if k in mkeys] != [k for k in mkeys if k in keys]:
            problems.append((code, "keys are not in the order of English"))
        en = dict(master)
        for k, v in entries:
            if k not in en:
                continue
            e = en[k]
            if sorted(PLACEHOLDER.findall(v)) != sorted(PLACEHOLDER.findall(e)):
                problems.append((code, "%s: placeholders differ from English" % k))
            if sorted(NUMBER.findall(v)) != sorted(NUMBER.findall(e)) and ENCODING[code] != "escaped":
                problems.append((code, "%s: numbers differ from English" % k))
            if v == e and len(_words(e)) >= 3:
                problems.append((code, "%s: left in English" % k))
            enc = ENCODING[code]
            if enc not in ("escaped", "ascii"):
                try:
                    v.encode(enc)
                except UnicodeEncodeError as exc:
                    problems.append((code, "%s: %s cannot show %r" % (k, enc, exc.object[exc.start:exc.end])))
            elif enc == "escaped":
                if any(ord(c) > 0xFFFF for c in v):
                    problems.append((code, "%s: a character outside the Basic Multilingual Plane" % k))
                need = {"zh": HAN, "ja": None, "ko": HANGUL}[code]
                if code == "ja":
                    if len(_words(e)) >= 3 and not (KANA.search(v) or HAN.search(v)):
                        problems.append((code, "%s: no Japanese script in it" % k))
                elif len(_words(e)) >= 3 and not need.search(v):
                    problems.append((code, "%s: no %s script in it" % (k, NAMES[code])))
            if enc in ("cp1250", "cp1252", "cp1254") and (CYRILLIC.search(v) or HAN.search(v)):
                problems.append((code, "%s: a script of another language" % k))
            if enc == "cp1251" and len(_words(e)) >= 3 and not CYRILLIC.search(v):
                problems.append((code, "%s: no Cyrillic in it" % k))
    return problems


def cp_table(page):
    """The table qmAboutLoc looks a character up in: four hex digits of the
    Unicode value of each byte 128..255 of the code page (`0000` for a byte it
    leaves undefined), 512 characters. A character's byte is 128 + the index
    of its four digits in the table."""
    out = []
    for b in range(128, 256):
        try:
            out.append("%04X" % ord(bytes([b]).decode(page)))
        except UnicodeDecodeError:
            out.append("0000")
    return "".join(out)


#: The code pages of CODES that a table is built for.
PAGES = ("cp1250", "cp1251", "cp1252", "cp1254")
