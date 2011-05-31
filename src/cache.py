import time
import hashlib
import email.utils

class Manager:
    def __init__(self, config):
        self.config = config
        self.resources = {}

    def add_resource(self, id, expires=None, headers={}):
        self.resources[id] = {
            'expires': expires,
            'retrieved': time.gmtime(),
            'headers': headers,
        }

    def is_cached(self, id):
        return False # disable the cache for assignment 3 and 4
        return id in self.resources and (self.resources[id]['expires'] == None or self.resources[id]['expires'] > time.gmtime())

    def get_attr(self, id, attr):
        return self.resources[id][attr]

    def remove_resource(self, id):
        if id in self.resources:
            del self.resources[id]

    def serve_resource(self, res_id, response):
        res = self.resources[res_id]
        rheaders = response.req['headers']

        print('Serving resource {0} from cache.'.format(res_id))

        not_changed = False
        if 'If-None-Match' in rheaders and 'ETag' in res['headers']:
            not_changed = not_changed or rheaders['If-None-Match'] == res['headers']['ETag']

        if 'If-Modified-Since' in rheaders:
            date = email.utils.parsedate(rheaders['If-Modified-Since'])
            not_changed = not_changed or date > res['retrieved']

        if not_changed:
            response.serve_error(304)
        else:
            response.client.sendall(response.create_response_header(200, self.resources[res_id]['headers']))
            cachedir = response.config['resources']['cache']
            with open(cachedir + '/' + res_id, 'br') as f:
                response.client.sendall(f.read())

def get_resource_id(uri):
    return hashlib.md5(uri.encode('ascii')).hexdigest()

def can_be_cached(response):
    if response.status != 200:
        return False, None

    headers = dict(response.getheaders())

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
                return True, time.gmtime(time.time() + int(value))

    if 'Expires' in headers:
        if headers['Expires'] == '-1':
            return False, None
        expires = email.utils.parsedate(headers['Expires'])
        return (expires > time.gmtime()), expires

    return True, None

