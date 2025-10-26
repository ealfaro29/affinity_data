# =============================
# File: app.py
# =============================

import streamlit as st
import pandas as pd
from config import * # Import constants directly if needed, or keep as config.
from data_engine import load_and_process_data, generate_csv_template, generate_task_guide
from analytics_engine import compute_analytics, analyze_comment_themes
from ui_components import (
    render_strategic_overview,
    render_affinity_status,
    render_team_profiles,
    render_skill_analysis,
    render_action_workbench
)
from typing import Dict, Any
from streamlit_modal import Modal # <-- IMPORT MODAL LIBRARY

# Page configuration
st.set_page_config(
    page_title="Team Skills Hub v3.2",
    layout="wide"
)

# --- EDIT: Define the How-to Use Guide Text ---
HOW_TO_USE_GUIDE = """
## 📖 Team Skills Hub v3.2: How-to Use Guide

### Introduction

Welcome to the **Team Skills Hub**, your central platform for understanding and developing your team's technical skills. This tool allows you to visualize self-assessed competencies, identify risks, find improvement opportunities, and plan development actions.

---

### Getting Started: Uploading Your Data

When you open the application, you'll see the welcome screen.

1.  **(Optional) Download Resources:**
    * **CSV Data Template:** If it's your first time or your data isn't ready, download this template. It contains all necessary columns (`BPS`, `Team Leader`, `Task 1`, `Task 2`, etc.) and an example row to guide you. Fill this template with your team's information.
    * **Task Reference Guide:** Download a simple plain text list with the ID and name of each task (skill) assessed. Useful for understanding what each `Task X` refers to when filling out the template.
2.  **Upload Data File:**
    * Drag and drop your CSV file (either the one filled using the template or one you already have in that format) into the designated area, or click to browse for it on your computer.
    * The application will automatically process the file. If everything is correct, it will take you to the main dashboard. If there are errors (e.g., incorrect format, missing columns), it will display a message asking you to review your file.

---

### 📈 Tab: Strategic Overview

This tab gives you a high-level view of the team's health and risks.

* **📊 Team Vital Signs:** KPIs showing total people, active participants (% response rate), and the overall average confidence score.
* **🩺 Data Health Check:** Shows assessment response rate, data quality issues (parsing errors), and lists pending participants.
* **🚨 Skill Risk Radar:** Lists the top 5 skills with the highest risk (many beginners, few experts) and visualizes the Risk Index vs. Expert/Beginner counts.
* **🗣️ Top Comment Themes:** Bar chart of the most frequent topics mentioned in user feedback.

---

### ⭐ Tab: Affinity Status

Focuses on Affinity software management and team feedback.

* **📊 Overall Software Status:** Metrics on active licenses and completion of McK training.
* **🚨 License Expiration Timeline:** Visual timeline of upcoming license expirations, color-coded by urgency.
* **🗣️ All Team Feedback:** A table displaying all raw comments provided by users.

---

### 👤 Tab: Team Profiles

Explore individual skill profiles.

* **📇 Team Roster (Left Column):** Select a team member from this ranked list (includes Rank, Avg Score, Archetype, Assessed status).
* **📇 Profile: [Selected Person] (Right Column):**
    * **Metrics:** Shows the selected person's Rank, Avg Score, and calculated Archetype (Versatile Leader, Niche Specialist, Consistent Learner, Needs Support).
    * **Radar Chart:** Compares the individual's confidence *by category* against the team average.
    * **Strengths & Development Areas:** Bar charts showing the person's Top 5 skills and Top 5 areas for improvement.

---

### 🧠 Tab: Skill Analysis

Deep dive into team performance on specific skills or categories.

* **Deep Dive:** Filter data by `Category` or specific `Task`.
* **Metrics:** Shows Avg Confidence, number of Experts (>=80%), and number of Beginners (<40%) *for the selected filter*.
* **Skill Leaderboard:** Ranks individuals based on their average confidence *in the selected skills/categories*.
* **Score Distribution:** Histogram showing the spread of scores for the selection, with a line indicating the average.

---

### 🔭 Tab: Action Workbench

Tools for making decisions and planning development.

* **Sub-Tab: 🚨 Risk Mitigation:**
    * Select a high-risk skill.
    * View analysis (Avg Confidence, Experts, Beginners for that skill).
    * See the **Talent Pipeline** (potential learners, 60-79% confidence) and available **Mentors** (Experts >=80% confidence, with their Archetype).
* **Sub-Tab: 👥 Group Builder:**
    * Select *any* skill.
    * Configure number of groups and people per group.
    * Optionally assign mentors automatically.
    * Generates balanced training groups (Mentor + Learners).

---

### Conclusion

Use the **Team Skills Hub** regularly to monitor progress, identify critical areas, and plan informed, data-driven development interventions (training, mentoring) to boost your team's capabilities!
"""


def upload_landing_page():
    """
    Renders the file upload screen with a How-to Use modal.
    """
    st.title("🚀 Welcome to the Team Skills Hub")
    st.markdown("Follow the steps to analyze your team's skills.")

    # --- EDIT: Initialize Modal ---
    howto_modal = Modal(
        "How to Use This App",
        key="howto-modal", # Assign a unique key
        # Optional: Set max_width
        # max_width=700
    )

    # --- EDIT: Add Button to Open Modal ---
    if st.button("📖 How to Use This App"):
        howto_modal.open()

    # --- EDIT: Define Modal Content ---
    if howto_modal.is_open():
        with howto_modal.container():
            st.markdown(HOW_TO_USE_GUIDE, unsafe_allow_html=True) # Use markdown for guide text

    tasks_json_path = "tasks.json"

    st.subheader("Step 1: Get Resources (Optional)")
    st.markdown("Download templates and guides to help you prepare your data.")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        with st.container(border=True):
            st.markdown("#### 📥 CSV Data Template")
            st.markdown("Use this pre-formatted CSV file to manually enter your team's skill data. It includes all required columns and an example row.")
            try:
                template_csv = generate_csv_template(tasks_json_path)
                st.download_button(
                    label="Download Template",
                    data=template_csv,
                    file_name="skills_template.csv",
                    mime="text/csv",
                    use_container_width=True,
                    help="Includes all 'Task X' columns and required fields."
                )
            except Exception as e:
                st.error(f"Could not generate CSV template: {e}")
                st.info("Ensure the `tasks.json` file is present.")

    with col2:
        with st.container(border=True):
            st.markdown("#### 📄 Task Reference Guide")
            st.markdown("Download a plain text file listing all the tasks (skills) and their IDs that are part of this assessment.")
            try:
                task_guide_content = generate_task_guide(tasks_json_path)
                st.download_button(
                    label="Download Task Guide",
                    data=task_guide_content,
                    file_name="task_guide.txt",
                    mime="text/plain",
                    use_container_width=True,
                    help="Provides a list of all skills/tasks for reference."
                )
            except Exception as e:
                st.error(f"Could not generate task guide: {e}")
                st.info("Ensure the `tasks.json` file is present.")

    st.markdown("---")

    with st.container(border=True):
        st.subheader("Step 2: Upload Your Data File")
        st.markdown("Upload your completed `userData.csv` file here to begin the analysis.")

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
    st.title("🚀 Team Skills Hub v3.2")

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

    # --- Simplified state check ---
    if not st.session_state.data_loaded:
        upload_landing_page()
    else:
        main_app()