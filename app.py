# =============================
# File: app.py
# =============================

import streamlit as st
import pandas as pd
from config import DEVELOPMENT_MODE
# --- EDIT: Import the new function ---
from data_engine import load_and_process_data, generate_csv_template, generate_task_guide
from analytics_engine import compute_analytics, analyze_comment_themes
from ui_components import (
    render_strategic_overview,
    render_affinity_status,
    render_team_profiles,
    render_skill_analysis,
    render_action_workbench,
    login_page
)
from typing import Dict, Any

# Page configuration
st.set_page_config(
    page_title="Team Skills Hub v3.1",
    layout="wide",
    initial_sidebar_state="expanded"
)

def upload_landing_page():
    """
    Renders the file upload screen. This page is shown after login
    but before data is loaded.
    """
    st.title("🚀 Welcome to the Team Skills Hub")
    st.markdown("Follow the steps to analyze your team's skills.")

    tasks_json_path = "tasks.json"

    # --- Container for Downloads ---
    with st.container(border=True):
        st.subheader("Step 1: Get Resources (Optional)")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Download Template**")
            st.caption("If you don't have a file ready, download the template to fill in your data. It includes the required columns and format.")
            try:
                template_csv = generate_csv_template(tasks_json_path)
                st.download_button(
                    label="📥 Download CSV Template",
                    data=template_csv,
                    file_name="skills_template.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Could not generate template: {e}")
                st.info("Ensure the `tasks.json` file is present.")
        
        # --- EDIT: Add Task Guide Download ---
        with col2:
            st.markdown("**Download Task Guide**")
            st.caption("Download a list of all tasks (skills) included in the assessment.")
            try:
                task_guide_content = generate_task_guide(tasks_json_path)
                st.download_button(
                    label="📄 Download Task Guide (.txt)",
                    data=task_guide_content,
                    file_name="task_guide.txt",
                    mime="text/plain", # Use text/plain for simple list
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Could not generate task guide: {e}")
                st.info("Ensure the `tasks.json` file is present.")


    with st.container(border=True):
        st.subheader("Step 2: Upload Your Data File")
        
        uploaded_csv = st.file_uploader(
            "Upload your `userData.csv` file (or the one filled using the template)", 
            type="csv",
            label_visibility="collapsed"
        )

    # --- AUTO-SUBMIT LOGIC ---
    if uploaded_csv is not None:
        if 'processed_data' not in st.session_state: 
            with st.spinner(f"Processing '{uploaded_csv.name}'... This might take a moment."):
                data = load_and_process_data(uploaded_csv, tasks_json_path)
            
            if data is not None and not data['merged_df'].empty:
                st.session_state.processed_data = data
                st.session_state.data_loaded = True
                st.success("Data loaded successfully! 🎉")
                st.rerun()
            elif data is not None and data['merged_df'].empty:
                st.error("Processing complete, but no valid skill data was found in the file. Please check your file and upload again.")
                st.session_state.data_loaded = False
            else:
                st.error("There was an error processing your file. Please check the format and column names.")
                st.session_state.data_loaded = False
                if 'processed_data' in st.session_state:
                    del st.session_state.processed_data
        
        elif st.session_state.data_loaded:
            st.rerun()


def main_app():
    """Renders the main application interface."""
    
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
    
    all_comments = user_df['Comments'].dropna().str.strip()
    all_comments = all_comments[all_comments != '']
    if not all_comments.empty:
        analytics['comment_themes'] = analyze_comment_themes(all_comments)
    else:
        analytics['comment_themes'] = pd.DataFrame(columns=['Mentions'])
    
    # --- UI Rendering ---
    st.title("🚀 Team Skills Hub v3.1")

    tabs = st.tabs([
        "📈 Strategic Overview",
        "⭐ Affinity Status",
        "👤 Team Profiles",
        "🧠 Skill Analysis",
        "🔭 Action Workbench",
    ])

    with tabs[0]:
        render_strategic_overview(df_merged, user_df, analytics, total_participants_in_file, score_parsing_errors)
    with tabs[1]:
        render_affinity_status(user_df, analytics)
    with tabs[2]:
        render_team_profiles(df_merged, user_df, analytics)
    with tabs[3]:
        render_skill_analysis(df_merged, analytics)
    with tabs[4]:
        render_action_workbench(df_merged, analytics)


# --- Main execution (State Machine) ---
if __name__ == "__main__":
    
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        
    if DEVELOPMENT_MODE:
        st.session_state.logged_in = True 

    if not st.session_state.logged_in:
        login_page()
    elif not st.session_state.data_loaded:
        upload_landing_page()
    else:
        main_app()