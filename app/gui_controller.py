# app/gui_controller.py

import tkinter as tk
from tkinter import ttk, filedialog
import re
from . import config

class SimulatorApp(tk.Frame):
    def __init__(self, master=None, gcode_data=None):
        super().__init__(master)
        self.master = master
        self.master.title("CNC G-code Simulator")
        self.master.geometry("1000x750")
        self.pack(fill=tk.BOTH, expand=True)
        
        self.gcode_commands = []
        self.command_index = 0
        self.is_playing = False
        self.pen_is_down = False
        self.current_pos = (0.0, 0.0)
        self.animation_job = None
        self.head_radius = 4 # NEW: Store head radius as a class attribute

        self.control_frame = ttk.Frame(self, width=250, relief=tk.RIDGE, padding=10)
        self.canvas_frame = ttk.Frame(self, relief=tk.RIDGE)
        
        self.control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        self.canvas_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.create_controls()
        self.create_canvas()
        self.create_status_display()

        if gcode_data:
            self.load_gcode_data(gcode_data)

    def create_controls(self):
        # (This function is unchanged)
        controls_group = ttk.LabelFrame(self.control_frame, text="Controls")
        controls_group.pack(fill=tk.X, pady=10)
        self.load_button = ttk.Button(controls_group, text="Load G-code File", command=self.load_gcode_from_file)
        self.load_button.pack(fill=tk.X, padx=10, pady=5)
        self.play_pause_button = ttk.Button(controls_group, text="▶ Play", command=self.toggle_play_pause, state=tk.DISABLED)
        self.play_pause_button.pack(fill=tk.X, padx=10, pady=5)
        self.reset_button = ttk.Button(controls_group, text="Reset", command=self.reset_simulation, state=tk.DISABLED)
        self.reset_button.pack(fill=tk.X, padx=10, pady=5)
        speed_group = ttk.LabelFrame(self.control_frame, text="Playback Speed")
        speed_group.pack(fill=tk.X, pady=10)
        self.speed_scale = ttk.Scale(speed_group, from_=0.5, to=10.0, orient=tk.HORIZONTAL)
        self.speed_scale.set(1.0)
        self.speed_scale.pack(fill=tk.X, padx=10, pady=10)

    def create_canvas(self):
        self.canvas = tk.Canvas(self.canvas_frame, bg="ivory", relief=tk.SUNKEN)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        # Use the class attribute for radius
        self.plotter_head = self.canvas.create_oval(
            -self.head_radius, -self.head_radius, self.head_radius, self.head_radius,
            outline="black", fill="blue", width=2
        )

    def create_status_display(self):
        # (This function is unchanged)
        status_group = ttk.LabelFrame(self.control_frame, text="Live Status")
        status_group.pack(pady=10, fill=tk.BOTH, expand=True)
        ttk.Label(status_group, text="Command:").pack(anchor='w', padx=10, pady=(10,0))
        self.current_command_var = tk.StringVar(value="None")
        ttk.Label(status_group, textvariable=self.current_command_var, wraplength=200).pack(anchor='w', padx=10)
        ttk.Label(status_group, text="Pen State:").pack(anchor='w', padx=10, pady=(10,0))
        self.pen_state_var = tk.StringVar(value="UP")
        self.pen_state_label = ttk.Label(status_group, textvariable=self.pen_state_var)
        self.pen_state_label.pack(anchor='w', padx=10)
        ttk.Label(status_group, text="Position (mm):").pack(anchor='w', padx=10, pady=(10,0))
        self.coords_var = tk.StringVar(value="X: 0.00, Y: 0.00")
        ttk.Label(status_group, textvariable=self.coords_var).pack(anchor='w', padx=10)
        ttk.Label(status_group, text="Feedrate (mm/min):").pack(anchor='w', padx=10, pady=(10,0))
        self.feedrate_var = tk.StringVar(value="0")
        ttk.Label(status_group, textvariable=self.feedrate_var).pack(anchor='w', padx=10, pady=(0,10))

    def load_gcode_from_file(self):
        # (This function is unchanged)
        filepath = filedialog.askopenfilename(filetypes=[("G-code Files", "*.gcode")])
        if not filepath: return
        with open(filepath, 'r') as f:
            gcode_data = f.readlines()
        self.load_gcode_data(gcode_data)

    def load_gcode_data(self, gcode_data):
        # (This function is unchanged)
        self.reset_simulation()
        self.gcode_commands = self._parse_gcode(gcode_data)
        if self.gcode_commands:
            self.play_pause_button.config(state=tk.NORMAL)
            self.reset_button.config(state=tk.NORMAL)
            print(f"Loaded {len(self.gcode_commands)} valid G-code commands.")

    def toggle_play_pause(self):
        # (This function is unchanged)
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.play_pause_button.config(text="❚❚ Pause")
            self._animation_loop()
        else:
            self.play_pause_button.config(text="▶ Play")
            if self.animation_job:
                self.master.after_cancel(self.animation_job)

    def reset_simulation(self):
        # (This function is unchanged)
        if self.animation_job:
            self.master.after_cancel(self.animation_job)
        self.is_playing = False
        self.command_index = 0
        self.current_pos = (0.0, 0.0)
        self.canvas.delete("line_segment", "arc_segment")
        self._update_plotter_head_pos()
        self._update_status(pen_state="UP", feedrate=0)
        if self.gcode_commands:
             self.play_pause_button.config(text="▶ Play")

    def _parse_gcode(self, gcode_data):
        # (This function is unchanged)
        parsed_commands = []
        g_pattern = re.compile(r'G([0-3])\s*(X([\d\.-]+))?\s*(Y([\d\.-]+))?\s*(I([\d\.-]+))?\s*(J([\d\.-]+))?\s*(F([\d\.-]+))?')
        for line in gcode_data:
            line = line.strip().upper()
            if not line or line.startswith(';'): continue
            cmd_obj = {'raw': line}
            if line.startswith('M3'): cmd_obj['type'] = 'M3'
            elif line.startswith('M5'): cmd_obj['type'] = 'M5'
            elif line.startswith('G'):
                match = g_pattern.search(line)
                if match:
                    cmd_obj['type'] = f'G{match.group(1)}'
                    cmd_obj['x'] = float(match.group(3)) if match.group(3) else None
                    cmd_obj['y'] = float(match.group(5)) if match.group(5) else None
                    cmd_obj['i'] = float(match.group(7)) if match.group(7) else None
                    cmd_obj['j'] = float(match.group(9)) if match.group(9) else None
                    cmd_obj['f'] = float(match.group(11)) if match.group(11) else None
            if 'type' in cmd_obj: parsed_commands.append(cmd_obj)
        return parsed_commands

    def _animation_loop(self):
        # (This function is unchanged)
        if not self.is_playing or self.command_index >= len(self.gcode_commands):
            self.toggle_play_pause()
            return

        cmd = self.gcode_commands[self.command_index]
        self.current_command_var.set(cmd['raw'])
        delay_ms = 20
        
        if cmd['type'] == 'M3':
            self.pen_is_down = True
            self._update_status(pen_state="DOWN")
        elif cmd['type'] == 'M5':
            self.pen_is_down = False
            self._update_status(pen_state="UP")
        elif cmd['type'] in ['G1', 'G2', 'G3']:
            start_pos_mm = self.current_pos
            end_pos_mm = (cmd['x'], cmd['y'])
            feedrate = cmd.get('f') or 2000
            self._update_status(feedrate=feedrate)
            
            start_pos_px = self._map_coords_to_canvas(start_pos_mm)
            end_pos_px = self._map_coords_to_canvas(end_pos_mm)
            
            if self.pen_is_down:
                self.canvas.create_line(start_pos_px, end_pos_px, fill="red", width=2, tags="line_segment")
            
            self.current_pos = end_pos_mm
            self._update_plotter_head_pos()
            
            dist_mm = ((end_pos_mm[0] - start_pos_mm[0])**2 + (end_pos_mm[1] - start_pos_mm[1])**2)**0.5
            time_min = dist_mm / feedrate if feedrate > 0 else 0
            time_sec = time_min * 60
            delay_ms = int(time_sec * 1000 / self.speed_scale.get())

        self.command_index += 1
        self.animation_job = self.master.after(max(1, delay_ms), self._animation_loop)

    def _map_coords_to_canvas(self, pos_mm):
        # (This function is unchanged)
        # Using winfo_width() can be unreliable before the window is fully drawn.
        # We can wait for the first 'Configure' event or use a fixed initial size.
        canvas_w = self.canvas.winfo_width() if self.canvas.winfo_width() > 1 else 750
        canvas_h = self.canvas.winfo_height() if self.canvas.winfo_height() > 1 else 750
        
        x_px = (pos_mm[0] / config.PLOTTER_WIDTH_MM) * canvas_w
        y_px = (1 - (pos_mm[1] / config.PLOTTER_HEIGHT_MM)) * canvas_h
        return (x_px, y_px)
        
    def _update_plotter_head_pos(self):
        """
        CORRECTED: Moves the virtual head by calculating the full bounding
        box for the oval.
        """
        pos_px = self._map_coords_to_canvas(self.current_pos)
        
        # --- THIS IS THE FIX ---
        # Calculate the 4 coordinates for the oval's bounding box
        x1 = pos_px[0] - self.head_radius
        y1 = pos_px[1] - self.head_radius
        x2 = pos_px[0] + self.head_radius
        y2 = pos_px[1] + self.head_radius
        
        # Use the 4 correct coordinates to update the oval
        self.canvas.coords(self.plotter_head, x1, y1, x2, y2)
        
        self.coords_var.set(f"X: {self.current_pos[0]:.2f}, Y: {self.current_pos[1]:.2f}")

    def _update_status(self, pen_state=None, feedrate=None):
        # (This function is unchanged)
        if pen_state == "DOWN":
            self.pen_state_var.set("DOWN")
            self.pen_state_label.config(foreground="red")
            self.canvas.itemconfig(self.plotter_head, fill="red")
        elif pen_state == "UP":
            self.pen_state_var.set("UP")
            self.pen_state_label.config(foreground="blue")
            self.canvas.itemconfig(self.plotter_head, fill="blue")
        if feedrate is not None:
            self.feedrate_var.set(f"{feedrate:.0f}")