"""Export the Auto card's verify clips out of the open Unreal editor, each WITH its preview mesh.

The Auto card (2026-10-02) was measured on the animator's MarkerLess_02 project. This writes one
clip per skeleton kind of interest into a folder, the way the bridge exports them
(`uescripts.export_script(..., preview_mesh=True)`), plus `fixtures.json` (name, package, fps, path)
that verify_auto_character.py reads. Run with mayapy (stdlib + Epic's remote_execution), the
editor open with Remote Execution on:

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' docs/superpowers/plans/export_auto_fixtures.py <folder>
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.normpath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))

# (name, package): who each one is - what the verify expects of it is the verify's
CLIPS = [
    ("MM_Fall_Loop", "/Game/Characters/Mannequins/Anims/Unarmed/Jump/MM_Fall_Loop"),
    ("Conjure_SwirlArms", "/Game/MC_DungeonLife/Animations/Conjure/am_Ready_Idle_Conjure_01_SwirlArms"),
    ("Orc_Walk_Fwd", "/Game/Orc_Marauder/Animation/MM_Walk_Fwd"),
    ("Sword1h_WalkStop_RU", "/Game/SwordAnimsetPro/Animations/RootMotion/Sword1h_WalkStop_RU"),
    ("Kwang_Ability_Q_Catch", "/Game/ParagonKwang/Characters/Heroes/Kwang/Animations/Ability_Q_Catch"),
    ("MetaHuman_AttackTest", "/Game/AS_AttackTest"),
]


def main(folder):
    sys.path.insert(0, PLUGIN)
    from maya_uebridge import uelink, uescripts
    if not os.path.isdir(folder):
        os.makedirs(folder)
    out = os.path.join(folder, "reply.json")
    manifest = []
    for name, package in CLIPS:
        fbx = os.path.join(folder, name + ".fbx").replace("\\", "/")
        payload = uelink.run_script(uescripts.export_script(out, package, fbx, preview_mesh=True),
                                    out, timeout=30)
        manifest.append(dict(name=name, package=package, fps=payload.get("fps"),
                             frames=payload.get("frames"), path=payload.get("path") or fbx,
                             bytes=os.path.getsize(fbx) if os.path.isfile(fbx) else 0))
        print("exported", name, manifest[-1]["bytes"], "bytes", payload.get("fps"), "fps")
        sys.stdout.flush()
    with open(os.path.join(folder, "fixtures.json"), "w") as handle:
        json.dump(manifest, handle, indent=1)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.environ.get("TEMP", "."),
                                                            "skeldar_auto_fixtures"))
