state: qmCaseHost
into: data/quartermaster/selftest.aix
helpers: qmlog, qmraw
requires:
---
//! SelfTest case `host`: the two halves of the settings of `host` scope in
//! the game's own interpreter, without a second machine - qmHostSend with
//! qm_rt hsdry = 1 (the message built, not sent) and qmHostRecv reading a
//! message this case builds (qm_rt hsparser) the way a client would get the
//! host's. The transport between two machines stays a test on two PCs.
//! Directive: mod <id> - the mod whose settings are used (its about.cfg
//! declares `rate` (int, host), `name` (text, host), `local` (bool)).
//! Dump lines (read by the in-game check):
//!   send|<n>|<m0>|<s0>|<v0>|...|<sig>        what the host would send
//!   recv|<rate>|<name>|<local>|<hostin>|<hostn>  after the host's message
//!   again|<rate>                               the same message once more
//!   bad|<rate>|<name>|<hostn>                  a message with a rate off 1..10
//!   save|<file rate>|<file name>|<rate>|<name> the Options save in the session:
//!                                              settings.cfg, then what is in effect
//!   back|<rate>|<name>                         after settings.cfg is read again
var qmChRt : Integer = ParserSelectByKey('qm_case_rt');
var qmChOut : String = ParserGetValueByKeyByHandle(qmChRt, 'out');
var qmChCode : Integer = ParserSelectByHandleByKey(ParserSelectByKey('qm_case'), 'Code');
var qmChCore : Integer = GetTriggerManagerStateMachineHandle('qm_core');
var qmChQrt : Integer = ParserSelectByKey('qm_rt');
var qmChDump : String = '';
var qmChMod : String = 'qmtesthost';
var qmChS : String;
var qmChD : Integer;
var qmChK : Integer;
var qmChO : Integer;
var qmChM : Integer;
var qmChSet : Integer;
var qmChCh : Integer;

procedure qmChPut(const qmCpLine : String);
begin
   qmChDump := qmChDump+qmCpLine+'~013~010';
   qmRawWriteStr(qmChOut, qmChDump);
   qmLog('host case '+qmCpLine);
end;
procedure qmChVal(const qmCvKey : String; var qmCvOut : String);
begin
   var qmCvSet : Integer = ParserSelectByKey('qm_settings');
   var qmCvCh : Integer = 0;
   qmCvOut := '-';
   if (qmCvSet<>0) then
   qmCvCh := ParserSelectByHandleByKey(qmCvSet, qmChMod);
   if (qmCvCh<>0) then
   qmCvOut := ParserGetValueByKeyByHandle(qmCvCh, qmCvKey);
end;

for qmChD:=1 to ParserGetCountByHandle(qmChCode)-1 do
begin
   qmChS := ParserGetValueByIndexByHandle(qmChCode, qmChD);
   if (SubStr(qmChS, 1, 5)=';mod ') then
   qmChMod := SubStr(qmChS, 6, StrLength(qmChS)-5);
end;
//! The host's half: the message built, not sent.
ParserSetIntValueByKeyByHandle(qmChQrt, 'hsdry', 1);
StateMachineExecuteState(qmChCore, 'qmHostSend', 0);
ParserSetIntValueByKeyByHandle(qmChQrt, 'hsdry', 0);
qmChO := ParserSelectByKey('qm_hostout');
qmChS := 'send|'+IntToStr(ParserGetIntValueByKeyByHandle(qmChO, 'n'));
for qmChK:=0 to ParserGetIntValueByKeyByHandle(qmChO, 'n')-1 do
qmChS := qmChS+'|'+ParserGetValueByKeyByHandle(qmChO, 'm'+IntToStr(qmChK))+'|'+ParserGetValueByKeyByHandle(qmChO, 's'+IntToStr(qmChK))+'|'+ParserGetValueByKeyByHandle(qmChO, 'v'+IntToStr(qmChK));
qmChPut(qmChS+'|'+ParserGetValueByKeyByHandle(qmChO, 'sig'));
//! A client's half: the host's message, as the engine would hand it over.
qmChM := ParserSelectByKey('qm_case_hostmsg');
if (qmChM=0) then
qmChM := ParserCreate('qm_case_hostmsg');
ParserClearByHandle(qmChM);
ParserSetIntValueByKeyByHandle(qmChM, 'n', 4);
ParserSetValueByKeyByHandle(qmChM, 'm0', qmChMod);
ParserSetValueByKeyByHandle(qmChM, 's0', 'rate');
ParserSetValueByKeyByHandle(qmChM, 'v0', '9');
ParserSetValueByKeyByHandle(qmChM, 'm1', qmChMod);
ParserSetValueByKeyByHandle(qmChM, 's1', 'name');
ParserSetValueByKeyByHandle(qmChM, 'v1', 'host');
ParserSetValueByKeyByHandle(qmChM, 'm2', qmChMod);
ParserSetValueByKeyByHandle(qmChM, 's2', 'local');
ParserSetValueByKeyByHandle(qmChM, 'v2', '0');
ParserSetValueByKeyByHandle(qmChM, 'm3', 'qmtestnomod');
ParserSetValueByKeyByHandle(qmChM, 's3', 'rate');
ParserSetValueByKeyByHandle(qmChM, 'v3', '1');
ParserSetValueByKeyByHandle(qmChM, 'sig', 'host case 1');
ParserSetIntValueByKeyByHandle(qmChQrt, 'hsparser', qmChM);
StateMachineExecuteState(qmChCore, 'qmHostRecv', 0);
qmChVal('rate', qmChS);

