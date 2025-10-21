# main.py

from app.image_processing import process_image
from app.gcode_generator import generate_raster_gcode, visualize_gcode_path

# --- (1) CONFIGURATION: Physical Machine Parameters ---
# Using the 28BYJ-48 motor specs
EFFECTIVE_STEPS_PER_REV = 4096 
BELT_PITCH = 2.0           
PULLEY_TEETH = 20          

PLOTTER_WIDTH_MM = 180.0
PEN_NIB_MM = 0.5           

IMAGE_FILE_PATH = "resources\\test1.jpeg" # Make sure you have an image with this name
OUTPUT_GCODE_FILE = "output.gcode"

# --- (2) CALCULATED PARAMETERS ---
SMALLEST_MOVE_MM = (PULLEY_TEETH * BELT_PITCH) / EFFECTIVE_STEPS_PER_REV
STEPS_PER_MM = 1.0 / SMALLEST_MOVE_MM

# --- (3) MAIN EXECUTION ---
if __name__ == "__main__":
    print("--- Starting Image to G-code Conversion ---")
    
    bw_image = process_image(IMAGE_FILE_PATH, PLOTTER_WIDTH_MM, STEPS_PER_MM)
    
    if bw_image:
        bw_image.save("debug_01_black_and_white.png")
        print("Saved intermediate B&W image to 'debug_01_black_and_white.png'")
        
        gcode_path = generate_raster_gcode(bw_image, STEPS_PER_MM, PEN_NIB_MM)
        
        with open(OUTPUT_GCODE_FILE, 'w') as f:
            f.write("\n".join(gcode_path))
        print(f"Successfully saved G-code to '{OUTPUT_GCODE_FILE}'")
        
        visualize_gcode_path(bw_image, gcode_path, STEPS_PER_MM)
        
        print("--- Process Finished ---")