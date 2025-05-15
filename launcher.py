import tkinter as tk
import pandas as pd
from tkinter import ttk, messagebox, PhotoImage
import threading
import subprocess
import socket
import webbrowser
import os
import sqlite3
import json
import csv
from datetime import datetime
from collections import defaultdict
import signal  # Required for CTRL_BREAK_EVENT

server_process = None
current_mode = None
console_window = None
console_text = None

CREATE_NEW_PROCESS_GROUP = 0x00000200  # Windows-only flag

def get_local_ip():
    try:
        return socket.gethostbyname(socket.gethostname())
    except:
        return "Unavailable"

def open_browser_url(url):
    webbrowser.open_new_tab(url)

def open_url_embedded(url):
    try:
        from tkinterweb import HtmlFrame
    except ImportError:
        messagebox.showerror("Missing tkinterweb", "Please run: pip install tkinterweb")
        webbrowser.open_new_tab(url)
        return

    popup = tk.Toplevel()
    popup.title(f"Preview — {url}")
    popup.geometry("900x700")
    frame = HtmlFrame(popup)
    frame.load_website(url)
    frame.pack(fill="both", expand=True)

def open_console_window():
    global console_window, console_text
    if console_window and tk.Toplevel.winfo_exists(console_window):
        return
    console_window = tk.Toplevel()
    console_window.title("Server Console")
    console_window.geometry("700x400")
    console_text = tk.Text(console_window, bg="black", fg="lime", insertbackground="white")
    console_text.pack(fill="both", expand=True)

def log_to_console(msg):
    if console_text:
        console_text.insert(tk.END, msg + "\n")
        console_text.see(tk.END)

def launch_server(mode, port, tab_control):
    global server_process, current_mode

    if server_process:
        messagebox.showinfo("Already Running", "The server is already running.")
        return

    open_console_window()
    log_to_console(f"Launching {mode.upper()} server on port {port}...")

    base = os.path.dirname(__file__)
    venv_python = os.path.join(base, "venv", "Scripts", "python.exe")
    waitress_path = os.path.join(base, "venv", "Scripts", "waitress-serve.exe")

    if mode == "main":
        # Launch main.py in visible cmd window for manual Ctrl+C control
        script_path = os.path.join(base, "main.py")
        cmd = [
            "cmd.exe", "/k",
            f'{venv_python} -u "{script_path}"'
        ]
        creationflags = 0
        log_to_console("🖥️ main.py opened in terminal. Use Ctrl+C there to stop.")
    else:
        # Silent WSGI mode with auto-managed subprocess
        cmd = [waitress_path, "--call", f"--port={port}", "wsgi:get_app"]
        creationflags = 0

    def stream_output():
        global server_process
        try:
            server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE if mode != "main" else None,
                stderr=subprocess.STDOUT if mode != "main" else None,
                bufsize=1,
                text=True,
                creationflags=creationflags
            )
            current_mode = mode
            if mode != "main":
                render_combined_route_tab(tab_control, port)
                if server_process.stdout:
                    for line in server_process.stdout:
                        log_to_console(line.rstrip())
        except Exception as e:
            log_to_console(f"❌ Error: {str(e)}")
            server_process = None

    threading.Thread(target=stream_output, daemon=True).start()

def stop_server():
    global server_process, current_mode
    if server_process:
        try:
            if current_mode == "main":
                log_to_console("🛑 Sending CTRL+BREAK to main.py server...")
                server_process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                log_to_console("🛑 Terminating WSGI server...")
                server_process.terminate()

            server_process.wait(timeout=5)
            log_to_console("✅ Server stopped.")
        except Exception as e:
            log_to_console(f"⚠️ Stop failed: {e}, attempting kill...")
            try:
                server_process.kill()
                server_process.wait(timeout=5)
                log_to_console("💥 Server force-killed.")
            except Exception as kill_e:
                log_to_console(f"❌ Kill also failed: {kill_e}")
        finally:
            server_process = None
            current_mode = None
    else:
        log_to_console("ℹ️ No server is currently running.")


