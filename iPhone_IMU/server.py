# pip install elevenlabs pyautogui sounddevice scipy numpy python-dotenv pyopenssl serial flask

import asyncio
import websockets
import pyautogui
import json
import ssl
import os
import sys
import threading 

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from voice_control import voice_controller

import esp_serial

PHONE_PORT = 8765

config = {
    "threshold": 12,
    "keyMap": {"up": "w", "down": "s", "left": "a", "right": "d"},
    "esp_key": "c",
    "esp_threshold": 10,
    "actionMap": {
        "jump":  "space",
        "go":    "enter",
        "run":   "shift",
        "click": "click",
        "sensor": "click",
    },
}

COMMAND_MAP = {
    # Movement
    # "move forward":    ("w",                0.5),
    # "move back":       ("s",                0.5),
    # "move left":       ("a",                0.5),
    # "move right":      ("d",                0.5),
    # Actions
    "jump":            ("space",            0.05),
    "go":              ("enter",            0.05),
    "run":             ("shift",            0.05),
    "click":           ("click",            0),
    # "crouch":          ("ctrl",             0.05),
    # "sprint":          ("shift",            0.05),
    # "reload":          ("r",                0.05),
    # "interact":        ("e",                0.05),
    # "inventory":       ("i",                0.05),
    # "map":             ("m",                0.05),
    # "pause":           ("escape",           0.05),
    # Abilities
    # "ability one":     ("q",                0.05),
    # "ability two":     ("w",                0.05),
    # "ability three":   ("e",                0.05),
    # "ultimate":        ("r",                0.05),
    # Mouse
    # "click":           ("click",            0),
    # "right click":     ("right_click",      0),
    # Control
    "type mode":       ("__mode_type__",    0),
    "command mode":    ("__mode_command__", 0),
    "stop listening":  ("__pause__",        0),
    "start listening": ("__resume__",       0),
}


ARROW_FIX = {
    "ArrowUp": "up", "ArrowDown": "down",
    "ArrowLeft": "left", "ArrowRight": "right",
}

pyautogui.PAUSE = 0
pressed_keys = set()

esp = esp_serial.EspInput(port="COM3")

# ── Key helpers ────────────────────────────────────────────────────────────────

def fix_key(k):
    return ARROW_FIX.get(k, k)

def press(key):
    key = fix_key(key)
    if key not in pressed_keys:
        try:
            pyautogui.keyDown(key)
            pressed_keys.add(key)
            print(f"  ↓ {key.upper()}")
        except Exception as e:
            print(f"  key error: {e}")

def release(key):
    key = fix_key(key)
    if key in pressed_keys:
        pyautogui.keyUp(key)
        pressed_keys.discard(key)

def release_all():
    for key in list(pressed_keys):
        pyautogui.keyUp(fix_key(key))
    pressed_keys.clear()

# ── handlers ───────────────────────────────────────────────────────────────

def handle_tilt(pitch, roll):
    T  = config["threshold"]
    km = config["keyMap"]
    if pitch > T:
        press(km["up"]);    release(km["down"]); release(km["left"]); release(km["right"])
    elif pitch < -T:
        press(km["down"]);  release(km["up"]);   release(km["left"]); release(km["right"])
    elif roll < -T:
        press(km["left"]);  release(km["right"]); release(km["up"]); release(km["down"])
    elif roll > T:
        press(km["right"]); release(km["left"]);  release(km["up"]); release(km["down"])
    else:
        release_all()

def handle_action(action_name):
    """Fire a one-shot action from actionMap (jump, go, run, click)."""
    key = config["actionMap"].get(action_name)
    if key is None:
        return
    if key == "click":
        pyautogui.click()
    elif key == "enter":
        pyautogui.press("enter")
    elif key == "space":
        pyautogui.press("space")
    elif key == "escape":
        pyautogui.press("escape")
    elif key == "backspace":
        pyautogui.press("backspace")
    elif key == "shift":
        pyautogui.press("shift")
    else:
        # Fallback: treat as a regular key tap
        # TODO: decide if this should be a tap or hold
        pass

# ── ESP polling ────────────────────────────────────────────────────────────────

async def esp_poll_loop():
    print("🔌 ESP polling started")
    while True:
        try:
            value = esp.get_data()
            if (value >= 0) and (value < config["esp_threshold"]):
                press(config["esp_key"])
            else:
                release(config["esp_key"])
        except Exception as e:
            print(f"  esp error: {e}")
        await asyncio.sleep(0.2)  # poll every

# ── WebSocket handler ──────────────────────────────────────────────────────────

async def phone_handler(ws):
    print("📱 iPhone connected!")
    try:
        async for msg in ws:
            data = json.loads(msg)

            if data.get("type") == "config":
                if "keyMap"        in data: config["keyMap"]        = data["keyMap"];        print(f"⌨️  Keys: {config['keyMap']}")
                if "threshold"     in data: config["threshold"]     = data["threshold"];     print(f"📐 Threshold: {config['threshold']}°")
                if "esp_key"       in data: config["esp_key"]       = data["esp_key"];       print(f"🔌 ESP key: {config['esp_key']}")
                if "esp_threshold" in data: config["esp_threshold"] = data["esp_threshold"]; print(f"🔌 ESP threshold: {config['esp_threshold']}")
                if "actionMap" in data:
                    config["actionMap"] = data["actionMap"]
                    print(f"🎮 Action map: {config['actionMap']}")

                    # Sync voice commands → COMMAND_MAP (keystroke only, preserve duration)
                    for action in ("jump", "go", "run", "click"):
                        if action in data["actionMap"] and action in COMMAND_MAP:
                            old_key, duration = COMMAND_MAP[action]
                            new_key = data["actionMap"][action]
                            COMMAND_MAP[action] = (new_key, duration)
                            print(f"  🎤 Voice '{action}': {old_key} → {new_key}")

                    # Sensor stays in config only
                    if "sensor" in data["actionMap"]:
                        config["esp_key"] = data["actionMap"]["sensor"]
                        print(f"🔌 ESP key (from actionMap): {config['esp_key']}")
                
                continue
            
            # if "keyMap"    in data: config["keyMap"]    = data["keyMap"]
            # if "threshold" in data: config["threshold"] = data["threshold"]

            handle_tilt(data.get("beta", 0), data.get("gamma", 0))
            handle_action(data.get("action", ""))

    except websockets.ConnectionClosed:
        print("📱 iPhone disconnected")
        release_all()

# ── Main ───────────────────────────────────────────────────────────────────────

async def main():
    ssl_ctx = None
    if os.path.exists("cert.pem") and os.path.exists("key.pem"):
        ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_ctx.load_cert_chain("cert.pem", "key.pem")
        print("🔒 SSL enabled (wss://)")
    else:
        print("⚠️  No cert.pem/key.pem found!")

    # Run voice_controller in a separate thread
    voice_thread = threading.Thread(target=voice_controller.main, args=(COMMAND_MAP,), daemon=True)
    voice_thread.start()
    print("🎤 Voice controller started in background thread")
    
        
    async with websockets.serve(phone_handler, "0.0.0.0", PHONE_PORT, ssl=ssl_ctx):
        print(f"✅ Tilt server running on port {PHONE_PORT}")
        print(f"   Threshold: {config['threshold']}°  |  Keys: {config['keyMap']}")
        print("   Alt-tab into your game and tilt!\n")
        await asyncio.gather(
            esp_poll_loop(),
            asyncio.Future(),  # keep server alive
        )

asyncio.run(main())