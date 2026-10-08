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
import tempfile

SHELF = "SkeldarAnim"

# The hub's workspaceControl (maya_hub.CONTROL). Named here, not imported: at
# drop time nothing of ours is on sys.path.
HUB_CONTROL = "skeldarAnimHub"
# The Pose Library's (maya_poselib.window.CONTROL), the same way (2026-10-02).
POSELIB_CONTROL = "skeldarPoseLibrary"
# The hub's edge panel host window (maya_hubedge.HOST), the same way
# (2026-10-08): with the hub at the edge no workspaceControl stands.
HUB_EDGE = "skeldarAnimHubEdge"

# The payload's library folder (2026-10-02): the animator's own cards saved
# into the INSTALLED copy must survive the install that replaces it.
POSES = "poses"
KEPT_PREFIX = "SkeldarAnim_poses_kept_"
# What a build SHIPPED in poses/, card by card (2026-10-03, the final review):
# each shipped card's relative path and its files' sha1, written at install
# and build time from the payload itself. The next install reads it to tell
# the previous build's own cards from the colleague's - a card is ONE unit
# (`<Name>.pose/`), never merged file by file. Its leading dot keeps it out of
# the library's listing (`maya_poselib.store`'s hidden-name rule).
SHIPPED = ".shipped.json"
SHIPPED_FORMAT = "skeldar.shipped"
CARD_SUFFIX = ".pose"               # maya_poselib.store.CARD_SUFFIX
CARD_NAME_MAX = 80                  # maya_poselib.store.NAME_MAX
LOCAL_SUFFIX = " (local)"           # a local card put back beside a shipped one of its name
HALF_WRITTEN = ".part"              # a card file being written (store's atomic writes)
OS_CLUTTER = frozenset(("thumbs.db", "desktop.ini", ".ds_store"))   # no card's files, lower case

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
    "maya_hubsound.py",         # its interface sounds (2026-10-01)
    "maya_hubmotion.py",        # how its cards move (2026-10-01)
    "maya_hubglow.py",          # its controls glowing under the mouse (2026-10-02)
    "maya_edgerules.py",        # the edge panel's rules (2026-10-08)
    "maya_hubedge.py",          # the edge panel's windows (2026-10-08)
    "maya_invlook.py",          # the weapon inventory's look (2026-09-29)
    "maya_inventory.py",        # the weapon inventory: the Weapons card
    "maya_charlook.py",         # the Characters portrait grid's look (2026-09-30)
    "maya_chargrid.py",         # the Characters portrait grid
    "maya_charfire.py",         # its fire under the mouse (2026-10-02)
    "maya_armorgrid.py",        # the Armor card's tiles (2026-10-01)
    "icons",
    "assets",
    "overrig",
    "skeldar_features.py",
    "maya_rigs.py",
    "maya_asretarget.py",
    "maya_pmretarget.py",
    "maya_skeletonmap.py",      # any humanoid convention onto our names (2026-10-02)
    "maya_rig_retarget.py",
    "maya_retargetmode.py",     # rotations or squash & stretch, and the choice (2026-10-02)
    "maya_ikmatch.py",          # the IK limbs take the FK limbs' shape (2026-10-02)
    "maya_graphoverlay",        # the Graph Editor over the viewport (2026-09-30)
    "maya_com",                 # the centre of mass (2026-10-01)
    "maya_poselib",             # the Pose Library (2026-10-02)
    "poses",                    # its shipped library; local cards survive an install
    "maya_update.py",
    "maya_sharerecords.py",     # Shared (2026-09-30): the record, pure
    "maya_sharenet.py",         # its network: litterbox + ntfy.sh
    "maya_share.py",            # the section
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


def _say(message):
    """A line for the Script Editor (a seam: the tests catch it)."""
    print(message)


def _hidden_pose_folder(name):
    """A folder the library never lists (`maya_poselib.store._hidden`): `.git`, `_trash...`."""
    return name.startswith(".") or name.lower().startswith("_trash")


def _is_card(name):
    return name.lower().endswith(CARD_SUFFIX)


