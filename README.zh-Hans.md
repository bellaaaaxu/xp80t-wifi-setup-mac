# 用 Mac 修改芯烨 Xprinter XP‑80T 的 Wi‑Fi 设置

[English](README.md) | 简体中文

用 USB 把 XP‑80T 连到 Mac，写入新的 Wi‑Fi 和固定 IP 设置，再通过 Wi‑Fi 打印一张测试小票并切纸，确认设置生效。

| 用途 | 命令 | 说明 |
| --- | --- | --- |
| 修改 Wi‑Fi 和固定 IPv4 | `xp80t setup-wifi` | 适用于与测试机 USB 接口一致的 XP‑80T Wi‑Fi 款 |
| 检查打印端口能不能连上 | `xp80t check 打印机IP` | 不发送任何打印数据 |
| 发送 ESC/POS 测试小票 | `xp80t test-print 打印机IP [--cut]` | 使用原始 TCP，默认端口 9100 |

`check` 和 `test-print` 用的是通用的原始 TCP 和 ESC/POS，其他网络小票打印机可能也能用，但目前只在 XP‑80T 上验证过。

## 从源码安装

需要 Python 3.9 或更高版本。网络相关的命令只用 Python 标准库，不需要 USB 驱动。

```sh
git clone https://github.com/bellaaaaxu/xp80t-wifi-setup-mac.git
cd xp80t-wifi-setup-mac
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
```

Windows 用户在 PowerShell 里把激活那一行换成 `.venv\Scripts\Activate.ps1`。网络命令在 Windows 上用本地模拟打印机测试过。

**哪些在真机上验证过：** 在一台 XP‑80T 上，用 Python 脚本和终端命令完成了 USB 写入 Wi‑Fi 设置、无线打印和自动切纸。打包后的这个命令行工具用模拟打印机和模拟 USB 库测试过。

## 通过 USB 设置 Wi‑Fi（macOS）

先确认你的打印机和测试机一致。用 USB 连上打印机后运行：

```sh
system_profiler SPUSBDataType | grep -B2 -A6 -i '0x5743'
```

看输出里有没有 `Product ID: 0x5743` 和 `Vendor ID: 0x0483`。如果没有，USB 设置会拒绝写入，欢迎把你看到的内容提交到兼容性反馈。

```sh
brew install libusb
python -m pip install '.[usb]'
xp80t setup-wifi
```

用 USB 数据线连接一台 XP‑80T。依次输入网络里空闲的固定 IP、子网掩码、网关，以及 WPA2 Wi‑Fi 的名称和密码，输入密码时不会显示。确认后重启打印机，等 30 到 60 秒，拔掉 USB，再做下面的网络测试。`setup-wifi` 会先检查 PyUSB、libusb 和打印机，都没问题才开始问设置。如果 PyUSB 找不到 libusb，运行：

```sh
XP80T_LIBUSB_PATHS="$(brew --prefix libusb)/lib" xp80t setup-wifi
```

支持：WPA2‑PSK（AES）加固定 IPv4 地址。不支持 DHCP、WPA3 和企业级 Wi‑Fi。测试机的 USB ID 是 `0483:5743`，bulk OUT 端点是 `0x02`，其他硬件或固件版本需要另外验证。写脚本调用的话，可以用 `python src/configure.py` 的 JSON 标准输入输出接口，字段说明见 [USB 模块](src/xp80t_usb.py)。

## 通过网络测试打印机

把示例地址换成打印机在局域网里的 IP。需要时可以加 `--port` 和 `--timeout`。

```sh
xp80t check 192.168.50.200
xp80t test-print 192.168.50.200
xp80t test-print 192.168.50.200 --cut
```

显示 “Sent” 只表示电脑把数据发出去了。请到打印机旁确认小票确实打出来了，加了 `--cut` 的话也确认切了纸。[ESC/POS 切纸指令参考（英文）](https://download4.epson.biz/sec_pubs/pos/reference_en/escpos/gs_cv.html)

## 排查顺序

| 你看到的情况 | 下一步测什么 |
| --- | --- |
| 电脑通过 USB 找不到打印机 | 查 USB 设备列表、数据线（要数据线，不能是只能充电的线）和电源 |
| 自检页已经显示新设置 | 看自检页上的路由器连接状态，再从电脑 ping 打印机 IP |
| 重启后自检页显示 `Disconnect` | 重新核对 Wi‑Fi 名称和密码，确认网络是 WPA2。只有 5 GHz 的网络没有测试过 |
| 能 ping 通 | 运行 `xp80t check 打印机IP` |
| `check` 成功 | 拔掉 USB，运行 `xp80t test-print 打印机IP --cut`，确认出纸和切纸 |

## 实测记录

换网络之后，我用 Mac 通过 USB 设置了这台 XP‑80T，重启后确认 TCP 9100 端口可以连接。拔掉 USB 后，打印机通过 Wi‑Fi 打出了 ESC/POS 小票并自动切纸。[完整测试记录](docs/test-log.zh-Hans.md)

## 反馈与贡献

欢迎反馈。如果你在自己的打印机上试了，请[提交 issue](../../issues/new/choose)，写上系统版本、打印机型号和固件版本（如果知道）、运行的命令，以及打印机有没有连上、打印、切纸。Wi‑Fi 信息和地址请用示例值代替。修改代码的话，请在仓库根目录运行 `python -m unittest discover -s tests`。

[MIT 许可证](LICENSE)
