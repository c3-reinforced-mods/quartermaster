"""Gates for ref.guard: the guard's decision (docs/plan.md S17) on the real
file lists of popular Workshop mods, as probe run g1 listed them
(docs/research/guard-probes.md)."""
from ref import guard as G

WS = b"..\\..\\workshop\\content\\333420\\"

# Global scripts per mod, from run g1 0.log (ParserGetFilesInRoot + dmscript.*).
LIBS = {
    b"873048118": ([], False, False),                                   # ZoomOut!
    b"3579561908": (["control.script", "country.script", "init.script", "miscext.script",
                     "miscext2.script", "player.script", "unit.script", "weapon.script"],
                    True, False),                                       # Great Cossacks 6
    b"1325221799": (["!gui.script", "ai.script", "classes.script", "control.script",
                     "country.script", "gui.script", "init.script", "misc.script",
                     "miscext.script", "miscext2.script", "net.script", "player.script",
                     "res.script", "scenario.script", "serial.script", "squad.script",
                     "unit.script", "weapon.script"], True, True),      # State vs Country
    b"870599630": ([], False, False),                                   # MGraphics MP
    b"855916926": ([], False, False),                                   # MGraphics Interface
    b"855882129": (["miscext2.script"], False, False),                  # MGraphics Lights
    b"1255766623": (["classes.script", "misc.script", "miscext.script", "miscext2.script",
                     "player.script"], True, False),                    # New Terrain
    b"1450025705": (["unit.script"], False, False),                     # Cannons
    b"917824662": ([], True, False),                                    # Patrol
    b"mods\\SW_Frontline_Protocol": (["control.script", "country.script", "gui.script",
                                      "map.script", "profile.script", "unit.script",
                                      "weapon.script"], True, False),
}


def gmod(key, on=True, is_self=False):
    libs, glob, src = LIBS.get(key, ([], False, False))
    d = key if key.startswith(b"mods\\") else WS + key
    files = G.global_names([n.encode() for n in libs], glob, src)
    return G.GMod(d, key, on, is_self, files)


def known(*keys):
    return [((k if k.startswith(b"mods\\") else WS + k), False) for k in keys]


QM = G.GMod(b"mods\\Quartermaster", b"Quartermaster", True, True, [])


def test_a_new_cannons_next_to_state_vs_country_is_switched_off():
    mods = [gmod(b"1325221799"), QM, gmod(b"1450025705")]
    plan = G.decide(mods, known(b"1325221799", b"mods\\Quartermaster"))
    assert plan.action == b"off" and plan.why == b"conflict"
    assert plan.off == [(2, b"lib\\unit.script", 0)]


def test_the_owners_start_of_2026_09_28_keeps_one_of_each_script():
    # mods.ini of that start: what known.cfg had at 16:52, then the Workshop
    # items the engine appended at 18:08 (all on), Cannons last.
    order = [b"873048118", b"mods\\SW_Frontline_Protocol", b"mods\\QMTestBroken",
             b"mods\\QMTestWASD", b"QM", b"3579561908", b"1325221799", b"870599630",
             b"855916926", b"855882129", b"1255766623", b"1450025705"]
    mods = [QM if k == b"QM" else gmod(k) for k in order]
    plan = G.decide(mods, known(b"873048118", b"mods\\SW_Frontline_Protocol",
                                b"mods\\QMTestBroken", b"mods\\QMTestWASD",
                                b"mods\\Quartermaster"))
    assert plan.action == b"off"
    off = dict((mods[i].title, (f, mods[j].title)) for i, f, j in plan.off)
    assert off == {
        b"3579561908": (b"lib\\control.script", b"mods\\SW_Frontline_Protocol"),
        b"1325221799": (b"lib\\control.script", b"mods\\SW_Frontline_Protocol"),
        # MGraphics Lights stays (SWFP ships no miscext2) and claims it first.
        b"1255766623": (b"lib\\miscext2.script", b"855882129"),
        b"1450025705": (b"lib\\unit.script", b"mods\\SW_Frontline_Protocol"),
    }


def test_of_two_new_mods_the_first_in_load_order_stays():
    mods = [gmod(b"1255766623"), gmod(b"855882129"), QM]
    plan = G.decide(mods, known(b"mods\\Quartermaster"))
    assert plan.off == [(1, b"lib\\miscext2.script", 0)]


def test_mods_without_global_scripts_are_never_switched_off():
    mods = [gmod(b"1325221799"), gmod(b"873048118"), gmod(b"870599630"),
            gmod(b"855916926"), QM]
    assert G.decide(mods, known(b"1325221799")).why == b"clean"


def test_without_a_compiled_record_known_mods_are_the_players_choice_even_when_they_clash():
    # Quartermaster before 0.1.3 wrote no compiled.cfg: known.cfg is the basis.
    mods = [gmod(b"1325221799"), gmod(b"1450025705"), QM]
    plan = G.decide(mods, known(b"1325221799", b"1450025705"))
    assert (plan.why, plan.basis) == (b"clean", b"known")
    # ...but the window and the report name the clash.
    c = G.conflicts(mods)
    assert c[1] == [(b"lib\\unit.script", 0)] and (b"lib\\unit.script", 1) in c[0]


