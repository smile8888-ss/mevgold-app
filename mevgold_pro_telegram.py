# mevgold_pro_telegram.py — MeVGold 96.5% (Telegram Version)
# แก้ไขล่าสุด: เพิ่มระบบถอดรหัสภาษาไทย 2 ชั้น (UTF-8 และ CP874) + Debug Mode

import os, json, re, csv, requests
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

import streamlit as st
from bs4 import BeautifulSoup
import pandas as pd

# ===== 1) ต้องมาก่อนคำสั่ง st.* อื่นเสมอ =====
st.set_page_config(page_title="MeVGold — Thai Gold 96.5%", page_icon="🏆", layout="centered")

# ===== 2) meta/PWA + auto refresh =====
st.markdown("""
<link rel="manifest" href="static/manifest.json">
<link rel="apple-touch-icon" href="static/apple-touch-icon.png">
<link rel="icon" href="static/icon-192.png">
<meta name="theme-color" content="#F0C159">
<meta http-equiv="refresh" content="60">
<meta name="viewport" content="width=device-width, initial-scale=1">
""", unsafe_allow_html=True)

# ===== 3) CONFIG / CONST =====
TZ = ZoneInfo("Asia/Bangkok")
STATE_FILE = "last_gold.json"
HIST_FILE  = "history_today.csv"
SOURCE_URL = "https://www.goldtraders.or.th/default.aspx"
FETCH_TIMEOUT = 25  # เพิ่มเวลาเผื่อเว็บช้า

TG_TOKEN = str(st.secrets.get("TELEGRAM_BOT_TOKEN", "") or "")
TG_CHAT  = str(st.secrets.get("TELEGRAM_CHAT_ID", "") or "")

UP_EMOJI = "🟢⬆️"      
DOWN_EMOJI = "🔻⬇️"     

