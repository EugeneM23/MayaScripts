"""The Pose Library's Save (2026-10-02): a pose dict built from the scene, and its thumbnail.

The animator: «если анимация относится к ригу то мы должны сохранять анимацию не контроллов а
костей». So a CHARACTER pose holds the BONES of one character (`scene.skeleton`: every bone, for
recognising the skeleton later, with the members the selection names), and on a rig source also
each unrolled limb bone's DRIVE - the bone as the rig's drive chain holds it, with the roll
AdvancedSkeleton moved into the twist joints put back (`rigsolve.drive_matrices`, trap 126), read
with the skeleton (`scene.skeleton`). Anything selected that is no character's makes an OBJECTS
pose instead: Studio Library's attribute pose, every keyable scalar unlocked attribute of each
selected transform.

`build_pose` refuses two characters at once («pick one character for a pose») - a card is the
bones of ONE skeleton; objects selected beside one character are left out of its pose, and the
note says so. `regions` are the save panel's chips: a chip the selection lit and the animator kept
keeps those members, one turned off drops them, and one turned ON that the selection did not
touch brings that region in whole (`region_members`) - so a chip always means what it shows.

Measured (2026-10-02, mayapy standalone): a pose of Manny_Rig reads in 0.13-0.17 s and is 57-61
KB of JSON (93 bones x rest + world, drives on the eight unrolled limb bones);
`build_pose(frame=12)` from frame 5 reads frame 12 and leaves the time at 5.

**The thumbnail** (`thumbnail`) is a playblast of the panel the animator looks at
(`maya_vpstudio.active_panel`), at its own port size (WYSIWYG for their camera), with the curves,
joints, locators, the clip labels (dimensions), the grid, the HUD, the manipulators and the
selection highlight switched off for the blast and put back (each queried first); centre-cropped
square, scaled to 640 px (320 until 2026-10-03, when a card under the mouse began to grow twice
its size), JPG. Viewport 2.0 loads textures while Maya is IDLE (trap 120): the
blast is repeated with idle events pumped between until two in a row are byte-identical - at least
three blasts (trap 120 measured two early blasts agreeing on a half-loaded texture), at most five.
Batch mode or no model panel: `(False, "no viewport for a thumbnail")`. Qt is imported inside
`thumbnail` only, so importing this module drags none in.

Spec: docs/superpowers/specs/2026-10-02-pose-library-design.md ("Save")
"""

import contextlib
import getpass
import os
import tempfile
import time

import maya.cmds as cmds

from maya_poselib import keys
from maya_poselib import scene
from maya_poselib import store

AUTHOR_VAR = "skeldarShareName"   # maya_share.AUTHOR_VAR: who the Shared card says is sending
HIDDEN = ("nurbsCurves", "joints", "locators", "dimensions", "grid", "manipulators",
          "headsUpDisplay", "selectionHiliteDisplay", "handles", "ikHandles", "deformers",
          "motionTrails", "cameras", "lights", "follicles", "nParticles")
THUMB_SIZE = 640
JPG_QUALITY = 92                  # the card's thumbnail
BLAST_QUALITY = 95                # the raw blast it is cut from
LEAST_BLASTS, MOST_BLASTS = 3, 5
SMALLEST_PORT = 16                # px: a port smaller than this is a hidden window (trap 105)
NO_VIEWPORT = "no viewport for a thumbnail"
NO_BONE = "no bone of %s in the pose of %s"


# ------------------------------------------------------------------ pure

def region_members(bones, members, regions):
    """The members a card holds once the region chips are read, in skeleton order.

    `regions` None: the members as they are. Otherwise a member stays when its region
    (`scene.bone_regions`) is one of `regions`; a region in `regions` that NO member touches
    comes in whole (its bones of `scene.whole_body`). An empty list leaves nothing."""
    if regions is None:
        return list(members)
    wanted = set(regions)
    region = scene.bone_regions(bones)
    present = set(members)
    touched = set(region.get(m) for m in present)
    kept = set(m for m in present if region.get(m) in wanted)
    kept.update(b for b in scene.whole_body(bones)
                if region.get(b) in wanted and region.get(b) not in touched)
    return [b for b in bones if b in kept]


def square(width, height):
    """(x, y, side) of the largest square centred in a `width` x `height` picture."""
    side = min(width, height)
    return (width - side) // 2, (height - side) // 2, side


