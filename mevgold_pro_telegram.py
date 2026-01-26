# mevgold_pro_telegram.py — MeVGold 96.5% (Official Penetration Fixed)
# แก้ไขล่าสุด: ใส่ฟังก์ชันที่ขาดหายไป + เน้นเจาะเว็บสมาคมฯ (Official) เป็นหลัก
# Notification Logic: คงเดิม 100%

import os, json, re, csv, requests
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

import streamlit as st
from bs4 import BeautifulSoup
import pandas as pd

# ===== 1) Config =====
st.set_page_config(page_title="MeVGold — Thai Gold 96.5%", page_icon="🏆", layout="centered")

st.markdown("""
<link rel="manifest" href="static/manifest.json">
<link rel="apple-touch-icon" href="static/apple-touch-icon.png">
<link rel="icon" href="static/icon-192.png">
<meta name="theme-color" content="#F0C159">
<meta http-equiv="refresh" content="60">
<meta name="viewport" content="width=device-width, initial-scale=1">
""", unsafe_allow_html=True)

TZ = ZoneInfo("Asia/Bangkok")
STATE_FILE = "last_gold.json"
HIST_FILE  = "history_today.csv"
FETCH_TIMEOUT = 20

TG_TOKEN = str(st.secrets.get("TELEGRAM_BOT_TOKEN", "") or "")
TG_CHAT  = str(st.secrets.get("TELEGRAM_CHAT_ID", "") or "")

UP_EMOJI = "🟢⬆️"      
DOWN_EMOJI = "🔻⬇️"     

