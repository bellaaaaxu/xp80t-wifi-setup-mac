# XP‑80T Network Printing on macOS

A troubleshooting case study from a retail environment. After a network change, I configured an Xprinter XP‑80T over USB from a MacBook, then verified that it could print and cut a receipt over Wi‑Fi with the USB cable disconnected.

## Results

| Layer | Test | Result |
| --- | --- | --- |
| USB | Identified the device and its bulk interface, then sent Wi‑Fi configuration | Printer self-test reflected the new settings |
| IP | Tested the printer's new static IPv4 address | Ping returned with 0% packet loss in that test |
| TCP | Tested the raw print port with netcat | TCP connection to port 9100 succeeded |
| Printer | Sent a short ESC/POS receipt and cut command with USB unplugged | Physical receipt printed and the cutter operated |

## How I configured and verified Wi‑Fi

1. **Established a local baseline.** macOS detected the printer over USB. I checked the device identifiers and bulk endpoints, then reviewed the vendor's setup materials. A plain-text probe printed on paper, so it did not validate the assumption that the print endpoint would accept a modem-style command.
2. **Applied and verified Wi‑Fi settings.** I used Python, PyUSB, and libusb to send the printer its static IP, subnet mask, gateway, and WPA2 settings. The first self-test showed the saved values and a disconnected router status. After a restart and recheck, the printer responded to ping and accepted a TCP connection on port 9100.
3. **Verified the physical outcome.** I disconnected USB, sent a raw ESC/POS receipt over TCP, and confirmed that the printer produced the receipt and cut the paper. This demonstrated an end-to-end Wi‑Fi print path from the Mac.

## Minimal test on macOS

Run on your own local network after the printer is configured. Enter the printer's actual address when prompted. The commands first test the network path, then send one physical test receipt.

```sh
printf 'Printer IPv4: '
read -r printer_ip
ping -c 4 "$printer_ip"
nc -vz -G 3 "$printer_ip" 9100
printf '\033@XP-80T network test\n\n\n\035V\000' | nc -w 3 "$printer_ip" 9100
```

The print payload starts with ESC/POS initialization and ends with the `GS V 0` cut command. Confirm that the paper actually prints and cuts. [ESC/POS cut command reference](https://download4.epson.biz/sec_pubs/pos/reference_en/escpos/gs_cv.html)

## Tools

- macOS USB device reporting, Python, PyUSB and libusb for USB configuration
- ping and netcat for IP, TCP and raw printing checks

[完整測試紀錄（中文）](docs/test-log.zh-Hant.md)
