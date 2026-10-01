helpers: qmraw, qmdiff, qmmergeout
requires: maxlines
---
//! Three-way merge and classifier (plan G9), the game side of ref/merge.py
//! `merge` + `merge_inc` + `result_rows`, rule for rule and in the same order:
//!
//! 1. Every participant, in the canonical order it is given in, is diffed
//!    against vanilla (qmdiff). A diff that is given up - D over the cap, or a
//!    file over the line cap - makes the file winner-takes-all, status fail,
//!    winner = the last participant; the participants after it are not diffed.
//! 2. A participant whose diff deletes or replaces more than half of the
//!    vanilla lines (2*deleted > n) is a full replacement. If another
//!    participant makes a different change to the file it is winner-takes-all,
//!    status warn; participants that made the very same change merge like any
//!    others (their hunks deduplicate).
//! 3. Hunks of different participants that overlap - the same start, or
//!    intersecting ranges - are resolved pairwise in hunk order: identical
//!    ones keep the first (duplicate, fine), different ones keep the later
//!    (conflict, the later participant wins, warn). Both are reported.
//! 4. Kept hunks of different participants with at most 3 vanilla lines
//!    between them are flagged (proximity, warn).
//! 5. The output is vanilla with the kept hunks applied: unchanged lines are
//!    vanilla's, changed lines the participant's.
//! 6. Quartermaster's hook lines, when given, go into the result as a separate
//!    step after the merge, at the hook index of plan S5 (before the first
//!    top-level Code line after the routines a state starts with; qminc.pas
//!    qmIncHookIndex, ref/inc.py hook_index / insert_at_hook): they never take
//!    part in a diff, and they go into a winner's file the same way.
//!
//! The merge touches no file itself. It reads through the read seam
//! (qmdiffsrc.pas: qmLnOpen, qmLnRead) and hands its final line list to the
//! write seam (qmmergeout.pas: qmMgOutBegin, qmMgOutLine, qmMgOutEnd) in order,
//! one line at a time (qmMgEmit).
//!
//! A hunk's pool index is its ref index: participants in order, each one's
//! hunks in file order. qmMgHby is the hunk that dropped this one (the one it
//! duplicates, or the later one that won), qmMgHbk why (1 conflict, 2
//! duplicate); qmMgHwon, qmMgHdup and qmMgHprx count the conflicts won, the
//! duplicates dropped in its favour and its proximity partners - which is all
//! ref's status property looks at.
//!
//! Limits: qmMgPmax participants per file; the hunk pool then always fits,
//! because a diff has at most qmDfCap hunks (16 x 998 = 15 968 < 16 384).
//! Every source stays in the read seam's pool for the whole merge: the output
//! and the duplicate test read their lines by index. A merge whose files do
//! not fit the pool together (65 536 lines, about 15 copies of the largest
//! vanilla .inc) ends with `error|pool full`, like more than qmMgPmax
//! participants - limits of the game side that ref/ does not have; the
//! planner sends such a file to winner-takes-all.
//!
//! Result (plan G13 prints it), per merge j of a call, in the named parser
//! qm_mg: the rows of ref/merge.py result_rows as j<j>r0..j<j>r<rows-1> and
//! the keys j<j> + rows, mode, status, reason, winner, hunks, conflicts,
//! proximity, lines, outlines (the final line list, hook lines included),
//! hookat (where they went), written (yes, none, failed), bytes, err and the
//! timings ms, msload, msdiff, msmerge, mswrite; j<j>done = 1 is set last.
//! The same rows go to the dump file when one is asked for, through the raw
//! writer: CRLF, padded with spaces to a multiple of 4 bytes (ref/textio.py
//! write_file).
const qmMgPmax = 16;
const qmMgHcap = 16383;
//! "distinct edits within <= 3 lines of each other" (plan G9).
const qmMgNear = 3;
var qmMgHp : array [0..16383] of Integer;
var qmMgHs : array [0..16383] of Integer;
var qmMgHe : array [0..16383] of Integer;
var qmMgHms : array [0..16383] of Integer;
var qmMgHme : array [0..16383] of Integer;
var qmMgHk : array [0..16383] of Integer;
var qmMgHby : array [0..16383] of Integer;
var qmMgHbk : array [0..16383] of Integer;
var qmMgHwon : array [0..16383] of Integer;
var qmMgHdup : array [0..16383] of Integer;
var qmMgHprx : array [0..16383] of Integer;
var qmMgHch : array [0..16383] of Integer;
var qmMgPc : array [0..15] of Integer;
var qmMgPm : array [0..15] of Integer;
var qmMgPok : array [0..15] of Integer;
var qmMgPwhy : array [0..15] of Integer;
var qmMgPd : array [0..15] of Integer;
var qmMgPdel : array [0..15] of Integer;
var qmMgPins : array [0..15] of Integer;
var qmMgPcl : array [0..15] of Integer;
var qmMgPrep : array [0..15] of Integer;
var qmMgPsq : array [0..15] of Integer;
var qmMgPh0 : array [0..15] of Integer;
var qmMgPh1 : array [0..15] of Integer;
var qmMgPtr : array [0..15] of Integer;
var qmMgAt : array [0..${maxlines}] of Integer;
var qmMgN : Integer = 0;
var qmMgNp : Integer = 0;
var qmMgNd : Integer = 0;
var qmMgH : Integer = 0;
var qmMgMode : Integer = 0;
var qmMgStat : Integer = 0;
var qmMgWhy : Integer = 0;
var qmMgWin : Integer = -1;
var qmMgConf : Integer = 0;
var qmMgProx : Integer = 0;
var qmMgLines : Integer = 0;
var qmMgOutLines : Integer = 0;
var qmMgHookAt : Integer = 0;
var qmMgErr : String = '';
var qmMgRes : Integer = 0;
var qmMgJob : String = '';
var qmMgRows : Integer = 0;
var qmMgDump : Integer = 0;
var qmMgAcc : Integer = 0;
var qmMgCnt : Integer = 0;

