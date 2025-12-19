"""
BOT RIVALS v18.5: best.pt + conf 0.10 + Aimbot + Anti-Recoil
                 + Movimento (frame diff)
                 + Parede por bbox (proximidade)
                 + Scan com easing (SCAN_BASE_SPEED=10, POW=0.5)
                 + Lock em um alvo até ele sumir (forma/posição)
                 + Movimento independente do alvo
                 + Tracking inteligente (interpolação + smoothing adaptativo)
                 + FIX: Auto-shoot funcional
"""

import math
import time
import ctypes
from ctypes import wintypes

import cv2
import numpy as np
import mss
import torch
import pydirectinput
from ultralytics import YOLO

# ===================== CONFIG GERAL =====================
YOLO_MODEL_PATH = "best.pt"
CONFIDENCE = 0.10

CAPTURE_WIDTH = 320
CAPTURE_HEIGHT = 160
YOLO_IMG_SZ = 320

ZONE_WIDTH = CAPTURE_WIDTH // 3

FORWARD_KEY = "w"
LEFT_KEY = "a"
RIGHT_KEY = "d"
SPRINT_KEY = "shift"
JUMP_KEY = "space"
SLIDE_KEY = "ctrl"
DASH_KEY = "f"

SPRINT_THRESHOLD = 2

BASE_SENSITIVITY = 0.65
BASE_SMOOTHING = 0.55
MAX_SMOOTHING = 0.9
MAX_MOVEMENT_PER_FRAME = 10
AIM_LOCK_RADIUS = 15  # aumentado pra facilitar o lock
AUTO_SHOOT = True

ADAPT_RATE = 0.002
TARGET_LOCK_GOAL = 0.7

RECOIL_FACTOR = 0.9

# Parede por bbox
NEAR_WALL_AREA_FRAC = 0.32
NEAR_WALL_CENTER_RADIUS = 50
NEAR_WALL_COOLDOWN = 0.15

# Scan forte ao perder alvo
SCAN_LOST_PIXELS_BASE = 700
SCAN_LOST_PIXELS_VAR  = 250

# Scan idle após tempo sem alvo
SCAN_NO_TARGET_TIME = 2.0
SCAN_IDLE_PIXELS_BASE = 600
SCAN_IDLE_PIXELS_VAR  = 200

# Controlador scan
SCAN_BASE_SPEED = 10.0
SCAN_EASING_POW = 0.5

# Lock de alvo
LOCK_MAX_DIST_PIXELS = 60
LOCK_MAX_SIZE_RATIO  = 1.6

# ===================== WIN32 MOUSE =====================
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
INPUT_MOUSE = 0

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG), ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]
    _anonymous_ = ("_input",)
    _fields_ = [("type", wintypes.DWORD), ("_input", _INPUT)]

SendInput = ctypes.windll.user32.SendInput

def send_mouse(flags, dx=0, dy=0):
    extra = ctypes.c_ulong(0)
    ii = INPUT()
    ii.type = INPUT_MOUSE
    ii.mi = MOUSEINPUT(int(dx), int(dy), 0, flags, 0, ctypes.pointer(extra))
    SendInput(1, ctypes.pointer(ii), ctypes.sizeof(ii))

def move_mouse(dx, dy):
    send_mouse(MOUSEEVENTF_MOVE, dx, dy)

shooting = False
def mouse_left_down():
    global shooting
    if not shooting:
        send_mouse(MOUSEEVENTF_LEFTDOWN)
        shooting = True

def mouse_left_up():
    global shooting
    if shooting:
        send_mouse(MOUSEEVENTF_LEFTUP)
        shooting = False

def mouse_right_click():
    send_mouse(MOUSEEVENTF_RIGHTDOWN)
    time.sleep(0.01)
    send_mouse(MOUSEEVENTF_RIGHTUP)

# ===================== INPUT TECLADO =====================
def key_down(k): pydirectinput.keyDown(k)
def key_up(k):   pydirectinput.keyUp(k)

pressed_keys = set()

def press_key(k):
    if k not in pressed_keys:
        key_down(k)
        pressed_keys.add(k)

def release_key(k):
    if k in pressed_keys:
        key_up(k)
        pressed_keys.remove(k)

