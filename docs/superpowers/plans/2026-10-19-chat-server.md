# Chat Server Implementation Plan (plan 1 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The chat server of `docs/superpowers/specs/2026-10-19-chat-messenger-design.md` running on a
Cloudflare staging Worker, every HTTP route and WebSocket message of the spec proven by
`verify_chat_server.py`.

**Architecture:** One ES-module Worker (`server/chat/worker.js`) forwards every `/v1/` request to one
SQLite-backed Durable Object `Studio`, which holds the tables, authenticates, answers HTTP and keeps the
WebSockets through the Hibernation API. `server/chat/deploy.py` uploads it through Cloudflare's HTTP API
(no Node on this machine). Plans 2 (client core, `SkeldarAnim/maya_chat/`) and 3 (window, rail,
production) follow once this one is green.

**Tech Stack:** Cloudflare Workers + Durable Objects (SQLite storage API, WebSocket Hibernation API),
JavaScript (ES2022), Python 3 stdlib under `mayapy` for the deploy tool, its unit tests and the
integration verify.

## Global Constraints

- No Node, npm or wrangler: deploy only through `https://api.cloudflare.com/client/v4`.
- Credentials only from the environment: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`; never in a
  file, a commit, a log line or chat.
- Workers: `skeldar-chat-staging` (tests) and `skeldar-chat` (colleagues). This plan deploys staging only.
- Nick: `^[a-z0-9_]{3,24}$` after lower-casing; reserved nicks refused.
- Token: 32 random bytes, base64url, prefixed `skc_`; the server keeps only its sha256 (hex).
- Limits: text ≤ 4000 characters; name ≤ 40; group name ≤ 60; group ≤ 50 members; avatar ≤ 256 KB
  (JPEG or PNG); per user ≤ 20 messages and ≤ 30 HTTP requests in any 10 s (`too_many`, 429).
- Events kept 30 days; a `hello` with `since` older than that, or `since` ≤ 0, answers `resync`.
- Errors are `{error: <code>, text: <one line>}` with a 4xx status; the client shows `text`.
- Python runs under Maya's interpreter: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe'`
  (there is no system Python; `python` hangs). Unit tests:
  `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`
- `server/` never ships: it is outside `SkeldarAnim/`, which is all `install.payload()` reads.
- Other sessions commit to `main` in this repository: stage only this plan's files by path, never
  `git add -A`.

## Files

| file | responsibility |
|---|---|
| `server/chat/worker.js` | the Worker's `fetch` (forward to the Durable Object) and the `Studio` class: schema, auth, limits, routes, events, WebSockets, pruning |
| `server/chat/deploy.py` | `check` / `staging` / `production`: upload the module with its binding and migration, enable workers.dev, print the URL |
| `server/chat/README.md` | what the animator sets up once, how to deploy, how to verify |
| `tests/test_chat_deploy.py` | unit tests of `deploy.py` with a fake opener |
| `docs/superpowers/plans/chat/wsclient.py` | a small stdlib WebSocket client for the verify |
| `docs/superpowers/plans/verify_chat_server.py` | the integration verify against staging, phased |

The worker grows task by task. Each task says exactly which methods to add to `Studio` and which rows to
add to the module-level `ROUTES` table; nothing is ever replaced except where a step says "replace".

---

### Task 0: Prerequisites (the animator, once)

Not code. The plan stops here until it is done.

- [ ] **Step 1: The animator creates the Cloudflare account and token**

Tell the animator, in Russian, and wait for «готово»:
1. Sign up at https://dash.cloudflare.com (free plan).
2. Open **Workers & Pages** once and accept the `*.workers.dev` subdomain it offers (it names the URL).
3. **My Profile → API Tokens → Create Token → Create Custom Token** with permissions
   *Account · Workers Scripts · Edit* and *Account · Account Settings · Read*, for their account.
