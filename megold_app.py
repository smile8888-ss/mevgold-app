import requests
import json
from bs4 import BeautifulSoup

# =====================================================
# 🔑 ส่วนตั้งค่า
# =====================================================
# 1. App ID (ตัวล่าสุดของคุณ)
ONESIGNAL_APP_ID = "6c5ebe0f-c2e6-4c00-8261-f217f76da7a1"

# 2. API Key (ใส่เฉพาะตัวรหัส os_v2 เพียวๆ ไม่ต้องมีคำนำหน้าในตัวแปร)
ONESIGNAL_API_KEY = "os_v2_app_nrpl4d6c4zgabatb6il7o3nhugsrsy5zec4ewreezk2leqkqsxzcrfd5lgtyfcdqsqi6ehxp2hvv64oiq6iwooinmnfedxjbcdxdr3a"

# =====================================================
# 📨 ฟังก์ชันส่งแจ้งเตือน
# =====================================================
def send_push_to_app(buy_price, sell_price):
    # 🔥 สร้าง Header ตามสูตรที่คุณส่งมา: "Key <token>"
    header = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Key {ONESIGNAL_API_KEY}" 
    }
    
    payload = {
        "app_id": ONESIGNAL_APP_ID,
        "included_segments": ["All"],
        "headings": {"en": "🔔 ทดสอบระบบ (Key Header)"},
        "contents": {"en": f"ราคาทอง: {buy_price} / {sell_price}"}
    }
    
    try:
        print(f"กำลังส่งไปยัง App ID: {ONESIGNAL_APP_ID}...")
        # print(f"Header ที่ใช้ส่ง: {header}") # (เปิดบรรทัดนี้ถ้าอยากเห็น Header จริงตอนรัน)
        
        req = requests.post("https://onesignal.com/api/v1/notifications", headers=header, json=payload)
        print("✅ สถานะการส่ง:", req.status_code)
        print("📄 ผลลัพธ์:", req.text)
    except Exception as e:
        print("❌ Error:", e)

# =====================================================
# 🕵️‍♂️ ส่วนดึงราคา (Force Test)
# =====================================================
def check_gold_price():
    print("--- เริ่มต้น Force Test ---")
    test_buy = "43,800"
    test_sell = "43,900"
    
    # สั่งส่งทันที
    send_push_to_app(test_buy, test_sell)

if __name__ == "__main__":
    check_gold_price()
