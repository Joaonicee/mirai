# ============================================
# SELETOR DE ALVOS INTELIGENTE
# Seleciona o melhor alvo baseado em distância e FOV
# ============================================

import math
from config import Config

class TargetSelector:
    def __init__(self, screen_width, screen_height, capture_width, capture_height):
        # Centro da região de captura
        self.center_x = capture_width // 2
        self.center_y = capture_height // 2
        self.fov_radius = Config.AIM_FOV // 2
        
        self.last_target = None
        self.sticky_frames = 0  # Frames para manter o mesmo alvo
    
    def get_distance(self, det):
        """Calcula distância do alvo ao centro."""
        dx = det.aim_x - self.center_x
        dy = det.aim_y - self.center_y
        return math.sqrt(dx * dx + dy * dy)
    
    def is_in_fov(self, det):
        """Verifica se o alvo está dentro do FOV."""
        return self.get_distance(det) <= self.fov_radius
    
    def select_best_target(self, detections):
        """
        Seleciona o melhor alvo da lista.
        Prioriza: 1) Alvo atual (sticky), 2) Mais próximo do centro
        """
        if not detections:
            self.last_target = None
            self.sticky_frames = 0
            return None
        
        # Filtrar apenas alvos dentro do FOV
        valid_targets = [d for d in detections if self.is_in_fov(d)]
        
        if not valid_targets:
            self.last_target = None
            self.sticky_frames = 0
            return None
        
        # Se temos um target anterior e ele ainda existe, manter (sticky aim)
        if self.last_target and self.sticky_frames < 30:  # Max 30 frames sticky
            for det in valid_targets:
                # Verificar se é aproximadamente o mesmo alvo
                dist_to_last = math.sqrt(
                    (det.aim_x - self.last_target.aim_x) ** 2 +
                    (det.aim_y - self.last_target.aim_y) ** 2
                )
                if dist_to_last < 50:  # Threshold para considerar mesmo alvo
                    self.sticky_frames += 1
                    self.last_target = det
                    return det
        
        # Selecionar o mais próximo do centro
        best = min(valid_targets, key=self.get_distance)
        self.last_target = best
        self.sticky_frames = 0
        return best
    
    def get_aim_offset(self, target):
        """Retorna o offset necessário para mirar no alvo."""
        if target is None:
            return (0, 0)
        
        dx = target.aim_x - self.center_x
        dy = target.aim_y - self.center_y
        return (dx, dy)
    
    def is_on_target(self, target):
        """Verifica se o crosshair está no alvo."""
        if target is None:
            return False
        
        dist = self.get_distance(target)
        return dist <= Config.TRIGGER_THRESHOLD
