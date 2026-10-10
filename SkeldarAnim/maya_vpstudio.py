"""
Viewport Studio -- one press for a juicy real-time picture in Viewport 2.0.

A LOOK picked from a dropdown -- **Studio** (three-point on a dark stage),
**Outdoor** (a hard sun under an open sky) or **Soft Studio** (wide warm
light in front, cold behind, on a warm cyclorama) -- with depth-map shadows,
screen-space ambient occlusion, anti-aliasing, motion blur, a floor to
catch the shadow, and the right thing behind it. Everything Viewport 2.0
can do at playback speed and nothing that needs a renderer -- there is no
Arnold in the loop.

A look is a bundle rather than a light table (`LOOKS`): the lights, the
floor's colour, the backdrop, how sharp the shadow is and how much bloom.
Anything that reads differently between a stage and a sunny day lives
there, so a third look is a row rather than a branch.

    import sys; sys.path.append(r"C:/!!!Work/MayaScripts/SkeldarAnim")
    import maya_vpstudio; maya_vpstudio.show_window()

Two things hold the whole design together:

* **It is reversible.** `hardwareRenderingGlobals` is a scene node and the
  panel flags are the animator's own -- so the state we are about to
  overwrite is captured and stored ON OUR OWN GROUP as JSON, and Restore
  puts it back. The capture happens only when no rig of ours exists yet:
  a second press must carry the FIRST press's memory forward, or Restore
  would hand back our studio settings as if they were the animator's.
* **It measures the scene.** Light distances, spot cones, the AO radius
  and the floor size all come from the subject's bounding box, so the
  same press works on one Manny, on two, and on a prop. The rig's own
  floor is excluded from that measurement -- without it every press
  measures the floor it made last time and the studio walks off to
  infinity.

Design: docs/superpowers/specs/2026-09-03-viewport-studio-design.md
"""

import collections
import json
import math

import maya.cmds as cmds

import maya_hubcopy as hubcopy
import maya_hubstyle as hubstyle



VERSION = "1"

GROUP = "VPStudio"
PIVOT = "VPStudio_lights"
FLOOR = "VPStudio_floor"
SHADER = "VPStudio_floorMat"

#  Identity by ATTRIBUTE, never by name: Maya uniquifies `VPStudio` to
#  `VPStudio1` the moment a second one could exist, and a rig found by name
#  is a rig that silently belongs to somebody else.
MARKER = "skeldarVpStudio"
STATE_ATTR = "skeldarVpStudioState"
NODES_ATTR = "skeldarVpStudioNodes"
OPTIONS_ATTR = "skeldarVpStudioOptions"
#  {spec name: UUID} -- the light INDEX, so the dials find the key light
#  again without trusting `VPStudio_key` to still be called that.
LIGHTS_ATTR = "skeldarVpStudioLights"
PIVOT_ATTR = "skeldarVpStudioPivot"


# ---------------------------------------------------------------------------
#  Options -- pure
# ---------------------------------------------------------------------------

DEFAULTS = collections.OrderedDict((
    ("look", "Studio"),
    ("quality", "Good"),
    ("floor", True),
    ("shadows", True),
    ("ao", True),
    ("motion_blur", True),
    ("anti_alias", True),
    ("bloom", True),
    ("fog", False),
    ("dof", False),
    ("clean", False),
    ("backdrop", True),
    ("brightness", 1.0),
    ("rotate", 0.0),
))


def merged_options(options=None):
    """The defaults with the caller's overrides on top, unknown keys out.

    The window, the hotkey and a verify script all call in with partial
    dicts; a typo must not silently become an option nobody reads.
    """
    merged = collections.OrderedDict(DEFAULTS)
    for key, value in (options or {}).items():
        if key in merged:
            merged[key] = value
    return merged


#  Sample counts and shadow-map sizes. Everything expensive in Viewport 2.0
#  is a count, so one dial moves them together. `Good` is the default and is
#  what the numbers below were tuned against; `Beauty` is for looking, not
#  for animating.
QUALITY = collections.OrderedDict((
    ("Fast", {"samples": 4, "ao_samples": 8, "ao_filter": 8,
              "blur_samples": 4, "dmap": 1024, "transparency": 1}),
    ("Good", {"samples": 8, "ao_samples": 16, "ao_filter": 16,
              "blur_samples": 8, "dmap": 2048, "transparency": 3}),
    ("Beauty", {"samples": 16, "ao_samples": 32, "ao_filter": 24,
                "blur_samples": 16, "dmap": 4096, "transparency": 3}),
))

QUALITY_ORDER = tuple(QUALITY)


def quality_of(name):
    """The named preset, or `Good` for anything we do not know."""
    return dict(QUALITY.get(name, QUALITY["Good"]))


# ---------------------------------------------------------------------------
#  The light rig -- pure data
# ---------------------------------------------------------------------------

#  A three-point studio plus a floor bounce and a breath of ambient, laid
#  out in SUBJECT RADII and degrees rather than centimetres, so the same
#  table serves a 40 cm prop and a 4 m character.
#
#  `azimuth` is measured from the viewing camera's own heading (see
#  `studio_azimuth`), so the key lands to one side of whatever the animator
#  is looking at instead of relying on a guess about which way the
#  character faces. The whole rig hangs under one pivot, so the Rotate dial
#  spins the studio without touching the table.
#
#  Spots carry the shadows: a spot's depth map covers its cone, so the
#  resolution lands on the subject. The fill and bounce are DIRECTIONAL --
#  they have to reach the far corners of the floor evenly, which a cone
#  cannot do without either a huge angle or a black floor beyond the pool
#  of light.
LightSpec = collections.namedtuple(
    "LightSpec",
    "name kind azimuth elevation distance intensity colour shadow "
    "specular cover")

STUDIO_LIGHTS = (
    LightSpec("key", "spot", 38.0, 30.0, 2.6, 1.30,
              (1.00, 0.96, 0.90), True, True, 1.7),
    LightSpec("fill", "directional", -62.0, 14.0, 3.0, 0.32,
              (0.80, 0.87, 1.00), False, False, 0.0),
    LightSpec("rim", "spot", 168.0, 42.0, 2.8, 1.05,
              (0.93, 0.96, 1.00), False, True, 1.5),
    LightSpec("bounce", "directional", -20.0, -18.0, 2.2, 0.14,
              (0.72, 0.76, 0.86), False, False, 0.0),
    LightSpec("ambient", "ambient", 0.0, 70.0, 3.0, 0.10,
              (0.62, 0.68, 0.80), False, False, 0.0),
)

#  Outdoors is not "the studio with different numbers": it is one hard
#  parallel source plus an enormous soft one, and that changes the KIND of
#  every light in the table.
#
#  The sun is DIRECTIONAL and has to be. A spot sun lights a pool on the
#  ground and reads as a stadium floodlight; the sun lights everything at
#  once and its shadows run parallel. The price is that a directional's
#  depth map covers whatever it is focused on rather than a cone -- see
#  `light_plan`, which focuses it on the subject by hand.
#
#  `sky` is the dome: outdoors the open sky is a light source the size of
#  the sky, so it is much stronger than the studio's breath of ambient and
#  it is what fills the sun's shadows (and why they read blue). `skylight`
#  gives that dome a direction, since the sky is brightest overhead, and
#  `bounce` is the sunlit ground throwing warm light back up.
OUTDOOR_LIGHTS = (
    LightSpec("sun", "directional", 42.0, 46.0, 3.0, 1.55,
              (1.00, 0.95, 0.86), True, True, 0.0),
    LightSpec("sky", "ambient", 0.0, 70.0, 3.0, 0.30,
              (0.55, 0.68, 0.92), False, False, 0.0),
    LightSpec("skylight", "directional", -70.0, 66.0, 3.0, 0.30,
              (0.70, 0.81, 1.00), False, False, 0.0),
    LightSpec("bounce", "directional", -30.0, -20.0, 2.2, 0.20,
              (0.86, 0.78, 0.62), False, False, 0.0),
)

