# Languages

Quartermaster's own texts, and the texts a mod declares for its settings, in the
sixteen languages of the family. Design decision G19 of [plan.md](plan.md); the
window it fills is described in [ui.md](ui.md), the author's side of about.cfg in
[authoring.md](authoring.md). Status: built and proved offline (the tests of
`tests/test_lang*.py`); not yet seen in the game.

## The languages

| Code | Language | Text encoding on screen |
|---|---|---|
| `en` | English (the fallback of every text) | ASCII |
| `cs` `pl` `hu` | Czech, Polish, Hungarian | code page 1250 |
| `ru` `uk` | Russian, Ukrainian | code page 1251 |
| `tu` | Turkish | code page 1254 |
| `de` `es` `fr` `it` `po` `nl` | German, Spanish, French, Italian, Portuguese (Portugal), Dutch | code page 1252 |
| `zh` `ja` `ko` | Chinese (Simplified), Japanese, Korean | ASCII with `\uXXXX` for every other character |

The codes are the folder names under `data/locale/` of the game and of Core. The
game's eleven come with the game; `hu`, `nl`, `zh`, `ja`, `ko` are added by
Reinforced - Core. Quartermaster works without Core: a language the running game
does not have is simply never selected, and a CJK text reaches a screen only where
Core's wide-text path (`src/gui_wide.pas` in Core) is installed.

The language of the game is the folder name in `GetLocaleTableFileName`
(`.\data\locale\pl\table.lng` is `pl`), read the way Core's decoder reads it
(`qmLang`, src/lib/qmtext.pas).

## Quartermaster's own texts

- **In the code** a text the player sees is written `qmT('English text')`; with
  arguments `qmT('Pending: %1 of %2', a, b)`. The build (`tools/hbuild.py`,
  `expand_texts`) turns it into a lookup in the named parser `qm_text` and adds
  `qmTextLoad;` to the start of every state that has one. The key is `t_` and the
  words of the English text (`t_open_workshop`); a text of more than 34
  characters is cut and ends with a hash of the whole. A change of the English
  changes the key, so a translation of the old text is missing - and the build
  says so - rather than wrong. Two texts that make one key stop the build.
  The English stays in the code and is shipped as `en.cfg` too.
- **Chinese, Japanese and Korean in lists and buttons.** Core's wide-text path
  draws a text that goes through `_gui_CreateText` and the other wrappers of
  `lib/gui.script`. A call a script of ours makes on the engine itself it does not
  reach, so Quartermaster does that work with the same rules (src/lib/qmwide.pas):
  `qmListAdd` puts a text with escapes into a list as a wide item (the list in wide
  mode, the wide font of its bitmap font `w<z|j|k>_<font>`, the cells of a row set
  apart to the columns), `qmSetText` sets a button's own text the same way, and
  `qmRect`, `qmRectF`, `qmWrap`, `qmHead` measure, wrap and cut by characters. In
  any other language, and for any text without an escape, each of them is the
  engine's call. All of it is ported from Core's `src/gui_wide.pas` and proved only
  on the emulated engine.
- **The one text kept English: the main-menu button.** Its caption is read back to
  see whether the menu drew it again, and a wide text reads back empty, so it is
  written `qmTL('Mod Manager')`: the key `l_...` holds the translation in the other
  languages and English in zh, ja and ko.
- **Sources:** `src/text/<code>.cfg`, UTF-8, `key = value`, one line each, sorted
  by key. `src/text/en.cfg` is written from the code by
  `python tools/qmtext.py --write` and the build refuses to run when it is not what the
  code holds. `python tools/qmtext.py --status` says how far each language is,
  `--missing CODE` lists what a language lacks, `--fill CODE FILE` adds the
  translations of FILE (one per line, in that order) to it.
- **Files:** the build writes `data/quartermaster/text/<code>.cfg` from each
  source, in the encoding of the table above, inside the `section.begin` /
  `section.end` the engine's parser needs for a flat list (the same as Core's
  texts), CRLF. `qmTextLoad` loads the file of the game's language once, or
  `en.cfg` when the language has none.
