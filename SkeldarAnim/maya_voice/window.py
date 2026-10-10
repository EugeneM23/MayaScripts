"""maya_voice.window - the Voice section of the hub.

    import maya_voice.window; maya_voice.window.show_window()   # the hub, on Voice

The animator (2026-10-10): «давай попробуем реализовать группу голосового чата
(как в дискорд) с возможностью шейринга экрана». The panel: the rooms on the
server (who is in each), a room to join, the roster of the room, mute, deafen,
share the screen, the viewer of a shared screen, and one status line.

Everything runs on Maya's main thread. One Qt timer (`PUMP_MS`) drains the
session's events, sends the microphone's packets, plays what arrived, sends a
screen frame when sharing, refreshes the lists, and fetches the lobby now and
then. The socket threads never touch cmds or Qt.

A dropped connection keeps the microphone and the speaker, clears the roster
and retries with a growing pause (`RETRY_STEPS`). Leave stops everything.

State lives on `sys._skeldar_voice` (trap 111): an install purges our modules,
and a call in flight must still find the one connection it made.

Spec: docs/superpowers/specs/2026-10-10-voice-screen-design.md
"""

import queue
import sys
import time
import traceback

import maya.cmds as cmds

from maya_voice import gate as gatemod
from maya_voice import jitter as jittermod
from maya_voice import protocol
from maya_voice import roster as rostermod
from maya_voice import session as sessionmod

HUB_SECTION = "voice"
NAME_FIELD = "skeldarVoiceName"
SERVER_FIELD = "skeldarVoiceServer"
ROOM_FIELD = "skeldarVoiceRoom"
ROOMS_LIST = "skeldarVoiceRooms"
ROSTER_LIST = "skeldarVoiceRoster"
JOIN_BUTTON = "skeldarVoiceJoin"
LEAVE_BUTTON = "skeldarVoiceLeave"
MUTE_BUTTON = "skeldarVoiceMute"
DEAFEN_BUTTON = "skeldarVoiceDeafen"
SHARE_BUTTON = "skeldarVoiceShare"
VIEW_BUTTON = "skeldarVoiceView"
STATUS = "skeldarVoiceStatus"
SUBTITLE = "skeldarVoiceSubtitle"
LIST_HEIGHT = 110

PUMP_MS = 30
PACKET_SECONDS = protocol.PACKET_MS / 1000.0
SCREEN_FPS = 6.0
LOBBY_EVERY = 6.0
ROSTER_EVERY = 0.5
RETRY_STEPS = (2, 4, 8, 16, 30)
OPT_NAME = "skeldarVoiceName"
OPT_SERVER = "skeldarVoiceServer"
OPT_ROOM = "skeldarVoiceRoom"


# ------------------------------------------------------------------ state

def state():
    """The section's state on `sys`, one per Maya session."""
    st = getattr(sys, "_skeldar_voice", None)
    if st is None:
        st = {
            "session": None, "roster": rostermod.Roster(),
            "mic": None, "speaker": None, "timer": None, "viewer": None,
            "gate": gatemod.Gate(), "pending": bytearray(), "seq": 0,
            "video_seq": 0, "muted": False, "deafened": False,
            "sharing": False, "jitter": {}, "frames": {}, "shown": None,
            "shown_seq": None, "next_play": None, "screen_at": 0.0,
            "lobby": queue.Queue(), "rooms": [], "lobby_at": 0.0,
            "lobby_busy": False, "rooms_text": "", "wanted": False,
            "room": "", "server": "", "name": "", "retry": 0,
            "retry_at": None, "roster_sig": None, "status": "",
        }
        sys._skeldar_voice = st
    return st


def _status(message, **_kwargs):
    st = state()
    st["status"] = message
    try:
        cmds.text(STATUS, edit=True, label=message)
    except RuntimeError:
        pass                              # the panel is not built
    return message


def _settings():
    """(name, server, room) as typed in the panel, or what was remembered."""
    st = state()

    def field(control, fallback):
        try:
            return cmds.textField(control, query=True, text=True).strip()
        except RuntimeError:
            return fallback
    name = field(NAME_FIELD, st["name"]) or st["name"]
    server = field(SERVER_FIELD, st["server"]) or st["server"]
    room = field(ROOM_FIELD, "")
    return name, server, room


def _remember(name, server, room):
    st = state()
    st["name"], st["server"] = name, server
    cmds.optionVar(stringValue=(OPT_NAME, name))
    cmds.optionVar(stringValue=(OPT_SERVER, server))
    if room:
        cmds.optionVar(stringValue=(OPT_ROOM, room))


