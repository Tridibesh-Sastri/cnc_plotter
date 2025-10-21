# app/image_processing.py

from PIL import Image
from . import config # Import the config file

def process_image(filepath):
    """
    Loads an image, resizes it to fit the canvas at the optimal processing
    resolution, and converts to pure black and white.
    """
    try:
        img = Image.open(filepath).convert('L')
    except FileNotFoundError:
        print(f"Error: The file '{filepath}' was not found.")
        return None

    # Calculate canvas size in pixels using the smart resolution from config
    canvas_width_px = int(config.PLOTTER_WIDTH_MM * config.PROCESSING_STEPS_PER_MM)
    canvas_height_px = int(config.PLOTTER_HEIGHT_MM * config.PROCESSING_STEPS_PER_MM)
    
    img.thumbnail((canvas_width_px, canvas_height_px))

    print(f"Processing image at {img.width}x{img.height} pixels (Target: {config.PROCESSING_DPI:.0f} DPI)")

    # Create a new white background and paste the image in the center
    bg = Image.new('L', (canvas_width_px, canvas_height_px), 255)
    paste_x = (canvas_width_px - img.width) // 2
    paste_y = (canvas_height_px - img.height) // 2
    bg.paste(img, (paste_x, paste_y))
    
    threshold = 128
    processed_img = bg.point(lambda p: 255 if p > threshold else 0, '1')
    
    return processed_img