r"""`.inc` state files: the `Code` values, and the bytes around them.

The shape is derived from the 313 `.inc` files under `<game>\data` (the gate in
tests/test_ref_inc.py parses every one of them and writes it back byte for byte).
Every file is one section, one state:

    section.begin
       Name = OnCamera                         (all 313)
       Description[*] = ;                      (docreate.inc:3 only)
       UsedFileName =                          (25 files, e.g. doprogress.inc:3)
       Code : struct.begin                     (294 files, e.g. oncamera.inc:3)
          [*] = ;if (gInterface.gamemode=gc_gamemode_mainmenu) then
          ...
       struct.end
    section.end
    <empty line>                               (295 files; 14 end without CRLF, 4 without the empty line)

or, instead of the struct, a single line `   Code[*] = ;SwitchTo('Nothing');`
(10 files, e.g. scripts/units/building.inc/onbeforesave.inc:3), or no `Code` at
all (9 files, e.g. gui/menu.inc/eventhud.inc). One code line of eventcustomgame.inc
(:174) is indented by five spaces instead of six.

A `Code` value is everything after `[*] = `, leading `;` kept (`values`). Every
vanilla value starts with `;`, but the engine does not require it: probe 4
appended a value without one, the engine wrote it as `      [*] = Log(...)` and
ran it after the restart (r4.1.log:21).

What the engine's parser hands a script is not quite that (`engine_values`):
it drops trailing spaces. Believed until SelfTest run m2a (2026-09-28): the
parser hands over the value as it is. What it cost: 13 of the 294 struct-form
vanilla files hashed differently in-game (qm_case1: onlaneventsession.inc
30548 bytes of values against 30563). True: all 294 match once each value
loses its trailing spaces (39 values, all trailing byte 32; no vanilla value
ends in a tab, so what the parser does with one is what the synthetic probe
of the SelfTest's incprobe case is for). The parser is therefore not a
lossless reader: the game side reads `.inc` files with the raw reader and
takes the values from the lines (`values_from_lines`), and uses the parser
only where nothing is lost.

Serialisers:

  `serialise`   lossless: the exact bytes that were parsed. The round-trip gate.
  `render`      the engine's layout: `section.begin`, the keys with three spaces,
                the Code values, CRLF, and an empty line after `section.end`.
                The Code form follows the NUMBER of values, not the file that was
                loaded: none - no Code line; one - `   Code[*] = <value>`; two or
                more - `   Code : struct.begin`, `      [*] = <value>` each,
                `   struct.end`. Believed until run m2a: the form stays the one
                of the loaded file (so `Code[*] = ` and no-Code layouts were
                refused as unverified). True, from what the engine's
                ParserSaveToFileByHandle wrote in m2a's incprobe: the
                struct-form onafterload.inc with one value came back as
                `Code[*] = `; the ten `Code[*] = ` files came back as they were
                and, with a second value, as a struct; the nine no-Code files
                came back as they were. Probes 4 and 5 (a struct loaded with one
                value written with two; oncamera.inc, 73 values) fit the same
                rule.
  `render_raw`  what the game side's raw writer makes of `render`'s lines: the
                same bytes, padded with 0-3 spaces to a multiple of 4. This is
                how Quartermaster writes `.inc` files (decided
                2026-09-28): the parser appends a value with the key `[*]` only
                once - m2a's incw1 appended three values to oncamera.inc and the
                saved file held one, the last - so it cannot write a result
                longer than the file it loaded plus one line.

`min_count` pads a result with empty statements `;`, as the probe-5 merge did
when it could only overwrite Code lines. With the raw writer a shorter result
can simply be shorter; the parameter stays for callers that want the old length.
"""
import re

from .textio import BOM, escape, unescape, write_file

__all__ = ["CODE_PREFIX", "EMPTY_VALUE", "IncFile", "IncFormatError",
           "UnverifiedLayout", "parse", "serialise", "engine_values", "render",
           "layout_lines", "render_lines", "render_raw", "values_from_lines",
           "is_engine_layout", "code_words", "hook_index", "insert_at_hook"]

