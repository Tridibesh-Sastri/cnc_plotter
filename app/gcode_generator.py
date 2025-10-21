# app/gcode_generator.py

from PIL import Image, ImageDraw
import re
import math
from scipy.spatial import KDTree
import numpy as np # We'll use NumPy for the math-heavy arc fitting
from . import config

# --- NEW ARC FITTING ALGORITHM ---
def fit_arc(points, tolerance):
    """
    Tries to fit a circular arc to a list of points using a least-squares method.
    Returns (end_point, center_offsets, direction) if successful, otherwise None.
    """
    if len(points) < 3:
        return None

    # Use NumPy for efficient calculations
    pts = np.array(points)
    x = pts[:, 0]
    y = pts[:, 1]

    # Least-squares circle fitting algorithm
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    u = x - x_mean
    v = y - y_mean

    Suu = np.sum(u**2)
    Svv = np.sum(v**2)
    Suv = np.sum(u * v)
    Suuu = np.sum(u**3)
    Svvv = np.sum(v**3)
    Suvv = np.sum(u * v**2)
    Svuu = np.sum(v * u**2)

    A = np.array([[Suu, Suv], [Suv, Svv]])
    B = np.array([-(Suuu + Suvv) / 2.0, -(Svvv + Svuu) / 2.0])

    try:
        # Solve for the center of the circle
        uc, vc = np.linalg.solve(A, B)
        center_x = uc + x_mean
        center_y = vc + y_mean
        radius = np.sqrt(uc**2 + vc**2 + (Suu + Svv) / len(x))

        # Check if all points are within the tolerance of this circle
        distances = np.sqrt((x - center_x)**2 + (y - center_y)**2)
        errors = np.abs(distances - radius)
        if np.max(errors) > tolerance:
            return None # The points do not form a good circle

        start_point = points[0]
        end_point = points[-1]

        # Determine arc direction (clockwise G2 or counter-clockwise G3)
        # using the cross product of vectors from start to middle and start to end
        mid_point = points[len(points) // 2]
        cross_product = (mid_point[0] - start_point[0]) * (end_point[1] - start_point[1]) - \
                        (mid_point[1] - start_point[1]) * (end_point[0] - start_point[0])
        
        direction = 'G2' if cross_product > 0 else 'G3'

        # Center offsets (I, J) are relative to the start point
        i_offset = center_x - start_point[0]
        j_offset = center_y - start_point[1]

        return (end_point, (i_offset, j_offset), direction)

    except np.linalg.LinAlgError:
        # This happens if points are perfectly collinear, which can't form a circle
        return None

# --- RDP ALGORITHM (Unchanged) ---
def ramer_douglas_peucker(point_list, epsilon):
    # ... (function is unchanged from before)
    if len(point_list) < 3: return point_list
    dmax, index = 0, 0
    start, end = point_list[0], point_list[-1]
    for i in range(1, len(point_list) - 1):
        d = perpendicular_distance(point_list[i], start, end)
        if d > dmax: index, dmax = i, d
    if dmax > epsilon:
        rec1 = ramer_douglas_peucker(point_list[:index + 1], epsilon)
        rec2 = ramer_douglas_peucker(point_list[index:], epsilon)
        return rec1[:-1] + rec2
    else: return [start, end]

def perpendicular_distance(point, line_start, line_end):
    # ... (function is unchanged from before)
    x1, y1 = line_start
    x2, y2 = line_end
    x0, y0 = point
    num = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1)
    den = math.sqrt((y2 - y1)**2 + (x2 - x1)**2)
    return num / den if den != 0 else math.sqrt((x0 - x1)**2 + (y0 - y1)**2)

