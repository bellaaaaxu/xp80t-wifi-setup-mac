"""Send static IPv4 and WPA2 Wi-Fi settings to an Xprinter XP-80T over USB.

Reads one JSON object from stdin:
    {"ip": "...", "mask": "...", "gateway": "...", "ssid": "...", "password": "..."}
Prints one JSON object to stdout:
    {"status": "ok" | "error" | "missing-pyusb" | "no-libusb", "message": "..."}

Requires Python 3, PyUSB and libusb. Tested with one XP-80T (USB ID 0483:5743).
"""

import ipaddress
import json
import os
from pathlib import Path
import sys


class SettingsError(ValueError):
    """Invalid settings; the message is safe to show to the user."""


def wifi_command(settings):
    ip = ipaddress.IPv4Address(settings["ip"])
    gateway = ipaddress.IPv4Address(settings["gateway"])
    network = ipaddress.IPv4Network(f"{ip}/{settings['mask']}", strict=False)
    if str(network.netmask) != settings["mask"] or network.prefixlen > 30:
        raise SettingsError("Enter a valid subnet mask, for example 255.255.255.0.")
    reserved = {network.network_address, network.broadcast_address}
    for address in (ip, gateway):
        if (address not in network or address in reserved or address.is_multicast
                or address.is_loopback or address.is_unspecified):
            raise SettingsError("The printer IP and gateway must be valid host addresses on the same subnet.")
    if ip == gateway:
        raise SettingsError("The printer IP cannot be the same as the gateway.")
    ssid = settings["ssid"].encode("utf-8")
    password = settings["password"].encode("ascii", errors="replace")
    if not 1 <= len(ssid) <= 32 or any(byte < 32 or byte == 127 for byte in ssid):
        raise SettingsError("The Wi-Fi name must be 1-32 UTF-8 bytes with no control characters.")
    if (not settings["password"].isascii() or not 8 <= len(password) <= 63
            or any(byte < 32 or byte > 126 for byte in password)):
        raise SettingsError("The WPA2 password must be 8-63 printable ASCII characters.")
    # Packet layout: header, IP, mask, gateway, security mode (0x06 = WPA2-PSK/AES),
    # then SSID and password, each NUL-terminated.
    return (
        bytes.fromhex("1f 1b 1f b4") + ip.packed + network.netmask.packed
        + gateway.packed + b"\x06" + ssid + b"\x00" + password + b"\x00"
    )


def send_usb(command):
    try:
        import usb.backend.libusb1
        import usb.core
        import usb.util
    except ImportError:
        return "missing-pyusb", "PyUSB is not installed in this Python environment."
    no_libusb = "libusb was not found. Check that libusb is installed."
    try:
        backend = usb.backend.libusb1.get_backend()
        if backend is None:
            # Optional fallback: directories to search for libusb-1.0.dylib.
            for directory in os.environ.get("XP80T_LIBUSB_PATHS", "").split(os.pathsep):
                if not directory:
                    continue
                dylib = Path(directory) / "libusb-1.0.dylib"
                if dylib.is_file():
                    backend = usb.backend.libusb1.get_backend(find_library=lambda _name: str(dylib))
                if backend is not None:
                    break
        if backend is None:
            return "no-libusb", no_libusb
        printers = list(usb.core.find(find_all=True, idVendor=0x0483, idProduct=0x5743, backend=backend))
    except usb.core.NoBackendError:
        return "no-libusb", no_libusb
    except usb.core.USBError:
        return "error", "Could not read USB devices. Reconnect the USB cable and try again."
    if len(printers) != 1:
        return "error", ("XP-80T (0483:5743) not found. Check that it is powered on and connected with a USB data cable."
                         if not printers else "More than one matching device found. Connect only the printer you want to configure.")
    printer = printers[0]
    try:
        try:
            configuration = printer.get_active_configuration()
        except usb.core.USBError:
            printer.set_configuration()
            configuration = printer.get_active_configuration()
        interface = configuration[(0, 0)]
        endpoint = usb.util.find_descriptor(interface, bEndpointAddress=0x02)
        if endpoint is None or usb.util.endpoint_type(endpoint.bmAttributes) != usb.util.ENDPOINT_TYPE_BULK:
            return "error", "USB device found, but its print endpoint does not match the tested XP-80T."
        usb.util.claim_interface(printer, 0)
        if printer.write(0x02, command, timeout=5000) != len(command):
            return "error", "The command was only partly sent. Check the printer before deciding whether to retry."
    except (usb.core.USBError, KeyError, ValueError):
        return "error", "USB send failed. Close other printing or setup tools, check the cable and try again."
    finally:
        try:
            usb.util.dispose_resources(printer)
        except usb.core.USBError:
            pass
    return "ok", "Settings sent. Restart the printer, wait 30-60 seconds, then test the new IP."


def main():
    try:
        command = wifi_command(json.load(sys.stdin))
    except SettingsError as error:
        result = "error", str(error)
    except (ValueError, TypeError, KeyError):
        result = "error", "Check the IP address, subnet mask, gateway and Wi-Fi settings."
    else:
        result = send_usb(command)
    print(json.dumps(dict(zip(("status", "message"), result)), ensure_ascii=True))


if __name__ == "__main__":
    main()
