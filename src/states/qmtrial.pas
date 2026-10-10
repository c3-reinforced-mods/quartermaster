state: qmTrial
into: data/quartermaster/core.aix
helpers: qmlog, qmstr, qmkeys
requires:
---
//! The activation check (plan G15b, milestone M8 task 4): before the manager
//! window takes a mod into the pending set for good, the whole pipeline runs
//! once for that set - index, plan, generation - into a sandbox of its own,
//! <save>\quartermaster\trial\ (qmWrOpen '*trial'), and never into a mod
//! folder. Asked by qmUiAct through qm_rt (trq, trrow, trsig) and run by
//! qmTick on the next main-menu frame; qmUiAct `trialdone` then acts on the
//! result.
//!
//! What it checks, for the rows it is about (qm_rt trrow: the row just
//! activated, or -1: every row the pending set switches on - the check of
//! Apply):
//!   - every file the generation merges or hooks that such a row takes part
//!     in: a FAIL (the merged file does not compile, a data merge refused;
//!     a WARN instead when such a row brings its own global scripts) or
//!     FATAL decision is a FAIL, a WARN one a WARN;
//!   - the row's own .inc files the game would load as they are (the plan's
//!     skip or winner decisions it wins, and the never-generated
//!     gui\menu.inc\docreate.inc and scripts\common.inc\initmap.inc, whose
//!     failure stops the game at start): each through qmValFiles. A mod that
//!     brings its own global scripts (qm_glob gl<i>) may use them in its
//!     .inc files, and those scripts are not the ones loaded now, so there a
//!     file that does not compile is a LATER line, not a FAIL;
//!   - its gui\menu.aix, if it ships one, loads as a parser (a menu.aix that
//!     does not stops the game at start, context section 3);
//!   - its own check, if it ships data\quartermaster\validate.aix: the state
//!     Validate, run in a trigger manager of its own (qm_modvaltm), reads the
//!     pending set from the named parser qm_modval and answers there
//!     (docs/authoring.md).
//!   - its global scripts, each against the ones loaded now, a WARN when one
//!     does not compile (it may need the mod's own others), and none for
//!     classes.script, which a running game cannot compile (context
//!     section 3: a class it has declared cannot be declared again).
//!   - its key settings: a key another mod active after the change holds
//!     on a key setting too, or a hotkey of the game uses, is a WARN.
//! Clashes between global scripts stay the start-up guard's (plan S17). The
//! validation copies the check made are deleted when it ends (qm_ui trvals).
//!
//! The boot's parsers are put back afterwards exactly: each is copied aside
//! first (ParserSelectByHandle + ParserCopyFromByHandle, the way vanilla
//! keeps the record manager aside, initmapgen.inc:70-71 and :248-250) and
//! copied back at the end, so the window, the report and a later Apply see
//! the boot's own state.
//!
//! What the running game cannot judge is neither: a file of a row that
//! brings its own global scripts and does not compile with the ones loaded
//! now (its own, a merge it is in, the scripts themselves, classes.script)
//! is a LATER line - logged, counted in trlater, and no part of the status.
//! Until 0.1.4 each was a WARN: Reinforced - Core, which is fine, showed
//! WARN with 24 of them and OK after the restart (hands-on, 2026-10-10).
//! The next start judges them: the boot's generation, and for a start that
//! stops, the start-up guard (plan S17).
//!
//! Results in qm_ui: trst (OK, WARN, FAIL, or SKIP when the check cannot
//! run), trn and per line k tr<k> (text) and trt<k> (FAIL or WARN), at most
//! 16, FAIL lines first; trrow, trsig (the pending set it checked, from
//! qm_rt), trfiles (own files validated), trms.
var qmTrCore : Integer = GetTriggerManagerStateMachineHandle('qm_core');
var qmTrRt : Integer = ParserSelectByKey('qm_rt');
var qmTrUi : Integer = ParserSelectByKey('qm_ui');
var qmTrMods : Integer = ParserSelectByKey('qm_mods');
var qmTrGl : Integer = ParserSelectByKey('qm_glob');
var qmTrApp : String = ExtractFilePath(GetApplicationFileName);
var qmTrT0 : Float = _misc_GetRealTime;
var qmTrRow : Integer = ParserGetIntValueByKeyByHandle(qmTrRt, 'trrow');
var qmTrN : Integer = ParserGetIntValueByKeyByHandle(qmTrUi, 'n');
var qmTrSelf : Integer = -1;
var qmTrNames : array [0..12] of String;
var qmTrHad : array [0..12] of Integer;
var qmTrInv : array [0..255] of Integer;
var qmTrPos : array [0..255] of Integer;
var qmTrLib : array [0..255] of Integer;
var qmTrFail : array [0..15] of String;
var qmTrWarn : array [0..15] of String;
var qmTrNf : Integer = 0;
var qmTrNw : Integer = 0;
// LATER lines: what only a game with the row's own global scripts loaded can judge.
var qmTrNl : Integer = 0;
var qmTrVn : Integer = 0;
var qmTrVrow : array [0..511] of Integer;
var qmTrVrel : array [0..511] of String;
var qmTrVs : array [0..511] of Integer;
var qmTrDrop : Integer = 0;
var qmTrSeq0 : Integer = 0;
var qmTrZ : Integer;
var qmTrOk : Boolean = True;
var qmTrWhy : String = '';
var qmTrI : Integer;
var qmTrK : Integer;
var qmTrM : Integer;
var qmTrJ : Integer;
var qmTrH : Integer;
var qmTrS : Integer;
var qmTrA : String;
var qmTrB : String;
var qmTrP : String;
var qmTrT : String;
var qmTrX : String;
var qmTrD : String;
var qmTrTit : String;
var qmTrEn : Integer = 0;