# ===== 2) Styles =====
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Prompt:wght@500;600;700;800&display=swap');
:root{ --gold1:#F8E08A; --gold2:#F0C159; --line:rgba(255,255,255,.08); --radius-lg:18px; }
html,body,.stApp{font-family:'Prompt',sans-serif;background:#0b0e12;color:#eceff4;}
.wrap{max-width:920px;margin:0 auto;padding:16px 12px 24px}
.brand{text-align:center;font-size:28px;margin:6px 0;background:linear-gradient(90deg,var(--gold1),var(--gold2));-webkit-background-clip:text;color:transparent;font-weight:800}
.sub{text-align:center;color:#9ca3af;font-size:13px;margin-bottom:12px}
.card{background:rgba(255,255,255,.03);border:1px solid var(--line);border-radius:var(--radius-lg);overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,.3)}
.header{display:flex;justify-content:space-between;align-items:center;padding:12px;background:rgba(240,193,89,.05);border-bottom:1px solid var(--line);flex-wrap:wrap;gap:8px}
.badge{background:#F0C159;color:#000;padding:4px 10px;border-radius:20px;font-weight:bold;font-size:14px}
.row{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;padding:10px}
.cell{background:rgba(255,255,255,.03);padding:12px;border-radius:12px;text-align:center;border:1px solid var(--line)}
.cell.head{font-size:12px;color:#9ca3af;background:transparent;border:none}
.price{font-size:26px;font-weight:900;color:#F8E08A}
.footer{padding:10px;text-align:center;font-size:12px;color:#6b7280;border-top:1px solid var(--line)}
.price.up{color:#22c55e} .price.down{color:#ef4444} .price.flat{color:#9ca3af}
</style>
<div class="wrap">
""", unsafe_allow_html=True)

# ===== 3) Logic Helpers =====
TH_MONTH = ["ม.ค.","ก.พ.","มี.ค.","เม.ย.","พ.ค.","มิ.ย.","ก.ค.","ส.ค.","ก.ย.","ต.ค.","พ.ย.","ธ.ค."]

def th_now(dt): 
    return f"{dt.day} {TH_MONTH[dt.month-1]} {dt.year+543} • {dt.strftime('%H:%M')} น."

def load_state():
    try: return json.load(open(STATE_FILE,"r"))
    except: return {}

def save_state(d):
    try: json.dump(d, open(STATE_FILE,"w"), ensure_ascii=False)
    except: pass

def ensure_hist():
    cols = ["date","time","times","buy_bar","sell_bar","buy_orn","sell_orn","d_buy","d_sell"]
    if not os.path.exists(HIST_FILE):
        with open(HIST_FILE,"w",newline="",encoding="utf-8") as f: csv.writer(f).writerow(cols)

def append_hist(row):
    # ป้องกันการบันทึกค่าว่าง
    if not row.get("sell_bar") or str(row.get("sell_bar")) in ["0","None","0.0"]: return
    ensure_hist()
    try:
        with open(HIST_FILE,"a",newline="",encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=["date","time","times","buy_bar","sell_bar","buy_orn","sell_orn","d_buy","d_sell"]).writerow(row)
    except: pass

def send_telegram(msg):
    if TG_TOKEN and TG_CHAT:
        try: requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data={"chat_id":TG_CHAT,"text":msg,"parse_mode":"HTML"}, timeout=5)
        except: pass

# ✅ ฟังก์ชันที่เคยหายไป (เติมให้แล้วครับ)
def fmt_delta_for_badge(n):
    if n > 0: return f"▲ +{n:,.0f}"
    if n < 0: return f"▼ {n:,.0f}"
    return "—"

# ===== 4) FETCHERS (Official First) =====

# --- 1. Official Website (GoldTraders.or.th) ---
# ใช้วิธีแกะ __NEXT_DATA__ JSON ที่ซ่อนอยู่หลังบ้าน
def fetch_official():
    try:
        # Header ต้องเนียนเหมือน Chrome
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "th-TH,th;q=0.9",
            "Referer": "https://www.google.com/"
        }
        r = requests.get("https://www.goldtraders.or.th/", headers=headers, timeout=FETCH_TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        
        # เจาะหา Script ที่เก็บข้อมูล JSON
        script = soup.find("script", id="__NEXT_DATA__")
        if script:
            data = json.loads(script.string)
            
            # ฟังก์ชันวนหา Key ที่ซ่อนอยู่ลึกๆ
            def find_key(d, k_tgt):
                if isinstance(d, dict):
                    for k,v in d.items():
                        if k.lower() == k_tgt.lower(): return v
                        res = find_key(v, k_tgt)
                        if res: return res
                elif isinstance(d, list):
                    for i in d:
                        res = find_key(i, k_tgt)
                        if res: return res
                return None
            
            def get_val(k): 
                v = find_key(data, k)
                try: return float(str(v).replace(",",""))
                except: return None
                
            # ดึงราคา (ชื่อตัวแปรของสมาคมคือ blSell, blBuy, omSell, omBuy)
            bs = get_val("blSell")
            bb = get_val("blBuy")
            os = get_val("omSell")
            ob = get_val("omBuy")
            
            if bs and bs > 0:
                # ดึงเวลา
                raw_d = str(find_key(data, "updateDate") or find_key(data, "timeUpdate") or "")
                mt = re.search(r"(\d{1,2}:\d{2})", raw_d)
                
                # ดึงครั้งที่
                raw_r = str(find_key(data, "round") or find_key(data, "times") or "")
                mr = re.search(r"(\d+)", raw_r)
                
                return {
                    "bar_buy": bb, "bar_sell": bs, "orn_buy": ob, "orn_sell": os,
                    "times": int(mr.group(1)) if mr else None,
                    "asof_time": mt.group(1) if mt else datetime.now(TZ).strftime("%H:%M")
                }
    except Exception as e:
        print(f"Official Failed: {e}")
    return None

# --- 2. Nam Chiang (Backup) ---
# เว็บ HTML ดั้งเดิมที่ดึงข้อมูลสมาคมมาแสดง
def fetch_namchiang():
    try:
        r = requests.get("http://www.namchiang.com/th/", headers={"User-Agent":"Mozilla/5.0"}, timeout=15)
        r.encoding = "cp874" 
        soup = BeautifulSoup(r.text, "html.parser")
        
        def get_vals(label):
            tag = soup.find("td", string=re.compile(label))
            if not tag: return None, None
            nums = []
            curr = tag.find_next("td")
            while curr and len(nums) < 2:
                txt = curr.get_text(strip=True).replace(",","")
                if re.match(r"^\d+(\.\d+)?$", txt) and float(txt) > 1000:
                    nums.append(float(txt))
                curr = curr.find_next("td")
            return (nums[0], nums[1]) if len(nums) >= 2 else (None, None)

        bb, bs = get_vals("ทองคำแท่ง")
        ob, os = get_vals("ทองรูปพรรณ")
        
        txt_all = soup.get_text()
        m_time = re.search(r"เวลา\s?(\d{1,2}:\d{2})", txt_all)
        m_round = re.search(r"ครั้งที่\s?(\d+)", txt_all)
        
        if bs:
            return {
                "bar_buy": bb, "bar_sell": bs, "orn_buy": ob, "orn_sell": os,
                "times": int(m_round.group(1)) if m_round else None,
                "asof_time": m_time.group(1) if m_time else datetime.now(TZ).strftime("%H:%M")
            }
    except: pass
    return None

# ตัวจัดการหลัก: เจาะ Official ก่อน ถ้าไม่ได้ค่อยไป NamChiang
def fetch_master():
    # ลอง Official (Web สมาคม) ก่อน
    res = fetch_official()
    if res: return res, "Official"
    
    # ถ้าพัง ให้ลอง Nam Chiang
    res = fetch_namchiang()
    if res: return res, "NamChiang"
    
    return None, "Fail"

# ===== 5) MAIN APP Logic =====
st.markdown('<div class="brand">🏆 MeVGold</div><div class="sub">Thai Gold 96.5% • Official Data</div>', unsafe_allow_html=True)

# Fetch Data
live_data, source_name = fetch_master()
state = load_state()
prev = state

if not live_data:
    cur = state or {} 
    msg_status = "⚠️ เชื่อมต่อสมาคมไม่ได้ (แสดงราคาล่าสุด)"
else:
    cur = live_data
    msg_status = ""

# Time & Date
now = datetime.now(TZ)
t_str = cur.get("asof_time") or now.strftime("%H:%M")
times_val = cur.get("times")
times_str = f"ครั้งที่ {times_val}" if times_val else "ครั้งที่ -"

# Prices
cb, cs = cur.get("bar_buy") or 0, cur.get("bar_sell") or 0
ob, os = cur.get("orn_buy") or 0, cur.get("orn_sell") or 0
pb, ps = prev.get("bar_buy") or 0, prev.get("bar_sell") or 0

diff = int(cs - ps) if ps > 0 else 0

# Sticky Badge
badge_delta = prev.get("badge_delta", 0)
if live_data: 
    # อัปเดตป้ายเมื่อ ครั้งที่ เปลี่ยน หรือ ราคาเปลี่ยน
    if times_val != prev.get("times") or cs != ps: 
        badge_delta = diff
    
# Display Header
st.markdown(f'''
<div class="card">
  <div class="header">
    <div>{th_now(now)} • {times_str}</div>
    <div class="badge">{fmt_delta_for_badge(badge_delta)}</div>
  </div>
''', unsafe_allow_html=True)

if msg_status: st.warning(msg_status)

# Display Table
def p_ui(val, d):
    c = "up" if d>0 else ("down" if d<0 else "flat")
    return f'<div class="price {c}">{val:,.0f}</div>' if val else "-"

st.markdown(f'''
  <div class="row"><div class="cell head"></div><div class="cell head">รับซื้อ</div><div class="cell head">ขายออก</div></div>
  <div class="row">
    <div class="cell" style="text-align:left">ทองคำแท่ง</div>
    <div class="cell">{p_ui(cb, diff)}</div>
    <div class="cell">{p_ui(cs, diff)}</div>
  </div>
  <div class="row">
    <div class="cell" style="text-align:left">รูปพรรณ</div>
    <div class="cell"><span class="price flat">{ob:,.2f}</span></div>
    <div class="cell"><span class="price flat">{os:,.2f}</span></div>
  </div>
  <div class="footer">เวลาสมาคม: {t_str} น. • แหล่งข้อมูล: {source_name}</div>
</div>
''', unsafe_allow_html=True)

# ===== 6) NOTIFICATION & HISTORY =====
if live_data: # ทำงานเฉพาะเมื่อดึงข้อมูลสำเร็จ
    
    # Logic: แจ้งเตือนเมื่อราคาเปลี่ยน หรือ ระบบฟื้นตัวจาก Error
    is_recovery = (prev.get("bar_sell") in [0, None, "0"]) and (cs > 0)
    is_change = (cs != ps) and (ps > 0)
    
    if is_recovery or is_change:
        # Save State
        new_state = cur.copy()
        new_state["badge_delta"] = diff if is_change else 0
        save_state(new_state)
        
        # Append History
        append_hist({
            "date": now.strftime("%Y-%m-%d"), "time": now.strftime("%H:%M:%S"),
            "times": times_val, "buy_bar": cb, "sell_bar": cs, "buy_orn": ob, "sell_orn": os,
            "d_buy": 0, "d_sell": diff
        })
        
        # Telegram
        if TG_TOKEN:
            emo = UP_EMOJI if diff>0 else DOWN_EMOJI
            if is_recovery: emo = "⚠️(Connected)"
            txt = f"<b>สมาคมค้าทองคำ 96.5%</b>\n" \
                  f"รับซื้อ: <b>{cb:,.0f}</b>\n" \
                  f"ขายออก: <b>{cs:,.0f}</b> ({diff:+}) {emo}\n" \
                  f"{times_str} • {t_str} น."
            send_telegram(txt)

# History Table
with st.expander("📅 ประวัติวันนี้", expanded=False):
    try:
        df = pd.read_csv(HIST_FILE)
        df = df[df["date"] == now.strftime("%Y-%m-%d")].iloc[::-1]
        st.dataframe(df[["time","buy_bar","sell_bar","d_sell"]], hide_index=True)
    except: st.info("ยังไม่มีข้อมูล")
