"""Scene tabs, stage 1: the proof in mayapy standalone (2026-10-15).

Run from the repo root (PowerShell):
  $env:MAYA_APP_DIR = "$env:TEMP\\skeldar_tabs_appdir"
  & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/verify_scene_tabs.py all
Phases: session layers_alone convert layers open_close switch save hooks restore hook_failures review, or "all".
Every gate prints PASS / FAIL; the last line is "N of M gates failed".
Spec: docs/superpowers/specs/2026-10-15-scene-tabs-design.md
"""
import builtins
import os
import shutil
import sys
import tempfile
import traceback

import maya.standalone
maya.standalone.initialize()
import maya.cmds as cmds  # noqa: E402

for _plug in ("matrixNodes", "quatNodes"):
    cmds.loadPlugin(_plug, quiet=True)

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
PLUGIN = os.path.join(REPO, "SkeldarAnim").replace("\\", "/")
sys.path.insert(0, PLUGIN)

from maya_scenetabs import records, session  # noqa: E402

WORK = os.path.join(tempfile.gettempdir(), "skeldar_tabs_verify").replace("\\", "/")
RUN = WORK + "/run"
RESULTS = []
QUEUE = []


def gate(name, ok, detail=""):
    RESULTS.append(bool(ok))
    print("%s  %s  %s" % ("PASS" if ok else "FAIL", name, detail))


def flush():
    """Run what the hooks deferred (executeDeferred never runs in mayapy)."""
    while QUEUE:
        QUEUE.pop(0)()


def fresh():
    """An empty scene, the hooks off, no namespace left. Maya keeps a namespace
    alive across `file -new` when the managers an import made sit in it (trap
    158): the next phase's tab would then be `tab_rig1` and nest the leftovers."""
    try:
        from maya_scenetabs import hooks
        hooks.remove()
    except Exception:                                           # noqa: BLE001
        pass
    cmds.file(new=True, force=True)
    found = [n for n in cmds.namespaceInfo(":", listOnlyNamespaces=True, recurse=True) or []
             if n.split(":")[0] not in records.SYSTEM_NAMESPACES]
    for name in sorted(found, key=lambda n: -n.count(":")):
        if cmds.namespace(exists=":" + name):
            cmds.namespace(removeNamespace=":" + name, mergeNamespaceWithRoot=True)
    cmds.undoInfo(state=True, infinity=True)


def copy(name, as_name=None):
    """A fixture copied into the run folder (tabs edit and save their files)."""
    os.makedirs(RUN, exist_ok=True)
    target = RUN + "/" + (as_name or name)
    shutil.copyfile(WORK + "/" + name, target)
    return target


def _save(path, kind="mayaAscii"):
    cmds.file(rename=path)
    cmds.file(save=True, type=kind, force=True)


def fixtures():
    """rig.ma / rig.mb: a Manny rig, ntsc, 0-50 / 0-60, FKShoulder_R keyed.
    film.ma: film, a cube with an animation layer and a display layer, a
    camera, a nested reference to ref.ma, an open-type script node, 5-40 / 0-45.
    plain.mb: ntscf, a keyed sphere, 0-24. Built once per WORK folder."""
    os.makedirs(WORK, exist_ok=True)
    done = WORK + "/fixtures.done"
    if os.path.exists(done):
        return
    cmds.file(new=True, force=True)
    cmds.currentUnit(time="film")
    box = cmds.polyCube(name="box")[0]
    cmds.setKeyframe(box, attribute="translateX", time=10, value=0)
    cmds.setKeyframe(box, attribute="translateX", time=30, value=10)
    _save(WORK + "/ref.ma")

    cmds.file(new=True, force=True)
    cmds.currentUnit(time="film")
    cmds.file(WORK + "/ref.ma", reference=True, namespace="ref")
    hero = cmds.polyCube(name="hero")[0]
    cmds.setKeyframe(hero, attribute="translateY", time=5, value=0)
    cmds.setKeyframe(hero, attribute="translateY", time=40, value=4)
    cmds.select(hero)
    layer = cmds.animLayer("Layer1", addSelectedObjects=True)
    cmds.setKeyframe(hero + ".rotateY", time=20, value=45, animLayer=layer)
    cmds.createDisplayLayer(hero, name="cubesLayer", noRecurse=True)
    cmds.camera(name="shotCam")
    cmds.scriptNode(name="opener", scriptType=1, sourceType="mel",
                    beforeScript='python("import builtins; builtins.SKELDAR_TABS_RAN = True")')
    cmds.playbackOptions(minTime=5, maxTime=40, animationStartTime=0, animationEndTime=45)
    _save(WORK + "/film.ma")

    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntsc")
    from maya_scenesetup import catalog, character
    character.add_character(catalog.default_rig())
    control = cmds.ls("*:FKShoulder_R", long=True)[0]
    cmds.setKeyframe(control, attribute="rotateZ", time=0, value=0)
    cmds.setKeyframe(control, attribute="rotateZ", time=20, value=40)
    cmds.playbackOptions(minTime=0, maxTime=50, animationStartTime=0, animationEndTime=60)
    _save(WORK + "/rig.ma")
    _save(WORK + "/rig.mb", "mayaBinary")

    cmds.file(new=True, force=True)
    cmds.currentUnit(time="ntscf")
    ball = cmds.polySphere(name="ball")[0]
    cmds.setKeyframe(ball, attribute="translateX", time=0, value=0)
    cmds.setKeyframe(ball, attribute="translateX", time=24, value=12)
    cmds.playbackOptions(minTime=0, maxTime=24, animationStartTime=0, animationEndTime=24)
    _save(WORK + "/plain.mb", "mayaBinary")
    open(done, "w").close()


def value_at(plug, frame):
    """A plug's value after a real time change (getAttr(time=) skips layer blends, trap 232)."""
    cmds.currentTime(frame)
    return round(cmds.getAttr(plug), 4)


def summary(path, probes=()):
    """What a scene file holds, read by opening it alone (the hooks off)."""
    fresh()
    cmds.file(path, open=True, force=True)
    defaults = set(cmds.ls(defaultNodes=True) or [])
    #  Maya names layer curves and blend nodes by rules of its own (a tab's
    #  file got `Layer4_inputB` where the same edit made directly got
    #  `hero_translateX_Layer2_inputB`, measured): they are compared by their
    #  keys and by the value probes, not by name.
    unnamed = set(cmds.ls(type=("animCurve", "animBlendNodeBase")) or [])
    startup = [c for c in cmds.ls(type="camera") or [] if cmds.camera(c, q=True, startupCamera=True)]
    unnamed |= set(startup) | set(cmds.listRelatives(startup, parent=True) or [])     # Maya makes them on open
    names = sorted(n for n in cmds.ls()
                   if n not in defaults and n not in unnamed and not cmds.referenceQuery(n, isNodeReferenced=True)
                   and cmds.nodeType(n) != "script"
                   and not records.is_furniture(n.split("|")[-1].split(":")[-1], cmds.nodeType(n)))
    keys = []
    for curve in cmds.ls(type="animCurve") or []:
        if not cmds.referenceQuery(curve, isNodeReferenced=True):
            pairs = cmds.keyframe(curve, q=True, timeChange=True, valueChange=True) or []
            keys.append([round(v, 4) for v in pairs])
    keys.sort()
    layer_tree = {l: cmds.animLayer(l, q=True, parent=True) for l in cmds.ls(type="animLayer") or []}
    refs = sorted((cmds.referenceQuery(r, namespace=True),
                   os.path.basename(cmds.referenceQuery(r, filename=True, withoutCopyNumber=True)))
                  for r in cmds.ls(type="reference") or []
                  if not r.endswith("sharedReferenceNode") and not cmds.referenceQuery(r, isNodeReferenced=True))
    displays = {d: sorted(cmds.editDisplayLayerMembers(d, q=True, fullNames=False) or [])
                for d in cmds.ls(type="displayLayer") or [] if d != "defaultLayer"}
    solved = all(cmds.listConnections(h + ".ikSolver") for h in cmds.ls(type="ikHandle") or [])
    values = {"%s@%s" % (plug, frame): value_at(plug, frame) for plug, frame in probes}
    return {"names": names, "keys": keys, "layers": layer_tree, "refs": refs, "displays": displays,
            "ik_solved": solved, "values": values, "unit": cmds.currentUnit(q=True, time=True),
            "ranges": [cmds.playbackOptions(q=True, minTime=True), cmds.playbackOptions(q=True, maxTime=True),
                       cmds.playbackOptions(q=True, animationStartTime=True),
                       cmds.playbackOptions(q=True, animationEndTime=True)]}


def scene_is(path):
    return records.same_file(cmds.file(q=True, sceneName=True), path)


def current_ns():
    return cmds.namespaceInfo(currentNamespace=True).lstrip(":")


# ------------------------------------------------------------------ phases

def phase_convert():
    """The open scene becomes tab 1 and back, every name exact."""
    from maya_scenetabs import opening
    import maya_rigs
    path = copy("rig.ma")
    fresh()
    cmds.file(path, open=True, force=True)
    before = sorted(cmds.ls())
    state = opening.start()
    gate("convert: tab 1 is tab_rig", state["active"] == "tab_rig", state["active"])
    gate("convert: the rig is in the tab", [r.namespace for r in maya_rigs.rigs()] == ["tab_rig:Manny_Rig"],
         [r.namespace for r in maya_rigs.rigs()])
    gate("convert: nothing of the scene is left in the root namespace", session.own_nodes("") == [],
         cmds.ls(session.own_nodes("")))
    gate("convert: the scene is the session", scene_is(state["session"]), cmds.file(q=True, sceneName=True))
    gate("convert: the tab's namespace is current", current_ns() == "tab_rig", current_ns())
    gate("convert: the key plays", value_at("tab_rig:Manny_Rig:FKShoulder_R.rotateZ", 20) == 40.0)
    message = opening.finish()
    gate("finish: back to one scene, every name exact", sorted(cmds.ls()) == before,
         sorted(set(cmds.ls()) ^ set(before))[:10])
    gate("finish: the scene is rig.ma again", scene_is(path), message)
    gate("finish: no session node", not session.exists())


def phase_session():
    """session alone: move_into and lift/lower round trips on the rig scene."""
    path = copy("rig.ma")
    fresh()
    cmds.file(path, open=True, force=True)
    before = sorted(cmds.ls())
    moved = session.move_into("tab_rig")
    gate("session: move_into empties the root namespace", session.own_nodes("") == [])
    gate("session: the rig's namespace moved under the tab", cmds.namespace(exists=":tab_rig:Manny_Rig"))
    lifted = session.lift("tab_rig")
    gate("session: lift brings it back to the root", sorted(cmds.ls()) == before)
    session.lower(lifted)
    gate("session: lower puts it in the tab again", session.own_nodes("") == [] and
         cmds.namespace(exists=":tab_rig:Manny_Rig"))
    cmds.createNode("transform", name=":Manny_Rig_Character")
    try:
        session.lift("tab_rig")
        refused = ""
    except session.TabError as exc:
        refused = str(exc)
    gate("session: a clash refuses by name", "Manny_Rig_Character" in refused, refused)
    gate("session: a refused lift leaves the tab whole",
         cmds.objExists("tab_rig:Manny_Rig_Character") and cmds.namespace(exists=":tab_rig:Manny_Rig"))


def layer_parent(layer):
    return cmds.animLayer(layer, q=True, parent=True) or ""


def phase_layers_alone():
    """layers without tabs: the film scene's root handed to the session and back."""
    from maya_scenetabs import layers
    path = copy("film.ma")
    fresh()
    cmds.file(path, open=True, force=True)
    children = layers.take_root()
    gate("layers: the session takes the root", layers.root() == records.LAYER_ROOT, layers.root())
    session.move_into("tab_film")
    made = layers.give_children("tab_film", children)
    gate("layers: the tab's root under the session's", made == "tab_film:AnimLayerRoot"
         and layer_parent(made) == records.LAYER_ROOT, made)
    gate("layers: the tab's layer under the tab's root", layer_parent("tab_film:Layer1") == made)
    gate("layers: the layer still plays", value_at("tab_film:hero.rotateY", 20) == 45.0)
    blends = sorted(cmds.ls(type="animBlendNodeBase") or [])
    links = layers.detach(made)
    gate("layers: detach cuts the tab root free", len(links) == 5 and layer_parent(made) == "", links)
    layers.attach(links)
    gate("layers: attach puts it back, no blend node rebuilt",
         layer_parent(made) == records.LAYER_ROOT and sorted(cmds.ls(type="animBlendNodeBase") or []) == blends)
    cmds.select("tab_film:hero")
    cmds.namespace(setNamespace=":tab_film")
    fresh_layer = cmds.animLayer("Fresh", addSelectedObjects=True)
    cmds.namespace(setNamespace=":")
    gate("layers: Maya parents a new layer to the session root", layer_parent(fresh_layer) == records.LAYER_ROOT)
    gate("layers: adopt moves it under the tab's root", layers.adopt(fresh_layer, "tab_film")
         and layer_parent(fresh_layer) == made)
    layers.flatten("tab_film")
    gate("layers: flatten - BaseAnimation is the root again", layers.root() == "BaseAnimation")
    gate("layers: flatten - the layers under it, the tab root gone",
         layer_parent("tab_film:Layer1") == "BaseAnimation" and not cmds.objExists(made))
    gate("layers: flatten - the layer still plays", value_at("tab_film:hero.rotateY", 20) == 45.0)


