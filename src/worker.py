import socket
import threading
import queue

import http

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

            try:
                req = http.parse_request(buf.decode('utf-8'))
                req['config'] = self.server.config

                print("Worker %s: %s %s" % (self.name.split('-')[1], req['method'], req['path']))

                http.handle_request(req, client)
            except http.HTTPError as e:
                http.serve_error(e.get_code(), client)
            except socket.error:
                pass # don't crash if client closes connection prematurely
            except:
                http.serve_error(500, client)

            client.close()
