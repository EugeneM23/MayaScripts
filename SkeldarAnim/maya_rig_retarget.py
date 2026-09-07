"""One shelf button for every AdvancedSkeleton rig we drive: select the imported skeleton, press.

The animator's button ran `maya_asretarget.connect()` -- the Manny rig's retarget -- and
on the Lugal (PlayerMale) rig that module can only refuse: the bones it maps are UE's.
This picks the module from the rig the scene holds and forwards to it, so the press is
the same on `manny_rig_02` and on `Lugal_Rig_01` (2026-09-06, «я просто выделяю скелет,
нажимаю на скрипт и ретаргет готов. Точно так же я хочу и для Lugal_Rig_01»).

    import sys; sys.path.append(r"C:/!!!Work/MayaScripts/SkeldarAnim")
    import maya_rig_retarget
    print(maya_rig_retarget.connect())     # the rig follows the SELECTED skeleton
    print(maya_rig_retarget.bake())        # the vendor's Bake over the clip's keys, then Disconnect
    print(maya_rig_retarget.report())      # read-only
    print(maya_rig_retarget.disconnect())  # keeps nothing of the clip

Which rig: the constrained game skeleton under the rig -- UE names (`pelvis`, `spine_05`)
mean the Manny rig and `maya_asretarget`; PlayerMale names (`Hip`, `Spine4`, `Right_Arm`)
mean the Lugal rig and `maya_pmretarget`.  Anything else is refused by name.
"""
import maya.cmds as cmds


def rig_module():
    """The retarget module for the rig in this scene, or a refusal string."""
    import maya_pmretarget as pm
    if not cmds.objExists("ControlSet") or not cmds.objExists("Main"):
        return None, "no AdvancedSkeleton rig in this scene (ControlSet/Main missing)"
    root = pm.rig_skeleton_root(pm.rig_paths())
    if not root:
        return None, "the rig drives no skeleton - nothing to retarget onto"
    names = [pm.leaf(p) for p in [root] + (cmds.listRelatives(root, allDescendents=True, type="joint", fullPath=True) or [])]
    return pick(names, root)


def pick(names, root=""):
    """Pure: which module drives a rig whose game skeleton has these bone names."""
    import maya_pmretarget as pm
    schema = pm.detect_schema(names)
    if schema is pm.OWN:
        return pm, ""
    if schema in (pm.UE5, pm.UE4):
        import maya_asretarget as ar
        return ar, ""
    return None, ("the rig's skeleton %s is neither the Manny's (UE names) nor the Lugal's (Hip/Spine4/Right_Arm) - "
                  "no retarget module knows it" % root)


def _forward(name, *args, **kwargs):
    mod, refusal = rig_module()
    if mod is None:
        return refusal
    fn = getattr(mod, name, None)
    if fn is None:
        return "%s has no %s()" % (mod.__name__, name)
    return "%s: %s" % (mod.__name__, fn(*args, **kwargs))


def report(*args, **kwargs):
    return _forward("report", *args, **kwargs)


def connect(*args, **kwargs):
    return _forward("connect", *args, **kwargs)


# ------------------------------------------------------------- helper bones
#
# 2026-09-07, the animator: «кроме ретаргета анимаций на адванцед скелетон
# мы еще должны переносить анимацию weapon bone (и левой и правой), а также
# анимацию camera root и camera bone ... и должен быть выполнен camera
# setup». None of the four is driven by the rig -- AdvancedSkeleton leaves
# them riding their parents -- so after the controls are baked each one is
# constrained to the source's bone of the same name, baked over the same
# range, and released. World space, no offset: the source is a twin of the
# rig's skeleton and the rig's hand reproduces the source's to 0.0016 cm.

HELPER_BONES = ("weapon_r", "weapon_l", "camera_root", "camera_bone")
_CHANNELS = ["translateX", "translateY", "translateZ",
             "rotateX", "rotateY", "rotateZ"]


def helper_plan(source_bones, rig_bones, foreign=()):
    """Pure: which helper bones move from the source onto the rig's skeleton.

    `source_bones`/`rig_bones` are {leaf name: path}; `foreign` names rig
    bones under somebody else's constraint, which are skipped by name rather
    than fought over. A rig without the bone has nothing to carry and says
    nothing about it.
    """
    moves, skipped = [], []
    for name in HELPER_BONES:
        if name not in rig_bones:
            continue
        if name not in source_bones:
            skipped.append((name, "not in the source"))
        elif name in foreign:
            skipped.append((name, "driven by somebody else's constraint"))
        else:
            moves.append((name, source_bones[name], rig_bones[name]))
    return moves, skipped


def helper_note(moved, skipped, camera_text):
    """Pure: the status line's tail."""
    parts = []
    if moved:
        parts.append(", ".join(moved) + " carried from the source")
    if skipped:
        parts.append("skipped " + ", ".join("%s (%s)" % pair for pair in skipped))
    if camera_text:
        parts.append(camera_text)
    return "; ".join(parts)


def _bones_under(root):
    """{leaf name without namespace: long path} for a skeleton."""
    paths = [root] + (cmds.listRelatives(root, allDescendents=True, type="joint",
                                         fullPath=True) or [])
    out = {}
    for path in paths:
        out.setdefault(path.split("|")[-1].split(":")[-1], path)
    return out