def tops_visible(namespace):
    from maya_scenetabs import switching
    return [cmds.getAttr(t + ".lodVisibility") for t in switching.tops(namespace)]


def phase_layers():
    """Three tabs with layers: the session owns the root; closing tab 1 leaves the others; back to one scene."""
    from maya_scenetabs import layers, opening, switching
    film, film_b, film_c = copy("film.ma"), copy("film.ma", "film_b.ma"), copy("film.ma", "film_c.ma")
    fresh()
    cmds.file(film, open=True, force=True)
    opening.open_tab(film_b)
    opening.open_tab(film_c)
    gate("layers: the session owns the root", layers.root() == records.LAYER_ROOT, layers.root())
    names = ("tab_film", "tab_film_b", "tab_film_c")
    roots = [ns + ":" + records.TAB_LAYER_ROOT for ns in names]
    active = session.state()["active"]
    #  2026-10-15: a hidden tab's root is cut off the session's (out of the Layer Editor)
    gate("layers: each tab has its own root - the active one under the session's, the hidden ones cut off",
         all(cmds.objExists(r) for r in roots)
         and all((layer_parent(r) == records.LAYER_ROOT) == (ns == active)
                 and (ns == active or cmds.attributeQuery(layers.OUT_ATTR, node=r, exists=True))
                 for ns, r in zip(names, roots)), [(r, layer_parent(r)) for r in roots])
    gate("layers: each tab's layer under its own root",
         all(layer_parent(ns + ":Layer1") == r for ns, r in zip(("tab_film", "tab_film_b", "tab_film_c"), roots)))
    gate("layers: every tab plays its layer",
         [value_at(ns + ":hero.rotateY", 20) for ns in ("tab_film", "tab_film_b", "tab_film_c")] == [45.0] * 3)
    opening.close_tab("tab_film", ask=False)
    gate("layers: closing tab 1 keeps the root", layers.root() == records.LAYER_ROOT)
    gate("layers: closing tab 1 keeps the others' layers",
         layer_parent("tab_film_b:Layer1") == "tab_film_b:" + records.TAB_LAYER_ROOT
         and value_at("tab_film_b:hero.rotateY", 20) == 45.0)
    switching.switch("tab_film_b")
    cmds.select("tab_film_b:hero")
    made = cmds.animLayer("Fresh", addSelectedObjects=True)
    gate("layers: a new layer after closing tab 1, no crash", cmds.objExists(made), made)
    layers.adopt(made, "tab_film_b")
    gate("layers: adopted under the active tab's root", layer_parent(made) == layers.tab_root("tab_film_b"))
    opening.close_tab("tab_film_c", ask=False)
    gate("layers: back to one scene - BaseAnimation is the root", layers.root() == "BaseAnimation", layers.root())
    gate("layers: back to one scene - both layers under it",
         layer_parent("Layer1") == "BaseAnimation" and layer_parent("Fresh") == "BaseAnimation")
    gate("layers: back to one scene - the layer plays", value_at("hero.rotateY", 20) == 45.0)


def phase_open_close():
    """Three tabs from three kinds of file; a reload; closing; back to one scene."""
    from maya_scenetabs import opening, switching
    import maya_rigs
    rig, film, plain = copy("rig.ma"), copy("film.ma"), copy("plain.mb")
    fresh()
    cmds.file(new=True, force=True)
    cmds.polyCube(name="infected")
    cmds.scriptNode(name="vaccine_gene", scriptType=1, sourceType="python", beforeScript="pass")
    vaccine = RUN + "/vaccine.ma"
    _save(vaccine)
    fresh()
    cmds.file(rig, open=True, force=True)
    builtins.SKELDAR_TABS_RAN = False
    opening.open_tab(film)
    opening.open_tab(plain)
    state = session.state()
    gate("open: three tabs in order", [t["ns"] for t in state["tabs"]] == ["tab_rig", "tab_film", "tab_plain"],
         [t["ns"] for t in state["tabs"]])
    gate("open: units read from the files", [t["unit"] for t in state["tabs"]] == ["ntsc", "film", "ntscf"],
         [t["unit"] for t in state["tabs"]])
    gate("open: the film's ranges read from its file", records.tab(state, "tab_film")["ranges"] ==
         {"minTime": 5.0, "maxTime": 40.0, "animationStartTime": 0.0, "animationEndTime": 45.0},
         records.tab(state, "tab_film")["ranges"])
    gate("open: the nested reference stays a reference",
         cmds.referenceQuery("tab_film:refRN", namespace=True) == ":tab_film:ref")
    gate("open: the file's script node did not run", not builtins.SKELDAR_TABS_RAN)
    gate("open: only the active tab shows",
         tops_visible("tab_plain") and all(tops_visible("tab_plain")) and not any(tops_visible("tab_rig"))
         and not any(tops_visible("tab_film")))
    gate("open: hidden tabs are out of the outliner",
         all(cmds.getAttr(t + ".hiddenInOutliner") for t in switching.tops("tab_rig")))
    gate("open: the active tab's unit is the scene's", cmds.currentUnit(q=True, time=True) == "ntscf")
    gate("open: keys on whole frames in their own unit",
         cmds.keyframe("tab_plain:ball.translateX", q=True, timeChange=True) == [0.0, 24.0])
    gate("open: a hidden tab's rig is not the active tab's (stage 2)", maya_rigs.rigs() == [],
         [r.namespace for r in maya_rigs.rigs()])
    switching.switch("tab_film")
    cmds.setAttr("tab_film:hero.translateZ", 5)
    opening.ASK = lambda message, buttons: "Reload"
    message = opening.reload_tab()
    opening.ASK = None
    gate("reload: the tab's changes dropped, read from disk", cmds.getAttr("tab_film:hero.translateZ") == 0.0
         and session.state()["active"] == "tab_film", message)
    gate("reload: still in its own unit, its layer playing", cmds.currentUnit(q=True, time=True) == "film"
         and value_at("tab_film:hero.rotateY", 20) == 45.0)
    switching.switch("tab_plain")
    real_delete = opening._delete_namespace

    def failing(namespace):
        raise RuntimeError("boom")
    opening._delete_namespace = failing
    try:
        opening.close_tab("tab_plain")
        raised = False
    except RuntimeError:
        raised = True
    finally:
        opening._delete_namespace = real_delete
    after = session.state()
    gate("close: a failed delete re-raises and the session matches the scene",
         raised and after["active"] == "tab_film" and records.tab(after, "tab_plain") is not None
         and cmds.namespace(exists=":tab_plain") and not any(tops_visible("tab_plain")),
         (raised, after["active"]))
    opening.close_tab("tab_plain")
    gate("close: the tab's namespace is gone", not cmds.namespace(exists=":tab_plain"))
    gate("close: the right-hand neighbour - none - so the left one is active",
         session.state()["active"] == "tab_film")
    cmds.setAttr("tab_film:hero.translateX", 3)
    opening.ASK = lambda message, buttons: "Cancel"
    message = opening.close_tab("tab_film")
    gate("close: Cancel keeps a modified tab", cmds.namespace(exists=":tab_film") and "cancelled" in message, message)
    opening.ASK = lambda message, buttons: "Don't Save"
    message = opening.close_tab("tab_film")
    opening.ASK = None
    gate("close: down to one tab is one ordinary scene", not session.exists() and scene_is(rig), message)
    gate("close: its names are plain again", [r.namespace for r in maya_rigs.rigs()] == ["Manny_Rig"])
    gate("close: no tab namespace left", not [n for n in cmds.namespaceInfo(":", listOnlyNamespaces=True) or []
                                              if n.startswith(records.TAB_PREFIX)])
    # two tabs: rig (tab 1), film (active)
    opening.open_tab(film)
    opening.open_tab(vaccine)
    gate("open: the vaccine script node was swept, not just not run",
         not [s for s in cmds.ls(type="script") if "vaccine" in s.split(":")[-1].lower()]
         and cmds.objExists("tab_vaccine:infected"), (cmds.ls(type="script"), cmds.namespaceInfo(":", listOnlyNamespaces=True)))
    opening.close_tab("tab_vaccine", ask=False)
    gate("close: back to the film tab", session.state()["active"] == "tab_film")
    def film_keys():
        return [(c, cmds.keyframe(c, q=True, timeChange=True), cmds.keyframe(c, q=True, valueChange=True))
                for c in sorted(cmds.ls("tab_film:*", type="animCurve"))]
    keys_before = film_keys()
    opening.reload_tab("tab_rig", ask=False)
    keys_after = film_keys()
    gate("reload: a non-active tab in another unit leaves the active tab's keys and the unit alone",
         keys_before and keys_before == keys_after and cmds.currentUnit(q=True, time=True) == "film"
         and session.state()["active"] == "tab_film", (keys_before, keys_after))
    opening.close_tab("tab_rig", ask=False)
    gate("close: closing the non-active one leaves the survivor an ordinary shown scene",
         not session.exists() and cmds.getAttr("hero.lodVisibility") == 1
         and cmds.currentUnit(q=True, time=True) == "film"
         and cmds.playbackOptions(q=True, minTime=True) == 5.0
         and cmds.playbackOptions(q=True, maxTime=True) == 40.0)


def phase_switch():
    """Each tab keeps its own time, view and selection; Ctrl+Z past a switch brings the tab back first."""
    from maya_scenetabs import opening, switching
    rig, film = copy("rig.ma"), copy("film.ma")
    fresh()
    cmds.file(rig, open=True, force=True)
    opening.open_tab(film)
    cmds.undoInfo(state=True, infinity=True)
    rig_frame = records.tab(session.state(), "tab_rig")["frame"]
    cmds.currentTime(12)
    cmds.select("tab_film:hero")
    switching.switch("tab_rig")
    gate("switch: the rig shows, the film hides", all(tops_visible("tab_rig")) and not any(tops_visible("tab_film")))
    gate("switch: the rig's unit", cmds.currentUnit(q=True, time=True) == "ntsc")
    gate("switch: the rig's ranges", [cmds.playbackOptions(q=True, minTime=True),
                                      cmds.playbackOptions(q=True, maxTime=True),
                                      cmds.playbackOptions(q=True, animationEndTime=True)] == [0.0, 50.0, 60.0])
    gate("switch: the rig's frame", cmds.currentTime(q=True) == rig_frame, (cmds.currentTime(q=True), rig_frame))
    gate("switch: the rig's namespace is current", current_ns() == "tab_rig")
    gate("switch: the rig's keys on their ntsc frames",
         cmds.keyframe("tab_rig:Manny_Rig:FKShoulder_R.rotateZ", q=True, timeChange=True) == [0.0, 20.0])
    switching.switch("tab_film")
    gate("switch: the film's frame comes back", cmds.currentTime(q=True) == 12.0)
    gate("switch: the film's selection comes back", cmds.ls(selection=True) == ["tab_film:hero"],
         cmds.ls(selection=True))
    gate("switch: the film's keys on their film frames (its base curve: the channel is in a layer)",
         cmds.keyframe("tab_film:hero_translateY", q=True, timeChange=True) == [5.0, 40.0],
         cmds.keyframe("tab_film:hero_translateY", q=True, timeChange=True))
    cmds.setAttr("tab_film:hero.translateX", 2)
    switching.switch("tab_rig")
    cmds.setAttr("tab_rig:Manny_Rig:FKShoulder_L.rotateY", 10)
    cmds.undo()
    gate("undo: the rig's step undone, still on the rig",
         cmds.getAttr("tab_rig:Manny_Rig:FKShoulder_L.rotateY") == 0.0 and session.state()["active"] == "tab_rig")
    cmds.undo()
    cmds.undo()
    gate("undo: the next Ctrl+Z stops at the rig's fence - no switch, the film's step kept (2026-10-19)",
         session.state()["active"] == "tab_rig" and cmds.currentUnit(q=True, time=True) == "ntsc"
         and all(tops_visible("tab_rig")) and not any(tops_visible("tab_film")))
    cmds.redo()
    gate("redo: the rig's step again",
         session.state()["active"] == "tab_rig" and cmds.getAttr("tab_rig:Manny_Rig:FKShoulder_L.rotateY") == 10.0)
    message = switching.cycle(1)
    gate("cycle: the next tab", session.state()["active"] == "tab_film", message)
    gate("cycle: wraps round", switching.cycle(1) and session.state()["active"] == "tab_rig")


PROBES = {
    "rig.ma": [("Manny_Rig:FKShoulder_L.rotateZ", 10), ("Manny_Rig:FKShoulder_R.rotateZ", 20)],
    "film.ma": [("hero.rotateY", 20), ("hero.translateX", 20), ("ref:box.translateZ", 0), ("ref:box.translateX", 20)],
    "plain.mb": [("ball.translateY", 12)],
}


def edit_rig(prefix, tab=None):
    control = prefix + "Manny_Rig:FKShoulder_L"
    cmds.setKeyframe(control, attribute="rotateZ", time=0, value=0)
    cmds.setKeyframe(control, attribute="rotateZ", time=10, value=30)
    cmds.spaceLocator(name="madeHere")
    cmds.file(WORK + "/ref.ma", i=True, namespace="Extra", preserveReferences=True, executeScriptNodes=False)


