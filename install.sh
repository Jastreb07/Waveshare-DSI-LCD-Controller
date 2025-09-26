#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="/opt/waveshare-dsi-lcd-controller"
CONF="/etc/touch-wake-display.conf"
ICON_SRC="$REPO_DIR/icons/touch-wake-settings.png"
ICON_PIX="/usr/share/pixmaps/touch-wake-settings.png"
SERVICE_NAME="touch-wake-display.service"
SERVICE_TMPL="$REPO_DIR/systemd/touch-wake-display.service.in"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME"
DESKTOP_FILE_SRC="$REPO_DIR/desktop/touch-wake-settings.desktop"
DESKTOP_FILE_DST="/usr/share/applications/touch-wake-settings.desktop"

# Ermittel den Ziel-User (der gerade installiert) – nicht root
TARGET_USER="${SUDO_USER:-${USER}}"
TARGET_GROUP="$(id -gn "$TARGET_USER")"

echo ">> Installiere Pakete (python3, evdev, tkinter, policykit-1)…"
apt-get update -y
apt-get install -y python3 python3-evdev python3-tk policykit-1

echo ">> Kopiere Dateien nach $APP_DIR …"
mkdir -p "$APP_DIR"
install -m 0755 "$REPO_DIR/daemon/touch-wake-display.py" "$APP_DIR/touch-wake-display.py"
install -m 0755 "$REPO_DIR/gui/touch-wake-settings.py" "$APP_DIR/touch-wake-settings.py"

echo ">> Config anlegen (falls fehlt): $CONF"
if [ ! -f "$CONF" ]; then
  install -m 0644 "$REPO_DIR/config/touch-wake-display.conf" "$CONF"
fi

echo ">> Service-Datei erzeugen für User: $TARGET_USER"
# Service aus Template bauen
sed \
  -e "s|@@APP_DIR@@|$APP_DIR|g" \
  -e "s|@@USER@@|$TARGET_USER|g" \
  -e "s|@@GROUP@@|$TARGET_GROUP|g" \
  "$SERVICE_TMPL" > "$SERVICE_FILE"

echo ">> Menüeintrag installieren …"
install -m 0644 "$DESKTOP_FILE_SRC" "$DESKTOP_FILE_DST"

echo ">> Icon installieren …"
ICON_SRC="$REPO_DIR/icons/touch-wake-settings.png"
ICON_DST="/usr/share/pixmaps/touch-wake-settings.png"
if [ -f "$ICON_SRC" ]; then
  install -m 0644 "$ICON_SRC" "$ICON_DST"
else
  echo "WARN: Icon nicht gefunden: $ICON_SRC"
fi

echo ">> Gruppenrechte setzen (video,input) für $TARGET_USER"
usermod -aG video,input "$TARGET_USER" || true

echo ">> Udev-Regel (Backlight-Schreiben für Gruppe video) …"
cat >/etc/udev/rules.d/99-backlight-perm.rules <<'RULE'
SUBSYSTEM=="backlight", RUN+="/bin/chgrp video /sys/class/backlight/%k/brightness", RUN+="/bin/chmod g+w /sys/class/backlight/%k/brightness"
RULE
udevadm control --reload-rules || true

echo ">> systemd neu laden & Service aktivieren …"
systemctl daemon-reload
systemctl enable --now "$SERVICE_NAME"

echo ">> FERTIG. Einstellungen öffnen über:"
echo "   Start → Accessories → Touch Wake Settings"
echo "   oder:  pkexec /usr/bin/python3 $APP_DIR/touch-wake-settings.py"
