state: qmOrder
into: data/quartermaster/core.aix
helpers: qmlog, qmstr, qminc, qmbootdir
requires: inchead
---
//! The load order and the mods.ini it asks for (plan S11 as revised on
//! 2026-09-28 and 2026-09-30, G5; twin: ref/order.py load_order,
//! apply_order, load_rows, order_file_after - its docstring has the rules and
//! the file format). qmModList has sorted the registered mods canonically
//! (qm_mods ord<k>: Workshop items by id, local folders by name, anything else
//! by dir, Quartermaster last), the order Auto-sort gives; this state turns
//! mods.ini's order and the player's saved order into the load order, the rows
//! qmModsIni should find in mods.ini, and runs it.
//!
//! The load order:
//!   - no saved order (<save>\quartermaster\order.cfg missing, or without its
//!     format line or a dir): mods.ini's own order (the rows' order,
//!     ModLibraryGetData's), Quartermaster moved last, and nothing is written.
//!     It is the order the game loads without Quartermaster, so every whole
//!     file two mods ship keeps its winner (since 2026-09-30: the canonical order here
//!     bricked Cannons + State vs Country, which start without Quartermaster);
//!   - a saved order: its dirs that are still registered, in its order; then
//!     the mods it does not place yet, in mods.ini's order; Quartermaster
//!     last. The file is written back when that changed it; when none of its
//!     dirs is registered any more it is deleted (mods.ini's order again);
//!   - an Apply of the manager window that changed the order (qm_rt
//!     uiapplyorder = 1, uiapplyordn, uiapplyord<k>; docs/ui.md): that order,
//!     if it lists every registered dir exactly once (compared folded), with
//!     Quartermaster moved last; saved, or order.cfg deleted when it is
//!     mods.ini's order. Otherwise the saved order stays and the log says why.
//! Every consumer after this state reads the load order from qm_mods: ord<k>
//! and pos<i> are rewritten to it (the index's providers, the plan's winner,
//! the fingerprint's lines, the report and the window all follow), and
//! qmModList's canonical order is kept in cord<k> / cpos<i>. A row whose load
//! position is not its canonical one is logged (`order: mod <i> pos=<k>
//! (canonical <c>)`), so a log replay can map positions to dirs.
//!
//! Flags. Every row keeps its own flag, except in an Apply: then the flags
//! qmUiApply recorded (qm_rt uiapplyn, uiapplydir<i>, uiapplydis<i>) replace
//! them, matched by folded dir, never Quartermaster's own (switching it off is
//! modman's job, plan S1). qm_mods on<i> then holds the flags wanted, and
//! e<j> / en the enabled mods the index should scan, in load order (never a
//! folder with core<i> = 1, another copy of Quartermaster; qmModList), so the
//! generation that follows is made for the mods the next start will load.
//! eon<i> keeps the flags the running game loaded: qmModsIni compares its
//! enabled order with the new one.
//!
//! An Apply also records the set it put into mods.ini for the start-up guard,
//! <save>\quartermaster\chosen.cfg (at the end of this state).
//!
//! mods.ini and order.cfg are left alone during an MP mod sync (plan S8: the
//! engine's restore branch owns the mod list then, data/scripts/
//! resource.script:44-74 - a mod missing for the sync must not drop out of
//! the saved order) and when Quartermaster's own folder is unknown.
//!
//! qm_order keys: src (ini, saved, apply), canon (1 = the enabled mods'
//! load order is their canonical order: nothing for MP players to agree on),
//! ext (1 = mods.ini had the placed mods in another order than the saved one,
//! an outside reorder, e.g. modman), unseen and u<j>, dropped and d<j>, file
//! (same, written, deleted, failed), why (an Apply's order not used: count,
//! dirs). qm_ini_in: n, dir<k>, dis<k> (True / False, as the engine spells
//! them).
var qmOrMods : Integer = ParserSelectByKey('qm_mods');
var qmOrRt : Integer = ParserSelectByKey('qm_rt');
var qmOrN : Integer = ParserGetIntValueByKeyByHandle(qmOrMods, 'n');
var qmOrSelf : Integer = ParserGetIntValueByKeyByHandle(qmOrMods, 'self');
var qmOrApply : Boolean = (ParserGetValueByKeyByHandle(qmOrRt, 'runmode')='apply');
var qmOrSync : Boolean = (ParserGetIntValueByKeyByHandle(qmOrRt, 'sync')=1);
var qmOrPath : String = GetAppSaveDirectoryPath+'quartermaster\order.cfg';
var qmOrNorm : array [0..255] of String;
var qmOrIsSelf : array [0..255] of Integer;
var qmOrCan : array [0..255] of Integer;
var qmOrRow : array [0..255] of Integer;
var qmOrTaken : array [0..255] of Integer;
var qmOrSv : array [0..511] of String;
var qmOrSvN : Integer = 0;
var qmOrHave : Integer = 0;
var qmOrI : Integer;
var qmOrJ : Integer;
var qmOrK : Integer;
var qmOrS : String;
var qmOrT : String;
var qmOrV : String;
var qmOrAn : Integer;
var qmOrWas : Integer;
var qmOrNow : Integer;
var qmOrEn : Integer = 0;
var qmOrM : Integer = 0;
var qmOrPlaced : Integer = 0;
var qmOrUnseen : Integer = 0;
var qmOrDropped : Integer = 0;
var qmOrExt : Integer = 0;
var qmOrCanon : Integer = 1;
var qmOrSrcName : String = 'ini';
var qmOrWhy : String = '';
var qmOrFile : String = 'same';
var qmOrSame : Boolean;
var qmOrHit : Integer;
var qmOrOrd : Integer = ParserSelectByKey('qm_order');
if (qmOrOrd=0) then
qmOrOrd := ParserCreate('qm_order');
ParserClearByHandle(qmOrOrd);
for qmOrI:=0 to qmOrN-1 do
ParserSetIntValueByKeyByHandle(qmOrMods, 'eon'+IntToStr(qmOrI), ParserGetIntValueByKeyByHandle(qmOrMods, 'on'+IntToStr(qmOrI)));
if (qmOrApply) then
begin
   qmOrAn := ParserGetIntValueByKeyByHandle(qmOrRt, 'uiapplyn');
   for qmOrI:=0 to qmOrN-1 do
   if (qmOrI<>qmOrSelf) then
   begin
      qmNormDir(ParserGetValueByKeyByHandle(qmOrMods, 'dir'+IntToStr(qmOrI)), qmOrS);
      for qmOrJ:=0 to qmOrAn-1 do
      begin
         qmNormDir(ParserGetValueByKeyByHandle(qmOrRt, 'uiapplydir'+IntToStr(qmOrJ)), qmOrT);
         if (qmOrT=qmOrS) then
         begin
            qmOrWas := ParserGetIntValueByKeyByHandle(qmOrMods, 'on'+IntToStr(qmOrI));
            qmOrNow := 1-ParserGetIntValueByKeyByHandle(qmOrRt, 'uiapplydis'+IntToStr(qmOrJ));
            ParserSetIntValueByKeyByHandle(qmOrMods, 'on'+IntToStr(qmOrI), qmOrNow);
            if (qmOrWas<>qmOrNow) then
            qmLog('order: apply sets on='+IntToStr(qmOrNow)+' for '+ParserGetValueByKeyByHandle(qmOrMods, 'dir'+IntToStr(qmOrI)));
         end;
      end;
   end;
