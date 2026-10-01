"""A parser for the engine's Pascal-like script language.

Read-only, no dependencies, `bytes` throughout, never decoded text. Nothing here
knows about this mod: it is given a file and answers questions about it.

Why this exists (AUDIT VERIFY-10). Both of the hard compile failures this
project has shipped were *language* errors, and nothing in the toolchain speaks
the language:

  `Compile script error: ShowCustomGame`   the emitted lobby called `GetRandom`,
      which is declared at file scope in `dogenerate.inc`. A menu screen is a
      separate compilation unit, so the name did not resolve - and an
      unresolved identifier is a hard error that kills the WHOLE screen. The
      menu came up as a bare backdrop.
  `Compile script error: EventCustomGame`  an injected block named a `const`
      above its declaration. That state declares its const block *after* its
      opening statements (conventions B8), so the whole state died and every
      button on the screen, Start included, went dead.

Each was then guarded by one bespoke check shaped around the exact defect. This
module generalises both into an analysis that also catches the case nobody
thought to name.

--------------------------------------------------------------------- the file

Two on-disk shapes, and `parse()` tells them apart by looking for the prefix:

  *wrapped*    `data/gui/menu.inc/*.inc`, `data/scripts/common.inc/*.inc`.
               A `section.begin / Name = X / Code : struct.begin ... struct.end
               / section.end` container whose every code line carries the
               literal prefix `      [*] = ;` (`c3kit.formats.bytes_ops.PREFIX`). Lines
               without it are container syntax, not code.
  *plain*      `data/scripts/lib/*.script`. Pascal from the first byte.

`Unit.code` is the source with comments, string literals and - for a wrapped
file - all container syntax replaced by spaces, **byte for byte in place**.
Every offset therefore still addresses the real file, which is what lets a
finding be reported as `file:line` (conventions V7).

------------------------------------------------------------------ the natives

`natives()` reads them out of `cossacks.exe`. The engine registers every script
native by storing its full declaration as a Delphi long string - refcount
`FF FF FF FF`, a uint32 length, the text, a NUL - and the text reads
`function RandomExt(): Float` or
`procedure SetGUIElementUserColor(const index: Integer; ...)`. 4856 of them.
This is the engine's own list, not a transcription of one, so
after a GSC patch it re-derives itself.

--------------------------------------------------------- what it does NOT do

Stated plainly, because a checker whose limits are unknown is a checker nobody
can trust:

  * **No scopes inside a unit.** Every declaration in a file is treated as
    visible everywhere in that file. A local of one procedure referenced from
    another resolves here and would not resolve in the engine. This direction
    is deliberate: it under-reports rather than crying wolf.
  * **No types.** `foo(1)` and `foo('1')` are the same to this module, and
    arity is not checked either.
  * **No expression grammar.** Operator precedence, statement structure and
    `if`/`then`/`else` pairing are not modelled. `begin`/`end` is counted, not
    matched to its construct.
  * **No `case` arm analysis.** A `case` contributes one `end` to the balance
    and nothing else.
  * **Order, not reachability, for B8.** `use_before_decl` compares byte
    offsets. A `const` declared at the top of a procedure and named earlier in
    the file by a *different* procedure is reported even though the engine
    might accept it; a name used before its declaration inside a loop that runs
    later is reported too. Both are the conservative direction for a hazard
    whose symptom is a dead screen.
  * **Includes are not followed** - there is no include mechanism in this
    language; a unit is a file.
"""
import os
import re
import struct

# Every code line of a wrapped .inc looks like `      [*] = ;<pascal>`. Spelled
# here rather than imported from swfp.bytes_ops so this module has no build
# dependency at all. verify.py's `gscript` section asserts the two agree, so a
# drift is one recorded failure rather than a parser that silently reads the
# wrong half of every line.
PREFIX = b"      [*] = ;"

# The part of it that is actually load-bearing. Vanilla is not consistent about
# the leading whitespace: 44980 code lines carry exactly six spaces, and five do
# not - `eventcustomgame.inc:174` has five, and four files put code on the
# container's own `Code`/`Description` line. Splitting on the six-space spelling
# silently drops those five lines, and dropping one `end` is enough to make the
# block balance of a perfectly good vanilla file look broken.
MARKER = b"[*] = ;"

SPACE = 32
QUOTE = 39          # '
BRACE_OPEN = 123    # {
BRACE_CLOSE = 125   # }
SLASH = 47          # /