#  Soft Studio (2026-10-01, «свет будет распределен в 3 раза более широким
#  пятном ... спереди теплый свет сзади холодный»): Studio's three points
#  opened up and split by temperature.
#
#  "Three times wider" is the POOL on the subject. `cover` is a cone's
#  half-width in radii at the light's distance, so Studio's key 1.7 and rim
#  1.5 become 5.1 and 4.5 here, at the same distances -- tan(half) is then
#  exactly three times Studio's (126 degrees for the key against 66). The
#  look's `spot` softness widens the falloff with it (see LOOKS).
#
#  Warm in front, cold behind: the key, fill and bounce all face the
#  camera's side; two cold back lights stand behind on either side, the
#  rim high and the kicker low, so the silhouette is edged in blue against
#  the warm paper. Six lights, inside the eight Viewport 2.0 is allowed.
#
#  The back lights outshine the key on purpose, and the fill is low: at
#  Studio-like strengths (rim 1.25, kicker 0.75, fill 0.40) the warm front
#  flooded the edges and nothing read cold -- judged on playblasts of a
#  textured Manny, 2026-10-01. They cool the floor around the subject to a
#  pale neutral; the wall, facing away from them, stays warm. (Light
#  linking them off the paper was tried: Viewport 2.0 then dropped the rim
#  from the character as well.)
SOFT_LIGHTS = (
    LightSpec("key", "spot", 35.0, 30.0, 2.6, 1.25,
              (1.00, 0.84, 0.64), True, True, 5.1),
    LightSpec("fill", "directional", -55.0, 12.0, 2.9, 0.28,
              (1.00, 0.88, 0.74), False, False, 0.0),
    LightSpec("rim", "spot", 160.0, 38.0, 2.8, 2.60,
              (0.50, 0.68, 1.00), False, True, 4.5),
    LightSpec("kicker", "spot", -150.0, 22.0, 2.8, 1.70,
              (0.55, 0.72, 1.00), False, True, 4.5),
    LightSpec("bounce", "directional", -20.0, -18.0, 2.2, 0.14,
              (0.95, 0.80, 0.66), False, False, 0.0),
    LightSpec("ambient", "ambient", 0.0, 70.0, 3.0, 0.10,
              (0.74, 0.71, 0.70), False, False, 0.0),
)

#  A LOOK is a bundle, not a light table. Outdoors also means a sky behind
#  the subject rather than a dark wall, pale ground rather than a black
#  studio floor, a sharper shadow (the sun is a small source) and more
#  bloom (a sunny day blows out). Anything that reads differently between
#  the two belongs here, so a third look is a row rather than a branch.
#
#  `spot` is how a spot's light falls off across its cone (Maya weighs it
#  by cos(angle)^dropoff, and the penumbra softens the edge), `fog` the
#  haze's colour, `dmap_scale` how many times the quality's shadow map the
#  shadow caster gets, and the floor's `kind` whether the shadow catcher is
#  a plane or the cyclorama.
STUDIO_SPOT = {"penumbra": 14.0, "dropoff": 6.0}
STUDIO_FOG = (0.09, 0.10, 0.12)

LOOKS = collections.OrderedDict((
    ("Studio", {
        "lights": STUDIO_LIGHTS,
        "floor": {"kind": "plane",
                  "colour": (0.30, 0.31, 0.34),
                  "specular": (0.045, 0.045, 0.05),
                  "eccentricity": 0.42, "roll_off": 0.55},
        "backdrop": {"top": (0.150, 0.163, 0.180),
                     "bottom": (0.035, 0.037, 0.042),
                     "flat": (0.078, 0.084, 0.094)},
        "shadow_filter": 4,
        "bloom": 0.22,
        "spot": STUDIO_SPOT,
        "fog": STUDIO_FOG,
        "dmap_scale": 1,
    }),
    ("Outdoor", {
        "lights": OUTDOOR_LIGHTS,
        "floor": {"kind": "plane",
                  "colour": (0.40, 0.39, 0.36),
                  "specular": (0.030, 0.030, 0.030),
                  "eccentricity": 0.60, "roll_off": 0.35},
        "backdrop": {"top": (0.26, 0.42, 0.70),
                     "bottom": (0.60, 0.68, 0.76),
                     "flat": (0.40, 0.52, 0.68)},
        "shadow_filter": 2,
        "bloom": 0.30,
        "spot": STUDIO_SPOT,
        "fog": STUDIO_FOG,
        "dmap_scale": 1,
    }),
    #  The wide cones need a wide falloff: at Studio's dropoff of 6 a
    #  126-degree cone is dark past 40 degrees and the pool ends at Studio's
    #  size. 1.3 keeps the wide pool's edge as bright, relative to its
    #  centre, as Studio's own edge (cos 63^1.3 = 0.36 against cos 33^6 =
    #  0.34). The same wide cone spreads its depth map three times as thin,
    #  hence twice the map and a softer filter -- a soft look anyway.
    ("Soft Studio", {
        "lights": SOFT_LIGHTS,
        "floor": {"kind": "cyclorama",
                  "colour": (0.62, 0.47, 0.36),
                  "specular": (0.020, 0.020, 0.020),
                  "eccentricity": 0.60, "roll_off": 0.30},
        "backdrop": {"top": (0.30, 0.22, 0.17),
                     "bottom": (0.13, 0.09, 0.07),
                     "flat": (0.21, 0.15, 0.12)},
        "shadow_filter": 6,
        "bloom": 0.20,
        "spot": {"penumbra": 20.0, "dropoff": 1.3},
        "fog": (0.30, 0.23, 0.18),
        "dmap_scale": 2,
    }),
))

#  The biggest shadow map a look's `dmap_scale` may ask for: Beauty's own.
MAX_DMAP = 4096

LOOK_ORDER = tuple(LOOKS)


def look_of(name):
    """The named look, or Studio for anything we do not know."""
    return LOOKS.get(name, LOOKS["Studio"])


def lights_of(name):
    """The light table of the named look."""
    return look_of(name)["lights"]


def light_names(name):
    return tuple(spec.name for spec in lights_of(name))


def bbox_union(boxes):
    """One box around them all, or None when there is nothing to enclose."""
    boxes = [b for b in boxes if b]
    if not boxes:
        return None
    lo = [min(b[i] for b in boxes) for i in range(3)]
    hi = [max(b[i + 3] for b in boxes) for i in range(3)]
    return tuple(lo + hi)


#  A scene with nothing in it still gets a studio: a standing human is the
#  only sensible guess, and guessing beats refusing when the animator is
#  about to import a character into the light they just set up.
EMPTY_BBOX = (-40.0, 0.0, -40.0, 40.0, 180.0, 40.0)


def subject_frame(bbox):
    """Centre, radius, height and floor height of what we are lighting.

    `radius` is half the box diagonal: it is the one measure that does not
    collapse on a flat subject (a floor plane has no height, a lying prop
    has no depth) and every distance in the light table is a multiple of
    it.
    """
    if not bbox:
        bbox = EMPTY_BBOX
    size = [max(bbox[i + 3] - bbox[i], 0.0) for i in range(3)]
    centre = tuple(bbox[i] + size[i] / 2.0 for i in range(3))
    radius = 0.5 * math.sqrt(sum(s * s for s in size))
    #  A single point in space is a legal subject; give it a body so the
    #  lights do not all land inside it.
    radius = max(radius, 1.0)
    return {"centre": centre, "radius": radius, "height": max(size[1], 1.0),
            "floor_y": bbox[1], "size": tuple(size)}


def spherical(centre, distance, azimuth, elevation):
    """A point at `distance` from `centre`, azimuth 0 looking down +Z."""
    az = math.radians(azimuth)
    el = math.radians(elevation)
    flat = distance * math.cos(el)
    return (centre[0] + flat * math.sin(az),
            centre[1] + distance * math.sin(el),
            centre[2] + flat * math.cos(az))


def studio_azimuth(camera_pos, centre):
    """Where the viewer stands, in the light table's own azimuth.

    Three-point lighting is defined against the VIEW, not against the
    subject -- so the rig is built relative to the camera that is looking
    at it, and no part of this tool has to know which way a character
    faces. Straight overhead (or no camera at all) falls back to 0.
    """
    if not camera_pos:
        return 0.0
    dx = camera_pos[0] - centre[0]
    dz = camera_pos[2] - centre[2]
    if abs(dx) < 1e-6 and abs(dz) < 1e-6:
        return 0.0
    return math.degrees(math.atan2(dx, dz))


def cone_angle(radius, distance, cover=1.7):
    """A spot cone wide enough to hold the subject, and no wider.

    Wider is not safer: the depth map spreads over the cone, so every
    degree past the subject is shadow resolution thrown away.
    """
    if distance <= 1e-6:
        return 120.0
    half = math.degrees(math.atan2(radius * cover, distance))
    return max(8.0, min(2.0 * half, 160.0))


