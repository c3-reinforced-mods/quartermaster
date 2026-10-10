state: qmUiAct
into: data/quartermaster/core.aix
helpers: qmlog, qmglob, qmstr, qmnum, qmkeys
requires:
---
//! The manager's controller. EventQmManager, a GUI state, turns each click or
//! key into one command in qm_ui (`cmd`, with `arg`, `argside`, `argto`,
//! `argtext`) and runs this state; a trigger-manager state cannot
//! read the GUI event values Tag / Press itself (capability probes, probe
//! 9b), so they travel in the named parser. Afterwards the event state either
//! hides the window (`close` = 1) or re-runs ShowQmManager, which draws qm_ui
//! as it is now - the vanilla refresh (data/gui/menu.inc/eventcampaign.inc:24).
//!
//! Keeping the logic here rather than in the GUI states means a scripted test
//! can drive the window's behaviour by writing `cmd` and running this state,
//! with no click. docs/ui.md lists the commands and keys.
//!
//! Modes (`mode`): 0 browse, 1 the confirm dialog, 2 the restart notice after
//! a confirmed Apply, 3 the start-up guard's notice (plan S17: the mods it
//! switched off, shown once over the window; qmTick opens the window with
//! `gdopen` = 1). While the dialog is open only its answers count; while
//! the restart notice shows only close does (the restart comes anyway); the
//! guard's notice takes `ok` (Enter, Esc) and close.
//!
//! Global scripts (plan S17): after every command the pending set - the rows
//! pe<i> = 1 - is checked for two rows that ship the same global script
//! (gl<i>, qmUiModel): `pcn` clashes, pc<k> one line each, pcl<i> the clash
//! of a row for its Details line. Apply asks with the clashes as notes: two
//! mods that ship the same file may still run together, and a start that
//! stops at "Error compiling scripts" is undone by the start-up guard at the
//! next start (plan S17, 0.1.3). Until 0.1.3 the dialog listed them instead of
//! the question (confblk) and confirm refused; confblk is now about.cfg rules
//! and the activation check only.
//!
//! After every command the pending changes are counted again: `chg` rows
//! whose activation differs from what the game loaded, and `canapply` = 1
//! while there is such a row or the load order differs (ordchg, qmUiOrder):
//! the Apply button is enabled only then (decided 2026-09-28).
//!
//! The commands are compared in an if chain: a `case` over strings with one
//! label per arm is vanilla (eventcampaign.inc:16-36), but several labels per
//! arm and an `else` arm over strings appear nowhere in the shipped scripts.
//!
//! The message texts are final since 2026-09-30.
var qmUaUi : Integer = ParserSelectByKey('qm_ui');
if (qmUaUi=0) then
exit;
var qmUaCore : Integer = GetTriggerManagerStateMachineHandle('qm_core');
var qmUaCmd : String = ParserGetValueByKeyByHandle(qmUaUi, 'cmd');
var qmUaArg : Integer = ParserGetIntValueByKeyByHandle(qmUaUi, 'arg');
var qmUaText : String = ParserGetValueByKeyByHandle(qmUaUi, 'argtext');
var qmUaMode : Integer = ParserGetIntValueByKeyByHandle(qmUaUi, 'mode');
var qmUaN : Integer = ParserGetIntValueByKeyByHandle(qmUaUi, 'n');
var qmUaSel : Integer = ParserGetIntValueByKeyByHandle(qmUaUi, 'sel');
var qmUaSelf : Integer = ParserGetIntValueByKeyByHandle(qmUaUi, 'self');
var qmUaDone : Boolean = False;
var qmUaS : String;
var qmUaI : Integer;
var qmUaK : Integer;
var qmUaChg : Integer;
var qmUaCn : Integer;
var qmUaPlace : Integer;
const qmUaConfMax = 14;

//! The pending set as one string: every row in the pending order with its
//! flag. The activation check (qmTrial) answers for exactly this set.
procedure qmUaSig(var qmUsOut : String);
begin
   var qmUsUi : Integer = ParserSelectByKey('qm_ui');
   var qmUsK : Integer;
   var qmUsR : String;
   qmUsOut := '';
   for qmUsK:=0 to ParserGetIntValueByKeyByHandle(qmUsUi, 'n')-1 do
   begin
      qmUsR := IntToStr(ParserGetIntValueByKeyByHandle(qmUsUi, 'ord'+IntToStr(qmUsK)));
      qmUsOut := qmUsOut+qmUsR+':'+IntToStr(ParserGetIntValueByKeyByHandle(qmUsUi, 'pe'+qmUsR))+',';
   end;
end;
//! Ask qmTick for the activation check (qmTrial) of the pending set: for
//! row qmUtRow just activated, or -1 for every row Apply switches on.
//! False when there is no boot to check against (no qm_rt or qm_mods).
function qmUaTrialAsk(const qmUtRow : Integer) : Boolean;
begin
   var qmUtUi : Integer = ParserSelectByKey('qm_ui');
   var qmUtRt : Integer = ParserSelectByKey('qm_rt');
   var qmUtSig : String;
   Result := False;
   if (qmUtRt<>0) and (ParserSelectByKey('qm_mods')<>0) then
   begin
      qmUaSig(qmUtSig);
      ParserSetIntValueByKeyByHandle(qmUtRt, 'trq', ParserGetIntValueByKeyByHandle(qmUtRt, 'trq')+1);
      ParserSetIntValueByKeyByHandle(qmUtRt, 'trat', Floor(_misc_GetRealTime*10));
      ParserSetIntValueByKeyByHandle(qmUtRt, 'trrow', qmUtRow);
      ParserSetValueByKeyByHandle(qmUtRt, 'trsig', qmUtSig);
      ParserSetIntValueByKeyByHandle(qmUtUi, 'trpend', 1);
      Result := True;
   end;
end;

//! One line of the confirm dialog's list (conf<k>), at most qmUaConfMax.
procedure qmUaConf(const qmUcLine : String);
begin
   var qmUcUi : Integer = ParserSelectByKey('qm_ui');
   var qmUcN : Integer = ParserGetIntValueByKeyByHandle(qmUcUi, 'confn');
   if (qmUcN<qmUaConfMax) then
   ParserSetValueByKeyByHandle(qmUcUi, 'conf'+IntToStr(qmUcN), qmUcLine);
   ParserSetIntValueByKeyByHandle(qmUcUi, 'confn', qmUcN+1);
end;

//! One line of the confirm dialog's load-order column (confo<k>), at most
//! qmUaConfMax: the dialog shows changes and order side by side (hands-on check),
//! so neither list pushes the other out of the window.
procedure qmUaConfOrd(const qmUoLine : String);
begin
   var qmUoUi : Integer = ParserSelectByKey('qm_ui');
   var qmUoN : Integer = ParserGetIntValueByKeyByHandle(qmUoUi, 'confon');
   if (qmUoN<qmUaConfMax) then
   ParserSetValueByKeyByHandle(qmUoUi, 'confo'+IntToStr(qmUoN), qmUoLine);
   ParserSetIntValueByKeyByHandle(qmUoUi, 'confon', qmUoN+1);
end;

//! The about.cfg rules of the pending set (qmAbRules into qm_abr): the rows
//! pe<i> = 1 in the pending order ord<k>. Only when qmUiModel matched
//! qm_about to these rows (abok); otherwise qm_abr is left empty.
procedure qmUaRules;
begin
   var qmUrUi : Integer = ParserSelectByKey('qm_ui');
   var qmUrN : Integer = ParserGetIntValueByKeyByHandle(qmUrUi, 'n');
   var qmUrK : Integer;
   var qmUrIn : Integer = ParserSelectByKey('qm_abin');
   if (qmUrIn=0) then
   qmUrIn := ParserCreate('qm_abin');
   ParserClearByHandle(qmUrIn);
   if (ParserGetIntValueByKeyByHandle(qmUrUi, 'abok')=1) then
   ParserSetIntValueByKeyByHandle(qmUrIn, 'n', qmUrN)
   else
   ParserSetIntValueByKeyByHandle(qmUrIn, 'n', 0);
   for qmUrK:=0 to qmUrN-1 do
   begin
      ParserSetIntValueByKeyByHandle(qmUrIn, 'on'+IntToStr(qmUrK), ParserGetIntValueByKeyByHandle(qmUrUi, 'pe'+IntToStr(qmUrK)));
      ParserSetIntValueByKeyByHandle(qmUrIn, 'ord'+IntToStr(qmUrK), ParserGetIntValueByKeyByHandle(qmUrUi, 'ord'+IntToStr(qmUrK)));
   end;
   StateMachineExecuteState(GetTriggerManagerStateMachineHandle('qm_core'), 'qmAbRules', 0);
end;

//! Where a key setting's new key is taken already (M10 task 2); '' when it
//! is free. In this order: a key the game refuses in its own hotkey window
//! (hotkeysettings.inc:24-79 single keys, :81-133 combinations, compared as
//! IsValidKey does, :135-160); another key setting of this mod in the edit
//! copy; a key setting of another mod that is active after Apply; a key the
//! effective hotkeys.cfg binds - the player's <save>\hotkeys\hotkeys.cfg,
//! else .\data\game\var\hotkeys.cfg, the files RegisterShortcuts reads
//! (registershortcuts.inc:187-192); a key the effective registershortcuts.inc
//! registers by its literal name (a mod that reads its key from a setting
//! registers none). The setting's own default and stored key are its own.
//! Both game files are read through the engine's parser, the way the game
//! reads them (.\data goes through the mod overlay).
procedure qmUaKeyCheck(const qmUkKey : String; const qmUkK : Integer; var qmUkWhy : String);
begin
   var qmUkUi : Integer = ParserSelectByKey('qm_ui');
   var qmUkS : String = IntToStr(qmUkK);
   var qmUkJ : Integer;
   var qmUkI : Integer;
   var qmUkM : Integer;
   var qmUkAb : Integer = ParserSelectByKey('qm_about');
   var qmUkSet : Integer = ParserSelectByKey('qm_settings');
   var qmUkCh : Integer;
   var qmUkSk : String;
   var qmUkV : String;
   qmUkWhy := '';
   // The reasons a key is not taken.
   if SameText(qmUkKey, ParserGetValueByKeyByHandle(qmUkUi, 'odf'+qmUkS)) or SameText(qmUkKey, ParserGetValueByKeyByHandle(qmUkUi, 'ovs'+qmUkS)) then
   exit;
   qmKeyForbidden(qmUkKey, qmUkWhy);
   if (qmUkWhy<>'') then
   exit;
   for qmUkJ:=0 to ParserGetIntValueByKeyByHandle(qmUkUi, 'optn')-1 do
   if (qmUkJ<>qmUkK) and (ParserGetValueByKeyByHandle(qmUkUi, 'oty'+IntToStr(qmUkJ))='key') and SameText(ParserGetValueByKeyByHandle(qmUkUi, 'ov'+IntToStr(qmUkJ)), qmUkKey) then
   begin
      qmUkWhy := 'it is '+ParserGetValueByKeyByHandle(qmUkUi, 'olb'+IntToStr(qmUkJ))+' already';
      exit;
   end;
   if (qmUkAb<>0) and (qmUkSet<>0) then
   for qmUkI:=0 to ParserGetIntValueByKeyByHandle(qmUkUi, 'n')-1 do
   if (qmUkI<>ParserGetIntValueByKeyByHandle(qmUkUi, 'opt')) and (ParserGetIntValueByKeyByHandle(qmUkUi, 'pe'+IntToStr(qmUkI))=1) and (ParserGetIntValueByKeyByHandle(qmUkUi, 'abs'+IntToStr(qmUkI))>0) then
   begin
      qmUkCh := ParserSelectByHandleByKey(qmUkSet, ParserGetValueByKeyByHandle(qmUkUi, 'abid'+IntToStr(qmUkI)));
      if (qmUkCh<>0) then
      for qmUkM:=0 to ParserGetIntValueByKeyByHandle(qmUkUi, 'abs'+IntToStr(qmUkI))-1 do
      begin
         qmUkSk := IntToStr(qmUkI)+'_'+IntToStr(qmUkM);
         if (ParserGetValueByKeyByHandle(qmUkAb, 'sty'+qmUkSk)='key') then
         begin
            qmUkV := ParserGetValueByKeyByHandle(qmUkCh, ParserGetValueByKeyByHandle(qmUkAb, 'sid'+qmUkSk));
            if SameText(qmUkV, qmUkKey) and (qmUkWhy='') then
            qmUkWhy := ParserGetValueByKeyByHandle(qmUkUi, 'name'+IntToStr(qmUkI))+' uses it for '+ParserGetValueByKeyByHandle(qmUkAb, 'slb'+qmUkSk);
         end;
      end;
   end;
   if (qmUkWhy<>'') then
   exit;
   qmKeyGameUse(qmUkKey, qmUkWhy);
