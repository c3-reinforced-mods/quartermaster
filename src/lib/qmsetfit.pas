helpers: qmstr, qmnum
requires:
---
//! Whether a setting's value fits its declaration: qm_about (qmAbout) of
//! the mod's row, the setting `<row>_<k>` in qmSfSk. A bool is 0 or 1; an
//! int or float has exactly its places and lies in its range; a choice is
//! one of its options; a key is not empty; a text is not longer than its
//! longest length, and empty only when that is its default. qmSettings
//! checks the stored values with it, qmHostRecv the host's: a host with
//! another version of a mod can send what this copy does not declare, and a
//! mod reads its values as its own copy declares them (docs/authoring.md).
function qmSetFits(const qmSfAb : Integer; const qmSfSk : String; const qmSfV : String) : Boolean;
begin
   var qmSfTy : String = ParserGetValueByKeyByHandle(qmSfAb, 'sty'+qmSfSk);
   var qmSfOk : Boolean = (qmSfV<>'');
   var qmSfD : Integer;
   var qmSfX : Integer;
   if (qmSfOk) and (qmSfTy='bool') then
   qmSfOk := (qmSfV='0') or (qmSfV='1');
   if (qmSfOk) and ((qmSfTy='int') or (qmSfTy='float')) then
   begin
      qmSfD := ParserGetIntValueByKeyByHandle(qmSfAb, 'sdc'+qmSfSk);
      qmSfOk := qmNumOk(qmSfV, qmSfD);
      if (qmSfOk) then
      begin
         //! The places must be exact: a stored value is always written
         //! with them (qmNumText), so any other text is not ours.
         if (qmSfD=0) then
         qmSfOk := (StrPos('.', qmSfV)=0)
         else
         qmSfOk := (StrPos('.', qmSfV)=StrLength(qmSfV)-qmSfD);
      end;
      if (qmSfOk) then
      begin
         qmSfX := qmNumScaled(qmSfV, qmSfD);
         qmSfOk := (qmSfX>=ParserGetIntValueByKeyByHandle(qmSfAb, 'slo'+qmSfSk)) and (qmSfX<=ParserGetIntValueByKeyByHandle(qmSfAb, 'shi'+qmSfSk));
      end;
   end;
   if (qmSfOk) and (qmSfTy='choice') then
   qmSfOk := (StrPos('|'+qmSfV+'|', ParserGetValueByKeyByHandle(qmSfAb, 'sop'+qmSfSk))>0);
   if (qmSfOk) and (qmSfTy='text') and (ParserGetIntValueByKeyByHandle(qmSfAb, 'smx'+qmSfSk)>0) then
   qmSfOk := (StrLength(qmSfV)<=ParserGetIntValueByKeyByHandle(qmSfAb, 'smx'+qmSfSk));
   //! An empty text is a value too, when it is the default.
   if (not qmSfOk) and (qmSfTy='text') and (qmSfV='') and (ParserGetValueByKeyByHandle(qmSfAb, 'sdf'+qmSfSk)='') then
   qmSfOk := True;
   Result := qmSfOk;
end;
