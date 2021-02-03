# poster module

import threading
import queue
from collections import deque
import requests
import json
import os
import thyme

# input queue, newly arrived records
inQ = queue.Queue()
# records waiting to be posted
waitQ = deque()
# backlog file path
backlogPath = "backlog"
# backend server URL
postURL = "https://groovymarty.com/gvyhome/data"
# network request in progress?
netActive = False
# network trouble? true until proven false
netTrouble = True
# network trouble initial delay
netTroubleInitDelay = 5
# my source name for network trouble reports
myNetSrc = ""

# add a record to be posted
def addRecord(rec):
    inQ.put(rec)
    
# set my source name for network trouble reports
def setNetSrc(src):
    global myNetSrc
    myNetSrc = src

# update network active status
def setNetActive(newVal):
    global netActive
    netActive = newVal

# send net trouble report
def sendNetTrouble():
    print("{0} network trouble".format("start" if netTrouble else "no"), flush=True)
    if myNetSrc:
        addRecord({"t": thyme.toStr(thyme.now()), "src": myNetSrc, "trouble": 1 if netTrouble else 0})
 
# update network trouble status
# because of boot record we will always have some network activity at startup
def setNetTrouble(newVal):
    global netTrouble, netTroubleInitDelay
    if netTrouble != newVal:
        netTrouble = newVal
        # send trouble record on status change
        # report ok immediately, but wait till after delay to report trouble
        if netTroubleInitDelay == 0 or not netTrouble:
            sendNetTrouble()
            netTroubleInitDelay = 0
    # count down initial delay
    if netTroubleInitDelay > 0:
        netTroubleInitDelay -= 1
        # send trouble record after initial delay
        if netTroubleInitDelay == 0:
            sendNetTrouble()

# read backlog file
def readBacklog():
    try:
        with open(backlogPath, mode='r') as f:
            backlog = json.load(f)
            waitQ.extendleft(reversed(backlog))
            print("read {0} records from backlog file".format(len(backlog)), flush=True)
    except FileNotFoundError:
        pass
    except json.JSONDecodeError as e:
        print("JSON error in backlog file: {0}".format(str(e)), flush=True)
    except Exception as e:
        print("error reading backlog file: {0}".format(str(e)), flush=True)

# write backlog file
def writeBacklog():
    try:
        with open(backlogPath, mode='w') as f:
            json.dump(list(waitQ), f, indent=1)
    except Exception as e:
        print("error writing backlog file: {0}".format(str(e)), flush=True)

# delete backlog file
def deleteBacklog():
    try:
        os.remove(backlogPath)
    except Exception:
        pass

# main function for thread
def posterMain():
    # load wait list from backlog file
    # these are records we were unable to post during previous execution
    readBacklog()
    backlogChanged = False
    while True:
        # transfer new records from input queue to wait list
        # input queue and wait list are always newest (left) to oldest (right)
        try:
            # block up to 5 seconds for first record
            rec = inQ.get(timeout=5)
            waitQ.appendleft(rec)
            backlogChanged = True
            # get additional input records without blocking
            while not inQ.empty():
                rec = inQ.get_nowait()
                waitQ.appendleft(rec)
        except queue.Empty:
            pass

        # any records to post?
        if waitQ:
            # post up to 100 records at a time
            # postRecs is oldest (left) to newest (right)
            postRecs = []
            while waitQ and len(postRecs) < 100:
                # remove oldest record from waitQ (pop from right)
                rec = waitQ.pop()
                # append to right, so postRecs will be chronological order (oldest to newest)
                postRecs.append(rec)

            # post to server
            # uncomment the if clause for testing, forces 404 error unless 3 or more records are ready to post
            url = postURL   # if len(postRecs) > 2 else postURL + "xxx"
            status = 0
            try:
                # note this is a synchronous call, so thread will block until post succeeds or fails
                setNetActive(True)
                r = requests.post(url, json=postRecs)
                status = r.status_code
            except Exception:
                pass
            if status != 200:
                # post failed
                setNetActive(False)
                setNetTrouble(True)
                if status != 0:
                    print("post status code is {0}".format(status), flush=True)
                # put records back on waiting list
                # extend waitQ on right with records from newest to oldest
                waitQ.extend(reversed(postRecs))
                # write all waiting records to backlog file
                # this ensures records will not be lost if reboot happens before next successful post
                # avoid writing file if contents unchanged
                if (backlogChanged):
                    writeBacklog()
                    backlogChanged = False
                # try again in next loop, usually 5 seconds
            else:
                # successful post
                setNetActive(False)
                setNetTrouble(False)
                #print("post successful", flush=True)
                # update or delete backlog file
                if waitQ:
                    writeBacklog()
                else:
                    deleteBacklog()
                backlogChanged = False

# start poster thread
thread = threading.Thread(name="poster", target=posterMain)
thread.start()
