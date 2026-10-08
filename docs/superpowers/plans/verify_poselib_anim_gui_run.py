"""The runner of verify_poselib_anim_gui.py inside a DISPOSABLE GUI Maya (2026-10-08).

Never sent to the animator's Maya: `verify_poselib_anim_gui_send.py` sends ONE line to the
disposable Maya's command port (7051 by default),

    exec(open(r"<this file>", encoding="utf-8").read(),
         {"__name__": "__main__", "__file__": r"<this file>", "PHASE": "...", "OUT": r"...",
          "PURGE": False})

and this file, run there, writes everything the phase prints into OUT and ends it with the line
`== END <phase> ==` the sender polls for (a stdout redirected into a file creates it at once -
bridge note 9). The command port runs one sent line TWICE (bridge note 5), so the first thing is
the marker `<OUT>.ran`; the second pass finds it and falls off the end - an `if`, never a
`raise SystemExit` (bridge note 8). `__file__` is passed in the globals: an exec'd text has none
of its own (trap 53).

The plugin is the one beside this script (`<repo>/SkeldarAnim`), put FIRST on `sys.path`.
`PURGE` (the first send, and after a fix of a plugin module) drops every module of ours from
`sys.modules` first (bridge note 9) - without it the window standing from an earlier send keeps
its module objects, which is what a phase after the first wants (trap 49). The verify itself is
loaded afresh from its file on every send (Maya keeps the first import of a module).
"""

import io
import os
import sys
import traceback

_OUT = globals().get("OUT")
_PHASE = globals().get("PHASE", "")
_MARK = (_OUT or "") + ".ran"
_HERE = os.path.dirname(os.path.abspath(globals().get("__file__") or "."))
_PLUGIN = os.path.normpath(os.path.join(_HERE, "..", "..", "..", "SkeldarAnim")).replace("\\", "/")

if _OUT and not os.path.exists(_MARK):
    with open(_MARK, "w") as _handle:
        _handle.write(_PHASE)
    _stream = io.open(_OUT, "w", encoding="utf-8", buffering=1)     # a line on disk at once
    _old = (sys.stdout, sys.stderr)
    sys.stdout = sys.stderr = _stream
    try:
        if _PLUGIN in sys.path:
            sys.path.remove(_PLUGIN)
        sys.path.insert(0, _PLUGIN)
        if globals().get("PURGE"):
            _gone = []
            for _name, _module in list(sys.modules.items()):
                _file = (getattr(_module, "__file__", None) or "").replace("\\", "/")
                if _file.startswith(_PLUGIN + "/"):
                    del sys.modules[_name]
                    _gone.append(_name)
            print("purged %d modules of the plugin" % len(_gone))
        import importlib.util
        _spec = importlib.util.spec_from_file_location(
            "verify_poselib_anim_gui", os.path.join(_HERE, "verify_poselib_anim_gui.py"))
        _verify = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_verify)
        _verify.run(_PHASE)
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
    finally:
        print("== END %s ==" % _PHASE)
        sys.stdout, sys.stderr = _old
        _stream.close()
