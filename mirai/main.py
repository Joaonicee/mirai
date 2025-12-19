"""
MirAi - Universal Computer Vision Aimbot
Main application entry point.
"""

import sys
import os
import threading
import time
import keyboard
from typing import Optional, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import customtkinter as ctk

from config.config_manager import ConfigManager, get_config
from core.model_loader import ModelLoader
from core.screen_capture import ScreenCapture
from core.detector import Detector, Detection
from core.aim_controller import AimController
from core.triggerbot import Triggerbot
from overlay.overlay_window import OverlayWindow, OverlayBox
from ui.main_window import MainWindow


class MirAiApp:
    """Main application controller."""
    
    def __init__(self):
        # Configuration
        self.config = get_config()
        
        # Core components
        self.model_loader = ModelLoader()
        self.screen_capture = ScreenCapture()
        self.detector = Detector()
        self.aim_controller = AimController()
        self.triggerbot = Triggerbot()
        self.overlay = OverlayWindow()
        
        # State
        self.aimbot_active = False
        self.running = True
        self.detection_thread: Optional[threading.Thread] = None
        
        # FPS tracking
        self.current_fps = 0.0
        self.frame_times: List[float] = []
        
        # UI
        self.window: Optional[MainWindow] = None
        
        # Setup hotkey
        self._setup_hotkey()
    
    def _setup_hotkey(self) -> None:
        """Setup the toggle hotkey."""
        hotkey = self.config.get('hotkey_toggle', 'insert')
        keyboard.on_press_key(hotkey, lambda _: self._toggle_aimbot())
    
    def _toggle_aimbot(self) -> None:
        """Toggle aimbot on/off."""
        self.aimbot_active = not self.aimbot_active
        print(f"[MirAi] Aimbot {'ON' if self.aimbot_active else 'OFF'}")
        
        # Update UI (thread-safe)
        if self.window:
            self.window.after(0, lambda: self.window.set_aimbot_status(self.aimbot_active))
    
    def _on_setting_changed(self, key: str, value) -> None:
        """Handle setting changes from UI."""
        print(f"[Config] {key} = {value}")
        
        if key == "load_model":
            self._load_model(value)
        elif key == "show_overlay":
            if value and not self.overlay.running:
                self.overlay.start()
            elif not value and self.overlay.running:
                self.overlay.stop()
        elif key == "show_fov_circle":
            self.overlay.update(self.overlay.boxes, show_fov=value)
        elif key == "fov_radius":
            self.config.fov_radius = value
            self.overlay.update(self.overlay.boxes, fov_radius=value)
        elif key.startswith("triggerbot_"):
            # Update triggerbot config
            self.config.set(key, value)
            self.triggerbot.update_config(
                self.config.triggerbot_enabled,
                self.config.triggerbot_mode,
                self.config.triggerbot_delay,
                self.config.triggerbot_interval
            )
        else:
            # Update config
            self.config.set(key, value)
    
    def _load_model(self, path: str) -> None:
        """Load a YOLO model."""
        if not path:
            if self.window:
                self.window.set_model_status("No model path specified", False)
            return
        
        if self.window:
            self.window.set_model_status("Loading model...", True)
        
        # Load in background to not block UI
        def load():
            success, message = self.model_loader.load_model(path)
            
            if self.window:
                self.window.after(0, lambda: self.window.set_model_status(message, success))
                
                if success:
                    classes = self.model_loader.get_classes()
                    self.window.after(0, lambda: self.window.set_classes(classes))
                    self.config.model_path = path
        
        threading.Thread(target=load, daemon=True).start()
    
    def _detection_loop(self) -> None:
        """Main detection loop running in background thread."""
        print("[MirAi] Detection loop started")
        
        while self.running:
            loop_start = time.perf_counter()
            
            # Check if aimbot is active and model is loaded
            if self.aimbot_active and self.model_loader.is_loaded():
                try:
                    self._process_frame()
                except Exception as e:
                    print(f"[MirAi] Detection error: {e}")
            
            # Calculate frame time and sleep to hit target FPS
            elapsed = time.perf_counter() - loop_start
            target_time = 1.0 / self.config.target_fps
            
            if elapsed < target_time:
                time.sleep(target_time - elapsed)
            
            # Update FPS
            frame_time = time.perf_counter() - loop_start
            self.frame_times.append(frame_time)
            if len(self.frame_times) > 30:
                self.frame_times.pop(0)
            
            if self.frame_times:
                avg_time = sum(self.frame_times) / len(self.frame_times)
                self.current_fps = 1.0 / avg_time if avg_time > 0 else 0
        
        print("[MirAi] Detection loop stopped")
    
    def _process_frame(self) -> None:
        """Process a single frame."""
        fov_radius = self.config.fov_radius
        
        # Capture screen region around center
        frame, offset = self.screen_capture.capture_fov(fov_radius)
        
        # Get target classes
        target_classes = self.config.target_classes
        if not target_classes:
            target_classes = None  # All classes
        
        # Run detection
        results = self.model_loader.predict(
            frame,
            conf=self.config.confidence_threshold,
            classes=target_classes
        )
        
        # Process results
        detections = self.detector.process_results(
            results,
            offset=offset,
            target_classes=target_classes,
            confidence_threshold=self.config.confidence_threshold
        )
        
        # Update overlay
        if self.config.show_overlay:
            boxes = [
                OverlayBox(
                    x1=int(d.x1),
                    y1=int(d.y1),
                    x2=int(d.x2),
                    y2=int(d.y2),
                    confidence=d.confidence,
                    label=d.class_name
                )
                for d in detections
            ]
            self.overlay.update(
                boxes,
                fov_radius=fov_radius,
                show_fov=self.config.show_fov_circle
            )
        
        # Select target and aim
        if detections:
            target = self.detector.select_target(
                detections,
                self.screen_capture.center,
                fov_radius,
                head_offset=self.config.head_offset
            )
            
            if target:
                offset = self.detector.get_target_offset(
                    target,
                    self.screen_capture.center,
                    head_offset=self.config.head_offset
                )
                
                self.aim_controller.aim_at_target(
                    offset,
                    smoothness=self.config.aim_smoothness,
                    speed=self.config.aim_speed
                )
        
        # Triggerbot logic
        is_on_target = False
        if detections and (self.config.triggerbot_enabled or self.config.triggerbot_magnet):
            cx, cy = self.screen_capture.center
            for det in detections:
                if det.x1 <= cx <= det.x2 and det.y1 <= cy <= det.y2:
                    is_on_target = True
                    break
        
        if self.aimbot_active:
            self.triggerbot.update_state(is_on_target)
    
    def _update_fps_display(self) -> None:
        """Periodically update FPS display in UI."""
        if self.window and self.running:
            self.window.update_fps(self.current_fps)
            self.window.after(500, self._update_fps_display)
    
    def run(self) -> None:
        """Run the application."""
        print("[MirAi] Starting...")
        
        # Set CustomTkinter appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        
        # Create main window
        self.window = MainWindow(
            on_setting_changed=self._on_setting_changed,
            on_close=self._on_close
        )
        
        # Load saved settings
        self.window.load_settings(self.config.to_dict())
        
        # Init triggerbot config
        self.triggerbot.update_config(
            self.config.triggerbot_enabled,
            self.config.triggerbot_mode,
            self.config.triggerbot_delay,
            self.config.triggerbot_interval
        )
        
        # Start overlay
        if self.config.show_overlay:
            self.overlay.start()
        
        # Start detection thread
        self.detection_thread = threading.Thread(target=self._detection_loop, daemon=True)
        self.detection_thread.start()
        
        # Start FPS display update
        self.window.after(500, self._update_fps_display)
        
        # Load model if path is saved
        if self.config.model_path:
            self._load_model(self.config.model_path)
        
        print("[MirAi] Running. Press INSERT to toggle aimbot.")
        
        # Run main loop
        self.window.mainloop()
    
    def _on_close(self) -> None:
        """Handle application close."""
        print("[MirAi] Shutting down...")
        self.running = False
        self.overlay.stop()
        
        if self.detection_thread:
            self.detection_thread.join(timeout=1.0)
        
        keyboard.unhook_all()


def main():
    """Main entry point."""
    app = MirAiApp()
    app.run()


if __name__ == "__main__":
    main()
