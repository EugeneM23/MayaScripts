"""The camera and the weapon bones on a card (2026-10-20): which of them a card applies, and how
each is written.

The animator: «Наша библиотека поз должна воспринимать камеру и оружие как часть рига и анимация
должна сохраняться для камеры и оружия автоматически ... мы не должны запоминать какое именно оружие
у нас в руках и записывать анимацию для него мы должны все делать через наши weapon_bone».

A card holds every bone of its skeleton, the four helpers too (`HELPERS`). Which of them an Apply
writes (`members_with`, pure, on the CARD's members - so every card made before applies them):
`weapon_r` with `hand_r`, `weapon_l` with `hand_l`, `camera_root` and `camera_bone` with a card on
the whole body (`scene.whole_body`). The body solvers never see them (`split`); a `Writer` does.

How a helper is written (`Writer`, prepared once per target, `solve` per frame):

- **free**: its own joint channels, rotate (`skelsolve.joint_channels`, nearest the seed or what it
  shows) and translate, its local read against its PARENT's target - the parent's solve may land a
  hair off, and the relation in the hand is what the card holds;
- **our weapon drives it** (`bonedrive.driving_weapon`: a weapon in a hand, or out on the floor):
  the WEAPON is keyed - whatever weapon it is; the card holds the bone. `K = W_bone · W_weapon⁻¹` is
  measured when the press begins (the link's constraint offset: constant), so the weapon must stand
  at `K⁻¹ · W_bone_wanted`, under its parent carried by the hand its weapon space follows
  (`P · W_hand_now⁻¹ · W_hand_wanted`) or standing still (the floor). Its channels keep its pivots,
  shear and scale (`driver_channels`);
- **our camera drives it** (`camera.camera_for`, Camera Setup): the camera is keyed the same way;
- **the hands ride that weapon** (Connections, `connections.followers_of`): skipped and said -
  keying the weapon would move the hands;
- **anything else drives it**: skipped and named (`keys.writable`).

After a press that keyed a free `camera_root` on a character with no Camera Setup, the camera is set
up on it (`camera_to_set_up`, `set_up_camera`: the animator's «если у нас в каких-то ригах нету
камеры то ее нужно добавить»).

Spec: docs/superpowers/specs/2026-10-20-camera-and-weapon-bones-design.md
"""

from collections import OrderedDict, namedtuple

import maya.api.OpenMaya as om
import maya.cmds as cmds

from maya_poselib import keys
from maya_poselib import posemath as pm
from maya_poselib import skelsolve

HELPERS = ("weapon_r", "weapon_l", "camera_root", "camera_bone")
CARRIERS = (("weapon_r", "hand_r"), ("weapon_l", "hand_l"))
CAMERA = ("camera_root", "camera_bone")
CAMERA_ROOT = "camera_root"
ROTATE = ("rotateX", "rotateY", "rotateZ")
TRANSLATE = ("translateX", "translateY", "translateZ")

THROUGH = "%s keyed through %s"
FOLLOWED = "%s skipped: the hands ride %s (Connections)"
CAMERA_SET = "camera set up on %s"
CAMERA_FAILED = "camera not set up on %s: %s"

# leaf, path, mode ("joint" | "driver"), driver path, K (W_bone · W_driver⁻¹), carrier leaf
Entry = namedtuple("Entry", "leaf path mode driver K carrier")


def _bare(leaf):
    return (leaf or "").split(":")[-1]


def is_helper(leaf):
    """One of OUR four helper bones (a namespace ignored)? `ik_*` and the rest are not."""
    return _bare(leaf) in HELPERS


# ------------------------------------------------------------------- pure

def members_with(members, bones, whole=None):
    """The card's members with the helpers its parts bring (pure): `weapon_r` with `hand_r`,
    `weapon_l` with `hand_l`, `camera_root` / `camera_bone` when the members hold every bone of
    `whole` (the whole body - `scene.whole_body(bones)` when not given). Only bones `bones` holds;
    never twice; the members' own order first."""
    members = list(members or ())
    have = set(members)
    out = list(members)
    for helper, carrier in CARRIERS:
        if carrier in have and helper in bones and helper not in have:
            out.append(helper)
            have.add(helper)
    if whole is None:
        from maya_poselib import scene
        whole = scene.whole_body(bones)
    whole = list(whole or ())
    if whole and set(whole) <= have:
        for helper in CAMERA:
            if helper in bones and helper not in have:
                out.append(helper)
                have.add(helper)
    return out


def split(members):
    """(body, helpers): the members the body solvers take, and our helper bones."""
    body = [m for m in members or () if not is_helper(m)]
    return body, [m for m in members or () if is_helper(m)]


def driver_target(K, wanted):
    """Where the driver must stand for its bone to stand at `wanted`: `K⁻¹ · wanted`."""
    return om.MMatrix(K).inverse() * pm.matrix(wanted)


