"""Our nodes that carry a marker attribute, found without combing the scene every time
(2026-10-27).

`cmds.ls("*.<marker>", recursive=True)` asks every node of the scene for the
attribute - ~12 ms with three rigs, more with more - and the card on show asked it
on every selection (Dynamics twice, Center of Mass, Ragdoll's arrows). The answer is
kept per marker until the scene changes: a node added or removed, a scene opened,
imported, referenced or made new, an undo or a redo, or one of ours marked by our
own code (`touch()`, which every writer of a marker this module answers for calls).
It is kept as UUIDs and resolved again at each ask - a rename or a reparent costs
nothing - and a kept node that has lost its marker is left out.

When the scene's callbacks cannot be installed (a fake cmds, batch quirks) every ask
combs the scene, as before. The state and the callbacks live on `sys`, so a module
purged by an install keeps one set (trap 111).
"""

import sys

import maya.cmds as cmds


def _state():
    return sys.__dict__.setdefault("_skeldar_markers",
                                   {"gen": 0, "found": {}, "callbacks": None})


def touch(*_args):
    """The scene's marked nodes may have changed: every kept answer asks again."""
    _state()["gen"] += 1


def _install():
    """The callbacks that bump the generation; True once they stand."""
    state = _state()
    if state["callbacks"] is not None:
        return bool(state["callbacks"])
    ids = []
    try:
        import maya.api.OpenMaya as om
        ids.append(om.MDGMessage.addNodeAddedCallback(touch, "dependNode"))
        ids.append(om.MDGMessage.addNodeRemovedCallback(touch, "dependNode"))
        for event in ("Undo", "Redo"):
            ids.append(om.MEventMessage.addEventCallback(event, touch))
        scene = om.MSceneMessage
        for kind in ("kAfterOpen", "kAfterNew", "kAfterImport", "kAfterReference",
                     "kAfterRemoveReference", "kAfterLoadReference", "kAfterUnloadReference"):
            if hasattr(scene, kind):
                ids.append(scene.addCallback(getattr(scene, kind), touch))
    except Exception:                                        # noqa: BLE001 - no API: comb every time
        try:
            import maya.api.OpenMaya as om
            for cid in ids:
                om.MMessage.removeCallback(cid)
        except Exception:                                    # noqa: BLE001
            pass
        state["callbacks"] = False
        return False
    state["callbacks"] = ids
    return True


def _scan(marker, node_type=None, commands=None):
    flags = {"recursive": True, "objectsOnly": True, "long": True}
    if node_type:
        flags["type"] = node_type
    return sorted(set((commands or cmds).ls("*." + marker, **flags) or []))


def find(marker, node_type=None, commands=None):
    """Long paths of the nodes carrying `marker` (of `node_type` when given).
    `commands`: the caller's cmds - another one (a test's fake) is asked every time."""
    if commands is not None and commands is not cmds:
        return _scan(marker, node_type, commands)
    if not _install():
        return _scan(marker, node_type)
    state = _state()
    key = (marker, node_type)
    kept = state["found"].get(key)
    if kept is not None and kept[0] == state["gen"]:
        uuids = kept[1]
        if not uuids:
            return []
        paths = cmds.ls(uuids, long=True) or []
        if not paths:
            return []
        still = cmds.ls([p + "." + marker for p in paths], objectsOnly=True, long=True) or []
        return sorted(set(still))
    gen = state["gen"]
    found = _scan(marker, node_type)
    uuids = (cmds.ls(found, uuid=True) or []) if found else []
    state["found"][key] = (gen, list(uuids))
    return found


def forget():
    """Every kept answer dropped (and the callbacks removed): tests, a reload."""
    state = _state()
    state["found"] = {}
    ids = state.get("callbacks") or []
    if ids:
        try:
            import maya.api.OpenMaya as om
            for cid in ids:
                om.MMessage.removeCallback(cid)
        except Exception:                                    # noqa: BLE001
            pass
    state["callbacks"] = None
