"""setup-wifi must check PyUSB, libusb and the printer before asking for any settings."""

import builtins
import contextlib
import io
from pathlib import Path
import sys
import types
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import xp80t_cli  # noqa: E402
import xp80t_usb  # noqa: E402


def fake_usb(printers=(), backend=object()):
    """Build a stand-in for the pyusb package that reports the given devices."""
    usb = types.ModuleType("usb")
    core = types.ModuleType("usb.core")
    util = types.ModuleType("usb.util")
    backend_pkg = types.ModuleType("usb.backend")
    libusb1 = types.ModuleType("usb.backend.libusb1")
    core.USBError = type("USBError", (Exception,), {})
    core.NoBackendError = type("NoBackendError", (Exception,), {})
    core.find = lambda **kwargs: list(printers)
    util.disposed = []
    util.dispose_resources = util.disposed.append
    libusb1.get_backend = lambda **kwargs: backend
    usb.core, usb.util, usb.backend, backend_pkg.libusb1 = core, util, backend_pkg, libusb1
    return {"usb": usb, "usb.core": core, "usb.util": util,
            "usb.backend": backend_pkg, "usb.backend.libusb1": libusb1}


class PreflightTests(unittest.TestCase):
    def run_setup(self, modules):
        asked = []
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(sys.modules, modules), \
                mock.patch.object(sys.stdin, "isatty", return_value=True), \
                mock.patch.object(builtins, "input", side_effect=lambda prompt="": asked.append(prompt) or (_ for _ in ()).throw(EOFError)), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = xp80t_cli.setup_xp80t()
        return code, asked, out.getvalue() + err.getvalue()

    def test_missing_pyusb_stops_before_any_prompt(self):
        code, asked, text = self.run_setup({"usb": None, "usb.core": None, "usb.backend": None, "usb.backend.libusb1": None})
        self.assertEqual((code, asked), (1, []))
        self.assertIn("pip install", text)

    def test_missing_libusb_stops_before_any_prompt(self):
        code, asked, text = self.run_setup(fake_usb(backend=None))
        self.assertEqual((code, asked), (1, []))
        self.assertIn("brew install libusb", text)

    def test_no_printer_stops_before_any_prompt(self):
        code, asked, text = self.run_setup(fake_usb(printers=[]))
        self.assertEqual((code, asked), (1, []))
        self.assertIn("not found", text)

    def test_two_printers_stop_before_any_prompt(self):
        code, asked, text = self.run_setup(fake_usb(printers=[object(), object()]))
        self.assertEqual((code, asked), (1, []))
        self.assertIn("More than one", text)

    def test_one_printer_goes_on_to_the_prompts(self):
        modules = fake_usb(printers=[object()])
        code, asked, text = self.run_setup(modules)
        self.assertEqual(asked, ["Printer IPv4 address: "])
        self.assertEqual(code, 1)  # the fake input ends with EOF, which cancels
        self.assertIn("Found one XP-80T", text)
        self.assertEqual(len(modules["usb.util"].disposed), 1)  # the check releases the device

    def test_check_writes_nothing(self):
        printer = mock.Mock()
        with mock.patch.dict(sys.modules, fake_usb(printers=[printer])):
            self.assertEqual(xp80t_usb.check_usb()[0], "ok")
        printer.write.assert_not_called()


    def test_send_still_writes_the_packet_to_bulk_out_0x02(self):
        modules = fake_usb(printers=[])
        util = modules["usb.util"]
        endpoint = types.SimpleNamespace(bmAttributes=2)
        util.ENDPOINT_TYPE_BULK = 2
        util.endpoint_type = lambda attributes: attributes
        util.find_descriptor = lambda interface, bEndpointAddress: endpoint if bEndpointAddress == 0x02 else None
        util.claimed = []
        util.claim_interface = lambda device, number: util.claimed.append(number)
        printer = mock.Mock()
        printer.get_active_configuration.return_value = {(0, 0): "interface"}
        packet = xp80t_usb.wifi_command(dict(ip="192.168.50.200", mask="255.255.255.0", gateway="192.168.50.1",
                                             ssid="Example", password="example-pass"))
        printer.write.return_value = len(packet)
        modules["usb.core"].find = lambda **kwargs: [printer]
        with mock.patch.dict(sys.modules, modules):
            self.assertEqual(xp80t_usb.send_usb(packet)[0], "ok")
        printer.write.assert_called_once_with(0x02, packet, timeout=5000)
        self.assertEqual(util.claimed, [0])
        self.assertEqual(util.disposed, [printer])


if __name__ == "__main__":
    unittest.main()
