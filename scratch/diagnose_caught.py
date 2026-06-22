import sys
from pathlib import Path
import cv2
import numpy as np

# Add src to path so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from window_capture import WindowCapture, get_window_rect, get_client_rect, find_pokemmo_hwnd
from battle_reader import read_battle, load_calibration, read_caught_icon
import paths

def diagnose():
    hwnd = find_pokemmo_hwnd()
    if not hwnd:
        print("PokeMMO window not found!")
        return

    win_rect = get_window_rect(hwnd)
    client_rect = get_client_rect(hwnd)
    if not win_rect or not client_rect:
        print("Could not get window rects")
        return

    capture = WindowCapture()
    frame = capture.grab(win_rect)

    cal = load_calibration(paths.CALIBRATION_PATH)
    reading = read_battle(frame, cal)

    if not reading.bars:
        print("No enemy HP bars found in the frame. Make sure you are in a battle!")
        return

    bar = reading.bars[0]
    print(f"Found enemy HP bar at x={bar.x}, y={bar.y}")

    c = cal.caught_icon
    h, w = frame.shape[:2]
    x0, x1 = max(0, bar.x + c.dx0), min(w, bar.x + c.dx1)
    y0, y1 = max(0, bar.y + c.dy0), min(h, bar.y + c.dy1)
    
    print(f"Searching for icon in region: x({x0}-{x1}), y({y0}-{y1})")
    
    if x1 <= x0 or y1 <= y0:
        print("Invalid search region bounds")
        return

    crop = frame[y0:y1, x0:x1]
    cv2.imwrite("scratch/caught_crop.png", crop)
    print("Saved crop to scratch/caught_crop.png")

    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    hue, sat, val = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    
    is_red = (hue <= c.red_h_low) | (hue >= c.red_h_high)
    red = is_red & (sat >= c.sat_min) & (val >= c.val_min)
    red_count = int(np.count_nonzero(red))
    
    print("\n--- Calibration Settings ---")
    print(f"Red Hue Range: 0-{c.red_h_low} and {c.red_h_high}-179")
    print(f"Min Saturation: {c.sat_min}")
    print(f"Min Value: {c.val_min}")
    print(f"Target Min Red Pixels: {c.min_red_px}")
    
    print("\n--- Actual Values Seen ---")
    print(f"Number of red pixels detected: {red_count}")
    
    if red_count >= c.min_red_px:
        print("SUCCESS: Icon DETECTED based on current settings.")
    else:
        print("FAILURE: Icon NOT DETECTED. Not enough red pixels.")
        
        # Let's see what the dominant colors are instead
        print("\nAnalyzing what colors are actually in the crop (ignoring dark/faded pixels):")
        bright_pixels = (sat >= c.sat_min) & (val >= c.val_min)
        if not np.any(bright_pixels):
            print("  -> Entire crop is too dark or washed out (doesn't meet sat_min/val_min)")
        else:
            active_hues = hue[bright_pixels]
            unique, counts = np.unique(active_hues, return_counts=True)
            dominant = sorted(zip(counts, unique), reverse=True)[:3]
            for count, h_val in dominant:
                print(f"  -> Found {count} pixels with Hue = {h_val}")

if __name__ == "__main__":
    diagnose()