def normalise(vector):
    length = math.sqrt(sum(c * c for c in vector))
    if length < 1e-9:
        return (0.0, 0.0, 1.0)
    return tuple(c / length for c in vector)


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def look_at_matrix(position, target, up=(0.0, 1.0, 0.0)):
    """A Maya row-vector 4x4, as 16 floats, aiming a light at `target`.

    Every Maya light shines down its own -Z, so the third row is the
    NEGATIVE of the direction we want lit. Handing Maya a matrix and
    letting `xform` decompose it is deliberate: euler extraction by hand
    is where this kind of code goes wrong, and Maya already owns the
    rotate order.
    """
    forward = normalise((target[0] - position[0],
                         target[1] - position[1],
                         target[2] - position[2]))
    z_axis = tuple(-c for c in forward)
    #  Straight down (or straight up) leaves the up vector parallel to the
    #  aim and the cross product undefined; +Z is the conventional escape.
    if abs(sum(a * b for a, b in zip(z_axis, up))) > 0.9995:
        up = (0.0, 0.0, 1.0)
    x_axis = normalise(cross(up, z_axis))
    y_axis = normalise(cross(z_axis, x_axis))
    return [x_axis[0], x_axis[1], x_axis[2], 0.0,
            y_axis[0], y_axis[1], y_axis[2], 0.0,
            z_axis[0], z_axis[1], z_axis[2], 0.0,
            position[0], position[1], position[2], 1.0]


def light_plan(frame, azimuth, options):
    """The whole rig as data: one dict per light, ready to build.

    Positions are LOCAL to the pivot group, which stands at the subject
    centre -- that is what makes the Rotate dial one attribute on one node
    instead of a recomputed table.
    """
    options = merged_options(options)
    quality = quality_of(options["quality"])
    look = look_of(options["look"])
    centre = frame["centre"]
    radius = frame["radius"]
    brightness = max(0.0, float(options["brightness"]))
    plan = []
    for spec in look["lights"]:
        distance = spec.distance * radius
        world = spherical(centre, distance, azimuth + spec.azimuth,
                          spec.elevation)
        local = spherical((0.0, 0.0, 0.0), distance,
                          azimuth + spec.azimuth, spec.elevation)
        entry = {
            "name": "{0}_{1}".format(GROUP, spec.name),
            "kind": spec.kind,
            "position": world,
            "matrix": look_at_matrix(local, (0.0, 0.0, 0.0)),
            "intensity": spec.intensity * brightness,
            "colour": spec.colour,
            "specular": spec.specular,
            "shadow": bool(spec.shadow and options["shadows"]),
            "dmap": min(MAX_DMAP, int(quality["dmap"] * look["dmap_scale"])),
            "filter": look["shadow_filter"],
        }
        if spec.kind == "spot":
            entry["cone"] = cone_angle(radius, distance, spec.cover)
            entry["penumbra"] = float(look["spot"]["penumbra"])
            entry["dropoff"] = float(look["spot"]["dropoff"])
        elif spec.shadow:
            #  A shadow-casting DIRECTIONAL light (the sun) has no cone to
            #  bound its depth map, and auto-focus fits it to the whole
            #  scene -- which now includes a floor twenty radii across, so
            #  a 2048 map lands about 1.7 cm per texel and the sun's
            #  shadow comes out mushy. Focused on the subject by hand it
            #  is ten times sharper, which is what a sun should look like.
            entry["width_focus"] = 2.6 * radius
        plan.append(entry)
    return plan


#  Twenty radii across. Seven was the first guess and the horizon sat
#  inside the frame at a normal orbit distance -- a bright floor edge with
#  bare background beyond it, which is the one thing a studio floor must
#  never show. It costs nothing: the shadows come from SPOT lights, whose
#  depth map covers the cone rather than the scene, so a bigger floor
#  takes no shadow resolution away (a directional light with auto-focus
#  would have paid for every metre).
FLOOR_RADII = 20.0


def floor_plan(frame, options=None):
    """Size and place the shadow catcher."""
    options = merged_options(options)
    surface = look_of(options["look"])["floor"]
    radius = frame["radius"]
    centre = frame["centre"]
    size = max(400.0, min(FLOOR_RADII * radius, 100000.0))
    return {"name": "{0}_{1}".format(GROUP, "floor"),
            "size": size,
            #  A hair below the lowest point: coplanar with the feet is
            #  where depth-map shadows fight the ground and flicker.
            "position": (centre[0],
                         frame["floor_y"] - max(0.02, 0.0005 * radius),
                         centre[2]),
            "colour": surface["colour"],
            "specular": surface["specular"],
            "eccentricity": surface["eccentricity"],
            "roll_off": surface["roll_off"]}


#  The cyclorama -- a photo studio's paper sweep: the floor curving up into
#  a wall behind the subject, with no corner and no horizon to read. Its
#  profile is in subject RADII in its own frame, +Z toward the camera and
#  the wall at -Z, across +-CYC_HALF_WIDTH in X.
#
#  The cove starts further back than any light of the look reaches (the
#  furthest, the kicker, stands 2.6 radii out), and the Rotate dial can
#  turn any light straight back -- so no light ever ends up behind the
#  paper. A test pins it against the light table.
CYC_FRONT = 12.0          # the floor runs this far toward the camera
CYC_COVE_START = 3.0      # where the floor starts to curve up, behind
CYC_COVE_RADIUS = 1.5
CYC_WALL = CYC_COVE_START + CYC_COVE_RADIUS
CYC_TOP = 8.0             # the wall's top above the floor
CYC_HALF_WIDTH = 12.0
CYC_COVE_SEGMENTS = 16


def cyclorama_profile(radius):
    """[(z, y), ...] from the front edge back through the cove to the top.

    The front edge, the cove's 17 points (its first is where the flat floor
    ends, its last where the wall starts) and the wall's top.
    """
    r = float(radius)
    start = CYC_COVE_START * r
    bend = CYC_COVE_RADIUS * r
    points = [(CYC_FRONT * r, 0.0)]
    for i in range(CYC_COVE_SEGMENTS + 1):
        t = 0.5 * math.pi * i / CYC_COVE_SEGMENTS
        points.append((-start - bend * math.sin(t), bend - bend * math.cos(t)))
    points.append((-CYC_WALL * r, CYC_TOP * r))
    return points


def cyclorama_plan(frame, azimuth, options=None):
    """The sweep as data, or None for a look whose floor is a plane.

    It stands where the floor would (under the subject, a hair below the
    feet) and is turned to the CAMERA's heading at the press, so the wall is
    behind the subject as the animator sees it. It hangs under our group,
    not under the light pivot: the Rotate dial turns the lights and leaves
    the paper behind the subject.
    """
    options = merged_options(options)
    surface = look_of(options["look"])["floor"]
    if surface.get("kind") != "cyclorama":
        return None
    floor = floor_plan(frame, options)
    radius = frame["radius"]
    return {"name": "{0}_{1}".format(GROUP, "cyclorama"),
            "position": floor["position"],
            "rotate_y": float(azimuth),
            "width": 2.0 * CYC_HALF_WIDTH * radius,
            "profile": cyclorama_profile(radius),
            "colour": surface["colour"],
            "specular": surface["specular"],
            "eccentricity": surface["eccentricity"],
            "roll_off": surface["roll_off"]}


def cyclorama_targets(starts, profile, half_width):
    """Where each vertex of a flat 1 x N polyPlane goes on the profile.

    Matched by the vertex's own STARTING position, never by its index: the
    rows are the distinct starting z values, front (+z) first, and a vertex
    keeps the side of its starting x. A plane whose row count is not the
    profile's is refused rather than bent into something else.
    """
    rows = sorted({round(s[2], 6) for s in starts}, reverse=True)
    if len(rows) != len(profile):
        raise ValueError("a plane of %d rows for a profile of %d points"
                         % (len(rows), len(profile)))
    row_of = {z: i for i, z in enumerate(rows)}
    targets = []
    for x, _y, z in starts:
        pz, py = profile[row_of[round(z, 6)]]
        targets.append((half_width if x > 0 else -half_width, py, pz))
    return targets


# ---------------------------------------------------------------------------
#  Viewport settings -- pure
# ---------------------------------------------------------------------------

RENDER_NODE = "hardwareRenderingGlobals"

#  Everything we write into `hardwareRenderingGlobals`. The list is also
#  what gets captured for Restore, so an attribute added here is remembered
#  for free -- and one added only to the writer would be a setting the
#  animator never gets back.
RENDER_ATTRS = (
    "multiSampleEnable", "multiSampleCount", "lineAAEnable",
    "ssaoEnable", "ssaoAmount", "ssaoRadius", "ssaoFilterRadius",
    "ssaoSamples",
    "motionBlurEnable", "motionBlurSampleCount",
    "motionBlurShutterOpenFraction",
    "bloomEnable", "bloomThreshold", "bloomAmount", "bloomFilterRadius",
    "hwFogEnable", "hwFogStart", "hwFogEnd", "hwFogDensity", "hwFogFalloff",
    "hwFogColorR", "hwFogColorG", "hwFogColorB", "hwFogAlpha",
    "transparencyAlgorithm", "transparencyQuality",
    "maxHardwareLights", "useMaximumHardwareLights",
    "floatingPointRTEnable",
)


