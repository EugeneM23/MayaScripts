"""Scene tabs: the Anim Layer Editor shows the active tab as an ordinary scene.

While tabs are on, Maya's root layer is the session's (`skeldarTabsLayerRoot`) and
each tab's layers hang under a root of the tab's own (`<tab>:AnimLayerRoot`,
`layers`). Maya's editor walks from the root and drew both holders as layers
(2026-10-16, found live): an empty tab showed `skeldarTabsLayerRoot`, a tab with
layers showed `AnimLayerRoot` between the base and its layers, and a click on
the base selected every layer when its `collapse` flag was on (Maya's own
`animLayerEditorOnSelect` selects a collapsed layer's children; the animator's
root carried the flag).

Maya's `layerEditor.mel` is read, two of its procs changed by exact lines, and the
whole changed copy sourced from a file of ours - the procs call local procs of
their own file, which a proc defined on its own cannot reach (`getBestLayers`,
measured). Then ours are defined over it (the scene's layers are never touched):
- `buildAnimLayerArray` (ours): a tab's root is left out of the list, its layers
  are listed; with nothing to show (an empty tab) the list is empty - an empty
  editor, as in a scene with no layers. With tabs off it is Maya's own.
- `rebuildAnimLayerEditor` (two lines changed): a layer under a tab's root sits at
  the top, as a layer on the base does; the session's root reads BaseAnimation and
  a layer of the active tab its name without the tab's prefix.
- `animLayerEditorOnSelect` (one line changed): a click on the session's root
  selects the root alone, whatever its collapse flag.
Maya sources its own file again when it builds the Channel Box / Layer Editor
(`initChannelsLayers`, `initLayers`); `ensure` puts ours back before each of our
editor refreshes. A Maya whose text differs keeps its own procs, said in the
Script Editor. GUI only; never raises.
"""

import os
import re
import sys
import tempfile
import traceback

from . import records

ROOT = records.LAYER_ROOT
TAB_ROOT = records.TAB_LAYER_ROOT
FILE = "layerEditor.mel"
PATCHED = "skeldarLayerEditor.mel"           # never FILE: `_source_file` must not find it
BUILD = "createLayerEditor($gLayerEditorForm);"   # in the file's last bare block: builds the editor's UI

HELPERS = r'''
global proc int skeldarTabsHolder(string $layer)
{
    if (`animLayer -q -parent $layer` != "%(root)s")
        return 0;
    string $leaf = match("[^:]*$", $layer);
    return size(match("^%(tab)s[0-9]*$", $leaf)) > 0;
}

global proc string skeldarTabsLayerLabel(string $label, string $layer)
{
    if (`animLayer -q -root` != "%(root)s")
        return $label;
    if ($layer == "%(root)s")
        return "BaseAnimation";
    string $active = `namespaceInfo -currentNamespace`;
    if ($active == ":" || $active == "")
        return $label;
    string $prefix = $active + ":";
    int $n = size($prefix);
    if (size($label) > $n && substring($label, 1, $n) == $prefix)
        return substring($label, $n + 1, size($label));
    return $label;
}

global proc skeldarTabsLayerWalk(string $layer, string $out[])
{
    string $children[] = `animLayer -query -children $layer`;
    for ($child in $children)
    {
        if (!skeldarTabsHolder($child))
            $out[size($out)] = $child;
        skeldarTabsLayerWalk($child, $out);
    }
}

global proc string[] buildAnimLayerArray()
{
    string $root = `animLayer -q -root`;
    string $out[];
    if ($root == "")
        return $out;
    if ($root != "%(root)s")
    {
        $out[0] = $root;
        buildAnimLayerArrayRecursive($root, $out);
        return $out;
    }
    string $shown[];
    skeldarTabsLayerWalk($root, $shown);
    if (!size($shown))
        return $out;
    $out[0] = $root;
    for ($layer in $shown)
        $out[size($out)] = $layer;
    return $out;
}
''' % {"root": ROOT, "tab": TAB_ROOT}

#  (proc, [(Maya's exact line, ours)]) - each line must be found exactly once
CHANGES = (
    ("rebuildAnimLayerEditor", (
        ('if( $grandParentLayer == "")',
         'if( $grandParentLayer == "" || skeldarTabsHolder($parentLayer))'),
        ('string $name = displayLabel( $showNamespace, $indentLayer);',
         'string $name = skeldarTabsLayerLabel(displayLabel( $showNamespace, $indentLayer), $indentLayer);'),
    )),
    ("animLayerEditorOnSelect", (
        ('int $collapse = `animLayer -query -collapse $layer`;',
         'int $collapse = `animLayer -query -collapse $layer` && $layer != "%s";' % ROOT),
    )),
)


def proc_text(text, name):
    """The whole `global proc ... name(...) { ... }` of `name` in a MEL file's text, or
    None. Braces inside strings and comments do not count. Pure."""
    found = re.search(r"global\s+proc\s+(?:[\w\[\]]+\s+)?%s\s*\(" % re.escape(name), text)
    if not found:
        return None
    at = text.find("{", found.end())
    if at < 0:
        return None
    depth, i, quote = 0, at, False
    while i < len(text):
        char = text[i]
        if quote:
            if char == "\\":
                i += 2
                continue
            if char == '"':
                quote = False
        elif char == '"':
            quote = True
        elif text.startswith("//", i):
            end = text.find("\n", i)
            i = len(text) if end < 0 else end
            continue
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = len(text) if end < 0 else end + 2
            continue
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[found.start():i + 1]
        i += 1
    return None


