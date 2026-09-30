"""Two hands (2026-09-29): which bone a hand drives, the left grip as the
mirror of the right through the rig's own sockets, the grip remembered per
hand, and the Weapons section's `Hand [Right | Left]`.

Spec: docs/superpowers/specs/2026-09-29-weapon-inventory-design.md
"""

import math
import random
import unittest

import maya.api.OpenMaya as om

from maya_scenesetup import bonedrive
from maya_scenesetup import catalog

MX = om.MMatrix([-1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])
MZ = om.MMatrix(bonedrive.MODEL_MIRROR)
F = om.MMatrix(bonedrive.BEHAVIOUR_MIRROR)


def m(rotate, translate):
    return om.MMatrix(bonedrive.matrix_of(rotate, translate))


def close(a, b, tol=1e-9):
    return max(abs(x - y) for x, y in zip(a, b)) <= tol


class SideBone(unittest.TestCase):

    def test_the_right_hand_keeps_the_rows_bone(self):
        self.assertEqual(catalog.side_bone("weapon_r", "R"), "weapon_r")

    def test_the_left_hand_takes_the_twin(self):
        self.assertEqual(catalog.side_bone("weapon_r", "L"), "weapon_l")

    def test_a_left_row_answers_its_right_twin(self):
        self.assertEqual(catalog.side_bone("weapon_l", "R"), "weapon_r")

    def test_a_bone_without_a_side_is_its_own_twin(self):
        self.assertEqual(catalog.side_bone("prop", "L"), "prop")

    def test_the_sides(self):
        self.assertEqual(catalog.SIDES, ("R", "L"))


class MirrorGrip(unittest.TestCase):
    """G_l . Fr . B_l == Mz . G_r . Fr . B_r . Mx for behaviour-mirrored
    hands, whatever the sockets are."""

    def _check(self, rotate, translate, frame_rotate, s_r, s_l):
        hand_r = m((-67.77, 1.47, 1.85), (-47.77, 104.47, 15.70))
        hand_l = F * hand_r * MX
        left = bonedrive.mirror_grip(rotate, translate, frame_rotate,
                                     tuple(s_r), tuple(s_l))
        fr = m(frame_rotate, (0, 0, 0))
        w_r = m(rotate, translate) * fr * s_r * hand_r
        w_l = m(*left) * fr * s_l * hand_l
        self.assertTrue(close(w_l, MZ * w_r * MX, 1e-7),
                        (list(w_l), list(MZ * w_r * MX)))
        return left

    def test_mannys_sockets(self):
        """weapon_r at (-6.62, -1.69, 0.98) turned 1.6 deg, weapon_l at
        (0, 3.4, 0) - measured on Manny_Rig.ma 2026-09-29."""
        s_r = m((-1.3928, -0.4914, 1.5764), (-6.6212, -1.6945, 0.9776))
        s_l = m((0, 0, 0), (0, 3.4, 0))
        self._check((0, 0, 0), (0, 0, 0), (0, 0, 0), s_r, s_l)
        self._check((10, -20, 35), (1.5, -2.0, 4.0), (0, 45, 0), s_r, s_l)

    def test_the_zero_right_grip_turns_the_left_blade_round_on_manny(self):
        """At zero grip the left blade points backwards (-0.9993 measured):
        the mirror grip is a half turn there, not the identity."""
        s_r = m((-1.3928, -0.4914, 1.5764), (-6.6212, -1.6945, 0.9776))
        s_l = m((0, 0, 0), (0, 3.4, 0))
        rotate, _ = bonedrive.mirror_grip((0, 0, 0), (0, 0, 0), (0, 0, 0),
                                          tuple(s_r), tuple(s_l))
        turned = om.MEulerRotation(*[math.radians(v) for v in rotate])
        angle = turned.asQuaternion().asAxisAngle()[1]
        self.assertGreater(math.degrees(angle), 170.0)

    def test_a_pair_mirrored_through_the_thickness_needs_no_correction(self):
        """Sockets already standing as each other's mirror through the
        model's thickness: zero right grip -> zero left grip. (The Creep's
        own pair is mirrored another way: its zero grip comes out a half
        turn about the blade - the same sword for a symmetric one, measured
        in verify_inventory.py.)"""
        s_r = m((92.87, -14.60, -21.18), (-9.80, -4.61, 1.01))
        s_l = MZ * s_r * F
        rotate, translate = self._check((0, 0, 0), (0, 0, 0), (0, 0, 0),
                                        s_r, s_l)
        self.assertTrue(close(rotate, (0, 0, 0), 1e-6), rotate)
        self.assertTrue(close(translate, (0, 0, 0), 1e-6), translate)

    def test_random_grips_frames_and_sockets(self):
        rng = random.Random(7)

        def r():
            return tuple(rng.uniform(-180, 180) for _ in range(3))

        def t():
            return tuple(rng.uniform(-20, 20) for _ in range(3))
        for _ in range(20):
            self._check(r(), t(), r(), m(r(), t()), m(r(), t()))


