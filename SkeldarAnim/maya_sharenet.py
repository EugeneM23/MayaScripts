"""maya_sharenet - the Shared section's network. Stdlib only, no `maya`.

A file goes to litterbox.catbox.moe (anonymous, up to 1 GB, kept 72 hours);
a record of it goes to an ntfy.sh channel, and every colleague's Maya holds
that channel open on a `Subscriber` thread. No keys and no accounts for
anybody -- the animator's condition (2026-09-30: «Ключи никакие не нужны»).

Measured from the animator's machine on 2026-09-30, before choosing:

- ntfy.sh: a publish reached a second process's open stream in 1.08 s; a
  message stays in the channel 12 hours (its `expires`);
- litterbox: 1.3-3.3 MB/s up and down (8 MB: 2.6-5.8 s up, 2.5-13.7 s down),
  against 4 MB/s from GitHub's release assets;
- filebin.net answered its download with an HTML page, 0x0.st and ntfy's own
  attachments aborted the connection, tmpfiles.org keeps files an hour.

`topic` and `base` default to the module constants AT CALL TIME, so a verify
run points the whole module at a test channel by setting `TOPIC`.

Spec: docs/superpowers/specs/2026-09-30-shared-files-design.md
"""

import json
import os
import socket
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid

import maya_sharerecords as records

UPLOAD_URL = "https://litterbox.catbox.moe/resources/internals/api.php"
KEEP = "72h"                    # litterbox's longest: 1h, 12h, 24h or 72h
NTFY = "https://ntfy.sh"
#  The studio's channel. Anybody who reads this repository can read it and
#  post to it: `maya_sharerecords.parse` is the gate.
TOPIC = "skeldaranim-share-e7dfb344c3b3ac98"
USER_AGENT = "SkeldarAnim-share"

TIMEOUT = 60                    # seconds per socket read, uploads and downloads
STREAM_TIMEOUT = 120            # ntfy sends a keepalive on an idle stream
CHUNK = 256 * 1024              # how often progress is reported
DELAYS = (1, 2, 4, 8, 16, 30)   # the subscriber's waits between reconnects
UPLOAD_NAME = "share.zip"       # the real name travels in the record


class ShareError(Exception):
    """A failure worth a sentence on the status line."""


class Expired(ShareError):
    """The file is no longer on litterbox (404)."""


class Cancelled(ShareError):
    """A progress callback asked to stop."""


def _open(request, timeout=TIMEOUT):
    """The one function that opens a connection."""
    return urllib.request.urlopen(request, timeout=timeout)


def _reason(exc):
    return str(getattr(exc, "reason", None) or exc) or type(exc).__name__


class MultipartBody(object):
    """A multipart/form-data body read from the disk as it is sent, with its
    exact length (http.client reads a body that has `read`, and litterbox
    wants a Content-Length, not a chunked upload). `progress(done, total)`
    is called every `CHUNK` bytes and at the end; returning False from it
    raises Cancelled inside the send."""

    def __init__(self, path, fields, file_field, filename, progress=None):
        self.boundary = "----SkeldarShare" + uuid.uuid4().hex
        head = []
        for name, value in fields:
            head.append('--{0}\r\nContent-Disposition: form-data; '
                        'name="{1}"\r\n\r\n{2}\r\n'.format(self.boundary,
                                                           name, value))
        head.append('--{0}\r\nContent-Disposition: form-data; name="{1}"; '
                    'filename="{2}"\r\nContent-Type: application/zip\r\n\r\n'
                    .format(self.boundary, file_field, filename))
        self._head = "".join(head).encode("utf-8")
        self._tail = "\r\n--{0}--\r\n".format(self.boundary).encode("ascii")
        self._path = path
        self.length = (len(self._head) + os.path.getsize(path)
                       + len(self._tail))
        self._file = None
        self._stage = 0             # 0 head, 1 file, 2 tail, 3 done
        self._offset = 0
        self._progress = progress
        self.done = 0
        self._reported = 0

    @property
    def content_type(self):
        return "multipart/form-data; boundary=" + self.boundary

    def read(self, size=-1):
        if size is None or size < 0:
            size = self.length
        out = []
        count = 0
        while count < size and self._stage < 3:
            want = size - count
            if self._stage == 1:
                if self._file is None:
                    self._file = open(self._path, "rb")
                piece = self._file.read(want)
                if not piece:
                    self._file.close()
                    self._stage, self._offset = 2, 0
                    continue
            else:
                source = self._head if self._stage == 0 else self._tail
                piece = source[self._offset:self._offset + want]
                self._offset += len(piece)
                if self._offset >= len(source):
                    self._stage, self._offset = self._stage + 1, 0
            out.append(piece)
            count += len(piece)
        data = b"".join(out)
        self.done += len(data)
        self._report()
        return data

    def _report(self):
        if self._progress is None:
            return
        if self.done - self._reported < CHUNK and self.done < self.length:
            return
        self._reported = self.done
        if self._progress(self.done, self.length) is False:
            raise Cancelled("cancelled")

    def close(self):
        if self._file is not None:
            self._file.close()
            self._file = None


