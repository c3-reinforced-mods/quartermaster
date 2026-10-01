"""Gates for ref.records (plan S3, S10; M9): the record layout on the
installed game's own files and on every mod's copy of them, and the merge
rules on edits built from vanilla's bytes."""
import glob
import os

import pytest

from ref import records as R
from ref import textio as T

REL = {b"game\\var\\hotkeys.cfg": "hotkeys.cfg", b"game\\var\\objcustom.cfg": "objcustom.cfg",
       b"game\\var\\wallcustom.cfg": "wallcustom.cfg", b"game\\var\\formations.cfg": "formations.cfg"}


def vanilla(game_dir, name):
    with open(os.path.join(game_dir, "data", "game", "var", name), "rb") as fh:
        return T.read_lines(fh.read())


@pytest.mark.parametrize("path", sorted(REL))
def test_vanilla_splits_and_joins_back(game_dir, path):
    lines = vanilla(game_dir, REL[path])
    sp = R.split(lines, R.PROFILES[path])
    assert sp is not None and R.join(sp) == lines
    assert R.check(sp, R.PROFILES[path]) == b""
    # objcustom.cfg: 244 - three records open with `[*]: struct.begin` (:26641).
    counts = {b"game\\var\\hotkeys.cfg": 55, b"game\\var\\objcustom.cfg": 244,
              b"game\\var\\wallcustom.cfg": 17, b"game\\var\\formations.cfg": 149}
    assert len(sp.records) == counts[path]


def test_every_installed_mod_s_copy_is_the_layout_or_refused(game_dir):
    """The Workshop and local mods of this machine: a copy either splits and
    joins back byte for byte, or split says None (then the winner's file)."""
    roots = glob.glob(os.path.join(os.path.dirname(os.path.dirname(game_dir)), "workshop",
                                   "content", "333420", "*"))
    roots += glob.glob(os.path.join(game_dir, "mods", "*"))
    seen = 0
    for root in roots:
        for path, name in REL.items():
            f = os.path.join(root, "data", "game", "var", name)
            if not os.path.isfile(f):
                continue
            with open(f, "rb") as fh:
                lines = T.read_lines(fh.read())
            sp = R.split(lines, R.PROFILES[path])
            if sp is not None:
                assert R.join(sp) == lines, f
            seen += 1
    assert seen >= 5


def edit(lines, old, new):
    i = lines.index(old)
    return lines[:i] + new + lines[i + 1:]


def records_of(lines, path):
    return R.split(lines, R.PROFILES[path])


HK = b"game\\var\\hotkeys.cfg"
FORM = b"game\\var\\formations.cfg"
OBJ = b"game\\var\\objcustom.cfg"
WALL = b"game\\var\\wallcustom.cfg"


def test_two_mods_changing_different_hotkeys_both_count(game_dir):
    base = vanilla(game_dir, "hotkeys.cfg")
    a = edit(base, b"      Key = H", [b"      Key = Y"])            # build house
    b = edit(base, b"      Key = L", [b"      Key = F6"])           # build blacksmith
    m = R.merge(base, [a, b], R.PROFILES[HK], [b"A", b"B"])
    assert m.status == R.OK and m.lines is not None
    got = records_of(m.lines, HK)
    assert b"      Key = Y" in got.by_key[b"build~124%nat%hou"].lines
    assert b"      Key = F6" in got.by_key[b"build~124%nat%bla"].lines
    assert (R.OK, b"record build|%nat%hou: from A") in m.lines_out


def test_the_same_record_changed_twice_later_wins_with_a_warning(game_dir):
    base = vanilla(game_dir, "hotkeys.cfg")
    a = edit(base, b"      Key = H", [b"      Key = Y"])
    b = edit(base, b"      Key = H", [b"      Key = F6"])
    m = R.merge(base, [a, b], R.PROFILES[HK], [b"A", b"B"])
    assert m.status == R.WARN
    assert b"      Key = F6" in records_of(m.lines, HK).by_key[b"build~124%nat%hou"].lines


def test_a_new_collision_is_a_warning_but_one_a_mod_made_itself_is_not(game_dir):
    base = vanilla(game_dir, "hotkeys.cfg")
    # A puts house on F6; B puts blacksmith on F6: only the merge has both.
    a = edit(base, b"      Key = H", [b"      Key = F6"])
    b = edit(base, b"      Key = L", [b"      Key = F6"])
    m = R.merge(base, [a, b], R.PROFILES[HK], [b"A", b"B"])
    assert (R.WARN, b"key f6: build|%nat%bla and build|%nat%hou are on it now") in m.lines_out
    # A alone puts both on F6: its own choice, no warning.
    both = edit(a, b"      Key = L", [b"      Key = F6"])
    other = edit(base, b"      Key = C", [b"      Key = F7"])
    m2 = R.merge(base, [both, other], R.PROFILES[HK], [b"A", b"B"])
    assert not any(t == R.WARN for t, _x in m2.lines_out)


