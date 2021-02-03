# maryanne, raspberry that lives in basement and is hooked up to furnace

# hardware is Adafruit GPIO port expander "bonnet"
# https://www.adafruit.com/product/4132
# 24VAC inputs are connected through this optoisolator board
# http://www.icstation.com/channel-optocoupler-isolator-photoelectric-isolation-module-level-voltage-converter-8bit-output-signal-converter-p-14096.html

import time
import board
import busio
import digitalio
import poster
import thyme

from adafruit_mcp230xx.mcp23017 import MCP23017

i2c = busio.I2C(board.SCL, board.SDA)

mcp = MCP23017(i2c)

# array of pins
pins = []
# array of hysteresis counters for each pin
oncount = []
# time when pin last came on
ontime = []
# filtered value for each pin, 0 means off, power of 2 means on
filt = []

# initialize arrays
for i in range(0, 16):
    pin = mcp.get_pin(i)
    pin.direction = digitalio.Direction.INPUT
    # no pull up, the opto isolator boards have PNP outputs
    pins.append(pin)
    oncount.append(0)
    ontime.append(0)
    filt.append(0)
    
#print("iodir={0}", mcp.iodir)
#print("gppu={0}", mcp.gppu)

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

# for test/debug
def printCounts():
    s = ""
    for i in range(0, 16):
        s = s + "{0} ".format(oncount[i])
    print(s)

# main loop
print("Hello from MaryAnne", flush=True)
# set source name for network trouble reports
poster.setNetSrc("ma1.net")
# post boot record
poster.addRecord({"t": thyme.toStr(thyme.now()), "src": "ma1.boot"})

while True:
    time.sleep(0.02)
    now = thyme.now()
    # read inputs
    raw = list(map(lambda pin: pin.value, pins))
    change = False
    for i in range(0, 16):
        # increment/decrement counter based on raw input
        # when input is on, count up to 20 and stop
        # when input is off, count down to 0 and stop
        if raw[i]:
            oncount[i] = min(oncount[i] + 2, 20)
        else:
            oncount[i] = max(oncount[i] - 1, 0)
        # look for changes with hysteresis filter
        # the filter is necessary for two reasons:
        # 1) inputs are A/C so they alternate between 1 and 0 when they're on
        # 2) when input is off, glitches to 1 can happen (this is noise current through the 10K pulldown resistor)
        if filt[i] != 0:
            # filtered state is on, looking for off
            # counter reaching 0 means off
            if oncount[i] == 0:
                filt[i] = 0
                change = True
                duration = now - ontime[i]
                print("{0}: {1} is OFF, duration = {2}".format(str(now), names[i], str(duration)),
                      flush=True)
        else:
            # filtered state is off, looking for on
            # counter crossing 10 means on
            if oncount[i] > 10:
                filt[i] = 1 << i
                change = True
                print("{0}: {1} is ON".format(str(now), names[i]),
                      flush=True)
                ontime[i] = now
    if change:
        # since we represent on with power of 2, we can just add up the filt array to get binary input value
        inp = sum(filt)
        # post record with current data
        poster.addRecord({"t": thyme.toStr(now), "src": "ma1", "inp": inp})
