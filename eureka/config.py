# ============================================
# CONFIGURAÇÕES DO SISTEMA DE DETECÇÃO
# ============================================

class Config:
    # --- MODELO ---
    MODEL_PATH = "best.pt"  # Caminho do modelo YOLO (.pt)
    CONFIDENCE_THRESHOLD = 0.35  # Confidence baixo para detectar mais (0.25 - 0.45 recomendado)
    
    # --- CAPTURA DE TELA ---
    CAPTURE_WIDTH = 640  # Largura da região de captura (centro da tela)
    CAPTURE_HEIGHT = 640  # Altura da região de captura (centro da tela)
    TARGET_FPS = 300  # FPS alvo para captura
    
    # --- AIMING ---
    AIM_SPEED = 1  # Velocidade do aim (0.1 = lento, 1.0 = rápido)
    SMOOTHING = 0.15  # Suavização do movimento (menor = mais suave)
    AIM_FOV = 300  # Field of View para aiming (pixels do centro)
    HEAD_OFFSET = 0.4  # Offset para mirar na cabeça (0.0 = centro, 0.3 = topo)
    
    # --- TRIGGERBOT ---
    TRIGGER_ENABLED = True  # Atirar automaticamente quando centralizado
    TRIGGER_THRESHOLD = 10  # Pixels de tolerância para considerar "no alvo"
    TRIGGER_DELAY_MIN = 0  # Delay mínimo antes de atirar (segundos)
    TRIGGER_DELAY_MAX = 0  # Delay máximo antes de atirar (segundos)
    TRIGGER_MODE = "rapid"  # Modos: "rapid", "single", "hold"
    TRIGGER_RAPID_DELAY = 0.05  # Delay entre cliques no modo rapid (segundos)
    
    # --- BYTETRACK ---
    ENABLE_BYTETRACK = True  # Usar ByteTrack para tracking melhorado
    TRACK_BUFFER = 30  # Frames para manter tracks perdidas
    TRACK_THRESH = 0.5  # Threshold de confiança para tracking
    MATCH_THRESH = 0.8  # Threshold de IoU para match de tracks
    
    # --- HUMANIZAÇÃO ---
    HUMAN_JITTER = 0  # Pixels de variação aleatória (simula tremida humana)
    CURVE_STRENGTH = 0  # Força da curva bezier no movimento
    MICRO_CORRECTIONS = True  # Ativar micro-correções humanas
    
    # --- TECLAS ---
    AIM_KEY = 0x02  # Botão direito do mouse (VK_RBUTTON)
    TRIGGER_KEY = 0x01  # Botão esquerdo do mouse (VK_LBUTTON)
    TOGGLE_KEY = 0x78  # F9 para toggle on/off
    EXIT_KEY = 0x23  # End para sair
    
    # --- MODO TESTE ---
    TEST_MODE = True  # Modo de teste SEM modelo (usa cores para detectar)
    TEST_COLOR_LOWER = (0, 100, 100)  # HSV mínimo (vermelho/roxo por padrão)
    TEST_COLOR_UPPER = (10, 255, 255)  # HSV máximo
    SHOW_OVERLAY = True  # Mostrar overlay de debug (DESATIVADO para não capturar a si mesmo)
    
    # --- CLASSES DO MODELO ---
    TARGET_CLASSES = [1]  # Classes para detectar (0 = pessoa normalmente)
