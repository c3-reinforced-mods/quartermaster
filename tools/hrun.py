r"""Run the game once under test conditions, then put everything back.

    python tools/hrun.py --dry-run [options]         print the whole plan; touch nothing
    python tools/hrun.py --logs-dir DIR [options]    one run
    python tools/hrun.py --recover [--logs-dir DIR]  undo a run whose harness died

Options:
    --fixture NAME          also deploy <fixtures-dir>\NAME as mods\NAME (repeatable)
    --no-quartermaster      do not deploy dist\Quartermaster
    --case FILE             copy FILE verbatim into <save>\qm_test\cases\ (repeatable)
    --autotest-cfg FILE     bytes of <save>\qm_autotest.cfg (default: an empty switch file,
                            written whenever a case is given)
    --until TEXT            stop waiting once TEXT appears in a new log
                            (default: the boot marker when Quartermaster is deployed)
    --until-log N           ... in the N-th new log (1 = the first life); for a
                            marker every life prints, or a life without Quartermaster
    --state DIR             start the run with DIR as <save>\quartermaster (a copy;
                            default: no such folder, a first boot)
    --timeout S             stop waiting after S seconds (default 180)
    --boot-marker TEXT      what proves Quartermaster booted (default "[qm]")
    --expect-compile-error STATE
                            a "Compile script error: STATE" the run provokes on purpose
                            (a validation state), not a brick (repeatable)
    --follow-bricks         a brick line does not end the wait: the run follows the
                            game past it (the pre-compile guard restarts a life that
                            bricks) until TEXT, the timeout or the game's exit; the
                            summary still reports the brick lines
    --hold S                keep the game running S seconds after TEXT appeared (a
                            helper captures the screen meanwhile)
    --qm-folder NAME        deploy dist\Quartermaster as mods\NAME: Quartermaster
                            (default) or QMTest<name>, for a machine whose player
                            keeps an installation in mods\Quartermaster
    --enable NAME           compose mods.ini for the run (test runs only): NAME (a
                            Workshop id or a mods\ folder) on; repeatable, in load order;
                            every other registered or installed mod off
    --unlisted ID           compose, and leave Workshop item ID out of mods.ini: the
                            engine registers it at the start like a new subscription;
                            or a folder in mods\ (a deployed --fixture or one there
                            already), which the engine then registers like a folder
                            new in mods\ (after the others)
    --compose               compose even with no --enable (only the deployed folders on)
    --disable NAME          compose, and list the deployed --fixture NAME off: there,
                            but not loaded (a mod the player has and has not switched on)
    --first NAME            compose, and list the installed mod NAME (a Workshop id or a
                            mods\ folder, not enabled) off at the top of mods.ini:
                            repeatable, in that order; the manager's Installed list
                            follows mods.ini's order, so it shows NAME first
    --canonical             compose, every row in Quartermaster's canonical order
                            (ref/order.py; itself last) instead of the order above -
                            the start of a player whose mods.ini it has put in order
    --launch EXE            cossacks.exe (default) or modman.exe
    --keep-deployed         leave the deployed folders in mods\ (a manual checkpoint only)
    --run-id ID             default yyyymmdd-hhmmss
    --game-dir --save-dir --fixtures-dir --dist
                            override the default locations
    --logs-dir DIR          where run folders and the journal go (or QM_HRUN_LOGS);
                            required for a real run

What one run does, in order (`--dry-run` prints exactly this list, with the
real paths, and stops):

   1 preflight  refuse if cossacks.exe or modman.exe runs (tasklist), if the
                shared lock <save>\swfp_game.lock exists (SWFP sessions take it
                too), if a journal of an unfinished run exists, or if a folder
                to deploy already exists in mods\.
   2 lock       create the lock with O_CREAT|O_EXCL; it names this run.
   3 baseline   read now, never hard-coded: the exact bytes and sha256 of
                mods\mods.ini, the listing of mods\, a sha256 manifest of
                every vanilla file Quartermaster could ever write an override
                for (the hook files of plan S5 and the S3 merge allow-list),
                and the size and time of the mod.ini and every data\ file of
                the folders already in mods\ (SW_Frontline_Protocol today).
   4 backup     binary copy of mods.ini into the run folder, sha256 verified.
   5 journal    <logs-dir>\hrun.journal.json: the baseline, the backup, and every
                folder and file this run creates, each recorded before it is
                created, so `--recover` can undo a run killed at any point.
   6 deploy     copy dist\Quartermaster and each fixture into mods\. The game
                registers and enables every folder in mods\ when it starts, so
                hrun writes no mods.ini of its own - unless the run composes one
                (--enable, --unlisted, --compose): then,
                after the backup, mods.ini holds every installed Workshop item
                and mods\ folder off, the --enable ones on in the order given,
                the deployed folders on, Quartermaster last; a copy goes into
                the run folder as mods.ini.composed.
   7 state      move <save>\quartermaster aside (renamed, never deleted) so the
                run starts without Quartermaster's marker files - or with a copy
                of --state DIR; runs do not see each other's state.
   8 cases      copy each --case file into <save>\qm_test\cases\ and
                write <save>\qm_autotest.cfg, the switch that makes the
                SelfTest run (ref/selftest.py has the case format; the files
                go over verbatim). The SelfTest writes its results into
                <save>\qm_test\out\, which must not exist before the run.
   9 launch     <game>\cossacks.exe with the game folder as working directory.
                Started by hand it exits with code 53 and Steam starts a copy
                that is nobody's child, so the process is tracked by image name.
  10 wait       poll the new <save>\log\cos_*.log files until TEXT appears, a
                brick line appears, the timeout passes, or no game process has
                existed for a while. Quartermaster restarts the game itself
                (RestartApplicationParam): a new process writes a new log, and
                the wait spans every life of the process.
  11 kill       taskkill cossacks.exe (every copy), and modman.exe only when
                hrun started it.
  12 collect    copy every new log into the run folder, the SelfTest's
                <save>\qm_test\out\ into <run folder>\qm_test_out\, the run's
                <save>\quartermaster\ into <run folder>\qm_save\, the deployed
                mods\Quartermaster (with what it generated) into <run
                folder>\qm_mod\ and mods.ini as the game left it into <run
                folder>\mods.ini.during.
  13 undeploy   remove exactly the folders this run deployed; never one that
                was in mods\ before the run.
  14 restore    copy the backup over mods.ini (binary), verify the sha256;
                remove the run's <save>\quartermaster and rename the one moved
                aside back.
  15 cleanup    remove the case files, the SelfTest's out folder (after it was
                collected) and the folders this run created.
  16 sweep      mods\ listing and mods.ini sha256 equal the baseline, no game
                process left, the vanilla manifest unchanged, every folder that
                was in mods\ unchanged (size and time of its mod.ini and data\),
                <save>\quartermaster as before (file by file): SWEEP OK or SWEEP
                FAILED, also in the JSON summary.
  17 unlock     remove the journal once this run's own changes are undone, and
                the lock if it is still ours.

Brick detection: "Error compiling scripts", "CompileFramework", "Compile script
error" or "Parser load error" in a new log, or - when Quartermaster is
deployed - no boot-marker line before the wait ends, sets `brick_suspected`
with the lines that caused it.

Output: `<logs-dir>\<run-id>\summary.json`, the copied logs and the mods.ini
backup; the summary is printed as well. Exit status 0 when the run reached its
marker, no brick is suspected and the sweep is OK; 1 when the run happened but
one of those failed; 2 when it was refused.
"""
import argparse
import datetime
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field

