"""
YOLO Trainer App - Main application class
"""

import customtkinter as ctk
import ctypes
from ctypes import wintypes
from .themes.red_theme import RedTheme
from .components.title_bar import CustomTitleBar
from .components.training_panel import TrainingPanel


# Windows API constants
GWL_STYLE = -16
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_SYSMENU = 0x00080000

# For proper taskbar icon
GWL_EXSTYLE = -20
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080


class YOLOTrainerApp:
    """Main YOLO Trainer Application"""
    
    def __init__(self):
        # Configure CustomTkinter appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        
        # Create main window
        self.root = ctk.CTk()
        self.root.title("YOLO Trainer")
        
        # Window size
        self.window_width = 900
        self.window_height = 800
        
        # Center window on screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - self.window_width) // 2
        y = (screen_height - self.window_height) // 2
        
        self.root.geometry(f"{self.window_width}x{self.window_height}+{x}+{y}")
        self.root.minsize(800, 600)
        
        # Set background color
        self.root.configure(fg_color=RedTheme.BG_PRIMARY)
        
        # Add window border effect
        self._create_window_border()
        
        # Create UI components
        self._create_ui()
        
        # Apply custom window style after window is created
        self.root.update_idletasks()
        self._setup_frameless_window()
        
        # Bring window to front
        self.root.lift()
        self.root.focus_force()
    
    def _setup_frameless_window(self):
        """Setup frameless window using Windows API while keeping taskbar presence"""
        try:
            # Get window handle
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            
            # Get current window style
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
            
            # Remove title bar and thick frame but keep minimize/maximize/sysmenu for taskbar
            style = style & ~WS_CAPTION  # Remove title bar
            style = style & ~WS_THICKFRAME  # Remove resize border
            style = style | WS_MINIMIZEBOX  # Keep minimize capability
            style = style | WS_MAXIMIZEBOX  # Keep maximize capability
            style = style | WS_SYSMENU  # Keep system menu (needed for taskbar)
            
            # Apply new style
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style)
            
            # Ensure window appears in taskbar
            ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ex_style = ex_style | WS_EX_APPWINDOW  # Force show in taskbar
            ex_style = ex_style & ~WS_EX_TOOLWINDOW  # Remove tool window style
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
            
            # Redraw window frame
            ctypes.windll.user32.SetWindowPos(
                hwnd, 0, 0, 0, 0, 0,
                0x0001 | 0x0002 | 0x0004 | 0x0020  # SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_FRAMECHANGED
            )
        except Exception as e:
            print(f"Warning: Could not apply custom window style: {e}")
            # Fallback to overrideredirect if Windows API fails
            self.root.overrideredirect(True)
    
    def _create_window_border(self):
        """Create a subtle border around the window"""
        # Main border frame
        self.border_frame = ctk.CTkFrame(
            self.root,
            fg_color=RedTheme.BG_PRIMARY,
            border_width=1,
            border_color=RedTheme.BORDER,
            corner_radius=0
        )
        self.border_frame.pack(fill="both", expand=True)
    
    def _create_ui(self):
        """Create the main UI components"""
        # Custom title bar
        self.title_bar = CustomTitleBar(
            self.border_frame,
            title="YOLO Trainer",
            app_icon="🎯"
        )
        self.title_bar.pack(fill="x")
        
        # Red accent line under title bar
        accent_line = ctk.CTkFrame(
            self.border_frame,
            height=2,
            fg_color=RedTheme.PRIMARY,
            corner_radius=0
        )
        accent_line.pack(fill="x")
        
        # Main content area
        self.training_panel = TrainingPanel(
            self.border_frame,
            on_gpu_status=self._on_gpu_status
        )
        self.training_panel.pack(fill="both", expand=True)
    
    def _on_gpu_status(self, status: str, is_available: bool):
        """Update title bar GPU status"""
        self.title_bar.set_gpu_status(status, is_available)
    
    def run(self):
        """Start the application main loop"""
        self.root.mainloop()


def main():
    """Entry point for the application"""
    app = YOLOTrainerApp()
    app.run()


if __name__ == "__main__":
    main()