def remembered():
    """(name, server, room) from the last session, read from optionVars."""
    def read(key):
        try:
            return cmds.optionVar(query=key) or ""
        except RuntimeError:
            return ""
    return read(OPT_NAME), read(OPT_SERVER), read(OPT_ROOM)


# --------------------------------------------------------------- rooms

def _rooms_label(entry):
    names = entry.get("members") or []
    tail = (": " + ", ".join(names)) if names else ""
    return "{0} ({1}){2}".format(entry.get("room", "?"), len(names), tail)


def _show_rooms(rooms):
    st = state()
    st["rooms"] = [r.get("room", "") for r in rooms]
    try:
        cmds.textScrollList(ROOMS_LIST, edit=True, removeAll=True)
        for entry in rooms:
            cmds.textScrollList(ROOMS_LIST, edit=True,
                                append=_rooms_label(entry))
    except RuntimeError:
        pass


def _on_room_picked(*_args):
    st = state()
    try:
        picked = cmds.textScrollList(ROOMS_LIST, query=True,
                                     selectIndexedItem=True) or []
    except RuntimeError:
        return
    if not picked:
        return
    index = picked[0] - 1
    if 0 <= index < len(st["rooms"]):
        try:
            cmds.textField(ROOM_FIELD, edit=True, text=st["rooms"][index])
        except RuntimeError:
            pass


def refresh_lobby(force=False):
    st = state()
    now = time.time()
    if st["lobby_busy"]:
        return
    if not force and now - st["lobby_at"] < LOBBY_EVERY:
        return
    server = _settings()[1]
    if not server:
        return
    st["lobby_at"] = now
    st["lobby_busy"] = True
    sessionmod.fetch_rooms_async(server, st["lobby"])


# ------------------------------------------------------------- connect

def join(room=None):
    """Join `room` (or the one typed). Refused by name when it cannot."""
    st = state()
    name, server, typed = _settings()
    room = protocol.clean_room(room or typed)
    if room is None:
        return _status("Room names are letters, digits, dashes, "
                       "e.g. layout-room.")
    if not server:
        return _status("Type the server address first (the Cloudflare "
                       "worker, e.g. skeldar-voice.name.workers.dev).")
    if st["session"] is not None and st["room"] == room:
        return _status("You are in {0} already.".format(room))
    if st["session"] is not None:
        leave(quiet=True)
    _remember(protocol.clean_name(name), server, room)
    st["room"] = room
    st["wanted"] = True
    st["retry"] = 0
    st["retry_at"] = None
    _ensure_devices()
    _start_timer()
    return _connect()


def _connect():
    st = state()
    name = st["name"] or "Guest"
    url = sessionmod.room_url(st["server"], st["room"])
    try:
        sess = sessionmod.Session()
        sess.open(url, name)
    except Exception as exc:                           # noqa: BLE001
        return _lost("could not connect: {0}".format(exc))
    st["session"] = sess
    st["roster"].reset()
    st["jitter"] = {}
    st["frames"] = {}
    st["next_play"] = None
    _status("Connecting to {0}...".format(st["room"]))
    _refresh_buttons()
    return True


def _ensure_devices():
    """The microphone and the speaker, opened once. A failure is said, and
    the room is still joined: listening works without a microphone."""
    st = state()
    if st["mic"] is None:
        try:
            from maya_voice import media
            mic = media.Mic()
            mic.start()
            st["mic"] = mic
        except Exception as exc:                       # noqa: BLE001
            st["mic"] = None
            _status("No microphone: {0}. You can listen.".format(exc))
    if st["speaker"] is None:
        try:
            from maya_voice import media
            speaker = media.Speaker()
            speaker.start()
            st["speaker"] = speaker
        except Exception as exc:                       # noqa: BLE001
            st["speaker"] = None
            _status("No audio output: {0}.".format(exc))


def _lost(reason):
    """The connection failed or dropped: keep the devices, schedule a retry."""
    st = state()
    sess = st["session"]
    st["session"] = None
    if sess is not None:
        sess.close()
    st["roster"].reset()
    st["jitter"] = {}
    st["frames"] = {}
    if not st["wanted"]:
        return _status(reason)
    step = RETRY_STEPS[min(st["retry"], len(RETRY_STEPS) - 1)]
    st["retry"] += 1
    st["retry_at"] = time.time() + step
    return _status("{0}. Reconnecting in {1} s.".format(reason, step))


