# Changes

## 0.1.8 (2026-10-18)

- A mod that says in its about.cfg it must load after another mod (`loadAfter`, `requires`,
  `extends`, or the other mod's `loadBefore`) now does, without you pressing Auto-sort.
  Example: you subscribe to Reinforced - LAN after Reinforced - Core; before, LAN stayed
  below Core and the lobby of Core was lost. Now Quartermaster puts Core just under LAN
  the first time the game starts and says so in its report.
- Only the mod that has to move is moved; all other mods stay where they were.
- An order you set yourself in the window is never changed. If it breaks a rule you still
  get the warning, as before.
- If the rules of two mods contradict each other, nothing is moved and the report shows
  the error.
- A new line in a mod's about.cfg, `carries = <id>`, for a mod that already contains the
  changes of another mod (Reinforced - Core carries Reinforced - LAN). When that mod loads
  after the one it carries, the two no longer show a warning for the files they share: the
  report says "carried" instead. The conflicts are still listed in conflicts.txt. If the
  order is the other way round, the warning stays. An older Quartermaster ignores the line
  and shows one note about an unknown key.

Workshop change note:

> 0.1.8: mods that must load after another mod (about.cfg: loadAfter, requires, extends,
> loadBefore) are now put in the right place automatically; no Auto-sort needed. Only that
> one mod moves. An order you set yourself stays as it is. New about.cfg line `carries`:
> a mod that contains another mod's changes (e.g. Reinforced - Core and LAN) no longer
> shows warnings for the files they share, as long as it loads after that mod.
