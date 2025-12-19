"""
Custom Titlebar for MirAi
Modern red-themed titlebar with custom buttons.
"""

import customtkinter as ctk
from typing import Callable, Optional
import ctypes


class CustomTitlebar(ctk.CTkFrame):
    """Custom titlebar with minimize, maximize, and close buttons."""
    
    # Color scheme
    COLORS = {
        'bg': '#1a1a1a',
        'bg_hover': '#252525',
        'accent': '#ff3333',
        'accent_hover': '#ff5555',
        'accent_dark': '#cc0000',
        'text': '#ffffff',
        'text_dim': '#888888',
        'button_hover': '#333333',
        'close_hover': '#ff3333',
    }
    
    def __init__(
        self,
        parent,
        title: str = "MirAi",
        on_close: Optional[Callable] = None,
        on_minimize: Optional[Callable] = None,
        on_maximize: Optional[Callable] = None
    ):
        super().__init__(parent, height=32, fg_color=self.COLORS['bg'])
        
        self.parent = parent
        self.on_close = on_close
        self.on_minimize = on_minimize
        self.on_maximize = on_maximize
        self.is_maximized = False
        
        # Prevent frame from shrinking
        self.pack_propagate(False)
        
        # Store initial position for dragging
        self._drag_start_x = 0
        self._drag_start_y = 0
        
        self._create_widgets(title)
        self._bind_events()
    
    def _create_widgets(self, title: str) -> None:
        """Create titlebar widgets."""
        # Left side - Icon and title
        self.left_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.left_frame.pack(side="left", fill="y", padx=(10, 0))
        
        # Icon (simple red dot as placeholder)
        self.icon_label = ctk.CTkLabel(
            self.left_frame,
            text="●",
            font=("Segoe UI", 16, "bold"),
            text_color=self.COLORS['accent']
        )
        self.icon_label.pack(side="left", padx=(0, 8))
        
        # Title
        self.title_label = ctk.CTkLabel(
            self.left_frame,
            text=title,
            font=("Segoe UI", 12, "bold"),
            text_color=self.COLORS['text']
        )
        self.title_label.pack(side="left")
        
        # Right side - Window buttons
        self.buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.buttons_frame.pack(side="right", fill="y")
        
        # Button style
        btn_width = 46
        btn_height = 32
        
        # Minimize button
        self.minimize_btn = ctk.CTkButton(
            self.buttons_frame,
            text="—",
            width=btn_width,
            height=btn_height,
            fg_color="transparent",
            hover_color=self.COLORS['button_hover'],
            text_color=self.COLORS['text'],
            font=("Segoe UI", 10),
            corner_radius=0,
            command=self._on_minimize
        )
        self.minimize_btn.pack(side="left")
        
        # Maximize button
        self.maximize_btn = ctk.CTkButton(
            self.buttons_frame,
            text="□",
            width=btn_width,
            height=btn_height,
            fg_color="transparent",
            hover_color=self.COLORS['button_hover'],
            text_color=self.COLORS['text'],
            font=("Segoe UI", 12),
            corner_radius=0,
            command=self._on_maximize
        )
        self.maximize_btn.pack(side="left")
        
        # Close button
        self.close_btn = ctk.CTkButton(
            self.buttons_frame,
            text="✕",
            width=btn_width,
            height=btn_height,
            fg_color="transparent",
            hover_color=self.COLORS['close_hover'],
            text_color=self.COLORS['text'],
            font=("Segoe UI", 12),
            corner_radius=0,
            command=self._on_close
        )
        self.close_btn.pack(side="left")
        
        # Status indicator (for aimbot on/off)
        self.status_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.status_frame.pack(side="right", fill="y", padx=10)
        
        self.status_dot = ctk.CTkLabel(
            self.status_frame,
            text="●",
            font=("Segoe UI", 10),
            text_color="#555555"
        )
        self.status_dot.pack(side="left", padx=(0, 5))
        
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="OFF",
            font=("Segoe UI", 10),
            text_color=self.COLORS['text_dim']
        )
        self.status_label.pack(side="left")
    
    def _bind_events(self) -> None:
        """Bind mouse events for dragging."""
        # Bind to titlebar and children
        for widget in [self, self.left_frame, self.icon_label, self.title_label]:
            widget.bind("<Button-1>", self._on_drag_start)
            widget.bind("<B1-Motion>", self._on_drag)
            widget.bind("<Double-Button-1>", lambda e: self._on_maximize())
    
    def _on_drag_start(self, event) -> None:
        """Start dragging the window."""
        self._drag_start_x = event.x_root
        self._drag_start_y = event.y_root
    
    def _on_drag(self, event) -> None:
        """Handle window dragging."""
        if self.is_maximized:
            # Restore window first
            self._on_maximize()
        
        # Calculate delta
        dx = event.x_root - self._drag_start_x
        dy = event.y_root - self._drag_start_y
        
        # Get current position
        x = self.parent.winfo_x() + dx
        y = self.parent.winfo_y() + dy
        
        # Move window
        self.parent.geometry(f"+{x}+{y}")
        
        # Update start position
        self._drag_start_x = event.x_root
        self._drag_start_y = event.y_root
    
    def _on_minimize(self) -> None:
        """Handle minimize button click."""
        if self.on_minimize:
            self.on_minimize()
        else:
            self.parent.iconify()
    
    def _on_maximize(self) -> None:
        """Handle maximize button click."""
        if self.on_maximize:
            self.on_maximize()
        else:
            if self.is_maximized:
                self.parent.geometry(self._restore_geometry)
                self.maximize_btn.configure(text="□")
                self.is_maximized = False
            else:
                self._restore_geometry = self.parent.geometry()
                # Get work area (screen minus taskbar)
                user32 = ctypes.windll.user32
                work_area = ctypes.wintypes.RECT()
                user32.SystemParametersInfoW(48, 0, ctypes.byref(work_area), 0)  # SPI_GETWORKAREA
                
                width = work_area.right - work_area.left
                height = work_area.bottom - work_area.top
                
                self.parent.geometry(f"{width}x{height}+{work_area.left}+{work_area.top}")
                self.maximize_btn.configure(text="❐")
                self.is_maximized = True
    
    def _on_close(self) -> None:
        """Handle close button click."""
        if self.on_close:
            self.on_close()
        else:
            self.parent.quit()
    
    def set_status(self, active: bool) -> None:
        """Update the status indicator."""
        if active:
            self.status_dot.configure(text_color=self.COLORS['accent'])
            self.status_label.configure(text="ON", text_color=self.COLORS['accent'])
        else:
            self.status_dot.configure(text_color="#555555")
            self.status_label.configure(text="OFF", text_color=self.COLORS['text_dim'])
