from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem

class ServerPluginsView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        layout.addWidget(QLabel("Available HPC Plugins"))
        self.list = QListWidget()
        item = QListWidgetItem("No plugins loaded")
        self.list.addItem(item)
        layout.addWidget(self.list)
