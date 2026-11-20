"""relay-host [--host H] [--port P] [--timeout S] COMMAND

Sends COMMAND (UTF-8) + \\n verbatim over pyserial socket://, prints the reply line.
Exit codes: 0 OK/STATUS, 1 any other reply, 2 connection or usage error, 3 no response within timeout.
If RELAY_HOST_LOG is set, appends a timestamped exchange log to that file (failures are ignored).
"""
import argparse
import os
import socket
import sys
from datetime import datetime

import serial
from serial.urlhandler.protocol_socket import Serial as SocketSerial

EXIT_OK, EXIT_DEVICE_ERROR, EXIT_TIMEOUT = 0, 1, 3
EXIT_CONNECTION = EXIT_USAGE = 2


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
    """Best-effort test log: a logging failure never changes the host's output or exit code."""

    def __init__(self, path: str | None) -> None:
        self.path = path

    def __call__(self, direction: str, payload: object) -> None:
        if not self.path:
            return
        ts = datetime.now().isoformat(timespec="milliseconds")
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(f"{ts} HOST {direction} {payload!r}\n")
        except OSError:
            pass


class _Parser(argparse.ArgumentParser):
    def error(self, message: str):
        """Usage error (requirements section 4 exception): usage line + one ERROR line, exit 2."""
        self.print_usage(sys.stderr)
        self.exit(EXIT_USAGE, f"ERROR: {message}\n")


def _port(value: str) -> int:
    port = int(value)
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError(f"port must be 1-65535, got {value}")
    return port


def _timeout(value: str) -> float:
    seconds = float(value)
    if not seconds > 0 or seconds == float("inf"):
        raise argparse.ArgumentTypeError(f"timeout must be a positive number of seconds, got {value}")
    return seconds


def main(argv: list[str] | None = None) -> int:
    p = _Parser(prog="relay-host", description="Send one command to the smart relay simulator")
    p.add_argument("--host", default="localhost", help="device host name or IP address (IPv6 allowed)")
    p.add_argument("--port", type=_port, default=5000)
    p.add_argument("--timeout", type=_timeout, default=1.0, help="seconds to wait for the reply")
    p.add_argument("command", help='command line to send verbatim, e.g. ON, OFF, STATUS ("" = empty line)')
    args = p.parse_args(argv)
    log = _ExchangeLog(os.environ.get("RELAY_HOST_LOG"))

    host = f"[{args.host}]" if ":" in args.host and not args.host.startswith("[") else args.host
    url = f"socket://{host}:{args.port}"
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
