"""glTF 2.0 (.gltf + .bin, .glb) skeletal animation: read and write. stdlib only.

2026-10-02 («максимальный обхват форматов»). glTF is Blender's and the
web's exchange format, documented to the byte (Khronos glTF 2.0 spec), so it
is read here without any plugin:

- the document: JSON, either a .gltf (buffers by URI: a file beside it, or a
  base64 `data:` URI) or a .glb (a 12-byte header, a JSON chunk and a BIN
  chunk that buffer 0 without a URI stands for);
- accessors through bufferViews: FLOAT and the integer types, `normalized`
  ones mapped to [-1, 1] / [0, 1] as the spec says, `byteStride` honoured,
  sparse accessors refused by name;
- the skeleton: every skin's joints and their ancestors among the nodes (a
  file with no skin: the animated nodes and theirs), each node's REST TRS
  (`translation`/`rotation`/`scale`, or a `matrix` decomposed);
- every `animations[i]` is a clip: its channels' samplers (`input` times in
  seconds, `output` values, LINEAR / STEP / CUBICSPLINE) evaluated at the
  union of that clip's key times - exact at every key; quaternions slerped
  for LINEAR, a CUBICSPLINE's value taken between its two tangents.

Axes: glTF is Y-up and right-handed, like Maya - nothing turns. Units:
metres, so translations are scaled by `units` (100 for Maya's centimetres).
"""

import base64
import bisect
import collections
import json
import math
import os
import struct

GLB_MAGIC = 0x46546C67          # "glTF"
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942

_COMPONENT = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2),
              5125: ("I", 4), 5126: ("f", 4)}
_NORMAL = {5120: 127.0, 5121: 255.0, 5122: 32767.0, 5123: 65535.0}
_WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT2": 4, "MAT3": 9,
          "MAT4": 16}

Node = collections.namedtuple("Node", "index name parent t r s")
Clip = collections.namedtuple("Clip", "index name start end keys")


class GltfError(ValueError):
    """A file that is not glTF 2.0, or one we cannot read honestly."""


# ------------------------------------------------------------------ document

def split_glb(data):
    """(json dict, bin bytes or None) of a .glb's bytes. Pure."""
    if len(data) < 20:
        raise GltfError("too short for a .glb")
    magic, version, length = struct.unpack_from("<III", data, 0)
    if magic != GLB_MAGIC:
        raise GltfError("not a .glb (bad magic)")
    if version != 2:
        raise GltfError("glb version {0}, only 2 is read".format(version))
    offset, doc, blob = 12, None, None
    while offset + 8 <= min(length, len(data)):
        size, kind = struct.unpack_from("<II", data, offset)
        body = data[offset + 8:offset + 8 + size]
        if kind == CHUNK_JSON:
            doc = json.loads(body.decode("utf-8"))
        elif kind == CHUNK_BIN and blob is None:
            blob = bytes(body)
        offset += 8 + size + (-size % 4)
    if doc is None:
        raise GltfError("no JSON chunk")
    return doc, blob


def load(path):
    """(document, [buffer bytes]) of a .gltf or .glb on disk."""
    with open(path, "rb") as handle:
        data = handle.read()
    if data[:4] == b"glTF":
        doc, blob = split_glb(data)
    else:
        doc, blob = json.loads(data.decode("utf-8")), None
    return doc, buffers_of(doc, blob, os.path.dirname(path))


def buffers_of(doc, blob=None, folder=""):
    """Every buffer's bytes: a GLB's BIN chunk, a data URI, or a file."""
    out = []
    for index, buffer in enumerate(doc.get("buffers") or []):
        uri = buffer.get("uri")
        if uri is None:
            if blob is None:
                raise GltfError("buffer {0} has no uri and no BIN chunk".format(index))
            out.append(blob)
        elif uri.startswith("data:"):
            out.append(base64.b64decode(uri.split(",", 1)[1]))
        else:
            from urllib.parse import unquote
            with open(os.path.join(folder, unquote(uri)), "rb") as handle:
                out.append(handle.read())
    return out


def accessor(doc, buffers, index):
    """Accessor `index` as a list of tuples (one per element). Pure."""
    acc = doc["accessors"][index]
    if acc.get("sparse"):
        raise GltfError("accessor {0} is sparse - not read".format(index))
    count, width = acc["count"], _WIDTH[acc["type"]]
    code, size = _COMPONENT[acc["componentType"]]
    if "bufferView" not in acc:
        return [tuple([0.0] * width)] * count
    view = doc["bufferViews"][acc["bufferView"]]
    data = buffers[view["buffer"]]
    base = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    stride = view.get("byteStride") or size * width
    scale = _NORMAL.get(acc["componentType"]) if acc.get("normalized") else None
    fmt = "<" + code * width
    out = []
    for i in range(count):
        values = struct.unpack_from(fmt, data, base + i * stride)
        if scale:
            values = tuple(max(v / scale, -1.0) for v in values)
        out.append(tuple(float(v) for v in values))
    return out


# ------------------------------------------------------------------ maths