# Words the language owns. Not a list of natives - a list of things that are
# never an identifier the resolver could be asked to bind. Derived from reading
# the shipped scripts; anything missing here surfaces as a false positive and is
# measured rather than assumed (see `tools/checks/gscript_check.py`).
KEYWORDS = frozenset(b"""
and args array begin break case class const constructor continue destructor div
do downto else end exit false for function global if in is mod nil not of or out
private procedure protected public record repeat result section self set shl shr
step struct then to true type until var while with xor
""".split())

# Compiler intrinsics: spelled like a call, resolved by the compiler, and
# therefore absent from the engine's registration table. Both are used by the
# shipped scripts (`SizeOf` 16 times, `PointerOf` 3), and both would otherwise
# be the resolver's only false positives across all 342 vanilla files.
INTRINSICS = frozenset(b"pointerof sizeof".split())

# Types appear in declarations, never as a call. The set is derived from the
# native signatures themselves (see `type_names()`), so it grows with the
# engine; these are the handful the signatures never mention as a bare type.
BUILTIN_TYPES = frozenset(b"boolean byte float integer pointer string".split())

_IDENT = re.compile(rb"[A-Za-z_]\w*")
_NUMBER_TAIL = re.compile(rb"[0-9]")


# --------------------------------------------------------------------- natives
_NATIVE_SIG = re.compile(rb"^\s*(function|procedure)\s+([A-Za-z_]\w*)")


def long_strings(blob):
    """Every Delphi long string in a PE image: `FFFFFFFF <len> <text> 00`."""
    out = []
    i = 0
    n = len(blob)
    while True:
        i = blob.find(b"\xff\xff\xff\xff", i)
        if i < 0:
            return out
        i += 4
        if i + 4 > n:
            return out
        size = struct.unpack_from("<I", blob, i)[0]
        end = i + 4 + size
        if 1 <= size <= 4096 and end < n and blob[end] == 0:
            out.append((i + 4, blob[i + 4:end]))
        # No skip past the record: a false FFFFFFFF must not hide a real one.


_ENGINE_CONST = re.compile(rb"^([A-Za-z_]\w*)\s*=")
_ENGINE_VAR = re.compile(rb"^[A-Za-z_]\w*$")


def natives(exe_path):
    """`{name: full declaration}` for every native the engine registers.

    Read out of the binary, so it cannot go stale the way a transcribed list
    would. Returns a dict; `len()` of it is the evidence
    that the extraction still works after a patch.
    """
    return engine_symbols(exe_path)[0]


def engine_symbols(exe_path):
    """`(routines, constants, variable candidates)` the engine registers.

    All three come out of the same long-string pool, and the region is bounded
    by the first and last `function`/`procedure` declaration - the registration
    table - so unrelated Delphi strings elsewhere in the image are out of
    scope by construction.

      routines   `{name: signature}`, 4856 of them.
      constants  `{name}` from the `name = value` form: `pi=3.14159265358979`,
                 `leConnect = `, and the rest of the LAN event enumeration.
      candidates `{name}` from bare single-identifier strings. This one is NOT
                 a symbol list - 1935 strings in the region are bare words and
                 most of them are GUI element names such as `Ok` and `edit`.
                 It is the *corroborating* half of a two-sided test: a name is
                 an engine variable when the binary registers it AND the whole
                 vanilla script corpus references it without ever declaring
                 it. That intersection is 22 names - the register slots,
                 `gLanEvent`, `gLanUID` - and it cannot swallow `GetRandom`,
                 because `GetRandom` IS declared in the corpus.
    """
    with open(exe_path, "rb") as f:
        blob = f.read()
    strings = long_strings(blob)
    sigs = [(off, text) for off, text in strings if _NATIVE_SIG.match(text)]
    if not sigs:
        raise RuntimeError("%s: no native declarations found - the engine's "
                           "registration table has moved" % exe_path)
    lo = min(off for off, _t in sigs)
    hi = max(off for off, _t in sigs)

    routines = {}
    for _off, text in sigs:
        m = _NATIVE_SIG.match(text)
        routines.setdefault(m.group(2), text.strip())

    constants, candidates = set(), set()
    for off, text in strings:
        if not (lo <= off <= hi) or _NATIVE_SIG.match(text):
            continue
        m = _ENGINE_CONST.match(text)
        if m:
            constants.add(m.group(1))
        elif _ENGINE_VAR.match(text):
            candidates.add(text)
    return routines, constants, candidates


def type_names(sigs):
    """Type identifiers mentioned by the native signatures.

    `const index: Integer`, `: TObj`, `array of String` - every word that
    appears in type position in the engine's own declarations. Derived, so a
    new engine type is known the day it is registered.
    """
    out = set()
    for text in sigs.values():
        for m in re.finditer(rb":\s*(?:array\s+of\s+)?([A-Za-z_]\w*)", text):
            out.add(m.group(1).lower())
    return out


