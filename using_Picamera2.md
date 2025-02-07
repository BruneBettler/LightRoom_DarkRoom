# Getting started with Picamera2

This file will contain notes useful to get started with Picamera2 for our particular implementation: 
- widefield imaging
- face cam

***
### Preview windows
On the pi that contains the two cameras (not recommended for a remote pi), use ***QtGL preview***.
It is the most efficient way to display images and should be used when implemented in a GUI environment.

`picam2 = Picamera2()`
`picam2.start_preview(Preview.QTGL)`

***
### Configuration Objects
Similarly to how pyqt5 functions, we can create a configuration object for each camera, either passing through all our parameters at once or modifying it after its initialization. 

configs do NOT include camera settings that can be changed at runtime (brightness or contrast). 

```python
config = picam2.create_preview_configuration(main={"size": (1920, 1080)})

# Manually adjust a specific setting (e.g., pixel format)
config['main']['format'] = "RGB888"

# Apply the configuration
picam2.configure(config)
```

Configuration of Picamera2 divides into 
1. general params that apply to the Picamera2 system and across the whole of the ISP
2. per-stream configs within ISP for main and lores streams
3. sensor params

**General config params**
- buffer_count: # of sets of buffers to allocate for the camera system. More buffers = smoother run and fewer dropped frames (though high memory consumption for high res images)
- colour_spaces: sYCC default 
- queue: whether the system is allowed to queue up a frame ready for capture request. **check this out for our application
- sensor: params that allow an app to select operating mode
- display: names of streams to be shown in previous window
- encode: names of streams to be encoded if a video recording is started (default: main)

For wfield cam I suggest: Raw (Bayer RGGB) or YUV422 or YUV444 as a compromise between precision and storage efficiency
For the behavioral face cam: YUV or H.264

*sensor_modes*: call `picam2.sensor_modes` to see the exact modes one can request for a particular camera object. 
- the pi4 and pi5 differ in their raw stream formats: pi5 stores raw pixels differently than the pi5.

*Tip: After configuring the camera, it’s often helpful to inspect picam2.camera_configuration() to check what you actually have

***
For video, we can also preset things that the user could change such as framerate:
`NoiseReductionMode` and `FrameDurationLimits` or `picam2.video_configuration.controls.FrameRate = 25.0`. 
- one can set runtime controls later using the  `Picamera2.set_controls` method but these will not become part of the configuration that we can recover later.

### Camera controls: 
These can be changed at runtime. 
You can see the full list with `picam2.camera_controls`. 

Camera controls can be set
- into the camera configs
- after config application but before camera start
- after the camera has started (but with some delay)

`picam2.controls.ExposureTime = 10000` 

***
### Autofocus Controls 
**Only possible for the Camera Module 3 up (not module 2) 

Contains three modes:
- manual: use the `LensPosition` control to move the lens as needed
- auto
- continuous

example:
```python
from picamera2 import Picamera2
from libcamera import controls
picam2 = Picamera2()
picam2.start(show_preview=True)
picam2.set_controls({"AfMode": controls.AfModeEnum.Manual, "LensPosition": 0.0})
```

***
### Synchronization
Small variations in clock timing, frame capture latency, and clock drift 
may cause the two cameras to desynchronize even after a common start time.

We will be using the Raspberry 5 which has two dedicated camera CSI ports. 
We cannot implement hardware synchronization as this requires the global shutter sensors or sensors with trigger pins. 

Since the cameras use the two CSI ports on the same Raspberry Pi, we can use timestamps that are based on the system's global clock to align the frames during post-processing. These timestamps will thus reflect any slight camera-specific delays and allow for proper synchronization. 
