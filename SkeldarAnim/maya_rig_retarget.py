"""One shelf button for every AdvancedSkeleton rig we drive: select the imported skeleton, press.

The animator's button ran `maya_asretarget.connect()` -- the Manny rig's retarget -- and
on the Lugal (PlayerMale) rig that module can only refuse: the bones it maps are UE's.
This picks the module from the rig the scene holds and forwards to it, so the press is
the same on `manny_rig_02` and on `Lugal_Rig_01` (2026-09-06, «я просто выделяю скелет,
нажимаю на скрипт и ретаргет готов. Точно так же я хочу и для Lugal_Rig_01»).

    import sys; sys.path.append(r"C:/!!!Work/MayaScripts")
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


def bake(*args, **kwargs):
    return _forward("bake", *args, **kwargs)


def disconnect(*args, **kwargs):
    return _forward("disconnect", *args, **kwargs)
