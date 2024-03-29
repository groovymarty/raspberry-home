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
import RPi.GPIO as GPIO

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
    "HSTAT BR",
    "HSTAT LR",
    "PEL ON",
    "HUMAX",
    "PIN 14",
    "TEST"]

# some port expander input pins
HEAT_1ST = names.index("HEAT 1ST")
HEAT_MBR = names.index("HEAT MBR")
PEL_ON = names.index("PEL ON")
HSTAT_BR = names.index("HSTAT BR")
HSTAT_LR = names.index("HSTAT LR")
HUMAX = names.index("HUMAX")

# GPIO output pins for solid state relays
SSR1 = 4
SSR2 = 17
SSR3 = 18
SSR4 = 27
SSR5 = 22
SSR6 = 23
SSR7 = 24
SSR8 = 25

ssrs = [SSR1, SSR2, SSR3, SSR4, SSR5, SSR6, SSR7, SSR8]

# SSR function assignments
SSR_FAN_BR = SSR1
SSR_HUM_BR = SSR2
SSR_FAN_LR = SSR3
SSR_HUM_LR = SSR4
SSR_PEL_HI = SSR5
SSR_HEAT_LR = SSR6

# Initialize outputs
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

for ssr in ssrs:
    GPIO.setup(ssr, GPIO.OUT)
    GPIO.output(ssr, GPIO.HIGH if ssr in [SSR_HUM_BR, SSR_HUM_LR, SSR_HEAT_LR] else GPIO.LOW)

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

# loop timing
SLEEP_SEC = 0.02
HUM_DUTY_ON_BR = 17.0  # adjust per water flow rate
HUM_DUTY_ON_LR = 150.0  # adjust per water flow rate
HUM_DUTY_PERIOD_BR = 60.0  # one minute
HUM_DUTY_PERIOD_LR = 3600.0  # one hour
hum_duty_tstart_br = hum_duty_tstart_lr = thyme.now()

while True:
    time.sleep(SLEEP_SEC)
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
                print("{0}: {1} is OFF, duration = {2}".format(thyme.toStr(now), names[i], str(duration)),
                      flush=True)
        else:
            # filtered state is off, looking for on
            # counter crossing 10 means on
            if oncount[i] > 10:
                filt[i] = 1 << i
                change = True
                print("{0}: {1} is ON".format(thyme.toStr(now), names[i]),
                      flush=True)
                ontime[i] = now
    if change:
        # since we represent on with power of 2, we can just add up the filt array to get binary input value
        inp = sum(filt)
        # post record with current data
        poster.addRecord({"t": thyme.toStr(now), "src": "ma1", "inp": inp})

    # turn off oil heat to LR when pellet stove is on
    GPIO.output(SSR_HEAT_LR, GPIO.LOW if filt[PEL_ON] else GPIO.HIGH)

    # regulate pellet stove according to LR thermostat
    GPIO.output(SSR_PEL_HI, GPIO.HIGH if filt[HEAT_1ST] else GPIO.LOW)
    
    # run humidifiers with cold air?
    # LR always runs cold because bypass duct has been disconnected
    # LR humidifier runs on hstat demand and heat is on (oil or pellet)
    # HUMAX switch forces continuous LR run when hstat demand is true
    # HUMAX switch forces continuous BR run when hstat demand is true and MBR heat is not on
    # When MBR heat is on, BR humidifier runs with warm air (thus not cold),
    # so we don't want to cycle water.  Let water run continuously.
    run_cold_lr = (filt[HEAT_1ST] or filt[PEL_ON] or filt[HUMAX]) and filt[HSTAT_LR]
    run_cold_br = filt[HUMAX] and filt[HSTAT_BR] and not filt[HEAT_MBR]

    # run LR fan when pellet stove is on or running humidifier cold
    want_fan_lr = filt[PEL_ON] or run_cold_lr
    GPIO.output(SSR_FAN_LR, GPIO.HIGH if want_fan_lr else GPIO.LOW)
    
    # run BR fan when running humidifier cold
    want_fan_br = run_cold_br
    GPIO.output(SSR_FAN_BR, GPIO.HIGH if want_fan_br else GPIO.LOW)

    # humidifier duty cycle timers
    elapsed_br = (now - hum_duty_tstart_br).total_seconds()
    if elapsed_br >= HUM_DUTY_PERIOD_BR:
        hum_duty_tstart_br = now
        elapsed_br = 0

    elapsed_lr = (now - hum_duty_tstart_lr).total_seconds()
    if elapsed_lr >= HUM_DUTY_PERIOD_LR:
        hum_duty_tstart_lr = now
        elapsed_lr = 0

    # cycle bedroom humidifier if we're running cold, to avoid wasting water
    # otherwise leave HUM output high to allow normal operation (warm air)
    if run_cold_br:
        GPIO.output(SSR_HUM_BR, GPIO.HIGH if elapsed_br < HUM_DUTY_ON_BR else GPIO.LOW)
    else:
        GPIO.output(SSR_HUM_BR, GPIO.HIGH)
        hum_duty_tstart_br = now

    # LR humidifier always runs cold and has a reservoir and pump to recirculate water
    # cycle the water valve often enough to keep the reservioir full
    # otherwise leave water valve off
    if run_cold_lr:
        GPIO.output(SSR_HUM_LR, GPIO.HIGH if elapsed_lr < HUM_DUTY_ON_LR else GPIO.LOW)
    else:
        GPIO.output(SSR_HUM_LR, GPIO.LOW)
        hum_duty_tstart_lr = now
