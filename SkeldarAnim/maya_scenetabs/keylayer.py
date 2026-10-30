"""BaseAnimation selected whenever no animation layer is (2026-10-27).

«перевір чому не працює авто кі»: with no layer selected Maya keys - autokey and S alike - into its
own "best" layer, and in the animator's scenes that is the MUTED additive `_3P_Upper_Body`: the key
lands there, nothing shows, and the pose snaps back on the next frame (measured in mayapy, in a tab
and in a plain file alike). With BaseAnimation selected the key lands on the base. Asked: «Make the
tool select BaseAnimation automatically when no layer is selected».

A layer deselection ends in Maya's `animLayerRefresh` (measured live); that, a scene opened and a new
scene check the selection one idle later and select the root - the session's while tabs are on, which
the Layer Editor shows as BaseAnimation - through the editor's own click (`animLayerEditorOnSelect`), so
the editor's highlight follows. A scene with no layers is left alone. GUI only; never raises.

2026-10-30, «перевір чому не ставляться авто кі» again, measured live: the selected (and preferred)
layer was the tab's own root, `<tab>:AnimLayerRoot` - a file's BaseAnimation keeps its selection when
it comes into a tab, but there it is a plain layer holding no channel, hidden from the Layer Editor.
Nothing looked selected, `animLayer -q -bestAnimLayer` answered the muted `_3P_Upper_Body`, and the
check above saw a selection. A tab's own root counts as nothing selected: it is let go first (the
editor's click only walks the layers it lists) and the root clicked.
"""

import sys
import traceback

import maya.cmds as cmds

from . import layers as tablayers

EVENTS = ("animLayerRefresh", "SceneOpened", "NewSceneOpened")


def needs_base(root, selected, holders=()):
    """Is the root to be selected: layers exist (`root`) and none of the `selected` is one but a tab's
    own root (`holders`). Pure."""
    return bool(root) and not [layer for layer in selected if layer not in holders]


def holders(root, layers, parent_of):
    """The tabs' own roots among `layers`: an `AnimLayerRoot` hanging on `root`. Pure."""
    return [layer for layer in layers
            if layer != root and tablayers.is_tab_root_name(layer) and (parent_of(layer) or "") == root]


def _st():
    state = getattr(sys, "_skeldar_keylayer", None)
    if state is None:
        state = {"jobs": [], "pending": False}
        sys._skeldar_keylayer = state
    return state


def ensure():
    """The root selected when no layer is (a tab's own root let go). True when it selected it."""
    root = cmds.animLayer(query=True, root=True)
    if not root:
        return False
    layers = cmds.ls(type="animLayer") or []
    selected = [l for l in layers if cmds.animLayer(l, query=True, selected=True)]
    held = holders(root, layers, lambda l: cmds.animLayer(l, query=True, parent=True))
    if not needs_base(root, selected, held):
        return False
    for layer in selected:
        cmds.animLayer(layer, edit=True, selected=False, preferred=False)
    import maya.mel as mel
    if mel.eval('exists "animLayerEditorOnSelect"'):
        mel.eval('animLayerEditorOnSelect("%s", 1)' % root)
    else:
        cmds.animLayer(root, edit=True, selected=True, preferred=True)
    return bool(cmds.animLayer(root, query=True, selected=True))


def _later():
    state = _st()
    if state["pending"]:
        return
    state["pending"] = True

    def run():
        state["pending"] = False
        try:
            ensure()
        except Exception:                                    # noqa: BLE001
            print(traceback.format_exc())
    import maya.utils
    maya.utils.executeDeferred(run)


def install():
    """The jobs, once (an update's reload replaces the old module's)."""
    if cmds.about(batch=True):
        return False
    remove()
    _st()["jobs"] = [cmds.scriptJob(event=(event, _later)) for event in EVENTS]
    _later()
    return True


def remove():
    state = _st()
    for job in state["jobs"]:
        try:
            if cmds.scriptJob(exists=job):
                cmds.scriptJob(kill=job, force=True)
        except RuntimeError:
            pass
    state["jobs"] = []
