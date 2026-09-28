"""The pure half of maya_vpstudio, plus the state machinery on a fake cmds.

Everything here runs without a Maya session. The claims that matter most:
the studio is measured from the subject rather than tabulated in
centimetres, a second press carries the FIRST press's memory of the
animator's viewport forward (or Restore hands back our own settings), and
nothing is ever resolved by name.
"""

import json
import math
import unittest

import maya_vpstudio as vp

from tests.uifakes import FakeUiCmds


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


BOX = (-40.0, 0.0, -40.0, 40.0, 180.0, 40.0)


class TestOptions(unittest.TestCase):

    def test_the_defaults_are_the_animator_s_ask(self):
        opts = vp.merged_options(None)
        for key in ("floor", "shadows", "ao", "motion_blur", "anti_alias"):
            self.assertTrue(opts[key], key)

    def test_an_override_wins(self):
        self.assertFalse(vp.merged_options({"floor": False})["floor"])

    def test_a_typo_never_becomes_an_option(self):
        self.assertNotIn("shadow", vp.merged_options({"shadow": False}))

    def test_the_rest_stay_at_their_defaults(self):
        opts = vp.merged_options({"quality": "Fast"})
        self.assertEqual(opts["quality"], "Fast")
        self.assertTrue(opts["ao"])

    def test_clean_view_is_off_by_default(self):
        """A press must never take the animator's controls away
        unasked -- the safe direction of failure is a juicy picture with
        the rig still visible."""
        self.assertFalse(vp.DEFAULTS["clean"])

    def test_the_three_named_qualities(self):
        self.assertEqual(vp.QUALITY_ORDER, ("Fast", "Good", "Beauty"))

    def test_an_unknown_quality_is_good(self):
        self.assertEqual(vp.quality_of("nonsense"), vp.quality_of("Good"))

    def test_quality_costs_more_as_it_climbs(self):
        for key in ("samples", "ao_samples", "blur_samples", "dmap"):
            values = [vp.quality_of(name)[key] for name in vp.QUALITY_ORDER]
            self.assertEqual(values, sorted(values), key)


class TestSubject(unittest.TestCase):

    def test_the_union_encloses_both(self):
        self.assertEqual(
            vp.bbox_union([(0, 0, 0, 1, 1, 1), (-5, -5, -5, 0, 0, 0)]),
            (-5, -5, -5, 1, 1, 1))

    def test_a_union_of_nothing_is_nothing(self):
        self.assertIsNone(vp.bbox_union([]))
        self.assertIsNone(vp.bbox_union([None, None]))

    def test_the_centre_is_the_middle(self):
        frame = vp.subject_frame(BOX)
        self.assertAlmostEqual(frame["centre"][0], 0.0)
        self.assertAlmostEqual(frame["centre"][1], 90.0)

    def test_the_height_and_the_floor(self):
        frame = vp.subject_frame(BOX)
        self.assertAlmostEqual(frame["height"], 180.0)
        self.assertAlmostEqual(frame["floor_y"], 0.0)

    def test_the_radius_is_half_the_diagonal(self):
        """Half the diagonal is the one measure that does not collapse on
        a flat subject: a floor plane has no height and a lying prop has
        no depth."""
        frame = vp.subject_frame(BOX)
        self.assertAlmostEqual(
            frame["radius"],
            0.5 * math.sqrt(80 ** 2 + 180 ** 2 + 80 ** 2), places=9)

    def test_a_flat_subject_still_has_a_radius(self):
        frame = vp.subject_frame((-100.0, 0.0, -100.0, 100.0, 0.0, 100.0))
        self.assertGreater(frame["radius"], 100.0)

    def test_a_single_point_gets_a_body(self):
        frame = vp.subject_frame((5.0, 5.0, 5.0, 5.0, 5.0, 5.0))
        self.assertGreaterEqual(frame["radius"], 1.0)
        self.assertGreaterEqual(frame["height"], 1.0)

    def test_an_empty_scene_is_lit_as_a_standing_human(self):
        """Guessing beats refusing: the animator is usually about to
        import a character into the light they just set up."""
        frame = vp.subject_frame(None)
        self.assertAlmostEqual(frame["height"], 180.0)


class TestPlacement(unittest.TestCase):

    def test_azimuth_zero_looks_down_plus_z(self):
        x, y, z = vp.spherical((0.0, 0.0, 0.0), 10.0, 0.0, 0.0)
        self.assertAlmostEqual(x, 0.0)
        self.assertAlmostEqual(y, 0.0)
        self.assertAlmostEqual(z, 10.0)

    def test_ninety_degrees_is_plus_x(self):
        x, _y, z = vp.spherical((0.0, 0.0, 0.0), 10.0, 90.0, 0.0)
        self.assertAlmostEqual(x, 10.0)
        self.assertAlmostEqual(z, 0.0, places=9)

    def test_elevation_lifts_it(self):
        _x, y, _z = vp.spherical((0.0, 0.0, 0.0), 10.0, 0.0, 90.0)
        self.assertAlmostEqual(y, 10.0)

    def test_the_distance_is_kept(self):
        point = vp.spherical((3.0, 4.0, 5.0), 12.0, 37.0, 21.0)
        self.assertAlmostEqual(
            math.sqrt(sum((point[i] - (3.0, 4.0, 5.0)[i]) ** 2
                          for i in range(3))), 12.0, places=9)

    def test_the_camera_decides_the_azimuth(self):
        """Three-point lighting is defined against the VIEW, which is why
        no part of this tool has to guess which way a character faces."""
        self.assertAlmostEqual(
            vp.studio_azimuth((100.0, 0.0, 0.0), (0.0, 0.0, 0.0)), 90.0)
        self.assertAlmostEqual(
            vp.studio_azimuth((0.0, 0.0, -100.0), (0.0, 0.0, 0.0)), 180.0)

    def test_straight_overhead_falls_back_to_zero(self):
        self.assertEqual(
            vp.studio_azimuth((0.0, 500.0, 0.0), (0.0, 0.0, 0.0)), 0.0)

    def test_no_camera_falls_back_to_zero(self):
        self.assertEqual(vp.studio_azimuth(None, (0.0, 0.0, 0.0)), 0.0)

    def test_a_wider_subject_wants_a_wider_cone(self):
        self.assertGreater(vp.cone_angle(200.0, 500.0),
                           vp.cone_angle(100.0, 500.0))

    def test_a_further_light_wants_a_narrower_cone(self):
        self.assertLess(vp.cone_angle(100.0, 1000.0),
                        vp.cone_angle(100.0, 300.0))

    def test_the_cone_never_closes_or_wraps(self):
        for radius, distance in ((0.0, 500.0), (1e6, 1.0), (10.0, 1e-9)):
            angle = vp.cone_angle(radius, distance)
            self.assertGreaterEqual(angle, 8.0)
            self.assertLessEqual(angle, 160.0)


