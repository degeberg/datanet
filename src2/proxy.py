#!/usr/bin/env python2

# Based on:
#   Sample solution for Assignment 2, Datanet 2010/2011
#   Christian Jacobsen, 2011

import BaseHTTPServer
import SocketServer
import httplib
import urlparse
import socket

import proxynet

multithreaded  = True
server_address = ('', 8000)
via_header     = '1.1 DatanetProxy'

# RFC2616 hop-by-hop headers
hop_by_hop_headers = [
        'connection',
        'keep-alive',
        'proxy-authenticate',
        'proxy-authorization',
        'te',
        'trailers',
        'transfer-encoding',
        'upgrade']

# Other hop-by-hop headers I have seen
hop_by_hop_headers += [
        'proxy-connection' # Firefox
        ]

class MultiThreadedHTTPServer(
        SocketServer.ThreadingMixIn, 
        BaseHTTPServer.HTTPServer):
    pass

class Headers(object):
    def __init__(self, headers=None):
        self.headers = {}
        if isinstance(headers, dict):
            self.headers = dict(headers)
        elif headers:
            for k, v in headers:
                self.addheader(k, v)
    def setheader(self, key, value):
        key = key.lower()
        self.headers[key] = value
    def addheader(self, key, value, prepend=False):
        key = key.lower()
        v = self.headers.get(key, None)
        if v is not None:
            if prepend:
                value = value + ', ' + v
            else:
                value = v + ', ' + value
        self.headers[key] = value
    def __contains__(self, key):
        return key.lower() in self.headers
    def __len__(self):
        return len(self.headers)
    def __getitem__(self, key):
        return self.headers[key.lower()]
    def __setitem__(self, key, value):
        self.addheader(key, value)
    def __delitem__(self, key):
        key = key.lower()
        if key in self.headers:
            del self.headers[key]
    def __iter__(self):
        return iter(self.headers)
    def keys(self):
        return [k.title() for k in self.headers.keys()]
    def values(self):
        return self.headers.values()
    def items(self):
        return [(k.title(), v) for k, v in self.headers.items()]
    def __str__(self):
        return '\n'.join(['%s: %s' % (k, v) for k, v in self.items()])
           
header_exceptions = dict(zip(hop_by_hop_headers,
        [lambda a, b, c: True] * len(hop_by_hop_headers)))

def fix_headers(headers, exceptions):
    new_headers = Headers()
    for k, v in headers:
        k = k.strip().lower()
        if k in exceptions:
            if exceptions[k](new_headers, k, v): continue
        new_headers.addheader(k.title(), v)
    return new_headers

class ProxyServer(BaseHTTPServer.BaseHTTPRequestHandler):
    server_version = 'DatanetProxyServer/0.1'
    def send_header(self, k, v, really_send=False):
        # BaseHTTPRequestHandler always sends a Date: and Server: 
        # header, but we want the values from the upstream server,
        # not the values that BaseHTTPRequestHandler makes up
        # so override this method so date and server are only sent when
        # we send them!
        if not really_send and k.lower() == 'date': return
        if not really_send and k.lower() == 'server': return
        BaseHTTPServer.BaseHTTPRequestHandler.send_header(self, k, v)
    def do_POST(self):
        self.proxy('POST')
    def do_HEAD(self):
        self.proxy('HEAD')
    def do_GET(self):
        self.proxy('GET')
    def proxy(self, method):
        if not self.path.startswith('http'):
            return self.send_error(403, 'scheme not supported')

        u = urlparse.urlparse(self.path)
        if u.scheme == 'http':
            c = httplib.HTTPConnection(u.netloc, timeout=10)
        else:
            return self.send_error(403, 'scheme not supported')
        url = urlparse.urlunparse(('', '') + u[2:])

        connection = None
        request_header_exceptions = dict(header_exceptions)
        def connection_exception(h, k, v):
            global connection
            connection = v
            return True
        request_header_exceptions['connection'] = connection_exception
        headers = fix_headers(self.headers.items(), request_header_exceptions)
        if connection:
            for f in [f.strip() for f in connection.split(',')]:
                if f in headers: del headers[f]
        headers.addheader('Via', via_header)
        headers.addheader('Connection', 'close')

        try:
            c.putrequest(method, url, True, True)
            for h in headers.items():
                c.putheader(*h)
            c.endheaders()
            content_length = int(self.headers.get('Content-Length', 0))
            while content_length > 0:
                data = self.rfile.read(min(content_length, 4096))
                if len(data) == 0:
                    return self.send_error(400)
                c.send(data)
                content_length -= len(data)
        except socket.gaierror:
            return self.send_error(404, 'name resolution error')
        except socket.timeout:
            return self.send_error(504)
        except ValueError:
            return self.send_error(502)
        except httplib.BadStatusLine:
            return self.send_error(502, 'Bad Gateway: Bad status line')

        r = c.getresponse()
        connection = None
        response_header_exceptions = dict(header_exceptions)
        response_header_exceptions['connection'] = connection_exception
        headers = fix_headers(r.getheaders(), response_header_exceptions)
        if connection:
            for f in [f.strip() for f in connection.split(',')]:
                if f in headers: del headers[f]
        headers.addheader('Via', via_header)
        headers.addheader('Connection', 'close')
        self.send_response(r.status, r.reason)
        for h, v in headers.items():
            self.send_header(h, v, really_send=True)
        self.end_headers()

        data = r.read(4096)
        while data:
            self.wfile.write(data)
            data = r.read(4096)
        c.close()

if __name__ == '__main__':
    if multithreaded:
        httpproxyd = MultiThreadedHTTPServer(server_address, ProxyServer)
    else:
        httpproxyd = BaseHTTPServer.HTTPServer(server_address, ProxyServer)
    httpproxyd.proxymanager = proxynet.ProxyManager('datanet2011tracker.appspot.com', server_address[1])
    httpproxyd.proxymanager.daemon = True
    httpproxyd.proxymanager.start()
    httpproxyd.serve_forever()