end;

ParserSetValueByKeyByHandle(qmUaUi, 'cmd', '');
ParserSetIntValueByKeyByHandle(qmUaUi, 'cmds', ParserGetIntValueByKeyByHandle(qmUaUi, 'cmds')+1);
// What the filter box holds now; the redraw puts it back.
ParserSetValueByKeyByHandle(qmUaUi, 'typed', qmUaText);
// Esc and Enter mean different things in the dialog and in the Report view.
if ((qmUaCmd='esc') or (qmUaCmd='enter')) and (qmUaMode=3) then
qmUaCmd := 'ok';
//! While the activation check runs (qmTrial, on the next frame) the pending
//! set stays the one it checks: the commands that change it wait.
if (ParserGetIntValueByKeyByHandle(qmUaUi, 'trpend')=1) then
if (qmUaCmd='activate') or (qmUaCmd='deactivate') or (qmUaCmd='up') or (qmUaCmd='down') or (qmUaCmd='move') or (qmUaCmd='apply') or (qmUaCmd='autosort') or (qmUaCmd='confirm') then
begin
   // The message while the activation check runs.
   ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Still checking the last change; a moment.');
   //! The check runs on the next frame, or from the window when no frame
   //! ticks (qmPump): one still unanswered five seconds after it was asked
   //! did not run at all, and the window says so instead of "a moment" for
   //! ever (hands-on, 2026-10-10: minutes of it, DoProgress had not compiled).
   var qmUaWrt : Integer = ParserSelectByKey('qm_rt');
   var qmUaWait : Integer = 0;
   if (qmUaWrt<>0) then
   qmUaWait := Floor(_misc_GetRealTime*10)-ParserGetIntValueByKeyByHandle(qmUaWrt, 'trat');
   if (qmUaWait>=50) then
   // The message when the activation check never ran.
   ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'The check did not run: the game is not running Quartermaster''s part of the main menu. Close the game and start it again; nothing was changed.');
   qmLog('ui '+qmUaCmd+' waits: the activation check runs, asked '+IntToStr(qmUaWait)+' tenths ago');
   qmUaCmd := '';
   qmUaDone := True;
end;
//! The activation check has answered (qmTick ran qmTrial): a row it
//! refuses goes back to inactive with the reason; after the check of Apply,
//! Apply goes on below with the answer.
if (qmUaCmd='trialdone') then
begin
   qmUaDone := True;
   ParserSetIntValueByKeyByHandle(qmUaUi, 'trpend', 0);
   var qmUaTr : Integer = ParserGetIntValueByKeyByHandle(qmUaUi, 'trrow');
   var qmUaTst : String = ParserGetValueByKeyByHandle(qmUaUi, 'trst');
   // The messages of the activation check.
   if (qmUaTr>=0) and (qmUaTr<qmUaN) then
   begin
      qmUaS := IntToStr(qmUaTr);
      if (qmUaTst='FAIL') then
      begin
         ParserSetIntValueByKeyByHandle(qmUaUi, 'pe'+qmUaS, 0);
         ParserSetIntValueByKeyByHandle(qmUaUi, 'side', 0);
         ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Not activated: '+ParserGetValueByKeyByHandle(qmUaUi, 'tr0')+'.');
         qmLog('ui activate refused row='+qmUaS+' by the check: '+ParserGetValueByKeyByHandle(qmUaUi, 'tr0'));
      end
      else
      if (qmUaTst='WARN') then
      ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Activated. Note: '+ParserGetValueByKeyByHandle(qmUaUi, 'tr0')+'.')
      else
      if (qmUaTst='SKIP') then
      ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Activated without the check: '+ParserGetValueByKeyByHandle(qmUaUi, 'tr0')+'.')
      else
      //! What only a start with the mod's own scripts can judge (qmTrial
      //! trlater) is said, and is no warning.
      if (ParserGetIntValueByKeyByHandle(qmUaUi, 'trlater')>0) then
      ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Checked: '+ParserGetValueByKeyByHandle(qmUaUi, 'name'+qmUaS)+' works with the active mods. '+IntToStr(ParserGetIntValueByKeyByHandle(qmUaUi, 'trlater'))+' of its files use its own scripts and are checked when the game restarts.')
      else
      ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Checked: '+ParserGetValueByKeyByHandle(qmUaUi, 'name'+qmUaS)+' works with the active mods.');
      //! The check's word for the row (tck<i>): ShowQmManager shows OK or WARN
      //! beside the row's + until Apply, instead of PENDING (since
      //! 2026-10-01); none for a SKIP or a refused row. A new load order
      //! keeps it: Apply checks the whole set in that order again and refuses
      //! what would not work (a word cleared by Move up only confused).
      if ((qmUaTst='OK') or (qmUaTst='WARN')) and (ParserGetIntValueByKeyByHandle(qmUaUi, 'pe'+qmUaS)=1) then
      ParserSetValueByKeyByHandle(qmUaUi, 'tck'+qmUaS, qmUaTst)
      else
      ParserSetValueByKeyByHandle(qmUaUi, 'tck'+qmUaS, '');
      StateMachineExecuteState(qmUaCore, 'qmUiDetails', 0);
      qmLog('ui trial answered row='+qmUaS+' st='+qmUaTst+' pending='+IntToStr(ParserGetIntValueByKeyByHandle(qmUaUi, 'pe'+qmUaS)));
   end
   else
   begin
      qmLog('ui trial answered for Apply st='+qmUaTst);
      if (ParserGetIntValueByKeyByHandle(qmUaUi, 'trapply')=1) then
      begin
         ParserSetIntValueByKeyByHandle(qmUaUi, 'trapply', 0);
         qmUaCmd := 'apply';
      end;
   end;
end;
if (qmUaCmd='esc') then
begin
   if (qmUaMode=1) then
   qmUaCmd := 'cancel'
   else
   if (qmUaMode=0) and (ParserGetIntValueByKeyByHandle(qmUaUi, 'panel')=1) then
   qmUaCmd := 'report'
   else
   if (qmUaMode=0) and (ParserGetIntValueByKeyByHandle(qmUaUi, 'panel')=2) and (ParserGetIntValueByKeyByHandle(qmUaUi, 'optcap')>=0) then
   begin
      qmUaCmd := 'optkey';
      qmUaText := '';
   end
   else
   if (qmUaMode=0) and (ParserGetIntValueByKeyByHandle(qmUaUi, 'panel')=2) then
   qmUaCmd := 'optcancel'
   else
   if (qmUaMode=4) then
   qmUaCmd := 'nmcancel'
   else
   if (qmUaMode=0) and (ParserGetIntValueByKeyByHandle(qmUaUi, 'panel')=3) then
   qmUaCmd := 'mfback'
   else
   qmUaCmd := 'close';
end;
if (qmUaCmd='enter') then
begin
   if (qmUaMode=1) then
   qmUaCmd := 'confirm'
   else
   if (qmUaMode=4) then
   qmUaCmd := 'nmcreate'
   else
   qmUaCmd := 'filter';
end;
// While the confirm dialog is open only its answers count: its mask swallows
// clicks, and a stray command must not change the rows under it. While the
// restart notice shows, nothing but close does.
if (qmUaMode=1) and (qmUaCmd<>'confirm') and (qmUaCmd<>'cancel') and (qmUaCmd<>'close') then
begin
   qmLog('ui cmd '+qmUaCmd+' ignored while the confirm dialog is open');
   exit;
end;
if (qmUaMode=4) and (qmUaCmd<>'nmtype') and (qmUaCmd<>'nmexcl') and (qmUaCmd<>'nmcreate') and (qmUaCmd<>'nmcancel') and (qmUaCmd<>'filter') and (qmUaCmd<>'close') then
begin
   qmLog('ui cmd '+qmUaCmd+' ignored while the new-mod dialog is open');
   exit;
end;
if (qmUaMode=2) and (qmUaCmd<>'close') then
begin
   qmLog('ui cmd '+qmUaCmd+' ignored while the restart notice shows');
   exit;
end;
//! `open` under the notice draws it again (qmTick after a rebuilt menu, or
//! the main menu button): until 2026-10-01 it was ignored, and a notice
//! whose window the game had rebuilt away left the manager unopenable.
if (qmUaMode=3) and (qmUaCmd<>'ok') and (qmUaCmd<>'close') and (qmUaCmd<>'open') then
begin
   qmLog('ui cmd '+qmUaCmd+' ignored while the guard notice shows');
   exit;
end;
if (qmUaMode=3) and (qmUaCmd='open') then
ParserSetIntValueByKeyByHandle(qmUaUi, 'gdopen', 1);
if (qmUaCmd='ok') then
begin
   qmUaDone := True;
   ParserSetIntValueByKeyByHandle(qmUaUi, 'mode', 0);
   qmLog('ui guard notice closed');