4. In PowerShell, as their user (values never pasted into chat):
   `[Environment]::SetEnvironmentVariable('CLOUDFLARE_API_TOKEN','<token>','User')` and the same for
   `CLOUDFLARE_ACCOUNT_ID` (the id on the dashboard's right side), then restart the Claude app so its
   shells see them.

- [ ] **Step 2: Nothing to commit.** Task 1's `check` command proves the setup.

---

### Task 1: The deploy tool

**Files:**
- Create: `server/chat/deploy.py`
- Create: `server/chat/worker.js` (a placeholder module answering `/v1/health`, replaced in Task 2)
- Create: `server/chat/README.md`
- Test: `tests/test_chat_deploy.py`

**Interfaces:**
- Produces: `deploy.metadata(with_migration: bool) -> dict`, `deploy.multipart(meta: dict, source: bytes, boundary: str) -> bytes`,
  `deploy.request(method, url, token, body=None, ctype=None, opener=...) -> object` (Cloudflare's `result`),
  `deploy.deploy(target: str, env=os.environ, opener=...) -> str` (the Worker's URL),
  `deploy.check(env=os.environ, opener=...) -> str` (the account's workers.dev subdomain),
  `deploy.DeployError`. Command line: `mayapy server/chat/deploy.py check|staging|production`, which prints
  `URL <url>` on success.

- [ ] **Step 1: Write the failing tests**

`tests/test_chat_deploy.py`:

```python
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
        }

    def test_uploads_enables_and_names_the_url(self):
        opener = Opener(self.table(ok({"id": "x"})))
        url = deploy.deploy("staging", env=ENV, opener=opener)
        self.assertEqual(url, "https://skeldar-chat-staging.evgen.workers.dev")
        method, _url, data, headers = opener.calls[0]
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
```

- [ ] **Step 2: Run them to verify they fail**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_chat_deploy -v`
Expected: ERROR, `FileNotFoundError` for `server/chat/deploy.py`.

- [ ] **Step 3: Write the deploy tool**

`server/chat/deploy.py`:

```python
"""Deploy the chat server to Cloudflare through its HTTP API - no Node, no wrangler.

    mayapy server/chat/deploy.py check        the token works; prints the workers.dev subdomain
    mayapy server/chat/deploy.py staging      uploads skeldar-chat-staging; prints "URL <url>"
    mayapy server/chat/deploy.py production   uploads skeldar-chat

Credentials come only from CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID.
"""
import json
import os
import sys
import urllib.error
import urllib.request
import uuid

API = "https://api.cloudflare.com/client/v4"
NAMES = {"staging": "skeldar-chat-staging", "production": "skeldar-chat"}
COMPAT = "2025-06-01"
MIGRATION = "v1"
HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "worker.js")


class DeployError(Exception):
    pass


def metadata(with_migration):
    meta = {
        "main_module": "worker.js",
        "compatibility_date": COMPAT,
        "bindings": [{"type": "durable_object_namespace", "name": "STUDIO", "class_name": "Studio"}],
    }
    if with_migration:
        meta["migrations"] = {"new_tag": MIGRATION, "new_sqlite_classes": ["Studio"]}
    return meta


def multipart(meta, source, boundary):
    parts = [
        b"--" + boundary.encode() + b"\r\n"
        b'Content-Disposition: form-data; name="metadata"\r\n'
        b"Content-Type: application/json\r\n\r\n" + json.dumps(meta).encode() + b"\r\n",
        b"--" + boundary.encode() + b"\r\n"
        b'Content-Disposition: form-data; name="worker.js"; filename="worker.js"\r\n'
        b"Content-Type: application/javascript+module\r\n\r\n" + source + b"\r\n",
    ]
    return b"".join(parts) + b"--" + boundary.encode() + b"--\r\n"


def request(method, url, token, body=None, ctype=None, opener=urllib.request.urlopen):
    headers = {"Authorization": "Bearer " + token}
    if ctype:
        headers["Content-Type"] = ctype
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with opener(req, timeout=60) as answer:
            data = answer.read()
    except urllib.error.HTTPError as exc:
        data = exc.read()
    try:
        doc = json.loads(data or b"{}")
    except ValueError:
        raise DeployError("Cloudflare answered something that is not JSON: %r" % data[:200])
    if not doc.get("success"):
        words = "; ".join("%s: %s" % (e.get("code"), e.get("message")) for e in doc.get("errors") or [])
        raise DeployError(words or "Cloudflare refused the request")
    return doc.get("result")


def _credentials(env):
    for name in ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"):
        if not env.get(name):
            raise DeployError("Set %s in the environment first (server/chat/README.md)" % name)
    return env["CLOUDFLARE_API_TOKEN"], env["CLOUDFLARE_ACCOUNT_ID"]


def check(env=os.environ, opener=urllib.request.urlopen):
    token, account = _credentials(env)
    result = request("GET", "%s/accounts/%s/workers/subdomain" % (API, account), token, opener=opener)
    return result["subdomain"]


def deploy(target, env=os.environ, opener=urllib.request.urlopen):
    if target not in NAMES:
        raise DeployError("Target is staging or production, not %r" % target)
    token, account = _credentials(env)
    name = NAMES[target]
    with open(SOURCE, "rb") as handle:
        source = handle.read()
    script = "%s/accounts/%s/workers/scripts/%s" % (API, account, name)

    def upload(with_migration):
        boundary = "skeldar" + uuid.uuid4().hex
        body = multipart(metadata(with_migration), source, boundary)
        return request("PUT", script, token, body, "multipart/form-data; boundary=" + boundary,
                       opener=opener)

    try:
        upload(True)
    except DeployError as exc:
        if "migration" not in str(exc).lower():
            raise
        upload(False)
    request("POST", script + "/subdomain", token, json.dumps({"enabled": True}).encode(),
            "application/json", opener=opener)
    return "https://%s.%s.workers.dev" % (name, check(env, opener))


def main(argv):
    if len(argv) != 2 or argv[1] not in ("check", "staging", "production"):
        print(__doc__)
        return 2
    try:
        if argv[1] == "check":
            print("SUBDOMAIN " + check())
        else:
            print("URL " + deploy(argv[1]))
    except DeployError as exc:
        print("FAILED " + str(exc))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

`server/chat/worker.js` (placeholder until Task 2):

```js
export default {
  async fetch(request) {
    const url = new URL(request.url);
    if (url.pathname === "/v1/health") return Response.json({ ok: true, placeholder: true });
    return Response.json({ error: "not_found", text: "No such address" }, { status: 404 });
  },
};
export class Studio {
  constructor(ctx, env) { this.ctx = ctx; }
  async fetch() { return new Response("placeholder", { status: 503 }); }
}
```

`server/chat/README.md`:

```markdown
# Skeldar chat server

The server of the in-Maya messenger (spec: docs/superpowers/specs/2026-10-19-chat-messenger-design.md).
It never ships with the plugin.

## Once (the animator)
1. A Cloudflare account (free); open Workers & Pages once and accept the workers.dev subdomain.
2. An API token: Account · Workers Scripts · Edit, Account · Account Settings · Read.
3. User environment variables CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID; restart the Claude app.

## Deploy
    & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' server/chat/deploy.py check
    & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' server/chat/deploy.py staging

## Verify (against staging)
    $env:CHAT_SERVER = '<the URL staging printed>'
    & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/verify_chat_server.py all
```

- [ ] **Step 4: Run the unit tests**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest tests.test_chat_deploy -v`
Expected: 9 tests, OK.

- [ ] **Step 5: Check the real account and deploy the placeholder**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' server/chat/deploy.py check`
Expected: `SUBDOMAIN <their subdomain>`. A `FAILED` names what is missing; send it to the animator.

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' server/chat/deploy.py staging`
Expected: `URL https://skeldar-chat-staging.<sub>.workers.dev`. Then
`Invoke-RestMethod <url>/v1/health` → `ok: True, placeholder: True` (a new workers.dev route can take up
to a minute; retry, never loop).

If the PUT is refused for a field name or part name, read Cloudflare's own message and fix `metadata` /
`multipart` and their tests to match it; record what was measured in the plan's addendum.

- [ ] **Step 6: Commit**

```bash
git add server/chat/deploy.py server/chat/worker.js server/chat/README.md tests/test_chat_deploy.py
git commit -m "feat(chat): the server's deploy tool, through Cloudflare's HTTP API"
```

---

### Task 2: The Studio object: schema, sign-in, events, the verify

**Files:**
- Replace: `server/chat/worker.js`
- Create: `docs/superpowers/plans/chat/wsclient.py`
- Create: `docs/superpowers/plans/verify_chat_server.py`

**Interfaces:**
- Produces (HTTP): `GET /v1/health` (open) → `{ok: true}`; `POST /v1/register {nick, name?}` (open) →
  `{token, user}`; `GET /v1/me` → `user`; `DELETE /v1/me` → `{ok: true}`.
  `user` is `{id, nick, name, avatar_v}`.
- Produces (inside `Studio`, used by every later task): `refuse(code, text, status)`,
  `this.body(request)`, `this.user(row)`, `this.limit(key, most)`,
  `this.emit({chat, uid, kind, payload}) -> seq`, `this.deliver(event, uids)`,
  `this.memberIds(chat)`, `this.friendIds(uid)`, `this.presence(uid)`, the `ROUTES` table
  `[method, RegExp, methodName, open]`.
- Produces (verify): `gate(name, ok, detail)`, `call(...)`, `jcall(...)`, `Users.make(label) -> (token, user)`,
  `PHASES` dict of name → function; `wsclient.WS(url, token)`.

- [ ] **Step 1: Write the verify first (it is the failing test)**

`docs/superpowers/plans/chat/wsclient.py`:

```python
"""A small stdlib WebSocket client for the chat verify (text frames, masked, no extensions)."""
import base64
import json
import os
import socket
import ssl
import struct
import time
import urllib.parse


class WS(object):
    def __init__(self, url, token, timeout=10):
        parts = urllib.parse.urlparse(url)
        host = parts.hostname
        port = parts.port or (443 if parts.scheme == "wss" else 80)
        raw = socket.create_connection((host, port), timeout=timeout)
        if parts.scheme == "wss":
            raw = ssl.create_default_context().wrap_socket(raw, server_hostname=host)
        self.sock = raw
        key = base64.b64encode(os.urandom(16)).decode()
        head = ("GET %s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n"
                "Authorization: Bearer %s\r\n\r\n" % (parts.path or "/", host, key, token))
        self.sock.sendall(head.encode())
        self.buf = b""
        while b"\r\n\r\n" not in self.buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise IOError("closed during the handshake")
            self.buf += chunk
        answer, self.buf = self.buf.split(b"\r\n\r\n", 1)
        self.status = int(answer.split(b" ")[1])
        if self.status != 101:
            raise IOError("handshake answered %d: %r" % (self.status, answer[:300]))

    def _frame(self, opcode, data):
        mask = os.urandom(4)
        n = len(data)
        if n < 126:
            head = struct.pack("!BB", 0x80 | opcode, 0x80 | n)
        elif n < 65536:
            head = struct.pack("!BBH", 0x80 | opcode, 0x80 | 126, n)
        else:
            head = struct.pack("!BBQ", 0x80 | opcode, 0x80 | 127, n)
        self.sock.sendall(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def send_text(self, text):
        self._frame(0x1, text.encode())

    def send(self, obj):
        self.send_text(json.dumps(obj))

    def _read(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise IOError("closed")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def recv_text(self, timeout=5):
        self.sock.settimeout(timeout)
        while True:
            b1, b2 = self._read(2)
            opcode, n = b1 & 0x0F, b2 & 0x7F
            if n == 126:
                n = struct.unpack("!H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack("!Q", self._read(8))[0]
            mask = self._read(4) if b2 & 0x80 else None
            payload = self._read(n)
            if mask:
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            if opcode == 0x8:
                raise IOError("closed by the server")
            if opcode == 0x9:
                self._frame(0xA, payload)
                continue
            if opcode in (0x0, 0x1):
                return payload.decode()

    def events(self, seconds):
        """Every JSON event that arrives within `seconds`."""
        out = []
        deadline = time.time() + seconds
        while time.time() < deadline:
            try:
                text = self.recv_text(max(0.05, deadline - time.time()))
            except (socket.timeout, ssl.SSLError):
                break
            if text != "pong":
                out.append(json.loads(text))
        return out

    def until(self, test, seconds=5):
        """The first event `test` accepts, and everything seen before it."""
        seen = []
        deadline = time.time() + seconds
        while time.time() < deadline:
            try:
                text = self.recv_text(max(0.05, deadline - time.time()))
            except (socket.timeout, ssl.SSLError):
                break
            if text == "pong":
                continue
            event = json.loads(text)
            if test(event):
                return event, seen
            seen.append(event)
        return None, seen

    def close(self):
        try:
            self._frame(0x8, struct.pack("!H", 1000))
        except Exception:
            pass
        self.sock.close()
```

`docs/superpowers/plans/verify_chat_server.py`:

```python
"""The chat server against staging (plan 2026-10-19-chat-server).

    $env:CHAT_SERVER = 'https://skeldar-chat-staging.<sub>.workers.dev'
    mayapy docs/superpowers/plans/verify_chat_server.py all        (or a phase name)

Every user it makes is named zzt_<hex>_<label> and deleted at the end (DELETE /v1/me).
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat"))
import wsclient  # noqa: E402

SERVER = os.environ.get("CHAT_SERVER", "").rstrip("/")
RUN = uuid.uuid4().hex[:6]
GATES = []


def gate(name, ok, detail=""):
    GATES.append((name, bool(ok)))
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" - %s" % (detail,)) if detail != "" else ""))


def call(method, path, token=None, body=None, raw=None, ctype=None):
    headers = {}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["content-type"] = "application/json"
    if raw is not None:
        data = raw
        headers["content-type"] = ctype
    if token:
        headers["authorization"] = "Bearer " + token
    req = urllib.request.Request(SERVER + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as answer:
            return answer.status, answer.read(), answer.headers.get("content-type", "")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), exc.headers.get("content-type", "")


def jcall(method, path, token=None, body=None, raw=None, ctype=None):
    status, data, ctype_ = call(method, path, token, body, raw, ctype)
    return status, (json.loads(data) if data and "json" in ctype_ else data)


class Users(object):
    made = []

    @classmethod
    def make(cls, label):
        nick = "zzt_%s_%s" % (RUN, label)
        status, doc = jcall("POST", "/v1/register", body={"nick": nick, "name": label.title()})
        if status != 200:
            raise RuntimeError("register %s answered %s %s" % (nick, status, doc))
        cls.made.append(doc["token"])
        return doc["token"], doc["user"]

    @classmethod
    def clean(cls):
        for token in cls.made:
            call("DELETE", "/v1/me", token)


def ws(token):
    return wsclient.WS(SERVER.replace("https://", "wss://") + "/v1/ws", token)


# ------------------------------------------------------------------ phases

def phase_signin():
    status, doc = jcall("GET", "/v1/health")
    gate("health answers", status == 200 and doc.get("ok") is True, doc)
    token, user = Users.make("alice")
    gate("register gives a skc_ token and a user", token.startswith("skc_") and user["nick"].endswith("_alice"), user)
    status, doc = jcall("POST", "/v1/register", body={"nick": user["nick"].upper()})
    gate("a taken nick is refused, whatever its case", status == 409 and doc.get("error") == "nick_taken", doc)
    status, doc = jcall("POST", "/v1/register", body={"nick": "a b"})
    gate("a bad nick is refused", status == 400 and doc.get("error") == "bad_nick", doc)
    status, doc = jcall("POST", "/v1/register", body={"nick": "admin"})
    gate("a reserved nick is refused", status == 409 and doc.get("error") == "nick_taken", doc)
    status, doc = jcall("GET", "/v1/me", token)
    gate("the token signs in", status == 200 and doc.get("id") == user["id"], doc)
    status, doc = jcall("GET", "/v1/me", "skc_wrong")
    gate("a wrong token is refused", status == 401 and doc.get("error") == "bad_token", doc)
    status, doc = jcall("GET", "/v1/me")
    gate("no token is refused", status == 401, doc)


PHASES = {"signin": phase_signin}


def main(argv):
    if not SERVER:
        print("Set CHAT_SERVER to the staging URL first")
        return 2
    names = list(PHASES) if argv[1:] in ([], ["all"]) else argv[1:]
    try:
        for name in names:
            print("--- " + name)
            PHASES[name]()
    finally:
        Users.clean()
    failed = [n for n, ok in GATES if not ok]
    print("%d of %d gates failed" % (len(failed), len(GATES)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 2: Run it against the placeholder to see it fail**

Run: `$env:CHAT_SERVER = '<staging URL>'; & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/verify_chat_server.py signin`
Expected: FAIL at `health answers` is PASS (the placeholder answers it), then `register` raises
`RuntimeError: register ... answered 404`. That is the failing state.

- [ ] **Step 3: Write the worker**

Replace `server/chat/worker.js`:

```js
// The Skeldar chat server: one Worker, one SQLite Durable Object "Studio" holding the whole studio.
// Spec: docs/superpowers/specs/2026-10-19-chat-messenger-design.md
import { DurableObject } from "cloudflare:workers";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (!url.pathname.startsWith("/v1/")) return json({ error: "not_found", text: "No such address" }, 404);
    const stub = env.STUDIO.get(env.STUDIO.idFromName("studio"));
    return stub.fetch(request);
  },
};

const NICK = /^[a-z0-9_]{3,24}$/;
const RESERVED = new Set(["admin", "skeldar", "system", "support", "root", "chat", "null", "undefined"]);
const DAY = 86400000;
const KEEP_EVENTS = 30 * DAY;
const TEXT_MAX = 4000;
const NAME_MAX = 40;
const GROUP_NAME_MAX = 60;
const GROUP_MAX = 50;
const AVATAR_MAX = 256 * 1024;

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status, headers: { "content-type": "application/json; charset=utf-8" },
  });
}

