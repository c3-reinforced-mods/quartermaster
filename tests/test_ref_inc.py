"""Gates for ref.inc: every vanilla `.inc` parses and writes back byte for byte,
and `render` reproduces the files the engine's parser wrote in probes 4 and 5."""
import collections
import os

import pytest

from conftest import DATA_DIR, read_bytes, vanilla_bytes
from ref import inc as I

CRLF = b"\r\n"


def test_every_vanilla_inc_round_trips_byte_identical(vanilla_inc_files):
    assert len(vanilla_inc_files) == 313
    for path in vanilla_inc_files:
        data = read_bytes(path)
        assert I.serialise(I.parse(data)) == data, path


def test_vanilla_forms_and_values(vanilla_inc_files):
    forms = collections.Counter()
    values = 0
    for path in vanilla_inc_files:
        f = I.parse(read_bytes(path))
        forms[f.form] += 1
        values += len(f.values)
        # The parser hands values over with their leading ';'.
        assert all(v.startswith(b";") for v in f.values), path
        assert f.name
    assert forms == {"struct": 294, "single": 10, "none": 9}
    assert values > 60000


def test_code_counts_the_game_reported(game_dir):
    # r5c.0.log:24 "vanilla ... oncamera.inc code lines=73"
    assert len(I.parse(vanilla_bytes("gui/menu.inc/oncamera.inc")).values) == 73
    # r4.0.log:20 "read absolute-path doprogress code lines=1735"
    assert len(I.parse(vanilla_bytes("gui/menu.inc/doprogress.inc")).values) == 1735


def test_values_are_everything_after_the_separator(game_dir):
    f = I.parse(vanilla_bytes("gui/menu.inc/oncamera.inc"))
    assert f.values[0] == b";if (gInterface.gamemode=gc_gamemode_mainmenu) then"
    assert f.values[1] == b";exit;"
    assert f.values[2] == b";"
    assert set(f.prefixes) == {I.CODE_PREFIX}
    assert f.name == b"OnCamera"


def test_odd_vanilla_shapes_survive(game_dir):
    f = I.parse(vanilla_bytes("gui/menu.inc/eventcustomgame.inc"))
    assert b"     [*] = " in f.prefixes            # :174, five spaces
    f = I.parse(vanilla_bytes("gui/menu.inc/initprofile.inc"))
    assert f.form == "single" and f.values == [
        b";_control_SetGameSpeedByMode(gProfile.igamespeed, True);"]
    f = I.parse(vanilla_bytes("gui/menu.inc/eventhud.inc"))
    assert f.form == "none" and f.values == []
    f = I.parse(vanilla_bytes("gui/menu.inc/docreate.inc"))
    assert f.keys[:3] == [b"   Name = DoCreate", b"   Description[*] = ;",
                          b"   UsedFileName = "]


def test_serialise_writes_edited_values_in_place(game_dir):
    data = vanilla_bytes("gui/menu.inc/oncamera.inc")
    f = I.parse(data)
    f.values[1] = b";begin exit; end;"
    out = I.serialise(f)
    assert out == data.replace(b"[*] = ;exit;\r\n", b"[*] = ;begin exit; end;\r\n", 1)


# ----------------------------------------------------------- engine layout
#: The template probe 4 loaded (struct, one value) ...
PROBE4_TEMPLATE = CRLF.join([
    b"section.begin", b"   Name = EventHUD", b"   Code : struct.begin",
    b"      [*] = ;if (gint_hprobe_evh<3) then begin gint_hprobe_evh := "
    b"gint_hprobe_evh+1; Log('HPROBE r4 TEMPLATE EventHUD ran, gamemode='+"
    b"IntToStr(gInterface.gamemode)); end;",
    b"   struct.end", b"section.end", b""]) + CRLF
#: ... and the 328 bytes the engine wrote after value 0 was edited and one value
#: appended with key [*] (r4_generated_eventhud.inc, sha256 26573be9...).
PROBE4_WRITTEN = CRLF.join([
    b"section.begin", b"   Name = EventHUD", b"   Code : struct.begin",
    b"      [*] = ;if (gint_hprobe_evh<3) then begin gint_hprobe_evh := "
    b"gint_hprobe_evh+1; Log('HPROBE r4 PATCHED EventHUD ran, gamemode='+"
    b"IntToStr(gInterface.gamemode)); end;",
    b"      [*] = Log('HPROBE r4 line appended through parser key [*]');",
    b"   struct.end", b"section.end", b""]) + CRLF


def test_render_reproduces_what_the_engine_wrote_in_probe_4():
    t = I.parse(PROBE4_TEMPLATE)
    assert t.form == "struct" and len(t.values) == 1
    values = [t.values[0].replace(b"TEMPLATE", b"PATCHED"),
              b"Log('HPROBE r4 line appended through parser key [*]');"]
    out = I.render(t, values)
    assert len(out) == 328
    assert out == PROBE4_WRITTEN


def test_render_pads_a_shorter_result_with_empty_statements(game_dir):
    f = I.parse(vanilla_bytes("gui/menu.inc/oncamera.inc"))
    out = I.parse(I.render(f, f.values[:70], min_count=73))
    assert out.values == f.values[:70] + [b";"] * 3


