state: qmGuard
into: data/quartermaster/core.aix
helpers: qmlog, qmstr
requires: ownfiles
---
//! The loop guards of plan S8 and the restart decision of G14, in two steps
//! qmBoot runs around the generation (qm_guard `step`). ref/boot.py is the
//! twin - boot_plan, restart_plan, next_marker, damaged, unstable_fp - and its
//! docstring has every rule, its order and its evidence; this state follows it
//! rule for rule. Inputs: the marker (qm_state, qmMarkerLoad), qm_rt (fp from
//! qmFingerprint, sync and unstable from qmBoot, runmode, qmdir), and for the
//! second step qm_gen (qmGenerate: status, gen, changed, w<m>, sp<k>/sr<k>)
//! and qm_ini (qmModsIni: action, effective).
//!
//! step plan: regenerate? and in which mode. The phase this start is in, the
//! boot count and rk = - go into qm_state at once, and qmBoot saves them
//! before anything else runs: a start that dies inside the generation leaves
//! `booting`, which the next start reads as a suspected brick and answers
//! with the winner-takes-all fallback - no merge is tried a second time.
//!
//! step restart: restart? (an output's content or the effective mods.ini
//! order changed; refused by an MP sync, a SelfTest run that did not ask for
//! restarts (qm_rt norestart), the loop rule - unless only mods registered at
//! this start moved the inputs: fpold is the marker's hash - two in a row or
//! one per hash),
//! then the whole next marker into qm_state, with the FileAge of
//! every output the generation left in the mirror - the stamps the next boot
//! compares (damaged). qmBoot saves it and schedules the restart, or runs it
//! itself after a start that rewrote its outputs (qmboot.pas).
//!
//! qm_guard keys: step; plan: regen (0/1), mode, why, followed, suspect,
//! phase, boots, damaged, fp, fpold; restart: wanted, restart, kind, rwhy,
//! refused.
var qmGdG : Integer = ParserSelectByKey('qm_guard');
if (qmGdG=0) then
qmGdG := ParserCreate('qm_guard');
var qmGdSt : Integer = ParserSelectByKey('qm_state');
var qmGdRt : Integer = ParserSelectByKey('qm_rt');
var qmGdApply : Boolean = (ParserGetValueByKeyByHandle(qmGdRt, 'runmode')='apply');
var qmGdHave : Boolean = (ParserGetIntValueByKeyByHandle(qmGdSt, 'have')=1);
var qmGdSync : Boolean = (ParserGetIntValueByKeyByHandle(qmGdRt, 'sync')=1);
var qmGdHash : String = ParserGetValueByKeyByHandle(qmGdSt, 'hash');
var qmGdPhase : String = ParserGetValueByKeyByHandle(qmGdSt, 'phase');
var qmGdK : Integer;
var qmGdN : Integer;
var qmGdS : String;
var qmGdT : String;
var qmGdFp : String;
if (ParserGetValueByKeyByHandle(qmGdG, 'step')='plan') then
begin
   var qmGdBoots : Integer = ParserGetIntValueByKeyByHandle(qmGdSt, 'boots');
   if (not qmGdApply) then
   qmGdBoots := qmGdBoots+1;
   qmGdFp := ParserGetValueByKeyByHandle(qmGdRt, 'fp');
   ParserSetValueByKeyByHandle(qmGdRt, 'fpinputs', qmGdFp);
   //! The fingerprint without the mods registered at this start
   //! (qmFingerprint fpold; none: the fingerprint itself), salted alike.
   var qmGdFpOld : String = ParserGetValueByKeyByHandle(qmGdRt, 'fpold');
   if (qmGdFpOld='') then
   qmGdFpOld := qmGdFp;
   //! The I5 run: a salt that changes with every boot (ref/boot.py unstable_fp).
   if (ParserGetIntValueByKeyByHandle(qmGdRt, 'unstable')=1) then
   begin
      qmGdFp := qmGdFp+'|unstable '+IntToStr(qmGdBoots);
      qmGdFpOld := qmGdFpOld+'|unstable '+IntToStr(qmGdBoots);
      ParserSetValueByKeyByHandle(qmGdRt, 'fp', qmGdFp);
   end;
   ParserSetValueByKeyByHandle(qmGdG, 'fpold', qmGdFpOld);
   //! Damaged: a recorded output whose FileAge moved (FileAge ignores the
   //! overlay and reads exactly that file, capability probe 5). The path is
   //! the mod dir as the engine lists it, relative to the game folder: the
   //! spelling the engine loads the mod's files by and the writer writes them
   //! by (src/lib/qmwrite.pas qmWrDst), and the one qmModList asks FileAge
   //! with. The same spelling records the stamps below.
   var qmGdDamaged : Boolean = False;
   ParserSetIntValueByKeyByHandle(qmGdG, 'recheck', 0);
   var qmGdBase : String = ParserGetValueByKeyByHandle(qmGdRt, 'qmdir');
   if (qmGdHave) and (qmGdBase<>'') then
   begin
      qmGdBase := qmGdBase+'\data\';
      qmGdN := ParserGetIntValueByKeyByHandle(qmGdSt, 'on');
      for qmGdK:=0 to qmGdN-1 do
      begin
         qmGdS := ParserGetValueByKeyByHandle(qmGdSt, 'op'+IntToStr(qmGdK));
         if (IntToStr(FileAge(qmGdBase+qmGdS))<>ParserGetValueByKeyByHandle(qmGdSt, 'oa'+IntToStr(qmGdK))) then
         begin
            if (not qmGdDamaged) then
            begin
               if (ParserGetValueByKeyByHandle(qmGdSt, 'oa'+IntToStr(qmGdK))='0') then
               begin
                  //! Recorded by an Apply that could not check it (below).
                  ParserSetIntValueByKeyByHandle(qmGdG, 'recheck', 1);
                  qmLog('guard: output '+qmGdS+' fell back in an Apply that could not check it against the scripts of the new set; built again now');
               end
               else
               qmLog('guard: output '+qmGdS+' changed on disk (FileAge '+IntToStr(FileAge(qmGdBase+qmGdS))+', recorded '+ParserGetValueByKeyByHandle(qmGdSt, 'oa'+IntToStr(qmGdK))+')');
            end;
            qmGdDamaged := True;
         end;
      end;
   end;
   var qmGdFollowed : Boolean = (not qmGdApply) and (qmGdHave) and (ParserGetValueByKeyByHandle(qmGdSt, 'rk')<>'-');
   var qmGdSuspect : Boolean = (not qmGdApply) and (qmGdHave) and (qmGdPhase='booting');
   var qmGdNewPhase : String = qmGdPhase;
   if (not qmGdApply) then
   begin
      if (qmGdHave) and ((qmGdPhase='written') or (qmGdPhase='booting')) then
      qmGdNewPhase := 'booting'
      else
      qmGdNewPhase := 'booted';
   end;
   var qmGdRegen : Integer = 0;
   var qmGdMode : String = 'normal';
   var qmGdWhy : String;
   if (qmGdSync) then
   qmGdWhy := 'mp-sync'
   else
   if (qmGdApply) then
   begin
      qmGdRegen := 1;
      qmGdWhy := 'apply';
   end
   else
   if (not qmGdHave) then
   begin
      qmGdRegen := 1;
      qmGdWhy := 'first';
   end
   else
   if (qmGdSuspect) and (qmGdFp=qmGdHash) then
   begin
      qmGdRegen := 1;
      qmGdMode := 'wta';
      qmGdWhy := 'suspected-brick';
   end
   else
   if (qmGdFp<>qmGdHash) then
   begin
      qmGdRegen := 1;
      qmGdWhy := 'inputs-changed';
   end
   else
   if (ParserGetValueByKeyByHandle(qmGdSt, 'mode')='wta') then
   begin
      qmGdMode := 'wta';
      if (qmGdDamaged) then
      begin
         qmGdRegen := 1;
         qmGdWhy := 'damaged';
      end
      else
      qmGdWhy := 'fallback-kept';
   end
   else
   if (qmGdDamaged) then
   begin
      qmGdRegen := 1;
      qmGdWhy := 'damaged';
   end
   else
   qmGdWhy := 'stable';
   ParserSetIntValueByKeyByHandle(qmGdG, 'regen', qmGdRegen);
   ParserSetValueByKeyByHandle(qmGdG, 'mode', qmGdMode);
   ParserSetValueByKeyByHandle(qmGdG, 'why', qmGdWhy);
   ParserSetValueByKeyByHandle(qmGdG, 'fp', qmGdFp);
   ParserSetValueByKeyByHandle(qmGdG, 'phase', qmGdNewPhase);
   ParserSetIntValueByKeyByHandle(qmGdG, 'boots', qmGdBoots);
   ParserSetValueByKeyByHandle(qmGdG, 'followed', BoolToStr(qmGdFollowed));
   ParserSetValueByKeyByHandle(qmGdG, 'suspect', BoolToStr(qmGdSuspect));
   ParserSetValueByKeyByHandle(qmGdG, 'damaged', BoolToStr(qmGdDamaged));
   //! The start's own marker fields, saved by qmBoot before the generation.
   ParserSetIntValueByKeyByHandle(qmGdSt, 'boots', qmGdBoots);
   ParserSetValueByKeyByHandle(qmGdSt, 'phase', qmGdNewPhase);
   if (not qmGdApply) then
   ParserSetValueByKeyByHandle(qmGdSt, 'rk', '-');
   qmLog('guard plan regen='+IntToStr(qmGdRegen)+' mode='+qmGdMode+' why='+qmGdWhy+' phase='+qmGdPhase+'->'+qmGdNewPhase+' followed='+BoolToStr(qmGdFollowed)+' suspect='+BoolToStr(qmGdSuspect)+' damaged='+BoolToStr(qmGdDamaged)+' fp='+qmGdFp+' marker hash='+qmGdHash);
