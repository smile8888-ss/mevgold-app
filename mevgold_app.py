# mevgold_app.py — MeVGold (Pro/Lite in 1 file)
# Pro: 1s auto-refresh, XAU/USD, USD/THB, 1-baht(96.5%), LINE Alerts (on-change + cooldown)
# Lite: Thai gold only, manual refresh, no alerts, no global/FX
import os, json, csv, re, requests
from datetime import datetime, timedelta
import streamlit as st
from bs4 import BeautifulSoup
import pandas as pd

st.set_page_config(page_title="MeVGold", page_icon="🥇", layout="centered")

# ───────── Config / Secrets ─────────
STATE_FILE = "last_gold.json"
HIST_FILE  = "history_today.csv"

# default mode from Secrets; can toggle in sidebar
IS_PRO_DEFAULT = str(st.secrets.get("IS_PRO", "true")).lower() in ("1", "true", "yes")
LINE_TOKEN_SECRET = st.secrets.get("LINE_NOTIFY_TOKEN", "")

# Alert policy (Pro only)
COOLDOWN_MIN = int(st.secrets.get("COOLDOWN_MIN", 2))           # minutes
MAX_ALERTS_PER_DAY = int(st.secrets.get("MAX_ALERTS_PER_DAY", 30))

# ───────── Sidebar (mode + LINE token for Pro) ─────────
with st.sidebar:
    st.header("⚙️ Settings")
    is_pro = st.toggle("โหมด Pro", value=IS_PRO_DEFAULT, help="สลับโหมดเพื่อทดสอบฟีเจอร์ Pro/Lite")
    if is_pro:
        st.subheader("🔔 LINE Notify (เฉพาะ Pro)")
        token_in = st.text_input("LINE Notify Token", type="password", value="")
        LINE_TOKEN = (token_in.strip() or LINE_TOKEN_SECRET or "").strip()
        if LINE_TOKEN:
            st.success("พร้อมส่งแจ้งเตือนผ่าน LINE ✅")
        else:
            st.info("ใส่ LINE Token เพื่อให้แจ้งเตือนได้")
    else:
        LINE_TOKEN = ""

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
.delta-up{
  color:#0A7B34; background:rgba(16,185,129,.12);
  border-color:rgba(16,185,129,.35);
}
.delta-down{
  color:#B00020; background:rgba(239,68,68,.12);
  border-color:rgba(239,68,68,.35);
}
.delta-flat{
  color:#6B7280; background:#F3F4F6;
  border-color:#E5E7EB;
}

.kv-wrap{display:flex;gap:16px;flex-wrap:wrap;justify-content:center;margin:10px auto 4px;}
.kv{flex:1 1 320px;background:var(--card);border-radius:16px;box-shadow:0 6px 14px rgba(0,0,0,.05);
  padding:14px 18px 16px;text-align:center;border:1px solid var(--line);}
.kv label{display:block;font-size:13px;color:var(--muted);margin-bottom:6px;}
.kv b{font-size:28px;color:#000;}

.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px 16px;
  box-shadow:0 6px 14px rgba(0,0,0,.05);text-align:center;}
.card h4{margin:0 0 6px;font-size:14px;color:#8b90a1;}
.card .v{font-size:22px;font-weight:800;}
.grid-3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:10px 0 4px}
@media(max-width:720px){.grid-3{grid-template-columns:1fr;}}

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
    m = re.search(r"ครั้งที่\s?(\d+)", tstr); times = int(m.group(1)) if m else None
    return {"buy_bar":buyv,"sell_bar":sellv,"times":times,"timestamp":tstr}

def fetch_global_gold_and_fx():
    try:
        r1 = requests.get("https://api.metals.live/v1/spot/gold", timeout=12) # XAU/USD
        xau = float(r1.json()[0]["price"])
        r2 = requests.get("https://api.exchangerate.host/latest?base=USD&symbols=THB", timeout=12) # USDTHB
        thb = float(r2.json()["rates"]["THB"])
        grams_per_baht = 15.244; troy_oz = 31.1035; purity = 0.965
        baht_price_96 = xau * thb * (grams_per_baht / troy_oz) * purity
        return {"xauusd": xau, "usdthb": thb, "baht96": baht_price_96}
    except Exception as e:
        return {"xauusd": None, "usdthb": None, "baht96": None, "error": str(e)}

