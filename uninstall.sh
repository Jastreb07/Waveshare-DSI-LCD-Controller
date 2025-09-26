#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/waveshare-dsi-lcd-controller"
SERVICE_NAME="touch-wake-display.service"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME"
DESKTOP_FILE="/usr/share/applications/touch-wake-settings.desktop"
CONF="/etc/touch-wake-display.conf"
UDEV_RULE="/etc/udev/rules.d/99-backlight-perm.rules"

echo ">> Stopping & disabling service …"
systemctl disable --now "$SERVICE_NAME" || true

echo ">> Removing files …"
rm -f "$SERVICE_FILE" "$DESKTOP_FILE" "$UDEV_RULE"
# Config intentionally NOT removed – if you really want to:
# rm -f "$CONF"
rm -rf "$APP_DIR"

echo ">> Reloading systemd/udev …"
systemctl daemon-reload
udevadm control --reload-rules || true

echo ">> Uninstall finished."
