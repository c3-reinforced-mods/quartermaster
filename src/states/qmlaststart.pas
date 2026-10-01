state: qmLastStart
into: data/quartermaster/core.aix
helpers: qmlog, qmstr
requires:
---
//! What stopped the previous start, when it stopped at "Error compiling
//! scripts" (ref/laststart.py is the twin and has the rule; the evidence is
//! docs/research/context-2026-09-27.md, CompileFramework line numbers). qmBoot
//! runs it outside a multiplayer sync and adds qm_ls `line` to its block.
//!
//! The previous start's log is the second newest <save>\log\cos_*.log by
//! FileAge (the newest is this start's). Its first LOG_LINES lines are read
//! for the CompileFramework line. Only then the libraries are counted: the
//! Files list of the vanilla dmscript.source after its Code lines, each in the
//! copy the failed start's mods put in effect - <save>\quartermaster\
//! compile.prev.cfg, which the start-up guard wrote before that start
//! compiled (n, d<k>, t<k>) - the last of them that ships it, else vanilla's.
//!
//! qm_ls keys: prev (the log read), found (1: the error line is there), n,
//! col, text, and with a place lib, owner, lo, hi, olib, oown; line - the
//! Boot line, '' when there is nothing to say.
var qmLsRes : Integer = ParserSelectByKey('qm_ls');
if (qmLsRes=0) then
qmLsRes := ParserCreate('qm_ls');
ParserClearByHandle(qmLsRes);
var qmLsTbl : String = ' !"#$%&''()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz';
var qmLsSave : String = GetAppSaveDirectoryPath;
var qmLsApp : String = ExtractFilePath(GetApplicationFileName);
var qmLsFs : Integer;
var qmLsInt : Integer = 0;
var qmLsSh : Integer = 4;
var qmLsEnd : Boolean = True;
var qmLsInts : Integer = 0;
var qmLsLast : Integer = 0;
var qmLsK : Integer;
var qmLsJ : Integer;
var qmLsA1 : Integer = -1;
var qmLsA2 : Integer = -1;
var qmLsN1 : String = '';
var qmLsN2 : String = '';
var qmLsAge : Integer;
var qmLsName : String;
var qmLsL : String;
var qmLsGot : Boolean;
var qmLsCount : Integer;
var qmLsFound : Boolean = False;
var qmLsN : Integer = 0;
var qmLsCol : Integer = 0;
var qmLsText : String = '';
var qmLsP : Integer;
var qmLsQ : Integer;
var qmLsD : String;

procedure qmLsOpen(const qmLoPath : String);
begin
   qmLsFs := OpenFileRead(qmLoPath);
   qmLsSh := 4;
   qmLsEnd := False;
   qmLsInts := 0;
   qmLsLast := 0;
end;

//! The next byte, 0 at the end (the size-unknown raw read of qmAbout).
function qmLsByte() : Integer;
begin
   Result := 0;
   if (not qmLsEnd) then
   begin
      if (qmLsSh>=4) then
      begin
         qmLsInt := 0;
         ReadInteger(qmLsFs, qmLsInt);
         qmLsInts := qmLsInts+1;
         qmLsSh := 0;
         if (qmLsInts>4194304) then
         qmLsEnd := True;
      end;
      if (not qmLsEnd) then
      begin
         Result := (qmLsInt shr (qmLsSh*8)) and 255;
         qmLsSh := qmLsSh+1;
         if (Result=0) then
         qmLsEnd := True;
      end;
   end;
end;

//! The next line as an internal string (bytes outside 32..122 as ~NNN, CR
//! dropped); qmLlGot is False at the end of the file.
procedure qmLsLine(var qmLlOut : String; var qmLlGot : Boolean);
begin
   var qmLlB : Integer = qmLsByte;
   var qmLlE : String;
   qmLlOut := '';
   qmLlGot := (qmLlB<>0);
   while (qmLlB<>0) and (qmLlB<>10) do
   begin
      if (qmLlB<>13) then
      begin
         if (qmLlB>=32) and (qmLlB<=122) then
         qmLlOut := qmLlOut+SubStr(qmLsTbl, qmLlB-31, 1)
         else
         begin
            qmLlE := IntToStr(qmLlB);
            while (StrLength(qmLlE)<3) do
            qmLlE := '0'+qmLlE;
            qmLlOut := qmLlOut+'~'+qmLlE;
         end;
      end;
      qmLlB := qmLsByte;
   end;
