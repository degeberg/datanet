import threading
import http.client
import json
import random
import time
import re

class ProxyManager(threading.Thread):
    def __init__(self, tracker, server_port):
        self.tracker = tracker
        self.server_port = server_port
        threading.Thread.__init__(self)

    def get_peer(self, super_only=False):
        while True:
            peer = random.choice(self.data['peers'])
            if peer['super_peer'] or not super_only: break
        return peer

    def check_whitelist(self, netloc):
        domain = re.sub(':\d+$', '', netloc)
        if domain[-1] != '.':
            domain += '.'

        return any(domain.endswith(a) and (len(a) == len(domain) or domain[-len(a)-1] == '.') for a in self.data['whitelist'])

    def run(self):
        while True:
            self.__register()
            time.sleep(self.data['options']['min_wait'])

    def __register(self):
        conn = http.client.HTTPConnection(self.tracker)
        conn.request('POST', '/peers.json', 'port={0}&action=register'.format(self.server_port), {
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        response = conn.getresponse().read().decode('utf8')
        self.data = json.loads(response)
