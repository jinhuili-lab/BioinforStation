from PySide6.QtWidgets import QTextEdit
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QTextCursor, QKeyEvent, QTextCharFormat, QColor, QGuiApplication
import re


CSI_PATTERN = re.compile(r"\x1b\[([0-9;?]*)([A-Za-z])")
OSC_PATTERN = re.compile(r"\x1b\][^\x07]*\x07")


def apply_sgr_to_format(fmt: QTextCharFormat, params: str) -> QTextCharFormat:
    """Apply SGR (Select Graphic Rendition) codes to the QTextCharFormat.

    Supports basic colors: 30-37, 90-97 foreground; 40-47 background; 0 reset.
    """
    if params == "":
        codes = [0]
    else:
        codes = [int(p or 0) for p in params.split(";") if p != ""]

    # Work on a copy
    new_fmt = QTextCharFormat(fmt)

    for code in codes:
        if code == 0:
            new_fmt = QTextCharFormat()  # reset
        elif 30 <= code <= 37:
            # standard foreground
            color_map = {
                30: QColor("#000000"),
                31: QColor("#e03131"),  # red
                32: QColor("#2f9e44"),  # green
                33: QColor("#f08c00"),  # yellow
                34: QColor("#1971c2"),  # blue
                35: QColor("#9c36b5"),  # magenta
                36: QColor("#0c8599"),  # cyan
                37: QColor("#f8f9fa"),  # white
            }
            new_fmt.setForeground(color_map.get(code, QColor("#f8f9fa")))
        elif 90 <= code <= 97:
            # bright foreground
            bright_map = {
                90: QColor("#868e96"),  # bright black (gray)
                91: QColor("#ff6b6b"),
                92: QColor("#51cf66"),
                93: QColor("#ffd43b"),
                94: QColor("#4dabf7"),
                95: QColor("#da77f2"),
                96: QColor("#63e6be"),
                97: QColor("#ffffff"),
            }
            new_fmt.setForeground(bright_map.get(code, QColor("#ffffff")))
        elif 40 <= code <= 47:
            # background colors
            bg_map = {
                40: QColor("#000000"),
                41: QColor("#661515"),
                42: QColor("#0f3b1d"),
                43: QColor("#5f3c00"),
                44: QColor("#102b5c"),
                45: QColor("#4b1c5e"),
                46: QColor("#0b3b42"),
                47: QColor("#ced4da"),
            }
            new_fmt.setBackground(bg_map.get(code, QColor("#000000")))
        # 1: bold 等可以视需要加，这里先忽略
    return new_fmt


class ShellReader(QObject):
    data_ready = Signal(str)
    closed = Signal()

    def __init__(self, ssh_client):
        super().__init__()
        self.ssh_client = ssh_client
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        while self._running:
            try:
                chunk = self.ssh_client.shell_recv()
                if chunk:
                    self.data_ready.emit(chunk)
            except Exception:
                break
            QThread.msleep(5)
        self.closed.emit()


