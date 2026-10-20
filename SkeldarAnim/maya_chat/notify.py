"""The chat's notifications: the rail badge, a viewport message, a sound (off by default).

Listens to the session (one listener a Maya, kept on sys - trap 111).
"""
import sys
import traceback

from . import look

OPTIONS = {"viewport": ("skeldarChatNotifyViewport", True),
           "sound": ("skeldarChatNotifySound", False)}
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


def message_text(session, message):
    c = session.state.chats.get(message["chat"]) or {}
    who = next((m for m in c.get("members", []) if m.get("id") == message.get("from_id")),
               {"nick": "?"})
    text = " ".join(str(message.get("text") or "").split())
    if len(text) > PREVIEW:
        text = text[:PREVIEW - 1] + "…"
    head = look.display_name(who)
    if c.get("kind") == "group":
        head = "{0} · {1}".format(head, c.get("name") or "")
    return head, text


def say(head, text):
    """A viewport message (Maya's own inViewMessage)."""
    cmds = _cmds()
    if cmds is None:
        return False
    try:
        safe = lambda t: t.replace("<", "&lt;").replace(">", "&gt;")  # noqa: E731
        cmds.inViewMessage(assistMessage="<hl>{0}</hl>  {1}".format(safe(head), safe(text)),
                           position="topRight", fade=True, fadeStayTime=3500)
        return True
    except Exception:                                        # noqa: BLE001
        return False


def ring():
    try:
        import maya_hubsound
        return bool(maya_hubsound.play("hover"))
    except Exception:                                        # noqa: BLE001
        return False


def heard(session, kind, data, out=None):
    """What a session event does: returns the list of things done (for the tests)."""
    done = [] if out is None else out
    if kind in ("message", "read", "read_local", "resync", "chat", "member_removed", "status"):
        done.append(("badge", paint(session)))
    if kind != "message" or not data:
        return done
    m = data.get("message") or {}
    me = (session.state.me or {}).get("id")
    if m.get("from_id") == me or _seen(m.get("chat")):
        return done
    head, text = message_text(session, m)
    if option("viewport") and say(head, text):
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
