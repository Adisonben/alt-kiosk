import RPi.GPIO as GPIO
import time

PIR_PIN = 17

GPIO.setmode(GPIO.BCM)
GPIO.setup(PIR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

print("starting motion sensor...")

time.sleep(2)

try:
    while True:
        if GPIO.input(PIR_PIN):
            print(GPIO.input(PIR_PIN), " :: Motion Detected!")
        else:
            print(GPIO.input(PIR_PIN), " :: No Motion")

        time.sleep(0.5)

except KeyboardInterrupt:
    GPIO.cleanup()