def edit_film(prefix, tab=None):
    from maya_scenetabs import layers
    hero = prefix + "hero"
    cmds.select(hero)
    layer = cmds.animLayer("Layer2", addSelectedObjects=True)
    if tab:
        layers.adopt(layer, tab)
    cmds.setKeyframe(hero + ".translateX", time=20, value=7, animLayer=layer)
    cmds.setAttr(prefix + "ref:box.translateZ", 3)
    cmds.select(clear=True)


def edit_plain(prefix, tab=None):
    cmds.setKeyframe(prefix + "ball", attribute="translateY", time=12, value=5)


EDITS = (("rig.ma", "tab_rig", edit_rig), ("film.ma", "tab_film", edit_film), ("plain.mb", "tab_plain", edit_plain))


def direct(name, edit):
    """The same edits made in the file opened on its own, saved: the expectation."""
    path = copy(name, "direct_" + name)
    fresh()
    cmds.file(path, open=True, force=True)
    edit("")
    cmds.file(save=True, force=True, type=records.FILE_TYPES[os.path.splitext(name)[1]])
    return summary(path, PROBES[name])


def phase_save():
    """Each tab saved back equals its file edited directly; refusals write nothing."""
    from maya_scenetabs import layers, opening, saving, switching
    expected = {name: direct(name, edit) for name, _, edit in EDITS}
    paths = {name: copy(name) for name, _, _ in EDITS}
    fresh()
    cmds.file(paths["rig.ma"], open=True, force=True)
    opening.open_tab(paths["film.ma"])
    opening.open_tab(paths["plain.mb"])
    for name, namespace, edit in EDITS:
        switching.switch(namespace)
        edit(namespace + ":", namespace)
    def names():
        """The session's names. Left out: a reference node - after a save it
        legitimately sits in the root (session._ref_file) - checked by its
        namespace in references(); and the layers' curves and blend nodes,
        which Maya rebuilds under names of its own during a save (measured:
        `hero_rotate_Layer2` came back `Layer10`) - checked by playing them."""
        rebuilt = set(cmds.ls(type=("animCurve", "animBlendNodeBase")) or [])
        return sorted(n for n in cmds.ls() if cmds.nodeType(n) != "reference" and n not in rebuilt)

    def references():
        return sorted(cmds.referenceQuery(r, namespace=True) for r in cmds.ls(type="reference") or []
                      if not r.endswith("sharedReferenceNode"))

    for _, namespace, _ in EDITS:
        layers.home_blends(namespace)           # what every save does first
    before, refs_before = names(), references()
    for name, namespace, _ in EDITS:
        switching.switch(namespace)
        message = saving.save_tab()
        gate("save %s: written" % namespace, message.startswith("Saved"), message)
        gate("save %s: the tab is clean" % namespace,
             not records.tab(session.state(), namespace)["modified"] and not cmds.file(q=True, modified=True))
    gate("save: the session is exactly as before the saves", names() == before,
         sorted(set(names()) ^ set(before))[:10])
    gate("save: every reference back under its tab", references() == refs_before, references())
    switching.switch("tab_film")
    gate("save: the film tab still plays both its layers in the session",
         value_at("tab_film:hero.rotateY", 20) == 45.0 and value_at("tab_film:hero.translateX", 20) == 7.0,
         (value_at("tab_film:hero.rotateY", 20), value_at("tab_film:hero.translateX", 20)))
    switching.switch("tab_rig")
    cmds.createNode("transform", name=":madeHere")
    with open(paths["rig.ma"], "rb") as handle:
        saved_rig = handle.read()
    try:
        saving.save_tab()
        refused = ""
    except session.TabError as exc:
        refused = str(exc)
    gate("save: a name the root namespace holds refuses by name", "madeHere" in refused, refused)
    with open(paths["rig.ma"], "rb") as handle:
        gate("save: the refused save wrote nothing", handle.read() == saved_rig)
    gate("save: the refused save put every name back",
         cmds.objExists("tab_rig:madeHere") and cmds.objExists("|madeHere")
         and names() == sorted(before + ["madeHere"]),
         sorted(set(names()) ^ set(before + ["madeHere"]))[:10])
    cmds.delete("|madeHere")
    switching.switch("tab_plain")
    stamp = os.path.getmtime(paths["plain.mb"]) + 20
    os.utime(paths["plain.mb"], (stamp, stamp))
    stamp = os.path.getmtime(paths["plain.mb"])                 # what NTFS kept (100 ns)
    cmds.setAttr("tab_plain:ball.translateZ", 1)
    saving.CONFIRM = lambda question: False
    message = saving.save_tab()
    saving.CONFIRM = None
    gate("save: a file changed on disk asks first; No writes nothing",
         "cancelled" in message and abs(os.path.getmtime(paths["plain.mb"]) - stamp) < 1e-3, message)
    cmds.setAttr("tab_plain:ball.translateZ", 0)
    switching.switch("tab_film")
    real_attach = layers.attach

    def failing_attach(links):
        real_attach(links)
        raise RuntimeError("injected cleanup failure")
    layers.attach = failing_attach
    try:
        saving.save_tab(path=RUN + "/film_failed_cleanup.ma", adopt=False)
        cleanup_error = ""
    except RuntimeError as exc:
        cleanup_error = str(exc)
    finally:
        layers.attach = real_attach
    gate("save: a failing cleanup step raises, and the undo state and the names are restored",
         "injected" in cleanup_error and cmds.undoInfo(q=True, stateWithoutFlush=True)
         and cmds.objExists("tab_film:hero") and not cmds.objExists("|hero")
         and not [f for f in os.listdir(RUN) if f.startswith("film_failed_cleanup") and "skeldartmp" in f],
         (cleanup_error, cmds.undoInfo(q=True, stateWithoutFlush=True)))
    # 2026-10-16, found live: with Maya's «Default file extensions» on, an export to
    # `x.ma.skeldartmp` writes `x.ma.skeldartmp.ma`, and the save died on the rename after it
    was_ext = cmds.file(q=True, defaultExtensions=True)
    cmds.file(defaultExtensions=True)
    try:
        ext_path = RUN + "/film_with_extensions.ma"
        try:
            ext_message = saving.save_tab(path=ext_path, adopt=False)
        except Exception as exc:                                # noqa: BLE001
            ext_message = "raised %s" % exc
    finally:
        cmds.file(defaultExtensions=was_ext)
    gate("save: with Maya's default file extensions on, the file is written and no temporary is left",
         ext_message.startswith("Saved") and os.path.isfile(ext_path)
         and not [f for f in os.listdir(RUN) if "skeldartmp" in f], ext_message)
    target = RUN + "/film_saved_as.ma"
    saving.save_tab(path=target)
    gate("save as: the tab takes the new path",
         records.tab(session.state(), "tab_film")["path"] == target and os.path.isfile(target))
    copy_path = RUN + "/film_copy.ma"
    saving.save_tab(path=copy_path, adopt=False)
    gate("save a copy: written, the tab keeps its path",
         os.path.isfile(copy_path) and records.tab(session.state(), "tab_film")["path"] == target)
    actual = {"rig.ma": summary(paths["rig.ma"], PROBES["rig.ma"]),
              "film.ma": summary(target, PROBES["film.ma"]),
              "plain.mb": summary(paths["plain.mb"], PROBES["plain.mb"])}
    for name in expected:
        for key in ("names", "keys", "layers", "refs", "displays", "ik_solved", "values", "unit", "ranges"):
            mine, theirs = actual[name][key], expected[name][key]
            same = mine == theirs
            if same:
                detail = ""
            elif key == "names":
                detail = "only the tab's: %s | only the direct: %s" % (sorted(set(mine) - set(theirs))[:15],
                                                                       sorted(set(theirs) - set(mine))[:15])
            else:
                detail = "tab %r / direct %r" % (mine, theirs)
            gate("save %s: %s as the same edits made directly" % (name, key), same, detail[:900])


def hooks_on():
    from maya_scenetabs import hooks
    hooks.install(force=True)
    hooks._st()["defer"] = QUEUE.append
    return hooks


def phase_hooks():
    """Maya's own Save, Save As, New and Open redirected; an autosave let through; a new layer adopted."""
    from maya_scenetabs import layers, switching
    rig, film, plain = copy("rig.ma"), copy("film.ma"), copy("plain.mb")
    fresh()
    cmds.file(rig, open=True, force=True)
    from maya_scenetabs import opening
    opening.open_tab(film)
    hooks = hooks_on()
    session_file = session.state()["session"]
    cmds.setAttr("tab_film:hero.translateX", 2)
    stamp = os.path.getmtime(film)
    try:
        cmds.file(save=True, force=True)
    except RuntimeError:
        pass                                    # «cancelled by user supplied callback»
    flush()
    gate("hooks: Maya's Save saves the active tab", os.path.getmtime(film) != stamp
         and not os.path.exists(session_file))
    gate("hooks: the scene keeps the session's name", scene_is(session_file))
    target = RUN + "/film_hook_as.ma"
    cmds.file(rename=target)
    try:
        cmds.file(save=True, force=True)
    except RuntimeError:
        pass
    flush()
    gate("hooks: Save As saves the active tab under the new name",
         os.path.isfile(target) and records.tab(session.state(), "tab_film")["path"] == target
         and scene_is(session_file))
    autosave = (cmds.autoSave(q=True, destinationFolder=True) or (RUN + "/autosave/")).replace("\\", "/")
    os.makedirs(autosave, exist_ok=True)
    auto = autosave.rstrip("/") + "/tabs_auto.ma"
    cmds.file(rename=auto)
    cmds.file(save=True, force=True, type="mayaAscii")
    cmds.file(rename=session_file)
    gate("hooks: an autosave is let through", os.path.isfile(auto) and records.holds_session(auto))
    try:
        cmds.file(new=True, force=True)
    except RuntimeError:
        pass
    flush()
    names = [t["ns"] for t in session.state()["tabs"]]
    gate("hooks: File > New opens an empty tab", names == ["tab_rig", "tab_film", "tab_untitled"]
         and cmds.namespace(exists=":tab_rig"), names)
    try:
        cmds.file(plain, open=True, force=True)
    except RuntimeError:
        pass
    flush()
    names = [t["ns"] for t in session.state()["tabs"]]
    gate("hooks: File > Open opens the file in a tab", "tab_plain" in names and cmds.objExists("tab_plain:ball"),
         names)
    switching.switch("tab_film")
    cmds.select("tab_film:hero")
    made = cmds.animLayer("ByHook", addSelectedObjects=True)
    flush()
    gate("hooks: a new layer goes under the active tab's root",
         layer_parent(made) == layers.tab_root("tab_film"), layer_parent(made))
    hooks.remove()
    gate("hooks: removed", not hooks._st()["callbacks"])


def phase_restore():
    """A session file (autosave, a crash's recovery) brings its tabs back; tabs off ends them."""
    from maya_scenetabs import hooks, layers, opening, switching
    rig, film, plain = copy("rig.ma"), copy("film.ma"), copy("plain.mb")
    fresh()
    cmds.file(rig, open=True, force=True)
    opening.open_tab(film)
    opening.open_tab(plain)
    switching.switch("tab_film")
    cmds.currentTime(15)
    switching.switch("tab_plain")
    switching.switch("tab_film")
    recovered = RUN + "/recovered_session.ma"
    with hooks.bypass():
        cmds.file(rename=recovered)
        cmds.file(save=True, force=True, type="mayaAscii")
    gate("restore: the file holds the session", records.holds_session(recovered))
    fresh()
    cmds.file(recovered, open=True, force=True)
    message = opening.restore()
    state = session.state()
    gate("restore: three tabs back", [t["ns"] for t in state["tabs"]] == ["tab_rig", "tab_film", "tab_plain"],
         message)
    gate("restore: only the active tab shows",
         all(tops_visible("tab_film")) and not any(tops_visible("tab_rig")) and not any(tops_visible("tab_plain")))
    gate("restore: the active tab's unit and frame",
         cmds.currentUnit(q=True, time=True) == "film" and cmds.currentTime(q=True) == 15.0)
    gate("restore: the scene takes the session's name", scene_is(state["session"]))
    hooks.remove()
    opening.ASK = lambda message, buttons: "Don't Save"
    message = opening.tabs_off()
    opening.ASK = None
    gate("tabs off: one ordinary scene, the active one", not session.exists() and scene_is(film)
         and cmds.objExists("hero") and not cmds.namespace(exists=":tab_film"), message)
    gate("tabs off: its layers are plain again", layers.root() == "BaseAnimation"
         and layer_parent("Layer1") == "BaseAnimation")


