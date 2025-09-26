#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, glob, subprocess, configparser, tkinter as tk
from tkinter import ttk, messagebox

CONF_PATH = "/etc/touch-wake-display.conf"
SERVICE = "touch-wake-display.service"
SYSTEMCTL = "/usr/bin/systemctl"  # fixed path (sudoers rule depends on this)

MIN_USER_BRIGHTNESS = 4  # Do not allow manual brightness below this raw value

def load_config():
    cfg = {"idle_seconds":"30", "bl_base":"", "force_max_on_wake":"false", "rescan_interval":"2.0", "debug":"false"}
    if os.path.exists(CONF_PATH):
        p = configparser.ConfigParser()
        p.read(CONF_PATH)
        sec = p["touchwake"] if "touchwake" in p else p["DEFAULT"]
        for k in cfg.keys():
            if k in sec: cfg[k] = sec.get(k, cfg[k])
    return cfg

def save_config(cfg):
    p = configparser.ConfigParser()
    p["touchwake"] = cfg
    with open(CONF_PATH, "w") as f:
        p.write(f)

def detect_backlight():
    cands = sorted([d for d in glob.glob("/sys/class/backlight/*") if os.path.isdir(d)])
    return cands[0] if cands else ""

def restart_service():
    try:
        subprocess.run([SYSTEMCTL, "restart", SERVICE], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e1:
        try:
            subprocess.run(["sudo", "-n", SYSTEMCTL, "restart", SERVICE], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            return True
        except subprocess.CalledProcessError as e2:
            messagebox.showerror("Error", (
                "Service restart failed.\n\n"
                f"systemctl exit: {e1.returncode}; sudo/systemctl exit: {e2.returncode}\n"
                "Check sudoers file: cat /etc/sudoers.d/touchwake\n"
                f"Expected: <user> ALL=NOPASSWD: {SYSTEMCTL} restart {SERVICE}"
            ))
            return False
        except FileNotFoundError:
            messagebox.showerror("Error", "sudo not found – install sudo or restart the service manually.")
            return False
    except FileNotFoundError:
        messagebox.showerror("Error", f"{SYSTEMCTL} not found.")
        return False

def check_groups_label():
    try:
        out = subprocess.check_output(["id"], text=True)
    except Exception:
        out = ""
    return out

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Touch Wake Settings")
        self.geometry("780x400")  # widened
        self.resizable(True, False)  # allow horizontal resize

        self.cfg = load_config()

        # Rebuild layout with brightness slider inserted before user/group info
        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Idle (seconds):").grid(row=0, column=0, sticky="w", padx=4, pady=6)
        self.idle_var = tk.StringVar(value=self.cfg["idle_seconds"])
        ttk.Entry(frm, textvariable=self.idle_var, width=12).grid(row=0, column=1, sticky="w")

        ttk.Label(frm, text="Backlight path (empty = auto):").grid(row=1, column=0, sticky="w", padx=4, pady=6)
        self.bl_var = tk.StringVar(value=self.cfg["bl_base"])
        ttk.Entry(frm, textvariable=self.bl_var, width=60).grid(row=1, column=1, sticky="w")
        ttk.Button(frm, text="Detect", command=self.on_detect).grid(row=1, column=2, padx=6)

        self.force_var = tk.BooleanVar(value=self.cfg["force_max_on_wake"].lower() in ("1","true","yes","on"))
        ttk.Checkbutton(frm, text="Force max brightness on wake", variable=self.force_var).grid(row=2, column=1, sticky="w", pady=6)

        ttk.Label(frm, text="Hotplug scan (s):").grid(row=3, column=0, sticky="w", padx=4, pady=6)
        self.scan_var = tk.StringVar(value=self.cfg["rescan_interval"])
        ttk.Entry(frm, textvariable=self.scan_var, width=12).grid(row=3, column=1, sticky="w")

        self.debug_var = tk.BooleanVar(value=self.cfg["debug"].lower() in ("1","true","yes","on"))
        ttk.Checkbutton(frm, text="Enable debug logs", variable=self.debug_var).grid(row=4, column=1, sticky="w", pady=6)

        # --- Brightness Slider -------------------------------------------------
        ttk.Label(frm, text="Brightness:").grid(row=5, column=0, sticky="w", padx=4, pady=(10,4))
        slider_frame = ttk.Frame(frm)
        slider_frame.grid(row=5, column=1, columnspan=2, sticky="we", pady=(10,4))
        slider_frame.columnconfigure(0, weight=1)
        self.brightness_scale = ttk.Scale(slider_frame, from_=0, to=100, orient="horizontal", command=self._on_brightness_drag)
        self.brightness_scale.grid(row=0, column=0, sticky="we", padx=(0,6))
        self.brightness_value_lbl = ttk.Label(slider_frame, text="-")
        self.brightness_value_lbl.grid(row=0, column=1, sticky="e")
        self.brightness_status = ttk.Label(slider_frame, text="", foreground="#666")
        self.brightness_status.grid(row=1, column=0, columnspan=2, sticky="w", pady=(2,0))
        self._brightness_base = None
        self._brightness_path = None
        self._brightness_max = 100  # real max (raw) will be detected
        self._dragging = False
        self._brightness_poll_job = None
        self._last_write_error = False
        self.brightness_scale.bind("<ButtonPress-1>", lambda e: self._set_dragging(True))
        self.brightness_scale.bind("<ButtonRelease-1>", lambda e: self._on_brightness_release())

        # --- User / Groups info ------------------------------------------------
        ttk.Label(frm, text="User / groups info:").grid(row=6, column=0, sticky="nw", padx=4, pady=6)
        self.groups = tk.Text(frm, height=3, width=70)
        self.groups.grid(row=6, column=1, columnspan=2, sticky="we")
        self.groups.insert("1.0", check_groups_label())
        self.groups.configure(state="disabled")

        btns = ttk.Frame(frm)
        btns.grid(row=7, column=0, columnspan=3, sticky="e", pady=12)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right", padx=6)
        ttk.Button(btns, text="Save & restart service", command=self.on_save).pack(side="right", padx=6)

        frm.grid_columnconfigure(1, weight=1)
        frm.grid_columnconfigure(0, weight=0)
        frm.grid_columnconfigure(2, weight=0)

        self._init_brightness_slider(initial=True)

    def on_detect(self):
        path = detect_backlight()
        if path:
            self.bl_var.set(path)
        else:
            messagebox.showwarning("Info", "No backlight device found.")
        self._init_brightness_slider()

    # --- Brightness handling --------------------------------------------------
    def _resolve_backlight_base(self):
        base = self.bl_var.get().strip()
        if base and os.path.isdir(base):
            return base
        auto = detect_backlight()
        return auto if auto and os.path.isdir(auto) else None

    def _init_brightness_slider(self, initial=False):
        base = self._resolve_backlight_base()
        self._brightness_base = base
        if not base:
            self._brightness_path = None
            self.brightness_scale.state(["disabled"])
            self.brightness_value_lbl.configure(text="n/a")
            self.brightness_status.configure(text="Backlight not found")
            return
        bright = os.path.join(base, "brightness")
        maxp = os.path.join(base, "max_brightness")
        if not os.path.exists(bright):
            self._brightness_path = None
            self.brightness_scale.state(["disabled"])
            self.brightness_status.configure(text="brightness file missing")
            return
        try:
            with open(maxp) as f:
                maxv = int(f.read().strip())
        except Exception:
            maxv = 255
        if maxv <= MIN_USER_BRIGHTNESS:
            maxv = MIN_USER_BRIGHTNESS + 1
        self._brightness_max = maxv
        self._brightness_path = bright
        self.brightness_scale.state(["!disabled"])
        # Slider is percentage 0..100
        self.brightness_scale.configure(from_=0, to=100)
        cur_raw = self._read_current_brightness()
        if cur_raw is not None:
            percent = self._raw_to_percent(cur_raw)
            self.brightness_scale.set(percent)
            self._update_brightness_label(percent, cur_raw)
            sleep_tag = " (sleep)" if cur_raw == 0 else ""
            self.brightness_status.configure(text=f"Path: {bright}{sleep_tag}")
        else:
            self.brightness_value_lbl.configure(text="-")
            self.brightness_status.configure(text=f"Path: {bright} (unreadable)")
        if initial:
            self._start_brightness_poll()

    # --- Mapping helpers -----------------------------------------------------
    def _raw_to_percent(self, raw: int) -> int:
        if raw <= MIN_USER_BRIGHTNESS:
            return 0
        span = self._brightness_max - MIN_USER_BRIGHTNESS
        if span <= 0:
            return 0
        return max(0, min(100, round((raw - MIN_USER_BRIGHTNESS) / span * 100)))

    def _percent_to_raw(self, percent: float) -> int:
        percent = max(0.0, min(100.0, float(percent)))
        if percent <= 0:
            # Enforce minimum (do not allow manual complete off)
            return MIN_USER_BRIGHTNESS
        span = self._brightness_max - MIN_USER_BRIGHTNESS
        return MIN_USER_BRIGHTNESS + round((percent / 100.0) * span)

    def _update_brightness_label(self, percent: float, raw: int):
        self.brightness_value_lbl.configure(text=f"{int(round(percent))}% ({raw}/{self._brightness_max})")

    def _read_current_brightness(self):
        path = self._brightness_path
        if not path:
            return None
        try:
            with open(path) as f:
                return int(f.read().strip())
        except Exception:
            return None

    def _write_brightness(self, percent_value: float):
        if not self._brightness_path:
            return
        try:
            raw = self._percent_to_raw(percent_value)
            with open(self._brightness_path, 'w') as f:
                f.write(str(raw))
            self._last_write_error = False
            self._update_brightness_label(percent_value, raw)
        except PermissionError:
            if not self._last_write_error:
                messagebox.showerror("Permission denied", "Cannot write brightness. Ensure user is in group 'video'.")
                self._last_write_error = True
        except Exception as e:
            if not self._last_write_error:
                messagebox.showerror("Write error", f"Failed to set brightness: {e}")
                self._last_write_error = True

    def _on_brightness_drag(self, val):
        if self._dragging:
            self._write_brightness(float(val))

    def _set_dragging(self, state: bool):
        self._dragging = state

    def _on_brightness_release(self):
        self._set_dragging(False)
        self._write_brightness(self.brightness_scale.get())

    def _start_brightness_poll(self):
        if self._brightness_poll_job:
            self.after_cancel(self._brightness_poll_job)
        self._brightness_poll_job = self.after(2000, self._poll_brightness_loop)

    def _poll_brightness_loop(self):
        cur_raw = self._read_current_brightness()
        if cur_raw is not None and not self._dragging:
            percent = self._raw_to_percent(cur_raw)
            if int(round(self.brightness_scale.get())) != int(percent):
                self.brightness_scale.set(percent)
            self._update_brightness_label(percent, cur_raw)
            sleep_tag = " (sleep)" if cur_raw == 0 else ""
            self.brightness_status.configure(text=f"Path: {self._brightness_path}{sleep_tag}")
        self._start_brightness_poll()

    def on_save(self):
        try:
            idle = int(self.idle_var.get()); assert idle > 0
        except Exception:
            messagebox.showerror("Error", "Idle (seconds) must be a positive integer.")
            return
        try:
            scan = float(self.scan_var.get()); assert scan > 0
        except Exception:
            messagebox.showerror("Error", "Hotplug scan interval must be > 0.")
            return

        bl = self.bl_var.get().strip()
        if bl and (not bl.startswith("/sys/class/backlight/")):
            messagebox.showerror("Error", "Backlight path must be under /sys/class/backlight/.")
            return
        if bl and (not os.path.isdir(bl)):
            if not messagebox.askyesno("Confirm", f"Path {bl} does not exist. Save anyway?"):
                return

        cfg = {
            "idle_seconds": str(idle),
            "bl_base": bl,
            "force_max_on_wake": "true" if self.force_var.get() else "false",
            "rescan_interval": str(scan),
            "debug": "true" if self.debug_var.get() else "false",
        }

        try:
            save_config(cfg)
        except PermissionError:
            messagebox.showerror("Permission required",
                                 "Cannot write /etc/touch-wake-display.conf.\n"
                                 "Reinstall: file should be owned by the user.")
            return
        except Exception as e:
            messagebox.showerror("Error", f"Saving failed:\n{e}")
            return

        if restart_service():
            messagebox.showinfo("OK", "Saved and service restarted.")
            self.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()
