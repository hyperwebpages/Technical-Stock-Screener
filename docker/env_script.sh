#!/bin/bash

# Script that copy the current docker env variables into a file "app/container.env"
# The file "app/container.env" is then loaded by the cronjob to fetch the data
declare -p | grep -Ev 'BASHOPTS|BASH_VERSINFO|EUID|PPID|SHELLOPTS|UID' > /app/container.env
