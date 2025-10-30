from PyQt5.QtCore import QSize, Qt, QTime, QDate, QTimer
from PyQt5.QtWidgets import *
from data_manager import *
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from PyQt5.QtGui import QImage, QPixmap
from picamera2 import Picamera2
from picamera2.previews.qt import QGlPicamera2
import time
from pathlib import Path

class SavePathWidget(QWidget):
    """
    A widget to select and display the final save path of captured  videos.
    """
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.dialog = QFileDialog()
        # configure dialog to select directories only
        self.dialog.setFileMode(QFileDialog.Directory)
        self.dialog.setOption(QFileDialog.ShowDirsOnly, True)

        self.directory_edit = QLineEdit()
        self.directory_edit.setEnabled(False)

        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self.open_file_dialog)
        
        layout = QHBoxLayout()
        save_path_label = QLabel("Save Path:")

        layout.addWidget(save_path_label)
        layout.addWidget(self.directory_edit)
        layout.addWidget(self.browse_btn)

        self.setLayout(layout)

    def open_file_dialog(self):
        directory = self.dialog.getExistingDirectory(self, "Select Save Directory")
        if directory:
            self.path = Path(directory)
            self.directory_edit.setText(str(self.path))
            self.data_manager.set_save_path(self.path)

class RecordingControlerWidget(QWidget):
    """
    A widget that allows user to start and stop the video recordings. 
    """
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.start_time = None
        
        self.stop_method_combo = QComboBox()
        self.stop_method_combo.addItems(["Manual", "Timer"])
        self.stop_method_combo.setCurrentText(self.data_manager.stop_method)
        self.stop_method_combo.currentTextChanged.connect(self.update_stop_method)
        stop_method_label = QLabel("Recording stop method:")
        stop_method_layout = QHBoxLayout()
        stop_method_layout.addWidget(stop_method_label)
        stop_method_layout.addWidget(self.stop_method_combo)

        self.start_time_label = QLabel(f"Recording start time: ")
        self.data_manager.start_time_updated.connect(lambda Qstart_time_dict: self.update_start_label(Qstart_time_dict)) 

        self.start_stop_btn = QPushButton("Start Recording")
        self.start_stop_btn.setObjectName("start_stop_btn")
        self.start_stop_btn.setStyleSheet("#start_stop_btn {background-color: green; }")
        self.start_stop_btn.clicked.connect(self.start_stop_toggled)
        self.start_stop_btn.setEnabled(False)
        self.data_manager.save_path_updated.connect(lambda: self.start_stop_btn.setEnabled(True))

        self.timer_widget = QDoubleSpinBox(parent=self)
        self.timer_widget.setRange(1.0, 60.0)
        self.timer_widget.setValue(5.0)
        self.timer_widget.setSingleStep(5.0)
        self.timer_widget.setDecimals(1)
        self.timer_widget.valueChanged.connect(lambda value: self.data_manager.set_timer_duration(value))
        self.timer_label = QLabel("Set recording time (min):", parent=self)
        self.timer_layout = QHBoxLayout()
        self.timer_layout.addWidget(self.timer_label)
        self.timer_layout.addWidget(self.timer_widget)
        self.timer_label.hide()
        self.timer_widget.hide()

        layout = QGridLayout()
        layout.addLayout(stop_method_layout, 0,0, 1,2)
        layout.addLayout(self.timer_layout, 1, 0, 1, 1)
        layout.addWidget(self.start_time_label, 1, 1, 1, 1)
        layout.addWidget(self.start_stop_btn, 2, 0, 1, 2)

        self.setLayout(layout)

        self.data_manager.timer_timeout.connect(self.handle_timer_timeout)

    def update_start_label(self, Qtime_dict):
        text = "Recording start time: "
        for room, qtime in Qtime_dict.items():
            if qtime != None:
                text += f"{room}: {qtime.toString('HH:mm:ss')} "
        self.start_time_label.setText(text)

    def handle_timer_timeout(self):
        self.start_stop_btn.setText("Start Recording")
        self.start_stop_btn.setStyleSheet("#start_stop_btn {background-color: green; }")

        self.start_time_label.setText(f"Recording start time: ") # rest the label

    def start_stop_toggled(self):
        """
        Start/Stop/Abort the recording process.
        """
        print(self.data_manager.is_running.values())
        if False in self.data_manager.is_running.values(): # we're now going to start the recording
            self.data_manager.set_start_date(QDate.currentDate()) # in case someone is doing recordings in the evening between midnight and 1am
            if self.data_manager.stop_method == "Manual":
                self.start_stop_btn.setText("Stop Recording")
            elif self.data_manager.stop_method == "Timer":
                self.start_stop_btn.setText("Abort Recording")
            self.start_stop_btn.setStyleSheet("#start_stop_btn {background-color: red; }")
        elif True in self.data_manager.is_running.values(): # we're stopping or aborting the recording 
            # if timer is on, first make sure the user truly wants to stop the recording
            if self.data_manager.stop_method == "Timer":
                reply = QMessageBox.question(self,
                    "Abort Timed Recording","A timer is running. Are you sure you want to abort the recording?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No) # options, yes and no with default = no
                if reply == QMessageBox.No:
                    return  # Do not abort
            self.start_stop_btn.setText("Start Recording")
            self.start_stop_btn.setStyleSheet("#start_stop_btn {background-color: green; }")

            self.start_time_label.setText(f"Recording start time: ") # rest the label

        self.data_manager.start_stop_toggled_signal.emit()  

    def update_stop_method(self, method):
        if method == "Manual":
            self.timer_widget.hide()
            self.timer_label.hide()
            self.data_manager.set_timer_duration(None)
        else: # method == "Timer":
            self.timer_widget.show()
            self.timer_label.show()
            self.data_manager.set_timer_duration(self.timer_widget.value())

        self.data_manager.set_stop_method(method)

class OnsetCameraSetupDialog(QDialog):
    def __init__(self, parent, data_manager):
        super().__init__(parent)
        self.data_manager = data_manager
        self.default_LR_index = 0
        self.default_DR_index = 1
        self.setWindowTitle("Camera Setup")

        # Create widgets
        self.LR_label = QLabel("LightRoom camera port index:")
        self.LR_edit = QLineEdit()
        self.LR_edit.setText(str(self.default_LR_index))  # default value
        self.LR_check = QCheckBox("Use LightRoom cam")
        self.LR_check.setChecked(True)
        self.LR_check.stateChanged.connect(lambda state: self.toggle_room_cam("LightRoom", state))  

        self.DR_label = QLabel("DarkRoom camera port index:")
        self.DR_edit = QLineEdit()
        self.DR_edit.setText(str(self.default_DR_index))  # default value
        self.DR_check = QCheckBox("Use DarkRoom cam")
        self.DR_check.setChecked(True) 
        self.DR_check.stateChanged.connect(lambda state: self.toggle_room_cam("DarkRoom", state))

        self.set_button = QPushButton("Set")
        self.set_button.clicked.connect(self.set_data)

        # Layout
        layout = QGridLayout()
        layout.addWidget(self.LR_check, 0, 0)
        layout.addWidget(self.LR_label, 0, 1)
        layout.addWidget(self.LR_edit, 0, 2)
        layout.addWidget(self.DR_label, 1, 1)
        layout.addWidget(self.DR_edit, 1, 2)
        layout.addWidget(self.DR_check, 1, 0)
        layout.addWidget(self.set_button, 2, 0, 1, 3)

        self.setLayout(layout)

    def toggle_room_cam(self, room, state):
        if room == "LightRoom":
            input_data = self.LR_edit
            default = self.default_LR_index
        elif room == "DarkRoom":
            input_data = self.DR_edit
            default = self.default_DR_index

        if state == Qt.Checked:
            input_data.setEnabled(True)
            input_data.setText(str(default))  # default value
        else:
            input_data.setText("")
            input_data.setEnabled(False)

    def set_data(self):
        valid_inputs = {"LightRoom": False, "DarkRoom": False} 
        visible_cam_indices = [cam['Num'] for cam in Picamera2.global_camera_info()]
        
        if [self.LR_edit.text(), self.DR_edit.text()] == ["", ""]: # both cameras unselected
            QMessageBox.warning(self, "At least one camera must be selected", "Please select at least one camera to proceed.")
        
        else: # check that the user input is valid
            for room, input_cam_i in zip(["LightRoom", "DarkRoom"], [self.LR_edit.text(), self.DR_edit.text()]):
                if input_cam_i != "":
                    if int(input_cam_i) in visible_cam_indices:
                        self.data_manager.camera_settings[room]['disp_num'] = int(input_cam_i)
                        self.data_manager.is_running[room] = False  # rather than None
                        valid_inputs[room] = True
                    else:
                        QMessageBox.warning(self, "Camera Setup", f"No valid PiCam found at index {input_cam_i} for {room} camera.")
                        valid_inputs[room] = False
                else:
                    valid_inputs[room] = None
        
        if False not in valid_inputs.values(): # both cameras are valid
            self.accept()