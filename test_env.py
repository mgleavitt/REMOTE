"""Simple test application to verify PySide6 is working correctly.

This module creates a basic GUI window to test that PySide6 is properly installed and functioning.
"""
# pylint: disable=no-name-in-module, import-error, trailing-whitespace, line-too-long
import sys
from PySide6.QtWidgets import (
    QApplication,
    QWidget, 
    QLabel,
    QVBoxLayout
)

# Create the application
app = QApplication(sys.argv)

# Create and configure the main window
window = QWidget()
window.setWindowTitle("PySide6 Test")

# Create and configure the layout
layout = QVBoxLayout()
label = QLabel("PySide6 is working!")
layout.addWidget(label)
window.setLayout(layout)
window.setMinimumSize(300, 200)

# Display the window and start the event loop
window.show()
sys.exit(app.exec())
