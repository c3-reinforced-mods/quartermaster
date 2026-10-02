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
//! Two things it puts right before they can go wrong:
//!   - a mod it does not trust that ships a global script an enabled mod
//!     ships already is taken out of this start with SteamSyncWorkshopItems
//!     (verdict 6) and switched off in mods.ini. Trusted are the mods of the
//!     last start that booted (compiled.cfg, written by qmGlobals); without
//!     that record the mods of known.cfg, as until 0.1.2 - when a known mod
//!     switched on in modman next to a clashing one went through (32 at once
//!     on 2026-10-02, "Error compiling scripts");
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

// The mods of the last start that booted (ref/guard.py compiled_dirs): a
// count of at least 1 - a boot always has Quartermaster on - or no record.
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
// What the trust comes from (ref/guard.py trusted_set): compiled, known, none.
var qmGdBasis : String = '-';
var qmGdTrust : String = '|';
if (qmGdWhy='') then
begin
   qmGdBasis := 'none';
   if (qmGdHave) then
   begin
      qmGdBasis := 'known';
      qmGdTrust := qmGdKnown;
   end;
   if (qmGdHaveC) then
   begin
      qmGdBasis := 'compiled';
      qmGdTrust := qmGdGood;
   end;
end;

// Every registered mod: 0 off or Quartermaster, 1 trusted and on, 2 not
// trusted and on, 3 not trusted and kept, 4 not trusted and switched off.
// Without a record (a first boot) every mod is trusted: nothing is switched off.
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
         if (qmGdOk) and (qmGdBasis<>'none') then
         if (StrPos('|'+qmGdFold[qmGdI]+'|', qmGdTrust)=0) then
         qmGdState[qmGdI] := 2;
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
   // Pass 1: the trusted mods claim their global scripts.
   for qmGdI:=0 to qmGdN-1 do
   if (qmGdState[qmGdI]=1) and (StrLength(qmGdFiles[qmGdI])>1) then
   qmGdClaim := qmGdClaim+SubStr(qmGdFiles[qmGdI], 2, StrLength(qmGdFiles[qmGdI])-1);
   // Pass 2: each other mod, in load order, loses to a claim or claims its own.
   for qmGdI:=0 to qmGdN-1 do
   if (qmGdState[qmGdI]=2) then
   begin
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
            qmGdHit[qmGdI] := qmGdF;
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
         if (qmGdBy[qmGdI]=-1) and (qmGdState[qmGdJ]=1) and (StrPos('|'+qmGdHit[qmGdI]+'|', qmGdFiles[qmGdJ])>0) then
         qmGdBy[qmGdI] := qmGdJ;
         for qmGdJ:=0 to qmGdI-1 do
         if (qmGdBy[qmGdI]=-1) and (qmGdState[qmGdJ]=3) and (StrPos('|'+qmGdHit[qmGdI]+'|', qmGdFiles[qmGdJ])>0) then
         qmGdBy[qmGdI] := qmGdJ;
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
   if (qmGdOffN=0) and (qmGdLate=0) then
   begin
      qmGdWhy := 'clean';
      if (qmGdBasis='none') then
      qmGdWhy := 'first-boot';
   end;
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
         log('[qm-guard] off '+qmGdDir[qmGdI]+' ('+qmGdHit[qmGdI]+', shipped by '+qmGdV+')');
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
// becomes compile.prev.cfg first. Not on a guard restart (the next life
// records its own set) and not where the mod list was not read.
if (qmGdWhy='clean') or (qmGdWhy='first-boot') or (qmGdWhy='loop') or (qmGdWhy='no-mods-ini') then
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
   if (qmGdOn[qmGdI]=1) then
   begin
      ParserSetValueByKeyByHandle(qmGdCp, 'd'+IntToStr(qmGdK), qmGdDir[qmGdI]);
      ParserSetValueByKeyByHandle(qmGdCp, 't'+IntToStr(qmGdK), qmGdTit[qmGdI]);
      qmGdK := qmGdK+1;
   end;
   ParserSetValueByKeyByHandle(qmGdCp, 'n', IntToStr(qmGdK));
   ParserSaveToFileByHandle(qmGdCp, qmGdSave+'compile.cfg');
end;
log('[qm-guard] '+qmGdWhy+' mods='+IntToStr(qmGdN)+' age='+IntToStr(qmGdAge)+' game='+qmGdStamp+' basis='+qmGdBasis);
