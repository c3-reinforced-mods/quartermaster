hook: data/gui/menu.inc/doprogress.inc
requires:
---
//! The last-resort boot hook and Quartermaster's main-menu tick (plan S5,
//! G14). The engine runs DoProgress itself every 10 ms (menu.cfg:20, :28) and
//! it kept running with DoInitialize or CameraControl broken (capability
//! probes 7-8). The build puts the lines at the hook index of plan S5: 10,
//! after the ExecuteStateByFlag routine and its blank line, where probes 4
//! and 5 inserted theirs.
//!
//! Main menu only: in a battle the first comparison is all these lines cost.
//! Boot: when no hook booted yet (qm_rt missing) and the InitMinimap hook had
//! its turn - it never ran (no qm_hk) or ran twice - so the priority of plan
//! S5 holds whenever the first tick comes: in capability probe 11 it came
//! between the two start-up DoCreates (gui.0.log:22), possibly before
//! InitMinimap's second call; in run m5compile, after a boot of 1.1 s in the
//! first DoCreate, only after the second (0.cos_260928_115653.log:53-62).
//! The hook names itself in qm_rt `hook` (WARN in the report).
//!
//! Tick: qmTick on every main-menu frame. It confirms that the start reached
//! the menu (state.cfg `booted`), runs a confirmed Apply of the manager window
//! (qm_rt uiapply, docs/ui.md) and the restart - at least 1 s after the last
//! write, on a main-menu frame, as the probe-5 restart did from a DoProgress
//! hook (docs/research/context-2026-09-27.md section 3); not the one after a
//! start that rewrote its outputs, which the boot runs itself, as this very
//! state may then be an old merge that does not compile (qmboot.pas). A
//! state run costs next to nothing (20k calls < 1 ms,
//! docs/research/context-2026-09-27.md section 3) and qmTick returns after a
//! few parser reads when there is nothing to do.
//! The manager qm_core is looked up by name each frame and created only when
//! missing: the CameraControl hook normally re-creates it after every
//! InitMap, so this happens only when that hook is gone.
if (gInterface.gamemode=gc_gamemode_mainmenu) then
begin
   var qmDpSm : Integer = GetTriggerManagerStateMachineHandle('qm_core');
   if (qmDpSm=0) then
   begin TriggerManagerAdd('qm_core'); qmDpSm := GetTriggerManagerStateMachineHandle('qm_core'); StateMachineLoadFromFile(qmDpSm, '.\data\quartermaster\core.aix'); end;
   if (ParserSelectByKey('qm_rt')=0) and ((ParserSelectByKey('qm_hk')=0) or (ParserGetIntValueByKeyByHandle(ParserSelectByKey('qm_hk'), 'im')>=2)) then
   begin ParserCreate('qm_rt'); ParserSetValueByKeyByHandle(ParserSelectByKey('qm_rt'), 'hook', 'doprogress'); StateMachineExecuteState(qmDpSm, 'qmBoot', 0); end;
   StateMachineExecuteState(qmDpSm, 'qmTick', 0);
end;
