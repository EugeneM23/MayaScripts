"""maya_filedrag - rows of Stash and Shared dragged between them and into the scene.

2026-10-21, the animator: «драг энд дроп того что находится в сташе и в шаре
между этими папками и на сцену, при драге на сцену это означает что мы делаем
экспорт в сцену». Asked: a viewport is Import as the card's button; Stash ->
Shared sends with no question; every picked row travels.

- a viewport: Import (`maya_stash.drop_import` / `maya_share.drop_import`);
- Stash -> Shared: Send file, each its own name (`maya_stash.drop_to_share`);
- Shared -> Stash: a copy into the stash (`maya_share.drop_to_stash`), a file
  not downloaded yet fetched first;
- a section is its list (the hub's card or a popup copy) or its rail icon.

The drag itself is the UE Bridge list's (`maya_uebridge.listdrag`), handed a
`FileScene`. Nothing here imports Maya or Qt at import time.

Spec: docs/superpowers/specs/2026-10-21-stash-shared-drag-design.md
"""

import collections

Item = collections.namedtuple("Item", "name section key")

LISTS = {"stash": "skeldarStashList", "shared": "skeldarShareList",
         "chat": "skeldarChatWindow"}
JUMP = "skeldarHubJump_"
TITLES = {"stash": "Stash", "shared": "Shared", "chat": "Chat"}
ICONS = {"stash": "archive", "shared": "send", "chat": "message-circle"}
DOT = u"·"
DROPS = ("import", "send", "stash", "chat")
NOWHERE = "drop onto Shared, Stash, the chat or a viewport"
TEXTS = {"shared": ("send", "send to Shared"), "stash": ("stash", "copy into Stash"),
         "chat": ("chat", "send to the chat")}


def section_under(names):
    """The section whose list or rail icon the chain of object `names` (the
    widget under the cursor first) belongs to, or None. A popup copy's list
    is the base name with the copy's prefix in front. Pure."""
    for name in names or []:
        name = name or ""
        for section, leaf in LISTS.items():
            if name == leaf or name.endswith("_" + leaf):
                return section
        if name.startswith(JUMP) and name[len(JUMP):] in LISTS:
            return name[len(JUMP):]
    return None


def aim_for(source, under, over_viewport):
    """What a release does: dict(kind, text, section). The other section
    under the cursor wins over a viewport behind it. Pure."""
    if under and under != source:
        kind, text = TEXTS[under]
        return dict(kind=kind, text=text, section=under)
    if under is None and over_viewport:
        return dict(kind="import", text="import into the scene", section=None)
    return dict(kind="none", text=NOWHERE, section=None)


def caption(items, aim):
    """(text, good) for the ghost. Pure."""
    items = list(items or [])
    if aim.get("kind") not in DROPS or not items:
        return aim.get("text") or NOWHERE, False
    what = items[0].name if len(items) == 1 else "%d files" % len(items)
    return "%s %s %s" % (what, DOT, aim["text"]), True


# ------------------------------------------------------------------ the scene

def _names_at(gx, gy):
    """The object names of the widget under the global point, then its
    parents'. Read afresh every time: a widget is never kept (trap 135)."""
    import maya_hubqt
    q = maya_hubqt.qt()
    widget = q.QtWidgets.QApplication.widgetAt(q.QtCore.QPoint(int(gx), int(gy)))
    names = []
    while widget is not None:
        names.append(widget.objectName())
        widget = widget.parentWidget()
    return names


def _viewport_at(gx, gy):
    from maya_scenesetup import droptarget
    view, _local = droptarget.Viewport.at(gx, gy)
    return view is not None


def _act(kind, items):
    """The release's action, one idle later (the ghost gone first)."""
    keys = [item.key for item in items]
    source = items[0].section
    if source == "stash":
        import maya_stash as module
        verb = {"import": module.drop_import, "send": module.drop_to_share,
                "chat": module.drop_to_chat}[kind]
    else:
        import maya_share as module
        verb = {"import": module.drop_import, "stash": module.drop_to_stash,
                "chat": module.drop_to_chat}[kind]
    import maya.utils
    import maya_hubcopy as hubcopy
    maya.utils.executeDeferred(hubcopy.wrap(lambda: module._run(lambda: verb(keys))))
    return ""


def light(section, on):
    """The rail icon of `section` shown pressed while a drag is over it."""
    try:
        import maya_hubqt
        q = maya_hubqt.qt()
        for top in q.QtWidgets.QApplication.topLevelWidgets():
            for button in top.findChildren(q.QtWidgets.QToolButton, JUMP + section):
                button.setDown(bool(on))
    except Exception:                                        # noqa: BLE001
        pass


class FileScene(object):
    """The listdrag scene of one section's list (`source`)."""

    drops = DROPS

    def __init__(self, source, names_at=None, viewport_at=None, act=None):
        self.source = source
        self.icon = ICONS[source]
        self._names_at = names_at or _names_at
        self._viewport_at = viewport_at or _viewport_at
        self._act = act or _act
        self._lit = None

    def scale(self):
        try:
            import maya.cmds as cmds
            return float(cmds.mayaDpiSetting(query=True, realScaleValue=True) or 1.0)
        except Exception:                                    # noqa: BLE001
            return 1.0

    def snapshot(self):
        return None

    def _light(self, section):
        if section == self._lit:
            return
        if self._lit:
            light(self._lit, False)
        if section:
            light(section, True)
        self._lit = section

    def target(self, gx, gy, snap):
        under = section_under(self._names_at(gx, gy))
        aim = aim_for(self.source, under, under is None and self._viewport_at(gx, gy))
        self._light(aim.get("section"))
        return aim

    def over_hub(self, gx, gy):
        """The hub stops a drop - but not the other section's list or icon.
        Where it does, listdrag asks nothing more (no target, no say), so the
        icon lit before must go out here."""
        under = section_under(self._names_at(gx, gy))
        if under and under != self.source:
            return False
        if under == self.source:
            hub = True
        else:
            try:
                import maya_hubqt
                hub = bool(maya_hubqt.on_hub(gx, gy))
            except Exception:                                # noqa: BLE001
                hub = False
        if hub:
            self._light(None)
        return hub

    def ended(self):
        """The drag is over, wherever it ended: no icon stays lit."""
        self._light(None)

    def caption(self, records, aim):
        return caption(records, aim)

    def drop(self, records, aim):
        self._light(None)
        self._act(aim["kind"], list(records))
        return caption(records, aim)[0] + "..."

    def say(self, text):
        self._light(None)
        module = __import__("maya_stash" if self.source == "stash" else "maya_share")
        try:
            module._status(text)
        except Exception:                                    # noqa: BLE001
            pass


def attach(source, records_of):
    """The drag on `source`'s list in the card being built (the hub's or a
    popup copy's: listdrag resolves the name in the current scope). Where Qt
    cannot stand the list stays the list it was."""
    try:
        from maya_uebridge import listdrag
        import maya_hubcopy as hubcopy
        listdrag.attach(LISTS[source], hubcopy.wrap(records_of), FileScene(source))
    except Exception:                                        # noqa: BLE001
        import traceback
        print(traceback.format_exc())
