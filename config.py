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

# function allowing opening and saving configuration json files 


# function widget that allows changing the configs (displayed as popup in the container)
class ConfigPopup(QDialog):
    def __init__(self, data_manager, cam_widget, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Cam {cam_widget.CamDisp_num}: Configuration settings")
        self.data_manager = data_manager
        self.cam = cam_widget.picam

        self.main_layout = QGridLayout()

        # frame rate (fps): take in int value
            #   int(100,0000 / fps) = frame duration limits
            # frame duration limits: max and min time that the sensor can take to deliver a frame, measured in microseconds. reciprocal of these values (first divided by 1000000) will give the min and max framerates that sensor can deliver
        self.frame_rate_intbox = QSpinBox()
        self.frame_rate_intbox.setValue(self._get_fps(self.cam.camera_controls['FrameDurationLimits'][2]))
        self.frame_rate_intbox.setRange(self._get_fps(self.cam.camera_controls['FrameDurationLimits'][0]), self._get_fps(self.cam.camera_controls['FrameDurationLimits'][1]))
        self.main_layout.addWidget(QLabel("Frame rate (fps): "), 0,0,1,1)
        self.main_layout.addWidget(self.frame_rate_intbox, 0,1,1,1)

        # exposure time: Exposure time for the sensor to use, measured in microseconds
        self.exposure_time_doublebox = QDoubleSpinBox()
        self.exposure_time_doublebox.setRange(self.cam.camera_controls['ExposureTime'][0], self.cam.camera_controls['ExposureTime'][1])
        self.exposure_time_doublebox.setValue(self.cam.camera_controls['ExposureTime'][2])
        self.main_layout.addWidget(QLabel("Exposure time (μs): "), 1,0,1,1)
        self.main_layout.addWidget(self.exposure_time_doublebox, 1,1,1,1)

        # lens position: position of lens in units of diopters (1/meters)
        self.lens_position_doublebox = QDoubleSpinBox()
        self.lens_position_doublebox.setRange(self.cam.camera_controls['LensPosition'][0], self.cam.camera_controls['LensPosition'][1])
        self.lens_position_doublebox.setValue(self.cam.camera_controls['LensPosition'][2])
        self.main_layout.addWidget(QLabel("Lens position (dpt): "), 2,0,1,1)
        self.main_layout.addWidget(self.lens_position_doublebox, 2,1,1,1)

        # scaler crop: rectangle that determines which part of the image received from sensor is cropped then scaled to produce an output image of the correct size. can be used to implement digital pan and zoom. coordinate are always given from within the full sensor resolution. x_offset, y_offset, w, h
        # have this be in a label and then have a button to select the region on the preview.
        # TODO: 

        # analog gain: analogue gain applied by the sensor
        self.analogue_gain_check = QCheckBox("Analogue gain: ")
        self.analogue_gain_check.setChecked(False)
        self.analogue_gain_doublebox = QDoubleSpinBox()
        self.analogue_gain_doublebox.setRange(self.cam.camera_controls['AnalogueGain'][0], self.cam.camera_controls['AnalogueGain'][1])
        self.analogue_gain_doublebox.setValue(self.cam.camera_controls['AnalogueGain'][2])
        self.main_layout.addWidget(self.analogue_gain_check, 4,0,1,1)
        self.main_layout.addWidget(self.analogue_gain_doublebox, 4,1,1,1)

        # brightness: adjusts the image brightness -1 very dark 1 very bright and 0.0 is normal / default
            # double to change brightness
        self.brightness_doublebox = QDoubleSpinBox()
        self.brightness_doublebox.setRange(self.cam.camera_controls['Brightness'][0], self.cam.camera_controls['Brightness'][1])
        self.brightness_doublebox.setValue(self.cam.camera_controls['Brightness'][2])
        self.main_layout.addWidget(QLabel("Brightness: "), 5,0,1,1)
        self.main_layout.addWidget(self.brightness_doublebox, 5,1,1,1)

        self.set_btn = QPushButton("Set")
        self.set_save_btn = QPushButton("Set & Save")
        self.main_layout.addWidget(QLabel("Current configuration: "), 6,0,2,1)
        self.main_layout.addWidget(self.set_btn, 6,1,1,1)
        self.main_layout.addWidget(self.set_save_btn, 7,1,1,1)
        
        self.setLayout(self.main_layout)
    
    def _get_fps(self, frame_duration_limit):
        # returns the int fps given an input frame_duration_limit in microseconds
        return int(1000000/frame_duration_limit)


class ConfigSetupWidget(QWidget):
    def __init__(self, data_manager, cam):
        super().__init__()
        self.data_manager = data_manager
        self.setFixedSize(int((self.data_manager.main_window_size['W']-30)/2), int(self.data_manager.main_window_size['H']*3/18))
        self.cam = cam

        layout = QGridLayout()

        current_config_label = QLabel("Currrent configuration: ")
        self.current_config_edit = QLineEdit("default")
        self.current_config_edit.setEnabled(False) # we just want it for visualization

        self.modify_view_btn = QPushButton("View/modify config")
        self.modify_view_btn.clicked.connect(self.cam.config_pop)
        self.load_btn = QPushButton("Load config")

        layout.addWidget(current_config_label, 0,0,1,1)
        layout.addWidget(self.current_config_edit, 0,1,1,1)
        layout.addWidget(self.load_btn, 0,2,1,1)
        layout.addWidget(self.modify_view_btn, 1,0,1,1)
        

        self.setLayout(layout)
