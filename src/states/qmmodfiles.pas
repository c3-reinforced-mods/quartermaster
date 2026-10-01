state: qmModFiles
into: data/quartermaster/core.aix
helpers: qmlog, qmstr, qmwrite
requires:
---
//! Create mod, Create about.cfg, Edit game file (plan G17; M11; twin
//! ref/createmod.py): the request the manager window left in qm_rt (the
//! window writes nothing itself, docs/ui.md), done by qmTick on the next
//! main-menu frame through the writer (qmWrNewMod, qmWrAboutDraft,
//! qmWrCopyVanilla make every check). The outcome goes to qm_rt mfres (1
//! done, 0 refused, -1 not confirmed) and, as a sentence, to the window's
//! message line.
//!
//!   qm_rt mfreq    new, about or copy (cleared here)
//!         new:     mffolder (A-Z a-z 0-9 _), mftitle (as typed), mftype
//!                  (mod, totalConversion), mfexcl (a slot or '')
//!         about:   mfdir (a local mod's dir), mftitle, mftags, mfcam (1 when
//!                  the mod ships gui\menu.inc\oncamera.inc)
//!         copy:    mfdir, mfrel (a vanilla.idx path)
var qmMfRt : Integer = ParserSelectByKey('qm_rt');
if (qmMfRt=0) then
exit;
var qmMfUi : Integer = ParserSelectByKey('qm_ui');
var qmMfReq : String = ParserGetValueByKeyByHandle(qmMfRt, 'mfreq');
ParserSetValueByKeyByHandle(qmMfRt, 'mfreq', '');
var qmMfRes : Integer = 0;
var qmMfMsg : String = '';
var qmMfNl : String = '~013~010';
var qmMfF : String;
var qmMfT : String;
var qmMfIni : String;
var qmMfAb : String;
var qmMfRd : String;
var qmMfDir : String;
var qmMfId : String;
var qmMfLow : String;
var qmMfI : Integer;
var qmMfC : String;

//! ref/about.py draft: the comment, id, name, version and type lines.
procedure qmMfDraft(const qmMdId : String; const qmMdTitle : String; const qmMdTotal : Boolean; var qmMdOut : String);
begin
   // The comment a draft about.cfg starts with.
   qmMdOut := '# about.cfg - read by Quartermaster; the Quartermaster Workshop page lists the keys.'+qmMfNl;
   qmMdOut := qmMdOut+'id = '+qmMdId+qmMfNl+'name = '+qmMdTitle+qmMfNl+'version = 1.0'+qmMfNl;
   if (qmMdTotal) then
   qmMdOut := qmMdOut+'type = totalConversion'+qmMfNl
   else
   qmMdOut := qmMdOut+'type = mod'+qmMfNl;
end;

if (qmMfReq='new') then
begin
   qmMfF := ParserGetValueByKeyByHandle(qmMfRt, 'mffolder');
   qmEscape(ParserGetValueByKeyByHandle(qmMfRt, 'mftitle'), qmMfT);
   //! mod.ini: the layout of a local mod's (ref/createmod.py MOD_INI_KEYS).
   // The description and change note a new mod's mod.ini carries.
   qmMfIni := 'section.begin'+qmMfNl+'   publishedfileid = 0'+qmMfNl+'   creatorappid = 0'+qmMfNl+'   consumerappid = 0'+qmMfNl;
   qmMfIni := qmMfIni+'   contentfolder = mods\'+qmMfF+qmMfNl+'   previewfile = '+qmMfNl+'   ownersteamid = 0'+qmMfNl;
   qmMfIni := qmMfIni+'   timecreated = 0'+qmMfNl+'   timeupdated = 0'+qmMfNl+'   visibility = 0'+qmMfNl+'   banned = False'+qmMfNl;
   qmMfIni := qmMfIni+'   title = '+qmMfT+qmMfNl+'   description[*] = ;A mod made with Quartermaster.'+qmMfNl+'   tags = '+qmMfNl;
   qmMfIni := qmMfIni+'   filename = '+qmMfF+qmMfNl+'   filesize = 0'+qmMfNl+'   previewfilesize = 0'+qmMfNl+'   url = '+qmMfNl;
   qmMfIni := qmMfIni+'   filetype = 0'+qmMfNl+'   acceptedforuse = False'+qmMfNl+'   changenote[*] = ;First version.'+qmMfNl;
   qmMfIni := qmMfIni+'section.end'+qmMfNl+qmMfNl;
   qmLowerAscii(qmMfF, qmMfId);
   qmMfDraft(qmMfId, qmMfT, ParserGetValueByKeyByHandle(qmMfRt, 'mftype')='totalConversion', qmMfAb);
   if (ParserGetValueByKeyByHandle(qmMfRt, 'mfexcl')<>'') then
   qmMfAb := qmMfAb+'exclusive = '+ParserGetValueByKeyByHandle(qmMfRt, 'mfexcl')+qmMfNl;
   // The readme a new mod gets.
   qmMfRd := 'This is a mod made with Quartermaster.'+qmMfNl;
   qmMfRd := qmMfRd+'Put the game files it changes under data\, in the same folders as in the'+qmMfNl;
   qmMfRd := qmMfRd+'game''s own data\ folder: data\gui\menu.inc\oncamera.inc, say.'+qmMfNl;
   qmMfRd := qmMfRd+'about.cfg says what the mod is; the Quartermaster Workshop page lists the keys.'+qmMfNl;
   qmMfRes := qmWrNewMod(qmMfF, qmMfIni, qmMfAb, qmMfRd);
   // The messages of Create mod.
   if (qmMfRes=1) then
   qmMfMsg := 'Created mods\'+qmMfF+'. It is in the list after you restart the game: the game looks for new mod folders only when it starts.'
   else
   qmMfMsg := 'mods\'+qmMfF+' was not created: that folder is taken or the name makes none.';
