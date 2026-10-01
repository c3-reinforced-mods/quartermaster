"""Settings of `host` scope (docs/authoring.md) run offline: qmTick in a LAN
room as the host sends the host's values (qmHostSend); the OnLanEvent hook
(src/hooks/onlanevent.pas) on a client hands the host's message to
qmHostRecv, which takes the values of the declared host settings that fit
this copy's declaration; the Options view's save (qmSetSave) keeps the host's
values out of settings.cfg; and qmTick puts the machine's own back when the
session is over. The transport between two machines is the engine's
(LanSendParser, the leParser event) and is not modelled here beyond the
parser the event hands over."""
import copy

import hbuild as H
import test_m10_settings as M10
import test_m3_pascal as PAS
import test_m5_pascal as PAS5

WASD = M10.WASD
HOST_ABOUT = M10.WASD_ABOUT.replace(b"setting = speed;int;6;Speed;1..8..2\r\n",
                                    b"setting = speed;int;6;Speed;1..8..2;host\r\n").replace(
    b"setting = tag;text;qm;Tag;5\r\n", b"setting = tag;text;qm;Tag;5;host\r\n")
PARSER_EVENT = 29       # the test engine's leParser (test_m5_pascal)


def booted():
    eng = M10.booted(files={WASD + b"\\about.cfg": HOST_ABOUT})
    PAS5.load(eng, "qmTick", "qmRestart", "qmMarkerSave", "qmHostSend", "qmHostRecv",
              "qmSetSave", "qmSettings")
    return eng


def tick(eng):
    PAS5.run(eng, "qmTick")


def message(eng, sig, *values):
    h = eng.n_ParserCreate(b"qm_testhostmsg")
    eng.nodes[h].keys = {}
    keys = {"n": len(values), "sig": sig}
    for k, (m, s, v) in enumerate(values):
        keys["m%d" % k], keys["s%d" % k], keys["v%d" % k] = m, s, v
    eng.set("qm_testhostmsg", **keys)
    return h


def hook_lines():
    hook = next(h for h in H.load_hooks() if h.into == "data/gui/menu.inc/onlanevent.inc")
    return H.hook_code(hook, H.BUILD_VARIABLES)


def lan_event(eng, number, h, event=PARSER_EVENT):
    """OnLanEvent with Quartermaster's hook lines in front: the event the
    engine is handling and the parser it hands over."""
    eng.lanevent, eng.lanmsg = event, (number, h)
    PAS.State(hook_lines(), eng).run()


def saved(eng, mod, key):
    tree = eng.saved.get(M10.SETTINGS)
    for name, (keys, _kids) in (tree[1] if tree else []):
        if name == mod:
            return keys.get(key)
    return None


# ------------------------------------------------------------- the host
def test_the_host_sends_its_host_settings_about_once_a_second():
    eng = booted()
    eng.lanmode, eng.lanclients = 2, 2
    tick(eng)
    assert len(eng.lansent) == 1
    aid, keys = eng.lansent[0]
    assert aid == 7301 and keys[b"n"] == b"2"
    assert [(keys[b"m%d" % k], keys[b"s%d" % k], keys[b"v%d" % k]) for k in range(2)] == [
        (b"qmtestwasd", b"speed", b"6"), (b"qmtestwasd", b"tag", b"qm")]
    assert keys[b"sig"] == b"qmtestwasd.speed=6;qmtestwasd.tag=qm;"
    # The next frame is too early; a second later it goes again.
    tick(eng)
    assert len(eng.lansent) == 1
    eng.now += 1.0
    tick(eng)
    assert len(eng.lansent) == 2
    assert eng.key(b"qm_rt", b"hsdrop") == b"0"


def test_nothing_is_sent_alone_in_a_room_or_outside_one():
    eng = booted()
    eng.lanmode, eng.lanclients = 2, 1
    tick(eng)
    eng.lanmode, eng.lanclients = 0, 0
    tick(eng)
    assert not getattr(eng, "lansent", [])


def test_past_256_values_the_rest_is_not_sent_and_the_log_says_so():
    eng = booted()
    # 257 host settings of one mod, as qmAbout would have declared them.
    row = next(i for i in range(int(eng.key(b"qm_about", b"n")))
               if eng.key(b"qm_about", b"mid%d" % i) == b"qmtestwasd")
    eng.set("qm_about", **dict([("sn%d" % row, 257)]
                               + [("sid%d_%d" % (row, k), b"h%d" % k) for k in range(257)]
                               + [("ssc%d_%d" % (row, k), b"host") for k in range(257)]))
    eng.set("qm_rt", hsdry=1)
    eng.lanmode, eng.lanclients = 2, 2
    tick(eng)
    assert eng.key(b"qm_hostout", b"n") == b"256"
    assert eng.key(b"qm_rt", b"hsdrop") == b"1"
    assert any(b"1 more not sent, at most 256 in one message" in line for line in eng.log)


