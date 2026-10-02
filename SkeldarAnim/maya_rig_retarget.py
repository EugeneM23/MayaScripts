"""One shelf button for every AdvancedSkeleton rig we drive: select the imported skeleton, press.

The animator's button ran `maya_asretarget.connect()` -- the Manny rig's retarget -- and
on the Lugal (PlayerMale) rig that module can only refuse: the bones it maps are UE's.
This picks the module from the rig and forwards to it, so the press is the same on
`manny_rig_02` and on `Lugal_Rig_01` (2026-09-06, «я просто выделяю скелет, нажимаю на
скрипт и ретаргет готов. Точно так же я хочу и для Lugal_Rig_01»).

**One button since 2026-09-08** («Ретаргет и бейк объединим в один скрипт»): `retarget()`
is the whole thing -- the previous take cleared, connect, bake over the clip's keys, the
helper bones carried, the camera set up, disconnect -- in one undo chunk. The source
skeleton is KEPT: the animator imported it, and a second look at the result wants it
there to press again. `connect()`, `bake()`, `report()` and `disconnect()` stay as API.

    import sys; sys.path.append(r"C:/!!!Work/MayaScripts/SkeldarAnim")
    import maya_rig_retarget
    print(maya_rig_retarget.retarget())    # the button: the rig takes the SELECTED skeleton's clip
    print(maya_rig_retarget.report())      # read-only

**Which rig, with several in the scene** (`maya_rigs`): the one whose control, bone or
mesh is in the selection, else the only one, else a refusal naming them. The selection
therefore carries two things at once -- the source skeleton's bones and, when needed, one
control of the rig -- and each module takes the half that is its own. Which MODULE: the
rig's constrained game skeleton -- UE names (`pelvis`, `spine_05`) mean the Manny rig and
`maya_asretarget`; PlayerMale names (`Hip`, `Spine4`, `Right_Arm`) mean the Lugal rig and
`maya_pmretarget`. Anything else is refused by name.
"""
import maya.cmds as cmds

import maya_hubstyle as hubstyle
import maya_rigs

POSED =("the rig is still posed after the reset - AdvancedSkeleton: Go To "
         "BuildPose, then press again")


def resolve(rig=None):
    """(rig, module, refusal): the rig to act on and the module that knows it."""
    if rig is None:
        rig, refusal = maya_rigs.current_rig()
        if rig is None:
            return None, None, refusal
    mod, refusal = rig_module(rig)
    return rig, mod, refusal


def rig_module(rig=None):
    """(module, refusal) for `rig` -- the current one when not given."""
    import maya_pmretarget as pm
    if rig is None:
        rig, refusal = maya_rigs.current_rig()
        if rig is None:
            return None, refusal
    root = rig.skeleton_root
    if not root:
        return None, ("the rig %s drives no skeleton - nothing to retarget onto"
                      % maya_rigs.label(rig))
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
    rig, mod, refusal = resolve(kwargs.pop("rig", None))
    if mod is None:
        return refusal
    fn = getattr(mod, name, None)
    if fn is None:
        return "%s has no %s()" % (mod.__name__, name)
    return "%s: %s" % (mod.__name__, fn(*args, rig=rig, **kwargs))


def report(*args, **kwargs):
    return _forward("report", *args, **kwargs)


def connect(*args, **kwargs):
    return _forward("connect", *args, **kwargs)


def disconnect(*args, **kwargs):
    return _forward("disconnect", *args, **kwargs)


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


def helper_space(mod, rig):
    """"parent" when the rig takes rotations only (the module says so), else "world".

    A rotation-only rig keeps its own bone lengths -- the Creep's arms are 26%
    longer than a UE clip's -- so a weapon_r carried in WORLD space would stand where
    the SOURCE's hand is, off the rig's own. Carried relative to its parent it keeps
    the clip's grip on the rig's hand (2026-09-24).

    Since 2026-10-02 the standing connect says which version it is
    (`connected_mode`): only the twin's exact stretch carries in world space; the
    rotations and a stretch onto another body (taken at our size) carry relative to
    the parent. A connect made without a version answers by the rig's mark, as before."""
    standing = getattr(mod, "connected_mode", None)
    mode = standing(rig) if standing is not None else None
    if mode:
        return "world" if mode == "twin" else "parent"
    probe = getattr(mod, "rotation_mode", None)
    return "parent" if probe is not None and probe(rig) else "world"


