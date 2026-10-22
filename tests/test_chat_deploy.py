"""server/chat/deploy.py: the Cloudflare upload, on a fake opener."""
import importlib.util
import io
import json
import os
import unittest
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "..", "server", "chat", "deploy.py")
SPEC = importlib.util.spec_from_file_location("chat_deploy", PATH)
deploy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(deploy)

ENV = {"CLOUDFLARE_API_TOKEN": "tok", "CLOUDFLARE_ACCOUNT_ID": "acc"}


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class Opener(object):
    """Answers each (method, url-suffix) from a table; records every call."""

    def __init__(self, answers):
        self.answers = answers
        self.calls = []

    def __call__(self, req, timeout=None):
        method = req.get_method()
        url = req.full_url
        self.calls.append((method, url, req.data, dict(req.header_items())))
        for (m, suffix), answer in self.answers.items():
            if m == method and url.endswith(suffix):
                doc = answer(self) if callable(answer) else answer
                body = json.dumps(doc).encode()
                if not doc.get("success"):
                    raise urllib.error.HTTPError(url, 400, "bad", {}, io.BytesIO(body))
                return Response(body)
        raise AssertionError("unexpected call %s %s" % (method, url))


def ok(result=None):
    return {"success": True, "errors": [], "result": result}


def bad(message, code=10000):
    return {"success": False, "errors": [{"code": code, "message": message}], "result": None}


class Metadata(unittest.TestCase):
    def test_binds_the_studio_class(self):
        meta = deploy.metadata(True)
        self.assertEqual(meta["main_module"], "worker.js")
        self.assertEqual(meta["bindings"], [{"type": "durable_object_namespace",
                                             "name": "STUDIO", "class_name": "Studio"}])
        self.assertEqual(meta["migrations"], {"new_tag": "v1", "new_sqlite_classes": ["Studio"]})

    def test_a_later_deploy_sends_no_migration(self):
        self.assertNotIn("migrations", deploy.metadata(False))

    def test_binds_the_files_bucket(self):
        meta = deploy.metadata(False, "skeldar-chat-files")
        self.assertIn({"type": "r2_bucket", "name": "FILES", "bucket_name": "skeldar-chat-files"},
                      meta["bindings"])


class Multipart(unittest.TestCase):
    def test_holds_the_metadata_and_the_module(self):
        body = deploy.multipart({"a": 1}, b"export default {}", "BOUND")
        self.assertIn(b'--BOUND\r\nContent-Disposition: form-data; name="metadata"', body)
        self.assertIn(b"Content-Type: application/json\r\n\r\n{\"a\": 1}", body)
        self.assertIn(b'name="worker.js"; filename="worker.js"\r\n'
                      b"Content-Type: application/javascript+module\r\n\r\nexport default {}", body)
        self.assertTrue(body.endswith(b"\r\n--BOUND--\r\n"))


