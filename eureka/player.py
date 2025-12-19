import torch
import cv2
import mss
import numpy as np
import pydirectinput
import time
import os
import shutil
from ultralytics import YOLO
from config import *

# Carrega YOLO para visão do player
yolo_player = YOLO("yolov8n.pt")
SENSITIVITY = 150

def get_smart_inputs(frame, prev_gray):
    # (Mesma lógica do trainer, otimizada p/ tempo real)
    if frame is None: return None, 0,0,0,0
    
    small = cv2.resize(frame, (320, 240))
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    
    rot, fwd = 0.0, 0.0
    if prev_gray is not None:
        flow = cv2.calcOpticalFlowFarneback(prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        if flow.size > 0:
            rot = -np.mean(flow[..., 0])
            cx = flow.shape[1] // 2
            fwd = (np.mean(flow[..., cx+20:]) - np.mean(flow[..., :cx-20]))

    # Detecta inimigo (apenas na área central p/ performance)
    h, w, _ = frame.shape
    center_crop = frame[h//4:3*h//4, w//4:3*w//4] # Crop central
    results = yolo_player(center_crop, verbose=False, classes=[0])
    
    enemy_x, enemy_y = 0.0, 0.0
    closest = 9999
    cw, ch = w//2, h//2 # Dimensões do crop
    
    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            ecx, ecy = (x1+x2)/2, (y1+y2)/2
            # Coordenadas relativas ao crop
            dist = abs(ecx - cw/2) + abs(ecy - ch/2)
            if dist < closest:
                closest = dist
                enemy_x = (ecx - cw/2) / (cw/2)
                enemy_y = (ecy - ch/2) / (ch/2)

    return gray, rot, fwd, enemy_x, enemy_y

def play():
    print("[PLAYER] Iniciando V2 Inteligente...")
    brain = RobloBrain()
    
    while not os.path.exists(MODEL_CURRENT): time.sleep(5)
    
    try: brain.load_state_dict(torch.load(MODEL_CURRENT))
    except: pass
    brain.eval()
    
    sct = mss.mss()
    monitor = {"top": 0, "left": 0, "width": 1920, "height": 1080}
    prev_gray = None
    hidden = None # Memória da LSTM
    
    last_update = time.time()

    while True:
        # Hot Swap
        if time.time() - last_update > 10 and os.path.exists(MODEL_NEW):
            try:
                brain.load_state_dict(torch.load(MODEL_NEW))
                shutil.copy(MODEL_NEW, MODEL_CURRENT)
                os.remove(MODEL_NEW)
                print("[UPGRADE] Cérebro atualizado!")
            except: pass
            last_update = time.time()

        # Input
        img = np.array(sct.grab(monitor))
        frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        
        gray, rot, fwd, ex, ey = get_smart_inputs(frame, prev_gray)
        prev_gray = gray
        if gray is None: continue

        # Inferência
        inputs = torch.tensor([rot, fwd, ex, ey], dtype=torch.float32)
        with torch.no_grad():
            # Passa a memória (hidden) para o próximo frame
            action, hidden = brain(inputs, hidden)
            action = action.numpy()[0] # Tira do batch

        # Ação
        move_x = int(action[0] * SENSITIVITY)
        
        # Lógica Híbrida: Se a rede detectar inimigo (ex != 0), ajuda na mira
        if abs(ex) > 0.05:
            # Mistura a decisão da IA com o "instinto" do YOLO
            move_x += int(ex * 50) 
            print(f"\r[ALVO] Inimigo detectado! Ajustando mira...", end="")

        pydirectinput.moveRel(move_x, 0, relative=True)
        
        if action[1] > 0.8: pydirectinput.keyDown('w')
        else: pydirectinput.keyUp('w')

if __name__ == "__main__":
    play()
