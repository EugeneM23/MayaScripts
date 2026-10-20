"""Running a skill, and what a cell shows of it (2026-10-19).

Every road is one the plugin already has: a section opens as the radial menu opens it (a window by
the cursor), a tool row runs through `maya_hotkeys.run` (a two-step one gets the radial menu's Finish
popup), a character is Animation Setup's Add Character, a card is the Pose Library's Apply, a weapon
is Inventory's Equip. Maya's own commands and scripts run in Maya's interpreter.

Nothing here keeps a module: each is imported when asked (`_mod`), so the tests hand in fakes.
"""

import importlib
import os
import sys
import traceback

from . import look

SHELF_ICON_FALLBACK = "commandButton.png"

# Our tool rows' own pictures (the Tools card's), where the radial menu's family icon would draw
# every tool alike; and their short names under the picture.
ROW_ICONS = {
    "tools.knot": "link", "tools.knot_offset": "focus-2", "tools.knot_orient": "rotate",
    "tools.double_local": "stack-2", "tools.double_world": "world", "tools.aim": "target",
    "tools.snapshot": "camera", "tools.bake": "check", "tools.bake_layer": "download",
    "tools.remove": "trash", "tools.inside": "transfer-in", "tools.world": "upload",
    "tools.swap": "arrows-exchange", "tools.across": "hand-grab", "tools.overlap": "wave-sine",
    "tools.fp_setup": "camera", "tools.attach_0": "unlink", "tools.attach_1": "link",
    "time.prev": "arrow-back-up", "time.insert": "plus", "time.remove": "x",
    "editor.graph": "chart-line", "editor.outliner": "picture-in-picture",
    "editor.script": "code", "editor.component": "table",
    "graph.overlay": "chart-line", "scene.weapon": "sword", "scene.remove_weapon": "sword",
    "retarget.run": "arrows-exchange", "connections.connect": "hand-grab",
    "connections.disconnect": "unlink",
}
SHORT = {
    "tools.knot_offset": "Offset", "tools.knot_orient": "Orient", "tools.double_local": "Local x2",
    "tools.double_world": "World x2", "tools.bake_layer": "Layer", "tools.remove": "Remove",
    "tools.bake": "Bake", "tools.inside": "Inside", "tools.world": "To world",
    "tools.fp_setup": "1P Setup", "time.insert": "Insert", "time.remove": "Remove",
    "time.prev": "Back", "time.next": "Forward", "editor.graph": "Graph", "editor.outliner": "Outliner",
    "editor.script": "Script", "editor.component": "Component",
    "graph.overlay": "Overlay", "scene.weapon": "Equip", "scene.remove_weapon": "Unequip",
    "retarget.run": "Retarget", "connections.connect": "Connect", "connections.disconnect": "Release",
}
SHORT_MAX = 9


def _mod(name):
    return importlib.import_module(name)


def _cmds():
    return _mod("maya.cmds")


# ------------------------------------------------------------------ texts

def label(item):
    """What a cell's tooltip and the drawer read for `item`."""
    if not item:
        return ""
    if item.get("label"):
        return item["label"]
    kind = item.get("kind")
    try:
        if kind in ("section", "cmd"):
            prefix = "section:" if kind == "section" else "cmd:"
            text = _mod("maya_radial").item_label(prefix + item["key"])
            return text or item["key"]
        if kind == "character":
            entry = _mod("maya_scenesetup.catalog").character_for(item["model"], item["char"])
            return entry.label if entry is not None else "%s [%s]" % (item["model"], item["char"])
        if kind == "card":
            return card_name(item["path"])
        if kind == "weapon":
            entry = _mod("maya_scenesetup.catalog").by_key(item["key"])
            return entry.label if entry is not None else item["key"]
        if kind == "maya":
            return item["command"]
        if kind in ("script", "shelf"):
            return look.script_label(item.get("code", ""))
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
    return item.get("key") or item.get("command") or kind or ""


def card_name(path):
    name = os.path.basename((path or "").replace("\\", "/").rstrip("/"))
    for suffix in (".pose", ".anim"):
        if name.lower().endswith(suffix):
            return name[:-len(suffix)]
    return name


