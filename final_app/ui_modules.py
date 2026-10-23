import streamlit as st

# ==========================================
# MODERN CLINICAL DASHBOARD THEME
# ==========================================

PRIMARY = "#0d9488"      # Teal
PRIMARY_DARK = "#0f766e"
ACCENT = "#0891b2"       # Cyan
DANGER = "#e11d48"
WARNING = "#d97706"
LIGHT_BG = "#f8fafc"
CARD_BG = "#ffffff"
TEXT = "#0f172a"
MUTED = "#64748b"


def brand_html():
    """Returns the header hero / branding markup used on the main screen."""
    return f"""
    <div class="hero">
        <div class="hero-badge">HYBRID QUANTUM-AI CLINICAL DECISION SUPPORT</div>
        <h1 class="hero-title">Genetic Disease Risk Prediction</h1>
        <p class="hero-sub">Combining statistical Monte Carlo simulation with AI clinical synthesis
        for a single, clear picture of hereditary risk.</p>
        <div class="hero-pills">
            <span class="pill">🧬 Quantum Simulation</span>
            <span class="pill">🤖 AI Synthesis</span>
            <span class="pill">📊 Risk Analytics</span>
        </div>
    </div>
    """


def section_header_card(title: str, subtitle: str = ""):
    """Renders a standalone card used as a section header (safe for wrapping UI below)."""
    st.markdown(
        f"""
        <div class="card">
            <div class="card-head">
                <div class="card-title">{title}</div>
                <div class="card-sub">{subtitle}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_card(title: str, icon: str = "", subtitle: str = ""):
    """Renders an open/close card wrapper with a header. Returns the closing div id."""
    st.markdown(
        f"""
        <div class="card">
            <div class="card-head">
                <div class="card-title">{icon} {title}</div>
                <div class="card-sub">{subtitle}</div>
            </div>
        """,
        unsafe_allow_html=True,
    )
    return "card-close"


def card_close():
    st.markdown("</div>", unsafe_allow_html=True)


def apply_theme(is_dark_mode: bool = False):
    """
    Applies a consistent, modern clinical dashboard theme.
    Theme is designed around light mode by default with a fully
    fleshed-out dark mode for sustained data-entry sessions.
    """
    base_colors = {
        "bg": "#0b1220" if is_dark_mode else LIGHT_BG,
        "card": "#111827" if is_dark_mode else CARD_BG,
        "card_border": "rgba(255,255,255,0.08)" if is_dark_mode else "#e2e8f0",
        "sidebar": "#0f172a" if is_dark_mode else "#ffffff",
        "heading": "#f9fafb" if is_dark_mode else "#0f172a",
        "text": "#e2e8f0" if is_dark_mode else "#334155",
        "muted": "#94a3b8" if is_dark_mode else MUTED,
        "input_bg": "#0b1220" if is_dark_mode else "#ffffff",
        "input_border": "#1e293b" if is_dark_mode else "#e2e8f0",
        "shadow": "rgba(0,0,0,0.45)" if is_dark_mode else "rgba(15,23,42,0.06)",
    }

    custom_css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    /* -- Global base -- */
    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        font-size: 1rem;
    }}
    [data-testid="stAppViewContainer"] {{
        background: {base_colors['bg']};
    }}
    [data-testid="stHeader"] {{
        background: rgba(0,0,0,0) !important;
        height: 0 !important;
    }}
    .block-container {{
        padding-top: 2.2rem !important;
        padding-bottom: 4rem !important;
        max-width: 1150px;
    }}
    .stMarkdown p, .stMarkdown li, .stMarkdown ul, .stMarkdown span {{
        font-size: 1rem !important;
        line-height: 1.6 !important;
    }}

    /* -- Sidebar -- */
    [data-testid="stSidebar"] {{
        background-color: {base_colors['sidebar']};
        border-right: 1px solid {base_colors['card_border']};
    }}
    [data-testid="stSidebar"] * {{
        color: {base_colors['text']} !important;
        font-size: 1rem !important;
    }}
    [data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{
        font-size: 0.95rem !important;
    }}
    [data-testid="stSidebar"] .stSubheader, [data-testid="stSidebar"] h3 {{
        font-size: 1.15rem !important;
    }}
    .sidebar-brand {{
        display: flex; align-items: center; gap: 0.6rem;
        padding: 0.6rem 0.4rem 1rem 0.4rem;
        border-bottom: 1px dashed {base_colors['card_border']};
        margin-bottom: 1.2rem;
    }}
    .sidebar-brand .logo {{
        width: 38px; height: 38px; border-radius: 10px;
        background: linear-gradient(135deg, {PRIMARY}, {ACCENT});
        display: flex; align-items: center; justify-content: center;
        font-size: 20px; color: #fff; flex-shrink: 0;
    }}
    .sidebar-brand .name {{ font-weight: 700; font-size: 1.02rem; color: {base_colors['heading']} !important; }}
    .sidebar-brand .tag {{ font-size: 0.7rem; color: {base_colors['muted']} !important; letter-spacing: 0.04em; }}

    /* -- Typography -- */
    h1 {{
        color: {base_colors['heading']} !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 800 !important;
        letter-spacing: -0.01em;
        font-size: 2.2rem !important;
    }}
    h2 {{
        color: {base_colors['heading']} !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 800 !important;
        letter-spacing: -0.01em;
        font-size: 1.7rem !important;
    }}
    h3 {{
        color: {base_colors['heading']} !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.01em;
        font-size: 1.35rem !important;
    }}
    h4 {{
        color: {base_colors['heading']} !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.01em;
        font-size: 1.15rem !important;
    }}
    .stCaption, [data-testid="stCaptionContainer"] p {{
        font-size: 0.95rem !important;
        color: {base_colors['muted']} !important;
    }}
    p, label, .stMarkdown, [data-testid="stWidgetLabel"] p {{
        color: {base_colors['text']} !important;
        font-size: 1rem !important;
    }}
    [data-testid="stWidgetLabel"] p {{ font-weight: 600 !important; }}

    /* -- Hero -- */
    .hero {{
        background: linear-gradient(135deg, {PRIMARY} 0%, {ACCENT} 100%);
        border-radius: 18px;
        padding: 2.2rem 2.4rem;
        color: #ffffff;
        position: relative;
        overflow: hidden;
        box-shadow: 0 12px 32px rgba(13,148,136,0.25);
        margin-bottom: 1.6rem;
    }}
    .hero::after {{
        content: ""; position: absolute; top: -40%; right: -10%;
        width: 360px; height: 360px; border-radius: 50%;
        background: rgba(255,255,255,0.12);
    }}
    .hero-badge {{
        display: inline-block; background: rgba(255,255,255,0.18);
        padding: 0.3rem 1rem; border-radius: 999px;
        font-size: 0.8rem; font-weight: 700; letter-spacing: 0.08em;
        margin-bottom: 1rem;
    }}
    .hero-title {{
        color: #ffffff !important; font-size: 2.5rem !important;
        margin: 0 0 0.6rem 0 !important; font-weight: 800 !important;
    }}
    .hero-sub {{
        color: rgba(255,255,255,0.92) !important; max-width: 620px;
        font-size: 1.1rem; line-height: 1.55; margin: 0 0 1.2rem 0;
    }}
    .hero-pills {{ display: flex; gap: 0.7rem; flex-wrap: wrap; position: relative; z-index: 2; }}
    .pill {{
        background: rgba(255,255,255,0.16); color: #fff !important;
        padding: 0.5rem 1.1rem; border-radius: 999px; font-size: 0.95rem; font-weight: 600;
    }}

    /* -- Cards -- */
    .card {{
        background: {base_colors['card']};
        border: 1px solid {base_colors['card_border']};
        border-radius: 16px;
        padding: 1.5rem 1.6rem;
        margin-bottom: 1.4rem;
        box-shadow: 0 4px 16px {base_colors['shadow']};
    }}
    .card-head {{ margin-bottom: 1.2rem; }}
    .card-title {{
        color: {base_colors['heading']};
        font-weight: 700; font-size: 1.25rem;
        display: flex; align-items: center; gap: 0.5rem;
    }}
    .card-sub {{
        color: {base_colors['muted']}; font-size: 0.95rem; margin-top: 0.3rem;
    }}

    /* -- Metrics -- */
    [data-testid="stMetric"] {{
        background: {base_colors['card']};
        border: 1px solid {base_colors['card_border']};
        border-radius: 14px;
        padding: 1.2rem 1.4rem;
        box-shadow: 0 4px 14px {base_colors['shadow']};
    }}
    [data-testid="stMetricValue"] {{ color: {base_colors['heading']} !important; font-size: 2rem !important; }}
    [data-testid="stMetricDelta"] {{ font-size: 0.95rem !important; }}
    [data-testid="stMetricLabel"] {{ color: {base_colors['muted']} !important; font-size: 0.95rem !important; }}

    /* -- Inputs (text, number, textarea) -- */
    div[data-baseweb="input"] > div,
    div[data-baseweb="textarea"] > div,
    input, textarea {{
        background-color: {base_colors['input_bg']} !important;
        border: 1px solid {base_colors['input_border']} !important;
        border-radius: 10px !important;
        color: {base_colors['heading']} !important;
        font-size: 1rem !important;
        padding: 0.6rem 0.8rem !important;
    }}
    div[data-baseweb="input"] {{
        min-height: 44px !important;
    }}

    /* -- Selects (gender, blood group, etc.) -- */
    .stSelectbox {{
        color: {base_colors['heading']} !important;
    }}
    div[data-baseweb="select"] > div {{
        background-color: {base_colors['input_bg']} !important;
        border: 1px solid {base_colors['input_border']} !important;
        border-radius: 10px !important;
        min-height: 44px !important;
        color: {base_colors['heading']} !important;
        font-size: 1rem !important;
    }}
    /* Force the selected value (and placeholder) text to be clearly visible */
    div[data-baseweb="select"] > div > div,
    div[data-baseweb="select"] [data-baseweb="base-input"],
    div[data-baseweb="select"] [data-baseweb="base-input"] span,
    div[data-baseweb="select"] div[class*="ValueContainer"],
    div[data-baseweb="select"] div[class*="ValueContainer"] div,
    div[data-baseweb="select"] div[class*="ValueContainer"] span,
    div[data-baseweb="select"] [class*="placeholder"],
    div[data-baseweb="select"] [class*="singleValue"],
    div[data-baseweb="select"] [class*="SelectValue"] {{
        color: {base_colors['heading']} !important;
        font-size: 1rem !important;
        opacity: 1 !important;
    }}
    div[data-baseweb="select"] > div:focus-within {{
        border-color: {PRIMARY} !important;
        box-shadow: 0 0 0 2px rgba(13,148,136,0.18) !important;
    }}

    [data-testid="stNumberInput"] input {{ font-size: 1rem !important; }}
    .stTextInput input::placeholder, .stTextArea textarea::placeholder {{
        font-size: 0.95rem !important;
    }}
    div[data-baseweb="input"]:focus-within > div,
    div[data-baseweb="textarea"]:focus-within > div {{
        border-color: {PRIMARY} !important;
        box-shadow: 0 0 0 2px rgba(13,148,136,0.18) !important;
    }}
    [data-baseweb="popover"] ul, [data-baseweb="menu"] {{
        background-color: {base_colors['input_bg']} !important;
    }}
    [data-baseweb="option"] {{ color: {base_colors['heading']} !important; font-size: 1rem; }}
    [data-baseweb="option"]:hover {{ background-color: rgba(13,148,136,0.12) !important; color: #fff !important; }}

    /* -- Checkboxes -- */
    [data-testid="stCheckbox"] label p {{ font-size: 1rem !important; }}
    [data-testid="stCheckbox"] {{ margin: 0.35rem 0; }}

    /* -- Buttons -- */
    .stButton, .stDownloadButton {{ margin: 0.4rem 0; }}
    .stButton > button, .stDownloadButton > button {{
        background: linear-gradient(135deg, {PRIMARY}, {ACCENT}) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        padding: 0.8rem 1.6rem !important;
        min-height: 52px !important;
        box-shadow: 0 6px 18px rgba(13,148,136,0.28);
        transition: transform 0.12s ease, box-shadow 0.12s ease;
    }}
    .stButton > button:hover, .stDownloadButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 10px 24px rgba(13,148,136,0.36);
    }}
    .stButton > button[kind="secondary"], .stDownloadButton > button[kind="secondary"] {{
        background: transparent !important;
        color: {PRIMARY} !important;
        border: 1px solid {base_colors['input_border']} !important;
        box-shadow: none !important;
    }}
    .stButton > button p, .stDownloadButton > button p {{ font-size: 1.05rem !important; }}

    /* -- Expanders -- */
    [data-testid="stExpander"] {{
        background: {base_colors['card']};
        border: 1px solid {base_colors['card_border']};
        border-radius: 14px !important;
        box-shadow: 0 4px 14px {base_colors['shadow']};
    }}
    [data-testid="stExpander"] summary span {{ color: {base_colors['heading']} !important; font-weight: 600; font-size: 1.05rem !important; }}

    /* -- Tabs -- */
    .stTabs [data-baseweb="tab-list"] {{ gap: 0.5rem; }}
    .stTabs [data-baseweb="tab"] {{
        background: {base_colors['card']};
        border-radius: 10px 10px 0 0;
        padding: 0.7rem 1.4rem;
        color: {base_colors['muted']} !important;
        font-size: 1.05rem !important;
        font-weight: 600;
    }}
    .stTabs [aria-selected="true"] {{ color: {PRIMARY} !important; border-bottom: 3px solid {PRIMARY} !important; }}

    /* -- Alerts / Badges -- */
    .risk-banner {{
        border-radius: 14px; padding: 1.2rem 1.5rem; margin: 0.4rem 0 1.2rem 0;
        display: flex; align-items: center; gap: 1rem;
        font-weight: 700; font-size: 1.15rem;
    }}
    .risk-banner .rb-icon {{ font-size: 2.1rem; }}
    .risk-low {{ background: rgba(22,163,74,0.12); color: #16a34a; border: 1px solid rgba(22,163,74,0.3); }}
    .risk-mid {{ background: rgba(217,119,6,0.12); color: #d97706; border: 1px solid rgba(217,119,6,0.3); }}
    .risk-high {{ background: rgba(225,29,72,0.12); color: #e11d48; border: 1px solid rgba(225,29,72,0.3); }}

    .tag {{
        display: inline-block; padding: 0.3rem 0.8rem; border-radius: 8px;
        font-size: 0.85rem; font-weight: 700;
    }}
    .tag-teal {{ background: rgba(13,148,136,0.12); color: {PRIMARY}; }}
    .tag-gray {{ background: rgba(100,116,139,0.12); color: {base_colors['muted']}; }}

    .footer-note {{
        text-align: center; color: {base_colors['muted']} !important;
        font-size: 0.9rem; margin-top: 2.5rem; padding-top: 1rem;
        border-top: 1px solid {base_colors['card_border']};
    }}

    /* -- Utility -- */
    .stSpinner > div {{ border-top-color: {PRIMARY} !important; }}
    hr {{ border-color: {base_colors['card_border']} !important; }}
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)


def sidebar_brand():
    """Renders the branded sidebar header block."""
    st.markdown(
        f"""
        <div class="sidebar-brand">
            <div class="logo">🧬</div>
            <div>
                <div class="name">RiskPredict</div>
                <div class="tag">Quantum · AI · Clinical</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def risk_banner(mean_value: float):
    """Renders a color-coded patient condition banner based on the simulated mean."""
    if mean_value < 20.0:
        cls, icon, label, note = "risk-low", "🟢", "PATIENT CONDITION: GOOD", "Low overall disease risk profile"
    elif mean_value < 50.0:
        cls, icon, label, note = "risk-mid", "🟠", "PATIENT CONDITION: CONCERNING", "Moderate risk profile identified"
    else:
        cls, icon, label, note = "risk-high", "🔴", "PATIENT CONDITION: HIGH RISK", "Action & follow-up highly recommended"

    st.markdown(
        f"""
        <div class="risk-banner {cls}">
            <span class="rb-icon">{icon}</span>
            <span>{label} — <span style="font-weight:600;opacity:.85">{note}</span></span>
        </div>
        """,
        unsafe_allow_html=True,
    )