def dirs(*keys):
    return [(k if k.startswith(b"mods\\") else WS + k) for k in keys]


def test_a_known_mod_switched_on_since_the_last_start_that_booted_is_judged():
    """The owner's start of 2026-10-02: every mod known, the last start that
    booted had only the Unofficial Patch on, then 32 Workshop mods were
    switched on in modman at once - the guard said `clean` and the start
    stopped at "Error compiling scripts". With the record, one of each script
    stays: the first in load order."""
    order = [b"mods\\UnofficialPatch", b"873048118", b"1325221799", b"3579561908",
             b"855882129", b"1255766623", b"1450025705", b"917824662", b"QM"]
    mods = [QM if k == b"QM" else gmod(k) for k in order]
    every = known(*[k for k in order if k != b"QM"] + [b"mods\\Quartermaster"])
    assert G.decide(mods, every).why == b"clean"                     # 0.1.2: no record
    plan = G.decide(mods, every, compiled=dirs(b"mods\\UnofficialPatch", b"mods\\Quartermaster"))
    assert (plan.action, plan.why, plan.basis) == (b"off", b"conflict", b"compiled")
    off = dict((mods[i].title, (f, mods[j].title)) for i, f, j in plan.off)
    # State vs Country, the first with libraries, claims them; ZoomOut! ships none.
    assert off == {
        b"3579561908": (b"lib\\control.script", b"1325221799"),
        b"855882129": (b"lib\\miscext2.script", b"1325221799"),
        b"1255766623": (b"lib\\classes.script", b"1325221799"),
        b"1450025705": (b"lib\\unit.script", b"1325221799"),
        b"917824662": (b"dmscript.global", b"1325221799"),
    }


def test_mods_of_the_last_start_that_booted_are_trusted_even_when_they_clash():
    # That set compiled: whatever the names say, the guard leaves it alone.
    mods = [gmod(b"1325221799"), gmod(b"1450025705"), QM]
    plan = G.decide(mods, known(b"1325221799"), compiled=dirs(b"1325221799", b"1450025705"))
    assert (plan.why, plan.basis) == (b"clean", b"compiled")


def test_the_record_decides_over_known_cfg():
    # Cannons is not in known.cfg but was on in the start that booted (the
    # record is newer); State vs Country is known but was off then.
    mods = [gmod(b"1450025705"), gmod(b"1325221799"), QM]
    plan = G.decide(mods, known(b"1325221799"), compiled=dirs(b"1450025705"))
    assert plan.off == [(1, b"lib\\unit.script", 0)] and plan.basis == b"compiled"


def test_a_mod_switched_off_since_then_claims_nothing():
    # The set compiled with State vs Country; now it is off and Cannons is on.
    mods = [gmod(b"1325221799", on=False), gmod(b"1450025705"), QM]
    assert G.decide(mods, known(b"1325221799"), compiled=dirs(b"1325221799")).why == b"clean"


def test_a_record_without_a_count_is_no_record():
    assert G.compiled_dirs({}) is None
    assert G.compiled_dirs({b"n": b"0", b"d0": b"x"}) is None
    assert G.compiled_dirs({b"n": b"x"}) is None
    assert G.compiled_dirs({b"n": b"2", b"d0": b"a"}) == [b"a", b""]
    assert G.compiled_dirs(dict(G.compiled_values([b"a", b"b"]))) == [b"a", b"b"]
    assert len(G.compiled_dirs({b"n": b"600"})) == 512


def test_the_basis_is_none_on_a_first_boot_and_not_read_in_a_sync():
    mods = [gmod(b"1325221799"), gmod(b"1450025705"), QM]
    assert G.decide(mods, None).basis == b"none"
    assert G.decide(mods, None, compiled=dirs(b"1325221799")).basis == b"compiled"
    assert G.decide(mods, None, mp_sync=True, compiled=dirs(b"1325221799")).basis == b"-"


def test_clash_pairs_name_the_first_shared_file_of_the_earlier_mod():
    mods = [gmod(b"1255766623"), gmod(b"855882129"), gmod(b"873048118"), QM,
            gmod(b"1325221799"), gmod(b"1450025705", on=False)]
    pairs = [(mods[a].title, mods[b].title, f) for a, b, f in G.conflict_pairs(mods)]
    assert pairs == [(b"1255766623", b"855882129", b"lib\\miscext2.script"),
                     (b"1255766623", b"1325221799", b"lib\\classes.script"),
                     (b"855882129", b"1325221799", b"lib\\miscext2.script")]


def test_a_mod_that_is_off_neither_claims_nor_is_judged():
    mods = [gmod(b"1325221799", on=False), gmod(b"1450025705"), QM]
    assert G.decide(mods, known(b"1325221799")).why == b"clean"


