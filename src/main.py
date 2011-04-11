#!/usr/bin/env python

import argparse
import os
import os.path
import sys
import socket

from server import Server

ERROR_LOG='/tmp/error.log'
SERVER_LOG='/tmp/server.log'
WORKERS=5

def daemonize():
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except os.error as e:
        print('fork failed: (%d) %s' % (e.errno, e.strerror), file=sys.stderr)
        sys.exit(1)

    os.chdir('/')
    os.umask(0)
    os.setsid()

    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except os.error as e:
        print('fork failed: (%d) %s' % (e.errno, e.strerror), file=sys.stderr)
        sys.exit(1)

    print('Server daemonized with pid %d.' % os.getpid())

    si = open('/dev/null', 'r')
    so = open(SERVER_LOG, 'a+')
    se = open(ERROR_LOG, 'a+')
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

def parse_args():
    def ipv4_addr(addr):
        try:
            socket.inet_aton(addr)
            return addr
        except socket.error:
            raise argparse.ArgumentTypeError('%s is not a valid IPv4 address' % addr)

    def path(p):
        if os.path.exists(p):
            return os.path.abspath(p)

        raise argparse.ArgumentTypeError("Directory '%s' does not exist" % p)

    parser = argparse.ArgumentParser(description='Starts a web server.')
    parser.add_argument('dir', default='.', type=path,
                        help='server root directory')
    parser.add_argument('-p', '--port', default=80, type=int,
                        help='port the web server should bind to')
    parser.add_argument('-a', '--address', default='0.0.0.0', type=ipv4_addr,
                        help='address the web server should bind to')
    parser.add_argument('-d', '--daemon', default=False, action='store_true',
                        help='daemonizes the server')

    return parser.parse_args()

def main():
    args = parse_args()

    print('Starting server on %s:%s.' % (args.address, args.port))
    print('Server root: %s' % args.dir)

    if args.daemon:
        daemonize()

    server = Server(args.address, args.port)
    server.serve(args.dir, WORKERS)

if __name__ == '__main__':
    main()
