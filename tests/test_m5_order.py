"""Gates for the mods.ini half of ref/order.py: the engine's layout, the
canonical rows, and every refusal of the writer (plan G5, S8, S11)."""
import os

import pytest

from ref import order as O

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Cossacks 3"
#: The mods.ini the game wrote during the capability-probe run (M0), with the
#: probe folder it had appended at the end.
CAP = (b"section.begin\r\n   mods : struct.begin\r\n"
       b"      [*] : struct.begin\r\n         dir = mods\\SW_Frontline_Protocol\r\n"
       b"         dis = True\r\n      struct.end\r\n"
       b"      [*] : struct.begin\r\n         dir = ..\\..\\workshop\\content\\333420\\873048118\r\n"
       b"         dis = True\r\n      struct.end\r\n"
       b"      [*] : struct.begin\r\n         dir = mods\\QmProbe\r\n"
       b"         dis = False\r\n      struct.end\r\n   struct.end\r\nsection.end\r\n\r\n")
LIVE = os.path.join(GAME, "mods", "mods.ini")
W = b"..\\..\\workshop\\content\\333420\\"
QM = b"mods\\Quartermaster"
SWFP = b"mods\\SW_Frontline_Protocol"


def read(path):
    with open(path, "rb") as fh:
        return fh.read()


def test_the_model_rebuilds_a_file_the_engine_wrote():
    data = CAP
    rows, problem = O.parse_mods_ini(data)
    assert problem is None
    assert rows == [(SWFP, b"True"), (W + b"873048118", b"True"), (b"mods\\QmProbe", b"False")]
    assert O.render_mods_ini(rows) == data


@pytest.mark.skipif(not os.path.isfile(LIVE), reason="installed game not found")
def test_the_model_rebuilds_the_installed_mods_ini():
    data = read(LIVE)                      # read only
    rows, problem = O.parse_mods_ini(data)
    assert problem is None and O.render_mods_ini(rows) == data


BASE = [(SWFP, b"True"), (W + b"873048118", b"True"), (b"mods\\QMTestWASD", b"False"),
        (QM, b"False"), (b"mods\\QMTestCamSpeed", b"False")]


def engine(rows):
    return [(d, not O.is_off(dis)) for d, dis in rows]


def test_canonical_rows_keep_every_flag_and_put_quartermaster_last():
    rows = O.canonical_rows(BASE, QM)
    assert rows == [(W + b"873048118", b"True"), (b"mods\\QMTestCamSpeed", b"False"),
                    (b"mods\\QMTestWASD", b"False"), (SWFP, b"True"), (QM, b"False")]


def test_an_apply_changes_only_the_flags_it_names_and_never_quartermasters():
    intent = {O.norm_dir(b"mods\\QMTestCamSpeed"): True, O.norm_dir(QM): True,
              O.norm_dir(SWFP): False}
    rows = O.canonical_rows(BASE, QM, intent)
    assert dict(rows)[b"mods\\QMTestCamSpeed"] == O.TRUE
    assert dict(rows)[SWFP] == O.FALSE
    assert dict(rows)[QM] == b"False"


def test_the_first_boot_under_the_owners_baseline_reorders_but_needs_no_restart():
    # The player's two disabled entries, then what the game appended for the
    # folders a run deployed (M0: at the end, in folder order).
    rows = [(SWFP, b"True"), (W + b"873048118", b"True"), (b"mods\\QMTestCamSpeed", b"False"),
            (b"mods\\QMTestWASD", b"False"), (QM, b"False")]
    data = O.render_mods_ini(rows)
    plan = O.mods_ini_plan(engine(rows), data, O.canonical_rows(rows, QM))
    assert plan.action == b"write" and not plan.effective and not O.needs_restart(plan)
    again = O.mods_ini_plan(engine(rows), O.render_mods_ini(plan.rows), plan.rows)
    assert again.action == b"same"


def test_a_shuffle_is_an_effective_change():
    canon = O.canonical_rows(BASE, QM)
    shuffled = [canon[-1]] + canon[:-1]              # Quartermaster first
    plan = O.mods_ini_plan(engine(shuffled), O.render_mods_ini(shuffled), canon)
    assert plan.action == b"write" and plan.effective and O.needs_restart(plan)
    # The same rows already on disk while the game still runs the old order.
    same = O.mods_ini_plan(engine(shuffled), O.render_mods_ini(canon), canon)
    assert same.action == b"same" and O.needs_restart(same)


