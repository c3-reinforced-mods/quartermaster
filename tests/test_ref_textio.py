"""Gates for ref.textio: the raw reader/writer twin, escapes and normalisation.

The in-game numbers asserted here were measured in probe 6 and probe 7
(2026-09-27): logs r6b.0.log:20-47 and r7.0.log:21, and in SelfTest run m2a
(2026-09-28), which disproved the constant EOF filler.
"""
import random

import pytest

from conftest import read_bytes, vanilla_bytes
from ref import textio as T


# ------------------------------------------------------------ the stream itself
def test_integer_stream_matches_the_game_on_a_10_byte_file():
    s = T.IntegerStream(b"ABCDEFGHIJ")
    got = [s.read_integer() for _ in range(5)]
    # r6b.0.log:21-25
    assert got == [1145258561, 1212630597, 19017, 32, 32]


def test_integer_stream_matches_the_game_on_a_12_byte_file():
    s = T.IntegerStream(b"ABCDEFGHIJKL")
    got = [s.read_integer() for _ in range(6)]
    # r6b.0.log:26-31
    assert got == [1145258561, 1212630597, 1280002633, 32, 32, 32]


def test_integer_stream_is_signed_like_the_engine():
    assert T.IntegerStream(b"\xff\xff\xff\xff").read_integer() == -1


def _unsized_read(data, stale):
    """The first game-side reader (probe 6's READ): no size, stop at a zero byte.

    `stale` is the list of values the engine handed back once the stream was
    exhausted, in order. Kept to show what run m2a saw and why it is gone.
    """
    stream = T.IntegerStream(data)
    stale = list(stale)
    lines, cur, done = [], bytearray(), False
    while not done:
        if stream.pos >= len(data):
            stream.stale = stale.pop(0) if len(stale) > 1 else stale[0]
        v = stream.read_integer()
        if v == 0:
            break
        for sh in range(4):
            if done:
                break
            b = (v >> (sh * 8)) & 255
            if b == 0:
                done = True
            elif b == 10:
                lines.append(bytes(cur))
                cur = bytearray()
            elif b != 13:
                cur += bytes([b]) if 32 <= b <= 122 else b"~%03d" % b
    if cur == b" ":
        cur = bytearray()
    if cur:
        lines.append(bytes(cur))
    return lines


def test_what_run_m2a_saw_is_the_stale_value_past_the_end(game_dir):
    # video.lib is 64 bytes and ends in CR LF: the read after the last integer
    # returned 4, so the unsized reader gained a line ~004 (rt4.txt: 68 bytes
    # instead of 64, ending 04 0D 0A 20).
    data = vanilla_bytes("video/video.lib")
    assert len(data) == 64
    old = _unsized_read(data, [4])
    assert old == T.read_lines(data) + [b"~004"]
    assert T.write_file(old)[-4:] == b"\x04\r\n "
    # The empty hud\bar.load.menu.cfg: the first read returned 0x0C66A540,
    # the next 4; rt1.txt held 40 A5 66 0C 04 0D 0A 20.
    old = _unsized_read(b"", [0x0C66A540, 4])
    assert T.write_file(old) == bytes.fromhex("40a5660c040d0a20")
    # Probe 6's reads past the end returned 32, which is how the filler
    # model came about: the same reader then gains a trailing space.
    assert _unsized_read(b"abcd", [32]) == [b"abcd "]


# ------------------------------------------------------------- the end of a file
@pytest.mark.parametrize("data, lines", [
    (b"abc", [b"abc"]),
    (b"abcd", [b"abcd"]),                    # 4 % 4 == 0, no LF: nothing added
    (b"abc\n", [b"abc"]),
    (b"ab\r\n", [b"ab"]),                    # CRLF, CR dropped
    (b"abcdefg\r\n", [b"abcdefg"]),
    (b"abcde\r\nfg", [b"abcde", b"fg"]),
    (b"abcde\r\nfgh", [b"abcde", b"fgh"]),
    (b"", []),
    (b" ", [b" "]),                          # a real last space is a real line
    (b"    ", [b"    "]),
    (b"a\r\n\r\nb", [b"a", b"", b"b"]),
    (b"a\x00bcdefgh\n", [b"a"]),             # stops at the first zero byte
    (b"x\ry\r\n", [b"xy"]),                  # bare CR is dropped, not a line end
])
def test_reader_end_of_file(data, lines):
    assert T.read_lines(data) == lines
    for stale in T.STALE_SEEN + (0, -1):
        assert T.read_lines_by_integers(data, stale=stale) == lines, stale


def test_sized_reader_adds_nothing_whatever_the_stale_value():
    for n in range(0, 40):
        data = b"x" * n
        want = [b"x" * n] if n else []
        assert T.read_raw_lines(data) == want, n
        for stale in T.STALE_SEEN + (0x0A0A0A0A, 0x7A7A7A7A):
            assert T.read_lines_by_integers(data, stale=stale) == want, (n, stale)


