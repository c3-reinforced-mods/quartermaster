state: qmMerge
into: data/quartermaster/core.aix
helpers: qmlog, qmmerge
requires:
---
//! Three-way merges of .inc files (plan G8 + G9), a batch per call: the named
//! parser qm_mg_in holds `jobs` and, per merge j, the keys qmmerge.pas
//! qmMgRun lists; the results go to qm_mg (and to the files named there),
//! `done` = 1 once every merge of the batch is through. The caller fills
//! qm_mg_in and runs this state synchronously with StateMachineExecuteState,
//! the way qmBoot runs its pipeline, and reads qm_mg when the call returns.
//!
//! Why a batch: the read seam's pool is a String array of 65 536 elements, and
//! a String array costs about 4.6 us per element on every call of the state
//! that declares it (probe 4) - 0.3 s per call, the same for one merge or
//! many. The Integer arrays (about 880 000 of plan S14's 1 000 000) cost
//! nothing measurable.
var qmMsIn : Integer = ParserSelectByKey('qm_mg_in');
var qmMsJobs : Integer = 0;
var qmMsK : Integer;
//! `res` names another result parser: qmGenerate's second batch (the merges
//! without the participants that lost a conflict) goes to qm_ms, so the first
//! batch's qm_mg stays as it was.
var qmMsRes : String = 'qm_mg';
if (qmMsIn<>0) then
if (ParserGetValueByKeyByHandle(qmMsIn, 'res')<>'') then
qmMsRes := ParserGetValueByKeyByHandle(qmMsIn, 'res');
qmMgRes := ParserSelectByKey(qmMsRes);
if (qmMgRes=0) then
qmMgRes := ParserCreate(qmMsRes);
ParserClearByHandle(qmMgRes);
if (qmMsIn=0) then
qmLog('merge: no qm_mg_in parser, nothing to merge')
else
begin
   qmMsJobs := ParserGetIntValueByKeyByHandle(qmMsIn, 'jobs');
   for qmMsK:=0 to qmMsJobs-1 do
   qmMgRun(qmMsIn, qmMsK);
end;
ParserSetValueByKeyByHandle(qmMgRes, 'jobs', IntToStr(qmMsJobs));
ParserSetValueByKeyByHandle(qmMgRes, 'done', '1');