//! Participant qmMlI's file: its source and line count. The last one's key
//! lines are kept: a winner-takes-all output takes the winner's layout.
procedure qmMgLoad(const qmMlI : Integer; const qmMlPath : String);
begin
   var qmMlSrc : Integer = 0;
   var qmMlN : Integer = 0;
   qmLnOpen(qmMlPath, qmMlSrc, qmMlN);
   qmMgPc[qmMlI] := qmMlSrc;
   qmMgPm[qmMlI] := 0;
   if (qmMlN=-2) then
   qmMgErr := 'participant '+IntToStr(qmMlI)+' missing'
   else
   if (qmMlN<0) then
   qmMgErr := 'pool full'
   else
   begin
      qmMgPm[qmMlI] := qmMlN;
      if (qmMlI=qmMgNp-1) then
      qmLnKeep(1);
   end;
end;

//! Rule 1: diff every participant in order; stop at the first one given up.
procedure qmMgDiffAll;
begin
   var qmMdI : Integer = 0;
   var qmMdK : Integer;
   var qmMdL : Integer;
   var qmMdCh : Integer;
   var qmMdSeq : Integer = 0;
   qmMgNd := 0;
   qmMgH := 0;
   if (qmMgN<=qmLnCap) then
   qmLnHashAll(qmLnVc, qmMgN, 0, qmMdSeq);
   while (qmMdI<qmMgNp) and (qmMgMode<>2) and (qmMgErr='') do
   begin
      qmLnPc := qmMgPc[qmMdI];
      qmLnPn := qmMgPm[qmMdI];
      qmMdSeq := 0;
      if (qmMgN<=qmLnCap) and (qmLnPn<=qmLnCap) then
      qmLnHashAll(qmLnPc, qmLnPn, 1, qmMdSeq);
      qmMgPsq[qmMdI] := qmMdSeq;
      qmDfRun;
      qmMgPok[qmMdI] := qmDfOk;
      qmMgPwhy[qmMdI] := qmDfWhy;
      qmMgPd[qmMdI] := qmDfD;
      qmMgPdel[qmMdI] := qmDfDel;
      qmMgPins[qmMdI] := qmDfIns;
      qmMgPcl[qmMdI] := qmDfCells;
      qmMgPrep[qmMdI] := 0;
      qmMgPh0[qmMdI] := qmMgH;
      qmMgNd := qmMdI+1;
      if (qmDfOk=0) then
      begin
         qmMgMode := 2;
         qmMgStat := 2;
         qmMgWhy := qmDfWhy;
         qmMgWin := qmMgNp-1;
      end
      else
      begin
         if (2*qmDfDel>qmMgN) then
         qmMgPrep[qmMdI] := 1;
         if (qmMgH+qmDfNh>qmMgHcap+1) then
         qmMgErr := 'hunk pool full'
         else
         for qmMdK:=0 to qmDfNh-1 do
         begin
            qmMgHp[qmMgH] := qmMdI;
            qmMgHs[qmMgH] := qmDfHs[qmMdK];
            qmMgHe[qmMgH] := qmDfHe[qmMdK];
            qmMgHms[qmMgH] := qmDfHms[qmMdK];
            qmMgHme[qmMgH] := qmDfHme[qmMdK];
            qmMgHk[qmMgH] := 1;
            qmMgHby[qmMgH] := -1;
            qmMgHbk[qmMgH] := 0;
            qmMgHwon[qmMgH] := 0;
            qmMgHdup[qmMgH] := 0;
            qmMgHprx[qmMgH] := 0;
            //! The hash of the hunk's new lines: the cheap first test of rule 3's
            //! "identical".
            qmMdCh := (qmDfHme[qmMdK]-qmDfHms[qmMdK]) and 1073741823;
            for qmMdL:=qmDfHms[qmMdK] to qmDfHme[qmMdK]-1 do
            qmMdCh := ((qmMdCh*31)+qmLnPh[qmMdL]) and 1073741823;
            qmMgHch[qmMgH] := qmMdCh;
            qmMgH := qmMgH+1;
         end;
      end;
      qmMgPh1[qmMdI] := qmMgH;
      qmMdI := qmMdI+1;
   end;