import hbuild

REPO = hbuild.REPO
GAME = hbuild.GAME
DIST_MOD = hbuild.DIST_MOD
FIXTURES = os.path.join(REPO, "fixtures")
LOCK_NAME = hbuild.LOCK_NAME
LOCK_OWNER = "quartermaster-hrun"
JOURNAL_NAME = "hrun.journal.json"
LOGS_ENV = "QM_HRUN_LOGS"
AUTOTEST_CFG = "qm_autotest.cfg"
AUTOTEST_DIR = ("qm_test", "cases")
# Where the SelfTest writes; hrun collects it into the run folder and removes it.
SELFTEST_OUT = ("qm_test", "out")
SELFTEST_COPY = "qm_test_out"
# Quartermaster's own files in the save folder (marker, known mods, report,
# validation copies): moved aside for a run, so every run starts from a known
# state and the player's folder ends as it was.
STATE_DIR = "quartermaster"
STATE_ASIDE = "quartermaster.hrun-aside"
STATE_COPY = "qm_save"
# The deployed mods\Quartermaster as the run left it (its generated files).
QM_COPY = "qm_mod"
INI_DURING = "mods.ini.during"
# The mods.ini a composed run started with: the start a check compares the
# game's file with. The player's backup is not that start - hrun lists every
# installed Workshop item, and one the player's file lacks (a subscription
# the engine has not registered) sits among the others.
INI_COMPOSED = "mods.ini.composed"
GAME_IMAGES = hbuild.GAME_IMAGES

# The hook files of plan S5, relative to data/.
HOOK_FILES = tuple(h[len("data/"):] for h in hbuild.HOOK_FILES)

# What a broken start looks like in cos_*.log (the brick probes of plan S2):
# "Compile script error: DoCreate", "CompileFramework() - compile global script
# error: ...", "Parser load error: line 982". "Error compiling scripts" is the
# dialog the engine shows for a broken library.
BRICK_PATTERNS = (b"Error compiling scripts", b"CompileFramework",
                  b"Compile script error", b"Parser load error")
COMPILE_ERROR = b"Compile script error: "


class Refused(RuntimeError):
    """The run must not start (or recovery must not proceed)."""