var qmChName : String;
var qmChLocal : String;
qmChVal('name', qmChName);
qmChVal('local', qmChLocal);
qmChPut('recv|'+qmChS+'|'+qmChName+'|'+qmChLocal+'|'+IntToStr(ParserGetIntValueByKeyByHandle(qmChQrt, 'hostin'))+'|'+IntToStr(ParserGetIntValueByKeyByHandle(qmChQrt, 'hostn')));
//! The same message again changes nothing.
qmChSet := ParserSelectByKey('qm_settings');
qmChCh := ParserSelectByHandleByKey(qmChSet, qmChMod);
if (qmChCh<>0) then
ParserSetValueByKeyByHandle(qmChCh, 'rate', '3');
StateMachineExecuteState(qmChCore, 'qmHostRecv', 0);
qmChVal('rate', qmChS);
qmChPut('again|'+qmChS);
//! A host with another version of the mod: rate 99 is off this copy's
//! 1..10 and is not taken; the name fits and is.
ParserClearByHandle(qmChM);
ParserSetIntValueByKeyByHandle(qmChM, 'n', 2);
ParserSetValueByKeyByHandle(qmChM, 'm0', qmChMod);
ParserSetValueByKeyByHandle(qmChM, 's0', 'rate');
ParserSetValueByKeyByHandle(qmChM, 'v0', '99');
ParserSetValueByKeyByHandle(qmChM, 'm1', qmChMod);
ParserSetValueByKeyByHandle(qmChM, 's1', 'name');
ParserSetValueByKeyByHandle(qmChM, 'v1', 'abc');
ParserSetValueByKeyByHandle(qmChM, 'sig', 'host case 2');
StateMachineExecuteState(qmChCore, 'qmHostRecv', 0);
qmChVal('rate', qmChS);
qmChVal('name', qmChName);
qmChPut('bad|'+qmChS+'|'+qmChName+'|'+IntToStr(ParserGetIntValueByKeyByHandle(qmChQrt, 'hostn')));
//! The Options view's save in the session (qmSetSave): the file gets the
//! own values - rate 3, which the player set above, and name x - while the
//! host's (9, abc) stay in effect.
StateMachineExecuteState(qmChCore, 'qmSetSave', 0);
var qmChFile : Integer = ParserSelectByKey('qm_case_hostfile');
if (qmChFile=0) then
qmChFile := ParserCreate('qm_case_hostfile');
ParserClearByHandle(qmChFile);
var qmChFr : String = '-';
var qmChFn : String = '-';
if ParserLoadFromFileByHandle(qmChFile, GetAppSaveDirectoryPath+'quartermaster\settings.cfg') then
begin
   var qmChFc : Integer = ParserSelectByHandleByKey(qmChFile, qmChMod);
   if (qmChFc<>0) then
   begin
      qmChFr := ParserGetValueByKeyByHandle(qmChFc, 'rate');
      qmChFn := ParserGetValueByKeyByHandle(qmChFc, 'name');
   end;
end;
ParserClearByHandle(qmChFile);
qmChVal('rate', qmChS);
qmChVal('name', qmChName);
qmChPut('save|'+qmChFr+'|'+qmChFn+'|'+qmChS+'|'+qmChName);
//! The session over: qmTick clears qm_hostown and reads settings.cfg again
//! (qmSettings).
ParserSetIntValueByKeyByHandle(qmChQrt, 'hsparser', 0);
ParserSetIntValueByKeyByHandle(qmChQrt, 'hostin', 0);
ParserSetValueByKeyByHandle(qmChQrt, 'hssig', '');
if (ParserSelectByKey('qm_hostown')<>0) then
ParserClearByHandle(ParserSelectByKey('qm_hostown'));
StateMachineExecuteState(qmChCore, 'qmSettings', 0);
qmChVal('rate', qmChS);
qmChVal('name', qmChName);
qmChPut('back|'+qmChS+'|'+qmChName);
ParserSetValueByKeyByHandle(qmChRt, 'status', 'ok');
