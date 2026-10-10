# Writing a mod for Quartermaster

Quartermaster loads every Cossacks 3 mod as it is; nothing here is required.
A mod that ships an `about.cfg` can also say what it needs and what it cannot
share, and can give the player settings to change in the manager window
without editing a file. This page is the author's side of both; the window
side is in [ui.md](ui.md), the design decisions in [plan.md](plan.md) (G4,
G15b, G16).

The player-facing texts of Quartermaster were placeholders (`TODO` marks in
the sources) until 2026-09-30; they are final for v0.1.

## about.cfg

A text file named `about.cfg` in the mod's folder, next to its `mod.ini`.
Quartermaster reads it at every start (the reader and its twin:
`src/states/qmabout.pas`, `ref/about.py`).

```
# lines starting with # are comments
id = mywasd
name = WASD camera
version = 1.2
type = mod
exclusive = camera
requires = 1325221799; mybase>=2.0
loadAfter = 1255766623
setting = camera_left;key;A;Camera left
```

Line rules: one `key = value` per line; spaces and tabs around the key and the
value do not count; keys are not case-sensitive; an empty line or one whose
first character is `#` is skipped; a UTF-8 byte order mark at the start is
allowed. Lists are separated by `;`. A key given twice keeps its last value,
except the list keys and `setting`, whose values add up.

| Key | Value | If it is wrong |
|---|---|---|
| `id` | the mod's id: `a-z`, `0-9`, `_`, `.`, `-` (case folded) | FAIL |
| `name` | a display name (any text) | - |
| `version` | digits and dots, e.g. `1.2.10` | WARN, ignored |
| `quartermaster` | the oldest Quartermaster version the mod works with | WARN, ignored |
| `gameBuild` | informational | - |
| `type` | `mod`, `totalConversion` or `library` | FAIL |
| `exclusive` | slots the mod takes alone: `camera`, `ai`, `ui`, `balance`, `economy`, `sound`, `graphics`, `hotkeys` | FAIL |
| `extends` | the id of the mod this one is an add-on to | FAIL |
| `requires` | ids, each optionally `>=version` | FAIL |
| `loadAfter`, `loadBefore` | ids | WARN, ignored |
| `incompatibleWith`, `compatibleWith` | ids | WARN, ignored |
| `extraDirs` | folders (read, not used yet) | - |
| `setting` | a setting (below), repeatable, at most 32 | WARN, dropped |

Any other key is a WARN. A FAIL marks the mod FAIL in the window and in the
report.

**Ids.** A mod answers to its declared `id` and also to its folder: the
Workshop item number (`1325221799`) or the local folder name in lower case
(`mods\SW_Frontline_Protocol` is `sw_frontline_protocol`). So a mod can name
a Workshop mod that has no about.cfg by its number. Quartermaster itself is
`quartermaster`.

### What Quartermaster does with it

- **Load order.** `requires`, `extends` and `loadAfter` load the named mod
  first, `loadBefore` loads this one first, in the canonical order that
  Auto-sort gives: Workshop id / folder name, then these rules; Quartermaster
  always loads last. A cycle of rules is broken at the earliest mod another
  one waits for and reported as FAIL. Until the player sets an order,
  Quartermaster keeps the one mods.ini has - what the game loads without it -
  and moves only itself to the end (since 2026-09-30: the canonical order as
  the default changed which mod wins whole files). A load order, set by hand
  or mods.ini's, that breaks a rule is a WARN that names the mod to load
  after the other.
- **Activation.** In the manager window a mod cannot be activated when that
  breaks a rule: a mod it requires is not active (or its version is lower), a
  second total conversion (unless one `extends` the other), a second mod in
  one `exclusive` slot (unless one extends the other or lists it in
  `compatibleWith`), a mod it is `incompatibleWith`. Apply refuses a set that
  breaks one; a WARN is shown in the confirm dialog and does not stop it.
