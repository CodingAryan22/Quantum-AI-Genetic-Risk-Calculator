import streamlit as st

# Import our custom modules
import ui_modules
import data_manager
import quantum_engine
import ai_synthesizer
import pdf_builder

# Set up the page layout
st.set_page_config(
    page_title="Genetic Disease Risk Prediction",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==========================================
# 1. THEME & SIDEBAR CONTROLS
# ==========================================
ui_modules.sidebar_brand()

st.sidebar.markdown("---")
st.sidebar.subheader("Theme & Data")

# Dark Mode Toggle
dark_mode = st.sidebar.toggle("🌙 Enable Dark Mode", value=False)
ui_modules.apply_theme(dark_mode)
# Clear Form Button (resets only the current patient's entries)
if st.sidebar.button("🧹 Clear Form", use_container_width=True):
    data_manager.clear_form()
    st.session_state["form_cleared"] = True
    st.rerun()

# Clear Data Button
if st.sidebar.button("🗑️ Clear All Records", use_container_width=True):
    data_manager.clear_session_state()
    st.session_state["records_cleared"] = True
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption("RiskPredict · Hybrid Quantum-AI Clinical Decision Support")

# ==========================================
# 2. MAIN HEADER / HERO
# ==========================================
if st.session_state.pop("form_cleared", False):
    st.toast("🧹 Patient entry form cleared.", icon="✨")
if st.session_state.pop("records_cleared", False):
    st.toast("🗑️ All records cleared.", icon="✨")

st.markdown(ui_modules.brand_html(), unsafe_allow_html=True)

# ==========================================
# 3. DATA COLLECTION FORM
# ==========================================
patient_data = data_manager.render_collection_form()

# ==========================================
# 4. PROCESSING & DASHBOARD GENERATION
# ==========================================
generate_col1, generate_col2, generate_col3 = st.columns([1, 2, 1])
with generate_col2:
    run_analysis = st.button(
        "⚡ Generate Risk Analysis & AI Report", type="primary", use_container_width=True
    )

if run_analysis:

    with st.spinner("Initializing Quantum Simulation & AI Synthesis..."):

        # Step A: Run the math models
        risk_table, risk_plot = quantum_engine.run_simulation(patient_data)

        # Step B: Generate the simplified text via Gemini
        ai_summary = ai_synthesizer.generate_report(patient_data, risk_table)

        # Step C: Render the Dashboard
        st.markdown("---")
        st.header("📊 Clinical Risk Dashboard")
        st.caption("Comprehensive patient risk profile, simulation results, and clinical guidance.")

        # --- PATIENT STATUS CONDITION BANNER ---
        simulated_mean_str = risk_table["Simulated Mean"].iloc[0]
        simulated_mean_val = float(simulated_mean_str.replace("%", ""))
        ui_modules.risk_banner(simulated_mean_val)

        # --- KEY METRICS CARDS ---
        base_str = risk_table["Base Deterministic Risk"].iloc[0]
        ci_str = risk_table["90% Confidence Interval"].iloc[0]
        m1, m2, m3 = st.columns(3)
        m1.metric("Base Deterministic Risk", base_str)
        m2.metric("Simulated Quantum Mean", f"{simulated_mean_val}%", delta="est.")
        m3.metric("90% Confidence Interval", ci_str)

        col1, col2 = st.columns([1, 1.2], gap="large")

        with col1:
            st.markdown("**Risk Distribution**")
            st.plotly_chart(risk_plot, use_container_width=True)

        with col2:
            st.markdown("**AI-Generated Clinical Summary**")
            st.write(ai_summary)

        # --- PDF DOWNLOAD ---
        st.markdown("---")
        st.subheader("📄 Export Report")
        pdf_bytes = pdf_builder.generate_pdf(patient_data, risk_table, ai_summary)
        st.download_button(
            label="⬇️ Download Complete PDF Report",
            data=pdf_bytes,
            file_name=f"Risk_Report_{patient_data.get('Name', 'Patient')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

        st.markdown(
            '<div class="footer-note">This tool provides an educational risk estimate and does '
            'not replace professional genetic counseling or clinical diagnosis.</div>',
            unsafe_allow_html=True,
        )
