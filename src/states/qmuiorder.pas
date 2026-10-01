state: qmUiOrder
into: data/quartermaster/core.aix
helpers: qmlog
requires:
---
//! The manager window's load-order commands (decided 2026-09-28; the keys
//! are agreed with the window's controller qmUiAct and listed in docs/ui.md;
//! twin: ref/order.py ui_move). qmUiAct copies the command into qm_ui `ocmd`
//! and runs this state:
//!   up / down   arg = the row (qm_ui sel): one place up or down the Active list
//!   move        arg = the row, argto = the place (0-based) it must have in the
//!               Active list afterwards - the window's drag, if the engine
//!               allows one
//! The pending order is qm_ui ord<k> (every row, Quartermaster last); oord<k>
//! is the order the running game loaded, copied when the window opened.
//!
//! Rules: only the rows that will be active (pe<i> = 1) move, and only among
//! the slots they hold in ord<k> - an inactive row keeps its slot, so it
//! comes back where it was when it is activated again. Quartermaster never
//! moves and nothing goes below it (plan S1: it carries the hook lines and
//! must be the final override). A place beyond the ends is clamped.
//!
//! Out: ord<k>, ordchg (1 when ord<k> differs from oord<k> anywhere: a pending
//! change, so Apply is enabled), omoved (this command
//! moved the row), msg ('' when it moved or stayed on a drag to its own
//! place, else why not). The Apply carries ord<k> to qm_rt uiapplyord<k>
//! (qmUiApply) and the boot's qmOrder makes it the saved load order.
var qmUoUi : Integer = ParserSelectByKey('qm_ui');
if (qmUoUi=0) then
exit;
var qmUoCmd : String = ParserGetValueByKeyByHandle(qmUoUi, 'ocmd');
var qmUoRow : Integer = ParserGetIntValueByKeyByHandle(qmUoUi, 'arg');
var qmUoTo : Integer = ParserGetIntValueByKeyByHandle(qmUoUi, 'argto');
var qmUoN : Integer = ParserGetIntValueByKeyByHandle(qmUoUi, 'n');
var qmUoSelf : Integer = ParserGetIntValueByKeyByHandle(qmUoUi, 'self');
var qmUoOrd : array [0..255] of Integer;
var qmUoSlot : array [0..255] of Integer;
var qmUoAct : array [0..255] of Integer;
var qmUoNa : Integer = 0;
var qmUoAt : Integer = -1;
var qmUoLim : Integer;
var qmUoGo : Integer = -1;
var qmUoK : Integer;
var qmUoI : Integer;
var qmUoMoved : Integer = 0;
var qmUoChg : Integer = 0;
var qmUoMsg : String = '';
var qmUoLine : String = '';
if (qmUoN>256) then
qmUoN := 256;
for qmUoK:=0 to qmUoN-1 do
begin
   qmUoOrd[qmUoK] := ParserGetIntValueByKeyByHandle(qmUoUi, 'ord'+IntToStr(qmUoK));
   qmUoI := qmUoOrd[qmUoK];
   if (qmUoI>=0) and (qmUoI<qmUoN) then
   if (ParserGetIntValueByKeyByHandle(qmUoUi, 'pe'+IntToStr(qmUoI))=1) then
   begin
      qmUoSlot[qmUoNa] := qmUoK;
      qmUoAct[qmUoNa] := qmUoI;
      if (qmUoI=qmUoRow) then
      qmUoAt := qmUoNa;
      qmUoNa := qmUoNa+1;
   end;
end;
//! The last place a row may take: before Quartermaster, when it is the last
//! active row (it always is while the boot knows its folder).
qmUoLim := qmUoNa-1;
if (qmUoNa>0) and (qmUoSelf>=0) then
if (qmUoAct[qmUoNa-1]=qmUoSelf) then
qmUoLim := qmUoNa-2;
// The texts of the refusals.
if (qmUoCmd<>'up') and (qmUoCmd<>'down') and (qmUoCmd<>'move') then
qmUoMsg := 'Unknown order command.'
else
if (qmUoRow<0) or (qmUoRow>=qmUoN) then
qmUoMsg := 'Select a mod in the Active list first.'
else
if (qmUoRow=qmUoSelf) then
qmUoMsg := 'Quartermaster always loads last.'
else
if (qmUoAt<0) then
qmUoMsg := 'Only an active mod has a place in the load order.'
else
begin
   if (qmUoCmd='up') then
   qmUoGo := qmUoAt-1
   else
   if (qmUoCmd='down') then
   qmUoGo := qmUoAt+1
   else
   begin
      qmUoGo := qmUoTo;
      if (qmUoGo<0) then
      qmUoGo := 0;
      if (qmUoGo>qmUoLim) then
      qmUoGo := qmUoLim;
   end;
   if (qmUoGo<0) then
   begin
      qmUoMsg := 'This mod loads first already.';
      qmUoGo := qmUoAt;
   end
   else
   if (qmUoGo>qmUoLim) then
   begin
      qmUoMsg := 'This mod loads last already; only Quartermaster comes after it.';
      qmUoGo := qmUoAt;
   end;
end;
if (qmUoGo>=0) and (qmUoAt>=0) and (qmUoGo<>qmUoAt) then
begin
   //! Take the row out of the active list and put it in at its new place;
   //! the active rows go back into the slots they held.
   if (qmUoGo<qmUoAt) then
   begin
      for qmUoK:=qmUoAt downto qmUoGo+1 do
      qmUoAct[qmUoK] := qmUoAct[qmUoK-1];
   end
   else
   begin
      for qmUoK:=qmUoAt to qmUoGo-1 do
      qmUoAct[qmUoK] := qmUoAct[qmUoK+1];
   end;
   qmUoAct[qmUoGo] := qmUoRow;
   for qmUoK:=0 to qmUoNa-1 do
   qmUoOrd[qmUoSlot[qmUoK]] := qmUoAct[qmUoK];
   for qmUoK:=0 to qmUoN-1 do
   ParserSetIntValueByKeyByHandle(qmUoUi, 'ord'+IntToStr(qmUoK), qmUoOrd[qmUoK]);
   qmUoMoved := 1;
end;
for qmUoK:=0 to qmUoN-1 do
if (qmUoOrd[qmUoK]<>ParserGetIntValueByKeyByHandle(qmUoUi, 'oord'+IntToStr(qmUoK))) then
qmUoChg := 1;
ParserSetIntValueByKeyByHandle(qmUoUi, 'ordchg', qmUoChg);
ParserSetIntValueByKeyByHandle(qmUoUi, 'omoved', qmUoMoved);
ParserSetValueByKeyByHandle(qmUoUi, 'msg', qmUoMsg);
for qmUoK:=0 to qmUoNa-1 do
begin
   if (qmUoLine<>'') then
   qmUoLine := qmUoLine+' | ';
   qmUoLine := qmUoLine+ParserGetValueByKeyByHandle(qmUoUi, 'dir'+IntToStr(qmUoAct[qmUoK]));
end;
qmLog('ui order '+qmUoCmd+' row='+IntToStr(qmUoRow)+' to='+IntToStr(qmUoTo)+' moved='+IntToStr(qmUoMoved)+' ordchg='+IntToStr(qmUoChg)+' active='+qmUoLine);
