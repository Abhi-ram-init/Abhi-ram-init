import os
import sys
import time
import math
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
        self.root.geometry(f"440x140+{screen_w - 480}+{screen_h - 200}")
        
        # 2. State Variables
        self.running = True
        self.visible = True
        self.target_cpu = 0.0
        self.target_ram = 0.0
        self.display_cpu = 0.0
        self.display_ram = 0.0
        self.wheel_angle = 0.0
        
        # Dragging variables
        self.drag_start_x = 0
        self.drag_start_y = 0

        # Road animation variables
        self.road_dashes = [20, 70, 120, 170]
        
        # 3. Load & Process Assets
        self.scale_factor = 0.2
        
        # Car body (wheels erased)
        body_path = resource_path("assets/car_body_final.png")
        self.orig_body = Image.open(body_path).convert("RGBA")
        w_body = int(self.orig_body.width * self.scale_factor)
        h_body = int(self.orig_body.height * self.scale_factor)
        self.body_img = self.orig_body.resize((w_body, h_body), Image.Resampling.LANCZOS)
        
        # Rear wheel image
        self.orig_wheel = Image.open(resource_path("assets/wheel_final.png")).convert("RGBA")
        
        # Scale factor: rear wheel radius=72 in 1024px image, front=75
        # Rear wheel scaled size
        r_rad_orig = 72
        f_rad_orig = 75
        r_size = int(r_rad_orig * 2 * self.scale_factor)
        f_size = int(f_rad_orig * 2 * self.scale_factor)
        self.scaled_wheel_rear  = self.orig_wheel.resize((r_size, r_size), Image.Resampling.LANCZOS)
        self.scaled_wheel_front = self.orig_wheel.resize((f_size, f_size), Image.Resampling.LANCZOS)
        
        # Exact wheel centers (visually debugged to fit tyre outline perfectly)
        self.rear_cx  = 238 * self.scale_factor
        self.rear_cy  = 577 * self.scale_factor
        self.front_cx = 793 * self.scale_factor
        self.front_cy = 585 * self.scale_factor
        
        # 4. Create UI Elements on Canvas
        self.canvas = tk.Canvas(self.root, width=440, height=140, bg="#00ff00", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # Draw Glassmorphic Rounded Card Background (Neon accent ring)
        self.draw_rounded_card(10, 10, 430, 130, 16, "#0f0f13", "#22222d", width=2)
        
        # Draw Close Button (hides to tray)
        self.close_btn = self.canvas.create_text(
            415, 25, text="×", font=("Segoe UI", 14, "bold"), fill="#60606b", activefill="#ff4a4a"
        )
        self.canvas.tag_bind(self.close_btn, "<Button-1>", lambda e: self.hide_window())

        # Draw Rolling Road Line
        self.canvas.create_line(15, 115, 195, 115, fill="#23232c", width=3)
        self.road_dash_items = []
        for i in range(len(self.road_dashes)):
            dash = self.canvas.create_line(self.road_dashes[i], 115, self.road_dashes[i] + 8, 115, fill="#6b6b7a", width=3)
            self.road_dash_items.append(dash)
            
        # Place car body (wheels already erased)
        self.car_x = 10
        self.car_y = -10
        self.body_photo = ImageTk.PhotoImage(self.body_img)
        self.car_body_item = self.canvas.create_image(self.car_x, self.car_y, image=self.body_photo, anchor="nw")
        
        # Wheel items drawn ON TOP of the body
        self.rear_wheel_item  = self.canvas.create_image(0, 0, anchor="center")
        self.front_wheel_item = self.canvas.create_image(0, 0, anchor="center")
        
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
        self.cpu_cx, self.cpu_cy = 265, 70
        self.ram_cx, self.ram_cy = 360, 70
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
        
        # Speed scales with CPU
        speed_factor = 2.0 + (self.display_cpu / 100.0) * 15.0
        now = time.time()
        dt = now - self.last_time
        self.last_time = now
        
        # Spin wheels — speed proportional to CPU
        speed_factor = 3.0 + (self.display_cpu / 100.0) * 20.0
        now = time.time()
        dt = now - self.last_time
        self.last_time = now
        
        # Rotate wheel image
        self.wheel_angle = (self.wheel_angle + speed_factor * dt * 120.0) % 360.0
        rot_rear  = self.scaled_wheel_rear.rotate(-self.wheel_angle,  resample=Image.Resampling.BICUBIC, expand=False)
        rot_front = self.scaled_wheel_front.rotate(-self.wheel_angle, resample=Image.Resampling.BICUBIC, expand=False)
        self.wheel_tk_rear  = ImageTk.PhotoImage(rot_rear)
        self.wheel_tk_front = ImageTk.PhotoImage(rot_front)
        
        rear_x  = self.car_x + self.rear_cx
        rear_y  = self.car_y + self.rear_cy
        front_x = self.car_x + self.front_cx
        front_y = self.car_y + self.front_cy
        
        self.canvas.coords(self.rear_wheel_item, rear_x, rear_y)
        self.canvas.itemconfigure(self.rear_wheel_item, image=self.wheel_tk_rear)
        self.canvas.coords(self.front_wheel_item, front_x, front_y)
        self.canvas.itemconfigure(self.front_wheel_item, image=self.wheel_tk_front)
        
        # Road dashes animate to give the illusion the car is moving forward
        road_speed = speed_factor * dt * 60.0
        for i in range(len(self.road_dashes)):
            self.road_dashes[i] -= road_speed
            if self.road_dashes[i] < 15:
                self.road_dashes[i] = 190
            self.canvas.coords(self.road_dash_items[i], self.road_dashes[i], 115, self.road_dashes[i] + 8, 115)
            
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
