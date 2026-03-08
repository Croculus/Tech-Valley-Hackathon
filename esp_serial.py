
import serial # pip install pyserial
import time

class EspInput:
    def __init__(self, port = "COM3", baud = 115200):
        print("Serial setup delay...")
        time.sleep(2) # setup time
        self.esp_serial = serial.Serial(port, baud, timeout=1)
        for _ in range(5):
            self.esp_serial.readline()

    def get_data(self, retry = 10) -> float:
        for i in range(retry):
            try:
                msg = self.esp_serial.readline()
                msg = msg.decode().strip()
                return float(msg)
            except Exception as e:
                # print("error", i)
                pass
        return -2 # error

    def close(self):
        print("Closing serial")
        self.esp_serial.close()
