import esp_serial

esp = esp_serial.EspInput(port = "COM3")

for i in range(100):
    print(esp.get_data())
