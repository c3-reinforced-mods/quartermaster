state: qmCaseBisect
into: data/quartermaster/selftest.aix
helpers: qmstr, qmraw
requires:
---
//! SelfTest case `bisect`: which construct of a state keeps it from compiling.
//! The candidate states come in the case file, not from the build: the build's
//! lints refuse the very constructs under test. They are written as an .aix
//! with the raw writer and loaded into a manager of their own, like the
//! capability probes' candidates; a state that does not compile logs
//! `Compile script error: <state>` and does not run.
//!
//!   aix <name> <text>   write <text> (an internal string) as <name> and load
//!                       it into the manager qm_bisect
//!   state <name>        run that state: bisect|name|<ran>|<done>
//!
//! Every candidate sets bs_ran = 1 in qm_case_rt as its first statement and
//! bs_done = 1 as its last. A control state that does neither means the file
//! itself did not load (it ends in the raw writer's padding spaces).
var qmBcRt : Integer = ParserSelectByKey('qm_case_rt');
var qmBcOutDir : String = ParserGetValueByKeyByHandle(qmBcRt, 'outdir');
var qmBcOut : String = ParserGetValueByKeyByHandle(qmBcRt, 'out');
var qmBcCode : Integer = ParserSelectByHandleByKey(ParserSelectByKey('qm_case'), 'Code');
var qmBcNd : Integer = ParserGetCountByHandle(qmBcCode);
var qmBcDump : String = '';
var qmBcD : Integer;
var qmBcDir : String;
var qmBcVerb : String;
var qmBcName : String;
var qmBcText : String;
var qmBcH : Integer = 0;
for qmBcD:=1 to qmBcNd-1 do
begin
   qmBcDir := ParserGetValueByIndexByHandle(qmBcCode, qmBcD);
   if (SubStr(qmBcDir, 1, 1)=';') then
   qmBcDir := SubStr(qmBcDir, 2, StrLength(qmBcDir)-1);
   qmField(qmBcDir, ' ', 0, qmBcVerb);
   qmField(qmBcDir, ' ', 1, qmBcName);
   qmField(qmBcDir, ' ', 2, qmBcText);
   if (qmBcVerb='aix') then
   begin
      qmRawWriteStr(qmBcOutDir+qmBcName, qmBcText);
      qmBcH := GetTriggerManagerStateMachineHandle('qm_bisect');
      if (qmBcH=0) then
      begin
         TriggerManagerAdd('qm_bisect');
         qmBcH := GetTriggerManagerStateMachineHandle('qm_bisect');
      end;
      StateMachineLoadFromFile(qmBcH, qmBcOutDir+qmBcName);
      qmBcDump := qmBcDump+'aix|'+qmBcName+'|'+IntToStr(qmBcH)+'~013~010';
   end;
   //! file <name>: load <save>\quartermaster\<name>, a candidate the run's
   //! start state brought (hrun --state), for candidates too big for a case.
   if (qmBcVerb='file') then
   begin
      qmBcH := GetTriggerManagerStateMachineHandle('qm_bisect');
      if (qmBcH=0) then
      begin
         TriggerManagerAdd('qm_bisect');
         qmBcH := GetTriggerManagerStateMachineHandle('qm_bisect');
      end;
      StateMachineLoadFromFile(qmBcH, GetAppSaveDirectoryPath+'quartermaster\'+qmBcName);
      qmBcDump := qmBcDump+'file|'+qmBcName+'|'+IntToStr(FileAge(GetAppSaveDirectoryPath+'quartermaster\'+qmBcName))+'~013~010';
   end;
   if (qmBcVerb='state') and (qmBcH<>0) then
   begin
      ParserSetIntValueByKeyByHandle(qmBcRt, 'bs_ran', 0);
      ParserSetIntValueByKeyByHandle(qmBcRt, 'bs_done', 0);
      StateMachineExecuteState(qmBcH, qmBcName, 0);
      qmBcDump := qmBcDump+'bisect|'+qmBcName+'|'+IntToStr(ParserGetIntValueByKeyByHandle(qmBcRt, 'bs_ran'))+'|'+IntToStr(ParserGetIntValueByKeyByHandle(qmBcRt, 'bs_done'))+'~013~010';
   end;
   qmRawWriteStr(qmBcOut, qmBcDump);
end;
qmRawWriteStr(qmBcOut, qmBcDump);
ParserSetValueByKeyByHandle(qmBcRt, 'status', 'ok');
