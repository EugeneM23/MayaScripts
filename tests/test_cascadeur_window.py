"""The Cascadeur bridge window's model (QML view over it). No Cascadeur, no
Unreal, no network, and no QtWidgets: the view is QML and never created here."""

import unittest

from PySide6 import QtCore  # noqa: F401  (the module must import under mayapy)

from skeldar_cascadeur import window
from skeldar_cascadeur.actions import ExportPlan
from maya_uebridge import records


def clip(name):
    return records.AnimRecord(name=name, package="/Game/" + name, skeleton="",
                              frames=10, length=0.3, fps=30.0, source="unreal",
                              path="", clip="", fmt="")


class FakeBridge(object):
    def __init__(self):
        self.records = [clip("A_Jump"), clip("B_Walk")]
        self.target = None
        self.calls = []
        self.plan_refusal = ""

    def refresh(self, project=None):
        self.calls.append("refresh")
        return "2 animation(s) in Unreal"

    def import_clips(self, picked, project=None):
        self.calls.append(("import", [r.name for r in picked]))
        return "done"

    def plan_export(self, record=None):
        self.calls.append(("plan", record.name if record else None))
        if self.plan_refusal:
            return self.plan_refusal, None
        return "", ExportPlan(record, "x.uasset", False, "Overwrite A?")

    def run_export(self, plan, project=None):
        self.calls.append(("run", plan.record.name if plan.record else None))
        return "reimported and saved"

    def send_to_shared(self, typed_name, author, project=None):
        self.calls.append(("send", typed_name, author))
        return "sent"


class FakeConfirm(object):
    def __init__(self, answer=True):
        self.asked = []
        self.answer = answer

    def __call__(self, text, on_yes):
        self.asked.append(text)
        if self.answer:
            on_yes()


class View(unittest.TestCase):
    """view.qml must parse and bind to the model's names without a window."""

    def test_view_loads_with_the_bridge_context(self):
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6 import QtGui, QtQml
        app = QtGui.QGuiApplication.instance() or QtGui.QGuiApplication([])
        engine = QtQml.QQmlEngine()
        engine.rootContext().setContextProperty("bridge", window.BridgeModel(
            FakeBridge(), FakeConfirm()))
        component = QtQml.QQmlComponent(engine)
        component.loadUrl(QtCore.QUrl.fromLocalFile(window.VIEW_FILE))
        errors = [e.toString() for e in component.errors()]
        self.assertEqual(errors, [])
        self.assertEqual(component.status(), QtQml.QQmlComponent.Status.Ready)


class Model(unittest.TestCase):

    def make(self, bridge=None, confirm=None):
        bridge = bridge or FakeBridge()
        confirm = confirm or FakeConfirm()
        return window.BridgeModel(bridge, confirm), bridge, confirm

    def test_lists_every_clip(self):
        model, _, _ = self.make()
        self.assertEqual(list(model.clipNames), ["A_Jump", "B_Walk"])

    def test_filter_narrows_the_list(self):
        model, _, _ = self.make()
        model.setFilter("walk")
        self.assertEqual(list(model.clipNames), ["B_Walk"])

    def test_import_takes_the_picked_names(self):
        model, bridge, _ = self.make()
        model.pick(["A_Jump"])
        model.importPicked()
        self.assertIn(("import", ["A_Jump"]), bridge.calls)
        self.assertEqual(model.statusText, "done")

    def test_import_with_nothing_picked_says_so(self):
        model, bridge, _ = self.make()
        model.importPicked()
        self.assertEqual(model.statusText, "select one or more animations first")
        self.assertEqual(bridge.calls, [])

    def test_export_asks_before_it_writes(self):
        model, bridge, confirm = self.make()
        model.pick(["B_Walk"])
        model.exportPicked()
        self.assertEqual(confirm.asked, ["Overwrite A?"])
        self.assertIn(("run", "B_Walk"), bridge.calls)
        self.assertEqual(model.statusText, "reimported and saved")

    def test_a_declined_export_writes_nothing(self):
        bridge = FakeBridge()
        model, _, _ = self.make(bridge=bridge, confirm=FakeConfirm(answer=False))
        model.pick(["B_Walk"])
        model.exportPicked()
        self.assertNotIn(("run", "B_Walk"), bridge.calls)

    def test_an_export_refusal_is_shown_and_not_asked(self):
        bridge = FakeBridge()
        bridge.plan_refusal = "no Unreal animation"
        model, _, confirm = self.make(bridge=bridge)
        model.exportPicked()
        self.assertEqual(model.statusText, "no Unreal animation")
        self.assertEqual(confirm.asked, [])

    def test_send_passes_name_and_author(self):
        model, bridge, _ = self.make()
        model.sendPicked("attack", "Yevhen")
        self.assertIn(("send", "attack", "Yevhen"), bridge.calls)

    def test_send_falls_back_to_the_author_set_in_the_view(self):
        model, bridge, _ = self.make()
        model.setAuthor("Yevhen")
        model.sendPicked("attack", "")
        self.assertIn(("send", "attack", "Yevhen"), bridge.calls)

    def test_refresh_reports_the_count(self):
        model, _, _ = self.make()
        model.refresh()
        self.assertIn("2", model.statusText)


if __name__ == "__main__":
    unittest.main()
