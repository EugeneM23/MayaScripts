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
import json
import os
import socketserver
import subprocess
import sys
import tempfile
import time
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

    # Where Maya is, for reading an FBX. The browser has no FBX reader and
    # writing one is weeks of work for a format every exporter writes
    # differently; Maya reads it for a living and is on the machine this is
    # for. Override with MAYAPY if it lives somewhere else.
    MAYAPY = os.environ.get('MAYAPY') or (
        'C:/Program Files/Autodesk/Maya2027/bin/mayapy.exe')

    def do_fbx(self):
        """Take an FBX, hand it to Maya, answer with the rig the page wants."""
        length = int(self.headers.get('Content-Length') or 0)
        if length <= 0 or length > 400 * 1024 * 1024:
            self.send_error(400, 'bad length')
            return
        blob = self.rfile.read(length)
        name = os.path.basename(self.path.split('?', 1)[0][len('/fbx/'):]) or 'drop.fbx'
        if not name.lower().endswith(('.fbx', '.ma', '.mb')):
            self.send_error(400, 'fbx, ma or mb only')
            return
        work = os.path.join(tempfile.gettempdir(), 'skeldar_slime')
        os.makedirs(work, exist_ok=True)
        src = os.path.join(work, name)
        out = os.path.join(work, name + '.rig.json')
        with open(src, 'wb') as f:
            f.write(blob)
        reader = os.path.join(HERE, 'fbxread.py')
        started = time.time()
        try:
            proc = subprocess.run([self.MAYAPY, reader, src, out],
                                  capture_output=True, timeout=600,
                                  creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except Exception as e:
            self.send_error(500, 'could not run Maya: %s' % e)
            return
        if not os.path.exists(out):
            tail = (proc.stderr or proc.stdout or b'').decode('utf-8', 'replace')[-600:]
            body = json.dumps({'error': 'Maya could not read it', 'detail': tail}).encode('utf-8')
            self.send_response(500)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        with open(out, 'rb') as f:
            body = f.read()
        print('read %s in %.1f s -> %d KB' % (name, time.time() - started, len(body) // 1024))
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        """Save a still the page sends to shots/<name>.

        The page can hand over what is on the canvas, which is how a frame gets
        looked at properly - and how the look is checked at all on a machine
        where a screenshot of the window is not available.
        """
        if self.path.startswith("/fbx/"):
            self.do_fbx()
            return
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
