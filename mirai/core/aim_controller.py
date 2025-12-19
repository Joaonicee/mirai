"""
Aim Controller for MirAi
Handles mouse movement for aiming.
"""

import ctypes
from ctypes import wintypes
import time
from typing import Tuple
import math


# Windows API constants
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_ABSOLUTE = 0x8000


class AimController:
    """Controls mouse movement for aiming."""
    
    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.last_move_time = 0
        self.min_move_interval = 0.001  # Minimum time between moves
        
    def move_mouse_relative(self, dx: int, dy: int) -> None:
        """
        Move mouse by relative offset.
        
        Args:
            dx: Horizontal offset
            dy: Vertical offset
        """
        # Use ctypes for fast mouse movement
        self.user32.mouse_event(MOUSEEVENTF_MOVE, int(dx), int(dy), 0, 0)
    
    def move_mouse_absolute(self, x: int, y: int) -> None:
        """
        Move mouse to absolute position.
        
        Args:
            x: Screen X coordinate
            y: Screen Y coordinate
        """
        # Get screen dimensions
        screen_width = self.user32.GetSystemMetrics(0)
        screen_height = self.user32.GetSystemMetrics(1)
        
        # Convert to normalized coordinates (0-65535)
        abs_x = int(x * 65535 / screen_width)
        abs_y = int(y * 65535 / screen_height)
        
        self.user32.mouse_event(
            MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE,
            abs_x, abs_y, 0, 0
        )
    
    def aim_at_target(
        self,
        offset: Tuple[float, float],
        smoothness: float = 0.5,
        speed: float = 1.0
    ) -> bool:
        """
        Aim at target with smooth movement.
        
        Args:
            offset: (dx, dy) offset from current position to target
            smoothness: How smooth the movement should be (0.1 = instant, 1.0 = very smooth)
            speed: Speed multiplier
            
        Returns:
            True if moved, False if already on target
        """
        dx, dy = offset
        
        # Check if already on target (within deadzone)
        distance = math.sqrt(dx * dx + dy * dy)
        if distance < 1:
            return False
        
        # Apply smoothing
        # Lower smoothness = faster movement
        factor = (1.0 - smoothness) * speed
        factor = max(0.1, min(1.0, factor))
        
        # Calculate movement amount
        move_x = dx * factor
        move_y = dy * factor
        
        # Ensure minimum movement of 1 pixel if there's significant offset
        if abs(move_x) < 1 and abs(dx) >= 1:
            move_x = 1 if dx > 0 else -1
        if abs(move_y) < 1 and abs(dy) >= 1:
            move_y = 1 if dy > 0 else -1
        
        # Move mouse
        self.move_mouse_relative(int(move_x), int(move_y))
        return True
    
    def get_cursor_position(self) -> Tuple[int, int]:
        """Get current cursor position."""
        point = wintypes.POINT()
        self.user32.GetCursorPos(ctypes.byref(point))
        return (point.x, point.y)
