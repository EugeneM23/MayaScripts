"""The numbers `look` copies from its siblings, pinned to their originals (2026-10-03).

`look` is stdlib only and imports no module of the library (its Boundary test pins that), so the
few values it shares with them are written out twice: how a paste's worst is said
(`apply.SHOW_DEG` / `SHOW_CM` / `DEG_PLACES` - `look.anim_status` says an animation's worst as
`apply._line` says a pose's) and the format an animation card's header carries
(`store.ANIM_FORMAT` - `look.details` tells an animation from a pose by it when it holds the
header alone). This module may import all three, so a change made to one copy and not the other
fails here instead of reading wrong in the status line or the details panel.

Spec: docs/superpowers/specs/2026-10-03-pose-library-animation-design.md
"""

import unittest

from maya_poselib import apply, look, store


class CopiedConstants(unittest.TestCase):

    def test_an_animation_s_worst_is_said_as_a_pose_s(self):
        self.assertEqual(look.SHOW_DEG, apply.SHOW_DEG)
        self.assertEqual(look.SHOW_CM, apply.SHOW_CM)
        self.assertEqual(look.DEG_PLACES, apply.DEG_PLACES)

    def test_an_animation_header_is_known_by_the_store_s_format(self):
        self.assertEqual(look._ANIM_FORMAT, store.ANIM_FORMAT)
        # a header the store wrote, read alone (no listing yet), says what the clip is
        lines = look.details(None, {"format": store.ANIM_FORMAT, "frames": 2, "start": 0.0,
                                    "end": 1.0, "fps": "ntsc"})
        self.assertTrue(any(line.startswith("2 frames") for line in lines), lines)


if __name__ == "__main__":
    unittest.main()