# ------------------------------------------------------------ the outside
class System(object):
    """Processes and time: everything a test replaces with a fake."""

    def running(self):
        return hbuild.running_images()

    def launch(self, exe, cwd):
        subprocess.Popen([exe], cwd=cwd)

    def kill(self, image):
        subprocess.call(["taskkill", "/F", "/IM", image],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def sleep(self, seconds):
        time.sleep(seconds)

    def now(self):
        return time.time()


@dataclass
class Options:
    game_dir: str = GAME
    save_dir: str = None
    dist_mod: str = DIST_MOD
    fixtures_dir: str = FIXTURES
    logs_dir: str = None
    fixtures: list = field(default_factory=list)
    quartermaster: bool = True
    cases: list = field(default_factory=list)
    autotest_cfg: str = None
    until: str = None
    until_log: int = None
    state: str = None
    timeout: float = 180.0
    boot_marker: str = "[qm]"
    expect_compile_errors: list = field(default_factory=list)
    follow_bricks: bool = False
    hold: float = 0.0
    enable: list = field(default_factory=list)
    unlisted: list = field(default_factory=list)
    compose: bool = False
    canonical: bool = False
    disable: list = field(default_factory=list)
    first: list = field(default_factory=list)
    qm_folder: str = None
    launch: str = "cossacks.exe"
    keep_deployed: bool = False
    game_created: list = field(default_factory=list)
    run_id: str = None
    dry_run: bool = False
    poll: float = 2.0
    settle: float = 3.0
    startup_grace: float = 60.0
    exit_grace: float = 20.0

    def resolve(self):
        if self.save_dir is None:
            self.save_dir = hbuild.default_save_dir()
        if self.logs_dir is None:
            self.logs_dir = os.environ.get(LOGS_ENV) or None
        if self.qm_folder is None:
            self.qm_folder = hbuild.MOD_NAME
        if self.run_id is None:
            self.run_id = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        if self.until is None and self.quartermaster:
            self.until = self.boot_marker
        # Absolute from here on: the lock carries the journal's path, and
        # --recover may run from any working directory.
        for name in ("game_dir", "save_dir", "dist_mod", "fixtures_dir", "logs_dir",
                     "autotest_cfg", "state"):
            if getattr(self, name):
                setattr(self, name, os.path.abspath(getattr(self, name)))
        self.cases = [os.path.abspath(c) for c in self.cases]
        return self


# ------------------------------------------------------------- the files
def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def mods_ini(game):
    return os.path.join(game, "mods", "mods.ini")


# Community-mod runs (decided 2026-09-28): the harness may compose
# mods.ini for one run - the mods named with --enable on, in that order, every
# other registered or installed mod off, the --unlisted Workshop items left out
# so the engine registers them at the start as it does a new subscription - and
# restores the player's file afterwards like any other run.
WORKSHOP_REL = ("..", "..", "workshop", "content", "333420")
WORKSHOP_DIR = b"..\\..\\workshop\\content\\333420\\"


def workshop_root(game):
    return os.path.normpath(os.path.join(game, *WORKSHOP_REL))


def installed_workshop(game):
    """The Workshop ids Steam has downloaded, sorted."""
    root = workshop_root(game)
    if not os.path.isdir(root):
        return []
    return sorted(n for n in os.listdir(root) if os.path.isdir(os.path.join(root, n)))


def composing(opts):
    return bool(opts.enable or opts.unlisted or opts.compose or opts.canonical or opts.disable
                or opts.first)


def mod_dir(game, name):
    """The dir the engine writes for `name`: a Workshop id or a mods\\ folder."""
    if name.isdigit() and name in installed_workshop(game):
        return WORKSHOP_DIR + name.encode("ascii")
    return b"mods\\" + name.encode("ascii")


def composed_rows(opts, listing):
    """`[(dir, dis)]` of a composed mods.ini, in load order: every other mod
    off, then the enabled ones in the order given, then the deployed folders
    (Quartermaster last)."""
    from ref.order import FALSE, TRUE
    game = opts.game_dir
    deployed = [name for name, _src in _deploy_sources(opts)]
    local = [n[:-1] for n in listing if n.endswith("/")]
    on = [mod_dir(game, n) for n in opts.enable]
    rows = [(mod_dir(game, n), TRUE) for n in installed_workshop(game)
            if n not in opts.enable and n not in opts.unlisted]
    rows += [(mod_dir(game, n), TRUE) for n in local
             if n not in opts.enable and n not in deployed and n not in opts.unlisted]
    rows += [(d, FALSE) for d in on]
    qm = [n for n in deployed if n == opts.qm_folder]
    rows += [(mod_dir(game, n), TRUE if n in opts.disable else FALSE) for n in deployed
             if n not in opts.enable and n not in qm and n not in opts.unlisted]
    rows += [(mod_dir(game, n), FALSE) for n in qm]
    if opts.first:
        top = [mod_dir(game, n) for n in opts.first]
        rows = [r for d in top for r in rows if r[0] == d] + [r for r in rows if r[0] not in top]
    if opts.canonical:
        from ref.order import canonical_rows
        rows = canonical_rows(rows, mod_dir(game, qm[0]) if qm else None)
    return rows


def composed_ini(opts, listing):
    from ref.order import render_mods_ini
    return render_mods_ini(composed_rows(opts, listing))


def compose_problems(opts, listing):
    game = opts.game_dir
    have = set(installed_workshop(game))
    local = set(n[:-1] for n in listing if n.endswith("/"))
    deployed = set(name for name, _src in _deploy_sources(opts))
    out = []
    for n in opts.enable:
        if n not in have and n not in local and n not in deployed:
            out.append("--enable %s: no Workshop item or mods\\ folder of that name" % n)
    for n in opts.unlisted:
        if n == opts.qm_folder or (n not in have and n not in deployed and n not in local):
            out.append("--unlisted %s: not an installed Workshop item or a folder in mods\\"
                       % n)
        if n in opts.enable:
            out.append("--unlisted %s is also enabled" % n)
    for n in opts.disable:
        if n not in deployed or n == opts.qm_folder:
            out.append("--disable %s: not a deployed fixture" % n)
        if n in opts.enable or n in opts.unlisted:
            out.append("--disable %s is also enabled or unlisted" % n)
    for n in opts.first:
        if n not in have and n not in local:
            out.append("--first %s: not an installed Workshop item or a folder in mods\\" % n)
        if n in opts.enable or n in opts.unlisted or n in deployed:
            out.append("--first %s is also enabled, unlisted or deployed" % n)
    if len(set(opts.enable)) != len(opts.enable):
        out.append("--enable names a mod twice")
    if len(set(opts.first)) != len(opts.first):
        out.append("--first names a mod twice")
    return out


def mods_listing(game):
    """`mods\\` as sorted names, folders with a trailing `/`."""
    root = os.path.join(game, "mods")
    return sorted(n + "/" if os.path.isdir(os.path.join(root, n)) else n
                  for n in os.listdir(root))


def touchable_files(game):
    """Vanilla files Quartermaster could write an override for, relative to data/.

    The S3 merge allow-list (hbuild.classify == "merge") plus the S5 hook files
    - which are on the allow-list already; naming them keeps the manifest right
    if the allow-list ever narrows.
    """
    data = os.path.join(game, "data")
    out = set(h for h in HOOK_FILES if os.path.isfile(os.path.join(data, *h.split("/"))))
    for sub in hbuild.MERGE_DIRS:
        top = os.path.join(data, *sub.strip("/").split("/"))
        for root, _dirs, files in os.walk(top):
            for fn in files:
                rel = os.path.relpath(os.path.join(root, fn), data).replace(os.sep, "/").lower()
                if rel.endswith(".inc") and hbuild.classify(rel, False) == "merge":
                    out.add(rel)
    return sorted(out)


def vanilla_manifest(game):
    data = os.path.join(game, "data")
    return {rel: _sha256(os.path.join(data, *rel.split("/"))) for rel in touchable_files(game)}


def stat_manifest(root):
    """`{relative path: [size, mtime_ns]}` of every file under `root`, or None
    when it is not a folder. Stat only: the installed mods are hundreds of MB,
    and a run that wrote into one changes a size or a time."""
    if not os.path.isdir(root):
        return None
    out = {}
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            st = os.stat(os.path.join(dirpath, f))
            out[os.path.relpath(os.path.join(dirpath, f), root).replace(os.sep, "/")] = [
                st.st_size, st.st_mtime_ns]
    return out


#: What the engine reads from a mod folder, so all a run could change in one
#: by mistake: its mod.ini and its data tree. A mod folder can also be a
#: working copy with its own tooling (SW_Frontline_Protocol has .git, tools,
#: docs), which another session may edit while a run waits; that is not the
#: run's doing and is left out.
MOD_TREE_PARTS = ("mod.ini", "data")


def mod_tree(folder):
    """`{relative path: [size, mtime_ns]}` of a mod folder's MOD_TREE_PARTS."""
    out = {}
    ini = os.path.join(folder, "mod.ini")
    if os.path.isfile(ini):
        st = os.stat(ini)
        out["mod.ini"] = [st.st_size, st.st_mtime_ns]
    for rel, v in (stat_manifest(os.path.join(folder, "data")) or {}).items():
        out["data/" + rel] = v
    return out


def mods_trees(game):
    """`{folder: mod_tree}` of every folder in mods\\ now: the mods that were
    there before a run (SW_Frontline_Protocol today), which no run may touch."""
    root = os.path.join(game, "mods")
    return dict((n.rstrip("/"), mod_tree(os.path.join(root, n.rstrip("/"))))
                for n in mods_listing(game) if n.endswith("/"))


def capture_baseline(game):
    ini = mods_ini(game)
    return {"mods_ini_sha256": _sha256(ini), "mods_ini_size": os.path.getsize(ini),
            "mods_listing": mods_listing(game), "vanilla_manifest": vanilla_manifest(game),
            "mods_trees": mods_trees(game)}


def tree_changes(before, now):
    """The relative paths that differ between two stat manifests, sorted."""
    before, now = before or {}, now or {}
    return sorted(p for p in set(before) | set(now) if before.get(p) != now.get(p))


def log_dir(save):
    return os.path.join(save, "log")


def game_logs(save):
    return sorted(glob.glob(os.path.join(log_dir(save), "cos_*.log")))


def state_dir(save):
    return os.path.join(save, STATE_DIR)


def state_aside(save):
    return os.path.join(save, STATE_ASIDE)


def tree_manifest(root):
    """`{relative path: sha256, or "dir" for a folder}` of `root`, or None when
    it does not exist."""
    if not os.path.isdir(root):
        return None
    out = {}
    for dirpath, dirs, files in os.walk(root):
        for d in dirs:
            out[os.path.relpath(os.path.join(dirpath, d), root).replace(os.sep, "/") + "/"] = "dir"
        for f in files:
            full = os.path.join(dirpath, f)
            out[os.path.relpath(full, root).replace(os.sep, "/")] = _sha256(full)
    return out


# -------------------------------------------------------------- the lock
def lock_path(save):
    return os.path.join(save, LOCK_NAME)


def read_lock(path):
    """The lock's content when hrun wrote it, else None (absent or foreign)."""
    try:
        with open(path, "rb") as fh:
            data = json.loads(fh.read().decode("utf-8"))
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) and data.get("owner") == LOCK_OWNER else None


def take_lock(path, token, journal):
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0))
    try:
        os.write(fd, json.dumps({"owner": LOCK_OWNER, "token": token, "journal": journal,
                                 "pid": os.getpid()}).encode("utf-8"))
    finally:
        os.close(fd)


def release_lock(path, token):
    """Remove the lock only if it is still ours; say whether it was."""
    held = read_lock(path)
    if held is None or held.get("token") != token:
        return False
    os.remove(path)
    return True


