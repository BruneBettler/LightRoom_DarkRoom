"""
Main window GUI container for LightRoom DarkRoom application.

Provides the primary window interface that contains camera preview widgets,
recording controls, and save path configuration. Manages application layout
and initialization.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import *
from data_manager import *
from camera import *
from global_widgets import *
from config import *


class MainWindow(QMainWindow):
    """
    Main application window with dual camera previews and recording controls.
    
    Initializes data manager, camera widgets, and control widgets. Shows
    camera setup dialog on startup and manages application lifecycle.
    """
    
    def __init__(self):
        super().__init__()
        self.initialized = False
        self.data_manager = DataManager()
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        dialog = OnsetCameraSetupDialog(parent=self.central_widget, data_manager=self.data_manager)
        dialog_output = dialog.exec_()

        if dialog_output == 0: 
            QApplication.quit()
            return      

        self.camera_widget = CameraControlWidget(self.data_manager)
        self.save_dialog_widget = SavePathWidget(self.data_manager)
        self.recording_control_widget = RecordingControlerWidget(self.data_manager)

        global_widgets_layout = QVBoxLayout()
        global_widgets_layout.addWidget(self.save_dialog_widget)
        global_widgets_layout.addWidget(self.recording_control_widget)

        self.setWindowTitle("LightRoom-DarkRoom") 
        self.main_window_size_H = self.data_manager.main_window_size['H'] 
        self.main_window_size_W = self.data_manager.main_window_size['W']  
        self.resize(self.main_window_size_W, self.main_window_size_H)
        self.setMinimumSize(int(self.main_window_size_W * 0.6), int(self.main_window_size_H * 0.6))
        
        central_layout = QVBoxLayout()
        self.camera_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.camera_widget.setMinimumHeight(int(self.main_window_size_H*1/4))
        central_layout.addWidget(self.camera_widget, 3)
        central_layout.addLayout(global_widgets_layout, 1)
        self.central_widget.setLayout(central_layout)

        self.initialized = True
        
    def closeEvent(self, event):
        """Clean up camera widgets on window close."""
        self.camera_widget.close()
        event.accept()

    def open_manage_configs(self):
        """Placeholder for removed Manage Configs feature."""
        return