from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import *
from data_manager import *
from camera import *
from global_widgets import *
from config import *

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

    # (Manage Configs button removed)

        """
        Main Window 
        """
        self.setWindowTitle("LightRoom-DarkRoom") 
        # QSize is (W, H)
        self.main_window_size_H = self.data_manager.main_window_size['H'] 
        self.main_window_size_W = self.data_manager.main_window_size['W']  
        # allow the window to be resizable; set a reasonable minimum size
        self.resize(self.main_window_size_W, self.main_window_size_H)
        self.setMinimumSize(int(self.main_window_size_W * 0.6), int(self.main_window_size_H * 0.6))
        central_layout = QVBoxLayout()
        # allow camera widget to expand; set a reasonable (smaller) minimum height
        # reduce the minimum so the preview can shrink when the window is resized
        self.camera_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.camera_widget.setMinimumHeight(int(self.main_window_size_H*1/4))
        # give camera area most of the vertical space; global widgets get less
        central_layout.addWidget(self.camera_widget, 3)
        central_layout.addLayout(global_widgets_layout, 1)
        self.central_widget.setLayout(central_layout)

        self.initialized = True
        
    # may need to add a close event here where we call the camera widget to close
    def closeEvent(self, event):
        self.camera_widget.close()
        event.accept()

    def open_manage_configs(self):
        # Manage Configs feature removed
        return
         