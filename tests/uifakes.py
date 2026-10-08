"""A recording `maya.cmds` for the `cmds`-only panels' `show_window`.

Every UI command is accepted, creations are counted as children of the one
open column, and control heights are whatever the test says they are -
Maya scales them for the display, so the code under test may never assume
a number. `dpi` is what `mayaDpiSetting -q -realScaleValue` answers.
"""


class FakeUiCmds(object):

    #  What a panel creates in its column. Anything else `cmds` is asked
    #  for (ls, objExists inside a refresh) is not a control.
    UI = ("text", "separator", "rowLayout", "optionMenu", "checkBox",
          "floatSliderGrp", "colorSliderGrp", "button", "intField",
          "floatField", "radioButtonGrp", "frameLayout", "formLayout",
          "textScrollList", "textField", "textFieldGrp", "floatFieldGrp",
          "scrollLayout", "iconTextRadioButton")

    def __init__(self, control_height=25, saved_pref=True, dpi=1.0):
        self.control_height = control_height
        self.saved_pref = saved_pref
        self.dpi = dpi
        self.windows = {}
        self.children = []
        self.calls = []
        self.column = {}
        self.selection = []
        #  The hub: workspaceControl name -> its creation kwargs plus the
        #  edits made to it, frameLayout name -> its kwargs (collapse read
        #  back by the tests), optionVars written, deferred callables.
        self.workspace = {}
        self.frames = {}
        self.optionvars = {}
        self.deferred = []
        self.existing = set()
        self.deleted = []

    def _record(self, name):
        def call(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            if kwargs.get("query") or kwargs.get("q"):
                if kwargs.get("childArray"):
                    return list(self.children)
                if kwargs.get("height"):
                    return self.control_height
                if kwargs.get("value"):
                    return 1.0
                if kwargs.get("rgbValue"):
                    return [0.5, 0.5, 0.5]
                if kwargs.get("exists"):
                    return False
                if kwargs.get("selection"):
                    return list(self.selection)
                return None
            if kwargs.get("edit") or kwargs.get("e"):
                return None
            if kwargs.get("exists"):
                return False
            if name in self.UI:
                label = args[0] if args else "%s%d" % (name,
                                                       len(self.children))
                self.children.append(label)
                return label
            return [] if name == "ls" else None
        return call

    def window(self, name, **kwargs):
        if kwargs.get("exists"):
            return name in self.windows
        if kwargs.get("query") or kwargs.get("q"):
            return self.windows[name].get(
                [k for k in kwargs if k not in ("query", "q")][0])
        if kwargs.get("edit") or kwargs.get("e"):
            for k, v in kwargs.items():
                if k not in ("edit", "e"):
                    self.windows[name][k] = v
            return name
        self.windows[name] = dict(kwargs)
        return name

    def windowPref(self, name, **kwargs):
        self.calls.append(("windowPref", (name,), kwargs))
        if kwargs.get("exists"):
            return self.saved_pref
        if kwargs.get("remove"):
            self.saved_pref = False
        return None

    def mayaDpiSetting(self, **kwargs):
        if kwargs.get("realScaleValue"):
            return self.dpi
        return 1.0

    def columnLayout(self, *args, **kwargs):
        self.calls.append(("columnLayout", args, kwargs))
        if kwargs.get("query") or kwargs.get("q"):
            if kwargs.get("childArray"):
                return list(self.children)
            return self.control_height
        self.column = kwargs
        return "fakeWin|columnLayout1"

    def optionVar(self, **kwargs):
        if kwargs.get("exists"):
            return kwargs["exists"] in self.optionvars
        if kwargs.get("query") or kwargs.get("q"):
            return self.optionvars.get(kwargs.get("query") or kwargs.get("q"))
        for flag in ("intValue", "floatValue", "stringValue"):
            if flag in kwargs:
                name, value = kwargs[flag]
                self.optionvars[name] = value
        return None

    def workspaceControl(self, name, **kwargs):
        self.calls.append(("workspaceControl", (name,), kwargs))
        if kwargs.get("exists"):
            return name in self.workspace
        if kwargs.get("query") or kwargs.get("q"):
            return self.workspace[name].get(
                [k for k in kwargs if k not in ("query", "q")][0])
        if kwargs.get("edit") or kwargs.get("e"):
            self.workspace[name].setdefault("edits", []).append(kwargs)
            return name
        self.workspace[name] = dict(kwargs)
        return name

    def frameLayout(self, name=None, **kwargs):
        self.calls.append(("frameLayout", (name,), kwargs))
        if kwargs.get("exists"):
            return name in self.frames
        if kwargs.get("query") or kwargs.get("q"):
            return self.frames[name].get(
                [k for k in kwargs if k not in ("query", "q")][0])
        if kwargs.get("edit") or kwargs.get("e"):
            for k, v in kwargs.items():
                if k not in ("edit", "e"):
                    self.frames[name][k] = v
            return name
        self.frames[name] = dict(kwargs)
        self.children.append(name)
        return name

    def scrollLayout(self, name=None, **kwargs):
        self.calls.append(("scrollLayout", (name,), kwargs))
        if kwargs.get("exists"):
            return name in self.existing
        if kwargs.get("query") or kwargs.get("q") or kwargs.get("edit")                 or kwargs.get("e"):
            return None
        self.existing.add(name)
        return name

    def evalDeferred(self, fn, **kwargs):
        self.deferred.append(fn)
        return None

    def control(self, name, **kwargs):
        self.calls.append(("control", (name,), kwargs))
        if kwargs.get("exists"):
            return name in self.existing or name in self.frames                 or name in self.children
        if kwargs.get("query") and kwargs.get("height"):
            return self.control_height
        return None

    def deleteUI(self, name, **kwargs):
        self.deleted.append(name)
        return None

    def setParent(self, *args, **kwargs):
        self.calls.append(("setParent", args, kwargs))
        return args[0] if args else None

    def run_deferred(self):
        """Fire what evalDeferred queued, in order."""
        queued, self.deferred = self.deferred, []
        for fn in queued:
            fn()

    def __getattr__(self, name):
        return self._record(name)

    #  --- what the tests read back ---

    def removed_prefs(self):
        return [c for c in self.calls
                if c[0] == "windowPref" and c[2].get("remove")]


#  --- reading the arrangement back (2026-10-08, the compact hub) ---

#  What opens a layout that a later setParent("..") closes.
LAYOUTS = ("rowLayout", "flowLayout", "columnLayout", "formLayout",
           "frameLayout", "scrollLayout")


def is_creation(call):
    """A recorded call that MADE something (no edit, query or exists flag)."""
    kwargs = call[2]
    return not (kwargs.get("edit") or kwargs.get("e") or kwargs.get("query")
                or kwargs.get("q") or kwargs.get("exists"))


def made(fake, kind, **match):
    """[(position, call)] of the creations of `kind` whose kwargs hold
    `match`, in the order the fake recorded them."""
    return [(i, c) for i, c in enumerate(fake.calls)
            if c[0] == kind and is_creation(c)
            and all(c[2].get(k) == v for k, v in match.items())]


def inside(fake, start):
    """The calls between the layout created at position `start` and the
    setParent("..") that closes it, nested layouts included."""
    depth, out = 1, []
    for call in fake.calls[start + 1:]:
        if call[0] in LAYOUTS and is_creation(call):
            depth += 1
        elif call[0] == "setParent" and call[1] == ("..",):
            depth -= 1
            if not depth:
                return out
        out.append(call)
    return out
