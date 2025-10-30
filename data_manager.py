from PyQt5.QtCore import QObject, pyqtSignal, QTime, QDateTime
import time
import json

class DataManager(QObject):
    """
    Object contains all global datas to be shared across the entire GUI.
    Store information about 
    """
    neuron_connectivity_updated = pyqtSignal()
    start_stop_toggled_signal = pyqtSignal()
    save_path_updated = pyqtSignal()
    start_time_updated = pyqtSignal(dict)

    def __init__(self):
        super().__init__()

        self.main_window_size = {'H': 1000, 'W': 1500}

        self.stop_method = "Manual"  # "Manual" or "Timer"
        self.timer_duration = None  # Duration in seconds if stop_method is "Timer"
        self.recording_delay = 0  # Countdown delay in seconds before recording starts
        self.save_path = None
        self.session_name = None  # Name of the current recording session
        self.is_running = {"LightRoom": None, "DarkRoom": None}
        self.recording_started = False
        self.start_time = {"LightRoom": None, "DarkRoom": None}
        self.end_time = {"LightRoom": None, "DarkRoom": None}
        self.start_date = None
        self.start_datetime = None  # QDateTime when recording actually started
        self.end_datetime = None    # QDateTime when recording ended
        
        # Camera configuration snapshots at recording time
        self.recording_configs = {"LightRoom": None, "DarkRoom": None}

        self.camera_settings = {
            "LightRoom":{
                    "disp_num": None,
                    "status": None,
                    "focus": None,
                    "frame_rate": None, 
                    "exposure": None, 
                    "zoom": None},
            "DarkRoom":{
                    "disp_num": None, 
                    "status": None,
                    "focus": None,
                    "frame_rate": None, 
                    "exposure": None, 
                    "zoom": None}}

    def set_start_time(self, room, QTime_time):
        self.start_time[room] = QTime_time
        self.start_time_updated.emit(self.start_time)
    
    def set_end_time(self, room, QTime_time):
        """
        Set the end time for a camera recording.
        :param room: "LightRoom" or "DarkRoom"
        :param QTime_time: QTime object representing the end time
        """
        self.end_time[room] = QTime_time
    
    def set_start_date(self, QDate_date):
        self.start_date = QDate_date
    
    def set_start_datetime(self, datetime_obj):
        """
        Set the start datetime for the recording session.
        :param datetime_obj: QDateTime object
        """
        self.start_datetime = datetime_obj
    
    def set_end_datetime(self, datetime_obj):
        """
        Set the end datetime for the recording session.
        :param datetime_obj: QDateTime object
        """
        self.end_datetime = datetime_obj
    
    def set_recording_config(self, room, config_dict):
        """
        Store a snapshot of the camera configuration at recording time.
        :param room: "LightRoom" or "DarkRoom"
        :param config_dict: Dictionary containing camera configuration
        """
        self.recording_configs[room] = config_dict

    def set_is_running(self, room, is_running):
        """
        Set the running status of the application.
        :param is_running: Boolean indicating if the application is running
        """
        self.is_running[room] = is_running

    def set_save_path(self, path):
        """
        Set the save path for the videos.
        :param path: Path to the directory where videos will be saved
        """
        self.save_path = path
        self.save_path_updated.emit()
    
    def save_data(self):
        """
        save all information as a json file along with the videos 
        """
        return 0 
    
    def set_stop_method(self, method):
        """
        Set the stop method for video recording.
        :param method: "Manual" or "Timer"
        """
        self.stop_method = method
    
    def get_timer_duration(self):
        """
        Get the remaining time in minutes and seconds if stop_method is "Timer".
        :return: Remaining time as a formatted string "MM:SS"
        """
        # handle unset timer
        if self.timer_duration is None:
            return "00:00"

        # timer_duration is stored in minutes (can be float). Convert to total seconds
        try:
            total_seconds = int(float(self.timer_duration) * 60)
        except Exception:
            return "00:00"

        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02}:{seconds:02}"

      
    def set_timer_duration(self, duration):
        """
        Set the timer duration for video recording.
        :param duration: Duration in minutes (float)
        """
        self.timer_duration = duration
    
    def set_recording_delay(self, delay):
        """
        Set the countdown delay before recording starts.
        :param delay: Delay in seconds (int)
        """
        self.recording_delay = delay
    
    def set_session_name(self, name):
        """
        Set the session name for the current recording.
        :param name: Session name string
        """
        self.session_name = name
    
    def get_session_file_path(self, camera_name):
        """
        Get the full file path for a camera recording based on session name.
        :param camera_name: "camera_1" or "camera_2"
        :return: Full path to the video file
        """
        if self.save_path is None or self.session_name is None:
            return None
        
        from pathlib import Path
        save_dir = Path(self.save_path)
        filename = f"{self.session_name}_{camera_name}.h264"
        return str(save_dir / filename)
        
        
