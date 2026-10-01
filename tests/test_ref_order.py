"""Gates for ref.order (canonical mod order) and ref.fingerprint."""
import itertools
import random

from ref import fingerprint as FP
from ref import inc as I
from ref import order as O
from ref import textio as T

W = b"..\\..\\workshop\\content\\333420\\"
QM = b"mods\\Quartermaster"


def test_identity_of_the_dir_forms_the_engine_lists():
    # mods\mods.ini:4,8 and ModLibraryGetData (r5c.0.log:13-17)
    assert O.identity(b"mods\\SW_Frontline_Protocol") == (O.LOCAL, b"SW_Frontline_Protocol")
    assert O.identity(W + b"873048118") == (O.WORKSHOP, b"873048118")
    assert O.identity(b"C:\\elsewhere\\x") == (O.OTHER, b"C:\\elsewhere\\x")
    assert O.identity(W + b"12ab") == (O.OTHER, W + b"12ab")


def test_canonical_order_rules():
    dirs = [QM, b"mods\\zeta", W + b"1000", b"mods\\Alpha", W + b"999",
            b"odd\\place", b"mods\\beta"]
    assert O.canonical_order(dirs, self_dir=QM) == [
        W + b"999", W + b"1000",                        # Workshop by number
        b"mods\\Alpha", b"mods\\beta", b"mods\\zeta",   # local, case folded
        b"odd\\place",                                  # anything else
        QM]                                             # Quartermaster last


def test_order_does_not_depend_on_input_order():
    dirs = [QM, b"mods\\QMTestWASD", b"mods\\QMTestConflict", W + b"873048118",
            b"mods\\SW_Frontline_Protocol"]
    want = O.canonical_order(dirs, self_dir=QM)
    for perm in itertools.permutations(dirs):
        assert O.canonical_order(list(perm), self_dir=QM) == want
    assert want[-1] == QM


def test_self_is_recognised_in_any_spelling():
    assert O.canonical_order([b"MODS\\quartermaster\\", b"mods\\zz"],
                             self_dir=QM) == [b"mods\\zz", b"MODS\\quartermaster\\"]


def test_fixture_order_used_by_the_merge_gates():
    got = O.canonical_order([b"mods\\QMTestWASD", b"mods\\QMTestCamSpeed",
                             b"mods\\QMTestConflict", b"mods\\QMTestBroken"])
    assert got == [b"mods\\QMTestBroken", b"mods\\QMTestCamSpeed",
                   b"mods\\QMTestConflict", b"mods\\QMTestWASD"]


# ----------------------------------------------------------------- fingerprint
MODS = [(W + b"873048118", True, 1552431982),
        (b"mods\\SW_Frontline_Protocol", False, 123),
        (QM, True, 999),
        (b"mods\\QMTestWASD", True, 1790000000)]


def test_fingerprint_text_is_canonical_and_leaves_quartermaster_out():
    text = FP.fingerprint_text(MODS, 1700000000, b"0.1", self_dir=QM)
    assert text == (b"qm-fingerprint 1\nqm 0.1\nvanilla 1700000000\n"
                    b"w 873048118 on 1552431982\n"
                    b"l QMTestWASD on 1790000000\n"
                    b"l SW_Frontline_Protocol off\n")


def test_fingerprint_is_stable_and_reacts_only_to_inputs():
    base = FP.fingerprint(MODS, 1700000000, b"0.1", self_dir=QM)
    shuffled = list(reversed(MODS))
    assert FP.fingerprint(shuffled, 1700000000, b"0.1", self_dir=QM) == base
    # Quartermaster's own stamp changes on every write: not an input.
    own = [(d, e, 5 if d == QM else s) for d, e, s in MODS]
    assert FP.fingerprint(own, 1700000000, b"0.1", self_dir=QM) == base
    # A disabled mod's stamp is not an input either; its flag is.
    off = [(d, e, 7 if not e else s) for d, e, s in MODS]
    assert FP.fingerprint(off, 1700000000, b"0.1", self_dir=QM) == base
    on = [(d, True, s) for d, e, s in MODS]
    assert FP.fingerprint(on, 1700000000, b"0.1", self_dir=QM) != base
    # Enabled stamps, vanilla and version are inputs.
    upd = [(d, e, s + 1 if d.startswith(W) else s) for d, e, s in MODS]
    assert FP.fingerprint(upd, 1700000000, b"0.1", self_dir=QM) != base
    assert FP.fingerprint(MODS, 1700000002, b"0.1", self_dir=QM) != base
    assert FP.fingerprint(MODS, 1700000000, b"0.2", self_dir=QM) != base


