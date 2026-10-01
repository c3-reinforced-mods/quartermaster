state: qmCaseMerge
into: data/quartermaster/selftest.aix
helpers: qmlog, qminc, qmraw
requires:
---
//! The SelfTest kind `merge` (plan G18): runs every merge of a suite through
//! the real engine state qmMerge and leaves its rows and output files in the
//! SelfTest out folder, where tools/m3cases.py compares them with ref/.
//!
//! The case file (loaded by qmSelfTest into the parser qm_case) holds
//!     ;kind merge
//!     ;suite <file, relative to the game folder>
//! and the suite is an .inc-shaped file whose Code values are one merge each:
//!     ;case <name> <vanilla path under data\> <hook file or -> <p0> [<p1> ..]
//! with the participant files relative to the game folder too, in canonical
//! order. A suite of several hundred merges travels as one fixture folder and
//! one case file, where a case file per merge would not fit a command line.
//!
//! Per merge: <out>\<name>.txt, the rows (ref/merge.py result_rows), and
//! <out>\<name>.inc, the output file when there is one. The merges go to
//! qmMerge in batches of qmCmBatch per call: its read pool costs 0.3 s per
//! call whatever it holds. The case's own dump (qm_case_rt `out`) gets
//!     m3case|<name>|<done>|<written>|<ms>|<load>|<diff>|<merge>|<write>
//! per merge, `m3call|<batch>|<merges>|<ms>` per call (the whole call, the
//! pool's allocation included) and `m3|<merges>|<not done>` last: done is 0
//! when qmMerge stopped before that merge was through, written is qm_mg's
//! (yes, none, failed), the times are ms. Vanilla is read by absolute path:
//! `.\data\` would go through the overlay and could read another mod's copy.
const qmCmBatch = 20;
var qmCmRt : Integer = ParserSelectByKey('qm_case_rt');
var qmCmOutDir : String = ParserGetValueByKeyByHandle(qmCmRt, 'outdir');
var qmCmOut : String = ParserGetValueByKeyByHandle(qmCmRt, 'out');
var qmCmApp : String = ExtractFilePath(GetApplicationFileName);
var qmCmCase : Integer = ParserSelectByKey('qm_case');
var qmCmCode : Integer = 0;
var qmCmSuite : String = '';
var qmCmI : Integer;
var qmCmV : String;
var qmCmRest : String;
var qmCmTok : String;
var qmCmParts : Integer;
var qmCmSum : String = '';
var qmCmRuns : Integer = 0;
var qmCmBad : Integer = 0;
var qmCmCalls : Integer = 0;
var qmCmJobs : Integer = 0;
var qmCmName : array [0..qmCmBatch-1] of String;
var qmCmIn : Integer = ParserSelectByKey('qm_mg_in');
var qmCmRes : Integer = ParserSelectByKey('qm_mg');
var qmCmCore : Integer = GetTriggerManagerStateMachineHandle('qm_core');

//! The next space-separated token of qmCnRest.
procedure qmCmNext(var qmCnRest : String; var qmCnTok : String);
begin
   var qmCnAt : Integer = StrPos(' ', qmCnRest);
   if (qmCnAt>0) then
   begin
      qmCnTok := SubStr(qmCnRest, 1, qmCnAt-1);
      qmCnRest := SubStr(qmCnRest, qmCnAt+1, StrLength(qmCnRest)-qmCnAt);
   end
   else
   begin
      qmCnTok := qmCnRest;
      qmCnRest := '';
   end;
end;

//! Run the merges queued in qm_mg_in and note what each one did.
procedure qmCmFlush;
begin
   var qmCfK : Integer;
   var qmCfJ : String;
   var qmCfDone : String;
   var qmCfT0 : Float;
   if (qmCmJobs>0) then
   begin
      ParserSetValueByKeyByHandle(qmCmIn, 'jobs', IntToStr(qmCmJobs));
      ParserClearByHandle(qmCmRes);
      qmLog('m3 call '+IntToStr(qmCmCalls)+' from '+qmCmName[0]+' merges='+IntToStr(qmCmJobs));
      qmCfT0 := _misc_GetRealTime;
      StateMachineExecuteState(qmCmCore, 'qmMerge', 0);
      qmCmSum := qmCmSum+'m3call|'+IntToStr(qmCmCalls)+'|'+IntToStr(qmCmJobs)+'|'+FloatToStr((_misc_GetRealTime-qmCfT0)*1000)+'~013~010';
      for qmCfK:=0 to qmCmJobs-1 do
      begin
         qmCfJ := 'j'+IntToStr(qmCfK);
         qmCfDone := ParserGetValueByKeyByHandle(qmCmRes, qmCfJ+'done');
         if (qmCfDone<>'1') then
         begin
            qmCfDone := '0';
            qmCmBad := qmCmBad+1;
         end;
         qmCmRuns := qmCmRuns+1;
         qmCmSum := qmCmSum+'m3case|'+qmCmName[qmCfK]+'|'+qmCfDone+'|'+ParserGetValueByKeyByHandle(qmCmRes, qmCfJ+'written')+'|'+ParserGetValueByKeyByHandle(qmCmRes, qmCfJ+'ms')+'|'+ParserGetValueByKeyByHandle(qmCmRes, qmCfJ+'msload')+'|'+ParserGetValueByKeyByHandle(qmCmRes, qmCfJ+'msdiff')+'|'+ParserGetValueByKeyByHandle(qmCmRes, qmCfJ+'msmerge')+'|'+ParserGetValueByKeyByHandle(qmCmRes, qmCfJ+'mswrite')+'~013~010';
         qmLog('m3 '+qmCmName[qmCfK]+' done='+qmCfDone+' '+ParserGetValueByKeyByHandle(qmCmRes, qmCfJ+'mode')+' '+ParserGetValueByKeyByHandle(qmCmRes, qmCfJ+'status')+' hunks='+ParserGetValueByKeyByHandle(qmCmRes, qmCfJ+'hunks')+' conflicts='+ParserGetValueByKeyByHandle(qmCmRes, qmCfJ+'conflicts')+' written='+ParserGetValueByKeyByHandle(qmCmRes, qmCfJ+'written')+' ms='+ParserGetValueByKeyByHandle(qmCmRes, qmCfJ+'ms'));
      end;
      qmCmCalls := qmCmCalls+1;
      qmCmJobs := 0;
      ParserClearByHandle(qmCmIn);
   end;
