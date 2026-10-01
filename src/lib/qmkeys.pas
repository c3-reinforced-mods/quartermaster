helpers:
requires:
---
//! What the game itself holds against a key a mod's key setting wants - the
//! one rule of the Options view (qmUiAct qmUaKeyCheck) and of the activation
//! check (qmTrial), so the two cannot drift apart. Each gives the reason in
//! its last parameter, empty when the game has nothing against the key.
//!
//! qmKeyForbidden  a key the game does not let a hotkey use at all: vanilla's
//!                 own lists (hotkeysettings.inc:24-133), mouse buttons, Esc
//! qmKeyGameUse    a key the game already uses: an action of the player's
//!                 hotkeys (<save>\hotkeys\hotkeys.cfg, else
//!                 .\data\game\var\hotkeys.cfg, the files RegisterShortcuts
//!                 reads, registershortcuts.inc:187-192) but an `event` one,
//!                 or a shortcut the effective registershortcuts.inc
//!                 registers by its literal name (a mod that reads its key
//!                 from a setting registers none). Both game files are read
//!                 through the engine's parser, the way the game reads them
//!                 (.\data goes through the mod overlay).
procedure qmKeyForbidden(const qmKfKey : String; var qmKfWhy : String);
begin
   var qmKfLow : String = StrToLowerCase(qmKfKey);
   var qmKfSingle : String = '|LButton|RButton|MButton|Left|Right|Up|Down|Space|Return|PrintScreen0|PrintScreen1|PrintScreen2|F10|Sub|Add|-|=|PGUP|PGDN|Del|Home|Shift|ShiftUp|Ctrl|CtrlUp|Alt|AltUp|0|1|2|3|4|5|6|7|8|9|Back|F5|F7|NUM0|NUM1|NUM2|NUM3|NUM4|NUM5|NUM6|NUM7|NUM8|NUM9|P|[|]|Escape|';
   var qmKfCombo : String = '|Alt+F4|Ctrl+Shift+P|Ctrl+PGUP|Ctrl+PGDN|Ctrl+Home|Ctrl+S|Ctrl+Tab|Ctrl+0|Ctrl+1|Ctrl+2|Ctrl+3|Ctrl+4|Ctrl+5|Ctrl+6|Ctrl+7|Ctrl+8|Ctrl+9|Shift+0|Shift+1|Shift+2|Shift+3|Shift+4|Shift+5|Shift+6|Shift+7|Shift+8|Shift+9|Shift+Alt+0|Shift+Alt+1|Shift+Alt+2|Shift+Alt+3|Shift+Alt+4|Shift+Alt+5|Shift+Alt+6|Shift+Alt+7|Shift+Alt+8|Shift+Alt+9|Shift+Alt+Mul|Alt+0|Alt+1|Alt+2|Alt+3|Alt+4|Alt+5|Alt+6|Alt+7|Alt+8|Alt+9|Alt+Mul|Ctrl+W|Ctrl+F|Ctrl+Sub|Ctrl+Add|Ctrl+T|';
   qmKfWhy := '';
   // The reasons a key is not taken.
   if (StrPos('+', qmKfKey)>0) then
   begin
      if (StrPos('|'+qmKfKey+'|', qmKfCombo)>0) then
      qmKfWhy := 'the game does not let a hotkey use it';
   end
   else
   if (StrPos('|'+qmKfKey+'|', qmKfSingle)>0) then
   qmKfWhy := 'the game does not let a hotkey use it';
   if (StrPos('lbutton', qmKfLow)>0) or (StrPos('rbutton', qmKfLow)>0) or (StrPos('escape', qmKfLow)>0) then
   qmKfWhy := 'the game does not let a hotkey use it';
end;

