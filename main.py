# main.py

import tkinter as tk
from app import config
from app.image_processing import process_image
from app.gcode_generator import generate_kdtree_gcode, visualize_gcode_path, analyze_gcode
from app.gui_controller import SimulatorApp

IMAGE_FILE_PATH = "resources/test1.jpeg"
OUTPUT_GCODE_FILE = "output.gcode"

if __name__ == "__main__":
    print("--- Starting Image to G-code Conversion ---")
    
    # --- Part 1: G-code Generation (from our command-line script) ---
    bw_image = process_image(IMAGE_FILE_PATH)
    
    if bw_image:
        bw_image.save("debug_01_black_and_white.png")
        print("Saved intermediate B&W image.")
        
        gcode_path = generate_kdtree_gcode(bw_image)
        
        with open(OUTPUT_GCODE_FILE, 'w') as f:
            f.write("\n".join(gcode_path))
        print(f"Successfully saved G-code to '{OUTPUT_GCODE_FILE}'")
        
        visualize_gcode_path(bw_image, gcode_path)
        analyze_gcode(gcode_path)
        
        print("--- Process Finished ---")
        print("\n--- Launching G-code Simulator ---")

        # --- Part 2: Launch the GUI with the generated G-code ---
        root = tk.Tk()
        # We pass the generated gcode_path directly to our app
        app = SimulatorApp(master=root, gcode_data=gcode_path)
        app.mainloop()