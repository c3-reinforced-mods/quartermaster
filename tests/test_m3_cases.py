"""Gates for tools/m3cases.py: the merge cases the SelfTest runs in game.

The generator must be deterministic, every expected file must be what ref/
computes from the very files the game will read, the named cases must have the
figures the milestone asks for, and the comparer must find a difference."""
import hashlib
import json
import os
import shutil

import pytest

import m3cases as C
from ref import diff as D
from ref import inc as I
from ref import merge as M

#: progresswarai.inc as of 2026-09-28, and the four inputs the in-game Myers
#: run of the capability probes read (cap.0.log:186-207); m0_fixture must
#: rebuild them byte for byte, so the D and hunk figures below are that run's.
PROGRESSWARAI_SHA = "3619629eca407be4cad33527c1fcb24cf7cfe32170f1be4ec1ee1908eff76fb6"
M0_SHA = {
    50: "6bca05ac8f47c2fa2410d7e5d940207abe4e33098e77c1df4ebe901418650499",
    300: "a90918d59b0ed95965bdccd32fb5e62c9a29288de84368c93922a3e3fa4a5b80",
    500: "e8a39b71411e26798ccef09c762d262ade997130b0697f88f52abe93edaefe51",
    600: "0664d4323e503ef3018ed771bdc7b9b6712c8ef1dba30212959e016aeba0410c",
}
#: D and hunks the game logged for b50/b300/b500; b600 went over that run's
#: cap of 706 and fits the cap of 998.
M0_FIGURES = {50: (67, 50), 300: (400, 298), 500: (667, 496), 600: (800, 587)}


@pytest.fixture(scope="module")
def built(game_dir, reference_dir):
    cases = C.build_cases(game_dir, reference_dir)
    files, manifest = C.render_tree(cases, game_dir)
    return cases, files, dict((m["name"], m) for m in manifest)


def named(manifest, tag):
    hits = [m for n, m in manifest.items() if n.split("_", 2)[2] == tag]
    assert len(hits) == 1, tag
    return hits[0]


def test_the_generator_is_deterministic(built, game_dir, reference_dir):
    _cases, files, _m = built
    again, _ = C.render_tree(C.build_cases(game_dir, reference_dir), game_dir)
    assert C.tree_digest(again) == C.tree_digest(files)


def test_at_least_300_cases_with_every_outcome(built):
    cases, _files, manifest = built
    assert len(cases) >= 300
    assert len(set(c.name for c in cases)) == len(cases)
    outcomes = set((m["mode"], m["status"], m["reason"]) for m in manifest.values())
    assert outcomes >= {("merged", "ok", None), ("merged", "warn", None),
                        ("vanilla", "ok", None), ("winner", "fail", "too-different"),
                        ("winner", "fail", "too-many-lines"),
                        ("winner", "warn", "replacement")}
    assert sum(1 for m in manifest.values() if m["conflicts"]) >= 50
    assert sum(1 for m in manifest.values() if m["proximity"]) >= 50
    assert sum(1 for m in manifest.values() if m["hook_lines"]) >= 20
    assert sum(1 for m in manifest.values() if len(m["participants"]) >= 3) >= 50


def test_the_named_cases(built):
    _c, _f, manifest = built
    p5 = named(manifest, "probe5")
    assert (p5["hunks"], p5["conflicts"], p5["lines"]) == (5, 1, 74)
    for stem in ("hotkeysettings", "oncamera", "registershortcuts"):
        m = named(manifest, "wasd_camspeed_" + stem)
        assert (m["mode"], m["status"], m["conflicts"], m["proximity"]) == ("merged", "ok", 0, 0)
    m = named(manifest, "wasd_conflict_oncamera")
    assert (m["conflicts"], m["status"]) == (1, "warn")
    assert m["participants"] == ["mods\\QMTestConflict", "mods\\QMTestWASD"]
    m = named(manifest, "repl_wta")
    assert (m["mode"], m["status"], m["reason"], m["winner"]) == ("winner", "warn", "replacement", 1)
    assert named(manifest, "repl_alone")["mode"] == "merged"
    assert named(manifest, "repl_same")["mode"] == "merged"
    assert named(manifest, "repl_half")["mode"] == "merged"
    assert named(manifest, "repl_half_plus")["reason"] == "replacement"
    cap = D.d_cap(D.DEFAULT_BUDGET)
    m = named(manifest, "dcap_998")
    assert (m["mode"], m["d"]) == ("merged", [cap])
    m = named(manifest, "dcap_999")
    assert (m["mode"], m["status"], m["reason"], m["winner"], m["d"]) == (
        "winner", "fail", "too-different", 1, [None])
    assert named(manifest, "dcap_b750")["reason"] == "too-different"
    assert named(manifest, "too_many_lines")["reason"] == "too-many-lines"
    assert named(manifest, "vanilla_only")["mode"] == "vanilla"


def test_the_hook_files_get_the_hook_block_at_the_s5_index(built):
    """cameracontrol.inc 8, doprogress.inc 10, the other two 0 in vanilla; in
    the output the block sits at the index of the merged lines."""
    cases, files, manifest = built
    seen = {}
    for c in cases:
        if "hook-file" not in c.tags:
            continue
        out = I.parse(files["expected/%s.inc" % c.name].rstrip(b" ")).values
        k = next(i for i in range(len(out)) if out[i:i + len(c.hook)] == c.hook)
        rest = out[:k] + out[k + len(c.hook):]
        assert k == I.hook_index(rest), c.name
        seen[c.name.split("_", 2)[2]] = k
    assert seen["hookfile_cameracontrol"] > 8          # a line went into the routine
    assert seen["hookfile_doprogress"] >= 10
    assert seen["hookfile_initminimap"] == seen["hookfile_eventmainmenu"] == 0
    assert named(manifest, "hookfile_cameracontrol_wta")["mode"] == "winner"


