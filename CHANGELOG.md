# Changes

## 0.1.9 (2026-11-08)

- Quartermaster speaks your language: the manager window, its messages and the button it puts in the main menu follow the language of the game. English, Czech, German, Spanish, French, Italian, Polish, Portuguese, Russian, Turkish and Ukrainian, and with Reinforced - Core also Hungarian, Dutch, Chinese, Japanese and Korean. A text without a translation reads English.
- Not translated: the report (`report.txt`, `conflicts.txt`) and the game log. In Chinese, Japanese and Korean the menu button still reads English.
- For mod authors: `name.<code>`, `group.<code>` and `label.<code>` in about.cfg give your mod's name, group titles and setting labels in other languages (UTF-8). A language you give no row for shows your English text. An older Quartermaster shows a warning for each row and the English texts.

Workshop change note:

> 0.1.9: Quartermaster now follows the language of the game: the window and its messages are translated into 15 languages. For mod authors: name.xx, group.xx and label.xx in about.cfg translate a mod's settings.

## 0.1.8 (2026-10-18)

- Mods that must load after another mod (their about.cfg says so) now do, the first time the game starts. No Auto-sort needed. Only that mod moves. A list you arranged by hand is never touched.
- Example: you add Reinforced - LAN after Reinforced - Core. Before, LAN stayed below Core and Core's lobby was lost. Now Core goes right under LAN.
- If the rules of two mods contradict each other, nothing moves and the report says so.
- For mod authors: `carries = <id>` in about.cfg marks a mod that already holds another mod's changes. If it loads after that mod, the shared files show no warning. An older Quartermaster ignores the line.

Workshop change note:

> 0.1.8: mods that have to load after another mod now land in the right place on their own, no Auto-sort needed. A list you arranged by hand stays as it is. For mod authors: a new about.cfg line, "carries", for a mod that already contains another mod's changes.
