import json
from pathlib import Path
import socket
import subprocess
import sys
import unittest


SRC = Path(__file__).resolve().parents[1] / "src"


def run_script(script, *args, stdin=None):
    return subprocess.run(
        [sys.executable, str(SRC / script), *args],
        input=stdin, capture_output=True, text=True, timeout=8,
    )


class NetworkCommandTests(unittest.TestCase):
    def received_bytes(self, command, *args):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            listener.settimeout(2)
            port = str(listener.getsockname()[1])
            result = run_script("xp80t_cli.py", command, "127.0.0.1", "--port", port, *args)
            self.assertEqual(result.returncode, 0, result.stderr)
            peer, _ = listener.accept()
            with peer, peer.makefile("rb") as stream:
                peer.settimeout(2)
                return stream.read()

    def test_check_sends_no_data(self):
        self.assertEqual(self.received_bytes("check"), b"")

    def test_print_includes_cutter_bytes_only_when_requested(self):
        test_page = b"\x1b@XP-80T network test\nTCP / ESC-POS\n\n\n"
        self.assertEqual(self.received_bytes("test-print"), test_page)
        self.assertEqual(self.received_bytes("test-print", "--cut"), test_page + b"\x1dV\0")

    def test_invalid_timeout_returns_usage_error(self):
        result = run_script("xp80t_cli.py", "check", "127.0.0.1", "--timeout", "nan")
        self.assertEqual(result.returncode, 2)
        self.assertIn("timeout must be", result.stderr)


class UsbCompatibilityTests(unittest.TestCase):
    def test_bad_input_keeps_json_status_contract(self):
        settings = dict(ip="192.168.50.200", mask="255.255.255.0",
                        gateway="192.168.50.1", ssid="Example", password="example-pass")
        for field in ("ssid", "password"):
            with self.subTest(field=field):
                result = run_script("configure.py", stdin=json.dumps({**settings, field: None}))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["status"], "error")
                self.assertNotIn(settings["password"], result.stdout + result.stderr)
