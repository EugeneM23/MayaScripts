"""A call is HEARD: two real call pages, and the question no gate ever asked - is the voice that
arrives actually rendered?

The animator, 2026-10-29: «Сейчас когда созваниваемся то не слышно собеседников. Но становиться
слышно когда шарим рабочий стол.» Measured: a remote participant's audio was played by the tile's
<video>, and a <video> whose MediaStream carries a live-but-FRAMELESS video track stands at
readyState 0 and renders NOTHING - which is every voice call, and every camera turned off. The
moment any frame arrives (a camera, a shared screen) the element starts and the voice comes with
it. That is the animator's "it becomes audible when we share".

The instrument is the element's own playback: a rendering element's currentTime advances, one that
renders nothing stays at 0. Bytes on the wire prove nothing about being heard, which is why every
earlier gate passed.

    1  a voice call connects and a's audio arrives at b
    2  b RENDERS it: four seconds of playback in four seconds        <- 0.000 before the fix
    3  the picture is silent: the <video> never carries the voice
    4  a's camera on - still rendered, and the picture plays
    5  a's camera off again - STILL rendered                          <- 0.000 before the fix
    6  a shared screen and its end - still rendered
    7  nobody hears themselves: the local tile has no audio sink
    8  the speaking light still has its analyser on the remote track
    9  a peer who leaves takes their sink with them

Everything here is silent on purpose: the microphone is a synthetic track at gain 0 and the camera
a canvas, so no device is opened, nothing is captured from the room and nothing can be heard - the
machine's own speakers stay out of it, which also keeps the two pages from feeding back.

    $env:QT_QPA_PLATFORM='offscreen'; mayapy docs/superpowers/plans/verify_call_audio.py

Spec: docs/superpowers/specs/2026-10-29-call-heard-and-which-screen-design.md
"""
import json
import os
import sys
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"
#  no --mute-audio and no fake device: the sources are silent by construction, and a muted output
#  is not what the animator has. No --autoplay-policy either - the animator's Maya has none, and
#  every earlier call verify set it (measured 2026-10-29: our page needs none, the attribute
#  PlaybackRequiresUserGesture=False does it).
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --disable-gpu-compositing"
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))

from PySide6 import QtCore, QtWidgets  # noqa: E402
from PySide6 import QtWebEngineWidgets  # noqa: E402,F401  (before the QApplication: shared GL)
QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)
app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

from maya_chat import callpage  # noqa: E402

GATES = []
SIDES = {}
ICE = [{"urls": ["stun:stun.cloudflare.com:3478"]}]
NAMES = {"a": "Ann", "b": "Bob"}
#  four seconds of real time: a rendering element advances by that much, one that renders nothing
#  by zero. Half of it is slack for a loaded machine.
RUN_S = 4.0
MOVED = RUN_S / 2.0


def gate(name, ok, detail=""):
    GATES.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" - " + str(detail) if detail else ""))
    sys.stdout.flush()


def pump(seconds, until=None):
    end = time.time() + seconds
    while time.time() < end:
        app.processEvents(QtCore.QEventLoop.AllEvents, 50)
        if until and until():
            return True
        time.sleep(0.01)
    return bool(until and until())


