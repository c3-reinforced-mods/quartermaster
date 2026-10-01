"""Gates for the boot milestone's part of the build: the four hook files of
plan S5, their pristine lines under data/quartermaster/hooks/, the generation
constant baked into the CameraControl copy, and the hook lines' shape."""
import os
import re

import pytest

import hbuild as H
from ref import inc as I
from ref import textio as T
from ref import validate as V

GAME = H.GAME
needs_game = pytest.mark.skipif(not os.path.isfile(os.path.join(GAME, "cossacks.exe")),
                                reason="installed game not found")


@pytest.fixture(scope="module")
def built():
    return H.build(offline=True)


def hooks():
    return dict((h.into, h) for h in H.load_hooks())


def test_quartermaster_ships_a_hook_for_every_hook_file_of_plan_s5():
    assert sorted(hooks()) == sorted(H.HOOK_FILES)


@needs_game
def test_every_hook_fits_the_limit_and_names_its_hook(built):
    for into, h in hooks().items():
        code = H.hook_code(h, H.build_variables([x for x in hooks()]))
        assert len(code) <= H.HOOK_MAX_LINES, into
    cc = hooks()["data/gui/menu.inc/cameracontrol.inc"]
    im = hooks()["data/gui/menu.inc/initminimap.inc"]
    dp = hooks()["data/gui/menu.inc/doprogress.inc"]
    text = lambda h: b"\n".join(H.hook_code(h, H.BUILD_VARIABLES))
    # The fallbacks name themselves; the boot flag is qm_rt for all three.
    assert b"'hook', 'initminimap'" in text(im) and b"'hook', 'doprogress'" in text(dp)
    for h in (cc, im, dp):
        assert text(h).count(b"ParserSelectByKey('qm_rt')=0") == 1
        assert b"'qmBoot'" in text(h)
    # Main menu only (InitMinimap also runs during a skirmish's map generation).
    for h in (cc, im, dp):
        assert b"gInterface.gamemode=gc_gamemode_mainmenu" in text(h)
    # The priority of plan S5: InitMinimap from its second call, DoProgress
    # only once InitMinimap had its turn.
    assert b"'im')>=2" in text(im) and b"'im')>=2" in text(dp)
    assert b"'qmTick'" in text(dp)


@needs_game
def test_the_shipped_hook_lines_are_the_hooks_code(built):
    for into, h in hooks().items():
        rel = H.hook_lines_rel(h)
        data = built.outputs[rel]
        inc = I.parse(data)
        assert inc.values == [b";" + c for c in H.hook_code(h, _vars(built, h))], rel
        name = re.search(rb"^   Name = (\w+)\r$", built.outputs[into], re.M).group(1)
        assert inc.name == name


def _vars(built, h):
    v = H.build_variables(sorted(hooks()))
    v["hookgen"] = H.qstr(H.alone_hookgen(list(hooks().values()), GAME, v))
    return v


@needs_game
def test_the_generation_constant_is_the_one_of_quartermaster_alone(built):
    cam = built.outputs["data/gui/menu.inc/cameracontrol.inc"]
    m = re.search(rb"      \[\*\] = ;const qmHookGen = '([0-9]+-[0-9]+-[0-9]+)';\r\n", cam)
    assert m, "no generation line in the shipped CameraControl copy"
    paths = sorted(H._vanilla_rel(i) for i in hooks())

    def read(path):
        with open(os.path.join(GAME, "data", *path.decode().split("\\")), "rb") as fh:
            return fh.read()

    def lines(path):
        return I.parse(built.outputs[H.HOOK_LINES_DIR + path.decode().rsplit("\\", 1)[1]]).values

    assert m.group(1) == V.alone_outputs_hash(paths, read, lines)
    assert m.group(1) != H.HOOKGEN_PLACEHOLDER.encode()


@needs_game
def test_the_shipped_copies_are_what_the_alone_generation_writes(built):
    """Token for token: the first generation of Quartermaster alone finds
    every shipped copy equal (the writer's `same`) and restarts nothing."""
    gen = re.search(rb";const qmHookGen = '([^']*)';",
                    built.outputs["data/gui/menu.inc/cameracontrol.inc"]).group(1)
    for into, h in hooks().items():
        path = H._vanilla_rel(into)
        with open(os.path.join(GAME, *into.split("/")), "rb") as fh:
            vkeys, vvalues = V.inc_lines(fh.read())
        hook = [T.escape(v) for v in I.parse(built.outputs[H.hook_lines_rel(h)]).values]
        want = V._hooked(vvalues, hook)
        if path == V.CAMERA:
            want = V.with_generation(want, gen)
        keys, values = V.inc_lines(built.outputs[into])
        assert V.token(keys, values) == V.token(vkeys, want), into
