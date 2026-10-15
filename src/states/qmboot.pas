state: qmBoot
into: data/quartermaster/core.aix
helpers: qmlog, qmstr
requires: version
---
//! Entry point, in the trigger manager qm_core that holds core.aix (plan S5,
//! S6, runtime flow). A boot hook runs it once per process in the main menu;
//! qmTick runs it again with qm_rt runmode = apply for a confirmed Apply of
//! the manager window.
//!
//! The pipeline, in order:
//!   marker     qmMarkerLoad: <save>\quartermaster\state.cfg (boot only)
//!   guards     MP sync: StringRegister7 <> '' or <save>\mods.restore exists,
//!              asked with FileAge, which is silent for a missing file where
//!              IsFileExists logs an ERROR (plan S8; both quiet at a normal
//!              boot, M0 probe 12)
//!   about      qmAbout (every mod's about.cfg), qmSettings (settings.cfg)
//!   mods       qmModList (canonical order), qmOrder (the load order: the
//!              player's saved order or canonical, an Apply's order and
//!              flags; mods.ini through qmModsIni), qmKnown (new mods)
//!   inputs     qmIndex, qmPlan, qmFingerprint
//!   plan       qmGuard step plan - regenerate? - and the marker saved at once
//!              with this start's phase (see qmguard.pas)
//!   generate   qmGenerate (the validated writer), with qm_gen_in wta = 1 for
//!              the fallback after a suspected brick and gensalt for the I5 run
//!   restart    qmGuard step restart, the marker saved, the report (qmReport
//!              after a generation, qmReportLoad and the boot's own lines
//!              otherwise)
//!   selftest   <save>\qm_autotest.cfg only, boot only (plan G18)
//!   schedule   qm_rt rs / rsdue / rskind: qmTick restarts at least 1 s after
//!              this last write, on a main-menu frame - or, after this start
//!              rewrote its outputs, the boot restarts itself (below)
//! qm_rt busy is 1 while this runs, so qmTick never runs into it.
//!
//! The I5 test: the SelfTest case file qm_m5_unstable.cfg makes the
//! fingerprint change on every boot and the generation constant with it
//! (qmGuard, gensalt) - a real "outputs change every start" loop for the
//! guards to stop. Nothing of it exists outside a SelfTest run.
//!
//! The SelfTest lives in its own file and manager so a normal start never
//! loads it; a manager name is looked up before it is added, because adding a
//! live name creates a second, empty manager (capability probes).
var qmBtBoot : Integer = 0;
var qmBtL : Integer = 0;
var qmBtTag : String = 'OK';
//! One line of the boot's report block (qm_boot l<k>) and the log.
procedure qmBtLine(const qmBlTag : String; const qmBlText : String);
begin
   ParserSetValueByKeyByHandle(qmBtBoot, 'l'+IntToStr(qmBtL), qmBlTag+' '+qmBlText);
   qmBtL := qmBtL+1;
   if (qmBlTag='FAIL') or ((qmBlTag='WARN') and (qmBtTag='OK')) then
   qmBtTag := qmBlTag;
   qmLog('boot report '+qmBlTag+' '+qmBlText);
end;

var qmBtRt : Integer = ParserSelectByKey('qm_rt');
if (qmBtRt=0) then
qmBtRt := ParserCreate('qm_rt');
var qmBtApply : Boolean = (ParserGetValueByKeyByHandle(qmBtRt, 'runmode')='apply');
var qmBtHook : String = ParserGetValueByKeyByHandle(qmBtRt, 'hook');
if (qmBtHook='') then
begin
   qmBtHook := 'cameracontrol';
   ParserSetValueByKeyByHandle(qmBtRt, 'hook', qmBtHook);
