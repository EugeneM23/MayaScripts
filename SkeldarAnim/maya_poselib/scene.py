"""The Pose Library's reading of the scene (2026-10-02): which character a selection names, its
skeleton as data, which of its bones the selection means, and how a card names its source.

The animator: «мне не обязательно выделять именно сохраненные элементы достаточно выделить любую
часть скелета или рига». So a CHARACTER is named by any part of it:

- a node of one of OUR rigs (`maya_rigs.rig_of`: its namespace, its group, its game skeleton, its
  character group) is that rig - a rig that drives no game skeleton is not a character for poses
  (a card holds BONES);
- a joint is the skeleton under its topmost joint (`skeletonimport._top_joint`), a mesh the
  skeleton it is skinned to (`_skin_root`), another transform the skeleton under it (the Creep
  skeleton's `Armature`), else its character group's root (`maya_rigs.group_root`: a weapon on the
  floor, the Camera Setup camera, the CoM handle);
- a weapon or an armour piece names the bone its space follows first
  (`weaponspace.hand_for`, `armor.bone_for`), so it names its character as `skeleton.current_root`
  reads it.

A skeleton read here (`skeleton`) is `{leaf: bone}` - the leaf with its namespace stripped, so a
card made on `Manny_Rig1` applies onto `Manny_Rig2` by name - each bone `{path, parent,
canonical, rest, world, rotateOrder, jointOrient, rotateAxis}` - a rig's four unrolled limb bones
a side with their `drive` too (`rigsolve.drive_matrices`). `rest` is the skinCluster's bind
(`maya_retargetmode.rest_world`; a joint's own `.bindPose` was measured 3.5 cm stale, trap 176) -
an unskinned helper's rides its parent's (`rests`: one rest, wherever the character stands now) -
`world` the bone as it stands at the current frame. `canonical` is our UE5 name from
`maya_skeletonmap.recognize` run on the WHOLE skeleton with its rest positions (it refuses a hand
chain alone); on a refusal a UE-named skeleton keeps its leaves as its names, any other none.

Which bones a selection MEANS (`members_from_selection`, pure, the spec's Save rules):

- on a rig a CONTROL names its bones through `maya_asretarget.our_bone_map` (`FKWrist_L` ->
  `hand_l`; every `*Extra*` group - FK, IK, Pole, RootX, IKhybrid, IKcv, Roll - what its control
  does); an IK end, a pole, an FK/IK switch or the IK foot's roll chain (`RollHeel`,
  `RollToes`, `RollToesEnd`) the whole LIMB (`IKArm_L` -> upperarm..hand with their twists, no
  clavicle); `IKToes_<side>` the ball; `Fingers_<side>` the hand's fingers and metacarpals; the
  IK spine controls, its curve's CV controls (`IKcvSpine*`) and the spine switch the spine;
  `HipSwinger_M` the pelvis and spine_01; `Main`, the rig's group, a mesh and any control the
  table does not know the WHOLE BODY. Each was measured on the shipped rigs (each of their 187
  ControlSet members nudged with the limbs in FK and in IK, the game bones' local matrices
  compared): only `Main` moves the whole character;
- a game bone names itself; an AdvancedSkeleton joint (a deformation joint, its FKX/IKX twin, a
  twist `Part` joint) its game bone, by AS's own naming (`Wrist_L` -> `hand_l`);
- on a skeleton a joint names itself; a mesh, the group and the root the whole body;
- helper bones (`ik_*`, `weapon_*`, `camera_*`, `interaction`, `center_of_mass`) and accessories
  (a weapon in a hand or on the floor, an armour piece) are never members on their own - selected
  beside a control they add nothing, selected alone they leave nothing, and nothing means the
  whole body;
- twist bones RIDE with their limb: a member brings the twist bones (and, on a skeleton whose
  names are not Unreal's, the unnamed bones - a finger's end joint) whose nearest named ancestor it
  is, and a rider selected names its carrier;
- the whole body is every bone but the helpers and the root - the root kept when it IS the pelvis
  (Mixamo's Hips), or every pose made on such a skeleton would lose the hips' turn.

Regions (`bone_regions`) come from the bone's canonical name - a UE-named skeleton's leaf - and an
unnamed bone takes its nearest named ancestor's (`posemath.regions`' labels).

Measured (2026-10-02, mayapy standalone, the shipped characters): Manny_Rig's and the Manny
skeleton's game skeletons read 93 bones, the Creep's 91, the UE4 Mannequin's 68, each in
0.01-0.04 s; recognize names 64 UE5 bones by their own leaves (the twists and helpers stay
unnamed) and the UE4 Mannequin's `spine_02` / `spine_03` as `spine_03` / `spine_05` (its three
spine bones distributed onto our five, ends kept). Every selected part of two rigs and three
skeletons - controls, game bones, AS joints, meshes, groups, the Creep's `Armature`, a sword in a
hand, a spear on the floor, the Tech Limb - named its own character.

Spec: docs/superpowers/specs/2026-10-02-pose-library-design.md ("Save", "What a card is")
"""

