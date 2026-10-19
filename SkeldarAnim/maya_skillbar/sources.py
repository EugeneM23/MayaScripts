"""The skill library's entries (2026-10-19): everything a cell can hold, by category.

An entry is (category, item, label). `entries(category)` answers one category, "All" every one.
Each category reads its own source and a failure there leaves the others standing.
"""

import importlib
import os
import traceback

from . import look, run

CATEGORIES = ("All", "Sections", "Tools", "Characters", "Poses", "Weapons", "Maya", "Shelves",
              "Scripts")

# Maya's runtime commands an animator reaches for; the drawer's search reaches every other one.
MAYA_COMMANDS = (
    "SetKey", "SetBreakdown", "SetKeyTranslate", "SetKeyRotate", "SetKeyScale",
    "GraphEditor", "DopeSheetEditor", "TimeEditorWindow", "OutlinerWindow", "HypershadeWindow",
    "ScriptEditor", "NodeEditorWindow", "BakeSimulation", "BakeSimulationOptions",
    "CreateLocator", "GroupObjects", "ParentConstraintOptions", "OrientConstraintOptions",
    "PointConstraintOptions", "AimConstraintOptions", "DeleteConstraints",
    "CreateMotionTrail", "GhostObject", "UnghostObject", "Playblast", "PlayblastOptions",
    "FrameSelectedWithoutChildren", "FrameAllInAllViews", "ToggleIsolateSelect",
    "CycleBackgroundColor", "DeleteHistory", "FreezeTransformations", "CenterPivot",
    "ResetTransformations", "HotkeyPreferencesWindow", "PreferencesWindow",
)


def _mod(name):
    return importlib.import_module(name)


def entries(category="All", search=""):
    """[(category, item, label)] of `category` (every category for "All") matching `search`."""
    wanted = CATEGORIES[1:] if category == "All" else (category,)
    out = []
    for name in wanted:
        reader = _READERS.get(name)
        if reader is None:
            continue
        try:
            found = reader(search if name == "Maya" else "")
        except Exception:                                    # noqa: BLE001
            traceback.print_exc()
            continue
        out.extend((name, item, text) for item, text in found)
    return filtered(out, search)


def filtered(found, search):
    words = (search or "").lower().split()
    if not words:
        return list(found)
    return [entry for entry in found
            if all(w in (entry[2] + " " + entry[0]).lower() for w in words)]


def _sections(_search):
    hub = _mod("maya_hub")
    return [({"kind": "section", "key": s.key}, s.label) for s in hub.SECTIONS]


def _tools(_search):
    out = []
    for _category, rows in _mod("maya_radial").functions():
        for key, text in rows:
            out.append(({"kind": "cmd", "key": key}, text))
    return out


def _characters(_search):
    catalog = _mod("maya_scenesetup.catalog")
    return [({"kind": "character", "model": e.model, "char": e.kind}, e.label)
            for e in catalog.CHARACTERS if getattr(e, "model", "")]


def _poses(_search):
    store = _mod("maya_poselib.store")
    root = _mod("maya_poselib.window").Scene().library()
    cards, _broken = store.cards(root)
    out = []
    for card in cards:
        rel = run.relative_card(card.path)
        name = card.name if not card.folder else "%s / %s" % (card.folder, card.name)
        out.append(({"kind": "card", "path": rel}, name))
    return out


def _weapons(_search):
    catalog = _mod("maya_scenesetup.catalog")
    return [({"kind": "weapon", "key": w.key}, w.label) for w in catalog.WEAPONS]


def _maya(search):
    cmds = _mod("maya.cmds")
    every = cmds.runTimeCommand(query=True, commandArray=True) or []
    if search and search.strip():
        words = search.lower().split()
        names = [n for n in every if all(w in n.lower() for w in words)][:200]
    else:
        known = set(every)
        names = [n for n in MAYA_COMMANDS if n in known]
    return [({"kind": "maya", "command": n}, n) for n in names]


def _shelves(_search):
    out = []
    for shelf, button in shelf_buttons():
        text = button.get("label") or look.script_label(button["code"])
        item = {"kind": "shelf", "lang": button["lang"], "code": button["code"], "label": text}
        if button.get("image"):
            item["image"] = button["image"]
        out.append((item, "%s / %s" % (shelf, text)))
    return out


def shelf_buttons():
    """[(shelf name, {"lang", "code", "label", "image"})] of every Maya shelf button with a command."""
    cmds, mel = _mod("maya.cmds"), _mod("maya.mel")
    top = mel.eval("global string $gShelfTopLevel; $skeldarSkillShelf = $gShelfTopLevel;")
    if not top or not cmds.tabLayout(top, exists=True):
        return []
    out = []
    for shelf in cmds.tabLayout(top, query=True, childArray=True) or []:
        for child in cmds.shelfLayout(shelf, query=True, childArray=True) or []:
            if cmds.objectTypeUI(child) != "shelfButton":
                continue
            code = cmds.shelfButton(child, query=True, command=True) or ""
            if not code.strip():
                continue
            source = (cmds.shelfButton(child, query=True, sourceType=True) or "mel").lower()
            text = (cmds.shelfButton(child, query=True, label=True)
                    or cmds.shelfButton(child, query=True, imageOverlayLabel=True)
                    or cmds.shelfButton(child, query=True, annotation=True) or "")
            image = cmds.shelfButton(child, query=True, image=True) or ""
            out.append((shelf, {"lang": "python" if source == "python" else "mel", "code": code,
                                "label": text.strip()[:40],
                                "image": image if image and image != run.SHELF_ICON_FALLBACK else ""}))
    return out


def _scripts(_search):
    text, lang = run.script_editor_text()
    item = look.script_item(text, lang, "From the Script Editor")
    return [(item, "From the Script Editor")] if item else []


_READERS = {
    "Sections": _sections, "Tools": _tools, "Characters": _characters, "Poses": _poses,
    "Weapons": _weapons, "Maya": _maya, "Shelves": _shelves, "Scripts": _scripts,
}


def icon_exists(path):
    return bool(path) and (path.startswith(":/") or os.path.isfile(path))
