# app/text_pipeline.py

import pytesseract
from PIL import Image
from . import config

# --- IMPORTANT: TESSERACT CONFIGURATION ---
# Point pytesseract to your Tesseract installation executable.
# This path might be different on your system.
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


# --- A Simple Embedded Single-Stroke Font (subset of Hershey Simplex) ---
# Each character is a list of paths. Each path is a list of (x,y) points.
# The coordinates are normalized from roughly -1 to 1.
HERSHEY_FONT = {
    'A': [[(-0.5, -0.8), (0.0, 0.9)], [(0.0, 0.9), (0.5, -0.8)], [(-0.3, 0.1), (0.3, 0.1)]],
    'B': [[(-0.5, -0.8), (-0.5, 0.9)], [(-0.5, 0.9), (0.3, 0.7)], [(0.3, 0.7), (0.3, 0.1)], [(-0.5, 0.1)], [(-0.5, 0.1), (0.4, -0.1)], [(0.4, -0.1), (0.4, -0.6)], [(-0.5, -0.8)]],
    'C': [[(0.5, 0.6), (0.2, 0.9)], [(0.2, 0.9), (-0.5, 0.6)], [(-0.5, 0.6), (-0.5, -0.5)], [(-0.5, -0.5), (0.2, -0.8)], [(0.2, -0.8), (0.5, -0.5)]],
    'D': [[(-0.5, -0.8), (-0.5, 0.9)], [(-0.5, 0.9), (0.3, 0.6)], [(0.3, 0.6), (0.3, -0.5)], [(-0.5, -0.8)]],
    'E': [[(0.5, 0.9), (-0.5, 0.9)], [(-0.5, 0.9), (-0.5, -0.8)], [(0.5, -0.8)], [(-0.5, 0.1), (0.2, 0.1)]],
    'H': [[(-0.5, 0.9), (-0.5, -0.8)], [(0.5, 0.9), (0.5, -0.8)], [(-0.5, 0.1), (0.5, 0.1)]],
    'L': [[(-0.5, 0.9), (-0.5, -0.8)], [(-0.5, -0.8), (0.5, -0.8)]],
    'O': [[(-0.5, 0.0), (-0.3, 0.9)], [(0.3, 0.9)], [(0.5, 0.0)], [(0.3, -0.8)], [(-0.3, -0.8)], [(-0.5, 0.0)]],
    'W': [[(-0.6, 0.9), (-0.3, -0.8)], [(-0.3, -0.8), (0.0, 0.5)], [(0.0, 0.5), (0.3, -0.8)], [(0.3, -0.8), (0.6, 0.9)]],
    ' ': [], # Space character has no path
}
# (Add more characters as needed)


def ocr_to_characters(image_obj):
    """Uses Tesseract to find all characters and their bounding boxes."""
    data = pytesseract.image_to_data(image_obj, output_type=pytesseract.Output.DICT)
    chars = []
    for i in range(len(data['text'])):
        # Tesseract returns data for words, lines, etc. We only want individual characters.
        if int(data['conf'][i]) > 0 and len(data['text'][i]) == 1:
            char = data['text'][i].upper()
            if char in HERSHEY_FONT:
                chars.append({
                    'char': char,
                    'x': data['left'][i],
                    'y': data['top'][i],
                    'w': data['width'][i],
                    'h': data['height'][i],
                })
    return chars

def generate_text_gcode(image):
    """The main function for the Text Pipeline."""
    print("Running OCR to detect characters...")
    characters = ocr_to_characters(image)
    
    if not characters:
        print("No characters detected.")
        return ["G1 X0 Y0"]

    print(f"Detected {len(characters)} characters. Sorting into lines...")

    # --- Sort characters into lines and apply serpentine (boustrophedon) order ---
    lines = {}
    for char in characters:
        # Group characters into lines based on vertical position
        line_key = round(char['y'] / (char['h'] * 1.5)) # Group by steps of 1.5x char height
        if line_key not in lines:
            lines[line_key] = []
        lines[line_key].append(char)

    sorted_chars = []
    for i, line_key in enumerate(sorted(lines.keys())):
        line = sorted(lines[line_key], key=lambda c: c['x'])
        if i % 2 == 1: # On odd lines, reverse the order for serpentine movement
            line.reverse()
        sorted_chars.extend(line)

    print("Generating single-stroke G-code...")
    gcode = []
    gcode.append("; Generated with Text Pipeline (OCR + Single-Stroke)")
    gcode.append("M5 ; Pen Up")
    gcode.append("G1 X0 Y0 F5000")

    # --- Convert each character to G-code ---
    for char_data in sorted_chars:
        char_path = HERSHEY_FONT.get(char_data['char'], [])
        
        # Bounding box from OCR (in pixels)
        box_x, box_y = char_data['x'], char_data['y']
        box_w, box_h = char_data['w'], char_data['h']
        
        for stroke in char_path:
            # First point of the stroke
            start_point_norm = stroke[0]
            
            # Scale and translate normalized font coordinate to the character's bounding box
            start_x_px = box_x + (start_point_norm[0] + 0.5) * box_w
            start_y_px = box_y + (-start_point_norm[1] + 0.9) * (box_h / 1.7)
            
            # Convert pixel coordinate to physical mm
            start_x_mm = start_x_px / config.PROCESSING_STEPS_PER_MM
            start_y_mm = config.PLOTTER_HEIGHT_MM - (start_y_px / config.PROCESSING_STEPS_PER_MM) # Y is inverted

            # Travel move to the start of the stroke
            gcode.append(f"G1 X{start_x_mm:.2f} Y{start_y_mm:.2f} F5000")
            gcode.append("M3 ; Pen Down")
            
            # Draw the rest of the stroke
            for point_norm in stroke[1:]:
                x_px = box_x + (point_norm[0] + 0.5) * box_w
                y_px = box_y + (-point_norm[1] + 0.9) * (box_h / 1.7)
                x_mm = x_px / config.PROCESSING_STEPS_PER_MM
                y_mm = config.PLOTTER_HEIGHT_MM - (y_px / config.PROCESSING_STEPS_PER_MM)
                gcode.append(f"G1 X{x_mm:.2f} Y{y_mm:.2f} F2000")

            gcode.append("M5 ; Pen Up")

    gcode.append("G1 X0 Y0 ; Return to home")
    print("G-code generation complete.")
    return gcode