def _foreign(bones):
    """Helper bones under a constraint that is neither the weapon link's nor
    our camera's -- those two are handled, anything else is not ours."""
    from maya_scenesetup import bonedrive, camera
    found = set()
    for name, path in bones.items():
        if name not in HELPER_BONES:
            continue
        constraints = cmds.listRelatives(path, children=True, type="constraint",
                                         fullPath=True) or []
        ours = len(camera.our_constraints(path)) + (1 if bonedrive.driving_weapon(path) else 0)
        if len(constraints) > ours:
            found.add(name)
    return found


def transfer_bone(src, dst, start, end):
    """The rig's bone onto the source bone's world track: constrain, bake, release.

    The bone's own keys are cut FIRST: constraining a keyed channel splices a
    pairBlend in (trap 37's mechanism) and a second Bake on the same rig
    would otherwise blend the new take with the old one.
    """
    cmds.cutKey(dst, attribute=_CHANNELS, clear=True)
    constraint = cmds.parentConstraint(src, dst)[0]
    cmds.bakeResults(dst, time=(start, end), attribute=_CHANNELS, simulation=False,
                     sampleBy=1, disableImplicitControl=True, preserveOutsideKeys=False,
                     sparseAnimCurveBake=False)
    cmds.delete(constraint)
    cmds.delete(dst, staticChannels=True, unitlessAnimationCurves=False,
                hierarchy="none", controlPoints=False, shape=True)


def carry_helpers(source_root, rig_root, start, end):
    """The after-bake step. Returns (moved names, skipped pairs, camera text).

    Order, each half paid for elsewhere: a standing camera setup is torn down
    first (`camera.teardown` bakes the bone back before deleting the camera)
    so its constraint cannot fight the transfer's; a weapon link is unlinked
    (the bone baked back off the sword) and relinked after the transfer, so
    the sword snaps onto the new track and takes its stored grip back -- the
    bridge's merge does exactly this; and the camera is set up LAST, on the
    bone's new track.
    """
    from maya_scenesetup import bonedrive, camera
    src, dst = _bones_under(source_root), _bones_under(rig_root)
    cam_bone = dst.get("camera_bone")
    if cam_bone:
        camera.teardown(cam_bone, start, end)
    links = {}
    for name in ("weapon_r", "weapon_l"):
        if name in dst:
            weapon = bonedrive.driving_weapon(dst[name])
            if weapon:
                links[dst[name]] = weapon
                bonedrive.unlink(dst[name])
    moves, skipped = helper_plan(src, dst, _foreign(dst))
    for _name, source_path, rig_path in moves:
        transfer_bone(source_path, rig_path, start, end)
    for bone, weapon in links.items():
        if cmds.objExists(weapon) and cmds.objExists(bone):
            bonedrive.relink(weapon, bone)
    camera_text = camera.setup(cam_bone, start, end) if cam_bone else ""
    return [move[0] for move in moves], skipped, camera_text


def bake(*args, **kwargs):
    """The Bake button: the module's bake, the helper bones, the camera, the disconnect.

    Six steps -- controls baked over the clip's key range (`vendor_bake`),
    a standing camera torn down, weapon links lifted, the four helper bones
    carried from the source, links restored, the module's disconnect, and
    Camera Setup on the rig's `camera_bone` -- so the whole "after the
    retarget" lives under one press and one undo chunk. With nothing
    connected the module says so and nothing else happens.
    """
    mod, refusal = rig_module()
    if mod is None:
        return refusal
    source = mod.connected_source()
    if source is None:
        return "%s: %s" % (mod.__name__, mod.bake(*args, **kwargs))
    span = mod.source_key_range() or (cmds.playbackOptions(query=True, min=True),
                                      cmds.playbackOptions(query=True, max=True))
    rig_root = mod.rig_skeleton_root(mod.rig_paths())
    cmds.undoInfo(openChunk=True, chunkName="Retarget bake")
    try:
        note = mod.bake(disconnect=False).split("; still connected")[0]
        moved, skipped, camera_text = carry_helpers(source, rig_root, span[0], span[1])
        note += "; " + mod.disconnect()
    finally:
        cmds.undoInfo(closeChunk=True)
    extra = helper_note(moved, skipped, camera_text)
    return "%s: %s%s" % (mod.__name__, note, ("; " + extra) if extra else "")


def disconnect(*args, **kwargs):
    return _forward("disconnect", *args, **kwargs)


# ------------------------------------------------------------ shelf buttons

def _show(text):
    """The first line in the viewport, the whole text in the Script Editor.

    A shelf button has no status line of its own; the print is the record
    and the in-view message is what the animator sees. Guarded: mayapy
    and a hidden viewport have nowhere to draw it.
    """
    print(text)
    try:
        cmds.inViewMessage(assistMessage=text.splitlines()[0],
                           position="midCenterBot", fade=True)
    except Exception:
        pass
    return text


def retarget_button():
    """The Retarget shelf button: the rig follows the SELECTED skeleton."""
    return _show(connect())


def bake_button():
    """The Bake shelf button: bake onto the controls, carry the weapon and
    camera bones, set the camera up, disconnect."""
    return _show(bake())