def settle(blast, pump, least=LEAST_BLASTS, most=MOST_BLASTS):
    """(picture, blasts taken, settled): `blast()` repeated, `pump()` between, until two in a row
    agree after at least `least`; at most `most`, the last one then answered unsettled."""
    previous, count = None, 0
    while True:
        picture = blast()
        count += 1
        if count >= least and picture == previous:
            return picture, count, True
        if count >= most:
            return picture, count, False
        previous = picture
        pump()


# ------------------------------------------------------------------ the card's common fields

def author():
    """Who saves the card: the name the Shared card goes by (`skeldarShareName`), else the
    Windows user."""
    try:
        if cmds.optionVar(exists=AUTHOR_VAR):
            name = (cmds.optionVar(query=AUTHOR_VAR) or "").strip()
            if name:
                return name
    except Exception:                                        # noqa: BLE001
        pass
    try:
        return getpass.getuser()
    except Exception:                                        # noqa: BLE001
        return os.environ.get("USERNAME", "")


def _common(kind):
    path = cmds.file(query=True, sceneName=True) or ""
    return {"format": store.FORMAT, "version": store.VERSION, "kind": kind, "name": "Pose",
            "created": time.strftime("%Y-%m-%dT%H:%M:%S"), "author": author(),
            "scene": os.path.basename(path), "frame": float(cmds.currentTime(query=True)),
            "fps": cmds.currentUnit(query=True, time=True)}


@contextlib.contextmanager
def _at(frame):
    """The scene at `frame` for the length of the block (a real time change: a constrained bone
    read with `getAttr(time=)` does not follow its rig, trap 69), the time put back after."""
    now = cmds.currentTime(query=True)
    if frame is None or abs(float(frame) - now) < 1e-9:
        yield now
        return
    tweaks = keys.Tweaks()          # coming back re-evaluates the frame: its tweaks put back
    cmds.currentTime(frame)
    try:
        yield frame
    finally:
        cmds.currentTime(now)
        tweaks.restore()


# ------------------------------------------------------------------ the poses

def character_pose(ref, nodes, regions=None):
    """(data, note): the pose of the character `ref` as `nodes` (the selection's parts of it)
    name its bones, narrowed by `regions` when given; (None, refusal) when nothing is left. A
    rig's drives come with its skeleton (`scene.skeleton`: `rigsolve.drive_matrices`)."""
    notes = []
    bones, convention = scene.skeleton(ref, notes)
    members = scene.members_of(ref, nodes, bones)
    members = region_members(bones, members, regions)
    if not members:
        return None, NO_BONE % (", ".join(regions or ()) or "the selection", ref.label)
    records = {}
    for name, bone in bones.items():
        record = {"parent": bone["parent"], "canonical": bone["canonical"],
                  "rest": bone["rest"], "world": bone["world"],
                  "rotateOrder": bone["rotateOrder"]}
        if bone.get("drive"):
            record["drive"] = bone["drive"]
        records[name] = record
    data = _common("character")
    data.update({"character": scene.identity(ref, convention), "bones": records,
                 "members": members, "regions": scene.regions_of(bones, members),
                 "objects": []})
    line = "%s: %d of %d bones" % (scene.describe([ref], []), len(members), len(bones))
    if data["regions"]:
        line += " - " + ", ".join(data["regions"])
    return data, " | ".join([line] + notes)


def objects_pose(nodes):
    """The objects pose of `nodes` (transforms; a shape or component names its transform): per
    object its leaf name without the namespace, its long path, and the value of every keyable,
    scalar, unlocked attribute. An attribute that cannot be read is left out."""
    objects, seen = [], set()
    for node in nodes or ():
        path = scene.dag_object(node)
        if path is None or path in seen:
            continue
        seen.add(path)
        attrs = {}
        for attr in cmds.listAttr(path, keyable=True, scalar=True, unlocked=True) or []:
            try:
                value = cmds.getAttr(path + "." + attr)
            except (RuntimeError, ValueError):
                continue
            if isinstance(value, (bool, int, float)):
                attrs[attr] = float(value)
        objects.append({"name": scene.leaf(path), "path": path, "attrs": attrs})
    data = _common("objects")
    data["objects"] = objects
    return data


def build_pose(selection=None, regions=None, frame=None):
    """(data, note): the pose the selection makes at `frame` (the current frame when None) - a
    character pose when it touches exactly one character, else an objects pose of its
    transforms, else (None, "select a character or objects"). Two characters: (None, "pick one
    character for a pose")."""
    with _at(frame):
        resolved = scene.resolve(selection)
        refs, loose = [], []
        for path, ref in resolved:
            if ref is None:
                loose.append(path)
            elif all(r.root != ref.root for r in refs):
                refs.append(ref)
        if len(refs) > 1:
            return None, scene.MANY
        if refs:
            nodes = [path for path, ref in resolved if ref is not None]
            data, note = character_pose(refs[0], nodes, regions)
            if data is not None and loose:
                note += " | %s outside %s left out" % (scene.describe([], loose), refs[0].label)
            return data, note
        if loose:
            data = objects_pose(loose)
            return data, scene.describe([], loose)
        return None, scene.NOTHING


