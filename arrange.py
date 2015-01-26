#!/usr/bin/env python
from ewmh import EWMH
import logging
import os.path
import subprocess
import sys
import time

try:
	import configparser
except ImportError:
	import ConfigParser as configparser

try:
	from subprocess import DEVNULL
except ImportError:
	DEVNULL = open(os.path.devnull, 'w')


CONFIG_DIR = '~/.arrange'
DEFAULT_CONFIG = '%s/default.conf' % CONFIG_DIR
RETRIES = 10
RETRY_INTERVAL = 1

COMMAND = 'command'
IGNORE = {COMMAND}
OPTIONS = {'close', 'maximize', 'move'}

rc = configparser.ConfigParser()

if len(sys.argv) > 1:
    rc.read(sys.argv[1])
else:
    rc.read(os.path.expanduser(DEFAULT_CONFIG))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('arrange')
logger.setLevel(logging.DEBUG)

ewmh = EWMH()


def _windows(name):
    all_windows = ewmh.getClientList()
    matched_windows = [w for w in all_windows if w.get_wm_class()[1] == name.capitalize()]
    return matched_windows


def close(application_windows, _):
    for application_window in application_windows:
        ewmh.setCloseWindow(application_window)


def maximize(application_windows, _):
    for application_window in application_windows:
        ewmh.setWmState(application_window, 1, '_NET_WM_STATE_MAXIMIZED_VERT', 0)
        ewmh.setWmState(application_window, 1, '_NET_WM_STATE_MAXIMIZED_HORZ', 0)


def move(application_windows, desktop_number):
    for application_window in application_windows:
        ewmh.setWmDesktop(application_window, desktop_number)


def arrange(started_applications):
    remaining = started_applications.copy()
    for application in started_applications.keys():
        matched_windows = _windows(application)
        our_windows = [w for w in matched_windows if ewmh.getWmPid(w) == started_applications.get(application)]
        if len(our_windows) > 0:
            remaining.pop(application)
        for option in rc.options(application):
            if option in IGNORE:
                continue
            elif option not in OPTIONS:
                logger.warning('Option "%s" for application "%s" is invalid and was ignored.', option, application)
                continue
            option_value = rc.getint(application, option)
            globals()[option](our_windows, option_value)
        ewmh.display.flush()
    return remaining


if __name__ == '__main__':

    started = {}
    for application in rc.sections():
        command = rc.get(application, COMMAND) if rc.has_option(application, COMMAND) else application
        logger.debug('Starting "%s" with "%s"', application, command)
        pid = subprocess.Popen(
            [os.path.expanduser(command)],
            stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL).pid
        logger.debug('Started "%s", PID: %s', application, pid)
        started[application] = pid

    retries = RETRIES
    not_arranged_yet = arrange(started)
    while retries > 0 and len(not_arranged_yet) > 0:
        not_arranged_yet = arrange(not_arranged_yet)
        retries -= 1
        time.sleep(RETRY_INTERVAL)
    if len(not_arranged_yet) > 0:
        logger.debug('Giving up on: %s', not_arranged_yet)
    logger.debug('All done.')
