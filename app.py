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
from typing import Dict, Any

# Page configuration
st.set_page_config(
    page_title="Team Skills Hub v2.32",
    layout="wide",
    initial_sidebar_state="expanded"
)

def upload_landing_page():
    """
    Renders the file upload screen. This page is shown after login
    but before data is loaded.
    """
    st.title("🚀 Welcome to the Team Skills Hub")
    st.subheader("Please upload your data to begin")

    # We assume tasks.json is a local file that defines the skills.
    # The user only needs to upload their own team's CSV data.
    tasks_json_path = "tasks.json" 

    uploaded_csv = st.file_uploader("Upload your User Data CSV file", type="csv")

    if uploaded_csv is not None:
        st.info(f"File '{uploaded_csv.name}' uploaded. Click below to analyze.")
        
        if st.button("Load and Analyze Data", type="primary", use_container_width=True):
            with st.spinner("Processing your data... This may take a moment."):
                # Pass the uploaded file object directly to the data engine
                data = load_and_process_data(uploaded_csv, tasks_json_path)
            
            if data is not None:
                # Store the processed data in session state
                st.session_state.processed_data = data
                st.session_state.data_loaded = True
                st.success("Data loaded successfully! 🎉")
                st.rerun() # Rerun to trigger main_app()
            else:
                # If data processing failed
                st.error("There was an error processing your file. Please check the file format.")
                st.session_state.data_loaded = False
                if 'processed_data' in st.session_state:
                    del st.session_state.processed_data

def main_app():
    """Renders the main application interface."""
    
    # --- Load data from session state ---
    if 'processed_data' not in st.session_state:
        st.error("Data not found. Please upload again.")
        st.session_state.data_loaded = False
        st.rerun()
        return

    data = st.session_state.processed_data
    
    # --- Sidebar ---
    st.sidebar.title("🚀 Team Skills Hub")
    st.sidebar.info("A strategic platform for talent intelligence and team development.")
    
    if st.sidebar.button("Upload New Data"):
        # Clear session state to return to upload screen
        st.session_state.data_loaded = False
        if 'processed_data' in st.session_state:
            del st.session_state.processed_data
        st.rerun()

    # --- Extract data ---
    df_merged: pd.DataFrame = data['merged_df']
    user_df: pd.DataFrame = data['user_df']
    total_participants_in_file: int = data['total_count']
    score_parsing_errors: int = data['parsing_errors']

    if df_merged.empty:
        st.warning("No participants with valid scores were found in the uploaded file.")
        st.stop()

    # --- Analytics Engine ---
    analytics: Dict[str, Any] = compute_analytics(df_merged, user_df)
    
    # Analyze comment themes
    all_comments = user_df['Comments'].dropna().str.strip()
    all_comments = all_comments[all_comments != '']
    if not all_comments.empty:
        analytics['comment_themes'] = analyze_comment_themes(all_comments)
    else:
        analytics['comment_themes'] = pd.DataFrame(columns=['Mentions'])
    
    # --- UI Rendering ---
    st.title("🚀 Team Skills & Affinity Hub v2.32")

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
        render_action_playbook(df_merged, analytics)
    with tabs[3]:
        render_team_profiles(df_merged, user_df, analytics)
    with tabs[4]:
        render_skill_analysis(df_merged, analytics)
    with tabs[5]:
        render_team_dna(df_merged, analytics)
    with tabs[6]:
        render_risk_opportunity(analytics)


# --- Main execution (State Machine) ---
if __name__ == "__main__":
    
    # Initialize session state keys
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        
    if DEVELOPMENT_MODE:
        st.session_state.logged_in = True # Bypass login in dev mode

    # Control flow:
    # 1. Check Login
    # 2. Check Data
    # 3. Run App
    
    if not st.session_state.logged_in:
        login_page()
    elif not st.session_state.data_loaded:
        upload_landing_page()
    else:
        main_app()