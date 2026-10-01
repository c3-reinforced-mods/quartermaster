state: qmCaseM4
into: data/quartermaster/selftest.aix
helpers: qmlog, qmstr, qmraw, qmhash, qmrepcfg
requires: rawcap
---
//! The SelfTest kind `m4gen` (plan G18) for the validator, the writer and the
//! report (G11-G13). tools/m4cases.py writes the case files and checks the
//! dump against ref/validate.py, ref/manifest.py and ref/report.py.
//!
//! Every generation runs in a sandbox (qmWrOpen): its data mirror, work
//! folder, validation copies, manifest and report all lie under
//! <save>\qm_test\out\m4\<label>\, which the harness collects and removes, so
//! a test never writes into a mod folder or leaves anything in the save
//! folder.
//!
//! Directives, after `kind m4gen`:
//!   val <path>        validate vanilla's <path> (vanilla.idx spelling) as it is
//!   valbroken <path>  the same with a line that is not Pascal (must fail)
//!   gen <label> [hooks] [drop <dir>]...
//!                     one generation into sandbox <label> from the boot's plan;
//!                     `hooks`: the pristine hook files are among the case files;
//!                     `drop <dir>`: that mod counts as disabled for this
//!                     generation - taken out of qm_index and qm_mods, qmPlan
//!                     run again - and is restored afterwards (the "disable one
//!                     participant, next run" step of the milestone, inside one
//!                     game session)
//! Dump rows (fields `|`, strings from the engine or a mod in hex):
//!   mod|<i>|<pos>|<on>|<dir>|<fo>|<id>   title|<i>|<title>   self|<i>   fp|<fp>
//!   idx|<k>|<path>|<class>|<providers>|<ages>        (paths with a provider)
//!   valv|<k>|<path>|<broken>|<seq>|<token>|<ok>
//!   plan|<label>|<m>|<path>|<act>|<str>|<why>|<win>|<providers>
//!   gen|<label>|<status>|<gen>|<outhash>|<fatal>|<written>|<same>|<changed>|<failed>|<removed>|<prevgen>
//!   path|<label>|<m>|<code>|<tag>|<job>|<err>|<participants>|<winner>|<first>|<n>|<tier>|<token>|<htoken>|<write>|<ci>
//!   cand|<label>|<m>|<tier>|<seq>|<token>|<ok>
//!   stale|<label>|<k>|<path>|<result>|<source>|<seq>|<token>|<ok>
//!   file|<label>|<name>|<lines hash>|<lines>        (outputs, manifest, report)
//!   qml|<label>|<lines>   qmr|<label>|<j>|<dir>|<tag>|<cn>   qmc|<label>|<j>|<k>|<text>
//!   rload|<label>|<keys compared>|<keys that differ>   (report.cfg read back)
var qmC4Rt : Integer = ParserSelectByKey('qm_case_rt');
var qmC4Out : String = ParserGetValueByKeyByHandle(qmC4Rt, 'out');
var qmC4Case : Integer = ParserSelectByKey('qm_case');
var qmC4Code : Integer = 0;
var qmC4Mods : Integer = ParserSelectByKey('qm_mods');
var qmC4Idx : Integer = ParserSelectByKey('qm_index');
var qmC4Plan : Integer = 0;
var qmC4Core : Integer = GetTriggerManagerStateMachineHandle('qm_core');
var qmC4In : Integer = ParserSelectByKey('qm_gen_in');
var qmC4Keep : Integer = ParserSelectByKey('qm_case_m4');
var qmC4App : String = ExtractFilePath(GetApplicationFileName);
var qmC4Save : String = GetAppSaveDirectoryPath;
var qmC4Pool : array [0..${rawcap}] of String;
var qmC4Sum : String = '';
var qmC4Vn : Integer = 0;
var qmC4Vp : String = '';
var qmC4Gens : Integer = 0;
var qmC4Bad : Integer = 0;
var qmC4I : Integer;
var qmC4J : Integer;
var qmC4K : Integer;
var qmC4M : Integer;
var qmC4N : Integer;
var qmC4C : Integer;
var qmC4Nm : Integer;
var qmC4Ni : Integer;
var qmC4V : String;
var qmC4T : String;
var qmC4S : String;
var qmC4U : String;
var qmC4W : String;
var qmC4X : String;
var qmC4Label : String;
var qmC4Hooks : String;
var qmC4Drops : String;
var qmC4Base : String;
var qmC4G : Integer = 0;
var qmC4Rep : Integer = 0;
var qmC4Rl : Integer = 0;
var qmC4Cmp : Integer = 0;
var qmC4Dif : Integer = 0;

