import threading
import httplib
import json
import random
import time
import re

class EmptyPeerList(Exception):
    pass

class ProxyManager(threading.Thread):
    def __init__(self, tracker, server_port):
        self.tracker = tracker
        self.server_port = server_port
        threading.Thread.__init__(self)

    def get_peer(self, super_only=False):
        peers = self.get_super_peers() if super_only else self.data['peers']

        if len(peers) == 0:
            raise EmptyPeerList()

        while True:
            peer = random.choice(peers)
            if peer['super_peer'] or not super_only: break
        return peer

    def get_super_peers(self):
        return [x for x in self.data['peers'] if x['super_peer']]

    def remove_peer(self, ip):
        self.data['peers'] = list(filter(lambda x: x['ip'] != ip, self.data['peers']))

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
        conn = httplib.HTTPConnection(self.tracker)
        conn.request('POST', '/peers.json', 'port={0}&action=register'.format(self.server_port), {
            'Content-Type': 'application/x-www-form-urlencoded'
        })
        response = conn.getresponse().read()
        self.data = json.loads(response)
