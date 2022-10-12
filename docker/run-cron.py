#!/usr/bin/env python

# run-cron.py
# sets environment variable crontab fragments and runs cron

import fileinput
import os
from subprocess import call

# read docker environment variables and set them in the appropriate crontab fragment


TWITTER_BEARER = os.environ["TWITTER_BEARER"]
ALPACA_API = os.environ["ALPACA_API"]
ALPACA_API_SECRET = os.environ["ALPACA_API_SECRET"]

for line in fileinput.input("/etc/cron.d/crontab", inplace=1):
    print(line.replace("TWITTER_BEARER", TWITTER_BEARER))
    print(line.replace("ALPACA_API", ALPACA_API))
    print(line.replace("ALPACA_API_SECRET", ALPACA_API_SECRET))

args = ["cron", "-f", "&&", "tail", "-f", "/var/log/cron.log"]
call(args)