def phase_hook_failures():
    """A failing check callback refuses (False, nothing written); open_any restores once."""
    from maya_scenetabs import opening, saving
    rig, film, plain = copy("rig.ma"), copy("film.ma"), copy("plain.mb")
    fresh()
    cmds.file(rig, open=True, force=True)
    opening.open_tab(film)
    hooks = hooks_on()
    stamp = os.path.getmtime(film)
    real = session.state
    calls = []
    def boom():
        calls.append(1)
        raise RuntimeError("injected")
    session.state = boom
    try:
        result = hooks.on_save()
    finally:
        session.state = real
    flush()
    gate("hooks: a failing Save check refuses and writes nothing",
         result is False and calls and os.path.getmtime(film) == stamp and not QUEUE)
    recovered = RUN + "/open_any_session.ma"
    with hooks.bypass():
        cmds.file(rename=recovered)
        cmds.file(save=True, force=True, type="mayaAscii")
    fresh()
    cmds.file(recovered, open=True, force=True)
    opening.restore()
    hooks._st()["jobs"] = [0]                   # as in a GUI: a job exists to consume the flag
    count = []
    hooks._st()["defer"] = QUEUE.append
    real_restore = opening.restore
    def counted():
        count.append(1)
        return real_restore()
    opening.restore = counted
    opening.ASK = lambda message, buttons: "Don't Save"
    try:
        opening.open_any(recovered)
        hooks._scene_opened()                 # the SceneOpened job, after bypass is gone
        flush()
    finally:
        opening.restore = real_restore
        opening.ASK = None
    gate("hooks: open_any on a session file restores exactly once", len(count) == 1, count)
    count[:] = []
    hooks._st()["defer"] = QUEUE.append
    opening.restore = counted
    try:
        hooks._scene_opened()                   # a later, genuine open of a session file
        flush()
    finally:
        opening.restore = real_restore
    gate("hooks: a genuine SceneOpened still restores", len(count) == 1, count)
    # the synchronous ordering: the job fires inside open_any's bypass block
    count[:] = []
    real_open = cmds.file
    def file_then_job(*args, **kwargs):
        result = real_open(*args, **kwargs)
        if kwargs.get("open"):
            hooks._scene_opened()               # inside the bypass: synchronous with the open
        return result
    cmds.file = file_then_job
    opening.restore = counted
    opening.ASK = lambda message, buttons: "Don't Save"
    try:
        opening.open_any(recovered)
        flush()
    finally:
        cmds.file = real_open
        opening.restore = real_restore
        opening.ASK = None
    gate("hooks: a job firing inside the open restores once, leaving no flag",
         len(count) == 1 and not hooks._st().get("restored"), (count, hooks._st().get("restored")))
    count[:] = []
    opening.restore = counted
    try:
        hooks._scene_opened()
        flush()
    finally:
        opening.restore = real_restore
    gate("hooks: the next genuine SceneOpened restores after a synchronous one", len(count) == 1, count)


def _undo_is_empty():
    """Ctrl+Z has nothing to walk into (a tab made or closed is not a step)."""
    try:
        cmds.undo()
    except RuntimeError as exc:
        return "no more commands" in str(exc)
    return False


def _tabs_match_namespaces():
    names = [t["ns"] for t in session.state()["tabs"]]
    found = [n for n in cmds.namespaceInfo(":", listOnlyNamespaces=True) or [] if n.startswith(records.TAB_PREFIX)]
    return sorted(names) == sorted(found) if len(names) >= 2 else not found


def _plain_names():
    """The scene's names but the layer blend nodes and curves Maya rebuilds."""
    rebuilt = set(cmds.ls(type=("animCurve", "animBlendNodeBase")) or [])
    return sorted(n for n in cmds.ls() if n not in rebuilt)


def phase_review():
    """The final review's fixes (2026-10-15): a cancelled save keeps the tab and
    stops a quit; a failed open puts the tabs back; tabs made and closed are not
    undo steps; a conversion and a finish are all or nothing; the emergency
    save let through; the hooks re-installed after a reload."""
    import importlib
    from maya_scenetabs import hooks, layers, opening, saving, scope, switching
    plain, film = copy("plain.mb"), copy("film.ma")
    bad = RUN + "/corrupt.mb"
    with open(bad, "wb") as handle:
        handle.write(b"\x00not a maya binary\x00" * 64)

    # 1 - a cancelled save keeps the tab, stops close_others and the quit
    fresh()
    cmds.file(plain, open=True, force=True)
    opening.new_tab()
    cmds.createNode("transform", name="madeInUntitled")
    cmds.file(modified=True)
    saving.PICK = lambda: ""
    opening.ASK = lambda message, buttons: "Save"
    try:
        message = opening.close_tab("tab_untitled")
    finally:
        saving.PICK, opening.ASK = None, None
    gate("review 1: Close > Save with no path picked keeps the untitled tab",
         isinstance(message, session.Cancelled) and cmds.namespace(exists=":tab_untitled")
         and records.tab(session.state(), "tab_untitled") is not None
         and cmds.objExists("tab_untitled:madeInUntitled"), message)
    saving.PICK = lambda: ""
    opening.ASK = lambda message, buttons: "Save all"
    try:
        allowed = opening.quit_ok()
    finally:
        saving.PICK, opening.ASK = None, None
    state = session.state()
    gate("review 1: Quit > Save all with a cancelled pick does not quit, the flags kept",
         allowed is False and state["active"] == "tab_untitled"
         and opening._is_modified(state, records.tab(state, "tab_untitled")), (allowed, state["active"]))
    switching.switch("tab_plain")
    saving.PICK = lambda: ""
    opening.ASK = lambda message, buttons: "Save"
    try:
        message = opening.close_others("tab_plain")
    finally:
        saving.PICK, opening.ASK = None, None
    gate("review 1: close_others stops on the cancel (a flag, not a word)",
         isinstance(message, session.Cancelled) and cmds.namespace(exists=":tab_untitled"), message)
    opening.open_tab(film)
    cmds.setAttr("tab_film:hero.translateZ", 2)
    switching.switch("tab_plain")
    stamp = os.path.getmtime(film) + 20
    os.utime(film, (stamp, stamp))
    stamp = os.path.getmtime(film)
    saving.CONFIRM = lambda question: False
    opening.ASK = lambda message, buttons: "Save"
    try:
        message = opening.close_tab("tab_film")
    finally:
        saving.CONFIRM, opening.ASK = None, None
    gate("review 1: Close > Save > overwrite refused keeps the tab, the active tab as it was",
         isinstance(message, session.Cancelled) and cmds.namespace(exists=":tab_film")
         and session.state()["active"] == "tab_plain" and abs(os.path.getmtime(film) - stamp) < 1e-3, message)

    # 2 - a failed open puts the tabs back
    cmds.file(modified=True)
    tabs_before = [t["ns"] for t in session.state()["tabs"]]
    try:
        opening.open_tab(bad)
        raised = ""
    except Exception as exc:                                     # noqa: BLE001
        raised = str(exc) or type(exc).__name__
    state = session.state()
    gate("review 2: a corrupt file raises and the previous tab is active, shown, still modified",
         raised and state["active"] == "tab_plain" and all(tops_visible("tab_plain"))
         and not any(tops_visible("tab_film")) and cmds.file(q=True, modified=True)
         and current_ns() == "tab_plain", (raised, state["active"]))
    gate("review 2: no stray namespace, the tab list as before",
         not cmds.namespace(exists=":tab_corrupt") and [t["ns"] for t in state["tabs"]] == tabs_before,
         [t["ns"] for t in state["tabs"]])
    import maya_scenesetup.fbximport as fbximport
    real_import = fbximport.import_nodes

    def failing_fbx(path, *args, **kwargs):
        raise RuntimeError("injected FBX failure")
    fbximport.import_nodes = failing_fbx
    try:
        scope.open_scene(RUN + "/clip.fbx")
        raised = ""
    except RuntimeError as exc:
        raised = str(exc)
    finally:
        fbximport.import_nodes = real_import
    state = session.state()
    gate("review 2: a failed FBX open closes its new tab again, back on the previous one",
         "injected" in raised and [t["ns"] for t in state["tabs"]] == tabs_before
         and state["active"] == "tab_plain" and _tabs_match_namespaces(), [t["ns"] for t in state["tabs"]])

    # 3 - a tab made or closed is not a step Ctrl+Z walks into
    cmds.createNode("transform", name="stepBefore")
    opening.new_tab()
    gate("review 3: after New tab there is nothing to undo", _undo_is_empty() and _tabs_match_namespaces())
    cmds.createNode("transform", name="stepInTab")
    opening.close_tab(session.state()["active"], ask=False)
    gate("review 3: after Close there is nothing to undo", _undo_is_empty() and _tabs_match_namespaces())

    # 2b - a failed open from one scene goes back to that scene
    fresh()
    cmds.file(plain, open=True, force=True)
    cmds.file(modified=True)
    try:
        opening.open_tab(bad)
        raised = False
    except Exception:                                            # noqa: BLE001
        raised = True
    gate("review 2: from one scene, a failed open leaves the ordinary scene, still modified",
         raised and not session.exists() and scene_is(plain) and cmds.objExists("|ball")
         and cmds.file(q=True, modified=True)
         and not [n for n in cmds.namespaceInfo(":", listOnlyNamespaces=True) or [] if n.startswith("tab_")])

    # 4 - start and finish all or nothing
    for label, patch in (("give_children", "layers"), ("lower", "session")):
        fresh()
        cmds.file(film, open=True, force=True)
        cmds.lockNode("hero", lock=True)
        before = _plain_names()
        module = layers if patch == "layers" else session
        real = getattr(module, label)

        def failing(*args, **kwargs):
            if patch == "layers":
                real(*args, **kwargs)              # half done, then the failure
            raise RuntimeError("injected %s failure" % label)
        setattr(module, label, failing)
        try:
            opening.start()
            raised = ""
        except RuntimeError as exc:
            raised = str(exc)
        finally:
            setattr(module, label, real)
        gate("review 4: start failing in %s puts the scene back" % label,
             "injected" in raised and not session.exists() and _plain_names() == before
             and layers.root() == "BaseAnimation" and layer_parent("Layer1") == "BaseAnimation"
             and bool(cmds.lockNode("hero", q=True, lock=True)[0])
             and cmds.referenceQuery("refRN", namespace=True) == ":ref"
             and not cmds.namespace(exists=":tab_film") and current_ns() == "",
             (raised, sorted(set(_plain_names()) ^ set(before))[:8], layers.root()))
        gate("review 4: ... and its layer still plays (%s)" % label, value_at("hero.rotateY", 20) == 45.0)
    fresh()
    cmds.file(film, open=True, force=True)
    opening.open_tab(plain)
    cmds.createNode("transform", name=":hero")
    message = opening.close_tab("tab_plain", ask=False)
    gate("review 4: finish refused by a clash leaves the tab whole, its layers not flattened, and says so",
         "Not back to one scene" in message and session.exists() and len(session.state()["tabs"]) == 1
         and cmds.objExists("tab_film:hero") and layers.root() == records.LAYER_ROOT
         and layers.tab_root("tab_film") and value_at("tab_film:hero.rotateY", 20) == 45.0, message)
    cmds.delete("|hero")
    message = opening.finish()
    gate("review 4: with the clash gone, finish goes back to one scene",
         not session.exists() and layers.root() == "BaseAnimation" and layer_parent("Layer1") == "BaseAnimation"
         and value_at("hero.rotateY", 20) == 45.0 and scene_is(film), message)

    # 5 - Maya's emergency save let through
    opening.open_tab(plain)
    hooks_on()
    session_file = session.state()["session"]
    emergency = (tempfile.gettempdir().replace("\\", "/") + "/skeldar_emergency.ma")
    cmds.file(rename=emergency)
    let_temp = hooks.on_save()
    cmds.file(rename=RUN + "/film[Recovered-ME.2026-10-15-10.00].ma")
    let_recovered = hooks.on_save()
    cmds.file(rename=session_file)
    gate("review 5: an emergency save (temp folder, [Recovered) is let through, nothing deferred",
         let_temp is True and let_recovered is True and not QUEUE, (let_temp, let_recovered))

    # 8 - a reloaded hooks module re-installs its own callbacks
    #  Maya reuses a removed callback's id, so the proof is who owns them and
    #  that remove() ran (it clears the verify's defer seam)
    old_owner = hooks._st()["owner"]
    fresh_hooks = importlib.reload(hooks)
    fresh_hooks.install(force=True)
    state = fresh_hooks._st()
    gate("review 8: after a reload install replaces the old module's callbacks",
         len(state["callbacks"]) == 4 and old_owner is not None and state["owner"] is not old_owner
         and state["owner"] is fresh_hooks.on_save and state["defer"] is None, state["callbacks"])
    state["defer"] = QUEUE.append
    fresh_hooks.install(force=True)
    gate("review 8: a second install of the same module keeps what stands",
         state["defer"] is not None and state["owner"] is fresh_hooks.on_save)
    fresh_hooks.remove()


def guarded(phase):
    def run():
        try:
            phase()
        finally:
            try:
                from maya_scenetabs import hooks
                hooks.remove()
            except Exception:                                   # noqa: BLE001
                pass
    return run


