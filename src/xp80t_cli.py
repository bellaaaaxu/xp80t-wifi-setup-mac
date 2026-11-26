"""Command-line setup and diagnostics for the Xprinter XP-80T."""

import argparse
import getpass
import math
import socket
import sys

from xp80t_usb import check_usb, send_usb, wifi_command


TEST_PAGE = b"\x1b@XP-80T network test\nTCP / ESC-POS\n\n\n"
FULL_CUT = b"\x1dV\x00"


def print_or_check(host, port, timeout, payload=None):
    with socket.create_connection((host, port), timeout=timeout) as connection:
        if payload is not None:
            connection.sendall(payload)


def port_number(value):
    port = int(value)
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def timeout_seconds(value):
    timeout = float(value)
    if not math.isfinite(timeout) or not 0 < timeout <= 60:
        raise argparse.ArgumentTypeError("timeout must be greater than 0 and at most 60 seconds")
    return timeout


def setup_xp80t():
    if not sys.stdin.isatty():
        print("Run setup-wifi in a terminal. For automation, use the USB helper's JSON interface.", file=sys.stderr)
        return 2

    # Check PyUSB, libusb and the printer first, so nobody types settings that cannot be written.
    status, message = check_usb()
    if status != "ok":
        print(message, file=sys.stderr)
        return 1
    print(message)

    try:
        settings = {
            "ip": input("Printer IPv4 address: ").strip(),
            "mask": input("Subnet mask [255.255.255.0]: ").strip() or "255.255.255.0",
            "gateway": input("Gateway IPv4 address: ").strip(),
            "ssid": input("Wi-Fi name: "),
            "password": getpass.getpass("Wi-Fi password: "),
        }
        packet = wifi_command(settings)
        print(f"Target: one XP-80T (0483:5743) over USB, new address {settings['ip']}.")
        if input("Write the settings? [y/N] ").strip().lower() not in {"y", "yes"}:
            print("Cancelled.")
            return 1
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.", file=sys.stderr)
        return 1
    except ValueError as error:
        print(f"Invalid settings: {error}", file=sys.stderr)
        return 2

    status, message = send_usb(packet)
    print(message, file=sys.stdout if status == "ok" else sys.stderr)
    return 0 if status == "ok" else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="Set up or test an Xprinter XP-80T.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("check", "Test the printer's raw TCP port without sending print data."),
        ("test-print", "Send one fixed ESC/POS test receipt."),
    ):
        command = commands.add_parser(name, help=help_text, description=help_text)
        command.add_argument("host", help="Printer IP address or hostname")
        command.add_argument("--port", type=port_number, default=9100)
        command.add_argument("--timeout", type=timeout_seconds, default=5, metavar="SECONDS")
        if name == "test-print":
            command.add_argument("--cut", action="store_true", help="Request a full cut after printing")
    commands.add_parser("setup-wifi", help="Write static IPv4 and WPA2 settings to an XP-80T over USB.")

    args = parser.parse_args(argv)
    if args.command == "setup-wifi":
        return setup_xp80t()

    target = f"[{args.host}]:{args.port}" if ":" in args.host else f"{args.host}:{args.port}"
    payload = None
    if args.command == "test-print":
        payload = TEST_PAGE + (FULL_CUT if args.cut else b"")

    try:
        print_or_check(args.host, args.port, args.timeout, payload)
    except OSError as error:
        print(f"{target}: {error}", file=sys.stderr)
        return 1

    if payload is None:
        print(f"TCP connection successful: {target}")
    else:
        print(f"Test data sent to {target}. Check that the printer produced a receipt.")
        if args.cut:
            print("Full-cut command sent. Check that the cutter operated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
