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

Workshop change note:

> 0.1.8: mods that must load after another mod (about.cfg: loadAfter, requires, extends,
> loadBefore) are now put in the right place automatically; no Auto-sort needed. Only that
> one mod moves. An order you set yourself stays as it is.