end;

//! 1 when participants qmMfA and qmMfB hold the same key sequence.
function qmMgSameFile(const qmMfA : Integer; const qmMfB : Integer) : Integer;
begin
   var qmMfK : Integer = 0;
   var qmMfF : Integer;
   var qmMfSa : String;
   var qmMfSb : String;
   Result := 1;
   if (qmMgPm[qmMfA]<>qmMgPm[qmMfB]) or (qmMgPsq[qmMfA]<>qmMgPsq[qmMfB]) then
   Result := 0;
   while (Result=1) and (qmMfK<qmMgPm[qmMfA]) do
   begin
      qmMfF := 0;
      if (qmMfK=0) then
      qmMfF := 1;
      qmLnRead(qmMgPc[qmMfA], qmMfK, qmMfSa);
      qmLnRead(qmMgPc[qmMfB], qmMfK, qmMfSb);
      Result := qmLnSame(qmMfSa, qmMfF, qmMfSb, qmMfF);
      qmMfK := qmMfK+1;
   end;
end;

//! Rule 2 and the vanilla case: who changes anything, and is one of them a
//! replacement that meets a different change.
procedure qmMgChangers;
begin
   var qmMcI : Integer;
   var qmMcFirst : Integer = -1;
   var qmMcRep : Integer = 0;
   var qmMcDiffer : Integer = 0;
   for qmMcI:=0 to qmMgNd-1 do
   if (qmMgPh1[qmMcI]>qmMgPh0[qmMcI]) then
   begin
      if (qmMcFirst<0) then
      qmMcFirst := qmMcI;
      if (qmMgPrep[qmMcI]=1) then
      qmMcRep := 1;
   end;
   if (qmMcFirst<0) then
   begin
      qmMgMode := 0;
      qmMgStat := 0;
   end
   else
   begin
      if (qmMcRep=1) then
      for qmMcI:=qmMcFirst+1 to qmMgNd-1 do
      if (qmMcDiffer=0) and (qmMgPh1[qmMcI]>qmMgPh0[qmMcI]) then
      begin
         if (qmMgSameFile(qmMcFirst, qmMcI)=0) then
         qmMcDiffer := 1;
      end;
      if (qmMcDiffer=1) then
      begin
         qmMgMode := 2;
         qmMgStat := 1;
         qmMgWhy := 3;
         qmMgWin := qmMgNp-1;
      end
      else
      qmMgMode := 1;
   end;
end;

//! 1 when hunks qmMuA and qmMuB replace the same vanilla range with the same
//! key sequence.
function qmMgHunkSame(const qmMuA : Integer; const qmMuB : Integer) : Integer;
begin
   var qmMuK : Integer = 0;
   var qmMuIa : Integer;
   var qmMuIb : Integer;
   var qmMuFa : Integer;
   var qmMuFb : Integer;
   var qmMuSa : String;
   var qmMuSb : String;
   Result := 1;
   if (qmMgHs[qmMuA]<>qmMgHs[qmMuB]) or (qmMgHe[qmMuA]<>qmMgHe[qmMuB]) then
   Result := 0;
   if (qmMgHme[qmMuA]-qmMgHms[qmMuA]<>qmMgHme[qmMuB]-qmMgHms[qmMuB]) or (qmMgHch[qmMuA]<>qmMgHch[qmMuB]) then
   Result := 0;
   while (Result=1) and (qmMuK<qmMgHme[qmMuA]-qmMgHms[qmMuA]) do
   begin
      qmMuIa := qmMgHms[qmMuA]+qmMuK;
      qmMuIb := qmMgHms[qmMuB]+qmMuK;
      qmMuFa := 0;
      if (qmMuIa=0) then
      qmMuFa := 1;
      qmMuFb := 0;
      if (qmMuIb=0) then
      qmMuFb := 1;
      qmLnRead(qmMgPc[qmMgHp[qmMuA]], qmMuIa, qmMuSa);
      qmLnRead(qmMgPc[qmMgHp[qmMuB]], qmMuIb, qmMuSb);
      Result := qmLnSame(qmMuSa, qmMuFa, qmMuSb, qmMuFb);
      qmMuK := qmMuK+1;
   end;
