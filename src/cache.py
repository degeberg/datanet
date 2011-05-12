import time
import hashlib
import email.utils

class Manager:
    def __init__(self, config):
        self.config = config
        self.resources = {}

    def add_resource(self, id, expires=None):
        self.resources[id] = {
            'expires': expires,
            'retrieved': time.gmtime(),
        }

    def is_cached(self, id):
        return id in self.resources and (self.resources[id]['expires'] == None or self.resources[id]['expires'] > time.gmtime())

    def remove_resource(self, id):
        if id in self.resources:
            del self.resources[id]

def get_resource_id(uri):
    return hashlib.md5(uri.encode('ascii')).hexdigest()

def can_be_cached(response):
    if response.status != 200:
        return False, None

    headers = dict(response.getheaders())

    if 'Expires' in headers:
        if headers['Expires'] == '-1':
            return False, None
        expires = email.utils.parsedate(headers['Expires'])
        return (expires > time.gmtime()), expires

    if 'Cache-Control' in headers:
        items = headers['Cache-Control'].split(', ')
        for item in items:
            stuff = item.split('=', 1)
            if len(stuff) == 2:
                key, value = stuff
            else:
                key = stuff[0]

            if key in ('private', 'no-cache', 'no-store'):
                return False, None
            elif key == 'max-age':
                return True, time.gmtime(time.time() + value)

    return True, None