class TestLookAt(unittest.TestCase):
    """A light shines down its own -Z, so the third row is the negative of
    the direction we want lit. Handing Maya a matrix keeps euler
    extraction -- and the rotate order -- out of this module."""

    def test_minus_z_points_at_the_target(self):
        m = vp.look_at_matrix((0.0, 100.0, 0.0), (0.0, 0.0, 0.0))
        self.assertAlmostEqual(dot((m[8], m[9], m[10]), (0.0, 1.0, 0.0)),
                               1.0, places=9)

    def test_it_aims_from_anywhere(self):
        pos, target = (300.0, 200.0, 100.0), (0.0, 50.0, 0.0)
        m = vp.look_at_matrix(pos, target)
        want = vp.normalise(tuple(pos[i] - target[i] for i in range(3)))
        self.assertAlmostEqual(dot((m[8], m[9], m[10]), want), 1.0,
                               places=9)

    def test_the_rows_are_orthonormal(self):
        m = vp.look_at_matrix((123.0, -45.0, 67.0), (-8.0, 9.0, 10.0))
        rows = [(m[0], m[1], m[2]), (m[4], m[5], m[6]), (m[8], m[9], m[10])]
        for row in rows:
            self.assertAlmostEqual(dot(row, row), 1.0, places=9)
        self.assertAlmostEqual(dot(rows[0], rows[1]), 0.0, places=9)
        self.assertAlmostEqual(dot(rows[1], rows[2]), 0.0, places=9)
        self.assertAlmostEqual(dot(rows[0], rows[2]), 0.0, places=9)

    def test_it_is_right_handed(self):
        m = vp.look_at_matrix((10.0, 20.0, 30.0), (0.0, 0.0, 0.0))
        rows = [(m[0], m[1], m[2]), (m[4], m[5], m[6]), (m[8], m[9], m[10])]
        self.assertAlmostEqual(dot(vp.cross(rows[0], rows[1]), rows[2]),
                               1.0, places=9)

    def test_straight_down_does_not_divide_by_zero(self):
        """Up parallel to the aim leaves the cross product undefined; +Z
        is the conventional escape."""
        m = vp.look_at_matrix((0.0, 500.0, 0.0), (0.0, 0.0, 0.0))
        rows = [(m[0], m[1], m[2]), (m[4], m[5], m[6]), (m[8], m[9], m[10])]
        for row in rows:
            self.assertAlmostEqual(dot(row, row), 1.0, places=9)

    def test_a_zero_length_aim_is_survivable(self):
        m = vp.look_at_matrix((1.0, 1.0, 1.0), (1.0, 1.0, 1.0))
        self.assertEqual(len(m), 16)

    def test_the_translation_is_the_position(self):
        m = vp.look_at_matrix((7.0, 8.0, 9.0), (0.0, 0.0, 0.0))
        self.assertEqual([m[12], m[13], m[14], m[15]], [7.0, 8.0, 9.0, 1.0])


