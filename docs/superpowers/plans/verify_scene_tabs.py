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
    gate("undo: the next Ctrl+Z brings the film back",
         session.state()["active"] == "tab_film" and cmds.currentUnit(q=True, time=True) == "film"
         and all(tops_visible("tab_film")) and not any(tops_visible("tab_rig")))
    cmds.undo()
    gate("undo: and then undoes the film's step", cmds.getAttr("tab_film:hero.translateX") == 0.0)
    cmds.redo()
    cmds.redo()
    gate("redo: forward to the rig again",
         session.state()["active"] == "tab_rig" and cmds.currentUnit(q=True, time=True) == "ntsc")
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
         and not os.path.exists(RUN + "/film_failed_cleanup.ma.skeldartmp"),
         (cleanup_error, cmds.undoInfo(q=True, stateWithoutFlush=True)))
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
    gate("outliner sets: undo of the switch hides A's set again",
         session.state()["active"] == b and hidden(a + ":selA") and not hidden(b + ":selB"))
    cmds.redo()
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
    gate("layer editor: undo of the switch brings B's layers back and takes A's out",
         session.state()["active"] == b and on_root(b) == [b + ":AnimLayerRoot"] and on_root(a) == []
         and shown_id(b, "B")[1] and shown_id(a, "A") == (0, False))
    cmds.redo()
    gate("layer editor: redo too", session.state()["active"] == a and on_root(a) == [a + ":AnimLayerRoot"]
         and on_root(b) == [])
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


PHASES = {"session": phase_session, "layers_alone": phase_layers_alone, "convert": phase_convert,
          "layers": phase_layers, "open_close": phase_open_close, "switch": phase_switch,
          "save": phase_save, "hooks": guarded(phase_hooks), "restore": guarded(phase_restore),
          "hook_failures": guarded(phase_hook_failures), "review": guarded(phase_review),
          "untitled": guarded(phase_untitled), "duplicates": phase_duplicates,
          "layer_editor": phase_layer_editor, "outliner_sets": phase_outliner_sets,
          "nested": phase_nested}


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
