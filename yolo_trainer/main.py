"""
YOLO Trainer - Main Entry Point
A modern GUI application for training YOLO models on Roboflow datasets
"""

from src.app import YOLOTrainerApp


if __name__ == "__main__":
    app = YOLOTrainerApp()
    app.run()
