# AdaptLink 🎮
### A Multi-Modal Adaptive Game Controller for People with Physical Disabilities

AdaptLink lets anyone control a PC game using head movement, proximity sensing, or voice commands — with zero specialized hardware. Built at GT Esports TechHack.

---

## Overview

Traditional controllers assume two working hands, full grip strength, and fine motor control. AdaptLink replaces all of that with three alternative input modes that work simultaneously:

| Input | Hardware | How it works |
|-------|----------|--------------|
| **Head Tilt** | iPhone (any model) | Gyroscope streams tilt angles over WebSocket → mapped to directional keys |
| **Proximity Trigger** | ESP32 + HC-SR04 | Ultrasonic sensor detects when user leans forward → fires action button |
| **Voice Commands** | Microphone | ElevenLabs Scribe v2 STT → maps spoken phrases to keypresses |

All three inputs feed into a unified Python server that drives keyboard inputs via `pyautogui` — compatible with any PC game out of the box.

---

## Repository Structure

```
AdaptLink/
│
├── iPhone_IMU/               # Head tilt controller (iPhone gyroscope)
│   ├── server.py             # WebSocket server — receives tilt, drives keyboard
│   ├── host.py               # Flask HTTPS server — serves controller.html to iPhone
│   └── controller.html       # iPhone UI — tilt input + remap + sensitivity slider
│
├── voice/
│   └── voice_controller.py   # ElevenLabs STT voice command pipeline
│
├── ultrasonic/
│   └── ultrasonic.ino        # Arduino sketch for ESP32 + HC-SR04
│
├── headband/
│   └── headband_ble.ino      # ESP32 BLE mouse firmware (MPU-9250 gyroscope)
│
├── unified_server.py         # Combined server — IMU + ultrasonic + TTS + GUI
├── dashboard.html            # Browser dashboard — calibration, remap, status
├── .gitignore
└── README.md
```

---

## Prerequisites

### Python (3.9+)
```bash
pip install websockets pyautogui flask pyopenssl elevenlabs sounddevice scipy numpy python-dotenv
```

### Arduino (for ESP32 components)
Install via Arduino Library Manager:
- `ESP32-BLE-Mouse` by T-vK
- `MPU9250` by Brian Taylor (bolderflight)

### Environment Variables
Create a `.env` file in the project root:
```
ELEVENLABS_API_KEY=sk_your_key_here
```

---

## Setup

### 1. Generate SSL Certificates
Required for iPhone gyroscope access (iOS Safari enforces HTTPS).

```bash
cd iPhone_IMU
python -c "from OpenSSL import crypto; k=crypto.PKey(); k.generate_key(crypto.TYPE_RSA,2048); c=crypto.X509(); c.get_subject().CN='localhost'; c.set_serial_number(1); c.gmtime_adj_notBefore(0); c.gmtime_adj_notAfter(365*24*60*60); c.set_issuer(c.get_subject()); c.set_pubkey(k); c.sign(k,'sha256'); open('cert.pem','wb').write(crypto.dump_certificate(crypto.FILETYPE_PEM,c)); open('key.pem','wb').write(crypto.dump_privatekey(crypto.FILETYPE_PEM,k))"
```

> ⚠️ `cert.pem` and `key.pem` are in `.gitignore` — never commit them. Each user generates their own locally.

### 2. Find Your Local IP
```bash
ipconfig       # Windows
ifconfig       # Mac / Linux
```
Look for the **IPv4 Address** under your WiFi adapter (e.g. `192.168.x.x`).

### 3. Update the IP in controller.html
Open `iPhone_IMU/controller.html` and replace:
```javascript
ws = new WebSocket("wss://YOUR_LOCAL_IP:8765");
```
with your actual IP.

### 4. Flash the ESP32 (Ultrasonic)
- Wire HC-SR04: `Trig → GPIO 13`, `Echo → GPIO 12`, `VCC → 5V`, `GND → GND`
- Open `ultrasonic/ultrasonic.ino` in Arduino IDE
- Select board: `ESP32 Dev Module`
- Upload

### 5. Flash the ESP32 (BLE Headband — optional)
- Wire MPU-9250: `SDA → GPIO 21`, `SCL → GPIO 22`, `VCC → 3.3V`, `GND → GND`, `AD0 → GND`
- Open `headband/headband_ble.ino` in Arduino IDE
- Upload — device will advertise as `HeadBand Controller` over BLE

---

## Running the Head Tilt Controller

Open **three terminals** from the `iPhone_IMU/` folder:

```bash
# Terminal 1 — WebSocket server (receives tilt, drives keyboard)
python server.py

# Terminal 2 — HTTPS server (serves page to iPhone)
python host.py
```

On your **iPhone**, open Safari and go to:
```
https://YOUR_LOCAL_IP:5000
```
Accept the security warning (expected for self-signed cert), then tap **START**.

