# ============================================
# OVERLAY DE DEBUG
# Mostra detecções e informações na tela
# ============================================

import cv2
import numpy as np
from config import Config

class Overlay:
    def __init__(self):
        self.window_name = "EUREKA - Debug Overlay"
        if Config.SHOW_OVERLAY:
            cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(self.window_name, 640, 480)
    
    def draw(self, frame, detections, target=None, fps=0, active=False):
        """Desenha overlay com informações de debug."""
        if not Config.SHOW_OVERLAY:
            return
        
        display = frame.copy()
        h, w = display.shape[:2]
        center_x, center_y = w // 2, h // 2
        
        # Desenhar crosshair central
        color = (0, 255, 0) if active else (128, 128, 128)
        cv2.line(display, (center_x - 20, center_y), (center_x + 20, center_y), color, 2)
        cv2.line(display, (center_x, center_y - 20), (center_x, center_y + 20), color, 2)
        
        # Desenhar FOV circle
        cv2.circle(display, (center_x, center_y), Config.AIM_FOV // 2, (50, 50, 50), 1)
        
        # Desenhar todas as detecções
        for det in detections:
            x1, y1, x2, y2 = det.get_bbox()
            
            # Cor baseada se é o alvo selecionado
            if target and det == target:
                box_color = (0, 255, 255)  # Amarelo para alvo
                thickness = 2
            else:
                box_color = (255, 0, 0)  # Azul para outros
                thickness = 1
            
            # Desenhar bounding box
            cv2.rectangle(display, (x1, y1), (x2, y2), box_color, thickness)
            
            # Desenhar ponto de mira
            cv2.circle(display, (det.aim_x, det.aim_y), 5, (0, 0, 255), -1)
            
            # Mostrar confidence
            label = f"{det.confidence:.2f}"
            cv2.putText(display, label, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 1)
        
        # Linha para o target atual
        if target and active:
            cv2.line(display, (center_x, center_y), 
                    (target.aim_x, target.aim_y), (0, 255, 255), 1)
        
        # Info panel
        status = "ACTIVE" if active else "STANDBY"
        mode = "TEST MODE" if Config.TEST_MODE else "YOLO"
        
        cv2.rectangle(display, (5, 5), (200, 80), (0, 0, 0), -1)
        cv2.putText(display, f"FPS: {fps:.0f}", (10, 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(display, f"Status: {status}", (10, 45), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        cv2.putText(display, f"Mode: {mode}", (10, 65), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        # Detections count
        cv2.putText(display, f"Targets: {len(detections)}", (10, 85), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv2.imshow(self.window_name, display)
    
    def process_keys(self):
        """Processa teclas do OpenCV e retorna se deve continuar."""
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:  # Q ou ESC
            return False
        return True
    
    def close(self):
        """Fecha a janela."""
        cv2.destroyAllWindows()
