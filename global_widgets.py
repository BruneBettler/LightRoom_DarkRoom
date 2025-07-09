from PyQt5.QtCore import QSize, Qt, QTime, QDate
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
        self.dialog.FileMode(QFileDialog.FileMode.Directory)
        self.dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)

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
    
            # TODO: self.data_manager.set_save_path(self.CamDisp_num, directory)

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
        self.stop_method_combo.currentTextChanged.connect(self.update_stop_method)
        stop_method_label = QLabel("Recording stop method:")
        stop_method_layout = QHBoxLayout()
        stop_method_layout.addWidget(stop_method_label)
        stop_method_layout.addWidget(self.stop_method_combo)

        self.increment_timer_label = QLabel(f"Time elapsed (M:S): 000:00")

        self.start_btn = QPushButton("Start Recording")
        self.start_btn.clicked.connect(self.start_stop_recording)

        self.timer_widget = QDoubleSpinBox(parent=self)
        self.timer_widget.setRange(1.0, 60.0)
        self.timer_widget.setValue(5.0)
        self.timer_widget.setSingleStep(5.0)
        self.timer_widget.setDecimals(1)
        self.timer_label = QLabel("Set recording time (min):", parent=self)
        self.timer_layout = QHBoxLayout()
        self.timer_layout.addWidget(self.timer_label)
        self.timer_layout.addWidget(self.timer_widget)
        self.timer_label.hide()
        self.timer_widget.hide()

        layout = QGridLayout()
        layout.addLayout(stop_method_layout, 0,0, 1,2)
        layout.addLayout(self.timer_layout, 1, 0, 1, 1)
        layout.addWidget(self.increment_timer_label, 1, 1, 1, 1)
        layout.addWidget(self.start_btn, 2, 0, 1, 2)

        self.setLayout(layout)

    def start_stop_recording(self):
        """
        Start/Stop/Abort the recording process.
        """
        if not self.data_manager.is_running:
            self.data_manager.is_running = True
            self.data_manager.start_time = QTime.currentTime()
            self.data_manager.start_date = QDate.currentDate() # in case someone is doing recordings in the evening between midnight and 1am
            if self.data_manager.stop_method == "Manual":
                self.start_btn.setText("Stop Recording")
            elif self.data_manager.stop_method == "Timer":
                self.start_btn.setText("Abort Recording")
                self.increment_timer_label.setText(f"Time remaining (M:S): {self.data_manager.get_timer_duration()}")
        else: # we're stopping or aborting the recording 
            self.data_manager.is_running = False
            self.start_btn.setText("Start Recording")
            if self.data_manager.stop_method == "Manual":
                self.increment_timer_label.setText(f"Time elapsed (M:S): 000:00")
            elif self.data_manager.stop_method == "Timer":
                self.increment_timer_label.setText(f"Time remaining (M:S): {self.data_manager.get_timer_duration()}")

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