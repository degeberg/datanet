import socket
import threading
import queue
import sys

from worker import Worker
from proxynet import ProxyManager

import cache

class Server:
    def __init__(self, config):
        self.proxymanager = None
        self.config = config

        self.workers = []

        self.cache = cache.Manager(config)

        self.clientqueue = queue.Queue(0) # create client queue of infinite size

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((config['server']['bind'], int(config['server']['port'])))
        self.sock.listen(int(config['server']['listen_backlog']))

    def stop(self):
        self.sock.close()
        sys.exit(0)

    def serve(self):
        if self.config['server']['tracker'] != None:
            self.proxymanager = ProxyManager(self.config['server']['tracker'], self.config['server']['port'])
            self.proxymanager.daemon = True
            self.proxymanager.start()

        for i in range(int(self.config['server']['workers'])):
            w = Worker(self)
            w.daemon = True
            w.start()

        while True:
            self.clientqueue.put(self.sock.accept())
