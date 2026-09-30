"""The see-through window: the ghost's picture, background taken out.

Qt and ctypes - never Maya. The Curve Overlay's measured window
(2026-09-05): frameless, translucent, a TOP-LEVEL (a native GL child would
paint over any child of ours), owned by Maya's main window so it rides its
z-order; WA_TransparentForMouseEvents does not cross a native window, so
the click-through is WS_EX_TRANSPARENT: asked of Qt itself with the
`WindowTransparentForInput` flag (Qt rewrites the style of its windows and
drops a bit it did not set - measured on the ghost 2026-09-30), and set
again after `show()` and by the mode's follow timer should it go.
"""

from PySide6 import QtCore, QtGui, QtWidgets

from maya_graphoverlay import winstyle

NAME = "skeldarGraphOverlayGlass"


class Glass(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super(Glass, self).__init__(parent, QtCore.Qt.Tool
                                    | QtCore.Qt.FramelessWindowHint
                                    | QtCore.Qt.WindowTransparentForInput)
        self.setObjectName(NAME)
        for attribute in (QtCore.Qt.WA_TranslucentBackground,
                          QtCore.Qt.WA_NoSystemBackground,
                          QtCore.Qt.WA_TransparentForMouseEvents,
                          QtCore.Qt.WA_ShowWithoutActivating):
            self.setAttribute(attribute, True)
        self.setAutoFillBackground(False)
        self._image = None
        self._buffer = None
        self.paint_count = 0

    def place(self, rect):
        """Geometry, then show, then the style - that order (re-showing
        recreates the native window and drops the style)."""
        self.setGeometry(*[int(v) for v in rect])
        if not self.isVisible():
            self.show()
        winstyle.set_click_through(int(self.winId()), True)

    def set_frame(self, bgra):
        """Show `bgra`: (h, w, 4) uint8, B G R A, straight alpha. The array
        is held - the image reads it in place."""
        height, width = bgra.shape[:2]
        self._buffer = bgra
        self._image = QtGui.QImage(bgra.data, width, height, width * 4,
                                   QtGui.QImage.Format_ARGB32)
        self.update()

    def frame(self):
        return self._image

    def keep_click_through(self):
        """Set WS_EX_TRANSPARENT again if it went; True when it had to."""
        hwnd = int(self.winId())
        if winstyle.is_click_through(hwnd):
            return False
        winstyle.set_click_through(hwnd, True)
        return True

    def paintEvent(self, event):
        self.paint_count += 1
        if self._image is None:
            return
        painter = QtGui.QPainter(self)
        try:
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_Source)
            painter.drawImage(0, 0, self._image)
        finally:
            painter.end()

    def close_glass(self):
        try:
            self.hide()
            self._image = None
            self._buffer = None
            self.deleteLater()
        except RuntimeError:
            pass
