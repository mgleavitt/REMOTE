"""Simple test application to verify PySide6 is working correctly.

This module creates a basic GUI window to test that PySide6 is properly installed and functioning.
"""
# pylint: disable=no-name-in-module, import-error, trailing-whitespace
import sys
from PySide6.QtWidgets import (
    QApplication,
    QWidget, 
    QLabel,
    QVBoxLayout
)

app = QApplication(sys.argv)
window = QWidget()
window.setWindowTitle("PySide6 Test")
layout = QVBoxLayout()
label = QLabel("PySide6 is working!")
layout.addWidget(label)
window.setLayout(layout)
window.setMinimumSize(300, 200)
window.show()
sys.exit(app.exec())
