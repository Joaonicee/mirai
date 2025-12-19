# ============================================
# CONTROLADOR DE MOUSE PARA ROBLOX/JOGOS
# Usa SendInput para inputs externos reais
# Funciona com anti-cheat básico
# ============================================

import ctypes
import ctypes.wintypes
import time
import random
import math
from config import Config

# Estruturas do Windows para SendInput
class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_ulong),
        ("mi", MOUSEINPUT)
    ]

# Constantes
INPUT_MOUSE = 0
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010

class MouseController:
    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.last_move_time = 0
        self.accumulated_x = 0.0
        self.accumulated_y = 0.0
        
    def get_position(self):
        """Retorna a posição atual do mouse."""
        point = ctypes.wintypes.POINT()
        self.user32.GetCursorPos(ctypes.byref(point))
        return (point.x, point.y)
    
    def _send_input(self, dx, dy, flags=MOUSEEVENTF_MOVE):
        """Envia input usando SendInput (funciona em jogos)."""
        extra = ctypes.c_ulong(0)
        mi = MOUSEINPUT(dx, dy, 0, flags, 0, ctypes.pointer(extra))
        inp = INPUT(INPUT_MOUSE, mi)
        self.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
    
    def move_relative(self, dx, dy):
        """Move o mouse relativamente usando SendInput."""
        # Adicionar jitter humano
        if Config.HUMAN_JITTER > 0:
            dx += random.uniform(-Config.HUMAN_JITTER, Config.HUMAN_JITTER)
            dy += random.uniform(-Config.HUMAN_JITTER, Config.HUMAN_JITTER)
        
        # Acumular movimento fracionário
        self.accumulated_x += dx
        self.accumulated_y += dy
        
        # Só mover quando tiver pelo menos 1 pixel inteiro
        move_x = int(self.accumulated_x)
        move_y = int(self.accumulated_y)
        
        if move_x != 0 or move_y != 0:
            self.accumulated_x -= move_x
            self.accumulated_y -= move_y
            
            # Usar SendInput para input externo (funciona em jogos)
            self._send_input(move_x, move_y, MOUSEEVENTF_MOVE)
    
    def smooth_move_to_target(self, target_x, target_y, current_x, current_y):
        """
        Move suavemente em direção ao alvo com curva bezier.
        Retorna True se chegou perto o suficiente.
        """
        dx = target_x - current_x
        dy = target_y - current_y
        distance = math.sqrt(dx * dx + dy * dy)
        
        if distance < Config.TRIGGER_THRESHOLD:
            return True  # Já está no alvo
        
        # Calcular movimento suavizado
        speed_factor = min(1.0, distance / 100) * Config.AIM_SPEED
        
        # Aplicar suavização exponencial
        move_x = dx * Config.SMOOTHING * speed_factor
        move_y = dy * Config.SMOOTHING * speed_factor
        
        # Adicionar curva bezier para movimento mais natural
        if Config.CURVE_STRENGTH > 0 and distance > 50:
            curve = math.sin(time.time() * 10) * Config.CURVE_STRENGTH
            move_x += curve * (dy / distance) * 2
            move_y -= curve * (dx / distance) * 2
        
        # Micro-correções (pequenos ajustes humanos)
        if Config.MICRO_CORRECTIONS and random.random() < 0.1:
            move_x *= random.uniform(0.8, 1.2)
            move_y *= random.uniform(0.8, 1.2)
        
        self.move_relative(move_x, move_y)
        return False
    
    def click(self):
        """Executa um clique do mouse usando SendInput."""
        # Delay humanizado antes do clique
        delay = random.uniform(Config.TRIGGER_DELAY_MIN, Config.TRIGGER_DELAY_MAX)
        time.sleep(delay)
        
        # Mouse down
        self._send_input(0, 0, MOUSEEVENTF_LEFTDOWN)
        
        # Delay entre down e up (simula clique humano)
        time.sleep(random.uniform(0.02, 0.05))
        
        # Mouse up
        self._send_input(0, 0, MOUSEEVENTF_LEFTUP)
    
    def mouse_down(self):
        """Pressiona o botão esquerdo (para modo hold)."""
        self._send_input(0, 0, MOUSEEVENTF_LEFTDOWN)
    
    def mouse_up(self):
        """Libera o botão esquerdo (para modo hold)."""
        self._send_input(0, 0, MOUSEEVENTF_LEFTUP)
    
    def rapid_click(self, delay=None):
        """Clique rápido para modo rapid."""
        if delay is None:
            delay = Config.TRIGGER_RAPID_DELAY
        self._send_input(0, 0, MOUSEEVENTF_LEFTDOWN)
        time.sleep(delay / 2)
        self._send_input(0, 0, MOUSEEVENTF_LEFTUP)
    
    def is_key_pressed(self, vk_code):
        """Verifica se uma tecla está pressionada."""
        return self.user32.GetAsyncKeyState(vk_code) & 0x8000 != 0
