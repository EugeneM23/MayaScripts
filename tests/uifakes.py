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
          "floatField", "radioButtonGrp", "frameLayout")

    def __init__(self, control_height=25, saved_pref=True, dpi=1.0):
        self.control_height = control_height
        self.saved_pref = saved_pref
        self.dpi = dpi
        self.windows = {}
        self.children = []
        self.calls = []
        self.column = {}
        self.selection = []

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
            return False
        return None

    def __getattr__(self, name):
        return self._record(name)

    #  --- what the tests read back ---

    def removed_prefs(self):
        return [c for c in self.calls
                if c[0] == "windowPref" and c[2].get("remove")]
