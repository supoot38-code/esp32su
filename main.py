import network
import urequests
import os
import machine
import time

# ---------------------- ตั้งค่าเท่านี้ ไม่ต้องแก้อย่างอื่น ----------------------
WIFI_SSID = "OPPO A17k"          # ชื่อฮอตสปอตจากรูป
WIFI_PASS = "Aa123123"           # รหัสผ่านจากรูป
GITHUB_PATH = "https://raw.githubusercontent.com/supoot38-code/esp32su/main/ota-firmwre"
CURRENT_VERSION = "1.0.0"        # เหมือนใน version.json
# -----------------------------------------------------------------------------------

# ฟังก์ชันเชื่อมต่อ WiFi
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("กำลังเชื่อมต่อฮอตสปอต...")
        wlan.connect(WIFI_SSID, WIFI_PASS)
        while not wlan.isconnected():
            time.sleep(0.5)
    print("เชื่อมต่อสำเร็จ IP:", wlan.ifconfig()[0])

# ฟังก์ชันตรวจสอบและดาวน์โหลดโค้ดใหม่
def check_update():
    try:
        # อ่านเวอร์ชันล่าสุดจาก GitHub
        res_ver = urequests.get(f"{GITHUB_PATH}/version.json", timeout=10)
        latest_ver = res_ver.json()["version"]
        res_ver.close()

        if latest_ver > CURRENT_VERSION:
            print(f"พบเวอร์ชันใหม่: {latest_ver} → กำลังอัปเดต...")
            # ดาวน์โหลดโค้ดใหม่
            res_code = urequests.get(f"{GITHUB_PATH}/main.py", timeout=10)
            with open("main.py", "w") as f:
                f.write(res_code.text)
            res_code.close()
            print("อัปเดตเสร็จ → รีสตาร์ท")
            time.sleep(2)
            machine.reset()
        else:
            print("เป็นเวอร์ชันล่าสุดแล้ว")
    except Exception as err:
        print("ตรวจสอบอัปเดตไม่ได้:", err)

# เริ่มทำงาน
connect_wifi()
check_update()

# วางโค้ดการทำงานจริงของเครื่องต่อจากบรรทัดนี้ได้เลย
# ตัวอย่าง: print("กำลังทำงาน...")
