#!/usr/bin/python
import RPi.GPIO as GPIO
import time

SSR1 = 4
SSR2 = 17
SSR3 = 18
SSR4 = 27
SSR5 = 22
SSR6 = 23
SSR7 = 24
SSR8 = 25

ssrs = [SSR1, SSR2, SSR3, SSR4, SSR5, SSR6, SSR7, SSR8]

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

for ssr in ssrs:
    GPIO.setup(ssr, GPIO.OUT)

i = 0
while True:
    GPIO.output(ssrs[i], GPIO.HIGH)
    time.sleep(0.5)
    GPIO.output(ssrs[i], GPIO.LOW)
    i = (i + 1) % 8
