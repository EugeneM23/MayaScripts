"""Camera flight's flights (2026-10-21): the state machine over a fake scene and a fake clock."""

import unittest

import maya_camflight
import maya_camflight_rules as rules


def view(x, coi=400.0, tan=0.3):
    m = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, x, 100, coi, 1]
    n = 0.1
    return rules.view_of(m, (-tan * 1.6 * n, tan * 1.6 * n, -tan * n, tan * n), n, 10000.0,
                         coi, False)


class Clock(object):
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class FakeScene(object):
    SUB = "|skeldarCameraFlight"

    def __init__(self):
        self.cams = {"|persp": view(0.0), "|shot": view(300.0, coi=200.0, tan=0.5),
                     "|third": view(-500.0)}
        self.panels = {"modelPanel4": "|persp"}
        self.on = True
        self.made = 0
        self.dropped = []
        self.placed = []
        self.refreshed = 0
        self.dirty = False
        self.cleaned = 0
        self.fail_place = False
        self.fail_make = False
        self.sub_alive = False
        self.swept = 0

    def sweep(self):
        self.swept += 1
        self.cams.pop(self.SUB, None)

    def is_sub(self, node):
        return node == self.SUB

    def animated(self):
        return self.on

    def view(self, cam, aspect):
        return self.cams.get(cam)

    def shown(self, panel):
        return self.panels.get(panel, "")

    def look(self, panel, cam):
        self.panels[panel] = cam

    def aspect(self, panel):
        return 1.6

    def make_sub(self):
        if self.fail_make:
            raise RuntimeError("no camera")
        self.made += 1
        self.sub_alive = True
        return self.SUB

    def place(self, sub, shot, aspect):
        if self.fail_place:
            raise RuntimeError("locked")
        self.placed.append(shot)

    def drop(self, sub):
        self.dropped.append(sub)
        self.sub_alive = False

    def exists(self, node):
        return node in self.cams or (node == self.SUB and self.sub_alive)

    def panel_alive(self, panel):
        return panel in self.panels

    def refresh(self, panel):
        self.refreshed += 1

    def modified(self):
        return self.dirty

    def set_clean(self):
        self.cleaned += 1


def close(test, a, b, places=6):
    for x, y in zip(a, b):
        test.assertAlmostEqual(x, y, places=places)


