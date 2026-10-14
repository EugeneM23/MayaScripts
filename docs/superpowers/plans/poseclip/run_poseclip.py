# Pose on clip - our poses onto a locomotion clip (docs/superpowers/plans/poseclip)
# Select any part of the character carrying the clip (or nothing: the only keyed skeleton in the scene),
# then run the lines you want (select them and Ctrl+Enter). Each apply makes a copy of the character beside it.
import sys
FOLDER = r"C:/!!!Work/MayaScripts/docs/superpowers/plans/poseclip"
if FOLDER not in sys.path:
    sys.path.insert(0, FOLDER)
for name in ("poseclip_maya", "poseclip", "posemath", "skeletonmap"):   # the latest code on every run
    sys.modules.pop(name, None)
import poseclip_maya as pc

print(pc.pose_names())                            # your poses (Walk Builder's Save pose)

pc.apply("goblin")                                # a copy 150 cm to the character's right
pc.apply("two_handed_sword", offset=-150)         # a copy 150 cm to its left

# share  - how much of the pose (0..1)
# motion - how much of the clip's own motion rides on it (0..2)
# parts  - ("torso", "pelvis", "knees", "arms", "feet")
# pc.apply("goblin", share=0.6, motion=0.8, parts=("torso", "pelvis", "arms", "feet"))
