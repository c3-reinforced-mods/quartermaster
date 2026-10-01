r"""Raw text IO: the twin of the in-game 4-byte reader and writer.

The engine has no byte-level file API. A script can only call
`FileStreamReadInteger` and `FileStreamWriteInteger` (4 bytes, little endian),
and `Chr` does not compile in any form, so a byte read from a file cannot be
turned back into a character directly. The game-side reader therefore keeps a
character table for bytes 32..122 (`SubStr(table, b-31, 1)`) and spells every
other byte as `~NNN` (three decimal digits) inside its strings. `~` itself is 126,
outside the table, so it is always escaped and every `~` in an internal string
starts an escape - the form is unambiguous.

The end of a file, and why the reader is told the file's size
----------------------------------------------------------------
Believed after probe 6 (2026-09-27, r6b.0.log:20-32): a read that starts
inside the last 4 bytes returns the remaining bytes with the high bytes zero,
and every read after that returns the constant 32. The first game-side reader
relied on it and stopped at the first zero byte.

What it cost: SelfTest run m2a (2026-09-28) read 333 vanilla files that way.
Every file whose length is a multiple of 4 came back with extra bytes at the
end - the read after the last integer returned 4, so the file gained a line
`~004` (onmousewheel.inc: 343 lines, not 342; rt4.txt 68 bytes, not 64) -
and the empty hud\bar.load.menu.cfg read as `@~165f~012~004` (the first read
returned 0x0C66A540, the next 4).

What is true: `FileStreamReadInteger` does not report the end of the stream.
Past the end it returns whatever its result held before - 32 in probe 6's
logging loop, 4 in the reader's loop, a pointer-like value right after the
stream was opened - so nothing read past the end means anything. A partial
read (1-3 bytes left) has the real bytes in the low positions and had zero
high bytes in both runs; whether those come from the stale value too (4 and
32 have zero high bytes) is not known, so they are not relied on either.

So the reader is given the file's size and reads exactly that many bytes:
`size div 4` whole integers, then, when `size mod 4` > 0, one more integer of
which only the low `size mod 4` bytes are used. It never reads past the end.
Vanilla files' sizes are in vanilla.idx; a file Quartermaster wrote itself has
the size its writer reports (`written_size`). A file of unknown size cannot be
read exactly this way (the SelfTest's `eofprobe` checks whether the
handle-based `ReadInteger(fs, var val)` can tell the end).

The reader (and this twin) drops every CR, splits on LF, stops at a zero byte
(text has none) and reads at most 2,000,000 integers (8 MB); a last line
without LF is kept when it is not empty. The line counts of probe 6 still
hold for it: init.script reads as 258 lines starting with `//` (r6b.0.log:34),
objcustom.cfg as 51586 lines ending in `section.end` (r6b.0.log:47).

The writer is the mirror image: each line, unescaped, then CR LF, and the final
partial integer is padded with spaces up to a multiple of 4. Read back exactly,
the 1-3 padding spaces are one more last line (`readback_extra_line`), which
the compared form (`compare_form`) does not count.

Comparison is not done on these bytes. `norm_key` gives the key two lines are
compared by: BOM dropped on the first line, CR dropped, tabs read as spaces,
trailing whitespace removed. What is written is always the bytes of the line the
merge chose, with CRLF.
"""
import re

__all__ = ["TABLE_FIRST", "TABLE_LAST", "CHAR_TABLE", "ESCAPE", "STALE_SEEN",
           "MAX_INTEGERS", "BOM", "IntegerStream", "escape", "unescape",
           "read_lines_by_integers", "read_lines", "read_raw_lines",
           "write_file", "written_size", "readback_extra_line", "norm_key",
           "norm_key_escaped", "compare_form"]

#: The character table of the game-side reader covers bytes 32..122, space to
#: `z`. That is the string the verified reader builds (probe 6), and why `{`, `|`,
#: `}` and `~` are escaped although they are printable.
TABLE_FIRST = 32
TABLE_LAST = 122
CHAR_TABLE = bytes(range(TABLE_FIRST, TABLE_LAST + 1))

ESCAPE = b"~"

#: Values `FileStreamReadInteger` returned past the end of a stream: 32 in
#: probe 6, 4 and 0x0C66A540 in run m2a. Not a constant - see the docstring.
STALE_SEEN = (32, 4, 0x0C66A540)

#: The verified reader's loop bound: `while (not rdDone) and (rdInts<2000000)`.
MAX_INTEGERS = 2_000_000

BOM = b"\xef\xbb\xbf"

_ESCAPED = [bytes([b]) if TABLE_FIRST <= b <= TABLE_LAST else b"~%03d" % b
            for b in range(256)]
_OUTSIDE_TABLE = re.compile(rb"[^\x20-\x7a]")
_ESCAPE_SEQ = re.compile(rb"~(\d{3})")


class IntegerStream(object):
    """`OpenFileStreamForRead` + `FileStreamReadInteger` over a byte buffer.

    `stale` is what the engine's result held before the call: past the end it
    is returned as it is, and a partial read keeps its high bytes. With a
    stale 32 this reproduces probe 6 (`IJ` of a 10-byte file read as 19017 =
    0x4A49, then 32, r6b.0.log:22-24).
    """

    def __init__(self, data, stale=32):
        self.data = bytes(data)
        self.pos = 0
        self.stale = stale & 0xFFFFFFFF

    def read_integer(self):
        n = len(self.data)
        if self.pos + 4 <= n:
            chunk = self.data[self.pos:self.pos + 4]
            self.pos += 4
        else:
            old = self.stale.to_bytes(4, "little")
            got = self.data[self.pos:]
            chunk = got + old[len(got):]
            self.pos = n
        return int.from_bytes(chunk, "little", signed=True)


