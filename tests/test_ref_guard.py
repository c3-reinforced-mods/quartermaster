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


def test_a_mod_switched_on_in_modman_is_judged_against_the_last_start_that_booted():
    # Cannons is known (it was installed before), but it was not in the last
    # start that booted: switched on in modman since, it is judged like a new
    # subscription, and the engine's "Error compiling scripts" never comes up.
    mods = [gmod(b"1325221799"), gmod(b"1450025705"), QM]
    every = known(b"1325221799", b"1450025705")
    plan = G.decide(mods, every, compiled=dirs(b"1325221799", b"mods\\Quartermaster"))
    assert (plan.why, plan.basis) == (b"conflict", b"compiled")
    assert plan.off == [(1, b"lib\\unit.script", 0)]
    # A pair that booted together is trusted, clash or not.
    both = dirs(b"1325221799", b"1450025705", b"mods\\Quartermaster")
    assert G.decide(mods, every, compiled=both).why == b"clean"
    # So is a pair the player applied in the window since (chosen.cfg).
    assert G.decide(mods, every, compiled=dirs(b"1325221799", b"mods\\Quartermaster"),
                    chosen=both).why == b"clean"
    # Without the record (a first start of 0.1.3) only new subscriptions are judged.
    assert (G.decide(mods, every).why, G.decide(mods, every).basis) == (b"clean", b"known")
    # The window and the report name the clash either way.
    c = G.conflicts(mods)
    assert c[1] == [(b"lib\\unit.script", 0)] and (b"lib\\unit.script", 1) in c[0]


def test_the_owners_start_of_2026_10_03_with_quartermaster_in_the_middle():
    """08:45: State vs Country on, Quartermaster in the middle, Cannons and
    Rise of America+ (unit.script and a DoProgress hook) after it, all
    switched on in modman. Both after it are judged and switched off; neither
    is left to replace a hook, so Quartermaster need not move."""
    roap = G.GMod(WS + b"2222380947", b"Rise of America+", True, False,
                  G.global_names([b"unit.script", b"classes.script"], False, False),
                  b"gui\\menu.inc\\doprogress.inc")
    mods = [gmod(b"1325221799"), QM, gmod(b"1450025705"), roap]
    every = known(b"1325221799", b"1450025705", b"2222380947", b"mods\\Quartermaster")
    plan = G.decide(mods, every, compiled=dirs(b"mods\\Quartermaster"))
    assert plan.why == b"conflict" and [i for i, _f, _j in plan.off] == [2, 3]
    assert plan.late == [] and not plan.moved


def dirs(*keys):
    return [(k if k.startswith(b"mods\\") else WS + k) for k in keys]


ERROR_LOG = (b"LOG|  4 |[qm-guard] clean mods=47\r\n"
             b"ERROR|165 |CompileFramework() - compile global script error: Syntax error: "
             b"Line: 39902, Column: 32: Unknown Name\r\n"
             b"ERROR|166 |Compile script error: OnClear\r\n")


def record(*keys, **extra):
    vals = dict(G.compiled_values(dirs(*keys)))
    vals.update(dict((k.encode(), v) for k, v in extra.items()))
    return vals