end;
ParserSetIntValueByKeyByHandle(qmBtRt, 'busy', 1);
var qmBtSave : String = GetAppSaveDirectoryPath;
var qmBtCore : Integer = GetTriggerManagerStateMachineHandle('qm_core');
var qmBtT0 : Float = _misc_GetRealTime;
if (qmBtApply) then
qmLog('boot version '+${version}+' apply seq='+IntToStr(ParserGetIntValueByKeyByHandle(qmBtRt, 'uiapplyseq')))
else
qmLog('boot version '+${version}+' hook='+qmBtHook+' hookgen='+ParserGetValueByKeyByHandle(qmBtRt, 'hookgen'));
qmBtBoot := ParserSelectByKey('qm_boot');
if (qmBtBoot=0) then
qmBtBoot := ParserCreate('qm_boot');
ParserClearByHandle(qmBtBoot);
if (not qmBtApply) then
StateMachineExecuteState(qmBtCore, 'qmMarkerLoad', 0);
//! The MP-sync guard (plan S8).
var qmBtSync : Integer = 0;
if (StringRegister7<>'') or (FileAge(qmBtSave+'mods.restore')<>-1) then
qmBtSync := 1;
ParserSetIntValueByKeyByHandle(qmBtRt, 'sync', qmBtSync);
//! The SelfTest's switches, in a SelfTest run only (qm_autotest.cfg exists):
//! a case file qm_m5_restart.cfg lets the run restart - without it a SelfTest
//! run keeps one life (qmGuard refuses the automatic restart), because the
//! SelfTest runs in every life and its results are those of one - and
//! qm_m5_unstable.cfg makes the fingerprint change every boot (I5). Both are
//! asked with FileAge alone: the switch file itself is empty in most runs,
//! and nothing here parses it.
var qmBtUnstable : Integer = 0;
var qmBtNoRestart : Integer = 0;
if (not qmBtApply) and (FileAge(qmBtSave+'qm_autotest.cfg')<>-1) then
begin
   qmBtNoRestart := 1;
   if (FileAge(qmBtSave+'qm_test\cases\qm_m5_restart.cfg')<>-1) then
   qmBtNoRestart := 0;
   if (FileAge(qmBtSave+'qm_test\cases\qm_m5_unstable.cfg')<>-1) then
   qmBtUnstable := 1;
end;
ParserSetIntValueByKeyByHandle(qmBtRt, 'unstable', qmBtUnstable);
//! A harness run's switch (tools/hrun.py --state seeds it; no player has the
//! file): <save>\quartermaster\qm_show_ui.flag opens the manager window on
//! the first main-menu frame (qmTick), so the run can capture what a player
//! would see. It changes nothing else.
if (not qmBtApply) and (FileAge(qmBtSave+'quartermaster\qm_show_ui.flag')<>-1) then
begin
   ParserSetIntValueByKeyByHandle(qmBtRt, 'uishow', 1);
   ParserSetIntValueByKeyByHandle(qmBtRt, 'tick', 1);
end;
//! The same for qm_skirmish.flag: qmTick walks the game into a skirmish on a
//! stable start, so a run sees the mods at work in a battle.
if (not qmBtApply) and (FileAge(qmBtSave+'quartermaster\qm_skirmish.flag')<>-1) then
ParserSetIntValueByKeyByHandle(qmBtRt, 'skphase', 1);
if (not qmBtApply) then
ParserSetIntValueByKeyByHandle(qmBtRt, 'norestart', qmBtNoRestart);
StateMachineExecuteState(qmBtCore, 'qmAbout', 0);
StateMachineExecuteState(qmBtCore, 'qmSettings', 0);
StateMachineExecuteState(qmBtCore, 'qmModList', 0);
StateMachineExecuteState(qmBtCore, 'qmOrder', 0);
StateMachineExecuteState(qmBtCore, 'qmKnown', 0);
StateMachineExecuteState(qmBtCore, 'qmGlobals', 0);
//! The about.cfg rules of the set this start loads (qmOrder left its flags
//! and load order in qm_mods), for the report's Boot block below.
var qmBtMods : Integer = ParserSelectByKey('qm_mods');
var qmBtAin : Integer = ParserSelectByKey('qm_abin');
if (qmBtAin=0) then
qmBtAin := ParserCreate('qm_abin');
ParserClearByHandle(qmBtAin);
var qmBtAi : Integer;
ParserSetIntValueByKeyByHandle(qmBtAin, 'n', ParserGetIntValueByKeyByHandle(qmBtMods, 'n'));
for qmBtAi:=0 to ParserGetIntValueByKeyByHandle(qmBtMods, 'n')-1 do
begin
   ParserSetIntValueByKeyByHandle(qmBtAin, 'on'+IntToStr(qmBtAi), ParserGetIntValueByKeyByHandle(qmBtMods, 'on'+IntToStr(qmBtAi)));
   ParserSetIntValueByKeyByHandle(qmBtAin, 'ord'+IntToStr(qmBtAi), ParserGetIntValueByKeyByHandle(qmBtMods, 'ord'+IntToStr(qmBtAi)));
