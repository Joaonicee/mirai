"""
Custom Title Bar - Modern frameless window title bar with red theme
"""

import customtkinter as ctk
from ..themes.red_theme import RedTheme


class CustomTitleBar(ctk.CTkFrame):
    """Custom title bar for frameless window"""
    
    def __init__(self, parent, title: str = "YOLO Trainer", app_icon: str = "🎯"):
        super().__init__(
            parent,
            height=40,
            fg_color=RedTheme.TITLEBAR_BG,
            corner_radius=0
        )
        
        self.parent = parent
        self.title = title
        self.app_icon = app_icon
        
        # For window dragging
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._is_maximized = False
        self._normal_geometry = None
        
        self.pack_propagate(False)
        self._create_widgets()
        self._bind_events()
    
    def _create_widgets(self):
        """Create title bar widgets"""
        # Left side - Icon and Title
        left_frame = ctk.CTkFrame(self, fg_color="transparent")
        left_frame.pack(side="left", padx=10, fill="y")
        
        # App icon
        icon_label = ctk.CTkLabel(
            left_frame,
            text=self.app_icon,
            font=(RedTheme.FONT_FAMILY, 18),
            text_color=RedTheme.PRIMARY
        )
        icon_label.pack(side="left", padx=(0, 8))
        
        # Title
        title_label = ctk.CTkLabel(
            left_frame,
            text=self.title,
            font=(RedTheme.FONT_FAMILY, RedTheme.FONT_SIZE_TITLE, "bold"),
            text_color=RedTheme.TEXT_PRIMARY
        )
        title_label.pack(side="left")
        
        # GPU status indicator (will be updated later)
        self.gpu_status = ctk.CTkLabel(
            left_frame,
            text="",
            font=(RedTheme.FONT_FAMILY, RedTheme.FONT_SIZE_SM),
            text_color=RedTheme.TEXT_MUTED
        )
        self.gpu_status.pack(side="left", padx=(20, 0))
        
        # Right side - Window controls
        right_frame = ctk.CTkFrame(self, fg_color="transparent")
        right_frame.pack(side="right", fill="y")
        
        # Minimize button
        self.min_btn = ctk.CTkButton(
            right_frame,
            text="─",
            width=46,
            height=40,
            corner_radius=0,
            fg_color="transparent",
            hover_color=RedTheme.TITLEBAR_BTN_HOVER,
            text_color=RedTheme.TEXT_PRIMARY,
            font=(RedTheme.FONT_FAMILY, 12),
            command=self._minimize_window
        )
        self.min_btn.pack(side="left")
        
        # Maximize button
        self.max_btn = ctk.CTkButton(
            right_frame,
            text="□",
            width=46,
            height=40,
            corner_radius=0,
            fg_color="transparent",
            hover_color=RedTheme.TITLEBAR_BTN_HOVER,
            text_color=RedTheme.TEXT_PRIMARY,
            font=(RedTheme.FONT_FAMILY, 12),
            command=self._toggle_maximize
        )
        self.max_btn.pack(side="left")
        
        # Close button
        self.close_btn = ctk.CTkButton(
            right_frame,
            text="✕",
            width=46,
            height=40,
            corner_radius=0,
            fg_color="transparent",
            hover_color=RedTheme.TITLEBAR_CLOSE_HOVER,
            text_color=RedTheme.TEXT_PRIMARY,
            font=(RedTheme.FONT_FAMILY, 12),
            command=self._close_window
        )
        self.close_btn.pack(side="left")
        
        # Make the title area draggable
        self._make_draggable(left_frame)
        self._make_draggable(icon_label)
        self._make_draggable(title_label)
    
    def _make_draggable(self, widget):
        """Make a widget draggable for window movement"""
        widget.bind("<Button-1>", self._on_drag_start)
        widget.bind("<B1-Motion>", self._on_drag_motion)
        widget.bind("<Double-Button-1>", self._on_double_click)
    
    def _bind_events(self):
        """Bind title bar events"""
        self.bind("<Button-1>", self._on_drag_start)
        self.bind("<B1-Motion>", self._on_drag_motion)
        self.bind("<Double-Button-1>", self._on_double_click)
    
    def _on_drag_start(self, event):
        """Start dragging the window"""
        self._drag_start_x = event.x
        self._drag_start_y = event.y
    
    def _on_drag_motion(self, event):
        """Handle window dragging"""
        if self._is_maximized:
            # Restore window before dragging
            self._toggle_maximize()
        
        # Get the root window
        root = self.winfo_toplevel()
        x = root.winfo_x() + event.x - self._drag_start_x
        y = root.winfo_y() + event.y - self._drag_start_y
        root.geometry(f"+{x}+{y}")
    
    def _on_double_click(self, event):
        """Toggle maximize on double click"""
        self._toggle_maximize()
    
    def _minimize_window(self):
        """Minimize the window"""
        root = self.winfo_toplevel()
        root.iconify()
    
    def _toggle_maximize(self):
        """Toggle window maximize state"""
        root = self.winfo_toplevel()
        
        if self._is_maximized:
            # Restore to normal
            if self._normal_geometry:
                root.geometry(self._normal_geometry)
            self._is_maximized = False
            self.max_btn.configure(text="□")
        else:
            # Save current geometry and maximize
            self._normal_geometry = root.geometry()
            
            # Get screen dimensions
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            
            # Set to full screen (accounting for taskbar)
            root.geometry(f"{screen_width}x{screen_height-40}+0+0")
            self._is_maximized = True
            self.max_btn.configure(text="❐")
    
    def _close_window(self):
        """Close the window"""
        root = self.winfo_toplevel()
        root.quit()
        root.destroy()
    
    def set_gpu_status(self, status: str, is_available: bool = True):
        """Update GPU status display"""
        color = RedTheme.SUCCESS if is_available else RedTheme.TEXT_MUTED
        self.gpu_status.configure(text=f"  |  {status}", text_color=color)