# ----------------------------------------------------------- the client
def test_the_hook_hands_only_the_hosts_message_on_a_client_to_the_receiver():
    eng = booted()
    eng.lanmode = 1
    h = message(eng, b"s1", (b"qmtestwasd", b"speed", b"8"))
    # Another number, another event, or this machine the host: nothing.
    lan_event(eng, 6, h)
    lan_event(eng, 7301, h, event=PARSER_EVENT + 1)
    eng.lanmode = 2
    lan_event(eng, 7301, h)
    assert M10.setting(eng, b"qmtestwasd", b"speed") == b"6"
    eng.lanmode = 1
    lan_event(eng, 7301, h)
    assert M10.setting(eng, b"qmtestwasd", b"speed") == b"8"
    # The main-menu tick reads no message any more.
    eng.lanmsg = (7301, message(eng, b"s2", (b"qmtestwasd", b"speed", b"2")))
    tick(eng)
    assert M10.setting(eng, b"qmtestwasd", b"speed") == b"8"


def test_a_client_takes_the_hosts_values_once_and_only_for_host_settings():
    eng = booted()
    eng.lanmode = 1
    h = message(eng, b"s1", (b"qmtestwasd", b"speed", b"8"), (b"qmtestwasd", b"smooth", b"0"),
                (b"qmtestnothere", b"speed", b"2"))
    lan_event(eng, 7301, h)
    assert M10.setting(eng, b"qmtestwasd", b"speed") == b"8"
    # smooth is local: the host does not decide it; an unknown mod is ignored.
    assert M10.setting(eng, b"qmtestwasd", b"smooth") == b"1"
    assert (eng.key(b"qm_rt", b"hostin"), eng.key(b"qm_rt", b"hostn")) == (b"1", b"1")
    # The same set is not applied again.
    ch = eng.n_ParserSelectByHandleByKey(eng.named[b"qm_settings"], b"qmtestwasd")
    eng.n_ParserSetValueByKeyByHandle(ch, b"speed", b"4")
    lan_event(eng, 7301, h)
    assert M10.setting(eng, b"qmtestwasd", b"speed") == b"4"


def test_a_value_that_does_not_fit_this_copys_declaration_is_not_taken():
    # A host with another version of the mod: speed off 1..8 or not a
    # number, a text past its longest length.
    eng = booted()
    eng.lanmode = 1
    lan_event(eng, 7301, message(eng, b"s1", (b"qmtestwasd", b"speed", b"99"),
                                 (b"qmtestwasd", b"tag", b"toolong")))
    assert M10.setting(eng, b"qmtestwasd", b"speed") == b"6"
    assert M10.setting(eng, b"qmtestwasd", b"tag") == b"qm"
    assert eng.key(b"qm_rt", b"hostn") == b"0"
    assert any(b"qmtestwasd.speed = [99] does not fit" in line for line in eng.log)
    lan_event(eng, 7301, message(eng, b"s2", (b"qmtestwasd", b"speed", b"fast"),
                                 (b"qmtestwasd", b"tag", b"abc")))
    assert M10.setting(eng, b"qmtestwasd", b"speed") == b"6"
    assert M10.setting(eng, b"qmtestwasd", b"tag") == b"abc"


def test_the_options_save_in_a_session_keeps_the_hosts_values_out_of_the_file():
    eng = booted()
    eng.lanmode = 1
    lan_event(eng, 7301, message(eng, b"s1", (b"qmtestwasd", b"speed", b"8"),
                                 (b"qmtestwasd", b"tag", b"host")))
    # The player accepts the Options view (a local setting changed).
    ch = eng.n_ParserSelectByHandleByKey(eng.named[b"qm_settings"], b"qmtestwasd")
    eng.n_ParserSetValueByKeyByHandle(ch, b"smooth", b"0")
    eng.set("qm_rt", setsave=1)
    tick(eng)
    assert (saved(eng, b"qmtestwasd", b"speed"), saved(eng, b"qmtestwasd", b"tag")) == (b"6", b"qm")
    assert saved(eng, b"qmtestwasd", b"smooth") == b"0"
    # The host's values stay in effect for the session.
    assert M10.setting(eng, b"qmtestwasd", b"speed") == b"8"
    assert M10.setting(eng, b"qmtestwasd", b"tag") == b"host"
    # A host setting the player changed in the session is the player's own
    # from now on: saved, and back after the session; the host's stays in
    # effect until then.
    eng.n_ParserSetValueByKeyByHandle(ch, b"speed", b"4")
    eng.set("qm_rt", setsave=1)
    tick(eng)
    assert saved(eng, b"qmtestwasd", b"speed") == b"4"
    assert M10.setting(eng, b"qmtestwasd", b"speed") == b"8"
    eng.lanmode = 0
    tick(eng)
    assert M10.setting(eng, b"qmtestwasd", b"speed") == b"4"
    assert M10.setting(eng, b"qmtestwasd", b"tag") == b"qm"


def test_after_the_session_the_machine_has_its_own_values_again():
    eng = booted()
    eng.lanmode = 1
    lan_event(eng, 7301, message(eng, b"s1", (b"qmtestwasd", b"speed", b"8")))
    assert M10.setting(eng, b"qmtestwasd", b"speed") == b"8"
    before = copy.deepcopy(eng.saved)
    eng.lanmode = 0
    tick(eng)
    assert M10.setting(eng, b"qmtestwasd", b"speed") == b"6"
    assert eng.key(b"qm_rt", b"hostin") == b"0"
    assert eng.key(b"qm_hostown", b"n") in (None, b"")
    # Nothing was written for it: the file never held the host's values.
    assert eng.saved == before
