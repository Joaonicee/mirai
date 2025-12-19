"""
YOLO Model Loader for MirAi
Handles loading and validating YOLO models.
"""

import os
from typing import Optional, List, Tuple
from pathlib import Path


class ModelLoader:
    """Loads and manages YOLO models."""
    
    def __init__(self):
        self.model = None
        self.model_path: Optional[str] = None
        self.classes: List[str] = []
        self.device: str = 'cuda'  # Will fallback to CPU if needed
        
    def load_model(self, model_path: str) -> Tuple[bool, str]:
        """
        Load a YOLO model from the given path.
        
        Args:
            model_path: Path to the .pt model file
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if not os.path.exists(model_path):
                return False, f"Model file not found: {model_path}"
            
            if not model_path.endswith('.pt'):
                return False, "Model must be a .pt file"
            
            # Import ultralytics here to avoid slow startup
            from ultralytics import YOLO
            
            print(f"[Model] Loading model from: {model_path}")
            self.model = YOLO(model_path)
            
            # Try to use CUDA, fallback to CPU
            try:
                import torch
                if torch.cuda.is_available():
                    self.device = 'cuda'
                    print(f"[Model] Using CUDA: {torch.cuda.get_device_name(0)}")
                else:
                    self.device = 'cpu'
                    print("[Model] CUDA not available, using CPU")
            except Exception:
                self.device = 'cpu'
                print("[Model] Using CPU")
            
            # Get class names
            self.classes = list(self.model.names.values())
            self.model_path = model_path
            
            print(f"[Model] Loaded successfully. Classes: {self.classes}")
            return True, f"Model loaded successfully with {len(self.classes)} classes"
            
        except Exception as e:
            self.model = None
            self.classes = []
            return False, f"Error loading model: {str(e)}"
    
    def is_loaded(self) -> bool:
        """Check if a model is currently loaded."""
        return self.model is not None
    
    def get_classes(self) -> List[str]:
        """Get the list of class names from the loaded model."""
        return self.classes
    
    def predict(self, frame, conf: float = 0.5, classes: Optional[List[int]] = None):
        """
        Run prediction on a frame.
        
        Args:
            frame: Image frame (numpy array)
            conf: Confidence threshold
            classes: List of class indices to detect (None = all)
            
        Returns:
            YOLO Results object or None
        """
        if self.model is None:
            return None
        
        try:
            results = self.model.predict(
                source=frame,
                conf=conf,
                classes=classes,
                device=self.device,
                verbose=False,
                stream=False
            )
            return results[0] if results else None
        except Exception as e:
            print(f"[Model] Prediction error: {e}")
            return None
    
    def unload(self) -> None:
        """Unload the current model."""
        self.model = None
        self.model_path = None
        self.classes = []
        print("[Model] Model unloaded")
