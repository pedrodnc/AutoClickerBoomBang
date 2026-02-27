"""
AutoClicker BoomBang - Detecta imágenes en ventanas específicas y hace click
"""

import pyautogui
import cv2
import numpy as np
from mss import mss
import time
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import ctypes
from ctypes import wintypes
import ctypes.wintypes

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.02

# --- Win32 API ---
user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi

EnumWindows = user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
GetWindowTextW = user32.GetWindowTextW
GetWindowTextLengthW = user32.GetWindowTextLengthW
IsWindowVisible = user32.IsWindowVisible
GetWindowRect = user32.GetWindowRect
SetForegroundWindow = user32.SetForegroundWindow
GetClientRect = user32.GetClientRect
ClientToScreen = user32.ClientToScreen

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def get_visible_windows():
    """Devuelve lista de (hwnd, título) de ventanas visibles con título"""
    windows = []
    def callback(hwnd, _):
        if IsWindowVisible(hwnd):
            length = GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value
                if title.strip():
                    windows.append((hwnd, title))
        return True
    EnumWindows(EnumWindowsProc(callback), 0)
    return windows


def get_window_rect(hwnd):
    """Devuelve (x, y, w, h) de la ventana"""
    rect = RECT()
    GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top


class BoomBangClicker:
    def __init__(self):
        self.targets = []
        self.running = False
        self.thread = None
        self.clicks = 0
        self.selected_windows = []  # list of (hwnd, title)
        self.build_gui()

    def build_gui(self):
        self.root = tk.Tk()
        self.root.title("AutoClicker BoomBang")
        self.root.configure(bg="#1a1a2e")
        self.root.resizable(False, False)
        self.root.geometry("460x640")

        main = tk.Frame(self.root, bg="#1a1a2e", padx=15, pady=10)
        main.pack(fill="both", expand=True)

        tk.Label(main, text="🎮 AutoClicker BoomBang", font=("Segoe UI", 14, "bold"),
                 bg="#1a1a2e", fg="#00d4aa").pack(pady=(0, 8))

        # ═══ VENTANAS ═══
        tk.Label(main, text="🪟 Ventanas a escanear:", font=("Segoe UI", 10, "bold"),
                 bg="#1a1a2e", fg="#00d4aa").pack(anchor="w")

        self.windows_list = tk.Listbox(main, height=4, bg="#16213e", fg="#e0e0e0",
                                        selectbackground="#00d4aa", font=("Segoe UI", 9),
                                        borderwidth=0, highlightthickness=0)
        self.windows_list.pack(fill="x", pady=(2, 5))

        wbtn_frame = tk.Frame(main, bg="#1a1a2e")
        wbtn_frame.pack(fill="x", pady=(0, 8))
        tk.Button(wbtn_frame, text="➕ Seleccionar ventana", command=self.pick_window,
                  bg="#16213e", fg="#e0e0e0", font=("Segoe UI", 9), relief="flat",
                  cursor="hand2").pack(side="left", padx=(0, 5))
        tk.Button(wbtn_frame, text="🔄 Refrescar", command=self.refresh_windows,
                  bg="#16213e", fg="#e0e0e0", font=("Segoe UI", 9), relief="flat",
                  cursor="hand2").pack(side="left", padx=(0, 5))
        tk.Button(wbtn_frame, text="🗑️ Quitar", command=self.remove_window,
                  bg="#16213e", fg="#e0e0e0", font=("Segoe UI", 9), relief="flat",
                  cursor="hand2").pack(side="left")

        # ═══ TARGETS ═══
        tk.Label(main, text="🎯 Imágenes objetivo:", font=("Segoe UI", 10, "bold"),
                 bg="#1a1a2e", fg="#00d4aa").pack(anchor="w")

        self.targets_list = tk.Listbox(main, height=3, bg="#16213e", fg="#e0e0e0",
                                        selectbackground="#00d4aa", font=("Segoe UI", 9),
                                        borderwidth=0, highlightthickness=0)
        self.targets_list.pack(fill="x", pady=(2, 5))

        tbtn_frame = tk.Frame(main, bg="#1a1a2e")
        tbtn_frame.pack(fill="x", pady=(0, 8))
        tk.Button(tbtn_frame, text="➕ Añadir imagen", command=self.add_target,
                  bg="#16213e", fg="#e0e0e0", font=("Segoe UI", 9), relief="flat",
                  cursor="hand2").pack(side="left", padx=(0, 5))
        tk.Button(tbtn_frame, text="🗑️ Quitar", command=self.remove_target,
                  bg="#16213e", fg="#e0e0e0", font=("Segoe UI", 9), relief="flat",
                  cursor="hand2").pack(side="left")

        # ═══ SETTINGS ═══
        tk.Label(main, text="⚙️ Configuración", font=("Segoe UI", 10, "bold"),
                 bg="#1a1a2e", fg="#00d4aa").pack(anchor="w", pady=(5, 5))

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

        row2 = tk.Frame(main, bg="#1a1a2e")
        row2.pack(fill="x", pady=2)
        tk.Label(row2, text="Escaneo cada (ms):", bg="#1a1a2e", fg="#e0e0e0",
                 font=("Segoe UI", 9)).pack(side="left")
        self.interval_var = tk.IntVar(value=300)
        tk.Spinbox(row2, from_=50, to=5000, increment=50, width=6,
                   textvariable=self.interval_var, bg="#16213e", fg="#e0e0e0",
                   font=("Segoe UI", 10), buttonbackground="#1a1a2e").pack(side="right")

        row3 = tk.Frame(main, bg="#1a1a2e")
        row3.pack(fill="x", pady=2)
        tk.Label(row3, text="Pausa entre clicks (ms):", bg="#1a1a2e", fg="#e0e0e0",
                 font=("Segoe UI", 9)).pack(side="left")
        self.delay_var = tk.IntVar(value=150)
        tk.Spinbox(row3, from_=10, to=2000, increment=50, width=6,
                   textvariable=self.delay_var, bg="#16213e", fg="#e0e0e0",
                   font=("Segoe UI", 10), buttonbackground="#1a1a2e").pack(side="right")

        # ═══ START ═══
        self.start_btn = tk.Button(main, text="▶  INICIAR", command=self.toggle,
                                    font=("Segoe UI", 13, "bold"),
                                    bg="#00d4aa", fg="#1a1a2e", relief="flat",
                                    cursor="hand2", height=2)
        self.start_btn.pack(fill="x", pady=(12, 5))

        self.status_var = tk.StringVar(value="⏸️ Parado")
        self.clicks_var = tk.StringVar(value="Clicks: 0")
        tk.Label(main, textvariable=self.status_var, font=("Segoe UI", 10, "bold"),
                 bg="#1a1a2e", fg="#ffcc00").pack()
        tk.Label(main, textvariable=self.clicks_var, font=("Segoe UI", 9),
                 bg="#1a1a2e", fg="#e0e0e0").pack()

        tk.Label(main, text="💡 Ratón a esquina sup-izq = parada de emergencia",
                 font=("Segoe UI", 8), bg="#1a1a2e", fg="#666").pack(pady=(8, 0))

        # Window picker dialog
        self.picker = None

    def pick_window(self):
        """Abre diálogo con lista de ventanas abiertas para seleccionar"""
        windows = get_visible_windows()

        picker = tk.Toplevel(self.root)
        picker.title("Seleccionar ventana")
        picker.geometry("500x400")
        picker.configure(bg="#1a1a2e")
        picker.transient(self.root)
        picker.grab_set()

        tk.Label(picker, text="Selecciona una ventana:", font=("Segoe UI", 11, "bold"),
                 bg="#1a1a2e", fg="#00d4aa").pack(pady=(10, 5))

        frame = tk.Frame(picker, bg="#1a1a2e")
        frame.pack(fill="both", expand=True, padx=10, pady=5)

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")

        listbox = tk.Listbox(frame, bg="#16213e", fg="#e0e0e0", selectbackground="#00d4aa",
                              font=("Segoe UI", 9), borderwidth=0, highlightthickness=0,
                              yscrollcommand=scrollbar.set)
        listbox.pack(fill="both", expand=True)
        scrollbar.config(command=listbox.yview)

        for hwnd, title in windows:
            listbox.insert("end", f"  {title}")

        def on_select():
            sel = listbox.curselection()
            if not sel:
                return
            idx = sel[0]
            hwnd, title = windows[idx]
            # Check not already added
            for h, _ in self.selected_windows:
                if h == hwnd:
                    messagebox.showinfo("Ya añadida", "Esa ventana ya está en la lista.")
                    return
            self.selected_windows.append((hwnd, title))
            self.windows_list.insert("end", f"  {title}")
            picker.destroy()

        tk.Button(picker, text="✅ Seleccionar", command=on_select,
                  bg="#00d4aa", fg="#1a1a2e", font=("Segoe UI", 10, "bold"),
                  relief="flat", cursor="hand2").pack(pady=10)

    def refresh_windows(self):
        """Revalida que las ventanas seleccionadas siguen abiertas"""
        valid = []
        self.windows_list.delete(0, "end")
        for hwnd, title in self.selected_windows:
            if IsWindowVisible(hwnd):
                valid.append((hwnd, title))
                self.windows_list.insert("end", f"  {title}")
        self.selected_windows = valid

    def remove_window(self):
        sel = self.windows_list.curselection()
        if sel:
            self.selected_windows.pop(sel[0])
            self.windows_list.delete(sel[0])

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
            if not self.selected_windows:
                messagebox.showwarning("Sin ventanas", "Selecciona al menos una ventana a escanear.")
                return
            self.running = True
            self.clicks = 0
            self.start_btn.config(text="⏹  PARAR", bg="#f85149")
            self.status_var.set("🔍 Escaneando ventanas...")
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

                    for hwnd, title in self.selected_windows:
                        if not self.running:
                            return
                        if not IsWindowVisible(hwnd):
                            continue

                        # Get window position
                        x, y, w, h = get_window_rect(hwnd)
                        if w <= 0 or h <= 0:
                            continue

                        # Capture window region
                        monitor = {"left": x, "top": y, "width": w, "height": h}
                        screenshot = np.array(sct.grab(monitor))
                        screen = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)

                        for t in self.targets:
                            if not self.running:
                                return
                            if t['h'] > h or t['w'] > w:
                                continue

                            result = cv2.matchTemplate(screen, t['img'], cv2.TM_CCOEFF_NORMED)
                            locations = np.where(result >= threshold)

                            coords = list(zip(*locations))
                            clicked_zones = []
                            for pt_y, pt_x in coords:
                                cx = x + pt_x + t['w'] // 2
                                cy = y + pt_y + t['h'] // 2

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
