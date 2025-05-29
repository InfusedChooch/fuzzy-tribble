# launcher.py
# GUI launcher for TJMS Hall-Pass server — CustomTkinter edition
#
# ▸ Requires: pip install customtkinter
#   (works on the PyPI release; dev-only widgets are gracefully downgraded)
# ------------------------------------------------------------------------------

import sys, os, time, json, subprocess, threading, socket, shutil, sqlite3, signal, webbrowser, pandas as pd
from datetime import datetime
from collections import defaultdict
import customtkinter as ctk

# ── global theme ────────────────────────────────────────────────────────────
ctk.set_appearance_mode("system")      # "light" | "dark" | "system"
ctk.set_default_color_theme("blue")    # "blue" | "green" | "dark-blue"

# ── cross-version message-box helper ────────────────────────────────────────
try:
    # dev branch
    from customtkinter import CTkMessagebox as _MsgBox

    def msgbox(title, message, icon="info"):
        _MsgBox(title=title, message=message, icon=icon)

except (ImportError, AttributeError):
    # stable release fallback
    from tkinter import messagebox as _tkmsg

    def msgbox(title, message, icon="info"):
        if icon in ("check", "info"):
            _tkmsg.showinfo(title, message)
        elif icon == "warning":
            _tkmsg.showwarning(title, message)
        else:
            _tkmsg.showerror(title, message)


IS_WINDOWS              = sys.platform.startswith("win")
CREATE_NEW_PROCESS_GROUP = 0x00000200
SERVER_EXE_NAME         = "hallpass_server.exe"

server_process = None
current_mode   = None
console_widget = None
status_var     = None
server_pid     = None

# ── helpers ─────────────────────────────────────────────────────────────────
def get_local_ip():
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "Unavailable"

def log(msg: str):
    if console_widget:
        console_widget.configure(state="normal")
        console_widget.insert("end", msg + "\n")
        console_widget.see("end")
        console_widget.configure(state="disabled")

def browser(url: str):
    webbrowser.open_new_tab(url)

# ── audit-log tail ──────────────────────────────────────────────────────────
def stream_audit_log():
    log_path = os.path.join("data", "logs", "console_audit.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    if not os.path.exists(log_path):
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("🔍 Audit log initialized.\n")

    def _follow():
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            f.seek(0, os.SEEK_END)
            while True:
                line = f.readline()
                if not line:
                    time.sleep(1)
                    continue
                log(line.replace("â€“", "-").replace("â€”", "-"))
    threading.Thread(target=_follow, daemon=True).start()

# ── launch / stop server ────────────────────────────────────────────────────
def launch_server(mode: str, port: str):
    global server_process, current_mode, server_pid
    if console_widget is None:
        msgbox("Wait", "GUI not ready yet", icon="warning")
        return
    if server_process and server_process.poll() is None:
        msgbox("Running", "Server already running", icon="warning")
        return

    console_widget.configure(state="normal")
    console_widget.delete("1.0", "end")
    console_widget.configure(state="disabled")
    log(f"Launching {mode.upper()} on port {port} …")

    base = os.path.dirname(__file__)
    vpy  = sys.executable
    bundled = os.path.join(os.path.dirname(sys.executable), SERVER_EXE_NAME)

    if os.path.exists(bundled):
        cmd = [bundled, f"--port={port}"]
    elif mode == "main":
        cmd = [vpy, "-u", os.path.join(base, "main.py")]
    else:
        wsgi_cli = shutil.which("waitress-serve")
        if not wsgi_cli:
            log("❌ waitress-serve not found.")
            return
        cmd = [wsgi_cli, "--call", "--port", port, "wsgi:get_app"]

    flags = CREATE_NEW_PROCESS_GROUP if (mode == "main" and IS_WINDOWS) else 0

    def _stream():
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, creationflags=flags
            )
            globals().update(server_process=proc, current_mode=mode, server_pid=proc.pid)
            for line in proc.stdout:
                log(line.rstrip())
        except Exception as exc:
            log(f"❌ Launch error: {exc}")
            globals().update(server_process=None, current_mode=None, server_pid=None)
    threading.Thread(target=_stream, daemon=True).start()

