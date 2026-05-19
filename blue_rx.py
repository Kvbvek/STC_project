import tkinter as tk
from tkinter import scrolledtext
from PIL import Image, ImageTk
from tkinter import filedialog

import threading
import bluetooth
import numpy as np
import matplotlib.pyplot as plt
import wave

# KONFIG
BG = "#0f172a"
CARD = "#162033"
CARD2 = "#0b1120"
TEXT = "#e5e7eb"
SUBTEXT = "#94a3b8"

GREEN = "#22c55e"
RED = "#ef4444"
BLUE = "#3b82f6"
PURPLE = "#8b5cf6"
ORANGE = "#f59e0b"

# STATE
server_sock = None
client_sock = None
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

# RX logic
def start_rx():
    global server_sock, client_sock, running, data_buffer

    if running:
        return

    try:
        data_buffer = []

        set_status("WAITING", BLUE)
        log("Opening RFCOMM server...")

        server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        server_sock.bind(("", 1))
        server_sock.listen(1)

        log("Waiting for connection...")

        def accept_loop():
            global client_sock, running

            try:
                client_sock, addr = server_sock.accept()

                log(f"Connected: {addr[0]}")
                set_status("CONNECTED", GREEN)

                running = True

                while running:
                    try:
                        data = client_sock.recv(4096)

                        if not data:
                            break

                        samples = np.frombuffer(data, dtype=np.int16)
                        data_buffer.append(samples)

                        update_wave(samples)

                    except Exception as e:
                        log(f"Receive ended: {e}")
                        break

            except Exception as e:
                log(f"ERROR: {e}")

            stop_rx()

        threading.Thread(target=accept_loop, daemon=True).start()

    except Exception as e:
        log(f"ERROR: {e}")
        set_status("ERROR", RED)

def stop_rx():
    global running, server_sock, client_sock

    running = False

    try:
        if client_sock:
            client_sock.close()
            client_sock = None
    except:
        pass

    try:
        if server_sock:
            server_sock.close()
            server_sock = None
    except:
        pass

    set_status("STOPPED", RED)
    log("Receiver stopped")

def plot_rx():
    if len(data_buffer) == 0:
        log("No RX data")
        return

    audio = np.concatenate(data_buffer)

    plt.figure(figsize=(12,4))
    plt.plot(audio)
    plt.title("RX waveform")
    plt.xlabel("Sample")
    plt.ylabel("Amplitude")
    plt.grid(True)
    plt.show()

    log("RX waveform plotted")

def save_wav():
    if len(data_buffer) == 0:
        log("No RX data")
        return

    audio = np.concatenate(data_buffer)

    path = filedialog.asksaveasfilename(
        defaultextension=".wav",
        filetypes=[("WAV file", "*.wav")],
        initialfile="received.wav"
    )

    if not path:
        return

    wf = wave.open(path, "wb")
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(44100)
    wf.writeframes(audio.tobytes())
    wf.close()

    log(f"Saved: {path}")

def on_close():
    stop_rx()
    root.destroy()

# ANALYSIS
FS = 44100


def get_audio():
    if len(data_buffer) == 0:
        log("No RX data")
        return None

    return np.concatenate(data_buffer).astype(float)


def plot_fft():
    audio = get_audio()
    if audio is None:
        return

    N = len(audio)

    window = np.hanning(N)
    y = audio * window

    fft = np.fft.rfft(y)
    freq = np.fft.rfftfreq(N, d=1/FS)

    mag = np.abs(fft)
    mag = mag / np.max(mag)

    plt.figure(figsize=(12, 5))
    plt.plot(freq, mag, linewidth=1.5)
    plt.title("FFT Spectrum")
    plt.xlabel("Frequency [Hz]")
    plt.ylabel("Normalized amplitude")
    plt.grid(True)
    plt.xlim(0, FS/2)
    plt.show()

    peak = freq[np.argmax(mag)]
    log(f"FFT peak = {peak:.1f} Hz")


def plot_spectrogram():
    audio = get_audio()
    if audio is None:
        return

    plt.figure(figsize=(12, 5))
    plt.specgram(
        audio,
        Fs=FS,
        NFFT=1024,
        noverlap=512
    )

    plt.title("Spectrogram")
    plt.xlabel("Time [s]")
    plt.ylabel("Frequency [Hz]")
    plt.colorbar(label="Intensity [dB]")
    plt.show()

    log("Spectrogram plotted")


def plot_energy():
    audio = get_audio()
    if audio is None:
        return

    frame = 1024
    rms = []

    for i in range(0, len(audio)-frame, frame):
        chunk = audio[i:i+frame]
        val = np.sqrt(np.mean(chunk**2))
        rms.append(val)

    rms = np.array(rms)
    t = np.arange(len(rms)) * frame / FS

    plt.figure(figsize=(12, 4))
    plt.plot(t, rms, linewidth=2)
    plt.title("Signal Energy (RMS)")
    plt.xlabel("Time [s]")
    plt.ylabel("Amplitude")
    plt.grid(True)
    plt.show()

    log("Energy plotted")

# APP
root = tk.Tk()
root.title("STC Wireless Sound Analyzer - RX")
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
    text="STC Wireless Sound Analyzer [RX]",
    font=("Arial", 28, "bold"),
    fg="white",
    bg=CARD
).pack(pady=(18, 0))

tk.Label(
    center,
    text="Bluetooth Audio Reception & Analysis System",
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
    text="Bluetooth RFCOMM Receiver",
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

make_btn("START RX", GREEN, start_rx).pack(side="left", padx=6)
make_btn("STOP", RED, stop_rx).pack(side="left", padx=6)

make_btn("PLOT RX", PURPLE, plot_rx).pack(side="left", padx=6)
make_btn("FFT", BLUE, plot_fft).pack(side="left", padx=6)
make_btn("SPECTROGRAM", "#0ea5e9", plot_spectrogram).pack(side="left", padx=6)
make_btn("ENERGY", "#14b8a6", plot_energy).pack(side="left", padx=6)

make_btn("SAVE WAV", ORANGE, save_wav).pack(side="left", padx=6)

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
log("RX ready")
log("Waiting for Start RX")

root.mainloop()