# ------------------------------------------------------- which version
#
# 2026-10-02, «должно быть две версии ретаргета ... скрипт должен определить
# какую ретаргет систему стоит использовать и если ... будет ломать пропорции
# то необходимо спросить»: the press measures the clip against the rig
# (`mod.measure`), and `maya_retargetmode` decides - and asks - before anything
# in the scene changes.

CANCELLED = "cancelled - nothing changed"


def decide_for(mod, rig, source_root=None, bones=None, setting=None):
    """The Decision for this clip onto this rig; raises
    `maya_retargetmode.Cancelled` on Cancel.

    `bones` forced by a caller wins; a module that cannot measure (or a clip it
    refuses) answers the legacy retarget (mode None) and the connect then says
    what is wrong."""
    import maya_retargetmode as rm
    if bones in (rm.ROTATION, rm.STRETCH):
        return rm.Decision(bones, False, "%s - asked for" % (
            "rotations" if bones == rm.ROTATION else "stretch"))
    probe = getattr(mod, "measure", None)
    if probe is None:
        return rm.Decision(None, False, "")
    m, refusal = probe(source_root=source_root, rig=rig)
    if refusal or m is None:
        return rm.Decision(None, False, "")
    return rm.choose(m, setting)


def connect_kwargs(decision):
    """Pure: the connect's keyword for a Decision ({} for the legacy call)."""
    return {"bones": decision.mode} if decision is not None and decision.mode else {}


def _parent_space_driver(src, dst):
    """A transform standing at the source bone's pose relative to ITS parent, carried by the rig
    bone's parent: world = W_src * P_src^-1 * P_dst (row vectors). Returns (driver, nodes)."""
    src_parent = cmds.listRelatives(src, parent=True, fullPath=True)
    dst_parent = cmds.listRelatives(dst, parent=True, fullPath=True)
    mm = cmds.createNode("multMatrix", skipSelect=True)
    cmds.connectAttr(src + ".worldMatrix[0]", mm + ".matrixIn[0]")
    if src_parent:
        cmds.connectAttr(src_parent[0] + ".worldInverseMatrix[0]", mm + ".matrixIn[1]")
    if dst_parent:
        cmds.connectAttr(dst_parent[0] + ".worldMatrix[0]", mm + ".matrixIn[2]")
    dm = cmds.createNode("decomposeMatrix", skipSelect=True)
    cmds.connectAttr(mm + ".matrixSum", dm + ".inputMatrix")
    driver = cmds.createNode("transform", name="rrtHelperDriver", skipSelect=True)
    cmds.connectAttr(dm + ".outputTranslate", driver + ".translate")
    cmds.connectAttr(dm + ".outputRotate", driver + ".rotate")
    return driver, [driver, dm, mm]


def transfer_bone(src, dst, start, end, relative=False):
    """The rig's bone onto the source bone's track: constrain, bake, release.

    World space by default; `relative` takes the source bone's pose relative to its
    parent onto the rig bone's parent instead (`helper_space`). The bone's own keys
    are cut FIRST: constraining a keyed channel splices a pairBlend in (trap 37's
    mechanism) and a second Bake on the same rig would otherwise blend the new take
    with the old one.
    """
    cmds.cutKey(dst, attribute=_CHANNELS, clear=True)
    driver, temp = (_parent_space_driver(src, dst) if relative else (src, []))
    constraint = cmds.parentConstraint(driver, dst)[0]
    cmds.bakeResults(dst, time=(start, end), attribute=_CHANNELS, simulation=False,
                     sampleBy=1, disableImplicitControl=True, preserveOutsideKeys=False,
                     sparseAnimCurveBake=False)
    # the relative driver's decomposed rotation wraps, so the bake keeps a
    # different euler from key to key: made continuous (2026-09-30)
    from maya_scenesetup import bonedrive
    bonedrive.euler_filter(dst)
    cmds.delete(constraint)
    for node in temp:
        if cmds.objExists(node):
            cmds.delete(node)
    cmds.delete(dst, staticChannels=True, unitlessAnimationCurves=False,
                hierarchy="none", controlPoints=False, shape=True)


