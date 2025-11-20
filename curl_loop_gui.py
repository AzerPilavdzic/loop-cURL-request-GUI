#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import tkinter as tk
from tkinter import messagebox, scrolledtext

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CURL_FILE = os.path.join(SCRIPT_DIR, "mycurl.txt")
LOGS_DIR = os.path.join(SCRIPT_DIR, "logs")
LOG_FILE = os.path.join(LOGS_DIR, "curl_I_provided.log")
loop_process = None

def ensure_dirs():
    os.makedirs(LOGS_DIR, exist_ok=True)


def run_curl_once(curl_cmd: str) -> str:
    # always enforce silent mode (remove existing -s to avoid duplication)
    curl_cmd = curl_cmd.replace(" -s ", " ").replace(" -s", "")
    curl_cmd = curl_cmd.replace("-s ", "").replace("-s", "")

    curl_cmd = f"{curl_cmd} -s"   # add silent mode
    
    try:
        output = subprocess.check_output(
            curl_cmd,
            shell=True,
            stderr=subprocess.STDOUT,
            text=True,
        )
        return output.strip()
    except subprocess.CalledProcessError as e:
        return e.output.strip() if e.output else f"curl failed with code {e.returncode}"

def notify(title: str, body: str):
    """
    Send desktop notification using notify-send (Linux).
    If notify-send is not available, silently ignore errors.
    """
    try:
        preview = body[:300] + ("..." if len(body) > 300 else "")
        subprocess.Popen(["notify-send", title, preview])
    except Exception:
        pass


def append_log(text: str):
    ensure_dirs()
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{ts} - {text}\n")


# ------------------ LOOP MODE (background worker) ------------------ #

def run_loop_mode(interval_seconds: int):
    ensure_dirs()
    while True:
        if not os.path.isfile(CURL_FILE):
            msg = f"Error: {CURL_FILE} not found!"
            append_log(msg)
            notify("cURL Loop Error", msg)
            time.sleep(interval_seconds)
            continue

        # Read curl command from file each time (like any_curl.sh did)
        with open(CURL_FILE, "r", encoding="utf-8") as f:
            curl_cmd = f.read().strip()

        if not curl_cmd:
            msg = "Empty cURL command in mycurl.txt"
            append_log(msg)
            notify("cURL Loop Error", msg)
            time.sleep(interval_seconds)
            continue

        response = run_curl_once(curl_cmd)
        append_log(response)
        notify("API Response", response)

        time.sleep(interval_seconds)


# ------------------ GUI MODE ------------------ #

def start_from_gui(curl_text_widget, minutes_entry):
    global loop_process

    curl_cmd = curl_text_widget.get("1.0", tk.END).strip()
    minutes_str = minutes_entry.get().strip()

    if not curl_cmd:
        messagebox.showerror("Error", "Please enter a cURL command.")
        return

    try:
        minutes = int(minutes_str)
        if minutes <= 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Error", "Minutes must be a positive integer.")
        return

    interval_seconds = minutes * 1

    # Save cURL to mycurl.txt
    with open(CURL_FILE, "w", encoding="utf-8") as f:
        f.write(curl_cmd)

    # Run once immediately (notify + log)
    response = run_curl_once(curl_cmd)
    append_log(response)
    notify("First cURL Response", response)

    # Start background loop
    loop_process = subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), "--loop", str(interval_seconds)],
        cwd=SCRIPT_DIR
    )

    messagebox.showinfo(
        "Started",
        f"Loop running every {minutes} minutes.\n"
        f"Log file: {LOG_FILE}"
    )



def run_gui_mode():
    global loop_process

    ensure_dirs()
    root = tk.Tk()
    root.title("cURL Loop Launcher (Python)")

    # Close handler
    def on_close():
        global loop_process
        if loop_process is not None:
            try:
                loop_process.terminate()
            except Exception:
                pass
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    # UI elements
    tk.Label(root, text="cURL command:").grid(row=0, column=0, sticky="nw", padx=5, pady=5)
    curl_text = scrolledtext.ScrolledText(root, width=80, height=10)
    curl_text.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(root, text="Interval (minutes):").grid(row=1, column=0, sticky="e", padx=5, pady=5)
    minutes_entry = tk.Entry(root, width=10)
    minutes_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)
    minutes_entry.insert(0, "1")

    start_button = tk.Button(
        root,
        text="Save & Start Loop",
        command=lambda: start_from_gui(curl_text, minutes_entry),
    )
    start_button.grid(row=2, column=0, columnspan=2, pady=10)

    root.mainloop()


if __name__ == "__main__":
    # If started with: python3 curl_loop_gui.py --loop 60
    if len(sys.argv) >= 3 and sys.argv[1] == "--loop":
        try:
            sec = int(sys.argv[2])
        except ValueError:
            sec = 60
        run_loop_mode(sec)
    else:
        run_gui_mode()

