from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import *
from data_manager import *
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from PyQt5.QtGui import QImage, QPixmap
from picamera2 import Picamera2
from picamera2.previews.qt import QGlPicamera2
from picamera2.encoders import H264Encoder
import time
from pathlib import Path
import os

class CameraWidget(QWidget): 
    def __init__(self, room_name, CamDisp_num, data_manager):
        super().__init__()
        self.CamDisp_num = CamDisp_num # find number on the physical pi, port number where the camera is inserted
        self.room_name = room_name
        self.data_manager = data_manager
        self.layout = QVBoxLayout()
        # add a "title" for this camera widget 
        self.layout.addWidget(QLabel(f"{self.room_name} Camera: port {CamDisp_num}"))


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

        self.data_manager.start_time_updated.connect(self.picam.start_stop_recording)


    def start_stop_recording(self):
        """
        Start, stop, or abort the camera recording.
        """ 
        if not self.data_manager.is_running[self.CamDisp_num]: # start the recording
            # stop the preview before starting the recording
            self.start_stop_preview(False)
            video_config = self.picam.create_video_configuration() # TODO: update this from the data_manager code
            self.picam.configure(video_config)
            encoder = H264Encoder(bitrate=10000000)
            start_time = QTime.currentTime()
            self.data_manager.set_start_time(self.CamDisp_num, start_time)
            save_path = os.path.join(self.data_manager.save_path, f"camera_{self.CamDisp_num}_{self.room_name}_{start_time}.h264")
            self.data_manager.set_is_running(True)
            print(f"Starting Camera {self.CamDisp_num} recording at {start_time.toString("hh:mm:ss")}")
            self.picam.start_recording(encoder, save_path)
        else:
            self.picam.stop_recording()
            self.data_manager.set_is_running(self.CamDisp_num, False)
            print(f"Camera {self.CamDisp_num} recording stopped at {QTime.currentTime().toString("hh:mm:ss")}")
            self.start_stop_preview(True)

    def start_stop_preview(self, start_preview):
        """
        Start or stop the camera preview.
        :param start_preview: Boolean indicating whether to start or stop the preview
        """
        if start_preview:
            self.picam.start()
            self.picam_preview_widget.show()
        else:
            self.picam.stop()
            self.picam_preview_widget.hide()

    def closeEvent(self, event):
        print(f"Safely closing Camera {self.CamDisp_num}")
        self.picam.stop()
        self.picam_preview_widget.close()
        event.accept()



