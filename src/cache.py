import time
import hashlib

class Manager:
    def __init__(self, config):
        self.config = config
        self.resources = {}

    def add_resource(self, id, expires=None):
        self.resources[id] = {
            'expires': expires,
            'retrieved': time.time(),
        }

    def is_cached(self, id):
        return id in self.resources and (self.resources[id]['expires'] == None or self.resources[id]['expires'] > time.time())

    def remove_resource(self, id):
        if id in self.resources:
            del self.resources[id]

def get_resource_id(uri):
    return hashlib.md5(uri.encode('ascii')).hexdigest()

def can_be_cached(response):
    return response.status == 200
