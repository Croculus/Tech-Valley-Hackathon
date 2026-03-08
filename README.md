# HeadBand Controller — Setup

## Hardware
- ESP32 (any variant)
- MPU-9250 IMU (~$3)
- Headband or hat for mounting

## Wiring
| MPU-9250 | ESP32     |
|----------|-----------|
| VCC      | 3.3V      |
| GND      | GND       |
| SDA      | GPIO 21   |
| SCL      | GPIO 22   |
| AD0      | GND       |

## Arduino Setup (headband_mouse.ino)
1. Install Arduino IDE + ESP32 board support
2. Install libraries via Library Manager:
   - `ESP32-BLE-Mouse` by T-vK (via https://github.com/T-vK/ESP32-BLE-Mouse)
   - `MPU6050` by Electronic Cats (via Arduino IDE orhttps://github.com/bolderflight/invensense-imu)
3. Open headband_mouse.ino, select your ESP32 board, flash
4. Pair "HeadBand Controller" in Windows Bluetooth settings
5. Hold still for 3 seconds during startup (auto-calibration)

## Python Setup (voice_controller.py)
```bash
pip install elevenlabs pyautogui sounddevice scipy python-dotenv
# Add your ElevenLabs API key to .env
python voice_controller.py
```

## Voice Commands
| Say                        | Action                                          |
|----------------------------|-------------------------------------------------|
| "type mode"               | Switch to dictation mode                        |
| "command mode"            | Switch to game command mode                     |
| "stop listening"          | Pause voice input                               |
| "start listening"         | Resume voice input                              |
| "use action"              | Press the current *action button* key           |
| "set action to <key>"     | Change which key is treated as the action button |
| "jump"                    | Press Space                                     |
| "reload"                  | Press R                                         |
| "ability one"             | Press Q                                         |
| "ultimate"                | Press R (hold)                                  |
| "click"                   | Left mouse click                                |
| ... (see COMMAND_MAP in voice_controller.py for full list)

The chosen action button is also shown in the tilt controller web UI (`iPhone_IMU/controller.html`) and in server logs.

## Tuning the headband sensitivity
Edit these values in headband_mouse.ino:
- `SENSITIVITY` — increase for faster cursor, decrease for finer control
- `DEADZONE` — increase if cursor drifts, decrease if it feels sluggish

## Bill of Materials
| Item              | Est. Cost |
|-------------------|-----------|
| ESP32 dev board   | $8        |
| MPU-9250 module   | $3        |
| Headband/hat      | $5        |
| Jumper wires      | $2        |
| **Total**         | **~$18**  |