# ------------------------------------------------------------ the journal
class Journal(object):
    def __init__(self, path, data):
        self.path = path
        self.data = data

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, indent=1, sort_keys=True)
        os.replace(tmp, self.path)

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as fh:
            return cls(path, json.load(fh))

    def __getitem__(self, key):
        return self.data[key]


# ------------------------------------------------------------------ plan
def _deploy_sources(opts):
    out = []
    if opts.quartermaster:
        out.append((opts.qm_folder, opts.dist_mod))
    for name in opts.fixtures:
        out.append((name, os.path.join(opts.fixtures_dir, name)))
    return out


def _case_targets(opts):
    """`[(source or None, target)]` for the case files and the switch file."""
    if not opts.cases and opts.autotest_cfg is None:
        return []
    folder = os.path.join(opts.save_dir, *AUTOTEST_DIR)
    out = [(c, os.path.join(folder, os.path.basename(c))) for c in opts.cases]
    out.append((opts.autotest_cfg, os.path.join(opts.save_dir, AUTOTEST_CFG)))
    return out


def selftest_out(save):
    return os.path.join(save, *SELFTEST_OUT)


def _new_case_dirs(opts):
    """The folders on the way to the case files that do not exist yet."""
    out, folder = [], opts.save_dir
    for part in AUTOTEST_DIR:
        folder = os.path.join(folder, part)
        if not os.path.isdir(folder):
            out.append(folder)
    return out


def preflight(opts, system):
    """Every reason not to start, as a list of sentences. Reads only."""
    problems = []
    game = opts.game_dir
    if not os.path.isfile(mods_ini(game)):
        return ["%s has no mods\\mods.ini - not a game folder" % game]
    # Decided 2026-09-28: the harness copies Quartermaster, QmProbe or QMTest*
    # into mods\ - Quartermaster may go in as a QMTest* folder when the
    # player's own installation holds mods\Quartermaster.
    if not re.match(r"^(Quartermaster|QMTest[A-Za-z0-9]+)$", opts.qm_folder or ""):
        problems.append("--qm-folder must be Quartermaster or QMTest<name>, not %r"
                        % opts.qm_folder)
    exe = os.path.join(game, opts.launch)
    if opts.launch not in GAME_IMAGES:
        problems.append("--launch must be one of %s" % ", ".join(GAME_IMAGES))
    elif not os.path.isfile(exe):
        problems.append("%s does not exist" % exe)
    try:
        running = sorted(set(GAME_IMAGES) & system.running())
    except hbuild.BuildError as exc:
        running = ["unknown (%s)" % exc]
    if running:
        problems.append("running: %s" % ", ".join(running))
    if not os.path.isdir(opts.save_dir):
        problems.append("the save folder %s does not exist" % opts.save_dir)
    lock = lock_path(opts.save_dir)
    if os.path.lexists(lock):
        problems.append("the lock %s exists (another session, or a crashed run: "
                        "--recover)" % lock)
    if not opts.dry_run and not opts.logs_dir:
        problems.append("no --logs-dir (or %s) for the run folder and the journal" % LOGS_ENV)
    if opts.logs_dir:
        journal = os.path.join(opts.logs_dir, JOURNAL_NAME)
        if os.path.exists(journal):
            problems.append("an unfinished run's journal %s exists - run --recover" % journal)
        if os.path.exists(os.path.join(opts.logs_dir, opts.run_id)):
            problems.append("the run folder %s exists already"
                            % os.path.join(opts.logs_dir, opts.run_id))
    listing = set(n.rstrip("/").lower() for n in mods_listing(game))
    names = set()
    for name, src in _deploy_sources(opts):
        try:
            hbuild.mod_folder(game, name)
        except hbuild.DeployError as exc:
            problems.append(str(exc))
            continue
        if name.lower() in names:
            problems.append("%s is deployed twice" % name)
        names.add(name.lower())
        if not os.path.isfile(os.path.join(src, "mod.ini")) and name == opts.qm_folder:
            problems.append("%s has no mod.ini - build first" % src)
        if not os.path.isdir(src):
            problems.append("%s does not exist" % src)
        if name.lower() in listing:
            problems.append("mods\\%s exists already; hrun never overwrites or removes "
                            "a folder it did not create" % name)
    for src, dst in _case_targets(opts):
        if src is not None and not os.path.isfile(src):
            problems.append("case file %s does not exist" % src)
        if os.path.lexists(dst):
            problems.append("%s exists already; hrun only removes what it created" % dst)
    aside = state_aside(opts.save_dir)
    if os.path.lexists(aside):
        problems.append("%s exists: the saved state of a run that did not finish - run "
                        "--recover" % aside)
    if hbuild.is_link(state_dir(opts.save_dir)):
        problems.append("%s is a link; hrun only moves a plain folder aside"
                        % state_dir(opts.save_dir))
    if opts.state and not os.path.isdir(opts.state):
        problems.append("--state %s is not a folder" % opts.state)
    # A folder the game itself makes during the run (Quartermaster's Create
    # mod, M11): only a test name, and not one that is there already.
    for name in opts.game_created:
        if not re.fullmatch(r"QMTest[A-Za-z0-9]+", name):
            problems.append("--game-created %s: only QMTest<letters and digits> folders" % name)
        if name.lower() in listing:
            problems.append("--game-created %s: mods\\%s exists already" % (name, name))
    if opts.until_log is not None and opts.until_log < 1:
        problems.append("--until-log counts lives from 1")
    if composing(opts):
        problems += compose_problems(opts, mods_listing(game))
    out_dir = selftest_out(opts.save_dir)
    if _case_targets(opts) and os.path.lexists(out_dir):
        problems.append("%s exists already (results of an earlier SelfTest?); move it "
                        "away - this run's results would mix with them" % out_dir)
    return problems


