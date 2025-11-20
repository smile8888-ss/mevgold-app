import requests
import json
from bs4 import BeautifulSoup

# =====================================================
# 🔑 ส่วนตั้งค่า
# =====================================================
# 1. App ID (ตัวใหม่จากหน้า Settings)
ONESIGNAL_APP_ID = "6c5ebe0f-c2e6-4c00-8261-f217f76da7a1"

# 2. API Key (ตัว os_v2 ตัวเต็ม)
# ⚠️ แก้ไข: ใช้คำนำหน้าว่า "Key" ตามคำแนะนำ
# (ใส่ Key ตัวยาวๆ ที่ก๊อปมา ต่อท้ายคำว่า Key ได้เลย)
ONESIGNAL_API_KEY = "Key os_v2_app_nrpl4d6c4zgabatb6il7o3nhugsrsy5zec4ewreezk2leqkqsxzcrfd5lgtyfcdqsqi6ehxp2hvv64oiq6iwooinmnfedxjbcdxdr3a"

# =====================================================
# 📨 ฟังก์ชันส่งแจ้งเตือน
# =====================================================
def send_push_to_app(buy_price, sell_price):
    # กำหนด Header
    header = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": ONESIGNAL_API_KEY  # ส่งค่า Key os_v2... เข้าไปตรงๆ
    }
    
    # ข้อความที่จะส่ง
    payload = {
        "app_id": ONESIGNAL_APP_ID,
        "included_segments": ["All"],
        "headings": {"en": "🔔 ทดสอบระบบ (Key Header)"},
        "contents": {"en": f"ราคาทอง: {buy_price} / {sell_price}"}
    }
    
    try:
        print(f"กำลังส่งไปยัง App ID: {ONESIGNAL_APP_ID}...")
        req = requests.post("https://onesignal.com/api/v1/notifications", headers=header, json=payload)
        print("✅ สถานะการส่ง:", req.status_code)
        print("📄 ผลลัพธ์:", req.text)
    except Exception as e:
        print("❌ Error:", e)

# =====================================================
# 🕵️‍♂️ ส่วนดึงราคา (Force Test Mode)
# =====================================================
def check_gold_price():
    print("--- เริ่มต้น Force Test ---")
    # จำลองราคาเพื่อทดสอบการส่งทันที
    test_buy = "43,500"
    test_sell = "43,600"
    
    # สั่งส่งทันที
    send_push_to_app(test_buy, test_sell)

if __name__ == "__main__":
    check_gold_price()
