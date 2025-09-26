#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/waveshare-dsi-lcd-controller"
SERVICE_NAME="touch-wake-display.service"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME"
DESKTOP_FILE="/usr/share/applications/touch-wake-settings.desktop"
CONF="/etc/touch-wake-display.conf"
UDEV_RULE="/etc/udev/rules.d/99-backlight-perm.rules"

echo ">> Stoppe & deaktiviere Service …"
systemctl disable --now "$SERVICE_NAME" || true

echo ">> Entferne Dateien …"
rm -f "$SERVICE_FILE" "$DESKTOP_FILE" "$UDEV_RULE"
# Config absichtlich NICHT löschen – falls doch gewünscht:
# rm -f "$CONF"
rm -rf "$APP_DIR"

echo ">> systemd/udev neu laden …"
systemctl daemon-reload
udevadm control --reload-rules || true

echo ">> Deinstallation abgeschlossen."
