"""
Triggerbot for MirAi
Handles auto-clicking when target is in crosshair.
"""

import time
import ctypes
import threading
from typing import Optional, Tuple
from dataclasses import dataclass

# Mouse constants
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

class Triggerbot:
    """Triggerbot logic handling different firing modes."""
    
    def __init__(self):
        self.user32 = ctypes.windll.user32
        
        # State
        self.is_aiming_at_target = False
        self.last_shot_time = 0
        self.is_holding = False
        self.target_on_crosshair_time = 0
        
        # Config (will be updated from main)
        self.enabled = False
        self.mode = "hold"  # rapid, hold, single
        self.delay = 0.1
        self.interval = 0.1
        
        # Thread safety
        self.lock = threading.Lock()
    
    def update_state(self, is_aiming_at_target: bool):
        """Update aiming state called from detection loop."""
        now = time.time()
        
        with self.lock:
            if is_aiming_at_target:
                if not self.is_aiming_at_target:
                    # Just started aiming at target
                    self.target_on_crosshair_time = now
            else:
                self.target_on_crosshair_time = 0
                if self.is_holding:
                    self._release_mouse()
            
            self.is_aiming_at_target = is_aiming_at_target
            
            if self.enabled and self.is_aiming_at_target:
                # Check delay
                if now - self.target_on_crosshair_time >= self.delay:
                    self._process_trigger(now)
    
    def _process_trigger(self, now: float):
        """Process trigger logic based on mode."""
        if self.mode == "rapid":
            if now - self.last_shot_time >= self.interval:
                self._click_mouse()
                self.last_shot_time = now
                
        elif self.mode == "single":
            # Fire only once per target acquisition
            # We use a long interval or flag logic
            if now - self.last_shot_time >= 0.5: # Min debounce for single
                 self._click_mouse()
                 self.last_shot_time = now
                 
        elif self.mode == "hold":
            # Hold down mouse button
            if not self.is_holding:
                self._press_mouse()
    
    def _click_mouse(self):
        """Perform a single click."""
        self.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.01 + (self.interval * 0.1)) # Tiny randomized sleep maybe?
        self.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    
    def _press_mouse(self):
        """Press and hold mouse button."""
        self.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        self.is_holding = True
        
    def _release_mouse(self):
        """Release mouse button."""
        self.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        self.is_holding = False
    
    def update_config(self, enabled: bool, mode: str, delay: float, interval: float):
        """Update configuration."""
        with self.lock:
            self.enabled = enabled
            self.mode = mode
            self.delay = delay
            self.interval = interval
            
            # Safety: Release if disabled
            if not enabled and self.is_holding:
                self._release_mouse()