def leave(quiet=False):
    """Leave the room and stop the devices, the timer and the viewer."""
    st = state()
    st["wanted"] = False
    st["retry_at"] = None
    st["sharing"] = False
    sess = st["session"]
    st["session"] = None
    if sess is not None:
        sess.close()
    for key in ("mic", "speaker"):
        dev = st[key]
        if dev is not None:
            try:
                dev.stop()
            except Exception:                          # noqa: BLE001
                pass
            st[key] = None
    st["pending"] = bytearray()
    st["jitter"] = {}
    st["frames"] = {}
    st["roster"].reset()
    st["roster_sig"] = None
    if st["viewer"] is not None:
        st["viewer"].close()
        st["viewer"] = None
    _stop_timer()
    _refresh_buttons()
    _show_roster()
    if not quiet:
        _status("Left the room.")


# ------------------------------------------------------------ controls

def toggle_mute(*_args):
    st = state()
    st["muted"] = not st["muted"]
    _push_state()
    _refresh_buttons()
    return _status("Microphone muted." if st["muted"]
                   else "Microphone on.")


def toggle_deafen(*_args):
    st = state()
    st["deafened"] = not st["deafened"]
    if st["deafened"]:
        st["jitter"] = {}
        st["next_play"] = None
    _push_state()
    _refresh_buttons()
    return _status("Deafened: you hear nobody." if st["deafened"]
                   else "You hear the room again.")


def toggle_share(*_args):
    st = state()
    if st["session"] is None:
        return _status("Join a room first.")
    if not st["sharing"]:
        try:
            from maya_voice import media
            media.grab_jpeg(max_width=320, quality=40)     # a test grab
        except Exception as exc:                       # noqa: BLE001
            return _status("Screen share refused: {0}".format(exc))
        st["sharing"] = True
        _status("Sharing the screen.")
    else:
        st["sharing"] = False
        _status("Screen share stopped.")
    _push_state()
    _refresh_buttons()
    return True


def view_screen(*_args):
    """Open the viewer on the first sharer (or the next one, on each press)."""
    st = state()
    sharers = st["roster"].sharers()
    if not sharers:
        return _status("Nobody is sharing.")
    if st["shown"] in sharers and len(sharers) > 1:
        index = sharers.index(st["shown"])
        st["shown"] = sharers[(index + 1) % len(sharers)]
    else:
        st["shown"] = sharers[0]
    st["shown_seq"] = None
    _ensure_viewer()
    name = st["roster"].members.get(st["shown"], {}).get("name", "")
    return _status("Showing the screen of {0}.".format(name))


def _ensure_viewer():
    st = state()
    if st["viewer"] is None:
        from maya_voice import media
        st["viewer"] = media.Viewer()
    return st["viewer"]


def _push_state():
    st = state()
    if st["session"] is not None:
        st["session"].send_state(st["muted"], st["deafened"], st["sharing"])


def _refresh_buttons():
    st = state()
    _label(MUTE_BUTTON, "Unmute" if st["muted"] else "Mute")
    _label(DEAFEN_BUTTON, "Undeafen" if st["deafened"] else "Deafen")
    _label(SHARE_BUTTON, "Stop sharing" if st["sharing"] else "Share screen")
    _label(JOIN_BUTTON, "Join" if st["session"] is None else "Switch")


def _label(control, text):
    try:
        cmds.button(control, edit=True, label=text)
    except RuntimeError:
        pass


# -------------------------------------------------------------- events

def _event(item):
    st = state()
    roster = st["roster"]
    kind = item[0]
    if kind == "control":
        change = roster.apply(item[1])
        if change == "welcome":
            _status("In {0} as {1}.".format(roster.room, st["name"]))
            st["retry"] = 0
        elif change == "error":
            _status(roster.error)
            if roster.error.startswith("room full"):
                st["wanted"] = False
                leave(quiet=True)
        if change in ("welcome", "roster"):
            _show_roster()
    elif kind == "media":
        _media(item)
    elif kind == "closed":
        _lost(str(item[1]))
    return None


def _media(item):
    st = state()
    _kind, sender, seq, data = item[1], item[2], item[3], item[4]
    if _kind == protocol.TYPE_AUDIO:
        st["roster"].heard(sender, time.time())
        if st["deafened"] or sender == st["roster"].me:
            return
        jb = st["jitter"].get(sender)
        if jb is None:
            jb = jittermod.JitterBuffer()
            st["jitter"][sender] = jb
        jb.push(seq, data)
    elif _kind == protocol.TYPE_VIDEO:
        if sender == st["roster"].me:
            return
        latest = st["frames"].get(sender)
        if latest is None:
            latest = jittermod.LatestFrame()
            st["frames"][sender] = latest
        latest.put(seq, data)


