#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, glob, subprocess, configparser, tkinter as tk
from tkinter import ttk, messagebox

CONF_PATH = "/etc/touch-wake-display.conf"
SERVICE = "touch-wake-display.service"

def load_config():
    cfg = {"idle_seconds":"30", "bl_base":"", "force_max_on_wake":"true", "rescan_interval":"2.0", "debug":"false"}
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
        subprocess.run(["systemctl","restart",SERVICE], check=True)
        return True
    except Exception as e:
        messagebox.showerror("Fehler", f"Service-Neustart fehlgeschlagen:\n{e}")
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
        self.geometry("600x380")
        self.resizable(False, False)

        self.cfg = load_config()

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Idle (Sekunden):").grid(row=0, column=0, sticky="w", padx=4, pady=6)
        self.idle_var = tk.StringVar(value=self.cfg["idle_seconds"])
        ttk.Entry(frm, textvariable=self.idle_var, width=12).grid(row=0, column=1, sticky="w")

        ttk.Label(frm, text="Backlight-Pfad (leer = auto):").grid(row=1, column=0, sticky="w", padx=4, pady=6)
        self.bl_var = tk.StringVar(value=self.cfg["bl_base"])
        ttk.Entry(frm, textvariable=self.bl_var, width=46).grid(row=1, column=1, sticky="w")
        ttk.Button(frm, text="Erkennen", command=self.on_detect).grid(row=1, column=2, padx=6)

        self.force_var = tk.BooleanVar(value=self.cfg["force_max_on_wake"].lower() in ("1","true","yes","on"))
        ttk.Checkbutton(frm, text="Beim Aufwachen maximale Helligkeit", variable=self.force_var).grid(row=2, column=1, sticky="w", pady=6)

        ttk.Label(frm, text="Hotplug-Scan (Sek.):").grid(row=3, column=0, sticky="w", padx=4, pady=6)
        self.scan_var = tk.StringVar(value=self.cfg["rescan_interval"])
        ttk.Entry(frm, textvariable=self.scan_var, width=12).grid(row=3, column=1, sticky="w")

        self.debug_var = tk.BooleanVar(value=self.cfg["debug"].lower() in ("1","true","yes","on"))
        ttk.Checkbutton(frm, text="Debug-Logs aktivieren", variable=self.debug_var).grid(row=4, column=1, sticky="w", pady=6)

        ttk.Label(frm, text="Benutzer-/Gruppeninfo:").grid(row=5, column=0, sticky="nw", padx=4, pady=6)
        self.groups = tk.Text(frm, height=3, width=52)
        self.groups.grid(row=5, column=1, columnspan=2, sticky="w")
        self.groups.insert("1.0", check_groups_label())
        self.groups.configure(state="disabled")

        btns = ttk.Frame(frm)
        btns.grid(row=6, column=0, columnspan=3, sticky="e", pady=12)
        ttk.Button(btns, text="Abbrechen", command=self.destroy).pack(side="right", padx=6)
        ttk.Button(btns, text="Speichern & Service neu starten", command=self.on_save).pack(side="right", padx=6)

        for i in range(3):
            frm.grid_columnconfigure(i, weight=0)

    def on_detect(self):
        path = detect_backlight()
        if path:
            self.bl_var.set(path)
        else:
            messagebox.showwarning("Hinweis", "Kein Backlight-Gerät gefunden.")

    def on_save(self):
        try:
            idle = int(self.idle_var.get()); assert idle > 0
        except Exception:
            messagebox.showerror("Fehler", "Idle (Sekunden) muss eine positive Zahl sein.")
            return
        try:
            scan = float(self.scan_var.get()); assert scan > 0
        except Exception:
            messagebox.showerror("Fehler", "Hotplug-Scan (Sek.) muss > 0 sein.")
            return

        bl = self.bl_var.get().strip()
        if bl and (not bl.startswith("/sys/class/backlight/")):
            messagebox.showerror("Fehler", "Backlight-Pfad muss unter /sys/class/backlight/ liegen.")
            return
        if bl and (not os.path.isdir(bl)):
            if not messagebox.askyesno("Bestätigen", f"Pfad {bl} existiert nicht. Trotzdem speichern?"):
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
            messagebox.showerror("Rechte erforderlich",
                                 "Kann /etc/touch-wake-display.conf nicht schreiben.\n"
                                 "Bitte über das Menü starten (fragt via pkexec nach Passwort).")
            return
        except Exception as e:
            messagebox.showerror("Fehler", f"Speichern fehlgeschlagen:\n{e}")
            return

        if restart_service():
            messagebox.showinfo("OK", "Gespeichert und Service neu gestartet.")
            self.destroy()

if __name__ == "__main__":
    app = App()
    app.mainloop()
