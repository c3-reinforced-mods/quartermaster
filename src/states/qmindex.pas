state: qmIndex
into: data/quartermaster/core.aix
helpers: qmlog
requires:
---
//! The index driver: build the scan list, then call qmIndexStep until the
//! cursor reaches the end. A step that does not move the cursor (a state that
//! failed to compile leaves it where it was) ends the loop instead of hanging
//! the game; the log says so.
var qmIxCore : Integer = GetTriggerManagerStateMachineHandle('qm_core');
var qmIxT0 : Float = _misc_GetRealTime;
StateMachineExecuteState(qmIxCore, 'qmIndexBegin', 0);
var qmIxIdx : Integer = ParserSelectByKey('qm_index');
var qmIxRounds : Integer = 0;
var qmIxLast : Integer = -1;
var qmIxGo : Boolean = True;
while (qmIxGo) and (ParserGetIntValueByKeyByHandle(qmIxIdx, 'done')=0) do
begin
   StateMachineExecuteState(qmIxCore, 'qmIndexStep', 0);
   qmIxRounds := qmIxRounds+1;
   if (ParserGetIntValueByKeyByHandle(qmIxIdx, 'cur')=qmIxLast) then
   begin
      qmLog('index step made no progress at '+IntToStr(qmIxLast)+'; scan abandoned');
      qmIxGo := False;
   end;
   qmIxLast := ParserGetIntValueByKeyByHandle(qmIxIdx, 'cur');
end;
var qmIxN : Integer = ParserGetIntValueByKeyByHandle(qmIxIdx, 'n');
var qmIxHit : Integer = 0;
var qmIxK : Integer;
for qmIxK:=0 to qmIxN-1 do
if (ParserGetValueByKeyByHandle(qmIxIdx, 'v'+IntToStr(qmIxK))<>'-') then
qmIxHit := qmIxHit+1;
qmLog('index scanned='+IntToStr(qmIxN)+' provided='+IntToStr(qmIxHit)+' fileage calls='+IntToStr(ParserGetIntValueByKeyByHandle(qmIxIdx, 'calls'))+' steps='+IntToStr(qmIxRounds)+' ms='+FloatToStr((_misc_GetRealTime-qmIxT0)*1000));