def test_a_flag_that_means_the_same_keeps_the_files_spelling():
    rows = [(b"mods\\A", b"true"), (QM, b"False")]
    plan = O.mods_ini_plan(engine(rows), O.render_mods_ini(rows),
                           [(b"mods\\A", O.TRUE), (QM, O.FALSE)])
    assert plan.action == b"same" and plan.rows[0] == (b"mods\\A", b"true")


def mutate(data, old, new):
    assert old in data
    return data.replace(old, new, 1)


@pytest.mark.parametrize("change, why", [
    (lambda d: None, b"missing"),
    (lambda d: b"garbage\r\n", b"layout"),
    (lambda d: mutate(d, b"   mods : struct.begin", b"   mod : struct.begin"), b"layout"),
    (lambda d: mutate(d, b"         dis = True\r\n", b"         dis = True\r\n         tag = 1\r\n"),
     b"entry"),
    (lambda d: mutate(d, b"         dis = True\r\n", b""), b"entry"),
    (lambda d: mutate(d, b"dis = True", b"dis = maybe"), b"dis"),
    (lambda d: mutate(d, b"mods\\QMTestWASD", b"mods\\Other"), b"dirs"),
    (lambda d: mutate(d, b"mods\\QMTestWASD", b"mods\\QMTestCamSpeed"), b"dirs"),
])
def test_the_writer_refuses_what_it_does_not_understand(change, why):
    data = change(O.render_mods_ini(BASE))
    plan = O.mods_ini_plan(engine(BASE), data, O.canonical_rows(BASE, QM))
    assert (plan.action, plan.why) == (b"refused", why)


def test_count_mismatches_are_refused_before_the_file_is_read():
    data = O.render_mods_ini(BASE)
    assert O.mods_ini_plan(engine(BASE[:-1]), data, O.canonical_rows(BASE[:-1], QM)).why == b"count"
    assert O.mods_ini_plan(engine(BASE), data, BASE[:-1]).why == b"count"
    assert O.mods_ini_plan(engine(BASE), None, BASE[:-1]).why == b"count"
    many = [(b"mods\\m%d" % i, b"False") for i in range(257)]
    assert O.mods_ini_plan(engine(many), O.render_mods_ini(many), many).why == b"count"


def test_dirs_are_compared_folded():
    rows = [(b"MODS\\QMTestWASD\\", b"False"), (QM, b"False")]
    plan = O.mods_ini_plan([(b"mods\\qmtestwasd", True), (QM, True)], O.render_mods_ini(rows),
                           [(b"mods/QMTestWASD", b"False"), (QM, b"False")])
    assert plan.action == b"write" and not plan.effective


def test_moved_past_names_the_mods_quartermaster_moved_over_when_only_it_moved():
    qm, a, b, c = b"q", b"a", b"b", b"c"
    assert O.moved_past([qm, a, b], [a, b, qm], qm) == [a, b]
    assert O.moved_past([a, qm, b], [a, b, qm], qm) == [b]
    assert O.moved_past([a, b, qm], [qm, a, b], qm) == [a, b]
    assert O.moved_past([a, b, qm], [a, b, qm], qm) is None          # nothing moved
    assert O.moved_past([qm, a, b], [b, a, qm], qm) is None          # the others moved too
    assert O.moved_past([a, b], [a, b, qm], qm) is None              # not enabled before
    assert O.moved_past([qm, a, c], [a, b, qm], qm) is None


def test_no_restart_for_a_move_of_quartermaster_past_mods_that_share_no_file():
    new = O.norm_dir(b"mods/Testowy")
    rows = [(QM, b"False"), (b"mods/Testowy", b"False")]
    engine_rows = [(d, True) for d, _x in rows]
    wanted = [rows[1], rows[0]]
    plan = O.mods_ini_plan(engine_rows, O.render_mods_ini(rows), wanted, self_dir=QM)
    assert plan.effective and plan.over == [new]
    assert O.needs_restart(plan)                                   # nobody asked
    assert not O.needs_restart(plan, lambda d: False)
    assert O.needs_restart(plan, lambda d: d == new)
    # Without self_dir the plan cannot tell: a restart, as before.
    assert O.mods_ini_plan(engine_rows, O.render_mods_ini(rows), wanted).over is None
