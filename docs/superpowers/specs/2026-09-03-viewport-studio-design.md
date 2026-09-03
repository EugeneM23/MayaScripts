# Viewport Studio — a juicy real-time picture, on one press

2026-09-03. The animator's ask, verbatim: «скрипт который по нажатию будет
автоматически настраивать красивый рендер во вьюпорте который будет работать
в реальном времени … студийное освещение, включить тени, амбиент аклюжен,
моушен блур, сделать пол геометрией … всё для красивого отображения сочной
картинки в реальном времени. Сделай скрипт отдельным инструментом.»

Separate tool, so: `SkeldarAnim/maya_vpstudio.py`, single file, `maya.cmds`
only, its own shelf button (**Studio**, the seventh). It is shipped rather
than kept at the repo root because a colleague wants it as much as we do —
`maya_overshoot.py` is the precedent for a single-file tool inside the
plugin folder.

Proof: `docs/superpowers/plans/verify_vpstudio.py` — **green live
2026-09-03, 0 of 85 gates failed** in the animator's two-character scene.
1602 unit tests green, 113 of them this tool's.

## What it does

One press (`setup`) measures the scene and builds:

- **Five lights** under one pivot at the subject's centre: a warm **key**
  spot with a depth-map shadow, a cool **fill** directional, a **rim** spot,
  a **bounce** directional from below-front, and a breath of **ambient**.
- **A floor** — a `polyPlane` with a blinn, twenty subject-radii across,
  receiving shadows and casting none, set to reference display so it stays
  out of a marquee select.
- **The viewport**: smooth-shaded, textured, all lights, shadows on, AO,
  multisample AA, motion blur, bloom, depth-peeled transparency, grid off,
  light icons off, and a dark gradient behind it all.

Then `restore` puts the animator's own viewport back and deletes our nodes.
Measured cost at Good quality on two skinned Mannys: **8.1 ms/frame,
123 fps** (Fast 147, Beauty 87). Real-time was the requirement and there is
room to spare.

## The decisions that carry the design

**It is reversible, and the memory lives on our own group.**
`hardwareRenderingGlobals` is a scene node and the panel flags are the
animator's own, so everything the press is about to overwrite is captured
first and stored as JSON on the `VPStudio` group
(`skeldarVpStudioState`). The state travels with the file, which an
optionVar would not, and a scene that never had the studio has nothing of
ours to mis-restore.

**The capture happens only on the press that finds no rig.** A second press
carries the FIRST press's memory forward. Capturing twice would record our
own studio as the thing to go back to, and Restore would hand the animator
a viewport they never had. This is the single most breakable thing here and
it has both a unit test and a live gate.

**Everything is measured from the subject, nothing is tabulated in
centimetres.** The light table is in *radii* and degrees; `radius` is half
the bounding-box diagonal, the one measure that does not collapse on a flat
subject. The AO radius is 10% of the subject's height — 16 cm of occlusion
radius reads as contact shadow on a 180 cm character and as nothing at all
on a 20 m one. So the same press works on one Manny, on two, and on a prop.

**Our own floor is excluded from that measurement.** Otherwise every press
measures the floor the last press built and the studio walks off to
infinity. Live gate: the floor is the same size after the second press, and
the subject measures identically both times.

**The azimuth comes from the viewing camera, not from the character.**
Three-point lighting is defined against the VIEW. Reading the camera's
heading means no part of this tool has to guess which way a character
faces — and it puts the key light to one side of whatever the animator is
actually looking at. The Rotate dial then spins the whole rig, which is one
attribute on one pivot rather than a recomputed table.

**Spots carry the shadows; the fill and bounce are directional.** A spot's
depth map covers its cone, so the resolution lands on the subject; a
directional with auto-focus spreads it over the whole floor. But a cone
cannot light a 35 m floor evenly without either a huge angle or a black
ring beyond the pool of light — so the two lights whose job is to lift
everything are directional, and neither casts.

**One shadow caster.** One reads as one sun; two make a mess of the floor
and cost a second depth map for it.

