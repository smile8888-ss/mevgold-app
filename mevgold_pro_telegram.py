# mevgold_pro_telegram.py — MeVGold 96.5% (stable + history seed + TG alert)
# • Render ได้แม้ดึงเว็บสมาคมไม่ได้/ปิดทำการ (ใช้แคช/placeholder)
# • Soft auto-refresh 60s
# • Badge ▲/▼/คงที่
# • Telegram: ส่งเมื่อ “ขายออก” เปลี่ยนจริงเท่านั้น
# • HISTORY: seed แถวแรกของวัน + migrate schema
# • เวลาไทย Asia/Bangkok และถ้ามี “เวลา ณ สมาคม” จะอ้างอิงเวลานั้นเป็นหลัก

import os, json, re, csv, requests
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

import streamlit as st
from bs4 import BeautifulSoup
import pandas as pd

# ------------------ CONFIG ------------------
st.set_page_config(page_title="MeVGold — Thai Gold 96.5%", page_icon="🏆", layout="centered")
st.markdown('<meta http-equiv="refresh" content="60">', unsafe_allow_html=True)

TZ = ZoneInfo("Asia/Bangkok")

STATE_FILE = "last_gold.json"
HIST_FILE  = "history_today.csv"
SOURCE_URL = "https://www.goldtraders.or.th/default.aspx"
FETCH_TIMEOUT = 20  # seconds

# อ่าน secrets แบบปลอดภัย
TG_TOKEN = str(st.secrets.get("TELEGRAM_BOT_TOKEN", "") or "")
TG_CHAT  = str(st.secrets.get("TELEGRAM_CHAT_ID", "") or "")

# Emojis สำหรับข้อความ Telegram
UP_EMOJI = "🟢⬆️"     # ขึ้น = เขียว
DOWN_EMOJI = "🔻⬇️"    # ลง  = แดง

