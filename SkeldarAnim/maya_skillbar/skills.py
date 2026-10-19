"""The skill bar's road from the strip (2026-10-19): what the grid asks, in Maya (`MayaSkills`) or in
memory (`MemorySkills`, the strip's tests and a fake link). No Qt."""

import traceback

from . import look


class MemorySkills(object):
    """The model in memory; runs recorded, nothing opened."""

    def __init__(self, data=None):
        self._data = look.normalised(data) if data is not None else look.defaults()
        self._page = look.TIME_PAGE
        self.log = []
        self.waiting_items = []

    def data(self):
        return self._data

    def set_data(self, data):
        self._data = look.normalised(data)
        return self._data

    def page(self):
        return self._page

    def set_page(self, n):
        if n == look.TIME_PAGE or look.is_skill_page(n):
            self._page = n
        return self._page

    def run(self, item, point):
        self.log.append(("run", item, point))
        return "ran %s" % self.label(item)

    def label(self, item):
        if not item:
            return ""
        return item.get("label") or item.get("key") or item.get("command") or item.get("model") \
            or item.get("path") or look.script_label(item.get("code", ""))

    def tip(self, item):
        return self.label(item) if item else "Empty - click for the skill library"

    def tag(self, item):
        return ""

    def short(self, item):
        return self.label(item)[:9] if item else ""

    def picture(self, item):
        return ("text", look.initials(self.label(item))) if item else None

    def waiting(self, item):
        return any(look.same_item(item, w) for w in self.waiting_items)

    def script_editor(self):
        self.log.append(("script_editor",))
        return None

    def open_library(self, target, point):
        self.log.append(("library", target, point))

    def say(self, message):
        self.log.append(("say", message))

    def scene_drag(self, item):
        """A skill dragged off the bar: a recording stand-in for run.SceneDrag."""
        log = self.log

        class Drag(object):
            def active(self):
                return bool(item) and look.valid_item(item)

            def caption(self, gx, gy):
                return ("%s · floor" % item.get("model", "?"), True) if self.active() else ("nothing", False)

            def drop(self, gx, gy, say=None):
                log.append(("scene_drop", item, (gx, gy)))
                return "dropped" if self.active() else ""

            def end(self):
                log.append(("scene_end",))
        return Drag()


class MayaSkills(object):
    """The real thing: the model in the user's file, the runs through `run`."""

    def __init__(self):
        import maya_skillbar
        from . import run
        self._bar, self._run = maya_skillbar, run

    def data(self):
        return self._bar.data()

    def set_data(self, data):
        return self._bar.set_data(data)

    def page(self):
        return self._bar.current_page()

    def set_page(self, n):
        return self._bar.set_current_page(n)

    def run(self, item, point):
        return self._run.run(item, point)

    def label(self, item):
        return self._run.label(item)

    def tip(self, item):
        return self._run.tip(item)

    def tag(self, item):
        return self._run.tag(item)

    def short(self, item):
        return self._run.short(item)

    def picture(self, item):
        return self._run.picture(item)

    def waiting(self, item):
        return self._run.waiting(item)

    def script_editor(self):
        text, lang = self._run.script_editor_text()
        return look.script_item(text, lang)

    def open_library(self, target, point):
        try:
            from . import library
            library.show(target, point)
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()

    def scene_drag(self, item):
        return self._run.SceneDrag(item)

    def say(self, message):
        if not message:
            return
        try:
            import maya.cmds as cmds
            cmds.inViewMessage(assistMessage=message, position="botCenter", fade=True)
        except Exception:                                    # noqa: BLE001
            pass
