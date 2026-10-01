# What Quartermaster reuses from SW: Frontline Protocol (2026-09-27)

Source: read-only survey of `mods\SW_Frontline_Protocol` (`<R>`). The game is pinned at 2.2.3.6008 there (`tools/swfp/vanilla.py:129`).

## WASD camera (basis for the Quartermaster test mod)
- All in `<R>\tools\swfp\patches\camera.py`: table `CAMERA` (:58-63 - Left/A tag 20, Right/D 21, Up/W 22, Down/S 23), `TAG_UP=30`, `SHORTCUT_PREFIX=b"swfpcamera"`, `RESEAT` (:79-85), `EVICTED` (:91-93). Registered in `tools/swfp/targets.py:747-764`. Template `tools/swfp/templates/hotkey_reseat.pas`.
- Files and edits (vanilla line numbers):
  1. `data/gui/menu.inc/registershortcuts.inc`: after the `spiUp` arrow block (:14-17) 8 registrations `RegisterGUIShortcutIgnoreShift(False, 'swfpcamera<stem>r', 'A', filter, 'spiRepeat', 'OnCamera', 20)` ... and `'swfpcamera<stem>up', <key>, filter, 'spiUp', 'OnCamera', 30`; after `:199` (`var action : String = ParserGetValueByKeyByHandle(pHotkey, 'Action');`) the re-seat block (skips `event|`, matches BY ACTION, rewrites hotkey/alternativekey on A/D/W/S; moves `interface|viewcollision` Q->Ctrl+I).
  2. `oncamera.inc` :18-21 `var bLeft : Boolean = IsKeyDownByName('Left');` x4 -> `... or IsKeyDownByName('A');` (without it: no diagonals, camera drifts after release).
  3. `hotkeysettings.inc` after :31 - 4 `forbiddenkeys` rows (array bound `keysarraycount = 60`, :20).
  4. `data/game/var/hotkeys.cfg` lines 24, 32, 85, 89, 117, 150: attack A->Q, standground S->X (+ `build|%nat%sta`), disableattack D->V (+ `build|%nat%dip`), viewcollision Q->Ctrl+I.
- Why re-seat at registration: the shipped .cfg is only read if `<Documents>\cossacks\hotkeys\hotkeys.cfg` is missing (`registershortcuts.inc:187-190`; `docs/hazards.md:15`).
- Verification: `tools/verify.py:5805-6025` (category camera) - file minus declared edits == vanilla, no bare LF, tags handled by vanilla OnCamera case, all 4 files agree on keys, forbiddenkeys fits, no camera key left in cfg, every vanilla action on A/S/D/W in RESEAT, new seats free. Unit tests `tools/tests/patchcases.py`, `synth.py`, `test_patch_bytes.py`, `test_patch_idempotency.py`. No in-game WASD test exists.
- Open issue: `filter` is '' unless dev mode (`registershortcuts.inc:4-6`) and IgnoreShift may ignore modifiers -> Ctrl+A / Ctrl+S may also scroll (unmeasured; `docs/roadmap.md` row 57). Quartermaster WASD test should check it.
- Getting the 4 files: (a) copy `<R>\data\...` (exactly vanilla+WASD, this game version only); (b) generate: import `swfp.patches.camera` (put `<R>\tools` on sys.path) and call `patch_registershortcuts`, `patch_oncamera`, `patch_hotkeysettings`, `patch_hotkeys_cfg` on vanilla bytes (pure `data -> PatchResult(data, steps)`); do NOT use `build.py --only` (writes SWFP's own data/).
- Rename the shortcut prefix for the Quartermaster fixture (e.g. `qmwasd`) so it cannot collide with SWFP.

## Harness to reuse
- `tools/autotest.py`: marker `<Documents>\cossacks\swfp_autotest.cfg` (parser file), launch `cossacks.exe` with cwd=GAME, Steam relaunch (exit 53) -> track by image name, poll done.txt/exit/timeout, foreground-only actions, desktop grab per `*.cue` (engine snapshot returns black), optional WASAPI loopback audio, finally kill all + remove marker, log diff + `smoke.py --log`.
- `templates/autotest.pas` phases 0-3 (marker check once; ShowCustomGame; seed/mapsize/season/nations + `gbool_gui_donewgamerestart := True` + `ExecuteState('DoNewGame')`; wait gamemode_game + gamestage_started) = generic "drive into a skirmish" code.
- `tools/harness.py`: `manifest`/`same` (sha256 of data/ + mod.ini), `sweep`/`untouched` (game dir outside mods/<mod>/; hashes cossacks.ini and mods/mods.ini).
- `tools/smoke.py`: reads `cossacks.ini` (LogFileEnabled), builds error patterns from cossacks.exe strings, ALLOW list, verdicts CLEAN/FAIL/STALE/NO_LOG/INCONCLUSIVE, `--json`.
- No lock-file protocol in SWFP -> Quartermaster uses `Documents\cossacks\swfp_game.lock` (shared with SWFP sessions; the probe launcher already takes it).
- Key injection for a WASD in-game test: not in SWFP (suggest SendInput while foreground; camera position via `GetCameraPosition` log lines).

## Patching model and tooling
- `tools/c3kit/formats/bytes_ops.py`: `PREFIX = b"      [*] = ;"`, `CRLF`, `line()`, `substitute(data, old, new, what, expect=1|"1+")`, `live_lines`, `replace_live`, `comment_line_containing`.
- `swfp/rules.py` (`PatchResult`, `Rule`, `Patch(requires, provides, const_anchor)`), `swfp/emit.py` (`.pas` templates: `requires:`/`wrap:` front matter, `${name}`, `//!` notes dropped, strict errors), `swfp/targets.py`, `swfp/pipeline.py:230-264` (build_plan in memory, "two targets claim the same path").
- `tools/c3kit/formats/gscript.py`: offline Pascal-dialect lint (balance, resolve, order, byref; 0 false positives on vanilla).
- Conventions: `docs/conventions.md` (B1-B12, V1-V11, E1 prefix, E2 begin/end markers, E3 minimal overlay, E7 namespace register, D1-D12), `docs/architecture.md`, `docs/hazards.md`, `docs/namespaces.md:392-408`.
- Commits `<type>: <imperative>` (feat/fix/docs/build/chore/test/revert), lower case, no trailing period, body says why.
