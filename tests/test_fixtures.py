"""Gates for tools/fixtures.py: the four test mods of docs/plan.md section 4."""
import os
import re
import subprocess
import sys

import pytest

from conftest import REPO, read_bytes
from ref import inc as I
from ref import merge as M

CRLF = b"\r\n"


@pytest.fixture(scope="module")
def F():
    import fixtures
    return fixtures


@pytest.fixture(scope="module")
def mods(F, game_dir, reference_dir):
    return F.build_all(game_dir, reference_dir)


def test_the_fixtures_with_the_planned_files(F, mods):
    assert {n: sorted(files) for n, files in mods.items()} == {
        F.WASD: sorted([F.REGISTERSHORTCUTS, F.ONCAMERA, F.HOTKEYSETTINGS,
                        F.HOTKEYS_CFG, "mod.ini"]),
        F.CAMSPEED: sorted([F.ONCAMERA, F.REGISTERSHORTCUTS, "mod.ini"]),
        F.CONFLICT: sorted([F.ONCAMERA, "mod.ini"]),
        F.BROKEN: sorted([F.REGISTERSHORTCUTS, "mod.ini"]),
        F.WASD2: sorted([F.REGISTERSHORTCUTS, F.ONCAMERA, F.HOTKEYSETTINGS,
                         F.HOTKEYS_CFG, "about.cfg", "mod.ini"]),
        F.CAM2: ["about.cfg", "mod.ini"],
        F.DATA_A: sorted([F.FORMATIONS_CFG, F.OBJCUSTOM_CFG, "mod.ini"]),
        F.DATA_B: sorted([F.FORMATIONS_CFG, F.OBJCUSTOM_CFG, "mod.ini"]),
        F.DATA_A6: sorted([F.FORMATIONS_CFG, "mod.ini"]),
        F.DATA_B6: sorted([F.FORMATIONS_CFG, "mod.ini"]),
    }


def test_wasd2_is_wasd_with_its_keys_read_from_the_settings(F, mods):
    """Phase B, M10: the same files as QMTestWASD but for the key names, which
    come from qm_settings; its about.cfg declares the four keys it reads."""
    from ref import about as A
    w, w2 = mods[F.WASD], mods[F.WASD2]
    assert w2[F.HOTKEYS_CFG] == w[F.HOTKEYS_CFG] and w2[F.HOTKEYSETTINGS] == w[F.HOTKEYSETTINGS]
    a = A.parse(w2["about.cfg"])
    assert a.problems == [] and a.id == b"qmtestwasd2" and a.exclusive == [b"camera"]
    assert [(s.id, s.kind, s.default) for s in a.settings] == [
        (b"camera_left", b"key", b"A"), (b"camera_right", b"key", b"D"),
        (b"camera_up", b"key", b"W"), (b"camera_down", b"key", b"S")]
    rs, oc = w2[F.REGISTERSHORTCUTS], w2[F.ONCAMERA]
    assert b"'A', filter," not in rs and rs.count(b"qmwasdkl, filter,") == 2
    assert b"IsKeyDownByName('A')" not in oc and b"IsKeyDownByName(qmwasdol)" in oc
    for sid in (b"camera_left", b"camera_right", b"camera_up", b"camera_down"):
        assert (b"'%s'" % sid) in rs and (b"'%s'" % sid) in oc


def test_the_data_fixtures_are_the_record_layout(F, mods):
    """Phase B, M9: each data fixture is a file the game can load - split
    into its records - with the formations the check of run m9 counts."""
    from ref import records as R
    from ref import textio as T
    want = {F.DATA_A: 150, F.DATA_B: 150, F.DATA_A6: 155, F.DATA_B6: 155}
    for name, count in want.items():
        data = mods[name][F.FORMATIONS_CFG]
        sp = R.split(T.read_lines(data), R.PROFILES[b"game\\var\\formations.cfg"])
        assert sp is not None and len(sp.records) == count, name
        assert R.check(sp, R.PROFILES[b"game\\var\\formations.cfg"]) == b""
    for name in (F.DATA_A, F.DATA_B):
        sp = R.split(T.read_lines(mods[name][F.OBJCUSTOM_CFG]), R.PROFILES[b"game\\var\\objcustom.cfg"])
        assert sp is not None and len(sp.records) == 244, name


def test_every_fixture_file_is_crlf_like_vanilla(mods):
    for name, files in mods.items():
        for rel, data in files.items():
            assert data.count(b"\n") == data.count(CRLF), (name, rel)
            assert data.count(b"\r") == data.count(CRLF), (name, rel)
            # vanilla's formations.cfg ends without a line break after
            # section.end; the data fixtures keep its bytes
            assert data.endswith(CRLF) or rel.endswith("formations.cfg"), (name, rel)


def test_inc_fixtures_parse_and_keep_the_engine_layout(F, mods, game_dir):
    for name, files in mods.items():
        for rel, data in files.items():
            if rel.endswith(".inc"):
                assert I.is_engine_layout(data), (name, rel)
                assert I.is_engine_layout(F.vanilla(game_dir, rel))


def test_mod_ini_has_the_layout_of_an_existing_local_mod(F, mods, reference_dir):
    def shape(data):
        rows = []
        for line in data.split(CRLF):
            if line == b"":
                rows.append(b"")
                continue
            m = re.match(rb"^( *)([A-Za-z_.\[\]*]+)( = |$)", line)
            assert m, line
            rows.append((m.group(1), m.group(2), m.group(3)))
        return rows

    reference = read_bytes(os.path.join(reference_dir, "mod.ini"))
    for name, files in mods.items():
        ini = files["mod.ini"]
        assert shape(ini) == shape(reference), name
        assert b"   title = " + name.encode() + CRLF in ini
        assert b"   contentfolder = mods\\" + name.encode() + CRLF in ini
        assert b"   description[*] = ;TODO(owner)" + CRLF in ini
        assert ini.endswith(b"section.end" + CRLF + CRLF)


