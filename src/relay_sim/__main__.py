"""Run the simulator:
relay-sim [--host H] [--port 5000] [--control-port 5001] [--clock real|manual] [--log FILE]
"""
import argparse
import sys
import time

from .clock import ManualClock, RealClock
from .device import RelayDevice
from .server import set_log_file, start_servers


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="relay-sim", description="Smart relay simulator (serial-over-TCP)")
    p.add_argument("--host", default="localhost", help="bind address; localhost = 127.0.0.1 and ::1")
    p.add_argument("--port", type=int, default=5000, help="serial port (TCP); 0 = pick a free port")
    p.add_argument("--control-port", type=int, default=5001, help="control API port; 0 = pick a free port")
    p.add_argument("--clock", choices=["real", "manual"], default="real")
    p.add_argument("--log", metavar="FILE", help="write the exchange log to FILE instead of stderr")
    args = p.parse_args(argv)

    if args.log:
        set_log_file(args.log)
    device = RelayDevice(ManualClock() if args.clock == "manual" else RealClock())
    try:
        serial_port, control_port, servers = start_servers(device, args.host, args.port, args.control_port)
    except OSError as e:
        print(f"ERROR: cannot open port: {e}", file=sys.stderr)
        return 1
    print(f"READY serial={serial_port} control={control_port}", flush=True)

    try:
        while True:  # servers run in their own threads; short sleeps keep Ctrl+C responsive on Windows
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for srv in servers:
            srv.shutdown()
            srv.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
