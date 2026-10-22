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

    def raw(self, method, path, data=None, content_type="application/octet-stream", timeout=TIMEOUT):
        """Bytes out and bytes back (avatars). A refusal is a ChatError as for call()."""
        headers = {"User-Agent": AGENT}
        if data is not None:
            headers["Content-Type"] = content_type
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        req = urllib.request.Request(self.server + path, data=data, method=method, headers=headers)
        try:
            with self.opener(req, timeout=timeout) as answer:
                return answer.read()
        except urllib.error.HTTPError as exc:
            raw, status = exc.read(), exc.code
        except (urllib.error.URLError, socket.timeout, OSError) as exc:
            raise ChatError("offline", "The chat server did not answer (%s)" % getattr(exc, "reason", exc))
        try:
            doc = json.loads(raw.decode("utf-8") or "{}")
        except ValueError:
            doc = {}
        raise ChatError(doc.get("error") or "server", doc.get("text") or "Refused", status)

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

    def put_avatar(self, data, content_type="image/jpeg"):
        """My picture (JPEG or PNG, at most 256 KB); answers me."""
        raw = self.raw("PUT", "/v1/me/avatar", bytes(data), content_type)
        return json.loads(raw.decode("utf-8") or "{}")

    def avatar(self, user_id):
        return self.raw("GET", "/v1/avatar/u/" + user_id)

    def delete_me(self):
        return self.call("DELETE", "/v1/me")

    # ---------------------------------------------------------------- people
    def users(self, q):
        return self.call("GET", "/v1/users?q=" + urllib.parse.quote(q))["users"]

    def person_files(self, user_id, before=None):
        """{user, files: [{msg, chat, seq, at, text, file, chat_kind, chat_name}], more}: what
        `user_id` sent in the chats I am in, newest first."""
        path = "/v1/users/%s/files" % user_id
        if before:
            path += "?before=%d" % int(before)
        return self.call("GET", path)

    def people(self):
        return self.call("GET", "/v1/people")["users"]

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

    # ---------------------------------------------------------------- files (2026-10-22)
    def file_start(self, chat_id, name, kind, size, zip_size, fps=None, frame_range=None):
        """An upload begun: {id, part_size, parts}."""
        return self.call("POST", "/v1/files", {"chat": chat_id, "name": name, "kind": kind,
                                               "bytes": int(size), "zip": int(zip_size),
                                               "fps": fps, "range": frame_range})

    def file_part(self, file_id, n, data):
        raw = self.raw("PUT", "/v1/files/%s/parts/%d" % (file_id, n), bytes(data), timeout=PART_TIMEOUT)
        return json.loads(raw.decode("utf-8") or "{}")

    def file_complete(self, file_id):
        return self.call("POST", "/v1/files/%s/complete" % file_id)

    def file_thumb_put(self, file_id, data, sheet=None):
        """The preview of my file on its way (a JPEG); `sheet` - an animation's grid."""
        path = "/v1/files/%s/thumb" % file_id
        if sheet:
            path += "?" + urllib.parse.urlencode({"cells": int(sheet["cells"]),
                                                  "columns": int(sheet["columns"]),
                                                  "step": int(sheet.get("step") or 1),
                                                  "fps": float(sheet.get("fps") or 30.0)})
        raw = self.raw("PUT", path, bytes(data), "image/jpeg")
        return json.loads(raw.decode("utf-8") or "{}")

    def file_thumb(self, file_id):
        return self.raw("GET", "/v1/files/%s/thumb" % file_id)

    def file_cancel(self, file_id):
        return self.call("DELETE", "/v1/files/" + file_id)

    def file_download(self, file_id, path, progress=None):
        """The file's zip streamed to `path` (via path + ".part"); its size. `progress(done, total)`
        answering False stops it (ChatError "cancelled")."""
        headers = {"User-Agent": AGENT}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        req = urllib.request.Request(self.server + "/v1/files/" + file_id, method="GET",
                                     headers=headers)
        part = path + ".part"
        try:
            with self.opener(req, timeout=PART_TIMEOUT) as answer:
                headers = getattr(answer, "headers", None) or {}
                total = int(headers.get("content-length") or 0)
                done = 0
                with open(part, "wb") as out:
                    while True:
                        piece = answer.read(PIECE)
                        if not piece:
                            break
                        out.write(piece)
                        done += len(piece)
                        if progress is not None and progress(done, total) is False:
                            raise ChatError("cancelled", "Stopped")
        except urllib.error.HTTPError as exc:
            raw, status = exc.read(), exc.code
            try:
                doc = json.loads(raw.decode("utf-8") or "{}")
            except ValueError:
                doc = {}
            _remove(part)
            raise ChatError(doc.get("error") or "server", doc.get("text") or "Refused", status)
        except (urllib.error.URLError, socket.timeout, OSError) as exc:
            _remove(part)
            raise ChatError("offline", "The chat server did not answer (%s)" % getattr(exc, "reason", exc))
        except ChatError:
            _remove(part)
            raise
        if total and done != total:
            _remove(part)
            raise ChatError("offline", "The download stopped half way")
        import os
        os.replace(part, path)
        return done


PART_TIMEOUT = 120
PIECE = 1024 * 1024


def _remove(path):
    import os
    try:
        os.remove(path)
    except OSError:
        pass
