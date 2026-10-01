state: qmDataMerge
into: data/quartermaster/core.aix
helpers: qmlog, qmstr, qmraw, qmhash, qmunesc
requires: rawcap
---
//! The data merge (plan S3, S10; G7 splitter, G10 merger): every merge-data
//! job qmGenerate lists in qm_dm_in, record by record, fail-closed. The rules,
//! the layout and the evidence are in the twin, ref/records.py (merge, check,
//! limits_from_global), line for line: the same records, decisions, report
//! lines and checks, on the raw reader's internal strings.
//!
//! A file is read one at a time into the pool (objcustom.cfg is 51,586 lines;
//! the pool holds rawcap+1): a first pass splits every input into records and
//! keeps only an index - key, a hash of the record's compared lines, where
//! its lines are, its array counts - then the decisions are made on the
//! index, and a second pass copies the chosen records from each file into
//! the output pool. Two records are the same when the hashes of their
//! lines as compared (tabs as spaces, no trailing space) are the same.
//!
//! The bounds (ref/records.py check): the dmscript.global in effect - the
//! last enabled mod that ships one (qm_index), else vanilla's - gives the
//! constants; a bound is the larger of its constant and what an input file
//! already has. A job that fails a check, or whose candidate the engine's
//! parser does not load, stages nothing: the winner's file stays in effect.
//! A candidate that passes has its token in qm_val d<seq> - the writer's gate
//! for data (qmWrDataOut) - and is staged at `out`.
//!
//!   qm_dm_in  jobs; per job j: j<j>path (vanilla.idx spelling), j<j>base,
//!             j<j>parts, j<j>p<i>, j<j>n<i> (the mods' titles), j<j>out
//!   qm_dm     per job j: j<j>done, j<j>st (OK, WARN, FAIL), j<j>err (the
//!             first FAIL), j<j>seq, j<j>tok, j<j>lines, j<j>bytes, j<j>nl
//!             and j<j>t<k> / j<j>x<k> the report lines (tag, text)
var qmDmIn : Integer = ParserSelectByKey('qm_dm_in');
var qmDmOut : Integer = ParserSelectByKey('qm_dm');
if (qmDmOut=0) then
qmDmOut := ParserCreate('qm_dm');
ParserClearByHandle(qmDmOut);
if (qmDmIn=0) then
exit;
var qmDmA : array [0..${rawcap}] of String;
var qmDmB : array [0..${rawcap}] of String;
//! The record index of every input of the job: file f's records are
//! rFirst[f] .. rFirst[f]+rCount[f]-1.
var qmDmRk : array [0..8191] of String;
var qmDmRh : array [0..8191] of String;
var qmDmRs : array [0..8191] of Integer;
var qmDmRp : array [0..8191] of Integer;
var qmDmRn : array [0..8191] of Integer;
var qmDmRc0 : array [0..8191] of Integer;
var qmDmRc1 : array [0..8191] of Integer;
var qmDmRc2 : array [0..8191] of Integer;
var qmDmRb : array [0..8191] of Integer;
var qmDmRv : array [0..8191] of String;
var qmDmFFirst : array [0..16] of Integer;
var qmDmFCount : array [0..16] of Integer;
var qmDmFOk : array [0..16] of Integer;
var qmDmFPath : array [0..16] of String;
var qmDmFName : array [0..16] of String;
var qmDmHeadN : Integer = 0;
var qmDmTrailS : Integer = 0;
var qmDmTrailN : Integer = 0;
var qmDmBaseBal : Integer = 0;
var qmDmNr : Integer = 0;
//! The output: records as (file, record index) in order.
var qmDmOf : array [0..4095] of Integer;
var qmDmOr : array [0..4095] of Integer;
var qmDmOn : Integer = 0;
var qmDmOat : array [0..4095] of Integer;
//! The job's profile (ref/records.py PROFILES).
var qmDmKey : String = '';
var qmDmArr : array [0..2] of String;
var qmDmArrC : array [0..2] of String;
var qmDmArrV : array [0..2] of Integer;
var qmDmArrN : Integer = 0;
var qmDmMaxC : String = '';
var qmDmMaxV : Integer = 0;
var qmDmRangeC : String = '';
var qmDmRangeV : Integer = 0;
var qmDmHot : Boolean = False;
var qmDmSt : String = 'OK';
var qmDmNl : Integer = 0;
var qmDmJs : String = '';
var qmDmErr : String = '';
var qmDmLimNames : String = '|gc_maxbuildercount|gc_maxexitpointscount|gc_maxshotpointscount|gc_maxwallbuilderpointscount|gc_maxwallvariationcount|gc_formation_maxcount|';
var qmDmLim : Integer = 0;

procedure qmDmNote(const qmDnTag : String; const qmDnText : String);
begin
   ParserSetValueByKeyByHandle(qmDmOut, qmDmJs+'t'+IntToStr(qmDmNl), qmDnTag);
   ParserSetValueByKeyByHandle(qmDmOut, qmDmJs+'x'+IntToStr(qmDmNl), qmDnText);
   qmDmNl := qmDmNl+1;
   if (qmDnTag='FAIL') or ((qmDnTag='WARN') and (qmDmSt='OK')) then
   qmDmSt := qmDnTag;
   if (qmDnTag='FAIL') and (qmDmErr='') then
   qmDmErr := qmDnText;
end;