def stop_server():
    global server_process, current_mode, server_pid
    if not server_process:
        log("ℹ️ No server running.")
        return
    try:
        log(f"🛑 Stopping server (PID {server_pid})…")
        if current_mode == "main" and IS_WINDOWS:
            server_process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            server_process.terminate()
        server_process.wait(timeout=5)
        log("✅ Server stopped.")
    except Exception as e:
        log(f"❌ Shutdown error: {e}")
    finally:
        server_process = current_mode = server_pid = None

# ── SETTINGS TAB ────────────────────────────────────────────────────────────
def render_settings_tab(notebook: ctk.CTkTabview):
    tab = notebook.add("Settings")
    path = os.path.join("data", "config.json")
    try:
        with open(path, "r") as f:
            config = json.load(f)
    except Exception as e:
        ctk.CTkLabel(tab, text=f"Failed to load config.json: {e}", text_color="red").pack(pady=10)
        return

    def titled(parent, title):
        frame = ctk.CTkFrame(parent)
        ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(weight="bold")
                     ).pack(anchor="w", pady=(0, 4))
        return frame

    # config editor
    edit = titled(tab, "Configuration")
    edit.pack(fill="x", padx=20, pady=10)
    fields = [
        ("School Name", "school_name"),
        ("Theme Colour (hex)", "theme_color"),
        ("Passes Available", "passes_available"),
        ("Max Pass Time (seconds)", "max_pass_time_seconds"),
        ("Auto Reset Time (HH:MM)", "auto_reset_time"),
        ("Session Timeout (minutes)", "session_timeout_minutes"),
    ]
    vars: dict[str, ctk.StringVar] = {}
    for lbl, key in fields:
        row = ctk.CTkFrame(edit, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=lbl, width=190, anchor="w").pack(side="left")
        v = ctk.StringVar(value=str(config.get(key, "")))
        vars[key] = v
        ctk.CTkEntry(row, textvariable=v, width=250).pack(side="left", padx=4)

    def save():
        try:
            for k, v in vars.items():
                val = v.get().strip()
                config[k] = int(val) if k in {"passes_available","max_pass_time_seconds","session_timeout_minutes"} else val
            with open(path, "w") as f:
                json.dump(config, f, indent=2)
            msgbox("Saved", "Configuration updated.", icon="check")
        except Exception as e:
            msgbox("Error", str(e), icon="cancel")
    ctk.CTkButton(edit, text="💾 Save Config", command=save).pack(pady=6)

    # admin password
    pw = titled(tab, "Change Admin Password")
    pw.pack(fill="x", padx=20, pady=8)
    cur, new, conf = ctk.StringVar(), ctk.StringVar(), ctk.StringVar()
    for name, var in [("Current",cur),("New",new),("Confirm",conf)]:
        row = ctk.CTkFrame(pw, fg_color="transparent"); row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=f"{name} Password", width=140, anchor="w").pack(side="left")
        ctk.CTkEntry(row, show="*", textvariable=var, width=230).pack(side="left", padx=4)
    def change_pw():
        if cur.get().strip() != config.get("admin_password"):
            msgbox("Error", "Current password incorrect", icon="cancel"); return
        if not new.get():
            msgbox("Error", "New password empty", icon="cancel"); return
        if new.get() != conf.get():
            msgbox("Error", "Passwords do not match", icon="cancel"); return
        config["admin_password"] = new.get()
        with open(path, "w") as f: json.dump(config, f, indent=2)
        msgbox("Done", "Password changed.", icon="check")
        cur.set(""); new.set(""); conf.set("")
    ctk.CTkButton(pw, text="Update Password", command=change_pw).pack(pady=5)

