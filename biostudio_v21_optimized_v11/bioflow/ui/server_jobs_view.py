from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QHBoxLayout, QPushButton

class ServerJobsView(QWidget):
    def __init__(self, ssh_client=None):
        super().__init__()
        self.ssh_client = ssh_client
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        header = QHBoxLayout()
        header.addWidget(QLabel("Jobs"))
        self.refresh_btn = QPushButton("Refresh")
        header.addStretch(1)
        header.addWidget(self.refresh_btn)
        layout.addLayout(header)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Job ID", "Name", "State", "Time"])
        layout.addWidget(self.table)
