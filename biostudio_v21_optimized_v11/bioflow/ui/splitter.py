from PySide6.QtWidgets import QSplitter, QSplitterHandle
from PySide6.QtCore import Qt

class CollapsibleHandle(QSplitterHandle):
    def __init__(self, orientation, parent):
        super().__init__(orientation, parent)

    def mouseDoubleClickEvent(self, event):
        s = self.splitter()
        sizes = s.sizes()
        if not sizes:
            return
        total = sum(sizes)
        idx = self.index()
        if idx != 0:
            return
        if s.orientation() == Qt.Horizontal:
            if sizes[0] == 0:
                left = max(total // 6, 140)
                sizes[0] = left
                if len(sizes) > 1:
                    sizes[1] = total - left
            else:
                sizes[0] = 0
                if len(sizes) > 1:
                    sizes[1] = total
            s.setSizes(sizes)
        elif s.orientation() == Qt.Vertical:
            if sizes[0] == 0:
                top = max(total // 5, 120)
                sizes[0] = top
                if len(sizes) > 1:
                    sizes[1] = total - top
            else:
                sizes[0] = 0
                if len(sizes) > 1:
                    sizes[1] = total
            s.setSizes(sizes)
        else:
            super().mouseDoubleClickEvent(event)

class CollapsibleSplitter(QSplitter):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)

    def createHandle(self):
        return CollapsibleHandle(self.orientation(), self)
