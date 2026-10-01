r"""What stopped the previous start: the twin of src/states/qmlaststart.pas.

When a start stops at "Error compiling scripts", its log holds one line

    ERROR|  5 |CompileFramework() - compile global script error: Syntax error: Line: 39434, Column: 13: Unknown Name

and nothing of Quartermaster ran (the libraries compile before any state).
The next start that gets as far as Quartermaster reads that log - the second
newest <save>\log\cos_*.log by FileAge, the newest being its own - and maps
the line number onto the libraries the failed start compiled.

The rule (docs/research/context-2026-09-27.md, CompileFramework line numbers):
the libraries compile as one text in the order of the Files list of the
vanilla data\scripts\dmscript.source - a mod's copy of it is not used - after
its Code lines and one more; each library counts its own lines (the copy that
wins in that start, a mod's or vanilla's), and one more line follows each.
The engine's numbers run up to DRIFT lines past that sum (cause unknown), so
the library is found by the number and the number less DRIFT, and the line is
given as a range.

The failed start's mods come from <save>\quartermaster\compile.prev.cfg: the
start-up guard (src/guard/resource.pas) records every start's enabled mods in
load order into compile.cfg before the libraries compile, and moves the
previous record to compile.prev.cfg first. Keys: n, d<k> (dir), t<k> (title).
"""
__all__ = ["ERROR", "DRIFT", "LOG_LINES", "parse_error", "source_layout", "line_count",
           "locate", "boot_line"]

ERROR = b"CompileFramework() - compile global script error: "
#: How far past the summed position the engine's number was seen to run
#: (probe_lines: +14 over the whole framework; a real case +9).
DRIFT = 15
#: The error comes within the first lines of a log; the reader stops here.
LOG_LINES = 400


def _digits(text, at):
    j = at
    while j < len(text) and 48 <= text[j] <= 57:
        j += 1
    return (int(text[at:j]), j) if j > at else (None, at)


def parse_error(line):
    """`(line, column, text)` of a log line with the CompileFramework error,
    or None. The text is what follows the column (`Unknown Name`)."""
    k = line.find(ERROR)
    if k < 0:
        return None
    rest = line[k + len(ERROR):]
    a = rest.find(b"Line: ")
    c = rest.find(b"Column: ")
    if a < 0 or c < 0:
        return None
    n, _j = _digits(rest, a + 6)
    col, j = _digits(rest, c + 8)
    if n is None or col is None:
        return None
    text = rest[j:]
    if text.startswith(b": "):
        text = text[2:]
    return n, col, text.strip(b" ")


def _lines(data):
    return [ln.rstrip(b"\r") for ln in data.split(b"\n")]


def source_layout(data):
    r"""`(code lines, [library file names])` of dmscript.source bytes: the
    `[*] =` lines of its Code struct, and the `lib\<name>` of each Files line."""
    code, libs, where = 0, [], None
    for ln in _lines(data):
        t = ln.strip(b" ")
        if t.startswith(b"Code : struct.begin"):
            where = b"code"
        elif t.startswith(b"Files : struct.begin"):
            where = b"files"
        elif t == b"struct.end":
            where = None
        elif where == b"code" and t.startswith(b"[*] ="):
            code += 1
        elif where == b"files" and t.startswith(b"[*] =") and b"\\" in t:
            libs.append(t[t.rfind(b"\\") + 1:])
    return code, libs


def line_count(data):
    """A library's lines: its LFs, and one more when the last line has none."""
    return data.count(b"\n") + (0 if data.endswith(b"\n") else 1)


def locate(n, code, libs):
    """Where framework line `n` is: `(name, owner, lo, hi, other)` - the
    library, the one whose copy is in effect, its lines lo..hi, and the
    `(name, owner)` whose end the number less DRIFT falls into when that is
    another library (else None). `libs` = [(name, lines, owner)] in Files
    order. None when `n` is before the first library or past the last."""
    at = code + 1
    rows = []
    for name, lines, owner in libs:
        rows.append((name, owner, at + 1, at + lines + 1))   # the line after it too
        at += lines + 1

    def find(m):
        for r in rows:
            if r[2] <= m <= r[3]:
                return r
        return None

    hit = find(n)
    if hit is None:
        return None
    name, owner, start, _end = hit
    hi = n - start + 1
    lo = max(1, hi - DRIFT)
    low = find(n - DRIFT)
    other = (low[0], low[1]) if low is not None and low[0] != name else None
    return name, owner, lo, hi, other


def boot_line(err, where):
    """The report's Boot line (WARN) for `err` = parse_error's result and
    `where` = locate's (or None)."""
    _n, _col, text = err
    head = b"The last start stopped at \"Error compiling scripts\" (" + text + b")"
    if where is None:
        return head + b"; where in the global scripts is not known."
    name, owner, lo, hi, other = where
    out = head + b": most likely scripts\\lib\\" + name + b" of " + owner + (
        b", lines %d-%d." % (lo, hi))
    if other is not None:
        out = out[:-1] + b", or the end of scripts\\lib\\" + other[0] + b" of " + other[1] + b"."
    return out
