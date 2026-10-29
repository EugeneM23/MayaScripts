"""The screen share, live, in a GUI Maya: the whole screen in one press, its own window, and
drawing over it (spec docs/superpowers/specs/2026-10-29-chat-screen-share-stage-drawing-design.md).

A real call window with a real call page and a fake session - nothing reaches a server. The share
is a real capture of this screen, so this runs in a Maya with a screen, over the command port:

    p = r'<this file>'
    exec(compile(open(p, encoding='utf-8').read(), p, 'exec'), {'__name__': '__main__', '__file__': p})

It writes its gates to verify_call_stage_out.txt beside itself and leaves nothing standing.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
OUT = os.path.join(HERE, "verify_call_stage_out.txt")
MARK = OUT + ".ran"

if not os.path.exists(MARK):
    open(MARK, "w").write("ran")
    LINES, GATES = [], []

    def say(text):
        LINES.append(str(text))
        with open(OUT, "w", encoding="utf-8") as f:
            f.write("\n".join(LINES) + "\n")

    def gate(name, ok, detail=""):
        GATES.append(bool(ok))
        say(("PASS " if ok else "FAIL ") + name + ((" - " + str(detail)) if detail else ""))

    try:
        for path in (os.path.join(REPO, "SkeldarAnim"), REPO):
            if path not in sys.path:
                sys.path.insert(0, path)
        for name in [n for n in list(sys.modules) if n.startswith("maya_chat")]:
            del sys.modules[name]
        os.environ.setdefault("QT_QPA_PLATFORM", "")          # a real screen: never offscreen
        from PySide6 import QtCore, QtWidgets
        from maya_chat import callview as V
        from maya_chat import session as S

        app = QtWidgets.QApplication.instance()
        ME, BOB = "me", "bob"

        def pump(seconds, until=None):
            end = time.time() + seconds
            while time.time() < end:
                app.processEvents(QtCore.QEventLoop.AllEvents, 30)
                if until and until():
                    return True
                time.sleep(0.01)
            return bool(until and until())

        class FakeSession(object):
            def __init__(self):
                self.state = S.State()
                self.state.me = {"id": ME, "nick": "me", "name": u"Я"}
                self.state.chats = {"dm": {"id": "dm", "kind": "dm", "name": u"Боб",
                                           "members": [{"id": ME, "name": u"Я"},
                                                       {"id": BOB, "name": u"Боб"}]}}
                self.listeners, self.calls = [], []

            def listen(self, fn):
                self.listeners.append(fn)

            def unlisten(self, fn):
                if fn in self.listeners:
                    self.listeners.remove(fn)

            def tell(self, kind, data):
                for fn in list(self.listeners):
                    fn(kind, data)

            def start_call(self, chat, kind):
                return "c-1"

            def leave_call(self, call_id):
                return True

            def call_signal(self, call_id, to, data):
                self.calls.append((to, data))
                return True

            def turn_servers(self, now=None):
                return [{"urls": ["stun:stun.cloudflare.com:3478"]}], False

            def call_here(self, call_id, on):
                pass

        def js(page, code, seconds=8):
            box = {}
            page.runJavaScript(code, lambda v: box.setdefault("v", v))
            pump(seconds, lambda: "v" in box)
            return box.get("v")

        def obj(page, code, seconds=8):
            raw = js(page, "JSON.stringify(%s)" % code, seconds)
            try:
                return json.loads(raw) if raw else None
            except ValueError:
                return None

        V.destroy()          # never a second call standing: it would ask, and a modal over the
        pump(0.5)            # command port stops Maya's idle queue (CLAUDE.md, the bridge's note 6)
        ses = FakeSession()
        win = V.start(ses, "dm", "video")
        gate("the call window opens with a real page", win is not None and win.page is not None)
        pump(25, lambda: win.page_ready)
        gate("the page is ready", win.page_ready)
        view = {"id": "c1", "chat": "dm", "by": ME, "kind": "video", "cid": "c-1", "state": "live",
                "members": [ME], "declined": [], "started_at": int(time.time() * 1000),
                "answered_at": int(time.time() * 1000), "ended_at": None}
        ses.tell("call", {"kind": "call", "call": view})
        pump(6, lambda: win.started)
        gate("the call started", win.started,
             (win.call_id, win.chat, win._pending_view is not None, win.page_ready,
              obj(win.page, "S.me"), obj(win.page, "S.colours")))

        # ------------------------------------------------ one press, the whole screen
        menus = []
        real_pick = V._pick_screen
        V._pick_screen = lambda w, choices: menus.append(choices) or None
        win.press("screen")
        shared = pump(25, lambda: bool(win.state.get("screen")))
        V._pick_screen = real_pick
        gate("one press shares the screen, with no menu", shared and not menus, (shared, menus))
        cap = win.state.get("capture") or {}
        gate("it is the whole monitor", cap.get("surface") == "monitor", cap)
        gate("the window says what is shared",
             win.last_message.startswith(u"Экран"), win.last_message)

        # ------------------------------------------------ the screen's own window
        staged = pump(20, lambda: win.stage is not None)
        gate("the shared screen opens its own window", staged, win.state.get("wants_stage"))
        if staged:
            gate("the stage window is up and framed",
                 win.stage.root.isVisible() and win.stage.root.objectName() == V.STAGE_NAME)
            here = obj(win.page, "document.querySelectorAll('#grid .tile.screen').length")
            gate("the call window's grid is left with the cameras", here == 0, here)
            strip = js(win.page, "document.getElementById('grid').style.gridTemplateRows || 'none'")
            gate("no 96 px strip under them", "96px" not in (strip or ""), strip)
            shown = obj(win.stage.page, """