class TestLightPlan(unittest.TestCase):

    def plan(self, options=None):
        return vp.light_plan(vp.subject_frame(BOX), 0.0, options)

    def test_five_lights(self):
        self.assertEqual(len(self.plan()), 5)
        self.assertEqual(vp.light_names("Studio"),
                         ("key", "fill", "rim", "bounce", "ambient"))

    def test_they_are_named_for_the_outliner(self):
        names = [e["name"] for e in self.plan()]
        self.assertEqual(names[0], "VPStudio_key")
        self.assertTrue(all(n.startswith("VPStudio_") for n in names))

    def test_only_the_key_casts(self):
        """One shadow caster reads as one sun. Two make a mess of the
        floor and cost a second depth map for it."""
        casting = [e["name"] for e in self.plan() if e["shadow"]]
        self.assertEqual(casting, ["VPStudio_key"])

    def test_shadows_off_means_nothing_casts(self):
        self.assertFalse(any(e["shadow"]
                             for e in self.plan({"shadows": False})))

    def test_the_spots_carry_the_shadows(self):
        """A spot's depth map covers its cone, so the resolution lands on
        the subject; a directional with auto-focus spends it on the
        floor."""
        for entry in self.plan():
            if entry["shadow"]:
                self.assertEqual(entry["kind"], "spot")

    def test_the_fill_and_bounce_reach_the_whole_floor(self):
        kinds = {e["name"]: e["kind"] for e in self.plan()}
        self.assertEqual(kinds["VPStudio_fill"], "directional")
        self.assertEqual(kinds["VPStudio_bounce"], "directional")

    def test_only_the_key_and_rim_put_a_highlight_on_the_skin(self):
        spec = {e["name"]: e["specular"] for e in self.plan()}
        self.assertTrue(spec["VPStudio_key"])
        self.assertTrue(spec["VPStudio_rim"])
        self.assertFalse(spec["VPStudio_fill"])
        self.assertFalse(spec["VPStudio_bounce"])

    def test_brightness_scales_every_light(self):
        base = {e["name"]: e["intensity"] for e in self.plan()}
        twice = {e["name"]: e["intensity"]
                 for e in self.plan({"brightness": 2.0})}
        for name, value in base.items():
            self.assertAlmostEqual(twice[name], 2.0 * value, places=9)

    def test_a_negative_brightness_cannot_invert_the_light(self):
        for entry in self.plan({"brightness": -3.0}):
            self.assertGreaterEqual(entry["intensity"], 0.0)

    def test_the_key_is_the_brightest(self):
        plan = {e["name"]: e["intensity"] for e in self.plan()}
        self.assertEqual(max(plan, key=plan.get), "VPStudio_key")

    def test_the_distances_are_multiples_of_the_radius(self):
        frame = vp.subject_frame(BOX)
        for spec, entry in zip(vp.lights_of("Studio"), self.plan()):
            reach = math.sqrt(sum(
                (entry["position"][i] - frame["centre"][i]) ** 2
                for i in range(3)))
            self.assertAlmostEqual(reach, spec.distance * frame["radius"],
                                   places=6)

    def test_a_bigger_subject_pushes_the_lights_out(self):
        big = vp.light_plan(vp.subject_frame(
            (-400.0, 0.0, -400.0, 400.0, 1800.0, 400.0)), 0.0, None)
        small = self.plan()
        self.assertGreater(abs(big[0]["position"][1]),
                           abs(small[0]["position"][1]))

    def test_the_local_matrix_aims_at_the_pivot(self):
        """Positions in the plan are LOCAL to a pivot standing at the
        subject centre -- that is what makes Rotate one attribute on one
        node instead of a recomputed table."""
        for entry in self.plan():
            m = entry["matrix"]
            here = (m[12], m[13], m[14])
            want = vp.normalise(here)
            self.assertAlmostEqual(dot((m[8], m[9], m[10]), want), 1.0,
                                   places=9)

    def test_the_azimuth_turns_the_whole_rig(self):
        turned = vp.light_plan(vp.subject_frame(BOX), 90.0, None)
        straight = self.plan()
        for a, b in zip(straight, turned):
            self.assertAlmostEqual(
                math.sqrt(sum(c * c for c in a["matrix"][12:15])),
                math.sqrt(sum(c * c for c in b["matrix"][12:15])),
                places=6)
        self.assertNotAlmostEqual(straight[0]["matrix"][12],
                                  turned[0]["matrix"][12], places=3)

    def test_the_shadow_map_comes_from_the_quality(self):
        self.assertEqual(self.plan({"quality": "Beauty"})[0]["dmap"], 4096)
        self.assertEqual(self.plan({"quality": "Fast"})[0]["dmap"], 1024)

    def test_only_spots_carry_a_cone(self):
        for entry in self.plan():
            self.assertEqual("cone" in entry, entry["kind"] == "spot")