import collections
import re

import maya.cmds as cmds

import maya_rigs
import maya_skeletonmap as skelmap
from maya_poselib import posemath

CharacterRef = collections.namedtuple("CharacterRef", "kind root rig label key model namespace")

ACCESSORY = "accessory"     # a weapon or an armour piece: the selection kind members_of hands down
MANY = "pick one character for a pose"
NOTHING = "select a character or objects"
DUPLICATE = "%s carries %d bones named %s - the first is kept"

_AS_SIDES = {"_L": "l", "_R": "r", "_M": ""}
_ARM_SWITCHES = ("IKArm", "PoleArm", "FKIKArm")
_LEG_SWITCHES = ("IKLeg", "PoleLeg", "FKIKLeg")
# the IK spine's controls, its curve's CV controls and the FK/IK switch: the spine (measured: an
# IKcvSpine control moves the spine bones and nothing else - spine_01..05 on Manny_Rig,
# spine_01..04 on Creep_Rig and Orc_D_Rig)
_SPINE_SWITCHES = ("FKIKSpine", "IKSpine", "IKhybridSpine", "IKcvSpine")
# the IK foot's roll chain (RollHeel, RollToes, RollToesEnd and the Roller groups above them)
# moves the IK foot, so it names the whole leg as the IK end does (measured: each moves the
# thigh, calf and foot with their twists - the ball too, but for RollToesEnd - nothing else)
_LEG_ROLL = "Roll"
# HipSwinger_M swings the hips under a still chest (measured, the spine in FK: the pelvis and
# spine_01, nothing else) - part names, not bone paths, so it holds on every rig of ours
_HIP_SWING = "HipSwinger"
_HIP_SWING_PARTS = ("pelvis", "spine_01")
# an AdvancedSkeleton "Extra" group above a control moves what the control moves (the first
# prefix that matches is taken off; none of them starts another)
_EXTRA = (("IKhybridExtra", "IKhybrid"), ("IKcvExtra", "IKcv"), ("RollExtra", "Roll"),
          ("FKExtra", "FK"), ("IKExtra", "IK"), ("PoleExtra", "Pole"),
          ("RootExtraX", "RootX"))
_JOINT_PREFIXES = ("FKX", "IKX")
_PART = re.compile(r"^(.+?)Part\d+$")
_LIMB_WORDS = {
    "arm": ("upperarm", "lowerarm"),
    "leg": ("thigh", "calf", "foot", "ball"),
    "hand": skelmap.FINGERS,
    "fingers": skelmap.FINGERS,
}
_WHOLE = "whole"            # a selection item that names the whole body


# ------------------------------------------------------------------ pure: names

def leaf(name):
    """A node's leaf name without its path or namespace: `|a|ns:b` -> `b`."""
    return (name or "").split("|")[-1].split(":")[-1]


