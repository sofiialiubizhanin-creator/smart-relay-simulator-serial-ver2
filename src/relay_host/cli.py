"""relay-host [--host H] [--port P] [--timeout S] COMMAND

Sends COMMAND + \\n verbatim over pyserial socket://, prints the reply line.
Exit codes: 0 OK/STATUS, 1 ERR/BUSY, 2 connection or usage error, 3 no response within timeout.
If RELAY_HOST_LOG is set, appends a timestamped exchange log to that file.
"""
import argparse
import os
import socket
import sys
from datetime import datetime

import serial
from serial.urlhandler.protocol_socket import Serial as SocketSerial

EXIT_OK, EXIT_DEVICE_ERROR, EXIT_CONNECTION, EXIT_TIMEOUT = 0, 1, 2, 3


class OneShotSocketSerial(SocketSerial):
    """pyserial socket:// port without the hard-coded 0.3 s sleep in close().

    pyserial sleeps after close "in case of quick reconnects" from the same process; a one-shot CLI
    exits right after closing, so the pause only adds latency to every call.
    """

    def close(self) -> None:
        if self.is_open and self._socket:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self._socket.close()
            self._socket = None
        self.is_open = False


class _ExchangeLog:
    def __init__(self, path: str | None) -> None:
        self.path = path

    def __call__(self, direction: str, payload: object) -> None:
        if not self.path:
            return
        ts = datetime.now().isoformat(timespec="milliseconds")
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(f"{ts} HOST {direction} {payload!r}\n")


class _Parser(argparse.ArgumentParser):
    def error(self, message: str):  # usage errors -> exit 2 (argparse default is also 2)
        self.print_usage(sys.stderr)
        self.exit(EXIT_CONNECTION, f"ERROR: {message}\n")


def main(argv: list[str] | None = None) -> int:
    p = _Parser(prog="relay-host", description="Send one command to the smart relay simulator")
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", type=int, default=5000)
    p.add_argument("--timeout", type=float, default=1.0, help="seconds to wait for the reply")
    p.add_argument("command", help='command line to send verbatim, e.g. ON, OFF, STATUS ("" = empty line)')
    args = p.parse_args(argv)
    log = _ExchangeLog(os.environ.get("RELAY_HOST_LOG"))

    url = f"socket://{args.host}:{args.port}"
    try:
        port = OneShotSocketSerial(url, timeout=args.timeout, write_timeout=args.timeout)
    except (serial.SerialException, OSError, ValueError) as e:
        log("ERROR", f"cannot connect: {e}")
        print(f"ERROR: cannot connect to device: {e}", file=sys.stderr)
        return EXIT_CONNECTION

    try:
        payload = args.command.encode("utf-8", "surrogateescape") + b"\n"
        log("TX", payload)
        port.write(payload)
        raw = port.read_until(b"\n")
    except (serial.SerialException, OSError) as e:
        log("ERROR", f"connection lost: {e}")
        print(f"ERROR: connection lost: {e}", file=sys.stderr)
        return EXIT_CONNECTION
    finally:
        port.close()

    if not raw.endswith(b"\n"):
        log("TIMEOUT", raw)
        print(f"ERROR: no response from device within {args.timeout}s", file=sys.stderr)
        return EXIT_TIMEOUT

    log("RX", raw)
    reply = raw[:-1].decode("ascii", "replace")
    print(reply)
    return EXIT_OK if reply == "OK" or reply.startswith("STATUS ") else EXIT_DEVICE_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