def phase_untitled():
    """2026-10-15, found live: an untitled scene into tabs and back keeps the session file's name
    (Maya cannot untitle a scene). The next tab 1 is untitled again, and Save asks for a name."""
    from maya_scenetabs import opening
    fresh()
    cmds.polyCube(name="untitledCube")
    opening.ASK = lambda message, buttons: "Don't Save"
    opening.new_tab()
    first = session.state()["tabs"][0]
    gate("untitled: tab 1 of an untitled scene is untitled", first["path"] == "", first)
    opening.close_tab(session.state()["tabs"][1]["ns"], ask=False)
    left = (cmds.file(q=True, sceneName=True) or "").replace("\\", "/")
    gate("untitled: back to one scene, the scene still wears the session's name",
         records.is_session_file(left, opening.folder()) and not session.exists(), left)
    hooks = hooks_on()
    try:
        del QUEUE[:]
        answer = hooks.on_save()
        gate("untitled: Save with tabs off refuses and queues Save As", answer is False and len(QUEUE) == 1,
             (answer, len(QUEUE)))
        del QUEUE[:]
        opening.new_tab()
        again = session.state()["tabs"][0]
        gate("untitled: the next tab 1 is untitled, not the session file", again["path"] == ""
             and not again["ns"].startswith("tab_session"), again)
        gate("untitled: its cube came along", cmds.objExists(again["ns"] + ":untitledCube"))
    finally:
        hooks.remove()


def phase_duplicates():
    """2026-10-15, found live (AS_TechLimb_Shoot_1P_01): a file holding two DAG nodes of one short
    name (OverRig's fin_jnt11 in every rig) did not open as a tab - nodeType on a short name.
    Open, switch away and back, save, reopen, close."""
    from maya_scenetabs import opening, saving, switching
    os.makedirs(RUN, exist_ok=True)
    dup = RUN + "/duplicates.ma"
    fresh()
    for group in ("rigA", "rigB"):
        top = cmds.group(empty=True, name=group)
        cmds.select(top)
        cmds.joint(name="fin_jnt11")
        cmds.joint(name="fin_jnt12")
    _save(dup)
    fresh()
    cmds.polyCube(name="mainCube")
    opening.ASK = lambda message, buttons: "Don't Save"
    try:
        message = opening.open_tab(dup)
        error = ""
    except Exception as exc:                                    # noqa: BLE001
        message, error = "", str(exc)
    ns = "tab_duplicates"
    gate("duplicates: a file with two nodes of one name opens as a tab",
         not error and session.state()["active"] == ns, error or message)
    gate("duplicates: both fin_jnt11 are in the tab",
         len(cmds.ls(ns + ":fin_jnt11", long=True) or []) == 2, cmds.ls(ns + ":fin_jnt11", long=True))
    first = session.state()["tabs"][0]["ns"]
    switching.switch(first)
    switching.switch(ns)
    gate("duplicates: switched away and back", session.state()["active"] == ns
         and cmds.getAttr("|%s:rigA.lodVisibility" % ns) == 1)
    cmds.setAttr("|%s:rigA.translateX" % ns, 7)
    try:
        saving.save_tab(ns)
        saved = ""
    except Exception as exc:                                    # noqa: BLE001
        saved = str(exc)
    text = open(dup).read()
    gate("duplicates: saved into its plain file with both joints, no tab prefix",
         not saved and text.count('"fin_jnt11"') == 2 and "tab_" not in text, saved)
    gate("duplicates: the tab's names are back after the save",
         len(cmds.ls(ns + ":fin_jnt11", long=True) or []) == 2)
    gate("duplicates: closed", "Closed" in opening.close_tab(ns, ask=False) or not session.exists())


def phase_outliner_sets():
    """2026-10-16, found live: the Outliner showed a hidden tab's selection sets. A hidden tab's
    sets are hiddenInOutliner (marked as ours); shown again, all back - but a set the animator
    hid themselves stays hidden; a hidden tab's save writes neither the flag nor the mark."""
    from maya_scenetabs import opening, saving, switching
    os.makedirs(RUN, exist_ok=True)
    made = {}
    for tag in ("A", "B"):
        fresh()
        cube = cmds.polyCube(name="cube" + tag)[0]
        cmds.sets(cube, name="sel" + tag)
        if tag == "A":
            own = cmds.sets(cube, name="ownHidden")
            cmds.setAttr(own + ".hiddenInOutliner", 1)
        made[tag] = RUN + "/sets%s.ma" % tag
        _save(made[tag])
    fresh()
    cmds.file(made["A"], open=True, force=True)
    opening.ASK = lambda message, buttons: "Don't Save"
    opening.open_tab(made["B"])
    a, b = "tab_setsA", "tab_setsB"

    def hidden(node):
        return cmds.getAttr(node + ".hiddenInOutliner")

    gate("outliner sets: the hidden tab's set hidden", hidden(a + ":selA") and not hidden(b + ":selB"),
         (hidden(a + ":selA"), hidden(b + ":selB")))
    switching.switch(a)
    gate("outliner sets: switched - A's set back, B's hidden",
         not hidden(a + ":selA") and hidden(b + ":selB"))
    gate("outliner sets: the animator's own hidden set stays hidden", hidden(a + ":ownHidden"))
    gate("outliner sets: no mark left on a shown tab",
         not cmds.attributeQuery(switching.SET_MARK, node=a + ":selA", exists=True))
    cmds.undo()
    gate("outliner sets: Ctrl+Z after the switch stays in A (a switch is no undo step since 2026-10-19)",
         session.state()["active"] == a and not hidden(a + ":selA") and hidden(b + ":selB"))
    switching.switch(b)
    cmds.setAttr(b + ":cubeB.translateZ", 1)
    saving.save_tab(b)
    switching.switch(a)
    text = open(made["B"]).read()
    gate("outliner sets: a hidden tab saved carries no mark and no hidden flag on its set",
         switching.SET_MARK not in text and hidden(b + ":selB"), text.count(switching.SET_MARK))
    opening.close_tab(b, ask=False)
    gate("outliner sets: back to one scene, its set shown",
         cmds.objExists("selA") and not hidden("selA") and hidden("ownHidden"))


def phase_nested():
    """2026-10-16, found live: a rig's own display layer (`Manny_Rig:UE5_Skeleton`, in a namespace
    NESTED in the tab) showed in every tab - `ls(":tab:*", recursive=True)` does not reach a nested
    namespace. A hidden tab's nested layers, sets and anim layers are hidden like its own."""
    from maya_scenetabs import opening, switching
    os.makedirs(RUN, exist_ok=True)
    made = {}
    for tag in ("A", "B"):
        fresh()
        cmds.namespace(add=":Rig" + tag)
        cube = cmds.polyCube(name=":Rig%s:cube" % tag)[0]
        cmds.createDisplayLayer([cube], name=":Rig%s:deep" % tag, noRecurse=True)
        cmds.sets(cube, name=":Rig%s:ControlSet" % tag)
        made[tag] = RUN + "/nested%s.ma" % tag
        _save(made[tag])
    fresh()
    cmds.file(made["A"], open=True, force=True)
    opening.ASK = lambda message, buttons: "Don't Save"
    opening.open_tab(made["B"])
    a, b = "tab_nestedA:RigA", "tab_nestedB:RigB"

    def shown_layer(name):
        return cmds.getAttr(name + ".identification") != 0

    def hidden_set(name):
        return cmds.getAttr(name + ".hiddenInOutliner")

    gate("nested: the hidden tab's nested layer out of the Display list, the active one's in",
         not shown_layer(a + ":deep") and shown_layer(b + ":deep"))
    gate("nested: the hidden tab's nested set out of the Outliner, the active one's in",
         hidden_set(a + ":ControlSet") and not hidden_set(b + ":ControlSet"))
    switching.switch("tab_nestedA")
    gate("nested: switched - the other way round",
         shown_layer(a + ":deep") and not shown_layer(b + ":deep")
         and not hidden_set(a + ":ControlSet") and hidden_set(b + ":ControlSet"))
    gate("nested: the layer still holds its cube",
         cmds.editDisplayLayerMembers(a + ":deep", q=True) and cmds.listConnections(a + ":deep.drawInfo"))
    opening.close_tab("tab_nestedB", ask=False)
    gate("nested: back to one scene, the layer and the set shown",
         shown_layer("RigA:deep") and not hidden_set("RigA:ControlSet"))


def phase_layer_editor():
    """2026-10-15, found live: the Layer Editor showed every tab's layers. A hidden tab's anim
    layers are cut off the session root and its display layers taken off layerManager
    (identification 0, which the editor skips as Maya's default); shown again, all back.
    The editor's own listing was proven in a GUI Maya; here the data it is built from."""
    from maya_scenetabs import layers, opening, saving, switching
    os.makedirs(RUN, exist_ok=True)
    made = {}
    for tag in ("A", "B"):
        fresh()
        cube = cmds.polyCube(name="cube" + tag)[0]
        cmds.setKeyframe(cube, attribute="translateX", time=0, value=0)
        cmds.setKeyframe(cube, attribute="translateX", time=10, value=5)
        cmds.createDisplayLayer([cube], name="display" + tag, noRecurse=True)
        cmds.select(cube)
        cmds.animLayer("anim" + tag, addSelectedObjects=True)
        cmds.setKeyframe(cube, attribute="translateY", time=0, value=0, animLayer="anim" + tag)
        cmds.setKeyframe(cube, attribute="translateY", time=10, value=3, animLayer="anim" + tag)
        made[tag] = RUN + "/layers%s.ma" % tag
        _save(made[tag])
    fresh()
    cmds.file(made["A"], open=True, force=True)
    opening.ASK = lambda message, buttons: "Don't Save"
    opening.open_tab(made["B"])
    a, b = "tab_layersA", "tab_layersB"
    root = layers.root()

    def on_root(ns):
        return [l for l in cmds.ls(":%s:*" % ns, type="animLayer") or []
                if (cmds.animLayer(l, q=True, parent=True) or "") == root]

    def shown_id(ns, tag):
        layer = "%s:display%s" % (ns, tag)
        return cmds.getAttr(layer + ".identification"), bool(
            cmds.listConnections(layer + ".identification", source=True, destination=False))

    def track(ns, tag):
        return [round(cmds.getAttr("%s:cube%s.%s" % (ns, tag, attr), time=f), 4)
                for attr in ("translateX", "translateY") for f in (0, 5, 10)]

    expected = [0.0, 2.5, 5.0, 0.0, 1.5, 3.0]
    gate("layer editor: the hidden tab's anim layers are off the session root", on_root(a) == [],
         on_root(a))
    gate("layer editor: the active tab's are on it", on_root(b) == [b + ":AnimLayerRoot"], on_root(b))
    gate("layer editor: the hidden tab's display layer off layerManager, id 0", shown_id(a, "A") == (0, False),
         shown_id(a, "A"))
    gate("layer editor: the active tab's display layer on it", shown_id(b, "B")[1] and shown_id(b, "B")[0] > 0,
         shown_id(b, "B"))
    gate("layer editor: both tabs' animation as keyed, layers included",
         track(a, "A") == expected and track(b, "B") == expected, (track(a, "A"), track(b, "B")))
    switching.switch(a)
    gate("layer editor: switched - A's layers back, B's out",
         on_root(a) == [a + ":AnimLayerRoot"] and on_root(b) == [] and shown_id(a, "A")[1]
         and shown_id(b, "B") == (0, False), (on_root(a), on_root(b), shown_id(a, "A"), shown_id(b, "B")))
    gate("layer editor: animation unchanged after the switch",
         track(a, "A") == expected and track(b, "B") == expected, (track(a, "A"), track(b, "B")))
    cmds.undo()
    gate("layer editor: Ctrl+Z after the switch leaves A's layers on and B's out (no undo of a switch)",
         session.state()["active"] == a and on_root(a) == [a + ":AnimLayerRoot"] and on_root(b) == []
         and shown_id(a, "A")[1] and shown_id(b, "B") == (0, False))
    switching.switch(b)
    gate("layer editor: switched back - B's layers back, A's out",
         session.state()["active"] == b and on_root(b) == [b + ":AnimLayerRoot"] and on_root(a) == []
         and shown_id(b, "B")[1] and shown_id(a, "A") == (0, False))
    switching.switch(a)
    cmds.setAttr(b + ":cubeB.translateZ", 1)
    saving.save_tab(b)
    text = open(made["B"]).read()
    gate("layer editor: a hidden tab saved - its file carries no marker and a real display layer id",
         layers.OUT_ATTR not in text and 'connectAttr "layerManager.dli[' in text
         and '"displayB.id"' in text, text.count(layers.OUT_ATTR))
    switching.switch(a)             # a save of another tab switches to it (stage 1's rule)
    gate("layer editor: back on A, the saved tab's layers are out again",
         on_root(b) == [] and shown_id(b, "B") == (0, False) and on_root(a) == [a + ":AnimLayerRoot"])
    opening.close_tab(b, ask=False)
    plain_ok = (not session.exists() and cmds.objExists("displayA") and cmds.objExists("animA")
                and cmds.getAttr("displayA.identification") > 0
                and (cmds.animLayer("animA", q=True, parent=True) or "") == layers.root()
                and not cmds.attributeQuery(layers.OUT_ATTR, node="displayA", exists=True))
    gate("layer editor: back to one scene, its layers on the root and its display layer in", plain_ok,
         (session.exists(), cmds.ls(type="displayLayer"), cmds.ls(type="animLayer")))


