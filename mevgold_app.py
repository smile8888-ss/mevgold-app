# mevgold_app.py — MeVGold (Pro/Lite in 1 file)
# Updated: Fixed scraping logic (Text-based + Encoding fix)
# Notification Logic: UNTOUCHED as requested.

import os, json, csv, re, requests
from datetime import datetime, timedelta
import streamlit as st
from bs4 import BeautifulSoup
import pandas as pd

st.set_page_config(page_title="MeVGold", page_icon="🥇", layout="centered")

# ───────── Config / Secrets ─────────
STATE_FILE = "last_gold.json"
HIST_FILE  = "history_today.csv"

# อ่านค่าจาก Secrets (ถ้าไม่มีให้ใช้ค่า Default)
IS_PRO_DEFAULT = str(st.secrets.get("IS_PRO", "true")).lower() in ("1", "true", "yes")
LINE_TOKEN_SECRET = st.secrets.get("LINE_NOTIFY_TOKEN", "")

# Alert policy (Pro only)
COOLDOWN_MIN = int(st.secrets.get("COOLDOWN_MIN", 2))           # minutes
MAX_ALERTS_PER_DAY = int(st.secrets.get("MAX_ALERTS_PER_DAY", 30))

# ───────── Sidebar (mode + LINE token for Pro) ─────────
with st.sidebar:
    st.header("⚙️ Settings")
    is_pro = st.toggle("โหมด Pro", value=IS_PRO_DEFAULT, help="สลับโหมดเพื่อทดสอบฟีเจอร์ Pro/Lite")
    
    line_token_input = ""
    if is_pro:
        st.subheader("🔔 LINE Notify (เฉพาะ Pro)")
        token_in = st.text_input("LINE Notify Token", type="password", value="")
        line_token_input = (token_in.strip() or LINE_TOKEN_SECRET or "").strip()
        
        if line_token_input:
            st.success("พร้อมส่งแจ้งเตือนผ่าน LINE ✅")
        else:
            st.info("ใส่ LINE Token เพื่อให้แจ้งเตือนได้")
    
    LINE_TOKEN = line_token_input

