"""Gates for tools/m5cases.py: the case files, the I7 seed, the run requests
(every one a valid hrun command) and the checks of a run folder."""
import json
import os
import shlex

import pytest

import hrun
import m5cases as C
from ref import boot as B
from ref import order as O
from ref import selftest as S

QM = b"mods\\Quartermaster"


def test_every_case_file_is_an_m5_case_the_selftest_reads():
    for name in C.CASES:
        kind, directives = S.parse_case(C.case_bytes(name))
        assert kind == b"m5" and directives == C.CASES[name]
    assert b"m5" in S.KINDS


def test_the_switch_case_names_are_the_ones_the_boot_asks_for():
    boot = open(os.path.join(C.REPO, "src", "states", "qmboot.pas"), "rb").read()
    assert b"'qm_test\\cases\\qm_m5_restart.cfg'" in boot
    assert b"'qm_test\\cases\\qm_m5_unstable.cfg'" in boot
    assert {"qm_m5_restart.cfg", "qm_m5_unstable.cfg"} <= set(C.CASES)


def test_the_i7_seed_knows_everything_but_the_new_folder():
    dirs = [b"mods\\SW_Frontline_Protocol", b"..\\..\\workshop\\content\\333420\\873048118"]
    entries = B.parse_known(C.seed_known(dirs))
    assert entries == [(d, False) for d in dirs] + [(QM, False)]
    _e, new, _c = B.update_known(entries, dirs + [QM, b"mods\\QMTestNew"])
    assert new == [b"mods\\QMTestNew"]


def test_prepare_writes_cases_fixture_and_seed(tmp_path, monkeypatch):
    game = tmp_path / "game"
    (game / "mods" / "A").mkdir(parents=True)
    # The seeds follow the folders, as hrun's composition does: a row of the
    # player's mods.ini whose folder is gone is not a mod the run has.
    (game / "mods" / "mods.ini").write_bytes(
        O.render_mods_ini([(b"mods\\A", b"True"), (b"mods\\Gone", b"True")]))
    vanilla = game.joinpath("data", *C.NEW_SHIPS.split("\\"))
    vanilla.parent.mkdir(parents=True)
    vanilla.write_bytes(b"section.begin\r\n   x = 1\r\nsection.end\r\n")
    out, fixtures = tmp_path / "cases", tmp_path / "fixtures"
    assert C.prepare(str(out), str(fixtures), str(game), echo=lambda *_: None) == 0
    assert sorted(os.listdir(out)) == sorted(list(C.CASES) + [C.SEED_I7, C.SEED_SAVED])
    assert sorted(os.listdir(fixtures / C.NEW_FIXTURE)) == ["data", "readme.txt"]
    # The game's own copy, byte for byte: a file the index reads (plan S8 chain).
    ships = fixtures.joinpath(C.NEW_FIXTURE, "data", *C.NEW_SHIPS.split("\\"))
    assert ships.read_bytes() == vanilla.read_bytes()
    known = B.parse_known((out / C.SEED_I7 / "known.cfg").read_bytes())
    assert known == [(b"mods\\A", False), (QM, False)]
    assert sorted(os.listdir(out / C.SEED_SAVED)) == ["known.cfg", "order.cfg"]
    assert O.parse_order((out / C.SEED_SAVED / "order.cfg").read_bytes()) == [b"mods\\A"]


def test_the_saved_order_seed_is_a_manual_order():
    dirs = [b"mods\\SW_Frontline_Protocol", W + b"873048118", QM]
    saved = O.parse_order(C.seed_order(dirs))
    assert saved == [b"mods\\SW_Frontline_Protocol", W + b"873048118"]
    assert saved != O.canonical_order(saved)
    # The run then places the new folder after it, before Quartermaster.
    run = dirs[:2] + [QM, NEWF]
    lo = O.load_order(run, QM, saved)
    assert [run[i] for i in lo.rows] == saved + [NEWF, QM] and lo.save == saved + [NEWF]