def test_a_start_failed_when_its_record_is_pending_and_its_log_has_the_error():
    mods = [gmod(b"1325221799"), gmod(b"1450025705"), QM]
    rec = record(b"1325221799", b"1450025705", b"mods\\Quartermaster", pending=b"1")
    assert G.failed(rec, ERROR_LOG, mods)
    cleared = dict(rec)
    cleared[b"pending"] = b"0"
    assert not G.failed(cleared, ERROR_LOG, mods)                 # its boot cleared it
    old = dict((k, v) for k, v in rec.items() if k != b"pending")
    assert G.failed(old, ERROR_LOG, mods)                         # 0.1.2's record: no key
    assert not G.failed(None, ERROR_LOG, mods)
    assert not G.failed(rec, b"LOG|  4 |[qm-guard] restart mods=47\r\n", mods)
    assert not G.failed(rec, None, mods)                          # no previous log
    # The main menu that did not compile is a start that stopped too.
    assert G.failed(rec, b"ERROR|  7 |Compile script error: DoCreate\r\n", mods)
    assert not G.failed(rec, b"ERROR|  7 |Compile script error: ShowCustomGame\r\n", mods)
    # Another set than the one that stopped: the player put it right in modman
    # (Cannons off), or a guard restart without Steam left mods.ini changed.
    fixed = [gmod(b"1325221799"), gmod(b"1450025705", on=False), QM]
    assert not G.failed(rec, ERROR_LOG, fixed)
    more = mods + [gmod(b"873048118")]
    assert not G.failed(rec, ERROR_LOG, more)
    # The order does not count: Quartermaster moved last is the same set.
    assert G.failed(rec, ERROR_LOG, [mods[0], QM, mods[1]])
    # A record without a count is no set.
    assert not G.failed({b"pending": b"1"}, ERROR_LOG, mods)
    # As the guard reads it: up to the first zero byte, LOG_INTS Integers.
    assert not G.log_failed(b"x\x00" + ERROR_LOG)
    assert G.log_failed(b"a" * (G.LOG_INTS * 4 - 16) + b"CompileFramework")
    assert not G.log_failed(b"a" * (G.LOG_INTS * 4 - 15) + b"CompileFramework")
    assert G.log_failed(b"CCompileFramework") and G.log_failed(b"CompilCompileFramework")
    assert G.log_failed(b"Compile script error: DoCompile script error: DoCreate")
    assert not G.log_failed(b"Compile script error: DoCreat")


def test_the_owners_32_mods_after_the_start_that_stopped():
    """2026-10-02: the last start that booted had only the Unofficial Patch on;
    32 Workshop mods switched on in modman at once stopped the next start.
    The start after it switches off, by name, the ones that clash: one of each
    script stays, the first in load order."""
    order = [b"mods\\UnofficialPatch", b"873048118", b"1325221799", b"3579561908",
             b"855882129", b"1255766623", b"1450025705", b"917824662", b"QM"]
    mods = [QM if k == b"QM" else gmod(k) for k in order]
    every = known(*[k for k in order if k != b"QM"] + [b"mods\\Quartermaster"])
    good = dirs(b"mods\\UnofficialPatch", b"mods\\Quartermaster")
    # Judged in advance now, the start would not have stopped: the same mods
    # go before the compile (only the rule's name differs).
    ahead = G.decide(mods, every, compiled=good)
    plan = G.decide(mods, every, compiled=good, failed=True)
    assert ahead.why == b"conflict" and ahead.off == plan.off
    assert (plan.action, plan.why, plan.basis) == (b"off", b"failed-names", b"compiled")
    off = dict((mods[i].title, (f, mods[j].title)) for i, f, j in plan.off)
    # State vs Country, the first with libraries, claims them; ZoomOut! ships none.
    assert off == {
        b"3579561908": (b"lib\\control.script", b"1325221799"),
        b"855882129": (b"lib\\miscext2.script", b"1325221799"),
        b"1255766623": (b"lib\\classes.script", b"1325221799"),
        b"1450025705": (b"lib\\unit.script", b"1325221799"),
        b"917824662": (b"dmscript.global", b"1325221799"),
    }


def test_without_a_name_clash_every_mod_outside_the_good_set_goes():
    # The start after the names step stopped too: nothing clashes by name any
    # more, so every mod switched on since the last start that booted goes.
    mods = [gmod(b"1325221799"), gmod(b"873048118"), gmod(b"855916926"), QM]
    plan = G.decide(mods, known(b"1325221799"), compiled=dirs(b"855916926"), failed=True)
    assert plan.why == b"failed-revert" and plan.off == [(0, b"", -1), (1, b"", -1)]
    assert plan.key == (WS + b"1325221799|" + WS + b"873048118|").lower()


