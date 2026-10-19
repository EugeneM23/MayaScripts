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
