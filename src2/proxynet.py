import threading
import httplib
import json
import random
import time
import re
import os.path
import hashlib

from tlslite.utils.cryptomath import numberToBase64, base64ToNumber
from Crypto.PublicKey import RSA
from Crypto import Random

class EmptyPeerList(Exception):
    pass

class ProxyManager(threading.Thread):
    def __init__(self, tracker, server_port):
        self.tracker = tracker
        self.server_port = server_port

        c = httplib.HTTPConnection(tracker)
        c.request('GET', '/tracker_pub.pem')
        self.tracker_pub = RSA.importKey(c.getresponse().read())

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
            try:
                self.__register(self.data['options']['nonce'])
            except:
                self.__register()
            time.sleep(self.data['options']['min_wait'])

    def __register(self, nonce=''):
        conn = httplib.HTTPConnection(self.tracker)

        with open('id_rsa') as f:
            key = RSA.importKey(f.read())
        pubkey = key.publickey()

        body = 'port={0}&action=register&pub_key={1}+{2}'.format(self.server_port, pubkey.n,  pubkey.e)

        h = '\x00' + '\xff'*95 + hashlib.sha256(body + nonce).digest()
        h = key.sign(h, Random.new().read(100))
        h = numberToBase64(h[0])

        conn.request('POST', '/peers.json', body, {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Content-Signature': h,
        })
        res = conn.getresponse()
        response = res.read()

        tsig = res.getheader('Content-Signature')
        rb = '\x00' + '\xff'*95 + hashlib.sha256(response).digest()
        if not self.tracker_pub.verify(rb, (base64ToNumber(tsig), )):
            print "Couldn't verify message integrity"
            return

        self.data = json.loads(response)

        if nonce == '':
            return self.__register(self.data['options']['nonce'])
        elif not self.data['options']['verified']:
            print 'Could not verify with tracker'
        else:
            print 'Tracker list updated'
            print response