end;

//! Rule 3, in ref's pair order: for every hunk a, every later hunk b of a
//! later participant. A pair that cannot overlap changes nothing in ref, so
//! it is skipped here: within one participant the hunks are disjoint and in
//! file order, so for each later participant a pointer (qmMgPtr) skips the
//! hunks that end before a starts - and, as a's start only grows inside a's
//! own participant, it never has to move back until that participant ends -
//! and the scan stops at the first hunk that starts after a ends.
procedure qmMgOverlap;
begin
   var qmMoA : Integer;
   var qmMoB : Integer;
   var qmMoQ : Integer;
   var qmMoOwn : Integer = -1;
   for qmMoA:=0 to qmMgH-1 do
   begin
      if (qmMgHp[qmMoA]<>qmMoOwn) then
      begin
         qmMoOwn := qmMgHp[qmMoA];
         for qmMoQ:=0 to qmMgNd-1 do
         qmMgPtr[qmMoQ] := qmMgPh0[qmMoQ];
      end;
      qmMoQ := qmMoOwn+1;
      while (qmMoQ<qmMgNd) and (qmMgHk[qmMoA]=1) do
      begin
         while (qmMgPtr[qmMoQ]<qmMgPh1[qmMoQ]) and (qmMgHe[qmMgPtr[qmMoQ]]<qmMgHs[qmMoA]) do
         qmMgPtr[qmMoQ] := qmMgPtr[qmMoQ]+1;
         qmMoB := qmMgPtr[qmMoQ];
         while (qmMoB<qmMgPh1[qmMoQ]) and (qmMgHk[qmMoA]=1) do
         begin
            if (qmMgHs[qmMoB]>qmMgHe[qmMoA]) then
            qmMoB := qmMgPh1[qmMoQ]
            else
            begin
               if (qmMgHk[qmMoB]=1) then
               begin
                  if (qmMgHs[qmMoA]=qmMgHs[qmMoB]) or ((qmMgHs[qmMoA]<qmMgHe[qmMoB]) and (qmMgHs[qmMoB]<qmMgHe[qmMoA])) then
                  begin
                     if (qmMgHunkSame(qmMoA, qmMoB)=1) then
                     begin
                        qmMgHk[qmMoB] := 0;
                        qmMgHby[qmMoB] := qmMoA;
                        qmMgHbk[qmMoB] := 2;
                        qmMgHdup[qmMoA] := qmMgHdup[qmMoA]+1;
                     end
                     else
                     begin
                        qmMgHk[qmMoA] := 0;
                        qmMgHby[qmMoA] := qmMoB;
                        qmMgHbk[qmMoA] := 1;
                        qmMgHwon[qmMoB] := qmMgHwon[qmMoB]+1;
                     end;
                  end;
               end;
               qmMoB := qmMoB+1;
            end;
         end;
         qmMoQ := qmMoQ+1;
      end;
   end;
end;

//! The kept hunks in start order: two kept hunks never share a start (that
//! would be an overlap), so qmMgAt[s] = the kept hunk starting at vanilla line
//! s, -1 for none, is exactly ref's sort by (start, end). Also counts the
//! output lines and the conflicts.
procedure qmMgOrder;
begin
   var qmMaS : Integer;
   var qmMaH : Integer;
   qmMgLines := qmMgN;
   qmMgConf := 0;
   for qmMaS:=0 to qmMgN do
   qmMgAt[qmMaS] := -1;
   for qmMaH:=0 to qmMgH-1 do
   if (qmMgHk[qmMaH]=1) then
   begin
      qmMgAt[qmMgHs[qmMaH]] := qmMaH;
      qmMgLines := qmMgLines-(qmMgHe[qmMaH]-qmMgHs[qmMaH])+(qmMgHme[qmMaH]-qmMgHms[qmMaH]);
   end
   else
   if (qmMgHbk[qmMaH]=1) then
   qmMgConf := qmMgConf+1;
end;

