# app/config.py
import math

# --- USER-DEFINED TARGETS ---
TARGET_DPI = 600.0  # The ideal resolution we want to process images at.

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