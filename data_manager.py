from PyQt5.QtCore import QObject, pyqtSignal 


class DataManager(QObject):
    """
    Object contains all global data to be shared across the entire GUI.
    Store information about 
    """
    neuron_connectivity_updated = pyqtSignal()


    def __init__(self):
        super().__init__()

        self.record_method = ""
        self.save_path = None
        self.is_running = False
        self.start_datetime = None

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


    def save_data(self, ):
        """
        save all information as a json file along with the videos 
        """
        return 0 

      
        
        
        
