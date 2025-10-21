# app/config.py
import math

# --- USER-DEFINED TARGETS ---
TARGET_DPI = 600.0  # The ideal resolution we want to process images at.

# --- ALGORITHM TUNING ---

# NEW: Parameters for cleaning the image before pathfinding
MORPH_CLOSING_ITERATIONS = 2 # How aggressively to merge nearby pixels. Try values between 1-5.
MIN_OBJECT_SIZE_PIXELS = 200  # Minimum size of objects to keep, in pixels.

# RDP Epsilon: A slightly larger value helps identify longer segments to test for curves.
RDP_EPSILON = 2.0 

# NEW: The tolerance for arc fitting, in pixels. How closely the points must follow the fitted circle.
ARC_FITTING_TOLERANCE = 1.0

SEARCH_RADIUS_MM = 5.0

# --- PHYSICAL MACHINE PARAMETERS ---
PLOTTER_WIDTH_MM = 115.0
PLOTTER_HEIGHT_MM = 115.0
EFFECTIVE_STEPS_PER_REV = 4096
BELT_PITCH_MM = 2.0
PULLEY_TEETH = 20
PEN_NIB_MM = 0.5
SEARCH_RADIUS_MM = 5.0

# --- CALCULATED PARAMETERS (Do not edit) ---

# 1. Calculate the machine's true physical resolution
PHYSICAL_STEPS_PER_MM = (EFFECTIVE_STEPS_PER_REV) / (PULLEY_TEETH * BELT_PITCH_MM)
MACHINE_DPI = PHYSICAL_STEPS_PER_MM * 25.4

# 2. Implement your logic to choose the best DPI for processing
if MACHINE_DPI < TARGET_DPI:
    # Case 2: Machine resolution is the limiting factor. Use it directly.
    PROCESSING_DPI = MACHINE_DPI
else:
    # Case 1: Machine resolution is higher than needed. Cap it at the target DPI.
    PROCESSING_DPI = TARGET_DPI

# 3. Calculate the final resolution to be used for image processing
PROCESSING_STEPS_PER_MM = PROCESSING_DPI / 25.4