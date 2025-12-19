"""
Detection Engine for MirAi
Handles object detection and target selection.
"""

import math
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass


@dataclass
class Detection:
    """Represents a single detection."""
    x1: float  # Left
    y1: float  # Top
    x2: float  # Right
    y2: float  # Bottom
    confidence: float
    class_id: int
    class_name: str
    
    @property
    def center(self) -> Tuple[float, float]:
        """Get center point of the detection."""
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)
    
    @property
    def width(self) -> float:
        return self.x2 - self.x1
    
    @property
    def height(self) -> float:
        return self.y2 - self.y1
    
    def get_aim_point(self, head_offset: float = 0.0) -> Tuple[float, float]:
        """
        Get the aim point with head offset.
        
        Args:
            head_offset: Offset from top as percentage of height (0.0 - 1.0)
                         0.0 = aim at top, 0.5 = aim at center, 1.0 = aim at bottom
                         
        Returns:
            (x, y) tuple of the aim point
        """
        cx = (self.x1 + self.x2) / 2
        # Calculate y position based on offset
        # head_offset of 0.2 means aim 20% down from the top
        cy = self.y1 + (self.height * head_offset)
        return (cx, cy)


class Detector:
    """Detection engine that processes YOLO results and selects targets."""
    
    def __init__(self):
        self.last_detections: List[Detection] = []
        self.current_target: Optional[Detection] = None
    
    def process_results(
        self,
        results,
        offset: Tuple[int, int] = (0, 0),
        target_classes: Optional[List[int]] = None,
        confidence_threshold: float = 0.5
    ) -> List[Detection]:
        """
        Process YOLO results into detection objects.
        
        Args:
            results: YOLO Results object
            offset: (x, y) offset to add to coordinates (for FOV capture)
            target_classes: List of class indices to include (None = all)
            confidence_threshold: Minimum confidence to include
            
        Returns:
            List of Detection objects
        """
        detections = []
        
        if results is None or results.boxes is None:
            self.last_detections = []
            return []
        
        boxes = results.boxes
        
        for i in range(len(boxes)):
            conf = float(boxes.conf[i])
            if conf < confidence_threshold:
                continue
            
            class_id = int(boxes.cls[i])
            if target_classes and class_id not in target_classes:
                continue
            
            # Get box coordinates
            box = boxes.xyxy[i].cpu().numpy()
            x1, y1, x2, y2 = box
            
            # Apply offset
            x1 += offset[0]
            y1 += offset[1]
            x2 += offset[0]
            y2 += offset[1]
            
            # Get class name
            class_name = results.names.get(class_id, f"class_{class_id}")
            
            detection = Detection(
                x1=float(x1),
                y1=float(y1),
                x2=float(x2),
                y2=float(y2),
                confidence=conf,
                class_id=class_id,
                class_name=class_name
            )
            detections.append(detection)
        
        self.last_detections = detections
        return detections
    
    def select_target(
        self,
        detections: List[Detection],
        screen_center: Tuple[int, int],
        fov_radius: int,
        head_offset: float = 0.2
    ) -> Optional[Detection]:
        """
        Select the best target from detections.
        
        Args:
            detections: List of detections
            screen_center: (x, y) center of the screen
            fov_radius: FOV radius in pixels
            head_offset: Offset for aim point (0.0 = top, 0.5 = center)
            
        Returns:
            Best target detection or None
        """
        if not detections:
            self.current_target = None
            return None
        
        cx, cy = screen_center
        best_target = None
        best_distance = float('inf')
        
        for det in detections:
            aim_x, aim_y = det.get_aim_point(head_offset)
            
            # Calculate distance from screen center
            distance = math.sqrt((aim_x - cx) ** 2 + (aim_y - cy) ** 2)
            
            # Check if within FOV
            if distance <= fov_radius and distance < best_distance:
                best_distance = distance
                best_target = det
        
        self.current_target = best_target
        return best_target
    
    def get_target_offset(
        self,
        target: Detection,
        screen_center: Tuple[int, int],
        head_offset: float = 0.2
    ) -> Tuple[float, float]:
        """
        Get the offset from screen center to target aim point.
        
        Args:
            target: Target detection
            screen_center: (x, y) center of the screen
            head_offset: Offset for aim point
            
        Returns:
            (dx, dy) offset to move
        """
        aim_x, aim_y = target.get_aim_point(head_offset)
        cx, cy = screen_center
        return (aim_x - cx, aim_y - cy)