# ------------------------------------------------------------------- tokenizer
def is_wrapped(data):
    """True for a `section.begin` container, false for a plain `.script`.

    A handful of vanilla states are containers with an empty body and carry no
    prefixed line at all (`gui/menu.inc/eventhud.inc`,
    `scripts/common.inc/oninit.inc`, and eight `nothing*.inc`), so the presence
    of the prefix alone is not the test.
    """
    return MARKER in data or data.lstrip()[:13] == b"section.begin"


def mask(data, wrapped=None):
    """Blank everything that is not code, preserving length and offsets.

    Replaced by spaces: `//` to end of line, `{ }` comments, the body of every
    string literal (the quotes stay, so `''` still reads as a token), and - in
    a wrapped file - every byte of every line that is not the code half of a
    `[*] = ;` line.

    Returns `(masked, wrapped)`.
    """
    if wrapped is None:
        wrapped = is_wrapped(data)
    out = bytearray(data)

    if wrapped:
        # Container syntax first: keep only what follows the prefix on lines
        # that carry it. Everything else on the line becomes spaces, so
        # `section.begin` cannot be read as a statement and `struct.end` cannot
        # be counted as a bare `end`.
        start = 0
        n = len(out)
        while start < n:
            stop = data.find(b"\n", start)
            if stop < 0:
                stop = n
            keep = data.find(MARKER, start, stop)
            # A line with no prefix is container syntax from end to end -
            # `Name = ShowMainMenu`, `UsedFileName = `, `struct.end`. Blanking
            # only up to the prefix would leave all of it readable as code.
            body = stop if keep < 0 else keep + len(MARKER)
            for k in range(start, body):
                if out[k] not in (13, 10):
                    out[k] = SPACE
            start = stop + 1

    i = 0
    n = len(out)
    while i < n:
        c = out[i]
        if c == SLASH and i + 1 < n and out[i + 1] == SLASH:
            while i < n and out[i] not in (13, 10):
                out[i] = SPACE
                i += 1
        elif c == BRACE_OPEN:
            while i < n and out[i] != BRACE_CLOSE:
                if out[i] not in (13, 10):
                    out[i] = SPACE
                i += 1
            if i < n:
                out[i] = SPACE
                i += 1
        elif c == QUOTE:
            i += 1
            while i < n:
                if out[i] == QUOTE:
                    # '' inside a literal is an escaped quote, not the end.
                    if i + 1 < n and out[i + 1] == QUOTE:
                        out[i] = SPACE
                        out[i + 1] = SPACE
                        i += 2
                        continue
                    i += 1
                    break
                if out[i] not in (13, 10):
                    out[i] = SPACE
                i += 1
        else:
            i += 1
    return bytes(out), wrapped


def container(data):
    """The container half of a wrapped file: everything the prefix hides.

    The inverse of `mask`'s first pass, comments removed the same way, so
    `section.begin` / `struct.begin` can be balanced separately from the code.
    """
    out = bytearray(data)
    start = 0
    n = len(out)
    while start < n:
        stop = data.find(b"\n", start)
        if stop < 0:
            stop = n
        keep = data[start:stop].find(MARKER)
        if keep >= 0:
            for k in range(start + keep, stop):
                out[k] = SPACE
        start = stop + 1
    for m in re.finditer(rb"//[^\r\n]*", bytes(out)):
        for k in range(m.start(), m.end()):
            out[k] = SPACE
    return bytes(out)


# ----------------------------------------------------------------- the objects
class Decl(object):
    __slots__ = ("kind", "name", "offset")

    def __init__(self, kind, name, offset):
        self.kind = kind            # const | var | function | procedure | type
        self.name = name            # bytes
        self.offset = offset

    def __repr__(self):
        return "Decl(%s %s @%d)" % (self.kind, self.name.decode(), self.offset)


class Use(object):
    __slots__ = ("name", "offset", "called")

    def __init__(self, name, offset, called):
        self.name = name
        self.offset = offset
        self.called = called        # True when followed by '('

    def __repr__(self):
        return "Use(%s @%d%s)" % (self.name.decode(), self.offset,
                                  ", called" if self.called else "")


