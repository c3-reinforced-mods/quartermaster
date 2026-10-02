"""Shared test setup: import paths, the installed game, and the `slow` marker.

The installed game is read-only input. Tests read vanilla files from it and never
write there; a test that needs the game is skipped when it is not installed.

Slow tests (every vanilla text file, the statement-by-statement reader twin) are
skipped unless `--runslow` is given or QM_SLOW=1 is set, so the default run stays
a routine gate.
"""
import os
import sys

# Before any test imports the reference mod's modules through tools/fixtures.py:
# that mod's folder must not gain a __pycache__.
sys.dont_write_bytecode = True

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for path in (REPO, os.path.join(REPO, "tools")):
    if path not in sys.path:
        sys.path.insert(0, path)

import pytest  # noqa: E402

GAME_DIR = os.environ.get(
    "QM_GAME_DIR", r"C:\Program Files (x86)\Steam\steamapps\common\Cossacks 3")
DATA_DIR = os.path.join(GAME_DIR, "data")
REFERENCE_DIR = os.environ.get(
    "QM_REFERENCE_MOD", os.path.join(GAME_DIR, "mods", "SW_Frontline_Protocol"))

def pytest_addoption(parser):
    parser.addoption("--runslow", action="store_true", default=False,
                     help="also run tests marked slow")


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: long gate, run with --runslow")


def pytest_sessionfinish(session, exitstatus):
    """With QM_PASCOV set, write what the interpreter ran (test_m3_pascal's
    COVERAGE) to <QM_PASCOV>\\<worker>.json, one file per process, so a
    parallel run's workers do not overwrite each other."""
    folder = os.environ.get("QM_PASCOV")
    pas = sys.modules.get("test_m3_pascal")
    if not folder or pas is None:
        return
    import json
    os.makedirs(folder, exist_ok=True)
    worker = os.environ.get("PYTEST_XDIST_WORKER", "main")
    rows = [{"text": text, "lines": sorted(lines), "ran": sorted(ran)}
            for text, (lines, ran) in pas.COVERAGE.items()]
    with open(os.path.join(folder, worker + ".json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh)


#: The tests that take tens of seconds each (interpreted boots, the merge
#: cases, the builds): run first, so a parallel run starts them at once on as
#: many workers instead of finishing on one of them while the others idle.
#: With --dist worksteal that took the full run from 4:10 to 2:40 on 32
#: workers (2026-10-02); with --dist load the order changed nothing.
HEAVY = ("test_m4_pascal.py", "test_m3_pascal.py::test_the_emitted_merge_dumps",
         "test_hbuild.py", "test_m6_screens.py", "test_m4_build.py", "test_m5_build.py",
         "test_m5_pascal.py", "test_ref_textio.py", "test_ref_selftest.py")


def pytest_collection_modifyitems(config, items):
    items.sort(key=lambda item: not any(h in item.nodeid for h in HEAVY))
    if config.getoption("--runslow") or os.environ.get("QM_SLOW") == "1":
        return
    skip = pytest.mark.skip(reason="slow: run with --runslow")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip)


def _walk(root, want):
    out = []
    for dirpath, _dirs, names in os.walk(root):
        for n in names:
            if want(n):
                out.append(os.path.join(dirpath, n))
    return sorted(out)


@pytest.fixture(scope="session")
def game_dir():
    if not os.path.isdir(DATA_DIR):
        pytest.skip("game not installed at %s" % GAME_DIR)
    return GAME_DIR


@pytest.fixture(scope="session")
def reference_dir(game_dir):
    if not os.path.isfile(os.path.join(REFERENCE_DIR, "tools", "swfp", "patches",
                                       "camera.py")):
        pytest.skip("reference mod not installed at %s" % REFERENCE_DIR)
    return REFERENCE_DIR


@pytest.fixture(scope="session")
def vanilla_inc_files(game_dir):
    """Every `.inc` file under <game>\\data (313 on 2026-09-28)."""
    return _walk(DATA_DIR, lambda n: n.lower().endswith(".inc"))


def has_zero_byte(path):
    """A file is binary if and only if it holds a zero byte - the same rule
    tools/hbuild.py uses. Read in chunks and stop at the first zero, so the
    6.8 GB of textures and models cost one small read each."""
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1 << 16)
            if not chunk:
                return False
            if b"\x00" in chunk:
                return True


@pytest.fixture(scope="session")
def vanilla_text_files(game_dir):
    """Every vanilla text file under <game>\\data (4341 files, 65 MB on
    2026-09-28, the .aaf animation lists included)."""
    return [p for p in _walk(DATA_DIR, lambda n: True) if not has_zero_byte(p)]


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def vanilla_bytes(rel):
    """Bytes of `<game>\\data\\<rel>` (`rel` with forward slashes)."""
    return read_bytes(os.path.join(DATA_DIR, *rel.split("/")))