def tag(item):
    """The few letters in a cell's corner: what kind of thing it is, where that is not obvious."""
    kind = (item or {}).get("kind")
    if kind == "character":
        return "rig" if item["char"] == "rig" else "skel"
    if kind == "card":
        return "anim" if item["path"].lower().rstrip("/").endswith(".anim") else "pose"
    if kind in ("script", "shelf"):
        return "py" if item.get("lang") == "python" else "mel"
    return ""


def short(item):
    """The few words under a cell's picture ("" where the picture says it: a portrait)."""
    if not item or item.get("kind") == "character":
        return ""
    if item.get("label"):
        text = item["label"]
    elif item.get("kind") == "cmd" and item["key"] in SHORT:
        return SHORT[item["key"]]
    else:
        text = label(item)
    text = text.replace("[", " ").replace("]", " ").strip()
    if len(text) <= SHORT_MAX:
        return text
    first = text.split()[0] if text.split() else text
    return first[:SHORT_MAX]


def tip(item):
    """The cell's tooltip: its name and what it is."""
    if not item:
        return "Empty - click for the skill library"
    return "%s\n%s" % (label(item), look.KIND_NAMES.get(item.get("kind"), ""))


def picture(item):
    """("icon", tabler name) / ("image", path) / ("text", letters) for a cell."""
    if not item:
        return None
    kind = item.get("kind")
    try:
        if kind in ("section", "cmd"):
            prefix = "section:" if kind == "section" else "cmd:"
            icon = ROW_ICONS.get(item["key"]) if kind == "cmd" else None
            icon = icon or _mod("maya_radial").item_icon(prefix + item["key"])
            if icon:
                return ("icon", icon)
        elif kind == "character":
            path = _mod("maya_scenesetup.catalog").portrait_path(item["model"])
            if os.path.isfile(path):
                return ("image", path)
        elif kind == "card":
            path = card_path(item) + "/thumbnail.jpg"
            if os.path.isfile(path):
                return ("image", path)
        elif kind == "weapon":
            catalog = _mod("maya_scenesetup.catalog")
            path = catalog.asset_path("weapon_icons/%s.png" % item["key"])
            if os.path.isfile(path):
                return ("image", path)
        elif kind == "shelf":
            image = item.get("image") or ""
            if image:
                return ("image", image if os.path.isabs(image) else ":/" + image)
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
    return ("text", look.initials(label(item)))


def card_path(item):
    """The card's folder: its path under the Pose Library's root."""
    path = item.get("path", "")
    if os.path.isabs(path):
        return path.replace("\\", "/")
    try:
        root = _mod("maya_poselib.window").Scene().library()
    except Exception:                                        # noqa: BLE001
        return path
    return (root.rstrip("/") + "/" + path).replace("\\", "/")


def relative_card(path):
    """A card's path under the library's root ("" root on another drive: the path itself)."""
    path = (path or "").replace("\\", "/").rstrip("/")
    try:
        root = _mod("maya_poselib.window").Scene().library().replace("\\", "/").rstrip("/")
    except Exception:                                        # noqa: BLE001
        return path
    if path.lower().startswith(root.lower() + "/"):
        return path[len(root) + 1:]
    return path


# ---------------------------------------------------------------- waiting

def waiting(item):
    """True while a two-step tool in this cell waits for its Finish."""
    if not item or item.get("kind") != "cmd":
        return False
    try:
        return bool(_mod("maya_radial").waiting(item["key"]))
    except Exception:                                        # noqa: BLE001
        return False


# ---------------------------------------------------------------- running

def run(item, point=(0, 0)):
    """Run `item`; `point` the global cursor (where a section's window or a Finish popup stands).
    Returns the line to say ("" when the road said its own)."""
    if not item or not look.valid_item(item):
        return "Empty cell"
    kind = item["kind"]
    if kind == "section":
        return _mod("maya_radial").run_item("section:" + item["key"], point) or ""
    if kind == "cmd":
        hotkeys = _mod("maya_hotkeys")
        if hotkeys.row(item["key"]) is None:
            return "No tool '%s' any more - set this cell again" % item["key"]
        return _mod("maya_radial").run_item("cmd:" + item["key"], point) or ""
    if kind == "character":
        return _character(item)
    if kind == "card":
        return _card(item)
    if kind == "weapon":
        return _weapon(item)
    if kind == "maya":
        _mod("maya.mel").eval(item["command"])
        return item["command"]
    return run_script(item.get("lang", "python"), item.get("code", ""), label(item))