end;
if (qmUaCmd='open') then
begin
   qmUaDone := True;
   StateMachineExecuteState(qmUaCore, 'qmUiModel', 0);
   ParserSetIntValueByKeyByHandle(qmUaUi, 'sel', -1);
   ParserSetIntValueByKeyByHandle(qmUaUi, 'side', 0);
   ParserSetIntValueByKeyByHandle(qmUaUi, 'panel', 0);
   ParserSetIntValueByKeyByHandle(qmUaUi, 'mode', 0);
   ParserSetIntValueByKeyByHandle(qmUaUi, 'close', 0);
   ParserSetIntValueByKeyByHandle(qmUaUi, 'topi', 0);
   ParserSetIntValueByKeyByHandle(qmUaUi, 'topa', 0);
   ParserSetValueByKeyByHandle(qmUaUi, 'filter', '');
   ParserSetValueByKeyByHandle(qmUaUi, 'typed', '');
   //! A fresh window has no activation check waiting: a request the last
   //! one left is dropped, so its answer cannot land on these rows.
   ParserSetIntValueByKeyByHandle(qmUaUi, 'trpend', 0);
   ParserSetIntValueByKeyByHandle(qmUaUi, 'trapply', 0);
   ParserSetValueByKeyByHandle(qmUaUi, 'trsig', '');
   var qmUaOrt : Integer = ParserSelectByKey('qm_rt');
   if (qmUaOrt<>0) then
   ParserSetIntValueByKeyByHandle(qmUaOrt, 'trdone', ParserGetIntValueByKeyByHandle(qmUaOrt, 'trq'));
   ParserSetValueByKeyByHandle(qmUaUi, 'msg', '');
   //! The guard's notice (qmTick sets gdopen once, after a start the guard
   //! restarted): its lines from qm_glob, one per mod switched off.
   ParserSetIntValueByKeyByHandle(qmUaUi, 'gdln', 0);
   if (ParserGetIntValueByKeyByHandle(qmUaUi, 'gdopen')=1) then
   begin
      ParserSetIntValueByKeyByHandle(qmUaUi, 'gdopen', 0);
      var qmUaGl : Integer = ParserSelectByKey('qm_glob');
      var qmUaGp : String;
      if (qmUaGl<>0) then
      if (ParserGetIntValueByKeyByHandle(qmUaGl, 'gdn')>0) then
      begin
         for qmUaK:=0 to ParserGetIntValueByKeyByHandle(qmUaGl, 'gdn')-1 do
         if (qmUaK<qmUaConfMax) then
         begin
            qmUaS := IntToStr(qmUaK);
            qmGlobPath(ParserGetValueByKeyByHandle(qmUaGl, 'gdf'+qmUaS), qmUaGp);
            // The lines of the guard's notice: a clash, or a mod a step after a
            // failed start switched off (no file; the notice's text says why).
            if (ParserGetValueByKeyByHandle(qmUaGl, 'gdf'+qmUaS)='') then
            ParserSetValueByKeyByHandle(qmUaUi, 'gdl'+qmUaS, ParserGetValueByKeyByHandle(qmUaGl, 'gdt'+qmUaS))
            else
            ParserSetValueByKeyByHandle(qmUaUi, 'gdl'+qmUaS, ParserGetValueByKeyByHandle(qmUaGl, 'gdt'+qmUaS)+' - ships '+qmUaGp+', like '+ParserGetValueByKeyByHandle(qmUaGl, 'gdo'+qmUaS));
            ParserSetIntValueByKeyByHandle(qmUaUi, 'gdln', qmUaK+1);
         end;
         ParserSetValueByKeyByHandle(qmUaUi, 'gdwhy', ParserGetValueByKeyByHandle(qmUaGl, 'gdwhy'));
         ParserSetIntValueByKeyByHandle(qmUaUi, 'mode', 3);
      end;
   end;
   StateMachineExecuteState(qmUaCore, 'qmUiDetails', 0);
   ParserSetIntValueByKeyByHandle(qmUaUi, 'opens', ParserGetIntValueByKeyByHandle(qmUaUi, 'opens')+1);
   qmLog('ui open n='+IntToStr(ParserGetIntValueByKeyByHandle(qmUaUi, 'n'))+' opens='+IntToStr(ParserGetIntValueByKeyByHandle(qmUaUi, 'opens')));
end;
if (qmUaCmd='select') then
begin
   qmUaDone := True;
   if (qmUaArg>=0) and (qmUaArg<qmUaN) then
   begin
      ParserSetIntValueByKeyByHandle(qmUaUi, 'sel', qmUaArg);
      ParserSetIntValueByKeyByHandle(qmUaUi, 'side', ParserGetIntValueByKeyByHandle(qmUaUi, 'argside'));
      StateMachineExecuteState(qmUaCore, 'qmUiDetails', 0);
      qmLog('ui select row='+IntToStr(qmUaArg)+' side='+IntToStr(ParserGetIntValueByKeyByHandle(qmUaUi, 'side')));
   end
   else
   qmLog('ui select ignored: row '+IntToStr(qmUaArg)+' is not in 0..'+IntToStr(qmUaN-1));
end;
if (qmUaCmd='activate') or (qmUaCmd='deactivate') then
begin
   qmUaDone := True;
   // The hints of activate and deactivate.
   if (qmUaSel<0) or (qmUaSel>=qmUaN) then
   ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Select a mod first.')
   else
   begin
      qmUaS := IntToStr(qmUaSel);
      if (qmUaCmd='activate') then
      begin
         if (ParserGetIntValueByKeyByHandle(qmUaUi, 'pe'+qmUaS)=1) then
         ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'This mod is active already.')
         else
         begin
            ParserSetIntValueByKeyByHandle(qmUaUi, 'pe'+qmUaS, 1);
            ParserSetValueByKeyByHandle(qmUaUi, 'tck'+qmUaS, '');
            ParserSetIntValueByKeyByHandle(qmUaUi, 'side', 1);
            ParserSetValueByKeyByHandle(qmUaUi, 'msg', '');
            //! An about.cfg rule the activation would break (M8 task 4: a FAIL
            //! blocks the move): a requirement not active, a second total
            //! conversion, a taken exclusive slot, an incompatible mod.
            qmUaRules;
            var qmUaAr : Integer = ParserSelectByKey('qm_abr');
            var qmUaBlk : String = '';
            for qmUaK:=0 to ParserGetIntValueByKeyByHandle(qmUaAr, 'n')-1 do
            if (qmUaBlk='') and (ParserGetValueByKeyByHandle(qmUaAr, 'tag'+IntToStr(qmUaK))='FAIL') then
            if (ParserGetIntValueByKeyByHandle(qmUaAr, 'row'+IntToStr(qmUaK))=qmUaSel) or (ParserGetIntValueByKeyByHandle(qmUaAr, 'oth'+IntToStr(qmUaK))=qmUaSel) then
            qmUaBlk := ParserGetValueByKeyByHandle(qmUaAr, 'text'+IntToStr(qmUaK));
            if (qmUaBlk<>'') then
            begin
               ParserSetIntValueByKeyByHandle(qmUaUi, 'pe'+qmUaS, 0);
               ParserSetIntValueByKeyByHandle(qmUaUi, 'side', 0);
               // The message of a refused activation.
               ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Not activated: '+qmUaBlk+'.');
               qmLog('ui activate refused row='+qmUaS+': '+qmUaBlk);
            end
            else
            //! The rules allow it: the activation check of the new set
            //! (qmTrial) decides on the next frame, `trialdone` above.
            if qmUaTrialAsk(qmUaSel) then
            begin
               // The message while the activation check runs.
               ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Checking '+ParserGetValueByKeyByHandle(qmUaUi, 'name'+qmUaS)+' with the active mods...');
               qmLog('ui activate row='+qmUaS+': the activation check is asked');
            end;
         end;
      end
      else
      begin
         // Quartermaster is switched off where the player switched it on,
         // in the game's own mod list (plan S1: the rescue is one click there).
         if (qmUaSel=qmUaSelf) then
         ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Quartermaster cannot switch itself off here; use the game''s own Mod Manager (modman.exe).')
         else
         if (ParserGetIntValueByKeyByHandle(qmUaUi, 'pe'+qmUaS)=0) then
         ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'This mod is not active.')
         else
         begin
            ParserSetIntValueByKeyByHandle(qmUaUi, 'pe'+qmUaS, 0);
            ParserSetValueByKeyByHandle(qmUaUi, 'tck'+qmUaS, '');
            ParserSetIntValueByKeyByHandle(qmUaUi, 'side', 0);
            ParserSetValueByKeyByHandle(qmUaUi, 'msg', '');
         end;
      end;
      StateMachineExecuteState(qmUaCore, 'qmUiDetails', 0);
      qmLog('ui '+qmUaCmd+' row='+qmUaS+' pending='+IntToStr(ParserGetIntValueByKeyByHandle(qmUaUi, 'pe'+qmUaS))+' engine='+IntToStr(ParserGetIntValueByKeyByHandle(qmUaUi, 'en'+qmUaS))+' dir='+ParserGetValueByKeyByHandle(qmUaUi, 'dir'+qmUaS));
   end;
end;
//! The load-order commands belong to qmUiOrder (the keys are agreed there):
//! it reads `ocmd`, `arg` (the row) and `argto` (the place a drag drops it
//! at) and writes ord<k>, ordchg, omoved and msg. The moved row stays
//! selected in the Active list.
if (qmUaCmd='up') or (qmUaCmd='down') or (qmUaCmd='move') then
begin
   qmUaDone := True;
   ParserSetValueByKeyByHandle(qmUaUi, 'ocmd', qmUaCmd);
   StateMachineExecuteState(qmUaCore, 'qmUiOrder', 0);
   if (ParserGetIntValueByKeyByHandle(qmUaUi, 'omoved')=1) then
   begin
      ParserSetIntValueByKeyByHandle(qmUaUi, 'sel', qmUaArg);
      ParserSetIntValueByKeyByHandle(qmUaUi, 'side', 1);
   end;
   StateMachineExecuteState(qmUaCore, 'qmUiDetails', 0);
end;
if (qmUaCmd='report') then
begin
   qmUaDone := True;
   ParserSetIntValueByKeyByHandle(qmUaUi, 'panel', 1-ParserGetIntValueByKeyByHandle(qmUaUi, 'panel'));
   qmLog('ui report panel='+IntToStr(ParserGetIntValueByKeyByHandle(qmUaUi, 'panel')));
