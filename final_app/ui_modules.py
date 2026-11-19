"""
UI layer: a clean SaaS-dashboard look (light gray canvas, white cards with
hairline borders, one purple accent, soft badges) plus the dashboard widgets
used to present a risk assessment.
"""

import html

import plotly.graph_objects as go
import streamlit as st

import quantum_engine

# ==========================================
# DESIGN TOKENS
# ==========================================
PRIMARY = "#7F56D9"
PRIMARY_DARK = "#6941C6"

LIGHT = {
    "bg": "#F9FAFB",
    "surface": "#FFFFFF",
    "border": "#EAECF0",
    "input_border": "#D0D5DD",
    "heading": "#101828",
    "text": "#344054",
    "muted": "#667085",
    "subtle": "#F2F4F7",
    "primary_soft": "#F9F5FF",
    "primary_soft_border": "#E9D7FE",
    "primary_text": "#6941C6",
    "shadow": "0 1px 2px rgba(16,24,40,0.05)",
    "shadow_md": "0 1px 3px rgba(16,24,40,0.10), 0 1px 2px rgba(16,24,40,0.06)",
    "good": ("#ECFDF3", "#067647", "#ABEFC6"),
    "warn": ("#FFFAEB", "#B54708", "#FEDF89"),
    "bad": ("#FEF3F2", "#B42318", "#FECDCA"),
    "neutral": ("#F9FAFB", "#344054", "#EAECF0"),
    # Sequential purple (low -> high magnitude) for chart fills
    "seq": ["#D6BBFB", "#9E77ED", "#6941C6"],
    "line": "#7F56D9",
    "area": "rgba(127,86,217,0.14)",
    "band": "rgba(127,86,217,0.07)",
    "grid": "#F2F4F7",
    "hero_top": "#F9F5FF",
    "hero_glow": "rgba(158,119,237,0.22)",
}

DARK = {
    "bg": "#0C111D",
    "surface": "#161B26",
    "border": "#1F242F",
    "input_border": "#333741",
    "heading": "#F5F5F6",
    "text": "#CECFD2",
    "muted": "#94969C",
    "subtle": "#1F242F",
    "primary_soft": "#2C1C5F",
    "primary_soft_border": "#53389E",
    "primary_text": "#D6BBFB",
    "shadow": "0 1px 2px rgba(0,0,0,0.30)",
    "shadow_md": "0 1px 3px rgba(0,0,0,0.40)",
    "good": ("#053321", "#75E0A7", "#085D3A"),
    "warn": ("#4E1D09", "#FEC84B", "#93370D"),
    "bad": ("#55160C", "#FDA29B", "#912018"),
    "neutral": ("#1F242F", "#CECFD2", "#333741"),
    "seq": ["#53389E", "#9E77ED", "#D6BBFB"],
    "line": "#B692F6",
    "area": "rgba(182,146,246,0.16)",
    "band": "rgba(182,146,246,0.08)",
    "grid": "#1F242F",
    "hero_top": "#1C1530",
    "hero_glow": "rgba(127,86,217,0.35)",
}


def tokens() -> dict:
    return DARK if st.session_state.get("_dark_mode") else LIGHT


def _esc(value) -> str:
    return html.escape(str(value)) if value not in (None, "") else ""


