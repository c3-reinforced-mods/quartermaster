helpers: qmstr
requires:
---
//! qmUnesc: an internal string (the raw reader's form: bytes 32..122 as
//! they are, every other byte as ~NNN, ref/textio.py) back to the bytes it
//! stands for, for a text the GUI shows - a label or a choice from a mod's
//! about.cfg. The engine has no Chr, so the bytes come from a table of
//! #NNN literals (they compile when joined with +, capability probes); the
//! table is built on every call, which only the boot's about.cfg reading
//! makes. A `~` without three digits stays as it is (the reader never
//! makes one).
procedure qmUnesc(const qmUeS : String; var qmUeOut : String);
begin
   var qmUeT : String = '';
   var qmUeI : Integer = 1;
   var qmUeL : Integer = StrLength(qmUeS);
   var qmUeC : String;
   var qmUeD : String;
   var qmUeB : Integer;
   qmUeOut := '';
   if (StrPos('~', qmUeS)=0) then
   begin
      qmUeOut := qmUeS;
      exit;
   end;
   qmUeT := qmUeT+#1+#2+#3+#4+#5+#6+#7+#8+#9+#10+#11+#12+#13+#14+#15+#16+#17+#18+#19+#20+#21+#22+#23+#24+#25+#26+#27+#28+#29+#30+#31+#32;
   qmUeT := qmUeT+#33+#34+#35+#36+#37+#38+#39+#40+#41+#42+#43+#44+#45+#46+#47+#48+#49+#50+#51+#52+#53+#54+#55+#56+#57+#58+#59+#60+#61+#62+#63+#64;
   qmUeT := qmUeT+#65+#66+#67+#68+#69+#70+#71+#72+#73+#74+#75+#76+#77+#78+#79+#80+#81+#82+#83+#84+#85+#86+#87+#88+#89+#90+#91+#92+#93+#94+#95+#96;
   qmUeT := qmUeT+#97+#98+#99+#100+#101+#102+#103+#104+#105+#106+#107+#108+#109+#110+#111+#112+#113+#114+#115+#116+#117+#118+#119+#120+#121+#122+#123+#124+#125+#126+#127+#128;
   qmUeT := qmUeT+#129+#130+#131+#132+#133+#134+#135+#136+#137+#138+#139+#140+#141+#142+#143+#144+#145+#146+#147+#148+#149+#150+#151+#152+#153+#154+#155+#156+#157+#158+#159+#160;
   qmUeT := qmUeT+#161+#162+#163+#164+#165+#166+#167+#168+#169+#170+#171+#172+#173+#174+#175+#176+#177+#178+#179+#180+#181+#182+#183+#184+#185+#186+#187+#188+#189+#190+#191+#192;
   qmUeT := qmUeT+#193+#194+#195+#196+#197+#198+#199+#200+#201+#202+#203+#204+#205+#206+#207+#208+#209+#210+#211+#212+#213+#214+#215+#216+#217+#218+#219+#220+#221+#222+#223+#224;
   qmUeT := qmUeT+#225+#226+#227+#228+#229+#230+#231+#232+#233+#234+#235+#236+#237+#238+#239+#240+#241+#242+#243+#244+#245+#246+#247+#248+#249+#250+#251+#252+#253+#254+#255;
   while (qmUeI<=qmUeL) do
   begin
      qmUeC := SubStr(qmUeS, qmUeI, 1);
      qmUeD := SubStr(qmUeS, qmUeI+1, 3);
      if (qmUeC='~') and (StrLength(qmUeD)=3) and (qmIsDigits(qmUeD)) then
      begin
         qmUeB := StrToInt(qmUeD);
         if (qmUeB>=1) and (qmUeB<=255) then
         qmUeOut := qmUeOut+SubStr(qmUeT, qmUeB, 1);
         qmUeI := qmUeI+4;
      end
      else
      begin
         qmUeOut := qmUeOut+qmUeC;
         qmUeI := qmUeI+1;
      end;
   end;
end;
