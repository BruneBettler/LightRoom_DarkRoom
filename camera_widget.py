from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import *
from data_manager import *
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, QThread
import cv2
from PyQt5.QtGui import QImage, QPixmap
from picamera2 import Picamera2, Preview
import time

class CameraWidget(QWidget):
    def __init__(self, room_name, camera_name, data_manager):
        super().__init__()
        self.camera = PiCameraHandler(camera_name)
        self.data_manager = data_manager

        layout = QVBoxLayout()
        # add a "title" for this camera widget 
        layout.addWidget(QLabel(f"{room_name}: {camera_name}"))

        layout.addWidget(self.camera)

        self.camera_viewer = CameraViewer()
        layout.addWidget(self.camera_viewer)

        # Connect signal for frame updates
        self.camera_handler.new_frame.connect(self.camera_viewer.update_image)

        # Add camera controls (example)
        btn_start = QPushButton("Start Live View")
        btn_stop = QPushButton("Stop Live View")
        btn_start.clicked.connect(self.start_live)
        btn_stop.clicked.connect(self.stop_live)

        #btn_record_start.clicked.connect(lambda: self.camera_handler.start_recording("/path/to/video.h264"))
        #btn_record_stop.clicked.connect(self.camera_handler.stop_recording)


        layout.addWidget(btn_start)
        layout.addWidget(btn_stop)

        self.setLayout(layout)

        def start_live(self):
            self.camera_handler.start_camera()

        def stop_live(self):
            self.camera_handler.stop_camera()

class CameraViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.label = QLabel("Camera Viewer")
        self.label.setScaledContents(True)
        layout = QHBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

        # picam2.camera_controls

    def update_image(self, frame):
        """
        Converts OpenCV frame to QPixmap and displays it.
        """
        # Picamera2 frame is RGB
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qt_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_img)
        self.label.setPixmap(pixmap)


class PiCameraHandler(QObject):
    """
    Handles a single Pi Camera using OpenCV VideoCapture.
    Streams video frames and exposes controls for settings.
    """
    new_frame = pyqtSignal(np.ndarray)

    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index = camera_index
        self.picam2 = None
        self.timer = None
        self.is_recording = False

    def start_camera(self):
        # Find all cameras and pick the desired one
        all_cams = Picamera2.global_camera_info()
        if len(all_cams) <= self.camera_num:
            print(f"No camera found at index {self.camera_num}")
            return

        # Open the chosen camera
        self.picam2 = Picamera2(camera_num=self.camera_num)

        # Configure preview (you can adjust size etc.)
        config = self.picam2.create_preview_configuration(main={"size": (640, 480)})
        self.picam2.configure(config)
        self.picam2.start()

        # Create a timer to grab frames periodically
        self.timer = QTimer()
        self.timer.timeout.connect(self._emit_frame)
        self.timer.start(30)  # ~30 fps

    def _emit_frame(self):
        frame = self.picam2.capture_array()
        self.new_frame.emit(frame)

        if self.is_recording:
            self.picam2.record_video_frame()

    def stop_camera(self):
        if self.timer:
            self.timer.stop()
        if self.picam2:
            self.picam2.stop()

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
            self.is_recording = False



