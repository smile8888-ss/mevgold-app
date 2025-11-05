# mevgold_pro_line.py — MeVGold PRO (LINE Alerts)
# - อัปเดตทุก 1 วินาที (UI refresh)
# - แจ้งเตือนผ่าน LINE Notify เฉพาะเมื่อสมาคมฯ "ประกาศใหม่" (ครั้งที่/ราคาเปลี่ยน)
# - คูลดาวน์ 2 นาที กันสแปม
# - แสดง XAU/USD, USD/THB, และคำนวณทอง 1 บาท (96.5%)
# - เก็บสถานะลง last_gold.json และบันทึกประวัติลง history_today.csv

import os, json, csv, re, requests, traceback
from datetime import datetime, timedelta
import streamlit as st
from bs4 import BeautifulSoup
import pandas as pd

# ───────────────────────── PAGE CONFIG ─────────────────────────
st.set_page_config(page_title="MeVGold Pro — LINE Alerts", page_icon="🥇", layout="centered")

# ───────────────────────── SETTINGS ────────────────────────────
STATE_FILE   = "last_gold.json"
HIST_FILE    = "history_today.csv"

# คูลดาวน์ระหว่างการแจ้งเตือน (นาที)
COOLDOWN_MIN = 2
# cap การแจ้งเตือน/วัน (กันลูป)
MAX_ALERTS_PER_DAY = 30

# ───────────────────────── SECRETS / INPUT ─────────────────────
# วิธีใส่ LINE TOKEN:
# 1) แนะนำเก็บใน Streamlit Secrets: LINE_NOTIFY_TOKEN="token"
# 2) หรือพิมพ์ใน Sidebar (จะไม่ถูกบันทึกถาวร)
LINE_TOKEN_SECRET = st.secrets.get("LINE_NOTIFY_TOKEN", "")
with st.sidebar:
    st.header("🔔 LINE Notify")
    token_in = st.text_input("ใส่ LINE Notify Token (ถ้าไม่ใช้ Secrets)", type="password", value="")
    LINE_TOKEN = token_in.strip() or LINE_TOKEN_SECRET
    if LINE_TOKEN:
        st.success("พร้อมส่งแจ้งเตือนผ่าน LINE ✅")
    else:
        st.info("กรุณาใส่ LINE Notify Token เพื่อให้แจ้งเตือนได้")

# ───────────────────────── STYLE ───────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Prompt:wght@500;600;700;800&display=swap');

:root{
  --bg1:#fffef9; --bg2:#faf8f3; --ink:#111; --muted:#788095; --line:#E9EBF3;
  --gold1:#FAD961; --gold2:#F7B733; --card:#ffffff;
}
html,body,.stApp{
  background: radial-gradient(140% 160% at 50% -40%, var(--bg1) 0%, var(--bg2) 100%);
  color:var(--ink); font-family:'Prompt',system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
}
.main-wrap{max-width:780px;margin:0 auto;padding:10px 16px 22px;}
.logo{ text-align:center;font-size:42px;font-weight:800; letter-spacing:-.4px; margin:8px 0 4px;
  background:linear-gradient(90deg,var(--gold1),var(--gold2)); -webkit-background-clip:text; color:transparent;}
.subtitle{ text-align:center;color:var(--muted);font-size:14px;margin-bottom:14px;}