# ───────── Style ─────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Prompt:wght@500;600;700;800&display=swap');
:root{--bg1:#fffef9;--bg2:#faf8f3;--ink:#111;--muted:#788095;--line:#E9EBF3;--gold1:#FAD961;--gold2:#F7B733;--card:#fff;}
html,body,.stApp{background:radial-gradient(140% 160% at 50% -40%,var(--bg1) 0%,var(--bg2) 100%);color:var(--ink);
  font-family:'Prompt',system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;}
.main-wrap{max-width:780px;margin:0 auto;padding:10px 16px 22px;}
.logo{text-align:center;font-size:42px;font-weight:800;letter-spacing:-.4px;margin:8px 0 4px;
  background:linear-gradient(90deg,var(--gold1),var(--gold2));-webkit-background-clip:text;color:transparent;}
.subtitle{text-align:center;color:var(--muted);font-size:14px;margin-bottom:14px;}

.pricebox{background:var(--card);border:2px solid rgba(247,183,51,.35);border-radius:20px;
  box-shadow:0 6px 18px rgba(247,183,51,.12);padding:20px 16px 12px;margin:10px auto 16px;text-align:center;}
.price-title{color:#000;font-weight:800;font-size:16px;margin-bottom:8px;}
/* headline: price + delta */
.headline{display:flex; align-items:baseline; gap:12px; justify-content:center;}
.price-main{font-size:60px;font-weight:900;margin:-2px 0 6px;}
.delta-badge{
  font-weight:900; font-size:28px; line-height:1;
  padding:6px 14px; border-radius:12px;
  border:1px solid var(--line);
}
.delta-up{ color:#0A7B34; background:rgba(16,185,129,.12); border-color:rgba(16,185,129,.35); }
.delta-down{ color:#B00020; background:rgba(239,68,68,.12); border-color:rgba(239,68,68,.35); }
.delta-flat{ color:#6B7280; background:#F3F4F6; border-color:#E5E7EB; }

.kv-wrap{display:flex;gap:16px;flex-wrap:wrap;justify-content:center;margin:10px auto 4px;}
.kv{flex:1 1 320px;background:var(--card);border-radius:16px;box-shadow:0 6px 14px rgba(0,0,0,.05);
  padding:14px 18px 16px;text-align:center;border:1px solid var(--line);}
.kv label{display:block;font-size:13px;color:var(--muted);margin-bottom:6px;}
.kv b{font-size:28px;color:#000;}

.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px 16px;
  box-shadow:0 6px 14px rgba(0,0,0,.05);text-align:center;}
.card h4{margin:0 0 6px;font-size:14px;color:#8b90a1;}
.card .v{font-size:22px;font-weight:800;}

.divider{height:1px;background:var(--line);width:min(760px,92%);margin:12px auto;}
.meta{text-align:center;color:var(--muted);font-size:13px;margin-top:6px;}
.footer{text-align:center;color:#8B90A1;font-size:12px;margin-top:14px;}
.note{font-size:12px;color:#8b90a1;text-align:center;margin-top:6px;}
.upgrade{text-align:center;margin:10px 0 0;}
.upgrade a{display:inline-block;padding:10px 16px;border-radius:12px;border:1px dashed #F7B733;color:#b07a00;
  text-decoration:none;font-weight:800;background:#FFF6E0}
</style>
<div class="main-wrap">
""", unsafe_allow_html=True)

# ───────── Utils: state & history ─────────
def load_state():
    try: return json.load(open(STATE_FILE,"r",encoding="utf-8"))
    except: return {}

def save_state(data:dict):
    try: json.dump(data, open(STATE_FILE,"w",encoding="utf-8"), ensure_ascii=False)
    except: pass

def append_history(row):
    try:
        is_new = not os.path.exists(HIST_FILE)
        with open(HIST_FILE,"a",newline="",encoding="utf-8") as f:
            w = csv.writer(f)
            if is_new:
                w.writerow(["date","time","buy","sell","xauusd","usdthb","calc_baht96"])
            w.writerow(row)
    except: pass

# ───────── Fetchers ─────────
def fetch_gold_thai():
    url = "https://www.goldtraders.or.th/default.aspx"
    # Header เลียนแบบ Browser เพื่อป้องกันการโดนบล็อก
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "th-TH,th;q=0.9"
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        
        # ✅ FIX 1: แก้ปัญหาภาษาต่างดาว (Auto Detect Encoding)
        # เว็บไทยเก่าๆ ชอบใช้ Windows-874 หรือ TIS-620
        r.encoding = r.apparent_encoding 
        
        soup = BeautifulSoup(r.text, "html.parser")

        # ✅ FIX 2: ใช้ Logic หาจาก "ข้อความ" แทนการใช้ ID (ทนทานกว่า)
        def get_price_from_table(label_text, col_index):
            # หาคำว่า "ทองคำแท่ง" หรือ "ทองรูปพรรณ"
            found = soup.find(string=re.compile(label_text))
            if not found: return None
            
            # ถอยกลับไปหาแถวตาราง (tr)
            row = found.find_parent("tr")
            if not row: return None
            
            # หาช่องข้อมูล (td)
            cols = row.find_all("td")
            
            # ดึงตัวเลขจากช่องที่กำหนด
            if len(cols) > col_index:
                text_val = cols[col_index].get_text(strip=True).replace(",", "")
                try: return float(text_val)
                except: return None
            return None

        # เริ่มดึงข้อมูล
        buyv  = get_price_from_table("ทองคำแท่ง", 1) # รับซื้อ
        sellv = get_price_from_table("ทองคำแท่ง", 2) # ขายออก

        # ดึงเวลา
        tstr = datetime.now().strftime("%d/%m/%Y %H:%M") # ค่าเริ่มต้น
        times = None
        
        time_node = soup.find(string=re.compile(r"เวลา\s?\d{1,2}:\d{2}"))
        if time_node:
            tstr = time_node.strip()
            # แกะครั้งที่
            m = re.search(r"ครั้งที่\s?(\d+)", tstr)
            if m: times = int(m.group(1))

        # ถ้าหาไม่เจอจริงๆ ให้ Error เพื่อแจ้งเตือน
        if sellv is None or buyv is None:
             st.error("⚠️ บอทหาคำว่า 'ทองคำแท่ง' ไม่เจอ! (Encoding/Structure Error)")
             # ✅ DEBUG MODE: แสดง HTML ที่บอทเห็น เพื่อดูว่าติดอะไร
             with st.expander("🔎 ดู HTML ที่บอทเห็น (Debug Info)", expanded=True):
                 st.code(soup.prettify()[:4000], language='html')
             
             raise ValueError("หาตัวเลขราคาไม่เจอ")

        return {"buy_bar": buyv, "sell_bar": sellv, "times": times, "timestamp": tstr}

    except Exception as e:
        raise ValueError(f"เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")

def fetch_global_gold_and_fx():
    data = {"xauusd": None, "usdthb": None, "baht96": None}
    try:
        # 1. Gold Spot (Free API)
        try:
            r1 = requests.get("https://api.metals.live/v1/spot/gold", timeout=5)
            if r1.status_code == 200:
                data["xauusd"] = float(r1.json()[0]["price"])
        except: pass

        # 2. USD/THB (Free API)
        try:
            r2 = requests.get("https://api.exchangerate-api.com/v4/latest/USD", timeout=5)
            if r2.status_code == 200:
                data["usdthb"] = float(r2.json()["rates"]["THB"])
        except: pass

        # 3. Calculate
        if data["xauusd"] and data["usdthb"]:
            grams_per_baht = 15.244
            troy_oz = 31.1035
            purity = 0.965
            data["baht96"] = data["xauusd"] * data["usdthb"] * (grams_per_baht / troy_oz) * purity
            
        return data
    except Exception as e:
        return data

# ───────── LINE Notify (Pro) ─────────
def send_line_notify(message: str, token: str):
    if not token: return 0, "no-token"
    try:
        r = requests.post(
            "https://notify-api.line.me/api/notify",
            headers={"Authorization": f"Bearer {token}"},
            data={"message": message}, timeout=10
        )
        return r.status_code, r.text
    except Exception as e:
        return -1, str(e)

# ───────── Alert helpers (Pro) ─────────
def in_cooldown(prev: dict, now: datetime) -> bool:
    last_push = prev.get("last_push")
    if not last_push: return False
    try:
        lp = datetime.fromisoformat(last_push)
        return (now - lp) < timedelta(minutes=COOLDOWN_MIN)
    except: return False

def daily_cap_reached(prev: dict, now: datetime) -> bool:
    tag = now.strftime("%Y-%m-%d")
    push_count = prev.get("push_count", f"{tag}:0")
    try:
        day, cnt = push_count.split(":")
        cnt = int(cnt) if day == tag else 0
        return cnt >= MAX_ALERTS_PER_DAY
    except: return False

def inc_daily_count(prev: dict, now: datetime) -> dict:
    tag = now.strftime("%Y-%m-%d")
    push_count = prev.get("push_count", f"{tag}:0")
    try:
        day, cnt = push_count.split(":")
        cnt = int(cnt) if day == tag else 0
    except:
        cnt = 0
    
    prev["push_count"] = f"{tag}:{cnt+1}"
    prev["last_push"] = now.isoformat()
    return prev

def should_alert(prev: dict, cur: dict) -> bool:
    if not prev: return False
    
    # เช็คว่าราคาเปลี่ยนหรือไม่ (เทียบกับ State ล่าสุดที่บันทึกไว้)
    changed = (cur.get("sell_bar") != prev.get("sell_bar"))
    
    if not changed: return False
    
    now = datetime.now()
    if in_cooldown(prev, now): return False
    if daily_cap_reached(prev, now): return False
    return True

# ───────── Header ─────────
st.markdown(f'<div class="logo">🥇 MeVGold {"Pro" if is_pro else "Lite"}</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">'
    + ('Thai Gold • XAU/USD • USD/THB • 1-Baht(96.5%) • LINE Alerts'
       if is_pro else 'Thai Gold Price (Free) — Manual refresh only')
    + '</div>', unsafe_allow_html=True)

# ───────── Auto-refresh ─────────
if is_pro:
    # Auto refresh every 60s (เพื่อไม่ให้โหลดหนักเกินไป)
    st.markdown('<meta http-equiv="refresh" content="60">', unsafe_allow_html=True)
else:
    st.caption("โหมด Lite: รีเฟรชด้วยปุ่มด้านล่าง (ไม่มี Auto-refresh)")

# ───────── Main flow ─────────
prev = load_state()

try:
    cur = fetch_gold_thai()
except Exception as e:
    # กรณี Error: แสดง Error เล็กน้อย แต่พยายามใช้ข้อมูลเก่าถ้ามี
    st.error(f"❌ ไม่สามารถดึงราคาทองได้: {e}")
    if prev.get("sell_bar"):
        cur = prev
        st.warning(f"⚠️ แสดงราคาล่าสุดที่บันทึกไว้: {prev.get('timestamp')}")
    else:
        st.stop()

# คำนวณส่วนต่าง (ใช้ราคาขายออก)
prev_sell = prev.get("sell_bar", cur["sell_bar"])
change = cur["sell_bar"] - prev_sell
delta_txt = ("+" if change > 0 else "") + f"{change:,.0f}"
delta_cls = "delta-up" if change > 0 else ("delta-down" if change < 0 else "delta-flat")

# กล่องราคา + ป้ายเปลี่ยนแปลง
st.markdown('<div class="pricebox">', unsafe_allow_html=True)
st.markdown('<div class="price-title">ราคาทองคำแท่ง 96.5% (สมาคมค้าทองคำ)</div>', unsafe_allow_html=True)
st.markdown(
    f'''
    <div class="headline">
      <div class="price-main">{cur["sell_bar"]:,.0f} บาท</div>
      <div class="delta-badge {delta_cls}">{delta_txt}</div>
    </div>
    ''',
    unsafe_allow_html=True
)
st.markdown('</div>', unsafe_allow_html=True)

# รับซื้อ / ขายออก
st.markdown('<div class="kv-wrap">', unsafe_allow_html=True)
st.markdown(f'<div class="kv"><label>รับซื้อ</label><b>{cur["buy_bar"]:,.0f}</b></div>', unsafe_allow_html=True)
st.markdown(f'<div class="kv"><label>ขายออก</label><b>{cur["sell_bar"]:,.0f}</b></div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Pro Features
g_data = {"xauusd": None, "usdthb": None, "baht96": None}

if is_pro:
    g_data = fetch_global_gold_and_fx()
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        val = f"${g_data['xauusd']:,.2f}" if g_data['xauusd'] else "N/A"
        st.markdown(f'<div class="card"><h4>XAU/USD</h4><div class="v">{val}</div></div>', unsafe_allow_html=True)
    with c2:
        val = f"{g_data['usdthb']:.2f}" if g_data['usdthb'] else "N/A"
        st.markdown(f'<div class="card"><h4>USD/THB</h4><div class="v">{val}</div></div>', unsafe_allow_html=True)
    with c3:
        val = f"{g_data['baht96']:,.0f}" if g_data['baht96'] else "N/A"
        st.markdown(f'<div class="card"><h4>คำนวณ (บาท)</h4><div class="v">{val}</div></div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="upgrade"><a href="#" title="Upgrade">🔓 เปิดโหมด Pro เพื่อดูราคา Spot & FX</a></div>', unsafe_allow_html=True)

times_txt = f'ครั้งที่ {cur["times"]}' if cur.get("times") else "ครั้งที่ –"
st.markdown(f'<div class="meta">{times_txt} • อัปเดต {cur["timestamp"]}</div>', unsafe_allow_html=True)

# ───────── History Log ─────────
should_log = False
if not os.path.exists(HIST_FILE):
    should_log = True
else:
    try:
        last_row = pd.read_csv(HIST_FILE).iloc[-1]
        if float(last_row["sell"]) != cur["sell_bar"]:
            should_log = True
    except: should_log = True

if should_log:
    append_history([
        datetime.now().strftime("%Y-%m-%d"),
        datetime.now().strftime("%H:%M:%S"),
        f"{cur['buy_bar']:.0f}", f"{cur['sell_bar']:.0f}",
        f"{g_data['xauusd']:.2f}" if g_data['xauusd'] else "",
        f"{g_data['usdthb']:.4f}" if g_data['usdthb'] else "",
        f"{g_data['baht96']:.0f}" if g_data['baht96'] else ""
    ])

with st.expander("📅 ประวัติราคา (CSV)", expanded=False):
    if os.path.exists(HIST_FILE):
        df = pd.read_csv(HIST_FILE)
        st.dataframe(df.tail(30).iloc[::-1], use_container_width=True, hide_index=True)
        st.download_button("⬇️ ดาวน์โหลด CSV", df.to_csv(index=False).encode("utf-8"), "gold_history.csv", "text/csv")

if is_pro:
    st.markdown('<div class="note">* สูตรคำนวณ: Spot × USDTHB × 0.4729 (โดยประมาณ)</div>', unsafe_allow_html=True)

st.markdown('<div class="footer">MeVGold © 2025</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ───────── Logic: Save State & Alerts (UNTOUCHED) ─────────
# เตรียม State ใหม่
new_state = prev.copy()
new_state.update(cur)

if is_pro and LINE_TOKEN:
    # ตรวจสอบเงื่อนไขแจ้งเตือน (ใช้ Logic เดิมเป๊ะ)
    if should_alert(prev, cur):
        sign = "ขึ้น 🟢" if cur["sell_bar"] > prev.get("sell_bar", 0) else "ลง 🔴"
        change_amt = abs(cur["sell_bar"] - prev.get("sell_bar", 0))
        
        msg = (
            f"\n📢 ราคาทอง {sign} {change_amt:,.0f} บาท\n"
            f"ขายออก: {cur['sell_bar']:,.0f}\n"
            f"รับซื้อ: {cur['buy_bar']:,.0f}\n"
            f"({times_txt} - {cur['timestamp']})"
        )
        
        # ส่ง LINE
        code, txt = send_line_notify(msg, LINE_TOKEN)
        
        if code == 200:
            # ถ้าส่งสำเร็จ ค่อยอัปเดต Counter และเวลา
            new_state = inc_daily_count(new_state, datetime.now())
            print(f"LINE Sent: {msg}")
        else:
            print(f"LINE Error: {txt}")

# บันทึก State ท้ายสุด
save_state(new_state)

# Lite: ปุ่มรีเฟรช
if not is_pro:
    if st.button("🔄 รีเฟรชข้อมูล"):
        st.rerun()