def plan_lines(opts, baseline):
    game, save = opts.game_dir, opts.save_dir
    logs = opts.logs_dir or "<--logs-dir required>"
    run_dir = os.path.join(logs, opts.run_id)
    m = baseline
    out = [
        ("preflight", "no cossacks.exe / modman.exe (tasklist); no %s; no journal in %s"
         % (lock_path(save), logs)),
        ("lock", "create %s exclusively (O_CREAT|O_EXCL)" % lock_path(save)),
        ("baseline", "mods.ini %d bytes sha256 %s; mods\\ = %s; %d vanilla files hashed "
         "(S5 hooks + S3 allow-list); size and time of mod.ini and data\\ of %s"
         % (m["mods_ini_size"], m["mods_ini_sha256"], ", ".join(m["mods_listing"]),
            len(m["vanilla_manifest"]),
            ", ".join("mods\\%s (%d)" % (n, len(t or {}))
                      for n, t in sorted(m.get("mods_trees", {}).items())) or "no folder")),
        ("backup", "copy %s -> %s (binary), verify sha256"
         % (mods_ini(game), os.path.join(run_dir, "mods.ini.backup"))),
        ("journal", os.path.join(logs, JOURNAL_NAME)),
    ]
    if composing(opts):
        rows = composed_rows(opts, m["mods_listing"])
        on = [d.decode("ascii") for d, dis in rows if dis == b"False"]
        out.append(("compose", "write mods.ini (test run): on, in load order = %s; "
                    "%d other mods off; unlisted = %s"
                    % (", ".join(on), len(rows) - len(on), ", ".join(opts.unlisted) or "none")))
    sources = _deploy_sources(opts)
    out.append(("deploy", "; ".join("copy %s -> %s" % (src, hbuild.mod_folder(game, name))
                                    for name, src in sources) or "nothing"))
    out.append(("state", "%s%s" % (
        ("rename %s -> %s" % (state_dir(save), state_aside(save))
         if os.path.lexists(state_dir(save)) else "no %s" % state_dir(save)),
        "; copy %s -> %s" % (opts.state, state_dir(save)) if opts.state else
        " (the run starts without it)")))
    cases = _case_targets(opts)
    new_dirs = _new_case_dirs(opts) if cases else []
    out.append(("cases", "; ".join(["create %s" % d for d in new_dirs]
                                   + ["%s %s" % ("copy %s ->" % src if src else "write empty",
                                                 dst) for src, dst in cases]) or "none"))
    out.append(("launch", "%s (cwd %s); Steam may replace the process - tracked by image "
                "name" % (os.path.join(game, opts.launch), game)))
    out.append(("wait", "until %s in %s %s, following game restarts; timeout %ds; a "
                "brick line ends the wait"
                % (repr(opts.until) if opts.until else "the timeout",
                   "new log number %d of" % opts.until_log if opts.until_log else "a new",
                   os.path.join(log_dir(save), "cos_*.log"), opts.timeout)))
    out.append(("kill", "taskkill cossacks.exe%s" % (" and modman.exe"
                                                     if opts.launch == "modman.exe" else "")))
    out.append(("collect", "copy every new log -> %s%s%s"
                % (run_dir, "; copy %s -> %s" % (selftest_out(save),
                                                 os.path.join(run_dir, SELFTEST_COPY))
                   if cases else "",
                   "; copy %s -> %s" % (hbuild.mod_folder(game, opts.qm_folder),
                                        os.path.join(run_dir, QM_COPY))
                   if opts.quartermaster else "")))
    out.append(("undeploy", "keep %s (--keep-deployed)" % ", ".join(n for n, _ in sources)
                if opts.keep_deployed else
                "; ".join("remove %s" % hbuild.mod_folder(game, n) for n, _ in sources)
                or "nothing"))
    out.append(("restore", "copy %s -> %s; copy the backup over it (binary), verify sha256 "
                "== %s; copy %s -> %s, remove it%s"
                % (mods_ini(game), os.path.join(run_dir, INI_DURING), m["mods_ini_sha256"],
                   state_dir(save), os.path.join(run_dir, STATE_COPY),
                   ", rename %s back" % state_aside(save) if os.path.lexists(state_dir(save))
                   else "")))
    out.append(("cleanup", "; ".join(["remove %s" % dst for _src, dst in cases]
                                     + (["remove %s (collected first)" % selftest_out(save)]
                                        if cases else [])
                                     + ["remove %s if still empty" % d
                                        for d in reversed(new_dirs)]) or "nothing"))
    out.append(("sweep", "mods\\ listing == baseline%s, mods.ini sha256 == baseline, no game "
                "process, %d vanilla files unchanged, the folders of mods\\ unchanged, %s "
                "file by file as before the run"
                % (" + kept folders" if opts.keep_deployed else "",
                   len(m["vanilla_manifest"]), state_dir(save))))
    out.append(("unlock", "remove the journal and our lock; write %s"
                % os.path.join(run_dir, "summary.json")))
    return out


# ------------------------------------------------------------------ logs
def scan_logs(paths, opts):
    """What the new logs say: marker, boot line, brick lines, `[qm]` lines."""
    until = opts.until.encode("ascii") if opts.until else None
    marker = opts.boot_marker.encode("ascii")
    expected = set(s.lower().encode("ascii") for s in opts.expect_compile_errors)
    found = {"until": False, "boot": False, "brick": [], "qm": []}
    for number, path in enumerate(paths, 1):
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            continue
        name = os.path.basename(path)
        for raw in data.split(b"\n"):
            line = raw.rstrip(b"\r")
            if until and until in line and opts.until_log in (None, number):
                found["until"] = True
            if marker in line:
                found["boot"] = True
                found["qm"].append((name, line.decode("latin-1")))
            # Quartermaster's own lines quote the game's error in its words
            # (the report's global-script lines); only the engine's lines count.
            if any(p in line for p in BRICK_PATTERNS) and b"[qm" not in line:
                at = line.find(COMPILE_ERROR)
                if at >= 0 and line[at + len(COMPILE_ERROR):].strip().lower() in expected:
                    continue
                found["brick"].append((name, line.decode("latin-1")))
    return found


def wait_for_game(opts, system, before, t0, out):
    """Poll until the marker, a brick line, the timeout or the game's exit."""
    state = "timeout"
    gone_since = None
    seen = {}
    found = scan_logs([], opts)
    while system.now() - t0 < opts.timeout:
        system.sleep(opts.poll)
        new = [p for p in game_logs(opts.save_dir) if p not in before]
        found = scan_logs(new, opts)
        for key in found["qm"]:
            seen.setdefault(key, round(system.now() - t0, 1))
        if found["brick"] and not opts.follow_bricks:
            state = "brick"
            system.sleep(opts.settle)
            break
        if found["until"]:
            state = "reached"
            system.sleep(opts.settle)
            break
        alive = set(GAME_IMAGES) & system.running()
        if alive:
            gone_since = None
        elif system.now() - t0 > opts.startup_grace:
            gone_since = gone_since if gone_since is not None else system.now()
            if system.now() - gone_since >= opts.exit_grace:
                state = "game exited"
                break
    new = [p for p in game_logs(opts.save_dir) if p not in before]
    found = scan_logs(new, opts)
    elapsed = round(system.now() - t0, 1)
    out("wait: %s after %.0f s, %d new log(s)" % (state, elapsed, len(new)))
    return {"state": state, "elapsed_s": elapsed, "found": found,
            "qm_first_seen": [{"log": k[0], "s": v, "line": k[1]}
                              for k, v in sorted(seen.items(), key=lambda kv: kv[1])][:200]}


# ------------------------------------------------------------ undo steps
def move_state_aside(opts, journal, out):
    r"""Step 7: <save>\quartermaster renamed aside (never deleted), then the
    --state seed copied in. The journal records each step before it happens."""
    st = {"dir": state_dir(opts.save_dir), "aside": state_aside(opts.save_dir),
          "original": None, "seed": opts.state, "before": tree_manifest(state_dir(opts.save_dir))}
    journal.data["state"] = st
    journal.save()
    if os.path.lexists(st["dir"]):
        os.rename(st["dir"], st["aside"])
        st["original"] = "moved"
        out("state: %s -> %s" % (st["dir"], st["aside"]))
    else:
        st["original"] = "absent"
    journal.save()
    if opts.state:
        shutil.copytree(opts.state, st["dir"])
        out("state: seeded %s from %s" % (st["dir"], opts.state))


