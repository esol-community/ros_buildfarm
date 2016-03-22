#!/usr/bin/env python3

import subprocess
import sys
from time import sleep


def main(argv=sys.argv[1:]):
    max_tries = 10
    known_error_strings = [
        'Failed to fetch',
        'Hash Sum mismatch',
        'Unable to locate package',
        'is not what the server reported',
    ]

    command = argv[0]
    if command in ['update', 'source']:
        rc, _, _ = call_apt_get_repeatedly(
            argv, known_error_strings, max_tries)
        return rc
    elif command == 'update-and-install':
        return call_apt_get_update_and_install(
            argv[1:], known_error_strings, max_tries)
    else:
        assert "Command '%s' not implemented" % command


def call_apt_get_update_and_install(
        install_argv, known_error_strings, max_tries):
    tries = 0
    command = 'update'
    while tries < max_tries:
        if command == 'update':
            rc, _, tries = call_apt_get_repeatedly(
                [command], known_error_strings, max_tries - tries,
                offset=tries)
            if rc != 0:
                # abort if update was unsuccessful even after retries
                break
            # move on to the install command if update was successful
            command = 'install'

        if command == 'install':
            # any call is considered a try
            tries += 1
            known_error_strings_redo_update = [
                'Size mismatch',
                'maybe run apt-get update',
                'The following packages cannot be authenticated!',
                ]
            rc, known_error_conditions = \
                call_apt_get(
                    [command] + install_argv,
                    known_error_strings + known_error_strings_redo_update)
            if not known_error_conditions:
                # break the loop and return the reported rc
                break
            # known errors are always interpreted as a non-zero rc
            if rc == 0:
                rc = 1
            # check if update needs to be rerun
            if (
                set(known_error_conditions) &
                set(known_error_strings_redo_update)
            ):
                command = 'update'
                print("'apt-get install' failed and likely requires " +
                      "'apt-get update' to run again")
                # retry with update command
                continue

            print('Invocation failed due to the following known error '
                  'conditions: ' + ', '.join(known_error_conditions))
            if tries < max_tries:
                sleep_time = 5
                print("Reinvoke 'apt-get install' after sleeping %s seconds" %
                      sleep_time)
                sleep(sleep_time)
                # retry install command

    return rc


def call_apt_get_repeatedly(argv, known_error_strings, max_tries, offset=0):
    command = argv[0]
    for i in range(1, max_tries + 1):
        if i > 1:
            sleep_time = 5 + 2 * (i + offset)
            print("Reinvoke 'apt-get %s' (%d/%d) after sleeping %s seconds" %
                  (command, i + offset, max_tries + offset, sleep_time))
            sleep(sleep_time)
        rc, known_error_conditions = call_apt_get(argv, known_error_strings)
        if not known_error_conditions:
            # break the loop and return the reported rc
            break
        # known errors are always interpreted as a non-zero rc
        if rc == 0:
            rc = 1
        print('')
        print('Invocation failed due to the following known error conditions: '
              ', '.join(known_error_conditions))
        print('')
        # retry in case of failure with known error condition
    return rc, known_error_conditions, i + offset


def call_apt_get(argv, known_error_strings):
    known_error_conditions = []

    cmd = ['apt-get'] + argv
    print("Invoking '%s'" % ' '.join(cmd))
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines = []
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        line = line.decode()
        lines.append(line)
        sys.stdout.write(line)
        for known_error_string in known_error_strings:
            if known_error_string in line:
                if known_error_string not in known_error_conditions:
                    known_error_conditions.append(known_error_string)
    proc.wait()
    rc = proc.returncode
    if rc and not known_error_conditions:
        print('Invocation failed without any known error condition, '
              'printing all lines to debug known error detection:')
        for index, line in enumerate(lines):
            print(' ', index + 1, "'%s'" % line)
        print('Neither of the following known errors was detected:')
        for index, known_error_string in enumerate(known_error_strings):
            print(' ', index + 1, "'%s'" % known_error_string)
    return rc, known_error_conditions


if __name__ == '__main__':
    sys.exit(main())
