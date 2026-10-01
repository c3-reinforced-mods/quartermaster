state: qmModsIni
into: data/quartermaster/core.aix
helpers: qmlog, qmstr, qmbootdir
requires:
---
//! The mods.ini writer (plan G5, S8, S11; twin: ref/order.py mods_ini_plan,
//! with the evidence). It puts the rows of qm_ini_in (n, dir<k>, dis<k>) into
//! mods.ini the way probe 5 did and the game honoured after the restart
//! (docs/research/context-2026-09-27.md section 3): the file from
//! ModLibraryGetIniFile loaded with the engine's parser, `dir` and `dis` set
//! in the entries that are there, ParserSaveToFileByHandle. No entry is added
//! or dropped. qmOrder asks for the canonical rows; the SelfTest's order cases
//! use the same writer for a shuffled or a disabled list (the harness never
//! writes mods.ini itself).
//!
//! Refused, and the file left alone, unless: the file loads and has the
//! `mods` node; it has as many entries as the engine registered (qm_mods n)
//! and as qm_ini_in asks for; every entry is exactly `dir` + `dis` and dis
//! reads True or False; its dirs and the rows' dirs are the engine's own list,
//! compared folded. Skipped when the rows are already there (plan S8: only if
//! its content differs); a row whose flag means what the file says keeps the
//! file's spelling of it. After a save the file is loaded again into another
//! parser and must read exactly the rows.
//!
//! `effective`: the enabled dirs in order - as the running game loaded them
//! (qm_mods dir<i> with eon<i> = 1, engine order) and as the new rows list
//! them - differ, so a restart is needed for the new order to count. Disabled
//! mods decide nothing: the overlay skips them.
//!
//! qm_ini keys: action (same, written, refused, failed), why, effective,
//! count (the entries found), moves and flags (what the write changes, in
//! words: `<dir> <from>-><to>` and `<dir> dis <old>-><new>`, `; ` between),
//! selfonly (1 = only Quartermaster's own place in the enabled order
//! changed), overn and over<j> (the qm_mods rows it moved past, in order).
var qmMiIni : Integer = ParserSelectByKey('qm_ini');
if (qmMiIni=0) then
qmMiIni := ParserCreate('qm_ini');
var qmMiIn : Integer = ParserSelectByKey('qm_ini_in');
var qmMiMods : Integer = ParserSelectByKey('qm_mods');
var qmMiPath : String = ModLibraryGetIniFile;
var qmMiSrc : Integer = ParserSelectByKey('qm_ini_src');
if (qmMiSrc=0) then
qmMiSrc := ParserCreate('qm_ini_src');
ParserClearByHandle(qmMiSrc);
var qmMiN : Integer = ParserGetIntValueByKeyByHandle(qmMiMods, 'n');
var qmMiFdir : array [0..255] of String;
var qmMiFdis : array [0..255] of String;
var qmMiFnorm : array [0..255] of String;
var qmMiWdir : array [0..255] of String;
var qmMiWdis : array [0..255] of String;
var qmMiWnorm : array [0..255] of String;
var qmMiEnorm : array [0..255] of String;
var qmMiWhy : String = '';
var qmMiCount : Integer = -1;
var qmMiNode : Integer = 0;
var qmMiE : Integer;
var qmMiK : Integer;
var qmMiJ : Integer;
var qmMiC : Integer;
var qmMiD : String;
var qmMiS : String;
var qmMiT : String;
ParserSetValueByKeyByHandle(qmMiIni, 'action', 'refused');
ParserSetIntValueByKeyByHandle(qmMiIni, 'effective', 0);
ParserSetIntValueByKeyByHandle(qmMiIni, 'selfonly', 0);
ParserSetIntValueByKeyByHandle(qmMiIni, 'overn', 0);
if (qmMiN>256) or (ParserGetIntValueByKeyByHandle(qmMiIn, 'n')<>qmMiN) then
qmMiWhy := 'count'
else
if (not ParserLoadFromFileByHandle(qmMiSrc, qmMiPath)) then
qmMiWhy := 'missing'
else
begin
   qmMiNode := ParserSelectByHandleByKey(qmMiSrc, 'mods');
   if (qmMiNode=0) then
   qmMiWhy := 'layout'
   else
   qmMiCount := ParserGetCountByHandle(qmMiNode);
