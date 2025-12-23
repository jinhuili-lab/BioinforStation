from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QLineEdit, QPushButton, QFrame, QSplitter, QProgressBar, QApplication, QStyle
from PySide6.QtCore import Qt, QTimer, QObject, QThread, Signal, QSize
from PySide6.QtGui import QShortcut, QKeySequence
import re
from bioflow.core.ssh_client import SSHClient
from bioflow.ui.server_terminal_view import ServerTerminalView
from bioflow.ui.server_files_view import ServerFilesView
from bioflow.ui.server_jobs_view import ServerJobsView
from bioflow.ui.server_plugins_view import ServerPluginsView
from bioflow.ui.splitter import CollapsibleSplitter

class ConnectWorker(QObject):
    finished = Signal(str, bool, str)

    def __init__(self, ssh_client, host, port, user, password):
        super().__init__()
        self.ssh_client = ssh_client
        self.host = host
        self.port = port
        self.user = user
        self.password = password

    def run(self):
        label = ""
        banner = ""
        ok = False
        try:
            self.ssh_client.connect(host=self.host, port=self.port, username=self.user, password=self.password)
            label = f"{self.user}@{self.host}:{self.port}"
            try:
                out, err, code = self.ssh_client.exec("echo 'Last login:' $(whoami)'@'$(hostname); pwd")
                banner = out + "\n"
            except Exception:
                banner = f"Connected to {label}\n"
            ok = True
        except Exception:
            label = "Connection failed"
            banner = ""
            ok = False
        self.finished.emit(label, ok, banner)