# --------------------------------------------------------------- the grips

from maya_scenesetup import grips  # noqa: E402


class FakeVars(object):
    """optionVar as Maya answers it."""

    def __init__(self, stored=None):
        self.vars = dict(stored or {})

    def optionVar(self, **kwargs):
        if "exists" in kwargs:
            return kwargs["exists"] in self.vars
        if "query" in kwargs:
            return self.vars.get(kwargs["query"])
        if "clearArray" in kwargs:
            self.vars[kwargs["clearArray"]] = []
        if "floatValueAppend" in kwargs:
            name, value = kwargs["floatValueAppend"]
            self.vars.setdefault(name, []).append(value)
        return None


class Entry(object):
    key = "LongSword_02"
    bone = "weapon_r"
    frame = (0.0, 0.0, 0.0)


class GripMemory(unittest.TestCase):

    def setUp(self):
        real = (grips.cmds, grips.sockets, grips.bonedrive.mirror_grip)
        self.addCleanup(self._restore, real)

    def _restore(self, real):
        grips.cmds, grips.sockets, grips.bonedrive.mirror_grip = real

    def test_the_right_hand_keeps_its_old_name(self):
        self.assertEqual(grips.optionvar_name("LongSword_02"),
                         "mayaSceneSetup_offset_LongSword_02")
        self.assertEqual(grips.optionvar_name("LongSword_02", "R"),
                         "mayaSceneSetup_offset_LongSword_02")

    def test_the_left_hand_has_its_own(self):
        self.assertEqual(grips.optionvar_name("LongSword_02", "L"),
                         "mayaSceneSetup_offset_LongSword_02_L")

    def test_nothing_stored_is_none_not_zeros(self):
        grips.cmds = FakeVars()
        self.assertIsNone(grips.stored("LongSword_02", "L"))

    def test_the_legacy_name_serves_the_right_hand_only(self):
        grips.cmds = FakeVars({"mayaWeapons_offset_LongSword_02":
                               [0, 90, 0, 1, 2, 3]})
        self.assertEqual(grips.stored("LongSword_02", "R"),
                         ((0.0, 90.0, 0.0), (1.0, 2.0, 3.0)))
        self.assertIsNone(grips.stored("LongSword_02", "L"))

    def test_remember_then_stored(self):
        grips.cmds = FakeVars()
        grips.remember("LongSword_02", "L", (1, 2, 3), (4, 5, 6))
        self.assertEqual(grips.stored("LongSword_02", "L"),
                         ((1.0, 2.0, 3.0), (4.0, 5.0, 6.0)))

    def test_a_dialled_left_grip_wins(self):
        grips.cmds = FakeVars({"mayaSceneSetup_offset_LongSword_02_L":
                               [1, 2, 3, 4, 5, 6]})
        grips.sockets = lambda root, bone="weapon_r": self.fail("no mirror")
        self.assertEqual(grips.for_hand(Entry(), "L", "|root"),
                         ((1.0, 2.0, 3.0), (4.0, 5.0, 6.0)))

    def test_an_undialled_left_grip_is_the_right_ones_mirror(self):
        grips.cmds = FakeVars({"mayaSceneSetup_offset_LongSword_02":
                               [0, 0, 0, 1, 0, 0]})
        seen = []
        grips.sockets = lambda root, bone="weapon_r": ("SR", "SL")
        grips.bonedrive.mirror_grip = (
            lambda *a: seen.append(a) or ((0, 0, 180), (-1, 0, 0)))
        self.assertEqual(grips.for_hand(Entry(), "L", "|root"),
                         ((0, 0, 180), (-1, 0, 0)))
        # the node's frame, not the row's: the socket turn composed in
        self.assertEqual(seen, [((0.0, 0.0, 0.0), (1.0, 0.0, 0.0),
                                 (90.0, 0.0, 0.0), "SR", "SL")])

    def test_the_right_hand_never_mirrors(self):
        grips.cmds = FakeVars()
        grips.sockets = lambda root, bone="weapon_r": self.fail("no mirror")
        self.assertEqual(grips.for_hand(Entry(), "R", "|root"), grips.ZERO)

    def test_no_sockets_means_zeros(self):
        grips.cmds = FakeVars()
        grips.sockets = lambda root, bone="weapon_r": None
        self.assertEqual(grips.for_hand(Entry(), "L", "|root"), grips.ZERO)

    def test_the_window_delegates(self):
        from maya_scenesetup import window
        self.assertEqual(window.optionvar_name("X"), grips.optionvar_name("X"))
        self.assertIs(window.pack_offsets, grips.pack)
        self.assertIs(window.unpack_offsets, grips.unpack)


