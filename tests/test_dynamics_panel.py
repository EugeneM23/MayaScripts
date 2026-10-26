"""maya_dynamics.panel - the hub's Dynamics card (2026-10-26): its controls, a released knob, the
presets and the presses; and its registration (hub row, icon, payload, hotkey rows). On a fake
cmds; the scene half is proven by docs/superpowers/plans/verify_dynamics.py."""

import unittest

import maya_hub
import maya_hubicons
import maya_hubstyle as hubstyle
from maya_dynamics import model
from maya_dynamics import panel
from maya_dynamics import run
from maya_dynamics import setup


class FakeCmds(object):
    """Controls by name: created, edited, queried; everything else recorded and answered empty."""

    def __init__(self):
        self.controls = {}
        self.order = []
        self.optionvars = {}
        self.calls = []

    def _control(self, kind):
        def call(*args, **kwargs):
            name = args[0] if args else None
            if kwargs.get("exists"):
                return name in self.controls
            if kwargs.get("query"):
                item = self.controls[name]
                for flag in ("value", "selectIndexedItem", "label"):
                    if kwargs.get(flag):
                        return item.get(flag)
                return None
            if kwargs.get("edit"):
                item = self.controls[name]
                if kwargs.get("removeAll"):
                    item["rows"] = []
                    item["selectIndexedItem"] = []
                if "append" in kwargs:
                    item.setdefault("rows", []).append(kwargs["append"])
                if "selectIndexedItem" in kwargs:
                    item.setdefault("selectIndexedItem", []).append(kwargs["selectIndexedItem"])
                for flag in ("value", "label", "enable"):
                    if flag in kwargs:
                        item[flag] = kwargs[flag]
                return name
            name = name or "%s%d" % (kind, len(self.order))
            self.controls[name] = dict(kwargs, kind=kind)
            self.order.append(name)
            return name
        return call

    def __getattr__(self, name):
        if name in ("text", "button", "floatSliderGrp", "floatField", "intField", "checkBox",
                    "textScrollList", "rowLayout", "columnLayout"):
            return self._control(name)

        def other(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            if name == "ls":
                return []
            return None
        return other

    def optionVar(self, **kwargs):
        if "exists" in kwargs:
            return kwargs["exists"] in self.optionvars
        if "query" in kwargs:
            return self.optionvars.get(kwargs["query"])
        name, value = kwargs["stringValue"]
        self.optionvars[name] = value


class Built(unittest.TestCase):

    def setUp(self):
        self.fake = FakeCmds()
        self.saved = (panel.cmds, panel.start, panel.refresh)
        panel.cmds = self.fake
        panel.start = lambda: None
        panel.refresh = lambda *_a: None
        hubstyle.take_marks()
        panel.build_panel()
        self.marks = hubstyle.take_marks()

    def tearDown(self):
        panel.cmds, panel.start, panel.refresh = self.saved
        panel._PICKED.clear()

    def test_every_control_the_spec_lists_is_built(self):
        names = set(self.fake.controls)
        for name in (panel.SUBTITLE, panel.STATUS, panel.CHAINS, panel.ADD_BTN, panel.REMOVE_BTN,
                     panel.SIMULATE_BTN, panel.LOOP_CHIP, panel.PREROLL, panel.SUBSTEPS,
                     panel.COLLIDER_RADIUS, panel.COLLIDER_LENGTH):
            self.assertIn(name, names)
        for key, _low, _high, _default, tip in model.KNOBS:
            self.assertIn(panel._slider(key), names)
            self.assertEqual(panel._tip(key) in names, tip is not None, key)
        for preset in model.PRESETS:
            self.assertIn(panel._preset(preset), names)
        for attr, *_rest in setup.WIND_CHANNELS:
            self.assertIn(panel._wind_slider(attr), names)
        self.assertTrue(self.fake.controls[panel.CHAINS]["allowMultiSelection"])

    def test_simulate_is_the_one_orange(self):
        primary = [m.name for m in self.marks if m.role == "primary"]
        self.assertEqual(primary, [panel.SIMULATE_BTN])

    def test_the_knobs_show_the_remembered_settings(self):
        for key, *_rest in model.KNOBS:
            self.assertEqual(self.fake.controls[panel._slider(key)]["value"],
                             model.DEFAULTS[key])


class Knobs(unittest.TestCase):

    def setUp(self):
        self.fake = FakeCmds()
        self.stored = {"|g|a_dyn": model.settings({}), "|g|b_dyn": model.settings({})}
        self.layers = {"|g|a_dyn": "Dynamics_a"}
        self.solved = []
        self.saved = (panel.cmds, panel.start, panel.refresh, panel.picked, setup.read_settings,
                      setup.write_settings, setup.layer_of, run.simulate, panel._fill_list)
        panel.cmds = self.fake
        panel.start = lambda: None
        panel.refresh = lambda *_a: None
        panel._fill_list = lambda: None
        panel.picked = lambda: ["|g|a_dyn", "|g|b_dyn"]
        setup.read_settings = lambda chain: dict(self.stored[chain])
        setup.write_settings = lambda chain, s: self.stored.__setitem__(chain, dict(s))
        setup.layer_of = lambda chain: self.layers.get(chain)
        run.simulate = lambda chains, reuse=False, **kw: (
            self.solved.append((list(chains), reuse)) or "solved")
        panel.build_panel()
        hubstyle.take_marks()

    def tearDown(self):
        (panel.cmds, panel.start, panel.refresh, panel.picked, setup.read_settings,
         setup.write_settings, setup.layer_of, run.simulate, panel._fill_list) = self.saved

    def test_a_released_knob_writes_every_picked_chain_and_re_solves_the_baked_ones(self):
        self.fake.controls[panel._slider("damping")]["value"] = 0.6
        self.stored["|g|b_dyn"]["stiffness"] = 0.9                 # b's own value kept
        line = panel.knob_changed("damping")
        self.assertEqual(self.stored["|g|a_dyn"]["damping"], 0.6)
        self.assertEqual(self.stored["|g|b_dyn"]["damping"], 0.6)
        self.assertEqual(self.stored["|g|b_dyn"]["stiffness"], 0.9)
        self.assertEqual(self.solved, [(["|g|a_dyn"], True)])
        self.assertEqual(line, "solved")

    def test_nothing_baked_says_simulate(self):
        self.layers.clear()
        self.fake.controls[panel._slider("gravity")]["value"] = 2.0
        line = panel.knob_changed("gravity")
        self.assertEqual(self.solved, [])
        self.assertIn("press Simulate", line)

    def test_a_tip_field_writes_its_tip(self):
        self.fake.controls[panel._tip("stiffness")]["value"] = 2.5
        panel.tip_changed("stiffness")
        self.assertEqual(self.stored["|g|a_dyn"]["stiffness_tip"], 2.5)

    def test_a_preset_keeps_the_bake_options(self):
        self.fake.controls[panel.SUBSTEPS]["value"] = 9
        self.fake.controls[panel.LOOP_CHIP]["value"] = True
        panel.apply_preset("chain")
        for chain in self.stored:
            s = self.stored[chain]
            self.assertEqual(s["gravity"], model.PRESETS["chain"]["gravity"])
            self.assertEqual(s["substeps"], model.DEFAULTS["substeps"])   # not a preset key
        self.assertEqual(self.fake.controls[panel._slider("gravity")]["value"],
                         model.PRESETS["chain"]["gravity"])
        self.assertEqual(self.fake.controls[panel.SUBSTEPS]["value"], 9)
        self.assertTrue(self.fake.controls[panel.LOOP_CHIP]["value"])

    def test_simulate_reads_afresh(self):
        forgot = []
        saved = run.forget
        run.forget = lambda: forgot.append(True)
        try:
            panel.press_simulate()
        finally:
            run.forget = saved
        self.assertEqual(forgot, [True])
        self.assertEqual(self.solved, [(["|g|a_dyn", "|g|b_dyn"], False)])


class Registered(unittest.TestCase):

    def test_the_hub_row_the_icon_and_the_payload(self):
        row = maya_hub.section("dynamics")
        self.assertEqual((row.module, row.builder, row.group, row.icon),
                         ("maya_dynamics.panel", "build_panel", "animation", "wind"))
        keys = [s.key for s in maya_hub.SECTIONS]
        self.assertEqual(keys.index("dynamics"), keys.index("tailbuilder") + 1)
        self.assertIn("wind", maya_hubicons.ICONS)
        import install
        self.assertIn("maya_dynamics", install.payload())

    def test_the_hotkey_rows(self):
        import maya_hotkeys
        keys = [row[0] for row in maya_hotkeys._OURS]
        for key in ("window.dynamics", "dynamics.simulate", "dynamics.add_chain"):
            self.assertIn(key, keys)


if __name__ == "__main__":
    unittest.main()