procedure qmTrAdd(const qmTaTag : String; const qmTaText : String);
begin
   if (qmTaTag='FAIL') then
   begin
      if (qmTrNf<16) then
      qmTrFail[qmTrNf] := qmTaText;
      qmTrNf := qmTrNf+1;
   end
   else
   if (qmTaTag='LATER') then
   qmTrNl := qmTrNl+1
   else
   begin
      if (qmTrNw<16) then
      qmTrWarn[qmTrNw] := qmTaText;
      qmTrNw := qmTrNw+1;
   end;
   qmLog('trial '+qmTaTag+' '+qmTaText);
end;
//! 1 when the `;`-list qmTiList holds the position of an involved row.
function qmTrTouches(const qmTiList : String; const qmTiLib : Integer) : Integer;
begin
   var qmTiK : Integer;
   var qmTiJ : Integer = 0;
   var qmTiF : String;
   Result := 0;
   qmField(qmTiList, ';', qmTiJ, qmTiF);
   while (qmTiF<>'') do
   begin
      for qmTiK:=0 to qmTrN-1 do
      if (qmTrInv[qmTiK]=1) and ((qmTiLib=0) or (qmTrLib[qmTiK]=1)) and (IntToStr(qmTrPos[qmTiK])=qmTiF) then
      Result := 1;
      qmTiJ := qmTiJ+1;
      qmField(qmTiList, ';', qmTiJ, qmTiF);
   end;
end;
procedure qmTrOwn(const qmToRow : Integer; const qmToRel : String; const qmToScript : Integer);
begin
   if (qmTrVn<512) then
   begin
      qmTrVrow[qmTrVn] := qmToRow;
      qmTrVrel[qmTrVn] := qmToRel;
      qmTrVs[qmTrVn] := qmToScript;
      qmTrVn := qmTrVn+1;
   end
   else
   qmTrDrop := qmTrDrop+1;
end;

qmTrNames[0] := 'qm_mods';
qmTrNames[1] := 'qm_index';
qmTrNames[2] := 'qm_index_keys';
qmTrNames[3] := 'qm_vidx';
qmTrNames[4] := 'qm_plan';
qmTrNames[5] := 'qm_gen';
qmTrNames[6] := 'qm_gen_in';
qmTrNames[7] := 'qm_gen_v';
qmTrNames[8] := 'qm_mg';
qmTrNames[9] := 'qm_mg_in';
qmTrNames[10] := 'qm_dm';
qmTrNames[11] := 'qm_dm_in';
qmTrNames[12] := 'qm_ms';
ParserSetValueByKeyByHandle(qmTrUi, 'trsig', ParserGetValueByKeyByHandle(qmTrRt, 'trsig'));
ParserSetIntValueByKeyByHandle(qmTrUi, 'trrow', qmTrRow);
//! The window's rows must be the boot's: the same dirs in the same places.
if (qmTrMods=0) or (qmTrCore=0) or (qmTrN<1) or (qmTrN>256) or (ParserGetIntValueByKeyByHandle(qmTrMods, 'n')<>qmTrN) then
begin
   qmTrOk := False;
   qmTrWhy := 'the mod list is not the one this start loaded';
