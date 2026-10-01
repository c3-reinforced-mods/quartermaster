state: qmConflicts
into: data/quartermaster/core.aix
helpers: qmlog, qmstr, qmraw, qmreptext
requires: version
---
//! The conflict report (ref/conflicts.py is the twin and owns the rules, the
//! layout and their evidence): where two enabled mods change the same game
//! code, built from what the generation did - qm_gen, qm_plan, the merge rows
//! in qm_mg and qm_ms, qm_mods, and in a production generation the boot's
//! clashes in qm_boot - without changing any of it (decided 2026-10-01).
//! qmReport runs it first, so the window's report can show its pair lines,
//! and it writes <work>conflicts.txt through the raw writer (CRLF, no
//! timestamps: the same inputs give the same bytes).
//!
//! It leaves the named parser qm_conf: wn and w<k> the pair lines the window
//! shows (at most 14, then one that counts the rest), d<position> a mod's
//! Details sentence, and its own counters and section lines.
//!
//! Where in the code a record is and its vanilla line (`state <Name>, ...`,
//! `at:`) need the vanilla file: a record asks (qm_conf rn, rp<q> rs<q>
//! re<q>), and qmConflictsCode answers every ask in one run (rpl<q>,
//! rat<q>) before the file is written. That state holds the read pool of
//! 65536 lines; in this one it cost 926 ms on every generation, with or
//! without a record (run cr-t1-133722), so it runs only when one asks.
//! Limit of the game side the twin does not have: 256 mods.
var qmXcG : Integer = ParserSelectByKey('qm_gen');
var qmXcPlan : Integer = ParserSelectByKey('qm_plan');
var qmXcMods : Integer = ParserSelectByKey('qm_mods');
var qmXcMg : Integer = ParserSelectByKey('qm_mg');
var qmXcMs : Integer = ParserSelectByKey('qm_ms');
var qmXcBoot : Integer = ParserSelectByKey('qm_boot');
var qmXcC : Integer = ParserSelectByKey('qm_conf');
var qmXcNm : Integer = 0;
var qmXcSelf : Integer = -1;
var qmXcRk : array [0..255] of Integer;
var qmXcInv : array [0..255] of Integer;
var qmXcFirst : Integer = 0;
var qmXcVn : Integer = 0;
var qmXcK : Integer;
var qmXcM : Integer;
var qmXcMs2 : String;
var qmXcT : String;
var qmXcU : String;

//! A line of section qmZaSec (`sc` conflicts, `sl` left out, `sn` close
//! together, `sw` whole files, `sk` core scripts) of conflicts.txt.
procedure qmZaLine(const qmZaSec : String; const qmZaS : String);
begin
   var qmZaN : Integer = ParserGetIntValueByKeyByHandle(qmXcC, 'n'+qmZaSec);
   ParserSetValueByKeyByHandle(qmXcC, qmZaSec+IntToStr(qmZaN), qmZaS);
   ParserSetIntValueByKeyByHandle(qmXcC, 'n'+qmZaSec, qmZaN+1);
end;

//! A line of section qmZySec that ends with the answer of ask qmZyQ:
//! qmZyKind 1 the place in the code, 2 the vanilla line.
procedure qmZyLine(const qmZySec : String; const qmZyS : String; const qmZyQ : Integer; const qmZyKind : Integer);
begin
   var qmZyN : Integer = ParserGetIntValueByKeyByHandle(qmXcC, 'n'+qmZySec);
   qmZaLine(qmZySec, qmZyS);
   ParserSetIntValueByKeyByHandle(qmXcC, 'q'+qmZySec+IntToStr(qmZyN), qmZyQ+1);
   ParserSetIntValueByKeyByHandle(qmXcC, 'k'+qmZySec+IntToStr(qmZyN), qmZyKind);
end;

//! Ask for the place in the code and the vanilla line of the range
//! [qmZxS, qmZxE) of file qmZxPath (qmConflictsCode answers).
procedure qmZxAsk(const qmZxPath : String; const qmZxS : Integer; const qmZxE : Integer; var qmZxQ : Integer);
begin
   qmZxQ := ParserGetIntValueByKeyByHandle(qmXcC, 'rn');
   ParserSetValueByKeyByHandle(qmXcC, 'rp'+IntToStr(qmZxQ), qmZxPath);
   ParserSetIntValueByKeyByHandle(qmXcC, 'rs'+IntToStr(qmZxQ), qmZxS);
   ParserSetIntValueByKeyByHandle(qmXcC, 're'+IntToStr(qmZxQ), qmZxE);
   ParserSetIntValueByKeyByHandle(qmXcC, 'rn', qmZxQ+1);
end;

procedure qmZbInc(const qmZbKey : String; const qmZbBy : Integer);
begin
   ParserSetIntValueByKeyByHandle(qmXcC, qmZbKey, ParserGetIntValueByKeyByHandle(qmXcC, qmZbKey)+qmZbBy);
end;

//! A mod as conflicts.txt names it (ref/report.py _who).
procedure qmZcWho(const qmZcPos : Integer; var qmZcOut : String);
begin
   var qmZcR : Integer = 0;
   if (qmZcPos>=0) and (qmZcPos<256) then
   qmZcR := qmXcRk[qmZcPos];
   qmWho(IntToStr(qmZcPos), qmXcMods, qmZcR, qmZcOut);
end;

//! Its number alone, 0 for a mod that is off (ref/conflicts.py _num).
procedure qmZdNum(const qmZdPos : Integer; var qmZdOut : String);
begin
   qmZdOut := '0';
   if (qmZdPos>=0) and (qmZdPos<256) then
   qmZdOut := IntToStr(qmXcRk[qmZdPos]);
end;

//! Its title, else its dir (ref/conflicts.py _name).
procedure qmZeName(const qmZePos : Integer; var qmZeOut : String);
begin
   var qmZeI : Integer = ParserGetIntValueByKeyByHandle(qmXcMods, 'ord'+IntToStr(qmZePos));
   qmZeOut := ParserGetValueByKeyByHandle(qmXcMods, 'tit'+IntToStr(qmZeI));
   if (qmZeOut='') then
   qmZeOut := ParserGetValueByKeyByHandle(qmXcMods, 'dir'+IntToStr(qmZeI));
