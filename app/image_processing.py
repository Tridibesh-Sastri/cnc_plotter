# app/image_processing.py

from PIL import Image

def process_image(filepath, canvas_width_mm, resolution):
    """Loads an image, resizes it, and converts it to pure black and white."""
    try:
        img = Image.open(filepath)
    except FileNotFoundError:
        print(f"Error: The file '{filepath}' was not found.")
        return None

    canvas_width_px = int(canvas_width_mm * resolution)
    aspect_ratio = img.height / img.width
    canvas_height_px = int(canvas_width_px * aspect_ratio)

    print(f"Resizing image to {canvas_width_px} x {canvas_height_px} pixels...")

    processed_img = img.resize((canvas_width_px, canvas_height_px)).convert('L')
    threshold = 128
    processed_img = processed_img.point(lambda p: 255 if p > threshold else 0, '1')
    
    return processed_img