def test_qhash_never_leaves_32_bit_integer_range():
    (m1, p1), (m2, p2) = FP.H1, FP.H2
    assert (p1 - 1) * m1 + 256 <= FP.INT_MAX
    assert (p2 - 1) * m2 + 256 <= FP.INT_MAX
    rng = random.Random(9)
    for _ in range(200):
        data = bytes(rng.randrange(256) for _ in range(rng.randint(0, 200)))
        h1 = h2 = 0
        for b in data:
            assert h1 * m1 + b + 1 <= FP.INT_MAX and h2 * m2 + b + 1 <= FP.INT_MAX
            h1 = (h1 * m1 + b + 1) % p1
            h2 = (h2 * m2 + b + 1) % p2
        assert FP.qhash(data) == b"%d-%d-%d" % (h1, h2, len(data))


def test_qhash_known_values():
    assert FP.qhash(b"") == b"0-0-0"
    assert FP.qhash(b"A") == b"66-66-1"
    assert FP.qhash(b"AB") == b"17029-17425-2"


# ------------------------------------------------------------ load order
SWFP = b"mods\\SW_Frontline_Protocol"
WASD = b"mods\\QMTestWASD"
CONF = b"mods\\QMTestConflict"
NEW = b"mods\\QMTestNew"
WS = W + b"873048118"
REG = [SWFP, WS, WASD, QM, CONF]            # mods.ini order, as the engine lists it


def _dirs(lo, dirs=REG):
    return [dirs[i] for i in lo.rows]


def test_order_cfg_round_trips_and_is_the_known_cfg_shape():
    dirs = [WASD, b"mods\\a|b", b"mods\\\xd0\x9c", b"mods\\ lead"]
    data = O.render_order(dirs)
    assert O.parse_order(data) == dirs
    assert data == T.write_file(I.layout_lines(O.ORDER_KEYS,
                                               [T.escape(v) for v in O.order_values(dirs)]))
    assert data.startswith(b"section.begin\r\n   Name = qmOrder\r\n   Code : struct.begin\r\n")
    assert b"      [*] = ;o|mods\\a|b\r\n" in data and len(data) % 4 == 0
    assert O.render_order(list(dirs)) == data            # the same order, the same bytes


def test_what_is_not_an_order_cfg_is_no_saved_order():
    assert O.parse_order(None) is None
    assert O.parse_order(b"garbage\r\n") is None
    no_format = T.write_file(I.layout_lines(O.ORDER_KEYS, [b";o~124mods\\x", b";o~124mods\\y"]))
    assert O.parse_order(no_format) is None
    # A format line and no dir says nothing (rule 3 over nothing is rule 1).
    only = T.write_file(I.layout_lines(O.ORDER_KEYS, [b";format~1241", b";x"]))
    assert O.parse_order(only) is None


def test_no_saved_order_is_mods_ini_s_own_order_and_writes_nothing():
    # The default: the order the game loads without Quartermaster, Quartermaster moved last.
    lo = O.load_order(REG, QM, None)
    assert _dirs(lo) == [SWFP, WS, WASD, CONF, QM] and lo.src == b"ini"
    assert (lo.save, lo.ext, lo.unseen, lo.dropped) == (False, False, [], [])
    assert not lo.canon                             # canonical: WS, CONF, WASD, SWFP
    assert O.order_file_after(lo, None) == (b"same", None)
    # A mods.ini already in canonical order stays in it, and says so.
    canon = O.canonical_order(REG, QM)
    lo = O.load_order(canon, QM, None)
    assert _dirs(lo, canon) == canon and lo.canon


def test_the_saved_order_rules():
    saved = [CONF, b"mods\\Gone", WASD, SWFP]
    lo = O.load_order(REG, QM, saved)
    # Placed in the saved order, the unseen one after them, Quartermaster last.
    assert _dirs(lo) == [CONF, WASD, SWFP, WS, QM]
    assert lo.src == b"saved" and [REG[i] for i in lo.unseen] == [WS]
    assert lo.dropped == [b"mods\\Gone"]
    assert lo.ext                                  # mods.ini had SWFP, WASD, CONF
    assert lo.save == [CONF, WASD, SWFP, WS]
    assert not lo.canon
    act, data = O.order_file_after(lo, O.render_order(saved))
    assert act == b"written" and O.parse_order(data) == lo.save
    # Written back, the next boot changes nothing.
    again = O.load_order(REG, QM, lo.save)
    assert again.rows == lo.rows and again.save is False and again.unseen == []


