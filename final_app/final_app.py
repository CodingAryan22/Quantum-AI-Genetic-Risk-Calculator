"""
RiskPredict entry point: page setup, sidebar and navigation.
The pages themselves live in views.py.

Run from this folder:  streamlit run final_app.py
"""

import streamlit as st

import data_manager
import ui_modules
import views

st.set_page_config(
    page_title="RiskPredict · Genetic Disease Risk",
    page_icon="🧬",
    layout="wide",
    # "auto" = open on desktop, collapsed on phones (where it would cover the page).
    initial_sidebar_state="auto",
)

# Streamlit forgets a widget's value when its page isn't shown. Re-saving the
# form fields on every run keeps the patient's details when you visit another
# page and come back (e.g. Results -> Edit). File uploads can't be re-saved.
data_manager.keep_form_values()

app_pages = views.pages()
page = st.navigation(list(app_pages.values()), position="hidden")

# ==========================================
# SIDEBAR: brand, navigation, workspace actions, appearance
# ==========================================
with st.sidebar:
    ui_modules.sidebar_brand()
    with st.container(key="nav"):
        for key, p in app_pages.items():
            label = p.title
            if key == "results" and views.RESULTS_KEY in st.session_state:
                tier, _ = ui_modules.risk_level(st.session_state[views.RESULTS_KEY]["mean"])
                label = f"{p.title} · {tier}"
            # Streamlit doesn't mark the current page's link in a stylable way,
            # so wrap it in a keyed container the theme CSS can highlight.
            if p.url_path == page.url_path:
                with st.container(key="nav-active"):
                    st.page_link(p, label=label)
            else:
                st.page_link(p, label=label)

    ui_modules.sidebar_label("Workspace")
    if st.button("Clear form", icon=":material/restart_alt:", key="btn-clear-form", width="stretch"):
        data_manager.clear_form()
        st.session_state.pop(views.RESULTS_KEY, None)
        st.session_state["form_cleared"] = True
        st.rerun()
    if st.button("Clear all records", icon=":material/delete:", key="btn-clear-all", width="stretch"):
        data_manager.clear_session_state()
        st.session_state["records_cleared"] = True
        st.rerun()

    ui_modules.sidebar_label("Appearance")
    dark_mode = st.toggle("Dark mode", value=True, key="dark_mode")
    ui_modules.sidebar_footer()

ui_modules.apply_theme(dark_mode)

if st.session_state.pop("form_cleared", False):
    st.toast("Patient entry form cleared.", icon="✨")
if st.session_state.pop("records_cleared", False):
    st.toast("All records cleared.", icon="✨")

page.run()
