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
        self.record_timer = QTimer(self)
        self.record_timer.setSingleShot(True)
        self.record_timer.timeout.connect(self.handle_timer_timeout)
        
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
        Start, stop, or abort the camera recording.
        """
        for i, (room, cam) in enumerate(self.camera_widgets.items()):
            if self.data_manager.is_running[room]:  # currently running so turn it off
                cam.picam.stop_recording()
                cam.picam.stop()
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
                # create default video configuration (no rotation/transform)
                try:
                    video_config = cam.picam.create_video_configuration()
                except Exception:
                    video_config = cam.picam.create_video_configuration()
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
            cam.picam.stop()
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

    
    