def _drain():
    st = state()
    sess = st["session"]
    if sess is not None:
        for item in sess.drain():
            _event(item)
    while True:
        try:
            lobby = st["lobby"].get_nowait()
        except queue.Empty:
            break
        st["lobby_busy"] = False
        if lobby[0] == "rooms":
            st["rooms"] = [r.get("room", "") for r in lobby[1]]
            _show_rooms(lobby[1])
        else:
            st["rooms_text"] = str(lobby[1])


# ---------------------------------------------------------- the pump

def _capture():
    """Microphone packets: gated, sent, numbered as they go."""
    st = state()
    mic = st["mic"]
    sess = st["session"]
    if mic is None or sess is None or st["muted"]:
        st["pending"] = bytearray()
        return
    st["pending"].extend(mic.read())
    size = protocol.PACKET_BYTES
    while len(st["pending"]) >= size:
        packet = bytes(st["pending"][:size])
        del st["pending"][:size]
        if st["gate"].feed(packet):
            sess.send_audio(st["seq"], packet)
            st["seq"] = (st["seq"] + 1) & 0xFFFFFFFF


def _play(now):
    """Playback on the packet clock: one mixed packet per 60 ms when due."""
    st = state()
    speaker = st["speaker"]
    if speaker is None or st["deafened"] or not st["jitter"]:
        st["next_play"] = None
        return
    if st["next_play"] is None:
        st["next_play"] = now
    while now >= st["next_play"]:
        chunks = []
        for jb in st["jitter"].values():
            due = jb.pop()
            if due is not None:
                chunks.append(due)
        if chunks and speaker.free() >= speaker.packet_size():
            speaker.write(jittermod.mix(chunks, protocol.PACKET_BYTES))
        st["next_play"] += PACKET_SECONDS
        if st["next_play"] < now - 0.2:
            st["next_play"] = now


def _share(now):
    st = state()
    if not st["sharing"] or st["session"] is None:
        return
    if now - st["screen_at"] < 1.0 / SCREEN_FPS:
        return
    st["screen_at"] = now
    try:
        from maya_voice import media
        data = media.grab_jpeg()
    except Exception as exc:                           # noqa: BLE001
        st["sharing"] = False
        _push_state()
        _refresh_buttons()
        _status("Screen share stopped: {0}".format(exc))
        return
    st["session"].send_video(st["video_seq"], data)
    st["video_seq"] = (st["video_seq"] + 1) & 0xFFFFFFFF


def _show_viewer(now):
    st = state()
    if st["shown"] is None or st["shown"] not in st["roster"].members:
        st["shown"] = None
        return
    latest = st["frames"].get(st["shown"])
    if latest is None or latest.seq == st["shown_seq"]:
        return
    data = latest.take()
    if not data:
        return
    viewer = _ensure_viewer()
    name = st["roster"].members.get(st["shown"], {}).get("name", "")
    if viewer.show_jpeg(data, name):
        st["shown_seq"] = latest.seq


def _roster_lines(now):
    st = state()
    roster = st["roster"]
    lines = []
    for mid in sorted(roster.members):
        lines.append(roster.label(mid, now))
    return lines


def _show_roster(now=None):
    st = state()
    now = time.time() if now is None else now
    lines = _roster_lines(now)
    sig = tuple(lines)
    if sig == st["roster_sig"]:
        return
    st["roster_sig"] = sig
    try:
        cmds.textScrollList(ROSTER_LIST, edit=True, removeAll=True)
        for line in lines:
            cmds.textScrollList(ROSTER_LIST, edit=True, append=line)
    except RuntimeError:
        pass


def _retry_due(now):
    st = state()
    if st["retry_at"] is not None and now >= st["retry_at"] \
            and st["wanted"] and st["session"] is None:
        st["retry_at"] = None
        _connect()


def pump():
    """One tick of the section, on the main thread. Never raises."""
    now = time.time()
    try:
        _drain()
        _retry_due(now)
        _capture()
        _play(now)
        _share(now)
        _show_viewer(now)
        _show_roster(now)
        refresh_lobby()
    except Exception:                                  # noqa: BLE001
        print(traceback.format_exc())
        _status("Voice failed a tick - see the Script Editor.")


def _tick():
    pump()


def _start_timer():
    st = state()
    if st["timer"] is not None:
        return
    from PySide6 import QtCore
    timer = QtCore.QTimer()
    timer.setInterval(PUMP_MS)
    timer.timeout.connect(_tick)
    timer.start()
    st["timer"] = timer


