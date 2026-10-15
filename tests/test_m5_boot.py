"""Gates for ref/boot.py: the start marker, known.cfg, the S8 loop guards and
the restart decision, with the acceptance scenarios I1, I5, I6, I7 and the
suspected-brick path as whole sequences of starts, and an exhaustive sweep
of the decision over every combination of its inputs."""
import itertools

import pytest

from ref import boot as B
from ref import inc as I
from ref import textio as T

FP, FP2, FP3 = b"1-2-3", b"4-5-6", b"7-8-9"


# ---------------------------------------------------------------- marker
def test_marker_round_trips_through_the_parser_view():
    m = B.Marker(gen=3, hash=FP, phase=B.WRITTEN, mode=B.WTA, rows=1, rhash=FP2,
                 rcount=1, rk=B.AUTO, boots=7,
                 outs=[(b"gui\\menu.inc\\oncamera.inc", b"1564229335"),
                       (b"quartermaster\\state\\manifest.cfg", b"-1")])
    data = B.render_marker(m)
    assert B.parse_marker(data) == m
    # The raw writer's shape: CRLF, whole Integers, the engine layout.
    assert len(data) % 4 == 0 and data.startswith(b"section.begin\r\n   Name = qmState\r\n")
    assert b"      [*] = ;format|1\r\n" in data and b"\t" not in data


def test_marker_bytes_are_the_layout_of_its_values():
    m = B.Marker()
    lines = I.layout_lines(B.STATE_KEYS, [T.escape(v) for v in B.marker_values(m)])
    assert B.render_marker(m) == T.write_file(lines)
    assert B.marker_values(m)[:3] == [b";format|1", b";gen|0", b";hash|-"]


def test_what_is_not_a_marker_reads_as_a_first_boot():
    assert B.parse_marker(None) is None
    assert B.parse_marker(b"") is None
    assert B.parse_marker(b"garbage\r\n") is None
    no_format = T.write_file(I.layout_lines(B.STATE_KEYS, [b";gen~1244"]))
    assert B.parse_marker(no_format) is None


def test_malformed_fields_keep_their_defaults():
    values = [b";format|1", b";gen|x", b";phase|weird", b";mode|fast", b";rk|later",
              b";rows|-1", b";out|only-a-path", b";out|p|12"]
    data = T.write_file(I.layout_lines(B.STATE_KEYS, [T.escape(v) for v in values]))
    m = B.parse_marker(data)
    assert (m.gen, m.phase, m.mode, m.rk, m.rows) == (0, B.BOOTED, B.NORMAL, B.NONE, 0)
    assert m.outs == [(b"p", b"12")]


def test_damaged_compares_every_recorded_output():
    m = B.Marker(outs=[(b"a", b"10"), (b"b", b"12")])
    assert not B.damaged(m, {b"a": b"10", b"b": b"12"}.get)
    assert B.damaged(m, {b"a": b"10", b"b": b"-1"}.get)
    assert not B.damaged(None, lambda p: b"0")
    assert not B.damaged(B.Marker(), lambda p: b"0")


# ----------------------------------------------------------------- known
def test_first_boot_records_everything_as_known():
    dirs = [b"mods\\A", b"..\\..\\workshop\\content\\333420\\1", b"MODS\\a"]
    entries, new, changed = B.update_known(None, dirs)
    assert entries == [(b"mods\\A", False), (b"..\\..\\workshop\\content\\333420\\1", False)]
    assert new == [] and changed


def test_a_dir_the_file_does_not_have_is_new_until_an_apply():
    known = [(b"mods\\A", False), (b"mods\\Gone", False)]
    entries, new, changed = B.update_known(known, [b"mods\\a", b"mods\\QMTestNew"])
    assert entries == known + [(b"mods\\QMTestNew", True)] and new == [b"mods\\QMTestNew"]
    assert changed
    # The next start: still new, nothing to write.
    entries2, new2, changed2 = B.update_known(entries, [b"mods\\A", b"mods\\QMTestNew"])
    assert entries2 == entries and new2 == [b"mods\\QMTestNew"] and not changed2
    acked, ch = B.acknowledge(entries2)
    assert ch and all(not n for _d, n in acked)
    assert B.acknowledge(acked) == (acked, False)


