# PiCams

[Official Pi Camera Documentation](https://www.raspberrypi.com/documentation/accessories/camera.html)


The two cameras we have access to at the moment are the following:
1. the Camera Module 2.1 NoIR
2. the Camera Module 3 NoIR Wide

Both camera uses a rolling shutter as opposed to the global shutter. 

Use modules from the *rpicam-apps* and *Picamera 2* libraries 

## Camera Hardware
*as listed on the official Pi documentation website*

||Camera Module V2| Camera Module 3 Wide| 
|---------|-----------| --------- | 
|Still resolution|8 megapixels|11.9 megapixels|
|Video modes|1080p47, 1640 × 1232p41 and 640 × 480p206| 2304 × 1296p56, 2304 × 1296p30 HDR, 1536 × 864p120|
|Sensor|Sony IMX219|Sony IMX708|
|Sensor resolution|3280 × 2464 pixels|4608 × 2592 pixels|
|Pixel size|1.12 µm × 1.12 µm|1.4 µm × 1.4 µm|
|Optical size|1/4"|1/2.43"|
|Focus|Adjustable|Motorized|
|Depth of field|Approx 10 cm to ∞|Approx 5 cm to ∞|
|Focal length|3.04 mm|2.75 mm|
|Horizontal FoV|62.2 degrees|102 degrees|
|Vertical FoV|48.8 degrees|67 degrees|
|Focal ratio F-Stop|F2.0|F2.2|
|Maximum exposure time (sec.)|11.76|112|

*Both the HQ Camera and the Global Shutter Camera, have support for synchronous captures. Making use of the XVS pin (Vertical Sync) allows one camera to pulse when a frame capture is initiated. The other camera can then listen for this sync pulse, and capture a frame at the same time as the other camera.*

***
## Camera Software
[Official Pi Documentation](https://www.raspberrypi.com/documentation/computers/camera_software.html)


libcamera is an open-source camera stack for Linux systems, providing low-level control of cameras on a variety of hardware, including Raspberry Pi.
The Raspberry Pi team customized libcamera for their hardware and initially provided applications like libcamera-still, libcamera-vid, and others.
With Raspberry Pi OS Bookworm, these camera applications have been renamed to rpicam-* (e.g., rpicam-still, rpicam-vid), reflecting the Pi-specific optimizations.

- Picamera2 is a Python library built on libcamera, providing programmatic control of the Raspberry Pi camera. It's ideal for Python projects that require image processing, video capture, or custom camera configurations.
- Rpicam consists of command-line applications (rpicam-still, rpicam-vid, etc.) built on libcamera, designed for quick image or video capture and automation via terminal commands or scripts.
*Use Picamera2 for Python development and Rpicam for simple or script-driven tasks. Both leverage the same underlying camera stack for optimized performance on Raspberry Pi hardware.*

### rpicam-apps
Built on top of libcamera. 
### libcamera
"RaspberryPi provides a custom pipeline handler which libcamera uses to drive the sensor and image signal processor (ISP) on the Raspberry Pi. libcamera contains a collection of image-processing algorithms (IPAs) including auto exposure/gain control (AEC/AGC), auto white balance (AWB), and auto lens-shading correction (ALSC)."
- important: If you run the X window server and want to use X forwarding, pass the qt-preview flag to render the preview window in a Qt window. The Qt preview window uses more resources than the alternatives.

***
## Tweak Camera Behavior
Use libcamera tuning files for each camera. 

***
## Using Multiple Cameras
"libcamera does not yet provide stereoscopic camera support. When running two cameras simultaneously, they must be run in separate processes. This means there is no way to synchronise sensor framing or 3A operation between them. As a workaround, you could synchronise the cameras through an external sync signal for the HQ (IMX477) camera, and switch the 3A to manual mode if necessary."

***
## Camera Control Options
- sharpness
- contrast
- brightness
- saturation
- ev (exposure value)
- shutter (specify the exposure time in microseconds)
- gain
- metering (sets metering mode of AEC/AGC algo
- exposure
- awb (Auto White Balance)
- awbgains
- denoise
- tuning-file (way to set all of these things at once)
- autofocus-mode
- autofocus-range
- autofocus-speed
- autofocus-window
- lens-position (moves lens to fixed focal distance in dioptres)

## Output options
- wrap (sets max value for counter used by output. Counter resets to zero after reaching this value
- flush (flushes output files to disk as soon as a frame finished writing instead of waiting for the system to handle it)

## Video options
To pass one of the following options to an application, prefix with --
- codec (sets the encoder to use for video output
- save-pts (only for pi4 and lower). for pi5 use libav to automatically generate timestamps for container formats
- signal
- initial (specifies whether to start the application with video output enabled or disabled) 
- split (writes video output from separate recording sessions into separate files)
- inline (writes sequence header in every intra frame which can help decode the video sequence from any point in the video (only works with H.264 format)
- framerate (records exactly the specified framerate)

rpicam-vid: 
- configures the encoder with a callback that handles the buffer containing the encoded image data. rpicam-vid can't recycle buffer data until the event loop, preview window, AND encoder all discard their references.

***
## Using libcamera with Qt
rpicam-apps includes an option to use Qt for a camera preview window

But Qt has errors with libcamera files. 


***
## Picamera2
Python interface to work with libcamera 
- read included PDF for detailed information