> **First time only:** Also visit `https://YOUR_LOCAL_IP:8765` in Safari and accept the warning — this trusts the WebSocket certificate.

---

## Using the iPhone Controller UI

Once connected, the iPhone page gives you:

- **D-pad remap** — tap any arrow to reassign it to any key (WASD, arrow keys, space, numbers)
- **Sensitivity slider** — adjust tilt threshold from 5° to 45° in real time
- **Live tilt readout** — shows current pitch and roll angles

All changes take effect instantly without restarting the server.

---

## Running the Voice Controller

```bash
cd voice
python voice_controller.py
```

### Modes
| Say | Effect |
|-----|--------|
| `"command mode"` | Maps speech to game actions |
| `"type mode"` | Types transcribed speech directly |
| `"stop listening"` | Pauses the controller |
| `"start listening"` | Resumes |

### Adding Voice Commands
Edit the `commands_mapping` dict in `voice_controller.py`:
```python
commands_mapping = {
    "jump":    ("space", 0.1),
    "shoot":   ("space", 0.1),
    "go left": ("left",  0.3),
    "go right":("right", 0.3),
    "pause":   ("escape",0.1),
}
```
Format: `"spoken phrase": ("key_to_press", duration_in_seconds)`

### Tuning Voice Detection
| Parameter | Default | Effect |
|-----------|---------|--------|
| `SILENCE_THRESHOLD` | `0.01` | RMS below this = silence. Raise if noisy environment |
| `SILENCE_TIMEOUT` | `0.6s` | Seconds of silence before utterance ends |
| `CHUNK_SECONDS` | `0.3s` | VAD polling interval — don't go below 0.3 on Windows |
| `MAX_RECORD_SECONDS` | `15s` | Hard cap on recording length |

---

## Running the Unified Server (All Inputs Together)

```bash
python unified_server.py
```

| Port | Purpose |
|------|---------|
| `8765` | iPhone IMU WebSocket |
| `8766` | Browser dashboard WebSocket |
| `8767` | ESP32 ultrasonic WebSocket |

The ESP32 should send JSON over WebSocket:
```json
{"distance": 42.5}
```

Open `dashboard.html` in your browser to monitor all inputs, calibrate, and remap.

---

## Wiring Reference

### HC-SR04 Ultrasonic (ESP32)
| HC-SR04 | ESP32 |
|---------|-------|
| VCC | 5V |
| GND | GND |
| Trig | GPIO 13 |
| Echo | GPIO 12 |

### MPU-9250 IMU (ESP32 BLE Headband)
| MPU-9250 | ESP32 |
|----------|-------|
| VCC | 3.3V |
| GND | GND |
| SDA | GPIO 21 |
| SCL | GPIO 22 |
| AD0 | GND (sets I2C address to 0x68) |

---

## Architecture

```
┌─────────────────────────────────────────────┐
│                  INPUTS                     │
│                                             │
│  iPhone Gyroscope  ESP32 Ultrasonic  Voice  │
│       (wss://)          (ws://)      (mic)  │
└────────────┬───────────────┬────────────────┘
             │               │        │
             ▼               ▼        ▼
┌─────────────────────────────────────────────┐
│         unified_server.py (Python)          │
│   - Asyncio WebSocket hub                   │
│   - Applies calibration offsets             │
│   - Threshold filtering                     │
│   - Key remapping                           │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
              pyautogui (keyboard)
                      │
                      ▼
            ┌─────────────────┐
            │   Any PC Game   │
            └─────────────────┘
```

---

## Troubleshooting

**`❌ Connection failed` on iPhone**
- Make sure phone and PC are on the same WiFi network
- Verify your IP address hasn't changed (`ipconfig`)
- Visit `https://YOUR_IP:8765` in Safari and accept the cert warning

**Keys firing when not tilting**
- Increase `TILT_THRESHOLD` in `server.py` (try 20–25)
- Recalibrate by restarting the server while holding head still

**Voice not detecting speech**
- Lower `SILENCE_THRESHOLD` (try `0.005`)
- Check correct microphone is selected: `print(sd.default.device)`
- On Windows, minimum buffer is ~300ms — don't set `CHUNK_SECONDS` below `0.3`

**pyautogui not sending keys to game**
- Click directly on the game window before tilting
- Make sure no other window stole focus

**ESP32 not connecting**
- Confirm ESP32 and PC are on same WiFi
- Check serial monitor for IP address output
- Verify port 8767 is open in Windows Firewall

---

## Notes for New Contributors

- SSL certs are **not committed** — run the cert generation command after cloning
- Replace `YOUR_LOCAL_IP` in `controller.html` with your machine's IP
- Voice threshold values may need per-device calibration — `SILENCE_THRESHOLD` especially varies by microphone
- The `pyautogui` keyboard driver sends to the **focused window** — alt-tab into your game before using any input mode