procedure qmC4Row(const qmQyS : String);
begin
   qmC4Sum := qmC4Sum+qmQyS+'~013~010';
end;

//! lines hash (ref/selftest.py lines_hash) and line count of a file as the
//! raw reader reads it without a size; `-` when it is missing.
procedure qmC4File(const qmQfName : String; const qmQfPath : String);
begin
   var qmQfN : Integer = 0;
   var qmQfK : Integer;
   var qmQfH1 : Integer = 0;
   var qmQfH2 : Integer = 0;
   var qmQfL : Integer = 0;
   var qmQfT : String = '-';
   qmRawReadAt(qmQfPath, -1, qmC4Pool, 0, qmQfN);
   if (qmQfN>=0) then
   begin
      for qmQfK:=0 to qmQfN-1 do
      begin
         qmHashStr(qmC4Pool[qmQfK], qmQfH1, qmQfH2, qmQfL);
         qmHashByte(10, qmQfH1, qmQfH2, qmQfL);
      end;
      qmHashText(qmQfH1, qmQfH2, qmQfL, qmQfT);
   end;
   qmC4Row('file|'+qmC4Label+'|'+qmQfName+'|'+qmQfT+'|'+IntToStr(qmQfN));
end;

//! One qm_report key against its value read back from report.cfg.
procedure qmC4Same(const qmQkKey : String);
begin
   qmC4Cmp := qmC4Cmp+1;
   if (ParserGetValueByKeyByHandle(qmC4Rep, qmQkKey)<>ParserGetValueByKeyByHandle(qmC4Rl, qmQkKey)) then
   qmC4Dif := qmC4Dif+1;
end;

//! Validate the files collected so far (qmValFiles), one batch.
procedure qmC4Flush;
begin
   var qmQvK : Integer;
   var qmQvG : Integer;
   var qmQvP : String;
   var qmQvB : String;
   if (qmC4Vn>0) then
   begin
      ParserSetValueByKeyByHandle(qmC4In, 'vbox', 'val');
      ParserSetIntValueByKeyByHandle(qmC4In, 'vn', qmC4Vn);
      StateMachineExecuteState(qmC4Core, 'qmValFiles', 0);
      qmQvG := ParserSelectByKey('qm_gen_v');
      for qmQvK:=0 to qmC4Vn-1 do
      begin
         qmField(qmC4Vp, ' ', qmQvK, qmQvP);
         qmQvB := '0';
         if (ParserGetIntValueByKeyByHandle(qmC4In, 'vb'+IntToStr(qmQvK))=1) then
         qmQvB := '1';
         qmC4Row('valv|'+IntToStr(qmQvK)+'|'+qmQvP+'|'+qmQvB+'|'+ParserGetValueByKeyByHandle(qmQvG, 'vr'+IntToStr(qmQvK)));
      end;
      ParserClearByHandle(qmC4In);
      qmC4Vn := 0;
      qmC4Vp := '';
   end;
end;

