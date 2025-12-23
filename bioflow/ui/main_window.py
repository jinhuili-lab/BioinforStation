import os
from PySide6.QtWidgets import QMainWindow, QListWidget, QListWidgetItem, QStackedWidget, QStatusBar, QApplication
from PySide6.QtCore import Qt
from bioflow.ui.home_view import HomeView
from bioflow.ui.server_view import ServerView
from bioflow.ui.projects_view import ProjectsView
from bioflow.ui.plugins_market_view import PluginsView
from bioflow.ui.local_tools_view import LocalToolsView
from bioflow.ui.settings_view import SettingsView
from bioflow.ui.splitter import CollapsibleSplitter

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BioFlow Desktop")
        self.resize(1360, 840)
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(190)
        self.stack = QStackedWidget()
        self.splitter = CollapsibleSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.sidebar)
        self.splitter.addWidget(self.stack)
        self.splitter.setSizes([190, 1100])
        self.setCentralWidget(self.splitter)
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.home_view = HomeView()
        self.local_tools_view = LocalToolsView()
        self.server_view = ServerView()
        self.projects_view = ProjectsView()
        self.plugins_view = PluginsView()
        self.settings_view = SettingsView()
        self.settings_view.theme_changed.connect(self.apply_theme)
        self.stack.addWidget(self.home_view)
        self.stack.addWidget(self.local_tools_view)
        self.stack.addWidget(self.server_view)
        self.stack.addWidget(self.projects_view)
        self.stack.addWidget(self.plugins_view)
        self.stack.addWidget(self.settings_view)
        items = [
            "Home",
            "Local Tools",
            "HPC / Servers",
            "Projects",
            "Plugins",
            "Settings",
        ]
        for text in items:
            item = QListWidgetItem(text)
            self.sidebar.addItem(item)
        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.sidebar.setCurrentRow(0)
        self.status.showMessage("Ready")
        self.apply_theme("light")

    def apply_theme(self, theme_name: str):
        app = QApplication.instance()
        if not app:
            return
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        mapping = {
            "light": "theme_light.qss",
            "dark": "theme_dark.qss",
            "teal": "theme_teal.qss",
            "graphite": "theme_graphite.qss",
            "solarized": "theme_solarized.qss",
            "nord": "theme_nord.qss",
        }
        theme_file = mapping.get(theme_name, "theme_light.qss")
        path = os.path.join(root_dir, theme_file)
        try:
            with open(path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
        except Exception:
            return
