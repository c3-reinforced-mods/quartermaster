state: qmHostRecv
into: data/quartermaster/core.aix
helpers: qmlog, qmstr, qmnum, qmsetfit
requires:
---
//! Settings of `host` scope (docs/authoring.md), a client's side. The
//! OnLanEvent hook (src/hooks/onlanevent.pas) runs it while the engine hands
//! the game a received parser - the moment vanilla's own receiver reads one
//! (ParserReceived, onlanevent.inc:176-215) - when that is the host's message
//! (number 7301, qmHostSend) and this machine is a client. Its values
//! replace this machine's in qm_settings for the session: only for a setting
//! a loaded mod declares with `host` scope, only a value that fits this
//! copy's declaration (qmSetFits: a host with another version of the mod can
//! send what this one does not declare), and once per set (sig).
//!
//! qm_hostown keeps what the session replaced: n, and per value k m<k> (the
//! mod's id, the child of qm_settings), s<k> (the setting's id), o<k> (this
//! machine's own value, taken the first time only) and t<k> (the host's value
//! in effect now). The Options view's save (qmSetSave) writes the own values,
//! never the host's, and qmTick reads settings.cfg again once the LAN session
//! is over (qm_rt hostin).
//!
//! qm_rt hsparser: a parser handle to read instead of the engine's (a
//! SelfTest run, which has no host to hear).
const qmHrMsg = 7301;
var qmHrRt : Integer = ParserSelectByKey('qm_rt');
var qmHrAb : Integer = ParserSelectByKey('qm_about');
var qmHrSet : Integer = ParserSelectByKey('qm_settings');
var qmHrP : Integer = ParserGetIntValueByKeyByHandle(qmHrRt, 'hsparser');
var qmHrSig : String;
var qmHrN : Integer;
var qmHrI : Integer;
var qmHrK : Integer;
var qmHrJ : Integer;
var qmHrOk : Integer = 0;
var qmHrNo : Integer = 0;
var qmHrBad : Integer = 0;
var qmHrMid : String;
var qmHrSid : String;
var qmHrV : String;
var qmHrKs : String;
var qmHrSk : String;
var qmHrCh : Integer;
var qmHrE : Integer;
if (qmHrP=0) then
if (LanGetParserID=qmHrMsg) then
qmHrP := LanSelectParser;
if (qmHrP=0) or (qmHrAb=0) or (qmHrSet=0) then
exit;
qmHrSig := ParserGetValueByKeyByHandle(qmHrP, 'sig');
if (qmHrSig='') or (qmHrSig=ParserGetValueByKeyByHandle(qmHrRt, 'hssig')) then
exit;
var qmHrOwn : Integer = ParserSelectByKey('qm_hostown');
if (qmHrOwn=0) then
qmHrOwn := ParserCreate('qm_hostown');
var qmHrOn : Integer = ParserGetIntValueByKeyByHandle(qmHrOwn, 'n');
qmHrN := ParserGetIntValueByKeyByHandle(qmHrP, 'n');
for qmHrJ:=0 to qmHrN-1 do
begin
   qmHrMid := ParserGetValueByKeyByHandle(qmHrP, 'm'+IntToStr(qmHrJ));
   qmHrSid := ParserGetValueByKeyByHandle(qmHrP, 's'+IntToStr(qmHrJ));
   qmHrV := ParserGetValueByKeyByHandle(qmHrP, 'v'+IntToStr(qmHrJ));
   //! The setting as this copy declares it (`<row>_<k>` of qm_about).
   qmHrSk := '';
   for qmHrI:=0 to ParserGetIntValueByKeyByHandle(qmHrAb, 'n')-1 do
   if (ParserGetValueByKeyByHandle(qmHrAb, 'mid'+IntToStr(qmHrI))=qmHrMid) then
   for qmHrK:=0 to ParserGetIntValueByKeyByHandle(qmHrAb, 'sn'+IntToStr(qmHrI))-1 do
   begin
      qmHrKs := IntToStr(qmHrI)+'_'+IntToStr(qmHrK);
      if (ParserGetValueByKeyByHandle(qmHrAb, 'sid'+qmHrKs)=qmHrSid) and (ParserGetValueByKeyByHandle(qmHrAb, 'ssc'+qmHrKs)='host') then
      qmHrSk := qmHrKs;
   end;
   qmHrCh := 0;
   if (qmHrSk<>'') then
   qmHrCh := ParserSelectByHandleByKey(qmHrSet, qmHrMid);
   if (qmHrCh=0) then
   qmHrNo := qmHrNo+1
   else
   if (not qmSetFits(qmHrAb, qmHrSk, qmHrV)) then
   begin
      qmHrBad := qmHrBad+1;
      qmLog('host settings: '+qmHrMid+'.'+qmHrSid+' = ['+qmHrV+'] does not fit this copy''s declaration; this machine''s value stays');
   end
   else
   begin
      qmHrE := -1;
      for qmHrK:=0 to qmHrOn-1 do
      if (ParserGetValueByKeyByHandle(qmHrOwn, 'm'+IntToStr(qmHrK))=qmHrMid) and (ParserGetValueByKeyByHandle(qmHrOwn, 's'+IntToStr(qmHrK))=qmHrSid) then
      qmHrE := qmHrK;
      if (qmHrE<0) then
      begin
         qmHrE := qmHrOn;
         qmHrOn := qmHrOn+1;
         ParserSetValueByKeyByHandle(qmHrOwn, 'm'+IntToStr(qmHrE), qmHrMid);
         ParserSetValueByKeyByHandle(qmHrOwn, 's'+IntToStr(qmHrE), qmHrSid);
         ParserSetValueByKeyByHandle(qmHrOwn, 'o'+IntToStr(qmHrE), ParserGetValueByKeyByHandle(qmHrCh, qmHrSid));
      end;
      ParserSetValueByKeyByHandle(qmHrOwn, 't'+IntToStr(qmHrE), qmHrV);
      ParserSetValueByKeyByHandle(qmHrCh, qmHrSid, qmHrV);
      qmHrOk := qmHrOk+1;
   end;
end;
ParserSetIntValueByKeyByHandle(qmHrOwn, 'n', qmHrOn);
ParserSetValueByKeyByHandle(qmHrRt, 'hssig', qmHrSig);
ParserSetIntValueByKeyByHandle(qmHrRt, 'hostin', 1);
ParserSetIntValueByKeyByHandle(qmHrRt, 'hostn', qmHrOk);
qmLog('host settings taken: '+IntToStr(qmHrOk)+' value(s), '+IntToStr(qmHrNo)+' not declared here with host scope, '+IntToStr(qmHrBad)+' not fitting the declaration here');
