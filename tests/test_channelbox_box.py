"""Our Channel Box offscreen (2026-10-18), on a fake link so no Maya scene is touched:
painting, selection and its sync into Maya's Channel Box, the virtual slider in one
undo chunk, typed values, the key cell, the effects a refresh finds, the keys the
playhead reaches, the menu, and the mount over stand-in widgets.

Spec: docs/superpowers/specs/2026-10-18-channel-box-rows-design.md
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import maya_hubqt
    QT = maya_hubqt.qt()
except Exception:                                            # noqa: BLE001
    QT = None

import maya_hubstyle
from maya_channelbox import box as box_module, look


def chan(attr, value, kind="double", keys=(), on_key=False, **kw):
    plug = "IKLeg_L." + attr
    d = {"key": attr, "node": "IKLeg_L", "attr": attr, "plug": plug, "nice": attr.title(),
         "kind": kind, "value": value, "names": None, "lo": None, "hi": None, "locked": False,
         "muted": False, "source": "curve" if keys else None, "keys": list(keys),
         "breakdowns": [], "on_key": on_key, "breakdown": False, "changed": False,
         "targets": [plug, "IKLeg_R." + attr]}
    d.update(kw)
    return d


class FakeLink(object):

    def __init__(self):
        self.log = []
        self.frame = 12.0
        self.chans = [chan("translateX", 4.8, "doubleLinear", [0, 12, 24], True),
                      chan("translateY", 9.4, "doubleLinear", [0, 6, 24]),
                      chan("rotateX", -18.5, "doubleAngle"),
                      chan("scaleX", 1.0, locked=True),
                      chan("visibility", 1, "bool"),
                      chan("rotateOrder", 0, "enum", names=["xyz", "yzx", "zxy"]),
                      chan("swivel", 0.0, source="driven")]

    def snapshot(self, opened=()):
        self.log.append(("snapshot", opened))
        return {"objects": ["|IKLeg_R", "|IKLeg_L"], "lead": "|IKLeg_L", "frame": self.frame,
                "sections": [{"key": "main", "kind": "main", "label": "IKLeg_L", "title": "",
                              "channels": [dict(c, keys=list(c["keys"])) for c in self.chans]},
                             {"key": "shapes:IKLeg_LShape", "kind": "shapes", "label": "IKLeg_LShape",
                              "title": "SHAPES",
                              "channels": [chan("lineWidth", -1.0)] if "shapes:IKLeg_LShape" in opened else []}]}

    def now(self):
        return self.frame

    def values(self, plugs):
        return [next((c["value"] for c in self.chans if c["plug"] == p), None) for p in plugs]

    def write(self, pairs):
        self.log.append(("write", list(pairs)))
        for plug, value in pairs:
            for c in self.chans:
                if c["plug"] == plug:
                    c["value"] = value
        return len(pairs)

    def key(self, plugs, breakdown=False):
        self.log.append(("key", list(plugs), breakdown))
        for c in self.chans:
            if c["plug"] in plugs and self.frame not in c["keys"]:
                c["keys"].append(self.frame)
                c["on_key"] = True
                c["source"] = "curve"
        return len(plugs)

    def unkey(self, plugs, frame):
        self.log.append(("unkey", list(plugs), frame))
        for c in self.chans:
            if c["plug"] in plugs and frame in c["keys"]:
                c["keys"].remove(frame)
                c["on_key"] = False
        return 1

    def mute(self, plugs, on):
        self.log.append(("mute", list(plugs), on))

    def lock(self, plugs, on):
        self.log.append(("lock", list(plugs), on))

    def select_connection(self, plugs):
        self.log.append(("select_connection", list(plugs)))

    def break_connections(self, plugs):
        self.log.append(("break_connections", list(plugs)))

    def sync_selection(self, plugs):
        self.log.append(("sync", list(plugs)))
        return True

    def speed(self):
        return 1.0

    def set_speed(self, value):
        self.log.append(("speed", value))

    def precision(self):
        return 3

    def chunk_open(self, name):
        self.log.append(("open", name))

    def chunk_close(self):
        self.log.append(("close",))

    def layers(self):
        return [("BaseAnimation", "BaseAnimation", False), ("AnimLayer1", "AnimLayer1", True)]

    def layer_label(self):
        return "AnimLayer1"

    def pick_layer(self, name):
        self.log.append(("pick_layer", name))

    def show_maya_box(self):
        self.log.append(("maya_box",))


@unittest.skipIf(QT is None, "no Qt")
class BoxTests(unittest.TestCase):

    def setUp(self):
        self.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])
        self.link = FakeLink()
        self.box = box_module.make(self.link, 1.0, maya_hubstyle.TOKENS, motion=True)
        self.box.resize(340, 420)
        self.box.show()
        self.app.processEvents()
        self.box.refresh(effects=False)
        self.app.processEvents()

    def tearDown(self):
        self.box.timer.stop()
        self.box.close()
        self.box.deleteLater()
        self.app.processEvents()

    def row_of(self, key):
        for i, r in enumerate(self.box.rows):
            if r["kind"] == "channel" and r["channel"]["key"] == key:
                return i, self.box.placed[i][2]
        raise KeyError(key)

    def point(self, rect):
        x, y, w, h = rect
        return QT.QtCore.QPointF(x + w / 2.0, y + h / 2.0)

    def mouse(self, kind, pos, mods=None, button=None):
        Qt = QT.QtCore.Qt
        button = button or Qt.LeftButton
        mods = mods if mods is not None else Qt.NoModifier
        types = {"press": QT.QtCore.QEvent.MouseButtonPress, "move": QT.QtCore.QEvent.MouseMove,
                 "release": QT.QtCore.QEvent.MouseButtonRelease,
                 "double": QT.QtCore.QEvent.MouseButtonDblClick}
        buttons = Qt.NoButton if kind == "release" else button
        ev = QT.QtGui.QMouseEvent(types[kind], pos, self.box.canvas.mapToGlobal(pos.toPoint()).toPointF(),
                                  button, buttons, mods)
        QT.QtWidgets.QApplication.sendEvent(self.box.canvas, ev)

    def render(self):
        img = QT.QtGui.QImage(self.box.size(), QT.QtGui.QImage.Format_ARGB32)
        img.fill(0)
        self.box.render(img)
        return img

    def test_rows_in_maya_order_with_rules_and_a_closed_shapes_section(self):
        kinds = [r["kind"] for r in self.box.rows]
        self.assertEqual(kinds, ["channel", "channel", "rule", "channel", "rule", "channel", "rule",
                                 "channel", "rule", "channel", "channel", "section"])
        self.assertEqual(self.box.lead, "|IKLeg_L")
        self.assertEqual(self.box.layer_text, "AnimLayer1")

    def test_it_paints_its_rows_and_the_keyed_cell_in_the_accent(self):
        img = self.render()
        i, parts = self.row_of("translateX")
        x, y, w, h = look.cell_rect(parts["mark"])
        head = self.box.head.height()
        c = img.pixelColor(int(x + w / 2), int(y + h / 2) + head)
        self.assertEqual(c.name(), maya_hubstyle.TOKENS["accent"])
        _, plain = self.row_of("rotateX")
        x, y, w, h = look.cell_rect(plain["mark"])
        self.assertNotEqual(img.pixelColor(int(x + w / 2), int(y + h / 2) + head).name(),
                            maya_hubstyle.TOKENS["accent"])

    def test_a_click_selects_and_writes_the_selection_into_maya(self):
        i, parts = self.row_of("translateY")
        self.mouse("press", self.point(parts["name"]))
        self.mouse("release", self.point(parts["name"]))
        self.assertEqual(self.box.selected, {"translateY"})
        self.assertEqual(self.link.log[-1], ("sync", ["IKLeg_L.translateY", "IKLeg_R.translateY"]))
        _, rx = self.row_of("rotateX")
        self.mouse("press", self.point(rx["name"]), QT.QtCore.Qt.ControlModifier)
        self.mouse("release", self.point(rx["name"]), QT.QtCore.Qt.ControlModifier)
        self.assertEqual(self.box.selected, {"translateY", "rotateX"})

    def test_a_drag_moves_every_selected_channel_of_every_object_in_one_chunk(self):
        self.box.selected = {"translateX", "rotateX"}
        _, parts = self.row_of("translateX")
        p = self.point(parts["name"])
        self.mouse("press", p)
        for dx in (2, 10, 20):
            self.mouse("move", QT.QtCore.QPointF(p.x() + dx, p.y()))
        self.mouse("release", QT.QtCore.QPointF(p.x() + 20, p.y()))
        names = [e[0] for e in self.link.log]
        self.assertEqual(names.count("open"), 1)
        self.assertEqual(names.count("close"), 1)
        self.assertLess(names.index("open"), names.index("write"))
        last = [e for e in self.link.log if e[0] == "write"][-1][1]
        values = dict(last)
        self.assertAlmostEqual(values["IKLeg_L.translateX"], 4.8 + 20 * 0.1)
        self.assertAlmostEqual(values["IKLeg_R.translateX"], 4.8 + 20 * 0.1)
        self.assertAlmostEqual(values["IKLeg_L.rotateX"], -18.5 + 20 * 1.0)
        self.assertNotIn("IKLeg_L.scaleX", values)

    def test_a_locked_channel_is_left_out_of_a_drag(self):
        self.box.selected = {"scaleX"}
        _, parts = self.row_of("scaleX")
        p = self.point(parts["value"])
        self.mouse("press", p)
        self.mouse("move", QT.QtCore.QPointF(p.x() + 30, p.y()))
        self.mouse("release", QT.QtCore.QPointF(p.x() + 30, p.y()))
        self.assertFalse([e for e in self.link.log if e[0] == "write" and e[1]])

    def test_typing_relative_values(self):
        i, parts = self.row_of("rotateX")
        ch = self.box.rows[i]["channel"]
        self.box.typed(ch, "+=10")
        writes = [e for e in self.link.log if e[0] == "write"]
        self.assertAlmostEqual(dict(writes[-1][1])["IKLeg_L.rotateX"], -8.5)
        self.box.typed(ch, "nonsense")
        self.assertEqual(len([e for e in self.link.log if e[0] == "write"]), len(writes))

    def test_the_editor_opens_on_a_double_click_and_applies_on_enter(self):
        _, parts = self.row_of("rotateX")
        self.mouse("double", self.point(parts["value"]))
        editor = self.box.canvas.editor
        self.assertIsNotNone(editor)
        editor.setText("45")
        editor.returnPressed.emit()
        self.app.processEvents()
        self.assertAlmostEqual(dict([e for e in self.link.log if e[0] == "write"][-1][1])["IKLeg_L.rotateX"], 45.0)

    def sweep_down(self, first, last, part="name", mods=None):
        _, a = self.row_of(first)
        _, b = self.row_of(last)
        pa, pb = self.point(a[part]), self.point(b[part])
        self.mouse("press", pa, mods)
        for t in (0.3, 0.7, 1.0):
            self.mouse("move", QT.QtCore.QPointF(pa.x(), pa.y() + (pb.y() - pa.y()) * t), mods)
        self.mouse("release", pb, mods)

    def test_a_drag_down_the_rows_selects_them_and_writes_nothing(self):
        self.sweep_down("translateX", "rotateX")
        self.assertEqual(self.box.selected, {"translateX", "translateY", "rotateX"})
        self.assertFalse([e for e in self.link.log if e[0] in ("write", "open")])
        self.assertEqual(self.link.log[-1][0], "sync")

    def test_a_ctrl_sweep_adds_to_the_selection(self):
        self.box.selected = {"visibility"} if "visibility" in self.box.order() else {self.box.order()[-1]}
        kept = set(self.box.selected)
        self.sweep_down("translateX", "translateY", mods=QT.QtCore.Qt.ControlModifier)
        self.assertEqual(self.box.selected, kept | {"translateX", "translateY"})

    def test_a_typed_value_lands_on_every_selected_channel(self):
        self.sweep_down("translateX", "rotateX", part="value")
        self.box.canvas.setFocus()
        ev = QT.QtGui.QKeyEvent(QT.QtCore.QEvent.KeyPress, QT.QtCore.Qt.Key_0, QT.QtCore.Qt.NoModifier, "0")
        QT.QtWidgets.QApplication.sendEvent(self.box.canvas, ev)
        editor = self.box.canvas.editor
        self.assertIsNotNone(editor)
        self.assertEqual(editor.text(), "0")
        editor.returnPressed.emit()
        self.app.processEvents()
        values = dict([e for e in self.link.log if e[0] == "write"][-1][1])
        for plug in ("IKLeg_L.translateX", "IKLeg_R.translateX", "IKLeg_L.translateY",
                     "IKLeg_L.rotateX"):
            self.assertEqual(values[plug], 0.0)

    def test_a_double_click_keeps_a_sweep_and_types_onto_all_of_it(self):
        self.sweep_down("translateX", "rotateX", part="value")
        _, parts = self.row_of("translateY")
        p = self.point(parts["value"])
        self.mouse("press", p)
        self.mouse("release", p)
        self.mouse("double", p)
        self.assertEqual(self.box.selected, {"translateX", "translateY", "rotateX"})
        editor = self.box.canvas.editor
        editor.setText("2")
        editor.returnPressed.emit()
        self.app.processEvents()
        values = dict([e for e in self.link.log if e[0] == "write"][-1][1])
        self.assertEqual(values["IKLeg_L.translateX"], 2.0)
        self.assertEqual(values["IKLeg_L.rotateX"], 2.0)

    def test_the_key_cell_keys_or_unkeys_and_the_refresh_flashes_or_breaks(self):
        _, ty = self.row_of("translateY")
        self.mouse("press", self.point(look.cell_rect(ty["mark"])))
        keys = [e for e in self.link.log if e[0] == "key"]
        self.assertEqual(keys[-1][1], ["IKLeg_L.translateY", "IKLeg_R.translateY"])
        self.assertTrue(any(i["kind"] == "set" for i in self.box.canvas.fx.items))
        _, tx = self.row_of("translateX")
        self.mouse("press", self.point(look.cell_rect(tx["mark"])))
        self.assertEqual([e for e in self.link.log if e[0] == "unkey"][-1][2], 12.0)
        self.assertTrue(any(i["kind"] == "delete" for i in self.box.canvas.fx.items))

    def test_a_bool_toggles_and_pops(self):
        _, parts = self.row_of("visibility")
        self.mouse("press", self.point(parts["value"]))
        self.mouse("release", self.point(parts["value"]))
        self.assertEqual(dict([e for e in self.link.log if e[0] == "write"][-1][1])["IKLeg_L.visibility"], 0)

    def test_time_moving_reads_the_key_cells_and_lights_nothing(self):
        self.link.frame = 24.0
        self.box.on_time()
        self.assertEqual(self.box.canvas.fx.items, [])       # no glow on keys the playhead passes
        tx = self.box.rows[self.row_of("translateX")[0]]["channel"]
        self.assertTrue(tx["on_key"])

    def test_animations_off_adds_no_effect(self):
        self.box.motion = False
        self.link.frame = 24.0
        self.box.on_time()
        self.assertEqual(self.box.canvas.fx.items, [])

    def test_a_section_opens_and_reads_its_channels(self):
        i = [n for n, r in enumerate(self.box.rows) if r["kind"] == "section"][0]
        self.mouse("press", self.point(self.box.placed[i][2]["row"]))
        self.assertIn("shapes:IKLeg_LShape", self.box.opened)
        self.assertEqual(self.box.rows[-1]["channel"]["attr"], "lineWidth")

    def test_the_menu_rows(self):
        self.box.selected = {"translateX"}
        labels = [r[0] for r in self.box.menu_rows() if r is not None]
        for want in ("Key Selected", "Breakdown Selected", "Delete Keys at 12", "Mute Selected",
                     "Lock Selected", "Select Connection", "Break Connections", "Copy Values",
                     "Maya's Channel Box"):
            self.assertIn(want, labels)
        self.box.copy_values()
        self.box.selected = {"rotateX"}
        self.box.paste_values()
        self.assertAlmostEqual(dict([e for e in self.link.log if e[0] == "write"][-1][1])["IKLeg_L.rotateX"], 4.8)

    def test_hover_eases_and_the_driver_stops_at_rest(self):
        t = [0.0]
        self.box.clock = lambda: t[0]
        _, parts = self.row_of("rotateX")
        self.mouse("move", self.point(parts["mark"]))
        self.assertTrue(self.box.timer.isActive())
        for _ in range(60):
            t[0] += 16.0
            self.box._step()
        self.assertAlmostEqual(self.box.level(("mark", self.row_of("rotateX")[0])), 1.0)
        self.assertFalse(self.box.timer.isActive())


@unittest.skipIf(QT is None, "no Qt")
class MountTests(unittest.TestCase):
    """The mount over stand-in widgets: Maya's forms move into ours and come back."""

    def setUp(self):
        self.app = QT.QtWidgets.QApplication.instance() or QT.QtWidgets.QApplication([])

    def test_mount_shows_ours_alone_and_unmount_gives_the_forms_back(self):
        """2026-10-18 «нужно убрать окно слоев»: Maya's forms kept hidden, ours alone."""
        import maya_channelbox
        from maya_sidepanel import holder
        QtWidgets = QT.QtWidgets
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        form = QtWidgets.QWidget(page)
        form.setObjectName("MainChannelsLayersLayout")
        layout.addWidget(form)
        page.show()

        class Panel(object):
            pages = {"channels": layout}

        saved = (holder.widget, maya_channelbox.enabled, maya_channelbox._start_callbacks, box_module.make)
        try:
            holder.widget = lambda name: form if name == "MainChannelsLayersLayout" else None
            maya_channelbox.enabled = lambda: True
            maya_channelbox._start_callbacks = lambda: None
            box_module.make = lambda link, ui, tokens, parent=None, motion=None: saved[3](
                FakeLink(), ui, tokens, parent, motion)
            built = maya_channelbox.mount(Panel(), [{"form": "MainChannelsLayersLayout"}])
            self.app.processEvents()
            self.assertIs(built.parentWidget(), page)
            self.assertTrue(built.isVisible())
            self.assertFalse(form.isVisible())                  # alive, hidden
            kept = page.findChild(QtWidgets.QWidget, maya_channelbox.HOLDER)
            self.assertTrue(kept.isAncestorOf(form))
            maya_channelbox.unmount()
            self.app.processEvents()
            self.assertIs(form.parentWidget(), page)
            self.assertTrue(form.isVisible())
            self.assertIsNone(maya_channelbox.current())
        finally:
            (holder.widget, maya_channelbox.enabled, maya_channelbox._start_callbacks,
             box_module.make) = saved
            page.deleteLater()


if __name__ == "__main__":
    unittest.main()
