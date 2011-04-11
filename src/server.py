import socket
import threading
import queue
import sys

from worker import Worker

class Server:
    def __init__(self, addr, port):
        self.addr = addr
        self.port = port

        self.workers = []

        self.clientqueue = queue.Queue(0) # create client queue of infinite size

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((addr, port))
        self.sock.listen(5)

    def stop(self):
        self.sock.close()
        sys.exit(0)

    def serve(self, root_dir, workers = 5):
        self.root_dir = root_dir
        for i in range(workers):
            w = Worker(self)
            w.daemon = True
            w.start()

        while True:
            self.clientqueue.put(self.sock.accept())
