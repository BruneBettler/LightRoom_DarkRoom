"""Camera configuration GUI components for Picamera2.

This module provides dialog widgets for configuring camera settings including:
- Frame rate (FPS)
- Exposure time
- Lens position (focus)
- Analogue gain
- Brightness
- Image tuning (Saturation, Contrast, Sharpness)
- Resolution

Configuration can be saved/loaded from JSON files in a global mapping format
where each camera ID maps to its control settings.
"""

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QImage, QPixmap
from picamera2 import Picamera2
from pathlib import Path
import json

DEFAULT_CONFIG_FILENAME = 'default_config.json'


class ConfigPopup(QDialog):
    """Configuration dialog for a single camera.
    
    Provides widgets for adjusting camera controls with live preview updates.
    Changes are debounced (250ms) before being applied to prevent excessive
    camera reconfiguration.
    
    Args:
        data_manager: Application data manager instance
        cam_widget: Camera widget containing the Picamera2 instance
        parent: Optional parent widget
    """

    def __init__(self, data_manager, cam_widget, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Cam {cam_widget.CamDisp_num}: Configuration settings")
        self.data_manager = data_manager
        self.cam_widget = cam_widget
        self.cam = cam_widget.picam

        self.main_layout = QGridLayout()
        row = 0
        
        # Timer for debouncing live control updates
        self._live_apply_timer = QTimer(self)
        self._live_apply_timer.setSingleShot(True)
        self._live_apply_timer.setInterval(250)
        self._live_apply_timer.timeout.connect(self._apply_controls_live)
        self._last_applied_resolution = None

        # Frame rate (FPS from FrameDurationLimits)
        try:
            fd_limits = getattr(self.cam, 'camera_controls', {}).get('FrameDurationLimits', None)
            if fd_limits is not None:
                min_fd = int(fd_limits[0])
                max_fd = int(fd_limits[1])
                default_fd = int(fd_limits[2]) if len(fd_limits) > 2 else max_fd
                min_fps = max(1, int(1000000 // max_fd))
                max_fps = max(1, int(1000000 // min_fd))
                default_fps = max(1, int(1000000 // default_fd))
            else:
                min_fps, max_fps, default_fps = 1, 60, 30
        except Exception:
            min_fps, max_fps, default_fps = 1, 60, 30

        self.frame_rate_spin = QSpinBox()
        self.frame_rate_spin.setRange(min_fps, max_fps)
        self.frame_rate_spin.setValue(default_fps)
        self.frame_rate_spin.valueChanged.connect(self.schedule_live_apply)
        self.main_layout.addWidget(QLabel("Frame rate (fps):"), row, 0)
        self.main_layout.addWidget(self.frame_rate_spin, row, 1)
        self.frame_rate_slider = QSlider(Qt.Horizontal)
        self.frame_rate_slider.setRange(min_fps, max_fps)
        self.frame_rate_slider.setValue(default_fps)
        self.frame_rate_slider.valueChanged.connect(self.frame_rate_spin.setValue)
        self.frame_rate_spin.valueChanged.connect(self.frame_rate_slider.setValue)
        self.frame_rate_slider.valueChanged.connect(self.schedule_live_apply)
        self.main_layout.addWidget(self.frame_rate_slider, row, 2)
        row += 1

        # Resolution selection
        try:
            preset_sizes = [(640, 480), (1280, 720), (1920, 1080), (2592, 1944)]
            self.resolution_combo = QComboBox()
            for w, h in preset_sizes:
                self.resolution_combo.addItem(f"{w}x{h}", (w, h))
            self.main_layout.addWidget(QLabel("Resolution:"), row, 0)
            self.main_layout.addWidget(self.resolution_combo, row, 1, 1, 2)
            self.resolution_combo.currentIndexChanged.connect(self.schedule_live_apply)
            row += 1
        except Exception:
            pass

        # Exposure time
        try:
            exp = getattr(self.cam, 'camera_controls', {}).get('ExposureTime', None)
            if exp is not None:
                e_min, e_max, e_def = int(exp[0]), int(exp[1]), int(exp[2]) if len(exp) > 2 else int((exp[0]+exp[1])/2)
                self.exposure_time_spin = QSpinBox()
                self.exposure_time_spin.setRange(e_min, e_max)
                self.exposure_time_spin.setValue(e_def)
                self.main_layout.addWidget(QLabel("Exposure time (µs):"), row, 0)
                self.main_layout.addWidget(self.exposure_time_spin, row, 1)
                self.exposure_time_slider = QSlider(Qt.Horizontal)
                self.exposure_time_slider.setRange(e_min, e_max)
                self.exposure_time_slider.setValue(e_def)
                self.exposure_time_slider.valueChanged.connect(self.exposure_time_spin.setValue)
                self.exposure_time_spin.valueChanged.connect(self.exposure_time_slider.setValue)
                self.main_layout.addWidget(self.exposure_time_slider, row, 2)
                self.exposure_time_spin.valueChanged.connect(self.schedule_live_apply)
                self.exposure_time_slider.valueChanged.connect(self.schedule_live_apply)
                row += 1
        except Exception:
            pass

        # Lens position
        try:
            lens = getattr(self.cam, 'camera_controls', {}).get('LensPosition', None)
            if lens is not None:
                l_min, l_max, l_def = float(lens[0]), float(lens[1]), float(lens[2]) if len(lens) > 2 else float((lens[0]+lens[1])/2)
                self.lens_position_spin = QDoubleSpinBox()
                self.lens_position_spin.setRange(l_min, l_max)
                self.lens_position_spin.setSingleStep(0.1)
                self.lens_position_spin.setValue(l_def)
                self.main_layout.addWidget(QLabel("Lens position:"), row, 0)
                self.main_layout.addWidget(self.lens_position_spin, row, 1)
                self.lens_position_slider = QSlider(Qt.Horizontal)
                lp_scale = 10
                self.lens_position_slider.setRange(int(l_min*lp_scale), int(l_max*lp_scale))
                self.lens_position_slider.setValue(int(l_def*lp_scale))
                self.lens_position_slider.valueChanged.connect(lambda v: self.lens_position_spin.setValue(v/lp_scale))
                self.lens_position_spin.valueChanged.connect(lambda v: self.lens_position_slider.setValue(int(v*lp_scale)))
                self.main_layout.addWidget(self.lens_position_slider, row, 2)
                self.lens_position_spin.valueChanged.connect(self.schedule_live_apply)
                self.lens_position_slider.valueChanged.connect(self.schedule_live_apply)
                row += 1
        except Exception:
            pass

        # Analogue gain
        try:
            gain = getattr(self.cam, 'camera_controls', {}).get('AnalogueGain', None)
            if gain is not None:
                g_min, g_max, g_def = float(gain[0]), float(gain[1]), float(gain[2]) if len(gain) > 2 else float((gain[0]+gain[1])/2)
                self.analogue_gain_check = QCheckBox("Enable analogue gain")
                self.analogue_gain_spin = QDoubleSpinBox()
                self.analogue_gain_spin.setRange(g_min, g_max)
                self.analogue_gain_spin.setSingleStep(0.1)
                self.analogue_gain_spin.setValue(g_def)
                self.analogue_gain_spin.setEnabled(False)
                self.analogue_gain_check.stateChanged.connect(lambda state: self.analogue_gain_spin.setEnabled(bool(state)))
                self.analogue_gain_check.stateChanged.connect(self.schedule_live_apply)
                self.main_layout.addWidget(self.analogue_gain_check, row, 0)
                self.main_layout.addWidget(self.analogue_gain_spin, row, 1)
                self.analogue_gain_slider = QSlider(Qt.Horizontal)
                ag_scale = 100
                self.analogue_gain_slider.setRange(int(g_min*ag_scale), int(g_max*ag_scale))
                self.analogue_gain_slider.setValue(int(g_def*ag_scale))
                self.analogue_gain_slider.valueChanged.connect(lambda v: self.analogue_gain_spin.setValue(v/ag_scale))
                self.analogue_gain_spin.valueChanged.connect(lambda v: self.analogue_gain_slider.setValue(int(v*ag_scale)))
                self.main_layout.addWidget(self.analogue_gain_slider, row, 2)
                self.analogue_gain_spin.valueChanged.connect(self.schedule_live_apply)
                self.analogue_gain_slider.valueChanged.connect(self.schedule_live_apply)
                row += 1
        except Exception:
            pass

        # Brightness
        try:
            bright = getattr(self.cam, 'camera_controls', {}).get('Brightness', None)
            if bright is not None:
                b_min, b_max, b_def = float(bright[0]), float(bright[1]), float(bright[2]) if len(bright) > 2 else 0.0
                self.brightness_spin = QDoubleSpinBox()
                self.brightness_spin.setRange(b_min, b_max)
                self.brightness_spin.setSingleStep(0.1)
                self.brightness_spin.setValue(b_def)
                self.main_layout.addWidget(QLabel("Brightness:"), row, 0)
                self.main_layout.addWidget(self.brightness_spin, row, 1)
                self.brightness_slider = QSlider(Qt.Horizontal)
                b_scale = 100
                self.brightness_slider.setRange(int(b_min*b_scale), int(b_max*b_scale))
                self.brightness_slider.setValue(int(b_def*b_scale))
                self.brightness_slider.valueChanged.connect(lambda v: self.brightness_spin.setValue(v/b_scale))
                self.brightness_spin.valueChanged.connect(lambda v: self.brightness_slider.setValue(int(v*b_scale)))
                self.main_layout.addWidget(self.brightness_slider, row, 2)
                self.brightness_spin.valueChanged.connect(self.schedule_live_apply)
                self.brightness_slider.valueChanged.connect(self.schedule_live_apply)
                row += 1
        except Exception:
            pass

        # Saturation
        try:
            sat = getattr(self.cam, 'camera_controls', {}).get('Saturation', None)
            if sat is not None:
                s_min, s_max, s_def = float(sat[0]), float(sat[1]), float(sat[2]) if len(sat) > 2 else float((sat[0]+sat[1])/2)
                self.saturation_spin = QDoubleSpinBox()
                self.saturation_spin.setRange(s_min, s_max)
                self.saturation_spin.setSingleStep(0.1)
                self.saturation_spin.setValue(s_def)
                self.main_layout.addWidget(QLabel("Saturation:"), row, 0)
                self.main_layout.addWidget(self.saturation_spin, row, 1)
                self.saturation_slider = QSlider(Qt.Horizontal)
                scale = 100
                self.saturation_slider.setRange(int(s_min*scale), int(s_max*scale))
                self.saturation_slider.setValue(int(s_def*scale))
                self.saturation_slider.valueChanged.connect(lambda v: self.saturation_spin.setValue(v/scale))
                self.saturation_spin.valueChanged.connect(lambda v: self.saturation_slider.setValue(int(v*scale)))
                self.main_layout.addWidget(self.saturation_slider, row, 2)
                self.saturation_spin.valueChanged.connect(self.schedule_live_apply)
                self.saturation_slider.valueChanged.connect(self.schedule_live_apply)
                row += 1
        except Exception:
            pass

        # Contrast
        try:
            con = getattr(self.cam, 'camera_controls', {}).get('Contrast', None)
            if con is not None:
                c_min, c_max, c_def = float(con[0]), float(con[1]), float(con[2]) if len(con) > 2 else float((con[0]+con[1])/2)
                self.contrast_spin = QDoubleSpinBox()
                self.contrast_spin.setRange(c_min, c_max)
                self.contrast_spin.setSingleStep(0.1)
                self.contrast_spin.setValue(c_def)
                self.main_layout.addWidget(QLabel("Contrast:"), row, 0)
                self.main_layout.addWidget(self.contrast_spin, row, 1)
                self.contrast_slider = QSlider(Qt.Horizontal)
                scale = 100
                self.contrast_slider.setRange(int(c_min*scale), int(c_max*scale))
                self.contrast_slider.setValue(int(c_def*scale))
                self.contrast_slider.valueChanged.connect(lambda v: self.contrast_spin.setValue(v/scale))
                self.contrast_spin.valueChanged.connect(lambda v: self.contrast_slider.setValue(int(v*scale)))
                self.main_layout.addWidget(self.contrast_slider, row, 2)
                self.contrast_spin.valueChanged.connect(self.schedule_live_apply)
                self.contrast_slider.valueChanged.connect(self.schedule_live_apply)
                row += 1
        except Exception:
            pass

        # Sharpness
        try:
            sharp = getattr(self.cam, 'camera_controls', {}).get('Sharpness', None)
            if sharp is not None:
                sh_min, sh_max, sh_def = float(sharp[0]), float(sharp[1]), float(sharp[2]) if len(sharp) > 2 else float((sharp[0]+sharp[1])/2)
                self.sharpness_spin = QDoubleSpinBox()
                self.sharpness_spin.setRange(sh_min, sh_max)
                self.sharpness_spin.setSingleStep(0.1)
                self.sharpness_spin.setValue(sh_def)
                self.main_layout.addWidget(QLabel("Sharpness:"), row, 0)
                self.main_layout.addWidget(self.sharpness_spin, row, 1)
                self.sharpness_slider = QSlider(Qt.Horizontal)
                scale = 100
                self.sharpness_slider.setRange(int(sh_min*scale), int(sh_max*scale))
                self.sharpness_slider.setValue(int(sh_def*scale))
                self.sharpness_slider.valueChanged.connect(lambda v: self.sharpness_spin.setValue(v/scale))
                self.sharpness_spin.valueChanged.connect(lambda v: self.sharpness_slider.setValue(int(v*scale)))
                self.main_layout.addWidget(self.sharpness_slider, row, 2)
                self.sharpness_spin.valueChanged.connect(self.schedule_live_apply)
                self.sharpness_slider.valueChanged.connect(self.schedule_live_apply)
                row += 1
        except Exception:
            pass

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_to_loaded_config)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addStretch()
        
        self.main_layout.addLayout(btn_layout, row, 0, 1, 3)
        
        self.setLayout(self.main_layout)
        self.resize(700, 500)

    def _get_fps(self, frame_duration_us):
        """Convert frame duration in microseconds to FPS."""
        if frame_duration_us > 0:
            return int(1000000 / frame_duration_us)
        return 30

    def _get_frame_duration(self, fps):
        """Convert FPS to frame duration in microseconds."""
        if fps > 0:
            return int(1000000 / fps)
        return 33333

    def schedule_live_apply(self):
        """Debounce rapid slider changes."""
        self._live_apply_timer.start()

    def _gather_controls(self):
        """Gather current widget values into controls dictionary."""
        controls = {}
        requested_resolution = None
        
        # Frame rate
        if hasattr(self, 'frame_rate_spin'):
            fps = self.frame_rate_spin.value()
            fd = self._get_frame_duration(fps)
            controls['FrameDurationLimits'] = [fd, fd]
        
        # Exposure
        if hasattr(self, 'exposure_time_spin'):
            controls['ExposureTime'] = self.exposure_time_spin.value()
        
        # Lens position
        if hasattr(self, 'lens_position_spin'):
            controls['LensPosition'] = self.lens_position_spin.value()
        
        # Analogue gain
        if hasattr(self, 'analogue_gain_check') and self.analogue_gain_check.isChecked():
            if hasattr(self, 'analogue_gain_spin'):
                controls['AnalogueGain'] = self.analogue_gain_spin.value()
        
        # Brightness
        if hasattr(self, 'brightness_spin'):
            controls['Brightness'] = self.brightness_spin.value()
        
        # Saturation
        if hasattr(self, 'saturation_spin'):
            controls['Saturation'] = self.saturation_spin.value()
        
        # Contrast
        if hasattr(self, 'contrast_spin'):
            controls['Contrast'] = self.contrast_spin.value()
        
        # Sharpness
        if hasattr(self, 'sharpness_spin'):
            controls['Sharpness'] = self.sharpness_spin.value()
        
        # Resolution
        if hasattr(self, 'resolution_combo'):
            requested_resolution = self.resolution_combo.currentData()
            if requested_resolution:
                controls['Resolution'] = list(requested_resolution)
        
        # ScalerCrop (always include default)
        controls['ScalerCrop'] = [0, 0, 3072, 1728]
        
        return controls, requested_resolution

    def _apply_controls_live(self):
        """Apply controls immediately for live updates."""
        try:
            controls, requested_resolution = self._gather_controls()
            picam = getattr(self.cam_widget, 'picam', None)
            
            if picam is None:
                return
            
            # Remove Resolution from controls sent to set_controls
            picam_controls = {k: v for k, v in controls.items() if k != 'Resolution'}
            
            # Store applied controls on camera widget for later retrieval (e.g., for swap function)
            if not hasattr(self.cam_widget, 'applied_controls'):
                self.cam_widget.applied_controls = {}
            self.cam_widget.applied_controls.update(controls)
            
            # Handle resolution change
            if requested_resolution and requested_resolution != self._last_applied_resolution:
                try:
                    picam.stop()
                    config = picam.create_preview_configuration(main={'size': requested_resolution})
                    config['controls'] = picam_controls
                    picam.configure(config)
                    picam.start()
                    self._last_applied_resolution = requested_resolution
                except Exception:
                    pass
            else:
                # Just update controls
                try:
                    picam.set_controls(picam_controls)
                except Exception:
                    pass
        except Exception:
            pass

    def save_to_loaded_config(self):
        """Save current settings to the currently loaded config file.
        
        If a config file was loaded via the Load button, saves to that file.
        Otherwise, saves to default_config.json.
        """
        try:
            controls, _ = self._gather_controls()
            cam_id = str(self.cam_widget.CamDisp_num)
            
            # Determine which file to save to
            loaded_path = getattr(self.cam_widget, 'loaded_config_path', None)
            if loaded_path and Path(loaded_path).exists():
                cfg_path = Path(loaded_path)
            else:
                cfg_path = Path.cwd() / DEFAULT_CONFIG_FILENAME
            
            # Load existing config or create new
            if cfg_path.exists():
                try:
                    data = json.loads(cfg_path.read_text())
                except:
                    data = {}
            else:
                data = {}
            
            # Update this camera's settings
            data[cam_id] = controls
            
            # Save
            cfg_path.write_text(json.dumps(data, indent=2))
            QMessageBox.information(self, "Saved", f"Configuration for Camera {cam_id} saved to {cfg_path.name}")
        except Exception as e:
            QMessageBox.warning(self, "Save Failed", f"Failed to save: {e}")

    def refresh_from_picam(self):
        """Refresh widgets from camera's current state."""
        try:
            picam = getattr(self.cam_widget, 'picam', None)
            cam_id = str(getattr(self.cam_widget, 'CamDisp_num', 'unknown'))
            
            controls = {}
            
            # Priority 1: Check for applied_controls (highest priority - includes swapped values)
            try:
                if hasattr(self.cam_widget, 'applied_controls') and self.cam_widget.applied_controls:
                    controls.update(self.cam_widget.applied_controls)
            except Exception:
                pass
            
            # Priority 2: Try to get current resolution from camera configuration if not in applied_controls
            if 'Resolution' not in controls:
                try:
                    if picam is not None:
                        cam_config = picam.camera_configuration()
                        if cam_config and 'main' in cam_config and 'size' in cam_config['main']:
                            res_from_cam = list(cam_config['main']['size'])
                            controls['Resolution'] = res_from_cam
                except Exception:
                    pass
            
            # Priority 3: Check for loaded config file
            if not controls or 'Resolution' not in controls:
                try:
                    loaded_path = getattr(self.cam_widget, 'loaded_config_path', None)
                    if loaded_path:
                        lp = Path(loaded_path)
                        if lp.exists():
                            try:
                                data = json.loads(lp.read_text())
                                if isinstance(data, dict):
                                    if cam_id in data and isinstance(data[cam_id], dict):
                                        src = data[cam_id]
                                        # Update controls with loaded config values (only for missing keys)
                                        for k, v in src.items():
                                            if k not in controls:
                                                controls[k] = v
                            except Exception:
                                pass
                except Exception:
                    pass
            
            # Priority 4: Fallback to default config
            if 'Resolution' not in controls:
                try:
                    cfg_path = Path.cwd() / DEFAULT_CONFIG_FILENAME
                    if cfg_path.exists():
                        existing = json.loads(cfg_path.read_text())
                        if cam_id in existing and isinstance(existing[cam_id], dict):
                            for k, v in existing[cam_id].items():
                                if k not in controls:
                                    controls[k] = v
                except Exception:
                    pass
            
            # Populate widgets
            def safe_set(widget, value):
                try:
                    widget.blockSignals(True)
                    widget.setValue(value)
                except Exception:
                    pass
                finally:
                    try:
                        widget.blockSignals(False)
                    except Exception:
                        pass
            
            if 'FrameDurationLimits' in controls and hasattr(self, 'frame_rate_spin'):
                fd = controls['FrameDurationLimits'][0]
                fps = self._get_fps(fd)
                safe_set(self.frame_rate_spin, fps)
                if hasattr(self, 'frame_rate_slider'):
                    safe_set(self.frame_rate_slider, fps)
            
            if 'ExposureTime' in controls and hasattr(self, 'exposure_time_spin'):
                safe_set(self.exposure_time_spin, int(controls['ExposureTime']))
                if hasattr(self, 'exposure_time_slider'):
                    safe_set(self.exposure_time_slider, int(controls['ExposureTime']))
            
            if 'LensPosition' in controls and hasattr(self, 'lens_position_spin'):
                safe_set(self.lens_position_spin, float(controls['LensPosition']))
                if hasattr(self, 'lens_position_slider'):
                    lp_scale = 10
                    safe_set(self.lens_position_slider, int(float(controls['LensPosition']) * lp_scale))
            
            if 'AnalogueGain' in controls and hasattr(self, 'analogue_gain_spin'):
                safe_set(self.analogue_gain_spin, float(controls['AnalogueGain']))
                if hasattr(self, 'analogue_gain_slider'):
                    ag_scale = 100
                    safe_set(self.analogue_gain_slider, int(float(controls['AnalogueGain']) * ag_scale))
                if hasattr(self, 'analogue_gain_check'):
                    safe_set(self.analogue_gain_check, True)
            
            if 'Brightness' in controls and hasattr(self, 'brightness_spin'):
                safe_set(self.brightness_spin, float(controls['Brightness']))
                if hasattr(self, 'brightness_slider'):
                    b_scale = 100
                    safe_set(self.brightness_slider, int(float(controls['Brightness']) * b_scale))
            
            if 'Saturation' in controls and hasattr(self, 'saturation_spin'):
                safe_set(self.saturation_spin, float(controls['Saturation']))
                if hasattr(self, 'saturation_slider'):
                    s_scale = 100
                    safe_set(self.saturation_slider, int(float(controls['Saturation']) * s_scale))
            
            if 'Contrast' in controls and hasattr(self, 'contrast_spin'):
                safe_set(self.contrast_spin, float(controls['Contrast']))
                if hasattr(self, 'contrast_slider'):
                    c_scale = 100
                    safe_set(self.contrast_slider, int(float(controls['Contrast']) * c_scale))
            
            if 'Sharpness' in controls and hasattr(self, 'sharpness_spin'):
                safe_set(self.sharpness_spin, float(controls['Sharpness']))
                if hasattr(self, 'sharpness_slider'):
                    sh_scale = 100
                    safe_set(self.sharpness_slider, int(float(controls['Sharpness']) * sh_scale))
            
            if 'Resolution' in controls and hasattr(self, 'resolution_combo'):
                try:
                    target_res = tuple(controls['Resolution'])
                    self.resolution_combo.blockSignals(True)
                    # Find and set the matching resolution
                    found = False
                    for i in range(self.resolution_combo.count()):
                        if self.resolution_combo.itemData(i) == target_res:
                            self.resolution_combo.setCurrentIndex(i)
                            found = True
                            break
                    # If resolution not in preset list, keep current selection
                    if not found:
                        print(f"[config] Warning: Resolution {target_res} not found in preset list for camera {cam_id}")
                    self.resolution_combo.blockSignals(False)
                except Exception as e:
                    print(f"[config] Error setting resolution combo: {e}")
                    pass
                    
        except Exception:
            pass

    def dump_diagnostics(self):
        """Print diagnostic information to terminal."""
        try:
            print(f"\n=== Camera {self.cam_widget.CamDisp_num} Diagnostics ===")
            picam = getattr(self.cam_widget, 'picam', None)
            if picam:
                try:
                    controls = picam.get_controls()
                    print(f"Current controls: {controls}")
                except:
                    print("Could not get controls")
                
                try:
                    print(f"Camera controls: {picam.camera_controls}")
                except:
                    pass
            else:
                print("No picam found")
        except Exception as e:
            print(f"Diagnostics error: {e}")


class ConfigSetupWidget(QWidget):
    """Control bar widget for loading/saving camera settings.
    
    Displays the currently loaded settings file and provides buttons for:
    - Load: Open file browser to load a JSON settings file
    - Save as...: Save current settings to a user-selected file
    - Modify settings: Open dialog to adjust camera settings
    
    Args:
        data_manager: Application data manager instance
        cam: Reference camera widget
    """
    
    def __init__(self, data_manager, cam):
        super().__init__()
        self.data_manager = data_manager
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.setMinimumHeight(int(self.data_manager.main_window_size['H']*1/18))
        self.cam = cam
        self._modify_callback = None
        self._all_cameras = []  # Will be populated externally with all camera widgets

        layout = QGridLayout()

        current_config_label = QLabel("Current settings:")
        self.current_config_edit = QLineEdit(DEFAULT_CONFIG_FILENAME)
        self.current_config_edit.setEnabled(False)
        self.current_config_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        self.load_btn = QPushButton("Load settings")
        self.load_btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.load_btn.setStyleSheet("background-color: #E0E0E0; color: black; padding: 5px;")
        self.load_btn.clicked.connect(self.open_and_load_config)

        self.modify_btn = QPushButton("Modify settings")
        self.modify_btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.modify_btn.setStyleSheet("background-color: #E0E0E0; color: black; padding: 5px;")
        self.modify_btn.clicked.connect(self._on_modify_clicked)

        self.swap_btn = QPushButton("Swap Room 1 ↔ Room 2 settings")
        self.swap_btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.swap_btn.setStyleSheet("background-color: #FFD700; color: black; padding: 5px;")
        self.swap_btn.clicked.connect(self._on_swap_clicked)
        self.swap_btn.clicked.connect(self._on_swap_clicked)

        # New layout:
        # Row 0: (empty)
        # Row 1: Current Settings | Load Field
        # Row 2: Load Settings
        # Row 3: Modify Settings
        # Row 4: Swap Settings
        layout.addWidget(current_config_label, 1, 0)
        layout.addWidget(self.current_config_edit, 1, 1)
        layout.addWidget(self.load_btn, 2, 0, 1, 2)  # span 2 columns
        layout.addWidget(self.modify_btn, 3, 0, 1, 2)  # span 2 columns
        layout.addWidget(self.swap_btn, 4, 0, 1, 2)  # span 2 columns

        self.setLayout(layout)
        
        # Auto-load default_config.json after widget is fully initialized
        # Use QTimer.singleShot to defer until event loop starts
        QTimer.singleShot(0, self._auto_load_default_config)

    def set_modify_callback(self, callback):
        """Set custom callback for modify button."""
        self._modify_callback = callback
    
    def set_all_cameras(self, cameras):
        """Set list of all camera widgets for config loading.
        
        Args:
            cameras: List of Camera widgets to apply config to
        """
        self._all_cameras = cameras

    def _on_modify_clicked(self):
        """Handle modify button click."""
        if self._modify_callback:
            self._modify_callback()
        else:
            self.cam.config_pop()
    
    def _on_swap_clicked(self):
        """Swap settings between Room 1 (LightRoom) and Room 2 (DarkRoom)."""
        if len(self._all_cameras) < 2:
            QMessageBox.warning(self, "Swap Failed", "Need two cameras to swap settings.")
            return
        
        cam1 = self._all_cameras[0]
        cam2 = self._all_cameras[1]
        
        try:
            import copy
            
            # Extract current settings from both cameras
            def get_camera_config(cam):
                config = {}
                try:
                    # Get current camera configuration for resolution
                    cam_config = cam.picam.camera_configuration()
                    if cam_config and 'main' in cam_config and 'size' in cam_config['main']:
                        config['Resolution'] = list(cam_config['main']['size'])
                    
                    # Get stored applied controls (if any were set via modify settings dialog)
                    if hasattr(cam, 'applied_controls'):
                        config.update(cam.applied_controls)
                        print(f"Camera {cam.CamDisp_num} applied_controls: {cam.applied_controls}")
                    else:
                        print(f"Camera {cam.CamDisp_num} has no stored applied_controls")
                except Exception as e:
                    print(f"Error getting config from camera {cam.CamDisp_num}: {e}")
                    import traceback
                    traceback.print_exc()
                return config
            
            # Get configs and make deep copies to avoid reference issues
            config1 = get_camera_config(cam1)
            config2 = get_camera_config(cam2)
            
            # Make deep copies before swapping
            config1_copy = copy.deepcopy(config1)
            config2_copy = copy.deepcopy(config2)
            
            print(f"Config 1 before swap: {config1_copy}")
            print(f"Config 2 before swap: {config2_copy}")
            
            # Apply swapped configurations
            def apply_config(cam, config):
                try:
                    requested_resolution = config.get('Resolution')
                    picam_controls = {k: v for k, v in config.items() if k != 'Resolution'}
                    
                    print(f"Applying to camera {cam.CamDisp_num}: resolution={requested_resolution}, controls={picam_controls}")
                    
                    # Store the swapped controls on the camera (deep copy to avoid reference issues)
                    cam.applied_controls = copy.deepcopy(config)
                    
                    if hasattr(cam, 'picam') and hasattr(cam.picam, 'started') and cam.picam.started:
                        # Apply controls
                        if picam_controls:
                            cam.picam.set_controls(picam_controls)
                            print(f"Applied controls to camera {cam.CamDisp_num}")
                        
                        # Handle resolution change if needed
                        if requested_resolution:
                            current_config = cam.picam.camera_configuration()
                            current_res = current_config.get('main', {}).get('size')
                            if current_res != tuple(requested_resolution):
                                print(f"Changing resolution from {current_res} to {requested_resolution}")
                                cam.requested_preview_size = tuple(requested_resolution)
                                cam.initialize_preview()
                except Exception as e:
                    print(f"Error applying config to camera {cam.CamDisp_num}: {e}")
                    import traceback
                    traceback.print_exc()
                    raise
            
            # Swap and apply using the deep copies
            apply_config(cam1, config2_copy)
            apply_config(cam2, config1_copy)
            
            QMessageBox.information(self, "Settings Swapped", 
                                  "Room 1 and Room 2 settings have been swapped successfully.")
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Swap Failed", f"Failed to swap settings: {e}")
    
    def _auto_load_default_config(self):
        """Automatically load default_config.json at startup if it exists.
        
        Silently loads the default configuration without showing any dialogs.
        This ensures the camera preview starts with the correct resolution.
        """
        default_config_path = Path.cwd() / DEFAULT_CONFIG_FILENAME
        if not default_config_path.exists():
            return
        
        try:
            self._load_config_from_file(str(default_config_path), silent=True)
        except Exception as e:
            # Silently fail - don't disrupt startup if config load fails
            print(f"[config] Warning: Could not auto-load {DEFAULT_CONFIG_FILENAME}: {e}")

    def open_and_load_config(self):
        """Open file dialog to load camera configuration from JSON.
        
        Validates file structure, applies settings to camera hardware immediately,
        and updates UI widgets to reflect loaded values.
        """
        fname, _ = QFileDialog.getOpenFileName(self, "Open configuration file", str(Path.cwd()), "JSON Files (*.json);;All Files (*)")
        if not fname:
            return
        
        self._load_config_from_file(fname, silent=False)
    
    def _load_config_from_file(self, fname, silent=False):
        """Load configuration from a file.
        
        Args:
            fname: Path to the configuration file
            silent: If True, suppress all dialog boxes (for auto-load at startup)
        """
        try:
            data = json.loads(Path(fname).read_text())
        except json.JSONDecodeError as e:
            if not silent:
                QMessageBox.warning(self, "Load Failed", f"Invalid JSON format: {e}")
            return
        except Exception as e:
            if not silent:
                QMessageBox.warning(self, "Load Failed", f"Failed to read JSON file: {e}")
            return

        # Validate mapping format
        if not isinstance(data, dict):
            if not silent:
                QMessageBox.warning(self, "Invalid Format", "Config file must be a JSON object (dictionary).")
            return
        
        expected_control_keys = {'FrameDurationLimits', 'ExposureTime', 'LensPosition', 'AnalogueGain', 'Brightness', 'Resolution'}
        is_mapping = any(isinstance(v, dict) for v in data.values())
        
        if not is_mapping:
            if not silent:
                if expected_control_keys.intersection(set(data.keys())):
                    QMessageBox.warning(self, "Invalid Format", 
                        "This appears to be a legacy single-camera config file.\n"
                        "Please convert it to the new format: a mapping of camera IDs to controls.\n"
                        "Example: {\"0\": {...controls...}, \"1\": {...controls...}}")
                else:
                    QMessageBox.warning(self, "Invalid Format", 
                        "Config file must map camera IDs to control dictionaries.\n"
                        "Example: {\"0\": {\"FrameDurationLimits\": [...], ...}, \"1\": {...}}")
            return
        
        # Validate each camera entry
        try:
            for cam_id, controls in data.items():
                if not isinstance(controls, dict):
                    if not silent:
                        QMessageBox.warning(self, "Invalid Format", 
                            f"Camera ID '{cam_id}' entry must be a dictionary of controls.")
                    return
                
                if 'FrameDurationLimits' in controls:
                    v = controls['FrameDurationLimits']
                    if not (isinstance(v, (list, tuple)) and len(v) >= 1):
                        raise ValueError(f"FrameDurationLimits for camera {cam_id} must be a list/tuple")
                
                for key in ['ExposureTime', 'LensPosition', 'AnalogueGain', 'Brightness']:
                    if key in controls:
                        _ = float(controls[key])
                
                if 'Resolution' in controls:
                    r = controls['Resolution']
                    if not (isinstance(r, (list, tuple)) and len(r) == 2):
                        raise ValueError(f"Resolution for camera {cam_id} must be [width, height]")
        except (ValueError, TypeError) as e:
            if not silent:
                QMessageBox.warning(self, "Invalid Format", f"Configuration validation failed: {e}")
            return
        except Exception as e:
            if not silent:
                QMessageBox.warning(self, "Invalid Format", f"Error validating configuration: {e}")
            return
        
        # Store loaded config info
        try:
            self._loaded_config_path = fname
            self._loaded_config_data = data
        except Exception:
            pass
        
        # Update UI field
        try:
            if hasattr(self, 'current_config_edit'):
                self.current_config_edit.setText(Path(fname).name)
        except Exception:
            pass
        
        # Apply to cameras
        cameras_to_update = []
        
        # Try to get cameras from direct reference first
        if self._all_cameras:
            cameras_to_update = [(f"cam_{i}", cam) for i, cam in enumerate(self._all_cameras)]
        else:
            # Fallback: try to find via window hierarchy
            try:
                main_window = self.window()
                if hasattr(main_window, 'camera_widget') and hasattr(main_window.camera_widget, 'camera_widgets'):
                    cameras_to_update = list(main_window.camera_widget.camera_widgets.items())
            except Exception:
                pass
        
        if cameras_to_update:
            try:
                resolution_changed = False
                for room, cam in cameras_to_update:
                    cam_id = str(cam.CamDisp_num)
                    if cam_id in data:
                        controls = data[cam_id]
                        
                        # Store applied controls on camera widget for swap functionality
                        if not hasattr(cam, 'applied_controls'):
                            cam.applied_controls = {}
                        cam.applied_controls.update(controls)
                        
                        # Store on camera widget
                        try:
                            cam.loaded_config_path = fname
                        except Exception:
                            pass
                        
                        # Store requested_preview_size for next preview initialization
                        try:
                            requested_resolution = controls.get('Resolution')
                            if requested_resolution:
                                cam.requested_preview_size = tuple(requested_resolution)
                        except Exception:
                            pass
                        
                        # Apply to hardware (if preview is already running)
                        try:
                            requested_resolution = controls.get('Resolution')
                            picam_controls = {k: v for k, v in controls.items() if k != 'Resolution'}
                            
                            # Check if picam is already started (preview is running)
                            if hasattr(cam, 'picam') and hasattr(cam.picam, 'started') and cam.picam.started:
                                if requested_resolution:
                                    current_config = cam.picam.create_preview_configuration()
                                    if current_config.get('main', {}).get('size') != tuple(requested_resolution):
                                        current_config['main']['size'] = tuple(requested_resolution)
                                        current_config['controls'] = picam_controls
                                        cam.picam.stop()
                                        cam.picam.configure(current_config)
                                        cam.picam.start()
                                        resolution_changed = True
                                    else:
                                        cam.picam.set_controls(picam_controls)
                                else:
                                    cam.picam.set_controls(picam_controls)
                        except Exception:
                            pass
                        
                        # Populate popup if exists
                        popup = getattr(cam, 'configuration_popup', None)
                        if popup is not None:
                            self._populate_popup_from_controls(popup, controls)
                
                # Show warning if resolution was changed (only if not silent)
                if resolution_changed and not silent:
                    QMessageBox.information(self, "Resolution Changed", 
                        "The camera resolution has been changed.\n\n"
                        "You may need to restart the program for the preview window size to update properly.")
            except Exception:
                pass
        
        if not silent:
            QMessageBox.information(self, "Loaded", 
                f"Configuration loaded and applied from {Path(fname).name}.\n"
                f"Found settings for {len(data)} camera(s).")

    def _populate_popup_from_controls(self, popup, controls):
        """Populate ConfigPopup widgets from controls dictionary."""
        try:
            widgets_to_block = []
            for attr in dir(popup):
                widget = getattr(popup, attr, None)
                if widget is not None and hasattr(widget, 'blockSignals'):
                    try:
                        widgets_to_block.append(widget)
                        widget.blockSignals(True)
                    except Exception:
                        pass
            
            if 'FrameDurationLimits' in controls and hasattr(popup, 'frame_rate_spin'):
                try:
                    fd = controls['FrameDurationLimits'][0]
                    fps = popup._get_fps(fd) if hasattr(popup, '_get_fps') else int(1000000 / fd)
                    popup.frame_rate_spin.setValue(fps)
                    if hasattr(popup, 'frame_rate_slider'):
                        popup.frame_rate_slider.setValue(fps)
                except Exception:
                    pass
            
            if 'ExposureTime' in controls and hasattr(popup, 'exposure_time_spin'):
                try:
                    popup.exposure_time_spin.setValue(int(controls['ExposureTime']))
                    if hasattr(popup, 'exposure_time_slider'):
                        popup.exposure_time_slider.setValue(int(controls['ExposureTime']))
                except Exception:
                    pass
            
            if 'LensPosition' in controls and hasattr(popup, 'lens_position_spin'):
                try:
                    popup.lens_position_spin.setValue(float(controls['LensPosition']))
                    if hasattr(popup, 'lens_position_slider'):
                        lp_scale = 10
                        popup.lens_position_slider.setValue(int(float(controls['LensPosition']) * lp_scale))
                except Exception:
                    pass
            
            if 'AnalogueGain' in controls and hasattr(popup, 'analogue_gain_spin'):
                try:
                    popup.analogue_gain_spin.setValue(float(controls['AnalogueGain']))
                    if hasattr(popup, 'analogue_gain_slider'):
                        ag_scale = 100
                        popup.analogue_gain_slider.setValue(int(float(controls['AnalogueGain']) * ag_scale))
                    if hasattr(popup, 'analogue_gain_check'):
                        popup.analogue_gain_check.setChecked(True)
                except Exception:
                    pass
            
            if 'Brightness' in controls and hasattr(popup, 'brightness_spin'):
                try:
                    popup.brightness_spin.setValue(float(controls['Brightness']))
                    if hasattr(popup, 'brightness_slider'):
                        b_scale = 100
                        popup.brightness_slider.setValue(int(float(controls['Brightness']) * b_scale))
                except Exception:
                    pass
            
            if 'Saturation' in controls and hasattr(popup, 'saturation_spin'):
                try:
                    popup.saturation_spin.setValue(float(controls['Saturation']))
                    if hasattr(popup, 'saturation_slider'):
                        s_scale = 100
                        popup.saturation_slider.setValue(int(float(controls['Saturation']) * s_scale))
                except Exception:
                    pass
            
            if 'Contrast' in controls and hasattr(popup, 'contrast_spin'):
                try:
                    popup.contrast_spin.setValue(float(controls['Contrast']))
                    if hasattr(popup, 'contrast_slider'):
                        c_scale = 100
                        popup.contrast_slider.setValue(int(float(controls['Contrast']) * c_scale))
                except Exception:
                    pass
            
            if 'Sharpness' in controls and hasattr(popup, 'sharpness_spin'):
                try:
                    popup.sharpness_spin.setValue(float(controls['Sharpness']))
                    if hasattr(popup, 'sharpness_slider'):
                        sh_scale = 100
                        popup.sharpness_slider.setValue(int(float(controls['Sharpness']) * sh_scale))
                except Exception:
                    pass
            
            if 'Resolution' in controls and hasattr(popup, 'resolution_combo'):
                try:
                    target_res = tuple(controls['Resolution'])
                    for i in range(popup.resolution_combo.count()):
                        if popup.resolution_combo.itemData(i) == target_res:
                            popup.resolution_combo.setCurrentIndex(i)
                            break
                except Exception:
                    pass
            
            for widget in widgets_to_block:
                try:
                    widget.blockSignals(False)
                except Exception:
                    pass
        except Exception:
            pass


class CombinedConfigDialog(QDialog):
    """Tabbed dialog for configuring multiple cameras simultaneously.
    
    Presents ConfigPopup instances for each camera in separate tabs.
    Each tab is refreshed from the camera's current state when opened.
    
    Args:
        data_manager: Application data manager instance
        cam1: First camera widget
        cam2: Second camera widget
        parent: Optional parent widget
    """
    
    def __init__(self, data_manager, cam1, cam2, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Modify settings (both cameras)")
        self.resize(900, 600)
        self.data_manager = data_manager
        self.cam1 = cam1
        self.cam2 = cam2

        layout = QVBoxLayout(self)
        tabs = QTabWidget(self)

        # Create tabs
        tab1 = None
        tab2 = None
        try:
            tab1 = ConfigPopup(self.data_manager, self.cam1, parent=self)
            try:
                tab1.refresh_from_picam()
            except Exception:
                pass
            tabs.addTab(tab1, f"Camera {getattr(self.cam1, 'CamDisp_num', '1')}")
        except Exception:
            placeholder1 = QWidget()
            tabs.addTab(placeholder1, "Camera 1")
        
        try:
            tab2 = ConfigPopup(self.data_manager, self.cam2, parent=self)
            try:
                tab2.refresh_from_picam()
            except Exception:
                pass
            tabs.addTab(tab2, f"Camera {getattr(self.cam2, 'CamDisp_num', '2')}")
        except Exception:
            placeholder2 = QWidget()
            tabs.addTab(placeholder2, "Camera 2")

        layout.addWidget(tabs)

        # Buttons
        btn_layout = QHBoxLayout()
        
        # Save All button
        save_all_btn = QPushButton("Save All")
        save_all_btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        save_all_btn.setStyleSheet("background-color: #90EE90; color: black; font-weight: bold; padding: 5px 15px;")
        save_all_btn.clicked.connect(self._save_all_cameras)
        btn_layout.addWidget(save_all_btn)
        
        # Save As button
        save_as_btn = QPushButton("Save As...")
        save_as_btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        save_as_btn.setStyleSheet("background-color: #ADD8E6; color: black; font-weight: bold; padding: 5px 15px;")
        save_as_btn.clicked.connect(self._save_as_new_file)
        btn_layout.addWidget(save_as_btn)
        
        btn_layout.addStretch(1)
        
        diag_btn = QPushButton("Diagnostics")
        diag_btn.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        diag_btn.setStyleSheet("background-color: #E0E0E0; color: black; padding: 5px 15px;")
        diag_btn.clicked.connect(self._run_diagnostics)
        btn_layout.addWidget(diag_btn)
        
        layout.addLayout(btn_layout)

        # Store tabs
        self._tab_widgets = []
        try:
            for i in range(tabs.count()):
                w = tabs.widget(i)
                self._tab_widgets.append(w)
        except Exception:
            pass

    def _save_all_cameras(self):
        """Save settings for all cameras to the currently loaded config file."""
        try:
            # Determine which file to save to (check first camera for loaded path)
            loaded_path = getattr(self.cam1, 'loaded_config_path', None)
            if loaded_path and Path(loaded_path).exists():
                cfg_path = Path(loaded_path)
            else:
                cfg_path = Path.cwd() / DEFAULT_CONFIG_FILENAME
            
            # Load existing config or create new
            if cfg_path.exists():
                try:
                    data = json.loads(cfg_path.read_text())
                except:
                    data = {}
            else:
                data = {}
            
            # Gather and save settings from all tabs
            saved_count = 0
            for tab_widget in self._tab_widgets:
                if hasattr(tab_widget, '_gather_controls') and hasattr(tab_widget, 'cam_widget'):
                    try:
                        controls, _ = tab_widget._gather_controls()
                        cam_id = str(tab_widget.cam_widget.CamDisp_num)
                        data[cam_id] = controls
                        saved_count += 1
                    except Exception as e:
                        print(f"Error gathering controls for camera: {e}")
            
            if saved_count > 0:
                # Save to file
                cfg_path.write_text(json.dumps(data, indent=2))
                QMessageBox.information(self, "Saved", 
                    f"Configuration for {saved_count} camera(s) saved to {cfg_path.name}")
            else:
                QMessageBox.warning(self, "Save Failed", "No camera configurations found to save.")
                
        except Exception as e:
            QMessageBox.warning(self, "Save Failed", f"Failed to save all cameras: {e}")

    def _save_as_new_file(self):
        """Save settings for all cameras to a new user-selected file."""
        fname, _ = QFileDialog.getSaveFileName(self, "Save configuration as", str(Path.cwd()), "JSON Files (*.json)")
        if not fname:
            return
        
        try:
            # Ensure .json extension
            fname_path = Path(fname)
            if fname_path.suffix.lower() != '.json':
                fname_path = fname_path.with_suffix('.json')
            
            # Gather settings from all tabs
            data = {}
            saved_count = 0
            
            for tab_widget in self._tab_widgets:
                if hasattr(tab_widget, '_gather_controls') and hasattr(tab_widget, 'cam_widget'):
                    try:
                        controls, _ = tab_widget._gather_controls()
                        cam_id = str(tab_widget.cam_widget.CamDisp_num)
                        data[cam_id] = controls
                        saved_count += 1
                    except Exception as e:
                        print(f"Error gathering controls for camera: {e}")
            
            if saved_count > 0:
                # Save to file
                fname_path.write_text(json.dumps(data, indent=2))
                
                # Update the loaded config path on all camera widgets
                fname_str = str(fname_path)
                try:
                    self.cam1.loaded_config_path = fname_str
                except Exception:
                    pass
                    
                try:
                    self.cam2.loaded_config_path = fname_str
                except Exception:
                    pass
                
                # Update the ConfigSetupWidget display to show the new file
                try:
                    setup_widget = None
                    if hasattr(self.cam1, 'setup_widget'):
                        setup_widget = self.cam1.setup_widget
                    elif hasattr(self.cam2, 'setup_widget'):
                        setup_widget = self.cam2.setup_widget
                    
                    if setup_widget and hasattr(setup_widget, 'current_config_edit'):
                        setup_widget.current_config_edit.setText(fname_path.name)
                        
                except Exception as e:
                    print(f"Error updating GUI display: {e}")
                
                QMessageBox.information(self, "Saved", 
                    f"Configuration for {saved_count} camera(s) saved to {fname_path.name}")
            else:
                QMessageBox.warning(self, "Save Failed", "No camera configurations found to save.")
                
        except Exception as e:
            QMessageBox.warning(self, "Save Failed", f"Failed to save as new file: {e}")

    def _run_diagnostics(self):
        """Run diagnostics for both cameras."""
        try:
            for w in getattr(self, '_tab_widgets', []):
                try:
                    if hasattr(w, 'dump_diagnostics'):
                        w.dump_diagnostics()
                except Exception:
                    pass
        except Exception:
            pass
