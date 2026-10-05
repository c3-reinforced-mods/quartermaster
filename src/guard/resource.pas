guard: QmGuard
into: data/scripts/resource.script
requires: guardstamp, h1mul, h1mod, h2mul, h2mod
---
//! The pre-compile guard (plan S17; twin: ref/guard.py, which has the rules).
//! tools/hbuild.py writes the installed game's resource.script first and these
//! lines after it, so they run where the vanilla file ends: the mod list is
//! final (SteamPrepareWorkshop has registered and switched on every new
//! subscription) and no library is compiled yet
//! (docs/research/guard-probes.md verdicts 1-3). Engine natives only: the
//! libraries do not exist at this point, and a name that does not resolve
//! here stops the game before anything can recover it.
//!
//! What it puts right before the libraries compile:
//!   - a mod that has not started with the others - a new subscription, or
//!     one switched on in modman since the last start that booted
//!     (compiled.cfg, qmGlobals) and not applied in the window since
//!     (chosen.cfg) - that ships a global script an enabled mod ships
//!     already is taken out of this start with SteamSyncWorkshopItems
//!     (verdict 6) and switched off in mods.ini. Without compiled.cfg only a
//!     new subscription (not in known.cfg) is judged. The engine's dialog
//!     for a start that stops is a string constant in cossacks.exe, so this
//!     is the one way it does not come up (until 0.1.2 a mod switched on in
//!     modman was not judged; 32 at once on 2026-10-02 stopped two starts in
//!     a row);
//!   - after a start that stopped (compile.cfg still pending and naming the
//!     mods enabled now, a CompileFramework or DoCreate compile error in that
//!     start's log), in steps a start each: the mods outside the last start
//!     that booted that clash by name, else all of those, else every mod but
//!     Quartermaster (ref/guard.py fallback);
//!   - Quartermaster loads last: an enabled mod after it that ships one of its
//!     hook files would replace the hook, and Quartermaster would boot late or
//!     not at all and never restart into its own order (proof run p4 of
//!     2026-09-28: 22 new subscriptions appended after it, State vs Country's
//!     doprogress.inc replaced the hook that runs qmTick).
//! Either way mods.ini is written back as it was loaded with only those
//! changes (the sync also switches every local mod off, Quartermaster
//! included), the note <save>\quartermaster\guard.cfg says what happened, and
//! the game restarts (run g8).
var qmGdSave : String = GetAppSaveDirectoryPath+'quartermaster\';
var qmGdWhy : String = '';
var qmGdAge : Integer = FileAge('.\data\scripts\resource.script');
//! The game this guard was built against: its own resource.script, read by
//! the absolute path (`.\data\` would read this mod's copy, the overlay's) the
//! way qmRawRead reads a text file - ReadInteger with the variable preset to
//! 0, bytes by `shr` and `and 255`, a zero byte ends it - and hashed as
//! ref/fingerprint.py qhash (ref/guard.py game_stamp). Content, not FileAge:
//! Steam stamps every file with the day it wrote it, so the date differs on
//! every installation and the guard was off on all but the author's (first
//! start on a second computer, 2026-10-02).
var qmGdStamp : String = '-';
var qmGdVan : String = ExtractFilePath(GetApplicationFileName)+'data\scripts\resource.script';
if (StringRegister7<>'') or (FileAge(GetAppSaveDirectoryPath+'mods.restore')<>-1) then
qmGdWhy := 'mp-sync'
else
begin
   if (FileAge(qmGdVan)<>-1) then
   begin
      var qmGdRf : Integer = OpenFileRead(qmGdVan);
      var qmGdRv : Integer = 0;
      var qmGdRb : Integer;
      var qmGdRs : Integer;
      var qmGdR1 : Integer = 0;
      var qmGdR2 : Integer = 0;
      var qmGdRl : Integer = 0;
      var qmGdRi : Integer = 0;
      var qmGdRe : Boolean = False;
      while (not qmGdRe) and (qmGdRi<262144) do
      begin
         qmGdRv := 0;
         ReadInteger(qmGdRf, qmGdRv);
         qmGdRi := qmGdRi+1;
         for qmGdRs:=0 to 3 do
         if (not qmGdRe) then
         begin
            qmGdRb := (qmGdRv shr (qmGdRs*8)) and 255;
            if (qmGdRb=0) then
            qmGdRe := True
            else
            begin
               qmGdR1 := (qmGdR1*${h1mul}+qmGdRb+1) mod ${h1mod};
               qmGdR2 := (qmGdR2*${h2mul}+qmGdRb+1) mod ${h2mod};
               qmGdRl := qmGdRl+1;
            end;
         end;
      end;
      CloseFile(qmGdRf);
      qmGdStamp := IntToStr(qmGdR1)+'-'+IntToStr(qmGdR2)+'-'+IntToStr(qmGdRl);
   end;
   if (qmGdStamp<>${guardstamp}) then
   qmGdWhy := 'game-version';
end;

