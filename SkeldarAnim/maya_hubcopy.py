"""maya_hubcopy - a second, independent copy of a section's controls.

2026-10-09 (the animator: «для каждого из наших разделов сделать кнопочку ...
которая открывает копию раздела в окне вьюпорта»; B, a true copy). Spec:
docs/superpowers/specs/2026-10-09-hub-section-popups-design.md.

A `cmds` control has ONE name per Maya session, and every section builds its
controls under constant names (`_STATUS = "mayaSceneSetupStatus"`) that its
callbacks name again. So a second build of a section would clash with the
first, and a callback of the copy would write the hub's line. A copy is
therefore built, and its callbacks run, inside a SCOPE:

- while a scope is entered, a creation command (CREATORS, no q/e flag) gets
  its first name prefixed with the scope's tag, and the name Maya made is
  recorded under the name the module knows it by;
- any other call maps the names it carries through the scope's record - a
  name the scope did not make passes through unchanged, so a copy can still
  reach a hub control the way a hub callback always could;
- a callable handed to a command (`command=`, a scriptJob, evalDeferred) is
  wrapped so it runs inside the scope that made it, whenever it fires;
- a scriptJob made inside a scope is recorded there and killed by `close()`.

Outside any scope nothing changes: `install()` wraps every function of
`maya.cmds` once (a module attribute swap; measured 2026-10-09 in mayapy - the
wrapper ran and answered), and each wrapper is a pass-through while no scope
is entered.

Qt-side lookups by name (`maya_hubqt.find`) go through `resolve()`, and every
Python callback a builder hands to a Qt object of ours goes through `wrap()`.
An object a Qt event calls (a grid's scene, a list drag's scene, an inventory's
scene) is `bind()`-ed: its methods run in the scope, whichever event calls them
(2026-10-09).

The scope stack and the registry live on `sys` (trap 111: an install purges
our modules; a copy outlives them, and its callbacks must find the stack
that a newer module object of this file entered).

Stdlib only at import - the names, the rules and the stack are testable with
a fake `cmds`. `install()` imports `maya.cmds` itself, or takes one.
"""

import contextlib
import functools
import sys
import types

#  The UI commands that make a control. Their first argument names it (or a
#  `name=` flag does). Anything not listed is never renamed - scene nodes
#  such as attributeQuery(MARKER) or shadingNode(SHADER) keep their names.
CREATORS = frozenset((
    "button", "checkBox", "columnLayout", "rowLayout", "frameLayout",
    "scrollLayout", "formLayout", "tabLayout", "gridLayout", "paneLayout",
    "text", "textField", "textFieldButtonGrp", "textFieldGrp",
    "textScrollList", "optionMenu", "menu", "menuItem", "popupMenu",
    "intField", "floatField", "intFieldGrp", "floatFieldGrp",
    "intSliderGrp", "floatSliderGrp", "colorSliderGrp", "colorSlider",
    "intSlider", "floatSlider", "iconTextButton", "iconTextCheckBox",
    "iconTextRadioButton", "iconTextRadioCollection", "radioButton",
    "radioCollection", "separator", "symbolButton", "image", "canvas",
    "scriptTable", "draggerContext", "attrControlGrp", "attrFieldSliderGrp",
    "attrColorSliderGrp", "helpLine", "iconTextScrollList",
    "toolCollection", "hardwareRenderPanel",
))

#  flags that make a call a query or an edit, not a creation
_QE_FLAGS = ("q", "query", "e", "edit")

_STATE_ATTR = "_skeldar_hubcopy"


def _state():
    """The shared state on `sys`: the stack of entered scopes, the counter
    that tags new scopes, the live scopes by tag, and whether the commands
    are wrapped (`install`)."""
    st = getattr(sys, _STATE_ATTR, None)
    if st is None:
        st = {"stack": [], "counter": 0, "scopes": {}, "installed": False}
        setattr(sys, _STATE_ATTR, st)
    return st


# ----------------------------------------------------------------- scopes