def release_all_movement():
    for k in list(pressed_keys):
        release_key(k)

# ===================== INIT YOLO =====================
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"🤖 BOT RIVALS v18.5 - Device: {device}")
print(f"🎯 Modelo: {YOLO_MODEL_PATH} | conf={CONFIDENCE}")

yolo_model = YOLO(YOLO_MODEL_PATH)
yolo_model.to(device)
if device == "cuda":
    yolo_model.fuse()

# ===================== CAPTURA =====================
sct = mss.mss()
monitor = sct.monitors[1]
screen_center_x = monitor["width"] // 2
screen_center_y = monitor["height"] // 2

capture_area = {
    "top":  screen_center_y - CAPTURE_HEIGHT // 2,
    "left": screen_center_x - CAPTURE_WIDTH  // 2,
    "width":  CAPTURE_WIDTH,
    "height": CAPTURE_HEIGHT,
}

def grab_frame():
    img = np.array(sct.grab(capture_area))
    return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

# ===================== ESTADO GLOBAL =====================
last_dx = 0.0
last_dy = 0.0

current_sensitivity = BASE_SENSITIVITY
current_smoothing = BASE_SMOOTHING

lock_good_frames = 0
lock_total_frames = 0

last_target_pos = None
prev_gray = None

scan_remaining = 0.0
scan_dir = 1
no_target_since = time.time()
had_target_prev = False
last_frame_time = time.time()
last_near_wall_time = 0.0

current_target_box = None

# ===================== YOLO AUX =====================
def analyze_zones(results):
    left_count = center_count = right_count = 0
    for r in results:
        if r.boxes is not None:
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                bx = (x1 + x2) / 2
                if bx < ZONE_WIDTH:
                    left_count += 1
                elif bx < 2 * ZONE_WIDTH:
                    center_count += 1
                else:
                    right_count += 1
    return left_count, center_count, right_count

def get_motion_map(gray, prev_gray_local):
    if prev_gray_local is None or prev_gray_local.shape != gray.shape:
        return np.zeros_like(gray, dtype=np.float32), 0.0
    diff = cv2.absdiff(gray, prev_gray_local)
    _, diff_bin = cv2.threshold(diff, 12, 255, 255, cv2.THRESH_BINARY)
    blurred = cv2.GaussianBlur(diff_bin, (7, 7), 0)
    norm = blurred.astype(np.float32) / 255.0
    global_motion = float(np.mean(norm))
    return norm, global_motion

def extract_boxes(results):
    boxes = []
    for r in results:
        if r.boxes is None:
            continue
        for b in r.boxes:
            x1, y1, x2, y2 = b.xyxy[0].cpu().numpy()
            conf = float(b.conf.cpu().item())
            w = max(x2 - x1, 0.0)
            h = max(y2 - y1, 0.0)
            cx = (x1 + x2) / 2
            cy = y1 + (y2 - y1) * 0.25
            boxes.append({"cx": cx, "cy": cy, "w": w, "h": h, "conf": conf})
    return boxes

def choose_best_box(boxes, motion_map):
    if not boxes:
        return None
    cx_s, cy_s = CAPTURE_WIDTH // 2, CAPTURE_HEIGHT // 2
    best_score = float("inf")
    best_box = None
    for box in boxes:
        cx, cy, w, h, conf = box["cx"], box["cy"], box["w"], box["h"], box["conf"]
        dist = math.hypot(cx - cx_s, cy - cy_s)
        x1i = max(int(cx - w / 2), 0)
        x2i = min(int(cx + w / 2), CAPTURE_WIDTH - 1)
        y1i = max(int(cy - h / 2), 0)
        y2i = min(int(cy + h / 2), CAPTURE_HEIGHT - 1)
        if x2i <= x1i or y2i <= y1i:
            motion_mean = 0.0
        else:
            motion_roi = motion_map[y1i:y2i, x1i:x2i]
            motion_mean = float(np.mean(motion_roi))
        score = dist - motion_mean * 40.0 - conf * 20.0
        if score < best_score:
            best_score = score
            best_box = box
    return best_box

