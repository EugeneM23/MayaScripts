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
- **our camera drives it** (`camera.camera_for`, Camera Setup): the camera's CONTROL is keyed the
  same way (2026-10-21; an older camera without one, the camera itself), its parent carried by the
  `root` when it stands under Main or the Root control (a travel moves Main);
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
Entry = namedtuple("Entry", "leaf path mode driver K carrier aim camera follow")
Entry.__new__.__defaults__ = (None, False, None)
# a weapon in Connections' Aim Mode (2026-10-21): its rotation aims at two world controllers, so
# its translate and theirs are keyed - (target path, up path, aim vector, up vector, distances)
Aim = namedtuple("Aim", "target up aim_v up_v d_aim d_up")


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


def follow_parent(parent_now, turn_now, turn_wanted, place_now, place_wanted):
    """A Camera_follow group's world once its carriers stand where wanted: the turn of `parent_now`
    carried by the turn carrier (Main's, the root), the place carried by the place carrier (the
    followed node's bone) - the group turns with Main and rides a point constraint. It assumes the
    aim group of a camera in Aim Mode stands at identity under `Camera_follow` (it does: `aimcore.put`
    parents it there relatively)."""
    turned = om.MTransformationMatrix(carried_parent(parent_now, turn_now, turn_wanted))
    placed = pm.position(carried_parent(parent_now, place_now, place_wanted))
    turned.setTranslation(om.MVector(placed.x, placed.y, placed.z), om.MSpace.kTransform)
    return turned.asMatrix()


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
    """What holds the camera's motion for bone `path`: its control (2026-10-21), else an older
    camera itself."""
    try:
        from maya_scenesetup import camera
    except ImportError:
        return None
    return camera.keyed_node(path)


#  1P Setup's chest knot (`maya_tools.firstperson.CHEST_MARKER`, spelled here): what stands under
#  it rides `spine_03` rigidly - the camera control, a weapon out of the hands, an Aim Mode group
CHEST_MARKER = "skeldar1PChest"
CHEST_BONE = "spine_03"
HEAD_BONE = "head"


def under_chest(node):
    """Does `node` stand below a 1P chest knot (any ancestor marked `CHEST_MARKER`)?"""
    try:
        parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
        while parents:
            if cmds.attributeQuery(CHEST_MARKER, node=parents[0], exists=True):
                return True
            parents = cmds.listRelatives(parents[0], parent=True, fullPath=True) or []
    except (AttributeError, RuntimeError, ValueError):      # no DAG to ask: not in a chest
        return False
    return False


def first_person(ref):
    """Is `ref` a rig in 1P - a 1P chest knot marked with its namespace (Tools > 1P Setup)? Its
    take lives on the 1P layers and its chest on the knot, so the card's original curves cannot
    land on it raw (2026-10-29: the upper body 110-120 deg off)."""
    rig = getattr(ref, "rig", None)
    if getattr(ref, "kind", None) != "rig" or rig is None:
        return False
    try:
        nodes = cmds.ls("*." + CHEST_MARKER, recursive=True, objectsOnly=True) or []
        return any(cmds.getAttr(node + "." + CHEST_MARKER) == rig.namespace for node in nodes)
    except (AttributeError, RuntimeError, ValueError, TypeError):
        return False


def _carrier_for_parent(parent, head, follow):
    """The game bone carrying a camera control's parent rigidly, from what the parent is (pure
    half of `_camera_carrier`): FKHead_M carries `head`; a Camera_follow group none (it turns with
    Main but rides another node's position - read in the world)."""
    if follow:
        return None
    if head:
        return HEAD_BONE
    return None


def _camera_carrier(driver):
    """The game bone that carries a camera control's parent rigidly: `root` when it stands under
    the rig's Main or its Root control (the root follows them), `head` under FKHead_M, `spine_03`
    under 1P Setup's chest (2026-10-21: a card that turns the chest turns the camera with it), else
    None (the world). None too in a Camera_follow group, which no one bone carries rigidly: it
    turns with Main and takes the followed bone's place (`Entry.follow`, `follow_parent`)."""
    try:
        from maya_scenesetup import camera, rootcontrol
    except ImportError:
        return None
    if not camera.is_control(driver):
        return None
    parents = cmds.listRelatives(driver, parent=True, fullPath=True) or []
    if parents and (camera.is_main(parents[0]) or cmds.attributeQuery(
            rootcontrol.MARKER, node=parents[0], exists=True)):
        return "root"
    if parents and cmds.attributeQuery(camera.FOLLOW_MARKER, node=parents[0], exists=True):
        return _carrier_for_parent(parents[0], head=False, follow=True)
    if parents and parents[0].split("|")[-1].split(":")[-1] == camera.HEAD:
        return _carrier_for_parent(parents[0], head=True, follow=False)
    if under_chest(driver):
        return CHEST_BONE
    return None


