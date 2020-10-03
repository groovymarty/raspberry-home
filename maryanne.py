import time
import datetime
import board
import busio
import digitalio

from adafruit_mcp230xx.mcp23017 import MCP23017

i2c = busio.I2C(board.SCL, board.SDA)

mcp = MCP23017(i2c)

pins = []
oncount = []
filt = []
for i in range(0, 16):
    pin = mcp.get_pin(i)
    pin.direction = digitalio.Direction.INPUT
    pin.pull = digitalio.Pull.UP
    pins.append(pin)
    oncount.append(0)
    filt.append(False)

names = [
    "HEAT WH",
    "HEAT MBR",
    "HEAT 1ST",
    "HEAT 2ND",
    "BOIL",
    "COOL MBR",
    "COOL 1ST",
    "COOL 2ND",
    "WELL",
    "HW PUMP",
    "PIN 10",
    "PIN 11",
    "PIN 12",
    "PIN 13",
    "PIN 14",
    "TEST"]

def printCounts():
    s = ""
    for i in range(0, 16):
        s = s + "{0} ".format(oncount[i])
    print(s)

while True:
    time.sleep(0.02)
    now = datetime.datetime.now()
    raw = list(map(lambda pin: pin.value, pins))
    for i in range(0, 16):
        if raw[i]:
            oncount[i] = min(oncount[i] + 2, 20)
            if oncount[i] == 2:
                printCounts()
        else:
            oncount[i] = max(oncount[i] - 1, 0)
        if filt[i]:
            if oncount[i] == 0:
                filt[i] = False
                print("{0}: {1} is OFF".format(str(now), names[i]))
        else:
            if oncount[i] > 10:
                filt[i] = True
                print("{0}: {1} is ON".format(str(now), names[i]))
