hook: data/gui/menu.inc/onlanevent.inc
requires:
---
//! Settings of `host` scope, a client's side (docs/authoring.md, plan S12):
//! when the engine hands the game a received parser - OnLanEvent, the state
//! menu.cfg:26 names for LAN events, with gLanEvent = leParser, where
//! vanilla reads its own messages (onlanevent.inc:176-215, :898) - and it
//! is the host's message 7301 (qmHostSend) on a client, qmHostRecv reads it.
//! Here and not polled from the main-menu tick: the engine selects the
//! received parser for this call - whether it stays selected after it is
//! not known - and a poll would see only the last message of a frame.
//!
//! The build puts the lines at the hook index of plan S5, which is 0 here:
//! the state starts with `var cAllowDebug`, not a routine. They change
//! nothing vanilla does next - its client arm of ParserReceived passes an
//! unknown number by without a word (onlanevent.inc:206-215). 1 is
//! gc_lanmode_client (classes.script:7558), spelled out because hook lines
//! name the engine's API only; `and` short-circuits (capability probes,
//! probe 4), so on every other LAN event the lines cost one comparison.
if (gLanEvent=leParser) and (GetLanMode=1) and (LanGetParserID=7301) then
if (GetTriggerManagerStateMachineHandle('qm_core')<>0) then
StateMachineExecuteState(GetTriggerManagerStateMachineHandle('qm_core'), 'qmHostRecv', 0);
