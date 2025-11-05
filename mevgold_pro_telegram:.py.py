# mevgold_pro_telegram.py — MeVGold 96.5% (history migration safe)
# • Meta-refresh 60s
# • Badge อยู่บรรทัดเดียว (ขยับใกล้ “บาทละ(บาท)”)
# • สีเขียว/แดงทั้งหน้า + ประวัติ
# • Telegram แจ้งเมื่อ “สมาคมเปลี่ยนจริง” (+/− ถูกต้อง)
# • HISTORY: อ่านได้แม้ไฟล์เก่าไม่มี d_buy/d_sell (auto-migrate)

import os, json, re, csv, requests
from datetime import datetime
import streamlit as st
from bs4 import BeautifulSoup
import pandas as pd

# ---------- CONFIG ----------
st.set_page_config(page_title="MeVGold — Thai Gold 96.5%", page_icon="🏆", layout="centered")
st.markdown('<meta http-equiv="refresh" content="60">', unsafe_allow_html=True)

STATE_FILE = "last_gold.json"
HIST_FILE  = "history_today.csv"
SOURCE_URL = "https://www.goldtraders.or.th/default.aspx"

TG_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT  = st.secrets.get("TELEGRAM_CHAT_ID", "")

# ---------- STYLES ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Prompt:wght@500;600;700;800&display=swap');
:root{ --gold1:#F8E08A; --gold2:#F0C159; --gold3:#E3AC3A; --line:rgba(255,255,255,.08); }
html, body, .stApp{ font-family:'Prompt',system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
  background: radial-gradient(130% 160% at 50% -40%, #121722 0%, #0b0e12 55%, #080a0e 100%); color:#eceff4; }
.wrap{max-width:980px;margin:0 auto;padding:18px 14px 28px}
.brand{display:flex;gap:10px;align-items:center;justify-content:center;margin:6px 0 2px}
.brand b{font-size:36px;letter-spacing:-.2px;background:linear-gradient(92deg,var(--gold1),var(--gold2),var(--gold3));
  -webkit-background-clip:text;color:transparent}
.sub{color:#c9ced6;text-align:center;margin-bottom:8px;font-size:14px}
.note{color:#aab1bb;text-align:center;margin-bottom:6px;font-size:12px}
.card{position:relative;border-radius:22px;border:1px solid var(--line);
  background:linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.02)),
  radial-gradient(120% 160% at 90% -30%, rgba(248,224,138,.10), transparent 50%);
  box-shadow:0 16px 42px rgba(0,0,0,.35), 0 0 0 1px rgba(255,255,255,.04) inset; overflow:hidden;}
.header{position:relative;display:flex;align-items:center;justify-content:space-between;padding:14px 16px;
  border-bottom:1px solid var(--line);background:linear-gradient(180deg, rgba(248,224,138,.12), rgba(240,193,89,.08));min-height:64px;}
.header .left{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.pill{color:#0b0e12;font-weight:800;border-radius:999px;padding:8px 12px;background:linear-gradient(92deg,#ffe39a,#f6c663);white-space:nowrap}
.unit{color:#0b0e12;font-size:12px;font-weight:800;border-radius:999px;padding:8px 12px;background:linear-gradient(92deg,#f6c663,#ffe39a);white-space:nowrap}
/* badge ชิด “บาทละ(บาท)” */
.status{position:absolute;right:160px;top:50%;transform:translateY(-50%);pointer-events:none}
.badge{display:inline-flex;align-items:center;gap:8px;font-weight:900;padding:6px 12px;border-radius:999px;font-size:16px;
  color:#0b0e12;background:linear-gradient(92deg,#ffe39a,#f6c663);border:1px solid rgba(248,224,138,.6);
  box-shadow:0 10px 28px rgba(240,193,89,.22),0 0 0 1px rgba(255,255,255,.06) inset}
.table{padding:10px 12px 12px}
.row{display:grid;grid-template-columns:1.1fr 1fr 1fr;gap:10px;margin-bottom:10px}
.cell{background:linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.02));
  border:1px solid var(--line);border-radius:16px;padding:14px 16px;min-height:58px;box-shadow:0 6px 18px rgba(0,0,0,.25) inset}
.cell.head{background:linear-gradient(180deg, rgba(248,224,138,.12), rgba(240,193,89,.08));
  border:1px solid rgba(248,224,138,.35);text-align:center;font-weight:800}
.cell.right{text-align:right}
.tag{font-size:13px;color:#cbd5e1}
.price{font-size:38px;font-weight:900;background:linear-gradient(92deg,#F8E08A,#F0C159,#E3AC3A);
  -webkit-background-clip:text;color:transparent;text-shadow:0 1px 0 rgba(0,0,0,.35);}
.price.up{color:#16a34a;-webkit-text-fill-color:#16a34a;background:none}
.price.down{color:#ef4444;-webkit-text-fill-color:#ef4444;background:none}
.price.flat{color:#cbd5e1;-webkit-text-fill-color:#cbd5e1;background:none}
.footer{display:flex;justify-content:space-between;align-items:center;padding:10px 14px 12px;border-top:1px solid var(--line);color:#d1d5db;font-size:13px}
.footer b{font-weight:900} hr.sep{border:none;height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.1),transparent);margin:14px 0}
</style>
<div class="wrap">
""", unsafe_allow_html=True)

# ---------- HELPERS ----------
TH_DOW   = ["วันจันทร์","วันอังคาร","วันพุธ","วันพฤหัสบดี","วันศุกร์","วันเสาร์","วันอาทิตย์"]
TH_MONTH = ["ม.ค.","ก.พ.","มี.ค.","เม.ย.","พ.ค.","มิ.ย.","ก.ค.","ส.ค.","ก.ย.","ต.ค.","พ.ย.","ธ.ค."]

def th_now(dt: datetime) -> str:
    return f"{TH_DOW[dt.weekday()]} {dt.day} {TH_MONTH[dt.month-1]} {dt.year+543} • {dt.strftime('%H:%M')} น."

def load_state():
    try: return json.load(open(STATE_FILE,"r",encoding="utf-8"))
    except: return {}

def save_state(d:dict):
    try: json.dump(d, open(STATE_FILE,"w",encoding="utf-8"), ensure_ascii=False)
    except: pass

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
    # เติมคอลัมน์ที่ขาด
    for col in STD_COLUMNS:
        if col not in df.columns:
            df[col] = "" if col in ["times","buy_orn","sell_orn"] else "0" if col in ["d_buy","d_sell"] else ""
    # จัดลำดับคอลัมน์
    df = df[STD_COLUMNS]
    df.to_csv(HIST_FILE, index=False, encoding="utf-8")

def ensure_hist():
    migrate_history_file()

def append_hist(row:dict):
    ensure_hist()
    with open(HIST_FILE,"a",newline="",encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=STD_COLUMNS).writerow(row)

def fetch_assoc():
    r = requests.get(SOURCE_URL, headers={"User-Agent":"Mozilla/5.0"}, timeout=20)
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")
    def num(sel):
        t = soup.select_one(sel)
        return float(t.get_text(strip=True).replace(",","")) if t and t.get_text(strip=True) else None
    data = {
        "bar_buy":  num("#DetailPlace_uc_goldprices1_lblBLBuy"),
        "bar_sell": num("#DetailPlace_uc_goldprices1_lblBLSell"),
        "orn_buy":  num("#DetailPlace_uc_goldprices1_lblOMBuy"),
        "orn_sell": num("#DetailPlace_uc_goldprices1_lblOMSell"),
        "times":    None
    }
    ts = soup.select_one("#DetailPlace_uc_goldprices1_lblAsTime")
    if ts:
        m = re.search(r"ครั้งที่\s?(\d+)", ts.get_text(strip=True))
        if m: data["times"] = int(m.group(1))
    return data

def fmt_delta(n:int) -> str:
    if n > 0:  return f"▲ +{n}"
    if n < 0:  return f"▼ -{abs(n)}"
    return "— 0"

def send_telegram(text:str):
    if not (TG_TOKEN and TG_CHAT): return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            data={"chat_id": TG_CHAT, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
    except:
        pass

# ---------- MAIN ----------
st.markdown('<div class="brand">🏆 <b>MeVGold</b></div>', unsafe_allow_html=True)
st.markdown('<div class="sub">Thai Gold 96.5% • จากสมาคมค้าทองคำ</div>', unsafe_allow_html=True)
st.markdown('<div class="note">อัปเดตอัตโนมัติทุก 1 นาที (โหลดทั้งหน้า)</div>', unsafe_allow_html=True)

try:
    cur = fetch_assoc()
except Exception as e:
    st.error(f"❌ โหลดราคาจากสมาคมฯ ไม่สำเร็จ: {e}")
    st.stop()

prev = load_state()
save_state(cur)

now = datetime.now()
date_txt  = th_now(now)
times_txt = f"ครั้งที่ {cur['times']}" if cur.get("times") else "ครั้งที่ –"

# tick เทียบ state ก่อนหน้า (ครั้งแรกจะเป็น 0)
tick_buy  = int(round((cur["bar_buy"]  or 0) - (prev.get("bar_buy")  or cur["bar_buy"])))
tick_sell = int(round((cur["bar_sell"] or 0) - (prev.get("bar_sell") or cur["bar_sell"])))
badge_txt = fmt_delta(tick_sell)

# ---------- CARD ----------
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown(
    f"""
    <div class="header">
      <div class="left">
        <div class="pill">ประจำวันที่ {date_txt}</div>
        <div class="pill">{times_txt}</div>
      </div>
      <div class="status"><div class="badge"><span class="dot">{badge_txt}</span></div></div>
      <div class="unit">บาทละ (บาท)</div>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown('<div class="table">', unsafe_allow_html=True)
st.markdown('<div class="row"><div class="cell head">96.5%</div><div class="cell head">รับซื้อ</div><div class="cell head">ขายออก</div></div>', unsafe_allow_html=True)

def price_cell(v, cls):
    if v is None: return '<div class="cell right">–</div>'
    return f'<div class="cell right"><span class="price {cls}">{v:,.2f}</span></div>'

cls_buy  = "up" if tick_buy>0 else ("down" if tick_buy<0 else "flat")
cls_sell = "up" if tick_sell>0 else ("down" if tick_sell<0 else "flat")

st.markdown(
    f'<div class="row"><div class="cell"><div class="tag">ทองคำแท่ง</div></div>'
    f'{price_cell(cur["bar_buy"], cls_buy)}{price_cell(cur["bar_sell"], cls_sell)}</div>',
    unsafe_allow_html=True
)
st.markdown(
    f'<div class="row"><div class="cell"><div class="tag">ทองรูปพรรณ</div></div>'
    f'{price_cell(cur.get("orn_buy"), "flat")}{price_cell(cur.get("orn_sell"), "flat")}</div>',
    unsafe_allow_html=True
)

st.markdown('</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="footer"><div>อัปเดตล่าสุด: <b>{now.strftime("%d/%m/%Y • %H:%M")} น.</b></div><div>{times_txt}</div></div>',
    unsafe_allow_html=True
)
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<hr class="sep">', unsafe_allow_html=True)

# ---------- HISTORY + TELEGRAM ----------
ensure_hist()
changed = (prev.get("bar_buy") != cur["bar_buy"]) or (prev.get("bar_sell") != cur["bar_sell"])

if changed:
    append_hist({
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "times": cur.get("times",""),
        "buy_bar":  f"{(cur['bar_buy']  or 0):.2f}",
        "sell_bar": f"{(cur['bar_sell'] or 0):.2f}",
        "buy_orn":  f"{(cur.get('orn_buy')  or 0):.2f}" if cur.get("orn_buy")  is not None else "",
        "sell_orn": f"{(cur.get('orn_sell') or 0):.2f}" if cur.get("orn_sell") is not None else "",
        "d_buy":  str(tick_buy),
        "d_sell": str(tick_sell),
    })

    if TG_TOKEN and TG_CHAT:
        msg = (
            "<b>สมาคมค้าทองคำ อัปเดตราคา 96.5%</b>\n"
            f"รับซื้อ: <b>{cur['bar_buy']:,.0f}</b> ({fmt_delta(tick_buy)})\n"
            f"ขายออก: <b>{cur['bar_sell']:,.0f}</b> ({fmt_delta(tick_sell)})\n"
            f"{times_txt}  •  เวลา {now.strftime('%H:%M')} น."
        )
        send_telegram(msg)

# ---------- SHOW HISTORY (เวอร์ชันเรียบ ไม่มี "ครั้งที่") ----------
with st.expander("📅 ประวัติวันนี้ (เฉพาะรอบที่มีการเปลี่ยนแปลง)", expanded=False):
    try:
        df = pd.read_csv(HIST_FILE, dtype=str, on_bad_lines="skip")
        if df.empty:
            st.info("ยังไม่มีประวัติของวันนี้")
        else:
            # เติมคอลัมน์กันพัง
            for col in ["date","time","buy_bar","sell_bar","d_sell"]:
                if col not in df.columns:
                    df[col] = "" if col in ["date","time","buy_bar","sell_bar"] else "0"

            df["_dt"] = pd.to_datetime(df["date"]+" "+df["time"], errors="coerce")
            df = df.sort_values("_dt", ascending=False)

            # แปลงตัวเลข
            df["sell_num"] = pd.to_numeric(df["sell_bar"], errors="coerce")
            df["d_sell"]   = pd.to_numeric(df["d_sell"], errors="coerce").fillna(0).astype(int)

            # ถ้า d_sell ไม่มีค่าเลย → คำนวณจาก sell_bar
            if df["d_sell"].abs().sum() == 0:
                df["prev_sell"] = df["sell_num"].shift(1)
                df["d_sell"] = (df["sell_num"] - df["prev_sell"]).fillna(0).astype(int)

            def sign_only(n: int) -> str:
                return f"+{n}" if n > 0 else (f"-{abs(n)}" if n < 0 else "0")

            df["สถานะ (บาท)"] = df["d_sell"].apply(sign_only)

            df = df.rename(columns={
                "date":"วันที่","time":"เวลา",
                "buy_bar":"ราคาซื้อ","sell_bar":"ราคาขาย"
            })

            st.dataframe(
                df[["วันที่","เวลา","ราคาซื้อ","ราคาขาย","สถานะ (บาท)"]],
                width='stretch', hide_index=True
            )
    except Exception as e:
        st.info(f"อ่านประวัติไม่ได้: {e}")


st.markdown("</div>", unsafe_allow_html=True)
