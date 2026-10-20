"""The messenger inside Maya (spec docs/superpowers/specs/2026-10-19-chat-messenger-design.md).

Imports nothing heavy: the session and the window are loaded when asked for.
"""
import sys

# The chat server, production since 2026-10-20 (staging is skeldar-chat-staging); the
# optionVar skeldarChatServer overrides it.
SERVER = "https://skeldar-chat.skeldar.workers.dev"
OPTION = "skeldarChatServer"


def server():
    try:
        from maya import cmds
        if cmds.optionVar(exists=OPTION):
            value = str(cmds.optionVar(query=OPTION) or "").strip()
            if value.startswith("https://") or value.startswith("http://"):
                return value.rstrip("/")
    except Exception:
        pass
    return SERVER


def show(origin=None):
    """The chat window up, out of the global point `origin` (the rail icon)."""
    from . import window
    win = window.show(origin)
    _notify()
    return win


def toggle(origin=None):
    """A rail press: the window out of the icon, or back into it."""
    from . import window
    done = window.toggle(origin)
    _notify()
    return done


def ensure():
    """At Maya's start (the hub's build, deferred): with a token on disk the session connects
    at once, so the rail shows the unread count before the window was ever opened."""
    from . import session as _session
    from . import store as _store
    url = server()
    if getattr(sys, "_skeldar_chat", None) is None:
        if not _store.Store.for_server(_session._base(), url).token():
            return False
    _notify()
    return True


def _notify():
    from . import notify
    notify.install(current())


def current():
    """The one session of this Maya (made on first use). Not called session(): a function of that
    name would shadow the submodule for `from maya_chat import session`."""
    from . import session as _session
    return _session.get()
