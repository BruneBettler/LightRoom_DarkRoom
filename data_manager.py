from PyQt5.QtCore import QObject, pyqtSignal, QTime 
import time


class DataManager(QObject):
    """
    Object contains all global datas to be shared across the entire GUI.
    Store information about 
    """
    neuron_connectivity_updated = pyqtSignal()
    is_running_updated = pyqtSignal()
    start_time_updated = pyqtSignal(QTime)


    def __init__(self):
        super().__init__()

        self.stop_method = None  # "Manual" or "Timer"
        self.timer_duration = None  # Duration in seconds if stop_method is "Timer"
        self.save_path = None
        self.is_running = [None, None]  # [cam 0, cam 1] Bool
        self.start_time = [None, None]  # [cam 0 QTime, cam 1 QTime]
        self.start_date = None

        self.LR_camera_settings = {
                    "disp_num": 0,
                    "status": None,
                    "focus": None,
                    "frame_rate": None, 
                    "exposure": None, 
                    "zoom": None}
        self.DR_camera_settings = {
                    "disp_num": 1, 
                    "status": None,
                    "focus": None,
                    "frame_rate": None, 
                    "exposure": None, 
                    "zoom": None}

    def set_start_time(self, cam_num, QTime_time):
        self.start_time[cam_num] = QTime_time
        self.start_time_updated.emit()
    
    def set_start_date(self, QDate_date):
        self.start_date = QDate_date

    def set_is_running(self, is_running):
        """
        Set the running status of the application.
        :param is_running: Boolean indicating if the application is running
        """
        self.is_running = is_running
        self.is_running_updated.emit()


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
        
        
