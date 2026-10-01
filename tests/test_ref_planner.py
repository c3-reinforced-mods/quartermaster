"""Gates for ref.planner: the strategy table, the WASD fixture paths, and the one
list of hook files the build, the harness and the game side share."""
import os

import pytest

import hbuild
import hrun
from ref import planner as P

QM = b"mods\\Quartermaster"
WASD = b"mods\\QMTestWASD"
CAMSPEED = b"mods\\QMTestCamSpeed"
OTHER = b"mods\\SomeoneElse"

#: The four files QMTestWASD ships (tools/fixtures.py), as vanilla.idx spells them.
WASD_FILES = {
    b"gui\\menu.inc\\registershortcuts.inc": (b"merge", 205),
    b"gui\\menu.inc\\oncamera.inc": (b"merge", 76),
    b"gui\\menu.inc\\hotkeysettings.inc": (b"merge", 426),
    b"game\\var\\hotkeys.cfg": (b"wta", 243),
}


def decide(path, providers, cls=None, lines=None, phase=P.PHASE_A):
    c, n = WASD_FILES.get(path, (cls, lines))
    return P.decide(path, cls or c, n if lines is None else lines, providers, QM, phase)


def test_wasd_files_strategy_is_three_inc_merges_and_hotkeys_winner():
    """The milestone's expectation, as strategies: what each WASD file gets once
    a second mod ships it."""
    got = dict((p, decide(p, [OTHER, WASD]).action) for p in WASD_FILES)
    assert got == {b"gui\\menu.inc\\registershortcuts.inc": P.MERGE_INC,
                   b"gui\\menu.inc\\oncamera.inc": P.MERGE_INC,
                   b"gui\\menu.inc\\hotkeysettings.inc": P.MERGE_INC,
                   b"game\\var\\hotkeys.cfg": P.WINNER}
    hot = decide(b"game\\var\\hotkeys.cfg", [OTHER, WASD])
    assert hot.reason == b"record-profile-phase-b" and hot.winner == WASD


def test_wasd_and_camspeed_deployed():
    """WASD + CamSpeed (canonical order CamSpeed < WASD): the two shared files
    merge, the two only WASD ships are skipped - its own copy is already what
    the overlay loads - with the strategy they would get."""
    index = {b"gui\\menu.inc\\registershortcuts.inc": [CAMSPEED, WASD],
             b"gui\\menu.inc\\oncamera.inc": [CAMSPEED, WASD],
             b"gui\\menu.inc\\hotkeysettings.inc": [WASD],
             b"game\\var\\hotkeys.cfg": [WASD]}
    got = dict((p, (d.action, d.strategy, d.winner))
               for p, d in ((p, decide(p, v)) for p, v in index.items()))
    assert got == {
        b"gui\\menu.inc\\registershortcuts.inc": (P.MERGE_INC, P.MERGE_INC, WASD),
        b"gui\\menu.inc\\oncamera.inc": (P.MERGE_INC, P.MERGE_INC, WASD),
        b"gui\\menu.inc\\hotkeysettings.inc": (P.SKIP, P.MERGE_INC, WASD),
        b"game\\var\\hotkeys.cfg": (P.SKIP, P.WINNER, WASD)}


def test_hook_file_is_hook_even_alone():
    cc = b"gui\\menu.inc\\cameracontrol.inc"
    alone = P.decide(cc, b"merge", 38, [QM], QM)
    assert (alone.action, alone.strategy, alone.reason) == (P.HOOK, P.HOOK, b"quartermaster-hook")
    shared = P.decide(cc, b"merge", 38, [WASD, QM], QM)
    assert shared.action == P.HOOK and shared.providers == [WASD, QM]
    # A hook file Quartermaster does not ship yet is merged like any other.
    dp = P.decide(b"gui\\menu.inc\\doprogress.inc", b"merge", 1736, [CAMSPEED, WASD], QM)
    assert dp.action == P.MERGE_INC


