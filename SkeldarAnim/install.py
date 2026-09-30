"""Drag this file into an open Maya viewport to install SkeldarAnim.

Copies the toolset into <userAppDir>/scripts/SkeldarAnim and builds the
SkeldarAnim shelf: the SkeldarAnim window (every tool a collapsible
section, dock it anywhere -- 2026-09-17), then UE Bridge, Characters,
Weapons, Retarget, Hotkeys, Studio, Colour, each opening that window on its own
section -- plus the Rig Picker, the native OverRig panel and Overshoot
when `skeldar_features` switches them on. Re-dragging updates in place.
The unzipped folder can be deleted after installing.

Design: docs/superpowers/specs/2026-08-21-installer-design.md

Stdlib-only at import: at drop time nothing of ours is on sys.path, and
maya.cmds exists only inside the running Maya -- so the Maya imports live
inside the functions that run there.
"""

import json
import os
import shutil
import subprocess
import sys

SHELF = "SkeldarAnim"

# The hub's workspaceControl (maya_hub.CONTROL). Named here, not imported: at
# drop time nothing of ours is on sys.path.
HUB_CONTROL = "skeldarAnimHub"

# Which build an installed copy is (2026-09-28, Check update): a build
# carries this file, and an install from the repository writes its git
# commit instead. Not a payload row -- the source tree holds none.
VERSION_FILE = "version.json"
LOG_LENGTH = 30

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
    "maya_hubstyle.py",         # the hub's skin (2026-09-28): the look as data
    "maya_hubicons.py",         # its Tabler icons
    "maya_hubqt.py",            # its Qt widgets
    "maya_invlook.py",          # the weapon inventory's look (2026-09-29)
    "maya_inventory.py",        # the weapon inventory: the Weapons card
    "maya_charlook.py",         # the Characters portrait grid's look (2026-09-30)
    "maya_chargrid.py",         # the Characters portrait grid
    "icons",
    "assets",
    "overrig",
    "skeldar_features.py",
    "maya_rigs.py",
    "maya_asretarget.py",
    "maya_pmretarget.py",
    "maya_rig_retarget.py",
    "maya_graphoverlay",        # the Graph Editor over the viewport (2026-09-30)
    "maya_update.py",
    "install.py",
    "README_INSTALL.txt",
)

