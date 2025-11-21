import firebase_admin
from firebase_admin import credentials, messaging
import os

# ==========================================
# 1. ตั้งค่า Firebase (อ่านจากไฟล์ JSON โดยตรง)
# ==========================================
try:
    # ตรวจสอบว่ามีไฟล์อยู่จริงไหม
    if not os.path.exists("firebase_key.json"):
        print("❌ ไม่เจอไฟล์ firebase_key.json ใน GitHub!")
        exit(1)

    cred = credentials.Certificate("firebase_key.json")
    
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    print("✅ เชื่อมต่อ Firebase สำเร็จ!")

except Exception as e:
    print("❌ Error กุญแจ:", e)

# ==========================================
# 2. ฟังก์ชันส่งแจ้งเตือน
# ==========================================
def send_push_to_app(buy_price, sell_price):
    print(f"กำลังส่งข้อมูล: {buy_price} / {sell_price}")
    
    message = messaging.Message(
        notification=messaging.Notification(
            title="🔔 ราคาทองเปลี่ยน!",
            body=f"รับซื้อ: {buy_price} | ขายออก: {sell_price}",
        ),
        topic="all",
    )

    try:
        response = messaging.send(message)
        print("✅ ส่งแจ้งเตือนสำเร็จ! Message ID:", response)
    except Exception as e:
        print("❌ ส่งไม่ผ่าน:", e)

# --- Test ---
if __name__ == "__main__":
    send_push_to_app("48,000", "48,100")
