state: qmValFiles
into: data/quartermaster/core.aix
helpers: qmlog, qmwrite
requires: rawcap, inchead
---
//! Validate a list of `.inc` files as they are (plan G11): the SelfTest's
//! check that the validation copy accepts code the game itself compiles and
//! rejects code that does not, and the seam for validating a mod's own files
//! (activation validation, Phase B). Nothing is written but validation copies
//! in the work folder.
//!
//! qm_gen_in: `vbox` (qmWrOpen's label: '' = <save>\quartermaster\), `vn`, and
//! per file k `v<k>` (absolute path), `vb<k>` (1: add a line that is not
//! Pascal, ref/validate.py BROKEN_LINE, so the candidate must be rejected)
//! and `vs<k>` (1: a global script, plain text, each line a Code value; one
//! that declares a class the game has loaded already cannot compile here -
//! context section 3).
//! Results in the named parser qm_gen_v: `vn`, per file `vr<k>` =
//! `<seq>|<token>|<ok>`, ok -1 when the file could not be read.
var qmVfIn : Integer = ParserSelectByKey('qm_gen_in');
var qmVfOut : Integer = ParserSelectByKey('qm_gen_v');
var qmVfPool : array [0..${rawcap}] of String;
var qmVfHead : array [0..${inchead}] of String;
var qmVfN : Integer = 0;
var qmVfK : Integer;
var qmVfC : Integer;
var qmVfNh : Integer;
var qmVfForm : Integer;
var qmVfSeq : Integer;
var qmVfOk : Integer;
var qmVfTok : String;
var qmVfWrap : String;
var qmVfPath : String;
if (qmVfOut=0) then
qmVfOut := ParserCreate('qm_gen_v');
ParserClearByHandle(qmVfOut);
if (qmVfIn<>0) then
begin
   qmVfC := qmWrOpen(ParserGetValueByKeyByHandle(qmVfIn, 'vbox'));
   qmVfN := ParserGetIntValueByKeyByHandle(qmVfIn, 'vn');
end;
for qmVfK:=0 to qmVfN-1 do
begin
   qmVfPath := ParserGetValueByKeyByHandle(qmVfIn, 'v'+IntToStr(qmVfK));
   qmVfNh := 0;
   qmVfForm := 0;
   qmVfC := -1;
   qmVfSeq := -1;
   qmVfOk := -1;
   qmVfTok := '-';
   if (ParserGetIntValueByKeyByHandle(qmVfIn, 'vs'+IntToStr(qmVfK))=1) then
   begin
      //! A global script is plain text, not an .inc: every line is one
      //! Code value of the validation copy.
      qmRawReadAt(qmVfPath, -1, qmVfPool, 0, qmVfC);
      if (qmVfC>=0) and (qmVfC<${rawcap}) then
      for qmVfForm:=0 to qmVfC-1 do
      qmVfPool[qmVfForm] := ';'+qmVfPool[qmVfForm];
      if (qmVfC=0) then
      qmVfC := -1;
   end
   else
   qmIncReadAt(qmVfPath, -1, qmVfPool, 0, qmVfHead, qmVfNh, qmVfC, qmVfForm);
   if (qmVfC>=0) and (qmVfC<${rawcap}) then
   begin
      if (ParserGetIntValueByKeyByHandle(qmVfIn, 'vb'+IntToStr(qmVfK))=1) then
      begin
         qmVfPool[qmVfC] := ';qm this line is not pascal (';
         qmVfC := qmVfC+1;
      end;
      qmValToken(qmVfPool, 0, qmVfC, qmVfHead, qmVfNh, 0, qmVfTok);
      qmValNext(qmVfSeq);
      qmVfWrap := qmWrWork+'val\'+IntToStr(qmVfSeq)+'.aix';
      qmValWrap(qmVfWrap, qmVfSeq, qmVfTok, qmVfPool, 0, qmVfC);
      qmVfOk := qmValRun(qmVfWrap, qmVfSeq, qmVfTok);
   end;
   ParserSetValueByKeyByHandle(qmVfOut, 'vr'+IntToStr(qmVfK), IntToStr(qmVfSeq)+'|'+qmVfTok+'|'+IntToStr(qmVfOk));
   qmLog('validate '+qmVfPath+' seq='+IntToStr(qmVfSeq)+' ok='+IntToStr(qmVfOk));
end;
ParserSetIntValueByKeyByHandle(qmVfOut, 'vn', qmVfN);