def poses_walk(root):
    """(cards, folders, files) of a pose library folder, relative "/" paths, parents first: every
    CARD folder (`<Name>.pose`, never entered - a card is one unit), every other folder, every file
    outside a card. Inside a hidden folder (`.git`, `_trash`: the library lists nothing there)
    everything is a plain file. The shipped manifest and `.part` halves are left out."""
    cards, folders, files = [], [], []
    for base, dirs, names in os.walk(root):
        dirs.sort()
        names.sort()
        rel = os.path.relpath(base, root)
        parts = [] if rel == os.curdir else rel.split(os.sep)
        hidden = any(_hidden_pose_folder(part) for part in parts)
        if not hidden:
            for name in [d for d in dirs if _is_card(d) and not _hidden_pose_folder(d)]:
                cards.append("/".join(parts + [name]))
                dirs.remove(name)
        folders.extend("/".join(parts + [d]) for d in dirs)
        for name in names:
            if name.endswith(HALF_WRITTEN) or (not parts and name == SHIPPED):
                continue
            files.append("/".join(parts + [name]))
    #  sorted as paths: a folder sorts before everything inside it, so parents stay first
    return sorted(cards), sorted(folders), sorted(files)


def _sha1(path):
    import hashlib
    digest = hashlib.sha1()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def card_files(card):
    """{file's relative "/" path: its sha1} of every file of the card folder `card` - a `.part`
    half and the files the OS writes into a folder by itself (`OS_CLUTTER`: Explorer's
    Thumbs.db / desktop.ini) left out, so a shipped card a colleague merely LOOKED at in Explorer
    still reads as the build's."""
    out = {}
    for base, dirs, names in os.walk(card):
        dirs.sort()
        rel = os.path.relpath(base, card)
        parts = [] if rel == os.curdir else rel.split(os.sep)
        for name in sorted(names):
            if not name.endswith(HALF_WRITTEN) and name.lower() not in OS_CLUTTER:
                out["/".join(parts + [name])] = _sha1(os.path.join(base, name))
    return out


def shipped_manifest(poses):
    """The manifest of a build's `poses` folder: {"format", "version", "cards": {relative card
    path: card_files}} - every card the build ships, file by file."""
    cards = {}
    if os.path.isdir(poses):
        for rel in poses_walk(poses)[0]:
            cards[rel] = card_files(os.path.join(poses, *rel.split("/")))
    return {"format": SHIPPED_FORMAT, "version": 1, "cards": cards}


