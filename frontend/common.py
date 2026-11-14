"""
frontend/common.py  —  Thanh phan DUNG CHUNG cua giao dien (MODULE M2, phu trach: Minh)
=======================================================================================
Ngon ngu thiet ke "Pho co Hoi An":
  - Nen giay do nga, chu muc nau den; diem nhan do den long, vang tuong co,
    xanh cua go; duong vien manh, goc vuong vua phai - khong emoji, khong mau ruc.
  - Tieu de chu co chan Cormorant Garamond, noi dung Be Vietnam Pro.
Moi trang chi can:   from common import page_header, kpi, kpi_row, ...
"""

import os
import sys
from datetime import datetime, timedelta

import requests
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))  # de import backend.report_export

try:
    import plotly.graph_objects as go  # noqa: F401
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

API_BASE = os.environ.get("SMARTCAU_API", "http://127.0.0.1:8000")   # giao dien (chay o may chu) goi backend


def public_api_base() -> str:
    """Dia chi backend DUNG CHO TRINH DUYET cua nguoi xem. Khi API_BASE la 127.0.0.1 ma nguoi xem
    mo web tu may khac (vd http://192.168.1.10:8501), doi 127.0.0.1 thanh dia chi ho dang dung."""
    from urllib.parse import urlparse
    u = urlparse(API_BASE)
    if u.hostname not in ("127.0.0.1", "localhost"):
        return API_BASE
    try:
        host = (st.context.headers.get("Host") or "").split(":")[0]
    except Exception:
        host = ""
    if not host or host in ("127.0.0.1", "localhost"):
        return API_BASE
    return f"{u.scheme}://{host}:{u.port or 8000}"

# ------------------------------------------------------------------- bang mau
C = {
    "ink": "#1F1A17", "muted": "#776B5F", "line": "#E3D9C8", "paper": "#F5F0E6", "surface": "#FFFDF8",
    "oxblood": "#7D2318", "gold": "#A8812F", "teal": "#2E5B58", "wood": "#5A3E2B", "stone": "#B9AE9F",
    "ok": "#3C6E47", "warn": "#B07A12", "danger": "#8E2418",
}
COLORS = {"primary": C["oxblood"], "ochre": C["gold"], "moss": C["ok"], "blue": C["teal"], "danger": C["danger"],
          "warn": C["warn"], "ok": C["ok"], "ink": C["ink"], "muted": C["muted"], "wood": C["wood"], "stone": C["stone"]}
SERIES = [C["oxblood"], C["gold"], C["teal"], C["wood"], "#8C7B6A", "#C4A77D"]

# ------------------------------------------------------------ nhan tieng Viet
GENDER_VI = {"Man": "Nam", "Woman": "Nữ", None: "Không xác định"}
ORIGIN_VI = {"Trong nuoc": "Trong nước/châu Á", "Nuoc ngoai": "Quốc tế", None: "Chưa rõ"}
AGE_ORDER = ["0-5", "6-12", "13-17", "18-24", "25-34", "35-44", "45-54", "55-64", "65-69", "70+"]
ROLE_VI = {"admin": "Quản trị viên", "quan_ly": "Quản lý", "nguoi_truc": "Người trực"}
STATUS_META = {
    "OK": {"label": "Bình thường", "tone": "ok"},
    "WARNING": {"label": "Cảnh báo Vàng", "tone": "warn"},
    "ALERT": {"label": "Vàng · đang xác nhận", "tone": "warn"},
    "CRITICAL": {"label": "Cảnh báo Đỏ · Quá tải", "tone": "danger"},
}


# ------------------------------------------------------------------- theme
def apply_theme():
    st.markdown(_THEME_CSS, unsafe_allow_html=True)


