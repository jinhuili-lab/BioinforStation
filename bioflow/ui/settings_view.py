from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFormLayout, QLineEdit, QPushButton, QComboBox
from PySide6.QtCore import Signal

class SettingsView(QWidget):
    theme_changed = Signal(str)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        title = QLabel("Settings")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        layout.addWidget(title)
        form = QFormLayout()
        self.default_workspace = QLineEdit()
        self.account_email = QLineEdit()
        self.theme_selector = QComboBox()
        self.theme_selector.addItem("Light", "light")
        self.theme_selector.addItem("Dark", "dark")
        self.theme_selector.addItem("Teal", "teal")
        self.theme_selector.addItem("Graphite", "graphite")
        self.theme_selector.addItem("Solarized", "solarized")
        self.theme_selector.addItem("Nord", "nord")
        form.addRow("Default workspace", self.default_workspace)
        form.addRow("Account email", self.account_email)
        form.addRow("Theme", self.theme_selector)
        layout.addLayout(form)
        save_btn = QPushButton("Save")
        layout.addWidget(save_btn)
        layout.addStretch(1)
        self.theme_selector.currentIndexChanged.connect(self.emit_theme_change)

    def emit_theme_change(self, index):
        value = self.theme_selector.itemData(index)
        self.theme_changed.emit(value)
