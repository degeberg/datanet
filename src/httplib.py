import urllib.parse
import http.client
import os
import os.path
import datetime
import mimetypes
import email.utils
import hashlib
import zlib
import gzip
import time
import re
import tempfile
import random

import template
import cache
import proxynet

METHOD_HANDLERS = {}

PROXY_TIMEOUT = 20

CODES = {
    100: 'Continue',
    101: 'Switching Protocols',

    200: 'OK',
    201: 'Created',
    202: 'Accepted',
    203: 'Non-Authoritative Information',
    204: 'No Content',
    205: 'Reset Content',
    206: 'Partial Content',

    300: 'Multiple Choices',
    301: 'Moved Permanently',
    302: 'Found',
    303: 'See Other',
    304: 'Not Modified',
    305: 'Use Proxy',
    307: 'Temporary Redirect',

    400: 'Bad Request',
    401: 'Unauthorized',
    402: 'Payment Required',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    406: 'Not Acceptable',
    407: 'Proxy Authentication Required',
    408: 'Request Timeout',
    409: 'Conflict',
    410: 'Gone',
    411: 'Length Required',
    412: 'Precondition Failed',
    413: 'Request Entity Too Large',
    414: 'Request-URI Too Long',
    415: 'Unsupported Media Type',
    416: 'Requested Range Not Satisfiable',
    417: 'Expectation Failed',

    500: 'Internal Server Error',
    501: 'Not Implemented',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
    504: 'Gateway Timeout',
    505: 'HTTP Version Not Supported',
}

class HTTPError(Exception):
    def __init__(self, code):
        self.code = code

    def get_code(self):
        return self.code

    def __str__(self):
        if self.code in CODES:
            return "%d %s" % (code, CODES[code])
        else:
            return str(code)

    def get_msg(self):
        if self.code in CODES:
            return CODES[code]
        else:
            return ''

class UserError(HTTPError):
    pass

class ServerError(HTTPError):
    pass

def parse_headers(headers):
    if type(headers) == str:
        headers = headers.split("\r\n")

    r = {}

    for header in headers:
        m = re.match('^(.+?):(?: (.*))?', header)
        if not m: break
        key, value = m.group(1, 2)
        if value == None:
            value = ''
        r[key] = value.strip()

    return r

def parse_request(req):
    lines = req.split("\r\n")
    try:
        method, uri, protocol = lines.pop(0).split(' ')

        r = {
            'method': method,
            'uri': uri,
            'protocol': protocol,
            'headers': {}
        }

        r['headers'] = parse_headers(lines)
    except:
        raise UserError(400)

    return r

def get_etag(path):
    return hashlib.md5(str(os.path.getmtime(path)).encode('ascii')).hexdigest()

def register_method_handler(method):
    def decorator(f):
        METHOD_HANDLERS[method] = f
        return f
    return decorator