end;

if (qmCmIn=0) then
qmCmIn := ParserCreate('qm_mg_in');
if (qmCmRes=0) then
qmCmRes := ParserCreate('qm_mg');
ParserClearByHandle(qmCmIn);
if (qmCmCase<>0) then
qmCmCode := ParserSelectByHandleByKey(qmCmCase, 'Code');
if (qmCmCode<>0) then
for qmCmI:=1 to ParserGetCountByHandle(qmCmCode)-1 do
begin
   qmCmV := ParserGetValueByIndexByHandle(qmCmCode, qmCmI);
   if (SubStr(qmCmV, 1, 7)=';suite ') then
   qmCmSuite := SubStr(qmCmV, 8, StrLength(qmCmV)-7);
end;
//! The case file and the suite are printable ASCII without trailing blanks,
//! so the parser reads them losslessly.
var qmCmSp : Integer = 0;
var qmCmSc : Integer = 0;
if (qmCmSuite<>'') then
qmCmSp := qmIncLoad('qm_m3_suite', qmCmApp+qmCmSuite);
if (qmCmSp<>0) then
qmCmSc := ParserSelectByHandleByKey(qmCmSp, 'Code');
qmLog('m3 suite '+qmCmSuite+' merges='+IntToStr(ParserGetCountByHandle(qmCmSc)));
if (qmCmSc<>0) and (qmCmCore<>0) then
for qmCmI:=0 to ParserGetCountByHandle(qmCmSc)-1 do
begin
   qmCmV := ParserGetValueByIndexByHandle(qmCmSc, qmCmI);
   if (SubStr(qmCmV, 1, 6)=';case ') then
   begin
      qmCmTok := 'j'+IntToStr(qmCmJobs);
      qmCmRest := SubStr(qmCmV, 7, StrLength(qmCmV)-6);
      qmCmNext(qmCmRest, qmCmV);
      qmCmName[qmCmJobs] := qmCmV;
      ParserSetValueByKeyByHandle(qmCmIn, qmCmTok+'out', qmCmOutDir+qmCmV+'.inc');
      ParserSetValueByKeyByHandle(qmCmIn, qmCmTok+'dump', qmCmOutDir+qmCmV+'.txt');
      qmCmNext(qmCmRest, qmCmV);
      ParserSetValueByKeyByHandle(qmCmIn, qmCmTok+'base', qmCmApp+'data\'+qmCmV);
      qmCmNext(qmCmRest, qmCmV);
      if (qmCmV='-') then
      ParserSetValueByKeyByHandle(qmCmIn, qmCmTok+'hook', '')
      else
      ParserSetValueByKeyByHandle(qmCmIn, qmCmTok+'hook', qmCmApp+qmCmV);
      qmCmParts := 0;
      while (qmCmRest<>'') do
      begin
         qmCmNext(qmCmRest, qmCmV);
         ParserSetValueByKeyByHandle(qmCmIn, qmCmTok+'p'+IntToStr(qmCmParts), qmCmApp+qmCmV);
         qmCmParts := qmCmParts+1;
      end;
      ParserSetValueByKeyByHandle(qmCmIn, qmCmTok+'parts', IntToStr(qmCmParts));
      qmCmJobs := qmCmJobs+1;
      if (qmCmJobs=qmCmBatch) then
      qmCmFlush;
   end;
end;
qmCmFlush;
qmCmSum := qmCmSum+'m3|'+IntToStr(qmCmRuns)+'|'+IntToStr(qmCmBad)+'~013~010';
qmRawWriteStr(qmCmOut, qmCmSum);
qmLog('m3 suite done merges='+IntToStr(qmCmRuns)+' not done='+IntToStr(qmCmBad));
if (qmCmSc=0) or (qmCmCore=0) then
ParserSetValueByKeyByHandle(qmCmRt, 'status', 'no-suite')
else
if (qmCmBad>0) then
ParserSetValueByKeyByHandle(qmCmRt, 'status', 'incomplete')
else
ParserSetValueByKeyByHandle(qmCmRt, 'status', 'ok');