- **The start guard.** A mod that has not started with the others - a new
  subscription, or one switched on in modman - is taken out of the start when
  it ships a global script an enabled mod already ships (a whole-file script
  in `data\scripts\lib\`, `dmscript.global`, `dmscript.source`). An add-on and
  its base are the exception: `extends = <id>` names the base, by its `id` or
  its folder, and the pair may ship the same script. The guard reads only
  `id` and `extends` of about.cfg, before the game's scripts compile, and
  looks one step only: an add-on of an add-on does not excuse a clash with
  the base. The window, the report and the Apply do not call the pair a clash
  either. Keep whole-file scripts in the base all the same: one of the two
  copies replaces the other, and which one is the load order's choice.
- **The activation check.** A mod the rules let in is then tried with the
  mods it would join, in the running game and before any restart: every file
  it would be merged into must compile, its own `.inc` files the game would
  load as they are must compile (with your own global scripts in
  `data\scripts\lib\` this is only a WARN, since the scripts loaded while the
  check runs are not yours), and a `gui\menu.aix` of yours must load. A FAIL
  keeps the mod inactive; the window says why. Your global scripts are
  compiled against the ones loaded while the check runs - only a WARN, for
  the same reason - except `classes.script`, which a running game cannot
  compile at all. A key setting whose key another key setting of your mod
  or of another active mod holds gives a WARN, and so does a key the game
  holds against it by the rules of the Options view below - except your
  setting's own default, which you chose with the game's keys in sight. The
  player can change the key in Options.

### Your own check (optional): data\quartermaster\validate.aix

A mod can bring its own check, run as part of the activation check. It is a
state file (the layout of any `.aix`) with a state named `Validate`,
loaded into a trigger manager of its own; nothing else of your mod runs, and
your global scripts are not loaded. It reads the named parser `qm_modval`:

| Key | Value |
|---|---|
| `dir` | your mod's dir |
| `n` | the mods of the set being checked |
| `dir<k>`, `id<k>`, `on<k>` | each of them in load order: its dir, its about.cfg id (empty without one), 1 when it would be active |

and answers in the same parser: `pn`, then per problem `pt<k>` (`FAIL` or
`WARN`) and `px<k>` (a short sentence), and last `done` = 1. A check that
does not set `done` - it did not compile, or stopped - gives a WARN. A FAIL
keeps your mod inactive with your sentence; a WARN is shown and does not.
For example, refusing to run without another mod:

```
[*] = ;var p : Integer = ParserSelectByKey('qm_modval');
[*] = ;var k : Integer;
[*] = ;var found : Boolean = False;
[*] = ;for k:=0 to ParserGetIntValueByKeyByHandle(p, 'n')-1 do
[*] = ;if (ParserGetValueByKeyByHandle(p, 'id'+IntToStr(k))='mybase') and (ParserGetIntValueByKeyByHandle(p, 'on'+IntToStr(k))=1) then
[*] = ;found := True;
[*] = ;if (not found) then
[*] = ;begin
[*] = ;   ParserSetIntValueByKeyByHandle(p, 'pn', 1);
[*] = ;   ParserSetValueByKeyByHandle(p, 'pt0', 'FAIL');
[*] = ;   ParserSetValueByKeyByHandle(p, 'px0', 'it needs My Base active');
[*] = ;end;
[*] = ;ParserSetIntValueByKeyByHandle(p, 'done', 1);
```

(`requires = mybase` in about.cfg says the same without code; the own check
is for what about.cfg cannot say.)
- **The report** lists what an enabled mod's about.cfg says wrong and every
  rule the enabled set breaks (mods can be switched on outside Quartermaster).

## Settings

A `setting` line declares one setting:

```
setting = <id>;<type>;<default>;<label>[;<extra>][;<scope>]
```

- `id`: `a-z`, `0-9`, `_`; unique in the mod.
- `type` and `extra`:

| Type | Default | Extra | In the window |
|---|---|---|---|
| `bool` | `1` / `0` (also true, yes, on / false, no, off) | - | Switch; stored as `1` / `0` |
| `int` | an integer | `min..max` or `min..max..step` (required) | `-` / `+` by the step |
| `float` | a decimal | `min..max` or `min..max..step` (required) | `-` / `+`; the value always has as many decimals as the longest of the four numbers, e.g. `0.5..2..0.25` gives `1.50` |
| `choice` | one of the options | the options: `slow|fast|off` | `<` / `>` |
| `key` | a key name, e.g. `A`, `F6`, `Ctrl+J` | - | Change, then press the key |
| `text` | a text | the longest length, optional | Edit, then type |

- `label`: what the window shows. *Corrected 2026-09-29:* this line said
  "any text; UTF-8 works", which no run ever showed. The game's own texts
  are single-byte code pages, one per language with a font to match
  (docs/research/context-2026-09-27.md section 3), so plain ASCII is the
  safe choice. Checked in the Polish game the same day: a name in cp1250
  reads right, the same name in UTF-8 shows as its bytes read as cp1250
  ("ZaĹĽĂłĹ‚Ä‡" for "Zażółć"); a label in a player's language is readable
  only in that language's code page. Keep it short: the window gives a label
  two lines of its column, about 60 characters each (65 of an English label
  filled the column in the hands-on check of 2026-10-10), breaks it at a
  space, and cuts what the second line cannot hold with `...`. A `host`
  setting's label gets " (the host decides in multiplayer)" added, which
  counts too.
- `scope`: `local` (the default) or `host`. A `host` setting is the one the
  host decides in a LAN game: while the room is open the host's
  Quartermaster sends its values of every `host` setting of the loaded mods
  about once a second, and each player's Quartermaster puts them into
  `qm_settings` for the session - only for settings its own copy of the mod
  declares with `host` scope, and only a value that fits that declaration
  (a host with another version of your mod may send one that does not; the
  player's own value stays then) - and its own values back once the player
  has left the session. The host's values are never written into the
  player's settings.cfg; a host setting the player changes in Options during
  the session becomes the player's own for after it. At most 256 values go
  in one message; the host's log says when some did not. So your script reads the host's value in the battle,
  as long as it reads it when the battle runs (not only at start-up, before
  the room). Everyone still needs the same mods (the game's own check).
  Not yet tried between two machines. An internet room is a LAN game over
  the game's public server - the internet shell creates one with the same
  `LanCreateGame` (`eventcreatejoinroom.inc:118`, then
  `LanPublicServerUpdateClientInfo` at `:123`) and joins one from the
  server's list with `LanJoinGame` (`eventinternetshell.inc:308`) - so the
  same lines should carry the values there too; that is not tried either.

A key setting is refused, with the reason, when the game does not allow the
key for a hotkey (its own list, `data/gui/menu.inc/hotkeysettings.inc:24-133`),
when the player's hotkeys (`Documents\cossacks\hotkeys\hotkeys.cfg`, else the
game's `hotkeys.cfg`) bind it to any action but an `event` one - the game's
own rule for a key that works everywhere, `hotkeysettings.inc:210-216` - or a shortcut the game registers by name
(`registershortcuts.inc`) already use it, or when another key setting of this
mod or of another active mod has it. The setting's own default is always
allowed.

### Reading a setting

The values live in the named parser `qm_settings`: one child per mod, named by
the mod's id (the declared `id`, else its Workshop number or folder name), and
in it one value per setting id. The parser survives a map load, and
Quartermaster fills in the default of every declared setting at each start.
The same values are saved in `Documents\cossacks\quartermaster\settings.cfg`
when the player accepts the Options view. Read them with a fallback, so the
mod still works without Quartermaster:

```pascal
var myKeyLeft : String = 'A';
var mySet : Integer = ParserSelectByKey('qm_settings');
if (mySet=0) and (FileAge(GetAppSaveDirectoryPath+'quartermaster\settings.cfg')<>-1) then
begin
   // RegisterShortcuts can run before Quartermaster's start-up: load the file.
   mySet := ParserCreate('qm_settings');
   ParserLoadFromFileByHandle(mySet, GetAppSaveDirectoryPath+'quartermaster\settings.cfg');
end;
var myMod : Integer = 0;
if (mySet<>0) then
myMod := ParserSelectByHandleByKey(mySet, 'mywasd');
if (myMod<>0) then
if (ParserGetValueByKeyByHandle(myMod, 'camera_left')<>'') then
myKeyLeft := ParserGetValueByKeyByHandle(myMod, 'camera_left');
```

Every value is a string: a bool is `1` or `0`, a number its text
(`StrToInt`, `StrToFloat`). The engine's parser drops a value's leading and
trailing spaces.

**When a change reaches the mod.** At once for everything that reads
`qm_settings` when it runs (a per-frame check, `IsKeyDownByName`). A key the
mod registers in `RegisterShortcuts` changes at once too: after the player
accepts new keys, Quartermaster registers the shortcuts again the way the
game does after its own hotkey window (`UnregisterGUIAllShortcuts`, then
`RegisterShortcuts`, `eventsettings.inc:727-728`). A value read only once at
start-up changes at the next start.

The test mod QMTestWASD2 (`tools/fixtures.py`) is a complete example: its
four camera keys are settings, read in `registershortcuts.inc` and
`oncamera.inc`.

### Quartermaster's own list

For a Workshop mod that ships no about.cfg, Quartermaster reads its own entry
instead, when it has one: `data\quartermaster\known\<Workshop number>.cfg` in
Quartermaster's folder (the sources: `src/known/`), in the same format and
with the same rules. A mod's own about.cfg always wins over the entry. An
entry holds only what was checked on the installed mods, and says why in its
comments:

| Mods | Entry | Why |
|---|---|---|
| New Terrain, The Great Cossacks 6, 19th Century, AI Extension, Realism, State vs Country, State vs Country++, Rise of America, Renaissance | `type = totalConversion` | each replaces core scripts that declare classes (classes, country or player), which cannot be merged: two of them do not go together |
| Sound Enhanced | `incompatibleWith` Renaissance, Rise of America, State vs Country++, Realism | each of them replaces sound.script, which declares classes |
| MGraphics - Main Menu | `incompatibleWith` Renaissance | tested in game 2026-09-30: its menu textures load into Renaissance's menu layout, the logo cut off |

An author who ships an about.cfg takes the entry's place with their own.

## Limits

- The rules only see mods that declare them, or that Quartermaster's own list
  covers; none of the 22 popular Workshop mods checked on 2026-09-28 ships an
  about.cfg.
- A key setting is a key name; `IsKeyDownByName` reads a single key, so a
  combination such as `Ctrl+J` only works where the mod registers it as a
  shortcut.
- Settings of `local` scope are per machine: in multiplayer every player
  keeps their own. Only `host` settings follow the host (above).