end;
//! The canonical order (qmModList's), kept; the rows' folded dirs; the rows
//! that are Quartermaster (origin s: its own folder in any spelling).
for qmOrK:=0 to qmOrN-1 do
begin
   qmOrCan[qmOrK] := ParserGetIntValueByKeyByHandle(qmOrMods, 'ord'+IntToStr(qmOrK));
   ParserSetIntValueByKeyByHandle(qmOrMods, 'cord'+IntToStr(qmOrK), qmOrCan[qmOrK]);
   ParserSetIntValueByKeyByHandle(qmOrMods, 'cpos'+IntToStr(qmOrCan[qmOrK]), qmOrK);
end;
for qmOrI:=0 to qmOrN-1 do
begin
   qmNormDir(ParserGetValueByKeyByHandle(qmOrMods, 'dir'+IntToStr(qmOrI)), qmOrNorm[qmOrI]);
   qmOrTaken[qmOrI] := 0;
   qmOrIsSelf[qmOrI] := 0;
   if (ParserGetValueByKeyByHandle(qmOrMods, 'org'+IntToStr(qmOrI))='s') then
   qmOrIsSelf[qmOrI] := 1;
end;
//! The saved order: `;format|1`, then `;o|<dir>` per mod (the parser keeps
//! the leading `;` of each value).
var qmOrSrc : Integer = qmIncLoad('qm_order_src', qmOrPath);
var qmOrCode : Integer = 0;
var qmOrCount : Integer = 0;
if (qmOrSrc<>0) then
qmOrCode := ParserSelectByHandleByKey(qmOrSrc, 'Code');
if (qmOrCode<>0) then
qmOrCount := ParserGetCountByHandle(qmOrCode);
for qmOrK:=0 to qmOrCount-1 do
if (ParserGetValueByIndexByHandle(qmOrCode, qmOrK)=';format|1') then
qmOrHave := 1;
if (qmOrHave=1) then
for qmOrK:=0 to qmOrCount-1 do
begin
   qmOrV := ParserGetValueByIndexByHandle(qmOrCode, qmOrK);
   if (SubStr(qmOrV, 1, 3)=';o|') and (StrLength(qmOrV)>3) and (qmOrSvN<512) then
   begin
      qmOrSv[qmOrSvN] := SubStr(qmOrV, 4, StrLength(qmOrV)-3);
      qmOrSvN := qmOrSvN+1;
   end;