**The light icons are hidden by the PANEL, never by hiding the lights.**
`modelEditor -lights false` stops the icons being drawn while the lights go
on lighting. Hiding a light's transform would turn it off instead — an
invisible light lights nothing in Viewport 2.0 (trap 15's cousin).

**Clean view is off by default, and switching it off puts the animator's
own flags back.** Hiding joints and curves is a big part of a beauty
picture, but a press that silently takes the controls away reads as the
tool having broken the viewport — so it is a checkbox, unticked. And when
it is unticked the clutter flags are restored *from the saved state*, not
forced to True: "clean off" means "as the animator had it". The first
version merely omitted them, which left the rig invisible until Restore.
Manipulators are never hidden at all: an animator who cannot see the
manipulator cannot animate.

**Identity by attribute, never by name.** `VPStudio` is found by its
`skeldarVpStudio` marker; the lights are found through a `{name: UUID}`
index on the group (`skeldarVpStudioLights`), so the Brightness and Rotate
dials find the key light again without trusting it to still be called
`VPStudio_key`. Nodes are deleted by UUID, existence re-checked in front of
every delete — the shading group is a set, and Maya deletes a set with its
last member (trap 18).

**The dials retune, they do not rebuild.** A slider is a dial: rebuilding
on every drag would re-measure the scene and re-aim the studio from
wherever the camera has drifted to, so the light being adjusted would move
under the animator's hand.

**The selection is deliberately ignored.** "Light what is selected" is a
trap on this rig: `hand_r` owns the sword mesh, so selecting a hand would
light a 40 cm sword and stand the key two metres from the character it
belongs to — and Manny's own body meshes are not even under his skeleton
(they sit at world level), so no walk from a selected joint reaches them.
The subject is every visible mesh, which is predictable.

## Measured facts, each paid for

1. **`render_settings` returns bare attribute names and `apply_plugs` wants
   plugs — and the mismatch was SILENT.** `cmds.objExists("ssaoEnable")` is
   False, so every single render setting was skipped: the studio built its
   lights and its floor, the picture looked plausible, and there was no
   ambient occlusion, no anti-aliasing, no motion blur and no bloom in it
   at all. Two screenshots were judged by eye in that state before a gate
   caught it. Hence `render_plugs` as its own named function, `_setup`
   counting the writes and naming the shortfall on the status line, and a
   live gate that compares EVERY planned setting against the scene. Trap 48
   again: a silent skip has to be able to fail.
2. **`playblast` renders the background from `background` and ignores the
   gradient entirely.** So the flat colour is set alongside the two
   gradient stops — an animator reviews on playblasts, and a look that
   exists only live is half a look.
3. **A playblast PNG carries alpha, and a transparent background reads as
   white.** Three screenshots were mis-read as "the backdrop is not
   applying" before a JPEG showed the real dark ground. Judge a viewport
   look in a format without an alpha channel.
4. **Viewport 2.0 motion blur does not reach playblast output at all.** A
   cube crossing at 300 cm/frame came out crisp with `motionBlurEnable` on,
   at 8 and at 16 samples, single-frame AND over a 7-frame sequence,
   offscreen and on-screen. It is an interactive-redraw effect: the
   attributes are proven set by gate, and the *visual* effect can only be
   confirmed by a human scrubbing the timeline — the bridge cannot press a
   key or drive an interactive redraw. Unverified visually, and said so.
5. **A Qt `widget.grab()` of a model panel captures the chrome and a blank
   white rectangle** where the GL surface is (Maya 2027, this machine).
   CLAUDE.md note 3's advice is for Qt panels; a viewport is not one.
   `playblast` is the way to capture a viewport.
6. **Bloom's own starting threshold is 0**, which blooms every pixel in the
   frame and turns the picture to fog. 1.0 — only what is brighter than
   white — is what makes it a highlight glow, and it needs
   `floatingPointRTEnable` on to have anything above white to find.
7. **Seven radii of floor put the horizon inside the frame** at a normal
   orbit distance: a bright floor edge with bare background beyond it.
   Twenty is free, because the shadows come from spots.

## Addendum, same day — looks are a dropdown

The animator, straight after using it: «это у нас студийное освещение а
теперь давай сделаем еще присет для уличного. Сделай так чтобы я мог
выбрать присеты из выпадающего списка». So: a **Look** dropdown —
**Studio** and **Outdoor** — beside the Quality one. The two are
orthogonal (a look is the lighting, a quality is the sample counts), which
is why they are two lists and not one.

**A look is a bundle, not a light table.** `LOOKS` carries the lights, the
floor's colour and roughness, the backdrop, the shadow filter size and the
bloom amount, because every one of those reads differently between a dark
stage and a sunny day: outdoors wants a sky behind the subject rather than
a wall, pale sunlit ground rather than a black floor, a *sharper* shadow
(the sun is a small source) and more bloom. A third look is now a row in
that table rather than a branch anywhere.

**Outdoors is not the studio with different numbers — the KINDS change.**
One hard parallel source plus one enormous soft one:

- **`sun`** is a **directional** light and has to be. A spot sun lights a
  visible pool on the ground and reads as a stadium floodlight; the sun
  lights everything at once and its shadows run parallel.
- **`sky`** is the dome, an ambient light three times the studio's, and it
  is what fills the sun's shadows — which is also why they read blue.
- **`skylight`** gives that dome a direction, since the sky is brightest
  overhead, and **`bounce`** is the sunlit ground throwing warm light back
  up. Four lights against the studio's five.

**The sun's shadow map is focused by hand.** This is the one thing the
directional sun costs, and it is measurable: a directional light has no
cone to bound its depth map, and `useDmapAutoFocus` fits the map to the
whole scene — which now includes a floor twenty radii across. Measured
live, auto-focus over a 5575 cm floor at 2048 texels is 2.7 cm per texel
and the sun's shadow comes out mushy. With `useDmapAutoFocus` off and
`dmapWidthFocus` set to 2.6 radii, the same map covers 725 cm at **0.35 cm
per texel** — eight times sharper, which is what a sun should look like.
Spots never ask for it: their map already covers the cone, and the two
levers are different attributes that would fight.

**Picking a look applies it immediately.** A preset picker that needs a
second press is a preset picker nobody believes. Unlike the two dials this
cannot retune — a different look is a different set of lights, a different
floor and a different sky — so the dropdown rebuilds, which is also what
keeps the group's stored look honest.

**But the dropdowns are wired up only after the window is built.** Setting
an `optionMenu`'s value FIRES its `changeCommand`, so restoring the
remembered look while building the panel would rebuild the entire studio
as a side effect of merely opening the window.

**The dials read the look off the GROUP, never off the dropdown.**
`retune` scales each light from its spec's base intensity, so it has to
use the table these very lights were built from: with Outdoor standing and
the dropdown flipped to Studio, reading the dropdown would scale the sun
off the studio key's intensity. It also writes the standing look back into
the group's options rather than the dropdown's, or the *next* retune would
inherit the lie. Live gate: brightness 2.0 with `look="Studio"` passed in
scales the sun to exactly 2 × the sun's own base.

Live: **0 of 101 gates failed** (was 85 before the looks), plus 16 panel
gates. 136 unit tests for this tool.

One more gate lesson, and it is CLAUDE.md note 4 in miniature: the AO
gate asserted a literal `18`, correct for the 181 cm subject the scene
held when it was written. The animator swapped what was in the scene
mid-session, the subject became 257 cm, the tool correctly computed 26 —
and the gate failed on correct code. Expectations are now COMPUTED from
the frame the run actually measured.

## Deliberately not built

A camera rig or framing (`persp` is the animator's), image-based lighting
(Viewport 2.0 has none for standard materials without a renderer), a
per-light UI (the five lights are in the outliner and can be dragged), a
saved look library, and screen-space reflections (not a Viewport 2.0
feature). Depth of field IS available as an unticked checkbox: it focuses
on the subject as measured at press time, so it goes stale as the camera
moves, which is why it is not on by default.