def test_every_run_request_is_a_valid_hrun_command():
    names = []
    for s in C.scenarios():
        argv = shlex.split(C.command(s).replace("\\", "/"))
        assert argv[:2] == ["python", "tools/hrun.py"]
        _recover, opts = hrun.parse_args(argv[2:])
        assert opts.until == s.until and opts.until_log == s.until_log
        assert opts.run_id == "m5" + s.name and opts.timeout == s.timeout
        assert [os.path.basename(c) for c in opts.cases] == s.cases
        names.append(s.name)
    assert names == ["compile", "i1", "i5", "i6a", "i6b", "i7", "order", "saved", "i8"]


def fake_run(tmp_path, s, lives=None, restarts=None, ini=None, known=None, state="reached",
             order=None, backup=None):
    run = tmp_path / ("m5" + s.name)
    run.mkdir()
    lives = s.lives if lives is None else lives
    for k, want in enumerate(lives):
        lines = [w for w in want if not w.startswith("!")]
        (run / ("%d.cos_260928_1000%02d.log" % (k, k))).write_bytes(
            "\r\n".join("LOG| %d |%s" % (i, w) for i, w in enumerate(lines)).encode("latin-1"))
    summary = {"state": state, "restarts": s.restarts if restarts is None else restarts,
               "sweep": {"ok": True, "problems": []}, "brick_suspected": False}
    (run / "summary.json").write_text(json.dumps(summary))
    if ini is not None:
        (run / "mods.ini.during").write_bytes(O.render_mods_ini(ini))
    if backup is not None:
        (run / "mods.ini.backup").write_bytes(O.render_mods_ini(backup))
    if known is not None or order is not None:
        (run / "qm_save").mkdir()
    if known is not None:
        (run / "qm_save" / "known.cfg").write_bytes(B.render_known(known))
    if order is not None:
        (run / "qm_save" / "order.cfg").write_bytes(O.render_order(order))
    return str(run)


W = b"..\\..\\workshop\\content\\333420\\"
NEWF = b"mods\\QMTestNew"
WASD = b"mods\\QMTestWASD"
CONF = b"mods\\QMTestConflict"
SWFP = b"mods\\SW_Frontline_Protocol"



#: mods.ini as a run starts (hrun's mods.ini.backup) and as the game leaves
#: it: its own order kept (plan S11), the folder the engine registered during the
#: run after it, Quartermaster last.
START = [(W + b"873048118", b"True"), (SWFP, b"True"), (QM, b"False")]
KEPT = [(W + b"873048118", b"True"), (SWFP, b"True"), (NEWF, b"False"), (QM, b"False")]


@pytest.mark.parametrize("name", ["compile", "i1", "i5", "i6a", "i6b", "i7", "i8"])
def test_a_run_that_did_what_its_scenario_says_passes(tmp_path, name):
    s = C.by_name(name)
    ini = KEPT
    if name == "i8":
        ini = [(d, b"True" if d == QM else dis) for d, dis in KEPT]
    run = fake_run(tmp_path, s, ini=ini, known=[(b"mods\\QMTestNew", True)], backup=START)
    problems, facts = C.check_run(run, s)
    assert problems == [], problems


def test_a_run_that_differs_is_caught(tmp_path):
    s = C.by_name("i5")
    lives = [list(s.lives[0]), [w for w in s.lives[1] if "refused=loop" not in w]
             + ["[qm] restart now kind=auto"]]
    problems, _f = C.check_run(fake_run(tmp_path, s, lives=lives, restarts=2), s)
    text = "\n".join(problems)
    assert "2 restart(s), expected 1" in text and "refused=loop" in text
    assert "holds '[qm] restart now'" in text