def _qnorm(q):
    n = math.sqrt(sum(c * c for c in q)) or 1.0
    return tuple(c / n for c in q)


def slerp(a, b, t):
    """Quaternions (x, y, z, w), the short way. Pure."""
    dot = sum(x * y for x, y in zip(a, b))
    if dot < 0.0:
        b, dot = tuple(-c for c in b), -dot
    if dot > 0.9995:
        return _qnorm(tuple(x + (y - x) * t for x, y in zip(a, b)))
    theta = math.acos(max(-1.0, min(1.0, dot)))
    sa, sb = math.sin((1 - t) * theta), math.sin(t * theta)
    s = math.sin(theta)
    return tuple((x * sa + y * sb) / s for x, y in zip(a, b))


def decompose(m):
    """A column-major glTF matrix -> (t, r quaternion xyzw, s). Pure."""
    cols = [m[0:3], m[4:7], m[8:11]]
    s = [math.sqrt(sum(c * c for c in col)) or 1.0 for col in cols]
    r = [[cols[c][row] / s[c] for c in range(3)] for row in range(3)]
    trace = r[0][0] + r[1][1] + r[2][2]
    if trace > 0:
        k = 0.5 / math.sqrt(trace + 1.0)
        q = ((r[2][1] - r[1][2]) * k, (r[0][2] - r[2][0]) * k,
             (r[1][0] - r[0][1]) * k, 0.25 / k)
    elif r[0][0] > r[1][1] and r[0][0] > r[2][2]:
        k = 2.0 * math.sqrt(1.0 + r[0][0] - r[1][1] - r[2][2])
        q = (0.25 * k, (r[0][1] + r[1][0]) / k, (r[0][2] + r[2][0]) / k,
             (r[2][1] - r[1][2]) / k)
    elif r[1][1] > r[2][2]:
        k = 2.0 * math.sqrt(1.0 + r[1][1] - r[0][0] - r[2][2])
        q = ((r[0][1] + r[1][0]) / k, 0.25 * k, (r[1][2] + r[2][1]) / k,
             (r[0][2] - r[2][0]) / k)
    else:
        k = 2.0 * math.sqrt(1.0 + r[2][2] - r[0][0] - r[1][1])
        q = ((r[0][2] + r[2][0]) / k, (r[1][2] + r[2][1]) / k, 0.25 * k,
             (r[1][0] - r[0][1]) / k)
    return tuple(m[12:15]), _qnorm(q), tuple(s)


# ------------------------------------------------------------------ skeleton

def nodes_of(doc):
    """Every node as Node(index, name, parent, t, r, s). Pure."""
    parents = {}
    for index, node in enumerate(doc.get("nodes") or []):
        for child in node.get("children") or []:
            parents[child] = index
    out = []
    for index, node in enumerate(doc.get("nodes") or []):
        if "matrix" in node:
            t, r, s = decompose(node["matrix"])
        else:
            t = tuple(node.get("translation") or (0.0, 0.0, 0.0))
            r = tuple(node.get("rotation") or (0.0, 0.0, 0.0, 1.0))
            s = tuple(node.get("scale") or (1.0, 1.0, 1.0))
        out.append(Node(index, node.get("name") or "node{0}".format(index),
                        parents.get(index), t, r, s))
    return out


def skeleton_nodes(doc):
    """The node indices that make the skeleton, parents first. Pure.

    Every skin's joints and their ancestors (an Armature node above the
    root included); with no skin, the animated nodes and theirs."""
    nodes = nodes_of(doc)
    wanted = set()
    for skin in doc.get("skins") or []:
        wanted.update(skin.get("joints") or [])
    if not wanted:
        for anim in doc.get("animations") or []:
            for channel in anim.get("channels") or []:
                node = channel.get("target", {}).get("node")
                if node is not None and channel["target"].get("path") != "weights":
                    wanted.add(node)
    for index in list(wanted):
        parent = nodes[index].parent
        while parent is not None and parent not in wanted:
            wanted.add(parent)
            parent = nodes[parent].parent

    def depth(index):
        d, parent = 0, nodes[index].parent
        while parent is not None:
            d, parent = d + 1, nodes[parent].parent
        return d
    return sorted(wanted, key=lambda i: (depth(i), i))


def clips(doc, buffers=None):
    """Every animation as Clip(index, name, start, end, keys) - its time span
    in seconds and its key count. Pure (reads only the input accessors'
    min/max when they carry them)."""
    out = []
    for index, anim in enumerate(doc.get("animations") or []):
        lo, hi, keys = None, None, 0
        for sampler in anim.get("samplers") or []:
            acc = doc["accessors"][sampler["input"]]
            keys = max(keys, acc.get("count", 0))
            if "min" in acc and "max" in acc:
                a, b = acc["min"][0], acc["max"][0]
            elif buffers is not None:
                times = [v[0] for v in accessor(doc, buffers, sampler["input"])]
                a, b = min(times), max(times)
            else:
                continue
            lo = a if lo is None else min(lo, a)
            hi = b if hi is None else max(hi, b)
        out.append(Clip(index, anim.get("name") or "animation{0}".format(index),
                        lo, hi, keys))
    return out


