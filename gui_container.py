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

        self.lightRoomCam_widget = CameraWidget("Light Room", 0, self.data_manager)
        self.darkRoomCam_widget = CameraWidget("Dark Room", 1, self.data_manager)

        self.setWindowTitle("LightRoom-DarkRoom") 
        self.setFixedSize(QSize(1500,1000)) 

        central_widget = QWidget()

        central_layout = QHBoxLayout()
        central_layout.addWidget(self.lightRoomCam_widget)
        central_layout.addWidget(self.darkRoomCam_widget)
        central_widget.setLayout(central_layout)
        
        self.setCentralWidget(central_widget)
    
    def closeEvent(self, event):
        """
        Close the camera widgets when the main window is closed.
        """
        self.lightRoomCam_widget.close()
        self.darkRoomCam_widget.close()
        event.accept()  