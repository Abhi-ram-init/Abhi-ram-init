import os
import sys
import time
import tkinter as tk
import threading
import psutil
from PIL import Image, ImageTk

# Helper to find assets under PyInstaller temp dir or local directory
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

class GTRMonitorApp:
    def __init__(self):
        # 1. Tkinter Window Setup
        self.root = tk.Tk()
        self.root.title("System Monitor")
        
        # Frameless and transparent setup
        self.root.overrideredirect(True)
        self.root.attributes("-transparentcolor", "#00ff00")
        self.root.attributes("-topmost", True)
        
        # Force window to appear in taskbar
        self.root.after(100, self.set_appwindow)
        
        # Center on screen initially or place at bottom-right
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        # Place 40 pixels from bottom right
        self.root.geometry(f"200x140+{screen_w - 240}+{screen_h - 200}")
        
        # 2. State Variables
        self.running = True
        self.visible = True
        self.target_cpu = 0.0
        self.target_ram = 0.0
        self.display_cpu = 0.0
        self.display_ram = 0.0
        
        # Dragging variables
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        # 3. Create UI Elements on Canvas
        self.canvas = tk.Canvas(self.root, width=200, height=140, bg="#00ff00", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # Draw Glassmorphic Rounded Card Background (Neon accent ring)
        self.draw_rounded_card(10, 10, 190, 130, 16, "#0f0f13", "#22222d", width=2)
        
        # Draw Close Button (hides to tray)
        self.close_btn = self.canvas.create_text(
            175, 25, text="×", font=("Segoe UI", 14, "bold"), fill="#60606b", activefill="#ff4a4a"
        )
        self.canvas.tag_bind(self.close_btn, "<Button-1>", lambda e: self.hide_window())
        
        # Setup Dials for CPU & RAM
        self.setup_dials()
        
        # Bind Drag events to the canvas
        self.canvas.bind("<Button-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag_window)
        
        # 4. Start System Tray Icon
        self.icon = None
        self.tray_thread = threading.Thread(target=self.setup_tray, daemon=True)
        self.tray_thread.start()
        
        # 5. Start Metric Polling Thread
        self.metrics_thread = threading.Thread(target=self.poll_metrics, daemon=True)
        self.metrics_thread.start()
        
        # 6. Start Animation Loop
        self.last_time = time.time()
        self.animate()
        
        # Handle protocol close to hide instead of exit
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

    def draw_rounded_card(self, x1, y1, x2, y2, r, fill, outline, width=1):
        # Draw solid corners
        self.canvas.create_arc(x1, y1, x1+2*r, y1+2*r, start=90, extent=90, fill=fill, outline="", style="pieslice")
        self.canvas.create_arc(x2-2*r, y1, x2, y1+2*r, start=0, extent=90, fill=fill, outline="", style="pieslice")
        self.canvas.create_arc(x2-2*r, y2-2*r, x2, y2, start=270, extent=90, fill=fill, outline="", style="pieslice")
        self.canvas.create_arc(x1, y2-2*r, x1+2*r, y2, start=180, extent=90, fill=fill, outline="", style="pieslice")
        
        # Fill rectangles
        self.canvas.create_rectangle(x1+r, y1, x2-r, y2, fill=fill, outline="")
        self.canvas.create_rectangle(x1, y1+r, x2, y2-r, fill=fill, outline="")
        
        # Draw crisp outline borders
        if outline:
            self.canvas.create_arc(x1, y1, x1+2*r, y1+2*r, start=90, extent=90, outline=outline, width=width, style="arc")
            self.canvas.create_arc(x2-2*r, y1, x2, y1+2*r, start=0, extent=90, outline=outline, width=width, style="arc")
            self.canvas.create_arc(x2-2*r, y2-2*r, x2, y2, start=270, extent=90, outline=outline, width=width, style="arc")
            self.canvas.create_arc(x1, y2-2*r, x1+2*r, y2, start=180, extent=90, outline=outline, width=width, style="arc")
            
            self.canvas.create_line(x1+r, y1, x2-r, y1, fill=outline, width=width)
            self.canvas.create_line(x2, y1+r, x2, y2-r, fill=outline, width=width)
            self.canvas.create_line(x1+r, y2, x2-r, y2, fill=outline, width=width)
            self.canvas.create_line(x1, y1+r, x1, y2-r, fill=outline, width=width)

    def setup_dials(self):
        # Dials configurations
        self.cpu_cx, self.cpu_cy = 55, 70
        self.ram_cx, self.ram_cy = 145, 70
        self.dial_r = 30
        
        # Background gauges (dark rings)
        for cx, name in [(self.cpu_cx, "CPU"), (self.ram_cx, "RAM")]:
            self.canvas.create_arc(
                cx - self.dial_r, self.cpu_cy - self.dial_r,
                cx + self.dial_r, self.cpu_cy + self.dial_r,
                start=135, extent=270, outline="#1d1d26", width=5, style="arc"
            )
            self.canvas.create_text(
                cx, self.cpu_cy + 45, text=name, font=("Segoe UI", 9, "bold"), fill="#6a6a78"
            )
            
        # Active gauge arcs (neon colors stand out nicely on monochrome theme)
        self.cpu_arc = self.canvas.create_arc(
            self.cpu_cx - self.dial_r, self.cpu_cy - self.dial_r,
            self.cpu_cx + self.dial_r, self.cpu_cy + self.dial_r,
            start=135, extent=0, outline="#00f3ff", width=5, style="arc"
        )
        self.ram_arc = self.canvas.create_arc(
            self.ram_cx - self.dial_r, self.cpu_cy - self.dial_r,
            self.ram_cx + self.dial_r, self.cpu_cy + self.dial_r,
            start=135, extent=0, outline="#ff2d55", width=5, style="arc"
        )
        
        # Center percentage values
        self.cpu_text = self.canvas.create_text(
            self.cpu_cx, self.cpu_cy - 1, text="0%", font=("Segoe UI Semibold", 11), fill="#ffffff"
        )
        self.ram_text = self.canvas.create_text(
            self.ram_cx, self.cpu_cy - 1, text="0%", font=("Segoe UI Semibold", 11), fill="#ffffff"
        )

    def poll_metrics(self):
        psutil.cpu_percent(interval=None)
        while self.running:
            self.target_cpu = psutil.cpu_percent(interval=None)
            self.target_ram = psutil.virtual_memory().percent
            time.sleep(1.0)

    def animate(self):
        if not self.running:
            return
            
        # 1. Smoothly interpolate metrics display (gliding gauge needles)
        self.display_cpu += (self.target_cpu - self.display_cpu) * 0.1
        self.display_ram += (self.target_ram - self.display_ram) * 0.1
        
        # Update Dial Arc Sweeps
        cpu_extent = -(self.display_cpu / 100.0) * 270.0
        ram_extent = -(self.display_ram / 100.0) * 270.0
        self.canvas.itemconfigure(self.cpu_arc, extent=cpu_extent)
        self.canvas.itemconfigure(self.ram_arc, extent=ram_extent)
        
        # Update Dial Text values
        self.canvas.itemconfigure(self.cpu_text, text=f"{int(round(self.display_cpu))}%")
        self.canvas.itemconfigure(self.ram_text, text=f"{int(round(self.display_ram))}%")
            
        # Re-schedule next frame (~60 FPS)
        self.root.after(16, self.animate)

    def set_appwindow(self):
        try:
            import ctypes
            GWL_EXSTYLE = -20
            WS_EX_APPWINDOW = 0x00040000
            WS_EX_TOOLWINDOW = 0x00000080
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = style & ~WS_EX_TOOLWINDOW
            style = style | WS_EX_APPWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
            # Refresh to show in taskbar
            self.root.wm_withdraw()
            self.root.wm_deiconify()
        except Exception as e:
            print(f"Taskbar error: {e}")

    # Window Drag and Drop Logic
    def start_drag(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def drag_window(self, event):
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")

    # Window visibility control
    def hide_window(self):
        if self.visible:
            self.root.withdraw()
            self.visible = False
            
    def show_window(self):
        if not self.visible:
            self.root.after(0, self._show_window_main_thread)
            
    def _show_window_main_thread(self):
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.visible = True

    def toggle_window(self):
        if self.visible:
            self.hide_window()
        else:
            self.show_window()

    def exit_app(self):
        self.running = False
        if self.icon:
            self.icon.stop()
        self.root.after(0, self.root.destroy)

    # System Tray Integration Setup
    def setup_tray(self):
        import pystray
        from pystray import MenuItem as item
        
        tray_icon_path = resource_path("assets/tray_icon.png")
        icon_img = Image.open(tray_icon_path)
        
        menu = (
            item('Toggle Widget', lambda icon, item: self.toggle_window(), default=True),
            item('Show Widget', lambda icon, item: self.show_window()),
            item('Hide Widget', lambda icon, item: self.hide_window()),
            item('Exit', lambda icon, item: self.exit_app())
        )
        
        self.icon = pystray.Icon("gtr_monitor", icon_img, "System Monitor", menu)
        self.icon.run()

if __name__ == '__main__':
    app = GTRMonitorApp()
    app.root.mainloop()
