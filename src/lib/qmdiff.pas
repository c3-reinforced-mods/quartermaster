helpers: qmdiffsrc
requires: dcap, maxlines
---
//! Line diff (plan G8), the game side of ref/diff.py: the common prefix and
//! suffix are trimmed, then greedy Myers O(ND) runs with the trace of every
//! round kept for the backtrack. Tie-break, backtrack and hunk grouping are
//! ref/diff.py's statement for statement, so the same inputs give the same
//! hunks - ref/diff.py is the twin, proven against a DP LCS offline, and the
//! algorithm matched it exactly in game (docs/research/m0-probes.md probe 6).
//!
//! THE TRACE (decision 6 of docs/research/m0-probes.md). Round d keeps the
//! furthest x on its d+1 diagonals k = -d, -d+2, .., d:
//!
//!     qmDfT[d*(d+1) div 2 + j],   j = (k+d) div 2
//!
//! so rounds 0..D take (D+1)(D+2)/2 Integers. qmDfT holds rounds 0..998,
//! 499 500 Integers: 998 is the largest D whose trace fits plan S14's
//! 500 000-Integer budget (ref/diff.py d_cap). A diff that would need round
//! 999 is given up as "too different" and the caller falls back to winner
//! takes all. Round d reads round d-1 straight out of the trace (diagonal
//! k+1 is j, k-1 is j-1 there), so no separate V row is kept.
//!
//! THE LINES stay where the read seam (qmdiffsrc.pas) keeps them and are
//! fetched by index; the diff holds no String array of its own. Each line is
//! reduced to an Integer hash of its comparison key once, the snake compares
//! the hashes and confirms every equal hash on the two lines themselves, so a
//! collision can never make two different lines equal, and the diff is exact.
//!
//! Before qmDfRun: qmLnVc/qmLnVn = vanilla's source and line count with
//! qmLnVh filled (qmLnHashAll(.., 0, ..)), qmLnPc/qmLnPn the same for the
//! participant with qmLnPh filled (qmLnHashAll(.., 1, ..)) - unless a count
//! is over qmLnCap, in which case the diff refuses before it reads a hash.
//! After it: qmDfOk (1 = a script was found), qmDfWhy (0, 1 too-different,
//! 2 too-many-lines), qmDfD, qmDfDel, qmDfIns, qmDfP/qmDfQ (prefix, suffix),
//! qmDfCells (trace Integers written, ref's `cells`), and qmDfNh hunks: vanilla
//! [qmDfHs, qmDfHe) becomes participant [qmDfHms, qmDfHme), in file order.
//!
//! Every routine keeps its own local names (qmXx...): the language is
//! case-insensitive and a state is one namespace (plan S14).
//! Lines a file may have: ref/diff.py MAX_LINES; plan S14 sends bigger files
//! to winner-takes-all.
const qmLnCap = ${maxlines};
//! The largest D, ref/diff.py d_cap(): (998+1)(998+2)/2 = 499 500 <= 500 000.
//! qmDfT holds exactly that many Integers (tests/test_m3_build.py ties the
//! literal bound to ref).
const qmDfCap = ${dcap};
var qmLnVh : array [0..${maxlines}-1] of Integer;
var qmLnPh : array [0..${maxlines}-1] of Integer;
var qmLnVc : Integer = 0;
var qmLnVn : Integer = 0;
var qmLnPc : Integer = 0;
var qmLnPn : Integer = 0;
var qmDfT : array [0..499499] of Integer;
var qmDfEd : array [0..${dcap}] of Integer;
var qmDfEx : array [0..${dcap}] of Integer;
var qmDfEy : array [0..${dcap}] of Integer;
var qmDfHs : array [0..${dcap}] of Integer;
var qmDfHe : array [0..${dcap}] of Integer;
var qmDfHms : array [0..${dcap}] of Integer;
var qmDfHme : array [0..${dcap}] of Integer;
var qmDfOk : Integer = 0;
var qmDfWhy : Integer = 0;
var qmDfD : Integer = 0;
var qmDfDel : Integer = 0;
var qmDfIns : Integer = 0;
var qmDfP : Integer = 0;
var qmDfQ : Integer = 0;
var qmDfCells : Integer = 0;
var qmDfNh : Integer = 0;

//! 1 when two lines have the same comparison key. The same bytes with the
//! same first-line flag need no key; anything else is compared key to key.
function qmLnSame(const qmLsA : String; const qmLsFa : Integer; const qmLsB : String; const qmLsFb : Integer) : Integer;
begin
   var qmLsKa : String = '';
   var qmLsKb : String = '';
   Result := 0;
   if (qmLsFa=qmLsFb) and (qmLsA=qmLsB) then
   Result := 1
   else
   begin
      qmLnKey(qmLsA, qmLsFa, qmLsKa);
      qmLnKey(qmLsB, qmLsFb, qmLsKb);
      if (qmLsKa=qmLsKb) then
      Result := 1;
   end;