class Refusal extends Error {
  constructor(code, text, status) { super(text); this.code = code; this.status = status; }
}
function refuse(code, text, status = 400) { throw new Refusal(code, text, status); }

function hex(bytes) { return [...bytes].map((b) => b.toString(16).padStart(2, "0")).join(""); }
function randomHex(n) { const b = new Uint8Array(n); crypto.getRandomValues(b); return hex(b); }
function b64url(bytes) {
  return btoa(String.fromCharCode(...bytes)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}
async function sha256(text) {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return hex(new Uint8Array(d));
}
function clean(text, most) { return String(text ?? "").replace(/\s+$/u, "").replace(/^\s+/u, "").slice(0, most); }

const SCHEMA = [
  `CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, nick TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
     token_hash TEXT UNIQUE NOT NULL, avatar BLOB, avatar_type TEXT, avatar_v INTEGER NOT NULL DEFAULT 0,
     created INTEGER NOT NULL, last_seen INTEGER NOT NULL DEFAULT 0)`,
  `CREATE TABLE IF NOT EXISTS friends (a TEXT NOT NULL, b TEXT NOT NULL, since INTEGER NOT NULL, PRIMARY KEY (a, b))`,
  `CREATE TABLE IF NOT EXISTS requests (from_id TEXT NOT NULL, to_id TEXT NOT NULL, at INTEGER NOT NULL,
     PRIMARY KEY (from_id, to_id))`,
  `CREATE TABLE IF NOT EXISTS chats (id TEXT PRIMARY KEY, kind TEXT NOT NULL, name TEXT NOT NULL DEFAULT '',
     admin TEXT, avatar BLOB, avatar_type TEXT, avatar_v INTEGER NOT NULL DEFAULT 0, created INTEGER NOT NULL,
     last_seq INTEGER NOT NULL DEFAULT 0)`,
  `CREATE TABLE IF NOT EXISTS members (chat TEXT NOT NULL, uid TEXT NOT NULL, joined INTEGER NOT NULL,
     read_upto INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (chat, uid))`,
  `CREATE INDEX IF NOT EXISTS members_uid ON members (uid)`,
  `CREATE TABLE IF NOT EXISTS messages (chat TEXT NOT NULL, seq INTEGER NOT NULL, id TEXT UNIQUE NOT NULL,
     from_id TEXT NOT NULL, cid TEXT NOT NULL, text TEXT NOT NULL, reply_to TEXT, at INTEGER NOT NULL,
     edited_at INTEGER, deleted INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (chat, seq))`,
  `CREATE UNIQUE INDEX IF NOT EXISTS messages_cid ON messages (from_id, cid)`,
  `CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT, chat TEXT, uid TEXT,
     kind TEXT NOT NULL, payload TEXT NOT NULL, at INTEGER NOT NULL)`,
  `CREATE INDEX IF NOT EXISTS events_at ON events (at)`,
];

export class Studio extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.sql = ctx.storage.sql;
    for (const statement of SCHEMA) this.sql.exec(statement);
    this.hits = new Map();
    ctx.setWebSocketAutoResponse(new WebSocketRequestResponsePair("ping", "pong"));
    ctx.blockConcurrencyWhile(async () => {
      if ((await ctx.storage.getAlarm()) == null) await ctx.storage.setAlarm(Date.now() + DAY);
    });
  }

  async fetch(request) {
    const url = new URL(request.url);
    try {
      const found = this.route(request.method, url.pathname);
      if (!found) refuse("not_found", "No such address", 404);
      const [handler, params, open] = found;
      const me = open ? null : await this.auth(request);
      if (me) this.limit(me.id + ":http", 30);
      return await handler.call(this, { request, url, params, me });
    } catch (e) {
      if (e instanceof Refusal) return json({ error: e.code, text: e.message }, e.status);
      return json({ error: "server", text: "The server failed: " + e.message }, 500);
    }
  }

  route(method, path) {
    for (const [m, pattern, name, open] of ROUTES) {
      if (m !== method) continue;
      const hit = path.match(pattern);
      if (hit) return [this[name], hit.slice(1), !!open];
    }
    return null;
  }

  async auth(request) {
    const header = request.headers.get("authorization") || "";
    const token = header.startsWith("Bearer ") ? header.slice(7).trim() : "";
    if (!token) refuse("bad_token", "Sign in first", 401);
    const row = this.sql.exec("SELECT * FROM users WHERE token_hash = ?", await sha256(token)).toArray()[0];
    if (!row) refuse("bad_token", "This sign-in code is not valid", 401);
    return row;
  }

  limit(key, most) {
    const now = Date.now();
    const recent = (this.hits.get(key) || []).filter((t) => now - t < 10000);
    if (recent.length >= most) refuse("too_many", "Too fast - wait a few seconds", 429);
    recent.push(now);
    this.hits.set(key, recent);
  }

  async body(request) {
    try { return await request.json(); } catch { refuse("bad_request", "The request is not JSON"); }
  }

  user(row) { return { id: row.id, nick: row.nick, name: row.name, avatar_v: row.avatar_v }; }

  userById(id) {
    const row = this.sql.exec("SELECT * FROM users WHERE id = ?", id).toArray()[0];
    if (!row) refuse("no_user", "No such person", 404);
    return row;
  }

  // ---------------------------------------------------------------- events
  // An event goes to a chat's members (chat), one user (uid), or everybody (neither).
  emit({ chat = null, uid = null, kind, payload }) {
    const row = this.sql.exec(
      "INSERT INTO events (chat, uid, kind, payload, at) VALUES (?, ?, ?, ?, ?) RETURNING seq",
      chat, uid, kind, JSON.stringify(payload), Date.now()).one();
    const event = { seq: row.seq, kind, ...payload };
    if (chat) this.deliver(event, this.memberIds(chat));
    else if (uid) this.deliver(event, [uid]);
    else this.deliver(event, null);
    return row.seq;
  }

  deliver(event, uids) {
    const text = JSON.stringify(event);
    const sockets = uids === null ? this.ctx.getWebSockets() : [...new Set(uids)].flatMap((u) => this.ctx.getWebSockets(u));
    for (const ws of sockets) { try { ws.send(text); } catch { /* a closing socket */ } }
  }

  memberIds(chat) { return this.sql.exec("SELECT uid FROM members WHERE chat = ?", chat).toArray().map((r) => r.uid); }

  friendIds(uid) {
    return this.sql.exec("SELECT b AS id FROM friends WHERE a = ? UNION SELECT a AS id FROM friends WHERE b = ?", uid, uid)
      .toArray().map((r) => r.id);
  }

  presence(uid) {
    const row = this.sql.exec("SELECT last_seen FROM users WHERE id = ?", uid).toArray()[0];
    return { online: this.ctx.getWebSockets(uid).length > 0, last_seen: row ? row.last_seen : 0 };
  }

  async alarm() {
    this.sql.exec("DELETE FROM events WHERE at < ?", Date.now() - KEEP_EVENTS);
    await this.ctx.storage.setAlarm(Date.now() + DAY);
  }

  // ---------------------------------------------------------------- routes: sign-in
  health() { return json({ ok: true }); }

  async register({ request }) {
    this.limit("ip:" + (request.headers.get("cf-connecting-ip") || "?"), 20);
    const b = await this.body(request);
    const nick = String(b.nick ?? "").trim().toLowerCase();
    if (!NICK.test(nick)) refuse("bad_nick", "A nick is 3-24 letters a-z, digits or _");
    if (RESERVED.has(nick) || this.sql.exec("SELECT 1 FROM users WHERE nick = ?", nick).toArray().length) {
      refuse("nick_taken", "@" + nick + " is taken", 409);
    }
    const bytes = new Uint8Array(32);
    crypto.getRandomValues(bytes);
    const token = "skc_" + b64url(bytes);
    const id = randomHex(8);
    const name = clean(b.name, NAME_MAX) || nick;
    this.sql.exec("INSERT INTO users (id, nick, name, token_hash, created) VALUES (?, ?, ?, ?, ?)",
      id, nick, name, await sha256(token), Date.now());
    return json({ token, user: { id, nick, name, avatar_v: 0 } });
  }

  getMe({ me }) { return json(this.user(me)); }

  deleteMe({ me }) {
    this.forget(me.id);
    return json({ ok: true });
  }

  forget(uid) {
    for (const ws of this.ctx.getWebSockets(uid)) { try { ws.close(1000, "account deleted"); } catch { /* gone */ } }
    this.sql.exec("DELETE FROM friends WHERE a = ? OR b = ?", uid, uid);
    this.sql.exec("DELETE FROM requests WHERE from_id = ? OR to_id = ?", uid, uid);
    this.sql.exec("DELETE FROM users WHERE id = ?", uid);
  }
}

