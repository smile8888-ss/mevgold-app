# mevgold_app.py — MeVGold Premium + OneSignal Push (Local-ready, Subdomain mode)
# ขั้นเตรียม: ใส่ REST API Key
# - macOS/Linux (ชั่วคราวในเทอร์มินัล): export ONESIGNAL_REST_KEY="YOUR_REST_API_KEY"
# - Windows (PowerShell): $env:ONESIGNAL_REST_KEY="YOUR_REST_API_KEY"
# หรือวางค่าชั่วคราวในตัวแปร ONESIGNAL_REST_KEY ด้านล่าง (เพื่อทดสอบโลคัล)

import os, json, csv, re, requests
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components
from bs4 import BeautifulSoup
import pandas as pd

# ─────────────────────────── PAGE & THEME ───────────────────────────
st.set_page_config(page_title="MeVGold", page_icon="🥇", layout="centered")

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
.subtitle{ text-align:center;color:var(--muted);font-size:14px;margin-bottom:10px;}
.toprow{display:flex;gap:8px;justify-content:center;align-items:center;margin:2px 0 6px;}
.stSelectbox>div>div{background:#fff !important;border:1px solid var(--line) !important}
.pricebox{background:#fff;border:2px solid rgba(247,183,51,.35);border-radius:20px;
  box-shadow:0 6px 18px rgba(247,183,51,.12);padding:18px 16px 12px;margin:8px auto 12px;text-align:center;}
.price-title{color:var(--gold2);font-weight:800;font-size:16px;margin-bottom:4px;}
.price-main{font-size:56px;font-weight:900;margin:-2px 0 4px;line-height:1;}
.pill{display:inline-flex;align-items:center;gap:6px;border-radius:999px;border:1px solid var(--line);
  padding:6px 12px;font-size:13px;color:#444;background:#F6F7FB;}
.kv-wrap{display:flex;gap:14px;flex-wrap:wrap;justify-content:center;margin:10px auto 4px;}
.kv{flex:1 1 320px;background:#fff;border-radius:16px;box-shadow:0 6px 14px rgba(0,0,0,.05);
  padding:14px 16px 16px;text-align:center;border:1px solid var(--line);}
.kv label{display:block;font-size:13px;color:var(--muted);margin-bottom:4px;}
.kv b{font-size:26px;color:#000;}
.divider{height:1px;background:var(--line);width:min(760px,92%);margin:10px auto;}
.meta{text-align:center;color:var(--muted);font-size:13px;margin-top:6px;}
.btn-center{text-align:center;margin-top:8px;}
.btn-center button{background:linear-gradient(90deg,var(--gold1),var(--gold2))!important;color:#222!important;
  border:none!important;font-weight:800!important;border-radius:12px!important;height:42px!important;padding:0 22px!important;
  box-shadow:0 4px 10px rgba(247,183,51,.25);}
.footer{text-align:center;color:#8B90A1;font-size:12px;margin-top:10px;}
</style>
<div class="main-wrap">
""", unsafe_allow_html=True)

# ─────────────────────────── FILES / STATE ───────────────────────────
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

# ─────────────────────────── FETCH GOLD ───────────────────────────
def fetch_gold():
    url = "https://www.goldtraders.or.th/default.aspx"
    headers = {"User-Agent":"Mozilla/5.0","Accept-Language":"th-TH,th;q=0.9"}
    r = requests.get(url, headers=headers, timeout=20)
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")

    sell = soup.select_one("#DetailPlace_uc_goldprices1_lblBLSell")   # ขายออก
    buy  = soup.select_one("#DetailPlace_uc_goldprices1_lblBLBuy")    # รับซื้อ
    ts   = soup.select_one("#DetailPlace_uc_goldprices1_lblAsTime")   # เวลา

    if not (sell and buy):
        raise ValueError("ไม่พบราคาทองจากเว็บสมาคมฯ")

    sellv = float(sell.get_text(strip=True).replace(",",""))
    buyv  = float(buy.get_text(strip=True).replace(",",""))
    tstr  = ts.get_text(strip=True) if ts else datetime.now().strftime("%d/%m/%Y %H:%M")
    m = re.search(r"ครั้งที่\\s?(\\d+)", tstr)
    times = int(m.group(1)) if m else None
    return {"buy_bar":buyv,"sell_bar":sellv,"times":times,"timestamp":tstr}

# ─────────────────────────── ONESIGNAL CONFIG ───────────────────────────
ONESIGNAL_APP_ID  = "fab796de-6fec-4b4c-bc7e-68601cdd68e5"  # จากหน้าตั้งค่า OneSignal ของเจ้านาย
ONESIGNAL_REST_KEY = os.getenv("ONESIGNAL_REST_KEY", "")     # ใส่ผ่าน env จะปลอดภัยกว่า

# ฝัง SDK (subdomain mode ใช้ได้กับ localhost)
st.markdown(f"""
<script src="https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.page.js" defer></script>
<script>
  window.OneSignalDeferred = window.OneSignalDeferred || [];
  OneSignalDeferred.push(async function(OneSignal) {{
    await OneSignal.init({{
      appId: "{ONESIGNAL_APP_ID}"
      // ถ้าตั้ง OneSignal Subdomain แล้ว ไม่ต้องวาง service worker ที่รูทเว็บเรา
    }});
  }});
</script>
""", unsafe_allow_html=True)

def send_push(title:str, body:str, url:str=None):
    """ยิง Push ผ่าน OneSignal REST; ถ้ายังไม่ตั้ง REST KEY จะข้ามไปเงียบๆ"""
    if not ONESIGNAL_REST_KEY:
        return False, "REST key missing"
    headers = {"Authorization": f"Basic {ONESIGNAL_REST_KEY}",
               "Content-Type": "application/json; charset=utf-8"}
    payload = {
        "app_id": ONESIGNAL_APP_ID,
        "included_segments": ["All"],
        "headings": {"en": title, "th": title},
        "contents": {"en": body, "th": body},
    }
    if url: payload["url"] = url
    r = requests.post("https://api.onesignal.com/notifications",
                      headers=headers, json=payload, timeout=20)
    ok = r.status_code in (200,202)
    return ok, r.text

# ─────────────────────────── HEADER ───────────────────────────
st.markdown('<div class="logo">🥇 MeVGold</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">ราคาทองคำสมาคมค้าทองคำแบบเรียลไทม์ (Premium Edition)</div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="toprow">', unsafe_allow_html=True)
    interval = st.selectbox("Auto-refresh", ["ปิด","ทุก 1 นาที","ทุก 5 นาที"], index=1, label_visibility="visible")
    # ปุ่มเปิดแจ้งเตือน
    components.html("""
    <div style="display:flex;justify-content:center">
      <button id="push-btn" style="
        background:linear-gradient(90deg,#FAD961,#F7B733);
        color:#222;font-weight:800;border:none;border-radius:12px;
        height:38px;padding:0 14px;margin-left:8px;box-shadow:0 4px 10px rgba(247,183,51,.25);
        cursor:pointer">🔔 เปิดแจ้งเตือน</button>
    </div>
    <script>
      (function(){
        const btn=document.getElementById('push-btn');
        btn&&btn.addEventListener('click',async()=>{
          try{
            if(!window.OneSignalDeferred){ alert('กำลังเตรียมระบบแจ้งเตือน ลองอีกครั้งใน 1-2 วิค่ะ'); return; }
            await new Promise(res=>window.OneSignalDeferred.push(res));
            const OneSignal=window.OneSignal;
            await OneSignal.Notifications.requestPermission();
            alert('เปิดแจ้งเตือนเรียบร้อย ถ้าเบราว์เซอร์ถาม ให้กด Allow นะคะ');
          }catch(e){ console.error(e); alert('เปิดแจ้งเตือนไม่สำเร็จ ลองใหม่ค่ะ'); }
        });
      })();
    </script>
    """, height=50)
    st.markdown('</div>', unsafe_allow_html=True)

refresh_secs = {"ปิด":None,"ทุก 1 นาที":60,"ทุก 5 นาที":300}[interval]
if refresh_secs:
    st.markdown(f'<meta http-equiv="refresh" content="{refresh_secs}">', unsafe_allow_html=True)

# ─────────────────────────── MAIN ───────────────────────────
try:
    cur  = fetch_gold()
    prev = load_state() or {}
    # delta ตามรับซื้อ (ทิศทางรวม)
    delta = cur["buy_bar"] - prev.get("buy_bar", cur["buy_bar"])

    # กล่องราคาหลัก
    st.markdown('<div class="pricebox">', unsafe_allow_html=True)
    st.markdown('<div class="price-title">ราคาทองคำแท่ง 96.5%</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="price-main">{cur["sell_bar"]:,.0f} บาท</div>', unsafe_allow_html=True)
    pill = "• คงที่"
    if delta>0: pill = f"▲ +{delta:,.0f}"
    elif delta<0: pill = f"▼ {delta:,.0f}"
    st.markdown(f'<div class="pill">{pill}</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # KV: ซื้อ/ขาย
    st.markdown('<div class="kv-wrap">', unsafe_allow_html=True)
    st.markdown(f'<div class="kv"><label>รับซื้อ</label><b>{cur["buy_bar"]:,.0f}</b></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="kv"><label>ขายออก</label><b>{cur["sell_bar"]:,.0f}</b></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    times_txt = f'ครั้งที่ {cur["times"]}' if cur.get("times") else "ครั้งที่ –"
    st.markdown(f'<div class="meta">{times_txt} • อัปเดต {cur["timestamp"]}</div>', unsafe_allow_html=True)

    # บันทึกประวัติทุกครั้งที่เปิด
    append_history([datetime.now().strftime("%Y-%m-%d"),
                    datetime.now().strftime("%H:%M:%S"),
                    f"{cur['buy_bar']:.0f}", f"{cur['sell_bar']:.0f}"])

    # Cooldown กันสแปม PUSH (ทุก 10 นาทีส่งได้ 1 ครั้งเมื่อราคาเปลี่ยน)
    state = prev
    now_stamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    last_sent = state.get("last_push_stamp")
    def can_send_again(now_str,last_str,mins=10):
        if not last_str: return True
        try:
            t1=datetime.strptime(now_str,"%d/%m/%Y %H:%M")
            t0=datetime.strptime(last_str,"%d/%m/%Y %H:%M")
            return (t1-t0).total_seconds()>=mins*60
        except:
            return True

    if delta!=0 and can_send_again(now_stamp,last_sent,minutes=10):
        direction = "ขึ้น" if delta>0 else "ลง"
        title = f"ราคาทอง{direction} {abs(delta):,.0f} บาท"
        body  = f"รับซื้อ {cur['buy_bar']:,.0f} • ขายออก {cur['sell_bar']:,.0f}  (อัปเดต {cur['timestamp']})"
        ok, resp = send_push(title, body)
        if ok:
            state["last_push_stamp"] = now_stamp

    # เซฟสถานะล่าสุด
    state.update(cur)
    save_state(state)

except Exception as e:
    st.error(f"❌ ดึงราคาไม่สำเร็จ: {e}")

# ปุ่มรีเฟรช
st.markdown('<div class="btn-center">', unsafe_allow_html=True)
if st.button("🔄 รีเฟรชราคา"): st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# ประวัติวันนี้ (ไม่มีกราฟ)
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
