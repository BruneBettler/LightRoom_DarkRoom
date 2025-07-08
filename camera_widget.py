from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import *
from data_manager import *
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, QThread
import cv2
from PyQt5.QtGui import QImage, QPixmap
from picamera2 import Picamera2, Preview
from picamera2.previews.qt import QGlPicamera2
import time

class CameraWidget(QWidget): 
    def __init__(self, room_name, CamDisp_num, data_manager):
        super().__init__()
        self.CamDisp_num = CamDisp_num # find number on the physical pi, port number where the camera is inserted
        self.data_manager = data_manager
        self.picam = None
        self.picam_preview_widget = None

        # Find all cameras and pick the desired one
        all_cams = Picamera2.global_camera_info()
        for cam in all_cams:
            if cam['Num'] == self.CamDisp_num:
                self.picam = Picamera2(camera_num=self.CamDisp_num)
                # Configure preview (you can adjust size etc.)
                config = self.picam.create_preview_configuration(main={"size": (640, 480)})
                self.picam.configure(config)
                self.picam_preview_widget = QGlPicamera2(self.picam)
                break
        if self.picam is None:
            print(f"No camera found at index {self.CamDisp_num}")
            return


        layout = QVBoxLayout()
        # add a "title" for this camera widget 
        layout.addWidget(QLabel(f"{room_name}: Camera port {CamDisp_num}"))

        layout.addWidget(self.picam_preview_widget)

        # Connect signal for frame updates
        #self.camera_handler.new_frame.connect(self.camera_viewer.update_image)

        # Add camera controls (example)
        btn_start = QPushButton("Start Live View")
        btn_stop = QPushButton("Stop Live View")
        btn_start.clicked.connect(self.start_preview)
        btn_stop.clicked.connect(self.stop_preview)

        #btn_record_start.clicked.connect(lambda: self.camera_handler.start_recording("/path/to/video.h264"))
        #btn_record_stop.clicked.connect(self.camera_handler.stop_recording)


        layout.addWidget(btn_start)
        layout.addWidget(btn_stop)

        self.setLayout(layout)

    def start_preview(self):
        self.picam.start()

    def stop_preview(self):
        if self.picam:
            self.picam.stop()
            self.picam_preview_widget.close()
            self.picam_preview_widget = None



        

        """# Create a timer to grab frames periodically
        self.timer = QTimer()
        self.timer.timeout.connect(self._emit_frame)
        self.timer.start(30)  # ~30 fps

    def _emit_frame(self):
        frame = self.picam2.capture_array()
        self.new_frame.emit(frame)

        if self.is_recording:
            self.picam2.record_video_frame()

    

    def set_exposure(self, exposure_us):
        # exposure_us in microseconds
        self.picam2.set_controls({"ExposureTime": int(exposure_us)})

    def set_focus(self, lens_position):
        # lens_position: 0.0 - infinity
        self.picam2.set_controls({"LensPosition": float(lens_position)})

    def set_frame_rate(self, fps):
        self.picam2.set_controls({"FrameRate": float(fps)})

    def start_recording(self, filepath):
        # Start video recording to file (H.264 or other supported formats)
        self.picam2.start_recording(filepath)
        self.is_recording = True

    def stop_recording(self):
        if self.is_recording:
            self.picam2.stop_recording()
            self.is_recording = False"""



