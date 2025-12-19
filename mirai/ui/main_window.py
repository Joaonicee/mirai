"""
Main Window for MirAi
Modern frameless window with custom titlebar.
"""

import customtkinter as ctk
from typing import Optional, Callable
import ctypes
from ctypes import wintypes

from .custom_titlebar import CustomTitlebar
from .settings_panel import SettingsPanel


# Windows constants for taskbar
GWL_EXSTYLE = -20
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080


class MainWindow(ctk.CTk):
    """Main application window with custom titlebar."""
    
    COLORS = {
        'bg': '#1a1a1a',
        'bg_secondary': '#252525',
        'accent': '#ff3333',
        'accent_hover': '#ff5555',
        'text': '#ffffff',
        'text_dim': '#888888',
        'border': '#333333',
    }
    
    def __init__(
        self,
        on_setting_changed: Optional[Callable] = None,
        on_close: Optional[Callable] = None
    ):
        super().__init__()
        
        self.on_setting_changed = on_setting_changed
        self.on_close_callback = on_close
        
        # Configure window
        self.title("MirAi")
        self.geometry("400x700")
        self.minsize(350, 500)
        
        # Remove default titlebar
        self.overrideredirect(True)
        
        # Set dark theme
        self.configure(fg_color=self.COLORS['bg'])
        
        # Create widgets
        self._create_widgets()
        
        # Center window on screen
        self._center_window()
        
        # Make window appear in taskbar (after a delay)
        self.after(10, self._setup_taskbar)
        
        # Bind resize
        self._create_resize_grip()
    
    def _create_widgets(self) -> None:
        """Create main widgets."""
        # Custom titlebar
        self.titlebar = CustomTitlebar(
            self,
            title="MirAi",
            on_close=self._on_close,
            on_minimize=self._on_minimize
        )
        self.titlebar.pack(fill="x", side="top")
        
        # Border effect
        self.border_frame = ctk.CTkFrame(
            self,
            fg_color=self.COLORS['bg'],
            border_width=1,
            border_color=self.COLORS['border'],
            corner_radius=0
        )
        self.border_frame.pack(fill="both", expand=True, padx=1, pady=(0, 1))
        
        # Main content area
        self.content_frame = ctk.CTkFrame(
            self.border_frame,
            fg_color=self.COLORS['bg']
        )
        self.content_frame.pack(fill="both", expand=True)
        
        # Header with status
        self._create_header()
        
        # Settings panel
        self.settings_panel = SettingsPanel(
            self.content_frame,
            on_setting_changed=self._on_setting_changed
        )
        self.settings_panel.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Footer with hotkey info
        self._create_footer()
    
    def _create_header(self) -> None:
        """Create header with status info."""
        header = ctk.CTkFrame(
            self.content_frame,
            fg_color=self.COLORS['bg_secondary'],
            corner_radius=8,
            height=80
        )
        header.pack(fill="x", padx=10, pady=10)
        header.pack_propagate(False)
        
        # Big status indicator
        status_frame = ctk.CTkFrame(header, fg_color="transparent")
        status_frame.pack(expand=True)
        
        self.big_status_label = ctk.CTkLabel(
            status_frame,
            text="AIMBOT OFF",
            font=("Segoe UI", 24, "bold"),
            text_color=self.COLORS['text_dim']
        )
        self.big_status_label.pack()
        
        self.hotkey_label = ctk.CTkLabel(
            status_frame,
            text="Press INSERT to toggle",
            font=("Segoe UI", 11),
            text_color=self.COLORS['text_dim']
        )
        self.hotkey_label.pack()
    
    def _create_footer(self) -> None:
        """Create footer with info."""
        footer = ctk.CTkFrame(
            self.content_frame,
            fg_color=self.COLORS['bg_secondary'],
            corner_radius=8,
            height=40
        )
        footer.pack(fill="x", padx=10, pady=(0, 10))
        footer.pack_propagate(False)
        
        # Info text
        info_label = ctk.CTkLabel(
            footer,
            text="🎮 MirAi Universal Aimbot • Computer Vision Based",
            font=("Segoe UI", 10),
            text_color=self.COLORS['text_dim']
        )
        info_label.pack(expand=True)
    
    def _create_resize_grip(self) -> None:
        """Create resize grip at bottom-right corner."""
        self.grip = ctk.CTkLabel(
            self,
            text="⋮⋮",
            font=("Segoe UI", 10),
            text_color=self.COLORS['text_dim'],
            width=15,
            height=15
        )
        self.grip.place(relx=1.0, rely=1.0, anchor="se")
        
        self._resize_start_x = 0
        self._resize_start_y = 0
        self._resize_start_width = 0
        self._resize_start_height = 0
        
        self.grip.bind("<Button-1>", self._on_resize_start)
        self.grip.bind("<B1-Motion>", self._on_resize)
    
    def _on_resize_start(self, event) -> None:
        """Start window resize."""
        self._resize_start_x = event.x_root
        self._resize_start_y = event.y_root
        self._resize_start_width = self.winfo_width()
        self._resize_start_height = self.winfo_height()
    
    def _on_resize(self, event) -> None:
        """Handle window resize."""
        dx = event.x_root - self._resize_start_x
        dy = event.y_root - self._resize_start_y
        
        new_width = max(self.minsize()[0], self._resize_start_width + dx)
        new_height = max(self.minsize()[1], self._resize_start_height + dy)
        
        self.geometry(f"{new_width}x{new_height}")
    
    def _center_window(self) -> None:
        """Center window on screen."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        self.geometry(f"+{x}+{y}")
    
    def _setup_taskbar(self) -> None:
        """Make window appear in taskbar as independent window."""
        # Get window handle
        hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
        
        # Get current extended style
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        
        # Add APPWINDOW flag (shows in taskbar) and remove TOOLWINDOW (hides from taskbar)
        style = style | WS_EX_APPWINDOW
        style = style & ~WS_EX_TOOLWINDOW
        
        # Set the new style
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        
        # Force window to update
        self.withdraw()
        self.after(10, self.deiconify)
    
    def _on_minimize(self) -> None:
        """Handle minimize."""
        self.withdraw()
        self.after(10, lambda: self.iconify())
        self.after(20, lambda: self.deiconify() if self.state() == 'iconic' else None)
        self.iconify()
    
    def _on_close(self) -> None:
        """Handle close."""
        if self.on_close_callback:
            self.on_close_callback()
        self.quit()
        self.destroy()
    
    def _on_setting_changed(self, key: str, value) -> None:
        """Handle setting change from panel."""
        if self.on_setting_changed:
            self.on_setting_changed(key, value)
    
    def set_aimbot_status(self, active: bool) -> None:
        """Update aimbot status display."""
        self.titlebar.set_status(active)
        
        if active:
            self.big_status_label.configure(
                text="AIMBOT ON",
                text_color=self.COLORS['accent']
            )
        else:
            self.big_status_label.configure(
                text="AIMBOT OFF",
                text_color=self.COLORS['text_dim']
            )
    
    def set_model_status(self, status: str, success: bool = True) -> None:
        """Update model status in settings panel."""
        self.settings_panel.set_model_status(status, success)
    
    def set_classes(self, classes: list) -> None:
        """Update available classes in settings panel."""
        self.settings_panel.set_classes(classes)
    
    def update_fps(self, fps: float) -> None:
        """Update FPS display."""
        self.settings_panel.update_fps(fps)
    
    def load_settings(self, config: dict) -> None:
        """Load settings into UI."""
        self.settings_panel.load_settings(config)
