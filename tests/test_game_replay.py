"""Game-side `.inc` IO replayed in Python, statement for statement.

src/lib/qminc.pas cannot run offline. These replays follow its qmIncFromLines
and qmIncRender line by line - SubStr 1-based, StrPos 0 when absent, the
byte counts it adds up - and hold them against ref/inc.py on every vanilla
`.inc`, so a slip in the Pascal's logic shows up before a run."""
import pytest

from conftest import read_bytes
from ref import inc as I
from ref import textio as T


def substr(s, i, n):
    """SubStr(s, i, n): 1-based, clamped like the engine's (Copy)."""
    if n <= 0:
        return b""
    return s[max(i, 1) - 1:max(i, 1) - 1 + n]


def strpos(sub, s):
    return s.find(sub) + 1


def lstrip_spaces(t):
    while substr(t, 1, 1) == b" ":
        t = substr(t, 2, len(t) - 1)
    return t


def game_inc_from_lines(lines):
    n = len(lines)
    i, head, values, form, go = 1, [], [], 0, True
    while go and i < n:
        t = lstrip_spaces(lines[i])
        if substr(t, 1, 19) == b"Code : struct.begin":
            form = 2
            i += 1
            t = lstrip_spaces(lines[i]) if i < n else b""
            while i < n and t != b"struct.end":
                at = strpos(b"[*] = ", lines[i])
                values.append(substr(lines[i], at + 6, len(lines[i]) - at - 5) if at > 0 else b"")
                i += 1
                t = lstrip_spaces(lines[i]) if i < n else b""
            go = False
        elif substr(t, 1, 10) == b"Code[*] = ":
            form = 1
            values = [substr(t, 11, len(t) - 10)]
            go = False
        elif t == b"section.end":
            go = False
        else:
            head.append(lines[i])
            i += 1
    return form, head, values


def raw_len(s):
    return len(s) - 3 * s.count(b"~")


def game_inc_render_bytes(head, values):
    """qmIncRender's qmIrBytes."""
    total = 15
    for key in head:
        total += raw_len(lstrip_spaces(key)) + 5
    if len(values) == 1:
        total += raw_len(values[0]) + 15
    if len(values) > 1:
        total += 24 + sum(raw_len(v) + 14 for v in values) + 15
    total += 15
    while total % 4:
        total += 1
    return total


FORMS = {0: "none", 1: "single", 2: "struct"}


def test_inc_from_lines_replay_equals_the_twin(vanilla_inc_files):
    for path in vanilla_inc_files:
        lines = T.read_lines(read_bytes(path))
        form, head, values = game_inc_from_lines(lines)
        assert (FORMS[form], head, values) == I.values_from_lines(lines), path


def test_inc_render_byte_count_replay_equals_the_file(vanilla_inc_files):
    for path in vanilla_inc_files:
        _form, head, values = I.values_from_lines(T.read_lines(read_bytes(path)))
        for vals in (values, values[:1], [], values + [b";~126 x"]):
            written = T.write_file(I.layout_lines(head, vals))
            assert game_inc_render_bytes(head, vals) == len(written), path


@pytest.mark.parametrize("size", range(0, 13))
def test_sized_reader_count_rule(size):
    """qmRawRead's integer count and the bytes it takes from the last one."""
    rem, total = size % 4, size // 4 + (1 if size % 4 else 0)
    taken = [(rem if (k + 1 == total and rem > 0 and total * 4 > size) else 4)
             for k in range(total)]
    assert sum(taken) == size


# ------------------------------------------------------------- hook index
OPENERS = (b"begin", b"case", b"try", b"asm", b"record", b"class")


def game_words(s, in_brace):
    """qmIncWords on an internal string: (first word, openers, ends, in_brace)."""
    i, n, out = 1, len(s), in_brace
    first, nopen, nend = b"", 0, 0
    while i <= n:
        b = s[i - 1]
        if b == 126:
            e = substr(s, i, 4)
            if out:
                if e == b"~125":
                    out = False
            elif e == b"~123":
                out = True
            i += 4
        elif out:
            i += 1
        elif b == 47 and substr(s, i + 1, 1) == b"/":
            i = n + 1
        elif b == 39:
            i += 1
            while i <= n and s[i - 1] != 39:
                i += 1
            i += 1
        elif b == 95 or 65 <= b <= 90 or 97 <= b <= 122 or 48 <= b <= 57:
            j = i
            c = b
            while j <= n and (c == 95 or 65 <= c <= 90 or 97 <= c <= 122 or 48 <= c <= 57):
                j += 1
                c = s[j - 1] if j <= n else 0
            if not 48 <= b <= 57:
                w = substr(s, i, j - i).lower()
                if not first:
                    first = w
                nopen += w in OPENERS
                nend += w == b"end"
            i = j
        else:
            i += 1
    return first, nopen, nend, out


