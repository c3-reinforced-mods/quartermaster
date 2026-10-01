state: qmHostSend
into: data/quartermaster/core.aix
helpers: qmlog
requires:
---
//! Settings of `host` scope (docs/authoring.md), the host's side: while a
//! LAN room is open, qmTick runs this about once a second and it sends the
//! host's values of every such setting of the loaded mods to the players in
//! the room, as a parser of its own message number (7301; vanilla's numbers
//! end at 300, classes.script:7560-7591) - the way vanilla sends its own
//! room data (LanSendParser, eventcustomgame.inc:369). A client's qmHostRecv
//! takes them. Nothing is sent when no loaded mod has such a setting, or
//! when qm_rt hsdry = 1 (a SelfTest run: the parser is built, not sent).
//!
//! The parser qm_hostout: n, and per value k m<k> (the mod's id, the child
//! of qm_settings), s<k> (the setting's id), v<k> (the value); sig - all of
//! them in one string, so a client applies a changed set once.
const qmHsMsg = 7301;
var qmHsRt : Integer = ParserSelectByKey('qm_rt');
var qmHsAb : Integer = ParserSelectByKey('qm_about');
var qmHsMods : Integer = ParserSelectByKey('qm_mods');
var qmHsSet : Integer = ParserSelectByKey('qm_settings');
var qmHsOut : Integer = ParserSelectByKey('qm_hostout');
var qmHsN : Integer = 0;
var qmHsDrop : Integer = 0;
var qmHsSig : String = '';
var qmHsI : Integer;
var qmHsK : Integer;
var qmHsCh : Integer;
var qmHsMid : String;
var qmHsSid : String;
var qmHsV : String;
var qmHsKs : String;
if (qmHsOut=0) then
qmHsOut := ParserCreate('qm_hostout');
ParserClearByHandle(qmHsOut);
if (qmHsAb<>0) and (qmHsMods<>0) and (qmHsSet<>0) then
for qmHsI:=0 to ParserGetIntValueByKeyByHandle(qmHsAb, 'n')-1 do
if (ParserGetIntValueByKeyByHandle(qmHsMods, 'on'+IntToStr(qmHsI))=1) then
begin
   qmHsMid := ParserGetValueByKeyByHandle(qmHsAb, 'mid'+IntToStr(qmHsI));
   qmHsCh := 0;
   if (qmHsMid<>'') then
   qmHsCh := ParserSelectByHandleByKey(qmHsSet, qmHsMid);
   if (qmHsCh<>0) then
   for qmHsK:=0 to ParserGetIntValueByKeyByHandle(qmHsAb, 'sn'+IntToStr(qmHsI))-1 do
   begin
      qmHsKs := IntToStr(qmHsI)+'_'+IntToStr(qmHsK);
      //! At most 256 values in one message; the rest stay each player's own,
      //! and the log line says how many.
      if (ParserGetValueByKeyByHandle(qmHsAb, 'ssc'+qmHsKs)='host') and (qmHsN>=256) then
      qmHsDrop := qmHsDrop+1
      else
      if (ParserGetValueByKeyByHandle(qmHsAb, 'ssc'+qmHsKs)='host') then
      begin
         qmHsSid := ParserGetValueByKeyByHandle(qmHsAb, 'sid'+qmHsKs);
         qmHsV := ParserGetValueByKeyByHandle(qmHsCh, qmHsSid);
         ParserSetValueByKeyByHandle(qmHsOut, 'm'+IntToStr(qmHsN), qmHsMid);
         ParserSetValueByKeyByHandle(qmHsOut, 's'+IntToStr(qmHsN), qmHsSid);
         ParserSetValueByKeyByHandle(qmHsOut, 'v'+IntToStr(qmHsN), qmHsV);
         qmHsSig := qmHsSig+qmHsMid+'.'+qmHsSid+'='+qmHsV+';';
         qmHsN := qmHsN+1;
      end;
   end;
end;
ParserSetIntValueByKeyByHandle(qmHsOut, 'n', qmHsN);
ParserSetValueByKeyByHandle(qmHsOut, 'sig', qmHsSig);
ParserSetIntValueByKeyByHandle(qmHsRt, 'hsdrop', qmHsDrop);
if (qmHsN>0) then
begin
   if (ParserGetIntValueByKeyByHandle(qmHsRt, 'hsdry')<>1) then
   LanSendParser(qmHsMsg, qmHsOut);
   ParserSetIntValueByKeyByHandle(qmHsRt, 'hssent', ParserGetIntValueByKeyByHandle(qmHsRt, 'hssent')+1);
   //! One line when the set changes, not one a second.
   if (ParserGetValueByKeyByHandle(qmHsRt, 'hslast')<>qmHsSig) then
   begin
      qmLog('host settings sent: '+IntToStr(qmHsN)+' value(s), sends='+IntToStr(ParserGetIntValueByKeyByHandle(qmHsRt, 'hssent'))+' dry='+IntToStr(ParserGetIntValueByKeyByHandle(qmHsRt, 'hsdry')));
      if (qmHsDrop>0) then
      qmLog('host settings: '+IntToStr(qmHsDrop)+' more not sent, at most 256 in one message; the players keep their own');
   end;
   ParserSetValueByKeyByHandle(qmHsRt, 'hslast', qmHsSig);
end;