(() => { const v = document.querySelector("video");
  return v ? {w: v.videoWidth, h: v.videoHeight, t: v.currentTime, paused: v.paused} : null; })()
""")
            gate("the live picture is in the stage window", bool(shown and shown.get("w")), shown)
            pump(1.5)
            later = obj(win.stage.page, "(() => { const v = document.querySelector('video');"
                                        " return v ? v.currentTime : 0; })()")
            gate("and it is still moving there",
                 bool(shown) and later and later > shown.get("t", 0), (shown, later))

            # ------------------------------------------------ drawing over it
            win.bridge.send("draw", {"on": True})
            pump(1)
            gate("the pen is on", bool(win.state.get("drawing")), win.state.get("drawing"))
            js(win.page, "ink('bob', {id: 'bob:1', c: '#ff00ff',"
                         " pts: [[0.2,0.2],[0.5,0.5],[0.8,0.3]], end: true});")
            pump(0.7)
            say("    [ink] " + str(obj(win.page, """
(() => { let err = ""; try { paintInk(); } catch (e) { err = String(e); }
  const t = screenTile();
  const c = t && t.querySelector("canvas.ink");
  const r = c && c.getBoundingClientRect();
  return {stageTile: !!S.stageTile, cls: S.stageTile ? S.stageTile.className : null,
          found: !!t, strokes: S.strokes.size, err: err, drawing: S.drawing,
          rect: r ? [Math.round(r.width), Math.round(r.height)] : null,
          size: c ? [c.width, c.height] : null,
          grid: document.querySelectorAll('#grid .tile').length}; })()
""")))
            inked = obj(win.stage.page, """
(() => { const c = document.querySelector("canvas.ink");
  if (!c || !c.width) return {n: 0};
  const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
  let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 10) n++;
  return {n: n, w: c.width, h: c.height}; })()
""")
            say("    [stage dom] " + str(obj(win.stage.page, """
(() => { const t = document.querySelector(".tile"), c = document.querySelector("canvas.ink");
  const cs = c && getComputedStyle(c), ts = t && getComputedStyle(t);
  return {styles: document.querySelectorAll("style").length, body: document.body.className,
          tilePos: ts && ts.position, tileBox: t ? [Math.round(t.getBoundingClientRect().width),
                                                    Math.round(t.getBoundingClientRect().height)] : null,
          canvasPos: cs && cs.position, canvasDisplay: cs && cs.display,
          inner: [innerWidth, innerHeight]}; })()
