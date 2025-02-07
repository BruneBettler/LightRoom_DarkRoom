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
### Synchronization
Small variations in clock timing, frame capture latency, and clock drift 
may cause the two cameras to desynchronize even after a common start time.

We will be using the Raspberry 5 which has two dedicated camera CSI ports. 
We cannot implement hardware synchronization as this requires the global shutter sensors or sensors with trigger pins. 

Since the cameras use the two CSI ports on the same Raspberry Pi, we can use timestamps that are based on the system's global clock to align the frames during post-processing. These timestamps will thus reflect any slight camera-specific delays and allow for proper synchronization. 
