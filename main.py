import sys
from gui_container import *


if __name__ == "__main__":
    LightRoomDarkRoom_GUI = QApplication([])
    mainwindow = MainWindow()
    mainwindow.show()
    sys.exit(LightRoomDarkRoom_GUI.exec_())