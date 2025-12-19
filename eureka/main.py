# ============================================
# EUREKA - Sistema de Detecção e Aiming
# ============================================
# 
# CONTROLES:
#   Botão Direito: Ativar aim assist
#   F9: Toggle on/off
#   End: Sair do programa
#   Q/ESC: Fechar overlay
#
# MODOS DE TRIGGERBOT:
#   single: Um clique quando no alvo
#   rapid: Cliques rápidos enquanto no alvo
#   hold: Segura o botão enquanto no alvo
#
# Para testar SEM modelo:
#   1. Defina TEST_MODE = True no config.py
#   2. Abra algo com a cor definida em TEST_COLOR_*
#   3. Segure botão direito para ativar
#
# Para usar COM modelo:
#   1. Coloque seu modelo .pt na pasta
#   2. Defina MODEL_PATH no config.py
#   3. Defina TEST_MODE = False
#   4. Ajuste CONFIDENCE_THRESHOLD conforme necessário
#
# ============================================

import time
import sys

from config import Config
from screen_capture import ScreenCapture
from mouse_controller import MouseController
from detector import get_detector
from target_selector import TargetSelector
from byte_tracker import ByteTrackWrapper
from transparent_overlay import get_overlay, OpenCVOverlay


class TriggerBot:
    """Gerencia os modos de disparo do triggerbot."""
    
    def __init__(self, mouse):
        self.mouse = mouse
        self.mode = Config.TRIGGER_MODE
        self.is_holding = False
        self.last_rapid_time = 0
        self.last_single_shot = False  # Para evitar múltiplos disparos no modo single
    
    def update(self, on_target, current_time):
        """
        Atualiza o estado do triggerbot.
        
        Args:
            on_target: True se o cursor está sobre o alvo
            current_time: Tempo atual
        """
        if not Config.TRIGGER_ENABLED:
            return
        
        if on_target:
            if self.mode == "hold":
                # Modo hold: segura o botão enquanto no alvo
                if not self.is_holding:
                    self.mouse.mouse_down()
                    self.is_holding = True
            
            elif self.mode == "rapid":
                # Modo rapid: cliques rápidos
                if current_time - self.last_rapid_time >= Config.TRIGGER_RAPID_DELAY:
                    self.mouse.rapid_click()
                    self.last_rapid_time = current_time
            
            elif self.mode == "single":
                # Modo single: um clique quando entra no alvo
                if not self.last_single_shot:
                    self.mouse.click()
                    self.last_single_shot = True
        else:
            # Fora do alvo
            if self.mode == "hold" and self.is_holding:
                self.mouse.mouse_up()
                self.is_holding = False
            
            # Reset para permitir novo single shot
            self.last_single_shot = False
    
    def cleanup(self):
        """Limpa estado ao sair."""
        if self.is_holding:
            self.mouse.mouse_up()
            self.is_holding = False


