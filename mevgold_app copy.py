# mevgold_app.py — MeVGold (Bright Premium v7: tidy spacing + history expander)
import os, json, csv, re, requests
from datetime import datetime
import streamlit as st
from bs4 import BeautifulSoup
import pandas as pd

st.set_page_config(page_title="MeVGold", page_icon="🥇", layout="centered")

# ─────────────────────────── STYLE ───────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Prompt:wght@600;700;800&display=swap');
:root{
  --bg1:#fffef9; --bg2:#faf8f3; --ink:#111; --muted:#788095; --line:#E9EBF3;
  --gold1:#FAD961; --gold2:#F7B733;
}
html,body,.stApp {background: radial-gradient(140% 160% at 50% -40%, var(--bg1) 0%, var(--bg2) 100%);
  font-family:'Prompt',system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; color:var(--ink);}
.main-wrap{max-width:760px;margin:0 auto;padding:8px 16px 18px;}
.logo{ text-align:center;font-size:40px;font-weight:800;
  background:linear-gradient(90deg,var(--gold1),var(--gold2));-webkit-background-clip:text;color:transparent;
  letter-spacing:-.4px;margin:10px 0 2px;}
.subtitle{ text-align:center;color:var(--muted);font-size:14px;margin-bottom:14px;}

.toprow{display:flex;justify-content:flex-end;align-items:center;margin:0 0 6px;}
.stSelectbox>div>div{background:#fff !important;border:1px solid var(--line) !important}

.pricebox{background:#fff;border:2px solid rgba(247,183,51,.35);border-radius:20px;
  box-shadow:0 6px 18px rgba(247,183,51,.12);padding:20px 16px 12px;margin:8px auto 14px;text-align:center;}
.price-title{color:var(--gold2);font-weight:800;font-size:17px;margin-bottom:4px;}
.price-main{font-size:58px;font-weight:900;margin:-2px 0 4px;}
.pill{display:inline-flex;align-items:center;gap:6px;border-radius:999px;border:1px solid var(--line);
  padding:6px 12px;font-size:13px;color:#444;background:#F6F7FB;}

.kv-wrap{display:flex;gap:18px;flex-wrap:wrap;justify-content:center;margin:12px auto 4px;}
.kv{flex:1 1 320px;background:#fff;border-radius:16px;box-shadow:0 6px 14px rgba(0,0,0,.05);
  padding:16px 18px 18px;text-align:center;border:1px solid var(--line);}
.kv label{display:block;font-size:13px;color:var(--muted);margin-bottom:6px;}
.kv b{font-size:28px;color:#000;}

.divider{height:1px;background:var(--line);width:min(760px,92%);margin:12px auto;}

.meta{text-align:center;color:var(--muted);font-size:13px;margin-top:6px;}
.btn-center{text-align:center;margin-top:8px;}
.btn-center button{background:linear-gradient(90deg,var(--gold1),var(--gold2))!important;color:#222!important;
  border:none!important;font-weight:800!important;border-radius:12px!important;height:42px!important;padding:0 22px!important;
  box-shadow:0 4px 10px rgba(247,183,51,.25);}
.footer{text-align:center;color:#8B90A1;font-size:12px;margin-top:12px;}
</style>
<div class="main-wrap">
""", unsafe_allow_html=True)

# ─────────────────────── FILES ───────────────────────
STATE_FILE, HIST_FILE = "last_gold.json", "history_today.csv"

def load_state():
    try: return json.load(open(STATE_FILE,"r",encoding="utf-8"))
    except: return {}

def save_state(data:dict):
    json.dump(data, open(STATE_FILE,"w",encoding="utf-8"), ensure_ascii=False)

def append_history(row):
    if not os.path.exists(HIST_FILE):
        with open(HIST_FILE,"w",newline="",encoding="utf-8") as f:
            csv.writer(f).writerow(["date","time","buy","sell"])
    with open(HIST_FILE,"a",newline="",encoding="utf-8") as f:
        csv.writer(f).writerow(row)

# ───────────────────── FETCH ─────────────────────
def fetch_gold():
    url = "https://www.goldtraders.or.th/default.aspx"
    headers = {"User-Agent":"Mozilla/5.0","Accept-Language":"th-TH,th;q=0.9"}
    r = requests.get(url, headers=headers, timeout=20)
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")

    sell = soup.select_one("#DetailPlace_uc_goldprices1_lblBLSell")
    buy  = soup.select_one("#DetailPlace_uc_goldprices1_lblBLBuy")
    ts   = soup.select_one("#DetailPlace_uc_goldprices1_lblAsTime")

    if not (sell and buy):
        raise ValueError("ไม่พบราคาทองจากเว็บสมาคมฯ")

    sellv = float(sell.get_text(strip=True).replace(",",""))
    buyv  = float(buy.get_text(strip=True).replace(",",""))
    tstr  = ts.get_text(strip=True) if ts else datetime.now().strftime("%d/%m/%Y %H:%M")

    m = re.search(r"ครั้งที่\\s?(\\d+)", tstr)
    times = int(m.group(1)) if m else None

    return {"buy_bar":buyv,"sell_bar":sellv,"times":times,"timestamp":tstr}

# ───────────────────── HEADER ─────────────────────
st.markdown('<div class="logo">🥇 MeVGold</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">ราคาทองคำสมาคมค้าทองคำแบบเรียลไทม์ (Premium Edition)</div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="toprow">', unsafe_allow_html=True)
    interval = st.selectbox("Auto-refresh", ["ปิด","ทุก 1 นาที","ทุก 5 นาที"], index=1)
    st.markdown('</div>', unsafe_allow_html=True)

refresh_secs = {"ปิด":None,"ทุก 1 นาที":60,"ทุก 5 นาที":300}[interval]
if refresh_secs:
    st.markdown(f'<meta http-equiv="refresh" content="{refresh_secs}">', unsafe_allow_html=True)

# ───────────────────── MAIN ─────────────────────
try:
    cur  = fetch_gold()
    prev = load_state(); save_state(cur)

    # delta เฉพาะรับซื้อ (อิงภาพรวมทิศทาง)
    delta = cur["buy_bar"] - prev.get("buy_bar", cur["buy_bar"])
    pill_text = "• คงที่"
    if delta > 0: pill_text = f"▲ +{delta:,.0f}"
    elif delta < 0: pill_text = f"▼ {delta:,.0f}"

    # อัปเดตประวัติ (บันทึกทุกครั้งที่เปิด)
    append_history([datetime.now().strftime("%Y-%m-%d"),
                    datetime.now().strftime("%H:%M:%S"),
                    f"{cur['buy_bar']:.0f}", f"{cur['sell_bar']:.0f}"])

    # กล่องราคาหลัก
    st.markdown('<div class="pricebox">', unsafe_allow_html=True)
    st.markdown('<div class="price-title">ราคาทองคำแท่ง 96.5%</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="price-main">{cur["sell_bar"]:,.0f} บาท</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pill">{pill_text}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # กล่องรับซื้อ / ขายออก (เว้นระยะให้โปร่งขึ้น)
    st.markdown('<div class="kv-wrap">', unsafe_allow_html=True)
    st.markdown(f'<div class="kv"><label>รับซื้อ</label><b>{cur["buy_bar"]:,.0f}</b></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="kv"><label>ขายออก</label><b>{cur["sell_bar"]:,.0f}</b></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    times_txt = f'ครั้งที่ {cur["times"]}' if cur.get("times") else "ครั้งที่ –"
    st.markdown(f'<div class="meta">{times_txt} • อัปเดต {cur["timestamp"]}</div>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"❌ ดึงราคาไม่สำเร็จ: {e}")

# ปุ่มรีเฟรช
st.markdown('<div class="btn-center">', unsafe_allow_html=True)
if st.button("🔄 รีเฟรชราคา"): st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# ประวัติแบบกดดู (ไม่มีกราฟ)
with st.expander("📅 ประวัติวันนี้ (ดูรายละเอียด)", expanded=False):
    if os.path.exists(HIST_FILE):
        try:
            df = pd.read_csv(HIST_FILE)
            st.dataframe(df.tail(50), width='stretch', hide_index=True)
            st.download_button("⬇️ ดาวน์โหลด CSV", data=df.to_csv(index=False).encode("utf-8"),
                               file_name="history_today.csv", mime="text/csv")
        except Exception:
            with open(HIST_FILE,"r",encoding="utf-8") as f:
                st.code("".join(f.readlines()[-50:]))

st.markdown('<div class="footer">MeVGold © 2025 — ข้อมูลจากสมาคมค้าทองคำ (เพื่อการแสดงผลเท่านั้น)</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)  # end .main-wrap
