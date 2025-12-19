# ============================================
# CAPTURA DE TELA ULTRA RÁPIDA
# Usa MSS para captura eficiente da GPU
# ============================================

import numpy as np
import mss
import cv2
from config import Config

class ScreenCapture:
    def __init__(self):
        self.sct = mss.mss()
        # Pegar dimensões do monitor principal
        monitor = self.sct.monitors[1]
        self.screen_width = monitor["width"]
        self.screen_height = monitor["height"]
        
        # Calcular região central de captura
        self.capture_region = {
            "left": (self.screen_width - Config.CAPTURE_WIDTH) // 2,
            "top": (self.screen_height - Config.CAPTURE_HEIGHT) // 2,
            "width": Config.CAPTURE_WIDTH,
            "height": Config.CAPTURE_HEIGHT
        }
        
        # Centro da tela (para cálculos de offset)
        self.center_x = self.screen_width // 2
        self.center_y = self.screen_height // 2
        
    def grab_frame(self):
        """Captura um frame da região central da tela."""
        screenshot = self.sct.grab(self.capture_region)
        # Converter para numpy array (BGR)
        frame = np.array(screenshot)
        # Remover canal alpha e converter para BGR
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        return frame
    
    def grab_full_screen(self):
        """Captura a tela inteira (mais lento, só para debug)."""
        monitor = self.sct.monitors[1]
        screenshot = self.sct.grab(monitor)
        frame = np.array(screenshot)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        return frame
    
    def get_region_offset(self):
        """Retorna o offset da região de captura em relação à tela."""
        return (self.capture_region["left"], self.capture_region["top"])
    
    def screen_to_absolute(self, x, y):
        """Converte coordenadas da região para coordenadas absolutas da tela."""
        offset_x, offset_y = self.get_region_offset()
        return (x + offset_x, y + offset_y)
    
    def close(self):
        """Libera recursos."""
        self.sct.close()