def test_unseen_mods_keep_mods_ini_s_order_among_themselves_before_quartermaster():
    # The engine appends a new folder, so mods.ini has them in the order they came.
    dirs = [WASD, QM, W + b"20", b"mods\\zz", W + b"3", b"mods\\Aa"]
    lo = O.load_order(dirs, QM, [WASD])
    assert _dirs(lo, dirs) == [WASD, W + b"20", b"mods\\zz", W + b"3", b"mods\\Aa", QM]


def test_ext_asks_only_about_the_mods_the_saved_order_places():
    # Quartermaster first and a new folder after it (the engine appends new
    # folders) is not an outside reorder; the placed mods swapped is.
    assert not O.load_order([QM, CONF, WASD, NEW], QM, [CONF, WASD]).ext
    assert O.load_order([QM, WASD, CONF, NEW], QM, [CONF, WASD]).ext


def test_spelling_follows_the_engine_and_matching_is_folded():
    lo = O.load_order([b"MODS\\qmtestwasd\\", QM, CONF], QM, [CONF, WASD])
    assert lo.save == [CONF, b"MODS\\qmtestwasd\\"]


def test_every_placed_mod_gone_is_mods_ini_s_order_again_and_deletes_the_file():
    lo = O.load_order(REG, QM, [b"mods\\Gone"])
    assert lo.src == b"ini" and _dirs(lo) == [SWFP, WS, WASD, CONF, QM]
    assert lo.save is None and lo.dropped == [b"mods\\Gone"]
    assert O.order_file_after(lo, b"x") == (b"deleted", None)


def test_canon_looks_at_the_enabled_mods_only():
    on = [False, False, True, True, True]           # SWFP and the Workshop item off
    lo = O.load_order(REG, QM, [SWFP, WS, CONF, WASD], enabled=on)
    assert lo.canon                                 # CONF, WASD, QM: canonical
    lo = O.load_order(REG, QM, [WASD, CONF], enabled=on)
    assert not lo.canon


def test_an_apply_order_is_saved_and_mods_ini_s_own_one_deletes_the_file():
    wanted = [WASD, CONF, SWFP, QM, WS]              # Quartermaster not last: moved there
    lo = O.apply_order(REG, QM, None, wanted)
    assert lo.src == b"apply" and _dirs(lo) == [WASD, CONF, SWFP, WS, QM]
    assert lo.save == [WASD, CONF, SWFP, WS] and not lo.ext
    ini = [SWFP, WS, WASD, CONF, QM]                 # rule 1's order for REG
    reset = O.apply_order(REG, QM, lo.save, ini)
    assert _dirs(reset) == ini and reset.save is None
    assert O.order_file_after(reset, O.render_order(lo.save)) == (b"deleted", None)
    # No file and rule 1's order asked for: nothing to write or delete.
    assert O.apply_order(REG, QM, None, ini).save is False
    # The same order as saved: nothing to write.
    assert O.apply_order(REG, QM, lo.save, wanted).save is False
    # Auto-sort's canonical order is saved like any order the player sets.
    canon = O.canonical_order(REG, QM)
    auto = O.apply_order(REG, QM, None, canon)
    assert _dirs(auto) == canon and auto.save == canon[:-1] and auto.canon


def test_an_apply_order_that_does_not_list_every_mod_once_is_not_used():
    saved = [CONF, WASD, SWFP, WS]
    for wanted, why in (([WASD, CONF, QM], b"count"),
                        ([WASD, CONF, SWFP, WS, b"mods\\Other"], b"dirs"),
                        ([WASD, WASD, SWFP, WS, QM], b"dirs")):
        lo = O.apply_order(REG, QM, saved, wanted)
        assert lo.why == why and lo.src == b"saved" and _dirs(lo) == saved + [QM]
    assert O.apply_order(REG, QM, saved, None).rows == O.load_order(REG, QM, saved).rows


