state: qmGlobals
into: data/quartermaster/core.aix
helpers: qmlog, qmglob
requires:
---
//! Global scripts of every registered mod, and the clashes between the
//! enabled ones (plan S17; twin: ref/guard.py `conflict_pairs`); qmBoot runs
//! it after qmKnown and prints its lines in the report's Boot block, the
//! manager's model (qmUiModel) reads the same lists for the rows.
//!
//! A clash is two enabled mods that ship the same global script: only the
//! later one's copy loads, the other mod's libraries then usually miss
//! names, and the game stops at "Error compiling scripts" before anything of
//! Quartermaster runs. Which of them the player keeps is the player's choice;
//! the report and the window say which files, and the manager's Apply
//! refuses a set with a clash.
//!
//! The guard's note (<save>\quartermaster\guard.cfg, written by
//! src/guard/resource.pas before a restart) is read here on a boot: with
//! `restarted` = 1 it is fresh - the guard switched those mods off at the
//! start of this process - so the boot reports it and qmTick shows the
//! notice once; the note is then saved with `restarted` = 0, which is also
//! what disarms the guard's loop test for a later start.
//!
//! A boot also records the mods this start compiled with:
//! <save>\quartermaster\compiled.cfg, d<k> every enabled mod's dir in the
//! engine's order (Quartermaster too) and n (ref/guard.py compiled_values).
//! Quartermaster running means the libraries compiled, so this is the set the
//! guard trusts at the next start; a mod switched on outside Quartermaster
//! since then is judged like a new subscription (revised 2026-10-02, 0.1.3).
//! Not on an Apply (that set has not compiled yet), not in a multiplayer sync
//! (that set is the host's, the player's own comes back after it - the
//! guard's own test), and written only when it differs.
//!
//! Keys of qm_glob (docs/ui.md):
//!   n                    registered mods (at most 256)
//!   dir<i> tit<i>        the engine's dir and the title shown
//!   on<i>                1 enabled (Quartermaster and its copies read 0)
//!   gl<i>                the global scripts, `|`-joined (qmGlobFiles)
//!   cn, ca<k> cb<k> cf<k>  clashes: the two mods (a before b) and the first
//!                        file of a's list that b ships too; at most 64
//!   gdn, gdnew           the guard note's mods, 1 while not shown yet
//!   gdmoved gdlate gdlatef  1 when the guard moved Quartermaster last at this
//!                        start, the first mod after it and its hook file
//!   gdd<k> gdt<k> gdf<k> gdo<k>  dir, title, file, title of the other mod
var qmGbG : Integer = ParserSelectByKey('qm_glob');
if (qmGbG=0) then
qmGbG := ParserCreate('qm_glob');
ParserClearByHandle(qmGbG);
var qmGbN : Integer = ModLibraryGetCount;
if (qmGbN>256) then
qmGbN := 256;
var qmGbFiles : array [0..255] of String;
var qmGbOn : array [0..255] of Integer;
var qmGbTag, qmGbDir, qmGbLast, qmGbTit, qmGbOwn, qmGbDesc, qmGbTags, qmGbUrl, qmGbNote : String;
var qmGbNumf, qmGbVis : Integer;
var qmGbDis, qmGbAcc, qmGbBan, qmGbRoot : Boolean;
var qmGbI : Integer;
var qmGbJ : Integer;
var qmGbK : Integer;
var qmGbF : String;
var qmGbL : String;
var qmGbWith : Integer = 0;
var qmGbCd : array [0..255] of String;
var qmGbCk : Integer = 0;
for qmGbI:=0 to qmGbN-1 do
begin
   //! For a folder without mod.ini the engine leaves the title and `last`
   //! untouched: they would still hold the row before's (run b4, 2026-09-29).
   qmGbTit := '';
   qmGbLast := '';
   ModLibraryGetData(qmGbI, qmGbTag, qmGbDir, qmGbLast, qmGbTit, qmGbOwn, qmGbDesc, qmGbTags, qmGbUrl, qmGbNote, qmGbNumf, qmGbVis, qmGbDis, qmGbAcc, qmGbBan, qmGbRoot);
   if (not qmGbDis) then
   begin
      qmGbCd[qmGbCk] := qmGbDir;
      qmGbCk := qmGbCk+1;
   end;
   if (qmGbTit='') then
   qmGbTit := qmGbLast;
   if (qmGbTit='') then
   qmGbTit := qmGbDir;
   ParserSetValueByKeyByHandle(qmGbG, 'dir'+IntToStr(qmGbI), qmGbDir);
   ParserSetValueByKeyByHandle(qmGbG, 'tit'+IntToStr(qmGbI), qmGbTit);
   qmGbOn[qmGbI] := 0;
   qmGbFiles[qmGbI] := '|';
   // Quartermaster and any copy of it are never judged (ref/guard.py).
   if (FileAge(qmGbDir+'\data\quartermaster\core.aix')=-1) then
   begin
      qmGlobFiles(qmGbI, qmGbDir, qmGbL);
      qmGbFiles[qmGbI] := qmGbL;
      if (not qmGbDis) then
      qmGbOn[qmGbI] := 1;
   end;
   if (StrLength(qmGbFiles[qmGbI])>1) then
   qmGbWith := qmGbWith+1;
   ParserSetIntValueByKeyByHandle(qmGbG, 'on'+IntToStr(qmGbI), qmGbOn[qmGbI]);
   ParserSetValueByKeyByHandle(qmGbG, 'gl'+IntToStr(qmGbI), qmGbFiles[qmGbI]);