class Unit(object):
    """One compilation unit: one file.

    `code` is the masked source, same length as `raw`, so every offset in
    `decls` and `uses` addresses the real file and `line(offset)` is exact.
    """

    def __init__(self, path, raw, code, wrapped, decls, uses, name=None):
        self.path = path
        self.raw = raw
        self.code = code
        self.wrapped = wrapped
        self.decls = decls
        self.uses = uses
        self.name = name            # the state name of a wrapped file

    def line(self, offset):
        return self.raw.count(b"\n", 0, max(0, offset)) + 1

    def where(self, offset):
        return "%s:%d" % (self.path, self.line(offset))

    def declared(self):
        return set(d.name for d in self.decls)

    def first_decl(self, name):
        """The earliest declaration of `name`, or None."""
        best = None
        for d in self.decls:
            if d.name == name and (best is None or d.offset < best.offset):
                best = d
        return best

    def __repr__(self):
        return "Unit(%s, %d decls, %d uses)" % (self.path, len(self.decls),
                                                len(self.uses))


# ---------------------------------------------------------------- declarations
# `function Name(` / `procedure Name(` / `function Name :` / `procedure Name;`
_ROUTINE = re.compile(rb"\b(function|procedure)\s+([A-Za-z_]\w*)")
# `const name = ...`. The language has no `const a, b = ...` form; verified by
# the calibration pass, which would have reported the missed name as unresolved.
_CONST = re.compile(rb"\bconst\s+([A-Za-z_]\w*)\s*=")
# `var a, b, c : Type` - and `const a, b : Integer` in a parameter list.
_VARS = re.compile(rb"\b(var|const)\s+([A-Za-z_]\w*(?:\s*,\s*[A-Za-z_]\w*)*)"
                   rb"\s*:")
# `TName : struct.begin`
_STRUCT = re.compile(rb"([A-Za-z_]\w*)\s*:\s*struct\.begin")
# `type TColor = class` - how data/scripts/lib/*.script declare their 140 types.
_CLASS = re.compile(rb"\btype\s+([A-Za-z_]\w*)\s*=\s*class")
# `global gMap : TMap;` - a library's own file-scope storage.
_GLOBAL = re.compile(rb"\bglobal\s+([A-Za-z_]\w*(?:\s*,\s*[A-Za-z_]\w*)*)\s*:")
# `args arg_plr: TPlayerArgs;` - the arguments a state is executed with.
_ARGS = re.compile(rb"\bargs\s+([A-Za-z_]\w*(?:\s*,\s*[A-Za-z_]\w*)*)\s*:")
# A class body's fields: `r, g, b, a : Float = 1;` at the start of a line.
_FIELD = re.compile(rb"^[ \t]*([A-Za-z_]\w*(?:\s*,\s*[A-Za-z_]\w*)*)\s*:\s*"
                    rb"(?:array\s*\[[^\]]*\]\s*of\s+)?[A-Za-z_]\w*", re.M)
# `for [MAIN]i := ... downto 0 do` ... `break(MAIN);` - the language's loop
# labels. Only the `for [` form declares one; `list[i]` must not.
_LABEL = re.compile(rb"\bfor\s*\[([A-Za-z_]\w*)\]")
_NAME_LINE = re.compile(rb"^\s*Name\s*=\s*(\S+)\s*$", re.M)


def class_spans(code):
    """`[(name, body start, body end)]` for every `type X = class ... end;`.

    Walked with the same token counter `balance()` uses, so a class holding
    methods - and `TRect` does - closes on its own `end` rather than on the
    first one it contains.
    """
    out = []
    for m in _CLASS.finditer(code):
        depth = 1
        start = m.end()
        pos = start
        for t in _BLOCK_TOK.finditer(code, start):
            word = t.group(1).lower()
            if word in (b"begin", b"case", b"class"):
                depth += 1
            else:
                depth -= 1
                if depth == 0:
                    pos = t.start()
                    break
        out.append((m.group(1), start, pos))
    return out


def _params(code, open_paren):
    """Names declared in the parameter list starting at `open_paren`."""
    depth = 0
    i = open_paren
    n = len(code)
    while i < n:
        if code[i] == 40:
            depth += 1
        elif code[i] == 41:
            depth -= 1
            if depth == 0:
                break
        i += 1
    body = code[open_paren + 1:i]
    out = []
    base = open_paren + 1
    for group in body.split(b";"):
        head = group.split(b":", 1)[0]
        for m in _IDENT.finditer(head):
            word = m.group(0)
            if word.lower() in (b"var", b"const", b"out"):
                continue
            out.append((word, base + head_offset(body, group) + m.start()))
    return out


def head_offset(body, group):
    """Byte offset of `group` inside `body`. Groups are split on `;`."""
    return body.find(group)


