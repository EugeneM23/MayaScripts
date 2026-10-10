"""maya_voice.roster - who is in the room, and who is talking. Pure, stdlib.

Fed with the control messages the server sends (`welcome`, `roster`,
`error`) and with the arrival of audio packets. Nothing here touches Maya.
"""

from maya_voice import protocol

SPEAKING_WINDOW = 0.4


class Roster(object):

    def __init__(self):
        self.me = None
        self.room = None
        self.members = {}
        self.error = ""
        self.last_audio = {}

    def apply(self, msg):
        """Take one control message. Returns what changed: 'welcome',
        'roster', 'error' or None for anything else."""
        kind = msg.get("t")
        if kind == "welcome":
            self.me = int(msg.get("id"))
            self.room = str(msg.get("room") or "")
            self.error = ""
            return "welcome"
        if kind == "roster":
            members = {}
            for item in msg.get("members") or []:
                try:
                    mid = int(item["id"])
                except (KeyError, TypeError, ValueError):
                    continue
                members[mid] = {
                    "name": protocol.clean_name(item.get("name")),
                    "muted": bool(item.get("muted")),
                    "deafened": bool(item.get("deafened")),
                    "sharing": bool(item.get("sharing")),
                }
            self.members = members
            return "roster"
        if kind == "error":
            self.error = str(msg.get("msg") or "error")
            return "error"
        return None

    def heard(self, sender, now):
        """A packet from `sender` arrived at `now` (seconds)."""
        self.last_audio[sender] = now

    def speaking(self, now):
        """The ids of members whose audio arrived within the window."""
        return set(
            mid for mid, at in self.last_audio.items()
            if now - at <= SPEAKING_WINDOW and mid in self.members)

    def sharers(self):
        """The ids of members who are sharing, in id order."""
        return sorted(mid for mid, m in self.members.items() if m["sharing"])

    def reset(self):
        self.me = None
        self.room = None
        self.members = {}
        self.last_audio = {}

    def label(self, mid, now=None):
        """«Name - speaking, muted, deafened, sharing» for one member."""
        m = self.members.get(mid)
        if m is None:
            return ""
        flags = []
        if now is not None and mid in self.speaking(now):
            flags.append("speaking")
        if m["muted"]:
            flags.append("muted")
        if m["deafened"]:
            flags.append("deafened")
        if m["sharing"]:
            flags.append("sharing")
        if mid == self.me:
            flags.insert(0, "you")
        tail = (" - " + ", ".join(flags)) if flags else ""
        return m["name"] + tail
