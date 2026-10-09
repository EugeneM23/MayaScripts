"""The Unreal side of the Cascadeur bridge: list, export and reimport.

Reuses maya_uebridge's stdlib modules unchanged. No Maya, no Cascadeur.
`run_script` is injectable (tests); the default is uelink.run_script.
"""

import os
import re

from maya_uebridge import records
from maya_uebridge import uelink
from maya_uebridge import uescripts

NO_FBX = "the editor did not write {0} - nothing imported"


def _runner(run_script):
    return run_script or uelink.run_script


def safe_name(name):
    """A file name for the clip: letters, digits, underscore and dash only."""
    text = re.sub(r"[^A-Za-z0-9_-]+", "_", (name or "").strip()).strip("_")
    return text or "clip"


def list_clips(out_dir, project=None, run_script=None):
    """(content_dir, records) of every AnimSequence under /Game."""
    out = os.path.join(out_dir, "uelist.json")
    payload = _runner(run_script)(uescripts.list_script(out, "/Game"), out,
                                  project=project)
    return payload.get("content_dir", ""), records.parse_payload(payload)


def export_clip(record, out_dir, project=None, run_script=None):
    """The clip as a bones-only FBX in `out_dir`: (fbx_path, payload)."""
    fbx = os.path.join(out_dir, safe_name(record.name) + ".fbx")
    out = os.path.join(out_dir, "uexport_" + safe_name(record.name) + ".json")
    payload = _runner(run_script)(
        uescripts.export_script(out, record.package, fbx), out, project=project)
    if not os.path.isfile(fbx):
        raise uelink.UeBridgeError(NO_FBX.format(os.path.basename(fbx)))
    return fbx, payload


def reimport(package, fbx, out_dir, project=None, run_script=None):
    """Replace-import `fbx` over the AnimSequence at `package`; the editor's reply."""
    out = os.path.join(out_dir, "ureimport.json")
    return _runner(run_script)(uescripts.reimport_script(out, package, fbx), out,
                               project=project)