def match_lock_box(prev_box, boxes):
    if prev_box is None or not boxes:
        return None
    best = None
    best_d = float("inf")
    pcx, pcy, pw, ph = prev_box["cx"], prev_box["cy"], prev_box["w"], prev_box["h"]
    for b in boxes:
        cx, cy, w, h = b["cx"], b["cy"], b["w"], b["h"]
        d = math.hypot(cx - pcx, cy - pcy)
        if d > LOCK_MAX_DIST_PIXELS:
            continue
        ratio_w = max(pw, 1.0) / max(w, 1.0)
        ratio_h = max(ph, 1.0) / max(h, 1.0)
        if ratio_w > LOCK_MAX_SIZE_RATIO or ratio_w < 1.0 / LOCK_MAX_SIZE_RATIO:
            continue
        if ratio_h > LOCK_MAX_SIZE_RATIO or ratio_h < 1.0 / LOCK_MAX_SIZE_RATIO:
            continue
        if d < best_d:
            best_d = d
            best = b
    return best

# ===================== AIM (TRACKING INTELIGENTE + FIX SHOOT) =====================
def clamp_len(dx, dy, max_len):
    mag = math.sqrt(dx * dx + dy * dy)
    if mag > max_len and mag > 0:
        return dx * max_len / mag, dy * max_len / mag
    return dx, dy

def aim_and_shoot_from_box(box):
    global last_dx, last_dy, lock_good_frames, lock_total_frames, last_target_pos
    global current_sensitivity, current_smoothing
    
    cx_t, cy_t = box["cx"], box["cy"]
    cx_s, cy_s = CAPTURE_WIDTH // 2, CAPTURE_HEIGHT // 2
    
    # erro em pixels na tela (antes de aplicar sens)
    error_x = cx_t - cx_s
    error_y = cy_t - cy_s
    dist = math.hypot(error_x, error_y)
    
    # interpolação temporal da posição do alvo (mais suave)
    if last_target_pos is not None:
        ltx, lty = last_target_pos
        cx_t = ltx + (cx_t - ltx) * 0.6
        cy_t = lty + (cy_t - lty) * 0.6
        error_x = cx_t - cx_s
        error_y = cy_t - cy_s
    last_target_pos = (cx_t, cy_t)
    
    # calcula movimento necessário
    raw_dx = error_x * current_sensitivity
    raw_dy = error_y * current_sensitivity

    # reduz recoil vertical
    if raw_dy < 0:
        raw_dy *= (1.0 - RECOIL_FACTOR)
    
    # smoothing adaptativo: mais suave quando longe, mais direto quando perto
    dist_norm = min(dist / (CAPTURE_WIDTH / 2), 1.0)
    smooth = current_smoothing + (MAX_SMOOTHING - current_smoothing) * dist_norm
    smooth = min(smooth, MAX_SMOOTHING)
    
    # aplica interpolação suave baseada no movimento anterior
    delta_x = raw_dx - last_dx
    delta_y = raw_dy - last_dy
    delta_x, delta_y = clamp_len(delta_x, delta_y, MAX_MOVEMENT_PER_FRAME)
    
    alpha = 1.0 - smooth
    final_dx = last_dx + delta_x * alpha
    final_dy = last_dy + delta_y * alpha
    
    # deadzone pra evitar micro-jitter
    if abs(final_dx) < 0.25:
        final_dx = 0.0
    if abs(final_dy) < 0.25:
        final_dy = 0.0
    
    if abs(final_dx) > 0.0 or abs(final_dy) > 0.0:
        move_mouse(final_dx, final_dy)
    
    last_dx, last_dy = final_dx, final_dy
    
    # CORRIGIDO: checa o erro em pixels na tela (antes da sens), não o movimento final
    lock_total_frames += 1
    if abs(error_x) < AIM_LOCK_RADIUS and abs(error_y) < AIM_LOCK_RADIUS:
        lock_good_frames += 1
        if AUTO_SHOOT:
            mouse_left_down()
    else:
        mouse_left_up()