# (label, annotation, module, function, icon, feature flag or ""). A row
# naming a flag is on the shelf only while that flag in skeldar_features
# is True -- the Rig Picker went behind PICKER on 2026-09-07, when the
# toolset moved from OverRig to the AdvancedSkeleton rig, Overshoot
# behind OVERSHOOT on 2026-09-08, and the seven section buttons behind
# SECTION_BUTTONS on 2026-09-19 («пока пусть будет только наш
# SkeldarAnim»): the hub button reaches every section. The Curve Overlay
# left the plugin on 2026-09-08 (archive/maya_curveview), and Bake folded
# into Retarget.
_PYTHON_BUTTONS = (
    ("SkeldarAnim", "The SkeldarAnim window: every tool a collapsible "
     "section - dock it to any panel, tear it off, it remembers its place",
     "maya_hub", "show", "hub.png", ""),
    ("Rig Picker", "OverRig picker: build, switch and select the rig",
     "maya_overrig", "show_picker", "picker.png", "PICKER"),
    ("UE Bridge", "Import animations from the running Unreal editor onto "
     "the AdvancedSkeleton rig", "maya_uebridge", "show_window",
     "uebridge.png", "SECTION_BUTTONS"),
    ("Characters", "Add the AdvancedSkeleton rig or a bare skeleton, in "
     "its own colour", "maya_scenesetup", "show_window", "characters.png",
     "SECTION_BUTTONS"),
    ("Weapons", "A weapon in the hand: sword, spear, dagger or any FBX; "
     "the grip, the colour", "maya_scenesetup", "show_weapons",
     "weapons.png", "SECTION_BUTTONS"),
    ("Retarget", "Select the imported skeleton (and a control of the rig "
     "when there are several): the rig takes the clip - retarget, bake, "
     "weapon and camera bones carried, camera set up",
     "maya_rig_retarget", "retarget_button", "retarget.png",
     "SECTION_BUTTONS"),
    ("Overshoot", "Build the stop of a move on the selected keys",
     "maya_overshoot", "show_overshoot_ui", "overshoot.png", "OVERSHOOT"),
    ("Hotkeys", "Temporary hotkey map on/off - assign keys in Maya's "
     "Hotkey Editor", "maya_hotkeys", "toggle", "hotkeys.png",
     "SECTION_BUTTONS"),
    ("Studio", "Viewport Studio: studio light, shadows, ambient occlusion "
     "and motion blur, live in the viewport", "maya_vpstudio",
     "show_window", "vpstudio.png", "SECTION_BUTTONS"),
    ("Colour", "Recolour the selected character, bone or mesh from an "
     "eight-colour palette", "maya_colour", "show_window", "colour.png",
     "SECTION_BUTTONS"),
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
    # OVERRIG is the shelf button alone; the 84 hotkey rows ride
    # OVERRIG_HOTKEYS in maya_hotkeys.commands (2026-09-19).
    if not getattr(flags, "OVERRIG", False):
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


def git_output(cwd, *args):
    """`git <args>` in `cwd`, stripped; "" when git or the repo is absent.

    CREATE_NO_WINDOW on Windows: from the Maya GUI a console program would
    flash a console window per call.
    """
    flags = 0x08000000 if os.name == "nt" else 0
    try:
        out = subprocess.check_output(("git",) + args, cwd=cwd,
                                      stderr=subprocess.DEVNULL,
                                      creationflags=flags)
    except Exception:
        return ""
    return out.decode("utf-8", "replace").strip()


def git_record(src_root, names=None):
    """The source's version record; {} without git.

    The commit is the last one that touched the PAYLOAD (`names`, the
    payload by default), not HEAD: a commit to CLAUDE.md or a spec changes
    nothing a colleague receives, and must not read as a new build to
    download. `log` is the last LOG_LENGTH such commits, newest first,
    `[sha, subject]` -- Check update lists the ones newer than what is
    installed. `dirty` asks about the payload only.
    """
    names = payload() if names is None else names
    commit = git_output(src_root, "log", "-1", "--format=%H", "--", *names)
    if len(commit) != 40:
        return {}
    log = []
    for line in git_output(src_root, "log", "-{0}".format(LOG_LENGTH),
                           "--format=%H %s", "--", *names).splitlines():
        sha, _, subject = line.partition(" ")
        log.append([sha, subject])
    return {
        "name": SHELF,
        "commit": commit,
        "short": commit[:7],
        "subject": git_output(src_root, "log", "-1", "--format=%s", commit),
        "date": git_output(src_root, "log", "-1", "--format=%cI", commit),
        "branch": git_output(src_root, "rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": bool(git_output(src_root, "status", "--porcelain", "--",
                                 *names)),
        "log": log,
    }


def read_version(folder):
    """The version record in `folder`, or {}."""
    try:
        with open(os.path.join(folder, VERSION_FILE),
                  encoding="utf-8") as handle:
            record = json.load(handle)
    except (OSError, ValueError):
        return {}
    return record if isinstance(record, dict) else {}


def write_version(src, dest):
    """`<dest>/version.json`: the build's own when `src` is a build, else
    the source's git record marked with where it came from."""
    own = os.path.join(src, VERSION_FILE)
    if os.path.isfile(own):
        shutil.copy2(own, os.path.join(dest, VERSION_FILE))
        return read_version(dest)
    record = git_record(src)
    record["source"] = src.replace("\\", "/")
    with open(os.path.join(dest, VERSION_FILE), "w",
              encoding="utf-8") as handle:
        json.dump(record, handle, indent=1, ensure_ascii=False)
    return record


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


def _cmds():
    import maya.cmds as cmds
    return cmds


def install(dropped=None, quiet=False):
    """Copy the payload, build the shelf, say so.

    `dropped` is the path Maya hands onMayaDroppedPythonFile; __file__
    is the fallback. `quiet` skips the confirm dialog: a modal dialog
    over the command port blocks Maya's idle queue, so scripted runs
    must never raise one.

    The purge runs BEFORE the shelf is built: building it loads
    skeldar_features (`features()`), and a purge after dropped that very
    module and told a fresh Maya «the previous version was loaded»
    (2026-09-28, the one-file installer's first run).
    """
    cmds = _cmds()
    src = os.path.dirname(os.path.abspath(dropped)) if dropped \
        else source_root()
    dest = os.path.join(cmds.internalVar(userAppDir=True),
                        "scripts", SHELF)
    if not same_place(src, dest):
        copy_payload(src, dest)
        write_version(src, dest)
    reloaded = purge_modules()
    _build_shelf(dest.replace("\\", "/"))
    buttons = len(button_specs(dest))
    # ...and the flags the shelf just read were the SOURCE's (a temp folder,
    # for the one-file installer): the next import finds the installed copy.
    sys.modules.pop("skeldar_features", None)
    # An open hub keeps the widgets the OLD modules built (2026-09-28, the
    # Orc D missing from its dropdown after an install); it is rebuilt from
    # the new ones once this call has returned -- deferred, as the updater's
    # `_reopen`, so an install run from a hub button never deletes the layout
    # holding that button under itself.
    hub_open = bool(cmds.workspaceControl(HUB_CONTROL, exists=True))
    if hub_open:
        target = dest.replace("\\", "/")
        cmds.evalDeferred(lambda: rebuild_open_hub(target),
                          lowestPriority=True)
    if not quiet:
        note = ""
        if reloaded:
            then = ("The open SkeldarAnim hub is rebuilt from\nthe new one;"
                    " restart Maya if anything still\nlooks old."
                    if hub_open else
                    "Close any of our panels that\nare open and reopen them"
                    " from the shelf; restart\nMaya if anything still looks"
                    " old.")
            note = ("\n\nThe previous version was loaded in this session"
                    "\n({0} modules dropped). {1}".format(len(reloaded),
                                                          then))
        cmds.confirmDialog(
            title="SkeldarAnim",
            message="Installed: shelf {0}, {1} buttons.\n{2}{3}".format(
                SHELF, buttons, dest, note),
            button=["OK"])
    return dest


def rebuild_open_hub(dest, importer=None):
    """The hub's accordion rebuilt inside its standing control from the FRESH
    maya_hub -- the installed copy's, `dest` first on sys.path. True when it
    was rebuilt; a hub closed meanwhile is left alone, and a failure is
    printed, never raised (this runs deferred, after the install said so)."""
    if importer is None:
        import importlib
        importer = importlib.import_module
    if dest not in sys.path:
        sys.path.insert(0, dest)
    try:
        hub = importer("maya_hub")
        if not hub.is_open():
            return False
        hub.rebuild()
        return True
    except Exception as exc:                                 # noqa: BLE001
        print("SkeldarAnim: the open hub was not rebuilt ({0}) - press the"
              " SkeldarAnim shelf button".format(exc))
        return False


def onMayaDroppedPythonFile(*args):
    install(args[0] if args else None)