# ───────── LINE Notify (Pro) ─────────
def send_line_notify(message: str):
    token = LINE_TOKEN if is_pro else ""
    if not token: return 0, "no-token"
    try:
        r = requests.post(
            "https://notify-api.line.me/api/notify",
            headers={"Authorization": f"Bearer {token}"},
            data={"message": message}, timeout=12
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

def should_alert(prev: dict, cur: dict) -> bool:
    if not prev: return False
    changed = (cur.get("times") != prev.get("times")) \
           or (cur.get("buy_bar") != prev.get("buy_bar")) \
           or (cur.get("sell_bar") != prev.get("sell_bar"))
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
    st.markdown('<meta http-equiv="refresh" content="1">', unsafe_allow_html=True)  # 1s
else:
    st.caption("โหมด Lite: รีเฟรชด้วยปุ่มด้านล่าง (ไม่มี Auto-refresh)")

# ───────── Main flow ─────────
try:
    cur  = fetch_gold_thai()
except Exception as e:
    st.error(f"❌ ดึงราคาทองไทยไม่สำเร็จ: {e}")
    st.stop()

prev = load_state()

# ใช้ "ขายออก" เป็นตัวอ้างอิงการเปลี่ยนแปลง
change = cur["sell_bar"] - prev.get("sell_bar", cur["sell_bar"])
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

# รับซื้อ / ขายออก แยกบล็อก
st.markdown('<div class="kv-wrap">', unsafe_allow_html=True)
st.markdown(f'<div class="kv"><label>รับซื้อ</label><b>{cur["buy_bar"]:,.0f}</b></div>', unsafe_allow_html=True)
st.markdown(f'<div class="kv"><label>ขายออก</label><b>{cur["sell_bar"]:,.0f}</b></div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Pro: show global/FX/1baht; Lite: upsell
if is_pro:
    g = fetch_global_gold_and_fx()
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="card"><h4>XAU/USD</h4><div class="v">'
                    + (f"${g['xauusd']:,.2f}" if g.get("xauusd") else "—")
                    + '</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="card"><h4>USD/THB</h4><div class="v">'
                    + (f"{g['usdthb']:.2f}" if g.get("usdthb") else "—")
                    + '</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="card"><h4>ทอง 1 บาท (96.5%)</h4><div class="v">'
                    + (f"{g['baht96']:,.0f} บาท" if g.get("baht96") else "—")
                    + '</div></div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="upgrade"><a href="#" title="อัปเกรดเป็น Pro">🔓 อัปเกรดเป็น MeVGold Pro เพื่อดู XAU/USD, ค่าเงินบาท และคำนวณทอง 1 บาท พร้อมแจ้งเตือน</a></div>', unsafe_allow_html=True)
    g = {"xauusd": None, "usdthb": None, "baht96": None}

times_txt = f'ครั้งที่ {cur["times"]}' if cur.get("times") else "ครั้งที่ –"
st.markdown(f'<div class="meta">{times_txt} • อัปเดต {cur["timestamp"]}</div>', unsafe_allow_html=True)

# History (บันทึกมากขึ้นเฉพาะ Pro)
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
            st.dataframe(df.tail(80 if is_pro else 40), width='stretch', hide_index=True)
            st.download_button("⬇️ ดาวน์โหลด CSV", data=df.to_csv(index=False).encode("utf-8"),
                               file_name="history_today.csv", mime="text/csv")
        except Exception:
            with open(HIST_FILE,"r",encoding="utf-8") as f:
                st.code("".join(f.readlines()[-(120 if is_pro else 60):]))

if is_pro:
    st.markdown('<div class="note">* ทอง 1 บาท (96.5%) = XAU/USD × USD/THB × 15.244/31.1035 × 0.965</div>', unsafe_allow_html=True)

st.markdown('<div class="footer">MeVGold © 2025 — ข้อมูลจากสมาคมค้าทองคำ & สาธารณะ API (เพื่อการแสดงผลเท่านั้น)</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ───────── Alerts (Pro only): on official change + cooldown ─────────
state = load_state()
if is_pro:
    ok = should_alert(state, cur)
    if ok and LINE_TOKEN:
        sign = "ขึ้น" if cur["sell_bar"] > state.get("sell_bar", cur["sell_bar"]) else "ลง"
        change_amt = abs(cur["sell_bar"] - state.get("sell_bar", cur["sell_bar"]))
        msg = (
            f"📢 ราคาทองคำอัปเดต{' (ครั้งที่ '+str(cur['times'])+')' if cur.get('times') else ''}\n"
            f"ขายออก: {cur['sell_bar']:,.0f} บาท ({'+' if sign=='ขึ้น' else '-'}{change_amt:,.0f})\n"
            f"รับซื้อ: {cur['buy_bar']:,.0f} บาท\n"
            f"เวลา: {cur['timestamp']}"
        )
        code, text = send_line_notify(msg)
        # update push counters
        now = datetime.now()
        state = {**state, **cur}
        state = inc_daily_count(state, now)
        save_state(state)
    else:
        # just save current state
        state = {**state, **cur}
        save_state(state)
else:
    # Lite: save current state (no alerts)
    state = {**state, **cur}
    save_state(state)

# Lite: manual refresh button
if not is_pro:
    if st.button("🔄 รีเฟรชตอนนี้"):
        st.rerun()