//! Spaces and tabs (~009) off both ends (ref/records.py _strip). StrTrim
//! does the spaces: in an internal string no other byte at or below a space
//! is left (they are ~NNN), so it drops exactly what _strip drops of them.
procedure qmDmStrip(const qmDsS : String; var qmDsOut : String);
begin
   var qmDsGo : Boolean = True;
   var qmDsL : Integer;
   qmDsOut := StrTrim(qmDsS);
   qmDsGo := (StrPos('~009', qmDsOut)>0);
   while (qmDsGo) do
   begin
      qmDsGo := False;
      qmDsL := StrLength(qmDsOut);
      if (qmDsL>=1) and (SubStr(qmDsOut, 1, 1)=' ') then
      begin
         qmDsOut := SubStr(qmDsOut, 2, qmDsL-1);
         qmDsGo := True;
      end
      else
      if (qmDsL>=4) and (SubStr(qmDsOut, 1, 4)='~009') then
      begin
         qmDsOut := SubStr(qmDsOut, 5, qmDsL-4);
         qmDsGo := True;
      end
      else
      if (qmDsL>=1) and (SubStr(qmDsOut, qmDsL, 1)=' ') then
      begin
         qmDsOut := SubStr(qmDsOut, 1, qmDsL-1);
         qmDsGo := True;
      end
      else
      if (qmDsL>=4) and (SubStr(qmDsOut, qmDsL-3, 4)='~009') then
      begin
         qmDsOut := SubStr(qmDsOut, 1, qmDsL-4);
         qmDsGo := True;
      end;
   end;
end;

//! ASCII case folding: StrToLowerCase, which is not trusted beyond ASCII -
//! an internal string has no byte above z (those are ~NNN).
procedure qmDmLower(const qmDfS : String; var qmDfOut : String);
begin
   qmDfOut := StrToLowerCase(qmDfS);
end;

//! Fields of a `|`-list (`|a|b|` has 4).
function qmDmPipes(const qmDqS : String) : Integer;
begin
   var qmDqN : Integer = 1;
   var qmDqI : Integer;
   for qmDqI:=1 to StrLength(qmDqS) do
   if (SubStr(qmDqS, qmDqI, 1)='|') then
   qmDqN := qmDqN+1;
   Result := qmDqN;
end;

//! (v1, a1, b1) against (v2, a2, b2), field by field: <0, 0, >0.
function qmDmTriCmp(const qmDtV1 : String; const qmDtA1 : String; const qmDtB1 : String; const qmDtV2 : String; const qmDtA2 : String; const qmDtB2 : String) : Integer;
begin
   Result := qmCmpStr(qmDtV1, qmDtV2);
   if (Result=0) then
   Result := qmCmpStr(qmDtA1, qmDtA2);
   if (Result=0) then
   Result := qmCmpStr(qmDtB1, qmDtB2);
end;

function qmDmEnds(const qmDeS : String; const qmDeT : String) : Boolean;
begin
   Result := (StrLength(qmDeS)>=StrLength(qmDeT)) and (SubStr(qmDeS, StrLength(qmDeS)-StrLength(qmDeT)+1, StrLength(qmDeT))=qmDeT);
end;

//! 1 begin, 2 end, 3 root, 4 root end, 5 note, 6 value (ref/records.py _kind).
function qmDmKind(const qmDkL : String) : Integer;
begin
   var qmDkS : String;
   var qmDkT : String;
   qmDmStrip(qmDkL, qmDkT);
   qmDmLower(qmDkT, qmDkS);
   if qmDmEnds(qmDkS, 'struct.begin') then
   Result := 1
   else
   if (qmDkS='struct.end') then
   Result := 2
   else
   if qmDmEnds(qmDkS, 'section.begin') then
   Result := 3
   else
   if (qmDkS='section.end') then
   Result := 4
   else
   if (qmDkS='') or (SubStr(qmDkS, 1, 2)='//') then
   Result := 5
   else
   Result := 6;
end;

//! A line as records are compared by (ref/textio.py norm_key_escaped): every
//! tab as a space, no trailing space.
procedure qmDmNorm(const qmDoL : String; var qmDoOut : String);
begin
   qmDoOut := qmDoL;
   while (StrPos('~009', qmDoOut)>0) do
   qmDoOut := StrReplace(qmDoOut, '~009', ' ');
   while (StrLength(qmDoOut)>0) and (SubStr(qmDoOut, StrLength(qmDoOut), 1)=' ') do
   qmDoOut := SubStr(qmDoOut, 1, StrLength(qmDoOut)-1);
end;

//! An int key (ref/records.py _key_int): optional minus, digits. 1 = it is.
function qmDmIsInt(const qmDiS : String) : Boolean;
begin
   var qmDiT : String = qmDiS;
   if (SubStr(qmDiT, 1, 1)='-') then
   qmDiT := SubStr(qmDiT, 2, StrLength(qmDiT)-1);
   Result := qmIsDigits(qmDiT);
end;

//! The children of the array struct `qmDaName` in record lines A[s..s+n-1]
//! (the record's own begin and end lines included), -1 without the struct
//! (ref/records.py _children).
function qmDmChildren(const qmDaS : Integer; const qmDaN : Integer; const qmDaName : String) : Integer;
begin
   var qmDaDepth : Integer = 0;
   var qmDaIn : Boolean = False;
   var qmDaCount : Integer = -1;
   var qmDaI : Integer;
   var qmDaK : Integer;
   var qmDaT : String;
   var qmDaL : String;
   var qmDaP : Integer;
   for qmDaI:=qmDaS+1 to qmDaS+qmDaN-2 do
   begin
      qmDaK := qmDmKind(qmDmA[qmDaI]);
      qmDmStrip(qmDmA[qmDaI], qmDaT);
      qmDmLower(qmDaT, qmDaL);
      if (qmDaK=1) then
      begin
         qmDaDepth := qmDaDepth+1;
         qmDaP := StrPos(':', qmDaL);
         if (qmDaP>0) then
         qmDmStrip(SubStr(qmDaL, 1, qmDaP-1), qmDaT)
         else
         qmDaT := qmDaL;
         if (qmDaDepth=1) and (qmDaT=qmDaName) then
         begin
            qmDaIn := True;
            qmDaCount := 0;
         end
         else
         if (qmDaIn) and (qmDaDepth=2) then
         qmDaCount := qmDaCount+1;
      end
      else
      if (qmDaK=2) then
      begin
         if (qmDaDepth=1) and (qmDaIn) then
         qmDaIn := False;
         qmDaDepth := qmDaDepth-1;
      end
      else
      if (qmDaIn) and (qmDaDepth=1) and (qmDaK=6) and (SubStr(qmDaL, 1, 3)='[*]') then
      qmDaCount := qmDaCount+1;
   end;
   Result := qmDaCount;