- **Checked** by the build (`ref/lang.py check`) and the tests: every key in every
  language and in the same order; the same placeholders (`%1`..`%9`) and numbers
  as English; every character encodable in the language's code page (or in the
  Basic Multilingual Plane for CJK); no backslash; no text of three words or more
  left in English; the script of the language (Cyrillic, Han, kana, Hangul).
  Words of the game itself come from its own tables of the language, Core's
  glossary is the source for the five languages it adds.
- **Not translated:** the `[qm]` lines of the game log, parser keys, file names,
  the tags `OK` `WARN` `FAIL` `NEW` `PENDING` `LATER`, the problems of about.cfg in
  the report, `report.txt` and `conflicts.txt` (they are compared byte for byte
  with their twin in `ref/`, and a player pastes them into a bug report), the
  files Quartermaster writes for authors (the about.cfg template, the readme of a
  new mod), the engine's own box "Error compiling scripts".
- **CJK and the engine:** the routines that measure a text, wrap it or cut it
  (`qmRect`, `qmRectF`, `qmWrap`, `qmHead`, src/lib/qmwide.pas) count an escape as
  one character and lay a line out with Core's rules; a text without an escape goes
  to the engine as before. Typing in a CJK language is not possible with the
  engine's fields (docs/asian-languages.md in Core): the search boxes take ASCII.

## Texts a mod declares

A mod can say, in its about.cfg, how its own texts read in other languages. The
texts it already declares (`name`, the `group` titles, the label of a `setting`)
are the English ones and the fallback.

```
name = WASD camera
name.pl = Kamera WASD
name.de = WASD-Kamera
group = Camera keys
group.pl = Camera keys;Klawisze kamery
setting = camera_left;key;A;Camera left
label.pl = camera_left;Kamera w lewo
label.de = camera_left;Kamera links
```

| Key | Value | Gives |
|---|---|---|
| `name.<code>` | the text | the mod's name in the window |
| `group.<code>` | `<title as declared>;<text>` | a group's title (every setting under it) |
| `label.<code>` | `<setting id>;<text>` | a setting's label |

- The file is UTF-8 (a byte order mark is allowed), so an author writes `Szybkość`
  as it is. Only the rows of the language of the game are applied. Quartermaster
  turns the text into what that language's screen takes when it reads the file at
  boot (`qmAboutLoc`; the twin is `ref/about.py localise`). A text with a
  character the language cannot show is dropped with a WARN, and the declared
  text stays.
- Every row is checked, whatever the language: an unknown language code, a row
  without its text or its target, and a setting or group the file does not
  declare are each a WARN in file order, `l10n-lang`, `l10n-fields`,
  `l10n-target`; `l10n-chars` is the one that depends on the language. The last
  row for the same thing counts.
- The setting ids, the stored values and `settings.cfg` never change with the
  language, so a player who changes the language keeps every value. The search
  box of Options looks in the label that is shown.
- Not translated: the options of a `choice` setting (their text is also their stored
  value); a `choice.<code>` row is an unknown key for now. A `host` setting's
  suffix and the texts of `requires` problems are Quartermaster's.
- An author who uses these keys says `quartermaster = <version>` of the first
  release that reads them. An older Quartermaster shows one WARN per row ("unknown
  key") and the declared English texts.
- Label length: the label line of the window holds about 60 characters twice
  (authoring.md); a CJK character counts as two.

## What is open

- The pictures of the window in the game in each language, and the fit of every
  text to its button and line: only a run in the game shows it (the owner's yes, no
  other test and no game running).
- Chinese, Japanese and Korean in the lists and buttons: ported from Core, never drawn in the game; the main-menu button stays English there.
- The options of a `choice` setting.
- `report.txt` and `conflicts.txt` in the player's language, if wanted: it needs
  the twin to take the language, and the byte-for-byte tests to run in English.
- A native reader for every language: none is a native speaker of any.