end;
if (qmMfReq='about') then
begin
   qmMfDir := ParserGetValueByKeyByHandle(qmMfRt, 'mfdir');
   //! ref/createmod.py draft_id: the folder, folded, anything outside
   //! a-z 0-9 _ . - as `_`.
   qmLowerAscii(SubStr(qmMfDir, 6, StrLength(qmMfDir)-5), qmMfLow);
   qmMfId := '';
   for qmMfI:=1 to StrLength(qmMfLow) do
   begin
      qmMfC := SubStr(qmMfLow, qmMfI, 1);
      if (StrPos(qmMfC, 'abcdefghijklmnopqrstuvwxyz0123456789_.-')=0) then
      qmMfC := '_';
      qmMfId := qmMfId+qmMfC;
   end;
   qmEscape(ParserGetValueByKeyByHandle(qmMfRt, 'mftitle'), qmMfT);
   qmLowerAscii(ParserGetValueByKeyByHandle(qmMfRt, 'mftags'), qmMfLow);
   qmMfDraft(qmMfId, qmMfT, StrPos('overhaul', qmMfLow)>0, qmMfAb);
   if (ParserGetIntValueByKeyByHandle(qmMfRt, 'mfcam')=1) then
   qmMfAb := qmMfAb+'exclusive = camera'+qmMfNl;
   qmMfRes := qmWrAboutDraft(qmMfDir, qmMfAb);
   // The messages of Create about.cfg.
   if (qmMfRes=1) then
   qmMfMsg := 'Wrote '+qmMfDir+'\about.cfg - check its values; the next start reads it.'
   else
   qmMfMsg := 'No about.cfg written: '+qmMfDir+' has one already or is not a local mod.';
end;
if (qmMfReq='copy') then
begin
   qmMfDir := ParserGetValueByKeyByHandle(qmMfRt, 'mfdir');
   qmMfRes := qmWrCopyVanilla(qmMfDir, ParserGetValueByKeyByHandle(qmMfRt, 'mfrel'));
   // The messages of Edit game file.
   if (qmMfRes=1) then
   qmMfMsg := 'Copied data\'+ParserGetValueByKeyByHandle(qmMfRt, 'mfrel')+' into '+qmMfDir+' - edit it there; the next start loads it.'
   else
   qmMfMsg := 'Not copied: the mod has that file already, or it is not a local mod.';
end;
ParserSetIntValueByKeyByHandle(qmMfRt, 'mfres', qmMfRes);
ParserSetIntValueByKeyByHandle(qmMfRt, 'mfdone', ParserGetIntValueByKeyByHandle(qmMfRt, 'mfdone')+1);
if (qmMfUi<>0) and (qmMfMsg<>'') then
ParserSetValueByKeyByHandle(qmMfUi, 'msg', qmMfMsg);
qmLog('mod files '+qmMfReq+' result='+IntToStr(qmMfRes)+' '+qmMfMsg);