def _character(item):
    catalog = _mod("maya_scenesetup.catalog")
    entry = catalog.character_for(item["model"], item["char"])
    if entry is None:
        return "No %s [%s] in the catalog any more - set this cell again" % (item["model"], item["char"])
    message = _mod("maya_scenesetup.character").add_character(entry)
    try:
        _mod("maya_scenesetup.window").refresh()
    except Exception:                                        # noqa: BLE001
        pass
    return message or entry.label


def _card(item):
    path = card_path(item)
    if not os.path.isdir(path):
        return "The card %s is gone from the Pose Library - set this cell again" % card_name(path)
    window = _mod("maya_poselib.window")
    scene = window.Scene()
    options = window.remembered_options(scene.option)
    message = scene.apply(path, False, options=options)
    return message or card_name(path)


def _weapon(item):
    catalog = _mod("maya_scenesetup.catalog")
    entry = catalog.by_key(item["key"])
    if entry is None:
        return "No weapon '%s' any more - set this cell again" % item["key"]
    window = _mod("maya_scenesetup.window")
    window.select_weapon(entry.key)
    message = window.add_weapon()
    return message or "Equip %s" % entry.label


def run_script(lang, code, name="Script"):
    """Run `code` in Maya's own interpreter: Python in __main__, MEL through mel.eval."""
    if lang == "mel":
        _mod("maya.mel").eval(code)
        return name
    namespace = sys.modules["__main__"].__dict__
    exec(compile(code, "<skill %s>" % name, "exec"), namespace)
    return name


# ------------------------------------------------------- the Script Editor

def script_editor_text():
    """(text, lang) of the Script Editor's current tab: its selected text, else all of it.
    ("", "python") when there is no Script Editor."""
    cmds, mel = _cmds(), _mod("maya.mel")
    try:
        tabs = mel.eval("global string $gCommandExecuterTabs; $skeldarSkillTmp = $gCommandExecuterTabs;")
        executers = mel.eval("global string $gCommandExecuter[]; $skeldarSkillTmpA = $gCommandExecuter;")
        if not tabs or not executers or not cmds.tabLayout(tabs, exists=True):
            return "", "python"
        index = int(cmds.tabLayout(tabs, query=True, selectTabIndex=True) or 1) - 1
        field = executers[min(max(index, 0), len(executers) - 1)]
        text = cmds.cmdScrollFieldExecuter(field, query=True, selectedText=True) or ""
        if not text.strip():
            text = cmds.cmdScrollFieldExecuter(field, query=True, text=True) or ""
        source = cmds.cmdScrollFieldExecuter(field, query=True, sourceType=True) or "python"
        return text, ("mel" if source.lower() == "mel" else "python")
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        return "", "python"


# ------------------------------------------------------- dragged into the scene

def _defer(call):
    """Run `call` one idle later (the drag's ghost gone first); at once without Maya's loop."""
    try:
        _mod("maya.utils").executeDeferred(call)
    except Exception:                                        # noqa: BLE001
        call()


