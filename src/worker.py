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

            req = http.parse_request(client.recv(1024).decode('utf-8'))
            req['root_dir'] = self.server.root_dir

            print("%s %s" % (req['method'], req['path']))

            try:
                http.handle_request(req, client)
            except http.HTTPError as e:
                http.serve_error(e.get_code(), client)

            client.close()