def main():
    print("=" * 50)
    print("       EUREKA - Detection & Aiming System")
    print("=" * 50)
    print()
    print("[*] Inicializando componentes...")
    
    # Inicializar componentes
    screen = ScreenCapture()
    mouse = MouseController()
    detector = get_detector()
    selector = TargetSelector(
        screen.screen_width,
        screen.screen_height,
        Config.CAPTURE_WIDTH,
        Config.CAPTURE_HEIGHT
    )
    
    # ByteTrack para tracking melhorado
    tracker = ByteTrackWrapper(frame_rate=Config.TARGET_FPS)
    
    # Overlay (transparente ou OpenCV)
    overlay = get_overlay()
    
    # TriggerBot com modos
    triggerbot = TriggerBot(mouse)
    
    print(f"[*] Resolução: {screen.screen_width}x{screen.screen_height}")
    print(f"[*] Região de captura: {Config.CAPTURE_WIDTH}x{Config.CAPTURE_HEIGHT}")
    print(f"[*] Modo: {'TESTE (cor)' if Config.TEST_MODE else 'YOLO'}")
    print(f"[*] Triggerbot: {Config.TRIGGER_MODE.upper()}")
    print(f"[*] ByteTrack: {'Ativo' if Config.ENABLE_BYTETRACK else 'Desativado'}")
    print(f"[*] Overlay: {'Ativo' if Config.SHOW_OVERLAY else 'Desativado'}")
    print()
    print("[!] Controles:")
    print("    Botão Direito: Ativar aim")
    print("    F9: Toggle on/off")
    print("    End: Sair")
    print()
    
    # Estado
    enabled = True
    last_time = time.time()
    fps = 0
    fps_counter = 0
    fps_timer = time.time()
    current_track_id = -1  # ID do track atual para locking
    
    print("[+] Sistema ativo! Segure botão direito para mirar.")
    print()
    
    try:
        while True:
            current_time = time.time()
            
            # Calcular FPS
            fps_counter += 1
            if current_time - fps_timer >= 1.0:
                fps = fps_counter
                fps_counter = 0
                fps_timer = current_time
            
            # Checar teclas de controle
            if mouse.is_key_pressed(Config.EXIT_KEY):  # End
                print("[!] Saindo...")
                break
            
            if mouse.is_key_pressed(Config.TOGGLE_KEY):  # F9
                enabled = not enabled
                print(f"[*] Sistema {'ATIVADO' if enabled else 'DESATIVADO'}")
                time.sleep(0.3)  # Debounce
            
            # Capturar frame
            frame = screen.grab_frame()
            
            # Detectar alvos
            detections = detector.detect(frame)
            
            # Aplicar ByteTrack para tracking
            tracked_detections = tracker.update(
                detections,
                img_info=[Config.CAPTURE_HEIGHT, Config.CAPTURE_WIDTH],
                img_size=[Config.CAPTURE_HEIGHT, Config.CAPTURE_WIDTH]
            )
            
            # Verificar se aim está ativo (botão direito)
            aim_active = enabled and mouse.is_key_pressed(Config.AIM_KEY)
            
            # Selecionar alvo (preferir manter o mesmo track)
            target = None
            if aim_active and tracked_detections:
                # Tentar manter o mesmo track
                if current_track_id >= 0:
                    target = tracker.get_track_by_id(current_track_id)
                
                # Se perdeu o track, selecionar novo
                if target is None:
                    # Converter tracked para format esperado pelo selector
                    target = selector.select_best_target(tracked_detections)
                    if target:
                        current_track_id = target.track_id if hasattr(target, 'track_id') else -1
            else:
                current_track_id = -1
            
            # Mover mouse para alvo
            on_target = False
            if target and aim_active:
                dx, dy = selector.get_aim_offset(target)
                mouse_x, mouse_y = mouse.get_position()
                
                # Converter offset da região para posição absoluta
                target_screen_x = mouse_x + dx
                target_screen_y = mouse_y + dy
                
                # Mover suavemente
                on_target = mouse.smooth_move_to_target(
                    target_screen_x, target_screen_y,
                    mouse_x, mouse_y
                )
            
            # Triggerbot
            if aim_active:
                triggerbot.update(on_target, current_time)
            else:
                triggerbot.update(False, current_time)  # Reset quando não está mirando
            
            # Atualizar overlay
            if overlay:
                if isinstance(overlay, OpenCVOverlay):
                    overlay.update(frame, tracked_detections, target, fps)
                    if not overlay.process_keys():
                        break
                else:
                    overlay.update(tracked_detections, target)
            
            # Limitar FPS se necessário
            frame_time = time.time() - current_time
            target_frame_time = 1.0 / Config.TARGET_FPS
            if frame_time < target_frame_time:
                time.sleep(target_frame_time - frame_time)
    
    except KeyboardInterrupt:
        print("\n[!] Interrompido pelo usuário")
    
    finally:
        # Cleanup
        triggerbot.cleanup()
        screen.close()
        if overlay:
            overlay.close()
        print("[+] Sistema encerrado.")


if __name__ == "__main__":
    main()