class TestLooks(unittest.TestCase):
    """A look is a bundle -- lights, floor, sky, shadow sharpness, bloom --
    so a third one is a row in the table rather than a branch in the
    code."""

    def test_two_looks_studio_first(self):
        self.assertEqual(vp.LOOK_ORDER, ("Studio", "Outdoor"))

    def test_studio_is_the_default(self):
        """Anyone who never opens the list gets what they had before."""
        self.assertEqual(vp.DEFAULTS["look"], "Studio")
        self.assertEqual(vp.merged_options(None)["look"], "Studio")

    def test_an_unknown_look_is_the_studio(self):
        self.assertEqual(vp.look_of("nonsense"), vp.look_of("Studio"))
        self.assertEqual(vp.lights_of("nonsense"), vp.STUDIO_LIGHTS)

    def test_every_look_carries_every_part(self):
        for name in vp.LOOK_ORDER:
            look = vp.look_of(name)
            for part in ("lights", "floor", "backdrop", "shadow_filter",
                         "bloom"):
                self.assertIn(part, look, "%s / %s" % (name, part))

    def test_every_look_has_exactly_one_shadow_caster(self):
        for name in vp.LOOK_ORDER:
            casters = [s for s in vp.lights_of(name) if s.shadow]
            self.assertEqual(len(casters), 1, name)

    def test_every_look_has_something_to_fill_the_shadows(self):
        for name in vp.LOOK_ORDER:
            self.assertTrue(any(not s.shadow for s in vp.lights_of(name)),
                            name)

    def test_no_look_exceeds_the_eight_hardware_lights(self):
        for name in vp.LOOK_ORDER:
            self.assertLessEqual(len(vp.lights_of(name)), 8, name)

    def test_every_light_name_is_unique_within_its_look(self):
        """The names are the keys of the UUID index the dials read."""
        for name in vp.LOOK_ORDER:
            names = [s.name for s in vp.lights_of(name)]
            self.assertEqual(len(names), len(set(names)), name)

    def test_outdoor_is_a_sun_and_a_sky(self):
        names = vp.light_names("Outdoor")
        self.assertIn("sun", names)
        self.assertIn("sky", names)

    def test_the_sun_is_directional(self):
        """A spot sun lights a pool on the ground and reads as a stadium
        floodlight; the sun lights everything and its shadows run
        parallel."""
        sun = [s for s in vp.lights_of("Outdoor") if s.name == "sun"][0]
        self.assertEqual(sun.kind, "directional")
        self.assertTrue(sun.shadow)

    def test_the_sun_is_higher_and_harder_than_the_key(self):
        sun = [s for s in vp.lights_of("Outdoor") if s.name == "sun"][0]
        key = [s for s in vp.lights_of("Studio") if s.name == "key"][0]
        self.assertGreater(sun.elevation, key.elevation)
        self.assertGreater(sun.intensity, key.intensity)
        self.assertLess(vp.look_of("Outdoor")["shadow_filter"],
                        vp.look_of("Studio")["shadow_filter"])

    def test_the_sky_fills_far_harder_than_the_studio_s_ambient(self):
        sky = [s for s in vp.lights_of("Outdoor") if s.name == "sky"][0]
        amb = [s for s in vp.lights_of("Studio") if s.name == "ambient"][0]
        self.assertGreater(sky.intensity, amb.intensity)

    def test_the_sky_is_blue_and_the_key_is_warm(self):
        sky = [s for s in vp.lights_of("Outdoor") if s.name == "sky"][0]
        sun = [s for s in vp.lights_of("Outdoor") if s.name == "sun"][0]
        self.assertGreater(sky.colour[2], sky.colour[0])
        self.assertGreater(sun.colour[0], sun.colour[2])

    def test_outdoor_puts_a_sky_behind_the_subject(self):
        studio = vp.backdrop_settings({"look": "Studio"})
        outdoor = vp.backdrop_settings({"look": "Outdoor"})
        self.assertGreater(outdoor["backgroundTop"][2],
                           studio["backgroundTop"][2])
        self.assertGreater(max(outdoor["backgroundTop"]),
                           max(studio["backgroundTop"]))

    def test_the_outdoor_sky_is_bluer_than_it_is_red(self):
        sky = vp.backdrop_settings({"look": "Outdoor"})
        self.assertGreater(sky["backgroundTop"][2], sky["backgroundTop"][0])

    def test_the_outdoor_horizon_is_paler_than_the_zenith(self):
        """Haze piles up at the horizon; the sky is deepest overhead."""
        sky = vp.backdrop_settings({"look": "Outdoor"})
        self.assertGreater(sum(sky["backgroundBottom"]),
                           sum(sky["backgroundTop"]))

    def test_the_outdoor_ground_is_paler_than_the_studio_floor(self):
        frame = vp.subject_frame(BOX)
        studio = vp.floor_plan(frame, {"look": "Studio"})["colour"]
        outdoor = vp.floor_plan(frame, {"look": "Outdoor"})["colour"]
        self.assertGreater(sum(outdoor), sum(studio))

    def test_a_sunny_day_blooms_harder(self):
        frame = vp.subject_frame(BOX)
        self.assertGreater(
            vp.render_settings(frame, {"look": "Outdoor"})["bloomAmount"],
            vp.render_settings(frame, {"look": "Studio"})["bloomAmount"])

    def test_the_backdrop_switch_still_wins_over_the_look(self):
        self.assertEqual(
            vp.backdrop_settings({"look": "Outdoor", "backdrop": False}),
            {})

    def test_each_look_plans_its_own_lights(self):
        frame = vp.subject_frame(BOX)
        for name in vp.LOOK_ORDER:
            plan = vp.light_plan(frame, 0.0, {"look": name})
            self.assertEqual([e["name"] for e in plan],
                             ["VPStudio_" + s
                              for s in vp.light_names(name)], name)

    def test_the_shadow_filter_reaches_the_plan(self):
        frame = vp.subject_frame(BOX)
        for name in vp.LOOK_ORDER:
            plan = vp.light_plan(frame, 0.0, {"look": name})
            self.assertTrue(all(e["filter"] ==
                                vp.look_of(name)["shadow_filter"]
                                for e in plan), name)

    def test_the_sun_focuses_its_shadow_map_on_the_subject(self):
        """A directional's auto-focus fits the map to the whole scene,
        which now includes a floor twenty radii across -- so the sun's
        shadow comes out mushy unless it is focused by hand."""
        frame = vp.subject_frame(BOX)
        plan = vp.light_plan(frame, 0.0, {"look": "Outdoor"})
        sun = [e for e in plan if e["name"] == "VPStudio_sun"][0]
        self.assertIn("width_focus", sun)
        self.assertLess(sun["width_focus"],
                        vp.floor_plan(frame, {"look": "Outdoor"})["size"])
        self.assertGreater(sun["width_focus"], frame["radius"])

    def test_a_spot_never_asks_for_a_width_focus(self):
        """A spot's map already covers its cone; the two levers are
        different attributes and mixing them would fight."""
        frame = vp.subject_frame(BOX)
        for entry in vp.light_plan(frame, 0.0, {"look": "Studio"}):
            if entry["kind"] == "spot":
                self.assertNotIn("width_focus", entry)

    def test_shadows_off_takes_the_sun_s_shadow_too(self):
        frame = vp.subject_frame(BOX)
        plan = vp.light_plan(frame, 0.0,
                             {"look": "Outdoor", "shadows": False})
        self.assertFalse(any(e["shadow"] for e in plan))

    def test_brightness_scales_the_outdoor_rig_as_well(self):
        frame = vp.subject_frame(BOX)
        base = vp.light_plan(frame, 0.0, {"look": "Outdoor"})
        twice = vp.light_plan(frame, 0.0,
                              {"look": "Outdoor", "brightness": 2.0})
        for a, b in zip(base, twice):
            self.assertAlmostEqual(b["intensity"], 2.0 * a["intensity"],
                                   places=9)

    def test_the_dropdown_offers_exactly_the_looks_that_exist(self):
        self.assertEqual(vp.MENU_ITEMS["look"], vp.LOOK_ORDER)
        self.assertEqual(vp.MENU_ITEMS["quality"], vp.QUALITY_ORDER)
        for key in vp.MENUS:
            self.assertIn(key, vp.DEFAULTS)
            self.assertIn(key, vp.CONTROL)


class TestFloorPlan(unittest.TestCase):

    def test_it_reaches_well_past_the_subject(self):
        """Seven radii was the first guess and the horizon sat inside the
        frame at a normal orbit distance."""
        frame = vp.subject_frame(BOX)
        self.assertGreater(vp.floor_plan(frame)["size"],
                           10.0 * frame["radius"])

    def test_it_scales_with_the_subject(self):
        small = vp.floor_plan(vp.subject_frame(BOX))["size"]
        big = vp.floor_plan(vp.subject_frame(
            (-400.0, 0.0, -400.0, 400.0, 1800.0, 400.0)))["size"]
        self.assertGreater(big, small)

    def test_a_tiny_prop_still_gets_a_usable_floor(self):
        self.assertGreaterEqual(vp.floor_plan(vp.subject_frame(
            (-1.0, 0.0, -1.0, 1.0, 2.0, 1.0)))["size"], 400.0)

    def test_it_sits_just_under_the_feet(self):
        """Coplanar with the feet is where depth-map shadows fight the
        ground and flicker."""
        frame = vp.subject_frame(BOX)
        y = vp.floor_plan(frame)["position"][1]
        self.assertLess(y, frame["floor_y"])
        self.assertGreater(y, frame["floor_y"] - 1.0)

    def test_it_is_centred_on_the_subject(self):
        frame = vp.subject_frame((100.0, 0.0, -50.0, 200.0, 180.0, 50.0))
        plan = vp.floor_plan(frame)
        self.assertAlmostEqual(plan["position"][0], frame["centre"][0])
        self.assertAlmostEqual(plan["position"][2], frame["centre"][2])