def carry_helpers(source_root, rig_root, start, end, relative=False):
    """The after-bake step. Returns (moved names, skipped pairs, camera text).

    Order, each half paid for elsewhere: a standing camera setup is torn down
    first (`camera.teardown` bakes the bone back before deleting the camera)
    so its constraint cannot fight the transfer's; a weapon link is unlinked
    (the bone baked back off the sword) and relinked after the transfer, so
    the sword snaps onto the new track and takes its stored grip back -- the
    bridge's merge does exactly this; and the camera is set up LAST, on the
    bone's new track. Each rig has its own camera, on its own camera_root.
    """
    from maya_scenesetup import bonedrive, camera
    src, dst = _bones_under(source_root), _bones_under(rig_root)
    #  the camera stands on camera_root (2026-09-18); a camera an older
    #  build left on camera_bone is torn down too, or the transfer onto
    #  that bone would splice a pairBlend into our own constraint
    cam_root = dst.get(camera.BONE)
    for name in ("camera_root", "camera_bone"):
        if name in dst:
            camera.teardown(dst[name], start, end)
    links = {}
    for name in ("weapon_r", "weapon_l"):
        if name in dst:
            weapon = bonedrive.driving_weapon(dst[name])
            if weapon:
                links[dst[name]] = weapon
                bonedrive.unlink(dst[name])
    moves, skipped = helper_plan(src, dst, _foreign(dst))
    for _name, source_path, rig_path in moves:
        transfer_bone(source_path, rig_path, start, end, relative=relative)
    for bone, weapon in links.items():
        if cmds.objExists(weapon) and cmds.objExists(bone):
            bonedrive.relink(weapon, bone)
    camera_text = camera.setup(cam_root, start, end) if cam_root else ""
    return [move[0] for move in moves], skipped, camera_text


CONNECTED = ("the hands are connected to the weapon (%s) - Connections > "
             "Disconnect first")


def hands_connected(rig):
    """The refusal when the rig's IK hands ride a weapon, else "".

    A retarget's `connect` would skip the constrained IK controls as
    somebody else's constraints and the take would arrive with the hands
    standing still; the bake would lift the weapon link under them. Lazy,
    guarded import: the retarget must keep working without Scene Setup.
    """
    try:
        from maya_scenesetup import connections
    except Exception:                                        # noqa: BLE001
        return ""
    sides = connections.connected_sides(rig)
    if not sides:
        return ""
    return CONNECTED % ", ".join(connections.SIDE_LABEL[s] for s in sides)


def bake(*args, **kwargs):
    """The after-the-connect half: the module's bake, the helper bones, the camera, the disconnect.

    Six steps -- controls baked over the clip's key range (`vendor_bake`),
    a standing camera torn down, weapon links lifted, the four helper bones
    carried from the source, links restored, the module's disconnect, and
    Camera Setup on the rig's `camera_bone` -- under one undo chunk. With
    nothing connected the module says so and nothing else happens.
    """
    rig, mod, refusal = resolve(kwargs.pop("rig", None))
    if mod is None:
        return refusal
    connected = hands_connected(rig)
    if connected:
        return connected
    source = mod.connected_source(rig)
    if source is None:
        return "%s: %s" % (mod.__name__, mod.bake(*args, rig=rig, **kwargs))
    span = mod.source_key_range(rig) or (cmds.playbackOptions(query=True, min=True),
                                         cmds.playbackOptions(query=True, max=True))
    rig_root = rig.skeleton_root
    cmds.undoInfo(openChunk=True, chunkName="Retarget bake")
    try:
        note = mod.bake(disconnect=False, rig=rig).split("; still connected")[0]
        relative = helper_space(mod, rig) == "parent"
        moved, skipped, camera_text = (carry_helpers(source, rig_root, span[0], span[1], relative=True)
                                       if relative else carry_helpers(source, rig_root, span[0], span[1]))
        note += "; " + mod.disconnect(rig)
    finally:
        cmds.undoInfo(closeChunk=True)
    extra = helper_note(moved, skipped, camera_text)
    return "%s: %s%s" % (mod.__name__, note, ("; " + extra) if extra else "")


# --------------------------------------------------------------- the button

def _first_line(text):
    lines = [line for line in (text or "").splitlines() if line.strip()]
    return lines[0] if lines else ""


