"""Run the simulator: python -m relay_sim [--port 5000] [--control-port 5001] [--clock real|manual]."""
import argparse
import threading

from .clock import ManualClock, RealClock
from .device import RelayDevice
from .server import start_servers


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="relay-sim", description="Smart relay simulator (serial-over-TCP)")
    p.add_argument("--host", default="localhost", help="bind address; localhost = 127.0.0.1 and ::1")
    p.add_argument("--port", type=int, default=5000, help="serial port (TCP); 0 = pick a free port")
    p.add_argument("--control-port", type=int, default=5001, help="control API port; 0 = pick a free port")
    p.add_argument("--clock", choices=["real", "manual"], default="real")
    args = p.parse_args(argv)

    device = RelayDevice(ManualClock() if args.clock == "manual" else RealClock())
    serial_port, control_port, servers = start_servers(device, args.host, args.port, args.control_port)
    print(f"READY serial={serial_port} control={control_port}", flush=True)

    stop = threading.Event()
    try:
        while not stop.wait(0.5):  # short waits keep Ctrl+C responsive on Windows
            pass
    except KeyboardInterrupt:
        pass
    finally:
        for srv in servers:
            srv.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