class TestRenderSettings(unittest.TestCase):

    def settings(self, options=None, box=BOX):
        return vp.render_settings(vp.subject_frame(box), options)

    def test_the_ao_radius_follows_the_scene_s_scale(self):
        """16 cm of occlusion radius reads as contact shadow on a 180 cm
        character and as nothing at all on a 20 m one."""
        self.assertEqual(self.settings()["ssaoRadius"], 18)
        self.assertEqual(self.settings(box=(
            -400.0, 0.0, -400.0, 400.0, 1800.0, 400.0))["ssaoRadius"], 180)

    def test_the_ao_radius_stays_sane_at_both_extremes(self):
        for box in ((0.0, 0.0, 0.0, 0.1, 0.1, 0.1),
                    (-1e5, 0.0, -1e5, 1e5, 1e5, 1e5)):
            radius = self.settings(box=box)["ssaoRadius"]
            self.assertGreaterEqual(radius, 2)
            self.assertLessEqual(radius, 200)

    def test_bloom_never_blooms_the_whole_frame(self):
        """Maya's own starting threshold is 0, which blooms every pixel
        and turns the picture to fog."""
        self.assertGreaterEqual(self.settings()["bloomThreshold"], 1.0)

    def test_bloom_needs_the_float_target(self):
        self.assertIs(self.settings()["floatingPointRTEnable"], True)

    def test_every_switch_reaches_its_attribute(self):
        for key, attr in (("ao", "ssaoEnable"),
                          ("motion_blur", "motionBlurEnable"),
                          ("anti_alias", "multiSampleEnable"),
                          ("bloom", "bloomEnable"),
                          ("fog", "hwFogEnable")):
            self.assertIs(self.settings({key: True})[attr], True, key)
            self.assertIs(self.settings({key: False})[attr], False, key)

    def test_anti_aliasing_covers_the_lines_too(self):
        self.assertIs(self.settings({"anti_alias": True})["lineAAEnable"],
                      True)

    def test_the_sample_counts_come_from_the_quality(self):
        self.assertEqual(self.settings({"quality": "Fast"})[
            "multiSampleCount"], 4)
        self.assertEqual(self.settings({"quality": "Beauty"})[
            "multiSampleCount"], 16)

    def test_everything_written_is_something_restore_knows(self):
        """An attribute added only to the writer is a setting the
        animator never gets back."""
        self.assertLessEqual(set(self.settings()), set(vp.RENDER_ATTRS))

    def test_eight_lights_are_allowed_through(self):
        self.assertEqual(self.settings()["maxHardwareLights"], 8)
        self.assertIs(self.settings()["useMaximumHardwareLights"], True)

    def test_the_plan_is_attribute_names_and_the_writer_wants_plugs(self):
        """The bug this pins cost a live run: `apply_plugs` skips a plug
        that does not exist, and `ssaoEnable` on its own does not -- so
        every setting was dropped silently and the studio came out with
        no AO, no AA, no motion blur and no bloom, looking plausible."""
        for attr in self.settings():
            self.assertNotIn(".", attr, attr)
        for plug in vp.render_plugs(self.settings()):
            self.assertTrue(plug.startswith(vp.RENDER_NODE + "."), plug)

    def test_the_plugs_carry_the_same_values(self):
        plan = self.settings()
        plugs = vp.render_plugs(plan)
        self.assertEqual(len(plugs), len(plan))
        for attr, value in plan.items():
            self.assertEqual(plugs[vp.RENDER_NODE + "." + attr], value)

    def test_nothing_in_is_nothing_out(self):
        self.assertEqual(vp.render_plugs(None), {})


class TestPanelSettings(unittest.TestCase):

    def test_it_lights_textures_and_shades(self):
        plan = vp.panel_settings(None)
        self.assertEqual(plan["displayAppearance"], "smoothShaded")
        self.assertEqual(plan["displayLights"], "all")
        self.assertIs(plan["displayTextures"], True)

    def test_the_icons_go_but_the_lighting_stays(self):
        """Hiding a light's TRANSFORM would turn it off instead: an
        invisible light lights nothing in Viewport 2.0."""
        plan = vp.panel_settings(None)
        self.assertIs(plan["lights"], False)
        self.assertEqual(plan["displayLights"], "all")

    def test_the_grid_goes_because_we_bring_a_floor(self):
        self.assertIs(vp.panel_settings(None)["grid"], False)

    def test_shadows_follow_the_option(self):
        self.assertIs(vp.panel_settings({"shadows": False})["shadows"],
                      False)

    def test_the_plain_view_takes_nothing_of_the_animator_s_away(self):
        plan = vp.panel_settings({"clean": False})
        for flag in vp.CLUTTER:
            self.assertNotIn(flag, plan)

    def test_clean_view_hides_the_clutter(self):
        plan = vp.panel_settings({"clean": True})
        for flag in vp.CLUTTER:
            self.assertIs(plan[flag], False, flag)

    def test_clean_view_never_hides_the_manipulators(self):
        """An animator who cannot see the manipulator cannot animate;
        this is not a playblast switch."""
        self.assertNotIn("manipulators", vp.CLUTTER)
        self.assertNotIn("manipulators", vp.panel_settings({"clean": True}))

    def test_every_flag_we_write_is_one_restore_knows(self):
        for plan in (vp.panel_settings({"clean": False}),
                     vp.panel_settings({"clean": True})):
            self.assertLessEqual(set(plan), set(vp.PANEL_FLAGS))