def row_key(namespace):
    """The catalog key a rig's namespace was made from: `Manny_Rig1` -> `Manny_Rig` (Add
    Character's `free_namespace` appends the number)."""
    return re.sub(r"\d+$", "", namespace or "")


def canonical_names(paths, mapping, refused):
    """{path: our UE5 name or None} from `maya_skeletonmap.recognize`'s mapping ({ours: path}).

    A bone playing two of our names (Mixamo's Hips is the top joint AND the pelvis) is the one
    that is not `root`. On a refusal a skeleton carrying the UE limbs by name keeps its leaves as
    its names (a first-person UE skeleton has no head and recognize refuses it); any other gets
    none - better no name than a wrong one."""
    if refused:
        leaves = [leaf(p) for p in paths]
        ue = skelmap.covers_ue_core(leaves)
        return dict((p, leaf(p) if ue else None) for p in paths)
    out = dict((p, None) for p in paths)
    for ours in sorted(mapping):
        path = mapping[ours]
        if path not in out:
            continue
        if out[path] is None or out[path] == "root":
            out[path] = ours
    return out


def _own_names(bones):
    """{leaf: the bone's own UE5 name or None}: its canonical name, else - on a UE-named
    skeleton - its leaf."""
    ue = posemath.ue_named(bones)
    return dict((name, bone.get("canonical") or (name if ue else None))
                for name, bone in bones.items())


def _ancestors(bones, name):
    """The bone's ancestors in the skeleton, nearest first (a cycle stops the walk)."""
    out, node, seen = [], bones[name].get("parent"), set([name])
    while node in bones and node not in seen:
        seen.add(node)
        out.append(node)
        node = bones[node].get("parent")
    return out


def part_names(bones):
    """{leaf: the UE5 name of the part the bone belongs to, or None}: its own name, else its
    nearest named ancestor's (a Mixamo finger's end joint is part of that finger)."""
    own = _own_names(bones)
    out = {}
    for name in bones:
        part = own[name]
        if part is None:
            part = next((own[a] for a in _ancestors(bones, name) if own[a]), None)
        out[name] = part
    return out


def bone_regions(bones):
    """{leaf: its region label (`posemath.REGIONS`) or None} by its part's name."""
    out = {}
    for name, part in part_names(bones).items():
        found = posemath.regions([part]) if part else []
        out[name] = found[0] if found else None
    return out


def regions_of(bones, members):
    """The regions a list of member bones touches, in the card's order (`posemath.REGIONS`)."""
    region = bone_regions(bones)
    found = set(region.get(m) for m in members or ())
    return [r for r in posemath.REGIONS if r in found]


def _is_root_out(bones, root):
    """The root leaves the whole body unless it plays the pelvis (Mixamo's Hips)."""
    return root is not None and part_names(bones).get(root) != "pelvis"


def whole_body(bones):
    """Every bone but the helpers (`posemath.is_helper`) and the root (kept when it is the
    pelvis), in skeleton order."""
    root = posemath.root_of(bones)
    drop_root = _is_root_out(bones, root)
    return [b for b in bones if not posemath.is_helper(b) and not (drop_root and b == root)]


def _part_split(part):
    """(base, side) of a part name: `upperarm_twist_01_l` -> (`upperarm_twist_01`, `l`)."""
    if part and len(part) > 2 and part[-2] == "_" and part[-1] in ("l", "r"):
        return part[:-2], part[-1]
    return part, ""


def limb_bones(bones, limb, side):
    """One side's limb, in skeleton order: `arm` the upper arm to the hand with their twists
    (the clavicle excluded), `leg` the thigh to the ball with their twists, `hand` the hand with
    its fingers and metacarpals, `fingers` the same without the hand. `side` is `l` or `r`.
    Read through the part names, so it holds on any skeleton recognize named; helpers never."""
    if limb not in _LIMB_WORDS:
        raise ValueError("no limb called %r (arm, leg, hand, fingers)" % (limb,))
    words = _LIMB_WORDS[limb]
    out = []
    for name, part in part_names(bones).items():
        if posemath.is_helper(name) or not part:
            continue
        base, part_side = _part_split(part)
        if part_side != side:
            continue
        word = base.split("_")[0]
        if word in words or (base == "hand" and limb in ("arm", "hand")):
            out.append(name)
    return out


