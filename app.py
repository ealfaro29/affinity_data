# =============================
# File: app.py
# =============================

import streamlit as st
import pandas as pd
from pathlib import Path # <-- Import Path
from data_engine import load_and_process_data, generate_csv_template, generate_task_guide
from analytics_engine import compute_analytics, analyze_comment_themes
# --- EDIT: Removed HOW_TO_USE_GUIDE import ---
from ui_components import (
    render_strategic_overview,
    render_affinity_status,
    render_team_profiles,
    render_skill_analysis,
    render_action_workbench
)
from typing import Dict, Any

# Page configuration
st.set_page_config(
    page_title="Affinity Skills Hub",
    layout="wide"
)

# --- EDIT: Function to read the guide file ---
@st.cache_data # Cache the guide content
def load_guide_content(filepath="guide.md") -> str:
    """Reads the content of the markdown guide file."""
    try:
        return Path(filepath).read_text(encoding="utf-8")
    except FileNotFoundError:
        return "Error: guide.md not found. Please ensure the guide file exists."
    except Exception as e:
        return f"Error reading guide file: {e}"

def upload_landing_page():
    """
    Renders the file upload screen AND the How-to Use guide from a file.
    """
    st.title("🚀 Welcome to the Team Skills Hub")
    st.markdown("Follow the steps to analyze your team's skills, or read the guide below for detailed instructions.")

    tasks_json_path = "tasks.json"

    col_upload, col_resources = st.columns([2,1], gap="large")

    with col_upload:
        with st.container(border=True):
            st.subheader("Step 1: Upload Your Data File") # Renumbered step
            st.markdown("Upload your completed `userData.csv` file here to begin the analysis.")

            uploaded_csv = st.file_uploader(
                "Upload your `userData.csv` file (or the one filled using the template)",
                type="csv",
                label_visibility="collapsed"
            )

    with col_resources:
        with st.container(border=True):
            st.subheader("Get Resources") # Removed step number
            st.markdown("Download templates and guides to help prepare your data.")

            try:
                template_csv = generate_csv_template(tasks_json_path)
                st.download_button(
                    label="📥 Download CSV Template",
                    data=template_csv,
                    file_name="skills_template.csv",
                    mime="text/csv",
                    use_container_width=True,
                    help="Includes all 'Task X' columns and required fields."
                )
            except Exception as e:
                st.error(f"Could not generate CSV template: {e}")

            try:
                task_guide_content = generate_task_guide(tasks_json_path)
                st.download_button(
                    label="📄 Download Task Guide",
                    data=task_guide_content,
                    file_name="task_guide.txt",
                    mime="text/plain",
                    use_container_width=True,
                    help="Provides a list of all skills/tasks for reference."
                )
            except Exception as e:
                st.error(f"Could not generate task guide: {e}")

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

    st.markdown("---")

    # --- EDIT: Load and display guide from file ---
    st.header("📖 How to Use the Team Skills Hub")
    guide_content = load_guide_content() # Load content using the cached function
    with st.expander("Click here to read the full guide", expanded=False):
        st.markdown(guide_content, unsafe_allow_html=True)


def main_app():
    """Renders the main application interface (dashboard)."""

    if 'processed_data' not in st.session_state:
        st.error("Data not found. Please upload again.")
        st.session_state.data_loaded = False
        st.rerun()
        return

    data = st.session_state.processed_data

    # --- Extract data ---
    df_merged: pd.DataFrame = data['merged_df']
    user_df: pd.DataFrame = data['user_df']
    total_participants_in_file: int = data['total_count']
    score_parsing_errors: int = data['parsing_errors']

    # Refresh button
    # --- EDIT: Added key for stability ---
    st.button("🔄 Upload New Data", key="refresh_button", on_click=lambda: st.session_state.clear(), help="Clear current data and return to upload screen.")


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
    st.title("🚀 Affinity Tracker")

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

    # Simplified state check (No login)
    if not st.session_state.data_loaded:
        upload_landing_page()
    else:
        main_app()