def manifest_text(manifest):
    return json.dumps(manifest, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def write_shipped(poses):
    """`<poses>/.shipped.json` written from what the folder holds now (the build's cards, before
    any local card is put back); the cards it lists ({path: files})."""
    manifest = shipped_manifest(poses)
    target = os.path.join(poses, SHIPPED)
    part = target + HALF_WRITTEN
    with open(part, "w", encoding="utf-8") as handle:
        handle.write(manifest_text(manifest))
    os.replace(part, target)
    return manifest["cards"]


def read_shipped(poses):
    """{relative card path: card_files} of the manifest in `poses`; None when there is none or
    it cannot be read (an install from before 2026-10-03 wrote none)."""
    try:
        with open(os.path.join(poses, SHIPPED), encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):          # valid JSON that is no manifest: [] or null
        return None
    cards = data.get("cards")
    if data.get("format") != SHIPPED_FORMAT or not isinstance(cards, dict):
        return None
    return dict((str(rel), dict(files)) for rel, files in cards.items()
                if isinstance(files, dict))


def _folded(cards):
    """{lower-case relative path: files}: the disk compares names without case."""
    return dict((rel.lower(), files) for rel, files in (cards or {}).items())


def free_card(folder, name, suffix=LOCAL_SUFFIX):
    """The card folder name `<name> (local).pose` free in `folder` - then `<name> (local)
    2.pose` ... - capped at the library's 80 characters (`maya_poselib.store.unique_name`'s
    rule)."""
    number = 1
    while True:
        tail = suffix if number == 1 else "%s %d" % (suffix, number)
        stem = name[:CARD_NAME_MAX - len(tail)].rstrip(". ") + tail
        if not os.path.exists(os.path.join(folder, stem + CARD_SUFFIX)):
            return stem + CARD_SUFFIX
        number += 1


def _rename_inside(card, name):
    """The card's pose.json `name` set to its new folder's (best effort: a card that cannot be
    read keeps its file as it is - the library names a card by its folder anyway)."""
    target = os.path.join(card, "pose.json")
    try:
        with open(target, encoding="utf-8-sig") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            return
        data["name"] = name
        part = target + HALF_WRITTEN
        with open(part, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, separators=(",", ":"))
        os.replace(part, target)
    except (OSError, ValueError):
        pass


class Kept(list):
    """What `keep_local` put back: the relative "/" paths of the local files (the list it always
    answered), and `renamed` {local card: where it went beside a shipped card of its name},
    `dropped` [the previous build's own cards the new build no longer ships], `unrestored`
    [what could not go back - the aside folder is then kept], `aside` (that folder, or "")."""

    def __init__(self, items=()):
        list.__init__(self, items)
        self.renamed = {}
        self.dropped = []
        self.unrestored = []
        self.aside = ""


def keep_local(old, new, new_cards=None):
    """The old installed `poses` (`old`, only read) put back into the new build's (`new`), CARD by
    CARD (2026-10-03, the final review: a file-by-file merge glued a colleague's thumbnail onto
    a shipped pose and threw their own pose.json away with the aside folder).

    The previous build's manifest (`old/.shipped.json`) says which cards IT shipped. A card
    still byte-identical to its manifest entry is the build's - the new build decides: it
    carries it, or it renamed, moved or deleted it upstream (`new_cards`, the new build's
    manifest, says which; that card is then `dropped`, never brought back). Every other card is
    LOCAL - absent from the old manifest, or changed since (Update from selection, Replace
    thumbnail) - and goes back WHOLE at its place; where the new build holds a card of that path
    (case-insensitively, as the disk compares) it goes back BESIDE it, `<Name> (local).pose`
    (`free_card`), never mixed into it - unless it is the very same files. `new_cards` None (the
    new build's poses never arrived: the copy failed half way) drops nothing and puts every
    card back where the new build has none.

    Folders come along (a catalog made and not filled yet), and files outside cards when the new
    build has none of that path; a file of the new build in the way of a folder, or a different
    file at the same path, leaves that part `unrestored`. Returns a `Kept`."""
    result = Kept()
    shipped = _folded(read_shipped(old))
    built = None if new_cards is None else _folded(new_cards)
    cards, folders, files = poses_walk(old)

    def parent_ready(rel):
        folder = os.path.dirname(os.path.join(new, *rel.split("/")))
        if os.path.isdir(folder):
            return True
        if os.path.exists(folder):
            return False
        try:
            os.makedirs(folder)
        except OSError:
            return False
        return True

    for rel in folders:
        target = os.path.join(new, *rel.split("/"))
        if os.path.isdir(target):
            continue
        if os.path.exists(target) or not parent_ready(rel):
            result.unrestored.append(rel + "/")
            continue
        os.makedirs(target)
    for rel in cards:
        source = os.path.join(old, *rel.split("/"))
        files_now = card_files(source)
        target = os.path.join(new, *rel.split("/"))
        if shipped.get(rel.lower()) == files_now:
            if built is not None and rel.lower() not in built:
                result.dropped.append(rel)
                continue
            if built is not None or os.path.exists(target):
                continue                     # the build's own card: the new build's stands
        placed = rel
        if os.path.exists(target):
            if os.path.isdir(target) and card_files(target) == files_now:
                continue                     # the very same card the new build ships
            folder = os.path.dirname(target)
            name = os.path.basename(rel)[:-len(CARD_SUFFIX)]
            if not os.path.isdir(folder):
                result.unrestored.append(rel)
                continue
            placed = "/".join(rel.split("/")[:-1] + [free_card(folder, name)])
            result.renamed[rel] = placed
        if not parent_ready(placed):
            result.unrestored.append(rel)
            continue
        destination = os.path.join(new, *placed.split("/"))
        shutil.copytree(source, destination)
        if placed != rel:
            _rename_inside(destination, os.path.basename(placed)[:-len(CARD_SUFFIX)])
        result.extend(placed + "/" + name for name in sorted(files_now))
    for rel in files:
        target = os.path.join(new, *rel.split("/"))
        source = os.path.join(old, *rel.split("/"))
        if os.path.exists(target):
            if not (os.path.isfile(target) and _sha1(target) == _sha1(source)):
                result.unrestored.append(rel)
            continue
        if not parent_ready(rel):
            result.unrestored.append(rel)
            continue
        shutil.copy2(source, target)
        result.append(rel)
    manifest = os.path.join(old, SHIPPED)
    if built is None and os.path.isfile(manifest) and os.path.isdir(new) \
            and not os.path.exists(os.path.join(new, SHIPPED)):
        #  the new build's poses never arrived: the old install stands back as it was, its
        #  manifest with it, so the next install still knows which cards were the build's
        shutil.copy2(manifest, os.path.join(new, SHIPPED))
    return result


def _put_back_poses(aside, dest, new_cards=None):
    """The local poses moved aside into `aside` put back under `dest` (`keep_local`); the temp
    folder is removed only once EVERY local file is back. A card put beside a shipped one of its
    name, and anything that could not go back, is said (the Script Editor, and `Kept` for the
    install's dialog) with where the aside folder is. A failure never raises (this runs in
    copy_payload's `finally`, where it would hide the copy's own error) and never deletes
    them: it says where they are."""
    old = os.path.join(aside, POSES)
    where = old.replace("\\", "/")
    try:
        kept = keep_local(old, os.path.join(dest, POSES), new_cards)
    except Exception as exc:                                 # noqa: BLE001
        _say("SkeldarAnim: the local poses were not put back ({0}) - they are kept in"
             " {1}".format(exc, where))
        failed = Kept()
        failed.unrestored = ["poses"]
        failed.aside = where
        return failed
    for rel, placed in sorted(kept.renamed.items()):
        _say("SkeldarAnim: your pose card {0} has the name of a card this build ships - it is"
             " kept beside it as {1}".format(rel, placed))
    if kept.unrestored:
        kept.aside = where
        _say("SkeldarAnim: {0} local pose file(s) could not go back ({1}) - they are kept in"
             " {2}".format(len(kept.unrestored), ", ".join(kept.unrestored[:4]), where))
        return kept
    shutil.rmtree(aside, ignore_errors=True)
    return kept


def poses_note(kept):
    """The install dialog's lines about the local poses: renamed cards and a kept aside folder;
    "" when there is nothing to say."""
    if not isinstance(kept, Kept):
        return ""
    lines = []
    if kept.renamed:
        lines.append("{0} local pose card(s) had a shipped card's name and were kept beside it"
                     " as \"<Name> (local)\".".format(len(kept.renamed)))
    if kept.aside:
        lines.append("Some local poses could not go back - they are kept in\n{0}".format(
            kept.aside))
    return "\n".join(lines)


def copy_payload(src_root, dest):
    """The whitelist into `dest`, replacing whatever was there - all but the poses the animator
    saved into the installed library (2026-10-02, the Pose Library: local poses survive every
    install).

    The installed `poses/` is RENAMED aside first, into a temp folder beside `dest`: the same
    volume, so nothing is copied, and a rename that fails (a file held open) raises with nothing
    moved or deleted - `shutil.move` would fall back to copy-then-delete, and a delete failing
    half way leaves the only whole copy in the temp folder. Then the folder is replaced, the new
    build's cards recorded in `poses/.shipped.json` (`write_shipped`: what THIS build shipped,
    read by the next install), then `keep_local` puts the local cards back, card by card. The
    poses go back even when the copy itself fails half way (trap 113: a payload row the source
    does not hold) - that error then goes on, and with no new manifest nothing is dropped.
    Returns `keep_local`'s `Kept`.
    """
    aside = None
    old_poses = os.path.join(dest, POSES)
    if os.path.isdir(old_poses):
        aside = tempfile.mkdtemp(prefix=KEPT_PREFIX,
                                 dir=os.path.dirname(os.path.abspath(dest)))
        try:
            os.rename(old_poses, os.path.join(aside, POSES))
        except OSError:
            os.rmdir(aside)                  # still empty: nothing was moved
            raise
    kept = Kept()
    new_cards = None
    try:
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        os.makedirs(dest)
        ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "*" + HALF_WRITTEN)
        for name in payload():
            src = os.path.join(src_root, name)
            target = os.path.join(dest, name)
            if os.path.isdir(src):
                shutil.copytree(src, target, ignore=ignore)
            else:
                shutil.copy2(src, target)
            if name == POSES and os.path.isdir(target):
                new_cards = write_shipped(target)
    finally:
        if aside is not None:
            kept = _put_back_poses(aside, dest, new_cards)
    return kept


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


