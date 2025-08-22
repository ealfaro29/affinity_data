# =============================
# File: app.py
# =============================

import streamlit as st
from pathlib import Path
from config import DEVELOPMENT_MODE
from data_engine import load_and_process_data
from analytics_engine import compute_analytics
from ui_components import (
    render_gap_radar,
    render_opportunity_lens,
    render_mentor_engine,
    render_archetypes_and_roles,
    render_growth_trajectory_placeholder,
    render_team_resources_and_health,
    login_page
)

st.set_page_config(
    page_title="Team Skills Decision Hub v1.0",
    layout="wide",
    initial_sidebar_state="expanded"
)


def main_app():
    st.sidebar.title("🚀 Team Skills Decision Hub")
    st.sidebar.info("A strategic platform for talent intelligence and team development, refactored for action.")

    # Fixed filenames by design
    data = load_and_process_data("userData.csv", "tasks.json")
    if data is None:
        st.error("Dashboard cannot be loaded. Check data files.")
        st.stop()

    df_merged = data['merged_df']
    user_df = data['user_df']

    if df_merged.empty:
        st.warning("No participants with valid assessment scores were found.")
        st.stop()

    analytics = compute_analytics(df_merged, user_df)

    st.title("🚀 Team Skills Decision Hub v1.0")
    st.markdown("From data art to a decision engine. Each module is designed to answer a key management question.")

    tabs = st.tabs([
        "🎯 Gap Radar (Staffing)",
        "💡 Opportunity Lens (Strategy)",
        "🤝 Mentor–Mentee Engine (Development)",
        "🎭 Archetypes & Roles (Team Design)",
        "📈 Growth Trajectory (Performance)",
        "🔧 Team Resources (Operations)"
    ])

    with tabs[0]:
        render_gap_radar(analytics)
    with tabs[1]:
        render_opportunity_lens(analytics)
    with tabs[2]:
        render_mentor_engine(df_merged, analytics)
    with tabs[3]:
        render_archetypes_and_roles(df_merged, user_df, analytics)
    with tabs[4]:
        render_growth_trajectory_placeholder()
    with tabs[5]:
        render_team_resources_and_health(user_df)


if DEVELOPMENT_MODE:
    main_app()
else:
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if st.session_state.logged_in:
        main_app()
    else:
        login_page()