procedure qmMgRow(const qmMrS : String);
begin
   ParserSetValueByKeyByHandle(qmMgRes, qmMgJob+'r'+IntToStr(qmMgRows), qmMrS);
   qmMgRows := qmMgRows+1;
   if (qmMgDump=1) then
   qmRawPutStr(qmMrS+'~013~010', qmMgAcc, qmMgCnt);
end;

//! Rule 4. Every kept hunk b after a starts at a's end or later, and at most
//! one starts at each line, so the lines a.end .. a.end+3 hold exactly the b
//! of ref's loop, in ref's order. qmMpDump = 0 counts, 1 writes the rows.
procedure qmMgProximity(const qmMpDump : Integer);
begin
   var qmMpS : Integer;
   var qmMpT : Integer;
   var qmMpA : Integer;
   var qmMpB : Integer;
   var qmMpTop : Integer;
   for qmMpS:=0 to qmMgN do
   begin
      qmMpA := qmMgAt[qmMpS];
      if (qmMpA>=0) then
      begin
         qmMpTop := qmMgHe[qmMpA]+qmMgNear;
         if (qmMpTop>qmMgN) then
         qmMpTop := qmMgN;
         for qmMpT:=qmMgHe[qmMpA] to qmMpTop do
         begin
            qmMpB := qmMgAt[qmMpT];
            if (qmMpB>=0) and (qmMpB<>qmMpA) then
            begin
               if (qmMgHp[qmMpB]<>qmMgHp[qmMpA]) then
               begin
                  if (qmMpDump=1) then
                  qmMgRow('prox|'+IntToStr(qmMpA)+'|'+IntToStr(qmMpB))
                  else
                  begin
                     qmMgHprx[qmMpA] := qmMgHprx[qmMpA]+1;
                     qmMgHprx[qmMpB] := qmMgHprx[qmMpB]+1;
                     qmMgProx := qmMgProx+1;
                  end;
               end;
            end;
         end;
      end;
   end;
end;

//! ref's MergeHunk.status: the strongest first.
procedure qmMgStatusOf(const qmMtH : Integer; var qmMtOut : String);
begin
   if (qmMgHk[qmMtH]=0) then
   begin
      if (qmMgHbk[qmMtH]=2) then
      qmMtOut := 'duplicate'
      else
      qmMtOut := 'conflict-lost';
   end
   else
   if (qmMgHwon[qmMtH]>0) then
   qmMtOut := 'conflict-won'
   else
   if (qmMgHprx[qmMtH]>0) then
   qmMtOut := 'proximity'
   else
   if (qmMgHdup[qmMtH]>0) then
   qmMtOut := 'identical'
   else
   qmMtOut := 'clean';
end;

//! Warn when any kept hunk won a conflict or has a proximity partner.
procedure qmMgStatus;
begin
   var qmMsH : Integer;
   qmMgStat := 0;
   for qmMsH:=0 to qmMgH-1 do
   if (qmMgHk[qmMsH]=1) and ((qmMgHwon[qmMsH]>0) or (qmMgHprx[qmMsH]>0)) then
   qmMgStat := 1;
end;

//! Rules 5 and 6: the final line list into the write seam, in order. The
//! result's lines are vanilla with the kept hunks applied in start order
//! (qmMgAt), vanilla itself when nobody changes anything, or the winner's own
//! lines; a merged result is laid out in the pool first, so the hook index can
//! be taken over it like over any file's values. Then the result up to the
//! hook index, the hook lines (source qmMeHook, qmMeHn of them, -1 for no hook
//! file), the rest. 1 when the file was written, 0 when the writer did not get
//! the lines it was promised, -1 when the pool had no room for the result.
procedure qmMgEmitRange(const qmMvSrc : Integer; const qmMvA : Integer; const qmMvB : Integer);
begin
   var qmMvK : Integer;
   var qmMvS : String;
   for qmMvK:=qmMvA to qmMvB-1 do
   begin
      qmLnRead(qmMvSrc, qmMvK, qmMvS);
      qmMgOutLine(qmMvS);
   end;
end;

function qmMgLayOut(const qmMyA : Integer; const qmMyFrom : Integer; const qmMyTo : Integer) : Integer;
begin
   var qmMyK : Integer;
   var qmMyS : String;
   Result := 1;
   for qmMyK:=qmMyFrom to qmMyTo-1 do
   if (Result=1) then
   begin
      qmLnRead(qmMyA, qmMyK, qmMyS);
      Result := qmLnPut(qmMyS);
   end;
end;