def test_render_form_follows_the_number_of_values(game_dir):
    """What ParserSaveToFileByHandle wrote in SelfTest run m2a (incprobe)."""
    # The struct-form onafterload.inc with its one value came back as Code[*].
    f = I.parse(vanilla_bytes("scripts/units/global.inc/onafterload.inc"))
    assert f.form == "struct" and len(f.values) == 1
    assert I.render(f, f.values) == (
        b"section.begin\r\n   Name = OnAfterLoad\r\n   UsedFileName = \r\n"
        b"   Code[*] = ;SwitchTo('Progress');\r\nsection.end\r\n\r\n")
    # A Code[*] file with a second value came back as a struct.
    single = I.parse(vanilla_bytes("gui/menu.inc/initprofile.inc"))
    assert I.render(single, single.values) == vanilla_bytes("gui/menu.inc/initprofile.inc")
    assert I.render(single, [b";// qm edited", b";// qm appended"]) == (
        b"section.begin\r\n   Name = InitProfile\r\n   Code : struct.begin\r\n"
        b"      [*] = ;// qm edited\r\n      [*] = ;// qm appended\r\n"
        b"   struct.end\r\nsection.end\r\n\r\n")
    # A file without Code comes back without one.
    none = I.parse(vanilla_bytes("gui/menu.inc/eventhud.inc"))
    assert I.render(none, []) == vanilla_bytes("gui/menu.inc/eventhud.inc")
    assert I.render(none, [b";x"]).count(b"   Code[*] = ;x\r\n") == 1


def test_engine_values_drop_trailing_spaces(game_dir):
    # ';   ' in doextract.inc reached the game side as ';' (run m2a: 243 bytes
    # of values in-game, 246 in the file).
    f = I.parse(vanilla_bytes("scripts/env/env.inc/doextract.inc"))
    assert b";   " in f.values
    # The dump counts bytes of values plus one LF each.
    assert sum(len(v) + 1 for v in I.engine_values(f)) == 243
    assert sum(len(v) + 1 for v in f.values) == 246


def test_values_from_lines_is_parse_on_the_raw_readers_lines(vanilla_inc_files):
    from ref import textio as T
    for path in vanilla_inc_files:
        data = read_bytes(path)
        f = I.parse(data)
        form, keys, values = I.values_from_lines(T.read_lines(data))
        assert form == f.form, path
        assert keys == [T.escape(k) for k in f.keys], path
        assert values == [T.escape(v) for v in f.values], path


def test_render_raw_is_render_padded(game_dir):
    f = I.parse(vanilla_bytes("gui/menu.inc/oncamera.inc"))
    for n in (0, 1, 2, 70, 73, 76):
        values = (f.values + [b";// qm %d" % k for k in range(10)])[:n]
        raw = I.render_raw(f, values)
        plain = I.render(f, values)
        assert raw == plain + b" " * ((-len(plain)) % 4)


def test_engine_layout_census(vanilla_inc_files):
    """281 vanilla files are exactly what the parser would write back; 13
    others have trailing spaces in Code values, which the parser drops (run
    m2a), one holds a single value in a struct, which the parser writes as
    `Code[*] = `, and the remaining 18 differ in how they end or in one indent. A file of
    either group written by the game side cannot be byte-identical to vanilla
    even where nothing changed."""
    reasons = collections.Counter()
    for path in vanilla_inc_files:
        data = read_bytes(path)
        if I.is_engine_layout(data):
            reasons["engine layout"] += 1
            continue
        f = I.parse(data)
        if f.form == "struct" and set(f.prefixes) != {I.CODE_PREFIX}:
            reasons["code indent"] += 1
        elif I.engine_values(f) != f.values:
            reasons["trailing spaces in values"] += 1
        elif f.form == "struct" and len(f.values) == 1 and data.endswith(CRLF + CRLF):
            reasons["one value in a struct"] += 1
        elif not data.endswith(CRLF):
            reasons["no final CRLF"] += 1
        elif not data.endswith(CRLF + CRLF):
            reasons["no empty last line"] += 1
        else:
            reasons[os.path.relpath(path, DATA_DIR)] += 1
    assert reasons == {"engine layout": 281, "trailing spaces in values": 13,
                       "no final CRLF": 13, "no empty last line": 4, "code indent": 1,
                       "one value in a struct": 1}


@pytest.mark.parametrize("bad", [
    b"",
    b"section.begin\r\n   Name = X\r\n",                         # no section.end
    b"section.begin\r\n   Code : struct.begin\r\n   struct.end\r\nsection.end\r\n",
    b"section.begin\r\n   Name = X\r\n   Code : struct.begin\r\n      x = ;a\r\n"
    b"   struct.end\r\nsection.end\r\n",                          # not [*] =
    b"section.begin\r\n   Name = X\r\n   Code : struct.begin\r\n      [*] = ;a\r\n"
    b"section.end\r\n",                                           # struct not closed
    b"section.begin\r\n   Name = X\r\nsection.end\r\nsection.begin\r\n",
    b"section.begin\r\n   Name = X\r\nsection.end\r\ntrailing\r\n",
])
def test_parse_refuses_shapes_vanilla_never_has(bad):
    with pytest.raises(I.IncFormatError):
        I.parse(bad)


def test_parse_accepts_lf_only_files():
    data = b"section.begin\n   Name = X\n   Code : struct.begin\n      [*] = ;a\n" \
           b"   struct.end\nsection.end\n"
    f = I.parse(data)
    assert f.values == [b";a"] and I.serialise(f) == data