def declarations(code):
    """Every declaration in a masked unit, with its byte offset."""
    out = []
    for m in _ROUTINE.finditer(code):
        out.append(Decl(m.group(1).decode(), m.group(2), m.start(2)))
        # Parameters, and the implicit `Result` of a function.
        tail = code[m.end(2):m.end(2) + 400]
        stripped = tail.lstrip()
        if stripped[:1] == b"(":
            open_paren = m.end(2) + (len(tail) - len(stripped))
            for word, off in _params(code, open_paren):
                out.append(Decl("param", word, off))
        if m.group(1) == b"function":
            out.append(Decl("var", b"Result", m.start(2)))
    for m in _CONST.finditer(code):
        out.append(Decl("const", m.group(1), m.start(1)))
    for m in _VARS.finditer(code):
        group = m.group(2)
        base = m.start(2)
        for w in _IDENT.finditer(group):
            out.append(Decl("var", w.group(0), base + w.start()))
    for m in _LABEL.finditer(code):
        out.append(Decl("label", m.group(1), m.start(1)))
    for m in _STRUCT.finditer(code):
        out.append(Decl("type", m.group(1), m.start(1)))
    for m in _CLASS.finditer(code):
        out.append(Decl("type", m.group(1), m.start(1)))
    for pattern, kind in ((_GLOBAL, "global"), (_ARGS, "var")):
        for m in pattern.finditer(code):
            base = m.start(1)
            for w in _IDENT.finditer(m.group(1)):
                out.append(Decl(kind, w.group(0), base + w.start()))
    # Class fields are named bare inside the class's own methods, so they are
    # declarations of this unit like any other.
    for _name, start, end in class_spans(code):
        for m in _FIELD.finditer(code[start:end]):
            base = start + m.start(1)
            for w in _IDENT.finditer(m.group(1)):
                out.append(Decl("field", w.group(0), base + w.start()))
    return out


def uses(code):
    """Every identifier reference in a masked unit.

    A name preceded by `.` is a field or a container keyword, never a name the
    resolver has to bind - `gMap.settings.gen.randkey1` contributes `gMap` and
    nothing else.
    """
    out = []
    n = len(code)
    for m in _IDENT.finditer(code):
        start = m.start()
        j = start - 1
        while j >= 0 and code[j] in (32, 9):
            j -= 1
        if j >= 0 and code[j] == 46:            # '.'
            continue
        if j >= 0 and _NUMBER_TAIL.match(code[j:j + 1]):
            continue                             # 1shl / hex tail, not a name
        if start and code[start - 1] == 36:      # '$ffff' is a hex literal
            continue
        k = m.end()
        while k < n and code[k] in (32, 9):
            k += 1
        out.append(Use(m.group(0), start, k < n and code[k] == 40))
    return out


def parse(path, data=None):
    """Read (or accept) one file and return its `Unit`.

    `data` is for analysing a variant that is not on disk - which is how the
    two historical bugs are re-injected in the checks without ever writing
    them (conventions V3).
    """
    if data is None:
        with open(path, "rb") as f:
            data = f.read()
    code, wrapped = mask(data)
    name = None
    if wrapped:
        m = _NAME_LINE.search(container(data))
        if m:
            name = m.group(1)
    return Unit(path, data, code, wrapped, declarations(code), uses(code),
                name)


# --------------------------------------------------------------------- balance
_STRUCT_TOK = re.compile(rb"\b(section|struct)\.(begin|end)\b")
_BLOCK_TOK = re.compile(rb"\b(begin|end|case|class)\b", re.I)


def block_counts(code):
    """`{begin, case, class, end}` over a masked unit."""
    out = {b"begin": 0, b"end": 0, b"case": 0, b"class": 0}
    for m in _BLOCK_TOK.finditer(code):
        out[m.group(1).lower()] += 1
    return out


