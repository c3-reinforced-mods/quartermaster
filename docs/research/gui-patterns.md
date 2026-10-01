# Vanilla GUI patterns for the Quartermaster manager (2026-09-27)

Source: read-only survey of `data/gui/menu.inc/*.inc`. `M` = `data/gui/menu.inc/`, `L` = `data/scripts/lib/`, `A` = `data/gui/menu.aix`. Not yet exercised in-game by Quartermaster.

## 1. Opening / handling / closing a screen
- States are declared in `A` (`Name = ShowX`, `LanClientExecute = True`, `UsedFile = True`, `UsedFileName = ...`), e.g. `A:603-615`. **Quartermaster never generates menu.aix** -> its own screens live in its own `.aix` loaded at runtime into a trigger manager, and events are forwarded from a hooked vanilla Event state (e.g. EventMainMenu).
- `_misc_GetGUIShowEventStateNames` (`L\misc.script:1929`) strips Show/Event -> root element name.
- Open from main menu: `M\eventmainmenu.inc:46-52` (hide `elmname+'.col1'` and `News.Newspn.news`, `gint_gui_newsshowvisible := 1`, `ExecuteState('ShowCampaign')`). `cTagModManager` (108) at `:154-156` only does `OpenURL(...)`; button in `M\showmainmenu.inc:141` via local `ShowButton` (`:16-24`).
- Modal skeleton `M\showcreatejoinroom.inc:219-226` (also `showsettings.inc:681-702`): `_gui_CreateParent(...)`, black mask `_gui_CreateImageActive('blackmask', ...)` + `SetGUIElementUserBlend(elmMask, 0.65)`, `SetGUIElementPressState(elmParent, eventstate)`, `SetGUIEventStateOnKeyDown(eventstate)`. Esc/Enter routed by `M\onshortcut.inc:158-176`.
- Frame + close: `M\showcampaign.inc:313-320` (`_gui_CreateMainWindow`, `_gui_CreateButton('bback', ..., 'btn.close', ..., gc_gui_event_tagClose, ...)`).
- Event skeleton `M\eventcampaign.inc:4-59` (reads ElementHandle/Press/Status/Tag; `press='c'` -> case tag: tagShow / tagHide / back|close|Esc -> hide, `ExecuteState('ShowMainMenu')`, news). Tag constants `data/scripts/dmscript.global:1178-1182` (Show 8001, Hide 8002, Close 8003, Esc 9001, Enter 9002). Refresh = `ExecuteState(showstate)` again.

## 2. ListBox with columns - template `M\showcampaign.inc`
- `:115-118`: `_gui_CreateListBox(listname, parent, ..., gc_font_serif_12, eventstate, False, bupdate)`; `AddGUIListBoxTabProperty(elmList, 1,1,1,1, width, 'tsText')` per column; `GUIListBoxClearSilent`.
- Items: `GUIListBoxAddItem(elmList, #9+name+#9, id)` (`:183`); inline colour `'%color(656060)%'` (`:130`).
- Selection/scroll `:190, 246-253`: `SetGUIListBoxItemIndexSilent`, `_gui_SetListBoxHeight`, `_gui_AddScroller`, `SetGUIListBoxTopIndex`, `_gui_UpdateListBoxScrollerPos`; save `GetGUIListBoxTopIndex`/`GetGUIListBoxItemIndex` before rebuild (`:49-55`).
- Status icons: `'tsImage'` column whose cell text is a material name (`M\showinternetshell.inc:721-735, 821`, e.g. `net.client.state.play`). Fonts likely lack OK/WARN/FAIL glyphs -> use text tags or materials.
- Gotcha with `bupdate=True`: tabs accumulate -> delete first (`M\showloadgame.inc:95-100`).
- Selection event `M\eventcampaign.inc:16-24`: `status='select'` -> `GetGUIListBoxItemTag(elmHnd, GetGUIListBoxItemIndex(elmHnd))`.
- Details panel `M\showcampaign.inc:262-278`: `GetGUIWrappedTextByFont` -> `_gui_CreateScrollLayer` -> `_gui_CreateText` -> `_gui_AddScroller`.
- Reorder: `GUIListBoxInsertItem`/`DeleteItem`/`SetGUIListBoxItemValue`/`SetGUIListBoxItemTag`, or rebuild from own array.