end;

procedure qmZfPlural(const qmZfN : Integer; const qmZfWord : String; var qmZfOut : String);
begin
   qmZfOut := IntToStr(qmZfN)+' '+qmZfWord;
   if (qmZfN<>1) then
   qmZfOut := qmZfOut+'s';
end;

//! The kind of a file by its folder (ref/conflicts.py kind).
procedure qmZgKind(const qmZgPath : String; var qmZgOut : String);
begin
   var qmZgP : String;
   qmLowerAscii(qmZgPath, qmZgP);
   qmZgOut := 'data, content';
   if (SubStr(qmZgP, 1, 9)='game\var\') then
   qmZgOut := 'data, gameplay';
   if (SubStr(qmZgP, 1, 7)='images\') then
   qmZgOut := 'graphics';
   if (SubStr(qmZgP, 1, 4)='hud\') then
   qmZgOut := 'graphics';
   if (SubStr(qmZgP, 1, 4)='gui\') then
   qmZgOut := 'interface layout';
   if (SubStr(qmZgP, 1, 15)='gui\common.inc\') then
   qmZgOut := 'script, interface';
   if (SubStr(qmZgP, 1, 13)='gui\menu.inc\') then
   qmZgOut := 'script, interface';
   if (SubStr(qmZgP, 1, 8)='scripts\') then
   qmZgOut := 'script, gameplay';
   if (SubStr(qmZgP, 1, 17)='scripts\dmscript.') then
   qmZgOut := 'core script, whole game';
   if (SubStr(qmZgP, 1, 12)='scripts\lib\') then
   qmZgOut := 'core script, whole game';
end;

//! A hunk row's change in words (ref/conflicts.py change).
procedure qmZmChange(const qmZmRow : String; var qmZmOut : String);
begin
   var qmZmA : String;
   var qmZmB : String;
   var qmZmC : String;
   var qmZmOld : Integer;
   var qmZmNew : Integer;
   var qmZmP : String;
   qmField(qmZmRow, '|', 3, qmZmA);
   qmField(qmZmRow, '|', 4, qmZmB);
   qmField(qmZmRow, '|', 5, qmZmC);
   qmZmOld := StrToInt(qmZmB)-StrToInt(qmZmA);
   qmZmNew := StrToInt(qmZmC);
   if (qmZmOld=0) then
   begin
      qmZfPlural(qmZmNew, 'line', qmZmP);
      qmZmOut := 'adds '+qmZmP;
   end
   else
   if (qmZmNew=0) then
   begin
      qmZfPlural(qmZmOld, 'line', qmZmP);
      qmZmOut := 'removes '+qmZmP;
   end
   else
   if (qmZmOld=qmZmNew) then
   begin
      qmZfPlural(qmZmOld, 'line', qmZmP);
      qmZmOut := 'changes '+qmZmP;
   end
   else
   begin
      qmZfPlural(qmZmOld, 'line', qmZmP);
      qmZmOut := 'replaces '+qmZmP+' with '+IntToStr(qmZmNew);
   end;
end;

//! The key of the pair of positions qmZnA and qmZnB, lower first.
procedure qmZnPair(const qmZnA : Integer; const qmZnB : Integer; var qmZnOut : String);
begin
   if (qmZnA<qmZnB) then
   qmZnOut := IntToStr(qmZnA)+'_'+IntToStr(qmZnB)
   else
   qmZnOut := IntToStr(qmZnB)+'_'+IntToStr(qmZnA);
   if (qmZnA>=0) and (qmZnA<256) then
   qmXcInv[qmZnA] := 1;
   if (qmZnB>=0) and (qmZnB<256) then
   qmXcInv[qmZnB] := 1;
end;

//! The position (text) of the participant of hunk row qmZoRow in the
//! `;`-joined participant list qmZoParts.
procedure qmZoPos(const qmZoRow : String; const qmZoParts : String; var qmZoOut : String);
begin
   var qmZoI : String;
   qmField(qmZoRow, '|', 2, qmZoI);
   qmField(qmZoParts, ';', StrToInt(qmZoI), qmZoOut);
end;

//! The number of part rows of job qmZpJs in parser qmZpP: hunk i is row 1+that+i.
function qmZpParts(const qmZpP : Integer; const qmZpJs : String) : Integer;
begin
   var qmZpR : Integer;
   Result := 0;
   for qmZpR:=0 to ParserGetIntValueByKeyByHandle(qmZpP, qmZpJs+'rows')-1 do
   if (SubStr(ParserGetValueByKeyByHandle(qmZpP, qmZpJs+'r'+IntToStr(qmZpR)), 1, 5)='part|') then
   Result := Result+1;
end;

//! The conflicts of job qmZqJ in parser qmZqP (participants qmZqParts) and
//! the duplicates of the changes that lost; qmZqOnly (`;`-joined, or '')
//! keeps the hunks of those positions alone (ref/conflicts.py
//! _merge_records), in hunk order, as conflict records of file plan qmZqM.
procedure qmZqMerge(const qmZqP : Integer; const qmZqJ : Integer; const qmZqParts : String; const qmZqOnly : String; const qmZqPath : String; const qmZqKind : String);
begin
   var qmZqJs : String = 'j'+IntToStr(qmZqJ);
   var qmZqNr : Integer = ParserGetIntValueByKeyByHandle(qmZqP, qmZqJs+'rows');
   var qmZqNp : Integer = qmZpParts(qmZqP, qmZqJs);
   var qmZqR : Integer;
   var qmZqD : Integer;
   var qmZqRow : String;
   var qmZqBy : String;
   var qmZqX : String;
   var qmZqI : String;
   var qmZqPa : String;
   var qmZqPb : String;
   var qmZqPd : String;
   var qmZqA : String;
   var qmZqB : String;
   var qmZqS : Integer;
   var qmZqE : Integer;
   var qmZqV : String;
   var qmZqRg : String;
   var qmZqQ : Integer;
   var qmZqWa : String;
   var qmZqWd : String;
   var qmZqCa : String;
   var qmZqCd : String;
   var qmZqDrop : String;
   var qmZqK : String;
   var qmZqN : String;
   var qmZqPk : String;
   for qmZqR:=0 to qmZqNr-1 do
   begin
      qmZqRow := ParserGetValueByKeyByHandle(qmZqP, qmZqJs+'r'+IntToStr(qmZqR));
      qmField(qmZqRow, '|', 6, qmZqV);
      if (SubStr(qmZqRow, 1, 5)='hunk|') and (qmZqV='conflict-lost') then
      begin
         qmZoPos(qmZqRow, qmZqParts, qmZqPd);
         if (qmZqOnly='') or (StrPos(';'+qmZqPd+';', ';'+qmZqOnly+';')>0) then
         begin
            qmField(qmZqRow, '|', 1, qmZqI);
            qmField(qmZqRow, '|', 7, qmZqBy);
            qmZqX := ParserGetValueByKeyByHandle(qmZqP, qmZqJs+'r'+IntToStr(1+qmZqNp+StrToInt(qmZqBy)));
            qmZoPos(qmZqX, qmZqParts, qmZqPa);
            qmField(qmZqRow, '|', 3, qmZqA);
            qmField(qmZqX, '|', 3, qmZqB);
            qmZqS := StrToInt(qmZqA);
            if (StrToInt(qmZqB)<qmZqS) then
            qmZqS := StrToInt(qmZqB);
            qmField(qmZqRow, '|', 4, qmZqA);
            qmField(qmZqX, '|', 4, qmZqB);
            qmZqE := StrToInt(qmZqA);
            if (StrToInt(qmZqB)>qmZqE) then
            qmZqE := StrToInt(qmZqB);
            qmRange(qmZqS, qmZqE, qmXcFirst, qmXcVn, qmZqRg);
            qmZxAsk(qmZqPath, qmZqS, qmZqE, qmZqQ);
            qmZcWho(StrToInt(qmZqPa), qmZqWa);
            qmZcWho(StrToInt(qmZqPd), qmZqWd);
            qmZmChange(qmZqX, qmZqCa);
            qmZmChange(qmZqRow, qmZqCd);
            qmZqDrop := qmZqWd+': '+qmZqCd;
            qmZbInc('xd'+qmZqPd+'_'+qmZqPa, 1);
            qmZnPair(StrToInt(qmZqPd), StrToInt(qmZqPa), qmZqPk);
            qmZbInc('xc'+qmZqPk, 1);
            qmZbInc('xw'+qmZqPk+'_'+qmZqPa, 1);
            for qmZqD:=0 to qmZqNr-1 do
            begin
               qmZqX := ParserGetValueByKeyByHandle(qmZqP, qmZqJs+'r'+IntToStr(qmZqD));
               qmField(qmZqX, '|', 6, qmZqV);
               qmField(qmZqX, '|', 7, qmZqB);
               if (SubStr(qmZqX, 1, 5)='hunk|') and (qmZqV='duplicate') and (qmZqB=qmZqI) then
               begin
                  qmZoPos(qmZqX, qmZqParts, qmZqN);
                  if (qmZqOnly='') or (StrPos(';'+qmZqN+';', ';'+qmZqOnly+';')>0) then
                  begin
                     qmZcWho(StrToInt(qmZqN), qmZqWd);
                     qmZqDrop := qmZqDrop+'; '+qmZqWd+': the same change';
                     qmZbInc('xd'+qmZqN+'_'+qmZqPa, 1);
                     qmZnPair(StrToInt(qmZqN), StrToInt(qmZqPa), qmZqPk);
                     qmZbInc('xc'+qmZqPk, 1);
                     qmZbInc('xw'+qmZqPk+'_'+qmZqPa, 1);
                  end;
               end;
            end;
            qmZqK := IntToStr(ParserGetIntValueByKeyByHandle(qmXcC, 'nsc') div 5+1);
            qmZdNum(StrToInt(qmZqPa), qmZqN);
            qmZyLine('sc', 'C'+qmZqK+' '+qmZqPath+', '+qmZqRg+', ', qmZqQ, 1);
            qmZyLine('sc', '   at: ', qmZqQ, 2);
            qmZaLine('sc', '   active: '+qmZqWa+': '+qmZqCa+'   dropped: '+qmZqDrop);
            qmZaLine('sc', '   why: '+qmZqN+' is later in the load order');
            qmZaLine('sc', '   kind: '+qmZqKind+' (by folder)');
         end;
      end;
   end;
end;

//! The pairs close together of job qmZrJ in parser qmZrP: both changes are in
//! the written file (ref/conflicts.py, the `written` merge).
procedure qmZrNear(const qmZrP : Integer; const qmZrJ : Integer; const qmZrParts : String; const qmZrPath : String; const qmZrKind : String);
begin
   var qmZrJs : String = 'j'+IntToStr(qmZrJ);
   var qmZrNr : Integer = ParserGetIntValueByKeyByHandle(qmZrP, qmZrJs+'rows');
   var qmZrNp : Integer = qmZpParts(qmZrP, qmZrJs);
   var qmZrR : Integer;
   var qmZrRow : String;
   var qmZrHa : String;
   var qmZrHb : String;
   var qmZrA : String;
   var qmZrB : String;
   var qmZrPa : String;
   var qmZrPb : String;
   var qmZrS : Integer;
   var qmZrE : Integer;
   var qmZrRa : String;
   var qmZrRb : String;
   var qmZrQ : Integer;
   var qmZrNa : String;
   var qmZrNb : String;
   var qmZrPk : String;
   for qmZrR:=0 to qmZrNr-1 do
   begin
      qmZrRow := ParserGetValueByKeyByHandle(qmZrP, qmZrJs+'r'+IntToStr(qmZrR));
      if (SubStr(qmZrRow, 1, 5)='prox|') then
      begin
         qmField(qmZrRow, '|', 1, qmZrA);
         qmField(qmZrRow, '|', 2, qmZrB);
         qmZrHa := ParserGetValueByKeyByHandle(qmZrP, qmZrJs+'r'+IntToStr(1+qmZrNp+StrToInt(qmZrA)));
         qmZrHb := ParserGetValueByKeyByHandle(qmZrP, qmZrJs+'r'+IntToStr(1+qmZrNp+StrToInt(qmZrB)));
         qmZoPos(qmZrHa, qmZrParts, qmZrPa);
         qmZoPos(qmZrHb, qmZrParts, qmZrPb);
         qmField(qmZrHa, '|', 3, qmZrA);
         qmField(qmZrHb, '|', 3, qmZrB);
         qmZrS := StrToInt(qmZrA);
         if (StrToInt(qmZrB)<qmZrS) then
         qmZrS := StrToInt(qmZrB);
         qmField(qmZrHa, '|', 4, qmZrA);
         qmField(qmZrHb, '|', 4, qmZrB);
         qmZrE := StrToInt(qmZrA);
         if (StrToInt(qmZrB)>qmZrE) then
         qmZrE := StrToInt(qmZrB);
         qmZxAsk(qmZrPath, qmZrS, qmZrE, qmZrQ);
         qmField(qmZrHa, '|', 3, qmZrA);
         qmField(qmZrHa, '|', 4, qmZrB);
         qmRange(StrToInt(qmZrA), StrToInt(qmZrB), qmXcFirst, qmXcVn, qmZrRa);
         qmField(qmZrHb, '|', 3, qmZrA);
         qmField(qmZrHb, '|', 4, qmZrB);
         qmRange(StrToInt(qmZrA), StrToInt(qmZrB), qmXcFirst, qmXcVn, qmZrRb);
         qmZdNum(StrToInt(qmZrPa), qmZrNa);
         qmZdNum(StrToInt(qmZrPb), qmZrNb);
         qmZyLine('sn', 'N'+IntToStr(ParserGetIntValueByKeyByHandle(qmXcC, 'nsn') div 4+1)+' '+qmZrPath+', ', qmZrQ, 1);
         qmZyLine('sn', '   at: ', qmZrQ, 2);
         qmZaLine('sn', '   '+qmZrNa+': '+qmZrRa+'   '+qmZrNb+': '+qmZrRb);
         qmZaLine('sn', '   kind: '+qmZrKind+' (by folder)');
         qmZnPair(StrToInt(qmZrPa), StrToInt(qmZrPb), qmZrPk);
         qmZbInc('xn'+qmZrPk, 1);
      end;
   end;
end;

//! A whole file: qmZsOwner's copy (position, -1 vanilla's), not used: the
//! positions qmZsOthers (`;`-joined) (ref/conflicts.py _whole).
procedure qmZsWhole(const qmZsPath : String; const qmZsOwner : Integer; const qmZsOthers : String; const qmZsWhy : String; const qmZsKind : String);
begin
   var qmZsK : Integer = 0;
   var qmZsL : Integer;
   var qmZsF : String;
   var qmZsG : String;
   var qmZsW : String;
   var qmZsList : String = '';
   var qmZsOwn : String = 'vanilla';
   var qmZsPk : String;
   if (qmZsOwner>=0) then
   qmZcWho(qmZsOwner, qmZsOwn);
   qmField(qmZsOthers, ';', 0, qmZsF);
   while (qmZsF<>'') do
   begin
      qmZcWho(StrToInt(qmZsF), qmZsW);
      if (qmZsList<>'') then
      qmZsList := qmZsList+', ';
      qmZsList := qmZsList+qmZsW;
      if (qmZsOwner>=0) then
      begin
         qmZnPair(StrToInt(qmZsF), qmZsOwner, qmZsPk);
         qmZbInc('xf'+qmZsPk, 1);
         qmZbInc('xo'+qmZsPk+'_'+IntToStr(qmZsOwner), 1);
      end
      else
      begin
         qmZsL := qmZsK+1;
         qmField(qmZsOthers, ';', qmZsL, qmZsG);
         while (qmZsG<>'') do
         begin
            qmZnPair(StrToInt(qmZsF), StrToInt(qmZsG), qmZsPk);
            qmZbInc('xf'+qmZsPk, 1);
            qmZbInc('xo'+qmZsPk+'_v', 1);
            qmZsL := qmZsL+1;
            qmField(qmZsOthers, ';', qmZsL, qmZsG);
         end;
      end;
      qmZsK := qmZsK+1;
      qmField(qmZsOthers, ';', qmZsK, qmZsF);
   end;
   qmZaLine('sw', '  '+qmZsPath+': '+qmZsOwn+'''s copy; not used: '+qmZsList+' ('+qmZsWhy+'; '+qmZsKind+')');
end;

//! The records of plan file qmZtM (ref/conflicts.py _path_records).
procedure qmZtPath(const qmZtM : Integer);
begin
   var qmZtMs : String = IntToStr(qmZtM);
   var qmZtP : String = ParserGetValueByKeyByHandle(qmXcPlan, 'path'+qmZtMs);
   var qmZtAct : String = ParserGetValueByKeyByHandle(qmXcPlan, 'act'+qmZtMs);
   var qmZtKind : String;
   var qmZtProv : String;
   var qmZtParts : String;
   var qmZtTier : String;
   var qmZtLo : String;
   var qmZtSub : String;
   var qmZtF : String;
   var qmZtWhy : String;
   var qmZtOth : String;
   var qmZtN : Integer;
   var qmZtK : Integer;
   var qmZtJ : Integer;
   var qmZtCnt : Integer;
   var qmZtOwner : Integer;
   var qmZtL : String;
   var qmZtW : String;
   var qmZtX : String;
   var qmZtR : Integer;
   var qmZtPk : String;
   var qmZtJs : String;
   var qmZtNp : Integer;
   var qmZtOp : String;
   qmZgKind(qmZtP, qmZtKind);
   if (qmZtAct='winner') then
   begin
      qmZtProv := ParserGetValueByKeyByHandle(qmXcPlan, 'prov'+qmZtMs);
      qmZtN := 0;
      qmField(qmZtProv, ';', 0, qmZtF);
      while (qmZtF<>'') do
      begin
         qmZtN := qmZtN+1;
         qmField(qmZtProv, ';', qmZtN, qmZtF);
      end;
      if (qmZtN>=2) then
      begin
         qmZtOth := '';
         for qmZtK:=0 to qmZtN-2 do
         begin
            qmField(qmZtProv, ';', qmZtK, qmZtF);
            if (qmZtOth<>'') then
            qmZtOth := qmZtOth+';';
            qmZtOth := qmZtOth+qmZtF;
         end;
         qmField(qmZtProv, ';', qmZtN-1, qmZtF);
         qmWinnerWhy(ParserGetValueByKeyByHandle(qmXcPlan, 'why'+qmZtMs), qmZtWhy);
         qmZsWhole(qmZtP, StrToInt(qmZtF), qmZtOth, qmZtWhy, qmZtKind);
      end;
   end
   else
   if (qmZtAct='merge-inc') or (qmZtAct='hook') then
   begin
      qmZtParts := ParserGetValueByKeyByHandle(qmXcG, 'pp'+qmZtMs);
      qmZtN := 0;
      qmField(qmZtParts, ';', 0, qmZtF);
      while (qmZtF<>'') do
      begin
         qmZtN := qmZtN+1;
         qmField(qmZtParts, ';', qmZtN, qmZtF);
      end;
      if (qmZtN>=2) then
      begin
         qmZtTier := ParserGetValueByKeyByHandle(qmXcG, 'r'+qmZtMs);
         qmZtJ := ParserGetIntValueByKeyByHandle(qmXcG, 'j'+qmZtMs);
         qmXcFirst := ParserGetIntValueByKeyByHandle(qmXcG, 'vf'+qmZtMs);
         qmXcVn := ParserGetIntValueByKeyByHandle(qmXcG, 'vn'+qmZtMs);
         if (SubStr(qmZtTier, 1, 6)='merged') or (SubStr(qmZtTier, 1, 6)='subset') then
         begin
            if (SubStr(qmZtTier, 1, 6)='subset') then
            begin
               qmZtLo := ParserGetValueByKeyByHandle(qmXcG, 'lo'+qmZtMs);
               // The subset's participants: every one but the left-out ones, in order.
               qmZtSub := '';
               for qmZtK:=0 to qmZtN-1 do
               begin
                  qmField(qmZtParts, ';', qmZtK, qmZtF);
                  if (StrPos(';'+qmZtF+';', ';'+qmZtLo+';')=0) then
                  begin
                     if (qmZtSub<>'') then
                     qmZtSub := qmZtSub+';';
                     qmZtSub := qmZtSub+qmZtF;
                  end;
               end;
               qmZqMerge(qmXcMg, qmZtJ, qmZtParts, qmZtLo, qmZtP, qmZtKind);
               if (qmXcMs<>0) then
               qmZqMerge(qmXcMs, ParserGetIntValueByKeyByHandle(qmXcG, 'sj'+qmZtMs), qmZtSub, '', qmZtP, qmZtKind);
               //! Left out: all of the mod's changes in the full merge.
               qmZtJs := 'j'+IntToStr(qmZtJ);
               qmZtNp := qmZpParts(qmXcMg, qmZtJs);
               qmZtK := 0;
               qmField(qmZtLo, ';', 0, qmZtL);
               while (qmZtL<>'') do
               begin
                  qmZtCnt := 0;
                  for qmZtR:=0 to ParserGetIntValueByKeyByHandle(qmXcMg, qmZtJs+'rows')-1 do
                  begin
                     qmZtX := ParserGetValueByKeyByHandle(qmXcMg, qmZtJs+'r'+IntToStr(qmZtR));
                     if (SubStr(qmZtX, 1, 5)='hunk|') then
                     begin
                        qmZoPos(qmZtX, qmZtParts, qmZtOp);
                        if (qmZtOp=qmZtL) then
                        qmZtCnt := qmZtCnt+1;
                     end;
                  end;
                  qmZcWho(StrToInt(qmZtL), qmZtW);
                  qmZfPlural(qmZtCnt, 'change', qmZtX);
                  qmZaLine('sl', '  '+qmZtP+': without '+qmZtW+' ('+qmZtX+'); the merged file does not compile, and it compiles without them');
                  if (ParserGetValueByKeyByHandle(qmXcC, 'dl'+qmZtL)='') then
                  ParserSetValueByKeyByHandle(qmXcC, 'dl'+qmZtL, qmZtP);
                  for qmZtR:=0 to qmZtN-1 do
                  begin
                     qmField(qmZtParts, ';', qmZtR, qmZtF);
                     if (StrPos(';'+qmZtF+';', ';'+qmZtLo+';')=0) then
                     begin
                        qmZnPair(StrToInt(qmZtL), StrToInt(qmZtF), qmZtPk);
                        qmZbInc('xl'+qmZtPk+'_'+qmZtL, 1);
                     end;
                  end;
                  qmZtK := qmZtK+1;
                  qmField(qmZtLo, ';', qmZtK, qmZtL);
               end;
               if (qmXcMs<>0) then
               qmZrNear(qmXcMs, ParserGetIntValueByKeyByHandle(qmXcG, 'sj'+qmZtMs), qmZtSub, qmZtP, qmZtKind);
            end
            else
            begin
               qmZqMerge(qmXcMg, qmZtJ, qmZtParts, '', qmZtP, qmZtKind);
               qmZrNear(qmXcMg, qmZtJ, qmZtParts, qmZtP, qmZtKind);
            end;
         end
         else
         begin
            //! One copy, or none: the winner's, or vanilla's with the hook lines.
            qmZtOwner := -1;
            if (SubStr(qmZtTier, 1, 7)<>'vanilla') then
            begin
               qmZtJs := 'j'+IntToStr(qmZtJ);
               qmZtX := '';
               if (qmZtJ>=0) and (qmXcMg<>0) and (ParserGetValueByKeyByHandle(qmXcG, 'e'+qmZtMs)='') then
               if (ParserGetValueByKeyByHandle(qmXcMg, qmZtJs+'mode')='winner') then
               qmZtX := ParserGetValueByKeyByHandle(qmXcMg, qmZtJs+'reason');
               if (qmZtX='too-different') then
               qmZtWhy := 'the copies differ too much to merge'
               else
               if (qmZtX='too-many-lines') then
               qmZtWhy := 'the file is too long to merge'
               else
               if (qmZtX='replacement') then
               qmZtWhy := 'a mod replaces most of the file'
               else
               if (ParserGetValueByKeyByHandle(qmXcG, 'e'+qmZtMs)<>'') then
               qmZtWhy := 'the merge failed'
               else
               if (SubStr(qmZtTier, 1, 6)='winner') then
               qmZtWhy := 'the merged file does not compile'
               else
               if (ParserGetValueByKeyByHandle(qmXcG, 'x'+qmZtMs)='wta') or (ParserGetValueByKeyByHandle(qmXcG, 'x'+qmZtMs)='wtahook') then
               qmZtWhy := 'not merged after a suspected start-up failure'
               else
               qmZtWhy := 'no candidate compiles';
               qmZtF := ParserGetValueByKeyByHandle(qmXcG, 'pw'+qmZtMs);
               if (qmZtF='') then
               qmField(qmZtParts, ';', qmZtN-1, qmZtF);
               qmZtOwner := StrToInt(qmZtF);
            end
            else
            qmZtWhy := 'neither the merge nor a mod''s copy compiles';
            qmZtOth := '';
            for qmZtK:=0 to qmZtN-1 do
            begin
               qmField(qmZtParts, ';', qmZtK, qmZtF);
               if (StrToInt(qmZtF)<>qmZtOwner) then
               begin
                  if (qmZtOth<>'') then
                  qmZtOth := qmZtOth+';';
                  qmZtOth := qmZtOth+qmZtF;
               end;
            end;
            qmZsWhole(qmZtP, qmZtOwner, qmZtOth, qmZtWhy, qmZtKind);
         end;
      end;
   end;
end;

//! One pair line (ref/conflicts.py _pair_line), '' for a pair without a record.
procedure qmZuPairLine(const qmZuA : Integer; const qmZuB : Integer; var qmZuOut : String);
begin
   var qmZuS : String = IntToStr(qmZuA)+'_'+IntToStr(qmZuB);
   var qmZuC : Integer = ParserGetIntValueByKeyByHandle(qmXcC, 'xc'+qmZuS);
   var qmZuN : Integer = ParserGetIntValueByKeyByHandle(qmXcC, 'xn'+qmZuS);
   var qmZuF : Integer = ParserGetIntValueByKeyByHandle(qmXcC, 'xf'+qmZuS);
   var qmZuLa : Integer = ParserGetIntValueByKeyByHandle(qmXcC, 'xl'+qmZuS+'_'+IntToStr(qmZuA));
   var qmZuLb : Integer = ParserGetIntValueByKeyByHandle(qmXcC, 'xl'+qmZuS+'_'+IntToStr(qmZuB));
   var qmZuK : Integer = ParserGetIntValueByKeyByHandle(qmXcC, 'xk'+qmZuS);
   var qmZuOa : Integer = ParserGetIntValueByKeyByHandle(qmXcC, 'xo'+qmZuS+'_'+IntToStr(qmZuA));
   var qmZuOb : Integer = ParserGetIntValueByKeyByHandle(qmXcC, 'xo'+qmZuS+'_'+IntToStr(qmZuB));
   var qmZuOv : Integer = ParserGetIntValueByKeyByHandle(qmXcC, 'xo'+qmZuS+'_v');
   var qmZuT : String;
   var qmZuNa : String;
   var qmZuNb : String;
   var qmZuD : Integer = 0;
   var qmZuL : String;
   qmZuOut := '';
   if (qmZuC>0) or (qmZuN>0) or (qmZuF>0) or (qmZuLa>0) or (qmZuLb>0) or (qmZuK>0) then
   begin
      qmZeName(qmZuA, qmZuNa);
      qmZeName(qmZuB, qmZuNb);
      qmZfPlural(qmZuC, 'conflict', qmZuOut);
      if (qmZuC>0) then
      qmZuOut := qmZuOut+' - '+qmZuNb+' active in '+IntToStr(ParserGetIntValueByKeyByHandle(qmXcC, 'xw'+qmZuS+'_'+IntToStr(qmZuB)))+', '+qmZuNa+' active in '+IntToStr(ParserGetIntValueByKeyByHandle(qmXcC, 'xw'+qmZuS+'_'+IntToStr(qmZuA)));
      qmZuOut := qmZuOut+'; '+IntToStr(qmZuN)+' close together (both active)';
      qmZfPlural(qmZuF, 'whole file', qmZuT);
      qmZuOut := qmZuOut+'; '+qmZuT;
      if (qmZuF>0) then
      begin
         if (qmZuOa>0) then
         qmZuD := qmZuD+1;
         if (qmZuOb>0) then
         qmZuD := qmZuD+1;
         if (qmZuOv>0) then
         qmZuD := qmZuD+1;
         qmZuL := '';
         if (qmZuOa>0) then
         begin
            qmZuL := qmZuNa;
            if (qmZuD>1) then
            qmZuL := qmZuL+' '+IntToStr(qmZuOa);
         end;
         if (qmZuOb>0) then
         begin
            if (qmZuL<>'') then
            qmZuL := qmZuL+', ';
            qmZuL := qmZuL+qmZuNb;
            if (qmZuD>1) then
            qmZuL := qmZuL+' '+IntToStr(qmZuOb);
         end;
         if (qmZuOv>0) then
         begin
            if (qmZuL<>'') then
            qmZuL := qmZuL+', ';
            qmZuL := qmZuL+'vanilla';
            if (qmZuD>1) then
            qmZuL := qmZuL+' '+IntToStr(qmZuOv);
         end;
         qmZuOut := qmZuOut+' ('+qmZuL+')';
      end;
      if (qmZuLa>0) then
      begin
         qmZfPlural(qmZuLa, 'file', qmZuT);
         qmZuOut := qmZuOut+'; '+qmZuNa+' left out of '+qmZuT;
      end;
      if (qmZuLb>0) then
      begin
         qmZfPlural(qmZuLb, 'file', qmZuT);
         qmZuOut := qmZuOut+'; '+qmZuNb+' left out of '+qmZuT;
      end;
      if (qmZuK>0) then
      begin
         qmZfPlural(qmZuK, 'core script', qmZuT);
         qmZuOut := qmZuOut+'; FAIL '+qmZuT+' both ship';
      end;
      qmZdNum(qmZuA, qmZuNa);
      qmZdNum(qmZuB, qmZuNb);
      qmZuOut := '  '+qmZuNa+' <-> '+qmZuNb+': '+qmZuOut;
   end;
end;

//! A line of conflicts.txt, straight to the open file (qmRawPutLine) when
//! there is a work folder to write it to.
var qmXcOpen : Boolean = False;
var qmXcAcc : Integer = 0;
var qmXcCnt : Integer = 0;
var qmXcNo : Integer = 0;
procedure qmZvOut(const qmZvS : String);
begin
   if (qmXcOpen) then
   qmRawPutLine(qmZvS, qmXcAcc, qmXcCnt);
   qmXcNo := qmXcNo+1;
end;

//! The lines of section qmZwSec into conflicts.txt, `  none` without one.
procedure qmZwSection(const qmZwHead : String; const qmZwSec : String);
begin
   var qmZwK : Integer;
   var qmZwN : Integer = ParserGetIntValueByKeyByHandle(qmXcC, 'n'+qmZwSec);
   var qmZwL : String;
   var qmZwQ : Integer;
   qmZvOut('');
   qmZvOut(qmZwHead);
   if (qmZwN=0) then
   qmZvOut('  none');
   for qmZwK:=0 to qmZwN-1 do
   begin
      qmZwL := ParserGetValueByKeyByHandle(qmXcC, qmZwSec+IntToStr(qmZwK));
      qmZwQ := ParserGetIntValueByKeyByHandle(qmXcC, 'q'+qmZwSec+IntToStr(qmZwK))-1;
      if (qmZwQ>=0) then
      begin
         if (ParserGetIntValueByKeyByHandle(qmXcC, 'k'+qmZwSec+IntToStr(qmZwK))=1) then
         qmZwL := qmZwL+ParserGetValueByKeyByHandle(qmXcC, 'rpl'+IntToStr(qmZwQ))
         else
         qmZwL := qmZwL+ParserGetValueByKeyByHandle(qmXcC, 'rat'+IntToStr(qmZwQ));
      end;
      qmZvOut(qmZwL);
   end;
end;

if (qmXcC=0) then
qmXcC := ParserCreate('qm_conf');
ParserClearByHandle(qmXcC);
if (qmXcG=0) or (qmXcPlan=0) or (qmXcMods=0) then
exit;
//! A SelfTest sandbox (qm_gen box) reports without the boot, as qmReport does.
if (ParserGetValueByKeyByHandle(qmXcG, 'box')<>'') then
qmXcBoot := 0;
qmXcNm := ParserGetIntValueByKeyByHandle(qmXcMods, 'n');
qmXcSelf := ParserGetIntValueByKeyByHandle(qmXcMods, 'self');
qmXcK := 0;
for qmXcM:=0 to qmXcNm-1 do
if (qmXcM<256) then
begin
   qmXcRk[qmXcM] := 0;
   qmXcInv[qmXcM] := 0;
   if (ParserGetIntValueByKeyByHandle(qmXcMods, 'on'+IntToStr(ParserGetIntValueByKeyByHandle(qmXcMods, 'ord'+IntToStr(qmXcM))))=1) then
   begin
      qmXcK := qmXcK+1;
      qmXcRk[qmXcM] := qmXcK;
   end;
end;

//! The boot's clashes between enabled mods: the lowest position with each dir.
var qmXcCa : Integer;
var qmXcCb : Integer;
var qmXcLa : String;
var qmXcLb : String;
var qmXcLd : String;
var qmXcPk : String;
if (qmXcBoot<>0) then
for qmXcK:=0 to ParserGetIntValueByKeyByHandle(qmXcBoot, 'gcn')-1 do
begin
   qmLowerAscii(ParserGetValueByKeyByHandle(qmXcBoot, 'gca'+IntToStr(qmXcK)), qmXcLa);
   qmLowerAscii(ParserGetValueByKeyByHandle(qmXcBoot, 'gcb'+IntToStr(qmXcK)), qmXcLb);
   qmXcCa := -1;
   qmXcCb := -1;
   for qmXcM:=qmXcNm-1 downto 0 do
   begin
      qmLowerAscii(ParserGetValueByKeyByHandle(qmXcMods, 'dir'+IntToStr(ParserGetIntValueByKeyByHandle(qmXcMods, 'ord'+IntToStr(qmXcM)))), qmXcLd);
      if (qmXcLd=qmXcLa) then
      qmXcCa := qmXcM;
      if (qmXcLd=qmXcLb) then
      qmXcCb := qmXcM;
   end;
   if (qmXcCa>=0) and (qmXcCb>=0) then
   begin
      if (qmXcCb<qmXcCa) then
      begin
         qmXcM := qmXcCa;
         qmXcCa := qmXcCb;
         qmXcCb := qmXcM;
      end;
      qmZcWho(qmXcCa, qmXcT);
      qmZcWho(qmXcCb, qmXcU);
      qmZaLine('sk', '  scripts\'+ParserGetValueByKeyByHandle(qmXcBoot, 'gcf'+IntToStr(qmXcK))+': '+qmXcT+' and '+qmXcU);
      qmZnPair(qmXcCa, qmXcCb, qmXcPk);
      qmZbInc('xk'+qmXcPk, 1);
   end;
end;

for qmXcM:=0 to ParserGetIntValueByKeyByHandle(qmXcPlan, 'n')-1 do
qmZtPath(qmXcM);

//! The pair lines, in load order.
var qmXcB : Integer;
var qmXcPn : Integer = 0;
for qmXcK:=0 to qmXcNm-1 do
if (qmXcK<256) then
if (qmXcInv[qmXcK]=1) then
for qmXcB:=qmXcK+1 to qmXcNm-1 do
if (qmXcB<256) then
if (qmXcInv[qmXcB]=1) then
begin
   qmZuPairLine(qmXcK, qmXcB, qmXcT);
   if (qmXcT<>'') then
   begin
      ParserSetValueByKeyByHandle(qmXcC, 'p'+IntToStr(qmXcPn), qmXcT);
      qmXcPn := qmXcPn+1;
   end;
end;

//! The window's share (ref/conflicts.py window): the pair lines, at most 14.
var qmXcWn : Integer = qmXcPn;
if (qmXcWn>14) then
qmXcWn := 14;
for qmXcK:=0 to qmXcWn-1 do
ParserSetValueByKeyByHandle(qmXcC, 'w'+IntToStr(qmXcK), ParserGetValueByKeyByHandle(qmXcC, 'p'+IntToStr(qmXcK)));
if (qmXcPn>14) then
begin
   ParserSetValueByKeyByHandle(qmXcC, 'w14', '  ... and '+IntToStr(qmXcPn-14)+' more pairs: see conflicts.txt');
   qmXcWn := 15;
end;
ParserSetIntValueByKeyByHandle(qmXcC, 'wn', qmXcWn);

//! A Details sentence per enabled mod (ref/conflicts.py details): the first
//! file it is left out of, else the mod it loses the most conflicts to, else
//! the one it wins the most over - the lower position on a tie.
var qmXcBest : Integer;
var qmXcAt : Integer;
var qmXcV : Integer;
for qmXcK:=0 to qmXcNm-1 do
if (qmXcK<256) then
if (qmXcRk[qmXcK]>0) then
begin
   qmXcT := ParserGetValueByKeyByHandle(qmXcC, 'dl'+IntToStr(qmXcK));
   if (qmXcT<>'') then
   qmXcT := 'Left out of '+qmXcT
   else
   begin
      qmXcBest := 0;
      qmXcAt := -1;
      for qmXcB:=0 to qmXcNm-1 do
      begin
         qmXcV := ParserGetIntValueByKeyByHandle(qmXcC, 'xd'+IntToStr(qmXcK)+'_'+IntToStr(qmXcB));
         if (qmXcV>qmXcBest) then
         begin
            qmXcBest := qmXcV;
            qmXcAt := qmXcB;
         end;
      end;
      if (qmXcAt>=0) then
      begin
         qmZfPlural(qmXcBest, 'conflict', qmXcU);
         qmZeName(qmXcAt, qmXcMs2);
         qmXcT := 'Loses '+qmXcU+' to '+qmXcMs2;
      end
      else
      begin
         for qmXcB:=0 to qmXcNm-1 do
         begin
            qmXcV := ParserGetIntValueByKeyByHandle(qmXcC, 'xd'+IntToStr(qmXcB)+'_'+IntToStr(qmXcK));
            if (qmXcV>qmXcBest) then
            begin
               qmXcBest := qmXcV;
               qmXcAt := qmXcB;
            end;
         end;
         if (qmXcAt>=0) then
         begin
            qmZfPlural(qmXcBest, 'conflict', qmXcU);
            qmZeName(qmXcAt, qmXcMs2);
            qmXcT := 'Wins '+qmXcU+' over '+qmXcMs2;
         end;
      end;
   end;
   if (qmXcT<>'') then
   ParserSetValueByKeyByHandle(qmXcC, 'd'+IntToStr(qmXcK), qmXcT);
end;

//! The asks answered, then conflicts.txt (ref/conflicts.py report_lines).
if (ParserGetIntValueByKeyByHandle(qmXcC, 'rn')>0) then
StateMachineExecuteState(GetTriggerManagerStateMachineHandle('qm_core'), 'qmConflictsCode', 0);
qmXcT := ParserGetValueByKeyByHandle(qmXcG, 'work');
if (qmXcT<>'') then
begin
   OpenFileStreamForWrite(qmXcT+'conflicts.txt');
   qmXcOpen := True;
end;
qmZvOut('Quartermaster conflict report');
qmZvOut('format 1, Quartermaster '+${version}+', generation '+IntToStr(ParserGetIntValueByKeyByHandle(qmXcG, 'gen'))+', outputs hash '+ParserGetValueByKeyByHandle(qmXcG, 'outhash'));
qmZvOut('rule: where two mods change the same lines, the mod later in the load order wins.');
qmZvOut('      Move a mod up or down in Quartermaster''s window to change the winner.');
qmZvOut('');
qmZvOut('Load order (enabled mods):');
for qmXcK:=0 to qmXcNm-1 do
if (qmXcK<256) then
if (qmXcRk[qmXcK]>0) then
begin
   qmZcWho(qmXcK, qmXcT);
   qmXcM := ParserGetIntValueByKeyByHandle(qmXcMods, 'ord'+IntToStr(qmXcK));
   if (qmXcM=qmXcSelf) and (ParserGetValueByKeyByHandle(qmXcMods, 'tit'+IntToStr(qmXcM))='') then
   qmXcT := qmXcT+' (Quartermaster)';
   qmZvOut('  '+qmXcT);
end;
qmZvOut('');
qmZvOut('Pairs:');
if (qmXcPn=0) then
qmZvOut('  none');
for qmXcK:=0 to qmXcPn-1 do
qmZvOut(ParserGetValueByKeyByHandle(qmXcC, 'p'+IntToStr(qmXcK)));
qmZwSection('Core scripts (only one copy loads; the game may not start with both):', 'sk');
qmZwSection('Conflicts (one version is active, the other is dropped):', 'sc');
qmZwSection('Files written without a mod (all its changes in the file are dropped):', 'sl');
qmZwSection('Close together (both changes are active; check they do not fix the same thing twice):', 'sn');
qmZwSection('Whole files (one copy is used, the other copies are not):', 'sw');
if (qmXcOpen) then
qmRawClose(qmXcAcc, qmXcCnt);
qmLog('conflicts pairs='+IntToStr(qmXcPn)+' conflicts='+IntToStr(ParserGetIntValueByKeyByHandle(qmXcC, 'nsc') div 5)+' close='+IntToStr(ParserGetIntValueByKeyByHandle(qmXcC, 'nsn') div 4)+' whole='+IntToStr(ParserGetIntValueByKeyByHandle(qmXcC, 'nsw'))+' core='+IntToStr(ParserGetIntValueByKeyByHandle(qmXcC, 'nsk'))+' lines='+IntToStr(qmXcNo));
