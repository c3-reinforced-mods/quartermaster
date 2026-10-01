helpers: qmstr
requires:
---
//! Texts both reports write: report.txt and the window's report (qmReport)
//! and conflicts.txt (qmConflicts), so a mod, a range and a reason read the
//! same in each (ref/report.py _who, rng, WINNER_WHY).
//!
//! qmWho        the mod at load position qmWhPos (text) of qm_mods (handle
//!              qmWhMods): `<k>. <title> (<Workshop number or dir>)`, or
//!              `<k>. <dir>` without a title; `<k>` is qmWhRank, its place on
//!              the window's Active list, and 0 gives no number
//! qmRange      a hunk's vanilla range [start, end) as text, numbered from
//!              the file's first Code line
//! qmWinnerWhy  why the planner let one copy win, in words

procedure qmWho(const qmWhPos : String; const qmWhMods : Integer; const qmWhRank : Integer; var qmWhOut : String);
begin
   var qmWhI : Integer = ParserGetIntValueByKeyByHandle(qmWhMods, 'ord'+qmWhPos);
   var qmWhD : String = ParserGetValueByKeyByHandle(qmWhMods, 'dir'+IntToStr(qmWhI));
   var qmWhT : String = ParserGetValueByKeyByHandle(qmWhMods, 'tit'+IntToStr(qmWhI));
   var qmWhW : String = '..\..\workshop\content\333420\';
   var qmWhN : String = '';
   var qmWhL : String = '';
   if (qmWhRank>0) then
   qmWhN := IntToStr(qmWhRank)+'. ';
   qmWhOut := qmWhN+qmWhD;
   if (qmWhT<>'') then
   begin
      if (StrLength(qmWhD)>StrLength(qmWhW)) then
      qmLowerAscii(SubStr(qmWhD, 1, StrLength(qmWhW)), qmWhL);
      if (qmWhL=qmWhW) then
      qmWhD := SubStr(qmWhD, StrLength(qmWhW)+1, StrLength(qmWhD)-StrLength(qmWhW));
      qmWhOut := qmWhN+qmWhT+' ('+qmWhD+')';
   end;
end;

procedure qmRange(const qmRgStart : Integer; const qmRgEnd : Integer; const qmRgFirst : Integer; const qmRgN : Integer; var qmRgOut : String);
begin
   if (qmRgEnd>qmRgStart+1) then
   qmRgOut := 'vanilla lines '+IntToStr(qmRgFirst+qmRgStart)+'-'+IntToStr(qmRgFirst+qmRgEnd-1)
   else
   if (qmRgEnd=qmRgStart+1) then
   qmRgOut := 'vanilla line '+IntToStr(qmRgFirst+qmRgStart)
   else
   if (qmRgStart<qmRgN) then
   qmRgOut := 'before vanilla line '+IntToStr(qmRgFirst+qmRgStart)
   else
   qmRgOut := 'after the last vanilla line';
end;

procedure qmWinnerWhy(const qmWyWhy : String; var qmWyOut : String);
begin
   qmWyOut := qmWyWhy;
   if (qmWyWhy='over-size-cap') then
   qmWyOut := 'the file has more lines than Quartermaster merges';
   if (qmWyWhy='never-generate') then
   qmWyOut := 'Quartermaster never generates this file';
   if (qmWyWhy='not-on-allow-list') then
   qmWyOut := 'this kind of file is not merged';
   if (qmWyWhy='record-profile-phase-b') then
   qmWyOut := 'data files are not merged yet';
   if (qmWyWhy='additive-global-phase-b') then
   qmWyOut := 'dmscript.global is not merged yet';
   if (qmWyWhy='global-script') then
   qmWyOut := 'a global script: only one copy loads';
   if (qmWyWhy='binary') then
   qmWyOut := 'a binary file';
   if (qmWyWhy='unknown-class') then
   qmWyOut := 'an unknown kind of file';
end;
