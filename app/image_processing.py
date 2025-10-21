# app/image_processing.py

from PIL import Image
import numpy as np
from skimage.morphology import closing, remove_small_objects, footprint_rectangle
from . import config

def process_image(filepath):
    """
    Loads, stretches to fill the canvas, cleans, and converts an image.
    """
    try:
        img = Image.open(filepath).convert('L')
    except FileNotFoundError:
        print(f"Error: The file '{filepath}' was not found.")
        return None

    # Calculate canvas size in pixels using the smart resolution from config
    canvas_width_px = int(config.PLOTTER_WIDTH_MM * config.PROCESSING_STEPS_PER_MM)
    canvas_height_px = int(config.PLOTTER_HEIGHT_MM * config.PROCESSING_STEPS_PER_MM)
    
    # --- THIS IS THE CORRECTED LOGIC ---
    # 1. Stretch the image to the exact canvas dimensions.
    img = img.resize((canvas_width_px, canvas_height_px))
    print(f"Image stretched to fit {img.width}x{img.height} pixel canvas (Target: {config.PROCESSING_DPI:.0f} DPI)")

    # 2. Convert to a binary image before cleaning.
    threshold = 128
    binary_img = img.point(lambda p: 255 if p > threshold else 0, '1')

    # 3. Apply cleaning operations.
    print("Cleaning image with morphological operations...")
    image_array = ~np.array(binary_img, dtype=bool)
    footprint = footprint_rectangle((3,3))
    
    closed_array = closing(image_array, footprint)
    for _ in range(config.MORPH_CLOSING_ITERATIONS - 1):
        closed_array = closing(closed_array, footprint)

    cleaned_array = remove_small_objects(closed_array, min_size=config.MIN_OBJECT_SIZE_PIXELS)

    # 4. Convert the cleaned array back to a final Pillow image.
    final_array = (~cleaned_array).astype(np.uint8) * 255
    processed_img = Image.fromarray(final_array, 'L').convert('1')
    
    print("Image cleaning complete.")
    return processed_img