.toprow{display:flex;gap:8px;justify-content:space-between;align-items:center;margin:0 0 6px;}
.small{color:#8b90a1;font-size:12px;}

.pricebox{background:var(--card);border:2px solid rgba(247,183,51,.35);border-radius:20px;
  box-shadow:0 6px 18px rgba(247,183,51,.12);padding:20px 16px 12px;margin:10px auto 16px;text-align:center;}
.price-title{color:#000;font-weight:800;font-size:16px;margin-bottom:4px;}
.price-main{font-size:60px;font-weight:900;margin:-2px 0 6px;}
.pill{display:inline-flex;align-items:center;gap:6px;border-radius:999px;border:1px solid var(--line);
  padding:6px 12px;font-size:13px;color:#444;background:#F6F7FB;}

.kv-wrap{display:flex;gap:16px;flex-wrap:wrap;justify-content:center;margin:10px auto 4px;}
.kv{flex:1 1 320px;background:var(--card);border-radius:16px;box-shadow:0 6px 14px rgba(0,0,0,.05);
  padding:14px 18px 16px;text-align:center;border:1px solid var(--line);}
.kv label{display:block;font-size:13px;color:var(--muted);margin-bottom:6px;}
.kv b{font-size:28px;color:#000;}

.grid-3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:10px 0 4px}
@media(max-width:720px){.grid-3{grid-template-columns:1fr;}}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px 16px;
  box-shadow:0 6px 14px rgba(0,0,0,.05); text-align:center;}
.card h4{margin:0 0 6px 0;font-size:14px;color:#8b90a1;}
.card .v{font-size:22px;font-weight:800;}

.divider{height:1px;background:var(--line);width:min(760px,92%);margin:12px auto;}
.meta{text-align:center;color:var(--muted);font-size:13px;margin-top:6px;}
.btn-center{text-align:center;margin-top:10px;}
.btn-main{background:linear-gradient(90deg,var(--gold1),var(--gold2))!important;color:#222!important;
  border:none!important;font-weight:800!important;border-radius:12px!important;height:42px!important;padding:0 22px!important;
  box-shadow:0 4px 10px rgba(247,183,51,.25);}
.footer{text-align:center;color:#8B90A1;font-size:12px;margin-top:14px;}
.note{font-size:12px;color:#8b90a1;text-align:center;margin-top:6px;}
</style>
<div class="main-wrap">
""", unsafe_allow_html=True)

# ───────────────────────── UTIL: STATE & HISTORY ─────────────────────────
def load_state():
    try: return json.load(open(STATE_FILE,"r",encoding="utf-8"))
    except: return {}

def save_state(data:dict):
    try:
        json.dump(data, open(STATE_FILE,"w",encoding="utf-8"), ensure_ascii=False)
    except Exception:
        pass

def append_history(row):
    try:
        is_new = not os.path.exists(HIST_FILE)
        with open(HIST_FILE,"a",newline="",encoding="utf-8") as f:
            w = csv.writer(f)
            if is_new:
                w.writerow(["date","time","buy","sell","xauusd","usdthb","calc_baht96"])
            w.writerow(row)
    except Exception:
        pass

# ───────────────────────── FETCHERS ──────────────────────────────────────
def fetch_gold_thai():
    """ราคาทองไทยจากสมาคมฯ: buy_bar, sell_bar, timestamp, times(no. update)"""
    url = "https://www.goldtraders.or.th/default.aspx"
    headers = {"User-Agent":"Mozilla/5.0","Accept-Language":"th-TH,th;q=0.9"}
    r = requests.get(url, headers=headers, timeout=20)
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")

    sell = soup.select_one("#DetailPlace_uc_goldprices1_lblBLSell")
    buy  = soup.select_one("#DetailPlace_uc_goldprices1_lblBLBuy")
    ts   = soup.select_one("#DetailPlace_uc_goldprices1_lblAsTime")
    if not (sell and buy):
        raise ValueError("ไม่พบราคาทองจากเว็บสมาคมฯ (โครงหน้าเว็บอาจเปลี่ยน)")

    sellv = float(sell.get_text(strip=True).replace(",",""))
    buyv  = float(buy.get_text(strip=True).replace(",",""))
    tstr  = ts.get_text(strip=True) if ts else datetime.now().strftime("%d/%m/%Y %H:%M")

    # ดึง "ครั้งที่ ..."
    m = re.search(r"ครั้งที่\s?(\d+)", tstr)
    times = int(m.group(1)) if m else None
    return {"buy_bar":buyv,"sell_bar":sellv,"times":times,"timestamp":tstr}

def fetch_global_gold_and_fx():
    """XAU/USD (USD/oz) + USD/THB + คำนวณราคาทอง 1 บาทไทย (96.5%)"""
    try:
        # 1) XAU/USD
        r1 = requests.get("https://api.metals.live/v1/spot/gold", timeout=12)
        xau = float(r1.json()[0]["price"])
        # 2) USD/THB
        r2 = requests.get("https://api.exchangerate.host/latest?base=USD&symbols=THB", timeout=12)
        thb = float(r2.json()["rates"]["THB"])
        # 3) แปลงเป็นราคาทอง 1 บาทไทย (96.5%)
        grams_per_baht = 15.244
        troy_oz = 31.1035
        purity = 0.965
        baht_price_96 = xau * thb * (grams_per_baht / troy_oz) * purity
        return {"xauusd": xau, "usdthb": thb, "baht96": baht_price_96}
    except Exception as e:
        return {"xauusd": None, "usdthb": None, "baht96": None, "error": str(e)}

# ───────────────────────── LINE NOTIFY ───────────────────────────────────
def send_line_notify(message: str) -> tuple[int, str]:
    """ส่งข้อความไป LINE Notify ด้วย Token ที่ผู้ใช้ป้อน/จาก Secrets"""
    if not LINE_TOKEN:
        return 0, "LINE token not set"
    try:
        r = requests.post(
            "https://notify-api.line.me/api/notify",
            headers={"Authorization": f"Bearer {LINE_TOKEN}"},
            data={"message": message},
            timeout=12
        )
        return r.status_code, r.text
    except Exception as e:
        return -1, str(e)

# ───────────────────────── ALERT POLICY ──────────────────────────────────
def in_cooldown(prev: dict, now: datetime) -> bool:
    last_push = prev.get("last_push")
    if not last_push:
        return False
    try:
        lp = datetime.fromisoformat(last_push)
        return (now - lp) < timedelta(minutes=COOLDOWN_MIN)
    except Exception:
        return False

def daily_cap_reached(prev: dict, now: datetime) -> bool:
    tag = now.strftime("%Y-%m-%d")
    push_count = prev.get("push_count", f"{tag}:0")
    day, cnt = push_count.split(":")
    cnt = int(cnt) if day == tag else 0
    return cnt >= MAX_ALERTS_PER_DAY

def inc_daily_count(prev: dict, now: datetime) -> dict:
    tag = now.strftime("%Y-%m-%d")
    day, cnt = prev.get("push_count", f"{tag}:0").split(":")
    cnt = int(cnt) if day == tag else 0
    prev["push_count"] = f"{tag}:{cnt+1}"
    prev["last_push"] = now.isoformat()
    return prev

def should_alert(prev: dict, cur: dict) -> tuple[bool, str]:
    # แจ้งเมื่อ "ครั้งที่" เปลี่ยน หรือ ราคาเปลี่ยน
    if not prev:
        return False, "first_run"
    changed = (cur.get("times") != prev.get("times")) \
              or (cur.get("buy_bar") != prev.get("buy_bar")) \
              or (cur.get("sell_bar") != prev.get("sell_bar"))
    if not changed:
        return False, "no_change"

    now = datetime.now()
    if in_cooldown(prev, now):
        return False, "cooldown"
    if daily_cap_reached(prev, now):
        return False, "daily_cap"
    return True, "ok"

# ───────────────────────── HEADER ────────────────────────────────────────
st.markdown('<div class="logo">🥇 MeVGold Pro</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Thai Gold • XAU/USD • USD/THB • 1-Baht(96.5%) • LINE Alerts</div>', unsafe_allow_html=True)

# ───────────────────────── TOP BAR ───────────────────────────────────────
colA, colB = st.columns([1,1])
with colA:
    st.caption("อัปเดตอัตโนมัติทุก 1 วินาที (เฉพาะหน้าเว็บนี้เปิดอยู่)")
with colB:
    if st.button("🔄 รีเฟรชทันที", type="primary"):
        st.rerun()

# Auto-refresh 1 วินาที
st.markdown('<meta http-equiv="refresh" content="1">', unsafe_allow_html=True)

# ───────────────────────── MAIN FLOW ─────────────────────────────────────
try:
    cur  = fetch_gold_thai()
except Exception as e:
    st.error(f"❌ ดึงราคาทองไทยไม่สำเร็จ: {e}")
    st.stop()

prev = load_state()

# Global/FX
g = fetch_global_gold_and_fx()

# Price Box
delta = cur["buy_bar"] - prev.get("buy_bar", cur["buy_bar"])
pill_text = "• คงที่"
if delta > 0: pill_text = f"▲ +{delta:,.0f}"
elif delta < 0: pill_text = f"▼ {delta:,.0f}"

st.markdown('<div class="pricebox">', unsafe_allow_html=True)
st.markdown('<div class="price-title">ราคาทองคำแท่ง 96.5% (สมาคมค้าทองคำ)</div>', unsafe_allow_html=True)
st.markdown(f'<div class="price-main">{cur["sell_bar"]:,.0f} บาท</div>', unsafe_allow_html=True)
st.markdown(f'<div class="pill">{pill_text}</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="kv-wrap">', unsafe_allow_html=True)
st.markdown(f'<div class="kv"><label>รับซื้อ</label><b>{cur["buy_bar"]:,.0f}</b></div>', unsafe_allow_html=True)
st.markdown(f'<div class="kv"><label>ขายออก</label><b>{cur["sell_bar"]:,.0f}</b></div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown('<div class="card"><h4>XAU/USD</h4><div class="v">'
                + (f"${g['xauusd']:,.2f}" if g.get("xauusd") else "—")
                + '</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="card"><h4>USD/THB</h4><div class="v">'
                + (f"{g['usdthb']:.2f}" if g.get("usdthb") else "—")
                + '</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown('<div class="card"><h4>ทอง 1 บาท (96.5%)</h4><div class="v">'
                + (f"{g['baht96']:,.0f} บาท" if g.get("baht96") else "—")
                + '</div></div>', unsafe_allow_html=True)

times_txt = f'ครั้งที่ {cur["times"]}' if cur.get("times") else "ครั้งที่ –"
st.markdown(f'<div class="meta">{times_txt} • อัปเดต {cur["timestamp"]}</div>', unsafe_allow_html=True)

# History
append_history([
    datetime.now().strftime("%Y-%m-%d"),
    datetime.now().strftime("%H:%M:%S"),
    f"{cur['buy_bar']:.0f}", f"{cur['sell_bar']:.0f}",
    f"{g['xauusd']:.2f}" if g.get("xauusd") else "",
    f"{g['usdthb']:.4f}" if g.get("usdthb") else "",
    f"{g['baht96']:.0f}" if g.get("baht96") else ""
])

with st.expander("📅 ประวัติวันนี้ (ดูรายละเอียด)", expanded=False):
    if os.path.exists(HIST_FILE):
        try:
            df = pd.read_csv(HIST_FILE)
            st.dataframe(df.tail(120), width='stretch', hide_index=True)
            st.download_button("⬇️ ดาวน์โหลด CSV", data=df.to_csv(index=False).encode("utf-8"),
                               file_name="history_today.csv", mime="text/csv")
        except Exception:
            with open(HIST_FILE,"r",encoding="utf-8") as f:
                st.code("".join(f.readlines()[-120:]))

st.markdown('<div class="note">* ทอง 1 บาท (96.5%) = XAU/USD × USD/THB × 15.244/31.1035 × 0.965</div>', unsafe_allow_html=True)
st.markdown('<div class="footer">MeVGold Pro © 2025 — ข้อมูลจากสมาคมค้าทองคำ & สาธารณะ API (เพื่อการแสดงผลเท่านั้น)</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ───────────────────────── ALERT: ONLY ON OFFICIAL CHANGE ────────────────
# เงื่อนไขแจ้งเตือน: สมาคมฯ ประกาศใหม่ (times/ราคาเปลี่ยน) + มี LINE TOKEN + คูลดาวน์
ok = False
reason = "-"
try:
    ok, reason = should_alert(prev, cur)
except Exception:
    ok, reason = False, "error-check"

if ok and LINE_TOKEN:
    sign = "ขึ้น" if cur["sell_bar"] > prev.get("sell_bar", cur["sell_bar"]) else "ลง"
    change = abs(cur["sell_bar"] - prev.get("sell_bar", cur["sell_bar"]))
    msg = (
        f"📢 ราคาทองคำอัปเดต{' (ครั้งที่ '+str(cur['times'])+')' if cur.get('times') else ''}\n"
        f"ขายออก: {cur['sell_bar']:,.0f} บาท ({'+' if sign=='ขึ้น' else '-'}{change:,.0f})\n"
        f"รับซื้อ: {cur['buy_bar']:,.0f} บาท\n"
        f"เวลา: {cur['timestamp']}"
    )
    code, text = send_line_notify(msg)
    # อัปเดตตัวนับ/เวลา push
    now = datetime.now()
    state = {**prev, **cur}
    state = inc_daily_count(state, now)
    save_state(state)
else:
    # ไม่มีแจ้งเตือน ก็อัปเดต state ปกติ
    state = {**prev, **cur}
    save_state(state)