def game_blank(s):
    t, go = s, True
    while go:
        go = False
        if substr(t, 1, 1) == b" ":
            t, go = substr(t, 2, len(t) - 1), True
        elif substr(t, 1, 4) == b"~009":
            t, go = substr(t, 5, len(t) - 4), True
        elif t and substr(t, len(t), 1) == b" ":
            t, go = substr(t, 1, len(t) - 1), True
        elif len(t) >= 4 and substr(t, len(t) - 3, 4) == b"~009":
            t, go = substr(t, 1, len(t) - 4), True
    r = t == b"" or substr(t, 1, 2) == b"//"
    if not r and substr(t, 1, 4) == b"~123" and len(t) >= 8:
        if substr(t, len(t) - 3, 4) == b"~125":
            r = strpos(b"~125", substr(t, 1, len(t) - 4)) == 0
    return r


def game_hook_index(pool, at, n):
    i, seen, go = 0, False, True
    while go and i < n:
        t = pool[at + i]
        t = substr(t, 2, len(t) - 1) if substr(t, 1, 1) == b";" else t
        first, _o, _e, _b = game_words(t, False)
        if first in (b"procedure", b"function"):
            seen, depth, opened, brace, inner = True, 0, False, False, True
            while inner and i < n:
                t = pool[at + i]
                t = substr(t, 2, len(t) - 1) if substr(t, 1, 1) == b";" else t
                _f, o, e, brace = game_words(t, brace)
                depth += o - e
                opened = opened or o > 0
                i += 1
                if opened and depth <= 0:
                    inner = False
        elif seen and game_blank(t):
            i += 1
        else:
            go = False
    return i if seen else 0


def test_hook_index_replay_equals_the_twin(vanilla_inc_files):
    hooked = 0
    for path in vanilla_inc_files:
        values = I.parse(read_bytes(path)).values
        want = I.hook_index(values)
        pool = [b"junk"] * 3 + [T.escape(v) for v in values]
        assert game_hook_index(pool, 3, len(values)) == want, path
        hooked += want > 0
    assert hooked == 24


@pytest.mark.parametrize("values, want", [
    ([], 0),
    ([b";x := 1;"], 0),
    ([b";procedure qmA;", b";begin", b";end;"], 3),
    ([b";procedure qmA;", b";begin", b";end;", b";", b"; // note", b";{ c }", b";x := 1;"], 6),
    ([b";function qmF : Integer;", b";begin", b";   case 1 of", b";   1 : Result := 1;",
      b";   end;", b";end;", b";procedure qmG;", b";begin", b";   { end }", b";end;", b";y;"], 10),
    ([b";procedure qmA;", b";var s : String = 'end';", b";begin", b";end;", b";z;"], 4),
    ([b";procedure qmA; begin end;", b";z;"], 1),
    ([b";// procedure qmA;", b";z;"], 0),
])
def test_hook_index_rule(values, want):
    assert I.hook_index(values) == want
    pool = [T.escape(v) for v in values]
    assert game_hook_index(pool, 0, len(values)) == want


# ------------------------------------------------------------ pool reader
def game_inc_read_at(data, pool, at):
    """qmIncReadAt: raw lines into the pool at `at`, then the values moved down
    in place. Returns (head, n, form)."""
    lines = T.read_lines(data)
    pool[at:at + len(lines)] = lines
    form, head, _values = game_inc_from_lines(lines)
    if form == 2:
        first = at + next(i for i, t in enumerate(lines) if lstrip_spaces(t).startswith(
            b"Code : struct.begin")) + 1
    elif form == 1:
        first = at + next(i for i, t in enumerate(lines) if i and lstrip_spaces(t).startswith(
            b"Code[*] = "))
    n = len(_values)
    for k in range(n):
        line = pool[first + k]
        if form == 1:
            t = lstrip_spaces(line)
            v = substr(t, 11, len(t) - 10)
        else:
            a = strpos(b"[*] = ", line)
            v = substr(line, a + 6, len(line) - a - 5) if a > 0 else b""
        pool[at + k] = v
    return head, n, form


def test_pool_reader_replay_keeps_every_file_indexable(vanilla_inc_files):
    pool = [b""] * 200000
    at, spans = 0, []
    for path in vanilla_inc_files[:40]:
        data = read_bytes(path)
        head, n, form = game_inc_read_at(data, pool, at)
        spans.append((path, at, n))
        at += n
    # Every earlier file is still intact after the later ones were read.
    for path, start, n in spans:
        f = I.parse(read_bytes(path))
        assert pool[start:start + n] == [T.escape(v) for v in f.values], path
