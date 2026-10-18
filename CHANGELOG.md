# Changes

## 0.1.8 (2026-10-18)

- Mods that must load after another mod (their about.cfg says so) now do, the first time the game starts. No Auto-sort needed. Only that mod moves. A list you arranged by hand is never touched.
- Example: you add Reinforced - LAN after Reinforced - Core. Before, LAN stayed below Core and Core's lobby was lost. Now Core goes right under LAN.
- If the rules of two mods contradict each other, nothing moves and the report says so.
- For mod authors: `carries = <id>` in about.cfg marks a mod that already holds another mod's changes. If it loads after that mod, the shared files show no warning. An older Quartermaster ignores the line.

Workshop change note:

> 0.1.8: mods that have to load after another mod now land in the right place on their own, no Auto-sort needed. A list you arranged by hand stays as it is. For mod authors: a new about.cfg line, "carries", for a mod that already contains another mod's changes.
