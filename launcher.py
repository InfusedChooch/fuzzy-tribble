import tkinter as tk
from tkinter import ttk, messagebox, PhotoImage
import threading
import subprocess
import socket
import webbrowser
import os
from collections import defaultdict

server_process = None
current_mode = None
console_window = None
console_text = None

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

def launch_server(mode, port):
    global server_process, current_mode

    if server_process:
        messagebox.showinfo("Already Running", "The server is already running.")
        return

    open_console_window()
    log_to_console(f"Launching {mode.upper()} server on port {port}...")

    cmd = ["python", "-u", "main.py"] if mode == "main" else ["waitress-serve", f"--port={port}", "wsgi:app"]

    def stream_output():
        global server_process
        try:
            server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                text=True
            )
            current_mode = mode
            for line in server_process.stdout:
                log_to_console(line.rstrip())
        except Exception as e:
            log_to_console(f"❌ Error: {str(e)}")
            server_process = None

    threading.Thread(target=stream_output, daemon=True).start()

def stop_server():
    global server_process, current_mode
    if server_process:
        server_process.terminate()
        server_process = None
        current_mode = None
        log_to_console("🛑 Server stopped.")

def discover_routes():
    try:
        from wsgi import app
    except Exception as e:
        messagebox.showerror("Route Load Error", f"Could not load app from wsgi.py:\n{e}")
        return {}

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
    return grouped

def build_gui():
    root = tk.Tk()
    root.title("Flask Server Launcher")

    # Set custom icon
    icon_path = os.path.join("static", "images", "school_logo.png")
    if os.path.exists(icon_path):
        try:
            logo_icon = PhotoImage(file=icon_path)
            root.iconphoto(True, logo_icon)
        except Exception as e:
            print(f"⚠️ Failed to set icon: {e}")
    else:
        print("⚠️ Icon file not found:", icon_path)

    tab_control = ttk.Notebook(root)

    # Server tab
    tab1 = ttk.Frame(tab_control)
    tab_control.add(tab1, text='Server')

    global port_var
    port_var = tk.StringVar(value="5000")

    ttk.Label(tab1, text="Port:").grid(row=0, column=0, padx=5, pady=5)
    ttk.Entry(tab1, textvariable=port_var, width=10).grid(row=0, column=1, padx=5, pady=5)

    ttk.Button(tab1, text="Launch via WSGI", command=lambda: launch_server("wsgi", port_var.get())).grid(row=1, column=0, columnspan=2, pady=5)
    ttk.Button(tab1, text="Launch via main.py", command=lambda: launch_server("main", port_var.get())).grid(row=2, column=0, columnspan=2, pady=5)
    ttk.Button(tab1, text="Stop Server", command=stop_server).grid(row=3, column=0, columnspan=2, pady=5)

    # Clickable URLs
    local_url = tk.Label(tab1, text="🌐 Local: http://127.0.0.1:5000", fg="blue", cursor="hand2")
    local_url.grid(row=4, column=0, columnspan=2, sticky="w", padx=10)
    local_url.bind("<Button-1>", lambda e: open_browser_url(f"http://127.0.0.1:{port_var.get()}"))

    lan_ip = get_local_ip()
    lan_url = tk.Label(tab1, text=f"📡 LAN:   http://{lan_ip}:5000", fg="blue", cursor="hand2")
    lan_url.grid(row=5, column=0, columnspan=2, sticky="w", padx=10)
    lan_url.bind("<Button-1>", lambda e: open_browser_url(f"http://{lan_ip}:{port_var.get()}"))

    # Route tabs
    route_by_module = discover_routes()
    for module, routes in sorted(route_by_module.items()):
        tab = ttk.Frame(tab_control)
        tab_control.add(tab, text=f"{module}.py")
        ttk.Label(tab, text=f"Routes from {module}.py", font=('Arial', 10, 'bold')).pack(pady=5)

        sorted_routes = sorted(routes, key=lambda r: ("GET" not in r[1], r[0]))
        for path, methods, endpoint in sorted_routes:
            label = f"{path} [{methods}]"
            link = tk.Label(tab, text=label, fg="blue", cursor="hand2")
            link.pack(anchor="w", padx=10)
            link.bind("<Button-1>", lambda e, p=path: open_url_embedded(f"http://127.0.0.1:{port_var.get()}{p}"))

    tab_control.pack(expand=1, fill='both')
    root.mainloop()

if __name__ == "__main__":
    build_gui()