_THEME_CSS_RAW = (
        """
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@300;400;500;600;700&family=Cormorant+Garamond:wght@500;600;700&display=swap" rel="stylesheet">
        <style>
        :root { --ink:#1F1A17; --muted:#776B5F; --line:#E3D9C8; --paper:#F5F0E6; --surface:#FFFDF8;
                --oxblood:#7D2318; --gold:#A8812F; --teal:#2E5B58; --wood:#5A3E2B;
                --ok:#3C6E47; --warn:#B07A12; --danger:#8E2418;
                --serif:'Cormorant Garamond', 'Times New Roman', serif; --sans:'Be Vietnam Pro', system-ui, sans-serif; }
        html, body, .stApp, button, input, textarea, select, [data-testid="stMarkdownContainer"] { font-family: var(--sans) !important; }
        .stApp { background: var(--paper); color: var(--ink); }
        .block-container { padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1240px; }
        h1, h2, h3, h4 { font-family: var(--serif) !important; color: var(--ink); font-weight: 600; letter-spacing: .005em; }
        [data-testid="stHeader"] { background: transparent; }

        /* --- sidebar go sam --- */
        [data-testid="stSidebar"] { border-right: 1px solid #3A2E25; }
        [data-testid="stSidebarNav"] [data-testid="stNavSectionHeader"], [data-testid="stSidebarNav"] header {
            font-size: .68rem !important; letter-spacing: .2em; text-transform: uppercase; color: #A8812F !important; font-weight: 600; }
        [data-testid="stSidebarNav"] a { border-radius: 2px; }
        [data-testid="stSidebarNav"] a[aria-current="page"] { background: rgba(168,129,47,.16); box-shadow: inset 2px 0 0 #C9A45C; }
        [data-testid="stSidebarNav"] a span { font-size: .9rem; }
        .sc-user { border-top: 1px solid #3A2E25; padding: 14px 2px 6px; margin-top: 8px; font-size: .85rem; color: #EDE4D3; }
        .sc-user .role { color: #B8AA95; font-size: .78rem; letter-spacing: .04em; }
        .sc-user .dot { display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:6px; vertical-align: 1px; }

        /* --- tieu de trang --- */
        .sc-head { margin: 0 0 26px 0; }
        .sc-eyebrow { font-size: .72rem; letter-spacing: .24em; text-transform: uppercase; color: var(--gold); font-weight: 600; }
        .sc-title { font-family: var(--serif); font-size: 2.45rem; line-height: 1.08; font-weight: 600; color: var(--ink); margin: 4px 0 6px; }
        .sc-sub { color: var(--muted); font-size: .95rem; font-weight: 300; max-width: 760px; }
        .sc-rule { display:flex; align-items:center; gap:10px; margin-top: 16px; }
        .sc-rule::before { content:""; height:1px; width:44px; background: var(--oxblood); }
        .sc-rule::after { content:""; height:1px; flex:1; background: var(--line); }
        .sc-rule span { width:6px; height:6px; transform: rotate(45deg); background: var(--gold); }
        .sc-section { font-family: var(--serif); font-size: 1.45rem; font-weight: 600; margin: 28px 0 10px; color: var(--ink);
                      border-bottom: 1px solid var(--line); padding-bottom: 6px; }
        .sc-section small { font-family: var(--sans); font-size: .8rem; color: var(--muted); font-weight: 300; margin-left: 10px; }

        /* --- the so lieu --- */
        .sc-kpis { display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 0; margin: 4px 0 18px;
                   border: 1px solid var(--line); background: var(--surface); }
        .sc-kpi { padding: 18px 20px 16px; border-right: 1px solid var(--line); position: relative; }
        .sc-kpi:last-child { border-right: none; }
        .sc-kpi::before { content:""; position:absolute; left:20px; top:0; width:28px; height:2px; background: var(--line); }
        .sc-kpi.ok::before { background: var(--ok); } .sc-kpi.warn::before { background: var(--warn); }
        .sc-kpi.danger::before { background: var(--danger); } .sc-kpi.primary::before { background: var(--oxblood); }
        .sc-kpi.info::before { background: var(--teal); }
        .sc-kpi-label { color: var(--muted); font-size: .7rem; font-weight: 600; letter-spacing: .14em; text-transform: uppercase; }
        .sc-kpi-value { font-size: 2.05rem; font-weight: 500; color: var(--ink); line-height: 1.15; margin-top: 8px;
                        font-variant-numeric: tabular-nums lining-nums; letter-spacing: -.01em; }
        .sc-kpi-value small { font-size: .95rem; color: var(--muted); font-weight: 300; }
        .sc-kpi-sub { color: var(--muted); font-size: .82rem; margin-top: 4px; font-weight: 300; }

        /* --- nhan trang thai --- */
        .sc-badge { display:inline-flex; align-items:center; gap:7px; padding: 3px 10px; border-radius: 2px; font-size: .74rem;
                    font-weight: 600; letter-spacing: .06em; text-transform: uppercase; border: 1px solid; white-space: nowrap; }
        .sc-badge::before { content:""; width:6px; height:6px; border-radius:50%; background: currentColor; }
        .sc-badge.ok { color: var(--ok); border-color: #C9D9CC; background: #F1F6F1; }
        .sc-badge.warn { color: #8A5E0B; border-color: #E8D6AE; background: #FBF4E4; }
        .sc-badge.danger { color: var(--danger); border-color: #E6C3BC; background: #FAEEEB; }
        .sc-badge.info { color: var(--teal); border-color: #C5D6D4; background: #EFF5F4; }
        .sc-badge.muted { color: var(--muted); border-color: var(--line); background: var(--surface); }

        .sc-bar { height: 6px; background: #EAE2D4; margin: 8px 0 6px; }
        .sc-bar > div { height: 100%; transition: width .4s; }
        .sc-meta { display:flex; justify-content: space-between; font-size: .8rem; color: var(--muted); letter-spacing: .02em; }
        .sc-note { border-left: 2px solid var(--gold); background: rgba(168,129,47,.06); padding: 10px 16px;
                   color: #5F554B; font-size: .86rem; line-height: 1.6; margin: 10px 0; }
        .sc-alert { padding: 13px 18px; margin-bottom: 14px; font-size: .95rem; border-left: 3px solid; }
        .sc-alert b { font-weight: 600; letter-spacing: .02em; }
        .sc-alert.danger { background: var(--oxblood); border-color: #C9A45C; color: #FBF4E8; }
        .sc-alert.warn { background: #F7EBCF; border-color: var(--warn); color: #5B3F07; }
        .sc-alert.info { background: #E7EFEE; border-color: var(--teal); color: #23443F; }
        .sc-item { border: 1px solid var(--line); background: var(--surface); padding: 12px 16px; margin-bottom: 8px; }
        .sc-item.danger { border-left: 3px solid var(--danger); }
        .sc-item .t { font-weight: 600; } .sc-item .m { color: var(--muted); font-size: .82rem; margin-top: 2px; }
        .sc-empty { color: var(--muted); font-size: .88rem; padding: 18px 0; font-style: italic; font-family: var(--serif); font-size: 1.05rem; }

        /* --- hinh camera truc tiep --- */
        .sc-live { position: relative; background: #14110F; border: 1px solid var(--line); aspect-ratio: 16 / 9;
                   max-height: 62vh; width: 100%; overflow: hidden; margin: 12px 0 12px; }
        .sc-live img { width: 100%; height: 100%; object-fit: contain; display: block; }
        .sc-live .tag { position: absolute; top: 10px; left: 10px; display: inline-flex; align-items: center; gap: 7px;
                        padding: 3px 10px; background: rgba(20,17,15,.72); color: #FBF4E8; border: 1px solid rgba(255,255,255,.16);
                        font-size: .68rem; font-weight: 600; letter-spacing: .16em; text-transform: uppercase; }
        .sc-live .tag::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: #D0453A;
                                animation: sc-pulse 1.6s ease-in-out infinite; }
        @keyframes sc-pulse { 50% { opacity: .25; } }
        .sc-live .full { position: absolute; top: 10px; right: 10px; }
        .sc-live .full a { display: inline-block; padding: 3px 10px; background: rgba(20,17,15,.72); color: #FBF4E8 !important;
                           border: 1px solid rgba(255,255,255,.16); font-size: .7rem; font-weight: 500; letter-spacing: .06em;
                           text-decoration: none !important; }
        .sc-live .full a:hover { background: var(--oxblood); }
        .sc-live.off { background: repeating-linear-gradient(135deg, var(--surface) 0 12px, #F4EEE3 12px 24px);
                       display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px;
                       text-align: center; padding: 0 24px; }
        .sc-live.off svg { width: 34px; height: 34px; opacity: .5; }
        .sc-live.off .t { font-family: var(--serif); font-size: 1.15rem; font-style: italic; color: var(--muted); }
        .sc-live.off .m { font-size: .8rem; color: var(--muted); font-weight: 300; }
        .sc-specs { display: grid; grid-template-columns: max-content 1fr; gap: 6px 22px; margin: 2px 0 4px; }
        .sc-specs.wide { grid-template-columns: max-content 1fr max-content 1fr; }
        .sc-specs span { font-size: .84rem; line-height: 1.45; }
        .sc-specs .k { color: var(--muted); font-weight: 400; }
        .sc-specs .v { color: var(--ink); font-weight: 500; overflow-wrap: anywhere; }
        .sc-camsub { color: var(--muted); font-size: .82rem; font-weight: 300; margin-top: 6px; }

        /* --- the Streamlit --- */
        div[data-testid="stVerticalBlockBorderWrapper"] { background: var(--surface); border-radius: 0 !important; border-color: var(--line) !important; }
        div[data-testid="stForm"] { background: var(--surface); border-radius: 0; border-color: var(--line); }
        .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button, [data-testid="stPopover"] button {
            border-radius: 2px; font-weight: 500; letter-spacing: .02em; border-color: #CFC3AF; }
        .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
            background: var(--oxblood); border-color: var(--oxblood); color: #FBF4E8; }
        .stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover { background: #63190F; border-color: #63190F; }
        /* o nhap lieu: nen + vien dat o .streamlit/config.toml (secondaryBackgroundColor, showWidgetBorder) */
        [data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"] { border-radius: 2px !important; }
        [data-testid="stWidgetLabel"] p { font-size: .82rem; font-weight: 500; color: #4E453D; letter-spacing: .01em; }
        [data-testid="stDataFrame"] { border: 1px solid var(--line); }
        [data-baseweb="tab-list"] { gap: 24px; border-bottom: 1px solid var(--line); }
        [data-baseweb="tab"] { font-weight: 500; letter-spacing: .02em; }
        [data-testid="stCaptionContainer"] { color: var(--muted); }
        </style>
        """
)
# Bo dong trong: dong trong lam Markdown cua Streamlit ngat khoi <style> va in CSS ra man hinh.
_THEME_CSS = "\n".join(line for line in _THEME_CSS_RAW.splitlines() if line.strip())


