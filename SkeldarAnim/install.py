"""Drag this file into an open Maya viewport to install SkeldarAnim.

Copies the toolset into <userAppDir>/scripts/SkeldarAnim and builds the
SkeldarAnim shelf: the SkeldarAnim window (every tool a collapsible
section, dock it anywhere -- 2026-09-17), then UE Bridge, Scene Setup,
Retarget, Hotkeys, Studio, Colour, each opening that window on its own
section -- plus the Rig Picker, the native OverRig panel and Overshoot
when `skeldar_features` switches them on. Re-dragging updates in place.
The unzipped folder can be deleted after installing.

Design: docs/superpowers/specs/2026-08-21-installer-design.md

Stdlib-only at import: at drop time nothing of ours is on sys.path, and
maya.cmds exists only inside the running Maya -- so the Maya imports live
inside the functions that run there.
"""

import os
import shutil
import sys

SHELF = "SkeldarAnim"

# The whitelist. Everything the animator's prefs receive, and nothing
# else: tests, docs, archive and the other root-level tools stay home.
_PAYLOAD = (
    "maya_overrig",
    "maya_uebridge",
    "maya_scenesetup",
    "maya_overshoot.py",
    "maya_hotkeys.py",
    "maya_vpstudio.py",
    "maya_colour.py",
    "maya_winfit.py",
    "maya_hub.py",
    "icons",
    "assets",
    "overrig",
    "skeldar_features.py",
    "maya_rigs.py",
    "maya_asretarget.py",
    "maya_pmretarget.py",
    "maya_rig_retarget.py",
    "install.py",
    "README_INSTALL.txt",
)

# (label, annotation, module, function, icon, feature flag or ""). A row
# naming a flag is on the shelf only while that flag in skeldar_features
# is True -- the Rig Picker went behind PICKER on 2026-09-07, when the
# toolset moved from OverRig to the AdvancedSkeleton rig, and Overshoot
# behind OVERSHOOT on 2026-09-08. The Curve Overlay left the plugin the
# same day (archive/maya_curveview), and Bake folded into Retarget.
_PYTHON_BUTTONS = (
    ("SkeldarAnim", "The SkeldarAnim window: every tool a collapsible "
     "section - dock it to any panel, tear it off, it remembers its place",
     "maya_hub", "show", "hub.png", ""),
    ("Rig Picker", "OverRig picker: build, switch and select the rig",
     "maya_overrig", "show_picker", "picker.png", "PICKER"),
    ("UE Bridge", "Import animations from the running Unreal editor onto "
     "the AdvancedSkeleton rig", "maya_uebridge", "show_window",
     "uebridge.png", ""),
    ("Scene Setup", "Add the rig or a skeleton, a weapon in the hand",
     "maya_scenesetup", "show_window", "scenesetup.png", ""),
    ("Retarget", "Select the imported skeleton (and a control of the rig "
     "when there are several): the rig takes the clip - retarget, bake, "
     "weapon and camera bones carried, camera set up",
     "maya_rig_retarget", "retarget_button", "retarget.png", ""),
    ("Overshoot", "Build the stop of a move on the selected keys",
     "maya_overshoot", "show_overshoot_ui", "overshoot.png", "OVERSHOOT"),
    ("Hotkeys", "Temporary hotkey map on/off - assign keys in Maya's "
     "Hotkey Editor", "maya_hotkeys", "toggle", "hotkeys.png", ""),
    ("Studio", "Viewport Studio: studio light, shadows, ambient occlusion "
     "and motion blur, live in the viewport", "maya_vpstudio",
     "show_window", "vpstudio.png", ""),
    ("Colour", "Recolour the selected character, bone or mesh from an "
     "eight-colour palette", "maya_colour", "show_window", "colour.png",
     ""),
)