""")))
            gate("a stroke is drawn over the shared screen", (inked or {}).get("n", 0) > 50, inked)
            sent = [d for to, d in ses.calls if isinstance(d, dict) and d.get("draw")]
            js(win.page, "ink('bob', {id: 'bob:2', c: '#00ffff', pts: [[0.3,0.6]], end: true});")
            pump(4.2)
            faded = obj(win.stage.page, """
(() => { const c = document.querySelector("canvas.ink");
  if (!c || !c.width) return {n: 0};
  const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
  let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 10) n++;
  return {n: n}; })()
""")
            gate("a stroke fades away by itself", (faded or {}).get("n", 0) == 0, faded)
            gate("the strokes are let go", obj(win.page, "S.strokes.size") == 0)

            # ------------------------------------------------ closing it
            win.stage.close()
            pump(2)
            back = obj(win.page, "document.querySelectorAll('#grid .tile.screen').length")
            gate("closing the stage puts the screen back in the call window", back == 1, back)
            gate("the stage window is gone", win.stage is None)

        # ------------------------------------------------ the other side, for real
        # A second page wired to this one through the window's own signalling: it is the one the
        # animator asked about - «чтобы участники могли рисовать по экрану того кто стримит».
        from maya_chat import callpage
        other = {"state": {}}
        other["bridge"] = callpage.bridge_class()(
            lambda: other.__setitem__("ready", True),
            lambda to, data: win.bridge.send("signal", {"from": BOB, "data": data}),
            lambda s: other.__setitem__("state", s))
        other["view"], other["page"] = callpage.make_view(other["bridge"])
        other["view"].resize(420, 260)
        other["view"].show()
        ses.calls = []
        ses.call_signal = lambda call_id, to, data: (
            other["bridge"].send("signal", {"from": ME, "data": data}), True)[1]
        pump(20, lambda: other.get("ready"))
        view2 = dict(view, members=[ME, BOB])
        ses.tell("call", {"kind": "call", "call": view2})
        other["bridge"].send("start", {"me": BOB, "names": {ME: u"Я", BOB: u"Боб"},
                                       "colours": {ME: "#7a6bb0", BOB: "#4f8a8b"},
                                       "ice_servers": [{"urls": ["stun:stun.cloudflare.com:3478"]}],
                                       "video": False, "peers": [ME], "offer_to": [ME]})
        joined = pump(40, lambda: ((other["state"].get("peers") or {}).get(ME) or {})
                      .get("state") == "connected")
        gate("the other side connects", joined,
             (other["state"].get("peers"), win.state.get("peers")))
        win.press("screen")                                   # the first share off
        pump(5, lambda: not win.state.get("screen"))
        win.press("screen")                                   # and a fresh one
        sharing = pump(25, lambda: ((other["state"].get("peers") or {}).get(ME) or {}).get("screen")
                       and win.state.get("screen"))
        gate("the other side sees the share", sharing)
        staged2 = pump(15, lambda: win.stage is not None)
        gate("a new share opens the stage again, after it was closed by hand", staged2)
        if staged2 and sharing:
            win.bridge.send("draw", {"on": True})
            pump(1)
            target = win.stage.view.focusProxy() or win.stage.view
            from PySide6 import QtGui
            w, h = target.width(), target.height()
            path = [(0.30, 0.40), (0.45, 0.55), (0.62, 0.45), (0.70, 0.60)]
            kinds = [QtCore.QEvent.MouseButtonPress] + [QtCore.QEvent.MouseMove] * 2 \
                + [QtCore.QEvent.MouseButtonRelease]
            for (fx, fy), kind in zip(path, kinds):
                point = QtCore.QPointF(w * fx, h * fy)
                glob = QtCore.QPointF(target.mapToGlobal(point.toPoint()))
                # a move carries no button of its own, only the one held: given LeftButton as the
                # event's button, Chromium read each move as another press (two strokes)
                button = QtCore.Qt.NoButton if kind == QtCore.QEvent.MouseMove \
                    else QtCore.Qt.LeftButton
                held = QtCore.Qt.NoButton if kind == QtCore.QEvent.MouseButtonRelease \
                    else QtCore.Qt.LeftButton
                app.sendEvent(target, QtGui.QMouseEvent(kind, point, glob, button, held,
                                                        QtCore.Qt.NoModifier))
                pump(0.25)
            # Synthetic mouse events are not a drag: Chromium reads the real cursor, which is
            # elsewhere, and splits the press from the moves (the repo's trap 138). What they do
            # prove is that a drag over the picture makes a stroke and carries its points; one
            # unbroken stroke under a real hand is the animator's own check.
            mine = obj(win.page, "S.strokes.size")
            points = obj(win.page, "[...S.strokes.values()].reduce((n, s) => n + s.pts.length, 0)")
            gate("drawing on the stage makes a stroke", (mine or 0) >= 1 and (points or 0) >= 3,
                 (mine, points))
            shot = os.environ.get("CALL_STAGE_SHOT")       # a picture of it, where asked for
            if shot:
                try:
                    # DWM's own copy: a composited window comes out black of grabWindow (trap 134)
                    from maya_graphoverlay import winstyle
                    from PySide6 import QtGui
                    root = win.stage.root
                    hwnd = int(root.winId())
                    w, h = root.width(), root.height()
                    raw = winstyle.capture(hwnd, w, h)
                    img = QtGui.QImage(raw, w, h, QtGui.QImage.Format_RGB32)
                    img.copy().save(shot)
                    say("    [picture] " + shot)
                except Exception as exc:                      # noqa: BLE001
                    say("    [picture] failed: %r" % (exc,))
            theirs = pump(6, lambda: (obj(other["page"], "S.strokes.size") or 0) >= 1)
            gate("the stroke reaches the other participant", theirs,
                 obj(other["page"], "[...S.strokes.values()].map(s => [s.uid, s.colour, s.pts.length])"))
            there = obj(other["page"], """
