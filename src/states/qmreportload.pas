state: qmReportLoad
into: data/quartermaster/core.aix
helpers: qmlog, qmrepcfg
requires:
---
//! The last report back into qm_report, for a boot that does not generate:
//! the manager window shows the statuses of the generation that is running
//! (docs/ui.md). qmReport saved qm_report as <save>\quartermaster\report.cfg
//! with the engine's own parser, which reads its file back here - the raw
//! text in report.txt could not return a mod folder's name byte for byte (no
//! Chr). qmRepCfgLoad takes off the guard that keeps the report's leading
//! spaces through the parser. qm_report is emptied first, and stays empty when
//! there is no file: a missing key reads '' / 0, so the window then shows no
//! report.
var qmRlRep : Integer = ParserSelectByKey('qm_report');
var qmRlPath : String = GetAppSaveDirectoryPath+'quartermaster\report.cfg';
if (qmRlRep=0) then
qmRlRep := ParserCreate('qm_report');
qmRepCfgLoad(qmRlPath, qmRlRep);
qmLog('report load '+qmRlPath+' lines='+IntToStr(ParserGetIntValueByKeyByHandle(qmRlRep, 'lines'))+' mods='+IntToStr(ParserGetIntValueByKeyByHandle(qmRlRep, 'n')));
