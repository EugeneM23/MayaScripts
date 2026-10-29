# Montage slot import — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (this plan is executed
> inline in the session that wrote it). Steps use checkbox (`- [ ]`) syntax.

**Goal:** Animation Setup's Unreal source lists the project's AnimMontages, and importing one
brings the chosen slot's whole track into Maya as one take, exactly as the engine plays it —
every segment's slice at its own play rate, in order.

**Architecture:** The editor cannot export a montage (its FBX exporter takes an `AnimSequence`
only) and this build exposes no `AnimSequence` controller to Python, so the composite is assembled
in Maya: the editor answers the montage's PLAN (slots, segments, slices, rates) and exports the
slot's distinct source clips to FBX; Maya imports the first clip into the target namespace, reads
the others in scratch namespaces, and rewrites the target's curves by sampling each frame's span.
The montage road is known in exactly two places — `window._export_from_editor` and
`rigimport.import_source` — so the button, the double click, the drag, the square and Auto all
take it with no road of their own.

**Tech stack:** Maya 2027 (`maya.cmds`, `maya.api.OpenMayaAnim`), Epic's Python Remote Execution,
stdlib. Spec: `docs/superpowers/specs/2026-10-29-montage-slot-import-design.md`.

## Global constraints

- `records.py`, `uescripts.py` and `montage.py`'s pure half stay **stdlib only** (subprocess tests
  pin the first two already; a new one pins `montage`).
