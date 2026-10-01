state: qmReport
into: data/quartermaster/core.aix
helpers: qmlog, qmstr, qmraw, qmrepcfg, qmreptext
requires:
---
//! The generation report (plan G13); ref/report.py is the twin and shows the
//! layout line by line. qmGenerate runs it last. It reads qm_gen, qm_plan,
//! qm_mods and the merge rows in qm_mg, and writes
//!   - <work>report.txt (work: qm_gen `work`, <save>\quartermaster\ or a
//!     SelfTest sandbox): plain English, CRLF, the raw writer's bytes; every
//!     line goes through qmEscape first, because a mod folder's name may hold
//!     any byte;
//!   - the named parser qm_report for the manager window (docs/ui.md): lines,
//!     l<k>, per enabled mod n, dir<j>, st<j>, why<j>, cn<j>, c<j>_<k>, and
//!     the report by mod mlines, m<k> (the window's Report view); saved as
//!     <work>report.cfg for qmReportLoad (qmRepCfgSave);
//!   - one [qm] line with the overall status.
//! The boot runs it after qmGenerate and may add a block first: the named
//! parser qm_boot (n, l<k> ready-made lines, st their worst tag, newn and
//! new<k> the dirs of new mods, whose record reads NEW while all is OK, gcn
//! and gca<k> gcb<k> gcf<k> the clashes between enabled mods, which also go
//! into both mods' blocks of the report by mod).
//! That block describes the boot's own generation. A SelfTest sandbox
//! generation (qm_gen box, the label) reports without it.
//! No timestamps and no timings, so the same inputs give the same bytes (plan
//! S12). Status tags are the words OK, WARN, FAIL, FATAL: the game's fonts
//! have no check mark or cross.
var qmReG : Integer = ParserSelectByKey('qm_gen');
var qmRePlan : Integer = ParserSelectByKey('qm_plan');
var qmReMods : Integer = ParserSelectByKey('qm_mods');
var qmReMg : Integer = ParserSelectByKey('qm_mg');
var qmReRep : Integer = ParserSelectByKey('qm_report');
var qmReL : Integer = 0;
var qmReN : Integer = 0;
var qmReNm : Integer = 0;
var qmReSelf : Integer = -1;
var qmReM : Integer;
var qmReK : Integer;
var qmReI : Integer;
var qmReJ : Integer;
var qmReR : Integer;
var qmReNp : Integer;
var qmReNr : Integer;
var qmReFirst : Integer;
var qmReVn : Integer;
var qmReTag : String;
var qmReMs : String;
var qmReJs : String;
var qmReS : String;
var qmReT : String;
var qmReU : String;
var qmReV : String;
var qmReW : String;
var qmReX : String;
var qmReA : String;
var qmReB : String;
var qmRePp : String;
var qmReAct : String;
var qmReRow : String;
var qmReAcc : Integer = 0;
var qmReCnt : Integer = 0;
var qmReE : String;
var qmReCn : Integer;
var qmReRec : Integer;
var qmReBoot : Integer = ParserSelectByKey('qm_boot');
var qmReBn : Integer = 0;
var qmReML : Integer = 0;
var qmReNf : Integer;
var qmReNb : Integer;
var qmReFb : Integer;
var qmReLs : Integer = -1;
var qmReKs : String;
var qmReCl : Integer;
var qmReRk : array [0..255] of Integer;

procedure qmReAdd(const qmQaS : String);
begin
   ParserSetValueByKeyByHandle(qmReRep, 'l'+IntToStr(qmReL), qmQaS);
   qmReL := qmReL+1;
end;

//! A line of the report by mod (qm_report m<k>).
procedure qmReMAdd(const qmQzS : String);
begin
   ParserSetValueByKeyByHandle(qmReRep, 'm'+IntToStr(qmReML), qmQzS);
   qmReML := qmReML+1;
end;

//! The mod at load position qmQwPos (text), as ref/report.py _who names it:
//! `<k>. <title> (<Workshop number or dir>)`, or `<k>. <dir>` when it has no
//! title (qm_mods tit<i>, qmModList), `<k>` its place on the Active list
//! (qmReRk). Until 2026-09-30 it was the dir alone, which for a Workshop
//! mod is only its folder number; until 2026-10-01 `<k>` was the position+1.
procedure qmReWho(const qmQwPos : String; var qmQwOut : String);
begin
   // The place on the Active list (qmReRk), no number for a mod that is off.
   var qmQwN : Integer = 0;
   if (StrToInt(qmQwPos)<256) then
   qmQwN := qmReRk[StrToInt(qmQwPos)];
   qmWho(qmQwPos, qmReMods, qmQwN, qmQwOut);
end;

