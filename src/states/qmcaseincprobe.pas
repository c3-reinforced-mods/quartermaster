state: qmCaseIncProbe
into: data/quartermaster/selftest.aix
helpers: qmstr, qmraw
requires:
---
//! SelfTest case `incprobe`: what the engine's parser does with `.inc` files.
//! ref/inc.py predicts what it can (tools/qmtest.py compares); the rest is how
//! the layouts are learnt.
//!
//!   probe <path>          load a vanilla file (absolute path), save it
//!                         unchanged as probe<k>_rt.inc, change it and save it
//!                         as probe<k>_ed.inc: with a Code node, value 0 becomes
//!                         `;// qm edited` and `;// qm appended` is appended
//!                         with the key [*]; without one, a child `Code` is
//!                         added and the value appended to it.
//!                         probe|k|path|<Code found 0/1>|<count before>|
//!                         <root count>|<count after>|<value 0 in hex>
//!   synth <name> <text>   write <text> (an internal string: ~NNN for any byte,
//!                         ~032 for a space) as <name> with the raw writer - so
//!                         it ends in padding spaces - load it with the parser
//!                         and dump every Code value in hex; save it unchanged
//!                         as <name>_rt.inc; then four ways to append, each
//!                         in a state of its own on a fresh load, so one that
//!                         does not compile or raises costs only its own line:
//!                         qmSyAppA [*] twice (_a), qmSyAppC a value with CR LF
//!                         and a second code line in it (_c), qmSyAppD the key
//!                         * (_d), qmSyAppB ParserSetValueByIndex one past the
//!                         end (_b).
//!                         synth|name|<root count>|<Code found>|<count>|<values>
//!                         synth<x>|name|<count after, -9 when the state did
//!                         not run>
//!
//! The dump is rewritten after every step, so a step that stops the state
//! leaves the evidence of the ones before it. Run m2a2 lost this whole state to
//! `Compile script error: qmCaseIncProbe`; the one construct it had that no
//! state before it had was the char literals written next to each other,
//! #13#10, now in qmSyAppC as #13+#10 and settled by the bisect case.
var qmIpRt : Integer = ParserSelectByKey('qm_case_rt');
var qmIpOutDir : String = ParserGetValueByKeyByHandle(qmIpRt, 'outdir');
var qmIpOut : String = ParserGetValueByKeyByHandle(qmIpRt, 'out');
var qmIpCode : Integer = ParserSelectByHandleByKey(ParserSelectByKey('qm_case'), 'Code');
var qmIpNd : Integer = ParserGetCountByHandle(qmIpCode);
var qmIpApp : String = ExtractFilePath(GetApplicationFileName)+'data\';
var qmIpDump : String = '';
var qmIpD : Integer;
var qmIpK : Integer = 0;
var qmIpJ : Integer;
var qmIpX : Integer;
var qmIpDir : String;
var qmIpVerb : String;
var qmIpPath : String;
var qmIpText : String;
var qmIpEsc : String;
var qmIpHex : String;
var qmIpAll : String;
var qmIpFile : String;
var qmIpStem : String;
var qmIpP : Integer;
var qmIpC : Integer;
var qmIpFound : Integer;
var qmIpBefore : Integer;
var qmIpRoot : Integer;
var qmIpAfter : Integer;
var qmIpV0 : String;
var qmIpT : Integer = GetTriggerManagerStateMachineHandle('qm_test');
for qmIpD:=1 to qmIpNd-1 do
begin
   qmIpDir := ParserGetValueByIndexByHandle(qmIpCode, qmIpD);
   if (SubStr(qmIpDir, 1, 1)=';') then
   qmIpDir := SubStr(qmIpDir, 2, StrLength(qmIpDir)-1);
   qmField(qmIpDir, ' ', 0, qmIpVerb);
   qmField(qmIpDir, ' ', 1, qmIpPath);
   qmField(qmIpDir, ' ', 2, qmIpText);
   qmEscape(qmIpPath, qmIpEsc);
   qmIpP := ParserSelectByKey('qm_case_inc');
   if (qmIpP=0) then
   qmIpP := ParserCreate('qm_case_inc');
   if (qmIpVerb='probe') and (FileAge(qmIpApp+qmIpPath)<>-1) then
   begin
      ParserClearByHandle(qmIpP);
      ParserLoadFromFileByHandle(qmIpP, qmIpApp+qmIpPath);
      qmIpRoot := ParserGetCountByHandle(qmIpP);
      qmIpC := ParserSelectByHandleByKey(qmIpP, 'Code');
      qmIpFound := 0;
      qmIpBefore := -1;
      qmIpV0 := '';
      if (qmIpC<>0) then
      begin
         qmIpFound := 1;
         qmIpBefore := ParserGetCountByHandle(qmIpC);
         if (qmIpBefore>0) then
         qmIpV0 := ParserGetValueByIndexByHandle(qmIpC, 0);
      end;
      ParserSaveToFileByHandle(qmIpP, qmIpOutDir+'probe'+IntToStr(qmIpK)+'_rt.inc');
      if (qmIpC<>0) then
      begin
         if (qmIpBefore>0) then
         begin
            ParserSelectByHandle(qmIpC);
            ParserSetValueByIndex(0, ';// qm edited');
         end;
      end
      else
      qmIpC := ParserAddChildByIndex(qmIpP, 'Code');
      ParserSetValueByKeyByHandle(qmIpC, '[*]', ';// qm appended');
      qmIpAfter := ParserGetCountByHandle(qmIpC);
      ParserSaveToFileByHandle(qmIpP, qmIpOutDir+'probe'+IntToStr(qmIpK)+'_ed.inc');
      qmHex(qmIpV0, qmIpHex);
      qmIpDump := qmIpDump+'probe|'+IntToStr(qmIpK)+'|'+qmIpEsc+'|'+IntToStr(qmIpFound)+'|'+IntToStr(qmIpBefore)+'|'+IntToStr(qmIpRoot)+'|'+IntToStr(qmIpAfter)+'|'+qmIpHex+'~013~010';
   end
   else
   if (qmIpVerb='synth') then
   begin
      //! The name is the path field; the text is written as it is.
      qmIpFile := qmIpOutDir+qmIpPath;
      qmIpStem := qmIpPath;
      if (StrPos('.', qmIpStem)>0) then
      qmIpStem := SubStr(qmIpStem, 1, StrPos('.', qmIpStem)-1);
      qmRawWriteStr(qmIpFile, qmIpText);
      ParserClearByHandle(qmIpP);
      ParserLoadFromFileByHandle(qmIpP, qmIpFile);
      qmIpRoot := ParserGetCountByHandle(qmIpP);
      qmIpC := ParserSelectByHandleByKey(qmIpP, 'Code');
      qmIpFound := 0;
      qmIpBefore := -1;
      qmIpAll := '';
      if (qmIpC<>0) then
      begin
         qmIpFound := 1;
         qmIpBefore := ParserGetCountByHandle(qmIpC);
         for qmIpJ:=0 to qmIpBefore-1 do
         begin
            qmHex(ParserGetValueByIndexByHandle(qmIpC, qmIpJ), qmIpHex);
            if (qmIpJ>0) then
            qmIpAll := qmIpAll+';';
            qmIpAll := qmIpAll+qmIpHex;
         end;
      end;
      ParserSaveToFileByHandle(qmIpP, qmIpOutDir+qmIpStem+'_rt.inc');
      qmIpDump := qmIpDump+'synth|'+qmIpEsc+'|'+IntToStr(qmIpRoot)+'|'+IntToStr(qmIpFound)+'|'+IntToStr(qmIpBefore)+'|'+qmIpAll+'~013~010';
      qmRawWriteStr(qmIpOut, qmIpDump);
      ParserSetValueByKeyByHandle(qmIpRt, 'sy_file', qmIpFile);
      for qmIpX:=0 to 3 do
      begin
         qmIpV0 := SubStr('acdb', qmIpX+1, 1);
         ParserSetValueByKeyByHandle(qmIpRt, 'sy_out', qmIpOutDir+qmIpStem+'_'+qmIpV0+'.inc');
         ParserSetIntValueByKeyByHandle(qmIpRt, 'sy_count', -9);
         qmIpDump := qmIpDump+'synth'+qmIpV0+'|'+qmIpEsc+'|started~013~010';
         qmRawWriteStr(qmIpOut, qmIpDump);
         StateMachineExecuteState(qmIpT, 'qmSyApp'+SubStr('ACDB', qmIpX+1, 1), 0);
         qmIpDump := qmIpDump+'synth'+qmIpV0+'|'+qmIpEsc+'|'+IntToStr(ParserGetIntValueByKeyByHandle(qmIpRt, 'sy_count'))+'~013~010';
         qmRawWriteStr(qmIpOut, qmIpDump);
      end;
   end
   else
   qmIpDump := qmIpDump+'missing|'+IntToStr(qmIpK)+'|'+qmIpEsc+'~013~010';
   qmIpK := qmIpK+1;
   qmRawWriteStr(qmIpOut, qmIpDump);
end;
qmRawWriteStr(qmIpOut, qmIpDump);
ParserSetValueByKeyByHandle(qmIpRt, 'status', 'ok');