(() => { const c = document.querySelector(".tile.screen canvas.ink");
  if (!c || !c.width) return {n: 0};
  const d = c.getContext("2d").getImageData(0, 0, c.width, c.height).data;
  let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 10) n++;
  return {n: n, w: c.width}; })()
""")
            gate("and is drawn over their copy of the screen", (there or {}).get("n", 0) > 20, there)

        # ------------------------------------------------ a capture that stalls
        win.bridge.send("draw", {"on": False})
        # A capture that stopped handing out frames: the frame callbacks are stopped too, or the
        # next real frame clears the stall inside the report's own 30 ms and nothing is reported.
        say("    [stall] " + str(obj(win.page, """
(() => { S.frameToken = (S.frameToken || 0) + 1; S.lastFrame = Date.now() - 60000; let err = "";
  try { checkStall(); } catch (e) { err = String(e); }
  return {err: err, screen: S.screen, track: S.screenTrack && S.screenTrack.readyState,
          stalled: S.stalled, seen: document.visibilityState, last: Date.now() - S.lastFrame}; })()
""")))
        # the line says it, and is then replaced by the fresh capture's own - count the re-take
        retaken = pump(10, lambda: win._retakes >= 1)
        gate("a stalled capture is noticed and taken again", retaken,
             (win._retakes, win.last_message))
        pump(3)
        gate("and the share is alive after the re-take", bool(win.state.get("screen")))

        try:
            other["view"].close()
        except Exception:                                     # noqa: BLE001
            pass
        win.press("screen")
        pump(4)
        gate("the share stops", not win.state.get("screen"), win.state.get("screen"))
        say("")
        say("%d of %d gates failed" % (GATES.count(False), len(GATES)))
    except Exception:
        import traceback
        LINES.append(traceback.format_exc())
        with open(OUT, "w", encoding="utf-8") as f:
            f.write("\n".join(LINES) + "\n")
    finally:
        try:
            V.hang_up()
        except Exception:                                     # noqa: BLE001
            pass
        LINES.append("done")
        with open(OUT, "w", encoding="utf-8") as f:
            f.write("\n".join(LINES) + "\n")
