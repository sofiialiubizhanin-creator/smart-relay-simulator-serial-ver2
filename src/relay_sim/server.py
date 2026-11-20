"""TCP servers: the relay "serial" port and the control API port, plus the exchange log."""
import socket
import socketserver
import sys
import threading
from datetime import datetime

from .clock import ManualClock
from .device import MAX_LINE_LEN, RelayDevice

MAX_CONTROL_LINE = 256  # bytes; control lines are short, longer ones are cut and rejected

_log_stream = sys.stderr
_log_lock = threading.Lock()


def set_log_file(path: str) -> None:
    """Send the exchange log to a file instead of stderr."""
    global _log_stream
    _log_stream = open(path, "a", encoding="utf-8", buffering=1)


def log(source: str, direction: str, payload: object) -> None:
    ts = datetime.now().isoformat(timespec="milliseconds")
    with _log_lock:
        print(f"{ts} {source} {direction} {payload!r}", file=_log_stream, flush=True)


class _Server(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, addr, handler, device: RelayDevice, lock: threading.Lock):
        self.device = device
        self.lock = lock
        super().__init__(addr, handler)


class _Server6(_Server):
    address_family = socket.AF_INET6


class SerialHandler(socketserver.BaseRequestHandler):
    """Reads \\n-terminated command lines and writes one reply line per command."""

    def handle(self) -> None:
        sock: socket.socket = self.request
        device: RelayDevice = self.server.device
        buf = bytearray()
        overflow = False
        while True:
            try:
                data = sock.recv(1024)
            except OSError:
                return
            if not data:
                return
            while data:
                idx = data.find(b"\n")
                part, data = (data, b"") if idx < 0 else (data[:idx], data[idx + 1:])
                if not overflow:
                    buf += part
                    if len(buf) > MAX_LINE_LEN:  # never buffer more than the limit
                        overflow = True
                        buf.clear()
                if idx < 0:
                    continue
                line = bytes(buf)
                with self.server.lock:
                    reply = device.handle_line(line, overflow=overflow)
                log("SIM", "RX", "<line longer than 32 bytes>" if overflow else line)
                buf.clear()
                overflow = False
                if reply is None:
                    log("SIM", "--", "silent: line discarded")
                    continue
                log("SIM", "TX", reply)
                try:
                    sock.sendall(reply + b"\n")
                except OSError:
                    return


class ControlHandler(socketserver.StreamRequestHandler):
    """Control API for tests (requirements section 2.3). One command per line, one reply per line."""

    def handle(self) -> None:
        try:
            while raw := self.rfile.readline(MAX_CONTROL_LINE):
                cmd = raw.decode("ascii", "replace").strip()
                with self.server.lock:
                    reply = self.execute(cmd)
                log("CTRL", "<>", f"{cmd} -> {reply}")
                self.wfile.write(reply.encode() + b"\n")
                self.wfile.flush()
        except OSError:  # client went away: nothing to report
            return

    def execute(self, cmd: str) -> str:
        device: RelayDevice = self.server.device
        parts = cmd.split()
        name, args = (parts[0], parts[1:]) if parts else ("", [])
        if name == "RESET" and not args:
            device.reset()
        elif name == "SET_STATE" and args in (["ON"], ["OFF"]):
            device.set_state(args[0])
        elif name == "GET_STATE" and not args:
            return f"STATE {device.state}"
        elif name == "FAULT" and args in (["HW_FAULT"], ["NONE"]):
            device.set_fault(args[0] == "HW_FAULT")
        elif name == "SILENCE" and args in (["ON"], ["OFF"]):
            device.set_silent(args[0] == "ON")
        elif name == "ADVANCE" and len(args) == 1:
            if not isinstance(device.clock, ManualClock):
                return "ERR NOT_MANUAL_CLOCK"
            try:
                device.clock.advance(float(args[0]))
            except ValueError:
                return "ERR BAD_ARG"
        else:
            return "ERR UNKNOWN_CONTROL_CMD"
        return "OK"


def _bind(host: str, port: int, handler, device, lock) -> list[_Server]:
    """Bind one listener, or for "localhost" both 127.0.0.1 and ::1 on the same port.

    Clients resolving "localhost" often try ::1 first; on Windows a refused ::1 attempt costs ~2 s.
    With port 0 a new free port is tried if the IPv4 one is taken on ::1.
    """
    if host != "localhost":
        return [_Server((host, port), handler, device, lock)]
    for _ in range(5 if port == 0 else 1):
        v4 = _Server(("127.0.0.1", port), handler, device, lock)
        try:
            return [v4, _Server6(("::1", v4.server_address[1]), handler, device, lock)]
        except OSError:
            v4.server_close()
    log("SIM", "--", "IPv6 loopback unavailable: listening on 127.0.0.1 only")
    return [_Server(("127.0.0.1", port), handler, device, lock)]


def start_servers(device: RelayDevice, host: str, port: int, control_port: int):
    """Start the serial and control servers. Returns (serial_port, control_port, servers)."""
    lock = threading.Lock()
    serial_srvs = _bind(host, port, SerialHandler, device, lock)
    try:
        control_srvs = _bind(host, control_port, ControlHandler, device, lock)
    except OSError:
        for srv in serial_srvs:
            srv.server_close()
        raise
    servers = serial_srvs + control_srvs
    for srv in servers:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    return serial_srvs[0].server_address[1], control_srvs[0].server_address[1], servers