# ------------------------------------------------------------- thanh phan
def page_header(eyebrow: str, title: str, subtitle: str = ""):
    st.markdown(f'<div class="sc-head"><div class="sc-eyebrow">{eyebrow}</div><div class="sc-title">{title}</div>'
                f'<div class="sc-sub">{subtitle}</div><div class="sc-rule"><span></span></div></div>',
                unsafe_allow_html=True)


def section(title: str, small: str = ""):
    st.markdown(f'<div class="sc-section">{title}' + (f"<small>{small}</small>" if small else "") + "</div>",
                unsafe_allow_html=True)


def fmt_int(n) -> str:
    return "–" if n is None else f"{int(n):,}".replace(",", ".")


def fmt_pct(v) -> str:
    return "–" if v is None else f"{v:.0f}%" if float(v).is_integer() else f"{v:.1f}%"


def kpi(label: str, value, sub: str = "", tone: str = "") -> str:
    return (f'<div class="sc-kpi {tone}"><div class="sc-kpi-label">{label}</div>'
            f'<div class="sc-kpi-value">{value}</div><div class="sc-kpi-sub">{sub}</div></div>')


def kpi_row(cards):
    st.markdown('<div class="sc-kpis">' + "".join(cards) + "</div>", unsafe_allow_html=True)


