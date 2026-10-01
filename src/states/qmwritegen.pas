state: qmGenerate
into: data/quartermaster/core.aix
helpers: qmlog, qmstr, qmwrite, qmmanifest
requires: rawcap, inchead
---
//! One generation (plan G11, G12, runtime flow): for every file the planner
//! decided to merge or hook, merge -> validate -> (fall back) -> write, then
//! remove the outputs of the previous generation that are no longer needed
//! and write the manifest. ref/validate.py generate is the twin, rule for
//! rule and in the same order.
//!
//! Inputs: qm_plan, qm_mods, qm_index (the boot pipeline), qm_rt (qmdir, fp)
//! and the optional parser qm_gen_in: `sandbox` (a SelfTest label: every file
//! goes under <save>\qm_test\out\m4\<label>\, see qmWrOpen), `hookdir`
//! (`cases`: the pristine hook files come from <save>\qm_test\cases\; `qm`:
//! from Quartermaster's own folder even in a sandbox - the activation
//! check, qmTrial; else from the mirror's data\quartermaster\hooks\), `wta` (1: the boot
//! suspects the last generation kept the game from starting, plan S8 -
//! nothing is merged: merge-inc paths get no output and their earlier
//! outputs go stale, hook paths try winner+hook and vanilla+hook) and
//! `gensalt` (appended to the generation constant; the boot's unstable-
//! fingerprint test). Results: qm_gen (keys below), the files, [qm] log
//! lines. The caller runs qmReport afterwards, so the boot can add its own
//! block to the report first.
//!
//! Phase B (plan S3, S10): a merge-data decision is a job of qmDataMerge
//! (qm_dm_in / qm_dm), run once for all of them after qmMerge: its one
//! candidate is the merged file, checked and trial-loaded there and gated by
//! qm_val d<seq> (qmWrDataOut); a job that fails stages nothing, and the
//! winner's file stays in effect (x<m> datafail). The bounds come from the
//! dmscript.global in effect: the last enabled mod's copy (qm_index), else
//! vanilla's.
//!
//! Phase 1, nothing is written into the data mirror yet:
//!   - one call of qmMerge for every merge of the generation (a batch: its
//!     String pool costs about 0.3 s per call, M3), with no hook lines and the
//!     output staged in the work folder;
//!   - a second qmMerge batch into qm_ms: for a merged file with conflicts,
//!     the merge without the participants that lost one (subset), when at
//!     least two stay;
//!   - per path the candidates of plan S7 in order - merge-inc: merged,
//!     subset, winner; hook: merged+hook, subset+hook, winner+hook,
//!     vanilla+hook (a chosen subset is `partial`, WARN) - each staged as
//!     <work>val\<seq>.inc, its validation copy <work>val\<seq>.aix run in the
//!     validation manager, until one compiles. Quartermaster's hook lines go
//!     in at qmIncHookIndex of the file they join (plan S5), the same index
//!     qmMerge would use;
//!   - CameraControl comes last: its hook lines carry the generation constant
//!     (plan S6), the outputs hash of this generation (ref/manifest.py
//!     outputs_hash), which needs every other output first.
//! vanilla+hook not compiling is a build bug: FATAL, and phase 2 does not run,
//! so nothing at all is written (plan S7).
//! Phase 2: qmWrOutput per chosen candidate (it re-checks the validation flag
//! against the staged bytes), stale cleanup per plan S9 (qmWrDelete, and an
//! undeletable file overwritten with the validated file the game should use
//! now), the manifest (qmWrManifest).
//!
//! A candidate whose token equals the file already in the mirror is not
//! written again (qmWrOutput 2, w<m> = same): the file keeps its bytes and its
//! FileAge, and `changed` - what the boot restarts for - does not count it.
//!
//! qm_gen keys: status (ok, fatal, error), box, work, n, gen, prevgen,
//! outhash, fp, fatal, written (w=yes), same (w=same), changed (written plus
//! stale files deleted or overwritten), failed, removed; per plan decision m: x<m>
//! result code, s<m> OK/WARN/FAIL/FATAL, j<m> merge job or -1, e<m> merge
//! error, sj<m> the subset's job in qm_ms and lo<m> the losers it leaves out
//! (positions, `;`; both only when there is one), pp<m> participants
//! (canonical positions, `;`), pw<m> winner, vf<m>
//! vanilla's first Code line (1-based), vn<m> its value count, t<m> tries and
//! t<m>_<k> `tier|seq|token|ok`, ci<m> the planned index of the chosen
//! candidate, r<m> k<m> h<m> f<m> its tier, token, token without the
//! generation line, staged file, w<m> the write (yes, same, refused, failed,
//! -);
//! stale: sn, sp<k> sr<k> ss<k> sc<k> (path, deleted/overwritten/failed/
//! refused, the source written over it, `stale|seq|token|ok`); pn, po<k> the
//! previous manifest's files.
var qmGnIn : Integer = ParserSelectByKey('qm_gen_in');
var qmGnBox : String = '';
var qmGnHooks : String = '';
var qmGnG : Integer = ParserSelectByKey('qm_gen');
var qmGnPlan : Integer = ParserSelectByKey('qm_plan');
var qmGnMods : Integer = ParserSelectByKey('qm_mods');
var qmGnIdx : Integer = ParserSelectByKey('qm_index');
var qmGnKeys : Integer = ParserSelectByKey('qm_index_keys');
var qmGnRt : Integer = ParserSelectByKey('qm_rt');
var qmGnMg : Integer = 0;
var qmGnMin : Integer = 0;
var qmGnApp : String = ExtractFilePath(GetApplicationFileName);
var qmGnPool : array [0..${rawcap}] of String;
var qmGnHead : array [0..${inchead}] of String;
var qmGnHk : array [0..${inchead}] of String;
var qmGnAct : array [0..511] of Integer;
var qmGnJob : array [0..511] of Integer;
var qmGnDone : array [0..511] of Integer;
var qmGnSeq : array [0..511] of Integer;
var qmGnSize : array [0..511] of Integer;
var qmGnDj : array [0..511] of Integer;
var qmGnSj : array [0..511] of Integer;
var qmGnSk : array [0..511] of String;
var qmGnSjobs : Integer = 0;
var qmGnMs : Integer = 0;
var qmGnKc : Integer;
var qmGnLo : String;
var qmGnSm : Integer;
var qmGnSr : Integer;
var qmGnSt : String;
var qmGnSs : String;
var qmGnSp : String;
var qmGnSd : String;
var qmGnLs : String;
var qmGnLr : String;
var qmGnLf : String;
var qmGnLp : String;
var qmGnLx : String;
var qmGnDin : Integer = 0;
var qmGnDm : Integer = 0;
var qmGnDjobs : Integer = 0;
var qmGnN : Integer = 0;
var qmGnSelf : String = '-';
var qmGnFatal : String = '';
var qmGnJobs : Integer = 0;
var qmGnHit : Integer = 0;
var qmGnSeen : String = '';
var qmGnNh : Integer = 0;
var qmGnForm : Integer = 0;
var qmGnHn : Integer = 0;
var qmGnOpen : Integer = 0;
var qmGnPrev : Integer = 0;
var qmGnPrevGen : Integer = 0;
var qmGnPrevHash : String = '';
var qmGnPn : Integer = 0;
var qmGnOutHash : String = '';
var qmGnGen : Integer = 1;
var qmGnFp : String = '-';
var qmGnWritten : Integer = 0;
var qmGnSame : Integer = 0;
var qmGnChanged : Integer = 0;
var qmGnWta : Integer = 0;
var qmGnSalt : String = '';
var qmGnFailed : Integer = 0;
var qmGnRemoved : Integer = 0;
var qmGnSn : Integer = 0;
var qmGnL : Integer = 0;
var qmGnM : Integer;
var qmGnK : Integer;
var qmGnI : Integer;
var qmGnJ : Integer;
var qmGnPass : Integer;
var qmGnC : Integer;
var qmGnR : Integer;
var qmGnS : String;
var qmGnT : String;
var qmGnU : String;
var qmGnP : String;
var qmGnV : String;
var qmGnW : String;
var qmGnJs : String;
var qmGnTok : String;
var qmGnSeqS : Integer;
var qmGnBytes : Integer;
var qmGnOk : Integer;
var qmGnCur : Boolean;