class SceneDrag(object):
    """A skill dragged off the bar into a viewport (2026-10-19, «персонажи не переносятся из панели
    скилов драгом на сцену»): what its own panel's drag does there. A character stands on the
    floor point or swaps the character under the cursor (the portrait grid's road); a pose /
    animation card goes onto the character under it or adds its source on the floor (the Pose
    Library's road); a weapon goes into the hand under the cursor or onto the floor (the
    Inventory's road). Any other skill dropped onto a viewport runs there, as a click on its cell
    would (2026-10-19, «скилы применялись ... драг анд дропом во вьюпорт»). The scene's characters
    are read once, at the start."""

    def __init__(self, item):
        self.item = item or {}
        self.kind = self.item.get("kind")
        self.name = label(item)
        self.snap = None
        self.scene = None
        try:
            if self.kind == "weapon":
                self.scene = _mod("maya_inventory").Scene()
                self.snap = self.scene.snapshot()
            elif self.kind == "character":
                self.scene = _mod("maya_chargrid").Scene()
                self.scene.begin(self.name)
            elif self.kind == "card":
                path = card_path(self.item)
                data = _mod("maya_poselib.store").read(path) if os.path.isdir(path) else {}
                if str((data or {}).get("kind") or "character") == "character":
                    self.scene = _mod("maya_poselib.window").Scene()
                    self.snap = self.scene.snapshot_scene()
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()
            self.scene = None

    def active(self):
        return bool(self.item) and look.valid_item(self.item)

    def _viewport(self, gx, gy):
        try:
            view, _local = _mod("maya_scenesetup.droptarget").Viewport.at(gx, gy)
            return view is not None
        except Exception:                                    # noqa: BLE001
            return False

    def _on_hub(self, gx, gy):
        try:
            return bool(_mod("maya_hubqt").on_hub(gx, gy))
        except Exception:                                    # noqa: BLE001
            return False

    def target(self, gx, gy):
        """{"kind": "floor" | "swap" | "character" | "none", ...} under the global point."""
        if not self.active():
            return {"kind": "none", "text": "off the bar: nothing"}
        if self._on_hub(gx, gy):
            return {"kind": "none", "text": "release off the hub"}
        if self.scene is None:
            if self._viewport(gx, gy):
                return {"kind": "run", "point": (gx, gy)}
            return {"kind": "none", "text": "drop onto a viewport"}
        try:
            if self.kind == "character":
                return self.scene.target(gx, gy)
            return self.scene.target(gx, gy, self.snap)
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()
            return {"kind": "none", "text": "no target"}

    def caption(self, gx, gy):
        """(text, good) for the ghost."""
        aim = self.target(gx, gy)
        kind = aim.get("kind")
        if kind == "swap":
            return aim.get("text") or "swap", True
        if kind == "run":
            return "%s · run here" % self.name, True
        if kind == "hand":
            return aim.get("text") or "%s · into the hand" % self.name, True
        if kind == "character":
            return "%s · onto %s" % (self.name, aim.get("label") or "the character"), True
        if kind == "floor" and aim.get("point") is not None:
            point = aim["point"]
            what = self.name if self.kind in ("character", "weapon") else "%s · a new character" % self.name
            return "%s · floor (%d, %d)" % (what, int(round(point[0])), int(round(point[-1]))), True
        return "%s · %s" % (self.name, aim.get("text") or "no target"), False

    def drop(self, gx, gy, say=None):
        """Released at the global point: done one idle later; `say` gets the line."""
        aim = self.target(gx, gy)
        kind = aim.get("kind")
        say = say or (lambda text: None)
        item = self.item

        def done(call):
            def later():
                try:
                    say(call() or "")
                except Exception as error:                   # noqa: BLE001
                    traceback.print_exc()
                    say("%s: %s" % (self.name, error))
            _defer(later)
            return "%s - adding it" % self.name

        if self.kind == "character" and kind in ("floor", "swap"):
            window = _mod("maya_scenesetup.window")
            if kind == "floor":
                point = aim["point"]
                return done(lambda: window.place_character(item["model"], item["char"], point))
            root = aim["root"]
            return done(lambda: window.swap_character(item["model"], item["char"], root))
        if kind == "run":
            point = aim["point"]
            done(lambda: run(item, point))
            return "%s - running" % self.name
        if self.kind == "weapon" and kind in ("hand", "floor"):
            entry = _mod("maya_scenesetup.catalog").by_key(item["key"])
            if entry is None:
                return "No weapon '%s' any more - set this cell again" % item["key"]
            scene = self.scene
            if kind == "hand":
                return done(lambda: scene.to_hand(aim["root"], aim["side"], entry))
            return done(lambda: scene.to_floor(aim["root"], entry, aim["point"], aim["heading"],
                                               aim.get("side")))
        if self.kind == "card" and kind in ("floor", "character"):
            path = card_path(item)
            if not os.path.isdir(path):
                return "The card %s is gone from the Pose Library" % card_name(path)
            window = _mod("maya_poselib.window")
            scene = self.scene
            options = window.remembered_options(scene.option) if path.lower().endswith(".anim") else None
            extra = {"options": options} if options is not None else {}
            if kind == "character":
                root = aim["root"]
                return done(lambda: scene.apply_onto(path, root, False, **extra))
            point = aim.get("point")
            return done(lambda: _last(scene.drop_floor(path, point, False, **extra)))
        return ""

    def end(self):
        try:
            if self.kind == "character" and self.scene is not None:
                self.scene.end()
        except Exception:                                    # noqa: BLE001
            pass


def _last(result):
    return result[-1] if isinstance(result, tuple) and result else result