def badge(text: str, tone: str = "muted") -> str:
    return f'<span class="sc-badge {tone}">{text}</span>'


def status_badge(code: str) -> str:
    m = STATUS_META.get(code, STATUS_META["OK"])
    return badge(m["label"], m["tone"])


def note(text: str):
    st.markdown(f'<div class="sc-note">{text}</div>', unsafe_allow_html=True)


def alert_box(text: str, tone: str = "danger"):
    st.markdown(f'<div class="sc-alert {tone}">{text}</div>', unsafe_allow_html=True)


def empty(text: str):
    st.markdown(f'<div class="sc-empty">{text}</div>', unsafe_allow_html=True)


def style_fig(fig, height=320, legend=True):
    fig.update_layout(height=height, margin=dict(l=4, r=4, t=26, b=4), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Be Vietnam Pro, sans-serif", color=C["ink"], size=12),
                      colorway=SERIES, showlegend=legend, bargap=0.35,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title_text="", font=dict(size=12)),
                      hoverlabel=dict(font_family="Be Vietnam Pro, sans-serif", bgcolor=C["surface"]))
    fig.update_xaxes(gridcolor="#ECE4D6", zeroline=False, linecolor=C["line"], tickfont=dict(color=C["muted"]))
    fig.update_yaxes(gridcolor="#ECE4D6", zeroline=False, linecolor=C["line"], tickfont=dict(color=C["muted"]))
    return fig