# ===== 4) STYLES (Mobile-first) =====
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Prompt:wght@500;600;700;800&display=swap');
:root{
  --gold1:#F8E08A; --gold2:#F0C159; --gold3:#E3AC3A; --line:rgba(255,255,255,.08);
  --radius-lg:18px; --radius-md:14px; --gap:10px;
}
html, body, .stApp{
  font-family:'Prompt',system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
  background: radial-gradient(130% 160% at 50% -40%, #121722 0%, #0b0e12 55%, #080a0e 100%);
  color:#eceff4;
}
.wrap{max-width:920px;margin:0 auto;padding:16px 12px 24px}

.brand{display:flex;gap:8px;align-items:center;justify-content:center;margin:6px 0 0}
.brand b{
  font-size:clamp(22px,7vw,36px);
  letter-spacing:-.2px;
  background:linear-gradient(92deg,var(--gold1),var(--gold2),var(--gold3));
  -webkit-background-clip:text;color:transparent;
}
.sub{color:#c9ced6;text-align:center;margin:.25rem 0 .5rem;font-size:clamp(11px,3.2vw,14px)}
.note{color:#aab1bb;text-align:center;margin-bottom:.25rem;font-size:clamp(10px,3vw,12px)}

.card{
  position:relative;border-radius:var(--radius-lg);border:1px solid var(--line);
  background:
    linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.02)),
    radial-gradient(120% 160% at 90% -30%, rgba(248,224,138,.10), transparent 50%);
  box-shadow:0 14px 36px rgba(0,0,0,.35), 0 0 0 1px rgba(255,255,255,.04) inset;
  overflow:hidden;
}

/* header – mobile */
.header{
  display:flex; flex-direction:row; align-items:center; justify-content:space-between;
  flex-wrap:wrap; gap:10px;
  padding:12px; border-bottom:1px solid var(--line);
  background:linear-gradient(180deg, rgba(248,224,138,.12), rgba(240,193,89,.08));
}
.header .left{display:flex; gap:8px; flex-wrap:wrap; align-items:center}
.status{margin-left:auto; display:flex; align-items:center}

.badge{
  display:inline-flex; align-items:center; gap:8px; font-weight:900;
  padding:6px 10px; border-radius:999px; font-size:clamp(13px,4vw,16px); line-height:1;
  color:#0b0e12; white-space:nowrap;
  background:linear-gradient(92deg,#ffe39a,#f6c663);
  border:1px solid rgba(248,224,138,.6);
  box-shadow:0 10px 28px rgba(240,193,89,.22), 0 0 0 1px rgba(255,255,255,.06) inset;
}

/* table */
.table{padding:10px}
.row{
  display:grid;
  grid-template-columns: 1.1fr 1fr 1fr;
  gap:var(--gap); margin-bottom:var(--gap);
}
.cell{
  background:linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.02));
  border:1px solid var(--line); border-radius:var(--radius-md);
  padding:12px; min-height:56px;
  box-shadow:0 6px 18px rgba(0,0,0,.25) inset;
}
.cell.head{
  background:linear-gradient(180deg, rgba(248,224,138,.12), rgba(240,193,89,.08));
  border:1px solid rgba(248,224,138,.35); text-align:center; font-weight:800;
  font-size:clamp(12px,3.6vw,14px)
}
.cell.right{text-align:right}
.tag{font-size:clamp(11px,3.3vw,13px);color:#cbd5e1}

.price{
  font-size:clamp(28px,8vw,44px); font-weight:900;
  background:linear-gradient(92deg,#F8E08A,#F0C159,#E3AC3A);
  -webkit-background-clip:text;color:transparent;text-shadow:0 1px 0 rgba(0,0,0,.35);
}
.price.up   { color:#16a34a; -webkit-text-fill-color:#16a34a; background:none; }
.price.down { color:#ef4444; -webkit-text-fill-color:#ef4444; background:none; }
.price.flat { color:#cbd5e1; -webkit-text-fill-color:#cbd5e1; background:none; }

.footer{
  display:flex;flex-direction:column;gap:6px;align-items:flex-start;
  padding:10px 12px 12px;border-top:1px solid var(--line);color:#d1d5db;
  font-size:clamp(11px,3.2vw,13px)
}
.footer b{font-weight:900}
hr.sep{border:none;height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.1),transparent);margin:12px 0}

/* desktop */
@media (min-width: 768px){
  .wrap{padding:18px 14px 28px}
  .header{flex-direction:row; align-items:center; justify-content:space-between; min-height:64px}
  .status{position:absolute;right:160px;top:50%;transform:translateY(-50%)}
  .footer{flex-direction:row;justify-content:space-between;align-items:center}
}
</style>
<div class="wrap">
""", unsafe_allow_html=True)

# ===== 5) HELPERS =====
TH_DOW   = ["วันจันทร์","วันอังคาร","วันพุธ","วันพฤหัสบดี","วันศุกร์","วันเสาร์","วันอาทิตย์"]
TH_MONTH = ["ม.ค.","ก.พ.","มี.ค.","เม.ย.","พ.ค.","มิ.ย.","ก.ค.","ส.ค.","ก.ย.","ต.ค.","พ.ย.","ธ.ค."]

def th_now(dt: datetime) -> str:
    return f"{TH_DOW[dt.weekday()]} {dt.day} {TH_MONTH[dt.month-1]} {dt.year+543} • {dt.strftime('%H:%M')} น."

def is_market_closed(now: datetime) -> bool:
    return (now.hour > 17) or (now.hour == 17 and now.minute >= 30)

def load_state():
    try:
        with open(STATE_FILE,"r",encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_state(d:dict):
    try:
        with open(STATE_FILE,"w",encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
    except:
        pass

STD_COLUMNS = ["date","time","times","buy_bar","sell_bar","buy_orn","sell_orn","d_buy","d_sell"]

def ensure_hist():
    # สร้างหรือซ่อมไฟล์ History
    if not os.path.exists(HIST_FILE):
        with open(HIST_FILE,"w",newline="",encoding="utf-8") as f:
            csv.writer(f).writerow(STD_COLUMNS)
        return
    
    # ตรวจสอบว่ามี Column ครบไหม
    try:
        df = pd.read_csv(HIST_FILE, dtype=str, on_bad_lines="skip")
        for col in STD_COLUMNS:
            if col not in df.columns:
                df[col] = "0"
        df[STD_COLUMNS].to_csv(HIST_FILE, index=False, encoding="utf-8")
    except:
        pass

def append_hist(row:dict):
    ensure_hist()
    with open(HIST_FILE,"a",newline="",encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=STD_COLUMNS).writerow(row)

def fmt_signed(n:int) -> str:
    if n > 0:  return f"+{n}"
    if n < 0:  return f"-{abs(n)}"
    return "0"

def fmt_delta_for_badge(n:int) -> str:
    if n > 0:  return f"▲ +{n}"
    if n < 0:  return f"▼ -{abs(n)}"
    return "— 0"

def send_telegram(text:str):
    if not (TG_TOKEN and TG_CHAT):
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            data={"chat_id": TG_CHAT, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
    except:
        pass

# ===== 6) FETCH (ULTRA ROBUST) =====
def fetch_assoc_raw():
    # เปลี่ยนเป้าหมาย: ไม่เข้าหน้าแรก (ที่หมุนติ้วๆ) 
    # แต่เข้าหน้า "ราคาทองคำประจำวัน" (ที่เป็นตาราง HTML โบราณ) แทน
    HIST_URL = "https://www.goldtraders.or.th/DailyPrices.aspx"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Cache-Control": "no-cache"
    }

    try:
        r = requests.get(HIST_URL, headers=headers, timeout=FETCH_TIMEOUT)
        r.raise_for_status()
        # หน้าตารางนี้มักใช้ utf-8 แต่กันเหนียวไว้
        r.encoding = r.apparent_encoding 
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        raise RuntimeError(f"Connect Error: {e}")

    # ค้นหาตาราง (Table)
    # ปกติหน้า History จะมีตารางใหญ่ๆ อยู่ตรงกลาง
    # เราจะหาตารางที่มีคำว่า "เวลา" หรือ "ครั้งที่" อยู่ในหัวตาราง
    target_table = None
    for table in soup.find_all("table"):
        if "ครั้งที่" in table.get_text() and "เวลา" in table.get_text():
            target_table = table
            break
    
    if not target_table:
         # เผื่อหาตารางไม่เจอ ลองหา row โดยตรง
         pass

    # ฟังก์ชันช่วยดึงตัวเลขจาก Cell
    def parse_num(txt):
        if not txt: return None
        clean = txt.replace(",", "").strip()
        try: return float(clean)
        except: return None

    # เริ่มแกะข้อมูลจาก "แถวแรก" ที่ไม่ใช่หัวตาราง (ข้อมูลล่าสุด)
    # โครงสร้างปกติ: วันที่ | เวลา | ครั้งที่ | แท่งรับซื้อ | แท่งขายออก | รูปพรรณรับซื้อ | รูปพรรณขายออก ...
    data = {
        "bar_buy": None, "bar_sell": None, 
        "orn_buy": None, "orn_sell": None, 
        "times": None, "asof_time": None
    }

    found_row = False
    
    # วนหาแถวข้อมูล (ข้ามแถวหัวข้อ)
    # เราจะหาแถวที่มี "ตัวเลขราคา" ครบๆ
    rows = soup.find_all("tr")
    for row in rows:
        cols = row.find_all("td")
        # ต้องมีมากกว่า 5 คอลัมน์ (วันที่, เวลา, ครั้งที่, ราคา4ตัว...)
        if len(cols) >= 8:
            # ลองเช็คว่าเป็นแถวข้อมูลจริงไหม (คอลัมน์ 3 ต้องเป็นราคา)
            test_price = parse_num(cols[3].get_text(strip=True))
            if test_price and test_price > 10000:
                # เจอแล้ว! นี่คือแถวข้อมูลล่าสุด (เพราะอยู่บนสุด)
                
                # [0]=วันที่, [1]=เวลา, [2]=ครั้งที่
                # [3]=แท่งรับซื้อ, [4]=แท่งขายออก
                # [5]=รูปพรรณรับซื้อ, [6]=รูปพรรณขายออก
                
                # ดึงเวลา
                raw_time = cols[1].get_text(strip=True) # เช่น 09:30
                data["asof_time"] = raw_time
                
                # ดึงครั้งที่
                raw_times = cols[2].get_text(strip=True)
                try: data["times"] = int(raw_times)
                except: data["times"] = None

                # ดึงราคา
                data["bar_buy"]  = parse_num(cols[3].get_text(strip=True))
                data["bar_sell"] = parse_num(cols[4].get_text(strip=True))
                data["orn_buy"]  = parse_num(cols[5].get_text(strip=True))
                data["orn_sell"] = parse_num(cols[6].get_text(strip=True))
                
                found_row = True
                break # เจอแถวบนสุด (ล่าสุด) แล้วหยุดเลย

    if not found_row or data["bar_sell"] is None:
        # Debug: ถ้าหาไม่เจอจริงๆ
        st.error("❌ หาตารางราคาในหน้า DailyPrices ไม่เจอ")
        raise RuntimeError("no_price_elements (Source: GTA History Page)")
    
    # Fallback เวลา ถ้าในตารางไม่มี
    if data["asof_time"] is None:
        data["asof_time"] = datetime.now(TZ).strftime("%H:%M")

    return data

def fetch_assoc_safe():
    status = {"source": "live", "message": ""}
    try:
        cur = fetch_assoc_raw()
        return cur, status
    except Exception as e:
        status["source"] = "cache"
        status["message"] = f"ดึงข้อมูลสดไม่ได้ ({e}) • แสดงราคาล่าสุดจากแคช"
        cur = load_state() or {}
        return cur, status

# ===== 7) MAIN UI =====
st.markdown('<div class="brand">🏆 <b>MeVGold</b></div>', unsafe_allow_html=True)
st.markdown('<div class="sub">Thai Gold 96.5% • จากสมาคมค้าทองคำ</div>', unsafe_allow_html=True)
st.markdown('<div class="note">อัปเดตอัตโนมัติทุก 1 นาที (โหลดทั้งหน้า)</div>', unsafe_allow_html=True)

cur, fetch_status = fetch_assoc_safe()
state = load_state() or {}
prev  = state

now = datetime.now(TZ)
date_txt  = th_now(now)

times_now = (cur or {}).get("times")
asof_time = (cur or {}).get("asof_time")
times_txt = f"ครั้งที่ {times_now}" if times_now else "ครั้งที่ –"
display_time = asof_time or now.strftime("%H:%M")

cur_buy   = float((cur or {}).get("bar_buy")  or 0)
cur_sell  = float((cur or {}).get("bar_sell") or 0)
prev_buy  = float((prev or {}).get("bar_buy",  cur_buy)  or 0)
prev_sell = float((prev or {}).get("bar_sell", cur_sell) or 0)

tick_buy  = int(round(cur_buy  - prev_buy))
tick_sell = int(round(cur_sell - prev_sell))

# ----- Sticky badge logic -----
prev_badge_times = prev.get("badge_times")
prev_badge_delta = prev.get("badge_delta")

if times_now is None:
    badge_delta_display = tick_sell
    badge_times_to_save = prev_badge_times
else:
    if prev_badge_times == times_now:
        badge_delta_display = prev_badge_delta if prev_badge_delta is not None else tick_sell
        badge_times_to_save = prev_badge_times
    else:
        badge_delta_display = tick_sell
        badge_times_to_save = times_now
if badge_delta_display is None:
    badge_delta_display = 0

# ----- CARD -----
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown(
    f"""
    <div class="header">
      <div class="left">
        <div class="pill">ประจำวันที่ {date_txt}</div>
        <div class="pill">{escape(times_txt)}</div>
      </div>
      <div class="status"><div class="badge">{escape(fmt_delta_for_badge(badge_delta_display))}</div></div>
      <div class="unit">บาทละ (บาท)</div>
    </div>
    """, unsafe_allow_html=True
)

if is_market_closed(now):
    st.info("🏁 สมาคมค้าทองคำปิดทำการแล้ว • แสดงราคาล่าสุดของวัน", icon="🏁")
if fetch_status["source"] == "cache" and fetch_status["message"]:
    st.warning("ℹ️ " + fetch_status["message"])

st.markdown('<div class="table">', unsafe_allow_html=True)
st.markdown(
    '<div class="row"><div class="cell head">96.5%</div>'
    '<div class="cell head">รับซื้อ</div>'
    '<div class="cell head">ขายออก</div></div>',
    unsafe_allow_html=True
)

def price_cell(v, tick):
    if v is None:
        return '<div class="cell right">–</div>'
    cls = "up" if tick>0 else ("down" if tick<0 else "flat")
    return f'<div class="cell right"><span class="price {cls}">{v:,.2f}</span></div>'

display_buy  = (cur or prev).get("bar_buy")  if (cur or prev) else None
display_sell = (cur or prev).get("bar_sell") if (cur or prev) else None
display_obuy = (cur or prev).get("orn_buy")  if (cur or prev) else None
display_osell= (cur or prev).get("orn_sell") if (cur or prev) else None

st.markdown(
    f'<div class="row"><div class="cell"><div class="tag">ทองคำแท่ง</div></div>'
    f'{price_cell(display_buy,  int(round((display_buy  or 0) - (prev_buy  if display_buy  is not None else 0))))}'
    f'{price_cell(display_sell, int(round((display_sell or 0) - (prev_sell if display_sell is not None else 0))))}</div>',
    unsafe_allow_html=True
)

def p_flat(v):
    return f'<div class="cell right"><span class="price flat">{v:,.2f}</span></div>' if v is not None else '<div class="cell right">–</div>'

st.markdown(
    f'<div class="row"><div class="cell"><div class="tag">ทองรูปพรรณ</div></div>'
    f'{p_flat(display_obuy)}{p_flat(display_osell)}</div>',
    unsafe_allow_html=True
)

st.markdown('</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="footer"><div>อัปเดตล่าสุด: <b>{now.strftime("%d/%m/%Y")} • {display_time} น.</b></div><div>{escape(times_txt)}</div></div>',
    unsafe_allow_html=True
)
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<hr class="sep">', unsafe_allow_html=True)

# ===== 8) HISTORY + TELEGRAM (NOT MODIFIED) =====
ensure_hist()

def seed_today_if_missing(cur_like, now):
    if not cur_like: return
    today = now.strftime("%Y-%m-%d")
    try:
        df = pd.read_csv(HIST_FILE, dtype=str, on_bad_lines="skip")
    except: return
    
    has_today = (not df.empty) and ("date" in df.columns) and (df["date"] == today).any()
    if not has_today:
        bb = cur_like.get("bar_buy");  bs = cur_like.get("bar_sell")
        ob = cur_like.get("orn_buy");  os = cur_like.get("orn_sell")
        append_hist({
            "date": today, "time": now.strftime("%H:%M:%S"),
            "times": cur_like.get("times",""),
            "buy_bar":  f"{(bb or 0):.2f}" if bb is not None else "",
            "sell_bar": f"{(bs or 0):.2f}" if bs is not None else "",
            "buy_orn":  f"{(ob or 0):.2f}" if ob is not None else "",
            "sell_orn": f"{(os or 0):.2f}" if os is not None else "",
            "d_buy":  "0", "d_sell": "0",
        })

seed_today_if_missing(cur or prev, now)

have_numbers_now  = (cur is not None) and (cur.get("bar_buy") is not None or cur.get("bar_sell") is not None)
have_numbers_prev = (prev is not None) and (prev.get("bar_buy") is not None or prev.get("bar_sell") is not None)
changed = have_numbers_now and have_numbers_prev and ((tick_buy != 0) or (tick_sell != 0))

if changed:
    append_hist({
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "times": times_now or "",
        "buy_bar":  f"{cur_buy:.2f}",
        "sell_bar": f"{cur_sell:.2f}",
        "buy_orn":  f"{(cur.get('orn_buy')  or 0):.2f}" if cur.get("orn_buy")  is not None else "",
        "sell_orn": f"{(cur.get('orn_sell') or 0):.2f}" if cur.get("orn_sell") is not None else "",
        "d_buy":  str(tick_buy),
        "d_sell": str(tick_sell),
    })
    if tick_sell != 0 and TG_TOKEN and TG_CHAT:
        arrow = UP_EMOJI if tick_sell > 0 else DOWN_EMOJI
        msg = (
            "<b>สมาคมค้าทองคำ อัปเดตราคา 96.5%</b>\n"
            f"รับซื้อ: <b>{escape(f'{cur_buy:,.0f}')}</b> ({fmt_signed(tick_buy)})\n"
            f"ขายออก: <b>{escape(f'{cur_sell:,.0f}')}</b> ({fmt_signed(tick_sell)}) {arrow}\n"
            f"{escape(times_txt)}  •  เวลา {display_time} น."
        )
        send_telegram(msg)

# ===== 9) SAVE STATE =====
if fetch_status["source"] == "live":
    new_state = dict(cur or {})
    new_state["badge_times"] = badge_times_to_save
    new_state["badge_delta"] = badge_delta_display
    save_state(new_state)

# ===== 10) HISTORY VIEW =====
with st.expander("📅 ประวัติวันนี้ (เฉพาะรอบที่มีการเปลี่ยนแปลง)", expanded=False):
    try:
        df = pd.read_csv(HIST_FILE, dtype=str, on_bad_lines="skip")
        today = now.strftime("%Y-%m-%d")
        df = df[df["date"] == today].copy()
        if df.empty:
            st.info("ยังไม่มีประวัติของวันนี้")
        else:
            df["_dt"] = pd.to_datetime(df["date"]+" "+df["time"], errors="coerce")
            df = df.sort_values("_dt", ascending=False)
            def sign_only(x):
                try:
                    n = int(float(x))
                    return f"+{n}" if n>0 else (f"-{abs(n)}" if n<0 else "0")
                except: return "0"
            df["สถานะ"] = df["d_sell"].apply(sign_only)
            st.dataframe(df[["time","buy_bar","sell_bar","สถานะ"]], hide_index=True)
    except:
        pass
