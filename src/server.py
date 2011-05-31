import socket
import threading
import queue
import sys
import http.client
import json

from worker import Worker

import cache

class Server:
    def __init__(self, config):
        self.proxynet = None
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
            tracker = http.client.HTTPConnection(self.config['server']['tracker'])
            tracker.request('POST', '/peers.json', 'port={0}&action=register'.format(self.config['server']['port']), {
                'Content-Type': 'application/x-www-form-urlencoded'
            })
            response = tracker.getresponse().read().decode('utf8')
            self.proxynet = json.loads(response)

        for i in range(int(self.config['server']['workers'])):
            w = Worker(self)
            w.daemon = True
            w.start()

        while True:
            self.clientqueue.put(self.sock.accept())
