import time
import os
import cv2
import numpy as np
import pandas as pd
import torch
import torch.optim as optim
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
import scrapetube
import yt_dlp
from ultralytics import YOLO 
from config import *

print("[TRAINER] Carregando YOLO...")
try: yolo_model = YOLO("yolov8n.pt")
except: exit()

SKIP_FRAMES = 2
BATCH_SIZE = 32
EPOCHS = 5

def get_stream_url(video_id):
    """Pega URL direta para streaming (sem baixar arquivo)"""
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        'format': 'best[ext=mp4][height<=480]/best[height<=480]', # 480p é leve
        'quiet': True, 'no_warnings': True, 'ignoreerrors': True
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info and 'url' in info:
                return info['url']
    except: pass
    return None

def extract_smart_features(frame, prev_gray):
    # (Mesma função de antes)
    if frame is None or frame.size == 0: return None, 0,0,0,0
    
    small = cv2.resize(frame, (320, 240))
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    
    rot, fwd = 0.0, 0.0
    if prev_gray is not None:
        flow = cv2.calcOpticalFlowFarneback(prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        if flow.size > 0:
            rot = -np.mean(flow[..., 0])
            cx = flow.shape[1] // 2
            left = flow[..., :cx-20]
            right = flow[..., cx+20:]
            if left.size > 0 and right.size > 0:
                fwd = (np.mean(right) - np.mean(left))

    results = yolo_model(frame, verbose=False, classes=[0])
    
    enemy_x, enemy_y = 0.0, 0.0
    h, w, _ = frame.shape
    center_x, center_y = w // 2, h // 2
    closest_dist = 99999
    
    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            ecx, ecy = (x1+x2)/2, (y1+y2)/2
            dist = abs(ecx - center_x) + abs(ecy - center_y)
            if dist < closest_dist:
                closest_dist = dist
                enemy_x = (ecx - center_x) / (w/2)
                enemy_y = (ecy - center_y) / (h/2)

    vals = [rot, fwd, enemy_x, enemy_y]
    clean_vals = []
    for v in vals:
        if np.isnan(v) or np.isinf(v): clean_vals.append(0.0)
        else: clean_vals.append(float(v))
    
    clean_vals[0] = np.clip(clean_vals[0], -50, 50)
    clean_vals[1] = np.clip(clean_vals[1], -50, 50)

    return gray, clean_vals[0], clean_vals[1], clean_vals[2], clean_vals[3]

def train_model():
    # (Mesma função de treino)
    if not os.path.exists(DATASET_FILE): return
    try:
        try: df = pd.read_csv(DATASET_FILE).dropna().tail(3000)
        except: return
        if len(df) < 50: return

        X = torch.tensor(df[['rot', 'fwd', 'enemy_x', 'enemy_y']].values.astype(np.float32))
        y = torch.tensor(df[['rot', 'fwd']].values.astype(np.float32))

        dataset = TensorDataset(X, y)
        loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

        model = RobloBrain()
        if os.path.exists(MODEL_CURRENT):
            try: model.load_state_dict(torch.load(MODEL_CURRENT))
            except: pass
        
        optimizer = optim.Adam(model.parameters(), lr=0.001)
        criterion = nn.MSELoss()

        model.train()
        total_loss = 0
        for epoch in range(EPOCHS):
            for bx, by in loader:
                optimizer.zero_grad()
                bx = bx.unsqueeze(1)
                pred, _ = model(bx) 
                loss = criterion(pred, by)
                if torch.isnan(loss): continue
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                total_loss += loss.item()
            
        print(f"[TRAINER] Treinado. Loss: {total_loss:.4f}")
        torch.save(model.state_dict(), MODEL_NEW)
        if not os.path.exists(MODEL_CURRENT): torch.save(model.state_dict(), MODEL_CURRENT)
    except Exception as e: print(f"[ERRO TREINO] {e}")

def main():
    print(f"[TRAINER] Streaming: {CHANNEL_URL}")
    if not os.path.exists(DATASET_FILE):
        with open(DATASET_FILE, 'w') as f: f.write("video_id,rot,fwd,enemy_x,enemy_y\n")

    while True:
        try: videos = scrapetube.get_channel(channel_url=CHANNEL_URL, limit=3)
        except: time.sleep(10); continue
        
        for video in videos:
            vid_id = video['videoId']
            print(f"[TRAINER] Conectando ao vídeo {vid_id}...")
            
            stream_url = get_stream_url(vid_id)
            if not stream_url: 
                print("[TRAINER] Stream indisponível.")
                continue

            # Abre o stream direto
            cap = cv2.VideoCapture(stream_url)
            
            # --- PROTEÇÃO DE STREAM ---
            # Se o OpenCV falhar em abrir, tenta de novo
            if not cap.isOpened():
                print("[TRAINER] Falha ao abrir stream.")
                continue

            prev_gray = None
            new_data = []
            frame_idx = 0
            start_time = time.time()
            
            print("[TRAINER] Assistindo e aprendendo...")
            
            while True:
                # Timeout de 5 minutos por vídeo para rotacionar aprendizado
                if time.time() - start_time > 300: break

                ret, frame = cap.read()
                if not ret: 
                    # Se cair a conexão, sai do loop e vai pro próximo vídeo
                    break
                
                frame_idx += 1
                if frame_idx % (SKIP_FRAMES+1) != 0: continue
                
                # Extração segura
                gray, rot, fwd, ex, ey = extract_smart_features(frame, prev_gray)
                prev_gray = gray
                
                if gray is None: continue

                # Só salva se tiver ação (Otimização)
                has_action = (abs(rot) > 0.05) or (abs(ex) > 0.01)
                
                if has_action:
                    if not (np.isnan(rot) or np.isnan(ex)):
                        new_data.append(f"{vid_id},{rot:.4f},{fwd:.4f},{ex:.4f},{ey:.4f}\n")
                
                # Buffer de 500 frames
                if len(new_data) > 500:
                    print(f"[TRAINER] Salvando {len(new_data)} exemplos e treinando...")
                    try:
                        with open(DATASET_FILE, 'a') as f: f.writelines(new_data)
                    except: pass
                    new_data = []
                    train_model()

            cap.release()
            print("[TRAINER] Vídeo finalizado ou conexão caiu.")
            
        print("[TRAINER] Ciclo completo. Dormindo 30s...")
        time.sleep(30)

if __name__ == "__main__":
    main()
