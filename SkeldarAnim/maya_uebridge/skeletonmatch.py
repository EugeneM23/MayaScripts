"""Is a clip's skeleton one of OUR characters'? - the Auto card's question (2026-10-02).

The animator: «сделаем карточку рига и скелета со знаком вопроса и когда переносим анимацию при
выбраной этой карточке наш плагин будет смотреть какой скелет в исходном файле если он найдет скелет
который совпадает с нашим то перенесем анимацию на наш риг или скелет, если ... совпадений нету то
импортируем в сцену родной риг или скелет». Spec:
docs/superpowers/specs/2026-10-02-auto-character-import-design.md.

What "the same skeleton" means here, measured on the animator's Unreal project (MarkerLess_02, 12
skeletons): the share of the clip's bones whose ANIMATED length - the median over a few sampled
frames, to the nearest bone both sides share - is within 1 % of our bone at its bind. Matches read
0.88-1.00 (Manny, MC_DungeonLife's and MC_LongswordVol2's UE5 mannequins, the Orc on Orc D, the UE4
mannequins), everything else at most 0.47 (an Orc clip against Manny, whose names it shares). Two
things that do NOT work, both measured: the mesh's bind (Unreal hands a Manny clip Quinn's mesh -
2 % of its bones Manny's, 100 % of the animation's), and one median over all bones (Orc against
Manny reads 1.9 % - a coin toss on a 1 % rule).

Our side is shipped data: `assets/character_skeletons.json`, every catalog row's game skeleton at its
bind (`docs/superpowers/plans/make_character_skeletons.py`). Stdlib only, and pure but for
`load_templates` reading that file: the clip arrives as data (`autoimport.clip_bones` reads it).
"""

import collections
import json
import math
import os

TOLERANCE = 0.01          # a bone within 1 % of ours votes "ours"
SHORTEST = 1.0            # cm: shorter bones on both sides do not vote
MIN_SHARE = 0.75          # the share of voters within TOLERANCE that makes a match
MIN_BONES = 10            # fewer voters than this decide nothing
SAMPLES = 9               # frames of the clip a length is the median over

# Bones that say nothing about whose skeleton it is (maya_retargetmode's own lists): the root and the
# pelvis offsets are motion, the export helpers each skeleton's own layout.
HELPER_PREFIXES = ("ik_", "weapon_", "camera_")
NOT_A_LENGTH = ("root", "pelvis", "center_of_mass", "interaction")

TEMPLATES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "assets", "character_skeletons.json").replace("\\", "/")

Score = collections.namedtuple("Score", "key share count median")
Match = collections.namedtuple("Match", "key best scores")


# --------------------------------------------------------------------- pure

def votes(name):
    """Whether a bone's length says anything about whose skeleton it is. Pure."""
    low = name.lower()
    return name not in NOT_A_LENGTH and not low.startswith(HELPER_PREFIXES)


def anchor(name, parents, names):
    """The nearest ancestor of `name` in `names`, walking `parents` {bone: parent or None}. Pure."""
    seen = set()
    parent = parents.get(name)
    while parent is not None and parent not in names:
        if parent in seen:
            return None
        seen.add(parent)
        parent = parents.get(parent)
    return parent


def _median(values):
    values = sorted(values)
    if not values:
        return 0.0
    middle = len(values) // 2
    if len(values) % 2:
        return values[middle]
    return 0.5 * (values[middle - 1] + values[middle])


def score(clip, template, key=""):
    """The Score of a clip against one of our skeletons. Pure.

    clip      {bone: (parent bone or None, [(x, y, z) per sampled frame])}
    template  {bone: (parent bone or None, (x, y, z) at its bind)}

    Each voter - a bone both sides have, not a helper - is measured to its nearest ancestor both
    sides have, and only when that ancestor is the same bone on both sides. A bone shorter than
    SHORTEST on both sides does not vote."""
    names = set(clip) & set(template)
    clip_parents = dict((bone, data[0]) for bone, data in clip.items())
    our_parents = dict((bone, data[0]) for bone, data in template.items())
    diffs = []
    for bone in names:
        if not votes(bone):
            continue
        ours = anchor(bone, our_parents, names)
        if ours is None or anchor(bone, clip_parents, names) != ours:
            continue
        rest = math.dist(template[bone][1], template[ours][1])
        frames = list(zip(clip[bone][1], clip[ours][1]))
        if not frames:
            continue
        length = _median(math.dist(a, b) for a, b in frames)
        longer = max(rest, length)
        if longer <= SHORTEST:
            continue
        diffs.append(abs(length - rest) / longer)
    if not diffs:
        return Score(key, 0.0, 0, 1.0)
    within = sum(1 for diff in diffs if diff <= TOLERANCE)
    return Score(key, float(within) / len(diffs), len(diffs), _median(diffs))


def accepted(found):
    """Whether a Score makes a match. Pure."""
    return found is not None and found.count >= MIN_BONES and found.share >= MIN_SHARE


def match(clip, templates, keys):
    """The Match of a clip among our rows `keys` (catalog order: ties go to the first). Pure.

    `templates` {row key: template}. `key` is the matched row or None; `best` the best Score
    whether it matched or not (None when no row could be scored); `scores` every row's, in `keys`
    order."""
    scores = [score(clip, templates[k], k) for k in keys if k in templates]
    ranked = sorted(enumerate(scores), key=lambda pair: (-pair[1].share, -pair[1].count, pair[0]))
    best = ranked[0][1] if ranked else None
    return Match(best.key if accepted(best) else None, best, scores)


def match_text(found, label_of=None):
    """«matched Manny [rig] - 78 of 78 bones» / «no skeleton of ours (best Orc D [rig]: 45 % of
    78 bones)». Pure; `label_of(key)` names a row (the key itself without one)."""
    label_of = label_of or (lambda key: key)
    best = found.best if found is not None else None
    if found is not None and found.key:
        return "matched {0} - {1} of {2} bones".format(
            label_of(found.key), int(round(best.share * best.count)), best.count)
    if best is None or not best.count:
        return "no skeleton of ours (no bone named as ours)"
    return "no skeleton of ours (best {0}: {1} % of {2} bones)".format(
        label_of(best.key), int(round(100.0 * best.share)), best.count)


# --------------------------------------------------------------------- data

_CACHE = {}


def read_templates(payload):
    """{row key: template} from the JSON payload. Pure."""
    out = {}
    for key, row in (payload.get("rows") or {}).items():
        out[key] = dict((bone, (data[0], (float(data[1]), float(data[2]), float(data[3]))))
                        for bone, data in (row.get("bones") or {}).items())
    return out


def load_templates(path=None):
    """{row key: template} from the shipped file, read once per change of the file."""
    path = path or TEMPLATES_PATH
    try:
        stamp = os.path.getmtime(path)
    except OSError:
        return {}
    cached = _CACHE.get(path)
    if cached is None or cached[0] != stamp:
        with open(path, "r") as handle:
            cached = (stamp, read_templates(json.load(handle)))
        _CACHE[path] = cached
    return dict(cached[1])