//! Take the mod at dir qmQdDir out of qm_index and qm_mods (the originals are
//! in qm_case_m4, saved before the first drop).
procedure qmC4Drop(const qmQdDir : String);
begin
   var qmQdI : Integer;
   var qmQdK : Integer;
   var qmQdJ : Integer;
   var qmQdPos : String = '';
   var qmQdA : String;
   var qmQdB : String;
   var qmQdV : String;
   var qmQdW : String;
   var qmQdF : String;
   var qmQdG : String;
   qmLowerAscii(qmQdDir, qmQdA);
   for qmQdI:=0 to qmC4Nm-1 do
   begin
      qmLowerAscii(ParserGetValueByKeyByHandle(qmC4Mods, 'dir'+IntToStr(qmQdI)), qmQdB);
      if (qmQdA=qmQdB) then
      begin
         qmQdPos := IntToStr(ParserGetIntValueByKeyByHandle(qmC4Mods, 'pos'+IntToStr(qmQdI)));
         ParserSetIntValueByKeyByHandle(qmC4Mods, 'on'+IntToStr(qmQdI), 0);
      end;
   end;
   qmLog('selftest m4 drop '+qmQdDir+' position='+qmQdPos);
   if (qmQdPos<>'') then
   for qmQdK:=0 to qmC4Ni-1 do
   begin
      qmQdV := ParserGetValueByKeyByHandle(qmC4Idx, 'v'+IntToStr(qmQdK));
      if (qmQdV<>'-') then
      begin
         qmQdW := '';
         qmQdG := '';
         qmQdJ := 0;
         qmField(qmQdV, ';', 0, qmQdF);
         while (qmQdF<>'') do
         begin
            if (qmQdF<>qmQdPos) then
            begin
               if (qmQdW<>'') then
               begin
                  qmQdW := qmQdW+';';
                  qmQdG := qmQdG+';';
               end;
               qmQdW := qmQdW+qmQdF;
               qmField(ParserGetValueByKeyByHandle(qmC4Idx, 'a'+IntToStr(qmQdK)), ';', qmQdJ, qmQdB);
               qmQdG := qmQdG+qmQdB;
            end;
            qmQdJ := qmQdJ+1;
            qmField(qmQdV, ';', qmQdJ, qmQdF);
         end;
         if (qmQdW='') then
         begin
            qmQdW := '-';
            qmQdG := '-';
         end;
         ParserSetValueByKeyByHandle(qmC4Idx, 'v'+IntToStr(qmQdK), qmQdW);
         ParserSetValueByKeyByHandle(qmC4Idx, 'a'+IntToStr(qmQdK), qmQdG);
      end;
   end;
end;

//! The SelfTest's validation states are numbered from 1000 up: a generation
//! the boot may have run before it used the numbers below, and the harness
//! must know in advance which state names fail on purpose.
qmC4K := ParserSelectByKey('qm_val');
if (qmC4K=0) then
qmC4K := ParserCreate('qm_val');
if (ParserGetIntValueByKeyByHandle(qmC4K, 'seq')<1000) then
ParserSetIntValueByKeyByHandle(qmC4K, 'seq', 1000);
if (qmC4In=0) then
qmC4In := ParserCreate('qm_gen_in');
ParserClearByHandle(qmC4In);
if (qmC4Keep=0) then
qmC4Keep := ParserCreate('qm_case_m4');
ParserClearByHandle(qmC4Keep);
if (qmC4Case<>0) then
qmC4Code := ParserSelectByHandleByKey(qmC4Case, 'Code');
qmC4Nm := ParserGetIntValueByKeyByHandle(qmC4Mods, 'n');
qmC4Ni := ParserGetIntValueByKeyByHandle(qmC4Idx, 'n');

