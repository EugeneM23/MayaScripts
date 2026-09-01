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

# Clicking a clavicle bone still switches its arm: the bone is no longer
# part of the switchable chain (2026-08-21 split), but the animator's habit
# is older than the split.
CLAVICLE_OF = {"clavicle_l": "arm_l", "clavicle_r": "arm_r"}


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
    # The clavicles are deliberately their own single-knot chains (the
    # pelvis/spine precedent, 2026-08-21): always FK, so the control
    # survives the arm's switches in both directions. Before the arms,
    # because parents precede children -- coupling must find its target.
    # The control drives ONLY the bone: the IK arm keeps riding the root
    # controller (the user's explicit call; see the spec before "fixing").
    ("clavicle_l", ("clavicle_l",)),
    ("clavicle_r", ("clavicle_r",)),
    ("arm_l", ("upperarm_l", "lowerarm_l", "hand_l")),
    ("arm_r", ("upperarm_r", "lowerarm_r", "hand_r")),
    ("leg_l", ("thigh_l", "calf_l", "foot_l", "ball_l")),
    ("leg_r", ("thigh_r", "calf_r", "foot_r", "ball_r")),
] + _finger_chains())

# The ten finger chains, and every bone in them.
#
# Described here but never BUILT (2026-08-18, the user's call): the animator
# poses finger bones directly for now. They stay in CHAINS deliberately --
# teardown walks that table, so a chain missing from it is a rig that nothing
# can find and nothing can bake, which is the failure mode traps 3, 5 and 16
# were all about. A file rigged before the change still comes apart cleanly.
FINGER_CHAINS = tuple(name for name, _ in _finger_chains())
FINGER_JOINTS = tuple(joint for name, chain in CHAINS
                      if name in FINGER_CHAINS for joint in chain)

# What a build may CREATE, as against what the rig may contain. One switch:
# put the finger chains back in and finger controllers return everywhere.
BUILDABLE = tuple(name for name, _ in CHAINS if name not in FINGER_CHAINS)

# What the default (hybrid) Build keeps as FK: everything buildable that is
# not an IK limb -- root, pelvis, spine and neck.
HYBRID_FK_CHAINS = tuple(name for name in BUILDABLE
                         if name not in LIMB_CHAINS)


def build_targets(only=None):
    """Chain names a build may create, in CHAINS order.

    `only=None` asks for everything buildable; an explicit list is filtered
    through the same rule, so no caller gets a finger chain by asking for one.
    Unknown names drop out rather than raise -- `only` arrives from Switch and
    from the picker, and a name the table does not carry is nothing to build.

    Pure. The one place the "which chains exist" / "which chains get built"
    distinction is decided, so the answer cannot drift between callers.
    """
    wanted = BUILDABLE if only is None else set(only)
    return [name for name in BUILDABLE if name in wanted]


def controller_name(joint):
    """Name of the controller for a joint.

    What NAMES a fresh controller. Since 2026-09-01 it is not what FINDS
    one: with two characters in the scene the second build's knot is
    `upperarm_l_FK_ctrl1`, so every name lookup resolved the first
    character -- coupling one character's spine onto another's pelvis,
    aligning somebody else's axes. Resolution goes through the per-
    character index (`fkcontrols.fk_controls`) instead.
    """
    return joint + SUFFIX


def control_leaf(leaf):
    """A knot's leaf name reduced to the controller name, or "".

    Maya appends a digit run when a second character builds the same
    chain, so `upperarm_l_FK_ctrl1` has to read as the same controller.
    The suffix ends in a letter, so stripping trailing digits can never
    eat part of a bone name -- `spine_01_FK_ctrl` survives whole.

    Everything else is rejected, which is what keeps the machinery out of
    the index: OverRig parks a dead `..._FK_ctrl_aimConstraint1` under
    every knot, our ring arrives as `..._FK_ring_tmpShape`, and neither
    reduces to a bare controller name.
    """
    bare = (leaf or "").rstrip("0123456789")
    if bare.endswith(SUFFIX) and len(bare) > len(SUFFIX):
        return bare
    return ""


def bone_of_control(leaf):
    """The bone a controller leaf name belongs to, or "". Pure."""
    name = control_leaf(leaf)
    return name[:-len(SUFFIX)] if name else ""


def controls_in(members):
    """{bone name: control path} read out of one manifest's members.

    Matching inside a manifest that already belongs to ONE character is
    unambiguous -- which is the whole point of tagging the manifests. The
    first hit wins, so a re-recorded duplicate cannot displace the
    controller the build made.
    """
    found = {}
    for path in members or []:
        leaf = (path or "").split("|")[-1].split(":")[-1]
        bone = bone_of_control(leaf)
        if bone:
            found.setdefault(bone, path)
    return found


def chain_set(chain):
    """The readable name a NEW chain manifest gets. Pure."""
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
    for joint, limb in CLAVICLE_OF.items():
        path = scene_map.get(joint)
        if path:
            out[path] = limb
    return out


def limbs_to_convert(limbs, states, to_ik):
    """(to_switch, to_build, already) for a directional FK/IK press.

    The 2026-08-21 buttons bring the selection TO a type, where Switch
    flipped it. `states` is {limb: (is_ik, is_fk)}. A limb already in the
    asked state is left alone and NAMED - pressing FK on an FK arm must not
    rebuild it; one in the opposite state switches; a bare one (or one the
    states never heard of) is built directly in the asked type.

    Pure - the scene arrives as data, order is preserved.
    """
    to_switch, to_build, already = [], [], []
    for limb in limbs:
        is_ik, is_fk = states.get(limb, (False, False))
        if is_ik if to_ik else is_fk:
            already.append(limb)
        elif is_ik or is_fk:
            to_switch.append(limb)
        else:
            to_build.append(limb)
    return to_switch, to_build, already


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