def adapt_control():
    global lock_good_frames, lock_total_frames
    global current_sensitivity, current_smoothing
    if lock_total_frames < 30:
        return
    ratio = lock_good_frames / max(lock_total_frames, 1)
    error = TARGET_LOCK_GOAL - ratio
    current_sensitivity += ADAPT_RATE * error
    current_smoothing   -= ADAPT_RATE * error
    current_sensitivity = float(np.clip(current_sensitivity, 0.45, 0.85))
    current_smoothing   = float(np.clip(current_smoothing, 0.4, 0.8))
    lock_good_frames = 0
    lock_total_frames = 0

# ===================== SCAN / EASING =====================
def start_scan(total_pixels):
    global scan_remaining
    scan_remaining = float(total_pixels)

def apply_scan(dt):
    global scan_remaining
    if abs(scan_remaining) < 0.5:
        scan_remaining = 0.0
        return
    mag = abs(scan_remaining)
    speed = SCAN_BASE_SPEED * (mag ** SCAN_EASING_POW) / (100.0 ** SCAN_EASING_POW)
    step = speed * dt
    step = min(step, mag)
    direction = 1 if scan_remaining > 0 else -1
    move = step * direction
    move_mouse(move, 0)
    scan_remaining -= move

def trigger_scan_lost():
    global scan_dir
    total = SCAN_LOST_PIXELS_BASE + (np.random.rand() * 2 - 1) * SCAN_LOST_PIXELS_VAR
    scan_dir = 1 if np.random.rand() < 0.5 else -1
    start_scan(total * scan_dir)

def trigger_scan_idle():
    global scan_dir
    total = SCAN_IDLE_PIXELS_BASE + (np.random.rand() * 2 - 1) * SCAN_IDLE_PIXELS_VAR
    scan_dir = 1 if np.random.rand() < 0.5 else -1
    start_scan(total * scan_dir)

def cancel_scan():
    global scan_remaining
    scan_remaining = 0.0

# ===================== PAREDE POR BBOX =====================
def detect_wall_by_bbox(results, now):
    global last_near_wall_time
    if now - last_near_wall_time < NEAR_WALL_COOLDOWN:
        return False
    if results is None or len(results) == 0:
        return False
    cx_s, cy_s = CAPTURE_WIDTH // 2, CAPTURE_HEIGHT // 2
    screen_area = CAPTURE_WIDTH * CAPTURE_HEIGHT
    triggered = False
    for r in results:
        if r.boxes is None:
            continue
        for b in r.boxes:
            x1, y1, x2, y2 = b.xyxy[0].cpu().numpy()
            w = max(x2 - x1, 0.0)
            h = max(y2 - y1, 0.0)
            area = w * h
            area_frac = area / screen_area
            if area_frac < NEAR_WALL_AREA_FRAC:
                continue
            bx = (x1 + x2) / 2
            by = (y1 + y2) / 2
            dist_center = math.hypot(bx - cx_s, by - cy_s)
            if dist_center > NEAR_WALL_CENTER_RADIUS:
                continue
            triggered = True
            break
        if triggered:
            break
    if triggered:
        last_near_wall_time = now
        total = SCAN_LOST_PIXELS_BASE + (np.random.rand() * 2 - 1) * SCAN_LOST_PIXELS_VAR
        direction = 1 if (int(now * 1000) % 2 == 0) else -1
        start_scan(total * direction)
        return True
    return False

# ===================== SCAN STATE =====================
def update_scan_state(has_target, now):
    global no_target_since, had_target_prev
    if has_target:
        cancel_scan()
        no_target_since = now
        had_target_prev = True
        return
    if had_target_prev and not has_target:
        trigger_scan_lost()
        had_target_prev = False
        no_target_since = now
        return
    if now - no_target_since > SCAN_NO_TARGET_TIME and scan_remaining == 0.0:
        trigger_scan_idle()
        no_target_since = now

