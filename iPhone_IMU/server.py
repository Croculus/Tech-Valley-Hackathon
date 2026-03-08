import asyncio
import websockets
import pyautogui
import json
import ssl
import os

PHONE_PORT = 8765

config = {
    "threshold": 12,
    "keyMap": {"up": "w", "down": "s", "left": "a", "right": "d"},
}

ARROW_FIX = {
    "ArrowUp": "up", "ArrowDown": "down",
    "ArrowLeft": "left", "ArrowRight": "right",
}

pyautogui.PAUSE = 0
pressed_keys = set()

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

async def phone_handler(ws):
    print("📱 iPhone connected!")
    try:
        async for msg in ws:
            data = json.loads(msg)

            if data.get("type") == "config":
                if "keyMap"    in data: config["keyMap"]    = data["keyMap"];    print(f"⌨️  Keys: {config['keyMap']}")
                if "threshold" in data: config["threshold"] = data["threshold"]; print(f"📐 Threshold: {config['threshold']}°")
                continue

            if "keyMap"    in data: config["keyMap"]    = data["keyMap"]
            if "threshold" in data: config["threshold"] = data["threshold"]

            handle_tilt(data.get("beta", 0), data.get("gamma", 0))

    except websockets.ConnectionClosed:
        print("📱 iPhone disconnected")
        release_all()

async def main():
    ssl_ctx = None
    if os.path.exists("cert.pem") and os.path.exists("key.pem"):
        ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_ctx.load_cert_chain("cert.pem", "key.pem")
        print("🔒 SSL enabled (wss://)")
    else:
        print("⚠️  No cert.pem/key.pem found!")

    async with websockets.serve(phone_handler, "0.0.0.0", PHONE_PORT, ssl=ssl_ctx):
        print(f"✅ Tilt server running on port {PHONE_PORT}")
        print(f"   Threshold: {config['threshold']}°  |  Keys: {config['keyMap']}")
        print("   Alt-tab into your game and tilt!\n")
        await asyncio.Future()

asyncio.run(main())