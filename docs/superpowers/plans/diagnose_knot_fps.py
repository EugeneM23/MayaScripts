"""Where a scene with our knots / aims loses its frame rate (2026-10-15) - run in the animator's
Maya, the scene that plays slowly open, a knot or aim of the Tools card in it.

The animator: «Просадка производительности происходит после когда у меня создан aim и я
проигрываю анимацию или двигаю контролы ... чего не происходит с работой over rig». Measured in
mayapy first (Manny_Rig, 240 keyed frames, an aim on FKHead_M): the evaluation costs the same with
and without our aim (4.7 against 4.8 ms a frame in parallel, a control dragged 0.26 against 0.20 ms
a step), Cached Playback stays on and fills - so what is slow is something only a GUI has. This
script tells which, in the scene where it happens, and changes nothing it does not put back.

Drop it into a viewport (or exec it in the Script Editor). It plays the playback range at free
speed, once, four times each way, and prints frames a second:

  A  as the scene is;
  B  our knots hidden (their groups' and across knots' visibility off) - the DRAWING of them;
  C  our knot constraints and their pairBlends switched off (nodeState HasNoEffect) - the GRAPH;
  D  both.

and the state that decides playback: the evaluation mode, Cached Playback and whether its safe
mode was triggered (with Maya's own messages), the number of our knots, constraints, pairBlends,
and OverRig's knots for comparison. Copy the printout back.
"""
import time

import maya.cmds as cmds

RUNS = 4


def _ours():
    """(groups to hide, constraints, pairBlends) of the Tools card's knots."""
    from maya_tools import knots, knotplan as plan
    tops = knots.knots()
    groups = list(knots._groups())
    across = [t for t in tops if not any(t.startswith(g + "|") for g in groups)]
    cons, blends = [], []
    for con in cmds.ls(type="constraint", long=True) or []:
        if knots._has(con, plan.OF_MARKER):
            cons.append(con)
            parent = (cmds.listRelatives(con, parent=True, fullPath=True) or [None])[0]
            for b in cmds.listConnections(parent, source=True, destination=False,
                                          type="pairBlend") or [] if parent else []:
                if b not in blends:
                    blends.append(b)
    return tops, groups + across, cons, blends


def _fps():
    first = cmds.playbackOptions(query=True, min=True)
    last = cmds.playbackOptions(query=True, max=True)
    best = 0.0
    for _ in range(RUNS):
        cmds.currentTime(first)
        t = time.perf_counter()
        cmds.play(forward=True, wait=True)
        dt = time.perf_counter() - t
        best = max(best, (last - first + 1) / dt if dt > 0 else 0.0)
    return best


def _state():
    out = {}
    out["evaluation"] = cmds.evaluationManager(query=True, mode=True)
    for name, call in (("cache on", lambda: cmds.evaluator(name="cache", query=True,
                                                            enable=True)),
                       ("cache safe mode", lambda: cmds.cacheEvaluator(
                           query=True, safeModeTriggered=True)),
                       ("cache messages", lambda: cmds.cacheEvaluator(
                           query=True, safeModeMessages=True))):
        try:
            out[name] = call()
        except Exception as error:                              # noqa: BLE001
            out[name] = "? %s" % error
    return out


def run():
    tops, hide, cons, blends = _ours()
    overrig = cmds.sets("OverRig_knots", query=True) if cmds.objExists("OverRig_knots") else []
    print("\n=== knot FPS diagnosis ===")
    print("our knots %d (%s)" % (len(tops), ", ".join(t.split("|")[-1] for t in tops[:6])))
    print("our constraints %d, pairBlends %d; OverRig knots %d" % (len(cons), len(blends),
                                                                   len(overrig or [])))
    for key, value in _state().items():
        print("  %s: %s" % (key, value))
    options = dict((k, cmds.playbackOptions(query=True, **{k: True}))
                   for k in ("loop", "playbackSpeed", "maxPlaybackSpeed"))
    now = cmds.currentTime(query=True)
    vis = dict((n, cmds.getAttr(n + ".visibility")) for n in hide)
    states = dict((n, cmds.getAttr(n + ".nodeState")) for n in cons + blends)
    auto = cmds.autoKeyframe(query=True, state=True)
    results = {}
    try:
        cmds.autoKeyframe(state=False)
        cmds.playbackOptions(loop="once", playbackSpeed=0, maxPlaybackSpeed=0)

        def visible(on):
            for n, v in vis.items():
                cmds.setAttr(n + ".visibility", v if on else 0)

        def active(on):
            for n, s in states.items():
                cmds.setAttr(n + ".nodeState", s if on else 1)

        for label, draw, graph in (("A as the scene is", True, True),
                                   ("B knots hidden", False, True),
                                   ("C knot graph off", True, False),
                                   ("D both", False, False)):
            visible(draw)
            active(graph)
            results[label] = _fps()
            print("  %-20s %.1f fps" % (label, results[label]))
    finally:
        for n, v in vis.items():
            cmds.setAttr(n + ".visibility", v)
        for n, s in states.items():
            cmds.setAttr(n + ".nodeState", s)
        cmds.playbackOptions(**options)
        cmds.autoKeyframe(state=auto)
        cmds.currentTime(now)
    print("  after: %s" % _state())
    print("=== copy everything from '=== knot FPS diagnosis' up ===\n")
    return results


def onMayaDroppedPythonFile(*_):
    run()


if __name__ == "__main__":
    run()