def test_added_and_removed_records(game_dir):
    base = vanilla(game_dir, "hotkeys.cfg")
    end = base.index(b"section.end")
    new = [b"   [*] : struct.begin", b"      Key = F9", b"      Action = event~124qmtest",
           b"   struct.end"]
    a = base[:end] + new + base[end:]
    first = base.index(b"   [*] : struct.begin")
    b = base[:first] + base[first + 4:]          # the first record (build|%nat%cen) removed
    m = R.merge(base, [a, b], R.PROFILES[HK], [b"A", b"B"])
    got = records_of(m.lines, HK)
    assert b"event~124qmtest" in got.by_key and b"build~124%nat%cen" not in got.by_key
    assert got.records[-1].key == b"event~124qmtest"


def formations_with(base, names):
    end = base.index(b"section.end")
    extra = []
    for n in names:
        extra += [b"   [*] : struct.begin", b"      id = " + n, b"   struct.end"]
    return base[:end] + extra + base[end:]


def test_formations_two_mods_add_past_the_bound_fail_and_nothing_is_written(game_dir):
    base = vanilla(game_dir, "formations.cfg")
    a = formations_with(base, [b"QMA%d" % i for i in range(6)])       # 155
    b = formations_with(base, [b"QMB%d" % i for i in range(6)])       # 155
    m = R.merge(base, [a, b], R.PROFILES[FORM])
    assert m.status == R.FAIL and m.lines is None
    assert m.problem == b"161 records, the game loads none above 160"
    # with room for them, both are in
    ok = R.merge(base, [a, formations_with(base, [b"QMB0"])], R.PROFILES[FORM])
    assert ok.status == R.OK and len(records_of(ok.lines, FORM).records) == 156


def test_a_total_conversion_s_own_bound_counts(game_dir):
    """State vs Country raises gc_formation_maxcount to 203 in its
    dmscript.global and ships 195 formations: the bound is the constant in
    effect, not vanilla's 160."""
    base = vanilla(game_dir, "formations.cfg")
    tc = formations_with(base, [b"TC%d" % i for i in range(46)])       # 195
    addon = formations_with(base, [b"ADD%d" % i for i in range(5)])    # 154
    glob = [b"   gc_formation_maxcount = 203{188}; //165 158  140 awar"]
    limits = R.limits_from_global(glob)
    assert limits == {b"gc_formation_maxcount": 203}
    m = R.merge(base, [tc, addon], R.PROFILES[FORM], limits=limits)
    assert m.status == R.OK and len(records_of(m.lines, FORM).records) == 200
    more = formations_with(base, [b"ADD%d" % i for i in range(9)])     # 195 + 9 = 204
    m2 = R.merge(base, [tc, more], R.PROFILES[FORM], limits=limits)
    assert m2.status == R.FAIL and m2.problem == b"204 records, the game loads none above 203"


def test_the_vanilla_bounds_come_from_vanilla_s_dmscript_global(game_dir):
    with open(os.path.join(game_dir, "data", "scripts", "dmscript.global"), "rb") as fh:
        limits = R.limits_from_global(T.read_lines(fh.read()))
    assert limits == {b"gc_maxwallvariationcount": 24, b"gc_maxwallbuilderpointscount": 16,
                      b"gc_maxbuildercount": 30, b"gc_maxexitpointscount": 4,
                      b"gc_maxshotpointscount": 40, b"gc_formation_maxcount": 160}
    for p in R.PROFILES.values():
        for _name, const, vanilla_value in p.arrays:
            assert limits[const] == vanilla_value
        for bound in (p.max_records, p.key_range):
            if bound:
                assert limits[bound[0]] == bound[1]


def test_the_array_bounds_and_the_key_range(game_dir):
    """A record comes whole from one file, so only a file that already breaks
    a bound can bring it; `check` itself holds every bound."""
    base = vanilla(game_dir, "objcustom.cfg")
    i = base.index(b"      ExitPoints : struct.begin")
    point = [b"         [*] : struct.begin", b"            x = 0", b"            y = 0",
             b"            z = 0", b"         struct.end"]
    five = records_of(base[:i + 1] + point * 3 + base[i + 1:], OBJ)   # ausbar had 2: now 5
    assert R.check(five, R.PROFILES[OBJ]) == b"record ausbar: exitpoints has 5 entries, the game holds 4"
    assert R.check(five, R.PROFILES[OBJ], inputs=[five]) == b""
    wall = vanilla(game_dir, "wallcustom.cfg")
    w = records_of(edit(wall, b"      WallVariation = 1", [b"      WallVariation = 24"]), WALL)
    assert R.check(w, R.PROFILES[WALL]) == b"record 24: the key must be 0..23"


def test_a_file_that_is_not_the_layout_keeps_the_winner(game_dir):
    base = vanilla(game_dir, "hotkeys.cfg")
    broken = base[:-3]                               # no struct.end / section.end
    m = R.merge(base, [broken, base], R.PROFILES[HK], [b"A", b"B"])
    assert m.status == R.FAIL and m.lines is None
    assert (R.FAIL, b"A: the file is not the record layout") in m.lines_out


def test_a_duplicate_key_is_not_the_layout(game_dir):
    base = vanilla(game_dir, "hotkeys.cfg")
    first = base.index(b"   [*] : struct.begin")
    dup = base[:first] + base[first:first + 4] + base[first:]
    assert R.split(dup, R.PROFILES[HK]) is None
