from PyQt5.QtCore import QObject, pyqtSignal, QTime 
import time


class DataManager(QObject):
    """
    Object contains all global datas to be shared across the entire GUI.
    Store information about 
    """
    neuron_connectivity_updated = pyqtSignal()
    start_stop_toggled = pyqtSignal()
    save_path_updated = pyqtSignal()
    timer_timeout = pyqtSignal() 


    def __init__(self):
        super().__init__()

        self.stop_method = "Manual"  # "Manual" or "Timer"
        self.timer_duration = None  # Duration in seconds if stop_method is "Timer"
        self.save_path = None
        self.is_running = {"LightRoom": None, "DarkRoom": None}
        self.recording_started = False
        self.start_time = {"LightRoom": None, "DarkRoom": None}  
        self.start_date = None

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
    
    def set_start_date(self, QDate_date):
        self.start_date = QDate_date

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
        str_time = str(self.timer_duration)
        str_minutes, str_seconds = str_time.split(".")
        return f"{str_minutes:02}:{str_seconds:02}"    

      
    def set_timer_duration(self, duration):
        """
        Set the timer duration for video recording.
        :param duration: Duration in minutes (float)
        """
        self.timer_duration = duration
        
        