// [method, path, Studio method, open (no token)]
const ROUTES = [
  ["GET", /^\/v1\/health$/, "health", true],
  ["POST", /^\/v1\/register$/, "register", true],
  ["GET", /^\/v1\/me$/, "getMe"],
  ["DELETE", /^\/v1\/me$/, "deleteMe"],
];
```

- [ ] **Step 4: Deploy and run the verify**

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' server/chat/deploy.py staging`
Expected: `URL ...` (the first real upload applies migration `v1`; the placeholder had none).

Run: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs/superpowers/plans/verify_chat_server.py signin`
Expected: `0 of 8 gates failed`.

- [ ] **Step 5: Commit**

```bash
git add server/chat/worker.js docs/superpowers/plans/chat/wsclient.py docs/superpowers/plans/verify_chat_server.py
git commit -m "feat(chat): the Studio object - schema, sign-in by nick, events"
```

---

### Task 3: Profile and avatars

**Files:**
- Modify: `server/chat/worker.js` (methods in `Studio`, rows in `ROUTES`)
- Modify: `docs/superpowers/plans/verify_chat_server.py` (a phase)

**Interfaces:**
- Consumes: `refuse`, `this.body`, `this.user`, `this.userById`, `this.emit`.
- Produces: `PATCH /v1/me {name}` → `user`; `PUT /v1/me/avatar` (raw JPEG/PNG) → `user`;
  `GET /v1/avatar/u/<id>` → the picture; `this.picture(request) -> {bytes, type}`;
  `this.servePicture(bytes, type)`; event `user {user}` to everybody.

- [ ] **Step 1: Add the failing phase**

Add to `verify_chat_server.py` above `PHASES`, and add `"profile": phase_profile` to `PHASES`:

```python
PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
       b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")


def phase_profile():
    token, user = Users.make("bob")
    status, doc = jcall("PATCH", "/v1/me", token, {"name": "  Bob Builder  "})
    gate("a name is trimmed and kept", status == 200 and doc["name"] == "Bob Builder", doc)
    status, doc = jcall("PATCH", "/v1/me", token, {"name": "   "})
    gate("an empty name is refused", status == 400 and doc.get("error") == "bad_name", doc)
    status, doc = jcall("PUT", "/v1/me/avatar", token, raw=PNG, ctype="image/png")
    gate("a PNG avatar is taken, its version up", status == 200 and doc["avatar_v"] == 1, doc)
    status, data, ctype = call("GET", "/v1/avatar/u/" + user["id"], token)
    gate("the avatar comes back byte for byte", status == 200 and data == PNG and ctype == "image/png", ctype)
    status, doc = jcall("PUT", "/v1/me/avatar", token, raw=b"GIF89a....", ctype="image/gif")
    gate("a picture that is not JPEG or PNG is refused", status == 400 and doc.get("error") == "bad_picture", doc)
    status, doc = jcall("PUT", "/v1/me/avatar", token, raw=PNG + b"\0" * (256 * 1024), ctype="image/png")
    gate("an avatar over 256 KB is refused", status == 413 and doc.get("error") == "too_big", doc)
```

Run: `... verify_chat_server.py profile` → Expected: FAIL on every gate (404 `not_found`).

- [ ] **Step 2: Implement**

Add to `Studio` (after `deleteMe`):

```js
  // ---------------------------------------------------------------- routes: profile
  async patchMe({ request, me }) {
    const b = await this.body(request);
    const name = clean(b.name, NAME_MAX);
    if (!name) refuse("bad_name", "A name cannot be empty");
    this.sql.exec("UPDATE users SET name = ? WHERE id = ?", name, me.id);
    const user = this.user(this.userById(me.id));
    this.emit({ kind: "user", payload: { user } });
    return json(user);
  }

  async picture(request) {
    const bytes = new Uint8Array(await request.arrayBuffer());
    if (bytes.length > AVATAR_MAX) refuse("too_big", "A picture is at most 256 KB", 413);
    if (bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) return { bytes, type: "image/jpeg" };
    if (bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e && bytes[3] === 0x47) return { bytes, type: "image/png" };
    refuse("bad_picture", "A picture is a JPEG or a PNG");
  }

  servePicture(bytes, type) {
    if (!bytes) refuse("no_picture", "No picture", 404);
    return new Response(bytes, { headers: { "content-type": type, "cache-control": "private, max-age=31536000" } });
  }

  async putMyAvatar({ request, me }) {
    const { bytes, type } = await this.picture(request);
    this.sql.exec("UPDATE users SET avatar = ?, avatar_type = ?, avatar_v = avatar_v + 1 WHERE id = ?", bytes, type, me.id);
    const user = this.user(this.userById(me.id));
    this.emit({ kind: "user", payload: { user } });
    return json(user);
  }

  userAvatar({ params }) {
    const row = this.userById(params[0]);
    return this.servePicture(row.avatar, row.avatar_type);
  }
```

Add to `ROUTES`:

```js
  ["PATCH", /^\/v1\/me$/, "patchMe"],
  ["PUT", /^\/v1\/me\/avatar$/, "putMyAvatar"],
  ["GET", /^\/v1\/avatar\/u\/([0-9a-f]{16})$/, "userAvatar"],
```

- [ ] **Step 3: Deploy and verify**

Run: `... deploy.py staging`, then `... verify_chat_server.py signin profile`
Expected: `0 of 14 gates failed`.

- [ ] **Step 4: Commit**

```bash
git add server/chat/worker.js docs/superpowers/plans/verify_chat_server.py
git commit -m "feat(chat): profile name and avatar pictures"
```

---

### Task 4: Friends

**Files:**
- Modify: `server/chat/worker.js`
- Modify: `docs/superpowers/plans/verify_chat_server.py`

**Interfaces:**
- Consumes: Task 2's helpers.
- Produces: `GET /v1/users?q=<prefix>` → `{users: [user + relation]}` (`relation` is `"friend"`,
  `"incoming"`, `"outgoing"` or `null`); `GET /v1/friends` → `{friends, incoming, outgoing}` (each a `user`
  plus `presence`); `POST /v1/friends/request {nick}` → `{state: "requested" | "friends"}`;
  `POST /v1/friends/accept|decline|cancel {user}` → `{ok: true}`; `DELETE /v1/friends/<id>` → `{ok: true}`;
  `this.areFriends(a, b) -> bool`; events `friend_request {user}`, `request_sent {user}`,
  `friend_added {user}`, `request_cancelled {from_id, to_id}`, `friend_removed {user_id}`.

- [ ] **Step 1: Add the failing phase** (and `"friends": phase_friends` to `PHASES`)

```python
def phase_friends():
    ta, a = Users.make("fa")
    tb, b = Users.make("fb")
    tc, c = Users.make("fc")
    status, doc = jcall("GET", "/v1/users?q=zzt_%s_f" % RUN, ta)
    nicks = sorted(u["nick"] for u in doc.get("users", []))
    gate("search by prefix finds the others, not me", status == 200 and nicks == sorted([b["nick"], c["nick"]]), nicks)
    status, doc = jcall("GET", "/v1/users?q=zzt%25", ta)
    gate("a % in the query is a letter, not a wildcard", status == 200 and doc["users"] == [], doc)
    status, doc = jcall("POST", "/v1/friends/request", ta, {"nick": b["nick"]})
    gate("a request is sent", status == 200 and doc["state"] == "requested", doc)
    status, doc = jcall("GET", "/v1/friends", tb)
    gate("the other sees it incoming", [u["id"] for u in doc["incoming"]] == [a["id"]], doc)
    status, doc = jcall("POST", "/v1/friends/accept", tb, {"user": a["id"]})
    gate("accept", status == 200, doc)
    status, doc = jcall("GET", "/v1/friends", ta)
    gate("they are friends both ways", [u["id"] for u in doc["friends"]] == [b["id"]] and not doc["outgoing"], doc)
    status, doc = jcall("POST", "/v1/friends/request", tc, {"nick": a["nick"]})
    status, doc = jcall("POST", "/v1/friends/request", ta, {"nick": c["nick"]})
    gate("asking someone who already asked you makes you friends", doc.get("state") == "friends", doc)
    status, doc = jcall("DELETE", "/v1/friends/" + c["id"], ta)
    status, doc = jcall("GET", "/v1/friends", tc)
    gate("remove takes the friend off both lists", doc["friends"] == [], doc)
    jcall("POST", "/v1/friends/request", tc, {"nick": b["nick"]})
    status, doc = jcall("POST", "/v1/friends/cancel", tc, {"user": b["id"]})
    status, doc = jcall("GET", "/v1/friends", tb)
    gate("cancel takes the request back", doc["incoming"] == [], doc)
    jcall("POST", "/v1/friends/request", tc, {"nick": b["nick"]})
    jcall("POST", "/v1/friends/decline", tb, {"user": c["id"]})
    status, doc = jcall("GET", "/v1/friends", tc)
    gate("decline clears the sender's outgoing", doc["outgoing"] == [], doc)
    status, doc = jcall("POST", "/v1/friends/request", ta, {"nick": a["nick"]})
    gate("asking yourself is refused", status == 400 and doc.get("error") == "self", doc)
    status, doc = jcall("POST", "/v1/friends/request", ta, {"nick": "zzt_nobody_here"})
    gate("an unknown nick is refused", status == 404 and doc.get("error") == "no_user", doc)
