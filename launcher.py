# launcher.py
import tkinter as tk
import pandas as pd
import time
from tkinter import ttk, messagebox
import threading, subprocess, socket, webbrowser, os, sqlite3, json, csv, sys, signal, shutil
from datetime import datetime
from collections import defaultdict
from importlib import import_module
import contextlib
from functools import partial

# ─── set‑up ────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "vendor"))

IS_WINDOWS              = sys.platform.startswith("win")
CREATE_NEW_PROCESS_GROUP = 0x00000200
SERVER_EXE_NAME         = "hallpass_server.exe"

server_process = None
current_mode   = None
console_text   = None
status_var     = None
status_label   = None
server_pid     = None

# ─── helpers ───────────────────────────────────────────────────────────────
def get_local_ip():
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "Unavailable"

def log(msg: str):
    if console_text:
        console_text.insert(tk.END, msg + "\n")
        console_text.see(tk.END)

def browser(url: str):
    webbrowser.open_new_tab(url)

def get_exe_path(rel: str):
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, rel)

# ─── audit log tailing ─────────────────────────────────────────────────────
def stream_audit_log():
    log_path = os.path.join("data", "logs", "console_audit.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    if not os.path.exists(log_path):
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("🔍 Audit log initialized.\n")

    def _follow():
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(0, os.SEEK_END)
                while True:
                    line = f.readline()
                    if not line:
                        time.sleep(1)
                        continue
                    if console_text:
                        clean_line = line.replace("â€“", "-").replace("â€”", "-")
                        console_text.insert(tk.END, clean_line)
                        console_text.see(tk.END)
        except Exception as e:
            if console_text:
                console_text.insert(tk.END, f"[Audit tail error] {e}\n")
                console_text.see(tk.END)

    threading.Thread(target=_follow, daemon=True).start()

# ─── launch / stop ─────────────────────────────────────────────────────────
def launch_server(mode: str, port: str, notebook):
    global server_process, current_mode, server_pid

    if console_text is None:
        messagebox.showerror("Console Not Ready", "Please wait for the GUI to load before launching.")
        return
    if server_process and server_process.poll() is None:
        messagebox.showinfo("Already running", "A server is already running.")
        return

    console_text.delete("1.0", tk.END)
    log(f"Launching {mode.upper()} on port {port}…")

    base = os.path.dirname(__file__)
    vpy  = sys.executable
    bundled_srv = os.path.join(os.path.dirname(sys.executable), SERVER_EXE_NAME)

    if os.path.exists(bundled_srv):
        cmd = [bundled_srv, f"--port={port}"]
    else:
        if mode == "main":
            cmd = [vpy, "-u", os.path.join(base, "main.py")]
        else:
            wsgi_cli = shutil.which("waitress-serve")
            if not wsgi_cli:
                log("❌ waitress-serve not found. Install Waitress or bundle hallpass_server.exe.")
                return
            cmd = [wsgi_cli, "--call", f"--port={port}", "wsgi:get_app"]

    flags = CREATE_NEW_PROCESS_GROUP if (mode == "main" and IS_WINDOWS) else 0

    def stream():
        global server_process, current_mode, server_pid
        try:
            server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=flags
            )
            current_mode = mode
            server_pid = server_process.pid
            for line in server_process.stdout:
                log(line.rstrip())
        except Exception as exc:
            log(f"❌ Launch error: {exc}")
            server_process = None
            current_mode   = None
            server_pid     = None

    threading.Thread(target=stream, daemon=True).start()

def stop_server():
    global server_process, current_mode, server_pid

    if not server_process:
        log("ℹ️ No server running.")
        return

    try:
        if server_process.poll() is not None:
            log("ℹ️ Server already exited.")
            server_process = None
            return

        log(f"🛑 Attempting to stop server (PID {server_pid})…")

        if current_mode == "main" and IS_WINDOWS:
            log("🛑 Sending CTRL+BREAK")
            server_process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            log("🛑 Sending terminate()")
            server_process.terminate()

        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            log("⚠️ Terminate timeout -forcing kill()")
            server_process.kill()
            server_process.wait(timeout=5)
            log("💥 Forced kill succeeded.")

        log(f"✅ Server process PID {server_pid} stopped.")

    except Exception as exc:
        log(f"❌ Shutdown error: {exc}")
    finally:
        if server_process and server_process.stdout:
            try:
                server_process.stdout.close()
            except Exception as e:
                log(f"⚠️ Could not close stdout: {e}")

        server_process = None
        current_mode = None
        server_pid = None

