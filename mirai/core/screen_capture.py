"""
Screen Capture for MirAi
High-performance screen capture using mss.
"""

import mss
import numpy as np
from typing import Tuple, Optional
import ctypes


class ScreenCapture:
    """High-performance screen capture utility."""
    
    def __init__(self):
        self.sct = None
        self._screen_width: int = 0
        self._screen_height: int = 0
        self._center_x: int = 0
        self._center_y: int = 0
        self._update_screen_info()
    
    def _update_screen_info(self) -> None:
        """Update screen dimensions."""
        # Get primary monitor info
        user32 = ctypes.windll.user32
        self._screen_width = user32.GetSystemMetrics(0)
        self._screen_height = user32.GetSystemMetrics(1)
        self._center_x = self._screen_width // 2
        self._center_y = self._screen_height // 2
    
    @property
    def screen_width(self) -> int:
        return self._screen_width
    
    @property
    def screen_height(self) -> int:
        return self._screen_height
    
    @property
    def center(self) -> Tuple[int, int]:
        return (self._center_x, self._center_y)
    
    def capture_region(self, x: int, y: int, width: int, height: int) -> np.ndarray:
        """
        Capture a specific region of the screen.
        
        Args:
            x: Left coordinate
            y: Top coordinate
            width: Region width
            height: Region height
            
        Returns:
            numpy array in BGR format
        """
        region = {
            'left': x,
            'top': y,
            'width': width,
            'height': height
        }
        
        if self.sct is None:
            self.sct = mss.mss()
            
        screenshot = self.sct.grab(region)
        # Convert to numpy array and remove alpha channel
        frame = np.array(screenshot)[:, :, :3]
        return frame
    
    def capture_fov(self, fov_radius: int) -> Tuple[np.ndarray, Tuple[int, int]]:
        """
        Capture the region within the FOV circle.
        
        Args:
            fov_radius: Radius of the FOV in pixels
            
        Returns:
            Tuple of (frame, (offset_x, offset_y))
            offset is the top-left corner of the capture region
        """
        # Calculate region around center
        size = fov_radius * 2
        left = max(0, self._center_x - fov_radius)
        top = max(0, self._center_y - fov_radius)
        
        # Ensure we don't go off screen
        right = min(self._screen_width, left + size)
        bottom = min(self._screen_height, top + size)
        
        width = right - left
        height = bottom - top
        
        frame = self.capture_region(left, top, width, height)
        return frame, (left, top)
    
    def capture_fullscreen(self) -> np.ndarray:
        """
        Capture the entire screen.
        
        Returns:
            numpy array in BGR format
        """
        return self.capture_region(0, 0, self._screen_width, self._screen_height)
    
    def release(self) -> None:
        """Release resources."""
        if self.sct:
            self.sct.close()