# ------------------------------------------------------ the Weapons section

from tests.uifakes import FakeUiCmds  # noqa: E402


class HandCmds(FakeUiCmds):
    """The UI fake plus radio collections (as in the Connections tests)."""

    def __init__(self):
        FakeUiCmds.__init__(self)
        self.selected, self.owner, self.on, self._current = {}, {}, {}, None

    def iconTextRadioCollection(self, name=None, **kwargs):
        if kwargs.get("query"):
            return self.selected.get(name)
        self.selected[name] = None
        self._current = name
        return name

    def iconTextRadioButton(self, name=None, **kwargs):
        if kwargs.get("exists"):
            return name in self.owner
        if kwargs.get("edit"):
            if kwargs.get("select"):
                self.selected[self.owner[name]] = name
            return name
        self.owner[name] = self._current
        self.on[name] = kwargs.get("onCommand")
        if kwargs.get("select"):
            self.selected[self._current] = name
        self.children.append(name)
        self.calls.append(("iconTextRadioButton", (name,), kwargs))
        return name


class HandRow(unittest.TestCase):

    def setUp(self):
        from maya_scenesetup import window
        self.window = window
        self.fake = HandCmds()
        real = (window.cmds, window.refresh, window.skeleton.resolve_bone,
                window._bound_root)
        window.cmds = self.fake
        self.addCleanup(self._restore, real)

    def _restore(self, real):
        (self.window.cmds, self.window.refresh,
         self.window.skeleton.resolve_bone, self.window._bound_root) = real

    def test_the_segments_are_right_and_left(self):
        self.window._hand_row()
        labels = [c[2]["label"] for c in self.fake.calls
                  if c[0] == "iconTextRadioButton"]
        self.assertEqual(labels, ["Right", "Left"])

    def test_the_right_hand_is_the_default(self):
        self.window._hand_row()
        self.assertEqual(self.window.side(), "R")

    def test_a_remembered_left_hand_opens_on_left(self):
        self.fake.optionvars[self.window._HAND_OPTIONVAR] = "L"
        self.window._hand_row()
        self.assertEqual(self.window.side(), "L")

    def test_picking_a_hand_remembers_it_and_refreshes(self):
        self.window._hand_row()
        refreshed = []
        self.window.refresh = lambda: refreshed.append(1)
        self.fake.selected[self.window._HAND] = self.window.hand_segment("L")
        self.fake.on[self.window.hand_segment("L")]()
        self.assertEqual(self.fake.optionvars[self.window._HAND_OPTIONVAR], "L")
        self.assertEqual(refreshed, [1])

    def test_the_left_hand_asks_for_weapon_l(self):
        asked = []
        self.fake.selected[self.window._HAND] = self.window.hand_segment("L")
        self.window.skeleton.resolve_bone = (
            lambda root, name: asked.append(name))
        self.window._bound_root = lambda: "|root"
        self.window._attached(catalog.by_key("LongSword_02"))
        self.assertEqual(asked, ["weapon_l"])

    def test_the_right_hand_asks_for_the_rows_bone(self):
        asked = []
        self.window.skeleton.resolve_bone = (
            lambda root, name: asked.append(name))
        self.window._bound_root = lambda: "|root"
        self.window._attached(catalog.by_key("LongSword_02"))
        self.assertEqual(asked, ["weapon_r"])

    def test_the_follow_refusal_names_the_hand_and_the_weapon(self):
        text = self.window.hand_follows_message("L", "Long Sword 02")
        self.assertIn("left hand follows the Long Sword 02", text)
        self.assertIn("Connections", text)

    def test_the_panel_builds_the_hand_row(self):
        import inspect
        self.assertIn("_hand_row()",
                      inspect.getsource(self.window.build_weapons_panel))