def _source_of(mod, rig):
    """The source root the module's holder remembers, or None."""
    try:
        return mod.connected_source(rig)
    except Exception:                                        # noqa: BLE001
        return None


def _unlabel(rig):
    """The rig's clip label gone with its take (`maya_scenesetup.cliplabel`).
    Never fails the press."""
    try:
        from maya_scenesetup import cliplabel
    except ImportError:
        return 0
    return cliplabel.clear_rig(rig)


def _relabel(rig, source):
    """The rig labelled with the clip `source` gives (its namespace, its top
    group, the clip file the scene was opened from), or unlabelled. Never
    fails the press."""
    try:
        from maya_scenesetup import cliplabel
    except ImportError:
        return None
    return cliplabel.relabel_rig(rig, source)


def run_retarget(source_root=None, rig=None, bones=None):
    """The whole retarget. Returns (ok, text).

    Which version (2026-10-02): `bones` forced, else the Retarget card's
    setting and the measured clip (`decide_for`) - asked BEFORE the reset, so
    a Cancel leaves the rig and its take exactly as they were.

    Reset first: a rig that already carries a take passes `posed_controls`
    (a keyed channel is not settable and is skipped) while standing in the
    take's pose, and a connect made there measures the pole offsets against
    that pose -- the bridge learned this on 2026-09-07 and this press is the
    same operation by hand. What is still posed afterwards is a channel the
    reset may not touch, and that IS the refusal, by name.

    A holder already standing on this rig (an interrupted press, or the
    vendor's own MoCap Matcher) is baked rather than refused: one button
    means "finish the retarget".
    """
    rig, mod, refusal = resolve(rig)
    if mod is None:
        return False, refusal
    connected = hands_connected(rig)
    if connected:
        return False, connected
    holder = mod.holder_of(rig)
    notes = []
    decision = None
    standing = cmds.objExists(holder)
    if not standing:
        import maya_retargetmode as rm
        try:
            decision = decide_for(mod, rig, source_root, bones)
        except rm.Cancelled:
            return False, "%s: %s" % (maya_rigs.label(rig), CANCELLED)
        if decision.reason:
            notes.append(decision.reason)
    cmds.undoInfo(openChunk=True, chunkName="Retarget")
    try:
        if standing:
            notes.append("already connected - baking what stands")
        else:
            curves, zeroed = mod.reset_build_pose(rig)
            # The take is gone; so is the name of the clip it was (2026-10-02,
            # cliplabel) - a refusal below must not leave the label lying.
            _unlabel(rig)
            if curves or zeroed:
                notes.append("previous take cleared (%d curves), rig at build pose" % curves)
            posed = mod.posed_controls(rig=rig)
            if posed:
                return False, "  |  ".join(notes + [
                    "%s: %s" % (POSED, ", ".join(sorted(posed)[:6]))])
            connect_text = mod.connect(source_root=source_root, rig=rig,
                                       **connect_kwargs(decision))
            if not cmds.objExists(holder):
                return False, "  |  ".join(notes + ["retarget refused: " + _first_line(connect_text)])
            notes.append(_first_line(connect_text))
        source = _source_of(mod, rig)
        notes.append(bake(rig=rig))
        if not cmds.objExists(holder):
            # Baked: the rig plays the source's take now, so its label names
            # that source - or goes, when the source gives no name.
            _relabel(rig, source)
    finally:
        cmds.undoInfo(closeChunk=True)
    return True, "%s: %s" % (maya_rigs.label(rig), "  |  ".join(notes))


def retarget(source_root=None, rig=None):
    """The Retarget button's text."""
    return run_retarget(source_root, rig)[1]


# ------------------------------------------------------------ shelf button

HUB_SECTION = "retarget"            # our section of the SkeldarAnim hub
STATUS = "skeldarRetargetStatus"    # exists exactly while the panel is built

PANEL_NOTE = ("Select the imported skeleton (any joint), and a control of "
              "the rig when the scene holds several. The rig takes the "
              "clip: retarget, bake, weapon and camera bones carried, "
              "camera set up. The source skeleton is kept.")
#  What the panel shows (2026-09-28, the skin); PANEL_NOTE is the tooltip.
PANEL_HINT = "Select the clip's skeleton (and the rig, when several)"