end;
if (qmUaCmd='apply') then
begin
   qmUaDone := True;
   qmUaChg := 0;
   for qmUaI:=0 to qmUaN-1 do
   if (ParserGetIntValueByKeyByHandle(qmUaUi, 'pe'+IntToStr(qmUaI))<>ParserGetIntValueByKeyByHandle(qmUaUi, 'en'+IntToStr(qmUaI))) then
   qmUaChg := qmUaChg+1;
   // Message when there is nothing to apply, and the lines of
   // the confirm dialog (+ activated, - deactivated, the new load order).
   //! Rows Apply switches on are checked together first (qmTrial for row
   //! -1), unless the last check was that one, for this very set.
   var qmUaNewOn : Integer = 0;
   var qmUaSigNow : String;
   for qmUaI:=0 to qmUaN-1 do
   if (ParserGetIntValueByKeyByHandle(qmUaUi, 'pe'+IntToStr(qmUaI))=1) and (ParserGetIntValueByKeyByHandle(qmUaUi, 'en'+IntToStr(qmUaI))=0) then
   qmUaNewOn := qmUaNewOn+1;
   qmUaSig(qmUaSigNow);
   var qmUaChecked : Boolean = (ParserGetIntValueByKeyByHandle(qmUaUi, 'trrow')=-1) and (ParserGetValueByKeyByHandle(qmUaUi, 'trsig')=qmUaSigNow) and (ParserGetValueByKeyByHandle(qmUaUi, 'trst')<>'');
   if (qmUaChg=0) and (ParserGetIntValueByKeyByHandle(qmUaUi, 'ordchg')<>1) then
   ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Nothing to apply.')
   else
   if (qmUaNewOn>0) and (not qmUaChecked) and qmUaTrialAsk(-1) then
   begin
      ParserSetIntValueByKeyByHandle(qmUaUi, 'trapply', 1);
      // The message while the activation check runs.
      ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Checking the mods Apply switches on...');
      qmLog('ui apply waits for the activation check of '+IntToStr(qmUaNewOn)+' mod(s)');
   end
   else
   begin
      ParserSetIntValueByKeyByHandle(qmUaUi, 'mode', 1);
      // A pending set with a broken about.cfg rule: the dialog lists them and
      // refuses (pa<k> are from the check after the last command; confbrule
      // says whether rule lines are among them, for the dialog's note). A
      // global-script clash is a note further down, not a refusal (0.1.3).
      ParserSetIntValueByKeyByHandle(qmUaUi, 'confblk', 0);
      ParserSetIntValueByKeyByHandle(qmUaUi, 'confbrule', 0);
      for qmUaK:=0 to ParserGetIntValueByKeyByHandle(qmUaUi, 'pan')-1 do
      if (ParserGetValueByKeyByHandle(qmUaUi, 'pat'+IntToStr(qmUaK))='FAIL') and (ParserGetIntValueByKeyByHandle(qmUaUi, 'confblk')<qmUaConfMax) then
      begin
         ParserSetValueByKeyByHandle(qmUaUi, 'confb'+IntToStr(ParserGetIntValueByKeyByHandle(qmUaUi, 'confblk')), ParserGetValueByKeyByHandle(qmUaUi, 'pa'+IntToStr(qmUaK)));
         ParserSetIntValueByKeyByHandle(qmUaUi, 'confblk', ParserGetIntValueByKeyByHandle(qmUaUi, 'confblk')+1);
         ParserSetIntValueByKeyByHandle(qmUaUi, 'confbrule', 1);
      end;
      //! What the activation check of this set refused (qmTrial FAIL lines).
      if (qmUaChecked) then
      for qmUaK:=0 to ParserGetIntValueByKeyByHandle(qmUaUi, 'trn')-1 do
      if (ParserGetValueByKeyByHandle(qmUaUi, 'trt'+IntToStr(qmUaK))='FAIL') and (ParserGetIntValueByKeyByHandle(qmUaUi, 'confblk')<qmUaConfMax) then
      begin
         ParserSetValueByKeyByHandle(qmUaUi, 'confb'+IntToStr(ParserGetIntValueByKeyByHandle(qmUaUi, 'confblk')), ParserGetValueByKeyByHandle(qmUaUi, 'tr'+IntToStr(qmUaK)));
         ParserSetIntValueByKeyByHandle(qmUaUi, 'confblk', ParserGetIntValueByKeyByHandle(qmUaUi, 'confblk')+1);
         ParserSetIntValueByKeyByHandle(qmUaUi, 'confbrule', 1);
      end;
      ParserSetIntValueByKeyByHandle(qmUaUi, 'confchg', qmUaChg);
      ParserSetIntValueByKeyByHandle(qmUaUi, 'confn', 0);
      ParserSetIntValueByKeyByHandle(qmUaUi, 'confon', 0);
      ParserSetIntValueByKeyByHandle(qmUaUi, 'confordchg', ParserGetIntValueByKeyByHandle(qmUaUi, 'ordchg'));
      for qmUaK:=0 to qmUaN-1 do
      begin
         qmUaS := IntToStr(ParserGetIntValueByKeyByHandle(qmUaUi, 'ord'+IntToStr(qmUaK)));
         if (ParserGetIntValueByKeyByHandle(qmUaUi, 'pe'+qmUaS)=1) and (ParserGetIntValueByKeyByHandle(qmUaUi, 'en'+qmUaS)=0) then
         qmUaConf('+ '+ParserGetValueByKeyByHandle(qmUaUi, 'name'+qmUaS));
      end;
      for qmUaK:=0 to qmUaN-1 do
      begin
         qmUaS := IntToStr(ParserGetIntValueByKeyByHandle(qmUaUi, 'ord'+IntToStr(qmUaK)));
         if (ParserGetIntValueByKeyByHandle(qmUaUi, 'pe'+qmUaS)=0) and (ParserGetIntValueByKeyByHandle(qmUaUi, 'en'+qmUaS)=1) then
         qmUaConf('- '+ParserGetValueByKeyByHandle(qmUaUi, 'name'+qmUaS));
      end;
      // A global-script clash of the pending set is asked about (pc<k>).
      for qmUaK:=0 to ParserGetIntValueByKeyByHandle(qmUaUi, 'pcn')-1 do
      qmUaConf('Note: '+ParserGetValueByKeyByHandle(qmUaUi, 'pc'+IntToStr(qmUaK))+'; if the game does not start with both, Quartermaster switches back at the next start.');
      // An about.cfg WARN of the pending set is asked about, not refused: it
      // goes into the dialog's list (M8 task 4: WARN asks for confirmation).
      // The prefix of a warning line.
      for qmUaK:=0 to ParserGetIntValueByKeyByHandle(qmUaUi, 'pan')-1 do
      if (ParserGetValueByKeyByHandle(qmUaUi, 'pat'+IntToStr(qmUaK))='WARN') then
      qmUaConf('Note: '+ParserGetValueByKeyByHandle(qmUaUi, 'pa'+IntToStr(qmUaK)));
      if (qmUaChecked) then
      for qmUaK:=0 to ParserGetIntValueByKeyByHandle(qmUaUi, 'trn')-1 do
      if (ParserGetValueByKeyByHandle(qmUaUi, 'trt'+IntToStr(qmUaK))='WARN') then
      qmUaConf('Note: '+ParserGetValueByKeyByHandle(qmUaUi, 'tr'+IntToStr(qmUaK)));
      // The load order after Apply, always: it is the second column.
      qmUaPlace := 0;
      for qmUaK:=0 to qmUaN-1 do
      begin
         qmUaS := IntToStr(ParserGetIntValueByKeyByHandle(qmUaUi, 'ord'+IntToStr(qmUaK)));
         if (ParserGetIntValueByKeyByHandle(qmUaUi, 'pe'+qmUaS)=1) then
         begin
            qmUaPlace := qmUaPlace+1;
            qmUaConfOrd(IntToStr(qmUaPlace)+'. '+ParserGetValueByKeyByHandle(qmUaUi, 'name'+qmUaS));
         end;
      end;
      qmUaCn := ParserGetIntValueByKeyByHandle(qmUaUi, 'confn');
      if (qmUaCn>qmUaConfMax) then
      begin
         ParserSetValueByKeyByHandle(qmUaUi, 'conf'+IntToStr(qmUaConfMax-1), '... and '+IntToStr(qmUaCn-qmUaConfMax+1)+' more');
         ParserSetIntValueByKeyByHandle(qmUaUi, 'confn', qmUaConfMax);
      end;
      qmUaCn := ParserGetIntValueByKeyByHandle(qmUaUi, 'confon');
      if (qmUaCn>qmUaConfMax) then
      begin
         ParserSetValueByKeyByHandle(qmUaUi, 'confo'+IntToStr(qmUaConfMax-1), '... and '+IntToStr(qmUaCn-qmUaConfMax+1)+' more');
         ParserSetIntValueByKeyByHandle(qmUaUi, 'confon', qmUaConfMax);
      end;
   end;
   qmLog('ui apply asked changes='+IntToStr(qmUaChg)+' order='+IntToStr(ParserGetIntValueByKeyByHandle(qmUaUi, 'ordchg'))+' mode='+IntToStr(ParserGetIntValueByKeyByHandle(qmUaUi, 'mode'))+' lines='+IntToStr(ParserGetIntValueByKeyByHandle(qmUaUi, 'confn')));
end;
if (qmUaCmd='confirm') then
begin
   qmUaDone := True;
   if (qmUaMode=1) and (ParserGetIntValueByKeyByHandle(qmUaUi, 'confblk')>0) then
   begin
      ParserSetIntValueByKeyByHandle(qmUaUi, 'mode', 0);
      // The message of a refused Apply (about.cfg rules and the activation
      // check only since 0.1.3).
      ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Not applied: first fix what the list showed.');
      qmLog('ui confirm refused: '+IntToStr(ParserGetIntValueByKeyByHandle(qmUaUi, 'confblk'))+' problem(s), rules='+IntToStr(ParserGetIntValueByKeyByHandle(qmUaUi, 'confbrule')));
   end
   else
   if (qmUaMode=1) then
   begin
      ParserSetIntValueByKeyByHandle(qmUaUi, 'mode', 0);
      qmLog('ui confirm');
      StateMachineExecuteState(qmUaCore, 'qmUiApply', 0);
      // A recorded request shows the restart notice until the game closes.
      var qmUaRt : Integer = ParserSelectByKey('qm_rt');
      if (qmUaRt<>0) then
      if (ParserGetIntValueByKeyByHandle(qmUaRt, 'uiapply')=1) then
      ParserSetIntValueByKeyByHandle(qmUaUi, 'mode', 2);
   end;
end;
if (qmUaCmd='cancel') then
begin
   qmUaDone := True;
   ParserSetIntValueByKeyByHandle(qmUaUi, 'mode', 0);
   // Message after the confirm dialog was cancelled.
   ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Apply cancelled.');
   qmLog('ui cancel');
