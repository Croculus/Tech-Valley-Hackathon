/*
 * HeadBand BLE Mouse Firmware
 * Hardware: ESP32 + MPU-9250 (I2C)
 * Library deps (install via Arduino Library Manager):
 *   - "ESP32-BLE-Mouse" by T-vK https://github.com/T-vK/ESP32-BLE-Mouse
 *   - "MPU9250" by Brian Taylor https://github.com/bolderflight/invensense-imu
 *
 * Wiring:
 *   MPU-9250 VCC -> ESP32 3.3V
 *   MPU-9250 GND -> ESP32 GND
 *   MPU-9250 SDA -> ESP32 GPIO 21
 *   MPU-9250 SCL -> ESP32 GPIO 22
 *   MPU-9250 AD0 -> GND (I2C address 0x68)
 */

#include <BleMouse.h>
#include <Wire.h>
#include <mpu9250.h>

// ── BLE Mouse instance ───────────────────────────────────────────────────────
BleMouse bleMouse("HeadBand Controller", "HackTeam", 100);

// ── MPU-9250 instance (address 0x68 with AD0 to GND) ────────────────────────
MPU9250 mpu(Wire, 0x68);

// ── Tuning parameters (adjust during calibration) ───────────────────────────
const float SENSITIVITY   = 0.08f;   // lower = slower cursor
const float DEADZONE      = 1.5f;    // degrees/s — ignore tiny movements
const int   LOOP_DELAY_MS = 10;      // ~100Hz polling rate

// ── Calibration offsets ──────────────────────────────────────────────────────
float gyroX_offset = 0;
float gyroY_offset = 0;

// ─────────────────────────────────────────────────────────────────────────────
void calibrate(int samples = 200) {
  Serial.println("Calibrating — hold still...");
  float sumX = 0, sumY = 0;
  for (int i = 0; i < samples; i++) {
    mpu.readSensor();
    sumX += mpu.getGyroX_rads() * (180.0f / PI);
    sumY += mpu.getGyroY_rads() * (180.0f / PI);
    delay(5);
  }
  gyroX_offset = sumX / samples;
  gyroY_offset = sumY / samples;
  Serial.printf("Offsets -> X: %.3f  Y: %.3f\n", gyroX_offset, gyroY_offset);
}

// ─────────────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  Wire.begin();

  // Init MPU-9250
  int status = mpu.begin();
  if (status < 0) {
    Serial.println("MPU-9250 connection FAILED — check wiring! Status: " + String(status));
    while (true) delay(1000);
  }
  Serial.println("MPU-9250 OK");

  // Set gyro range to ±250°/s for fine head movement sensitivity
  mpu.setGyroRange(MPU9250::GYRO_RANGE_250DPS);
  mpu.setAccelRange(MPU9250::ACCEL_RANGE_2G);
  mpu.setDlpfBandwidth(MPU9250::DLPF_BANDWIDTH_20HZ); // low-pass filter smooths noise

  calibrate();

  // Start BLE
  bleMouse.begin();
  Serial.println("BLE Mouse advertising — waiting for host connection...");
}

// ─────────────────────────────────────────────────────────────────────────────
void loop() {
  if (!bleMouse.isConnected()) {
    delay(100);
    return;
  }

  mpu.readSensor();

  // Get gyro in degrees/sec, apply calibration offset
  float rateX = (mpu.getGyroX_rads() * (180.0f / PI)) - gyroX_offset; // yaw  → horizontal
  float rateY = (mpu.getGyroY_rads() * (180.0f / PI)) - gyroY_offset; // pitch → vertical

  // Deadzone — ignore values below threshold
  if (abs(rateX) < DEADZONE) rateX = 0;
  if (abs(rateY) < DEADZONE) rateY = 0;

  // Scale to mouse movement delta
  int8_t moveX = (int8_t)constrain(rateX * SENSITIVITY * -1, -127, 127);
  int8_t moveY = (int8_t)constrain(rateY * SENSITIVITY, -127, 127);

  if (moveX != 0 || moveY != 0) {
    bleMouse.move(moveX, moveY);
  }

  delay(LOOP_DELAY_MS);
}