def test_wasd_is_the_reference_mods_camera_with_the_prefix_renamed(F, mods,
                                                                   reference_dir):
    """The reference mod ships the output of the same functions for this game
    version in its own data folder - an independent check of the import."""
    wasd = mods[F.WASD]
    for rel in (F.REGISTERSHORTCUTS, F.ONCAMERA, F.HOTKEYSETTINGS, F.HOTKEYS_CFG):
        shipped = os.path.join(reference_dir, *rel.split("/"))
        if not os.path.isfile(shipped):
            pytest.skip("reference mod has no %s" % rel)
        want = read_bytes(shipped).replace(b"swfpcamera", b"qmwasd")
        got = wasd[rel]
        if rel == F.REGISTERSHORTCUTS:
            got = got.replace(F.WASD_MARKER, b"", 1)
        assert got == want, rel
    assert all(b"swfpcamera" not in data for data in wasd.values())
    assert wasd[F.REGISTERSHORTCUTS].count(b"qmwasd") == 8


def test_each_fixture_changes_only_what_it_claims(F, mods, game_dir):
    """Hunks of each fixture file against vanilla, with the plan's edits."""
    def hunks(name, rel):
        vanilla = F.vanilla(game_dir, rel)
        if rel.endswith(".inc"):
            r, _ = M.merge_inc(vanilla, [(name.encode(), mods[name][rel])])
        else:
            r, _ = M.merge_text(vanilla, [(name.encode(), mods[name][rel])])
        return [(h.start, h.end, len(h.lines)) for h in r.hunks]

    assert hunks(F.WASD, F.ONCAMERA) == [(14, 18, 6)]
    assert hunks(F.WASD, F.REGISTERSHORTCUTS) == [(14, 14, 13), (196, 196, 23)]
    assert hunks(F.WASD, F.HOTKEYSETTINGS) == [(28, 28, 8)]
    assert len(hunks(F.WASD, F.HOTKEYS_CFG)) == 6
    assert hunks(F.CAMSPEED, F.ONCAMERA) == [(1, 2, 1), (6, 7, 1)]
    assert hunks(F.CAMSPEED, F.REGISTERSHORTCUTS) == [(0, 0, 1)]
    assert hunks(F.CONFLICT, F.ONCAMERA) == [(14, 15, 1)]
    assert hunks(F.BROKEN, F.REGISTERSHORTCUTS) == [(192, 192, 1)]


def test_markers(F, mods):
    assert b"Log('QMTEST wasd');" in mods[F.WASD][F.REGISTERSHORTCUTS]
    assert b"Log('QMTEST camspeed');" in mods[F.CAMSPEED][F.ONCAMERA]
    assert b"Log('QMTEST camspeed registershortcuts');" in mods[F.CAMSPEED][
        F.REGISTERSHORTCUTS]
    assert b"// QMTEST conflict" in mods[F.CONFLICT][F.ONCAMERA]
    assert b"// QMTEST broken" in mods[F.BROKEN][F.REGISTERSHORTCUTS]


def test_build_is_deterministic(F, mods, game_dir, reference_dir):
    assert F.build_all(game_dir, reference_dir) == mods


def test_write_then_check(F, mods, game_dir, tmp_path):
    out = str(tmp_path / "fixtures")
    F.write(mods, out, game_dir)
    assert F.check(mods, out) == []
    for name, files in mods.items():
        assert F.read_tree(os.path.join(out, name)) == files
    # A stray file inside a fixture folder is reported, and removed by a rebuild.
    stray = os.path.join(out, F.WASD, "data", "stray.txt")
    with open(stray, "wb") as f:
        f.write(b"x")
    assert F.check(mods, out) == ["%s/data/stray.txt" % F.WASD]
    F.write(mods, out, game_dir)
    assert not os.path.exists(stray)


def test_refuses_to_write_inside_the_game_folder(F, mods, game_dir):
    for target in (os.path.join(game_dir, "mods"), game_dir):
        with pytest.raises(F.FixtureError):
            F.write(mods, target, game_dir)


def snapshot(root):
    """Names, file sizes and mtimes; directory mtimes change when an entry is
    added or removed, which is what a stray __pycache__ would do."""
    out = {}
    for dirpath, dirs, names in os.walk(root):
        for d in dirs:
            p = os.path.join(dirpath, d)
            out[p + os.sep] = os.stat(p).st_mtime_ns
        for n in names:
            p = os.path.join(dirpath, n)
            st = os.stat(p)
            out[p] = (st.st_size, st.st_mtime_ns)
    return out


def test_building_writes_nothing_into_the_reference_mod(reference_dir, tmp_path):
    """Run the CLI in a fresh interpreter WITHOUT PYTHONDONTWRITEBYTECODE, so the
    script's own guard is what keeps the reference mod's tools clean."""
    tools = os.path.join(reference_dir, "tools")
    before = snapshot(tools)
    env = dict(os.environ)
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    proc = subprocess.run(
        [sys.executable, os.path.join(REPO, "tools", "fixtures.py"),
         "--out", str(tmp_path / "fx")],
        cwd=str(tmp_path), env=env, capture_output=True, timeout=120)
    assert proc.returncode == 0, proc.stderr.decode(errors="replace")
    assert b"wrote 10 fixtures" in proc.stdout
    assert os.path.isfile(str(tmp_path / "fx" / "QMTestWASD" / "mod.ini"))
    assert snapshot(tools) == before
