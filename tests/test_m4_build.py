"""Build gates for the M4 states: they are emitted where the runtime loads
them, pass every lint of tools/hbuild.py, the SelfTest runs the new kind, and
the CameraControl hook lines the M4 runs use pass the hook rules."""
import os

import pytest

import hbuild as H
import m4cases as C
from ref import selftest as S
from ref import validate as V

CORE = ("qmGenerate", "qmReport", "qmValFiles", "qmReportLoad")


@pytest.fixture(scope="module")
def built(game_dir):
    return H.build(game_dir=game_dir)


def test_the_states_are_emitted_and_lint_clean(built):
    where = dict((name, into) for name, into, _src in built.states)
    for name in CORE:
        assert where[name] == "data/quartermaster/core.aix"
        assert b"   Name = " + name.encode() + b"\r\n" in built.outputs[where[name]]
    assert where["qmCaseM4"] == "data/quartermaster/selftest.aix"
    mine = set(CORE) | {"qmCaseM4"}
    assert [f for f in built.findings if f.state in mine] == []


def test_the_selftest_runs_the_m4_kind():
    assert b"m4gen" in S.KINDS
    with open(os.path.join(H.REPO, "src", "states", "qmselftest.pas"), "rb") as fh:
        text = fh.read()
    assert (b"if (qmStKind='m4gen') then\n   StateMachineExecuteState(qmStT, 'qmCaseM4', 0)"
            in text.replace(b"\r\n", b"\n"))


def test_the_camera_hook_lines_of_the_m4_runs_pass_the_hook_rules(game_dir):
    hooks = dict((h.into, h) for h in H.load_hooks())
    hook = hooks["data/gui/menu.inc/cameracontrol.inc"]
    with open(os.path.join(game_dir, "data", "gui", "menu.inc", "cameracontrol.inc"), "rb") as fh:
        vanilla = fh.read()
    env = H.LintEnv.from_game(game_dir)
    for lines in (C.PROPOSED_HOOK,
                  V.inc_lines(C.hook_files()["cameracontrol.inc"])[1]):
        code = [l[1:] if l.startswith(b";") else l for l in lines]
        data, span = H.assemble_hook(hook, vanilla, code)
        assert H.lint_state(hook.into, "CameraControl", data, 0, env, hook_lines=span) == []
        assert len(code) <= H.HOOK_MAX_LINES
        assert sum(1 for l in code if V.is_gen_line(b";" + l)) == 1


def test_a_fresh_install_finds_its_shipped_hook_copies_current(built, game_dir):
    """Quartermaster alone: every candidate the generation would write equals,
    by token, the hooked copy the build ships - so the first generation writes
    nothing and needs no restart (plan I1). Holds once the CameraControl
    template carries the generation line with the build's alone value."""
    entries = C.idx_entries()
    inp = C.offline_inputs((), game_dir, entries=entries)
    inp.hooks = dict((k.rsplit("/", 1)[-1], v) for k, v in built.outputs.items()
                     if k.startswith("data/quartermaster/hooks/"))
    if not inp.hooks:
        pytest.skip("the build ships no pristine hook lines yet")
    shipped = dict((k[len("data/"):].replace("/", "\\").encode(), v)
                   for k, v in built.outputs.items() if k.startswith("data/gui/menu.inc/"))
    g = C.run_generation(inp, C.decisions_for(inp, entries), C.duplicate_var_oracle,
                         dict(shipped))
    cam = V.inc_lines(built.outputs["data/gui/menu.inc/cameracontrol.inc"])[1]
    if not any(V.is_gen_line(v) for v in cam):
        pytest.skip("the CameraControl template has no generation line yet")
    assert [(r.path, r.written) for r in g.paths] == [(p, b"same") for p in sorted(shipped)]
    assert g.changed == 0


def test_a_shipped_generation_line_has_the_form_the_generator_replaces():
    """Whoever owns the hook template: a line that sets qmHookGen is exactly
    `const qmHookGen = '<value>';`, the one form qmGenerate rewrites."""
    for h in H.load_hooks():
        variables = H.build_variables([x.into for x in H.load_hooks()])
        for line in H.render_lines(h, H._vars_for(h, variables)):
            if b"qmhookgen" in line.lower() and b"const" in line.lower():
                assert V.is_gen_line(b";" + line) and line.endswith(b"';"), line
