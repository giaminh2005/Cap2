"""
frontend/common.py  —  Thanh phan DUNG CHUNG cua giao dien (phu trach: Minh)
=============================================================================
Tach ra tu admin_web/app.py cu: theme Hoi An, ham goi API, the KPI, dang
nhap. Moi trang trong frontend/views/ chi can:

    from common import api_get, page_header, render_metric, ...

Muon them ham dung chung moi -> nhan Minh them vao day (tranh 2 nguoi
cung sua file nay mot luc).
"""

import os
import sys
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

# streamlit-option-menu va plotly la "do trang tri" (giao dien dep hon) -
# KHONG bat buoc de trang chay duoc: neu may ban chua cai (vd quen chay
# pip install -r requirements.txt sau khi cap nhat), trang se tu dong
# chuyen ve phien ban don gian hon o dung do thay vi bao loi va sap trang.
try:
    from streamlit_option_menu import option_menu
    _HAS_OPTION_MENU = True
except ImportError:
    _HAS_OPTION_MENU = False

try:
    import plotly.express as px
    _HAS_PLOTLY = True
except ImportError:
    _HAS_PLOTLY = False


# Cho phep import google_sheets_sync.py tu thu muc ../tools
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))

API_BASE = os.environ.get("SMARTCAU_API", "http://127.0.0.1:8000")
ADMIN_WEB_PASSWORD = os.environ.get("ADMIN_WEB_PASSWORD", "admin123")
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "")
USING_DEMO_PASSWORD = "ADMIN_WEB_PASSWORD" not in os.environ

# Nhan hien thi tieng Viet - DU LIEU THAT phia backend/camera van giu
# nguyen gia tri goc (vd "Man"/"Woman", "OK"/"WARNING"/...) de khop CHINH
# XAC voi nhung gi age_gender_estimator.py / crowd_counter.py dang ghi;
# o day CHI doi nhan hien thi cho nguoi dung xem, khong doi du lieu that.
GENDER_LABEL_VI = {"Man": "Nam", "Woman": "Nu"}
GENDER_VALUE_FROM_VI = {v: k for k, v in GENDER_LABEL_VI.items()}

AGE_ORDER = ["0-5", "6-12", "13-17", "18-24", "25-34", "35-44", "45-54",
             "55-64", "65-69", "70+", "Khong ro"]

# Mau trang thai lay tu CHINH bang mau di san (son son - vang dong - rong
# reu - tram) de dong bo voi toan bo giao dien, thay vi mau xanh-do mac
# dinh thuong thay tren web hien dai.
STATUS_META = {
    "OK": {"label": "Binh thuong", "badge": "ok", "icon": "✅"},
    "WARNING": {"label": "Gan nguong - theo doi", "badge": "warn", "icon": "⚠️"},
    "ALERT": {"label": "Vuot nguong - can canh bao", "badge": "alert", "icon": "\U0001F6A8"},
    "CRITICAL": {"label": "Qua tai nghiem trong", "badge": "critical", "icon": "⛔"},
}


