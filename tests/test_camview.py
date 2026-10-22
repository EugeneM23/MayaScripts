"""A character's own camera puts it in 1P (maya_camview, 2026-10-22)."""

import contextlib
import unittest

import maya_camview as camview

A = "Manny_Rig:Main.view"
B = "Orc_D_Rig:Main.view"


class Plan(unittest.TestCase):
    def test_a_rig_shown_in_3p_goes_to_1p(self):
        first, third, ours = camview.plan({A}, {A: 0}, set())
        self.assertEqual((first, third, ours), ([A], [], {A}))

    def test_a_rig_already_in_1p_by_hand_is_not_taken_over(self):
        first, third, ours = camview.plan({A}, {A: 1}, set())
        self.assertEqual((first, third, ours), ([], [], set()))

    def test_leaving_puts_back_only_what_the_watch_switched(self):
        first, third, ours = camview.plan(set(), {A: 1, B: 1}, {A})
        self.assertEqual((first, third, ours), ([], [A], set()))

    def test_still_shown_stays_ours(self):
        self.assertEqual(camview.plan({A}, {A: 1}, {A}), ([], [], {A}))

    def test_a_plug_that_cannot_be_written_is_left_alone(self):
        self.assertEqual(camview.plan({A}, {A: None}, set()), ([], [], set()))

    def test_put_back_to_3p_by_hand_while_shown_is_not_fought(self):
        #  the animator switched it back while looking through: kept as theirs
        self.assertEqual(camview.plan({A}, {A: 0}, {A}), ([], [], {A}))


class FakeCmds(object):
    def __init__(self):
        self.values = {}

    def setAttr(self, plug, value):
        self.values[plug] = value


class Tick(unittest.TestCase):
    def setUp(self):
        self.cmds = FakeCmds()
        self.cmds.values = {A: 0, B: 0}
        self.panels = {"modelPanel4": "|persp"}
        owners = {"|Manny_Rig:Camera_ctrl|Manny_Rig:SceneSetup_camera": A,
                  "|Orc_D_Rig:Camera_ctrl|Orc_D_Rig:SceneSetup_camera": B}
        saved = {}
        patches = {
            "_cmds": lambda: self.cmds,
            "_panels": lambda: list(self.panels),
            "_shown_camera": lambda panel: self.panels[panel],
            "owner_plug": lambda camera: owners.get(camera, ""),
            "_value": lambda plug: self.cmds.values.get(plug),
            "_quiet": contextlib.nullcontext,
        }
        for name, fn in patches.items():
            saved[name] = getattr(camview, name)
            setattr(camview, name, fn)
        self.addCleanup(lambda: [setattr(camview, n, f) for n, f in saved.items()])
        st = camview._state()
        old = dict(st)
        st.update(timer=None, ours=set(), owners={})
        self.addCleanup(lambda: st.update(old))

    def test_into_the_camera_and_out_again(self):
        self.panels["modelPanel4"] = "|Manny_Rig:Camera_ctrl|Manny_Rig:SceneSetup_camera"
        self.assertEqual(camview.tick(), ([A], []))
        self.assertEqual(self.cmds.values[A], 1)
        self.assertEqual(camview.tick(), ([], []))
        self.panels["modelPanel4"] = "|persp"
        self.assertEqual(camview.tick(), ([], [A]))
        self.assertEqual(self.cmds.values, {A: 0, B: 0})

    def test_from_one_character_s_camera_to_another_s(self):
        self.panels["modelPanel4"] = "|Manny_Rig:Camera_ctrl|Manny_Rig:SceneSetup_camera"
        camview.tick()
        self.panels["modelPanel4"] = "|Orc_D_Rig:Camera_ctrl|Orc_D_Rig:SceneSetup_camera"
        self.assertEqual(camview.tick(), ([B], [A]))
        self.assertEqual(self.cmds.values, {A: 0, B: 1})

    def test_a_second_viewport_on_it_keeps_it_in_1p(self):
        cam = "|Manny_Rig:Camera_ctrl|Manny_Rig:SceneSetup_camera"
        self.panels = {"modelPanel1": cam, "modelPanel4": cam}
        camview.tick()
        self.panels["modelPanel4"] = "|persp"
        self.assertEqual(camview.tick(), ([], []))
        self.assertEqual(self.cmds.values[A], 1)

    def test_a_camera_of_no_rig_switches_nothing(self):
        self.panels["modelPanel4"] = "|shotCam"
        self.assertEqual(camview.tick(), ([], []))

    def test_switching_off_puts_its_rigs_back(self):
        self.panels["modelPanel4"] = "|Manny_Rig:Camera_ctrl|Manny_Rig:SceneSetup_camera"
        camview.tick()
        camview.unwatch()
        self.assertEqual(self.cmds.values[A], 0)


if __name__ == "__main__":
    unittest.main()
