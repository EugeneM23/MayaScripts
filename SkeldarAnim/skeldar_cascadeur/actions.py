"""The three flows of the bridge window, over injected ports.

The window's buttons call these. Nothing here imports Qt, csc or Maya, so the
whole flow is tested with fakes. bridge.py wires the real ports.

Ports:
  unreal   -- module-like: list_clips, export_clip, reimport  (unreal.py)
  cascade  -- import_clip_new_tab, export_skeleton, skeleton_roots,
              animation_frames, scene_fps                     (cascade_io.py)
  share    -- module-like: send                                 (shared.py)
  ask      -- callable(text) -> bool, the confirm dialog
"""

import os
import socket

import maya_sharerecords as sharerecords
from maya_uebridge import records
from maya_uebridge import uasset_core
from skeldar_cascadeur import prefs
from skeldar_cascadeur import rules

CANCELLED = "cancelled - nothing changed"
NO_AUTHOR = "type an author name first - nothing sent"
FALLBACK_NAME = "animation.fbx"


def _machine():
    try:
        return socket.gethostname()
    except OSError:
        return "unknown"


class Bridge(object):
    """One bridge window's state and its three flows."""

    def __init__(self, unreal, cascade, share, prefs_path, temp_dir, ask,
                 machine=None, now=None):
        self.unreal = unreal
        self.cascade = cascade
        self.share = share
        self.prefs_path = prefs_path
        self.temp_dir = temp_dir
        self.ask = ask
        self.machine = machine or _machine()
        self.now = now
        self.records = []
        self.content_dir = ""
        self.target = None
        os.makedirs(temp_dir, exist_ok=True)

    # ---- the list ---------------------------------------------------------

    def refresh(self, project=None):
        """Re-read the Unreal list. Returns the status line."""
        self.content_dir, self.records = self.unreal.list_clips(
            self.temp_dir, project=project)
        return "{0} animation(s) in Unreal".format(len(self.records))

    # ---- import -----------------------------------------------------------

    def import_clips(self, picked, project=None):
        """Each picked clip: exported from Unreal, imported into a new tab.
        Returns one status line naming every clip and its frame count."""
        lines = []
        for rec in picked:
            try:
                fbx, _payload = self.unreal.export_clip(rec, self.temp_dir,
                                                        project=project)
                self.cascade.import_clip_new_tab(fbx)
                frames = self.cascade.animation_frames()
                self.target = rec
                lines.append("{0}: new tab, {1} frames".format(
                    rules.clip_tab_name(rec.name),
                    "?" if frames is None else frames))
            except Exception as exc:                    # noqa: BLE001
                lines.append("{0}: {1}".format(rec.name, exc))
        self._remember_target()
        return rules.join_status(lines)

    # ---- export to uasset -------------------------------------------------

    def export_to_uasset(self, record=None, project=None):
        """The scene's skeleton animation back into the picked clip's uasset."""
        rec = record or self.target
        package = rec.package if rec is not None else ""
        uasset = (records.uasset_path_of(package, self.content_dir)
                  if package and self.content_dir else "")
        problem = rules.export_refusal(package, uasset,
                                       bool(uasset) and os.path.isfile(uasset))
        if problem:
            return problem
        problem = rules.skeleton_problem(self.cascade.skeleton_roots())
        if problem:
            return problem

        read_only = uasset_core.is_read_only(uasset)
        if not self.ask(self._confirm_text(rec, read_only)):
            return CANCELLED

        # The export first, into a temp file: a failed export leaves the
        # uasset exactly as it was, flag included.
        fbx = uasset_core.fbx_staging_path(rec.name, self.temp_dir)
        self.cascade.export_skeleton(fbx)
        if read_only:
            failure = uasset_core.clear_read_only(uasset)
            if failure:
                return "cannot clear read-only on {0}: {1}".format(uasset, failure)

        payload = self.unreal.reimport(package, fbx, self.temp_dir, project=project)
        self.target = rec
        self._remember_target()
        return rules.join_status([
            uasset_core.readonly_note(read_only),
            records.reimport_line(payload),
            records.unchanged_warning(payload),
            rules.fps_problem(self.cascade.scene_fps()),
            ("editor: " + str(payload.get("error"))) if payload.get("error") else "",
        ])

    def _confirm_text(self, rec, read_only):
        lines = ["Overwrite the animation in {0}?".format(rec.name), "",
                 "    asset:    {0}".format(rec.package), "",
                 "The asset is REBUILT from an FBX of the scene, so curves the FBX",
                 "does not carry do not survive it ({0}).".format(
                     uasset_core.LOST_CURVES),
                 "",
                 "Perforce is not touched: the uasset is written on disk."]
        if read_only:
            lines += ["", "The file is read-only. That flag will be CLEARED and "
                          "left off."]
        return "\n".join(lines)

    # ---- send to Shared ---------------------------------------------------

    def send_to_shared(self, typed_name, author, project=None):
        """The scene's skeleton animation to everybody, as a zipped FBX."""
        author = (author or "").strip()
        if not author:
            return NO_AUTHOR
        problem = rules.skeleton_problem(self.cascade.skeleton_roots())
        if problem:
            return problem
        name = sharerecords.upload_name(typed_name, FALLBACK_NAME)
        fbx = os.path.join(self.temp_dir, name)
        self.cascade.export_skeleton(fbx)
        self._remember_author(author)
        ready = self.share.send(fbx, name, author, self.machine, now=self.now)
        return "sent {0} to everybody ({1} zipped)".format(
            ready["name"], sharerecords.size_text(ready["zip"]))

    # ---- prefs ------------------------------------------------------------

    def _remember_target(self):
        if self.target is not None:
            prefs.put(self.prefs_path, "target", self.target.package)

    def _remember_author(self, author):
        prefs.put(self.prefs_path, "author", author)