class TestBackdropAndDof(unittest.TestCase):

    def test_the_flat_colour_is_set_alongside_the_gradient(self):
        """playblast renders the background from `background` and ignores
        the gradient (measured 2026-09-03) -- and an animator reviews on
        playblasts."""
        plan = vp.backdrop_settings({"backdrop": True})
        self.assertIn("background", plan)
        self.assertIn("backgroundTop", plan)

    def test_the_flat_colour_sits_between_the_two(self):
        plan = vp.backdrop_settings({"backdrop": True})
        for i in range(3):
            self.assertGreater(plan["background"][i],
                               plan["backgroundBottom"][i])
            self.assertLess(plan["background"][i], plan["backgroundTop"][i])

    def test_it_is_dark(self):
        self.assertLess(max(vp.backdrop_settings(None)["background"]), 0.2)

    def test_switched_off_it_writes_nothing(self):
        self.assertEqual(vp.backdrop_settings({"backdrop": False}), {})

    def test_dof_is_off_unless_asked(self):
        self.assertEqual(vp.dof_plan(500.0, {"dof": False}), {})

    def test_dof_focuses_where_the_subject_is(self):
        plan = vp.dof_plan(523.0, {"dof": True})
        self.assertAlmostEqual(plan["focusDistance"], 523.0)
        self.assertIs(plan["depthOfField"], True)

    def test_a_camera_inside_the_subject_still_focuses(self):
        self.assertGreater(vp.dof_plan(0.0, {"dof": True})["focusDistance"],
                           0.0)


class TestIdentity(unittest.TestCase):

    def test_no_rig_picks_nothing(self):
        self.assertIsNone(vp.pick_rig([]))

    def test_two_rigs_resolve_the_same_way_twice(self):
        self.assertEqual(vp.pick_rig(["|b", "|a"]), "|a")
        self.assertEqual(vp.pick_rig(["|a", "|b"]), "|a")

    def test_the_separator_matters(self):
        """`|VPStudio_extra` is not a child of `|VPStudio` (trap 7)."""
        self.assertTrue(vp._under("|VPStudio|VPStudio_floor", "|VPStudio"))
        self.assertTrue(vp._under("|VPStudio", "|VPStudio"))
        self.assertFalse(vp._under("|VPStudio_extra", "|VPStudio"))

    def test_the_marker_names_are_ours_and_stable(self):
        """They are written into the animator's saved file: renaming one
        orphans every studio built before the rename."""
        self.assertEqual(vp.MARKER, "skeldarVpStudio")
        self.assertEqual(vp.STATE_ATTR, "skeldarVpStudioState")
        self.assertEqual(vp.NODES_ATTR, "skeldarVpStudioNodes")
        self.assertEqual(vp.LIGHTS_ATTR, "skeldarVpStudioLights")


# ---------------------------------------------------------------------------
#  The scene-touching half, on a fake cmds
# ---------------------------------------------------------------------------

class FakeCmds(object):
    """Just enough of `maya.cmds` for the state machinery."""

    def __init__(self, attrs=None, panels=None):
        self.attrs = dict(attrs or {})
        self.panels = dict(panels or {})
        self.written = []
        self.string_attrs = []
        self.gradient = True
        self.colours = {"background": [0.6, 0.6, 0.6],
                        "backgroundTop": [0.5, 0.6, 0.7],
                        "backgroundBottom": [0.05, 0.05, 0.05]}
        self.autokey = True
        self.refreshed = 0
        self.uuids = {}

    # --- attributes ---
    def objExists(self, name):
        return name in self.attrs or name in self.uuids

    def getAttr(self, plug, **_kw):
        if plug not in self.attrs:
            raise RuntimeError("no such plug " + plug)
        return self.attrs[plug]

    def setAttr(self, plug, *values, **kwargs):
        if plug not in self.attrs:
            raise RuntimeError("no such plug " + plug)
        self.attrs[plug] = values[0] if len(values) == 1 else list(values)
        self.written.append((plug, self.attrs[plug], kwargs.get("type")))

    def addAttr(self, node, **kwargs):
        plug = "%s.%s" % (node, kwargs["longName"])
        self.attrs[plug] = ""
        self.string_attrs.append(plug)

    def ls(self, *args, **kwargs):
        if kwargs.get("uuid"):
            return [self.uuids.get(args[0], "")] if args else []
        if args and args[0] in self.uuids.values():
            return [k for k, u in self.uuids.items() if u == args[0]]
        if args and kwargs.get("objectsOnly"):
            return []
        return list(args) if args else []

    def listRelatives(self, *_args, **_kwargs):
        return []

    # --- panels ---
    def getPanel(self, **kwargs):
        if kwargs.get("type") == "modelPanel":
            return list(self.panels)
        if kwargs.get("visiblePanels"):
            return list(self.panels)[:1]
        if kwargs.get("withFocus"):
            return list(self.panels)[0] if self.panels else None
        return []

    def modelPanel(self, name, **kwargs):
        if kwargs.get("exists"):
            return name in self.panels
        return None

    def modelEditor(self, name, **kwargs):
        if kwargs.get("query"):
            flag = [k for k in kwargs if k not in ("query", "edit")][0]
            if flag not in self.panels.get(name, {}):
                raise RuntimeError("no such flag " + flag)
            return self.panels[name][flag]
        if kwargs.get("edit"):
            for flag, value in kwargs.items():
                if flag == "edit":
                    continue
                self.panels.setdefault(name, {})[flag] = value
        return None

    # --- prefs ---
    def displayPref(self, **kwargs):
        if kwargs.get("query"):
            return self.gradient
        if "displayGradient" in kwargs:
            self.gradient = kwargs["displayGradient"]

    def displayRGBColor(self, name, *values, **kwargs):
        if kwargs.get("query"):
            return list(self.colours[name])
        self.colours[name] = list(values)

    def autoKeyframe(self, **kwargs):
        if kwargs.get("query"):
            return self.autokey
        self.autokey = kwargs.get("state", self.autokey)
        return self.autokey

    def refresh(self, *_a, **_kw):
        self.refreshed += 1

    def headsUpMessage(self, *_a, **_kw):
        pass


