"""walkfile.py - a saved walk: the cycle as the model reads it (every joint's world on every frame) and each
bone's parent, canonical name and rest, in one gzip JSON file (format `skeldar.walk` 1). stdlib + numpy.

The design: docs/superpowers/specs/2026-10-12-walk-onto-any-skeleton-design.md.
"""
import gzip
import json
import os
import re

import numpy as np

FORMAT = "skeldar.walk"
VERSION = 1
SUFFIX = ".walk.gz"
# a skeleton is Manny's when its median bone length is within this of his (template_rests)
TEMPLATE_TOLERANCE = 0.01
SHORTEST = 1.0           # cm: a shorter bone does not vote
NOT_A_BONE = ("root", "pelvis")
HELPERS = ("ik_", "weapon_", "camera_", "interaction", "center_of_mass")


class Refusal(Exception):
    """A file this tool does not read; the message says why."""


def safe_name(name):
    """A file-safe walk name: anything but letters, digits, '_', '-', '.' becomes '_'."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name or "").strip("._") or "walk"


def path_for(folder, name):
    return os.path.join(folder, safe_name(name) + SUFFIX)


def names_in(folder):
    """The walks saved in `folder`, sorted (their names, no suffix)."""
    if not os.path.isdir(folder):
        return []
    return sorted(f[:-len(SUFFIX)] for f in os.listdir(folder) if f.endswith(SUFFIX))


def save(path, clip, statics, start=0):
    """`clip` (walkmodel.Clip), `statics` {leaf: {"parent", "canonical", "rest" (16 floats)}} and the
    cycle's first frame `start` to `path`."""
    folder = os.path.dirname(path)
    if folder and not os.path.isdir(folder):
        os.makedirs(folder)
    data = {
        "format": FORMAT, "version": VERSION, "name": clip.name, "fps": clip.fps, "start": int(start),
        "up": [float(v) for v in clip.up], "names": list(clip.names), "parents": list(clip.parents),
        "worlds": [[[round(float(v), 9) for v in m.reshape(16)] for m in joint] for joint in clip.worlds],
        "statics": dict((leaf, {"parent": b.get("parent"), "canonical": b.get("canonical"),
                                "rest": [float(v) for v in b["rest"]]}) for leaf, b in statics.items()),
    }
    temporary = path + ".part"
    with gzip.open(temporary, "wt", encoding="utf-8") as handle:
        json.dump(data, handle)
    if os.path.exists(path):
        os.remove(path)
    os.rename(temporary, path)


def load(path):
    """The saved walk as a dict: names, parents, worlds (J, F, 4, 4), fps, up, name, start, statics."""
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as error:
        raise Refusal("%s is not a saved walk (%s)" % (os.path.basename(path), error))
    if data.get("format") != FORMAT or int(data.get("version", 0)) > VERSION:
        raise Refusal("%s is not a walk this tool reads (format %s, version %s)"
                      % (os.path.basename(path), data.get("format"), data.get("version")))
    count = len(data["names"])
    data["worlds"] = np.array(data["worlds"], float).reshape(count, -1, 4, 4)
    data.setdefault("start", 0)
    return data


def clip_of(data, model):
    """The loaded walk as `model.Clip` (model: the walkmodel module)."""
    return model.Clip(data["names"], data["parents"], data["worlds"], data["fps"], data["up"], data["name"])


def template_rests(positions, parents, template):
    """{bone: Manny's bind (16 floats)} for a skeleton whose bones are Manny's, else None. Pure.

    `positions` {bone: (x, y, z)} at any frame (bone lengths do not depend on the pose), `parents`
    {bone: parent or None}, `template` {bone: {"parent", "world_matrix"}} (the plugin's
    assets/manny_skeleton_template.json). Manny's: the bones both share (helpers, the root-pelvis offset and
    bones under 1 cm left out) differ in length by a median of at most TEMPLATE_TOLERANCE, and the skeleton
    has every leg bone Manny has. Bones the template does not hold are left out of the answer."""
    diffs = []
    for bone, parent in parents.items():
        if parent is None or bone in NOT_A_BONE or bone.startswith(HELPERS):
            continue
        if bone not in template or parent not in template or template[bone].get("parent") != parent:
            continue
        mine = float(np.linalg.norm(np.array(positions[bone]) - np.array(positions[parent])))
        his = float(np.linalg.norm(np.array(template[bone]["world_matrix"][12:15]) -
                                   np.array(template[parent]["world_matrix"][12:15])))
        if max(mine, his) < SHORTEST:
            continue
        diffs.append(abs(mine - his) / max(mine, his))
    legs = ("thigh_l", "calf_l", "foot_l", "thigh_r", "calf_r", "foot_r")
    if len(diffs) < 10 or any(b not in parents for b in legs) or sorted(diffs)[len(diffs) // 2] > TEMPLATE_TOLERANCE:
        return None
    return dict((b, list(template[b]["world_matrix"])) for b in parents if b in template)


def read_template(path):
    """{bone: {"parent", "world_matrix"}} from the plugin's skeleton template file."""
    with open(path) as handle:
        joints = json.load(handle)["joints"]
    return dict((j["name"], {"parent": j.get("parent"), "world_matrix": [float(v) for v in j["world_matrix"]]})
                for j in joints)