var qmGdKnown : String = '|';
var qmGdHave : Boolean = False;
var qmGdK : Integer;
var qmGdV : String;
if (qmGdWhy='') then
begin
   var qmGdKp : Integer = ParserSelectByKey('qm_guard_known');
   if (qmGdKp=0) then
   qmGdKp := ParserCreate('qm_guard_known');
   ParserClearByHandle(qmGdKp);
   if (FileAge(qmGdSave+'known.cfg')<>-1) then
   if (ParserLoadFromFileByHandle(qmGdKp, qmGdSave+'known.cfg')) then
   begin
      var qmGdKc : Integer = ParserSelectByHandleByKey(qmGdKp, 'Code');
      if (qmGdKc<>0) then
      for qmGdK:=0 to ParserGetCountByHandle(qmGdKc)-1 do
      begin
         qmGdV := ParserGetValueByIndexByHandle(qmGdKc, qmGdK);
         if (qmGdV=';format|1') then
         qmGdHave := True;
         if ((SubStr(qmGdV, 1, 3)=';k|') or (SubStr(qmGdV, 1, 3)=';n|')) and (StrLength(qmGdV)>3) then
         begin
            qmGdV := StrToLowerCase(SubStr(qmGdV, 4, StrLength(qmGdV)-3));
            while (StrPos('/', qmGdV)>0) do
            qmGdV := StrReplace(qmGdV, '/', '\');
            qmGdKnown := qmGdKnown+qmGdV+'|';
         end;
      end;
   end;
end;

// After a start that stopped (ref/guard.py failed): compile.cfg, written
// before that start compiled, is still pending - pending = 1, its boot never
// set 0, or no pending key at all, a record of 0.1.2 - and that start's log
// holds a CompileFramework line (the libraries did not compile) or "Compile
// script error: DoCreate" (the main menu did not; of 1268 logs, the 19 with
// it never reached the menu). That log is the second newest cos_*.log by
// FileAge, the newest being this start's (qmLastStart finds it the same
// way); it is read the way resource.script is read above, at most 262144
// Integers. Whether that start had the mods enabled now (qmGdFset, qmGdFn)
// is told once the mod list is read: only then is it qmGdFailed.
var qmGdFailed : Boolean = False;
var qmGdFailLog : Boolean = False;
var qmGdFset : String = '|';
var qmGdFn : Integer = 0;
if (qmGdWhy='') then
begin
   var qmGdPc : Integer = ParserSelectByKey('qm_guard_compile');
   if (qmGdPc=0) then
   qmGdPc := ParserCreate('qm_guard_compile');
   ParserClearByHandle(qmGdPc);
   var qmGdPend : Boolean = False;
   if (FileAge(qmGdSave+'compile.cfg')<>-1) then
   if (ParserLoadFromFileByHandle(qmGdPc, qmGdSave+'compile.cfg')) then
   begin
      qmGdV := ParserGetValueByKeyByHandle(qmGdPc, 'pending');
      if (qmGdV='1') or (qmGdV='') then
      qmGdPend := True;
      // Its mods (ref/guard.py compiled_dirs): a count of at least 1.
      qmGdFn := ParserGetIntValueByKeyByHandle(qmGdPc, 'n');
      if (qmGdFn>512) then
      qmGdFn := 512;
      for qmGdK:=0 to qmGdFn-1 do
      begin
         qmGdV := StrToLowerCase(ParserGetValueByKeyByHandle(qmGdPc, 'd'+IntToStr(qmGdK)));
         while (StrPos('/', qmGdV)>0) do
         qmGdV := StrReplace(qmGdV, '/', '\');
         qmGdFset := qmGdFset+qmGdV+'|';
      end;
   end;
   if (qmGdPend) and (qmGdFn>0) then
   begin
      var qmGdLp : Integer = ParserSelectByKey('qm_guard_logs');
      if (qmGdLp=0) then
      begin
         ParserCreate('qm_guard_logs');
         qmGdLp := ParserSelectByKey('qm_guard_logs');
      end;
      ParserClearByHandle(qmGdLp);
      ParserGetFilesInRoot(GetAppSaveDirectoryPath+'log\cos_*.log');
      var qmGdLa1 : Integer = -1;
      var qmGdLa2 : Integer = -1;
      var qmGdLn1 : String = '';
      var qmGdLn2 : String = '';
      var qmGdLa : Integer;
      var qmGdLnm : String;
      for qmGdK:=0 to ParserGetCountByHandle(qmGdLp)-1 do
      begin
         qmGdLnm := ParserGetValueByIndexByHandle(qmGdLp, qmGdK);
         qmGdLa := FileAge(GetAppSaveDirectoryPath+'log\'+qmGdLnm);
         if (qmGdLa>qmGdLa1) then
         begin
            qmGdLa2 := qmGdLa1;
            qmGdLn2 := qmGdLn1;
            qmGdLa1 := qmGdLa;
            qmGdLn1 := qmGdLnm;
         end
         else
         if (qmGdLa>qmGdLa2) then
         begin
            qmGdLa2 := qmGdLa;
            qmGdLn2 := qmGdLnm;
         end;
      end;
      if (qmGdLn2<>'') then
      begin
         var qmGdLf : Integer = OpenFileRead(GetAppSaveDirectoryPath+'log\'+qmGdLn2);
         var qmGdPat : String = 'CompileFramework';
         var qmGdPat2 : String = 'Compile script error: DoCreate';
         var qmGdPm : Integer = 0;
         var qmGdPm2 : Integer = 0;
         var qmGdLv : Integer = 0;
         var qmGdLb : Integer;
         var qmGdLs : Integer;
         var qmGdLi : Integer = 0;
         var qmGdLend : Boolean = False;
         while (not qmGdLend) and (not qmGdFailLog) and (qmGdLi<262144) do
         begin
            qmGdLv := 0;
            ReadInteger(qmGdLf, qmGdLv);
            qmGdLi := qmGdLi+1;
            for qmGdLs:=0 to 3 do
            if (not qmGdLend) and (not qmGdFailLog) then
            begin
               qmGdLb := (qmGdLv shr (qmGdLs*8)) and 255;
               if (qmGdLb=0) then
               qmGdLend := True
               else
               begin
                  // 'C' is in the word only at its start: a mismatch starts over.
                  if (qmGdLb=Ord(SubStr(qmGdPat, qmGdPm+1, 1))) then
                  qmGdPm := qmGdPm+1
                  else
                  if (qmGdLb=Ord(SubStr(qmGdPat, 1, 1))) then
                  qmGdPm := 1
                  else
                  qmGdPm := 0;
                  // The second has a 'C' at its start and one in 'DoCreate':
                  // after '...DoC' an 'o' makes 'Co', its start again.
                  if (qmGdLb=Ord(SubStr(qmGdPat2, qmGdPm2+1, 1))) then
                  qmGdPm2 := qmGdPm2+1
                  else
                  if (qmGdPm2=25) and (qmGdLb=Ord(SubStr(qmGdPat2, 2, 1))) then
                  qmGdPm2 := 2
                  else
                  if (qmGdLb=Ord(SubStr(qmGdPat2, 1, 1))) then
                  qmGdPm2 := 1
                  else
                  qmGdPm2 := 0;
                  if (qmGdPm=16) or (qmGdPm2=30) then
                  qmGdFailLog := True;
               end;
            end;
         end;
         CloseFile(qmGdLf);
      end;
   end;
end;

// The mods of the last start that booted (ref/guard.py compiled_dirs): a
// count of at least 1 - a boot always has Quartermaster on - or no record
// (after a failed start the good set is then the game alone).
var qmGdGood : String = '|';
var qmGdHaveC : Boolean = False;
if (qmGdWhy='') then
begin
   var qmGdCc : Integer = ParserSelectByKey('qm_guard_compiled');
   if (qmGdCc=0) then
   qmGdCc := ParserCreate('qm_guard_compiled');
   ParserClearByHandle(qmGdCc);
   if (FileAge(qmGdSave+'compiled.cfg')<>-1) then
   if (ParserLoadFromFileByHandle(qmGdCc, qmGdSave+'compiled.cfg')) then
   begin
      var qmGdCn : Integer = ParserGetIntValueByKeyByHandle(qmGdCc, 'n');
      if (qmGdCn>512) then
      qmGdCn := 512;
      if (qmGdCn>0) then
      begin
         qmGdHaveC := True;
         for qmGdK:=0 to qmGdCn-1 do
         begin
            qmGdV := StrToLowerCase(ParserGetValueByKeyByHandle(qmGdCc, 'd'+IntToStr(qmGdK)));
            while (StrPos('/', qmGdV)>0) do
            qmGdV := StrReplace(qmGdV, '/', '\');
            qmGdGood := qmGdGood+qmGdV+'|';
         end;
      end;
   end;
end;
// The mods the player applied in the window since the last boot (chosen.cfg,
// the same flat form; the boot clears it to n = 0): trusted on an ordinary
// start, so a pair that names alone would refuse can still be run.
var qmGdChosen : String = '';
var qmGdHaveCh : Boolean = False;
if (qmGdWhy='') then
begin
   var qmGdCh : Integer = ParserSelectByKey('qm_guard_chosen');
   if (qmGdCh=0) then
   qmGdCh := ParserCreate('qm_guard_chosen');
   ParserClearByHandle(qmGdCh);
   if (FileAge(qmGdSave+'chosen.cfg')<>-1) then
   if (ParserLoadFromFileByHandle(qmGdCh, qmGdSave+'chosen.cfg')) then
   begin
      var qmGdChn : Integer = ParserGetIntValueByKeyByHandle(qmGdCh, 'n');
      if (qmGdChn>512) then
      qmGdChn := 512;
      if (qmGdChn>0) then
      begin
         qmGdHaveCh := True;
         for qmGdK:=0 to qmGdChn-1 do
         begin
            qmGdV := StrToLowerCase(ParserGetValueByKeyByHandle(qmGdCh, 'd'+IntToStr(qmGdK)));
            while (StrPos('/', qmGdV)>0) do
            qmGdV := StrReplace(qmGdV, '/', '\');
            qmGdChosen := qmGdChosen+qmGdV+'|';
         end;
      end;
   end;
end;
// What claims first (ref/guard.py decide, Plan.basis), set once the mod list
// is read: on an ordinary start the last start that booted and the chosen
// set, without that record known.cfg - every mod but a new subscription;
// after a failed start the good set. qmGdJudge: whether any mod is judged at
// all (an ordinary start without either record is a first boot).
var qmGdBasis : String = '-';
var qmGdTrust : String = '|';
var qmGdJudge : Boolean = False;

// Every registered mod: 0 off or Quartermaster, 1 claims first (known, or in
// the good set) and on, 2 judged and on, 3 judged and kept, 4 switched off.
var qmGdN : Integer = ModLibraryGetCount;
if (qmGdN>512) then
qmGdN := 512;
var qmGdDir : array [0..511] of String;
var qmGdFold : array [0..511] of String;
var qmGdTit : array [0..511] of String;
var qmGdFiles : array [0..511] of String;
var qmGdState : array [0..511] of Integer;
var qmGdOn : array [0..511] of Integer;
var qmGdHit : array [0..511] of String;
var qmGdBy : array [0..511] of Integer;
// What an enabled mod's about.cfg says (ref/guard.py about_of, mod_names): the
// id it declares, the folder identity (Workshop number or local folder name),
// and the id its `extends` names. qmGdAny: some mod extends another.
var qmGdId : array [0..511] of String;
var qmGdFid : array [0..511] of String;
var qmGdExt : array [0..511] of String;
var qmGdAny : Boolean = False;
var qmGdWsDir : String = '..\..\workshop\content\333420\';
var qmGdIdSet : String = 'abcdefghijklmnopqrstuvwxyz0123456789_.-';
var qmGdTbl : String = ' !"#$%&''()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz';
var qmGdAp, qmGdAcur, qmGdAk, qmGdAva, qmGdAid, qmGdAex, qmGdAe, qmGdXr : String;
var qmGdAf, qmGdAv, qmGdAb, qmGdAs, qmGdAi, qmGdAn, qmGdAeq, qmGdAc, qmGdXc, qmGdXb : Integer;
var qmGdAdone, qmGdAok, qmGdXo, qmGdQ : Boolean;
// A judged mod's related mods, as `|j|` (an add-on and its base).
var qmGdRel : String = '|';
var qmGdTag, qmGdD, qmGdLast, qmGdT, qmGdOwn, qmGdDesc, qmGdTags, qmGdUrl, qmGdNt : String;
var qmGdNumf, qmGdVis : Integer;
var qmGdDis, qmGdAcc, qmGdBan, qmGdRoot : Boolean;
var qmGdI : Integer;
var qmGdJ : Integer;
var qmGdC : Integer;
var qmGdO : Integer;
var qmGdOk : Boolean;
var qmGdP : Integer;
var qmGdF : String;
var qmGdRest : String;
var qmGdClaim : String = '|';
var qmGdOffN : Integer = 0;
var qmGdOffKey : String = '';
var qmGdSelf : Integer = -1;
var qmGdLate : Integer = 0;
var qmGdLateDir : String = '';
var qmGdLateFile : String = '';
// The note's `why` (ref/guard.py Plan.why of an `off` plan).
var qmGdRule : String = 'conflict';
if (qmGdWhy='') then
begin
   var qmGdFp : Integer = ParserSelectByKey('qm_guard_files');
   if (qmGdFp=0) then
   qmGdFp := ParserCreate('qm_guard_files');
   for qmGdI:=0 to qmGdN-1 do
   begin
      ModLibraryGetData(qmGdI, qmGdTag, qmGdD, qmGdLast, qmGdT, qmGdOwn, qmGdDesc, qmGdTags, qmGdUrl, qmGdNt, qmGdNumf, qmGdVis, qmGdDis, qmGdAcc, qmGdBan, qmGdRoot);
      qmGdDir[qmGdI] := qmGdD;
      qmGdTit[qmGdI] := qmGdT;
      qmGdFiles[qmGdI] := '|';
      qmGdState[qmGdI] := 0;
      qmGdOn[qmGdI] := 0;
      qmGdHit[qmGdI] := '';
      qmGdBy[qmGdI] := -1;
      qmGdId[qmGdI] := '';
      qmGdFid[qmGdI] := '';
      qmGdExt[qmGdI] := '';
      qmGdOk := (StrLength(qmGdD)>0) and (StrPos('~', qmGdD)=0);
      for qmGdC:=1 to StrLength(qmGdD) do
      begin
         qmGdO := Ord(SubStr(qmGdD, qmGdC, 1));
         if (qmGdO<32) or (qmGdO>126) then
         qmGdOk := False;
      end;
      qmGdFold[qmGdI] := '';
      if (qmGdOk) then
      begin
         qmGdFold[qmGdI] := StrToLowerCase(qmGdD);
         while (StrPos('/', qmGdFold[qmGdI])>0) do
         qmGdFold[qmGdI] := StrReplace(qmGdFold[qmGdI], '/', '\');
      end;
      if (not qmGdDis) then
      qmGdOn[qmGdI] := 1;
      // Quartermaster: the last enabled mod with core.aix (ref/index.py find_self).
      if (not qmGdDis) and (ModLibGetFileExist(qmGdI, 'data\quartermaster\core.aix')) then
      qmGdSelf := qmGdI;
      if (not qmGdDis) and (not ModLibGetFileExist(qmGdI, 'data\quartermaster\core.aix')) then
      begin
         qmGdState[qmGdI] := 1;
         qmGdFp := ParserSelectByKey('qm_guard_files');
         ParserClearByHandle(qmGdFp);
         ParserGetFilesInRoot(qmGdD+'\data\scripts\lib\*.script');
         for qmGdK:=0 to ParserGetCountByHandle(qmGdFp)-1 do
         qmGdFiles[qmGdI] := qmGdFiles[qmGdI]+'lib\'+StrToLowerCase(ParserGetValueByIndexByHandle(qmGdFp, qmGdK))+'|';
         if (ModLibGetFileExist(qmGdI, 'data\scripts\dmscript.global')) then
         qmGdFiles[qmGdI] := qmGdFiles[qmGdI]+'dmscript.global|';
         if (ModLibGetFileExist(qmGdI, 'data\scripts\dmscript.source')) then
         qmGdFiles[qmGdI] := qmGdFiles[qmGdI]+'dmscript.source|';
      end;
   end;
   // What each mod that ships a global script says about itself (ref/guard.py
   // about_of, mod_names): only such a mod can claim a file or be judged, so
   // no other about.cfg is read. After the list, so Quartermaster's own folder
   // is known for the known\<number>.cfg fallback.
   for qmGdI:=0 to qmGdN-1 do
   if (qmGdState[qmGdI]=1) and (StrLength(qmGdFiles[qmGdI])>1) then
   begin
      // Its folder identity (ref/order.py identity): the digits after the
      // Workshop folder, or the name after mods\ with no further \.
      if (qmGdFold[qmGdI]<>'') then
      begin
         qmGdXr := '';
         if (SubStr(qmGdFold[qmGdI], 1, StrLength(qmGdWsDir))=qmGdWsDir) then
         begin
            qmGdXr := SubStr(qmGdFold[qmGdI], StrLength(qmGdWsDir)+1, StrLength(qmGdFold[qmGdI])-StrLength(qmGdWsDir));
            qmGdXo := (StrLength(qmGdXr)>0);
            for qmGdXc:=1 to StrLength(qmGdXr) do
            begin
               qmGdXb := Ord(SubStr(qmGdXr, qmGdXc, 1));
               if (qmGdXb<48) or (qmGdXb>57) then
               qmGdXo := False;
            end;
            if (not qmGdXo) then
            qmGdXr := '';
         end
         else
         if (SubStr(qmGdFold[qmGdI], 1, 5)='mods\') then
         begin
            qmGdXr := SubStr(qmGdFold[qmGdI], 6, StrLength(qmGdFold[qmGdI])-5);
            if (StrPos('\', qmGdXr)>0) then
            qmGdXr := '';
         end;
         qmGdFid[qmGdI] := qmGdXr;
      end;
      // Its about.cfg - or, for a Workshop mod without one, Quartermaster's
      // known\<number>.cfg, as the manager reads it (qmabout.pas): the last
      // `id` and `extends` line, read as the manager reads the file - bytes
      // up to a zero byte or 262144 Integers, the text table with ~NNN for
      // any other byte, a tab as a space - and kept only when a valid id
      // (ref/guard.py about_of).
      qmGdAp := qmGdDir[qmGdI]+'\about.cfg';
      if (FileAge(qmGdAp)=-1) and (qmGdSelf>=0) and (qmGdFid[qmGdI]<>'') and (SubStr(qmGdFold[qmGdI], 1, StrLength(qmGdWsDir))=qmGdWsDir) then
      qmGdAp := qmGdDir[qmGdSelf]+'\data\quartermaster\known\'+qmGdFid[qmGdI]+'.cfg';
      if (FileAge(qmGdAp)<>-1) then
      begin
         qmGdAf := OpenFileRead(qmGdAp);
         qmGdAcur := '';
         qmGdAid := '';
         qmGdAex := '';
         qmGdAn := 0;
         qmGdAi := 0;
         qmGdAdone := False;
         while (not qmGdAdone) do
         begin
            qmGdAv := 0;
            if (qmGdAi<262144) then
            ReadInteger(qmGdAf, qmGdAv);
            qmGdAi := qmGdAi+1;
            for qmGdAs:=0 to 3 do
            if (not qmGdAdone) then
            begin
               qmGdAb := (qmGdAv shr (qmGdAs*8)) and 255;
               // The end closes the last line like a line feed does.
               if (qmGdAb=0) then
               begin
                  qmGdAdone := True;
                  qmGdAb := 10;
               end;
               if (qmGdAb=10) then
               begin
                  qmGdAn := qmGdAn+1;
                  if (qmGdAn=1) and (SubStr(qmGdAcur, 1, 12)='~239~187~191') then
                  qmGdAcur := SubStr(qmGdAcur, 13, StrLength(qmGdAcur)-12);
                  while (SubStr(qmGdAcur, 1, 1)=' ') do
                  qmGdAcur := SubStr(qmGdAcur, 2, StrLength(qmGdAcur)-1);
                  while (StrLength(qmGdAcur)>0) and (SubStr(qmGdAcur, StrLength(qmGdAcur), 1)=' ') do
                  qmGdAcur := SubStr(qmGdAcur, 1, StrLength(qmGdAcur)-1);
                  qmGdAeq := StrPos('=', qmGdAcur);
                  // A comment line's key starts with `#`: it is never id or extends.
                  if (qmGdAeq>1) then
                  begin
                     qmGdAk := SubStr(qmGdAcur, 1, qmGdAeq-1);
                     qmGdAva := SubStr(qmGdAcur, qmGdAeq+1, StrLength(qmGdAcur)-qmGdAeq);
                     while (StrLength(qmGdAk)>0) and (SubStr(qmGdAk, StrLength(qmGdAk), 1)=' ') do
                     qmGdAk := SubStr(qmGdAk, 1, StrLength(qmGdAk)-1);
                     while (SubStr(qmGdAva, 1, 1)=' ') do
                     qmGdAva := SubStr(qmGdAva, 2, StrLength(qmGdAva)-1);
                     qmGdAk := StrToLowerCase(qmGdAk);
                     if (qmGdAk='id') then
                     qmGdAid := StrToLowerCase(qmGdAva);
                     if (qmGdAk='extends') then
                     qmGdAex := StrToLowerCase(qmGdAva);
                  end;
                  qmGdAcur := '';
               end
               else
               if (qmGdAb<>13) then
               begin
                  if (qmGdAb=9) then
                  qmGdAcur := qmGdAcur+' '
                  else
                  if (qmGdAb>=32) and (qmGdAb<=122) then
                  qmGdAcur := qmGdAcur+SubStr(qmGdTbl, qmGdAb-31, 1)
                  else
                  begin
                     qmGdAe := IntToStr(qmGdAb);
                     while (StrLength(qmGdAe)<3) do
                     qmGdAe := '0'+qmGdAe;
                     qmGdAcur := qmGdAcur+'~'+qmGdAe;
                  end;
               end;
            end;
         end;
         CloseFile(qmGdAf);
         // An id that is not a-z, 0-9, _ . - counts as none.
         qmGdAva := qmGdAid;
         for qmGdAs:=1 to 2 do
         begin
            qmGdAok := (StrLength(qmGdAva)>0);
            for qmGdAc:=1 to StrLength(qmGdAva) do
            if (StrPos(SubStr(qmGdAva, qmGdAc, 1), qmGdIdSet)=0) then
            qmGdAok := False;
            if (not qmGdAok) then
            qmGdAva := '';
            if (qmGdAs=1) then
            begin
               qmGdAid := qmGdAva;
               qmGdAva := qmGdAex;
            end
            else
            qmGdAex := qmGdAva;
         end;
         qmGdId[qmGdI] := qmGdAid;
         qmGdExt[qmGdI] := qmGdAex;
         if (qmGdAex<>'') then
         qmGdAny := True;
      end;
   end;
   // The start before stopped only if it had the mods enabled now (ref/guard.py
   // same_set): as many, every one the guard can compare among them. A set
   // changed since - the player switched the culprit off in modman, as the
   // engine's dialog tells him to, or a guard restart Steam did not carry
   // out - starts as an ordinary one, so no step switches off more.
   if (qmGdFailLog) then
   begin
      var qmGdOnN : Integer = 0;
      var qmGdSame : Boolean = True;
      for qmGdI:=0 to qmGdN-1 do
      if (qmGdOn[qmGdI]=1) then
      begin
         qmGdOnN := qmGdOnN+1;
         if (qmGdFold[qmGdI]<>'') and (StrPos('|'+qmGdFold[qmGdI]+'|', qmGdFset)=0) then
         qmGdSame := False;
      end;
      qmGdFailed := (qmGdSame) and (qmGdOnN=qmGdFn);
   end;
   qmGdBasis := 'none';
   if (qmGdFailed) then
   begin
      qmGdJudge := True;
      qmGdTrust := qmGdGood;
      if (qmGdHaveC) then
      qmGdBasis := 'compiled';
   end
   else
   if (qmGdHaveC) then
   begin
      qmGdJudge := True;
      qmGdBasis := 'compiled';
      qmGdTrust := qmGdGood+qmGdChosen;
   end
   else
   if (qmGdHave) then
   begin
      qmGdJudge := True;
      qmGdBasis := 'known';
      qmGdTrust := qmGdKnown;
   end;
   for qmGdI:=0 to qmGdN-1 do
   if (qmGdState[qmGdI]=1) and (qmGdFold[qmGdI]<>'') and (qmGdJudge) then
   if (StrPos('|'+qmGdFold[qmGdI]+'|', qmGdTrust)=0) then
   qmGdState[qmGdI] := 2;
   // Pass 1: the trusted mods claim their global scripts.
   for qmGdI:=0 to qmGdN-1 do
   if (qmGdState[qmGdI]=1) and (StrLength(qmGdFiles[qmGdI])>1) then
   qmGdClaim := qmGdClaim+SubStr(qmGdFiles[qmGdI], 2, StrLength(qmGdFiles[qmGdI])-1);
   // Pass 2: each other mod, in load order, loses to a claim or claims its own.
   // A claim by the mod's base, or by an add-on of it, is no clash (ref/guard.py
   // related): the claimants - trusted or kept - that are one, as `|j|`.
   for qmGdI:=0 to qmGdN-1 do
   if (qmGdState[qmGdI]=2) then
   begin
      qmGdRel := '|';
      if (qmGdAny) then
      for qmGdJ:=0 to qmGdN-1 do
      if (qmGdJ<>qmGdI) and ((qmGdState[qmGdJ]=1) or (qmGdState[qmGdJ]=3)) then
      begin
         qmGdQ := False;
         if (qmGdExt[qmGdI]<>'') and ((qmGdExt[qmGdI]=qmGdId[qmGdJ]) or (qmGdExt[qmGdI]=qmGdFid[qmGdJ])) then
         qmGdQ := True;
         if (qmGdExt[qmGdJ]<>'') and ((qmGdExt[qmGdJ]=qmGdId[qmGdI]) or (qmGdExt[qmGdJ]=qmGdFid[qmGdI])) then
         qmGdQ := True;
         if (qmGdQ) then
         qmGdRel := qmGdRel+IntToStr(qmGdJ)+'|';
      end;
      qmGdRest := SubStr(qmGdFiles[qmGdI], 2, StrLength(qmGdFiles[qmGdI])-1);
      while (qmGdRest<>'') and (qmGdHit[qmGdI]='') do
      begin
         qmGdP := StrPos('|', qmGdRest);
         if (qmGdP<2) then
         qmGdRest := ''
         else
         begin
            qmGdF := SubStr(qmGdRest, 1, qmGdP-1);
            qmGdRest := SubStr(qmGdRest, qmGdP+1, StrLength(qmGdRest)-qmGdP);
            if (StrPos('|'+qmGdF+'|', qmGdClaim)>0) then
            begin
               if (StrLength(qmGdRel)<=1) then
               qmGdHit[qmGdI] := qmGdF
               else
               for qmGdJ:=0 to qmGdN-1 do
               if (qmGdHit[qmGdI]='') and (qmGdJ<>qmGdI) and ((qmGdState[qmGdJ]=1) or (qmGdState[qmGdJ]=3)) and (StrPos('|'+qmGdF+'|', qmGdFiles[qmGdJ])>0) and (StrPos('|'+IntToStr(qmGdJ)+'|', qmGdRel)=0) then
               qmGdHit[qmGdI] := qmGdF;
            end;
         end;
      end;
      if (qmGdHit[qmGdI]='') then
      begin
         qmGdState[qmGdI] := 3;
         if (StrLength(qmGdFiles[qmGdI])>1) then
         qmGdClaim := qmGdClaim+SubStr(qmGdFiles[qmGdI], 2, StrLength(qmGdFiles[qmGdI])-1);
      end
      else
      begin
         qmGdState[qmGdI] := 4;
         qmGdOffN := qmGdOffN+1;
         qmGdOffKey := qmGdOffKey+qmGdFold[qmGdI]+'|';
         // Who claimed it: the first trusted mod that ships it, else the first
         // mod kept before this one.
         for qmGdJ:=0 to qmGdN-1 do
         if (qmGdBy[qmGdI]=-1) and (qmGdState[qmGdJ]=1) and (StrPos('|'+qmGdHit[qmGdI]+'|', qmGdFiles[qmGdJ])>0) and (StrPos('|'+IntToStr(qmGdJ)+'|', qmGdRel)=0) then
         qmGdBy[qmGdI] := qmGdJ;
         for qmGdJ:=0 to qmGdI-1 do
         if (qmGdBy[qmGdI]=-1) and (qmGdState[qmGdJ]=3) and (StrPos('|'+qmGdHit[qmGdI]+'|', qmGdFiles[qmGdJ])>0) and (StrPos('|'+IntToStr(qmGdJ)+'|', qmGdRel)=0) then
         qmGdBy[qmGdI] := qmGdJ;
      end;
   end;
   // After a failed start (ref/guard.py fallback): the names step switched
   // something off, or else every mod outside the good set goes (revert), or
   // - none outside it, the good set itself failed - every mod but
   // Quartermaster (vanilla). Without a clash: no file, no other mod.
   if (qmGdFailed) then
   begin
      qmGdRule := 'failed-names';
      if (qmGdOffN=0) then
      begin
         qmGdC := 0;
         for qmGdI:=0 to qmGdN-1 do
         if (qmGdState[qmGdI]=3) then
         qmGdC := qmGdC+1;
         if (qmGdC>0) then
         begin
            qmGdRule := 'failed-revert';
            for qmGdI:=0 to qmGdN-1 do
            if (qmGdState[qmGdI]=3) then
            begin
               qmGdState[qmGdI] := 4;
               qmGdOffN := qmGdOffN+1;
               qmGdOffKey := qmGdOffKey+qmGdFold[qmGdI]+'|';
            end;
         end
         else
         begin
            qmGdRule := 'failed-vanilla';
            for qmGdI:=0 to qmGdN-1 do
            if (qmGdState[qmGdI]=1) and (qmGdFold[qmGdI]<>'') then
            begin
               qmGdState[qmGdI] := 4;
               qmGdOffN := qmGdOffN+1;
               qmGdOffKey := qmGdOffKey+qmGdFold[qmGdI]+'|';
            end;
         end;
      end;
   end;
   // Quartermaster last: enabled mods after it (none switched off here) that
   // ship one of its hook files (plan S5).
   if (qmGdSelf>=0) and (qmGdFold[qmGdSelf]<>'') then
   for qmGdI:=qmGdSelf+1 to qmGdN-1 do
   if (qmGdOn[qmGdI]=1) and (qmGdState[qmGdI]<>4) then
   begin
      qmGdF := '';
      if (ModLibGetFileExist(qmGdI, 'data\gui\menu.inc\cameracontrol.inc')) then
      qmGdF := 'gui\menu.inc\cameracontrol.inc'
      else
      if (ModLibGetFileExist(qmGdI, 'data\gui\menu.inc\initminimap.inc')) then
      qmGdF := 'gui\menu.inc\initminimap.inc'
      else
      if (ModLibGetFileExist(qmGdI, 'data\gui\menu.inc\doprogress.inc')) then
      qmGdF := 'gui\menu.inc\doprogress.inc'
      else
      if (ModLibGetFileExist(qmGdI, 'data\gui\menu.inc\eventmainmenu.inc')) then
      qmGdF := 'gui\menu.inc\eventmainmenu.inc'
      else
      if (ModLibGetFileExist(qmGdI, 'data\gui\menu.inc\onlanevent.inc')) then
      qmGdF := 'gui\menu.inc\onlanevent.inc';
      if (qmGdF<>'') then
      begin
         if (qmGdLate=0) then
         begin
            qmGdLateDir := qmGdDir[qmGdI];
            qmGdLateFile := qmGdF;
         end;
         qmGdLate := qmGdLate+1;
      end;
   end;
   if (qmGdLate>0) then
   qmGdOffKey := qmGdOffKey+'order:'+qmGdFold[qmGdSelf]+'|';
   if (qmGdOffN=0) then
   qmGdRule := 'order';
   if (qmGdOffN=0) and (qmGdLate=0) then
   begin
      qmGdWhy := 'clean';
      if (qmGdFailed) then
      qmGdWhy := 'failed-alone'
      else
      if (qmGdBasis='none') then
      qmGdWhy := 'first-boot';
   end;
end;

// After a failed start the chosen set is spent: a pair the player chose that
// stopped the start is not trusted at a later one either.
if (qmGdFailed) and (qmGdHaveCh) then
begin
   var qmGdChw : Integer = ParserSelectByKey('qm_guard_chosen');
   ParserClearByHandle(qmGdChw);
   ParserSetValueByKeyByHandle(qmGdChw, 'n', '0');
   ParserSaveToFileByHandle(qmGdChw, qmGdSave+'chosen.cfg');
end;

// The loop test: the previous start was a guard restart for the same changes.
var qmGdNote : Integer = ParserSelectByKey('qm_guard_note');
if (qmGdNote=0) then
qmGdNote := ParserCreate('qm_guard_note');
if (qmGdWhy='') then
begin
   ParserClearByHandle(qmGdNote);
   if (FileAge(qmGdSave+'guard.cfg')<>-1) then
   if (ParserLoadFromFileByHandle(qmGdNote, qmGdSave+'guard.cfg')) then
   if (ParserGetValueByKeyByHandle(qmGdNote, 'restarted')='1') and (ParserGetValueByKeyByHandle(qmGdNote, 'key')=qmGdOffKey) then
   qmGdWhy := 'loop';
end;

// True once SteamSyncWorkshopItems took the switched-off mods out of this start.
var qmGdTook : Boolean = False;
if (qmGdWhy='') then
begin
   var qmGdIni : Integer = ParserSelectByKey('qm_guard_ini');
   if (qmGdIni=0) then
   qmGdIni := ParserCreate('qm_guard_ini');
   ParserClearByHandle(qmGdIni);
   var qmGdIm : Integer = 0;
   if (ParserLoadFromFileByHandle(qmGdIni, ModLibraryGetIniFile)) then
   qmGdIm := ParserSelectByHandleByKey(qmGdIni, 'mods');
   if (qmGdIm=0) then
   qmGdWhy := 'no-mods-ini'
   else
   begin
      var qmGdSync : Integer = -1;
      if (qmGdOffN>0) and (SteamwrapIsSteamRunning) then
      begin
         var qmGdL : Integer = ParserSelectByKey('qm_guard_list');
         if (qmGdL=0) then
         qmGdL := ParserCreate('qm_guard_list');
         ParserClearByHandle(qmGdL);
         ModLibraryGetParser(qmGdL, False);
         var qmGdLm : Integer = ParserSelectByHandleByKey(qmGdL, 'mods');
         if (qmGdLm<>0) then
         begin
            for qmGdK:=0 to ParserGetCountByHandle(qmGdLm)-1 do
            begin
               var qmGdLe : Integer = ParserSelectByHandleByIndex(qmGdLm, qmGdK);
               qmGdV := StrToLowerCase(ParserGetValueByKeyByHandle(qmGdLe, 'dir'));
               while (StrPos('/', qmGdV)>0) do
               qmGdV := StrReplace(qmGdV, '/', '\');
               if (StrPos('|'+qmGdV+'|', '|'+qmGdOffKey)>0) then
               ParserSetValueByKeyByHandle(qmGdLe, 'dis', 'True');
            end;
            qmGdSync := SteamSyncWorkshopItems(qmGdL);
            qmGdTook := True;
         end;
      end;
      // mods.ini as loaded, the switched-off mods off, and Quartermaster's
      // entry moved last: the values of the entries move, no entry is added
      // or dropped (the way qmModsIni rewrites it).
      var qmGdEn : Integer = ParserGetCountByHandle(qmGdIm);
      if (qmGdEn>512) then
      qmGdEn := 512;
      var qmGdEd : array [0..511] of String;
      var qmGdEs : array [0..511] of String;
      var qmGdSelfE : Integer = -1;
      var qmGdMoved : Integer = 0;
      for qmGdK:=0 to qmGdEn-1 do
      begin
         var qmGdIe : Integer = ParserSelectByHandleByIndex(qmGdIm, qmGdK);
         qmGdEd[qmGdK] := ParserGetValueByKeyByHandle(qmGdIe, 'dir');
         qmGdEs[qmGdK] := ParserGetValueByKeyByHandle(qmGdIe, 'dis');
         qmGdV := StrToLowerCase(qmGdEd[qmGdK]);
         while (StrPos('/', qmGdV)>0) do
         qmGdV := StrReplace(qmGdV, '/', '\');
         if (StrPos('|'+qmGdV+'|', '|'+qmGdOffKey)>0) then
         qmGdEs[qmGdK] := 'True';
         if (qmGdLate>0) and (qmGdV=qmGdFold[qmGdSelf]) then
         qmGdSelfE := qmGdK;
      end;
      qmGdJ := 0;
      for qmGdK:=0 to qmGdEn-1 do
      if (qmGdK<>qmGdSelfE) then
      begin
         var qmGdWe : Integer = ParserSelectByHandleByIndex(qmGdIm, qmGdJ);
         ParserSetValueByKeyByHandle(qmGdWe, 'dir', qmGdEd[qmGdK]);
         ParserSetValueByKeyByHandle(qmGdWe, 'dis', qmGdEs[qmGdK]);
         qmGdJ := qmGdJ+1;
      end;
      if (qmGdSelfE>=0) then
      begin
         var qmGdWs : Integer = ParserSelectByHandleByIndex(qmGdIm, qmGdJ);
         ParserSetValueByKeyByHandle(qmGdWs, 'dir', qmGdEd[qmGdSelfE]);
         ParserSetValueByKeyByHandle(qmGdWs, 'dis', qmGdEs[qmGdSelfE]);
         if (qmGdSelfE<>qmGdEn-1) then
         qmGdMoved := 1;
      end;
      var qmGdSaved : Boolean = ParserSaveToFileByHandle(qmGdIni, ModLibraryGetIniFile);
      ParserClearByHandle(qmGdNote);
      ParserSetValueByKeyByHandle(qmGdNote, 'restarted', '1');
      ParserSetValueByKeyByHandle(qmGdNote, 'shown', '0');
      ParserSetValueByKeyByHandle(qmGdNote, 'key', qmGdOffKey);
      ParserSetValueByKeyByHandle(qmGdNote, 'n', IntToStr(qmGdOffN));
      ParserSetValueByKeyByHandle(qmGdNote, 'moved', IntToStr(qmGdMoved));
      ParserSetValueByKeyByHandle(qmGdNote, 'why', qmGdRule);
      if (qmGdLate>0) then
      begin
         ParserSetValueByKeyByHandle(qmGdNote, 'latedir', qmGdLateDir);
         ParserSetValueByKeyByHandle(qmGdNote, 'latefile', qmGdLateFile);
         log('[qm-guard] Quartermaster moved last='+IntToStr(qmGdMoved)+': '+IntToStr(qmGdLate)+' mod(s) after it ship a hook file, first '+qmGdLateDir+' ('+qmGdLateFile+')');
      end;
      qmGdK := 0;
      for qmGdI:=0 to qmGdN-1 do
      if (qmGdState[qmGdI]=4) then
      begin
         ParserSetValueByKeyByHandle(qmGdNote, 'dir'+IntToStr(qmGdK), qmGdDir[qmGdI]);
         ParserSetValueByKeyByHandle(qmGdNote, 'tit'+IntToStr(qmGdK), qmGdTit[qmGdI]);
         ParserSetValueByKeyByHandle(qmGdNote, 'file'+IntToStr(qmGdK), qmGdHit[qmGdI]);
         if (qmGdBy[qmGdI]>=0) then
         begin
            ParserSetValueByKeyByHandle(qmGdNote, 'odir'+IntToStr(qmGdK), qmGdDir[qmGdBy[qmGdI]]);
            ParserSetValueByKeyByHandle(qmGdNote, 'otit'+IntToStr(qmGdK), qmGdTit[qmGdBy[qmGdI]]);
         end;
         qmGdV := '?';
         if (qmGdBy[qmGdI]>=0) then
         qmGdV := qmGdDir[qmGdBy[qmGdI]];
         if (qmGdHit[qmGdI]<>'') then
         log('[qm-guard] off '+qmGdDir[qmGdI]+' ('+qmGdHit[qmGdI]+', shipped by '+qmGdV+')')
         else
         log('[qm-guard] off '+qmGdDir[qmGdI]+' ('+qmGdRule+')');
         qmGdK := qmGdK+1;
      end;
      ParserSaveToFileByHandle(qmGdNote, qmGdSave+'guard.cfg');
      if (qmGdSaved) then
      log('[qm-guard] switched off='+IntToStr(qmGdOffN)+' moved='+IntToStr(qmGdMoved)+' sync='+IntToStr(qmGdSync)+' mods.ini=saved; restarting')
      else
      log('[qm-guard] switched off='+IntToStr(qmGdOffN)+' moved='+IntToStr(qmGdMoved)+' sync='+IntToStr(qmGdSync)+' mods.ini=NOT saved; restarting');
      LanShutdown;
      SteamwrapFree;
      RestartApplicationParam('');
      qmGdWhy := 'restart';
   end;
end;
// The mods this start compiles with, in load order: a CompileFramework error's
// line number maps onto their libraries (qmLastStart reads the record at the
// next start that gets as far as Quartermaster). The previous start's record
// becomes compile.prev.cfg first. Not where the mod list was not read. A guard
// restart is recorded too: the life it ends still compiles the libraries
// before the engine restarts, and stops at "Error compiling scripts" when its
// set has a clash. Until 2026-10-03 it was not (the next life was to record
// its own set); what it cost: with Quartermaster put in the middle of
// mods.ini, the guard restarted to move it last, that life stopped at the
// error, and the next start - its record not pending - ran the same set into
// the error a second time (the owner's starts of 2026-10-03 08:45 and 08:46).
// The mods SteamSyncWorkshopItems took out of the running start are not in
// the set it compiles (run g8, verdict 6).
if (qmGdWhy='clean') or (qmGdWhy='first-boot') or (qmGdWhy='loop') or (qmGdWhy='no-mods-ini') or (qmGdWhy='failed-alone') or (qmGdWhy='restart') then
begin
   var qmGdCp : Integer = ParserSelectByKey('qm_guard_compile');
   if (qmGdCp=0) then
   qmGdCp := ParserCreate('qm_guard_compile');
   ParserClearByHandle(qmGdCp);
   if (FileAge(qmGdSave+'compile.cfg')<>-1) then
   if (ParserLoadFromFileByHandle(qmGdCp, qmGdSave+'compile.cfg')) then
   ParserSaveToFileByHandle(qmGdCp, qmGdSave+'compile.prev.cfg');
   ParserClearByHandle(qmGdCp);
   qmGdK := 0;
   for qmGdI:=0 to qmGdN-1 do
   if (qmGdOn[qmGdI]=1) and ((not qmGdTook) or (qmGdState[qmGdI]<>4)) then
   begin
      ParserSetValueByKeyByHandle(qmGdCp, 'd'+IntToStr(qmGdK), qmGdDir[qmGdI]);
      ParserSetValueByKeyByHandle(qmGdCp, 't'+IntToStr(qmGdK), qmGdTit[qmGdI]);
      qmGdK := qmGdK+1;
   end;
   ParserSetValueByKeyByHandle(qmGdCp, 'n', IntToStr(qmGdK));
   // Until this start's boot sets 0: the `failed` test of the next start.
   ParserSetValueByKeyByHandle(qmGdCp, 'pending', '1');
   ParserSaveToFileByHandle(qmGdCp, qmGdSave+'compile.cfg');
end;
log('[qm-guard] '+qmGdWhy+' mods='+IntToStr(qmGdN)+' age='+IntToStr(qmGdAge)+' game='+qmGdStamp+' basis='+qmGdBasis);
