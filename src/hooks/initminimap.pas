hook: data/gui/menu.inc/initminimap.inc
requires:
---
//! The second boot hook (plan S5): it boots Quartermaster only when the
//! CameraControl hook did not. InitMinimap has two call paths in each start-up
//! DoCreate - through InitMap (control.script:718-719), before DoInitialize,
//! and from DoInitialize itself (doinitialize.inc:206), after CameraControl
//! (:203) - and the InitMap one keeps running when DoInitialize does not
//! compile (capability probe 7, badinit.0.log:9, :17). The build puts the
//! lines at the hook index of plan S5, 0 here: the state starts with no
//! routine, and what follows is drawing the minimap.
//!
//! The InitMap call of the first DoCreate comes before CameraControl had its
//! chance, so this hook boots from its second call on (qm_hk `im` counts the
//! calls): the DoInitialize call right after CameraControl when only the
//! CameraControl hook is missing, or the second DoCreate's InitMap call when
//! DoInitialize is broken. In a normal start the flag qm_rt is set by then
//! and the lines do nothing but count.
//!
//! Once per process and main menu only, with CameraControl's flag: the
//! named parser qm_rt exists once any hook booted (plan S5). InitMinimap also
//! runs during a skirmish's map generation (probe 7, gui.0.log:82), where the
//! main-menu guard stops it. The hook names itself in qm_rt `hook`, so the
//! report says that only a fallback ran (WARN, plan S5). The manager qm_core
//! is looked up by name and created only when missing (see cameracontrol.pas).
if (ParserSelectByKey('qm_hk')=0) then ParserCreate('qm_hk');
ParserSetIntValueByKeyByHandle(ParserSelectByKey('qm_hk'), 'im', ParserGetIntValueByKeyByHandle(ParserSelectByKey('qm_hk'), 'im')+1);
if (ParserSelectByKey('qm_rt')=0) and (gInterface.gamemode=gc_gamemode_mainmenu) and (ParserGetIntValueByKeyByHandle(ParserSelectByKey('qm_hk'), 'im')>=2) then
begin
   var qmImSm : Integer = GetTriggerManagerStateMachineHandle('qm_core');
   if (qmImSm=0) then
   begin TriggerManagerAdd('qm_core'); qmImSm := GetTriggerManagerStateMachineHandle('qm_core'); StateMachineLoadFromFile(qmImSm, '.\data\quartermaster\core.aix'); end;
   ParserCreate('qm_rt'); ParserSetValueByKeyByHandle(ParserSelectByKey('qm_rt'), 'hook', 'initminimap'); StateMachineExecuteState(qmImSm, 'qmBoot', 0);
end;