function qmMgEmit(const qmMePath : String; const qmMeHook : Integer; const qmMeHn : Integer; var qmMeBytes : Integer) : Integer;
begin
   var qmMeS : Integer;
   var qmMeH : Integer;
   var qmMePos : Integer = 0;
   var qmMeSrc : Integer = qmLnVc;
   var qmMeN : Integer = qmMgN;
   var qmMeOk : Integer = 1;
   var qmMeSlot : Integer = 0;
   var qmMeK : Integer = 0;
   var qmMeHk : Integer = 0;
   Result := -1;
   if (qmMgMode=2) then
   begin
      qmMeSrc := qmMgPc[qmMgNp-1];
      qmMeN := qmMgPm[qmMgNp-1];
      qmMeSlot := 1;
   end;
   if (qmMgMode=1) then
   begin
      qmMeSrc := qmLnTop;
      for qmMeS:=0 to qmMgN do
      begin
         qmMeH := qmMgAt[qmMeS];
         if (qmMeH>=0) and (qmMeOk=1) then
         begin
            qmMeOk := qmMgLayOut(qmLnVc, qmMePos, qmMgHs[qmMeH]);
            if (qmMeOk=1) then
            qmMeOk := qmMgLayOut(qmMgPc[qmMgHp[qmMeH]], qmMgHms[qmMeH], qmMgHme[qmMeH]);
            qmMePos := qmMgHe[qmMeH];
         end;
      end;
      if (qmMeOk=1) then
      qmMeOk := qmMgLayOut(qmLnVc, qmMePos, qmMgN);
      qmMeN := qmMgLines;
   end;
   if (qmMeOk=1) then
   begin
      if (qmMeHn>=0) then
      begin
         qmMeHk := qmMeHn;
         qmMeK := qmIncHookIndex(qmLnPool, qmMeSrc, qmMeN);
      end;
      qmMgHookAt := qmMeK;
      qmMgOutLines := qmMeN+qmMeHk;
      qmMgOutBegin(qmMePath, qmMeSlot, qmMgOutLines);
      qmMgEmitRange(qmMeSrc, 0, qmMeK);
      if (qmMeHk>0) then
      qmMgEmitRange(qmMeHook, 0, qmMeHk);
      qmMgEmitRange(qmMeSrc, qmMeK, qmMeN);
      Result := qmMgOutEnd(qmMeBytes);
   end;
end;

//! The names ref/merge.py uses for mode, status and reason codes.
procedure qmMgNames(var qmMnMode : String; var qmMnStat : String; var qmMnWhy : String);
begin
   qmMnMode := 'vanilla';
   if (qmMgMode=1) then
   qmMnMode := 'merged';
   if (qmMgMode=2) then
   qmMnMode := 'winner';
   qmMnStat := 'ok';
   if (qmMgStat=1) then
   qmMnStat := 'warn';
   if (qmMgStat=2) then
   qmMnStat := 'fail';
   qmMnWhy := '-';
   if (qmMgWhy=1) then
   qmMnWhy := 'too-different';
   if (qmMgWhy=2) then
   qmMnWhy := 'too-many-lines';
   if (qmMgWhy=3) then
   qmMnWhy := 'replacement';
end;

//! ref/merge.py result_rows, row for row.
procedure qmMgRowsOut;
begin
   var qmMzMode : String;
   var qmMzStat : String;
   var qmMzWhy : String;
   var qmMzI : Integer;
   var qmMzHunks : Integer = 0;
   var qmMzS : String;
   var qmMzBy : Integer;
   qmMgNames(qmMzMode, qmMzStat, qmMzWhy);
   if (qmMgMode=1) then
   qmMzHunks := qmMgH;
   if (qmMgMode<>1) then
   begin
      qmMgConf := 0;
      qmMgProx := 0;
   end;
   qmMgRow('merge|'+qmMzMode+'|'+qmMzStat+'|'+qmMzWhy+'|'+IntToStr(qmMgWin)+'|'+IntToStr(qmMzHunks)+'|'+IntToStr(qmMgConf)+'|'+IntToStr(qmMgProx)+'|'+IntToStr(qmMgLines));
   for qmMzI:=0 to qmMgNd-1 do
   begin
      if (qmMgPok[qmMzI]=1) then
      qmMgRow('part|'+IntToStr(qmMzI)+'|1|-|'+IntToStr(qmMgPd[qmMzI])+'|'+IntToStr(qmMgPdel[qmMzI])+'|'+IntToStr(qmMgPins[qmMzI])+'|'+IntToStr(qmMgPcl[qmMzI])+'|'+IntToStr(qmMgPrep[qmMzI]))
      else
      begin
         qmMzS := 'too-different';
         if (qmMgPwhy[qmMzI]=2) then
         qmMzS := 'too-many-lines';
         qmMgRow('part|'+IntToStr(qmMzI)+'|0|'+qmMzS+'|-1|-1|-1|'+IntToStr(qmMgPcl[qmMzI])+'|0');
      end;
   end;
   if (qmMgMode=1) then
   begin
      for qmMzI:=0 to qmMgH-1 do
      begin
         qmMgStatusOf(qmMzI, qmMzS);
         qmMzBy := -1;
         if (qmMgHk[qmMzI]=0) then
         qmMzBy := qmMgHby[qmMzI];
         qmMgRow('hunk|'+IntToStr(qmMzI)+'|'+IntToStr(qmMgHp[qmMzI])+'|'+IntToStr(qmMgHs[qmMzI])+'|'+IntToStr(qmMgHe[qmMzI])+'|'+IntToStr(qmMgHme[qmMzI]-qmMgHms[qmMzI])+'|'+qmMzS+'|'+IntToStr(qmMzBy));
      end;
      qmMgProximity(1);
   end;
