#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backlight-Idle/Wake Daemon (CM5 + Waveshare 8-DSI-TOUCH-A) mit Hotplug + Config + Logs
- Dimmt nach Inaktivität (Brightness=0)
- Wake bei Touch/Keyboard/Mouse (optional: immer maximale Helligkeit)
- Steuert bl_power (falls vorhanden)
- KEIN grab(); erkennt Hotplug (USB Tastatur/Maus)
- Lädt Einstellungen aus /etc/touch-wake-display.conf
"""

import os, time, signal, select, glob, configparser

CONF_PATH = "/etc/touch-wake-display.conf"

# ===== Defaults (über Config überschreibbar) =================================
IDLE_SECONDS = 30
BL_BASE = ""  # leer => auto-detect
FORCE_MAX_ON_WAKE = True
RESCAN_INTERVAL = 2.0
DEBUG = False
# ============================================================================

def load_config():
    global IDLE_SECONDS, BL_BASE, FORCE_MAX_ON_WAKE, RESCAN_INTERVAL, DEBUG
    if not os.path.exists(CONF_PATH):
        return
    cfg = configparser.ConfigParser()
    cfg.read(CONF_PATH)
    sec = cfg["touchwake"] if "touchwake" in cfg else cfg["DEFAULT"]
    IDLE_SECONDS = int(sec.get("idle_seconds", IDLE_SECONDS))
    BL_BASE = sec.get("bl_base", BL_BASE).strip()
    FORCE_MAX_ON_WAKE = sec.get("force_max_on_wake", str(FORCE_MAX_ON_WAKE)).lower() in ("1","true","yes","on")
    RESCAN_INTERVAL = float(sec.get("rescan_interval", RESCAN_INTERVAL))
    DEBUG = sec.get("debug", str(DEBUG)).lower() in ("1","true","yes","on")

load_config()

try:
    from evdev import InputDevice, ecodes  # type: ignore
except Exception:
    print("Fehlt evdev? -> sudo apt install -y python3-evdev")
    raise

def log(*a):
    if DEBUG:
        print(time.strftime("%H:%M:%S"), *a, flush=True)

# --- Backlight/Power ---------------------------------------------------------
def autodetect_backlight():
    cands = sorted([d for d in glob.glob("/sys/class/backlight/*") if os.path.isdir(d)])
    return cands[0] if cands else None

if not BL_BASE:
    BL_BASE = autodetect_backlight() or ""
if not BL_BASE or not os.path.isdir(BL_BASE):
    raise SystemExit(f"Backlight-Gerät nicht gefunden. Setze 'bl_base' in {CONF_PATH}.")

BL_BRIGHTNESS = os.path.join(BL_BASE, "brightness")
BL_MAX_PATH   = os.path.join(BL_BASE, "max_brightness")
BL_POWER_PATH = os.path.join(BL_BASE, "bl_power")

try:
    MAX = int(open(BL_MAX_PATH).read().strip())
except Exception:
    MAX = 255

def set_power(on: bool):
    if os.path.exists(BL_POWER_PATH):
        try:
            with open(BL_POWER_PATH, 'w') as f:
                f.write('0' if on else '4')  # 0=an, 4=aus
            log("bl_power ->", 0 if on else 4)
        except Exception as e:
            log("WARN set_power:", e)

def read_brightness():
    try:
        return int(open(BL_BRIGHTNESS).read().strip())
    except Exception:
        return MAX

def set_brightness(val: int):
    val = max(0, min(MAX, int(val)))
    try:
        with open(BL_BRIGHTNESS, 'w') as f:
            f.write(str(val))
        log("brightness ->", val)
    except Exception as e:
        log("ERROR set_brightness:", e)

# --- Geräteklassifizierung ---------------------------------------------------
def is_touchscreen(dev) -> bool:
    name = (dev.name or "").lower()
    if 'touch' in name or 'goodix' in name:
        return True
    try:
        props = dev.properties()
        if ecodes.INPUT_PROP_DIRECT in props:
            return True
    except Exception:
        pass
    return False

def is_keyboard_or_mouse(dev) -> bool:
    name = (dev.name or "").lower()
    caps = dev.capabilities()
    is_mouse = (ecodes.EV_REL in caps) or ('mouse' in name)
    is_kbd   = (ecodes.EV_KEY in caps) or ('keyboard' in name) or ('kbd' in name)
    return is_mouse or is_kbd

RELEVANT_TYPES = {ecodes.EV_KEY, ecodes.EV_REL, ecodes.EV_ABS}
def is_relevant_event(e):
    if e.type == ecodes.EV_KEY:
        return e.value in (1, 2)  # press/repeat
    if e.type == ecodes.EV_REL:
        return True               # Mausbewegung
    if e.type == ecodes.EV_ABS:
        return True               # Touch-Koordinaten
    return False

# --- Hotplug-Verwaltung ------------------------------------------------------
poller = select.poll()
FD_TO_DEV = {}
PATH_TO_DEV = {}

def register_device_path(path):
    if path in PATH_TO_DEV:
        return
    try:
        dev = InputDevice(path)
        if not (is_touchscreen(dev) or is_keyboard_or_mouse(dev)):
            log("skip device:", path, dev.name)
            return
        _ = dev.fd
        poller.register(dev.fd, select.POLLIN)
        FD_TO_DEV[dev.fd] = dev
        PATH_TO_DEV[path] = dev
        log("reg device:", path, dev.name)
    except Exception as e:
        log("WARN register", path, e)

def unregister_missing_devices():
    existing_paths = set(glob.glob('/dev/input/event*'))
    to_remove = [p for p in list(PATH_TO_DEV.keys()) if p not in existing_paths]
    for p in to_remove:
        dev = PATH_TO_DEV.pop(p, None)
        if dev:
            try:
                poller.unregister(dev.fd)
            except Exception:
                pass
            FD_TO_DEV.pop(dev.fd, None)
            try:
                dev.close()
            except Exception:
                pass
            log("unreg device:", p)

def rescan_devices():
    unregister_missing_devices()
    for p in sorted(glob.glob('/dev/input/event*')):
        register_device_path(p)

# Erste Registrierung
rescan_devices()
if not PATH_TO_DEV:
    raise SystemExit("Keine passenden /dev/input/event* Geräte gefunden.")

# --- Idle/Wake ---------------------------------------------------------------
asleep = False
last_event_ts = time.time()
last_rescan_ts = 0.0

def wake_display():
    global asleep
    set_power(True)
    if FORCE_MAX_ON_WAKE or read_brightness() <= 0:
        set_brightness(MAX)
    asleep = False
    log("WAKE")

def sleep_display():
    global asleep
    set_brightness(0)
    set_power(False)
    asleep = True
    log("SLEEP")

# Beim Start sicherstellen, dass es nicht dunkel bleibt
set_power(True)
if read_brightness() <= 0:
    set_brightness(MAX)

# --- Signal Handling ---------------------------------------------------------
_running = True
def _stop(*_):
    global _running
    _running = False
signal.signal(signal.SIGTERM, _stop)
signal.signal(signal.SIGINT, _stop)

log(f"RUN idle={IDLE_SECONDS}s, rescan={RESCAN_INTERVAL}s, max={MAX}, path={BL_BASE}, debug={DEBUG}")

# --- Hauptschleife -----------------------------------------------------------
while _running:
    now = time.time()
    if now - last_rescan_ts >= RESCAN_INTERVAL:
        rescan_devices()
        last_rescan_ts = now

    events = poller.poll(200)
    any_relevant = False
    if events:
        for fd, flag in events:
            if not (flag & select.POLLIN): continue
            dev = FD_TO_DEV.get(fd)
            if not dev: continue
            try:
                for e in dev.read():
                    if e.type in RELEVANT_TYPES and is_relevant_event(e):
                        any_relevant = True
            except BlockingIOError:
                pass
            except OSError:
                pass

    if any_relevant:
        if asleep:
            wake_display()
        last_event_ts = now
        log("EVENT -> reset idle")
    else:
        if not asleep and (now - last_event_ts) >= IDLE_SECONDS:
            sleep_display()

    time.sleep(0.02)

log("EXIT")