def _riders(bones):
    """{rider: carrier}: a twist bone (or a bone with no name of its own on a skeleton not named
    by Unreal) rides with its nearest ancestor that is neither - nor a helper. A bone with no such
    ancestor rides with nothing."""
    own = _own_names(bones)

    def rides(name):
        return not posemath.is_helper(name) and (posemath.is_twist(name) or own[name] is None)

    out = {}
    for name in bones:
        if not rides(name):
            continue
        carrier = next((a for a in _ancestors(bones, name)
                        if not rides(a) and not posemath.is_helper(a)), None)
        if carrier is not None:
            out[name] = carrier
    return out


# ------------------------------------------------------------------ pure: the selection

_OUR_MAP = []


def _our_map():
    """`maya_asretarget.our_bone_map()` ({control: UE bone}) - imported on first use, so reading
    names needs no retarget module loaded."""
    if not _OUR_MAP:
        import maya_asretarget
        _OUR_MAP.append(dict(maya_asretarget.our_bone_map()))
    return _OUR_MAP[0]


def _deform_map():
    """{AdvancedSkeleton deformation joint: UE bone}: an FK control's name without `FK` is its
    joint (`FKWrist_L` -> `Wrist_L`), plus the root joint `Root_M` -> pelvis."""
    out = dict((name[2:], bone) for name, bone in _our_map().items() if name.startswith("FK"))
    out["Root_M"] = "pelvis"
    return out


def _side(name):
    """(base, side) of an AdvancedSkeleton name: `IKArm_L` -> (`IKArm`, `l`), `_M` -> ""."""
    if name[-2:] in _AS_SIDES:
        return name[:-2], _AS_SIDES[name[-2:]]
    return name, None


def _spine(bones):
    region = bone_regions(bones)
    return [b for b in bones if region[b] == "Spine" and not posemath.is_helper(b)]


def _parts(bones, wanted):
    """The non-helper bones whose part name is one of `wanted`, in skeleton order."""
    part = part_names(bones)
    return [b for b in bones if part[b] in wanted and not posemath.is_helper(b)]


def _control_bones(name, bones):
    """The bones a rig control names, or `_WHOLE`. Of the shipped rigs' 187 ControlSet members
    only `Main` names the whole body (`tests/test_poselib_scene.ShippedControlSet`)."""
    for extra, plain in _EXTRA:
        if name.startswith(extra):
            name = plain + name[len(extra):]
            break
    if name == "Main":
        return _WHOLE
    base, side = _side(name)
    if side in ("l", "r"):
        if base in _ARM_SWITCHES:
            return limb_bones(bones, "arm", side)
        if base in _LEG_SWITCHES or base.startswith(_LEG_ROLL):
            return limb_bones(bones, "leg", side)
        if base == "Fingers":
            return limb_bones(bones, "fingers", side)
    if base == _HIP_SWING and side == "":
        return _parts(bones, _HIP_SWING_PARTS) or _WHOLE
    if base.startswith(_SPINE_SWITCHES):
        return _spine(bones) or _WHOLE
    bone = _our_map().get(name)
    if bone is None and name.startswith("FK"):
        bone = _deform_map().get(name[2:])          # FKRoot_M: the root joint's control
    return [bone] if bone in bones else _WHOLE


