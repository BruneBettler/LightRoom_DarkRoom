from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import *
from data_manager import *
from camera import *
from global_widgets import *

class MainWindow(QMainWindow):
    """
    The main GUI window contains two large panels with each showing 
    the live view of the noir and global shutter camera respectively 
    """
    def __init__(self):
        super().__init__()
        self.data_manager = DataManager()

        """
        Camera widgets
        """
        #self.lightRoomCam_widget = CameraWidget("Light Room", 1, self.data_manager)
        self.darkRoomCam_widget = CameraWidget("Dark Room", 1, self.data_manager)
        
        camera_layout = QHBoxLayout()
        #camera_layout.addWidget(self.lightRoomCam_widget)
        camera_layout.addWidget(self.darkRoomCam_widget)

        """
        Global widgets
        """

        self.save_dialog_widget = SavePathWidget(self.data_manager)
        self.recording_control_widget = RecordingControlerWidget(self.data_manager)

        global_widgets_layout = QVBoxLayout()
        global_widgets_layout.addWidget(self.save_dialog_widget)
        global_widgets_layout.addWidget(self.recording_control_widget)  

        """
        Main Window 
        """
        self.setWindowTitle("LightRoom-DarkRoom") 
        self.setFixedSize(QSize(1500,1000)) 
        central_layout = QVBoxLayout()
        central_layout.addLayout(camera_layout)
        central_layout.addLayout(global_widgets_layout)
        central_widget = QWidget()
        central_widget.setLayout(central_layout)
        
        self.setCentralWidget(central_widget)
    
    def closeEvent(self, event):
        """
        Close the camera widgets when the main window is closed.
        """
        #self.lightRoomCam_widget.close()
        self.darkRoomCam_widget.close()
        event.accept()  