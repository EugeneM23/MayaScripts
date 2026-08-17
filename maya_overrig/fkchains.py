"""The chain tables and their pure resolution.

Which bones form which chain, and everything that answers questions about
chains from plain data: the first bone the skeleton HAS (trap 21), the
innermost recorded owner of a node, which chains ride inside a doomed
container. Nothing here touches the scene -- callers pass the scene as
data, which is what makes all of it testable without Maya.
"""

from maya_overrig import builder

FK_SET = "RigPicker_fk"          # legacy flat set; absorbed by a full bake
FK_SET_PREFIX = "RigPicker_fk_"  # one set per chain, the switchable unit
SUFFIX = "_FK_ctrl"

# The four limb chains -- they carry the finger bracket on arm switches.
LIMB_CHAINS = ("arm_l", "arm_r", "leg_l", "leg_r")

# Everything Switch FK/IK may convert. The spine is deliberately absent:
# its spline IK was removed at the user's call (2026-08-15); git history
# holds the full implementation at 0e0794f for when it returns.
SWITCHABLE = LIMB_CHAINS


def _finger_chains():
    chains = []
    for side in ("l", "r"):
        for finger in ("index", "middle", "ring", "pinky"):
            joints = tuple(["{0}_metacarpal_{1}".format(finger, side)]
                           + ["{0}_{1:02d}_{2}".format(finger, i, side)
                              for i in (1, 2, 3)])
            chains.append(("{0}_{1}".format(finger, side), joints))
        chains.append(("thumb_" + side,
                       tuple("thumb_{0:02d}_{1}".format(i, side)
                             for i in (1, 2, 3))))
    return chains


# Selection order for apply_ForwHierarhy IS the chain order, root first.
# Chains are independent of each other on purpose.
CHAINS = tuple([
    ("root", ("root",)),
    # The pelvis is deliberately its own single-knot chain: a spine switch
    # must leave the pelvis controller standing, so they cannot share a
    # manifest.
    ("pelvis", ("pelvis",)),
    ("spine", ("spine_01", "spine_02", "spine_03", "spine_04", "spine_05")),
    ("neck", ("neck_01", "neck_02", "head")),
    ("arm_l", ("clavicle_l", "upperarm_l", "lowerarm_l", "hand_l")),
    ("arm_r", ("clavicle_r", "upperarm_r", "lowerarm_r", "hand_r")),
    ("leg_l", ("thigh_l", "calf_l", "foot_l", "ball_l")),
    ("leg_r", ("thigh_r", "calf_r", "foot_r", "ball_r")),
] + _finger_chains())

# What the default (hybrid) Build keeps as FK: everything that is not an IK
# limb -- root, spine, neck and the ten finger chains.
HYBRID_FK_CHAINS = tuple(name for name, _ in CHAINS
                         if name not in LIMB_CHAINS)


def controller_name(joint):
    """Name of the controller for a joint."""
    return joint + SUFFIX


def chain_set(chain):
    """Name of the object set recording one chain's created nodes."""
    return FK_SET_PREFIX + chain


def finger_chains_for(limb):
    """The finger chains riding on an arm's hand; empty for legs.

    These hang inside the hand controller, so an arm switch must lift them out
    first or they die with the arm's rig.
    """
    if limb not in ("arm_l", "arm_r"):
        return []
    side = limb[-1]
    fingers = ("index", "middle", "ring", "pinky", "thumb")
    return [name for name, _ in CHAINS
            if name.endswith("_" + side) and name.split("_")[0] in fingers]


def chain_root(chain, scene_map):
    """The chain's first bone that this skeleton actually HAS, or None.

    Skeletons arrive with bones missing, and a chain is built from whatever
    of it is there: a UE4-schema rig has no metacarpals, so its finger chains
    start at `<finger>_01_<side>`, and one that stops at `spine_03` has no
    `spine_04` to root anything on.

    The controller at the top of a built chain belongs to THIS bone, never to
    the nominal first one. Asking for the nominal name instead is what left
    eight finger chains standing in world space while the hand walked away:
    `index_metacarpal_l_FK_ctrl` does not exist on such a rig, so nothing
    hung them on the hand and nothing lifted them off it either.

    Pure -- `scene_map` is the picker's {bone name: DAG path} binding.
    """
    for joint in chain:
        if joint in scene_map:
            return joint
    return None