# --- MAIN G-CODE GENERATOR (HEAVILY MODIFIED) ---
def generate_kdtree_gcode(image):
    """
    Generates a highly optimized and simplified G-code path by finding,
    sorting, and then processing all drawing paths (islands).
    """
    
    print("Finding all black pixels...")
    pixels = image.load()
    width, height = image.size
    
    point_list = []
    for y in range(height):
        for x in range(width):
            if pixels[x, y] == 0:
                point_list.append((x, y))

    if not point_list:
        print("No black pixels found.")
        return ["M5", "G1 X0 Y0"]

    print(f"Found {len(point_list)} points. Building k-d tree and finding islands...")
    
    kdtree = KDTree(point_list)
    visited = [False] * len(point_list)
    
    # --- PHASE 1: FIND ALL ISLANDS ---
    all_islands = []
    for i in range(len(point_list)):
        if not visited[i]:
            current_index = i
            raw_path = []
            
            while True:
                visited[current_index] = True
                raw_path.append(point_list[current_index])

                distances, indices = kdtree.query(point_list[current_index], k=10, 
                                                  distance_upper_bound=(config.SEARCH_RADIUS_MM / (config.PLOTTER_WIDTH_MM / width)))

                found_neighbor = False
                for idx in indices:
                    if idx < len(point_list) and not visited[idx]:
                        current_index = idx
                        found_neighbor = True
                        break
                
                if not found_neighbor:
                    break
            
            all_islands.append(raw_path)
    
    print(f"Found {len(all_islands)} distinct drawing islands.")

    # --- PHASE 2: SORT THE ISLANDS ---
    all_islands.sort(key=lambda path: (min(p[1] for p in path), min(p[0] for p in path)))
    print("Sorted all islands from top-to-bottom.")

    # --- PHASE 3: GENERATE G-CODE FROM SORTED, SIMPLIFIED ISLANDS ---
    gcode = []
    gcode.append("; Generated with Sorted Arc Fitting & RDP Simplification")
    gcode.append("M5 ; Pen Up")
    gcode.append("G1 X0 Y0 F5000")

    scale_x = config.PLOTTER_WIDTH_MM / width
    scale_y = config.PLOTTER_HEIGHT_MM / height

    for island_path in all_islands:
        simplified_path_points = ramer_douglas_peucker(island_path, config.RDP_EPSILON)
        
        if simplified_path_points:
            start_point = simplified_path_points[0]
            gcode.append(f"G1 X{start_point[0] * scale_x:.2f} Y{start_point[1] * scale_y:.2f} F5000")
            gcode.append("M3 ; Pen Down")

            for i in range(len(simplified_path_points) - 1):
                segment_start = simplified_path_points[i]
                segment_end = simplified_path_points[i+1]
                
                start_idx_in_raw = island_path.index(segment_start)
                end_idx_in_raw = island_path.index(segment_end)
                # Handle cases where index might not find the exact point
                if start_idx_in_raw > end_idx_in_raw:
                    start_idx_in_raw, end_idx_in_raw = end_idx_in_raw, start_idx_in_raw
                segment_points = island_path[start_idx_in_raw : end_idx_in_raw + 1]

                arc_data = fit_arc(segment_points, config.ARC_FITTING_TOLERANCE)

                if arc_data:
                    end_pt, (i_off, j_off), direction = arc_data
                    gcode.append(f"{direction} X{end_pt[0] * scale_x:.2f} Y{end_pt[1] * scale_y:.2f} I{i_off * scale_x:.2f} J{j_off * scale_y:.2f} F2000")
                else:
                    gcode.append(f"G1 X{segment_end[0] * scale_x:.2f} Y{segment_end[1] * scale_y:.2f} F2000")

            gcode.append("M5 ; Pen Up")
            
    gcode.append("G1 X0 Y0 ; Return to home")
    print("G-code generation complete.")
    return gcode


# --- VISUALIZER AND ANALYZER (Unchanged but included for completeness) ---
def visualize_gcode_path(base_image, gcode):
    # ... (function is unchanged from before)
    print("Creating toolpath visualization...")
    scale_x = base_image.width / config.PLOTTER_WIDTH_MM
    scale_y = base_image.height / config.PLOTTER_HEIGHT_MM
    canvas = base_image.convert('RGB')
    draw = ImageDraw.Draw(canvas)
    current_pos_px, pen_is_down = (0, 0), False
    g_pattern = re.compile(r'G([123])\s+X([\d\.-]+)\s+Y([\d\.-]+)')
    for command in gcode:
        if command.startswith("M3"): pen_is_down = True
        elif command.startswith("M5"): pen_is_down = False
        match = g_pattern.search(command)
        if match:
            x_mm, y_mm = float(match.group(2)), float(match.group(3))
            target_pos_px = (int(x_mm * scale_x), int(y_mm * scale_y))
            # Draw arcs as green lines for now to differentiate them
            if pen_is_down:
                line_color = "lime" if match.group(1) in ['2', '3'] else "red"
            else:
                line_color = "blue"
            draw.line([current_pos_px, target_pos_px], fill=line_color, width=1)
            current_pos_px = target_pos_px
    canvas.save("debug_02_toolpath_visualization.png")
    print("Visualization saved.")

def analyze_gcode(gcode):
    # ... (function is unchanged from before)
    draw_dist, travel_dist, current_pos, pen_is_down = 0.0, 0.0, (0.0, 0.0), False
    g_pattern = re.compile(r'G([123])\s+X([\d\.-]+)\s+Y([\d\.-]+)') # Updated to catch G1/2/3
    ij_pattern = re.compile(r'I([\d\.-]+)\s+J([\d\.-]+)')
    for command in gcode:
        if "M3" in command: pen_is_down = True
        elif "M5" in command: pen_is_down = False
        match = g_pattern.search(command)
        if match:
            g_code_type = match.group(1)
            target_x, target_y = float(match.group(2)), float(match.group(3))
            dist = 0
            if g_code_type == '1': # Linear move
                dist = math.sqrt((target_x - current_pos[0])**2 + (target_y - current_pos[1])**2)
            elif g_code_type in ['2', '3']: # Arc move
                ij_match = ij_pattern.search(command)
                if ij_match:
                    i_off, j_off = float(ij_match.group(1)), float(ij_match.group(2))
                    radius = math.sqrt(i_off**2 + j_off**2)
                    # Arc length approximation
                    chord = math.sqrt((target_x - current_pos[0])**2 + (target_y - current_pos[1])**2)
                    if radius > chord/2:
                        angle = 2 * math.asin((chord / 2) / radius)
                        dist = radius * angle
                    else: # Fallback to linear distance
                         dist = chord
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