end;
StateMachineExecuteState(qmBtCore, 'qmAbRules', 0);
StateMachineExecuteState(qmBtCore, 'qmIndex', 0);
StateMachineExecuteState(qmBtCore, 'qmPlan', 0);
StateMachineExecuteState(qmBtCore, 'qmFingerprint', 0);
var qmBtG : Integer = ParserSelectByKey('qm_guard');
if (qmBtG=0) then
qmBtG := ParserCreate('qm_guard');
ParserClearByHandle(qmBtG);
ParserSetValueByKeyByHandle(qmBtG, 'step', 'plan');
StateMachineExecuteState(qmBtCore, 'qmGuard', 0);
if (not qmBtApply) then
StateMachineExecuteState(qmBtCore, 'qmMarkerSave', 0);
var qmBtRegen : Boolean = (ParserGetIntValueByKeyByHandle(qmBtG, 'regen')=1);
var qmBtGen : Integer = ParserSelectByKey('qm_gen');
if (qmBtGen<>0) then
ParserClearByHandle(qmBtGen);
if (qmBtRegen) then
begin
   var qmBtIn : Integer = ParserSelectByKey('qm_gen_in');
   if (qmBtIn=0) then
   qmBtIn := ParserCreate('qm_gen_in');
   ParserClearByHandle(qmBtIn);
   if (ParserGetValueByKeyByHandle(qmBtG, 'mode')='wta') then
   ParserSetIntValueByKeyByHandle(qmBtIn, 'wta', 1);
   if (qmBtUnstable=1) then
   ParserSetValueByKeyByHandle(qmBtIn, 'gensalt', IntToStr(ParserGetIntValueByKeyByHandle(qmBtG, 'boots')));
   StateMachineExecuteState(qmBtCore, 'qmGenerate', 0);
end;
ParserSetValueByKeyByHandle(qmBtG, 'step', 'restart');
StateMachineExecuteState(qmBtCore, 'qmGuard', 0);
StateMachineExecuteState(qmBtCore, 'qmMarkerSave', 0);
//! The boot's own report lines (docs/plan.md G13; the report prints them as
//! its Boot block).
var qmBtSt : Integer = ParserSelectByKey('qm_state');
var qmBtIni : Integer = ParserSelectByKey('qm_ini');
var qmBtKn : Integer = ParserSelectByKey('qm_known');
var qmBtOrd : Integer = ParserSelectByKey('qm_order');
var qmBtSrc : String = ParserGetValueByKeyByHandle(qmBtOrd, 'src');
var qmBtWhy : String = ParserGetValueByKeyByHandle(qmBtG, 'why');
var qmBtRef : String = ParserGetValueByKeyByHandle(qmBtG, 'refused');
var qmBtK : Integer;
if (qmBtHook<>'cameracontrol') and (not qmBtApply) then
qmBtLine('WARN', 'Quartermaster was started by its '+qmBtHook+' hook: the CameraControl hook did not run (another mod may replace cameracontrol.inc).');
if (qmBtSync=1) then
qmBtLine('OK', 'A multiplayer mod sync is in progress: nothing was regenerated, written or restarted.');
//! The previous start, when it stopped at "Error compiling scripts": which
//! library of which mod, from its log (qmLastStart, ref/laststart.py).
if (qmBtSync=0) then
begin
   StateMachineExecuteState(qmBtCore, 'qmLastStart', 0);
   if (ParserGetValueByKeyByHandle(ParserSelectByKey('qm_ls'), 'line')<>'') then
   qmBtLine('WARN', ParserGetValueByKeyByHandle(ParserSelectByKey('qm_ls'), 'line'));
end;
if (qmBtWhy='suspected-brick') then
qmBtLine('FAIL', 'The previous start with generation '+IntToStr(ParserGetIntValueByKeyByHandle(qmBtSt, 'gen'))+' stopped before the main menu: merges are switched off for these mods (each file comes from its winner).');
if (qmBtWhy='fallback-kept') then
qmBtLine('FAIL', 'Merges stay switched off for these mods after a start that stopped before the main menu.');
if (qmBtWhy='damaged') then
begin
   // After an Apply that could not check a merged file (qmGuard recheck).
   if (ParserGetIntValueByKeyByHandle(qmBtG, 'recheck')=1) then
   qmBtLine('OK', 'A file the last Apply could not check was built again, now that the scripts of the new mods are loaded.')
   else
   qmBtLine('OK', 'Quartermaster''s files were changed from outside (an update?): regenerated.');
