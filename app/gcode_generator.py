# app/gcode_generator.py

from PIL import Image, ImageDraw
import re
import math
from scipy.spatial import KDTree # New powerful import!
from . import config

def generate_kdtree_gcode(image):
    """
    Generates a highly optimized G-code path using a k-d tree and path sorting.
    """
    
    print("Finding all black pixels...")
    pixels = image.load()
    width, height = image.size
    
    point_list = []
    # Create a map to quickly find the index of a point
    point_to_index_map = {}
    for y in range(height):
        for x in range(width):
            if pixels[x, y] == 0:
                index = len(point_list)
                point_list.append((x, y))
                point_to_index_map[(x, y)] = index

    if not point_list:
        print("No black pixels found.")
        return ["M5", "G1 X0 Y0"]

    print(f"Found {len(point_list)} points. Building k-d tree for optimization...")
    
    kdtree = KDTree(point_list)
    visited = [False] * len(point_list)
    points_remaining = len(point_list)

    scale_x = config.PLOTTER_WIDTH_MM / width
    scale_y = config.PLOTTER_HEIGHT_MM / height
    search_radius_px = config.SEARCH_RADIUS_MM / scale_x

    gcode = []
    gcode.append("; Generated with Sorted k-d tree nearest neighbor")
    gcode.append("M5 ; Pen Up")
    gcode.append("G1 X0 Y0 F5000")

    while points_remaining > 0:
        # --- PATH SORTING LOGIC ---
        # Find the top-most, left-most unvisited point to start the next island.
        next_start_index = -1
        for i, point in enumerate(point_list):
            if not visited[i]:
                next_start_index = i
                break
        
        if next_start_index == -1: break # Should not happen if points_remaining > 0

        current_index = next_start_index
        start_point = point_list[current_index]
        
        gcode.append(f"G1 X{start_point[0] * scale_x:.2f} Y{start_point[1] * scale_y:.2f} F5000")
        gcode.append("M3 ; Pen Down")
        
        path = [start_point]
        visited[current_index] = True
        points_remaining -= 1

        while True:
            # Query the tree for the 10 nearest neighbors
            distances, indices = kdtree.query(point_list[current_index], k=10, distance_upper_bound=search_radius_px)

            found_neighbor = False
            for i, idx in enumerate(indices):
                if idx >= len(point_list): continue
                if not visited[idx]:
                    current_index = idx
                    path.append(point_list[current_index])
                    visited[current_index] = True
                    points_remaining -= 1
                    found_neighbor = True
                    break
            
            if not found_neighbor:
                break

        # --- PATH CHAINING LOGIC ---
        # Generate G-code for the full traced path, not just the end point.
        for point in path:
             gcode.append(f"G1 X{point[0] * scale_x:.2f} Y{point[1] * scale_y:.2f} F2000") # Drawing speed
        
        gcode.append("M5 ; Pen Up")

        if points_remaining % 1000 == 0 and points_remaining > 0:
            print(f"Points remaining: {points_remaining}")
            
    gcode.append("G1 X0 Y0 ; Return to home")
    print("G-code generation complete.")
    return gcode

# (The visualize_gcode_path and analyze_gcode functions remain the same)
def visualize_gcode_path(base_image, gcode):
    """Draws the G-code path onto the base image for debugging."""
    print("Creating toolpath visualization...")
    # Calculate scaling from mm back to pixels for drawing
    scale_x = base_image.width / config.PLOTTER_WIDTH_MM
    scale_y = base_image.height / config.PLOTTER_HEIGHT_MM

    canvas = base_image.convert('RGB')
    draw = ImageDraw.Draw(canvas)
    current_pos_px = (0, 0)
    pen_is_down = False
    g1_pattern = re.compile(r'G1\s+X([\d\.]+)\s+Y([\d\.]+)')

    for command in gcode:
        if command.startswith("M3"): pen_is_down = True
        elif command.startswith("M5"): pen_is_down = False
        match = g1_pattern.search(command)
        if match:
            x_mm = float(match.group(1))
            y_mm = float(match.group(2))
            target_pos_px = (int(x_mm * scale_x), int(y_mm * scale_y))
            line_color = "red" if pen_is_down else "blue"
            draw.line([current_pos_px, target_pos_px], fill=line_color, width=1)
            current_pos_px = target_pos_px
    
    canvas.save("debug_02_toolpath_visualization.png")
    print("Visualization saved.")

def analyze_gcode(gcode):
    """Calculates the total drawing distance vs. travel distance."""
    # (This function is unchanged)
    draw_dist, travel_dist, current_pos, pen_is_down = 0.0, 0.0, (0.0, 0.0), False
    g1_pattern = re.compile(r'G1\s+X([\d\.]+)\s+Y([\d\.]+)')
    for command in gcode:
        if "M3" in command: pen_is_down = True
        elif "M5" in command: pen_is_down = False
        match = g1_pattern.search(command)
        if match:
            target_x, target_y = float(match.group(1)), float(match.group(2))
            dist = math.sqrt((target_x - current_pos[0])**2 + (target_y - current_pos[1])**2)
            if pen_is_down: draw_dist += dist
            else: travel_dist += dist
            current_pos = (target_x, target_y)
    total_dist = draw_dist + travel_dist
    efficiency = (draw_dist / total_dist) * 100 if total_dist > 0 else 0
    print("\n--- G-code Path Analysis ---")
    print(f"Total Drawing Distance: {draw_dist:.2f} mm")
    print(f"Total Travel Distance:  {travel_dist:.2f} mm")
    print(f"Path Efficiency:        {efficiency:.2f}%")
    print("----------------------------")