def escape(raw):
    """Raw bytes of one line -> the reader's internal string."""
    if not _OUTSIDE_TABLE.search(raw):
        return bytes(raw)
    return _OUTSIDE_TABLE.sub(lambda m: _ESCAPED[m.group()[0]], raw)


def unescape(text):
    """The reader's internal string -> raw bytes. Refuses a malformed escape."""
    if _OUTSIDE_TABLE.search(text.replace(ESCAPE, b"")):
        raise ValueError("byte outside the character table in %r" % text[:60])
    if ESCAPE not in text:
        return bytes(text)
    out = bytearray()
    pos = 0
    for m in _ESCAPE_SEQ.finditer(text):
        if ESCAPE in text[pos:m.start()]:
            raise ValueError("'~' without three digits in %r" % text[:60])
        value = int(m.group(1))
        if value > 255:
            raise ValueError("escape ~%03d is not a byte" % value)
        out += text[pos:m.start()]
        out.append(value)
        pos = m.end()
    if ESCAPE in text[pos:]:
        raise ValueError("'~' without three digits in %r" % text[:60])
    out += text[pos:]
    return bytes(out)


def read_lines_by_integers(data, max_integers=MAX_INTEGERS, stale=32):
    """The game-side reader (src/lib/qmraw.pas qmRawRead), statement for statement.

    It is told the size (here `len(data)`), reads `size div 4` whole integers
    and, for `size mod 4` > 0, one more of which it uses the low bytes only.
    Slow on purpose: it is the specification `read_lines` is proven against,
    for any `stale` value the engine may hand back.
    """
    size = len(data)
    stream = IntegerStream(data, stale)
    total = size // 4 + (1 if size % 4 else 0)
    lines = []
    cur = bytearray()
    done = False
    ints = 0
    while not done and ints < total and ints < max_integers:
        v = stream.read_integer()
        count = size % 4 if (ints == total - 1 and size % 4) else 4
        ints += 1
        for sh in range(count):
            if done:
                break
            b = (v >> (sh * 8)) & 255
            if b == 0:
                done = True
            elif b == 10:
                lines.append(bytes(cur))
                cur = bytearray()
            elif b != 13:
                if TABLE_FIRST <= b <= TABLE_LAST:
                    cur.append(b)
                else:
                    cur += b"~%03d" % b
    if cur:
        lines.append(bytes(cur))
    return lines


def read_lines(data, max_integers=MAX_INTEGERS):
    """What the in-game reader returns for `data`, as internal (escaped) strings.

    Same result as `read_lines_by_integers`, computed on whole buffers.
    """
    seen = data[:4 * max_integers]
    nul = seen.find(b"\x00")
    if nul >= 0:
        seen = seen[:nul]
    parts = seen.replace(b"\r", b"").split(b"\n")
    lines = parts[:-1]
    if parts[-1]:
        lines.append(parts[-1])
    return [escape(line) for line in lines]


def read_raw_lines(data, max_integers=MAX_INTEGERS):
    """`read_lines`, unescaped - the bytes of each line the game would hold."""
    return [unescape(t) for t in read_lines(data, max_integers)]


def write_file(lines):
    """Bytes the verified writer produces for internal strings `lines`.

    Each line unescaped plus CR LF; the last partial integer padded with spaces,
    because only whole integers can be written (probe 6 `WRITE`).
    """
    out = bytearray()
    for text in lines:
        out += unescape(text)
        out += b"\r\n"
    out += b" " * ((-len(out)) % 4)
    return bytes(out)


def written_size(lines):
    """Bytes `write_file(lines)` makes: what the game-side writer reports, so the
    file can be read back with its exact size."""
    unpadded = sum(len(unescape(t)) + 2 for t in lines)
    return unpadded + (-unpadded) % 4


def readback_extra_line(lines):
    """The line `read_lines(write_file(lines))` has in excess of `lines`, or None.

    The 1-3 padding spaces after the final CR LF, read back exactly.
    """
    unpadded = sum(len(unescape(t)) + 2 for t in lines)
    pad = (-unpadded) % 4
    return b" " * pad if pad else None


def norm_key(line, first=False):
    """The key a line is compared by. `first`: this is the file's first line."""
    if first and line.startswith(BOM):
        line = line[len(BOM):]
    return line.replace(b"\r", b"").replace(b"\t", b" ").rstrip(b" ")


def norm_key_escaped(text, first=False):
    """`norm_key` on the reader's internal form - the version the game computes.

    BOM is `~239~187~191`, a tab `~009`; CR never reaches an internal string.
    """
    if first and text.startswith(b"~239~187~191"):
        text = text[12:]
    return _replace_escape(text, 9, b" ").rstrip(b" ")


def compare_form(lines):
    """The lines two versions of a file are compared by, as internal strings.

    `norm_key_escaped` on every line, then trailing empty lines dropped. The
    second step is what keeps plan S8's "restart only if an output's bytes
    changed" from looping: a file this writer wrote reads back with an extra
    last line of 1-3 padding spaces (`readback_extra_line`), which normalises
    to an empty line and must not count as a change. A file that ends in
    blank lines and one that does not therefore compare equal; the engine's
    parser skips blank lines, so no output differs by them alone.
    """
    out = [norm_key_escaped(t, i == 0) for i, t in enumerate(lines)]
    while out and not out[-1]:
        out.pop()
    return out


def _replace_escape(text, byte, new):
    # A plain replace of b"~009" could match across a boundary only if a '~'
    # could be data, and it cannot: every '~' starts an escape.
    return text.replace(b"~%03d" % byte, new)
