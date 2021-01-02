# poster module

import threading
import queue
from collections import deque
import requests

# input queue, newly arrived records
inQ = queue.Queue()
# records waiting to be posted
waitQ = deque()

# add a record to be posted
def addRecord(rec):
    inQ.put(rec)

# main function for thread
def posterMain():
    while True:
        # transfer records from input queue to wait list
        try:
            # block up to 5 seconds for first record
            rec = inQ.get(timeout=5)
            waitQ.appendleft(rec)
            # get additional input records without blocking
            while not inQ.empty():
                rec = inQ.get_nowait()
                waitQ.appendleft(rec)
        except queue.Empty:
            pass

        # any records to post?
        if waitQ:
            # post up to 100 records at a time
            postRecs = []
            while waitQ and len(postRecs) < 100:
                rec = waitQ.pop()
                postRecs.append(rec)

            # post to server
            # note this is a synchronous call, so thread will block until post succeeds or fails
            r = requests.post("https://groovymarty.com/gvyhome/data", json=postRecs)
            if r.status_code != 200:
                # post failed
                print("post status code is {0}".format(r.status_code), flush=True)
                # put records back on waiting list
                # try again in next loop, usually 5 seconds
                waitQ.extend(postRecs)

# start poster thread
thread = threading.Thread(name="poster", target=posterMain)
thread.start()