class FakeSceneTest(unittest.TestCase):

    def setUp(self):
        self.real = vp.cmds
        self.fake = FakeCmds()
        vp.cmds = self.fake

    def tearDown(self):
        vp.cmds = self.real


class TestStateRoundTrip(FakeSceneTest):

    def test_the_state_survives_json(self):
        state = {"plugs": {"hardwareRenderingGlobals.ssaoEnable": False},
                 "panels": {"modelPanel4": {"grid": True}}}
        self.fake.attrs["|VPStudio." + vp.STATE_ATTR] = json.dumps(state)
        self.assertEqual(vp.read_state("|VPStudio"), state)

    def test_no_attribute_is_an_empty_state(self):
        self.assertEqual(vp.read_state("|VPStudio"), {})

    def test_garbage_is_an_empty_state_not_a_traceback(self):
        self.fake.attrs["|VPStudio." + vp.STATE_ATTR] = "{not json"
        self.assertEqual(vp.read_state("|VPStudio"), {})

    def test_the_options_come_back_merged(self):
        self.fake.attrs["|VPStudio." + vp.OPTIONS_ATTR] = json.dumps(
            {"quality": "Beauty"})
        opts = vp.read_options("|VPStudio")
        self.assertEqual(opts["quality"], "Beauty")
        self.assertIn("floor", opts)

    def test_the_light_index_comes_back_as_a_dict(self):
        self.fake.attrs["|VPStudio." + vp.LIGHTS_ATTR] = json.dumps(
            {"key": "UUID-1"})
        self.assertEqual(vp.read_index("|VPStudio"), {"key": "UUID-1"})

    def test_a_list_where_a_dict_belongs_is_refused(self):
        self.fake.attrs["|VPStudio." + vp.LIGHTS_ATTR] = json.dumps([1, 2])
        self.assertEqual(vp.read_index("|VPStudio"), {})

    def test_the_node_list_is_uuids(self):
        self.fake.attrs["|VPStudio." + vp.NODES_ATTR] = "A,B,,C"
        self.assertEqual(vp.recorded_nodes("|VPStudio"), ["A", "B", "C"])

    def test_writing_a_string_attr_creates_it_once(self):
        vp._write_string("|VPStudio", vp.MARKER, "1")
        vp._write_string("|VPStudio", vp.MARKER, "2")
        self.assertEqual(self.fake.attrs["|VPStudio." + vp.MARKER], "2")
        self.assertEqual(len(self.fake.string_attrs), 1)


class TestCapture(FakeSceneTest):

    def setUp(self):
        FakeSceneTest.setUp(self)
        for attr in vp.RENDER_ATTRS:
            self.fake.attrs["hardwareRenderingGlobals." + attr] = 0
        self.fake.attrs["hardwareRenderingGlobals.ssaoEnable"] = False
        self.fake.panels = {
            "modelPanel4": {flag: "was" for flag in vp.PANEL_FLAGS}}

    def test_every_attribute_we_write_is_captured(self):
        state = vp.capture_state()
        for attr in vp.RENDER_ATTRS:
            self.assertIn("hardwareRenderingGlobals." + attr,
                          state["plugs"], attr)

    def test_every_panel_flag_we_write_is_captured(self):
        state = vp.capture_state()
        self.assertEqual(sorted(state["panels"]["modelPanel4"]),
                         sorted(vp.PANEL_FLAGS))

    def test_the_backdrop_is_captured(self):
        state = vp.capture_state()
        self.assertIn("backgroundTop", state["backdrop"])
        self.assertIn("gradient", state["backdrop"])

    def test_a_camera_s_dof_is_captured_when_asked(self):
        self.fake.attrs["perspShape.depthOfField"] = False
        self.fake.attrs["perspShape.focusDistance"] = 5.0
        state = vp.capture_state(["perspShape"])
        self.assertIn("perspShape.depthOfField", state["plugs"])
        self.assertIn("perspShape.focusDistance", state["plugs"])

    def test_an_attribute_this_maya_lacks_is_skipped_not_fatal(self):
        del self.fake.attrs["hardwareRenderingGlobals.bloomEnable"]
        state = vp.capture_state()
        self.assertNotIn("hardwareRenderingGlobals.bloomEnable",
                         state["plugs"])


class TestRestoreWrites(FakeSceneTest):

    def test_it_writes_what_it_was_given(self):
        self.fake.attrs["hardwareRenderingGlobals.ssaoEnable"] = True
        written = vp.apply_plugs(
            {"hardwareRenderingGlobals.ssaoEnable": False})
        self.assertEqual(written, 1)
        self.assertEqual(
            self.fake.attrs["hardwareRenderingGlobals.ssaoEnable"], 0)

    def test_a_plug_that_has_gone_is_skipped(self):
        self.assertEqual(vp.apply_plugs({"nope.gone": 1}), 0)

    def test_one_bad_plug_does_not_take_the_restore_down(self):
        """A locked or connected plug is somebody else's business and
        must not cost the animator the rest of their viewport."""
        self.fake.attrs["a.b"] = 1
        self.fake.attrs["c.d"] = 1

        real_set = self.fake.setAttr

        def picky(plug, *values, **kwargs):
            if plug == "a.b":
                raise RuntimeError("locked")
            return real_set(plug, *values, **kwargs)

        self.fake.setAttr = picky
        self.assertEqual(vp.apply_plugs({"a.b": 9, "c.d": 9}), 1)
        self.assertEqual(self.fake.attrs["c.d"], 9)

    def test_a_string_is_written_as_a_string(self):
        self.fake.attrs["a.b"] = ""
        vp.apply_plugs({"a.b": "smoothShaded"})
        self.assertEqual(self.fake.written[-1][2], "string")

    def test_a_colour_triple_is_written_as_three(self):
        self.fake.attrs["a.b"] = [0, 0, 0]
        vp.apply_plugs({"a.b": [1, 2, 3]})
        self.assertEqual(self.fake.attrs["a.b"], [1, 2, 3])

    def test_the_panels_go_back(self):
        self.fake.panels = {"modelPanel4": {"grid": False}}
        vp.apply_panels({"modelPanel4": {"grid": True}})
        self.assertIs(self.fake.panels["modelPanel4"]["grid"], True)

    def test_a_panel_that_has_gone_is_skipped(self):
        self.assertEqual(vp.apply_panels({"modelPanel9": {"grid": True}}), 0)

    def test_a_flag_this_maya_lacks_is_skipped(self):
        self.fake.panels = {"modelPanel4": {"grid": False}}
        vp.apply_panels({"modelPanel4": {"grid": True, "nonsense": 1}})
        self.assertIs(self.fake.panels["modelPanel4"]["grid"], True)

    def test_the_backdrop_goes_back(self):
        vp.apply_backdrop({"gradient": False,
                           "backgroundTop": [0.1, 0.2, 0.3]})
        self.assertIs(self.fake.gradient, False)
        self.assertEqual(self.fake.colours["backgroundTop"], [0.1, 0.2, 0.3])

    def test_an_empty_backdrop_writes_nothing(self):
        self.assertEqual(vp.apply_backdrop({}), 0)