class Deploy(unittest.TestCase):
    def table(self, upload):
        return {
            ("PUT", "/accounts/acc/workers/scripts/skeldar-chat-staging"): upload,
            ("POST", "/accounts/acc/workers/scripts/skeldar-chat-staging/subdomain"): ok({}),
            ("GET", "/accounts/acc/workers/subdomain"): ok({"subdomain": "evgen"}),
            ("GET", "/accounts/acc/r2/buckets/skeldar-chat-files-staging"): ok({"name": "b"}),
        }

    def test_uploads_enables_and_names_the_url(self):
        opener = Opener(self.table(ok({"id": "x"})))
        url = deploy.deploy("staging", env=ENV, opener=opener)
        self.assertEqual(url, "https://skeldar-chat-staging.evgen.workers.dev")
        method, _url, data, headers = [c for c in opener.calls if c[0] == "PUT"][0]
        self.assertEqual(method, "PUT")
        self.assertIn(b'"new_sqlite_classes": ["Studio"]', data)
        self.assertEqual(headers.get("Authorization"), "Bearer tok")

    def test_a_migration_already_applied_retries_without_it(self):
        def upload(opener):
            first = len([c for c in opener.calls if c[0] == "PUT"]) == 1
            return bad("Migration tag precondition failed") if first else ok({"id": "x"})
        opener = Opener(self.table(upload))
        deploy.deploy("staging", env=ENV, opener=opener)
        puts = [c for c in opener.calls if c[0] == "PUT"]
        self.assertEqual(len(puts), 2)
        self.assertNotIn(b"new_sqlite_classes", puts[1][2])

    def test_a_missing_bucket_is_made_and_bound(self):
        table = self.table(ok({"id": "x"}))
        table[("GET", "/accounts/acc/r2/buckets/skeldar-chat-files-staging")] = bad("not found", 10006)
        table[("POST", "/accounts/acc/r2/buckets")] = ok({"name": "skeldar-chat-files-staging"})
        opener = Opener(table)
        deploy.deploy("staging", env=ENV, opener=opener)
        made = [c for c in opener.calls if c[0] == "POST" and c[1].endswith("/r2/buckets")]
        self.assertEqual(json.loads(made[0][2]), {"name": "skeldar-chat-files-staging"})
        put = [c for c in opener.calls if c[0] == "PUT"][0]
        self.assertIn(b'"bucket_name": "skeldar-chat-files-staging"', put[2])

    def test_r2_off_says_so_before_any_upload(self):
        table = self.table(ok({"id": "x"}))
        table[("GET", "/accounts/acc/r2/buckets/skeldar-chat-files-staging")] = bad(
            "Please enable R2 through the Cloudflare Dashboard.", 10042)
        opener = Opener(table)
        with self.assertRaises(deploy.DeployError) as cm:
            deploy.deploy("staging", env=ENV, opener=opener)
        self.assertIn("R2 is not enabled", str(cm.exception))
        self.assertFalse([c for c in opener.calls if c[0] == "PUT"])

    def test_another_refusal_is_raised_with_cloudflare_s_words(self):
        opener = Opener(self.table(bad("Script too large", 10027)))
        with self.assertRaises(deploy.DeployError) as cm:
            deploy.deploy("staging", env=ENV, opener=opener)
        self.assertIn("10027: Script too large", str(cm.exception))

    def test_missing_credentials_name_the_variable(self):
        with self.assertRaises(deploy.DeployError) as cm:
            deploy.deploy("staging", env={"CLOUDFLARE_ACCOUNT_ID": "acc"}, opener=Opener({}))
        self.assertIn("CLOUDFLARE_API_TOKEN", str(cm.exception))

    def test_an_unknown_target_is_refused(self):
        with self.assertRaises(deploy.DeployError):
            deploy.deploy("live", env=ENV, opener=Opener({}))


class Secrets(unittest.TestCase):
    def test_no_secrets_keeps_the_bindings_as_they_were(self):
        self.assertEqual(deploy.metadata(True)["bindings"],
                         [{"type": "durable_object_namespace", "name": "STUDIO", "class_name": "Studio"}])

    def test_secrets_are_secret_text_bindings(self):
        meta = deploy.metadata(False, secrets={"TURN_KEY_ID": "k1", "TURN_KEY_TOKEN": "t1"})
        self.assertIn({"type": "secret_text", "name": "TURN_KEY_ID", "text": "k1"}, meta["bindings"])
        self.assertIn({"type": "secret_text", "name": "TURN_KEY_TOKEN", "text": "t1"}, meta["bindings"])

    def test_an_empty_secret_is_left_out(self):
        meta = deploy.metadata(False, secrets={"TURN_KEY_ID": None, "TURN_KEY_TOKEN": ""})
        self.assertEqual(len(meta["bindings"]), 1)


