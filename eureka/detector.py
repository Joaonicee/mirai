# ============================================
# SISTEMA DE DETECÇÃO
# Suporta YOLO (.pt) e modo de teste por cor
# ============================================

import cv2
import numpy as np
from config import Config

class Detection:
    """Representa uma detecção de alvo."""
    def __init__(self, x, y, w, h, confidence, class_id=0):
        self.x = x  # Centro X
        self.y = y  # Centro Y
        self.w = w  # Largura
        self.h = h  # Altura
        self.confidence = confidence
        self.class_id = class_id
        
        # Calcular ponto de mira (cabeça)
        self.aim_x = x
        self.aim_y = y - int(h * Config.HEAD_OFFSET)  # Offset para cabeça
    
    def get_bbox(self):
        """Retorna bounding box (x1, y1, x2, y2)."""
        x1 = int(self.x - self.w / 2)
        y1 = int(self.y - self.h / 2)
        x2 = int(self.x + self.w / 2)
        y2 = int(self.y + self.h / 2)
        return (x1, y1, x2, y2)


class YOLODetector:
    """Detector usando modelo YOLO (.pt)."""
    def __init__(self, model_path):
        try:
            from ultralytics import YOLO
            self.model = YOLO(model_path)
            self.model.to('cuda')  # Usar GPU se disponível
            print(f"[+] Modelo YOLO carregado: {model_path}")
        except Exception as e:
            print(f"[!] Erro ao carregar modelo: {e}")
            self.model = None
    
    def detect(self, frame):
        """Detecta alvos no frame usando YOLO."""
        if self.model is None:
            return []
        
        detections = []
        results = self.model.predict(
            frame,
            conf=Config.CONFIDENCE_THRESHOLD,
            verbose=False,
            imgsz=Config.CAPTURE_WIDTH
        )
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                class_id = int(box.cls[0])
                if class_id not in Config.TARGET_CLASSES:
                    continue
                
                conf = float(box.conf[0])
                x, y, w, h = box.xywh[0].tolist()
                
                detections.append(Detection(
                    x=int(x),
                    y=int(y),
                    w=int(w),
                    h=int(h),
                    confidence=conf,
                    class_id=class_id
                ))
        
        return detections


class ColorDetector:
    """
    Detector por cor para MODO DE TESTE.
    Detecta objetos de uma cor específica (útil para testar sem modelo).
    """
    def __init__(self):
        self.lower_color = np.array(Config.TEST_COLOR_LOWER)
        self.upper_color = np.array(Config.TEST_COLOR_UPPER)
        print("[+] Detector de cor inicializado (MODO TESTE)")
        print(f"    Cor HSV: {Config.TEST_COLOR_LOWER} - {Config.TEST_COLOR_UPPER}")
    
    def detect(self, frame):
        """Detecta objetos por cor."""
        detections = []
        
        # Converter para HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Criar máscara da cor
        mask = cv2.inRange(hsv, self.lower_color, self.upper_color)
        
        # Para vermelho, precisamos de duas faixas (0-10 e 170-180)
        if Config.TEST_COLOR_LOWER[0] < 10:
            lower2 = np.array([170, Config.TEST_COLOR_LOWER[1], Config.TEST_COLOR_LOWER[2]])
            upper2 = np.array([180, Config.TEST_COLOR_UPPER[1], Config.TEST_COLOR_UPPER[2]])
            mask2 = cv2.inRange(hsv, lower2, upper2)
            mask = cv2.bitwise_or(mask, mask2)
        
        # Operações morfológicas para limpar ruído
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # Encontrar contornos
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 500:  # Ignorar áreas muito pequenas
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            center_x = x + w // 2
            center_y = y + h // 2
            
            # Calcular "confidence" baseado no tamanho
            confidence = min(1.0, area / 10000)
            
            detections.append(Detection(
                x=center_x,
                y=center_y,
                w=w,
                h=h,
                confidence=confidence
            ))
        
        return detections


def get_detector():
    """Retorna o detector apropriado baseado na configuração."""
    if Config.TEST_MODE:
        return ColorDetector()
    else:
        return YOLODetector(Config.MODEL_PATH)
