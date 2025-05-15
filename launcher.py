import tkinter as tk
import pandas as pd
from tkinter import ttk, messagebox
import threading, subprocess, socket, webbrowser, os, sqlite3, json, csv, sys, signal
from datetime import datetime
from collections import defaultdict
from importlib import import_module
import contextlib

# 1) include vendor in search path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "vendor"))

IS_WINDOWS              = sys.platform.startswith("win")
CREATE_NEW_PROCESS_GROUP = 0x00000200

server_process = None
current_mode   = None
console_text   = None

# ────────────────────── helper shortcuts ───────────────────────
def get_local_ip():
    try:  return socket.gethostbyname(socket.gethostname())
    except: return "Unavailable"

def log(msg):
    if console_text:
        console_text.insert(tk.END, msg + "\n"); console_text.see(tk.END)

def browser(url): webbrowser.open_new_tab(url)


#-------------------------------

def get_exe_path(relative_path):
    base = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base, relative_path)
# ────────────────────── server start/stop ──────────────────────
def launch_server(mode, port, notebook):
    global server_process, current_mode

    if console_text is None:
        messagebox.showerror("Console Not Ready", "Please wait for the GUI to load before launching.")
        return

    if server_process:
        messagebox.showinfo("Already running", "A server is already running.")
        return

    console_text.delete("1.0", tk.END)
    log(f"Launching {mode.upper()} on port {port}…")

    base = os.path.dirname(__file__)
    vpy  = os.path.join(base, "venv", "Scripts", "python.exe")
    wsgi = os.path.join(base, "venv", "Scripts", "waitress-serve.exe")
    cmd  = ([vpy, "-u", os.path.join(base, "main.py")] if mode=="main"
            else [wsgi, "--call", f"--port={port}", "wsgi:get_app"])
    flags = CREATE_NEW_PROCESS_GROUP if (mode=="main" and IS_WINDOWS) else 0

    def stream():
        global server_process
        try:
            server_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, creationflags=flags)
            current_mode = mode
            for line in server_process.stdout: log(line.rstrip())
        except Exception as e:
            log(f"❌ Launch error: {e}"); server_process=None
    threading.Thread(target=stream, daemon=True).start()

def stop_server():
    global server_process, current_mode
    if not server_process: log("ℹ️ No server running."); return
    try:
        if current_mode=="main" and IS_WINDOWS:
            log("🛑 CTRL+BREAK …"); server_process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            log("🛑 Terminating …"); server_process.terminate()
        server_process.wait(timeout=5); log("✅ Server stopped.")
    except Exception as e:
        log(f"⚠️ {e} – kill()"); 
        try: server_process.kill(); server_process.wait(timeout=5); log("💥 Killed.")
        except Exception as k: log(f"❌ kill() failed: {k}")
    finally: server_process=None; current_mode=None

# ────────────────────── ROUTES TAB logic ───────────────────────
def create_routes_tab(notebook, port_var):
    tab = ttk.Frame(notebook)
    notebook.add(tab, text="All Routes")

    btn_frame = ttk.Frame(tab)
    btn_frame.pack(anchor="w", pady=8, padx=8)
    load_btn = ttk.Button(btn_frame, text="Load Routes")
    load_btn.pack(side="left", padx=2)

    # Scrollable area setup
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
        # Expand content if smaller than visible area
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

