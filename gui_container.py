from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import *
from data_manager import *
from camera_widget import *

class MainWindow(QMainWindow):
    """
    The main GUI window contains two large panels with each showing 
    the live view of the noir and global shutter camera respectively 
    """
    def __init__(self):
        super().__init__()
        self.data_manager = DataManager()

        self.lightRoomCam_widget = CameraWidget("Light Room", "Global Shutter Cam", None, self.data_manager)
        self.darkRoomCam_widget = CameraWidget("Dark Room", "PiNoir Cam", None, self.data_manager)

        self.setWindowTitle("LightRoom-DarkRoom") 
        self.setMinimumSize(QSize(700,400)) 

        central_widget = QWidget()

        central_layout = QHBoxLayout()
        central_layout.addWidget(self.lightRoomCam_widget)
        central_layout.addWidget(self.darkRoomCam_widget)
        central_widget.setLayout(central_layout)
        
        self.setCentralWidget(central_widget)