def test_known_round_trips_and_keeps_any_byte():
    entries = [(b"mods\\A", False), (b"mods\\\xd0\x9c\xd0\xbe\xd0\xb4", True), (b"mods\\{x}~", False)]
    data = B.render_known(entries)
    assert B.parse_known(data) == entries
    assert B.parse_known(None) is None
    assert B.parse_known(T.write_file(I.layout_lines(B.KNOWN_KEYS, [b";k~124mods\\A"]))) is None
    # The format line keeps the struct form even for one mod.
    assert b"   Code : struct.begin\r\n" in B.render_known([(b"mods\\A", False)])


# ------------------------------------------------------------- decisions
def M(**kw):
    return B.Marker(**kw)


@pytest.mark.parametrize("marker, fp, sync, damaged, why, regen, mode", [
    (None, FP, False, False, B.FIRST, True, B.NORMAL),
    (None, FP, True, False, B.SYNC, False, B.NORMAL),
    (M(hash=FP), FP, False, False, B.STABLE, False, B.NORMAL),
    (M(hash=FP), FP2, False, False, B.INPUTS, True, B.NORMAL),
    (M(hash=FP), FP, False, True, B.DAMAGED, True, B.NORMAL),
    (M(hash=FP, phase=B.BOOTING), FP, False, False, B.SUSPECT, True, B.WTA),
    (M(hash=FP, phase=B.BOOTING), FP2, False, False, B.INPUTS, True, B.NORMAL),
    (M(hash=FP, mode=B.WTA), FP, False, False, B.KEPT, False, B.WTA),
    (M(hash=FP, mode=B.WTA), FP, False, True, B.DAMAGED, True, B.WTA),
    (M(hash=FP, mode=B.WTA), FP2, False, False, B.INPUTS, True, B.NORMAL),
    (M(hash=FP, phase=B.BOOTING), FP, True, False, B.SYNC, False, B.NORMAL),
])
def test_boot_plan_rules(marker, fp, sync, damaged, why, regen, mode):
    p = B.boot_plan(marker, fp, sync, damaged)
    assert (p.why, p.regen, p.mode) == (why, regen, mode)


def test_phases_of_a_start():
    assert B.boot_plan(None, FP, False, False).phase == B.BOOTED
    assert B.boot_plan(M(phase=B.WRITTEN), FP, False, False).phase == B.BOOTING
    assert B.boot_plan(M(phase=B.BOOTING), FP, False, False).phase == B.BOOTING
    assert B.boot_plan(M(phase=B.BOOTED), FP, False, False).phase == B.BOOTED
    assert B.tick(M(phase=B.BOOTING)).phase == B.BOOTED
    assert B.tick(M(phase=B.WRITTEN)).phase == B.WRITTEN


def test_restart_rules_in_order():
    def plan(m, fp=FP, sync=False, apply=False):
        return B.boot_plan(m, fp, sync, False, apply=apply)

    assert B.restart_plan(None, plan(None), FP, 0, False).why == B.NOTHING
    r = B.restart_plan(None, plan(None), FP, 2, False)
    assert (r.restart, r.kind, r.why) == (True, B.AUTO, B.OUTPUTS)
    r = B.restart_plan(None, plan(None), FP, 0, True)
    assert (r.restart, r.why) == (True, B.MODSINI)
    assert B.restart_plan(None, plan(None, sync=True), FP, 1, False).refused == B.SYNC
    m = M(hash=FP, rk=B.AUTO)
    assert B.restart_plan(m, plan(m, FP2), FP2, 1, False).refused == B.LOOP
    m = M(hash=FP, rows=2)
    assert B.restart_plan(m, plan(m, FP2), FP2, 1, False).refused == B.IN_A_ROW
    m = M(hash=FP, rhash=FP, rcount=1)
    assert B.restart_plan(m, plan(m, FP, False), FP, 1, False).refused == B.PER_HASH
    # The player's Apply: only an MP sync stops it, and it is not automatic.
    m = M(hash=FP, rows=2, rhash=FP, rcount=1)
    r = B.restart_plan(m, plan(m, apply=True), FP, 1, False)
    assert (r.restart, r.kind) == (True, B.APPLY)
    assert B.restart_plan(m, plan(m, sync=True, apply=True), FP, 1, False).refused == B.SYNC