class ServerView(QWidget):
    def __init__(self):
        super().__init__()
        self.ssh_client = SSHClient()
        self.connect_thread = None
        self.connect_worker = None
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(8)
        self.main_splitter = CollapsibleSplitter(Qt.Vertical)
        self._build_top_panel()
        self._build_bottom_panel()
        self.main_splitter.setSizes([110, 700])
        root_layout.addWidget(self.main_splitter)

        # F11 快捷键切换终端全屏模式
        self.fullscreen_shortcut = QShortcut(QKeySequence(Qt.Key_F11), self)
        self.fullscreen_shortcut.activated.connect(self._toggle_fullscreen)

        # Metrics timer for resource usage
        self.metrics_timer = QTimer(self)
        self.metrics_timer.setInterval(5000)
        self.metrics_timer.timeout.connect(self._update_metrics)
        self._last_net_rx = None
        self._last_net_tx = None

    def _build_top_panel(self):
        self.top_panel = top = QWidget()
        layout = QVBoxLayout(top)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header_row = QHBoxLayout()
        title = QLabel("HPC / Servers")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        self.status_label = QLabel("Disconnected")
        self.status_label.setStyleSheet("color: #6B7280;")

        # small status LED on the right
        self.status_led = QLabel()
        self.status_led.setFixedSize(10, 10)
        self._set_status_led(False)

        header_row.addWidget(title)
        header_row.addStretch(1)
        header_row.addWidget(self.status_label)
        header_row.addSpacing(4)
        header_row.addWidget(self.status_led)
        layout.addLayout(header_row)

        conn_card = QFrame()
        conn_card.setObjectName("ConnCard")
        conn_card.setStyleSheet(
            "QFrame#ConnCard { background-color: #FFFFFF; border-radius: 12px; border: 1px solid #E5E7EB; }"
        )
        conn_layout = QHBoxLayout(conn_card)
        conn_layout.setContentsMargins(8, 4, 8, 4)
        conn_layout.setSpacing(8)

        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("Host")
        self.port_edit = QLineEdit()
        self.port_edit.setPlaceholderText("Port")
        self.port_edit.setText("22")
        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("Username")
        self.pass_edit = QLineEdit()
        self.pass_edit.setPlaceholderText("Password")
        self.pass_edit.setEchoMode(QLineEdit.Password)

        self.connect_btn = QPushButton("Connect")
        self.disconnect_btn = QPushButton("Disconnect")


        # Files panel toggle button with folder icon
        self.toggle_files_btn = QPushButton()
        self.toggle_files_btn.setToolTip("Toggle remote file browser")
        self.toggle_files_btn.setFixedWidth(32)
        folder_icon = self.style().standardIcon(QStyle.SP_DirIcon)
        self.toggle_files_btn.setIcon(folder_icon)
        self.toggle_files_btn.setIconSize(QSize(22, 22))
        self.toggle_files_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; padding: 2px; } "
            "QPushButton:hover { background: rgba(148,163,184,0.35); border-radius: 4px; }"
        )

        # Terminal font zoom out button (-)
        self.zoom_out_btn = QPushButton("–")
        self.zoom_out_btn.setToolTip("Decrease terminal font size")
        self.zoom_out_btn.setFixedWidth(28)
        self.zoom_out_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; padding: 0 4px; "
            "font-size: 18px; font-weight: 600; } "
            "QPushButton:hover { background: rgba(148,163,184,0.35); border-radius: 4px; }"
        )

        # Terminal font zoom in button (+)
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setToolTip("Increase terminal font size")
        self.zoom_in_btn.setFixedWidth(28)
        self.zoom_in_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; padding: 0 4px; "
            "font-size: 18px; font-weight: 600; } "
            "QPushButton:hover { background: rgba(148,163,184,0.35); border-radius: 4px; }"
        )

        # Fullscreen toggle button (terminal)
        self.fullscreen_btn = QPushButton()
        self.fullscreen_btn.setToolTip("Toggle fullscreen window")
        self.fullscreen_btn.setFixedWidth(32)
        fs_icon = self.style().standardIcon(QStyle.SP_TitleBarMaxButton)
        self.fullscreen_btn.setIcon(fs_icon)
        self.fullscreen_btn.setIconSize(QSize(20, 20))
        self.fullscreen_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; padding: 2px; } "
            "QPushButton:hover { background: rgba(148,163,184,0.35); border-radius: 4px; }"
        )

        conn_layout.addWidget(self.host_edit)
        conn_layout.addWidget(self.port_edit)
        conn_layout.addWidget(self.user_edit)
        conn_layout.addWidget(self.pass_edit)
        conn_layout.addWidget(self.connect_btn)
        conn_layout.addWidget(self.disconnect_btn)
        conn_layout.addWidget(self.toggle_files_btn)
        conn_layout.addWidget(self.zoom_out_btn)
        conn_layout.addWidget(self.zoom_in_btn)
        conn_layout.addWidget(self.fullscreen_btn)
        layout.addWidget(conn_card)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setMaximumHeight(8)
        layout.addWidget(self.progress)

        self.connect_btn.clicked.connect(self.connect_server)
        self.disconnect_btn.clicked.connect(self.disconnect_server)
        self.toggle_files_btn.clicked.connect(self.toggle_files)
        self.zoom_out_btn.clicked.connect(lambda: self._change_terminal_font(-1))
        self.zoom_in_btn.clicked.connect(lambda: self._change_terminal_font(1))
        self.fullscreen_btn.clicked.connect(self._toggle_fullscreen)

        # allow pressing Enter in password field (and others) to trigger connect
        self.host_edit.returnPressed.connect(self.connect_server)
        self.port_edit.returnPressed.connect(self.connect_server)
        self.user_edit.returnPressed.connect(self.connect_server)
        self.pass_edit.returnPressed.connect(self.connect_server)

        self.main_splitter.addWidget(top)

    def _build_bottom_panel(self):
        self.bottom_panel = bottom = QWidget()
        layout = QVBoxLayout(bottom)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.inner_splitter = QSplitter(Qt.Horizontal)

        # left: terminal
        left_side = QWidget()
        left_layout = QVBoxLayout(left_side)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self.terminal_tab = ServerTerminalView(self.ssh_client)
        left_layout.addWidget(self.terminal_tab)

        # right: remote files
        self.files_view = ServerFilesView(self.ssh_client)

        self.inner_splitter.addWidget(left_side)
        self.inner_splitter.addWidget(self.files_view)

        # default: hide files, terminal full width
        self.files_view.setVisible(False)
        self.inner_splitter.setSizes([1, 0])

        layout.addWidget(self.inner_splitter)

        # bottom resource/status bar
        self.resource_bar = QWidget()
        bar_layout = QHBoxLayout(self.resource_bar)
        bar_layout.setContentsMargins(4, 0, 4, 0)
        bar_layout.setSpacing(8)
        self.resource_bar.setMaximumHeight(22)

        # monitor toggle button (default off)
        self.monitor_enabled = False
        self.monitor_btn = QPushButton()
        self.monitor_btn.setCheckable(True)
        self.monitor_btn.setToolTip("Toggle resource monitor")
        cpu_icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
        self.monitor_btn.setIcon(cpu_icon)
        self.monitor_btn.setIconSize(QSize(18, 18))
        self.monitor_btn.setFixedHeight(18)
        self.monitor_btn.clicked.connect(self._toggle_monitor)
        self.monitor_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; padding: 2px; color: #9CA3AF; } "
            "QPushButton:hover { background: rgba(148,163,184,0.25); border-radius: 4px; } "
            "QPushButton:checked { color: #10B981; }"
        )

        bar_layout.addWidget(self.monitor_btn)

        self.session_label = QLabel("Server: -")
        self.cpu_label = QLabel("CPU: -")
        self.mem_label = QLabel("Mem: -")
        self.net_up_label = QLabel("Up: -")
        self.net_down_label = QLabel("Down: -")

        for w in (self.session_label, self.cpu_label, self.mem_label, self.net_up_label, self.net_down_label):
            w.setStyleSheet("font-size: 11px;")
            bar_layout.addWidget(w)

        bar_layout.addStretch(1)
        layout.addWidget(self.resource_bar)
        self.main_splitter.addWidget(bottom)
    
    def _change_terminal_font(self, delta: int):
        """调整终端字号，delta 为正数放大，为负数缩小。"""
        if not hasattr(self, "terminal_tab"):
            return
        # 统一用 ServerTerminalView.adjust_font_size，保证和 Ctrl+滚轮一致
        self.terminal_tab.adjust_font_size(delta)

    def _toggle_fullscreen(self):
        win = self.window()
        if not hasattr(self, "_is_fullscreen"):
            self._is_fullscreen = False
            self._saved_sidebar_sizes = None

        # 找主窗口里的 CollapsibleSplitter（左侧 sidebar + 右侧内容）
        splitter = None
        try:
            splitters = win.findChildren(CollapsibleSplitter)
            if splitters:
                splitter = splitters[0]
        except Exception:
            splitter = None

        if self._is_fullscreen:
            # 退出全屏
            win.showNormal()
            self._is_fullscreen = False

            if hasattr(self, "top_panel"):
                self.top_panel.setVisible(True)
            if hasattr(self, "files_view"):
                self.files_view.setVisible(True)
            if hasattr(self, "resource_bar"):
                self.resource_bar.setVisible(True)
            if hasattr(self, "inner_splitter"):
                self.inner_splitter.setSizes([1, 1])

            # 恢复 sidebar 宽度
            if splitter is not None and getattr(self, "_saved_sidebar_sizes", None):
                splitter.setSizes(self._saved_sidebar_sizes)
        else:
            # 进入全屏，仅保留终端黑色区域
            win.showFullScreen()
            self._is_fullscreen = True

            if hasattr(self, "top_panel"):
                self.top_panel.setVisible(False)
            if hasattr(self, "files_view"):
                self.files_view.setVisible(False)
            if hasattr(self, "resource_bar"):
                self.resource_bar.setVisible(False)
            if hasattr(self, "inner_splitter"):
                self.inner_splitter.setSizes([1, 0])

            # 折叠左侧 sidebar
            if splitter is not None:
                sizes = splitter.sizes()
                total = sum(sizes) or 1
                self._saved_sidebar_sizes = sizes
                splitter.setSizes([0, total])
    def connect_server(self):
        host = self.host_edit.text().strip()
        port_text = self.port_edit.text().strip()
        user = self.user_edit.text().strip()
        password = self.pass_edit.text()
        if not host or not user or not port_text:
            return
        try:
            port = int(port_text)
        except ValueError:
            return

        # show indeterminate progress until connection completes
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.progress.setValue(0)
        QApplication.processEvents()

        if self.connect_thread is not None:
            return

        self.connect_thread = QThread()
        self.connect_worker = ConnectWorker(self.ssh_client, host, port, user, password)
        self.connect_worker.moveToThread(self.connect_thread)
        self.connect_thread.started.connect(self.connect_worker.run)
        self.connect_worker.finished.connect(self._on_connected)
        self.connect_worker.finished.connect(self.connect_thread.quit)
        self.connect_worker.finished.connect(self.connect_worker.deleteLater)
        self.connect_thread.finished.connect(self._cleanup_thread)
        self.connect_thread.start()

    def _cleanup_thread(self):
        if self.connect_thread is not None:
            self.connect_thread.deleteLater()
        self.connect_thread = None
        self.connect_worker = None

    def _stop_progress_bar(self):
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(False)

    def _on_connected(self, label: str, ok: bool, banner: str):
        # hide progress bar when connection attempt finishes
        self._stop_progress_bar()

        if ok:
            self.status_label.setText(label)
            self._set_status_led(True)
            self.terminal_tab.set_connected(True, banner)
            self.files_view.load_root()
            self.session_label.setText(f"Server: {label}")
            # toggle connect/disconnect icons
            self.connect_btn.setVisible(False)
            self.disconnect_btn.setVisible(True)
        else:
            self.status_label.setText(label)
            self._set_status_led(False)
            self.terminal_tab.set_connected(False, banner)
            self.files_view.load_root()
            self.session_label.setText("Server: -")
            self.connect_btn.setVisible(True)
            self.disconnect_btn.setVisible(False)
            self._stop_metrics()

    def _set_status_led(self, connected: bool):
        if not hasattr(self, 'status_led') or self.status_led is None:
            return
        color = '#10B981' if connected else '#EF4444'
        self.status_led.setStyleSheet(f'background-color: {color}; border-radius: 5px;')

    def _start_metrics(self):
        if not self.monitor_enabled:
            return
        self._last_net_rx = None
        self._last_net_tx = None
        self.metrics_timer.start()

    def _stop_metrics(self):
        self.metrics_timer.stop()
        self.cpu_label.setText('CPU: -')
        self.mem_label.setText('Mem: -')
        self.net_up_label.setText('Up: -')
        self.net_down_label.setText('Down: -')

    def _toggle_monitor(self):
        # manual toggle by user; default is off
        self.monitor_enabled = self.monitor_btn.isChecked()
        if self.monitor_enabled and getattr(self.ssh_client, 'client', None):
            self._start_metrics()
        else:
            self._stop_metrics()
    def _update_metrics(self):
        """Lightweight resource polling using /proc; avoids heavy 'top' calls."""
        if not getattr(self.ssh_client, 'client', None):
            return

        # --- CPU: from /proc/loadavg (1-min load) ---
        try:
            out_load, _, _ = self.ssh_client.exec("cat /proc/loadavg")
            parts = out_load.strip().split()
            load1 = float(parts[0]) if parts else 0.0
            self.cpu_label.setText(f"CPU(load1): {load1:.2f}")
        except Exception:
            self.cpu_label.setText("CPU: -")

        # --- Memory: from /proc/meminfo ---
        try:
            out_mem, _, _ = self.ssh_client.exec("grep -E 'MemTotal:|MemAvailable:' /proc/meminfo")
            mem_total_kb = mem_avail_kb = None
            for line in out_mem.splitlines():
                if line.startswith("MemTotal:"):
                    mem_total_kb = float(line.split()[1])
                elif line.startswith("MemAvailable:"):
                    mem_avail_kb = float(line.split()[1])
            if mem_total_kb and mem_avail_kb is not None:
                used_kb = mem_total_kb - mem_avail_kb
                mem_pct = used_kb / mem_total_kb * 100.0
                self.mem_label.setText(f"Mem: {mem_pct:.0f}%")
            else:
                self.mem_label.setText("Mem: -")
        except Exception:
            self.mem_label.setText("Mem: -")

        # --- Network: from /proc/net/dev ---
        try:
            out_net, _, _ = self.ssh_client.exec("cat /proc/net/dev")
            rx = tx = None
            for line in out_net.splitlines()[2:]:  # skip headers
                line = line.strip()
                if not line or ':' not in line:
                    continue
                iface, data = line.split(':', 1)
                iface = iface.strip()
                if iface == 'lo':
                    continue
                fields = data.split()
                if len(fields) >= 9:
                    rx = int(fields[0])
                    tx = int(fields[8])
                    break
            if rx is not None and tx is not None:
                if self._last_net_rx is not None and self._last_net_tx is not None:
                    interval = self.metrics_timer.interval() / 1000.0
                    delta_rx = max(rx - self._last_net_rx, 0)
                    delta_tx = max(tx - self._last_net_tx, 0)
                    down_rate = delta_rx / interval
                    up_rate = delta_tx / interval
                    self.net_down_label.setText(f"Down: {down_rate / (1024*1024):.2f} MB/s")
                    self.net_up_label.setText(f"Up: {up_rate / (1024*1024):.2f} MB/s")
                self._last_net_rx = rx
                self._last_net_tx = tx
        except Exception:
            self.net_down_label.setText("Down: -")
            self.net_up_label.setText("Up: -")
    def disconnect_server(self):
        self.ssh_client.close()
        self.status_label.setText('Disconnected')
        self._set_status_led(False)
        self.terminal_tab.set_connected(False, '')
        self.files_view.load_root()
        self.session_label.setText('Server: -')
        # toggle back to connect icon
        self.connect_btn.setVisible(True)
        self.disconnect_btn.setVisible(False)
        self._stop_metrics()
        self._stop_progress_bar()

    def toggle_files(self):
        visible = self.files_view.isVisible()
        if visible:
            self.files_view.setVisible(False)
            self.inner_splitter.setSizes([1, 0])
        else:
            self.files_view.setVisible(True)
            total = max(self.inner_splitter.width(), 1)
            main = int(total * 0.7)
            side = max(total - main, 1)
            self.inner_splitter.setSizes([main, side])