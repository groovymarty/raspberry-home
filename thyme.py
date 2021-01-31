# time module for home telemetry

import datetime

# official time zone for home telemetry is EST without Daylight Savings time
# in other words, -5 hours from UTC
def now():
    return datetime.datetime.now(datetime.timezone(-datetime.timedelta(hours=5)))
