"""maya_chat.store in a temp folder."""
import os
import shutil
import tempfile
import unittest

from maya_chat import store as s


class Store(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.st = s.Store(self.dir)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_empty(self):
        self.assertIsNone(self.st.token())
        self.assertIsNone(self.st.me())
        self.assertEqual((self.st.chats(), self.st.messages("c"), self.st.outbox(), self.st.since()),
                         ([], [], [], 0))

    def test_round_trips(self):
        self.st.set_token("skc_x")
        self.st.set_me({"id": "a"})
        self.st.set_chats([{"id": "c"}])
        self.st.set_outbox([{"cid": "1"}])
        self.st.set_since(42)
        self.st.set_messages("dm_a_b", [{"id": "m", "seq": 1}])
        again = s.Store(self.dir)
        self.assertEqual(again.token(), "skc_x")
        self.assertEqual(again.me(), {"id": "a"})
        self.assertEqual(again.chats(), [{"id": "c"}])
        self.assertEqual(again.outbox(), [{"cid": "1"}])
        self.assertEqual(again.since(), 42)
        self.assertEqual(again.messages("dm_a_b"), [{"id": "m", "seq": 1}])
        self.assertFalse([n for n in os.listdir(self.dir) if n.endswith(".tmp")])

    def test_only_the_last_500_are_kept(self):
        self.st.set_messages("c", [{"id": str(i), "seq": i} for i in range(700)])
        rows = self.st.messages("c")
        self.assertEqual((len(rows), rows[0]["seq"], rows[-1]["seq"]), (500, 200, 699))

    def test_a_broken_file_reads_empty(self):
        with open(os.path.join(self.dir, "chats.json"), "w") as handle:
            handle.write("{nope")
        with open(os.path.join(self.dir, "since"), "w") as handle:
            handle.write("x")
        self.assertEqual((self.st.chats(), self.st.since()), ([], 0))
        os.makedirs(os.path.join(self.dir, "messages"))
        with open(os.path.join(self.dir, "messages", "c.jsonl"), "w") as handle:
            handle.write('{"id": "1", "seq": 1}\nbroken\n{"id": "2"}\n')
        self.assertEqual(self.st.messages("c"), [{"id": "1", "seq": 1}])

    def test_forget_keeps_the_history(self):
        self.st.set_token("t")
        self.st.set_me({"id": "a"})
        self.st.set_messages("c", [{"id": "m", "seq": 1}])
        self.st.forget()
        self.assertIsNone(self.st.token())
        self.assertIsNone(self.st.me())
        self.assertEqual(len(self.st.messages("c")), 1)

    def test_a_folder_per_host(self):
        st = s.Store.for_server(self.dir, "https://skeldar-chat-staging.skeldar.workers.dev")
        self.assertEqual(st.root, os.path.join(self.dir, "skeldar-chat-staging.skeldar.workers.dev"))


if __name__ == "__main__":
    unittest.main()