class ServerTerminalView(QTextEdit):
    """Interactive SSH terminal with basic ANSI color rendering."""
    def __init__(self, ssh_client=None):
        super().__init__()
        self.ssh_client = ssh_client
        self.setReadOnly(True)
        self.setAcceptRichText(False)
        self.setUndoRedoEnabled(False)

        # 可调字号：用 _font_size + _apply_font_style 管理
        self._font_size = 11
        self._base_style = (
            "QTextEdit { background-color: #000000; color: #f8f9fa; "
            "font-family: Consolas, 'Cascadia Mono', 'DejaVu Sans Mono', monospace; "
        )
        self._apply_font_style()

        self.reader_thread: QThread | None = None
        self.reader: ShellReader | None = None
        self._connected = False
        self._current_format = QTextCharFormat()
        self._append_text("Disconnected\n")
    
    def _apply_font_style(self):
        """根据当前字号刷新样式和 QFont（覆盖全局 QSS 的 font-size）。"""
        style = self._base_style + f"font-size: {self._font_size}pt; }}"
        self.setStyleSheet(style)
        font = self.font()
        font.setPointSize(self._font_size)
        self.setFont(font)

    def adjust_font_size(self, delta: int):
        """根据增量调整字号，限制在 8–32pt 区间。"""
        new_size = max(8, min(32, self._font_size + delta))
        if new_size == self._font_size:
            return
        self._font_size = new_size
        self._apply_font_style()
    def set_connected(self, connected: bool, banner: str):
        if connected:
            self.start_shell()
        else:
            self._connected = False
            self._stop_reader()
            self._append_text("\nDisconnected\n")

    def start_shell(self):
        try:
            self.ssh_client.open_shell()
        except Exception as e:
            self._append_text(f"Shell error: {e}\n")
            return

        self.clear()
        self._connected = True
        self._current_format = QTextCharFormat()

        self.reader_thread = QThread()
        self.reader = ShellReader(self.ssh_client)
        self.reader.moveToThread(self.reader_thread)
        self.reader_thread.started.connect(self.reader.run)
        self.reader.data_ready.connect(self._append_text)
        self.reader.closed.connect(self._on_remote_closed)
        self.reader_thread.start()

    def _stop_reader(self):
        if self.reader:
            self.reader.stop()
        if self.reader_thread:
            self.reader_thread.quit()
            self.reader_thread.wait(200)
        self.reader = None
        self.reader_thread = None

    def _on_remote_closed(self):
        self._append_text("\n[remote shell closed]\n")
        self._stop_reader()

    
    
    def _append_text(self, text: str):
        """Append text with basic ANSI color support and strip unsupported CSI codes.

        - 保留普通文本和颜色（SGR）
        - 处理退格字符（\b, DEL，以及 ^?/^H 文本形式），避免出现删除符号乱码
        - 处理清屏 CSI（ESC[2J / ESC[H），用于 top/htop 等全屏程序
        """
        if not text:
            return

        def _normalize_backspace(s: str) -> str:
            s = s.replace("^?", "\b").replace("^H", "\b")
            buf = []
            for ch in s:
                if ch in ("\b", "\x7f"):
                    if buf:
                        buf.pop()
                        continue
                buf.append(ch)
            return "".join(buf)

        # 在 _append_text 里面：
        text = OSC_PATTERN.sub("", text)
        text = _normalize_backspace(text)
        text = text.replace("\x07", "")
        text = text.replace("\x1b(B", "")
        text = text.replace("\n", "")
        text = text.replace("\r", "\n")

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)

        pos = 0
        while pos < len(text):
            m = CSI_PATTERN.search(text, pos)
            if not m:
                chunk = text[pos:]
                if chunk:
                    cursor.insertText(chunk, self._current_format)
                break

            if m.start() > pos:
                chunk = text[pos:m.start()]
                if chunk:
                    cursor.insertText(chunk, self._current_format)

            params = m.group(1) or ""
            final = m.group(2)

            if final == "m":
                # SGR 颜色 / 重置
                self._current_format = apply_sgr_to_format(self._current_format, params)
            elif final == "J":
                # 清屏：仅对 ESC[2J 进行整屏清除，避免干扰普通 prompt
                if params == "2":
                    self.clear()
                    cursor = self.textCursor()
                    cursor.movePosition(QTextCursor.End)

            # 其它 CSI（光标移动等）暂时忽略

            pos = m.end()

        self.setTextCursor(cursor)
        self.ensureCursorVisible()
    def mouseReleaseEvent(self, event):
        """Left-button selection -> auto copy to clipboard."""
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton:
            cursor = self.textCursor()
            if cursor.hasSelection():
                text = cursor.selectedText()
                if text:
                    # QTextEdit uses U+2029 for line breaks in selectedText
                    text = text.replace("\u2029", "\n")
                    QGuiApplication.clipboard().setText(text)


    def mouseDoubleClickEvent(self, event):
        """双击时按自定义规则选择一整块内容：以空格和 '$' 为分隔符，'.', '-', '+' 视为单词一部分。"""
        cursor = self.cursorForPosition(event.pos())
        pos = cursor.position()
        doc = self.toPlainText()
        n = len(doc)
        if n == 0:
            return QTextEdit.mouseDoubleClickEvent(self, event)

        separators = set(" \t\r\n$")
        left = pos
        while left > 0 and doc[left - 1] not in separators:
            left -= 1
        right = pos
        while right < n and doc[right] not in separators:
            right += 1

        new_cursor = self.textCursor()
        new_cursor.setPosition(left)
        new_cursor.setPosition(right, QTextCursor.KeepAnchor)
        self.setTextCursor(new_cursor)

        # 同时复制到剪贴板（与 mouseReleaseEvent 行为一致）
        text = new_cursor.selectedText()
        if text:
            text = text.replace("\u2029", "\n")
            QGuiApplication.clipboard().setText(text)
    def contextMenuEvent(self, event):
        """Right-click -> paste clipboard content into remote shell."""
        if self._connected and self.ssh_client is not None and self.ssh_client.channel is not None:
            text = QGuiApplication.clipboard().text()
            if text:
                text = text.replace("\r\n", "\n")
                try:
                    self.ssh_client.shell_send(text)
                except Exception:
                    pass
        else:
            # fall back to default behavior if not connected
            super().contextMenuEvent(event)

    def wheelEvent(self, event):
        """Ctrl + 滚轮缩放终端字体；不按 Ctrl 时保持原始滚动。"""
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta == 0:
                event.accept()
                return
            step = 1 if abs(delta) < 240 else 2
            if delta > 0:
                self.adjust_font_size(step)
            else:
                self.adjust_font_size(-step)
            event.accept()
        else:
            super().wheelEvent(event)

   

    def focusNextPrevChild(self, next: bool) -> bool:
        """禁止 Tab / Shift+Tab 在控件间切换焦点，由终端自身处理。"""
        return False

    def keyPressEvent(self, event: QKeyEvent):
        if not self._connected or self.ssh_client is None or self.ssh_client.channel is None:
            return

        key = event.key()
        text = event.text()

        try:
            # 基本控制键
            if key in (Qt.Key_Return, Qt.Key_Enter):
                self.ssh_client.shell_send("\r")
                return
            if key == Qt.Key_Backspace:
                self.ssh_client.shell_send("\x7f")
                return
            if key == Qt.Key_Tab:
                self.ssh_client.shell_send("\t")
                event.accept()
                return

            # 方向键
            
            if key == Qt.Key_Up:
                self.ssh_client.shell_send("\x1b[A")
                return
            if key == Qt.Key_Down:
                self.ssh_client.shell_send("\x1b[B")
                return
            if key == Qt.Key_Right:
                self.ssh_client.shell_send("\x1b[C")
                return
            if key == Qt.Key_Left:
                self.ssh_client.shell_send("\x1b[D")
                return

            # Home / End
            if key == Qt.Key_Home:
                self.ssh_client.shell_send("\x1b[H")
                return
            if key == Qt.Key_End:
                self.ssh_client.shell_send("\x1b[F")
                return

            # PageUp / PageDown 交给 QTextEdit 自己处理（滚动）
            if key in (Qt.Key_PageUp, Qt.Key_PageDown):
                return QTextEdit.keyPressEvent(self, event)

            # Ctrl+C 中断前台程序
            if key == Qt.Key_C and (event.modifiers() & Qt.ControlModifier):
                self.ssh_client.shell_send("\x03")
                return

            # 其它可见字符
            if text:
                self.ssh_client.shell_send(text)
        except Exception:
            return