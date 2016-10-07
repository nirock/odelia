import socket
import time
import struct
import logging
import sys
from threading import Thread
import select

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

WEBSERVER_COMMUNICATOR_PORT = 15236

BUFFER_SIZE = 2 ** 16


class WebServerCommunicator(Thread):
    def __init__(self):
        super(WebServerCommunicator, self).__init__()
        self._logger = logging.getLogger("WebServerCommunicator")
        self._init_socket()
        self._recv_messages = []
        self._is_running = False
        self._logger.debug("Initialized")

    def __del__(self):
        self._logger.debug("__del__")
        self._sock.close()

    def _init_socket(self):
        self._logger.debug("Init socket")
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setblocking(0)
        self._sock.bind(("127.0.0.1", 15236))

    def run(self):
        self._logger.info("Web server thread running")
        self._is_running = True
        while self._is_running:
            try:
                message = self._sock.recv(BUFFER_SIZE)
                self._logger.info("Received message %s" % (message))
                self._recv_messages.append(message)
            except socket.error:
                pass  # Probably timeout passed
            time.sleep(1)

    def stop(self):
        self._is_running = False

    def recv_messages(self):
        messages = []
        while len(self._recv_messages) > 0:
            messages.append(self._recv_messages.pop(0))
        return messages


class OdeliaCommunicator(Thread):
    def __init__(self, ip="0.0.0.0", port=1221, max_listeners=1):
        super(OdeliaCommunicator, self).__init__()
        self._logger = logging.getLogger("OdeliaCommunicator")
        self._init_socket(ip, port, max_listeners)
        self._is_running = False
        self._logger.info("Initialized")
        self._send_messages = []

    def _init_socket(self, ip, port, max_listeners):
        self._sock = socket.socket()
        self._sock.bind((ip, port))
        self._sock.listen(max_listeners)

    def _search_for_client(self):
        rfds = []
        while self._is_running:
            rfds, wfds, xfds = select.select([self._sock], [], [], 1)
            if len(rfds) != 0:
                return self._sock.accept()
        return None

    def _handle_client(self):
        self._logger.info("Waiting for client")
        client = self._search_for_client()
        try:
            while self._is_running:
                while len(self._send_messages) != 0:
                    message = self._send_messages.pop(0)
                    size = struct.pack(">I", len(message))
                    client.sendall(size)
                    client.sendall(message)
                    self._logger.info("Sent message to odelia %s" % (message,))
                time.sleep(0.01)
        except socket.error:
            logging.info("Client Disconnected")
        finally:
            if client is not None:
                client.close()

    def send_message(self, message):
        self._send_messages.append(message)

    def run(self):
        self._is_running = True
        while self._is_running:
            self._handle_client()

    def stop(self):
        self._is_running = False

if __name__ == "__main__":
    web_server_communicator = WebServerCommunicator()
    odelia_communicator = OdeliaCommunicator()
    try:
        web_server_communicator.start()
        odelia_communicator.start()

        while True:
            for message in web_server_communicator.recv_messages():
                odelia_communicator.send_message(message)
            time.sleep(0.01)
    except (KeyboardInterrupt, SystemExit):
        print '### Received keyboard interrupt, quitting threads ###'
    finally:
        web_server_communicator.stop()
        odelia_communicator.stop()