# ────────────────────── Rebuild / export tab (unchanged) ───────
def render_rebuild_tab(notebook):
    tab = ttk.Frame(notebook); notebook.add(tab, text="Rebuild & Export")
    ttk.Label(tab,text="Rebuild the database from Seed files.",font=("Arial",10)).pack(pady=(20,5))

    def trigger_rebuild():
        if server_process:
            messagebox.showwarning("Server running","Stop the server first."); return
        with contextlib.suppress(ImportError):
            wsgi_mod = import_module("wsgi")
            if hasattr(wsgi_mod,"get_app"):
                try:
                    app=wsgi_mod.get_app()
                    with app.app_context():
                        from src.models import db
                        db.session.close_all(); db.get_engine().dispose()
                except: pass
        script=os.path.join(os.path.dirname(__file__),"scripts","rebuild_db.py")
        vpy=os.path.join(os.path.dirname(__file__),"venv","Scripts","python.exe")
        try: subprocess.run([vpy,script],check=True); messagebox.showinfo("Done","Database rebuilt.")
        except subprocess.CalledProcessError as e: messagebox.showerror("Failed",str(e))

    ttk.Button(tab,text="Rebuild Database",command=trigger_rebuild).pack(pady=10)

    ttk.Label(tab,text="Export current DB to /data/logs/",font=("Arial",10)).pack(pady=(30,5))

    def export_from_db():
        db_path="data/hallpass.db"; log_dir="data/logs"; os.makedirs(log_dir,exist_ok=True)
        today=datetime.now().strftime("%Y%m%d")
        try:
            conn=sqlite3.connect(db_path)
            pd.read_sql("SELECT * FROM audit_log",conn)\
              .to_json(os.path.join(log_dir,f"{today}_audit.json"),orient="records",indent=2)
            pd.read_sql("SELECT id,name,schedule FROM students",conn)\
              .to_csv(os.path.join(log_dir,f"{today}_masterlist.csv"),index=False)
            df_pass=pd.read_sql("SELECT * FROM passes",conn)
            df_log=pd.read_sql("SELECT * FROM pass_log",conn)
            grouped={}
            for _,p in df_pass.iterrows():
                rec=p.to_dict(); rec["logs"]=df_log[df_log["pass_id"]==p["id"]][["station","event_type","timestamp"]].to_dict("records")
                grouped.setdefault(p["student_id"],[]).append(rec)
            with open(os.path.join(log_dir,f"{today}_passlog.json"),"w") as fh:
                json.dump(grouped,fh,indent=2)
            conn.close(); messagebox.showinfo("Exported",f"Files saved to /data/logs/ with prefix {today}_*")
        except Exception as e:
            messagebox.showerror("Export failed",str(e))

    ttk.Button(tab,text="Export DB → /data/logs/",command=export_from_db).pack(pady=10)

# ────────────────────── build GUI ──────────────────────────────
def build_gui():
    global console_text  # ← this line ensures console_text connects to global

    root = tk.Tk()
    root.title("Flask Server Launcher")
    root.geometry("1100x700")
    root.minsize(900, 600)

    notebook = ttk.Notebook(root)

    # Server tab
    tab_server = ttk.Frame(notebook)
    notebook.add(tab_server, text="Server")

    port_var = tk.StringVar(value="5000")
    ttk.Label(tab_server, text="Port:")\
        .grid(row=0, column=0, padx=5, pady=5, sticky="e")
    ttk.Entry(tab_server, textvariable=port_var, width=8)\
        .grid(row=0, column=1, padx=5, pady=5, sticky="w")

    ttk.Button(tab_server, text="Launch via WSGI",
               command=lambda: launch_server("wsgi", port_var.get(), notebook))\
        .grid(row=1, column=0, columnspan=2, pady=4)
    ttk.Button(tab_server, text="Launch via main.py",
               command=lambda: launch_server("main", port_var.get(), notebook))\
        .grid(row=2, column=0, columnspan=2, pady=4)
    ttk.Button(tab_server, text="Stop Server", command=stop_server)\
        .grid(row=3, column=0, columnspan=2, pady=8)

    local = tk.Label(tab_server, text="🌐 Local: http://127.0.0.1:5000",
                     fg="blue", cursor="hand2")
    local.grid(row=4, column=0, columnspan=2, sticky="w", padx=10)
    local.bind("<Button-1>",
               lambda e: webbrowser.open_new_tab(f"http://127.0.0.1:{port_var.get()}"))

    lan_ip = get_local_ip()
    lan = tk.Label(tab_server, text=f"📡 LAN:   http://{lan_ip}:5000",
                   fg="blue", cursor="hand2")
    lan.grid(row=5, column=0, columnspan=2, sticky="w", padx=10)
    lan.bind("<Button-1>",
             lambda e: webbrowser.open_new_tab(f"http://{lan_ip}:{port_var.get()}"))

    # ─── Embedded console log viewer ───
    console_frame = ttk.LabelFrame(tab_server, text="Server Console")
    console_frame.grid(row=6, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")

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

    # Other tabs
    create_routes_tab(notebook, port_var)
    render_rebuild_tab(notebook)

    notebook.pack(expand=True, fill="both")
    root.mainloop()

# ───────────────────────────────────────────────────────────────
if __name__=="__main__": build_gui()
