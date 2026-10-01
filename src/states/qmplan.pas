state: qmPlan
into: data/quartermaster/core.aix
helpers: qmlog
requires: sizecap, phasebdata, additiveglobal
---
//! The planner (plan G6; twin: ref/planner.py, which has the rules and their
//! reasons in the same order). Phase B: a data file with a record profile is
//! merged by records (merge-data, qmDataMerge); dmscript.global stays the
//! winner's - a global script (plan S17) never loads twice, so there is no
//! second copy to add into it.
//!
//! For every scanned path with a provider: the strategy (what happens when two
//! or more mods ship the path), then the action - skip when one mod alone
//! ships it and it is not Quartermaster's hook file, else the strategy. The
//! winner is the last provider in canonical order.
//!
//! qm_plan keys: n, then per decision m: path<m> act<m> str<m> why<m> win<m>
//! prov<m> (positions as in qm_index), and a count per action.
var qmPlIdx : Integer = ParserSelectByKey('qm_index');
var qmPlMods : Integer = ParserSelectByKey('qm_mods');
var qmPlPlan : Integer = ParserSelectByKey('qm_plan');
if (qmPlPlan=0) then
qmPlPlan := ParserCreate('qm_plan');
ParserClearByHandle(qmPlPlan);
var qmPlN : Integer = ParserGetIntValueByKeyByHandle(qmPlIdx, 'n');
var qmPlSelf : Integer = ParserGetIntValueByKeyByHandle(qmPlMods, 'self');
var qmPlSelfPos : String = '';
if (qmPlSelf>=0) then
qmPlSelfPos := IntToStr(ParserGetIntValueByKeyByHandle(qmPlMods, 'pos'+IntToStr(qmPlSelf)));
var qmPlM : Integer = 0;
var qmPlK : Integer;
var qmPlProv : String;
var qmPlPath : String;
var qmPlCls : String;
var qmPlLines : Integer;
var qmPlCnt : Integer;
var qmPlLast : String;
var qmPlStr : String;
var qmPlWhy : String;
var qmPlAct : String;
var qmPlHook : Integer = 0;
var qmPlMerge : Integer = 0;
var qmPlWin : Integer = 0;
var qmPlSkip : Integer = 0;
for qmPlK:=0 to qmPlN-1 do
begin
   qmPlProv := ParserGetValueByKeyByHandle(qmPlIdx, 'v'+IntToStr(qmPlK));
   if (qmPlProv<>'-') then
   begin
      qmPlPath := ParserGetValueByKeyByHandle(qmPlIdx, 'p'+IntToStr(qmPlK));
      qmPlCls := ParserGetValueByKeyByHandle(qmPlIdx, 'c'+IntToStr(qmPlK));
      qmPlLines := StrToInt(ParserGetValueByKeyByHandle(qmPlIdx, 'l'+IntToStr(qmPlK)));
      //! Count the providers; what is left after the last `;` is the winner.
      qmPlCnt := 1;
      qmPlLast := qmPlProv;
      while (StrPos(';', qmPlLast)>0) do
      begin
         qmPlLast := SubStr(qmPlLast, StrPos(';', qmPlLast)+1, StrLength(qmPlLast));
         qmPlCnt := qmPlCnt+1;
      end;
      if (qmPlSelfPos<>'') and (qmPlLast=qmPlSelfPos) then
      begin
         qmPlStr := 'hook';
         qmPlWhy := 'quartermaster-hook';
      end
      else
      if (qmPlLines>${sizecap}) then
      begin
         qmPlStr := 'winner';
         qmPlWhy := 'over-size-cap';
      end
      else
      if (qmPlCls='merge') then
      begin
         qmPlStr := 'merge-inc';
         qmPlWhy := 'merge-allow-list';
      end
      else
      if (StrPos('|'+qmPlPath+'|', ${phasebdata})>0) then
      begin
         qmPlStr := 'merge-data';
         qmPlWhy := 'record-profile';
      end
      else
      if (qmPlPath=${additiveglobal}) then
      begin
         qmPlStr := 'winner';
         qmPlWhy := 'global-script';
      end
      else
      if (qmPlLines<0) then
      begin
         qmPlStr := 'winner';
         qmPlWhy := 'binary';
      end
      else
      if (qmPlCls='never') then
      begin
         qmPlStr := 'winner';
         qmPlWhy := 'never-generate';
      end
      else
      if (qmPlCls='wta') then
      begin
         qmPlStr := 'winner';
         qmPlWhy := 'not-on-allow-list';
      end
      else
      begin
         qmPlStr := 'winner';
         qmPlWhy := 'unknown-class';
      end;
      if (qmPlStr='hook') or (qmPlCnt>1) then
      qmPlAct := qmPlStr
      else
      qmPlAct := 'skip';
      if (qmPlAct='hook') then
      qmPlHook := qmPlHook+1;
      if (qmPlAct='merge-inc') or (qmPlAct='merge-data') then
      qmPlMerge := qmPlMerge+1;
      if (qmPlAct='winner') then
      qmPlWin := qmPlWin+1;
      if (qmPlAct='skip') then
      qmPlSkip := qmPlSkip+1;
      ParserSetValueByKeyByHandle(qmPlPlan, 'path'+IntToStr(qmPlM), qmPlPath);
      ParserSetValueByKeyByHandle(qmPlPlan, 'act'+IntToStr(qmPlM), qmPlAct);
      ParserSetValueByKeyByHandle(qmPlPlan, 'str'+IntToStr(qmPlM), qmPlStr);
      ParserSetValueByKeyByHandle(qmPlPlan, 'why'+IntToStr(qmPlM), qmPlWhy);
      ParserSetValueByKeyByHandle(qmPlPlan, 'win'+IntToStr(qmPlM), qmPlLast);
      ParserSetValueByKeyByHandle(qmPlPlan, 'prov'+IntToStr(qmPlM), qmPlProv);
      qmLog('plan '+qmPlPath+' '+qmPlAct+' ('+qmPlStr+', '+qmPlWhy+') winner='+qmPlLast+' providers='+qmPlProv);
      qmPlM := qmPlM+1;
   end;
end;
ParserSetIntValueByKeyByHandle(qmPlPlan, 'n', qmPlM);
ParserSetIntValueByKeyByHandle(qmPlPlan, 'hook', qmPlHook);
ParserSetIntValueByKeyByHandle(qmPlPlan, 'mergeinc', qmPlMerge);
ParserSetIntValueByKeyByHandle(qmPlPlan, 'winner', qmPlWin);
ParserSetIntValueByKeyByHandle(qmPlPlan, 'skip', qmPlSkip);
qmLog('plan decisions='+IntToStr(qmPlM)+' hook='+IntToStr(qmPlHook)+' merge-inc='+IntToStr(qmPlMerge)+' winner='+IntToStr(qmPlWin)+' skip='+IntToStr(qmPlSkip));
