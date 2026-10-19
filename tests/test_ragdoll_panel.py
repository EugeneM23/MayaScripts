"""maya_ragdoll.panel: the subtitle reads the rig on a selection and only the frames on a
time change (2026-10-17, the performance pass: a scrub read the scene's characters on every
frame). A fake cmds is bound to the module (the tests' pattern)."""

import unittest

from maya_ragdoll import fall as rd
from maya_ragdoll import impulse
from maya_ragdoll import panel


class FakeCmds(object):

    def __init__(self):
        self.labels = {}
        self.selection = ["|Manny_Rig_Character|Manny_Rig:Group|Manny_Rig:Main"]
        self.time = 10.0

    def text(self, name, exists=False, edit=False, label=None, **_kw):
        if exists:
            return True
        if edit:
            self.labels[name] = label
        return None

    def ls(self, selection=False, long=False, **_kw):
        return list(self.selection)

    def currentTime(self, query=False, **_kw):           # noqa: N802
        return self.time

    def getAttr(self, plug):                             # noqa: N802
        return True


class Ref(object):
    label = "Manny_Rig"
    rig = "Manny_Rig"


class TimeRefresh(unittest.TestCase):

    def setUp(self):
        self.fake = FakeCmds()
        self.saved = (panel.cmds, panel.remembered, rd._ref, rd._highlight, rd.plan.span,
                      impulse.arrows)
        panel.cmds = self.fake
        panel.remembered = lambda: {"mode": "fall", "length": 30}
        self.reads = []

        def ref(selection):
            self.reads.append(list(selection))
            return Ref()
        rd._ref = ref
        rd._highlight = lambda: None
        rd.plan.span = lambda highlight, now, length: (int(now), int(now) + length)
        impulse.arrows = lambda rig: []
        panel._DESCRIBED.clear()

    def tearDown(self):
        (panel.cmds, panel.remembered, rd._ref, rd._highlight, rd.plan.span,
         impulse.arrows) = self.saved
        panel._DESCRIBED.clear()

    def test_a_time_change_moves_the_frames_and_reads_no_rig(self):
        panel.refresh()
        self.assertEqual(self.fake.labels[panel.SUBTITLE], "Manny_Rig falls from frame 10 to 40")
        self.assertEqual(len(self.reads), 1)
        for now in (11.0, 12.0, 13.0):
            self.fake.time = now
            panel.refresh_time()
        self.assertEqual(self.fake.labels[panel.SUBTITLE], "Manny_Rig falls from frame 13 to 43")
        self.assertEqual(len(self.reads), 1)          # the rig read once, on the selection

    def test_a_time_change_before_any_selection_reads_it_once(self):
        panel.refresh_time()
        self.assertEqual(len(self.reads), 1)
        panel.refresh_time()
        self.assertEqual(len(self.reads), 1)

    def test_a_refusal_stays_until_the_selection_changes(self):
        def refuse(selection):
            self.reads.append(list(selection))
            raise rd.Refused("select a rig")
        rd._ref = refuse
        panel.refresh()
        self.fake.time = 20.0
        panel.refresh_time()
        self.assertEqual(self.fake.labels[panel.SUBTITLE], "select a rig")
        self.assertEqual(len(self.reads), 1)

    def test_the_subtitle_alone_still_reads_the_scene(self):
        self.assertEqual(panel.subtitle(), "Manny_Rig falls from frame 10 to 40")


if __name__ == "__main__":
    unittest.main()
