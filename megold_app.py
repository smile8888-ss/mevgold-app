import firebase_admin
from firebase_admin import credentials, messaging

# ==================================================================
# 🔑 ส่วนตั้งค่ากุญแจ (ใส่ให้ครบแล้ว พร้อมระบบทำความสะอาด)
# ==================================================================

# นี่คือรหัส Private Key ที่คุณส่งมา (ผมจัดรูปแบบให้มันเป็นบรรทัดเดียว เพื่อกัน Error 100%)
RAW_PRIVATE_KEY = "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC3Fu9U0SX7RfCW\n56fbbcO21G+nomPJHytEAcGa703mfUq1eSfplphKQ498QmKgZBEl+sQuueiL0TAC\nkJUw4ZuTwBljW6KfwYWuXY3BP5C/OxkANSLUzwh4DwDGo9DHM5cT/P82aayxeaSv\nSKiBf4XU6HVpRtkcjp93b7GgWEIuBbwj22M3UqvSMQPptQLPRAeAb6N2Hl1xRWOo\nTRAPnP72os8iKNiA0WuDXGWkG/Jh2sOz3PSUDwxn17YMsI/aw77JYOkV89eYC+Vo\np4p1ijKivZlSc/IZPTnw4iTimGOOq5paHsAgEsdtGkJRPttFO2dWdLBamIu8CJHw\nLQp62wbVAgMBAAECggEABvJNUUwAI2jzaF5QrZAcEVc9B0CvhYVzuEhSxqSWsYyG\nZZ07qO6oR4UJsB66rDgvuF+rytQN4SQmLKq8plag9vmeXPkwkdwfTM7K3o6hWMgO\nukXJ1QYn3ZpAHsk/Vhd8f2slabSXs0IYv/fDQOqMMthBACYKfb1hioAH3rwKgsFv\narRE9xqeZ8tWPwdCDQ2pZkL9IghkOonTrA5214Tpi0lV9nBMKaEcwuLoQkEA9OQ0\nsuja97YMcwXrRN64UpN4/YPvCgNDfew4hOgCGjd2A1nxNOsvRdf9IQGcfgMtY3Xk\nE2+vrYkp4UZqHC2x6Z6a40/EkamJmrJH1zu96jfKnwKBgQDyAkb256M3zyauIe5S\nEZ/S7e5tpOWrN0x70eXNnJI8Nk99pejRCJbDWPz95wH/HdTQGlz3MIVoM0KOoZhr\nVFWUraW2nwrbnlnmLWVSNhGvV2zSoIAqLU/3CwIS+/4pKFdY86ae7FsIIE+Q8fjD\nVahBuJ57kqbvc2rqdba7ZDX/vwKBgQDBrKdz1xBVcWJbttbl1YFcEFQTK51B23P3\nwZebnGd3UMj4qFcHh1XZOWMLk5VFEzSU0RcxekoMssTK4fVFsqvG3CnrsBIqizOf\n4ZTKHQaEV9RL4gs8NRn/neJi90OMpbiiP4ZgmZvoBn53PnNvrGTrP8U7EYvc0B4j\nsXvNQ99eawKBgQCBw/DTUa92LHBcLLuCbArb6lLPnfy8iwFK32iukIblHGYRRJYL\nB+T3SE8XwfeTGSbUk15H+U9/aQUGP+Xfny/ochgKTUtgKY+g2bSbmXxwHZuvcPpo\nIzXejJuHHHHTFduISdWNH8VMHS8s1GKEMvjujJUGQ8OZX7TzlTzvTDOcNwKBgQCo\n77+JLhmTTjnroktFY71Y3u1XY3u1XY3iylgXzwg9tmoSC6eiLsTrTkO2HXalzHAyNpRx\nEwnWIMOi2/UIu5zE1Rs9dSIj8guGjLHVTmIJAtSCcFJAdsYyGGe7Lq8ggGqtroil\nDiBa9uKlu7Ros1LiIFBPW+rgoWeMjwUbQV+qJwAaTQKBgEobkvPP9JpaYhCsWdkx\ny8zWfvxewelkAWi6OMuAg3LOpKU2+wa2YIboy3EEc8Q/xAbjOXw7IV1J+nmZKjpk\nfs4DI4tfs3OpLcPX3wd/dTcFQhNe0XVXvcHf2Pg5/gL5bNAUqkgJVlY5zdIITHve\nY5zAkQAambVXYunRP2p0PeJ6\n-----END PRIVATE KEY-----\n"

# สร้าง Dictionary กุญแจ (ตามข้อมูลที่คุณส่งมา)
cred_dict = {
    "type": "service_account",
    "project_id": "megold-app",
    "private_key_id": "f771c63b780570558b97b2389bfcbc7c55242a73",
    "private_key": RAW_PRIVATE_KEY.replace('\\n', '\n').strip(), # 🟢 ระบบทำความสะอาดกุญแจ
    "client_email": "firebase-adminsdk-fbsvc@megold-app.iam.gserviceaccount.com",
    "client_id": "106605295384852319462",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40megold-app.iam.gserviceaccount.com"
}

# ==================================================================
# ⚙️ เริ่มต้นระบบ
# ==================================================================
try:
    cred = credentials.Certificate(cred_dict)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    print("✅ เชื่อมต่อ Firebase สำเร็จ!")
    
except Exception as e:
    print("❌ Error เชื่อมต่อ:", e)

# ==================================================================
# 📨 ฟังก์ชันส่งแจ้งเตือน
# ==================================================================
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
    send_push_to_app("47,000", "47,100")
