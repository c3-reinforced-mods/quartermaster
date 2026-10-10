# Manager window v1.1 (G15) - design note

The window that replaces the vanilla "Mod manager" button's Workshop page:
Installed on the left, Active in load order on the right, Activate / Deactivate
between them, Move up / Move down under the Active list, a one-line Details
panel, and Apply (with Quartermaster's own confirm dialog), Report, Open
Workshop and Close. The Report view shows the report grouped by mod. This note
owns the window's named-parser keys, its commands and the lines it needs from
the hook files. The safety rules are in [the plan](plan.md) (S1, S5, S6, S8);
the vanilla patterns it copies are in [gui-patterns](research/gui-patterns.md);
the screen mechanism was chosen in [the M0 probes](research/m0-probes.md)
(probes 9-11).

State of this version: v1 was built, wired into the hooks, the boot and the
report, and checked by hand (2026-09-28). v1.1 answers that
check's nine points: a status for every loaded mod, a manual load order
set by the player, Apply only with pending changes, one Details line
and a report by mod, a filter on every keystroke, the title in the head frame,
the changes in the confirm dialog, a restart notice, and the main menu button
renamed. The window writes nothing to disk itself. A confirmed Apply leaves its
intent in `qm_rt`; the boot's main-menu tick picks it up, writes `mods.ini`,
regenerates and restarts (below).

## Pieces

| Piece | Source | Emitted into | Runs in |
|---|---|---|---|
| `ShowQmManager` | `src/screens/showqmmanager.pas` | `data/quartermaster/ui/showqmmanager.inc` | GUI machine (added at run time) |
| `EventQmManager` | `src/screens/eventqmmanager.pas` | `data/quartermaster/ui/eventqmmanager.inc` | GUI machine (added at run time) |
| `qmUiEnsure` | `src/states/qmuiensure.pas` | `data/quartermaster/core.aix` | trigger manager `qm_core` |
| `qmUiAct`, `qmUiModel`, `qmUiDetails`, `qmUiApply` | `src/states/qmui*.pas` | `data/quartermaster/core.aix` | trigger manager `qm_core` |
| `qmUiOrder` (load-order commands, twin `ref/order.py ui_move`) | `src/states/qmuiorder.pas` | `data/quartermaster/core.aix` | trigger manager `qm_core` |
| `qmTick` (restart notice, button caption) | `src/states/qmrestarttick.pas` | `data/quartermaster/core.aix` | trigger manager `qm_core`, from the DoProgress hook |
| `qmPump` (the tick's work when no frame runs it, see *When no frame runs the tick*) | `src/states/qmpump.pas` | `data/quartermaster/core.aix` | trigger manager `qm_core`, from `ShowQmManager` and `EventQmManager` |
| EventMainMenu hook | `src/hooks/eventmainmenu.pas` | `data/gui/menu.inc/eventmainmenu.inc` | GUI machine (vanilla state) |
| OnLanEvent hook (host settings, a client's side) | `src/hooks/onlanevent.pas` | `data/gui/menu.inc/onlanevent.inc` | GUI machine (vanilla state), runs `qmHostRecv` |
| `qmSetSave` (the Options view's save) | `src/states/qmsetsave.pas` | `data/quartermaster/core.aix` | trigger manager `qm_core`, from `qmTick` |

The GUI states only draw and translate events; all behaviour is in `qmUiAct`
(and `qmUiOrder` for the order), so a scripted test can drive the window by
writing `cmd` and running that state. A trigger-manager state cannot read the
GUI event values, so `EventQmManager` passes them in `qm_ui` (probe 9b).
Offline desk checks run these states on the script interpreter:
`tests/test_m6_window.py` (the controller) and `tests/test_m6_events.py` (the
event state over an emulated GUI).

The window is a modal, and only `EventQmManager` can close it; a state that
does not compile does not run (probe 8). So a fresh open first runs
`EventQmManager` with `ping` = 1 and draws nothing unless `pong` comes back and
`qmUiAct` took the command `open`; otherwise the button falls back to the
vanilla Workshop page. A command the controller did not take closes the
window. Parent and event state are set before anything else is drawn, so Esc
reaches `EventQmManager` even if drawing stops half way.

## Adding the screens (qmUiEnsure)

`qmUiEnsure` reads each screen file through the engine parser and adds it with
`StateMachineStateAdd` / `StateMachineStateAddCodeLine`, every line before the
state first runs (probe 9a verified the mechanism with real clicks).

**No lookup by name is silent when the name is missing.** The engine exports
no state count; the name lookups (`StateMachineGetStateIndByName`,
`StateMachineGetStateHndByName`) go through `TXStateMachine.IndexOfState`,
which logs one ERROR per lookup of a missing name (probe 10). Vanilla never
checks for a state. Until 0.1.3 the check used one such lookup and so cost one
ERROR line (`IndexOfState(ShowQmManager)`) at the first main menu after every
battle - harmless, but it read like a fault in the log. A lookup of a present
name is silent, so the check now asks the other way round, by index:

- `ready` = 0 (new process): the GUI machine was just read from `menu.aix`, so
  both states are added without a lookup, and the index `ShowQmManager` got is
  kept in `qm_ui` `showidx` (the log line `ui ensure: added ... index=` shows it).
- `ready` = 1: the name at `showidx` (`StateMachineGetStateNameByInd`) must be
  `ShowQmManager`. A map load reloads the whole GUI machine and drops both
  states together (probe 10), so the index is past the end of the list - the
  states were added at 142 and 143 after `menu.aix`'s 142 - or holds another
  state; the name differs, and both states are added again.
- Outside the main menu the state does nothing.

**Checked in game (run g17b1, 2026-10-05):** a skirmish the run switch
started and the player left through the menu. At the first main-menu DoCreate
after it the read at the remembered index (142, past the end of the reloaded
list) answered silently: no `ERROR` line and no `IndexOfState` line, `screens
gone`, both states added again at 142 and 143, `ready=1 adds=2`, and the
window opened afterwards (`ui show ... windows=1`). `tools/m6cases.py log RUN
--battles 1` passes. Only that one kind of start was run; the rule of
`m6cases.py` fails on any `ERROR` line of that DoCreate before `screens gone`, so
another kind (a campaign mission, a loaded save, a LAN battle) that behaved
differently would show.

## Status, pending marks and Apply

- **Status** (`st<i>`, drawn in both lists in the vanilla colour tags,
  `dmscript.global:1212-1217`; plain text, no glyphs): `-` only for a mod the
  game did not load. A loaded mod takes the status of its `qm_report` record,
  matched by dir: `OK`, `WARN`, `FAIL` or `NEW`. After every generation the
  report has a record for every enabled mod, one that ships no scanned file
  included (its status is `OK`; `ref/report.py qm_report`). A loaded mod
  without a record - the report is from a generation that did not load it -
  is `OK` when the boot's index shows it ships none of the files Quartermaster
  merges (`stsrc<i>` = `index`), and `?` otherwise, with a `ui model: no report
  record` log line; the next start with it generates one.
- **Pending marks**: a row Apply will activate is marked
  `+` (green), one it will deactivate `-` (red), in the lists' mark column; an
  Active row pending activation shows `+` as its status, since it has none yet.
- **Apply** is enabled only while `canapply` = 1: in browse mode, with a row
  whose activation differs from what the game loaded (`chg` > 0) or a load
  order that differs from the one it loaded (`ordchg` = 1). A disabled button
  also gets a grey caption. The controller refuses an Apply with nothing
  pending in any case ("Nothing to apply.").

## Load order

The Active list shows the pending load order `ord<k>`; Quartermaster is always
last. **Move up / Move down** move the selected Active row one place among the
active rows; inactive rows keep their slots (qmUiOrder, whose rules and twin
are in `ref/order.py`). Apply carries the order to `qm_rt uiapplyord<k>` and
the boot's qmOrder makes it the saved load order (`<save>\quartermaster\order.cfg`;
an order equal to mods.ini's own deletes that file again). Without a saved
order the load order is the one mods.ini has, Quartermaster last: what
the game loads without Quartermaster. Auto-sort gives the canonical order.

**Drag was tried and dropped** (2026-09-28). The engine has no
list drag-and-drop call (its `GUIListBox*` exports insert, delete and select items
only; vanilla drags nothing but its sliders: `onmousehook.inc:9-12`,
`onmousemove.inc:36-58`). A drag built from a list's `select` with the left button
held never started in the hands-on check: every select arrived with the button
already up (12 x `ui drag none: the button was up at the select`). A real drag would
need the mouse-down and mouse-move events of `data/gui/common.inc/onmousehook.inc`,
i.e. a fifth hook file outside S5. The order is set with Move up / Move down only.

## Custom-order footer (added 2026-09-28; taken out 2026-09-30)

Until 2026-09-30 the window showed one line under its bottom buttons, in both
views (`tfoot`), while the effective load order was not the canonical one:
"Custom load order: every player in a multiplayer game needs the same mods in
the same order." It rested on the canonical order being the default, which
the players of one multiplayer game would share without agreeing on
anything. The decision of 2026-09-30 made mods.ini's own order the default - as a default the
canonical order changed which mod wins every whole file two mods ship, and a
set that starts without Quartermaster (Cannons + State vs Country) stopped at
"Error compiling scripts" with it - so the line would show on nearly every
machine. It went, with qmUiAct's `ordcustom`, the twin `ref/order.py
ui_custom` and the `custom=` field of the `ui show` log line. The
multiplayer note stays in two places: the report's Boot block, an OK line
while the enabled mods' order is not the canonical one (`qm_order` `canon` =
0), and the lobby line (`lobbycustom`, below).

- **Canonical order**: qmUiModel copies `qm_mods` `cord<k>` into `qm_ui`
  `cord<k>` when `qm_mods` lists exactly the window's rows and `cord<k>` is a
  permutation of them (`hascanon` = 1). Auto-sort needs it and is disabled
  without it (the model's log line then says `canon=0`).

## Commands (qm_ui `cmd`)

`EventQmManager` writes one command and runs `qmUiAct`, then hides the window
(`close` = 1) or runs `ShowQmManager` again.

| Command | From | Effect |
|---|---|---|
| `open` | `ShowQmManager`, when no visible window exists | rebuild the model (`qmUiModel`), reset selection, panel, mode, filter |
| `select` | list `select` event; `arg` = row, `argside` 0 Installed / 1 Active | select the row, rebuild the Details line (`qmUiDetails`) |
| `activate` / `deactivate` | Activate / Deactivate buttons | change the pending flag `pe<i>`; Quartermaster refuses to deactivate itself (plan S1: that is modman's job) |
| `up` / `down` | Move up / Move down; `arg` = `sel` | copied into `ocmd` for `qmUiOrder`: one place up or down the Active list |
| `move` | not sent by the window since drag was dropped; `arg` = row, `argto` = its place in the Active list afterwards | copied into `ocmd` for `qmUiOrder`; the moved row stays selected |
| `report` | Report / Back button | switch between the lists and the Report view (`panel`) |
| `apply` | Apply button | with changes, open the confirm dialog (`mode` = 1) and list them (`conf<k>`); a clash in the pending set is a `Note:` line of that list (0.1.3; until then the dialog listed the clashes instead, `confblk`) |
| `ok` | OK of the guard's notice; Enter or Esc in mode 3 | back to browsing (`mode` = 0) |
| `confirm` / `cancel` | dialog buttons | `confirm` runs `qmUiApply`; a recorded request shows the restart notice (`mode` = 2); `cancel` closes the dialog |
| `filter` | a key's release in the filter box when its text changed; `argtext` = the text | filter the Installed list |
| `esc` | Esc | `cancel` in the dialog, `report` (back) in the Report view, else `close` |
| `enter` | Enter | `confirm` in the dialog, else `filter` |
| `workshop` | Open Workshop (the event state already called `OpenURL`) | log only |
| `autosort` | Auto-sort (tag 119) | the pending order becomes the canonical one (`cord<k>`: about.cfg rules, then Workshop id / folder name); `ordchg` again |
| `options` | Options (tag 118), a row with settings selected | open the Options view (`panel` = 2) with an edit copy of the row's settings (below) |
| `optbtn` | a setting's button; `arg` = the setting, `argto` = 0 the main button, 1 the other | bool switches; int / float `+` (0) or `-` (1) one step, clamped; choice the next (0) or previous (1) option, round the list; key waits for a key (`optcap`); text points the Options text box at it (`optsel`) |
| `optkey` | the key a capture took (`argtext`, '' for Esc) | checked (below) and taken into the edit copy, or refused with the reason |
| `optpage` | Previous / Next (tags 113, 114); `arg` = -1 / 1 | the Options page, ten settings each |
| `optdef` | Defaults (tag 117) | every setting of the edit copy back to its declared default |
| `optcancel` | Cancel (tag 116), Esc in the Options view | back to the lists, the edit copy dropped |
| `optacc` | Accept (tag 115) | the edit copy into `qm_settings`, `qm_rt` `setsave` for the file, `rereg` for new keys; back to the lists |
| `close` | close button, Close, Esc | hide the window |

While the dialog is open only its answers count; while the restart notice
shows only `close` does (the restart comes anyway, and the notice stays the
mode: a later open shows it again).

Keys: every keystroke's release in the filter box is read
(`eventloadgame.inc:77-99` redraws its window on every key the same way).
Esc and Enter arrive as shortcut tags (`onshortcut.inc:157-179`); while an
edit control has the focus they may arrive as key releases instead
(`eventloadgame.inc:77-90`), which count then. One key arriving both ways
within 0.4 s is taken once; two presses by the same way are two.

## Report view and Details

- **Details** (`dn` = 1, `d0`): one line, `<name> - <status>: <why>`, with what
  Apply will do to the row. `why<i>` is the record's `why<j>` from
  `qm_report`.
- **Report view** (`panel` = 1): the whole window shows `qm_report` `m<k>`, the
  report grouped by mod in load order: per mod the worst tag of its files as
  that mod sees them (OK for a file where all its own changes went in: the
  winner whose copy was written, a mod the written subset keeps -
  ref/report.py mod_status), its
  one-line why, and per file it ships what became of it and where the merge
  touched it (`conflict: <range>: this mod's change lost to <mod>` / `kept
  over <mod>`, `near: ...`). report.txt stays by file, with every detail.
  A clash between enabled mods (two mods shipping the same global script,
  qmGlobals) makes both mods' blocks FAIL, with a line naming the file and
  the other mod (`FAIL scripts\<file>: <mod> ships it too: ...`; qm_boot
  `gcn`, `gca<k>`, `gcb<k>`, `gcf<k>` from qmBoot). Until 2026-10-01 only the
  Boot block said so, and both blocks read OK beside the window's FAIL (run
  look-wsZ).
  Both name a mod `<position+1>. <title> (<Workshop number or dir>)`, or by
  its dir alone when it has no title (ref/report.py `_who`). Until 2026-09-30
  they named it by dir only, which for a Workshop mod is just its folder
  number (`42. ..\..\workshop\content\333420\855916926`) and told a player
  nothing.

## Restart notice (mode 2)

The restart is the vanilla sequence (`onworkshopautoupdate.inc:4-11`), and
the process exit plus Steam's relaunch took about 25-30 s in our runs; nothing
in the scripts can shorten that. Vanilla shows nothing before its own restart
and does not wait a tick. Quartermaster shows a notice instead: a confirmed
Apply switches the window to it at once, and `qmTick` draws it
(`GUIExecuteState('ShowQmManager')` with `mode` = 2) on the first main-menu
frame on which a restart it runs is scheduled - so the boot's own restarts
get it too - and runs the restart on a later frame, at least a tenth of a
second after it (`qm_rt rsnote`). A notice whose restart is gone (the request
withdrawn, the restart dropped) is stale and the window browses again.

## When no frame runs the tick

`qmTick` hangs on a line in DoProgress, and DoProgress is a merged state. The
copy a start loads is the one the last generation wrote; when a mod it was
merged from has been switched off outside Quartermaster since (mods.ini by
the game's own manager, by hand, by unsubscribing), that copy calls a
library that is not loaded and does not compile. *Hands-on, 2026-10-10:*
Reinforced - Core off, the outputs made with it on; the log said `Compile
script error: DoProgress`, the boot (the CameraControl hook, another state)
regenerated and asked for its restart, the restart never came, and the
window answered every Apply with "Still checking the last change; a moment."
for minutes: restart, Apply, the activation check and the settings' save all
waited for a tick that did not run. The next start loaded the new files and
was fine.

- **The heartbeat.** Every run of `qmTick` by a frame leaves its time in
  `qm_rt tkat` (tenths of a second).
- **`qmPump`** runs `qmTick` itself when that time has stood still for a
  second, in the main menu with no boot running (`tkat` 0: no frame ever
  ran it in this start). `ShowQmManager` runs it before a fresh open,
  `EventQmManager` before and after every command, so what the last command
  left for the tick is done before the next is judged and what a command
  asks for right after it. A run too many costs nothing: `qmTick` does what
  is pending and no more. `qm_rt pump` = 1 marks such a run, `pumps` counts
  them; the first says so in the log.
- **A pumped tick** does the work - settings, mod files, the activation
  check, the marker's confirm, an Apply - and leaves out what belongs to a
  frame: the caption, the version and the lobby line (drawn through
  `EventQmManager`, which may be the state running the pump), the notices
  and the run switches, and the restart.
- **The restart** that is pending then runs in `qmPump`, at once: no later
  frame would show the notice or wait out the second after the last write,
  and the minute after which `qmTick` drops a late restart does not count -
  this process runs files older than the ones on the disk. Main menu,
  outside a map and no MP sync, as for `qmTick`. So opening the window in
  such a start restarts the game.
- **A check that still did not run** five seconds after it was asked
  (`qm_rt trat`) is named: the message line says that the game is not
  running Quartermaster's part of the main menu and to start it again.

Not covered: a player who never opens the window in such a start gets no
restart from Quartermaster in it - nothing of Quartermaster's runs without
a frame or a click - and the new files load at the next start. The restart
from the window's states instead of a DoProgress frame is not yet tried in
the game.

## Main menu button

The vanilla button reads "Warsztat modow" (with an o-acute) in the Polish locale (`mods.workshop`,
`showmainmenu.inc:81`; the button `bmodman` at `:141`, made by the local
`ShowButton` at `:16-24`). `qmTick` compares the caption of
`MainMenu.col1.row1.wnewgame.bmodman.txtbtn` (`:85-93`) on every main-menu
frame while the manager's screens are ready, and when ShowMainMenu has drawn
it again, runs `EventQmManager` with `rename` = 1, which sets "Mod Manager"
the vanilla way (`eventprofile.inc:43-67`: width, logic width,
text). No hook file is involved. A caption that does not read back as set
turns the check off (`renameoff`), so it is never set on every frame.

## Version in the main menu (2026-09-30)

Quartermaster's version stands in the main menu's bottom-right corner, one
line under the game's own, the way SW_Frontline_Protocol shows its version
(its `showmainmenu.inc:173` adds a line to the version text before the menu
makes it). Quartermaster ships no `showmainmenu.inc` (its game files are the
hook files, plan S5), so it adds a text of its own, `qmver`, to the frame of
the game's version text `ver`, `MainMenu.col1.row1.wnewgame.ver`
(`showmainmenu.inc:173`; Renaissance, New Terrain Mod and the Unofficial
Patch keep it at that path), and changes no text the menu made. `qmTick`
looks `ver` up on every main-menu frame while the manager's screens are
ready, and when its frame has no `qmver` (the menu made the frame again) runs
`EventQmManager` with `verline` = 1. That puts "Quartermaster 0.1.5" in the
window's head colour `FFDFAF` one line above the stack of texts the menu
keeps there: `ver`, then each visible text of the frame whose y lies less
than two heights above the stack's top (New Terrain Mod's own version, a line
above the game's, `showmainmenu.inc:174-175` of that mod). The text is made
the way the menu makes `ver`: anchored to the frame's right and bottom,
`gc_font_serif_10`. A text that cannot be found again turns the check off
(`veroff`). Evidence: `[qm] ui version line: made, vers=<n> stack=<k> y=<y>
off=<0|1>`.

*Corrected 2026-09-30:* the first version appended the line to `ver` itself
and grew that element to two lines (height and logic height, as
`eventsettings.inc:318-319` grows one), so SW_Frontline_Protocol's layout
held: the game's line one up, Quartermaster's under it. With New Terrain Mod
that pushed the game's line into the mod's own version line (run look-wsD,
2026-09-30): Quartermaster got in the way of another mod's text, so it now
leaves every text as it is and stacks its own above them.

## Named parsers

Keys are lower case (the parser folds and trims keys, probe 4). `<i>` is a row
in `ModLibraryGetData` order (mods.ini order), `<k>` a position, `<j>` a record.

### `qm_ui` - the window's own state (written by the window only)

| Key | Meaning |
|---|---|
| `ready` | 1 while both screen states are in the GUI machine; the EventMainMenu hook opens the window only then |
| `show`, `event` | 1 once that state was added and not known to be lost |
| `showidx` | the index `ShowQmManager` got when it was added; the check reads the name there (a different name, or none: the states are gone) |
| `adds`, `checks` | times the pair was added / confirmed (run evidence) |
| `n`, `self` | rows; Quartermaster's row or -1 (last enabled mod with `data\quartermaster\core.aix`) |
| `dir<i>`, `name<i>`, `org<i>` | dir as the engine lists it; title, else `last`, else dir; origin text (Workshop, Local, Local copy, Other, Quartermaster) |
| `en<i>`, `pe<i>` | 1 = enabled now (engine) / after Apply (pending) |
| `tck<i>` | the activation check's word for a pending activation, `OK` or `WARN` (none: not checked, SKIP, refused); cleared by activate and deactivate, kept over a change of the load order (Apply checks the set in its order again). The status column shows it beside the `+` instead of `PENDING` (since 2026-10-01) |
| `st<i>`, `stsrc<i>`, `why<i>` | status (above); where it came from: `report`, `index`, `none`, '' for an inactive row; the record's short sentence |
| `ord<k>`, `oord<k>`, `order` | the pending load order (every row, Quartermaster last) and the order the game loaded; `qm_mods` when that parser lists exactly these dirs, else `engine` (mods.ini order, Quartermaster last) |
| `ordchg` | 1 while `ord<k>` differs from `oord<k>` (qmUiOrder; 0 at open) |
| `cord<k>`, `hascanon` | the canonical order (every row, Quartermaster last; `qm_mods` `cord<k>`, copied at open), what Auto-sort gives; 1 when it is known (above) |
| `ocmd`, `omoved` | the order command for qmUiOrder (up, down, move); 1 when it moved the row |
| `chg`, `canapply` | rows whose activation is pending; 1 while Apply is enabled |
| `hasreport` | 1 when `qm_report` exists |
| `sel`, `side`, `panel`, `mode`, `msg` | selection, its list, 0 lists / 1 Report view, 0 browse / 1 confirm / 2 restart notice / 3 the guard's notice, message line |
| `gl<i>`, `gdoff<i>` | the row's global scripts (`|`-joined, `qmGlobFiles`; `|` for Quartermaster and its copies); 1 when the start-up guard switched the row off at this start (see *Global scripts* below) |
| `pcn`, `pc<k>`, `pcl<i>` | clashes of the pending set (qmUiAct, after every command): how many, one line each (at most 14; the message line shows `pc0`), and the row's clash for its Details line |
| `confblk`, `confb<k>` | what the confirm dialog shows instead of the question - an about.cfg FAIL of the pending set or one the activation check refused (a global-script clash until 0.1.3); its Apply is disabled and `confirm` refuses |
| `gdopen`, `gdln`, `gdl<k>`, `gdwhy` | set by qmTick to open the window with the guard's notice; its lines (at most 14); the guard's rule (qm_glob `gdwhy`), which picks the notice's text: a clash, or `failed-*` - mods switched off after a start that stopped |
| `filter`, `typed` | the filter in effect; the filter box's text at the last command (the command carries its box's text, in the New mod dialog the name box's, so closing the dialog - Create, Cancel - and Back from Mod files set it back to the filter) |
| `topi`, `topa` | scroll positions of the two lists |
| `confchg`, `confn`, `conf<k>` | activation changes in the confirm dialog; its left column (`+ name`, `- name`, at most 14, the last one `... and N more`) |
| `confon`, `confo<k>`, `confordchg` | its right column: the load order Apply leaves (`1. name`, always shown, at most 14), and whether it changed (head `Load order (changed):`) |
| `lobby`, `lobbycustom`, `lobbies`, `lobbyoff` | the multiplayer lobby line: qmTick sets `lobby` = 1 and `lobbycustom` (custom load order) when the lobby window has no `qmlobby` text yet; EventQmManager draws it and counts `lobbies`; `lobbyoff` = 1 stops it for the process if the text cannot be found after it was made |
| `dn`, `d<k>` | the Details line (`dn` = 1, `d0`) |
| `cmd`, `arg`, `argside`, `argto`, `argtext`, `close` | the command channel above |
| `keycmd`, `keyvia`, `keyt` | the last Esc / Enter, the way it came (shortcut, key) and when, for taking one key once |
| `ping`, `pong` | the fresh-open check that `EventQmManager` runs |
| `rename`, `renames`, `renameoff` | set by qmTick for the button caption; captions set; 1 when the caption did not read back |
| `verline`, `vers`, `veroff` | set by qmTick for the version line in the main menu; texts made; 1 when the text could not be found again |
| `cmds`, `opens`, `closes`, `applies` | counters (run evidence) |

`qm_ui_src` is a scratch parser the ensure loads each screen file into.

### `qm_rt` - Apply's intent (written by `qmUiApply`, read by the boot)

`qm_rt` is created by the boot hook once per process (CameraControl, or the
InitMinimap / DoProgress fallback when CameraControl's hook did not run); the
window never creates it (its absence means "boot has not run"). The window
reads `qmdir` (Quartermaster's folder, recorded by the boot) and `rs` (a
restart is scheduled, for the notice), and writes:

| Key | Meaning |
|---|---|
| `uiapply` | 1 = a confirmed Apply waits; the consumer sets 0 when it has acted |
| `uiapplyseq` | incremented per confirmed Apply |
| `uiapplyn` | rows in the vectors below (= `qm_ui` `n`) |
| `uiapplydir<i>` | the row's dir, exactly as `ModLibraryGetData` returns it |
| `uiapplydis<i>` | the wanted `dis` flag: 1 = off, 0 = on (the whole vector, not only the changes) |
| `uiapplychg` | rows whose flag differs from the engine's |
| `uiapplyordn`, `uiapplyord<k>` | the pending load order, every row, as dirs (written with every Apply) |
| `uiapplyorder` | 1 when the player changed the order (`qm_ui` `ordchg`) |
| `uiregen` | 1 = the player asked for a regeneration |
| `setsave`, `setsaveseq` | 1 = accepted options wait to be written: qmTick saves `qm_settings` into `<save>\quartermaster\settings.cfg` on the next main-menu frame and sets 0; the count of Accepts |
| `hsnext`, `hssent`, `hslast`, `hsdry`, `hsdrop`; `hssig`, `hostin`, `hostn`, `hsparser` | settings of `host` scope in a LAN room (docs/authoring.md): the host's next send (tenths of a second), sends so far, the last set sent, 1 = build the message and do not send it (SelfTest), how many values did not fit into the message (at most 256; qmHostSend, run by qmTick); a client's last set taken, 1 while the host's values are in qm_settings, how many were taken, a parser to read instead of the one the engine hands over (SelfTest; qmHostRecv, run by the OnLanEvent hook). The message is the parser `qm_hostout`: `n`, `m<k>` (mod id), `s<k>` (setting id), `v<k>`, `sig`, number 7301. What a session replaced is in the parser `qm_hostown`: `n`, `m<k>`, `s<k>`, `o<k>` (this machine's own value), `t<k>` (the host's in effect); qmSetSave writes the own values into settings.cfg, and qmTick clears it when the session is over |
| `trq`, `trrow`, `trsig`, `trat` | the activation check asked (see *Activation check* below): the request count, the row just activated or -1 for Apply's, the pending set it is for (`qmUaSig`); `trdone`, the last request qmTick ran - `open` sets it to `trq`, so a request an earlier window left is never answered into a new one |

qmTick keeps `rsnote` there: the tenth of a second the restart notice was drawn;
`trat` is the tenth of a second the activation check was asked. `tkat`, `pump`
and `pumps` are the tick's heartbeat and qmPump's marks (see *When no frame
runs the tick*).

The consumer rewrites `mods.ini` only if its content differs (plan S8),
regenerates, and restarts the vanilla way. It is `qmTick`
(src/states/qmrestarttick.pas), run by the DoProgress hook on every
main-menu frame: it sets `uiapply` to 0 and runs `qmBoot` with qm_rt
`runmode` = apply - the load order with these flags (qmOrder: `uiapplyord<k>`
only when `uiapplyorder` = 1 and it lists every registered dir exactly once,
folded; Quartermaster forced last; it also writes chosen.cfg, see *Global
scripts and the start-up guard* below), a generation for them, all new mods
acknowledged (qmKnown) and a restart of kind `apply`, which only an MP mod
sync or a SelfTest run holds (ref/boot.py). A test's request withdrawn in the
same state that made it is never seen.

### `qm_report` - status and report seam (read only; the report fills it)

| Key | Meaning |
|---|---|
| `n` | per-mod records, one per enabled mod in load order |
| `dir<j>`, `st<j>` | the mod's dir; its status: `OK`, `WARN`, `FAIL` or `NEW` (plain text, drawn in the vanilla colour tags; no glyphs) |
| `why<j>` | one short sentence on how it loads: no merged file, all fine, or how many files need a look and the first of them (the Details line) |
| `cn<j>`, `c<j>_<k>` | its last classification lines |
| `cpd<j>` | the conflict report's sentence on it, without the full stop: `Left out of <file>`, `Loses <n> conflicts to <mod>` or `Wins <n> conflicts over <mod>`; empty without one (`qmUiModel` copies it to `qm_ui` `cpd<i>`, the Details line ends with it) |
| `lines`, `l<k>` | the report by file (report.txt) |
| `mlines`, `m<k>` | the report by mod (the Report view); with a pair of mods that share a record, it opens with `Conflicts between mods (...)` and the pair lines |

### `qm_conf` - the conflict report (qmConflicts; ref/conflicts.py owns the rules and the layout)

`qmReport` runs `qmConflicts` first (and logs `report conflicts ms=`). It writes
`<save>\quartermaster\conflicts.txt` (or the SelfTest sandbox's work folder) line by
line through the raw writer and leaves:

| Key | Meaning |
|---|---|
| `wn`, `w<k>` | the pair lines the Report view shows: at most 14, then `... and <n> more pairs: see conflicts.txt` |
| `d<position>` | a mod's Details sentence (`qm_report` `cpd<j>`) |
| `rn`, `rp<q>`, `rs<q>`, `re<q>`; `rpl<q>`, `rat<q>` | a record's ask for its place in the code and its vanilla line (file, vanilla range), and `qmConflictsCode`'s answer; that state holds the 65536-line read pool and runs once, only when a record asks - in `qmConflicts` itself the pool cost 926 ms on every generation (run cr-t1-133722) |
| `pn`, `p<k>`, `n<section>`, `<section><k>`, `q<section><k>`, `k<section><k>`, `x...`, `dl<position>` | its own working keys: every pair line, the section lines of conflicts.txt (and which answer a line ends with), the counters |

The records describe the file actually written: conflicts, files written
without a mod, changes close together (both in the written file), whole files
(one copy used) and core scripts two enabled mods ship (the boot's clashes,
`qm_boot` `gc<k>`). Mods are numbered by their place on the Active list.

Who fills it, every boot: after a generation `qmReport` (src/states/qmreport.pas),
which also saves it as `<save>\quartermaster\report.cfg`; on a boot that
generates nothing `qmReportLoad` reads that file back (src/lib/qmrepcfg.pas
keeps the lines' leading spaces through the engine's parser; ref/report.py owns
the format). A disabled mod has no record. A row's "new" mark is `st<i>` =
`NEW`; the window infers nothing. `NEW` comes from the boot's list of new mods
(known.cfg, plan S13): `qmReport` marks a new mod whose files are all OK, and
the boot lays the same marks over the loaded report when it does not generate.

### Read from the boot (read only)

- `qm_mods` (qmModList, then qmOrder): `n`, `dir<i>`, `ord<k>` for the **load
  order** the running game uses and the next start will use - the saved
  manual order, mods it has not seen after the saved ones and before
  Quartermaster in mods.ini's order, removed ones dropped, Quartermaster last;
  with no saved order mods.ini's own order, Quartermaster last - and
  `pos<i>` for a row's place in it; `cord<k>` / `cpos<i>` keep the canonical
  order (the window copies `cord<k>` for Auto-sort).
- `qm_index` (qmIndexBegin / qmIndexStep): `n`, `p<k>` (path), `v<k>`
  (providers as `;`-joined load positions, `-` for none) for the files a mod
  provides. Only enabled mods are scanned.
- `qm_order` (the boot, not read by the window yet): `src` (ini - no saved
  order, mods.ini's own; saved; apply), `canon` (1 = the enabled mods' load
  order is their canonical order), `ext` (1 = mods.ini was reordered outside
  and put back), `unseen` + `u<j>`, `dropped` + `d<j>`, `file`, `why`. The
  report's Boot block says when the load order is not the canonical one (an
  MP game needs the same order); the window no longer does (the footer went
  with the default order of 2026-09-30, above).

## Global scripts and the start-up guard (plan S17)

A mod's global scripts are its `data\scripts\lib\*.script` and
`data\scripts\dmscript.global` / `dmscript.source`; two enabled mods that ship
the same one cannot both load (twin: `ref/guard.py`, which has the rules).

- **The boot** (`qmGlobals`, after `qmKnown`) lists them for every registered
  mod into `qm_glob` and reports every clash between enabled mods as a WARN
  line of the Boot block (a FAIL until 0.1.3). It reads the guard's note
  `<save>\quartermaster\guard.cfg` (written by `src/guard/resource.pas`
  before the restart it makes): a note not yet shown (`shown` <> 1) gives one
  WARN line per mod the guard switched off, and `qm_rt` `gdshow` = 1 (with
  `tick`); the boot saves it back with `restarted` = 0 (the guard's loop test
  is disarmed once the restarted start boots), and qmTick with `shown` = 1
  when the notice is on the screen - a first generation's own restart may
  come in between. It also records the enabled mods of the start in
  `<save>\quartermaster\compiled.cfg` (`d<k>`, `n`; ref/guard.py
  `compiled_values`) when they differ from the file, never on an Apply or in
  a multiplayer sync: the set the guard steps back to after a start that
  stopped at "Error compiling scripts" (plan S17). Then it sets `pending` = 0
  in the guard's record `<save>\quartermaster\compile.cfg`: a record still
  pending at the next start is one part of the guard's proof that the start
  before never booted (with the same mods enabled and a mark in that start's
  log, plan S17; it was one half until the set test of 2026-10-03). The Boot line ends
  `compiled=<n> written|same|not-saved|- pending=cleared|not-saved|-`. On
  the same boots (never on an Apply or in a multiplayer sync) it clears the
  window's choice `<save>\quartermaster\chosen.cfg` (*The Apply's choice*,
  below) to `n` = 0 when it lists mods: the guard has trusted that set at
  this start, which booted, so compiled.cfg holds it from now on. A line of
  its own says so, `[qm] globals chosen=cleared|not-saved`; with nothing to
  clear there is no line.
- **Run switches** (a test run's seeded `<save>\quartermaster\`, no player has
  them): `qm_show_ui.flag` opens the window on the first main-menu frame
  (`qm_rt` `uishow`); `qm_skirmish.flag` walks the game into a skirmish on a
  stable start (`qm_rt` `skphase`, `skt`: ShowCustomGame, then DoNewGame, as
  the SW_Frontline_Protocol autotest does) - log lines `[qm] run: ...`.
- **The window**: `qmUiModel` marks an enabled row that clashes WARN when
  it reads OK, NEW or ? (`stsrc<i>` = `globals`, `why<i>` names the file and
  the other mod; since 0.1.4 an add-on and the mod its about.cfg `extends`
  are no clash here, in `qmUiAct`'s pending check or in the boot's lines -
  `qmGlobRelated`) and a row the guard switched off (`gdoff<i>`, its Details line
  says why). After every command `qmUiAct` checks the pending set; a clash
  shows on the message line (orange, after an about.cfg FAIL), in the row's
  Details line (`pcl<i>`), and as a `Note:` line of the confirm dialog, which
  still asks. *Revised 2026-10-03 (0.1.3):* until then a clash row read FAIL,
  the line was red and the dialog listed the clashes with Apply disabled
  (`confblk`); two mods that ship the same file may still run together, and
  the start-up guard undoes a start that stops (plan S17). The message line
  wraps to the window's width and takes its colour (red for an about.cfg
  FAIL, orange for a clash or a WARN) as the text's colour rather than a
  `%color()%` code in it. Until 2026-10-01 it was one centred line with the code in front, and a
  clash naming two long mod titles ran past both edges of the window (run
  look-wsX).
- **The Apply's choice** (*added 2026-10-03, 0.1.3*): the start-up guard
  switches off, before the compile, an enabled mod outside the last set that
  booted when another enabled mod ships one of its global scripts (the rule
  is in plan S17), but two such mods may run together (an add-on built on
  another mod ships that mod's libraries). Activating them here is the
  player's way out: the Apply boot (qmTick runs qmBoot with `runmode` =
  apply) writes `<save>\quartermaster\chosen.cfg` in qmOrder, right after
  qmModsIni and only when `qm_ini` action is `written` or `same` (mods.ini
  then holds exactly the applied rows): `d<k>` the dir of every mod the
  applied mods.ini enables, Quartermaster too, in the new load order, and
  `n` - compiled.cfg's layout. The guard trusts those mods at the next
  start; that start's boot clears the file (above), and when the start stops
  instead, the guard clears it itself and steps back. The window itself still
  writes nothing to disk. Log: `[qm] ui apply chosen=written|not-saved
  n=<n>`, or `[qm] ui apply chosen=- mods.ini=<action>` when mods.ini was
  refused or not written.
- **The notice** (mode 3): qmTick opens the window once, on the first
  main-menu frame outside a map after a guard restart (`gdshow` -> `qm_ui`
  `gdopen`); `open` then sets mode 3 with the lines `gdl<k>`; OK (tag 112),
  Enter or Esc send `ok` and the window is browsed as usual. While mode 3
  lasts, a main-menu frame whose window (`QmManager`) is gone or hidden draws
  the notice again (`gdagain` counts it), and `open` - the main menu button
  too - shows it again instead of being ignored. The game's second start-up
  DoCreate rebuilds the GUI: in run look-wsH (2026-09-30) it took the window
  right after it had opened, and the manager then ignored every `open`; in
  run look-gdfix2 (2026-10-01) the same race drew the notice again.
  Its text follows `gdwhy`. For `conflict` the heading is "Quartermaster
  switched off clashing mods", the body "Each of them replaces a core script
  that another active mod replaces too, and they have not started together
  before. With both, the game may stop at "Error compiling scripts", so
  Quartermaster switched these mods off and restarted the game:", then the
  list, and the last line "If they do work together, activate them here:
  Quartermaster lets them start once and switches back if the game does not
  start." For `failed-*` it says the last start did not reach the main menu
  (it stopped at "Error compiling scripts", or the menu did not compile) and
  lists the mods switched off; the report's Boot lines and the rows' Details
  lines (`gdwhy` in qm_glob) say the same of a step, by name or without a
  clash. *Revised 2026-10-03 (0.1.3):*
  until then the conflict body said the game *would* stop, and the last line
  told the player to deactivate the other mod to use one of them - written
  when only a new subscription was judged. A mod switched on in modman may
  run with the other one, so the text says *may* and points to the way out
  (*The Apply's choice*, above).

### `qm_glob` - global scripts (written by `qmGlobals`, read by the boot and the window)

| key | meaning |
|---|---|
| `n` | registered mods (at most 256) |
| `dir<i>`, `tit<i>`, `on<i>` | the engine's dir, the title shown, 1 enabled (Quartermaster and its copies 0) |
| `gl<i>` | the global scripts, `|`-joined |
| `cn`, `ca<k>`, `cb<k>`, `cf<k>` | clashes between enabled mods (a before b), the first file of a's list that b ships too; at most 64 |
| `gdn`, `gdnew` | the guard note's mods; 1 when the note was fresh at this boot |
| `gdd<k>`, `gdt<k>`, `gdf<k>`, `gdo<k>` | dir and title of a mod the guard switched off, the file, the title of the mod that ships it already (file and other mod empty: a step after a start that stopped, plan S17) |
| `gdwhy` | the guard note's rule: `conflict`, `failed-names`, `failed-revert`, `failed-vanilla`, `order`; empty for a note before 0.1.3 |
| `gdmoved`, `gdlate`, `gdlatef` | 1 when the guard moved Quartermaster to the end of mods.ini at this start (an enabled mod after it shipped one of its hook files), that mod's dir and the hook file; the Boot block says so in one OK line |

`qm_rt` `gdshow`: 1 from the boot until qmTick has opened the notice.

## about.cfg in the window (plan G15b, M8)

A mod may say in its about.cfg what it needs and what it cannot share
(docs/authoring.md; grammar and twin ref/about.py). The boot reads every
registered mod's file into `qm_about` (qmAbout) and checks the set it loads
(qmAbRules); the window checks the set the player is putting together.

- **The model** (qmUiModel): `abok` = 1 when `qm_about` lists exactly the
  window's rows (matched by `dir<i>`); then `abs<i>` is the row's number of
  settings and `abid<i>` the id they are kept under. A loaded row that breaks
  a rule of the loaded set, or whose about.cfg has a FAIL value, is FAIL
  (`stsrc<i>` = `about`, `why<i>` the problem); an OK or NEW row with a WARN
  is WARN. A FAIL of about.cfg wins over a global-script clash's WARN.
- **After every command** (qmUiAct): the rules of the pending set - `pe<i>`
  in the pending order `ord<k>` - into `pan` problems, `pa<k>` the text and
  `pat<k>` the tag of each (at most 14; the message line shows the first
  FAIL, else `pa0`), `pafail` how many are FAIL, `pal<i>` a row's first one
  for its Details line.
- **Activate** is refused when the activated row would break a rule: a FAIL
  of `qm_abr` with the row as `row` or `oth` (a requirement that is not
  active, a second total conversion, a taken exclusive slot, an incompatible
  mod). The message says which.
- **Apply**: every FAIL of the pending set goes into the confirm dialog's
  refused list (`confblk`, `confb<k>`; `confbrule` = 1 when rule lines are
  among them, for the dialog's note), and confirm refuses; a WARN - and,
  since 0.1.3, a global-script clash - goes into the dialog's Changes column
  as a `Note:` line and does not stop it.
- **Auto-sort** (`autosort`): the pending order becomes `cord<k>`, the
  canonical order v2 (qmModList: Kahn's sort of the about.cfg constraints
  over Workshop id / folder name, Quartermaster last).

### Activation check (plan G15b, M8 task 4)

A mod the rules let in is checked with the mods it would join before the
window keeps it: qmTrial (src/states/qmtrial.pas) runs index, plan and a
whole generation for the pending set into `<save>\quartermaster\trial\`
(qmWrOpen `*trial`; nothing goes into a mod folder), and puts the boot's own
parsers back afterwards (ParserCopyFromByHandle, the way vanilla keeps its
record manager aside, initmapgen.inc:70-71 and :248-250).

- **Activate** (after the rules): `pe<i>` = 1 at once, `trpend` = 1 and a
  request in `qm_rt` (`trq`, `trrow` = the row, `trsig`); the message line
  says it is checking. qmTick runs qmTrial on the next main-menu frame, then
  qmUiAct `trialdone`: a FAIL puts the row back (`pe<i>` = 0, "Not activated:
  <the first FAIL>"), a WARN keeps it with a note, SKIP (the window's rows
  are not the boot's) keeps it unchecked. OK and WARN stay as the row's
  `tck<i>`: its status column says `+ OK` / `+ WARN` until Apply instead of
  `+ PENDING`. A later activation's check runs with it in the set, so a clash
  with it refuses the later one; a new load order keeps the words, since Apply
  checks the whole set in that order again.
- **Apply** with rows it switches on: checked together first (`trrow` = -1,
  `trapply` = 1; `trialdone` runs Apply again), unless the last check was
  that one for this very set (`trsig`). Its FAIL lines join the dialog's
  refused list (`confb<k>`, `confbrule` = 1), its WARN lines are `Note:`
  lines.
- **While a check is asked** (`trpend` = 1) activate, deactivate, the moves,
  Auto-sort, Apply and confirm wait with a message; in the game the answer
  comes on the next frame.
- **What qmTrial counts**, for the rows it is about: a FAIL or FATAL
  decision of the generation they take part in (the merged file does not
  compile, a data merge refused) - but a merged or hooked file that does
  not compile is a LATER line when such a row brings its own global scripts: the
  file may call them, and the running game has not loaded them. *Until
  0.1.4 that was a FAIL, and a mod like that could not be activated again
  once it was off (hands-on, 2026-10-10: Reinforced - Core refused twice,
  "gui\menu.inc\doprogress.inc: the merged file does not compile").* The
  Apply that follows meets the same miss, writes the file's fallback and
  records its age as 0 in state.cfg (qmGuard; ref/boot.py `recorded_age`),
  so the next start - with the new set's scripts loaded - finds it changed,
  builds it again (`why=damaged`, qm_guard `recheck` = 1, its own report
  line) and restarts once more if the file came out different; that
  start's generation records the real age, so this happens once. Their
  own .inc files the game would load
  as they are (the plan's skip and winner decisions they win, plus
  `gui\menu.inc\docreate.inc` and `scripts\common.inc\initmap.inc`) through
  qmValFiles - for a mod that brings its own global scripts, which those
  files may need, a file that does not compile is no FAIL but a LATER line
  (below); a `gui\menu.aix` that does not load
  as a parser; and the mod's own check, `data\quartermaster\validate.aix`
  (docs/authoring.md). The rows' global scripts (`scripts\lib\*.script`)
  are compiled one by one against the ones loaded now (qmValFiles `vs`), a
  WARN when one does not - it may need the mod's own others;
  `classes.script` is not compiled at all, a class the game has declared
  cannot be declared again in a state (context section 3), so it gets a
  WARN that says so. Clashes between global scripts stay the start-up
  guard's (plan S17). At most 512 own files are validated in one check; a
  WARN says how many more were not.
- **Key settings**: a key a key setting of the rows holds (stored, else the
  default) that another key setting of the same mod, or one of another mod
  active after the change, holds too is a WARN; so is a key the game holds
  against it by the Options view's own rules (`src/lib/qmkeys.pas`, the same
  code: a key the game does not let a hotkey use, a player's hotkey but an
  `event` one, a shortcut registered by its literal name) - except the
  setting's own default, which the Options view allows too. The player can
  change it in Options.
- **Clean-up**: the validation copies the check made (`<seq>.inc`,
  `<seq>.aix` in `trial\work\val\`, the qm_val numbers from its start to its
  end) are deleted when it ends; the files named by decision are written
  over by the next check.
- **Keys of `qm_ui`**: `trpend`, `trapply`, and the answer `trst` (OK, WARN,
  FAIL, SKIP), `trn`, `tr<k>`, `trt<k>` (at most 16, FAIL first: `tr0` is
  the one the message line shows), `trrow`,
  `trsig`, `trlater` (LATER lines: what only a start with the row's own
  global scripts loaded can judge - its files, a merge it is in, the
  scripts themselves, classes.script - logged, counted, and no part of
  `trst`; the message of an OK check says how many. *Until 0.1.4 each was
  a WARN: Reinforced - Core, which is fine, showed WARN with 24 of them
  and OK after the restart, hands-on 2026-10-10.* The next start judges
  them: the boot's generation, and the start-up guard when a start stops),
  `trfiles` (own files validated), `trvals` (validation copies
  deleted), `trms`.

### The rules seam

| Parser | Keys |
|---|---|
| `qm_abin` (written by the caller) | `n`, `on<i>` (1 active), `ord<k>` (every row in load order); `n` = 0 skips the check |
| `qm_abr` (written by qmAbRules) | `n` (at most 64), `row<k>`, `tag<k>` (FAIL / WARN), `code<k>`, `text<k>`, `oth<k>` (the other row or -1), `fail` |
| `qm_about` (written by qmAbout, read here) | `n`, `dir<i>`, `id<i>`, `nm<i>` (the names a row answers to, `|a|b|`), `pn<i>` with `pt<i>_<k>` / `px<i>_<k>` (the file's problems), `sn<i>` with per setting `sid<i>_<k>`, `sty<i>_<k>`, `sdf<i>_<k>`, `slb<i>_<k>`, `ssc<i>_<k>`, `slo<i>_<k>`, `shi<i>_<k>`, `sst<i>_<k>`, `sdc<i>_<k>`, `sop<i>_<k>`, `smx<i>_<k>`; the full list is in src/states/qmabout.pas |

## Options view (plan G16, M10)

The settings a mod declares in its about.cfg (`setting = id;type;default;
label[;extra][;scope]`, docs/authoring.md), edited in the manager window and
read by the mod from the named parser `qm_settings` (one child per mod id,
one value per setting id; loaded at every boot by qmSettings from
`<save>\quartermaster\settings.cfg`, defaults filled in). Options (tag 118)
is enabled for a selected row with `abs<i>` > 0.

- **The view** (`panel` = 2) replaces the lists, ten settings a page
  (`optpg`; Previous / Next when there are more): label, the edited value -
  green while it differs from the stored one - and the buttons of its type
  (below). A label that does not fit its column takes a second line: broken
  at the last space that fits, and what the second line cannot hold is cut
  with `...` (qmSmLabel, measured in the font it is drawn in; until 0.1.4 a
  label had one line, measured in a smaller font than it was drawn in, so a
  long one lost its end at the value column without a `...` - hands-on,
  2026-10-10). What a cut label leaves out is in a hint over it (`olh<k>`:
  a blank image with a hint and no event state, as vanilla hangs a hint on
  an icon, showaiassistantadvices.inc:309; the whole label, wrapped at the
  label's width, in the style of showaiassistantsettings.inc:98). The rows
  are 48 apart for the second line. The buttons:
  bool Switch; int and float `-` / `+` by the declared step within the range
  (fixed-point: the value always has the declared places, src/lib/qmnum.pas);
  choice `<` / `>`; key Change; text Edit, which shows a text box in the
  value column (`obox` > `otext`, a layer of its own updated in place like
  the filter box). At the bottom Accept, Cancel, Defaults and Close.
- **Key capture**: Change sets `optcap`; the key's down event reaches
  EventQmManager (the window's key state), which names it the way vanilla's
  hotkey window does (hotkeysettings.inc:227-253: GetKeyNameByCode, a name
  longer than two characters ignored unless it is Escape, `Ctrl+` / `Shift+`
  / `Alt+` in front) and sends `optkey`; Escape keeps the old key. The
  keystroke's own release or Esc / Enter shortcut within 0.4 s is not taken
  again (`capend`).
- **A key is refused** (qmUiAct qmUaKeyCheck), with the reason on the
  message line, when the game refuses it for a hotkey (the lists of
  hotkeysettings.inc:24-133, compared as IsValidKey does), another key
  setting of this mod has it, a key setting of another mod that is active
  after Apply has it, the effective hotkeys.cfg binds it to an action that is
  not an `event` one - the rule vanilla applies to its `interface` hotkeys,
  hotkeysettings.inc:210-216 (the player's
  `<save>\hotkeys\hotkeys.cfg`, else `.\data\game\var\hotkeys.cfg` - what
  RegisterShortcuts reads, registershortcuts.inc:187-192), or the effective
  registershortcuts.inc registers it by its literal name. The setting's own
  default and stored key are always its own.
- **Accept** (`optacc`): two key settings of the mod on one key refuse the
  save; otherwise the edit copy goes into `qm_settings` at once, `qm_rt`
  `setsave` asks qmTick to write the file (the window writes nothing to
  disk), and when a key changed `rereg` = 1 makes EventQmManager register
  the shortcuts again as vanilla does after its hotkeys are saved
  (eventsettings.inc:727-728: UnregisterGUIAllShortcuts, then
  RegisterShortcuts) - a mod that reads its keys from `qm_settings` in
  RegisterShortcuts has the new key at once (`reregs` counts them).
  `optsaves` counts Accepts.
- **Keys of `qm_ui`**: `opt` (the row), `optmid` (its id in `qm_settings`),
  `optn`, `optpg`, `optcap`, `optsel`, and per setting `<k>`: `oid<k>`,
  `oty<k>`, `olb<k>`, `odf<k>`, `olo<k>`, `ohi<k>`, `ost<k>`, `odc<k>`,
  `oop<k>`, `omx<k>`, `osc<k>` (the declaration, copied from `qm_about`;
  a label of scope `host` says that the host decides it in multiplayer),
  `ovs<k>` (stored) and `ov<k>` (edited).

## Create mod, Mod files (plan G17, M11)

For a mod author without Python or a command line: a new mod folder, a
draft about.cfg for a local mod, and a copy of a game file to edit. The
window writes nothing itself: each asks with a request in `qm_rt` (`mfreq`),
and qmTick runs qmModFiles on the next main-menu frame, whose writer
functions (src/lib/qmwrite.pas qmWrNewMod, qmWrAboutDraft, qmWrCopyVanilla)
make every check - the only writes outside Quartermaster's mirror, and only
into `mods\<name>`, one level, never Quartermaster's own folder. The
outcome is the window's message line (qmTick draws the window again when it
is open). The twin of the files is ref/createmod.py.

- **New mod** (tag 120, mode 4, `newmod`): a dialog with the name box
  (layer `nbox` > `nname`, updated in place like the filter box; its text is
  `nmname`), the folder
  it makes (`nmfolder`: the name with every character outside A-Z a-z 0-9 _
  dropped, a space as `_`, at most 40, a letter first), Type (`nmtype`: mod
  or total conversion) and Slot (`nmexcl`: none or an exclusive slot).
  Create (`nmcreate`; Enter) refuses an empty folder or one a registered mod
  has, else asks `mfreq` = `new` with `mffolder`, `mftitle` (the name as
  typed), `mftype`, `mfexcl`: mods\<folder>\mod.ini (the layout
  local mods have), about.cfg and data\readme.txt. The game registers the
  folder at its next start, and the window lists it as NEW; the engine has no
  call that registers it sooner (docs/research/context-2026-09-27.md
  section 3), so the message line says so: "Created mods\<folder>. It is in
  the list after you restart the game: the game looks for new mod folders
  only when it starts." (decided 2026-10-01). Cancel
  (`nmcancel`; Esc) closes the dialog; while it is open only its commands count.
- **Mod files** (tag 121, panel 3, `modfiles`) of a selected Local or Local
  copy row (`mfrow`): Create about.cfg (`mfabout`, enabled while `mfhas` = 0)
  asks `mfreq` = `about` with `mfdir`, `mftitle`, `mftags` (Overhaul makes it
  a total conversion) and `mfcam` (1 when the mod ships
  gui\menu.inc\oncamera.inc: the camera slot) - never over an existing file.
  The filter box finds game files: its text (`vq`, three characters at
  least) against the paths of Quartermaster's vanilla.idx, at most 100
  matches (`vn`, `v<k>`, `vc<k>` the class: `merge` is merged with other
  mods, anything else is a whole-file override); a list select (`vfiles`,
  `vselect`) picks one (`vsel`), and Copy into mod (`mfcopy`) asks
  `mfreq` = `copy` with `mfdir`, `mfrel`: the pristine game file copied byte
  for byte into the mod under the same path (CopyFileStream, after a stream
  write has made the folders), never over an existing file. Back (`mfback`;
  Esc) returns to the lists.

## Window elements

`ShowQmManager` builds (names are what `EventQmManager` looks up):
`QmManager` (top parent, event state, black mask `blackmask`) > `main` >
`wnd` (the main window; the title in its `head.head`, `showcampaign.inc:318-320`)
> `inst` > `installed`, `act` > `active`, `descr` > `scrolllayer` > `txt`, the
buttons, or in the Report view `rep` > `scrolllayer` > `txt`; in both views
the message line `tmsg`; beside `main`
the layers `fbox` > `filter` (input box, edit control `text`), `confirm`
(mode 1) and `notice` (mode 2). `main`, `confirm` and `notice` are rebuilt on
every run: `_gui_CreateParent` reuses a parent by name and removes its
children first (`data/scripts/lib/gui.script:446-452`). `QmManager` and `fbox`
are updated in place instead, so the filter's edit control survives every
redraw with its caret and focus (`_gui_CreateInputBox` sets the text only
when it changed, `gui.script:1602-1636`). Closing hides the parent; the main
menu under the modal was never hidden, so nothing has to be re-shown.

## Hooks and build

**EventMainMenu** (`src/hooks/eventmainmenu.pas`) - five lines. hbuild places
them at the S5 hook index, 0 for this file, so `dist` holds vanilla's bytes
with those lines in front of the first Code line (tested byte for byte). They
read Tag and Press themselves, and the vanilla lines they run ahead of
(`eventmainmenu.inc:4-27`: event-value reads, constants, a pure name helper, a
remap of tag 100) have no effect an early exit could lose. The button's arm is
`eventmainmenu.inc:154-156`; `108` is `cTagModManager` (`:20`).

**CameraControl** (`src/hooks/cameracontrol.pas`) - its last line runs
`qmUiEnsure` on every DoCreate, after the boot line; the ensure returns at once
outside the main menu. The hook carries no comment line, to stay within ten.

**DoProgress** (`src/hooks/doprogress.pas`) runs `qmTick` on every main-menu
frame; the notice and the button caption need no hook line of their own.

**OnLanEvent** (`src/hooks/onlanevent.pas`) - three lines at hook index 0 (the
state starts with `var cAllowDebug`, not a routine). On a client, when the
engine hands over a received parser (`gLanEvent = leParser`, where vanilla's
ParserReceived reads its own, `onlanevent.inc:176-215`, `:898`) with the
number 7301, they run `qmHostRecv`. The main-menu tick does not poll for the
message: whether the engine still has the parser selected outside this call
is not known, and a poll would see only a frame's last message.

**Screens** - hbuild's `screen` template kind: `src/screens/*.pas` (not
recursively), front matter `screen`, `into`, `helpers`, `requires`; the name
matches `(Show|Event)Qm[A-Za-z0-9]+`, `into` is
`data/quartermaster/ui/<name in lower case>.inc`; assembled and linted like a
one-state `.inc`, and the names join the uniqueness check of state names.

**SelfTest** - case kind `ui` (`src/states/qmcaseui.pas`, twin
`ref.selftest.ui_expected`, tool `tools/m6cases.py`): open/close cycles, then
on one mod: select it in Active, Move up and back (or down and back when it
loads first), type its folder's name into the filter and clear it (key
releases), the Report view and Esc out of it, Deactivate - Apply - Esc - Apply
- Enter (the restart notice) - Esc, all driven by GUI tags and events. Each
step dumps `canapply`, `ordchg`, the panel and whether the Apply button is
enabled; `order`, `filtered` and `unfiltered` lines carry what only the run
knows. The case withdraws its Apply at the end (and the notice with it),
unless it says `keep 1`: then the flow runs once per run, in the first life
whose boot neither generated nor has a restart pending, and the request is
left for `qmTick` - the I9 run through the window (`m6cases.py case --i9`,
`i9check`; twin `ref.selftest.ui_keep_*`).

## v1.2 (hands-on check 2026-09-28)
- Title: `Quartermaster` in both views.
- Status column: a row whose activation Apply will change shows its mark (`+`/`-`)
  in the mark column and `PENDING` in the status column, in both lists,
  until the next generation gives it a real status.
- Confirm dialog: two columns, `Changes:` and `Load order:` (see `conf*` keys).
- Multiplayer lobby: qmTick adds one line (`qmlobby`) to the lobby window
  `InternetShell.backgroundparent.background` (`showinternetshell.inc:682,687,1813`)
  through EventQmManager, once per window: standard or custom load order;
  `[qm] lobby line shown custom=<0|1>`.
- Main menu: Quartermaster's version one line under the game's in the
  bottom-right corner (see "Version in the main menu");
  `[qm] ui version line: made, vers=<n> stack=<k> y=<y> off=<0|1>`.