def _edge_standing():
    """The hub's edge panel stands (2026-10-08): its host window, found by
    name among Qt's top-level widgets - the hub's module is not asked (the
    install has just purged it). False without PySide6 (Maya before 2025)
    or a QApplication (mayapy)."""
    try:
        from PySide6 import QtWidgets
    except ImportError:
        return False
    app = QtWidgets.QApplication.instance()
    if app is None:
        return False
    return any(widget.objectName() == HUB_EDGE
               for widget in app.topLevelWidgets())


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
    kept = None
    if not same_place(src, dest):
        kept = copy_payload(src, dest)
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
    # The edge panel (2026-10-08) is the hub's other home: no workspaceControl
    # stands then, its host window does, and the fresh maya_hub.rebuild()
    # knows which home it is rebuilding.
    hub_open = (bool(cmds.workspaceControl(HUB_CONTROL, exists=True))
                or _edge_standing())
    target = dest.replace("\\", "/")
    if hub_open:
        cmds.evalDeferred(lambda: rebuild_open_hub(target),
                          lowestPriority=True)
    # The Pose Library's window is a control of its own (2026-10-02): the same
    # staleness, the same deferred rebuild.
    poses_open = bool(cmds.workspaceControl(POSELIB_CONTROL, exists=True))
    if poses_open:
        cmds.evalDeferred(lambda: rebuild_open_poselib(target),
                          lowestPriority=True)
    if not quiet:
        note = ""
        if reloaded:
            rebuilt = [name for name, is_open in (("SkeldarAnim hub", hub_open),
                                                  ("Pose Library", poses_open))
                       if is_open]
            then = ("The open {0} {1} rebuilt from\nthe new one;"
                    " restart Maya if anything still\nlooks old.".format(
                        " and ".join(rebuilt), "is" if len(rebuilt) == 1 else "are")
                    if rebuilt else
                    "Close any of our panels that\nare open and reopen them"
                    " from the shelf; restart\nMaya if anything still looks"
                    " old.")
            note = ("\n\nThe previous version was loaded in this session"
                    "\n({0} modules dropped). {1}".format(len(reloaded),
                                                          then))
        poses = poses_note(kept)
        if poses:
            note += "\n\n" + poses
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


def rebuild_open_poselib(dest, importer=None):
    """The Pose Library's window rebuilt inside its standing control from the FRESH
    maya_poselib.window -- the installed copy's, `dest` first on sys.path -- as
    `rebuild_open_hub` does the hub (2026-10-02). True when it was rebuilt; a window closed
    meanwhile is left alone, and a failure is printed, never raised (this runs deferred)."""
    if importer is None:
        import importlib
        importer = importlib.import_module
    if dest not in sys.path:
        sys.path.insert(0, dest)
    try:
        window = importer("maya_poselib.window")
        if not window.is_open():
            return False
        window.rebuild()
        return True
    except Exception as exc:                                 # noqa: BLE001
        print("SkeldarAnim: the open Pose Library was not rebuilt ({0}) - close it and open it"
              " again from the hub".format(exc))
        return False


def onMayaDroppedPythonFile(*args):
    install(args[0] if args else None)
