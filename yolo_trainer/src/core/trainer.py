"""
YOLO Trainer - Training logic with progress callbacks
"""

import os
import threading
from pathlib import Path
from typing import Callable, Optional, Dict, Any
from ultralytics import YOLO
from .gpu_utils import GPUUtils


class TrainingCallback:
    """Custom callback to capture training progress"""
    
    def __init__(self, on_epoch_end: Callable = None, on_log: Callable = None):
        self.on_epoch_end = on_epoch_end
        self.on_log = on_log
        self.current_epoch = 0
        self.total_epochs = 0
        self.metrics = {}
    
    def __call__(self, trainer):
        """Called at the end of each epoch"""
        self.current_epoch = trainer.epoch + 1
        self.total_epochs = trainer.epochs
        
        # Extract metrics
        self.metrics = {
            'epoch': self.current_epoch,
            'total_epochs': self.total_epochs,
            'box_loss': trainer.loss_items[0].item() if hasattr(trainer, 'loss_items') and trainer.loss_items is not None else 0,
            'cls_loss': trainer.loss_items[1].item() if hasattr(trainer, 'loss_items') and trainer.loss_items is not None and len(trainer.loss_items) > 1 else 0,
            'dfl_loss': trainer.loss_items[2].item() if hasattr(trainer, 'loss_items') and trainer.loss_items is not None and len(trainer.loss_items) > 2 else 0,
        }
        
        # Get validation metrics if available
        if hasattr(trainer, 'metrics') and trainer.metrics:
            metrics_dict = trainer.metrics
            if hasattr(metrics_dict, 'box'):
                self.metrics['mAP50'] = metrics_dict.box.map50 if hasattr(metrics_dict.box, 'map50') else 0
                self.metrics['mAP50-95'] = metrics_dict.box.map if hasattr(metrics_dict.box, 'map') else 0
        
        if self.on_epoch_end:
            self.on_epoch_end(self.metrics)


