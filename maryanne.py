import time
import datetime
import board
import busio
import digitalio
import requests

from adafruit_mcp230xx.mcp23017 import MCP23017

i2c = busio.I2C(board.SCL, board.SDA)

mcp = MCP23017(i2c)

pins = []
oncount = []
ontime = []
filt = []
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

def printCounts():
    s = ""
    for i in range(0, 16):
        s = s + "{0} ".format(oncount[i])
    print(s)

print("Hello from MaryAnne", flush=True)
while True:
    time.sleep(0.02)
    now = datetime.datetime.now()
    raw = list(map(lambda pin: pin.value, pins))
    change = False
    for i in range(0, 16):
        if raw[i]:
            oncount[i] = min(oncount[i] + 2, 20)
        else:
            oncount[i] = max(oncount[i] - 1, 0)
        if filt[i] != 0:
            if oncount[i] == 0:
                filt[i] = 0
                change = True
                duration = now - ontime[i]
                print("{0}: {1} is OFF, duration = {2}".format(str(now), names[i], str(duration)),
                      flush=True)
        else:
            if oncount[i] > 10:
                filt[i] = 1 << i
                change = True
                print("{0}: {1} is ON".format(str(now), names[i]),
                      flush=True)
                ontime[i] = now
    if change:
        inp = sum(filt)
        r = requests.post("https://groovymarty.com/gvyhome/data",
                         json = {"t": str(now),
                                 "src": "ma1",
                                 "inp": inp})
        if r.status_code != 200:
            print("post status code is {0}".format(r.status_code), flush=True)
