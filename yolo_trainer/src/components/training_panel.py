"""
Training Panel - Main training interface with all controls and progress display
"""

import customtkinter as ctk
from tkinter import filedialog
from pathlib import Path
from typing import Optional, Dict, Any
from ..themes.red_theme import RedTheme
from ..core.trainer import YOLOTrainer
from ..core.gpu_utils import GPUUtils


class TrainingPanel(ctk.CTkFrame):
    """Main training panel with all controls"""
    
    def __init__(self, parent, on_gpu_status: callable = None):
        super().__init__(parent, fg_color=RedTheme.BG_PRIMARY, corner_radius=0)
        
        self.on_gpu_status = on_gpu_status
        self.trainer = YOLOTrainer()
        self.dataset_path: Optional[str] = None
        
        # Set up trainer callbacks
        self.trainer.on_progress = self._on_training_progress
        self.trainer.on_log = self._on_training_log
        self.trainer.on_complete = self._on_training_complete
        
        self._create_widgets()
        self._update_gpu_status()
    
    def _create_widgets(self):
        """Create all panel widgets"""
        # Main scrollable container
        self.main_container = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=RedTheme.SCROLLBAR_THUMB,
            scrollbar_button_hover_color=RedTheme.SCROLLBAR_THUMB_HOVER
        )
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # === DATASET SECTION ===
        self._create_section_header("📁 Dataset")
        self._create_dataset_section()
        
        # === MODEL CONFIGURATION ===
        self._create_section_header("⚙️ Model Configuration")
        self._create_model_section()
        
        # === TRAINING PARAMETERS ===
        self._create_section_header("📊 Training Parameters")
        self._create_parameters_section()
        
        # === GPU STATUS ===
        self._create_gpu_status_section()
        
        # === PROGRESS SECTION ===
        self._create_section_header("📈 Training Progress")
        self._create_progress_section()
        
        # === CONTROL BUTTONS ===
        self._create_control_buttons()
    
    def _create_section_header(self, text: str):
        """Create a section header"""
        header = ctk.CTkLabel(
            self.main_container,
            text=text,
            font=(RedTheme.FONT_FAMILY, RedTheme.FONT_SIZE_LG, "bold"),
            text_color=RedTheme.TEXT_PRIMARY,
            anchor="w"
        )
        header.pack(fill="x", pady=(20, 10))
    
    def _create_dataset_section(self):
        """Create dataset selection section"""
        frame = ctk.CTkFrame(self.main_container, fg_color=RedTheme.BG_SURFACE, corner_radius=RedTheme.RADIUS_LG)
        frame.pack(fill="x", pady=(0, 10))
        
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="x", padx=15, pady=15)
        
        # Path display
        path_frame = ctk.CTkFrame(inner, fg_color="transparent")
        path_frame.pack(fill="x")
        
        self.path_entry = ctk.CTkEntry(
            path_frame,
            placeholder_text="Select Roboflow dataset folder...",
            font=(RedTheme.FONT_FAMILY, RedTheme.FONT_SIZE_MD),
            fg_color=RedTheme.INPUT_BG,
            border_color=RedTheme.INPUT_BORDER,
            text_color=RedTheme.INPUT_TEXT,
            placeholder_text_color=RedTheme.INPUT_PLACEHOLDER,
            height=40,
            corner_radius=RedTheme.RADIUS_MD
        )
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        browse_btn = ctk.CTkButton(
            path_frame,
            text="Browse...",
            font=(RedTheme.FONT_FAMILY, RedTheme.FONT_SIZE_MD),
            fg_color=RedTheme.BTN_SECONDARY_BG,
            hover_color=RedTheme.BTN_SECONDARY_HOVER,
            text_color=RedTheme.BTN_SECONDARY_TEXT,
            height=40,
            width=100,
            corner_radius=RedTheme.RADIUS_MD,
            command=self._browse_dataset
        )
        browse_btn.pack(side="right")
        
        # Validation status
        self.dataset_status = ctk.CTkLabel(
            inner,
            text="",
            font=(RedTheme.FONT_FAMILY, RedTheme.FONT_SIZE_SM),
            text_color=RedTheme.TEXT_MUTED,
            anchor="w"
        )
        self.dataset_status.pack(fill="x", pady=(8, 0))
    
    def _create_model_section(self):
        """Create model configuration section"""
        frame = ctk.CTkFrame(self.main_container, fg_color=RedTheme.BG_SURFACE, corner_radius=RedTheme.RADIUS_LG)
        frame.pack(fill="x", pady=(0, 10))
        
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="x", padx=15, pady=15)
        
        # Two columns
        cols = ctk.CTkFrame(inner, fg_color="transparent")
        cols.pack(fill="x")
        
        # Left column - Model type
        left = ctk.CTkFrame(cols, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        ctk.CTkLabel(
            left,
            text="Model Type",
            font=(RedTheme.FONT_FAMILY, RedTheme.FONT_SIZE_SM),
            text_color=RedTheme.TEXT_SECONDARY,
            anchor="w"
        ).pack(fill="x")
        
        # Models ordered by speed (fastest first)
        self.model_var = ctk.StringVar(value="yolov5n")
        self.model_dropdown = ctk.CTkOptionMenu(
            left,
            values=[
                "yolov5n",   # Fastest - ~200 FPS
                "yolov5s",   # Fast - ~100 FPS
                "yolov8n",   # Fast - ~150 FPS
                "yolov8s",   # Medium - ~80 FPS
                "yolov5m",   # Medium
                "yolov8m",   # Slower
                "yolov5l",   # Slow
                "yolov8l",   # Slow
                "yolov5x",   # Slowest
                "yolov8x"    # Slowest
            ],
            variable=self.model_var,
            font=(RedTheme.FONT_FAMILY, RedTheme.FONT_SIZE_MD),
            fg_color=RedTheme.INPUT_BG,
            button_color=RedTheme.PRIMARY,
            button_hover_color=RedTheme.PRIMARY_HOVER,
            dropdown_fg_color=RedTheme.BG_SURFACE,
            dropdown_hover_color=RedTheme.BG_ELEVATED,
            text_color=RedTheme.TEXT_PRIMARY,
            height=40,
            corner_radius=RedTheme.RADIUS_MD,
            command=self._on_model_changed
        )
        self.model_dropdown.pack(fill="x", pady=(5, 0))
        
        # Speed indicator label
        self.speed_label = ctk.CTkLabel(
            left,
            text="⚡ Fastest (~200 FPS) - Best for aimbot",
            font=(RedTheme.FONT_FAMILY, RedTheme.FONT_SIZE_SM),
            text_color=RedTheme.SUCCESS,
            anchor="w"
        )
        self.speed_label.pack(fill="x", pady=(5, 0))
        
        # Right column - Output name
        right = ctk.CTkFrame(cols, fg_color="transparent")
        right.pack(side="right", fill="x", expand=True, padx=(10, 0))
        
        ctk.CTkLabel(
            right,
            text="Output Model Name",
            font=(RedTheme.FONT_FAMILY, RedTheme.FONT_SIZE_SM),
            text_color=RedTheme.TEXT_SECONDARY,
            anchor="w"
        ).pack(fill="x")
        
        self.output_name_entry = ctk.CTkEntry(
            right,
            placeholder_text="my_custom_model",
            font=(RedTheme.FONT_FAMILY, RedTheme.FONT_SIZE_MD),
            fg_color=RedTheme.INPUT_BG,
            border_color=RedTheme.INPUT_BORDER,
            text_color=RedTheme.INPUT_TEXT,
            placeholder_text_color=RedTheme.INPUT_PLACEHOLDER,
            height=40,
            corner_radius=RedTheme.RADIUS_MD
        )
        self.output_name_entry.pack(fill="x", pady=(5, 0))
        self.output_name_entry.insert(0, "custom_model")
    
    def _create_parameters_section(self):
        """Create training parameters section"""
        frame = ctk.CTkFrame(self.main_container, fg_color=RedTheme.BG_SURFACE, corner_radius=RedTheme.RADIUS_LG)
        frame.pack(fill="x", pady=(0, 10))
        
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="x", padx=15, pady=15)
        
        # Three columns
        cols = ctk.CTkFrame(inner, fg_color="transparent")
        cols.pack(fill="x")
        
        # Epochs
        col1 = ctk.CTkFrame(cols, fg_color="transparent")
        col1.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        ctk.CTkLabel(
            col1,
            text="Epochs",
            font=(RedTheme.FONT_FAMILY, RedTheme.FONT_SIZE_SM),
            text_color=RedTheme.TEXT_SECONDARY,
            anchor="w"
        ).pack(fill="x")
        
        self.epochs_entry = ctk.CTkEntry(
            col1,
            font=(RedTheme.FONT_FAMILY, RedTheme.FONT_SIZE_MD),
            fg_color=RedTheme.INPUT_BG,
            border_color=RedTheme.INPUT_BORDER,
            text_color=RedTheme.INPUT_TEXT,
            height=40,
            corner_radius=RedTheme.RADIUS_MD
        )
        self.epochs_entry.pack(fill="x", pady=(5, 0))
        self.epochs_entry.insert(0, "100")
        
        # Batch Size
        col2 = ctk.CTkFrame(cols, fg_color="transparent")
        col2.pack(side="left", fill="x", expand=True, padx=10)
        
        ctk.CTkLabel(
            col2,
            text="Batch Size",
            font=(RedTheme.FONT_FAMILY, RedTheme.FONT_SIZE_SM),
            text_color=RedTheme.TEXT_SECONDARY,
            anchor="w"
        ).pack(fill="x")
        
        self.batch_entry = ctk.CTkEntry(
            col2,
            font=(RedTheme.FONT_FAMILY, RedTheme.FONT_SIZE_MD),
            fg_color=RedTheme.INPUT_BG,
            border_color=RedTheme.INPUT_BORDER,
            text_color=RedTheme.INPUT_TEXT,
            height=40,
            corner_radius=RedTheme.RADIUS_MD
        )
        self.batch_entry.pack(fill="x", pady=(5, 0))
        self.batch_entry.insert(0, "8")  # Default 8 for 6GB GPUs
        
        # Resume Training Checkbox
        self.resume_var = ctk.BooleanVar(value=False)
        self.resume_chk = ctk.CTkCheckBox(
            inner,
            text="Resume Training (from last checkpoint)",
            variable=self.resume_var,
            font=(RedTheme.FONT_FAMILY, RedTheme.FONT_SIZE_SM),
            text_color=RedTheme.TEXT_SECONDARY,
            fg_color=RedTheme.PRIMARY,
            hover_color=RedTheme.PRIMARY_HOVER,
            corner_radius=RedTheme.RADIUS_SM
        )
        self.resume_chk.pack(fill="x", pady=(10, 0), padx=5)
        
        # Sleep Mode Checkbox - Shutdown PC when training completes
        self.sleep_var = ctk.BooleanVar(value=False)
        self.sleep_chk = ctk.CTkCheckBox(
            inner,
            text="💤 Sleep Mode (shutdown PC when done)",
            variable=self.sleep_var,
            font=(RedTheme.FONT_FAMILY, RedTheme.FONT_SIZE_SM),
            text_color=RedTheme.TEXT_SECONDARY,
            fg_color=RedTheme.PRIMARY,
            hover_color=RedTheme.PRIMARY_HOVER,
            corner_radius=RedTheme.RADIUS_SM
        )
        self.sleep_chk.pack(fill="x", pady=(5, 0), padx=5)

        # Image Size
        col3 = ctk.CTkFrame(cols, fg_color="transparent")
        col3.pack(side="left", fill="x", expand=True, padx=(10, 0))
        
        ctk.CTkLabel(
            col3,

            text="Image Size",
            font=(RedTheme.FONT_FAMILY, RedTheme.FONT_SIZE_SM),
            text_color=RedTheme.TEXT_SECONDARY,
            anchor="w"
        ).pack(fill="x")
        
        self.imgsize_entry = ctk.CTkEntry(
            col3,
            font=(RedTheme.FONT_FAMILY, RedTheme.FONT_SIZE_MD),
            fg_color=RedTheme.INPUT_BG,
            border_color=RedTheme.INPUT_BORDER,
            text_color=RedTheme.INPUT_TEXT,
            height=40,
            corner_radius=RedTheme.RADIUS_MD
        )
        self.imgsize_entry.pack(fill="x", pady=(5, 0))
        self.imgsize_entry.insert(0, "640")
    
    def _create_gpu_status_section(self):
        """Create GPU status display"""
        frame = ctk.CTkFrame(self.main_container, fg_color=RedTheme.BG_SURFACE, corner_radius=RedTheme.RADIUS_LG)
        frame.pack(fill="x", pady=(10, 10))
        
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="x", padx=15, pady=12)
        
        # GPU icon and status
        self.gpu_label = ctk.CTkLabel(
            inner,
            text="🖥️ Checking GPU...",
            font=(RedTheme.FONT_FAMILY, RedTheme.FONT_SIZE_MD),
            text_color=RedTheme.TEXT_SECONDARY,
            anchor="w"
        )
        self.gpu_label.pack(fill="x")
    
    def _create_progress_section(self):
        """Create training progress display"""
        frame = ctk.CTkFrame(self.main_container, fg_color=RedTheme.BG_SURFACE, corner_radius=RedTheme.RADIUS_LG)
        frame.pack(fill="x", pady=(0, 10))
        
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="x", padx=15, pady=15)
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            inner,
            height=20,
            corner_radius=RedTheme.RADIUS_MD,
            fg_color=RedTheme.PROGRESS_BG,
            progress_color=RedTheme.PROGRESS_FILL
        )
        self.progress_bar.pack(fill="x", pady=(0, 10))
        self.progress_bar.set(0)
        
        # Progress label
        self.progress_label = ctk.CTkLabel(
            inner,
            text="Ready to train",
            font=(RedTheme.FONT_FAMILY, RedTheme.FONT_SIZE_MD),
            text_color=RedTheme.TEXT_SECONDARY,
            anchor="w"
        )
        self.progress_label.pack(fill="x", pady=(0, 10))
        
        # Metrics display
        metrics_frame = ctk.CTkFrame(inner, fg_color="transparent")
        metrics_frame.pack(fill="x", pady=(0, 10))
        
        self.epoch_label = ctk.CTkLabel(
            metrics_frame,
            text="Epoch: --/--",
            font=(RedTheme.FONT_FAMILY, RedTheme.FONT_SIZE_SM),
            text_color=RedTheme.TEXT_MUTED
        )
        self.epoch_label.pack(side="left", padx=(0, 20))
        
        self.loss_label = ctk.CTkLabel(
            metrics_frame,
            text="Loss: --",
            font=(RedTheme.FONT_FAMILY, RedTheme.FONT_SIZE_SM),
            text_color=RedTheme.TEXT_MUTED
        )
        self.loss_label.pack(side="left", padx=(0, 20))
        
        self.map_label = ctk.CTkLabel(
            metrics_frame,
            text="mAP50: --",
            font=(RedTheme.FONT_FAMILY, RedTheme.FONT_SIZE_SM),
            text_color=RedTheme.TEXT_MUTED
        )
        self.map_label.pack(side="left")
        
        # Log display
        self.log_textbox = ctk.CTkTextbox(
            inner,
            height=150,
            font=(RedTheme.FONT_FAMILY, RedTheme.FONT_SIZE_SM),
            fg_color=RedTheme.BG_DARK,
            text_color=RedTheme.TEXT_SECONDARY,
            corner_radius=RedTheme.RADIUS_MD,
            scrollbar_button_color=RedTheme.SCROLLBAR_THUMB,
            scrollbar_button_hover_color=RedTheme.SCROLLBAR_THUMB_HOVER
        )
        self.log_textbox.pack(fill="x")
        self.log_textbox.configure(state="disabled")
    
    def _create_control_buttons(self):
        """Create start/stop training buttons"""
        frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        frame.pack(fill="x", pady=20)
        
        # Center the buttons
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(anchor="center")
        
        # Start button
        self.start_btn = ctk.CTkButton(
            btn_frame,
            text="🚀 START TRAINING",
            font=(RedTheme.FONT_FAMILY, RedTheme.FONT_SIZE_LG, "bold"),
            fg_color=RedTheme.BTN_PRIMARY_BG,
            hover_color=RedTheme.BTN_PRIMARY_HOVER,
            text_color=RedTheme.BTN_PRIMARY_TEXT,
            height=50,
            width=200,
            corner_radius=RedTheme.RADIUS_LG,
            command=self._start_training
        )
        self.start_btn.pack(side="left", padx=(0, 15))
        
        # Stop button
        self.stop_btn = ctk.CTkButton(
            btn_frame,
            text="⏹ STOP",
            font=(RedTheme.FONT_FAMILY, RedTheme.FONT_SIZE_LG, "bold"),
            fg_color=RedTheme.BTN_DANGER_BG,
            hover_color=RedTheme.BTN_DANGER_HOVER,
            text_color=RedTheme.BTN_DANGER_TEXT,
            height=50,
            width=120,
            corner_radius=RedTheme.RADIUS_LG,
            command=self._stop_training,
            state="disabled"
        )
        self.stop_btn.pack(side="left")
    
    def _on_model_changed(self, model_name: str):
        """Update speed indicator when model is changed"""
        speed_info = {
            "yolov5n": ("⚡ Fastest (~200 FPS) - Best for aimbot", RedTheme.SUCCESS),
            "yolov5s": ("⚡ Fast (~100 FPS) - Good balance", RedTheme.SUCCESS),
            "yolov8n": ("⚡ Fast (~150 FPS) - Good for aimbot", RedTheme.SUCCESS),
            "yolov8s": ("🔶 Medium (~80 FPS)", RedTheme.WARNING),
            "yolov5m": ("🔶 Medium (~60 FPS)", RedTheme.WARNING),
            "yolov8m": ("🔶 Medium-Slow (~50 FPS)", RedTheme.WARNING),
            "yolov5l": ("🐢 Slow (~30 FPS)", RedTheme.TEXT_MUTED),
            "yolov8l": ("🐢 Slow (~25 FPS)", RedTheme.TEXT_MUTED),
            "yolov5x": ("🐢 Slowest (~15 FPS) - High accuracy", RedTheme.TEXT_MUTED),
            "yolov8x": ("🐢 Slowest (~12 FPS) - High accuracy", RedTheme.TEXT_MUTED),
        }
        
        text, color = speed_info.get(model_name, ("", RedTheme.TEXT_MUTED))
        self.speed_label.configure(text=text, text_color=color)
    
    def _browse_dataset(self):
        """Open folder browser for dataset selection"""
        folder = filedialog.askdirectory(
            title="Select Roboflow Dataset Folder"
        )
        
        if folder:
            self.dataset_path = folder
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, folder)
            
            # Validate dataset
            is_valid, message = self.trainer.validate_dataset(folder)
            
            if is_valid:
                self.dataset_status.configure(
                    text=f"✓ Valid dataset found: {Path(message).name}",
                    text_color=RedTheme.SUCCESS
                )
            else:
                self.dataset_status.configure(
                    text=f"✗ {message}",
                    text_color=RedTheme.ERROR
                )
    
    def _update_gpu_status(self):
        """Update GPU status display"""
        is_available, gpu_name, cuda_version = GPUUtils.get_gpu_info()
        
        if is_available:
            total_mem, free_mem = GPUUtils.get_gpu_memory()
            status = f"🖥️ GPU: {gpu_name} (CUDA {cuda_version}) - {free_mem:.1f}GB free"
            self.gpu_label.configure(text=status, text_color=RedTheme.SUCCESS)
            
            if self.on_gpu_status:
                self.on_gpu_status(f"{gpu_name} (CUDA {cuda_version})", True)
        else:
            status = "🖥️ No GPU detected - Training will use CPU (slower)"
            self.gpu_label.configure(text=status, text_color=RedTheme.WARNING)
            
            if self.on_gpu_status:
                self.on_gpu_status("CPU Mode", False)
    
    def _log(self, message: str):
        """Add message to log display"""
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"{message}\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")
    
    def _start_training(self):
        """Start the training process"""
        # Get parameters
        dataset_path = self.path_entry.get()
        if not dataset_path:
            self._log("[ERROR] Please select a dataset folder")
            return
        
        model_type = self.model_var.get()
        output_name = self.output_name_entry.get() or "custom_model"
        
        try:
            epochs = int(self.epochs_entry.get())
            batch_size = int(self.batch_entry.get())
            img_size = int(self.imgsize_entry.get())
        except ValueError:
            self._log("[ERROR] Invalid parameter values")
            return
        
        # Update UI
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.progress_label.configure(text="Initializing training...")
        
        # Clear log
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")
        
        # Start training
        output_dir = str(Path(dataset_path).parent / "trained_models")
        
        # Get resume state
        resume_training = self.resume_var.get()
        
        # Build options dictionary
        options = {
            'dataset_path': dataset_path,
            'model_type': model_type,
            'output_name': output_name,
            'epochs': epochs,
            'batch_size': batch_size,
            'img_size': img_size,
            'output_dir': output_dir,
            'resume': resume_training
        }
        
        self.trainer.train_with_options(options)
    
    def _stop_training(self):
        """Stop the training process"""
        self.trainer.stop_training()
        self.stop_btn.configure(state="disabled")
    
    def _on_training_progress(self, metrics: Dict[str, Any]):
        """Handle training progress update"""
        epoch = metrics.get('epoch', 0)
        total = metrics.get('total_epochs', 1)
        box_loss = metrics.get('box_loss', 0)
        map50 = metrics.get('mAP50', 0)
        
        # Update progress bar
        progress = epoch / total
        self.progress_bar.set(progress)
        
        # Update labels
        self.progress_label.configure(text=f"Training... {int(progress * 100)}%")
        self.epoch_label.configure(text=f"Epoch: {epoch}/{total}")
        self.loss_label.configure(text=f"Loss: {box_loss:.4f}")
        self.map_label.configure(text=f"mAP50: {map50:.3f}" if map50 > 0 else "mAP50: --")
    
    def _on_training_log(self, message: str):
        """Handle log message from trainer"""
        # Use after() to update UI from training thread
        self.after(0, lambda: self._log(message))
    
    def _on_training_complete(self, success: bool, message: str):
        """Handle training completion"""
        def _update_ui():
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            
            if success:
                self.progress_bar.set(1)
                self.progress_label.configure(text="Training Complete! ✓")
                self._log(f"[SUCCESS] Model saved to: {message}")
                
                # Check if Sleep Mode is enabled
                if self.sleep_var.get():
                    self._log("[INFO] Sleep Mode enabled - Shutting down PC in 60 seconds...")
                    self._log("[INFO] Close the app to cancel shutdown")
                    self._shutdown_pc()
            else:
                self.progress_label.configure(text="Training Failed")
        
        self.after(0, _update_ui)
    
    def _shutdown_pc(self):
        """Shutdown the PC after training completes"""
        import subprocess
        import sys
        
        if sys.platform == "win32":
            # Windows: shutdown in 60 seconds (gives time to cancel if needed)
            subprocess.run(["shutdown", "/s", "/t", "60", "/c", "YOLO Training Complete - Shutting down..."], shell=True)
        else:
            # Linux/Mac
            subprocess.run(["shutdown", "-h", "+1"], shell=True)