#: How the engine writes a code line (r4_generated_eventhud.inc, r5c merge).
CODE_PREFIX = b"      [*] = "
#: What the probe-5 writer put into a vanilla line the merged result no longer
#: needed.
EMPTY_VALUE = b";"
CRLF = b"\r\n"

_EOL = re.compile(rb"\r\n|\n|\r")
_NAME = re.compile(rb"^ *Name = (.*)$")
_KEY = re.compile(rb"^ *[A-Za-z_][A-Za-z0-9_]*(\[\*\])? = .*$")
_STRUCT_OPEN = re.compile(rb"^ *Code : struct\.begin$")
_STRUCT_CLOSE = re.compile(rb"^ *struct\.end$")
_CODE_LINE = re.compile(rb"^( *\[\*\] = )(.*)$")
_CODE_SINGLE = re.compile(rb"^( *Code\[\*\] = )(.*)$")


class IncFormatError(ValueError):
    """The file is not in the shape every vanilla `.inc` has."""


class UnverifiedLayout(ValueError):
    """A layout no engine-written file has shown yet (none left since run m2a;
    kept for callers that catch it)."""


class IncFile(object):
    """One parsed `.inc`: `head` + code lines + `tail`, all as the file had them.

    form      'struct' (`Code : struct.begin`), 'single' (`Code[*] = `) or 'none'
    name      the state name, from `Name = `
    keys      the key lines between `section.begin` and `Code`, without EOL,
              in file order (`Name`, `Description[*]`, `UsedFileName`)
    values    the Code values, leading `;` kept
    prefixes  per value, the bytes in front of it on its line
    eols      per value, the line terminator after it
    """

    def __init__(self, form, name, keys, head, values, prefixes, eols, tail):
        self.form = form
        self.name = name
        self.keys = keys
        self.head = head
        self.values = values
        self.prefixes = prefixes
        self.eols = eols
        self.tail = tail

    def __repr__(self):
        return "IncFile(%r, %s, %d values)" % (self.name, self.form,
                                               len(self.values))


def _lines(data):
    """`data` as `[(text, eol)]`; joining them gives `data` back exactly."""
    out = []
    pos = 0
    for m in _EOL.finditer(data):
        out.append((data[pos:m.start()], m.group()))
        pos = m.end()
    if pos < len(data):
        out.append((data[pos:], b""))
    return out


def parse(data):
    """Parse `.inc` bytes. Raises `IncFormatError` on any shape not seen in vanilla."""
    lines = _lines(data)
    texts = [t for t, _eol in lines]
    if not texts:
        raise IncFormatError("empty file")
    first = texts[0][len(BOM):] if texts[0].startswith(BOM) else texts[0]
    if first != b"section.begin":
        raise IncFormatError("first line is %r, not section.begin" % texts[0][:40])
    if texts.count(b"section.end") != 1 or sum(
            1 for t in texts if t.endswith(b"section.begin")) != 1:
        raise IncFormatError("not exactly one section")
    end = texts.index(b"section.end")
    for t in texts[end + 1:]:
        if t != b"":
            raise IncFormatError("text after section.end: %r" % t[:40])

    keys = []
    name = None
    i = 1
    code_at = None
    form = "none"
    while i < end:
        t = texts[i]
        if _STRUCT_OPEN.match(t):
            form, code_at = "struct", i
            break
        if _CODE_SINGLE.match(t):
            form, code_at = "single", i
            break
        if not _KEY.match(t):
            raise IncFormatError("line %d is not a key: %r" % (i + 1, t[:60]))
        m = _NAME.match(t)
        if m:
            if name is not None:
                raise IncFormatError("two Name keys")
            name = m.group(1)
        keys.append(t)
        i += 1
    if name is None:
        raise IncFormatError("no Name key")

    values, prefixes, eols = [], [], []
    if form == "struct":
        j = code_at + 1
        while j < end and not _STRUCT_CLOSE.match(texts[j]):
            m = _CODE_LINE.match(texts[j])
            if not m:
                raise IncFormatError("line %d inside Code is not [*] = : %r"
                                     % (j + 1, texts[j][:60]))
            prefixes.append(m.group(1))
            values.append(m.group(2))
            eols.append(lines[j][1])
            j += 1
        if j >= end:
            raise IncFormatError("Code struct not closed")
        first_code, after_code = code_at + 1, j
        if j + 1 != end:
            raise IncFormatError("lines between struct.end and section.end")
    elif form == "single":
        m = _CODE_SINGLE.match(texts[code_at])
        prefixes.append(m.group(1))
        values.append(m.group(2))
        eols.append(lines[code_at][1])
        first_code, after_code = code_at, code_at + 1
        if after_code != end:
            raise IncFormatError("lines between Code[*] and section.end")
    else:
        first_code = after_code = end

    head = b"".join(t + e for t, e in lines[:first_code])
    tail = b"".join(t + e for t, e in lines[after_code:])
    return IncFile(form, name, keys, head, values, prefixes, eols, tail)


