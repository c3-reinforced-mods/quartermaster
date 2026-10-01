state: qmIndexStep
into: data/quartermaster/core.aix
helpers: qmhash
requires: indexbatch, shippedhooks
---
//! Second half of the index (plan G3; twin: ref/index.py build_index): up to
//! `indexbatch` scanned paths per call, from the cursor `cur` of qm_index, so
//! a caller can spread a long scan over frames. The Phase A scan is a few
//! hundred paths and FileAge costs 9-17 us (capability probes), so today one
//! call does it all.
//!
//! A mod provides a path when FileAge(<its dir>\data\<path>) is not -1.
//! Quartermaster's own folder is never asked: it provides exactly the hook
//! files it ships (`shippedhooks`, from the build). Asking would count its own
//! outputs as inputs (plan S8, guard 2).
//!
//! v<k> lists the providers' load positions (qm_mods pos<i>: qmOrder sets
//! them, and e<j>, to the load order before the index runs; ref/index.py
//! load_positions), `;` between, in load order (mods are visited in e<j>'s
//! order, Quartermaster last), a<k> their FileAge (`-` for Quartermaster).
//! qm_mods ord<pos> maps a position back to its row. Every hit also feeds
//! `<path> <FileAge>` LF into that mod's stamp hash; when the cursor reaches
//! the end, st<pos> holds each stamp and done is 1.
var qmIsIdx : Integer = ParserSelectByKey('qm_index');
var qmIsMods : Integer = ParserSelectByKey('qm_mods');
var qmIsN : Integer = ParserGetIntValueByKeyByHandle(qmIsIdx, 'n');
var qmIsCur : Integer = ParserGetIntValueByKeyByHandle(qmIsIdx, 'cur');
var qmIsCalls : Integer = ParserGetIntValueByKeyByHandle(qmIsIdx, 'calls');
var qmIsEn : Integer = ParserGetIntValueByKeyByHandle(qmIsMods, 'en');
var qmIsSelf : Integer = ParserGetIntValueByKeyByHandle(qmIsMods, 'self');
var qmIsSelfPos : Integer = -1;
if (qmIsSelf>=0) then
qmIsSelfPos := ParserGetIntValueByKeyByHandle(qmIsMods, 'pos'+IntToStr(qmIsSelf));
var qmIsDir : array [0..255] of String;
var qmIsPos : array [0..255] of Integer;
var qmIsH1 : array [0..255] of Integer;
var qmIsH2 : array [0..255] of Integer;
var qmIsHL : array [0..255] of Integer;
var qmIsJ : Integer;
var qmIsM : Integer;
var qmIsK : Integer;
var qmIsPath : String;
var qmIsProv : String;
var qmIsAges : String;
var qmIsAge : Integer;
var qmIsA1 : Integer;
var qmIsA2 : Integer;
var qmIsAL : Integer;
var qmIsStamp : String;
for qmIsJ:=0 to qmIsEn-1 do
begin
   qmIsM := ParserGetIntValueByKeyByHandle(qmIsMods, 'e'+IntToStr(qmIsJ));
   qmIsDir[qmIsJ] := ParserGetValueByKeyByHandle(qmIsMods, 'dir'+IntToStr(qmIsM));
   qmIsPos[qmIsJ] := ParserGetIntValueByKeyByHandle(qmIsMods, 'pos'+IntToStr(qmIsM));
   qmIsH1[qmIsJ] := ParserGetIntValueByKeyByHandle(qmIsIdx, 'h1_'+IntToStr(qmIsPos[qmIsJ]));
   qmIsH2[qmIsJ] := ParserGetIntValueByKeyByHandle(qmIsIdx, 'h2_'+IntToStr(qmIsPos[qmIsJ]));
   qmIsHL[qmIsJ] := ParserGetIntValueByKeyByHandle(qmIsIdx, 'hl_'+IntToStr(qmIsPos[qmIsJ]));
end;
var qmIsEnd : Integer = qmIsCur+${indexbatch};
if (qmIsEnd>qmIsN) then
qmIsEnd := qmIsN;
for qmIsK:=qmIsCur to qmIsEnd-1 do
begin
   qmIsPath := ParserGetValueByKeyByHandle(qmIsIdx, 'p'+IntToStr(qmIsK));
   qmIsProv := '';
   qmIsAges := '';
   for qmIsJ:=0 to qmIsEn-1 do
   begin
      qmIsAge := FileAge(qmIsDir[qmIsJ]+'\data\'+qmIsPath);
      qmIsCalls := qmIsCalls+1;
      if (qmIsAge<>-1) then
      begin
         if (qmIsProv<>'') then
         begin
            qmIsProv := qmIsProv+';';
            qmIsAges := qmIsAges+';';
         end;
         qmIsProv := qmIsProv+IntToStr(qmIsPos[qmIsJ]);
         qmIsAges := qmIsAges+IntToStr(qmIsAge);
         qmIsA1 := qmIsH1[qmIsJ];
         qmIsA2 := qmIsH2[qmIsJ];
         qmIsAL := qmIsHL[qmIsJ];
         qmHashStr(qmIsPath+' '+IntToStr(qmIsAge), qmIsA1, qmIsA2, qmIsAL);
         qmHashByte(10, qmIsA1, qmIsA2, qmIsAL);
         qmIsH1[qmIsJ] := qmIsA1;
         qmIsH2[qmIsJ] := qmIsA2;
         qmIsHL[qmIsJ] := qmIsAL;
      end;
   end;
   if (qmIsSelfPos>=0) and (StrPos('|'+qmIsPath+'|', ${shippedhooks})>0) then
   begin
      if (qmIsProv<>'') then
      begin
         qmIsProv := qmIsProv+';';
         qmIsAges := qmIsAges+';';
      end;
      qmIsProv := qmIsProv+IntToStr(qmIsSelfPos);
      qmIsAges := qmIsAges+'-';
   end;
   if (qmIsProv='') then
   begin
      qmIsProv := '-';
      qmIsAges := '-';
   end;
   ParserSetValueByKeyByHandle(qmIsIdx, 'v'+IntToStr(qmIsK), qmIsProv);
   ParserSetValueByKeyByHandle(qmIsIdx, 'a'+IntToStr(qmIsK), qmIsAges);
end;
for qmIsJ:=0 to qmIsEn-1 do
begin
   ParserSetIntValueByKeyByHandle(qmIsIdx, 'h1_'+IntToStr(qmIsPos[qmIsJ]), qmIsH1[qmIsJ]);
   ParserSetIntValueByKeyByHandle(qmIsIdx, 'h2_'+IntToStr(qmIsPos[qmIsJ]), qmIsH2[qmIsJ]);
   ParserSetIntValueByKeyByHandle(qmIsIdx, 'hl_'+IntToStr(qmIsPos[qmIsJ]), qmIsHL[qmIsJ]);
end;
ParserSetIntValueByKeyByHandle(qmIsIdx, 'cur', qmIsEnd);
ParserSetIntValueByKeyByHandle(qmIsIdx, 'calls', qmIsCalls);
if (qmIsEnd>=qmIsN) then
begin
   for qmIsJ:=0 to qmIsEn-1 do
   begin
      qmHashText(qmIsH1[qmIsJ], qmIsH2[qmIsJ], qmIsHL[qmIsJ], qmIsStamp);
      ParserSetValueByKeyByHandle(qmIsIdx, 'st'+IntToStr(qmIsPos[qmIsJ]), qmIsStamp);
   end;
   ParserSetIntValueByKeyByHandle(qmIsIdx, 'done', 1);
end;
