"""The messenger inside Maya (spec docs/superpowers/specs/2026-10-19-chat-messenger-design.md).

Imports nothing heavy: the session and the window are loaded when asked for.
"""

# The chat server. Staging until the production Worker exists (plan 3); the optionVar
# skeldarChatServer overrides it.
SERVER = "https://skeldar-chat-staging.skeldar.workers.dev"
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


def current():
    """The one session of this Maya (made on first use). Not called session(): a function of that
    name would shadow the submodule for `from maya_chat import session`."""
    from . import session as _session
    return _session.get()
