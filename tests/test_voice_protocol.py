"""maya_voice.protocol and maya_voice.pcm - the wire format and the sound format."""

import unittest

from maya_voice import pcm, protocol


class MediaFrames(unittest.TestCase):

    def test_round_trip_keeps_type_sender_seq_and_payload(self):
        data = protocol.pack_media(protocol.TYPE_AUDIO, 7, 123456, b"\x01\x02")
        kind, sender, seq, payload = protocol.unpack_media(data)
        self.assertEqual(kind, protocol.TYPE_AUDIO)
        self.assertEqual(sender, 7)
        self.assertEqual(seq, 123456)
        self.assertEqual(payload, b"\x01\x02")

    def test_header_is_seven_bytes_big_endian(self):
        data = protocol.pack_media(protocol.TYPE_VIDEO, 0x0102, 0x03040506,
                                   b"")
        self.assertEqual(data, b"V\x01\x02\x03\x04\x05\x06")

    def test_sequence_wraps_to_32_bits(self):
        data = protocol.pack_media(protocol.TYPE_AUDIO, 1, 0x1FFFFFFFF, b"")
        self.assertEqual(protocol.unpack_media(data)[2], 0xFFFFFFFF)

    def test_unknown_type_refused_on_both_sides(self):
        with self.assertRaises(ValueError):
            protocol.pack_media(ord("X"), 1, 1, b"")
        with self.assertRaises(ValueError):
            protocol.unpack_media(b"X\x00\x01\x00\x00\x00\x01")

    def test_short_frame_refused(self):
        with self.assertRaises(ValueError):
            protocol.unpack_media(b"A\x00")


class ControlMessages(unittest.TestCase):

    def test_control_is_json_with_the_type_field(self):
        text = protocol.control("join", name="Eugene")
        self.assertEqual(protocol.parse_control(text),
                         {"t": "join", "name": "Eugene"})

    def test_parse_refuses_non_objects_and_missing_type(self):
        for bad in ("[1, 2]", '{"name": "x"}', "not json", '{"t": 5}'):
            with self.assertRaises(ValueError):
                protocol.parse_control(bad)


class Cleaning(unittest.TestCase):

    def test_name_collapses_spaces_and_caps_length(self):
        self.assertEqual(protocol.clean_name("  Eugene   M  "), "Eugene M")
        long = protocol.clean_name("x" * 50)
        self.assertEqual(len(long), protocol.NAME_MAX)

    def test_empty_name_becomes_guest(self):
        self.assertEqual(protocol.clean_name("   "), "Guest")
        self.assertEqual(protocol.clean_name(None), "Guest")

    def test_room_is_lowercased_and_dashed(self):
        self.assertEqual(protocol.clean_room(" Layout Room "), "layout-room")

    def test_room_refuses_what_the_server_refuses(self):
        for bad in ("", "-start", "has/slash", "x" * 41, "ünï"):
            self.assertIsNone(protocol.clean_room(bad))

    def test_room_accepts_the_server_rule(self):
        self.assertEqual(protocol.clean_room("a_b-9"), "a_b-9")


class Sound(unittest.TestCase):

    def test_ratio_for_integer_multiples_only(self):
        self.assertEqual(pcm.ratio_for(48000, 2, 2), 3)
        self.assertEqual(pcm.ratio_for(16000, 1, 2), 1)
        self.assertIsNone(pcm.ratio_for(44100, 2, 2))
        self.assertIsNone(pcm.ratio_for(48000, 6, 2))
        self.assertIsNone(pcm.ratio_for(0, 1, 2))

    def test_float32_is_the_studio_default_and_is_supported(self):
        #  measured 2026-10-10: the preferred format is 48 kHz, 2 ch, Float32
        self.assertEqual(pcm.kind_for(4), "f")
        self.assertEqual(pcm.kind_for(2), "h")
        self.assertIsNone(pcm.kind_for(3))
        self.assertEqual(pcm.ratio_for(48000, 2, 4), 3)

    def test_float_device_converts_to_our_s16(self):
        from array import array
        #  one stereo frame per output sample, three frames per our sample
        values = array("f", [0.5, 0.5] * 3)          # mono 0.5, three times
        out = pcm.to_ours(values.tobytes(), 2, 3, "f")
        self.assertEqual(array_values(out), [round(0.5 * 32767)])

    def test_float_round_trip_is_close(self):
        from array import array
        samples = array("h", [1000, -2000, 3000])
        out = pcm.from_ours(samples.tobytes(), 2, 3, "f")
        back = pcm.to_ours(out, 2, 3, "f")
        self.assertEqual(array_values(back), [1000, -2000, 3000])

    def test_downmix_and_decimate_keeps_length_ratio(self):
        #  48 kHz stereo: 3 frames of 2 channels per output sample
        samples = []
        for _ in range(9):
            samples.extend([1000, 3000])          # mono average 2000
        data = array_bytes(samples)
        out = pcm.to_ours(data, 2, 3)
        self.assertEqual(len(out), 9 * 2 // 3 * 1)  # 3 output samples
        self.assertEqual(array_values(out), [2000, 2000, 2000])

    def test_upsample_repeats_each_sample(self):
        data = array_bytes([5, -5])
        out = pcm.from_ours(data, 2, 3)
        self.assertEqual(array_values(out), [5, 5, 5, 5, 5, 5, -5, -5, -5,
                                             -5, -5, -5])


def array_bytes(values):
    from array import array
    return array("h", values).tobytes()


def array_values(data):
    from array import array
    out = array("h")
    out.frombytes(data)
    return list(out)


if __name__ == "__main__":
    unittest.main()
