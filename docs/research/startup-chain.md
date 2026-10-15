# Startup chain and file classes (safety audit, 2026-09-27)

Source: read-only audit of vanilla scripts (cross-checked against the logs of the in-game probe runs).
"verified" = observed in an in-game probe; "inferred" = read from code only - confirm with a probe before relying on it.

## Startup order (paths relative to the game dir)
1. `data/projects/project.main.prj:5` -> `data/resources/resource.lib` (table of all subsystems: objects.lib :6, font.lib :22, actors.lib :31, minimap.cfg :33, menu.cfg :34, user.aix :54, table.lng/table.lib :55,:74, dmscript.global :56, common.aix :78, resource.script :88).
2. `data/scripts/resource.script`: writes a language-patched resource.lib to Documents (:31), Steam/Workshop init (:35-42), `mods.restore` / `StringRegister7` restore branch (:44-74).
3. Libraries from `data/scripts/dmscript.source:71-100` (top-level code runs before any GUI): `init.script:211` NewMap, `:214` formations.cfg (via `:10`), `:258` checksum; `country.script:4281-4283` loads objcustom.cfg (:4113) and wallcustom.cfg (:4084); `profile.script:729-737`.
4. Races in `objects/objects.lib` load global.aix + group.aix (:6-7) and progress.aix (:60); `.prop` files load unit.aix / building.aix (`ref/refunit.prop:156`, `ref/refbuilding.prop:158`).
5. `gui/menu.cfg:2` loads menu.aix; `:3` DoCreate = create state; `:20,:28` DoProgress every 10 ms; `menu.aix:981` CurrentState=DoProgress.
6. DoCreate: `:46-50` first start -> `MapExecuteState('InitMap')` (common.aix:1-5) -> `common.inc/initmap.inc:39` CreatePlayers -> progress player (`player.script:652-654`) -> `initmap.inc:70` -> `control.script:718-719` `GUIExecuteState('DoUpdateSelection')` + `GUIExecuteState('InitMinimap')`; `:135` OnResize (skipped with bDbgCamera, :104/:126); `:149` project.main.prj; `:158` DoInitialize; `:278` `_gui_InitShowMainMenu` -> ShowMainMenu + ShowNews (`gui.script:2675-2676`); `:431` ShowAnnouncement.
7. DoInitialize: `:83` InitHUD, `:203` CameraControl, `:204` RegisterShortcuts (reads hotkeys.cfg, `registershortcuts.inc:188-192`), `:205` DoUpdateCursor, `:206` InitMinimap, `:252` DoUpdateSelection, `:254` DoAmbientSound.
8. DoCreate re-runs on every GUI rebuild (`onresize.inc:5-6` NeedRestartGUI) and every map load -> every hook runs many times per session -> hooks need a once-per-process guard.

## File classes -> Quartermaster rule
| File / class | Brick risk | Evidence | Rule |
|---|---|---|---|
| `gui/menu.aix` | brick | verified (`r9badmenu.0.log`: Parser load error line 982, IndexOfState(DoCreate)) | never generate (new GUI states: load own .aix at runtime) |
| `gui/menu.cfg` | brick (inferred) | declares GUI machine `menu.cfg:2-3` | never generate |
| `gui/menu.inc/docreate.inc` | brick | verified (`r10_baddocreate.0.log`) | never generate |
| `scripts/lib/*.script` | brick | verified (round 8: CompileFramework error + dialog) | never generate |
| `scripts/dmscript.source` | not used from mods (most likely) | verified-ish (round 10: Log in its Code did not print) | never generate |
| `project.main.prj`, `resource.lib`, `resource.script` | brick (inferred) | engine start-up files | never generate |
| `scripts/common.aix` | likely brick (inferred) | `docreate.inc:50`, `resource.lib:78` | never generate |
| `common.inc/initmap.inc` | likely brick (inferred) | `docreate.inc:50`, `initmap.inc:39` | never generate in prototype |
| `units/*.aix`, `progress.aix`, env/misc `.aix` | silent AI/state loss (inferred) | `objects.lib:6-7,60`, `player.script:652` | never generate (winner-takes-all) |
| `objects.lib`, `*.prop` | engine object tables (inferred) | `resource.lib:6` | never generate / winner-takes-all |
| `font.lib`, `font*.lib` | silent: fonts used BY INDEX | `classes.script:4556` (`gc_font_serif_12 = 17`) | never generate |
| `.lng` (binary), `table.lib` | binary / locale | `table.lib:2-20` | never generate .lng; table.lib append-only (later) |
| hud/materials/actors/sound `.lib` | engine tables (inferred) | `resource.lib:19-31` | later: append-only unique names, fail-closed; prototype: winner-takes-all |
| `formations.cfg` | SILENT TOTAL LOSS if >160 records (vanilla 149) | `init.script:11-14`, `dmscript.global:166` | later: record merge with count <=160, fail-closed |
| `objcustom.cfg`, `wallcustom.cfg` | not a brick (verified `r9baddata.0.log`), array-bound overflow risk | ExitPoints <=4, builders <=30, wall builders <=16, variation <24 (`dmscript.global:136-162`; used `country.script:4096,4134,4146`) | later: per-record bound checks, fail-closed |
| `hotkeys.cfg` | not a brick; IGNORED if player has a saved copy | `registershortcuts.inc:188-192`, `dmscript.global:1353-1354` | later: merge by Action + key-collision check; report that saved copy wins |
| `dmscript.global` | not a brick (verified: line without `=`, unknown type) | round 10 | Quartermaster never ships it; later additive-only merge, names unique case-insensitively |
| `doinitialize.inc` | not a brick (verified) but kills all DoInitialize hooks | `r9badinit.0.log` | merge + mandatory validation; fail -> winner-takes-all |
| `cameracontrol.inc` and other lazily compiled `.inc` | not a brick (verified `r9badinc.0.log`) | | 3-way merge + validation |

