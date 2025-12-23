from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout, QPushButton, QSizePolicy

class LocalToolsView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        title = QLabel("Local Tools")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        layout.addWidget(title)
        grid = QGridLayout()
        grid.setSpacing(16)
        tools = [
            "Sequence Tools",
            "Primer Design",
            "Plotting",
            "Local Pipelines",
            "QC Viewer",
            "Genome Tools",
        ]
        cols = 6
        for i, text in enumerate(tools):
            tile = QPushButton(text)
            tile.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            tile.setMinimumHeight(140)
            tile.setStyleSheet(
                "QPushButton { text-align: left; padding: 18px; font-size: 15px; "
                "font-weight: 500; background-color: #FFFFFF; color: #111827; border-radius: 16px; border: 1px solid #E5E7EB; } "
                "QPushButton:hover { background-color: #EEF2FF; }"
            )
            row = i // cols
            col = i % cols
            grid.addWidget(tile, row, col)
        layout.addLayout(grid)
        layout.addStretch(1)