```

Run: `... verify_chat_server.py friends` → Expected: FAIL (404).

- [ ] **Step 2: Implement**

Add to `Studio`:

```js
  // ---------------------------------------------------------------- routes: friends
  areFriends(a, b) {
    const [x, y] = a < b ? [a, b] : [b, a];
    return this.sql.exec("SELECT 1 FROM friends WHERE a = ? AND b = ?", x, y).toArray().length > 0;
  }

  relation(me, other) {
    if (this.areFriends(me, other)) return "friend";
    if (this.sql.exec("SELECT 1 FROM requests WHERE from_id = ? AND to_id = ?", other, me).toArray().length) return "incoming";
    if (this.sql.exec("SELECT 1 FROM requests WHERE from_id = ? AND to_id = ?", me, other).toArray().length) return "outgoing";
    return null;
  }

  withPresence(row) { return { ...this.user(row), ...this.presence(row.id) }; }

  searchUsers({ url, me }) {
    const q = String(url.searchParams.get("q") || "").trim().toLowerCase().replace(/^@/, "");
    if (q.length < 1) return json({ users: [] });
    const like = q.replace(/[\\%_]/g, (c) => "\\" + c) + "%";
    const rows = this.sql.exec("SELECT * FROM users WHERE nick LIKE ? ESCAPE '\\' AND id != ? ORDER BY nick LIMIT 20", like, me.id).toArray();
    return json({ users: rows.map((r) => ({ ...this.user(r), relation: this.relation(me.id, r.id) })) });
  }

  friends({ me }) {
    const pick = (sql, ...args) => this.sql.exec(sql, ...args).toArray().map((r) => this.withPresence(r));
    return json({
      friends: this.friendIds(me.id).map((id) => this.withPresence(this.userById(id))),
      incoming: pick("SELECT u.* FROM requests r JOIN users u ON u.id = r.from_id WHERE r.to_id = ? ORDER BY r.at", me.id),
      outgoing: pick("SELECT u.* FROM requests r JOIN users u ON u.id = r.to_id WHERE r.from_id = ? ORDER BY r.at", me.id),
    });
  }

  befriend(a, b) {
    const [x, y] = a < b ? [a, b] : [b, a];
    this.sql.exec("DELETE FROM requests WHERE (from_id = ? AND to_id = ?) OR (from_id = ? AND to_id = ?)", a, b, b, a);
    this.sql.exec("INSERT OR IGNORE INTO friends (a, b, since) VALUES (?, ?, ?)", x, y, Date.now());
    this.emit({ uid: a, kind: "friend_added", payload: { user: this.withPresence(this.userById(b)) } });
    this.emit({ uid: b, kind: "friend_added", payload: { user: this.withPresence(this.userById(a)) } });
  }

  async requestFriend({ request, me }) {
    const b = await this.body(request);
    const nick = String(b.nick ?? "").trim().toLowerCase().replace(/^@/, "");
    const other = this.sql.exec("SELECT * FROM users WHERE nick = ?", nick).toArray()[0];
    if (!other) refuse("no_user", "Nobody is called @" + nick, 404);
    if (other.id === me.id) refuse("self", "That is you");
    const rel = this.relation(me.id, other.id);
    if (rel === "friend") return json({ state: "friends" });
    if (rel === "incoming") { this.befriend(me.id, other.id); return json({ state: "friends" }); }
    if (rel !== "outgoing") {
      this.sql.exec("INSERT INTO requests (from_id, to_id, at) VALUES (?, ?, ?)", me.id, other.id, Date.now());
      this.emit({ uid: other.id, kind: "friend_request", payload: { user: this.withPresence(me) } });
      this.emit({ uid: me.id, kind: "request_sent", payload: { user: this.withPresence(other) } });
    }
    return json({ state: "requested" });
  }

  async answerRequest({ request, me, params }) {
    const b = await this.body(request);
    const other = this.userById(String(b.user ?? ""));
    const action = params[0];
    const [from, to] = action === "cancel" ? [me.id, other.id] : [other.id, me.id];
    if (!this.sql.exec("SELECT 1 FROM requests WHERE from_id = ? AND to_id = ?", from, to).toArray().length) {
      refuse("no_request", "There is no such request", 404);
    }
    if (action === "accept") { this.befriend(me.id, other.id); return json({ ok: true }); }
    this.sql.exec("DELETE FROM requests WHERE from_id = ? AND to_id = ?", from, to);
    for (const uid of [from, to]) this.emit({ uid, kind: "request_cancelled", payload: { from_id: from, to_id: to } });
    return json({ ok: true });
  }

  unfriend({ me, params }) {
    const other = this.userById(params[0]);
    const [x, y] = me.id < other.id ? [me.id, other.id] : [other.id, me.id];
    this.sql.exec("DELETE FROM friends WHERE a = ? AND b = ?", x, y);
    this.emit({ uid: me.id, kind: "friend_removed", payload: { user_id: other.id } });
    this.emit({ uid: other.id, kind: "friend_removed", payload: { user_id: me.id } });
    return json({ ok: true });
  }
```

Add to `ROUTES`:

```js
  ["GET", /^\/v1\/users$/, "searchUsers"],
  ["GET", /^\/v1\/friends$/, "friends"],
  ["POST", /^\/v1\/friends\/request$/, "requestFriend"],
  ["POST", /^\/v1\/friends\/(accept|decline|cancel)$/, "answerRequest"],
  ["DELETE", /^\/v1\/friends\/([0-9a-f]{16})$/, "unfriend"],
```

- [ ] **Step 3: Deploy and verify**

Run: `... deploy.py staging`, then `... verify_chat_server.py signin profile friends`
Expected: `0 of 26 gates failed`.

- [ ] **Step 4: Commit**

```bash
git add server/chat/worker.js docs/superpowers/plans/verify_chat_server.py
git commit -m "feat(chat): friends - search, request, accept, decline, cancel, remove"
```

---

### Task 5: Chats and groups

**Files:**
- Modify: `server/chat/worker.js`
- Modify: `docs/superpowers/plans/verify_chat_server.py`

**Interfaces:**
- Consumes: `areFriends`, `withPresence`, `picture`, `servePicture`, `emit`.
- Produces: `GET /v1/chats` → `{seq, chats: [view]}` where `seq` is the newest event seq and `view` is
  `{id, kind, name, admin, avatar_v, members: [user + presence + joined], last: message|null, unread, read_upto}`;
  `POST /v1/chats {kind: "dm", with}` / `{kind: "group", name, members}` → `view`;
  `PATCH /v1/chats/<id> {name}`, `PUT /v1/chats/<id>/avatar`, `GET /v1/avatar/c/<id>`,
  `POST /v1/chats/<id>/members {user}`, `DELETE /v1/chats/<id>/members/<uid>`,
  `GET /v1/chats/<id>/messages?before=&limit=` → `{messages: [message]}`;
  `message` is `{id, chat, seq, from_id, cid, text, reply_to, at, edited_at, deleted}`;
  `this.chatRow(id)`, `this.member(chat, uid)`, `this.shared(chat)`, `this.messageView(row)`;
  events `chat {chat: shared}`, `member_added {chat_id, user}`, `member_removed {chat_id, user_id, admin}`.

- [ ] **Step 1: Add the failing phase** (and `"chats": phase_chats` to `PHASES`)

```python
def friends_of(*pairs):
    for (ta, a), (tb, b) in pairs:
        jcall("POST", "/v1/friends/request", ta, {"nick": b["nick"]})
        jcall("POST", "/v1/friends/accept", tb, {"user": a["id"]})


def phase_chats():
    A, B, C, D = (Users.make(x) for x in ("ca", "cb", "cc", "cd"))
    friends_of((A, B), (A, C))
    status, doc = jcall("POST", "/v1/chats", A[0], {"kind": "dm", "with": D[1]["id"]})
    gate("a dm with a stranger is refused", status == 403 and doc.get("error") == "not_friend", doc)
    status, dm = jcall("POST", "/v1/chats", A[0], {"kind": "dm", "with": B[1]["id"]})
    gate("a dm with a friend", status == 200 and dm["kind"] == "dm" and len(dm["members"]) == 2, dm)
    status, again = jcall("POST", "/v1/chats", B[0], {"kind": "dm", "with": A[1]["id"]})
    gate("the same dm from the other side, never a second", again.get("id") == dm["id"], again)
    status, doc = jcall("POST", "/v1/chats", A[0], {"kind": "group", "name": "G", "members": [D[1]["id"]]})
    gate("a group with a stranger is refused", status == 403 and doc.get("error") == "not_friend", doc)
    status, g = jcall("POST", "/v1/chats", A[0], {"kind": "group", "name": " Crypt anim ", "members": [B[1]["id"]]})
    gate("a group, its creator the admin", status == 200 and g["admin"] == A[1]["id"] and g["name"] == "Crypt anim", g)
    status, doc = jcall("PATCH", "/v1/chats/" + g["id"], B[0], {"name": "Mine"})
    gate("a member who is not admin cannot rename", status == 403 and doc.get("error") == "not_admin", doc)
    status, doc = jcall("PATCH", "/v1/chats/" + g["id"], A[0], {"name": "Crypt"})
    gate("the admin renames", status == 200 and doc["name"] == "Crypt", doc)
    status, doc = jcall("POST", "/v1/chats/%s/members" % g["id"], A[0], {"user": C[1]["id"]})
    gate("the admin adds a friend", status == 200 and len(doc["members"]) == 3, doc)
    status, doc = jcall("POST", "/v1/chats/%s/members" % g["id"], B[0], {"user": A[1]["id"]})
    gate("a non-admin cannot add", status == 403, doc)
    status, doc = jcall("DELETE", "/v1/chats/%s/members/%s" % (g["id"], C[1]["id"]), A[0])
    status, chats = jcall("GET", "/v1/chats", C[0])
    gate("a removed member no longer has the group", g["id"] not in [c["id"] for c in chats["chats"]], chats)
    status, doc = jcall("DELETE", "/v1/chats/%s/members/%s" % (g["id"], A[1]["id"]), A[0])
    status, chats = jcall("GET", "/v1/chats", B[0])
    group = [c for c in chats["chats"] if c["id"] == g["id"]]
    gate("an admin who leaves hands the group on", group and group[0]["admin"] == B[1]["id"], group)
    gate("GET /v1/chats carries the newest event seq", isinstance(chats.get("seq"), int) and chats["seq"] > 0, chats.get("seq"))
    status, doc = jcall("GET", "/v1/chats/%s/messages" % g["id"], A[0])
    gate("someone who left cannot read the history", status == 403 and doc.get("error") == "not_member", doc)
    status, doc = jcall("PUT", "/v1/chats/%s/avatar" % g["id"], B[0], raw=PNG, ctype="image/png")
    status, data, ctype = call("GET", "/v1/avatar/c/" + g["id"], B[0])
    gate("a group avatar", status == 200 and data == PNG, ctype)
