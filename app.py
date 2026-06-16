"""
💛 布布给一二宝做的 A股每日简评
上传晨报 → 实时行情 → DeepSeek AI → PDF
"""
import streamlit as st
import sys, os, socket, traceback, base64
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import run_pipeline, fetch_market_data

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
YIER_IMG = os.path.join(ASSETS, 'yier.png')
BUBU_IMG = os.path.join(ASSETS, 'bubu.png')

def _img_b64(path):
    if os.path.exists(path):
        with open(path, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    return None

YIER_B64 = _img_b64(YIER_IMG)
BUBU_B64 = _img_b64(BUBU_IMG)

def _weekday_cn(w):
    return ['周一','周二','周三','周四','周五','周六','周日'][w]

def _get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        s.close()
        return s.getsockname()[0]
    except:
        return 'localhost'

st.set_page_config(page_title="一二宝的A股简评", page_icon="💛", layout="wide", initial_sidebar_state="collapsed")

# ── 暖萌主题 ──
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap');
* { font-family: 'Noto Sans SC', 'Microsoft YaHei', sans-serif; }
.stApp { background: linear-gradient(180deg, #FFF8F0 0%, #FFF0E5 100%); }

.card { background: #FFFFFF; border-radius: 14px; padding: 16px 24px; margin: 10px 0;
    box-shadow: 0 2px 12px rgba(180,140,100,0.10); border-left: 4px solid #E8986E; }
.card.warm { border-left-color: #F4B860; }
.card.cool { border-left-color: #8CB89F; }
.card h3 { color: #4A3728; font-size: 15px; font-weight: 700; margin: 0 0 10px; }
.card p, .card li { color: #5A4A3A; font-size: 14px; line-height: 2.1; margin: 0; }
.card li b { color: #D4784C; }
.tag { display: inline-block; background: #FFF0E5; color: #D4784C;
    padding: 1px 8px; border-radius: 4px; font-size: 11px; margin: 0 2px; }

.mbox { background: #FFFFFF; border-radius: 10px; padding: 10px; text-align: center;
    box-shadow: 0 1px 6px rgba(180,140,100,0.08); transition: transform 0.15s; }
.mbox:hover { transform: translateY(-2px); box-shadow: 0 3px 12px rgba(180,140,100,0.15); }
.mbox .v { font-size: 17px; font-weight: 700; }
.mbox .l { font-size: 9px; color: #B5A090; margin-top: 2px; }
.mbox .n { font-size: 9px; color: #A09080; margin-bottom: 4px; letter-spacing: 0.5px; }
.mbox.up .v { color: #D4784C; } .mbox.down .v { color: #7BA88F; } .mbox.flat .v { color: #F4B860; }

.risk { background: linear-gradient(135deg, #FFF5EC, #FFEFE0); border: 1px solid #E8C8A8;
    border-radius: 12px; padding: 14px 18px; color: #8B6B4A; font-size: 13px; line-height: 1.7; }

.stButton > button {
    background: linear-gradient(135deg, #E8986E, #D4784C) !important;
    color: #fff !important; border: none !important; border-radius: 12px !important;
    padding: 10px 28px !important; font-weight: 600 !important; font-size: 15px !important;
    box-shadow: 0 2px 10px rgba(212,120,76,0.25) !important; transition: all 0.2s !important; }
.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(212,120,76,0.35) !important; }
.stButton > button:disabled { background: #DDD !important; box-shadow: none !important; }

.page-title { font-size: 26px; font-weight: 700; color: #D4784C; margin: 0; }
.page-sub { color: #B5A090; font-size: 12px; margin-top: 2px; }
hr { border: none; border-top: 1px solid #F0E0D0; }

/* ── 一二布布头像 ── */
.mascot-bar { display: flex; align-items: center; justify-content: center; gap: 14px; margin-bottom: 8px; }
.mascot-img { width: 90px; height: 90px; border-radius: 50%; object-fit: cover;
    border: 3px solid #F0D8C0; box-shadow: 0 3px 12px rgba(180,140,100,0.18);
    animation: float 2.5s ease-in-out infinite; }
.mascot-img:nth-child(1) { animation-delay: 0s; }
.mascot-img:nth-child(3) { animation-delay: 0.5s; }
.mascot-heart { font-size: 34px; animation: pulse 1.3s ease-in-out infinite; }
@keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-6px); } }
@keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.25); } }

.lan-badge { display: inline-block; background: #F5EDE5; color: #8B6B4A; padding: 4px 10px;
    border-radius: 6px; font-size: 11px; margin: 4px; }
.lan-badge.live { background: #E8F5EE; color: #5A8A72; }
.lan-badge.warm { background: #FFF0E5; color: #D4784C; }

.motto { text-align: center; color: #D4B8A0; font-size: 12px; margin-top: 4px; font-style: italic; }

.signature { text-align: right; color: #D4B8A0; font-size: 13px; margin-top: 12px; font-style: italic; }
@media (max-width: 768px) { .card { padding: 12px 14px; } .card li { font-size: 13px; } }
</style>""", unsafe_allow_html=True)

# ── State ──
for k, v in {'done': False, 'processing': False, 'result': None, 'error': None}.items():
    if k not in st.session_state: st.session_state[k] = v

today = date.today()
ip = _get_ip()

# ═══════════════════════════════════
# ── 头部：一二布布头像 ──
# ═══════════════════════════════════

if YIER_B64 and BUBU_B64:
    st.markdown(f"""
    <div class="mascot-bar">
        <img class="mascot-img" src="data:image/png;base64,{YIER_B64}" alt="一二">
        <span class="mascot-heart">💛</span>
        <img class="mascot-img" src="data:image/png;base64,{BUBU_B64}" alt="布布">
    </div>
    """, unsafe_allow_html=True)
elif YIER_B64:
    st.markdown(f"""
    <div class="mascot-bar">
        <img class="mascot-img" src="data:image/png;base64,{YIER_B64}" alt="一二">
        <span class="mascot-heart">💛</span>
        <span style="font-size:80px;">🐻</span>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="mascot-bar">
        <span style="font-size:80px;">🐼</span>
        <span class="mascot-heart">💛</span>
        <span style="font-size:80px;">🐻</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown(f'<p class="page-title">💛 一二宝的A股每日简评</p>', unsafe_allow_html=True)
st.markdown(f'<p class="page-sub">{today.strftime("%Y年%m月%d日")} {_weekday_cn(today.weekday())} · 布布给一二宝做的 ✨</p>',
            unsafe_allow_html=True)
st.markdown('<p class="motto">人生不如意事十常八九，常想一二 💛</p>', unsafe_allow_html=True)
st.markdown('<hr>', unsafe_allow_html=True)

# ═══════════════════════════════════
# ── 实时行情 ──
# ═══════════════════════════════════

st.markdown('<p style="color:#B5A090;font-size:11px;margin-bottom:4px;">📡 实时行情（Sina · AKShare · 每5分钟刷新）</p>',
            unsafe_allow_html=True)

@st.cache_data(ttl=300)
def _live():
    return fetch_market_data()

mkt_raw = _live()
live = not mkt_raw.get('_fallback', True)

mkt = [
    ('上证', f"{mkt_raw.get('sh',{}).get('price',0):.2f}", f"{mkt_raw.get('sh',{}).get('chg',0):+.2f}%",
     'up' if mkt_raw.get('sh',{}).get('chg',0) >= 0 else 'down'),
    ('深证', f"{mkt_raw.get('sz',{}).get('price',0):.2f}", f"{mkt_raw.get('sz',{}).get('chg',0):+.2f}%",
     'up' if mkt_raw.get('sz',{}).get('chg',0) >= 0 else 'down'),
    ('创业板', f"{mkt_raw.get('cy',{}).get('price',0):.2f}", f"{mkt_raw.get('cy',{}).get('chg',0):+.2f}%",
     'up' if mkt_raw.get('cy',{}).get('chg',0) >= 0 else 'down'),
    ('科创50', f"{mkt_raw.get('kc',{}).get('price',0):.2f}", f"{mkt_raw.get('kc',{}).get('chg',0):+.2f}%",
     'up' if mkt_raw.get('kc',{}).get('chg',0) >= 0 else 'down'),
    ('沪深300', f"{mkt_raw.get('hs',{}).get('price',0):.2f}", f"{mkt_raw.get('hs',{}).get('chg',0):+.2f}%",
     'up' if mkt_raw.get('hs',{}).get('chg',0) >= 0 else 'down'),
]
cols = st.columns(len(mkt))
for i, (name, val, chg, d) in enumerate(mkt):
    with cols[i]:
        st.markdown(f"<div class='mbox {d}'><div class='n'>{name}</div><div class='v'>{val}</div><div class='l'>{chg}</div></div>",
                    unsafe_allow_html=True)

st.markdown(f"""
<div style='display:flex;justify-content:space-between;align-items:center;margin-top:4px;'>
    <span class='lan-badge live'>{'🟢 实时在线' if live else '🟡 缓存'}</span>
    <span class='lan-badge'>🔗 http://{ip}:8501</span>
    <span class='lan-badge warm'>🧸 布布在守护一二宝的盘</span>
</div>
""", unsafe_allow_html=True)

st.markdown('<hr>', unsafe_allow_html=True)

# ═══════════════════════════════════
# ── 上传 ──
# ═══════════════════════════════════

u1, u2 = st.columns([1, 1])
with u1:
    up = st.file_uploader("📎 一二宝，把今天的中信晨会PDF给我~", type='pdf')
with u2:
    st.info("""
💛 **布布的工作**
① 收到一二宝的晨报 📎
② 布布跑去抓实时行情 📡
③ 找 DeepSeek 写简评 🧠
④ 一二宝下载 PDF，布布开心 🧸
    """)

btn = st.button("🧸 布布，给一二宝生成简评！", disabled=(up is None), use_container_width=True)

if btn and up and not st.session_state.processing:
    st.session_state.processing = True
    st.session_state.error = None
    with st.spinner("🧸 布布在读一二宝的晨报... 抓行情中... 喵~"):
        try:
            result = run_pipeline(up.read())
            st.session_state.result = result
            st.session_state.done = True
        except Exception as e:
            st.session_state.error = f"{e}\\n{traceback.format_exc()}"
        finally:
            st.session_state.processing = False

if st.session_state.error:
    st.error(f"❌ 布布摔了一跤：{st.session_state.error}")

if st.session_state.done and st.session_state.result:
    r = st.session_state.result
    st.markdown('<hr>', unsafe_allow_html=True)

    live_badge = "🟢 实时" if r.get('market_is_live') else "🟡 缓存"
    st.markdown(f"<p style='color:#B5A090;font-size:11px;'>{live_badge} | 🧠 DeepSeek | 🕐 {datetime.now().strftime('%H:%M:%S')} | 布布给一二宝做的 💛</p>",
                unsafe_allow_html=True)

    briefing = r['briefing']
    lines = briefing.strip().split('\n')
    items, dirs, etfs, risks = [], [], [], []
    phase = 'items'
    for line in lines:
        line = line.strip()
        if not line: continue
        if '|' in line and len(line.split('|')) >= 2:
            phase = 'dirs'; dirs.append(line); continue
        if any(k in line for k in ['ETF', 'etf']) and any(c in line for c in ['588','159','etf']):
            etfs.append(line); continue
        if any(k in line for k in ['风险','止损','注意','风控','⚠','回调']):
            risks.append(line); continue
        if phase == 'items':
            items.append(line)

    st.markdown('<div class="card"><h3>📋 今日简评</h3><ol style="margin:0;padding-left:18px;">',
                unsafe_allow_html=True)
    for item in items:
        clean = item.strip()
        for i in range(1, 10):
            clean = clean.replace(f'{i}. ', '').replace(f'{i}.', '')
        if clean:
            for code in ['688981','002475','300750','002594','600030','601012']:
                clean = clean.replace(f'({code})', f'<b>({code})</b>')
            st.markdown(f'<li>{clean}</li>', unsafe_allow_html=True)
    st.markdown('</ol></div>', unsafe_allow_html=True)

    if dirs:
        st.markdown('<div class="card warm"><h3>🧸 布布整理的方向</h3>', unsafe_allow_html=True)
        dir_data = [{'方向': p[0].strip(), '标的': p[1].strip(), '逻辑': p[2].strip()}
                     for d in dirs if len(p := [x.strip() for x in d.split('|')]) >= 3]
        if dir_data:
            st.dataframe(dir_data, hide_index=True, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if etfs:
        st.markdown(f'<div class="card cool"><h3>💡 ETF 省力方案</h3><p style="color:#5A4A3A;font-size:14px;">{" ".join(etfs)}</p></div>',
                    unsafe_allow_html=True)

    if risks:
        st.markdown(f'<div class="risk">⚠️ <b>布布的提醒：</b>{" ".join(risks)}</div>',
                    unsafe_allow_html=True)

    st.markdown('<p class="signature">—— 布布给一二宝，爱你 💛</p>', unsafe_allow_html=True)

    st.markdown('<hr>', unsafe_allow_html=True)
    if os.path.exists(r['pdf_path']):
        with open(r['pdf_path'], 'rb') as f:
            st.download_button("📥 一二宝，下载PDF报告~", f.read(),
                               os.path.basename(r['pdf_path']),
                               'application/pdf', use_container_width=True)

else:
    if YIER_B64 and BUBU_B64:
        st.markdown(f"""
        <div style='text-align:center;padding:60px 0 20px;'>
            <div style='display:flex;align-items:center;justify-content:center;gap:10px;margin-bottom:12px;'>
                <img src="data:image/png;base64,{YIER_B64}" style='width:70px;height:70px;border-radius:50%;object-fit:cover;border:2px solid #F0D8C0;box-shadow:0 2px 8px rgba(180,140,100,0.15);'>
                <span style='font-size:28px;'>💛</span>
                <img src="data:image/png;base64,{BUBU_B64}" style='width:70px;height:70px;border-radius:50%;object-fit:cover;border:2px solid #F0D8C0;box-shadow:0 2px 8px rgba(180,140,100,0.15);'>
            </div>
            <p style='font-size:18px;color:#5A4A3A;margin:4px 0;'>一二宝，把晨报给布布~</p>
            <p style='font-size:12px;color:#B5A090;'>上传 → 自动抓行情 → AI简评 → 下载PDF</p>
        </div>
        """, unsafe_allow_html=True)
    elif YIER_B64:
        st.markdown(f"""
        <div style='text-align:center;padding:60px 0 20px;'>
            <div style='margin-bottom:12px;'>
                <img src="data:image/png;base64,{YIER_B64}" style='width:70px;height:70px;border-radius:50%;object-fit:cover;border:2px solid #F0D8C0;'>
            </div>
            <p style='font-size:18px;color:#5A4A3A;margin:4px 0;'>一二宝，把晨报给布布~</p>
            <p style='font-size:12px;color:#B5A090;'>上传 → 自动抓行情 → AI简评 → 下载PDF</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='text-align:center;padding:80px;color:#C0A890;'>
            <p style='font-size:80px;margin:0;'>🧸</p>
            <p style='font-size:17px;margin:6px 0;'>一二宝，把晨报给布布~</p>
            <p style='font-size:12px;color:#D4B8A0;'>上传 → 自动抓行情 → AI简评 → 下载PDF</p>
        </div>
        """, unsafe_allow_html=True)

st.markdown('<hr>', unsafe_allow_html=True)
st.markdown(f"""<p style='text-align:center;color:#C0A890;font-size:11px;'>
🧸 布布给一二宝做的 · 人生不如意事十常八九，常想一二 💛<br/>
中信证券 · Sina行情 · DeepSeek · Streamlit &nbsp;|&nbsp; 🔗 http://{ip}:8501
</p>""", unsafe_allow_html=True)