def balance(unit):
    """Block, bracket and container balance. Returns a list of messages.

    Three constructs close with `end` and only one of them opens with `begin`:
    `case ... of ... end` and `type X = class ... end` are the other two. The
    identity is therefore `begin + case + class == end`, and it holds on all
    342 vanilla `.inc`/`.script` files in the installed game - which is what
    makes it an assertion rather than a guess.
    """
    problems = []
    code = unit.code

    n = block_counts(code)
    opens = n[b"begin"] + n[b"case"] + n[b"class"]
    if opens != n[b"end"]:
        problems.append(
            "block balance: %d begin + %d case + %d class != %d end"
            % (n[b"begin"], n[b"case"], n[b"class"], n[b"end"]))

    for opener, closer, label in ((40, 41, "parentheses"), (91, 93, "brackets")):
        depth = 0
        worst = None
        for i, ch in enumerate(code):
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth < 0 and worst is None:
                    worst = i
                    depth = 0
        if worst is not None:
            problems.append("%ses: a closer at %s has no opener"
                            % (label, unit.where(worst)))
        elif depth:
            problems.append("%ses: %d left open" % (label, depth))

    if unit.wrapped:
        opened = {}
        for m in _STRUCT_TOK.finditer(container(unit.raw)):
            key = m.group(1).decode()
            opened[key] = opened.get(key, 0) + (1 if m.group(2) == b"begin"
                                                else -1)
        for key, depth in sorted(opened.items()):
            if depth:
                problems.append("%s.begin/%s.end: %+d" % (key, key, depth))
    return problems


# ----------------------------------------------------------- use before decl
# `const` is the hazard conventions B8 is about: some states declare their const
# block AFTER their opening statements, and naming one above it does not fail
# that line - it kills the entire state.
def use_before_decl(unit, kinds=("const",)):
    """[(Use, Decl)] for every name used before the byte that declares it."""
    firsts = {}
    for d in unit.decls:
        if d.kind not in kinds:
            continue
        if d.name not in firsts or d.offset < firsts[d.name].offset:
            firsts[d.name] = d
    # A name also declared as something else earlier (a param, a var) is not
    # the const hazard; it is shadowing, and the engine resolves it.
    other = {}
    for d in unit.decls:
        if d.kind in kinds:
            continue
        if d.name not in other or d.offset < other[d.name].offset:
            other[d.name] = d

    out = []
    seen = set()
    for u in unit.uses:
        d = firsts.get(u.name)
        if d is None or u.offset >= d.offset or u.name in seen:
            continue
        # The declaration itself is a use of its own name; skip it.
        if u.offset == d.offset:
            continue
        early = other.get(u.name)
        if early is not None and early.offset <= u.offset:
            continue
        seen.add(u.name)
        out.append((u, d))
    return out


# --------------------------------------------------------------- resolution
def lower_all(names):
    return set(n.lower() for n in names)


def resolvable(unit, native_names, global_names, library_names, types=()):
    """The set of names this unit may legally reference, lower cased.

    The language is case-insensitive - the shipped scripts call the engine's
    `Floor` as `floor` and its `Round` as `round`, several hundred times - so
    every set is folded before it is compared. Case-sensitive matching costs
    62 false positives on `floor` alone.
    """
    return (lower_all(native_names) | lower_all(global_names)
            | lower_all(library_names) | lower_all(unit.declared())
            | set(types) | KEYWORDS | BUILTIN_TYPES | INTRINSICS)


def unresolved(unit, known):
    """Every identifier this unit references that nothing declares.

    `known` is what `resolvable()` returned. One entry per distinct name, at
    its first occurrence, so a name used forty times is one finding.
    """
    out = []
    seen = set()
    for u in unit.uses:
        low = u.name.lower()
        if low in known or low in seen:
            continue
        seen.add(low)
        out.append(u)
    return out


# ---------------------------------------------------------------- the globals
def dmscript_globals(path):
    """Names every unit can see: `dmscript.global`'s constants, types, globals.

    Three sections, three shapes, all of them `name` on the left:
    `gc_ResCount = 7;` constants, `TObj : struct.begin` types, and
    `gMap = TMap` globals. Comments are stripped the same way as code.
    """
    with open(path, "rb") as f:
        data = f.read()
    data = re.sub(rb"//[^\r\n]*", b"", data)
    out = set()
    for m in re.finditer(rb"^\s*([A-Za-z_]\w*)\s*(?::\s*struct\.begin|=)",
                         data, re.M):
        out.add(m.group(1))
    # Struct fields are addressed through a `.`, so they are never resolved as
    # a bare name and are deliberately not collected.
    return out


# ---------------------------------------------------------- by-reference arguments

_LITERAL_ARG = re.compile(rb"^(?:'.*'|[-+]?\d+(?:\.\d+)?|\$[0-9A-Fa-f]+|true|false|nil)$",
                          re.I | re.S)


def _param_modes(code, open_paren):
    """`[(name, mode)]` of the parameter list at `open_paren`, mode b'' when bare."""
    depth, i, n = 0, open_paren, len(code)
    while i < n:
        if code[i] == 40:
            depth += 1
        elif code[i] == 41:
            depth -= 1
            if depth == 0:
                break
        i += 1
    out = []
    for group in code[open_paren + 1:i].split(b";"):
        head = group.split(b":", 1)[0].strip()
        mode = b""
        first = head.split(None, 1)
        if first and first[0].lower() in (b"var", b"const", b"out"):
            mode = first[0].lower()
            head = first[1] if len(first) > 1 else b""
        for m in _IDENT.finditer(head):
            out.append((m.group(0), mode))
    return out, i