end;

//! ref/laststart.py line_count: the LFs, and one more when the last line has none.
function qmLsCountLines(const qmLcPath : String) : Integer;
begin
   var qmLcB : Integer;
   var qmLcPrev : Integer = 0;
   Result := 0;
   qmLsOpen(qmLcPath);
   qmLcB := qmLsByte;
   while (qmLcB<>0) do
   begin
      if (qmLcB=10) then
      Result := Result+1;
      qmLcPrev := qmLcB;
      qmLcB := qmLsByte;
   end;
   CloseFile(qmLsFs);
   if (qmLcPrev<>10) then
   Result := Result+1;
end;

//! Leading and trailing spaces off.
procedure qmLsTrim(const qmLtS : String; var qmLtOut : String);
begin
   var qmLtA : Integer = 1;
   var qmLtB : Integer = StrLength(qmLtS);
   while (qmLtA<=qmLtB) and (SubStr(qmLtS, qmLtA, 1)=' ') do
   qmLtA := qmLtA+1;
   while (qmLtB>=qmLtA) and (SubStr(qmLtS, qmLtB, 1)=' ') do
   qmLtB := qmLtB-1;
   qmLtOut := '';
   if (qmLtB>=qmLtA) then
   qmLtOut := SubStr(qmLtS, qmLtA, qmLtB-qmLtA+1);
end;

//! The number that starts at qmLdAt of qmLdS, -1 when none; qmLdEnd after it.
procedure qmLsDigits(const qmLdS : String; const qmLdAt : Integer; var qmLdN : Integer; var qmLdEnd : Integer);
begin
   var qmLdC : Integer = 0;
   qmLdN := -1;
   qmLdEnd := qmLdAt;
   if (qmLdEnd<=StrLength(qmLdS)) then
   qmLdC := Ord(SubStr(qmLdS, qmLdEnd, 1));
   while (qmLdEnd<=StrLength(qmLdS)) and (qmLdC>=48) and (qmLdC<=57) do
   begin
      if (qmLdN<0) then
      qmLdN := 0;
      qmLdN := qmLdN*10+qmLdC-48;
      qmLdEnd := qmLdEnd+1;
      qmLdC := 0;
      if (qmLdEnd<=StrLength(qmLdS)) then
      qmLdC := Ord(SubStr(qmLdS, qmLdEnd, 1));
   end;
end;

//! The previous start's log.
var qmLsFp : Integer = ParserSelectByKey('qm_ls_files');
if (qmLsFp=0) then
begin
   ParserCreate('qm_ls_files');
   qmLsFp := ParserSelectByKey('qm_ls_files');