# ------------------------------------------------------------------ the thumbnail

def _port(panel):
    """(width, height) of a model panel's port, or None."""
    import maya.api.OpenMayaUI as omui
    try:
        view = omui.M3dView.getM3dViewFromModelPanel(panel)
        return view.portWidth(), view.portHeight()
    except RuntimeError:
        return None


def thumbnail(path, size=THUMB_SIZE):
    """(ok, note): the active model panel blasted at the current frame into a `size` px square
    JPG at `path` (written atomically). Batch mode, no panel, a hidden port: (False, why)."""
    if cmds.about(batch=True):
        return False, NO_VIEWPORT
    import maya_vpstudio
    panel = maya_vpstudio.active_panel()
    port = _port(panel) if panel else None
    if not port:
        return False, NO_VIEWPORT
    width, height = port
    if width < SMALLEST_PORT or height < SMALLEST_PORT:
        return False, "the viewport is %dx%d - too small for a thumbnail" % (width, height)
    import maya_hubqt
    qt = maya_hubqt.qt()
    if qt is None:
        return False, "no Qt for a thumbnail"
    import maya.utils
    raw = os.path.join(tempfile.gettempdir(),
                       "skeldar_pose_thumbnail_%d.jpg" % os.getpid()).replace("\\", "/")
    shown = {}
    for flag in HIDDEN:
        try:
            shown[flag] = cmds.modelEditor(panel, query=True, **{flag: True})
        except Exception:                                    # noqa: BLE001
            continue

    def blast():
        cmds.refresh(force=True)
        cmds.playblast(frame=[cmds.currentTime(query=True)], format="image", compression="jpg",
                       quality=BLAST_QUALITY, completeFilename=raw, widthHeight=(width, height),
                       percent=100, viewer=False, showOrnaments=False, offScreen=True,
                       forceOverwrite=True, clearCache=True, editorPanelName=panel)
        with open(raw, "rb") as handle:
            return handle.read()

    def pump():
        maya.utils.processIdleEvents()
        qt.QtWidgets.QApplication.processEvents()

    #  a playblast steps the time to its frame - the current one - and may re-evaluate it, which
    #  throws away the animator's unkeyed tweaks on keyed channels; Save reads the pose AFTER the
    #  snapshot, so they are read first and set back (a GUI Maya only: not measured here, mayapy
    #  has no viewport to blast - the final review asked)
    tweaks = keys.Tweaks()
    try:
        for flag in shown:
            try:
                cmds.modelEditor(panel, edit=True, **{flag: False})
            except Exception:                                # noqa: BLE001
                pass
        _picture, count, settled = settle(blast, pump)
    finally:
        for flag, value in shown.items():
            try:
                cmds.modelEditor(panel, edit=True, **{flag: value})
            except Exception:                                # noqa: BLE001
                pass
        tweaks.restore()
    try:
        ok, note = square_jpg(qt, raw, path, size)
    finally:
        try:
            os.remove(raw)
        except OSError:
            pass
    if not ok:
        return False, note
    return True, "thumbnail from %s (%dx%d, %d blast%s%s)" % (
        panel, width, height, count, "" if count == 1 else "s",
        "" if settled else ", textures still loading")


def square_jpg(qt, source, path, size=THUMB_SIZE):
    """(ok, note): the picture at `source` centre-cropped square (`square`), scaled to `size` px
    with smooth filtering and written as a JPG at `path` - through `path + ".part"` and
    `os.replace`, so a reader never sees half a file. `qt` is `maya_hubqt.qt()` (a QImage needs no
    QApplication)."""
    image = qt.QtGui.QImage(source)
    if image.isNull():
        return False, "the playblast wrote nothing readable"
    x, y, side = square(image.width(), image.height())
    small = image.copy(x, y, side, side).scaled(
        size, size, qt.QtCore.Qt.IgnoreAspectRatio, qt.QtCore.Qt.SmoothTransformation)
    part = path + ".part"
    try:
        if not small.save(part, "JPG", JPG_QUALITY):
            return False, "could not write " + path
        os.replace(part, path)
    finally:
        try:
            os.remove(part)
        except OSError:
            pass
    return True, ""