//! The inputs, for the twin.
for qmC4I:=0 to qmC4Nm-1 do
begin
   qmHex(ParserGetValueByKeyByHandle(qmC4Mods, 'dir'+IntToStr(qmC4I)), qmC4S);
   qmHex(ParserGetValueByKeyByHandle(qmC4Mods, 'id'+IntToStr(qmC4I)), qmC4T);
   qmC4Row('mod|'+IntToStr(qmC4I)+'|'+IntToStr(ParserGetIntValueByKeyByHandle(qmC4Mods, 'pos'+IntToStr(qmC4I)))+'|'+IntToStr(ParserGetIntValueByKeyByHandle(qmC4Mods, 'on'+IntToStr(qmC4I)))+'|'+qmC4S+'|'+ParserGetValueByKeyByHandle(qmC4Mods, 'fo'+IntToStr(qmC4I))+'|'+qmC4T);
   qmHex(ParserGetValueByKeyByHandle(qmC4Mods, 'tit'+IntToStr(qmC4I)), qmC4S);
   qmC4Row('title|'+IntToStr(qmC4I)+'|'+qmC4S);
   ParserSetIntValueByKeyByHandle(qmC4Keep, 'on'+IntToStr(qmC4I), ParserGetIntValueByKeyByHandle(qmC4Mods, 'on'+IntToStr(qmC4I)));
end;
qmC4Row('self|'+IntToStr(ParserGetIntValueByKeyByHandle(qmC4Mods, 'self')));
qmC4Row('fp|'+ParserGetValueByKeyByHandle(ParserSelectByKey('qm_rt'), 'fp'));
for qmC4K:=0 to qmC4Ni-1 do
begin
   qmC4V := ParserGetValueByKeyByHandle(qmC4Idx, 'v'+IntToStr(qmC4K));
   ParserSetValueByKeyByHandle(qmC4Keep, 'v'+IntToStr(qmC4K), qmC4V);
   ParserSetValueByKeyByHandle(qmC4Keep, 'a'+IntToStr(qmC4K), ParserGetValueByKeyByHandle(qmC4Idx, 'a'+IntToStr(qmC4K)));
   if (qmC4V<>'-') then
   qmC4Row('idx|'+IntToStr(qmC4K)+'|'+ParserGetValueByKeyByHandle(qmC4Idx, 'p'+IntToStr(qmC4K))+'|'+ParserGetValueByKeyByHandle(qmC4Idx, 'c'+IntToStr(qmC4K))+'|'+qmC4V+'|'+ParserGetValueByKeyByHandle(qmC4Idx, 'a'+IntToStr(qmC4K)));
end;

