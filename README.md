# Waveshare DSI LCD Controller (Raspberry Pi 5 / CM5)

Utility to turn off (dim to brightness=0) a DSI backlight after user inactivity and wake it on input (touch / keyboard / mouse). Provides a minimal Tk GUI to adjust idle timeout, backlight path and current brightness; optionally force maximum brightness on wake.

## Features
- Auto-detects first backlight under `/sys/class/backlight/*` (override via config)
- Monitors touch / keyboard / mouse via evdev (hotplug rescanning in daemon)
- Dims to 0 after configurable idle timeout
- Restores last user brightness on wake (default) OR forces max if enabled
- Optional: force max brightness on every wake (disabled by default)
- Backlight power (`bl_power`) toggled where supported
- Runs as non-root systemd service (user-level execution)
- GUI writes config and restarts service via password-less sudo rule
- Direct brightness slider (0% maps to safe minimum raw value, daemon sleep still reaches true 0)

## Installation
```bash
git clone https://github.com/Jastreb07/Waveshare-DSI-LCD-Controller.git
cd Waveshare-DSI-LCD-Controller
sudo bash install.sh
```
This will:
1. Install required packages (`python3`, `python3-evdev`, `python3-tk`, `policykit-1`).
2. Copy daemon + GUI to `/opt/waveshare-dsi-lcd-controller/`.
3. Install a config at `/etc/touch-wake-display.conf` (owned by your user).
4. Create and enable `touch-wake-display.service` (runs as your user).
5. Add sudoers rule for password-less service restart.
6. Install desktop launcher & icon.
7. Add udev rule giving group `video` write access to brightness.

After installation log out/in (or reboot) so new `video` and `input` group membership becomes active.

## Uninstall
```bash
sudo bash uninstall.sh
```
Config is preserved (delete manually if unwanted).
## GUI Usage
Menu → Accessories → Touch Wake Settings (or run: `python3 /opt/waveshare-dsi-lcd-controller/touch-wake-settings.py`).
Elements:
- Idle (seconds)
- Backlight path (empty → auto)
- Brightness slider (%). 0% corresponds to a minimal raw value (not full off). The daemon sets true 0 only when sleeping.
- Force max brightness on every wake (checkbox)

Click “Save & restart service” to apply.

## License (MIT)
This project is released under the MIT License — a permissive license allowing reuse in proprietary and open-source projects.

Copyright (c) 2025 Waveshare DSI LCD Controller Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

---
Contributions welcome. Submit PRs or open issues for enhancements.
