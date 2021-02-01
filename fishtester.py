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
    poster.addRecord({"t": thyme.toStr(thyme.now()), "src": "tst", "foo": pattern})

try:
    fish.button.when_pressed = send_test_record
    while True:
        if poster.netActive:
            fish.yellow.on()
        else:
            fish.yellow.off()
        if poster.netTrouble:
            fish.red.on()
            fish.green.off()
        else:
            fish.red.off()
            fish.green.on()
        time.sleep(.5)
except Exception as e:
    fish.close()
    raise e
