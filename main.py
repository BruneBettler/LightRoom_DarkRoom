"""
LightRoom DarkRoom dual camera recording application entry point.

This script initializes and runs the PyQt5-based GUI application for controlling
and recording from two Raspberry Pi cameras simultaneously.
"""

import sys
from gui_container import *


if __name__ == "__main__":
    LightRoomDarkRoom_GUI = QApplication([])
    mainwindow = MainWindow()
    if mainwindow.initialized:
        mainwindow.setWindowTitle("LightRoom-DarkRoom")
        mainwindow.show()
        sys.exit(LightRoomDarkRoom_GUI.exec_())