"""
Transparent Overlay Window for MirAi
Renders bounding boxes, confidence, and FOV circle.
Uses Win32 API for transparent, click-through overlay.
"""

import ctypes
from ctypes import wintypes
import threading
import time
from typing import List, Tuple, Optional, Callable
from dataclasses import dataclass

# Win32 constants
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000

GWL_EXSTYLE = -20
LWA_COLORKEY = 0x00000001
LWA_ALPHA = 0x00000002

WM_DESTROY = 0x0002
WM_PAINT = 0x000F
WM_ERASEBKGND = 0x0014

# GDI constants
PS_SOLID = 0
TRANSPARENT = 1
HOLLOW_BRUSH = 5

# Color key for transparency (must match background)
TRANSPARENCY_KEY = 0x000000  # Black will be transparent


@dataclass
class OverlayBox:
    """Represents a box to render on the overlay."""
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float
    label: str
    color: Tuple[int, int, int] = (255, 50, 50)  # BGR -> RGB red


class OverlayWindow:
    """Transparent overlay window for rendering detection visualization."""
    
    def __init__(self):
        self.hwnd = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        # Render data
        self.boxes: List[OverlayBox] = []
        self.fov_radius: int = 150
        self.show_fov: bool = True
        self.screen_center: Tuple[int, int] = (0, 0)
        
        # Screen dimensions
        self.user32 = ctypes.windll.user32
        self.gdi32 = ctypes.windll.gdi32
        self.kernel32 = ctypes.windll.kernel32
        self.screen_width = self.user32.GetSystemMetrics(0)
        self.screen_height = self.user32.GetSystemMetrics(1)
        self.screen_center = (self.screen_width // 2, self.screen_height // 2)
        
        # Lock for thread-safe updates
        self.lock = threading.Lock()
        
        # Store callback
        self._wndproc = None
        
    def start(self) -> bool:
        """Start the overlay window in a separate thread."""
        if self.running:
            return True
            
        self.running = True
        self.thread = threading.Thread(target=self._run_window, daemon=True)
        self.thread.start()
        
        # Wait for window to be created
        timeout = 2.0
        start = time.time()
        while self.hwnd is None and time.time() - start < timeout:
            time.sleep(0.01)
            
        return self.hwnd is not None
    
    def stop(self) -> None:
        """Stop the overlay window."""
        self.running = False
        if self.hwnd:
            self.user32.PostMessageW(self.hwnd, WM_DESTROY, 0, 0)
        if self.thread:
            self.thread.join(timeout=1.0)
        self.hwnd = None
    
    def update(
        self,
        boxes: List[OverlayBox],
        fov_radius: Optional[int] = None,
        show_fov: Optional[bool] = None
    ) -> None:
        """
        Update the overlay with new render data.
        
        Args:
            boxes: List of boxes to render
            fov_radius: FOV radius (optional update)
            show_fov: Whether to show FOV circle (optional update)
        """
        with self.lock:
            if boxes:
                self.boxes = boxes.copy()
                self.last_boxes_time = time.time()
            elif time.time() - getattr(self, 'last_boxes_time', 0) > 0.1:  # 100ms persistence
                self.boxes = []
            
            if fov_radius is not None:
                self.fov_radius = fov_radius
            if show_fov is not None:
                self.show_fov = show_fov
        
        # Trigger repaint
        if self.hwnd:
            self.user32.InvalidateRect(self.hwnd, None, True)
    
    def _run_window(self) -> None:
        """Run the overlay window message loop."""
        # Define window class
        WNDPROC = ctypes.WINFUNCTYPE(
            wintypes.LPARAM,
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM
        )
        
        class WNDCLASSEX(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.UINT),
                ("style", wintypes.UINT),
                ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HANDLE),
                ("hIcon", wintypes.HANDLE),
                ("hCursor", wintypes.HANDLE),
                ("hbrBackground", wintypes.HANDLE),
                ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR),
                ("hIconSm", wintypes.HANDLE),
            ]
        
        # Define DefWindowProcW signature
        self.user32.DefWindowProcW.argtypes = [
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM
        ]
        self.user32.DefWindowProcW.restype = wintypes.LPARAM

        def wnd_proc(hwnd, msg, wparam, lparam):
            if msg == WM_PAINT:
                self._on_paint(hwnd)
                return 0
            elif msg == WM_ERASEBKGND:
                return 1
            elif msg == WM_DESTROY:
                self.user32.PostQuitMessage(0)
                return 0
            return self.user32.DefWindowProcW(hwnd, msg, wparam, lparam)
        
        # Store callback to prevent garbage collection
        self._wndproc = WNDPROC(wnd_proc)
        
        # Register window class
        class_name = "MirAiOverlay"
        hinstance = self.kernel32.GetModuleHandleW(None)
        
        wc = WNDCLASSEX()
        wc.cbSize = ctypes.sizeof(WNDCLASSEX)
        wc.style = 0
        wc.lpfnWndProc = self._wndproc
        wc.cbClsExtra = 0
        wc.cbWndExtra = 0
        wc.hInstance = hinstance
        wc.hIcon = 0
        wc.hCursor = 0
        wc.hbrBackground = self.gdi32.GetStockObject(HOLLOW_BRUSH)
        wc.lpszMenuName = None
        wc.lpszClassName = class_name
        wc.hIconSm = 0
        
        if not self.user32.RegisterClassExW(ctypes.byref(wc)):
            print("[Overlay] Failed to register window class")
            return
        
        # Create window
        ex_style = WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_TOOLWINDOW
        style = WS_POPUP | WS_VISIBLE
        
        self.hwnd = self.user32.CreateWindowExW(
            ex_style,
            class_name,
            "MirAi Overlay",
            style,
            0, 0,
            self.screen_width, self.screen_height,
            None, None, hinstance, None
        )
        
        if not self.hwnd:
            print("[Overlay] Failed to create window")
            return
        
        # Set layered window attributes for color key transparency
        self.user32.SetLayeredWindowAttributes(
            self.hwnd,
            TRANSPARENCY_KEY,
            255,
            LWA_COLORKEY
        )
        
        # Message loop
        msg = wintypes.MSG()
        while self.running:
            while self.user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                if msg.message == 0x0012:  # WM_QUIT
                    self.running = False
                    break
                self.user32.TranslateMessage(ctypes.byref(msg))
                self.user32.DispatchMessageW(ctypes.byref(msg))
            
            # Small sleep to prevent CPU spinning
            time.sleep(0.001)
        
        # Cleanup
        if self.hwnd:
            self.user32.DestroyWindow(self.hwnd)
        self.user32.UnregisterClassW(class_name, hinstance)
    
    def _on_paint(self, hwnd) -> None:
        """Handle paint message."""
        # Begin paint
        class PAINTSTRUCT(ctypes.Structure):
            _fields_ = [
                ("hdc", wintypes.HDC),
                ("fErase", wintypes.BOOL),
                ("rcPaint", wintypes.RECT),
                ("fRestore", wintypes.BOOL),
                ("fIncUpdate", wintypes.BOOL),
                ("rgbReserved", wintypes.BYTE * 32),
            ]
        
        ps = PAINTSTRUCT()
        hdc = self.user32.BeginPaint(hwnd, ctypes.byref(ps))
        
        # Clear with transparency key
        brush = self.gdi32.CreateSolidBrush(TRANSPARENCY_KEY)
        rect = wintypes.RECT(0, 0, self.screen_width, self.screen_height)
        self.user32.FillRect(hdc, ctypes.byref(rect), brush)
        self.gdi32.DeleteObject(brush)
        
        # Set text background to transparent
        self.gdi32.SetBkMode(hdc, TRANSPARENT)
        
        with self.lock:
            # Draw FOV circle
            if self.show_fov:
                self._draw_fov_circle(hdc)
            
            # Draw boxes
            for box in self.boxes:
                self._draw_box(hdc, box)
        
        # End paint
        self.user32.EndPaint(hwnd, ctypes.byref(ps))
    
    def _draw_fov_circle(self, hdc) -> None:
        """Draw the FOV circle."""
        cx, cy = self.screen_center
        r = self.fov_radius
        
        # Create red pen
        pen = self.gdi32.CreatePen(PS_SOLID, 2, 0x3333FF)  # BGR red
        old_pen = self.gdi32.SelectObject(hdc, pen)
        
        # Create hollow brush
        old_brush = self.gdi32.SelectObject(hdc, self.gdi32.GetStockObject(HOLLOW_BRUSH))
        
        # Draw ellipse
        self.gdi32.Ellipse(hdc, cx - r, cy - r, cx + r, cy + r)
        
        # Cleanup
        self.gdi32.SelectObject(hdc, old_pen)
        self.gdi32.SelectObject(hdc, old_brush)
        self.gdi32.DeleteObject(pen)
    
    def _draw_box(self, hdc, box: OverlayBox) -> None:
        """Draw a detection box with label."""
        # Create pen (BGR format)
        color = (box.color[2] | (box.color[1] << 8) | (box.color[0] << 16))
        pen = self.gdi32.CreatePen(PS_SOLID, 2, color)
        old_pen = self.gdi32.SelectObject(hdc, pen)
        
        # Create hollow brush
        old_brush = self.gdi32.SelectObject(hdc, self.gdi32.GetStockObject(HOLLOW_BRUSH))
        
        # Draw rectangle
        self.gdi32.Rectangle(hdc, box.x1, box.y1, box.x2, box.y2)
        
        # Draw label
        label = f"{box.label} {box.confidence:.0%}"
        self.gdi32.SetTextColor(hdc, color)
        self.user32.DrawTextW(
            hdc,
            label,
            -1,
            ctypes.byref(wintypes.RECT(box.x1, box.y1 - 20, box.x2 + 100, box.y1)),
            0
        )
        
        # Cleanup
        self.gdi32.SelectObject(hdc, old_pen)
        self.gdi32.SelectObject(hdc, old_brush)
        self.gdi32.DeleteObject(pen)
