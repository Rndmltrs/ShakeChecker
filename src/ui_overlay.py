"""Shared UI overlay logic: docking constants, window scaling, and Z-order management."""

from __future__ import annotations

import win32api
import win32con
import win32gui
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QWidget

# Base (scale 1.0) sizes in logical px. apply_scale() multiplies these; 1.0 is the
# cap, so the overlay is never larger than this.
DOCK_MARGIN = 12  # gap from the game window's side edge
DOCK_SIDE = "left"  # "left" or "right"
# Push the overlay down past the game's fixed top-left HUD (location, money,
# time, ability, and a possible donator line) AND the enemy HP meter block. 
# The HUD and HP meters are fixed pixel sizes regardless of window size. 
# The HP meter block (including the trainer party icons) extends to ~260px, 
# so 270 ensures we clear it without being unnecessarily low.
DOCK_TOP_OFFSET = 180

# Window-height (physical px) at/above which the overlay is at full size, and the
# smallest scale it will shrink to. Below REF the overlay scales down with the
# window so it stays inside a small battle view.
REF_WINDOW_HEIGHT = 1400
MIN_SCALE = 0.6
UI_SCALE_MULTIPLIER = 1.0  # Manual override multiplier to increase UI size

def scale_for_window(height_px: int) -> float:
    """Overlay scale for a game-window client height."""
    return max(1.0, height_px / REF_WINDOW_HEIGHT) * UI_SCALE_MULTIPLIER

def phys_to_logical(px: int, py: int) -> tuple[int, int]:
    """Convert a physical-pixel screen point (from win32) to Qt's logical-pixel
    coordinates, which move() expects. They differ when Windows display scaling
    is not 100%; without this the overlay lands on the wrong monitor."""
    screens = QGuiApplication.screens()
    if not screens:
        return px, py

    monitors = win32api.EnumDisplayMonitors()
    monitors.sort(key=lambda m: m[2][0])
    screens_sorted = sorted(screens, key=lambda s: s.geometry().x())

    target_idx = 0
    for i, m in enumerate(monitors):
        left, top, right, bottom = m[2]
        if left <= px < right and top <= py < bottom:
            target_idx = i
            break

    if target_idx >= len(screens_sorted):
        target_idx = 0

    phys_left, phys_top, _, _ = monitors[target_idx][2]
    qt_screen = screens_sorted[target_idx]
    dpr = qt_screen.devicePixelRatio()

    lx = qt_screen.geometry().x() + (px - phys_left) / dpr
    ly = qt_screen.geometry().y() + (py - phys_top) / dpr

    return round(lx), round(ly)

def bring_overlay_above_game(widget: QWidget) -> None:
    """Insert the overlay just below the game window in the Z-order,
    without stealing focus or changing its state."""
    try:
        handle = widget.windowHandle()
        if not handle:
            return
        parent = handle.transientParent()
        if not parent:
            return
        game_hwnd = int(parent.winId())
        if not game_hwnd:
            return
        
        hwnd = int(widget.winId())
        prev_hwnd = win32gui.GetWindow(game_hwnd, win32con.GW_HWNDPREV)
        insert_after = prev_hwnd if prev_hwnd else win32con.HWND_TOP
        
        flags = win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE | win32con.SWP_NOOWNERZORDER
        win32gui.SetWindowPos(hwnd, insert_after, 0, 0, 0, 0, flags)
    except Exception:
        pass
