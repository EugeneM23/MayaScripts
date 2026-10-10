"""maya_voice.jitter, maya_voice.gate and maya_voice.roster - playback, gating, the room."""

import unittest
from array import array

from maya_voice import gate, jitter, roster


def packet(value, size=8):
    return array("h", [value] * (size // 2)).tobytes()


SILENCE = bytes(8)


class JitterBufferPlayback(unittest.TestCase):

    def test_waits_for_the_depth_then_plays_in_order(self):
        jb = jitter.JitterBuffer(depth=2, packet_bytes=8)
        jb.push(10, packet(1))
        self.assertIsNone(jb.pop())                 # still filling
        jb.push(11, packet(2))
        self.assertEqual(jb.pop(), packet(1))
        self.assertEqual(jb.pop(), packet(2))
        self.assertIsNone(jb.pop())                 # ran dry, nothing due

    def test_out_of_order_packets_are_reordered(self):
        jb = jitter.JitterBuffer(depth=2, packet_bytes=8)
        jb.push(5, packet(5))
        jb.push(7, packet(7))
        jb.push(6, packet(6))
        self.assertEqual([jb.pop() for _ in range(3)],
                         [packet(5), packet(6), packet(7)])

    def test_a_missing_packet_plays_silence_once_later_ones_wait(self):
        jb = jitter.JitterBuffer(depth=2, packet_bytes=8)
        for seq in (1, 2, 4, 5):                    # 3 is lost
            jb.push(seq, packet(seq))
        self.assertEqual(jb.pop(), packet(1))
        self.assertEqual(jb.pop(), packet(2))
        self.assertEqual(jb.pop(), SILENCE)         # the gap
        self.assertEqual(jb.pop(), packet(4))
        self.assertEqual(jb.pop(), packet(5))

    def test_a_late_packet_is_dropped(self):
        jb = jitter.JitterBuffer(depth=1, packet_bytes=8)
        jb.push(1, packet(1))
        jb.pop()
        self.assertFalse(jb.push(1, packet(9)))

    def test_silence_then_speech_resumes_without_waiting_for_the_gap(self):
        jb = jitter.JitterBuffer(depth=2, packet_bytes=8)
        jb.push(1, packet(1))
        jb.push(2, packet(2))
        jb.pop()
        jb.pop()
        #  the sender was quiet for many packets, then talks again
        jb.push(400, packet(4))
        jb.push(401, packet(5))
        self.assertEqual(jb.pop(), packet(4))
        self.assertEqual(jb.pop(), packet(5))

    def test_a_far_jump_resets_the_window(self):
        jb = jitter.JitterBuffer(depth=1, packet_bytes=8)
        jb.push(100, packet(1))
        self.assertEqual(jb.pop(), packet(1))
        jb.push(100000, packet(9))                  # far ahead: started again
        self.assertEqual(jb.pop(), packet(9))

    def test_sequence_wraps_around_the_32_bit_counter(self):
        jb = jitter.JitterBuffer(depth=1, packet_bytes=8)
        jb.push(0xFFFFFFFF, packet(1))
        jb.push(0, packet(2))
        self.assertEqual(jb.pop(), packet(1))
        self.assertEqual(jb.pop(), packet(2))


class LatestFrameRules(unittest.TestCase):

    def test_newer_replaces_older_and_older_is_refused(self):
        latest = jitter.LatestFrame()
        self.assertTrue(latest.put(3, b"a"))
        self.assertTrue(latest.put(4, b"b"))
        self.assertFalse(latest.put(2, b"old"))
        self.assertEqual(latest.take(), b"b")

    def test_wrap_counts_as_newer(self):
        latest = jitter.LatestFrame()
        latest.put(0xFFFFFFFF, b"a")
        self.assertTrue(latest.put(0, b"b"))


class Mixing(unittest.TestCase):

    def test_sum_of_chunks_clipped_to_s16(self):
        out = jitter.mix([packet(30000), packet(30000)], 8)
        self.assertEqual(array("h", out).tolist(), [32767] * 4)

    def test_no_chunks_is_silence_of_the_size(self):
        self.assertEqual(jitter.mix([], 8), bytes(8))

    def test_short_and_odd_chunks_do_not_break_the_clock(self):
        out = jitter.mix([b"\x01\x00\x01"], 8)
        self.assertEqual(len(out), 8)


class GateRules(unittest.TestCase):

    def test_loud_packet_is_sent_and_quiet_one_is_not(self):
        g = gate.Gate(threshold=100.0, hang=0)
        self.assertTrue(g.feed(packet(500)))
        self.assertFalse(g.feed(packet(10)))

    def test_hangover_keeps_the_tail_of_a_word(self):
        g = gate.Gate(threshold=100.0, hang=2)
        g.feed(packet(500))
        self.assertTrue(g.feed(packet(10)))
        self.assertTrue(g.feed(packet(10)))
        self.assertFalse(g.feed(packet(10)))

    def test_rms_of_a_constant_signal(self):
        self.assertAlmostEqual(gate.rms(packet(300)), 300.0)
        self.assertEqual(gate.rms(b""), 0.0)


class RosterRules(unittest.TestCase):

    def test_welcome_then_roster_then_speaking(self):
        r = roster.Roster()
        self.assertEqual(r.apply({"t": "welcome", "id": 3, "room": "layout"}),
                         "welcome")
        self.assertEqual(r.me, 3)
        r.apply({"t": "roster", "members": [
            {"id": 3, "name": "Eugene", "muted": False, "deafened": False,
             "sharing": True},
            {"id": 4, "name": "Oleg", "muted": True, "deafened": False,
             "sharing": False}]})
        self.assertEqual(r.sharers(), [3])
        #  a muted member sends nothing, so nothing marks them as speaking
        r.heard(4, now=10.0)
        self.assertEqual(r.speaking(now=10.1), {4})

    def test_speaking_window_is_short(self):
        r = roster.Roster()
        r.apply({"t": "roster", "members": [
            {"id": 4, "name": "Oleg", "muted": False, "deafened": False,
             "sharing": False}]})
        r.heard(4, now=10.0)
        self.assertEqual(r.speaking(now=10.1), {4})
        self.assertEqual(r.speaking(now=11.0), set())

    def test_label_names_the_flags_and_marks_you(self):
        r = roster.Roster()
        r.apply({"t": "welcome", "id": 3, "room": "x"})
        r.apply({"t": "roster", "members": [
            {"id": 3, "name": "Eugene", "muted": True, "deafened": False,
             "sharing": True}]})
        self.assertEqual(r.label(3), "Eugene - you, muted, sharing")

    def test_error_is_kept_and_reported(self):
        r = roster.Roster()
        self.assertEqual(r.apply({"t": "error", "msg": "room full"}), "error")
        self.assertEqual(r.error, "room full")

    def test_unknown_control_changes_nothing(self):
        r = roster.Roster()
        self.assertIsNone(r.apply({"t": "something"}))

    def test_bad_member_rows_are_skipped_not_fatal(self):
        r = roster.Roster()
        r.apply({"t": "roster", "members": [{"name": "no id"}, {"id": "x"},
                                            {"id": 2, "name": "ok"}]})
        self.assertEqual(sorted(r.members), [2])


if __name__ == "__main__":
    unittest.main()