end
else
begin
   qmTrSelf := ParserGetIntValueByKeyByHandle(qmTrMods, 'self');
   for qmTrI:=0 to qmTrN-1 do
   begin
      qmLowerAscii(ParserGetValueByKeyByHandle(qmTrMods, 'dir'+IntToStr(qmTrI)), qmTrA);
      qmLowerAscii(ParserGetValueByKeyByHandle(qmTrUi, 'dir'+IntToStr(qmTrI)), qmTrB);
      if (qmTrA<>qmTrB) then
      begin
         qmTrOk := False;
         qmTrWhy := 'the mod list is not the one this start loaded';
      end;
   end;
end;
if (not qmTrOk) then
begin
   ParserSetValueByKeyByHandle(qmTrUi, 'trst', 'SKIP');
   ParserSetIntValueByKeyByHandle(qmTrUi, 'trn', 1);
   ParserSetValueByKeyByHandle(qmTrUi, 'tr0', qmTrWhy);
   ParserSetValueByKeyByHandle(qmTrUi, 'trt0', 'WARN');
   qmLog('trial skipped: '+qmTrWhy);
   exit;
end;
//! The boot's parsers aside.
for qmTrK:=0 to 12 do
begin
   qmTrH := ParserSelectByKey(qmTrNames[qmTrK]);
   qmTrHad[qmTrK] := 0;
   if (qmTrH<>0) then
   begin
      qmTrHad[qmTrK] := 1;
      qmTrS := ParserSelectByKey('qm_trsnap'+IntToStr(qmTrK));
      if (qmTrS=0) then
      qmTrS := ParserCreate('qm_trsnap'+IntToStr(qmTrK));
      ParserSelectByHandle(qmTrS);
      ParserClearByHandle(qmTrS);
      ParserCopyFromByHandle(qmTrH);
   end;
end;
//! The pending set as the load order: flags, places, the scan list.
for qmTrK:=0 to qmTrN-1 do
begin
   qmTrI := ParserGetIntValueByKeyByHandle(qmTrUi, 'ord'+IntToStr(qmTrK));
   if (qmTrI>=0) and (qmTrI<qmTrN) then
   begin
      qmTrPos[qmTrI] := qmTrK;
      ParserSetIntValueByKeyByHandle(qmTrMods, 'ord'+IntToStr(qmTrK), qmTrI);
      ParserSetIntValueByKeyByHandle(qmTrMods, 'pos'+IntToStr(qmTrI), qmTrK);
      ParserSetIntValueByKeyByHandle(qmTrMods, 'on'+IntToStr(qmTrI), ParserGetIntValueByKeyByHandle(qmTrUi, 'pe'+IntToStr(qmTrI)));
      if (ParserGetIntValueByKeyByHandle(qmTrUi, 'pe'+IntToStr(qmTrI))=1) and (qmTrI<>qmTrSelf) and (ParserGetIntValueByKeyByHandle(qmTrMods, 'core'+IntToStr(qmTrI))=0) then
      begin
         ParserSetIntValueByKeyByHandle(qmTrMods, 'e'+IntToStr(qmTrEn), qmTrI);
         qmTrEn := qmTrEn+1;
      end;
   end;
end;
ParserSetIntValueByKeyByHandle(qmTrMods, 'en', qmTrEn);
for qmTrI:=0 to qmTrN-1 do
begin
   qmTrInv[qmTrI] := 0;
   if (qmTrRow>=0) and (qmTrI=qmTrRow) then
   qmTrInv[qmTrI] := 1;
   if (qmTrRow<0) and (ParserGetIntValueByKeyByHandle(qmTrUi, 'pe'+IntToStr(qmTrI))=1) and (ParserGetIntValueByKeyByHandle(qmTrUi, 'en'+IntToStr(qmTrI))=0) then
   qmTrInv[qmTrI] := 1;
   qmTrLib[qmTrI] := 0;
   if (qmTrGl<>0) then
   if (StrLength(ParserGetValueByKeyByHandle(qmTrGl, 'gl'+IntToStr(qmTrI)))>1) then
   qmTrLib[qmTrI] := 1;