class Flights(unittest.TestCase):
    def setUp(self):
        self.scene = FakeScene()
        self.clock = Clock()
        self.flights = maya_camflight.Flights(self.scene, self.clock, 0.3)

    def fly(self, target="|shot"):
        return self.flights.fly("modelPanel4", target)

    def at(self, seconds):
        self.clock.now = seconds
        return self.flights.tick()

    def test_off_switches_at_once(self):
        self.scene.on = False
        self.assertFalse(self.fly())
        self.assertEqual(self.scene.made, 0)

    def test_the_camera_already_shown_is_no_flight(self):
        self.assertFalse(self.fly("|persp"))

    def test_from_or_to_something_not_a_camera_is_at_once(self):
        self.assertFalse(self.fly("|light"))
        self.scene.panels["modelPanel4"] = "|light"
        self.assertFalse(self.fly("|shot"))
        self.assertEqual(self.scene.made, 0)

    def test_a_flight_starts_on_the_view_shown_and_ends_on_the_target(self):
        self.assertTrue(self.fly())
        self.assertEqual(self.scene.panels["modelPanel4"], FakeScene.SUB)
        close(self, self.scene.placed[0].matrix, rules.shot(self.scene.cams["|persp"]).matrix)
        self.assertTrue(self.at(0.15))
        mid = rules.shot(rules.blend(self.scene.cams["|persp"], self.scene.cams["|shot"],
                                     rules.ease(0.5)))
        close(self, self.scene.placed[-1].matrix, mid.matrix)
        self.assertGreater(self.scene.refreshed, 0)
        self.assertFalse(self.at(0.3))
        self.assertEqual(self.scene.panels["modelPanel4"], "|shot")
        self.assertEqual(self.scene.dropped, [FakeScene.SUB])
        self.assertIsNone(self.flights.target_of("modelPanel4"))

    def test_the_ends_are_read_live(self):
        self.fly()
        self.scene.cams["|shot"] = view(900.0)
        self.at(0.29999)
        close(self, self.scene.placed[-1].matrix[12:15], rules.shot(view(900.0)).matrix[12:15],
              places=2)

    def test_a_new_target_mid_flight_starts_from_where_the_substitute_stands(self):
        self.fly()
        self.at(0.15)
        here = self.scene.placed[-1]
        self.assertTrue(self.fly("|third"))
        self.assertEqual(self.scene.made, 1)
        self.at(0.15)                                  # the new flight's first tick
        close(self, self.scene.placed[-1].matrix, here.matrix)
        self.assertTrue(self.at(0.3))
        self.assertFalse(self.at(0.45))
        self.assertEqual(self.scene.panels["modelPanel4"], "|third")
        self.assertEqual(self.scene.dropped, [FakeScene.SUB])

    def test_the_same_target_again_keeps_flying(self):
        self.fly()
        self.at(0.2)
        self.assertTrue(self.fly())
        self.assertFalse(self.at(0.3))                 # not started again

    def test_a_target_gone_mid_flight_goes_back_to_the_source(self):
        self.fly()
        del self.scene.cams["|shot"]
        self.assertFalse(self.at(0.1))
        self.assertEqual(self.scene.panels["modelPanel4"], "|persp")
        self.assertEqual(self.scene.dropped, [FakeScene.SUB])

    def test_a_failure_on_the_way_switches_at_once(self):
        self.fly()
        self.scene.fail_place = True
        self.assertFalse(self.at(0.1))
        self.assertEqual(self.scene.panels["modelPanel4"], "|shot")
        self.assertEqual(self.scene.dropped, [FakeScene.SUB])

    def test_a_failure_to_start_leaves_nothing(self):
        self.scene.fail_make = True
        self.assertFalse(self.fly())
        self.assertEqual(self.scene.panels["modelPanel4"], "|persp")
        self.scene.fail_make, self.scene.fail_place = False, True
        self.assertFalse(self.fly())
        self.assertEqual(self.scene.panels["modelPanel4"], "|persp")
        self.assertEqual(self.scene.dropped, [FakeScene.SUB])

    def test_a_clean_scene_is_left_clean(self):
        self.fly()
        self.at(0.3)
        self.assertEqual(self.scene.cleaned, 1)

    def test_a_modified_scene_stays_modified(self):
        self.scene.dirty = True
        self.fly()
        self.at(0.3)
        self.assertEqual(self.scene.cleaned, 0)

    def test_the_first_flight_sweeps_old_substitutes_away(self):
        self.fly()
        self.fly("|third")
        self.assertEqual(self.scene.swept, 1)
        self.at(0.3)
        self.fly("|persp")
        self.assertEqual(self.scene.swept, 2)

    def test_a_stale_substitute_shown_is_flown_from_before_it_is_swept(self):
        stale = view(-200.0)
        self.scene.cams[FakeScene.SUB] = stale
        self.scene.panels["modelPanel4"] = FakeScene.SUB
        self.assertTrue(self.fly())
        self.assertEqual(self.scene.swept, 1)
        close(self, self.scene.placed[0].matrix, rules.shot(stale).matrix)
        self.assertFalse(self.at(0.3))
        self.assertEqual(self.scene.panels["modelPanel4"], "|shot")

    def test_the_target_is_known_mid_flight(self):
        self.fly()
        self.assertEqual(self.flights.target_of("modelPanel4"), "|shot")

    def test_stop_all_lands_on_the_target(self):
        self.fly()
        self.flights.stop_all()
        self.assertEqual(self.scene.panels["modelPanel4"], "|shot")
        self.assertEqual(self.scene.dropped, [FakeScene.SUB])

    def test_a_panel_gone_drops_the_substitute(self):
        self.fly()
        del self.scene.panels["modelPanel4"]
        self.assertFalse(self.at(0.1))
        self.assertEqual(self.scene.dropped, [FakeScene.SUB])


class Look(unittest.TestCase):
    def test_flying_is_said_true_only_when_a_flight_took_it(self):
        saved = maya_camflight.flights
        scene = FakeScene()
        flights = maya_camflight.Flights(scene, Clock(), 0.3)
        maya_camflight.flights = lambda: flights
        started = []
        saved_drive = maya_camflight._drive
        maya_camflight._drive = lambda: started.append(1)
        try:
            self.assertTrue(maya_camflight.fly("modelPanel4", "|shot"))
            self.assertEqual(started, [1])
            scene.on = False
            self.assertFalse(maya_camflight.fly("modelPanel4", "|third"))
        finally:
            maya_camflight.flights = saved
            maya_camflight._drive = saved_drive


if __name__ == "__main__":
    unittest.main()