```

Run: `... verify_chat_server.py chats` → Expected: FAIL (404).

- [ ] **Step 2: Implement**

Add to `Studio`:

```js
  // ---------------------------------------------------------------- routes: chats
  chatRow(id) {
    const row = this.sql.exec("SELECT * FROM chats WHERE id = ?", id).toArray()[0];
    if (!row) refuse("no_chat", "No such chat", 404);
    return row;
  }

  member(chat, uid) {
    const row = this.sql.exec("SELECT * FROM members WHERE chat = ? AND uid = ?", chat, uid).toArray()[0];
    if (!row) refuse("not_member", "You are not in this chat", 403);
    return row;
  }

  messageView(r) {
    return { id: r.id, chat: r.chat, seq: r.seq, from_id: r.from_id, cid: r.cid,
             text: r.deleted ? "" : r.text, reply_to: r.reply_to, at: r.at, edited_at: r.edited_at, deleted: !!r.deleted };
  }

  shared(chat) {
    const row = this.chatRow(chat);
    const members = this.sql.exec(
      "SELECT u.*, m.joined FROM members m JOIN users u ON u.id = m.uid WHERE m.chat = ? ORDER BY m.joined, u.nick", chat)
      .toArray().map((r) => ({ ...this.withPresence(r), joined: r.joined }));
    return { id: row.id, kind: row.kind, name: row.name, admin: row.admin, avatar_v: row.avatar_v, members };
  }

  view(chat, uid) {
    const mine = this.member(chat, uid);
    const last = this.sql.exec("SELECT * FROM messages WHERE chat = ? ORDER BY seq DESC LIMIT 1", chat).toArray()[0];
    const unread = this.sql.exec(
      "SELECT COUNT(*) AS n FROM messages WHERE chat = ? AND seq > ? AND from_id != ? AND deleted = 0",
      chat, mine.read_upto, uid).one().n;
    return { ...this.shared(chat), last: last ? this.messageView(last) : null, unread, read_upto: mine.read_upto };
  }

  chats({ me }) {
    const ids = this.sql.exec("SELECT chat FROM members WHERE uid = ?", me.id).toArray().map((r) => r.chat);
    const seq = this.sql.exec("SELECT COALESCE(MAX(seq), 0) AS s FROM events").one().s;
    return json({ seq, chats: ids.map((id) => this.view(id, me.id)) });
  }

  addMember(chat, uid) {
    this.sql.exec("INSERT OR IGNORE INTO members (chat, uid, joined) VALUES (?, ?, ?)", chat, uid, Date.now());
  }

  async createChat({ request, me }) {
    const b = await this.body(request);
    if (b.kind === "dm") {
      const other = this.userById(String(b.with ?? ""));
      if (other.id === me.id) refuse("self", "That is you");
      if (!this.areFriends(me.id, other.id)) refuse("not_friend", "Add them as a friend first", 403);
      const id = "dm_" + [me.id, other.id].sort().join("_");
      if (!this.sql.exec("SELECT 1 FROM chats WHERE id = ?", id).toArray().length) {
        this.sql.exec("INSERT INTO chats (id, kind, created) VALUES (?, 'dm', ?)", id, Date.now());
        this.addMember(id, me.id);
        this.addMember(id, other.id);
        this.emit({ chat: id, kind: "chat", payload: { chat: this.shared(id) } });
      }
      return json(this.view(id, me.id));
    }
    if (b.kind !== "group") refuse("bad_request", "A chat is a dm or a group");
    const name = clean(b.name, GROUP_NAME_MAX);
    if (!name) refuse("bad_name", "Name the group");
    const others = [...new Set((b.members || []).map(String))].filter((id) => id !== me.id);
    if (others.length + 1 > GROUP_MAX) refuse("too_big", "A group holds at most " + GROUP_MAX + " people", 413);
    for (const id of others) {
      this.userById(id);
      if (!this.areFriends(me.id, id)) refuse("not_friend", "Only friends can be added", 403);
    }
    const id = "g_" + randomHex(8);
    this.sql.exec("INSERT INTO chats (id, kind, name, admin, created) VALUES (?, 'group', ?, ?, ?)", id, name, me.id, Date.now());
    this.addMember(id, me.id);
    for (const uid of others) this.addMember(id, uid);
    this.emit({ chat: id, kind: "chat", payload: { chat: this.shared(id) } });
    return json(this.view(id, me.id));
  }

  adminOf(chatId, me) {
    const row = this.chatRow(chatId);
    this.member(chatId, me.id);
    if (row.kind !== "group") refuse("not_group", "Only a group has an admin");
    if (row.admin !== me.id) refuse("not_admin", "Only the group's admin can do that", 403);
    return row;
  }

  async patchChat({ request, me, params }) {
    this.adminOf(params[0], me);
    const name = clean((await this.body(request)).name, GROUP_NAME_MAX);
    if (!name) refuse("bad_name", "Name the group");
    this.sql.exec("UPDATE chats SET name = ? WHERE id = ?", name, params[0]);
    this.emit({ chat: params[0], kind: "chat", payload: { chat: this.shared(params[0]) } });
    return json(this.view(params[0], me.id));
  }

  async putChatAvatar({ request, me, params }) {
    this.adminOf(params[0], me);
    const { bytes, type } = await this.picture(request);
    this.sql.exec("UPDATE chats SET avatar = ?, avatar_type = ?, avatar_v = avatar_v + 1 WHERE id = ?", bytes, type, params[0]);
    this.emit({ chat: params[0], kind: "chat", payload: { chat: this.shared(params[0]) } });
    return json(this.view(params[0], me.id));
  }

  chatAvatar({ me, params }) {
    this.member(params[0], me.id);
    const row = this.chatRow(params[0]);
    return this.servePicture(row.avatar, row.avatar_type);
  }

  async postMember({ request, me, params }) {
    const chat = params[0];
    this.adminOf(chat, me);
    const user = this.userById(String((await this.body(request)).user ?? ""));
    if (!this.areFriends(me.id, user.id)) refuse("not_friend", "Only friends can be added", 403);
    if (this.memberIds(chat).length >= GROUP_MAX) refuse("too_big", "A group holds at most " + GROUP_MAX + " people", 413);
    this.addMember(chat, user.id);
    this.emit({ chat, kind: "member_added", payload: { chat_id: chat, user: this.withPresence(user) } });
    this.emit({ chat, kind: "chat", payload: { chat: this.shared(chat) } });
    return json(this.view(chat, me.id));
  }

  leave(chat, uid) {
    const row = this.chatRow(chat);
    let admin = row.admin;
    if (admin === uid) {
      const next = this.sql.exec("SELECT uid FROM members WHERE chat = ? AND uid != ? ORDER BY joined LIMIT 1", chat, uid).toArray()[0];
      admin = next ? next.uid : null;
      this.sql.exec("UPDATE chats SET admin = ? WHERE id = ?", admin, chat);
    }
    this.emit({ chat, kind: "member_removed", payload: { chat_id: chat, user_id: uid, admin } });
    this.sql.exec("DELETE FROM members WHERE chat = ? AND uid = ?", chat, uid);
    if (!this.memberIds(chat).length) {
      this.sql.exec("DELETE FROM messages WHERE chat = ?", chat);
      this.sql.exec("DELETE FROM chats WHERE id = ?", chat);
    }
  }

  deleteMember({ me, params }) {
    const [chat, uid] = params;
    const row = this.chatRow(chat);
    this.member(chat, me.id);
    if (row.kind !== "group") refuse("not_group", "A dm cannot be left");
    if (uid !== me.id && row.admin !== me.id) refuse("not_admin", "Only the group's admin can do that", 403);
    this.member(chat, uid);
    this.leave(chat, uid);
    return json({ ok: true });
  }

  history({ url, me, params }) {
    this.member(params[0], me.id);
    const before = Number(url.searchParams.get("before")) || Number.MAX_SAFE_INTEGER;
    const limit = Math.max(1, Math.min(100, Number(url.searchParams.get("limit")) || 50));
    const rows = this.sql.exec("SELECT * FROM messages WHERE chat = ? AND seq < ? ORDER BY seq DESC LIMIT ?",
      params[0], before, limit).toArray();
    return json({ messages: rows.reverse().map((r) => this.messageView(r)) });
  }
```

Replace `forget` (from Task 2) so a deleted account also leaves its chats:

```js
  forget(uid) {
    for (const ws of this.ctx.getWebSockets(uid)) { try { ws.close(1000, "account deleted"); } catch { /* gone */ } }
    for (const r of this.sql.exec("SELECT chat FROM members WHERE uid = ?", uid).toArray()) this.leave(r.chat, uid);
    this.sql.exec("DELETE FROM friends WHERE a = ? OR b = ?", uid, uid);
    this.sql.exec("DELETE FROM requests WHERE from_id = ? OR to_id = ?", uid, uid);
    this.sql.exec("DELETE FROM users WHERE id = ?", uid);
  }
