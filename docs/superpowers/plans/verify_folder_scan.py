"""The Folder source's Refresh: it reads, it never writes, and it asks first.

    mayapy docs/superpowers/plans/verify_folder_scan.py [phases] [out.txt]

phases: takes,nothing,guard  (default: all)

2026-11-03, the animator: «Я нажал на обновление списка файлов в animation
setup и теперь у меня создаюстся какие-то 14 тысяч файлов? Это какой-то
очень страшный баг». Nothing was created. Their own listing cache, written
that morning at 05:11:53, says `folder` / `C:/Users/MY PC/Downloads` / 14 037
rows, and their Downloads holds 14 206 files the plugin reads as clips - an
extracted Unity course among them, 5 894 fbx of asset packs. The whole tree
held 188 082 entries before the scan and 188 082 after.

Two defects came out of that press and this script is their proof:

1. the take read went through a MEL string, and **MEL cannot carry a
   non-ASCII path** - every clip in a folder with a Russian name was refused
   («Use syntax: FBXRead -f filename») and listed with no takes and no
   frames. 5 874 of their 11 580 Downloads fbx are such files. Gate 1 reads
   real clips in such a folder BOTH ways: the MEL road is the control and
   must fail.
2. one click walked whatever was picked. The walk is cheap, so Refresh now
   counts first and asks over `sources.ASK_OVER` clips, naming the count,
   the time, where the files are and that nothing is written.

Standalone: it reads the animator's own clips and writes only into a scratch
folder of its own, which it removes.
"""

import os
import shutil
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(REPO, "SkeldarAnim"))

import maya.standalone                                       # noqa: E402
maya.standalone.initialize()

import maya.mel as mel                                       # noqa: E402

from maya_uebridge import animimport, formats, sources        # noqa: E402

#  Where the animator's own clips and the embedded-media file live.
CLIPS = "C:/!!!Work/Animations"
EMBEDDED = os.path.join(REPO, "sources/creep/creep_T-pose_draft.fbx")
DOWNLOADS = "C:/Users/MY PC/Downloads"
#  A folder whose name MEL cannot carry.
RUSSIAN = "Анимации Модуль V"

FAILED = []
LINES = []


def say(text=""):
    LINES.append(text)
    print(text)


def gate(number, what, ok, detail=""):
    say("  %-5s gate %-2s %s%s" % ("ok" if ok else "FAILED", number, what,
                                   "   " + detail if detail else ""))
    if not ok:
        FAILED.append(number)


def mel_takes(path):
    """The road before 2026-11-03, kept as the control: the path inside a MEL
    string."""
    animimport.ensure_fbx_plugin()
    try:
        mel.eval('FBXRead -f "{0}"'.format(path.replace("\\", "/")))
        count = int(mel.eval("FBXGetTakeCount") or 0)
    except Exception:                                        # noqa: BLE001
        return []
    out = []
    for index in range(1, count + 1):
        try:
            span = mel.eval("FBXGetTakeLocalTimeSpan {0}".format(index))
            out.append((index, mel.eval("FBXGetTakeName {0}".format(index)) or "",
                        float(span[0]), float(span[1])))
        except Exception:                                    # noqa: BLE001
            out.append((index, "", None, None))
    return out


def animated_clips(how_many):
    """`how_many` of the animator's own clips that hold a moving take."""
    out = []
    for path in sources.walk_files(CLIPS, (".fbx",)):
        takes = formats.fbx_takes(path)
        if any(t[3] is not None and t[2] is not None and t[3] > t[2]
               for t in takes):
            out.append(path)
        if len(out) >= how_many:
            break
    return out


# ----------------------------------------------------------- 1: the take read

def phase_takes(scratch):
    say("")
    say("=== a folder with a Russian name")
    folder = os.path.join(scratch, RUSSIAN)
    os.makedirs(folder)
    clips = animated_clips(4)
    for path in clips:
        shutil.copyfile(path, os.path.join(folder, os.path.basename(path)))
    say("  %d of the animator's own clips in %r" % (len(clips), RUSSIAN))

    before = sources.scan(folder, "folder", mel_takes)
    after = sources.scan(folder, "folder", formats.fbx_takes)
    old_framed = [r for r in before if r.frames]
    new_framed = [r for r in after if r.frames]
    gate(1, "the MEL road reads no takes there (the control)",
         len(before) == len(clips) and not old_framed,
         "%d rows, %d with frames" % (len(before), len(old_framed)))
    gate(2, "every clip is read now",
         len(new_framed) == len(clips),
         "frames " + ", ".join(str(r.frames) for r in new_framed))
    gate(3, "the frames are the ones the file holds",
         all(formats.fbx_takes(os.path.join(folder, os.path.basename(p)))
             == formats.fbx_takes(p) for p in clips))

    #  an ASCII path must answer exactly what it answered before
    same = all(formats.fbx_takes(p) == mel_takes(p) for p in clips)
    gate(4, "an ASCII path reads the same as it did", same)

    #  a row of a Russian-named folder can be imported: the reference is
    #  built from the takes, and the import reads an ASCII copy (`staged`)
    row = [r for r in after if r.frames][0]
    ref = sources.record_ref(row)
    gate(5, "such a row has an import reference and no refusal",
         bool(ref) and formats.check(ref) == "",
         "%r -> %r" % (os.path.basename(ref), formats.check(ref) or "ok"))