end;
if (qmOrSvN=0) then
qmOrHave := 0;
//! An Apply's order: every registered dir exactly once.
var qmOrUse : Boolean = False;
if (qmOrApply) and (ParserGetIntValueByKeyByHandle(qmOrRt, 'uiapplyorder')=1) then
begin
   qmOrAn := ParserGetIntValueByKeyByHandle(qmOrRt, 'uiapplyordn');
   if (qmOrAn<>qmOrN) then
   qmOrWhy := 'count'
   else
   begin
      for qmOrJ:=0 to qmOrAn-1 do
      if (qmOrWhy='') then
      begin
         qmNormDir(ParserGetValueByKeyByHandle(qmOrRt, 'uiapplyord'+IntToStr(qmOrJ)), qmOrT);
         qmOrHit := -1;
         for qmOrI:=0 to qmOrN-1 do
         if (qmOrHit<0) and (qmOrTaken[qmOrI]=0) and (qmOrNorm[qmOrI]=qmOrT) then
         qmOrHit := qmOrI;
         if (qmOrHit<0) then
         qmOrWhy := 'dirs'
         else
         begin
            qmOrTaken[qmOrHit] := 1;
            if (qmOrIsSelf[qmOrHit]=0) then
            begin
               qmOrRow[qmOrM] := qmOrHit;
               qmOrM := qmOrM+1;
            end;
         end;
      end;
   end;
   if (qmOrWhy='') then
   begin
      qmOrUse := True;
      qmOrSrcName := 'apply';
   end
   else
   begin
      qmLog('order: apply order refused ('+qmOrWhy+'): '+IntToStr(qmOrAn)+' dirs for '+IntToStr(qmOrN)+' mods; the saved order stays');
      qmOrM := 0;
      for qmOrI:=0 to qmOrN-1 do
      qmOrTaken[qmOrI] := 0;
   end;
