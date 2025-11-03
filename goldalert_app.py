# mevgold_app.py — MeVGold (Gold Premium v6)
import os, json, csv, re, requests
from datetime import datetime
import streamlit as st
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="MeVGold", page_icon="🥇", layout="centered")

# ──────────────────────────── STYLE ────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Prompt:wght@600;700;800&display=swap');
html,body,.stApp {
  background: radial-gradient(140% 160% at 50% -40%, #fffef9 0%, #faf8f3 100%);
  font-family: 'Prompt', sans-serif;
  color: #1A1A1A;
}
h1,h2,h3 {font-weight: 800;}
.main-wrap {max-width: 760px; margin: 0 auto; padding: 6px 16px 20px;}
.logo {
  text-align:center;
  font-size: 40px;
  font-weight: 800;
  background: linear-gradient(90deg,#FAD961,#F7B733);
  -webkit-background-clip: text;
  color: transparent;
  letter-spacing: -0.5px;
  margin-top: 10px;
  margin-bottom: 2px;
}
.subtitle {text-align:center;color:#777;font-size:14px;margin-bottom:16px;}
.price-box {
  background: #fff;
  border: 2px solid rgba(247,183,51,.35);
  border-radius: 20px;
  box-shadow: 0 6px 18px rgba(247,183,51,.12);
  padding: 20px 14px 10px;
  margin: 10px auto 14px;
  text-align: center;
}
.price-main {font-size: 58px; font-weight: 900; margin: -4px 0;}
.gold-label {color: #F7B733; font-size: 17px; font-weight: 700; margin-bottom: 2px;}
.pill {
  display:inline-flex;align-items:center;gap:5px;
  border-radius: 999px; border:1px solid #ddd;
  padding: 5px 12px; font-size:13px;
  color:#333; background:#f7f7f7; margin-top:4px;
}
.pill.up {color:#09996A;background:rgba(13,189,125,.10);border-color:rgba(13,189,125,.35);}
.pill.down{color:#D94A5E;background:rgba(255,94,116,.10);border-color:rgba(255,94,116,.35);}
.kv-box {
  display:flex; justify-content:center; gap:14px; flex-wrap:wrap;
  margin-top:10px;
}
.kv {
  flex:1 1 300px;
  background:#fff;
  border-radius:14px;
  box-shadow:0 4px 10px rgba(0,0,0,0.05);
  padding:10px 12px;
  text-align:center;
}
.kv label{font-size:13px;color:#777;}
.kv b{font-size:24px;color:#000;}
.meta{text-align:center;color:#777;font-size:13px;margin-top:6px;}
.btn-center{text-align:center;margin-top:8px;}
.btn-center button {
  background:linear-gradient(90deg,#FAD961,#F7B733)!important;
  color:#222!important;border:none!important;
  font-weight:800!important;border-radius:12px!important;
  height:42px!important;padding:0 22px!important;
  box-shadow:0 4px 10px rgba(247,183,51,.3);
}
.footer{text-align:center;color:#888;font-size:12px;margin-top:12px;}
</style>
<div class="main-wrap">
""", unsafe_allow_html=True)

# ──────────────────────────── DATA FILES ────────────────────────────
STATE_FILE, HIST_FILE = "last_gold.json", "history_today.csv"
def load_state():
    try: return json.load(open(STATE_FILE,"r",encoding="utf-8"))
    except: return {}
def save_state(data):
    json.dump(data, open(STATE_FILE,"w",encoding="utf-8"), ensure_ascii=False)
def append_history(row):
    if not os.path.exists(HIST_FILE):
        csv.writer(open(HIST_FILE,"w",newline="",encoding="utf-8")).writerow(["date","time","buy","sell"])
    with open(HIST_FILE,"a",newline="",encoding="utf-8") as f:
        csv.writer(f).writerow(row)

# ──────────────────────────── FETCH ────────────────────────────
def fetch_gold():
    url = "https://www.goldtraders.or.th/default.aspx"
    headers = {"User-Agent":"Mozilla/5.0","Accept-Language":"th-TH,th;q=0.9"}
    r = requests.get(url,headers=headers,timeout=20)
    r.encoding="utf-8"; soup=BeautifulSoup(r.text,"html.parser")
    sell = soup.select_one("#DetailPlace_uc_goldprices1_lblBLSell")
    buy  = soup.select_one("#DetailPlace_uc_goldprices1_lblBLBuy")
    ts   = soup.select_one("#DetailPlace_uc_goldprices1_lblAsTime")
    if not sell or not buy:
        raise ValueError("ไม่พบราคาทองจากเว็บสมาคมฯ")
    sellv, buyv = float(sell.text.replace(",","")), float(buy.text.replace(",",""))
    tstr = ts.text.strip() if ts else datetime.now().strftime("%d/%m/%Y %H:%M")
    m=re.search(r"ครั้งที่\s?(\d+)",tstr); times=int(m.group(1)) if m else None
    return {"buy_bar":buyv,"sell_bar":sellv,"times":times,"timestamp":tstr}

# ──────────────────────────── UI ────────────────────────────
st.markdown('<div class="logo">🥇 MeVGold</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">ราคาทองคำสมาคมค้าทองคำแบบเรียลไทม์ (Premium Edition)</div>', unsafe_allow_html=True)

interval = st.selectbox("⏱ Auto-refresh", ["ปิด","ทุก 1 นาที","ทุก 5 นาที"], index=1)
refresh_secs = {"ปิด":None,"ทุก 1 นาที":60,"ทุก 5 นาที":300}[interval]
if refresh_secs: st.markdown(f'<meta http-equiv="refresh" content="{refresh_secs}">', unsafe_allow_html=True)

try:
    cur  = fetch_gold()
    prev = load_state(); save_state(cur)
    delta = cur["buy_bar"] - prev.get("buy_bar",cur["buy_bar"])
    pill_class = "up" if delta>0 else "down" if delta<0 else ""
    pill_text  = f"▲ +{delta:,.0f}" if delta>0 else f"▼ {delta:,.0f}" if delta<0 else "• คงที่"

    append_history([datetime.now().strftime("%Y-%m-%d"),
                    datetime.now().strftime("%H:%M:%S"),
                    f"{cur['buy_bar']:.0f}", f"{cur['sell_bar']:.0f}"])

    # กล่องราคา
    st.markdown('<div class="price-box">', unsafe_allow_html=True)
    st.markdown('<div class="gold-label">ราคาทองคำแท่ง 96.5%</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="price-main">{cur["sell_bar"]:,.0f} บาท</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pill {pill_class}">{pill_text}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # แถวรับซื้อ/ขายออก
    st.markdown('<div class="kv-box">', unsafe_allow_html=True)
    st.markdown(f'<div class="kv"><label>รับซื้อ</label><b>{cur["buy_bar"]:,.0f}</b></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="kv"><label>ขายออก</label><b>{cur["sell_bar"]:,.0f}</b></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # กราฟ Sparkline
    if os.path.exists(HIST_FILE):
        df = pd.read_csv(HIST_FILE)
        df["datetime"] = pd.to_datetime(df["date"]+" "+df["time"])
        df = df.tail(40)
        fig, ax = plt.subplots(figsize=(6,1.8))
        ax.plot(df["datetime"], df["sell"].astype(float), color="#F7B733", linewidth=2)
        ax.scatter(df["datetime"].iloc[-1], df["sell"].astype(float).iloc[-1], color="#FAD961", s=50, edgecolor="#fff", zorder=5)
        ax.set_xticks([]); ax.set_yticks([])
        for spine in ax.spines.values(): spine.set_visible(False)
        st.pyplot(fig, use_container_width=True)

    # เวลาล่าสุด
    times_txt = f'ครั้งที่ {cur["times"]}' if cur.get("times") else "ครั้งที่ –"
    st.markdown(f'<div class="meta">{times_txt} • อัปเดต {cur["timestamp"]}</div>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"❌ ดึงราคาไม่สำเร็จ: {e}")

# ปุ่มรีเฟรช
st.markdown('<div class="btn-center">', unsafe_allow_html=True)
if st.button("🔄 รีเฟรชราคา"): st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="footer">MeVGold © 2025 — ข้อมูลจากสมาคมค้าทองคำ (เพื่อแสดงผลเท่านั้น)</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
