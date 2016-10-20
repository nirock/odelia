from flask import Flask, redirect, render_template, g
from odelia import WEBSERVER_COMMUNICATOR_PORT
import socket

app = Flask("Odelia")

KEYS = {
    "UP": 0,
    "DOWN": 1,
    "RIGHT": 2,
    "LEFT": 3,
    "STOP": 4
}


@app.route("/")
def hello():
    data = ""
    for key, value in KEYS.items():
        data += "<a href='/key/%d'>%s</a><br />" % (value, key,)
    return render_template('index.html', data=data)


@app.route("/key/<int:key_id>", methods=['GET', 'POST'])
def key(key_id):
    conn = get_communicator()
    conn.sendall(chr(key_id))
    return "Done"


def get_communicator():
    if not hasattr(g, "communicator_sock"):
        g.communicator_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        g.communicator_sock.connect(("127.0.0.1", WEBSERVER_COMMUNICATOR_PORT))
    return g.communicator_sock


@app.teardown_appcontext
def close_connection(exception):
    if hasattr(g, 'communicator_sock'):
        g.communicator_sock.close()

if __name__ == "__main__":
    app.run("0.0.0.0", 80, debug=True, threaded=True)