def test_the_kept_order_starts_from_the_composed_file(tmp_path):
    """hrun lists every installed Workshop item; one the player's mods.ini
    does not list (the published Quartermaster, which its local copy kept out:
    runs m12fulli1-i7) sits among the others in the start, not after them."""
    pub = W + b"3811537510"
    composed = [(W + b"873048118", b"True"), (pub, b"True"), (SWFP, b"True"), (QM, b"False")]
    during = [(W + b"873048118", b"True"), (pub, b"True"), (SWFP, b"True"), (NEWF, b"False"),
              (QM, b"False")]
    run = tmp_path / "run"
    run.mkdir()
    (run / "mods.ini.backup").write_bytes(O.render_mods_ini(START))
    assert C.kept_order_problems(str(run), during)            # the backup alone: wrong
    (run / "mods.ini.composed").write_bytes(O.render_mods_ini(composed))
    assert C.kept_order_problems(str(run), during) == []
    moved = [during[2], during[0], during[1]] + during[3:]
    assert "has not kept the order" in "\n".join(C.kept_order_problems(str(run), moved))


def test_the_seeds_know_what_hrun_composes(tmp_path):
    """Every installed Workshop item and every folder in mods\\, whatever the
    player's mods.ini lists."""
    game = tmp_path / "steamapps" / "common" / "Cossacks 3"
    (game / "mods" / "QMTestWASD").mkdir(parents=True)
    (game / "mods" / "mods.ini").write_bytes(O.render_mods_ini([(SWFP, b"True")]))
    for n in ("873048118", "3811537510"):
        (tmp_path / "steamapps" / "workshop" / "content" / "333420" / n).mkdir(parents=True)
    assert C.installed_dirs(str(game)) == [W + b"3811537510", W + b"873048118",
                                           b"mods\\QMTestWASD"]


def test_the_order_checks_read_mods_ini_as_the_game_left_it(tmp_path):
    s = C.by_name("i7")
    shuffled = [KEPT[-1]] + list(reversed(KEPT[:-1]))
    problems, _f = C.check_run(fake_run(tmp_path, s, ini=shuffled, backup=START,
                                        known=[(b"mods\\QMTestNew", False)]), s)
    text = "\n".join(problems)
    assert "has not kept the order" in text and "not last" in text and "new" in text


def test_a_compile_error_and_two_boots_in_one_log_are_caught(tmp_path):
    s = C.by_name("compile")
    lives = [list(s.lives[0][:-1]) + ["Compile script error: qmTick",
                                       "[qm] boot version 0.0.0 hook=initminimap",
                                       "[qm] boot version 0.0.0 hook=cameracontrol"]]
    problems, _f = C.check_run(fake_run(tmp_path, s, lives=lives, ini=KEPT, backup=START), s)
    text = "\n".join(problems)
    assert "Compile script error: qmTick" in text and "boots in one process" in text


def test_an_incomplete_run_folder_is_reported(tmp_path):
    lines = []
    assert C.check(str(tmp_path), "compile", lines.append) == 2


def _write_line(path, result, before, after):
    return ("[qm] write %s result=%d before abs=%d dst=%d old=raw:3:x staged=3:y flag=1 end=1 "
            "bytes=40 after abs=%d dst=%d back=3:y to mods\\Quartermaster\\data\\%s"
            % (path, result, before, before, after, after, path))


def test_the_stamps_are_what_the_writer_saw():
    a, b, c = "gui/menu.inc/a.inc", "gui/menu.inc/b.inc", "gui/menu.inc/c.inc"
    log = [("0.cos_1.log", [_write_line(a, 2, 100, -1), _write_line(b, 1, 100, 200),
                            _write_line(c, 0, 100, -1)])]
    good = B.Marker(outs=[(a.encode(), b"100"), (b.encode(), b"200"),
                          (b"quartermaster/state/manifest.cfg", b"300")])
    assert C.stamp_problems(log, B.render_marker(good)) == []
    bad = B.Marker(outs=[(a.encode(), b"-1"), (b.encode(), b"100")])
    problems = C.stamp_problems(log, B.render_marker(bad))
    assert len(problems) == 2 and "a.inc is -1, the writer saw 100" in problems[0]
    # Only the last life that wrote counts; no write line, nothing to compare.
    later = log + [("1.cos_2.log", [_write_line(a, 1, 100, 400)])]
    assert C.stamp_problems(later, B.render_marker(good))[0].endswith("saw 400 (result=1)")
    assert C.stamp_problems([("0.log", ["x"])], B.render_marker(bad)) == []


