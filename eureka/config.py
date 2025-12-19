# ============================================
# CONFIGURAÇÕES DO SISTEMA DE DETECÇÃO
# ============================================

class Config:
    # --- MODELO ---
    MODEL_PATH = "model.pt"  # Caminho do modelo YOLO (.pt)
    CONFIDENCE_THRESHOLD = 0.35  # Confidence baixo para detectar mais (0.25 - 0.45 recomendado)
    
    # --- CAPTURA DE TELA ---
    CAPTURE_WIDTH = 640  # Largura da região de captura (centro da tela)
    CAPTURE_HEIGHT = 640  # Altura da região de captura (centro da tela)
    TARGET_FPS = 60  # FPS alvo para captura
    
    # --- AIMING ---
    AIM_SPEED = 1  # Velocidade do aim (0.1 = lento, 1.0 = rápido)
    SMOOTHING = 0.15  # Suavização do movimento (menor = mais suave)
    AIM_FOV = 300  # Field of View para aiming (pixels do centro)
    HEAD_OFFSET = 0.1  # Offset para mirar na cabeça (0.0 = centro, 0.3 = topo)
    
    # --- TRIGGERBOT ---
    TRIGGER_ENABLED = True  # Atirar automaticamente quando centralizado
    TRIGGER_THRESHOLD = 15  # Pixels de tolerância para considerar "no alvo"
    TRIGGER_DELAY_MIN = 0.02  # Delay mínimo antes de atirar (segundos)
    TRIGGER_DELAY_MAX = 0.08  # Delay máximo antes de atirar (segundos)
    
    # --- HUMANIZAÇÃO ---
    HUMAN_JITTER = 2  # Pixels de variação aleatória (simula tremida humana)
    CURVE_STRENGTH = 0.3  # Força da curva bezier no movimento
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
    SHOW_OVERLAY = False  # Mostrar overlay de debug (DESATIVADO para não capturar a si mesmo)
    
    # --- CLASSES DO MODELO ---
    TARGET_CLASSES = [0]  # Classes para detectar (0 = pessoa normalmente)