def restore_state(journal, out):
    r"""Collect the run's <save>\quartermaster into the run folder, remove it
    and rename the original back. True when the folder is as before."""
    st = journal.data.get("state")
    if not st:
        return True
    d, aside = st["dir"], st["aside"]
    moved = os.path.isdir(aside) and not hbuild.is_link(aside)
    if not moved:
        if st.get("original") == "moved":
            out("state: FAILED - %s was moved aside but is gone" % aside)
            return False
        if st.get("original") != "absent":
            return True             # nothing was moved: the original never left
    run_dir = journal["run_dir"]
    if os.path.isdir(d) and os.path.isdir(run_dir):
        dst = os.path.join(run_dir, STATE_COPY)
        if not os.path.exists(dst):
            shutil.copytree(d, dst)
            out("collect: %s -> %s" % (d, dst))
    if os.path.lexists(d):
        if hbuild.is_link(d) or not os.path.isdir(d):
            out("state: REFUSED to remove %s - not a plain folder" % d)
            return False
        shutil.rmtree(d)
    if moved:
        os.rename(aside, d)
    ok = tree_manifest(d) == st["before"]
    out("state: %s %s" % (d, "as before the run" if ok else "DIFFERS from before the run"))
    return ok


def _listed_before(journal, name):
    return name.lower() in set(n.rstrip("/").lower() for n in journal["baseline"]["mods_listing"])


def remove_deployed(journal, name, out):
    """Remove mods\\<name> if this run created it. Returns True when it is gone."""
    game = journal["game_dir"]
    path = hbuild.mod_folder(game, name)
    if _listed_before(journal, name):
        out("undeploy: REFUSED %s - it was in mods\\ before the run" % path)
        return False
    if not os.path.lexists(path):
        return True
    if hbuild.is_link(path) or not os.path.isdir(path):
        out("undeploy: REFUSED %s - not a plain folder" % path)
        return False
    shutil.rmtree(path)
    out("undeploy: removed %s" % path)
    return not os.path.lexists(path)


def remove_game_created(journal, name, out):
    """A folder the game made in mods\\ during the run (--game-created): copied
    into the run folder as evidence, then removed like a deployed one."""
    path = hbuild.mod_folder(journal["game_dir"], name)
    if os.path.isdir(path) and not hbuild.is_link(path) and not _listed_before(journal, name):
        dst = os.path.join(journal["run_dir"], "created", name)
        if not os.path.exists(dst):
            shutil.copytree(path, dst)
            out("collect: %s -> %s" % (path, dst))
    return remove_deployed(journal, name, out)


def restore_mods_ini(journal, out):
    ini = mods_ini(journal["game_dir"])
    backup = journal["backup"]
    if not os.path.isfile(backup):
        out("restore: FAILED - the backup %s is missing" % backup)
        return False
    if _sha256(backup) != journal["baseline"]["mods_ini_sha256"]:
        out("restore: FAILED - the backup %s does not match the baseline sha256" % backup)
        return False
    shutil.copyfile(backup, ini)
    ok = _sha256(ini) == journal["baseline"]["mods_ini_sha256"]
    out("restore: mods.ini %s" % ("byte-identical to the baseline" if ok else "DIFFERS"))
    return ok


def collect_selftest(journal, out):
    """Copy the SelfTest's out folder into the run folder; the files copied."""
    copied = []
    for path in journal.data.get("game_output_dirs", []):
        if not os.path.isdir(path) or not os.path.isdir(journal["run_dir"]):
            continue
        dst = os.path.join(journal["run_dir"], SELFTEST_COPY)
        if os.path.exists(dst):
            continue
        shutil.copytree(path, dst)
        for dirpath, _dirs, names in os.walk(dst):
            for n in sorted(names):
                copied.append(os.path.join(dirpath, n))
        out("collect: %s -> %s (%d file(s))" % (path, dst, len(copied)))
    return copied


def collect_quartermaster(journal, out):
    """Copy the deployed Quartermaster folder, as the game left it, into the run
    folder: the files Quartermaster generated in it (merged outputs, hook files,
    manifest) are what a check compares with ref/. Reads the game folder only.
    Returns the copy's path, or None."""
    folder = journal.data.get("qm_folder", hbuild.MOD_NAME)
    if folder not in journal.data.get("deployed", []):
        return None
    src = hbuild.mod_folder(journal["game_dir"], folder)
    dst = os.path.join(journal["run_dir"], QM_COPY)
    if (not os.path.isdir(src) or hbuild.is_link(src) or not os.path.isdir(journal["run_dir"])
            or os.path.exists(dst)):
        return None
    shutil.copytree(src, dst)
    out("collect: %s -> %s" % (src, dst))
    return dst


def remove_created(journal, out):
    ok = True
    for path in reversed(journal["created_files"]):
        if os.path.lexists(path):
            os.remove(path)
            out("cleanup: removed %s" % path)
        ok = ok and not os.path.lexists(path)
    # The game wrote these during the run; preflight made sure none existed
    # before it, so the whole folder is this run's doing.
    for path in journal.data.get("game_output_dirs", []):
        if os.path.isdir(path) and not hbuild.is_link(path):
            shutil.rmtree(path)
            out("cleanup: removed %s" % path)
        ok = ok and not os.path.lexists(path)
    for path in reversed(journal["created_dirs"]):
        if os.path.isdir(path) and not os.listdir(path):
            os.rmdir(path)
            out("cleanup: removed %s" % path)
        elif os.path.isdir(path):
            out("cleanup: kept %s - the game wrote into it" % path)
    return ok


def sweep(journal, system, kept=()):
    """`(ok, problems)` against the journal's baseline."""
    game = journal["game_dir"]
    base = journal["baseline"]
    problems = []
    expected = sorted(set(base["mods_listing"]) | set(k + "/" for k in kept))
    now = mods_listing(game)
    for name in sorted(set(now) - set(expected)):
        problems.append("mods\\%s is new" % name)
    for name in sorted(set(expected) - set(now)):
        problems.append("mods\\%s is gone" % name)
    if _sha256(mods_ini(game)) != base["mods_ini_sha256"]:
        problems.append("mods.ini sha256 differs from the baseline")
    try:
        running = sorted(set(GAME_IMAGES) & system.running())
    except hbuild.BuildError as exc:
        running = ["unknown (%s)" % exc]
    if running:
        problems.append("still running: %s" % ", ".join(running))
    manifest = vanilla_manifest(game)
    for rel in sorted(set(base["vanilla_manifest"]) | set(manifest)):
        if base["vanilla_manifest"].get(rel) != manifest.get(rel):
            problems.append("vanilla data\\%s changed" % rel.replace("/", "\\"))
    # The mods that were there before the run (a journal from before this
    # check has none to compare).
    for name, tree in sorted((base.get("mods_trees") or {}).items()):
        changed = tree_changes(tree, mod_tree(os.path.join(game, "mods", name)))
        if changed:
            problems.append("mods\\%s changed: %d file(s), first %s"
                            % (name, len(changed), changed[0].replace("/", "\\")))
    st = journal.data.get("state")
    if st and tree_manifest(st["dir"]) != st["before"]:
        problems.append("%s differs from before the run" % st["dir"])
    if st and os.path.lexists(st["aside"]):
        problems.append("%s is still there" % st["aside"])
    return not problems, problems


