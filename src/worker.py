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
            print(req)

            client.send(http.create_response(200, headers={
                    'Content-Type': 'text/plain; charset=utf-8',
                },
                body='Not done yet...'
            ).encode('ascii'))

            client.close()