end;

//! The Key / AlternativeKey values of a hotkeys record, `|a|b|` folded.
procedure qmDmHotKeys(const qmDhS : Integer; const qmDhN : Integer; var qmDhOut : String);
begin
   var qmDhI : Integer;
   var qmDhT : String;
   var qmDhEq : Integer;
   var qmDhK : String;
   var qmDhV : String;
   var qmDhL : String;
   qmDhOut := '|';
   for qmDhI:=qmDhS to qmDhS+qmDhN-1 do
   begin
      qmDmStrip(qmDmA[qmDhI], qmDhT);
      qmDhEq := StrPos('=', qmDhT);
      if (qmDhEq>1) then
      begin
         qmDmStrip(SubStr(qmDhT, 1, qmDhEq-1), qmDhK);
         qmDmLower(qmDhK, qmDhL);
         qmDhK := qmDhL;
         if (qmDhK='key') or (qmDhK='alternativekey') then
         begin
            qmDmStrip(SubStr(qmDhT, qmDhEq+1, StrLength(qmDhT)-qmDhEq), qmDhV);
            qmDmLower(qmDhV, qmDhL);
            qmDhV := qmDhL;
            if (qmDhV<>'') and (StrPos('|'+qmDhV+'|', qmDhOut)=0) then
            qmDhOut := qmDhOut+qmDhV+'|';
         end;
      end;
   end;
end;

//! File f, read into A (n lines), split into records (ref/records.py split).
//! qmDmFOk[f] = 1 when it is the record layout.
procedure qmDmSplit(const qmDpF : Integer; const qmDpN : Integer);
begin
   var qmDpState : Integer = 0;
   var qmDpDepth : Integer = 0;
   var qmDpStart : Integer = 0;
   var qmDpPend : Integer = 0;
   var qmDpPendAt : Integer = 0;
   var qmDpKey : String = '';
   var qmDpHas : Boolean = False;
   var qmDpI : Integer;
   var qmDpK : Integer;
   var qmDpT : String;
   var qmDpL : String;
   var qmDpEq : Integer;
   var qmDpKn : String;
   var qmDpKl : String;
   var qmDpH1 : Integer;
   var qmDpH2 : Integer;
   var qmDpHl : Integer;
   var qmDpJ : Integer;
   var qmDpR : Integer;
   var qmDpBad : Boolean = False;
   var qmDpBal : Integer = 0;
   qmDmFFirst[qmDpF] := qmDmNr;
   qmDmFCount[qmDpF] := 0;
   qmDmFOk[qmDpF] := 0;
   for qmDpI:=0 to qmDpN-1 do
   if (not qmDpBad) then
   begin
      qmDpK := qmDmKind(qmDmA[qmDpI]);
      if (qmDpK=1) or (qmDpK=3) then
      qmDpBal := qmDpBal+1;
      if (qmDpK=2) or (qmDpK=4) then
      qmDpBal := qmDpBal-1;
      if (qmDpState=0) then
      begin
         if (qmDpK=3) then
         begin
            qmDpState := 1;
            if (qmDpF=0) then
            qmDmHeadN := qmDpI+1;
            qmDpPend := 0;
            qmDpPendAt := qmDpI+1;
         end
         else
         if (qmDpK<>5) then
         qmDpBad := True;
      end
      else
      if (qmDpState=1) then
      begin
         qmDmStrip(qmDmA[qmDpI], qmDpT);
         qmDmLower(qmDpT, qmDpL);
         while (StrPos(' ', qmDpL)>0) do
         qmDpL := StrReplace(qmDpL, ' ', '');
         if (qmDpK=1) and (qmDpL='[*]:struct.begin') then
         begin
            qmDpState := 2;
            qmDpDepth := 1;
            qmDpStart := qmDpI;
            qmDpHas := False;
            qmDpKey := '';
         end
         else
         if (qmDpK=4) then
         begin
            if (qmDpF=0) then
            begin
               qmDmTrailS := qmDpPendAt;
               qmDmTrailN := qmDpN-qmDpPendAt;
            end;
            qmDpState := 3;
         end
         else
         if (qmDpK=5) then
         qmDpPend := qmDpPend+1
         else
         qmDpBad := True;
      end
      else
      if (qmDpState=2) then
      begin
         if (qmDpK=1) then
         qmDpDepth := qmDpDepth+1
         else
         if (qmDpK=2) then
         begin
            qmDpDepth := qmDpDepth-1;
            if (qmDpDepth=0) then
            begin
               if (not qmDpHas) or (qmDmNr>8191) then
               qmDpBad := True
               else
               begin
                  qmDpR := qmDmNr;
                  qmDmLower(qmDpKey, qmDmRk[qmDpR]);
                  qmDmRs[qmDpR] := qmDpPendAt;
                  qmDmRp[qmDpR] := qmDpPend;
                  qmDmRn[qmDpR] := qmDpI-qmDpStart+1;
                  //! The compared lines' hash: the record's own lines, as compared.
                  qmDpH1 := 0;
                  qmDpH2 := 0;
                  qmDpHl := 0;
                  for qmDpJ:=qmDpStart to qmDpI do
                  begin
                     qmDmNorm(qmDmA[qmDpJ], qmDpT);
                     qmHashStr(qmDpT, qmDpH1, qmDpH2, qmDpHl);
                     qmHashByte(10, qmDpH1, qmDpH2, qmDpHl);
                  end;
                  qmHashText(qmDpH1, qmDpH2, qmDpHl, qmDmRh[qmDpR]);
                  qmDmRc0[qmDpR] := -1;
                  qmDmRc1[qmDpR] := -1;
                  qmDmRc2[qmDpR] := -1;
                  if (qmDmArrN>0) then
                  qmDmRc0[qmDpR] := qmDmChildren(qmDpStart, qmDmRn[qmDpR], qmDmArr[0]);
                  if (qmDmArrN>1) then
                  qmDmRc1[qmDpR] := qmDmChildren(qmDpStart, qmDmRn[qmDpR], qmDmArr[1]);
                  if (qmDmArrN>2) then
                  qmDmRc2[qmDpR] := qmDmChildren(qmDpStart, qmDmRn[qmDpR], qmDmArr[2]);
                  qmDmRv[qmDpR] := '';
                  if (qmDmHot) then
                  qmDmHotKeys(qmDpStart, qmDmRn[qmDpR], qmDmRv[qmDpR]);
                  qmDmRb[qmDpR] := qmDpF;
                  //! A key twice in one file is not the layout.
                  for qmDpJ:=qmDmFFirst[qmDpF] to qmDpR-1 do
                  if (qmDmRk[qmDpJ]=qmDmRk[qmDpR]) then
                  qmDpBad := True;
                  //! The original key (not folded) for the report lines.
                  ParserSetValueByKeyByHandle(qmDmOut, 'rk'+IntToStr(qmDpR), qmDpKey);
                  qmDmNr := qmDmNr+1;
                  qmDmFCount[qmDpF] := qmDmFCount[qmDpF]+1;
                  qmDpState := 1;
                  qmDpPend := 0;
                  qmDpPendAt := qmDpI+1;
               end;
            end;
         end
         else
         if (qmDpK=3) or (qmDpK=4) then
         qmDpBad := True
         else
         if (qmDpDepth=1) and (not qmDpHas) and (qmDpK=6) then
         begin
            qmDmStrip(qmDmA[qmDpI], qmDpT);
            qmDpEq := StrPos('=', qmDpT);
            if (qmDpEq>1) then
            begin
               qmDmStrip(SubStr(qmDpT, 1, qmDpEq-1), qmDpKn);
               qmDmLower(qmDpKn, qmDpKl);
               qmDpKn := qmDpKl;
               if (qmDpKn=qmDmKey) then
               begin
                  qmDmStrip(SubStr(qmDpT, qmDpEq+1, StrLength(qmDpT)-qmDpEq), qmDpKey);
                  qmDpHas := True;
               end;
            end;
         end;
      end;
   end;
   if (qmDpState=3) and (not qmDpBad) then
   qmDmFOk[qmDpF] := 1;
   if (qmDpF=0) then
   qmDmBaseBal := qmDpBal;