def render_settings(frame, options=None):
    """`hardwareRenderingGlobals` as a plain {attr: value} plan.

    The AO radius is the one number that MUST follow the scene's scale:
    16 cm of occlusion radius reads as contact shadow on a 180 cm
    character and as nothing at all on a 20 m one.
    """
    options = merged_options(options)
    quality = quality_of(options["quality"])
    look = look_of(options["look"])
    height = frame["height"]
    radius = frame["radius"]
    ao_radius = int(max(2, min(round(0.10 * height), 200)))
    settings = collections.OrderedDict((
        ("multiSampleEnable", bool(options["anti_alias"])),
        ("multiSampleCount", int(quality["samples"])),
        ("lineAAEnable", bool(options["anti_alias"])),

        ("ssaoEnable", bool(options["ao"])),
        ("ssaoAmount", 1.0),
        ("ssaoRadius", ao_radius),
        ("ssaoFilterRadius", int(quality["ao_filter"])),
        ("ssaoSamples", int(quality["ao_samples"])),

        ("motionBlurEnable", bool(options["motion_blur"])),
        ("motionBlurSampleCount", int(quality["blur_samples"])),
        ("motionBlurShutterOpenFraction", 0.40),

        #  Bloom on a threshold of 1.0 touches only what is brighter than
        #  white -- the specular hits. A threshold of 0 (Maya's own
        #  starting value) blooms every pixel in the frame and turns the
        #  whole picture to fog.
        ("bloomEnable", bool(options["bloom"])),
        ("bloomThreshold", 1.0),
        ("bloomAmount", look["bloom"]),
        ("bloomFilterRadius", 12.0),

        ("hwFogEnable", bool(options["fog"])),
        ("hwFogFalloff", 0),
        ("hwFogDensity", 0.18),
        ("hwFogStart", frame["centre"][2] - radius),
        ("hwFogEnd", frame["centre"][2] + 6.0 * radius),
        ("hwFogColorR", look["fog"][0]), ("hwFogColorG", look["fog"][1]),
        ("hwFogColorB", look["fog"][2]),
        ("hwFogAlpha", 1.0),

        ("transparencyAlgorithm", int(quality["transparency"])),
        ("transparencyQuality", 1.0),
        ("maxHardwareLights", 8),
        ("useMaximumHardwareLights", True),
        #  Bloom reads values above white, which only exist in a float
        #  target.
        ("floatingPointRTEnable", True),
    ))
    return settings


def render_plugs(settings):
    """The plan's bare attribute names turned into real plugs.

    Load-bearing, and it cost a whole live run to find out: `apply_plugs`
    skips a plug that does not exist, and `ssaoEnable` on its own does
    not. Every setting in the plan was therefore dropped SILENTLY -- the
    studio built its lights and its floor, the picture looked plausible,
    and there was no ambient occlusion, no anti-aliasing, no motion blur
    and no bloom in it at all. Hence `_setup` counting the writes as
    well: a silent skip has to be able to fail (trap 48's lesson).
    """
    return collections.OrderedDict(
        ("{0}.{1}".format(RENDER_NODE, attr), value)
        for attr, value in (settings or {}).items())


#  Every panel flag we write, and therefore every panel flag Restore knows
#  how to put back.
PANEL_FLAGS = (
    "displayAppearance", "displayTextures", "displayLights", "shadows",
    "twoSidedLighting", "useDefaultMaterial", "wireframeOnShaded",
    "grid", "lights", "headsUpDisplay", "selectionHiliteDisplay",
    "joints", "locators", "nurbsCurves", "handles", "deformers",
    "dimensions", "ikHandles", "planes", "cameras", "pivots", "textures",
)

#  What Clean view hides. Manipulators are deliberately absent: an animator
#  who cannot see the manipulator cannot animate, and this tool is not a
#  playblast switch.
CLUTTER = ("joints", "locators", "nurbsCurves", "handles", "deformers",
           "dimensions", "ikHandles", "planes", "cameras", "pivots")


def panel_settings(options=None):
    """`modelEditor` flags as a plan.

    `lights` is False and `displayLights` is "all": the icons stop being
    drawn while the lights keep lighting. Hiding a light's TRANSFORM would
    turn it off instead -- an invisible light lights nothing in Viewport
    2.0 (trap 15's cousin).
    """
    options = merged_options(options)
    plan = collections.OrderedDict((
        ("displayAppearance", "smoothShaded"),
        ("displayTextures", True),
        ("displayLights", "all"),
        ("shadows", bool(options["shadows"])),
        ("twoSidedLighting", True),
        ("useDefaultMaterial", False),
        ("wireframeOnShaded", False),
        ("textures", True),
        ("grid", False),
        ("lights", False),
    ))
    if options["clean"]:
        for flag in CLUTTER:
            plan[flag] = False
        plan["headsUpDisplay"] = False
        plan["selectionHiliteDisplay"] = False
    return plan


def backdrop_settings(options=None):
    """What is behind the subject: a dark wall, or a sky.

    The FLAT colour is set alongside the two gradient stops, and that is
    not belt-and-braces: measured 2026-09-03, `playblast` renders the
    background from `background` and ignores the gradient entirely. An
    animator reviews on playblasts, so a look that only exists live is
    half a look.
    """
    options = merged_options(options)
    if not options["backdrop"]:
        return {}
    sky = look_of(options["look"])["backdrop"]
    return {"gradient": True,
            "background": sky["flat"],
            "backgroundTop": sky["top"],
            "backgroundBottom": sky["bottom"]}


def dof_plan(distance, options=None):
    """Camera depth of field, focused on the subject we just measured."""
    options = merged_options(options)
    if not options["dof"]:
        return {}
    return {"depthOfField": True,
            "focusDistance": max(1.0, float(distance)),
            "fStop": 8.0,
            "focusRegionScale": 1.0}


# ---------------------------------------------------------------------------
#  Finding our own rig
# ---------------------------------------------------------------------------

def pick_rig(candidates):
    """One rig out of however many answer the marker. Pure.

    Sorted, so two of them (an imported scene carrying one, say) resolve
    the same way twice rather than following whatever order Maya listed.
    """
    return sorted(candidates)[0] if candidates else None


def find_rig():
    """Our group, by its marker attribute. None when the scene has none."""
    found = cmds.ls("*." + MARKER, objectsOnly=True, long=True,
                    recursive=True) or []
    return pick_rig([n for n in found if cmds.objExists(n)])


def _string_attr(node, attr, default=""):
    plug = "{0}.{1}".format(node, attr)
    if not cmds.objExists(plug):
        return default
    value = cmds.getAttr(plug)
    return default if value is None else value


def _write_string(node, attr, value):
    plug = "{0}.{1}".format(node, attr)
    if not cmds.objExists(plug):
        cmds.addAttr(node, longName=attr, dataType="string")
    cmds.setAttr(plug, value, type="string")


def read_state(rig):
    """The animator's viewport, as it was before the first press."""
    raw = _string_attr(rig, STATE_ATTR)
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except ValueError:
        return {}


def read_options(rig):
    """What the rig in the scene was built with, so the panel can show it."""
    raw = _string_attr(rig, OPTIONS_ATTR)
    if not raw:
        return {}
    try:
        return merged_options(json.loads(raw))
    except ValueError:
        return {}


def recorded_nodes(rig):
    """Our nodes, by UUID -- never by path (trap 16) and never by name."""
    raw = _string_attr(rig, NODES_ATTR)
    return [u for u in raw.split(",") if u.strip()]


def read_index(rig):
    """{light name: UUID}. What the Brightness and Rotate dials aim at."""
    raw = _string_attr(rig, LIGHTS_ATTR)
    if not raw:
        return {}
    try:
        index = json.loads(raw)
    except ValueError:
        return {}
    return index if isinstance(index, dict) else {}


def resolve(uuid):
    """A UUID back to one long path, or None. Paths go stale; UUIDs do not."""
    if not uuid:
        return None
    paths = cmds.ls(uuid, long=True) or []
    return paths[0] if paths else None


# ---------------------------------------------------------------------------
#  Capturing and restoring the animator's viewport
# ---------------------------------------------------------------------------