# ------------------------------------------------------------ the load order
def test_the_order_run_that_did_what_it_says_passes(tmp_path):
    s = C.by_name("order")
    ini = [(W + b"873048118", b"True"), (WASD, b"False"), (CONF, b"False"), (SWFP, b"True"),
           (QM, b"False")]
    run = fake_run(tmp_path, s, ini=ini, order=[d for d, _x in ini[:-1]])
    assert C.check_run(run, s)[0] == []


@pytest.mark.parametrize("ini, order, want", [
    ([(CONF, b"False"), (WASD, b"False"), (QM, b"False")], [CONF, WASD],
     "QMTestWASD is not before QMTestConflict"),
    ([(WASD, b"False"), (CONF, b"False"), (QM, b"False")], [CONF, WASD],
     "is not mods.ini's order"),
    ([(WASD, b"False"), (CONF, b"False"), (QM, b"False")], None, "order.cfg is missing"),
    ([(WASD, b"False"), (QM, b"False"), (CONF, b"False")], [WASD, CONF], "not last"),
])
def test_the_order_run_checks_catch_a_wrong_order(tmp_path, ini, order, want):
    s = C.by_name("order")
    problems, _f = C.check_run(fake_run(tmp_path, s, ini=ini, order=order), s)
    assert any(want in p for p in problems), problems


def _saved_seed(tmp_path, saved):
    seed = tmp_path / "seed"
    seed.mkdir()
    (seed / "order.cfg").write_bytes(O.render_order(saved))
    return str(seed)


def test_the_saved_run_that_did_what_it_says_passes(tmp_path):
    s = C.saved_scenario()
    s.state = _saved_seed(tmp_path, [SWFP, W + b"873048118"])
    ini = [(SWFP, b"True"), (W + b"873048118", b"True"), (NEWF, b"False"), (QM, b"False")]
    run = fake_run(tmp_path, s, ini=ini, known=[(NEWF, True)],
                   order=[d for d, _x in ini[:-1]])
    assert C.check_run(run, s)[0] == []


def test_the_saved_run_checks_catch_the_canonical_order(tmp_path):
    s = C.saved_scenario()
    s.state = _saved_seed(tmp_path, [SWFP, W + b"873048118"])
    ini = [(W + b"873048118", b"True"), (NEWF, b"False"), (SWFP, b"True"), (QM, b"False")]
    problems, _f = C.check_run(fake_run(tmp_path, s, ini=ini, known=[(NEWF, True)],
                                        order=[d for d, _x in ini[:-1]]), s)
    assert any("is not the saved order" in p for p in problems), problems


def test_the_order_case_files_are_the_directives_qmcasem5_reads():
    case = open(os.path.join(C.REPO, "src", "states", "qmcasem5.pas"), "rb").read()
    for directive in (b"';step '", b"';mod '", b"';cmd '", b"';to '", b"';reverse 1'"):
        assert directive in case
    assert (b"mod", C.UIORDER_MOD) in C.CASES["qm_m5_uiorder.cfg"]
    assert (b"reverse", b"1") in C.CASES["qm_m5_shufflex.cfg"]


def test_the_saved_run_check_reads_the_seed_hrun_names(tmp_path):
    s = C.saved_scenario()
    s.state = None
    seed = _saved_seed(tmp_path, [SWFP, W + b"873048118"])
    ini = [(SWFP, b"True"), (W + b"873048118", b"True"), (NEWF, b"False"), (QM, b"False")]
    run = fake_run(tmp_path, s, ini=ini, known=[(NEWF, True)], order=[d for d, _x in ini[:-1]])
    assert any("cannot be read" in p for p in C.check_run(run, s)[0])
    path = os.path.join(run, "summary.json")
    summary = json.load(open(path))
    summary["state_seed"] = seed
    with open(path, "w") as fh:
        json.dump(summary, fh)
    assert C.check_run(run, s)[0] == []
