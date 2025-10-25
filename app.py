# =============================
# File: app.py
# =============================

import streamlit as st
import pandas as pd
from config import DEVELOPMENT_MODE
from data_engine import load_and_process_data
from analytics_engine import compute_analytics, analyze_comment_themes
from ui_components import (
    render_strategic_overview,
    render_affinity_status,
    render_action_playbook,
    render_team_profiles,
    render_skill_analysis,
    render_team_dna,
    render_risk_opportunity,
    login_page
)

st.set_page_config(
    page_title="Team Skills Hub v2.32",
    layout="wide",
    initial_sidebar_state="expanded"
)


def main_app():
    st.sidebar.title("🚀 Team Skills Hub")
    st.sidebar.info("A strategic platform for talent intelligence and team development.")

    # Fixed filenames by design
    data = load_and_process_data("userData.csv", "tasks.json")
    if data is None:
        st.error("Dashboard cannot be loaded. Check data files.")
        st.stop()

    df_merged = data['merged_df']
    user_df = data['user_df']
    total_participants_in_file = data['total_count']
    score_parsing_errors = data['parsing_errors']

    if df_merged.empty:
        st.warning("No participants with valid scores were found.")
        st.stop()

    # --- Controller Logic: Prepare all analytics before rendering ---
    analytics = compute_analytics(df_merged, user_df)
    
    all_comments = user_df['Comments'].dropna().str.strip()
    all_comments = all_comments[all_comments != '']
    analytics['comment_themes'] = analyze_comment_themes(all_comments) if not all_comments.empty else pd.DataFrame(columns=['Mentions'])
    
    # --- UI Rendering ---
    st.title("🚀 Team Skills & Affinity Hub v2.0 (Restored & Enhanced)")

    tabs = st.tabs([
        "📈 Strategic Overview",
        "⭐ Affinity Status",
        "🗺️ Action Playbook",
        "👤 Team Profiles",
        "🧠 Skill Analysis",
        "🧬 Team DNA & Dynamics",
        "🔭 Risk & Opportunity Forecaster",
    ])

    with tabs[0]:
        render_strategic_overview(df_merged, user_df, analytics, total_participants_in_file, score_parsing_errors)
    with tabs[1]:
        render_affinity_status(user_df, analytics) # Pass analytics for comments
    with tabs[2]:
        render_action_playbook(df_merged, analytics) # Enhanced
    with tabs[3]:
        render_team_profiles(df_merged, user_df, analytics)
    with tabs[4]:
        render_skill_analysis(df_merged, analytics)
    with tabs[5]:
        render_team_dna(df_merged, analytics)
    with tabs[6]:
        render_risk_opportunity(analytics) # Enhanced


if DEVELOPMENT_MODE:
    main_app()
else:
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if st.session_state.logged_in:
        main_app()
    else:
        login_page()