end;

//! 1 when vanilla line qmLeI equals line qmLeJ of the participant: the hashes
//! first, then the lines themselves.
function qmLnEq(const qmLeI : Integer; const qmLeJ : Integer) : Integer;
begin
   var qmLeFa : Integer = 0;
   var qmLeFb : Integer = 0;
   var qmLeA : String;
   var qmLeB : String;
   Result := 0;
   if (qmLnVh[qmLeI]=qmLnPh[qmLeJ]) then
   begin
      if (qmLeI=0) then
      qmLeFa := 1;
      if (qmLeJ=0) then
      qmLeFb := 1;
      qmLnRead(qmLnVc, qmLeI, qmLeA);
      qmLnRead(qmLnPc, qmLeJ, qmLeB);
      Result := qmLnSame(qmLeA, qmLeFa, qmLeB, qmLeFb);
   end;
end;

//! Hash lines 0..qmLaN-1 of a source into qmLnVh (qmLaWhich = 0) or
//! qmLnPh (1). qmLaSeq gets a hash of the whole sequence, the cheap first test
//! of "two participants made the very same file". Masking after the multiply
//! keeps it positive; the multiply may wrap, which is deterministic in this
//! engine (probe 4), and nothing but equality is ever asked of it.
procedure qmLnHashAll(const qmLaSrc : Integer; const qmLaN : Integer; const qmLaWhich : Integer; var qmLaSeq : Integer);
begin
   var qmLaI : Integer;
   var qmLaF : Integer;
   var qmLaH : Integer;
   var qmLaS : String;
   qmLaSeq := qmLaN and 1073741823;
   for qmLaI:=0 to qmLaN-1 do
   begin
      qmLaF := 0;
      if (qmLaI=0) then
      qmLaF := 1;
      qmLnRead(qmLaSrc, qmLaI, qmLaS);
      qmLaH := qmLnHash(qmLaS, qmLaF);
      if (qmLaWhich=0) then
      qmLnVh[qmLaI] := qmLaH
      else
      qmLnPh[qmLaI] := qmLaH;
      qmLaSeq := ((qmLaSeq*31)+qmLaH) and 1073741823;
   end;
end;