def _rig_joint_bones(name, bones):
    """The game bone an AdvancedSkeleton joint plays, or `_WHOLE`: its deformation name with an
    FKX/IKX prefix or a twist `Part` taken off (`ShoulderPart1_L` -> `Shoulder_L` -> upperarm)."""
    for prefix in _JOINT_PREFIXES:
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    deform = _deform_map()
    bone = deform.get(name)
    if bone is None:
        base, side = _side(name)
        part = _PART.match(base or "")
        if part and side is not None:
            bone = deform.get(part.group(1) + name[-2:])
    return [bone] if bone in bones else _WHOLE


def _item_bones(ref, name, kind, bones, root):
    """What one selected item names: a list of bones, `_WHOLE`, or [] (a helper, an
    accessory)."""
    if kind == ACCESSORY:
        return []
    if kind == "joint":
        if name in bones:
            if name == root:
                return _WHOLE
            return [] if posemath.is_helper(name) else [name]
        if ref.kind == "rig":
            return _rig_joint_bones(name, bones)
        return _WHOLE
    if kind == "transform" and ref.kind == "rig":
        return _control_bones(name, bones)
    return _WHOLE                                   # a mesh, a group, anything else


def members_from_selection(ref, selection, bones):
    """The member bones a selection names, in skeleton order (the spec's Save rules - the module
    docstring). `selection` is a list of `(name, kind)`: the node's name or path (namespaces
    ignored) and `joint` / `transform` / `mesh` / `accessory` (`members_of` builds it from the
    scene). Nothing named, or the whole body named by any item, gives `whole_body(bones)`."""
    root = posemath.root_of(bones)
    riders = _riders(bones)
    chosen = set()
    for name, kind in selection or ():
        found = _item_bones(ref, leaf(name), kind, bones, root)
        if found == _WHOLE:
            return whole_body(bones)
        chosen.update(riders.get(b, b) for b in found)
    if not chosen:
        return whole_body(bones)
    chosen.update(r for r, carrier in riders.items() if carrier in chosen)
    return [b for b in bones if b in chosen]


def describe(refs, loose):
    """What the save panel says the selection is."""
    if len(refs) > 1:
        return "%d characters selected - %s" % (len(refs), MANY)
    if refs:
        ref = refs[0]
        name = ref.namespace or leaf(ref.root)
        return ref.label if name == ref.label else "%s (%s)" % (ref.label, name)
    if loose:
        return "%d object%s" % (len(loose), "" if len(loose) == 1 else "s")
    return "nothing selected"


# ------------------------------------------------------------------ scene: which character

def _long(path):
    if not path:
        return None
    found = cmds.ls(path, long=True) or []
    return found[0] if found else None


def dag_object(item):
    """The DAG transform a selection item stands for: a component's object, a shape's transform;
    None for a node that is not in the DAG."""
    path = _long((item or "").split(".")[0])
    if path is None or not cmds.objectType(path, isAType="dagNode"):
        return None
    if cmds.objectType(path, isAType="shape"):
        parent = cmds.listRelatives(path, parent=True, fullPath=True) or []
        return parent[0] if parent else None
    return path


def _entry(label=None, key=None):
    from maya_scenesetup import catalog
    if label:
        found = catalog.character_by_label(label)
        if found is not None:
            return found
    return catalog.character_by_key(key) if key else None


def _group_label(group):
    if group and cmds.attributeQuery(maya_rigs.CHARACTER_MARKER, node=group, exists=True):
        return cmds.getAttr(group + "." + maya_rigs.CHARACTER_MARKER) or ""
    return ""


def rig_ref(rig):
    """The CharacterRef of a rig, or None when it drives no game skeleton. Its catalog row from
    its character group's marker (the label Add Character wrote), else its namespace's key."""
    if not rig.skeleton_root:
        return None
    entry = _entry(_group_label(rig.character), row_key(rig.namespace))
    label = entry.label if entry is not None else maya_rigs.label(rig)
    return CharacterRef("rig", rig.skeleton_root, rig, label,
                        entry.key if entry is not None else None,
                        (entry.model or None) if entry is not None else None, rig.namespace)