# --------------------------------------------------- 2: it writes nothing

def phase_nothing(scratch):
    say("")
    say("=== what a scan leaves behind")
    folder = os.path.join(scratch, "embedded")
    os.makedirs(folder)
    #  the one file that WOULD make a `.fbm`: its textures are embedded
    shutil.copyfile(EMBEDDED, os.path.join(folder, os.path.basename(EMBEDDED)))
    for path in animated_clips(3):
        shutil.copyfile(path, os.path.join(folder, os.path.basename(path)))

    def inventory(root):
        out = set()
        for here, dirs, files in os.walk(root):
            out |= set(os.path.join(here, n) for n in files)
            out |= set(os.path.join(here, d) + os.sep for d in dirs)
        return out

    before = inventory(folder)
    rows = sources.scan(folder, "folder", formats.fbx_takes)
    after = inventory(folder)
    gate(6, "the scan read the folder", len(rows) >= 4, "%d rows" % len(rows))
    gate(7, "nothing was created beside the files",
         after == before,
         "%d entries before, %d after" % (len(before), len(after)))
    gate(8, "no .fbm folder from the embedded-media file",
         not any(p.lower().endswith(".fbm" + os.sep) for p in after))


# ------------------------------------------------------- 3: the guard

def phase_guard(scratch):
    say("")
    say("=== the question before a huge scan")
    small = sources.walk_files(CLIPS, tuple(sources.FORMATS))
    gate(9, "a real animation folder is scanned with no question",
         sources.scan_question(CLIPS, small) == "",
         "%s holds %d clips" % (CLIPS, len(small)))

    if not os.path.isdir(DOWNLOADS):
        say("  (no %s - the animator's own folder is not here)" % DOWNLOADS)
        return
    files = sources.scan_files(DOWNLOADS, "folder")
    question = sources.scan_question(DOWNLOADS, files)
    gate(10, "the animator's own press is asked about first",
         bool(question), "%s holds %d clip files" % (DOWNLOADS, len(files)))
    gate(11, "the question says the count, the folder and the time",
         sources.grouped(len(files)) in question and DOWNLOADS in question
         and ("min" in question or " s" in question))
    gate(12, "it says nothing is written", "writes nothing" in question)
    biggest = sources.biggest_folders(DOWNLOADS, files)
    gate(13, "it names where the files are",
         bool(biggest) and all(name in question for name, _n in biggest),
         ", ".join("%d in %s" % (count, name) for name, count in biggest))
    say("")
    for line in question.splitlines():
        say("      | " + line)

    #  the walk is handed on: the scan must not walk the tree again
    def no_walk(top):
        raise AssertionError("the scan walked again")
    rows = sources.scan(scratch, "folder", formats.fbx_takes,
                        files=[], walk=no_walk)
    gate(14, "the scan takes the walk it is given", rows == [])


PHASES = {"takes": phase_takes, "nothing": phase_nothing, "guard": phase_guard}


def main():
    args = [a for a in sys.argv[1:]]
    out = None
    if args and (args[-1].endswith(".txt") or args[-1].endswith(".log")):
        out = args.pop()
    chosen = args[0].split(",") if args else list(PHASES)
    scratch = tempfile.mkdtemp(prefix="verify_folder_scan_")
    try:
        for name in chosen:
            PHASES[name](scratch)
    finally:
        say("")
        say("%d of %d gates failed%s"
            % (len(FAILED), 14, (": " + ", ".join(str(n) for n in FAILED))
               if FAILED else ""))
        if out:
            with open(out, "w", encoding="utf-8") as handle:
                handle.write("\n".join(LINES) + "\n")
        #  the FBX plugin keeps the last file it read open
        shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    main()