def test_mods_registered_at_this_start_are_not_a_loop():
    # The inputs moved across Quartermaster's restart, but only by mods the
    # engine registered now: without them the fingerprint is the marker's.
    m = M(hash=FP, rk=B.APPLY)
    p = B.boot_plan(m, FP2, False, False)
    assert p.followed
    r = B.restart_plan(m, p, FP2, 0, True, fp_known=FP)
    assert (r.restart, r.kind, r.why, r.refused) == (True, B.AUTO, B.MODSINI, None)
    # Something else moved as well: the loop rule as before.
    assert B.restart_plan(m, p, FP2, 0, True, fp_known=FP3).refused == B.LOOP
    assert B.restart_plan(m, p, FP2, 0, True).refused == B.LOOP
    # The other rules still bound the restarts.
    m = M(hash=FP, rk=B.AUTO, rows=2)
    p = B.boot_plan(m, FP2, False, False)
    assert B.restart_plan(m, p, FP2, 1, False, fp_known=FP).refused == B.IN_A_ROW


def test_fresh_is_what_known_cfg_did_not_have():
    known = [(b"mods\\A", False), (b"mods\\Gone", True)]
    assert B.fresh(known, [b"mods\\a", b"mods\\Testowy", b"MODS\\GONE"]) == [False, True, False]
    assert B.fresh(None, [b"mods\\A"]) == [False]
    assert B.fresh([], [b"mods\\A"]) == [True]


def test_a_folder_made_before_an_apply_restarts_once_more_without_fail():
    # Logs of 2026-10-01 (cos_261001_180032 / 180239): New mod
    # made mods\Testowy, an Apply restarted the game, and the engine
    # registered the folder after Quartermaster - mods.ini had to change, and
    # the loop rule refused that restart with a FAIL. Now: one automatic
    # restart, then stable.
    lives = [B.Life(FP, apply=B.Apply(FP2, changed=1, mods=True)),
             B.Life(FP3, mods=True, known_fp=FP2), B.Life(FP3)]
    trace, m = B.simulate(lives)
    assert [(p.apply, r.restart, r.kind, r.refused) for p, r, _m in trace] == [
        (False, False, B.NONE, None), (True, True, B.APPLY, None),
        (False, True, B.AUTO, None), (False, False, B.NONE, None)]
    assert trace[-1][0].why == B.STABLE and m.rows == 0
    # Before: the same starts without the exception.
    lives[1] = B.Life(FP3, mods=True)
    trace, _m = B.simulate(lives)
    assert trace[2][1].refused == B.LOOP


def test_next_marker_counts_the_chain():
    p = B.boot_plan(None, FP, False, False)
    r = B.restart_plan(None, p, FP, 1, False)
    n = B.next_marker(None, p, r, FP, 1, True, 1, [(b"x", b"5")])
    assert (n.gen, n.hash, n.phase, n.rows, n.rhash, n.rcount, n.rk, n.boots) == (
        1, FP, B.WRITTEN, 1, FP, 1, B.AUTO, 1)
    # The next start finds the same inputs: nothing to do, the chain ends.
    p2 = B.boot_plan(n, FP, False, False)
    r2 = B.restart_plan(n, p2, FP, 0, False)
    n2 = B.next_marker(n, p2, r2, FP, 0, True, 0, [])
    assert (n2.phase, n2.rows, n2.rhash, n2.rcount, n2.rk, n2.outs) == (
        B.BOOTING, 0, b"-", 0, B.NONE, [(b"x", b"5")])
    assert B.tick(n2).phase == B.BOOTED


def test_a_failed_generation_leaves_the_marker_for_a_retry():
    m = M(gen=2, hash=FP, outs=[(b"x", b"5")])
    p = B.boot_plan(m, FP2, False, False)
    r = B.restart_plan(m, p, FP2, 0, False)
    n = B.next_marker(m, p, r, FP2, 3, False, 0, [])
    assert (n.gen, n.hash, n.outs) == (2, FP, [(b"x", b"5")])


