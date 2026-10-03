"""Send one phase of verify_poselib_gui.py to a DISPOSABLE GUI Maya and print what it wrote.

    & 'C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe' `
        docs/superpowers/plans/verify_poselib_gui_send.py <phase> [--port 7031] [--purge]

Stdlib only (mayapy is used as a plain Python: there is no system Python here). Never the
animator's Maya: port 7001 is refused. The output goes into `$env:POSELIB_GUI_OUT` (else a
folder in %TEMP%), one file per send (a fixed name returns the previous run's text when the
poll races the write - the bridge's own lesson). The sender WAITS for the port's reply before it
closes the socket (a sender that closed at once never had its line run), then polls the file for
the runner's last line.
"""

import io
import os
import socket
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(HERE, "verify_poselib_gui_run.py").replace("\\", "/")
REFUSED_PORTS = (7001,)      # the animator's own Maya


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    phase = argv[0]
    port = 7031
    purge = "--purge" in argv
    if "--port" in argv:
        port = int(argv[argv.index("--port") + 1])
    if port in REFUSED_PORTS:
        print("refused: port %d is the animator's Maya" % port)
        return 2
    wait = 1800.0
    if "--wait" in argv:
        wait = float(argv[argv.index("--wait") + 1])
    folder = os.environ.get("POSELIB_GUI_OUT") or os.path.join(
        os.environ.get("TEMP", "."), "skeldar_poselib_gui")
    if not os.path.isdir(folder):
        os.makedirs(folder)
    out = os.path.join(folder, "%s_%d.txt" % (phase, int(time.time() * 1000))).replace("\\", "/")
    line = ('exec(open(r"%s", encoding="utf-8").read(), {"__name__": "__main__", '
            '"__file__": r"%s", "PHASE": %r, "OUT": r"%s", "PURGE": %s})\n'
            % (RUNNER, RUNNER, phase, out, purge))
    started = time.time()
    sock = socket.create_connection(("127.0.0.1", port), timeout=10)
    try:
        sock.sendall(line.encode("utf-8"))
        sock.settimeout(wait)
        try:
            sock.recv(4096)
        except socket.timeout:
            print("(no reply from the port in %.0f s)" % wait)
    finally:
        sock.close()
    end = "== END %s ==" % phase
    text = ""
    while time.time() - started < wait:
        if os.path.isfile(out):
            with io.open(out, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
            if end in text:
                break
        time.sleep(0.5)
    sys.stdout.write(text)
    print("(%s in %.1f s, %s)" % (phase, time.time() - started, out))
    return 0 if end in text else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
