# mevgold_pro_telegram.py — MeVGold 96.5% (The Avenger Edition: Multi-Source)
# แก้ไขล่าสุด: เรียงลำดับการดึงข้อมูลใหม่ (Nam Chiang -> Official -> Sanook) เพื่อหนีการบล็อก
# Notification Logic: คงเดิม 100% (เตือนเมื่อเปลี่ยน / เตือนเมื่อระบบฟื้นคืนชีพ)

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
FETCH_TIMEOUT = 15 # ลดเวลา timeout ต่อเว็บลงหน่อย จะได้วนครบไวๆ

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
def th_now(dt): return f"{dt.day} {TH_MONTH[dt.month-1]} {dt.year+543} • {dt.strftime('%H:%M')} น."
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

# ===== 4) THE AVENGER FETCHERS (3 Sources) =====

# --- Source 1: Nam Chiang (ห้างทองนำเชียง) ---
# ข้อดี: HTML บ้านๆ โหลดไว ไม่บล็อกบอท
def fetch_namchiang():
    try:
        r = requests.get("http://www.namchiang.com/th/", headers={"User-Agent":"Mozilla/5.0"}, timeout=FETCH_TIMEOUT)
        r.encoding = "cp874" # เว็บนี้ใช้ภาษาไทยเก่า
        soup = BeautifulSoup(r.text, "html.parser")
        
        # ค้นหาตารางที่มีคำว่า "ทองคำแท่ง"
        # โครงสร้าง: <td>ทองคำแท่ง 96.5%</td> ... <td>26,000</td> ... <td>26,100</td>
        def get_vals(label):
            # หา td ที่มีคำค้นหา
            tag = soup.find("td", string=re.compile(label))
            if not tag: return None, None
            # หา td ถัดไปเรื่อยๆ จนกว่าจะเจอตัวเลข
            nums = []
            curr = tag.find_next("td")
            while curr and len(nums) < 2:
                txt = curr.get_text(strip=True).replace(",","")
                if txt.isdigit() or (txt.replace(".","").isdigit() and float(txt) > 1000):
                    nums.append(float(txt))
                curr = curr.find_next("td")
            return (nums[0], nums[1]) if len(nums) >= 2 else (None, None)

        bb, bs = get_vals("ทองคำแท่ง")
        ob, os = get_vals("ทองรูปพรรณ")
        
        # หาเวลา
        txt_all = soup.get_text()
        m_time = re.search(r"เวลา\s?(\d{1,2}:\d{2})", txt_all)
        m_round = re.search(r"ครั้งที่\s?(\d+)", txt_all)
        
        if bs:
            return {
                "bar_buy": bb, "bar_sell": bs, "orn_buy": ob, "orn_sell": os,
                "times": int(m_round.group(1)) if m_round else None,
                "asof_time": m_time.group(1) if m_time else datetime.now(TZ).strftime("%H:%M")
            }
    except Exception as e:
        print(f"NamChiang Failed: {e}")
    return None

# --- Source 2: Official Association (Next.js JSON) ---
# ข้อดี: ข้อมูลต้นทาง 100% (ถ้าไม่โดนบล็อก)
def fetch_official():
    try:
        r = requests.get("https://www.goldtraders.or.th/", headers={"User-Agent":"Mozilla/5.0"}, timeout=FETCH_TIMEOUT)
        soup = BeautifulSoup(r.text, "html.parser")
        script = soup.find("script", id="__NEXT_DATA__")
        if script:
            data = json.loads(script.string)
            # (Logic เดิมที่เคยใช้ได้ผล)
            def find_key(d, k_tgt):
                if isinstance(d, dict):
                    for k,v in d.items():
                        if k.lower()==k_tgt.lower(): return v
                        r = find_key(v, k_tgt)
                        if r: return r
                elif isinstance(d, list):
                    for i in d:
                        r = find_key(i, k_tgt)
                        if r: return r
            
            def f(k): 
                v = find_key(data, k)
                return float(str(v).replace(",","")) if v else None
                
            bs = f("blSell")
            if bs:
                raw_d = str(find_key(data, "updateDate") or "")
                mt = re.search(r"(\d{1,2}:\d{2})", raw_d)
                mr = re.search(r"ครั้งที่\s?(\d+)", str(find_key(data,"round") or ""))
                return {
                    "bar_buy": f("blBuy"), "bar_sell": bs, "orn_buy": f("omBuy"), "orn_sell": f("omSell"),
                    "times": int(mr.group(1)) if mr else None,
                    "asof_time": mt.group(1) if mt else datetime.now(TZ).strftime("%H:%M")
                }
    except Exception as e:
        print(f"Official Failed: {e}")
    return None

