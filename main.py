# ==================================================
# ระบบควบคุมรถอัจฉริยะ - เวอร์ชันสมบูรณ์
# ✅ แก้ไขข้อผิดพลาด Wifi Internal State Error
# ✅ รอไฟนิ่ง 3 วินาที เพื่อความเสถียร
# ✅ รองรับอัปเดตโค้ดอัตโนมัติผ่าน GitHub
# ✅ ครบทุกฟังก์ชัน: จอแสดงผล, เสียง, บลูทูธ, เมนู
# ==================================================
import machine, time, framebuf, network, urequests, random, math, ntptime, os, gc
from neopixel import NeoPixel

# ==================================================
# ⚙️ การตั้งค่าพื้นฐาน
# ==================================================
machine.freq(160000000)

# รอให้แรงดันไฟและระบบนิ่งก่อนเริ่มทำงาน
time.sleep_ms(3000)

# กำหนดขาเชื่อมต่อฮาร์ดแวร์
np = NeoPixel(machine.Pin(48), 1)
i2c = machine.I2C(0, scl=machine.Pin(1), sda=machine.Pin(2))
WIDTH, HEIGHT = 128, 32
buffer = bytearray(WIDTH * HEIGHT // 8)
oled = framebuf.FrameBuffer(buffer, WIDTH, HEIGHT, framebuf.MONO_VLSB)

btn_menu = machine.Pin(13, machine.Pin.IN, machine.Pin.PULL_UP)
speaker = machine.PWM(machine.Pin(7))
speaker.duty(0)

# ข้อมูลการเชื่อมต่อ
WIFI_SSID = 'MPY'
WIFI_PASS = 'Aa123123'
VOICE_URL = "http://global-free-intelligence.com/audio/welcome_th.raw"

SCREEN_UPDATE_DELAY = 0.07

# 🔹 การตั้งค่าระบบอัปเดต (แก้ไขเป็นข้อมูลของคุณเมื่อพร้อม)
CURRENT_VERSION = "1.0.0"
USER_NAME = "supoot38-code"
REPO_NAME = "esp32su"
BRANCH_NAME = "main"

# สร้างลิงก์เรียกใช้งาน
VERSION_CHECK_URL = f"https://raw.githubusercontent.com/{USER_NAME}/{REPO_NAME}/{BRANCH_NAME}/version.txt"
NEW_CODE_URL = f"https://raw.githubusercontent.com/{USER_NAME}/{REPO_NAME}/{BRANCH_NAME}/main.py"

MAX_UPDATE_ATTEMPTS = 2
UPDATE_TIMEOUT = 4000
ENABLE_AUTO_UPDATE = True

# การจัดการระบบเบื้องหลัง
ENABLE_AUTO_CLEAN = True
CLEAN_INTERVAL = 10
last_clean_time = time.time()

ENABLE_MEM_CLEAN = True
MEM_CLEAN_INTERVAL = 20
last_mem_clean_time = time.time()

# ==================================================
# 🎉 ลำดับการแสดงผลต้อนรับ
# ==================================================
def show_welcome_sequence():
    time.sleep_ms(200)
    oled.fill(0)
    # เขียนตัวอักษร H E L L O
    oled.line(8, 4, 8, 28, 1)
    oled.line(8, 16, 20, 16, 1)
    oled.line(20, 4, 20, 28, 1)
    
    oled.line(28, 4, 28, 28, 1)
    oled.line(28, 4, 38, 4, 1)
    oled.line(28, 16, 38, 16, 1)
    oled.line(28, 28, 38, 28, 1)
    
    oled.line(46, 4, 46, 28, 1)
    oled.line(46, 28, 56, 28, 1)
    
    oled.line(64, 4, 64, 28, 1)
    oled.line(64, 28, 74, 28, 1)
    
    oled.rect(82, 4, 18, 24, 1)
    render()
    time.sleep_ms(1800)
    
    welcome_text = "S A W A S D E E K R U B"
    text_length = len(welcome_text) * 8
    for offset in range(WIDTH, -text_length, -2):
        oled.fill(0)
        oled.text(welcome_text, offset, 12, 1)
        render()
        time.sleep_ms(130)
    
    oled.fill(0)
    render()
    time.sleep_ms(600)

# ==================================================
# 🛠️ ฟังก์ชันจัดการไวไฟอย่างปลอดภัย
# ==================================================
def safe_wifi_init():
    """ป้องกันข้อผิดพลาดสถานะภายในของโมดูลไวไฟ"""
    try:
        wlan = network.WLAN(network.STA_IF)
        wlan.active(False)
        time.sleep_ms(300)
        wlan.active(True)
        time.sleep_ms(500)
        return wlan
    except Exception as e:
        print("WiFi init error:", e)
        time.sleep_ms(1000)
        return network.WLAN(network.STA_IF)

# ==================================================
# 🎤 ระบบรับคำสั่งเสียง
# ==================================================
VOICE_MODULE_RX = machine.Pin(16)
VOICE_MODULE_TX = machine.Pin(17)
voice_uart = machine.UART(2, baudrate=9600, tx=VOICE_MODULE_TX, rx=VOICE_MODULE_RX)

VOICE_COMMANDS = {
    "เปิดระบบ": "START",
    "ปิดระบบ": "STOP",
    "ล็อกรถ": "LOCK",
    "ปลดล็อก": "UNLOCK",
    "โหมดไวไฟ": "MODE_WIFI",
    "โหมดบลูทูธ": "MODE_BT",
    "ตรวจสอบสถานะ": "STATUS"
}
last_voice_check = time.ticks_ms()
VOICE_CHECK_INTERVAL = 1000

# ==================================================
# 📶 ระบบสลับโหมดการทำงาน
# ==================================================
try:
    import bluetooth
    bt = bluetooth.Bluetooth()
except:
    import ubluetooth as bluetooth
    bt = bluetooth.BLE()

BT_NAME = "MPY"
MODE_WIFI = True
SWITCH_DELAY = 1000
CHECK_INTERVAL = 5000
last_check_time = time.ticks_ms()

# ตัวแปรสถานะระบบ
location_info = "กำลังค้นหาไวไฟ..."
lat_lon = "0.00, 0.00"
temperature = 28.0
humidity = 60
car_locked = True
owner_registered = False
system_state = "idle"

# ==================================================
# 🧹 งานเบื้องหลังรักษาระบบ
# ==================================================
def auto_clean_screen():
    global last_clean_time
    if not ENABLE_AUTO_CLEAN:
        return
    current_time = time.time()
    if current_time - last_clean_time >= CLEAN_INTERVAL:
        for i in range(len(buffer)):
            buffer[i] = 0x00
        render()
        last_clean_time = current_time

def auto_clean_memory():
    global last_mem_clean_time
    if not ENABLE_MEM_CLEAN:
        return
    current_time = time.time()
    if current_time - last_mem_clean_time >= MEM_CLEAN_INTERVAL:
        gc.collect()
        last_mem_clean_time = current_time

# ==================================================
# 🎤 ประมวลผลคำสั่งเสียง
# ==================================================
def process_voice_command(cmd_code):
    global car_locked, MODE_WIFI, location_info
    response = "ไม่เข้าใจคำสั่ง"
    try:
        if cmd_code == "START":
            if owner_registered:
                car_locked = False
                response = "✅ เปิดระบบ"
                set_light(0, 255, 0, 0.3)
            else:
                response = "❌ กรุณาลงทะเบียนก่อน"
                set_light(255, 165, 0, 0.3)
        elif cmd_code == "STOP":
            car_locked = True
            response = "✅ ปิดระบบ"
            set_light(255, 0, 0, 0.3)
        elif cmd_code == "LOCK":
            car_locked = True
            response = "✅ ล็อกรถเรียบร้อย"
            set_light(255, 0, 0, 0.3)
        elif cmd_code == "UNLOCK":
            if owner_registered:
                car_locked = False
                response = "✅ ปลดล็อกเรียบร้อย"
                set_light(0, 255, 0, 0.3)
            else:
                response = "❌ ไม่มีสิทธิ์เข้าถึง"
                set_light(255, 165, 0, 0.3)
        elif cmd_code == "MODE_WIFI":
            if not MODE_WIFI:
                switch_mode(to_wifi=True)
                response = "✅ เปลี่ยนเป็นโหมดไวไฟ"
            else:
                response = "ℹ️ อยู่ในโหมดไวไฟแล้ว"
        elif cmd_code == "MODE_BT":
            if MODE_WIFI:
                switch_mode(to_wifi=False)
                response = "✅ เปลี่ยนเป็นโหมดบลูทูธ"
            else:
                response = "ℹ️ อยู่ในโหมดบลูทูธแล้ว"
        elif cmd_code == "STATUS":
            mode = "ไวไฟ" if MODE_WIFI else f"บลูทูธ:{BT_NAME}"
            lock = "ล็อกอยู่" if car_locked else "ปลดล็อก"
            response = f"โหมด:{mode} | {lock}"
    except:
        response = "⚠️ เกิดข้อผิดพลาด"
        set_light(255, 0, 0, 0.3)
    
    oled.fill(0)
    oled.text("คำสั่งเสียง:", 5, 5)
    oled.text(response[:20], 2, 20)
    render()
    time.sleep_ms(1200)

def check_voice_command():
    global last_voice_check
    if time.ticks_diff(time.ticks_ms(), last_voice_check) < VOICE_CHECK_INTERVAL:
        return
    last_voice_check = time.ticks_ms()
    try:
        if voice_uart.any():
            data = voice_uart.readline()
            if data:
                cmd_str = data.decode('utf-8', errors='ignore').strip()
                if cmd_str in VOICE_COMMANDS:
                    process_voice_command(VOICE_COMMANDS[cmd_str])
    except:
        pass

# ==================================================
# 📟 สลับโหมดการทำงาน
# ==================================================
def switch_mode(to_wifi=True):
    global MODE_WIFI, location_info
    oled.fill(0)
    if to_wifi:
        oled.text("กำลังเปลี่ยนเป็นไวไฟ...", 5, 12)
        for _ in range(2):
            set_light(0, 0, 255, 0.2)
            time.sleep_ms(300)
            set_light(0, 0, 0, 0)
            time.sleep_ms(300)
    else:
        oled.text("กำลังเปลี่ยนเป็นบลูทูธ...", 5, 12)
        for _ in range(2):
            set_light(128, 0, 255, 0.2)
            time.sleep_ms(300)
            set_light(0, 0, 0, 0)
            time.sleep_ms(300)
    render()
    time.sleep_ms(SWITCH_DELAY)
    try:
        if to_wifi:
            bt.active(False)
            time.sleep_ms(300)
            wlan = safe_wifi_init()
            wlan.connect(WIFI_SSID, WIFI_PASS)
            MODE_WIFI = True
            location_info = "กลับสู่โหมดไวไฟแล้ว"
            set_light(0, 255, 0, 0.3)
        else:
            wlan = network.WLAN(network.STA_IF)
            wlan.active(False)
            time.sleep_ms(300)
            bt.active(True)
            bt.config(gap_name=BT_NAME)
            MODE_WIFI = False
            location_info = "เชื่อมต่อบลูทูธแล้ว"
            set_light(0, 128, 255, 0.3)
        time.sleep_ms(500)
    except:
        location_info = "เปลี่ยนโหมดไม่สำเร็จ"
        set_light(255, 0, 0, 0.3)
        time.sleep_ms(800)

def check_connection_auto():
    global last_check_time, MODE_WIFI
    if time.ticks_diff(time.ticks_ms(), last_check_time) < CHECK_INTERVAL:
        return
    last_check_time = time.ticks_ms()
    try:
        if MODE_WIFI:
            if hasattr(bt, 'isconnected') and bt.isconnected():
                switch_mode(to_wifi=False)
        else:
            if hasattr(bt, 'isconnected') and not bt.isconnected():
                switch_mode(to_wifi=True)
    except:
        pass

# ==================================================
# 💡 ระบบไฟสัญญาณ
# ==================================================
def set_light(r, g, b, brightness=0.1):
    np[0] = (int(r * brightness), int(g * brightness), int(b * brightness))
    np.write()

def light_idle():
    pulse = (math.sin(time.ticks_ms() / 1300) + 1) / 2
    brightness = 0.05 + (pulse * 0.06)
    set_light(0, 180, 40, brightness)

def light_connecting():
    blink = int((time.ticks_ms() / 700) % 2)
    set_light(20, 80, 180, 0.12 if blink else 0.02)

def light_checking_update():
    blink = int((time.ticks_ms() / 550) % 2)
    set_light(40, 120, 200, 0.13 if blink else 0.03)

def light_downloading():
    blink = int((time.ticks_ms() / 350) % 2)
    set_light(128, 40, 200, 0.14 if blink else 0.04)

def light_update_success():
    for _ in range(3):
        set_light(200, 200, 200, 0.12)
        time.sleep(0.12)
        set_light(0, 0, 0)
        time.sleep(0.12)

def light_warning():
    for _ in range(2):
        set_light(180, 20, 0, 0.12)
        time.sleep(0.2)
        set_light(0, 0, 0)
        time.sleep(0.2)

def update_light():
    if system_state == "connecting":
        light_connecting()
    elif system_state == "checking_update":
        light_checking_update()
    elif system_state == "downloading":
        light_downloading()
    elif system_state == "warning":
        light_warning()
    else:
        light_idle()

# ==================================================
# 🖥️ ระบบจอแสดงผล
# ==================================================
def init_oled():
    try:
        cmds = [0xAE, 0x20, 0x00, 0x40, 0xA1, 0xA8, 31, 0xC8, 0xD3, 0x00,
                0xDA, 0x02, 0xD5, 0x80, 0xD9, 0xF1, 0xDB, 0x30, 0xA4, 0xA6,
                0x8D, 0x14, 0xAF]
        for cmd in cmds:
            i2c.writeto(0x3c, bytearray([0x80, cmd]))
            time.sleep_ms(2)
    except: pass

def render():
    try:
        for page in range(4):
            i2c.writeto(0x3c, bytearray([0x80, 0xB0 + page, 0x00, 0x10]))
            i2c.writeto(0x3c, b'\x40' + buffer[page*WIDTH : (page+1)*WIDTH])
            time.sleep_ms(1)
    except: pass

# ==================================================
# 🔄 ระบบอัปเดตโค้ดอัตโนมัติ
# ==================================================
def get_version():
    try:
        res = urequests.get(VERSION_CHECK_URL, timeout=3)
        if res.status_code == 200:
            latest_ver = res.read().decode().strip()
            res.close()
            return latest_ver
        res.close()
    except:
        pass
    return None

def download_new_code():
    global system_state
    system_state = "downloading"
    try:
        res = urequests.get(NEW_CODE_URL, timeout=6)
        if res.status_code == 200:
            new_code = res.read()
            res.close()
            try:
                os.remove("main.bak")
            except:
                pass
            os.rename("main.py", "main.bak")
            with open("main.py", "wb") as f:
                f.write(new_code)
            return True
        res.close()
    except:
        pass
    return False

def compare_version(v1, v2):
    try:
        v1_parts = list(map(int, v1.split(".")))
        v2_parts = list(map(int, v2.split(".")))
        return v2_parts > v1_parts
    except:
        return False

def auto_update_check():
    global system_state
    if not ENABLE_AUTO_UPDATE or not MODE_WIFI:
        return
    try:
        wlan = network.WLAN(network.STA_IF)
        if not wlan.isconnected():
            return
        system_state = "checking_update"
        oled.fill(0)
        oled.text("กำลังตรวจสอบเวอร์ชัน...", 5, 12)
        render()
        for attempt in range(MAX_UPDATE_ATTEMPTS):
            start_time = time.ticks_ms()
            latest_version = get_version()
            if time.ticks_diff(time.ticks_ms(), start_time) > UPDATE_TIMEOUT:
                continue
            if latest_version and compare_version(CURRENT_VERSION, latest_version):
                oled.fill(0)
                oled.text(f"พบเวอร์ชันใหม่: {latest_version}", 2, 8)
                oled.text("กำลังอัปเดต...", 25, 20)
                render()
                if download_new_code():
                    light_update_success()
                    oled.fill(0)
                    oled.text("อัปเดตสำเร็จ! กำลังรีสตาร์ท", 2, 12)
                    render()
                    time.sleep(1.5)
                    machine.reset()
                else:
                    break
            else:
                break
        system_state = "idle"
        oled.fill(0)
        oled.text("ระบบเป็นเวอร์ชันล่าสุด", 8, 12)
        render()
        time.sleep(0.8)
    except:
        system_state = "idle"

# ==================================================
# 📊 รวบรวมและแสดงผลข้อมูล
# ==================================================
def update_all_data():
    global location_info, lat_lon, temperature, humidity
    if not MODE_WIFI:
        return
    try:
        wlan = network.WLAN(network.STA_IF)
        if wlan.isconnected():
            try:
                ntptime.settime()
                res = urequests.get("http://ip-api.com/json/", timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("status") == "success":
                        location_info = f"{data.get('city','ไม่ทราบที่ตั้ง')}, {data.get('regionName','')}"
                        lat_lon = f"{data.get('lat',0):.2f}, {data.get('lon',0):.2f}"
                res.close()
            except:
                if location_info == "กำลังค้นหาไวไฟ...":
                    location_info = "ไม่สามารถระบุตำแหน่งได้"
        else:
            location_info = "ไม่ได้เชื่อมต่อไวไฟ"
        temperature = round(25 + (math.sin(time.time() / 2) * 5) + random.uniform(-0.5, 0.5), 1)
        humidity = round(55 + (math.cos(time.time() / 3) * 10) + random.uniform(-1, 1), 1)
    except:
        location_info = "เกิดข้อผิดพลาดในการรับข้อมูล"

def get_time_str():
    try:
        t = time.localtime(time.time() + 7 * 3600)
        return f"{t[3]:02d}:{t[4]:02d}"
    except:
        return "--:--"

def get_wink_emoji():
    try:
        sec = time.localtime()[5]
        return "(^_-)" if sec % 4 == 0 else "(^_^)"
    except:
        return "(^_^)"

def get_status_indicator():
    if MODE_WIFI:
        return "[ไวไฟ]" + ("[ล็อก]" if car_locked else "[ปลดล็อก]")
    else:
        return f"[บลูทูธ:{BT_NAME}]" + ("[ล็อก]" if car_locked else "[ปลดล็อก]")

# ==================================================
# 🔒 ระบบควบคุมความปลอดภัย
# ==================================================
def register_owner():
    global owner_registered
    owner_registered = True
    return "✅ ลงทะเบียนเจ้าของเรียบร้อย"

def verify_owner():
    return owner_registered

def start_car():
    global car_locked
    if verify_owner():
        car_locked = False
        return "✅ สตาร์ทเครื่องยนต์"
    else:
        global system_state
        system_state = "warning"
        time.sleep(0.8)
        system_state = "idle"
        return "❌ กรุณาลงทะเบียนก่อน"

def stop_car():
    global car_locked
    if verify_owner():
        car_locked = True
        return "✅ ดับเครื่องยนต์"
    else:
        return "❌ ไม่มีสิทธิ์เข้าถึง"

# ==================================================
# 📋 ระบบเมนูหลัก
# ==================================================
def system_menu():
    menu_list = [
        "ทำงานปกติ",
        "ลงทะเบียนเจ้าของ",
        "สตาร์ทเครื่องยนต์",
        "ดับเครื่องยนต์",
        "ตรวจสอบอัปเดต",
        "เล่นเสียงต้อนรับ",
        "แสดงข้อมูลระบบ",
        "ออกจากเมนู"
    ]
    sel = 0
    while True:
        oled.fill(0)
        oled.text("== เมนูระบบ ==", 25, 0)
        for i, item in enumerate(menu_list):
            mark = ">" if i == sel else " "
            oled.text(f"{mark}{item}", 3, 10 + (i * 7))
        render()
        if btn_menu.value() == 0:
            press_start = time.ticks_ms()
            while btn_menu.value() == 0: pass
            press_duration = time.ticks_diff(time.ticks_ms(), press_start)
            if press_duration < 600:
                sel = (sel + 1) % len(menu_list)
            else:
                selected = menu_list[sel]
                if selected in ("ทำงานปกติ", "ออกจากเมนู"):
                    break
                elif selected == "ลงทะเบียนเจ้าของ":
                    msg = register_owner()
                elif selected == "สตาร์ทเครื่องยนต์":
                    msg = start_car()
                elif selected == "ดับเครื่องยนต์":
                    msg = stop_car()
                elif selected == "ตรวจสอบอัปเดต":
                    msg = "กำลังตรวจสอบ..."
                    oled.fill(0); oled.text(msg, 20, 12); render()
                    auto_update_check()
                    msg = "ตรวจสอบเสร็จสิ้น" if MODE_WIFI else "ทำงานได้เฉพาะโหมดไวไฟ"
                elif selected == "เล่นเสียงต้อนรับ":
                    msg = "กำลังเล่นเสียง..."
                    if MODE_WIFI:
                        try:
                            wlan = network.WLAN(network.STA_IF)
                            if wlan.isconnected():
                                res = urequests.get(VOICE_URL, stream=True, timeout=10)
                                for chunk in res.raw:
                                    if not chunk: break
                                    for byte_val in chunk:
                                        speaker.duty(int(byte_val * 3.8))
                                        time.sleep_us(42)
                                res.close()
                                speaker.duty(0)
                                msg = "เล่นเสียงเสร็จสิ้น"
                            else:
                                msg = "กรุณาเชื่อมต่อไวไฟก่อน"
                        except:
                            speaker.duty(0)
                            msg = "เกิดข้อผิดพลาดในการเล่นเสียง"
                    else:
                        msg = "ทำงานได้เฉพาะโหมดไวไฟ"
                elif selected == "แสดงข้อมูลระบบ":
                    msg = f"{get_status_indicator()} | อุณหภูมิ:{temperature}°C ความชื้น:{humidity}% | พิกัด:{lat_lon}"
                oled.fill(0); oled.text(msg[:21], 2, 12); render(); time.sleep(1.8)
        time.sleep(0.1)

# ==================================================
# 🚀 ลูปหลักการทำงาน
# ==================================================
def main():
    global system_state
    init_oled()
    
    show_welcome_sequence()
    
    system_state = "idle"
    update_light()
    time.sleep(1.2)

    # เริ่มต้นการเชื่อมต่อไวไฟอย่างปลอดภัย
    try:
        wlan = safe_wifi_init()
        if not wlan.isconnected():
            system_state = "connecting"
            oled.fill(0); oled.text("กำลังเชื่อมต่อไวไฟ...", 5, 12); render()
            wlan.connect(WIFI_SSID, WIFI_PASS)
            wait_count = 0
            while not wlan.isconnected() and wait_count < 8:
                update_light()
                time.sleep(0.5)
                wait_count += 1
    except Exception as e:
        print("WiFi connect error:", e)
        oled.fill(0); oled.text("ไม่สามารถเชื่อมต่อไวไฟได้", 2, 12); render()
        time.sleep(1.5)
    
    system_state = "idle"
    auto_update_check()
    
    welcome_text = "ระบบพร้อมทำงาน..."
    for offset in range(-WIDTH, len(welcome_text)*8, 2):
        oled.fill(0); oled.text(welcome_text, -offset, 12); render()
        update_light()
        time.sleep(0.04)
    
    update_all_data()
    last_refresh = time.time()

    while True:
        update_light()
        
        auto_clean_screen()
        auto_clean_memory()
        check_connection_auto()
        check_voice_command()

        if btn_menu.value() == 0:
            system_menu()
            last_refresh = time.time()

        if time.time() - last_refresh > 180 and MODE_WIFI:
            update_all_data()
            last_refresh = time.time()

        display_text = (
            f"{get_status_indicator()} | {location_info} | "
            f"อุณหภูมิ:{temperature}°C ความชื้น:{humidity}% | พิกัด:{lat_lon} | *** "
        )
        text_pixel_len = len(display_text) * 8
        for offset in range(-WIDTH, text_pixel_len + WIDTH, 1):
            update_light()
            if btn_menu.value() == 0: break
            oled.fill(0)
            oled.text(get_wink_emoji(), 0, 0)
            oled.text(get_time_str(), 85, 0)
            oled.text(display_text, -offset, 12)
            for x in range(0, WIDTH, 8):
                bar_height = random.getrandbits(3)
                oled.line(x, 31, x, 31 - bar_height, 1)
            render()
            time.sleep(SCREEN_UPDATE_DELAY)

if __name__ == '__main__':
    main()
