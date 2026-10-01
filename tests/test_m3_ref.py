"""Gates for what M3 added to ref.merge: the hook step, the final line list,
the two writers of merge_inc, and result_rows - the rows the game side dumps."""
import hashlib

import pytest

from conftest import vanilla_bytes
from ref import inc as I
from ref import merge as M
from test_ref_merge import ONCAMERA, ONCAMERA_SHA, PROBE5_MERGED_SHA, probe5_mods

V10 = [b";v%d" % i for i in range(10)]
HOOK = [b";// hook 1", b";// hook 2"]


def edited(repl, base=V10):
    out = list(base)
    for i, line in sorted(repl.items(), reverse=True):
        if line is None:
            del out[i]
        else:
            out[i] = line
    return out


def inc_file(values, name=b"X"):
    return (b"section.begin\r\n   Name = " + name + b"\r\n   Code : struct.begin\r\n"
            + b"".join(I.CODE_PREFIX + v + b"\r\n" for v in values)
            + b"   struct.end\r\nsection.end\r\n\r\n")


ROUTINE = [b";procedure qmX(n : Integer);", b";begin", b";   Log('x');", b";end;",
           b";", b";const cA = 1;", b";qmX(cA);"]


# ------------------------------------------------------------ the hook step
def test_hook_lines_go_on_top_of_code_that_starts_with_a_statement():
    assert M.insert_hook([b";a", b";b"], HOOK) == HOOK + [b";a", b";b"]
    assert M.insert_hook([], HOOK) == HOOK
    assert M.insert_hook([b";a"], []) == [b";a"]


def test_hook_lines_go_after_the_routines_a_state_starts_with():
    """Plan S5: before the first top-level Code line after leading routines."""
    assert I.hook_index(ROUTINE) == 5
    assert M.insert_hook(ROUTINE, HOOK) == ROUTINE[:5] + HOOK + ROUTINE[5:]


def test_the_hook_index_is_taken_on_the_merged_lines():
    # A participant adds a line inside the leading routine: the hook moves down
    # with the code it follows, it is not placed by vanilla's index.
    inside = ROUTINE[:2] + [b";   Log('inside');"] + ROUTINE[2:]
    r = M.merge(ROUTINE, [(b"A", inside)])
    assert M.final_lines(r, HOOK) == inside[:6] + HOOK + inside[6:]


def test_final_lines_of_each_mode():
    merged = M.merge(V10, [(b"A", edited({4: b";A4"}))])
    assert M.final_lines(merged) == merged.lines
    assert M.final_lines(merged, HOOK) == HOOK + merged.lines
    plain = M.merge(V10, [(b"A", list(V10))])
    assert plain.mode == "vanilla" and M.final_lines(plain, HOOK) == HOOK + V10
    winner = M.merge(V10, [(b"R", [b";R%d" % i for i in range(8)] + V10[8:]),
                           (b"S", edited({9: b";S9"}))])
    assert winner.mode == "winner"
    # Nothing is written for winner-takes-all; with hook lines the winner's
    # own lines get them on top.
    assert M.final_lines(winner) is None
    assert M.final_lines(winner, HOOK) == HOOK + edited({9: b";S9"})


def test_hook_lines_never_take_part_in_the_diff():
    # A participant that happens to carry the same line as the hook does not
    # conflict with it or deduplicate against it: the hook is added afterwards.
    a = [HOOK[0]] + V10
    r = M.merge(V10, [(b"A", a)])
    assert [(h.start, h.end, h.status) for h in r.hunks] == [(0, 0, M.CLEAN)]
    assert M.final_lines(r, HOOK) == HOOK + a


# --------------------------------------------------------------- the writers
def test_parser_writer_is_the_probe5_bytes_and_raw_is_the_same_lines(game_dir):
    vanilla = vanilla_bytes(ONCAMERA)
    if hashlib.sha256(vanilla).hexdigest() != ONCAMERA_SHA:
        pytest.skip("oncamera.inc changed since probe 5")
    a, b = probe5_mods(vanilla)
    mods = [(b"A", a), (b"B", b)]
    r, out = M.merge_inc(vanilla, mods, writer="parser")
    assert hashlib.sha256(out).hexdigest() == PROBE5_MERGED_SHA
    r2, raw = M.merge_inc(vanilla, mods, writer="raw")
    # The raw writer pads the file with spaces to a multiple of 4 bytes.
    assert raw.rstrip(b" ") == out and len(raw) % 4 == 0 and len(raw) - len(out) < 4
    assert M.result_rows(r) == M.result_rows(r2)


def test_raw_writer_keeps_a_shorter_result_short_and_parser_pads_it():
    vanilla = inc_file(V10)
    shorter = inc_file(edited({i: None for i in (2, 3, 4)}))
    r, parser = M.merge_inc(vanilla, [(b"A", shorter)], writer="parser")
    assert I.parse(parser).values == edited({i: None for i in (2, 3, 4)}) + [b";"] * 3
    r, raw = M.merge_inc(vanilla, [(b"A", shorter)], writer="raw")
    assert I.parse(raw.rstrip(b" ")).values == edited({i: None for i in (2, 3, 4)})