def chain_tip(chain, scene_map):
    """The chain's last bone that this skeleton actually HAS, or None.

    The other end of `chain_root`: what an arm offers a finger to hang on
    once it is FK again, and the bone a leg ends at when there is no ball.
    """
    for joint in reversed(chain):
        if joint in scene_map:
            return joint
    return None


def chain_root_control(chain, scene_map):
    """Name of the controller at the top of this chain, or None.

    None means the skeleton has none of the chain's bones -- there is nothing
    to build, hang or lift, and every caller treats it that way.
    """
    first = chain_root(chain, scene_map)
    return controller_name(first) if first else None


def switchable_bones(scene_map):
    """{bone path: switchable chain} for every bone of every switchable chain.

    What lets the picker-less workflow work: select any BONE of an arm, a
    leg or the spine in the viewport, press Switch, and the chain resolves
    even when no rig exists yet. Pure -- scene_map is plain data.
    """
    table = dict(CHAINS)
    out = {}
    for name in SWITCHABLE:
        for joint in table[name]:
            path = scene_map.get(joint)
            if path:
                out[path] = name
    return out


def innermost_owner(node, candidates):
    """The (kind, name) whose member is the node's NEAREST recorded ancestor.

    Pure. `candidates` is [(member path, kind, name)]. FK controllers nest
    -- the hand controller lives inside spine_05's, which lives inside the
    pelvis's and the root's -- so "descendant of any member" resolves a
    hand click to four chains at once, and a bake wipes the whole rig. The
    longest matching member path is the chain the user actually clicked.
    """
    best = None
    best_len = -1
    for member, kind, name in candidates:
        if node == member or node.startswith(member + "|"):
            if len(member) > best_len:
                best = (kind, name)
                best_len = len(member)
    return best


def dependent_chains(root_ctrls, containers):
    """Chains whose root controller sits inside one of the container paths.

    `root_ctrls` is {chain: long path or None}, `containers` a list of long
    paths about to be deleted. A controller that is a DAG descendant of a
    container dies with it, so the caller must lift these chains out first.
    Pure -- both arguments are plain data; results keep CHAINS order.
    """
    found = []
    for chain_name, _ in CHAINS:
        path = root_ctrls.get(chain_name)
        if not path:
            continue
        if any(builder._is_inside(path, container)
               for container in containers):
            found.append(chain_name)
    return found


def limbs_riding_inside(limb_members, containers):
    """IK limbs whose recorded nodes sit inside one of the container paths.

    The mirror image of `dependent_chains`: there an FK chain rides inside an
    IK limb, here an IK limb rides inside an FK chain -- which is exactly what
    hanging the IK rigs on the root controller creates. Deleting the container
    would take the whole IK rig with it, unbaked, so the caller lifts these
    limbs to world first.

    Pure -- `limb_members` is a {limb: [long paths]} mapping supplied by the
    caller; results keep LIMBS order.
    """
    found = []
    for limb, _ in builder.LIMBS:
        members = limb_members.get(limb) or []
        if any(builder._is_inside(member, container)
               for member in members for container in containers):
            found.append(limb)
    return found


def attach_parent(chain_first, parent_of, targeted):
    """The bone whose controller a chain should hang from.

    Walks up from the chain's first bone to the nearest ancestor that carries a
    controller: clavicle_l -> spine_05, thigh_l -> pelvis, index_metacarpal_l
    -> hand_l, pelvis -> root. Returns None at the top (root stays in world).

    Pure -- `parent_of` is a plain {joint: parent} mapping.
    """
    node = parent_of.get(chain_first)
    seen = set()
    while node is not None and node not in seen:
        if node in targeted:
            return node
        seen.add(node)
        node = parent_of.get(node)
    return None