def render_combined_route_tab(parent, port):
    from wsgi import get_app
    app = get_app()

    tab = ttk.Frame(parent)
    parent.add(tab, text='All Routes')

    try:
        grouped = defaultdict(list)
        with app.app_context():
            for rule in app.url_map.iter_rules():
                if rule.rule.startswith("/static"):
                    continue
                endpoint = app.view_functions.get(rule.endpoint)
                if not endpoint:
                    continue
                module_name = endpoint.__module__.split(".")[-1]
                if module_name == "main":
                    continue
                grouped[module_name].append((rule.rule, ",".join(sorted(rule.methods - {"HEAD", "OPTIONS"})), rule.endpoint))

        ttk.Label(tab, text="All Flask Routes", font=('Arial', 10, 'bold')).pack(pady=5)

        scroll_frame = ttk.Frame(tab)
        scroll_frame.pack(fill="both", expand=True)

        canvas = tk.Canvas(scroll_frame, height=500)
        h_scroll = ttk.Scrollbar(scroll_frame, orient="horizontal", command=canvas.xview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(xscrollcommand=h_scroll.set)

        canvas.pack(side="top", fill="both", expand=True)
        h_scroll.pack(side="bottom", fill="x")

        for col, (module, routes) in enumerate(sorted(grouped.items())):
            mod_frame = ttk.LabelFrame(scrollable_frame, text=f"{module}.py")
            mod_frame.grid(row=0, column=col, padx=10, pady=10, sticky="n")

            for i, (path, methods, endpoint) in enumerate(sorted(routes, key=lambda r: r[0])):
                label = f"{path} [{methods}]"
                link = tk.Label(mod_frame, text=label, fg="blue", cursor="hand2", anchor="w", justify="left", wraplength=200)
                link.pack(anchor="w", pady=2)
                link.bind("<Button-1>", lambda e, p=path: open_url_embedded(f"http://127.0.0.1:{port}{p}"))

    except Exception as e:
        label = tk.Label(tab, text=f"Error loading routes: {e}", fg="red")
        label.pack(pady=10)

def render_rebuild_tab(parent):
    tab = ttk.Frame(parent)
    parent.add(tab, text='Rebuild & Export')

    ttk.Label(tab, text="Rebuild the database from Seed files.", font=("Arial", 10)).pack(pady=(20, 5))

    def trigger_rebuild():
        try:
            script_path = os.path.join(os.path.dirname(__file__), "scripts", "rebuild_db.py")
            venv_python = os.path.join(os.path.dirname(__file__), "venv", "Scripts", "python.exe")
            subprocess.run([venv_python, script_path], check=True)
            messagebox.showinfo("Rebuild Complete", "Database successfully rebuilt from Seed.")
        except subprocess.CalledProcessError:
            messagebox.showerror("Rebuild Failed", "Could not rebuild the database.")

    ttk.Button(tab, text="Rebuild Database", command=trigger_rebuild).pack(pady=10)

    ttk.Label(tab, text="Export current DB to /data/logs/ as dated files.", font=("Arial", 10)).pack(pady=(30, 5))

    def export_from_db():
        db_path = os.path.join(os.path.dirname(__file__), "data", "hallpass.db")
        log_dir = os.path.join(os.path.dirname(__file__), "data", "logs")
        os.makedirs(log_dir, exist_ok=True)
        today = datetime.now().strftime("%Y%m%d")

        try:
            conn = sqlite3.connect(db_path)

            df_audit = pd.read_sql("SELECT student_id, reason, time FROM audit_log", conn)
            audit_path = os.path.join(log_dir, f"{today}_auditlog.json")
            df_audit.to_json(audit_path, orient="records", indent=2)

            df_students = pd.read_sql("SELECT id, name, schedule FROM students", conn)
            master_path = os.path.join(log_dir, f"{today}_masterlist.csv")
            df_students.to_csv(master_path, index=False)

            df_pass = pd.read_sql("SELECT * FROM passes", conn)
            df_log = pd.read_sql("SELECT * FROM pass_log", conn)

            grouped = {}
            for _, p in df_pass.iterrows():
                pid = p["id"]
                sid = p["student_id"]
                logs = df_log[df_log["pass_id"] == pid][["station", "event_type", "timestamp"]].to_dict(orient="records")
                p_dict = p.to_dict()
                p_dict["logs"] = logs
                grouped.setdefault(sid, []).append(p_dict)

            passlog_path = os.path.join(log_dir, f"{today}_passlog.json")
            with open(passlog_path, "w") as f:
                json.dump(grouped, f, indent=2)

            conn.close()
            messagebox.showinfo("Export Complete", f"Exported to /data/logs/ as {today}_*.json/.csv")
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

    ttk.Button(tab, text="Export DB → /data/logs/", command=export_from_db).pack(pady=10)

def build_gui():
    root = tk.Tk()
    root.title("Flask Server Launcher")

    icon_path = os.path.join("static", "images", "school_logo.png")
    if os.path.exists(icon_path):
        try:
            logo_icon = PhotoImage(file=icon_path)
            root.iconphoto(True, logo_icon)
        except Exception as e:
            print(f"⚠️ Failed to set icon: {e}")

    tab_control = ttk.Notebook(root)

    tab1 = ttk.Frame(tab_control)
    tab_control.add(tab1, text='Server')

    global port_var
    port_var = tk.StringVar(value="5000")

    ttk.Label(tab1, text="Port:").grid(row=0, column=0, padx=5, pady=5)
    ttk.Entry(tab1, textvariable=port_var, width=10).grid(row=0, column=1, padx=5, pady=5)

    ttk.Button(tab1, text="Launch via WSGI", command=lambda: launch_server("wsgi", port_var.get(), tab_control)).grid(row=1, column=0, columnspan=2, pady=5)
    ttk.Button(tab1, text="Launch via main.py", command=lambda: launch_server("main", port_var.get(), tab_control)).grid(row=2, column=0, columnspan=2, pady=5)
    ttk.Button(tab1, text="Stop Server", command=stop_server).grid(row=3, column=0, columnspan=2, pady=5)

    local_url = tk.Label(tab1, text="🌐 Local: http://127.0.0.1:5000", fg="blue", cursor="hand2")
    local_url.grid(row=4, column=0, columnspan=2, sticky="w", padx=10)
    local_url.bind("<Button-1>", lambda e: open_browser_url(f"http://127.0.0.1:{port_var.get()}"))

    lan_ip = get_local_ip()
    lan_url = tk.Label(tab1, text=f"📡 LAN:   http://{lan_ip}:5000", fg="blue", cursor="hand2")
    lan_url.grid(row=5, column=0, columnspan=2, sticky="w", padx=10)
    lan_url.bind("<Button-1>", lambda e: open_browser_url(f"http://{lan_ip}:{port_var.get()}"))

    render_rebuild_tab(tab_control)
    tab_control.pack(expand=1, fill='both')
    root.mainloop()

if __name__ == "__main__":
    build_gui()