# ===================== MOVIMENTO (INDEPENDENTE DO ALVO) =====================
def decide_movement(left_count, center_count, right_count, now, has_target, results):
    total = left_count + center_count + right_count
    hit_wall = detect_wall_by_bbox(results, now)
    for k in [FORWARD_KEY, LEFT_KEY, RIGHT_KEY, SPRINT_KEY]:
        release_key(k)
    if hit_wall:
        if np.random.rand() < 0.5:
            press_key(LEFT_KEY)
        else:
            press_key(RIGHT_KEY)
        return "wall_bbox"
    press_key(FORWARD_KEY)
    if total >= SPRINT_THRESHOLD and np.random.rand() < 0.5:
        press_key(SPRINT_KEY)
    r = np.random.rand()
    if r < 0.33:
        press_key(LEFT_KEY)
    elif r < 0.66:
        press_key(RIGHT_KEY)
    if total == 0 and not has_target:
        if np.random.rand() < 0.01:
            pydirectinput.press(JUMP_KEY)
        return "search"
    max_count = max(left_count, center_count, right_count)
    if left_count == max_count and left_count > 0:
        return "left_dense"
    if right_count == max_count and right_count > 0:
        return "right_dense"
    return "forward"

# ===================== LOOP PRINCIPAL =====================
if __name__ == "__main__":
    print("\n" + "="*70)
    print("🤖 BOT RIVALS v18.5 - best.pt (conf 0.10 + lock + tracking inteligente + FIX shoot)")
    print("="*70)
    print(f"  📷 Captura: {CAPTURE_WIDTH}x{CAPTURE_HEIGHT}")
    print(f"  🎯 Zonas: {ZONE_WIDTH}px | {ZONE_WIDTH}px | {ZONE_WIDTH}px")
    print(f"  💻 Device: {device}")
    print("="*70 + "\n")
    
    bot_active = True
    frame_counter = 0
    t0 = time.time()
    last_adapt_time = time.time()
    
    prev_gray = None
    no_target_since = time.time()
    had_target_prev = False
    last_frame_time = time.time()
    current_target_box = None
    
    try:
        while bot_active:
            now = time.time()
            dt = now - last_frame_time
            if dt <= 0:
                dt = 1 / 144.0
            last_frame_time = now
            
            frame = grab_frame()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            motion_map, _ = get_motion_map(gray, prev_gray)
            prev_gray = gray.copy()
            
            apply_scan(dt)
            
            if device == "cuda":
                results = yolo_model(
                    frame, verbose=False, conf=CONFIDENCE, imgsz=YOLO_IMG_SZ, half=True
                )
            else:
                results = yolo_model(
                    frame, verbose=False, conf=CONFIDENCE, imgsz=YOLO_IMG_SZ
                )
            
            boxes = extract_boxes(results)
            left_c, center_c, right_c = analyze_zones(results)
            
            if current_target_box is None:
                current_target_box = choose_best_box(boxes, motion_map)
            else:
                matched = match_lock_box(current_target_box, boxes)
                if matched is not None:
                    current_target_box = matched
                else:
                    current_target_box = None
            
            has_target = current_target_box is not None
            if has_target:
                aim_and_shoot_from_box(current_target_box)
            else:
                mouse_left_up()
            
            update_scan_state(has_target, now)
            
            strategy = decide_movement(left_c, center_c, right_c, now, has_target, results)
            
            if now - last_adapt_time > 1.0:
                adapt_control()
                last_adapt_time = now
            
            frame_counter += 1
            if frame_counter % 60 == 0:
                t1 = time.time()
                fps = 60 / (t1 - t0)
                total = left_c + center_c + right_c
                dist_str = "None"
                if current_target_box is not None:
                    cx_t, cy_t = current_target_box["cx"], current_target_box["cy"]
                    cx_s, cy_s = CAPTURE_WIDTH // 2, CAPTURE_HEIGHT // 2
                    dist_str = f"{math.hypot(cx_t - cx_s, cy_t - cy_s):.1f}"
                print(
                    f"[{total}] L:{left_c} C:{center_c} R:{right_c} | "
                    f"{strategy} | LOCK:{has_target} | SCAN_REMAIN:{scan_remaining:.1f} | "
                    f"FPS:{fps:.0f} | sens={current_sensitivity:.3f} "
                    f"smooth={current_smoothing:.3f} | dist={dist_str}"
                )
                t0 = t1
    
    except KeyboardInterrupt:
        print("\n🛑 Parando...")
        bot_active = False
        release_all_movement()
        mouse_left_up()
        print("✅ Finalizado!")
    
    finally:
        release_all_movement()
        mouse_left_up()