# ==========================================
# THEME
# ==========================================
def apply_theme(is_dark_mode: bool = False):
    st.session_state["_dark_mode"] = is_dark_mode
    t = tokens()
    good, warn, bad, neutral = t["good"], t["warn"], t["bad"], t["neutral"]

    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html {{ font-size: 20px; }}
    html, body, [class*="css"], .stApp, button, input, textarea, select {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }}
    [data-testid="stAppViewContainer"], .stApp {{ background: {t['bg']}; }}
    [data-testid="stHeader"] {{ background: transparent !important; }}
    [data-testid="stToolbar"], [data-testid="stDecoration"] {{ display: none !important; }}
    .block-container {{
        padding-top: 2.4rem !important;
        padding-bottom: 4rem !important;
        max-width: 1240px;
    }}
    p, li, label, .stMarkdown {{ color: {t['text']}; }}
    h1, h2, h3, h4 {{ color: {t['heading']} !important; letter-spacing: -0.02em; }}

    /* ---------- Sidebar ---------- */
    [data-testid="stSidebar"] {{
        background: {t['surface']};
        border-right: 1px solid {t['border']};
    }}
    [data-testid="stSidebar"] .block-container, [data-testid="stSidebarContent"] {{ padding-top: 0.6rem; }}
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] label {{ color: {t['text']} !important; }}
    .sb-brand {{ display: flex; align-items: center; gap: 0.65rem; padding: 0.2rem 0 1.1rem 0; }}
    .sb-logo {{
        width: 34px; height: 34px; border-radius: 50%;
        background: radial-gradient(circle at 30% 30%, #B692F6, {PRIMARY_DARK} 70%);
        box-shadow: inset 0 -4px 8px rgba(0,0,0,0.18);
        display: flex; align-items: center; justify-content: center; color: #fff; font-size: 16px;
    }}
    .sb-name {{ font-weight: 600; font-size: 1.05rem; color: {t['heading']}; }}
    .sb-label {{
        font-size: 0.75rem; font-weight: 600; color: {t['muted']};
        text-transform: uppercase; letter-spacing: 0.04em; margin: 1rem 0 0.35rem 0.25rem;
    }}
    [data-testid="stSidebar"] .stButton {{ margin: 0 0 0.5rem 0 !important; }}
    [data-testid="stSidebar"] .stButton > button {{
        min-height: 42px !important; border-radius: 8px !important;
        background: {t['surface']} !important; color: {t['text']} !important;
        border: 1px solid {t['input_border']} !important; box-shadow: {t['shadow']} !important;
        font-weight: 600 !important;
    }}
    [data-testid="stSidebar"] .stButton > button:hover {{ background: {t['subtle']} !important; }}
    .st-key-btn-clear-all button {{
        color: {bad[1]} !important; border-color: {bad[2]} !important; background: {t['surface']} !important;
    }}
    .st-key-btn-clear-all button:hover {{ background: {bad[0]} !important; }}
    .st-key-btn-clear-all button p, .st-key-btn-clear-all button span {{ color: {bad[1]} !important; }}
    .sb-promo {{
        background: {t['primary_soft']}; border-radius: 10px; padding: 1rem;
        margin-top: 1.4rem; font-size: 0.875rem; color: {t['text']};
    }}
    .sb-promo b {{ color: {t['primary_text']}; display: block; margin-bottom: 0.3rem; font-weight: 600; }}
    .sb-promo ol {{ margin: 0.4rem 0 0 1.1rem; padding: 0; }}
    .sb-promo li {{ font-size: 0.85rem; margin: 0.15rem 0; color: {t['text']}; }}
    .sb-foot {{
        border-top: 1px solid {t['border']}; margin-top: 1.4rem; padding-top: 1rem;
        font-size: 0.8rem; color: {t['muted']};
    }}

    /* ---------- Landing hero ---------- */
    .hero {{
        position: relative; overflow: hidden;
        display: flex; align-items: center; justify-content: space-between; gap: 2rem;
        border: 1px solid {t['border']}; border-radius: 16px; box-shadow: {t['shadow_md']};
        padding: 2.2rem 2.4rem; margin-bottom: 1.25rem;
        background:
            radial-gradient(600px 260px at 100% 0%, {t['hero_glow']}, transparent 70%),
            linear-gradient(180deg, {t['hero_top']}, {t['surface']});
    }}
    .hero-copy {{ max-width: 600px; position: relative; z-index: 1; }}
    .hero-pill {{
        display: inline-flex; align-items: center; gap: 0.5rem;
        background: {t['primary_soft']}; border: 1px solid {t['primary_soft_border']};
        border-radius: 999px; padding: 0.2rem 0.75rem 0.2rem 0.25rem;
        font-size: 0.8rem; font-weight: 500; color: {t['primary_text']};
    }}
    .hero-pill b {{
        background: {t['surface']}; border: 1px solid {t['primary_soft_border']}; border-radius: 999px;
        padding: 0.05rem 0.55rem; font-weight: 600;
    }}
    .hero-title {{
        font-size: 2.6rem; line-height: 1.15; font-weight: 700; letter-spacing: -0.03em;
        color: {t['heading']}; margin: 1rem 0 0.75rem 0;
    }}
    .hero-title span {{
        background: linear-gradient(90deg, {PRIMARY}, #B692F6);
        -webkit-background-clip: text; background-clip: text; color: transparent;
    }}
    .hero-sub {{ font-size: 1.05rem !important; line-height: 1.6; color: {t['muted']} !important; margin: 0 0 1.25rem 0; }}
    .hero-checks {{ display: flex; flex-wrap: wrap; gap: 0.5rem 1.25rem; }}
    .hero-checks div {{ display: flex; align-items: center; gap: 0.45rem; font-size: 0.9rem; color: {t['text']}; font-weight: 500; }}
    .hero-checks i {{
        font-style: normal; width: 20px; height: 20px; border-radius: 50%; display: inline-flex;
        align-items: center; justify-content: center; font-size: 0.7rem;
        background: {t['primary_soft']}; color: {t['primary_text']};
    }}
    .hero-art {{ flex-shrink: 0; }}
    @media (max-width: 900px) {{
        .hero {{ padding: 1.5rem; }}
        .hero-art {{ display: none; }}
        .hero-title {{ font-size: 2rem; }}
    }}

    /* ---------- Feature tiles ---------- */
    .feat-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }}
    @media (max-width: 900px) {{ .feat-grid {{ grid-template-columns: 1fr; }} }}
    .feat {{
        background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 12px;
        box-shadow: {t['shadow']}; padding: 1.25rem;
    }}
    .feat-ic {{
        width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center;
        background: {t['primary_soft']}; border: 1px solid {t['primary_soft_border']}; font-size: 1.15rem;
        margin-bottom: 0.9rem;
    }}
    .feat-num {{ font-size: 1.6rem; font-weight: 600; color: {t['heading']}; letter-spacing: -0.02em; line-height: 1.2; }}
    .feat-t {{ font-weight: 600; color: {t['heading']}; font-size: 0.95rem; margin-top: 0.15rem; }}
    .feat-s {{ font-size: 0.85rem; color: {t['muted']}; margin-top: 0.2rem; line-height: 1.5; }}

    /* ---------- Empty results state ---------- */
    .empty {{
        margin-top: 1.5rem; border: 1px dashed {t['input_border']}; border-radius: 16px;
        padding: 2.2rem 1.5rem; text-align: center; background: {t['surface']};
    }}
    .empty-ic {{
        width: 48px; height: 48px; margin: 0 auto 0.9rem auto; border-radius: 50%;
        display: flex; align-items: center; justify-content: center; font-size: 1.3rem;
        background: {t['primary_soft']}; box-shadow: 0 0 0 8px {t['hero_top']};
    }}
    .empty-t {{ font-weight: 600; color: {t['heading']}; font-size: 1.05rem; }}
    .empty-s {{ color: {t['muted']}; font-size: 0.9rem; margin: 0.3rem auto 1.1rem auto; max-width: 460px; }}
    .steps {{ display: inline-flex; flex-wrap: wrap; justify-content: center; align-items: center; gap: 0.5rem; }}
    .step {{
        display: inline-flex; align-items: center; gap: 0.45rem; font-size: 0.85rem; font-weight: 500;
        color: {t['text']}; border: 1px solid {t['border']}; border-radius: 999px;
        padding: 0.3rem 0.75rem 0.3rem 0.3rem; background: {t['bg']};
    }}
    .step b {{
        width: 22px; height: 22px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center;
        background: {PRIMARY}; color: #fff; font-size: 0.75rem;
    }}
    .step-sep {{ color: {t['muted']}; }}

    /* ---------- Evidence section (landing) ---------- */
    .ev-card {{
        background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 12px;
        box-shadow: {t['shadow']}; padding: 1.25rem 1.5rem; margin: 1.5rem 0;
    }}
    .ev-legend {{ display: flex; gap: 1.25rem; flex-wrap: wrap; font-size: 0.8rem; color: {t['muted']}; margin: 0.6rem 0 0.9rem 0; }}
    .ev-legend span {{ display: inline-flex; align-items: center; gap: 0.4rem; }}
    .ev-sw-band, .ev-sw-pop {{ display: inline-block; }}
    .ev-sw-band {{ width: 18px; height: 8px; border-radius: 4px; background: {PRIMARY}; }}
    .ev-sw-pop {{ width: 3px; height: 12px; border-radius: 2px; background: {t['heading']}; }}
    table.ev {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; min-width: 680px; }}
    table.ev, table.ev th, table.ev td, table.ev tr {{ border-left: none !important; border-right: none !important; border-top: none !important; }}
    table.ev th {{
        background: {t['bg']}; color: {t['muted']}; font-weight: 500; font-size: 0.75rem; text-align: left;
        padding: 0.7rem 1.25rem; border-bottom: 1px solid {t['border']};
    }}
    table.ev td {{ padding: 1rem 1.25rem; border-bottom: 1px solid {t['border']}; color: {t['muted']}; vertical-align: top; }}
    table.ev tr:last-child td {{ border-bottom: none; }}
    .ev-gene {{ color: {t['heading']}; font-weight: 600; font-size: 0.95rem; }}
    .ev-syn {{ font-size: 0.8rem; margin-top: 0.15rem; }}
    .ev-tags {{ display: flex; flex-wrap: wrap; gap: 0.3rem; margin-top: 0.55rem; }}
    .ev-metric {{ margin-bottom: 0.7rem; min-width: 230px; }}
    .ev-metric:last-child {{ margin-bottom: 0; }}
    .ev-mhead {{ display: flex; justify-content: space-between; gap: 0.75rem; font-size: 0.8rem; margin-bottom: 0.3rem; }}
    .ev-mhead b {{ color: {t['heading']}; font-weight: 600; }}
    .ev-track {{ position: relative; height: 8px; border-radius: 999px; background: {t['subtle']}; }}
    .ev-band {{ position: absolute; top: 0; bottom: 0; border-radius: 999px; background: {PRIMARY}; min-width: 6px; }}
    .ev-pop {{
        position: absolute; top: -3px; width: 3px; height: 14px; border-radius: 2px;
        background: {t['heading']}; box-shadow: 0 0 0 2px {t['surface']};
    }}
    .ev-freq {{ color: {t['text']}; font-size: 0.85rem; line-height: 1.5; }}
    .ev-life {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; margin-top: 1rem; }}
    @media (max-width: 900px) {{ .ev-life {{ grid-template-columns: 1fr; }} }}
    .ev-life > div {{ border: 1px solid {t['border']}; border-radius: 12px; padding: 1rem 1.1rem; background: {t['bg']}; }}
    .ev-life-num {{ font-size: 1.5rem; font-weight: 600; color: {t['heading']}; letter-spacing: -0.02em; }}
    .ev-life-t {{ font-size: 0.875rem; color: {t['text']}; margin-top: 0.15rem; }}
    .ev-src {{ font-size: 0.75rem; color: {t['muted']}; margin-top: 0.35rem; }}
    .ev-caution {{
        margin-top: 1rem; border-radius: 12px; padding: 1rem 1.15rem; border: 1px solid {warn[2]};
        background: {warn[0]}; color: {t['text']}; font-size: 0.85rem; line-height: 1.6;
    }}
    .ev-caution b {{ color: {warn[1]}; }}
    .ev-caution ul {{ margin: 0.35rem 0 0 1.1rem; padding: 0; }}
    .ev-caution li {{ margin: 0.15rem 0; font-size: 0.85rem; }}
    .ev-caution a, .ev-sources a {{ color: {t['primary_text']}; }}
    .ev-sources {{ font-size: 0.78rem; color: {t['muted']}; margin-top: 0.8rem; line-height: 1.7; }}

    /* ---------- Page header ---------- */
    .page-head {{ display: flex; align-items: flex-end; justify-content: space-between; gap: 1rem; margin-bottom: 1.6rem; flex-wrap: wrap; }}
    .page-title {{ font-size: 1.875rem; font-weight: 600; color: {t['heading']}; letter-spacing: -0.02em; line-height: 1.25; margin: 0; }}
    .page-sub {{ color: {t['muted']}; font-size: 1rem; margin-top: 0.25rem; }}

    /* ---------- Cards (keyed containers) ---------- */
    div[class*="st-key-card"] {{
        background: {t['surface']};
        border: 1px solid {t['border']};
        border-radius: 12px;
        box-shadow: {t['shadow']};
        padding: 1.25rem 1.5rem 1.25rem 1.5rem;
        gap: 0.75rem;
    }}
    .card-h {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; }}
    .card-t {{ font-size: 1.05rem; font-weight: 600; color: {t['heading']}; line-height: 1.5; }}
    .card-s {{ font-size: 0.875rem; color: {t['muted']}; margin-top: 0.1rem; }}
    .kebab {{ color: {t['muted']}; font-size: 1.1rem; line-height: 1; letter-spacing: 1px; }}

    /* ---------- KPI tiles ---------- */
    .kpi {{
        background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 12px;
        box-shadow: {t['shadow']}; padding: 1.25rem 1.5rem; height: 100%;
    }}
    .kpi-label {{ font-size: 0.875rem; font-weight: 500; color: {t['muted']}; }}
    .kpi-row {{ display: flex; align-items: flex-end; justify-content: space-between; gap: 0.6rem; margin-top: 0.5rem; flex-wrap: wrap; }}
    .kpi-value {{ font-size: 2.1rem; font-weight: 600; color: {t['heading']}; letter-spacing: -0.02em; line-height: 1.15; white-space: nowrap; }}
    .kpi-foot {{ font-size: 0.8rem; color: {t['muted']}; margin-top: 0.4rem; }}

    /* ---------- Badges ---------- */
    .badge {{
        display: inline-flex; align-items: center; gap: 0.3rem; white-space: nowrap;
        border-radius: 999px; padding: 0.12rem 0.55rem; font-size: 0.75rem; font-weight: 500;
        border: 1px solid;
    }}
    .badge .dot {{ width: 6px; height: 6px; border-radius: 50%; background: currentColor; }}
    .b-good {{ background: {good[0]}; color: {good[1]}; border-color: {good[2]}; }}
    .b-warn {{ background: {warn[0]}; color: {warn[1]}; border-color: {warn[2]}; }}
    .b-bad {{ background: {bad[0]}; color: {bad[1]}; border-color: {bad[2]}; }}
    .b-neutral {{ background: {neutral[0]}; color: {neutral[1]}; border-color: {neutral[2]}; }}
    .b-primary {{ background: {t['primary_soft']}; color: {t['primary_text']}; border-color: {t['primary_soft_border']}; }}
    .b-sq {{ border-radius: 6px; }}

    /* ---------- Data table ---------- */
    .dt-wrap {{ border: 1px solid {t['border']}; border-radius: 12px; overflow-x: auto; }}
    table.dt {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; min-width: 640px; }}
    table.dt, table.dt th, table.dt td, table.dt tr {{ border-left: none !important; border-right: none !important; border-top: none !important; }}
    table.dt th {{
        background: {t['bg']}; color: {t['muted']}; font-weight: 500; font-size: 0.75rem;
        text-align: left; padding: 0.75rem 1.5rem; border-bottom: 1px solid {t['border']};
    }}
    table.dt td {{ padding: 0.95rem 1.5rem; border-bottom: 1px solid {t['border']}; color: {t['muted']}; vertical-align: middle; }}
    table.dt tr:last-child td {{ border-bottom: none; }}
    .dt-name {{ display: flex; align-items: center; gap: 0.75rem; }}
    .dt-avatar {{
        width: 40px; height: 40px; border-radius: 50%; flex-shrink: 0;
        display: flex; align-items: center; justify-content: center;
        font-weight: 600; font-size: 0.8rem; color: {t['primary_text']};
        background: {t['primary_soft']}; border: 1px solid {t['primary_soft_border']};
    }}
    .dt-avatar.off {{ color: {t['muted']}; background: {t['subtle']}; border-color: {t['border']}; }}
    .dt-title {{ color: {t['heading']}; font-weight: 500; }}
    .dt-meter {{ display: flex; align-items: center; gap: 0.75rem; min-width: 180px; }}
    .dt-track {{ flex: 1; height: 8px; border-radius: 999px; background: {t['subtle']}; overflow: hidden; }}
    .dt-fill {{ height: 100%; border-radius: 999px; background: {PRIMARY}; }}
    table.dt-compact {{ min-width: 0 !important; }}
    table.dt-compact th, table.dt-compact td {{ padding: 0.7rem 0.6rem !important; }}
    table.dt-compact th:first-child, table.dt-compact td:first-child {{ padding-left: 1rem !important; }}
    table.dt-compact .dt-meter {{ min-width: 70px; gap: 0.5rem; }}
    table.dt-compact .dt-track {{ min-width: 48px; }}
    table.dt-compact .dt-title {{ white-space: nowrap; }}
    table.dt-compact .dt-sub {{ font-size: 0.78rem; }}
    table.dt-compact td:last-child {{ white-space: nowrap; }}
    table.dt-compact th {{ white-space: nowrap; }}
    .dt-num {{ color: {t['heading']}; font-weight: 500; min-width: 2.5rem; text-align: right; }}

    /* ---------- Risk callout ---------- */
    .callout {{
        display: flex; gap: 0.85rem; align-items: flex-start;
        border: 1px solid; border-radius: 12px; padding: 1rem 1.15rem; margin-bottom: 1.25rem;
    }}
    .callout .ic {{
        width: 36px; height: 36px; border-radius: 50%; flex-shrink: 0;
        display: flex; align-items: center; justify-content: center; font-weight: 700;
        background: currentColor;
    }}
    .callout .ic span {{ color: {t['surface']}; font-size: 1rem; }}
    .callout .ct {{ font-weight: 600; font-size: 0.95rem; }}
    .callout .cs {{ font-size: 0.875rem; color: {t['text']}; margin-top: 0.1rem; }}
    .c-good {{ background: {good[0]}; color: {good[1]}; border-color: {good[2]}; }}
    .c-warn {{ background: {warn[0]}; color: {warn[1]}; border-color: {warn[2]}; }}
    .c-bad {{ background: {bad[0]}; color: {bad[1]}; border-color: {bad[2]}; }}

    /* ---------- Hint row inside form tabs ---------- */
    .hint {{
        display: flex; gap: 0.6rem; align-items: center; color: {t['muted']};
        font-size: 0.875rem; margin: 0.2rem 0 0.9rem 0;
    }}
    .hint b {{ color: {t['heading']}; font-weight: 600; white-space: nowrap; }}
    @media (max-width: 640px) {{ .hint {{ flex-direction: column; align-items: flex-start; gap: 0.15rem; }} }}

    /* ---------- Inputs ---------- */
    [data-testid="stWidgetLabel"] p {{ font-size: 0.875rem !important; font-weight: 500 !important; color: {t['text']} !important; }}
    div[data-baseweb="input"], div[data-baseweb="textarea"], div[data-baseweb="select"] > div {{
        background: {t['surface']} !important;
        border: 1px solid {t['input_border']} !important;
        border-radius: 8px !important;
        box-shadow: {t['shadow']};
        min-height: 44px;
    }}
    div[data-baseweb="input"] > div, div[data-baseweb="textarea"] > div,
    div[data-baseweb="input"] input, div[data-baseweb="textarea"] textarea {{
        background: transparent !important; border: none !important;
        color: {t['heading']} !important; font-size: 0.95rem !important;
    }}
    div[data-baseweb="select"] * {{ color: {t['heading']} !important; }}
    div[data-baseweb="input"]:focus-within, div[data-baseweb="textarea"]:focus-within,
    div[data-baseweb="select"] > div:focus-within {{
        border-color: {t['line']} !important;
        box-shadow: 0 0 0 3px rgba(158,119,237,0.35) !important;
    }}
    input::placeholder, textarea::placeholder {{ color: {t['muted']} !important; opacity: 0.8 !important; }}
    [data-testid="stNumberInputContainer"], [data-testid="stTextInputRootElement"] {{
        border-color: {t['input_border']} !important; background: {t['surface']} !important; border-radius: 8px !important;
    }}
    [data-testid="stNumberInput"] div[data-baseweb="input"] {{ border: none !important; box-shadow: none !important; }}
    [data-testid="stNumberInput"] button * {{ color: {t['muted']} !important; fill: {t['muted']} !important; }}
    [data-testid="stNumberInput"] button {{ background: transparent !important; border: none !important; color: {t['muted']} !important; }}
    /* Text cursor: Streamlit's light base theme makes it dark navy, invisible in dark mode. */
    input, textarea {{ caret-color: {t['line']} !important; }}
    /* Clear "you are here" state on the field being edited or the dropdown that is open. */
    [data-testid="stTextInputRootElement"]:focus-within,
    [data-testid="stNumberInputContainer"]:focus-within,
    [data-testid="stTextArea"] div[data-baseweb="textarea"]:focus-within,
    div[data-baseweb="select"] > div:focus-within,
    div[data-baseweb="select"] > div[aria-expanded="true"] {{
        border-color: {t['line']} !important;
        box-shadow: 0 0 0 3px rgba(158,119,237,0.35) !important;
    }}
    /* Dropdown list (rendered in a floating layer outside the form) */
    [data-baseweb="popover"] > div, [data-baseweb="popover"] ul,
    [data-baseweb="menu"], [role="listbox"] {{
        background: {t['surface']} !important;
        border-color: {t['input_border']} !important;
    }}
    [data-baseweb="popover"] li, [data-baseweb="popover"] li *,
    [role="listbox"] [role="option"], [role="listbox"] [role="option"] *,
    [data-baseweb="option"], [data-baseweb="option"] * {{
        color: {t['heading']} !important;
        background-color: transparent;
    }}
    [data-baseweb="popover"] li:hover, [role="listbox"] [role="option"]:hover,
    [role="listbox"] [role="option"][aria-selected="true"],
    [data-baseweb="option"]:hover, [data-baseweb="option"][aria-selected="true"],
    [role="option"]:hover, [role="option"][aria-selected="true"] {{
        background: {t['primary_soft']} !important;
    }}
    [role="option"][aria-selected="true"], [role="option"][aria-selected="true"] *,
    [data-baseweb="option"][aria-selected="true"] * {{
        color: {t['primary_text']} !important; font-weight: 600;
    }}
    /* Help tooltips (the "?" next to a label). Streamlit paints them with the
       light base theme, so set both background and text from our tokens. */
    [data-baseweb="tooltip"] > div {{
        background: {t['surface']} !important;
        border: 1px solid {t['input_border']} !important;
        border-radius: 8px !important;
        box-shadow: {t['shadow_md']} !important;
    }}
    [data-baseweb="tooltip"] [data-testid="stTooltipContent"],
    [data-baseweb="tooltip"] [data-testid="stTooltipContent"] * {{
        background: transparent !important;
        color: {t['heading']} !important;
    }}
    [data-testid="stFileUploaderDropzone"] {{
        background: {t['surface']} !important; border: 1px dashed {t['input_border']} !important; border-radius: 12px !important;
    }}
    [data-testid="stCheckbox"] label p {{ font-size: 0.9rem !important; font-weight: 500 !important; }}

    /* ---------- Buttons ---------- */
    .stButton > button, .stDownloadButton > button {{
        border-radius: 8px !important; font-weight: 600 !important; font-size: 0.9rem !important;
        min-height: 42px; padding: 0.5rem 1rem !important; transition: background .12s ease;
        background: {t['surface']} !important; color: {t['text']} !important;
        border: 1px solid {t['input_border']} !important; box-shadow: {t['shadow']} !important;
    }}
    .stButton > button:hover, .stDownloadButton > button:hover {{ background: {t['bg']} !important; }}
    .stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {{
        background: {PRIMARY} !important; color: #fff !important; border-color: {PRIMARY} !important;
    }}
    .stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover {{
        background: {PRIMARY_DARK} !important;
    }}
    .stButton > button[kind="primary"] p, .stDownloadButton > button[kind="primary"] p {{ color: #fff !important; }}
    /* Segmented controls (e.g. the tier filter on Patient records) follow the theme. */
    [data-testid="stBaseButton-segmented_control"] {{
        background: {t['surface']} !important; border-color: {t['input_border']} !important;
    }}
    [data-testid="stBaseButton-segmented_control"] p {{ color: {t['text']} !important; }}
    [data-testid="stBaseButton-segmented_control"]:hover {{ background: {t['subtle']} !important; }}
    [data-testid="stBaseButton-segmented_controlActive"] {{
        background: {t['primary_soft']} !important; border-color: {t['line']} !important;
    }}
    [data-testid="stBaseButton-segmented_controlActive"] p {{ color: {t['primary_text']} !important; font-weight: 600 !important; }}
    [data-testid="stButtonGroup"] > div {{ flex-wrap: nowrap !important; }}
    /* Disabled buttons (e.g. Next before a step is complete) must look unavailable. */
    .stButton > button:disabled, .stButton > button[disabled] {{
        background: {t['subtle']} !important; border-color: {t['border']} !important;
        box-shadow: none !important; cursor: not-allowed !important; opacity: 1 !important;
    }}
    .stButton > button:disabled p, .stButton > button:disabled span {{ color: {t['muted']} !important; }}

    /* ---------- Tabs ---------- */
    .stTabs [data-baseweb="tab-list"] {{ gap: 0.25rem; border-bottom: 1px solid {t['border']}; }}
    .stTabs [data-baseweb="tab"] {{
        background: transparent; padding: 0.55rem 0.75rem; height: auto;
        color: {t['muted']} !important; font-weight: 600;
    }}
    .stTabs [data-baseweb="tab"] p {{ font-size: 0.9rem !important; }}
    .stTabs [aria-selected="true"] {{ color: {t['primary_text']} !important; }}
    .stTabs [aria-selected="true"] p {{ color: {t['primary_text']} !important; }}
    .stTabs [data-baseweb="tab-highlight"] {{ background: {PRIMARY} !important; height: 2px; }}
    .stTabs [data-baseweb="tab-border"] {{ display: none; }}

    /* ---------- Toggle ---------- */
    [data-testid="stSidebar"] [data-testid="stCheckbox"] {{ padding: 0.3rem 0.75rem; }}

    /* ---------- AI summary text ---------- */
    .st-key-card-summary p, .st-key-card-summary li {{ font-size: 0.95rem; line-height: 1.65; color: {t['text']}; }}

    .footer-note {{
        text-align: center; color: {t['muted']}; font-size: 0.8rem;
        margin-top: 2rem; padding-top: 1rem; border-top: 1px solid {t['border']};
    }}
    .stSpinner > div {{ border-top-color: {PRIMARY} !important; }}

    /* ---------- Sidebar navigation ---------- */
    [data-testid="stSidebar"] [data-testid="stPageLink"] {{ margin: 0; }}
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {{
        border-radius: 8px; padding: 0.45rem 0.75rem; text-decoration: none;
        background: transparent;
    }}
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] p,
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] span {{
        color: {t['text']} !important; font-weight: 500 !important; font-size: 0.92rem !important;
    }}
    [data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover {{ background: {t['subtle']} !important; }}
    .st-key-nav {{ gap: 0.15rem !important; margin-bottom: 0.5rem; }}
    .st-key-nav-active {{ gap: 0 !important; }}
    [data-testid="stSidebar"] [data-testid="stPageLink"] p {{ margin: 0 !important; line-height: 1.4 !important; }}
    .st-key-nav-active [data-testid="stPageLink-NavLink"] {{ background: {t['primary_soft']} !important; }}
    .st-key-nav-active [data-testid="stPageLink-NavLink"] p,
    .st-key-nav-active [data-testid="stPageLink-NavLink"] span {{
        color: {t['primary_text']} !important; font-weight: 600 !important;
    }}

    /* ---------- Patient summary bar (Results) ---------- */
    .ps {{ padding: 0.1rem 0; }}
    .ps-top {{ display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }}
    .ps-name {{ font-size: 1.6rem; font-weight: 600; color: {t['heading']}; letter-spacing: -0.02em; }}
    .ps-chips {{ display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.5rem; }}
    .ps-chip {{
        font-size: 0.8rem; color: {t['text']}; background: {t['surface']};
        border: 1px solid {t['border']}; border-radius: 999px; padding: 0.15rem 0.65rem;
    }}

    /* ---------- Headline risk card (Results > Overview) ---------- */
    .hl {{
        display: flex; gap: 2.5rem; align-items: center; flex-wrap: wrap;
        background: {t['surface']}; border: 1px solid {t['border']}; border-radius: 12px;
        box-shadow: {t['shadow']}; padding: 1.5rem 1.75rem; margin-top: 1rem;
    }}
    .hl-left {{ min-width: 170px; }}
    .hl-num {{ font-size: 3.4rem; font-weight: 700; color: {t['heading']}; letter-spacing: -0.03em; line-height: 1.05; margin: 0.25rem 0 0.5rem 0; }}
    .hl-num span {{ font-size: 1.8rem; font-weight: 600; color: {t['muted']}; margin-left: 0.1rem; }}
    .hl-right {{ flex: 1; min-width: 260px; }}
    .hl-range {{ color: {t['text']}; font-size: 1rem; margin-bottom: 0.9rem; }}
    .hl-range b {{ color: {t['heading']}; }}
    .hl-scale {{ position: relative; height: 14px; border-radius: 999px; overflow: hidden; background: {t['subtle']}; }}
    .hl-zone {{ position: absolute; top: 0; bottom: 0; opacity: 0.9; }}
    .z-good {{ background: {t['good'][0]}; }}
    .z-warn {{ background: {t['warn'][0]}; }}
    .z-bad {{ background: {t['bad'][0]}; }}
    .hl-band {{ position: absolute; top: 2px; bottom: 2px; border-radius: 999px; background: {t['line']}; opacity: 0.45; }}
    .hl-mark {{ position: absolute; top: -2px; bottom: -2px; width: 4px; margin-left: -2px; border-radius: 2px; background: {PRIMARY_DARK}; }}
    .hl-ticks {{ position: relative; height: 1.2rem; margin-top: 0.3rem; font-size: 0.75rem; color: {t['muted']}; }}
    .hl-ticks span {{ position: absolute; transform: translateX(-50%); }}
    .hl-ticks span:first-child {{ transform: none; }}
    .hl-ticks span:last-child {{ transform: translateX(-100%); }}
    .hl-note {{ font-size: 0.85rem; color: {t['muted']}; margin-top: 0.6rem; line-height: 1.5; }}
    .hl-note b {{ color: {t['text']}; }}

    /* ---------- About page ---------- */
    .ab-steps {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-top: 0.75rem; }}
    @media (max-width: 900px) {{ .ab-steps {{ grid-template-columns: 1fr; }} }}
    .ab-step {{ display: flex; gap: 0.75rem; align-items: flex-start; }}
    .ab-n {{
        flex-shrink: 0; width: 28px; height: 28px; border-radius: 999px; display: grid; place-items: center;
        background: {t['primary_soft']}; color: {t['primary_text']}; font-weight: 600; font-size: 0.85rem;
        border: 1px solid {t['primary_soft_border']};
    }}
    .ab-t {{ font-weight: 600; color: {t['heading']}; font-size: 0.95rem; }}
    .ab-s {{ color: {t['muted']}; font-size: 0.85rem; margin-top: 0.2rem; line-height: 1.5; }}
    .ab-body p {{ color: {t['text']}; font-size: 0.9rem !important; line-height: 1.6 !important; margin: 0.6rem 0 0 0; }}
    .ab-body b {{ color: {t['heading']}; }}

    /* ---------- Form wizard ---------- */
    .wz {{ display: flex; align-items: center; gap: 0.75rem; margin: 0.1rem 0 1.25rem 0; flex-wrap: wrap; }}
    .wz-step {{ display: flex; align-items: center; gap: 0.5rem; font-size: 0.9rem; font-weight: 500; color: {t['muted']}; }}
    .wz-n {{
        width: 28px; height: 28px; border-radius: 999px; display: grid; place-items: center;
        font-size: 0.82rem; font-weight: 600; border: 1.5px solid {t['input_border']};
        color: {t['muted']}; background: {t['surface']};
    }}
    .wz-current {{ color: {t['heading']}; }}
    .wz-current .wz-n {{ background: {PRIMARY}; border-color: {PRIMARY}; color: #fff; box-shadow: 0 0 0 4px rgba(158,119,237,0.25); }}
    .wz-done {{ color: {t['text']}; }}
    .wz-done .wz-n {{ background: {t['primary_soft']}; border-color: {t['primary_soft_border']}; color: {t['primary_text']}; }}
    .wz-sep {{ flex: 1; min-width: 24px; height: 2px; border-radius: 2px; background: {t['border']}; }}
    @media (max-width: 640px) {{ .wz-l {{ display: none; }} .wz-current .wz-l {{ display: inline; }} }}
    .wz-missing {{ font-size: 0.85rem; color: {t['muted']}; line-height: 1.45; }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


# ==========================================
# LAYOUT PIECES
# ==========================================
def sidebar_brand():
    st.markdown(
        """
        <div class="sb-brand">
            <div class="sb-logo">🧬</div>
            <div class="sb-name">RiskPredict</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_label(text: str):
    st.markdown(f'<div class="sb-label">{_esc(text)}</div>', unsafe_allow_html=True)


def sidebar_footer():
    st.markdown(
        '<div class="sb-foot">Educational estimate only — not a substitute for genetic '
        'counseling. See <b>About &amp; method</b>.</div>',
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str, right_html: str = ""):
    st.markdown(
        f"""
        <div class="page-head">
            <div>
                <div class="page-title">{_esc(title)}</div>
                <div class="page-sub">{_esc(subtitle)}</div>
            </div>
            <div>{right_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _helix_svg(width: int = 300, height: int = 190) -> str:
    """Decorative DNA double helix drawn in the accent purples."""
    import math

    t = tokens()
    mid, amp, period = height / 2, height * 0.34, 150.0
    top, bottom, rungs, dots = [], [], [], []
    x = 10.0
    while x <= width - 10:
        phase = 2 * math.pi * x / period
        top.append(f"{x:.1f},{mid + amp * math.sin(phase):.1f}")
        bottom.append(f"{x:.1f},{mid - amp * math.sin(phase):.1f}")
        x += 2.0
    for i in range(int((width - 20) / 12) + 1):
        x = 10 + i * 12
        phase = 2 * math.pi * x / period
        y1, y2 = mid + amp * math.sin(phase), mid - amp * math.sin(phase)
        depth = abs(math.cos(phase))
        rungs.append(
            f'<line x1="{x}" y1="{y1:.1f}" x2="{x}" y2="{y2:.1f}" stroke="#9E77ED" '
            f'stroke-opacity="{0.15 + 0.35 * depth:.2f}" stroke-width="3" stroke-linecap="round"/>'
        )
        front = math.cos(phase) > 0
        near, far = (PRIMARY_DARK, "#B692F6") if front else ("#B692F6", PRIMARY_DARK)
        dots.append(f'<circle cx="{x}" cy="{y1:.1f}" r="{3.5 if front else 2.5}" fill="{near}"/>')
        dots.append(f'<circle cx="{x}" cy="{y2:.1f}" r="{2.5 if front else 3.5}" fill="{far}"/>')
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" aria-hidden="true">'
        f'<circle cx="{width * 0.7:.0f}" cy="{mid:.0f}" r="{height * 0.48:.0f}" fill="{t["primary_soft"]}" opacity="0.7"/>'
        + "".join(rungs)
        + f'<polyline points="{" ".join(top)}" fill="none" stroke="{PRIMARY}" stroke-width="2.5" stroke-linecap="round"/>'
        + f'<polyline points="{" ".join(bottom)}" fill="none" stroke="#B692F6" stroke-width="2.5" stroke-linecap="round"/>'
        + "".join(dots)
        + "</svg>"
    )


def landing_hero():
    st.markdown(
        f"""<div class="hero">
<div class="hero-copy">
<div class="hero-pill"><b>New</b>Hybrid quantum-AI risk engine</div>
<div class="hero-title">Understand hereditary risk <span>in minutes</span></div>
<p class="hero-sub">Enter a patient's profile, genetic markers and family history. RiskPredict compares
a rule-based score with classical and quantum machine-learning models, explains what drives the risk,
and writes a plain-language clinical summary.</p>
<div class="hero-checks">
<div><i>✓</i>BRCA1, BRCA2, APC, TP53</div>
<div><i>✓</i>9-qubit quantum kernel model</div>
<div><i>✓</i>Explainable, exportable report</div>
</div>
</div>
<div class="hero-art">{_helix_svg()}</div>
</div>""",
        unsafe_allow_html=True,
    )


def empty_results():
    st.markdown(
        """<div class="empty">
<div class="empty-ic">📊</div>
<div class="empty-t">No analysis yet</div>
<div class="empty-s">Fill in a patient's details on the New assessment page and generate
an analysis. The headline risk, model predictions and AI summary will appear here.</div>
<div class="steps">
<span class="step"><b>1</b>Demographics</span><span class="step-sep">→</span>
<span class="step"><b>2</b>Markers &amp; history</span><span class="step-sep">→</span>
<span class="step"><b>3</b>Generate</span>
</div>
</div>""",
        unsafe_allow_html=True,
    )


# ==========================================
# REAL-WORLD REFERENCE DATA (landing page)
# ==========================================
# Published estimates. Lifetime risk = chance of developing the cancer by about age 70-80.
# "pop" is the general-population lifetime risk for comparison (US, SEER).
# Keep ranges as published; studies differ, so never collapse them to one number.
EVIDENCE = [
    {
        "gene": "BRCA1",
        "syndrome": "Hereditary breast & ovarian cancer",
        "tags": ["Breast", "Ovarian", "Pancreatic", "Prostate"],
        # NCI gives one combined breast figure for BRCA1 or BRCA2 carriers ("more than 60%").
        "metrics": [
            ("Breast cancer", 60, None, 13),
            ("Ovarian cancer", 39, 58, 1.1),
        ],
        "freq": "About 1 in 400 people carry a harmful BRCA1 or BRCA2 change "
                "(about 2%, or 1 in 50, of people of Ashkenazi Jewish descent).",
        "src": "NCI (reviewed July 2024)",
    },
    {
        "gene": "BRCA2",
        "syndrome": "Hereditary breast & ovarian cancer",
        "tags": ["Breast", "Ovarian", "Prostate", "Pancreatic", "Male breast"],
        "metrics": [
            ("Breast cancer", 60, None, 13),
            ("Ovarian cancer", 13, 29, 1.1),
        ],
        "freq": "Counted together with BRCA1 above. The breast cancer figure is for BRCA1 and BRCA2 carriers combined.",
        "src": "NCI (reviewed July 2024)",
    },
    # APC and TP53 risk figures are the standard GeneReviews statements but could not be
    # re-checked automatically (NCBI blocks scripted access); confirm them before publishing.
    {
        "gene": "APC",
        "syndrome": "Familial adenomatous polyposis (FAP)",
        "tags": ["Colorectal", "Duodenal", "Thyroid"],
        "metrics": [
            ("Colorectal cancer*", 95, 100, 3.9),
        ],
        "freq": "Rare inherited syndrome. *Nearly 100% in classic FAP without preventive surgery.",
        "src": "GeneReviews",
    },
    {
        "gene": "TP53",
        "syndrome": "Li-Fraumeni syndrome",
        "tags": ["Breast", "Sarcoma", "Brain", "Adrenal", "Leukemia"],
        "metrics": [
            ("Any cancer", 70, 90, 40),
        ],
        "freq": "Rare inherited syndrome. Lifetime risk is at least 70% in men and 90% in women.",
        "src": "GeneReviews",
    },
]

EVIDENCE_SOURCES = [
    ("NCI — BRCA Gene Changes: Cancer Risk and Genetic Testing",
     "https://www.cancer.gov/about-cancer/causes-prevention/genetics/brca-fact-sheet"),
    ("GeneReviews — APC-Associated Polyposis Conditions", "https://www.ncbi.nlm.nih.gov/books/NBK1345/"),
    ("GeneReviews — Li-Fraumeni Syndrome", "https://www.ncbi.nlm.nih.gov/books/NBK1311/"),
    ("NCI SEER — Cancer Stat Facts (general-population lifetime risk)", "https://seer.cancer.gov/statfacts/"),
]


def _fmt_pct(v) -> str:
    return f"{v:g}%"


def _evidence_metric(label, lo, hi, pop) -> str:
    """hi=None means the source gives only a lower bound ("more than lo%")."""
    if hi is None:
        risk = f"Over {_fmt_pct(lo)}"
        band = (f'left:{lo}%;width:{100 - lo}%;'
                f'background:linear-gradient(90deg, {PRIMARY}, rgba(127,86,217,0))')
    else:
        risk = "≈100%" if lo >= 95 else f"{_fmt_pct(lo)}–{_fmt_pct(hi)}"
        band = f"left:{lo}%;width:{max(hi - lo, 0)}%"
    return (
        f'<div class="ev-metric"><div class="ev-mhead"><span>{_esc(label)}</span>'
        f'<span><b>{risk}</b> vs {_fmt_pct(pop)}</span></div>'
        f'<div class="ev-track" title="Carriers {risk} · general population {_fmt_pct(pop)}">'
        f'<div class="ev-band" style="{band}"></div>'
        f'<div class="ev-pop" style="left:calc({pop}% - 1px)"></div></div></div>'
    )


def evidence_section():
    rows = []
    for g in EVIDENCE:
        tags = "".join(badge(tg, "neutral", square=True) for tg in g["tags"])
        metrics = "".join(_evidence_metric(*m) for m in g["metrics"])
        rows.append(
            f'<tr><td style="width:30%"><div class="ev-gene">{g["gene"]}</div><div class="ev-syn">{_esc(g["syndrome"])}</div>'
            f'<div class="ev-tags">{tags}</div></td>'
            f'<td style="width:40%">{metrics}</td>'
            f'<td><div class="ev-freq">{_esc(g["freq"])}</div><div class="ev-src">Source: {g["src"]}</div></td></tr>'
        )
    sources = " · ".join(
        f'<a href="{url}" target="_blank" rel="noopener">{_esc(name)}</a>' for name, url in EVIDENCE_SOURCES
    )
    st.markdown(
        f"""<div class="ev-card">
<div class="card-h"><div><div class="card-t">What the research says</div>
<div class="card-s">Published lifetime cancer risk for people who carry each variant, compared with the general population.</div></div></div>
<div class="ev-legend"><span><i class="ev-sw-band"></i>Carriers (published range)</span><span><i class="ev-sw-pop"></i>General population</span></div>
<div class="dt-wrap"><table class="ev">
<thead><tr><th>Gene &amp; linked cancers</th><th>Lifetime risk: carriers vs everyone</th><th>How common</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table></div>
<div class="ev-life">
<div><div class="ev-life-num">80–90%</div><div class="ev-life-t">of lung cancer deaths in the US are linked to cigarette smoking.</div><div class="ev-src">Source: CDC</div></div>
<div><div class="ev-life-num">≈ 9 in 10</div><div class="ev-life-t">cancers in the US are diagnosed in people aged 50 or older.</div><div class="ev-src">Source: American Cancer Society</div></div>
</div>
<div class="ev-caution"><b>⚠ Read these numbers with care</b>
<ul>
<li>They are averages across large groups of carriers, not a prediction for any one person. Family history, the exact variant, sex, age and screening all change individual risk.</li>
<li>Many carriers never develop cancer, and most cancers happen in people without these variants.</li>
<li>Prevention works: screening, risk-reducing surgery and medication can lower these risks substantially.</li>
<li>RiskPredict's scoring uses simplified educational weights; its percentages are not these published figures.</li>
<li>Genetic results should always be interpreted with a doctor or genetic counselor.</li>
</ul></div>
<div class="ev-sources">Sources: {sources}</div>
</div>""",
        unsafe_allow_html=True,
    )


def card_header(title: str, subtitle: str = "", right_html: str = '<span class="kebab">⋮</span>'):
    sub = f'<div class="card-s">{_esc(subtitle)}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="card-h">
            <div><div class="card-t">{_esc(title)}</div>{sub}</div>
            <div>{right_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def card(key: str):
    """A white bordered card. Use as `with ui_modules.card("x"):`."""
    return st.container(key=f"card-{key}")


def badge(text: str, kind: str = "neutral", dot: bool = False, square: bool = False) -> str:
    d = '<span class="dot"></span>' if dot else ""
    sq = " b-sq" if square else ""
    return f'<span class="badge b-{kind}{sq}">{d}{_esc(text)}</span>'


def hint(title: str, body: str):
    st.markdown(f'<div class="hint"><b>{_esc(title)}</b><span>{_esc(body)}</span></div>', unsafe_allow_html=True)


# ==========================================
# RISK HELPERS
# ==========================================
def risk_level(value: float):
    """Returns (label, badge kind) for a risk percentage."""
    if value < 20.0:
        return "Low risk", "good"
    if value < 50.0:
        return "Moderate risk", "warn"
    return "High risk", "bad"


def risk_banner(mean_value: float):
    label, kind = risk_level(mean_value)
    copy = {
        "good": ("✓", "Patient condition: good", "Low overall disease risk profile. Continue routine screening."),
        "warn": ("!", "Patient condition: concerning", "Moderate risk identified. Consider enhanced screening and counseling."),
        "bad": ("!", "Patient condition: high risk", "Action and specialist follow-up are strongly recommended."),
    }[kind]
    st.markdown(
        f"""
        <div class="callout c-{kind}">
            <div class="ic"><span>{copy[0]}</span></div>
            <div><div class="ct">{copy[1]}</div><div class="cs">{copy[2]}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_tiles(base: str, mean: float, ci: tuple, base_val: float):
    label, kind = risk_level(mean)
    # "0.4–12.6%" fits on one line; "[0.4%, 12.6%]" wrapped at this font size.
    ci = f"{ci[0]:g}–{ci[1]:g}%"
    diff = round(mean - base_val, 1)
    arrow = "↑" if diff > 0 else ("↓" if diff < 0 else "→")
    tiles = [
        ("Baseline risk", base, badge("Rule-based", "neutral"), "Deterministic score from markers & lifestyle"),
        ("Simulated mean", f"{mean}%", badge(label, kind, dot=True), f"{arrow} {abs(diff)} pts vs baseline"),
        ("90% confidence interval", ci, badge("1,500 runs", "primary"), "5th – 95th percentile of simulations"),
    ]
    cols = st.columns(3)
    for col, (lbl, val, b, foot) in zip(cols, tiles):
        col.markdown(
            f"""
            <div class="kpi">
                <div class="kpi-label">{lbl}</div>
                <div class="kpi-row"><div class="kpi-value">{_esc(val)}</div>{b}</div>
                <div class="kpi-foot">{_esc(foot)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ==========================================
# CHARTS
# ==========================================
def _distribution_from_figure(risk_plot):
    """
    Pulls the per-bin density and per-tier shares out of the heatmap figure
    produced by quantum_engine.run_simulation (rows: High, Moderate, Low).
    """
    trace = risk_plot.data[0]
    x = [float(v) for v in trace.x]
    z = [list(row) for row in trace.z]
    density = [sum(z[r][i] for r in range(len(z))) for i in range(len(x))]
    high, moderate, low = (round(float(sum(row)), 1) for row in z)
    return x, density, {"Low <20%": low, "Moderate 20–50%": moderate, "High ≥50%": high}


def _base_layout(t, height):
    return dict(
        height=height,
        margin=dict(l=8, r=8, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=14, color=t["muted"]),
        hoverlabel=dict(bgcolor=t["surface"], bordercolor=t["border"], font=dict(color=t["heading"], size=14)),
    )


def distribution_area(risk_plot, mean: float, ci_low: float, ci_high: float):
    t = tokens()
    x, density, _ = _distribution_from_figure(risk_plot)
    fig = go.Figure()
    fig.add_vrect(x0=ci_low, x1=ci_high, fillcolor=t["band"], line_width=0, layer="below")
    fig.add_trace(
        go.Scatter(
            x=x,
            y=density,
            mode="lines",
            line=dict(color=t["line"], width=2, shape="spline", smoothing=0.8),
            fill="tozeroy",
            fillcolor=t["area"],
            name="Simulated runs",
            hovertemplate="Risk %{x:.1f}%<br>%{y:.1f}% of runs<extra></extra>",
        )
    )
    fig.add_vline(x=mean, line=dict(color=t["heading"], width=1, dash="dot"))
    fig.add_annotation(
        x=mean, y=1, yref="paper", text=f"Mean {mean}%", showarrow=False,
        yanchor="bottom", font=dict(color=t["heading"], size=13),
    )
    fig.update_layout(
        **_base_layout(t, 250),
        showlegend=False,
        hovermode="x unified",
        xaxis=dict(
            range=[0, 100], ticksuffix="%", showgrid=False, zeroline=False,
            linecolor=t["border"], title=dict(text="Predicted risk score", font=dict(size=14)),
        ),
        yaxis=dict(
            ticksuffix="%", gridcolor=t["grid"], zeroline=False,
            title=dict(text="Share of runs", font=dict(size=14)),
        ),
    )
    fig.update_layout(height=300, margin=dict(l=64, r=16, t=28, b=56))
    return fig


def chart_config():
    return {"displayModeBar": False}


# ==========================================
# FACTOR TABLE
# ==========================================
# Mirrors the weights in quantum_engine.calculate_deterministic_risk.
MARKERS = [
    ("BRCA1", "Breast / ovarian cancer", 30.0),
    ("BRCA2", "Breast / ovarian cancer", 25.0),
    ("APC", "Colorectal cancer", 20.0),
    ("TP53", "Li-Fraumeni syndrome", 35.0),
]


def _age_points(age) -> float:
    try:
        age = float(age or 0)
    except (TypeError, ValueError):
        age = 0
    return 8.0 if age > 70 else 5.0 if age > 50 else 0.0


def factor_rows(patient_data: dict):
    genetics = patient_data.get("Genetic Markers", {})
    rows = []
    for name, condition, weight in MARKERS:
        present = bool(genetics.get(name))
        rows.append(dict(
            code=name, title=name, sub=condition, kind="Genetic marker",
            points=weight if present else 0.0,
            status=("Detected", "bad") if present else ("Not detected", "good"),
        ))
    for name in patient_data.get("Other Genetic Markers", []):
        rows.append(dict(
            code=name, title=name, sub="Added by clinician · not scored", kind="Genetic marker",
            points=0.0, status=("Reported", "warn"),
        ))
    age = patient_data.get("Age")
    pts = _age_points(age)
    rows.append(dict(
        code="AG", title="Age", sub=f"{int(age)} years" if age else "Not provided", kind="Demographic",
        points=pts, status=("Elevated", "warn") if pts else ("Baseline", "good"),
    ))
    smoking = patient_data.get("Smoking History", "Never Smoked")
    spts = {"Current Smoker": 10.0, "Former Smoker": 3.0}.get(smoking, 0.0)
    rows.append(dict(
        code="SM", title="Smoking", sub=smoking, kind="Lifestyle",
        points=spts, status=("Elevated", "warn") if spts else ("Baseline", "good"),
    ))
    family = patient_data.get("Family History", {}) or {}
    first, second = family.get("First-degree", 0) or 0, family.get("Second-degree", 0) or 0
    fpts = quantum_engine.family_history_points(patient_data)
    rows.append(dict(
        code="FH", title="Family history",
        sub=f"{first} first-degree · {second} second-degree relatives", kind="Hereditary",
        points=fpts, status=("Elevated", "warn") if fpts else ("None reported", "good"),
    ))
    return rows


def factor_table(patient_data: dict):
    rows = factor_rows(patient_data)
    body = []
    for r in rows:
        width = min(r["points"] / 35.0 * 100, 100)
        avatar_cls = "dt-avatar" if r["points"] else "dt-avatar off"
        body.append(f"""
            <tr>
                <td><div class="dt-name"><div class="{avatar_cls}">{_esc(r['code'][:4])}</div>
                    <div><div class="dt-title">{_esc(r['title'])}</div><div>{_esc(r['sub'])}</div></div></div></td>
                <td><div class="dt-meter"><div class="dt-track"><div class="dt-fill" style="width:{width:.0f}%"></div></div>
                    <span class="dt-num">+{r['points']:.0f}</span></div></td>
                <td>{badge(r['status'][0], r['status'][1], dot=True)}</td>
                <td>{badge(r['kind'], 'primary', square=True)}</td>
            </tr>""")
    st.markdown(
        f"""
        <div class="dt-wrap"><table class="dt">
            <thead><tr><th>Factor</th><th>Risk contribution (pts)</th><th>Status</th><th>Category</th></tr></thead>
            <tbody>{''.join(body)}</tbody>
        </table></div>
        """,
        unsafe_allow_html=True,
    )


# ==========================================
# ML MODEL PREDICTIONS (results page)
# ==========================================
MODEL_BLURBS = {
    "Logistic regression": ("LR", "Linear, explainable"),
    "Random forest": ("RF", "400 decision trees"),
    "Quantum kernel SVM": ("QK", "9 qubits · Qiskit"),
}


def models_missing_notice():
    hint(
        "ML models not trained yet.",
        "Run `python -m ml.train` in the final_app folder, then refresh this page.",
    )


def model_predictions(preds: dict, reference: float | None):
    """Table of each trained model's 20-year risk for this patient."""
    rows = []
    for name, p in preds.items():
        code, blurb = MODEL_BLURBS.get(name, (name[:2].upper(), ""))
        pct = p * 100
        label, kind = risk_level(pct)
        rows.append(f"""
            <tr>
                <td><div class="dt-name"><div class="dt-avatar">{code}</div>
                    <div><div class="dt-title">{_esc(name)}</div><div class="dt-sub">{_esc(blurb)}</div></div></div></td>
                <td><div class="dt-meter"><div class="dt-track"><div class="dt-fill" style="width:{min(pct, 100):.0f}%"></div></div>
                    <span class="dt-num">{pct:.0f}%</span></div></td>
                <td>{badge(label.replace(" risk", ""), kind, dot=True)}</td>
            </tr>""")
    if reference is not None:
        pct = reference * 100
        rows.append(f"""
            <tr>
                <td><div class="dt-name"><div class="dt-avatar off">REF</div>
                    <div><div class="dt-title">Reference formula</div><div class="dt-sub">Formula that generated the data</div></div></div></td>
                <td><div class="dt-meter"><div class="dt-track"><div class="dt-fill" style="width:{min(pct, 100):.0f}%;opacity:.35"></div></div>
                    <span class="dt-num">{pct:.0f}%</span></div></td>
                <td>{badge("Truth", "neutral", square=True)}</td>
            </tr>""")
    st.markdown(
        f"""<div class="dt-wrap"><table class="dt dt-compact">
            <thead><tr><th>Model</th><th>20-year risk</th><th>Tier</th></tr></thead>
            <tbody>{''.join(rows)}</tbody></table></div>""",
        unsafe_allow_html=True,
    )


def explanation_chart(contributions: list, base_risk: float, patient_risk: float):
    """
    Horizontal bars: how much each factor moves this patient's logistic-regression
    risk up or down compared with an average patient (in log-odds).
    """
    t = tokens()
    rows = [r for r in contributions if abs(r["log_odds"]) >= 0.005][:8][::-1]
    if not rows:
        rows = contributions[:1]
    colors = [t["line"] if r["log_odds"] > 0 else t["muted"] for r in rows]
    fig = go.Figure(go.Bar(
        x=[r["log_odds"] for r in rows],
        y=[r["label"] for r in rows],
        orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        hovertemplate="%{y}: %{x:+.2f} log-odds<extra></extra>",
    ))
    fig.add_vline(x=0, line=dict(color=t["border"], width=1))
    fig.update_layout(
        **_base_layout(t, 300),
        showlegend=False,
        xaxis=dict(title=dict(text="← lowers risk     raises risk →", font=dict(size=13)),
                   gridcolor=t["grid"], zeroline=False),
        yaxis=dict(showgrid=False, automargin=True, tickfont=dict(color=t["text"], size=13)),
        bargap=0.35,
    )
    fig.update_layout(margin=dict(l=8, r=16, t=8, b=48))
    st.plotly_chart(fig, width="stretch", config=chart_config(), theme=None)
    st.markdown(
        f'<div class="card-s">An average patient in the training data has a '
        f'{base_risk * 100:.0f}% predicted risk; these factors move this patient to '
        f'{patient_risk * 100:.0f}%. Bars are exact logistic-regression contributions '
        f'(coefficient × standardised value).</div>',
        unsafe_allow_html=True,
    )


# ==========================================
# MODEL COMPARISON TAB
# ==========================================
def _metric_cell(value, best, fmt="{:.3f}"):
    if value is None:
        return "–"
    text = fmt.format(value)
    is_best = best is not None and abs(value - best) < 1e-9
    return f'<b style="color:{PRIMARY}">{text}</b>' if is_best else text


def model_comparison(metrics: dict):
    t = tokens()
    data, models, q = metrics["dataset"], metrics["models"], metrics["quantum"]
    names = list(models)

    page_header(
        "Model comparison",
        f"Classical vs quantum models on {data['n_test']} held-out synthetic patients "
        f"(trained on {data['n_train']}).",
        badge("Synthetic data", "warn", dot=True),
    )

    hint(
        "About the data:",
        f"{data['n_patients']:,} simulated patients, not real people. Outcome: "
        f"{data['outcome']} ({data['outcome_rate'] * 100:.0f}% of patients). Best possible AUC "
        f"with the true simulated risk: {data['oracle_auc']:.3f}.",
    )

    trained = [n for n in names if models[n]["cv_auc"] is not None]
    best = {
        "auc": max(models[n]["auc"] for n in names),
        "cv_auc": max(models[n]["cv_auc"] for n in trained),
        "brier": min(models[n]["brier"] for n in names),
        "sensitivity": max(models[n]["sensitivity"] for n in names),
        "specificity": max(models[n]["specificity"] for n in names),
        "f1": max(models[n]["f1"] for n in names),
    }
    rows = []
    for n in names:
        m = models[n]
        cv = "–" if m["cv_auc"] is None else (
            _metric_cell(m["cv_auc"], best["cv_auc"])
            + f' <span class="card-s">± {m["cv_auc_std"]:.3f}</span>')
        rows.append(
            f"<tr><td><span class='dt-title'>{_esc(n)}</span></td>"
            f"<td>{_metric_cell(m['auc'], best['auc'])}</td><td>{cv}</td>"
            f"<td>{_metric_cell(m['brier'], best['brier'])}</td>"
            f"<td>{_metric_cell(m['sensitivity'], best['sensitivity'], '{:.0%}')}</td>"
            f"<td>{_metric_cell(m['specificity'], best['specificity'], '{:.0%}')}</td>"
            f"<td>{_metric_cell(m['f1'], best['f1'])}</td>"
            f"<td>{m['fit_seconds']:.2f} s</td>"
            f"<td>{'<0.01' if m['predict_ms'] < 0.01 else format(m['predict_ms'], '.2f')} ms</td></tr>"
        )
    with card("metrics"):
        card_header(
            "Test-set performance",
            f"Best value in each column highlighted. Sensitivity, specificity and F1 treat a "
            f"predicted risk ≥ {data['threshold'] * 100:.0f}% as \"at risk\". Lower Brier is better.",
            right_html="",
        )
        st.markdown(
            f"""<div class="dt-wrap"><table class="dt dt-compact" style="min-width:760px !important">
            <thead><tr><th>Model</th><th>Test AUC</th><th>CV AUC</th><th>Brier</th>
            <th>Sensitivity</th><th>Specificity</th><th>F1</th><th>Fit time</th><th>Predict / patient</th></tr></thead>
            <tbody>{''.join(rows)}</tbody></table></div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    left, right = st.columns([1.3, 1], gap="medium")
    palette = [t["muted"], "#B692F6", "#9E77ED", PRIMARY_DARK]
    with left:
        with card("roc"):
            card_header("ROC curves", "True-positive vs false-positive rate on the test set.")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Chance",
                                     line=dict(color=t["border"], dash="dot", width=1), hoverinfo="skip"))
            for n, color in zip(names, palette):
                roc = models[n]["roc"]
                fig.add_trace(go.Scatter(
                    x=roc["fpr"], y=roc["tpr"], mode="lines", name=f"{n} ({models[n]['auc']:.3f})",
                    line=dict(color=color, width=2.5 if "Quantum" in n else 1.8,
                              dash="dash" if n == "Rule-based score" else "solid"),
                    hovertemplate="FPR %{x:.2f} · TPR %{y:.2f}<extra>" + n + "</extra>",
                ))
            fig.update_layout(
                **_base_layout(t, 360), showlegend=True,
                legend=dict(x=0.98, xanchor="right", y=0.02, yanchor="bottom",
                            bgcolor="rgba(0,0,0,0)", font=dict(color=t["text"], size=12)),
                xaxis=dict(title="False-positive rate", range=[0, 1], gridcolor=t["grid"], zeroline=False),
                yaxis=dict(title="True-positive rate", range=[0, 1.02], gridcolor=t["grid"], zeroline=False),
            )
            fig.update_layout(margin=dict(l=56, r=16, t=8, b=48))
            st.plotly_chart(fig, width="stretch", config=chart_config(), theme=None)
    with right:
        with card("qinfo"):
            card_header("Quantum model", "Kernel SVM on simulated quantum states.", right_html="")
            gates = ", ".join(f"{v} {k.upper()}" for k, v in q["gate_counts"].items())
            items = [
                ("Qubits", f"{q['qubits']} (one per feature)"),
                ("Feature map", q["feature_map"]),
                ("Circuit", f"depth {q['depth']} · {gates} gates"),
                ("Kernel", "Fidelity |⟨ψ(x)|ψ(y)⟩|², exact simulation"),
                ("Tuned by CV", f"angle scale {q['best_params']['scale']}, C = {q['best_params']['C']}"),
                ("Tuning time", f"{models['Quantum kernel SVM'].get('tuning_seconds', 0):.0f} s"),
            ]
            st.markdown(
                "<div class='dt-wrap'><table class='dt' style='min-width:0'><tbody>"
                + "".join(f"<tr><td style='white-space:nowrap'><span class='dt-title'>{k}</span></td>"
                          f"<td>{_esc(v)}</td></tr>" for k, v in items)
                + "</tbody></table></div>",
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    with card("importance"):
        card_header("What the random forest relies on",
                    "Feature importance: each feature's share of the forest's total impurity reduction.",
                    right_html="")
        from ml.schema import FEATURE_LABELS
        imp = metrics["feature_importance"]["Random forest (impurity importance)"]
        pairs = sorted(imp.items(), key=lambda kv: kv[1])
        fig = go.Figure(go.Bar(
            x=[v for _, v in pairs], y=[FEATURE_LABELS.get(k, k) for k, _ in pairs], orientation="h",
            marker=dict(color=t["line"]), hovertemplate="%{y}: %{x:.1%}<extra></extra>",
        ))
        fig.update_layout(**_base_layout(t, 320), showlegend=False,
                          xaxis=dict(tickformat=".0%", gridcolor=t["grid"], zeroline=False),
                          yaxis=dict(automargin=True, tickfont=dict(color=t["text"], size=13)))
        fig.update_layout(margin=dict(l=8, r=16, t=8, b=32))
        st.plotly_chart(fig, width="stretch", config=chart_config(), theme=None)


# ==========================================
# RESULTS PAGE PIECES
# ==========================================
def patient_summary(patient: dict, right_badge: str = ""):
    """One-line patient summary shown above the results (replaces the full form)."""
    try:
        from features import positive_markers
    except ModuleNotFoundError:
        from .features import positive_markers
    family = patient.get("Family History", {}) or {}
    first, second = family.get("First-degree", 0) or 0, family.get("Second-degree", 0) or 0
    age = patient.get("Age")
    markers = positive_markers(patient) + list(patient.get("Other Genetic Markers", []))
    bits = [
        f"{int(age)} yrs" if age is not None else None,
        patient.get("Gender") if patient.get("Gender") not in (None, "Select") else None,
        (patient.get("Smoking History") or "").replace("Smoked", "smoked").replace("Smoker", "smoker"),
        ", ".join(markers) if markers else "No scored mutations",
        f"{first} first-degree · {second} second-degree relatives" if (first or second) else "No family history",
    ]
    chips = "".join(f'<span class="ps-chip">{_esc(b)}</span>' for b in bits if b)
    st.markdown(
        f"""<div class="ps">
            <div class="ps-top"><span class="ps-name">{_esc(patient.get('Name') or 'Patient')}</span>{right_badge}</div>
            <div class="ps-chips">{chips}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def headline_card(mean: float, ci_low: float, ci_high: float, model_preds: dict | None = None):
    """The one number to read first: estimated risk, its likely range, and where it sits on 0-100%."""
    label, kind = risk_level(mean)
    models_line = ""
    if model_preds:
        vals = [v * 100 for v in model_preds.values()]
        models_line = (f" The three ML models predict <b>{min(vals):.0f}–{max(vals):.0f}%</b> "
                       f"over 20 years; see the <b>Models</b> tab.")
    st.markdown(
        f"""<div class="hl">
            <div class="hl-left">
                <div class="kpi-label">Estimated risk</div>
                <div class="hl-num">{mean:.0f}<span>%</span></div>
                {badge(label, kind, dot=True)}
            </div>
            <div class="hl-right">
                <div class="hl-range">Likely between <b>{ci_low:.0f}%</b> and <b>{ci_high:.0f}%</b></div>
                <div class="hl-scale">
                    <div class="hl-zone z-good" style="left:0;width:20%"></div>
                    <div class="hl-zone z-warn" style="left:20%;width:30%"></div>
                    <div class="hl-zone z-bad" style="left:50%;width:50%"></div>
                    <div class="hl-band" style="left:{ci_low:.1f}%;width:{max(ci_high - ci_low, 0.8):.1f}%"></div>
                    <div class="hl-mark" style="left:{mean:.1f}%"></div>
                </div>
                <div class="hl-ticks"><span style="left:0">0%</span><span style="left:20%">20%</span>
                    <span style="left:50%">50%</span><span style="left:100%">100%</span></div>
                <div class="hl-note">Rule-based score with 1,500 Monte Carlo runs; the range is the
                    middle 90% of runs.{models_line}</div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )


def footer_note():
    st.markdown(
        '<div class="footer-note">This tool provides an educational risk estimate and does '
        "not replace professional genetic counseling or clinical diagnosis.</div>",
        unsafe_allow_html=True,
    )


# ==========================================
# ABOUT PAGE
# ==========================================
def about_page(metrics: dict | None):
    page_header("About & method", "How RiskPredict works, what the data is, and its limits.")
    steps = [
        ("Enter the patient", "Demographics, the four scored genes (BRCA1, BRCA2, APC, TP53), "
                              "other reported mutations, smoking and family history."),
        ("Rule-based score", "Hand-weighted points for each factor, plus 1,500 Monte Carlo runs "
                             "to show how certain the estimate is (90% range)."),
        ("Machine-learning models", "Logistic regression, a random forest and a 9-qubit quantum "
                                    "kernel SVM predict 20-year risk; the logistic regression "
                                    "explains which factors drive it."),
        ("AI summary and report", "Gemini turns de-identified results into plain-language "
                                  "guidance; everything can be exported as a PDF."),
    ]
    step_html = "".join(
        f'<div class="ab-step"><div class="ab-n">{i}</div><div><div class="ab-t">{_esc(t)}</div>'
        f'<div class="ab-s">{_esc(b)}</div></div></div>'
        for i, (t, b) in enumerate(steps, 1)
    )
    with card("how"):
        card_header("How an assessment works", "", right_html="")
        st.markdown(f'<div class="ab-steps">{step_html}</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    left, right = st.columns(2, gap="medium")
    with left:
        with card("data"):
            card_header("Data and models", "", right_html=badge("Synthetic data", "warn", dot=True))
            if metrics:
                d, q = metrics["dataset"], metrics["quantum"]
                best = max(metrics["models"].items(), key=lambda kv: kv[1]["auc"])
                body = (
                    f"<p>The models are trained on <b>{d['n_patients']:,} simulated patients</b>, not real people. "
                    f"Each one's risk is built from published lifetime-risk figures (NCI, GeneReviews, SEER) "
                    f"plus stated assumptions, and their outcome is drawn from that risk.</p>"
                    f"<p>Outcome: {_esc(d['outcome'])} ({d['outcome_rate'] * 100:.0f}% of patients). "
                    f"Best test AUC: <b>{_esc(best[0])}</b> ({best[1]['auc']:.3f}); the best possible "
                    f"on this data is {d['oracle_auc']:.3f}.</p>"
                    f"<p>The quantum model uses {q['qubits']} qubits ({_esc(q['feature_map'])}), "
                    f"simulated exactly with Qiskit.</p>"
                )
            else:
                body = "<p>Models are not trained yet. Run <code>python -m ml.train</code>.</p>"
            st.markdown(f'<div class="ab-body">{body}</div>', unsafe_allow_html=True)
    with right:
        with card("privacy"):
            card_header("Privacy", "", right_html="")
            st.markdown(
                '<div class="ab-body"><p>Only de-identified data is sent to the AI: no name, a '
                '10-year age band instead of the exact age, and emails, phone numbers and ID numbers '
                'removed from the notes.</p><p>Each generated assessment is saved to the patient '
                'records database (MongoDB, or a local file if MongoDB is unavailable), including the '
                'patient name, so it can be found again. Uploaded lab reports are not saved. '
                'Records can be deleted from the <b>Patient records</b> page.</p></div>',
                unsafe_allow_html=True,
            )
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        with card("limits"):
            card_header("Limitations", "", right_html="")
            st.markdown(
                '<div class="ab-body"><p>RiskPredict is an educational project. Its numbers are not '
                'validated on real patients and must not be used for diagnosis or treatment '
                'decisions. Genetic results should always be interpreted with a doctor or genetic '
                'counselor.</p></div>',
                unsafe_allow_html=True,
            )


# ==========================================
# PATIENT RECORDS PAGE
# ==========================================
def fmt_when(dt) -> str:
    """Local date and time, e.g. '19 Nov 2026, 16:42'."""
    return dt.astimezone().strftime("%d %b %Y, %H:%M")


def records_stats(patients: list):
    total = sum(p["assessments"] for p in patients)
    high = sum(1 for p in patients if p["latest_tier"] == "High risk")
    moderate = sum(1 for p in patients if p["latest_tier"] == "Moderate risk")
    tiles = [
        ("Patients", f"{len(patients)}", "People with at least one saved assessment"),
        ("Assessments", f"{total}", "All saved analyses, including repeats"),
        ("Need follow-up", f"{high + moderate}", f"{high} high risk · {moderate} moderate risk (latest result)"),
    ]
    cols = st.columns(3)
    for col, (label, value, foot) in zip(cols, tiles):
        col.markdown(
            f'<div class="kpi"><div class="kpi-label">{label}</div>'
            f'<div class="kpi-row"><div class="kpi-value">{value}</div></div>'
            f'<div class="kpi-foot">{_esc(foot)}</div></div>',
            unsafe_allow_html=True,
        )


def _chips(items: list, kind: str = "neutral", empty: str = "None") -> str:
    if not items:
        return f'<span class="card-s">{_esc(empty)}</span>'
    return " ".join(badge(i, kind, square=True) for i in items)


def records_table(patients: list):
    rows = []
    for p in patients:
        tier_kind = risk_level(p["latest_mean"])[1]
        sub = " · ".join(str(x) for x in [
            f"{int(p['age'])} yrs" if p.get("age") is not None else None,
            p.get("gender") if p.get("gender") not in (None, "Select") else None,
        ] if x)
        rows.append(f"""
            <tr>
                <td><div class="dt-name"><div class="dt-avatar">{_esc(_initials(p['name']))}</div>
                    <div><div class="dt-title">{_esc(p['name'])}</div><div class="dt-sub">{_esc(sub)}</div></div></div></td>
                <td><div class="dt-meter"><div class="dt-track"><div class="dt-fill" style="width:{min(p['latest_mean'], 100):.0f}%"></div></div>
                    <span class="dt-num">{p['latest_mean']:.0f}%</span></div></td>
                <td>{badge(p['latest_tier'].replace(' risk', ''), tier_kind, dot=True)}</td>
                <td>{_chips(p['markers'], 'primary', 'No mutations')}</td>
                <td class="dt-wrap-cell">{_chips(p['diseases'], 'neutral', '—')}</td>
                <td style="text-align:center">{p['assessments']}</td>
                <td style="white-space:nowrap">{_esc(fmt_when(p['last_assessed']))}</td>
            </tr>""")
    st.markdown(
        f"""<div class="dt-wrap"><table class="dt dt-compact" style="min-width:980px !important">
            <thead><tr><th>Patient</th><th>Latest risk</th><th>Tier</th><th>Mutations</th>
            <th>Linked diseases</th><th>Visits</th><th>Last assessed</th></tr></thead>
            <tbody>{''.join(rows)}</tbody></table></div>""",
        unsafe_allow_html=True,
    )


def _initials(name: str) -> str:
    parts = [p for p in (name or "?").split() if p]
    return "".join(p[0] for p in parts[:2]).upper() or "?"


def history_chart(history: list):
    """Risk over time for one patient, with the 90% range as a band."""
    t = tokens()
    pts = sorted(history, key=lambda r: r["created_at"])
    x = [fmt_when(r["created_at"]) for r in pts]
    mean = [r["result"]["mean"] for r in pts]
    lo = [r["result"]["ci_low"] for r in pts]
    hi = [r["result"]["ci_high"] for r in pts]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x + x[::-1], y=hi + lo[::-1], fill="toself", fillcolor=t["band"],
                             line=dict(width=0), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(
        x=x, y=mean, mode="lines+markers", line=dict(color=t["line"], width=2.5),
        marker=dict(size=9, color=t["line"], line=dict(color=t["surface"], width=2)),
        hovertemplate="%{x}<br>Risk %{y:.0f}%<extra></extra>", showlegend=False,
    ))
    for y0, y1, color in [(0, 20, t["good"][0]), (20, 50, t["warn"][0]), (50, 100, t["bad"][0])]:
        fig.add_hrect(y0=y0, y1=y1, fillcolor=color, opacity=0.35, line_width=0, layer="below")
    fig.update_layout(
        **_base_layout(t, 280), hovermode="closest",
        xaxis=dict(type="category", showgrid=False, linecolor=t["border"]),
        yaxis=dict(range=[0, 100], ticksuffix="%", gridcolor=t["grid"], zeroline=False,
                   title=dict(text="Estimated risk", font=dict(size=13))),
    )
    fig.update_layout(margin=dict(l=56, r=16, t=12, b=40))
    st.plotly_chart(fig, width="stretch", config=chart_config(), theme=None)


def history_table(history: list):
    rows = []
    for r in history:
        res = r["result"]
        models = res.get("models") or {}
        model_txt = " · ".join(f"{MODEL_BLURBS.get(k, (k[:2],))[0]} {v * 100:.0f}%" for k, v in models.items()) or "—"
        fam = r["patient"].get("family_history") or {}
        rows.append(
            f"<tr><td style='white-space:nowrap'><span class='dt-title'>{_esc(fmt_when(r['created_at']))}</span></td>"
            f"<td><b>{res['mean']:.0f}%</b> <span class='card-s'>({res['ci_low']:.0f}–{res['ci_high']:.0f}%)</span></td>"
            f"<td>{badge(res['tier'].replace(' risk', ''), risk_level(res['mean'])[1], dot=True)}</td>"
            f"<td style='white-space:nowrap'>{_esc(model_txt)}</td>"
            f"<td>{_chips(r['patient'].get('markers', []) + r['patient'].get('other_markers', []), 'primary', 'None')}</td>"
            f"<td style='white-space:nowrap'>{fam.get('First-degree', 0)} · {fam.get('Second-degree', 0)}</td></tr>"
        )
    st.markdown(
        f"""<div class="dt-wrap"><table class="dt dt-compact" style="min-width:820px !important">
            <thead><tr><th>Date</th><th>Risk (90% range)</th><th>Tier</th><th>ML models (20-yr)</th>
            <th>Mutations</th><th>Relatives 1st · 2nd</th></tr></thead>
            <tbody>{''.join(rows)}</tbody></table></div>""",
        unsafe_allow_html=True,
    )