# ---------------------------------------------------------------- theme & style
def apply_custom_theme():
    """Giao dien SmartCau AI lay cam hung tu pho co Hoi An: giay do am
    mau, son mai do - vang dong, font chu serif cho tieu de (Playfair
    Display) phoi voi font sans-serif ho tro tieng Viet day du (Be Vietnam
    Pro) cho phan noi dung - giu cam giac di san nhung van ro rang, de
    doc tren man hinh (khac voi lam banner/pano trang tri thuan tuy)."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@300;400;500;600;700&family=Playfair+Display:wght@600;700;800&display=swap');

    :root {
        --hoian-cream: #F7F0E3;
        --hoian-paper: #FFFDF7;
        --hoian-yellow: #D8A548;
        --hoian-ochre: #B77A2B;
        --hoian-red: #7A3028;
        --hoian-red-dark: #54221E;
        --hoian-wood: #563B2D;
        --hoian-moss: #344B3B;
        --hoian-ink: #30251F;
        --hoian-muted: #78685A;
        --hoian-line: #D8BD8A;
    }

    html, body, [class*="css"], p, span, div, label, input, button, textarea {
        font-family: 'Be Vietnam Pro', sans-serif;
    }

    .stApp {
        background:
            radial-gradient(ellipse at 95% 0%, rgba(216,165,72,.13), transparent 28%),
            linear-gradient(135deg, #F7F0E3 0%, #FBF7EF 54%, #F4E8D3 100%) !important;
        color: var(--hoian-ink);
    }

    .block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1180px; }

    [data-testid="stHeader"] {
        background: rgba(255,253,247,.88) !important;
        border-bottom: 1px solid rgba(183,122,43,.24);
    }

    [data-testid="stSidebar"] {
        background:
            linear-gradient(rgba(255,253,247,.96), rgba(247,240,227,.98)),
            repeating-linear-gradient(45deg, transparent 0 12px, rgba(183,122,43,.08) 12px 14px) !important;
        border-right: 2px solid var(--hoian-ochre) !important;
        box-shadow: 5px 0 24px rgba(86,59,45,.07);
    }
    [data-testid="stSidebar"] > div:first-child { padding-top: 1.25rem; }

    h1, h2, h3 {
        font-family: 'Playfair Display', Georgia, serif !important;
        color: var(--hoian-red-dark) !important;
        letter-spacing: -.02em;
    }
    h2, h3 { color: var(--hoian-wood) !important; }

    p, label, [data-testid="stMarkdownContainer"] { color: var(--hoian-ink); }
    [data-testid="stCaptionContainer"] { color: var(--hoian-muted) !important; }

    /* ---- banner tieu de trang (thay the st.title - 1 khoi duy nhat,
       giong 1 tam bang hieu son mai pho co) ---- */
    .hoian-page-header {
        display: flex; align-items: center; gap: 18px;
        background: linear-gradient(110deg, rgba(122,48,40,.97), rgba(84,34,30,.97));
        color: #FFF8E8; padding: 22px 28px; border-radius: 14px;
        border: 1px solid var(--hoian-yellow);
        box-shadow: 0 10px 24px rgba(86,59,45,.18);
        margin-bottom: 26px; position: relative; overflow: hidden;
    }
    .hoian-page-header:after {
        content: "❖"; position: absolute; right: 20px; top: 2px;
        font-size: 3rem; color: rgba(255,225,164,.16); pointer-events: none;
    }
    .hoian-page-header-icon { font-size: 2.3rem; line-height: 1; flex-shrink: 0; }
    .hoian-page-eyebrow {
        font-size: .68rem; letter-spacing: .22em; text-transform: uppercase;
        color: #F0D49A; font-weight: 700;
    }
    .hoian-page-title {
        font-family: 'Playfair Display', Georgia, serif; font-size: 1.55rem;
        font-weight: 800; margin-top: 2px; color: #FFF8E8; letter-spacing: -.01em;
    }
    .hoian-page-desc { font-size: .86rem; color: #F3E6CE; margin-top: 5px; line-height: 1.5; }

    /* ---- the thong ke: nen giay do, vien go va dai do den long ---- */
    .hoian-kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 22px; }
    @media (max-width: 900px) { .hoian-kpi-row { grid-template-columns: repeat(2, 1fr); } }
    .custom-metric-card {
        background: linear-gradient(135deg, rgba(255,253,247,.98), rgba(255,248,232,.98));
        border: 1px solid var(--hoian-line);
        border-top: 5px solid var(--hoian-red);
        border-radius: 12px 12px 7px 7px;
        padding: 18px 20px 20px;
        box-shadow: 0 7px 18px rgba(86,59,45,.09);
        text-align: left; min-height: 116px; position: relative; overflow: hidden;
    }
    .custom-metric-card:after {
        content: "❖"; position: absolute; right: 12px; bottom: -16px;
        font-size: 3.7rem; color: rgba(183,122,43,.10); pointer-events: none;
    }
    .custom-metric-label {
        color: var(--hoian-wood); font-size: .86rem; font-weight: 600;
        margin-bottom: 8px; position: relative; z-index: 1;
    }
    .custom-metric-value {
        font-family: 'Playfair Display', Georgia, serif; color: var(--hoian-red-dark);
        font-size: 2.05rem; font-weight: 700; line-height: 1.2;
        overflow-wrap: anywhere; position: relative; z-index: 1;
    }
    .custom-metric-sub { font-size: 1.05rem; color: var(--hoian-muted); font-weight: 600; }

    /* ---- huy hieu trang thai (dong bo voi bang mau di san) ---- */
    .hoian-badge {
        display: inline-flex; align-items: center; gap: 6px; padding: 6px 14px;
        border-radius: 999px; font-size: .95rem; font-weight: 700; border: 1px solid transparent;
    }
    .hoian-badge-ok { background: #E4ECE4; color: var(--hoian-moss); border-color: rgba(52,75,59,.25); }
    .hoian-badge-warn { background: #F7E9CF; color: #8A5A1E; border-color: rgba(183,122,43,.3); }
    .hoian-badge-alert { background: #F3DCC9; color: #9A4A22; border-color: rgba(122,48,40,.3); }
    .hoian-badge-critical { background: #F2D9D5; color: var(--hoian-red-dark); border-color: rgba(84,34,30,.35); }

    /* ---- thanh suc chua (tien do) ---- */
    .hoian-progress-wrap { margin: -6px 0 20px 0; }
    .hoian-progress-top {
        display: flex; justify-content: space-between; font-size: .82rem;
        color: var(--hoian-muted); font-weight: 600; margin-bottom: 6px;
    }
    .hoian-progress-track { width: 100%; height: 11px; background: #ECE0C8; border-radius: 999px; overflow: hidden; }
    .hoian-progress-fill { height: 100%; border-radius: 999px; transition: width .4s ease; }

    /* ---- khung the/noi dung (st.container(border=True)) ---- */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid var(--hoian-line) !important;
        border-radius: 14px !important;
        background: rgba(255,253,247,.65) !important;
    }

    /* ---- sidebar ---- */
    [data-testid="stSidebar"] div[role="radiogroup"] label {
        background: rgba(122,48,40,.05); border-radius: 10px; padding: 9px 12px; margin-bottom: 4px;
        border: 1px solid transparent;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover { background: rgba(183,122,43,.12); }
    .hoian-side-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
    .hoian-brand {
        background: linear-gradient(135deg, #FFFDF7, #F2E2C3);
        border: 1px solid var(--hoian-line); border-left: 5px solid var(--hoian-red);
        border-radius: 8px; padding: 12px 12px 10px; margin-bottom: 12px;
        box-shadow: 0 3px 12px rgba(86,59,45,.06);
    }
    .hoian-brand-title {
        color: var(--hoian-red-dark); font-family: 'Playfair Display', Georgia, serif;
        font-size: 1.14rem; font-weight: 700;
    }
    .hoian-brand-subtitle { color: var(--hoian-muted); font-size: .72rem; margin-top: 3px; letter-spacing: .03em; }
    .hoian-sidebar-note {
        margin-top: 18px; padding: 12px 10px; text-align: center;
        border-top: 1px solid var(--hoian-line); color: var(--hoian-muted);
        font-size: .76rem; line-height: 1.7;
    }

    /* ---- nut bam theo mau son va vang dong ---- */
    .stButton > button, .stDownloadButton > button {
        border: 1px solid var(--hoian-ochre) !important;
        border-radius: 8px !important;
        background: var(--hoian-red) !important;
        color: #FFFDF7 !important;
        font-weight: 600 !important;
        transition: all .18s ease-in-out;
        box-shadow: 0 3px 8px rgba(122,48,40,.12);
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        background: var(--hoian-red-dark) !important;
        border-color: var(--hoian-yellow) !important;
        transform: translateY(-1px);
    }

    /* ---- truong nhap lieu ---- */
    [data-baseweb="input"], [data-baseweb="select"], [data-baseweb="textarea"] {
        border-color: var(--hoian-line) !important;
        border-radius: 8px !important;
        background: var(--hoian-paper) !important;
    }
    [data-baseweb="input"] input, [data-baseweb="textarea"] textarea { color: var(--hoian-ink) !important; }

    /* ---- thong bao, bang, duong ke ---- */
    [data-testid="stAlert"] { border-radius: 10px; border: 1px solid rgba(183,122,43,.24); }
    [data-testid="stDataFrame"], [data-testid="stTable"] {
        border: 1px solid var(--hoian-line); border-radius: 10px; overflow: hidden;
    }
    hr { border-color: var(--hoian-line) !important; }
    a { color: var(--hoian-red) !important; }

    /* ---- the thuong hieu dang nhap ---- */
    .hoian-login-card {
        background: rgba(255,253,247,.85); border: 1px solid var(--hoian-line);
        border-top: 5px solid var(--hoian-red); border-radius: 14px 14px 8px 8px;
        padding: 26px 28px 22px; box-shadow: 0 12px 28px rgba(86,59,45,.1);
    }

    @media (max-width: 768px) {
        .custom-metric-card { padding: 15px; min-height: 100px; }
        .custom-metric-value { font-size: 1.65rem; }
        .hoian-page-title { font-size: 1.25rem; }
        .hoian-page-header { padding: 16px 18px; }
    }
    </style>
    """, unsafe_allow_html=True)