end;
if (qmMiWhy='') and (qmMiCount<>qmMiN) then
qmMiWhy := 'count';
if (qmMiWhy='') then
for qmMiK:=0 to qmMiN-1 do
if (qmMiWhy='') then
begin
   qmMiE := ParserSelectByHandleByIndex(qmMiNode, qmMiK);
   qmMiFdir[qmMiK] := ParserGetValueByKeyByHandle(qmMiE, 'dir');
   qmMiFdis[qmMiK] := ParserGetValueByKeyByHandle(qmMiE, 'dis');
   qmNormDir(qmMiFdir[qmMiK], qmMiFnorm[qmMiK]);
   qmLowerAscii(qmMiFdis[qmMiK], qmMiS);
   if (ParserGetCountByHandle(qmMiE)<>2) or (qmMiFdir[qmMiK]='') then
   begin
      qmMiWhy := 'entry';
      qmLog('mods.ini entry '+IntToStr(qmMiK)+' has '+IntToStr(ParserGetCountByHandle(qmMiE))+' values, dir='+qmMiFdir[qmMiK]);
   end
   else
   if (qmMiS<>'true') and (qmMiS<>'false') then
   qmMiWhy := 'dis';
   qmMiWdir[qmMiK] := ParserGetValueByKeyByHandle(qmMiIn, 'dir'+IntToStr(qmMiK));
   qmMiWdis[qmMiK] := ParserGetValueByKeyByHandle(qmMiIn, 'dis'+IntToStr(qmMiK));
   qmNormDir(qmMiWdir[qmMiK], qmMiWnorm[qmMiK]);
   qmNormDir(ParserGetValueByKeyByHandle(qmMiMods, 'dir'+IntToStr(qmMiK)), qmMiEnorm[qmMiK]);
   qmLowerAscii(qmMiWdis[qmMiK], qmMiS);
   if (qmMiWhy='') and (qmMiS<>'true') and (qmMiS<>'false') then
   qmMiWhy := 'dis';
end;
//! The dirs of the file and of the rows are the engine's list, as a set:
//! every engine dir occurs exactly once in each.
if (qmMiWhy='') then
for qmMiK:=0 to qmMiN-1 do
begin
   qmMiC := 0;
   for qmMiJ:=0 to qmMiN-1 do
   if (qmMiFnorm[qmMiJ]=qmMiEnorm[qmMiK]) then
   qmMiC := qmMiC+1;
   if (qmMiC<>1) then
   qmMiWhy := 'dirs';
   qmMiC := 0;
   for qmMiJ:=0 to qmMiN-1 do
   if (qmMiWnorm[qmMiJ]=qmMiEnorm[qmMiK]) then
   qmMiC := qmMiC+1;
   if (qmMiC<>1) then
   qmMiWhy := 'dirs';
end;
if (qmMiWhy<>'') then
begin
   ParserSetValueByKeyByHandle(qmMiIni, 'why', qmMiWhy);
   ParserSetIntValueByKeyByHandle(qmMiIni, 'count', qmMiCount);
   qmLog('mods.ini refused: '+qmMiWhy+' (entries '+IntToStr(qmMiCount)+', mods '+IntToStr(qmMiN)+', '+qmMiPath+')');
   exit;
end;
//! A wanted flag that means what the file says keeps the file's spelling.
for qmMiK:=0 to qmMiN-1 do
for qmMiJ:=0 to qmMiN-1 do
if (qmMiFnorm[qmMiJ]=qmMiWnorm[qmMiK]) then
begin
   qmLowerAscii(qmMiFdis[qmMiJ], qmMiS);
   qmLowerAscii(qmMiWdis[qmMiK], qmMiT);
   if (qmMiS=qmMiT) then
   qmMiWdis[qmMiK] := qmMiFdis[qmMiJ];