//! Dir of the mod at canonical position qmGdPos (text).
procedure qmGnDir(const qmGdPos : String; var qmGdOut : String);
begin
   qmGdOut := ParserGetValueByKeyByHandle(qmGnMods, 'dir'+IntToStr(ParserGetIntValueByKeyByHandle(qmGnMods, 'ord'+qmGdPos)));
end;

procedure qmGnPath(const qmGpM : Integer; var qmGpOut : String);
begin
   qmGpOut := ParserGetValueByKeyByHandle(qmGnPlan, 'path'+IntToStr(qmGpM));
end;

//! A file into the pool at qmGlAt: values there, key lines in qmGnHead.
procedure qmGnLoad(const qmGlPath : String; const qmGlSize : Integer; const qmGlAt : Integer; var qmGlN : Integer);
begin
   qmGnNh := 0;
   qmGnForm := 0;
   qmIncReadAt(qmGlPath, qmGlSize, qmGnPool, qmGlAt, qmGnHead, qmGnNh, qmGlN, qmGnForm);
end;

//! The outputs hash (ref/manifest.py outputs_hash) over the paths chosen so
//! far, plan order, with qmGhTok standing for decision qmGhM (-1: none).
procedure qmGnHash(const qmGhM : Integer; const qmGhTok : String; var qmGhOut : String);
begin
   var qmGhH1 : Integer = 0;
   var qmGhH2 : Integer = 0;
   var qmGhL : Integer = 0;
   var qmGhK : Integer;
   var qmGhT : String;
   var qmGhP : String;
   for qmGhK:=0 to qmGnN-1 do
   begin
      qmGhT := '';
      if (qmGhK=qmGhM) then
      qmGhT := qmGhTok
      else
      if (qmGnDone[qmGhK]=1) then
      qmGhT := ParserGetValueByKeyByHandle(qmGnG, 'h'+IntToStr(qmGhK));
      if (qmGhT<>'') then
      begin
         qmGnPath(qmGhK, qmGhP);
         qmHashStr(qmGhP+'|'+qmGhT, qmGhH1, qmGhH2, qmGhL);
         qmHashByte(10, qmGhH1, qmGhH2, qmGhL);
      end;
   end;
   qmHashText(qmGhH1, qmGhH2, qmGhL, qmGhOut);
end;

//! One candidate: pool[qmGtAt..] with the key lines in qmGnHead. Skipped when
//! a candidate of the same path had the same token (it would compile the
//! same way); qmGtIdx is its place among the planned candidates.
procedure qmGnTry(const qmGtM : Integer; const qmGtTier : String; const qmGtIdx : Integer; const qmGtAt : Integer; const qmGtN : Integer);
begin
   var qmGtTok : String = '';
   var qmGtH : String = '';
   var qmGtSeq : Integer = 0;
   var qmGtBytes : Integer = 0;
   var qmGtOk : Integer = 0;
   var qmGtK : Integer;
   var qmGtMs : String = IntToStr(qmGtM);
   var qmGtStaged : String;
   var qmGtWrap : String;
   var qmGtP : String;
   qmValToken(qmGnPool, qmGtAt, qmGtN, qmGnHead, qmGnNh, 0, qmGtTok);
   if (StrPos('|'+qmGtTok+'|', qmGnSeen)=0) then
   begin
      qmGnSeen := qmGnSeen+qmGtTok+'|';
      qmValToken(qmGnPool, qmGtAt, qmGtN, qmGnHead, qmGnNh, 1, qmGtH);
      qmValNext(qmGtSeq);
      qmGtStaged := qmWrWork+'val\'+IntToStr(qmGtSeq)+'.inc';
      qmGtWrap := qmWrWork+'val\'+IntToStr(qmGtSeq)+'.aix';
      if (qmValStage(qmGtStaged, qmGnHead, qmGnNh, qmGnPool, qmGtAt, qmGtN, qmGtBytes)=1) then
      begin
         qmValWrap(qmGtWrap, qmGtSeq, qmGtTok, qmGnPool, qmGtAt, qmGtN);
         qmGtOk := qmValRun(qmGtWrap, qmGtSeq, qmGtTok);
      end;
      qmGtK := ParserGetIntValueByKeyByHandle(qmGnG, 't'+qmGtMs);
      ParserSetValueByKeyByHandle(qmGnG, 't'+qmGtMs+'_'+IntToStr(qmGtK), qmGtTier+'|'+IntToStr(qmGtSeq)+'|'+qmGtTok+'|'+IntToStr(qmGtOk));
      ParserSetIntValueByKeyByHandle(qmGnG, 't'+qmGtMs, qmGtK+1);
      qmGnPath(qmGtM, qmGtP);
      qmLog('gen candidate '+qmGtP+' '+qmGtTier+' seq='+IntToStr(qmGtSeq)+' ok='+IntToStr(qmGtOk));
      if (qmGtOk=1) then
      begin
         qmGnHit := 1;
         qmGnDone[qmGtM] := 1;
         qmGnSeq[qmGtM] := qmGtSeq;
         qmGnSize[qmGtM] := qmGtBytes;
         ParserSetValueByKeyByHandle(qmGnG, 'r'+qmGtMs, qmGtTier);
         ParserSetValueByKeyByHandle(qmGnG, 'k'+qmGtMs, qmGtTok);
         ParserSetValueByKeyByHandle(qmGnG, 'h'+qmGtMs, qmGtH);
         ParserSetValueByKeyByHandle(qmGnG, 'f'+qmGtMs, qmGtStaged);
         ParserSetIntValueByKeyByHandle(qmGnG, 'ci'+qmGtMs, qmGtIdx);
      end;
   end;
end;

