"""The characters the bridge can put into a Cascadeur scene. Pure; stdlib only.

Each row is a skeleton WITH its mesh, Y-up and without a wrapper node: the form
Cascadeur imports as a standing character (docs/superpowers/plans/
make_cascadeur_character.py says why a UE export needs the flattening step).
"""

import os
from collections import namedtuple

Character = namedtuple("Character", "key label path")

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(PLUGIN, "assets", "Cascadeur")

CHARACTERS = (
    Character("manny_ue5", "Manny UE5", os.path.join(ASSETS, "Manny_UE5.fbx")),
)


def labels():
    """The cards' labels, in order."""
    return [character.label for character in CHARACTERS]


def by_label(label):
    """The character with that label, or None."""
    for character in CHARACTERS:
        if character.label == label:
            return character
    return None


def default():
    """The character a fresh bridge starts with."""
    return CHARACTERS[0]
