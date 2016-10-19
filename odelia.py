import socket
import time
import struct
import logging
import sys
from threading import Thread
import select

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", stream=sys.stdout, level=logging.DEBUG)

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
        self._sock.bind(("127.0.0.1", WEBSERVER_COMMUNICATOR_PORT))

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

    def send_message(self, message):
        self._send_messages.append(message)

    def run(self):
        self._is_running = True
        connections = []
        while self._is_running:
            rfds, wfds, xfds = select.select([self._sock], [], [], 0.001)
            if self._sock in rfds:
                conn, addr = self._sock.accept()
                connections.append(conn)
            try:
                message = self._send_messages.pop(0)
            except IndexError:
                continue

            size = struct.pack(">I", len(message))
            for client in connections:
                try:
                    client.sendall(size)
                    client.sendall(message)
                    self._logger.info("Sent message to odelia %s" % (message.encode("hex"),))
                except socket.error:
                    logging.info("Client Disconnected")
                    client.close()
                    connections.remove(client)
        for conn in connections:
            conn.close()

    def stop(self):
        self._is_running = False


class VideoStreamer(Thread):
    def __init__(self):
        super(VideoStreamer, self).__init__()
        self._logger = logging.getLogger("VideoStreamer")
        self._is_running = False
        self._logger.info("Initialized")

    def run(self):
        self._is_running = True
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", 1222))
        sock.setblocking(0)

        sock2 = socket.socket()
        sock2.bind(("0.0.0.0", 1223))
        sock2.listen(10)

        connections = []

        while self._is_running:
            rfds, wfds, xfds = select.select([sock2, sock] + connections, [], [], 1)
            for conn in connections:
                if conn in rfds:
                    if conn.recv(2 ** 16) != "":
                        continue
                    self._logger.info("Connection closed with")
                    conn.close()
                    connections.remove(conn)
            if sock2 in rfds:
                conn = sock2.accept()[0]
                conn.setblocking(0)
                conn.sendall("HTTP/1.1 200 OK\r\nContent-Type: multipart/x-mixed-replace;boundary=Ba4oTvQMY8ew04N8dcnM\r\n\r\n")
                self._logger.info("Got connection and sent header - with %s" % (str(conn.getpeername())))
                connections.append(conn)
            if sock in rfds:
                while True:
                    try:
                        data = sock.recv(65536)
                    except socket.error:
                        break

                content_length_string_index = data.rfind("Content-Length: ")
                if content_length_string_index == -1:
                    continue

                end_of_content_length_index = data.find("\r\n", content_length_string_index)
                length = int(data[content_length_string_index + len("Content-Length: "):end_of_content_length_index])
                image = data[
                    end_of_content_length_index + 4:
                    end_of_content_length_index + 4 + length]

                if (len(image) != length):
                    continue

                for conn in connections:
                    try:
                        conn.sendall("\r\n--Ba4oTvQMY8ew04N8dcnM\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n" % (length) + image)
                    except socket.error:
                        self._logger.info("Connection closed")
                        conn.close()
                        connections.remove(conn)

        for conn in connections:
            conn.close()

        sock.close()
        sock2.close()

    def stop(self):
        self._is_running = False


if __name__ == "__main__":
    video_streamer = VideoStreamer()
    web_server_communicator = WebServerCommunicator()
    odelia_communicator = OdeliaCommunicator()
    try:
        web_server_communicator.start()
        odelia_communicator.start()
        video_streamer.start()

        while True:
            for message in web_server_communicator.recv_messages():
                odelia_communicator.send_message(message)
    except (KeyboardInterrupt, SystemExit):
        print '### Received keyboard interrupt, quitting threads ###'
    finally:
        web_server_communicator.stop()
        odelia_communicator.stop()
        video_streamer.stop()