def _stop_timer():
    st = state()
    timer = st["timer"]
    if timer is not None and not st["wanted"]:
        timer.stop()
        st["timer"] = None


# --------------------------------------------------------------- the panel

def build_panel():
    """The section: server and name, the rooms, the room to join, the
    roster, the controls, one status line. Lists the rooms when it is built."""
    import maya_hubstyle as hubstyle
    name, server, room = remembered()
    st = state()
    st["name"] = name or st["name"]
    st["server"] = server or st["server"]
    cmds.columnLayout(adjustableColumn=True,
                      rowSpacing=hubstyle.row_spacing(6),
                      columnOffset=("both", hubstyle.pick(0, 8)))
    hubstyle.mark(cmds.text(SUBTITLE, label="Not connected", align="left"),
                  "subtitle")
    cmds.textField(NAME_FIELD, text=st["name"],
                   placeholderText="your name in the room",
                   height=hubstyle.height("field", 24),
                   annotation="The name the others see. Remembered.")
    cmds.textField(SERVER_FIELD, text=st["server"],
                   placeholderText="server: skeldar-voice.<name>.workers.dev",
                   height=hubstyle.height("field", 24),
                   annotation="The address of the voice server (the "
                              "Cloudflare worker from voice_server/).")
    hubstyle.mark(cmds.text(label="Rooms", align="left"), "note")
    cmds.textScrollList(ROOMS_LIST, allowMultiSelection=False,
                        height=LIST_HEIGHT,
                        selectCommand=lambda *_: _on_room_picked(),
                        doubleClickCommand=lambda *_: _run(join))
    cmds.rowLayout(numberOfColumns=3, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "both", 4),
                                 (3, "both", 4)])
    cmds.textField(ROOM_FIELD, text=room,
                   placeholderText="room name, e.g. layout-room",
                   height=hubstyle.height("field", 24))
    hubstyle.mark(cmds.button(
        JOIN_BUTTON, label="Join", height=hubstyle.height("button", 28),
        annotation="Join the room named in the field (or the one picked "
                   "above). Your microphone goes on.",
        command=lambda *_: _run(join)), "primary", "mic")
    hubstyle.mark(cmds.button(
        LEAVE_BUTTON, label="Leave", height=hubstyle.height("button", 28),
        annotation="Leave the room, and stop the microphone and the sound.",
        command=lambda *_: _run(lambda: leave())), "danger")
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=4, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "both", 4),
                                 (3, "both", 4), (4, "both", 4)])
    hubstyle.mark(cmds.button(
        MUTE_BUTTON, label="Mute", height=hubstyle.height("button", 28),
        annotation="Stop sending your microphone. The others hear silence.",
        command=lambda *_: _run(toggle_mute)), "secondary", "mic")
    hubstyle.mark(cmds.button(
        DEAFEN_BUTTON, label="Deafen", height=hubstyle.height("button", 28),
        annotation="Stop playing the room. You still send your voice.",
        command=lambda *_: _run(toggle_deafen)), "secondary", "mic")
    hubstyle.mark(cmds.button(
        SHARE_BUTTON, label="Share screen",
        height=hubstyle.height("button", 28),
        annotation="Send the primary screen to the room, about "
                   "{0} frames a second.".format(int(SCREEN_FPS)),
        command=lambda *_: _run(toggle_share)), "secondary", "screen")
    hubstyle.mark(cmds.button(
        VIEW_BUTTON, label="View", height=hubstyle.height("button", 28),
        annotation="Open the screen of the next sharer in a window.",
        command=lambda *_: _run(view_screen)), "secondary", "screen")
    cmds.setParent("..")
    hubstyle.mark(cmds.text(label="Room", align="left"), "note")
    cmds.textScrollList(ROSTER_LIST, allowMultiSelection=False,
                        height=LIST_HEIGHT)
    hubstyle.mark(cmds.text(STATUS, label=st["status"] or "",
                            align="left", wordWrap=True, height=36),
                  "status")
    cmds.setParent("..")
    _refresh_buttons()
    _show_roster()
    if st["rooms"]:
        _show_rooms([{"room": r, "members": []} for r in st["rooms"]])
    refresh_lobby(force=True)
    return None


def _run(action):
    try:
        return action()
    except Exception as exc:                           # noqa: BLE001
        print(traceback.format_exc())
        return _status("Voice failed: {0}".format(exc))


def is_open():
    return bool(cmds.textScrollList(ROSTER_LIST, exists=True))


def show_window():
    """The hub, on the Voice section."""
    import maya_hub
    return maya_hub.show(HUB_SECTION)
