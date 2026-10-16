"""Daemon of the mideamsmart Jeedom plugin, started by mideamsmart::deamon_start()."""

import argparse
import asyncio
import logging
import sys

from mideamsmart_daemon.daemon import Daemon
from mideamsmart_daemon.jeedom import setup_logging

_LOGGER = logging.getLogger('mideamsmartd')


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='mideamsmart daemon for Jeedom')
    parser.add_argument('--loglevel', default='error', help='Jeedom log level')
    parser.add_argument('--sockethost', default='127.0.0.1', help='Listening address of the socket')
    parser.add_argument('--socketport', type=int, required=True, help='Listening port of the socket')
    parser.add_argument('--callback', required=True, help='URL of the plugin callback')
    parser.add_argument('--apikey', required=True, help='Plugin apikey')
    parser.add_argument('--pid', required=True, help='PID file')
    parser.add_argument('--cycle', type=float, default=0.5, help='Delay between two sendings of values to Jeedom (s)')
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    setup_logging(args.loglevel)
    _LOGGER.info('Starting the daemon (Python %s, log level %s, port %s)', sys.version.split()[0], args.loglevel, args.socketport)
    daemon = Daemon(
        socket_host=args.sockethost,
        socket_port=args.socketport,
        callback_url=args.callback,
        apikey=args.apikey,
        pid_file=args.pid,
        cycle=args.cycle,
    )
    try:
        return asyncio.run(daemon.run())
    except Exception:
        _LOGGER.exception('Fatal error')
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