class YOLOTrainer:
    """YOLO model trainer with GUI integration"""
    
    def __init__(self):
        self.model: Optional[YOLO] = None
        self.is_training = False
        self.training_thread: Optional[threading.Thread] = None
        self.stop_requested = False
        
        # Callbacks
        self.on_progress: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_log: Optional[Callable[[str], None]] = None
        self.on_complete: Optional[Callable[[bool, str], None]] = None
    
    def log(self, message: str):
        """Send log message to callback"""
        if self.on_log:
            self.on_log(message)
    
    def validate_dataset(self, dataset_path: str) -> tuple[bool, str]:
        """
        Validate Roboflow dataset structure
        
        Returns:
            Tuple of (is_valid, message)
        """
        path = Path(dataset_path)
        
        if not path.exists():
            return False, "Dataset path does not exist"
        
        # Look for data.yaml
        data_yaml = path / "data.yaml"
        if not data_yaml.exists():
            # Check in parent or common locations
            possible_locations = [
                path / "data.yaml",
                path.parent / "data.yaml",
            ]
            data_yaml = None
            for loc in possible_locations:
                if loc.exists():
                    data_yaml = loc
                    break
            
            if not data_yaml:
                return False, "data.yaml not found in dataset folder"
        
        # Check for train/valid folders
        train_folder = path / "train"
        valid_folder = path / "valid"
        
        if not train_folder.exists():
            # Some Roboflow exports have images directly
            images_folder = path / "train" / "images"
            if not images_folder.exists():
                return False, "Training images folder not found"
        
        return True, str(data_yaml)
    
    def train(
        self,
        dataset_path: str,
        model_type: str = "yolov8n",
        output_name: str = "custom_model",
        epochs: int = 100,
        batch_size: int = 16,
        img_size: int = 640,
        output_dir: str = None
    ):
        """
        Start training in a separate thread
        """
        if self.is_training:
            self.log("[ERROR] Training already in progress")
            return
        
        self.stop_requested = False
        self.training_thread = threading.Thread(
            target=self._train_worker,
            args=(dataset_path, model_type, output_name, epochs, batch_size, img_size, output_dir),
            kwargs={'resume': False}, # Gets updated by train call if needed
            daemon=True
        )
        # Store args for thread to pick up
        self._thread_args = {
            'dataset_path': dataset_path,
            'model_type': model_type,
            'output_name': output_name,
            'epochs': epochs,
            'batch_size': batch_size,
            'img_size': img_size,
            'output_dir': output_dir,
            'resume': False
        }
        self.training_thread.start()
    
    def train_with_options(self, options: Dict[str, Any]):
        """Start training with options dictionary"""
        if self.is_training:
            self.log("[ERROR] Training already in progress")
            return
            
        self.stop_requested = False
        self.training_thread = threading.Thread(
            target=self._train_worker,
            args=(),
            kwargs=options,
            daemon=True
        )
        self.training_thread.start()

    def _train_worker(
        self,
        dataset_path: str,
        model_type: str,
        output_name: str,
        epochs: int,
        batch_size: int,
        img_size: int,
        output_dir: str,
        resume: bool = False
    ):
        """Training worker thread"""
        self.is_training = True
        success = False
        message = ""
        
        try:
            # Set CUDA memory allocation config to avoid fragmentation
            import os
            os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'
            
            # Clear CUDA cache and run garbage collection
            import gc
            gc.collect()
            GPUUtils.clear_cache()
            
            # Validate dataset
            self.log("[INFO] Validating dataset...")
            is_valid, result = self.validate_dataset(dataset_path)
            
            if not is_valid:
                raise Exception(result)
            
            data_yaml_path = result
            self.log(f"[INFO] Found data.yaml: {data_yaml_path}")
            
            # Check GPU
            device = GPUUtils.get_device()
            gpu_status = GPUUtils.get_status_string()
            self.log(f"[INFO] Device: {gpu_status}")
            
            # Clear cache again before loading model
            GPUUtils.clear_cache()
            
            # Set output directory
            if output_dir is None:
                output_dir = str(Path(dataset_path).parent / "runs")
            
            project_dir = Path(output_dir)
            project_dir.mkdir(parents=True, exist_ok=True)
            
            # Handle Resume vs New Training
            if resume:
                self.log("[INFO] Resuming from last checkpoint...")
                # Search for last.pt in the output directory
                last_pt = project_dir / output_name / "weights" / "last.pt"
                if not last_pt.exists():
                     self.log(f"[WARNING] Checkpoint not found at {last_pt}. Starting fresh.")
                     resume = False
                else:
                    self.log(f"[INFO] Found checkpoint: {last_pt}")
                    model_file = str(last_pt)
                    self.model = YOLO(model_file)
            
            if not resume:
                # Load model
                self.log(f"[INFO] Loading {model_type} model...")
                
                # Model info for user
                model_info = {
                    "yolov5n": "YOLOv5 Nano - Fastest (~200 FPS)",
                    "yolov5s": "YOLOv5 Small - Fast (~100 FPS)",
                    "yolov5m": "YOLOv5 Medium (~60 FPS)",
                    "yolov5l": "YOLOv5 Large (~30 FPS)",
                    "yolov5x": "YOLOv5 XLarge (~15 FPS)",
                    "yolov8n": "YOLOv8 Nano - Fast (~150 FPS)",
                    "yolov8s": "YOLOv8 Small (~80 FPS)",
                    "yolov8m": "YOLOv8 Medium (~50 FPS)",
                    "yolov8l": "YOLOv8 Large (~25 FPS)",
                    "yolov8x": "YOLOv8 XLarge (~12 FPS)",
                }
                self.log(f"[INFO] Model: {model_info.get(model_type, model_type)}")
                
                model_file = f"{model_type}.pt"
                self.model = YOLO(model_file)
            
            
            self.log(f"[INFO] Starting training for {epochs} epochs...")
            self.log(f"[INFO] Batch size: {batch_size}, Image size: {img_size}")
            self.log(f"[INFO] Workers set to 0 to prevent crashes")
            
            # Custom callback for progress
            def on_epoch_end_callback(metrics):
                if self.on_progress:
                    self.on_progress(metrics)
                
                epoch = metrics.get('epoch', 0)
                total = metrics.get('total_epochs', epochs)
                box_loss = metrics.get('box_loss', 0)
                
                self.log(f"[EPOCH {epoch}/{total}] box_loss: {box_loss:.4f}")
            
            # Train the model
            results = self.model.train(
                data=data_yaml_path,
                epochs=epochs,
                batch=batch_size,
                imgsz=img_size,
                device=device,
                project=str(project_dir),
                name=output_name,
                exist_ok=True,
                verbose=True,
                plots=True,
                workers=0,  # CRITICAL: Fix for DataLoader crash on Windows
                resume=resume
            )
            
            # Save the final model as .pt
            final_model_path = project_dir / output_name / "weights" / "best.pt"
            output_model_path = project_dir / f"{output_name}.pt"
            
            if final_model_path.exists():
                import shutil
                shutil.copy(final_model_path, output_model_path)
                self.log(f"[SUCCESS] Model saved to: {output_model_path}")
                success = True
                message = str(output_model_path)
            else:
                # Try last.pt
                last_model_path = project_dir / output_name / "weights" / "last.pt"
                if last_model_path.exists():
                    import shutil
                    shutil.copy(last_model_path, output_model_path)
                    self.log(f"[SUCCESS] Model saved to: {output_model_path}")
                    success = True
                    message = str(output_model_path)
                else:
                    raise Exception("Could not find trained model weights")
            
        except Exception as e:
            self.log(f"[ERROR] Training failed: {str(e)}")
            message = str(e)
            success = False
        
        finally:
            self.is_training = False
            GPUUtils.clear_cache()
            
            if self.on_complete:
                self.on_complete(success, message)
    
    def stop_training(self):
        """Request training to stop"""
        if self.is_training:
            self.stop_requested = True
            self.log("[INFO] Stop requested - training will stop after current epoch")
            # Note: Ultralytics doesn't have a clean way to interrupt training
            # The user may need to wait for current epoch to finish
