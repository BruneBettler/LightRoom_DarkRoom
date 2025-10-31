"""
Global UI widgets for LightRoom DarkRoom application.

Provides reusable widget components for recording control, countdown timers,
camera setup dialogs, and save path selection. These widgets are shared
across the application interface.
"""

from PyQt5.QtCore import Qt, QTime, QTimer, pyqtSignal
from PyQt5.QtWidgets import *
from data_manager import *
from picamera2 import Picamera2
from pathlib import Path


class SavePathWidget(QWidget):
    """
    Widget for selecting and displaying video save directory.
    
    Provides a file dialog to browse for save location and displays
    the selected path in a read-only text field.
    """
    
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.dialog = QFileDialog()
        
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
        """Open directory selection dialog and update save path."""
        directory = self.dialog.getExistingDirectory(self, "Select Save Directory")
        if directory:
            self.path = Path(directory)
            self.directory_edit.setText(str(self.path))
            self.data_manager.set_save_path(self.path)


class RecordingControlerWidget(QWidget):
    """
    Widget for controlling video recording start/stop and parameters.
    
    Provides controls for:
    - Recording stop method (Manual or Timer)
    - Timer duration (when using Timer mode)
    - Recording delay countdown
    - Start/Stop recording button
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

        self.delay_widget = QSpinBox(parent=self)
        self.delay_widget.setRange(0, 120)
        self.delay_widget.setValue(0)
        self.delay_widget.setSingleStep(5)
        self.delay_widget.setSuffix(" sec")
        self.delay_widget.valueChanged.connect(lambda value: self.data_manager.set_recording_delay(value))
        self.delay_label = QLabel("Recording delay:", parent=self)
        self.delay_layout = QHBoxLayout()
        self.delay_layout.addWidget(self.delay_label)
        self.delay_layout.addWidget(self.delay_widget)

        layout = QGridLayout()
        layout.addLayout(stop_method_layout, 0, 0, 1, 2)
        layout.addLayout(self.timer_layout, 1, 0, 1, 1)
        layout.addWidget(self.start_time_label, 1, 1, 1, 1)
        layout.addLayout(self.delay_layout, 2, 0, 1, 2)
        layout.addWidget(self.start_stop_btn, 3, 0, 1, 2)

        self.setLayout(layout)

    def update_start_label(self, Qtime_dict):
        """Update the start time display label for each camera."""
        text = "Recording start time: "
        for room, qtime in Qtime_dict.items():
            if qtime != None:
                text += f"{room}: {qtime.toString('HH:mm:ss')} "
        self.start_time_label.setText(text)

    def start_stop_toggled(self):
        """Emit signal to trigger recording start."""
        self.data_manager.start_stop_toggled_signal.emit()  

    def update_stop_method(self, method):
        """Show/hide timer controls based on selected stop method."""
        if method == "Manual":
            self.timer_widget.hide()
            self.timer_label.hide()
            self.data_manager.set_timer_duration(None)
        else:
            self.timer_widget.show()
            self.timer_label.show()
            self.data_manager.set_timer_duration(self.timer_widget.value())

        self.data_manager.set_stop_method(method)


class CountdownWindow(QDialog):
    """
    Modal dialog showing countdown before recording starts.
    
    Displays large countdown timer and allows user to cancel.
    Automatically closes when countdown reaches zero.
    
    Signals:
        countdown_finished: Emitted when countdown completes
        countdown_cancelled: Emitted when user cancels countdown
    """
    countdown_finished = pyqtSignal()
    countdown_cancelled = pyqtSignal()
    
    def __init__(self, delay_seconds, parent=None):
        super().__init__(parent)
        self.delay_seconds = delay_seconds
        self.remaining_seconds = delay_seconds
        
        self.setWindowTitle("Recording Starts In...")
        self.setModal(True)
        self.resize(400, 250)
        
        layout = QVBoxLayout()
        
        info_label = QLabel("Recording will start in:")
        info_label.setAlignment(Qt.AlignCenter)
        info_font = info_label.font()
        info_font.setPointSize(14)
        info_label.setFont(info_font)
        layout.addWidget(info_label)
        
        self.countdown_label = QLabel()
        self.countdown_label.setAlignment(Qt.AlignCenter)
        font = self.countdown_label.font()
        font.setPointSize(72)
        font.setBold(True)
        self.countdown_label.setFont(font)
        self.countdown_label.setStyleSheet("color: orange;")
        self._update_display()
        layout.addWidget(self.countdown_label)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("background-color: red; color: white; font-size: 14px; padding: 10px;")
        self.cancel_btn.clicked.connect(self.cancel_countdown)
        layout.addWidget(self.cancel_btn)
        
        self.setLayout(layout)
        
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.countdown_timer.start(1000)
        
    def _update_display(self):
        """Update countdown display with color based on time remaining."""
        self.countdown_label.setText(f"{self.remaining_seconds}")
        
        if self.remaining_seconds <= 3:
            self.countdown_label.setStyleSheet("color: red;")
        elif self.remaining_seconds <= 5:
            self.countdown_label.setStyleSheet("color: orange;")
        else:
            self.countdown_label.setStyleSheet("color: green;")
    
    def update_countdown(self):
        """Decrement countdown and check if finished."""
        self.remaining_seconds -= 1
        
        if self.remaining_seconds <= 0:
            self.countdown_timer.stop()
            self.countdown_finished.emit()
            self.accept()
        else:
            self._update_display()
    
    def cancel_countdown(self):
        """Handle countdown cancellation."""
        self.countdown_timer.stop()
        self.countdown_cancelled.emit()
        self.reject()
    
    def closeEvent(self, event):
        """Clean up timer on window close."""
        self.countdown_timer.stop()
        self.countdown_cancelled.emit()
        event.accept()


class OnsetCameraSetupDialog(QDialog):
    """
    Initial camera setup dialog shown on application startup.
    
    Allows user to select which cameras to use and specify their
    port indices. Validates that selected cameras are available.
    """
    
    def __init__(self, parent, data_manager):
        super().__init__(parent)
        self.data_manager = data_manager
        self.default_LR_index = 0
        self.default_DR_index = 1
        self.setWindowTitle("Camera Setup")

        self.LR_label = QLabel("LightRoom camera port index:")
        self.LR_edit = QLineEdit()
        self.LR_edit.setText(str(self.default_LR_index))
        self.LR_check = QCheckBox("Use LightRoom cam")
        self.LR_check.setChecked(True)
        self.LR_check.stateChanged.connect(lambda state: self.toggle_room_cam("LightRoom", state))  

        self.DR_label = QLabel("DarkRoom camera port index:")
        self.DR_edit = QLineEdit()
        self.DR_edit.setText(str(self.default_DR_index))
        self.DR_check = QCheckBox("Use DarkRoom cam")
        self.DR_check.setChecked(True) 
        self.DR_check.stateChanged.connect(lambda state: self.toggle_room_cam("DarkRoom", state))

        self.set_button = QPushButton("Set")
        self.set_button.clicked.connect(self.set_data)

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
        """Enable/disable camera input field based on checkbox state."""
        if room == "LightRoom":
            input_data = self.LR_edit
            default = self.default_LR_index
        elif room == "DarkRoom":
            input_data = self.DR_edit
            default = self.default_DR_index

        if state == Qt.Checked:
            input_data.setEnabled(True)
            input_data.setText(str(default))
        else:
            input_data.setText("")
            input_data.setEnabled(False)

    def set_data(self):
        """Validate camera selections and update data manager."""
        valid_inputs = {"LightRoom": False, "DarkRoom": False} 
        visible_cam_indices = [cam['Num'] for cam in Picamera2.global_camera_info()]
        
        if [self.LR_edit.text(), self.DR_edit.text()] == ["", ""]:
            QMessageBox.warning(self, "At least one camera must be selected", "Please select at least one camera to proceed.")
        
        else:
            for room, input_cam_i in zip(["LightRoom", "DarkRoom"], [self.LR_edit.text(), self.DR_edit.text()]):
                if input_cam_i != "":
                    if int(input_cam_i) in visible_cam_indices:
                        self.data_manager.camera_settings[room]['disp_num'] = int(input_cam_i)
                        self.data_manager.is_running[room] = False
                        valid_inputs[room] = True
                    else:
                        QMessageBox.warning(self, "Camera Setup", f"No valid PiCam found at index {input_cam_i} for {room} camera.")
                        valid_inputs[room] = False
                else:
                    valid_inputs[room] = None
        
        if False not in valid_inputs.values():
            self.accept()


class RecordingWindow(QDialog):
    """
    Modal dialog displayed during active recording.
    
    Shows recording timer (elapsed or countdown) and stop button.
    Supports two modes:
    - Manual: Counts up from 00:00:00
    - Timer: Counts down from specified duration
    
    Signals:
        stop_recording_signal: Emitted when recording should stop
    """
    stop_recording_signal = pyqtSignal()
    
    def __init__(self, mode="Manual", duration_minutes=None, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.duration_minutes = duration_minutes
        self.elapsed_seconds = 0
        
        self.setWindowTitle("Recording in Progress")
        self.setModal(True)
        self.resize(400, 200)
        
        layout = QVBoxLayout()
        
        self.timer_label = QLabel()
        self.timer_label.setAlignment(Qt.AlignCenter)
        font = self.timer_label.font()
        font.setPointSize(48)
        font.setBold(True)
        self.timer_label.setFont(font)
        
        if self.mode == "Manual":
            self.timer_label.setText("00:00:00")
            self.timer_label.setStyleSheet("color: green;")
        else:
            total_seconds = int(self.duration_minutes * 60)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            self.timer_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            self.timer_label.setStyleSheet("color: orange;")
        
        layout.addWidget(self.timer_label)
        
        if self.mode == "Manual":
            status_text = "Recording - Elapsed Time"
        else:
            status_text = f"Recording - Time Remaining"
        
        self.status_label = QLabel(status_text)
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.stop_btn = QPushButton("Stop Recording")
        self.stop_btn.setStyleSheet("#stop_btn {background-color: red; color: white; font-size: 16px; padding: 10px;}")
        self.stop_btn.setObjectName("stop_btn")
        self.stop_btn.clicked.connect(self.stop_recording)
        layout.addWidget(self.stop_btn)
        
        self.setLayout(layout)
        
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(1000)
        
    def update_display(self):
        """Update timer display every second."""
        self.elapsed_seconds += 1
        
        if self.mode == "Manual":
            hours = self.elapsed_seconds // 3600
            minutes = (self.elapsed_seconds % 3600) // 60
            seconds = self.elapsed_seconds % 60
            self.timer_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        else:
            total_seconds = int(self.duration_minutes * 60)
            remaining_seconds = total_seconds - self.elapsed_seconds
            
            if remaining_seconds <= 0:
                self.timer_label.setText("00:00:00")
                self.timer_label.setStyleSheet("color: red;")
                self.update_timer.stop()
                self.stop_recording()
            else:
                hours = remaining_seconds // 3600
                minutes = (remaining_seconds % 3600) // 60
                seconds = remaining_seconds % 60
                self.timer_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
                
                if remaining_seconds <= 10:
                    self.timer_label.setStyleSheet("color: red;")
    
    def stop_recording(self):
        """Stop recording and close window."""
        self.update_timer.stop()
        self.stop_recording_signal.emit()
        self.accept()
    
    def get_elapsed_time(self):
        """Return elapsed recording time in seconds."""
        return self.elapsed_seconds
    
    def closeEvent(self, event):
        """Clean up timer on window close."""
        self.update_timer.stop()
        self.stop_recording_signal.emit()
        event.accept()