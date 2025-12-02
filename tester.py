"""Simple tester GUI

Creates a small Tkinter window with:
- a horizontal slider (0-100) to control PWM duty cycle on GPIO18
- an ON/OFF toggle to control GPIO15

The module uses RPi.GPIO when available, otherwise falls back to a lightweight mock
so the script can be run on non-RPi systems for UI testing.
"""

import sys
import time
try:
    import RPi.GPIO as GPIO
    _HAVE_RPI = True
except Exception:
    _HAVE_RPI = False

from tkinter import Tk, Scale, HORIZONTAL, Label, Checkbutton, IntVar, Button


class _MockPWM:
    def __init__(self, pin, freq):
        self.pin = pin
        self.freq = freq
        self._dc = 0
        print(f"[MockPWM] created on pin {pin} at {freq}Hz")

    def start(self, duty_cycle):
        self._dc = duty_cycle
        print(f"[MockPWM] start duty={duty_cycle}%")

    def ChangeDutyCycle(self, duty_cycle):
        self._dc = duty_cycle
        print(f"[MockPWM] duty -> {duty_cycle}%")

    def stop(self):
        print("[MockPWM] stop")


class _MockGPIO:
    BCM = 'BCM'
    OUT = 'OUT'
    HIGH = 1
    LOW = 0

    def __init__(self):
        self._pin_state = {}

    def setwarnings(self, flag):
        pass

    def setmode(self, mode):
        print(f"[MockGPIO] setmode({mode})")

    def setup(self, pin, mode):
        self._pin_state[pin] = self.LOW
        print(f"[MockGPIO] setup pin {pin} as {mode}")

    def output(self, pin, value):
        self._pin_state[pin] = value
        print(f"[MockGPIO] output pin {pin} -> {value}")

    def PWM(self, pin, freq):
        return _MockPWM(pin, freq)

    def cleanup(self):
        print("[MockGPIO] cleanup")


if not _HAVE_RPI:
    GPIO = _MockGPIO()


# Pins
PWM_PIN = 18  # PWM pin for brightness
FREQ = 10000   # PWM frequency


def main():
    # GPIO setup
    GPIO.setwarnings(False)
    try:
        GPIO.setmode(GPIO.BCM)
    except Exception:
        # Some mocks may not require this; ignore
        pass

    GPIO.setup(PWM_PIN, GPIO.OUT)

    # Start PWM
    pwm = GPIO.PWM(PWM_PIN, FREQ)
    pwm.start(0)

    # Build UI
    root = Tk()
    root.title("PWM & LED Tester")
    root.geometry("420x120")

    label = Label(root, text="PWM Duty Cycle: 0%")
    label.pack(pady=(8, 0))

    def on_duty_change(val):
        try:
            duty = float(val)
        except Exception:
            duty = 0.0
        pwm.ChangeDutyCycle(duty)
        label.config(text=f"PWM Duty Cycle: {duty:.0f}%")

    scale = Scale(root, from_=0, to=100, orient=HORIZONTAL, length=380,
                  command=on_duty_change)
    scale.set(0)
    scale.pack(pady=(4, 8))

    # Toggle to enable/disable the LED PWM. When disabled we force duty to 0.
    led_var = IntVar(value=1)

    def on_led_toggle():
        enabled = bool(led_var.get())
        if not enabled:
            # Force PWM to 0 when turned off
            try:
                pwm.ChangeDutyCycle(0)
            except Exception:
                pass
            label.config(text=f"PWM Duty Cycle: 0% (disabled)")
            scale.config(state='disabled')
        else:
            # Re-enable slider and restore to current value
            scale.config(state='normal')
            try:
                duty = float(scale.get())
            except Exception:
                duty = 0.0
            pwm.ChangeDutyCycle(duty)
            label.config(text=f"PWM Duty Cycle: {duty:.0f}%")

    chk = Checkbutton(root, text="LED Enabled (allow PWM)", variable=led_var,
                      command=on_led_toggle)
    chk.pack()

    def on_close():
        try:
            pwm.ChangeDutyCycle(0)
            pwm.stop()
        except Exception:
            pass
        # No second pin to clear; PWM already set to 0 above.
        try:
            GPIO.cleanup()
        except Exception:
            pass
        root.destroy()

    quit_btn = Button(root, text="Quit", command=on_close)
    quit_btn.pack(pady=(6, 6))

    root.protocol("WM_DELETE_WINDOW", on_close)

    print("Starting GUI loop. Close the window to exit.")
    root.mainloop()


if __name__ == '__main__':
    main()