def carried_parent(parent_now, carrier_now, carrier_wanted):
    """The driver's parent's world once its carrier stands at `carrier_wanted`: `P · C_now⁻¹ ·
    C_wanted` (a weapon space follows its hand); `parent_now` when nothing carries it."""
    if carrier_now is None or carrier_wanted is None:
        return pm.matrix(parent_now)
    return pm.matrix(parent_now) * pm.matrix(carrier_now).inverse() * pm.matrix(carrier_wanted)


def driver_channels(local, attrs, current):
    """(rotate, translate) of a transform for its local matrix `local` (pure, OpenMaya).

    `attrs` holds the transform's rotateOrder, rotateAxis, scale, shear, rotatePivot,
    rotatePivotTranslate, scalePivot and scalePivotTranslate as it stands - all kept. The rotate
    is `RA⁻¹ · rot(local)` in its order nearest `current`; the translate the rest of `local`'s
    place once the pivots and scale have put theirs: `pos(local) - pos(X)`, X the transform's
    matrix with the new rotate and no translate."""
    rotate = skelsolve.joint_channels(local, (0, 0, 0), attrs.get("rotateAxis") or (0, 0, 0),
                                      attrs.get("rotateOrder", 0), current)
    tm = om.MTransformationMatrix()
    tm.setScale(list(attrs.get("scale") or (1, 1, 1)), om.MSpace.kTransform)
    tm.setShear(list(attrs.get("shear") or (0, 0, 0)), om.MSpace.kTransform)
    tm.setScalePivot(om.MPoint(*(attrs.get("scalePivot") or (0, 0, 0))), om.MSpace.kTransform,
                     False)
    tm.setScalePivotTranslation(om.MVector(*(attrs.get("scalePivotTranslate") or (0, 0, 0))),
                                om.MSpace.kTransform)
    tm.setRotatePivot(om.MPoint(*(attrs.get("rotatePivot") or (0, 0, 0))), om.MSpace.kTransform,
                      False)
    tm.setRotatePivotTranslation(om.MVector(*(attrs.get("rotatePivotTranslate") or (0, 0, 0))),
                                 om.MSpace.kTransform)
    ra = om.MEulerRotation(*[v * 3.141592653589793 / 180.0
                             for v in (attrs.get("rotateAxis") or (0, 0, 0))])
    tm.setRotationOrientation(ra.asQuaternion())
    euler = om.MEulerRotation(*([v * 3.141592653589793 / 180.0 for v in rotate] +
                                [int(attrs.get("rotateOrder", 0))]))
    tm.setRotation(euler)
    x = tm.asMatrix()
    t = pm.position(pm.matrix(local)) - pm.position(x)
    return rotate, (t.x, t.y, t.z)


# ------------------------------------------------------------------ scene seams

def _world(node):
    return om.MMatrix(cmds.getAttr(node + ".worldMatrix[0]"))


def _parent_world(node):
    return om.MMatrix(cmds.getAttr(node + ".parentMatrix[0]"))


def _get(plug):
    return float(cmds.getAttr(plug))


def _attrs(node):
    def v3(attr):
        return [float(v) for v in cmds.getAttr(node + "." + attr)[0]]
    return {"rotateOrder": int(cmds.getAttr(node + ".rotateOrder")),
            "rotateAxis": v3("rotateAxis"), "scale": v3("scale"), "shear": v3("shear"),
            "rotatePivot": v3("rotatePivot"), "rotatePivotTranslate": v3("rotatePivotTranslate"),
            "scalePivot": v3("scalePivot"), "scalePivotTranslate": v3("scalePivotTranslate")}


def _weapon_of(path):
    try:
        from maya_scenesetup import bonedrive
    except ImportError:
        return None
    return bonedrive.driving_weapon(path)


def _camera_of(path):
    try:
        from maya_scenesetup import camera
    except ImportError:
        return None
    return camera.camera_for(path)


def _followers(weapon):
    try:
        from maya_scenesetup import connections
    except ImportError:
        return []
    return connections.followers_of(weapon)


def _carrier_of(driver):
    """The joint whose weapon space carries `driver`, or None (the floor, a camera)."""
    try:
        from maya_scenesetup import weaponspace
    except ImportError:
        return None
    return weaponspace.holding_hand(driver)


def _leaf(path):
    return _bare((path or "").split("|")[-1])