# ── MAINTENANCE TAB ─────────────────────────────────────────────────────────
def render_maintenance_tab(notebook: ctk.CTkTabview, port_var: ctk.StringVar):
    tab = notebook.add("Maintenance")

    def titled(parent, title):
        frame = ctk.CTkFrame(parent)
        ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0,4))
        return frame

    # routes
    routes_box = titled(tab, "Flask Routes ⤵ click to open")
    routes_box.pack(fill="both", expand=True, padx=20, pady=10)
    scroll = ctk.CTkScrollableFrame(routes_box, height=220)
    scroll.pack(fill="both", expand=True, padx=6, pady=6)

    def load_routes():
        for w in scroll.winfo_children(): w.destroy()
        try:
            from wsgi import get_app
            app = get_app()
            grouped = defaultdict(list)
            with app.app_context():
                for r in app.url_map.iter_rules():
                    if r.rule.startswith("/static"): continue
                    endpoint = app.view_functions.get(r.endpoint)
                    mod = endpoint.__module__.split(".")[-1] if endpoint else "other"
                    grouped[mod].append((r.rule, ",".join(sorted(r.methods-{"HEAD","OPTIONS"}))))
            col=0
            for mod, lst in sorted(grouped.items()):
                col_frame = ctk.CTkFrame(scroll)
                col_frame.grid(row=0, column=col, padx=8, sticky="n")
                ctk.CTkLabel(col_frame, text=f"{mod}.py", font=ctk.CTkFont(weight="bold")).pack(anchor="w")
                for p, m in sorted(lst):
                    link = ctk.CTkLabel(col_frame, text=f"{p} [{m}]", text_color="dodgerblue",
                                        cursor="hand2", anchor="w")
                    link.pack(anchor="w")
                    link.bind("<Button-1>",
                              lambda e, pa=p: browser(f"http://127.0.0.1:{port_var.get()}{pa}"))
                col += 1
        except Exception as e:
            ctk.CTkLabel(scroll, text=f"Error: {e}", text_color="red").pack()
    ctk.CTkButton(routes_box, text="↻ Load Routes", command=load_routes).pack(pady=4)

    # db tools
    tools = titled(tab, "Database Tools")
    tools.pack(fill="x", padx=20, pady=10)
    def run_script(pyfile, done):
        script = os.path.join(os.path.dirname(__file__), "scripts", pyfile)
        try:
            subprocess.run([sys.executable, script], check=True)
            msgbox("Done", done, icon="check")
        except subprocess.CalledProcessError as e:
            msgbox("Error", str(e), icon="cancel")
    ctk.CTkButton(tools, text="✂ Split Masterlist",
                  command=lambda: run_script("build_student_periods.py","Masterlist split.")
                  ).pack(pady=3)
    ctk.CTkButton(tools, text="🗄 Rebuild Database",
                  command=lambda: run_script("rebuild_db.py","Database rebuilt.")
                  ).pack(pady=3)

    def export_db():
        try:
            db_path, log_dir = "data/hallpass.db", "data/logs"
            os.makedirs(log_dir, exist_ok=True)
            today = datetime.now().strftime("%Y%m%d")
            conn = sqlite3.connect(db_path)
            for tbl in ["users","student_periods","passes","pass_events","audit_log","active_rooms"]:
                pd.read_sql(f"SELECT * FROM {tbl}", conn).to_csv(
                    os.path.join(log_dir, f"{today}_{tbl}.csv"), index=False)
            # nested JSON
            dfp = pd.read_sql("SELECT * FROM passes", conn)
            dfe = pd.read_sql("SELECT * FROM pass_events", conn)
            grouped={}
            for _, p in dfp.iterrows():
                rec = p.to_dict()
                rec["logs"] = dfe[dfe.pass_id == p.id][["station","event","timestamp"]].to_dict("records")
                grouped.setdefault(p.student_id, []).append(rec)
            with open(os.path.join(log_dir, f"{today}_passlog.json"), "w") as fh:
                json.dump(grouped, fh, indent=2)
            conn.close()
            msgbox("Export", "CSV + JSON written to /data/logs", icon="check")
        except Exception as e:
            msgbox("Error", str(e), icon="cancel")
    ctk.CTkButton(tools, text="⬇ Export DB", command=export_db).pack(pady=3)