def features():
    """The flag module, loaded from beside this file.

    Not a plain import: at drop time nothing of ours is on sys.path, and
    the installed folder carries its own copy that must not shadow the
    one being dragged. Cached in sys.modules under its own name so the
    tests can flip a flag and see the shelf follow.
    """
    import importlib.util
    path = os.path.join(source_root(), "skeldar_features.py")
    module = sys.modules.get("skeldar_features")
    if module is None or os.path.normcase(
            getattr(module, "__file__", "") or "") != os.path.normcase(path):
        spec = importlib.util.spec_from_file_location("skeldar_features",
                                                      path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules["skeldar_features"] = module
    return module


def payload():
    """What gets copied, as names relative to the distribution root."""
    return _PAYLOAD


def source_root():
    """The distribution root: the folder this file was dragged from."""
    return os.path.dirname(os.path.abspath(__file__))


def module_names():
    """What the shelf buttons import, derived from the payload.

    `install` itself is left out: it is the module running right now.
    """
    names = []
    for name in payload():
        if name.endswith(".py"):
            stem = name[:-3]
            if stem != "install":
                names.append(stem)
        elif os.path.isdir(os.path.join(source_root(), name)) \
                and os.path.isfile(os.path.join(source_root(), name,
                                                "__init__.py")):
            names.append(name)
    return names


def purge_modules(names=None, modules=None):
    """Drop our packages from the import cache. Returns what was dropped.

    The update's missing half. Copying the files replaces what is on
    disk, but a Maya that has already imported the old ones keeps them
    in `sys.modules` for the rest of the session -- so the shelf button
    goes on opening the previous version, and the animator, who did
    everything right, reports that the update did nothing. Purged here
    the next press imports from disk.

    Package roots go too, not only submodules: a stale root keeps its
    submodules bound as attributes, and `from pkg import mod` then hands
    back the old object (the same trap the tests hit).
    """
    names = module_names() if names is None else names
    modules = sys.modules if modules is None else modules
    dropped = []
    for key in list(modules):
        root = key.split(".")[0]
        if root in names:
            del modules[key]
            dropped.append(key)
    return sorted(dropped)


def button_specs(dest):
    """The shelf buttons as data, every path baked in absolute.

    `dest` may arrive with backslashes; commands reach MEL and the shelf
    editor, where a backslash starts an escape -- so it is normalised
    once here and nowhere else needs to care.
    """
    dest = dest.replace("\\", "/").rstrip("/")
    bootstrap = (
        "import sys\n"
        "_p = \"{0}\"\n"
        "if _p not in sys.path:\n"
        "    sys.path.insert(0, _p)\n").format(dest)
    flags = features()
    specs = []
    for label, note, module, func, icon, flag in _PYTHON_BUTTONS:
        if flag and not getattr(flags, flag, False):
            continue
        specs.append({
            "label": label,
            "annotation": note,
            "image": "{0}/icons/{1}".format(dest, icon),
            "sourceType": "python",
            "command": (bootstrap
                        + "import {0}\n{0}.{1}()\n".format(module, func)),
        })
    if not flags.OVERRIG:
        return specs
    # Verbatim from OverRig's own Drag_and_Drop_to_install.mel, paths
    # aside: the two globals and the (1) coloring are the author's own
    # defaults, and $path_to_JGLBN must point at the shipped misc/.
    specs.append({
        "label": "OverRig",
        "annotation": "The native OverRig panel (Pavel Barnev, v10.2)",
        "image": "{0}/overrig/icons/base_OverRig.bmp".format(dest),
        "sourceType": "mel",
        "command": (
            'source "{0}/overrig/base_OverRig_scripts.mel";\n'
            "global int $barnev_OverRig_RotateOrder = 0;\n"
            "global string $path_to_JGLBN;\n"
            '$path_to_JGLBN = "{0}/overrig/misc/";\n'
            "base_OverRig_scripts(1);\n").format(dest),
    })
    return specs


def same_place(a, b):
    """True when the two paths are one folder on disk.

    The guard that keeps a re-drag from the installed folder itself from
    rmtree-ing the very files it is about to copy.
    """
    if not (os.path.isdir(a) and os.path.isdir(b)):
        return False
    return os.path.samefile(a, b)


def copy_payload(src_root, dest):
    """The whitelist into `dest`, replacing whatever was there."""
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    for name in payload():
        src = os.path.join(src_root, name)
        target = os.path.join(dest, name)
        if os.path.isdir(src):
            shutil.copytree(src, target, ignore=ignore)
        else:
            shutil.copy2(src, target)


def _build_shelf(dest):
    """The SkeldarAnim tab, rebuilt button-for-button.

    The tab is created through Maya's own addNewShelfTab (it keeps the
    shelf optionVars consistent) and never deleted -- an existing tab
    only has its buttons replaced, which is what makes a re-drag an
    update rather than a duplicate.
    """
    import maya.cmds as cmds
    import maya.mel as mel
    if not cmds.shelfLayout(SHELF, exists=True):
        mel.eval('addNewShelfTab "{0}";'.format(SHELF))
    for child in cmds.shelfLayout(SHELF, query=True, childArray=True) or []:
        cmds.deleteUI(child)
    for spec in button_specs(dest):
        cmds.shelfButton(
            label=spec["label"],
            annotation=spec["annotation"],
            image=spec["image"],
            sourceType=spec["sourceType"],
            command=spec["command"],
            parent=SHELF,
        )


def install(dropped=None, quiet=False):
    """Copy the payload, build the shelf, say so.

    `dropped` is the path Maya hands onMayaDroppedPythonFile; __file__
    is the fallback. `quiet` skips the confirm dialog: a modal dialog
    over the command port blocks Maya's idle queue, so scripted runs
    must never raise one.
    """
    import maya.cmds as cmds
    src = os.path.dirname(os.path.abspath(dropped)) if dropped \
        else source_root()
    dest = os.path.join(cmds.internalVar(userAppDir=True),
                        "scripts", SHELF)
    if not same_place(src, dest):
        copy_payload(src, dest)
    _build_shelf(dest.replace("\\", "/"))
    reloaded = purge_modules()
    if not quiet:
        note = ""
        if reloaded:
            note = ("\n\nThe previous version was loaded in this session"
                    "\n({0} modules dropped). Close any of our panels that"
                    "\nare open and reopen them from the shelf; restart"
                    "\nMaya if anything still looks old.".format(
                        len(reloaded)))
        cmds.confirmDialog(
            title="SkeldarAnim",
            message="Installed: shelf {0}, {1} buttons.\n{2}{3}".format(
                SHELF, len(button_specs(dest)), dest, note),
            button=["OK"])
    return dest


def onMayaDroppedPythonFile(*args):
    install(args[0] if args else None)