class TurnKey(unittest.TestCase):
    URL = "/accounts/acc/calls/turn_keys"

    def setUp(self):
        import tempfile
        self.dir = tempfile.mkdtemp()
        self.old = deploy.KEYS_FILE
        deploy.KEYS_FILE = os.path.join(self.dir, "cloudflare.json")

    def tearDown(self):
        import shutil
        deploy.KEYS_FILE = self.old
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_creates_the_key_and_saves_it(self):
        opener = Opener({("POST", self.URL): ok({"uid": "u" * 32, "secret": "k" * 64, "name": "skeldar-chat"})})
        self.assertEqual(deploy.turn(env=ENV, opener=opener), "u" * 32)
        held = deploy.saved(deploy.TURN_NAMES)
        self.assertEqual(held["turn_key_id"], "u" * 32)
        self.assertEqual(held["turn_key_token"], "k" * 64)
        self.assertEqual(json.loads(opener.calls[0][2]), {"name": "skeldar-chat"})

    def test_it_keeps_what_the_file_already_held(self):
        with open(deploy.KEYS_FILE, "w", encoding="utf-8") as handle:
            json.dump({"CLOUDFLARE_API_TOKEN": "old"}, handle)
        deploy.turn(env=ENV, opener=Opener({("POST", self.URL): ok({"uid": "u", "secret": "k"})}))
        with open(deploy.KEYS_FILE, encoding="utf-8") as handle:
            self.assertEqual(json.load(handle)["CLOUDFLARE_API_TOKEN"], "old")

    def test_a_token_without_calls_rights_says_so(self):
        opener = Opener({("POST", self.URL): bad("Authentication error")})
        with self.assertRaises(deploy.DeployError) as cm:
            deploy.turn(env=ENV, opener=opener)
        self.assertIn("Calls Write", str(cm.exception))

    def test_deploy_sends_saved_turn_secrets(self):
        with open(deploy.KEYS_FILE, "w", encoding="utf-8") as handle:
            json.dump({"turn_key_id": "kid", "turn_key_token": "ktok"}, handle)
        table = Deploy.table(None, ok({"id": "x"}))
        opener = Opener(table)
        deploy.deploy("staging", env=ENV, opener=opener)
        put = [c for c in opener.calls if c[0] == "PUT"][0]
        self.assertIn(b'{"type": "secret_text", "name": "TURN_KEY_ID", "text": "kid"}', put[2])
        self.assertIn(b'{"type": "secret_text", "name": "TURN_KEY_TOKEN", "text": "ktok"}', put[2])

    def test_deploy_without_a_turn_key_sends_no_secrets(self):
        opener = Opener(Deploy.table(None, ok({"id": "x"})))
        deploy.deploy("staging", env=ENV, opener=opener)
        put = [c for c in opener.calls if c[0] == "PUT"][0]
        self.assertNotIn(b"secret_text", put[2])


class Check(unittest.TestCase):
    def test_answers_the_subdomain(self):
        opener = Opener({("GET", "/accounts/acc/workers/subdomain"): ok({"subdomain": "evgen"})})
        self.assertEqual(deploy.check(env=ENV, opener=opener), "evgen")


class NeverShips(unittest.TestCase):
    def test_the_payload_holds_nothing_of_the_server(self):
        import install
        self.assertFalse([p for p in install.payload() if "server" in p.replace("\\", "/").split("/")[:1]])


if __name__ == "__main__":
    unittest.main()


class Keys(unittest.TestCase):
    def test_keeps_the_token_and_finds_the_one_account(self):
        opener = Opener({("GET", "/accounts?per_page=50"): {"success": True, "result": [
            {"id": "a1b2", "name": "Studio"}]}})
        kept = {}
        name = deploy.keys(ask=lambda: " tok123 ", opener=opener, store=kept.update)
        self.assertEqual(name, "Studio")
        self.assertEqual(kept, {"CLOUDFLARE_API_TOKEN": "tok123", "CLOUDFLARE_ACCOUNT_ID": "a1b2"})
        self.assertEqual(opener.calls[0][3].get("Authorization"), "Bearer tok123")

    def test_several_accounts_are_chosen_from(self):
        opener = Opener({("GET", "/accounts?per_page=50"): {"success": True, "result": [
            {"id": "a1", "name": "One"}, {"id": "a2", "name": "Two"}]}})
        kept = {}
        deploy.keys(ask=lambda: "tok", choose=lambda: 2, opener=opener, store=kept.update)
        self.assertEqual(kept["CLOUDFLARE_ACCOUNT_ID"], "a2")

    def test_a_placeholder_is_refused_before_any_request(self):
        opener = Opener({})
        with self.assertRaises(deploy.DeployError):
            deploy.keys(ask=lambda: "<токен>", opener=opener, store=lambda v: None)
        self.assertEqual(opener.calls, [])

    def test_saved_variables_fill_the_process_environment(self):
        original = deploy.saved
        deploy.saved = lambda names=deploy.NAMES_ENV: {"CLOUDFLARE_API_TOKEN": "t",
                                                       "CLOUDFLARE_ACCOUNT_ID": "a"}
        try:
            self.assertEqual(deploy._credentials(os.environ), ("t", "a"))
        finally:
            deploy.saved = original
