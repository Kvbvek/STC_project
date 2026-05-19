import tkinter as tk
from tkinter import scrolledtext
from PIL import Image, ImageTk

import threading
import bluetooth
import subprocess
import numpy as np
import matplotlib.pyplot as plt

# KONFIG
MAC = "E4:5F:01:2B:5F:7F"   # MAC RX
AUDIO_DEV = "plughw:3,0"

BG = "#0f172a"
CARD = "#162033"
CARD2 = "#0b1120"
TEXT = "#e5e7eb"
SUBTEXT = "#94a3b8"
GREEN = "#22c55e"
RED = "#ef4444"
BLUE = "#3b82f6"

# AUDIO / BT
sock = None
process = None
running = False
data_buffer = []

# GUI helpers
def rounded_frame(parent, color):
    return tk.Frame(parent, bg=color, bd=0, highlightthickness=0)

def log(msg):
    console.insert(tk.END, f"> {msg}\n")
    console.see(tk.END)

def set_status(text, color):
    status_dot.config(fg=color)
    status_text.config(text=text)

def draw_wave(samples):
    canvas.delete("wave")

    if len(samples) < 2:
        return

    w = canvas.winfo_width()
    h = canvas.winfo_height()

    if w < 10 or h < 10:
        return

    step = max(1, len(samples)//w)
    s = samples[::step][:w]

    if len(s) < 2:
        return

    s = s.astype(float)
    mx = np.max(np.abs(s))
    if mx > 0:
        s /= mx

    mid = h/2
    scale = h*0.35

    pts = []
    for x, val in enumerate(s):
        y = mid - val*scale
        pts.extend([x, y])

    canvas.create_line(
        pts,
        fill="#22c55e",
        width=2,
        smooth=True,
        tags="wave"
    )

def update_wave(samples):
    root.after(0, lambda: draw_wave(samples))

# TX logic
def start_stream():
    global sock, process, running, data_buffer

    if running:
        return

    try:
        log("Connecting Bluetooth...")
        set_status("CONNECTING", BLUE)

        sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        sock.connect((MAC, 1))

        log("Bluetooth connected")
        set_status("STREAMING", GREEN)

        data_buffer = []
        running = True

        process = subprocess.Popen([
            "arecord",
            "-D", AUDIO_DEV,
            "-f", "S16_LE",
            "-c", "1",
            "-r", "44100"
        ], stdout=subprocess.PIPE)

        log("Audio capture started")

        def loop():
            global running

            while running:
                data = process.stdout.read(4096)
                if not data:
                    break

                sock.send(data)

                samples = np.frombuffer(data, dtype=np.int16)
                data_buffer.append(samples)

                update_wave(samples)

            log("Streaming loop ended")

        threading.Thread(target=loop, daemon=True).start()

    except Exception as e:
        log(f"ERROR: {e}")
        set_status("ERROR", RED)

def stop_stream():
    global running, sock, process

    if not running:
        return

    running = False

    try:
        if process:
            process.terminate()
            process = None

        if sock:
            sock.close()
            sock = None

    except:
        pass

    set_status("STOPPED", RED)
    log("Streaming stopped")

def plot_tx():
    if len(data_buffer) == 0:
        log("No TX data")
        return

    audio = np.concatenate(data_buffer)

    plt.figure(figsize=(12,4))
    plt.plot(audio)
    plt.title("TX waveform")
    plt.xlabel("Sample")
    plt.ylabel("Amplitude")
    plt.grid(True)
    plt.show()

    log("TX waveform plotted")

def on_close():
    stop_stream()
    root.destroy()

# APP
root = tk.Tk()
root.title("STC Wireless Sound Analyzer - TX")
root.geometry("1250x780")
root.configure(bg=BG)
root.protocol("WM_DELETE_WINDOW", on_close)

# ================= HEADER
header = rounded_frame(root, CARD)
header.pack(fill="x", padx=20, pady=20)

img1 = Image.open("aghlogo.png").resize((90, 90))
logo1 = ImageTk.PhotoImage(img1)

img2 = Image.open("mtmlogo.png").resize((90, 90))
logo2 = ImageTk.PhotoImage(img2)

tk.Label(header, image=logo1, bg=CARD).pack(side="left", padx=20, pady=15)

center = tk.Frame(header, bg=CARD)
center.pack(side="left", expand=True)

tk.Label(
    center,
    text="STC Wireless Sound Analyzer [TX]",
    font=("Arial", 28, "bold"),
    fg="white",
    bg=CARD
).pack(pady=(18, 0))

tk.Label(
    center,
    text="Bluetooth Audio Acquisition & Analysis System",
    font=("Arial", 13),
    fg=SUBTEXT,
    bg=CARD
).pack(pady=(0, 18))

tk.Label(header, image=logo2, bg=CARD).pack(side="right", padx=20, pady=15)

# ================= STATUS
status_frame = rounded_frame(root, CARD)
status_frame.pack(fill="x", padx=20, pady=(0, 15))

status_dot = tk.Label(
    status_frame,
    text="●",
    font=("Arial", 26),
    fg=GREEN,
    bg=CARD
)
status_dot.pack(side="left", padx=(20, 5), pady=15)

status_text = tk.Label(
    status_frame,
    text="READY",
    font=("Arial", 18, "bold"),
    fg=TEXT,
    bg=CARD
)
status_text.pack(side="left", pady=15)

device_label = tk.Label(
    status_frame,
    text=f"{AUDIO_DEV} | Bluetooth RFCOMM",
    font=("Arial", 12),
    fg=SUBTEXT,
    bg=CARD
)
device_label.pack(side="right", padx=20)

# ================= BUTTONS
btn_frame = tk.Frame(root, bg=BG)
btn_frame.pack(fill="x", padx=20, pady=5)

def make_btn(text, color, cmd):
    return tk.Button(
        btn_frame,
        text=text,
        command=cmd,
        bg=color,
        fg="white",
        activebackground=color,
        activeforeground="white",
        relief="flat",
        bd=0,
        padx=25,
        pady=12,
        font=("Arial", 11, "bold"),
        cursor="hand2"
    )

make_btn("START", GREEN, start_stream).pack(side="left", padx=6)
make_btn("STOP", RED, stop_stream).pack(side="left", padx=6)
make_btn("PLOT TX", BLUE, plot_tx).pack(side="left", padx=6)

# ================= MAIN
main = tk.Frame(root, bg=BG)
main.pack(fill="both", expand=True, padx=20, pady=15)

wave_frame = rounded_frame(main, CARD)
wave_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

tk.Label(
    wave_frame,
    text="LIVE SIGNAL VIEW",
    font=("Arial", 18, "bold"),
    fg="white",
    bg=CARD
).pack(pady=15)

canvas = tk.Canvas(
    wave_frame,
    bg=CARD2,
    highlightthickness=0
)
canvas.pack(fill="both", expand=True, padx=20, pady=(0, 20))

side = rounded_frame(main, CARD)
side.pack(side="right", fill="y")

tk.Label(
    side,
    text="SYSTEM LOG",
    font=("Arial", 16, "bold"),
    fg="white",
    bg=CARD
).pack(pady=15)

console = scrolledtext.ScrolledText(
    side,
    width=42,
    height=22,
    bg=CARD2,
    fg=TEXT,
    insertbackground="white",
    relief="flat",
    font=("Consolas", 10)
)
console.pack(padx=20, pady=(0, 20), fill="both", expand=True)

log("Application initialized")
log("TX ready")
log(f"Receiver MAC = {MAC}")

root.mainloop()