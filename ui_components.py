# =============================
# File: ui_components.py
# =============================

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime


# ==============================================================================
# TAB 1: STRATEGIC DASHBOARD
# ==============================================================================
def render_strategic_dashboard(df_merged, user_df, analytics, total_participants_in_file):
    st.header("📈 Strategic Dashboard")
    st.info("Your command center for team skills. Get a high-level overview of vital signs and critical risks.")

    person_summary = analytics.get('person_summary', pd.DataFrame())
    task_summary = analytics.get('task_summary', pd.DataFrame())

    col1, col2 = st.columns(2, gap="large")
    with col1:
        with st.container(border=True):
            st.subheader("📊 Team Vital Signs")
            kpi1, kpi2, kpi3 = st.columns(3)
            active_participants_count = df_merged['Name'].nunique()
            kpi1.metric("People in File", total_participants_in_file)
            kpi2.metric("Active Participants", active_participants_count, f"{active_participants_count / total_participants_in_file:.0%} Response Rate")
            kpi3.metric("Average Confidence", f"{df_merged['Score'].mean():.1%}")

            st.markdown("**Talent Archetype Distribution**")
            archetype_counts = person_summary['Archetype'].value_counts()
            if not archetype_counts.empty:
                fig_pie = px.pie(archetype_counts, values=archetype_counts.values, names=archetype_counts.index, hole=0.5)
                fig_pie.update_layout(height=300, margin=dict(t=30, b=20, l=0, r=0), legend_orientation="h")
                st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        with st.container(border=True):
            st.subheader("🚨 Top Skill Risks")
            st.caption("Tasks with the highest risk (few experts, many beginners).")
            risk_radar = task_summary.sort_values(by='Risk Index', ascending=False)
            if not risk_radar.empty:
                for _, row in risk_radar.head(5).iterrows():
                    st.metric(label=row.name, value=f"{row['Avg_Score']:.1%} Avg. Confidence", delta=f"Risk Index: {row['Risk Index']:.2f}", delta_color="inverse")
            else:
                st.info("No risk data available.")
    
    with st.expander("🩺 View Data Health & Pending Assessments"):
        assessed_names = set(df_merged['Name'].unique())
        all_user_names = set(user_df['Name'].unique())
        pending_assessment_names = all_user_names - assessed_names
        st.metric("Self-Assessment Response", f"{len(assessed_names)} / {len(all_user_names)}", f"{len(pending_assessment_names)} pending")
        if pending_assessment_names:
            st.dataframe(user_df[user_df['Name'].isin(pending_assessment_names)][['Name', 'Team Leader']], hide_index=True)


# ==============================================================================
# TAB 2: TALENT & STAFFING
# ==============================================================================
def render_talent_and_staffing(df_merged, user_df, analytics):
    st.header("👤 Talent & Staffing")
    st.info("Explore individual profiles, align roles using archetypes, and staff projects with the Gap Radar.")

    sub_tabs = st.tabs(["📇 Team Profiles", "🎭 Archetype Roster", "🎯 Gap Radar"])

    with sub_tabs[0]:
        _render_team_profiles_view(df_merged, user_df, analytics)
    with sub_tabs[1]:
        _render_archetypes_view(analytics)
    with sub_tabs[2]:
        _render_gap_radar_view(analytics)

def _render_team_profiles_view(df_merged, user_df, analytics):
    st.subheader("Individual Skill Profiles")
    person_summary = analytics.get('person_summary', pd.DataFrame())
    
    col1, col2 = st.columns([1, 2], gap="large")
    with col1:
        all_user_names_list = sorted(user_df['Name'].unique())
        selected_person = st.selectbox("Select a Team Member", all_user_names_list)

    with col2:
        with st.container(border=True):
            st.header(f"Profile: {selected_person}")
            if selected_person not in set(df_merged['Name'].unique()):
                st.warning(f"**{selected_person} has not completed the self-assessment.**")
            else:
                person_stats = person_summary.loc[selected_person]
                person_data = df_merged[df_merged['Name'] == selected_person].copy()
                st.metric("Archetype", person_stats['Archetype'])
                
                st.markdown("**Strengths & Development Areas**")
                person_skills = person_data.sort_values('Score', ascending=False).drop_duplicates(subset=['Task_Prefixed'])
                sc1, sc2 = st.columns(2)
                with sc1:
                    st.markdown("✅ **Top 5 Skills**")
                    st.dataframe(person_skills.head(5)[['Task_Prefixed', 'Score']], hide_index=True,
                                 column_config={"Score": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1)})
                with sc2:
                    st.markdown("🌱 **Top 5 Improvement Areas**")
                    st.dataframe(person_skills.tail(5)[['Task_Prefixed', 'Score']], hide_index=True,
                                 column_config={"Score": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1)})