#  a microphone that is silent (a gain of 0) and a camera that really draws: no device is opened
FAKE = """
window.__ctx = window.__ctx || new AudioContext();
window.__cam = false;
if (!navigator.mediaDevices.__real) {
  navigator.mediaDevices.__real = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
  navigator.mediaDevices.getUserMedia = function (c) {
    const out = new MediaStream();
    if (c && c.audio) {
      const ctx = window.__ctx;
      const dest = ctx.createMediaStreamDestination();
      const gain = ctx.createGain(); gain.gain.value = 0;
      const osc = ctx.createOscillator(); osc.connect(gain); gain.connect(dest); osc.start();
      for (const t of dest.stream.getAudioTracks()) out.addTrack(t);
    }
    if (c && c.video) {
      if (!window.__cam) return Promise.reject(new DOMException("no cam", "NotFoundError"));
      const cv = document.createElement("canvas"); cv.width = 320; cv.height = 180;
      const g = cv.getContext("2d");
      setInterval(() => { g.fillStyle = "#" + Math.floor(Math.random() * 16777215).toString(16);
                          g.fillRect(0, 0, 320, 180); }, 60);
      for (const t of cv.captureStream(15).getVideoTracks()) out.addTrack(t);
    }
    return Promise.resolve(out);
  };
  navigator.mediaDevices.getDisplayMedia = function () {
    const cv = document.createElement("canvas"); cv.width = 1280; cv.height = 720;
    const g = cv.getContext("2d");
    setInterval(() => { g.fillStyle = "#" + Math.floor(Math.random() * 16777215).toString(16);
                        g.fillRect(0, 0, 1280, 720); }, 60);
    const s = cv.captureStream(15);
    for (const t of s.getVideoTracks()) {
      t.getSettings = () => ({displaySurface: "monitor", width: 1280, height: 720});
    }
    return Promise.resolve(s);
  };
}
"""

#  what the tile for `uid` is playing: the picture's element and the voice's, each with its own
#  playback position - the number that says whether anything is rendered at all
LOOK = """
(() => {
  const t = document.getElementById("t-%(uid)s");
  const read = (el) => el ? {
      has: true, paused: el.paused, ready: el.readyState, muted: el.muted,
      time: Math.round(el.currentTime * 1000) / 1000,
      tracks: el.srcObject ? el.srcObject.getTracks().map((x) => x.kind) : []
  } : {has: false};
  return {tile: !!t, cls: t ? t.className : null,
          video: read(t && t.querySelector("video")),
          audio: read(document.getElementById("s-%(uid)s")),
          levels: [...S.levels.keys()]};
})()
"""


class Side(object):
    def __init__(self, me):
        self.me, self.ready, self.state, self.other = me, False, {}, None
        SIDES[me] = self
        self.bridge = callpage.bridge_class()(self._ready, self._signal, self._state)
        self.view, self.page = callpage.make_view(self.bridge)
        self.view.resize(480, 300)
        self.view.show()

    def _ready(self):
        self.ready = True

    def _signal(self, to, data):
        SIDES[to].bridge.send("signal", {"from": self.me, "data": data})

    def _state(self, s):
        self.state = s

    def peer(self, uid=None):
        return (self.state.get("peers") or {}).get(uid or self.other.me) or {}

    def run(self, code):
        self.page.runJavaScript(code)
        pump(0.3)

    def obj(self, code, seconds=10):
        held = {}
        self.page.runJavaScript("JSON.stringify(%s)" % code, lambda v: held.setdefault("v", v))
        pump(seconds, lambda: "v" in held)
        raw = held.get("v")
        try:
            return json.loads(raw) if raw else None
        except ValueError:
            return raw

    def look(self, uid):
        return self.obj(LOOK % {"uid": uid}) or {}


def rendered(side, uid, what="audio"):
    """How many seconds of playback the element gave in RUN_S of real time."""
    first = (side.look(uid).get(what) or {}).get("time", 0)
    pump(RUN_S)
    second = (side.look(uid).get(what) or {}).get("time", 0)
    return round(second - first, 3)