def model_panels():
    """Every model panel that exists, in Maya's own order."""
    return [p for p in (cmds.getPanel(type="modelPanel") or [])
            if cmds.modelPanel(p, exists=True)]


def active_panel():
    """The panel the animator is looking at, as best as it can be known."""
    try:
        focus = cmds.getPanel(withFocus=True)
    except Exception:                                         # noqa: BLE001
        focus = None
    panels = model_panels()
    if focus in panels:
        return focus
    visible = cmds.getPanel(visiblePanels=True) or []
    for panel in panels:
        if panel in visible:
            return panel
    return panels[0] if panels else None


def panel_camera(panel):
    """The camera SHAPE the panel looks through, or None."""
    if not panel:
        return None
    try:
        camera = cmds.modelEditor(panel, query=True, camera=True)
    except Exception:                                         # noqa: BLE001
        return None
    if not camera or not cmds.objExists(camera):
        return None
    if cmds.nodeType(camera) == "camera":
        return cmds.ls(camera, long=True)[0]
    shapes = cmds.listRelatives(camera, shapes=True, fullPath=True,
                                type="camera") or []
    return shapes[0] if shapes else None


def capture_state(cameras=()):
    """Read back everything this tool is about to write.

    Called once, on the press that finds no rig of ours. A second press
    reads the first one's capture off the group instead -- capturing
    twice would record our own studio as the thing to go back to.
    """
    plugs = collections.OrderedDict()
    for attr in RENDER_ATTRS:
        plug = "hardwareRenderingGlobals." + attr
        if cmds.objExists(plug):
            plugs[plug] = cmds.getAttr(plug)
    for camera in cameras:
        for attr in ("depthOfField", "focusDistance", "fStop",
                     "focusRegionScale"):
            plug = "{0}.{1}".format(camera, attr)
            if cmds.objExists(plug):
                plugs[plug] = cmds.getAttr(plug)

    panels = collections.OrderedDict()
    for panel in model_panels():
        state = collections.OrderedDict()
        for flag in PANEL_FLAGS:
            try:
                state[flag] = cmds.modelEditor(panel, query=True,
                                               **{flag: True})
            except Exception:                                 # noqa: BLE001
                continue
        panels[panel] = state

    backdrop = {}
    try:
        backdrop["gradient"] = cmds.displayPref(query=True,
                                                displayGradient=True)
    except Exception:                                         # noqa: BLE001
        pass
    for name in ("background", "backgroundTop", "backgroundBottom"):
        try:
            backdrop[name] = list(cmds.displayRGBColor(name, query=True))
        except Exception:                                     # noqa: BLE001
            continue
    return {"plugs": plugs, "panels": panels, "backdrop": backdrop,
            "version": VERSION}


def apply_plugs(plugs):
    """Write a {plug: value} map back, skipping what has gone away.

    Every write is on its own: a locked or connected plug is somebody
    else's business and must not take the rest of the restore down with
    it (trap 42's lesson, applied to a teardown).
    """
    written = 0
    for plug, value in (plugs or {}).items():
        if not cmds.objExists(plug):
            continue
        try:
            if isinstance(value, (list, tuple)):
                cmds.setAttr(plug, *value)
            elif isinstance(value, bool):
                cmds.setAttr(plug, int(value))
            elif isinstance(value, str):
                cmds.setAttr(plug, value, type="string")
            else:
                cmds.setAttr(plug, value)
            written += 1
        except Exception:                                     # noqa: BLE001
            continue
    return written


def apply_panels(panels):
    """Write per-panel `modelEditor` flags back."""
    written = 0
    for panel, flags in (panels or {}).items():
        if not cmds.modelPanel(panel, exists=True):
            continue
        for flag, value in flags.items():
            try:
                cmds.modelEditor(panel, edit=True, **{flag: value})
                written += 1
            except Exception:                                 # noqa: BLE001
                continue
    return written


def apply_backdrop(backdrop):
    """Put the background gradient and its colours back."""
    if not backdrop:
        return 0
    written = 0
    for name in ("background", "backgroundTop", "backgroundBottom"):
        colour = backdrop.get(name)
        if not colour:
            continue
        try:
            cmds.displayRGBColor(name, *colour[:3])
            written += 1
        except Exception:                                     # noqa: BLE001
            continue
    if "gradient" in backdrop:
        try:
            cmds.displayPref(displayGradient=bool(backdrop["gradient"]))
            written += 1
        except Exception:                                     # noqa: BLE001
            pass
    return written


# ---------------------------------------------------------------------------
#  Measuring the subject
# ---------------------------------------------------------------------------

def _under(path, root):
    """Is `path` inside `root`? The separator matters (trap 7)."""
    return path == root or path.startswith(root.rstrip("|") + "|")


def subject_bbox(rig=None):
    """The world box of what we are lighting: every visible mesh.

    Deliberately NOT the selection. A one-press studio has to be
    predictable, and on this rig the selection is a trap: `hand_r` owns
    the sword mesh, so "light what is selected" would light a 40 cm sword
    and stand the key light two metres from the character it belongs to.
    Manny's own body meshes are not even under his skeleton (they sit at
    world level), so no walk from a selected joint reaches them.

    OUR OWN nodes are excluded: a press that measured the floor it built
    last time would double the studio's size every time it ran.
    """
    rig = find_rig() if rig is None else rig
    wanted = cmds.ls(type="mesh", long=True, noIntermediate=True) or []
    if rig:
        wanted = [m for m in wanted if not _under(m, rig)]
    wanted = [m for m in wanted
              if not cmds.getAttr(m + ".intermediateObject")]

    boxes = []
    for mesh in wanted:
        try:
            boxes.append(cmds.exactWorldBoundingBox(mesh))
        except Exception:                                     # noqa: BLE001
            continue
    box = bbox_union(boxes)
    if box:
        return box

    #  No geometry at all: a rigged scene mid-build, or a skeleton on its
    #  own. Joints are a subject too.
    joints = cmds.ls(type="joint", long=True) or []
    if rig:
        joints = [j for j in joints if not _under(j, rig)]
    if joints:
        try:
            return cmds.exactWorldBoundingBox(joints)
        except Exception:                                     # noqa: BLE001
            pass
    return None


# ---------------------------------------------------------------------------
#  Building
# ---------------------------------------------------------------------------

class _quiet_autokey(object):
    """autoKey off for the length of a block, and back exactly as found.

    The animator runs autoKey on (trap 14). Nothing here writes to a
    channel that already has keys, but a tool that creates and places
    nodes with autoKey live is one refactor away from keying them.
    """

    def __enter__(self):
        self.was = cmds.autoKeyframe(query=True, state=True)
        cmds.autoKeyframe(state=False)
        return self

    def __exit__(self, *exc):
        cmds.autoKeyframe(state=self.was)
        return False


def _uuid(node):
    found = cmds.ls(node, uuid=True) or []
    return found[0] if found else ""


def _make_light(entry, parent):
    """One light of the plan, placed by matrix and named for the outliner."""
    kind = entry["kind"]
    if kind == "spot":
        shape = cmds.spotLight()
    elif kind == "directional":
        shape = cmds.directionalLight()
    else:
        shape = cmds.ambientLight()
    transform = cmds.listRelatives(shape, parent=True, fullPath=True)[0]
    #  Long paths at every step: `parent` and `rename` both answer with a
    #  short name, and a short name is ambiguous the moment a second rig
    #  or a same-named node exists (trap 16's neighbourhood).
    transform = cmds.ls(cmds.parent(transform, parent)[0], long=True)[0]
    transform = cmds.ls(cmds.rename(transform, entry["name"]),
                        long=True)[0]
    shape = cmds.listRelatives(transform, shapes=True, fullPath=True)[0]

    cmds.setAttr(shape + ".intensity", entry["intensity"])
    cmds.setAttr(shape + ".color", *entry["colour"], type="double3")
    for attr, value in (("emitSpecular", entry["specular"]),
                        ("emitDiffuse", True)):
        plug = shape + "." + attr
        if cmds.objExists(plug):
            cmds.setAttr(plug, int(bool(value)))
    #  Ray-traced shadows OFF on every light, the caster included -- its
    #  shadow is the depth map. Maya's light commands make a light with them
    #  ON and Viewport 2.0 draws them, so until 2026-10-01 every light of
    #  the rig threw a shadow of its own (Studio's streak to the right was
    #  the fill's, measured by switching the lights off one by one).
    if cmds.objExists(shape + ".useRayTraceShadows"):
        cmds.setAttr(shape + ".useRayTraceShadows", 0)
    if kind == "ambient":
        cmds.setAttr(shape + ".ambientShade", 0.45)
    if kind == "spot":
        cmds.setAttr(shape + ".coneAngle", entry["cone"])
        cmds.setAttr(shape + ".penumbraAngle", entry["penumbra"])
        cmds.setAttr(shape + ".dropoff", entry["dropoff"])
    if entry["shadow"]:
        cmds.setAttr(shape + ".useDepthMapShadows", 1)
        cmds.setAttr(shape + ".dmapResolution", int(entry["dmap"]))
        cmds.setAttr(shape + ".dmapFilterSize", int(entry["filter"]))
        cmds.setAttr(shape + ".shadowColor", 0.0, 0.0, 0.0, type="double3")
        #  The sun: focus its depth map on the subject instead of letting
        #  auto-focus spread it over a floor twenty radii across.
        width = entry.get("width_focus")
        if width and cmds.objExists(shape + ".dmapWidthFocus"):
            cmds.setAttr(shape + ".useDmapAutoFocus", 0)
            cmds.setAttr(shape + ".dmapWidthFocus", float(width))
        else:
            cmds.setAttr(shape + ".useDmapAutoFocus", 1)
    elif cmds.objExists(shape + ".useDepthMapShadows"):
        cmds.setAttr(shape + ".useDepthMapShadows", 0)

    cmds.xform(transform, objectSpace=True, matrix=entry["matrix"])
    return transform, shape