# ------------------------------------------------------------- scenarios
def test_i1_quartermaster_alone_is_stable_after_the_first_boot():
    # The shipped copies carry the generation constant of Quartermaster alone,
    # so the first generation changes nothing (M4: every output `same`).
    trace, m = B.simulate([B.Life(FP, changed=0), B.Life(FP)])
    assert B.auto_restarts(trace) == 0
    assert [p.why for p, _r, _m in trace] == [B.FIRST, B.STABLE]
    # With a first generation that does change a file: exactly one restart.
    trace, m = B.simulate([B.Life(FP, changed=1), B.Life(FP), B.Life(FP)])
    assert B.auto_restarts(trace) == 1
    assert [p.why for p, _r, _m in trace] == [B.FIRST, B.STABLE, B.STABLE]
    assert m.phase == B.BOOTED and m.rows == 0


def test_i5_an_unstable_fingerprint_gets_one_restart_then_fail():
    lives = [B.Life(B.unstable_fp(FP, k), changed=1) for k in range(1, 7)]
    trace, m = B.simulate(lives[:2])
    assert B.auto_restarts(trace) == 1
    assert trace[1][1].refused == B.LOOP
    # Started again by hand, and again: never two restarts in a row, and the
    # loop is refused after every one.
    trace, m = B.simulate(lives)
    kinds = [(r.restart, r.refused) for _p, r, _m in trace]
    assert kinds == [(True, None), (False, B.LOOP), (True, None), (False, B.LOOP),
                     (False, B.IN_A_ROW), (False, B.IN_A_ROW)]


def test_unstable_outputs_with_a_stable_fingerprint_restart_once_per_hash():
    trace, _m = B.simulate([B.Life(FP, changed=1), B.Life(FP, damaged=True, changed=1),
                            B.Life(FP, damaged=True, changed=1)])
    assert [(r.restart, r.refused) for _p, r, _m in trace] == [
        (True, None), (False, B.PER_HASH), (False, B.PER_HASH)]


def test_i6_restored_hook_files_regenerate_and_restart_once():
    trace, m = B.simulate([B.Life(FP, changed=3), B.Life(FP)])
    assert B.auto_restarts(trace) == 1
    # A Workshop update puts the shipped copies back: same inputs, damaged.
    trace, m = B.simulate([B.Life(FP, damaged=True, changed=2), B.Life(FP)], m)
    assert [p.why for p, _r, _m in trace] == [B.DAMAGED, B.STABLE]
    assert B.auto_restarts(trace) == 1


def test_i7_a_shuffled_mods_ini_is_restored_with_one_restart():
    # The engine lists a freshly deployed mod after Quartermaster, so the
    # first boot reorders and restarts; the next start needs nothing and ends
    # that chain, the shuffle's test restart follows, and the boot after it
    # may restart once more for the same fingerprint.
    trace, m = B.simulate([B.Life(FP, mods=True), B.Life(FP, restart=B.TEST),
                           B.Life(FP, mods=True), B.Life(FP)])
    assert [(r.restart, r.kind, r.why, r.refused) for _p, r, _m in trace] == [
        (True, B.AUTO, B.MODSINI, None), (False, B.NONE, B.NOTHING, None),
        (True, B.AUTO, B.MODSINI, None), (False, B.NONE, B.NOTHING, None)]
    assert [(n.rows, n.rcount, n.rk) for _p, _r, n in trace] == [
        (1, 1, B.AUTO), (0, 0, B.TEST), (1, 1, B.AUTO), (0, 0, B.NONE)]
    # Shuffled in the life of the first boot's own restart, the order is back
    # on disk at the next boot but that restart is refused (the first I7 run).
    trace, _m = B.simulate([B.Life(FP, mods=True), B.Life(FP, mods=True)])
    assert [(r.restart, r.refused) for _p, r, _m in trace] == [(True, None),
                                                               (False, B.PER_HASH)]


def test_d10_a_reorder_in_the_manager_regenerates_restarts_once_and_is_stable():
    # The order is in the fingerprint (FP2: the new order). The first boot
    # merges and restarts; in the next life the player moves a mod up and
    # applies: the winner changes, one Apply restart; the next boot computes
    # FP2 from the saved order and is stable.
    trace, m = B.simulate([B.Life(FP, changed=1),
                           B.Life(FP, apply=B.Apply(FP2, changed=1, mods=True)),
                           B.Life(FP2)])
    assert [(p.apply, p.why, r.restart, r.kind, r.why) for p, r, _m in trace] == [
        (False, B.FIRST, True, B.AUTO, B.OUTPUTS),
        (False, B.STABLE, False, B.NONE, B.NOTHING),
        (True, B.APPLIED, True, B.APPLY, B.OUTPUTS),
        (False, B.STABLE, False, B.NONE, B.NOTHING)]
    assert B.auto_restarts(trace) == 1
    assert (m.hash, m.phase, m.rows, m.rk) == (FP2, B.BOOTED, 0, B.NONE)


