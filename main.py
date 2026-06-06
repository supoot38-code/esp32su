import machine, time, framebuf, network, urequests, random, math, ntptime, os, gc
from neopixel import NeoPixel

# ==================================================
# ⚙️ การตั้งค่าพื้นฐาน
# ==================================================
machine.freq(160000000)
time.sleep_ms(1000)

# ฮาร์ดแวร์ - คงโหมดจอเดิมที่ทำงานตรงกับเครื่อง
np = NeoPixel(machine.Pin(48), 1)
i2c = machine.I2C(0, scl=machine.Pin(1), sda=machine.Pin(2), freq=400000)
WIDTH, HEIGHT = 128, 32
I2C_ADDR = 0x3C
buffer = bytearray(WIDTH * HEIGHT // 8)
oled = framebuf.FrameBuffer(buffer, WIDTH, HEIGHT, framebuf.MONO_VLSB)

# จังหวะการทำงานจอ
SCREEN_UPDATE_DELAY = 0.075
CLEAR_DRAW_OFFSET_US = 150

# ตัวแปรควบคุมอีโมจิ
face_offset = 0
face_direction = 1
MAX_FACE_MOVE = 2

# 📏 ตำแหน่งปรับใหม่ พร้อมจัดระยะห่างให้ชัดเจน
CHAR_WIDTH = 8
TOP_AREA_HEIGHT = 12       # ความสูงแถวบน
BOTTOM_AREA_Y = 16        # จุดเริ่มแถวล่าง เว้นช่องว่างให้สะอาด
TIME_X_POS = 4 * CHAR_WIDTH
DIVIDER_X = TIME_X_POS + 6 * CHAR_WIDTH
STATUS_X_POS = DIVIDER_X + 4
GPS_X_POS = STATUS_X_POS + 16

# ข้อมูลระบบ
WIFI_SSID = 'OPPO A17k'
WIFI_PASS = 'Aa123123'
VOICE_URL = "http://global-free-intelligence.com/audio/welcome_th.raw"

CURRENT_VERSION = "1.4.10"
BUILD_NUMBER = "แก้เส้นขีดยาวหาย - จัดพื้นที่ให้สะอาด"

USER_NAME = "supoot38-code"
REPO_NAME = "esp32su"
BRANCH_NAME = "main"

VERSION_CHECK_URL = "https://raw.githubusercontent.com/{}/{}/{}/version.txt".format(USER_NAME, REPO_NAME, BRANCH_NAME)
NEW_CODE_URL = "https://raw.githubusercontent.com/{}/{}/{}/main.py".format(USER_NAME, REPO_NAME, BRANCH_NAME)

MAX_UPDATE_ATTEMPTS = 2
UPDATE_TIMEOUT = 5000
ENABLE_AUTO_UPDATE = False

ENABLE_AUTO_CLEAN = True
CLEAN_INTERVAL = 15
last_clean_time = time.time()

ENABLE_MEM_CLEAN = True
MEM_CLEAN_INTERVAL = 25
last_mem_clean_time = time.time()

MAX_WIFI_RETRY = 5
WIFI_RETRY_DELAY = 1000

# ==================================================
# 📋 ตัวแปรทำงาน
# ==================================================
FACE_UART_TX = machine.Pin(18)
FACE_UART_RX = machine.Pin(19)
face_uart = machine.UART(1, baudrate=9600, tx=FACE_UART_TX, rx=FACE_UART_RX, timeout=50)

VOICE_MODULE_RX = machine.Pin(16)
VOICE_MODULE_TX = machine.Pin(17)
voice_uart = machine.UART(2, baudrate=9600, tx=VOICE_MODULE_TX, rx=VOICE_MODULE_RX, timeout=50)

VOICE_COMMANDS = {
    "เปิดระบบ": "START",
    "ปิดระบบ": "STOP",
    "ล็อกรถ": "LOCK",
    "ปลดล็อก": "UNLOCK",
    "โหมดไวไฟ": "MODE_WIFI",
    "โหมดบลูทูธ": "MODE_BT",
    "ตรวจสอบสถานะ": "STATUS",
    "เปิดเพลงออนไลน์": "PLAY_ONLINE",
    "หยุดเพลง": "STOP_MUSIC",
    "เปลี่ยนเพลง": "CHANGE_MUSIC"
}
last_voice_check = time.ticks_ms()
VOICE_CHECK_INTERVAL = 1000

is_playing_music = False
current_stream_url = ""
owner_fav_songs = ["เพลงโปรด 1", "เพลงโปรด 2", "เพลงโปรด 3"]
local_songs = ["เพลงในเครื่อง 1", "เพลงในเครื่อง 2", "เพลงในเครื่อง 3"]
COMMAND_DELAY = 800
STREAM_SWITCH_DELAY = 600
last_command_time = 0

MODE_WIFI = True
SWITCH_MODE_DELAY = 1000
CHECK_CONN_INTERVAL = 6000
last_conn_check = time.ticks_ms()
BT_NAME = "MPY"

location_info = "กำลังค้นหาไวไฟ..."
lat_lon = "13.73, 100.52"
temperature = 27.5
humidity = 62.0
car_locked = True
owner_verified = False
system_state = "idle"

btn_menu = machine.Pin(13, machine.Pin.IN, machine.Pin.PULL_UP)
speaker = machine.PWM(machine.Pin(7))
speaker.duty(0)

# ==================================================
# 🛡️ ฟังก์ชันตรวจสอบความพร้อมอุปกรณ์
# ==================================================
def is_voice_module_ready():
    try:
        if voice_uart is None:
            return False
        voice_uart.flush()
        return True
    except:
        return False

def is_face_module_ready():
    try:
        if face_uart is None:
            return False
        face_uart.flush()
        return True
    except:
        return False

# ==================================================
# 🖼️ ฟังก์ชันวาดสัญลักษณ์
# ==================================================
def draw_wifi(x, y):
    oled.line(x+1, y+7, x+7, y+7, 1)
    oled.line(x+2, y+6, x+6, y+6, 1)
    oled.line(x+3, y+5, x+5, y+5, 1)
    oled.pixel(x+4, y+4, 1)

def draw_bluetooth(x, y):
    oled.line(x+1, y+1, x+5, y+5, 1)
    oled.line(x+5, y+5, x+1, y+9, 1)
    oled.line(x+1, y+9, x+5, y+13, 1)
    oled.line(x+5, y+13, x+1, y+17, 1)
    oled.line(x+3, y+1, x+3, y+17, 1)

def draw_gps(x, y):
    oled.text("GPS", x, y, 1)

# ==================================================
# 🖥️ ระบบจอแสดงผล
# ==================================================
def init_oled():
    try:
        cmd = [0xAE, 0xD5, 0x80, 0xA8, 0x1F, 0xD3, 0x00, 0x40, 0x8D, 0x14,
               0x20, 0x00, 0xA1, 0xC8, 0xDA, 0x02, 0x81, 0xCF, 0xD9, 0xF1,
               0xDB, 0x40, 0xA4, 0xA6, 0xAF]
        for c in cmd:
            i2c.writeto(I2C_ADDR, bytearray([0x80, c]))
            time.sleep_us(50)
        clear_oled()
        print("[จอ] เริ่มต้นเรียบร้อย")
    except Exception as e:
        print("[จอ] ผิดพลาดเริ่มต้น:", e)

def clear_oled():
    oled.fill(0)

def refresh_oled():
    try:
        for page in range(4):
            i2c.writeto(I2C_ADDR, bytearray([0x80, 0xB0 + page, 0x00, 0x10]))
            i2c.writeto(I2C_ADDR, b'\x40' + buffer[page*WIDTH : (page+1)*WIDTH])
            time.sleep_us(100)
    except:
        pass

def welcome_screen():
    print("[ระบบ] แสดงหน้าต้อนรับ")
    clear_oled()
    oled.text("V{} | {}".format(CURRENT_VERSION, BUILD_NUMBER), 12, 0, 1)
    oled.line(6, 3, 6, 29, 1)
    oled.line(6, 15, 18, 15, 1)
    oled.line(18, 3, 18, 29, 1)
    oled.line(26, 3, 26, 29, 1)
    oled.line(26, 3, 36, 3, 1)
    oled.line(26, 15, 36, 15, 1)
    oled.line(26, 29, 36, 29, 1)
    oled.line(44, 3, 44, 29, 1)
    oled.line(44, 29, 54, 29, 1)
    oled.line(62, 3, 62, 29, 1)
    oled.line(62, 29, 72, 29, 1)
    oled.rect(80, 3, 18, 24, 1)
    refresh_oled()
    time.sleep_ms(1500)

    text = "S A W A S D E E K R U B"
    length = len(text) * 8
    for offset in range(WIDTH, -length, -2):
        clear_oled()
        oled.text(text, offset, 12, 1)
        refresh_oled()
        time.sleep_ms(100)

    clear_oled()
    refresh_oled()
    time.sleep_ms(400)
    print("[ระบบ] หน้าต้อนรับเสร็จสิ้น")

def get_blink_symbol():
    global face_offset, face_direction
    try:
        sec = time.localtime()[5]
        phase = sec % 12
        if phase < 3:
            sym = "^_^"
        elif phase < 6:
            sym = "^o^"
        elif phase < 9:
            sym = "-_-"
        else:
            sym = ">.<"

        if sec % 2 == 0:
            face_offset += face_direction
            if face_offset >= MAX_FACE_MOVE or face_offset <= 0:
                face_direction *= -1

        return sym, face_offset
    except:
        return "^_^", 0

def get_current_time():
    try:
        t = time.localtime(time.time() + 7 * 3600)
        return "{:02d}:{:02d}".format(t[3], t[4])
    except:
        return "--:--"

def get_wifi_status():
    try:
        if not MODE_WIFI:
            return False
        wlan = network.WLAN(network.STA_IF)
        return wlan.isconnected()
    except:
        return False

def get_status_text():
    mode = "WiFi" if MODE_WIFI else "BT"
    lock = "LOCKED" if car_locked else "UNLOCKED"
    temp = f"{temperature:.1f}C"
    hum = f"{humidity:.0f}%"
    return f"{mode}|{lock}|Temp:{temp}|Hum:{hum}|GPS:{lat_lon}"

def draw_and_refresh(text_line, offset):
    # ✅ ล้างพื้นที่ให้สะอาดหมดจดทุกครั้ง ไม่ให้มีบิตค้าง
    oled.fill_rect(0, 0, WIDTH, TOP_AREA_HEIGHT, 0)
    oled.fill_rect(0, TOP_AREA_HEIGHT, WIDTH, BOTTOM_AREA_Y - TOP_AREA_HEIGHT, 0) # ล้างช่องว่างตรงกลาง
    oled.fill_rect(0, BOTTOM_AREA_Y, WIDTH, HEIGHT - BOTTOM_AREA_Y, 0)
    time.sleep_us(CLEAR_DRAW_OFFSET_US)

    # วาดอีโมจิ
    icon, x_pos = get_blink_symbol()
    oled.text(icon, x_pos, 2)

    # วาดเวลา
    oled.text(get_current_time(), TIME_X_POS, 2)

    # วาดขีดแบ่ง
    oled.line(DIVIDER_X, 1, DIVIDER_X, TOP_AREA_HEIGHT - 1, 1)

    # วาดสัญลักษณ์
    wifi_connected = get_wifi_status()
    if MODE_WIFI:
        if wifi_connected:
            draw_wifi(STATUS_X_POS, 2)
        else:
            oled.text("x", STATUS_X_POS + 3, 2, 1)
    else:
        draw_bluetooth(STATUS_X_POS, 0)

    if MODE_WIFI and wifi_connected:
        draw_gps(GPS_X_POS, 2)

    # วาดข้อความเลื่อนส่วนล่าง
    oled.text(text_line, -offset, BOTTOM_AREA_Y)

    refresh_oled()

# ==================================================
# 💡 ชุดไฟสถานะ
# ==================================================
def set_rgb(r, g, b, bright=0.1):
    np[0] = (max(0, min(255, int(r * bright))),
             max(0, min(255, int(g * bright))),
             max(0, min(255, int(b * bright))))
    np.write()

def light_idle():
    pulse = (math.sin(time.ticks_ms() / 1300) + 1) / 2
    bright = 0.05 + (pulse * 0.07)
    set_rgb(0, 180, 30, bright)

def light_locked():
    set_rgb(120, 0, 0, 0.12)

def light_unlocked():
    set_rgb(0, 200, 40, 0.15)

def light_connecting():
    blink = int((time.ticks_ms() / 750) % 2)
    set_rgb(0, 60, 180, 0.13 if blink else 0.02)

def light_check_update():
    blink = int((time.ticks_ms() / 550) % 2)
    set_rgb(20, 120, 200, 0.14 if blink else 0.03)

def light_downloading():
    blink = int((time.ticks_ms() / 380) % 2)
    set_rgb(100, 40, 180, 0.15 if blink else 0.04)

def light_update_success():
    for _ in range(3):
        set_rgb(220, 220, 220, 0.12)
        time.sleep(0.15)
        set_rgb(0, 0, 0, 0)
        time.sleep(0.15)

def light_warning():
    for _ in range(3):
        set_rgb(200, 0, 0, 0.15)
        time.sleep(0.12)
        set_rgb(0, 0, 0, 0)
        time.sleep(0.12)

def update_status_light():
    if system_state == "connecting":
        light_connecting()
    elif system_state == "checking_update":
        light_check_update()
    elif system_state == "downloading":
        light_downloading()
    elif system_state == "warning":
        light_warning()
    elif car_locked:
        light_locked()
    elif not car_locked:
        light_unlocked()
    else:
        light_idle()

# ==================================================
# 🎤 ส่วนจัดการคำสั่งเสียง
# ==================================================
def handle_voice_command(cmd):
    global car_locked, MODE_WIFI, location_info
    reply = "ไม่เข้าใจคำสั่ง"
    try:
        if cmd == "START":
            if check_owner():
                car_locked = False
                reply = "✅ เปิดระบบ"
                if scan_face():
                    time.sleep_ms(500)
                    reply = play_favorite()
            else:
                reply = "❌ กรุณาลงทะเบียนก่อน"
        elif cmd == "STOP":
            car_locked = True
            stop_audio()
            reply = "✅ ปิดระบบ"
        elif cmd == "LOCK":
            car_locked = True
            stop_audio()
            reply = "✅ ล็อกเรียบร้อย"
        elif cmd == "UNLOCK":
            if check_owner():
                car_locked = False
                reply = "✅ ปลดล็อกเรียบร้อย"
            else:
                reply = "❌ ไม่มีสิทธิ์"
        elif cmd == "MODE_WIFI":
            if not MODE_WIFI:
                switch_network_mode(True)
                reply = "✅ เปลี่ยนเป็นไวไฟ"
            else:
                reply = "ℹ️ อยู่ในโหมดไวไฟแล้ว"
        elif cmd == "MODE_BT":
            if MODE_WIFI:
                switch_network_mode(False)
                reply = "✅ เปลี่ยนเป็นบลูทูธ"
            else:
                reply = "ℹ️ อยู่ในโหมดบลูทูธแล้ว"
        elif cmd == "STATUS":
            net = "ไวไฟ" if MODE_WIFI else "บลูทูธ: {}".format(BT_NAME)
            lock = "ล็อก" if car_locked else "ปลดล็อก"
            playing = " | กำลังเล่นเพลง" if is_playing_music else ""
            reply = "โหมด:{} | {}{} | {}".format(net, lock, playing, BUILD_NUMBER)
        elif cmd == "PLAY_ONLINE":
            reply = "🎤 พูดชื่อเพลงที่ต้องการ"
        elif cmd == "STOP_MUSIC":
            reply = stop_audio()
        elif cmd == "CHANGE_MUSIC":
            reply = "🎤 พูดชื่อเพลงใหม่ได้เลย"
    except Exception as e:
        return None

    clear_oled()
    oled.text("คำสั่ง:", 5, 5)
    oled.text(reply[:20], 2, 20)
    refresh_oled()
    time.sleep_ms(1200)

def check_voice_input():
    global last_voice_check
    if time.ticks_diff(time.ticks_ms(), last_voice_check) < VOICE_CHECK_INTERVAL:
        return
    last_voice_check = time.ticks_ms()

    if not is_voice_module_ready():
        return

    try:
        if voice_uart.any():
            data = voice_uart.readline()
            if not data:
                return
            cmd_str = data.decode("utf-8", errors="ignore").strip()
            if not cmd_str:
                return

            print("[เสียง] ข้อมูลเข้ามา:", cmd_str)

            if cmd_str.startswith("เล่นเพลง") or cmd_str.startswith("เพลง"):
                name = cmd_str.replace("เล่นเพลง", "").replace("เพลง", "").strip()
                if name:
                    res = play_online_audio(name)
                    clear_oled()
                    oled.text("ผลลัพธ์:", 2, 5)
                    oled.text(res[:20], 2, 20)
                    refresh_oled()
                    time.sleep_ms(1500)
                    return

            if cmd_str in VOICE_COMMANDS:
                handle_voice_command(VOICE_COMMANDS[cmd_str])

    except Exception as e:
        return

# ==================================================
# 🧑 ส่วนตรวจสอบสแกนใบหน้า
# ==================================================
def scan_face():
    if not is_face_module_ready():
        return False
    try:
        if face_uart.any():
            data = face_uart.readline()
            if not data:
                return False
            result = data.decode("utf-8", errors="ignore").strip()
            ok = (result == "OWNER")
            print("[สแกนหน้า]:", "เจ้าของ" if ok else "ไม่ใช่เจ้าของ")
            return ok
        return False
    except:
        return False

# ==================================================
# 🛠️ ฟังก์ชันอื่นๆ ทั้งหมด
# ==================================================
def print_system_status():
    print("\n========================================")
    print("🚗 ระบบควบคุมรถ | เวอร์ชัน: {} | {}".format(CURRENT_VERSION, BUILD_NUMBER))
    print("----------------------------------------")
    print("📶 โหมด: {}".format('ไวไฟ' if MODE_WIFI else 'บลูทูธ: ' + BT_NAME))
    print("🔒 สถานะล็อก: {}".format('ล็อกอยู่' if car_locked else 'ปลดล็อกแล้ว'))
    print("📍 ตำแหน่ง: {} | พิกัด: {}".format(location_info, lat_lon))
    print("🌡️ อุณหภูมิ: {:.1f}°C | ความชื้น: {:.1f}%".format(temperature, humidity))
    print("⚙️ สถานะ: {} | หน่วยความจำว่าง: {} ไบต์".format(system_state, gc.mem_free()))
    print("========================================\n")

def init_wifi():
    print("[ไวไฟ] กำลังเชื่อมต่อ:", WIFI_SSID)
    wlan = network.WLAN(network.STA_IF)
    if wlan.active():
        wlan.disconnect()
        time.sleep_ms(200)
    wlan.active(True)
    time.sleep_ms(500)
    wlan.connect(WIFI_SSID, WIFI_PASS)
    for i in range(MAX_WIFI_RETRY):
        if wlan.isconnected():
            print("[ไวไฟ] เชื่อมต่อสำเร็จ IP:", wlan.ifconfig()[0])
            return wlan, True
        time.sleep_ms(WIFI_RETRY_DELAY)
        print("[ไวไฟ] ลองใหม่ครั้งที่", i+1)
    print("[ไวไฟ] เชื่อมต่อไม่ได้")
    return wlan, False

def switch_network_mode(use_wifi=True):
    global MODE_WIFI, location_info
    print("[ระบบ] เปลี่ยนเป็นโหมด:", 'ไวไฟ' if use_wifi else 'บลูทูธ')
    clear_oled()
    oled.text("เปลี่ยนเป็น...", 5, 12)
    refresh_oled()
    time.sleep_ms(SWITCH_MODE_DELAY)
    try:
        if use_wifi:
            try:
                import bluetooth
                if hasattr(bluetooth, 'BLE'):
                    bt = bluetooth.BLE()
                    if bt.active():
                        bt.active(False)
            except:
                pass
            _, ok = init_wifi()
            MODE_WIFI = True
            location_info = "ออนไลน์" if ok else "ไม่สามารถเชื่อมต่อ"
        else:
            wlan = network.WLAN(network.STA_IF)
            wlan.active(False)
            time.sleep_ms(300)
            try:
                import bluetooth
                bt = bluetooth.BLE()
                bt.active(True)
                bt.config(gap_name=BT_NAME)
                print("[บลูทูธ] เปิดสำเร็จ ชื่อ:", BT_NAME)
                MODE_WIFI = False
                location_info = "บลูทูธพร้อม"
            except Exception as e:
                location_info = "ไม่รองรับบลูทูธ"
                print("[บลูทูธ] ผิดพลาด:", e)
        time.sleep_ms(500)
    except Exception as e:
        location_info = "เปลี่ยนโหมดไม่สำเร็จ"
        print("[โหมด] ผิดพลาด:", e)
        time.sleep_ms(800)

def check_network_connection():
    global last_conn_check, MODE_WIFI
    if time.ticks_diff(time.ticks_ms(), last_conn_check) < CHECK_CONN_INTERVAL:
        return
    last_conn_check = time.ticks_ms()
    try:
        if not MODE_WIFI:
            import bluetooth
            bt = bluetooth.BLE()
            if hasattr(bt, 'isconnected') and not bt.isconnected():
                print("[ตรวจสอบ] บลูทูธหลุด เชื่อมต่อไวไฟอัตโนมัติ")
                switch_network_mode(True)
    except Exception as e:
        print("[ตรวจสอบ] ผิดพลาด:", e)

def auto_clear_screen():
    global last_clean_time
    if not ENABLE_AUTO_CLEAN:
        return
    if time.time() - last_clean_time >= CLEAN_INTERVAL:
        clear_oled()
        refresh_oled()
        last_clean_time = time.time()

def auto_garbage_collect():
    global last_mem_clean_time
    if not ENABLE_MEM_CLEAN:
        return
    if time.time() - last_mem_clean_time >= MEM_CLEAN_INTERVAL:
        gc.collect()
        last_mem_clean_time = time.time()

def get_latest_version():
    try:
        print("[อัปเดต] ตรวจสอบเวอร์ชัน:", VERSION_CHECK_URL)
        res = urequests.get(VERSION_CHECK_URL, timeout=3)
        if res.status_code == 200:
            ver = res.read().decode().strip()
            res.close()
            print("[อัปเดต] ล่าสุดคือ:", ver)
            return ver
        res.close()
    except Exception as e:
        print("[อัปเดต] ตรวจสอบผิดพลาด:", e)
    return None

def download_update():
    global system_state
    system_state = "downloading"
    print("[อัปเดต] กำลังดาวน์โหลดโค้ดใหม่")
    try:
        res = urequests.get(NEW_CODE_URL, timeout=8)
        if res.status_code == 200:
            data = res.read()
            res.close()
            try:
                os.remove("main.bak")
            except:
                pass
            try:
                os.rename("main.py", "main.bak")
                print("[อัปเดต] สำรองไฟล์เดิมเรียบร้อย")
            except:
                print("[อัปเดต] ไม่สามารถสำรองไฟล์ได้")
            with open("main.py", "wb") as f:
                f.write(data)
            print("[อัปเดต] ดาวน์โหลดและบันทึกสำเร็จ")
            return True
        res.close()
    except Exception as e:
        print("[อัปเดต] ดาวน์โหลดผิดพลาด:", e)
    return False

def compare_version(v_now, v_new):
    try:
        parts_now = list(map(int, v_now.split(".")))
        parts_new = list(map(int, v_new.split(".")))
        newer = parts_new > parts_now
        print("[อัปเดต] เปรียบเทียบ: ปัจจุบัน={} | ใหม่={} | ต้องอัปเดต={}".format(v_now, v_new, newer))
        return newer
    except Exception as e:
        print("[อัปเดต] เปรียบเทียบผิดพลาด:", e)
        return False

def check_for_update():
    global system_state
    if not ENABLE_AUTO_UPDATE or not MODE_WIFI:
        print("[อัปเดต] ปิดการตรวจสอบหรือไม่ได้เชื่อมต่อไวไฟ")
        return
    try:
        wlan = network.WLAN(network.STA_IF)
        if not wlan.isconnected():
            return
        system_state = "checking_update"
        clear_oled()
        oled.text("ตรวจสอบอัปเดต...", 3, 12)
        refresh_oled()
        for _ in range(MAX_UPDATE_ATTEMPTS):
            start = time.ticks_ms()
            latest = get_latest_version()
            if time.ticks_diff(time.ticks_ms(), start) > UPDATE_TIMEOUT:
                continue
            if latest and compare_version(CURRENT_VERSION, latest):
                clear_oled()
                oled.text("พบเวอร์ชันใหม่", 2, 8)
                oled.text("กำลังอัปเดต...", 22, 20)
                refresh_oled()
                if download_update():
                    light_update_success()
                    clear_oled()
                    oled.text("อัปเดตเสร็จ กำลังรีสตาร์ท", 2, 12)
                    refresh_oled()
                    print("[อัปเดต] เสร็จสิ้น รีสตาร์ทระบบ")
                    time.sleep(1.5)
                    machine.reset()
                break
            else:
                print("[อัปเดต] ใช้เวอร์ชันล่าสุดอยู่แล้ว")
                break
        system_state = "idle"
        clear_oled()
        oled.text("ระบบพร้อม V{}/{}".format(CURRENT_VERSION, BUILD_NUMBER), 2, 12)
        refresh_oled()
        time.sleep(0.8)
    except Exception as e:
        print("[อัปเดต] ผิดพลาด:", e)
        system_state = "idle"

def update_system_data():
    global location_info, lat_lon, temperature, humidity
    if not MODE_WIFI:
        return
    try:
        wlan = network.WLAN(network.STA_IF)
        if wlan.isconnected():
            try:
                ntptime.settime()
                print("[เวลา] ซิงค์เวลาจากอินเทอร์เน็ต")
            except:
                pass
            try:
                res = urequests.get("http://ip-api.com/json/", timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("status") == "success":
                        location_info = "{}, {}".format(data.get("city", "ไม่ทราบ"), data.get("regionName", ""))
                        lat_lon = "{:.2f}, {:.2f}".format(data.get("lat", 0), data.get("lon", 0))
                        print("[ข้อมูล] ตำแหน่ง: {} | {}".format(location_info, lat_lon))
                res.close()
            except Exception as e:
                print("[ข้อมูล] ดึงตำแหน่งผิดพลาด:", e)
                if location_info in ("กำลังค้นหาไวไฟ...", "ไม่ได้เชื่อมต่อไวไฟ"):
                    location_info = "ไม่สามารถระบุตำแหน่งได้"
        else:
            location_info = "ไม่ได้เชื่อมต่อไวไฟ"
        temperature = round(25 + (math.sin(time.time() / 2) * 3) + random.uniform(-0.3, 0.3), 1)
        humidity = round(55 + (math.cos(time.time() / 3) * 6) + random.uniform(-0.5, 0.5), 1)
    except Exception as e:
        print("[ข้อมูล] อัปเดตผิดพลาด:", e)
        location_info = "เกิดข้อผิดพลาด"

def register_owner():
    global owner_verified
    owner_verified = True
    print("[ระบบ] ลงทะเบียนเจ้าของเรียบร้อย")
    return "✅ ลงทะเบียนเรียบร้อย"

def check_owner():
    return owner_verified

def stop_audio():
    global is_playing_music, current_stream_url
    speaker.duty(0)
    is_playing_music = False
    current_stream_url = ""
    print("[เสียง] หยุดเล่นแล้ว")
    return "✅ หยุดเพลงเรียบร้อย"

def play_online_audio(name):
    global is_playing_music, current_stream_url, last_command_time
    now = time.ticks_ms()
    if time.ticks_diff(now, last_command_time) < COMMAND_DELAY:
        return "⚠️ รอสักครู่"
    last_command_time = now
    if not MODE_WIFI or not network.WLAN(network.STA_IF).isconnected():
        return "❌ ต้องเชื่อมต่อไวไฟก่อน"
    stop_audio()
    time.sleep_ms(STREAM_SWITCH_DELAY)
    try:
        clear_oled()
        oled.text("กำลังค้นหา:", 2, 5)
        oled.text(name[:18], 2, 18)
        refresh_oled()
        print("[เพลง] ค้นหา:", name)
        url = "https://itunes.apple.com/search?term={}&entity=song&limit=5".format(name.replace(" ", "+"))
        res = urequests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data.get("resultCount", 0) > 0:
                for item in data["results"]:
                    link = item.get("previewUrl", "")
                    if link:
                        current_stream_url = link
                        print("[เพลง] พบลิงก์:", link)
                        res_audio = urequests.get(current_stream_url, timeout=15)
                        if res_audio.status_code == 200:
                            is_playing_music = True
                            return "✅ กำลังเล่น: {}".format(name)
                        res_audio.close()
                res.close()
        return "⚠️ ไม่พบเพลงที่ต้องการ"
    except Exception as e:
        print("[เพลง] เล่นผิดพลาด:", e)
        stop_audio()
        return "⚠️ เกิดข้อผิดพลาด"

def play_favorite():
    if not owner_fav_songs:
        return "⚠️ ไม่มีเพลงในรายการ"
    return play_online_audio(owner_fav_songs[0])

def start_car_system():
    global car_locked, system_state
    if check_owner():
        car_locked = False
        if scan_face():
            time.sleep_ms(500)
            return play_favorite()
        return "✅ สตาร์ทเครื่องยนต์"
    else:
        system_state = "warning"
        time.sleep(0.8)
        system_state = "idle"
        return "❌ กรุณาลงทะเบียนเจ้าของก่อน"

def stop_car_system():
    global car_locked
    if check_owner():
        car_locked = True
        stop_audio()
        return "✅ ดับเครื่องยนต์เรียบร้อย"
    else:
        return "❌ ไม่มีสิทธิ์"

def open_menu():
    menu = [
        "ทำงานปกติ",
        "ลงทะเบียนเจ้าของ",
        "สตาร์ทเครื่อง",
        "ดับเครื่อง",
        "ตรวจสอบอัปเดต",
        "เล่นเสียงต้อนรับ",
        "เปิดเพลงออนไลน์",
        "เพลงในเครื่อง",
        "หยุดเพลง",
        "ดูสถานะระบบ",
        "ออกจากเมนู"
    ]
    select = 0
    print("[เมนู] เปิดเมนูหลัก")
    while True:
        clear_oled()
        oled.text("เมนู V{}/{}".format(CURRENT_VERSION, BUILD_NUMBER), 5, 0)
        for i, item in enumerate(menu):
            mark = ">" if i == select else " "
            oled.text("{}{}".format(mark, item), 3, 10 + (i * 7))
        refresh_oled()
        if btn_menu.value() == 0:
            press_start = time.ticks_ms()
            while btn_menu.value() == 0:
                time.sleep_ms(10)
            duration = time.ticks_diff(time.ticks_ms(), press_start)
            if duration < 600:
                select = (select + 1) % len(menu)
            else:
                selected = menu[select]
                print("[เมนู] เลือก:", selected)
                msg = ""
                if selected in ("ทำงานปกติ", "ออกจากเมนู"):
                    break
                elif selected == "ลงทะเบียนเจ้าของ":
                    msg = register_owner()
                elif selected == "สตาร์ทเครื่อง":
                    msg = start_car_system()
                elif selected == "ดับเครื่อง":
                    msg = stop_car_system()
                elif selected == "ตรวจสอบอัปเดต":
                    msg = "กำลังตรวจสอบ..."
                    clear_oled()
                    oled.text(msg, 20, 12)
                    refresh_oled()
                    check_for_update()
                    msg = "V{}/{} พร้อมใช้งาน".format(CURRENT_VERSION, BUILD_NUMBER) if MODE_WIFI else "ต้องเชื่อมต่อไวไฟก่อน"
                elif selected == "เล่นเสียงต้อนรับ":
                    msg = "กำลังเล่น..."
                    if MODE_WIFI:
                        try:
                            wlan = network.WLAN(network.STA_IF)
                            if wlan.isconnected():
                                res = urequests.get(VOICE_URL, timeout=10)
                                if res.status_code == 200:
                                    for b in res.content:
                                        speaker.duty(min(1023, max(0, int(b * 3.8))))
                                        time.sleep_us(42)
                                    res.close()
                                speaker.duty(0)
                                msg = "เล่นเสร็จสิ้น"
                            else:
                                msg = "ไม่ได้เชื่อมต่อไวไฟ"
                        except Exception as e:
                            print("[เสียงต้อนรับ] ผิดพลาด:", e)
                            speaker.duty(0)
                            msg = "เกิดข้อผิดพลาด"
                    else:
                        msg = "ต้องอยู่ในโหมดไวไฟ"
                elif selected == "เปิดเพลงออนไลน์":
                    msg = "พูดชื่อเพลงได้เลย"
                elif selected == "เพลงในเครื่อง":
                    msg = "มี {} รายการ".format(len(local_songs))
                elif selected == "หยุดเพลง":
                    msg = stop_audio()
                elif selected == "ดูสถานะระบบ":
                    mem = gc.mem_free()
                    msg = "หน่วยความจำว่าง: {}B".format(mem)
                    print_system_status()
                clear_oled()
                oled.text(msg[:21], 2, 12)
                refresh_oled()
                time.sleep(1.8)
        time.sleep_ms(50)
    print("[เมนู] ปิดเมนู กลับสู่การทำงานปกติ")

# ==================================================
# 🚀 ลูปหลัก
# ==================================================
def main():
    global system_state
    print("\n==================================================")
    print("🚀 เริ่มทำงานเวอร์ชัน: {} | {}".format(CURRENT_VERSION, BUILD_NUMBER))
    print("==================================================\n")

    init_oled()
    gc.collect()

    welcome_screen()

    system_state = "connecting"
    clear_oled()
    oled.text("กำลังเชื่อมต่อ...", 2, 12)
    refresh_oled()
    _, wifi_ok = init_wifi()

    system_state = "idle"
    if wifi_ok:
        check_for_update()

    intro = "ระบบพร้อมทำงาน V{}/{}".format(CURRENT_VERSION, BUILD_NUMBER)
    length = len(intro) * 8
    for offset in range(-WIDTH, length, 2):
        clear_oled()
        oled.text(intro, -offset, 12)
        refresh_oled()
        update_status_light()
        time.sleep(0.04)

    update_system_data()
    last_data_refresh = time.time()

    while True:
        update_status_light()
        auto_clear_screen()
        auto_garbage_collect()
        check_network_connection()

        check_voice_input()

        if btn_menu.value() == 0:
            open_menu()
            last_data_refresh = time.time()

        if time.time() - last_data_refresh > 120 and MODE_WIFI:
            update_system_data()
            print_system_status()
            last_data_refresh = time.time()

        text_line = get_status_text()
        total_width = len(text_line) * 8

        for offset in range(-WIDTH, total_width + WIDTH, 1):
            update_status_light()
            if btn_menu.value() == 0:
                break
            draw_and_refresh(text_line, offset)
            time.sleep(SCREEN_UPDATE_DELAY)

# ==================================================
# 🛡️ ป้องกันข้อผิดพลาด
# ==================================================
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("\n❌ ระบบเกิดข้อผิดพลาดร้ายแรง:", e)
        clear_oled()
        oled.text("ผิดพลาด V{}".format(CURRENT_VERSION), 2, 8, 1)
        oled.text("รีสตาร์ทใน 3 วินาที", 2, 20, 1)
        refresh_oled()
        time.sleep(3)
        machine.reset()
