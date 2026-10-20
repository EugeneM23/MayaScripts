"""The chat server's HTTP calls. Stdlib only.

Every failure becomes ChatError(code, text): the server's own {error, text}, or "offline" when the
network did not answer. Every request sends our User-Agent - Cloudflare refuses Python-urllib's
default with 403 "error code: 1010" (measured 2026-10-20).
"""
import json
import socket
import urllib.error
import urllib.parse
import urllib.request

AGENT = "skeldar-chat/1"
TIMEOUT = 15


class ChatError(Exception):
    def __init__(self, code, text, status=0):
        Exception.__init__(self, text)
        self.code = code
        self.text = text
        self.status = status


class Api(object):
    def __init__(self, server, token=None, opener=urllib.request.urlopen):
        self.server = server.rstrip("/")
        self.token = token
        self.opener = opener

    def call(self, method, path, body=None):
        headers = {"User-Agent": AGENT}
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        req = urllib.request.Request(self.server + path, data=data, method=method, headers=headers)
        try:
            with self.opener(req, timeout=TIMEOUT) as answer:
                raw, status = answer.read(), getattr(answer, "status", 200)
        except urllib.error.HTTPError as exc:
            raw, status = exc.read(), exc.code
        except (urllib.error.URLError, socket.timeout, OSError) as exc:
            raise ChatError("offline", "The chat server did not answer (%s)" % getattr(exc, "reason", exc))
        try:
            doc = json.loads(raw.decode("utf-8") or "{}")
        except ValueError:
            raise ChatError("server", "The chat server answered something unreadable", status)
        if status >= 400 or (isinstance(doc, dict) and "error" in doc and status >= 400):
            if isinstance(doc, dict):
                raise ChatError(doc.get("error") or "server", doc.get("text") or "Refused", status)
            raise ChatError("server", "Refused", status)
        return doc

    # ---------------------------------------------------------------- the account
    def register(self, nick):
        return self.call("POST", "/v1/register", {"nick": nick})

    def me(self):
        return self.call("GET", "/v1/me")

    def rename(self, name):
        return self.call("PATCH", "/v1/me", {"name": name})

    def delete_me(self):
        return self.call("DELETE", "/v1/me")

    # ---------------------------------------------------------------- people
    def users(self, q):
        return self.call("GET", "/v1/users?q=" + urllib.parse.quote(q))["users"]

    def friends(self):
        return self.call("GET", "/v1/friends")

    def request(self, nick):
        return self.call("POST", "/v1/friends/request", {"nick": nick})

    def answer(self, verb, user_id):
        if verb not in ("accept", "decline", "cancel"):
            raise ValueError(verb)
        return self.call("POST", "/v1/friends/" + verb, {"user": user_id})

    def unfriend(self, user_id):
        return self.call("DELETE", "/v1/friends/" + user_id)

    # ---------------------------------------------------------------- chats
    def chats(self):
        return self.call("GET", "/v1/chats")

    def dm(self, user_id):
        return self.call("POST", "/v1/chats", {"kind": "dm", "with": user_id})

    def group(self, name, members):
        return self.call("POST", "/v1/chats", {"kind": "group", "name": name, "members": list(members)})

    def rename_chat(self, chat_id, name):
        return self.call("PATCH", "/v1/chats/" + chat_id, {"name": name})

    def add_member(self, chat_id, user_id):
        return self.call("POST", "/v1/chats/%s/members" % chat_id, {"user": user_id})

    def remove_member(self, chat_id, user_id):
        return self.call("DELETE", "/v1/chats/%s/members/%s" % (chat_id, user_id))

    def history(self, chat_id, before=None, limit=50):
        query = {"limit": limit}
        if before is not None:
            query["before"] = before
        return self.call("GET", "/v1/chats/%s/messages?%s" % (chat_id, urllib.parse.urlencode(query)))["messages"]
