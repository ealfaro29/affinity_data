# =============================
# File: app.py
# =============================

import streamlit as st
import pandas as pd
from config import DEVELOPMENT_MODE
from data_engine import load_and_process_data
from analytics_engine import compute_analytics, analyze_comment_themes
from ui_components import (
    render_strategic_dashboard,
    render_talent_and_staffing,
    render_development_and_growth,
    render_skill_intelligence,
    render_operational_health,
    login_page
)

st.set_page_config(
    page_title="Team Skills Hub v1.5 (Hybrid)",
    layout="wide",
    initial_sidebar_state="expanded"
)


def main_app():
    st.sidebar.title("🚀 Team Skills Hub")
    st.sidebar.info("A hybrid dashboard combining strategic overviews with actionable insights for talent management.")

    # Fixed filenames by design
    data = load_and_process_data("userData.csv", "tasks.json")
    if data is None:
        st.error("Dashboard cannot be loaded. Check data files.")
        st.stop()

    df_merged = data['merged_df']
    user_df = data['user_df']
    total_participants_in_file = data['total_count']

    if df_merged.empty:
        st.warning("No participants with valid assessment scores were found.")
        st.stop()

    # --- Controller Logic: Prepare all analytics before rendering ---
    analytics = compute_analytics(df_merged, user_df)
    
    all_comments = user_df['Comments'].dropna().str.strip()
    all_comments = all_comments[all_comments != '']
    analytics['comment_themes'] = analyze_comment_themes(all_comments) if not all_comments.empty else pd.DataFrame(columns=['Mentions'])

    # --- UI Rendering ---
    st.title("🚀 Team Skills Hub v1.5 (Hybrid)")

    tabs = st.tabs([
        "📈 Strategic Dashboard",
        "👤 Talent & Staffing",
        "🌱 Development & Growth",
        "🧠 Skill Intelligence",
        "🔧 Operational Health",
    ])

    with tabs[0]:
        render_strategic_dashboard(df_merged, user_df, analytics, total_participants_in_file)
    with tabs[1]:
        render_talent_and_staffing(df_merged, user_df, analytics)
    with tabs[2]:
        render_development_and_growth(df_merged, analytics)
    with tabs[3]:
        render_skill_intelligence(df_merged, analytics)
    with tabs[4]:
        render_operational_health(user_df, analytics)


if DEVELOPMENT_MODE:
    main_app()
else:
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if st.session_state.logged_in:
        main_app()
    else:
        login_page()