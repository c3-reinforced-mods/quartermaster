helpers:
requires:
---
//! report.cfg: the named parser qm_report (docs/ui.md keys) saved and read
//! back by the engine's own parser, so a mod folder's name keeps every byte
//! (ref/report.py report_cfg and read_report_cfg are the twin and own the
//! format). qmReport saves it, qmReportLoad reads it for a boot that does not
//! generate, and the SelfTest (qmCaseM4, row rload) checks the round trip.
//!
//! The engine's parser drops the spaces a value starts with when it loads
//! the file. In run m4a exactly the 34 values of 72 that began with a space
//! read back different, and every other value, inner spaces included, read
//! back equal. M2 had already shown that it drops the spaces a Code value ends
//! with. Every detail line of the report starts with two spaces, so each text
//! value (l<k>, dir<j>, st<j>, why<j>, c<j>_<k>, m<k>) is saved behind a `;`. That is the one
//! first character proven to keep the spaces after it through the parser:
//! every .inc Code value is `;` plus the line, indentation included (M2). The
//! load takes the `;` off. The numbers (lines, n, cn<j>, mlines) are saved as
//! they are. No report text ends with a space: every line ends with a word, a tag
//! or a mod folder's name, and Windows does not end a folder's name with one.
//!
//! qmRepCfgSave  qm_report (handle qmRkRep) into the file qmRkPath, through
//!               the scratch parser qm_report_cfg
//! qmRepCfgLoad  the file qmRjPath into the parser qmRjTo, emptied first; it
//!               stays empty when there is no file. A text value without the
//!               `;` (a report.cfg saved before the guard) is taken as it is:
//!               the next generation saves it again
procedure qmRepCfgGuard(const qmRqFrom : Integer; const qmRqTo : Integer; const qmRqKey : String);
begin
   ParserSetValueByKeyByHandle(qmRqTo, qmRqKey, ';'+ParserGetValueByKeyByHandle(qmRqFrom, qmRqKey));
end;

procedure qmRepCfgUnguard(const qmRuFrom : Integer; const qmRuTo : Integer; const qmRuKey : String);
begin
   var qmRuV : String = ParserGetValueByKeyByHandle(qmRuFrom, qmRuKey);
   if (SubStr(qmRuV, 1, 1)=';') then
   begin
      if (StrLength(qmRuV)=1) then
      qmRuV := ''
      else
      qmRuV := SubStr(qmRuV, 2, StrLength(qmRuV)-1);
   end;
   ParserSetValueByKeyByHandle(qmRuTo, qmRuKey, qmRuV);
end;

procedure qmRepCfgSave(const qmRkRep : Integer; const qmRkPath : String);
begin
   var qmRkF : Integer = ParserSelectByKey('qm_report_cfg');
   var qmRkJ : Integer;
   var qmRkK : Integer;
   var qmRkS : String;
   if (qmRkF=0) then
   qmRkF := ParserCreate('qm_report_cfg');
   ParserClearByHandle(qmRkF);
   ParserSetIntValueByKeyByHandle(qmRkF, 'lines', ParserGetIntValueByKeyByHandle(qmRkRep, 'lines'));
   for qmRkK:=0 to ParserGetIntValueByKeyByHandle(qmRkRep, 'lines')-1 do
   qmRepCfgGuard(qmRkRep, qmRkF, 'l'+IntToStr(qmRkK));
   ParserSetIntValueByKeyByHandle(qmRkF, 'n', ParserGetIntValueByKeyByHandle(qmRkRep, 'n'));
   for qmRkJ:=0 to ParserGetIntValueByKeyByHandle(qmRkRep, 'n')-1 do
   begin
      qmRkS := IntToStr(qmRkJ);
      qmRepCfgGuard(qmRkRep, qmRkF, 'dir'+qmRkS);
      qmRepCfgGuard(qmRkRep, qmRkF, 'st'+qmRkS);
      qmRepCfgGuard(qmRkRep, qmRkF, 'why'+qmRkS);
      ParserSetIntValueByKeyByHandle(qmRkF, 'cn'+qmRkS, ParserGetIntValueByKeyByHandle(qmRkRep, 'cn'+qmRkS));
      for qmRkK:=0 to ParserGetIntValueByKeyByHandle(qmRkRep, 'cn'+qmRkS)-1 do
      qmRepCfgGuard(qmRkRep, qmRkF, 'c'+qmRkS+'_'+IntToStr(qmRkK));
      qmRepCfgGuard(qmRkRep, qmRkF, 'cpd'+qmRkS);
   end;
   ParserSetIntValueByKeyByHandle(qmRkF, 'mlines', ParserGetIntValueByKeyByHandle(qmRkRep, 'mlines'));
   for qmRkK:=0 to ParserGetIntValueByKeyByHandle(qmRkRep, 'mlines')-1 do
   qmRepCfgGuard(qmRkRep, qmRkF, 'm'+IntToStr(qmRkK));
   ParserSaveToFileByHandle(qmRkF, qmRkPath);
end;

procedure qmRepCfgLoad(const qmRjPath : String; const qmRjTo : Integer);
begin
   var qmRjF : Integer = ParserSelectByKey('qm_report_cfg');
   var qmRjJ : Integer;
   var qmRjK : Integer;
   var qmRjS : String;
   if (qmRjF=0) then
   qmRjF := ParserCreate('qm_report_cfg');
   ParserClearByHandle(qmRjF);
   ParserClearByHandle(qmRjTo);
   if (FileAge(qmRjPath)<>-1) then
   begin
      ParserLoadFromFileByHandle(qmRjF, qmRjPath);
      ParserSetIntValueByKeyByHandle(qmRjTo, 'lines', ParserGetIntValueByKeyByHandle(qmRjF, 'lines'));
      for qmRjK:=0 to ParserGetIntValueByKeyByHandle(qmRjF, 'lines')-1 do
      qmRepCfgUnguard(qmRjF, qmRjTo, 'l'+IntToStr(qmRjK));
      ParserSetIntValueByKeyByHandle(qmRjTo, 'n', ParserGetIntValueByKeyByHandle(qmRjF, 'n'));
      for qmRjJ:=0 to ParserGetIntValueByKeyByHandle(qmRjF, 'n')-1 do
      begin
         qmRjS := IntToStr(qmRjJ);
         qmRepCfgUnguard(qmRjF, qmRjTo, 'dir'+qmRjS);
         qmRepCfgUnguard(qmRjF, qmRjTo, 'st'+qmRjS);
         qmRepCfgUnguard(qmRjF, qmRjTo, 'why'+qmRjS);
         ParserSetIntValueByKeyByHandle(qmRjTo, 'cn'+qmRjS, ParserGetIntValueByKeyByHandle(qmRjF, 'cn'+qmRjS));
         for qmRjK:=0 to ParserGetIntValueByKeyByHandle(qmRjF, 'cn'+qmRjS)-1 do
         qmRepCfgUnguard(qmRjF, qmRjTo, 'c'+qmRjS+'_'+IntToStr(qmRjK));
         qmRepCfgUnguard(qmRjF, qmRjTo, 'cpd'+qmRjS);
      end;
      ParserSetIntValueByKeyByHandle(qmRjTo, 'mlines', ParserGetIntValueByKeyByHandle(qmRjF, 'mlines'));
      for qmRjK:=0 to ParserGetIntValueByKeyByHandle(qmRjF, 'mlines')-1 do
      qmRepCfgUnguard(qmRjF, qmRjTo, 'm'+IntToStr(qmRjK));
   end;
end;
