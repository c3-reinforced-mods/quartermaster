# Quartermaster

A merge framework and in-game mod manager for **Cossacks 3** (GSC Game World).

Two mods change the same game file, and the game simply takes the last one: the other
mod's change is gone, or the game stops at "Error compiling scripts". Quartermaster
fixes that inside the game. It is a tool, not a gameplay mod: on its own it changes
nothing in battles, units or balance, and it needs no other mod.

Version 0.1.0 (beta). Players get it from the game's Steam Workshop.

## What it does

- **Merges** the interface and game script files (`.inc`) two mods both change, line by
  line, against the game's own copy; where two mods change the same lines, the mod later
  in the load order wins. Every merged file is compiled by the game before it is used; one
  that does not compile falls back to a copy that does.
- **Protects the start:** a new subscription that ships a core script an enabled mod
  ships too (two copies of `scripts\lib\*.script` cannot load together) is switched off
  before the scripts compile, and the player is told which one and why.
- **Keeps the player's load order:** mods load in the order mods.ini already has;
  Quartermaster only puts itself last. The order can be changed in its window, or by
  Auto-sort.
- **A mod manager in the game** (main menu, Mod Manager): switch mods on and off, move them
  in the load order, and see for every mod how it loads.
- **Reports** what it did: `Documents\cossacks\quartermaster\report.txt` file by file, the
  window's Report view mod by mod, and `conflicts.txt` for every pair of mods that change
  the same code - which file, where in it, whose version is active and why.
- **Settings for mods:** a mod that declares settings in an `about.cfg` gets an Options page
  in the window, and reads the values from a named parser at run time.

## For mod authors

A mod needs nothing to work with Quartermaster. An optional `about.cfg` in the mod's folder
declares its id, version, load-order rules (`requires`, `loadAfter`, `loadBefore`,
`incompatibleWith`, ...) and settings; see [docs/authoring.md](docs/authoring.md).
New mod in the window creates a mod folder with a draft about.cfg.

## Building

Requirements: Windows, Cossacks 3 installed from Steam, Python 3 (3.13 is what it is built
with). The build reads the installed game: the hook files are the game's own scripts with
Quartermaster's lines merged in, and `vanilla.idx` lists the game's files.

```
python tools/hbuild.py                # writes dist/Quartermaster (lints first)
python tools/hbuild.py --check        # builds in memory and compares with dist
python tools/hbuild.py --vanilla-idx  # also regenerates data/quartermaster/vanilla.idx
```

`dist/` holds files of the game itself and is never part of the repository. `--deploy`
copies the build into the game's `mods\Quartermaster`; `--update` replaces an installed
copy and keeps its mod.ini once it names a Workshop item (its id after an upload), else
takes the build's.

## Tests

```
python -m pytest                 # fast tests
python -m pytest --runslow       # every test
```

The tests read the installed game (and skip what needs a mod that is not installed); no
file of the game or of another mod is copied into this repository. `ref/` is a Python twin
of the game-side code in `src/`: the tests run that code in an interpreter of the game's
script language and compare its output with the twin's, byte for byte. Do not run the tests
while the game runs from a harness run (`tools/hrun.py`).

## Layout

| Path | What is there |
|---|---|
| `src/` | the game-side code: states, screens, hooks, libraries (`.pas` sources `tools/hbuild.py` assembles) |
| `ref/` | the Python twin: merge, plan, validation, report, conflict report, load order |
| `tools/` | the build (`hbuild.py`), the test harness for in-game runs (`hrun.py`), the acceptance checkers |
| `tests/` | the test suite |
| `docs/plan.md` | the design: safety decisions, architecture, acceptance criteria |
| `docs/ui.md` | the manager window, its keys and the report seams |
| `docs/authoring.md` | about.cfg, its rules and settings |
| `docs/research/` | verified facts about the engine, with their evidence |

## License

[MIT](LICENSE). Cossacks 3 is a game by GSC Game World; this project is not affiliated
with GSC, and none of the game's files are part of it.