end;

//! A file's lines into A; -1 when it cannot be read or does not fit.
function qmDmRead(const qmDrPath : String) : Integer;
begin
   var qmDrN : Integer = -2;
   qmRawRead(qmDrPath, -1, qmDmA, qmDrN);
   Result := qmDrN;
end;

//! The bound constants of the dmscript.global in effect (ref/records.py
//! limits_from_global): the first `<name> = <digits>` of each name.
procedure qmDmLimits(const qmDlPath : String);
begin
   var qmDlN : Integer = qmDmRead(qmDlPath);
   var qmDlI : Integer;
   var qmDlT : String;
   var qmDlS : String;
   var qmDlEq : Integer;
   var qmDlName : String;
   var qmDlV : String;
   var qmDlD : String;
   var qmDlC : Integer;
   var qmDlSeen : String = '|';
   if (qmDlN<0) then
   exit;
   for qmDlI:=0 to qmDlN-1 do
   begin
      qmDmStrip(qmDmA[qmDlI], qmDlT);
      qmDmLower(qmDlT, qmDlS);
      qmDlEq := StrPos('=', qmDlS);
      if (qmDlEq>1) then
      begin
         qmDmStrip(SubStr(qmDlS, 1, qmDlEq-1), qmDlName);
         if (StrPos('|'+qmDlName+'|', qmDmLimNames)>0) and (StrPos('|'+qmDlName+'|', qmDlSeen)=0) then
         begin
            qmDmStrip(SubStr(qmDlS, qmDlEq+1, StrLength(qmDlS)-qmDlEq), qmDlV);
            qmDlD := '';
            qmDlC := 1;
            while (qmDlC<=StrLength(qmDlV)) and (StrPos(SubStr(qmDlV, qmDlC, 1), '0123456789')>0) do
            begin
               qmDlD := qmDlD+SubStr(qmDlV, qmDlC, 1);
               qmDlC := qmDlC+1;
            end;
            if (qmDlD<>'') then
            begin
               qmDlSeen := qmDlSeen+qmDlName+'|';
               ParserSetValueByKeyByHandle(qmDmOut, 'lim_'+qmDlName, qmDlD);
            end;
         end;
      end;
   end;
end;

//! A bound's constant: the dmscript.global in effect, else vanilla's value.
function qmDmConst(const qmDcName : String; const qmDcVanilla : Integer) : Integer;
begin
   var qmDcV : String = ParserGetValueByKeyByHandle(qmDmOut, 'lim_'+qmDcName);
   if (qmDcV<>'') then
   Result := StrToInt(qmDcV)
   else
   Result := qmDcVanilla;
end;

procedure qmDmShow(const qmDwR : Integer; var qmDwOut : String);
begin
   qmUnesc(ParserGetValueByKeyByHandle(qmDmOut, 'rk'+IntToStr(qmDwR)), qmDwOut);
end;