# --- Source 3: Sanook Money (Fallback สุดท้าย) ---
# ข้อดี: เว็บใหญ่ ไม่ล่มง่าย
def fetch_sanook():
    try:
        r = requests.get("https://money.sanook.com/gold/", headers={"User-Agent":"Mozilla/5.0"}, timeout=FETCH_TIMEOUT)
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        
        def get_row(lbl):
            tag = soup.find(string=re.compile(lbl))
            if tag:
                row = tag.find_parent("tr")
                nums = [float(x.get_text().replace(",","")) for x in row.find_all("td") if re.match(r"[\d,]+", x.get_text()) and float(x.get_text().replace(",","")) > 1000]
                if len(nums)>=2: return sorted(nums)[0], sorted(nums)[1] # buy, sell
            return None, None

        bb, bs = get_row("ทองคำแท่ง")
        ob, os = get_row("ทองรูปพรรณ")
        
        # เวลาของ Sanook มักอยู่ใน h3 หรือ span
        txt = soup.get_text()
        mt = re.search(r"เวลา\s?(\d{1,2}:\d{2})", txt)
        mr = re.search(r"ครั้งที่\s?(\d+)", txt)
        
        if bs:
            return {
                "bar_buy": bb, "bar_sell": bs, "orn_buy": ob, "orn_sell": os,
                "times": int(mr.group(1)) if mr else None,
                "asof_time": mt.group(1) if mt else datetime.now(TZ).strftime("%H:%M")
            }
    except Exception as e:
        print(f"Sanook Failed: {e}")
    return None

# ตัวจัดการหลัก: ลอง 1 -> 2 -> 3
def fetch_master():
    res = fetch_namchiang()
    if res: return res, "live (NamChiang)"
    
    res = fetch_official()
    if res: return res, "live (Official)"
    
    res = fetch_sanook()
    if res: return res, "live (Sanook)"
    
    return None, "fail"

# ===== 5) MAIN APP Logic =====
st.markdown('<div class="brand">🏆 MeVGold</div><div class="sub">Thai Gold 96.5% • อัปเดตอัตโนมัติ</div>', unsafe_allow_html=True)

# Fetch
live_data, source_status = fetch_master()
state = load_state()
prev = state

# ถ้าดึงสดไม่ได้ ให้ใช้ค่าเก่า (แต่แจ้งเตือน)
if not live_data:
    cur = state or {} # ถ้าไม่มี state เลย ก็ว่าง
    msg_status = "⚠️ ดึงข้อมูลไม่ได้ (ทุกแหล่ง) • แสดงราคาล่าสุด"
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

# Sticky Badge Logic
badge_delta = prev.get("badge_delta", 0)
if live_data: # ถ้าดึงสดได้ ค่อยอัปเดต Badge
    if times_val != prev.get("times"): # รอบเปลี่ยน
        badge_delta = diff
    # ถ้ารอบเท่าเดิม ใช้ delta เดิม

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
  <div class="footer">เวลาสมาคม: {t_str} น.</div>
</div>
''', unsafe_allow_html=True)

# ===== 6) NOTIFICATION & HISTORY =====
if live_data: # ทำงานเฉพาะเมื่อดึงข้อมูลสำเร็จ
    
    # 1. เช็ค Recovery (ของเดิมพัง ของใหม่มา)
    is_recovery = (prev.get("bar_sell") in [0, None, "0"]) and (cs > 0)
    # 2. เช็คราคาเปลี่ยน
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
            if is_recovery: emo = "⚠️(ระบบฟื้น)"
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