def test_reader_integer_cap():
    data = b"abcdefgh" * 3
    assert T.read_lines(data, max_integers=3) == [b"abcdefghabcd"]
    assert T.read_lines_by_integers(data, max_integers=3) == [b"abcdefghabcd"]


def test_fast_reader_equals_statement_by_statement_reader_on_random_buffers():
    rng = random.Random(20260928)
    alphabet = b"ab \t\r\n~{\x00\xe9\xff"
    for case in range(3000):
        n = rng.randint(0, 40)
        data = bytes(rng.choice(alphabet) for _ in range(n))
        cap = rng.choice([T.MAX_INTEGERS, 1, 2, 3, 5])
        stale = rng.choice(T.STALE_SEEN + (0, 0x0A0D0A0D))
        assert T.read_lines(data, cap) == T.read_lines_by_integers(data, cap, stale), (
            case, data, cap, stale)


# ------------------------------------------------------ in-game line counts
def test_init_script_reads_as_the_game_read_it(game_dir):
    data = vanilla_bytes("scripts/lib/init.script")
    lines = T.read_lines(data)
    # r6b.0.log:34: "lib read init.script lines=258 ... line0=//"
    assert len(lines) == 258
    assert lines[0] == b"//"
    # 11328 bytes, no final LF: read with its size, the last line is exactly
    # the file's (the unsized reader of probe 6 added a stale byte to it).
    assert len(data) % 4 == 0 and not data.endswith(b"\n")
    assert lines[-1] == data.rsplit(b"\n", 1)[1]


def test_objcustom_cfg_reads_as_the_game_read_it(game_dir):
    lines = T.read_lines(vanilla_bytes("game/var/objcustom.cfg"))
    # r6b.0.log:47: "objcustom.cfg read as text lines=51586 ... last=section.end"
    assert len(lines) == 51586
    assert lines[-1] == b"section.end"


def test_cameracontrol_reads_as_the_game_read_it(game_dir):
    # r7.0.log:21: "wrote 3 validation copies of cameracontrol, lines=38"
    assert len(T.read_lines(vanilla_bytes("gui/menu.inc/cameracontrol.inc"))) == 38


def test_oncamera_code_lines_as_the_game_counted_them(game_dir):
    lines = T.read_lines(vanilla_bytes("gui/menu.inc/oncamera.inc"))
    # r6b.0.log:38: 77 = 2 header + 73 lines containing '[*] = ;' + 2 footer
    assert sum(1 for t in lines if b"[*] = ;" in t) == 73


# --------------------------------------------------------------- escaping
def test_table_is_32_to_122():
    assert T.CHAR_TABLE == bytes(range(32, 123))
    assert T.CHAR_TABLE[0:1] == b" " and T.CHAR_TABLE[-1:] == b"z"


def test_every_byte_escapes_and_comes_back():
    for b in range(256):
        e = T.escape(bytes([b]))
        if 32 <= b <= 122:
            assert e == bytes([b])
        else:
            assert e == b"~%03d" % b
        assert T.unescape(e) == bytes([b])


@pytest.mark.parametrize("bad", [b"~", b"~12", b"~1a3", b"~256", b"a\tb", b"\xe9",
                                 b"~~123"])
def test_unescape_refuses_malformed_text(bad):
    with pytest.raises(ValueError):
        T.unescape(bad)


def test_escape_round_trip_on_every_vanilla_inc(vanilla_inc_files):
    assert len(vanilla_inc_files) == 313
    for path in vanilla_inc_files:
        for line in read_bytes(path).split(b"\n"):
            e = T.escape(line)
            assert set(e) <= set(T.CHAR_TABLE) | {ord("~")}
            assert T.unescape(e) == line, path


def test_reader_twins_agree_on_every_vanilla_inc(vanilla_inc_files):
    for path in vanilla_inc_files:
        data = read_bytes(path)
        assert T.read_lines(data) == T.read_lines_by_integers(data), path


@pytest.mark.slow
def test_escape_round_trip_on_every_vanilla_text_file(vanilla_text_files):
    assert len(vanilla_text_files) >= 4300
    for path in vanilla_text_files:
        data = read_bytes(path)
        e = T.escape(data)
        assert set(e) <= set(T.CHAR_TABLE) | {ord("~")}, path
        assert T.unescape(e) == data, path


@pytest.mark.slow
def test_reader_twins_agree_on_every_vanilla_text_file(vanilla_text_files):
    for path in vanilla_text_files:
        data = read_bytes(path)
        assert T.read_lines(data) == T.read_lines_by_integers(data), path