def skeleton_ref(root):
    """The CharacterRef of a bare skeleton: its catalog row from the label its Add recorded
    (`deletion.recorded`), else its character group's marker; a native skeleton (Auto's own)
    keeps its recorded label and has no row."""
    from maya_scenesetup import deletion
    label = deletion.recorded(root)[1] or _group_label(maya_rigs.group_of(root))
    entry = _entry(label)
    return CharacterRef("skeleton", root, None, label or leaf(root),
                        entry.key if entry is not None else None,
                        (entry.model or None) if entry is not None else None,
                        maya_rigs.namespace_of(root))


def _bare():
    from maya_uebridge import skeletonimport
    return skeletonimport.bare_roots()


def character_of(path, rigs=None, bare=None, refs=None):
    """The CharacterRef `path` belongs to, or None (the module docstring's rules). `rigs` and
    `bare` (the skeletons no rig owns) are read from the scene when not given; `refs` (a dict)
    keeps one `rig_ref` per rig and one `skeleton_ref` per skeleton across the calls of one
    selection.

    A node of a rig - its namespace, its group, its game skeleton, its character group - is
    answered by `maya_rigs.rig_of` (pure) BEFORE the weapon and armour walks: those climb every
    ancestor of a deep AdvancedSkeleton control asking each for a marker, and with a rig's 187
    controls selected that cost 0.8 s on every selection change and every card click (the final
    review); a weapon or an armour piece of a rig stands in its group and is answered the same."""
    from maya_scenesetup import armor, weaponspace
    from maya_uebridge import skeletonimport
    path = _long(path) if path else None
    if path is None:
        return None
    refs = {} if refs is None else refs
    rigs = maya_rigs.rigs() if rigs is None else rigs
    bare = _bare() if bare is None else bare
    rig = maya_rigs.rig_of(path, rigs)
    if rig is None and cmds.objectType(path) == "joint":
        # a bare skeleton's own joint names it at once (an armour piece's joints stand under
        # their own top joint, no skeleton's: they go on to the walk)
        root = skeletonimport._top_joint(path)
        if root in bare:
            return _cached(refs, ("skeleton", root), lambda: skeleton_ref(root))
    if rig is None:
        path = weaponspace.hand_for(path) or armor.bone_for(path) or path
        rig = maya_rigs.rig_of(path, rigs)
    if rig is not None:
        return _cached(refs, ("rig", rig.namespace, rig.group), lambda: rig_ref(rig))
    if cmds.objectType(path) == "joint":
        root = skeletonimport._top_joint(path)
    else:
        root = skeletonimport._skin_root(path) \
            or next((r for r in bare if maya_rigs.under(r, path)), None) \
            or maya_rigs.group_root(maya_rigs.group_of(path))
    if root not in bare:
        return None
    return _cached(refs, ("skeleton", root), lambda: skeleton_ref(root))


def _cached(refs, key, make):
    if key not in refs:
        refs[key] = make()
    return refs[key]


def resolve(selection=None):
    """[(the selected DAG transform, its CharacterRef or None)] in selection order, repeats
    dropped. `selection` defaults to Maya's."""
    if selection is None:
        selection = cmds.ls(selection=True, long=True) or []
    objects = []
    for item in selection:
        path = dag_object(item)
        if path is not None and path not in objects:
            objects.append(path)
    if not objects:
        return []
    rigs, bare, refs = maya_rigs.rigs(), _bare(), {}
    return [(path, character_of(path, rigs, bare, refs)) for path in objects]


def characters(selection=None):
    """(every character the selection touches, in selection order, each once; the selected
    transforms that belong to none)."""
    refs, loose = [], []
    for path, ref in resolve(selection):
        if ref is None:
            loose.append(path)
        elif all(r.root != ref.root for r in refs):
            refs.append(ref)
    return refs, loose


def all_characters():
    """Every character in the scene: each rig driving a game skeleton, then each bare
    skeleton."""
    out = [r for r in (rig_ref(rig) for rig in maya_rigs.rigs()) if r is not None]
    return out + [skeleton_ref(root) for root in _bare()]