def serialise(inc):
    """The exact bytes `inc` was parsed from (or its edited values in place)."""
    body = b"".join(p + v + e for p, v, e in zip(inc.prefixes, inc.values, inc.eols))
    return inc.head + body + inc.tail


def engine_values(inc):
    """The Code values as the engine's parser hands them to a script (run m2a)."""
    return [v.rstrip(b" ") for v in inc.values]


def _layout(keys, values):
    """The engine layout as lines without EOL: keys are re-indented, the Code
    form follows the number of values."""
    out = [b"section.begin"] + [b"   " + key.lstrip(b" ") for key in keys]
    if len(values) == 1:
        out.append(b"   Code[*] = " + values[0])
    elif values:
        out.append(b"   Code : struct.begin")
        out.extend(CODE_PREFIX + v for v in values)
        out.append(b"   struct.end")
    return out + [b"section.end", b""]


def layout_lines(keys, values):
    """The engine layout's lines for key lines and values given as internal
    strings - what the game side's qmIncRender writes, before CRLF and padding.

    Every fixed part of the layout is inside the raw reader's character table,
    so the lines are internal strings too; `ref.textio.write_file` of them is
    the file.
    """
    return _layout(keys, list(values))


def render(inc, values, min_count=0):
    """The engine's layout of `inc`'s keys with `values` as Code (see the docstring).

    `min_count`: pad with `;` up to this many values.
    """
    values = list(values) + [EMPTY_VALUE] * max(0, min_count - len(values))
    return b"".join(line + CRLF for line in _layout(inc.keys, values))


def render_lines(inc, values, min_count=0):
    """`render`'s lines as the raw writer's internal strings (`ref.textio`)."""
    values = list(values) + [EMPTY_VALUE] * max(0, min_count - len(values))
    return [escape(line) for line in _layout(inc.keys, values)]


def render_raw(inc, values, min_count=0):
    """The bytes the game side's raw writer writes for `render(inc, values)`."""
    return write_file(render_lines(inc, values, min_count))


def values_from_lines(lines):
    """`(form, keys, values)` from the raw reader's lines (internal strings).

    The game side's qmIncFromLines (src/lib/qminc.pas), rule for rule: line 0
    is `section.begin`; key lines follow until a line that, without its leading
    spaces, starts `Code : struct.begin` (struct: every following line up to
    `struct.end` is a value, the text after the first `[*] = `), starts
    `Code[*] = ` (single: the text after it) or is `section.end` (none). On a
    well-formed file this is `parse` on the same bytes, escaped.
    """
    keys, values, form = [], [], "none"
    i = 1
    while i < len(lines):
        t = lines[i].lstrip(b" ")
        if t.startswith(b"Code : struct.begin"):
            form = "struct"
            i += 1
            while i < len(lines) and lines[i].lstrip(b" ") != b"struct.end":
                at = lines[i].find(b"[*] = ")
                values.append(lines[i][at + 6:] if at >= 0 else b"")
                i += 1
            break
        if t.startswith(b"Code[*] = "):
            form = "single"
            values.append(t[len(b"Code[*] = "):])
            break
        if t == b"section.end":
            break
        keys.append(lines[i])
        i += 1
    return form, keys, values


