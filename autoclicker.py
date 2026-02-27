"""
AutoClicker BoomBang - Detecta imágenes y hace click
"""

import pyautogui
import cv2
import numpy as np
from mss import mss
import time
import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.02


class BoomBangClicker:
    def __init__(self):
        self.targets = []
        self.running = False
        self.thread = None
        self.clicks = 0
        self.build_gui()

    def build_gui(self):
        self.root = tk.Tk()
        self.root.title("AutoClicker BoomBang")
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(False, False)
        self.root.geometry("420x520")

        main = tk.Frame(self.root, bg="#1a1a2e", padx=15, pady=15)
        main.pack(fill="both", expand=True)

        tk.Label(main, text="🎮 AutoClicker BoomBang", font=("Segoe UI", 14, "bold"),
                 bg="#1a1a2e", fg="#00d4aa").pack(pady=(0, 10))

        # --- Targets ---
        tk.Label(main, text="🎯 Imágenes objetivo:", font=("Segoe UI", 10),
                 bg="#1a1a2e", fg="#e0e0e0").pack(anchor="w")

        self.targets_list = tk.Listbox(main, height=4, bg="#16213e", fg="#e0e0e0",
                                        selectbackground="#00d4aa", font=("Segoe UI", 9),
                                        borderwidth=0, highlightthickness=0)
        self.targets_list.pack(fill="x", pady=(2, 5))

        btn_frame = tk.Frame(main, bg="#1a1a2e")
        btn_frame.pack(fill="x", pady=(0, 10))
        tk.Button(btn_frame, text="➕ Añadir imagen", command=self.add_target,
                  bg="#16213e", fg="#e0e0e0", font=("Segoe UI", 9), relief="flat",
                  cursor="hand2").pack(side="left", padx=(0, 5))
        tk.Button(btn_frame, text="🗑️ Quitar", command=self.remove_target,
                  bg="#16213e", fg="#e0e0e0", font=("Segoe UI", 9), relief="flat",
                  cursor="hand2").pack(side="left")

        # --- Settings ---
        tk.Label(main, text="⚙️ Configuración", font=("Segoe UI", 10, "bold"),
                 bg="#1a1a2e", fg="#00d4aa").pack(anchor="w", pady=(5, 5))

        # Threshold
        row1 = tk.Frame(main, bg="#1a1a2e")
        row1.pack(fill="x", pady=2)
        tk.Label(row1, text="Sensibilidad:", bg="#1a1a2e", fg="#e0e0e0",
                 font=("Segoe UI", 9)).pack(side="left")
        self.threshold_var = tk.IntVar(value=75)
        self.threshold_label = tk.Label(row1, text="75%", bg="#1a1a2e", fg="#e0e0e0",
                                         font=("Segoe UI", 9))
        self.threshold_label.pack(side="right")
        tk.Scale(row1, from_=50, to=95, orient="horizontal", variable=self.threshold_var,
                 bg="#1a1a2e", fg="#e0e0e0", troughcolor="#16213e", highlightthickness=0,
                 length=180, showvalue=False,
                 command=lambda v: self.threshold_label.config(text=f"{v}%")).pack(side="right")

        # Scan interval
        row2 = tk.Frame(main, bg="#1a1a2e")
        row2.pack(fill="x", pady=2)
        tk.Label(row2, text="Escaneo cada (ms):", bg="#1a1a2e", fg="#e0e0e0",
                 font=("Segoe UI", 9)).pack(side="left")
        self.interval_var = tk.IntVar(value=300)
        tk.Spinbox(row2, from_=50, to=5000, increment=50, width=6,
                   textvariable=self.interval_var, bg="#16213e", fg="#e0e0e0",
                   font=("Segoe UI", 10), buttonbackground="#1a1a2e").pack(side="right")

        # Click delay
        row3 = tk.Frame(main, bg="#1a1a2e")
        row3.pack(fill="x", pady=2)
        tk.Label(row3, text="Pausa entre clicks (ms):", bg="#1a1a2e", fg="#e0e0e0",
                 font=("Segoe UI", 9)).pack(side="left")
        self.delay_var = tk.IntVar(value=150)
        tk.Spinbox(row3, from_=10, to=2000, increment=50, width=6,
                   textvariable=self.delay_var, bg="#16213e", fg="#e0e0e0",
                   font=("Segoe UI", 10), buttonbackground="#1a1a2e").pack(side="right")

        # --- Start button ---
        self.start_btn = tk.Button(main, text="▶  INICIAR", command=self.toggle,
                                    font=("Segoe UI", 13, "bold"),
                                    bg="#00d4aa", fg="#1a1a2e", relief="flat",
                                    cursor="hand2", height=2)
        self.start_btn.pack(fill="x", pady=(15, 5))

        # --- Status ---
        self.status_var = tk.StringVar(value="⏸️ Parado")
        self.clicks_var = tk.StringVar(value="Clicks: 0")
        tk.Label(main, textvariable=self.status_var, font=("Segoe UI", 10, "bold"),
                 bg="#1a1a2e", fg="#ffcc00").pack()
        tk.Label(main, textvariable=self.clicks_var, font=("Segoe UI", 9),
                 bg="#1a1a2e", fg="#e0e0e0").pack()

        tk.Label(main, text="💡 Ratón a esquina sup-izq = parada de emergencia",
                 font=("Segoe UI", 8), bg="#1a1a2e", fg="#666").pack(pady=(10, 0))

    def add_target(self):
        files = filedialog.askopenfilenames(
            title="Selecciona imágenes de los objetos",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.bmp")]
        )
        for f in files:
            img = cv2.imread(f)
            if img is not None:
                name = os.path.basename(f)
                self.targets.append({'name': name, 'img': img, 'h': img.shape[0], 'w': img.shape[1]})
                self.targets_list.insert("end", f"  {name} ({img.shape[1]}x{img.shape[0]}px)")

    def remove_target(self):
        sel = self.targets_list.curselection()
        if sel:
            self.targets.pop(sel[0])
            self.targets_list.delete(sel[0])

    def toggle(self):
        if self.running:
            self.running = False
            self.start_btn.config(text="▶  INICIAR", bg="#00d4aa")
            self.status_var.set("⏸️ Parado")
        else:
            if not self.targets:
                messagebox.showwarning("Sin objetivos", "Añade al menos una imagen objetivo.")
                return
            self.running = True
            self.clicks = 0
            self.start_btn.config(text="⏹  PARAR", bg="#f85149")
            self.status_var.set("🔍 Escaneando...")
            self.thread = threading.Thread(target=self.scan_loop, daemon=True)
            self.thread.start()

    def scan_loop(self):
        threshold = self.threshold_var.get() / 100.0
        interval = self.interval_var.get() / 1000.0
        delay = self.delay_var.get() / 1000.0

        with mss() as sct:
            while self.running:
                try:
                    # Failsafe
                    pos = pyautogui.position()
                    if pos.x <= 5 and pos.y <= 5:
                        self.running = False
                        self.root.after(0, lambda: self.status_var.set("🛑 Failsafe — parado"))
                        self.root.after(0, lambda: self.start_btn.config(text="▶  INICIAR", bg="#00d4aa"))
                        return

                    # Scan all monitors
                    for monitor in sct.monitors[1:]:
                        if not self.running:
                            return
                        screenshot = np.array(sct.grab(monitor))
                        screen = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)

                        for t in self.targets:
                            if not self.running:
                                return
                            result = cv2.matchTemplate(screen, t['img'], cv2.TM_CCOEFF_NORMED)
                            locations = np.where(result >= threshold)

                            coords = list(zip(*locations))
                            # Skip nearby duplicates
                            clicked_zones = []
                            for pt_y, pt_x in coords:
                                cx = monitor["left"] + pt_x + t['w'] // 2
                                cy = monitor["top"] + pt_y + t['h'] // 2

                                # Check not too close to previous click
                                too_close = False
                                for zx, zy in clicked_zones:
                                    if abs(cx - zx) < t['w'] and abs(cy - zy) < t['h']:
                                        too_close = True
                                        break
                                if too_close:
                                    continue

                                clicked_zones.append((cx, cy))
                                pyautogui.click(cx, cy)
                                self.clicks += 1
                                self.root.after(0, lambda c=self.clicks: self.clicks_var.set(f"Clicks: {c}"))
                                time.sleep(delay)

                    time.sleep(interval)

                except pyautogui.FailSafeException:
                    self.running = False
                    self.root.after(0, lambda: self.status_var.set("🛑 Failsafe — parado"))
                    self.root.after(0, lambda: self.start_btn.config(text="▶  INICIAR", bg="#00d4aa"))
                    return
                except Exception:
                    time.sleep(0.5)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = BoomBangClicker()
    app.run()