# ------------------------------------------------------------------- thoi gian
@st.cache_data(ttl=300, show_spinner=False)
def utc_offset_hours() -> float:
    try:
        return float(requests.get(f"{API_BASE}/health", timeout=3).json().get("utc_offset_hours", 7))
    except Exception:
        return 7.0


def to_local(iso_utc):
    if not iso_utc:
        return None
    return datetime.fromisoformat(str(iso_utc).replace("Z", "")) + timedelta(hours=utc_offset_hours())


def fmt_time(iso_utc, fmt="%H:%M:%S %d/%m/%Y") -> str:
    dt = to_local(iso_utc)
    return dt.strftime(fmt) if dt else "–"


def fmt_duration(seconds) -> str:
    if seconds is None:
        return "–"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds} giây"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m} phút {s:02d} giây"
    h, m = divmod(m, 60)
    return f"{h} giờ {m:02d} phút"


def fmt_mmss(seconds) -> str:
    """Thoi luong gon cho o KPI: 1:49 phut / 45 giay."""
    if seconds is None:
        return "–"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}<small> giây</small>"
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}<small> phút</small>"


def local_now():
    return datetime.utcnow() + timedelta(hours=utc_offset_hours())


def local_today():
    return local_now().date()


# ------------------------------------------------------------------- API
class ApiError(Exception):
    pass


def _headers():
    tok = st.session_state.get("token")
    return {"Authorization": f"Bearer {tok}"} if tok else {}


def _call(method, path, raw=False, **kw):
    try:
        r = requests.request(method, f"{API_BASE}{path}", headers=_headers(), timeout=20, **kw)
    except requests.RequestException:
        raise ApiError("Không kết nối được máy chủ. Hãy chạy backend: uvicorn backend.main:app --port 8000")
    if r.status_code == 401 and st.session_state.get("token"):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail", r.text)
        except ValueError:
            detail = r.text
        raise ApiError(detail if isinstance(detail, str) else str(detail))
    return r.content if raw else r.json()


def api_get(path, params=None):
    return _call("GET", path, params=params)


def api_get_bytes(path):
    return _call("GET", path, raw=True)


def api_post(path, payload=None, params=None):
    return _call("POST", path, json=payload, params=params)


def api_put(path, payload):
    return _call("PUT", path, json=payload)


def api_delete(path):
    return _call("DELETE", path)


def safe_get(path, params=None):
    try:
        return api_get(path, params)
    except ApiError as e:
        st.error(str(e))
        return None


def api_is_up() -> bool:
    try:
        return requests.get(f"{API_BASE}/health", timeout=2).status_code == 200
    except requests.RequestException:
        return False


