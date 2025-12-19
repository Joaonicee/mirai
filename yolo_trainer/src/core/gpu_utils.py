"""
GPU Utilities - CUDA detection and GPU information
"""

import torch
from typing import Tuple, Optional


class GPUUtils:
    """Utility class for GPU/CUDA operations"""
    
    @staticmethod
    def is_cuda_available() -> bool:
        """Check if CUDA is available"""
        return torch.cuda.is_available()
    
    @staticmethod
    def get_device() -> str:
        """Get the best available device (cuda or cpu)"""
        return "cuda" if torch.cuda.is_available() else "cpu"
    
    @staticmethod
    def get_gpu_info() -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Get GPU information
        
        Returns:
            Tuple of (is_available, gpu_name, cuda_version)
        """
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            cuda_version = torch.version.cuda
            return True, gpu_name, cuda_version
        return False, None, None
    
    @staticmethod
    def get_gpu_memory() -> Tuple[Optional[float], Optional[float]]:
        """
        Get GPU memory information in GB
        
        Returns:
            Tuple of (total_memory_gb, free_memory_gb)
        """
        if torch.cuda.is_available():
            total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            allocated = torch.cuda.memory_allocated(0) / (1024**3)
            free = total - allocated
            return round(total, 2), round(free, 2)
        return None, None
    
    @staticmethod
    def get_device_count() -> int:
        """Get number of available CUDA devices"""
        return torch.cuda.device_count() if torch.cuda.is_available() else 0
    
    @staticmethod
    def clear_cache():
        """Clear CUDA cache"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    
    @staticmethod
    def get_status_string() -> str:
        """Get a formatted status string for display"""
        is_available, gpu_name, cuda_version = GPUUtils.get_gpu_info()
        
        if is_available:
            total_mem, free_mem = GPUUtils.get_gpu_memory()
            return f"✓ {gpu_name} (CUDA {cuda_version}) - {free_mem:.1f}GB free"
        else:
            return "✗ No GPU detected - Using CPU"