end;
//! The enabled order before (the running game) and after (the rows).
qmMiS := '';
for qmMiK:=0 to qmMiN-1 do
if (ParserGetIntValueByKeyByHandle(qmMiMods, 'eon'+IntToStr(qmMiK))=1) then
qmMiS := qmMiS+qmMiEnorm[qmMiK]+'|';
qmMiT := '';
for qmMiK:=0 to qmMiN-1 do
begin
   qmLowerAscii(qmMiWdis[qmMiK], qmMiD);
   if (qmMiD='false') then
   qmMiT := qmMiT+qmMiWnorm[qmMiK]+'|';
end;
if (qmMiS<>qmMiT) then
ParserSetIntValueByKeyByHandle(qmMiIni, 'effective', 1);
//! Only Quartermaster's own place in the enabled order changed: the engine
//! rows it moved past (ref/order.py moved_past), for qmGuard's restart.
var qmMiSelf : Integer = ParserGetIntValueByKeyByHandle(qmMiMods, 'self');
var qmMiBr : array [0..255] of Integer;
var qmMiAr : array [0..255] of Integer;
var qmMiBn : Integer = 0;
var qmMiAn : Integer = 0;
var qmMiBs : Integer = -1;
var qmMiAs : Integer = -1;
var qmMiLo : Integer;
var qmMiHi : Integer;
var qmMiEq : Boolean;
for qmMiK:=0 to qmMiN-1 do
if (ParserGetIntValueByKeyByHandle(qmMiMods, 'eon'+IntToStr(qmMiK))=1) then
begin
   if (qmMiK=qmMiSelf) then
   qmMiBs := qmMiBn
   else
   begin
      qmMiBr[qmMiBn] := qmMiK;
      qmMiBn := qmMiBn+1;
   end;
end;
for qmMiK:=0 to qmMiN-1 do
begin
   qmLowerAscii(qmMiWdis[qmMiK], qmMiD);
   if (qmMiD='false') then
   for qmMiJ:=0 to qmMiN-1 do
   if (qmMiEnorm[qmMiJ]=qmMiWnorm[qmMiK]) then
   begin
      if (qmMiJ=qmMiSelf) then
      qmMiAs := qmMiAn
      else
      begin
         qmMiAr[qmMiAn] := qmMiJ;
         qmMiAn := qmMiAn+1;
      end;
   end;
end;
if (qmMiS<>qmMiT) and (qmMiSelf>=0) and (qmMiBs>=0) and (qmMiAs>=0) and (qmMiBn=qmMiAn) then
begin
   qmMiEq := True;
   for qmMiK:=0 to qmMiBn-1 do
   if (qmMiBr[qmMiK]<>qmMiAr[qmMiK]) then
   qmMiEq := False;
   if (qmMiEq) then
   begin
      qmMiLo := qmMiBs;
      qmMiHi := qmMiAs;
      if (qmMiAs<qmMiBs) then
      begin
         qmMiLo := qmMiAs;
         qmMiHi := qmMiBs;
      end;
      ParserSetIntValueByKeyByHandle(qmMiIni, 'selfonly', 1);
      ParserSetIntValueByKeyByHandle(qmMiIni, 'overn', qmMiHi-qmMiLo);
      for qmMiK:=qmMiLo to qmMiHi-1 do
      ParserSetIntValueByKeyByHandle(qmMiIni, 'over'+IntToStr(qmMiK-qmMiLo), qmMiBr[qmMiK]);
   end;