def page_header(icon: str, eyebrow: str, title: str, description: str):
    """1 khoi tieu de DUY NHAT cho moi trang - thay the viec xep chong
    st.title() + 1 banner rieng (truoc day lam 2 lop trung nhau) - giong
    1 tam bien hieu son mai pho co: icon ben trai, chu Playfair Display
    serif ben phai, co dong mo ta ngan duoi tieu de."""
    st.markdown(
        f"""
        <div class="hoian-page-header">
            <div class="hoian-page-header-icon">{icon}</div>
            <div>
                <div class="hoian-page-eyebrow">✦ {eyebrow} ✦</div>
                <div class="hoian-page-title">{title}</div>
                <div class="hoian-page-desc">{description}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric(label: str, value, sub: str = "") -> str:
    sub_html = f'<span class="custom-metric-sub"> {sub}</span>' if sub else ""
    return f"""
    <div class="custom-metric-card">
        <div class="custom-metric-label">{label}</div>
        <div class="custom-metric-value">{value}{sub_html}</div>
    </div>
    """


def render_status_metric(label: str, status_code: str) -> str:
    meta = STATUS_META.get(status_code, {"label": status_code, "badge": "ok", "icon": "ℹ️"})
    badge = f'<span class="hoian-badge hoian-badge-{meta["badge"]}">{meta["icon"]} {meta["label"]}</span>'
    return f"""
    <div class="custom-metric-card">
        <div class="custom-metric-label">{label}</div>
        <div style="margin-top:6px;">{badge}</div>
    </div>
    """


# ---------------------------------------------------------------- helpers
def api_get(path: str, params: dict = None):
    try:
        resp = requests.get(f"{API_BASE}{path}", params=params, timeout=5)
        resp.raise_for_status()
        return resp.json(), None
    except Exception as e:
        return None, f"Khong goi duoc API ({path}): {e}. Ban da chay backend chua? (uvicorn backend.main:app --port 8000)"


def api_put(path: str, payload: dict):
    headers = {"X-Admin-Key": ADMIN_API_KEY} if ADMIN_API_KEY else {}
    try:
        resp = requests.put(f"{API_BASE}{path}", json=payload, headers=headers, timeout=5)
        if resp.status_code == 401:
            return None, "Sai hoac thieu ADMIN_API_KEY (phai khop voi bien moi truong ben backend)."
        resp.raise_for_status()
        return resp.json(), None
    except Exception as e:
        return None, f"Khong goi duoc API ({path}): {e}"


def api_is_up() -> bool:
    try:
        requests.get(f"{API_BASE}/health", timeout=2).raise_for_status()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------- login gate
def login_gate() -> bool:
    if st.session_state.get("authenticated"):
        return True

    apply_custom_theme()

    _, mid, _ = st.columns([1, 1.15, 1])
    with mid:
        st.markdown(
            """
            <div style="text-align:center; margin: 40px 0 18px 0;">
                <div style="font-size:42px;">\U0001FAD4</div>
                <div style="font-family:'Playfair Display',Georgia,serif; font-size:1.7rem;
                            font-weight:800; color:var(--hoian-red-dark); margin-top:6px;">SmartCau AI</div>
                <div style="font-size:.78rem; letter-spacing:.18em; text-transform:uppercase;
                            color:var(--hoian-ochre); font-weight:700; margin-top:4px;">
                    ✦ Cong Quan Tri ✦
                </div>
                <div style="font-size:.85rem; color:var(--hoian-muted); margin-top:6px;">
                    Khong gian quan ly di san Chua Cau &middot; Hoi An, Viet Nam
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="hoian-login-card">', unsafe_allow_html=True)
        if USING_DEMO_PASSWORD:
            st.warning(
                "Dang dung MAT KHAU DEMO mac dinh ('admin123'). "
                "Hay set bien moi truong ADMIN_WEB_PASSWORD truoc khi dung that/trinh bay cong khai.",
                icon="⚠️",
            )
        pwd = st.text_input("Mat khau quan tri", type="password", placeholder="Nhap mat khau...")
        if st.button("Dang nhap", use_container_width=True):
            if pwd == ADMIN_WEB_PASSWORD:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Sai mat khau.")
        st.markdown('</div>', unsafe_allow_html=True)
    return False


# ---------------------------------------------------------------- helpers moi (Sprint 3)
def api_post(path: str, payload: dict, admin: bool = False):
    """Goi POST. admin=True -> gui kem X-Admin-Key (vd them nguoi nhan canh bao)."""
    headers = {"X-Admin-Key": ADMIN_API_KEY} if (admin and ADMIN_API_KEY) else {}
    try:
        resp = requests.post(f"{API_BASE}{path}", json=payload, headers=headers, timeout=5)
        if resp.status_code == 401:
            return None, "Sai hoac thieu ADMIN_API_KEY."
        resp.raise_for_status()
        return resp.json(), None
    except Exception as e:
        return None, f"Khong goi duoc API ({path}): {e}"


def api_delete(path: str, admin: bool = True):
    headers = {"X-Admin-Key": ADMIN_API_KEY} if (admin and ADMIN_API_KEY) else {}
    try:
        resp = requests.delete(f"{API_BASE}{path}", headers=headers, timeout=5)
        resp.raise_for_status()
        return resp.json(), None
    except Exception as e:
        return None, f"Khong goi duoc API ({path}): {e}"


def mock_notice(data):
    """Hien 1 dong nhac khi API con tra DU LIEU MAU ("mock": true) - de ca
    nhom biet trang nao dang cho backend that, khong nham khi demo."""
    if isinstance(data, dict) and data.get("mock"):
        st.info("Dang hien thi DU LIEU MAU tu API skeleton - se tu doi sang du lieu that "
                "khi backend cua module nay hoan thanh (xem docs/API_CONTRACT.md).", icon="🧪")


def todo_box(owner: str, items: list):
    """Khung 'viec can lam' tren trang skeleton - xoa khi trang hoan thanh."""
    bullet = "".join(f"<li>{i}</li>" for i in items)
    st.markdown(
        f'<div class="custom-metric-card" style="min-height:auto;border-top-color:var(--hoian-ochre);">'
        f'<div class="custom-metric-label">Viec can lam · phu trach: {owner}</div>'
        f'<ul style="margin:6px 0 0 18px;font-size:.9rem;line-height:1.7;">{bullet}</ul></div>',
        unsafe_allow_html=True,
    )