def _kill_game(journal, system, out):
    images = ["cossacks.exe"] + (["modman.exe"] if journal["launched"] == "modman.exe" else [])
    for image in images:
        system.kill(image)
    for _ in range(10):
        if not (set(images) & system.running()):
            break
        system.sleep(1)
    out("kill: %s" % ", ".join(images))


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, sort_keys=True)


def finish(journal, system, opts, waited, error, out):
    """Undo everything the run did, sweep, summarise. Runs whatever happened before."""
    run_dir = journal["run_dir"]
    if journal["launched"]:
        _kill_game(journal, system, out)
    before = set(journal["logs_before"])
    copied = []
    for n, path in enumerate(p for p in game_logs(journal["save_dir"]) if p not in before):
        dst = os.path.join(run_dir, "%d.%s" % (n, os.path.basename(path)))
        shutil.copyfile(path, dst)
        copied.append(dst)
    selftest_files = collect_selftest(journal, out)
    qm_copy = collect_quartermaster(journal, out)
    ini_during = None
    if os.path.isdir(run_dir) and os.path.isfile(mods_ini(journal["game_dir"])):
        ini_during = os.path.join(run_dir, INI_DURING)
        shutil.copyfile(mods_ini(journal["game_dir"]), ini_during)
    own_ok = restore_state(journal, out)
    kept = []
    if opts.keep_deployed and error is None:
        kept = list(journal["deployed"])
    else:
        for name in reversed(journal["deployed"]):
            own_ok = remove_deployed(journal, name, out) and own_ok
    for name in journal.data.get("game_created", []):
        own_ok = remove_game_created(journal, name, out) and own_ok
    own_ok = restore_mods_ini(journal, out) and own_ok
    own_ok = remove_created(journal, out) and own_ok
    ok, problems = sweep(journal, system, kept)
    out("SWEEP OK" if ok else "SWEEP FAILED")
    for p in problems:
        out("  " + p)

    found = (waited or {}).get("found") or {"boot": False, "brick": [], "qm": [], "until": False}
    brick_reasons = [line for _log, line in found["brick"]]
    if journal["quartermaster"] and waited and not found["boot"]:
        brick_reasons.append("no %r line before the wait ended" % opts.boot_marker)
    summary = {
        "run_id": journal["run_id"],
        "state": (waited or {}).get("state", "not started"),
        "error": error,
        "elapsed_s": (waited or {}).get("elapsed_s"),
        "until": opts.until,
        "until_log": opts.until_log,
        "logs": copied,
        "restarts": max(0, len(copied) - 1),
        "boot_seen": found["boot"],
        "qm_first_seen": (waited or {}).get("qm_first_seen", []),
        "brick_suspected": bool(brick_reasons) if waited else False,
        "brick_lines": brick_reasons,
        "deployed": journal["deployed"],
        "dist": opts.dist_mod if opts.quartermaster else None,
        "fixtures_dir": opts.fixtures_dir if opts.fixtures else None,
        "kept_deployed": kept,
        "case_files": journal["created_files"],
        "mods_ini_during": ini_during,
        "state_seed": (journal.data.get("state") or {}).get("seed"),
        "state_copy": os.path.join(run_dir, STATE_COPY)
        if os.path.isdir(os.path.join(run_dir, STATE_COPY)) else None,
        "selftest_out": selftest_files,
        "quartermaster_copy": qm_copy,
        "sweep": {"ok": ok, "problems": problems,
                  "mods_listing": mods_listing(journal["game_dir"]),
                  "mods_ini_sha256": _sha256(mods_ini(journal["game_dir"])),
                  "vanilla_files_checked": len(journal["baseline"]["vanilla_manifest"]),
                  "mods_trees_checked": dict(
                      (n, len(t or {}))
                      for n, t in (journal["baseline"].get("mods_trees") or {}).items())},
    }
    if kept:
        game = journal["game_dir"]
        out("KEPT DEPLOYED (manual checkpoint): these folders were added and are still there:")
        for name in kept:
            out("  %s" % hbuild.mod_folder(game, name))
        out("To remove them: close the game, then")
        for name in kept:
            if name == hbuild.MOD_NAME:
                out("  python tools/hbuild.py --undeploy")
            else:
                out('  rmdir /S /Q "%s"' % hbuild.mod_folder(game, name))
        out("mods.ini was restored to its baseline (backup: %s); the game registers the "
            "kept folders again on its next start." % journal["backup"])
    if own_ok:
        os.remove(journal.path)
        summary["journal"] = "removed"
    else:
        summary["journal"] = "kept: %s - fix the step that failed, then --recover" % journal.path
        out("journal kept: %s" % journal.path)
    summary["lock_released"] = release_lock(journal["lock"], journal["token"])
    _write_json(os.path.join(run_dir, "summary.json"), summary)
    out(json.dumps(summary, indent=1, sort_keys=True))
    return summary


# --------------------------------------------------------------------- run
def _check_ascii(text, what):
    if text is not None:
        try:
            text.encode("ascii")
        except UnicodeEncodeError:
            raise Refused("%s must be ASCII (the log is in the game's code page)" % what)