def phase_pasted():
    """2026-10-16, found live: Copy / Paste from one tab into another nests the source tab's
    namespace in the target (`tab_B:tab_A:mat`), and every save of the target then refused -
    «cannot save tab_B: the scene already holds a namespace tab_A». A pasted tab namespace is
    folded into the tab on save (its nodes are the target's: `mat` -> `mat1` beside its own),
    and the save goes through."""
    from maya_scenetabs import opening, saving
    os.makedirs(RUN, exist_ok=True)
    made = {}
    for tag in ("A", "B"):
        fresh()
        cmds.namespace(add=":Bow")
        cube = cmds.polyCube(name="cube" + tag)[0]
        cmds.shadingNode("lambert", asShader=True, name="mat")
        cmds.createDisplayLayer([cube], name=":Bow:Arrow", noRecurse=True)
        made[tag] = RUN + "/pasted%s.ma" % tag
        _save(made[tag])
    fresh()
    cmds.file(made["A"], open=True, force=True)
    opening.ASK = lambda message, buttons: "Don't Save"
    opening.open_tab(made["B"])
    a, b = "tab_pastedA", "tab_pastedB"
    # what Maya's paste of A's material and layer makes in B (B's namespace current)
    cmds.namespace(add=":%s:%s:Bow" % (b, a))
    cmds.shadingNode("lambert", asShader=True, name=":%s:%s:mat" % (b, a))
    cmds.shadingNode("lambert", asShader=True, name=":%s:%s:only" % (b, a))
    cmds.createDisplayLayer(empty=True, name=":%s:%s:Bow:Arrow" % (b, a), noRecurse=True)
    cmds.lockNode(":%s:%s:only" % (b, a), lock=True)
    before_a = sorted(cmds.namespaceInfo(":" + a, listOnlyDependencyNodes=True, recurse=True) or [])
    cmds.setAttr(b + ":cubeB.translateZ", 1)
    try:
        message = saving.save_tab(b)
        error = ""
    except Exception as exc:                                    # noqa: BLE001
        message, error = "", str(exc)
    gate("pasted: a tab holding another tab's namespace saves", message.startswith("Saved"), message or error)
    gate("pasted: the line says what was folded", "tab_pastedA" in message and "pasted" in message, message)
    gate("pasted: the pasted namespace is gone from the tab",
         not cmds.namespace(exists=":%s:%s" % (b, a)), cmds.namespaceInfo(":" + b, listOnlyNamespaces=True))
    gate("pasted: its nodes are the tab's own, clashes renamed",
         all(cmds.objExists(":%s:%s" % (b, n)) for n in ("mat", "mat1", "only", "Bow:Arrow", "Bow1:Arrow"))
         and cmds.lockNode(":%s:only" % b, q=True, lock=True)[0])
    gate("pasted: the other tab untouched",
         sorted(cmds.namespaceInfo(":" + a, listOnlyDependencyNodes=True, recurse=True) or []) == before_a)
    text = open(made["B"]).read()
    gate("pasted: the file holds them under plain names, no tab namespace",
         '-n "mat1"' in text and '-n "only"' in text and "tab_" not in text,
         [l for l in text.splitlines() if "tab_" in l][:3])
    gate("pasted: the tab is clean after the save",
         not records.tab(session.state(), b)["modified"] and not cmds.file(q=True, modified=True))
    fresh()
    cmds.file(made["B"], open=True, force=True)
    gate("pasted: the saved file opens with its own and the pasted nodes",
         all(cmds.objExists(n) for n in ("mat", "mat1", "only", "Bow:Arrow", "Bow1:Arrow", "cubeB")))


def _leak_tree(namespace):
    """The tab's layers on the session root other than its own root, the root copies anywhere,
    the layers still carrying stored links."""
    from maya_scenetabs import layers
    session_root = layers.root()
    found = session.typed(namespace, "animLayer")
    made = layers.tab_root(namespace)
    loose = [l for l in found if l != made and (cmds.animLayer(l, q=True, parent=True) or "") == session_root]
    copies = [l for l in cmds.ls(type="animLayer") or []
              if l.split(":")[-1].startswith(records.LAYER_ROOT) and l != session_root]
    stored = [l for l in found + session.typed(namespace, "displayLayer")
              if cmds.attributeQuery(layers.OUT_ATTR, node=l, exists=True)]
    return loose, copies, stored


def phase_leak():
    """2026-10-16, found live: AS_DG_ATK_JA_04.ma did not open as a tab («No object matches
    name: tab_...:AnimLayerRoot.solo»). An old save had written another whole tab into it,
    hidden, with the session's layer root: `exportSelected` writes a node's upstream, and the
    tab was tied to the other one (a material fed by its stack) and to the session root (a layer
    hung on it). A save now cuts every input from another tab or the session for the export;
    a file an old save wrote opens, its leaked tab removed when the animator says so."""
    from maya_scenetabs import layers, opening, saving, switching
    made = {}
    for tag in ("A", "B", "C"):
        fresh()
        cube = cmds.polyCube(name="cube" + tag)[0]
        cmds.setKeyframe(cube, attribute="tx", time=0, value=0)
        cmds.setKeyframe(cube, attribute="tx", time=10, value=5)
        cmds.select(cube)
        cmds.animLayer("L" + tag, addSelectedObjects=True)
        cmds.setKeyframe(cube, attribute="ty", time=0, value=1, animLayer="L" + tag)
        made[tag] = RUN + "/leak%s.ma" % tag
        _save(made[tag])
    answers = {"leak": "Remove"}
    asked = []

    def ask(message, buttons):
        if "Remove" in buttons:
            asked.append(message)
            return answers["leak"]
        return "Don't Save" if "Don't Save" in buttons else buttons[-1]
    opening.ASK = ask
    fresh()
    cmds.file(made["A"], open=True, force=True)
    opening.open_tab(made["B"])
    opening.open_tab(made["C"])
    a, b, c = "tab_leakA", "tab_leakB", "tab_leakC"
    switching.switch(b)
    # B tied to the others the ways an old save leaked them
    cmds.select(b + ":cubeB")
    stray = cmds.animLayer("Stray", addSelectedObjects=True)
    gate("leak: a layer Maya makes hangs on the session root (the fixture)",
         cmds.animLayer(stray, q=True, parent=True) == layers.root(), stray)
    cmds.addAttr(b + ":cubeB", longName="fromA")
    cmds.addAttr(b + ":cubeB", longName="fromC")
    cmds.namespace(setNamespace=":")
    mid = cmds.createNode("multDoubleLinear", name="leakMid")
    cmds.namespace(setNamespace=":" + b)
    ties = [(a + ":cubeA.translateY", mid + ".input1"), (mid + ".output", b + ":cubeB.fromA"),
            (c + ":cubeC.translateZ", b + ":cubeB.fromC")]
    for source, destination in ties:
        cmds.connectAttr(source, destination)
    target = RUN + "/leakSaved.ma"
    message = saving.save_tab(b, path=target, adopt=False)
    text = open(target).read()
    gate("leak: B saves", message.startswith("Saved"), message)
    others = ["cubeA", "cubeC", "tab_leakA", "tab_leakC", records.LAYER_ROOT, records.SESSION_NODE,
              layers.OUT_ATTR]
    gate("leak: the file holds nothing of the other tabs or of the session",
         not [w for w in others if w in text], [w for w in others if w in text])
    gate("leak: the node between them is B's upstream and goes in, cut from A", '"leakMid"' in text)
    gate("leak: the stray layer went under B's root, in the file under BaseAnimation",
         cmds.animLayer(stray, q=True, parent=True) == layers.tab_root(b)
         and '"Stray.play" "BaseAnimation.cdly' in text.replace("connectAttr ", ""), stray)
    gate("leak: every connection to the other tabs is back after the save",
         all(cmds.isConnected(s, d) for s, d in ties))
    gate("leak: the other tabs are still hidden, their layers off the Layer Editor",
         all(cmds.attributeQuery(layers.OUT_ATTR, node=ns + ":AnimLayerRoot", exists=True)
             and not cmds.animLayer(ns + ":AnimLayerRoot", q=True, parent=True) for ns in (a, c)))
    # the control: the old save (no walk, no strays moved) writes A and C in, hidden
    stray2 = cmds.animLayer("Stray2", addSelectedObjects=True)
    real = saving.foreign_inputs, layers.adopt_strays
    saving.foreign_inputs, layers.adopt_strays = (lambda *args: []), (lambda namespace: [])
    leaky = RUN + "/leakOld.ma"
    try:
        saving.save_tab(b, path=leaky, adopt=False)
    finally:
        saving.foreign_inputs, layers.adopt_strays = real
    text = open(leaky).read()
    gate("leak: the old save writes the other tabs and the session root in (the control)",
         "tab_leakA:cubeA" in text and "tab_leakC:cubeC" in text and records.LAYER_ROOT in text
         and layers.OUT_ATTR in text,
         stray2)
    # a file the old save wrote, opened as a tab: Remove
    fresh()
    cmds.file(made["A"], open=True, force=True)
    del asked[:]
    try:
        message, error = opening.open_tab(leaky), ""
    except Exception as exc:                                    # noqa: BLE001
        message, error = "", str(exc)
    new = session.state()["active"]
    gate("leak: the file opens in a tab", message.startswith("Opened") and new == "tab_leakOld", message or error)
    gate("leak: Remove leaves the tab flagged, the line says to save it (the file stays leaky until then)",
         cmds.file(q=True, modified=True) and "save this tab" in message, message)
    gate("leak: the animator is asked, the line says what went",
         asked and "tab_leakA" in asked[0] and "tab_leakC" in asked[0] and "removed another tab" in message,
         message)
    gate("leak: the other tabs are gone from it",
         not [n for n in session.child_namespaces(new) if n.startswith(records.TAB_PREFIX)]
         and not cmds.objExists(":%s:tab_leakA:cubeA" % new), session.child_namespaces(new))
    loose, copies, stored = _leak_tree(new)
    gate("leak: no root copy, no loose layer, no stored link left", not (loose or copies or stored),
         (loose, copies, stored))
    gate("leak: its own layers under its root",
         all(cmds.animLayer(":%s:%s" % (new, l), q=True, parent=True) == layers.tab_root(new)
             for l in ("LB", "Stray", "Stray2")))
    try:
        switching.switch("tab_leakA")
        switching.switch(new)
        error = ""
    except Exception as exc:                                    # noqa: BLE001
        error = str(exc)
    gate("leak: away and back", not error and session.state()["active"] == new, error)
    # Keep
    answers["leak"] = "Keep"
    message = opening.open_tab(leaky)
    kept = session.state()["active"]
    loose, copies, stored = _leak_tree(kept)
    gate("leak: Keep opens it with the other tabs inside, said",
         "(kept)" in message and cmds.objExists(":%s:tab_leakA:cubeA" % kept), message)
    gate("leak: Keep opens it unflagged (nothing changed)", not cmds.file(q=True, modified=True))
    gate("leak: kept, their layers hang under the tab's root, nothing stored, no root copy",
         not (loose or copies or stored)
         and cmds.animLayer(":%s:tab_leakA:AnimLayerRoot" % kept, q=True, parent=True) == layers.tab_root(kept),
         (loose, copies, stored))
    try:
        switching.switch("tab_leakA")
        switching.switch(kept)
        error = ""
    except Exception as exc:                                    # noqa: BLE001
        error = str(exc)
    gate("leak: kept, away and back", not error, error)
    # opened plainly, then tabs on: the conversion
    answers["leak"] = "Remove"
    fresh()
    cmds.file(leaky, open=True, force=True)
    gate("leak: the file opens plainly (the control: its copy of the session root is there)",
         cmds.objExists(":" + records.LAYER_ROOT) and cmds.objExists("cubeB"))
    message = opening.new_tab()
    first = session.state()["tabs"][0]["ns"]
    try:
        switching.switch(first)
        error = ""
    except Exception as exc:                                    # noqa: BLE001
        error = str(exc)
    gate("leak: tabs on, the new tab made, tab 1 shown again", not error and "removed another tab" in message,
         error or message)
    gate("leak: tab 1, cleaned, is flagged", cmds.file(q=True, modified=True)
         and records.tab(session.state(), first)["modified"])
    loose, copies, stored = _leak_tree(first)
    gate("leak: tab 1: the real root takes its name, the copy dissolved, the leak removed",
         layers.root() == records.LAYER_ROOT and not (loose or copies or stored)
         and not [n for n in session.child_namespaces(first) if n.startswith(records.TAB_PREFIX)]
         and all(cmds.animLayer(":%s:%s" % (first, l), q=True, parent=True) == layers.tab_root(first)
                 for l in ("LB", "Stray", "Stray2")),
         (layers.root(), loose, copies, stored))
    opening.ASK = None