def test_d10_a_reorder_that_changes_no_file_still_restarts_for_mods_ini():
    trace, m = B.simulate([B.Life(FP), B.Life(FP, apply=B.Apply(FP2, changed=0, mods=True)),
                           B.Life(FP2)])
    assert [(r.restart, r.kind, r.why) for _p, r, _m in trace[1:]] == [
        (False, B.NONE, B.NOTHING), (True, B.APPLY, B.MODSINI), (False, B.NONE, B.NOTHING)]
    assert trace[-1][0].why == B.STABLE


def test_d10_an_outside_reorder_keeps_the_fingerprint_and_is_put_back():
    # The saved order is authoritative: modman's order is no input, the boot
    # rewrites mods.ini and restarts once for it, as I7 does.
    trace, _m = B.simulate([B.Life(FP), B.Life(FP, mods=True), B.Life(FP)])
    assert [(p.why, r.restart, r.why) for p, r, _m in trace] == [
        (B.FIRST, False, B.NOTHING), (B.STABLE, True, B.MODSINI), (B.STABLE, False, B.NOTHING)]


def test_d10_no_apply_while_the_boot_restarts():
    trace, _m = B.simulate([B.Life(FP, changed=1, apply=B.Apply(FP2, changed=1))])
    assert len(trace) == 1 and not trace[0][0].apply


def test_a_suspected_brick_falls_back_and_keeps_the_fallback():
    wrote = B.Life(FP, changed=2)                       # generation 1 written, restart
    died = B.Life(FP, menu=False)                       # that start never reached the menu

    def wta_changes(plan):
        return 1 if plan.mode == B.WTA else 0

    after = B.Life(FP, changed=wta_changes)
    trace, m = B.simulate([wrote, died, after, B.Life(FP), B.Life(FP2, changed=1)])
    whys = [p.why for p, _r, _m in trace]
    assert whys == [B.FIRST, B.STABLE, B.SUSPECT, B.KEPT, B.INPUTS]
    assert trace[2][0].mode == B.WTA and trace[3][2].mode == B.WTA
    # The start that died still booted and needed no restart, so the chain
    # was over: the fallback may restart once, into files without a merge.
    assert (trace[2][1].restart, trace[2][1].kind) == (True, B.AUTO)
    # New inputs end the fallback.
    assert trace[4][2].mode == B.NORMAL


def test_an_mp_sync_boot_touches_nothing():
    m = M(gen=4, hash=FP, rows=1, rhash=FP, rcount=1, outs=[(b"x", b"1")])
    trace, n = B.simulate([B.Life(FP2, sync=True, changed=5, mods=True)], m)
    p, r, n = trace[0]
    assert not p.regen and r.refused == B.SYNC
    assert (n.gen, n.hash, n.rows, n.rhash, n.rcount, n.outs) == (4, FP, 1, FP, 1, m.outs)


def test_restart_timing():
    due = B.restart_due(100)
    assert due == 111
    assert B.restart_now(110, due, True, False) == b"wait"
    assert B.restart_now(111, due, True, False) == b"restart"
    assert B.restart_now(111, due, False, False) == b"wait"
    assert B.restart_now(111, due, True, True) == b"wait"
    assert B.restart_now(due + B.WINDOW_TENTHS + 1, due, True, False) == b"drop"
    # Floor(t*10) is at most one tenth late: 11 tenths are at least 1 s.
    for t in (5.0, 5.01, 5.09, 5.0999):
        now = int(t * 10)
        assert (B.restart_due(now)) / 10.0 - t >= 1.0