def _camera_follow(driver):
    """(turn carrier, place carrier) of the Camera_follow group a camera control stands in - the
    root for Main's turn; head / root / spine_03 for FKHead_M / Root_ctrl / the 1P chest it
    follows, None for anything else - or None out of a follow group."""
    try:
        from maya_scenesetup import camera, rootcontrol
    except ImportError:
        return None
    if not camera.is_control(driver):
        return None
    group = camera.follow_of(driver)
    if not group:
        return None
    followed = cmds.ls(cmds.getAttr(group + "." + camera.FOLLOW_MARKER) or "", long=True) or []
    place = None
    if followed:
        node = followed[0]
        if node.split("|")[-1].split(":")[-1] == camera.HEAD:
            place = HEAD_BONE
        elif cmds.attributeQuery(rootcontrol.MARKER, node=node, exists=True):
            place = "root"
        elif cmds.attributeQuery(CHEST_MARKER, node=node, exists=True):
            place = CHEST_BONE
    return ("root", place)


def _aim_of(driver):
    """An `Aim` when `driver` (a weapon or the camera's control) stands in Aim Mode, else None."""
    try:
        from maya_scenesetup import cameraaim, weaponaim
    except ImportError:
        return None
    for module in (weaponaim, cameraaim):
        group = module.group_of(driver)
        if group is None:
            continue
        made = module.controllers(group)
        if "target" not in made or "up" not in made:
            return None
        aim_v, up_v, d_aim, d_up = module.stored_vectors(group)
        return Aim(made["target"], made["up"], aim_v, up_v, d_aim, d_up)
    return None


def _point(matrix, direction, distance):
    p = om.MPoint(*[v * distance for v in direction]) * om.MMatrix(matrix)
    return (p.x, p.y, p.z)


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
            aimed = _aim_of(driver)
            if aimed:
                why = (self._unwritable(driver, TRANSLATE) or
                       self._unwritable(aimed.target, TRANSLATE) or
                       self._unwritable(aimed.up, TRANSLATE))
            else:
                why = self._unwritable(driver)
            if why:
                self.skipped[leaf] = "%s %s" % (_leaf(driver), why)
                return None
            carrier = _carrier_of(driver) if weapon else None
            carrier_leaf = _leaf(carrier) if carrier else (
                (CHEST_BONE if under_chest(driver) else None) if weapon
                else _camera_carrier(driver))
            if carrier_leaf not in self.bones:
                carrier_leaf = None
            follow = None if weapon else _camera_follow(driver)
            if follow:
                follow = tuple(c if c in self.bones else None for c in follow)
            K = _world(path) * _world(driver).inverse()
            self.notes.append(THROUGH % (leaf, _leaf(driver) + (" (Aim Mode: its controllers)"
                                                                if aimed else "")))
            return Entry(leaf, path, "aimed" if aimed else "driver", driver, K, carrier_leaf,
                         aimed, camera=not weapon, follow=follow)
        why = self._unwritable(path)
        if why:
            self.skipped[leaf] = why
            return None
        return Entry(leaf, path, "joint", None, None, None)

    @staticmethod
    def _unwritable(node, channels=ROTATE + TRANSLATE):
        for channel in channels:
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

    def _followed(self, entry, parent_now, wanted):
        """`parent_now` (a Camera_follow group, or an aim group repeating it) where the card puts
        its carriers (`follow_parent`)."""
        now = [_world(self.bones[c]["path"]) if c and c in wanted else None for c in entry.follow]
        want = [wanted[c] if c and c in wanted else None for c in entry.follow]
        return follow_parent(parent_now, now[0], want[0], now[1], want[1])

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
                parent_new = self._followed(entry, _parent_world(node), wanted) if entry.follow \
                    else carried_parent(_parent_world(node), carrier_now, carrier_wanted)
                local = target * parent_new.inverse()
                plugs = ["%s.%s" % (node, ch) for ch in ROTATE]
                rotate, translate = driver_channels(local, _attrs(node),
                                                    self._current(plugs, seed))
            if entry.mode == "aimed":
                # the weapon's place keyed, its turn through the two controllers in world
                aim = entry.aim
                for ctrl, direction, distance in ((aim.target, aim.aim_v, aim.d_aim),
                                                  (aim.up, aim.up_v, aim.d_up)):
                    point = om.MPoint(*_point(target, direction, distance))
                    ctrl_parent = _parent_world(ctrl)
                    if entry.follow:
                        ctrl_parent = self._followed(entry, ctrl_parent, wanted)
                    elif entry.camera and entry.carrier is not None and entry.carrier in wanted:
                        # a camera's controllers repeat the control's parent: carried with it
                        ctrl_parent = carried_parent(ctrl_parent,
                                                     _world(self.bones[entry.carrier]["path"]),
                                                     wanted[entry.carrier])
                    elif CHEST_BONE in self.bones and CHEST_BONE in wanted and under_chest(ctrl):
                        # in 1P its group rides the chest: carried as the chest will stand
                        ctrl_parent = carried_parent(ctrl_parent,
                                                     _world(self.bones[CHEST_BONE]["path"]),
                                                     wanted[CHEST_BONE])
                    point = point * ctrl_parent.inverse()
                    for channel, value in zip(TRANSLATE, (point.x, point.y, point.z)):
                        values["%s.%s" % (ctrl, channel)] = value
                for channel, value in zip(TRANSLATE, translate):
                    values["%s.%s" % (node, channel)] = value
                continue
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