@pytest.mark.slow
def test_read_then_write_reproduces_every_crlf_vanilla_text_file(vanilla_text_files):
    """For a file whose line ends are all CRLF, the writer gives the file back:
    exactly, plus padding, when it ends in CRLF; with a CRLF added when it does
    not. These are the bytes the game writes for what it read with the file's
    size (probe 6's unsized reader added a stale byte instead)."""
    ended = unended = 0
    for path in vanilla_text_files:
        data = read_bytes(path)
        if data.count(b"\n") != data.count(b"\r\n") \
                or data.count(b"\r") != data.count(b"\r\n") or not data:
            continue
        if len(data) >= 4 * T.MAX_INTEGERS:
            # pattern.lib: the reader's loop bound ends the read at 8 MB, and the
            # file is far over the 60k-line cap anyway (winner-takes-all).
            assert T.read_lines(data) == T.read_lines(data[:4 * T.MAX_INTEGERS])
            continue
        if data.endswith(b"\r\n"):
            want = data
            ended += 1
        else:
            want = data + b"\r\n"
            unended += 1
        written = T.write_file(T.read_lines(data))
        assert written == want + b" " * ((-len(want)) % 4), path
    # 2988 + 1226 on 2026-09-28; a floor keeps the gate from passing vacuously.
    assert ended >= 2900 and unended >= 1200


# ------------------------------------------------------------------ writer
def test_writer_pads_to_whole_integers_and_writes_crlf():
    assert T.write_file([b"ab"]) == b"ab\r\n"
    assert T.write_file([b"abc"]) == b"abc\r\n   "
    assert T.write_file([b"a~009b"]) == b"a\tb\r\n   "
    assert T.write_file([]) == b""
    for n in range(12):
        assert len(T.write_file([b"x" * n])) % 4 == 0


def test_readback_of_a_padded_file_gains_one_whitespace_line():
    rng = random.Random(7)
    for _ in range(500):
        lines = [T.escape(bytes(rng.choice(b"ab\t ") for _ in range(rng.randint(0, 9))))
                 for _ in range(rng.randint(0, 6))]
        back = T.read_lines(T.write_file(lines))
        extra = T.readback_extra_line(lines)
        assert back == lines + ([extra] if extra else []), lines


# ------------------------------------------------------------- normalisation
def test_norm_key_rules():
    assert T.norm_key(b"\xef\xbb\xbfsection.begin", first=True) == b"section.begin"
    assert T.norm_key(b"\xef\xbb\xbfx") == b"\xef\xbb\xbfx"      # BOM only on line 0
    assert T.norm_key(b"a := 1;  \t ") == b"a := 1;"
    assert T.norm_key(b"\tif x then") == b" if x then"
    assert T.norm_key(b"a\r") == b"a"
    assert T.norm_key(b"   x") == b"   x"                        # leading kept


def test_norm_key_escaped_is_norm_key_on_the_internal_form():
    rng = random.Random(3)
    alphabet = b"ab \t;~\xef\xbb\xbf"
    for _ in range(3000):
        raw = bytes(rng.choice(alphabet) for _ in range(rng.randint(0, 12)))
        first = rng.random() < 0.5
        assert T.norm_key_escaped(T.escape(raw), first) == T.escape(
            T.norm_key(raw, first)), raw


def test_norm_key_escaped_on_every_vanilla_inc_line(vanilla_inc_files):
    for path in vanilla_inc_files:
        for i, raw in enumerate(T.read_raw_lines(read_bytes(path))):
            assert T.norm_key_escaped(T.escape(raw), i == 0) == T.escape(
                T.norm_key(raw, i == 0)), path


# --------------------------------------------------------- compared form
def test_compared_form_does_not_see_the_readback_line():
    """plan S8: a file this writer wrote must compare equal to the lines it was
    written from, or "restart only if an output's bytes changed" never settles."""
    rng = random.Random(7)
    for _ in range(3000):
        lines = [T.escape(bytes(rng.choice(b"ab \t\xe9~") for _ in range(rng.randint(0, 6))))
                 for _ in range(rng.randint(0, 5))]
        back = T.read_lines(T.write_file(lines))
        assert T.compare_form(back) == T.compare_form(lines), lines
        if T.readback_extra_line(lines):
            assert len(back) == len(lines) + 1


def test_compared_form_rules():
    assert T.compare_form([b"~239~187~191a~009 ", b"b  ", b"", b"   "]) == [b"a", b"b"]
    assert T.compare_form([b"", b"x", b""]) == [b"", b"x"]
    assert T.compare_form([b"  ", b" "]) == []
    # A BOM only counts on the first line.
    assert T.compare_form([b"a", b"~239~187~191b"]) == [b"a", b"~239~187~191b"]


def test_compared_form_survives_a_rewrite_of_every_vanilla_inc(vanilla_inc_files):
    for path in vanilla_inc_files:
        lines = T.read_lines(read_bytes(path))
        assert T.compare_form(T.read_lines(T.write_file(lines))) == T.compare_form(lines), path


@pytest.mark.slow
def test_compared_form_survives_a_rewrite_of_every_vanilla_text_file(vanilla_text_files):
    for path in vanilla_text_files:
        lines = T.read_lines(read_bytes(path))
        assert T.compare_form(T.read_lines(T.write_file(lines))) == T.compare_form(lines), path