end;
ParserSetIntValueByKeyByHandle(qmMiIni, 'count', qmMiCount);
ParserSetValueByKeyByHandle(qmMiIni, 'why', '-');
qmMiC := 0;
for qmMiK:=0 to qmMiN-1 do
if (qmMiFdir[qmMiK]<>qmMiWdir[qmMiK]) or (qmMiFdis[qmMiK]<>qmMiWdis[qmMiK]) then
qmMiC := qmMiC+1;
//! What changes, in words the player can check against modman (ref/order.py
//! ini_changes): every entry that moves, with its 1-based position in the
//! file before and after, and every flag that changes.
var qmMiMoves : String = '';
var qmMiFlags : String = '';
for qmMiK:=0 to qmMiN-1 do
for qmMiJ:=0 to qmMiN-1 do
if (qmMiFnorm[qmMiJ]=qmMiWnorm[qmMiK]) then
begin
   if (qmMiJ<>qmMiK) then
   begin
      if (qmMiMoves<>'') then
      qmMiMoves := qmMiMoves+'; ';
      qmMiMoves := qmMiMoves+qmMiWdir[qmMiK]+' '+IntToStr(qmMiJ+1)+'->'+IntToStr(qmMiK+1);
   end;
   if (qmMiFdis[qmMiJ]<>qmMiWdis[qmMiK]) then
   begin
      if (qmMiFlags<>'') then
      qmMiFlags := qmMiFlags+'; ';
      qmMiFlags := qmMiFlags+qmMiWdir[qmMiK]+' dis '+qmMiFdis[qmMiJ]+'->'+qmMiWdis[qmMiK];
   end;
end;
ParserSetValueByKeyByHandle(qmMiIni, 'moves', qmMiMoves);
ParserSetValueByKeyByHandle(qmMiIni, 'flags', qmMiFlags);
if (qmMiC=0) then
begin
   ParserSetValueByKeyByHandle(qmMiIni, 'action', 'same');
   qmLog('mods.ini same: '+IntToStr(qmMiN)+' entries already in order, effective='+IntToStr(ParserGetIntValueByKeyByHandle(qmMiIni, 'effective')));
   exit;
end;
for qmMiK:=0 to qmMiN-1 do
begin
   qmMiE := ParserSelectByHandleByIndex(qmMiNode, qmMiK);
   ParserSetValueByKeyByHandle(qmMiE, 'dir', qmMiWdir[qmMiK]);
   ParserSetValueByKeyByHandle(qmMiE, 'dis', qmMiWdis[qmMiK]);
end;
var qmMiSaved : Boolean = ParserSaveToFileByHandle(qmMiSrc, qmMiPath);
//! Read back: another parser, the same checks.
var qmMiChk : Integer = ParserSelectByKey('qm_ini_chk');
if (qmMiChk=0) then
qmMiChk := ParserCreate('qm_ini_chk');
ParserClearByHandle(qmMiChk);
var qmMiOk : Boolean = qmMiSaved and ParserLoadFromFileByHandle(qmMiChk, qmMiPath);
var qmMiCn : Integer = 0;
if (qmMiOk) then
qmMiCn := ParserSelectByHandleByKey(qmMiChk, 'mods');
if (qmMiCn=0) then
qmMiOk := False
else
if (ParserGetCountByHandle(qmMiCn)<>qmMiN) then
qmMiOk := False
else
for qmMiK:=0 to qmMiN-1 do
begin
   qmMiE := ParserSelectByHandleByIndex(qmMiCn, qmMiK);
   if (ParserGetValueByKeyByHandle(qmMiE, 'dir')<>qmMiWdir[qmMiK]) or (ParserGetValueByKeyByHandle(qmMiE, 'dis')<>qmMiWdis[qmMiK]) then
   qmMiOk := False;
end;
if (qmMiOk) then
begin
   ParserSetValueByKeyByHandle(qmMiIni, 'action', 'written');
   qmLog('mods.ini written: '+IntToStr(qmMiC)+' of '+IntToStr(qmMiN)+' entries changed, effective='+IntToStr(ParserGetIntValueByKeyByHandle(qmMiIni, 'effective'))+', read back equal');
   if (qmMiMoves<>'') then
   qmLog('mods.ini moved: '+qmMiMoves);
   if (qmMiFlags<>'') then
   qmLog('mods.ini flags: '+qmMiFlags);
end
else
begin
   ParserSetValueByKeyByHandle(qmMiIni, 'action', 'failed');
   ParserSetValueByKeyByHandle(qmMiIni, 'why', 'readback');
   qmLog('mods.ini written but it does not read back as the rows (saved='+BoolToStr(qmMiSaved)+')');
end;
for qmMiK:=0 to qmMiN-1 do
qmLog('mods.ini row '+IntToStr(qmMiK)+' dir='+qmMiWdir[qmMiK]+' dis='+qmMiWdis[qmMiK]);
