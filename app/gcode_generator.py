# app/gcode_generator.py

# Import Image and ImageDraw from Pillow for image handling and drawing.
from PIL import Image, ImageDraw
# Import regex module for parsing G-code commands in visualization.
import re


def generate_raster_gcode(image, resolution, pen_nib_mm):
    """Generates G-code with scan lines spaced by the pen's nib size.

    Parameters:
    - image: a PIL Image (mode 'L' or similar) where 0 represents black/ink.
    - resolution: pixels per millimeter (px/mm) used to convert between image
      pixel coordinates and real-world millimeters for G-code.
    - pen_nib_mm: pen nib width in millimeters; used to space raster scanlines.

    Returns a list of G-code command strings.
    """
    # Container for the generated lines of G-code.
    gcode = []

    # Get width and height (in pixels) from the PIL Image object.
    width, height = image.size

    # Load the pixel access object to read pixel values quickly.
    pixels = image.load()
    
    # Add a comment to the top of the G-code with the pen nib info.
    gcode.append(f"; Generated with pen nib size: {pen_nib_mm}mm")

    # Ensure the pen is up to start: 'M5' is used here as the pen-up command.
    gcode.append("M5 ; Pen Up")

    # Move to origin (0,0) with a feedrate (F2000) to establish starting position.
    gcode.append("G1 X0 Y0 F2000")

    # Track whether the pen is currently down (drawing) or up (traveling).
    pen_is_down = False
    
    # Compute how many pixels correspond to the pen nib width. This controls
    # vertical step size between successive raster rows so lines don't overlap.
    y_step = int(pen_nib_mm * resolution)
    # Guard against a zero step if pen_nib_mm is very small or resolution low.
    if y_step == 0: y_step = 1
    
    # Print a helpful message for the user/developer describing the step.
    print(f"Raster scan will advance {y_step} pixels per line to match pen width.")

    # Iterate over rows in the image stepping by y_step pixels each loop.
    for y in range(0, height, y_step):
        # For efficiency in travel between rows, alternate the horizontal scan
        # direction every row (a serpentine/zig-zag pattern). On even rows
        # scan left-to-right; on odd rows scan right-to-left.
        x_range = range(width) if y % 2 == 0 else range(width - 1, -1, -1)

        # Iterate over every x in the chosen direction.
        for x in x_range:
            # Determine whether the current pixel is black (ink) or not.
            # This assumes an 8-bit grayscale image where 0 == black.
            is_black = (pixels[x, y] == 0)
            
            # If we encounter a black pixel and the pen is currently up,
            # move to that pixel position and lower the pen to start drawing.
            if is_black and not pen_is_down:
                # Convert pixel coordinates to millimeters using resolution
                # and append a G1 move to that position (fast positioning).
                gcode.append(f"G1 X{x/resolution:.2f} Y{y/resolution:.2f}")
                # Lower the pen: 'M3' here is used as the pen-down command.
                gcode.append("M3 ; Pen Down")
                pen_is_down = True
            
            # If pixel is not black but pen is down, we reached the end of a
            # drawn segment and need to raise the pen after moving to the last
            # drawn pixel so we don't lift mid-segment.
            elif not is_black and pen_is_down:
                # Compute the last drawn x coordinate depending on scan direction.
                last_x = x - 1 if y % 2 == 0 else x + 1
                # Move to the last drawn pixel (converted to mm) before lifting.
                gcode.append(f"G1 X{last_x/resolution:.2f} Y{y/resolution:.2f}")
                # Raise the pen.
                gcode.append("M5 ; Pen Up")
                pen_is_down = False
                
        # After finishing the row, if the pen is still down, ensure we lift it
        # at the end of the row and move explicitly to the row's end point.
        if pen_is_down:
            # Choose the end-of-row x coordinate based on scan direction.
            end_of_row_x = width - 1 if y % 2 == 0 else 0
            # Move to the end of row in mm and then lift the pen.
            gcode.append(f"G1 X{end_of_row_x/resolution:.2f} Y{y/resolution:.2f}")
            gcode.append("M5 ; Pen Up")
            pen_is_down = False

    # After all rows are processed, return to home (0,0).
    gcode.append("G1 X0 Y0 ; Return to home")
    
    # Log completion and return the list of G-code commands.
    print("G-code generation complete.")
    return gcode


def visualize_gcode_path(base_image, gcode, resolution):
    """Draws the G-code path onto the base image for debugging.

    This function parses simple G1 X.. Y.. moves and M3/M5 pen commands to
    render the motion path. Pen-down movement is drawn in red; pen-up in blue.
    """
    # Inform the user that visualization is starting.
    print("Creating toolpath visualization...")

    # Convert the base image to RGB so colored lines can be drawn.
    canvas = base_image.convert('RGB')

    # Create a drawing context for the image.
    draw = ImageDraw.Draw(canvas)

    # Track the current position in pixel coordinates; start at origin (0,0).
    current_pos_px = (0, 0)

    # Track pen state: True when drawing, False when lifted.
    pen_is_down = False

    # Precompile a regex to find G1 commands with X and Y numeric values.
    g1_pattern = re.compile(r'G1\s+X([\d\.]+)\s+Y([\d\.]+)')

    # Iterate over each G-code command string produced earlier.
    for command in gcode:
        # Toggle pen state based on M3 (down) and M5 (up) commands.
        if command.startswith("M3"): pen_is_down = True
        elif command.startswith("M5"): pen_is_down = False

        # If there's a G1 X.. Y.. command, extract the X and Y coordinates.
        match = g1_pattern.search(command)
        if match:
            # Parse the millimeter coordinates from the command.
            x_mm = float(match.group(1))
            y_mm = float(match.group(2))

            # Convert millimeters back to pixels for drawing on the canvas.
            target_pos_px = (int(x_mm * resolution), int(y_mm * resolution))

            # Use red for pen-down segments and blue for pen-up travel moves.
            line_color = "red" if pen_is_down else "blue"

            # Draw a line from the current position to the target position.
            draw.line([current_pos_px, target_pos_px], fill=line_color, width=1)

            # Update current position for the next segment.
            current_pos_px = target_pos_px

    # Save the visualization to a PNG file for inspection.
    canvas.save("debug_02_toolpath_visualization.png")
    print("Visualization saved to 'debug_02_toolpath_visualization.png'")