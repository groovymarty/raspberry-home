# use fish dish to send test records

import time
import thyme
import poster
import sys
sys.path.append("../raspberry-fun")
from fishdish import FishDish

fish = FishDish()

# main loop
print("Hello from fishtester", flush=True)
# set source name for network trouble reports
poster.setNetSrc("fish.net");
# post boot record
poster.addRecord({"t": thyme.toStr(thyme.now()), "src": "boot", "who": "fish"})

pattern = 1
def send_test_record():
    global pattern
    pattern += 1
    fish.buzzer.beep(.05,0,1)
    poster.addRecord({"t": thyme.toStr(thyme.now()), "src": "tst", "foot", pattern})

try:
    fish.button.when_pressed = send_test_record
    while True:
        if poster.netTrouble:
            fish.leds[0].off()
            fish.leds[2].on()
        else
            fish.leds[0].on()
            fish.leds[2].off()
        sleep(.5)
except Exception as e:
    fish.close()
    raise e
