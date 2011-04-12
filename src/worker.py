import socket
import threading
import queue

import http

BUFSIZE=1024

class Worker(threading.Thread):
    def __init__(self, server):
        self.server = server
        threading.Thread.__init__(self)

    def run(self):
        while True:
            client, (addr, port) = self.server.clientqueue.get()
            if client == None:
                continue

            buf = client.recv(BUFSIZE)
            while buf != b'' and b'\r\n\r\n' not in buf:
                buf += client.recv(BUFSIZE)

            req = http.parse_request(buf.decode('utf-8'))
            req['root_dir'] = self.server.root_dir

            print("%s %s" % (req['method'], req['path']))

            try:
                http.handle_request(req, client)
            except http.HTTPError as e:
                http.serve_error(e.get_code(), client)
            except socket.error:
                pass # don't crash if client closes connection prematurely

            client.close()
