# Pre-compile guard probes (2026-09-28)

Eight in-game runs of a temporary probe mod (`QmProbe`) whose only file is
`data\scripts\resource.script`: the vanilla file byte for byte with probe code
appended. `resource.script` is the on-load script of `data\resources\resource.lib:88`
(`OnLoadScriptFileName`), and the only script that runs before the libraries
compile ([the startup chain](startup-chain.md), step 2). Every run went through
the test harness (`tools/hrun.py`) with a composed `mods.ini`; after each one
the installed `mods.ini` was byte-identical to the baseline, the `mods\` listing
and the 311 vanilla files unchanged (SWEEP OK), and all 22 Workshop items were
still installed. Evidence is cited as `<run> <life>.log:<line>`.

| Run | Mods on (load order) | Left out of mods.ini | What the probe did |
|---|---|---|---|
| g1 | Cannons (1450025705), MGraphics Lights (855882129), QmProbe | ZoomOut (873048118) | listed every mod and its global scripts; switched ZoomOut off in mods.ini; restarted |
| g2a | State vs Country (1325221799) | Cannons | nothing (no QmProbe): control |
| g2, g3, g5 | State vs Country, QmProbe | Cannons | as g1, with Cannons as the target |
| g4 | as g2 | Cannons | as g2, then `CloseQuery` |
| g6 | as g1 | ZoomOut | dumped `ModLibraryGetParser`, tried `ModLibGetFileExist` |
| g7 | as g2 | Cannons | `SteamSyncWorkshopItems` with Cannons off in the list |
| g8 | as g2 | Cannons | the full sequence below |

## Verdicts

1. **A mod's copy of `resource.script` replaces the vanilla one.** The probe's
   first line comes right after the vanilla part (`SteamPrepareWorkshop`,
   the `mods.restore` check): g1 0.log:2-4. A local folder in `mods\` is
   enough; no Workshop mod ships the file (22 items checked).
2. **Everything the guard needs works there**, before any library is compiled:
   `ModLibraryGetCount`/`ModLibraryGetData` (29 mods with dir, dis, title,
   tag: g1 0.log:6-80), `ParserGetFilesInRoot(dir+'\data\scripts\lib\*.script')`
   on Workshop and local folders (g1 0.log:11, 71), the parser round trip of
   `ModLibraryGetIniFile` (g1 0.log:81-82), a parser file in
   `<save>\quartermaster\` (g1 0.log:83), and `LanShutdown; SteamwrapFree;
   RestartApplicationParam('')`: the second life started 27 s later
   (g1 1.log). `ModLibGetFileExist(libind, 'data\scripts\lib\unit.script')`
   answers per mod and, unlike `IsFileExists`, logs nothing for a missing
   file (g6 0.log:8-35; `IsFileExists` logs one `ERROR| FileStreamExists` per
   miss, g1 0.log:7-8).
3. **A new subscription is already registered and on.** ZoomOut, left out of
   mods.ini, was appended by the engine with `dis=False` before the probe ran
   (g1 0.log:80); after the probe switched it off and restarted, the second
   life had it off (g1 1.log:79).
4. **State vs Country + a new Cannons is a brick** (control g2a:
   `CompileFramework() - compile global script error: ... Unknown Name`):
   Cannons' `scripts\lib\unit.script` is vanilla plus two lines and replaces
   State vs Country's.
5. **Switching the mod off in mods.ini and restarting does not save the start
   it was found in.** `RestartApplicationParam` returns (g2 0.log:84), the
   libraries still compile with the mod in, and the game stops at the error
   (g2 0.log:100). `CloseQuery` after it changes nothing (g4 0.log:85, 101).
   The error screen is drawn by the game, not a Windows dialog: no `#32770`
   window of the process appeared in 200 s (g5).
6. **`SteamSyncWorkshopItems` takes a mod out of the running start.** Handed
   the engine's own list (`ModLibraryGetParser(p, False)`: `mods` of
   `tag`/`dis`/`dir`/`tit` entries, the list the vanilla multiplayer sync
   saves as `mods.restore`) with Cannons `dis=True`, it returned 0, Cannons
   read off in `ModLibraryGetData` at once, and the same start compiled
   (g7 0.log:4-9, `...DoCreate started...` at :39). **Side effects:** it
   switched every local mod off (QmProbe included) and moved the enabled
   Workshop item to the front, in memory and in mods.ini (g7
   mods.ini.during). Nothing was unsubscribed or downloaded.
7. **The full sequence works** (g8): keep mods.ini as loaded, sync with the
   mod off, write the kept file back with only that mod off, restart. Life 1
   compiled (g8 0.log:38) and restarted; life 2 had State vs Country and
   QmProbe on, Cannons off, the order unchanged, and compiled
   (g8 1.log:5-8, :38). 66 s for both lives.

## Consequences for the design

- The guard lives in Quartermaster's own `data\scripts\resource.script`, so
  switching Quartermaster off in the Mod Manager removes it.
- It must carry the vanilla file unchanged in front of its own code, and must
  stay out of the multiplayer sync (`mods.restore` / `StringRegister7`).
- It detects conflicts by file names only (global scripts shipped by two
  enabled mods); it cannot know whether a set compiles.
- It uses the sync only to take mods out of the running start, and writes
  mods.ini back itself, because of the side effects in verdict 6.

## Undoing a library before the compile (Phase C probes, 2026-09-29)

Three more runs (a probe script, no Quartermaster, only the
probe folder on): a local mod whose `data\scripts\lib\miscext2.script` is
vanilla plus one line that is not Pascal, and in two of them a
`data\scripts\resource.script` (vanilla, then probe lines) that acts on that
file before the libraries compile. SWEEP OK after each.

8. **Control (c2):** the start stops at
   `CompileFramework() - compile global script error: Syntax error: Line: 60812`
   ten seconds in (`c0c2-broken-175706` 0.log:6).
9. **Deleting the library does not undo it (c3):** `DeleteFileStream` removes
   it (`FileAge` -1 after, `c0c3-delete-175717` 0.log:4-5), but the engine
   still asks for the mod's file
   (`ERROR| CreateFileStream: .\data\scripts\lib\miscext2.script`, :7) and
   the start hangs - no menu and no error line in 240 s.
10. **Overwriting it does (c3):** `CopyFileStream` of the vanilla file over the
    mod's copy (a new `FileAge`, `c0c3-copy-180119` 0.log:5) - the same start
    compiles the new bytes and reaches the menu 10 s in (`...DoCreate
    started...`, :9).

So the guard undoes a library Quartermaster wrote by writing other bytes into
the same file, never by deleting it. Those bytes must compile with the mods
that stay on: for a pair whose start fails without the merged copy, the
sequence of verdict 7 switches the later mod off as well.
