"""Headless spike for maya_voice: what Qt in Maya's Python sees here.

Run in mayapy, offscreen, with no GUI and no command port:

    $env:QT_QPA_PLATFORM = 'offscreen'
    & 'C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe' docs\superpowers\plans\voice_spike_headless.py

It prints the audio devices and whether our 16 kHz mono s16 format is
accepted, then grabs the primary screen as JPEG and reports the size. It does
not open a device for recording or playback. The live check (a real microphone,
a real speaker, a real screen in the animator's Maya) stays with the animator.
"""

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.normpath(os.path.join(HERE, "..", "..", "..", "SkeldarAnim"))
if PLUGIN not in sys.path:
    sys.path.insert(0, PLUGIN)


def main():
    from PySide6 import QtCore, QtGui, QtMultimedia as M
    from maya_voice import media, protocol

    app = QtGui.QGuiApplication.instance() or QtGui.QGuiApplication([])
    print("Qt", QtCore.qVersion())

    fmt = M.QAudioFormat()
    fmt.setSampleRate(protocol.RATE)
    fmt.setChannelCount(1)
    fmt.setSampleFormat(M.QAudioFormat.SampleFormat.Int16)

    inputs = M.QMediaDevices.audioInputs()
    outputs = M.QMediaDevices.audioOutputs()
    print("audio inputs:", [d.description() for d in inputs] or "none")
    print("audio outputs:", [d.description() for d in outputs] or "none")

    default_in = M.QMediaDevices.defaultAudioInput()
    if default_in.isNull():
        print("microphone: none (the panel would say so)")
    else:
        print("microphone:", default_in.description(),
              "accepts 16 kHz mono s16:",
              default_in.isFormatSupported(fmt))
        print("  its preferred format:", default_in.preferredFormat()
              .sampleRate(), "Hz", default_in.preferredFormat()
              .channelCount(), "ch")

    default_out = M.QMediaDevices.defaultAudioOutput()
    if default_out.isNull():
        print("speaker: none (the panel would say so)")
    else:
        print("speaker:", default_out.description(),
              "accepts 16 kHz mono s16:",
              default_out.isFormatSupported(fmt))

    started = time.time()
    try:
        data = media.grab_jpeg(max_width=1280, quality=55)
        print("screen frame: {0} bytes JPEG in {1:.3f} s".format(
            len(data), time.time() - started))
        image = QtGui.QImage()
        print("decodes back:", image.loadFromData(data, "JPEG"),
              "{0}x{1}".format(image.width(), image.height()))
    except media.MediaError as exc:
        print("screen: {0}".format(exc))


if __name__ == "__main__":
    main()
