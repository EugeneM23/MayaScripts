"""A `cmds` stand-in for the knot that hides the control it drives (2026-10-29).

Enough of Maya for `knots.hide_source` / `show_hidden`: nodes with a UUID, shapes, attributes
and locks. Everything else raises, so a test cannot pass by accident.
"""


class FakeHideCmds(object):

    def __init__(self):
        self.nodes = {}
        self.deleted = []

    #  ------------------------------------------------------------- the scene

    def add(self, path, uuid, shapes=(), attrs=None):
        self.nodes[path] = {"uuid": uuid, "attrs": dict(attrs or {}),
                            "shapes": list(shapes), "locked": set()}
        return path

    def lock(self, path, attr):
        self.nodes[path]["locked"].add(attr)

    def visible(self, path):
        return self.nodes[path]["attrs"]["visibility"]

    #  ------------------------------------------------------------------ cmds

    def ls(self, name, long=False, uuid=False):
        if name in self.nodes:
            return [self.nodes[name]["uuid"]] if uuid else [name]
        for path, node in self.nodes.items():
            if node["uuid"] == name:
                return [node["uuid"]] if uuid else [path]
        return []

    def objExists(self, name):
        return name in self.nodes

    def attributeQuery(self, attr, node=None, exists=False):
        return attr in self.nodes.get(node, {}).get("attrs", {})

    def addAttr(self, node, longName=None, **kwargs):
        self.nodes[node]["attrs"].setdefault(longName, "")

    def getAttr(self, plug, lock=False):
        node, _, attr = plug.rpartition(".")
        if lock:
            return attr in self.nodes[node]["locked"]
        return self.nodes[node]["attrs"][attr]

    def setAttr(self, plug, value, type=None):
        node, _, attr = plug.rpartition(".")
        if attr in self.nodes[node]["locked"]:
            raise RuntimeError("setAttr: the attribute '%s' is locked" % plug)
        self.nodes[node]["attrs"][attr] = value

    def listRelatives(self, node, shapes=False, fullPath=False, **kwargs):
        if shapes:
            return list(self.nodes.get(node, {}).get("shapes", ())) or None
        return None

    def delete(self, node):
        self.deleted.append(node)
        self.nodes.pop(node, None)
