"""The Override pick key (2026-11-02): one more pick in the weapon's tab.

Spec: docs/superpowers/specs/2026-11-02-connections-2h-and-override-design.md
"""
import unittest

from maya_scenesetup import pending


class OverrideKey(unittest.TestCase):
    def test_it_belongs_to_the_weapon_tab(self):
        picks = {pending.OVERRIDE: (True, 1.0, 1.0, 80.0),
                 pending.CAMERA: "Main"}
        self.assertEqual(pending.of_tab(picks, "weapon"),
                         {pending.OVERRIDE: (True, 1.0, 1.0, 80.0)})

    def test_it_is_not_the_camera_tab_s(self):
        picks = {pending.OVERRIDE: (True, 1.0, 1.0, 80.0)}
        self.assertEqual(pending.of_tab(picks, "camera"), {})

    def test_it_is_one_change(self):
        self.assertEqual(pending.count({pending.OVERRIDE: (True, 1.0, 1.0, 80.0)}), 1)

    def test_it_sorts_after_the_aim(self):
        text = pending.text({pending.OVERRIDE: (True, 1.0, 1.0, 80.0),
                             pending.AIM: True})
        self.assertLess(text.index("aim"), text.index("override"))

    def test_on_says_its_numbers(self):
        self.assertEqual(pending.phrase(pending.OVERRIDE, (True, 1.0, 0.5, 80.0)),
                         "the weapon's override on: 1 / 0.5 / 80 ms")

    def test_off_says_off(self):
        self.assertEqual(pending.phrase(pending.OVERRIDE, (False, 1.0, 1.0, 80.0)),
                         "the weapon's override off")

    def test_a_pick_that_is_the_state_is_dropped(self):
        state = (False, 1.0, 1.0, 80.0)
        self.assertEqual(pending.record({}, pending.OVERRIDE, state, state), {})
