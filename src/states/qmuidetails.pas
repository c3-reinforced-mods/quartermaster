state: qmUiDetails
into: data/quartermaster/core.aix
helpers: qmlog
requires:
---
//! The Details line of the selected row: one line per mod, whether it loads
//! without problems or why not, in qm_ui d0 (dn = 1; ShowQmManager draws it).
//! The hands-on check found the file list and the classification too much
//! for this panel; the Report view (qm_report m<k>) has them, grouped by mod.
//!
//! The line is `<name> - <status>: <why>`, and says what Apply will do to the
//! row when that differs from what the game loaded. The status and why<i>
//! are qmUiModel's (docs/ui.md): the record's status and short sentence from
//! qm_report, OK from the index for a mod that ships none of the merged
//! files, `?` without either, `-` for a mod the game did not load.
//!
//! The texts are final since 2026-09-30.
var qmUdUi : Integer = ParserSelectByKey('qm_ui');
var qmUdLine : String;

//! One more sentence: the status sentences carry no full stop of their own,
//! so the line gets one first when it has none (run look-wsX read
//! `Deactivate one of them It clashes with ...`).
procedure qmUdAdd(const qmQuS : String);
begin
   if (SubStr(qmUdLine, StrLength(qmUdLine), 1)<>'.') then
   qmUdLine := qmUdLine+'.';
   qmUdLine := qmUdLine+' '+qmQuS;
end;

if (qmUdUi=0) then
exit;
var qmUdSel : Integer = ParserGetIntValueByKeyByHandle(qmUdUi, 'sel');
var qmUdS : String = IntToStr(qmUdSel);
var qmUdSt : String = ParserGetValueByKeyByHandle(qmUdUi, 'st'+qmUdS);
var qmUdSrc : String = ParserGetValueByKeyByHandle(qmUdUi, 'stsrc'+qmUdS);
var qmUdEn : Integer = ParserGetIntValueByKeyByHandle(qmUdUi, 'en'+qmUdS);
var qmUdPe : Integer = ParserGetIntValueByKeyByHandle(qmUdUi, 'pe'+qmUdS);
// The hint shown while nothing is selected, and the wording of
// the Details line.
if (qmUdSel<0) or (qmUdSel>=ParserGetIntValueByKeyByHandle(qmUdUi, 'n')) then
qmUdLine := 'Select a mod to see how it loads.'
else
begin
   qmUdLine := ParserGetValueByKeyByHandle(qmUdUi, 'name'+qmUdS)+' - ';
   if (qmUdEn=0) and (ParserGetValueByKeyByHandle(qmUdUi, 'why'+qmUdS)<>'') then
   qmUdLine := qmUdLine+'inactive: '+ParserGetValueByKeyByHandle(qmUdUi, 'why'+qmUdS)
   else
   if (qmUdEn=0) then
   qmUdLine := qmUdLine+'inactive'
   else
   if (qmUdSrc='globals') then
   qmUdLine := qmUdLine+'FAIL: '+ParserGetValueByKeyByHandle(qmUdUi, 'why'+qmUdS)
   else
   if (qmUdSrc='about') then
   qmUdLine := qmUdLine+qmUdSt+': '+ParserGetValueByKeyByHandle(qmUdUi, 'why'+qmUdS)
   else
   if (qmUdSrc='report') and (qmUdSt='NEW') then
   qmUdLine := qmUdLine+'NEW: a new mod; '+ParserGetValueByKeyByHandle(qmUdUi, 'why'+qmUdS)
   else
   if (qmUdSrc='report') then
   qmUdLine := qmUdLine+qmUdSt+': '+ParserGetValueByKeyByHandle(qmUdUi, 'why'+qmUdS)
   else
   if (qmUdSrc='index') then
   qmUdLine := qmUdLine+'OK: loads as it is: it ships none of the files Quartermaster merges'
   else
   qmUdLine := qmUdLine+'?: no report for this mod yet; the next start with it generates one';
   if (qmUdSel=ParserGetIntValueByKeyByHandle(qmUdUi, 'self')) then
   qmUdLine := qmUdLine+' (Quartermaster itself)';
   if (qmUdPe>qmUdEn) then
   qmUdAdd('Apply activates it.');
   if (qmUdPe<qmUdEn) then
   qmUdAdd('Apply deactivates it.');
   // What the conflict report says of it (qmUiModel cpd<i>, qmConflicts):
   // the file it is left out of, or whom it loses or wins conflicts against.
   if (qmUdEn=1) and (ParserGetValueByKeyByHandle(qmUdUi, 'cpd'+qmUdS)<>'') then
   qmUdAdd(ParserGetValueByKeyByHandle(qmUdUi, 'cpd'+qmUdS)+'.');
   // The pending set's clash for this row (qmUiAct pcl<i>): Apply refuses it.
   if (ParserGetValueByKeyByHandle(qmUdUi, 'pcl'+qmUdS)<>'') then
   qmUdAdd(ParserGetValueByKeyByHandle(qmUdUi, 'pcl'+qmUdS));
   // The pending set's first about.cfg problem of this row (qmUiAct pal<i>),
   // unless the status already says it.
   if (ParserGetValueByKeyByHandle(qmUdUi, 'pal'+qmUdS)<>'') and (ParserGetValueByKeyByHandle(qmUdUi, 'pal'+qmUdS)<>qmUdSt+': '+ParserGetValueByKeyByHandle(qmUdUi, 'why'+qmUdS)+'.') then
   qmUdAdd('Pending: '+ParserGetValueByKeyByHandle(qmUdUi, 'pal'+qmUdS));
   // Settings the mod declares (M10): the Options button opens them.
   if (ParserGetIntValueByKeyByHandle(qmUdUi, 'abs'+qmUdS)>0) then
   qmUdAdd('It has '+IntToStr(ParserGetIntValueByKeyByHandle(qmUdUi, 'abs'+qmUdS))+' setting(s): Options.');
end;
ParserSetValueByKeyByHandle(qmUdUi, 'd0', qmUdLine);
ParserSetIntValueByKeyByHandle(qmUdUi, 'dn', 1);
qmLog('ui details row='+qmUdS+' status='+qmUdSt+' from='+qmUdSrc+' pending='+IntToStr(qmUdPe)+' engine='+IntToStr(qmUdEn));
