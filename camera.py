from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import *
from data_manager import *
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from PyQt5.QtGui import QImage, QPixmap
from picamera2 import Picamera2
from picamera2.previews.qt import QGlPicamera2
import time
from pathlib import Path

class CameraWidget(QWidget): 
    def __init__(self, room_name, CamDisp_num, data_manager):
        super().__init__()
        self.CamDisp_num = CamDisp_num # find number on the physical pi, port number where the camera is inserted
        self.data_manager = data_manager
        self.layout = QVBoxLayout()
        # add a "title" for this camera widget 
        self.layout.addWidget(QLabel(f"{room_name} Camera: port {CamDisp_num}"))


        self.picam = None
        self.picam_preview_widget = None

        # Find all cameras and pick the desired one
        all_cams = Picamera2.global_camera_info()
        for cam in all_cams:
            if cam['Num'] == self.CamDisp_num:
                self.picam = Picamera2(camera_num=self.CamDisp_num)
                # Configure preview (you can adjust size etc.)
                config = self.picam.create_preview_configuration()
                self.picam.configure(config)
                self.picam_preview_widget = QGlPicamera2(self.picam)
                break
        if self.picam is None:
            print(f"No camera found at index {self.CamDisp_num}")
            return

        self.layout.addWidget(self.picam_preview_widget)

        """
        Add camera controls widgets (always available on GUI screen)
        """
        self.lens_position_widget = QDoubleSpinBox()
        min_diop, max_diop, default_diop = self.picam.camera_controls["LensPosition"]
        self.lens_position_widget.setRange(min_diop, max_diop)
        self.lens_position_widget.setValue(default_diop)
        self.lens_position_widget.setSingleStep(0.1)
        

        self.setLayout(self.layout)

        self.picam.start()
        self.picam_preview_widget.show()

    def closeEvent(self, event):
        print(f"Safely closing Camera {self.CamDisp_num}")
        self.picam.stop()
        self.picam_preview_widget.close()
        event.accept()



