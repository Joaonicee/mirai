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
from overlay import Overlay

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
    overlay = Overlay()
    selector = TargetSelector(
        screen.screen_width,
        screen.screen_height,
        Config.CAPTURE_WIDTH,
        Config.CAPTURE_HEIGHT
    )
    
    print(f"[*] Resolução: {screen.screen_width}x{screen.screen_height}")
    print(f"[*] Região de captura: {Config.CAPTURE_WIDTH}x{Config.CAPTURE_HEIGHT}")
    print(f"[*] Modo: {'TESTE (cor)' if Config.TEST_MODE else 'YOLO'}")
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
    last_trigger_time = 0
    
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
            
            # Verificar se aim está ativo (botão direito)
            aim_active = enabled and mouse.is_key_pressed(Config.AIM_KEY)
            
            # Selecionar melhor alvo
            target = selector.select_best_target(detections) if aim_active else None
            
            # Mover mouse para alvo
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
                
                # Triggerbot - atirar quando no alvo
                if on_target and Config.TRIGGER_ENABLED:
                    if current_time - last_trigger_time > 0.15:  # Cooldown
                        mouse.click()
                        last_trigger_time = current_time
            
            # Atualizar overlay
            overlay.draw(frame, detections, target, fps, aim_active)
            
            # Processar teclas do OpenCV
            if not overlay.process_keys():
                break
            
            # Limitar FPS se necessário
            frame_time = time.time() - current_time
            target_frame_time = 1.0 / Config.TARGET_FPS
            if frame_time < target_frame_time:
                time.sleep(target_frame_time - frame_time)
    
    except KeyboardInterrupt:
        print("\n[!] Interrompido pelo usuário")
    
    finally:
        # Cleanup
        screen.close()
        overlay.close()
        print("[+] Sistema encerrado.")

if __name__ == "__main__":
    main()
