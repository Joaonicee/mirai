# ============================================
# OVERLAY TRANSPARENTE
# Mostra bounding boxes dos alvos na tela
# ============================================

import ctypes
from ctypes import wintypes
import threading
import time
from config import Config

# Windows API constants
WS_EX_LAYERED = 0x80000
WS_EX_TRANSPARENT = 0x20
WS_EX_TOPMOST = 0x8
WS_EX_TOOLWINDOW = 0x80
WS_POPUP = 0x80000000
GWL_EXSTYLE = -20
LWA_COLORKEY = 0x1
LWA_ALPHA = 0x2

# GDI constants
PS_SOLID = 0
TRANSPARENT = 1

# Colors (BGR format for GDI)
COLOR_GREEN = 0x00FF00
COLOR_YELLOW = 0x00FFFF
COLOR_RED = 0x0000FF
COLOR_TRANSPARENT = 0x000001  # Cor que será transparente

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

# Definir tipos que podem não existir em wintypes
HCURSOR = wintypes.HANDLE
HICON = wintypes.HANDLE
HBRUSH = wintypes.HANDLE

class WNDCLASSEX(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("style", ctypes.c_uint),
        ("lpfnWndProc", ctypes.WINFUNCTYPE(ctypes.c_long, wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM)),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", HICON),
        ("hCursor", HCURSOR),
        ("hbrBackground", HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", HICON),
    ]


class TransparentOverlay:
    """Overlay transparente que desenha bounding boxes sobre a tela."""
    
    def __init__(self):
        self.enabled = Config.SHOW_OVERLAY
        self.hwnd = None
        self.running = False
        self.detections = []
        self.target = None
        self.lock = threading.Lock()
        
        # Dimensões da tela
        self.screen_width = user32.GetSystemMetrics(0)
        self.screen_height = user32.GetSystemMetrics(1)
        
        # Offset da região de captura (para converter coordenadas)
        self.capture_offset_x = (self.screen_width - Config.CAPTURE_WIDTH) // 2
        self.capture_offset_y = (self.screen_height - Config.CAPTURE_HEIGHT) // 2
        
        if self.enabled:
            self._start_overlay_thread()
    
    def _start_overlay_thread(self):
        """Inicia a thread do overlay."""
        self.running = True
        self.thread = threading.Thread(target=self._overlay_loop, daemon=True)
        self.thread.start()
    
    def _overlay_loop(self):
        """Loop principal do overlay."""
        # Criar janela
        self._create_window()
        
        # Loop de mensagens com redraw periódico
        msg = wintypes.MSG()
        last_draw = 0
        
        while self.running:
            # Processar mensagens do Windows
            if user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            
            # Redesenhar periodicamente
            now = time.time()
            if now - last_draw > 0.016:  # ~60 FPS
                self._redraw()
                last_draw = now
            
            time.sleep(0.001)
        
        if self.hwnd:
            user32.DestroyWindow(self.hwnd)
    
    def _create_window(self):
        """Cria a janela transparente do overlay."""
        # Definir callback de janela
        def wnd_proc(hwnd, msg, wparam, lparam):
            if msg == 0x000F:  # WM_PAINT
                self._on_paint(hwnd)
                return 0
            elif msg == 0x0002:  # WM_DESTROY
                return 0
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)
        
        self.wnd_proc = ctypes.WINFUNCTYPE(
            ctypes.c_long, wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM
        )(wnd_proc)
        
        # Registrar classe de janela
        wc = WNDCLASSEX()
        wc.cbSize = ctypes.sizeof(WNDCLASSEX)
        wc.lpfnWndProc = self.wnd_proc
        wc.hInstance = kernel32.GetModuleHandleW(None)
        wc.lpszClassName = "EurekaOverlay"
        wc.hbrBackground = gdi32.CreateSolidBrush(COLOR_TRANSPARENT)
        
        user32.RegisterClassExW(ctypes.byref(wc))
        
        # Criar janela
        ex_style = WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_TOOLWINDOW
        
        self.hwnd = user32.CreateWindowExW(
            ex_style,
            "EurekaOverlay",
            "Eureka Overlay",
            WS_POPUP,
            0, 0,
            self.screen_width, self.screen_height,
            None, None,
            kernel32.GetModuleHandleW(None),
            None
        )
        
        # Configurar transparência
        user32.SetLayeredWindowAttributes(
            self.hwnd,
            COLOR_TRANSPARENT,
            0,
            LWA_COLORKEY
        )
        
        # Mostrar janela
        user32.ShowWindow(self.hwnd, 1)
        user32.UpdateWindow(self.hwnd)
    
    def _on_paint(self, hwnd):
        """Callback de pintura."""
        ps = (ctypes.c_byte * 68)()
        hdc = user32.BeginPaint(hwnd, ctypes.byref(ps))
        
        # Limpar com cor transparente
        brush = gdi32.CreateSolidBrush(COLOR_TRANSPARENT)
        rect = (ctypes.c_int * 4)(0, 0, self.screen_width, self.screen_height)
        user32.FillRect(hdc, ctypes.byref(rect), brush)
        gdi32.DeleteObject(brush)
        
        # Desenhar detecções
        with self.lock:
            detections = self.detections.copy()
            target = self.target
        
        for det in detections:
            is_target = target is not None and self._same_detection(det, target)
            self._draw_box(hdc, det, is_target)
        
        user32.EndPaint(hwnd, ctypes.byref(ps))
    
    def _same_detection(self, det1, det2):
        """Verifica se duas detecções são a mesma."""
        if hasattr(det1, 'track_id') and hasattr(det2, 'track_id'):
            return det1.track_id == det2.track_id
        return abs(det1.x - det2.x) < 5 and abs(det1.y - det2.y) < 5
    
    def _draw_box(self, hdc, detection, is_target=False):
        """Desenha uma bounding box."""
        x1, y1, x2, y2 = detection.get_bbox()
        
        # Converter para coordenadas de tela
        x1 += self.capture_offset_x
        y1 += self.capture_offset_y
        x2 += self.capture_offset_x
        y2 += self.capture_offset_y
        
        # Cor baseada se é o alvo
        color = COLOR_YELLOW if is_target else COLOR_GREEN
        thickness = 3 if is_target else 2
        
        # Criar pen
        pen = gdi32.CreatePen(PS_SOLID, thickness, color)
        old_pen = gdi32.SelectObject(hdc, pen)
        
        # Desenhar retângulo (apenas contorno)
        gdi32.SetBkMode(hdc, TRANSPARENT)
        
        # Linhas do retângulo
        gdi32.MoveToEx(hdc, x1, y1, None)
        gdi32.LineTo(hdc, x2, y1)
        gdi32.LineTo(hdc, x2, y2)
        gdi32.LineTo(hdc, x1, y2)
        gdi32.LineTo(hdc, x1, y1)
        
        # Desenhar crosshair no ponto de mira
        aim_x = detection.aim_x + self.capture_offset_x
        aim_y = detection.aim_y + self.capture_offset_y
        
        cross_size = 5
        gdi32.MoveToEx(hdc, aim_x - cross_size, aim_y, None)
        gdi32.LineTo(hdc, aim_x + cross_size, aim_y)
        gdi32.MoveToEx(hdc, aim_x, aim_y - cross_size, None)
        gdi32.LineTo(hdc, aim_x, aim_y + cross_size)
        
        # Limpar
        gdi32.SelectObject(hdc, old_pen)
        gdi32.DeleteObject(pen)
    
    def _redraw(self):
        """Força redesenho da janela."""
        if self.hwnd:
            user32.InvalidateRect(self.hwnd, None, True)
    
    def update(self, detections, target=None):
        """Atualiza as detecções a serem desenhadas."""
        if not self.enabled:
            return
        
        with self.lock:
            self.detections = list(detections) if detections else []
            self.target = target
    
    def close(self):
        """Fecha o overlay."""
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=1.0)


