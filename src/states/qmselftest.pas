state: qmSelfTest
into: data/quartermaster/selftest.aix
helpers: qmlog, qmstr, qmraw, qminc
requires:
---
//! The SelfTest runner (plan G18). qmBoot loads selftest.aix and runs this
//! only when <save>\qm_autotest.cfg exists; nothing here runs otherwise.
//!
//! Case files are <save>\qm_test\cases\*.cfg, in the shape ref/selftest.py
//! documents: a one-state .inc whose Code values are directives, the first
//! `kind <kind>`. They are listed with ParserGetFilesInRoot (file names only,
//! as data/scripts/common.inc/generatemap.inc:173-189 uses it); if that finds
//! none, qm_case1.cfg .. qm_case9.cfg are looked for by name. Cases run in
//! file-name order, each in its own state, so a case that does not compile
//! costs only its own result.
//!
//! Results go to <save>\qm_test\out\: <case>.txt from the case state, and
//! done.txt from here with `case|<file>|<kind>|<status>` per case and
//! `done|<cases>|<not ok>`. A status stays `started` when the case state
//! stopped early (a compile error, a runtime exception); that is reported as
//! `crashed`. The raw writer creates the out folder.
var qmStSave : String = GetAppSaveDirectoryPath;
var qmStCases : String = qmStSave+'qm_test\cases\';
var qmStOut : String = qmStSave+'qm_test\out\';
var qmStName : array [0..63] of String;
var qmStNn : Integer = 0;
var qmStI : Integer;
var qmStJ : Integer;
var qmStS : String;
var qmStLs : Integer = ParserSelectByKey('qm_test_ls');
if (qmStLs=0) then
qmStLs := ParserCreate('qm_test_ls');
ParserClearByHandle(qmStLs);
ParserSelectByHandle(qmStLs);
ParserGetFilesInRoot(qmStCases+'*.cfg');
var qmStListed : Integer = ParserGetCountByHandle(qmStLs);
for qmStI:=0 to qmStListed-1 do
if (qmStNn<64) then
begin
   qmStS := ParserGetValueByIndexByHandle(qmStLs, qmStI);
   //! Keep only the part after the last backslash, in case a path comes back.
   while (StrPos('\', qmStS)>0) do
   qmStS := SubStr(qmStS, StrPos('\', qmStS)+1, StrLength(qmStS));
   qmStName[qmStNn] := qmStS;
   qmStNn := qmStNn+1;
end;
if (qmStNn=0) then
for qmStI:=1 to 9 do
if (FileAge(qmStCases+'qm_case'+IntToStr(qmStI)+'.cfg')<>-1) then
begin
   qmStName[qmStNn] := 'qm_case'+IntToStr(qmStI)+'.cfg';
   qmStNn := qmStNn+1;
end;
//! Insertion sort by bytes, so the run order does not depend on the listing.
for qmStI:=1 to qmStNn-1 do
begin
   qmStS := qmStName[qmStI];
   qmStJ := qmStI;
   while (qmStJ>0) and (qmCmpStr(qmStS, qmStName[qmStJ-1])<0) do
   begin
      qmStName[qmStJ] := qmStName[qmStJ-1];
      qmStJ := qmStJ-1;
   end;
   qmStName[qmStJ] := qmStS;
end;
qmLog('selftest start cases='+IntToStr(qmStNn)+' listed='+IntToStr(qmStListed)+' in '+qmStCases);
var qmStT : Integer = GetTriggerManagerStateMachineHandle('qm_test');
var qmStRt : Integer = ParserSelectByKey('qm_case_rt');
if (qmStRt=0) then
qmStRt := ParserCreate('qm_case_rt');
var qmStDone : String = '';
var qmStBad : Integer = 0;
var qmStKind : String;
var qmStStatus : String;
var qmStStem : String;
var qmStCase : Integer;
var qmStCode : Integer;
var qmStEsc : String;
for qmStI:=0 to qmStNn-1 do
begin
   qmStStem := qmStName[qmStI];
   if (StrPos('.', qmStStem)>0) then
   qmStStem := SubStr(qmStStem, 1, StrPos('.', qmStStem)-1);
   ParserSetValueByKeyByHandle(qmStRt, 'outdir', qmStOut);
   ParserSetValueByKeyByHandle(qmStRt, 'out', qmStOut+qmStStem+'.txt');
   ParserSetValueByKeyByHandle(qmStRt, 'status', 'started');
   qmStKind := '';
   qmStCase := qmIncLoad('qm_case', qmStCases+qmStName[qmStI]);
   qmStCode := 0;
   if (qmStCase<>0) then
   qmStCode := ParserSelectByHandleByKey(qmStCase, 'Code');
   if (qmStCode<>0) then
   if (ParserGetCountByHandle(qmStCode)>0) then
   begin
      qmStKind := ParserGetValueByIndexByHandle(qmStCode, 0);
      if (SubStr(qmStKind, 1, 6)=';kind ') then
      qmStKind := SubStr(qmStKind, 7, StrLength(qmStKind)-6)
      else
      qmStKind := '';
   end;
   if (qmStKind='readdump') then
   StateMachineExecuteState(qmStT, 'qmCaseReadDump', 0)
   else
   if (qmStKind='incprobe') then
   StateMachineExecuteState(qmStT, 'qmCaseIncProbe', 0)
   else
   if (qmStKind='plan') then
   StateMachineExecuteState(qmStT, 'qmCasePlan', 0)
   else
   if (qmStKind='keys') then
   StateMachineExecuteState(qmStT, 'qmCaseKeys', 0)
   else
   if (qmStKind='eofprobe') then
   StateMachineExecuteState(qmStT, 'qmCaseEofProbe', 0)
   else
   if (qmStKind='merge') then
   StateMachineExecuteState(qmStT, 'qmCaseMerge', 0)
   else
   if (qmStKind='bisect') then
   StateMachineExecuteState(qmStT, 'qmCaseBisect', 0)
   else
   if (qmStKind='m4gen') then
   StateMachineExecuteState(qmStT, 'qmCaseM4', 0)
   else
   if (qmStKind='ui') then
   StateMachineExecuteState(qmStT, 'qmCaseUi', 0)
   else
   if (qmStKind='m5') then
   StateMachineExecuteState(qmStT, 'qmCaseM5', 0)
   else
   if (qmStKind='opt') then
   StateMachineExecuteState(qmStT, 'qmCaseOpt', 0)
   else
   if (qmStKind='data') then
   StateMachineExecuteState(qmStT, 'qmCaseData', 0)
   else
   if (qmStKind='mod') then
   StateMachineExecuteState(qmStT, 'qmCaseMod', 0)
   else
   if (qmStKind='host') then
   StateMachineExecuteState(qmStT, 'qmCaseHost', 0)
   else
   ParserSetValueByKeyByHandle(qmStRt, 'status', 'unknown-kind');
   qmStStatus := ParserGetValueByKeyByHandle(qmStRt, 'status');
   if (qmStStatus='started') then
   qmStStatus := 'crashed';
   if (qmStStatus<>'ok') then
   qmStBad := qmStBad+1;
   qmEscape(qmStName[qmStI], qmStEsc);
   qmStDone := qmStDone+'case|'+qmStEsc+'|'+qmStKind+'|'+qmStStatus+'~013~010';
   qmLog('selftest case '+qmStName[qmStI]+' '+qmStKind+' '+qmStStatus);
end;
qmStDone := qmStDone+'done|'+IntToStr(qmStNn)+'|'+IntToStr(qmStBad)+'~013~010';
qmRawWriteStr(qmStOut+'done.txt', qmStDone);
qmLog('selftest done cases='+IntToStr(qmStNn)+' failed='+IntToStr(qmStBad));