end;
//! The saved order's dirs that are registered, in its order.
if (not qmOrUse) and (qmOrHave=1) then
begin
   for qmOrJ:=0 to qmOrSvN-1 do
   begin
      qmNormDir(qmOrSv[qmOrJ], qmOrT);
      qmOrHit := -1;
      for qmOrI:=0 to qmOrN-1 do
      if (qmOrHit<0) and (qmOrTaken[qmOrI]=0) and (qmOrIsSelf[qmOrI]=0) and (qmOrNorm[qmOrI]=qmOrT) then
      qmOrHit := qmOrI;
      if (qmOrHit<0) then
      begin
         ParserSetValueByKeyByHandle(qmOrOrd, 'd'+IntToStr(qmOrDropped), qmOrSv[qmOrJ]);
         qmOrDropped := qmOrDropped+1;
         qmLog('order: '+qmOrSv[qmOrJ]+' is no longer registered; it drops out of the saved order');
      end
      else
      begin
         qmOrTaken[qmOrHit] := 1;
         qmOrRow[qmOrM] := qmOrHit;
         qmOrM := qmOrM+1;
      end;
   end;
   qmOrPlaced := qmOrM;
   if (qmOrPlaced>0) then
   qmOrSrcName := 'saved';
   //! An outside reorder: the placed mods are not in mods.ini's order (a
   //! boot's question; an Apply comes after the boot that restored it).
   if (not qmOrApply) then
   for qmOrK:=1 to qmOrPlaced-1 do
   if (qmOrRow[qmOrK]<qmOrRow[qmOrK-1]) then
   qmOrExt := 1;
end;
//! Then every mod not placed, in mods.ini's order (with no saved order: all
//! of them, and nothing moves but Quartermaster), and Quartermaster last.
for qmOrI:=0 to qmOrN-1 do
if (qmOrTaken[qmOrI]=0) and (qmOrIsSelf[qmOrI]=0) then
begin
   qmOrRow[qmOrM] := qmOrI;
   qmOrM := qmOrM+1;
   if (qmOrSrcName='saved') then
   begin
      ParserSetValueByKeyByHandle(qmOrOrd, 'u'+IntToStr(qmOrUnseen), ParserGetValueByKeyByHandle(qmOrMods, 'dir'+IntToStr(qmOrI)));
      qmOrUnseen := qmOrUnseen+1;
      qmLog('order: '+ParserGetValueByKeyByHandle(qmOrMods, 'dir'+IntToStr(qmOrI))+' is not in the saved order yet; placed before Quartermaster');
   end;
end;
for qmOrI:=0 to qmOrN-1 do
if (qmOrIsSelf[qmOrI]=1) then
begin
   qmOrRow[qmOrM] := qmOrI;
   qmOrM := qmOrM+1;
end;
//! Is it canonical, for the mods the next start loads?
qmOrJ := 0;
for qmOrK:=0 to qmOrN-1 do
if (ParserGetIntValueByKeyByHandle(qmOrMods, 'on'+IntToStr(qmOrRow[qmOrK]))=1) then
begin
   while (qmOrJ<qmOrN) and (ParserGetIntValueByKeyByHandle(qmOrMods, 'on'+IntToStr(qmOrCan[qmOrJ]))=0) do
   qmOrJ := qmOrJ+1;
   if (qmOrJ>=qmOrN) then
   qmOrCanon := 0
   else
   if (qmOrCan[qmOrJ]<>qmOrRow[qmOrK]) then
   qmOrCanon := 0;
   qmOrJ := qmOrJ+1;
end;
//! The load order into qm_mods, and the scan list in it.
for qmOrK:=0 to qmOrN-1 do
begin
   qmOrI := qmOrRow[qmOrK];
   ParserSetIntValueByKeyByHandle(qmOrMods, 'ord'+IntToStr(qmOrK), qmOrI);
   ParserSetIntValueByKeyByHandle(qmOrMods, 'pos'+IntToStr(qmOrI), qmOrK);
   if (qmOrCan[qmOrK]<>qmOrI) then
   qmLog('order: mod '+IntToStr(qmOrI)+' pos='+IntToStr(qmOrK)+' (canonical '+IntToStr(ParserGetIntValueByKeyByHandle(qmOrMods, 'cpos'+IntToStr(qmOrI)))+')');
   if (ParserGetIntValueByKeyByHandle(qmOrMods, 'on'+IntToStr(qmOrI))=1) and (qmOrI<>qmOrSelf) and (ParserGetIntValueByKeyByHandle(qmOrMods, 'core'+IntToStr(qmOrI))=0) then
   begin
      ParserSetIntValueByKeyByHandle(qmOrMods, 'e'+IntToStr(qmOrEn), qmOrI);
      qmOrEn := qmOrEn+1;
   end;