def by_reference(units):
    """`{routine (lower case): set of var-parameter positions}` over library units."""
    out = {}
    for unit in units:
        for m in _ROUTINE.finditer(unit.code):
            tail = unit.code[m.end(2):m.end(2) + 400]
            stripped = tail.lstrip()
            if stripped[:1] != b"(":
                continue
            params, _end = _param_modes(unit.code, m.end(2) + len(tail) - len(stripped))
            refs = set(k for k, (_n, mode) in enumerate(params) if mode in (b"var", b"out"))
            if refs:
                out[m.group(2).lower()] = refs
    return out


def _routine_scopes(code):
    """`[(body start, body end, const parameter names lower)]` for every routine."""
    scopes = []
    for m in _ROUTINE.finditer(code):
        tail = code[m.end(2):m.end(2) + 400]
        stripped = tail.lstrip()
        consts, after = set(), m.end(2)
        if stripped[:1] == b"(":
            params, after = _param_modes(code, m.end(2) + len(tail) - len(stripped))
            consts = set(nm.lower() for nm, mode in params if mode == b"const")
        first = re.compile(rb"\bbegin\b", re.I).search(code, after)
        if not first:
            continue
        depth, end = 0, len(code)
        for t in _BLOCK_TOK.finditer(code, first.start()):
            word = t.group(1).lower()
            depth += -1 if word == b"end" else 1
            if depth == 0:
                end = t.end()
                break
        scopes.append((first.start(), end, consts))
    return scopes


def _call_args(code, open_paren):
    """The top-level argument texts of the call whose `(` is at `open_paren`."""
    depth, i, n, start, out, quoted = 0, open_paren, len(code), open_paren + 1, [], False
    while i < n:
        c = code[i]
        if c == 39:
            quoted = not quoted
        elif not quoted:
            if c in (40, 91):
                depth += 1
            elif c in (41, 93):
                depth -= 1
                if depth == 0:
                    out.append(code[start:i].strip())
                    return out
            elif c == 44 and depth == 1:
                out.append(code[start:i].strip())
                start = i + 1
        i += 1
    return out


def byref_misuse(unit, byref):
    """Arguments no `var` parameter can take: `[(offset, routine, argument, why)]`.

    A `var` parameter is written through, so what is handed to it has to be
    storage the caller may write: a variable, a field, an element. A literal is
    not, and neither is the caller's own `const` parameter - handing one over
    is a compile error that takes the whole state with it, which is how
    `swfp_AutotestProduce` passing its `const sid` to
    `_unit_ConvertObjSIDToID(const cid; var sid : String)` (`unit.script:438`)
    became `Compile script error: DoProgress` on 2026-09-17. A routine the unit
    declares itself is left alone: its own signature is the one in force.
    """
    own = set(d.name.lower() for d in unit.decls if d.kind in ("function", "procedure"))
    scopes = _routine_scopes(unit.code)
    out = []
    for use in unit.uses:
        name = use.name.lower()
        if not use.called or name not in byref or name in own:
            continue
        paren = unit.code.find(b"(", use.offset + len(use.name))
        args = _call_args(unit.code, paren)
        consts = set()
        for start, end, names in scopes:
            if start <= use.offset < end:
                consts = names
        for k in sorted(byref[name]):
            if k >= len(args):
                continue
            arg = args[k]
            if _LITERAL_ARG.match(arg):
                out.append((use.offset, use.name, arg, "a literal"))
            elif arg.lower() in consts:
                out.append((use.offset, use.name, arg,
                            "a const parameter of the routine it is called from"))
    return out


def library_globals(lib_dir, overlay_dir=None):
    """File-scope declarations of `data/scripts/lib/*.script`.

    `dmscript.source:72-99` loads these 28 libraries for every compilation
    unit, so anything they declare at file scope is a genuine global. Locals
    inside their bodies are not, and this is the one place where the absence of
    scope tracking widens the resolver instead of narrowing it - measured in
    the calibration, not assumed.

    `overlay_dir` is the mod's own `data/scripts/lib`. A library the mod
    shadows is read from there, because that is the file the engine loads
    (proven on 2026-08-25 by overriding `gui.script`) - so a helper the overlay
    deletes stops resolving here too.
    """
    out = set()
    files = []
    for fn in sorted(os.listdir(lib_dir)):
        if not fn.lower().endswith(".script"):
            continue
        path = os.path.join(lib_dir, fn)
        if overlay_dir:
            shadow = os.path.join(overlay_dir, fn)
            if os.path.exists(shadow):
                path = shadow
        unit = parse(path)
        files.append(unit)
        out |= set(d.name for d in unit.decls
                   if d.kind in ("function", "procedure", "const", "type",
                                 "global"))
    return out, files


