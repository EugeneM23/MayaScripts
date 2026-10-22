"""The chat's notifications: the rail badge, a viewport message, a sound (a chime, on by default).

Listens to the session (one listener a Maya, kept on sys - trap 111).
"""
import sys
import traceback

from . import look

OPTIONS = {"viewport": ("skeldarChatNotifyViewport", True),
           "sound": ("skeldarChatNotifySound", True)}
RING_GAP = 1.5      # s: a burst of messages rings once
_VARS = {}
PREVIEW = 80


def _cmds():
    try:
        from maya import cmds
        cmds.optionVar(exists=OPTIONS["viewport"][0])
        return cmds
    except Exception:                                        # noqa: BLE001
        return None


def option(what):
    name, default = OPTIONS[what]
    cmds = _cmds()
    if cmds is not None:
        try:
            if cmds.optionVar(exists=name):
                return bool(cmds.optionVar(query=name))
            return default
        except Exception:                                    # noqa: BLE001
            pass
    return bool(_VARS.get(name, default))


def set_option(what, on):
    name = OPTIONS[what][0]
    cmds = _cmds()
    if cmds is not None:
        try:
            cmds.optionVar(intValue=(name, 1 if on else 0))
            return bool(on)
        except Exception:                                    # noqa: BLE001
            pass
    _VARS[name] = bool(on)
    return bool(on)


def unread(session):
    return look.total_unread(session.state.chats.values())


def paint(session):
    """The rail icon's count."""
    n = unread(session)
    try:
        import maya_hub
        maya_hub.paint_badge("chat", n)
    except Exception:                                        # noqa: BLE001
        pass
    return n


def _seen(chat_id):
    """Whether the animator is looking at this chat now."""
    try:
        from . import window
        win = window.window()
        return bool(win is not None and win.root.isVisible() and win.chat == chat_id
                    and win.root.isActiveWindow())
    except Exception:                                        # noqa: BLE001
        return False


def sender(session, message):
    c = session.state.chats.get(message.get("chat")) or {}
    return next((u for u in c.get("members", []) if u.get("id") == message.get("from_id")),
                {"id": message.get("from_id"), "nick": "?"})


def message_text(session, message):
    c = session.state.chats.get(message["chat"]) or {}
    who = next((m for m in c.get("members", []) if m.get("id") == message.get("from_id")),
               {"nick": "?"})
    text = look.message_text(message)
    if len(text) > PREVIEW:
        text = text[:PREVIEW - 1] + "…"
    head = look.display_name(who)
    if c.get("kind") == "group":
        head = "{0} · {1}".format(head, c.get("name") or "")
    return head, text


def say(head, text, message=None, user=None):
    """A card at the viewport's bottom-left above the Time Bar (toast.py); where Qt cannot
    stand, Maya's own inViewMessage there."""
    try:
        from . import toast
        if toast.show((message or {}).get("chat"), user or {"nick": "?"}, head, text) is not None:
            return True
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
    cmds = _cmds()
    if cmds is None:
        return False
    try:
        safe = lambda t: t.replace("<", "&lt;").replace(">", "&gt;")  # noqa: E731
        cmds.inViewMessage(assistMessage="<hl>{0}</hl>  {1}".format(safe(head), safe(text)),
                           position="botLeft", fade=True, fadeStayTime=3500)
        return True
    except Exception:                                        # noqa: BLE001
        return False


def ring(now=None):
    """The message chime (assets/sounds/message.wav), whatever the hub's interface sounds say;
    not again within RING_GAP."""
    import time
    now = time.monotonic() if now is None else now
    last = getattr(sys, "_skeldar_chat_rang", None)
    if last is not None and now - last < RING_GAP:
        return False
    try:
        import maya_hubsound
        played = bool(maya_hubsound.play("message", force=True))
    except Exception:                                        # noqa: BLE001
        return False
    if played:
        sys._skeldar_chat_rang = now
    return played


def _rings():
    """{call id: ring handle (or None)} for the calls ringing here, kept on sys (trap 111)."""
    held = getattr(sys, "_skeldar_chat_rings", None)
    if not isinstance(held, dict):
        held = {}
        sys._skeldar_chat_rings = held
    return held


def _loop_ring():
    """The looped ring, whatever the interface-sounds switch says; None when it cannot play."""
    try:
        import maya_hubsound
        return maya_hubsound.loop("ring", force=True)
    except Exception:                                        # noqa: BLE001
        return None


def _now_ms():
    import time
    return int(time.time() * 1000)


def _user(session, uid):
    for c in session.state.chats.values():
        for m in c.get("members", []):
            if m.get("id") == uid:
                return m
    for m in session.state.people or []:
        if m.get("id") == uid:
            return m
    return None


def _gone(call_id):
    """Stop the ring and take the card away."""
    handle = _rings().pop(call_id, None)
    if handle is not None:
        try:
            handle.stop()
        except Exception:                                    # noqa: BLE001
            pass
    try:
        from . import toast
        toast.dismiss_call(call_id)
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()


def _stop_after(call_id, seconds):
    """The ring gives up after `seconds` (a single-shot timer, where Qt is)."""
    try:
        from PySide6 import QtCore
        QtCore.QTimer.singleShot(int(seconds * 1000), lambda: _gone(call_id))
    except Exception:                                        # noqa: BLE001
        pass


def _heard_call(session, data, out):
    from . import calls as _calls, toast
    view = (data or {}).get("call") or {}
    cid = view.get("id")
    me = (session.state.me or {}).get("id")
    ringing = {c["id"] for c in _calls.ringing_for(session.state.calls, me, _now_ms())}
    held = _rings()
    if cid in ringing and cid not in held:
        caller = _user(session, view.get("by"))
        head = look.display_name(caller) if caller else "Звонок"
        held[cid] = None
        try:
            toast.show_call(view, caller or {"nick": "?"}, head)
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()
        held[cid] = _loop_ring()
        _stop_after(cid, _calls.RING_S)
        out.append(("call_card", cid))
    elif cid in held and cid not in ringing:
        _gone(cid)
        out.append(("call_gone", cid))


def heard(session, kind, data, out=None):
    """What a session event does: returns the list of things done (for the tests)."""
    done = [] if out is None else out
    if kind == "call":
        _heard_call(session, data, done)
        return done
    if kind in ("message", "read", "read_local", "resync", "chat", "member_removed", "status"):
        done.append(("badge", paint(session)))
    if kind != "message" or not data:
        return done
    m = data.get("message") or {}
    me = (session.state.me or {}).get("id")
    if m.get("from_id") == me or _seen(m.get("chat")):
        return done
    head, text = message_text(session, m)
    if option("viewport") and say(head, text, m, sender(session, m)):
        done.append(("viewport", head, text))
    if option("sound") and ring():
        done.append(("sound",))
    return done


def install(session):
    """One listener a Maya: the old one (an older module's) taken off first."""
    old = getattr(sys, "_skeldar_chat_notify", None)
    if old is not None:
        try:
            old[0].unlisten(old[1])
        except Exception:                                    # noqa: BLE001
            pass

    def listener(kind, data):
        try:
            heard(session, kind, data)
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()

    session.listen(listener)
    sys._skeldar_chat_notify = (session, listener)
    paint(session)
    return listener
