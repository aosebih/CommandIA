"""
CommandIA • The "Belief Machine" Simulator
=========================================
Single-file Streamlit web application (streamlit_sandbox/app.py) for hackathon demo video.
Acts as a dual-pane simulator proving CommandIA's ability to extract structured e-commerce
order details from messy Franco-Arabic / Algerian Darija Instagram DMs in real-time.

Architecture:
- Left Column: The Instagram Mock (The Customer View)
  Header: "📱 Instagram Direct - @brownies_mahelma"
  Interactive chat via st.chat_message and st.chat_input, preserved in st.session_state.
- Right Column: The CommandIA Dashboard (The Merchant View)
  Header: "⚡ CommandIA Extraction Engine"
  Dynamic live extraction: st.metric, st.dataframe, 5 Sacred Fields verification HUD,
  and Supabase cloud sync status.
"""

import base64
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import requests
import streamlit as st
from dotenv import load_dotenv

# Ensure the project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Load .env variables
load_dotenv(dotenv_path=ROOT_DIR / ".env")

# Try to import canonical Algerian wilayas mapping from backend
try:
    from ai.wilayas import get_wilaya_name
except ImportError:
    def get_wilaya_name(code):
        return f"Wilaya {code}" if code else None

# Helper: Load CommandIA Logo as Data URI
def get_logo_data_uri() -> str:
    logo_path = ROOT_DIR / "frontend" / "src" / "assets" / "logo.png"
    if logo_path.exists():
        try:
            with open(logo_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
                return f"data:image/png;base64,{encoded}"
        except Exception:
            return ""
    return ""

# Helper: Detect Algerian Telecom Operator
def detect_dz_operator(phone: Optional[str]) -> str:
    if not phone:
        return ""
    clean = str(phone).replace(" ", "").replace("-", "")
    if clean.startswith("+213"):
        clean = "0" + clean[4:]
    elif clean.startswith("00213"):
        clean = "0" + clean[5:]
    if clean.startswith("05"):
        return "Ooredoo"
    elif clean.startswith("06"):
        return "Mobilis"
    elif clean.startswith("07"):
        return "Djezzy"
    return "Algérie"

# Helper: Format Currency (DA)
def format_da(amount: Optional[float]) -> str:
    if amount is None or amount == 0:
        return "0 DA"
    return f"{amount:,.0f}".replace(",", " ") + " DA"

# Page Configuration
st.set_page_config(
    page_title="CommandIA • Hackathon Demo Simulator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

LOGO_URI = get_logo_data_uri()

# Injected CSS for Brand Identity & Seamless Layout
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

    /* Brand Tokens (CommandIA) */
    :root {
        --n: #0E0724;
        --v: #2A0E5C;
        --m: #DB1A86;
        --r: #FF5FAE;
        --l: #CDBDF5;
        --p: #F7F3FF;
        --ok: #19C37D;
        --wa: #F5A623;
        --in: #4DA3FF;
        --bd: #E4DCF5;
    }

    html, body, [class*="css"] {
        font-family: 'Poppins', 'Inter', -apple-system, sans-serif !important;
    }

    /* Hide Streamlit default chrome so video recording is clean */
    .stDeployButton, [data-testid="stDecoration"], [data-testid="stToolbar"] {
        display: none !important;
    }
    #MainMenu, footer {
        visibility: hidden !important;
    }
    header[data-testid="stHeader"] {
        background: transparent !important;
        pointer-events: none;
        z-index: 5;
    }
    header[data-testid="stHeader"] > * {
        pointer-events: auto;
    }

    /* Container padding: 5rem top clearance so Streamlit header never masks content */
    .block-container {
        padding-top: 4.8rem !important;
        padding-bottom: 2rem !important;
        max-width: 98% !important;
        background: #F7F3FF;
    }

    /* Top Brand Navigation Banner */
    .top-brand-nav {
        background: #0E0724;
        color: white;
        padding: 14px 24px;
        border-radius: 16px;
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 22px;
        box-shadow: 0 8px 30px rgba(14, 7, 36, 0.25);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .brand-left {
        display: flex;
        align-items: center;
        gap: 16px;
    }
    .brand-logo-img {
        height: 38px;
        display: block;
    }
    .workspace-tag {
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 99px;
        padding: 4px 14px;
        font-size: 13px;
        color: #CDBDF5;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .badge-live-ai {
        background: rgba(25, 195, 125, 0.16);
        color: #19C37D;
        border: 1px solid rgba(25, 195, 125, 0.4);
        padding: 4px 14px;
        border-radius: 99px;
        font-size: 12px;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .pulse-dot {
        width: 8px;
        height: 8px;
        background: #19C37D;
        border-radius: 50%;
        animation: pulse-ring 2s infinite;
    }
    @keyframes pulse-ring {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(25, 195, 125, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(25, 195, 125, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(25, 195, 125, 0); }
    }

    /* Column Headers */
    .col-header-ig {
        background: #ffffff;
        border: 1.5px solid #E4DCF5;
        border-bottom: 2px solid #F1EBFF;
        border-radius: 20px 20px 0 0;
        padding: 14px 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .col-header-saas {
        background: linear-gradient(135deg, #2A0E5C, #0E0724);
        color: #ffffff;
        border-radius: 20px 20px 0 0;
        padding: 16px 22px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    /* Left Frame (Instagram DM Card) */
    .ig-container-card {
        background: #ffffff;
        border: 1.5px solid #E4DCF5;
        border-top: none;
        border-radius: 0 0 20px 20px;
        padding: 16px;
        box-shadow: 0 8px 24px rgba(42, 14, 92, 0.05);
        margin-bottom: 16px;
    }

    /* Right Frame (CommandIA SaaS Dashboard) */
    .saas-container-card {
        background: #ffffff;
        border: 1.5px solid #E4DCF5;
        border-top: none;
        border-radius: 0 0 20px 20px;
        padding: 22px;
        box-shadow: 0 8px 24px rgba(42, 14, 92, 0.05);
        margin-bottom: 16px;
    }

    /* Customer details box */
    .customer-summary-box {
        background: #FAF7FF;
        border: 1px solid #E4DCF5;
        border-radius: 14px;
        padding: 16px;
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px 18px;
        margin-bottom: 20px;
    }
    .cs-item {
        display: flex;
        flex-direction: column;
    }
    .cs-label {
        font-size: 11px;
        font-weight: 600;
        color: #6E6590;
        text-transform: uppercase;
        letter-spacing: 0.4px;
    }
    .cs-value {
        font-size: 14.5px;
        font-weight: 700;
        color: #0E0724;
        margin-top: 2px;
    }
    .carrier-tag {
        display: inline-block;
        background: #E6F1FF;
        color: #1D63B8;
        font-size: 10px;
        font-weight: 700;
        padding: 2px 7px;
        border-radius: 4px;
        margin-left: 6px;
    }

    /* 5 Sacred Fields Visual Cards */
    .sacred-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 8px;
        margin-top: 8px;
    }
    .sacred-card {
        padding: 9px 12px;
        border-radius: 10px;
        border: 1px solid #E4DCF5;
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: #ffffff;
    }
    .sacred-card.valid {
        border-color: #BFEBD6;
        background: #F0FDF4;
    }
    .sacred-card.pending {
        border-color: #F5D79A;
        background: #FFF8EA;
    }
    .sc-label {
        font-size: 11px;
        color: #6E6590;
        font-weight: 500;
    }
    .sc-value {
        font-size: 12.5px;
        font-weight: 700;
        color: #0E0724;
    }

    /* Total COD Card */
    .total-cod-card {
        background: linear-gradient(135deg, #2A0E5C, #0E0724);
        color: #ffffff;
        border-radius: 14px;
        padding: 16px 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-top: 18px;
        box-shadow: 0 6px 20px rgba(42, 14, 92, 0.2);
    }
    .t-label {
        font-size: 11px;
        font-weight: 600;
        letter-spacing: .15em;
        text-transform: uppercase;
        color: #CDBDF5;
    }
    .t-val {
        font-size: 26px;
        font-weight: 800;
        color: #FF5FAE;
        letter-spacing: -0.5px;
    }

    /* Supabase Sync Banner */
    .supabase-pill {
        background: #FAF7FF;
        border: 1px solid #E4DCF5;
        border-radius: 10px;
        padding: 10px 14px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 12px;
        margin-top: 14px;
    }

    .eb {
        font: 600 11px 'Poppins', Arial;
        letter-spacing: .22em;
        text-transform: uppercase;
        color: #6E6590;
    }
    .mg {
        color: #DB1A86 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = f"ig_client_{uuid.uuid4().hex[:6]}"

if "last_response" not in st.session_state:
    st.session_state.last_response = None

if "api_error" not in st.session_state:
    st.session_state.api_error = None


# --- Sidebar: Configuration & Scenario Controls ---
with st.sidebar:
    st.markdown('<div class="eb mg">SIMULATOR SETTINGS</div>', unsafe_allow_html=True)
    st.title("⚙️ Backend Setup")

    default_backend = os.getenv("COMMANDIA_BACKEND_URL", "http://127.0.0.1:8000")
    backend_url = st.text_input("FastAPI Base URL", value=default_backend).rstrip("/")
    env_api_key = os.getenv("COMMANDIA_API_KEY", "commandia_sandbox_secret")
    api_key = st.text_input("API Key (X-API-Key)", value=env_api_key, type="password")

    if st.button("🔌 Ping FastAPI Backend", use_container_width=True):
        with st.spinner("Checking server..."):
            try:
                r = requests.get(f"{backend_url}/healthz", timeout=4.0)
                if r.status_code == 200:
                    st.success("✅ FastAPI Online & Supabase Connected!")
                    st.json(r.json())
                else:
                    st.warning(f"Server returned status {r.status_code}")
            except Exception as e:
                st.error(f"Cannot reach server: {e}")

    st.divider()

    st.markdown('<div class="eb">ACTIVE STORE PRESET</div>', unsafe_allow_html=True)
    active_product_context = {
        "merchant_id": os.getenv("DEFAULT_MERCHANT_ID", "brownies_mahelma_01"),
        "store_name": "Brownies Mahelma",
        "item_id": "brownies_box_classic",
        "product_name": "Boîte de Brownies Classique",
        "price": 250,
        "total_price_da": 250,
        "shipping_rates": {
            "16": {"home_fee_da": 250, "desk_fee_da": 150},
            "31": {"home_fee_da": 500, "desk_fee_da": 300},
            "19": {"home_fee_da": 450, "desk_fee_da": 250},
            "25": {"home_fee_da": 500, "desk_fee_da": 300},
        },
    }
    st.caption("Store: **Brownies Mahelma (Algiers)** • Product: **Boîte de Brownies (250 DA)**")

    st.divider()
    st.caption(f"Session Thread ID: `{st.session_state.conversation_id}`")
    if st.button("🔄 Reset Chat & Clear Order", use_container_width=True, type="primary"):
        st.session_state.messages = []
        st.session_state.conversation_id = f"ig_client_{uuid.uuid4().hex[:6]}"
        st.session_state.last_response = None
        st.session_state.api_error = None
        st.rerun()


# --- TOP BRAND APPLICATION BANNER ---
logo_markup = f'<img src="{LOGO_URI}" class="brand-logo-img" alt="CommandIA">' if LOGO_URI else '<span style="font-size:22px; font-weight:800; color:#FF5FAE;">COMMANDIA</span>'

st.markdown(
    f"""
    <div class="top-brand-nav">
        <div class="brand-left">
            {logo_markup}
            <div class="workspace-tag">
                <span>🏬 Store:</span>
                <b style="color:#ffffff;">Brownies Mahelma</b>
            </div>
        </div>
        <div style="display:flex; align-items:center; gap:16px;">
            <div class="badge-live-ai">
                <span class="pulse-dot"></span>
                AI Extraction Engine: Active
            </div>
            <div style="font-size:12px; color:#CDBDF5;">
                🗄️ PostgreSQL Supabase Sync • 🇩🇿 Darija Mirroring
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# --- DUAL-PANE SPLIT-SCREEN LAYOUT ---
col_left, col_right = st.columns([1, 1], gap="large")


# ==============================================================================
# LEFT COLUMN: The Instagram Mock (The Customer View)
# ==============================================================================
with col_left:
    # Required Instagram Header
    st.markdown(
        """
        <div class="col-header-ig">
            <div style="display:flex; align-items:center; gap:12px;">
                <div style="width:40px; height:40px; border-radius:50%; background:linear-gradient(135deg, #7A35E8, #DB1A86, #F5A623); padding:2px; display:flex; align-items:center; justify-content:center;">
                    <div style="width:100%; height:100%; border-radius:50%; background:#ffffff; display:flex; align-items:center; justify-content:center; font-size:18px;">🧁</div>
                </div>
                <div>
                    <div style="font-weight:700; font-size:15px; color:#0E0724;">📱 Instagram Direct - @brownies_mahelma</div>
                    <div style="font-size:11.5px; color:#19C37D; font-weight:600;">Active now • Customer DM Channel</div>
                </div>
            </div>
            <div style="display:flex; gap:12px; color:#6E6590; font-size:17px;">
                <span>📞</span>
                <span>📹</span>
                <span>ℹ️</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ig-container-card">', unsafe_allow_html=True)

    # Chat Messages History (using st.chat_message)
    if not st.session_state.messages:
        st.info("👋 **Start simulating customer messages in Franco-Arabic or Darija!**")

    for msg in st.session_state.messages:
        role = msg["role"]
        avatar = "👤" if role == "user" else "🧁"
        with st.chat_message(role, avatar=avatar):
            st.markdown(msg["content"])

    st.markdown('</div>', unsafe_allow_html=True)

    # 1-Click Scenario Buttons for Flawless Hackathon Video Recording
    st.markdown('<div class="eb mg" style="margin-top:10px; margin-bottom:6px;">⚡ AUTHENTIC ALGERIAN SCENARIOS (CLICK TO TEST)</div>', unsafe_allow_html=True)
    b_col1, b_col2 = st.columns(2)
    prompt_to_send = None

    with b_col1:
        if st.button("🎓 1. Lyna_dz (Sidi Abdellah)\n'Cc stp ch7al dir la boite...'", use_container_width=True):
            prompt_to_send = "Cc stp ch7al dir la boite ta3 les brownies? w esq kayen livraison l sidi abdellah?"
        if st.button("📍 1b. Lyna_dz (Address & Num)\n'B1 dirili 2 boîtes ENSIA...'", use_container_width=True):
            prompt_to_send = "B1, c bon dirili 2 boîtes w l'adresse f la résidence ta3 ENSIA. num: 0555123456 mrc"
        if st.button("⚡ 3. Zaki_officiel (Zeralda)\n'Slt, 3 boites l zeralda...'", use_container_width=True):
            prompt_to_send = "Slt, 3 boites brownies l zeralda centre, num 0661223344"

    with b_col2:
        if st.button("🇩🇿 2. Amine.99 (USTHB)\n'سلام، حبيت نكوموندي لي براونيز...'", use_container_width=True):
            prompt_to_send = "سلام، حبيت نكوموندي لي براونيز تع 250 دج. ديرو التوصيل لباب الزوار؟"
        if st.button("📍 2b. Amine.99 (Num & Time)\n'نسحق 4 ميرو 0770987654...'", use_container_width=True):
            prompt_to_send = "نسحق 4، وهذا ميرو تاعي 0770987654. ابعثهم ل l'USTHB غدوة الصباح stp"
        if st.button("🎉 4. Meriem_sweets (Bulk 10)\n'Bnsr, svp dirou commandes kbar?'", use_container_width=True):
            prompt_to_send = "Bnsr, svp dirou des commandes kbar? 3andi anniversaire w s7a9it 10 boîtes"

    # Chat Input (Franco-Arabic placeholder)
    user_input = st.chat_input("e.g., Salam, nhab ncomandi 2 boites de brownies l Alger centre...")
    if user_input:
        prompt_to_send = user_input

    # Execution & API Call Logic
    if prompt_to_send:
        # 1. Display instantly as user chat bubble
        st.session_state.messages.append({"role": "user", "content": prompt_to_send})

        # 2. Prepare payload and call local FastAPI backend
        endpoint = f"{backend_url}/chat"
        payload = {
            "message": prompt_to_send,
            "conversation_id": st.session_state.conversation_id,
            "product_context": active_product_context,
        }
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["X-API-Key"] = api_key

        with st.spinner("⚡ CommandIA AI extracting order details..."):
            try:
                response = requests.post(endpoint, json=payload, headers=headers, timeout=35.0)
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.last_response = data
                    st.session_state.api_error = None

                    if data.get("conversation_id"):
                        st.session_state.conversation_id = data["conversation_id"]

                    reply = (
                        data.get("reply_to_customer")
                        or data.get("response_text")
                        or "D'accord, bien reçu !"
                    )
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                elif response.status_code == 401:
                    st.session_state.api_error = "401 Unauthorized: Invalid COMMANDIA_API_KEY."
                elif response.status_code == 503:
                    st.session_state.api_error = "503 Unavailable: Check GEMINI_API_KEY in .env."
                else:
                    st.session_state.api_error = f"Error {response.status_code}: {response.text}"
            except requests.exceptions.ConnectionError:
                st.session_state.api_error = "Cannot connect to FastAPI backend on port 8000. Start it with: `uvicorn backend.app:app --port 8000`"
            except requests.exceptions.Timeout:
                st.session_state.api_error = "Request timed out (>35s). AI model is responding slowly."
            except Exception as e:
                st.session_state.api_error = f"Unexpected Error: {e}"

        # Instantly update both columns
        st.rerun()


# ==============================================================================
# RIGHT COLUMN: The CommandIA Dashboard (The Merchant View)
# ==============================================================================
with col_right:
    data = st.session_state.last_response or {}

    extracted = data.get("extracted_data") or {}
    collected = data.get("collected_fields") or {}
    merged = dict(extracted)
    merged.update({k: v for k, v in collected.items() if v is not None})

    state = data.get("state", "WAITING")
    language = data.get("language", "Not detected")
    order_status = merged.get("order_status") or "IN_PROGRESS"
    saved_order_id = data.get("saved_order_id")

    # Status badge styling
    if order_status == "CONFIRMED":
        status_html = '<span style="background:#E3F7EE; color:#0B7A4F; border:1px solid #BFEBD6; padding:4px 12px; border-radius:99px; font-weight:700; font-size:12px;">🟢 CONFIRMED</span>'
    elif order_status == "REQUIRES_HUMAN":
        status_html = '<span style="background:#FDE8EB; color:#B3182E; border:1px solid #F7C2CA; padding:4px 12px; border-radius:99px; font-weight:700; font-size:12px;">🔴 ESCALATED</span>'
    else:
        status_html = '<span style="background:#FFF3DC; color:#8A5A00; border:1px solid #F5D79A; padding:4px 12px; border-radius:99px; font-weight:700; font-size:12px;">🟡 IN PROGRESS</span>'

    order_ref = f"#CMD-{st.session_state.conversation_id[-4:].upper()}"

    # Required SaaS Header
    st.markdown(
        f"""
        <div class="col-header-saas">
            <div>
                <div class="eb" style="color:#FF5FAE;">MERCHANT REAL-TIME VIEW</div>
                <div style="font-weight:700; font-size:18px;">⚡ CommandIA Extraction Engine</div>
            </div>
            <div>{status_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="saas-container-card">', unsafe_allow_html=True)

    if st.session_state.api_error:
        st.error(f"⚠️ {st.session_state.api_error}")

    # Top Metrics Row (st.metric)
    subtotal = extracted.get("subtotal_da") or 0
    shipping = extracted.get("shipping_fee_da") or 0
    total = extracted.get("total_price_da") or (subtotal + shipping if subtotal else 0)

    # Count 5 sacred fields
    c_name = merged.get("customer_name")
    c_phone = merged.get("phone_number")
    c_carrier = detect_dz_operator(c_phone) if c_phone else ""
    c_wilaya = merged.get("wilaya_code")
    c_wname = get_wilaya_name(c_wilaya) if c_wilaya else None
    c_del = merged.get("delivery_type")
    c_addr = merged.get("address")

    sacred_list = [
        ("customer_name", "Customer Name", "👤", c_name),
        ("phone_number", "Phone (10 digits)", "📱", c_phone),
        ("wilaya_code", "Wilaya (1-69)", "📍", f"{c_wilaya} - {c_wname}" if (c_wilaya and c_wname) else (f"Wilaya {c_wilaya}" if c_wilaya else None)),
        ("delivery_type", "Delivery Type", "🚚", "Home Delivery" if c_del == "HOME" else ("Desk Pickup" if c_del == "DESK" else None)),
        ("address", "Commune / Address", "🏠", c_addr),
    ]
    ready_count = sum(1 for _, _, _, val in sacred_list if val is not None)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Order Ref", order_ref)
    m2.metric("Fields Validated", f"{ready_count}/5")
    m3.metric("Shipping Fee", format_da(shipping))
    m4.metric("Total COD", format_da(total))

    # Structured Customer & Order View
    w_str = f"{c_wilaya} - {c_wname}" if (c_wilaya and c_wname) else (f"Wilaya {c_wilaya}" if c_wilaya else "Awaiting Wilaya...")
    del_str = "Home Delivery (À Domicile)" if c_del == "HOME" else ("Desk Pickup (Au Bureau)" if c_del == "DESK" else "Awaiting delivery mode...")

    st.markdown(
        f"""
        <div class="customer-summary-box">
            <div class="cs-item">
                <span class="cs-label">👤 Customer Name</span>
                <span class="cs-value">{c_name or "Awaiting name..."}</span>
            </div>
            <div class="cs-item">
                <span class="cs-label">📱 Phone Contact</span>
                <span class="cs-value">{c_phone or "Awaiting phone..."} {f'<span class="carrier-tag">{c_carrier}</span>' if c_carrier else ''}</span>
            </div>
            <div class="cs-item">
                <span class="cs-label">📍 Wilaya Destination</span>
                <span class="cs-value">🇩🇿 {w_str}</span>
            </div>
            <div class="cs-item">
                <span class="cs-label">🚚 Delivery Mode</span>
                <span class="cs-value">{del_str}</span>
            </div>
            <div class="cs-item" style="grid-column: span 2;">
                <span class="cs-label">🏠 Street Address / Commune</span>
                <span class="cs-value">{c_addr or "Awaiting address..."}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # The 5 Sacred Fields Visual Checklist
    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <span class="eb">THE 5 SACRED FIELDS VERIFICATION</span>
            <span style="font-size:11.5px; font-weight:700; color:{'#19C37D' if ready_count==5 else '#F5A623'};">
                {ready_count}/5 ({int(ready_count / 5.0 * 100)}%)
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(ready_count / 5.0)

    # Sacred Cards
    sf_cols = st.columns(2)
    for idx, (f_key, f_title, f_ico, f_val) in enumerate(sacred_list):
        t_col = sf_cols[idx % 2]
        is_ok = f_val is not None
        cls_name = "valid" if is_ok else "pending"
        badge_sym = "✅" if is_ok else "⏳"
        txt_val = f_val if is_ok else "Pending"

        with t_col:
            st.markdown(
                f"""
                <div class="sacred-card {cls_name}">
                    <div>
                        <div class="sc-label">{f_ico} {f_title}</div>
                        <div class="sc-value">{txt_val}</div>
                    </div>
                    <span>{badge_sym}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Clean Order Items Table (st.dataframe)
    st.markdown('<div class="eb" style="margin-top:18px; margin-bottom:6px;">EXTRACTED ORDER ITEMS</div>', unsafe_allow_html=True)
    order_items = extracted.get("order_items") or []

    if order_items:
        items_rows = []
        for itm in order_items:
            items_rows.append({
                "Product": itm.get("product_name", "Item"),
                "Qty": itm.get("quantity", 1),
                "Variant": itm.get("size_color") or "-",
                "Unit Price": format_da(itm.get("unit_price_da")),
            })
        st.dataframe(items_rows, use_container_width=True, hide_index=True)
    else:
        st.caption("No product items extracted yet.")

    # Total COD Banner
    st.markdown(
        f"""
        <div class="total-cod-card">
            <div>
                <div class="t-label">TOTAL TO COLLECT (CASH ON DELIVERY)</div>
                <div style="font-size:12px; color:#CDBDF5; margin-top:2px;">
                    Subtotal: {format_da(subtotal)} • Shipping: {format_da(shipping)}
                </div>
            </div>
            <div class="t-val">{format_da(total)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Supabase PostgreSQL Status Card
    st.markdown(
        f"""
        <div class="supabase-pill">
            <div>
                <span style="font-weight:700; color:#0E0724;">🧠 Language:</span>
                <span style="color:#7A35E8; font-weight:600; margin-left:4px;">{str(language).replace('_', ' ').title()}</span>
            </div>
            <div>
                <span style="font-weight:700; color:#0E0724;">AI State:</span>
                <span style="background:#F1EBFF; color:#0E0724; padding:2px 8px; border-radius:6px; font-weight:600; font-size:11px; margin-left:4px;">{state}</span>
            </div>
            <div>
                <span style="font-weight:700; color:#0E0724;">🗄️ Supabase:</span>
                <span style="color:#19C37D; font-weight:700; margin-left:4px;">Connected</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if saved_order_id:
        st.success(f"💾 **Logged to Supabase Orders Table**: Order ID `{saved_order_id}`")

    # Collapsible Raw JSON Card
    with st.expander("🔍 Raw JSON Inspection", expanded=False):
        st.json(data or {"status": "Waiting for conversation messages..."})

    st.markdown('</div>', unsafe_allow_html=True)