qmC4N := 0;
if (qmC4Code<>0) then
qmC4N := ParserGetCountByHandle(qmC4Code);
for qmC4I:=1 to qmC4N-1 do
begin
   qmC4V := ParserGetValueByIndexByHandle(qmC4Code, qmC4I);
   if (SubStr(qmC4V, 1, 1)=';') then
   qmC4V := SubStr(qmC4V, 2, StrLength(qmC4V)-1);
   qmField(qmC4V, ' ', 0, qmC4T);
   qmField(qmC4V, ' ', 1, qmC4S);
   if (qmC4T='val') or (qmC4T='valbroken') then
   begin
      ParserSetValueByKeyByHandle(qmC4In, 'v'+IntToStr(qmC4Vn), qmC4App+'data\'+qmC4S);
      if (qmC4T='valbroken') then
      ParserSetIntValueByKeyByHandle(qmC4In, 'vb'+IntToStr(qmC4Vn), 1);
      if (qmC4Vp<>'') then
      qmC4Vp := qmC4Vp+' ';
      qmC4Vp := qmC4Vp+qmC4S;
      qmC4Vn := qmC4Vn+1;
   end;
   if (qmC4T='gen') then
   begin
      qmC4Flush;
      qmC4Label := qmC4S;
      qmC4Hooks := '';
      qmC4Drops := '';
      qmC4K := 2;
      qmField(qmC4V, ' ', qmC4K, qmC4T);
      while (qmC4T<>'') do
      begin
         if (qmC4T='hooks') then
         qmC4Hooks := 'cases';
         if (qmC4T='drop') then
         begin
            qmC4K := qmC4K+1;
            qmField(qmC4V, ' ', qmC4K, qmC4U);
            qmC4Drop(qmC4U);
            qmC4Drops := qmC4Drops+' '+qmC4U;
         end;
         qmC4K := qmC4K+1;
         qmField(qmC4V, ' ', qmC4K, qmC4T);
      end;
      if (qmC4Drops<>'') then
      StateMachineExecuteState(qmC4Core, 'qmPlan', 0);
      qmC4Plan := ParserSelectByKey('qm_plan');
      ParserSetValueByKeyByHandle(qmC4In, 'sandbox', qmC4Label);
      ParserSetValueByKeyByHandle(qmC4In, 'hookdir', qmC4Hooks);
      qmLog('selftest m4 generation '+qmC4Label+' hooks='+qmC4Hooks+' drop='+qmC4Drops);
      StateMachineExecuteState(qmC4Core, 'qmGenerate', 0);
      StateMachineExecuteState(qmC4Core, 'qmReport', 0);
      ParserClearByHandle(qmC4In);
      qmC4Gens := qmC4Gens+1;

      //! What the generation did.
      qmC4G := ParserSelectByKey('qm_gen');
      qmC4Rep := ParserSelectByKey('qm_report');
      if (ParserGetValueByKeyByHandle(qmC4G, 'status')<>'ok') then
      qmC4Bad := qmC4Bad+1;
      for qmC4M:=0 to ParserGetIntValueByKeyByHandle(qmC4Plan, 'n')-1 do
      begin
         qmC4S := IntToStr(qmC4M);
         qmC4Row('plan|'+qmC4Label+'|'+qmC4S+'|'+ParserGetValueByKeyByHandle(qmC4Plan, 'path'+qmC4S)+'|'+ParserGetValueByKeyByHandle(qmC4Plan, 'act'+qmC4S)+'|'+ParserGetValueByKeyByHandle(qmC4Plan, 'str'+qmC4S)+'|'+ParserGetValueByKeyByHandle(qmC4Plan, 'why'+qmC4S)+'|'+ParserGetValueByKeyByHandle(qmC4Plan, 'win'+qmC4S)+'|'+ParserGetValueByKeyByHandle(qmC4Plan, 'prov'+qmC4S));
      end;
      qmC4Row('gen|'+qmC4Label+'|'+ParserGetValueByKeyByHandle(qmC4G, 'status')+'|'+ParserGetValueByKeyByHandle(qmC4G, 'gen')+'|'+ParserGetValueByKeyByHandle(qmC4G, 'outhash')+'|'+ParserGetValueByKeyByHandle(qmC4G, 'fatal')+'|'+ParserGetValueByKeyByHandle(qmC4G, 'written')+'|'+ParserGetValueByKeyByHandle(qmC4G, 'same')+'|'+ParserGetValueByKeyByHandle(qmC4G, 'changed')+'|'+ParserGetValueByKeyByHandle(qmC4G, 'failed')+'|'+ParserGetValueByKeyByHandle(qmC4G, 'removed')+'|'+ParserGetValueByKeyByHandle(qmC4G, 'prevgen'));
      qmC4Base := qmC4Save+'qm_test\out\m4\'+qmC4Label+'\';
      for qmC4M:=0 to ParserGetIntValueByKeyByHandle(qmC4G, 'n')-1 do
      begin
         qmC4S := IntToStr(qmC4M);
         qmHex(ParserGetValueByKeyByHandle(qmC4G, 'e'+qmC4S), qmC4X);
         qmC4Row('path|'+qmC4Label+'|'+qmC4S+'|'+ParserGetValueByKeyByHandle(qmC4G, 'x'+qmC4S)+'|'+ParserGetValueByKeyByHandle(qmC4G, 's'+qmC4S)+'|'+ParserGetValueByKeyByHandle(qmC4G, 'j'+qmC4S)+'|'+qmC4X+'|'+ParserGetValueByKeyByHandle(qmC4G, 'pp'+qmC4S)+'|'+ParserGetValueByKeyByHandle(qmC4G, 'pw'+qmC4S)+'|'+ParserGetValueByKeyByHandle(qmC4G, 'vf'+qmC4S)+'|'+ParserGetValueByKeyByHandle(qmC4G, 'vn'+qmC4S)+'|'+ParserGetValueByKeyByHandle(qmC4G, 'r'+qmC4S)+'|'+ParserGetValueByKeyByHandle(qmC4G, 'k'+qmC4S)+'|'+ParserGetValueByKeyByHandle(qmC4G, 'h'+qmC4S)+'|'+ParserGetValueByKeyByHandle(qmC4G, 'w'+qmC4S)+'|'+ParserGetValueByKeyByHandle(qmC4G, 'ci'+qmC4S));
         for qmC4J:=0 to ParserGetIntValueByKeyByHandle(qmC4G, 't'+qmC4S)-1 do
         qmC4Row('cand|'+qmC4Label+'|'+qmC4S+'|'+ParserGetValueByKeyByHandle(qmC4G, 't'+qmC4S+'_'+IntToStr(qmC4J)));
         if (ParserGetValueByKeyByHandle(qmC4G, 'w'+qmC4S)='yes') or (ParserGetValueByKeyByHandle(qmC4G, 'w'+qmC4S)='same') then
         qmC4File('out:'+ParserGetValueByKeyByHandle(qmC4Plan, 'path'+qmC4S), qmC4Base+'qmdir\data\'+ParserGetValueByKeyByHandle(qmC4Plan, 'path'+qmC4S));
      end;
      for qmC4J:=0 to ParserGetIntValueByKeyByHandle(qmC4G, 'sn')-1 do
      begin
         qmC4S := IntToStr(qmC4J);
         qmC4X := ParserGetValueByKeyByHandle(qmC4G, 'sc'+qmC4S);
         if (qmC4X='') then
         qmC4X := '-|-|-|-';
         qmField(qmC4X, '|', 1, qmC4T);
         qmField(qmC4X, '|', 2, qmC4U);
         qmField(qmC4X, '|', 3, qmC4W);
         qmC4Row('stale|'+qmC4Label+'|'+qmC4S+'|'+ParserGetValueByKeyByHandle(qmC4G, 'sp'+qmC4S)+'|'+ParserGetValueByKeyByHandle(qmC4G, 'sr'+qmC4S)+'|'+ParserGetValueByKeyByHandle(qmC4G, 'ss'+qmC4S)+'|'+qmC4T+'|'+qmC4U+'|'+qmC4W);
         if (ParserGetValueByKeyByHandle(qmC4G, 'sr'+qmC4S)='overwritten') then
         qmC4File('out:'+ParserGetValueByKeyByHandle(qmC4G, 'sp'+qmC4S), qmC4Base+'qmdir\data\'+ParserGetValueByKeyByHandle(qmC4G, 'sp'+qmC4S));
      end;
      qmC4File('manifest', qmC4Base+'qmdir\data\quartermaster\state\manifest.cfg');
      qmC4File('report', qmC4Base+'work\report.txt');
      qmC4Row('qml|'+qmC4Label+'|'+ParserGetValueByKeyByHandle(qmC4Rep, 'lines'));
      for qmC4J:=0 to ParserGetIntValueByKeyByHandle(qmC4Rep, 'n')-1 do
      begin
         qmC4S := IntToStr(qmC4J);
         qmHex(ParserGetValueByKeyByHandle(qmC4Rep, 'dir'+qmC4S), qmC4X);
         qmC4Row('qmr|'+qmC4Label+'|'+qmC4S+'|'+qmC4X+'|'+ParserGetValueByKeyByHandle(qmC4Rep, 'st'+qmC4S)+'|'+ParserGetValueByKeyByHandle(qmC4Rep, 'cn'+qmC4S));
         for qmC4K:=0 to ParserGetIntValueByKeyByHandle(qmC4Rep, 'cn'+qmC4S)-1 do
         begin
            qmHex(ParserGetValueByKeyByHandle(qmC4Rep, 'c'+qmC4S+'_'+IntToStr(qmC4K)), qmC4X);
            qmC4Row('qmc|'+qmC4Label+'|'+qmC4S+'|'+IntToStr(qmC4K)+'|'+qmC4X);
         end;
      end;

      //! report.cfg read back the way qmReportLoad reads it (qmRepCfgLoad,
      //! the engine's parser and the guard taken off) must give every
      //! qm_report key the same value.
      qmC4Rl := ParserSelectByKey('qm_case_rl');
      if (qmC4Rl=0) then
      qmC4Rl := ParserCreate('qm_case_rl');
      ParserClearByHandle(qmC4Rl);
      qmC4Cmp := 0;
      qmC4Dif := 0;
      if (FileAge(qmC4Base+'work\report.cfg')<>-1) then
      begin
         qmRepCfgLoad(qmC4Base+'work\report.cfg', qmC4Rl);
         qmC4Same('lines');
         qmC4Same('n');
         for qmC4J:=0 to ParserGetIntValueByKeyByHandle(qmC4Rep, 'lines')-1 do
         qmC4Same('l'+IntToStr(qmC4J));
         for qmC4J:=0 to ParserGetIntValueByKeyByHandle(qmC4Rep, 'n')-1 do
         begin
            qmC4S := IntToStr(qmC4J);
            qmC4Same('dir'+qmC4S);
            qmC4Same('st'+qmC4S);
            qmC4Same('cn'+qmC4S);
            for qmC4K:=0 to ParserGetIntValueByKeyByHandle(qmC4Rep, 'cn'+qmC4S)-1 do
            qmC4Same('c'+qmC4S+'_'+IntToStr(qmC4K));
         end;
      end
      else
      qmC4Dif := -1;
      qmC4Row('rload|'+qmC4Label+'|'+IntToStr(qmC4Cmp)+'|'+IntToStr(qmC4Dif));

      //! Undo the drops: the boot's own index, mod list and plan again.
      if (qmC4Drops<>'') then
      begin
         for qmC4K:=0 to qmC4Ni-1 do
         begin
            ParserSetValueByKeyByHandle(qmC4Idx, 'v'+IntToStr(qmC4K), ParserGetValueByKeyByHandle(qmC4Keep, 'v'+IntToStr(qmC4K)));
            ParserSetValueByKeyByHandle(qmC4Idx, 'a'+IntToStr(qmC4K), ParserGetValueByKeyByHandle(qmC4Keep, 'a'+IntToStr(qmC4K)));
         end;
         for qmC4K:=0 to qmC4Nm-1 do
         ParserSetIntValueByKeyByHandle(qmC4Mods, 'on'+IntToStr(qmC4K), ParserGetIntValueByKeyByHandle(qmC4Keep, 'on'+IntToStr(qmC4K)));
         StateMachineExecuteState(qmC4Core, 'qmPlan', 0);
      end;
   end;
end;
qmC4Flush;
qmC4Row('m4|'+IntToStr(qmC4Gens)+'|'+IntToStr(qmC4Bad));
qmRawWriteStr(qmC4Out, qmC4Sum);
qmLog('selftest m4 done generations='+IntToStr(qmC4Gens)+' not ok='+IntToStr(qmC4Bad));
if (qmC4Core=0) then
ParserSetValueByKeyByHandle(qmC4Rt, 'status', 'no-core')
else
if (qmC4Bad>0) then
ParserSetValueByKeyByHandle(qmC4Rt, 'status', 'incomplete')
else
ParserSetValueByKeyByHandle(qmC4Rt, 'status', 'ok');