end;
ParserSetIntValueByKeyByHandle(qmOrMods, 'en', qmOrEn);
//! order.cfg: what it must hold now (ref/order.py order_file_after).
var qmOrWrite : Boolean = False;
var qmOrDelete : Boolean = False;
var qmOrCount2 : Integer = 0;
for qmOrK:=0 to qmOrN-1 do
if (qmOrIsSelf[qmOrRow[qmOrK]]=0) then
qmOrCount2 := qmOrCount2+1;
qmOrSame := (qmOrCount2=qmOrSvN);
qmOrJ := 0;
if (qmOrSame) then
for qmOrK:=0 to qmOrN-1 do
if (qmOrIsSelf[qmOrRow[qmOrK]]=0) then
begin
   if (ParserGetValueByKeyByHandle(qmOrMods, 'dir'+IntToStr(qmOrRow[qmOrK]))<>qmOrSv[qmOrJ]) then
   qmOrSame := False;
   qmOrJ := qmOrJ+1;
end;
if (qmOrSrcName='apply') then
begin
   //! mods.ini's order, Quartermaster last: what no saved order gives.
   var qmOrIsIni : Boolean = True;
   qmOrJ := 0;
   for qmOrI:=0 to qmOrN-1 do
   if (qmOrIsSelf[qmOrI]=0) then
   begin
      if (qmOrRow[qmOrJ]<>qmOrI) then
      qmOrIsIni := False;
      qmOrJ := qmOrJ+1;
   end;
   for qmOrI:=0 to qmOrN-1 do
   if (qmOrIsSelf[qmOrI]=1) then
   begin
      if (qmOrRow[qmOrJ]<>qmOrI) then
      qmOrIsIni := False;
      qmOrJ := qmOrJ+1;
   end;
   if (qmOrIsIni) then
   qmOrDelete := (qmOrHave=1)
   else
   qmOrWrite := (not qmOrSame);
end
else
if (qmOrSrcName='saved') then
qmOrWrite := (not qmOrSame)
else
qmOrDelete := (qmOrHave=1);
if (qmOrSync) or (qmOrSelf<0) then
begin
   qmOrWrite := False;
   qmOrDelete := False;
end;
if (qmOrWrite) then
begin
   var qmOrHead : array [0..${inchead}] of String;
   var qmOrBytes : Integer = 0;
   var qmOrE : String;
   qmOrHead[0] := 'Name = qmOrder';
   qmIncBegin(qmOrPath, qmOrHead, 1, qmOrCount2+1);
   qmIncLine(';format~1241');
   for qmOrK:=0 to qmOrN-1 do
   if (qmOrIsSelf[qmOrRow[qmOrK]]=0) then
   begin
      qmEscape(ParserGetValueByKeyByHandle(qmOrMods, 'dir'+IntToStr(qmOrRow[qmOrK])), qmOrE);
      qmIncLine(';o~124'+qmOrE);
   end;
   if (qmIncEnd(qmOrBytes)=1) then
   qmOrFile := 'written'
   else
   qmOrFile := 'failed';
end;
if (qmOrDelete) then
begin
   DeleteFileStream(qmOrPath);
   if (FileAge(qmOrPath)=-1) then
   qmOrFile := 'deleted'
   else
   qmOrFile := 'failed';