def test_when_the_good_set_itself_stops_only_quartermaster_stays():
    # Every enabled mod booted before (a Workshop update broke one since).
    mods = [gmod(b"1325221799"), gmod(b"873048118"), QM]
    plan = G.decide(mods, known(), compiled=dirs(b"1325221799", b"873048118"), failed=True)
    assert plan.why == b"failed-vanilla" and plan.off == [(0, b"", -1), (1, b"", -1)]
    # Nothing left to switch off: the start goes on as it is.
    alone = G.decide([gmod(b"1325221799", on=False), QM], known(),
                     compiled=dirs(b"1325221799"), failed=True)
    assert (alone.action, alone.why) == (b"none", b"failed-alone")


def test_without_a_record_the_good_set_is_the_game_alone():
    mods = [gmod(b"873048118"), gmod(b"855916926"), QM]
    plan = G.decide(mods, known(), failed=True)
    assert (plan.why, plan.basis) == (b"failed-revert", b"none")
    assert [i for i, _f, _j in plan.off] == [0, 1]
    # A record that is not one (no count of at least 1) is no record.
    assert G.compiled_dirs({b"n": b"0", b"d0": WS + b"873048118"}) is None


def test_a_dir_the_guard_cannot_compare_is_never_switched_off_after_a_failed_start():
    odd = G.GMod(b"mods\\\xd0\x9c", b"cyrillic", True, False, [G.LIB + b"unit.script"])
    mods = [odd, gmod(b"873048118"), QM]
    plan = G.decide(mods, known(), compiled=dirs(b"873048118"), failed=True)
    assert plan.why == b"failed-vanilla" and plan.off == [(1, b"", -1)]


def test_a_record_without_a_count_is_no_record():
    assert G.compiled_dirs({}) is None
    assert G.compiled_dirs({b"n": b"0", b"d0": b"x"}) is None
    assert G.compiled_dirs({b"n": b"x"}) is None
    assert G.compiled_dirs({b"n": b"2", b"d0": b"a"}) == [b"a", b""]
    assert G.compiled_dirs(dict(G.compiled_values([b"a", b"b"]))) == [b"a", b"b"]
    assert len(G.compiled_dirs({b"n": b"600"})) == 512


def test_the_basis_says_what_the_decision_stood_on():
    mods = [gmod(b"1325221799"), gmod(b"1450025705"), QM]
    assert G.decide(mods, None).basis == b"none"
    assert G.decide(mods, known(b"1325221799")).basis == b"known"
    assert G.decide(mods, known(b"1325221799"), compiled=dirs(b"1325221799")).basis == b"compiled"
    assert G.decide(mods, None, compiled=dirs(b"1325221799"), failed=True).basis == b"compiled"
    assert G.decide(mods, None, failed=True).basis == b"none"
    assert G.decide(mods, None, mp_sync=True, failed=True).basis == b"-"
    assert G.decide(mods, None, same_game=False, failed=True).why == b"game-version"


def test_the_note_of_a_step_has_no_file_and_no_other_mod():
    mods = [gmod(b"873048118"), QM]
    plan = G.decide(mods, known(), failed=True)
    assert G.note_values(mods, plan) == [
        (b"restarted", b"1"), (b"shown", b"0"), (b"key", WS.lower() + b"873048118|"),
        (b"n", b"1"), (b"moved", b"0"), (b"why", b"failed-revert"),
        (b"dir0", WS + b"873048118"), (b"tit0", b"873048118"), (b"file0", b"")]


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
        (b"n", b"1"), (b"moved", b"0"), (b"why", b"conflict"),
        (b"dir0", WS + b"1450025705"), (b"tit0", b"1450025705"),
        (b"file0", b"lib\\unit.script"), (b"odir0", WS + b"1325221799"),
        (b"otit0", b"1325221799")]
