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
from picamera2 import Picamera2


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

        # Automatically detect both cameras (indices 0 and 1)
        # Exit with error if both cameras are not available
        visible_cam_indices = [cam['Num'] for cam in Picamera2.global_camera_info()]
        
        if 0 not in visible_cam_indices or 1 not in visible_cam_indices:
            QMessageBox.critical(
                None, 
                "Camera Error", 
                f"Both cameras (indices 0 and 1) are required.\n\n"
                f"Available cameras: {visible_cam_indices}\n\n"
                f"Please ensure both cameras are connected and try again."
            )
            QApplication.quit()
            return
        
        # Set up both cameras automatically
        self.data_manager.camera_settings["LightRoom"]['disp_num'] = 0
        self.data_manager.camera_settings["DarkRoom"]['disp_num'] = 1
        self.data_manager.is_running["LightRoom"] = False
        self.data_manager.is_running["DarkRoom"] = False

        self.camera_widget = CameraControlWidget(self.data_manager)
        self.save_dialog_widget = SavePathWidget(self.data_manager)
        self.recording_control_widget = RecordingControlerWidget(self.data_manager)

        # Pass the control widgets to camera_widget for new layout
        self.camera_widget.set_control_widgets(self.save_dialog_widget, self.recording_control_widget)

        self.setWindowTitle("LightRoom-DarkRoom") 
        self.main_window_size_H = self.data_manager.main_window_size['H'] 
        self.main_window_size_W = self.data_manager.main_window_size['W']  
        self.resize(self.main_window_size_W, self.main_window_size_H)
        self.setMinimumSize(int(self.main_window_size_W * 0.6), int(self.main_window_size_H * 0.6))
        
        central_layout = QVBoxLayout()
        self.camera_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        central_layout.addWidget(self.camera_widget, 1)
        self.central_widget.setLayout(central_layout)

        self.initialized = True
        
    def closeEvent(self, event):
        """Clean up camera widgets on window close."""
        self.camera_widget.close()
        event.accept()

    def open_manage_configs(self):
        """Placeholder for removed Manage Configs feature."""
        return