# ------------------------------------------------------------------- dang nhap
def current_user():
    return st.session_state.get("user")


def has_role(*roles) -> bool:
    u = current_user()
    return bool(u) and u["role"] in roles


def restore_session() -> bool:
    """Giu dang nhap khi tai lai trang (F5): token nam o tham so ?s= tren URL."""
    if st.session_state.get("token"):
        st.query_params["s"] = st.session_state["token"]
        return True
    tok = st.query_params.get("s")
    if not tok:
        return False
    try:
        r = requests.get(f"{API_BASE}/auth/me", headers={"Authorization": f"Bearer {tok}"}, timeout=5)
    except requests.RequestException:
        return False
    if r.status_code != 200:
        del st.query_params["s"]
        return False
    st.session_state["token"], st.session_state["user"] = tok, r.json()
    return True


BRIDGE_SVG = """<svg viewBox="0 0 360 150" xmlns="http://www.w3.org/2000/svg" fill="none" stroke="#C9A45C" stroke-width="1.4">
<path d="M10 128 H350"/><path d="M40 128 Q180 70 320 128" />
<path d="M70 114 V86 M110 100 V78 M150 92 V72 M210 92 V72 M250 100 V78 M290 114 V86"/>
<path d="M58 88 Q180 40 302 88"/><path d="M52 86 L180 26 L308 86"/>
<path d="M150 40 L180 14 L210 40"/><path d="M174 14 V6 M186 14 V6"/>
<circle cx="120" cy="96" r="3"/><circle cx="240" cy="96" r="3"/>
<path d="M10 140 Q40 134 70 140 T130 140 T190 140 T250 140 T310 140 T350 140" stroke-opacity=".5"/>
</svg>"""


def login_page():
    apply_theme()
    st.markdown("<style>.block-container{max-width:1100px;padding-top:6vh}</style>", unsafe_allow_html=True)
    left, gap, right = st.columns([1.15, .12, 1])
    with left:
        st.markdown(
            f"""<div style="background:#1E1814;color:#EDE4D3;padding:44px 42px 36px;min-height:520px;position:relative">
            <div style="font-size:.7rem;letter-spacing:.3em;color:#C9A45C;font-weight:600">HỘI AN · DI SẢN THẾ GIỚI</div>
            <div style="font-family:var(--serif);font-size:3.1rem;line-height:1.05;margin:18px 0 10px;font-weight:600">Chùa Cầu</div>
            <div style="font-family:var(--serif);font-size:1.35rem;color:#C9B89C;font-style:italic">Lai Viễn Kiều · 1593</div>
            <div style="width:44px;height:1px;background:#C9A45C;margin:26px 0"></div>
            <div style="font-size:.92rem;line-height:1.75;color:#CDBFA8;font-weight:300;max-width:380px">
            Hệ thống camera AI giám sát lượng khách, cảnh báo quá tải và phân tích cơ cấu du khách,
            giúp gìn giữ di tích và an toàn cho người tham quan.</div>
            <div style="margin-top:40px;opacity:.9">{BRIDGE_SVG}</div>
            <div style="position:absolute;bottom:22px;left:42px;font-size:.72rem;color:#8F826F;letter-spacing:.08em">
            SMARTCAU AI · NHÓM 50 · ĐẠI HỌC KINH TẾ ĐÀ NẴNG</div></div>""",
            unsafe_allow_html=True)
    with right:
        st.markdown('<div style="height:70px"></div><div class="sc-eyebrow">Đăng nhập hệ thống</div>'
                    '<div class="sc-title" style="font-size:2.1rem">Trạm quản lý</div>'
                    '<div class="sc-sub">Dành cho người trực, cán bộ quản lý và quản trị viên.</div>'
                    '<div class="sc-rule" style="margin-bottom:22px"><span></span></div>', unsafe_allow_html=True)
        if not api_is_up():
            alert_box("Chưa kết nối được máy chủ.", "warn")
        st.markdown("<style>div[data-testid='stForm']{background:transparent !important;border:none !important;padding:0 !important}"
                    "[data-baseweb='input']{height:46px}</style>", unsafe_allow_html=True)
        with st.form("login", border=False):
            username = st.text_input("Tên đăng nhập")
            password = st.text_input("Mật khẩu", type="password")
            ok = st.form_submit_button("Đăng nhập", type="primary", width="stretch")
        if ok:
            try:
                r = requests.post(f"{API_BASE}/auth/login", json={"username": username, "password": password}, timeout=8)
            except requests.RequestException:
                st.error("Không kết nối được máy chủ.")
                return
            if r.status_code == 200:
                d = r.json()
                st.session_state["token"] = d.pop("token")
                st.session_state["user"] = d
                st.query_params["s"] = st.session_state["token"]
                st.rerun()
            else:
                try:
                    st.error(r.json().get("detail", "Đăng nhập thất bại."))
                except ValueError:
                    st.error("Đăng nhập thất bại.")


