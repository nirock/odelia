import socket
import time
import struct
import logging
import sys
from threading import Thread
import select

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout, level=logging.INFO)

WEBSERVER_COMMUNICATOR_PORT = 15236
BUFFER_SIZE = 2 ** 16


def safe_create_tcp_socket(ip, port, max_listeners):
    sock = socket.socket()
    while True:
        try:
            sock.bind((ip, port))
            break
        except socket.error:
            logging.fatal(
                "Could not bind on port %d."
                " Waiting 5 seconds and retry" % (port,))
            time.sleep(5)
    sock.listen(max_listeners)
    return sock


class SelectBasedServer(object):

    def get_fds(self):
        raise NotImplementedError

    def handle_fds(self, rfds):
        raise NotImplementedError


class WebServerCommunicator(SelectBasedServer):

    def __init__(self, handle_message_callback):
        self._logger = logging.getLogger("WebServerCommunicator")
        super(WebServerCommunicator, self).__init__()

        self._init_socket()
        self._handle_message_callback = handle_message_callback

        self._logger.info("Initialized")

    def __del__(self):
        self._logger.info("__del__")
        self._sock.close()

    def _init_socket(self, ip="127.0.0.1", port=WEBSERVER_COMMUNICATOR_PORT):
        self._logger.info("Init socket")
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind((ip, port))
        self._sock.setblocking(0)

    def get_fds(self):
        return [self._sock]

    def handle_fds(self, rfds):
        if self._sock in rfds:
            while True:
                try:
                    message = self._sock.recv(BUFFER_SIZE)
                except socket.error:
                    break
            self._logger.info("Received message %s" % (message.encode("hex")))
            self._handle_message_callback(message)


class OdeliaCommunicator(SelectBasedServer):

    def __init__(self, ip="0.0.0.0", port=1221, max_listeners=5):
        self._logger = logging.getLogger("OdeliaCommunicator")
        super(OdeliaCommunicator, self).__init__()

        self._init_socket(ip, port, max_listeners)
        self._connections = []

        self._logger.info("Initialized")

    def __del__(self):
        self._logger.info("__del__")
        self._sock.close()
        for conn in self._connections:
            conn[0].close()

    def _init_socket(self, ip, port, max_listeners):
        self._logger.info("Init socket")
        self._sock = safe_create_tcp_socket(ip, port, max_listeners)

    def get_fds(self):
        return [self._sock] + [conn for conn, addr in self._connections]

    def handle_fds(self, rfds):
        for conn, addr in self._connections:
            if conn in rfds:
                if conn.recv(2 ** 16) != "":
                    continue
                conn.close()
                self._connections.remove((conn, addr))
                self._logger.info("Disconnected %s" % (str(addr),))
        if self._sock in rfds:
            conn, addr = self._sock.accept()
            conn.setblocking(0)
            self._connections.append((conn, addr))
            self._logger.info("Connected %s" % (addr,))

    def send_message(self, message):
        size = struct.pack(">I", len(message))
        for conn, addr in self._connections:
            try:
                conn.sendall(size)
                conn.sendall(message)
                self._logger.info(
                    "Sent message %s to odelia %s"
                    % (message.encode("hex"), str(addr)))
            except socket.error:
                conn.close()
                self._connections.remove((conn, addr))
                self._logger.info("Disconnected %s" % (str(addr),))


class VideoStreamer(SelectBasedServer):

    def __init__(self):
        self._logger = logging.getLogger("VideoStreamer")
        super(VideoStreamer, self).__init__()

        self._init_sockets()
        self._connections = []

        self._logger.info("Initialized")

    def __del__(self):
        self._logger.info("__del__")
        self._sock_recv_video.close()
        self._sock_send_video.close()
        for conn in self._connections:
            conn[0].close()

    def _init_sockets(self):
        self._logger.info("Init sockets")
        self._sock_recv_video = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM)
        self._sock_recv_video.bind(("0.0.0.0", 1222))
        self._sock_recv_video.setblocking(0)

        self._sock_send_video = safe_create_tcp_socket("0.0.0.0", 1223, 10)

    def get_fds(self):
        return [self._sock_recv_video, self._sock_send_video] + \
            [conn for conn, addr in self._connections]

    def handle_fds(self, rfds):
        for conn, addr in self._connections:
            if conn in rfds:
                if conn.recv(2 ** 16) != "":
                    continue
                conn.close()
                self._connections.remove((conn, addr))
                self._logger.info("Disconnected %s" % (str(addr),))
        if self._sock_send_video in rfds:
            conn, addr = self._sock_send_video.accept()
            conn.setblocking(0)
            conn.sendall(
                "HTTP/1.1 200 OK\r\nContent-Type: multipart/x-mixed-replace;"
                "boundary=Ba4oTvQMY8ew04N8dcnM\r\n\r\n")
            self._logger.info("Connected and sent header %s" % (str(addr),))
            self._connections.append((conn, addr))
        if self._sock_recv_video in rfds:
            while True:
                try:
                    data = self._sock_recv_video.recv(BUFFER_SIZE)
                except socket.error:
                    break

                content_length_string_index = data.rfind("Content-Length: ")
                if content_length_string_index == -1:
                    continue

                end_of_content_length_index = data.find(
                    "\r\n", content_length_string_index)
                length = int(
                    data[content_length_string_index + len("Content-Length: "):
                         end_of_content_length_index])
                image = data[
                    end_of_content_length_index + 4:
                    end_of_content_length_index + 4 + length]

                if (len(image) != length):
                    continue

                self._logger.debug(
                    "Sending image to %d conntions" % (len(self._connections)))

                for conn, addr in self._connections:
                    try:
                        conn.sendall(
                            "\r\n--Ba4oTvQMY8ew04N8dcnM"
                            "\r\nContent-Type: image/jpeg"
                            "\r\nContent-Length: %d\r\n\r\n"
                            % (length) + image)
                    except socket.error:
                        self._logger.info("%s disconnected" % (addr,))
                        conn.close()
                        self._connections.remove((conn, addr))


def main():
    odelia_communicator = OdeliaCommunicator()
    web_server_communicator = WebServerCommunicator(
        odelia_communicator.send_message)

    select_based_servers = [
        web_server_communicator,
        odelia_communicator,
        VideoStreamer(),
    ]

    while True:
        logging.debug("In select loop")
        rfds = []
        for server in select_based_servers:
            rfds.extend(server.get_fds())
        rfds, wfds, xfds = select.select(rfds, [], [], 10)
        for server in select_based_servers:
            server.handle_fds(rfds)


if __name__ == "__main__":
    main()
