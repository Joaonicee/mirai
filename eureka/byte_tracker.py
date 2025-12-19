# ============================================
# BYTETRACK WRAPPER
# Integração do ByteTrack para tracking melhorado
# ============================================

import numpy as np
from config import Config

try:
    from bytetracker import BYTETracker
    BYTETRACK_AVAILABLE = True
except ImportError:
    BYTETRACK_AVAILABLE = False
    print("[!] ByteTrack não instalado. Use: pip install bytetracker")
    print("[!] Usando tracking básico como fallback")


class ByteTrackArgs:
    """Argumentos para o BYTETracker."""
    def __init__(self):
        self.track_thresh = Config.TRACK_THRESH
        self.track_buffer = Config.TRACK_BUFFER
        self.match_thresh = Config.MATCH_THRESH
        self.mot20 = False


class TrackedDetection:
    """Detecção com informações de tracking."""
    def __init__(self, detection, track_id=-1):
        self.x = detection.x
        self.y = detection.y
        self.w = detection.w
        self.h = detection.h
        self.confidence = detection.confidence
        self.class_id = detection.class_id
        self.aim_x = detection.aim_x
        self.aim_y = detection.aim_y
        self.track_id = track_id
    
    def get_bbox(self):
        """Retorna bounding box (x1, y1, x2, y2)."""
        x1 = int(self.x - self.w / 2)
        y1 = int(self.y - self.h / 2)
        x2 = int(self.x + self.w / 2)
        y2 = int(self.y + self.h / 2)
        return (x1, y1, x2, y2)


class ByteTrackWrapper:
    """Wrapper para integrar ByteTrack com as detecções."""
    
    def __init__(self, frame_rate=60):
        self.enabled = Config.ENABLE_BYTETRACK and BYTETRACK_AVAILABLE
        
        if self.enabled:
            args = ByteTrackArgs()
            self.tracker = BYTETracker(args, frame_rate=frame_rate)
            print("[+] ByteTrack inicializado")
        else:
            self.tracker = None
            self.simple_tracks = {}  # Fallback simples
            self.next_track_id = 1
            self.frame_count = 0
        
        self.last_tracked = []
    
    def update(self, detections, img_info=None, img_size=None):
        """
        Atualiza o tracker com novas detecções.
        
        Args:
            detections: Lista de Detection objects
            img_info: Tuple (height, width) da imagem
            img_size: Tuple (height, width) do tamanho de processamento
        
        Returns:
            Lista de TrackedDetection objects com track_ids
        """
        if not detections:
            self.last_tracked = []
            return []
        
        if self.enabled and self.tracker is not None:
            return self._update_bytetrack(detections, img_info, img_size)
        else:
            return self._update_simple(detections)
    
    def _update_bytetrack(self, detections, img_info, img_size):
        """Atualiza usando ByteTrack."""
        # Converter detecções para formato numpy [x1, y1, x2, y2, score]
        det_array = []
        for det in detections:
            x1, y1, x2, y2 = det.get_bbox()
            det_array.append([x1, y1, x2, y2, det.confidence])
        
        if not det_array:
            return []
        
        online_targets = self.tracker.update(
            np.array(det_array),
            img_info if img_info else [Config.CAPTURE_HEIGHT, Config.CAPTURE_WIDTH],
            img_size if img_size else [Config.CAPTURE_HEIGHT, Config.CAPTURE_WIDTH]
        )
        
        tracked = []
        for t in online_targets:
            tlwh = t.tlwh  # top-left x, top-left y, width, height
            track_id = t.track_id
            
            # Encontrar a detecção original mais próxima
            best_det = None
            best_dist = float('inf')
            t_cx = tlwh[0] + tlwh[2] / 2
            t_cy = tlwh[1] + tlwh[3] / 2
            
            for det in detections:
                dist = ((det.x - t_cx) ** 2 + (det.y - t_cy) ** 2) ** 0.5
                if dist < best_dist:
                    best_dist = dist
                    best_det = det
            
            if best_det:
                tracked.append(TrackedDetection(best_det, track_id))
        
        self.last_tracked = tracked
        return tracked
    
    def _update_simple(self, detections):
        """Fallback robusto quando ByteTrack não está disponível (usa IoU matching)."""
        self.frame_count += 1
        tracked = []
        
        # Calcular IoU entre detecções e tracks existentes
        def calculate_iou(det, track_pos):
            tx, ty, tw, th, _ = track_pos
            
            # Bboxes
            det_x1, det_y1, det_x2, det_y2 = det.get_bbox()
            track_x1 = tx - tw / 2
            track_y1 = ty - th / 2
            track_x2 = tx + tw / 2
            track_y2 = ty + th / 2
            
            # Interseção
            inter_x1 = max(det_x1, track_x1)
            inter_y1 = max(det_y1, track_y1)
            inter_x2 = min(det_x2, track_x2)
            inter_y2 = min(det_y2, track_y2)
            
            if inter_x1 >= inter_x2 or inter_y1 >= inter_y2:
                return 0.0
            
            inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
            det_area = (det_x2 - det_x1) * (det_y2 - det_y1)
            track_area = tw * th
            union_area = det_area + track_area - inter_area
            
            return inter_area / union_area if union_area > 0 else 0.0
        
        # Match detections to existing tracks usando IoU
        used_tracks = set()
        unmatched_dets = []
        
        for det in detections:
            best_track_id = -1
            best_iou = 0.3  # Threshold mínimo de IoU
            
            for tid, track_data in self.simple_tracks.items():
                if tid in used_tracks:
                    continue
                # Só considerar tracks recentes
                if self.frame_count - track_data[4] > Config.TRACK_BUFFER:
                    continue
                
                iou = calculate_iou(det, track_data)
                if iou > best_iou:
                    best_iou = iou
                    best_track_id = tid
            
            if best_track_id >= 0:
                used_tracks.add(best_track_id)
                # Atualizar track com nova posição (com suavização)
                old_data = self.simple_tracks[best_track_id]
                alpha = 0.7  # Peso para nova detecção
                new_x = alpha * det.x + (1 - alpha) * old_data[0]
                new_y = alpha * det.y + (1 - alpha) * old_data[1]
                self.simple_tracks[best_track_id] = (
                    new_x, new_y, det.w, det.h, self.frame_count
                )
                tracked.append(TrackedDetection(det, best_track_id))
            else:
                unmatched_dets.append(det)
        
        # Criar novos tracks para detecções não matcheadas
        for det in unmatched_dets:
            new_id = self.next_track_id
            self.next_track_id += 1
            self.simple_tracks[new_id] = (
                det.x, det.y, det.w, det.h, self.frame_count
            )
            tracked.append(TrackedDetection(det, new_id))
        
        # Limpar tracks antigas
        old_tracks = [tid for tid, data in self.simple_tracks.items() 
                      if self.frame_count - data[4] > Config.TRACK_BUFFER]
        for tid in old_tracks:
            del self.simple_tracks[tid]
        
        self.last_tracked = tracked
        return tracked
    
    def get_track_by_id(self, track_id):
        """Retorna a detecção com o track_id especificado."""
        for t in self.last_tracked:
            if t.track_id == track_id:
                return t
        return None