## Hooks (recommended)
1. **CameraControl** (primary; verified to run at start; 38 lines; SWFP does not override it).
2. **InitMinimap** (second): two call paths at first start - InitMap -> `control.script:719` BEFORE DoInitialize, and `doinitialize.inc:206`. May survive a broken DoInitialize (inferred -> probe in M0).
3. **DoProgress** (last resort): engine runs it itself (`menu.cfg:20`); verified to keep running with DoInitialize/CameraControl broken. Big and often modded (SWFP overrides it) -> Quartermaster always merges its lines.
- Drop DoAmbientSound (only through DoInitialize, :254). OnResize (`docreate.inc:135`) is a possible substitute but skipped with bDbgCamera.
- Hook lines: engine API only, no new globals, byte-identical across generations except the hash/generation constants, once per process (named parser flag), main menu only (`docreate.inc:49`). Ship static hooked copies inside the Workshop item so a wipe loses merges but not hooks.
- Weak spot: a newly auto-registered mod after Quartermaster that overrides all three hook files -> Quartermaster silently does not run (not a brick).
- Weak spot found hands-on, 2026-10-10: the hook lines sit in merged states, and a start loads the merge the last generation wrote. A mod of that merge switched off outside Quartermaster leaves a DoProgress that does not compile (`Compile script error: DoProgress`; it compiled lazily, after the boot in the CameraControl hook had already rewritten the file - the engine keeps the text it loaded). The boot ran and regenerated; the tick, which only DoProgress runs, did not, so the restart never came in that process. What was believed: that DoProgress is the hook that survives the others. What is true: it survives a broken DoInitialize or CameraControl (probes 7-8), not its own merge. The manager window now does the tick's work when no frame runs it (docs/ui.md, *When no frame runs the tick*). *Seen again 2026-10-14 (0.1.6):* Reinforced - Core's build changed with the game closed; the old DoProgress merge called a function the new libraries no longer have (`cos_261014_224523.log:196`), the boot regenerated and asked for its restart (:181), no line of the tick ever ran (no `hooks ... booted by`, no caption or version line), the player went for the lobby instead of the window and got a blank screen (`Compile script error: ShowCustomGame`, :206, the old lobby merge). How the engine ends a process: `RestartApplicationParam` returns, and the process ends later - the start-up guard's call, made in `resource.script` before the libraries compile, ended its life right after the start-up's second DoCreate, with the boot's regeneration and `Compile script error: DoProgress` in between (`cos_261010_130720.log:7`, :148, :158, :164-169; the next life, `cos_261010_130727.log`, started 7 s after it and booted clean, :122, :154); the tick's own restart also came after the second DoCreate (`cos_261014_200458.log:196`, :210-211). Two calls in one process - the guard's in `resource.script`, then the boot's at its end - make one restart: one next life, 7 s later, and no third within 40 s (run g22g, 2026-10-15). So a start that rewrote its outputs now restarts at the end of its boot, from the hook that ran it (docs/plan.md S8, *Corrected 2026-10-15*, with the run that proved it).

## Restart-loop risks and guards
Loop paths: Quartermaster's own output or mods.ini counted as input (FileAge changes on write; Quartermaster moves itself); hook re-runs on every DoCreate; new folders auto-registered; MP sync (inferred): a Quartermaster restart during the sync boot -> restore branch (`resource.script:64-69`) reverts the mod list -> checksum fails (`docreate.inc:246-247`) -> retry.
Guards:
1. Once per process, main menu only. No auto-restart if `StringRegister7<>''` or `<save>\mods.restore` exists (check with `FileAge`, not `IsFileExists`). If regeneration is needed then, recreate the tmp/checksum section like `eventconnectstatemessage.inc:72-82`.
2. Fingerprint inputs only: canonical mod ids + enabled flag, other mods' timeupdated/FileAge, vanilla FileAge, Quartermaster version. Exclude Quartermaster's folder, its mods.ini position and anything Quartermaster writes.
3. Deterministic output; restart only if some output file's bytes actually changed; rewrite mods.ini only if its content differs.
4. Start marker in `<save>\quartermaster\state.cfg`: `gen N, hash H, state written|booted, autoRestarts k`. `written` before restart; first hook of next start sets `booted`. `written` without `booted` -> suspected brick of gen N -> do not regenerate the same H, fall back to winner-takes-all, report FAIL. Max 1 automatic restart per hash, 2 in a row; then only manual Apply.
5. Never write or create folders in `mods\` outside Quartermaster's own folder (the game auto-enables any folder). "Create mod" records the new id before restarting.