## 3. Text input
- `M\showcreatejoinroom.inc:160-190` (`ShowInput`): `_gui_CreateInputBox(elmName, parent, text, ..., width, maxlength, eventstate, nul, bEnabled, 10,1, gc_halLeft, gc_valMiddle, font, 1,1,1,1, bupdate)`, `SetGUIElementFocusedHandle(GetGUIElementIndexByNameParent('text', Result))`, `_gui_InputBoxSetupStrCharFilter(Result, True, gc_gui_charfilter_default)`.
- Read: `GetGUIElementText(GetGUIElementIndexByNameParent('text', childHnd))` (`M\eventcreatejoinroom.inc:4-18`; short form `M\eventloadgame.inc:35-38`).
- Enter/Esc in field: `status='key'`, `press='d'`, `tag=13|27` (`M\eventcreatejoinroom.inc:41-66`). Numeric: `_gui_InputBoxSetupNumCharFilter` (`L\gui.script:711`), `gc_gui_charfilter_numeric` (`dmscript.global:1219`).

## 4. Checkbox, dropdown, slider, persistence
- Checkbox `_gui_CreateCheckBox(name, parent, bChecked, ..., eventstate, hint, tag, bupdate)` (`L\gui.script:993`); label pattern `M\showsettings.inc:1098-1101`; helper `M\showcreatejoinroom.inc:198-207`; toggle `M\eventsettings.inc:629-633`.
- Dropdown `_gui_CreateComboBox(...)` + `GUIListBoxAddItem` + `SetGUIListBoxItemIndexSilent` (`M\showsettings.inc:758-770`, `M\showcampaign.inc:101-110`); event `status='select'` (`M\eventsettings.inc:455-489`).
- Slider: copy `CreateSimpleSlider` (`M\showsettings.inc:4-20`, elements `sliderline`/`sliderbtn`, id in StringTag); value `ModifySliderValueByMouseCoord` (`M\eventsettings.inc:197-226`, dispatch `:339-405`); drag routed for elements named sliderline/sliderbtn (`data/gui/common.inc/onmousehook.inc:9-12`, `M\onmousemove.inc:36-58`); on release re-runs `Show+<PressState minus 'Event'>`.
- Persistence: settings edit copies (`gProfileTmp := gProfile`, `L\gui.script:2637-2657`), Accept/Cancel `M\eventsettings.inc:692-739`. Mods cannot add gProfile fields -> own parser file like the hotkey Accept path (`:702-729`: `ParserAddChildByIndex`, `ParserSetValueByKeyByHandle`, `ParserSaveToFileByHandle(p, GetAppSaveDirectoryPath+...)`).

## 5. Key capture
- Start: `M\eventsettings.inc:904-928` (`gint_gui_hotkeytoedit := ...; SetGUIEventStateOnKeyDown('HotkeySettings')`).
- Capture: `M\hotkeysettings.inc:225-261` (`GetKeyNameByCode(GetIntValueByName('Tag'))`, ignore names longer than 2 chars, Ctrl/Shift/Alt prefix via `IsGUIShortcutPressed`, `IsValidKey`). Blocklists `forbiddenkeys`/`forbiddencombokeys` (`:20-133`), `IsValidKey` (`:135-160`), duplicate -> `_gui_ShowModalMessage` (`:282-287`). End: `SetGUIEventStateOnKeyDown('')` (`M\eventsettings.inc:670, 928`).

## 6. Dialogs, URL, restart
- `_gui_ShowModalMessage(header, msg, btn1, btn2, tag1, tag2)` (`L\gui.script:2511-2521`) - but button tags go to `EventModalMessage` (`M\eventmodalmessage.inc:21-146`), not your state -> Quartermaster needs its own dialog.
- `SetupWindow` pattern (local to `M\showconnectstatemessage.inc:71-83, 192, 244-293`; `_gui_CreatePaperWindow`).
- `OpenURL` (`M\eventmainmenu.inc:155`, `M\eventnews.inc:54`). Restart `M\onworkshopautoupdate.inc:10-11`. Mod list `M\showmainmenu.inc:174-186`.

## 7. Localisation
- `GetLocaleTableListItemByID(table, key)` returns '' if missing; `_misc_GetNewTextLocale` (`L\misc.script:6307-6318`). Plain strings are safe: `_gui_CreateText` -> `_misc_StringToText` (`L\misc.script:732-758`) resolves only `table|key` and otherwise returns the text.
- Own table at runtime: `AddLocaleTableList(id, path)` (`M\showannouncement.inc:18-22`, `M\showcampaign.inc:164-168`). `.lng` binary: u32 count, then per record u32 length + `key=value` bytes + `0x03`. Prototype: plain English strings only.