```

Add to `ROUTES`:

```js
  ["GET", /^\/v1\/chats$/, "chats"],
  ["POST", /^\/v1\/chats$/, "createChat"],
  ["PATCH", /^\/v1\/chats\/([\w]+)$/, "patchChat"],
  ["PUT", /^\/v1\/chats\/([\w]+)\/avatar$/, "putChatAvatar"],
  ["GET", /^\/v1\/avatar\/c\/([\w]+)$/, "chatAvatar"],
  ["POST", /^\/v1\/chats\/([\w]+)\/members$/, "postMember"],
  ["DELETE", /^\/v1\/chats\/([\w]+)\/members\/([0-9a-f]{16})$/, "deleteMember"],
  ["GET", /^\/v1\/chats\/([\w]+)\/messages$/, "history"],
```

- [ ] **Step 3: Deploy and verify**

Run: `... deploy.py staging`, then `... verify_chat_server.py signin profile friends chats`
Expected: `0 of 40 gates failed`.

- [ ] **Step 4: Commit**

```bash
git add server/chat/worker.js docs/superpowers/plans/verify_chat_server.py
git commit -m "feat(chat): chats and groups - dm, group, admin, members, history"
```

---

### Task 6: The live connection: messages, catch-up, read, typing, presence

**Files:**
- Modify: `server/chat/worker.js`
- Modify: `docs/superpowers/plans/verify_chat_server.py`

**Interfaces:**
- Consumes: Tasks 2–5.
- Produces: `GET /v1/ws` (upgrade, token in `Authorization`); the text frame `ping` answered `pong`
  without waking the object; client messages `hello {since}`, `send {chat, cid, text, reply_to?}`,
  `edit {chat, id, text}`, `delete {chat, id}`, `read {chat, upto}`, `typing {chat}`; server messages
  `ack {cid, id, seq}`, `error {cid?, code, text}`, `resync`, `caught_up {seq}`, and events
  `message {message}`, `edited {chat_id, id, text, edited_at}`, `deleted {chat_id, id}`,
  `read {chat_id, user_id, upto}`, `typing {chat_id, user_id}` (no seq), `presence {user_id, online, last_seen}` (no seq).

- [ ] **Step 1: Add the failing phase** (and `"live": phase_live` to `PHASES`)

```python
def phase_live():
    A, B, S = Users.make("la"), Users.make("lb"), Users.make("ls")
    friends_of((A, B))
    status, dm = jcall("POST", "/v1/chats", A[0], {"kind": "dm", "with": B[1]["id"]})
    seq0 = jcall("GET", "/v1/chats", B[0])[1]["seq"]
    wa, wb = ws(A[0]), ws(B[0])
    wb.send({"type": "hello", "since": seq0})
    done, _ = wb.until(lambda e: e["kind"] == "caught_up")
    gate("hello answers caught_up", done is not None and done["seq"] >= seq0, done)
    wa.send_text("ping")
    gate("ping answers pong", wa.recv_text(5) == "pong")
    t0 = time.time()
    wa.send({"type": "send", "chat": dm["id"], "cid": "c1", "text": "hello  "})
    ack, _ = wa.until(lambda e: e["kind"] == "ack")
    got, _ = wb.until(lambda e: e["kind"] == "message")
    gate("the other gets the message within 1 s", got is not None and time.time() - t0 < 1.0, round(time.time() - t0, 3))
    gate("the text is trimmed, the ack names it", got and got["message"]["text"] == "hello" and ack["id"] == got["message"]["id"], (ack, got))
    wa.send({"type": "send", "chat": dm["id"], "cid": "c1", "text": "hello"})
    again, _ = wa.until(lambda e: e["kind"] == "ack")
    msgs = jcall("GET", "/v1/chats/%s/messages" % dm["id"], A[0])[1]["messages"]
    gate("the same cid twice is one message", again["id"] == ack["id"] and len(msgs) == 1, len(msgs))
    wa.send({"type": "send", "chat": dm["id"], "cid": "c2", "text": "re", "reply_to": ack["id"]})
    reply, _ = wb.until(lambda e: e["kind"] == "message")
    gate("a reply carries its original", reply and reply["message"]["reply_to"] == ack["id"], reply)
    wa.send({"type": "edit", "chat": dm["id"], "id": ack["id"], "text": "hello there"})
    ed, _ = wb.until(lambda e: e["kind"] == "edited")
    gate("an edit reaches the other", ed and ed["text"] == "hello there" and ed["edited_at"], ed)
    wb.send({"type": "edit", "chat": dm["id"], "id": ack["id"], "text": "mine now"})
    err, _ = wb.until(lambda e: e["kind"] == "error")
    gate("editing someone else's message is refused", err and err["code"] == "not_yours", err)
    wb.send({"type": "read", "chat": dm["id"], "upto": reply["message"]["seq"]})
    rd, _ = wa.until(lambda e: e["kind"] == "read")
    gate("a read mark reaches the sender", rd and rd["user_id"] == B[1]["id"] and rd["upto"] == reply["message"]["seq"], rd)
    wa.send({"type": "typing", "chat": dm["id"]})
    ty, _ = wb.until(lambda e: e["kind"] == "typing")
    gate("typing reaches the other, with no seq", ty and "seq" not in ty, ty)
    wa.send({"type": "delete", "chat": dm["id"], "id": reply["message"]["id"]})
    de, _ = wb.until(lambda e: e["kind"] == "deleted")
    msgs = jcall("GET", "/v1/chats/%s/messages" % dm["id"], B[0])[1]["messages"]
    gate("a delete leaves an empty, deleted message", de and msgs[-1]["deleted"] and msgs[-1]["text"] == "", msgs[-1])
    last_seen = got["seq"]
    wb.close()
    wa.send({"type": "send", "chat": dm["id"], "cid": "c3", "text": "while you were away"})
    wa.until(lambda e: e["kind"] == "ack")
    wb = ws(B[0])
    wb.send({"type": "hello", "since": last_seen})
    done, seen = wb.until(lambda e: e["kind"] == "caught_up")
    texts = [e["message"]["text"] for e in seen if e["kind"] == "message"]
    gate("hello since a seq brings what was missed", "while you were away" in texts and "re" in texts, texts)
    wb.send({"type": "hello", "since": 0})
    rs, _ = wb.until(lambda e: e["kind"] == "resync")
    gate("hello since 0 asks for a resync", rs is not None, rs)
    ws_s = ws(S[0])
    ws_s.send({"type": "send", "chat": dm["id"], "cid": "x", "text": "let me in"})
    err, _ = ws_s.until(lambda e: e["kind"] == "error")
    gate("a stranger cannot write into the chat", err and err["code"] == "not_member", err)
    wa.send({"type": "send", "chat": dm["id"], "cid": "big", "text": "y" * 4001})
    err, _ = wa.until(lambda e: e["kind"] == "error")
    gate("a text over 4000 characters is refused", err and err["code"] == "too_long", err)
    for i in range(25):
        wa.send({"type": "send", "chat": dm["id"], "cid": "flood%d" % i, "text": "x"})
    flood = wa.events(3)
    gate("more than 20 messages in 10 s are refused", any(e["kind"] == "error" and e["code"] == "too_many" for e in flood))
    jcall("DELETE", "/v1/friends/" + B[1]["id"], A[0])
    time.sleep(11)
    wa.events(0.5)
    wa.send({"type": "send", "chat": dm["id"], "cid": "c9", "text": "still?"})
    err, _ = wa.until(lambda e: e["kind"] == "error")
    gate("a dm stops when they are no longer friends", err and err["code"] == "not_friend", err)
    for w in (wa, wb, ws_s):
        w.close()
