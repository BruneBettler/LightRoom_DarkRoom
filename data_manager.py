from PyQt5.QtCore import QObject, pyqtSignal 
import time


class DataManager(QObject):
    """
    Object contains all global data to be shared across the entire GUI.
    Store information about 
    """
    neuron_connectivity_updated = pyqtSignal()


    def __init__(self):
        super().__init__()

        self.stop_method = None  # "Manual" or "Timer"
        self.timer_duration = None  # Duration in seconds if stop_method is "Timer"
        self.save_path = None
        self.is_running = False
        self.start_time = None
        self.start_date = None

        self.camera_settings = {
            "LightRoom": {
                    "status": None,
                    "focus": None,
                    "frame_rate": None, 
                    "exposure": None, 
                    "zoom": None},
            "darkRoom": {
                    "status": None,
                    "focus": None,
                    "frame_rate": None, 
                    "exposure": None, 
                    "zoom": None}}


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
        
        