def test_nothing_is_written_during_an_mp_sync_or_without_quartermaster():
    lo = O.load_order(REG, QM, [CONF, WASD])
    assert lo.save
    assert O.order_file_after(lo, None, sync=True) == (b"same", None)
    assert O.order_file_after(lo, None, self_known=False) == (b"same", None)


def test_load_rows_arrange_mods_ini_and_keep_each_flag():
    ini = [(d, O.TRUE if d in (SWFP, WS) else O.FALSE) for d in REG]
    lo = O.load_order(REG, QM, [WASD, CONF])
    rows = O.load_rows(ini, QM, lo, {O.norm_dir(CONF): True, O.norm_dir(QM): True})
    assert rows == [(WASD, O.FALSE), (CONF, O.TRUE), (SWFP, O.TRUE), (WS, O.TRUE),
                    (QM, O.FALSE)]
    assert O.load_rows(ini, QM, O.load_order(REG, QM)) == [ini[0], ini[1], ini[2], ini[4],
                                                           ini[3]]


# --------------------------------------------------------- window moves
def test_up_down_and_move_keep_inactive_rows_and_quartermaster_in_place():
    #        rows: 0 SWFP (off), 1 WS, 2 WASD, 3 QM, 4 CONF
    order = [1, 0, 4, 2, 3]
    pend = [False, True, True, True, True]
    assert O.ui_move(order, pend, 3, 2, b"up") == ([1, 0, 2, 4, 3], True, None)
    assert O.ui_move(order, pend, 3, 4, b"up") == ([4, 0, 1, 2, 3], True, None)
    assert O.ui_move(order, pend, 3, 1, b"up") == (order, False, O.UI_FIRST)
    assert O.ui_move(order, pend, 3, 2, b"down") == (order, False, O.UI_LAST)
    assert O.ui_move(order, pend, 3, 1, b"move", 2) == ([4, 0, 2, 1, 3], True, None)
    assert O.ui_move(order, pend, 3, 1, b"move", 99) == ([4, 0, 2, 1, 3], True, None)
    assert O.ui_move(order, pend, 3, 2, b"move", -5) == ([2, 0, 1, 4, 3], True, None)
    assert O.ui_move(order, pend, 3, 4, b"move", 1) == (order, False, None)
    assert O.ui_move(order, pend, 3, 3, b"up") == (order, False, O.UI_SELF)
    assert O.ui_move(order, pend, 3, 0, b"down") == (order, False, O.UI_INACTIVE)
    assert O.ui_move(order, pend, 3, -1, b"up") == (order, False, O.UI_SELECT)
    assert O.ui_move(order, pend, 3, 1, b"left") == (order, False, O.UI_UNKNOWN)


def test_every_move_is_a_permutation_with_quartermaster_last():
    rng = random.Random(10)
    for _ in range(400):
        n = rng.randint(2, 7)
        order = list(range(n))
        rng.shuffle(order)
        self_row = order[-1]
        pend = [rng.random() < 0.7 or i == self_row for i in range(n)]
        row = rng.randrange(-1, n + 1)
        cmd = rng.choice([b"up", b"down", b"move"])
        new, moved, _why = O.ui_move(order, pend, self_row, row, cmd, rng.randint(-2, n + 2))
        assert sorted(new) == sorted(order) and new[-1] == self_row
        assert moved == (new != order)
        for k, i in enumerate(order):
            if not pend[i]:
                assert new[k] == i                     # an inactive row keeps its slot


# ------------------------------------------------ the fingerprint's order
def test_the_fingerprint_follows_the_load_order():
    canon = FP.fingerprint_text(MODS, 1700000000, b"0.1", self_dir=QM)
    dirs = [d for d, _e, _s in MODS]
    assert FP.fingerprint_text(MODS, 1700000000, b"0.1", QM,
                               O.canonical_order(dirs, QM)) == canon
    mine = [WASD, SWFP, W + b"873048118", QM]
    text = FP.fingerprint_text(MODS, 1700000000, b"0.1", QM, mine)
    assert text == (b"qm-fingerprint 1\nqm 0.1\nvanilla 1700000000\n"
                    b"l QMTestWASD on 1790000000\n"
                    b"l SW_Frontline_Protocol off\n"
                    b"w 873048118 on 1552431982\n")
    assert FP.qhash(text) != FP.qhash(canon)