def _make_floor(plan):
    """The shadow catcher, its blinn, and the reason it is a blinn.

    A lambert is flat and a floor is the one surface in the frame whose
    whole job is to show the light falling across it -- the same reason
    `maya_scenesetup.colour` paints characters with a blinn.
    """
    floor = cmds.polyPlane(width=plan["size"], height=plan["size"],
                           subdivisionsX=1, subdivisionsY=1,
                           createUVs=2, constructionHistory=False)[0]
    floor = cmds.rename(floor, plan["name"])
    floor = cmds.ls(floor, long=True)[0]
    cmds.xform(floor, worldSpace=True, translation=plan["position"])
    shader, group = _dress_catcher(floor, plan)
    return floor, shader, group


def _make_cyclorama(plan):
    """The paper sweep: a flat 1 x N plane bent onto the profile.

    `polyPlane` and vertex moves rather than an OpenMaya `MFnMesh.create`,
    because the press is one undo chunk and an API-created mesh is not in
    Maya's undo queue. Each vertex is moved by where it STARTS
    (`cyclorama_targets`); a fresh polyPlane's edges are hard (measured
    2026-10-01), so they are softened for the cove to shade as one surface.
    The plane faces +Y and its rows run from +Z to -Z, so bent up at the
    back it faces the subject.
    """
    profile = plan["profile"]
    sweep = cmds.polyPlane(width=1.0, height=1.0, subdivisionsX=1,
                           subdivisionsY=len(profile) - 1, createUVs=2,
                           constructionHistory=False)[0]
    sweep = cmds.rename(sweep, plan["name"])
    sweep = cmds.ls(sweep, long=True)[0]
    count = cmds.polyEvaluate(sweep, vertex=True)
    vertices = ["{0}.vtx[{1}]".format(sweep, i) for i in range(count)]
    starts = [tuple(cmds.xform(v, query=True, objectSpace=True,
                               translation=True)) for v in vertices]
    targets = cyclorama_targets(starts, profile, plan["width"] / 2.0)
    for vertex, target in zip(vertices, targets):
        cmds.xform(vertex, objectSpace=True, translation=target)
    cmds.polySoftEdge(sweep, angle=180, constructionHistory=False)
    cmds.xform(sweep, worldSpace=True, translation=plan["position"],
               rotation=(0.0, plan["rotate_y"], 0.0))
    shader, group = _dress_catcher(sweep, plan)
    return sweep, shader, group


def _dress_catcher(node, plan):
    """The blinn, the shadow flags and the reference display -- what the
    floor and the cyclorama share."""
    shader = cmds.shadingNode("blinn", asShader=True, name=SHADER)
    cmds.setAttr(shader + ".color", *plan["colour"], type="double3")
    cmds.setAttr(shader + ".specularColor", *plan["specular"],
                 type="double3")
    cmds.setAttr(shader + ".eccentricity", plan["eccentricity"])
    cmds.setAttr(shader + ".specularRollOff", plan["roll_off"])
    group = cmds.sets(renderable=True, noSurfaceShader=True, empty=True,
                      name=shader + "SG")
    cmds.connectAttr(shader + ".outColor", group + ".surfaceShader",
                     force=True)
    cmds.sets(node, edit=True, forceElement=group)

    shape = cmds.listRelatives(node, shapes=True, fullPath=True)[0]
    #  It catches shadows and casts none: a ground plane in its own
    #  shadow map is how a floor ends up striped with acne.
    for attr, value in (("castsShadows", 0), ("receiveShadows", 1),
                        ("doubleSided", 1), ("primaryVisibility", 1)):
        plug = shape + "." + attr
        if cmds.objExists(plug):
            cmds.setAttr(plug, value)
    #  Reference display: it stays out of the way of a marquee select and
    #  is still there in the outliner when the animator wants it.
    cmds.setAttr(node + ".overrideEnabled", 1)
    cmds.setAttr(node + ".overrideDisplayType", 2)
    return shader, group


def delete_rig(rig=None):
    """Take our nodes out, by UUID, and say how many went.

    Existence is re-checked in front of every delete: our shading group
    is a set, and Maya deletes a set together with its last member
    (trap 18), so half of this list is already gone by the time the loop
    reaches it.
    """
    rig = find_rig() if rig is None else rig
    if not rig:
        return 0
    uuids = recorded_nodes(rig) + [_uuid(rig)]
    gone = 0
    for uuid in uuids:
        paths = cmds.ls(uuid, long=True) or []
        for path in paths:
            if cmds.objExists(path):
                try:
                    cmds.delete(path)
                    gone += 1
                except Exception:                             # noqa: BLE001
                    continue
    return gone


def setup(options=None, undoable=True):
    """The press. Build the studio on what the scene holds right now.

    Idempotent: an existing rig is taken down first, so the subject is
    measured without our own floor in the way, and the state captured by
    the FIRST press is carried forward onto the new group.
    """
    options = merged_options(options)
    if undoable:
        cmds.undoInfo(openChunk=True, chunkName="Viewport Studio")
    try:
        return _setup(options)
    finally:
        if undoable:
            cmds.undoInfo(closeChunk=True)