end;
ParserSetValueByKeyByHandle(qmOrOrd, 'src', qmOrSrcName);
ParserSetIntValueByKeyByHandle(qmOrOrd, 'canon', qmOrCanon);
ParserSetIntValueByKeyByHandle(qmOrOrd, 'ext', qmOrExt);
ParserSetIntValueByKeyByHandle(qmOrOrd, 'unseen', qmOrUnseen);
ParserSetIntValueByKeyByHandle(qmOrOrd, 'dropped', qmOrDropped);
ParserSetValueByKeyByHandle(qmOrOrd, 'file', qmOrFile);
ParserSetValueByKeyByHandle(qmOrOrd, 'why', qmOrWhy);
qmLog('order: src='+qmOrSrcName+' canon='+IntToStr(qmOrCanon)+' ext='+IntToStr(qmOrExt)+' unseen='+IntToStr(qmOrUnseen)+' dropped='+IntToStr(qmOrDropped)+' order.cfg='+qmOrFile);
var qmOrIn : Integer = ParserSelectByKey('qm_ini_in');
if (qmOrIn=0) then
qmOrIn := ParserCreate('qm_ini_in');
ParserClearByHandle(qmOrIn);
ParserSetIntValueByKeyByHandle(qmOrIn, 'n', qmOrN);
for qmOrK:=0 to qmOrN-1 do
begin
   qmOrI := qmOrRow[qmOrK];
   ParserSetValueByKeyByHandle(qmOrIn, 'dir'+IntToStr(qmOrK), ParserGetValueByKeyByHandle(qmOrMods, 'dir'+IntToStr(qmOrI)));
   if (ParserGetIntValueByKeyByHandle(qmOrMods, 'on'+IntToStr(qmOrI))=1) then
   ParserSetValueByKeyByHandle(qmOrIn, 'dis'+IntToStr(qmOrK), 'False')
   else
   ParserSetValueByKeyByHandle(qmOrIn, 'dis'+IntToStr(qmOrK), 'True');
end;
var qmOrIni : Integer = ParserSelectByKey('qm_ini');
if (qmOrIni=0) then
qmOrIni := ParserCreate('qm_ini');
ParserClearByHandle(qmOrIni);
ParserSetValueByKeyByHandle(qmOrIni, 'action', 'skipped');
ParserSetIntValueByKeyByHandle(qmOrIni, 'effective', 0);
if (qmOrSync) then
begin
   ParserSetValueByKeyByHandle(qmOrIni, 'why', 'mp-sync');
   qmLog('order: mods.ini and order.cfg left alone during an MP mod sync');
end
else
if (qmOrSelf<0) then
begin
   ParserSetValueByKeyByHandle(qmOrIni, 'action', 'refused');
   ParserSetValueByKeyByHandle(qmOrIni, 'why', 'no-self');
   qmLog('order: Quartermaster''s own folder is unknown; mods.ini left alone');
end
else
StateMachineExecuteState(GetTriggerManagerStateMachineHandle('qm_core'), 'qmModsIni', 0);
//! The set an Apply put into mods.ini, for the start-up guard (plan S17,
//! 0.1.3): <save>\quartermaster\chosen.cfg, d<k> every mod the applied rows
//! enable (Quartermaster too) as they spell the dir, in the new load order,
//! then n - compiled.cfg's format (ref/guard.py compiled_values). Two mods
//! that ship the same core script and never started together are switched
//! off before the compile, unless the player chose them together here: the
//! guard trusts this set at the next start, and undoes it if that start
//! stops. Written only when mods.ini holds exactly these rows (qmModsIni
//! written or same); the boot after it (qmGlobals) sets n = 0 again.
if (qmOrApply) then
begin
   var qmOrAct : String = ParserGetValueByKeyByHandle(qmOrIni, 'action');
   if (qmOrAct='written') or (qmOrAct='same') then
   begin
      var qmOrCh : Integer = ParserSelectByKey('qm_order_chosen');
      if (qmOrCh=0) then
      qmOrCh := ParserCreate('qm_order_chosen');
      ParserClearByHandle(qmOrCh);
      qmOrJ := 0;
      for qmOrK:=0 to qmOrN-1 do
      if (ParserGetValueByKeyByHandle(qmOrIn, 'dis'+IntToStr(qmOrK))='False') then
      begin
         ParserSetValueByKeyByHandle(qmOrCh, 'd'+IntToStr(qmOrJ), ParserGetValueByKeyByHandle(qmOrIn, 'dir'+IntToStr(qmOrK)));
         qmOrJ := qmOrJ+1;
      end;
      ParserSetValueByKeyByHandle(qmOrCh, 'n', IntToStr(qmOrJ));
      if (ParserSaveToFileByHandle(qmOrCh, GetAppSaveDirectoryPath+'quartermaster\chosen.cfg')) then
      qmLog('ui apply chosen=written n='+IntToStr(qmOrJ))
      else
      qmLog('ui apply chosen=not-saved n='+IntToStr(qmOrJ));
   end
   else
   qmLog('ui apply chosen=- mods.ini='+qmOrAct);
end;
