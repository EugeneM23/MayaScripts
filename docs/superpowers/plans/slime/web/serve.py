"""Serve this folder, so the page can load its own scripts.

A page opened with a double click runs from file://, where Chrome refuses to
load a sibling script, so the prototype needs an address. Run

    python serve.py

(or, with no python on the PATH, Maya's own:
 "C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe" serve.py)

and open the address it prints. Chrome or Edge: WebGPU is what this needs, and
Firefox and Safari do not have it yet.
"""
import http.server
import os
import socketserver
import sys
import webbrowser

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8744
HERE = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=HERE, **kw)

    def end_headers(self):
        # Nothing here should ever be served from a cache: the whole point is
        # editing a shader and pressing reload.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_POST(self):
        """Save a still the page sends to shots/<name>.

        The page can hand over what is on the canvas, which is how a frame gets
        looked at properly - and how the look is checked at all on a machine
        where a screenshot of the window is not available.
        """
        if not self.path.startswith("/save/"):
            self.send_error(404)
            return
        name = os.path.basename(self.path[len("/save/"):]) or "shot.png"
        if not name.endswith((".png", ".jpg")):
            self.send_error(400, "png or jpg only")
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > 40 * 1024 * 1024:
            self.send_error(400, "bad length")
            return
        folder = os.path.join(HERE, "shots")
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, name), "wb") as f:
            f.write(self.rfile.read(length))
        self.send_response(200)
        self.send_header("Content-Length", "2")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, fmt, *args):
        pass


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    url = "http://127.0.0.1:%d/" % PORT
    with Server(("127.0.0.1", PORT), Handler) as httpd:
        print("Slime is at %s   (Ctrl+C to stop)" % url)
        try:
            webbrowser.open(url)
        except Exception:
            pass
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")


if __name__ == "__main__":
    main()