end;
//! Where this check's validation copies start (qmValNext numbers them in
//! qm_val seq), so they can go afterwards: each check adds some, and a big
//! mod's add megabytes.
if (ParserSelectByKey('qm_val')<>0) then
qmTrSeq0 := ParserGetIntValueByKeyByHandle(ParserSelectByKey('qm_val'), 'seq');
//! The pipeline, into the sandbox.
StateMachineExecuteState(qmTrCore, 'qmIndex', 0);
StateMachineExecuteState(qmTrCore, 'qmPlan', 0);
var qmTrIn : Integer = ParserSelectByKey('qm_gen_in');
if (qmTrIn=0) then
qmTrIn := ParserCreate('qm_gen_in');
ParserClearByHandle(qmTrIn);
ParserSetValueByKeyByHandle(qmTrIn, 'sandbox', '*trial');
ParserSetValueByKeyByHandle(qmTrIn, 'hookdir', 'qm');
var qmTrG : Integer = ParserSelectByKey('qm_gen');
if (qmTrG<>0) then
ParserClearByHandle(qmTrG);
StateMachineExecuteState(qmTrCore, 'qmGenerate', 0);
qmTrG := ParserSelectByKey('qm_gen');
var qmTrPlan : Integer = ParserSelectByKey('qm_plan');
var qmTrPn : Integer = ParserGetIntValueByKeyByHandle(qmTrPlan, 'n');
if (qmTrG=0) or (ParserGetValueByKeyByHandle(qmTrG, 'status')='') then
qmTrAdd('WARN', 'the trial generation did not run')
else
for qmTrM:=0 to qmTrPn-1 do
begin
   qmTrP := ParserGetValueByKeyByHandle(qmTrPlan, 'path'+IntToStr(qmTrM));
   qmTrA := ParserGetValueByKeyByHandle(qmTrPlan, 'act'+IntToStr(qmTrM));
   qmTrT := ParserGetValueByKeyByHandle(qmTrG, 's'+IntToStr(qmTrM));
   qmTrX := ParserGetValueByKeyByHandle(qmTrG, 'x'+IntToStr(qmTrM));
   //! A merge or a hook the involved rows take part in.
   if (qmTrA='merge-inc') or (qmTrA='merge-data') or (qmTrA='hook') then
   if (qmTrTouches(ParserGetValueByKeyByHandle(qmTrPlan, 'prov'+IntToStr(qmTrM)), 0)=1) then
   begin
      // The lines of the activation check.
      if (qmTrT='FAIL') or (qmTrT='FATAL') then
      begin
         if (qmTrX='datafail') then
         qmTrAdd('FAIL', qmTrP+': '+ParserGetValueByKeyByHandle(qmTrG, 'e'+IntToStr(qmTrM)))
         else
         //! A file merged from a row that brings its own global scripts may
         //! call them, and they are not the ones loaded now: as for the row's
         //! own files below, that is a WARN. An Apply builds the file again at
         //! the next start, with the new set loaded (qmguard.pas). Until 0.1.4
         //! it was a FAIL, and such a mod could not be activated again once it
         //! was off (hands-on, 2026-10-10: Reinforced - Core refused twice,
         //! "gui\menu.inc\doprogress.inc: the merged file does not compile").
         if (qmTrTouches(ParserGetValueByKeyByHandle(qmTrPlan, 'prov'+IntToStr(qmTrM)), 1)=1) then
         qmTrAdd('LATER', qmTrP+' does not compile merged with the global scripts loaded now; a mod in it brings its own, so it is built again at the next start')
         else
         if (qmTrX='fallback') then
         qmTrAdd('FAIL', qmTrP+': the merged file does not compile')
         else
         qmTrAdd('FAIL', qmTrP+': no version of the file compiles');
      end
      else
      if (qmTrT='WARN') then
      qmTrAdd('WARN', qmTrP+' is merged with a warning; the report after Apply shows the details');
   end;
   //! An .inc an involved row brings alone, or wins with: loaded as it is.
   if (qmTrA='skip') or (qmTrA='winner') then
   if (StrLength(qmTrP)>4) and (SubStr(qmTrP, StrLength(qmTrP)-3, 4)='.inc') then
   for qmTrI:=0 to qmTrN-1 do
   if (qmTrInv[qmTrI]=1) and (ParserGetValueByKeyByHandle(qmTrPlan, 'win'+IntToStr(qmTrM))=IntToStr(qmTrPos[qmTrI])) then
   qmTrOwn(qmTrI, qmTrP, 0);
