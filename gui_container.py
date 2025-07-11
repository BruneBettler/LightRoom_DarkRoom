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
        self.initialized = False
        self.data_manager = DataManager()
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # show the camera_indices dialog to set the camera indices
        dialog = OnsetCameraSetupDialog(parent=self.central_widget, data_manager=self.data_manager)
        dialog_output = dialog.exec_()

        if dialog_output == 0: 
            QApplication.quit()
            return      

        """
        Camera widgets
        """
        self.camera_widget = CameraControlWidget(self.data_manager)
        
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
        central_layout.addWidget(self.camera_widget)
        central_layout.addLayout(global_widgets_layout)
        self.central_widget.setLayout(central_layout)

        self.initialized = True
        
    # may need to add a close event here where we call the camera widget to close
    def closeEvent(self, event):
        self.camera_widget.close()
        event.accept()
         