end;
//! The filter follows every keystroke (EventQmManager sends it on a key's
//! release when the box's text changed, as eventloadgame.inc:77-99 redraws
//! on every key); the box's edit control survives the redraw with its caret
//! (ShowQmManager keeps it in a layer of its own).
//! Create mod (plan G17, M11; mode 4): a name, a type and an exclusive slot;
//! Create leaves the request in qm_rt (mfreq new) for qmTick - qmModFiles
//! writes mods\<folder>\ - since the window writes nothing itself. The
//! folder is the name with every character outside A-Z a-z 0-9 _ dropped, a
//! space as `_`, at most 40, a letter first (ref/createmod.py folder_of).
//! Keys: nmname (the name as typed in the dialog's box, layer nbox),
//! nmfolder, nmtype (0 mod, 1 total conversion), nmexcl (0 none, else a
//! slot of ref/about.py SLOTS).
procedure qmUaFolder(const qmUfN : String; var qmUfOut : String);
begin
   var qmUfI : Integer;
   var qmUfC : String;
   qmUfOut := '';
   for qmUfI:=1 to StrLength(qmUfN) do
   begin
      qmUfC := SubStr(qmUfN, qmUfI, 1);
      if (qmUfC=' ') then
      qmUfC := '_';
      if (StrPos(qmUfC, 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_')>0) and (StrLength(qmUfOut)<40) then
      qmUfOut := qmUfOut+qmUfC;
   end;
   while (qmUfOut<>'') and (StrPos(SubStr(qmUfOut, 1, 1), 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz')=0) do
   qmUfOut := SubStr(qmUfOut, 2, StrLength(qmUfOut)-1);
end;
if (qmUaCmd='newmod') then
begin
   qmUaDone := True;
   ParserSetIntValueByKeyByHandle(qmUaUi, 'mode', 4);
   ParserSetValueByKeyByHandle(qmUaUi, 'nmname', '');
   ParserSetValueByKeyByHandle(qmUaUi, 'nmfolder', '');
   ParserSetIntValueByKeyByHandle(qmUaUi, 'nmtype', 0);
   ParserSetIntValueByKeyByHandle(qmUaUi, 'nmexcl', 0);
   ParserSetValueByKeyByHandle(qmUaUi, 'msg', '');
   qmLog('ui new mod dialog');
end;
if (qmUaCmd='nmtype') then
begin
   qmUaDone := True;
   ParserSetIntValueByKeyByHandle(qmUaUi, 'nmtype', 1-ParserGetIntValueByKeyByHandle(qmUaUi, 'nmtype'));
end;
if (qmUaCmd='nmexcl') then
begin
   qmUaDone := True;
   ParserSetIntValueByKeyByHandle(qmUaUi, 'nmexcl', (ParserGetIntValueByKeyByHandle(qmUaUi, 'nmexcl')+1) mod 9);
end;
//! Closing the dialog gives the filter box its own text back: every command
//! stores the box text it came with as `typed`, and in mode 4 that was the
//! name box's - the filter box showed the name, and its next key filtered
//! the Installed list by it to nothing (run look-msg2, 2026-10-01).
if (qmUaCmd='nmcancel') then
begin
   qmUaDone := True;
   ParserSetIntValueByKeyByHandle(qmUaUi, 'mode', 0);
   ParserSetValueByKeyByHandle(qmUaUi, 'typed', ParserGetValueByKeyByHandle(qmUaUi, 'filter'));
   ParserSetValueByKeyByHandle(qmUaUi, 'msg', '');
end;
if (qmUaCmd='nmcreate') then
begin
   qmUaDone := True;
   var qmUaNf : String = ParserGetValueByKeyByHandle(qmUaUi, 'nmfolder');
   var qmUaNrt : Integer = ParserSelectByKey('qm_rt');
   var qmUaNtaken : Boolean = False;
   var qmUaNs : String;
   for qmUaK:=0 to qmUaN-1 do
   if SameText(ParserGetValueByKeyByHandle(qmUaUi, 'dir'+IntToStr(qmUaK)), 'mods\'+qmUaNf) then
   qmUaNtaken := True;
   // The messages of Create mod in the window.
   if (qmUaNf='') then
   ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Type a name with at least one letter.')
   else
   if (qmUaNtaken) then
   ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'mods\'+qmUaNf+' is a mod already; choose another name.')
   else
   if (qmUaNrt=0) then
   ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Quartermaster did not start here; nothing can be created.')
   else
   begin
      ParserSetValueByKeyByHandle(qmUaNrt, 'mffolder', qmUaNf);
      ParserSetValueByKeyByHandle(qmUaNrt, 'mftitle', ParserGetValueByKeyByHandle(qmUaUi, 'nmname'));
      if (ParserGetIntValueByKeyByHandle(qmUaUi, 'nmtype')=1) then
      ParserSetValueByKeyByHandle(qmUaNrt, 'mftype', 'totalConversion')
      else
      ParserSetValueByKeyByHandle(qmUaNrt, 'mftype', 'mod');
      qmField('|camera|ai|ui|balance|economy|sound|graphics|hotkeys|', '|', ParserGetIntValueByKeyByHandle(qmUaUi, 'nmexcl'), qmUaNs);
      ParserSetValueByKeyByHandle(qmUaNrt, 'mfexcl', qmUaNs);
      ParserSetValueByKeyByHandle(qmUaNrt, 'mfreq', 'new');
      ParserSetIntValueByKeyByHandle(qmUaUi, 'mode', 0);
      ParserSetValueByKeyByHandle(qmUaUi, 'typed', ParserGetValueByKeyByHandle(qmUaUi, 'filter'));
      ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Creating mods\'+qmUaNf+'...');
      qmLog('ui new mod asked folder='+qmUaNf+' type='+ParserGetValueByKeyByHandle(qmUaNrt, 'mftype')+' slot='+qmUaNs);
   end;
end;
//! Mod files (plan G17, M11; panel 3) of the selected local mod: Create
//! about.cfg when it has none, and Edit game file - a vanilla.idx path found
//! by what the filter box holds (three characters at least, 100 matches at
//! most), copied byte for byte into the mod under the same path. Both leave
//! a request in qm_rt for qmTick (qmModFiles). Keys: mfrow, mfhas (1 when the
//! mod has an about.cfg), vq (the query), vn and v<k> vc<k> (the matches
//! and their vanilla.idx class), vsel.
procedure qmUaFind(const qmUvQ : String);
begin
   var qmUvUi : Integer = ParserSelectByKey('qm_ui');
   var qmUvRt : Integer = ParserSelectByKey('qm_rt');
   var qmUvP : Integer;
   var qmUvC : Integer;
   var qmUvK : Integer;
   var qmUvL : String;
   var qmUvN : Integer = 0;
   var qmUvQl : String = StrToLowerCase(qmUvQ);
   var qmUvPath : String;
   ParserSetValueByKeyByHandle(qmUvUi, 'vq', qmUvQ);
   ParserSetIntValueByKeyByHandle(qmUvUi, 'vsel', -1);
   if (StrLength(qmUvQ)>=3) and (qmUvRt<>0) then
   begin
      qmUvP := ParserSelectByKey('qm_vidx_src');
      if (qmUvP=0) then
      qmUvP := ParserCreate('qm_vidx_src');
      ParserClearByHandle(qmUvP);
      ParserLoadFromFileByHandle(qmUvP, ParserGetValueByKeyByHandle(qmUvRt, 'qmdir')+'\data\quartermaster\vanilla.idx');
      qmUvC := ParserSelectByHandleByKey(qmUvP, 'Code');
      if (qmUvC<>0) then
      for qmUvK:=0 to ParserGetCountByHandle(qmUvC)-1 do
      if (qmUvN<100) then
      begin
         qmUvL := ParserGetValueByIndexByHandle(qmUvC, qmUvK);
         if (SubStr(qmUvL, 1, 1)=';') then
         qmUvL := SubStr(qmUvL, 2, StrLength(qmUvL)-1);
         qmField(qmUvL, '|', 0, qmUvPath);
         if (qmUvPath<>'') and (StrPos(qmUvQl, StrToLowerCase(qmUvPath))>0) then
         begin
            ParserSetValueByKeyByHandle(qmUvUi, 'v'+IntToStr(qmUvN), qmUvPath);
            qmField(qmUvL, '|', 3, qmUvPath);
            ParserSetValueByKeyByHandle(qmUvUi, 'vc'+IntToStr(qmUvN), qmUvPath);
            qmUvN := qmUvN+1;
         end;
      end;
      ParserClearByHandle(qmUvP);
   end;
   ParserSetIntValueByKeyByHandle(qmUvUi, 'vn', qmUvN);
end;
if (qmUaCmd='modfiles') then
begin
   qmUaDone := True;
   // The messages of the Mod files view.
   if (qmUaSel<0) or (qmUaSel>=qmUaN) then
   ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Select a local mod first.')
   else
   if (ParserGetValueByKeyByHandle(qmUaUi, 'org'+IntToStr(qmUaSel))<>'Local') and (ParserGetValueByKeyByHandle(qmUaUi, 'org'+IntToStr(qmUaSel))<>'Local copy') then
   ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Only a local mod (a folder in mods\) can be edited here.')
   else
   begin
      ParserSetIntValueByKeyByHandle(qmUaUi, 'panel', 3);
      ParserSetIntValueByKeyByHandle(qmUaUi, 'mfrow', qmUaSel);
      ParserSetIntValueByKeyByHandle(qmUaUi, 'mfhas', 0);
      if (FileAge(ParserGetValueByKeyByHandle(qmUaUi, 'dir'+IntToStr(qmUaSel))+'\about.cfg')<>-1) then
      ParserSetIntValueByKeyByHandle(qmUaUi, 'mfhas', 1);
      ParserSetValueByKeyByHandle(qmUaUi, 'typed', '');
      qmUaFind('');
      ParserSetValueByKeyByHandle(qmUaUi, 'msg', '');
      qmLog('ui mod files row='+IntToStr(qmUaSel)+' about='+IntToStr(ParserGetIntValueByKeyByHandle(qmUaUi, 'mfhas')));
   end;
end;
if (qmUaCmd='filter') and (ParserGetIntValueByKeyByHandle(qmUaUi, 'mode')=4) then
begin
   qmUaDone := True;
   ParserSetValueByKeyByHandle(qmUaUi, 'nmname', qmUaText);
   qmUaFolder(qmUaText, qmUaS);
   ParserSetValueByKeyByHandle(qmUaUi, 'nmfolder', qmUaS);
end;
if (qmUaCmd='filter') and (ParserGetIntValueByKeyByHandle(qmUaUi, 'panel')=3) and (not qmUaDone) then
begin
   qmUaDone := True;
   qmUaFind(qmUaText);
   qmLog('ui mod files find ['+qmUaText+'] matches='+IntToStr(ParserGetIntValueByKeyByHandle(qmUaUi, 'vn')));
end;
if (qmUaCmd='vselect') then
begin
   qmUaDone := True;
   if (qmUaArg>=0) and (qmUaArg<ParserGetIntValueByKeyByHandle(qmUaUi, 'vn')) then
   ParserSetIntValueByKeyByHandle(qmUaUi, 'vsel', qmUaArg);
end;
if (qmUaCmd='mfback') then
begin
   qmUaDone := True;
   ParserSetIntValueByKeyByHandle(qmUaUi, 'panel', 0);
   ParserSetValueByKeyByHandle(qmUaUi, 'typed', ParserGetValueByKeyByHandle(qmUaUi, 'filter'));
   ParserSetValueByKeyByHandle(qmUaUi, 'msg', '');
end;
if (qmUaCmd='mfabout') or (qmUaCmd='mfcopy') then
begin
   qmUaDone := True;
   var qmUaMrt : Integer = ParserSelectByKey('qm_rt');
   var qmUaMrow : Integer = ParserGetIntValueByKeyByHandle(qmUaUi, 'mfrow');
   var qmUaMdir : String = ParserGetValueByKeyByHandle(qmUaUi, 'dir'+IntToStr(qmUaMrow));
   var qmUaMtag, qmUaMd, qmUaMlast, qmUaMtit, qmUaMown, qmUaMdesc, qmUaMtags, qmUaMurl, qmUaMnote : String;
   var qmUaMnumf, qmUaMvis : Integer;
   var qmUaMdis, qmUaMacc, qmUaMban, qmUaMroot : Boolean;
   // The messages of Create about.cfg and Copy into mod.
   if (qmUaMrt=0) or (ParserGetIntValueByKeyByHandle(qmUaUi, 'panel')<>3) then
   ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Quartermaster did not start here; nothing can be written.')
   else
   if (qmUaCmd='mfabout') then
   begin
      if (ParserGetIntValueByKeyByHandle(qmUaUi, 'mfhas')=1) then
      ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'This mod has an about.cfg already.')
      else
      begin
         ModLibraryGetData(qmUaMrow, qmUaMtag, qmUaMd, qmUaMlast, qmUaMtit, qmUaMown, qmUaMdesc, qmUaMtags, qmUaMurl, qmUaMnote, qmUaMnumf, qmUaMvis, qmUaMdis, qmUaMacc, qmUaMban, qmUaMroot);
         ParserSetValueByKeyByHandle(qmUaMrt, 'mfdir', qmUaMdir);
         ParserSetValueByKeyByHandle(qmUaMrt, 'mftitle', ParserGetValueByKeyByHandle(qmUaUi, 'name'+IntToStr(qmUaMrow)));
         ParserSetValueByKeyByHandle(qmUaMrt, 'mftags', qmUaMtags);
         ParserSetIntValueByKeyByHandle(qmUaMrt, 'mfcam', 0);
         if (FileAge(qmUaMdir+'\data\gui\menu.inc\oncamera.inc')<>-1) then
         ParserSetIntValueByKeyByHandle(qmUaMrt, 'mfcam', 1);
         ParserSetValueByKeyByHandle(qmUaMrt, 'mfreq', 'about');
         ParserSetIntValueByKeyByHandle(qmUaUi, 'mfhas', 1);
         ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Writing about.cfg...');
      end;
   end
   else
   begin
      if (ParserGetIntValueByKeyByHandle(qmUaUi, 'vsel')<0) then
      ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Pick a game file in the list first.')
      else
      begin
         ParserSetValueByKeyByHandle(qmUaMrt, 'mfdir', qmUaMdir);
         ParserSetValueByKeyByHandle(qmUaMrt, 'mfrel', ParserGetValueByKeyByHandle(qmUaUi, 'v'+IntToStr(ParserGetIntValueByKeyByHandle(qmUaUi, 'vsel'))));
         ParserSetValueByKeyByHandle(qmUaMrt, 'mfreq', 'copy');
         // The message while a copy is on its way.
         ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Copying...');
      end;
   end;
   qmLog('ui '+qmUaCmd+' dir='+qmUaMdir+' request='+ParserGetValueByKeyByHandle(ParserSelectByKey('qm_rt'), 'mfreq'));
end;
if (qmUaCmd='filter') and (ParserGetIntValueByKeyByHandle(qmUaUi, 'panel')=2) then
begin
   //! In the Options view the box edits the text setting chosen with Edit
   //! (optsel); the filter stays as it was.
   qmUaDone := True;
   qmUaK := ParserGetIntValueByKeyByHandle(qmUaUi, 'optsel');
   if (qmUaK>=0) and (qmUaK<ParserGetIntValueByKeyByHandle(qmUaUi, 'optn')) then
   begin
      qmUaS := IntToStr(qmUaK);
      if (ParserGetIntValueByKeyByHandle(qmUaUi, 'omx'+qmUaS)>0) and (StrLength(qmUaText)>ParserGetIntValueByKeyByHandle(qmUaUi, 'omx'+qmUaS)) then
      begin
         qmUaText := SubStr(qmUaText, 1, ParserGetIntValueByKeyByHandle(qmUaUi, 'omx'+qmUaS));
         ParserSetValueByKeyByHandle(qmUaUi, 'typed', qmUaText);
         // The message of a text cut to its length.
         ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'At most '+IntToStr(ParserGetIntValueByKeyByHandle(qmUaUi, 'omx'+qmUaS))+' characters.');
      end;
      ParserSetValueByKeyByHandle(qmUaUi, 'ov'+qmUaS, qmUaText);
      qmLog('ui option text '+ParserGetValueByKeyByHandle(qmUaUi, 'oid'+qmUaS)+' ['+qmUaText+']');
   end;
end;
if (qmUaCmd='filter') and (not qmUaDone) then
begin
   qmUaDone := True;
   if (ParserGetValueByKeyByHandle(qmUaUi, 'filter')<>qmUaText) then
   ParserSetIntValueByKeyByHandle(qmUaUi, 'topi', 0);
   ParserSetValueByKeyByHandle(qmUaUi, 'filter', qmUaText);
   qmLog('ui filter ['+qmUaText+']');
end;
//! The Options view (plan G16, M10; panel 2): the settings the selected mod
//! declares in its about.cfg (qm_about, rows matched by qmUiModel `abok`),
//! edited in a copy - ov<k> - and written to qm_settings and
//! <save>\quartermaster\settings.cfg only on Accept, the way vanilla's
//! settings window keeps gProfileTmp until Accept (eventsettings.inc:692-739).
//! Keys: opt (the row), optmid (its id in qm_settings), optn, optpg (page of
//! ten), optcap (the setting waiting for a key, -1), optsel (the text
//! setting the box edits, -1), and per setting k: oid oty olb odf olo ohi
//! ost odc oop omx (qm_about's declaration), ovs (stored), ov (edited).
if (qmUaCmd='options') then
begin
   qmUaDone := True;
   var qmUaOab : Integer = ParserSelectByKey('qm_about');
   // The messages of the Options view.
   if (qmUaSel<0) or (qmUaSel>=qmUaN) then
   ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Select a mod first.')
   else
   if (ParserGetIntValueByKeyByHandle(qmUaUi, 'abok')<>1) or (ParserGetIntValueByKeyByHandle(qmUaUi, 'abs'+IntToStr(qmUaSel))=0) or (qmUaOab=0) then
   ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'This mod has no settings.')
   else
   begin
      qmUaS := IntToStr(qmUaSel);
      var qmUaOset : Integer = ParserSelectByKey('qm_settings');
      var qmUaOch : Integer = 0;
      var qmUaOk2 : String;
      var qmUaOv : String;
      var qmUaOpk : String;
      if (qmUaOset<>0) then
      qmUaOch := ParserSelectByHandleByKey(qmUaOset, ParserGetValueByKeyByHandle(qmUaUi, 'abid'+qmUaS));
      ParserSetIntValueByKeyByHandle(qmUaUi, 'opt', qmUaSel);
      ParserSetValueByKeyByHandle(qmUaUi, 'optmid', ParserGetValueByKeyByHandle(qmUaUi, 'abid'+qmUaS));
      ParserSetIntValueByKeyByHandle(qmUaUi, 'optn', ParserGetIntValueByKeyByHandle(qmUaUi, 'abs'+qmUaS));
      ParserSetIntValueByKeyByHandle(qmUaUi, 'optpg', 0);
      ParserSetIntValueByKeyByHandle(qmUaUi, 'optcap', -1);
      ParserSetIntValueByKeyByHandle(qmUaUi, 'optsel', -1);
      for qmUaK:=0 to ParserGetIntValueByKeyByHandle(qmUaUi, 'optn')-1 do
      begin
         qmUaOk2 := qmUaS+'_'+IntToStr(qmUaK);
         qmUaOpk := IntToStr(qmUaK);
         ParserSetValueByKeyByHandle(qmUaUi, 'oid'+qmUaOpk, ParserGetValueByKeyByHandle(qmUaOab, 'sid'+qmUaOk2));
         ParserSetValueByKeyByHandle(qmUaUi, 'oty'+qmUaOpk, ParserGetValueByKeyByHandle(qmUaOab, 'sty'+qmUaOk2));
         ParserSetValueByKeyByHandle(qmUaUi, 'olb'+qmUaOpk, ParserGetValueByKeyByHandle(qmUaOab, 'slb'+qmUaOk2));
         ParserSetValueByKeyByHandle(qmUaUi, 'osc'+qmUaOpk, ParserGetValueByKeyByHandle(qmUaOab, 'ssc'+qmUaOk2));
         ParserSetValueByKeyByHandle(qmUaUi, 'odf'+qmUaOpk, ParserGetValueByKeyByHandle(qmUaOab, 'sdf'+qmUaOk2));
         ParserSetIntValueByKeyByHandle(qmUaUi, 'olo'+qmUaOpk, ParserGetIntValueByKeyByHandle(qmUaOab, 'slo'+qmUaOk2));
         ParserSetIntValueByKeyByHandle(qmUaUi, 'ohi'+qmUaOpk, ParserGetIntValueByKeyByHandle(qmUaOab, 'shi'+qmUaOk2));
         ParserSetIntValueByKeyByHandle(qmUaUi, 'ost'+qmUaOpk, ParserGetIntValueByKeyByHandle(qmUaOab, 'sst'+qmUaOk2));
         ParserSetIntValueByKeyByHandle(qmUaUi, 'odc'+qmUaOpk, ParserGetIntValueByKeyByHandle(qmUaOab, 'sdc'+qmUaOk2));
         ParserSetValueByKeyByHandle(qmUaUi, 'oop'+qmUaOpk, ParserGetValueByKeyByHandle(qmUaOab, 'sop'+qmUaOk2));
         ParserSetIntValueByKeyByHandle(qmUaUi, 'omx'+qmUaOpk, ParserGetIntValueByKeyByHandle(qmUaOab, 'smx'+qmUaOk2));
         qmUaOv := '';
         if (qmUaOch<>0) then
         qmUaOv := ParserGetValueByKeyByHandle(qmUaOch, ParserGetValueByKeyByHandle(qmUaOab, 'sid'+qmUaOk2));
         if (qmUaOv='') then
         qmUaOv := ParserGetValueByKeyByHandle(qmUaOab, 'sdf'+qmUaOk2);
         ParserSetValueByKeyByHandle(qmUaUi, 'ovs'+qmUaOpk, qmUaOv);
         ParserSetValueByKeyByHandle(qmUaUi, 'ov'+qmUaOpk, qmUaOv);
      end;
      ParserSetIntValueByKeyByHandle(qmUaUi, 'panel', 2);
      ParserSetValueByKeyByHandle(qmUaUi, 'msg', '');
      qmLog('ui options open row='+qmUaS+' mod='+ParserGetValueByKeyByHandle(qmUaUi, 'optmid')+' settings='+IntToStr(ParserGetIntValueByKeyByHandle(qmUaUi, 'optn'))+' stored='+IntToStr(qmUaOch));
   end;
end;
if (qmUaCmd='optpage') then
begin
   qmUaDone := True;
   qmUaK := ParserGetIntValueByKeyByHandle(qmUaUi, 'optpg')+qmUaArg;
   if (qmUaK*10>=ParserGetIntValueByKeyByHandle(qmUaUi, 'optn')) then
   qmUaK := (ParserGetIntValueByKeyByHandle(qmUaUi, 'optn')-1) div 10;
   if (qmUaK<0) then
   qmUaK := 0;
   ParserSetIntValueByKeyByHandle(qmUaUi, 'optpg', qmUaK);
end;
if (qmUaCmd='optbtn') then
begin
   qmUaDone := True;
   qmUaK := qmUaArg;
   if (ParserGetIntValueByKeyByHandle(qmUaUi, 'panel')=2) and (qmUaK>=0) and (qmUaK<ParserGetIntValueByKeyByHandle(qmUaUi, 'optn')) then
   begin
      qmUaS := IntToStr(qmUaK);
      var qmUaOty : String = ParserGetValueByKeyByHandle(qmUaUi, 'oty'+qmUaS);
      var qmUaOval : String = ParserGetValueByKeyByHandle(qmUaUi, 'ov'+qmUaS);
      var qmUaOact : Integer = ParserGetIntValueByKeyByHandle(qmUaUi, 'argto');
      var qmUaOx : Integer;
      var qmUaOd : Integer;
      var qmUaOops : String;
      var qmUaOcnt : Integer;
      var qmUaOat : Integer;
      var qmUaOj : Integer;
      var qmUaOit : String;
      ParserSetValueByKeyByHandle(qmUaUi, 'msg', '');
      ParserSetIntValueByKeyByHandle(qmUaUi, 'optcap', -1);
      if (qmUaOty='bool') then
      begin
         if (qmUaOval='1') then
         qmUaOval := '0'
         else
         qmUaOval := '1';
      end;
      if (qmUaOty='int') or (qmUaOty='float') then
      begin
         qmUaOd := ParserGetIntValueByKeyByHandle(qmUaUi, 'odc'+qmUaS);
         qmUaOx := ParserGetIntValueByKeyByHandle(qmUaUi, 'olo'+qmUaS);
         if (qmNumOk(qmUaOval, qmUaOd)) then
         qmUaOx := qmNumScaled(qmUaOval, qmUaOd);
         if (qmUaOact=1) then
         qmUaOx := qmUaOx-ParserGetIntValueByKeyByHandle(qmUaUi, 'ost'+qmUaS)
         else
         qmUaOx := qmUaOx+ParserGetIntValueByKeyByHandle(qmUaUi, 'ost'+qmUaS);
         if (qmUaOx<ParserGetIntValueByKeyByHandle(qmUaUi, 'olo'+qmUaS)) then
         qmUaOx := ParserGetIntValueByKeyByHandle(qmUaUi, 'olo'+qmUaS);
         if (qmUaOx>ParserGetIntValueByKeyByHandle(qmUaUi, 'ohi'+qmUaS)) then
         qmUaOx := ParserGetIntValueByKeyByHandle(qmUaUi, 'ohi'+qmUaS);
         qmNumText(qmUaOx, qmUaOd, qmUaOval);
      end;
      if (qmUaOty='choice') then
      begin
         //! oop is `|a|b|c|`: the choice after (or before) the current one,
         //! round the list.
         qmUaOops := ParserGetValueByKeyByHandle(qmUaUi, 'oop'+qmUaS);
         qmUaOcnt := 0;
         for qmUaOj:=1 to StrLength(qmUaOops) do
         if (SubStr(qmUaOops, qmUaOj, 1)='|') then
         qmUaOcnt := qmUaOcnt+1;
         qmUaOcnt := qmUaOcnt-1;
         qmUaOat := 0;
         for qmUaOj:=1 to qmUaOcnt do
         begin
            qmField(qmUaOops, '|', qmUaOj, qmUaOit);
            if (qmUaOit=qmUaOval) then
            qmUaOat := qmUaOj;
         end;
         if (qmUaOcnt>0) then
         begin
            if (qmUaOact=1) then
            qmUaOat := qmUaOat-1
            else
            qmUaOat := qmUaOat+1;
            if (qmUaOat<1) then
            qmUaOat := qmUaOcnt;
            if (qmUaOat>qmUaOcnt) then
            qmUaOat := 1;
            qmField(qmUaOops, '|', qmUaOat, qmUaOval);
         end;
      end;
      // The messages of the Options view.
      if (qmUaOty='key') then
      begin
         ParserSetIntValueByKeyByHandle(qmUaUi, 'optcap', qmUaK);
         ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Press a key for '+ParserGetValueByKeyByHandle(qmUaUi, 'olb'+qmUaS)+'; Esc keeps the old one.');
      end;
      if (qmUaOty='text') then
      begin
         ParserSetIntValueByKeyByHandle(qmUaUi, 'optsel', qmUaK);
         ParserSetValueByKeyByHandle(qmUaUi, 'typed', qmUaOval);
         ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Type the new text in the box; Accept keeps it.');
      end;
      ParserSetValueByKeyByHandle(qmUaUi, 'ov'+qmUaS, qmUaOval);
      qmLog('ui option '+ParserGetValueByKeyByHandle(qmUaUi, 'oid'+qmUaS)+' '+qmUaOty+' action='+IntToStr(qmUaOact)+' value=['+qmUaOval+']');
   end;
end;
// The messages of the Options view.
if (qmUaCmd='optkey') then
begin
   qmUaDone := True;
   qmUaK := ParserGetIntValueByKeyByHandle(qmUaUi, 'optcap');
   ParserSetIntValueByKeyByHandle(qmUaUi, 'optcap', -1);
   if (qmUaK>=0) and (qmUaK<ParserGetIntValueByKeyByHandle(qmUaUi, 'optn')) then
   begin
      qmUaS := IntToStr(qmUaK);
      var qmUaKwhy : String = '';
      if (qmUaText='') then
      ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Key not changed.')
      else
      begin
         qmUaKeyCheck(qmUaText, qmUaK, qmUaKwhy);
         if (qmUaKwhy<>'') then
         begin
            ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Key '+qmUaText+' not taken: '+qmUaKwhy+'.');
            qmLog('ui option key '+qmUaText+' refused for '+ParserGetValueByKeyByHandle(qmUaUi, 'oid'+qmUaS)+': '+qmUaKwhy);
         end
         else
         begin
            ParserSetValueByKeyByHandle(qmUaUi, 'ov'+qmUaS, qmUaText);
            ParserSetValueByKeyByHandle(qmUaUi, 'msg', '');
            qmLog('ui option key '+ParserGetValueByKeyByHandle(qmUaUi, 'oid'+qmUaS)+' = '+qmUaText);
         end;
      end;
   end;
end;
// The messages of the Options view.
if (qmUaCmd='optdef') then
begin
   qmUaDone := True;
   for qmUaK:=0 to ParserGetIntValueByKeyByHandle(qmUaUi, 'optn')-1 do
   ParserSetValueByKeyByHandle(qmUaUi, 'ov'+IntToStr(qmUaK), ParserGetValueByKeyByHandle(qmUaUi, 'odf'+IntToStr(qmUaK)));
   ParserSetIntValueByKeyByHandle(qmUaUi, 'optcap', -1);
   ParserSetIntValueByKeyByHandle(qmUaUi, 'optsel', -1);
   ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Defaults set; Accept keeps them.');
end;
if (qmUaCmd='optcancel') then
begin
   qmUaDone := True;
   ParserSetIntValueByKeyByHandle(qmUaUi, 'panel', 0);
   ParserSetIntValueByKeyByHandle(qmUaUi, 'optcap', -1);
   ParserSetIntValueByKeyByHandle(qmUaUi, 'optsel', -1);
   ParserSetValueByKeyByHandle(qmUaUi, 'typed', ParserGetValueByKeyByHandle(qmUaUi, 'filter'));
   ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Options not changed.');
   qmLog('ui options cancelled');
end;
// The messages of the Options view.
if (qmUaCmd='optacc') then
begin
   qmUaDone := True;
   //! Two key settings of this mod on one key: the edit copy is checked as a
   //! whole before anything is written.
   var qmUaAdup : String = '';
   var qmUaAj : Integer;
   for qmUaK:=0 to ParserGetIntValueByKeyByHandle(qmUaUi, 'optn')-1 do
   if (ParserGetValueByKeyByHandle(qmUaUi, 'oty'+IntToStr(qmUaK))='key') then
   for qmUaAj:=qmUaK+1 to ParserGetIntValueByKeyByHandle(qmUaUi, 'optn')-1 do
   if (ParserGetValueByKeyByHandle(qmUaUi, 'oty'+IntToStr(qmUaAj))='key') and SameText(ParserGetValueByKeyByHandle(qmUaUi, 'ov'+IntToStr(qmUaK)), ParserGetValueByKeyByHandle(qmUaUi, 'ov'+IntToStr(qmUaAj))) and (qmUaAdup='') then
   qmUaAdup := ParserGetValueByKeyByHandle(qmUaUi, 'olb'+IntToStr(qmUaK))+' and '+ParserGetValueByKeyByHandle(qmUaUi, 'olb'+IntToStr(qmUaAj))+' are both '+ParserGetValueByKeyByHandle(qmUaUi, 'ov'+IntToStr(qmUaK));
   if (qmUaAdup<>'') then
   ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Not saved: '+qmUaAdup+'.')
   else
   begin
      var qmUaSp : Integer = ParserSelectByKey('qm_settings');
      if (qmUaSp=0) then
      qmUaSp := ParserCreate('qm_settings');
      var qmUaSc : Integer = ParserSelectByHandleByKey(qmUaSp, ParserGetValueByKeyByHandle(qmUaUi, 'optmid'));
      if (qmUaSc=0) then
      qmUaSc := ParserAddChildByIndex(qmUaSp, ParserGetValueByKeyByHandle(qmUaUi, 'optmid'));
      var qmUaKeys : Integer = 0;
      var qmUaChanged : Integer = 0;
      for qmUaK:=0 to ParserGetIntValueByKeyByHandle(qmUaUi, 'optn')-1 do
      begin
         qmUaS := IntToStr(qmUaK);
         if (ParserGetValueByKeyByHandle(qmUaUi, 'ov'+qmUaS)<>ParserGetValueByKeyByHandle(qmUaUi, 'ovs'+qmUaS)) then
         begin
            qmUaChanged := qmUaChanged+1;
            if (ParserGetValueByKeyByHandle(qmUaUi, 'oty'+qmUaS)='key') then
            qmUaKeys := qmUaKeys+1;
         end;
         ParserSetValueByKeyByHandle(qmUaSc, ParserGetValueByKeyByHandle(qmUaUi, 'oid'+qmUaS), ParserGetValueByKeyByHandle(qmUaUi, 'ov'+qmUaS));
         ParserSetValueByKeyByHandle(qmUaUi, 'ovs'+qmUaS, ParserGetValueByKeyByHandle(qmUaUi, 'ov'+qmUaS));
      end;
      //! The file is written by qmTick on the next main-menu frame (qm_rt
      //! setsave): the window writes nothing to disk. qm_settings holds the
      //! new values already, so a mod that reads them sees them now.
      var qmUaSrt : Integer = ParserSelectByKey('qm_rt');
      var qmUaSaved : Boolean = (qmUaSrt<>0);
      if (qmUaSrt<>0) then
      begin
         ParserSetIntValueByKeyByHandle(qmUaSrt, 'setsave', 1);
         ParserSetIntValueByKeyByHandle(qmUaSrt, 'setsaveseq', ParserGetIntValueByKeyByHandle(qmUaSrt, 'setsaveseq')+1);
      end;
      //! A new key reaches the game at once: EventQmManager re-registers the
      //! shortcuts the way vanilla does after its hotkeys are saved
      //! (eventsettings.inc:727-728), and a mod that reads qm_settings in
      //! RegisterShortcuts registers the new key.
      if (qmUaKeys>0) then
      ParserSetIntValueByKeyByHandle(qmUaUi, 'rereg', 1);
      ParserSetIntValueByKeyByHandle(qmUaUi, 'panel', 0);
      ParserSetIntValueByKeyByHandle(qmUaUi, 'optcap', -1);
      ParserSetIntValueByKeyByHandle(qmUaUi, 'optsel', -1);
      ParserSetValueByKeyByHandle(qmUaUi, 'typed', ParserGetValueByKeyByHandle(qmUaUi, 'filter'));
      ParserSetIntValueByKeyByHandle(qmUaUi, 'optsaves', ParserGetIntValueByKeyByHandle(qmUaUi, 'optsaves')+1);
      // The messages of the Options view.
      if (qmUaSaved) then
      ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Options saved: '+IntToStr(qmUaChanged)+' changed.')
      else
      ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Options kept for this session only: Quartermaster did not start here.');
      qmLog('ui options saved mod='+ParserGetValueByKeyByHandle(qmUaUi, 'optmid')+' changed='+IntToStr(qmUaChanged)+' keys='+IntToStr(qmUaKeys)+' file='+BoolToStr(qmUaSaved));
   end;
end;
if (qmUaCmd='workshop') then
begin
   qmUaDone := True;
   qmLog('ui workshop page opened');
end;
//! Auto-sort (M8 task 5): the pending order becomes the canonical one - the
//! about.cfg rules, then Workshop id / folder name, Quartermaster last
//! (qmModList, kept as cord<k>). The Active list shows it before Apply.
if (qmUaCmd='autosort') then
begin
   qmUaDone := True;
   // The messages of Auto-sort.
   if (ParserGetIntValueByKeyByHandle(qmUaUi, 'hascanon')<>1) then
   ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'The standard load order is not available right now.')
   else
   begin
      qmUaChg := 0;
      for qmUaK:=0 to qmUaN-1 do
      begin
         ParserSetIntValueByKeyByHandle(qmUaUi, 'ord'+IntToStr(qmUaK), ParserGetIntValueByKeyByHandle(qmUaUi, 'cord'+IntToStr(qmUaK)));
         if (ParserGetIntValueByKeyByHandle(qmUaUi, 'ord'+IntToStr(qmUaK))<>ParserGetIntValueByKeyByHandle(qmUaUi, 'oord'+IntToStr(qmUaK))) then
         qmUaChg := 1;
      end;
      ParserSetIntValueByKeyByHandle(qmUaUi, 'ordchg', qmUaChg);
      ParserSetValueByKeyByHandle(qmUaUi, 'msg', 'Load order sorted: required mods first, then the standard order.');
   end;
   qmLog('ui autosort ordchg='+IntToStr(ParserGetIntValueByKeyByHandle(qmUaUi, 'ordchg')));
end;
if (qmUaCmd='close') then
begin
   qmUaDone := True;
   // The restart notice stays the mode until the restart: a later open shows it again.
   if (qmUaMode<>2) then
   ParserSetIntValueByKeyByHandle(qmUaUi, 'mode', 0);
   ParserSetIntValueByKeyByHandle(qmUaUi, 'close', 1);
   ParserSetIntValueByKeyByHandle(qmUaUi, 'closes', ParserGetIntValueByKeyByHandle(qmUaUi, 'closes')+1);
   qmLog('ui close closes='+IntToStr(ParserGetIntValueByKeyByHandle(qmUaUi, 'closes')));
end;
if (not qmUaDone) then
qmLog('ui cmd ['+qmUaCmd+'] unknown');

//! The pending changes, counted after every command (decided 2026-09-28).
//! `open` has just rebuilt the rows (qmUiModel): read their count and
//! Quartermaster's row again, since the values read at the top may be from
//! before the first model.
qmUaN := ParserGetIntValueByKeyByHandle(qmUaUi, 'n');
qmUaSelf := ParserGetIntValueByKeyByHandle(qmUaUi, 'self');
qmUaChg := 0;
for qmUaI:=0 to qmUaN-1 do
if (ParserGetIntValueByKeyByHandle(qmUaUi, 'pe'+IntToStr(qmUaI))<>ParserGetIntValueByKeyByHandle(qmUaUi, 'en'+IntToStr(qmUaI))) then
qmUaChg := qmUaChg+1;
ParserSetIntValueByKeyByHandle(qmUaUi, 'chg', qmUaChg);

//! Global-script clashes of the pending set (see the top): pairs a before b
//! in row order, both pe = 1, neither Quartermaster; the first file of a's
//! list that b ships too (qmGlobFirst, ref/guard.py conflict_pairs).
var qmUaPn : Integer = 0;
var qmUaA : Integer;
var qmUaB : Integer;
var qmUaF : String;
var qmUaP : String;
for qmUaI:=0 to qmUaN-1 do
ParserSetValueByKeyByHandle(qmUaUi, 'pcl'+IntToStr(qmUaI), '');
for qmUaA:=0 to qmUaN-1 do
if (qmUaA<>qmUaSelf) and (ParserGetIntValueByKeyByHandle(qmUaUi, 'pe'+IntToStr(qmUaA))=1) and (StrLength(ParserGetValueByKeyByHandle(qmUaUi, 'gl'+IntToStr(qmUaA)))>1) then
for qmUaB:=qmUaA+1 to qmUaN-1 do
if (qmUaB<>qmUaSelf) and (ParserGetIntValueByKeyByHandle(qmUaUi, 'pe'+IntToStr(qmUaB))=1) and (StrLength(ParserGetValueByKeyByHandle(qmUaUi, 'gl'+IntToStr(qmUaB)))>1) and (qmUaPn<qmUaConfMax) then
begin
   qmGlobFirst(ParserGetValueByKeyByHandle(qmUaUi, 'gl'+IntToStr(qmUaA)), ParserGetValueByKeyByHandle(qmUaUi, 'gl'+IntToStr(qmUaB)), qmUaF);
   // An add-on and the mod it extends are no clash (0.1.4, qmGlobRelated).
   if (qmUaF<>'') then
   if qmGlobRelated(ParserGetValueByKeyByHandle(qmUaUi, 'dir'+IntToStr(qmUaA)), ParserGetValueByKeyByHandle(qmUaUi, 'dir'+IntToStr(qmUaB))) then
   qmUaF := '';
   if (qmUaF<>'') then
   begin
      qmGlobPath(qmUaF, qmUaP);
      // The clash lines.
      ParserSetValueByKeyByHandle(qmUaUi, 'pc'+IntToStr(qmUaPn), ParserGetValueByKeyByHandle(qmUaUi, 'name'+IntToStr(qmUaA))+' and '+ParserGetValueByKeyByHandle(qmUaUi, 'name'+IntToStr(qmUaB))+' both replace '+qmUaP);
      ParserSetValueByKeyByHandle(qmUaUi, 'pcl'+IntToStr(qmUaA), 'It may clash with '+ParserGetValueByKeyByHandle(qmUaUi, 'name'+IntToStr(qmUaB))+': both replace '+qmUaP+'. If the game does not start with both, Quartermaster switches back.');
      ParserSetValueByKeyByHandle(qmUaUi, 'pcl'+IntToStr(qmUaB), 'It may clash with '+ParserGetValueByKeyByHandle(qmUaUi, 'name'+IntToStr(qmUaA))+': both replace '+qmUaP+'. If the game does not start with both, Quartermaster switches back.');
      qmUaPn := qmUaPn+1;
   end;
end;
ParserSetIntValueByKeyByHandle(qmUaUi, 'pcn', qmUaPn);
if (qmUaPn>0) then
qmLog('ui pending set clashes='+IntToStr(qmUaPn)+' first: '+ParserGetValueByKeyByHandle(qmUaUi, 'pc0'));

//! The about.cfg rules of the pending set (qmUaRules): `pan` problems,
//! `pa<k>` the text and `pat<k>` the tag of each (at most 14), `pafail`
//! how many are FAIL, `pal<i>` the first one of a row for its Details line.
qmUaRules;
var qmUaAr2 : Integer = ParserSelectByKey('qm_abr');
var qmUaAn : Integer = 0;
var qmUaAf : Integer = 0;
var qmUaAw : Integer;
for qmUaI:=0 to qmUaN-1 do
ParserSetValueByKeyByHandle(qmUaUi, 'pal'+IntToStr(qmUaI), '');
for qmUaK:=0 to ParserGetIntValueByKeyByHandle(qmUaAr2, 'n')-1 do
begin
   qmUaS := IntToStr(qmUaK);
   qmUaAw := ParserGetIntValueByKeyByHandle(qmUaAr2, 'row'+qmUaS);
   if (qmUaAn<qmUaConfMax) then
   begin
      ParserSetValueByKeyByHandle(qmUaUi, 'pa'+IntToStr(qmUaAn), ParserGetValueByKeyByHandle(qmUaAr2, 'text'+qmUaS));
      ParserSetValueByKeyByHandle(qmUaUi, 'pat'+IntToStr(qmUaAn), ParserGetValueByKeyByHandle(qmUaAr2, 'tag'+qmUaS));
      qmUaAn := qmUaAn+1;
   end;
   if (ParserGetValueByKeyByHandle(qmUaAr2, 'tag'+qmUaS)='FAIL') then
   qmUaAf := qmUaAf+1;
   if (qmUaAw>=0) and (qmUaAw<qmUaN) then
   if (ParserGetValueByKeyByHandle(qmUaUi, 'pal'+IntToStr(qmUaAw))='') then
   ParserSetValueByKeyByHandle(qmUaUi, 'pal'+IntToStr(qmUaAw), ParserGetValueByKeyByHandle(qmUaAr2, 'tag'+qmUaS)+': '+ParserGetValueByKeyByHandle(qmUaAr2, 'text'+qmUaS)+'.');
end;
ParserSetIntValueByKeyByHandle(qmUaUi, 'pan', qmUaAn);
ParserSetIntValueByKeyByHandle(qmUaUi, 'pafail', qmUaAf);
if (qmUaAn>0) then
qmLog('ui pending set about.cfg problems='+IntToStr(qmUaAn)+' fail='+IntToStr(qmUaAf)+' first: '+ParserGetValueByKeyByHandle(qmUaUi, 'pa0'));
if (ParserGetIntValueByKeyByHandle(qmUaUi, 'sel')>=0) then
StateMachineExecuteState(qmUaCore, 'qmUiDetails', 0);
if ((qmUaChg>0) or (ParserGetIntValueByKeyByHandle(qmUaUi, 'ordchg')=1)) and (ParserGetIntValueByKeyByHandle(qmUaUi, 'mode')=0) then
ParserSetIntValueByKeyByHandle(qmUaUi, 'canapply', 1)
else
ParserSetIntValueByKeyByHandle(qmUaUi, 'canapply', 0);
