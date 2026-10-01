helpers: qminc, qmhash
requires: rawcap, inchead
---
//! The validator (plan G11, S7); ref/validate.py is the twin and has the
//! evidence for every part of the validation copy.
//!
//! A candidate is a key-line header and Code values in a pool region, as
//! qmIncReadAt leaves them (internal strings). Its validation copy is a
//! one-state machine file outside every folder the engine loads from:
//! section.begin, Name = qmVal<seq>, UsedFileName, a Code struct whose first
//! value sets the flag and whose second is exit;, then the candidate's values
//! unchanged, and the CurrentState trailer - the shape probe 3 loaded
//! (its val\cand.aix, cap.0.log:94-105; m0-probes probe 3). The candidate's
//! own code is compiled but never run. The flag is the candidate's token in
//! the named parser qm_val (plan S4: no globals), key f<seq>.
//!
//! One validation trigger manager per boot, qm_valtm (plan S7): looked up by
//! name and added only when missing, because TriggerManagerAdd on a live name
//! makes a second, empty manager (cap.0.log:90-91). StateMachineLoadFromFile
//! replaces its states, re-reads a rewritten path at once and recovers after a
//! broken candidate (cap.0.log:85-89, :95-96, :103-105). Each candidate has
//! its own state name and flag key, so a load that silently failed can never
//! run an earlier candidate's state and set this one's flag.
//!
//! qmValIsGen    the CameraControl generation line (ref/validate.py GEN_PREFIX)
//! qmValToken    the content token: qhash of the key-line count, the key lines
//!               without leading spaces and the values, LF after each
//!               (qmVtSkip = 1 leaves generation lines out)
//! qmValNext     the next candidate number of this boot (qm_val `seq`)
//! qmValStage    the candidate as an .inc file, in the engine layout by value
//!               count: what the writer copies into the data mirror
//! qmValWrap     the validation copy
//! qmValRun      load and run it; 1 when the flag came back as the token
//! qmValCheck    1 when qm_val holds the token for candidate qmVcSeq: the
//!               writer's gate
//! qmValInsert   pool[at..] with the hook lines at their hook index (plan S5,
//!               ref/inc.py insert_at_hook), copied to pool[cat..]
function qmValIsGen(const qmVgV : String) : Boolean;
begin
   Result := (SubStr(qmVgV, 1, 19)=';const qmHookGen = ');
end;

procedure qmValToken(var qmVtPool : array [0..${rawcap}] of String; const qmVtAt : Integer; const qmVtN : Integer; var qmVtHead : array [0..${inchead}] of String; const qmVtNh : Integer; const qmVtSkip : Integer; var qmVtOut : String);
begin
   var qmVtH1 : Integer = 0;
   var qmVtH2 : Integer = 0;
   var qmVtL : Integer = 0;
   var qmVtK : Integer;
   var qmVtT : String;
   qmHashStr(IntToStr(qmVtNh), qmVtH1, qmVtH2, qmVtL);
   qmHashByte(10, qmVtH1, qmVtH2, qmVtL);
   for qmVtK:=0 to qmVtNh-1 do
   begin
      qmIncLstrip(qmVtHead[qmVtK], qmVtT);
      qmHashStr(qmVtT, qmVtH1, qmVtH2, qmVtL);
      qmHashByte(10, qmVtH1, qmVtH2, qmVtL);
   end;
   for qmVtK:=0 to qmVtN-1 do
   if (qmVtSkip=0) or (not qmValIsGen(qmVtPool[qmVtAt+qmVtK])) then
   begin
      qmHashStr(qmVtPool[qmVtAt+qmVtK], qmVtH1, qmVtH2, qmVtL);
      qmHashByte(10, qmVtH1, qmVtH2, qmVtL);
   end;
   qmHashText(qmVtH1, qmVtH2, qmVtL, qmVtOut);
end;

procedure qmValNext(var qmVnSeq : Integer);
begin
   var qmVnP : Integer = ParserSelectByKey('qm_val');
   if (qmVnP=0) then
   qmVnP := ParserCreate('qm_val');
   qmVnSeq := ParserGetIntValueByKeyByHandle(qmVnP, 'seq');
   ParserSetIntValueByKeyByHandle(qmVnP, 'seq', qmVnSeq+1);
end;

function qmValStage(const qmVsPath : String; var qmVsHead : array [0..${inchead}] of String; const qmVsNh : Integer; var qmVsPool : array [0..${rawcap}] of String; const qmVsAt : Integer; const qmVsN : Integer; var qmVsBytes : Integer) : Integer;
begin
   var qmVsK : Integer;
   qmIncBegin(qmVsPath, qmVsHead, qmVsNh, qmVsN);
   for qmVsK:=0 to qmVsN-1 do
   qmIncLine(qmVsPool[qmVsAt+qmVsK]);
   Result := qmIncEnd(qmVsBytes);
