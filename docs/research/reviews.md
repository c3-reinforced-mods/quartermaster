# Architecture reviews (2026-09-27)

Two reviews of the design in `context-2026-09-27.md`. Decisions taken from them are in `docs/plan.md` §1-2; this file keeps the reasoning and the details the milestones need.

## A. Simplification review - "can it be simpler?"
Short answer: yes, ~25% of the design proves the core. The merge core already exists (probe 5, ~190 lines, verified in-game: parser read, trim, LCS, hunk overlap, parser write).

Findings adopted:
1. "Same state -> WARN" flags nearly everything: all 313 vanilla `.inc` are a single `section.begin` state, 229 have no procedure -> use hunk overlap / proximity instead.
2. ">50% changed -> full replacement" measured on the trimmed region would refuse the verified case (`r5c` log: mod B prefix=1 suffix=0 region 72x72 of 73 lines) -> measure by edit count after the diff.
3. Stale output: Quartermaster is last, so a leftover merged file would override the remaining mod and revive a disabled mod's changes -> manifest + cleanup.
4. "Hash all data always" contradicts "read only files touched by >=2 mods" (objcustom.cfg 1.56 MB ~ 1.8 s per copy; FileAge differs per machine) -> hash merged outputs + (path, mod id, timeupdated).
5. Validation needs a temp file outside the mirrored `data\` paths, otherwise the engine loads it natively.
6. DoProgress is a poor primary hook (SWFP overrides it, 1742 lines) -> last resort only.
7. New-mod policy cannot stop a mod's first run (auto-registered after Quartermaster, enabled) -> this is why a second hook is needed.
8. Hooks re-run on every DoCreate (GUI reload, map load) -> once-per-process guard.
9. Create-mod and `text` settings depend on GUI text input (open -> M0 probe; vanilla `_gui_CreateInputBox` exists).
10. Raw-text/CRLF layer only needed for data; `.inc` via parser (verified byte-identical). *Reversed 2026-09-28:* the parser strips trailing spaces from Code values and appends to a Code node only once, so `.inc` also goes through the raw layer ([context §3](context-2026-09-27.md)).
Suggested (adopted in Phase A): index by `FileAge(dir+path)<>-1` over a shipped list of vanilla paths; Myers with D cap (~1M Integer budget -> D ~ 700-1000); over cap -> winner FAIL; manager v1 = two lists + ->/<- + Apply; data winner-takes-all in v1; about.cfg/settings/create-mod deferred.
Probes requested: `DeleteFileStream`, cost of ~3000 `FileAge` calls, Myers speed on `progresswarai.inc` (4261 lines), `ParserSaveToFile` creating subfolders.

## B. Implementation-plan review
Constraints found in code:
- No Quartermaster library possible: libraries are listed in `dmscript.source` (not read from mods); runtime `StateMachineLibraryGetOrAddExt` failed (`r7.0.log`). Each state compiles alone -> helpers must be inlined per state (build tool).
- String arrays allocate slowly (1M = 15 s), Integer arrays instantly (`r10_base.0.log`) -> bounded String pool per state (~196k ~ 3 s), Integer ids where useful.
- Size cap: `pattern.lib` has 1.17M lines (> array limit) -> files > ~60k lines winner-takes-all WARN; objcustom.cfg (51.6k) fits.
- Existence checks via `FileAge = -1` (IsFileExists logs an ERROR).
- READ quirk: file length divisible by 4 and no final LF gains a trailing space (past-EOF value 32) - the Python reference must reproduce it.
- Quartermaster must not ship `dmscript.global` (would override other mods' globals as last mod).
- Unverified engine calls to probe: `CopyFileStream`, `MoveFileStream`, `RenameFileStream`, `DeleteFileStream`, `_gui_CreateInputBox` (vanilla `showprofile.inc` and others).
Module list G1-G18 and the dev tools -> `docs/plan.md` §3. Build: generate with Python (`hbuild.py`), built output committed; lints are the only debugger because compile errors carry no details.
Tests: offline gates (split/join identity, linear diff == DP LCS on 10k seeded cases, merge properties `merge(v,A,v)=A`, `merge(v,A,A)=A`, non-overlapping edits survive), in-game unit loop via `hrun.py` + SelfTest marker, integration runs I1-I8 (+ I9 stale cleanup added in plan).
M0 probe list: nested-procedure scope, array var-parameters, recursion, Integer overflow / `shr` on negatives, String allocation at 64k/128k/256k, parser as a heap/dictionary, Copy/Move/Rename/Delete file streams, writing into `<save>` subfolders, missing trigger-manager handle behaviour, reusing one validator trigger manager, event from a Quartermaster GUI element reaching a hooked vanilla Event state, runtime-added GUI states (StateMachineStateAdd) for screens, InputBox, ListBox tabs, whether a broken `doprogress.inc` / `eventmainmenu.inc` bricks.
Effort estimate: ~23 dev-days total (Phase A ~12, Phase B ~11).
