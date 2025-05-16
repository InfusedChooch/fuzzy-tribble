# launcher.py
import tkinter as tk
import pandas as pd
from tkinter import ttk, messagebox
import threading, subprocess, socket, webbrowser, os, sqlite3, json, csv, sys, signal, shutil
from datetime import datetime
from collections import defaultdict
from importlib import import_module
import contextlib

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

    if os.path.exists(bundled_srv):  # EXE version
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

        if current_mode == "main" and IS_WINDOWS:
            log("🛑 CTRL+BREAK …")
            server_process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            log("🛑 Terminating …")
            server_process.terminate()

        server_process.wait(timeout=5)
        log("✅ Server stopped.")
    except Exception as exc:
        log(f"⚠️ {exc} – trying kill()")
        try:
            server_process.kill()
            server_process.wait(timeout=5)
            log("💥 Killed.")
        except Exception as kexc:
            log(f"❌ kill() failed: {kexc}")
    finally:
        server_process = None
        current_mode   = None
        server_pid     = None


def create_routes_tab(notebook, port_var):
    tab = ttk.Frame(notebook)
    notebook.add(tab, text="All Routes")

    btn_frame = ttk.Frame(tab)
    btn_frame.pack(anchor="w", pady=8, padx=8)
    load_btn = ttk.Button(btn_frame, text="Load Routes")
    load_btn.pack(side="left", padx=2)

    outer_frame = ttk.Frame(tab)
    outer_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    canvas = tk.Canvas(outer_frame, background="white")
    canvas.pack(side="left", fill="both", expand=True)

    vbar = ttk.Scrollbar(outer_frame, orient="vertical", command=canvas.yview)
    vbar.pack(side="right", fill="y", padx=(5, 0))

    hbar = ttk.Scrollbar(tab, orient="horizontal", command=canvas.xview)
    hbar.pack(fill="x", padx=10, pady=(0, 10))

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
                    lbl.bind("<Button-1>",
                             lambda e, p=path: webbrowser.open_new_tab(
                                 f"http://127.0.0.1:{port_var.get()}{p}"))
                col += 1

        except Exception as e:
            tk.Label(inner, text=f"Error loading routes: {e}", fg="red").pack(pady=10)

    load_btn.config(command=load_routes)


def render_config_editor_tab(notebook):
    tab = ttk.Frame(notebook)
    notebook.add(tab, text="Config Editor")

    path = os.path.join("data", "config.json")

    fields = [
        ("School Name", "school_name"),
        ("Theme Color (hex)", "theme_color"),
        ("Passes Available", "passes_available"),
        ("Max Pass Time (seconds)", "max_pass_time_seconds"),
        ("Auto Reset Time (HH:MM)", "auto_reset_time"),
        ("Session Timeout (min)", "session_timeout_minutes"),
    ]

    try:
        with open(path, "r") as f:
            config = json.load(f)
    except Exception as e:
        tk.Label(tab, text=f"Failed to load config.json: {e}", fg="red").pack(pady=10)
        return

    widgets = {}
    for label_text, key in fields:
        frame = ttk.Frame(tab)
        frame.pack(anchor="w", padx=10, pady=4)
        ttk.Label(frame, text=label_text, width=25).pack(side="left")
        val = config.get(key, "")
        var = tk.StringVar(value=str(val))
        entry = ttk.Entry(frame, textvariable=var, width=40)
        entry.pack(side="left")
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

    ttk.Button(tab, text="Save Config", command=save_config).pack(pady=10)

def render_rebuild_tab(notebook):
    tab = ttk.Frame(notebook)
    notebook.add(tab, text="Rebuild & Export")
    ttk.Label(tab, text="Rebuild the database from Seed files.", font=("Arial", 10)).pack(pady=(20, 5))

    def trigger_rebuild():
        if server_process:
            messagebox.showwarning("Server running", "Stop the server first.")
            return
        with contextlib.suppress(ImportError):
            wsgi_mod = import_module("wsgi")
            if hasattr(wsgi_mod, "get_app"):
                try:
                    app = wsgi_mod.get_app()
                    with app.app_context():
                        from src.models import db
                        db.session.close_all()
                        db.get_engine().dispose()
                except:
                    pass
        script = os.path.join(os.path.dirname(__file__), "scripts", "rebuild_db.py")
        try:
            subprocess.run([sys.executable, script], check=True)
            messagebox.showinfo("Done", "Database rebuilt.")
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Failed", str(e))

    ttk.Button(tab, text="Rebuild Database", command=trigger_rebuild).pack(pady=10)

    ttk.Label(tab, text="Export current DB to /data/logs/", font=("Arial", 10)).pack(pady=(30, 5))

    def export_from_db():
        db_path = "data/hallpass.db"
        log_dir = "data/logs"
        os.makedirs(log_dir, exist_ok=True)
        today = datetime.now().strftime("%Y%m%d")
        try:
            conn = sqlite3.connect(db_path)
            pd.read_sql("SELECT * FROM audit_log", conn)\
                .to_json(os.path.join(log_dir, f"{today}_audit.json"), orient="records", indent=2)
            pd.read_sql("SELECT id,name,schedule FROM students", conn)\
                .to_csv(os.path.join(log_dir, f"{today}_masterlist.csv"), index=False)
            df_pass = pd.read_sql("SELECT * FROM passes", conn)
            df_log = pd.read_sql("SELECT * FROM pass_log", conn)
            grouped = {}
            for _, p in df_pass.iterrows():
                rec = p.to_dict()
                rec["logs"] = df_log[df_log["pass_id"] == p["id"]][["station", "event_type", "timestamp"]].to_dict("records")
                grouped.setdefault(p["student_id"], []).append(rec)
            with open(os.path.join(log_dir, f"{today}_passlog.json"), "w") as fh:
                json.dump(grouped, fh, indent=2)
            conn.close()
            messagebox.showinfo("Exported", f"Files saved to /data/logs/ with prefix {today}_*")
        except Exception as e:
            messagebox.showerror("Export failed", str(e))

    ttk.Button(tab, text="Export DB → /data/logs/", command=export_from_db).pack(pady=10)