end;
ParserClearByHandle(qmLsFp);
ParserGetFilesInRoot(qmLsSave+'log\cos_*.log');
for qmLsK:=0 to ParserGetCountByHandle(qmLsFp)-1 do
begin
   qmLsName := ParserGetValueByIndexByHandle(qmLsFp, qmLsK);
   qmLsAge := FileAge(qmLsSave+'log\'+qmLsName);
   if (qmLsAge>qmLsA1) then
   begin
      qmLsA2 := qmLsA1;
      qmLsN2 := qmLsN1;
      qmLsA1 := qmLsAge;
      qmLsN1 := qmLsName;
   end
   else
   if (qmLsAge>qmLsA2) then
   begin
      qmLsA2 := qmLsAge;
      qmLsN2 := qmLsName;
   end;
end;
ParserSetValueByKeyByHandle(qmLsRes, 'prev', qmLsN2);
ParserSetValueByKeyByHandle(qmLsRes, 'found', '0');
ParserSetValueByKeyByHandle(qmLsRes, 'line', '');
if (qmLsN2<>'') then
begin
   qmLsOpen(qmLsSave+'log\'+qmLsN2);
   qmLsCount := 0;
   qmLsGot := True;
   while (qmLsGot) and (not qmLsFound) and (qmLsCount<400) do
   begin
      qmLsLine(qmLsL, qmLsGot);
      qmLsCount := qmLsCount+1;
      qmLsP := StrPos('CompileFramework() - compile global script error: ', qmLsL);
      if (qmLsP>0) then
      begin
         qmLsD := SubStr(qmLsL, qmLsP+50, StrLength(qmLsL));
         qmLsP := StrPos('Line: ', qmLsD);
         qmLsQ := StrPos('Column: ', qmLsD);
         if (qmLsP>0) and (qmLsQ>0) then
         begin
            qmLsDigits(qmLsD, qmLsP+6, qmLsN, qmLsJ);
            qmLsDigits(qmLsD, qmLsQ+8, qmLsCol, qmLsJ);
            if (qmLsN>=0) and (qmLsCol>=0) then
            begin
               qmLsFound := True;
               qmLsText := SubStr(qmLsD, qmLsJ, StrLength(qmLsD));
               if (SubStr(qmLsText, 1, 2)=': ') then
               qmLsText := SubStr(qmLsText, 3, StrLength(qmLsText));
               qmLsTrim(qmLsText, qmLsD);
               qmLsText := qmLsD;
            end;
         end;
      end;
   end;
   CloseFile(qmLsFs);
end;
if (qmLsFound) then
begin
   ParserSetValueByKeyByHandle(qmLsRes, 'found', '1');
   ParserSetIntValueByKeyByHandle(qmLsRes, 'n', qmLsN);
   ParserSetIntValueByKeyByHandle(qmLsRes, 'col', qmLsCol);
   ParserSetValueByKeyByHandle(qmLsRes, 'text', qmLsText);
   //! The failed start's mods.
   var qmLsOrd : Integer = ParserSelectByKey('qm_ls_order');
   if (qmLsOrd=0) then
   qmLsOrd := ParserCreate('qm_ls_order');
   ParserClearByHandle(qmLsOrd);
   var qmLsHave : Boolean = False;
   if (FileAge(qmLsSave+'quartermaster\compile.prev.cfg')<>-1) then
   qmLsHave := ParserLoadFromFileByHandle(qmLsOrd, qmLsSave+'quartermaster\compile.prev.cfg');
   var qmLsOn : Integer = 0;
   if (qmLsHave) then
   qmLsOn := ParserGetIntValueByKeyByHandle(qmLsOrd, 'n');
   //! The vanilla dmscript.source: its Code lines, its Files.
   var qmLsCode : Integer = 0;
   var qmLsLibs : Integer = 0;
   var qmLsWhere : Integer = 0;
   qmLsOpen(qmLsApp+'data\scripts\dmscript.source');
   qmLsGot := True;
   while (qmLsGot) do
   begin
      qmLsLine(qmLsL, qmLsGot);
      qmLsTrim(qmLsL, qmLsD);
      if (SubStr(qmLsD, 1, 19)='Code : struct.begin') then
      qmLsWhere := 1
      else
      if (SubStr(qmLsD, 1, 20)='Files : struct.begin') then
      qmLsWhere := 2
      else
      if (qmLsD='struct.end') then
      qmLsWhere := 0
      else
      if (qmLsWhere=1) and (SubStr(qmLsD, 1, 5)='[*] =') then
      qmLsCode := qmLsCode+1
      else
      if (qmLsWhere=2) and (SubStr(qmLsD, 1, 5)='[*] =') and (StrPos('\', qmLsD)>0) then
      begin
         while (StrPos('\', qmLsD)>0) do
         qmLsD := SubStr(qmLsD, StrPos('\', qmLsD)+1, StrLength(qmLsD));
         ParserSetValueByKeyByHandle(qmLsRes, 'f'+IntToStr(qmLsLibs), qmLsD);
         qmLsLibs := qmLsLibs+1;
      end;
   end;
   CloseFile(qmLsFs);
   //! Where framework line n falls, and n less DRIFT (15).
   if (qmLsHave) and (qmLsLibs>0) then
   begin
      var qmLsAt : Integer = qmLsCode+1;
      var qmLsLines : Integer;
      var qmLsOwner : String;
      var qmLsPath : String;
      var qmLsStart : Integer;
      var qmLsHit : String = '';
      var qmLsHitOwner : String = '';
      var qmLsHitStart : Integer = 0;
      var qmLsLow : String = '';
      var qmLsLowOwner : String = '';
      for qmLsK:=0 to qmLsLibs-1 do
      begin
         qmLsName := ParserGetValueByKeyByHandle(qmLsRes, 'f'+IntToStr(qmLsK));
         qmLsOwner := 'the game itself';
         qmLsPath := qmLsApp+'data\scripts\lib\'+qmLsName;
         for qmLsJ:=0 to qmLsOn-1 do
         if (FileAge(qmLsApp+ParserGetValueByKeyByHandle(qmLsOrd, 'd'+IntToStr(qmLsJ))+'\data\scripts\lib\'+qmLsName)<>-1) then
         begin
            qmLsOwner := ParserGetValueByKeyByHandle(qmLsOrd, 't'+IntToStr(qmLsJ));
            qmLsPath := qmLsApp+ParserGetValueByKeyByHandle(qmLsOrd, 'd'+IntToStr(qmLsJ))+'\data\scripts\lib\'+qmLsName;
         end;
         qmLsLines := qmLsCountLines(qmLsPath);
         qmLsStart := qmLsAt+1;
         if (qmLsHit='') and (qmLsN>=qmLsStart) and (qmLsN<=qmLsAt+qmLsLines+1) then
         begin
            qmLsHit := qmLsName;
            qmLsHitOwner := qmLsOwner;
            qmLsHitStart := qmLsStart;
         end;
         if (qmLsLow='') and (qmLsN-15>=qmLsStart) and (qmLsN-15<=qmLsAt+qmLsLines+1) then
         begin
            qmLsLow := qmLsName;
            qmLsLowOwner := qmLsOwner;
         end;
         qmLsAt := qmLsAt+qmLsLines+1;
      end;
      if (qmLsHit<>'') then
      begin
         var qmLsHi : Integer = qmLsN-qmLsHitStart+1;
         var qmLsLo : Integer = qmLsHi-15;
         if (qmLsLo<1) then
         qmLsLo := 1;
         ParserSetValueByKeyByHandle(qmLsRes, 'lib', qmLsHit);
         ParserSetValueByKeyByHandle(qmLsRes, 'owner', qmLsHitOwner);
         ParserSetIntValueByKeyByHandle(qmLsRes, 'lo', qmLsLo);
         ParserSetIntValueByKeyByHandle(qmLsRes, 'hi', qmLsHi);
         qmLsD := 'The last start stopped at "Error compiling scripts" ('+qmLsText+'): most likely scripts\lib\'+qmLsHit+' of '+qmLsHitOwner+', lines '+IntToStr(qmLsLo)+'-'+IntToStr(qmLsHi);
         if (qmLsLow<>'') and (qmLsLow<>qmLsHit) then
         begin
            ParserSetValueByKeyByHandle(qmLsRes, 'olib', qmLsLow);
            ParserSetValueByKeyByHandle(qmLsRes, 'oown', qmLsLowOwner);
            qmLsD := qmLsD+', or the end of scripts\lib\'+qmLsLow+' of '+qmLsLowOwner;
         end;
         ParserSetValueByKeyByHandle(qmLsRes, 'line', qmLsD+'.');
      end;
   end;
   if (ParserGetValueByKeyByHandle(qmLsRes, 'line')='') then
   ParserSetValueByKeyByHandle(qmLsRes, 'line', 'The last start stopped at "Error compiling scripts" ('+qmLsText+'); where in the global scripts is not known.');
   qmLog('last start: '+qmLsN2+' stopped at framework line '+IntToStr(qmLsN)+' column '+IntToStr(qmLsCol)+': '+ParserGetValueByKeyByHandle(qmLsRes, 'line'));
end;