class Scope(object):
    """The names one copy made, and the scriptJobs it made.

    `names` maps the name a module knows a control by to the name Maya made
    it as (the full path a creation answers). `section` is the hub section
    the copy is of (`instances()` finds a section's copies by it)."""

    def __init__(self, tag, section=None, serial=0):
        self.tag = tag
        self.prefix = tag + "_"
        self.section = section
        self.serial = serial
        self.names = {}
        self.jobs = []
        self.alive = True

    def resolve(self, name):
        """The name this scope's control `name` answers to, or `name`."""
        return _map(name, self.names)

    def wrap(self, fn):
        """`fn`, made to run inside this scope (see `wrap`)."""
        return _wrap_in(self, fn)

    def call(self, command, real, args, kwargs):
        """One call of `command` while this scope is entered: the real
        command, with its names and callbacks put in this scope."""
        base = _creation_name(command, args, kwargs)
        if base is not None:
            return self._create(base, real, args, kwargs)
        args = tuple(self._prepare(a) for a in args)
        kwargs = dict((k, self._prepare(v)) for k, v in kwargs.items())
        result = real(*args, **kwargs)
        if command == "scriptJob" and isinstance(result, int):
            self.jobs.append(result)
        return result

    def _create(self, base, real, args, kwargs):
        made = base if base.startswith(self.prefix) else self.prefix + base
        if args and args[0] == base:
            args = (made,) + tuple(args[1:])
        else:
            kwargs = dict(kwargs, name=made)
        args = tuple(self._prepare(a) for a in args)
        kwargs = dict((k, self._prepare(v)) for k, v in kwargs.items())
        result = real(*args, **kwargs)
        if isinstance(result, str) and not base.startswith(self.prefix):
            self.names[base] = result
        return result

    def _prepare(self, value):
        """A value on its way into a command: names mapped (lists and tuples
        inside too), callables made to run in this scope."""
        if isinstance(value, str):
            return self.names.get(value, value)
        if isinstance(value, list):
            return [self._prepare(v) for v in value]
        if isinstance(value, tuple):
            return tuple(self._prepare(v) for v in value)
        if callable(value) and not isinstance(value, type):
            return _wrap_in(self, value)
        return value


def _creation_name(command, args, kwargs):
    """The name a creation call makes, or None for any other call."""
    if command not in CREATORS:
        return None
    if any(kwargs.get(flag) for flag in _QE_FLAGS):
        return None
    if args and isinstance(args[0], str) and args[0]:
        return args[0]
    if isinstance(kwargs.get("name"), str) and kwargs["name"]:
        return kwargs["name"]
    return None


def _map(value, names):
    """`value` with every string that `names` knows replaced; lists and
    tuples mapped inside. Pure."""
    if isinstance(value, str):
        return names.get(value, value)
    if isinstance(value, list):
        return [_map(v, names) for v in value]
    if isinstance(value, tuple):
        return tuple(_map(v, names) for v in value)
    return value


def new_scope(section=None):
    """A fresh scope, registered (live until `close`)."""
    st = _state()
    st["counter"] += 1
    tag = "hubcopy{0}".format(st["counter"])
    scope = Scope(tag, section, serial=st["counter"])
    st["scopes"][tag] = scope
    return scope


def current():
    """The innermost scope entered, or None (the hub's own names)."""
    stack = _state()["stack"]
    return stack[-1] if stack else None


@contextlib.contextmanager
def entered(scope):
    """Run the block with `scope` current. The scope is None-safe: entering
    None runs the block with the hub's names, as it always did."""
    stack = _state()["stack"]
    stack.append(scope)
    try:
        yield scope
    finally:
        stack.pop()


def _wrap_in(scope, fn):
    """`fn` made to run inside `scope`. A callable already made for a scope
    keeps it; with no scope it is `fn` itself."""
    if scope is None or getattr(fn, "_skeldar_scope", None) is not None:
        return fn

    @functools.wraps(fn)
    def run(*args, **kwargs):
        with entered(scope):
            return fn(*args, **kwargs)

    run._skeldar_scope = scope
    return run