def phase_stash_open():
    """2026-10-16, live: with one scene open, Stash's Open replaced it - only after «+ empty
    tab» did the next open go into a tab. The plugin's opens (Stash, Shared, Open scene) now
    take the first scene into an empty one and every later one into a tab beside it."""
    from maya_scenesetup import opener
    from maya_scenetabs import scope
    os.makedirs(RUN, exist_ok=True)
    files = {}
    for tag in ("A", "B", "C"):
        fresh()
        cmds.polyCube(name="stash" + tag)
        files[tag] = RUN + "/stash%s.ma" % tag
        _save(files[tag])
    cmds.loadPlugin("fbxmaya", quiet=True)
    fresh()
    cmds.polyCube(name="stashFbx")
    fbx = RUN + "/stashFbx.fbx"
    cmds.select("stashFbx")
    cmds.file(fbx, force=True, exportSelected=True, type="FBX export")

    def tabs():
        return [t["ns"] for t in session.state()["tabs"]]
    fresh()
    gate("stash: a fresh scene is empty", scope.scene_empty())
    opened, _note = opener.open_path(files["A"])
    gate("stash: the first scene opens into it, plainly", opened and not session.exists()
         and cmds.file(q=True, sceneName=True) == files["A"] and cmds.objExists("stashA"))
    gate("stash: a scene from a file is not empty", not scope.scene_empty())
    cmds.setAttr("stashA.tx", 3)
    opened, _note = opener.open_path(files["B"])
    gate("stash: the second opens in a tab beside it, the first is tab 1",
         opened and tabs() == ["tab_stashA", "tab_stashB"] and session.state()["active"] == "tab_stashB"
         and cmds.objExists("tab_stashA:stashA") and cmds.objExists("tab_stashB:stashB"), tabs())
    gate("stash: tab 1 kept its unsaved change, flagged",
         cmds.getAttr("tab_stashA:stashA.tx") == 3 and records.tab(session.state(), "tab_stashA")["modified"])
    opened, _note = opener.open_path(files["C"])
    gate("stash: the third, a third tab", tabs() == ["tab_stashA", "tab_stashB", "tab_stashC"], tabs())
    # untitled work goes into tab 1
    fresh()
    cmds.polyCube(name="draftCube")
    gate("stash: an untitled scene with work in it is not empty", not scope.scene_empty())
    opener.open_path(files["A"])
    first = session.state()["tabs"][0] if session.exists() else {}
    gate("stash: the untitled work is tab 1, the file tab 2",
         tabs() == [first.get("ns"), "tab_stashA"] and not first.get("path")
         and cmds.objExists(":%s:draftCube" % first.get("ns")), tabs())
    # untitled, flagged, nothing in it: the file takes its place
    fresh()
    cube = cmds.polyCube(name="gone")[0]
    cmds.delete(cube)
    gate("stash: an untitled scene flagged with nothing in it is empty",
         cmds.file(q=True, modified=True) and scope.scene_empty())
    opener.open_path(files["B"])
    gate("stash: ... and the file opens into it", not session.exists() and cmds.objExists("stashB"))
    # an FBX beside a scene: an empty tab, the FBX imported into it
    message = scope.open_scene(fbx)
    gate("stash: an FBX beside a scene opens in a tab of its own",
         len(tabs()) == 2 and cmds.objExists(":%s:stashFbx" % session.state()["active"])
         and cmds.objExists(":tab_stashB:stashB"), (tabs(), message))
    # a new scene beside one
    message = scope.new_scene()
    gate("stash: a new scene beside one is an empty tab", len(tabs()) == 3, (tabs(), message))


def phase_maya_open():
    """2026-10-16: Maya's own File > Open (and Open Recent) of a .ma / .mb goes into a tab while
    the open scene is not empty - with tabs off too - and its «save changes?» is not asked then:
    nothing is replaced. An empty scene, the same file again, a saved session, an FBX and New
    stay Maya's."""
    import maya.mel as mel
    from maya_scenetabs import opening, savechanges, scope
    os.makedirs(RUN, exist_ok=True)
    files = {}
    for tag in ("A", "B"):
        fresh()
        cmds.polyCube(name="open" + tag)
        files[tag] = RUN + "/mopen%s.ma" % tag
        _save(files[tag])
    cmds.loadPlugin("fbxmaya", quiet=True)
    fresh()
    cmds.polyCube(name="openFbx")
    fbx = RUN + "/mopenFbx.fbx"
    cmds.select("openFbx")
    cmds.file(fbx, force=True, exportSelected=True, type="FBX export")

    def tabs():
        return [t["ns"] for t in session.state()["tabs"]]

    def maya_open(path):
        """Maya's open as pv_performAction runs it: saveChanges, then the action."""
        action = 'file -f -typ "mayaAscii" -o "%s";addRecentFile("%s", "mayaAscii")' % (path, path)
        try:
            mel.eval("saveChanges(\"%s\")" % action.replace("\\", "\\\\").replace('"', '\\"'))
            return ""
        except RuntimeError as exc:
            return str(exc)

    fresh()
    hooks = hooks_on()
    gate("open: our saveChanges sourced over Maya's", savechanges.install(force=True)
         and "skeldarSaveChanges.mel" in (mel.eval('whatIs "%s"' % savechanges.MAYA) or ""))
    error = maya_open(files["A"])
    flush()
    gate("open: into an empty scene Maya's own open", not error and not session.exists()
         and scope.same_file(cmds.file(q=True, sceneName=True), files["A"]), error)
    cmds.setAttr("openA.tx", 4)
    gate("open: the scene modified, an open of another file skips the question",
         cmds.file(q=True, modified=True) and savechanges.skip_question(
             'file -f -o "%s"' % files["B"]))
    maya_open(files["B"])
    flush()
    gate("open: tabs off, Maya's open of B goes into a tab beside A",
         tabs() == ["tab_mopenA", "tab_mopenB"] and session.state()["active"] == "tab_mopenB"
         and cmds.objExists("tab_mopenB:openB"), tabs())
    gate("open: A kept its unsaved change, flagged", cmds.getAttr("tab_mopenA:openA.tx") == 4
         and records.tab(session.state(), "tab_mopenA")["modified"])
    # a saved session opened with tabs off brings its tabs back as before
    sess = RUN + "/mopenSession.ma"
    with hooks.bypass():
        keep = cmds.file(q=True, sceneName=True)
        cmds.file(rename=sess)
        cmds.file(save=True, type="mayaAscii", force=True)
        cmds.file(rename=keep)
    # the same file again, tabs off: Maya reopens it
    fresh()
    hooks = hooks_on()
    savechanges.install(force=True)
    cmds.file(files["A"], open=True, force=True)
    cmds.setAttr("openA.tx", 6)
    gate("open: the same file again asks as Maya does", not savechanges.skip_question(
        'file -f -o "%s"' % files["A"]))
    try:
        cmds.file(files["A"], open=True, force=True)
        error = ""
    except RuntimeError as exc:
        error = str(exc)
    flush()
    gate("open: ... and reopens it in place", not error and not session.exists()
         and cmds.getAttr("openA.tx") == 0, error)
    gate("open: a saved session asks as Maya does", not savechanges.skip_question(
        'file -f -o "%s"' % sess))
    try:
        cmds.file(sess, open=True, force=True)
        error = ""
    except RuntimeError as exc:
        error = str(exc)
    flush()
    gate("open: ... and opens as Maya does", not error and scope.same_file(
        cmds.file(q=True, sceneName=True), sess), error)
    # an FBX and New beside a scene: Maya's own
    fresh()
    hooks = hooks_on()
    savechanges.install(force=True)
    cmds.file(files["A"], open=True, force=True)
    try:
        cmds.file(fbx, open=True, force=True, type="FBX")
        error = ""
    except RuntimeError as exc:
        error = str(exc)
    flush()
    gate("open: an FBX through Maya's Open replaces the scene as before",
         not error and not session.exists() and cmds.objExists("openFbx"), error)
    cmds.file(files["A"], open=True, force=True)
    gate("open: New asks as Maya does", not savechanges.skip_question("file -f -new"))
    try:
        cmds.file(new=True, force=True)
        error = ""
    except RuntimeError as exc:
        error = str(exc)
    gate("open: New with tabs off is Maya's", not error and not session.exists()
         and not cmds.objExists("openA"), error)
    # the checks off: our saveChanges is Maya's again
    cmds.file(files["A"], open=True, force=True)
    hooks.remove()
    gate("open: with the checks off nothing skips the question",
         not savechanges.skip_question('file -f -o "%s"' % files["B"]))
    try:
        cmds.file(files["B"], open=True, force=True)
        error = ""
    except RuntimeError as exc:
        error = str(exc)
    gate("open: ... and Maya's open replaces the scene", not error and not session.exists()
         and cmds.objExists("openB"), error)


def phase_camera_keys():
    """2026-10-16, the animator: «если я накину анимации на камеру которая в сцене по умолчанию то
    она будет во всех сценах». A key on persp / top / front / side made in a tab is that tab's: its
    curve is connected while the tab is active and disconnected while it is hidden."""
    from maya_scenetabs import hooks, opening, saving, switching
    os.makedirs(RUN, exist_ok=True)

    def keyed(name, keys, focal=None):
        fresh()
        cmds.polyCube(name="cube" + name)
        for frame, value in keys:
            cmds.setKeyframe("persp", attribute="translateX", time=frame, value=value)
        if focal:
            for frame, value in focal:
                cmds.setKeyframe("perspShape", attribute="focalLength", time=frame, value=value)
        path = RUN + "/camk%s.ma" % name
        _save(path)
        return path

    def tx(frame):
        cmds.currentTime(frame + 1)
        cmds.currentTime(frame)
        return round(cmds.getAttr("persp.translateX"), 4)

    def source(plug):
        found = cmds.listConnections(":" + plug, source=True, destination=False) or []
        return found[0] if found else ""

    a = keyed("A", [(0, 10), (10, 50)])
    b = keyed("B", [(0, -20), (10, -60)], focal=[(0, 20), (10, 80)])
    c = keyed("C", [])
    fresh()
    cmds.file(a, open=True, force=True)
    gate("cameras: a file's own keys on persp, before tabs", tx(10) == 50 and source("persp.translateX"))
    opening.open_tab(b)
    gate("cameras: B's keys drive persp in B", tx(10) == -60 and source("persp.translateX").startswith("tab_camkB:")
         and round(cmds.getAttr("perspShape.focalLength"), 3) == 80.0, (tx(10), source("persp.translateX")))
    gate("cameras: A's curve went into A's tab and waits off the camera",
         cmds.objExists("tab_camkA:persp_translateX")
         and not cmds.listConnections("tab_camkA:persp_translateX.output"))
    switching.switch("tab_camkA")
    gate("cameras: back in A, A's keys again", tx(10) == 50 and tx(0) == 10
         and source("persp.translateX").startswith("tab_camkA:"), (tx(10), source("persp.translateX")))
    gate("cameras: B's focal length keys are off the camera in A, A's own focal length back",
         not source("perspShape.focalLength") and round(cmds.getAttr("perspShape.focalLength"), 3) == 35.0,
         cmds.getAttr("perspShape.focalLength"))
    opening.open_tab(c)
    gate("cameras: a file with no keys - persp free, on the file's place",
         not source("persp.translateX") and tx(10) == 28.0, tx(10))
    cmds.setKeyframe("persp", attribute="translateY", time=0, value=5)
    cmds.setKeyframe("persp", attribute="translateY", time=10, value=9)
    gate("cameras: a key made in C is C's curve", source("persp.translateY").startswith("tab_camkC:"),
         source("persp.translateY"))
    switching.switch("tab_camkB")
    cmds.undo()             # stops at B's fence: no switch back to C (2026-10-19)
    gate("cameras: Ctrl+Z after the switch stays in B, C's key kept off the camera",
         session.state()["active"] == "tab_camkB" and not source("persp.translateY"),
         (session.state()["active"], source("persp.translateY")))
    gate("cameras: in B, C's key is off and B's on",
         not source("persp.translateY") and tx(10) == -60 and round(cmds.getAttr("perspShape.focalLength"), 3) == 80.0)
    target = RUN + "/camkB_saved.ma"
    saving.save_tab(path=target, adopt=False)
    text = open(target).read()
    gate("cameras: B saved holds B's keys on persp, nothing of A's or C's",
         'connectAttr "persp_translateX.o" ":persp.tx"' in text
         and 'connectAttr "perspShape_focalLength.o" ":perspShape.fl"' in text
         and "persp_translateY" not in text and "camkA" not in text and "camkC" not in text)
    # a hidden tab read again from its file keeps its own keys; the active one's stay on
    cmds.setKeyframe("persp", attribute="translateX", time=5, value=0)       # B edited, unsaved
    opening.reload_tab("tab_camkA", ask=False)
    gate("cameras: reloading hidden A leaves B's keys on persp",
         source("persp.translateX").startswith("tab_camkB:") and tx(5) == 0.0, tx(5))
    switching.switch("tab_camkA")
    gate("cameras: ... and A comes back with its file's keys", tx(10) == 50
         and source("persp.translateX").startswith("tab_camkA:"), (tx(10), source("persp.translateX")))
    # a session saved and opened again: the hidden tabs' keys come back by their UUIDs
    switching.switch("tab_camkC")
    recovered = RUN + "/camk_session.ma"
    with hooks.bypass():
        cmds.file(rename=recovered)
        cmds.file(save=True, force=True, type="mayaAscii")
    fresh()
    cmds.file(recovered, open=True, force=True)
    opening.restore()
    gate("cameras: restored, the active tab C's key on persp", session.state()["active"] == "tab_camkC"
         and source("persp.translateY").startswith("tab_camkC:") and not source("persp.translateX"),
         (session.state()["active"], source("persp.translateY"), source("persp.translateX")))
    switching.switch("tab_camkA")
    gate("cameras: restored, hidden A's keys come back on its switch", tx(10) == 50 and not source("persp.translateY"),
         tx(10))
    # a hidden tab closed takes its keys with it
    opening.ASK = lambda message, buttons: "Don't Save"
    try:
        opening.close_tab("tab_camkB", ask=False)
    finally:
        opening.ASK = None
    gate("cameras: closing hidden B deletes its curves, A's keys stay",
         not cmds.ls("tab_camkB:*", type="animCurve") and tx(10) == 50)