var qmDmJobs : Integer = ParserGetIntValueByKeyByHandle(qmDmIn, 'jobs');
var qmDmJ : Integer;
var qmDmP : Integer;
var qmDmF : Integer;
var qmDmI : Integer;
var qmDmK : Integer;
var qmDmR : Integer;
var qmDmX : Integer;
var qmDmN : Integer;
var qmDmPath : String;
var qmDmS : String;
var qmDmT : String;
var qmDmU : String;
var qmDmBad : Boolean;
var qmDmLastF : Integer;
var qmDmLastR : Integer;
var qmDmVers : String;
var qmDmWho : String;
var qmDmCnt : Integer;
var qmDmFound : Integer;
var qmDmAllow : Integer;
var qmDmTop : Integer;
var qmDmLines : Integer;
var qmDmSeq : Integer;
var qmDmTok : String;
var qmDmBytes : Integer;
var qmDmH1 : Integer;
var qmDmH2 : Integer;
var qmDmHl : Integer;
var qmDmQ : Integer;
var qmDmPairs : String;
var qmDmKnown : String;
var qmDmPv : String;
var qmDmPa : String;
var qmDmPb : String;
var qmDmPl : array [0..511] of String;
var qmDmPla : array [0..511] of String;
var qmDmPlb : array [0..511] of String;
var qmDmPn : Integer;
var qmDmOk : Boolean;
var qmDmTp : Integer;
var qmDmT0 : Float;
for qmDmJ:=0 to qmDmJobs-1 do
begin
   qmDmT0 := _misc_GetRealTime;
   qmDmJs := 'j'+IntToStr(qmDmJ);
   qmDmNl := 0;
   qmDmSt := 'OK';
   qmDmErr := '';
   qmDmNr := 0;
   qmDmOn := 0;
   qmDmHeadN := 0;
   qmDmTrailS := 0;
   qmDmTrailN := 0;
   qmDmPath := ParserGetValueByKeyByHandle(qmDmIn, qmDmJs+'path');
   qmDmP := ParserGetIntValueByKeyByHandle(qmDmIn, qmDmJs+'parts');
   if (qmDmP>16) then
   qmDmP := 16;
   //! The profile (ref/records.py PROFILES).
   qmDmArrN := 0;
   qmDmMaxC := '';
   qmDmRangeC := '';
   qmDmHot := False;
   qmDmKey := '';
   if (qmDmPath='game\var\hotkeys.cfg') then
   begin
      qmDmKey := 'action';
      qmDmHot := True;
   end;
   if (qmDmPath='game\var\objcustom.cfg') then
   begin
      qmDmKey := 'sid';
      qmDmArr[0] := 'builderpoints';
      qmDmArrC[0] := 'gc_maxbuildercount';
      qmDmArrV[0] := 30;
      qmDmArr[1] := 'exitpoints';
      qmDmArrC[1] := 'gc_maxexitpointscount';
      qmDmArrV[1] := 4;
      qmDmArr[2] := 'shotpoints';
      qmDmArrC[2] := 'gc_maxshotpointscount';
      qmDmArrV[2] := 40;
      qmDmArrN := 3;
   end;
   if (qmDmPath='game\var\wallcustom.cfg') then
   begin
      qmDmKey := 'wallvariation';
      qmDmArr[0] := 'builderpoints';
      qmDmArrC[0] := 'gc_maxwallbuilderpointscount';
      qmDmArrV[0] := 16;
      qmDmArrN := 1;
      qmDmRangeC := 'gc_maxwallvariationcount';
      qmDmRangeV := 24;
   end;
   if (qmDmPath='game\var\formations.cfg') then
   begin
      qmDmKey := 'id';
      qmDmMaxC := 'gc_formation_maxcount';
      qmDmMaxV := 160;
   end;
   qmDmFPath[0] := ParserGetValueByKeyByHandle(qmDmIn, qmDmJs+'base');
   qmDmFName[0] := 'vanilla';
   for qmDmF:=1 to qmDmP do
   begin
      qmDmFPath[qmDmF] := ParserGetValueByKeyByHandle(qmDmIn, qmDmJs+'p'+IntToStr(qmDmF-1));
      qmDmFName[qmDmF] := ParserGetValueByKeyByHandle(qmDmIn, qmDmJs+'n'+IntToStr(qmDmF-1));
   end;
   qmDmBad := (qmDmKey='');
   if (qmDmBad) then
   qmDmNote('FAIL', 'no record profile for '+qmDmPath);
   //! The constants of the dmscript.global in effect (ref/records.py
   //! limits_from_global), read before the inputs.
   for qmDmI:=0 to 5 do
   begin
      qmField(qmDmLimNames, '|', qmDmI+1, qmDmS);
      ParserSetValueByKeyByHandle(qmDmOut, 'lim_'+qmDmS, '');
   end;
   if (not qmDmBad) then
   qmDmLimits(ParserGetValueByKeyByHandle(qmDmIn, qmDmJs+'glob'));
   //! Pass 1: every input split into the index.
   for qmDmF:=0 to qmDmP do
   if (not qmDmBad) then
   begin
      qmDmN := qmDmRead(qmDmFPath[qmDmF]);
      if (qmDmN<0) then
      begin
         qmDmFOk[qmDmF] := 0;
         qmDmFFirst[qmDmF] := qmDmNr;
         qmDmFCount[qmDmF] := 0;
      end
      else
      qmDmSplit(qmDmF, qmDmN);
      if (qmDmFOk[qmDmF]=0) then
      begin
         qmDmBad := True;
         if (qmDmF=0) then
         qmDmNote('FAIL', 'vanilla''s file is not the record layout')
         else
         qmDmNote('FAIL', qmDmFName[qmDmF]+': the file is not the record layout');
      end;
   end;
   //! The decisions (ref/records.py merge): vanilla's records in order, the
   //! last mod that touched one decides; then the records vanilla lacks.
   if (not qmDmBad) then
   begin
      for qmDmR:=qmDmFFirst[0] to qmDmFFirst[0]+qmDmFCount[0]-1 do
      begin
         qmDmLastF := -1;
         qmDmLastR := -1;
         qmDmVers := '|';
         qmDmWho := '';
         qmDmCnt := 0;
         for qmDmF:=1 to qmDmP do
         begin
            qmDmFound := -1;
            for qmDmI:=qmDmFFirst[qmDmF] to qmDmFFirst[qmDmF]+qmDmFCount[qmDmF]-1 do
            if (qmDmFound<0) and (qmDmRk[qmDmI]=qmDmRk[qmDmR]) then
            qmDmFound := qmDmI;
            if (qmDmFound<0) or (qmDmRh[qmDmFound]<>qmDmRh[qmDmR]) then
            begin
               //! touched: removed (-1) or changed
               qmDmLastF := qmDmF;
               qmDmLastR := qmDmFound;
               if (qmDmFound<0) then
               qmDmT := 'removed'
               else
               qmDmT := qmDmRh[qmDmFound];
               if (StrPos('|'+qmDmT+'|', qmDmVers)=0) then
               begin
                  qmDmVers := qmDmVers+qmDmT+'|';
                  qmDmCnt := qmDmCnt+1;
               end;
               if (qmDmWho<>'') then
               qmDmWho := qmDmWho+', ';
               qmDmWho := qmDmWho+qmDmFName[qmDmF];
            end;
         end;
         qmDmShow(qmDmR, qmDmU);
         if (qmDmLastF<0) then
         begin
            qmDmOf[qmDmOn] := 0;
            qmDmOr[qmDmOn] := qmDmR;
            qmDmOn := qmDmOn+1;
         end
         else
         begin
            if (qmDmCnt>1) then
            qmDmNote('WARN', 'record '+qmDmU+': changed by '+qmDmWho+' differently; '+qmDmFName[qmDmLastF]+'''s version is used');
            if (qmDmLastR<0) then
            qmDmNote('OK', 'record '+qmDmU+': removed by '+qmDmFName[qmDmLastF])
            else
            begin
               qmDmOf[qmDmOn] := qmDmLastF;
               qmDmOr[qmDmOn] := qmDmLastR;
               qmDmOn := qmDmOn+1;
               qmDmNote('OK', 'record '+qmDmU+': from '+qmDmFName[qmDmLastF]);
            end;
         end;
      end;
      //! Added records: first appearance keeps its place, a later version wins.
      qmDmK := qmDmOn;
      for qmDmF:=1 to qmDmP do
      for qmDmI:=qmDmFFirst[qmDmF] to qmDmFFirst[qmDmF]+qmDmFCount[qmDmF]-1 do
      begin
         qmDmFound := -1;
         for qmDmR:=qmDmFFirst[0] to qmDmFFirst[0]+qmDmFCount[0]-1 do
         if (qmDmRk[qmDmR]=qmDmRk[qmDmI]) then
         qmDmFound := qmDmR;
         if (qmDmFound<0) then
         begin
            qmDmX := -1;
            for qmDmR:=qmDmK to qmDmOn-1 do
            if (qmDmRk[qmDmOr[qmDmR]]=qmDmRk[qmDmI]) then
            qmDmX := qmDmR;
            if (qmDmX<0) then
            begin
               if (qmDmOn<=4095) then
               begin
                  qmDmOf[qmDmOn] := qmDmF;
                  qmDmOr[qmDmOn] := qmDmI;
                  qmDmOn := qmDmOn+1;
               end;
            end
            else
            begin
               if (qmDmRh[qmDmOr[qmDmX]]<>qmDmRh[qmDmI]) then
               begin
                  qmDmShow(qmDmI, qmDmU);
                  qmDmNote('WARN', 'record '+qmDmU+': added by '+qmDmFName[qmDmOf[qmDmX]]+' and '+qmDmFName[qmDmF]+' differently; '+qmDmFName[qmDmF]+'''s version is used');
               end;
               qmDmOf[qmDmX] := qmDmF;
               qmDmOr[qmDmX] := qmDmI;
            end;
         end;
      end;
      for qmDmR:=qmDmK to qmDmOn-1 do
      begin
         qmDmShow(qmDmOr[qmDmR], qmDmU);
         qmDmNote('OK', 'record '+qmDmU+': added by '+qmDmFName[qmDmOf[qmDmR]]);
      end;
      //! The checks (ref/records.py check), in its order. Structs balanced:
      //! vanilla's header and trailer carry the root's begin and end, every
      //! record is balanced by its split.
      if (qmDmBaseBal<>0) then
      qmDmNote('FAIL', 'the merged file has unbalanced structs');
      if (qmDmMaxC<>'') and (qmDmSt<>'FAIL') then
      begin
         qmDmAllow := qmDmConst(qmDmMaxC, qmDmMaxV);
         for qmDmF:=0 to qmDmP do
         if (qmDmFCount[qmDmF]>qmDmAllow) then
         qmDmAllow := qmDmFCount[qmDmF];
         if (qmDmOn>qmDmAllow) then
         qmDmNote('FAIL', IntToStr(qmDmOn)+' records, the game loads none above '+IntToStr(qmDmAllow));
      end;
      if (qmDmRangeC<>'') and (qmDmSt<>'FAIL') then
      begin
         qmDmTop := qmDmConst(qmDmRangeC, qmDmRangeV)-1;
         for qmDmI:=0 to qmDmNr-1 do
         if (qmDmIsInt(qmDmRk[qmDmI])) then
         if (StrToInt(qmDmRk[qmDmI])>qmDmTop) then
         qmDmTop := StrToInt(qmDmRk[qmDmI]);
         for qmDmR:=0 to qmDmOn-1 do
         if (qmDmSt<>'FAIL') then
         begin
            qmDmOk := qmDmIsInt(qmDmRk[qmDmOr[qmDmR]]);
            if (qmDmOk) then
            qmDmOk := (StrToInt(qmDmRk[qmDmOr[qmDmR]])>=0) and (StrToInt(qmDmRk[qmDmOr[qmDmR]])<=qmDmTop);
            if (not qmDmOk) then
            begin
               qmDmShow(qmDmOr[qmDmR], qmDmU);
               qmDmNote('FAIL', 'record '+qmDmU+': the key must be 0..'+IntToStr(qmDmTop));
            end;
         end;
      end;
      for qmDmK:=0 to qmDmArrN-1 do
      if (qmDmSt<>'FAIL') then
      begin
         qmDmAllow := qmDmConst(qmDmArrC[qmDmK], qmDmArrV[qmDmK]);
         for qmDmI:=0 to qmDmNr-1 do
         begin
            qmDmX := qmDmRc0[qmDmI];
            if (qmDmK=1) then
            qmDmX := qmDmRc1[qmDmI];
            if (qmDmK=2) then
            qmDmX := qmDmRc2[qmDmI];
            if (qmDmX>qmDmAllow) then
            qmDmAllow := qmDmX;
         end;
         for qmDmR:=0 to qmDmOn-1 do
         if (qmDmSt<>'FAIL') then
         begin
            qmDmI := qmDmOr[qmDmR];
            qmDmX := qmDmRc0[qmDmI];
            if (qmDmK=1) then
            qmDmX := qmDmRc1[qmDmI];
            if (qmDmK=2) then
            qmDmX := qmDmRc2[qmDmI];
            if (qmDmX>qmDmAllow) then
            begin
               qmDmShow(qmDmI, qmDmU);
               qmDmNote('FAIL', 'record '+qmDmU+': '+qmDmArr[qmDmK]+' has '+IntToStr(qmDmX)+' entries, the game holds '+IntToStr(qmDmAllow));
            end;
         end;
      end;
   end;
   //! Pass 2: the output lines - vanilla's header, the chosen records from
   //! each file (read once more), vanilla's trailer.
   if (not qmDmBad) and (qmDmSt<>'FAIL') then
   begin
      qmDmLines := qmDmHeadN;
      for qmDmR:=0 to qmDmOn-1 do
      begin
         qmDmOat[qmDmR] := qmDmLines;
         qmDmI := qmDmOr[qmDmR];
         qmDmLines := qmDmLines+qmDmRp[qmDmI]+qmDmRn[qmDmI];
      end;
      if (qmDmLines+qmDmTrailN>${rawcap}+1) then
      qmDmNote('FAIL', 'the merged file has more lines than Quartermaster can hold');
   end;
   if (not qmDmBad) and (qmDmSt<>'FAIL') then
   begin
      for qmDmF:=0 to qmDmP do
      begin
         qmDmCnt := 0;
         for qmDmR:=0 to qmDmOn-1 do
         if (qmDmOf[qmDmR]=qmDmF) then
         qmDmCnt := qmDmCnt+1;
         if (qmDmCnt>0) or (qmDmF=0) then
         begin
            qmDmN := qmDmRead(qmDmFPath[qmDmF]);
            if (qmDmF=0) then
            begin
               for qmDmI:=0 to qmDmHeadN-1 do
               qmDmB[qmDmI] := qmDmA[qmDmI];
               for qmDmI:=0 to qmDmTrailN-1 do
               qmDmB[qmDmLines+qmDmI] := qmDmA[qmDmTrailS+qmDmI];
            end;
            for qmDmR:=0 to qmDmOn-1 do
            if (qmDmOf[qmDmR]=qmDmF) then
            begin
               qmDmI := qmDmOr[qmDmR];
               for qmDmX:=0 to qmDmRp[qmDmI]+qmDmRn[qmDmI]-1 do
               qmDmB[qmDmOat[qmDmR]+qmDmX] := qmDmA[qmDmRs[qmDmI]+qmDmX];
            end;
         end;
      end;
      qmDmLines := qmDmLines+qmDmTrailN;
      //! Hotkeys: two actions the merge put on one key that no single input
      //! has on it together (ref/records.py _hotkey_collisions), sorted.
      if (qmDmHot) then
      begin
         qmDmKnown := '|';
         for qmDmF:=0 to qmDmP do
         for qmDmI:=qmDmFFirst[qmDmF] to qmDmFFirst[qmDmF]+qmDmFCount[qmDmF]-1 do
         for qmDmX:=qmDmI+1 to qmDmFFirst[qmDmF]+qmDmFCount[qmDmF]-1 do
         for qmDmK:=1 to qmDmPipes(qmDmRv[qmDmI])-2 do
         begin
            qmField(qmDmRv[qmDmI], '|', qmDmK, qmDmPv);
            if (StrPos('|'+qmDmPv+'|', qmDmRv[qmDmX])>0) then
            begin
               //! `{` never stands raw in an internal string (qmstr), so it
               //! joins the triple unambiguously. A control character did not:
               //! in the game the fields came back empty (run p3collide).
               if (qmCmpStr(qmDmRk[qmDmI], qmDmRk[qmDmX])<0) then
               qmDmKnown := qmDmKnown+qmDmPv+'{'+qmDmRk[qmDmI]+'{'+qmDmRk[qmDmX]+'|'
               else
               qmDmKnown := qmDmKnown+qmDmPv+'{'+qmDmRk[qmDmX]+'{'+qmDmRk[qmDmI]+'|';
            end;
         end;
         qmDmPn := 0;
         for qmDmR:=0 to qmDmOn-1 do
         for qmDmQ:=qmDmR+1 to qmDmOn-1 do
         begin
            qmDmI := qmDmOr[qmDmR];
            qmDmX := qmDmOr[qmDmQ];
            for qmDmK:=1 to qmDmPipes(qmDmRv[qmDmI])-2 do
            begin
               qmField(qmDmRv[qmDmI], '|', qmDmK, qmDmPv);
               if (StrPos('|'+qmDmPv+'|', qmDmRv[qmDmX])>0) then
               begin
                  if (qmCmpStr(qmDmRk[qmDmI], qmDmRk[qmDmX])<0) then
                  begin
                     qmDmPa := qmDmRk[qmDmI];
                     qmDmPb := qmDmRk[qmDmX];
                  end
                  else
                  begin
                     qmDmPa := qmDmRk[qmDmX];
                     qmDmPb := qmDmRk[qmDmI];
                  end;
                  qmDmT := qmDmPv+'{'+qmDmPa+'{'+qmDmPb;
                  if (StrPos('|'+qmDmT+'|', qmDmKnown)=0) and (qmDmPn<512) then
                  begin
                     //! insertion by the triple's order (value, a, b), field by
                     //! field as Python compares tuples
                     qmDmTp := qmDmPn;
                     while (qmDmTp>0) and (qmDmTriCmp(qmDmPl[qmDmTp-1], qmDmPla[qmDmTp-1], qmDmPlb[qmDmTp-1], qmDmPv, qmDmPa, qmDmPb)>0) do
                     begin
                        qmDmPl[qmDmTp] := qmDmPl[qmDmTp-1];
                        qmDmPla[qmDmTp] := qmDmPla[qmDmTp-1];
                        qmDmPlb[qmDmTp] := qmDmPlb[qmDmTp-1];
                        qmDmTp := qmDmTp-1;
                     end;
                     qmDmPl[qmDmTp] := qmDmPv;
                     qmDmPla[qmDmTp] := qmDmPa;
                     qmDmPlb[qmDmTp] := qmDmPb;
                     qmDmPn := qmDmPn+1;
                  end;
               end;
            end;
         end;
         for qmDmK:=0 to qmDmPn-1 do
         begin
            qmUnesc(qmDmPl[qmDmK], qmDmPv);
            qmUnesc(qmDmPla[qmDmK], qmDmPa);
            qmUnesc(qmDmPlb[qmDmK], qmDmPb);
            qmDmNote('WARN', 'key '+qmDmPv+': '+qmDmPa+' and '+qmDmPb+' are on it now');
         end;
      end;
      //! Staged, loaded by the engine's parser (plan S10: the trial load must
      //! succeed), and its token put where the writer looks for it.
      qmDmS := ParserGetValueByKeyByHandle(qmDmIn, qmDmJs+'out');
      qmRawWrite(qmDmS, qmDmB, qmDmLines);
      qmDmBytes := qmRawWrittenSize(qmDmB, qmDmLines);
      qmDmTp := ParserSelectByKey('qm_dm_trial');
      if (qmDmTp=0) then
      qmDmTp := ParserCreate('qm_dm_trial');
      ParserClearByHandle(qmDmTp);
      qmDmOk := (FileAge(qmDmS)<>-1);
      if (qmDmOk) then
      qmDmOk := ParserLoadFromFileByHandle(qmDmTp, qmDmS);
      if (qmDmOk) then
      qmDmOk := (ParserGetCountByHandle(qmDmTp)=qmDmOn);
      ParserClearByHandle(qmDmTp);
      if (not qmDmOk) then
      qmDmNote('FAIL', 'the engine''s parser does not load the merged file as '+IntToStr(qmDmOn)+' records')
      else
      begin
         qmDmH1 := 0;
         qmDmH2 := 0;
         qmDmHl := 0;
         for qmDmI:=0 to qmDmLines-1 do
         begin
            qmHashStr(qmDmB[qmDmI], qmDmH1, qmDmH2, qmDmHl);
            qmHashByte(10, qmDmH1, qmDmH2, qmDmHl);
         end;
         qmHashText(qmDmH1, qmDmH2, qmDmHl, qmDmTok);
         //! qmValNext (src/lib/qmval.pas): one sequence for every candidate.
         qmDmTp := ParserSelectByKey('qm_val');
         if (qmDmTp=0) then
         qmDmTp := ParserCreate('qm_val');
         qmDmSeq := ParserGetIntValueByKeyByHandle(qmDmTp, 'seq');
         ParserSetIntValueByKeyByHandle(qmDmTp, 'seq', qmDmSeq+1);
         ParserSetValueByKeyByHandle(qmDmTp, 'd'+IntToStr(qmDmSeq), qmDmTok);
         ParserSetIntValueByKeyByHandle(qmDmOut, qmDmJs+'seq', qmDmSeq);
         ParserSetValueByKeyByHandle(qmDmOut, qmDmJs+'tok', qmDmTok);
         ParserSetIntValueByKeyByHandle(qmDmOut, qmDmJs+'lines', qmDmLines);
         ParserSetIntValueByKeyByHandle(qmDmOut, qmDmJs+'bytes', qmDmBytes);
      end;
   end;
   ParserSetIntValueByKeyByHandle(qmDmOut, qmDmJs+'done', 1);
   ParserSetValueByKeyByHandle(qmDmOut, qmDmJs+'st', qmDmSt);
   ParserSetValueByKeyByHandle(qmDmOut, qmDmJs+'err', qmDmErr);
   ParserSetIntValueByKeyByHandle(qmDmOut, qmDmJs+'nl', qmDmNl);
   qmLog('data merge '+qmDmPath+' parts='+IntToStr(qmDmP)+' records='+IntToStr(qmDmOn)+' status='+qmDmSt+' '+qmDmErr+' ms='+FloatToStr((_misc_GetRealTime-qmDmT0)*1000));
end;