end
else
if (ParserGetValueByKeyByHandle(qmGdG, 'step')='restart') then
begin
   var qmGdGen : Integer = ParserSelectByKey('qm_gen');
   var qmGdIni : Integer = ParserSelectByKey('qm_ini');
   var qmGdPlan : Integer = ParserSelectByKey('qm_plan');
   var qmGdR : Boolean = (ParserGetIntValueByKeyByHandle(qmGdG, 'regen')=1);
   var qmGdOk : Boolean = qmGdR and (qmGdGen<>0);
   if (qmGdOk) then
   qmGdOk := (ParserGetValueByKeyByHandle(qmGdGen, 'status')='ok');
   var qmGdChanged : Integer = 0;
   if (qmGdR) and (qmGdGen<>0) then
   qmGdChanged := ParserGetIntValueByKeyByHandle(qmGdGen, 'changed');
   var qmGdMods : Boolean = False;
   if (qmGdIni<>0) then
   qmGdMods := ((ParserGetValueByKeyByHandle(qmGdIni, 'action')='same') or (ParserGetValueByKeyByHandle(qmGdIni, 'action')='written')) and (ParserGetIntValueByKeyByHandle(qmGdIni, 'effective')=1);
   //! Only Quartermaster's own place changed (qmModsIni selfonly): the mods it
   //! moved past decide nothing a restart would change when none ships a path
   //! the index read (qm_index v<k>, load positions) or a file of
   //! Quartermaster's the index does not read (${ownfiles}). ref/order.py
   //! needs_restart; a folder made with New mod cost a restart for that.
   if (qmGdMods) and (ParserGetIntValueByKeyByHandle(qmGdIni, 'selfonly')=1) then
   begin
      var qmGdIdx : Integer = ParserSelectByKey('qm_index');
      var qmGdMl : Integer = ParserSelectByKey('qm_mods');
      var qmGdOv : Integer = ParserGetIntValueByKeyByHandle(qmGdIni, 'overn');
      var qmGdShips : Boolean = (qmGdIdx=0);
      var qmGdRow : Integer;
      var qmGdI : Integer;
      var qmGdPos : String;
      var qmGdDir : String;
      var qmGdF : String;
      for qmGdK:=0 to qmGdOv-1 do
      begin
         qmGdRow := ParserGetIntValueByKeyByHandle(qmGdIni, 'over'+IntToStr(qmGdK));
         qmGdPos := ';'+ParserGetValueByKeyByHandle(qmGdMl, 'pos'+IntToStr(qmGdRow))+';';
         qmGdDir := ParserGetValueByKeyByHandle(qmGdMl, 'dir'+IntToStr(qmGdRow));
         if (qmGdIdx<>0) then
         for qmGdI:=0 to ParserGetIntValueByKeyByHandle(qmGdIdx, 'n')-1 do
         if (StrPos(qmGdPos, ';'+ParserGetValueByKeyByHandle(qmGdIdx, 'v'+IntToStr(qmGdI))+';')>0) then
         qmGdShips := True;
         qmGdI := 1;
         qmField(${ownfiles}, '|', qmGdI, qmGdF);
         while (qmGdF<>'') do
         begin
            if (FileAge(qmGdDir+'\data\'+qmGdF)<>-1) then
            qmGdShips := True;
            qmGdI := qmGdI+1;
            qmField(${ownfiles}, '|', qmGdI, qmGdF);
         end;
      end;
      if (not qmGdShips) then
      begin
         qmGdMods := False;
         qmLog('guard: mods.ini only moved Quartermaster past '+IntToStr(qmGdOv)+' mod(s) that ship none of its files and no file the index reads: no restart for that');
      end;
   end;
   qmGdFp := ParserGetValueByKeyByHandle(qmGdG, 'fp');
   var qmGdRows : Integer = ParserGetIntValueByKeyByHandle(qmGdSt, 'rows');
   var qmGdRhash : String = ParserGetValueByKeyByHandle(qmGdSt, 'rhash');
   var qmGdRcount : Integer = ParserGetIntValueByKeyByHandle(qmGdSt, 'rcount');
   var qmGdWanted : Boolean = (qmGdChanged>0) or (qmGdMods);
   var qmGdRestart : Boolean = False;
   var qmGdKind : String = '-';
   var qmGdRwhy : String = 'nothing-changed';
   var qmGdRefused : String = '';
   if (qmGdWanted) then
   begin
      if (qmGdChanged>0) then
      qmGdRwhy := 'outputs-changed'
      else
      qmGdRwhy := 'mods-ini-changed';
      if (qmGdSync) then
      qmGdRefused := 'mp-sync'
      else
      if (ParserGetIntValueByKeyByHandle(qmGdRt, 'norestart')=1) then
      qmGdRefused := 'selftest'
      else
      if (qmGdApply) then
      begin
         qmGdRestart := True;
         qmGdKind := 'apply';
      end
      else
      if (ParserGetValueByKeyByHandle(qmGdG, 'followed')='True') and (qmGdFp<>qmGdHash) and (ParserGetValueByKeyByHandle(qmGdG, 'fpold')<>qmGdHash) then
      qmGdRefused := 'loop'
      else
      if (qmGdHave) and (qmGdRows>=2) then
      qmGdRefused := 'in-a-row'
      else
      if (qmGdHave) and (qmGdRhash=qmGdFp) and (qmGdRcount>=1) then
      qmGdRefused := 'per-hash'
      else
      begin
         qmGdRestart := True;
         qmGdKind := 'auto';
      end;
   end;
   if (qmGdWanted) and (not qmGdApply) and (ParserGetValueByKeyByHandle(qmGdG, 'followed')='True') and (qmGdFp<>qmGdHash) and (ParserGetValueByKeyByHandle(qmGdG, 'fpold')=qmGdHash) then
   qmLog('guard: across Quartermaster''s restart only mods registered at this start changed the inputs: not a loop');
   //! The next marker (ref/boot.py next_marker).
   if (qmGdR) and (qmGdOk) then
   begin
      ParserSetIntValueByKeyByHandle(qmGdSt, 'gen', ParserGetIntValueByKeyByHandle(qmGdGen, 'gen'));
      ParserSetValueByKeyByHandle(qmGdSt, 'mode', ParserGetValueByKeyByHandle(qmGdG, 'mode'));
      ParserSetValueByKeyByHandle(qmGdSt, 'hash', qmGdFp);
      if (qmGdChanged>0) then
      ParserSetValueByKeyByHandle(qmGdSt, 'phase', 'written');
      //! The stamps: every output the mirror holds now - the plan's files the
      //! writer wrote or found equal, the stale files it overwrote, the
      //! manifest - with its FileAge (ref/boot.py damaged reads them back).
      var qmGdBase2 : String = ParserGetValueByKeyByHandle(qmGdRt, 'qmdir')+'\data\';
      var qmGdOn : Integer = 0;
      qmGdN := ParserGetIntValueByKeyByHandle(qmGdPlan, 'n');
      for qmGdK:=0 to qmGdN-1 do
      begin
         qmGdT := ParserGetValueByKeyByHandle(qmGdGen, 'w'+IntToStr(qmGdK));
         if (qmGdT='yes') or (qmGdT='same') then
         begin
            qmGdS := ParserGetValueByKeyByHandle(qmGdPlan, 'path'+IntToStr(qmGdK));
            ParserSetValueByKeyByHandle(qmGdSt, 'op'+IntToStr(qmGdOn), qmGdS);
            ParserSetValueByKeyByHandle(qmGdSt, 'oa'+IntToStr(qmGdOn), IntToStr(FileAge(qmGdBase2+qmGdS)));
            //! An Apply checks what it merges against the scripts this process
            //! loaded, not the ones the new set brings: a file that fell back
            //! then (qm_gen x = fallback) may only have missed the library of a
            //! mod just switched on. Its age is recorded as 0, which no file
            //! has, so the next start finds it changed and builds it again
            //! with the new set loaded - once: a start's own generation
            //! records the real age (ref/boot.py recorded_age). Hands-on,
            //! 2026-10-10: Reinforced - Core's DoProgress would have stayed
            //! out of the merge for good.
            if (qmGdApply) and (ParserGetValueByKeyByHandle(qmGdGen, 'x'+IntToStr(qmGdK))='fallback') then
            ParserSetValueByKeyByHandle(qmGdSt, 'oa'+IntToStr(qmGdOn), '0');
            qmGdOn := qmGdOn+1;
         end;
      end;
      qmGdN := ParserGetIntValueByKeyByHandle(qmGdGen, 'sn');
      for qmGdK:=0 to qmGdN-1 do
      if (ParserGetValueByKeyByHandle(qmGdGen, 'sr'+IntToStr(qmGdK))='overwritten') then
      begin
         qmGdS := ParserGetValueByKeyByHandle(qmGdGen, 'sp'+IntToStr(qmGdK));
         ParserSetValueByKeyByHandle(qmGdSt, 'op'+IntToStr(qmGdOn), qmGdS);
         ParserSetValueByKeyByHandle(qmGdSt, 'oa'+IntToStr(qmGdOn), IntToStr(FileAge(qmGdBase2+qmGdS)));
         qmGdOn := qmGdOn+1;
      end;
      qmGdS := 'quartermaster\state\manifest.cfg';
      ParserSetValueByKeyByHandle(qmGdSt, 'op'+IntToStr(qmGdOn), qmGdS);
      ParserSetValueByKeyByHandle(qmGdSt, 'oa'+IntToStr(qmGdOn), IntToStr(FileAge(qmGdBase2+qmGdS)));
      qmGdOn := qmGdOn+1;
      ParserSetIntValueByKeyByHandle(qmGdSt, 'on', qmGdOn);
   end;
   if (qmGdRestart) then
   begin
      ParserSetValueByKeyByHandle(qmGdSt, 'rk', qmGdKind);
      if (qmGdKind='auto') then
      begin
         ParserSetIntValueByKeyByHandle(qmGdSt, 'rows', qmGdRows+1);
         if (qmGdHave) and (qmGdRhash=qmGdFp) then
         ParserSetIntValueByKeyByHandle(qmGdSt, 'rcount', qmGdRcount+1)
         else
         ParserSetIntValueByKeyByHandle(qmGdSt, 'rcount', 1);
         ParserSetValueByKeyByHandle(qmGdSt, 'rhash', qmGdFp);
      end
      else
      begin
         ParserSetIntValueByKeyByHandle(qmGdSt, 'rows', 0);
         ParserSetValueByKeyByHandle(qmGdSt, 'rhash', '-');
         ParserSetIntValueByKeyByHandle(qmGdSt, 'rcount', 0);
      end;
   end
   else
   if (qmGdRefused='') and (not qmGdSync) and (not qmGdApply) then
   begin
      //! A start that needed no restart ends the chain of automatic ones.
      ParserSetIntValueByKeyByHandle(qmGdSt, 'rows', 0);
      ParserSetValueByKeyByHandle(qmGdSt, 'rhash', '-');
      ParserSetIntValueByKeyByHandle(qmGdSt, 'rcount', 0);
   end;
   ParserSetValueByKeyByHandle(qmGdG, 'wanted', BoolToStr(qmGdWanted));
   if (qmGdRestart) then
   ParserSetIntValueByKeyByHandle(qmGdG, 'restart', 1)
   else
   ParserSetIntValueByKeyByHandle(qmGdG, 'restart', 0);
   ParserSetValueByKeyByHandle(qmGdG, 'kind', qmGdKind);
   ParserSetValueByKeyByHandle(qmGdG, 'rwhy', qmGdRwhy);
   ParserSetValueByKeyByHandle(qmGdG, 'refused', qmGdRefused);
   qmLog('guard restart='+BoolToStr(qmGdRestart)+' kind='+qmGdKind+' why='+qmGdRwhy+' refused='+qmGdRefused+' changed='+IntToStr(qmGdChanged)+' modsini='+BoolToStr(qmGdMods)+' generated='+BoolToStr(qmGdOk)+' rows='+IntToStr(ParserGetIntValueByKeyByHandle(qmGdSt, 'rows')));
end;