def _render_archetypes_view(analytics):
    st.subheader("Role Alignment Roster")
    st.caption("Filter the roster to find the right people for your project roles.")
    person_summary = analytics.get('person_summary', pd.DataFrame())
    
    all_archetypes = ['All'] + sorted(person_summary['Archetype'].unique())
    selected_archetype = st.selectbox("Filter by Archetype:", options=all_archetypes)

    roster_df = person_summary if selected_archetype == 'All' else person_summary[person_summary['Archetype'] == selected_archetype]

    st.dataframe(
        roster_df.reset_index()[['Name', 'Archetype', 'Avg Score', 'Team Leader']],
        height=500, use_container_width=True, hide_index=True,
        column_config={"Avg Score": st.column_config.ProgressColumn("Avg Confidence", min_value=0, max_value=1)}
    )

def _render_gap_radar_view(analytics):
    st.subheader("Project Skill Gap Analysis")
    st.caption("**Decision:** Who to staff? Which skills require urgent training to meet demand?")
    task_summary = analytics.get('task_summary', pd.DataFrame())
    
    required_skills = st.multiselect("Select skills needed for a project:", options=sorted(task_summary.index.unique()))

    if required_skills:
        project_readiness = task_summary.loc[required_skills].copy()
        def get_status(score):
            if score > 0.75: return "✅ Covered"
            elif score > 0.5: return "⚠️ At Risk"
            else: return "❌ Critical Gap"
        project_readiness['Status'] = project_readiness['Avg_Score'].apply(get_status)
        st.dataframe(
            project_readiness[['Avg_Score', 'Expert_Count', 'Status']],
            column_config={"Avg_Score": st.column_config.ProgressColumn("Team Avg Confidence", format="%.1f%%", min_value=0, max_value=1)},
            use_container_width=True
        )

# ==============================================================================
# TAB 3: DEVELOPMENT & GROWTH
# ==============================================================================
def render_development_and_growth(df_merged, analytics):
    st.header("🌱 Development & Growth")
    st.info("Accelerate team growth with the Mentor Engine and discover strategic opportunities.")

    sub_tabs = st.tabs(["🤝 Mentor Engine", "💡 Opportunity Lens", "📈 Growth Trajectory (Future)"])

    with sub_tabs[0]:
        _render_mentor_engine_view(df_merged, analytics)
    with sub_tabs[1]:
        _render_opportunity_lens_view(analytics)
    with sub_tabs[2]:
        st.warning("📈 **Feature in Development:** This module requires historical data snapshots to track skill progress over time.")
        st.markdown("**To enable this, please save a version of `userData.csv` periodically (e.g., `userData_YYYY-MM.csv`).**")

def _render_mentor_engine_view(df_merged, analytics):
    st.subheader("Build Training Groups & Find Mentors")
    person_summary = analytics.get('person_summary', pd.DataFrame())
    
    with st.expander("👥 Custom Training Group Builder", expanded=True):
        all_tasks = sorted(df_merged['Task_Prefixed'].unique())
        selected_task = st.selectbox("Select a skill for the training session:", all_tasks)
        if st.button("Generate Groups", key="gen_groups"):
            filtered_df = df_merged[df_merged['Task_Prefixed'] == selected_task]
            group_scores = filtered_df.groupby('Name')['Score'].mean().sort_values()
            mentors = group_scores[group_scores >= 0.8].sort_values(ascending=False)
            learners = group_scores[group_scores < 0.8]
            st.success(f"Found {len(mentors)} potential mentors and {len(learners)} learners for this skill.")
    
    with st.expander("🤝 Mentor Matchmaker", expanded=True):
        learners_list = sorted(person_summary[person_summary['Archetype'].isin(["🌱 Consistent Learner", "🎯 Needs Support"])].index.tolist())
        all_tasks = sorted(df_merged['Task_Prefixed'].unique())
        c1, c2 = st.columns(2)
        selected_learner = c1.selectbox("Select a Learner", options=learners_list)
        skill_needed = c2.selectbox("Select a Skill Needed", options=all_tasks)
        if st.button("Find Mentor", use_container_width=True, type="primary"):
            experts_df = df_merged[(df_merged['Task_Prefixed'] == skill_needed) & (df_merged['Name'] != selected_learner) & (df_merged['Score'] >= 0.8)]
            if not experts_df.empty:
                st.success(f"Top Mentor Recommendations for **{selected_learner}**")
                recs = experts_df.sort_values(by="Score", ascending=False).head(3)
                st.dataframe(recs[['Name', 'Score']], hide_index=True, use_container_width=True)
            else:
                st.error("No suitable mentors found for this skill.")

def _render_opportunity_lens_view(analytics):
    st.subheader("Strategic Skill Radar")
    st.caption("**Decision:** Where can we expand our services based on latent team strengths?")
    opportunity_df = analytics.get('opportunity_lens', pd.DataFrame())
    if opportunity_df.empty:
        st.info("No significant team strengths found (Avg. Confidence < 75%).")
    else:
        st.dataframe(opportunity_df.sort_values('Competency_Score', ascending=False),
            column_config={"Avg_Score": st.column_config.ProgressColumn("Avg Confidence", format="%.1f%%", min_value=0, max_value=1)},
            use_container_width=True
        )

