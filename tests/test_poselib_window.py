"""The Pose Library window, offscreen (2026-10-02): the cards of a temp library listed, searched,
sorted and narrowed by a folder; a pick filling the details; drops onto a character, the floor, a
folder and the window itself; the right button's rows; the blend gesture (middle drag, release,
Esc) and the slider; the save panel; the folder tree's rows; the hub card and the
workspaceControl half on a recording `cmds`. Every scene call goes to a FakeScene, so no Maya
scene is touched - the scene half is verify_poselib_apply.py's, the live window Task 10's.

Spec: docs/superpowers/specs/2026-10-02-pose-library-design.md ("The window")
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
from maya_poselib import look
from maya_poselib import store
from maya_poselib import window as pw
from tests.uifakes import FakeUiCmds


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
        return self.targets

    def save(self, name, folder, regions, snapshot_path):
        self.log.append(("save", name, folder, regions, snapshot_path))
        path = store.write(self.root, folder, name, card_data(name), thumbnail=snapshot_path)
        return path, "saved " + name

    def snapshot(self, path):
        self.log.append(("snapshot", path))
        write_jpg(path, "#aa3322")
        return True, "thumbnail from modelPanel4"

    def update(self, path):
        self.log.append(("update", path))
        return True, "updated"

    def apply(self, path, mirror):
        self.log.append(("apply", path, mirror))
        return True, "applied"

    def apply_onto(self, path, root, mirror):
        self.log.append(("apply_onto", path, root, mirror))
        return True, "applied onto " + root

    def drop_floor(self, path, point, mirror):
        self.log.append(("drop_floor", path, point, mirror))
        return True, "added on the floor"

    def select_objects(self, path):
        self.log.append(("select_objects", path))
        return True, "selected"

    def blend_start(self, path, mirror):
        self.log.append(("blend_start", path, mirror))
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
        self.assertEqual(roles[1][1], "books" if "books" in maya_hubicons.ICONS else "folder")
        texts = [c for c in self.cmds.calls if c[0] == "text"]
        self.assertEqual(texts[0][2]["label"], "Poses of bones - onto any rig or skeleton.")
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

    def names(self):
        return [os.path.basename(path)[:-len(store.CARD_SUFFIX)]
                for path in self.win.cards_shown()]

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
                         [("apply", self.fist, False), ("apply", self.fist, True)])
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

    def test_select_objects(self):
        self.win.pick(self.idle)
        self.win.select_button.click()
        self.assertEqual(self.scene.calls("select_objects"), [("select_objects", self.idle)])

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
                         [("apply_onto", self.fist, "|Manny_Rig1:root", False)])

    def test_over_the_floor_the_source_is_added_one_idle_later(self):
        self.scene.aim = dict(kind="floor", point=(150.0, 0.0, -60.0))
        self.win.drop_at(-2000, 40, self.fist)
        self.assertEqual(self.scene.calls("drop_floor"), [])
        self.assertEqual(len(self.deferred), 1)
        self.deferred.pop()()
        self.assertEqual(self.scene.calls("drop_floor"),
                         [("drop_floor", self.fist, (150.0, 0.0, -60.0), False)])

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
        self.assertEqual(self.scene.calls("apply"), [("apply", self.wave, False)])

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
        self.assertEqual(self.scene.calls("apply"), [("apply", self.fist, True)])

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
        self.assertEqual(self.scene.calls("blend_start"), [("blend_start", self.fist, False)])
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
        self.assertEqual(self.scene.calls("blend_start"), [("blend_start", self.fist, False)])
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
        self.assertEqual(self.blend_calls(), [("blend_start", self.fist, False),
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
        self.assertEqual(self.blend_calls(), [("blend_start", self.fist, False),
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
        self.assertEqual(self.blend_calls(), [("blend_start", self.fist, False),
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
        self.assertEqual(self.blend_calls(), [("blend_start", self.fist, False),
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
        (_name, name, folder, regions, snap), = self.scene.calls("save")
        self.assertEqual((name, folder, regions), ("Grip", "Hands", None))
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


if __name__ == "__main__":
    unittest.main()
