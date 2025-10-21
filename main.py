# main.py

from app import config
from app.image_processing import process_image
# Import our two different G-code generators
from app.gcode_generator import generate_kdtree_gcode, visualize_gcode_path, analyze_gcode
from app.text_pipeline import generate_text_gcode

# Create a simple image with text for testing
IMAGE_FILE_PATH = "resources/text_test.png" # IMPORTANT: Create this new image file!
OUTPUT_GCODE_FILE = "output.gcode"

if __name__ == "__main__":
    print(f"--- Starting G-code Conversion using '{config.PROCESSING_STRATEGY}' strategy ---")
    
    # Image processing is simpler for the text pipeline; we just need the raw image.
    bw_image = process_image(IMAGE_FILE_PATH)
    
    if bw_image:
        bw_image.save("debug_01_black_and_white.png")
        print("Saved intermediate B&W image.")
        
        gcode_path = []
        if config.PROCESSING_STRATEGY == 'photo':
            # Run the complex photo/diagram pipeline
            gcode_path = generate_kdtree_gcode(bw_image)
        elif config.PROCESSING_STRATEGY == 'text':
            # Run the new, efficient text pipeline
            # Note: it needs the original PIL image object, not the cleaned one
            pil_image = Image.open(IMAGE_FILE_PATH)
            gcode_path = generate_text_gcode(pil_image)

        if gcode_path:
            with open(OUTPUT_GCODE_FILE, 'w') as f:
                f.write("\n".join(gcode_path))
            print(f"Successfully saved G-code to '{OUTPUT_GCODE_FILE}'")
            
            visualize_gcode_path(bw_image, gcode_path)
            analyze_gcode(gcode_path)
        
        print("--- Process Finished ---")