end;
ParserSetIntValueByKeyByHandle(qmGbG, 'n', qmGbN);
var qmGbCn : Integer = 0;
for qmGbI:=0 to qmGbN-1 do
if (qmGbOn[qmGbI]=1) and (StrLength(qmGbFiles[qmGbI])>1) then
for qmGbJ:=qmGbI+1 to qmGbN-1 do
if (qmGbOn[qmGbJ]=1) and (StrLength(qmGbFiles[qmGbJ])>1) and (qmGbCn<64) then
begin
   qmGlobFirst(qmGbFiles[qmGbI], qmGbFiles[qmGbJ], qmGbF);
   if (qmGbF<>'') then
   begin
      ParserSetIntValueByKeyByHandle(qmGbG, 'ca'+IntToStr(qmGbCn), qmGbI);
      ParserSetIntValueByKeyByHandle(qmGbG, 'cb'+IntToStr(qmGbCn), qmGbJ);
      ParserSetValueByKeyByHandle(qmGbG, 'cf'+IntToStr(qmGbCn), qmGbF);
      qmLog('globals clash '+ParserGetValueByKeyByHandle(qmGbG, 'dir'+IntToStr(qmGbI))+' x '+ParserGetValueByKeyByHandle(qmGbG, 'dir'+IntToStr(qmGbJ))+' on '+qmGbF);
      qmGbCn := qmGbCn+1;
   end;
end;
ParserSetIntValueByKeyByHandle(qmGbG, 'cn', qmGbCn);

