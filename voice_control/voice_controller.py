"""
HeadBand Voice Controller
Captures microphone audio and transcribes via ElevenLabs STT (Scribe v2).
Uses Voice Activity Detection (VAD) to dynamically extend recording while
the speaker is still talking, and stop shortly after they go silent.

Dependencies:
  pip install elevenlabs pyautogui sounddevice scipy numpy python-dotenv

Usage:
  1. Add your ELEVENLABS_API_KEY to a .env file:
       ELEVENLABS_API_KEY=sk_...
  2. Run: python voice_controller.py
  3. Say "type mode" or "command mode" to switch, then speak
  4. Say "stop listening" to pause, "start listening" to resume
"""
import os
import io
import time
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
import pyautogui
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
SAMPLE_RATE        = 16000  # Hz — ElevenLabs accepts 16kHz mono
CHUNK_SECONDS      = 0.3    # VAD polling interval — 300ms avoids Windows WASAPI minimum buffer rejection
SILENCE_THRESHOLD  = 0.08 # RMS below this → silence
SILENCE_TIMEOUT    = 0.6    # seconds of silence that ends an utterance
MAX_RECORD_SECONDS = 15.0   # hard cap to prevent runaway recordings

if not ELEVENLABS_API_KEY:
    raise RuntimeError("ELEVENLABS_API_KEY is not set. Add it to your .env file.")

client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# ── Game command map ───────────────────────────────────────────────────────────
COMMAND_MAP = {
    # Movement
    "move forward":    ("w",                0.5),
    "move back":       ("s",                0.5),
    "move left":       ("a",                0.5),
    "move right":      ("d",                0.5),
    # Actions
    "jump":            ("space",            0.05),
    "crouch":          ("ctrl",             0.05),
    "sprint":          ("shift",            0.05),
    "reload":          ("r",                0.05),
    "interact":        ("e",                0.05),
    "inventory":       ("i",                0.05),
    "map":             ("m",                0.05),
    "pause":           ("escape",           0.05),
    # Abilities
    "ability one":     ("q",                0.05),
    "ability two":     ("w",                0.05),
    "ability three":   ("e",                0.05),
    "ultimate":        ("r",                0.05),
    # Mouse
    "click":           ("click",            0),
    "right click":     ("right_click",      0),
    # Control
    "type mode":       ("__mode_type__",    0),
    "command mode":    ("__mode_command__", 0),
    "stop listening":  ("__pause__",        0),
    "start listening": ("__resume__",       0),
}

# ── State ──────────────────────────────────────────────────────────────────────
mode      = "command"  # "type" or "command"
listening = True


# ── Audio capture with VAD ─────────────────────────────────────────────────────
def record_utterance() -> bytes | None:
    """
    Record until the speaker stops talking using a single continuous stream.
    This avoids the click/gap caused by repeatedly opening and closing the mic.

    Flow:
      1. Open one InputStream that runs the whole time.
      2. Read CHUNK_SECONDS worth of samples at a time via stream.read().
      3. Wait for speech to start, then buffer until silence persists for
         SILENCE_TIMEOUT seconds or MAX_RECORD_SECONDS is reached.
    """
    chunk_samples  = int(CHUNK_SECONDS * SAMPLE_RATE)
    silence_chunks = int(SILENCE_TIMEOUT / CHUNK_SECONDS)
    max_chunks     = int(MAX_RECORD_SECONDS / CHUNK_SECONDS)

    frames         = []
    silent_count   = 0
    speech_started = False

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16") as stream:
        for _ in range(max_chunks):
            chunk, _ = stream.read(chunk_samples)  # blocks until samples are ready
            rms  = (chunk.flatten().astype(np.float32) ** 2).mean() ** 0.5 / 32768
            #print('chunk max: {}, chunk min: {}, rms: {}'.format(chunk.max(), chunk.min(), rms))
            #print("device {}".format(sd.default.device))
            is_speech = rms > SILENCE_THRESHOLD

            if not speech_started:
                if is_speech:
                    speech_started = True
                    frames.append(chunk)
                    silent_count = 0
                # still waiting for speech — don't buffer leading silence
            else:
                frames.append(chunk)
                if is_speech:
                    silent_count = 0  # speaker still going — reset timer
                else:
                    silent_count += 1
                    if silent_count >= silence_chunks:
                        break  # speaker stopped — end utterance

    if not frames:
        return None

    audio = np.concatenate(frames, axis=0)
    buf   = io.BytesIO()
    wav.write(buf, SAMPLE_RATE, audio)
    buf.seek(0)
    return buf.getvalue()


# ── Transcription ──────────────────────────────────────────────────────────────
def transcribe(audio_bytes: bytes) -> str:
    """Send audio to ElevenLabs STT, return lowercase transcript or empty string."""
    try:
        result = client.speech_to_text.convert(
            file=("audio.wav", audio_bytes, "audio/wav"),
            model_id="scribe_v2",
            language_code="en",
        )
        return (result.text or "").strip().lower()
    except Exception as e:
        print(f"[Error] {e}")
        return ""


# ── Command / type handlers ────────────────────────────────────────────────────
def handle_command(text: str):
    global mode, listening
    for phrase, (action, duration) in COMMAND_MAP.items():
        if phrase in text:
            print(f"[CMD] '{phrase}' → {action}")
            if action == "__mode_type__":
                mode = "type";    print("[MODE] TYPE")
            elif action == "__mode_command__":
                mode = "command"; print("[MODE] COMMAND")
            elif action == "__pause__":
                listening = False; print("[PAUSED] Say 'start listening' to resume")
            elif action == "__resume__":
                listening = True;  print("[RESUMED]")
            elif action == "click":
                pyautogui.click()
            elif action == "right_click":
                pyautogui.rightClick()
            else:
                pyautogui.keyDown(action)
                time.sleep(duration)
                pyautogui.keyUp(action)
            return
    print(f"[CMD] No match for: '{text}'")


def handle_type(text: str):
    if text:
        print(f"[TYPE] {text}")
        pyautogui.typewrite(text + " ", interval=0.03)


# ── Main loop ──────────────────────────────────────────────────────────────────
def main():
    global listening, mode

    print("=" * 50)
    print("HeadBand Voice Controller  (VAD mode)")
    print(f"  Mode            : {mode.upper()}")
    print(f"  Silence timeout : {SILENCE_TIMEOUT}s  (tweak SILENCE_TIMEOUT)")
    print(f"  Max utterance   : {MAX_RECORD_SECONDS}s")
    print("  Say 'type mode' / 'command mode' to switch")
    print("  Say 'stop listening' / 'start listening' to pause")
    print("  Move mouse to screen corner to emergency-stop")
    print("=" * 50)

    pyautogui.FAILSAFE = True

    while True:
        if not listening:
            time.sleep(0.2)
            continue

        audio = record_utterance()
        if audio is None:
            continue  # no speech detected — skip API call

        text = transcribe(audio)
        if not text:
            continue

        print(f"[HEARD] {text}")

        # Control commands always fire regardless of mode
        if any(cmd in text for cmd in ["type mode", "command mode", "stop listening", "start listening"]):
            handle_command(text)
        elif mode == "command":
            handle_command(text)
        elif mode == "type":
            handle_type(text)


if __name__ == "__main__":
    main()