//! The boot's clashes of the mod with index qmQcI (qm_boot gcn, gca<k>,
//! gcb<k>, gcf<k>, written by qmBoot; ref/report.py _clash_lines): how many,
//! and with qmQcAdd their lines in its block of the report by mod, the other
//! mod named as qmReWho names it. Until 2026-10-01 only the Boot block told
//! of a clash, and both mods' own blocks read OK while the window marked them
//! FAIL (run look-wsZ).
procedure qmReClash(const qmQcI : Integer; const qmQcAdd : Boolean; var qmQcN : Integer);
begin
   var qmQcK : Integer;
   var qmQcP : Integer;
   var qmQcMe : String;
   var qmQcA : String;
   var qmQcB : String;
   var qmQcO : String;
   var qmQcW : String;
   qmQcN := 0;
   if (qmReBoot<>0) then
   begin
      qmLowerAscii(ParserGetValueByKeyByHandle(qmReMods, 'dir'+IntToStr(qmQcI)), qmQcMe);
      for qmQcK:=0 to ParserGetIntValueByKeyByHandle(qmReBoot, 'gcn')-1 do
      begin
         qmLowerAscii(ParserGetValueByKeyByHandle(qmReBoot, 'gca'+IntToStr(qmQcK)), qmQcA);
         qmLowerAscii(ParserGetValueByKeyByHandle(qmReBoot, 'gcb'+IntToStr(qmQcK)), qmQcB);
         qmQcO := '';
         if (qmQcA=qmQcMe) then
         qmQcO := ParserGetValueByKeyByHandle(qmReBoot, 'gcb'+IntToStr(qmQcK))
         else
         if (qmQcB=qmQcMe) then
         qmQcO := ParserGetValueByKeyByHandle(qmReBoot, 'gca'+IntToStr(qmQcK));
         if (qmQcO<>'') then
         begin
            qmQcN := qmQcN+1;
            if (qmQcAdd) then
            begin
               // The lowest position with that dir, as the twin's first match.
               qmQcW := qmQcO;
               qmLowerAscii(qmQcO, qmQcA);
               for qmQcP:=qmReNm-1 downto 0 do
               begin
                  qmLowerAscii(ParserGetValueByKeyByHandle(qmReMods, 'dir'+IntToStr(ParserGetIntValueByKeyByHandle(qmReMods, 'ord'+IntToStr(qmQcP)))), qmQcB);
                  if (qmQcB=qmQcA) then
                  qmReWho(IntToStr(qmQcP), qmQcW);
               end;
               qmReMAdd('  FAIL scripts\'+ParserGetValueByKeyByHandle(qmReBoot, 'gcf'+IntToStr(qmQcK))+': '+qmQcW+' ships it too: only one copy loads, and the game may not start with both');
            end;
         end;
      end;
   end;
end;

//! A hunk's vanilla range [start, end) as text (ref/report.py rng).
//! The mod that made hunk row qmQhRow: its participant index is field 2.
procedure qmReHunkMod(const qmQhRow : String; const qmQhParts : String; var qmQhOut : String);
begin
   var qmQhI : String;
   var qmQhP : String;
   qmField(qmQhRow, '|', 2, qmQhI);
   qmField(qmQhParts, ';', StrToInt(qmQhI), qmQhP);
   qmReWho(qmQhP, qmQhOut);
end;

//! The canonical position (text) of the mod that made hunk row qmQpRow.
procedure qmReHunkPos(const qmQpRow : String; const qmQpParts : String; var qmQpOut : String);
begin
   var qmQpI : String;
   qmField(qmQpRow, '|', 2, qmQpI);
   qmField(qmQpParts, ';', StrToInt(qmQpI), qmQpOut);
end;

procedure qmReHunkRange(const qmQgRow : String; var qmQgOut : String);
begin
   var qmQgA : String;
   var qmQgB : String;
   qmField(qmQgRow, '|', 3, qmQgA);
   qmField(qmQgRow, '|', 4, qmQgB);
   qmRange(StrToInt(qmQgA), StrToInt(qmQgB), qmReFirst, qmReVn, qmQgOut);
end;

function qmReRank(const qmQkTag : String) : Integer;
begin
   Result := 0;
   if (qmQkTag='WARN') then
   Result := 1;
   if (qmQkTag='FAIL') then
   Result := 2;
   if (qmQkTag='FATAL') then
   Result := 3;
end;

procedure qmReDecision(const qmQdAct : String; const qmQdWhy : String; var qmQdOut : String);
begin
   qmQdOut := qmQdAct;
   if (qmQdAct='skip') then
   qmQdOut := 'one mod ships this file; the game uses that copy';
   if (qmQdAct='merge-inc') then
   qmQdOut := 'merge (a script file on the merge list)';
   if (qmQdAct='merge-data') then
   qmQdOut := 'merge by records (a data file with a record profile)';
   if (qmQdAct='hook') then
   qmQdOut := 'Quartermaster''s hook file: its hook lines are always merged in';
   if (qmQdAct='winner') then
   begin
      qmWinnerWhy(qmQdWhy, qmQdOut);
      qmQdOut := 'winner takes all: '+qmQdOut;
   end;
end;

procedure qmReResult(const qmQcCode : String; var qmQcOut : String);
begin
   qmQcOut := '';
   if (qmQcCode='merged') then
   qmQcOut := 'the merged file was written';
   if (qmQcCode='gaveup') then
   qmQcOut := 'not merged: the copies differ too much to merge; the copy of the last mod in load order was written, as the game alone would load it';
   if (qmQcCode='mergeerr') then
   qmQcOut := 'the merge failed; the winner''s copy was written';
   if (qmQcCode='fallback') then
   qmQcOut := 'the first candidate does not compile; the next one that does was written';
   if (qmQcCode='partial') then
   qmQcOut := 'the merged file does not compile; merged again without the mods whose changes lost a conflict, and that was written';
   if (qmQcCode='none') then
   qmQcOut := 'no candidate compiles; nothing was written, the game uses the winner''s copy as it is';
   if (qmQcCode='hooked') then
   qmQcOut := 'written with Quartermaster''s hook lines';
   if (qmQcCode='fatal') then
   qmQcOut := 'even vanilla with Quartermaster''s hook lines does not compile; nothing was written';
   if (qmQcCode='nohook') then
   qmQcOut := 'Quartermaster''s own copy of its hook lines is missing; nothing was written for this file';
   if (qmQcCode='writefail') then
   qmQcOut := 'the file compiles but was not written';
   if (qmQcCode='datafail') then
   qmQcOut := 'the merged records failed a check; nothing was written, the game uses the winner''s copy as it is';
   if (qmQcCode='wta') then
   qmQcOut := 'the last generation may have kept the game from starting; nothing was merged, the game uses the winner''s copy as it is';
   if (qmQcCode='wtahook') then
   qmQcOut := 'written with Quartermaster''s hook lines only; nothing was merged, because the last generation may have kept the game from starting';
end;

procedure qmReShort(const qmQsCode : String; var qmQsOut : String);
begin
   qmQsOut := qmQsCode;
   if (qmQsCode='winner') then
   qmQsOut := 'winner takes all';
   if (qmQsCode='merged') or (qmQsCode='hooked') then
   qmQsOut := 'merged; a later mod''s change replaced some of its changes';
   if (qmQsCode='gaveup') then
   qmQsOut := 'not merged, the last mod''s copy is used';
   if (qmQsCode='mergeerr') then
   qmQsOut := 'the merge failed';
   if (qmQsCode='fallback') then
   qmQsOut := 'the first candidate does not compile';
   if (qmQsCode='partial') then
   qmQsOut := 'merged without the mods whose changes lost a conflict';
   if (qmQsCode='none') then
   qmQsOut := 'no candidate compiles';
   if (qmQsCode='fatal') then
   qmQsOut := 'vanilla with the hook lines does not compile';
   if (qmQsCode='nohook') then
   qmQsOut := 'the hook lines are missing';
   if (qmQsCode='writefail') then
   qmQsOut := 'not written';
   if (qmQsCode='datafail') then
   qmQsOut := 'the records were not merged, the last mod''s copy is used';
   if (qmQsCode='wta') or (qmQsCode='wtahook') then
   qmQsOut := 'not merged after a suspected start-up failure';
end;

//! Plan file qmQtM's tag for the mod at canonical position qmQtK (text;
//! ref/report.py mod_status): a mod whose own changes all went in lost
//! nothing - one the written subset keeps, the winner when its own copy
//! (with or without the hook lines) was written after the merge failed.
procedure qmReModSt(const qmQtM : String; const qmQtK : String; var qmQtOut : String);
begin
   var qmQtX : String = ParserGetValueByKeyByHandle(qmReG, 'x'+qmQtM);
   var qmQtR : String;
   qmQtOut := ParserGetValueByKeyByHandle(qmReG, 's'+qmQtM);
   if (qmQtX='partial') then
   begin
      if (StrPos(';'+qmQtK+';', ';'+ParserGetValueByKeyByHandle(qmReG, 'lo'+qmQtM)+';')>0) then
      qmQtOut := 'WARN'
      else
      qmQtOut := 'OK';
   end
   else
   if (qmQtX='fallback') and (ParserGetValueByKeyByHandle(qmReG, 'pw'+qmQtM)=qmQtK) then
   begin
      qmQtR := ParserGetValueByKeyByHandle(qmReG, 'r'+qmQtM);
      if (SubStr(qmQtR, 1, 6)='winner') then
      qmQtOut := 'OK';
   end;
end;

//! qmReShort of plan file qmQvM, seen from the mod at position qmQvK
//! (ref/report.py mod_short).
procedure qmReModShort(const qmQvM : String; const qmQvK : String; var qmQvOut : String);
begin
   if (ParserGetValueByKeyByHandle(qmReG, 'x'+qmQvM)='partial') and (StrPos(';'+qmQvK+';', ';'+ParserGetValueByKeyByHandle(qmReG, 'lo'+qmQvM)+';')>0) then
   qmQvOut := 'its changes are left out: they lost a conflict'
   else
   // A hook file whose merge gave up holds the last mod's copy: nothing was
   // merged, so nothing was replaced (ref/report.py mod_short).
   if (ParserGetValueByKeyByHandle(qmReG, 'x'+qmQvM)='hooked') and (ParserGetIntValueByKeyByHandle(qmReG, 'j'+qmQvM)>=0) and (ParserGetValueByKeyByHandle(qmReMg, 'j'+IntToStr(ParserGetIntValueByKeyByHandle(qmReG, 'j'+qmQvM))+'mode')='winner') then
   qmQvOut := 'not merged, the last mod''s copy is used'
   else
   qmReShort(ParserGetValueByKeyByHandle(qmReG, 'x'+qmQvM), qmQvOut);
end;

//! What became of plan file qmQoM for the mod at canonical position qmQoK
//! (text), in the report by mod (ref/report.py mod_how).
procedure qmReHow(const qmQoM : String; const qmQoK : String; var qmQoOut : String);
begin
   var qmQoAct : String = ParserGetValueByKeyByHandle(qmRePlan, 'act'+qmQoM);
   var qmQoWin : String = ParserGetValueByKeyByHandle(qmRePlan, 'win'+qmQoM);
   var qmQoW : String;
   var qmQoWho : String;
   var qmQoI : Integer = 0;
   var qmQoP : String;
   if (qmQoAct='skip') then
   qmQoOut := 'used as it is; no other mod ships it'
   else
   if (qmQoAct='winner') then
   begin
      qmWinnerWhy(ParserGetValueByKeyByHandle(qmRePlan, 'why'+qmQoM), qmQoW);
      if (qmQoWin=qmQoK) then
      qmQoOut := 'winner takes all ('+qmQoW+'); this mod''s copy is used'
      else
      begin
         qmReWho(qmQoWin, qmQoWho);
         qmQoOut := 'winner takes all ('+qmQoW+'); '+qmQoWho+' wins, this mod''s copy is not used';
      end;
   end
   else
   if (ParserGetValueByKeyByHandle(qmReG, 'x'+qmQoM)='partial') then
   begin
      //! The subset was written: seen from a loser, or from a mod that stayed.
      qmQoW := ParserGetValueByKeyByHandle(qmReG, 'lo'+qmQoM);
      if (StrPos(';'+qmQoK+';', ';'+qmQoW+';')>0) then
      qmQoOut := 'this mod''s changes are left out: some of them lost a conflict, and the file does not compile with the rest'
      else
      begin
         qmQoOut := 'merged without ';
         qmField(qmQoW, ';', 0, qmQoP);
         while (qmQoP<>'') do
         begin
            qmReWho(qmQoP, qmQoWho);
            if (qmQoI>0) then
            qmQoOut := qmQoOut+', ';
            qmQoOut := qmQoOut+qmQoWho;
            qmQoI := qmQoI+1;
            qmField(qmQoW, ';', qmQoI, qmQoP);
         end;
      end;
   end
   else
   if (ParserGetValueByKeyByHandle(qmReG, 'x'+qmQoM)='fallback') and (ParserGetIntValueByKeyByHandle(qmReG, 't'+qmQoM)>0) then
   begin
      //! The validator refused the first candidate; the one written is the
      //! last one tried (field 0 of a try row is its tier).
      qmField(ParserGetValueByKeyByHandle(qmReG, 't'+qmQoM+'_'+IntToStr(ParserGetIntValueByKeyByHandle(qmReG, 't'+qmQoM)-1)), '|', 0, qmQoW);
      qmQoOut := 'the merged file does not compile; written instead: the '+qmQoW+' candidate';
      qmQoWin := ParserGetValueByKeyByHandle(qmReG, 'pw'+qmQoM);
      if (SubStr(qmQoW, 1, 6)='winner') and (qmQoWin<>'') then
      begin
         qmReWho(qmQoWin, qmQoWho);
         qmQoOut := qmQoOut+' of '+qmQoWho;
      end;
   end
   else
   begin
      qmReResult(ParserGetValueByKeyByHandle(qmReG, 'x'+qmQoM), qmQoOut);
      if (qmQoOut='') then
      qmQoOut := ParserGetValueByKeyByHandle(qmReG, 'x'+qmQoM);
   end;
end;

//! The conflicts and near edits of merged plan file qmQmM that involve the
//! mod at canonical position qmQmK (text): the file lines of the report,
//! seen from that mod (ref/report.py _mod_merge_lines).
procedure qmReModMerge(const qmQmM : String; const qmQmK : String);
begin
   var qmQmJ : Integer = ParserGetIntValueByKeyByHandle(qmReG, 'j'+qmQmM);
   var qmQmJs : String = 'j'+IntToStr(qmQmJ);
   var qmQmGo : Boolean = (qmQmJ>=0) and (qmReMg<>0);
   if (qmQmGo) then
   qmQmGo := (ParserGetValueByKeyByHandle(qmReG, 'e'+qmQmM)='') and (ParserGetValueByKeyByHandle(qmReMg, qmQmJs+'mode')='merged');
   if (qmQmGo) then
   begin
      var qmQmPp : String = ParserGetValueByKeyByHandle(qmReG, 'pp'+qmQmM);
      var qmQmNr : Integer = ParserGetIntValueByKeyByHandle(qmReMg, qmQmJs+'rows');
      var qmQmNp : Integer = 0;
      var qmQmR : Integer;
      var qmQmRow : String;
      var qmQmX : String;
      var qmQmS : String;
      var qmQmT : String;
      var qmQmA : String;
      var qmQmB : String;
      var qmQmPa : String;
      var qmQmPb : String;
      var qmQmWho : String;
      qmReFirst := ParserGetIntValueByKeyByHandle(qmReG, 'vf'+qmQmM);
      qmReVn := ParserGetIntValueByKeyByHandle(qmReG, 'vn'+qmQmM);
      for qmQmR:=0 to qmQmNr-1 do
      if (SubStr(ParserGetValueByKeyByHandle(qmReMg, qmQmJs+'r'+IntToStr(qmQmR)), 1, 5)='part|') then
      qmQmNp := qmQmNp+1;
      for qmQmR:=0 to qmQmNr-1 do
      begin
         qmQmRow := ParserGetValueByKeyByHandle(qmReMg, qmQmJs+'r'+IntToStr(qmQmR));
         qmField(qmQmRow, '|', 6, qmQmS);
         if (SubStr(qmQmRow, 1, 5)='hunk|') and (qmQmS='conflict-lost') then
         begin
            qmField(qmQmRow, '|', 7, qmQmT);
            qmQmX := ParserGetValueByKeyByHandle(qmReMg, qmQmJs+'r'+IntToStr(1+qmQmNp+StrToInt(qmQmT)));
            qmReHunkRange(qmQmRow, qmQmA);
            qmReHunkPos(qmQmRow, qmQmPp, qmQmPa);
            qmReHunkPos(qmQmX, qmQmPp, qmQmPb);
            if (qmQmPa=qmQmK) then
            begin
               qmReWho(qmQmPb, qmQmWho);
               qmReMAdd('    conflict: '+qmQmA+': this mod''s change lost to '+qmQmWho);
            end
            else
            if (qmQmPb=qmQmK) then
            begin
               qmReWho(qmQmPa, qmQmWho);
               qmReMAdd('    conflict: '+qmQmA+': this mod''s change kept over '+qmQmWho);
            end;
         end;
      end;
      for qmQmR:=0 to qmQmNr-1 do
      begin
         qmQmRow := ParserGetValueByKeyByHandle(qmReMg, qmQmJs+'r'+IntToStr(qmQmR));
         if (SubStr(qmQmRow, 1, 5)='prox|') then
         begin
            qmField(qmQmRow, '|', 1, qmQmS);
            qmField(qmQmRow, '|', 2, qmQmT);
            qmQmX := ParserGetValueByKeyByHandle(qmReMg, qmQmJs+'r'+IntToStr(1+qmQmNp+StrToInt(qmQmS)));
            qmQmRow := ParserGetValueByKeyByHandle(qmReMg, qmQmJs+'r'+IntToStr(1+qmQmNp+StrToInt(qmQmT)));
            qmReHunkRange(qmQmX, qmQmA);
            qmReHunkRange(qmQmRow, qmQmB);
            qmReHunkPos(qmQmX, qmQmPp, qmQmPa);
            qmReHunkPos(qmQmRow, qmQmPp, qmQmPb);
            if (qmQmPa=qmQmK) then
            begin
               qmReWho(qmQmPb, qmQmWho);
               qmReMAdd('    near: '+qmQmA+' and '+qmQmB+' of '+qmQmWho);
            end
            else
            if (qmQmPb=qmQmK) then
            begin
               qmReWho(qmQmPa, qmQmWho);
               qmReMAdd('    near: '+qmQmB+' and '+qmQmA+' of '+qmQmWho);
            end;
         end;
      end;
   end;
end;

if (qmReG=0) or (qmRePlan=0) or (qmReMods=0) then
begin
   qmLog('report: no generation to report');
   exit;
end;
//! qmBoot fills qm_boot before it runs the SelfTest, so a sandbox generation
//! would otherwise print the live boot's lines and NEW marks in a report its
//! twin makes without them (runs m4a, m4c).
if (ParserGetValueByKeyByHandle(qmReG, 'box')<>'') then
qmReBoot := 0;
if (qmReRep=0) then
qmReRep := ParserCreate('qm_report');
ParserClearByHandle(qmReRep);
qmReN := ParserGetIntValueByKeyByHandle(qmReG, 'n');
qmReNm := ParserGetIntValueByKeyByHandle(qmReMods, 'n');
qmReSelf := ParserGetIntValueByKeyByHandle(qmReMods, 'self');
//! A mod's number is its place on the window's Active list - the
//! enabled mods in load order, from 1 (ref/report.py Dirs.ranks); 0 for one
//! that is off. qmReWho reads it.
qmReCl := 0;
for qmReK:=0 to qmReNm-1 do
if (qmReK<256) then
begin
   qmReRk[qmReK] := 0;
   if (ParserGetIntValueByKeyByHandle(qmReMods, 'on'+IntToStr(ParserGetIntValueByKeyByHandle(qmReMods, 'ord'+IntToStr(qmReK))))=1) then
   begin
      qmReCl := qmReCl+1;
      qmReRk[qmReK] := qmReCl;
   end;
end;
//! The conflict report first (qmConflicts; ref/conflicts.py): it writes
//! conflicts.txt, its pair lines open the report by mod, and its Details
//! sentences go to cpd<j> (qm_conf w<k>, d<position>).
var qmReT0 : Float = _misc_GetRealTime;
StateMachineExecuteState(GetTriggerManagerStateMachineHandle('qm_core'), 'qmConflicts', 0);
var qmReConf : Integer = ParserSelectByKey('qm_conf');
qmLog('report conflicts ms='+FloatToStr((_misc_GetRealTime-qmReT0)*1000));
qmReTag := 'OK';
for qmReM:=0 to qmReN-1 do
begin
   qmReS := ParserGetValueByKeyByHandle(qmReG, 's'+IntToStr(qmReM));
   if (qmReRank(qmReS)>qmReRank(qmReTag)) then
   qmReTag := qmReS;
end;
if (qmReBoot<>0) then
qmReBn := ParserGetIntValueByKeyByHandle(qmReBoot, 'n');
if (qmReBn>0) then
begin
   qmReS := ParserGetValueByKeyByHandle(qmReBoot, 'st');
   if (qmReRank(qmReS)>qmReRank(qmReTag)) then
   qmReTag := qmReS;
end;
if (ParserGetValueByKeyByHandle(qmReG, 'status')='fatal') then
qmReTag := 'FATAL';
qmReAdd('Quartermaster report');
qmReAdd('generation '+IntToStr(ParserGetIntValueByKeyByHandle(qmReG, 'gen'))+', outputs hash '+ParserGetValueByKeyByHandle(qmReG, 'outhash'));
qmReAdd('status '+qmReTag+': '+IntToStr(ParserGetIntValueByKeyByHandle(qmReG, 'written')+ParserGetIntValueByKeyByHandle(qmReG, 'same'))+' files in place, '+IntToStr(ParserGetIntValueByKeyByHandle(qmReG, 'failed'))+' failed, '+IntToStr(ParserGetIntValueByKeyByHandle(qmReG, 'removed'))+' removed');
if (qmReBn>0) then
begin
   qmReAdd('');
   qmReAdd('Boot:');
   for qmReK:=0 to qmReBn-1 do
   qmReAdd('  '+ParserGetValueByKeyByHandle(qmReBoot, 'l'+IntToStr(qmReK)));
end;
qmReAdd('');
qmReAdd('Mods in load order:');
for qmReK:=0 to qmReNm-1 do
begin
   qmReI := ParserGetIntValueByKeyByHandle(qmReMods, 'ord'+IntToStr(qmReK));
   if (ParserGetIntValueByKeyByHandle(qmReMods, 'on'+IntToStr(qmReI))=1) then
   begin
      qmReWho(IntToStr(qmReK), qmReS);
      if (qmReI=qmReSelf) then
      if (ParserGetValueByKeyByHandle(qmReMods, 'tit'+IntToStr(qmReI))='') then
      qmReS := qmReS+' (Quartermaster)';
      qmReAdd('  '+qmReS);
   end;
end;
qmReAdd('');
qmReAdd('Files:');
for qmReM:=0 to qmReN-1 do
begin
   qmReMs := IntToStr(qmReM);
   qmReAct := ParserGetValueByKeyByHandle(qmRePlan, 'act'+qmReMs);
   qmReAdd('');
   qmReAdd(ParserGetValueByKeyByHandle(qmReG, 's'+qmReMs)+' '+ParserGetValueByKeyByHandle(qmRePlan, 'path'+qmReMs));
   qmReDecision(qmReAct, ParserGetValueByKeyByHandle(qmRePlan, 'why'+qmReMs), qmReS);
   qmReAdd('  decision: '+qmReS);
   qmReV := ParserGetValueByKeyByHandle(qmRePlan, 'prov'+qmReMs);
   qmReU := '';
   qmReI := 0;
   qmField(qmReV, ';', 0, qmReT);
   while (qmReT<>'') do
   begin
      qmReWho(qmReT, qmReS);
      if (qmReI>0) then
      qmReU := qmReU+', ';
      qmReU := qmReU+qmReS;
      qmReI := qmReI+1;
      qmField(qmReV, ';', qmReI, qmReT);
   end;
   qmReAdd('  mods: '+qmReU);
   qmReW := '';
   if (qmReAct='merge-inc') or (qmReAct='hook') then
   qmReW := ParserGetValueByKeyByHandle(qmReG, 'pw'+qmReMs);
   if (qmReAct='winner') then
   qmReW := ParserGetValueByKeyByHandle(qmRePlan, 'win'+qmReMs);
   if (qmReW<>'') then
   begin
      qmReWho(qmReW, qmReS);
      qmReAdd('  winner: '+qmReS);
   end;
   qmReJ := ParserGetIntValueByKeyByHandle(qmReG, 'j'+qmReMs);
   if (qmReJ>=0) and (qmReMg<>0) then
   begin
      qmReJs := 'j'+IntToStr(qmReJ);
      qmReE := ParserGetValueByKeyByHandle(qmReG, 'e'+qmReMs);
      if (qmReE<>'') then
      qmReAdd('  merge error: '+qmReE)
      else
      begin
         qmReS := '  merge: '+ParserGetValueByKeyByHandle(qmReMg, qmReJs+'mode')+', '+ParserGetValueByKeyByHandle(qmReMg, qmReJs+'status');
         if (ParserGetValueByKeyByHandle(qmReMg, qmReJs+'reason')<>'-') then
         qmReS := qmReS+', '+ParserGetValueByKeyByHandle(qmReMg, qmReJs+'reason');
         qmReAdd(qmReS+': '+ParserGetValueByKeyByHandle(qmReMg, qmReJs+'hunks')+' changes, '+ParserGetValueByKeyByHandle(qmReMg, qmReJs+'conflicts')+' conflicts, '+ParserGetValueByKeyByHandle(qmReMg, qmReJs+'proximity')+' near each other');
         if (ParserGetValueByKeyByHandle(qmReMg, qmReJs+'mode')='merged') then
         begin
            qmRePp := ParserGetValueByKeyByHandle(qmReG, 'pp'+qmReMs);
            qmReFirst := ParserGetIntValueByKeyByHandle(qmReG, 'vf'+qmReMs);
            qmReVn := ParserGetIntValueByKeyByHandle(qmReG, 'vn'+qmReMs);
            qmReNr := ParserGetIntValueByKeyByHandle(qmReMg, qmReJs+'rows');
            qmReNp := 0;
            for qmReR:=0 to qmReNr-1 do
            if (SubStr(ParserGetValueByKeyByHandle(qmReMg, qmReJs+'r'+IntToStr(qmReR)), 1, 5)='part|') then
            qmReNp := qmReNp+1;
            for qmReR:=0 to qmReNr-1 do
            begin
               qmReRow := ParserGetValueByKeyByHandle(qmReMg, qmReJs+'r'+IntToStr(qmReR));
               qmField(qmReRow, '|', 6, qmReS);
               if (SubStr(qmReRow, 1, 5)='hunk|') and (qmReS='conflict-lost') then
               begin
                  qmField(qmReRow, '|', 7, qmReT);
                  qmReX := ParserGetValueByKeyByHandle(qmReMg, qmReJs+'r'+IntToStr(1+qmReNp+StrToInt(qmReT)));
                  qmReHunkRange(qmReRow, qmReA);
                  qmReHunkMod(qmReRow, qmRePp, qmReB);
                  qmReHunkMod(qmReX, qmRePp, qmReU);
                  qmReAdd('  conflict: '+qmReA+' of '+qmReB+' lost to '+qmReU);
               end;
            end;
            for qmReR:=0 to qmReNr-1 do
            begin
               qmReRow := ParserGetValueByKeyByHandle(qmReMg, qmReJs+'r'+IntToStr(qmReR));
               if (SubStr(qmReRow, 1, 5)='prox|') then
               begin
                  qmField(qmReRow, '|', 1, qmReS);
                  qmField(qmReRow, '|', 2, qmReT);
                  qmReX := ParserGetValueByKeyByHandle(qmReMg, qmReJs+'r'+IntToStr(1+qmReNp+StrToInt(qmReS)));
                  qmReHunkRange(qmReX, qmReA);
                  qmReHunkMod(qmReX, qmRePp, qmReB);
                  qmReX := ParserGetValueByKeyByHandle(qmReMg, qmReJs+'r'+IntToStr(1+qmReNp+StrToInt(qmReT)));
                  qmReHunkRange(qmReX, qmReU);
                  qmReHunkMod(qmReX, qmRePp, qmReV);
                  qmReAdd('  near: '+qmReA+' of '+qmReB+' and '+qmReU+' of '+qmReV);
               end;
            end;
         end;
      end;
   end;
   for qmReK:=0 to ParserGetIntValueByKeyByHandle(qmReG, 't'+qmReMs)-1 do
   begin
      qmReRow := ParserGetValueByKeyByHandle(qmReG, 't'+qmReMs+'_'+IntToStr(qmReK));
      qmField(qmReRow, '|', 0, qmReS);
      qmField(qmReRow, '|', 3, qmReT);
      if (qmReT='1') then
      qmReAdd('  candidate '+qmReS+': compiles')
      else
      qmReAdd('  candidate '+qmReS+': does not compile');
   end;
   //! The mods the written subset leaves out (qmGenerate lo<m>).
   if (ParserGetValueByKeyByHandle(qmReG, 'x'+qmReMs)='partial') then
   begin
      qmReK := 0;
      qmField(ParserGetValueByKeyByHandle(qmReG, 'lo'+qmReMs), ';', 0, qmReT);
      while (qmReT<>'') do
      begin
         qmReWho(qmReT, qmReS);
         qmReAdd('  left out: '+qmReS);
         qmReK := qmReK+1;
         qmField(ParserGetValueByKeyByHandle(qmReG, 'lo'+qmReMs), ';', qmReK, qmReT);
      end;
   end;
   //! A data merge's own lines (qmDataMerge qm_dm): what became of each
   //! record another mod changed, added or removed, the conflicts and a
   //! failed check.
   if (ParserGetValueByKeyByHandle(qmReG, 'dj'+qmReMs)<>'') and (ParserSelectByKey('qm_dm')<>0) then
   begin
      qmReT := 'j'+ParserGetValueByKeyByHandle(qmReG, 'dj'+qmReMs);
      for qmReK:=0 to ParserGetIntValueByKeyByHandle(ParserSelectByKey('qm_dm'), qmReT+'nl')-1 do
      begin
         qmReS := ParserGetValueByKeyByHandle(ParserSelectByKey('qm_dm'), qmReT+'t'+IntToStr(qmReK));
         if (qmReS='OK') then
         qmReAdd('  '+ParserGetValueByKeyByHandle(ParserSelectByKey('qm_dm'), qmReT+'x'+IntToStr(qmReK)))
         else
         qmReAdd('  '+qmReS+': '+ParserGetValueByKeyByHandle(ParserSelectByKey('qm_dm'), qmReT+'x'+IntToStr(qmReK)));
      end;
   end;
   qmReResult(ParserGetValueByKeyByHandle(qmReG, 'x'+qmReMs), qmReS);
   if (qmReS<>'') then
   qmReAdd('  result: '+qmReS);
end;
if (ParserGetIntValueByKeyByHandle(qmReG, 'sn')>0) then
begin
   qmReAdd('');
   qmReLs := qmReL;
   qmReAdd('Removed from the previous generation:');
   for qmReK:=0 to ParserGetIntValueByKeyByHandle(qmReG, 'sn')-1 do
   begin
      qmReS := ParserGetValueByKeyByHandle(qmReG, 'sr'+IntToStr(qmReK));
      qmReT := qmReS;
      if (qmReS='deleted') then
      qmReT := 'deleted';
      if (qmReS='overwritten') then
      begin
         if (ParserGetValueByKeyByHandle(qmReG, 'ss'+IntToStr(qmReK))='winner') then
         qmReT := 'could not be deleted; overwritten with the winner''s copy'
         else
         qmReT := 'could not be deleted; overwritten with the vanilla copy';
      end;
      if (qmReS='failed') then
      qmReT := 'could not be deleted or overwritten';
      if (qmReS='refused') then
      qmReT := 'kept: Quartermaster may not write or delete this file';
      qmReAdd('  '+ParserGetValueByKeyByHandle(qmReG, 'sp'+IntToStr(qmReK))+': '+qmReT);
   end;
end;
if (ParserGetValueByKeyByHandle(qmReG, 'status')='fatal') then
begin
   qmReAdd('');
   qmReAdd('FATAL: '+ParserGetValueByKeyByHandle(qmReG, 'fatal')+': vanilla with Quartermaster''s hook lines does not compile. This is a Quartermaster bug; nothing was written.');
end;
ParserSetIntValueByKeyByHandle(qmReRep, 'lines', qmReL);

//! Per enabled mod, in load order: the worst tag of the files it ships, one
//! short sentence on how it loads (why<j>, ref/report.py mod_why) and one line
//! per file that is not OK (at most 20).
qmReRec := 0;
for qmReK:=0 to qmReNm-1 do
begin
   qmReI := ParserGetIntValueByKeyByHandle(qmReMods, 'ord'+IntToStr(qmReK));
   if (ParserGetIntValueByKeyByHandle(qmReMods, 'on'+IntToStr(qmReI))=1) then
   begin
      qmReJs := IntToStr(qmReRec);
      ParserSetValueByKeyByHandle(qmReRep, 'dir'+qmReJs, ParserGetValueByKeyByHandle(qmReMods, 'dir'+IntToStr(qmReI)));
      qmReS := 'OK';
      qmReCn := 0;
      qmReNf := 0;
      qmReNb := 0;
      qmReFb := -1;
      for qmReM:=0 to qmReN-1 do
      begin
         qmReMs := IntToStr(qmReM);
         if (StrPos(';'+IntToStr(qmReK)+';', ';'+ParserGetValueByKeyByHandle(qmRePlan, 'prov'+qmReMs)+';')>0) then
         begin
            qmReNf := qmReNf+1;
            qmReModSt(qmReMs, IntToStr(qmReK), qmReT);
            if (qmReRank(qmReT)>qmReRank(qmReS)) then
            qmReS := qmReT;
            if (qmReT<>'OK') then
            begin
               qmReNb := qmReNb+1;
               if (qmReFb<0) then
               qmReFb := qmReM;
            end;
            if (qmReT<>'OK') and (qmReCn<20) then
            begin
               qmReModShort(qmReMs, IntToStr(qmReK), qmReU);
               ParserSetValueByKeyByHandle(qmReRep, 'c'+qmReJs+'_'+IntToStr(qmReCn), qmReT+' '+ParserGetValueByKeyByHandle(qmRePlan, 'path'+qmReMs)+': '+qmReU);
               qmReCn := qmReCn+1;
            end;
         end;
      end;
      if (qmReNf=0) then
      qmReU := 'loads as it is: it ships none of the files Quartermaster merges'
      else
      if (qmReNb=0) then
      qmReU := IntToStr(qmReNf)+' files, all merged or used without problems'
      else
      begin
         qmReModShort(IntToStr(qmReFb), IntToStr(qmReK), qmReV);
         qmReU := IntToStr(qmReNb)+' of '+IntToStr(qmReNf)+' files need a look, first '+ParserGetValueByKeyByHandle(qmRePlan, 'path'+IntToStr(qmReFb))+': '+qmReV;
      end;
      ParserSetValueByKeyByHandle(qmReRep, 'why'+qmReJs, qmReU);
      //! A mod the boot lists as new is NEW while all its files are OK.
      if (qmReS='OK') and (qmReBoot<>0) then
      begin
         qmLowerAscii(ParserGetValueByKeyByHandle(qmReMods, 'dir'+IntToStr(qmReI)), qmReA);
         for qmReJ:=0 to ParserGetIntValueByKeyByHandle(qmReBoot, 'newn')-1 do
         begin
            qmLowerAscii(ParserGetValueByKeyByHandle(qmReBoot, 'new'+IntToStr(qmReJ)), qmReB);
            if (qmReA=qmReB) then
            qmReS := 'NEW';
         end;
      end;
      ParserSetValueByKeyByHandle(qmReRep, 'st'+qmReJs, qmReS);
      ParserSetIntValueByKeyByHandle(qmReRep, 'cn'+qmReJs, qmReCn);
      qmReU := '';
      if (qmReConf<>0) then
      qmReU := ParserGetValueByKeyByHandle(qmReConf, 'd'+IntToStr(qmReK));
      ParserSetValueByKeyByHandle(qmReRep, 'cpd'+qmReJs, qmReU);
      qmReRec := qmReRec+1;
   end;
end;
ParserSetIntValueByKeyByHandle(qmReRep, 'n', qmReRec);

//! The report grouped by mod, the window's Report view (qm_report mlines,
//! m<k>; ref/report.py mod_lines): per enabled mod in load order the worst
//! tag of its files, its why<j>, and per file it ships what became of it and
//! where the merge touched it. report.txt stays by file.
qmReMAdd('Quartermaster report by mod');
qmReMAdd(ParserGetValueByKeyByHandle(qmReRep, 'l2'));
if (qmReConf<>0) then
if (ParserGetIntValueByKeyByHandle(qmReConf, 'wn')>0) then
begin
   qmReMAdd('');
   qmReMAdd('Conflicts between mods (the later mod in the load order wins; every detail in conflicts.txt):');
   for qmReK:=0 to ParserGetIntValueByKeyByHandle(qmReConf, 'wn')-1 do
   qmReMAdd(ParserGetValueByKeyByHandle(qmReConf, 'w'+IntToStr(qmReK)));
end;
if (qmReBn>0) then
begin
   qmReMAdd('');
   qmReMAdd('Boot:');
   for qmReK:=0 to qmReBn-1 do
   qmReMAdd('  '+ParserGetValueByKeyByHandle(qmReBoot, 'l'+IntToStr(qmReK)));
end;
qmReRec := 0;
for qmReK:=0 to qmReNm-1 do
begin
   qmReI := ParserGetIntValueByKeyByHandle(qmReMods, 'ord'+IntToStr(qmReK));
   if (ParserGetIntValueByKeyByHandle(qmReMods, 'on'+IntToStr(qmReI))=1) then
   begin
      qmReKs := IntToStr(qmReK);
      qmReS := 'OK';
      for qmReM:=0 to qmReN-1 do
      if (StrPos(';'+qmReKs+';', ';'+ParserGetValueByKeyByHandle(qmRePlan, 'prov'+IntToStr(qmReM))+';')>0) then
      begin
         qmReModSt(IntToStr(qmReM), qmReKs, qmReV);
         if (qmReRank(qmReV)>qmReRank(qmReS)) then
         qmReS := qmReV;
      end;
      qmReWho(qmReKs, qmReT);
      if (qmReI=qmReSelf) then
      if (ParserGetValueByKeyByHandle(qmReMods, 'tit'+IntToStr(qmReI))='') then
      qmReT := qmReT+' (Quartermaster)';
      qmReClash(qmReI, False, qmReCl);
      if (qmReCl>0) and (qmReRank('FAIL')>qmReRank(qmReS)) then
      qmReS := 'FAIL';
      qmReMAdd('');
      qmReMAdd(qmReS+' '+qmReT);
      qmReMAdd('  '+ParserGetValueByKeyByHandle(qmReRep, 'why'+IntToStr(qmReRec)));
      qmReClash(qmReI, True, qmReCl);
      for qmReM:=0 to qmReN-1 do
      begin
         qmReMs := IntToStr(qmReM);
         if (StrPos(';'+qmReKs+';', ';'+ParserGetValueByKeyByHandle(qmRePlan, 'prov'+qmReMs)+';')>0) then
         begin
            qmReHow(qmReMs, qmReKs, qmReU);
            qmReModSt(qmReMs, qmReKs, qmReV);
            qmReMAdd('  '+qmReV+' '+ParserGetValueByKeyByHandle(qmRePlan, 'path'+qmReMs)+': '+qmReU);
            qmReModMerge(qmReMs, qmReKs);
         end;
      end;
      qmReRec := qmReRec+1;
   end;
end;
if (qmReLs>=0) then
begin
   qmReMAdd('');
   for qmReK:=qmReLs to qmReLs+ParserGetIntValueByKeyByHandle(qmReG, 'sn') do
   qmReMAdd(ParserGetValueByKeyByHandle(qmReRep, 'l'+IntToStr(qmReK)));
end;
if (ParserGetValueByKeyByHandle(qmReG, 'status')='fatal') then
begin
   qmReMAdd('');
   qmReMAdd(ParserGetValueByKeyByHandle(qmReRep, 'l'+IntToStr(qmReL-1)));
end;
ParserSetIntValueByKeyByHandle(qmReRep, 'mlines', qmReML);

qmReW := ParserGetValueByKeyByHandle(qmReG, 'work');
if (qmReW<>'') then
begin
   OpenFileStreamForWrite(qmReW+'report.txt');
   for qmReK:=0 to qmReL-1 do
   begin
      qmEscape(ParserGetValueByKeyByHandle(qmReRep, 'l'+IntToStr(qmReK)), qmReS);
      qmRawPutLine(qmReS, qmReAcc, qmReCnt);
   end;
   qmRawClose(qmReAcc, qmReCnt);
   //! qm_report itself, for a boot that does not generate (qmReportLoad): the
   //! engine's parser writes it and reads it back, so a mod folder's name
   //! keeps every byte, which the raw text could not give back. The helper
   //! guards the leading spaces the parser would drop.
   qmRepCfgSave(qmReRep, qmReW+'report.cfg');
end;
qmLog('report '+qmReTag+' lines='+IntToStr(qmReL)+' mods='+IntToStr(qmReRec)+' bymod='+IntToStr(qmReML)+' file='+qmReW+'report.txt');
