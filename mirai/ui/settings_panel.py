"""
Settings Panel for MirAi
Configuration UI with all aimbot settings.
"""

import customtkinter as ctk
from tkinter import filedialog
from typing import Callable, Optional, List
import os


class SettingsPanel(ctk.CTkFrame):
    """Settings panel with tabbed interface."""
    
    COLORS = {
        'bg': '#1a1a1a',
        'bg_secondary': '#252525',
        'accent': '#ff3333',
        'accent_hover': '#ff5555',
        'accent_dark': '#cc0000',
        'text': '#ffffff',
        'text_dim': '#888888',
        'border': '#333333',
        'input_bg': '#2a2a2a',
    }
    
    def __init__(
        self,
        parent,
        on_setting_changed: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(parent, fg_color=self.COLORS['bg'], **kwargs)
        
        self.on_setting_changed = on_setting_changed
        
        # Variables
        self.model_path_var = ctk.StringVar(value="")
        self.fov_var = ctk.IntVar(value=150)
        self.confidence_var = ctk.DoubleVar(value=0.5)
        self.smoothness_var = ctk.DoubleVar(value=0.5)
        self.speed_var = ctk.DoubleVar(value=1.0)
        self.head_offset_var = ctk.DoubleVar(value=0.2)
        self.target_fps_var = ctk.IntVar(value=60)
        self.show_overlay_var = ctk.BooleanVar(value=True)
        self.show_fov_var = ctk.BooleanVar(value=True)
        
        # Triggerbot vars
        self.trigger_enabled_var = ctk.BooleanVar(value=False)
        self.trigger_mode_var = ctk.StringVar(value="hold")
        self.trigger_delay_var = ctk.DoubleVar(value=0.1)
        self.trigger_interval_var = ctk.DoubleVar(value=0.1)
        
        self.available_classes: List[str] = []
        self.selected_classes: List[int] = []
        self.class_checkboxes = []
        
        self._create_widgets()
        
    def _create_widgets(self):
        # Create TabView
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=self.COLORS['bg_secondary'],
            segmented_button_fg_color=self.COLORS['bg'],
            segmented_button_selected_color=self.COLORS['accent'],
            segmented_button_selected_hover_color=self.COLORS['accent_hover'],
            text_color=self.COLORS['text']
        )
        self.tabview.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.tabview.add("General")
        self.tabview.add("Triggerbot")
        self.tabview.add("Visuals")
        
        self._setup_general_tab()
        self._setup_triggerbot_tab()
        self._setup_visuals_tab()
        
    def _setup_general_tab(self):
        tab = self.tabview.tab("General")
        
        # Scrollable frame for content inside tab
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        
        # Model Section
        self._create_section_header(scroll, "📁 Model")
        self._create_model_section(scroll)
        
        # Aim Settings
        self._create_section_header(scroll, "🎯 Aim Settings")
        self._create_slider_row(scroll, "FOV Radius", self.fov_var, 10, 500, "px", self._on_fov_changed)
        self._create_slider_row(scroll, "Smoothness", self.smoothness_var, 0.1, 1.0, "", self._on_smoothness_changed, 0.05)
        self._create_slider_row(scroll, "Aim Speed", self.speed_var, 0.1, 5.0, "x", self._on_speed_changed, 0.1)
        self._create_slider_row(scroll, "Head Offset", self.head_offset_var, 0.0, 1.0, "", self._on_head_offset_changed, 0.05)
        
        # Detection
        self._create_section_header(scroll, "🔍 Detection")
        self._create_slider_row(scroll, "Confidence", self.confidence_var, 0.1, 1.0, "", self._on_confidence_changed, 0.05)
        self._create_slider_row(scroll, "Target FPS", self.target_fps_var, 1, 240, "fps", self._on_target_fps_changed)
        
        # Classes
        self._create_section_header(scroll, "🏷️ Target Classes")
        self.classes_frame = ctk.CTkFrame(scroll, fg_color=self.COLORS['bg'], corner_radius=8)
        self.classes_frame.pack(fill="x", padx=10, pady=(0, 15))
        self.no_classes_label = ctk.CTkLabel(self.classes_frame, text="Load model first", text_color=self.COLORS['text_dim'])
        self.no_classes_label.pack(pady=20)

    def _setup_triggerbot_tab(self):
        tab = self.tabview.tab("Triggerbot")
        
        # Enable Switch
        switch_row = ctk.CTkFrame(tab, fg_color="transparent")
        switch_row.pack(fill="x", padx=15, pady=15)
        ctk.CTkLabel(switch_row, text="Enable Triggerbot", text_color=self.COLORS['text']).pack(side="left")
        ctk.CTkSwitch(
            switch_row, text="", variable=self.trigger_enabled_var,
            progress_color=self.COLORS['accent'], command=self._on_trigger_changed
        ).pack(side="right")
        
        # Mode
        mode_row = ctk.CTkFrame(tab, fg_color="transparent")
        mode_row.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(mode_row, text="Mode", text_color=self.COLORS['text']).pack(side="left")
        ctk.CTkOptionMenu(
            mode_row, variable=self.trigger_mode_var,
            values=["hold", "rapid", "single"],
            fg_color=self.COLORS['accent'], button_color=self.COLORS['accent_dark'],
            command=self._on_trigger_changed
        ).pack(side="right")
        
        # Delay & Interval
        self._create_slider_row(tab, "Shot Delay", self.trigger_delay_var, 0.0, 1.0, "s", self._on_trigger_changed, 0.05)
        self._create_slider_row(tab, "Rapid Interval", self.trigger_interval_var, 0.01, 1.0, "s", self._on_trigger_changed, 0.01)
        
        ctk.CTkLabel(tab, text="Triggerbot fires when center of screen\nis inside the target box.", 
                     text_color=self.COLORS['text_dim'], font=("Segoe UI", 11)).pack(pady=20)

    def _setup_visuals_tab(self):
        tab = self.tabview.tab("Visuals")
        
        # Performance info
        fps_frame = ctk.CTkFrame(tab, fg_color="transparent")
        fps_frame.pack(fill="x", padx=15, pady=15)
        ctk.CTkLabel(fps_frame, text="Current FPS:", text_color=self.COLORS['text_dim']).pack(side="left")
        self.current_fps_label = ctk.CTkLabel(fps_frame, text="--", font=("Segoe UI", 11, "bold"), text_color=self.COLORS['accent'])
        self.current_fps_label.pack(side="left", padx=5)
        
        # Toggles
        self._create_switch_row(tab, "Show Overlay", self.show_overlay_var, self._on_overlay_toggled)
        self._create_switch_row(tab, "Show FOV Circle", self.show_fov_var, self._on_fov_toggled)

    def _create_section_header(self, parent, title):
        ctk.CTkLabel(parent, text=title, font=("Segoe UI", 14, "bold"), text_color=self.COLORS['accent'], anchor="w").pack(fill="x", padx=10, pady=(15, 5))

    def _create_model_section(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=self.COLORS['input_bg'], corner_radius=8)
        frame.pack(fill="x", padx=10, pady=5)
        
        path_frame = ctk.CTkFrame(frame, fg_color="transparent")
        path_frame.pack(fill="x", padx=10, pady=10)
        self.model_entry = ctk.CTkEntry(path_frame, textvariable=self.model_path_var, placeholder_text="Select py model...", height=32)
        self.model_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(path_frame, text="Browse", width=60, height=32, command=self._browse_model, fg_color=self.COLORS['accent']).pack(side="right")
        
        ctk.CTkButton(frame, text="Load Model", height=32, fg_color="transparent", border_width=1, border_color=self.COLORS['accent'], text_color=self.COLORS['accent'], command=self._load_model).pack(fill="x", padx=10, pady=(0, 10))
        self.model_status = ctk.CTkLabel(frame, text="No model loaded", font=("Segoe UI", 10), text_color=self.COLORS['text_dim'])
        self.model_status.pack(pady=(0, 10))

    def _create_switch_row(self, parent, text, var, cmd):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(row, text=text, text_color=self.COLORS['text']).pack(side="left")
        ctk.CTkSwitch(row, text="", variable=var, command=cmd, progress_color=self.COLORS['accent']).pack(side="right")

    def _on_trigger_changed(self, *args):
        if self.on_setting_changed:
            self.on_setting_changed("triggerbot_enabled", self.trigger_enabled_var.get())
            self.on_setting_changed("triggerbot_mode", self.trigger_mode_var.get())
            self.on_setting_changed("triggerbot_delay", self.trigger_delay_var.get())
            self.on_setting_changed("triggerbot_interval", self.trigger_interval_var.get())

    # Keep existing helper methods, load_settings, etc.
    
    def _create_slider_row(
        self,
        parent,
        label: str,
        variable,
        min_val: float,
        max_val: float,
        suffix: str,
        command: Callable,
        resolution: float = 1
    ) -> None:
        """Create a labeled slider row."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=15, pady=(15, 5))
        
        # Label
        ctk.CTkLabel(
            row,
            text=label,
            font=("Segoe UI", 11),
            text_color=self.COLORS['text']
        ).pack(side="left")
        
        # Value display
        value_label = ctk.CTkLabel(
            row,
            text=f"{variable.get():.2f}{suffix}" if isinstance(variable.get(), float) else f"{variable.get()}{suffix}",
            font=("Segoe UI", 11, "bold"),
            text_color=self.COLORS['accent'],
            width=60
        )
        value_label.pack(side="right")
        
        # Slider
        slider_row = ctk.CTkFrame(parent, fg_color="transparent")
        slider_row.pack(fill="x", padx=15, pady=(0, 5))
        
        def on_slider_change(value):
            if resolution >= 1:
                value = int(value)
                variable.set(value)
                value_label.configure(text=f"{value}{suffix}")
            else:
                value = round(value, 2)
                variable.set(value)
                value_label.configure(text=f"{value:.2f}{suffix}")
            command()
        
        slider = ctk.CTkSlider(
            slider_row,
            from_=min_val,
            to=max_val,
            variable=variable,
            progress_color=self.COLORS['accent'],
            button_color=self.COLORS['text'],
            button_hover_color=self.COLORS['accent_hover'],
            command=on_slider_change
        )
        slider.pack(fill="x")
    
    def _browse_model(self) -> None:
        """Open file dialog to browse for model."""
        filepath = filedialog.askopenfilename(
            title="Select YOLO Model",
            filetypes=[("PyTorch Model", "*.pt"), ("All Files", "*.*")]
        )
        if filepath:
            self.model_path_var.set(filepath)
    
    def _load_model(self) -> None:
        """Trigger model loading."""
        if self.on_setting_changed:
            self.on_setting_changed("load_model", self.model_path_var.get())
    
    def set_model_status(self, status: str, success: bool = True) -> None:
        """Update model status display."""
        self.model_status.configure(
            text=status,
            text_color=self.COLORS['accent'] if success else "#ff6666"
        )
    
    def set_classes(self, classes: List[str]) -> None:
        """Update available classes list."""
        self.available_classes = classes
        
        # Clear existing checkboxes
        for cb in self.class_checkboxes:
            cb.destroy()
        self.class_checkboxes = []
        
        if self.no_classes_label:
            self.no_classes_label.destroy()
            self.no_classes_label = None
        
        if not classes:
            self.no_classes_label = ctk.CTkLabel(
                self.classes_frame,
                text="No classes available",
                font=("Segoe UI", 11),
                text_color=self.COLORS['text_dim']
            )
            self.no_classes_label.pack(pady=20)
            return
        
        # Create checkboxes for each class
        for i, cls_name in enumerate(classes):
            var = ctk.BooleanVar(value=True)
            
            cb = ctk.CTkCheckBox(
                self.classes_frame,
                text=f"{i}: {cls_name}",
                variable=var,
                onvalue=True,
                offvalue=False,
                fg_color=self.COLORS['accent'],
                hover_color=self.COLORS['accent_hover'],
                text_color=self.COLORS['text'],
                command=lambda idx=i, v=var: self._on_class_toggled(idx, v.get())
            )
            cb.pack(anchor="w", padx=15, pady=5)
            self.class_checkboxes.append(cb)
    
    def _on_class_toggled(self, class_idx: int, enabled: bool) -> None:
        """Handle class checkbox toggle."""
        if enabled and class_idx not in self.selected_classes:
            self.selected_classes.append(class_idx)
        elif not enabled and class_idx in self.selected_classes:
            self.selected_classes.remove(class_idx)
        
        if self.on_setting_changed:
            self.on_setting_changed("target_classes", self.selected_classes.copy())
    
    def _on_fov_changed(self) -> None:
        if self.on_setting_changed:
            self.on_setting_changed("fov_radius", self.fov_var.get())
    
    def _on_confidence_changed(self) -> None:
        if self.on_setting_changed:
            self.on_setting_changed("confidence_threshold", self.confidence_var.get())
    
    def _on_smoothness_changed(self) -> None:
        if self.on_setting_changed:
            self.on_setting_changed("aim_smoothness", self.smoothness_var.get())
    
    def _on_speed_changed(self) -> None:
        if self.on_setting_changed:
            self.on_setting_changed("aim_speed", self.speed_var.get())
    
    def _on_head_offset_changed(self) -> None:
        if self.on_setting_changed:
            self.on_setting_changed("head_offset", self.head_offset_var.get())
    
    def _on_target_fps_changed(self) -> None:
        if self.on_setting_changed:
            self.on_setting_changed("target_fps", self.target_fps_var.get())
    
    def _on_overlay_toggled(self) -> None:
        if self.on_setting_changed:
            self.on_setting_changed("show_overlay", self.show_overlay_var.get())
    
    def _on_fov_toggled(self) -> None:
        if self.on_setting_changed:
            self.on_setting_changed("show_fov_circle", self.show_fov_var.get())
    
    def update_fps(self, fps: float) -> None:
        """Update current FPS display."""
        self.current_fps_label.configure(text=f"{fps:.1f}")
    
    def load_settings(self, config: dict) -> None:
        """Load settings from config dict."""
        self.model_path_var.set(config.get("model_path", ""))
        self.fov_var.set(config.get("fov_radius", 150))
        self.confidence_var.set(config.get("confidence_threshold", 0.5))
        self.smoothness_var.set(config.get("aim_smoothness", 0.5))
        self.speed_var.set(config.get("aim_speed", 1.0))
        self.head_offset_var.set(config.get("head_offset", 0.2))
        self.target_fps_var.set(config.get("target_fps", 60))
        self.show_overlay_var.set(config.get("show_overlay", True))
        self.show_fov_var.set(config.get("show_fov_circle", True))
        self.trigger_enabled_var.set(config.get("triggerbot_enabled", False))
        self.trigger_mode_var.set(config.get("triggerbot_mode", "hold"))
        self.trigger_delay_var.set(config.get("triggerbot_delay", 0.1))
        self.trigger_interval_var.set(config.get("triggerbot_interval", 0.1))