```

Run: `... verify_chat_server.py live` → Expected: FAIL (`handshake answered 404`).

- [ ] **Step 2: Implement**

Add to `Studio`:

```js
  // ---------------------------------------------------------------- the live connection
  connect({ request, me }) {
    if ((request.headers.get("upgrade") || "").toLowerCase() !== "websocket") refuse("bad_request", "This address is a WebSocket");
    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair);
    const wasOnline = this.ctx.getWebSockets(me.id).length > 0;
    this.ctx.acceptWebSocket(server, [me.id]);
    server.serializeAttachment({ uid: me.id });
    if (!wasOnline) this.announce(me.id, true);
    return new Response(null, { status: 101, webSocket: client });
  }

  announce(uid, online) {
    const row = this.userById(uid);
    this.deliver({ kind: "presence", user_id: uid, online, last_seen: row.last_seen }, this.friendIds(uid));
  }

  async webSocketMessage(ws, raw) {
    const { uid } = ws.deserializeAttachment() || {};
    let msg = {};
    try {
      msg = JSON.parse(typeof raw === "string" ? raw : new TextDecoder().decode(raw));
      const me = this.userById(uid);
      const handler = { hello: this.onHello, send: this.onSend, edit: this.onEdit, delete: this.onDelete,
                        read: this.onRead, typing: this.onTyping }[msg.type];
      if (!handler) refuse("bad_request", "Unknown message " + msg.type);
      handler.call(this, ws, me, msg);
    } catch (e) {
      const code = e instanceof Refusal ? e.code : "server";
      const text = e instanceof Refusal ? e.message : "The server failed: " + e.message;
      try { ws.send(JSON.stringify({ kind: "error", cid: msg.cid ?? null, code, text })); } catch { /* gone */ }
    }
  }

  webSocketClose(ws) {
    const { uid } = ws.deserializeAttachment() || {};
    try { ws.close(1000, "bye"); } catch { /* already closed */ }
    if (!uid) return;
    const others = this.ctx.getWebSockets(uid).filter((s) => s !== ws && s.readyState === WebSocket.OPEN);
    if (!others.length && this.sql.exec("SELECT 1 FROM users WHERE id = ?", uid).toArray().length) {
      this.sql.exec("UPDATE users SET last_seen = ? WHERE id = ?", Date.now(), uid);
      this.announce(uid, false);
    }
  }

  webSocketError(ws) { this.webSocketClose(ws); }

  onHello(ws, me, msg) {
    const since = Number(msg.since) || 0;
    const oldest = this.sql.exec("SELECT MIN(seq) AS s FROM events").one().s;
    const newest = this.sql.exec("SELECT COALESCE(MAX(seq), 0) AS s FROM events").one().s;
    if (since <= 0 || (oldest != null && since < oldest - 1)) {
      ws.send(JSON.stringify({ kind: "resync" }));
    } else {
      let after = since;
      for (;;) {
        const rows = this.sql.exec(
          `SELECT * FROM events WHERE seq > ? AND (uid = ? OR (uid IS NULL AND chat IS NULL)
             OR chat IN (SELECT chat FROM members WHERE uid = ?)) ORDER BY seq LIMIT 500`, after, me.id, me.id).toArray();
        for (const r of rows) ws.send(JSON.stringify({ seq: r.seq, kind: r.kind, ...JSON.parse(r.payload) }));
        if (rows.length < 500) break;
        after = rows[rows.length - 1].seq;
      }
    }
    ws.send(JSON.stringify({ kind: "caught_up", seq: newest }));
  }

  writable(chat, me) {
    const row = this.chatRow(chat);
    this.member(chat, me.id);
    if (row.kind === "dm") {
      const other = this.memberIds(chat).find((id) => id !== me.id);
      if (!other || !this.areFriends(me.id, other)) refuse("not_friend", "You are no longer friends", 403);
    }
    return row;
  }

  text(raw) {
    const text = String(raw ?? "").replace(/^\s+|\s+$/gu, "");
    if (!text) refuse("empty", "An empty message");
    if (text.length > TEXT_MAX) refuse("too_long", "A message is at most " + TEXT_MAX + " characters");
    return text;
  }

  onSend(ws, me, msg) {
    const cid = String(msg.cid ?? "");
    if (!cid || cid.length > 64) refuse("bad_request", "A message needs its cid");
    const chat = String(msg.chat ?? "");
    const known = this.sql.exec("SELECT * FROM messages WHERE from_id = ? AND cid = ?", me.id, cid).toArray()[0];
    if (known) { ws.send(JSON.stringify({ kind: "ack", cid, id: known.id, seq: known.seq })); return; }
    this.limit(me.id + ":msg", 20);
    this.writable(chat, me);
    const text = this.text(msg.text);
    let reply = msg.reply_to ? String(msg.reply_to) : null;
    if (reply && !this.sql.exec("SELECT 1 FROM messages WHERE chat = ? AND id = ?", chat, reply).toArray().length) reply = null;
    const message = this.ctx.storage.transactionSync(() => {
      const seq = this.sql.exec("UPDATE chats SET last_seq = last_seq + 1 WHERE id = ? RETURNING last_seq", chat).one().last_seq;
      const id = randomHex(8);
      const at = Date.now();
      this.sql.exec("INSERT INTO messages (chat, seq, id, from_id, cid, text, reply_to, at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        chat, seq, id, me.id, cid, text, reply, at);
      this.sql.exec("UPDATE members SET read_upto = ? WHERE chat = ? AND uid = ?", seq, chat, me.id);
      return this.messageView(this.sql.exec("SELECT * FROM messages WHERE id = ?", id).one());
    });
    this.emit({ chat, kind: "message", payload: { message } });
    ws.send(JSON.stringify({ kind: "ack", cid, id: message.id, seq: message.seq }));
  }

  own(chat, id, me) {
    this.member(chat, me.id);
    const row = this.sql.exec("SELECT * FROM messages WHERE chat = ? AND id = ?", chat, String(id ?? "")).toArray()[0];
    if (!row || row.deleted) refuse("no_message", "No such message", 404);
    if (row.from_id !== me.id) refuse("not_yours", "Only your own messages", 403);
    return row;
  }

  onEdit(ws, me, msg) {
    const chat = String(msg.chat ?? "");
    const row = this.own(chat, msg.id, me);
    const text = this.text(msg.text);
    const at = Date.now();
    this.sql.exec("UPDATE messages SET text = ?, edited_at = ? WHERE id = ?", text, at, row.id);
    this.emit({ chat, kind: "edited", payload: { chat_id: chat, id: row.id, text, edited_at: at } });
  }

  onDelete(ws, me, msg) {
    const chat = String(msg.chat ?? "");
    const row = this.own(chat, msg.id, me);
    this.sql.exec("UPDATE messages SET deleted = 1, text = '' WHERE id = ?", row.id);
    this.emit({ chat, kind: "deleted", payload: { chat_id: chat, id: row.id } });
  }

  onRead(ws, me, msg) {
    const chat = String(msg.chat ?? "");
    const mine = this.member(chat, me.id);
    const last = this.chatRow(chat).last_seq;
    const upto = Math.min(Number(msg.upto) || 0, last);
    if (upto <= mine.read_upto) return;
    this.sql.exec("UPDATE members SET read_upto = ? WHERE chat = ? AND uid = ?", upto, chat, me.id);
    this.emit({ chat, kind: "read", payload: { chat_id: chat, user_id: me.id, upto } });
  }

  onTyping(ws, me, msg) {
    const chat = String(msg.chat ?? "");
    this.member(chat, me.id);
    this.deliver({ kind: "typing", chat_id: chat, user_id: me.id }, this.memberIds(chat).filter((u) => u !== me.id));
  }
```

Add to `ROUTES`:

```js
  ["GET", /^\/v1\/ws$/, "connect"],
```

- [ ] **Step 3: Deploy and verify**

Run: `... deploy.py staging`, then `... verify_chat_server.py live`
Expected: `0 of 17 gates failed`. The flood gate needs the per-user rate limit to survive between
messages; the object stays awake while a socket sends, so `this.hits` holds. If a gate reads 1–2 s for
delivery, run the phase once more before blaming code: a first request after a deploy starts the object.

- [ ] **Step 4: Commit**

```bash
git add server/chat/worker.js docs/superpowers/plans/verify_chat_server.py
git commit -m "feat(chat): the live connection - send, ack by cid, edit, delete, read, typing, catch-up"
```

---

### Task 7: Everything together, and the record

**Files:**
- Modify: `docs/superpowers/plans/verify_chat_server.py` (one phase: events of everyone, presence)
- Modify: `CLAUDE.md` (a short section)

**Interfaces:**
- Consumes: everything above.
- Produces: `verify_chat_server.py all` green; a CLAUDE.md section the client plans build on.

- [ ] **Step 1: Add the failing phase** (and `"presence": phase_presence` to `PHASES`)

```python
def phase_presence():
    A, B = Users.make("pa"), Users.make("pb")
    friends_of((A, B))
    wa = ws(A[0])
    wa.send({"type": "hello", "since": jcall("GET", "/v1/chats", A[0])[1]["seq"]})
    wa.until(lambda e: e["kind"] == "caught_up")
    wb = ws(B[0])
    on, _ = wa.until(lambda e: e["kind"] == "presence" and e["user_id"] == B[1]["id"])
    gate("a friend coming online is announced", on and on["online"] is True, on)
    jcall("PATCH", "/v1/me", B[0], {"name": "Renamed"})
    ev, _ = wa.until(lambda e: e["kind"] == "user" and e["user"]["id"] == B[1]["id"])
    gate("a name change reaches everybody", ev and ev["user"]["name"] == "Renamed", ev)
    wb.close()
    off, _ = wa.until(lambda e: e["kind"] == "presence" and e["user_id"] == B[1]["id"] and not e["online"], 10)
    gate("going offline is announced with last_seen", off and off["last_seen"] > 0, off)
    friends = jcall("GET", "/v1/friends", A[0])[1]["friends"]
    gate("the friends list says offline and when", friends and friends[0]["online"] is False and friends[0]["last_seen"] > 0, friends)
    wa.close()
```

Run: `... verify_chat_server.py presence` → Expected: PASS already if Tasks 3 and 6 are right; if any gate
fails, fix `announce` / `webSocketClose` / `patchMe` in `worker.js`, redeploy, run again.

- [ ] **Step 2: The whole verify, twice**

Run: `... verify_chat_server.py all` twice in a row.
Expected both times: `0 of 61 gates failed` (8 + 6 + 12 + 14 + 17 + 4), and the second run proves the
first left nothing that collides (its users were deleted).

- [ ] **Step 3: The record in CLAUDE.md**

Append this section at the end of `CLAUDE.md`:

```markdown
## Chat server: one Worker, one SQLite Durable Object (2026-10-19)

The messenger's server (spec `docs/superpowers/specs/2026-10-19-chat-messenger-design.md`, plan
`docs/superpowers/plans/2026-10-19-chat-server.md`; the client and the window are plans 2 and 3).
`server/chat/worker.js` forwards `/v1/*` to one `Studio` Durable Object (SQLite: users, friends,
requests, chats, members, messages, events) that also holds every WebSocket (Hibernation API; the
text frame `ping` is answered `pong` without waking it). `server/chat/deploy.py check|staging|production`
uploads it through Cloudflare's HTTP API (no Node here); credentials only from
`CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ACCOUNT_ID`. `server/` never ships.
Proof: `verify_chat_server.py all` against `skeldar-chat-staging` - <N> of 61 gates, <date>.
<What the first real deploy measured: the migration retry, the workers.dev delay, delivery times.>
```

Fill the three bracketed values with what the runs printed; leave nothing bracketed.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/verify_chat_server.py CLAUDE.md
git commit -m "test(chat): the server's whole verify green on staging; recorded"
```

---

## Self-review against the spec

- Sign-in by nick, token sha256, login code = token, reserved nicks: Task 2. Profile, avatars ≤ 256 KB in
  SQLite (no R2): Task 3. Friends by request, accept / decline / cancel / remove, search: Task 4. Chats,
  dm only with friends, groups, admin, add / remove / leave / handover, avatars, history 50 at a time:
  Task 5. WebSocket, `hello {since}`, `resync`, `caught_up`, `cid` never doubled, edit / delete own,
  read marks, typing without seq, presence, rate limits, text ≤ 4000: Task 6. Events kept 30 days
  (`alarm`): Task 2. Two Workers: Task 1 names both; this plan deploys staging only (production is plan 3).
- Spec said client `ping` is a JSON message; the plan uses the bare text frame `ping` so Cloudflare
  answers without waking the object. Plan 2's client sends the text frame.
- `DELETE /v1/me` exists for the verify's clean-up (the window has no button for it, as the spec says).