def wrap(fn):
    """`fn` made to run inside the scope current NOW, whenever it is called
    (a Python callback handed to a Qt object of ours). With no scope current,
    `fn` itself."""
    return _wrap_in(current(), fn)


class Bound(object):
    """An object whose methods run inside one scope (2026-10-09): a Qt event
    calls them - a drag, a click - and no cmds command is on the way to put
    them in the copy. A method of a closed copy runs nothing: its names are
    gone, and a call would reach the hub's controls. Attributes read and write
    through as they are."""

    def __init__(self, obj, scope):
        object.__setattr__(self, "_obj", obj)
        object.__setattr__(self, "_scope", scope)

    def __getattr__(self, name):
        attr = getattr(self._obj, name)
        if not callable(attr) or isinstance(attr, type):
            return attr
        scope = self._scope

        @functools.wraps(attr)
        def call(*args, **kwargs):
            if not scope.alive:
                return None
            with entered(scope):
                return attr(*args, **kwargs)
        return call

    def __setattr__(self, name, value):
        setattr(self._obj, name, value)


def bind(obj):
    """`obj` with its methods run in the scope current NOW (a `Bound`), or
    `obj` itself with no scope current."""
    scope = current()
    if scope is None:
        return obj
    return Bound(obj, scope)


def resolve(name):
    """The name a copy's control is made as, when a scope is current - for
    a Qt lookup by name (maya_hubqt.find). Otherwise `name` itself."""
    scope = current()
    if scope is None:
        return name
    return scope.resolve(name)


def instances(section):
    """The live copies of hub section `section`, oldest first."""
    return [scope for scope in live() if scope.section == section]


def live():
    """Every live copy, oldest first (the section ones and any other)."""
    scopes = _state()["scopes"]
    return sorted((s for s in scopes.values() if s.alive),
                  key=lambda s: s.serial)


def close(scope, cmds=None):
    """The copy is gone: its scriptJobs killed, its names forgotten and its
    tag dropped from the registry. Idempotent. Each step on its own - a job
    Maya no longer knows must not stop the rest. `cmds` is the module to kill
    the jobs with (maya.cmds when None)."""
    if scope is None or not scope.alive:
        return 0
    scope.alive = False
    killed = 0
    if cmds is None:
        import maya.cmds as cmds
    for job in scope.jobs:
        try:
            cmds.scriptJob(kill=job, force=True)
            killed += 1
        except Exception:                                    # noqa: BLE001
            pass
    scope.jobs = []
    scope.names = {}
    _state()["scopes"].pop(scope.tag, None)
    return killed


# --------------------------------------------------------- the cmds wrapper

def _is_command(value):
    """A function of maya.cmds (not a module, class or constant)."""
    if isinstance(value, (type, types.ModuleType)):
        return False
    return callable(value)


def _command_wrapper(command, real):
    """`real`, wrapped so a call made while a scope is current is put in it."""

    @functools.wraps(real)
    def command_fn(*args, **kwargs):
        scope = current()
        if scope is None:
            return real(*args, **kwargs)
        return scope.call(command, real, args, kwargs)

    command_fn._skeldar_real = real
    return command_fn


def install(cmds=None):
    """Wrap every command of `maya.cmds` (once per session: a wrapper keeps the
    real function it wraps, so a later install rewraps the real ones with its
    own code). Returns how many commands it wrapped. Never raises for one
    command."""
    if cmds is None:
        import maya.cmds as cmds
    count = 0
    for name in dir(cmds):
        if name.startswith("_"):
            continue
        try:
            value = getattr(cmds, name)
        except Exception:                                    # noqa: BLE001
            continue
        if not _is_command(value):
            continue
        real = getattr(value, "_skeldar_real", value)
        try:
            setattr(cmds, name, _command_wrapper(name, real))
            count += 1
        except Exception:                                    # noqa: BLE001
            pass
    _state()["installed"] = True
    return count


def installed():
    return bool(_state()["installed"])