# ─── GUI Builder ────────────────────────────────────────────────────────────

# --- Merge of Config Editor + Password Tab ---
def render_settings_tab(notebook):
    tab = ttk.Frame(notebook)
    notebook.add(tab, text="Settings")
    path = os.path.join("data", "config.json")

    try:
        with open(path, "r") as f:
            config = json.load(f)
    except Exception as e:
        tk.Label(tab, text=f"Failed to load config.json: {e}", fg="red").pack(pady=10)
        return

    # --- Config Editor Section ---
    config_frame = ttk.LabelFrame(tab, text="Configuration")
    config_frame.pack(fill="x", padx=10, pady=10)

    fields = [
        ("School Name", "school_name"),
        ("Theme Color (hex)", "theme_color"),
        ("Passes Available", "passes_available"),
        ("Max Pass Time (seconds)", "max_pass_time_seconds"),
        ("Auto Reset Time (HH:MM)", "auto_reset_time"),
        ("Session Timeout (min)", "session_timeout_minutes"),
    ]

    widgets = {}
    for label_text, key in fields:
        frame = ttk.Frame(config_frame)
        frame.pack(anchor="w", padx=10, pady=4)
        ttk.Label(frame, text=label_text, width=25).pack(side="left")
        val = config.get(key, "")
        var = tk.StringVar(value=str(val))
        ttk.Entry(frame, textvariable=var, width=40).pack(side="left")
        widgets[key] = var

    def save_config():
        try:
            for k, var in widgets.items():
                val = var.get().strip()
                if k in ["passes_available", "max_pass_time_seconds", "session_timeout_minutes"]:
                    config[k] = int(val)
                else:
                    config[k] = val
            with open(path, "w") as f:
                json.dump(config, f, indent=2)
            messagebox.showinfo("Saved", "Configuration updated.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    ttk.Button(config_frame, text="Save Config", command=save_config).pack(pady=5)

    # --- Admin Password Section ---
    password_frame = ttk.LabelFrame(tab, text="Change Admin Password")
    password_frame.pack(fill="x", padx=10, pady=10)

    current_var = tk.StringVar()
    new_var     = tk.StringVar()
    confirm_var = tk.StringVar()

    def change_password():
        current = current_var.get().strip()
        new     = new_var.get().strip()
        confirm = confirm_var.get().strip()

        if current != config.get("admin_password"):
            messagebox.showerror("Error", "Current password incorrect.")
            return
        if not new:
            messagebox.showerror("Error", "New password cannot be empty.")
            return
        if new != confirm:
            messagebox.showerror("Error", "New and confirm password do not match.")
            return

        config["admin_password"] = new
        try:
            with open(path, "w") as f:
                json.dump(config, f, indent=2)
            messagebox.showinfo("Success", "Password changed successfully.")
            current_var.set("")
            new_var.set("")
            confirm_var.set("")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

    for label, var in [
        ("Current Password", current_var),
        ("New Password", new_var),
        ("Confirm New Password", confirm_var)
    ]:
        row = ttk.Frame(password_frame)
        row.pack(anchor="w", pady=5, padx=10)
        ttk.Label(row, text=label, width=20).pack(side="left")
        ttk.Entry(row, textvariable=var, show="*", width=30).pack(side="left")

    ttk.Button(password_frame, text="Change Password", command=change_password).pack(pady=10)

# --- Merge of Rebuild + Route Preview ---
def render_maintenance_tab(notebook, port_var):
    tab = ttk.Frame(notebook)
    notebook.add(tab, text="Maintenance")

    # --- Route Preview Section ---
    route_frame = ttk.LabelFrame(tab, text="Flask Routes")
    route_frame.pack(fill="both", expand=True, padx=10, pady=10)

    btn_frame = ttk.Frame(route_frame)
    btn_frame.pack(anchor="w", pady=5)
    load_btn = ttk.Button(btn_frame, text="Load Routes")
    load_btn.pack(side="left", padx=2)

    outer = ttk.Frame(route_frame)
    outer.pack(fill="both", expand=True)

    canvas = tk.Canvas(outer, background="white")
    canvas.pack(side="left", fill="both", expand=True)
    vbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    vbar.pack(side="right", fill="y")
    hbar = ttk.Scrollbar(route_frame, orient="horizontal", command=canvas.xview)
    hbar.pack(fill="x")

    canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)

    inner = ttk.Frame(canvas)
    inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def refresh_inner():
        nonlocal inner, inner_id
        canvas.delete(inner_id)
        inner = ttk.Frame(canvas)
        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")

    def on_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
        if inner.winfo_reqwidth() != canvas.winfo_width():
            canvas.itemconfig(inner_id, width=canvas.winfo_width())

    inner.bind("<Configure>", on_configure)

    def load_routes():
        refresh_inner()
        try:
            from wsgi import get_app
            app = get_app()
            grouped = defaultdict(list)
            with app.app_context():
                for r in app.url_map.iter_rules():
                    if r.rule.startswith("/static"):
                        continue
                    endpoint = app.view_functions.get(r.endpoint)
                    if not endpoint:
                        continue
                    mod = endpoint.__module__.split(".")[-1]
                    grouped[mod].append((r.rule, ",".join(sorted(r.methods - {"HEAD", "OPTIONS"}))))

            col = 0
            for mod, routes in sorted(grouped.items()):
                lf = ttk.LabelFrame(inner, text=f"{mod}.py")
                lf.grid(row=0, column=col, padx=10, pady=10, sticky="n")
                for path, methods in sorted(routes):
                    lbl = tk.Label(
                        lf, text=f"{path} [{methods}]",
                        fg="blue", cursor="hand2",
                        anchor="w", justify="left", wraplength=200
                    )
                    lbl.pack(anchor="w", pady=1)
                    lbl.bind("<Button-1>", lambda e, p=path: webbrowser.open_new_tab(
                        f"http://127.0.0.1:{port_var.get()}{p}"))
                col += 1
        except Exception as e:
            tk.Label(inner, text=f"Error loading routes: {e}", fg="red").pack(pady=10)

    load_btn.config(command=load_routes)

    # --- Rebuild Section ---
    def run_split_masterlist():
        script = os.path.join(os.path.dirname(__file__), "scripts", "build_student_periods.py")
        try:
            subprocess.run([sys.executable, script], check=True)
            messagebox.showinfo("Done", "Masterlist split into CSVs.")
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Failed", f"Split failed: {str(e)}")

    def trigger_rebuild():
        if server_process:
            messagebox.showwarning("Server running", "Stop the server first.")
            return
        script = os.path.join(os.path.dirname(__file__), "scripts", "rebuild_db.py")
        try:
            subprocess.run([sys.executable, script], check=True)
            messagebox.showinfo("Done", "Database rebuilt.")
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Failed", str(e))

    def export_from_db():
        try:
            db_path = "data/hallpass.db"
            log_dir = "data/logs"
            os.makedirs(log_dir, exist_ok=True)
            today = datetime.now().strftime("%Y%m%d")
            conn = sqlite3.connect(db_path)

            tables = ["users", "student_periods", "passes", "pass_events", "audit_log", "active_rooms"]
            for table in tables:
                df = pd.read_sql(f"SELECT * FROM {table}", conn)
                df.to_csv(os.path.join(log_dir, f"{today}_{table}.csv"), index=False)

            df_passes = pd.read_sql("SELECT * FROM passes", conn)
            df_events = pd.read_sql("SELECT * FROM pass_events", conn)
            grouped = {}
            for _, p in df_passes.iterrows():
                rec = p.to_dict()
                rec["logs"] = df_events[df_events["pass_id"] == p["id"]][["station", "event", "timestamp"]].to_dict("records")
                grouped.setdefault(p["student_id"], []).append(rec)

            with open(os.path.join(log_dir, f"{today}_passlog.json"), "w") as fh:
                json.dump(grouped, fh, indent=2)

            conn.close()
            messagebox.showinfo("Exported", f"✅ Exported tables + JSON to /data/logs/")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))

    tools_frame = ttk.LabelFrame(tab, text="Database Tools")
    tools_frame.pack(fill="x", padx=10, pady=10)
    ttk.Label(tools_frame, text="Pre-process Seed Files").pack(pady=5)
    ttk.Button(tools_frame, text="Split Masterlist", command=run_split_masterlist).pack(pady=2)
    ttk.Button(tools_frame, text="Rebuild Database", command=trigger_rebuild).pack(pady=5)
    ttk.Label(tools_frame, text="Export DB to /data/logs/").pack(pady=(10, 5))
    ttk.Button(tools_frame, text="Export DB", command=export_from_db).pack(pady=2)