- Every editor script interpolates its parameters with `json.dumps` and wraps its body in
  try/except/finally writing the reply file (`uescripts`'s own rules).
- A refusal happens **before anything is exported or imported** and leaves the scene untouched.
- Keys are written through `MFnAnimCurve.addKeys` — times in UI units, angles in **radians**
  (trap 224); `cmds.setKeyframe` per key is 16x slower and not used here.
- The composed rotate series is made continuous (a step over 180° between consecutive frames is a
  wrap — trap 108).
- The take's length is the **slot track's** end, never the montage's.
- Tests: `& 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' -m unittest discover -s tests -t . -v`
  from the repo root.
- No file in the plugin may name the animator's own paths; nothing is written into the Unreal
  project.

---

### Task 1: The record knows a montage

**Files:**
- Modify: `SkeldarAnim/maya_uebridge/records.py`
- Test: `tests/test_uebridge_montage_records.py` (create)

**Interfaces:**
- Produces: `AnimRecord` with a trailing `kind` field (default `""`);
  `records.is_montage(record) -> bool`; `records.with_slot(record, slot) -> AnimRecord`
  (`name` becomes `"<montage>_<slot>"`, `clip` becomes the slot, `kind` stays `"montage"`);
  `records.montage_slot(record) -> str`.
  `parse_payload` reads `entry["kind"]`; `format_row` shows `montage` where a frame count would
  be, and `<name> · <slot>` for a slotted record.

- [ ] **Step 1: Write the failing tests**

```python
class MontageRecords(unittest.TestCase):
    def test_a_record_defaults_to_no_kind(self):
        rec = records.AnimRecord("A", "/Game/A", "SK", 10, 1.0, 30.0)
        self.assertEqual(rec.kind, "")
        self.assertFalse(records.is_montage(rec))

    def test_parse_payload_reads_the_kind(self):
        out = records.parse_payload({"assets": [
            {"name": "AM_X", "package": "/Game/AM_X", "kind": "montage"}]})
        self.assertTrue(records.is_montage(out[0]))

    def test_with_slot_names_the_montage_and_the_slot(self):
        rec = records.AnimRecord("AM_X", "/Game/AM_X", "SK", None, None, None,
                                 kind="montage")
        slotted = records.with_slot(rec, "1P")
        self.assertEqual(slotted.name, "AM_X_1P")
        self.assertEqual(records.montage_slot(slotted), "1P")
        self.assertEqual(slotted.package, rec.package)

    def test_a_montage_row_says_montage_in_place_of_frames(self):
        rec = records.AnimRecord("AM_X", "/Game/Combat/AM_X", "SK", None, None,
                                 None, kind="montage")
        self.assertIn("montage", records.format_row(rec))
```

- [ ] **Step 2: Run them, see them fail** (`kind` unknown).
- [ ] **Step 3: Implement** — add `kind` to the namedtuple's fields and defaults
      (`defaults=("unreal", "", "", "", "")`), the three helpers, the `parse_payload` field and
      the `format_row` branch.
- [ ] **Step 4: Run the whole bridge suite** (`tests/test_uebridge_*`): every positional
      constructor and every older record must still mean what it meant.
- [ ] **Step 5: Commit** `feat(uebridge): a record knows it is a montage`.

---

### Task 2: The editor's three scripts

**Files:**
- Modify: `SkeldarAnim/maya_uebridge/uescripts.py`
- Test: `tests/test_uebridge_montage_scripts.py` (create)

**Interfaces:**
- Produces:
  - `montage_list_script(out_path, package_path="/Game") -> str` — reply
    `{"ok", "error", "scanning", "project", "content_dir", "assets": [{"name", "package",
    "skeleton", "kind": "montage"}]}`, registry only, loads nothing.
  - `montage_plan_script(out_path, packages) -> str` — reply
    `{"ok", "error", "montages": {package: {"name", "length", "skeleton", "sections": [...],
    "slots": [{"slot": str, "segments": [{"clip", "clip_name", "start_pos", "anim_start_time",
    "anim_end_time", "anim_play_rate", "looping_count", "additive", "clip_length",
    "clip_frames"}]}]}}}`.
  - `montage_export_script(out_path, packages, folder, preview_mesh=False) -> str` — reply
    `{"ok", "error", "clips": {package: {"path", "fps", "frames", "length"}}, "failed":
    {package: reason}}`; one round trip for every clip of a slot.

- [ ] **Step 1: Write the failing tests** — each script's text compiles (`compile(src, "<s>",
      "exec")`), carries the out path and the packages as JSON literals (a Windows backslash is
      not an escape), ends in the marker, and `montage_export_script` writes one FBX per package
      under the folder.
- [ ] **Step 2: Run them, see them fail.**
- [ ] **Step 3: Implement** the three bodies, following `_LIST_HEAD` / `_EXPORT_HEAD`: an
      `attempt()` helper, `looping_count` read as **`looping_count`** (the property's real name —
      `loop_count` answers None), `additive` read off the referenced clip's
      `additive_anim_type`, and the reply tail shared.
- [ ] **Step 4: Run the tests and the stdlib-only subprocess test for `uescripts`.**
- [ ] **Step 5: Commit** `feat(uebridge): editor scripts for montages - list, plan, export`.

---

### Task 3: The plan model (pure)

**Files:**
- Create: `SkeldarAnim/maya_uebridge/montage.py` (pure half only in this task)
- Test: `tests/test_uebridge_montage_plan.py` (create)

**Interfaces:**
- Produces:
  - `REF_PREFIX = "montage:"`, `is_ref(text)`, `ref_of(plan_path)`, `plan_file_of(ref)`
  - `Span = namedtuple("Span", "clip t0 t1 src rate")` — `src` is the source time at `t0`,
    `rate` signed; the span covers `[t0, t1)`.
  - `slots_of(payload, package) -> [str]` (the montage's own order)
  - `segments_of(payload, package, slot) -> [dict]`
  - `plan_for(payload, package, slot) -> Plan(montage, slot, spans, end, clips)` —
    `looping_count` N expands into N spans; `end` is the last span's `t1`; `clips` the distinct
    clip packages in first use order.
  - `samples(plan, fps) -> [(frame, clip, source_time)]` — frames `0..floor(end * fps + 1e-6)`,
    each frame's span found by `t = frame / fps`, the source time clamped into the span's slice.
  - `cuts(plan, fps) -> [float]` — each span's `t0` after the first, in frames, rounded to 0.1.
  - `refusal(payload, package, slot) -> str`
  - `clip_name(montage, slot) -> str`
  - `pick_slot(slots, remembered) -> str`

- [ ] **Step 1: Write the failing tests** over a hand-written payload shaped like the plan
      script's reply, with the measured numbers of `AM_SwordShield_1p_blockreact_mid`:

```python
PAYLOAD = {"montages": {"/Game/AM_X": {"name": "AM_X", "length": 1.4231, "slots": [
    {"slot": "DefaultSlot", "segments": [
        {"clip": "/Game/C3", "start_pos": 0.0, "anim_start_time": 0.0,
         "anim_end_time": 0.27, "anim_play_rate": 1.5, "looping_count": 1},
        {"clip": "/Game/C3", "start_pos": 0.18, "anim_start_time": 0.27,
         "anim_end_time": 0.8666667, "anim_play_rate": 0.8, "looping_count": 1},
        {"clip": "/Game/C3", "start_pos": 0.9258333, "anim_start_time": 0.27,
         "anim_end_time": 0.8666667, "anim_play_rate": 1.2, "looping_count": 1}]},
    {"slot": "1P", "segments": [...]}]}}}
