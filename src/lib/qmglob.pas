helpers:
requires:
---
//! Global scripts (plan S17; twin: ref/guard.py): the files the game compiles
//! as one framework before any state runs - every data\scripts\lib\*.script
//! a mod ships, and data\scripts\dmscript.global / dmscript.source. Two
//! enabled mods that ship the same one cannot both be loaded.
//!
//! qmGlobFiles: the folded names of mod `qmGfI` (ModLibraryGetData index) as
//! one `|`-joined list with a `|` at each end - `lib\<name>` for a library,
//! then `dmscript.global`, `dmscript.source`; `|` alone for none. The same
//! calls as the guard (src/guard/resource.pas): ParserGetFilesInRoot into a
//! parser of its own, and ModLibGetFileExist, which logs nothing for a
//! missing file (docs/research/guard-probes.md verdict 2).
procedure qmGlobFiles(const qmGfI : Integer; const qmGfDir : String; var qmGfOut : String);
begin
   var qmGfP : Integer = ParserSelectByKey('qm_glob_files');
   if (qmGfP=0) then
   qmGfP := ParserCreate('qm_glob_files');
   qmGfP := ParserSelectByKey('qm_glob_files');
   ParserClearByHandle(qmGfP);
   ParserGetFilesInRoot(qmGfDir+'\data\scripts\lib\*.script');
   var qmGfK : Integer;
   qmGfOut := '|';
   for qmGfK:=0 to ParserGetCountByHandle(qmGfP)-1 do
   qmGfOut := qmGfOut+'lib\'+StrToLowerCase(ParserGetValueByIndexByHandle(qmGfP, qmGfK))+'|';
   if (ModLibGetFileExist(qmGfI, 'data\scripts\dmscript.global')) then
   qmGfOut := qmGfOut+'dmscript.global|';
   if (ModLibGetFileExist(qmGfI, 'data\scripts\dmscript.source')) then
   qmGfOut := qmGfOut+'dmscript.source|';
end;

//! qmGlobFirst: the first name of list `qmGaA`, in its order, that list
//! `qmGaB` holds too, or '' (ref/guard.py conflict_pairs).
procedure qmGlobFirst(const qmGaA : String; const qmGaB : String; var qmGaOut : String);
begin
   var qmGaRest : String = SubStr(qmGaA, 2, StrLength(qmGaA)-1);
   var qmGaP : Integer;
   var qmGaF : String;
   qmGaOut := '';
   while (qmGaRest<>'') and (qmGaOut='') do
   begin
      qmGaP := StrPos('|', qmGaRest);
      if (qmGaP<2) then
      qmGaRest := ''
      else
      begin
         qmGaF := SubStr(qmGaRest, 1, qmGaP-1);
         qmGaRest := SubStr(qmGaRest, qmGaP+1, StrLength(qmGaRest)-qmGaP);
         if (StrPos('|'+qmGaF+'|', qmGaB)>0) then
         qmGaOut := qmGaF;
      end;
   end;
end;

//! qmGlobRelated: whether the mods with dirs `qmGrA` and `qmGrB` are an add-on
//! and its base - one's about.cfg `extends` names the other by a name it
//! answers to (qm_about ext<i>, nm<i>; ref/about.py _related, ref/guard.py
//! related). Such a pair is no clash (0.1.4): the start-up guard lets it start
//! together, so the boot, the window and the Apply do not call it one. False
//! when qm_about is not there or a dir is not in it. Callers ask only for a
//! pair that ships a file both ways, so the row scan stays rare.
function qmGlobRelated(const qmGrA : String; const qmGrB : String) : Boolean;
begin
   Result := False;
   var qmGrP : Integer = ParserSelectByKey('qm_about');
   if (qmGrP=0) then
   exit;
   var qmGrI : Integer = -1;
   var qmGrJ : Integer = -1;
   var qmGrK : Integer;
   for qmGrK:=0 to ParserGetIntValueByKeyByHandle(qmGrP, 'n')-1 do
   begin
      if (qmGrI<0) and SameText(ParserGetValueByKeyByHandle(qmGrP, 'dir'+IntToStr(qmGrK)), qmGrA) then
      qmGrI := qmGrK;
      if (qmGrJ<0) and SameText(ParserGetValueByKeyByHandle(qmGrP, 'dir'+IntToStr(qmGrK)), qmGrB) then
      qmGrJ := qmGrK;
   end;
   if (qmGrI<0) or (qmGrJ<0) then
   exit;
   var qmGrEa : String = ParserGetValueByKeyByHandle(qmGrP, 'ext'+IntToStr(qmGrI));
   var qmGrEb : String = ParserGetValueByKeyByHandle(qmGrP, 'ext'+IntToStr(qmGrJ));
   if (qmGrEa<>'') and (StrPos('|'+qmGrEa+'|', ParserGetValueByKeyByHandle(qmGrP, 'nm'+IntToStr(qmGrJ)))>0) then
   Result := True;
   if (qmGrEb<>'') and (StrPos('|'+qmGrEb+'|', ParserGetValueByKeyByHandle(qmGrP, 'nm'+IntToStr(qmGrI)))>0) then
   Result := True;
end;

//! qmGlobPath: a folded name as the player reads it: `lib\unit.script` is
//! scripts\lib\unit.script, `dmscript.global` scripts\dmscript.global.
procedure qmGlobPath(const qmGpF : String; var qmGpOut : String);
begin
   qmGpOut := 'scripts\'+qmGpF;
end;