def upload(path, progress=None, url=None, keep=KEEP):
    """`path` onto litterbox; its address. ShareError otherwise."""
    body = MultipartBody(path, [("reqtype", "fileupload"), ("time", keep)],
                         "fileToUpload", UPLOAD_NAME, progress)
    request = urllib.request.Request(
        url or UPLOAD_URL, data=body, method="POST",
        headers={"User-Agent": USER_AGENT, "Content-Type": body.content_type,
                 "Content-Length": str(body.length)})
    try:
        with _open(request) as response:
            text = response.read().decode("utf-8", "replace").strip()
    except Cancelled:
        raise
    except urllib.error.HTTPError as exc:
        raise ShareError("litterbox answered {0} {1}".format(exc.code,
                                                             exc.reason))
    except (urllib.error.URLError, socket.timeout, OSError) as exc:
        raise ShareError("could not reach litterbox: " + _reason(exc))
    finally:
        body.close()
    if not records.allowed_url(text):
        raise ShareError("litterbox answered {0!r}, not a file address".format(
            text[:120]))
    return text


def publish(text, topic=None, base=None):
    """`text` into the channel; the message's id."""
    request = urllib.request.Request(
        "{0}/{1}".format(base or NTFY, urllib.parse.quote(topic or TOPIC)),
        data=text.encode("utf-8"), method="POST",
        headers={"User-Agent": USER_AGENT})
    try:
        with _open(request) as response:
            answer = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        raise ShareError("ntfy.sh answered {0} {1}".format(exc.code,
                                                           exc.reason))
    except (urllib.error.URLError, socket.timeout, OSError) as exc:
        raise ShareError("could not reach ntfy.sh: " + _reason(exc))
    try:
        return json.loads(answer).get("id") or ""
    except (ValueError, AttributeError):
        return ""


def _remove(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def download(url, path, progress=None):
    """`url` into `path` (written through `path + ".part"`, so `path` exists
    only whole); the bytes. Expired on 404, Cancelled, ShareError."""
    part = path + ".part"
    done = 0
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with _open(request) as response, open(part, "wb") as out:
            total = int(response.headers.get("Content-Length") or 0)
            while True:
                chunk = response.read(CHUNK)
                if not chunk:
                    break
                out.write(chunk)
                done += len(chunk)
                if progress is not None and progress(done, total) is False:
                    raise Cancelled("cancelled")
    except Cancelled:
        _remove(part)
        raise
    except urllib.error.HTTPError as exc:
        _remove(part)
        if exc.code == 404:
            raise Expired("the file is gone from litterbox (72 hours)")
        raise ShareError("litterbox answered {0} {1}".format(exc.code,
                                                             exc.reason))
    except (urllib.error.URLError, socket.timeout, OSError) as exc:
        _remove(part)
        raise ShareError("the download failed: " + _reason(exc))
    os.replace(part, path)
    return done


class Subscriber(threading.Thread):
    """The channel held open: every event of ntfy's JSON stream goes to
    `on_event(event)`, on THIS thread (the caller hands it to Maya's main
    thread). `since` follows the last message id, so a reconnect -- after
    1, 2, 4 ... 30 s -- misses nothing the channel still holds. `on_state`
    hears "online" and "offline - <why>". `stop()` shuts the socket down so
    a blocked read returns at once."""

    def __init__(self, on_event, since="12h", on_state=None, topic=None,
                 base=None, delays=DELAYS, timeout=STREAM_TIMEOUT):
        threading.Thread.__init__(self, name="SkeldarShareSubscriber")
        self.daemon = True
        self.on_event = on_event
        self.on_state = on_state
        self.since = since or "12h"
        self.topic = topic
        self.base = base
        self.delays = tuple(delays) or (1,)
        self.timeout = timeout
        self.state = "connecting..."
        self._halt = threading.Event()
        self._response = None

    def url(self):
        return "{0}/{1}/json?since={2}".format(
            self.base or NTFY, urllib.parse.quote(self.topic or TOPIC),
            urllib.parse.quote(str(self.since)))

    def stopped(self):
        return self._halt.is_set()

    def stop(self):
        """Halt, and unblock a read in progress. Measured 2026-09-30 on
        Windows: `response.close()` from here waits on the buffer's lock,
        which the reading thread holds until its read times out, and
        `socket.shutdown` does not wake a read waiting under a timeout --
        both took the whole STREAM_TIMEOUT. Closing the SocketIO beneath the
        buffer wakes it at once (the read raises; the reader ends)."""
        self._halt.set()
        response = self._response
        if response is None:
            return
        try:
            response.fp.raw.close()
        except Exception:                                    # noqa: BLE001
            pass

    def _tell(self, state):
        self.state = state
        if self.on_state is not None and not self.stopped():
            try:
                self.on_state(state)
            except Exception:                                # noqa: BLE001
                pass

    def _dispatch(self, raw):
        line = raw.strip()
        if not line:
            return
        try:
            event = json.loads(line.decode("utf-8"))
        except ValueError:
            return
        if not isinstance(event, dict):
            return
        if event.get("event") == "message" and event.get("id"):
            self.since = event["id"]
        try:
            self.on_event(event)
        except Exception:                                    # noqa: BLE001
            pass

    def run(self):
        failures = 0
        while not self.stopped():
            try:
                request = urllib.request.Request(
                    self.url(), headers={"User-Agent": USER_AGENT})
                response = _open(request, timeout=self.timeout)
                self._response = response
                try:
                    self._tell("online")
                    failures = 0
                    for raw in response:
                        if self.stopped():
                            return
                        self._dispatch(raw)
                finally:
                    self._response = None
                    try:
                        response.close()
                    except Exception:                        # noqa: BLE001
                        pass    # its SocketIO closed under it by stop()
                reason = "the channel closed the stream"
            except Exception as exc:                         # noqa: BLE001
                if self.stopped():
                    return
                reason = _reason(exc)
            failures += 1
            self._tell("offline - " + reason)
            self._halt.wait(self.delays[min(failures, len(self.delays)) - 1])