//! A hook candidate: the source file after the hook lines (pool[0..qmGnHn-1]),
//! the two joined at the source's hook index; for CameraControl the
//! generation constant is set first.
procedure qmGnHookTier(const qmGkM : Integer; const qmGkTier : String; const qmGkPath : String; const qmGkSize : Integer; var qmGkIdx : Integer);
begin
   var qmGkAt : Integer = qmGnHn+64;
   var qmGkN : Integer = -1;
   var qmGkCat : Integer;
   var qmGkCn : Integer = -1;
   var qmGkI : Integer;
   var qmGkH : String;
   var qmGkG : String;
   var qmGkP : String;
   qmGnLoad(qmGkPath, qmGkSize, qmGkAt, qmGkN);
   if (qmGkN>=0) then
   begin
      qmGkCat := qmGkAt+qmGkN+64;
      qmValInsert(qmGnPool, qmGkAt, qmGkN, 0, qmGnHn, qmGkCat, qmGkCn);
   end;
   if (qmGkCn>=0) then
   begin
      qmGnPath(qmGkM, qmGkP);
      if (qmGkP='gui\menu.inc\cameracontrol.inc') then
      begin
         qmValToken(qmGnPool, qmGkCat, qmGkCn, qmGnHead, qmGnNh, 1, qmGkH);
         qmGnHash(qmGkM, qmGkH, qmGkG);
         if (qmGnSalt<>'') then
         qmGkG := qmGkG+'-'+qmGnSalt;
         for qmGkI:=0 to qmGkCn-1 do
         if (qmValIsGen(qmGnPool[qmGkCat+qmGkI])) then
         qmGnPool[qmGkCat+qmGkI] := ';const qmHookGen = '''+qmGkG+''';';
      end;
      qmGnTry(qmGkM, qmGkTier, qmGkIdx, qmGkCat, qmGkCn);
      qmGkIdx := qmGkIdx+1;
   end;
end;

//! The candidates of decision qmGeM, in the order of plan S7.
procedure qmGnDecide(const qmGeM : Integer);
begin
   var qmGeMs : String = IntToStr(qmGeM);
   var qmGeJ : Integer = qmGnJob[qmGeM];
   var qmGeJs : String = 'j'+IntToStr(qmGnJob[qmGeM]);
   var qmGeMerged : Boolean = False;
   var qmGeSub : Boolean = False;
   var qmGeSout : String = '';
   var qmGeSsz : Integer = -1;
   var qmGeErr : String = '';
   var qmGeWin : String = '';
   var qmGeWfile : String = '';
   var qmGeOut : String = '';
   var qmGeOsz : Integer = -1;
   var qmGeIdx : Integer = 0;
   var qmGeN : Integer = -1;
   var qmGeHf : String = '';
   var qmGeNk : Integer = 0;
   var qmGeFk : Integer = 0;
   var qmGePath : String;
   var qmGeT : String;
   var qmGeSt : String;
   qmGnPath(qmGeM, qmGePath);
   qmGnSeen := '|';
   qmGnHit := 0;
   if (qmGnAct[qmGeM]=3) then
   begin
      //! A data decision: qmDataMerge's candidate, or none (the winner's file).
      qmGeT := 'j'+IntToStr(qmGnDj[qmGeM]);
      if (qmGnWta=1) then
      begin
         ParserSetValueByKeyByHandle(qmGnG, 'x'+qmGeMs, 'wta');
         ParserSetValueByKeyByHandle(qmGnG, 's'+qmGeMs, 'FAIL');
      end
      else
      if (qmGnDj[qmGeM]<0) or (qmGnDm=0) then
      begin
         ParserSetValueByKeyByHandle(qmGnG, 'x'+qmGeMs, 'none');
         ParserSetValueByKeyByHandle(qmGnG, 's'+qmGeMs, 'FAIL');
      end
      else
      if (ParserGetValueByKeyByHandle(qmGnDm, qmGeT+'done')<>'1') or (ParserGetValueByKeyByHandle(qmGnDm, qmGeT+'st')='FAIL') or (ParserGetValueByKeyByHandle(qmGnDm, qmGeT+'tok')='') then
      begin
         ParserSetValueByKeyByHandle(qmGnG, 'x'+qmGeMs, 'datafail');
         ParserSetValueByKeyByHandle(qmGnG, 's'+qmGeMs, 'FAIL');
         qmGeErr := ParserGetValueByKeyByHandle(qmGnDm, qmGeT+'err');
         if (qmGeErr='') then
         qmGeErr := 'the data merge did not run';
         ParserSetValueByKeyByHandle(qmGnG, 'e'+qmGeMs, qmGeErr);
      end
      else
      begin
         qmGnDone[qmGeM] := 1;
         qmGnSeq[qmGeM] := ParserGetIntValueByKeyByHandle(qmGnDm, qmGeT+'seq');
         qmGnSize[qmGeM] := ParserGetIntValueByKeyByHandle(qmGnDm, qmGeT+'lines');
         ParserSetValueByKeyByHandle(qmGnG, 'r'+qmGeMs, 'merged');
         ParserSetValueByKeyByHandle(qmGnG, 'k'+qmGeMs, ParserGetValueByKeyByHandle(qmGnDm, qmGeT+'tok'));
         ParserSetValueByKeyByHandle(qmGnG, 'h'+qmGeMs, ParserGetValueByKeyByHandle(qmGnDm, qmGeT+'tok'));
         ParserSetValueByKeyByHandle(qmGnG, 'f'+qmGeMs, qmWrWork+'val\d'+qmGeMs+'.cfg');
         ParserSetIntValueByKeyByHandle(qmGnG, 'ci'+qmGeMs, 0);
         ParserSetValueByKeyByHandle(qmGnG, 'x'+qmGeMs, 'merged');
         ParserSetValueByKeyByHandle(qmGnG, 's'+qmGeMs, ParserGetValueByKeyByHandle(qmGnDm, qmGeT+'st'));
      end;
      qmLog('gen data '+qmGePath+' '+ParserGetValueByKeyByHandle(qmGnG, 'x'+qmGeMs)+' '+ParserGetValueByKeyByHandle(qmGnG, 's'+qmGeMs));
      exit;
   end;
   if (qmGeJ>=0) then
   begin
      qmGeErr := ParserGetValueByKeyByHandle(qmGnMg, qmGeJs+'err');
      if (ParserGetValueByKeyByHandle(qmGnMg, qmGeJs+'done')<>'1') then
      qmGeErr := 'the merge did not run';
      ParserSetValueByKeyByHandle(qmGnG, 'e'+qmGeMs, qmGeErr);
      qmGeMerged := (qmGeErr='') and (ParserGetValueByKeyByHandle(qmGnMg, qmGeJs+'mode')<>'winner') and (ParserGetValueByKeyByHandle(qmGnMg, qmGeJs+'written')='yes');
      qmGeOut := qmWrWork+'val\m'+qmGeMs+'.inc';
      qmGeOsz := ParserGetIntValueByKeyByHandle(qmGnMg, qmGeJs+'bytes');
   end;
   if (qmGnSj[qmGeM]>=0) and (qmGnMs<>0) then
   begin
      qmGeT := 'j'+IntToStr(qmGnSj[qmGeM]);
      qmGeSub := (ParserGetValueByKeyByHandle(qmGnMs, qmGeT+'done')='1') and (ParserGetValueByKeyByHandle(qmGnMs, qmGeT+'err')='') and (ParserGetValueByKeyByHandle(qmGnMs, qmGeT+'mode')<>'winner') and (ParserGetValueByKeyByHandle(qmGnMs, qmGeT+'written')='yes');
      qmGeSout := qmWrWork+'val\s'+qmGeMs+'.inc';
      qmGeSsz := ParserGetIntValueByKeyByHandle(qmGnMs, qmGeT+'bytes');
   end;
   qmGeWin := ParserGetValueByKeyByHandle(qmGnG, 'pw'+qmGeMs);
   if (qmGeWin<>'') then
   begin
      qmGnDir(qmGeWin, qmGeT);
      qmGeWfile := qmGnApp+qmGeT+'\data\'+qmGePath;
   end;
   if (qmGnAct[qmGeM]=1) then
   begin
      if (qmGnWta=1) then
      begin
         ParserSetValueByKeyByHandle(qmGnG, 'x'+qmGeMs, 'wta');
         ParserSetValueByKeyByHandle(qmGnG, 's'+qmGeMs, 'FAIL');
         exit;
      end;
      if (qmGeMerged) then
      begin
         qmGnLoad(qmGeOut, qmGeOsz, 0, qmGeN);
         if (qmGeN>=0) then
         begin
            qmGnTry(qmGeM, 'merged', qmGeIdx, 0, qmGeN);
            qmGeIdx := qmGeIdx+1;
         end;
      end;
      if (qmGnHit=0) and (qmGeSub) then
      begin
         qmGnLoad(qmGeSout, qmGeSsz, 0, qmGeN);
         if (qmGeN>=0) then
         begin
            qmGnTry(qmGeM, 'subset', qmGeIdx, 0, qmGeN);
            qmGeIdx := qmGeIdx+1;
         end;
      end;
      if (qmGnHit=0) and (qmGeWfile<>'') then
      begin
         qmGnLoad(qmGeWfile, -1, 0, qmGeN);
         if (qmGeN>=0) then
         begin
            qmGnTry(qmGeM, 'winner', qmGeIdx, 0, qmGeN);
            qmGeIdx := qmGeIdx+1;
         end;
      end;
   end
   else
   begin
      //! The hook lines: <hookdir><file name>, into pool[0..qmGnHn-1].
      qmGeHf := qmGePath;
      while (StrPos('\', qmGeHf)>0) do
      qmGeHf := SubStr(qmGeHf, StrPos('\', qmGeHf)+1, StrLength(qmGeHf));
      qmGnHn := -2;
      if (qmGnHooks<>'') then
      qmIncReadAt(qmGnHooks+qmGeHf, -1, qmGnPool, 0, qmGnHk, qmGeNk, qmGnHn, qmGeFk);
      if (qmGnHn<0) then
      begin
         ParserSetValueByKeyByHandle(qmGnG, 'x'+qmGeMs, 'nohook');
         ParserSetValueByKeyByHandle(qmGnG, 's'+qmGeMs, 'FAIL');
         qmLog('gen '+qmGePath+': no pristine hook lines at '+qmGnHooks+qmGeHf+'; this file is left alone');
         exit;
      end;
      if (qmGeMerged) then
      qmGnHookTier(qmGeM, 'merged+hook', qmGeOut, qmGeOsz, qmGeIdx);
      if (qmGnHit=0) and (qmGeSub) then
      qmGnHookTier(qmGeM, 'subset+hook', qmGeSout, qmGeSsz, qmGeIdx);
      if (qmGnHit=0) and (qmGeWfile<>'') then
      qmGnHookTier(qmGeM, 'winner+hook', qmGeWfile, -1, qmGeIdx);
      if (qmGnHit=0) then
      qmGnHookTier(qmGeM, 'vanilla+hook', qmGnApp+'data\'+qmGePath, -1, qmGeIdx);
   end;
   if (qmGnHit=1) then
   begin
      qmGeT := ParserGetValueByKeyByHandle(qmGnG, 'r'+qmGeMs);
      if (qmGeT='subset') or (qmGeT='subset+hook') then
      begin
         //! Every change but the losers' is in: a warning, not a failure.
         ParserSetValueByKeyByHandle(qmGnG, 'x'+qmGeMs, 'partial');
         ParserSetValueByKeyByHandle(qmGnG, 's'+qmGeMs, 'WARN');
      end
      else
      if (ParserGetIntValueByKeyByHandle(qmGnG, 'ci'+qmGeMs)>0) then
      begin
         ParserSetValueByKeyByHandle(qmGnG, 'x'+qmGeMs, 'fallback');
         ParserSetValueByKeyByHandle(qmGnG, 's'+qmGeMs, 'FAIL');
      end
      else
      if (qmGnWta=1) then
      begin
         ParserSetValueByKeyByHandle(qmGnG, 'x'+qmGeMs, 'wtahook');
         ParserSetValueByKeyByHandle(qmGnG, 's'+qmGeMs, 'FAIL');
      end
      else
      begin
         if (qmGnAct[qmGeM]=2) then
         ParserSetValueByKeyByHandle(qmGnG, 'x'+qmGeMs, 'hooked')
         else
         if (ParserGetValueByKeyByHandle(qmGnG, 'r'+qmGeMs)='merged') then
         ParserSetValueByKeyByHandle(qmGnG, 'x'+qmGeMs, 'merged')
         else
         if (qmGeErr<>'') then
         ParserSetValueByKeyByHandle(qmGnG, 'x'+qmGeMs, 'mergeerr')
         else
         ParserSetValueByKeyByHandle(qmGnG, 'x'+qmGeMs, 'gaveup');
         qmGeSt := 'OK';
         if (qmGeErr<>'') then
         qmGeSt := 'FAIL'
         else
         if (qmGeJ>=0) then
         begin
            qmGeT := ParserGetValueByKeyByHandle(qmGnMg, qmGeJs+'status');
            if (qmGeT='warn') then
            qmGeSt := 'WARN';
            if (qmGeT='fail') then
            qmGeSt := 'FAIL';
            // ref/validate.py _merge_status (the Workshop check): a merge
            // that gave up leaves the last mod's copy, as the game alone
            // would load it (WARN); near edits alone lost nothing (OK).
            if (ParserGetValueByKeyByHandle(qmGnG, 'x'+qmGeMs)='gaveup') then
            qmGeSt := 'WARN';
            // A hook file whose merge gave up has the last mod's copy with
            // the hook lines: WARN as gaveup, OK when that mod is the only
            // participant (pp<m> without a `;`). It read FAIL until
            // 2026-10-01 (SW_Frontline_Protocol's doprogress.inc).
            if (ParserGetValueByKeyByHandle(qmGnG, 'x'+qmGeMs)='hooked') and (ParserGetValueByKeyByHandle(qmGnMg, qmGeJs+'mode')='winner') then
            begin
               qmGeSt := 'WARN';
               if (StrPos(';', ParserGetValueByKeyByHandle(qmGnG, 'pp'+qmGeMs))=0) then
               qmGeSt := 'OK';
            end;
            if (ParserGetValueByKeyByHandle(qmGnMg, qmGeJs+'mode')='merged') and (qmGeT='warn') and (ParserGetValueByKeyByHandle(qmGnMg, qmGeJs+'conflicts')='0') then
            qmGeSt := 'OK';
         end;
         ParserSetValueByKeyByHandle(qmGnG, 's'+qmGeMs, qmGeSt);
      end;
   end
   else
   if (qmGnAct[qmGeM]=2) then
   begin
      ParserSetValueByKeyByHandle(qmGnG, 'x'+qmGeMs, 'fatal');
      ParserSetValueByKeyByHandle(qmGnG, 's'+qmGeMs, 'FATAL');
      if (qmGnFatal='') then
      qmGnFatal := qmGePath;
   end
   else
   begin
      ParserSetValueByKeyByHandle(qmGnG, 'x'+qmGeMs, 'none');
      ParserSetValueByKeyByHandle(qmGnG, 's'+qmGeMs, 'FAIL');
   end;
end;

//! The FileAge of the copy the mod at position qmGaPos ships of qmGaPath
//! (qm_index a<k>, aligned with v<k>), '-' when unknown.
procedure qmGnAge(const qmGaPath : String; const qmGaPos : String; var qmGaOut : String);
begin
   var qmGaKey : String;
   var qmGaK : Integer;
   var qmGaV : String;
   var qmGaF : String;
   var qmGaI : Integer = 0;
   var qmGaGo : Boolean = True;
   qmGaOut := '-';
   qmIdxKey(qmGaPath, qmGaKey);
   qmGaK := ParserGetIntValueByKeyByHandle(qmGnKeys, qmGaKey);
   if (ParserGetValueByKeyByHandle(qmGnIdx, 'p'+IntToStr(qmGaK))=qmGaPath) then
   begin
      qmGaV := ParserGetValueByKeyByHandle(qmGnIdx, 'v'+IntToStr(qmGaK));
      while (qmGaGo) do
      begin
         qmField(qmGaV, ';', qmGaI, qmGaF);
         if (qmGaF='') then
         qmGaGo := False
         else
         if (qmGaF=qmGaPos) then
         begin
            qmField(ParserGetValueByKeyByHandle(qmGnIdx, 'a'+IntToStr(qmGaK)), ';', qmGaI, qmGaOut);
            qmGaGo := False;
         end;
         qmGaI := qmGaI+1;
      end;
   end;
end;

if (qmGnIn<>0) then
begin
   qmGnBox := ParserGetValueByKeyByHandle(qmGnIn, 'sandbox');
   qmGnHooks := ParserGetValueByKeyByHandle(qmGnIn, 'hookdir');
   qmGnWta := ParserGetIntValueByKeyByHandle(qmGnIn, 'wta');
   qmGnSalt := ParserGetValueByKeyByHandle(qmGnIn, 'gensalt');
end;
if (qmGnG=0) then
qmGnG := ParserCreate('qm_gen');
ParserClearByHandle(qmGnG);
qmGnOpen := qmWrOpen(qmGnBox);
if (qmGnHooks='cases') then
qmGnHooks := GetAppSaveDirectoryPath+'qm_test\cases\'
else
if (qmGnHooks='qm') then
qmGnHooks := qmGnApp+ParserGetValueByKeyByHandle(qmGnRt, 'qmdir')+'\data\quartermaster\hooks\'
else
qmWrHookDir(qmGnHooks);
ParserSetValueByKeyByHandle(qmGnG, 'box', qmGnBox);
ParserSetValueByKeyByHandle(qmGnG, 'work', qmWrWork);
ParserSetValueByKeyByHandle(qmGnG, 'status', 'error');
if (qmGnRt<>0) then
qmGnFp := ParserGetValueByKeyByHandle(qmGnRt, 'fp');
if (qmGnFp='') then
qmGnFp := '-';
ParserSetValueByKeyByHandle(qmGnG, 'fp', qmGnFp);
if (qmGnOpen=0) or (qmGnPlan=0) or (qmGnMods=0) or (qmGnIdx=0) or (qmGnKeys=0) then
begin
   qmLog('gen: nothing generated - '+'folder='+IntToStr(qmGnOpen)+' plan='+IntToStr(qmGnPlan)+' mods='+IntToStr(qmGnMods)+' index='+IntToStr(qmGnIdx));
   exit;
end;
qmGnN := ParserGetIntValueByKeyByHandle(qmGnPlan, 'n');
if (qmGnN>512) then
begin
   qmLog('gen: '+IntToStr(qmGnN)+' plan decisions, only the first 512 are handled');
   qmGnN := 512;
end;
ParserSetIntValueByKeyByHandle(qmGnG, 'n', qmGnN);
qmGnK := ParserGetIntValueByKeyByHandle(qmGnMods, 'self');
if (qmGnK>=0) then
qmGnSelf := IntToStr(ParserGetIntValueByKeyByHandle(qmGnMods, 'pos'+IntToStr(qmGnK)));

//! The previous generation's manifest: its generation, hash and files.
qmWrReadManifest(qmGnPool, 0, qmGnHead, qmGnC);
if (qmGnC>=0) then
begin
   qmGnPrev := 1;
   for qmGnI:=0 to qmGnC-1 do
   begin
      qmMqField(qmGnPool[qmGnI], 0, qmGnS);
      qmMqField(qmGnPool[qmGnI], 1, qmGnT);
      if (qmGnS=';gen') and (qmIsDigits(qmGnT)) then
      qmGnPrevGen := StrToInt(qmGnT);
      if (qmGnS=';outhash') then
      qmGnPrevHash := qmGnT;
      if ((qmGnS=';out') or (qmGnS=';left')) and (qmGnT<>'') then
      begin
         ParserSetValueByKeyByHandle(qmGnG, 'po'+IntToStr(qmGnPn), qmGnT);
         qmGnPn := qmGnPn+1;
      end;
   end;
end;
ParserSetIntValueByKeyByHandle(qmGnG, 'pn', qmGnPn);

//! The decisions, their participants and the merges.
qmGnMin := ParserSelectByKey('qm_mg_in');
if (qmGnMin=0) then
qmGnMin := ParserCreate('qm_mg_in');
ParserClearByHandle(qmGnMin);
for qmGnM:=0 to qmGnN-1 do
begin
   qmGnAct[qmGnM] := 0;
   qmGnJob[qmGnM] := -1;
   qmGnDj[qmGnM] := -1;
   qmGnDone[qmGnM] := 0;
   qmGnSeq[qmGnM] := 0;
   qmGnSize[qmGnM] := 0;
   qmGnJs := IntToStr(qmGnM);
   qmGnPath(qmGnM, qmGnP);
   qmGnS := ParserGetValueByKeyByHandle(qmGnPlan, 'act'+qmGnJs);
   ParserSetValueByKeyByHandle(qmGnG, 'j'+qmGnJs, '-1');
   ParserSetValueByKeyByHandle(qmGnG, 'w'+qmGnJs, '-');
   if (qmGnS='merge-inc') then
   qmGnAct[qmGnM] := 1
   else
   if (qmGnS='hook') then
   qmGnAct[qmGnM] := 2
   else
   if (qmGnS='merge-data') then
   qmGnAct[qmGnM] := 3
   else
   if (qmGnS='skip') then
   begin
      ParserSetValueByKeyByHandle(qmGnG, 'x'+qmGnJs, 'skip');
      ParserSetValueByKeyByHandle(qmGnG, 's'+qmGnJs, 'OK');
   end
   else
   begin
      ParserSetValueByKeyByHandle(qmGnG, 'x'+qmGnJs, 'winner');
      ParserSetValueByKeyByHandle(qmGnG, 's'+qmGnJs, 'WARN');
   end;
   //! The participants: every provider but Quartermaster, canonical order;
   //! the last one is the winner (also what an undeletable stale output is
   //! overwritten with, below).
   qmGnV := ParserGetValueByKeyByHandle(qmGnPlan, 'prov'+qmGnJs);
   qmGnU := '';
   qmGnW := '';
   qmGnC := 0;
   qmGnI := 0;
   qmField(qmGnV, ';', 0, qmGnT);
   while (qmGnT<>'') do
   begin
      if (qmGnT<>qmGnSelf) then
      begin
         if (qmGnU<>'') then
         qmGnU := qmGnU+';';
         qmGnU := qmGnU+qmGnT;
         qmGnW := qmGnT;
         qmGnC := qmGnC+1;
      end;
      qmGnI := qmGnI+1;
      qmField(qmGnV, ';', qmGnI, qmGnT);
   end;
   ParserSetValueByKeyByHandle(qmGnG, 'pp'+qmGnJs, qmGnU);
   ParserSetValueByKeyByHandle(qmGnG, 'pw'+qmGnJs, qmGnW);
   if (qmGnAct[qmGnM]=3) and (qmGnC>0) and (qmGnWta=0) then
   begin
      //! A data job: vanilla, the participants in load order with their
      //! titles, the dmscript.global in effect.
      if (qmGnDin=0) then
      begin
         qmGnDin := ParserSelectByKey('qm_dm_in');
         if (qmGnDin=0) then
         qmGnDin := ParserCreate('qm_dm_in');
         ParserClearByHandle(qmGnDin);
         qmGnV := qmGnApp+'data\scripts\dmscript.global';
         qmIdxKey('scripts\dmscript.global', qmGnW);
         qmGnK := ParserGetIntValueByKeyByHandle(qmGnKeys, qmGnW);
         if (ParserGetValueByKeyByHandle(qmGnIdx, 'p'+IntToStr(qmGnK))='scripts\dmscript.global') then
         begin
            qmGnW := ParserGetValueByKeyByHandle(qmGnIdx, 'v'+IntToStr(qmGnK));
            if (qmGnW<>'-') and (qmGnW<>'') then
            begin
               while (StrPos(';', qmGnW)>0) do
               qmGnW := SubStr(qmGnW, StrPos(';', qmGnW)+1, StrLength(qmGnW));
               qmGnDir(qmGnW, qmGnT);
               qmGnV := qmGnApp+qmGnT+'\data\scripts\dmscript.global';
            end;
         end;
         ParserSetValueByKeyByHandle(qmGnDin, 'glob', qmGnV);
      end;
      qmGnDj[qmGnM] := qmGnDjobs;
      ParserSetIntValueByKeyByHandle(qmGnG, 'dj'+qmGnJs, qmGnDjobs);
      qmGnT := 'j'+IntToStr(qmGnDjobs);
      ParserSetValueByKeyByHandle(qmGnDin, qmGnT+'path', qmGnP);
      ParserSetValueByKeyByHandle(qmGnDin, qmGnT+'base', qmGnApp+'data\'+qmGnP);
      ParserSetValueByKeyByHandle(qmGnDin, qmGnT+'glob', ParserGetValueByKeyByHandle(qmGnDin, 'glob'));
      ParserSetIntValueByKeyByHandle(qmGnDin, qmGnT+'parts', qmGnC);
      for qmGnI:=0 to qmGnC-1 do
      begin
         qmField(qmGnU, ';', qmGnI, qmGnS);
         qmGnDir(qmGnS, qmGnW);
         ParserSetValueByKeyByHandle(qmGnDin, qmGnT+'p'+IntToStr(qmGnI), qmGnApp+qmGnW+'\data\'+qmGnP);
         qmGnJ := ParserGetIntValueByKeyByHandle(qmGnMods, 'ord'+qmGnS);
         qmGnV := ParserGetValueByKeyByHandle(qmGnMods, 'tit'+IntToStr(qmGnJ));
         if (qmGnV='') then
         qmGnV := ParserGetValueByKeyByHandle(qmGnMods, 'last'+IntToStr(qmGnJ));
         if (qmGnV='') then
         qmGnV := qmGnW;
         ParserSetValueByKeyByHandle(qmGnDin, qmGnT+'n'+IntToStr(qmGnI), qmGnV);
      end;
      ParserSetValueByKeyByHandle(qmGnDin, qmGnT+'out', qmWrWork+'val\d'+qmGnJs+'.cfg');
      qmGnDjobs := qmGnDjobs+1;
   end;
   if (qmGnAct[qmGnM]>0) and (qmGnAct[qmGnM]<3) then
   begin
      //! Vanilla's first Code line, for the report's line numbers.
      qmGnLoad(qmGnApp+'data\'+qmGnP, -1, 0, qmGnK);
      qmGnR := qmGnNh+2;
      if (qmGnForm=2) then
      qmGnR := qmGnR+1;
      ParserSetIntValueByKeyByHandle(qmGnG, 'vf'+qmGnJs, qmGnR);
      ParserSetIntValueByKeyByHandle(qmGnG, 'vn'+qmGnJs, qmGnK);
      if (qmGnC>0) and (qmGnWta=0) then
      begin
         qmGnJob[qmGnM] := qmGnJobs;
         ParserSetIntValueByKeyByHandle(qmGnG, 'j'+qmGnJs, qmGnJobs);
         qmGnT := 'j'+IntToStr(qmGnJobs);
         ParserSetValueByKeyByHandle(qmGnMin, qmGnT+'base', qmGnApp+'data\'+qmGnP);
         ParserSetIntValueByKeyByHandle(qmGnMin, qmGnT+'parts', qmGnC);
         for qmGnI:=0 to qmGnC-1 do
         begin
            qmField(qmGnU, ';', qmGnI, qmGnS);
            qmGnDir(qmGnS, qmGnW);
            ParserSetValueByKeyByHandle(qmGnMin, qmGnT+'p'+IntToStr(qmGnI), qmGnApp+qmGnW+'\data\'+qmGnP);
         end;
         ParserSetValueByKeyByHandle(qmGnMin, qmGnT+'hook', '');
         ParserSetValueByKeyByHandle(qmGnMin, qmGnT+'out', qmWrWork+'val\m'+qmGnJs+'.inc');
         ParserSetValueByKeyByHandle(qmGnMin, qmGnT+'dump', qmWrWork+'val\m'+qmGnJs+'.txt');
         qmGnJobs := qmGnJobs+1;
      end;
   end;
end;
ParserSetIntValueByKeyByHandle(qmGnMin, 'jobs', qmGnJobs);
qmLog('gen start sandbox='+qmGnBox+' decisions='+IntToStr(qmGnN)+' merges='+IntToStr(qmGnJobs)+' previous files='+IntToStr(qmGnPn));
if (qmGnJobs>0) then
StateMachineExecuteState(GetTriggerManagerStateMachineHandle('qm_core'), 'qmMerge', 0);
qmGnMg := ParserSelectByKey('qm_mg');
//! The second batch (ref/validate.py losers): for a merged file with
//! conflicts, the merge without the participants that lost one, when at
//! least two stay. A mod's own hunks can depend on each other - a const one
//! declares, another uses - so half of one mod may not compile where the
//! other mods whole do (Renaissance + MGraphics - Main Menu, 2026-09-30).
//! The results go to qm_ms; qm_mg keeps the first batch's.
for qmGnSm:=0 to qmGnN-1 do
begin
   qmGnSj[qmGnSm] := -1;
   qmGnSk[qmGnSm] := '';
   if (qmGnJob[qmGnSm]>=0) and (qmGnMg<>0) then
   begin
      qmGnSt := 'j'+IntToStr(qmGnJob[qmGnSm]);
      if (ParserGetValueByKeyByHandle(qmGnMg, qmGnSt+'err')='') and (ParserGetValueByKeyByHandle(qmGnMg, qmGnSt+'mode')='merged') and (ParserGetIntValueByKeyByHandle(qmGnMg, qmGnSt+'conflicts')>0) then
      begin
         //! The losers: the participant of every hunk row that lost.
         qmGnLs := '|';
         for qmGnSr:=0 to ParserGetIntValueByKeyByHandle(qmGnMg, qmGnSt+'rows')-1 do
         begin
            qmGnLr := ParserGetValueByKeyByHandle(qmGnMg, qmGnSt+'r'+IntToStr(qmGnSr));
            qmField(qmGnLr, '|', 0, qmGnLf);
            if (qmGnLf='hunk') then
            begin
               qmField(qmGnLr, '|', 6, qmGnLf);
               if (qmGnLf='conflict-lost') then
               begin
                  qmField(qmGnLr, '|', 2, qmGnLf);
                  if (StrPos('|'+qmGnLf+'|', qmGnLs)=0) then
                  qmGnLs := qmGnLs+qmGnLf+'|';
               end;
            end;
         end;
         qmGnLp := ParserGetValueByKeyByHandle(qmGnG, 'pp'+IntToStr(qmGnSm));
         qmGnLo := '';
         qmGnKc := 0;
         qmGnSr := 0;
         qmField(qmGnLp, ';', 0, qmGnLx);
         while (qmGnLx<>'') do
         begin
            if (StrPos('|'+IntToStr(qmGnSr)+'|', qmGnLs)>0) then
            begin
               if (qmGnLo<>'') then
               qmGnLo := qmGnLo+';';
               qmGnLo := qmGnLo+qmGnLx;
            end
            else
            begin
               if (qmGnSk[qmGnSm]<>'') then
               qmGnSk[qmGnSm] := qmGnSk[qmGnSm]+';';
               qmGnSk[qmGnSm] := qmGnSk[qmGnSm]+qmGnLx;
               qmGnKc := qmGnKc+1;
            end;
            qmGnSr := qmGnSr+1;
            qmField(qmGnLp, ';', qmGnSr, qmGnLx);
         end;
         //! One participant left is the winner's own copy, the next tier.
         if (qmGnKc>=2) then
         begin
            qmGnSj[qmGnSm] := qmGnSjobs;
            ParserSetIntValueByKeyByHandle(qmGnG, 'sj'+IntToStr(qmGnSm), qmGnSjobs);
            ParserSetValueByKeyByHandle(qmGnG, 'lo'+IntToStr(qmGnSm), qmGnLo);
            qmGnSjobs := qmGnSjobs+1;
         end
         else
         qmGnSk[qmGnSm] := '';
      end;
   end;
end;
if (qmGnSjobs>0) then
begin
   ParserClearByHandle(qmGnMin);
   for qmGnSm:=0 to qmGnN-1 do
   if (qmGnSj[qmGnSm]>=0) then
   begin
      qmGnSs := IntToStr(qmGnSm);
      qmGnSt := 'j'+IntToStr(qmGnSj[qmGnSm]);
      qmGnPath(qmGnSm, qmGnSp);
      ParserSetValueByKeyByHandle(qmGnMin, qmGnSt+'base', qmGnApp+'data\'+qmGnSp);
      qmGnKc := 0;
      qmField(qmGnSk[qmGnSm], ';', 0, qmGnLx);
      while (qmGnLx<>'') do
      begin
         qmGnDir(qmGnLx, qmGnSd);
         ParserSetValueByKeyByHandle(qmGnMin, qmGnSt+'p'+IntToStr(qmGnKc), qmGnApp+qmGnSd+'\data\'+qmGnSp);
         qmGnKc := qmGnKc+1;
         qmField(qmGnSk[qmGnSm], ';', qmGnKc, qmGnLx);
      end;
      ParserSetIntValueByKeyByHandle(qmGnMin, qmGnSt+'parts', qmGnKc);
      ParserSetValueByKeyByHandle(qmGnMin, qmGnSt+'hook', '');
      ParserSetValueByKeyByHandle(qmGnMin, qmGnSt+'out', qmWrWork+'val\s'+qmGnSs+'.inc');
      ParserSetValueByKeyByHandle(qmGnMin, qmGnSt+'dump', qmWrWork+'val\s'+qmGnSs+'.txt');
   end;
   ParserSetIntValueByKeyByHandle(qmGnMin, 'jobs', qmGnSjobs);
   ParserSetValueByKeyByHandle(qmGnMin, 'res', 'qm_ms');
   qmLog('gen subset merges='+IntToStr(qmGnSjobs));
   StateMachineExecuteState(GetTriggerManagerStateMachineHandle('qm_core'), 'qmMerge', 0);
   qmGnMs := ParserSelectByKey('qm_ms');
end;
if (qmGnDin<>0) then
ParserSetIntValueByKeyByHandle(qmGnDin, 'jobs', qmGnDjobs);
if (qmGnDjobs>0) then
StateMachineExecuteState(GetTriggerManagerStateMachineHandle('qm_core'), 'qmDataMerge', 0);
qmGnDm := ParserSelectByKey('qm_dm');

//! Phase 1: candidates and validation; CameraControl last.
for qmGnPass:=0 to 1 do
for qmGnM:=0 to qmGnN-1 do
if (qmGnAct[qmGnM]>0) then
begin
   qmGnPath(qmGnM, qmGnP);
   if ((qmGnPass=0) and (qmGnP<>'gui\menu.inc\cameracontrol.inc')) or ((qmGnPass=1) and (qmGnP='gui\menu.inc\cameracontrol.inc')) then
   qmGnDecide(qmGnM);
end;
qmGnHash(-1, '', qmGnOutHash);
ParserSetValueByKeyByHandle(qmGnG, 'outhash', qmGnOutHash);

if (qmGnFatal<>'') then
begin
   qmGnGen := qmGnPrevGen;
   ParserSetValueByKeyByHandle(qmGnG, 'status', 'fatal');
   ParserSetValueByKeyByHandle(qmGnG, 'fatal', qmGnFatal);
   qmLog('FATAL '+qmGnFatal+': vanilla with Quartermaster''s hook lines does not compile (a build bug); nothing was written');
end
else
begin
   //! Phase 2: the writes, each gated by its validation flag.
   for qmGnM:=0 to qmGnN-1 do
   if (qmGnDone[qmGnM]=1) then
   begin
      qmGnJs := IntToStr(qmGnM);
      qmGnPath(qmGnM, qmGnP);
      if (qmGnAct[qmGnM]=3) then
      qmGnR := qmWrDataOut(qmGnP, ParserGetValueByKeyByHandle(qmGnG, 'f'+qmGnJs), qmGnSize[qmGnM], qmGnSeq[qmGnM], qmGnPool)
      else
      qmGnR := qmWrOutput(qmGnP, ParserGetValueByKeyByHandle(qmGnG, 'f'+qmGnJs), qmGnSize[qmGnM], qmGnSeq[qmGnM], qmGnPool, qmGnHk);
      if (qmGnR=1) then
      begin
         ParserSetValueByKeyByHandle(qmGnG, 'w'+qmGnJs, 'yes');
         qmGnWritten := qmGnWritten+1;
         qmGnChanged := qmGnChanged+1;
      end
      else
      if (qmGnR=2) then
      begin
         ParserSetValueByKeyByHandle(qmGnG, 'w'+qmGnJs, 'same');
         qmGnSame := qmGnSame+1;
      end
      else
      begin
         if (qmGnR=0) then
         ParserSetValueByKeyByHandle(qmGnG, 'w'+qmGnJs, 'refused')
         else
         ParserSetValueByKeyByHandle(qmGnG, 'w'+qmGnJs, 'failed');
         ParserSetValueByKeyByHandle(qmGnG, 'x'+qmGnJs, 'writefail');
         ParserSetValueByKeyByHandle(qmGnG, 's'+qmGnJs, 'FAIL');
      end;
      qmLog('gen write '+qmGnP+' '+ParserGetValueByKeyByHandle(qmGnG, 'r'+qmGnJs)+' '+ParserGetValueByKeyByHandle(qmGnG, 'w'+qmGnJs));
   end;

   //! Stale cleanup (plan S9): the previous generation's files that no
   //! decision chose this time.
   for qmGnK:=0 to qmGnPn-1 do
   begin
      qmGnS := ParserGetValueByKeyByHandle(qmGnG, 'po'+IntToStr(qmGnK));
      qmGnCur := False;
      for qmGnM:=0 to qmGnN-1 do
      if (qmGnDone[qmGnM]=1) then
      begin
         qmGnPath(qmGnM, qmGnP);
         if (qmGnP=qmGnS) then
         qmGnCur := True;
      end;
      if (not qmGnCur) then
      begin
         qmGnJs := IntToStr(qmGnSn);
         ParserSetValueByKeyByHandle(qmGnG, 'sp'+qmGnJs, qmGnS);
         ParserSetValueByKeyByHandle(qmGnG, 'ss'+qmGnJs, '-');
         qmGnR := qmWrDelete(qmGnS);
         if (qmGnR=-1) then
         ParserSetValueByKeyByHandle(qmGnG, 'sr'+qmGnJs, 'refused');
         if (qmGnR=1) then
         begin
            ParserSetValueByKeyByHandle(qmGnG, 'sr'+qmGnJs, 'deleted');
            qmGnRemoved := qmGnRemoved+1;
            qmGnChanged := qmGnChanged+1;
         end;
         if (qmGnR=0) and (qmWrCheckData(qmGnS)=1) then
         begin
            //! A data file still there: the .inc overwrite below does not
            //! apply to it (it is no code to compile); reported as failed.
            ParserSetValueByKeyByHandle(qmGnG, 'sr'+qmGnJs, 'failed');
            qmGnR := 3;
         end;
         if (qmGnR=0) then
         begin
            //! Still there: overwrite it with what the game should use now -
            //! the current winner's copy, else vanilla - validated first.
            qmGnU := 'vanilla';
            qmGnV := qmGnApp+'data\'+qmGnS;
            for qmGnM:=0 to qmGnN-1 do
            begin
               qmGnPath(qmGnM, qmGnP);
               if (qmGnP=qmGnS) and (ParserGetValueByKeyByHandle(qmGnG, 'pw'+IntToStr(qmGnM))<>'') then
               begin
                  qmGnDir(ParserGetValueByKeyByHandle(qmGnG, 'pw'+IntToStr(qmGnM)), qmGnW);
                  if (FileAge(qmGnApp+qmGnW+'\data\'+qmGnS)<>-1) then
                  begin
                     qmGnU := 'winner';
                     qmGnV := qmGnApp+qmGnW+'\data\'+qmGnS;
                  end;
               end;
            end;
            ParserSetValueByKeyByHandle(qmGnG, 'ss'+qmGnJs, qmGnU);
            ParserSetValueByKeyByHandle(qmGnG, 'sr'+qmGnJs, 'failed');
            qmGnLoad(qmGnV, -1, 0, qmGnC);
            if (qmGnC>=0) then
            begin
               qmValToken(qmGnPool, 0, qmGnC, qmGnHead, qmGnNh, 0, qmGnTok);
               qmValNext(qmGnSeqS);
               qmGnT := qmWrWork+'val\'+IntToStr(qmGnSeqS)+'.inc';
               qmGnOk := 0;
               if (qmValStage(qmGnT, qmGnHead, qmGnNh, qmGnPool, 0, qmGnC, qmGnBytes)=1) then
               begin
                  qmValWrap(qmWrWork+'val\'+IntToStr(qmGnSeqS)+'.aix', qmGnSeqS, qmGnTok, qmGnPool, 0, qmGnC);
                  qmGnOk := qmValRun(qmWrWork+'val\'+IntToStr(qmGnSeqS)+'.aix', qmGnSeqS, qmGnTok);
               end;
               ParserSetValueByKeyByHandle(qmGnG, 'sc'+qmGnJs, 'stale|'+IntToStr(qmGnSeqS)+'|'+qmGnTok+'|'+IntToStr(qmGnOk));
               qmLog('gen candidate '+qmGnS+' stale seq='+IntToStr(qmGnSeqS)+' ok='+IntToStr(qmGnOk));
               if (qmGnOk=1) then
               begin
                  if (qmWrOutput(qmGnS, qmGnT, qmGnBytes, qmGnSeqS, qmGnPool, qmGnHk)>=1) then
                  begin
                     ParserSetValueByKeyByHandle(qmGnG, 'sr'+qmGnJs, 'overwritten');
                     ParserSetValueByKeyByHandle(qmGnG, 'sk'+qmGnJs, qmGnTok);
                     qmGnRemoved := qmGnRemoved+1;
                     qmGnChanged := qmGnChanged+1;
                  end;
               end;
            end;
         end;
         qmLog('gen stale '+qmGnS+' '+ParserGetValueByKeyByHandle(qmGnG, 'sr'+qmGnJs));
         qmGnSn := qmGnSn+1;
      end;
   end;
   ParserSetIntValueByKeyByHandle(qmGnG, 'sn', qmGnSn);

   //! The manifest (ref/manifest.py): the generation stays the same when the
   //! outputs hash does.
   qmGnGen := 1;
   if (qmGnPrev=1) then
   begin
      if (qmGnPrevHash=qmGnOutHash) then
      qmGnGen := qmGnPrevGen
      else
      qmGnGen := qmGnPrevGen+1;
   end;
   qmGnL := 0;
   qmGnPool[0] := ';gen|'+IntToStr(qmGnGen);
   qmGnPool[1] := ';outhash|'+qmGnOutHash;
   qmGnPool[2] := ';fp|'+qmGnFp;
   qmGnL := 3;
   for qmGnM:=0 to qmGnN-1 do
   if ((ParserGetValueByKeyByHandle(qmGnG, 'w'+IntToStr(qmGnM))='yes') or (ParserGetValueByKeyByHandle(qmGnG, 'w'+IntToStr(qmGnM))='same')) and (qmGnL<${rawcap}-64) then
   begin
      qmGnJs := IntToStr(qmGnM);
      qmGnPath(qmGnM, qmGnP);
      qmGnT := '-|-|-|0|0|0';
      if (qmGnJob[qmGnM]>=0) then
      begin
         qmGnS := 'j'+IntToStr(qmGnJob[qmGnM]);
         if (ParserGetValueByKeyByHandle(qmGnG, 'e'+qmGnJs)<>'') then
         qmGnT := 'error|fail|-|0|0|0'
         else
         qmGnT := ParserGetValueByKeyByHandle(qmGnMg, qmGnS+'mode')+'|'+ParserGetValueByKeyByHandle(qmGnMg, qmGnS+'status')+'|'+ParserGetValueByKeyByHandle(qmGnMg, qmGnS+'reason')+'|'+ParserGetValueByKeyByHandle(qmGnMg, qmGnS+'hunks')+'|'+ParserGetValueByKeyByHandle(qmGnMg, qmGnS+'conflicts')+'|'+ParserGetValueByKeyByHandle(qmGnMg, qmGnS+'proximity');
      end;
      qmGnPool[qmGnL] := ';out|'+qmGnP+'|'+ParserGetValueByKeyByHandle(qmGnG, 'k'+qmGnJs)+'|'+ParserGetValueByKeyByHandle(qmGnG, 'r'+qmGnJs)+'|'+qmGnT;
      qmGnL := qmGnL+1;
      qmGnU := ParserGetValueByKeyByHandle(qmGnG, 'pp'+qmGnJs);
      qmGnI := 0;
      qmField(qmGnU, ';', 0, qmGnS);
      while (qmGnS<>'') and (qmGnL<${rawcap}-64) do
      begin
         qmGnJ := ParserGetIntValueByKeyByHandle(qmGnMods, 'ord'+qmGnS);
         qmHex(ParserGetValueByKeyByHandle(qmGnMods, 'id'+IntToStr(qmGnJ)), qmGnW);
         qmGnAge(qmGnP, qmGnS, qmGnV);
         qmGnPool[qmGnL] := ';src|'+qmGnP+'|'+qmGnS+'|'+ParserGetValueByKeyByHandle(qmGnMods, 'fo'+IntToStr(qmGnJ))+'|'+qmGnW+'|'+qmGnV;
         qmGnL := qmGnL+1;
         qmGnI := qmGnI+1;
         qmField(qmGnU, ';', qmGnI, qmGnS);
      end;
   end;
   for qmGnK:=0 to qmGnSn-1 do
   if (ParserGetValueByKeyByHandle(qmGnG, 'sr'+IntToStr(qmGnK))='overwritten') and (qmGnL<${rawcap}-64) then
   begin
      qmGnPool[qmGnL] := ';left|'+ParserGetValueByKeyByHandle(qmGnG, 'sp'+IntToStr(qmGnK))+'|'+ParserGetValueByKeyByHandle(qmGnG, 'sk'+IntToStr(qmGnK));
      qmGnL := qmGnL+1;
   end;
   if (qmWrManifest(qmGnPool, 0, qmGnL, qmGnHk)=0) then
   qmLog('gen: the manifest could not be written');
   ParserSetValueByKeyByHandle(qmGnG, 'status', 'ok');
end;
for qmGnM:=0 to qmGnN-1 do
begin
   qmGnS := ParserGetValueByKeyByHandle(qmGnG, 's'+IntToStr(qmGnM));
   if (qmGnS='FAIL') or (qmGnS='FATAL') then
   qmGnFailed := qmGnFailed+1;
end;
ParserSetIntValueByKeyByHandle(qmGnG, 'gen', qmGnGen);
ParserSetIntValueByKeyByHandle(qmGnG, 'prevgen', qmGnPrevGen);
ParserSetIntValueByKeyByHandle(qmGnG, 'written', qmGnWritten);
ParserSetIntValueByKeyByHandle(qmGnG, 'same', qmGnSame);
ParserSetIntValueByKeyByHandle(qmGnG, 'changed', qmGnChanged);
ParserSetIntValueByKeyByHandle(qmGnG, 'failed', qmGnFailed);
ParserSetIntValueByKeyByHandle(qmGnG, 'removed', qmGnRemoved);
qmLog('gen done status='+ParserGetValueByKeyByHandle(qmGnG, 'status')+' generation='+IntToStr(qmGnGen)+' outputs hash='+qmGnOutHash+' written='+IntToStr(qmGnWritten)+' same='+IntToStr(qmGnSame)+' changed='+IntToStr(qmGnChanged)+' failed='+IntToStr(qmGnFailed)+' removed='+IntToStr(qmGnRemoved));
