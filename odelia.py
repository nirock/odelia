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
            except socket.error:
                time.sleep(0.001)  # Nothing to receive
                continue

            self._logger.info(
                "Received message %s" % (message.encode("hex")))
            self._recv_messages.append(message)

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

    def __del__(self):
        self._logger.debug("__del__")
        self._sock.close()

    def _init_socket(self, ip, port, max_listeners):
        self._logger.debug("Init socket")
        self._sock = socket.socket()
        while True:
            try:
                self._sock.bind((ip, port))
                break
            except socket.error:
                self._logger.fatal(
                    "Could not bind on port %d. Waiting 5 seconds and retry"
                    % (port,))
                time.sleep(5)

        self._sock.listen(max_listeners)

    def _search_for_client(self):
        self._logger.info("Waiting for client")
        rfds = []
        while self._is_running:
            rfds, wfds, xfds = select.select([self._sock], [], [], 1)
            if len(rfds) != 0:
                conn, addr = self._sock.accept()
                self._logger.info("Client Connected %s" % (str(addr)))
                return conn, addr
        return None

    def _handle_client(self):
        client = self._search_for_client()
        try:
            while self._is_running:
                try:
                    message = self._send_messages.pop(0)
                except IndexError:
                    # Probably no messages are waiting
                    time.sleep(0.001)
                    continue

                size = struct.pack(">I", len(message))
                client[0].sendall(size)
                client[0].sendall(message)
                self._logger.info("Sent message to odelia %s" % (message,))

        except socket.error:
            logging.info("Client Disconnected")
        finally:
            if client is not None:
                logging.info("Closing connection with client")
                client[0].close()

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
    except (KeyboardInterrupt, SystemExit):
        print '### Received keyboard interrupt, quitting threads ###'
    finally:
        web_server_communicator.stop()
        odelia_communicator.stop()
