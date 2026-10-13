state: qmSettings
into: data/quartermaster/core.aix
helpers: qmlog, qmstr, qmnum, qmsetfit
requires:
---
//! Mod settings (plan G16; M10): `<save>\quartermaster\settings.cfg` into
//! the named parser qm_settings, which survives a map load (capability
//! probes) - the parser a mod reads its settings from (docs/authoring.md).
//! qmBoot runs it after qmAbout, whose qm_about has every registered mod's
//! declared settings.
//!
//! Layout: one child per mod, named by the mod's id (its about.cfg `id`, or
//! its Workshop number / local folder name), and in it one value per
//! setting id - the way vanilla keeps its hotkeys in a parser file of its own
//! (eventsettings.inc:702-729: ParserAddChildByIndex, ParserSetValueByKey-
//! ByHandle, ParserSaveToFileByHandle). A value that is missing or does not
//! fit its declaration (qmSetFits: a bool not 0/1, a number off its range or
//! its places, a choice not listed, an empty key, a text too long) becomes the
//! default, so a mod always finds a value for every setting it declared.
//! Nothing is written here: the file changes only when the player accepts
//! the Options view (qmUiAct `optacc`).
//!
//! The engine's parser drops a value's leading and trailing spaces when it
//! loads a file (M4 runs); a text setting keeps its inner spaces only.
//!
//! qm_about per row i (qmUiModel copies it): `mid<i>` the child's name.
var qmStT0 : Float = _misc_GetRealTime;
var qmStAb : Integer = ParserSelectByKey('qm_about');
var qmStP : Integer = ParserSelectByKey('qm_settings');
if (qmStP=0) then
qmStP := ParserCreate('qm_settings');
ParserClearByHandle(qmStP);
var qmStPath : String = GetAppSaveDirectoryPath+'quartermaster\settings.cfg';
var qmStLoaded : Integer = 0;
if (FileAge(qmStPath)<>-1) then
begin
   if (ParserLoadFromFileByHandle(qmStP, qmStPath)) then
   qmStLoaded := 1;
end;
var qmStN : Integer = 0;
if (qmStAb<>0) then
qmStN := ParserGetIntValueByKeyByHandle(qmStAb, 'n');
var qmStI : Integer;
var qmStK : Integer;
var qmStS : String;
var qmStSk : String;
var qmStId : String;
var qmStC : Integer;
var qmStV : String;
var qmStOk : Boolean;
var qmStMods : Integer = 0;
var qmStFixed : Integer = 0;
for qmStI:=0 to qmStN-1 do
begin
   qmStS := IntToStr(qmStI);
   qmStId := ParserGetValueByKeyByHandle(qmStAb, 'id'+qmStS);
   if (qmStId='') then
   qmField(ParserGetValueByKeyByHandle(qmStAb, 'nm'+qmStS), '|', 1, qmStId);
   ParserSetValueByKeyByHandle(qmStAb, 'mid'+qmStS, qmStId);
   if (ParserGetIntValueByKeyByHandle(qmStAb, 'sn'+qmStS)>0) and (qmStId<>'') then
   begin
      qmStMods := qmStMods+1;
      qmStC := ParserSelectByHandleByKey(qmStP, qmStId);
      if (qmStC=0) then
      qmStC := ParserAddChildByIndex(qmStP, qmStId);
      for qmStK:=0 to ParserGetIntValueByKeyByHandle(qmStAb, 'sn'+qmStS)-1 do
      begin
         qmStSk := qmStS+'_'+IntToStr(qmStK);
         qmStV := ParserGetValueByKeyByHandle(qmStC, ParserGetValueByKeyByHandle(qmStAb, 'sid'+qmStSk));
         qmStOk := qmSetFits(qmStAb, qmStSk, qmStV);
         if (not qmStOk) then
         begin
            if (qmStV<>'') then
            qmLog('settings: '+qmStId+'.'+ParserGetValueByKeyByHandle(qmStAb, 'sid'+qmStSk)+' = ['+qmStV+'] does not fit its declaration; the default is used');
            ParserSetValueByKeyByHandle(qmStC, ParserGetValueByKeyByHandle(qmStAb, 'sid'+qmStSk), ParserGetValueByKeyByHandle(qmStAb, 'sdf'+qmStSk));
            qmStFixed := qmStFixed+1;
         end;
      end;
   end;
end;
qmLog('settings loaded='+IntToStr(qmStLoaded)+' mods='+IntToStr(qmStMods)+' defaults='+IntToStr(qmStFixed)+' file='+qmStPath+' ms='+FloatToStr((_misc_GetRealTime-qmStT0)*1000));