```

- the three spans' `t1` are 0.18, 0.9258, 1.4231 (the rate divides the slice);
- `end` is 1.4231 and `samples(plan, 30)` ends at frame 42 (`floor(1.4231 * 30)`), never past it;
- frame 0 reads `C3` at 0.0; frame 6 (0.2 s) reads span 2 at `0.27 + (0.2 - 0.18) * 0.8`;
- the last frame's source time is clamped to `anim_end_time`;
- a `looping_count` of 3 makes three spans of equal length;
- a negative rate runs the source backwards from `anim_end_time`;
- `cuts(plan, 30)` is `[5.4, 27.8]`;
- `refusal` names a slot the montage lacks, an empty track, an additive clip and a segment with
  no clip package, and answers `""` for the good payload;
- `clip_name("AM_X", "1P") == "AM_X_1P"`;
- `pick_slot(["DefaultSlot", "1P"], "1P") == "1P"` and `pick_slot(["FullBody"], "1P") ==
  "FullBody"`;
- a subprocess test asserts importing `maya_uebridge.montage` pulls in no `maya` module.

- [ ] **Step 2: Run them, see them fail.**
- [ ] **Step 3: Implement** the pure half.
- [ ] **Step 4: Run the tests.**
- [ ] **Step 5: Commit** `feat(uebridge): the montage plan - spans, samples, cuts, refusals`.

---

### Task 4: The composer in Maya

**Files:**
- Modify: `SkeldarAnim/maya_uebridge/montage.py` (the scene half)
- Test: `tests/test_uebridge_montage_compose.py` (create — the pure helpers of this half)

**Interfaces:**
- Produces:
  - `channel_plan(sources, joints) -> {(leaf, attr): ...}` (pure): the union of the channels the
    spans' clips animate.
  - `continuous(values) -> [float]` (pure): whole turns added where a step exceeds 180.
  - `import_clip(ref, namespace, set_timeline=True, clip_fps=None) -> info` — the dict
    `animimport.import_clip` returns, with `start`/`end`/`curves` of the composite and a
    `montage` key `{"name", "slot", "frames", "cuts", "clips", "held"}`.
  - `write_plan(folder, plan, clips, fps) -> path` — the JSON the export step leaves for the
    import step: `{"montage", "slot", "spans", "end", "clips": {package: fbx}, "fps", "name"}`.
  - `read_plan(path) -> dict`

- [ ] **Step 1: Write the failing tests** for `continuous` (a 359 → 1 step becomes 361; a
      genuine 170 step is left alone) and `channel_plan` (a channel only the second clip
      animates is in the plan; `visibility` is not).
- [ ] **Step 2: Run them, see them fail.**
- [ ] **Step 3: Implement** `import_clip`:
      1. `read_plan`; the first span's clip imported into `namespace` through
         `animimport.import_clip(..., merge=False, set_timeline=False)`;
      2. every other distinct clip into `<namespace>_src<N>` the same way;
      3. the target's joints by leaf; per (leaf, attr) of `channel_plan`, per span, the source
         curve read with one `cmds.keyframe(curve, q=True, eval=True, time=[...])` call (a
         channel with no curve read once with `getAttr`), a joint or attribute a clip lacks
         holding the previous sample and named in `held`;
      4. the target's own curves deleted and rewritten with `MFnAnimCurve.addKeys` (rotate series
         through `continuous`, angles in radians);
      5. the scratch namespaces removed (`namespace -removeNamespace -deleteNamespaceContent`,
         unlocking what an import of a `.ma` may have locked — trap 164's family);
      6. the timeline set to `0..frames` when asked;
      7. the info dict.
- [ ] **Step 4: Run the tests.**
- [ ] **Step 5: Commit** `feat(uebridge): compose a montage slot into one take`.

---

### Task 5: The import funnel's branch

**Files:**
- Modify: `SkeldarAnim/maya_uebridge/rigimport.py:354-379`
- Test: `tests/test_uebridge_montage_funnel.py` (create)

**Interfaces:**
- Consumes: `montage.is_ref`, `montage.import_clip`.
- Produces: `rigimport.import_source` sending a `montage:` reference to `montage.import_clip`
  with the namespace it made, before the plain-FBX and the formats branches.

- [ ] **Step 1: Write the failing test** — `import_source("montage:C:/x/plan.json", "AM_X_1P")`
      with `montage.import_clip` and `animimport` faked: the montage importer is called with the
      namespace `records.namespace_for` made, and `animimport.import_clip` is not.
- [ ] **Step 2: Run it, see it fail** (it goes to `formats`).
- [ ] **Step 3: Implement** the branch (a lazy import, as the formats branch is).
- [ ] **Step 4: Run the bridge suite.**
- [ ] **Step 5: Commit** `feat(uebridge): the import funnel takes a montage reference`.

---

### Task 6: The card — the Montages filter and the Slot row

**Files:**
- Modify: `SkeldarAnim/maya_uebridge/window.py`
- Test: `tests/test_uebridge_montage_window.py` (create)

**Interfaces:**
- Produces:
  - `ASSET_KINDS = (("anims", "Animations", note), ("montages", "Montages", note))`,
    `_ASSET_KIND = "ueAnimBridgeAssetKind"`, `asset_kind()`, `set_asset_kind(kind)`,
    `asset_kind_button(kind)`, `_KIND_ROW`, `_SLOT_ROW`, `_SLOT` (the optionMenu),
    `SLOT_VAR = "ueAnimBridgeSlot"`, `montage_slot()`, `set_montage_slot(slot)`,
    `_montage_plan(packages)` (cached in `_STATE["montage_plans"]`), `_fill_slots(record)`,
    `_export_montage(record, mesh)`.
  - `cache_path(kind="anims")` and `cache_payload` carrying `kind`, so Animations and Montages
    each keep their own cached list and switching back costs no round trip.
  - `_refresh_unreal` running `uescripts.montage_list_script` in the Montages kind.
  - `_selected_records()` returning slotted copies (`records.with_slot`) in the Montages kind, so
    the Import words, the clip label, the drag, the square and Auto all name the slot.
  - `_export_from_editor` → `_export_montage` for a montage record: the plan (cached), the slot,
    `montage.refusal` raised as a `UeBridgeError`, the slot's distinct clips exported in one
    round trip, `montage.write_plan`, and `(montage.ref_of(path), fps)` returned.

- [ ] **Step 1: Write the failing tests** on the repo's fake `cmds`
      (`tests/uifakes.FakeUiCmds`, as the other window tests do):
      the kind is remembered and read back; `set_asset_kind` repopulates; the kind row is
      managed off for the Unity and Folder sources; the slot row is managed only in Montages;
      `_fill_slots` fills the dropdown from a plan payload in the montage's own order and keeps
      the remembered slot when the montage has it; `_selected_records` returns `AM_X_1P` in the
      Montages kind; `_export_montage` refuses an additive slot without asking the editor to
      export anything (a fake `uelink`); the Import button's words name the slot.
- [ ] **Step 2: Run them, see them fail.**
- [ ] **Step 3: Implement**, following the card's own idioms: `hubstyle.mark(...)` segments and a
      `label` for the kind row, an `optionMenu` for the slot (a dropdown, not segments — trap
      117), every press through `_run`, the slot dropdown filled in `_on_select` only when the
      kind is Montages and exactly one row is picked.
- [ ] **Step 4: Run the whole suite.**
- [ ] **Step 5: Commit** `feat(uebridge): Animation Setup lists montages and picks a slot`.

---

### Task 7: The verify script

**Files:**
- Create: `docs/superpowers/plans/verify_montage_import.py`

- [ ] **Step 1: Write the standalone phase** (mayapy, no editor): build two fixture skeletons in
      Maya with known curves (a joint chain with `root` carrying a custom float attribute), export
      each as an FBX through the plugin's own exporter, write a plan with three spans across the
      two clips at rates 1.5 / 0.8 / 1.2, run `montage.import_clip`, and gate:
      every frame's every channel against the source clip read at the mapped time (computed in
      the verify from the fixture's own curve definition, not from `montage.samples`);
      the frame count equals `floor(end * fps)`; the scratch namespaces are gone; the custom
      attribute is composed; the cuts are reported; a refusal changes nothing; one `cmds.undo()`.
- [ ] **Step 2: Run it** and fix until every gate passes.
- [ ] **Step 3: Write the live phase** (`--live`): `AM_LongSword_Block_Stun` slots `1P` and
      `DefaultSlot` and `AM_SwordShield_1p_blockreact_mid` slot `1P` imported onto a Manny rig
      through the real roads, with the composed bones compared against the ENGINE's own reading
      of the source clips at the mapped times
      (`unreal.AnimationLibrary.get_bone_pose_for_time`; if this build has no such call, the
      editor samples the clip another way and the gate says which it used).
- [ ] **Step 4: Run the live phase against the open editor.**
- [ ] **Step 5: Commit** `test(uebridge): verify_montage_import - the composite against the engine`.

---

### Task 8: Ship it

- [ ] **Step 1: Run the whole unit suite** (the known `test_chat_deploy.Keys` failure aside).
- [ ] **Step 2: Add `maya_uebridge/montage.py` to nothing** — the package is already a payload
      row, and a new module inside it ships with it; check `tests/test_make_build.py` and the
      payload test still pass.
- [ ] **Step 3: Write the CLAUDE.md section** (what the feature is, the measured numbers, the two
      engine limits, what is not built) and any new trap.
- [ ] **Step 4: Commit and push** — a push to `main` touching `SkeldarAnim/` is a release, so
      the animator gets it through Check update.

## Self-review

- **Spec coverage:** the filter and the slot row (Task 6), the registry-only listing (Tasks 2, 6),
  the plan and the slot's own length (Task 3), the composition and the channel rule (Task 4), the
  funnel (Task 5), the refusals (Tasks 3, 6), the proof (Task 7), the shipping and the notes
  (Task 8). The status line's cuts: `montage.cuts` (Task 3) reported by `import_clip`'s info
  (Task 4) and shown by the window's own status write (Task 6).
- **Placeholders:** none; every signature and every reply shape is written out.
- **Type consistency:** `Span(clip, t0, t1, src, rate)`, `Plan(montage, slot, spans, end, clips)`,
  `samples -> [(frame, clip, source_time)]`, `ref_of(plan_path)` / `plan_file_of(ref)` and
  `records.with_slot` are used by Tasks 4, 5 and 6 under exactly these names.