end;

procedure qmValWrap(const qmVwPath : String; const qmVwSeq : Integer; const qmVwTok : String; var qmVwPool : array [0..${rawcap}] of String; const qmVwAt : Integer; const qmVwN : Integer);
begin
   var qmVwAcc : Integer = 0;
   var qmVwCnt : Integer = 0;
   var qmVwK : Integer;
   var qmVwS : String = IntToStr(qmVwSeq);
   OpenFileStreamForWrite(qmVwPath);
   qmRawPutLine('section.begin', qmVwAcc, qmVwCnt);
   qmRawPutLine('   Name = qmVal'+qmVwS, qmVwAcc, qmVwCnt);
   qmRawPutLine('   UsedFileName = ', qmVwAcc, qmVwCnt);
   qmRawPutLine('   Code : struct.begin', qmVwAcc, qmVwCnt);
   qmRawPutLine('      [*] = ;ParserSetValueByKeyByHandle(ParserSelectByKey(''qm_val''), ''f'+qmVwS+''', '''+qmVwTok+''');', qmVwAcc, qmVwCnt);
   qmRawPutLine('      [*] = ;exit;', qmVwAcc, qmVwCnt);
   for qmVwK:=0 to qmVwN-1 do
   qmRawPutLine('      [*] = '+qmVwPool[qmVwAt+qmVwK], qmVwAcc, qmVwCnt);
   qmRawPutLine('   struct.end', qmVwAcc, qmVwCnt);
   qmRawPutLine('section.end', qmVwAcc, qmVwCnt);
   qmRawPutLine('', qmVwAcc, qmVwCnt);
   qmRawPutLine('section.begin', qmVwAcc, qmVwCnt);
   qmRawPutLine('   CurrentState = ', qmVwAcc, qmVwCnt);
   qmRawPutLine('   SaveVariables = False', qmVwAcc, qmVwCnt);
   qmRawPutLine('section.end', qmVwAcc, qmVwCnt);
   qmRawPutLine('', qmVwAcc, qmVwCnt);
   qmRawClose(qmVwAcc, qmVwCnt);
end;

function qmValRun(const qmVrPath : String; const qmVrSeq : Integer; const qmVrTok : String) : Integer;
begin
   var qmVrP : Integer = ParserSelectByKey('qm_val');
   var qmVrH : Integer = GetTriggerManagerStateMachineHandle('qm_valtm');
   var qmVrKey : String = 'f'+IntToStr(qmVrSeq);
   if (qmVrP=0) then
   qmVrP := ParserCreate('qm_val');
   ParserSetValueByKeyByHandle(qmVrP, qmVrKey, '');
   if (qmVrH=0) then
   begin
      TriggerManagerAdd('qm_valtm');
      qmVrH := GetTriggerManagerStateMachineHandle('qm_valtm');
   end;
   Result := 0;
   if (qmVrH<>0) and (FileAge(qmVrPath)<>-1) then
   begin
      StateMachineLoadFromFile(qmVrH, qmVrPath);
      StateMachineExecuteState(qmVrH, 'qmVal'+IntToStr(qmVrSeq), 0);
      if (ParserGetValueByKeyByHandle(qmVrP, qmVrKey)=qmVrTok) then
      Result := 1;
   end;
end;

function qmValCheck(const qmVcSeq : Integer; const qmVcTok : String) : Integer;
begin
   var qmVcP : Integer = ParserSelectByKey('qm_val');
   Result := 0;
   if (qmVcP<>0) and (qmVcTok<>'') then
   begin
      if (ParserGetValueByKeyByHandle(qmVcP, 'f'+IntToStr(qmVcSeq))=qmVcTok) then
      Result := 1;
   end;
end;

procedure qmValInsert(var qmViPool : array [0..${rawcap}] of String; const qmViAt : Integer; const qmViN : Integer; const qmViHat : Integer; const qmViHn : Integer; const qmViCat : Integer; var qmViCn : Integer);
begin
   var qmViK : Integer = qmIncHookIndex(qmViPool, qmViAt, qmViN);
   var qmViI : Integer;
   qmViCn := -1;
   if (qmViCat+qmViN+qmViHn<=${rawcap}+1) then
   begin
      for qmViI:=0 to qmViK-1 do
      qmViPool[qmViCat+qmViI] := qmViPool[qmViAt+qmViI];
      for qmViI:=0 to qmViHn-1 do
      qmViPool[qmViCat+qmViK+qmViI] := qmViPool[qmViHat+qmViI];
      for qmViI:=qmViK to qmViN-1 do
      qmViPool[qmViCat+qmViHn+qmViI] := qmViPool[qmViAt+qmViI];
      qmViCn := qmViN+qmViHn;
   end;
end;
