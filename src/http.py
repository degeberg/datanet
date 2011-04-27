import urllib.parse
import os
import os.path
import datetime
import mimetypes
import email.utils
import hashlib
import zlib
import gzip
import time

import template

METHOD_HANDLERS = {}

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

def parse_request(req):
    lines = req.split("\r\n")
    try:
        method, path, protocol = lines.pop(0).split(' ')

        r = {
            'method': method,
            'path': path,
            'protocol': protocol,
            'headers': {}
        }

        for header in lines:
            if header == '': continue
            key, value = header.split(': ', 1)

            r['headers'][key] = value
    except:
        raise UserError(400)

    return r

def parse_request_uri(uri):
    res = urllib.parse.urlparse(uri)
    
    return {
        'path': res.path,
        'query': urllib.parse.parse_qs(res.query),
    }

def create_response_header(code, headers):
    headers['Server'] = 'DanielServer'
    headers['Connection'] = 'close'
    headers['Date'] = email.utils.formatdate(timeval=None, localtime=False, usegmt=True)
    headers['Accept-Ranges'] = 'none'

    res = 'HTTP/1.1 %d %s\r\n' % (code, CODES[code])
    res += ''.join(map(lambda x: "%s: %s\r\n" % x, headers.items()))+'\r\n'
    return res.encode('ascii')

def register_method_handler(method):
    def decorator(f):
        METHOD_HANDLERS[method] = f
        return f
    return decorator

@register_method_handler('GET')
@register_method_handler('HEAD')
def handle_get_and_head(req, client):
    uri = parse_request_uri(req['path'])

    real_path = req['config']['server']['webroot'] + uri['path']

    headers_only = req['method'] == 'HEAD'

    if os.path.isdir(real_path):
        if real_path[-1] != '/':
            serve_redirect(uri['path'] + '/', client, headers_only)
        elif os.path.isfile(real_path + '/index.html'):
            serve_file(uri['path'] + '/index.html', req['config']['server']['webroot'], client, {}, headers_only)
        else:
            serve_directory_listing(uri['path'], req['config']['server']['webroot'], client, headers_only)
    elif os.path.isfile(real_path):
        serve_file(uri['path'], req, client, {}, headers_only)
    else:
        serve_error(404, client, {}, headers_only)

def handle_request(req, client):
    if req['method'] not in METHOD_HANDLERS:
        raise ServerError(501)

    return METHOD_HANDLERS[req['method']](req, client)

def serve_string(code, string, client, headers={}, headers_only=False):
    headers['Content-Length'] = len(string)

    client.sendall(create_response_header(code, headers))
    if not headers_only:
        client.sendall(string)

def serve_error(code, client, headers={}, headers_only=False):
    headers['Content-Type'] = 'text/html; charset=utf-8'
    body = template.load_template('error.html', {'CODE': code, 'MSG': CODES[code]}).encode('utf-8')
    if not headers_only:
        serve_string(code, body, client, headers)

def serve_redirect(to, client, headers_only=False):
    serve_error(301, client, {'Location': to}, headers_only)

def serve_directory_listing(path, root_dir, client, headers_only=False):
    vars = {
        'PATH': path,
        'FILES': '',
    }

    try:
        for item in sorted(os.listdir(root_dir + path)):
            real_path = root_dir + path + '/' + item

            vars['FILES'] += template.load_template('dir_listing_entry.html', {
                'URL': path + item,
                'NAME': item,
                'SIZE': os.path.getsize(real_path),
                'MODTIME': datetime.datetime.fromtimestamp(os.path.getmtime(real_path)),
            })
    except OSError:
        serve_error(403, client)
        return

    serve_string(200, template.load_template('dir_listing.html', vars).encode('utf-8'), client,
                 {'Content-Type': 'text/html; charset=utf-8'}, headers_only)

def get_etag(path):
    return hashlib.md5(str(os.path.getmtime(path)).encode('ascii')).hexdigest()

def serve_file(path, req, client, headers={}, headers_only=False):
    real_path = req['config']['server']['webroot'] + path

    headers['Last-Modified'] = email.utils.formatdate(timeval=os.path.getmtime(real_path), localtime=False, usegmt=True)
    headers['ETag'] = get_etag(real_path)

    filesize = os.path.getsize(real_path)

    mime, _ = mimetypes.guess_type(real_path)
    if mime == None:
        mime = 'text/plain'

    headers['Content-Type'] = mime

    cached = False

    if 'If-None-Match' in req['headers'] and req['headers']['If-None-Match'] == headers['ETag']:
        cached = True
    if 'If-Modified-Since' in req['headers']:
        cached = cached or time.mktime(email.utils.parsedate(req['headers']['If-Modified-Since'])) > os.path.getmtime(real_path)

    if cached:
        client.sendall(create_response_header(304, headers))
        return

    if 'Accept-Encoding' in req['headers']:
        aenc = req['headers']['Accept-Encoding'].split(', ')
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

        if not found and 'identity' in aencq or filesize > int(req['config']['server']['compression_limit']) and 'identity' in aencq and aencq['identity'] == 0:
            if 'Content-Encoding' in headers: del headers['Content-Encoding']
            if 'Content-Length' in headers: del headers['Content-Length']
            client.sendall(create_response_header(406, headers))
            return

        with open(real_path, 'rb') as f:
            client.sendall(create_response_header(200, headers))
            if not headers_only:
                if comp == None:
                    headers['Content-Length'] = filesize
                    while True:
                        s = f.read(1024)
                        if len(s) == 0: break
                        client.sendall(s)
                else:
                    client.sendall(comp)
    except IOError:
        # file exists, but is unreadable. assume permission denied
        serve_error(403, client)