//! The guard's note, on a boot only (an Apply run reads nothing of it).
var qmGbRt : Integer = ParserSelectByKey('qm_rt');
var qmGbApply : Boolean = False;
if (qmGbRt<>0) then
qmGbApply := (ParserGetValueByKeyByHandle(qmGbRt, 'runmode')='apply');
var qmGbPath : String = GetAppSaveDirectoryPath+'quartermaster\guard.cfg';
var qmGbNt : Integer = ParserSelectByKey('qm_glob_note');
if (qmGbNt=0) then
qmGbNt := ParserCreate('qm_glob_note');
ParserClearByHandle(qmGbNt);
var qmGbGn : Integer = 0;
var qmGbFresh : Integer = 0;
if (not qmGbApply) and (FileAge(qmGbPath)<>-1) then
if (ParserLoadFromFileByHandle(qmGbNt, qmGbPath)) then
begin
   qmGbGn := ParserGetIntValueByKeyByHandle(qmGbNt, 'n');
   if (qmGbGn>32) then
   qmGbGn := 32;
   // Shown once, whenever that is: a first generation's own restart may come
   // before the menu (qmTick sets `shown` when the notice is on the screen).
   if (qmGbGn>0) and (ParserGetValueByKeyByHandle(qmGbNt, 'shown')<>'1') then
   qmGbFresh := 1;
   // The guard moved Quartermaster last (a later mod shipped a hook file): one
   // report line on the start after it; there is no notice to show for it.
   if (ParserGetValueByKeyByHandle(qmGbNt, 'moved')='1') and (ParserGetValueByKeyByHandle(qmGbNt, 'restarted')='1') then
   begin
      ParserSetIntValueByKeyByHandle(qmGbG, 'gdmoved', 1);
      ParserSetValueByKeyByHandle(qmGbG, 'gdlate', ParserGetValueByKeyByHandle(qmGbNt, 'latedir'));
      ParserSetValueByKeyByHandle(qmGbG, 'gdlatef', ParserGetValueByKeyByHandle(qmGbNt, 'latefile'));
   end;
   for qmGbK:=0 to qmGbGn-1 do
   begin
      qmGbL := IntToStr(qmGbK);
      ParserSetValueByKeyByHandle(qmGbG, 'gdd'+qmGbL, ParserGetValueByKeyByHandle(qmGbNt, 'dir'+qmGbL));
      qmGbF := ParserGetValueByKeyByHandle(qmGbNt, 'tit'+qmGbL);
      if (qmGbF='') then
      qmGbF := ParserGetValueByKeyByHandle(qmGbNt, 'dir'+qmGbL);
      ParserSetValueByKeyByHandle(qmGbG, 'gdt'+qmGbL, qmGbF);
      ParserSetValueByKeyByHandle(qmGbG, 'gdf'+qmGbL, ParserGetValueByKeyByHandle(qmGbNt, 'file'+qmGbL));
      qmGbF := ParserGetValueByKeyByHandle(qmGbNt, 'otit'+qmGbL);
      if (qmGbF='') then
      qmGbF := ParserGetValueByKeyByHandle(qmGbNt, 'odir'+qmGbL);
      ParserSetValueByKeyByHandle(qmGbG, 'gdo'+qmGbL, qmGbF);
   end;
   // The start the guard restarted has booted: its loop test is disarmed.
   if (ParserGetValueByKeyByHandle(qmGbNt, 'restarted')='1') then
   begin
      ParserSetValueByKeyByHandle(qmGbNt, 'restarted', '0');
      if (ParserSaveToFileByHandle(qmGbNt, qmGbPath)) then
      qmLog('globals: guard note read, '+IntToStr(qmGbGn)+' mod(s) switched off; the guard restart booted')
      else
      qmLog('globals: guard note read, '+IntToStr(qmGbGn)+' mod(s); the note could not be saved back');
   end;
end;
ParserSetIntValueByKeyByHandle(qmGbG, 'gdn', qmGbGn);
ParserSetIntValueByKeyByHandle(qmGbG, 'gdnew', qmGbFresh);

//! The record of this start's mods for the guard (see the head of this file).
var qmGbCw : String = '-';
if (not qmGbApply) and (StringRegister7='') and (FileAge(GetAppSaveDirectoryPath+'mods.restore')=-1) then
begin
   var qmGbCp : String = GetAppSaveDirectoryPath+'quartermaster\compiled.cfg';
   var qmGbCr : Integer = ParserSelectByKey('qm_glob_compiled');
   if (qmGbCr=0) then
   qmGbCr := ParserCreate('qm_glob_compiled');
   ParserClearByHandle(qmGbCr);
   var qmGbSame : Boolean = False;
   if (FileAge(qmGbCp)<>-1) then
   if (ParserLoadFromFileByHandle(qmGbCr, qmGbCp)) then
   if (ParserGetValueByKeyByHandle(qmGbCr, 'n')=IntToStr(qmGbCk)) then
   begin
      qmGbSame := True;
      for qmGbK:=0 to qmGbCk-1 do
      if (ParserGetValueByKeyByHandle(qmGbCr, 'd'+IntToStr(qmGbK))<>qmGbCd[qmGbK]) then
      qmGbSame := False;
   end;
   qmGbCw := 'same';
   if (not qmGbSame) then
   begin
      ParserClearByHandle(qmGbCr);
      for qmGbK:=0 to qmGbCk-1 do
      ParserSetValueByKeyByHandle(qmGbCr, 'd'+IntToStr(qmGbK), qmGbCd[qmGbK]);
      ParserSetValueByKeyByHandle(qmGbCr, 'n', IntToStr(qmGbCk));
      if (ParserSaveToFileByHandle(qmGbCr, qmGbCp)) then
      qmGbCw := 'written'
      else
      qmGbCw := 'not-saved';
   end;
end;
qmLog('globals mods='+IntToStr(qmGbN)+' with global scripts='+IntToStr(qmGbWith)+' clashes='+IntToStr(qmGbCn)+' guard note='+IntToStr(qmGbGn)+' fresh='+IntToStr(qmGbFresh)+' compiled='+IntToStr(qmGbCk)+' '+qmGbCw);