end;
if (ParserGetValueByKeyByHandle(qmBtIni, 'action')='written') then
begin
   //! Exactly what moved (1-based positions in mods.ini) and which flags
   //! changed, so the player can compare with modman.
   var qmBtWhat : String = '';
   if (ParserGetValueByKeyByHandle(qmBtIni, 'moves')<>'') then
   qmBtWhat := ' Moved: '+ParserGetValueByKeyByHandle(qmBtIni, 'moves')+'.';
   if (ParserGetValueByKeyByHandle(qmBtIni, 'flags')<>'') then
   qmBtWhat := qmBtWhat+' Switched: '+ParserGetValueByKeyByHandle(qmBtIni, 'flags')+'.';
   //! Which order it was put into (qmOrder, qm_order src): the order chosen
   //! in the manager, the saved one - put back when mods.ini was reordered
   //! outside Quartermaster (modman) - or, with no saved order, mods.ini's
   //! own with Quartermaster moved last (plan S11).
   if (qmBtSrc='apply') then
   qmBtLine('OK', 'mods.ini was put into the load order chosen in the manager, Quartermaster last.'+qmBtWhat)
   else
   if (qmBtSrc='saved') and (ParserGetIntValueByKeyByHandle(qmBtOrd, 'ext')=1) then
   qmBtLine('OK', 'mods.ini was reordered outside Quartermaster (in modman?): the saved load order was put back, Quartermaster last.'+qmBtWhat)
   else
   if (qmBtSrc='saved') then
   qmBtLine('OK', 'mods.ini was put into the saved load order, Quartermaster last.'+qmBtWhat)
   else
   qmBtLine('OK', 'Your load order is kept; Quartermaster moved itself to the end.'+qmBtWhat);
end;
if (ParserGetValueByKeyByHandle(qmBtIni, 'action')='refused') or (ParserGetValueByKeyByHandle(qmBtIni, 'action')='failed') then
qmBtLine('WARN', 'mods.ini was not changed ('+ParserGetValueByKeyByHandle(qmBtIni, 'why')+'): the game may load the mods in another order than Quartermaster''s load order.');
if (ParserGetIntValueByKeyByHandle(qmBtOrd, 'unseen')>0) then
begin
   var qmBtUn : String = '';
   for qmBtK:=0 to ParserGetIntValueByKeyByHandle(qmBtOrd, 'unseen')-1 do
   begin
      if (qmBtUn<>'') then
      qmBtUn := qmBtUn+', ';
      qmBtUn := qmBtUn+ParserGetValueByKeyByHandle(qmBtOrd, 'u'+IntToStr(qmBtK));
   end;
   qmBtLine('OK', 'Not in the saved load order yet, so placed after it, before Quartermaster: '+qmBtUn+'.');