# ── MAIN GUI ────────────────────────────────────────────────────────────────
def build_gui():
    global console_widget, status_var
    root = ctk.CTk()
    root.title("Hall-Pass Server Launcher")
    root.geometry("1080x680")
    root.minsize(960,540)
    ico = os.path.join("static", "images", "icon.png")
    if os.path.exists(ico):
        try: root.iconphoto(True, ctk.CTkImage(file=ico))
        except: pass

    top = ctk.CTkFrame(root); top.pack(fill="x", pady=8, padx=10)
    port_var = ctk.StringVar(value="5000")
    ctk.CTkLabel(top, text="Port").pack(side="left", padx=(5,2))
    ctk.CTkEntry(top, textvariable=port_var, width=70).pack(side="left", padx=(0,6))
    ctk.CTkButton(top, text="Launch (WSGI)", command=lambda: launch_server("wsgi", port_var.get())
                  ).pack(side="left", padx=2)
    ctk.CTkButton(top, text="Launch (main.py)", command=lambda: launch_server("main", port_var.get())
                  ).pack(side="left", padx=2)
    ctk.CTkButton(top, text="Stop", command=stop_server).pack(side="left", padx=2)
    ctk.CTkButton(top, text="Open Browser",
                  command=lambda: browser(f"http://127.0.0.1:{port_var.get()}")).pack(side="left", padx=2)

    day_var = ctk.StringVar(value="regular")
    def save_day(*_):
        try:
            with open("data/config.json") as f: cfg=json.load(f)
            cfg["active_schedule"] = day_var.get()
            with open("data/config.json","w") as f: json.dump(cfg,f,indent=2)
            log(f"📅 Schedule set: {day_var.get()}")
        except Exception as e:
            log(f"⚠️ Failed to save schedule: {e}")
    ctk.CTkOptionMenu(top, variable=day_var, values=["regular","half_day","delayed"], command=save_day
                      ).pack(side="right", padx=6)
    ctk.CTkLabel(top, text="Day Type").pack(side="right")

    # links + status
    links = ctk.CTkFrame(root, fg_color="transparent"); links.pack(fill="x", padx=10)
    local = ctk.CTkLabel(links, text="🌐 Local: http://127.0.0.1", text_color="dodgerblue",
                         cursor="hand2"); local.pack(side="left", padx=4)
    local.bind("<Button-1>", lambda e: browser(f"http://127.0.0.1:{port_var.get()}"))
    lan_ip = get_local_ip()
    lan = ctk.CTkLabel(links, text=f"📡 LAN: http://{lan_ip}", text_color="dodgerblue",
                       cursor="hand2"); lan.pack(side="left", padx=4)
    lan.bind("<Button-1>", lambda e: browser(f"http://{lan_ip}:{port_var.get()}"))
    status_var = ctk.StringVar(value="⏳ status: unknown")
    ctk.CTkLabel(links, textvariable=status_var).pack(side="right", padx=6)

    notebook = ctk.CTkTabview(root); notebook.pack(fill="both", expand=True, padx=10, pady=6)
    serv_tab = notebook.add("Server")
    console_widget = ctk.CTkTextbox(serv_tab, wrap="none", state="disabled"
                                    ); console_widget.pack(fill="both", expand=True, padx=10, pady=10)

    render_maintenance_tab(notebook, port_var)
    render_settings_tab(notebook)

    def health():
        import urllib.request
        while True:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port_var.get()}/ping", timeout=2):
                    status_var.set("✅ server running")
            except:
                status_var.set("❌ not responding")
            time.sleep(10)
    threading.Thread(target=health, daemon=True).start()
    stream_audit_log()

    root.protocol("WM_DELETE_WINDOW", lambda: (stop_server(), root.destroy()))
    root.mainloop()

if __name__ == "__main__":
    build_gui()
