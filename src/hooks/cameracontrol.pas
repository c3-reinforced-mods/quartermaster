hook: data/gui/menu.inc/cameracontrol.inc
requires: hookgen
---
//! Quartermaster's primary boot hook (plan S5, S6), in front of the first line
//! after CameraControl's nested procedure - the place the capability probes
//! hooked. CameraControl runs from DoInitialize (doinitialize.inc:203) on
//! every DoCreate. Engine API only, no globals.
//!
//! qmHookGen is the generation constant of plan S6: inside the MP checksum,
//! so two players with different outputs never pass the check. The build
//! bakes in the value the generator writes when Quartermaster is the only mod
//! (ref/validate.py alone_outputs_hash), so a fresh install with no other mod
//! finds its shipped copies current and needs no restart; every generation
//! replaces the line with its own outputs hash (M4, qmGenerate). The boot
//! publishes it as qm_rt `hookgen`.
//!
//! Trigger managers die at every DoCreate that runs InitMap and at every map
//! load, so the manager qm_core is looked up by name on every call and
//! re-created only when it is gone: adding a live name creates a second, empty
//! manager (capability probes). core.aix loads through the overlay, which
//! serves the last enabled copy - the one qmModList then calls Quartermaster's
//! own folder by the same rule (plan G1; the hook has no room for the
//! sixteen var parameters of ModLibraryGetData).
//!
//! qm_hk counts the calls of the boot hooks (`cc` here, `im` in InitMinimap)
//! across the process: the evidence that the hook points run as the capability
//! probes counted them (probe 11), and the input of the fallback hooks'
//! priority.
//!
//! qmBoot runs once per process, in the main menu: the named parser qm_rt
//! survives map loads and marks that it ran (plan S5). The fallback hooks
//! (InitMinimap, DoProgress) share that flag and name themselves in qm_rt
//! `hook`; this one leaves it empty. For the ten-line limit of plan S5 the
//! hook carries no comment line.
//!
//! qmUiEnsure runs on every DoCreate, after the boot: a map load reloads the
//! GUI machine and drops the manager window's runtime-added states, so they
//! are checked and put back each time (docs/ui.md). It acts in the main menu
//! only and returns at once, without a log line, anywhere else - CameraControl
//! runs in a battle too.
const qmHookGen = ${hookgen};
var qmHookSm : Integer = GetTriggerManagerStateMachineHandle('qm_core');
if (qmHookSm=0) then
begin TriggerManagerAdd('qm_core'); qmHookSm := GetTriggerManagerStateMachineHandle('qm_core'); StateMachineLoadFromFile(qmHookSm, '.\data\quartermaster\core.aix'); end;
if (ParserSelectByKey('qm_hk')=0) then ParserCreate('qm_hk');
ParserSetIntValueByKeyByHandle(ParserSelectByKey('qm_hk'), 'cc', ParserGetIntValueByKeyByHandle(ParserSelectByKey('qm_hk'), 'cc')+1);
if (ParserSelectByKey('qm_rt')=0) and (gInterface.gamemode=gc_gamemode_mainmenu) then
begin ParserCreate('qm_rt'); ParserSetValueByKeyByHandle(ParserSelectByKey('qm_rt'), 'hookgen', qmHookGen); StateMachineExecuteState(qmHookSm, 'qmBoot', 0); end;
StateMachineExecuteState(qmHookSm, 'qmUiEnsure', 0);
