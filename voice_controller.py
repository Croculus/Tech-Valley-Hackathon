"""
HeadBand Voice Controller
Uses ElevenLabs STT (Scribe v2) for:
  1. Typing mode  — transcribes speech and types it out via keyboard
  2. Command mode — maps spoken commands to keypresses for gaming

Dependencies:
  pip install elevenlabs pyautogui sounddevice scipy python-dotenv

Usage:
  1. Copy .env.example to .env and add your ELEVENLABS_API_KEY
  2. Run: python voice_controller.py
  3. Say "type mode" or "command mode" to switch, then speak
  4. Say "stop listening" to pause, "start listening" to resume
"""

import os
import io
import time
import threading
import tempfile
import sounddevice as sd
import scipy.io.wavfile as wav
import pyautogui
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
SAMPLE_RATE        = 16000   # Hz — ElevenLabs accepts 16kHz mono
RECORD_SECONDS     = 2.5     # seconds per voice chunk (lower = more responsive)
SILENCE_THRESHOLD  = 0.01    # RMS below this = silence, skip API call

# ── Game command map — customize per game ────────────────────────────────────
# Key = what you say, Value = pyautogui key string or sequence
COMMAND_MAP = {
    # Movement
    "move forward":    ("w",       0.5),
    "move back":       ("s",       0.5),
    "move left":       ("a",       0.5),
    "move right":      ("d",       0.5),

    # Actions
    "jump":            ("space",   0.05),
    "crouch":          ("ctrl",    0.05),
    "sprint":          ("shift",   0.05),
    "reload":          ("r",       0.05),
    "interact":        ("e",       0.05),
    "inventory":       ("i",       0.05),
    "map":             ("m",       0.05),
    "pause":           ("escape",  0.05),

    # Abilities (common in MOBAs/RPGs)
    "ability one":     ("q",       0.05),
    "ability two":     ("w",       0.05),
    "ability three":   ("e",       0.05),
    "ultimate":        ("r",       0.05),

    # Mouse clicks (useful for point-and-click or menus)
    "click":           ("click",   0),
    "right click":     ("right_click", 0),

    # Mode switching (always active)
    "type mode":       ("__mode_type__",    0),
    "command mode":    ("__mode_command__", 0),
    "stop listening":  ("__pause__",        0),
    "start listening": ("__resume__",       0),
}

# ── State ─────────────────────────────────────────────────────────────────────
mode      = "type"      # "type" or "command"
listening = True
client    = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# ─────────────────────────────────────────────────────────────────────────────
def record_chunk() -> bytes | None:
    """Record RECORD_SECONDS of audio, return WAV bytes or None if silence."""
    recording = sd.rec(
        int(RECORD_SECONDS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16"
    )
    sd.wait()

    # Simple silence detection
    rms = (recording ** 2).mean() ** 0.5 / 32768
    if rms < SILENCE_THRESHOLD:
        return None

    buf = io.BytesIO()
    wav.write(buf, SAMPLE_RATE, recording)
    return buf.getvalue()


def transcribe(audio_bytes: bytes) -> str:
    """Send audio to ElevenLabs STT, return transcript string."""
    try:
        result = client.speech_to_text.convert(
            file=("audio.wav", audio_bytes, "audio/wav"),
            model_id="scribe_v2",
            language_code="en",
        )
        return result.text.strip().lower()
    except Exception as e:
        print(f"[STT Error] {e}")
        return ""


def handle_command(text: str):
    """Match transcription to command map and execute."""
    global mode, listening

    for phrase, (action, duration) in COMMAND_MAP.items():
        if phrase in text:
            print(f"[CMD] '{phrase}' → {action}")

            if action == "__mode_type__":
                mode = "type"
                print("[MODE] Switched to TYPE mode")
            elif action == "__mode_command__":
                mode = "command"
                print("[MODE] Switched to COMMAND mode")
            elif action == "__pause__":
                listening = False
                print("[PAUSED] Say 'start listening' to resume")
            elif action == "__resume__":
                listening = True
                print("[RESUMED]")
            elif action == "click":
                pyautogui.click()
            elif action == "right_click":
                pyautogui.rightClick()
            else:
                pyautogui.keyDown(action)
                time.sleep(duration)
                pyautogui.keyUp(action)
            return  # first match wins

    print(f"[CMD] No match for: '{text}'")


def handle_type(text: str):
    """Type transcribed text at the current cursor position."""
    if text:
        print(f"[TYPE] {text}")
        pyautogui.typewrite(text + " ", interval=0.03)


# ── Main loop ─────────────────────────────────────────────────────────────────
def main():
    global listening, mode

    print("=" * 50)
    print("HeadBand Voice Controller")
    print(f"Mode: {mode.upper()} | Say 'type mode' or 'command mode' to switch")
    print("=" * 50)

    # Allow pyautogui failsafe (move mouse to corner to emergency-stop)
    pyautogui.FAILSAFE = True

    while True:
        if not listening:
            time.sleep(0.2)
            continue

        audio = record_chunk()
        if audio is None:
            continue  # silence — skip API call

        text = transcribe(audio)
        if not text:
            continue

        print(f"[HEARD] {text}")

        # Mode-switch and pause commands work in both modes
        if any(cmd in text for cmd in ["type mode", "command mode", "stop listening", "start listening"]):
            handle_command(text)
        elif mode == "command":
            handle_command(text)
        elif mode == "type":
            handle_type(text)


if __name__ == "__main__":
    main()