procedure qmKeyGameUse(const qmKuKey : String; var qmKuWhy : String);
begin
   var qmKuP : Integer = ParserSelectByKey('qm_keys_src');
   var qmKuJ : Integer;
   var qmKuC : Integer;
   var qmKuLine : String;
   var qmKuQ : Integer;
   var qmKuName : String;
   var qmKuRest : String;
   var qmKuHit : String;
   qmKuWhy := '';
   if (qmKuP=0) then
   qmKuP := ParserCreate('qm_keys_src');
   ParserClearByHandle(qmKuP);
   if (FileAge(GetAppSaveDirectoryPath+'hotkeys\hotkeys.cfg')<>-1) then
   ParserLoadFromFileByHandle(qmKuP, GetAppSaveDirectoryPath+'hotkeys\hotkeys.cfg')
   else
   ParserLoadFromFileByHandle(qmKuP, '.\data\game\var\hotkeys.cfg');
   //! A mod's key works everywhere, like vanilla's `interface` hotkeys, so it
   //! meets what they meet in IsKeyAlreadySet: every action but an `event`
   //! one (the 'se','in' arm, hotkeysettings.inc:210-216; an action's type is
   //! its text before `|`, GetAction :4-17).
   for qmKuJ:=0 to ParserGetCountByHandle(qmKuP)-1 do
   begin
      qmKuC := ParserSelectByHandleByIndex(qmKuP, qmKuJ);
      qmKuName := ParserGetValueByKeyByHandle(qmKuC, 'action');
      if (qmKuWhy='') and (SubStr(qmKuName, 1, 6)<>'event|') then
      if SameText(ParserGetValueByKeyByHandle(qmKuC, 'key'), qmKuKey) or SameText(ParserGetValueByKeyByHandle(qmKuC, 'alternativekey'), qmKuKey) then
      qmKuWhy := 'the game''s hotkey '+qmKuName+' uses it';
   end;
   ParserClearByHandle(qmKuP);
   if (qmKuWhy<>'') then
   exit;
   ParserLoadFromFileByHandle(qmKuP, '.\data\gui\menu.inc\registershortcuts.inc');
   qmKuC := ParserSelectByHandleByKey(qmKuP, 'Code');
   if (qmKuC<>0) then
   for qmKuJ:=0 to ParserGetCountByHandle(qmKuC)-1 do
   if (qmKuWhy='') then
   begin
      qmKuLine := ParserGetValueByIndexByHandle(qmKuC, qmKuJ);
      qmKuQ := StrPos('RegisterGUIShortcut', qmKuLine);
      if (qmKuQ>0) and ((StrPos('//', qmKuLine)=0) or (StrPos('//', qmKuLine)>qmKuQ)) then
      begin
         //! The name and the key are the call's first two string literals.
         qmKuRest := SubStr(qmKuLine, qmKuQ, StrLength(qmKuLine)-qmKuQ+1);
         qmKuQ := StrPos('''', qmKuRest);
         if (qmKuQ>0) then
         begin
            qmKuRest := SubStr(qmKuRest, qmKuQ+1, StrLength(qmKuRest)-qmKuQ);
            qmKuQ := StrPos('''', qmKuRest);
            qmKuName := SubStr(qmKuRest, 1, qmKuQ-1);
            qmKuRest := SubStr(qmKuRest, qmKuQ+1, StrLength(qmKuRest)-qmKuQ);
            qmKuQ := StrPos(',', qmKuRest);
            if (qmKuQ>0) then
            begin
               qmKuRest := SubStr(qmKuRest, qmKuQ+1, StrLength(qmKuRest)-qmKuQ);
               while (SubStr(qmKuRest, 1, 1)=' ') do
               qmKuRest := SubStr(qmKuRest, 2, StrLength(qmKuRest)-1);
               if (SubStr(qmKuRest, 1, 1)='''') then
               begin
                  qmKuRest := SubStr(qmKuRest, 2, StrLength(qmKuRest)-1);
                  qmKuQ := StrPos('''', qmKuRest);
                  qmKuHit := SubStr(qmKuRest, 1, qmKuQ-1);
                  if (qmKuQ>0) and SameText(qmKuHit, qmKuKey) then
                  qmKuWhy := 'the game''s shortcut '+qmKuName+' uses it';
               end;
            end;
         end;
      end;
   end;
   ParserClearByHandle(qmKuP);
end;