def check_server_health(port_var):
    def _check():
        import urllib.request, time
        global status_var, status_label
        while True:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port_var.get()}/ping", timeout=2):
                    if status_var:
                        status_var.set("Server status: running")
                        status_label.config(fg="green")
            except:
                if status_var:
                    status_var.set("Server status: not responding")
                    status_label.config(fg="red")
            time.sleep(10)
    threading.Thread(target=_check, daemon=True).start()

def build_gui():
    global console_text

    root = tk.Tk()
    icon_path = os.path.join("static", "images", "icon.png")
    if os.path.exists(icon_path):
        try:
            root.iconphoto(True, tk.PhotoImage(file=icon_path))
        except Exception as e:
            print(f"Failed to set window icon: {e}")

    
    root.title("Flask Server Launcher")
    root.geometry("1100x700")
    root.minsize(900, 600)

    notebook = ttk.Notebook(root)

    tab_server = ttk.Frame(notebook)
    notebook.add(tab_server, text="Server")

    port_var = tk.StringVar(value="5000")
    ttk.Label(tab_server, text="Port:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
    ttk.Entry(tab_server, textvariable=port_var, width=8).grid(row=0, column=1, padx=5, pady=5, sticky="w")

    # ─── Schedule Dropdown ───
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

    ttk.Label(tab_server, text="Day Type:").grid(row=0, column=2, padx=10, sticky="e")
    schedule_var = tk.StringVar(value="regular")
    schedule_menu = ttk.Combobox(tab_server, textvariable=schedule_var, state="readonly")
    schedule_menu["values"] = ["regular", "half_day", "delayed"]
    schedule_menu.grid(row=0, column=3, padx=5, sticky="w")
    schedule_menu.bind("<<ComboboxSelected>>", update_schedule_choice)

    ttk.Button(tab_server, text="Launch via WSGI", command=lambda: launch_server("wsgi", port_var.get(), notebook)).grid(row=1, column=0, columnspan=2, pady=4)
    ttk.Button(tab_server, text="Launch via main.py", command=lambda: launch_server("main", port_var.get(), notebook)).grid(row=2, column=0, columnspan=2, pady=4)
    ttk.Button(tab_server, text="Stop Server", command=stop_server).grid(row=3, column=0, columnspan=2, pady=8)
    ttk.Button(tab_server, text="Try to Open", command=lambda: browser(f"http://127.0.0.1:{port_var.get()}")).grid(row=3, column=2, columnspan=2, padx=10, pady=4)

    local = tk.Label(tab_server, text="🌐 Local: http://127.0.0.1:5000", fg="blue", cursor="hand2")
    local.grid(row=4, column=0, columnspan=2, sticky="w", padx=10)
    local.bind("<Button-1>", lambda e: webbrowser.open_new_tab(f"http://127.0.0.1:{port_var.get()}"))

    lan_ip = get_local_ip()
    lan = tk.Label(tab_server, text=f"📡 LAN:   http://{lan_ip}:5000", fg="blue", cursor="hand2")
    status_var = tk.StringVar(value="Server status: unknown")
    status_label = tk.Label(tab_server, textvariable=status_var, font=("Arial", 10))
    status_label.grid(row=6, column=2, sticky="w", padx=10)
    lan.grid(row=5, column=0, columnspan=2, sticky="w", padx=10)
    lan.bind("<Button-1>", lambda e: webbrowser.open_new_tab(f"http://{lan_ip}:{port_var.get()}"))

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

    create_routes_tab(notebook, port_var)
    render_rebuild_tab(notebook)

    notebook.pack(expand=True, fill="both")
    check_server_health(port_var)
    render_config_editor_tab(notebook)
    root.mainloop()

if __name__ == "__main__":
    build_gui()
