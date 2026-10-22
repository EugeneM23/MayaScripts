"""Deploy the chat server to Cloudflare through its HTTP API - no Node, no wrangler.

    mayapy server/chat/deploy.py check        the token works; prints the workers.dev subdomain
    mayapy server/chat/deploy.py staging      uploads skeldar-chat-staging; prints "URL <url>"
    mayapy server/chat/deploy.py production   uploads skeldar-chat
    mayapy server/chat/deploy.py keys         asks for the API token (hidden), finds the account
                                              and keeps both as user environment variables

Credentials come only from CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID: the process
environment first, then the user's saved variables (so no restart is needed after `keys`).
Nothing here ever prints a credential.
"""
import json
import os
import sys
import urllib.error
import urllib.request
import uuid

API = "https://api.cloudflare.com/client/v4"
NAMES = {"staging": "skeldar-chat-staging", "production": "skeldar-chat"}
# The R2 bucket a target keeps its chat files in (2026-10-22); made on the first deploy.
BUCKETS = {"staging": "skeldar-chat-files-staging", "production": "skeldar-chat-files"}
R2_OFF = 10042            # "Please enable R2 through the Cloudflare Dashboard."
NO_BUCKET = 10006
COMPAT = "2025-06-01"
MIGRATION = "v1"
HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "worker.js")


class DeployError(Exception):
    pass


def metadata(with_migration, bucket=None):
    meta = {
        "main_module": "worker.js",
        "compatibility_date": COMPAT,
        "bindings": [{"type": "durable_object_namespace", "name": "STUDIO", "class_name": "Studio"}],
    }
    if bucket:
        meta["bindings"].append({"type": "r2_bucket", "name": "FILES", "bucket_name": bucket})
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
        errors = doc.get("errors") or []
        words = "; ".join("%s: %s" % (e.get("code"), e.get("message")) for e in errors)
        error = DeployError(words or "Cloudflare refused the request")
        error.codes = [e.get("code") for e in errors]
        raise error
    return doc.get("result")


NAMES_ENV = ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID")
# A file beside the registry: the Claude app's processes can see a different HKCU than a
# terminal opened outside it (measured 2026-10-20 - keys written by one were absent in the other).
KEYS_FILE = os.path.join(os.path.expanduser("~"), ".skeldar", "cloudflare.json")


def saved(names=NAMES_ENV):
    """The user's saved environment variables (the registry's HKCU Environment key), {} off Windows."""
    try:
        import winreg
    except ImportError:
        return {}
    found = {}
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            for name in names:
                try:
                    found[name] = str(winreg.QueryValueEx(key, name)[0])
                except OSError:
                    pass
    except OSError:
        pass
    try:
        with open(KEYS_FILE, encoding="utf-8") as handle:
            for name, value in json.load(handle).items():
                if name in names and value and name not in found:
                    found[name] = str(value)
    except (OSError, ValueError, AttributeError):
        pass
    return found


def save(values):
    os.makedirs(os.path.dirname(KEYS_FILE), exist_ok=True)
    with open(KEYS_FILE, "w", encoding="utf-8") as handle:
        json.dump(values, handle)
    import ctypes
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE) as key:
        for name, value in values.items():
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
    try:  # tell running programs the environment changed (as setx does)
        ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x1A, 0, "Environment", 2, 2000, None)
    except Exception:
        pass


def _environment(env):
    if env is not os.environ:
        return env
    merged = dict(saved())
    merged.update({k: v for k, v in env.items() if k in NAMES_ENV and v})
    return merged


def accounts(token, opener=urllib.request.urlopen):
    return request("GET", API + "/accounts?per_page=50", token, opener=opener) or []


def keys(ask=None, choose=None, opener=urllib.request.urlopen, store=save):
    """Ask the token once, find the account it reaches, keep both. Returns the account's name."""
    if ask is None:
        import getpass
        ask = lambda: getpass.getpass("Cloudflare API token (not shown as you type): ")
    token = (ask() or "").strip()
    if not token or any(c in token for c in "<> \t") or not token.isascii():
        raise DeployError("That is not a token - paste the token Cloudflare showed you")
    found = accounts(token, opener)
    if not found:
        raise DeployError("The token reaches no account - give it Account > Workers Scripts > Edit")
    if len(found) > 1:
        if choose is None:
            for i, acc in enumerate(found, 1):
                print("  %d  %s" % (i, acc.get("name")))
            choose = lambda: int(input("Which account (number): "))
        found = [found[choose() - 1]]
    store({"CLOUDFLARE_API_TOKEN": token, "CLOUDFLARE_ACCOUNT_ID": found[0]["id"]})
    return found[0].get("name") or "the account"


def _credentials(env):
    env = _environment(env)
    for name in ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID"):
        if not env.get(name):
            raise DeployError("Set %s in the environment first (server/chat/README.md)" % name)
        value = env[name].strip()
        if any(c in value for c in "<> \t") or not value.isascii():
            raise DeployError("%s still holds a placeholder or spaces - put the real value there "
                              "(the value itself is not printed)" % name)
    return env["CLOUDFLARE_API_TOKEN"].strip(), env["CLOUDFLARE_ACCOUNT_ID"].strip()


def check(env=os.environ, opener=urllib.request.urlopen):
    token, account = _credentials(env)
    result = request("GET", "%s/accounts/%s/workers/subdomain" % (API, account), token, opener=opener)
    return result["subdomain"]


def ensure_bucket(token, account, name, opener=urllib.request.urlopen):
    """The R2 bucket `name`, made when missing. Refuses plainly when R2 is off on the account."""
    base = "%s/accounts/%s/r2/buckets" % (API, account)
    try:
        request("GET", base + "/" + name, token, opener=opener)
        return False
    except DeployError as exc:
        codes = getattr(exc, "codes", [])
        if R2_OFF in codes:
            raise DeployError("R2 is not enabled on this Cloudflare account - open the dashboard, "
                              "R2 Object Storage, and enable it (free up to 10 GB); then deploy again")
        if NO_BUCKET not in codes:
            raise
    request("POST", base, token, json.dumps({"name": name}).encode(), "application/json", opener=opener)
    return True


def deploy(target, env=os.environ, opener=urllib.request.urlopen):
    if target not in NAMES:
        raise DeployError("Target is staging or production, not %r" % target)
    token, account = _credentials(env)
    name = NAMES[target]
    with open(SOURCE, "rb") as handle:
        source = handle.read()
    script = "%s/accounts/%s/workers/scripts/%s" % (API, account, name)
    bucket = BUCKETS[target]
    ensure_bucket(token, account, bucket, opener)

    def upload(with_migration):
        boundary = "skeldar" + uuid.uuid4().hex
        body = multipart(metadata(with_migration, bucket), source, boundary)
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
    if len(argv) != 2 or argv[1] not in ("check", "staging", "production", "keys"):
        print(__doc__)
        return 2
    try:
        if argv[1] == "keys":
            print("KEPT for %s - now run: deploy.py check" % keys())
        elif argv[1] == "check":
            print("SUBDOMAIN " + check())
        else:
            print("URL " + deploy(argv[1]))
    except DeployError as exc:
        print("FAILED " + str(exc))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
