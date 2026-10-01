state: qmSetSave
into: data/quartermaster/core.aix
helpers: qmlog
requires:
---
//! The Options view's save (qmUiAct optacc sets qm_rt setsave, and qmTick
//! runs this on the next main-menu frame): qm_settings - already in effect -
//! into <save>\quartermaster\settings.cfg, the file qmSettings loads at every
//! boot. The window itself writes nothing to disk (docs/ui.md).
//!
//! In a LAN session where the host's values of `host` settings are in effect
//! (qmHostRecv, qm_hostown), the file gets this machine's own values for
//! them, never the host's: those hold for the session only, and a host's
//! value saved here would stay the player's after it. A host setting the
//! player changed in the Options view meanwhile (its value is no longer the
//! host's) is the player's own from now on - saved, and back after the
//! session - while the host's value stays in effect until then. The swap
//! happens inside this one state run, so nothing else sees it.
var qmSsRt : Integer = ParserSelectByKey('qm_rt');
var qmSsSet : Integer = ParserSelectByKey('qm_settings');
var qmSsOwn : Integer = ParserSelectByKey('qm_hostown');
var qmSsPath : String = GetAppSaveDirectoryPath+'quartermaster\settings.cfg';
var qmSsN : Integer = 0;
var qmSsK : Integer;
var qmSsCh : Integer;
var qmSsSid : String;
var qmSsCur : String;
var qmSsMine : Integer = 0;
var qmSsOut : Integer = 0;
if (qmSsSet=0) then
exit;
if (qmSsOwn<>0) and (ParserGetIntValueByKeyByHandle(qmSsRt, 'hostin')=1) then
qmSsN := ParserGetIntValueByKeyByHandle(qmSsOwn, 'n');
for qmSsK:=0 to qmSsN-1 do
begin
   qmSsCh := ParserSelectByHandleByKey(qmSsSet, ParserGetValueByKeyByHandle(qmSsOwn, 'm'+IntToStr(qmSsK)));
   if (qmSsCh<>0) then
   begin
      qmSsSid := ParserGetValueByKeyByHandle(qmSsOwn, 's'+IntToStr(qmSsK));
      qmSsCur := ParserGetValueByKeyByHandle(qmSsCh, qmSsSid);
      if (qmSsCur<>ParserGetValueByKeyByHandle(qmSsOwn, 't'+IntToStr(qmSsK))) then
      begin
         ParserSetValueByKeyByHandle(qmSsOwn, 'o'+IntToStr(qmSsK), qmSsCur);
         qmSsMine := qmSsMine+1;
      end;
      ParserSetValueByKeyByHandle(qmSsCh, qmSsSid, ParserGetValueByKeyByHandle(qmSsOwn, 'o'+IntToStr(qmSsK)));
      qmSsOut := qmSsOut+1;
   end;
end;
qmLog('tick: settings saved='+BoolToStr(ParserSaveToFileByHandle(qmSsSet, qmSsPath))+' seq='+IntToStr(ParserGetIntValueByKeyByHandle(qmSsRt, 'setsaveseq'))+' host values kept out='+IntToStr(qmSsOut)+' changed here='+IntToStr(qmSsMine));
//! The host's values back in effect.
for qmSsK:=0 to qmSsN-1 do
begin
   qmSsCh := ParserSelectByHandleByKey(qmSsSet, ParserGetValueByKeyByHandle(qmSsOwn, 'm'+IntToStr(qmSsK)));
   if (qmSsCh<>0) then
   ParserSetValueByKeyByHandle(qmSsCh, ParserGetValueByKeyByHandle(qmSsOwn, 's'+IntToStr(qmSsK)), ParserGetValueByKeyByHandle(qmSsOwn, 't'+IntToStr(qmSsK)));
end;