def test_the_m0_cases_are_the_inputs_the_game_diffed(built, game_dir):
    _c, _f, manifest = built
    data = C.vanilla(game_dir, C.PROGRESSWARAI)
    if hashlib.sha256(data).hexdigest() != PROGRESSWARAI_SHA:
        pytest.skip("progresswarai.inc changed since the capability probes")
    for n, sha in sorted(M0_SHA.items()):
        assert hashlib.sha256(C.m0_fixture(data, n, n)).hexdigest() == sha, n
        m = named(manifest, "m0_b%d" % n)
        assert (m["d"][0], m["part_hunks"][0]) == M0_FIGURES[n], n


def test_every_expected_file_is_ref_on_the_files_the_game_reads(built, game_dir):
    cases, files, manifest = built
    suite = I.parse(files[C.FIXTURE + "/m3/" + C.SUITE]).values
    assert len(suite) == len(cases)
    for value, case in zip(suite, cases):
        words = value[1:].split(b" ")
        assert words[0] == b"case" and words[1].decode() == case.name
        base = words[2].decode("ascii").replace("\\", "/")
        parts = []
        for k, path in enumerate(words[4:]):
            rel = path.decode("ascii")
            assert rel.startswith(C.GAME_REL)
            parts.append((b"p%d" % k, files[C.FIXTURE + "/m3/" + rel[len(C.GAME_REL):]]))
        hook = None
        if words[3] != b"-":
            rel = words[3].decode("ascii")
            hook = I.parse(files[C.FIXTURE + "/m3/" + rel[len(C.GAME_REL):]]).values
        result, out = M.merge_inc(C.vanilla(game_dir, "data/" + base), parts, hook=hook,
                                  writer="raw")
        want_rows = C.dump_bytes(M.result_rows(result))
        assert files["expected/%s.txt" % case.name] == want_rows, case.name
        if M.final_lines(result, hook) is None:
            assert "expected/%s.inc" % case.name not in files
        else:
            assert files["expected/%s.inc" % case.name] == out, case.name
        assert manifest[case.name]["mode"] == result.mode


def test_the_fixture_overrides_no_game_file_and_is_what_the_game_can_read(built):
    _c, files, _m = built
    for rel, data in files.items():
        if not rel.startswith(C.FIXTURE + "/"):
            continue
        inner = rel[len(C.FIXTURE) + 1:]
        assert not inner.lower().startswith("data/"), rel
        assert inner == "mod.ini" or inner.startswith("m3/"), rel
        assert all(c.isalnum() or c in "_./" for c in inner), rel
        if rel.endswith(".inc"):
            I.parse(data)
    case = I.parse(files["cases/" + C.CASE_FILE])
    assert case.name == b"qmTestCase"
    assert case.values == [b";kind merge", b";suite " + (C.GAME_REL + C.SUITE).encode()]


def test_participant_files_keep_vanilla_bytes_around_the_code(built, game_dir):
    cases, _f, _m = built
    for case in cases:
        if "random" not in case.tags:
            continue
        v = I.parse(C.vanilla(game_dir, case.base))
        for _mod, data in case.parts:
            p = I.parse(data)
            assert (p.head, p.tail) == (v.head, v.tail), case.name


def test_the_written_tree_is_up_to_date(built):
    if not os.path.isdir(C.OUT):
        pytest.skip("fixtures/m3cases not generated (python tools/m3cases.py)")
    _c, files, _m = built
    assert C.tree_digest(C.read_tree(C.OUT)) == C.tree_digest(files), (
        "fixtures/m3cases is stale: run python tools/m3cases.py")


# ------------------------------------------------------------ the comparer
def _fake_run(built, tmp_path):
    """The expected files laid out as a perfect SelfTest out folder."""
    _c, files, manifest = built
    root = tmp_path / "expected_root"
    for rel, data in files.items():
        if rel.startswith("expected/") or rel == "manifest.json":
            path = root.joinpath(*rel.split("/"))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    out = tmp_path / "qm_test_out"
    shutil.copytree(root / "expected", out)
    summary = b"".join(b"m3case|%s|1|%s|1|0|0|0|0\r\n"
                       % (n.encode(), b"yes" if m["output"] else b"none")
                       for n, m in manifest.items())
    (out / "qm_m3.txt").write_bytes(summary + b"m3|%d|0\r\n" % len(manifest))
    return str(root), out


def test_compare_accepts_a_perfect_run_and_catches_each_kind_of_mismatch(built, tmp_path):
    root, out = _fake_run(built, tmp_path)
    assert C.compare(str(out), root)[0] == []
    _c, _f, manifest = built
    name = next(n for n, m in manifest.items() if m["output"])
    rows = (out / (name + ".txt")).read_bytes()
    (out / (name + ".txt")).write_bytes(rows.replace(b"merged", b"winner", 1))
    problems, _ = C.compare(str(out), root)
    assert len(problems) == 1 and "rows differ" in problems[0]
    (out / (name + ".txt")).write_bytes(rows)
    (out / (name + ".inc")).unlink()
    problems, _ = C.compare(str(out), root)
    assert len(problems) == 1 and "no output file" in problems[0]
    assert C.compare(str(out), root, rows_only=True)[0] == []


def test_manifest_is_json_the_comparer_reads(built):
    _c, files, manifest = built
    assert json.loads(files["manifest.json"].decode("ascii"))[0]["name"] in manifest
