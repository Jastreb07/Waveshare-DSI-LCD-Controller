# Waveshare DSI LCD Controller (Raspberry Pi 5 / CM5)

Utility to turn off (dim to brightness=0) a DSI backlight after user inactivity and wake it on input (touch / keyboard / mouse). Includes a simple Tk GUI for configuring idle timeout, hotplug rescan interval, forced max brightness on wake, and debug logging.

## Features
- Auto-detects first backlight under `/sys/class/backlight/*` (override via config)
- Monitors touch, keyboard and mouse event devices (evdev)
- Hotplug support: rescans `/dev/input/event*` periodically
- Writes brightness and (if present) `bl_power` to save power
- Optional: force max brightness on every wake
- Idle timeout configurable via GUI or config file
- Runs as a systemd service under the invoking (non-root) user
- GUI can update config and restart service without password (sudoers rule)

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
4. Create a systemd service `touch-wake-display.service` running as your user.
5. Add a sudoers rule allowing password-less `systemctl restart touch-wake-display.service`.
6. Add a desktop launcher (Menu → Accessories → Touch Wake Settings).
7. Add a udev rule to grant group `video` write access to the brightness file.

After installation, log out and back in (or reboot) so your user group changes (`video`, `input`) apply.

## Configuration
Main file: `/etc/touch-wake-display.conf`
```
[touchwake]
idle_seconds = 30
bl_base =
force_max_on_wake = true
rescan_interval = 2.0
debug = false
```
Fields:
- `idle_seconds`: Inactivity threshold before brightness is set to 0.
- `bl_base`: Explicit backlight path (leave empty for auto-detect).
- `force_max_on_wake`: If true, always set brightness to max when waking.
- `rescan_interval`: Seconds between rescans for new/removed input devices.
- `debug`: Verbose logging to the journal when true.

## GUI Usage
Launch: Menu → Accessories → Touch Wake Settings (or run `python3 /opt/waveshare-dsi-lcd-controller/touch-wake-settings.py`).
Adjust desired values, click "Save & restart service". The GUI writes the config and restarts the systemd service.

If restart fails, verify sudoers rule:
```
cat /etc/sudoers.d/touchwake
# Expect: <user> ALL=NOPASSWD: /usr/bin/systemctl restart touch-wake-display.service
```

## Service Management
```bash
systemctl status touch-wake-display.service
systemctl restart touch-wake-display.service
journalctl -u touch-wake-display.service -f
```

## Uninstall
```bash
sudo bash uninstall.sh
```
The config file is preserved (remove manually if desired).

## Troubleshooting
- No brightness change: Ensure user is in `video` and brightness file has group write (`ls -l /sys/class/backlight/*/brightness`).
- No wake on input: Confirm membership in `input` group and that matching `/dev/input/event*` devices appear in logs.
- Wrong backlight chosen: Set explicit `bl_base` in config and restart.
- Service fails early: Check for `Missing evdev?` → install `python3-evdev`.

## License
MIT (implicit unless otherwise noted). Replace/update if you add a LICENSE file.

---
All code, comments, and documentation must be in English (repository policy).