def run(opts, system=None, out=print):
    """One run. Returns `(exit status, summary or None)`."""
    system = system or System()
    opts.resolve()
    _check_ascii(opts.until, "--until")
    _check_ascii(opts.boot_marker, "--boot-marker")
    problems = preflight(opts, system)
    if opts.dry_run:
        out("hrun plan (dry run: nothing is written, launched or killed)")
        out("  run id : %s" % opts.run_id)
        out("  game   : %s" % opts.game_dir)
        out("  save   : %s" % opts.save_dir)
        if problems and not os.path.isfile(mods_ini(opts.game_dir)):
            out("would refuse: " + problems[0])
            return 2, None
        for n, (step, text) in enumerate(plan_lines(opts, capture_baseline(opts.game_dir)), 1):
            out("  %2d %-9s %s" % (n, step, text))
        for p in problems:
            out("would refuse: " + p)
        return (2 if problems else 0), None
    if problems:
        for p in problems:
            out("hrun: refusing - " + p)
        return 2, None

    game, save = opts.game_dir, opts.save_dir
    os.makedirs(opts.logs_dir, exist_ok=True)
    journal_path = os.path.join(opts.logs_dir, JOURNAL_NAME)
    token = "%s:%d:%s" % (opts.run_id, os.getpid(), os.urandom(4).hex())
    lock = lock_path(save)
    try:
        take_lock(lock, token, journal_path)
    except FileExistsError:
        out("hrun: refusing - the lock %s appeared" % lock)
        return 2, None
    journal = None
    waited = None
    error = None
    try:
        baseline = capture_baseline(game)
        run_dir = os.path.join(opts.logs_dir, opts.run_id)
        os.makedirs(run_dir)
        backup = os.path.join(run_dir, "mods.ini.backup")
        shutil.copyfile(mods_ini(game), backup)
        if _sha256(backup) != baseline["mods_ini_sha256"]:
            raise RuntimeError("the mods.ini backup does not match what was read")
        journal = Journal(journal_path, {
            "run_id": opts.run_id, "token": token, "lock": lock, "game_dir": game,
            "save_dir": save, "run_dir": run_dir, "backup": backup, "baseline": baseline,
            "quartermaster": opts.quartermaster, "qm_folder": opts.qm_folder, "deployed": [],
            "game_created": list(opts.game_created), "created_files": [],
            "created_dirs": [], "launched": None, "logs_before": game_logs(save)})
        journal.save()
        out("baseline: mods.ini sha256 %s, mods\\ = %s, %d vanilla files; backup %s"
            % (baseline["mods_ini_sha256"], ", ".join(baseline["mods_listing"]),
               len(baseline["vanilla_manifest"]), backup))
        if composing(opts):
            data = composed_ini(opts, baseline["mods_listing"])
            journal.data["composed"] = hashlib.sha256(data).hexdigest()
            journal.save()
            with open(os.path.join(run_dir, INI_COMPOSED), "wb") as fh:
                fh.write(data)
            with open(mods_ini(game), "wb") as fh:
                fh.write(data)
            out("compose: mods.ini written, %d bytes; on = %s" % (
                len(data), ", ".join(d.decode("ascii") for d, dis
                                     in composed_rows(opts, baseline["mods_listing"])
                                     if dis == b"False")))
        for name, src in _deploy_sources(opts):
            target = hbuild.mod_folder(game, name)
            journal.data["deployed"].append(name)
            journal.save()
            shutil.copytree(src, target)
            out("deploy: %s -> %s" % (src, target))
        move_state_aside(opts, journal, out)
        cases = _case_targets(opts)
        if cases:
            journal.data["game_output_dirs"] = [selftest_out(save)]
            journal.save()
            for folder in _new_case_dirs(opts):
                journal.data["created_dirs"].append(folder)
                journal.save()
                os.mkdir(folder)
            for src, dst in cases:
                journal.data["created_files"].append(dst)
                journal.save()
                if src is None:
                    with open(dst, "wb"):
                        pass
                else:
                    shutil.copyfile(src, dst)
                out("case: %s" % dst)
        exe = os.path.join(game, opts.launch)
        journal.data["launched"] = opts.launch
        journal.save()
        t0 = system.now()
        system.launch(exe, game)
        out("launch: %s" % exe)
        waited = wait_for_game(opts, system, set(journal["logs_before"]), t0, out)
        if opts.hold > 0 and waited["state"] == "reached":
            # The game stays up a while after the marker, so a helper can
            # capture the screen the player would see (the proof runs).
            out("hold: %.0f s" % opts.hold)
            t1 = system.now()
            while system.now() - t1 < opts.hold:
                system.sleep(opts.poll)
    except Exception as exc:                  # noqa: BLE001 - undone below, then reported
        error = "%s: %s" % (type(exc).__name__, exc)
        out("hrun: error - %s" % error)
    finally:
        if journal is None:
            release_lock(lock, token)
        else:
            summary = finish(journal, system, opts, waited, error, out)
    if journal is None:
        return 1, None
    good = (summary["sweep"]["ok"] and not summary["brick_suspected"] and error is None
            and (summary["state"] == "reached" or not opts.until))
    return (0 if good else 1), summary


def recover(opts, system=None, out=print):
    """Undo a run whose harness died, from its journal. Returns an exit status."""
    system = system or System()
    opts.resolve()
    lock = lock_path(opts.save_dir)
    held = read_lock(lock)
    journal_path = (held or {}).get("journal") or (
        os.path.join(opts.logs_dir, JOURNAL_NAME) if opts.logs_dir else None)
    if not journal_path or not os.path.isfile(journal_path):
        if held is not None:
            # The journal is written before anything is deployed, so a lock of
            # ours without one means the run died before it changed anything.
            os.remove(lock)
            out("recover: no journal; removed our lock %s - nothing else was changed" % lock)
            return 0
        out("recover: nothing to recover (no hrun lock, no journal%s)"
            % (" at %s" % journal_path if journal_path else "; pass --logs-dir"))
        return 0
    journal = Journal.load(journal_path)
    running = sorted(set(GAME_IMAGES) & system.running())
    if running:
        out("recover: REFUSED - %s still running; close the game first" % ", ".join(running))
        return 2
    out("recover: run %s from %s" % (journal["run_id"], journal_path))
    collect_selftest(journal, out)
    own_ok = restore_state(journal, out)
    for name in reversed(journal["deployed"]):
        own_ok = remove_deployed(journal, name, out) and own_ok
    for name in journal.data.get("game_created", []):
        own_ok = remove_game_created(journal, name, out) and own_ok
    own_ok = restore_mods_ini(journal, out) and own_ok
    own_ok = remove_created(journal, out) and own_ok
    ok, problems = sweep(journal, system)
    out("SWEEP OK" if ok else "SWEEP FAILED")
    for p in problems:
        out("  " + p)
    if own_ok:
        os.remove(journal_path)
    released = release_lock(journal["lock"], journal["token"])
    result = {"run_id": journal["run_id"], "recovered": own_ok, "journal_removed": own_ok,
              "lock_released": released, "sweep": {"ok": ok, "problems": problems}}
    if os.path.isdir(journal["run_dir"]):
        _write_json(os.path.join(journal["run_dir"], "recover.json"), result)
    out(json.dumps(result, indent=1, sort_keys=True))
    return 0 if own_ok and ok else 1


# --------------------------------------------------------------------- CLI
def parse_args(argv):
    p = argparse.ArgumentParser(prog="hrun.py", description=__doc__.split("\n\n")[0])
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--recover", action="store_true")
    p.add_argument("--fixture", action="append", default=[], dest="fixtures")
    p.add_argument("--no-quartermaster", action="store_false", dest="quartermaster")
    p.add_argument("--case", action="append", default=[], dest="cases")
    p.add_argument("--autotest-cfg")
    p.add_argument("--until")
    p.add_argument("--until-log", type=int)
    p.add_argument("--state")
    p.add_argument("--timeout", type=float, default=180.0)
    p.add_argument("--boot-marker", default="[qm]")
    p.add_argument("--expect-compile-error", action="append", default=[],
                   dest="expect_compile_errors")
    p.add_argument("--follow-bricks", action="store_true")
    p.add_argument("--hold", type=float, default=0.0)
    p.add_argument("--enable", action="append", default=[])
    p.add_argument("--unlisted", action="append", default=[])
    p.add_argument("--compose", action="store_true")
    p.add_argument("--canonical", action="store_true")
    p.add_argument("--disable", action="append", default=[])
    p.add_argument("--first", action="append", default=[])
    p.add_argument("--qm-folder")
    p.add_argument("--launch", default="cossacks.exe")
    p.add_argument("--keep-deployed", action="store_true")
    p.add_argument("--game-created", action="append", default=[], dest="game_created")
    p.add_argument("--run-id")
    p.add_argument("--game-dir", default=GAME)
    p.add_argument("--save-dir")
    p.add_argument("--fixtures-dir", default=FIXTURES)
    p.add_argument("--dist", default=DIST_MOD, dest="dist_mod")
    p.add_argument("--logs-dir")
    a = p.parse_args(argv)
    recover_only = a.recover
    del a.recover
    return recover_only, Options(**vars(a))


def main(argv=None, system=None, out=print):
    recover_only, opts = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if recover_only:
            return recover(opts, system, out)
        return run(opts, system, out)[0]
    except (Refused, hbuild.BuildError) as exc:
        out("hrun: refusing - %s" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