class TestAutoKeyIsPutBack(FakeSceneTest):

    def test_the_block_leaves_autokey_as_it_found_it(self):
        """The animator runs autoKey on (trap 14)."""
        self.fake.autokey = True
        with vp._quiet_autokey():
            self.assertFalse(self.fake.autokey)
        self.assertTrue(self.fake.autokey)

    def test_even_when_the_block_raises(self):
        self.fake.autokey = True
        try:
            with vp._quiet_autokey():
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        self.assertTrue(self.fake.autokey)


# ---------------------------------------------------------------------------
#  The panel: a section of the SkeldarAnim hub (2026-09-17), no window
# ---------------------------------------------------------------------------

class TestPanelBuildsIntoTheHub(unittest.TestCase):
    """The window of its own is gone: `build_panel` puts the controls into
    whatever layout is current, and `show_window` opens the hub on the
    Studio section. Before this the panel was a `sizeable=False` window
    whose bottom buttons were clipped (2026-09-17, morning)."""

    def setUp(self):
        self.real = vp.cmds
        self.fake = FakeUiCmds(control_height=25)
        vp.cmds = self.fake
        self.column = vp.build_panel()

    def tearDown(self):
        vp.cmds = self.real

    def test_no_window_is_created(self):
        self.assertEqual(self.fake.windows, {})
        self.assertFalse([c for c in self.fake.calls
                          if c[0] in ("showWindow", "windowPref")])

    def test_the_controls_land_in_one_stretching_column(self):
        self.assertTrue(self.fake.column.get("adjustableColumn"))
        self.assertGreater(len(self.fake.children), 20)

    def test_the_status_line_exists_and_the_panel_reads_open(self):
        self.assertIn(vp.STATUS, self.fake.children)
        self.fake.existing.add(vp.STATUS)
        self.assertTrue(vp.is_open())

    def test_no_fixed_widths_and_no_fixed_width_font(self):
        """2026-09-28, the skin: Studio stretches like every other section
        (it sat in a 300 px column) and its status is in the UI font."""
        for call in self.fake.calls:
            #  a button beside the primary one keeps its own width; nothing
            #  is sized to the old column (WIDTH - 20 = 280)
            self.assertLess(call[2].get("width", 0), 200, call)
            self.assertNotEqual(call[2].get("font"), "smallFixedWidthFont")
        separators = [c for c in self.fake.calls if c[0] == "separator"]
        self.assertEqual(separators, [])

    def test_the_checks_are_chips_two_to_a_row(self):
        import maya_hubstyle
        maya_hubstyle.take_marks()
        vp.build_panel()
        marks = maya_hubstyle.take_marks()
        chips = [m.name for m in marks if m.role == "chip"]
        self.assertEqual(chips, [vp._control(k) for k, _l, _n in vp.CHECKS])
        roles = dict((m.role, m.icon) for m in marks
                     if m.role in ("primary", "secondary"))
        self.assertEqual(roles, {"primary": "bulb",
                                 "secondary": "arrow-back-up"})

    def test_the_dropdowns_go_live_only_after_the_build(self):
        """Setting an optionMenu's value fires its changeCommand, so the
        wiring has to come after every remembered value is in place."""
        menus = [c for c in self.fake.calls if c[0] == "optionMenu"]
        created = [c for c in menus if not c[2].get("edit")]
        wired = [c for c in menus
                 if c[2].get("edit") and "changeCommand" in c[2]]
        self.assertEqual(len(wired), len(vp.MENUS))
        for c in created:
            self.assertNotIn("changeCommand", c[2])
        last_create = max(self.fake.calls.index(c) for c in created)
        self.assertTrue(all(self.fake.calls.index(c) > last_create
                            for c in wired))


class TestShowWindowOpensTheHub(unittest.TestCase):

    def test_it_asks_the_hub_for_the_studio_section(self):
        import maya_hub
        asked = []
        saved = maya_hub.show
        maya_hub.show = lambda key=None: asked.append(key) or "hub"
        try:
            self.assertEqual(vp.show_window(), "hub")
        finally:
            maya_hub.show = saved
        self.assertEqual(asked, ["studio"])
        self.assertEqual(maya_hub.section("studio").module, "maya_vpstudio")


class TestIsOpenGuardsTheReads(unittest.TestCase):
    """`window_options` and `refresh` used to ask `cmds.window(WINDOW)`;
    with the panel in the hub the question is whether OUR controls exist."""

    def setUp(self):
        self.real = vp.cmds
        self.fake = FakeUiCmds()
        vp.cmds = self.fake

    def tearDown(self):
        vp.cmds = self.real

    def test_closed_panel_options_are_the_stored_ones(self):
        self.assertFalse(vp.is_open())
        self.assertEqual(vp.window_options(), vp.window_options())
        self.assertEqual(vp.refresh(), "")


if __name__ == "__main__":
    unittest.main()