class Environment(object):
    """Everything a compilation unit can see before it declares anything.

    Built once per run from the installed game and nothing else. `stats` is
    what the checks print, and what makes it visible when a GSC patch moves
    something: a rule derived from an empty set passes everything.
    """

    def __init__(self, game, overlay=None):
        exe = os.path.join(game, "cossacks.exe")
        routines, constants, candidates = engine_symbols(exe)
        self.exe = exe
        self.routines = routines
        self.constants = constants
        self.types = type_names(routines)
        # The overlay's copy when the mod ships one, for exactly the reason
        # `library_globals` below is told about the overlay: `dmscript.global`
        # is loaded by path from `data/scripts`, so a mod that overrides it
        # overrides what every compilation unit can see. Reading vanilla's
        # instead reports every constant the mod adds as an unresolved
        # identifier - a hard compile error that is not there - and, worse,
        # stays silent about one the mod removed.
        glob_path = os.path.join(game, "data", "scripts", "dmscript.global")
        over_glob = (os.path.join(overlay, "data", "scripts", "dmscript.global")
                     if overlay else None)
        if over_glob and os.path.isfile(over_glob):
            glob_path = over_glob
        self.globals = dmscript_globals(glob_path)
        self.globals_path = glob_path
        lib_dir = os.path.join(game, "data", "scripts", "lib")
        over = (os.path.join(overlay, "data", "scripts", "lib")
                if overlay else None)
        if over and not os.path.isdir(over):
            over = None
        self.library, self.library_units = library_globals(lib_dir, over)
        self.byref = by_reference(self.library_units)
        self.corpus = corpus_files(game)
        self.variables = engine_variables(self.corpus, candidates,
                                          set(routines) | constants
                                          | self.globals | self.library)
        self.known = (lower_all(routines) | lower_all(constants)
                      | lower_all(self.variables) | lower_all(self.globals)
                      | lower_all(self.library) | self.types
                      | KEYWORDS | BUILTIN_TYPES | INTRINSICS)

    def resolvable(self, unit):
        return self.known | lower_all(unit.declared())

    def unresolved(self, unit):
        return unresolved(unit, self.resolvable(unit))

    def stats(self):
        return {"natives": len(self.routines),
                "engine constants": len(self.constants),
                "engine variables": len(self.variables),
                "dmscript.global": len(self.globals),
                "scripts/lib": len(self.library),
                "by-reference routines": len(self.byref),
                "vanilla corpus files": len(self.corpus)}


def corpus_files(game):
    """Every vanilla `.inc` and `.script` under `<game>/data`."""
    out = []
    for root, _dirs, files in os.walk(os.path.join(game, "data")):
        for fn in sorted(files):
            if fn.lower().endswith((".inc", ".script")):
                out.append(os.path.join(root, fn))
    return sorted(out)


def engine_variables(corpus, candidates, declared_elsewhere):
    """Engine-provided storage: `IntRegister0`, `gLanEvent`, `gLanUID`, ...

    Two-sided, because neither side alone is safe. The binary side (1935 bare
    strings in the registration region) is far too wide - it holds every GUI
    element name in the game. The corpus side ("vanilla references it and
    nothing declares it") is the same authority the scope check already uses:
    the installed game compiles, so a name it references resolves somehow.

    Their intersection is what this returns, and the corpus side is exactly
    what keeps `GetRandom` out of it: `GetRandom` IS declared in the corpus -
    at file scope in `dogenerate.inc` - so it can never be mistaken for an
    engine symbol, which is the whole point of the scope check.
    """
    referenced, declared = set(), set(declared_elsewhere)
    units = []
    for path in corpus:
        unit = parse(path)
        units.append(unit)
        declared |= unit.declared()
    low = lower_all(declared)
    for unit in units:
        for u in unit.uses:
            if u.name.lower() not in low:
                referenced.add(u.name)
    fold = dict((c.lower(), c) for c in candidates)
    return set(fold[n.lower()] for n in referenced
               if n.lower() in fold and n.lower() not in KEYWORDS)