# ------------------ STYLES ------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Prompt:wght@500;600;700;800&display=swap');
:root{ --gold1:#F8E08A; --gold2:#F0C159; --gold3:#E3AC3A; --line:rgba(255,255,255,.08); }
html, body, .stApp{ font-family:'Prompt',system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
  background: radial-gradient(130% 160% at 50% -40%, #121722 0%, #0b0e12 55%, #080a0e 100%); color:#eceff4; }
.wrap{max-width:980px;margin:0 auto;padding:18px 14px 28px}
.brand{display:flex;gap:10px;align-items:center;justify-content:center;margin:6px 0 2px}
.brand b{font-size:36px;letter-spacing:-.2px;background:linear-gradient(92deg,var(--gold1),var(--gold2),var(--gold3));
  -webkit-background-clip:text;color:transparent;}
.sub{color:#c9ced6;text-align:center;margin-bottom:8px;font-size:14px}
.note{color:#aab1bb;text-align:center;margin-bottom:6px;font-size:12px}
.card{position:relative;border-radius:22px;border:1px solid var(--line);
  background:linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.02)),
             radial-gradient(120% 160% at 90% -30%, rgba(248,224,138,.10), transparent 50%);
  box-shadow:0 16px 42px rgba(0,0,0,.35), 0 0 0 1px rgba(255,255,255,.04) inset; overflow:hidden;}
.header{position:relative; display:flex; align-items:center; justify-content:space-between;
  padding:14px 16px; border-bottom:1px solid var(--line);
  background:linear-gradient(180deg, rgba(248,224,138,.12), rgba(240,193,89,.08)); min-height:64px;}
.header .left{display:flex; gap:12px; align-items:center; flex-wrap:wrap}
.pill{color:#0b0e12;font-weight:800;border-radius:999px;padding:8px 12px;background:linear-gradient(92deg,#ffe39a,#f6c663);white-space:nowrap}
.unit{color:#0b0e12;font-size:12px;font-weight:800;border-radius:999px;padding:8px 12px;background:linear-gradient(92deg,#f6c663,#ffe39a);white-space:nowrap}
.status{position:absolute;right:160px;top:50%;transform:translateY(-50%);pointer-events:none}
.badge{display:inline-flex; align-items:center; gap:8px; font-weight:900; padding:6px 12px; border-radius:999px; font-size:16px; line-height:1;
  color:#0b0e12; white-space:nowrap; background:linear-gradient(92deg,#ffe39a,#f6c663);
  border:1px solid rgba(248,224,138,.6); box-shadow:0 10px 28px rgba(240,193,89,.22), 0 0 0 1px rgba(255,255,255,.06) inset;}
.table{padding:10px 12px 12px}
.row{display:grid;grid-template-columns:1.1fr 1fr 1fr;gap:10px;margin-bottom:10px}
.cell{background:linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.02));
  border:1px solid var(--line); border-radius:16px; padding:14px 16px; min-height:58px; box-shadow:0 6px 18px rgba(0,0,0,.25) inset;}
.cell.head{background:linear-gradient(180deg, rgba(248,224,138,.12), rgba(240,193,89,.08));
  border:1px solid rgba(248,224,138,.35); text-align:center; font-weight:800}
.cell.right{text-align:right}
.tag{font-size:13px;color:#cbd5e1}
.price{font-size:38px; font-weight:900;
  background:linear-gradient(92deg,#F8E08A,#F0C159,#E3AC3A); -webkit-background-clip:text;color:transparent;text-shadow:0 1px 0 rgba(0,0,0,.35);}
.price.up{ color:#16a34a; -webkit-text-fill-color:#16a34a; background:none; }
.price.down{ color:#ef4444; -webkit-text-fill-color:#ef4444; background:none; }
.price.flat{ color:#cbd5e1; -webkit-text-fill-color:#cbd5e1; background:none; }
.footer{display:flex;justify-content:space-between;align-items:center;padding:10px 14px 12px;border-top:1px solid var(--line);color:#d1d5db;font-size:13px}
.footer b{font-weight:900}
hr.sep{border:none;height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.1),transparent);margin:14px 0}
</style>
<div class="wrap">
""", unsafe_allow_html=True)

# ------------------ HELPERS ------------------
TH_DOW   = ["วันจันทร์","วันอังคาร","วันพุธ","วันพฤหัสบดี","วันศุกร์","วันเสาร์","วันอาทิตย์"]
TH_MONTH = ["ม.ค.","ก.พ.","มี.ค.","เม.ย.","พ.ค.","มิ.ย.","ก.ค.","ส.ค.","ก.ย.","ต.ค.","พ.ย.","ธ.ค."]

def th_now(dt: datetime) -> str:
    # dt เป็น timezone-aware (Asia/Bangkok)
    return f"{TH_DOW[dt.weekday()]} {dt.day} {TH_MONTH[dt.month-1]} {dt.year+543} • {dt.strftime('%H:%M')} น."

def is_market_closed(now: datetime) -> bool:
    """สมาคมโดยทั่วไปอัปเดตราว 09:00–17:30 → หลัง 17:30 ถือว่าปิด"""
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

# schema ของ history
STD_COLUMNS = ["date","time","times","buy_bar","sell_bar","buy_orn","sell_orn","d_buy","d_sell"]

def migrate_history_file():
    """ทำให้ history_today.csv เข้ารูปมาตรฐานเสมอ (เติมคอลัมน์ที่ขาดด้วยค่า 0/ว่าง)"""
    if not os.path.exists(HIST_FILE):
        with open(HIST_FILE,"w",newline="",encoding="utf-8") as f:
            csv.writer(f).writerow(STD_COLUMNS)
        return
    try:
        df = pd.read_csv(HIST_FILE, dtype=str, on_bad_lines="skip")
    except Exception:
        with open(HIST_FILE,"w",newline="",encoding="utf-8") as f:
            csv.writer(f).writerow(STD_COLUMNS)
        return
    for col in STD_COLUMNS:
        if col not in df.columns:
            df[col] = "" if col in ["times","buy_orn","sell_orn"] else "0"
    df = df[STD_COLUMNS]
    df.to_csv(HIST_FILE, index=False, encoding="utf-8")

def ensure_hist():
    migrate_history_file()
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    try:
        df = pd.read_csv(HIST_FILE, dtype=str, on_bad_lines="skip")
        if df.empty or "date" not in df.columns or not (df["date"] == today).any():
            with open(HIST_FILE,"w",newline="",encoding="utf-8") as f:
                csv.writer(f).writerow(STD_COLUMNS)
    except Exception:
        with open(HIST_FILE,"w",newline="",encoding="utf-8") as f:
            csv.writer(f).writerow(STD_COLUMNS)

def append_hist(row:dict):
    ensure_hist()
    with open(HIST_FILE,"a",newline="",encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=STD_COLUMNS).writerow(row)

def fmt_signed(n:int) -> str:
    if n > 0:  return f"+{n}"
    if n < 0:  return f"-{abs(n)}"
    return "0"

def fmt_delta_for_badge(n:int) -> str:
    if n > 0:  return f"▲ {fmt_signed(n)}"
    if n < 0:  return f"▼ {fmt_signed(n)}"
    return "— 0"

def send_telegram(text:str):
    if not (TG_TOKEN and TG_CHAT):
        return
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                      data={"chat_id": TG_CHAT, "text": text, "parse_mode": "HTML"},
                      timeout=10)
    except:
        pass

# ------------------ FETCH (with graceful fallback) ------------------
def fetch_assoc_raw():
    """ดึงข้อมูลจากเว็บสมาคม (อาจโยน Exception ถ้าเน็ต/โครงสร้างเพจมีปัญหา)"""
    r = requests.get(SOURCE_URL, headers={"User-Agent":"Mozilla/5.0 (MevGoldBot)"}, timeout=FETCH_TIMEOUT)
    r.raise_for_status()
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "lxml")  # ใช้ lxml เร็ว/ทนกว่า

    def num(sel):
        t = soup.select_one(sel)
        txt = t.get_text(strip=True) if t else ""
        if not txt:
            return None
        try:
            return float(txt.replace(",",""))
        except:
            return None

    data = {
        "bar_buy":  num("#DetailPlace_uc_goldprices1_lblBLBuy"),
        "bar_sell": num("#DetailPlace_uc_goldprices1_lblBLSell"),
        "orn_buy":  num("#DetailPlace_uc_goldprices1_lblOMBuy"),
        "orn_sell": num("#DetailPlace_uc_goldprices1_lblOMSell"),
        "times":    None,
        "asof_time": None,  # เวลา ณ สมาคม ถ้ามี
    }

    ts = soup.select_one("#DetailPlace_uc_goldprices1_lblAsTime")
    if ts:
        ts_text = ts.get_text(strip=True)
        m = re.search(r"ครั้งที่\s?(\d+)", ts_text)
        if m:
            try: data["times"] = int(m.group(1))
            except: data["times"] = None
        m2 = re.search(r"เวลา\s?(\d{1,2}:\d{2})", ts_text)
        if m2:
            data["asof_time"] = m2.group(1)

    return data

def fetch_assoc_safe():
    """
    พยายามดึงข้อมูลจากสมาคม:
      - ถ้าได้ตัวเลข → ใช้งานเลย
      - ถ้าดึงไม่ได้/เพจเปลี่ยน/ไม่มีตัวเลข → ใช้แคช STATE_FILE (ถ้ามี)
      - ถ้าไม่มีแคชเลย → คืน dict เปล่าเพื่อให้โชว์ placeholder
    พร้อมส่ง flag อธิบายสถานะให้ UI
    """
    status = {"source": "live", "message": ""}
    cur = None
    try:
        cur = fetch_assoc_raw()
        if cur["bar_buy"] is None and cur["bar_sell"] is None:
            raise RuntimeError("no_price_elements")
    except Exception as e:
        status["source"] = "cache"
        status["message"] = f"ดึงข้อมูลสดไม่ได้ ({e}) • แสดงราคาล่าสุดจากแคช"
        cur = load_state() or {"bar_buy": None, "bar_sell": None, "orn_buy": None, "orn_sell": None, "times": None, "asof_time": None}
    return cur, status

# ------------------ MAIN ------------------
st.markdown('<div class="brand">🏆 <b>MeVGold</b></div>', unsafe_allow_html=True)
st.markdown('<div class="sub">Thai Gold 96.5% • จากสมาคมค้าทองคำ</div>', unsafe_allow_html=True)
st.markdown('<div class="note">อัปเดตอัตโนมัติทุก 1 นาที (โหลดทั้งหน้า)</div>', unsafe_allow_html=True)

# ดึงข้อมูล (มี fallback)
cur, fetch_status = fetch_assoc_safe()
prev = load_state()
if cur:  # บันทึกเฉพาะกรณีมี dict (แม้บางฟิลด์จะ None)
    save_state(cur)

now = datetime.now(TZ)
date_txt  = th_now(now)
times_txt = f"ครั้งที่ {cur.get('times')}" if (cur and cur.get("times")) else "ครั้งที่ –"
asof_time = (cur or {}).get("asof_time")
display_time = asof_time or now.strftime("%H:%M")  # ให้เวลาสมาคมเป็นหลัก

# Δ เทียบ state (กัน None)
cur_buy   = float((cur or {}).get("bar_buy")  or 0)
cur_sell  = float((cur or {}).get("bar_sell") or 0)
prev_buy  = float((prev or {}).get("bar_buy",  cur_buy)  or 0)
prev_sell = float((prev or {}).get("bar_sell", cur_sell) or 0)

tick_buy  = int(round(cur_buy  - prev_buy))
tick_sell = int(round(cur_sell - prev_sell))

# ------------------ CARD ------------------
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown(
    f"""
    <div class="header">
      <div class="left">
        <div class="pill">ประจำวันที่ {date_txt}</div>
        <div class="pill">{escape(times_txt)}</div>
      </div>
      <div class="status"><div class="badge">{escape(fmt_delta_for_badge(tick_sell))}</div></div>
      <div class="unit">บาทละ (บาท)</div>
    </div>
    """, unsafe_allow_html=True
)

# แถบแจ้งสถานะตลาด/การดึงข้อมูล
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

# กำหนดค่าที่จะแสดง (ถ้ายังไม่เคยมีข้อมูลเลยให้เป็น None เพื่อโชว์ "–")
display_buy  = None if (cur is None and not prev) else ((cur or prev).get("bar_buy"))
display_sell = None if (cur is None and not prev) else ((cur or prev).get("bar_sell"))
display_obuy = (cur or prev).get("orn_buy")  if (cur or prev) else None
display_osell= (cur or prev).get("orn_sell") if (cur or prev) else None

st.markdown(
    f'<div class="row"><div class="cell"><div class="tag">ทองคำแท่ง</div></div>'
    f'{price_cell(display_buy, tick_buy)}{price_cell(display_sell, tick_sell)}</div>',
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

# ------------------ HISTORY + TELEGRAM ------------------
ensure_hist()

def seed_today_if_missing(cur_like, now):
    """ถ้าวันนี้ยังไม่มีแถวในประวัติ ให้ seed 1 แถว (Δ=0) เพื่อไม่ให้หน้า 'ว่าง' """
    if not cur_like:  # ไม่มีข้อมูลอะไรเลยไม่ seed
        return
    today = now.strftime("%Y-%m-%d")
    try:
        df = pd.read_csv(HIST_FILE, dtype=str, on_bad_lines="skip")
    except Exception:
        return
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

# บันทึกเฉพาะเมื่อมีตัวเลขจริงทั้งก่อนและหลัง
have_numbers_now  = (cur is not None) and (cur.get("bar_buy") is not None or cur.get("bar_sell") is not None)
have_numbers_prev = (prev is not None) and (prev.get("bar_buy") is not None or prev.get("bar_sell") is not None)
changed = have_numbers_now and have_numbers_prev and ((tick_buy != 0) or (tick_sell != 0))

if changed:
    append_hist({
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "times": cur.get("times",""),
        "buy_bar":  f"{cur_buy:.2f}",
        "sell_bar": f"{cur_sell:.2f}",
        "buy_orn":  f"{(cur.get('orn_buy')  or 0):.2f}" if cur.get("orn_buy")  is not None else "",
        "sell_orn": f"{(cur.get('orn_sell') or 0):.2f}" if cur.get("orn_sell") is not None else "",
        "d_buy":  str(tick_buy),
        "d_sell": str(tick_sell),
    })

    # Telegram เฉพาะเมื่อ "ขายออก" เปลี่ยนจริง
    if tick_sell != 0 and TG_TOKEN and TG_CHAT:
        arrow = UP_EMOJI if tick_sell > 0 else DOWN_EMOJI
        msg = (
            "<b>สมาคมค้าทองคำ อัปเดตราคา 96.5%</b>\n"
            f"รับซื้อ: <b>{escape(f'{cur_buy:,.0f}')}</b> ({fmt_signed(tick_buy)})\n"
            f"ขายออก: <b>{escape(f'{cur_sell:,.0f}')}</b> ({fmt_signed(tick_sell)}) {arrow}\n"
            f"{escape(times_txt)}  •  เวลา {display_time} น."
        )
        send_telegram(msg)

# ประวัติวันนี้ (เฉพาะรอบที่มีเปลี่ยนแปลง)
with st.expander("📅 ประวัติวันนี้ (เฉพาะรอบที่มีการเปลี่ยนแปลง)", expanded=False):
    try:
        df = pd.read_csv(HIST_FILE, dtype=str, on_bad_lines="skip")
        if df.empty or "date" not in df.columns:
            st.info("ยังไม่มีประวัติของวันนี้")
        else:
            today = now.strftime("%Y-%m-%d")
            df = df[df["date"] == today].copy()
            if df.empty:
                st.info("ยังไม่มีประวัติของวันนี้")
            else:
                for col in ["time","buy_bar","sell_bar","d_sell"]:
                    if col not in df.columns:
                        df[col] = "0" if col == "d_sell" else ""
                df["_dt"] = pd.to_datetime(df["date"]+" "+df["time"], errors="coerce")
                df = df.sort_values("_dt", ascending=False)
                def sign_only(x):
                    try:
                        n = int(float(x))
                        return f"+{n}" if n>0 else (f"-{abs(n)}" if n<0 else "0")
                    except:
                        return "0"
                df["สถานะ (บาท)"] = df["d_sell"].apply(sign_only)
                df = df.rename(columns={"date":"วันที่","time":"เวลา","buy_bar":"ราคาซื้อ","sell_bar":"ราคาขาย"})
                st.dataframe(df[["วันที่","เวลา","ราคาซื้อ","ราคาขาย","สถานะ (บาท)"]], hide_index=True)
    except Exception as e:
        st.info(f"อ่านประวัติไม่ได้: {e}")

st.markdown("</div>", unsafe_allow_html=True)
