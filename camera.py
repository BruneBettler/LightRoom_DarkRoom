from PyQt5.QtCore import QSize, Qt, QTimer, QTime
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
from config import *
import json

# Local debug flag: set to True to re-enable verbose debug prints
DEBUG = False
def dprint(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

class Camera(QWidget): 
    def __init__(self, data_manager, CamDisp_num):
        super().__init__()
        self.cam_layout = QVBoxLayout()
        self.data_manager = data_manager
        # allow the camera widget to scale with the window
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(int((self.data_manager.main_window_size['W']-30)/8), int(self.data_manager.main_window_size['H']*3/18))

        self.CamDisp_num = CamDisp_num # find number on the physical pi, port number where the camera is inserted
        self.preview_off_widget = QWidget()
        self.preview_off_widget.setStyleSheet("background-color: black;")

        # Find all cameras and pick the desired one
        self.picam = Picamera2(self.CamDisp_num)
        self.picam_preview_widget = None 

        # popup containing camera configuration controls
        self.configuration_popup = ConfigPopup(self.data_manager, self)  #Todo: add parent? 
     
        """
        Add camera controls widgets (always available on GUI screen)
        """
        self.lens_position_widget = QDoubleSpinBox()
        min_diop, max_diop, default_diop = self.picam.camera_controls["LensPosition"]
        self.lens_position_widget.setRange(min_diop, max_diop)
        self.lens_position_widget.setValue(default_diop)
        self.lens_position_widget.setSingleStep(0.1)

        self.setLayout(self.cam_layout)
    
    def config_pop(self):
        # show the configuration popup instance (use the attribute name, not the method name)
        if hasattr(self, 'configuration_popup') and self.configuration_popup is not None:
            try:
                # refresh popup from currently-applied Picamera2 state so it shows loaded values
                try:
                    if hasattr(self.configuration_popup, 'refresh_from_picam'):
                        self.configuration_popup.refresh_from_picam()
                except Exception:
                    pass
            except Exception:
                pass
            self.configuration_popup.exec_()

    def initialize_preview(self):
        """Configure and show the default preview (no rotation/transform).
        This is a simplified implementation with any rotation logic removed.
        """
        dprint(f"[camera] initialize_preview: enter for Camera {self.CamDisp_num}")
        try:
            # stop camera before reconfiguring (safe if not running)
            try:
                self.picam.stop()
                dprint(f"[camera] initialize_preview: picam.stop() called for {self.CamDisp_num}")
            except Exception as e:
                dprint(f"[camera] initialize_preview: picam.stop() failed: {e}")

            # remove any existing preview widgets so layout doesn't shrink or duplicate
            try:
                if hasattr(self, 'picam_preview_widget') and self.picam_preview_widget is not None:
                    try:
                        self.cam_layout.removeWidget(self.picam_preview_widget)
                        self.picam_preview_widget.deleteLater()
                    except Exception:
                        pass
                    self.picam_preview_widget = None
            except Exception:
                pass
            try:
                if hasattr(self, 'software_preview_label') and self.software_preview_label is not None:
                    try:
                        self.cam_layout.removeWidget(self.software_preview_label)
                        self.software_preview_label.deleteLater()
                    except Exception:
                        pass
                    self.software_preview_label = None
            except Exception:
                pass

            # create a standard preview configuration (no transform)
            # If a requested preview size was set by the UI, use it.
            try:
                if hasattr(self, 'requested_preview_size') and getattr(self, 'requested_preview_size'):
                    req = getattr(self, 'requested_preview_size')
                    config = self.picam.create_preview_configuration(main={'size': req})
                    # consume the request so future calls use defaults unless changed again
                    try:
                        delattr(self, 'requested_preview_size')
                    except Exception:
                        try:
                            del self.requested_preview_size
                        except Exception:
                            pass
                else:
                    config = self.picam.create_preview_configuration()
            except Exception:
                config = self.picam.create_preview_configuration()
            try:
                # Diagnostic: print the preview configuration that will be used
                try:
                    dprint(f"[camera] initialize_preview: created preview config for {self.CamDisp_num}: {config}")
                except Exception:
                    pass

                # Merge any currently-set Picamera2 controls (from set_controls) into the
                # preview configuration so frame-duration and other settings are honored
                try:
                    picam_controls = None
                    # Prefer an explicit get_controls() call if available (returns dict-like)
                    if hasattr(self.picam, 'get_controls'):
                        try:
                            gc = self.picam.get_controls()
                            dprint(f"[camera] initialize_preview: picam.get_controls() -> {gc}")
                            if isinstance(gc, dict):
                                picam_controls = dict(gc)
                            else:
                                try:
                                    picam_controls = dict(gc)
                                except Exception:
                                    # try to iterate items()
                                    try:
                                        picam_controls = {k: v for k, v in gc.items()}
                                    except Exception:
                                        picam_controls = None
                        except Exception as e:
                            dprint(f"[camera] initialize_preview: picam.get_controls() failed: {e}")

                    # Fallback: inspect self.picam.controls attribute
                    if not picam_controls and hasattr(self.picam, 'controls') and self.picam.controls is not None:
                        try:
                            cobj = self.picam.controls
                            # dict-like?
                            if isinstance(cobj, dict):
                                picam_controls = dict(cobj)
                            elif hasattr(cobj, 'items'):
                                picam_controls = {k: v for k, v in cobj.items()}
                            else:
                                # last resort: str parsing (not ideal) - attempt to extract the braces content
                                s = str(cobj)
                                # look for first '{' and last '}' and evaluate safely using literal_eval
                                from ast import literal_eval
                                try:
                                    start = s.find('{')
                                    end = s.rfind('}')
                                    if start != -1 and end != -1 and end > start:
                                        inner = s[start:end+1]
                                        picam_controls = literal_eval(inner)
                                except Exception:
                                    picam_controls = None
                        except Exception as e:
                            dprint(f"[camera] initialize_preview: error reading picam.controls: {e}")

                    # If we have controls from the Picamera2 instance, inject them into config['controls']
                    if picam_controls:
                        if 'controls' not in config or config['controls'] is None:
                            config['controls'] = {}
                        # update config controls with any keys from picam_controls
                        try:
                            config['controls'].update(picam_controls)
                            dprint(f"[camera] initialize_preview: merged picam.controls into preview config for {self.CamDisp_num}: {picam_controls}")
                        except Exception as e:
                            dprint(f"[camera] initialize_preview: failed to merge picam.controls: {e}")
                except Exception as e:
                    dprint(f"[camera] initialize_preview: error while merging controls: {e}")

                self.picam.configure(config)
                dprint(f"[camera] initialize_preview: picam.configure() succeeded for {self.CamDisp_num}")
            except Exception as e:
                dprint(f"[camera] configure failed: {e}; attempting to continue")
            # Diagnostic: show camera_controls exposed by Picamera2 after configure
            try:
                dprint(f"[camera] initialize_preview: picam.camera_controls={getattr(self.picam, 'camera_controls', None)}")
            except Exception:
                pass

            self.picam_preview_widget = QGlPicamera2(self.picam, parent=self)
            try:
                self.picam_preview_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            except Exception:
                pass
            # add with stretch so it takes available space
            try:
                self.cam_layout.addWidget(self.picam_preview_widget, 1)
            except Exception:
                # fallback to add without stretch
                self.cam_layout.addWidget(self.picam_preview_widget, alignment=Qt.AlignCenter)
            dprint(f"[camera] initialize_preview: added picam_preview_widget for {self.CamDisp_num}")
            # ensure software preview attributes cleared
            if hasattr(self, 'software_preview_timer'):
                try:
                    self.software_preview_timer.stop()
                except Exception:
                    pass
                self.software_preview_timer = None
            self.software_preview_label = None
        except Exception as e:
            dprint(f"[camera] initialize_preview error: {e}")
        # ensure software preview attributes cleared
        if hasattr(self, 'software_preview_timer'):
            try:
                self.software_preview_timer.stop()
            except Exception:
                pass
            self.software_preview_timer = None
        self.software_preview_label = None

    def initialize_software_preview(self, rotation_deg=0):
        """Fallback preview that captures frames and displays them rotated in a QLabel."""
        # configure camera preview without transform
        try:
            config = self.picam.create_preview_configuration()
            self.picam.configure(config)
        except Exception:
            try:
                config = self.picam.create_preview_configuration()
                self.picam.configure(config)
            except Exception as e:
                print(f"[camera] Failed to configure camera for software preview: {e}")
                return

        # create a QLabel to show frames
        self.software_preview_label = QLabel(parent=self)
        self.software_preview_label.setAlignment(Qt.AlignCenter)
        self.software_preview_label.setStyleSheet("background-color: black;")
        self.cam_layout.addWidget(self.software_preview_label)

        # start camera and timer to poll frames
        try:
            self.picam.start()
        except Exception:
            pass

        self.software_rotation = int(rotation_deg) % 360
        # timer interval (ms) - 30 FPS default
        interval_ms = 33
        self.software_preview_timer = QTimer(self)
        self.software_preview_timer.timeout.connect(self._software_preview_update)
        self.software_preview_timer.start(interval_ms)

    def _software_preview_update(self):
        # capture a frame as numpy array and display rotated
        try:
            arr = self.picam.capture_array()  # capture from default stream (main)
            # arr expected shape (H, W, 3) RGB
            if arr is None:
                return
            # rotate using numpy
            k = 0
            if self.software_rotation == 90:
                k = 3  # clockwise 90
            elif self.software_rotation == 180:
                k = 2
            elif self.software_rotation == 270:
                k = 1
            if k != 0:
                arr = np.rot90(arr, k=k)

            h, w, ch = arr.shape
            bytes_per_line = ch * w
            # ensure RGB888
            img = QImage(arr.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pix = QPixmap.fromImage(img)
            self.software_preview_label.setPixmap(pix.scaled(self.software_preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception as e:
            # On capture errors, silently ignore (camera may be busy)
            # print for debug
            print(f"[camera] software preview update error: {e}")
            return

    def start_recording(self, output_file_path):
        """
        Start recording video to the specified file path.
        Stops preview and starts H264 encoding.
        
        :param output_file_path: Full path to the output video file
        :return: Dictionary with 'success' (bool) and 'config' (dict) keys
        """
        try:
            dprint(f"[camera] start_recording: Starting recording for Camera {self.CamDisp_num} to {output_file_path}")
            
            # Stop any preview that's running
            try:
                self.picam.stop()
            except Exception as e:
                dprint(f"[camera] start_recording: Error stopping preview: {e}")
            
            # Hide preview widgets
            if hasattr(self, 'picam_preview_widget') and self.picam_preview_widget is not None:
                self.picam_preview_widget.hide()
            if hasattr(self, 'software_preview_label') and self.software_preview_label is not None:
                self.software_preview_label.hide()
            if hasattr(self, 'software_preview_timer') and self.software_preview_timer is not None:
                self.software_preview_timer.stop()
            
            # Show the "preview off" widget during recording
            if hasattr(self, 'preview_off_widget') and self.preview_off_widget is not None:
                try:
                    self.cam_layout.addWidget(self.preview_off_widget)
                    self.preview_off_widget.show()
                except Exception:
                    pass
            
            # Create video configuration for recording
            # Use the current resolution or default to 1920x1080
            try:
                if hasattr(self, 'requested_preview_size') and getattr(self, 'requested_preview_size'):
                    req_size = getattr(self, 'requested_preview_size')
                    video_config = self.picam.create_video_configuration(main={'size': req_size})
                else:
                    video_config = self.picam.create_video_configuration(main={'size': (1920, 1080)})
            except Exception:
                video_config = self.picam.create_video_configuration()
            
            # Apply the video configuration
            self.picam.configure(video_config)
            
            # Capture the actual configuration that will be used
            actual_config = {}
            try:
                # Get camera controls
                camera_controls = self.picam.camera_controls
                actual_config['FrameDurationLimits'] = camera_controls.get('FrameDurationLimits', 'N/A')
                actual_config['ExposureTime'] = camera_controls.get('ExposureTime', 'N/A')
                actual_config['AnalogueGain'] = camera_controls.get('AnalogueGain', 'N/A')
                actual_config['LensPosition'] = camera_controls.get('LensPosition', 'N/A')
                actual_config['Brightness'] = camera_controls.get('Brightness', 'N/A')
                actual_config['Saturation'] = camera_controls.get('Saturation', 'N/A')
                actual_config['Contrast'] = camera_controls.get('Contrast', 'N/A')
                actual_config['Sharpness'] = camera_controls.get('Sharpness', 'N/A')
                
                # Get video configuration
                actual_config['Resolution'] = video_config.get('main', {}).get('size', 'N/A')
                actual_config['Format'] = video_config.get('main', {}).get('format', 'N/A')
                
            except Exception as e:
                dprint(f"[camera] start_recording: Could not capture full config: {e}")
            
            # Create H264 encoder
            self.encoder = H264Encoder()
            
            # Start recording
            self.picam.start_recording(self.encoder, output_file_path)
            dprint(f"[camera] start_recording: Recording started successfully for Camera {self.CamDisp_num}")
            
            return {'success': True, 'config': actual_config}
            
        except Exception as e:
            print(f"[camera] start_recording: ERROR starting recording for Camera {self.CamDisp_num}: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'config': {}}
    
    def stop_recording(self):
        """
        Stop the current recording and return to preview mode.
        
        :return: True if recording stopped successfully, False otherwise
        """
        try:
            dprint(f"[camera] stop_recording: Stopping recording for Camera {self.CamDisp_num}")
            
            # Stop the recording
            try:
                self.picam.stop_recording()
                dprint(f"[camera] stop_recording: Recording stopped for Camera {self.CamDisp_num}")
            except Exception as e:
                dprint(f"[camera] stop_recording: Error stopping recording: {e}")
            
            # Stop the camera
            try:
                self.picam.stop()
            except Exception as e:
                dprint(f"[camera] stop_recording: Error stopping camera: {e}")
            
            # Hide the "preview off" widget
            if hasattr(self, 'preview_off_widget') and self.preview_off_widget is not None:
                try:
                    self.cam_layout.removeWidget(self.preview_off_widget)
                    self.preview_off_widget.hide()
                except Exception:
                    pass
            
            # Reinitialize preview
            try:
                self.initialize_preview()
                dprint(f"[camera] stop_recording: Preview reinitialized for Camera {self.CamDisp_num}")
            except Exception as e:
                print(f"[camera] stop_recording: Error reinitializing preview: {e}")
            
            return True
            
        except Exception as e:
            print(f"[camera] stop_recording: ERROR stopping recording for Camera {self.CamDisp_num}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def closeEvent(self, event):
        print(f"Safely closing Camera {self.CamDisp_num}")
        try:
            # stop the camera if running
            if hasattr(self, 'picam') and self.picam is not None:
                self.picam.stop()
        except Exception:
            pass
        # close preview widget if it exists
        if hasattr(self, 'picam_preview_widget') and self.picam_preview_widget is not None:
            try:
                self.picam_preview_widget.close()
            except Exception:
                pass
        if hasattr(self, 'software_preview_timer') and self.software_preview_timer is not None:
            try:
                self.software_preview_timer.stop()
            except Exception:
                pass
        if hasattr(self, 'software_preview_label') and self.software_preview_label is not None:
            try:
                self.software_preview_label.clear()
            except Exception:
                pass
        event.accept()

class CameraControlWidget(QWidget):    
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        
        camera_layout = QHBoxLayout()
        # determine which cameras to show based on the data_manager settings
        self.camera_widgets = {}

        for i, room in enumerate(["LightRoom", "DarkRoom"]): 
            # check if the camera is set to be displayed
            if self.data_manager.camera_settings[room]['disp_num'] is not None:
                # add to the camera_widgets dictionary
                cam = Camera(self.data_manager, self.data_manager.camera_settings[room]['disp_num'])
                self.camera_widgets[room] = cam
                layout = QVBoxLayout()
                layout.addWidget(QLabel(f"{room} Camera: port {self.data_manager.camera_settings[room]['disp_num']}"))
                
                # Add camera preview directly (no arrows)
                layout.addWidget(cam, 1)

                # add each camera column with stretch so they divide space evenly
                camera_layout.addLayout(layout, 1)
        
        # Create a single global ConfigSetupWidget below both camera previews
        # Wire a single global Modify button that opens a combined dialog for both cameras.
        try:
            cams = list(self.camera_widgets.values())
            if len(cams) >= 2:
                cam_a, cam_b = cams[0], cams[1]
                # define opener
                def open_combined():
                    try:
                        from config import CombinedConfigDialog
                        dlg = CombinedConfigDialog(self.data_manager, cam_a, cam_b, parent=self)
                        dlg.exec_()
                    except Exception:
                        try:
                            # fallback: open individual popups
                            cam_a.config_pop()
                            cam_b.config_pop()
                        except Exception:
                            pass

                # Create one global setup widget (pass first camera as reference)
                global_setup = ConfigSetupWidget(self.data_manager, cam_a)
                global_setup.set_modify_callback(open_combined)
                
                # Store reference so other code can update the UI
                try:
                    cam_a.setup_widget = global_setup
                    cam_b.setup_widget = global_setup
                except Exception:
                    pass
                
                # Create a vertical layout that holds the camera_layout and the global setup widget
                main_v_layout = QVBoxLayout()
                main_v_layout.addLayout(camera_layout)
                main_v_layout.addWidget(global_setup)
                self.setLayout(main_v_layout)
            elif len(cams) == 1:
                # Single camera: setup widget under that camera
                cam = cams[0]
                setup_widget = ConfigSetupWidget(self.data_manager, cam)
                try:
                    cam.setup_widget = setup_widget
                except Exception:
                    pass
                main_v_layout = QVBoxLayout()
                main_v_layout.addLayout(camera_layout)
                main_v_layout.addWidget(setup_widget)
                self.setLayout(main_v_layout)
            else:
                self.setLayout(camera_layout)
        except Exception:
            self.setLayout(camera_layout)
        self.start_stop_preview(True)

        self.data_manager.start_stop_toggled_signal.connect(self.start_stop_recording)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Arrow widgets removed - no dynamic resizing needed
        pass
    
    def start_stop_recording(self):
        """
        Start, stop, or abort the camera recording with session naming.
        Shows RecordingWindow during recording.
        """
        # Check if any camera is currently recording
        is_any_running = any(self.data_manager.is_running[room] for room in self.camera_widgets.keys())
        
        if is_any_running:
            # Stop recording - this will be called by RecordingWindow
            self._stop_all_recordings()
        else:
            # Start recording - show session dialog first
            self._start_all_recordings()
    
    def _start_all_recordings(self):
        """
        Start recording on all cameras after getting session name and countdown.
        """
        # Get session name and save location from user
        session_name, save_path = self._get_session_info()
        
        if not session_name or not save_path:
            # User cancelled
            return
        
        # Store session info in data manager
        self.data_manager.set_session_name(session_name)
        self.data_manager.set_save_path(save_path)
        
        # Check if files already exist and warn user
        from pathlib import Path
        existing_files = []
        camera_num = 1
        for room in self.camera_widgets.keys():
            output_file = self.data_manager.get_session_file_path(f"camera_{camera_num}")
            if Path(output_file).exists():
                existing_files.append(Path(output_file).name)
            camera_num += 1
        
        # Also check for session_data.txt
        session_data_file = Path(save_path) / "session_data.txt"
        if session_data_file.exists():
            existing_files.append("session_data.txt")
        
        if existing_files:
            # Show warning dialog
            file_list = "\n".join(existing_files)
            reply = QMessageBox.question(
                self,
                "Overwrite Files?",
                f"The following file(s) already exist and will be overwritten:\n\n{file_list}\n\nAre you sure you want to continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                # User chose not to overwrite, cancel recording
                return
        
        # Hide preview before countdown/recording
        self.start_stop_preview(False)
        
        # Show countdown if delay is set
        if self.data_manager.recording_delay > 0:
            from global_widgets import CountdownWindow
            countdown_window = CountdownWindow(self.data_manager.recording_delay, parent=self)
            
            # Connect signals
            countdown_window.countdown_cancelled.connect(self._on_countdown_cancelled)
            
            # Show countdown window (modal)
            result = countdown_window.exec_()
            
            if result == QDialog.Rejected:
                # User cancelled countdown, return to preview
                self.start_stop_preview(True)
                return
        
        # Record the actual start datetime
        from PyQt5.QtCore import QDateTime
        self.data_manager.set_start_datetime(QDateTime.currentDateTime())
        
        # Start recording for each camera
        camera_num = 1
        for room, cam in self.camera_widgets.items():
            # Get the output file path
            output_file = self.data_manager.get_session_file_path(f"camera_{camera_num}")
            
            # Start recording and get config
            result = cam.start_recording(output_file)
            
            if result['success']:
                self.data_manager.set_is_running(room, True)
                self.data_manager.set_start_time(room, QTime.currentTime())
                self.data_manager.set_recording_config(room, result['config'])
                print(f"Started {room} camera recording to {output_file}")
            else:
                print(f"Failed to start {room} camera recording")
                # If any camera fails, stop all and return to preview
                self._stop_all_recordings()
                return
            
            camera_num += 1
        
        # Show the recording window
        self._show_recording_window()
    
    def _on_countdown_cancelled(self):
        """
        Handle countdown cancellation.
        """
        print("Recording countdown cancelled by user")
    
    def _stop_all_recordings(self):
        """
        Stop recording on all cameras and return to preview.
        """
        for room, cam in self.camera_widgets.items():
            if self.data_manager.is_running[room]:
                cam.stop_recording()
                self.data_manager.set_is_running(room, False)
                print(f"Stopped {room} camera recording")
        
        # Return to preview
        self.start_stop_preview(True)
    
    def _get_session_info(self):
        """
        Show dialog to get session name and save location.
        Returns (session_name, save_path) or (None, None) if cancelled.
        """
        # First, get the save directory
        save_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Save Directory",
            str(self.data_manager.save_path) if self.data_manager.save_path else ""
        )
        
        if not save_dir:
            return None, None
        
        # Then get the session name
        session_name, ok = QInputDialog.getText(
            self,
            "Session Name",
            "Enter session name:",
            QLineEdit.Normal,
            ""
        )
        
        if not ok or not session_name:
            return None, None
        
        return session_name, save_dir
    
    def _show_recording_window(self):
        """
        Show the recording window with timer based on the stop method.
        """
        from global_widgets import RecordingWindow
        
        if self.data_manager.stop_method == "Manual":
            # Manual mode - elapsed timer
            self.recording_window = RecordingWindow(mode="Manual", parent=self)
        else:
            # Timer mode - countdown
            self.recording_window = RecordingWindow(
                mode="Timer",
                duration_minutes=self.data_manager.timer_duration,
                parent=self
            )
        
        # Connect stop signal
        self.recording_window.stop_recording_signal.connect(self._on_recording_stopped)
        
        # Show the window (modal)
        self.recording_window.exec_()
    
    def _on_recording_stopped(self):
        """
        Handle recording stop from RecordingWindow.
        Save comprehensive session data to session_data.txt.
        """
        # Record the end datetime
        from PyQt5.QtCore import QDateTime
        self.data_manager.set_end_datetime(QDateTime.currentDateTime())
        
        # Record end times for each camera
        for room in self.camera_widgets.keys():
            self.data_manager.set_end_time(room, QTime.currentTime())
        
        # Get elapsed time from recording window
        elapsed_seconds = self.recording_window.get_elapsed_time()
        
        # Stop all recordings
        self._stop_all_recordings()
        
        # Save comprehensive session data
        self._save_session_data_file(elapsed_seconds)
    
    def _save_session_data_file(self, elapsed_seconds):
        """
        Save comprehensive recording session data to session_data.txt in the save directory.
        Includes: session name, dates/times, duration, stop method, camera configurations, file paths, etc.
        """
        if not self.data_manager.save_path:
            return
        
        from pathlib import Path
        session_data_file = Path(self.data_manager.save_path) / "session_data.txt"
        
        try:
            # Convert seconds to hours:minutes:seconds
            hours = elapsed_seconds // 3600
            minutes = (elapsed_seconds % 3600) // 60
            seconds = elapsed_seconds % 60
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            with open(session_data_file, 'w') as f:
                # Header
                f.write("="*60 + "\n")
                f.write("RECORDING SESSION DATA\n")
                f.write("="*60 + "\n\n")
                
                # Session Information
                f.write("SESSION INFORMATION\n")
                f.write("-"*60 + "\n")
                f.write(f"Session Name: {self.data_manager.session_name}\n")
                f.write(f"Save Path: {self.data_manager.save_path}\n\n")
                
                # Timing Information
                f.write("TIMING INFORMATION\n")
                f.write("-"*60 + "\n")
                if self.data_manager.start_datetime:
                    f.write(f"Start Date/Time: {self.data_manager.start_datetime.toString('yyyy-MM-dd hh:mm:ss')}\n")
                if self.data_manager.end_datetime:
                    f.write(f"End Date/Time: {self.data_manager.end_datetime.toString('yyyy-MM-dd hh:mm:ss')}\n")
                f.write(f"Total Duration: {time_str}\n")
                f.write(f"Elapsed Seconds: {elapsed_seconds}\n\n")
                
                # Recording Parameters
                f.write("RECORDING PARAMETERS\n")
                f.write("-"*60 + "\n")
                f.write(f"Stop Method: {self.data_manager.stop_method}\n")
                if self.data_manager.stop_method == "Timer" and self.data_manager.timer_duration:
                    f.write(f"Timer Duration: {self.data_manager.timer_duration} minutes\n")
                f.write(f"Recording Delay (Countdown): {self.data_manager.recording_delay} seconds\n\n")
                
                # Camera Information
                camera_num = 1
                for room in self.camera_widgets.keys():
                    f.write(f"CAMERA {camera_num} ({room})\n")
                    f.write("-"*60 + "\n")
                    
                    # File path
                    output_file = self.data_manager.get_session_file_path(f"camera_{camera_num}")
                    f.write(f"Video File: {Path(output_file).name}\n")
                    
                    # Start/End times
                    if self.data_manager.start_time[room]:
                        f.write(f"Start Time: {self.data_manager.start_time[room].toString('hh:mm:ss')}\n")
                    if self.data_manager.end_time[room]:
                        f.write(f"End Time: {self.data_manager.end_time[room].toString('hh:mm:ss')}\n")
                    
                    # Camera configuration at recording time
                    if self.data_manager.recording_configs[room]:
                        f.write(f"\nCamera Configuration:\n")
                        config = self.data_manager.recording_configs[room]
                        for key, value in config.items():
                            # Format the value nicely
                            if isinstance(value, tuple):
                                value_str = f"{value[0]} x {value[1]}" if len(value) == 2 else str(value)
                            else:
                                value_str = str(value)
                            f.write(f"  {key}: {value_str}\n")
                    
                    # Camera settings from data manager
                    if room in self.data_manager.camera_settings:
                        settings = self.data_manager.camera_settings[room]
                        if any(settings.values()):
                            f.write(f"\nCamera Settings:\n")
                            if settings.get('disp_num') is not None:
                                f.write(f"  Display Number: {settings['disp_num']}\n")
                            if settings.get('status') is not None:
                                f.write(f"  Status: {settings['status']}\n")
                            if settings.get('focus') is not None:
                                f.write(f"  Focus: {settings['focus']}\n")
                            if settings.get('frame_rate') is not None:
                                f.write(f"  Frame Rate: {settings['frame_rate']}\n")
                            if settings.get('exposure') is not None:
                                f.write(f"  Exposure: {settings['exposure']}\n")
                            if settings.get('zoom') is not None:
                                f.write(f"  Zoom: {settings['zoom']}\n")
                    
                    f.write("\n")
                    camera_num += 1
                
                # Footer
                f.write("="*60 + "\n")
                f.write("End of session data\n")
                f.write("="*60 + "\n")
            
            print(f"Saved comprehensive session data to {session_data_file}")
        except Exception as e:
            print(f"Error saving session data file: {e}")
            import traceback
            traceback.print_exc()

    def start_stop_preview(self, start_preview):
        """
        Start or stop the camera preview.
        :param start_preview: Boolean indicating whether to start or stop the preview
        """
        if start_preview:
            for room, cam in self.camera_widgets.items():
                cam.initialize_preview()
                try:
                    cam.picam.start()
                except Exception:
                    pass
                # prefer the GL preview widget, otherwise the software preview label
                if hasattr(cam, 'picam_preview_widget') and cam.picam_preview_widget is not None:
                    cam.cam_layout.addWidget(cam.picam_preview_widget)
                elif hasattr(cam, 'software_preview_label') and cam.software_preview_label is not None:
                    cam.cam_layout.addWidget(cam.software_preview_label)
                else:
                    cam.cam_layout.addWidget(cam.preview_off_widget)
        else:
            for room, cam in self.camera_widgets.items():
                try:
                    cam.picam.stop()
                except Exception:
                    pass
                # remove GL preview if present
                if hasattr(cam, 'picam_preview_widget') and cam.picam_preview_widget is not None:
                    try:
                        cam.picam_preview_widget.deleteLater()
                        cam.cam_layout.removeWidget(cam.picam_preview_widget)
                    except Exception:
                        pass
                # stop software preview if present
                if hasattr(cam, 'software_preview_timer') and cam.software_preview_timer is not None:
                    try:
                        cam.software_preview_timer.stop()
                    except Exception:
                        pass
                if hasattr(cam, 'software_preview_label') and cam.software_preview_label is not None:
                    try:
                        cam.software_preview_label.clear()
                        cam.cam_layout.removeWidget(cam.software_preview_label)
                    except Exception:
                        pass
                cam.cam_layout.addWidget(cam.preview_off_widget)

    def closeEvent(self, event):
        for room, cam in self.camera_widgets.items():
            cam.close()
        event.accept() 

    
    