//! Vanilla (qmLnV*) against the participant (qmLnP*): ref/diff.py `diff`.
procedure qmDfRun;
begin
   var qmDrN : Integer = qmLnVn;
   var qmDrM : Integer = qmLnPn;
   var qmDrBn : Integer = 0;
   var qmDrBm : Integer = 0;
   var qmDrFound : Integer = -1;
   var qmDrD : Integer = 0;
   var qmDrJ : Integer = 0;
   var qmDrK : Integer = 0;
   var qmDrX : Integer = 0;
   var qmDrY : Integer = 0;
   var qmDrBp : Integer = 0;
   var qmDrBc : Integer = 0;
   var qmDrDown : Boolean = False;
   var qmDrJp : Integer = 0;
   var qmDrDd : Integer;
   var qmDrNe : Integer = 0;
   var qmDrE : Integer;
   var qmDrPx : Integer = -1;
   var qmDrPy : Integer = -1;
   var qmDrOpen : Boolean = False;
   qmDfOk := 0;
   qmDfWhy := 0;
   qmDfD := 0;
   qmDfDel := 0;
   qmDfIns := 0;
   qmDfP := 0;
   qmDfQ := 0;
   qmDfCells := 0;
   qmDfNh := 0;
   if (qmDrN>qmLnCap) or (qmDrM>qmLnCap) then
   qmDfWhy := 2
   else
   begin
      while (qmDfP<qmDrN) and (qmDfP<qmDrM) and (qmLnEq(qmDfP, qmDfP)=1) do
      qmDfP := qmDfP+1;
      while (qmDfQ<qmDrN-qmDfP) and (qmDfQ<qmDrM-qmDfP) and (qmLnEq(qmDrN-1-qmDfQ, qmDrM-1-qmDfQ)=1) do
      qmDfQ := qmDfQ+1;
      qmDrBn := qmDrN-qmDfP-qmDfQ;
      qmDrBm := qmDrM-qmDfP-qmDfQ;
      if (qmDrBn=0) and (qmDrBm=0) then
      qmDfOk := 1
      else
      begin
         //! Forward: round qmDrD, diagonal k = 2j-d. The tie-break of
         //! ref/diff.py: down (an insertion) from k+1 at j = 0, right (a
         //! deletion) from k-1 at j = d, otherwise down only when k+1 reached
         //! strictly further - on equal reach the deletion comes first.
         while (qmDrFound<0) and (qmDfWhy=0) do
         begin
            if (qmDrD>qmDfCap) then
            qmDfWhy := 1
            else
            begin
               qmDrBp := ((qmDrD-1)*qmDrD) div 2;
               qmDrBc := (qmDrD*(qmDrD+1)) div 2;
               qmDrJ := 0;
               while (qmDrJ<=qmDrD) and (qmDrFound<0) do
               begin
                  qmDrK := (2*qmDrJ)-qmDrD;
                  if (qmDrD=0) then
                  qmDrX := 0
                  else
                  if (qmDrJ=0) then
                  qmDrX := qmDfT[qmDrBp]
                  else
                  if (qmDrJ=qmDrD) then
                  qmDrX := qmDfT[qmDrBp+qmDrJ-1]+1
                  else
                  if (qmDfT[qmDrBp+qmDrJ-1]<qmDfT[qmDrBp+qmDrJ]) then
                  qmDrX := qmDfT[qmDrBp+qmDrJ]
                  else
                  qmDrX := qmDfT[qmDrBp+qmDrJ-1]+1;
                  qmDrY := qmDrX-qmDrK;
                  while (qmDrX<qmDrBn) and (qmDrY<qmDrBm) and (qmLnEq(qmDfP+qmDrX, qmDfP+qmDrY)=1) do
                  begin
                     qmDrX := qmDrX+1;
                     qmDrY := qmDrY+1;
                  end;
                  qmDfT[qmDrBc+qmDrJ] := qmDrX;
                  qmDfCells := qmDrBc+qmDrJ+1;
                  //! Only diagonal N-M ends at (N, M), so the first hit is the
                  //! only one and the rest of the round is not needed.
                  if (qmDrX>=qmDrBn) and (qmDrY>=qmDrBm) then
                  qmDrFound := qmDrJ
                  else
                  qmDrJ := qmDrJ+1;
               end;
               if (qmDrFound<0) then
               qmDrD := qmDrD+1;
            end;
         end;
         if (qmDrFound>=0) then
         begin
            qmDfOk := 1;
            qmDfD := qmDrD;
            //! Backtrack from (D, found) to (0, 0), one edit per round, the
            //! same rule re-applied: no direction bits are stored. The edits
            //! come out last first; qmDfEd 1 = insertion, 0 = deletion, at the
            //! trimmed point (qmDfEx, qmDfEy) where the edit starts.
            qmDrJ := qmDrFound;
            for qmDrDd:=qmDrD downto 1 do
            begin
               qmDrBp := ((qmDrDd-1)*qmDrDd) div 2;
               if (qmDrJ=0) then
               qmDrDown := True
               else
               if (qmDrJ=qmDrDd) then
               qmDrDown := False
               else
               qmDrDown := (qmDfT[qmDrBp+qmDrJ-1]<qmDfT[qmDrBp+qmDrJ]);
               if (qmDrDown) then
               qmDrJp := qmDrJ
               else
               qmDrJp := qmDrJ-1;
               qmDrX := qmDfT[qmDrBp+qmDrJp];
               qmDrY := qmDrX-((2*qmDrJp)-(qmDrDd-1));
               if (qmDrDown) then
               qmDfEd[qmDrNe] := 1
               else
               qmDfEd[qmDrNe] := 0;
               qmDfEx[qmDrNe] := qmDrX;
               qmDfEy[qmDrNe] := qmDrY;
               qmDrNe := qmDrNe+1;
               qmDrJ := qmDrJp;
            end;
            //! Hunks in file order: consecutive edits with no matched line
            //! between them are one hunk. qmDfNh is the open hunk's index
            //! while one is open, the count once the loop is done.
            for qmDrE:=qmDrNe-1 downto 0 do
            begin
               if (not qmDrOpen) or (qmDfEx[qmDrE]<>qmDrPx) or (qmDfEy[qmDrE]<>qmDrPy) then
               begin
                  if (qmDrOpen) then
                  qmDfNh := qmDfNh+1;
                  qmDfHs[qmDfNh] := qmDfP+qmDfEx[qmDrE];
                  qmDfHe[qmDfNh] := qmDfP+qmDfEx[qmDrE];
                  qmDfHms[qmDfNh] := qmDfP+qmDfEy[qmDrE];
                  qmDfHme[qmDfNh] := qmDfP+qmDfEy[qmDrE];
                  qmDrOpen := True;
               end;
               if (qmDfEd[qmDrE]=1) then
               begin
                  qmDfHme[qmDfNh] := qmDfHme[qmDfNh]+1;
                  qmDfIns := qmDfIns+1;
                  qmDrPx := qmDfEx[qmDrE];
                  qmDrPy := qmDfEy[qmDrE]+1;
               end
               else
               begin
                  qmDfHe[qmDfNh] := qmDfHe[qmDfNh]+1;
                  qmDfDel := qmDfDel+1;
                  qmDrPx := qmDfEx[qmDrE]+1;
                  qmDrPy := qmDfEy[qmDrE];
               end;
            end;
            if (qmDrOpen) then
            qmDfNh := qmDfNh+1;
         end;
      end;
   end;
end;