def test_quartermaster_and_its_copies_are_left_alone():
    copy = G.GMod(b"mods\\QM copy", b"copy", True, True, [G.LIB + b"unit.script"])
    mods = [gmod(b"1325221799"), copy, QM]
    assert G.decide(mods, known(b"1325221799")).why == b"clean"


def test_dmscript_global_alone_is_a_global_script():
    mods = [gmod(b"1255766623"), gmod(b"917824662"), QM]
    plan = G.decide(mods, known(b"1255766623"))
    assert plan.off == [(1, b"dmscript.global", 0)]


def test_no_known_cfg_is_a_first_boot_and_changes_nothing():
    mods = [gmod(b"1325221799"), gmod(b"1450025705"), QM]
    assert G.decide(mods, None).why == b"first-boot"


def test_the_multiplayer_sync_and_another_game_version_change_nothing():
    mods = [gmod(b"1325221799"), gmod(b"1450025705"), QM]
    k = known(b"1325221799")
    assert G.decide(mods, k, mp_sync=True).why == b"mp-sync"
    assert G.decide(mods, k, restore_file=True).why == b"mp-sync"
    assert G.decide(mods, k, same_game=False).why == b"game-version"


def test_a_second_restart_for_the_same_mods_is_a_loop():
    mods = [gmod(b"1325221799"), gmod(b"1450025705"), QM]
    k = known(b"1325221799")
    plan = G.decide(mods, k)
    note = dict(G.note_values(mods, plan))
    again = G.decide(mods, k, previous=note)
    assert again.action == b"none" and again.why == b"loop"
    other = dict(note)
    other[b"key"] = b"something else"
    assert G.decide(mods, k, previous=other).action == b"off"


def test_a_dir_the_guard_cannot_compare_counts_as_known():
    odd = G.GMod(b"mods\\\xd0\x9c\xd0\xbe\xd0\xb4", b"cyrillic", True, False, [G.LIB + b"unit.script"])
    tilde = G.GMod(b"mods\\a~b", b"tilde", True, False, [G.LIB + b"unit.script"])
    mods = [gmod(b"1325221799"), odd, tilde, QM]
    assert G.decide(mods, known(b"1325221799")).why == b"clean"


def test_dirs_and_names_are_folded():
    mods = [gmod(b"1325221799"), G.GMod(WS + b"1450025705", b"c", True, False,
                                        G.global_names([b"Unit.Script"], False, False))]
    k = [((WS + b"1325221799").upper(), False)]
    assert G.decide(mods, k).off == [(1, b"lib\\unit.script", 0)]


def test_quartermaster_is_moved_last_when_a_later_mod_ships_a_hook_file():
    """Proof run p4: the new subscriptions were appended after Quartermaster,
    and State vs Country's doprogress.inc replaced the hook that runs qmTick."""
    svc = gmod(b"1325221799")
    svc.hooks = b"gui\\menu.inc\\doprogress.inc"
    mods = [QM, svc, gmod(b"873048118")]
    plan = G.decide(mods, known(b"1325221799", b"873048118", b"mods\\Quartermaster"))
    assert plan.action == b"off" and plan.why == b"order" and plan.off == []
    assert plan.late == [(1, b"gui\\menu.inc\\doprogress.inc")] and plan.moved
    assert plan.key == b"order:mods\\quartermaster|"
    note = dict(G.note_values(mods, plan))
    assert note[b"moved"] == b"1" and note[b"latedir"] == WS + b"1325221799"
    # The same start again (the move did not take) is a loop.
    assert G.decide(mods, known(b"1325221799", b"873048118"), previous=note).why == b"loop"


def test_a_mod_switched_off_or_before_quartermaster_does_not_move_it():
    svc = gmod(b"1325221799")
    svc.hooks = b"gui\\menu.inc\\doprogress.inc"
    assert G.decide([svc, QM], known(b"1325221799")).why == b"clean"
    cannons = gmod(b"1450025705")
    cannons.hooks = b"gui\\menu.inc\\cameracontrol.inc"
    # Cannons is switched off for its clash, so it cannot replace the hook.
    plan = G.decide([gmod(b"1325221799"), QM, cannons], known(b"1325221799"))
    assert plan.why == b"conflict" and plan.late == [] and not plan.moved


def test_without_known_cfg_the_order_is_still_put_right():
    svc = gmod(b"1325221799")
    svc.hooks = b"gui\\menu.inc\\initminimap.inc"
    plan = G.decide([QM, svc], None)
    assert plan.why == b"order" and plan.off == [] and plan.moved


def test_the_note_names_each_mod_and_what_it_clashed_with():
    mods = [gmod(b"1325221799"), QM, gmod(b"1450025705")]
    plan = G.decide(mods, known(b"1325221799"))
    assert G.note_values(mods, plan) == [
        (b"restarted", b"1"), (b"shown", b"0"), (b"key", WS.lower() + b"1450025705|"),
        (b"n", b"1"), (b"moved", b"0"),
        (b"dir0", WS + b"1450025705"), (b"tit0", b"1450025705"),
        (b"file0", b"lib\\unit.script"), (b"odir0", WS + b"1325221799"),
        (b"otit0", b"1325221799")]
