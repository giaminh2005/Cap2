"""
frontend/common.py  —  Thanh phan DUNG CHUNG cua giao dien (MODULE M2, phu trach: Minh)
=======================================================================================
Theme, dang nhap, goi API kem token, nhan tieng Viet, the KPI, bieu do.
Moi trang trong frontend/views/ chi can:   from common import ...
"""

import os
from datetime import datetime, timedelta

import requests
import streamlit as st

try:
    import plotly.graph_objects as go  # noqa: F401
    import plotly.express as px  # noqa: F401
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

API_BASE = os.environ.get("SMARTCAU_API", "http://127.0.0.1:8000")

# ------------------------------------------------------------ nhan tieng Viet
GENDER_VI = {"Man": "Nam", "Woman": "Nữ", None: "Không xác định"}
ORIGIN_VI = {"Trong nuoc": "Trong nước", "Nuoc ngoai": "Nước ngoài", None: "Chưa rõ"}
AGE_ORDER = ["0-5", "6-12", "13-17", "18-24", "25-34", "35-44", "45-54", "55-64", "65-69", "70+"]
ROLE_VI = {"admin": "Quản trị viên", "quan_ly": "Quản lý", "nguoi_truc": "Người trực"}
STATUS_META = {
    "OK": {"label": "Bình thường", "tone": "ok", "icon": "●"},
    "WARNING": {"label": "Cảnh báo Vàng", "tone": "warn", "icon": "▲"},
    "ALERT": {"label": "Vàng · đang xác nhận", "tone": "warn", "icon": "▲"},
    "CRITICAL": {"label": "Cảnh báo Đỏ · Quá tải", "tone": "danger", "icon": "■"},
}
EVENT_TONE = {"WARNING": "warn", "CRITICAL_ALERT": "danger", "CRITICAL_CLEARED": "ok", "GROUP_DETECTED": "info",
              "CAMERA_LOST": "danger", "CAMERA_RESTORED": "ok", "GATE_CLOSED": "warn", "GATE_REOPENED": "ok"}

COLORS = {"primary": "#8E2A1F", "ochre": "#C0862B", "moss": "#3E7B57", "blue": "#2F6690",
          "ink": "#2A2420", "muted": "#7A6F66", "line": "#E7E0D6", "bg": "#F7F4EE",
          "danger": "#B3261E", "warn": "#C98A12", "ok": "#2E7D4F"}
SERIES = ["#8E2A1F", "#C0862B", "#2F6690", "#3E7B57", "#7B5EA7", "#9C6644"]