# ==============================================================================
# TAB 4: SKILL INTELLIGENCE
# ==============================================================================
def render_skill_intelligence(df_merged, analytics):
    st.header("🧠 Skill Intelligence")
    st.info("Perform deep dives into specific skills, analyze distributions, and understand skill relationships.")
    
    sub_tabs = st.tabs(["📊 Skill Deep Dive", "🚨 Skill Risk Matrix", "🕸️ Skill Correlation"])
    
    with sub_tabs[0]:
        options = sorted(df_merged['Task_Prefixed'].unique())
        selected = st.selectbox("Select a Task to Analyze", options)
        if selected:
            skill_data = df_merged[df_merged['Task_Prefixed'] == selected]
            c1, c2 = st.columns(2)
            c1.metric("Avg Confidence", f"{skill_data['Score'].mean():.1%}")
            c2.metric("Experts (≥80%)", skill_data[skill_data['Score'] >= 0.8]['Name'].nunique())
            st.markdown("**Score Distribution**")
            fig = px.histogram(skill_data, x='Score', nbins=10)
            st.plotly_chart(fig, use_container_width=True)
    
    with sub_tabs[1]:
        st.subheader("Full Talent Risk Matrix")
        risk_matrix = analytics.get('task_summary', pd.DataFrame())
        if not risk_matrix.empty:
            def highlight_risks(row):
                styles = [''] * len(row)
                if row['SPOF']: styles[row.index.get_loc('SPOF')] = 'background-color: orange'
                if row['Expiration Risk']: styles[row.index.get_loc('Expiration Risk')] = 'background-color: red; color: white'
                return styles
            risk_df_display = risk_matrix.reset_index()[['Task_Prefixed', 'Avg_Score', 'Expert_Count', 'SPOF', 'Expiration Risk']]
            st.dataframe(risk_df_display.style.apply(highlight_risks, axis=1).format({'Avg_Score': "{:.1%}"}), use_container_width=True)
            st.caption("🟧 Orange: Single Point of Failure (SPOF). 🔴 Red: Key expert license expires soon.")

    with sub_tabs[2]:
        st.subheader("Skill Correlation Heatmap")
        skill_corr_matrix = analytics.get('skill_correlation', pd.DataFrame())
        if not skill_corr_matrix.empty:
            fig = px.imshow(skill_corr_matrix, text_auto=".2f", aspect="auto", height=600)
            st.plotly_chart(fig, use_container_width=True)

# ==============================================================================
# TAB 5: OPERATIONAL HEALTH
# ==============================================================================
def render_operational_health(user_df, analytics):
    st.header("🔧 Operational Health")
    st.info("Manage software licenses, training status, and analyze qualitative team feedback.")

    st.subheader("📊 Affinity Software & Training Status")
    total_users = len(user_df)
    k1, k2 = st.columns(2)
    k1.metric("Active Affinity Licenses", f"{user_df['Active License'].sum()}", f"{user_df['Active License'].sum()/total_users:.0%} of team")
    k2.metric("Received McK Training", f"{user_df['Has received Affinity training of McK?'].sum()}", f"{user_df['Has received Affinity training of McK?'].sum()/total_users:.0%} of team")

    st.subheader("🚨 License Expiration Timeline")
    exp_df = user_df[user_df['License Expiration'].notna()].copy()
    if not exp_df.empty:
        exp_df['Days Left'] = (exp_df['License Expiration'] - pd.to_datetime('today')).dt.days
        exp_df_upcoming = exp_df[(exp_df['Days Left'] > 0) & (exp_df['Days Left'] <= 180)].sort_values('Days Left')
        if not exp_df_upcoming.empty:
            st.dataframe(exp_df_upcoming[['Name', 'License Expiration', 'Days Left']], use_container_width=True, hide_index=True)
        else:
            st.success("✅ No licenses expiring in the next 6 months.")
    
    st.subheader("🗣️ Team Feedback Analysis")
    theme_counts = analytics.get('comment_themes', pd.DataFrame())
    if not theme_counts.empty:
        fig = px.bar(theme_counts, x='Mentions', y=theme_counts.index, orientation='h', text_auto=True, title="Common Themes in Comments")
        st.plotly_chart(fig, use_container_width=True)
        with st.expander("View Raw Comments"):
            st.dataframe(user_df[['Name', 'Comments']].dropna().drop_duplicates(), hide_index=True)

# ==============================================================================
# LOGIN PAGE
# ==============================================================================
def login_page():
    st.title("🔐 Team Skills Hub Login")
    with st.form("login_form"):
        username = st.text_input("Username").lower()
        password = st.text_input("PIN", type="password")
        if st.form_submit_button("Log In"):
            try:
                correct_username = st.secrets["credentials"]["username"]
                correct_password = st.secrets["credentials"]["password"]
                if username == correct_username and password == correct_password:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Incorrect username or PIN.")
            except (KeyError, FileNotFoundError):
                 st.error("Secrets not configured for deployment. Contact administrator.")