def main():
    a, b = Side("a"), Side("b")
    a.other, b.other = b, a
    gate("both pages load", pump(25, lambda: a.ready and b.ready))
    for side in (a, b):
        side.run(FAKE)
    a.bridge.send("start", {"me": "a", "names": NAMES, "ice_servers": ICE, "video": False,
                            "peers": [], "offer_to": []})
    pump(3)
    a.bridge.send("add_peer", {"uid": "b", "offer": False})
    b.bridge.send("start", {"me": "b", "names": NAMES, "ice_servers": ICE, "video": False,
                            "peers": ["a"], "offer_to": ["a"]})
    joined = pump(40, lambda: a.peer().get("state") == "connected"
                  and b.peer().get("state") == "connected")
    gate("a voice call connects", joined,
         (a.peer().get("state"), b.peer().get("state"), a.state.get("error"), b.state.get("error")))
    gate("a's audio arrives at b",
         pump(20, lambda: (b.peer().get("bytes") or {}).get("audio_in", 0) > 2000),
         b.peer().get("bytes"))

    #  1 - the heart of it: arriving is not being heard
    voice = rendered(b, "a")
    gate("b RENDERS a's voice in a call with no camera", voice >= MOVED,
         "%.3f s of playback in %.1f s - %s" % (voice, RUN_S, json.dumps(b.look("a"))))
    look = b.look("a")
    gate("the picture carries no voice: the <video> is muted and audio-free",
         (look.get("video") or {}).get("muted") is True
         and "audio" not in ((look.get("video") or {}).get("tracks") or []),
         look.get("video"))
    gate("the voice has a sink of its own with the audio track in it",
         (look.get("audio") or {}).get("has") and
         ((look.get("audio") or {}).get("tracks") or []) == ["audio"], look.get("audio"))

    #  2 - a camera on: the picture plays, and the voice keeps being heard
    a.run("window.__cam = true;")
    a.bridge.send("camera", {"on": True})
    pump(6)
    gate("a's camera reaches b", b.peer().get("cam") is True, b.peer().get("cam"))
    with_cam = rendered(b, "a")
    picture = (b.look("a").get("video") or {}).get("ready")
    gate("with a camera the voice is still rendered", with_cam >= MOVED, with_cam)
    gate("and the picture plays too", picture == 4, picture)

    #  3 - the camera off again: this is where the old build went silent for good
    a.bridge.send("camera", {"on": False})
    pump(5)
    gate("a's camera off reaches b", b.peer().get("cam") is False, b.peer().get("cam"))
    after_cam = rendered(b, "a")
    gate("with the camera off again the voice is STILL rendered", after_cam >= MOVED,
         "%.3f s - %s" % (after_cam, json.dumps(b.look("a"))))

    #  4 - a shared screen and its end
    a.bridge.send("screen", {"on": True})
    shared = pump(15, lambda: b.peer().get("screen") is True)
    gate("a's shared screen reaches b", shared, b.peer().get("screen"))
    with_screen = rendered(b, "a")
    gate("while a screen is shared the voice is rendered", with_screen >= MOVED, with_screen)
    a.bridge.send("screen", {"on": False})
    pump(5)
    after_screen = rendered(b, "a")
    gate("and after the share stops", after_screen >= MOVED,
         "%.3f s - %s" % (after_screen, json.dumps(b.look("a"))))

    #  5 - nobody hears themselves
    mine = b.look("b")
    gate("the local tile plays no voice of its own",
         not ((mine.get("audio") or {}).get("tracks") or [])
         and (mine.get("video") or {}).get("muted") is not False, mine)

    #  6 - the speaking light still reads the remote track
    gate("the speaking light has its analyser on a's track",
         "a" in (b.look("a").get("levels") or []), b.look("a").get("levels"))
    b.run("tickLevels();")
    pump(1)

    #  7 - a peer who leaves takes their sink with them
    b.bridge.send("remove_peer", {"uid": "a"})
    pump(3)
    gone = b.look("a")
    gate("a peer who leaves takes their tile and sink with them",
         not gone.get("tile") and not (gone.get("audio") or {}).get("has"), gone)
    gate("and nothing is left playing",
         b.obj("document.querySelectorAll('#sinks audio').length") == 0,
         b.obj("document.querySelectorAll('#sinks audio').length"))

    a.bridge.send("end", {})
    b.bridge.send("end", {})
    pump(2)
    print("")
    print("%d of %d gates failed" % (GATES.count(False), len(GATES)))
    sys.stdout.flush()                       # os._exit below skips the buffers


try:
    main()
finally:
    os._exit(0)
