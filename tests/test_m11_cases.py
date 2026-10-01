"""tools/m11cases.py's --own check over a synthetic run folder: the lives it
expects, the lines a life must not hold, and the new mod's files."""
import os

import m11cases as M
from ref import createmod as CM


def _run(tmp_path, lives, files=True):
    run = str(tmp_path)
    for k, lines in enumerate(lives):
        with open(os.path.join(run, "%d.cos_261001_1200%02d.log" % (k, k)), "wb") as fh:
            fh.write(b"".join(b"LOG| %d |" % n + l.encode("latin-1") + b"\r\n"
                              for n, l in enumerate(lines)))
    if files:
        for rel, data in CM.files(M.OWN_NAME, M.OWN_NAME).items():
            path = os.path.join(run, "created", M.OWN_NAME.decode(), *rel.decode().split("\\"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as fh:
                fh.write(data)
    return run


def _good():
    """Each life's lines: everything it must hold, nothing it must not."""
    return [[w for w in wants if not w.startswith("!")] for wants in M.OWN_LIVES]


def test_the_own_check_accepts_the_lives_it_describes(tmp_path):
    assert M.check_own(_run(tmp_path, _good())) == 0


def test_the_own_check_needs_every_line(tmp_path):
    lives = _good()
    lives[1] = [l for l in lives[1] if "no restart for that" not in l]
    assert M.check_own(_run(tmp_path, lives)) == 1


def test_the_own_check_refuses_a_line_a_life_must_not_hold(tmp_path):
    lives = _good()
    lives[1].append("[qm] boot report FAIL No automatic restart: the mods changed again")
    assert M.check_own(_run(tmp_path, lives)) == 1


def test_the_own_check_counts_the_lives(tmp_path):
    assert M.check_own(_run(tmp_path, _good() + [["[qm] boot version"]])) == 1


def test_the_own_check_needs_the_new_mods_files(tmp_path):
    assert M.check_own(_run(tmp_path, _good(), files=False)) == 1


def test_the_own_case_file_names_the_folder_and_its_own_restart():
    case = M.case_files(own=True)[M.CASE]
    assert b";name QMTestFresh" in case and b";own 1" in case and b";local" not in case
