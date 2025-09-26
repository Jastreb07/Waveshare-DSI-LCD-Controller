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

# Determine target user (invoking user) – not root
TARGET_USER="${SUDO_USER:-${USER}}"
TARGET_GROUP="$(id -gn "$TARGET_USER")"

echo ">> Installing packages (python3, evdev, tkinter, policykit-1)…"
apt-get update -y
apt-get install -y python3 python3-evdev python3-tk policykit-1

echo ">> Copying application files to $APP_DIR …"
mkdir -p "$APP_DIR"
install -m 0755 "$REPO_DIR/daemon/touch-wake-display.py" "$APP_DIR/touch-wake-display.py"
install -m 0755 "$REPO_DIR/gui/touch-wake-settings.py" "$APP_DIR/touch-wake-settings.py"

echo ">> Ensuring config file exists: $CONF"
if [ ! -f "$CONF" ]; then
  install -m 0644 "$REPO_DIR/config/touch-wake-display.conf" "$CONF"
  # Make the user owner so GUI can save without pkexec
  chown "$TARGET_USER:$TARGET_GROUP" "$CONF"
else
  OWNER="$(stat -c %U "$CONF" 2>/dev/null || echo root)"
  if [ "$OWNER" != "$TARGET_USER" ]; then
    echo "   Changing owner of $CONF to $TARGET_USER:$TARGET_GROUP (before: $OWNER)"
    chown "$TARGET_USER:$TARGET_GROUP" "$CONF" || echo "WARN: chown failed"
  fi
fi

# Ensure readable by user/group
chmod 0644 "$CONF" || true

echo ">> Generating service file for user: $TARGET_USER"
# Build service from template
sed \
  -e "s|@@APP_DIR@@|$APP_DIR|g" \
  -e "s|@@USER@@|$TARGET_USER|g" \
  -e "s|@@GROUP@@|$TARGET_GROUP|g" \
  "$SERVICE_TMPL" > "$SERVICE_FILE"

echo ">> Installing desktop entry …"
install -m 0644 "$DESKTOP_FILE_SRC" "$DESKTOP_FILE_DST"

echo ">> Installing icon …"
ICON_SRC="$REPO_DIR/icons/touch-wake-settings.png"
ICON_DST="/usr/share/pixmaps/touch-wake-settings.png"
if [ -f "$ICON_SRC" ]; then
  install -m 0644 "$ICON_SRC" "$ICON_DST"
else
  echo "WARN: Icon not found: $ICON_SRC"
fi

echo ">> Adding user $TARGET_USER to groups video,input (if not already) …"
usermod -aG video,input "$TARGET_USER" || true

echo ">> Writing udev rule (group write access to brightness for group video) …"
cat >/etc/udev/rules.d/99-backlight-perm.rules <<'RULE'
SUBSYSTEM=="backlight", RUN+="/bin/chgrp video /sys/class/backlight/%k/brightness", RUN+="/bin/chmod g+w /sys/class/backlight/%k/brightness"
RULE
udevadm control --reload-rules || true

echo ">> Reloading systemd and enabling service …"
systemctl daemon-reload
systemctl enable --now "$SERVICE_NAME"

echo ">> Creating sudoers rule for systemctl restart $SERVICE_NAME (user: $TARGET_USER) …"
SUDOERS_FILE="/etc/sudoers.d/touchwake"
# Correct path: systemctl typically at /usr/bin on Debian/RPi OS
SUDOERS_LINE="$TARGET_USER ALL=NOPASSWD: /usr/bin/systemctl restart $SERVICE_NAME"
OLD_LINE="$TARGET_USER ALL=NOPASSWD: /bin/systemctl restart $SERVICE_NAME"
if [ ! -f "$SUDOERS_FILE" ]; then
  echo "$SUDOERS_LINE" > "$SUDOERS_FILE"
  chmod 0440 "$SUDOERS_FILE"
  echo "   Added sudoers rule: $SUDOERS_LINE"
else
  if grep -Fq "$OLD_LINE" "$SUDOERS_FILE"; then
    echo "   Removing outdated /bin/systemctl line"
    grep -Fv "$OLD_LINE" "$SUDOERS_FILE" >"${SUDOERS_FILE}.tmp" && mv "${SUDOERS_FILE}.tmp" "$SUDOERS_FILE"
  fi
  if ! grep -Fxq "$SUDOERS_LINE" "$SUDOERS_FILE"; then
    echo "$SUDOERS_LINE" >> "$SUDOERS_FILE"
    echo "   Added missing sudoers rule: $SUDOERS_LINE"
  else
    echo "   Sudoers rule already present."
  fi
fi

visudo -cf "$SUDOERS_FILE" >/dev/null 2>&1 || echo "WARN: visudo validation failed (please verify manually)"

echo ">> DONE. Launch settings via:"
echo "   Menu → Accessories → Touch Wake Settings"
echo "   Or: /usr/bin/python3 $APP_DIR/touch-wake-settings.py"