end;

//! Merge qmMxJob of a call. qmMxIn is a named parser holding, for j =
//! qmMxJob, the keys j<j>base (the vanilla .inc, by absolute path - `.\data\`
//! would go through the overlay), j<j>parts (1..qmMgPmax) and j<j>p0 .. (the
//! participants' files, canonical order), j<j>hook (a file whose Code values
//! are the hook lines, or ''), j<j>out (where the result is written, or '')
//! and j<j>dump (where the rows go, or ''). A winner-takes-all result without
//! hook lines writes no file: the winner's own file is what the engine loads
//! anyway. qm_mg_in and qm_mg are key/value stores only; files go through the
//! two seams.
procedure qmMgRun(const qmMxIn : Integer; const qmMxJob : Integer);
begin
   var qmMxT0 : Float = _misc_GetRealTime;
   var qmMxT1 : Float = qmMxT0;
   var qmMxT2 : Float = qmMxT0;
   var qmMxT3 : Float = qmMxT0;
   var qmMxT4 : Float = qmMxT0;
   var qmMxJ : String = 'j'+IntToStr(qmMxJob);
   var qmMxBase : String = ParserGetValueByKeyByHandle(qmMxIn, qmMxJ+'base');
   var qmMxHook : String = ParserGetValueByKeyByHandle(qmMxIn, qmMxJ+'hook');
   var qmMxOut : String = ParserGetValueByKeyByHandle(qmMxIn, qmMxJ+'out');
   var qmMxDump : String = ParserGetValueByKeyByHandle(qmMxIn, qmMxJ+'dump');
   var qmMxHs : Integer = 0;
   var qmMxHn : Integer = -1;
   var qmMxI : Integer;
   var qmMxW : Integer = 0;
   var qmMxBytes : Integer = 0;
   var qmMxN : Integer = 0;
   var qmMxWritten : String = 'none';
   var qmMxMode : String;
   var qmMxStat : String;
   var qmMxWhy : String;
   qmMgJob := qmMxJ;
   qmMgNp := ParserGetIntValueByKeyByHandle(qmMxIn, qmMxJ+'parts');
   qmMgN := 0;
   qmMgNd := 0;
   qmMgH := 0;
   qmMgMode := 0;
   qmMgStat := 0;
   qmMgWhy := 0;
   qmMgWin := -1;
   qmMgConf := 0;
   qmMgProx := 0;
   qmMgLines := 0;
   qmMgOutLines := 0;
   qmMgHookAt := 0;
   qmMgErr := '';
   qmMgRows := 0;
   qmMgDump := 0;
   qmMgAcc := 0;
   qmMgCnt := 0;
   qmLnReset;
   if (qmMgNp<1) or (qmMgNp>qmMgPmax) then
   qmMgErr := 'participants '+IntToStr(qmMgNp)
   else
   begin
      qmLnOpen(qmMxBase, qmLnVc, qmMxN);
      if (qmMxN=-2) then
      qmMgErr := 'base missing'
      else
      if (qmMxN<0) then
      qmMgErr := 'pool full'
      else
      begin
         qmLnKeep(0);
         qmMgN := qmMxN;
         qmLnVn := qmMgN;
      end;
      for qmMxI:=0 to qmMgNp-1 do
      if (qmMgErr='') then
      qmMgLoad(qmMxI, ParserGetValueByKeyByHandle(qmMxIn, qmMxJ+'p'+IntToStr(qmMxI)));
   end;
   qmMxT1 := _misc_GetRealTime;
   if (qmMgErr='') then
   begin
      qmMgDiffAll;
      qmMxT2 := _misc_GetRealTime;
      if (qmMgMode<>2) and (qmMgErr='') then
      qmMgChangers;
      if (qmMgMode=0) then
      qmMgLines := qmMgN;
      if (qmMgMode=2) then
      qmMgLines := qmMgPm[qmMgNp-1];
      if (qmMgMode=1) then
      begin
         qmMgOverlap;
         qmMgOrder;
         qmMgProximity(0);
         qmMgStatus;
      end;
      qmMxT3 := _misc_GetRealTime;
      if (qmMxOut<>'') and (qmMgErr='') and ((qmMgMode<>2) or (qmMxHook<>'')) then
      begin
         if (qmMxHook<>'') then
         begin
            qmLnOpen(qmMxHook, qmMxHs, qmMxHn);
            if (qmMxHn=-2) then
            qmMgErr := 'hook file missing'
            else
            if (qmMxHn<0) then
            qmMgErr := 'pool full';
         end;
         if (qmMgErr='') then
         begin
            qmMxW := qmMgEmit(qmMxOut, qmMxHs, qmMxHn, qmMxBytes);
            if (qmMxW=1) then
            qmMxWritten := 'yes'
            else
            if (qmMxW=0) then
            qmMxWritten := 'failed'
            else
            qmMgErr := 'pool full';
         end;
      end;
      qmMxT4 := _misc_GetRealTime;
   end;
   if (qmMxDump<>'') then
   begin
      OpenFileStreamForWrite(qmMxDump);
      qmMgDump := 1;
   end;
   if (qmMgErr<>'') then
   qmMgRow('error|'+qmMgErr)
   else
   qmMgRowsOut;
   if (qmMgDump=1) then
   begin
      qmRawClose(qmMgAcc, qmMgCnt);
      qmMgDump := 0;
   end;
   qmMgNames(qmMxMode, qmMxStat, qmMxWhy);
   ParserSetValueByKeyByHandle(qmMgRes, qmMxJ+'rows', IntToStr(qmMgRows));
   ParserSetValueByKeyByHandle(qmMgRes, qmMxJ+'mode', qmMxMode);
   ParserSetValueByKeyByHandle(qmMgRes, qmMxJ+'status', qmMxStat);
   ParserSetValueByKeyByHandle(qmMgRes, qmMxJ+'reason', qmMxWhy);
   ParserSetValueByKeyByHandle(qmMgRes, qmMxJ+'winner', IntToStr(qmMgWin));
   if (qmMgMode=1) then
   ParserSetValueByKeyByHandle(qmMgRes, qmMxJ+'hunks', IntToStr(qmMgH))
   else
   ParserSetValueByKeyByHandle(qmMgRes, qmMxJ+'hunks', '0');
   ParserSetValueByKeyByHandle(qmMgRes, qmMxJ+'conflicts', IntToStr(qmMgConf));
   ParserSetValueByKeyByHandle(qmMgRes, qmMxJ+'proximity', IntToStr(qmMgProx));
   ParserSetValueByKeyByHandle(qmMgRes, qmMxJ+'lines', IntToStr(qmMgLines));
   ParserSetValueByKeyByHandle(qmMgRes, qmMxJ+'outlines', IntToStr(qmMgOutLines));
   ParserSetValueByKeyByHandle(qmMgRes, qmMxJ+'hookat', IntToStr(qmMgHookAt));
   ParserSetValueByKeyByHandle(qmMgRes, qmMxJ+'written', qmMxWritten);
   ParserSetValueByKeyByHandle(qmMgRes, qmMxJ+'bytes', IntToStr(qmMxBytes));
   ParserSetValueByKeyByHandle(qmMgRes, qmMxJ+'err', qmMgErr);
   ParserSetValueByKeyByHandle(qmMgRes, qmMxJ+'msload', FloatToStr((qmMxT1-qmMxT0)*1000));
   ParserSetValueByKeyByHandle(qmMgRes, qmMxJ+'msdiff', FloatToStr((qmMxT2-qmMxT1)*1000));
   ParserSetValueByKeyByHandle(qmMgRes, qmMxJ+'msmerge', FloatToStr((qmMxT3-qmMxT2)*1000));
   ParserSetValueByKeyByHandle(qmMgRes, qmMxJ+'mswrite', FloatToStr((qmMxT4-qmMxT3)*1000));
   ParserSetValueByKeyByHandle(qmMgRes, qmMxJ+'ms', FloatToStr((_misc_GetRealTime-qmMxT0)*1000));
   ParserSetValueByKeyByHandle(qmMgRes, qmMxJ+'done', '1');
end;
