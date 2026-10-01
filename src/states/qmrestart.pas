state: qmRestart
into: data/quartermaster/core.aix
helpers: qmlog
requires:
---
//! The restart, the vanilla way and nothing else (plan G14): the sequence the
//! game runs itself when a Workshop update needs one,
//! data/gui/menu.inc/onworkshopautoupdate.inc:8-11 - LanShutdown;
//! SteamwrapFree; RestartApplicationParam(''). The earlier probe rounds
//! restarted the game this way after writing into a mod folder and mods.ini,
//! and the new process loaded both (docs/research/context-2026-09-27.md
//! section 3). Only qmTick runs it, after every guard of plan S8 agreed.
//! The SelfTest's compile step (qmcasem5.pas) sets qm_rt rsdry: then this
//! state proves that it compiles and returns before the restart.
var qmReRt : Integer = ParserSelectByKey('qm_rt');
if (qmReRt<>0) then
if (ParserGetIntValueByKeyByHandle(qmReRt, 'rsdry')=1) then
begin
   ParserSetIntValueByKeyByHandle(qmReRt, 'rsdryok', 1);
   qmLog('restart: dry run for the SelfTest, not restarting');
   exit;
end;
qmLog('restart: LanShutdown, SteamwrapFree, RestartApplicationParam');
LanShutdown;
SteamwrapFree;
RestartApplicationParam('');
