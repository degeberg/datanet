import socket
import threading
import queue
import sys

import httplib

class Worker(threading.Thread):
    def __init__(self, server):
        self.server = server
        threading.Thread.__init__(self)

    def run(self):
        while True:
            client, (addr, port) = self.server.clientqueue.get()
            if client == None:
                continue

            bufsize = self.server.config['server'].getint('read_bufsize')

            buf = client.recv(bufsize)
            while buf != b'' and b'\r\n\r\n' not in buf:
                buf += client.recv(bufsize)

            client.settimeout(1.0)
            response = httplib.Response(self.server.config, client, self.server.cache, self.server.proxynet)

            try:
                try:
                    req = httplib.parse_request(buf.decode('utf-8'))

                    print("Worker %s: %s %s" % (self.name.split('-')[1], req['method'], req['uri']))

                    response.handle_request(req)
                except httplib.HTTPError as e:
                    response.serve_error(e.get_code())
#                except Exception as e:
#                    sys.stderr.write(str(e))
#                    response.serve_error(500)
            except socket.error:
                pass # don't crash if client closes connection prematurely
            finally:
                client.close()
