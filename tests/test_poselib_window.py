"""The Pose Library window, offscreen (2026-10-02): the cards of a temp library listed, searched,
sorted and narrowed by a folder; a pick filling the details; drops onto a character, the floor, a
folder and the window itself; the right button's rows; the blend gesture (middle drag, release,
Esc) and the slider; the save panel; the folder tree's rows; the hub card and the
workspaceControl half on a recording `cmds`. Every scene call goes to a FakeScene, so no Maya
scene is touched - the scene half is verify_poselib_apply.py's, the live window Task 10's.

The animation cards (2026-10-03): the type filter, + Save with Pose / Animation and a range, the
paste options of a picked clip (remembered, passed with every press), the details looping the
preview, the rows of an animation card; and the real `Scene`'s animation half - Save, Update,
Replace thumbnail and preview, the presses dispatched to `animapply` under a progress window -
over fake capture and apply modules and a temp library on the disk.

Spec: docs/superpowers/specs/2026-10-02-pose-library-design.md ("The window"),
      docs/superpowers/specs/2026-10-03-pose-library-animation-design.md ("The window")
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import maya_hubqt
    QT = maya_hubqt.qt()
except Exception:                                            # noqa: BLE001
    QT = None

import maya_hubstyle as hubstyle
import maya_poselib
from maya_poselib import animdata
from maya_poselib import look
from maya_poselib import store
from maya_poselib import window as pw
from tests.uifakes import FakeUiCmds

#  An animation card's frames file as the window hands it on (the press reads it, not the window)
#  - as `store.read_frames` answers it: `drive` always there, {} for a skeleton's clip
FRAMES = {"bones": ["root"], "world": [[0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]], "drive": {}}


def card_data(name, label="Manny [rig]", created="2026-10-02T18:00:00", kind="character",
              members=("hand_l",), regions=("Hand L",)):
    """A pose file as the window reads it (the bones themselves are the apply's business)."""
    data = {"format": store.FORMAT, "version": store.VERSION, "kind": kind, "name": name,
            "created": created, "author": "Eugene", "scene": "shot_010.ma", "frame": 12.0,
            "fps": "ntsc"}
    if kind == "character":
        data.update(character={"label": label, "key": "Manny_Rig", "model": "Manny",
                               "kind": "rig"},
                    bones={}, members=list(members), regions=list(regions), objects=[])
    else:
        data["objects"] = [{"name": "pCube1", "path": "|pCube1", "attrs": {"translateX": 1.0}}]
    return data


def write_jpg(path, colour="#3366aa", side=64):
    image = QT.QtGui.QImage(side, side, QT.QtGui.QImage.Format_RGB32)
    image.fill(QT.QtGui.QColor(colour))
    image.save(path, "JPG")
    return path


def anim_data(name, start=10.0, end=57.0, label="Manny [rig]", created="2026-10-03T12:00:00",
              preview=None, kind="character"):
    """An animation card's header as the window reads it - the clip's frames and its preview
    sheet's grid; the bones are the press's business."""
    data = {"format": store.ANIM_FORMAT, "version": store.VERSION, "kind": kind, "name": name,
            "created": created, "author": "Eugene", "scene": "walk_010.ma", "fps": "ntsc",
            "start": float(start), "end": float(end), "frames": int(round(end - start)) + 1,
            "key_times": [float(start), float(end)], "objects": []}
    if kind == "character":
        data.update(character={"label": label, "key": "Manny_Rig", "model": "Manny",
                               "kind": "rig"},
                    bones={}, members=["pelvis", "spine_01"], regions=["Pelvis", "Spine"],
                    rig_source=True)
    else:
        data["objects"] = [{"name": "pCube1", "path": "|pCube1",
                            "attrs": {"translateX": {"static": 1.0},
                                      "translateY": {"static": 2.0}}}]
    if preview is not None:
        data["preview"] = preview
    return data


def write_sheet(path, colours, size=32):
    """A preview sheet of one flat colour per cell, laid out as the saver lays its cells
    (`look.sheet_cell`); answers the header's `preview` dict for it."""
    columns = look.sheet_columns(len(colours))
    rows = -(-len(colours) // columns)
    image = QT.QtGui.QImage(columns * size, rows * size, QT.QtGui.QImage.Format_RGB32)
    image.fill(QT.QtGui.QColor("#000000"))
    painter = QT.QtGui.QPainter(image)
    for index, colour in enumerate(colours):
        x, y, w, h = look.sheet_cell(index, columns, size)
        painter.fillRect(x, y, w, h, QT.QtGui.QColor(colour))
    painter.end()
    image.save(path, "JPG", 95)
    return {"frames": len(colours), "columns": columns, "size": size, "step": 1}


class FakeScene(object):
    """What the window asks of Maya, recorded."""

    def __init__(self, root, trash):
        self.root = root
        self.trash_dir = trash
        self.log = []
        self.options = {}
        self.aim = dict(kind="character", root="|Manny_Rig1:root", label="Manny_Rig1",
                        text="onto Manny_Rig1")
        self.on_window = False
        self.regions = ["Hand L"]
        self.targets = ("onto Manny_Rig1", True)
        self.refusal = ""
        self.callback = None
        self.range = (10, 20)
        self.preview_text = "new thumbnail and preview"

    def calls(self, name):
        return [entry for entry in self.log if entry[0] == name]

    def scale(self):
        return 1.0

    def library(self):
        return self.root

    def set_library(self, root):
        self.log.append(("set_library", root))
        self.root = root

    def option(self, name, default=None):
        return self.options.get(name, default)

    def set_option(self, name, value):
        self.options[name] = value

    def selection_label(self):
        return "Manny [rig] (Manny_Rig1)"

    def selection_regions(self):
        self.log.append(("selection_regions",))
        return self.regions

    def apply_targets(self):
        self.reads = getattr(self, "reads", 0) + 1
        return self.targets

    def anim_range(self):
        self.log.append(("anim_range",))
        return self.range

    def save(self, name, folder, regions, snapshot_path, anim=None):
        self.log.append(("save", name, folder, regions, snapshot_path, anim))
        if anim is None:
            path = store.write(self.root, folder, name, card_data(name), thumbnail=snapshot_path)
        else:
            path = store.write(self.root, folder, name,
                               anim_data(name, anim["start"], anim["end"]),
                               thumbnail=snapshot_path, frames=FRAMES)
        return path, "saved " + name

    def snapshot(self, path):
        self.log.append(("snapshot", path))
        write_jpg(path, "#aa3322")
        return True, "thumbnail from modelPanel4"

    def update(self, path):
        self.log.append(("update", path))
        return True, "updated"

    def replace_preview(self, path):
        self.log.append(("replace_preview", path))
        return self.preview_text

    def apply(self, path, mirror, options=None):
        self.log.append(("apply", path, mirror, options))
        return True, "applied"

    def apply_onto(self, path, root, mirror, options=None):
        self.log.append(("apply_onto", path, root, mirror, options))
        return True, "applied onto " + root

    def drop_floor(self, path, point, mirror, options=None):
        self.log.append(("drop_floor", path, point, mirror, options))
        return True, "added on the floor"

    def select_objects(self, path, options=None):
        self.log.append(("select_objects", path, options))
        return True, "selected"

    def blend_start(self, path, mirror, options=None):
        self.log.append(("blend_start", path, mirror, options))
        return self.refusal

    def blend_set(self, alpha):
        self.log.append(("blend_set", alpha))

    def blend_finish(self):
        self.log.append(("blend_finish",))
        return "blended"

    def blend_cancel(self):
        self.log.append(("blend_cancel",))

    def snapshot_scene(self):
        self.log.append(("snapshot_scene",))
        return ["snap"]

    def target(self, gx, gy, snap):
        self.log.append(("target", snap))
        return self.aim

    def over_window(self, gx, gy):
        return self.on_window

    def say(self, text):
        self.log.append(("say", text))

    def watch(self, callback):
        self.callback = callback
        return [7, 8]

    def unwatch(self, jobs):
        self.log.append(("unwatch", list(jobs)))

    def trash(self):
        return self.trash_dir

    def reveal(self, path):
        self.log.append(("reveal", path))

    def open_path(self, path):
        self.log.append(("open_path", path))


# ------------------------------------------------------------------ pure

class Pure(unittest.TestCase):

    def test_the_blend_drag_is_200_logical_px_for_the_whole_pose(self):
        self.assertEqual(pw.blend_alpha(0), 0.0)
        self.assertAlmostEqual(pw.blend_alpha(100), 0.5)
        self.assertEqual(pw.blend_alpha(200), 1.0)
        self.assertEqual(pw.blend_alpha(800), 1.0)
        self.assertEqual(pw.blend_alpha(-50), 0.0)
        self.assertAlmostEqual(pw.blend_alpha(150, 1.5), 0.5)

    def test_a_folder_holds_its_subfolders_and_not_a_namesake(self):
        self.assertTrue(pw.in_folder("", ""))
        self.assertTrue(pw.in_folder("Hands/Left", ""))
        self.assertTrue(pw.in_folder("Hands", "Hands"))
        self.assertTrue(pw.in_folder("Hands/Left", "Hands"))
        self.assertTrue(pw.in_folder("hands/left", "Hands"))
        self.assertFalse(pw.in_folder("HandsOld", "Hands"))
        self.assertFalse(pw.in_folder("", "Hands"))

    def test_the_folder_text(self):
        self.assertEqual(pw.folder_text(""), "Library")
        self.assertEqual(pw.folder_text("Hands/Left"), "Library / Hands / Left")

    def test_the_region_chips_mean_the_selection_until_one_is_touched(self):
        self.assertIsNone(pw.regions_arg(["Hand L"], ["Hand L"]))
        self.assertIsNone(pw.regions_arg(None, ["Hand L"]))
        self.assertEqual(pw.regions_arg(["Hand L"], ["Head", "Hand L"]), ["Head", "Hand L"])
        self.assertEqual(pw.regions_arg(["Hand L"], []), [])

    def test_a_scene_target_becomes_the_caption_s_aim(self):
        aim = pw.scene_aim("character", "Manny [rig]",
                           dict(kind="character", root="|r", label="Manny_Rig1", text="x"))
        self.assertEqual(aim, {"kind": "character", "label": "Manny_Rig1", "root": "|r"})
        aim = pw.scene_aim("character", "Manny [rig]", dict(kind="floor", point=(120, 0, -36)))
        self.assertEqual(look.drop_caption("Fist", aim),
                         ("Fist \u00b7 a new Manny [rig] \u00b7 floor (120, -36)", True))
        aim = pw.scene_aim("character", "Manny [rig]",
                           dict(kind="none", text="no floor under the cursor"))
        self.assertEqual(look.drop_caption("Fist", aim), ("no floor under the cursor", False))
        aim = pw.scene_aim("objects", "objects", dict(kind="character", root="|r", label="x"))
        self.assertFalse(look.drop_caption("Cubes", aim)[1])

    def test_the_cards_shown_are_narrowed_then_sorted(self):
        cards = [store.Card("/l/A.pose", "Hands", "A", "2026-10-01", "", "Manny [rig]",
                            "character", 1, [], ""),
                 store.Card("/l/B.pose", "", "B", "2026-10-03", "", "Creep [rig]",
                            "character", 1, [], ""),
                 store.Card("/l/C.pose", "Hands/Left", "C", "2026-10-02", "", "Creep [rig]",
                            "character", 1, [], "")]
        names = lambda found: [card.name for card in found]          # noqa: E731
        self.assertEqual(names(pw.shown_cards(cards, "", "", "name")), ["A", "B", "C"])
        self.assertEqual(names(pw.shown_cards(cards, "Hands", "", "newest")), ["C", "A"])
        self.assertEqual(names(pw.shown_cards(cards, "", "creep", "name")), ["B", "C"])
        self.assertEqual(names(pw.shown_cards(cards, "", "", "character")), ["B", "C", "A"])
        self.assertEqual(names(pw.shown_cards(cards, "", "", "nonsense")), ["A", "B", "C"])

    def test_the_target_line_follows_the_apply_s_own_rule(self):
        self.assertEqual(pw.targets_text(["Manny_Rig1", "Creep_Rig"], True, []),
                         ("onto Manny_Rig1, Creep_Rig", True))
        self.assertEqual(pw.targets_text(["Manny_Rig1"], True, ["Manny_Rig1", "Creep_Rig"]),
                         ("onto Manny_Rig1", True))
        # a selection holding no character is refused, never sent to the only one
        text, ok = pw.targets_text([], True, ["Manny_Rig1"])
        self.assertFalse(ok)
        self.assertEqual(text, pw.NOT_A_CHARACTER)
        self.assertEqual(pw.targets_text([], False, ["Manny_Rig1"]),
                         ("onto Manny_Rig1 - the only character", True))
        self.assertEqual(pw.targets_text([], False, []), (pw.NO_CHARACTER, False))
        text, ok = pw.targets_text([], False, ["Manny_Rig1", "Creep_Rig"])
        self.assertFalse(ok)
        self.assertIn("2 characters in the scene (Manny_Rig1, Creep_Rig)", text)

    def test_the_ui_script_carries_the_plugin_path(self):
        text = pw.uiscript("C:\\!!!Work\\MayaScripts\\SkeldarAnim\\")
        self.assertIn('_p = "C:/!!!Work/MayaScripts/SkeldarAnim"', text)
        self.assertIn("sys.path.insert(0, _p)", text)
        self.assertIn("import maya_poselib.window as w", text)
        self.assertTrue(text.rstrip().endswith("w.build()"))
        self.assertNotIn("\\", text)
        compile(text, "uiScript", "exec")

    def test_importing_the_window_pulls_in_neither_maya_nor_qt(self):
        """The hub imports the package to build its card, and `maya_poselib.__getattr__`
        hands out this module: Qt and cmds come in when a window is built, never before."""
        script = (
            "import sys\n"
            "import maya_poselib.window\n"
            "import maya_poselib.cardgrid\n"
            "leaked = [m for m in sys.modules if m == 'maya.cmds' or m.startswith('maya.api')\n"
            "          or m.startswith('PySide') or m.startswith('shiboken')]\n"
            "print(';'.join(sorted(leaked)))\n"
        )
        plugin = os.path.dirname(os.path.dirname(os.path.abspath(pw.__file__)))
        result = subprocess.run([sys.executable, "-c", script], cwd=plugin,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "",
                         "importing the window leaked: " + result.stdout.strip())

    def test_the_names(self):
        self.assertEqual((pw.CONTROL, pw.LABEL, pw.ROOT),
                         ("skeldarPoseLibrary", "Pose Library", "skeldarPoseLibraryRoot"))
        self.assertEqual((pw.INITIAL_WIDTH, pw.INITIAL_HEIGHT), (1000, 640))
        self.assertEqual(pw.NOTE, "Poses and animations of bones - onto any rig or skeleton.")
        self.assertEqual(pw.EMPTY_LIBRARY,
                         "Nothing saved yet - select a character and press Save")

    def test_what_the_window_remembers(self):
        self.assertEqual((pw.TYPE_VAR, pw.SAVE_TYPE_VAR, pw.PASTE_VAR, pw.AT_CURRENT_VAR,
                          pw.CONNECT_VAR, pw.KEYS_VAR, pw.IN_PLACE_VAR),
                         ("skeldarPoseLibraryType", "skeldarPoseLibrarySaveType",
                          "skeldarPoseLibraryPaste", "skeldarPoseLibraryAtCurrent",
                          "skeldarPoseLibraryConnect", "skeldarPoseLibraryKeys",
                          "skeldarPoseLibraryInPlace"))

    # -- the animation cards (2026-10-03)

    def test_the_cards_shown_are_narrowed_by_type(self):
        cards = [store.Card("/l/A.pose", "", "A", "2026-10-01", "", "Manny [rig]",
                            "character", 1, [], ""),
                 store.Card("/l/W.anim", "", "W", "2026-10-02", "", "Manny [rig]",
                            "character", 1, [], "", "anim", 48, "", "ntsc", 0.0, 47.0)]
        names = lambda found: [card.name for card in found]          # noqa: E731
        self.assertEqual(names(pw.shown_cards(cards, "", "", "name")), ["A", "W"])
        self.assertEqual(names(pw.shown_cards(cards, "", "", "name", "all")), ["A", "W"])
        self.assertEqual(names(pw.shown_cards(cards, "", "", "name", "pose")), ["A"])
        self.assertEqual(names(pw.shown_cards(cards, "", "", "name", "anim")), ["W"])
        self.assertEqual(names(pw.shown_cards(cards, "", "", "name", "clips")), ["A", "W"])
        self.assertEqual(names(pw.shown_cards(cards, "", "manny", "name", "anim")), ["W"])

    def test_the_save_panel_says_how_many_frames_and_preview_cells(self):
        self.assertEqual(pw.save_frames_text(0, 47), "48 frames · 48 preview cells")
        self.assertEqual(pw.save_frames_text(5, 5), "1 frame · 1 preview cell")
        # a clip longer than look.PREVIEW_MAX keeps every step-th frame in its preview
        self.assertEqual(pw.save_frames_text(0, 99), "100 frames · 50 preview cells")
        self.assertEqual(pw.save_frames_text(10, 9), pw.NO_RANGE)

    def test_a_press_steps_once_per_pasted_frame(self):
        header = anim_data("Walk", 10, 57)
        self.assertEqual(pw.press_steps(header, None, 100.0), 48)
        self.assertEqual(pw.press_steps(header, {"start": 20, "end": 29}, 0.0), 10)
        self.assertEqual(pw.press_steps(header, animdata.Options(start=20.0, end=29.0), 0.0), 10)
        self.assertEqual(pw.press_steps(header, {"keys": "source"}, 0.0), 2)   # 10 and 57
        self.assertEqual(pw.press_steps(header, {"start": 80}, 0.0), 1)        # refused anyway
        # an objects card steps once per channel it pastes
        self.assertEqual(pw.press_steps(anim_data("Cubes", 0, 9, kind="objects"), None, 0.0), 2)

    def test_the_options_remembered(self):
        self.assertEqual(pw.remembered_options({}.get), animdata.Options())
        saved = {pw.PASTE_VAR: "merge", pw.AT_CURRENT_VAR: 0, pw.CONNECT_VAR: 1,
                 pw.KEYS_VAR: "source", pw.IN_PLACE_VAR: 1}
        self.assertEqual(pw.remembered_options(saved.get),
                         animdata.Options(mode="merge", at_current=False, connect=True,
                                          keys="source", in_place=True))
        # a value from another build is made valid, never handed on
        odd = {pw.PASTE_VAR: "paste_over", pw.KEYS_VAR: "some", pw.AT_CURRENT_VAR: "off"}
        self.assertEqual(pw.remembered_options(odd.get),
                         animdata.Options(at_current=False))


# ------------------------------------------------------------- the cmds half

class Workspace(unittest.TestCase):
    """show_window / build_panel on a recording cmds: the hub's pattern."""

    def setUp(self):
        self.cmds = FakeUiCmds()
        self.saved = pw._cmds, pw.build, pw._BUILT_HERE
        pw._cmds = lambda: self.cmds
        self.built = []
        pw.build = lambda: self.built.append("build")
        hubstyle.take_marks()

    def tearDown(self):
        pw._cmds, pw.build, pw._BUILT_HERE = self.saved
        hubstyle.take_marks()

    def test_the_first_show_creates_a_floating_control_running_the_ui_script(self):
        pw.show_window()
        made = self.cmds.workspace[pw.CONTROL]
        self.assertEqual(made["label"], "Pose Library")
        self.assertTrue(made["floating"])
        self.assertFalse(made["retain"])
        self.assertEqual((made["initialWidth"], made["initialHeight"]), (1000, 640))
        self.assertIn("w.build()", made["uiScript"])

    def test_a_standing_control_built_by_this_module_is_restored(self):
        self.cmds.workspace[pw.CONTROL] = {}
        pw._BUILT_HERE = True
        pw.show_window()
        self.assertEqual(self.built, [])
        self.assertTrue(self.cmds.workspace[pw.CONTROL]["edits"][-1]["restore"])

    def test_a_standing_control_an_older_module_built_is_rebuilt_in_place(self):
        self.cmds.workspace[pw.CONTROL] = {}
        pw._BUILT_HERE = False
        pw.show_window()
        self.assertEqual(self.built, ["build"])
        self.assertTrue(self.cmds.workspace[pw.CONTROL]["edits"][-1]["restore"])

    def test_the_hub_card_is_a_note_and_the_primary_open_button(self):
        pw.build_panel()
        marks = hubstyle.take_marks()
        roles = [(m.role, m.icon) for m in marks]
        self.assertEqual(roles[0], ("note", None))
        self.assertEqual(roles[1][0], "primary")
        import maya_hubicons
        self.assertEqual(roles[1][1], "books")
        self.assertIn("books", maya_hubicons.ICONS)
        self.assertFalse(hasattr(pw, "_open_icon"))      # the folder fallback is gone
        texts = [c for c in self.cmds.calls if c[0] == "text"]
        self.assertEqual(texts[0][2]["label"],
                         "Poses and animations of bones - onto any rig or skeleton.")
        buttons = [c for c in self.cmds.calls if c[0] == "button"]
        self.assertEqual(buttons[0][2]["label"], "Open Pose Library")


# ------------------------------------------------------------------ the window

@unittest.skipIf(QT is None, "no Qt")
class WindowCase(unittest.TestCase):
    """A window over a temp library holding three cards:

        Idle   (Library)      Creep [rig]  2026-10-03
        Fist   (Hands)        Manny [rig]  2026-10-01
        Wave   (Hands/Left)   Manny [rig]  2026-10-02
    """

    def setUp(self):
        self.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        self.tmp = tempfile.mkdtemp(prefix="skeldar_poselib_window_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = os.path.join(self.tmp, "poses").replace("\\", "/")
        os.makedirs(self.root)
        store.make_folder(self.root, "", "Hands")
        store.make_folder(self.root, "Hands", "Left")
        jpg = write_jpg(os.path.join(self.tmp, "t.jpg"))
        self.fist = store.write(self.root, "Hands", "Fist",
                                card_data("Fist", created="2026-10-01T10:00:00"), jpg)
        self.wave = store.write(self.root, "Hands/Left", "Wave",
                                card_data("Wave", created="2026-10-02T10:00:00"), jpg)
        self.idle = store.write(self.root, "", "Idle",
                                card_data("Idle", label="Creep [rig]",
                                          created="2026-10-03T10:00:00",
                                          members=("pelvis", "spine_01"),
                                          regions=("Pelvis", "Spine")))
        self.scene = FakeScene(self.root, os.path.join(self.tmp, "trash"))
        self.deferred = []
        saved = pw.defer
        pw.defer = self.deferred.append
        self.addCleanup(setattr, pw, "defer", saved)
        self.win = pw.make_window(self.scene)
        self.win.resize(1000, 640)
        self.win.move(3000, 3000)
        self.win.show()
        self.pump()
        self.addCleanup(self.win.deleteLater)

    def pump(self):
        for _ in range(3):
            self.app.processEvents()

    def names(self, win=None):
        return [os.path.basename(path)[:-len(store.card_suffix(path))]
                for path in (win or self.win).cards_shown()]

    def card_point(self, path, local=False):
        canvas = self.win.canvas
        index = self.win.cards_shown().index(path)
        x, y, w, h = canvas.rects()[index]
        point = QT.QtCore.QPoint(x + w // 2, y + h // 2)
        return point if local else canvas.mapToGlobal(point)

    def mouse(self, widget, kind, local, button, buttons=None):
        Qt = QT.QtCore.Qt
        types = {"press": QT.QtCore.QEvent.MouseButtonPress,
                 "move": QT.QtCore.QEvent.MouseMove,
                 "release": QT.QtCore.QEvent.MouseButtonRelease,
                 "double": QT.QtCore.QEvent.MouseButtonDblClick}
        buttons = button if buttons is None else buttons
        event = QT.QtGui.QMouseEvent(types[kind], QT.QtCore.QPointF(local),
                                     QT.QtCore.QPointF(widget.mapToGlobal(local)),
                                     button, buttons, Qt.NoModifier)
        {"press": widget.mousePressEvent, "move": widget.mouseMoveEvent,
         "release": widget.mouseReleaseEvent,
         "double": widget.mouseDoubleClickEvent}[kind](event)

    def escape(self, widget):
        widget.keyPressEvent(QT.QtGui.QKeyEvent(QT.QtCore.QEvent.KeyPress,
                                                QT.QtCore.Qt.Key_Escape,
                                                QT.QtCore.Qt.NoModifier))

    def tree_point(self, rel):
        tree = self.win.tree
        item = self.win.folder_item(rel)
        rect = tree.visualItemRect(item)
        return tree.viewport().mapToGlobal(rect.center())


class Listing(WindowCase):

    def test_the_window_lists_every_card(self):
        self.assertEqual(self.names(), ["Fist", "Idle", "Wave"])
        self.assertEqual(self.win.folder(), "")
        self.assertEqual(len(self.win.canvas.rects()), 3)

    def test_the_root_is_named_and_styled(self):
        self.assertEqual(self.win.objectName(), "skeldarPoseLibraryRoot")
        sheet = self.win.styleSheet()
        self.assertIn("#skeldarPoseLibraryRoot", sheet)
        self.assertIn(hubstyle.TOKENS["panel"], sheet)
        self.assertIn('QPushButton[skRole="primary"]', sheet)

    def test_the_folder_tree_draws_the_hubs_chevrons(self):
        # the live run (2026-10-03, poselib_window.png): with no ::branch rule, Maya's own style
        # drew the tree's open arrow as a white box beside the dark skin
        sheet = self.win.styleSheet()
        self.assertRegex(sheet, r"QTreeWidget#skeldarPoseFolders::branch, "
                                r"QTreeWidget#skeldarPoseFolders::branch:selected \{[^}]*"
                                r"transparent")
        self.assertIn("QTreeWidget#skeldarPoseFolders { show-decoration-selected: 0; }", sheet)
        self.assertRegex(sheet, r"#skeldarPoseFolders::branch:has-children:open \{[^}]*"
                                r"chevron-down")
        self.assertRegex(sheet, r"#skeldarPoseFolders::branch:has-children:closed \{[^}]*"
                                r"chevron-right")

    def test_the_header_shows_the_library_path(self):
        self.assertIn(self.root, self.win.path_label.text())

    def test_search_narrows_by_name_folder_and_character(self):
        self.win.search.setText("creep")
        self.assertEqual(self.names(), ["Idle"])
        self.win.search.setText("fist manny")
        self.assertEqual(self.names(), ["Fist"])
        self.win.search.setText("hands")
        self.assertEqual(self.names(), ["Fist", "Wave"])
        self.win.search.setText("")
        self.assertEqual(len(self.names()), 3)

    def test_sort_reorders_and_is_remembered(self):
        self.win.sort.setCurrentIndex(1)                     # Newest
        self.assertEqual(self.names(), ["Idle", "Wave", "Fist"])
        self.win.sort.setCurrentIndex(2)                     # Character
        self.assertEqual(self.names(), ["Idle", "Fist", "Wave"])
        self.assertEqual(self.scene.options[pw.SORT_VAR], "character")

    def test_a_folder_pick_narrows_to_it_and_below(self):
        self.win.set_folder("Hands")
        self.assertEqual(self.win.folder(), "Hands")
        self.assertEqual(self.names(), ["Fist", "Wave"])
        self.win.set_folder("Hands/Left")
        self.assertEqual(self.names(), ["Wave"])
        self.win.set_folder("")
        self.assertEqual(len(self.names()), 3)

    def test_clicking_a_folder_in_the_tree_picks_it(self):
        self.win.tree.setCurrentItem(self.win.folder_item("Hands/Left"))
        self.assertEqual(self.win.folder(), "Hands/Left")
        self.assertEqual(self.names(), ["Wave"])

    def test_the_card_size_slider_resizes_the_cards(self):
        self.win.size.setValue(look.CELL_MIN)
        small = self.win.canvas.rects()[0][2]
        self.win.size.setValue(look.CELL_MAX)
        self.assertGreater(self.win.canvas.rects()[0][2], small)
        self.assertEqual(self.scene.options[pw.SIZE_VAR], look.CELL_MAX)

    def test_the_cards_paint(self):
        canvas = self.win.canvas
        image = QT.QtGui.QImage(canvas.size(), QT.QtGui.QImage.Format_ARGB32)
        image.fill(0)
        canvas.render(image)
        before = image.copy()
        self.win.pick(self.fist)
        image.fill(0)
        canvas.render(image)
        self.assertNotEqual(before, image)

    def test_a_broken_card_is_named_not_raised(self):
        broken = os.path.join(self.root, "Bad.pose")
        os.makedirs(broken)
        with open(os.path.join(broken, "pose.json"), "w") as handle:
            handle.write("{not json")
        self.win.refresh()
        self.assertEqual(len(self.names()), 3)
        self.assertIn("could not be read", self.win.status.text())

    def test_the_library_menu_points_at_another_folder(self):
        other = os.path.join(self.tmp, "other").replace("\\", "/")
        os.makedirs(other)
        store.write(other, "", "Alone", card_data("Alone"))
        self.win.ask_directory = lambda title, start: other
        self.win.choose_library()
        self.assertIn(("set_library", other), self.scene.log)
        self.assertEqual(self.names(), ["Alone"])


class Details(WindowCase):

    def test_a_pick_shows_the_details(self):
        self.assertFalse(self.win.apply_button.isEnabled())
        self.assertTrue(self.win.pick(self.fist))
        self.assertEqual(self.win.name_label.text(), "Fist")
        info = self.win.info.text()
        self.assertIn("Manny [rig]", info)
        self.assertIn("Hand L", info)
        self.assertIn("Eugene", info)
        self.assertIn("Library / Hands", self.win.folder_label.text())
        self.assertTrue(self.win.apply_button.isEnabled())
        self.assertFalse(self.win.thumb.pixmap().isNull())

    def test_an_unknown_path_picks_nothing(self):
        self.assertFalse(self.win.pick(self.root + "/Nope.pose"))

    def test_apply_presses_the_scene_with_the_mirror(self):
        self.win.pick(self.fist)
        self.win.apply_button.click()
        self.win.mirror.setChecked(True)
        self.win.apply_button.click()
        self.assertEqual(self.scene.calls("apply"),
                         [("apply", self.fist, False, None), ("apply", self.fist, True, None)])
        self.assertEqual(self.win.status.text(), "applied")

    def test_apply_follows_the_selection(self):
        self.win.pick(self.fist)
        self.scene.targets = ("select a part of one of 2 characters", False)
        self.win.follow()
        self.assertFalse(self.win.apply_button.isEnabled())
        self.assertEqual(self.win.target_line.text(), "select a part of one of 2 characters")
        self.scene.targets = ("onto Manny_Rig1", True)
        self.scene.callback()                    # the SelectionChanged job: coalesced
        self.assertTrue(self.win.follow_timer.isActive())
        self.assertFalse(self.win.apply_button.isEnabled())
        deadline = time.time() + 2.0
        while not self.win.apply_button.isEnabled() and time.time() < deadline:
            self.app.processEvents()
            time.sleep(0.01)
        self.assertTrue(self.win.apply_button.isEnabled())
        self.assertEqual(self.win.target_line.text(), "onto Manny_Rig1")

    # the final review (2026-10-03): the selection was read again on every card click - 0.8 s
    # with a rig's 187 controls selected, 3 s with the save panel open, before a drag could start

    def test_a_card_click_reads_nothing_of_the_scene(self):
        self.win.pick(self.fist)
        reads = self.scene.reads
        self.win.pick(self.idle)
        self.win.pick(self.fist)
        self.assertEqual(self.scene.reads, reads)
        self.assertTrue(self.win.apply_button.isEnabled())
        self.assertEqual(self.win.target_line.text(), "onto Manny_Rig1")

    def test_with_no_card_picked_a_selection_change_reads_nothing(self):
        self.win.unpick()
        reads = getattr(self.scene, "reads", 0)
        self.win.follow()
        self.assertEqual(getattr(self.scene, "reads", 0), reads)
        self.assertFalse(self.win.apply_button.isEnabled())
        self.win.pick(self.fist)                  # read once, the first time it is needed
        self.assertEqual(self.scene.reads, reads + 1)

    def test_a_hidden_window_reads_when_it_shows_again(self):
        self.win.pick(self.fist)
        self.win.hide()
        self.scene.targets = ("select a part of one of 2 characters", False)
        self.scene.callback()
        self.assertFalse(self.win.follow_timer.isActive())
        self.assertTrue(self.win.apply_button.isEnabled())         # not read while hidden
        self.win.show()
        self.assertTrue(self.win.follow_timer.isActive())
        deadline = time.time() + 2.0
        while self.win.apply_button.isEnabled() and time.time() < deadline:
            self.app.processEvents()
            time.sleep(0.01)
        self.assertFalse(self.win.apply_button.isEnabled())
        self.assertEqual(self.win.target_line.text(), "select a part of one of 2 characters")

    def test_select_objects(self):
        self.win.pick(self.idle)
        self.win.select_button.click()
        self.assertEqual(self.scene.calls("select_objects"), [("select_objects", self.idle, None)])

    def test_a_scene_failure_lands_on_the_status_line(self):
        def boom(path, mirror):
            raise RuntimeError("the rig is referenced")
        self.scene.apply = boom
        self.win.pick(self.fist)
        self.win.apply_button.click()
        self.assertIn("the rig is referenced", self.win.status.text())

    def test_the_jobs_and_a_half_done_blend_die_with_the_window(self):
        win = pw.make_window(self.scene)
        win.blend_drag(self.fist, 50)
        del self.scene.log[:]
        win.deleteLater()
        QT.QtCore.QCoreApplication.sendPostedEvents(None, QT.QtCore.QEvent.DeferredDelete)
        self.assertEqual(self.scene.log, [("blend_cancel",), ("unwatch", [7, 8])])

    def test_an_objects_card_blends_too(self):
        cubes = store.write(self.root, "", "Cubes", card_data("Cubes", kind="objects"))
        self.win.refresh()
        self.win.pick(cubes)
        self.assertTrue(self.win.blend.isEnabled())
        self.assertTrue(self.win.apply_button.isEnabled())
        self.assertEqual(self.win.target_line.text(), pw.OBJECTS_TARGET)


class Drops(WindowCase):

    def test_over_a_character_the_card_goes_onto_it(self):
        self.win.drop_at(-2000, 40, self.fist)
        self.assertEqual(self.scene.calls("apply_onto"),
                         [("apply_onto", self.fist, "|Manny_Rig1:root", False, None)])

    def test_over_the_floor_the_source_is_added_one_idle_later(self):
        self.scene.aim = dict(kind="floor", point=(150.0, 0.0, -60.0))
        self.win.drop_at(-2000, 40, self.fist)
        self.assertEqual(self.scene.calls("drop_floor"), [])
        self.assertEqual(len(self.deferred), 1)
        self.deferred.pop()()
        self.assertEqual(self.scene.calls("drop_floor"),
                         [("drop_floor", self.fist, (150.0, 0.0, -60.0), False, None)])

    def test_inside_the_window_nothing(self):
        centre = self.win.details_page.mapToGlobal(self.win.details_page.rect().center())
        self.win.drop_at(centre.x(), centre.y(), self.fist)
        self.assertEqual([e for e in self.scene.log
                          if e[0] in ("target", "apply_onto", "drop_floor")], [])
        self.assertEqual(self.deferred, [])

    def test_over_the_hub_nothing(self):
        self.scene.on_window = True
        self.win.drop_at(-2000, 40, self.fist)
        self.assertEqual([e for e in self.scene.log if e[0] in ("target", "apply_onto")], [])

    def test_no_target_says_why(self):
        self.scene.aim = dict(kind="none", text="no floor under the cursor")
        self.win.drop_at(-2000, 40, self.fist)
        self.assertEqual(self.scene.calls("apply_onto") + self.scene.calls("drop_floor"), [])
        self.assertEqual(self.win.status.text(), "no floor under the cursor")

    def test_over_a_folder_the_card_moves_there(self):
        point = self.tree_point("Hands/Left")
        self.win.drop_at(point.x(), point.y(), self.idle)
        moved = self.root + "/Hands/Left/Idle.pose"
        self.assertTrue(os.path.isdir(moved))
        self.assertFalse(os.path.isdir(self.idle))
        self.assertIn(moved, self.win.cards_shown())
        self.assertEqual(self.scene.calls("target"), [])

    def test_a_real_drag_carries_a_ghost_naming_the_target(self):
        canvas = self.win.canvas
        start = self.card_point(self.fist, local=True)
        self.mouse(canvas, "press", start, QT.QtCore.Qt.LeftButton)
        self.assertIsNone(canvas._drag)
        far = start + QT.QtCore.QPoint(-4000, 40)
        self.mouse(canvas, "move", far, QT.QtCore.Qt.NoButton, QT.QtCore.Qt.LeftButton)
        self.assertIsNotNone(canvas._drag)
        self.assertEqual(canvas._drag["ghost"].text, "Fist \u00b7 onto Manny_Rig1")
        self.assertTrue(canvas._drag["ghost"].good)
        self.mouse(canvas, "release", far, QT.QtCore.Qt.LeftButton)
        self.assertIsNone(canvas._drag)
        self.assertEqual(self.scene.calls("snapshot_scene"), [("snapshot_scene",)])
        self.assertEqual([e[:3] for e in self.scene.calls("apply_onto")],
                         [("apply_onto", self.fist, "|Manny_Rig1:root")])

    def test_escape_and_the_right_button_cancel_a_drag(self):
        canvas = self.win.canvas
        start = self.card_point(self.fist, local=True)
        for cancel in ("escape", "right"):
            self.mouse(canvas, "press", start, QT.QtCore.Qt.LeftButton)
            self.mouse(canvas, "move", start + QT.QtCore.QPoint(80, 80),
                       QT.QtCore.Qt.NoButton, QT.QtCore.Qt.LeftButton)
            self.assertIsNotNone(canvas._drag)
            if cancel == "escape":
                self.escape(canvas)
            else:
                self.mouse(canvas, "press", start, QT.QtCore.Qt.RightButton)
            self.assertIsNone(canvas._drag)
        self.assertEqual(self.scene.calls("apply_onto"), [])

    def test_a_click_picks_and_a_double_click_applies(self):
        canvas = self.win.canvas
        point = self.card_point(self.wave, local=True)
        self.mouse(canvas, "press", point, QT.QtCore.Qt.LeftButton)
        self.mouse(canvas, "release", point, QT.QtCore.Qt.LeftButton)
        self.assertEqual(self.win.picked, self.wave)
        self.assertIsNone(canvas._drag)
        self.mouse(canvas, "double", point, QT.QtCore.Qt.LeftButton)
        self.assertEqual(self.scene.calls("apply"), [("apply", self.wave, False, None)])

    def test_an_objects_card_names_no_character(self):
        cubes = store.write(self.root, "", "Cubes", card_data("Cubes", kind="objects"))
        self.win.refresh()
        aim = self.win.aim(-2000, 40, cubes)
        self.assertEqual(aim["kind"], "none")
        self.win.drop_at(-2000, 40, cubes)
        self.assertEqual(self.scene.calls("apply_onto"), [])


class Menus(WindowCase):

    def test_the_right_button_rows_of_a_card(self):
        labels = [row[0] for row in self.win.context_actions(self.fist) if row]
        self.assertEqual(labels, ["Apply", "Apply mirrored", "Select objects", "Rename...",
                                  "Move to...", "Replace thumbnail", "Update from selection",
                                  "Show in Explorer", "Delete"])

    def test_nothing_off_every_card(self):
        self.assertEqual(self.win.context_actions(None), [])

    def test_apply_mirrored_from_the_menu(self):
        rows = dict(row for row in self.win.context_actions(self.fist) if row)
        rows["Apply mirrored"]()
        self.assertEqual(self.scene.calls("apply"), [("apply", self.fist, True, None)])

    def test_rename_from_the_menu(self):
        self.win.ask_text = lambda title, label, text: "Punch"
        dict(row for row in self.win.context_actions(self.fist) if row)["Rename..."]()
        renamed = self.root + "/Hands/Punch.pose"
        self.assertTrue(os.path.isdir(renamed))
        self.assertEqual(self.win.picked, renamed)

    def test_move_from_the_menu(self):
        self.win.ask_item = lambda title, label, items: "Hands/Left"
        dict(row for row in self.win.context_actions(self.fist) if row)["Move to..."]()
        self.assertTrue(os.path.isdir(self.root + "/Hands/Left/Fist.pose"))

    def test_delete_goes_to_the_trash_after_a_yes(self):
        rows = dict(row for row in self.win.context_actions(self.fist) if row)
        self.win.confirm = lambda title, text: False
        rows["Delete"]()
        self.assertTrue(os.path.isdir(self.fist))
        self.win.confirm = lambda title, text: True
        rows["Delete"]()
        self.assertFalse(os.path.isdir(self.fist))
        self.assertEqual(len(os.listdir(self.scene.trash_dir)), 1)
        self.assertNotIn(self.fist, self.win.cards_shown())

    def test_replace_thumbnail_blasts_into_the_card(self):
        before = os.path.getsize(self.idle + "/" + store.THUMB_FILE) \
            if os.path.isfile(self.idle + "/" + store.THUMB_FILE) else None
        self.assertIsNone(before)
        dict(row for row in self.win.context_actions(self.idle) if row)["Replace thumbnail"]()
        self.assertTrue(os.path.isfile(self.idle + "/" + store.THUMB_FILE))

    def test_update_from_selection_asks_first(self):
        rows = dict(row for row in self.win.context_actions(self.fist) if row)
        self.win.confirm = lambda title, text: True
        rows["Update from selection"]()
        self.assertEqual(self.scene.calls("update"), [("update", self.fist)])

    def test_the_folder_rows(self):
        labels = [row[0] for row in self.win.folder_actions("Hands") if row]
        self.assertEqual(labels, ["New folder...", "Rename...", "Delete", "Show in Explorer"])
        rows = [row for row in self.win.folder_actions("") if row]
        self.assertEqual([label for label, fn in rows if fn is None], ["Rename...", "Delete"])

    def test_a_new_folder_is_made_and_picked(self):
        self.win.ask_text = lambda title, label, text: "Idles"
        dict(row for row in self.win.folder_actions("Hands") if row)["New folder..."]()
        self.assertTrue(os.path.isdir(self.root + "/Hands/Idles"))
        self.assertEqual(self.win.folder(), "Hands/Idles")
        self.assertIsNotNone(self.win.folder_item("Hands/Idles"))

    def test_a_renamed_folder_keeps_the_pick_inside_it(self):
        self.win.set_folder("Hands/Left")
        self.win.pick(self.wave)
        self.win.ask_text = lambda title, label, text: "Right"
        dict(row for row in self.win.folder_actions("Hands/Left") if row)["Rename..."]()
        self.assertEqual(self.win.folder(), "Hands/Right")
        self.assertEqual(self.names(), ["Wave"])
        self.assertEqual(self.win.picked, self.root + "/Hands/Right/Wave.pose")
        self.assertEqual(self.win.name_label.text(), "Wave")

    def test_a_card_gone_from_the_disk_is_said_not_raised(self):
        rows = dict(row for row in self.win.context_actions(self.fist) if row)
        shutil.rmtree(self.fist)
        self.win.refresh()
        rows["Delete"]()
        self.assertEqual(self.win.status.text(), pw.GONE)

    def test_a_deleted_folder_goes_to_the_trash(self):
        self.win.confirm = lambda title, text: True
        dict(row for row in self.win.folder_actions("Hands") if row)["Delete"]()
        self.assertFalse(os.path.isdir(self.root + "/Hands"))
        self.assertEqual(self.names(), ["Idle"])


class Blend(WindowCase):

    def middle(self, kind, local, buttons=None):
        Qt = QT.QtCore.Qt
        button = Qt.NoButton if kind == "move" else Qt.MiddleButton
        self.mouse(self.win.canvas, kind, local, button,
                   Qt.MiddleButton if buttons is None else buttons)

    def test_a_middle_drag_blends_live_and_keys_on_release(self):
        start = self.card_point(self.fist, local=True)
        self.middle("press", start)
        self.assertEqual(self.scene.calls("blend_start"), [])
        self.middle("move", start + QT.QtCore.QPoint(100, 0))
        self.middle("move", start + QT.QtCore.QPoint(300, 0))
        self.assertEqual(self.scene.calls("blend_start"),
                         [("blend_start", self.fist, False, None)])
        self.assertEqual(self.scene.calls("blend_set"), [("blend_set", 0.5), ("blend_set", 1.0)])
        self.middle("release", start + QT.QtCore.QPoint(300, 0), QT.QtCore.Qt.NoButton)
        self.assertEqual(self.scene.calls("blend_finish"), [("blend_finish",)])
        self.assertEqual(self.win.status.text(), "blended")

    def test_blend_drag_is_the_gesture_without_a_mouse(self):
        self.assertEqual(self.win.blend_drag(self.fist, 50), 0.25)
        self.assertEqual(self.win.blend_drag(self.fist, 150), 0.75)
        self.assertEqual(len(self.scene.calls("blend_start")), 1)
        self.win.blend_release()
        self.assertEqual(self.scene.calls("blend_finish"), [("blend_finish",)])

    def test_escape_puts_every_value_back(self):
        start = self.card_point(self.fist, local=True)
        self.middle("press", start)
        self.middle("move", start + QT.QtCore.QPoint(60, 0))
        self.escape(self.win.canvas)
        self.assertEqual(self.scene.calls("blend_cancel"), [("blend_cancel",)])
        self.middle("move", start + QT.QtCore.QPoint(90, 0))
        self.middle("release", start, QT.QtCore.Qt.NoButton)
        self.assertEqual(self.scene.calls("blend_finish"), [])
        self.assertEqual(len(self.scene.calls("blend_start")), 1)

    # the final review (2026-10-03): a release lost to Alt+Tab or a modal dialog left the session
    # open - every press on the grid swallowed, the keyboard grabbed, the previews unrecorded

    def test_a_lost_middle_release_cancels_the_blend_and_says_so(self):
        start = self.card_point(self.fist, local=True)
        self.middle("press", start)
        self.middle("move", start + QT.QtCore.QPoint(100, 0))
        self.assertTrue(self.win.blending())
        self.middle("move", start + QT.QtCore.QPoint(140, 0), QT.QtCore.Qt.NoButton)
        self.assertEqual(self.scene.calls("blend_cancel"), [("blend_cancel",)])
        self.assertEqual(self.scene.calls("blend_finish"), [])
        self.assertFalse(self.win.blending())
        self.assertIsNone(QT.QtWidgets.QWidget.keyboardGrabber())
        self.assertEqual(self.win.status.text(), pw.cardgrid.LOST_BLEND)
        # and the grid takes presses again: a click picks
        self.mouse(self.win.canvas, "press", self.card_point(self.idle, local=True),
                   QT.QtCore.Qt.LeftButton)
        self.assertEqual(self.win.picked, self.idle)

    def test_a_lost_left_release_ends_the_drag(self):
        canvas = self.win.canvas
        start = self.card_point(self.fist, local=True)
        self.mouse(canvas, "press", start, QT.QtCore.Qt.LeftButton)
        far = start + QT.QtCore.QPoint(-4000, 40)
        self.mouse(canvas, "move", far, QT.QtCore.Qt.NoButton, QT.QtCore.Qt.LeftButton)
        ghost = canvas._drag["ghost"]
        self.mouse(canvas, "move", far + QT.QtCore.QPoint(5, 0), QT.QtCore.Qt.NoButton,
                   QT.QtCore.Qt.NoButton)
        self.assertIsNone(canvas._drag)
        self.assertFalse(ghost.isVisible())
        self.assertEqual(self.scene.calls("apply_onto"), [])
        self.assertIsNone(QT.QtWidgets.QWidget.keyboardGrabber())
        self.assertEqual(self.win.status.text(), pw.cardgrid.LOST_DRAG)

    def test_a_lost_slider_release_cancels_and_keys_nothing(self):
        self.win.pick(self.fist)
        slider = self.win.blend
        self.slider_mouse("press", slider.width() * 0.5)
        self.assertTrue(self.win.blending())
        self.slider_mouse("move", slider.width() * 0.7, held=QT.QtCore.Qt.NoButton)
        self.assertEqual(self.scene.calls("blend_cancel"), [("blend_cancel",)])
        self.assertEqual(self.scene.calls("blend_finish"), [])
        self.assertFalse(slider.isSliderDown())
        self.assertEqual(slider.value(), 0)
        self.assertFalse(self.win.blending())
        self.assertEqual(self.win.status.text(), pw.cardgrid.LOST_BLEND)

    def test_losing_the_focus_mid_blend_cancels_it(self):
        self.win.blend_drag(self.fist, 40)
        self.assertTrue(self.win.blending())
        self.win.isActiveWindow = lambda: False                 # Alt+Tab
        QT.QtWidgets.QApplication.sendEvent(self.win,
                                            QT.QtCore.QEvent(QT.QtCore.QEvent.ActivationChange))
        self.assertEqual(self.scene.calls("blend_cancel"), [("blend_cancel",)])
        self.assertFalse(self.win.blending())
        self.assertEqual(self.win.status.text(), pw.cardgrid.LOST_BLEND)

    def test_losing_the_focus_with_nothing_going_on_does_nothing(self):
        self.win.isActiveWindow = lambda: False
        QT.QtWidgets.QApplication.sendEvent(self.win,
                                            QT.QtCore.QEvent(QT.QtCore.QEvent.ActivationChange))
        self.assertEqual(self.scene.calls("blend_cancel"), [])

    def test_escape_on_the_window_cancels_too(self):
        self.win.blend_drag(self.fist, 40)
        self.escape(self.win)
        self.assertEqual(self.scene.calls("blend_cancel"), [("blend_cancel",)])

    def test_a_refused_blend_sets_nothing(self):
        self.scene.refusal = "Manny_Rig1's layer AnimLayer1 is locked"
        self.assertIsNone(self.win.blend_drag(self.fist, 100))
        self.assertEqual(self.scene.calls("blend_set"), [])
        self.assertEqual(self.win.status.text(), "Manny_Rig1's layer AnimLayer1 is locked")

    def test_a_middle_click_is_no_blend(self):
        start = self.card_point(self.fist, local=True)
        self.middle("press", start)
        self.middle("release", start, QT.QtCore.Qt.NoButton)
        self.assertEqual(self.scene.calls("blend_start") + self.scene.calls("blend_finish"), [])

    def test_the_slider_previews_while_dragged_and_keys_on_release(self):
        self.win.pick(self.fist)
        slider = self.win.blend
        slider.setSliderDown(True)                   # sliderPressed
        slider.setSliderPosition(40)                 # sliderMoved, valueChanged
        slider.setSliderPosition(70)
        slider.setSliderDown(False)                  # sliderReleased
        self.assertEqual(self.scene.calls("blend_start"),
                         [("blend_start", self.fist, False, None)])
        self.assertEqual(self.scene.calls("blend_set"), [("blend_set", 0.4), ("blend_set", 0.7)])
        self.assertEqual(self.scene.calls("blend_finish"), [("blend_finish",)])
        self.assertEqual(slider.value(), 0)

    # -- the slider under a real mouse. Review finding 1 (2026-10-03): every value change that
    #    was not a handle drag keyed a blend at once - a wheel notch (3 notches: 3 blends of 3 %)
    #    and the groove's auto-repeat (a press held 1.5 s: 17 blends of 10 %, each keyed) - with
    #    no preview and no release. These go through QApplication.sendEvent, as the mouse does.

    def blend_calls(self):
        return [entry for entry in self.scene.log if entry[0].startswith("blend")]

    def slider_mouse(self, kind, x, button=None, held=None):
        """A mouse event on the Blend slider at local x (its vertical middle). `button` is the
        one pressed or released (left by default); `held` what is down after the event."""
        Qt = QT.QtCore.Qt
        slider = self.win.blend
        button = Qt.LeftButton if button is None else button
        if held is None:
            held = Qt.NoButton if kind == "release" else button
        types = {"press": QT.QtCore.QEvent.MouseButtonPress,
                 "move": QT.QtCore.QEvent.MouseMove,
                 "release": QT.QtCore.QEvent.MouseButtonRelease}
        local = QT.QtCore.QPoint(int(x), slider.height() // 2)
        event = QT.QtGui.QMouseEvent(types[kind], QT.QtCore.QPointF(local),
                                     QT.QtCore.QPointF(slider.mapToGlobal(local)),
                                     Qt.NoButton if kind == "move" else button, held,
                                     Qt.NoModifier)
        QT.QtWidgets.QApplication.sendEvent(slider, event)
        return event

    def wheel(self, widget, dy):
        """One wheel notch over `widget`, delivered as Qt delivers one from the mouse: to the
        widget, then up its parents while it is ignored. The walk is done here because Qt 6 does
        not propagate a wheel event sent from Python (it is not spontaneous; QApplication::notify
        «Synthesized events shouldn't propagate») - measured offscreen (task8/probe_wheel.py): an
        ignoring child in a QScrollArea left the bar at 635, the walk moved it to 575. The widget
        that took it, or None."""
        Qt = QT.QtCore.Qt
        centre = widget.rect().center()
        spot = widget.mapToGlobal(centre)
        target = widget
        while target is not None:
            event = QT.QtGui.QWheelEvent(QT.QtCore.QPointF(target.mapFromGlobal(spot)),
                                         QT.QtCore.QPointF(spot), QT.QtCore.QPoint(),
                                         QT.QtCore.QPoint(0, dy), Qt.NoButton, Qt.NoModifier,
                                         Qt.NoScrollPhase, False)
            QT.QtWidgets.QApplication.sendEvent(target, event)
            if event.isAccepted():
                return target
            target = None if target.isWindow() else target.parentWidget()
        return None

    def test_the_wheel_over_the_slider_scrolls_the_panel_and_keys_nothing(self):
        self.win.pick(self.fist)
        self.win.resize(1000, 300)                   # a short dock: the side panel scrolls
        self.pump()
        side = self.win.findChild(QT.QtWidgets.QScrollArea, "skeldarPoseSideScroll")
        bar = side.verticalScrollBar()
        self.assertGreater(bar.maximum(), 0)
        bar.setValue(bar.maximum())
        slider = self.win.blend
        seen = [bar.value()]
        for dy in (120, 120, 120, -120, -120, -120):  # three notches up, three down
            taker = self.wheel(slider, dy)
            self.assertIsNot(taker, slider)
            seen.append(bar.value())
        self.assertLess(seen[3], seen[0])            # the panel scrolled up ...
        self.assertGreater(seen[6], seen[3])         # ... and down again
        self.assertEqual(slider.value(), 0)
        self.assertEqual(self.blend_calls(), [])

    def test_a_click_on_the_groove_previews_there_and_keys_once_on_the_release(self):
        self.win.pick(self.fist)
        slider = self.win.blend
        x = slider.width() * 0.4
        self.slider_mouse("press", x)
        value = slider.sliderPosition()
        self.assertTrue(20 <= value <= 45, value)    # the handle jumped under the press ...
        self.assertLessEqual(abs(slider.handle_rect().center().x() - int(x)), 1)  # centred
        self.assertTrue(slider.isSliderDown())
        self.assertEqual(self.blend_calls(), [("blend_start", self.fist, False, None),
                                              ("blend_set", value / 100.0)])
        self.slider_mouse("release", x)
        self.assertEqual(self.blend_calls()[2:], [("blend_finish",)])
        self.assertFalse(slider.isSliderDown())
        self.assertEqual(slider.value(), 0)
        self.assertEqual(self.win.status.text(), "blended")

    def test_a_press_held_on_the_groove_keys_once_and_only_after_the_release(self):
        self.win.pick(self.fist)
        slider = self.win.blend
        x = slider.width() * 0.85
        self.slider_mouse("press", x)
        value = slider.sliderPosition()
        end = time.time() + 0.7          # past Qt's 500 ms auto-repeat delay, into its repeats
        while time.time() < end:
            self.app.processEvents()
            time.sleep(0.01)
        self.assertEqual(slider.sliderPosition(), value)
        self.assertEqual(self.blend_calls(), [("blend_start", self.fist, False, None),
                                              ("blend_set", value / 100.0)])
        self.slider_mouse("release", x)
        self.assertEqual(self.blend_calls()[2:], [("blend_finish",)])
        self.assertEqual(slider.value(), 0)

    def test_a_press_on_the_groove_starts_a_drag(self):
        self.win.pick(self.fist)
        slider = self.win.blend
        width = slider.width()
        self.slider_mouse("press", width * 0.3)
        self.slider_mouse("move", width * 0.6, held=QT.QtCore.Qt.LeftButton)
        self.slider_mouse("move", width * 0.9, held=QT.QtCore.Qt.LeftButton)
        last = slider.sliderPosition()
        self.assertEqual(self.scene.calls("blend_finish"), [])
        self.slider_mouse("release", width * 0.9)
        alphas = [entry[1] for entry in self.scene.calls("blend_set")]
        self.assertEqual(len(alphas), 3)
        self.assertEqual(alphas, sorted(alphas))
        self.assertEqual(alphas[-1], last / 100.0)
        self.assertEqual(len(self.scene.calls("blend_start")), 1)
        self.assertEqual(self.blend_calls()[-1], ("blend_finish",))
        self.assertEqual(len(self.scene.calls("blend_finish")), 1)

    def test_a_drag_of_the_handle_previews_and_keys_on_release(self):
        self.win.pick(self.fist)
        slider = self.win.blend
        self.slider_mouse("press", 2)                # the handle stands at 0, at the left end
        self.assertTrue(slider.isSliderDown())
        self.slider_mouse("move", slider.width() * 0.6, held=QT.QtCore.Qt.LeftButton)
        moved = slider.sliderPosition()
        self.assertGreater(moved, 0)
        self.assertEqual(self.scene.calls("blend_finish"), [])
        self.slider_mouse("release", slider.width() * 0.6)
        self.assertEqual(self.blend_calls(), [("blend_start", self.fist, False, None),
                                              ("blend_set", moved / 100.0), ("blend_finish",)])
        self.assertEqual(slider.value(), 0)

    def test_escape_mid_slider_drag_puts_every_value_back(self):
        self.win.pick(self.fist)
        slider = self.win.blend
        self.slider_mouse("press", slider.width() * 0.5)
        self.escape(self.win)
        self.slider_mouse("move", slider.width() * 0.8, held=QT.QtCore.Qt.LeftButton)
        self.slider_mouse("release", slider.width() * 0.8)
        self.assertEqual(self.scene.calls("blend_cancel"), [("blend_cancel",)])
        self.assertEqual(self.scene.calls("blend_finish"), [])
        self.assertEqual(slider.value(), 0)

    def test_the_middle_and_right_buttons_on_the_slider_do_nothing(self):
        Qt = QT.QtCore.Qt
        self.win.pick(self.fist)
        slider = self.win.blend
        for button in (Qt.MiddleButton, Qt.RightButton):
            self.slider_mouse("press", slider.width() * 0.5, button=button)
            self.slider_mouse("release", slider.width() * 0.5, button=button)
        self.assertEqual(self.blend_calls(), [])
        self.assertEqual(slider.value(), 0)

    def test_keys_never_move_the_slider(self):
        Qt = QT.QtCore.Qt
        self.win.pick(self.fist)
        slider = self.win.blend
        for key in (Qt.Key_Right, Qt.Key_PageUp, Qt.Key_End, Qt.Key_Up):
            QT.QtWidgets.QApplication.sendEvent(
                slider, QT.QtGui.QKeyEvent(QT.QtCore.QEvent.KeyPress, key, Qt.NoModifier))
        self.assertEqual(slider.value(), 0)
        self.assertEqual(self.blend_calls(), [])

    def test_a_handle_a_style_jumped_before_the_press_is_previewed_at_once(self):
        # QSlider's absolute-set branch (a style giving the left button SH_Slider_AbsoluteSet-
        # Buttons) moves the handle BEFORE it downs the slider: the session must preview there
        self.win.pick(self.fist)
        slider = self.win.blend
        slider.setSliderPosition(20)                 # up: the label only
        self.assertEqual(self.blend_calls(), [])
        slider.setSliderDown(True)                   # sliderPressed
        self.assertEqual(self.blend_calls(), [("blend_start", self.fist, False, None),
                                              ("blend_set", 0.2)])
        slider.setSliderDown(False)                  # sliderReleased
        self.assertEqual(self.blend_calls()[-1], ("blend_finish",))
        self.assertEqual(slider.value(), 0)

    def test_a_value_set_by_code_keys_nothing(self):
        self.win.pick(self.fist)
        self.win.blend.setValue(30)
        self.assertEqual(self.blend_calls(), [])


class Save(WindowCase):

    def open(self):
        self.win.set_folder("Hands")
        self.win.save_button.click()

    def test_save_opens_the_panel_with_a_free_name_and_the_selection(self):
        store.write(self.root, "Hands", "Pose", card_data("Pose"))
        self.win.refresh()
        self.open()
        self.assertTrue(self.win.saving())
        self.assertEqual(self.win.save_name.text(), "Pose 2")
        self.assertIn("Library / Hands", self.win.save_folder.text())
        self.assertEqual(self.win.save_character.text(), "Manny [rig] (Manny_Rig1)")
        lit = [region for region, chip in self.win.chips.items() if chip.isChecked()]
        self.assertEqual(lit, ["Hand L"])
        self.assertEqual(len(self.scene.calls("snapshot")), 1)
        self.assertFalse(self.win.save_thumb.pixmap().isNull())

    def test_save_writes_the_card_and_picks_it(self):
        self.open()
        self.win.save_name.setText("Grip")
        self.win.save_confirm.click()
        (_name, name, folder, regions, snap, anim), = self.scene.calls("save")
        self.assertEqual((name, folder, regions, anim), ("Grip", "Hands", None, None))
        self.assertTrue(snap and snap.endswith(".jpg"))
        path = self.root + "/Hands/Grip.pose"
        self.assertTrue(os.path.isfile(path + "/" + store.THUMB_FILE))
        self.assertFalse(self.win.saving())
        self.assertEqual(self.win.picked, path)
        self.assertIn(path, self.win.cards_shown())

    def test_a_chip_turned_on_brings_its_region(self):
        self.open()
        self.win.chips["Head"].click()
        self.win.save_confirm.click()
        self.assertEqual(self.scene.calls("save")[0][3], ["Head", "Hand L"])

    def test_an_objects_selection_has_no_chips(self):
        self.scene.regions = None
        self.open()
        self.assertFalse(any(chip.isEnabled() for chip in self.win.chips.values()))
        self.win.save_confirm.click()
        self.assertIsNone(self.scene.calls("save")[0][3])

    def test_snapshot_takes_it_again(self):
        self.open()
        self.win.snapshot_button.click()
        self.assertEqual(len(self.scene.calls("snapshot")), 2)

    def test_cancel_writes_nothing(self):
        self.open()
        self.win.save_cancel.click()
        self.assertFalse(self.win.saving())
        self.assertEqual(self.scene.calls("save"), [])

    def test_a_refused_save_keeps_the_panel_and_says_why(self):
        refusal = "pick one character for a pose"
        self.scene.save = lambda name, folder, regions, snap: (None, refusal)
        self.open()
        self.win.save_confirm.click()
        self.assertTrue(self.win.saving())
        self.assertEqual(self.win.status.text(), "pick one character for a pose")


# ------------------------------------------------------------------ the animation cards

class AnimCase(WindowCase):
    """The library above plus an animation card:

        Walk   (Library)      Manny [rig]  48 frames 10-57, a green still and a preview sheet
                                           of two cells - red, then blue
    """

    RED, BLUE, GREEN = "#d02020", "#2040d0", "#20a040"

    def setUp(self):
        WindowCase.setUp(self)
        sheet = os.path.join(self.tmp, "sheet.jpg")
        info = write_sheet(sheet, (self.RED, self.BLUE))
        still = write_jpg(os.path.join(self.tmp, "still.jpg"), self.GREEN)
        self.walk = store.write(self.root, "", "Walk", anim_data("Walk", preview=info), still,
                                frames=FRAMES, preview=sheet)
        self.win.refresh()

    def rows(self, path):
        return dict(row for row in self.win.context_actions(path) if row)

    def window(self):
        """A second window over the same scene - what the next session opens."""
        win = pw.make_window(self.scene)
        self.addCleanup(win.deleteLater)
        return win


class TypeFilter(AnimCase):

    def test_the_type_filter_shows_one_type_and_is_remembered(self):
        self.assertEqual(self.names(), ["Fist", "Idle", "Walk", "Wave"])
        types = self.win.type_filter
        self.assertEqual(types.objectName(), "skeldarPoseType")
        self.assertEqual([types.itemText(i) for i in range(types.count())],
                         ["All", "Poses", "Animations"])
        types.setCurrentIndex(2)
        self.assertEqual(self.names(), ["Walk"])
        self.assertEqual(self.scene.options[pw.TYPE_VAR], "anim")
        types.setCurrentIndex(1)
        self.assertEqual(self.names(), ["Fist", "Idle", "Wave"])
        self.assertEqual(self.scene.options[pw.TYPE_VAR], "pose")
        win = self.window()
        self.assertEqual(win.type_filter.currentData(), "pose")
        self.assertEqual(self.names(win), ["Fist", "Idle", "Wave"])

    def test_a_type_with_nothing_says_no_card_matches(self):
        shutil.rmtree(self.walk)
        self.win.refresh()
        self.win.type_filter.setCurrentIndex(2)
        self.assertEqual(self.names(), [])
        self.assertEqual(self.win.canvas.empty_text, pw.EMPTY_SEARCH)

    def test_an_unknown_remembered_type_is_all(self):
        self.scene.options[pw.TYPE_VAR] = "clips"
        self.assertEqual(self.window().type_filter.currentData(), "all")

    def test_an_empty_library_says_save(self):
        for path in (self.fist, self.wave, self.idle, self.walk):
            shutil.rmtree(path)
        self.win.refresh()
        self.assertEqual(self.win.canvas.empty_text,
                         "Nothing saved yet - select a character and press Save")


class SaveAnimation(AnimCase):

    def open(self):
        self.win.save_button.click()

    def test_save_opens_the_panel_with_pose_lit(self):
        self.assertEqual(self.win.save_button.text(), "Save")
        self.open()
        self.assertTrue(self.win.saving())
        self.assertEqual(self.win.save_types["pose"].objectName(), "skeldarPoseSaveType_pose")
        self.assertEqual(self.win.save_types["anim"].objectName(), "skeldarPoseSaveType_anim")
        self.assertTrue(self.win.save_types["pose"].isChecked())
        self.assertFalse(self.win.save_types["anim"].isChecked())
        self.assertFalse(self.win.save_start.isVisible())
        self.assertFalse(self.win.save_frames.isVisible())
        self.assertEqual(self.win.save_name.text(), "Pose")
        self.assertEqual(self.scene.calls("anim_range"), [])

    def test_lighting_animation_shows_the_range_the_scene_reads(self):
        self.open()
        self.win.save_types["anim"].click()
        self.assertTrue(self.win.save_types["anim"].isChecked())
        self.assertFalse(self.win.save_types["pose"].isChecked())
        self.assertTrue(self.win.save_start.isVisible())
        self.assertEqual(self.win.save_start.objectName(), "skeldarPoseSaveStart")
        self.assertEqual(self.win.save_end.objectName(), "skeldarPoseSaveEnd")
        self.assertEqual((self.win.save_start.value(), self.win.save_end.value()), (10, 20))
        self.assertEqual(self.win.save_frames.objectName(), "skeldarPoseSaveFrames")
        self.assertEqual(self.win.save_frames.text(), "11 frames · 11 preview cells")
        self.assertEqual(self.win.save_name.text(), "Anim")
        self.assertEqual(self.scene.options[pw.SAVE_TYPE_VAR], "anim")

    def test_save_hands_the_scene_the_range(self):
        self.open()
        self.win.save_types["anim"].click()
        self.win.save_confirm.click()
        (_save, name, folder, regions, snap, anim), = self.scene.calls("save")
        self.assertEqual((name, folder, regions, anim),
                         ("Anim", "", None, {"start": 10, "end": 20}))
        self.assertTrue(snap and snap.endswith(".jpg"))
        path = self.root + "/Anim.anim"
        self.assertFalse(self.win.saving())
        self.assertEqual(self.win.picked, path)
        self.assertIn(path, self.win.cards_shown())

    def test_a_typed_range_is_said_and_saved(self):
        self.open()
        self.win.save_types["anim"].click()
        self.win.save_end.setValue(109)
        self.assertEqual(self.win.save_frames.text(), "100 frames · 50 preview cells")
        self.win.save_start.setValue(110)
        self.assertEqual(self.win.save_frames.text(), pw.NO_RANGE)
        self.win.save_start.setValue(5)
        self.win.save_confirm.click()
        self.assertEqual(self.scene.calls("save")[0][5], {"start": 5, "end": 109})

    def test_the_type_is_remembered_and_a_typed_name_kept(self):
        self.open()
        self.win.save_name.setText("Run")
        self.win.save_types["anim"].click()
        self.assertEqual(self.win.save_name.text(), "Run")          # typed: the animator's
        self.win.save_cancel.click()
        self.open()
        self.assertTrue(self.win.save_types["anim"].isChecked())
        self.assertTrue(self.win.save_start.isVisible())
        self.assertEqual(self.win.save_name.text(), "Anim")
        self.win.save_types["pose"].click()
        self.assertEqual(self.win.save_name.text(), "Pose")         # the panel's own: follows
        self.assertFalse(self.win.save_start.isVisible())
        self.assertEqual(self.scene.options[pw.SAVE_TYPE_VAR], "pose")

    def test_a_free_name_beside_either_type(self):
        store.write(self.root, "", "Anim", card_data("Anim"))       # a POSE called Anim
        self.win.refresh()
        self.open()
        self.win.save_types["anim"].click()
        self.assertEqual(self.win.save_name.text(), "Anim 2")

    def test_a_pose_save_hands_the_scene_no_range(self):
        self.open()
        self.win.save_confirm.click()
        self.assertIsNone(self.scene.calls("save")[0][5])
        self.assertEqual(self.win.picked, self.root + "/Pose.pose")


class AnimOptions(AnimCase):

    WHOLE = {"mode": "replace", "at_current": True, "start": 10.0, "end": 57.0,
             "connect": False, "keys": "every", "in_place": False}

    def set_every_option(self, win=None):
        win = win or self.win
        win.paste_buttons["insert"].click()
        win.at_current.click()                       # off
        win.connect_box.click()                      # on
        win.keys_buttons["source"].click()
        win.in_place.click()                         # on
        win.range_start.setValue(12)
        win.range_end.setValue(30)

    def test_picking_an_animation_shows_its_options_and_its_range(self):
        self.assertFalse(self.win.anim_options.isVisible())
        self.win.pick(self.walk)
        self.assertEqual(self.win.anim_options.objectName(), "skeldarPoseAnimOptions")
        self.assertTrue(self.win.anim_options.isVisible())
        self.assertEqual((self.win.range_start.value(), self.win.range_end.value()), (10, 57))
        self.assertIn("48 frames (10-57)", self.win.info.text())
        self.win.pick(self.fist)
        self.assertFalse(self.win.anim_options.isVisible())

    def test_the_widgets_are_named(self):
        names = [self.win.paste_buttons[mode].objectName() for mode in animdata.MODES]
        self.assertEqual(names, ["skeldarPosePaste_replace", "skeldarPosePaste_replace_all",
                                 "skeldarPosePaste_insert", "skeldarPosePaste_merge"])
        self.assertEqual([self.win.paste_buttons[m].text() for m in animdata.MODES],
                         ["Replace", "Replace all", "Insert", "Merge"])
        self.assertEqual([self.win.keys_buttons[k].objectName() for k in ("every", "source")],
                         ["skeldarPoseKeys_every", "skeldarPoseKeys_source"])
        win = self.win
        self.assertEqual((win.at_current.objectName(), win.connect_box.objectName(),
                          win.in_place.objectName(), win.range_start.objectName(),
                          win.range_end.objectName()),
                         ("skeldarPoseAtCurrent", "skeldarPoseConnect", "skeldarPoseInPlace",
                          "skeldarPoseRangeStart", "skeldarPoseRangeEnd"))

    def test_the_frame_fields_wear_the_hubs_field(self):
        self.win.pick(self.walk)
        box = self.win.range_start
        image = QT.QtGui.QImage(box.size(), QT.QtGui.QImage.Format_ARGB32)
        image.fill(0)
        box.render(image)
        self.assertEqual(image.pixelColor(box.width() // 4, box.height() // 2).name(),
                         hubstyle.TOKENS["field"])                  # not Maya's own spin box

    def test_the_options_start_at_their_defaults(self):
        self.win.pick(self.walk)
        self.assertEqual(self.win.options(), self.WHOLE)
        self.assertTrue(self.win.paste_buttons["replace"].isChecked())
        self.assertTrue(self.win.keys_buttons["every"].isChecked())
        self.assertEqual(self.scene.options, {})                     # nothing written yet

    def test_apply_passes_every_option(self):
        self.win.pick(self.walk)
        self.set_every_option()
        self.win.apply_button.click()
        self.assertEqual(self.scene.calls("apply"),
                         [("apply", self.walk, False,
                           {"mode": "insert", "at_current": False, "start": 12.0, "end": 30.0,
                            "connect": True, "keys": "source", "in_place": True})])

    def test_a_pose_card_hides_the_block_and_passes_no_options(self):
        self.win.pick(self.walk)
        self.win.pick(self.fist)
        self.assertFalse(self.win.anim_options.isVisible())
        self.win.apply_button.click()
        self.assertEqual(self.scene.calls("apply"), [("apply", self.fist, False, None)])

    def test_the_options_are_remembered_across_a_new_window(self):
        self.win.pick(self.walk)
        self.set_every_option()
        self.assertEqual((self.scene.options[pw.PASTE_VAR], self.scene.options[pw.AT_CURRENT_VAR],
                          self.scene.options[pw.CONNECT_VAR], self.scene.options[pw.KEYS_VAR],
                          self.scene.options[pw.IN_PLACE_VAR]), ("insert", 0, 1, "source", 1))
        win = self.window()
        win.pick(self.walk)
        # the range is the card's own again: it is not remembered
        self.assertEqual(win.options(), {"mode": "insert", "at_current": False, "start": 10.0,
                                         "end": 57.0, "connect": True, "keys": "source",
                                         "in_place": True})

    def test_an_option_turned_off_stays_off_and_one_never_written_is_its_default(self):
        self.scene.options[pw.AT_CURRENT_VAR] = 0
        self.scene.options[pw.PASTE_VAR] = "paste_over"               # another build's
        win = self.window()
        win.pick(self.walk)
        self.assertEqual(win.options(), dict(self.WHOLE, at_current=False))
        self.assertTrue(win.paste_buttons["replace"].isChecked())

    def test_the_range_is_the_card_s_and_resets_when_another_card_is_picked(self):
        self.win.pick(self.walk)
        self.win.range_start.setValue(0)
        self.win.range_end.setValue(99)
        self.assertEqual((self.win.range_start.value(), self.win.range_end.value()), (10, 57))
        self.win.range_start.setValue(20)
        self.win.range_end.setValue(30)
        self.win.pick(self.walk)            # the same card again - a press to drag it: kept
        self.assertEqual((self.win.range_start.value(), self.win.range_end.value()), (20, 30))
        self.win.pick(self.fist)
        self.win.pick(self.walk)
        self.assertEqual((self.win.range_start.value(), self.win.range_end.value()), (10, 57))

    def test_drops_pass_the_options(self):
        self.win.pick(self.walk)
        self.set_every_option()
        options = self.win.options()
        self.win.drop_at(-2000, 40, self.walk)
        self.assertEqual(self.scene.calls("apply_onto"),
                         [("apply_onto", self.walk, "|Manny_Rig1:root", False, options)])
        self.scene.aim = dict(kind="floor", point=(150.0, 0.0, -60.0))
        self.win.drop_at(-2000, 40, self.walk)
        self.deferred.pop()()
        self.assertEqual(self.scene.calls("drop_floor"),
                         [("drop_floor", self.walk, (150.0, 0.0, -60.0), False, options)])

    def test_the_blend_and_select_objects_pass_the_options(self):
        self.win.pick(self.walk)
        options = self.win.options()
        self.win.mirror.setChecked(True)
        self.assertEqual(self.win.blend_drag(self.walk, 100), 0.5)
        self.win.blend_release()
        self.assertEqual(self.scene.calls("blend_start"),
                         [("blend_start", self.walk, True, options)])
        self.win.select_button.click()
        self.assertEqual(self.scene.calls("select_objects"),
                         [("select_objects", self.walk, options)])

    def test_a_card_not_picked_is_pasted_whole_with_the_options_shown(self):
        self.win.pick(self.walk)
        self.win.paste_buttons["merge"].click()
        self.win.range_start.setValue(30)
        self.win.pick(self.fist)
        self.rows(self.walk)["Apply"]()
        (_apply, path, mirror, options), = self.scene.calls("apply")
        self.assertEqual((path, mirror), (self.walk, False))
        self.assertEqual(options, dict(self.WHOLE, mode="merge", start=None, end=None))


class AnimMenus(AnimCase):

    def test_the_right_button_rows_of_an_animation_card(self):
        labels = [row[0] for row in self.win.context_actions(self.walk) if row]
        self.assertEqual(labels, ["Apply", "Apply mirrored", "Select objects", "Rename...",
                                  "Move to...", "Replace thumbnail and preview",
                                  "Update from selection", "Show in Explorer", "Delete"])

    def test_replace_thumbnail_and_preview_asks_the_scene(self):
        self.assertIsNotNone(self.win.canvas.sheet(self.win._card(self.walk)))
        self.rows(self.walk)["Replace thumbnail and preview"]()
        self.assertEqual(self.scene.calls("replace_preview"), [("replace_preview", self.walk)])
        self.assertEqual(self.scene.calls("snapshot"), [])          # not the pose's road
        self.assertEqual(self.win.status.text(), "new thumbnail and preview")
        self.assertNotIn(self.walk, self.win.canvas.sheets)         # the old sheet dropped

    def test_a_pose_card_keeps_its_replace_thumbnail(self):
        labels = [row[0] for row in self.win.context_actions(self.fist) if row]
        self.assertIn("Replace thumbnail", labels)
        self.assertNotIn("Replace thumbnail and preview", labels)
        self.rows(self.fist)["Replace thumbnail"]()
        self.assertEqual(self.scene.calls("replace_preview"), [])
        self.assertEqual(len(self.scene.calls("snapshot")), 1)

    def test_a_failed_replace_lands_on_the_status_line(self):
        def boom(path):
            raise RuntimeError("no model panel")
        self.scene.replace_preview = boom
        self.rows(self.walk)["Replace thumbnail and preview"]()
        self.assertIn("no model panel", self.win.status.text())

    def test_the_dialogs_name_what_the_card_is(self):
        for path, noun in ((self.walk, "animation"), (self.fist, "pose")):
            titles = []
            self.win.ask_text = lambda title, label, text, seen=titles: seen.append(title)
            self.win.ask_item = lambda title, label, items, seen=titles: seen.append(title)
            self.win.confirm = lambda title, text, seen=titles: seen.append(title) or False
            rows = self.rows(path)
            for label in ("Rename...", "Move to...", "Update from selection", "Delete"):
                rows[label]()
            self.assertEqual(titles, ["Rename " + noun, "Move " + noun, "Update " + noun,
                                      "Delete " + noun])
        self.assertEqual(self.scene.calls("update"), [])            # every dialog said no

    def test_a_renamed_animation_keeps_its_type(self):
        self.win.ask_text = lambda title, label, text: "Run"
        self.rows(self.walk)["Rename..."]()
        renamed = self.root + "/Run.anim"
        self.assertTrue(os.path.isdir(renamed))
        self.assertEqual(self.win.picked, renamed)
        self.assertEqual(self.win.status.text(), "renamed to Run")

    def test_update_from_selection_says_the_still_and_the_preview_are_kept(self):
        asked = []
        self.win.confirm = lambda title, text: asked.append((title, text)) or True
        self.rows(self.walk)["Update from selection"]()
        self.assertEqual(self.scene.calls("update"), [("update", self.walk)])
        title, text = asked[0]
        self.assertEqual(title, "Update animation")
        self.assertIn("10-57", text)
        self.assertIn("thumbnail and preview are kept", text)


class DetailsPlayback(AnimCase):
    """The details picture of a picked animation card loops its preview."""

    def setUp(self):
        AnimCase.setUp(self)
        self.now = 0
        self.win._clock_ms = lambda: self.now

    def centre(self):
        image = self.win.thumb.pixmap().toImage()
        return image.pixelColor(image.width() // 2, image.height() // 2)

    def test_the_details_loop_the_preview_and_stop_on_unpick(self):
        self.win.pick(self.walk)
        self.assertTrue(self.win.play_timer.isActive())
        self.assertEqual(self.win.play_timer.interval(), look.PLAY_MS)
        self.assertGreater(self.centre().red(), 150)                 # cell 0 at once
        self.assertEqual(self.win.thumb.pixmap().width(), self.win.thumb_side())
        self.now = 100                                               # 3 frames at 30 fps
        self.win._play_tick()
        self.assertGreater(self.centre().blue(), 150)                # cell 1
        self.now = 200                                               # 6 frames: round again
        self.win._play_tick()
        self.assertGreater(self.centre().red(), 150)
        self.win.unpick()
        self.assertFalse(self.win.play_timer.isActive())

    def test_a_pose_pick_stops_it(self):
        self.win.pick(self.walk)
        self.win.pick(self.fist)
        self.assertFalse(self.win.play_timer.isActive())

    def test_a_hidden_window_does_not_play(self):
        self.win.pick(self.walk)
        self.win.hide()
        self.assertFalse(self.win.play_timer.isActive())
        self.win.show()
        self.assertTrue(self.win.play_timer.isActive())

    def test_the_save_panel_stops_it(self):
        self.win.pick(self.walk)
        self.win.save_button.click()
        self.assertFalse(self.win.play_timer.isActive())
        self.win.save_cancel.click()
        self.assertTrue(self.win.play_timer.isActive())

    def test_off_the_screen_it_rests_and_plays_again_when_exposed(self):
        """A floating Pose Library whose Maya is minimised is hidden by Windows while Qt still
        calls it visible (measured in a GUI Maya, 2026-10-08: isVisible True, isExposed False,
        IsWindowVisible False) - no hideEvent comes. Its details then draw nothing and the
        timer slows to PLAY_HIDDEN_MS; exposed again, it plays at PLAY_MS from where the clock
        is."""
        self.win.pick(self.walk)
        before = self.win.thumb.pixmap().cacheKey()
        self.win._on_screen = lambda: False
        self.now = 100                                               # cell 1 is due ...
        self.win._play_tick()
        self.assertEqual(self.win.thumb.pixmap().cacheKey(), before)  # ... and not drawn
        self.assertEqual(self.win.play_timer.interval(), pw.PLAY_HIDDEN_MS)
        self.assertTrue(self.win.play_timer.isActive())
        self.win._on_screen = lambda: True
        self.win._play_tick()
        self.assertGreater(self.centre().blue(), 150)                # cell 1 drawn
        self.assertEqual(self.win.play_timer.interval(), look.PLAY_MS)

    def test_offscreen_qt_counts_as_on_the_screen(self):
        """No native window to ask (the offscreen platform the tests run on): on the screen."""
        self.win.pick(self.walk)
        self.assertTrue(self.win._on_screen())

    def test_a_native_window_is_seen_while_its_root_is_shown_and_not_minimised(self):
        """`native_shown` asks Windows from a plain handle (no wrapper of a Maya widget - trap
        135): the root window of `hwnd` visible and not minimised. A floating window whose Maya
        is minimised is HIDDEN (measured: IsWindowVisible False); a docked one stands in a
        minimised Maya (IsIconic True); a handle Windows does not know counts as seen."""

        class User32(object):
            def __init__(self, known=True, root=7, visible=True, iconic=False):
                self.known, self.root, self.visible, self.iconic = known, root, visible, iconic
                self.asked = []

            def IsWindow(self, hwnd):                                # noqa: N802
                return self.known

            def GetAncestor(self, hwnd, flag):                       # noqa: N802
                self.asked.append((hwnd, flag))
                return self.root

            def IsWindowVisible(self, hwnd):                         # noqa: N802
                return self.visible if hwnd == self.root or not self.root else True

            def IsIconic(self, hwnd):                                # noqa: N802
                return self.iconic if hwnd == self.root or not self.root else False

        seen = User32()
        self.assertTrue(pw.native_shown(42, seen))
        self.assertEqual(seen.asked, [(42, pw.GA_ROOT)])
        self.assertFalse(pw.native_shown(42, User32(visible=False)))    # hidden with its owner
        self.assertFalse(pw.native_shown(42, User32(iconic=True)))      # docked, Maya minimised
        self.assertTrue(pw.native_shown(42, User32(known=False, visible=False)))
        self.assertTrue(pw.native_shown(0, User32(visible=False)))      # no handle at all
        self.assertFalse(pw.native_shown(42, User32(root=0, visible=False)))  # its own root

    def test_a_refresh_keeps_the_decoded_sheets(self):
        """A sheet decoded is about 23 MB of pixels and its cache already checks the file's time
        and size: a plain refresh (Refresh, a save, a rename) keeps it - only the card whose
        preview was replaced drops it (Task 9's review, minor 3)."""
        picture = self.win.canvas.sheet(self.win._card(self.walk))[0]
        self.win.refresh()
        self.assertIn(self.walk, self.win.canvas.sheets)
        self.assertIs(self.win.canvas.sheet(self.win._card(self.walk))[0], picture)
        self.win.replace_preview(self.walk)
        self.assertIsNot(self.win.canvas.sheet(self.win._card(self.walk))[0], picture)

    def test_an_animation_without_a_preview_shows_its_still(self):
        still = write_jpg(os.path.join(self.tmp, "run.jpg"), self.GREEN)
        run = store.write(self.root, "", "Run", anim_data("Run"), still, frames=FRAMES)
        self.win.refresh()
        self.win.pick(run)
        self.assertFalse(self.win.play_timer.isActive())
        self.assertGreater(self.centre().green(), 120)


# ------------------------------------------------------------------ the real Scene

class FakeProgress(object):
    """timewalk.Progress, recorded."""

    log = None
    answers = ()

    def __init__(self, title, total):
        self.title, self.total = title, total
        FakeProgress.log.append(("progress", title, total))

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        FakeProgress.log.append(("progress_end", self.title))
        return False

    def step(self, text=""):
        return True


class FakeModules(object):
    """The modules the real Scene imports late - `animapply`, `animcapture`, `apply`,
    `capture`, `timewalk` - as attributes standing in for them on the package, recording
    every call into one log."""

    def __init__(self, test):
        self.test = test
        self.log = []
        FakeProgress.log = self.log
        self.built = None             # what build_animation answers; None: a card of 7 frames
        self.previewed = None         # what preview answers; None: a sheet is painted
        self.preview_error = None     # an exception preview raises instead of answering
        self.colour = "#c08020"

    # --- animcapture

    def default_range(self):
        return (3, 9)

    def build_animation(self, selection=None, regions=None, start=None, end=None,
                        progress=None):
        self.log.append(("build_animation", regions, start, end, progress is not None))
        if self.built is not None:
            return self.built
        header = anim_data("Anim", start, end)
        return header, {"bones": ["root"], "world": [[0, 0, 0, 1, 0, 0, float(n)]
                                                      for n in range(end - start + 1)]}, \
            "Manny_Rig: %d frames" % (end - start + 1)

    def preview(self, sheet_path, start, end, progress=None):
        self.log.append(("preview", start, end, progress is not None))
        if self.preview_error is not None:
            raise self.preview_error
        if self.previewed is not None:
            return self.previewed
        info = write_sheet(sheet_path, (self.colour, "#202020"))
        return True, "preview from modelPanel4: 2 cells", info

    # --- capture

    def thumbnail(self, path):
        self.log.append(("thumbnail",))
        write_jpg(path, self.colour)
        return True, "thumbnail from modelPanel4"

    def build_pose(self, selection=None, regions=None, frame=None):
        self.log.append(("build_pose", regions))
        return card_data("Pose"), "a pose"

    # --- the presses

    def install(self):
        import types
        ap = types.SimpleNamespace(apply=self._press("animapply.apply"),
                                   apply_onto=self._press("animapply.apply_onto"),
                                   drop_floor=self._press("animapply.drop_floor"),
                                   select_objects=self._select("animapply.select_objects"),
                                   Blend=self._blend("animapply"))
        pose = types.SimpleNamespace(apply=self._press("apply.apply"),
                                     apply_onto=self._press("apply.apply_onto"),
                                     drop_floor=self._press("apply.drop_floor"),
                                     select_objects=self._select("apply.select_objects"),
                                     Blend=self._blend("apply"))
        capture = types.SimpleNamespace(thumbnail=self.thumbnail, build_pose=self.build_pose)
        animcapture = types.SimpleNamespace(default_range=self.default_range,
                                            build_animation=self.build_animation,
                                            preview=self.preview,
                                            CANCELLED="cancelled - nothing saved")
        timewalk = types.SimpleNamespace(Progress=FakeProgress)
        for name, fake in (("animapply", ap), ("apply", pose), ("capture", capture),
                           ("animcapture", animcapture), ("timewalk", timewalk)):
            had = name in maya_poselib.__dict__
            saved = maya_poselib.__dict__.get(name)
            setattr(maya_poselib, name, fake)
            if had:
                self.test.addCleanup(setattr, maya_poselib, name, saved)
            else:
                self.test.addCleanup(delattr, maya_poselib, name)

    def _press(self, name):
        def press(data, *args, **kwargs):
            frames = None
            if name.startswith("animapply"):
                frames, args = args[0], args[1:]
            self.log.append((name, data.get("name"), frames, args,
                             dict((k, v) for k, v in kwargs.items() if k != "progress"),
                             kwargs.get("progress") is not None))
            return True, name + " done"
        return press

    def _select(self, name):
        def select(data, selection=None, options=None):
            self.log.append((name, data.get("name"), options))
            return True, "selected"
        return select

    def _blend(self, owner):
        log = self.log

        class Blend(object):
            def start(self, data, *args, **kwargs):
                log.append((owner + ".Blend.start", data.get("name"), args, kwargs))
                return ""

            def set(self, alpha):
                log.append((owner + ".Blend.set", alpha))

            def finish(self, progress=None):
                log.append((owner + ".Blend.finish", progress is not None))
                return "blended"

            def cancel(self):
                log.append((owner + ".Blend.cancel",))
        return Blend


@unittest.skipIf(QT is None, "no Qt")
class RealScene(unittest.TestCase):
    """The real `Scene`'s animation half over a temp library, its late imports standing in."""

    def setUp(self):
        self.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        self.tmp = tempfile.mkdtemp(prefix="skeldar_poselib_scene_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = os.path.join(self.tmp, "poses").replace("\\", "/")
        os.makedirs(self.root)
        self.fakes = FakeModules(self)
        self.fakes.install()
        saved = pw._current_time
        pw._current_time = lambda: 100.0
        self.addCleanup(setattr, pw, "_current_time", saved)
        self.scene = pw.Scene()
        self.scene.library = lambda: self.root
        self.fist = store.write(self.root, "", "Fist", card_data("Fist"))
        sheet = os.path.join(self.tmp, "sheet.jpg")
        info = write_sheet(sheet, ("#d02020", "#2040d0"))
        still = write_jpg(os.path.join(self.tmp, "still.jpg"), "#20a040")
        self.walk = store.write(self.root, "", "Walk", anim_data("Walk", preview=info), still,
                                frames=FRAMES, preview=sheet)
        self.snapshot = write_jpg(os.path.join(self.tmp, "snap.jpg"), "#3060c0")

    def logged(self, prefix):
        return [entry for entry in self.fakes.log if entry[0].startswith(prefix)]

    def colour(self, path):
        """The image's colour a quarter in from its left, half way down - in a two-cell sheet,
        the first cell's."""
        image = QT.QtGui.QImage(path)
        return image.pixelColor(image.width() // 4, image.height() // 2).name()

    def assertColour(self, path, expected):                 # noqa: N802
        """`path`'s colour (`colour`) is `expected` but for what a JPG makes of it."""
        seen, wanted = QT.QtGui.QColor(self.colour(path)), QT.QtGui.QColor(expected)
        self.assertTrue(all(abs(a - b) <= 12 for a, b in zip(seen.getRgb()[:3],
                                                              wanted.getRgb()[:3])),
                        "%s: %s, not %s" % (os.path.basename(path), seen.name(), expected))

    # --- the presses

    def test_a_pose_card_takes_the_pose_road(self):
        self.assertEqual(self.scene.apply(self.fist, True), (True, "apply.apply done"))
        self.assertEqual(self.logged("apply."),
                         [("apply.apply", "Fist", None, (), {"mirror": True}, False)])
        self.assertEqual(self.logged("progress"), [])

    def test_an_animation_card_is_pasted_with_its_frames_under_a_progress_window(self):
        options = {"mode": "insert", "start": 20.0, "end": 29.0}
        ok, text = self.scene.apply(self.walk, True, options)
        self.assertEqual((ok, text), (True, "animapply.apply done"))
        (name, card, frames, args, kwargs, progressed), = self.logged("animapply.")
        self.assertEqual((name, card, args), ("animapply.apply", "Walk", ()))
        self.assertEqual(frames, FRAMES)
        self.assertEqual(kwargs, {"mirror": True, "options": options})
        self.assertTrue(progressed)
        self.assertEqual(self.logged("progress"),
                         [("progress", "Pasting Walk", 10), ("progress_end", "Pasting Walk")])

    def test_the_drops_and_select_objects_dispatch_too(self):
        options = {"mode": "merge"}
        self.scene.apply_onto(self.walk, "|Manny_Rig1:root", False, options)
        self.scene.drop_floor(self.walk, (150.0, 0.0, -60.0), True, options)
        self.scene.select_objects(self.walk, options)
        self.scene.apply_onto(self.fist, "|Manny_Rig1:root", False)
        self.scene.select_objects(self.fist)
        self.assertEqual(
            [entry[:2] + entry[3:5] for entry in self.logged("animapply.")[:2]],
            [("animapply.apply_onto", "Walk", ("|Manny_Rig1:root",),
              {"mirror": False, "options": options}),
             ("animapply.drop_floor", "Walk", ((150.0, 0.0, -60.0),),
              {"mirror": True, "options": options})])
        self.assertEqual(self.logged("animapply.select_objects"),
                         [("animapply.select_objects", "Walk", options)])
        self.assertEqual([entry[0] for entry in self.logged("apply.")],
                         ["apply.apply_onto", "apply.select_objects"])

    def test_a_card_whose_frames_cannot_be_read_hands_the_press_none(self):
        os.remove(self.walk + "/" + store.FRAMES_FILE)
        self.scene.apply(self.walk, False)
        self.assertIsNone(self.logged("animapply.apply")[0][2])

    def test_an_animation_blend_finishes_under_a_progress_window(self):
        options = {"mode": "replace"}
        self.assertEqual(self.scene.blend_start(self.walk, False, options), "")
        self.scene.blend_set(0.5)
        self.assertEqual(self.scene.blend_finish(), "blended")
        self.assertEqual(self.logged("animapply.Blend"),
                         [("animapply.Blend.start", "Walk", (FRAMES,),
                           {"mirror": False, "options": options}),
                          ("animapply.Blend.set", 0.5), ("animapply.Blend.finish", True)])
        self.assertEqual(self.logged("progress")[0], ("progress", "Pasting Walk", 48))
        # a pose's blend is the pose's, with no progress window
        self.scene.blend_start(self.fist, True)
        self.scene.blend_finish()
        self.assertEqual(self.logged("apply.Blend")[-1], ("apply.Blend.finish", False))

    # --- Save, Update, Replace thumbnail and preview

    def test_save_an_animation_writes_its_frames_still_and_preview(self):
        path, text = self.scene.save("Run", "", None, self.snapshot, anim={"start": 3, "end": 9})
        self.assertEqual(path, self.root + "/Run.anim")
        self.assertEqual(self.logged("build_animation"), [("build_animation", None, 3, 9, True)])
        self.assertEqual(self.logged("preview"), [("preview", 3, 9, True)])
        # one progress window: a step a frame read, a step a preview cell painted
        self.assertEqual(self.logged("progress"),
                         [("progress", "Saving Run", 14), ("progress_end", "Saving Run")])
        header = store.read(path)
        self.assertEqual(header["preview"], {"frames": 2, "columns": 2, "size": 32, "step": 1})
        self.assertEqual(len(store.read_frames(path)["world"]), 7)
        for name in (store.THUMB_FILE, store.PREVIEW_FILE):
            self.assertTrue(os.path.isfile(path + "/" + name), name)
        self.assertTrue(text.startswith("saved Run in Library - Manny_Rig: 7 frames"), text)
        self.assertIn("preview from modelPanel4", text)
        self.assertEqual([n for n in os.listdir(tempfile.gettempdir())
                          if n.startswith("skeldar_anim_sheet_%d" % os.getpid())], [])

    def test_a_save_without_a_preview_says_why_and_keeps_the_card(self):
        self.fakes.previewed = (False, "no viewport for a preview", None)
        path, text = self.scene.save("Run", "", None, None, anim={"start": 3, "end": 9})
        self.assertNotIn("preview", store.read(path))
        self.assertFalse(os.path.isfile(path + "/" + store.PREVIEW_FILE))
        self.assertFalse(os.path.isfile(path + "/" + store.THUMB_FILE))
        self.assertIn("saved without a preview: no viewport for a preview", text)

    def test_a_preview_that_raises_still_saves_the_card(self):
        """The frames were walked already: an exception out of the preview (a playblast Maya
        refused) saves the card without one, and says why - the spec's «a preview that cannot be
        made still saves the card» (Task 9's review, minor 2)."""
        self.fakes.preview_error = RuntimeError("Maya command error")
        path, text = self.scene.save("Run", "", None, self.snapshot, anim={"start": 3, "end": 9})
        self.assertEqual(path, self.root + "/Run.anim")
        self.assertNotIn("preview", store.read(path))
        self.assertEqual(len(store.read_frames(path)["world"]), 7)
        self.assertTrue(os.path.isfile(path + "/" + store.THUMB_FILE))
        self.assertFalse(os.path.isfile(path + "/" + store.PREVIEW_FILE))
        self.assertTrue(text.endswith("saved without a preview: RuntimeError: Maya command "
                                      "error"), text)
        self.assertEqual(self.logged("progress"),
                         [("progress", "Saving Run", 14), ("progress_end", "Saving Run")])
        self.assertEqual([n for n in os.listdir(tempfile.gettempdir())
                          if n.startswith("skeldar_anim_sheet_%d" % os.getpid())], [])

    def test_a_cancelled_save_writes_nothing(self):
        for built, previewed in (((None, None, "cancelled - nothing saved"), None),
                                 (None, (False, "cancelled - nothing saved", None))):
            self.fakes.built, self.fakes.previewed = built, previewed
            path, text = self.scene.save("Run", "", None, self.snapshot,
                                         anim={"start": 3, "end": 9})
            self.assertEqual((path, text), (None, "cancelled - nothing saved"))
            self.assertFalse(os.path.exists(self.root + "/Run.anim"))

    def test_a_pose_save_is_the_pose_s(self):
        path, text = self.scene.save("Grip", "", None, self.snapshot)
        self.assertEqual(path, self.root + "/Grip.pose")
        self.assertEqual(text, "saved Grip in Library - a pose")
        self.assertEqual(self.logged("progress"), [])

    def test_the_range_is_animcapture_s(self):
        self.assertEqual(self.scene.anim_range(), (3, 9))

    def test_update_an_animation_reads_its_own_range_and_keeps_the_still_and_preview(self):
        still = self.colour(self.walk + "/" + store.THUMB_FILE)
        before = store.read(self.walk)["preview"]
        ok, text = self.scene.update(self.walk)
        self.assertTrue(ok)
        self.assertEqual(self.logged("build_animation"), [("build_animation", None, 10, 57, True)])
        self.assertEqual(self.logged("progress")[0], ("progress", "Updating Walk", 48))
        header = store.read(self.walk)
        self.assertEqual(header["name"], "Walk")
        self.assertEqual(header["preview"], before)
        self.assertEqual(len(store.read_frames(self.walk)["world"]), 48)
        self.assertEqual(self.colour(self.walk + "/" + store.THUMB_FILE), still)
        self.assertEqual(text, "Walk updated from the selection over frames 10-57 - "
                               "Manny_Rig: 48 frames")

    def test_replace_thumbnail_and_preview_takes_both_again(self):
        text = self.scene.replace_preview(self.walk)
        self.assertEqual(self.logged("preview"), [("preview", 10, 57, True)])
        self.assertEqual(self.logged("progress")[0], ("progress", "Previewing Walk", 48))
        self.assertColour(self.walk + "/" + store.THUMB_FILE, self.fakes.colour)
        self.assertColour(self.walk + "/" + store.PREVIEW_FILE, self.fakes.colour)
        self.assertEqual(store.read(self.walk)["preview"]["frames"], 2)
        self.assertEqual(len(store.read_frames(self.walk)["world"]), 1)        # kept
        self.assertEqual(text, "new thumbnail and preview - thumbnail from modelPanel4 | "
                               "preview from modelPanel4: 2 cells")

    def test_a_cancelled_preview_changes_nothing(self):
        still = self.colour(self.walk + "/" + store.THUMB_FILE)
        self.fakes.previewed = (False, "cancelled - nothing saved", None)
        self.assertEqual(self.scene.replace_preview(self.walk), "cancelled - nothing changed")
        self.assertEqual(self.colour(self.walk + "/" + store.THUMB_FILE), still)

    def test_a_preview_that_cannot_be_made_keeps_the_old_one(self):
        before = store.read(self.walk)["preview"]
        sheet = self.colour(self.walk + "/" + store.PREVIEW_FILE)
        self.fakes.previewed = (False, "no viewport for a preview", None)
        text = self.scene.replace_preview(self.walk)
        self.assertColour(self.walk + "/" + store.THUMB_FILE, self.fakes.colour)
        self.assertEqual(self.colour(self.walk + "/" + store.PREVIEW_FILE), sheet)
        self.assertEqual(store.read(self.walk)["preview"], before)
        self.assertEqual(text, "new thumbnail - thumbnail from modelPanel4 | the preview "
                               "kept: no viewport for a preview")

    def test_replace_on_a_pose_card_is_the_thumbnail_alone(self):
        text = self.scene.replace_preview(self.fist)
        self.assertColour(self.fist + "/" + store.THUMB_FILE, self.fakes.colour)
        self.assertEqual(self.logged("preview"), [])
        self.assertEqual(text, "new thumbnail - thumbnail from modelPanel4")


if __name__ == "__main__":
    unittest.main()