def _depth0_blocks(text):
    """(start, end) of every brace block at the top level of MEL text, end past
    its `}`. Braces inside strings and comments do not count. Pure."""
    blocks, depth, i, quote, start = [], 0, 0, False, 0
    while i < len(text):
        char = text[i]
        if quote:
            if char == "\\":
                i += 2
                continue
            if char == '"':
                quote = False
        elif char == '"':
            quote = True
        elif text.startswith("//", i):
            end = text.find("\n", i)
            i = len(text) if end < 0 else end
            continue
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = len(text) if end < 0 else end + 2
            continue
        elif char == "{":
            if depth == 0:
                start = i
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                blocks.append((start, i + 1))
        i += 1
    return blocks


def _uncommented_before(text, at):
    """The code before `at`, comments removed, trailing space stripped. Pure."""
    code = re.sub(r"/\*.*?\*/", "", text[:at], flags=re.S)
    return re.sub(r"//[^\n]*", "", code).rstrip()


def without_build(text):
    """The file's text without its bare top-level block that builds the editor's
    UI (sourced again it would build a second one: «Object's name
    'DisplayLayerUITabLayout' is not unique», measured), or None. Pure."""
    at = text.find(BUILD)
    if at < 0 or text.find(BUILD, at + 1) >= 0:
        return None
    for start, end in _depth0_blocks(text):
        if start < at < end:
            if _uncommented_before(text, start).endswith(")"):
                return None             # a proc's body or an if's: not the bare block
            return text[:start] + text[end:]
    return None


def changed(text, changes):
    """`text` with each (old, new) applied, or None when an old line is not there
    exactly once. Pure."""
    for old, new in changes:
        if text.count(old) != 1:
            return None
        text = text.replace(old, new)
    return text


def patched_procs(source):
    """{name: changed text} for every proc of CHANGES, or (None, the reason). Pure."""
    out = {}
    for name, changes in CHANGES:
        text = proc_text(source, name)
        if text is None:
            return None, "%s is not in %s" % (name, FILE)
        new = changed(text, changes)
        if new is None:
            return None, "%s in %s is not the text this patch knows" % (name, FILE)
        out[name] = new
    return out, ""


def patched_file(source):
    """Maya's whole file with CHANGES applied, or (None, the reason). Pure."""
    procs, reason = patched_procs(source)
    if procs is None:
        return None, reason
    text = without_build(source)
    if text is None:
        return None, "the block of %s that builds the editor is not the one this patch knows" % FILE
    for name, _ in CHANGES:
        text = text.replace(proc_text(source, name), procs[name], 1)
    return text, ""


def _source_file():
    """Maya's own layerEditor.mel: its install's, else where Maya found it."""
    path = os.path.join(os.environ.get("MAYA_LOCATION", ""), "scripts", "startup", FILE)
    if os.path.isfile(path):
        return path
    import maya.mel as mel
    try:
        where = mel.eval('whatIs "rebuildAnimLayerEditor"') or ""
    except RuntimeError:
        where = ""
    marker = "found in: "
    if marker in where:
        path = where.split(marker, 1)[1].strip()
        if os.path.basename(path) == FILE and os.path.isfile(path):
            return path
    return ""


def _state():
    state = getattr(sys, "_skeldar_layereditor", None)
    if state is None:
        state = {"failed": ""}
        sys._skeldar_layereditor = state
    return state


def installed():
    """Our copy is what Maya runs (Maya sourced its own file again otherwise)."""
    import maya.mel as mel
    try:
        return PATCHED in (mel.eval('whatIs "rebuildAnimLayerEditor"') or "")
    except RuntimeError:
        return False


def install():
    """The changed copy sourced, ours defined over it, the editor rebuilt. True when patched."""
    try:
        import maya.cmds as cmds
        if cmds.about(batch=True):
            return False
        state = _state()
        path = _source_file()
        if not path:
            state["failed"] = "%s not found" % FILE
            print("Scene Tabs: %s - the Anim Layer Editor keeps Maya's own procs" % state["failed"])
            return False
        with open(path, encoding="utf-8", errors="replace") as handle:
            text, reason = patched_file(handle.read())
        if text is None:
            state["failed"] = reason
            print("Scene Tabs: %s - the Anim Layer Editor keeps Maya's own procs" % reason)
            return False
        folder = os.path.join(tempfile.gettempdir(), "skeldar_scenetabs")
        if not os.path.isdir(folder):
            os.makedirs(folder)
        target = os.path.join(folder, PATCHED)
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(text)
        import maya.mel as mel
        mel.eval('source "%s";' % target.replace("\\", "/"))
        mel.eval(HELPERS)
        state["failed"] = ""
        from . import layers
        layers.refresh_editors()
        return True
    except Exception:                                           # noqa: BLE001
        print(traceback.format_exc())
        return False


def ensure():
    """Ours again when Maya has sourced its own file since (GUI only, never raises).
    A Maya whose text this patch does not know is not read again."""
    try:
        import maya.cmds as cmds
        if cmds.about(batch=True) or _state()["failed"] or installed():
            return
        install()
    except Exception:                                           # noqa: BLE001
        print(traceback.format_exc())