def _show(text):
    """The first line in the viewport and on the panel's status line, the
    whole text in the Script Editor.

    A shelf button has no status line of its own; the print is the record
    and the in-view message is what the animator sees. Guarded: mayapy
    and a hidden viewport have nowhere to draw it.
    """
    print(text)
    first = text.splitlines()[0] if text.strip() else ""
    try:
        if cmds.control(STATUS, exists=True):
            cmds.text(STATUS, edit=True, label=first)
    except Exception:
        pass
    try:
        cmds.inViewMessage(assistMessage=text.splitlines()[0],
                           position="midCenterBot", fade=True)
    except Exception:
        pass
    return text


def retarget_button():
    """The Retarget shelf button: the rig takes the SELECTED skeleton's clip."""
    return _show(retarget())


# ------------------------------------------------------------- hub section

def is_open():
    """True while our section is built in the hub."""
    return bool(cmds.control(STATUS, exists=True))


def _press(*_args):
    """The panel's button: the shelf button's work, failures on the line."""
    try:
        return retarget_button()
    except Exception as exc:                                  # noqa: BLE001
        _show("%s: %s" % (type(exc).__name__, exc))
        raise


def show_window():
    """Open the SkeldarAnim hub on the Retarget section (see `maya_hub`)."""
    import maya_hub
    return maya_hub.show(HUB_SECTION)


BONES = "skeldarRetargetBones"      # the version segments' collection
BONES_NOTES = {
    "auto": "The clip's twin is retargeted exactly, squash & stretch. Any other "
            "body is asked: keep its proportions (rotations) or squash & "
            "stretch to the clip.",
    "rotation": "Rotations: every bone turns as the clip's and keeps its own "
                "length - never asked.",
    "stretch": "Squash & stretch: every bone lands on the clip's joint and "
               "takes its length - never asked.",
}


def bones_button(value):
    """The Bones segment of a setting ("auto" / "rotation" / "stretch")."""
    return "{0}_{1}".format(BONES, value)


def _set_bones(value):
    import maya_retargetmode as rm
    rm.set_setting(value)
    _show("retarget version: %s" % rm.LABELS[value])


def _bones_row():
    """[Auto | Rotations | Stretch] - the retarget version (2026-10-02), the
    setting every press reads (`maya_retargetmode.setting`), remembered in
    its optionVar; built into the Retarget card only (the Animation Setup
    card's import rows are another session's work this day, and the setting
    is one for every press)."""
    import maya_retargetmode as rm
    current = rm.setting()
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=2,
                   columnAttach=[(1, "left", 0), (2, "both", 4)])
    cmds.text(label="Bones", align="left",
              annotation="Which retarget the presses run - Auto decides")
    segments = cmds.rowLayout(numberOfColumns=len(rm.SETTINGS),
                              columnAttach=[(i + 1, "both", 1)
                                            for i in range(len(rm.SETTINGS))])
    hubstyle.mark(segments, "segments", layout=True)
    cmds.iconTextRadioCollection(BONES)
    for value in rm.SETTINGS:
        hubstyle.mark(cmds.iconTextRadioButton(
            bones_button(value), style="textOnly", label=rm.LABELS[value],
            height=22, select=value == current, annotation=BONES_NOTES[value],
            onCommand=lambda *_a, v=value: _set_bones(v)), "segment")
    cmds.setParent("..")
    cmds.setParent("..")


def build_panel():
    """One instruction, one button, one status line - the shelf button's
    action with somewhere to report (2026-09-17, the hub)."""
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=6,
                               columnOffset=("both", hubstyle.pick(0, 8)))
    #  One line since the skin (2026-09-28): the paragraph is the tooltip.
    hubstyle.mark(cmds.text(label=PANEL_HINT, align="left", wordWrap=True,
                            height=36), "note")
    _bones_row()
    hubstyle.mark(cmds.button(label="Retarget", height=34,
                              backgroundColor=(0.45, 0.60, 0.70),
                              annotation=PANEL_NOTE, command=_press),
                  "primary", "arrows-exchange")
    hubstyle.mark(cmds.text(STATUS, label="", align="left", wordWrap=True,
                            height=36), "status")
    cmds.setParent("..")
    return column