def _cam(name="persp", attr="translate"):
    node = name if attr in ("translate", "rotate") else cmds.listRelatives(name, shapes=True)[0]
    value = cmds.getAttr(node + "." + attr)
    if isinstance(value, list):
        return [round(v, 4) for v in value[0]]
    return round(value, 4)


def _cam_file(path, kind, unit="cm", persp=None, top_ow=None, side_ow=None, fl=None, tp=None):
    fresh()
    cmds.currentUnit(linear=unit)
    cmds.polyCube(name="box_" + os.path.splitext(os.path.basename(path))[0])
    if persp:
        cmds.setAttr("persp.t", *persp[0])
        cmds.setAttr("persp.r", *persp[1])
    if fl:
        cmds.setAttr("perspShape.fl", fl)
    if tp:
        cmds.setAttr("perspShape.tp", *tp)
    if top_ow:
        cmds.setAttr("top.t", 5, 1000, 7)
        cmds.setAttr("topShape.ow", top_ow)
    if side_ow:
        cmds.setAttr("sideShape.ow", side_ow)
    _save(path, kind)


def phase_cameras():
    """2026-10-16, the animator: «камеры перспективы и других направлений общие для всех
    вкладок». Each tab keeps its own persp / top / front / side: its file's when it opens
    (an import leaves the scene's), what it showed when it was left, Maya's defaults in an
    empty tab; a save writes them into its file; a session file brings the active tab's."""
    from maya_scenetabs import hooks, opening, saving, switching
    os.makedirs(RUN, exist_ok=True)
    a, b, m = RUN + "/camA.ma", RUN + "/camB.mb", RUN + "/camM.ma"
    _cam_file(a, "mayaAscii", persp=((100, 50, 30), (-20, 70, 0)), fl=50, top_ow=77)
    _cam_file(b, "mayaBinary", persp=((-80, 40, 60), (-15, -50, 0)), fl=24, tp=(1, 2, 3), side_ow=55)
    _cam_file(m, "mayaAscii", unit="meter", persp=((1, 2, 3), (-10, 30, 0)))
    fresh()
    cmds.file(a, open=True, force=True)
    opening.ASK = lambda message, buttons: "Don't Save"
    opening.open_tab(b)
    cmds.undoInfo(state=True, infinity=True)
    gate("cameras: a tab opened from a .mb takes its file's persp",
         _cam() == [-80.0, 40.0, 60.0] and _cam(attr="rotate") == [-15.0, -50.0, 0.0]
         and _cam(attr="focalLength") == 24.0 and _cam(attr="tumblePivot") == [1.0, 2.0, 3.0],
         (_cam(), _cam(attr="rotate"), _cam(attr="focalLength"), _cam(attr="tumblePivot")))
    gate("cameras: and its side camera, the top the default its file has",
         _cam("side", "orthographicWidth") == 55.0 and _cam("top", "orthographicWidth") == 30.0
         and _cam("top") == [0.0, 1000.1, 0.0])
    gate("cameras: no camera came in with the import", len(cmds.ls(type="camera")) == 4, cmds.ls(type="camera"))
    switching.switch("tab_camA")
    switching.switch("tab_camB")
    switching.switch("tab_camA")
    state = session.state()
    gate("cameras: switching leaves clean tabs clean (it flagged every tab it entered)",
         not cmds.file(q=True, modified=True)
         and not any(t["modified"] for t in state["tabs"]), [(t["ns"], t["modified"]) for t in state["tabs"]])
    cmds.setAttr("tab_camA:box_camA.translateX", 3)
    switching.switch("tab_camB")
    clean_b = not cmds.file(q=True, modified=True)
    switching.switch("tab_camA")
    gate("cameras: a modified tab stays modified, the other clean",
         clean_b and cmds.file(q=True, modified=True), clean_b)
    cmds.setAttr("tab_camA:box_camA.translateX", 0)
    cmds.file(modified=False)
    opening.reload_tab("tab_camB", ask=False)
    switching.switch("tab_camB")
    gate("cameras: a hidden tab read again from disk keeps its camera", _cam() == [-80.0, 40.0, 60.0], _cam())
    switching.switch("tab_camA")
    gate("cameras: the first tab's own back", _cam() == [100.0, 50.0, 30.0]
         and _cam(attr="focalLength") == 50.0 and _cam("top", "orthographicWidth") == 77.0
         and _cam("top") == [5.0, 1000.0, 7.0] and _cam("side", "orthographicWidth") == 30.0,
         (_cam(), _cam("top"), _cam("top", "orthographicWidth")))
    cmds.setAttr("persp.t", 11, 22, 33)
    cmds.setAttr("perspShape.coi", 66)
    switching.switch("tab_camB")
    gate("cameras: a move in one tab stays there", _cam() == [-80.0, 40.0, 60.0], _cam())
    switching.switch("tab_camA")
    gate("cameras: and comes back with it", _cam() == [11.0, 22.0, 33.0]
         and _cam(attr="centerOfInterest") == 66.0, (_cam(), _cam(attr="centerOfInterest")))
    switching.switch("tab_camB")
    cmds.undo()
    gate("cameras: Ctrl+Z after a switch stays in B with B's camera (2026-10-19)",
         session.state()["active"] == "tab_camB" and _cam() == [-80.0, 40.0, 60.0],
         (session.state()["active"], _cam()))
    switching.switch("tab_camA")
    opening.new_tab()
    gate("cameras: an empty tab has a new scene's cameras",
         _cam() == [28.0, 21.0, 28.0] and _cam(attr="focalLength") == 35.0
         and _cam("top", "orthographicWidth") == 30.0 and _cam("top") == [0.0, 1000.1, 0.0], _cam())
    opening.open_tab(m)
    gate("cameras: a file in meters opens in this scene's centimeters",
         _cam() == [100.0, 200.0, 300.0] and _cam(attr="rotate") == [-10.0, 30.0, 0.0], _cam())
    switching.switch("tab_camB")
    cmds.setAttr("persp.t", 7, 8, 9)
    switching.switch("tab_camA")
    saved = RUN + "/camB_saved.ma"
    message = saving.save_tab("tab_camB", path=saved, adopt=False)
    gate("cameras: a tab saved while another was active", str(message).startswith("Saved")
         and session.state()["active"] == "tab_camB", message)
    text = open(saved).read()
    gate("cameras: its file holds its persp, not the other tab's",
         'createNode transform -s -n "persp"' in text and '".t" -type "double3" 7 8 9' in text
         and "11 22 33" not in text)
    probe = RUN + "/camB_session.ma"
    cmds.setAttr("persp.t", 4, 5, 6)
    with hooks.bypass():
        cmds.file(rename=probe)
        cmds.file(save=True, force=True, type="mayaAscii")
    fresh()
    cmds.file(saved, open=True, force=True)
    gate("cameras: the saved file opened alone shows the tab's persp",
         _cam() == [7.0, 8.0, 9.0] and _cam(attr="focalLength") == 24.0
         and _cam("side", "orthographicWidth") == 55.0 and cmds.objExists("box_camB")
         and len(cmds.ls(type="camera")) == 4, (_cam(), _cam(attr="focalLength")))
    fresh()
    opening.open_tab(saved)
    gate("cameras: and opened as a tab", _cam() == [7.0, 8.0, 9.0], _cam())
    fresh()
    cmds.file(probe, open=True, force=True)
    opening.restore()
    gate("cameras: a session file brings the active tab's camera as it was saved",
         session.state()["active"] == "tab_camB" and _cam() == [4.0, 5.0, 6.0], _cam())
    switching.switch("tab_camA")
    gate("cameras: the other tabs keep theirs across the session file", _cam() == [11.0, 22.0, 33.0], _cam())
    switching.switch("tab_camB")
    gate("cameras: and the active one its newest", _cam() == [4.0, 5.0, 6.0], _cam())
    hooks.remove()
    opening.ASK = None


def phase_undo():
    """Each tab its own undo history as far as one queue allows (2026-10-19): Ctrl+Z never
    reaches another tab's work nor switches tabs; a tab left untouched goes on with the
    history under it; a fence redone from another tab is taken back."""
    from maya_scenetabs import opening, switching, tabundo
    rig, film = copy("rig.ma"), copy("film.ma")
    fresh()
    cmds.file(rig, open=True, force=True)
    opening.open_tab(film)
    said, say = [], tabundo._say
    tabundo._say = lambda message, cmds_: said.append(message)
    # an unkeyed probe of the film's own: hero's channels follow their curves on a time change
    cmds.undoInfo(stateWithoutFlush=False)
    probe = cmds.spaceLocator(name=":tab_film:probe")[0]
    cmds.undoInfo(stateWithoutFlush=True)
    hero, shoulder = probe + ".translateX", "tab_rig:Manny_Rig:FKShoulder_L.rotateY"
    gate("undo: the film active after its open, the queue flushed and its own",
         session.state()["active"] == "tab_film" and tabundo.state()["owner"] == "tab_film")
    cmds.setAttr(hero, 1)
    switching.switch("tab_rig")
    cmds.setAttr(shoulder, 10)
    switching.switch("tab_film")
    cmds.undo()
    gate("undo: in the film, Ctrl+Z stops at its fence - the rig's step and the film's own kept",
         session.state()["active"] == "tab_film" and cmds.getAttr(hero) == 1.0 and cmds.getAttr(shoulder) == 10.0,
         (cmds.getAttr(hero), cmds.getAttr(shoulder)))
    gate("undo: and says its earlier steps are under another tab's work", said[-1:] == [tabundo.UNDER], said)
    switching.switch("tab_rig")
    gate("undo: the film left untouched - its fence popped, no new fence for the rig",
         cmds.undoInfo(q=True, undoName=True) == "" or not tabundo.is_fence(cmds.undoInfo(q=True, undoName=True)),
         cmds.undoInfo(q=True, undoName=True))
    cmds.undo()
    gate("undo: back in the rig, its history goes on - its step undone",
         session.state()["active"] == "tab_rig" and cmds.getAttr(shoulder) == 0.0 and cmds.getAttr(hero) == 1.0)
    cmds.undo()
    gate("undo: then its own fence - the film's step under it kept",
         session.state()["active"] == "tab_rig" and cmds.getAttr(hero) == 1.0 and said[-1:] == [tabundo.START],
         said)
    cmds.redo()
    gate("redo: the rig's step again", cmds.getAttr(shoulder) == 10.0)
    switching.switch("tab_film")
    switching.switch("tab_rig")
    cmds.redo()
    top = cmds.undoInfo(q=True, undoName=True) or ""
    gate("redo: the film's fence popped into the redo queue is taken back - nothing changes, still the rig",
         session.state()["active"] == "tab_rig" and cmds.getAttr(shoulder) == 10.0 and cmds.getAttr(hero) == 1.0
         and tabundo.fence_tab(top) != "tab_film", top)
    cmds.undo()
    gate("undo: the rig's step still the next undo", cmds.getAttr(shoulder) == 0.0)
    cmds.setAttr(shoulder, 5)
    for _ in range(4):
        cmds.undo()
    gate("undo: four Ctrl+Z in a row stay in the rig",
         session.state()["active"] == "tab_rig" and cmds.getAttr(shoulder) == 0.0 and cmds.getAttr(hero) == 1.0)
    tabundo._say = say


PHASES = {"undo": phase_undo, "session": phase_session, "layers_alone": phase_layers_alone, "convert": phase_convert,
          "layers": phase_layers, "open_close": phase_open_close, "switch": phase_switch,
          "save": phase_save, "hooks": guarded(phase_hooks), "restore": guarded(phase_restore),
          "hook_failures": guarded(phase_hook_failures), "review": guarded(phase_review),
          "untitled": guarded(phase_untitled), "duplicates": phase_duplicates,
          "layer_editor": phase_layer_editor, "outliner_sets": phase_outliner_sets,
          "nested": phase_nested, "pasted": phase_pasted, "cameras": phase_cameras,
          "leak": phase_leak, "stash_open": phase_stash_open, "maya_open": guarded(phase_maya_open), "camera_keys": phase_camera_keys}


def main(names):
    fixtures()
    for name in names:
        try:
            PHASES[name]()
        except Exception:                                       # noqa: BLE001
            gate("phase %s ran to the end" % name, False, traceback.format_exc())
    failed = RESULTS.count(False)
    print("%d of %d gates failed" % (failed, len(RESULTS)))
    return failed


if __name__ == "__main__":
    wanted = sys.argv[1:] or ["all"]
    if wanted == ["all"]:
        wanted = list(PHASES)
    code = main(wanted)
    maya.standalone.uninitialize()
    sys.exit(1 if code else 0)