# ------------------------------------------------------------------- theme
def apply_theme():
    st.markdown(
        """
        <link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
        :root { --primary:#8E2A1F; --ochre:#C0862B; --moss:#3E7B57; --ink:#2A2420; --muted:#7A6F66;
                --line:#E7E0D6; --card:#FFFFFF; --bg:#F7F4EE; --danger:#B3261E; --warn:#C98A12; --ok:#2E7D4F; --info:#2F6690; }
        html, body, [class*="css"], .stApp, button, input, textarea, select { font-family: 'Be Vietnam Pro', system-ui, sans-serif !important; }
        .stApp { background: var(--bg); color: var(--ink); }
        .block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1280px; }
        [data-testid="stSidebar"] { background: #FFFDF9; border-right: 1px solid var(--line); }
        [data-testid="stSidebarNav"] a span { font-weight: 500; }
        h1, h2, h3 { color: var(--ink); letter-spacing: -0.01em; }
        .sc-header { display:flex; align-items:center; gap:14px; margin: 0 0 18px 0; }
        .sc-header-icon { width:46px; height:46px; border-radius:12px; background:var(--primary); color:#fff;
                          display:flex; align-items:center; justify-content:center; font-size:22px; flex-shrink:0; }
        .sc-title { font-size: 1.55rem; font-weight: 800; line-height:1.2; margin:0; color:var(--ink); }
        .sc-sub { color: var(--muted); font-size: .92rem; margin-top: 2px; }
        .sc-kpis { display:grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap:12px; margin: 4px 0 16px 0; }
        .sc-kpi { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:14px 16px;
                  box-shadow: 0 1px 2px rgba(42,36,32,.04); border-left: 4px solid var(--line); }
        .sc-kpi.ok { border-left-color: var(--ok); } .sc-kpi.warn { border-left-color: var(--warn); }
        .sc-kpi.danger { border-left-color: var(--danger); } .sc-kpi.info { border-left-color: var(--info); }
        .sc-kpi.primary { border-left-color: var(--primary); }
        .sc-kpi-label { color:var(--muted); font-size:.8rem; font-weight:600; text-transform:uppercase; letter-spacing:.04em; }
        .sc-kpi-value { font-size:1.9rem; font-weight:800; color:var(--ink); line-height:1.15; margin-top:4px; font-variant-numeric: tabular-nums; }
        .sc-kpi-sub { color:var(--muted); font-size:.85rem; margin-top:2px; }
        .sc-badge { display:inline-flex; align-items:center; gap:6px; padding:3px 10px; border-radius:999px;
                    font-size:.82rem; font-weight:700; border:1px solid transparent; white-space:nowrap; }
        .sc-badge.ok { background:#E5F2EA; color:var(--ok); border-color:#C7E3D2; }
        .sc-badge.warn { background:#FBF0D9; color:#8A5D05; border-color:#F0DBAA; }
        .sc-badge.danger { background:#FBE3E1; color:var(--danger); border-color:#F2C2BE; }
        .sc-badge.info { background:#E3EDF5; color:var(--info); border-color:#C5D8E8; }
        .sc-badge.muted { background:#EFEBE5; color:var(--muted); border-color:var(--line); }
        .sc-bar { height:14px; background:#EFEBE5; border-radius:999px; overflow:hidden; margin:6px 0 4px; }
        .sc-bar > div { height:100%; border-radius:999px; transition: width .4s; }
        .sc-note { background:#FFFDF9; border:1px dashed var(--line); border-radius:12px; padding:10px 14px;
                   color:var(--muted); font-size:.86rem; }
        .sc-alert { border-radius:14px; padding:14px 18px; font-weight:700; margin-bottom:14px; font-size:1.02rem; }
        .sc-alert.danger { background:var(--danger); color:#fff; } .sc-alert.warn { background:#F6E2B3; color:#5E3F03; }
        .sc-alert.info { background:#E3EDF5; color:var(--info); }
        .sc-incident { background:#fff; border:1px solid #F2C2BE; border-left:6px solid var(--danger);
                       border-radius:14px; padding:12px 16px; margin-bottom:8px; }
        .sc-brand { font-weight:800; font-size:1.15rem; color:var(--primary); }
        .sc-brand-sub { color:var(--muted); font-size:.75rem; letter-spacing:.08em; text-transform:uppercase; }
        .sc-user { background:var(--bg); border:1px solid var(--line); border-radius:12px; padding:10px 12px; margin:8px 0; font-size:.88rem; }
        div[data-testid="stForm"], div[data-testid="stVerticalBlockBorderWrapper"] { background: var(--card); border-radius: 14px; }
        .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button { border-radius: 10px; font-weight: 600; }
        .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] { background: var(--primary); border-color: var(--primary); }
        [data-testid="stDataFrame"] { border-radius: 12px; overflow: hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------- thanh phan
def page_header(icon: str, title: str, subtitle: str = ""):
    st.markdown(f'<div class="sc-header"><div class="sc-header-icon">{icon}</div><div>'
                f'<div class="sc-title">{title}</div><div class="sc-sub">{subtitle}</div></div></div>',
                unsafe_allow_html=True)


def fmt_int(n) -> str:
    return "–" if n is None else f"{int(n):,}".replace(",", ".")


def kpi(label: str, value, sub: str = "", tone: str = "") -> str:
    return (f'<div class="sc-kpi {tone}"><div class="sc-kpi-label">{label}</div>'
            f'<div class="sc-kpi-value">{value}</div><div class="sc-kpi-sub">{sub}</div></div>')


def kpi_row(cards):
    st.markdown('<div class="sc-kpis">' + "".join(cards) + "</div>", unsafe_allow_html=True)


def badge(text: str, tone: str = "muted") -> str:
    return f'<span class="sc-badge {tone}">{text}</span>'


def status_badge(code: str) -> str:
    m = STATUS_META.get(code, STATUS_META["OK"])
    return badge(f"{m['icon']} {m['label']}", m["tone"])


def note(text: str):
    st.markdown(f'<div class="sc-note">{text}</div>', unsafe_allow_html=True)


def alert_box(text: str, tone: str = "danger"):
    st.markdown(f'<div class="sc-alert {tone}">{text}</div>', unsafe_allow_html=True)


def capacity_bar(count: int, maximum: int):
    pct = min(100, round(count / maximum * 100)) if maximum else 0
    warn_at = round(maximum * 0.75)
    color = COLORS["danger"] if count > maximum else COLORS["warn"] if count >= warn_at else COLORS["ok"]
    st.markdown(f'<div style="display:flex;justify-content:space-between;font-size:.85rem;color:var(--muted)">'
                f'<span>Sức chứa cầu</span><span><b style="color:var(--ink)">{count}/{maximum}</b> người ({pct}%)</span></div>'
                f'<div class="sc-bar"><div style="width:{pct}%;background:{color}"></div></div>',
                unsafe_allow_html=True)


def style_fig(fig, height=320, legend=True):
    fig.update_layout(height=height, margin=dict(l=8, r=8, t=30, b=8), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Be Vietnam Pro, sans-serif", color="#2A2420", size=13),
                      colorway=SERIES, showlegend=legend,
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title_text=""),
                      hoverlabel=dict(font_family="Be Vietnam Pro, sans-serif"))
    fig.update_xaxes(gridcolor="#EFEBE5", zeroline=False)
    fig.update_yaxes(gridcolor="#EFEBE5", zeroline=False)
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


def local_today():
    return (datetime.utcnow() + timedelta(hours=utc_offset_hours())).date()


# ------------------------------------------------------------------- API
class ApiError(Exception):
    pass


def _headers():
    tok = st.session_state.get("token")
    return {"Authorization": f"Bearer {tok}"} if tok else {}


def _call(method, path, **kw):
    try:
        r = requests.request(method, f"{API_BASE}{path}", headers=_headers(), timeout=10, **kw)
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
    return r.json()


def api_get(path, params=None):
    return _call("GET", path, params=params)


def api_post(path, payload=None, params=None):
    return _call("POST", path, json=payload, params=params)


def api_put(path, payload):
    return _call("PUT", path, json=payload)


def api_delete(path):
    return _call("DELETE", path)


def safe_get(path, params=None):
    """GET va tu hien loi tren trang; tra ve None neu loi."""
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


def login_page():
    apply_theme()
    _, mid, _ = st.columns([1, 1.1, 1])
    with mid:
        st.markdown('<div style="text-align:center;margin:48px 0 18px">'
                    '<div style="font-size:44px">🏯</div>'
                    '<div class="sc-title" style="font-size:1.8rem">SmartCau AI</div>'
                    '<div class="sc-sub">Hệ thống camera AI quản lý đám đông · Chùa Cầu Hội An</div></div>',
                    unsafe_allow_html=True)
        if not api_is_up():
            st.error("Chưa kết nối được máy chủ. Hãy chạy backend trước:\n\n"
                     "`uvicorn backend.main:app --reload --port 8000`")
        with st.form("login"):
            username = st.text_input("Tên đăng nhập", placeholder="vd: admin")
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
        st.caption("Lần đầu sử dụng: tài khoản **admin**, mật khẩu **admin123** — hệ thống sẽ yêu cầu đổi mật khẩu.")


def change_password_form(forced=False):
    if forced:
        st.warning("Bạn đang dùng mật khẩu mặc định hoặc mật khẩu do quản trị viên đặt. Hãy đổi mật khẩu để tiếp tục.")
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
