#!/usr/bin/env python

import argparse
import os
import os.path
import sys
import socket
import signal
import configparser

from server import Server

CONFIG_DEFAULTS = {
    # server:
    'port': '80',
    'bind': '0.0.0.0',
    'webroot': '.',
    'workers': '20',
    'read_bufsize': '1024',
    'compression_limit': '1048576',
    'listen_backlog': '5',
    # resources:
    'templates': './templates',
    'cache': './cache',
    # logs:
    'error': '/tmp/error.log',
    'server': '/tmp/server.log',
}

def daemonize(config):
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
    so = open(config['logs']['server'], 'a+')
    se = open(config['logs']['error'], 'a+')
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

def parse_args():
    def ipv4_addr(addr):
        if addr == None: return
        try:
            socket.inet_aton(addr)
            return addr
        except socket.error:
            raise argparse.ArgumentTypeError('%s is not a valid IPv4 address' % addr)

    def path(p):
        if p == None: return
        if os.path.exists(p):
            return os.path.abspath(p)

        raise argparse.ArgumentTypeError("Path '%s' does not exist" % p)

    parser = argparse.ArgumentParser(description='Starts a web server.')
    parser.add_argument('-w', '--webroot', type=path,
                        help='server root directory')
    parser.add_argument('-p', '--port', type=int,
                        help='port the web server should bind to')
    parser.add_argument('-a', '--address', type=ipv4_addr,
                        help='address the web server should bind to')
    parser.add_argument('-d', '--daemon', default=False, action='store_true',
                        help='daemonizes the server')
    parser.add_argument('-c', '--config', default='config.ini', type=path,
                        help='Path to configuration file.')

    return parser.parse_args()

def parse_config(path, args):
    config = configparser.ConfigParser(defaults=CONFIG_DEFAULTS)
    config.read([path])

    if args.webroot != None:
        config['server']['webroot'] = args.webroot
    if args.port != None:
        config['server']['port'] = str(args.port)
    if args.address != None:
        config['server']['bind'] = args.address

    config['server']['tracker'] = 'datanet2011tracker.appspot.com'
    config['server']['webroot'] = os.path.abspath(config['server']['webroot'])
    config['resources']['templates'] = os.path.abspath(config['resources']['templates'])
    config['resources']['cache'] = os.path.abspath(config['resources']['cache'])
    config['logs']['error'] = os.path.abspath(config['logs']['error'])
    config['logs']['server'] = os.path.abspath(config['logs']['server'])

    return config

def main():
    args = parse_args()
    config = parse_config(args.config, args)

    print('Starting server on %s:%s.' % (config['server']['bind'], config['server']['port']))
    print('Server root: %s' % config['server']['webroot'])

    if args.daemon:
        daemonize(config)

    server = Server(config)
    try:
        server.serve()
    except KeyboardInterrupt:
        server.stop()

if __name__ == '__main__':
    main()
