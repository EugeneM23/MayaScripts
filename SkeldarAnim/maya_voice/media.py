"""maya_voice.media - the sound and the screen, through Qt. Imported lazily.

Everything here runs on Maya's main thread (the window's timer calls it).
The only logic is in the pure modules; this file is the thin glue to
QtMultimedia and QtGui. Nothing is opened at import.

- `Mic`: the default input, read in pulls. Opens at 16 kHz mono s16 when the
  device allows it, else its own preferred format converted by `pcm`.
- `Speaker`: the default output, written in pushes, the same way.
- `grab_jpeg`: the primary screen as a JPEG, scaled to a maximum width.
- `Viewer`: a small window that shows the last JPEG it was given.
"""

from maya_voice import pcm
from maya_voice import protocol


class MediaError(Exception):
    """A device or the screen is not there, or its format is not ours."""


def _qt():
    try:
        from PySide6 import QtCore, QtGui, QtMultimedia
    except ImportError as exc:
        raise MediaError("Qt multimedia is not available: {0}".format(exc))
    return QtCore, QtGui, QtMultimedia


def _bytes(qbytes):
    """The bytes of a QByteArray, whichever way this PySide answers."""
    try:
        return bytes(qbytes)
    except TypeError:
        return bytes(qbytes.data())


def _format(M, rate, channels):
    fmt = M.QAudioFormat()
    fmt.setSampleRate(rate)
    fmt.setChannelCount(channels)
    fmt.setSampleFormat(M.QAudioFormat.SampleFormat.Int16)
    return fmt


class Mic(object):

    def __init__(self):
        QtCore, _gui, M = _qt()
        device = M.QMediaDevices.defaultAudioInput()
        if device.isNull():
            raise MediaError("no microphone")
        want = _format(M, protocol.RATE, 1)
        self.ratio = None
        self.channels = 1
        self.kind = "h"
        if device.isFormatSupported(want):
            fmt = want
        else:
            fmt = device.preferredFormat()
            kind = pcm.kind_for(fmt.bytesPerSample())
            ratio = pcm.ratio_for(fmt.sampleRate(), fmt.channelCount(),
                                  fmt.bytesPerSample())
            if ratio is None or kind is None:
                raise MediaError("the microphone's format is not converted")
            self.ratio = ratio
            self.channels = fmt.channelCount()
            self.kind = kind
        self.source = M.QAudioSource(device, fmt)
        self.io = None

    def start(self):
        self.io = self.source.start()

    def read(self):
        """The PCM that arrived since the last read, as ours (16 kHz mono)."""
        if self.io is None:
            return b""
        raw = _bytes(self.io.readAll())
        if self.ratio is None:
            #  whole samples only: an odd byte would shift every packet after it
            return raw[:len(raw) - (len(raw) % 2)]
        return pcm.to_ours(raw, self.channels, self.ratio, self.kind)

    def stop(self):
        if self.source is not None:
            self.source.stop()
        self.io = None


class Speaker(object):

    def __init__(self):
        QtCore, _gui, M = _qt()
        device = M.QMediaDevices.defaultAudioOutput()
        if device.isNull():
            raise MediaError("no audio output")
        want = _format(M, protocol.RATE, 1)
        self.ratio = None
        self.channels = 1
        self.kind = "h"
        if device.isFormatSupported(want):
            fmt = want
        else:
            fmt = device.preferredFormat()
            kind = pcm.kind_for(fmt.bytesPerSample())
            ratio = pcm.ratio_for(fmt.sampleRate(), fmt.channelCount(),
                                  fmt.bytesPerSample())
            if ratio is None or kind is None:
                raise MediaError("the output's format is not converted")
            self.ratio = ratio
            self.channels = fmt.channelCount()
            self.kind = kind
        self.sink = M.QAudioSink(device, fmt)
        self.io = None

    def start(self):
        self.io = self.sink.start()

    def free(self):
        return self.sink.bytesFree()

    def packet_size(self):
        """One 60 ms packet in the device's own format, in bytes."""
        from array import array
        width = array(self.kind).itemsize
        return protocol.PACKET_SAMPLES * (self.ratio or 1) * self.channels * width

    def write(self, data):
        if self.io is None:
            return 0
        if self.ratio is not None:
            data = pcm.from_ours(data, self.channels, self.ratio, self.kind)
        return self.io.write(data)

    def stop(self):
        if self.sink is not None:
            self.sink.stop()
        self.io = None


def grab_jpeg(max_width=1280, quality=55):
    """The primary screen as JPEG bytes, at most `max_width` wide."""
    QtCore, QtGui, _M = _qt()
    app = QtGui.QGuiApplication.instance()
    if app is None:
        raise MediaError("no Qt application")
    screen = QtGui.QGuiApplication.primaryScreen()
    if screen is None:
        raise MediaError("no screen")
    image = screen.grabWindow(0).toImage()
    if image.width() > max_width:
        image = image.scaledToWidth(
            max_width, QtCore.Qt.TransformationMode.SmoothTransformation)
    buffer = QtCore.QBuffer()
    buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer, "JPEG", quality):
        raise MediaError("the frame would not encode")
    return _bytes(buffer.data())


class Viewer(object):
    """A window that shows the last frame it was given (created on demand)."""

    def __init__(self):
        QtCore, QtGui, _M = _qt()
        from PySide6 import QtWidgets
        self.QtCore = QtCore
        self.QtGui = QtGui
        self.window = QtWidgets.QLabel()
        self.window.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.window.setMinimumSize(640, 360)
        self.window.resize(960, 540)
        self.window.setWindowTitle("Skeldar Voice - screen")
        self.pixmap = None

    def show_jpeg(self, data, title=""):
        image = self.QtGui.QImage()
        if not image.loadFromData(data, "JPEG"):
            return False
        self.pixmap = self.QtGui.QPixmap.fromImage(image)
        self.window.setPixmap(self.pixmap.scaled(
            self.window.size(), self.QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            self.QtCore.Qt.TransformationMode.SmoothTransformation))
        if title:
            self.window.setWindowTitle("Skeldar Voice - " + title)
        if not self.window.isVisible():
            self.window.show()
        return True

    def close(self):
        self.window.close()