@pytest.mark.parametrize("cls, lines, path, want", [
    (b"merge", 60000, b"scripts\\a.inc", (P.MERGE_INC, b"merge-allow-list")),
    (b"merge", 60001, b"scripts\\a.inc", (P.WINNER, b"over-size-cap")),
    # Phase B (the build's phase): data files merge by records; dmscript.global
    # is a global script, the winner's.
    (b"wta", 10, b"game\\var\\objcustom.cfg", (P.MERGE_DATA, b"record-profile")),
    (b"wta", 10, b"scripts\\dmscript.global", (P.WINNER, b"global-script")),
    (b"never", -1, b"textures\\a.dds", (P.WINNER, b"binary")),
    (b"never", 10, b"gui\\menu.aix", (P.WINNER, b"never-generate")),
    (b"wta", 10, b"game\\var\\units.cfg", (P.WINNER, b"not-on-allow-list")),
    (b"odd", 10, b"x\\y.z", (P.WINNER, b"unknown-class")),
])
def test_strategy_table(cls, lines, path, want):
    assert P.strategy(path, cls, lines) == want
    assert decide(path, [OTHER, WASD], cls, lines, phase=P.PHASE_B).action == want[0]
    assert decide(path, [WASD], cls, lines).action == P.SKIP


def test_phase_b_turns_the_reserved_strategies_on():
    assert P.strategy(b"game\\var\\hotkeys.cfg", b"wta", 243, phase=P.PHASE_B) == (
        P.MERGE_DATA, b"record-profile")
    # dmscript.global is a global script (plan S17): the winner's, in Phase B too.
    assert P.strategy(P.ADDITIVE_GLOBAL, b"wta", 2400, phase=P.PHASE_B) == (
        P.WINNER, b"global-script")


def test_no_provider_no_decision_and_plan_keeps_vanilla_idx_order():
    assert P.decide(b"a", b"merge", 1, [], QM) is None
    entries = [(b"b.inc", 1, 1, b"merge"), (b"a.inc", 1, 1, b"merge"), (b"c.inc", 1, 1, b"merge")]
    plan = P.plan({b"a.inc": [WASD], b"b.inc": [CAMSPEED, WASD]}, entries, QM)
    assert [d.path for d in plan] == [b"b.inc", b"a.inc"]
    pos = {CAMSPEED: 0, WASD: 1, QM: 2}
    assert P.plan_lines(plan, pos.get) == [
        b"plan|b.inc|merge-inc|merge-inc|merge-allow-list|1|0;1",
        b"plan|a.inc|skip|merge-inc|merge-allow-list|1|1"]


def test_the_hook_list_is_one_list():
    """S5's five files, spelled for vanilla.idx, and the same list in hbuild and
    hrun (they derive theirs from it)."""
    assert P.HOOK_FILES == (b"gui\\menu.inc\\cameracontrol.inc", b"gui\\menu.inc\\initminimap.inc",
                            b"gui\\menu.inc\\doprogress.inc", b"gui\\menu.inc\\eventmainmenu.inc",
                            b"gui\\menu.inc\\onlanevent.inc")
    assert hbuild.HOOK_FILES == tuple("data/" + h.decode().replace("\\", "/")
                                      for h in P.HOOK_FILES)
    assert hrun.HOOK_FILES == tuple(h[len("data/"):] for h in hbuild.HOOK_FILES)
    # Every shipped hook is on the list.
    for hook in hbuild.load_hooks():
        assert hook.into in hbuild.HOOK_FILES


def test_constants_agree_with_vanilla_idx():
    with open(os.path.join(hbuild.DIST_MOD, *hbuild.IDX_REL.split("/")), "rb") as fh:
        _h, rows = hbuild.parse_vanilla_idx(fh.read())
    table = dict((p.encode(), (n, c.encode())) for p, _s, n, c in rows)
    for hook in P.HOOK_FILES:
        assert table[hook][1] == P.MERGE_CLASS
    for path in P.PHASE_B_DATA + (P.ADDITIVE_GLOBAL,):
        assert table[path][1] == b"wta" and 0 < table[path][0] <= P.SIZE_CAP_LINES
    for path, (cls, _lines) in WASD_FILES.items():
        assert table[path][1] == cls
    assert set(c for _n, c in table.values()) == set(P.KNOWN_CLASSES)