end;
//! Plan S11: the same order on every machine is the players' job in MP once it
//! is not the canonical one (docs/plan.md S11, S12).
if (ParserGetIntValueByKeyByHandle(qmBtOrd, 'canon')=0) and (qmBtSrc<>'') then
qmBtLine('OK', 'Multiplayer: every player needs the same mods in the same load order.');
//! Global scripts (qmGlobals, plan S17): the mods the start-up guard
//! switched off at this start, then every clash between enabled mods.
var qmBtGl : Integer = ParserSelectByKey('qm_glob');
var qmBtGs : String;
// The clashes also go to qm_boot as dirs (gcn, gca<k>, gcb<k>, gcf<k>), so
// qmReport puts each into both mods' own blocks; qm_boot outlives a boot, so
// the count is reset first.
ParserSetIntValueByKeyByHandle(qmBtBoot, 'gcn', 0);
if (qmBtGl<>0) then
begin
   if (ParserGetIntValueByKeyByHandle(qmBtGl, 'gdnew')=1) then
   begin
      for qmBtK:=0 to ParserGetIntValueByKeyByHandle(qmBtGl, 'gdn')-1 do
      begin
         qmBtGs := IntToStr(qmBtK);
         // A step after a failed start switches a mod off without a clash (no
         // file), or by name (failed-names). Such a start stopped at "Error
         // compiling scripts" or with a main menu that did not compile, so the
         // lines say only that it did not reach the main menu.
         if (ParserGetValueByKeyByHandle(qmBtGl, 'gdf'+qmBtGs)='') then
         qmBtLine('WARN', 'Switched off at the start, before the scripts compiled: the mod '+ParserGetValueByKeyByHandle(qmBtGl, 'gdt'+qmBtGs)+'. The start before did not reach the main menu, so Quartermaster went back towards mods that started.')
         else
         if (SubStr(ParserGetValueByKeyByHandle(qmBtGl, 'gdwhy'), 1, 7)='failed-') then
         qmBtLine('WARN', 'Switched off at the start, before the scripts compiled: the mod '+ParserGetValueByKeyByHandle(qmBtGl, 'gdt'+qmBtGs)+'. It ships scripts\'+ParserGetValueByKeyByHandle(qmBtGl, 'gdf'+qmBtGs)+', and so does '+ParserGetValueByKeyByHandle(qmBtGl, 'gdo'+qmBtGs)+', and the start before, with both, did not reach the main menu.')
         else
         qmBtLine('WARN', 'Switched off at the start, before the scripts compiled: the mod '+ParserGetValueByKeyByHandle(qmBtGl, 'gdt'+qmBtGs)+'. It ships scripts\'+ParserGetValueByKeyByHandle(qmBtGl, 'gdf'+qmBtGs)+', and so does '+ParserGetValueByKeyByHandle(qmBtGl, 'gdo'+qmBtGs)+'; they had not started together, and with both the game may stop at "Error compiling scripts". If they work together, activate it again in Quartermaster''s window.');
      end;
      ParserSetIntValueByKeyByHandle(qmBtRt, 'gdshow', 1);
      ParserSetIntValueByKeyByHandle(qmBtRt, 'tick', 1);
   end;
   if (ParserGetIntValueByKeyByHandle(qmBtGl, 'gdmoved')=1) then
   qmBtLine('OK', 'Quartermaster was moved to the end of the load order at the start: '+ParserGetValueByKeyByHandle(qmBtGl, 'gdlate')+' was after it and ships '+ParserGetValueByKeyByHandle(qmBtGl, 'gdlatef')+', which would have replaced its hook.');
   for qmBtK:=0 to ParserGetIntValueByKeyByHandle(qmBtGl, 'cn')-1 do
   begin
      qmBtGs := IntToStr(qmBtK);
      // A WARN since 0.1.3: this start compiled with both (a booted clash).
      qmBtLine('WARN', ParserGetValueByKeyByHandle(qmBtGl, 'tit'+IntToStr(ParserGetIntValueByKeyByHandle(qmBtGl, 'ca'+qmBtGs)))+' and '+ParserGetValueByKeyByHandle(qmBtGl, 'tit'+IntToStr(ParserGetIntValueByKeyByHandle(qmBtGl, 'cb'+qmBtGs)))+' both ship scripts\'+ParserGetValueByKeyByHandle(qmBtGl, 'cf'+qmBtGs)+': only the later one''s copy loads. The game started with both; if one of them misbehaves, switch the other one off.');
      ParserSetValueByKeyByHandle(qmBtBoot, 'gca'+qmBtGs, ParserGetValueByKeyByHandle(qmBtGl, 'dir'+IntToStr(ParserGetIntValueByKeyByHandle(qmBtGl, 'ca'+qmBtGs))));
      ParserSetValueByKeyByHandle(qmBtBoot, 'gcb'+qmBtGs, ParserGetValueByKeyByHandle(qmBtGl, 'dir'+IntToStr(ParserGetIntValueByKeyByHandle(qmBtGl, 'cb'+qmBtGs))));
      ParserSetValueByKeyByHandle(qmBtBoot, 'gcf'+qmBtGs, ParserGetValueByKeyByHandle(qmBtGl, 'cf'+qmBtGs));
      // tools/m7accept.py reads the pair back from this line (no dir holds `|`).
      qmLog('boot clash|'+ParserGetValueByKeyByHandle(qmBtBoot, 'gca'+qmBtGs)+'|'+ParserGetValueByKeyByHandle(qmBtBoot, 'gcb'+qmBtGs)+'|'+ParserGetValueByKeyByHandle(qmBtBoot, 'gcf'+qmBtGs));
   end;
   ParserSetIntValueByKeyByHandle(qmBtBoot, 'gcn', ParserGetIntValueByKeyByHandle(qmBtGl, 'cn'));
end;
//! about.cfg (qmAbout, qmAbRules; ref/about.py): what an enabled mod's file
//! says wrong, the rules the set breaks, a cycle of load-order rules.
var qmBtAb : Integer = ParserSelectByKey('qm_about');
var qmBtAr : Integer = ParserSelectByKey('qm_abr');
var qmBtAs : String;
var qmBtAk : Integer;
var qmBtAt : String;
if (qmBtAb<>0) then
begin
   for qmBtK:=0 to ParserGetIntValueByKeyByHandle(qmBtAb, 'n')-1 do
   if (ParserGetIntValueByKeyByHandle(qmBtMods, 'on'+IntToStr(qmBtK))=1) then
   begin
      qmBtAs := IntToStr(qmBtK);
      for qmBtAk:=0 to ParserGetIntValueByKeyByHandle(qmBtAb, 'pn'+qmBtAs)-1 do
      qmBtLine(ParserGetValueByKeyByHandle(qmBtAb, 'pt'+qmBtAs+'_'+IntToStr(qmBtAk)), 'about.cfg of '+ParserGetValueByKeyByHandle(qmBtAb, 'tit'+qmBtAs)+': '+ParserGetValueByKeyByHandle(qmBtAb, 'px'+qmBtAs+'_'+IntToStr(qmBtAk))+'.');
   end;
   if (qmBtAr<>0) then
   for qmBtK:=0 to ParserGetIntValueByKeyByHandle(qmBtAr, 'n')-1 do
   qmBtLine(ParserGetValueByKeyByHandle(qmBtAr, 'tag'+IntToStr(qmBtK)), ParserGetValueByKeyByHandle(qmBtAr, 'text'+IntToStr(qmBtK))+'.');
   if (ParserGetIntValueByKeyByHandle(qmBtMods, 'cycn')>0) then
   begin
      qmBtAt := '';
      for qmBtK:=0 to ParserGetIntValueByKeyByHandle(qmBtMods, 'cycn')-1 do
      begin
         if (qmBtAt<>'') then
         qmBtAt := qmBtAt+', ';
         qmBtAt := qmBtAt+ParserGetValueByKeyByHandle(qmBtAb, 'tit'+IntToStr(ParserGetIntValueByKeyByHandle(qmBtMods, 'cyc'+IntToStr(qmBtK))));
      end;
      qmBtLine('FAIL', 'The load-order rules in about.cfg files form a cycle; placed by canonical order to break it: '+qmBtAt+'.');
   end;
end;
//! Plan S10: the player's saved hotkeys replace every shipped hotkeys.cfg -
//! RegisterShortcuts reads <save>\hotkeys\hotkeys.cfg when it exists
//! (registershortcuts.inc:187-192) - so a mod's key changes there do not
//! apply for this player.
var qmBtHkIdx : Integer = ParserSelectByKey('qm_index');
var qmBtHkKeys : Integer = ParserSelectByKey('qm_index_keys');
var qmBtHkK : Integer;
if (qmBtHkIdx<>0) and (qmBtHkKeys<>0) and (FileAge(qmBtSave+'hotkeys\hotkeys.cfg')<>-1) then
for qmBtHkK:=0 to ParserGetIntValueByKeyByHandle(qmBtHkIdx, 'n')-1 do
if (ParserGetValueByKeyByHandle(qmBtHkIdx, 'p'+IntToStr(qmBtHkK))='game\var\hotkeys.cfg') and (ParserGetValueByKeyByHandle(qmBtHkIdx, 'v'+IntToStr(qmBtHkK))<>'-') then
qmBtLine('WARN', 'Your saved hotkeys (Documents\cossacks\hotkeys\hotkeys.cfg) are what the game reads: the hotkeys.cfg a mod ships does not apply for you.');
if (qmBtRef='loop') then
qmBtLine('FAIL', 'No automatic restart: the mods changed again across Quartermaster''s own restart. The new files load at the next start.');
if (qmBtRef='in-a-row') then
qmBtLine('FAIL', 'No automatic restart: two in a row already. The new files load at the next start.');
if (qmBtRef='per-hash') then
qmBtLine('FAIL', 'No automatic restart: the game was already restarted once for these mods. The new files load at the next start.');
if (qmBtRef='mp-sync') then
qmBtLine('WARN', 'No restart during a multiplayer mod sync.');
if (qmBtRef='selftest') then
qmBtLine('OK', 'No automatic restart in a SelfTest run (no qm_m5_restart.cfg case).');
if (ParserGetIntValueByKeyByHandle(qmBtG, 'restart')=1) then
//! In the past tense: the player reads it after the restart, in the window
//! or in report.txt (until 2026-10-01 it read "restarts now").
qmBtLine('OK', 'The game restarted to load the new files ('+ParserGetValueByKeyByHandle(qmBtG, 'rwhy')+').');
ParserSetIntValueByKeyByHandle(qmBtBoot, 'n', qmBtL);
ParserSetValueByKeyByHandle(qmBtBoot, 'st', qmBtTag);
ParserSetIntValueByKeyByHandle(qmBtBoot, 'newn', ParserGetIntValueByKeyByHandle(qmBtKn, 'newn'));
for qmBtK:=0 to ParserGetIntValueByKeyByHandle(qmBtKn, 'newn')-1 do
ParserSetValueByKeyByHandle(qmBtBoot, 'new'+IntToStr(qmBtK), ParserGetValueByKeyByHandle(qmBtKn, 'new'+IntToStr(qmBtK)));
if (qmBtRegen) then
StateMachineExecuteState(qmBtCore, 'qmReport', 0)
else
begin
   //! No generation: the last generation's report, with this boot's NEW
   //! marks and its lines on top (qmReport does both itself after a
   //! generation).
   StateMachineExecuteState(qmBtCore, 'qmReportLoad', 0);
   var qmBtRep : Integer = ParserSelectByKey('qm_report');
   var qmBtJ : Integer;
   var qmBtNd : String;
   var qmBtRd : String;
   if (qmBtRep<>0) then
   begin
      for qmBtK:=0 to ParserGetIntValueByKeyByHandle(qmBtKn, 'newn')-1 do
      begin
         qmLowerAscii(ParserGetValueByKeyByHandle(qmBtKn, 'new'+IntToStr(qmBtK)), qmBtNd);
         for qmBtJ:=0 to ParserGetIntValueByKeyByHandle(qmBtRep, 'n')-1 do
         begin
            qmLowerAscii(ParserGetValueByKeyByHandle(qmBtRep, 'dir'+IntToStr(qmBtJ)), qmBtRd);
            if (qmBtRd=qmBtNd) and (ParserGetValueByKeyByHandle(qmBtRep, 'st'+IntToStr(qmBtJ))='OK') then
            ParserSetValueByKeyByHandle(qmBtRep, 'st'+IntToStr(qmBtJ), 'NEW');
         end;
      end;
      if (qmBtL>0) then
      begin
         qmBtJ := ParserGetIntValueByKeyByHandle(qmBtRep, 'lines');
         ParserSetValueByKeyByHandle(qmBtRep, 'l'+IntToStr(qmBtJ), '');
         ParserSetValueByKeyByHandle(qmBtRep, 'l'+IntToStr(qmBtJ+1), 'This start:');
         qmBtJ := qmBtJ+2;
         for qmBtK:=0 to qmBtL-1 do
         begin
            ParserSetValueByKeyByHandle(qmBtRep, 'l'+IntToStr(qmBtJ), '  '+ParserGetValueByKeyByHandle(qmBtBoot, 'l'+IntToStr(qmBtK)));
            qmBtJ := qmBtJ+1;
         end;
         ParserSetIntValueByKeyByHandle(qmBtRep, 'lines', qmBtJ);
      end;
   end;
end;
if (not qmBtApply) and (FileAge(qmBtSave+'qm_autotest.cfg')<>-1) then
begin
   var qmBtTest : Integer = GetTriggerManagerStateMachineHandle('qm_test');
   if (qmBtTest=0) then
   begin
      TriggerManagerAdd('qm_test');
      qmBtTest := GetTriggerManagerStateMachineHandle('qm_test');
   end;
   StateMachineLoadFromFile(qmBtTest, '.\data\quartermaster\selftest.aix');
   StateMachineExecuteState(qmBtTest, 'qmSelfTest', 0);
end;
//! The restart, scheduled last: at least 1 s after this boot's last write.
var qmBtNow : Integer = Floor(_misc_GetRealTime*10);
//! An automatic restart after this start rewrote its outputs (the marker says
//! `written`) runs here, at the end of the boot, not from qmTick. This process
//! loaded the files the generation replaced, and the engine compiles a state
//! when it first runs it, from the text it loaded: an old DoProgress merged
//! with a mod's library that has since lost a function does not compile, and
//! the frame hook goes with it (hands-on, 2026-10-14: Reinforced - Core
//! changed with the game closed, "Compile script error: DoProgress", no
//! restart, a blank screen for the lobby). The hook that ran this boot did
//! compile, and qmRestart is Quartermaster's own. RestartApplicationParam
//! returns, and the engine ends the process later: the start-up guard's call,
//! made before the libraries compile, ended its life right after the
//! start-up's second DoCreate, with DoProgress broken as well
//! (cos_261010_130720.log:7, :164-169; the next life started 7 s after it).
//! Run g22 (2026-10-15) proved this call the same way: a test mod updated
//! with the game closed, the old DoProgress did not compile, the life ended
//! after the second DoCreate and the next one, 7 s later, booted clean; 0.1.6
//! under the same update stayed in its first life (no tick, no restart).
//! When the start-up guard restarted this process already (it moved
//! Quartermaster last), this second call changes nothing: one restart, one
//! next life (run g22g).
//! Every other restart stays with qmTick: after mods.ini alone no file this
//! process loaded changed; a generation that did not finish leaves the marker
//! in the phase this start set, and `booting` wants the first main-menu
//! frame's confirm before a restart (ref/boot.py restart_at_boot); an Apply's
//! the player asked for in the window.
var qmBtNowRs : Boolean = False;
if (ParserGetIntValueByKeyByHandle(qmBtG, 'restart')=1) then
begin
   ParserSetIntValueByKeyByHandle(qmBtRt, 'rs', 1);
   ParserSetIntValueByKeyByHandle(qmBtRt, 'rsdue', qmBtNow+11);
   ParserSetValueByKeyByHandle(qmBtRt, 'rskind', ParserGetValueByKeyByHandle(qmBtG, 'kind'));
   ParserSetValueByKeyByHandle(qmBtRt, 'rswhy', ParserGetValueByKeyByHandle(qmBtG, 'rwhy'));
   if (ParserGetValueByKeyByHandle(qmBtG, 'kind')='auto') and (ParserGetValueByKeyByHandle(qmBtSt, 'phase')='written') and (gMap.gamestage=gc_map_gamestage_none) then
   begin
      qmBtNowRs := True;
      ParserSetIntValueByKeyByHandle(qmBtRt, 'rs', 2);
   end;
end;
if (ParserGetValueByKeyByHandle(qmBtSt, 'phase')='booting') then
ParserSetIntValueByKeyByHandle(qmBtRt, 'confirm', 1);
ParserSetIntValueByKeyByHandle(qmBtRt, 'tick', 1);
ParserSetIntValueByKeyByHandle(qmBtRt, 'busy', 0);
qmLog('boot done regen='+BoolToStr(qmBtRegen)+' why='+qmBtWhy+' restart='+ParserGetValueByKeyByHandle(qmBtG, 'kind')+' refused='+qmBtRef+' mods.ini='+ParserGetValueByKeyByHandle(qmBtIni, 'action')+' new='+IntToStr(ParserGetIntValueByKeyByHandle(qmBtKn, 'newn'))+' report='+qmBtTag+' ms='+FloatToStr((_misc_GetRealTime-qmBtT0)*1000));
if (not qmBtRegen) and (qmBtRef='') and (ParserGetIntValueByKeyByHandle(qmBtG, 'restart')=0) and (not qmBtApply) and (qmBtSync=0) then
qmLog('boot stable gen='+IntToStr(ParserGetIntValueByKeyByHandle(qmBtSt, 'gen'))+' hash='+ParserGetValueByKeyByHandle(qmBtSt, 'hash')+' boots='+IntToStr(ParserGetIntValueByKeyByHandle(qmBtSt, 'boots')));
if (qmBtNowRs) then
begin
   qmLog('restart now kind=auto why='+ParserGetValueByKeyByHandle(qmBtG, 'rwhy')+' at the end of the boot: this start loaded the files it rewrote');
   StateMachineExecuteState(qmBtCore, 'qmRestart', 0);
end;