def test_the_boot_restarts_at_once_only_after_rewriting_what_it_loaded():
    """Hands-on, 2026-10-14: the outputs this process loaded were made with
    the mod's old build, the old DoProgress did not compile, and a restart
    left to the tick never came. A start that rewrote its outputs restarts at
    the end of its boot; the others still wait for the tick."""
    m = M(gen=297, hash=FP, phase=B.BOOTED)
    p = B.boot_plan(m, FP2, False, False)
    r = B.restart_plan(m, p, FP2, 9, False)
    n = B.next_marker(m, p, r, FP2, 298, True, 9, [])
    assert (p.why, r.kind, r.why, n.phase) == (B.INPUTS, B.AUTO, B.OUTPUTS, B.WRITTEN)
    assert B.restart_at_boot(r, n)
    assert not B.restart_at_boot(r, n, map_loaded=True)
    # mods.ini alone: the marker stays as the start set it.
    for phase in (B.BOOTED, B.WRITTEN):
        m2 = M(gen=3, hash=FP, phase=phase)
        p2 = B.boot_plan(m2, FP, False, False)
        r2 = B.restart_plan(m2, p2, FP, 0, True)
        n2 = B.next_marker(m2, p2, r2, FP, 4, True, 0, [])
        assert (r2.restart, r2.why) == (True, B.MODSINI) and not B.restart_at_boot(r2, n2)
    # A generation that did not finish: `booting` waits for the confirm.
    m3 = M(gen=3, hash=FP, phase=B.WRITTEN)
    p3 = B.boot_plan(m3, FP2, False, False)
    r3 = B.restart_plan(m3, p3, FP2, 2, False)
    n3 = B.next_marker(m3, p3, r3, FP2, 4, False, 2, [])
    assert r3.restart and n3.phase == B.BOOTING and not B.restart_at_boot(r3, n3)
    # An Apply: the player's restart, after the window's notice.
    pa = B.boot_plan(M(hash=FP), FP2, False, False, apply=True)
    ra = B.restart_plan(M(hash=FP), pa, FP2, 1, False)
    na = B.next_marker(M(hash=FP), pa, ra, FP2, 2, True, 1, [])
    assert (ra.kind, na.phase) == (B.APPLY, B.WRITTEN) and not B.restart_at_boot(ra, na)
    # Refused or not wanted: nothing to restart, whatever the plan's kind says.
    assert not B.restart_at_boot(B.RestartPlan(True, False, B.NONE, B.OUTPUTS, B.LOOP),
                                 M(phase=B.WRITTEN))
    assert not B.restart_at_boot(B.RestartPlan(True, False, B.AUTO, B.OUTPUTS, None),
                                 M(phase=B.WRITTEN))


def test_the_2026_10_14_switch_restarts_once_and_the_next_start_is_clean():
    # Generation 297 booted with the old build; the new build changes the
    # inputs, the boot rewrites nine files and restarts by itself - whether or
    # not a main-menu frame ever runs - and the start after it is stable.
    trace, m = B.simulate([B.Life(FP, changed=0), B.Life(FP2, changed=9, menu=False),
                           B.Life(FP2)], M(gen=296, hash=FP, phase=B.BOOTED))
    assert [p.why for p, _r, _n in trace] == [B.STABLE, B.INPUTS, B.STABLE]
    assert [B.restart_at_boot(r, n) for _p, r, n in trace] == [False, True, False]
    assert B.auto_restarts(trace) == 1
    assert (m.phase, m.rows, m.rk) == (B.BOOTED, 0, B.NONE)


# ------------------------------------------------------------ exhaustive
PHASES = (B.WRITTEN, B.BOOTING, B.BOOTED)
MODES = (B.NORMAL, B.WTA)
KINDS = (B.AUTO, B.APPLY, B.TEST, B.NONE)


def markers():
    yield None
    for phase, mode, rows, rh, rc, rk, h in itertools.product(
            PHASES, MODES, range(4), (FP, FP2, b"-"), range(3), KINDS, (FP, FP2)):
        yield B.Marker(gen=5, hash=h, phase=phase, mode=mode, rows=rows, rhash=rh,
                       rcount=rc, rk=rk, boots=9, outs=[(b"x", b"1")])