def _setup(options):
    rig = find_rig()
    panels = model_panels()
    cameras = [c for c in {panel_camera(p) for p in panels} if c]
    state = read_state(rig) if rig else capture_state(cameras)

    if rig:
        delete_rig(rig)

    box = subject_bbox(rig=None)
    frame = subject_frame(box)
    panel = active_panel()
    camera = panel_camera(panel)
    camera_pos = None
    if camera:
        transform = cmds.listRelatives(camera, parent=True,
                                       fullPath=True) or []
        if transform:
            camera_pos = cmds.xform(transform[0], query=True,
                                    worldSpace=True, translation=True)
    azimuth = studio_azimuth(camera_pos, frame["centre"])

    selection = cmds.ls(selection=True, long=True) or []
    made = []
    with _quiet_autokey():
        group = cmds.group(empty=True, name=GROUP)
        group = cmds.ls(group, long=True)[0]
        pivot = cmds.group(empty=True, name=PIVOT, parent=group)
        pivot = cmds.ls(pivot, long=True)[0]
        cmds.xform(pivot, objectSpace=True,
                   translation=frame["centre"])

        index = {}
        for spec, entry in zip(lights_of(options["look"]),
                               light_plan(frame, azimuth, options)):
            transform, _shape = _make_light(entry, pivot)
            made.append(transform)
            index[spec.name] = _uuid(transform)
        cmds.setAttr(pivot + ".rotateY", float(options["rotate"]))

        #  The shadow catcher: Soft Studio's cyclorama or everybody else's
        #  flat floor -- under the GROUP either way, never the light pivot.
        catcher = None
        if options["floor"]:
            sweep = cyclorama_plan(frame, azimuth, options)
            if sweep:
                floor, shader, shading = _make_cyclorama(sweep)
                catcher = "cyclorama"
            else:
                floor, shader, shading = _make_floor(
                    floor_plan(frame, options))
                catcher = "floor"
            floor = cmds.parent(floor, group)[0]
            floor = cmds.ls(floor, long=True)[0]
            made += [floor, shader, shading]

        uuids = [_uuid(n) for n in [pivot] + made]
        _write_string(group, MARKER, VERSION)
        _write_string(group, STATE_ATTR, json.dumps(state))
        _write_string(group, NODES_ATTR,
                      ",".join(u for u in uuids if u))
        _write_string(group, OPTIONS_ATTR, json.dumps(dict(options)))
        _write_string(group, LIGHTS_ATTR, json.dumps(index))
        _write_string(group, PIVOT_ATTR, _uuid(pivot))

    #  The viewport last: the lights have to exist before a panel is told
    #  to light with all of them.
    wanted = render_settings(frame, options)
    wrote = apply_plugs(render_plugs(wanted))
    plan = panel_settings(options)
    for name in panels:
        for flag, value in plan.items():
            try:
                cmds.modelEditor(name, edit=True, **{flag: value})
            except Exception:                                 # noqa: BLE001
                continue
    #  Clean view OFF means "as the animator had it", not "leave it
    #  hidden": a press with the box ticked and then a press without it
    #  used to leave the whole rig invisible, which reads as the tool
    #  having broken the viewport. The saved state is what their own
    #  values are, so it answers this for free.
    if not options["clean"]:
        remembered = state.get("panels") or {}
        for name in panels:
            for flag in CLUTTER + ("headsUpDisplay",
                                   "selectionHiliteDisplay"):
                value = remembered.get(name, {}).get(flag, True)
                try:
                    cmds.modelEditor(name, edit=True, **{flag: value})
                except Exception:                             # noqa: BLE001
                    continue
    back = backdrop_settings(options)
    if back:
        cmds.displayPref(displayGradient=bool(back["gradient"]))
        for name in ("background", "backgroundTop", "backgroundBottom"):
            cmds.displayRGBColor(name, *back[name])

    if camera and camera_pos:
        distance = math.sqrt(sum((camera_pos[i] - frame["centre"][i]) ** 2
                                 for i in range(3)))
        for attr, value in dof_plan(distance, options).items():
            plug = "{0}.{1}".format(camera, attr)
            if cmds.objExists(plug):
                try:
                    cmds.setAttr(plug, value if not isinstance(value, bool)
                                 else int(value))
                except Exception:                             # noqa: BLE001
                    continue
        if not options["dof"] and cmds.objExists(camera + ".depthOfField"):
            try:
                cmds.setAttr(camera + ".depthOfField", 0)
            except Exception:                                 # noqa: BLE001
                pass

    if selection:
        alive = [n for n in selection if cmds.objExists(n)]
        if alive:
            cmds.select(alive, replace=True)
        else:
            cmds.select(clear=True)
    else:
        cmds.select(clear=True)

    cmds.refresh()
    #  Say so when a setting did not land. This Maya has all of them, but
    #  an older one may not, and the animator should hear it from the
    #  status line rather than wonder why the picture is flat.
    short = len(wanted) - wrote
    return ("%s on - %d lights%s, %s quality, subject %.0f cm%s"
            % (options["look"], len(lights_of(options["look"])),
               ", " + catcher if catcher else "",
               options["quality"], frame["height"],
               "" if not short else " (%d setting(s) unavailable)" % short))


def retune(options=None):
    """Brightness and Rotate onto a standing rig, without rebuilding it.

    A slider is a dial, not a build button. Rebuilding on every drag
    would re-measure the scene and re-aim the whole studio from wherever
    the camera has drifted to since -- so the light the animator was
    adjusting would move under their hand.
    """
    options = merged_options(options)
    rig = find_rig()
    if not rig:
        return ""
    index = read_index(rig)
    brightness = max(0.0, float(options["brightness"]))
    #  The look the RIG was built with, not whatever the dropdown says
    #  now: the base intensities have to come from the table these very
    #  lights were made from, and picking a new look rebuilds anyway.
    built = read_options(rig).get("look", options["look"])
    touched = 0
    with _quiet_autokey():
        for spec in lights_of(built):
            path = resolve(index.get(spec.name))
            if not path:
                continue
            for shape in (cmds.listRelatives(path, shapes=True,
                                             fullPath=True) or []):
                plug = shape + ".intensity"
                if cmds.objExists(plug):
                    cmds.setAttr(plug, spec.intensity * brightness)
                    touched += 1
        pivot = resolve(_string_attr(rig, PIVOT_ATTR))
        if pivot and cmds.objExists(pivot + ".rotateY"):
            cmds.setAttr(pivot + ".rotateY", float(options["rotate"]))
        #  Keep the group's own record in step, or the next press -- and
        #  `refresh` -- report the numbers from before the drag. The LOOK
        #  written back is the one standing in the scene, never the
        #  dropdown's: recording a look these lights were not built from
        #  would make the next retune scale them off the wrong table.
        record = collections.OrderedDict(options)
        record["look"] = built
        _write_string(rig, OPTIONS_ATTR, json.dumps(dict(record)))
    cmds.refresh()
    return "%s: brightness %.2f, rotate %.0f, %d lights" % (
        built, brightness, float(options["rotate"]), touched)


def restore(undoable=True):
    """Give the animator their viewport back and take our nodes out."""
    rig = find_rig()
    if not rig:
        return "nothing to restore - no Viewport Studio in this scene"
    if undoable:
        cmds.undoInfo(openChunk=True, chunkName="Viewport Studio off")
    try:
        state = read_state(rig)
        gone = delete_rig(rig)
        plugs = apply_plugs(state.get("plugs"))
        apply_panels(state.get("panels"))
        apply_backdrop(state.get("backdrop"))
        cmds.refresh()
        if not state:
            return ("studio off - %d nodes out; no saved viewport state"
                    % gone)
        return "studio off - viewport restored, %d nodes out" % gone
    finally:
        if undoable:
            cmds.undoInfo(closeChunk=True)


def toggle():
    """One entry point for a hotkey: on if it is off, off if it is on."""
    return restore() if find_rig() else setup(window_options())


# ---------------------------------------------------------------------------
#  UI
# ---------------------------------------------------------------------------

HUB_SECTION = "studio"              # our section of the SkeldarAnim hub
STATUS = "vpStudioStatus"           # exists exactly while the panel is built
WIDTH = 300
ROW_SPACING = 3                     # the column's gap between controls



STATUS_WIDTH = 44

_OPTION_VAR = "skeldarVpStudio_%s"

CHECKS = (
    ("floor", "Floor", "a plane under the subject to catch the shadow"),
    ("shadows", "Shadows", "depth-map shadows from the key light"),
    ("ao", "Ambient occlusion", "screen-space contact shadow"),
    ("motion_blur", "Motion blur", "costs the most of anything here"),
    ("anti_alias", "Anti-aliasing", "multisampling and smooth lines"),
    ("bloom", "Bloom", "glow on the highlights only"),
    ("fog", "Atmosphere", "depth haze behind the subject"),
    ("dof", "Depth of field", "focused where the subject is now"),
    ("clean", "Clean view", "hide joints, curves and locators"),
    ("backdrop", "Backdrop", "the look's own colour behind it all"),
)

#  The compact skin's chip labels (2026-10-08): the full label is the tooltip
SHORT_CHECK = {"floor": "Floor", "shadows": "Shadows", "ao": "AO",
               "motion_blur": "Blur", "anti_alias": "AA", "bloom": "Bloom",
               "fog": "Haze", "dof": "DoF", "clean": "Clean",
               "backdrop": "Backdrop"}

CONTROL = {"look": "vpStudioLook",
           "quality": "vpStudioQuality",
           "brightness": "vpStudioBrightness",
           "rotate": "vpStudioRotate"}

MENUS = ("look", "quality")

MENU_ITEMS = {"look": LOOK_ORDER, "quality": QUALITY_ORDER}


def _control(key):
    return CONTROL.get(key, "vpStudio_" + key)


def window_options():
    """Read the panel, or the remembered choices when it is closed.

    A hotkey has no panel to read, and the animator's last set of
    choices is the only honest answer in that case.
    """
    options = collections.OrderedDict(DEFAULTS)
    for key, default in DEFAULTS.items():
        var = _OPTION_VAR % key
        if cmds.optionVar(exists=var):
            stored = cmds.optionVar(query=var)
            if isinstance(default, bool):
                options[key] = bool(stored)
            elif isinstance(default, float):
                options[key] = float(stored)
            else:
                options[key] = stored
    if not is_open():
        return options
    for key, _label, _note in CHECKS:
        name = _control(key)
        if cmds.checkBox(name, exists=True):
            options[key] = cmds.checkBox(name, query=True, value=True)
    for key in MENUS:
        name = _control(key)
        if cmds.optionMenu(name, exists=True):
            options[key] = cmds.optionMenu(name, query=True, value=True)
    for key in ("brightness", "rotate"):
        name = _control(key)
        if cmds.floatSliderGrp(name, exists=True):
            options[key] = cmds.floatSliderGrp(name, query=True, value=True)
    return options