def selection_label(selection=None):
    """What the save panel's character line says about the selection (`describe`)."""
    return describe(*characters(selection))


# ------------------------------------------------------------------ scene: the skeleton

def _joints(root):
    """The skeleton's joints, long paths, parents first (a preorder by name)."""
    if not root or not cmds.objExists(root):
        return []
    paths = [_long(root)] + (cmds.listRelatives(root, allDescendents=True, type="joint",
                                                fullPath=True) or [])
    return sorted(set(paths), key=lambda p: p.split("|"))


def rests(paths, binds, now):
    """{path: flat rest world} of a skeleton's joints, ONE consistent rest: pure.

    `paths` parents first (`_joints`), `binds` {path: flat} the skinned joints' binds
    (`maya_retargetmode.rest_world`), `now` {path: flat} every joint's world as it stands. A
    skinned joint rests at its bind; an UNSKINNED one (UE's weapon_r / weapon_l, camera_root /
    camera_bone) takes its parent's rest with its own local as it stands now - the helper rides
    its parent - and an unskinned TOP joint takes its nearest skinned descendant's way to its
    bind. A skeleton with no skin at all rests as it stands.

    Read straight off `rest_world` - the bind for a skinned joint, the CURRENT world for any
    other - the rest mixed two poses: a Manny standing 150 cm low (Main.ty -150) had its helpers
    150 cm under the bind's feet, `maya_skeletonmap`'s floor rule took the lowest of them for the
    floor, the root (at the bind's 0) stood 50 cm over it and lost its name - `has_root` False,
    the pelvis put over the WORLD floor, 245.897 cm over the root for 95.897 (fix round 2)."""
    parents = skelmap.parent_map(paths)
    if not binds:
        return dict((p, list(now[p])) for p in paths)
    out = {}
    for path in paths:
        if path in binds:
            out[path] = list(binds[path])
            continue
        parent = parents.get(path)
        if parent is not None and parent in out:
            anchor, anchor_rest = parent, out[parent]
        else:
            below = [q for q in binds if q.startswith(path + "|")]
            if not below:
                out[path] = list(now[path])
                continue
            anchor = min(below, key=lambda q: (q.count("|"), q))
            anchor_rest = binds[anchor]
        out[path] = posemath.flat(posemath.matrix(now[path]) *
                                  posemath.matrix(now[anchor]).inverse() *
                                  posemath.matrix(anchor_rest))
    return out


def _bind(path):
    """The joint's bind (`maya_retargetmode.rest_world`) when a skinCluster holds it, else None."""
    if not cmds.listConnections(path + ".worldMatrix[0]", source=False, destination=True,
                                type="skinCluster"):
        return None
    import maya_retargetmode
    return [float(v) for v in maya_retargetmode.rest_world(path)]