def test_every_decision_keeps_the_guards():
    seen = 0
    for m in markers():
        for sync, dmg, changed, mods, apply in itertools.product(
                (False, True), (False, True), (0, 1), (False, True), (False, True)):
            p = B.boot_plan(m, FP, sync, dmg, apply=apply)
            r = B.restart_plan(m, p, FP, changed if p.regen else 0, mods)
            n = B.next_marker(m, p, r, FP, 6, True, changed if p.regen else 0, [(b"y", b"2")])
            seen += 1
            if sync:
                assert not p.regen and not r.restart
                assert (n.gen, n.hash, n.outs) == ((m.gen, m.hash, m.outs) if m else (0, b"-", []))
                assert (n.rows, n.rhash, n.rcount) == ((m.rows, m.rhash, m.rcount) if m else (0, b"-", 0))
            if not ((changed if p.regen else 0) or mods):
                assert not r.restart and r.refused is None
            if r.restart and r.kind == B.AUTO:
                assert not apply and not sync
                assert not (p.followed and FP != m.hash)
                assert m is None or m.rows < B.MAX_IN_A_ROW
                assert not (m is not None and m.rhash == FP and m.rcount >= B.MAX_PER_HASH)
                assert n.rows <= B.MAX_IN_A_ROW and n.rhash == FP and n.rcount == 1
                assert n.rk == B.AUTO
            if r.restart and r.kind == B.APPLY:
                assert apply and (n.rows, n.rhash, n.rcount, n.rk) == (0, b"-", 0, B.APPLY)
            # The boot's own restart: an automatic one after this start's
            # generation changed a file, never for mods.ini alone; every other
            # automatic restart leaves the marker for the tick to confirm.
            if B.restart_at_boot(r, n):
                assert r.kind == B.AUTO and r.why == B.OUTPUTS and not apply and not sync
                assert p.regen and changed and n.phase == B.WRITTEN
            elif r.restart and r.kind == B.AUTO:
                assert r.why == B.MODSINI and n.phase != B.WRITTEN
            if not p.regen:
                assert (n.gen, n.hash, n.outs) == ((m.gen, m.hash, m.outs) if m else (0, b"-", []))
            else:
                assert (n.gen, n.hash, n.outs) == (6, FP, [(b"y", b"2")])
                if changed:
                    assert n.phase == B.WRITTEN
            if not apply and not sync and m is not None and m.phase == B.BOOTING and m.hash == FP:
                assert p.regen and p.mode == B.WTA
            if not apply and not r.restart:
                assert n.rk == B.NONE
            if apply:
                assert n.boots == (m.boots if m else 0)
                if not (p.regen and changed):
                    assert n.phase == (m.phase if m else B.BOOTED)
            else:
                assert n.boots == (m.boots if m else 0) + 1
    assert seen > 50000


def test_no_sequence_of_starts_restarts_more_than_twice_in_a_row():
    """Any run of starts in which every generation changes a file and the
    fingerprint does what it likes: never more than two automatic restarts
    back to back, never two for one fingerprint in a chain."""
    fps = (FP, FP2, FP3)
    for seq in itertools.product(fps, repeat=6):
        trace, _m = B.simulate([B.Life(f, changed=1, damaged=True) for f in seq])
        row = 0
        hashes = []
        for (p, r, _n), f in zip(trace, seq):
            if r.restart:
                row += 1
                assert f not in hashes
                hashes.append(f)
            else:
                row, hashes = 0, []
            assert row <= 1


def test_a_selftest_run_holds_every_restart_but_its_own():
    p = B.boot_plan(None, FP, False, False)
    r = B.restart_plan(None, p, FP, 1, True, held=True)
    assert (r.restart, r.refused) == (False, B.HELD)
    pa = B.boot_plan(M(hash=FP), FP, False, False, apply=True)
    assert B.restart_plan(M(hash=FP), pa, FP, 1, False, held=True).refused == B.HELD
    # Held is not a stable start: the chain's counters stay.
    m = M(hash=FP, rows=1, rhash=FP, rcount=1, rk=B.AUTO)
    p = B.boot_plan(m, FP, False, True)
    r = B.restart_plan(m, p, FP, 1, False, held=True)
    n = B.next_marker(m, p, r, FP, 2, True, 1, [])
    assert (n.rows, n.rhash, n.rcount) == (1, FP, 1)
    # Without anything to restart for, held changes nothing.
    assert B.restart_plan(None, B.boot_plan(None, FP, False, False), FP, 0, False,
                          held=True).refused is None
