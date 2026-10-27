"""maya_markers in a real Maya (mayapy standalone, 2026-10-27): the kept answer is the
scan's answer after every kind of change the index watches, and asks no scan while
nothing changed.

    mayapy verify_markers.py

Green 2026-10-27: 0 of 15 gates failed. mayapy then dies on its way out ("Fatal Error.
Attempting to save", nCloth's class cleanup in the exit table) - after the summary,
with the index's callbacks removed too: Maya's exit after a referenced scene, not ours.
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.normpath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))
sys.path.insert(0, PLUGIN)

import maya.standalone  # noqa: E402
maya.standalone.initialize(name="python")
import maya.cmds as cmds  # noqa: E402

import maya_markers  # noqa: E402

M = "skeldarVerifyMark"
FAILED = []
N = [0]


def gate(ok, text):
    N[0] += 1
    print("%s %2d %s" % ("PASS" if ok else "FAIL", N[0], text))
    if not ok:
        FAILED.append(N[0])


def scan():
    return sorted(set(cmds.ls("*." + M, recursive=True, objectsOnly=True, long=True) or []))


def marked(name, parent=None):
    node = cmds.createNode("transform", name=name, **({"parent": parent} if parent else {}))
    cmds.addAttr(node, longName=M, dataType="string")
    maya_markers.touch()
    return cmds.ls(node, long=True)[0]


def same(text):
    found = maya_markers.find(M)
    gate(found == scan(), "%s: %s" % (text, found))


def counting():
    real = maya_markers._scan
    count = [0]

    def spy(*a, **k):
        count[0] += 1
        return real(*a, **k)
    maya_markers._scan = spy
    return count, real


def main():
    gate(maya_markers._install(), "the scene's callbacks stand")
    cmds.namespace(add="rigA")
    a = marked("a")
    b = marked("rigA:b")
    same("two marked, one in a namespace")
    count, real = counting()
    for _ in range(5):
        maya_markers.find(M)
    gate(count[0] == 0, "five asks with nothing changed: %d scans" % count[0])
    cmds.createNode("transform", name="plain")
    maya_markers.find(M)
    gate(count[0] == 1, "a node added: combed again (%d)" % count[0])
    maya_markers._scan = real

    cmds.rename(a, "a_renamed")
    same("renamed")
    grp = cmds.createNode("transform", name="grp")
    cmds.parent("a_renamed", grp)
    same("reparented")
    cmds.undoInfo(state=True)
    cmds.undoInfo(openChunk=True)
    c = marked("c")
    cmds.undoInfo(closeChunk=True)
    same("one more")
    cmds.undo()
    same("undone")
    cmds.redo()
    same("redone")
    cmds.deleteAttr(c + "." + M)
    same("a marker removed")
    cmds.delete("rigA:b")
    same("a marked node deleted")

    path = os.path.join(tempfile.mkdtemp(), "markers.ma")
    cmds.file(rename=path)
    cmds.file(save=True, type="mayaAscii")
    cmds.file(new=True, force=True)
    same("a new scene")
    cmds.file(path, i=True, namespace="imp")
    same("imported")
    cmds.file(path, reference=True, namespace="ref")
    same("referenced")
    cmds.file(path, open=True, force=True)
    same("opened")

    print("%d of %d gates failed" % (len(FAILED), N[0]))


if __name__ == "__main__":
    main()
    os._exit(0)
