#!/usr/bin/env python
# encoding: utf8
'''
Usage: gitcontribs [options] [<file>]

Options:
    -v, --verbose       increase output
    -h, --help          print this text
'''
import logging

from pprint import pformat
from docopt import docopt       # type: ignore

log = logging.getLogger()
logging.basicConfig(level=logging.DEBUG)


def main():
    'Start main CLI entry point.'
    args = docopt(__doc__)
    if args['--verbose']:
        log.setLevel(logging.DEBUG)
    log.debug(pformat(args))

    log.info("Hello World")


if __name__ == '__main__':
    main()