def change_password_form(forced=False):
    if forced:
        note("Bạn đang dùng mật khẩu mặc định hoặc mật khẩu tạm do quản trị viên đặt. Hãy đổi mật khẩu để tiếp tục.")
    with st.form("change_pw", clear_on_submit=True):
        old = st.text_input("Mật khẩu hiện tại", type="password")
        new = st.text_input("Mật khẩu mới (ít nhất 6 ký tự)", type="password")
        new2 = st.text_input("Nhập lại mật khẩu mới", type="password")
        ok = st.form_submit_button("Đổi mật khẩu", type="primary")
    if ok:
        if new != new2:
            st.error("Hai lần nhập mật khẩu mới không khớp.")
            return
        try:
            api_post("/auth/change_password", {"old_password": old, "new_password": new})
            st.session_state["user"]["must_change_password"] = False
            st.success("Đã đổi mật khẩu.")
            st.rerun()
        except ApiError as e:
            st.error(str(e))


def logout():
    try:
        api_post("/auth/logout")
    except ApiError:
        pass
    st.session_state.clear()
    st.query_params.clear()
    st.rerun()


# ------------------------------------------------------------- so do cau truc quan
LEVEL_COLOR = {"OK": C["ok"], "WARNING": C["warn"], "ALERT": C["warn"], "CRITICAL": C["danger"]}


def bridge_svg(count: int, cap: int, level: str = "OK", in_rate=None, out_rate=None) -> str:
    """So do Chua Cau: moi cham = 1 nguoi dang tren cau, mau theo muc canh bao."""
    col = LEVEL_COLOR.get(level, C["ok"])
    n = max(0, int(count))
    slots = max(cap, n)
    dots = []
    for i in range(min(n, 60)):
        t = (i + 0.5) / max(slots, 1)
        x = 110 + t * 380
        y = 150 - 46 * (1 - (2 * t - 1) ** 2) - (10 if i % 2 else 0)
        dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{col}" opacity=".92"><animate attributeName="r" '
                    f'values="6;6.6;6" dur="{2 + (i % 5) * .3:.1f}s" repeatCount="indefinite"/></circle>')
    pct = min(100, round(n / cap * 100)) if cap else 0
    rate_in = "" if in_rate is None else f"vào {str(in_rate).replace('.', ',')}/phút"
    rate_out = "" if out_rate is None else f"ra {str(out_rate).replace('.', ',')}/phút"
    return f"""
<svg viewBox="0 0 600 246" width="100%" xmlns="http://www.w3.org/2000/svg" style="display:block">
  <defs><linearGradient id="w" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#C9D8D5"/><stop offset="1" stop-color="#EEF2EF"/></linearGradient></defs>
  <rect x="0" y="182" width="600" height="48" fill="url(#w)" opacity=".55"/>
  <path d="M0 196 Q50 190 100 196 T200 196 T300 196 T400 196 T500 196 T600 196" stroke="#9FB6B2" fill="none" stroke-width="1"/>
  <path d="M60 172 Q300 70 540 172" stroke="{C['wood']}" stroke-width="7" fill="none" stroke-linecap="round"/>
  <path d="M60 182 Q300 92 540 182" stroke="{C['wood']}" stroke-width="2" fill="none" opacity=".5"/>
  <path d="M96 118 L300 40 L504 118" stroke="{C['oxblood']}" stroke-width="3" fill="none" stroke-linejoin="round"/>
  <path d="M260 56 L300 26 L340 56" stroke="{C['oxblood']}" stroke-width="3" fill="none"/>
  <path d="M120 112 V150 M200 84 V128 M300 62 V112 M400 84 V128 M480 112 V150" stroke="{C['wood']}" stroke-width="2" opacity=".55"/>
  {''.join(dots)}
  <text x="22" y="200" font-family="Be Vietnam Pro" font-size="12" fill="{C['muted']}">CHÂN CẦU 1</text>
  <text x="578" y="200" text-anchor="end" font-family="Be Vietnam Pro" font-size="12" fill="{C['muted']}">CHÂN CẦU 2</text>
  <text x="22" y="218" font-family="Be Vietnam Pro" font-size="12" fill="{C['teal']}">{rate_in}</text>
  <text x="578" y="218" text-anchor="end" font-family="Be Vietnam Pro" font-size="12" fill="{C['teal']}">{rate_out}</text>
  <text x="300" y="238" text-anchor="middle" font-family="Cormorant Garamond, serif" font-size="22" font-weight="600" fill="{col}">{n} / {cap} người · {pct}%</text>
</svg>"""