def test_hook_lines_come_before_the_padding():
    vanilla = inc_file(V10)
    shorter = inc_file(edited({i: None for i in (2, 3, 4)}))
    r, parser = M.merge_inc(vanilla, [(b"A", shorter)], hook=HOOK, writer="parser")
    want = HOOK + edited({i: None for i in (2, 3, 4)})
    assert I.parse(parser).values == want + [b";"]
    r, raw = M.merge_inc(vanilla, [(b"A", shorter)], hook=HOOK, writer="raw")
    assert I.parse(raw.rstrip(b" ")).values == want


def test_winner_with_hook_rewrites_the_winners_file():
    vanilla = inc_file(V10)
    rewrite = inc_file([b";R%d" % i for i in range(8)] + V10[8:], b"R")
    small = inc_file(edited({9: b";S9"}), b"S")
    r, out = M.merge_inc(vanilla, [(b"R", rewrite), (b"S", small)])
    assert r.mode == "winner" and out == small
    r, out = M.merge_inc(vanilla, [(b"R", rewrite), (b"S", small)], hook=HOOK, writer="raw")
    got = I.parse(out.rstrip(b" "))
    assert got.name == b"S" and got.values == HOOK + edited({9: b";S9"})


def test_unknown_writer_is_refused():
    with pytest.raises(ValueError):
        M.merge_inc(inc_file(V10), [(b"A", inc_file(V10))], writer="stream")


# ------------------------------------------------------------ result_rows
def test_probe5_rows(game_dir):
    vanilla = vanilla_bytes(ONCAMERA)
    if hashlib.sha256(vanilla).hexdigest() != ONCAMERA_SHA:
        pytest.skip("oncamera.inc changed since probe 5")
    a, b = probe5_mods(vanilla)
    r, _out = M.merge_inc(vanilla, [(b"A", a), (b"B", b)])
    assert M.result_rows(r) == [
        b"merge|merged|warn|-|-1|5|1|1|74",
        b"part|0|1|-|3|1|2|8|0",
        b"part|1|1|-|6|3|3|25|0",
        b"hunk|0|0|0|0|1|proximity|-1",
        b"hunk|1|0|6|7|1|conflict-lost|3",
        b"hunk|2|1|1|2|1|proximity|-1",
        b"hunk|3|1|6|7|1|conflict-won|-1",
        b"hunk|4|1|72|73|1|clean|-1",
        b"prox|0|2"]


def test_rows_of_a_diff_given_up_list_the_participants_up_to_it():
    a = [b";A%d" % i for i in range(10)]
    r = M.merge(V10, [(b"A", a), (b"B", edited({1: b";B"})), (b"C", list(V10))], budget=20)
    rows = M.result_rows(r)
    assert rows[0] == b"merge|winner|fail|too-different|2|0|0|0|10"
    assert rows[1:] == [b"part|0|0|too-different|-1|-1|-1|%d|0" % r.participants[0].cells]
    assert r.participants[0].cells == 15    # rounds 0..4, the last that fits 20


def test_rows_of_a_replacement_and_of_nothing_changed():
    rewrite = [b";R%d" % i for i in range(8)] + V10[8:]
    r = M.merge(V10, [(b"R", rewrite), (b"S", edited({9: b";S9"}))])
    assert M.result_rows(r) == [b"merge|winner|warn|replacement|1|0|0|0|10",
                                b"part|0|1|-|16|8|8|%d|1" % r.participants[0].cells,
                                b"part|1|1|-|2|1|1|%d|0" % r.participants[1].cells]
    r = M.merge(V10, [(b"A", list(V10))])
    assert M.result_rows(r) == [b"merge|vanilla|ok|-|-1|0|0|0|10", b"part|0|1|-|0|0|0|0|0"]


def test_by_names_the_duplicated_and_the_winning_hunk():
    same = edited({4: b";X"})
    r = M.merge(V10, [(b"A", same), (b"B", list(same)), (b"C", edited({4: b";C"}))])
    rows = [row for row in M.result_rows(r) if row.startswith(b"hunk")]
    # B duplicates A; A then loses to C, which wins the conflict.
    assert rows == [b"hunk|0|0|4|5|1|conflict-lost|2",
                    b"hunk|1|1|4|5|1|duplicate|0",
                    b"hunk|2|2|4|5|1|conflict-won|-1"]


def test_pairs_are_recorded_in_the_order_they_are_found():
    a = edited({2: b";A2", 7: b";A7"})
    b = edited({4: b";B4", 9: b";B9"})
    r = M.merge(V10, [(b"A", a), (b"B", b)])
    assert r.pairs == [(0, 2), (2, 1), (1, 3)]
    assert len(r.pairs) == r.proximity_pairs
    assert [row for row in M.result_rows(r) if row.startswith(b"prox")] == [
        b"prox|0|2", b"prox|2|1", b"prox|1|3"]