# Overlay simples usando OpenCV (fallback)
class OpenCVOverlay:
    """Overlay usando OpenCV para debug (janela separada)."""
    
    def __init__(self):
        import cv2
        self.cv2 = cv2
        self.enabled = Config.SHOW_OVERLAY
        self.window_name = "EUREKA - Target Overlay"
        
        if self.enabled:
            cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(self.window_name, Config.CAPTURE_WIDTH, Config.CAPTURE_HEIGHT)
    
    def update(self, frame, detections, target=None, fps=0):
        """Atualiza o overlay com o frame atual."""
        if not self.enabled:
            return
        
        display = frame.copy()
        h, w = display.shape[:2]
        center_x, center_y = w // 2, h // 2
        
        # Desenhar crosshair central
        self.cv2.line(display, (center_x - 20, center_y), (center_x + 20, center_y), (0, 255, 0), 2)
        self.cv2.line(display, (center_x, center_y - 20), (center_x, center_y + 20), (0, 255, 0), 2)
        
        # Desenhar todas as detecções
        for det in detections:
            x1, y1, x2, y2 = det.get_bbox()
            
            # Cor baseada se é o alvo selecionado
            is_target = target is not None and self._same_detection(det, target)
            
            if is_target:
                box_color = (0, 255, 255)  # Amarelo para alvo
                thickness = 3
            else:
                box_color = (0, 255, 0)  # Verde para outros
                thickness = 2
            
            # Desenhar bounding box
            self.cv2.rectangle(display, (x1, y1), (x2, y2), box_color, thickness)
            
            # Desenhar ponto de mira
            self.cv2.circle(display, (det.aim_x, det.aim_y), 5, (0, 0, 255), -1)
            
            # Mostrar track_id se disponível
            label = f"#{det.track_id}" if hasattr(det, 'track_id') and det.track_id >= 0 else ""
            if label:
                self.cv2.putText(display, label, (x1, y1 - 5), 
                               self.cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 1)
        
        # Linha para o target atual
        if target:
            self.cv2.line(display, (center_x, center_y), 
                        (target.aim_x, target.aim_y), (0, 255, 255), 1)
        
        # Info panel
        self.cv2.rectangle(display, (5, 5), (150, 50), (0, 0, 0), -1)
        self.cv2.putText(display, f"FPS: {fps:.0f}", (10, 25), 
                       self.cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        self.cv2.putText(display, f"Targets: {len(detections)}", (10, 45), 
                       self.cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        self.cv2.imshow(self.window_name, display)
    
    def _same_detection(self, det1, det2):
        """Verifica se duas detecções são a mesma."""
        if hasattr(det1, 'track_id') and hasattr(det2, 'track_id'):
            return det1.track_id == det2.track_id
        return abs(det1.x - det2.x) < 5 and abs(det1.y - det2.y) < 5
    
    def process_keys(self):
        """Processa teclas do OpenCV."""
        key = self.cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            return False
        return True
    
    def close(self):
        """Fecha o overlay."""
        self.cv2.destroyAllWindows()


def get_overlay():
    """Retorna o overlay apropriado."""
    if not Config.SHOW_OVERLAY:
        return None
    
    # Tentar usar o overlay transparente, fallback para OpenCV
    try:
        overlay = TransparentOverlay()
        return overlay
    except Exception as e:
        print(f"[!] Erro ao criar overlay transparente: {e}")
        print("[!] Usando overlay OpenCV como fallback")
        return OpenCVOverlay()