def skeleton(ref, notes=None):
    """(bones, convention): the character's game skeleton as `{leaf: bone}` (the module
    docstring) and its naming convention (`maya_skeletonmap.convention_of`). A leaf twice in one
    skeleton keeps the first and is noted into `notes` (a list) when one is given.

    On a RIG the four unrolled limb bones a side (upperarm, lowerarm, thigh, calf) also carry
    their `drive` as it stands (`rigsolve.drive_matrices`): a card saved from the rig keeps it,
    and a target read here stands in it (`posemath.targets`), so what follows such a bone
    follows the drive chain the rig holds it by."""
    paths = _joints(ref.root)
    now = dict((p, [float(v) for v in cmds.getAttr(p + ".worldMatrix[0]")]) for p in paths)
    binds = {}
    for path in paths:
        bind = _bind(path)
        if bind is not None:
            binds[path] = bind
    rest = rests(paths, binds, now)
    result = skelmap.recognize(paths, dict((p, tuple(m[12:15])) for p, m in rest.items()))
    names = canonical_names(paths, result.mapping, bool(result.refusal))
    parents = skelmap.parent_map(paths)
    bones, seen = {}, collections.Counter(leaf(p) for p in paths)
    for path in paths:
        name = leaf(path)
        if name in bones:
            continue
        parent = parents.get(path)
        bones[name] = {
            "path": path,
            "parent": leaf(parent) if parent else None,
            "canonical": names[path],
            "rest": rest[path],
            "world": now[path],
            "rotateOrder": int(cmds.getAttr(path + ".rotateOrder")),
            "jointOrient": [float(v) for v in cmds.getAttr(path + ".jointOrient")[0]],
            "rotateAxis": [float(v) for v in cmds.getAttr(path + ".rotateAxis")[0]],
        }
    if ref.kind == "rig" and ref.rig is not None:
        from maya_poselib import rigsolve
        for name, drive in rigsolve.drive_matrices(ref.rig).items():
            if name in bones:
                bones[name]["drive"] = posemath.flat(drive)
    if notes is not None:
        for name in sorted(n for n, count in seen.items() if count > 1):
            notes.append(DUPLICATE % (ref.label, seen[name], name))
    return bones, result.convention


def bone_path(ref, name):
    """The long path of the character's bone with leaf `name` (the first in `skeleton`'s order),
    or None."""
    return next((p for p in _joints(ref.root) if leaf(p) == name), None)


def identity(ref, convention=None):
    """The card's `character` block: who the pose was made on."""
    rotation_only = False
    if ref.rig is not None:
        import maya_asretarget
        rotation_only = bool(maya_asretarget.rotation_mode(ref.rig))
    if convention is None:
        convention = skelmap.convention_of(_joints(ref.root))
    return {"key": ref.key, "model": ref.model, "kind": ref.kind, "label": ref.label,
            "namespace": ref.namespace, "root": leaf(ref.root), "convention": convention,
            "rotation_only": rotation_only}


def _own(ref, path):
    """Is `path` the character's own node - in its non-empty namespace (a rig's controls and
    joints, a namespaced skeleton's), or one of its JOINTS? Then no weapon space or armour space
    stands above it, and `_kind` skips the walks up its ancestors (a weapon and an armour piece
    stand in spaces of their own, outside the skeleton; one parented by hand under a bone still
    carries its own marker, which is still asked)."""
    if ref is None:
        return False
    namespace = maya_rigs.namespace_of(path)
    if ref.namespace and namespace == ref.namespace:
        return True
    return ref.kind == "skeleton" and not namespace and maya_rigs.under(path, ref.root) and \
        cmds.nodeType(path) == "joint"


def _kind(path, ref=None):
    """The selection kind of one DAG transform (`members_from_selection`): a weapon - in a hand's
    space or out on the floor (the marked node itself) - or an armour piece is an accessory. The
    character `ref`'s own nodes (`_own`) are asked only for those markers of their own, never
    walked up: a rig's 187 controls walked cost 0.8 s on every selection change (the final
    review)."""
    from maya_scenesetup import armor, bonedrive, weaponspace
    walked = not _own(ref, path) and (weaponspace.hand_for(path) or armor.bone_for(path))
    if walked or any(
            cmds.attributeQuery(marker, node=path, exists=True)
            for marker in (bonedrive.MARKER, armor.MARKER)):
        return ACCESSORY
    kind = cmds.nodeType(path)
    if kind != "joint" and cmds.listRelatives(path, shapes=True, type="mesh", fullPath=True):
        return "mesh"
    return kind


def members_of(ref, nodes, bones=None):
    """The member bones the selected `nodes` name on `ref` (`members_from_selection`, the kinds
    read from the scene). `bones` is `skeleton(ref)[0]`, read when not given."""
    if bones is None:
        bones = skeleton(ref)[0]
    selection = []
    for node in nodes or ():
        path = dag_object(node)
        if path is not None:
            selection.append((path, _kind(path, ref)))
    return members_from_selection(ref, selection, bones)
