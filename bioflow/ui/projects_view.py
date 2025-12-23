from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QTextEdit, QSplitter, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt

class ProjectsView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(8)
        header = QHBoxLayout()
        title = QLabel("Projects")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        new_btn = QPushButton("New Project")
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(new_btn)
        layout.addLayout(header)
        splitter = QSplitter(Qt.Horizontal)
        self.project_list = QListWidget()
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setText("Select a project to see details.")
        splitter.addWidget(self.project_list)
        splitter.addWidget(self.details)
        splitter.setSizes([260, 700])
        layout.addWidget(splitter)
