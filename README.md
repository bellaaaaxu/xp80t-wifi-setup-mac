# Change Xprinter XP‑80T Wi‑Fi Settings from a Mac

用 Mac 修改 Xprinter XP‑80T 的 Wi‑Fi 設定

Connect an Xprinter XP‑80T to a Mac by USB, write new Wi‑Fi and static IP settings, then confirm over Wi‑Fi that it prints and cuts a test receipt.

| Use case | Command | Notes |
| --- | --- | --- |
| Change Wi‑Fi and static IPv4 settings | `xp80t setup-wifi` | XP‑80T Wi‑Fi variant matching the tested USB interface |
| Check whether the print port is reachable | `xp80t check HOST` | Sends no print data |
| Send an ESC/POS test receipt | `xp80t test-print HOST [--cut]` | Uses raw TCP, port 9100 by default |

`check` and `test-print` use standard raw TCP and ESC/POS, so they may also work with other network receipt printers. They have only been verified on the XP‑80T.

## Install from source

Requires Python 3.9 or newer. The network commands use only the Python standard library and need no USB driver.

```sh
git clone https://github.com/bellaaaaxu/xp80t-wifi-setup-mac.git
cd xp80t-wifi-setup-mac
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
```

On Windows, run `.venv\Scripts\Activate.ps1` in PowerShell in place of the activation line. The network commands use cross-platform Python sockets and were tested on Windows with a local simulated printer. The USB setup was verified on macOS with one XP‑80T.

## Set up Wi‑Fi over USB (macOS)

First check that your printer matches the tested unit. With the printer connected by USB, run:

```sh
system_profiler SPUSBDataType | grep -B2 -A6 -i '0x5743'
```

Look for `Product ID: 0x5743` and `Vendor ID: 0x0483`. If nothing matches, the USB setup will refuse to write; please open a compatibility report with what you see.

```sh
brew install libusb
python -m pip install '.[usb]'
xp80t setup-wifi
```

Connect one XP‑80T via a USB data cable. Enter a static IP that is free on your network, the subnet mask, gateway, and WPA2 Wi‑Fi details. The password prompt hides your input. Confirm, then restart the printer and wait 30–60 seconds. Unplug USB and run the network tests below. If PyUSB cannot find libusb, run the setup with `XP80T_LIBUSB_PATHS="$(brew --prefix libusb)/lib"`.

Supported: WPA2‑PSK (AES) with a static IPv4 address. DHCP, WPA3 and enterprise Wi‑Fi are not supported. The tested unit had USB ID `0483:5743` and bulk OUT endpoint `0x02`; other hardware and firmware variants need separate verification. For scripts, a JSON stdin/stdout interface is available at `python src/configure.py`; the [USB module](src/xp80t_usb.py) documents its fields.

## Test the printer over the network

Replace the example address with the printer's LAN IP. Use `--port` and `--timeout` when needed.

```sh
xp80t check 192.168.50.200
xp80t test-print 192.168.50.200
xp80t test-print 192.168.50.200 --cut
```

"Sent" means the computer delivered the data. Confirm at the printer that the receipt printed and, with `--cut`, that the cutter operated. [ESC/POS cut command reference](https://download4.epson.biz/sec_pubs/pos/reference_en/escpos/gs_cv.html)

## Troubleshooting order

| What you see | Next test |
| --- | --- |
| The computer does not see the printer over USB | Check the USB device list, cable (data, not charge‑only) and power |
| The self‑test page shows the new settings | Check its router status, then ping the printer's IP from the computer |
| Self‑test shows `Disconnect` after a restart | Recheck the Wi‑Fi name and password, and that the network uses WPA2. 5 GHz‑only networks have not been tested |
| Ping works | Run `xp80t check` |
| `check` succeeds | Unplug USB, run `xp80t test-print --cut`, confirm paper and cut |

## Field test

After a network change, I configured the XP‑80T over USB from a Mac, restarted it, and verified TCP port 9100. With USB unplugged, the printer produced an ESC/POS receipt over Wi‑Fi and cut it automatically. [完整測試紀錄（中文）](docs/test-log.zh-Hant.md)

## Feedback and contributions

Feedback is welcome. If you try this on your own printer, please [open an issue](../../issues/new/choose) with your OS, printer model and firmware if known, the command you ran, and whether the printer connected, printed and cut. Use example values for Wi‑Fi settings and addresses. For code changes, run `python -m unittest discover -s tests` from the repo root.

[MIT License](LICENSE)
