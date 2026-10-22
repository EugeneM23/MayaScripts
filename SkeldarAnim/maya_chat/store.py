"""The chat's cache on disk, one folder per server host. Stdlib only.

    token  me.json  chats.json  messages/<chat>.jsonl  outbox.json  since  calls.json

Every write goes to a temporary file and replaces the old one, so a crash never leaves half a file;
a file that cannot be read reads as empty.
"""
import json
import os
import re
import urllib.parse

KEEP = 500


def _safe(name):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


class Store(object):
    def __init__(self, root):
        self.root = root

    @classmethod
    def for_server(cls, base, server):
        host = urllib.parse.urlparse(server).netloc or "server"
        return cls(os.path.join(base, _safe(host)))

    # ---------------------------------------------------------------- the files
    def _path(self, *parts):
        return os.path.join(self.root, *parts)

    def _write(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(tmp, path)

    def _read(self, path):
        try:
            with open(path, encoding="utf-8") as handle:
                return handle.read()
        except OSError:
            return None

    def _json(self, name, default):
        text = self._read(self._path(name))
        if text is None:
            return default
        try:
            value = json.loads(text)
        except ValueError:
            return default
        return value if isinstance(value, type(default)) else default

    # ---------------------------------------------------------------- the record
    def token(self):
        text = (self._read(self._path("token")) or "").strip()
        return text or None

    def set_token(self, token):
        self._write(self._path("token"), token)

    def me(self):
        return self._json("me.json", {}) or None

    def set_me(self, me):
        self._write(self._path("me.json"), json.dumps(me))

    def chats(self):
        return self._json("chats.json", [])

    def set_chats(self, chats):
        self._write(self._path("chats.json"), json.dumps(list(chats)))

    def messages(self, chat_id):
        text = self._read(self._path("messages", _safe(chat_id) + ".jsonl"))
        out = []
        for line in (text or "").splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, dict) and "id" in row and "seq" in row:
                out.append(row)
        return out

    def set_messages(self, chat_id, messages):
        rows = list(messages)[-KEEP:]
        self._write(self._path("messages", _safe(chat_id) + ".jsonl"),
                    "".join(json.dumps(m) + "\n" for m in rows))

    def outbox(self):
        return self._json("outbox.json", [])

    def set_outbox(self, outbox):
        self._write(self._path("outbox.json"), json.dumps(list(outbox)))

    def since(self):
        try:
            return int((self._read(self._path("since")) or "0").strip() or 0)
        except ValueError:
            return 0

    def set_since(self, seq):
        self._write(self._path("since"), str(int(seq)))

    def calls_here(self):
        """The ids of the calls this Maya is in (a crash leaves them here)."""
        return [c for c in self._json("calls.json", []) if isinstance(c, str)]

    def set_calls_here(self, ids):
        self._write(self._path("calls.json"), json.dumps(sorted(set(ids))))

    def forget(self):
        """Sign out on this machine: the token and me go, the history stays."""
        for name in ("token", "me.json"):
            try:
                os.remove(self._path(name))
            except OSError:
                pass