end;
//! The never-generated files that stop the start, and menu.aix.
for qmTrI:=0 to qmTrN-1 do
if (qmTrInv[qmTrI]=1) then
begin
   qmTrD := ParserGetValueByKeyByHandle(qmTrUi, 'dir'+IntToStr(qmTrI));
   if (FileAge(qmTrD+'\data\gui\menu.inc\docreate.inc')<>-1) then
   qmTrOwn(qmTrI, 'gui\menu.inc\docreate.inc', 0);
   if (FileAge(qmTrD+'\data\scripts\common.inc\initmap.inc')<>-1) then
   qmTrOwn(qmTrI, 'scripts\common.inc\initmap.inc', 0);
   //! Its global scripts, each against the ones loaded now (a broken one
   //! stops the game at start, context section 3), but classes.script: a
   //! class the game has declared already cannot be declared again in the
   //! validation copy (probe cls-111839), so it is not compiled here.
   if (qmTrGl<>0) then
   begin
      qmTrA := ParserGetValueByKeyByHandle(qmTrGl, 'gl'+IntToStr(qmTrI));
      qmTrK := 1;
      qmField(qmTrA, '|', qmTrK, qmTrB);
      while (qmTrB<>'') do
      begin
         if (qmTrB='lib\classes.script') then
         qmTrAdd('LATER', 'scripts\lib\classes.script is not checked: a running game cannot compile it')
         else
         if (SubStr(qmTrB, 1, 4)='lib\') then
         qmTrOwn(qmTrI, 'scripts\'+qmTrB, 1);
         qmTrK := qmTrK+1;
         qmField(qmTrA, '|', qmTrK, qmTrB);
      end;
   end;
   if (FileAge(qmTrD+'\data\gui\menu.aix')<>-1) then
   begin
      qmTrH := ParserSelectByKey('qm_traix');
      if (qmTrH=0) then
      qmTrH := ParserCreate('qm_traix');
      ParserClearByHandle(qmTrH);
      if (not ParserLoadFromFileByHandle(qmTrH, qmTrApp+qmTrD+'\data\gui\menu.aix')) then
      qmTrAdd('FAIL', 'gui\menu.aix does not load: the game would not start');
      ParserClearByHandle(qmTrH);
   end;
end;
if (qmTrDrop>0) then
qmTrAdd('WARN', IntToStr(qmTrDrop)+' more of its own files were not checked: at most 512 in one check');
//! The own files through the validator.
if (qmTrVn>0) then
begin
   ParserClearByHandle(qmTrIn);
   ParserSetValueByKeyByHandle(qmTrIn, 'vbox', '*trial');
   ParserSetIntValueByKeyByHandle(qmTrIn, 'vn', qmTrVn);
   for qmTrK:=0 to qmTrVn-1 do
   begin
      ParserSetValueByKeyByHandle(qmTrIn, 'v'+IntToStr(qmTrK), qmTrApp+ParserGetValueByKeyByHandle(qmTrUi, 'dir'+IntToStr(qmTrVrow[qmTrK]))+'\data\'+qmTrVrel[qmTrK]);
      ParserSetIntValueByKeyByHandle(qmTrIn, 'vb'+IntToStr(qmTrK), 0);
      ParserSetIntValueByKeyByHandle(qmTrIn, 'vs'+IntToStr(qmTrK), qmTrVs[qmTrK]);
   end;
   StateMachineExecuteState(qmTrCore, 'qmValFiles', 0);
   var qmTrV : Integer = ParserSelectByKey('qm_gen_v');
   for qmTrK:=0 to qmTrVn-1 do
   begin
      qmField(ParserGetValueByKeyByHandle(qmTrV, 'vr'+IntToStr(qmTrK)), '|', 2, qmTrA);
      if (qmTrA='0') and (qmTrVs[qmTrK]=1) then
      qmTrAdd('LATER', qmTrVrel[qmTrK]+' does not compile with the global scripts loaded now; if the mod does not bring what it needs, the game will not start')
      else
      if (qmTrA='0') then
      begin
         if (qmTrLib[qmTrVrow[qmTrK]]=1) then
         qmTrAdd('LATER', qmTrVrel[qmTrK]+' does not compile with the global scripts loaded now; the mod brings its own, so this is not certain')
         else
         qmTrAdd('FAIL', qmTrVrel[qmTrK]+' does not compile');
      end;
      if (qmTrA='-1') then
      qmTrAdd('WARN', qmTrVrel[qmTrK]+' could not be read');
   end;
end;
//! Its key settings (M8 task 4): the key each holds - its stored value, or
//! the default qmSettings filled in - that another key setting of the same
//! mod holds too, or a key setting of another mod active after the change,
//! or that the game holds against it by the Options view's own rules
//! (qmkeys: a key the game does not let a hotkey use, one of the player's
//! hotkeys but an `event` one, a shortcut the game registers by name). The
//! game's rules pass over the setting's own default, as the Options view
//! does: its author chose it with the game's keys in sight - QMTestWASD2's
//! S and D are vanilla build hotkeys. A WARN: the player can change it in
//! Options.
var qmTrAb : Integer = ParserSelectByKey('qm_about');
var qmTrSet : Integer = ParserSelectByKey('qm_settings');
var qmTrCi : Integer;
var qmTrCj : Integer;
var qmTrKey : String;
var qmTrKs : String;
var qmTrLb : String;
var qmTrX2 : Integer;
var qmTrGame : String;
if (qmTrAb<>0) and (qmTrSet<>0) then
for qmTrI:=0 to qmTrN-1 do
if (qmTrInv[qmTrI]=1) and (ParserGetIntValueByKeyByHandle(qmTrUi, 'abs'+IntToStr(qmTrI))>0) then
begin
   qmTrCi := ParserSelectByHandleByKey(qmTrSet, ParserGetValueByKeyByHandle(qmTrUi, 'abid'+IntToStr(qmTrI)));
   if (qmTrCi<>0) then
   for qmTrK:=0 to ParserGetIntValueByKeyByHandle(qmTrUi, 'abs'+IntToStr(qmTrI))-1 do
   begin
      qmTrKs := IntToStr(qmTrI)+'_'+IntToStr(qmTrK);
      qmTrKey := '';
      if (ParserGetValueByKeyByHandle(qmTrAb, 'sty'+qmTrKs)='key') then
      qmTrKey := ParserGetValueByKeyByHandle(qmTrCi, ParserGetValueByKeyByHandle(qmTrAb, 'sid'+qmTrKs));
      if (qmTrKey<>'') then
      begin
         qmTrLb := ParserGetValueByKeyByHandle(qmTrAb, 'slb'+qmTrKs)+' of '+ParserGetValueByKeyByHandle(qmTrUi, 'name'+IntToStr(qmTrI));
         // The lines of a key two settings or a setting and the game share.
         //! Another key setting of this mod, each pair once.
         for qmTrX2:=qmTrK+1 to ParserGetIntValueByKeyByHandle(qmTrUi, 'abs'+IntToStr(qmTrI))-1 do
         begin
            qmTrA := IntToStr(qmTrI)+'_'+IntToStr(qmTrX2);
            if (ParserGetValueByKeyByHandle(qmTrAb, 'sty'+qmTrA)='key') then
            if SameText(ParserGetValueByKeyByHandle(qmTrCi, ParserGetValueByKeyByHandle(qmTrAb, 'sid'+qmTrA)), qmTrKey) then
            qmTrAdd('WARN', 'key '+qmTrKey+': '+ParserGetValueByKeyByHandle(qmTrAb, 'slb'+qmTrKs)+' and '+ParserGetValueByKeyByHandle(qmTrAb, 'slb'+qmTrA)+' of '+ParserGetValueByKeyByHandle(qmTrUi, 'name'+IntToStr(qmTrI)));
         end;
         for qmTrJ:=0 to qmTrN-1 do
         if (qmTrJ<>qmTrI) and (ParserGetIntValueByKeyByHandle(qmTrUi, 'pe'+IntToStr(qmTrJ))=1) and (ParserGetIntValueByKeyByHandle(qmTrUi, 'abs'+IntToStr(qmTrJ))>0) and ((qmTrInv[qmTrJ]=0) or (qmTrJ>qmTrI)) then
         begin
            qmTrCj := ParserSelectByHandleByKey(qmTrSet, ParserGetValueByKeyByHandle(qmTrUi, 'abid'+IntToStr(qmTrJ)));
            if (qmTrCj<>0) then
            for qmTrM:=0 to ParserGetIntValueByKeyByHandle(qmTrUi, 'abs'+IntToStr(qmTrJ))-1 do
            begin
               qmTrA := IntToStr(qmTrJ)+'_'+IntToStr(qmTrM);
               if (ParserGetValueByKeyByHandle(qmTrAb, 'sty'+qmTrA)='key') then
               if SameText(ParserGetValueByKeyByHandle(qmTrCj, ParserGetValueByKeyByHandle(qmTrAb, 'sid'+qmTrA)), qmTrKey) then
               qmTrAdd('WARN', 'key '+qmTrKey+': '+qmTrLb+' and '+ParserGetValueByKeyByHandle(qmTrAb, 'slb'+qmTrA)+' of '+ParserGetValueByKeyByHandle(qmTrUi, 'name'+IntToStr(qmTrJ)));
            end;
         end;
         //! The game's rules, but for the setting's own default.
         if (not SameText(qmTrKey, ParserGetValueByKeyByHandle(qmTrAb, 'sdf'+qmTrKs))) then
         begin
            qmKeyForbidden(qmTrKey, qmTrGame);
            if (qmTrGame='') then
            qmKeyGameUse(qmTrKey, qmTrGame);
            if (qmTrGame<>'') then
            qmTrAdd('WARN', 'key '+qmTrKey+': '+qmTrLb+' - '+qmTrGame);
         end;
      end;
   end;
end;
//! The mod's own check.
for qmTrI:=0 to qmTrN-1 do
if (qmTrInv[qmTrI]=1) then
begin
   qmTrD := ParserGetValueByKeyByHandle(qmTrUi, 'dir'+IntToStr(qmTrI));
   if (FileAge(qmTrD+'\data\quartermaster\validate.aix')<>-1) then
   begin
      var qmTrMv : Integer = ParserSelectByKey('qm_modval');
      if (qmTrMv=0) then
      qmTrMv := ParserCreate('qm_modval');
      ParserClearByHandle(qmTrMv);
      ParserSetValueByKeyByHandle(qmTrMv, 'dir', qmTrD);
      ParserSetIntValueByKeyByHandle(qmTrMv, 'n', qmTrN);
      //! id<k> is the id the mod's about.cfg declares, empty without one
      //! (docs/authoring.md) - not the window's abid, which falls back to the
      //! Workshop number or folder name: a folder named like a required id
      //! must not pass for it.
      for qmTrK:=0 to qmTrN-1 do
      begin
         qmTrJ := ParserGetIntValueByKeyByHandle(qmTrUi, 'ord'+IntToStr(qmTrK));
         ParserSetValueByKeyByHandle(qmTrMv, 'dir'+IntToStr(qmTrK), ParserGetValueByKeyByHandle(qmTrUi, 'dir'+IntToStr(qmTrJ)));
         qmTrT := '';
         if (qmTrAb<>0) then
         qmTrT := ParserGetValueByKeyByHandle(qmTrAb, 'id'+IntToStr(qmTrJ));
         ParserSetValueByKeyByHandle(qmTrMv, 'id'+IntToStr(qmTrK), qmTrT);
         ParserSetIntValueByKeyByHandle(qmTrMv, 'on'+IntToStr(qmTrK), ParserGetIntValueByKeyByHandle(qmTrUi, 'pe'+IntToStr(qmTrJ)));
      end;
      ParserSetIntValueByKeyByHandle(qmTrMv, 'done', 0);
      qmTrH := GetTriggerManagerStateMachineHandle('qm_modvaltm');
      if (qmTrH=0) then
      begin
         TriggerManagerAdd('qm_modvaltm');
         qmTrH := GetTriggerManagerStateMachineHandle('qm_modvaltm');
      end;
      if (qmTrH<>0) then
      begin
         StateMachineLoadFromFile(qmTrH, qmTrApp+qmTrD+'\data\quartermaster\validate.aix');
         StateMachineExecuteState(qmTrH, 'Validate', 0);
      end;
      qmTrTit := ParserGetValueByKeyByHandle(qmTrUi, 'name'+IntToStr(qmTrI));
      if (ParserGetIntValueByKeyByHandle(qmTrMv, 'done')<>1) then
      qmTrAdd('WARN', 'the own check of '+qmTrTit+' did not run to its end')
      else
      for qmTrK:=0 to ParserGetIntValueByKeyByHandle(qmTrMv, 'pn')-1 do
      begin
         qmTrT := ParserGetValueByKeyByHandle(qmTrMv, 'pt'+IntToStr(qmTrK));
         if (qmTrT='FAIL') then
         qmTrAdd('FAIL', qmTrTit+': '+ParserGetValueByKeyByHandle(qmTrMv, 'px'+IntToStr(qmTrK)))
         else
         qmTrAdd('WARN', qmTrTit+': '+ParserGetValueByKeyByHandle(qmTrMv, 'px'+IntToStr(qmTrK)));
      end;
   end;
end;
//! This check's validation copies go (<seq>.inc staged, <seq>.aix the
//! copy); the files named by decision (d<m>, m<m>) are written over by the
//! next check anyway.
var qmTrSeq1 : Integer = qmTrSeq0;
if (ParserSelectByKey('qm_val')<>0) then
qmTrSeq1 := ParserGetIntValueByKeyByHandle(ParserSelectByKey('qm_val'), 'seq');
for qmTrZ:=qmTrSeq0 to qmTrSeq1-1 do
begin
   DeleteFileStream(GetAppSaveDirectoryPath+'quartermaster\trial\work\val\'+IntToStr(qmTrZ)+'.inc');
   DeleteFileStream(GetAppSaveDirectoryPath+'quartermaster\trial\work\val\'+IntToStr(qmTrZ)+'.aix');
end;
ParserSetIntValueByKeyByHandle(qmTrUi, 'trvals', qmTrSeq1-qmTrSeq0);
//! The boot's parsers back, and the result.
for qmTrK:=12 downto 0 do
begin
   qmTrH := ParserSelectByKey(qmTrNames[qmTrK]);
   if (qmTrHad[qmTrK]=1) then
   begin
      qmTrS := ParserSelectByKey('qm_trsnap'+IntToStr(qmTrK));
      ParserSelectByHandle(qmTrH);
      ParserClearByHandle(qmTrH);
      ParserCopyFromByHandle(qmTrS);
      ParserClearByHandle(qmTrS);
   end
   else
   if (qmTrH<>0) then
   ParserClearByHandle(qmTrH);
end;
qmTrT := 'OK';
if (qmTrNw>0) then
qmTrT := 'WARN';
if (qmTrNf>0) then
qmTrT := 'FAIL';
ParserSetValueByKeyByHandle(qmTrUi, 'trst', qmTrT);
ParserSetIntValueByKeyByHandle(qmTrUi, 'trlater', qmTrNl);
qmTrJ := 0;
for qmTrK:=0 to qmTrNf-1 do
if (qmTrK<16) then
begin
   ParserSetValueByKeyByHandle(qmTrUi, 'tr'+IntToStr(qmTrJ), qmTrFail[qmTrK]);
   ParserSetValueByKeyByHandle(qmTrUi, 'trt'+IntToStr(qmTrJ), 'FAIL');
   qmTrJ := qmTrJ+1;
end;
for qmTrK:=0 to qmTrNw-1 do
if (qmTrK<16) and (qmTrJ<16) then
begin
   ParserSetValueByKeyByHandle(qmTrUi, 'tr'+IntToStr(qmTrJ), qmTrWarn[qmTrK]);
   ParserSetValueByKeyByHandle(qmTrUi, 'trt'+IntToStr(qmTrJ), 'WARN');
   qmTrJ := qmTrJ+1;
end;
ParserSetIntValueByKeyByHandle(qmTrUi, 'trn', qmTrJ);
for qmTrK:=qmTrJ to 15 do
begin
   ParserSetValueByKeyByHandle(qmTrUi, 'tr'+IntToStr(qmTrK), '');
   ParserSetValueByKeyByHandle(qmTrUi, 'trt'+IntToStr(qmTrK), '');
end;
ParserSetIntValueByKeyByHandle(qmTrUi, 'trfiles', qmTrVn);
ParserSetIntValueByKeyByHandle(qmTrUi, 'trms', Floor((_misc_GetRealTime-qmTrT0)*1000));
qmLog('trial row='+IntToStr(qmTrRow)+' st='+qmTrT+' fails='+IntToStr(qmTrNf)+' warns='+IntToStr(qmTrNw)+' later='+IntToStr(qmTrNl)+' own files='+IntToStr(qmTrVn)+' ms='+IntToStr(Floor((_misc_GetRealTime-qmTrT0)*1000)));
