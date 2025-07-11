from PyQt5.QtCore import QSize, Qt, QTimer
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

class Camera(QWidget): 
    def __init__(self, data_manager, CamDisp_num):
        super().__init__()
        self.CamDisp_num = CamDisp_num # find number on the physical pi, port number where the camera is inserted
        self.data_manager = data_manager
        self.preview_off_widget = QWidget(styleSheet="background-color: black;", parent=self)

        # Find all cameras and pick the desired one
        self.picam = Picamera2(self.CamDisp_num)
        self.picam_preview_widget = None 

     
        """
        Add camera controls widgets (always available on GUI screen)
        """
        self.lens_position_widget = QDoubleSpinBox()
        min_diop, max_diop, default_diop = self.picam.camera_controls["LensPosition"]
        self.lens_position_widget.setRange(min_diop, max_diop)
        self.lens_position_widget.setValue(default_diop)
        self.lens_position_widget.setSingleStep(0.1)

    def initialize_preview(self):
        # Configure preview (you can adjust size etc.)
        config = self.picam.create_preview_configuration()
        self.picam.configure(config)
        self.picam_preview_widget = QGlPicamera2(self.picam, parent=self)

    def closeEvent(self, event):
        print(f"Safely closing Camera {self.CamDisp_num}")
        self.picam.stop()
        self.picam_preview_widget.close()
        event.accept()

class CameraControlWidget(QWidget):    
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.record_timer = QTimer(self)
        self.record_timer.setSingleShot(True)
        self.record_timer.timeout.connect(self.handle_timer_timeout)
        
        camera_layout = QHBoxLayout()
        # determine which cameras to show based on the data_manager settings
        self.camera_widgets = {}

        for room in ["LightRoom", "DarkRoom"]: 
            # check if the camera is set to be displayed
            if self.data_manager.camera_settings[room]['disp_num'] is not None:
                # add to the camera_widgets dictionary
                self.camera_widgets[room] = Camera(self.data_manager, self.data_manager.camera_settings[room]['disp_num'])
                layout = QVBoxLayout()
                layout.addWidget(QLabel(f"{room} Camera: port {self.data_manager.camera_settings[room]['disp_num']}"))
                layout.addWidget(self.camera_widgets[room])
                camera_layout.addLayout(layout)
        
        self.setLayout(camera_layout)        
        self.start_stop_preview(True)

        self.data_manager.start_stop_toggled.connect(self.start_stop_recording)
    
 
    
    def start_stop_recording(self):
        """
        Start, stop, or abort the camera recording.
        """
        for i, (room, cam) in enumerate(self.camera_widgets.items()):
            if self.data_manager.is_running[room]:  # currently running so turn it off
                cam.picam.stop_recording()
                self.data_manager.set_is_running(room, False)
                if self.record_timer.isActive():
                    print("Timer stopped early")
                    self.record_timer.stop()
                print(f"Stopped {room} cam recording at {QTime.currentTime().toString('HH:mm:ss')}")
                self.start_stop_preview(True)
            else:  # not running so turn it on
                if i == 0:
                    # only need to call this once since it applies to all cameras
                    self.start_stop_preview(False)
                video_config = cam.picam.create_video_configuration()  # TODO: update this from the data_manager code
                cam.picam.configure(video_config)
                encoder = H264Encoder(bitrate=10000000)
                start_time = QTime.currentTime()
                self.data_manager.set_start_time(room, start_time)
                save_path = os.path.join(self.data_manager.save_path, f"{room}_cam_{start_time.toString('HH:mm:ss')}.h264")
                self.data_manager.set_is_running(room, True)
                print(f"Started {room} cam recording at {start_time.toString('HH:mm:ss')}")

                if self.data_manager.stop_method == "Timer":
                    self.set_timer()

                cam.picam.start_recording(encoder, save_path)
                # in both cases, update the elapsed time label
    def set_timer(self):
        duration_min = self.data_manager.timer_duration
        duration_ms = int(float(duration_min) * 60 * 1000)
        self.record_timer.start(duration_ms)
        print(f"Timer started for {duration_min} minute(s)") 

    def handle_timer_timeout(self):
        print("Timer finished, stopping all recordings.")
        self.data_manager.timer_timeout.emit() # changes the recording button text and resets the timer label
        for room, cam in self.camera_widgets.items():
            cam.picam.stop_recording()
            self.data_manager.set_is_running(room, False)
            self.start_stop_preview(True)

    def start_stop_preview(self, start_preview):
        """
        Start or stop the camera preview.
        :param start_preview: Boolean indicating whether to start or stop the preview
        """
        if start_preview:
            for room, cam in self.camera_widgets.items():
                cam.initialize_preview()
                cam.picam.start()
                cam.picam_preview_widget.show()
        else:
            for room, cam in self.camera_widgets.items():
                cam.picam.stop()
                cam.picam_preview_widget.deleteLater()
                cam.picam_preview_widget = cam.preview_off_widget
                cam.picam_preview_widget.show()


    def closeEvent(self, event):
        for room, cam in self.camera_widgets.items():
            cam.close()
        event.accept() 

    