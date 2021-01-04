import time
import datetime
import poster

loopCtr = 0
while True:
    loopCtr += 1
    time.sleep(10)
    print("test loop {0}".format(loopCtr), flush=True)
    now = datetime.datetime.now()
    poster.addRecord({"t": str(now), "src": "tst", "foo": loopCtr})