class Response:
    def __init__(self, config, client, cache, proxymanager=None):
        self.config = config
        self.client = client
        self.cache = cache
        self.proxymanager = proxymanager
        self.tpl = template.TemplateManager(config['resources']['templates'])

    def create_response_header(self, code, headers):
        headers['Server'] = 'DanielServer'
        headers['Connection'] = 'close'
        headers['Date'] = email.utils.formatdate(timeval=None, localtime=False, usegmt=True)
        headers['Accept-Ranges'] = 'none'

        res = 'HTTP/1.1 %d %s\r\n' % (code, CODES[code])
        res += ''.join(map(lambda x: "%s: %s\r\n" % x, headers.items()))+'\r\n'
        return res.encode('ascii')

    @register_method_handler('GET')
    @register_method_handler('HEAD')
    def __handle_get_and_head(**kwargs):
        self = kwargs['self']
        self.req = kwargs['req']

        uridata = urllib.parse.urlparse(self.req['uri'])

        headers_only = self.req['method'] == 'HEAD'

        if uridata.netloc != '':
            self.serve_remote(headers_only)
        else:
            real_path = self.config['server']['webroot'] + uridata.path

            if os.path.isdir(real_path):
                if real_path[-1] != '/':
                    self.serve_redirect(uridata.path + '/', headers_only)
                elif os.path.isfile(real_path + '/index.html'):
                    self.serve_file(uridata.path + '/index.html', {}, headers_only)
                else:
                    self.serve_directory_listing(uridata.path, headers_only)
            elif os.path.isfile(real_path):
                self.serve_file(uridata.path, {}, headers_only)
            else:
                self.serve_error(404, {}, headers_only)

    def handle_request(self, req):
        if req['method'] not in METHOD_HANDLERS:
            raise ServerError(501)

        return METHOD_HANDLERS[req['method']](self=self, req=req, client=self.client)

    def serve_remote(self, headers_only=False, body=None):
        uridata = urllib.parse.urlparse(self.req['uri'])
        headers = self.req['headers']

        use_proxy_peer = False
        if self.proxymanager == None:
            conn = http.client.HTTPConnection(uridata.netloc)
        else:
            if not self.proxymanager.check_whitelist(uridata.netloc):
                self.serve_error(403)
                return

            if 'Max-Forwards' not in headers or int(headers['Max-Forwards']) > 5:
                headers['Max-Forwards'] = '5'

            headers['Super-Via'] = ''

            if int(headers['Max-Forwards']) > 1:
                try:
                    peer = self.proxymanager.get_peer(True)
                except proxynet.EmptyPeerList:
                    raise ServerError(502)
                conn = http.client.HTTPConnection('{0}:{1}'.format(peer['ip'], peer['port']), timeout=PROXY_TIMEOUT)
                headers['Max-Forwards'] = str(int(headers['Max-Forwards']) - 1)
                use_proxy_peer = True
            else:
                conn = http.client.HTTPConnection(uridata.netloc, timeout=PROXY_TIMEOUT)

        cachedir = self.config['resources']['cache']

        res_id = cache.get_resource_id(self.req['uri'])

        method = 'HEAD' if headers_only else 'GET'

        if self.cache.is_cached(res_id) and method == 'GET':
            self.cache.serve_resource(res_id, self)
            return

        path = uridata.path
        if uridata.query:
            path += '?' + uridata.query

        try: # stupid browser cache...
            del headers['If-None-Match']
            del headers['If-Modified-Since']
        except:
            pass

        if 'Via' in headers and use_proxy_peer: # TODO: fix hard coded IP address
            if headers['Via'] == '':
                headers['Via'] = '1.1 109.74.202.182:{0}'.format(self.config['server']['port'])
            else:
                headers['Via'] = headers['Via'] + ', 1.1 109.74.202.182:{0}'.format(self.config['server']['port'])
        if 'Via' in headers and not use_proxy_peer:
            del headers['Via']

        try:
            if use_proxy_peer:
                conn.request(method, self.req['uri'], body, headers)
            else:
                conn.request(method, path, body, headers)
        except: # bad peer
            self.proxymanager.remove_peer(peer['ip'])
            raise ServerError(504)

        res = conn.getresponse()

        rheaders = dict(res.getheaders())
        rheaders['Transfer-Encoding'] = 'identity'

        bufsize = self.config['server'].getint('read_bufsize')

        if method == 'GET':
            do_cache, cache_expires = cache.can_be_cached(res)
        else:
            do_cache = False

        response_header = self.create_response_header(res.status, rheaders)

        if do_cache:
            tmpfd, tmpname = tempfile.mkstemp(dir=cachedir+'/tmp')

        self.client.sendall(response_header)

        buf = res.read(bufsize)
        while buf:
            self.client.send(buf)
            if do_cache:
                os.write(tmpfd, buf)
            buf = res.read(bufsize)

        if do_cache:
            os.close(tmpfd)
            os.rename(tmpname, cachedir + '/' + res_id)
            self.cache.add_resource(res_id, cache_expires, rheaders)

    def serve_string(self, code, string, headers={}, headers_only=False):
        headers['Content-Length'] = len(string)

        self.client.sendall(self.create_response_header(code, headers))
        if not headers_only:
            self.client.sendall(string)

    def serve_error(self, code, headers={}, headers_only=False):
        headers['Content-Type'] = 'text/html; charset=utf-8'
        body = self.tpl.load_template('error.html', {'CODE': code, 'MSG': CODES[code]}).encode('utf-8')
        if not headers_only:
            self.serve_string(code, body, headers)

    def serve_redirect(self, to, headers_only=False):
        self.serve_error(301, {'Location': to}, headers_only)

    def serve_directory_listing(self, path, headers_only=False):
        vars = {
            'PATH': path,
            'FILES': '',
        }

        webroot = self.config['server']['webroot']

        try:
            for item in sorted(os.listdir(webroot + path)):
                real_path = webroot + path + '/' + item

                vars['FILES'] += self.tpl.load_template('dir_listing_entry.html', {
                    'URL': path + item,
                    'NAME': item,
                    'SIZE': os.path.getsize(real_path),
                    'MODTIME': datetime.datetime.fromtimestamp(os.path.getmtime(real_path)),
                })
        except OSError:
            serve_error(403)
            return

        self.serve_string(200, self.tpl.load_template('dir_listing.html', vars).encode('utf-8'),
                     {'Content-Type': 'text/html; charset=utf-8'}, headers_only)

    def serve_file(self, path, headers={}, headers_only=False):
        real_path = self.config['server']['webroot'] + path

        headers['Last-Modified'] = email.utils.formatdate(timeval=os.path.getmtime(real_path), localtime=False, usegmt=True)
        headers['ETag'] = get_etag(real_path)

        filesize = os.path.getsize(real_path)

        mime, _ = mimetypes.guess_type(real_path)
        if mime == None:
            mime = 'text/plain'

        headers['Content-Type'] = mime

        cached = False

        if 'If-None-Match' in self.req['headers'] and self.req['headers']['If-None-Match'] == headers['ETag']:
            cached = True
        if 'If-Modified-Since' in self.req['headers']:
            cached = cached or time.mktime(email.utils.parsedate(self.req['headers']['If-Modified-Since'])) > os.path.getmtime(real_path)

        if cached:
            self.client.sendall(self.create_response_header(304, headers))
            return

        if 'Accept-Encoding' in self.req['headers']:
            aenc = self.req['headers']['Accept-Encoding'].split(', ')
        else:
            aenc = []

        try:
            aencq = {}
            comp = None
            for t in aenc:
                t = t.split(';q=')
                if len(t) > 1:
                    aencq[t[0]] = float(t[1])
                else:
                    aencq[t[0]] = 1.0

            if '*' in aencq:
                for x in ('identity', 'gzip', 'deflate'):
                    if x not in aencq:
                        aencq[x] = aencq['*']
                del aencq['*']

            found = False
            for t, q in sorted(aencq.items(), key=lambda x: x[1], reverse=True):
                if q == 0: continue

                if t == 'identity':
                    found = True
                    break
                elif t == 'gzip':
                    headers['Content-Encoding'] = 'gzip'
                    with open(real_path, 'rb') as f:
                        comp = gzip.compress(f.read())
                    headers['Content-Length'] = len(comp)
                    found = True
                    break
                elif t == 'deflate':
                    headers['Content-Encoding'] = 'deflate'
                    with open(real_path, 'rb') as f:
                        comp = zlib.compress(f.read())
                    headers['Content-Length'] = len(comp)
                    found = True
                    break

            if not found and 'identity' in aencq or filesize > int(self.config['server']['compression_limit']) and 'identity' in aencq and aencq['identity'] == 0:
                if 'Content-Encoding' in headers: del headers['Content-Encoding']
                if 'Content-Length' in headers: del headers['Content-Length']
                self.serve_error(406)
                return

            headers['Content-Length'] = os.path.getsize(real_path)
            with open(real_path, 'rb') as f:
                self.client.sendall(self.create_response_header(200, headers))
                if not headers_only:
                    if comp == None:
                        headers['Content-Length'] = filesize
                        while True:
                            s = f.read(1024)
                            if len(s) == 0: break
                            self.client.sendall(s)
                    else:
                        self.client.sendall(comp)
        except IOError:
            # file exists, but is unreadable. assume permission denied
            self.serve_error(403)