def _remember(options):
    for key, value in options.items():
        var = _OPTION_VAR % key
        if isinstance(value, bool):
            cmds.optionVar(intValue=(var, int(value)))
        elif isinstance(value, float):
            cmds.optionVar(floatValue=(var, float(value)))
        else:
            cmds.optionVar(stringValue=(var, str(value)))


def _status(text):
    """Fixed width: a long message must not stretch the window. The line of every
    card shows it (2026-10-09: the studio is the scene's, one look for all the
    cards); the hub's message line is told from the press's own card only."""
    short = text if len(text) <= STATUS_WIDTH else text[:STATUS_WIDTH - 1] + "…"

    def line():
        if cmds.control(STATUS, exists=True):
            cmds.text(STATUS, edit=True, label=short)
    for scope in [None] + hubcopy.instances("studio"):
        with hubcopy.entered(scope):
            line()
    if cmds.control(STATUS, exists=True):
        #  2026-10-08: the skin's one message line carries the whole text;
        #  the heads-up below already shows it in the viewport
        hubstyle.tell(STATUS, text, viewport=True)
    cmds.headsUpMessage(text, time=2.5)
    return text


def _run(fn, *args):
    """Failures belong on the status line, not in the Script Editor."""
    try:
        return fn(*args)
    except Exception as exc:                                  # noqa: BLE001
        _status("%s: %s" % (type(exc).__name__, exc))
        raise


def _press_setup(*_args):
    def go():
        options = window_options()
        _remember(options)
        return _status(setup(options))
    return _run(go)


def _press_restore(*_args):
    return _run(lambda: _status(restore()))


def _live_change(*_args):
    """A dial moved: re-aim and re-brighten a standing rig, nothing else.

    Only ever touched while a rig exists -- with the studio off these two
    are just remembered numbers, and building a whole studio because
    somebody nudged a slider is not what a slider means.
    """
    def go():
        options = window_options()
        _remember(options)
        if not find_rig():
            return _status("brightness and rotate remembered")
        return _status(retune(options))
    return _run(go)


def _menu_change(*_args):
    """Picking a look (or a quality) re-applies it on a standing studio.

    A preset picker that needs a second press to take effect is a preset
    picker nobody believes; with nothing built it is just remembered.
    Unlike the two dials this cannot retune -- a different look is a
    different set of lights, a different floor and a different sky -- so
    it rebuilds, which is also what keeps the group's stored look honest.
    """
    def go():
        options = window_options()
        _remember(options)
        if not find_rig():
            return _status("%s look remembered" % options["look"])
        return _status(setup(options))
    return _run(go)


def refresh(*_args):
    """Show what the scene holds. Never writes to a control's value.

    The one bug this shape can have is a refresh that clobbers a choice
    the animator made a second ago, so this reads the rig and writes only
    the status line (`maya_scenesetup.window`'s swatch lesson).
    """
    if not is_open():
        return ""
    rig = find_rig()
    if not rig:
        return _status("studio off - pick a look and press Apply")
    opts = read_options(rig)
    return _status("%s on - %s quality" % (opts.get("look", "?"),
                                           opts.get("quality", "?")))


def is_open():
    """True while our section is built in the hub (read by maya_hotkeys)."""
    return bool(cmds.control(STATUS, exists=True))


def show_window():
    """Open the SkeldarAnim hub on the Studio section.

    A `cmds` control has one name per Maya session, so the panel lives in
    the hub or in a window of its own, never both - since 2026-09-17 it is
    the hub (`maya_hub`), and the standalone window is gone.
    """
    import maya_hub
    return maya_hub.show(HUB_SECTION)


def build_panel():
    """One column of plain `cmds`: a dropdown, ten checks and two dials,
    built into whatever layout is current (the hub's section)."""
    stored = window_options()

    #  2026-09-28 (the skin): no fixed widths -- the column stretches like
    #  every other section's; the two menus side by side, the ten checks
    #  as chips, Apply Look the one primary action. 2026-10-08 (the compact
    #  hub): the chips flow and wrap in one layout under short labels (the
    #  full label and its note are the tooltip); the classic hub keeps its
    #  pairs of rows and its words.
    column = cmds.columnLayout(adjustableColumn=True,
                               rowSpacing=hubstyle.row_spacing(6),
                               columnOffset=("both", hubstyle.pick(0, 10)))

    hubstyle.mark(cmds.text(label="lighting, shadows, AO and motion blur, "
                                  "live", align="left"), "note")

    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                   columnWidth2=(150, 120),
                   columnAttach=[(1, "both", 0), (2, "left", 4)])
    for key, note in (("look", "Look: the lights, floor and sky"),
                      ("quality", "Quality: how much the viewport renders")):
        #  No changeCommand yet: it is attached at the end of the build.
        #  Setting an optionMenu's value FIRES its changeCommand, so
        #  wiring it here would rebuild the whole studio as a side effect
        #  of merely opening the panel.
        cmds.optionMenu(_control(key), annotation=note)
        for name in MENU_ITEMS[key]:
            cmds.menuItem(label=name)
        if stored.get(key) in MENU_ITEMS[key]:
            cmds.optionMenu(_control(key), edit=True, value=stored[key])
    cmds.setParent("..")

    def chip(key, label, note):
        hubstyle.mark(cmds.checkBox(
            _control(key), label=hubstyle.pick(SHORT_CHECK[key], label),
            value=bool(stored.get(key, DEFAULTS[key])),
            annotation=label + " - " + note), "chip")

    if hubstyle.skinning():
        #  "flow": Maya's flowLayout wraps the chips and keeps ONE line's
        #  height - the second line stood behind the Bright slider (live,
        #  2026-10-08); the skin keeps the wrapped lines in its height
        hubstyle.mark(cmds.flowLayout(wrap=True, columnSpacing=3), "flow",
                      layout=True)
        for key, label, note in CHECKS:
            chip(key, label, note)
        cmds.setParent("..")
    else:
        for start in range(0, len(CHECKS), 2):
            cmds.rowLayout(numberOfColumns=2, columnWidth2=(140, 140),
                           columnAttach=[(1, "left", 0), (2, "left", 4)])
            for key, label, note in CHECKS[start:start + 2]:
                chip(key, label, note)
            cmds.setParent("..")

    cmds.floatSliderGrp(_control("brightness"),
                        label=hubstyle.pick("Bright", "Brightness "),
                        field=True, minValue=0.1, maxValue=3.0,
                        value=float(stored.get("brightness", 1.0)),
                        fieldMinValue=0.0, fieldMaxValue=10.0,
                        columnWidth3=hubstyle.pick((44, 40, 150),
                                                   (70, 45, 150)),
                        adjustableColumn=3,
                        height=hubstyle.height("small", 22),
                        changeCommand=_live_change)
    cmds.floatSliderGrp(_control("rotate"),
                        label=hubstyle.pick("Rotate", "Rotate "), field=True,
                        minValue=-180.0, maxValue=180.0,
                        value=float(stored.get("rotate", 0.0)),
                        fieldMinValue=-720.0, fieldMaxValue=720.0,
                        columnWidth3=hubstyle.pick((44, 40, 150),
                                                   (70, 45, 150)),
                        adjustableColumn=3,
                        height=hubstyle.height("small", 22),
                        changeCommand=_live_change)

    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                   columnAttach=[(1, "both", 0), (2, "left", 4)])
    hubstyle.mark(cmds.button(
        label="Apply Look", height=hubstyle.height("button", 32),
        backgroundColor=(0.45, 0.70, 0.50),
        annotation="build the chosen look on whatever the scene holds",
        command=_press_setup), "primary", "bulb")
    hubstyle.mark(cmds.button(
        label=hubstyle.pick("Restore", "Restore Viewport"),
        height=hubstyle.height("button", 32), width=hubstyle.pick(80, 130),
        annotation="put the animator's own viewport back and delete our "
                   "nodes",
        command=_press_restore), "secondary", "arrow-back-up")
    cmds.setParent("..")

    hubstyle.mark(cmds.text(STATUS, label="pick a look and press Apply",
                            align="left"), "status")

    #  Only now, with every control built and every remembered value in
    #  place, do the dropdowns become live.
    for key in MENUS:
        cmds.optionMenu(_control(key), edit=True,
                        changeCommand=_menu_change)

    cmds.setParent("..")
    refresh()
    return column


if __name__ == "__main__":
    show_window()
