# Cascadeur API probe, 2026-10-09

Run inside the animator's Cascadeur (version 0.3.1 script server, Cascadeur's own
licence) through `POST /run`, with `docs/superpowers/plans/probe_cascadeur.py`.
Result file: `skeldar_cascade_probe/probe_result.json` (not in the repo).

| Question | Answer | Used by |
|---|---|---|
| Does `FbxSceneLoader.import_scene` into a new tab work? | Yes. `wrapping.new_scene()` then `import_scene(path)` created the tab and imported the clip. | `cascade_io.import_clip_new_tab` |
| Skeleton roots | `get_scene_objects(only_roots=True)` with NO type filter found `['root']`. `of_type="joint"` and `of_type="bone"` found nothing. | `cascade_io.skeleton_roots` |
| Animation frame count | `get_animation_size()` = 38 for a 37-frame UE clip (inclusive count). | `cascade_io.animation_frames` |
| Scene fps | No getter. The loader has no `fps` attribute; the scene exposes only the current frame. `scene_fps()` returns None and the fps warning is skipped. | `cascade_io.scene_fps` |
| Export bones (`export_joints`) | BLOCKED on this licence. The call returns None, writes no file, and Cascadeur logs "Feature not available. The free and trial versions only support .CASC file format." | `cascade_io.export_skeleton` raises `EXPORT_BLOCKED` when no file appears |
| Absolute `Python.Path` in settings.json, restart needed | Not yet checked: needs the installer run and a Cascadeur restart. | Task 12 |

**Consequence:** the import road works on this Cascadeur. Export to uasset and
Send to Shared cannot produce a file until the animator's Cascadeur licence allows
FBX export. The bridge says so in its status line instead of failing silently.