def is_engine_layout(data):
    """Would the engine's parser write these exact bytes back?

    `render` of the values the parser holds (`engine_values`) - which is what
    ParserSaveToFileByHandle wrote in run m2a for all 22 probed files.
    """
    inc = parse(data)
    return render(inc, engine_values(inc)) == data


# ------------------------------------------------------------------ hooks
_OPENERS = (b"begin", b"case", b"try", b"asm", b"record", b"class")


def code_words(text, in_brace=False, keep_case=False):
    """`(words, in_brace)`: the lower-cased words of one code line, or the
    words as written with `keep_case` (the conflict report names routines).

    Outside `//` comments, `{ }` comments (which may span lines: `in_brace`
    says whether the line starts inside one) and string literals. A word is a
    run of letters, digits and `_` that starts with a letter or `_`.
    """
    words = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if in_brace:
            if c == 125:
                in_brace = False
            i += 1
        elif c == 123:
            in_brace = True
            i += 1
        elif c == 47 and text[i + 1:i + 2] == b"/":
            break
        elif c == 39:
            i += 1
            while i < n and text[i] != 39:
                i += 1
            i += 1
        elif c == 95 or 65 <= c <= 90 or 97 <= c <= 122:
            j = i
            while j < n and (text[j] == 95 or 48 <= text[j] <= 57 or 65 <= text[j] <= 90
                             or 97 <= text[j] <= 122):
                j += 1
            words.append(text[i:j] if keep_case else text[i:j].lower())
            i = j
        elif 48 <= c <= 57:
            while i < n and (text[i] == 95 or 48 <= text[i] <= 57 or 65 <= text[i] <= 90
                             or 97 <= text[i] <= 122):
                i += 1
        else:
            i += 1
    return words, in_brace


def _code_of(value):
    return value[1:] if value.startswith(b";") else value


def hook_index(values):
    """Where Quartermaster's hook lines go in a file's Code values (plan S5).

    Before the first top-level Code line after the routines a state may start
    with: a routine begins with a line whose first word is `procedure` or
    `function` and ends with the line that closes its outermost `begin` (or
    `case`, `try`, `asm`, `record`, `class`) block; blank and comment-only
    lines between and after such routines are passed over too. A file that
    does not start with a routine gets the hook at index 0. The four hook
    files: cameracontrol.inc 8 (`const cTagLeft = 20;`, after
    CreateCameraControlLayer and one blank line - where the capability probes
    and run m2a hooked), doprogress.inc 10 (after ExecuteStateByFlag and one
    blank line - where probes 4 and 5 inserted their blocks), initminimap.inc
    and eventmainmenu.inc 0.

    The one definition of the rule: tools/hbuild.py places the static hook
    copy with it, merged output (ref/merge.py) and the game side
    (src/lib/qminc.pas qmIncHookIndex) the same way, so the hook lines keep
    their position across generations.
    """
    n = len(values)
    i = 0
    seen = False
    while i < n:
        words, _brace = code_words(_code_of(values[i]))
        if words and words[0] in (b"procedure", b"function"):
            seen = True
            depth, opened, in_brace = 0, False, False
            while i < n:
                words, in_brace = code_words(_code_of(values[i]), in_brace)
                for w in words:
                    if w in _OPENERS:
                        depth += 1
                        opened = True
                    elif w == b"end":
                        depth -= 1
                i += 1
                if opened and depth <= 0:
                    break
            continue
        if seen and _is_blank(_code_of(values[i])):
            i += 1
            continue
        break
    return i if seen else 0


def _is_blank(text):
    """No code on the line: empty, spaces and tabs, or one comment."""
    t = text.strip(b" \t")
    return (not t or t.startswith(b"//")
            or (t.startswith(b"{") and t.endswith(b"}") and b"}" not in t[:-1]))


def insert_at_hook(values, hook):
    """`values` with the hook lines at `hook_index(values)`."""
    k = hook_index(values)
    return list(values[:k]) + list(hook) + list(values[k:])