def _evaluate(times, values, interp, at, kind):
    """One sampler's value at time `at`. `values` are tuples; a
    CUBICSPLINE's come in (in-tangent, value, out-tangent) triples."""
    cubic = interp == "CUBICSPLINE"
    if cubic:
        values = [values[i * 3 + 1] for i in range(len(times))]
    if at <= times[0]:
        return values[0]
    if at >= times[-1]:
        return values[-1]
    k = bisect.bisect_right(times, at) - 1
    t0, t1 = times[k], times[k + 1]
    u = (at - t0) / (t1 - t0) if t1 > t0 else 0.0
    if interp == "STEP":
        return values[k]
    if kind == "rotation":
        return slerp(values[k], values[k + 1], u)
    return tuple(a + (b - a) * u for a, b in zip(values[k], values[k + 1]))


def tracks(doc, buffers, clip_index):
    """(times in seconds, {node index: {"t"/"r"/"s": [values per time]}}) for
    one animation, sampled at the union of its key times. Pure."""
    anim = (doc.get("animations") or [])[clip_index]
    samplers = anim.get("samplers") or []
    chans = []
    union = set()
    for channel in anim.get("channels") or []:
        target = channel.get("target") or {}
        path = target.get("path")
        if path not in ("translation", "rotation", "scale") or target.get("node") is None:
            continue
        sampler = samplers[channel["sampler"]]
        times = [v[0] for v in accessor(doc, buffers, sampler["input"])]
        values = accessor(doc, buffers, sampler["output"])
        interp = sampler.get("interpolation") or "LINEAR"
        chans.append((target["node"], path, times, values, interp))
        union.update(times)
    times = sorted(union)
    out = collections.defaultdict(dict)
    key = {"translation": "t", "rotation": "r", "scale": "s"}
    for node, path, ts, vs, interp in chans:
        out[node][key[path]] = [_evaluate(ts, vs, interp, at, path) for at in times]
    return times, dict(out)


# ------------------------------------------------------------------ writing

def write_glb(path, nodes, clip_name, times, tracks_by_node, skin_joints=None):
    """A minimal valid .glb: `nodes` [(name, parent index or None, t, r, s)],
    one animation of LINEAR translation/rotation channels per node in
    `tracks_by_node` {index: {"t": [...], "r": [...]}}, `times` in seconds,
    and a skin over `skin_joints` (default every node). The verify's
    writer; pure but for the file."""
    blob = bytearray()
    views, accessors = [], []

    def add(values, kind, minmax=False):
        width = _WIDTH[kind]
        start = len(blob)
        for v in values:
            blob.extend(struct.pack("<" + "f" * width, *(v if width > 1 else (v,))))
        while len(blob) % 4:
            blob.append(0)
        views.append({"buffer": 0, "byteOffset": start,
                      "byteLength": len(values) * 4 * width})
        acc = {"bufferView": len(views) - 1, "componentType": 5126,
               "count": len(values), "type": kind}
        if minmax:
            acc["min"], acc["max"] = [min(values)], [max(values)]
        accessors.append(acc)
        return len(accessors) - 1

    gl_nodes = []
    for name, parent, t, r, s in nodes:
        gl_nodes.append({"name": name, "translation": list(t),
                         "rotation": list(r), "scale": list(s)})
    for index, (_name, parent, _t, _r, _s) in enumerate(nodes):
        if parent is not None:
            gl_nodes[parent].setdefault("children", []).append(index)
    time_acc = add(list(times), "SCALAR", minmax=True)
    samplers, channels = [], []
    for node, track in sorted(tracks_by_node.items()):
        for key, target, kind in (("t", "translation", "VEC3"),
                                ("r", "rotation", "VEC4")):
            if key in track:
                samplers.append({"input": time_acc,
                                 "output": add(track[key], kind),
                                 "interpolation": "LINEAR"})
                channels.append({"sampler": len(samplers) - 1,
                                 "target": {"node": node, "path": target}})
    roots = [i for i, n in enumerate(nodes) if n[1] is None]
    doc = {"asset": {"version": "2.0", "generator": "SkeldarAnim verify"},
           "scene": 0, "scenes": [{"nodes": roots}], "nodes": gl_nodes,
           "skins": [{"joints": list(skin_joints if skin_joints is not None
                                     else range(len(nodes)))}],
           "animations": [{"name": clip_name, "samplers": samplers,
                           "channels": channels}],
           "buffers": [{"byteLength": len(blob)}],
           "bufferViews": views, "accessors": accessors}
    text = json.dumps(doc).encode("utf-8")
    text += b" " * (-len(text) % 4)
    total = 12 + 8 + len(text) + 8 + len(blob)
    with open(path, "wb") as handle:
        handle.write(struct.pack("<III", GLB_MAGIC, 2, total))
        handle.write(struct.pack("<II", len(text), CHUNK_JSON))
        handle.write(text)
        handle.write(struct.pack("<II", len(blob), CHUNK_BIN))
        handle.write(bytes(blob))
    return path