# ─── Main Entry ─────────────────────────────────────────────────────────────
def build_gui():
    global console_text

    root = tk.Tk()
    icon_path = os.path.join("static", "images", "icon.png")
    if os.path.exists(icon_path):
        try:
            root.iconphoto(True, tk.PhotoImage(file=icon_path))
        except Exception as e:
            print(f"Failed to set window icon: {e}")

    root.title("Server Launcher")
    root.geometry("1100x700")
    root.minsize(900, 600)

    notebook = ttk.Notebook(root)
    tab_server = ttk.Frame(notebook)
    notebook.add(tab_server, text="Server")

    port_var = tk.StringVar(value="5000")
    ttk.Label(tab_server, text="Port:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
    ttk.Entry(tab_server, textvariable=port_var, width=8).grid(row=0, column=1, padx=5, pady=5, sticky="w")

    ttk.Label(tab_server, text="Day Type:").grid(row=0, column=2, padx=10, sticky="e")
    schedule_var = tk.StringVar(value="regular")
    schedule_menu = ttk.Combobox(tab_server, textvariable=schedule_var, state="readonly")
    schedule_menu["values"] = ["regular", "half_day", "delayed"]
    schedule_menu.grid(row=0, column=3, padx=5, sticky="w")

    def update_schedule_choice(event=None):
        selected = schedule_var.get()
        try:
            with open("data/config.json", "r") as f:
                cfg = json.load(f)
            cfg["active_schedule"] = selected
            with open("data/config.json", "w") as f:
                json.dump(cfg, f, indent=2)
            log(f"📅 Schedule switched to: {selected}")
        except Exception as e:
            log(f"⚠️ Failed to update schedule: {e}")

    schedule_menu.bind("<<ComboboxSelected>>", update_schedule_choice)

    ttk.Button(tab_server, text="Launch via WSGI", command=lambda: launch_server("wsgi", port_var.get(), notebook)).grid(row=1, column=0, columnspan=2, pady=4)
    ttk.Button(tab_server, text="Launch via main.py", command=lambda: launch_server("main", port_var.get(), notebook)).grid(row=2, column=0, columnspan=2, pady=4)
    ttk.Button(tab_server, text="Stop Server", command=stop_server).grid(row=3, column=0, columnspan=2, pady=8)
    ttk.Button(tab_server, text="Try to Open", command=lambda: browser(f"http://127.0.0.1:{port_var.get()}")).grid(row=3, column=2, columnspan=2, padx=10, pady=4)

    local = tk.Label(tab_server, text="🌐 Local: http://127.0.0.1:5000", fg="blue", cursor="hand2")
    local.grid(row=4, column=0, columnspan=2, sticky="w", padx=10)
    local.bind("<Button-1>", lambda e: browser(f"http://127.0.0.1:{port_var.get()}"))

    lan_ip = get_local_ip()
    lan = tk.Label(tab_server, text=f"📡 LAN:   http://{lan_ip}:5000", fg="blue", cursor="hand2")
    lan.grid(row=5, column=0, columnspan=2, sticky="w", padx=10)
    lan.bind("<Button-1>", lambda e: browser(f"http://{lan_ip}:{port_var.get()}"))

    status_var = tk.StringVar(value="Server status: unknown")
    status_label = tk.Label(tab_server, textvariable=status_var, font=("Arial", 10))
    status_label.grid(row=6, column=2, sticky="w", padx=10)

    console_frame = ttk.LabelFrame(tab_server, text="Server Console")
    console_frame.grid(row=6, column=0, columnspan=4, padx=10, pady=10, sticky="nsew")

    console_scroll = ttk.Scrollbar(console_frame)
    console_scroll.pack(side="right", fill="y")

    console_text = tk.Text(
        console_frame,
        bg="black", fg="lime", insertbackground="white",
        wrap="none", yscrollcommand=console_scroll.set, height=20
    )
    console_text.pack(fill="both", expand=True)
    console_scroll.config(command=console_text.yview)

    tab_server.rowconfigure(6, weight=1)
    tab_server.columnconfigure(0, weight=1)

    notebook.pack(expand=True, fill="both")

    render_maintenance_tab(notebook, port_var)
    render_settings_tab(notebook)

    def check_server_health():
        import urllib.request
        while True:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port_var.get()}/ping", timeout=2):
                    status_var.set("Server status: running")
                    status_label.config(fg="green")
            except:
                status_var.set("Server status: not responding")
                status_label.config(fg="red")
            time.sleep(10)

    threading.Thread(target=check_server_health, daemon=True).start()

    stream_audit_log()

    def on_close():
        stop_server()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()

if __name__ == "__main__":
    build_gui()