class Writer(object):
    """The helper members of one target, prepared once (`__init__`: what drives each, its
    constant offset), solved per frame (`solve`)."""

    def __init__(self, ref, bones, leaves):
        self.ref, self.bones = ref, bones
        self.entries = []
        self.notes = []
        self.skipped = OrderedDict()
        for leaf in skelsolve.parents_first(bones, [l for l in leaves or () if l in bones]):
            entry = self._prepare(leaf, bones[leaf]["path"])
            if entry is not None:
                self.entries.append(entry)

    def _prepare(self, leaf, path):
        weapon = _weapon_of(path)
        driver = weapon or _camera_of(path)
        if driver:
            if weapon and _followers(weapon):
                self.notes.append(FOLLOWED % (leaf, _leaf(weapon)))
                self.skipped[leaf] = "the hands ride %s" % _leaf(weapon)
                return None
            why = self._unwritable(driver)
            if why:
                self.skipped[leaf] = "%s %s" % (_leaf(driver), why)
                return None
            carrier = _carrier_of(driver) if weapon else None
            carrier_leaf = _leaf(carrier) if carrier else None
            if carrier_leaf not in self.bones:
                carrier_leaf = None
            K = _world(path) * _world(driver).inverse()
            self.notes.append(THROUGH % (leaf, _leaf(driver)))
            return Entry(leaf, path, "driver", driver, K, carrier_leaf)
        why = self._unwritable(path)
        if why:
            self.skipped[leaf] = why
            return None
        return Entry(leaf, path, "joint", None, None, None)

    @staticmethod
    def _unwritable(node):
        for channel in ROTATE + TRANSLATE:
            ok, why = keys.writable("%s.%s" % (node, channel))
            if not ok:
                return "%s %s" % (channel, why)
        return ""

    def leaves(self):
        return [e.leaf for e in self.entries]

    def camera_to_set_up(self):
        """camera_root's path when a press keys it free (no Camera Setup drives it), else None."""
        for entry in self.entries:
            if entry.leaf == CAMERA_ROOT and entry.mode == "joint":
                return entry.path
        return None

    @staticmethod
    def _current(plugs, seed):
        if seed and all(p in seed for p in plugs):
            return [float(seed[p]) for p in plugs]
        return [_get(p) for p in plugs]

    def solve(self, wanted, seed=None):
        """skelsolve.Solution: the FINAL values of every prepared helper's plugs for `wanted`
        ({leaf: matrix}, every target bone). A helper `wanted` does not name is left alone."""
        values = OrderedDict()
        for entry in self.entries:
            want = wanted.get(entry.leaf)
            if want is None:
                continue
            want = pm.matrix(want)
            bone = self.bones[entry.leaf]
            parent = bone.get("parent")
            parent_wanted = pm.matrix(wanted[parent]) if parent in wanted else None
            if entry.mode == "joint":
                parent_world = parent_wanted if parent_wanted is not None else \
                    _parent_world(entry.path)
                local = want * parent_world.inverse()
                plugs = ["%s.%s" % (entry.path, ch) for ch in ROTATE]
                rotate = skelsolve.joint_channels(
                    local, bone.get("jointOrient") or (0, 0, 0), bone.get("rotateAxis") or (0, 0, 0),
                    bone.get("rotateOrder", 0), self._current(plugs, seed))
                t = pm.position(local)
                translate = (t.x, t.y, t.z)
                node = entry.path
            else:
                node = entry.driver
                target = driver_target(entry.K, want)
                carrier_now = carrier_wanted = None
                if entry.carrier is not None:
                    carrier_now = _world(self.bones[entry.carrier]["path"])
                    carrier_wanted = wanted.get(entry.carrier)
                parent_new = carried_parent(_parent_world(node), carrier_now, carrier_wanted)
                local = target * parent_new.inverse()
                plugs = ["%s.%s" % (node, ch) for ch in ROTATE]
                rotate, translate = driver_channels(local, _attrs(node),
                                                    self._current(plugs, seed))
            for channel, value in zip(ROTATE, rotate):
                values["%s.%s" % (node, channel)] = value
            for channel, value in zip(TRANSLATE, translate):
                values["%s.%s" % (node, channel)] = value
        return skelsolve.Solution(values, list(self.notes), dict(self.skipped))


def merged(body, helper):
    """One skelsolve.Solution of the body's and the helpers' (the body's first)."""
    values = OrderedDict(body.values)
    values.update(helper.values)
    notes = list(body.notes) + [n for n in helper.notes if n not in body.notes]
    skipped = dict(body.skipped)
    skipped.update(helper.skipped)
    return skelsolve.Solution(values, notes, skipped)


def _span(bone):
    try:
        from maya_scenesetup import bonedrive
    except ImportError:
        return None
    times = cmds.keyframe(bone, query=True, timeChange=True) or []
    return bonedrive.union_range(cmds.playbackOptions(query=True, min=True),
                                 cmds.playbackOptions(query=True, max=True), times)


def set_up_camera(bone):
    """Camera Setup on `bone` (a free camera_root a press keyed) over the playback range and the
    bone's keys, as the button; the line to say, "" when it is already set up or None."""
    if not bone or not cmds.objExists(bone) or _camera_of(bone):
        return ""
    selection = cmds.ls(selection=True, long=True) or []
    try:
        from maya_scenesetup import camera
        start, end = _span(bone)
        camera.setup(bone, start, end)
    except Exception as error:      # never fails the press that keyed the pose
        return CAMERA_FAILED % (_leaf(bone), str(error).strip().splitlines()[0] if str(error)
                                else type(error).__name__)
    finally:
        # Camera Setup leaves its camera selected: the animator's selection back (a floor drop's
        # «the selection as before», the verify)
        kept = [node for node in selection if cmds.objExists(node)]
        if kept:
            cmds.select(kept, replace=True)
        else:
            cmds.select(clear=True)
    return CAMERA_SET % _leaf(bone)