TONE_MARK = {"up": ("▲", C["ok"]), "down": ("▼", C["danger"]), "warn": ("!", C["warn"]), "info": ("i", C["teal"])}


def insight_list(items):
    rows = []
    for it in items:
        mark, col = TONE_MARK.get(it["tone"], TONE_MARK["info"])
        rows.append(f'<div style="display:flex;gap:12px;padding:10px 0;border-bottom:1px solid var(--line)">'
                    f'<div style="flex:0 0 22px;height:22px;border:1px solid {col};color:{col};font-size:.7rem;font-weight:700;'
                    f'display:flex;align-items:center;justify-content:center;margin-top:2px">{mark}</div>'
                    f'<div><div style="font-weight:600;font-size:.9rem">{it["title"]}</div>'
                    f'<div style="color:#5F554B;font-size:.88rem;line-height:1.55">{it["text"]}</div></div></div>')
    st.markdown("".join(rows), unsafe_allow_html=True)


def alert_watcher():
    """Thong bao noi (toast) o MOI trang khi co su co Do moi, doan khach lon, mat tin hieu camera."""
    @st.fragment(run_every=5)
    def _watch():
        try:
            incidents = api_get("/incidents", {"status": "open"})
            events = api_get("/system_events", {"limit": 15})
        except ApiError:
            return
        seen = st.session_state.setdefault("_seen_alerts", None)
        current = {f"i{i['id']}" for i in incidents} | {f"e{e['id']}" for e in events}
        if seen is None:                      # lan dau mo trang: chi ghi nho, khong bao lai chuyen cu
            st.session_state["_seen_alerts"] = current
        else:
            for i in incidents:
                if f"i{i['id']}" not in seen:
                    st.toast(f"**Cảnh báo Đỏ · sự cố #{i['id']}** — {i['peak_count']} người trên cầu. "
                             "Mở trang Trực ca để xác nhận.", icon=":material/warning:")
            for e in events:
                if f"e{e['id']}" not in seen and e["event_type"] in ("GROUP_DETECTED", "CAMERA_LOST", "WARNING"):
                    st.toast(f"**{e['label']}** — {(e['message'] or '').replace('[SmartCau AI] ', '')[:110]}",
                             icon=":material/groups:" if e["event_type"] == "GROUP_DETECTED" else ":material/notifications:")
            st.session_state["_seen_alerts"] = seen | current
        if incidents:
            st.markdown(f'<div style="margin-top:10px;padding:8px 10px;border:1px solid #8E2418;background:rgba(142,36,24,.25);'
                        f'color:#F3D9D3;font-size:.8rem">● {len(incidents)} sự cố đang mở</div>', unsafe_allow_html=True)
    _watch()
