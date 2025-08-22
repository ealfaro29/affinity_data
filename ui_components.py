# =============================
# File: ui_components.py
# =============================

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime


def render_gap_radar(analytics):
    st.header("🎯 Gap Radar: Skill Coverage vs. Project Needs")
    st.info("**Decision:** Who to staff on a project? Which skills require urgent training or hiring to meet demand?")
    
    task_summary = analytics.get('task_summary', pd.DataFrame())
    if task_summary.empty:
        st.warning("No task data available for analysis.")
        return

    all_skills = sorted(task_summary.index.unique())
    
    with st.container(border=True):
        st.subheader("1. Define Project Skill Requirements")
        required_skills = st.multiselect(
            "Select the skills needed for your upcoming project:",
            options=all_skills,
            default=all_skills[:3]
        )

    if not required_skills:
        st.warning("Please select at least one skill to analyze the team's readiness.")
        return
        
    project_readiness = task_summary.loc[required_skills].copy()
    
    def get_status(score):
        if score > 0.75:
            return "✅ Covered"
        elif score > 0.5:
            return "⚠️ At Risk"
        else:
            return "❌ Critical Gap"
            
    project_readiness['Status'] = project_readiness['Avg_Score'].apply(get_status)

    st.subheader("2. Analyze Team Readiness & Take Action")
    col1, col2 = st.columns([2, 1])

    with col1:
        st.dataframe(
            project_readiness[['Avg_Score', 'Expert_Count', 'Beginner_Count', 'Status']],
            column_config={
                "Avg_Score": st.column_config.ProgressColumn("Team Avg Confidence", format="%.1f%%", min_value=0, max_value=1),
                "Expert_Count": st.column_config.NumberColumn("Nº of Experts (≥80%)"),
                "Beginner_Count": st.column_config.NumberColumn("Nº of Beginners (<40%)"),
            },
            use_container_width=True,
            height=300
        )
    with col2:
        critical_gaps = project_readiness[project_readiness['Status'] == "❌ Critical Gap"]
        with st.container(border=True):
            st.markdown("🚨 **Action: Close Critical Gaps**")
            if not critical_gaps.empty:
                st.error(f"Found {len(critical_gaps)} critical skill gaps.")
                for skill in critical_gaps.index:
                    st.markdown(f"- **{skill}**: Prioritize immediate training or external hiring.")
            else:
                st.success("No critical skill gaps identified for this project. Proceed with staffing.")

def render_opportunity_lens(analytics):
    st.header("💡 Opportunity Lens: Strategic Skill Radar")
    st.info("**Decision:** Where can we expand our services? What new initiatives can we launch based on our team's latent strengths?")
    
    opportunity_df = analytics.get('opportunity_lens', pd.DataFrame())
    if opportunity_df.empty:
        st.warning("No significant team strengths identified (Avg. Confidence < 75%). Focus on foundational training.")
        return
    
    top_opportunities = opportunity_df.head(5)

    st.subheader("Team's Top 5 Latent Strengths")
    st.caption("These are areas where the team has high confidence and a strong concentration of experts, representing potential for new business or innovation.")

    fig = px.bar(
        top_opportunities,
        x='Competency_Score',
        y=top_opportunities.index,
        orientation='h',
        title="Top Skills by Competency (Confidence x Experts)",
        text='Avg_Score',
    )
    fig.update_traces(texttemplate='%{text:.0%}', textposition='outside')
    fig.update_layout(yaxis_title="Skill / Capability", xaxis_title="Competency Score")
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Take Action on These Opportunities"):
        st.markdown("""
        - **Pitch New Services:** Can these skills be packaged into a new service offering for clients?
        - **Launch Internal Initiatives:** Use these strengths to improve internal processes or create new tools.
        - **Develop Thought Leadership:** Encourage experts in these areas to write articles, host workshops, or represent the company.
        - **Formalize Expertise:** Create Centers of Excellence around these skills to standardize best practices.
        """)

def render_mentor_engine(df_merged, analytics):
    st.header("🤝 Mentor–Mentee Engine")
    st.info("**Decision:** How can we accelerate internal knowledge transfer and upskill the team efficiently?")
    
    sub1, sub2 = st.tabs(["👥 Build Training Groups", "🤝 Find a Mentor"])

    with sub1:
        st.subheader("Build Custom Training Groups")
        st.caption("Create balanced groups of learners, optionally led by an expert mentor, to tackle specific skills.")
        with st.form("group_builder_form"):
            all_tasks = sorted(df_merged['Task_Prefixed'].unique())
            selected_task = st.selectbox(
                "Select a skill for the training session:",
                all_tasks, index=0
            )
            g1, g2, g3 = st.columns(3)
            num_groups = g1.number_input("Number of groups:", 1, 10, value=2)
            num_per_group = g2.number_input("People per group:", 2, 10, value=4)
            add_mentors = g3.checkbox("Assign mentor?", value=True)

            if st.form_submit_button("Generate Groups", type="primary", use_container_width=True):
                st.subheader(f"✅ Generated Groups for: {selected_task}")
                filtered_df = df_merged[df_merged['Task_Prefixed'] == selected_task]
                
                if filtered_df.empty:
                    st.error("No participant data for the selected skill.")
                else:
                    group_scores = filtered_df.groupby('Name')['Score'].mean().sort_values()
                    mentors = group_scores[group_scores >= 0.8].sort_values(ascending=False)
                    learners = group_scores[group_scores < 0.8].sort_values(ascending=True)
                    cols = st.columns(num_groups)
                    assigned = set()
                    for i in range(num_groups):
                        with cols[i]:
                            with st.container(border=True):
                                st.markdown(f"**Group {i+1}**")
                                group_data = []
                                available_mentors = mentors[~mentors.index.isin(assigned)] if add_mentors else pd.Series(dtype=float)
                                if add_mentors and not available_mentors.empty:
                                    m_name = available_mentors.index[0]
                                    group_data.append({'Role': '🏆 Mentor', 'Name': m_name, 'Score': f"{available_mentors.iloc[0]:.1%}"})
                                    assigned.add(m_name)
                                needed = num_per_group - len(group_data)
                                group_learners = learners[~learners.index.isin(assigned)].head(needed)
                                for name, score in group_learners.items():
                                    group_data.append({'Role': '🌱 Learner', 'Name': name, 'Score': f"{score:.1%}"})
                                    assigned.add(name)
                                if group_data:
                                    st.dataframe(pd.DataFrame(group_data), hide_index=True, use_container_width=True)
                                else:
                                    st.warning(f"Not enough people to form Group {i+1}.")

    with sub2:
        st.subheader("Find a Mentor for a Specific Skill")
        st.caption("Quickly connect a team member needing help with a subject matter expert.")
        person_summary = analytics.get('person_summary', pd.DataFrame())
        learners_list = sorted(person_summary[person_summary['Archetype'].isin(["🌱 Consistent Learner", "🎯 Needs Support"])].index.tolist())
        all_tasks = sorted(df_merged['Task_Prefixed'].unique())
        c1, c2 = st.columns(2)
        selected_learner = c1.selectbox("Select a Learner", options=learners_list)
        skill_needed = c2.selectbox("Select a Skill Needed", options=all_tasks)
        if st.button("Find Mentor", use_container_width=True, type="primary"):
            experts_df = df_merged[(df_merged['Task_Prefixed'] == skill_needed) & (df_merged['Name'] != selected_learner) & (df_merged['Score'] >= 0.8)]
            if experts_df.empty:
                st.error(f"No suitable mentors found for the skill: **{skill_needed}**.")
            else:
                st.success(f"Top Mentor Recommendations for **{selected_learner}**")
                recs = experts_df.sort_values(by="Score", ascending=False).head(3)
                recs = recs.merge(person_summary, left_on='Name', right_index=True, how='left')
                st.dataframe(recs[['Name', 'Archetype', 'Score']], hide_index=True, use_container_width=True,
                             column_config={"Score": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1)})

def render_archetypes_and_roles(df_merged, user_df, analytics):
    st.header("🎭 Archetypes & Roles Alignment")
    st.info("**Decision:** Who fits best into which role for a project? How do we build balanced, high-performing teams?")

    person_summary = analytics.get('person_summary', pd.DataFrame())
    if person_summary.empty:
        st.warning("Cannot generate archetypes without assessment data.")
        return

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Team Archetype Distribution")
        archetype_counts = person_summary['Archetype'].value_counts()
        fig_pie = px.pie(
            archetype_counts, values=archetype_counts.values, names=archetype_counts.index, hole=0.5,
            title="Team Composition"
        )
        fig_pie.update_layout(height=400, margin=dict(t=50, b=20), legend_orientation="h")
        st.plotly_chart(fig_pie, use_container_width=True)
        st.caption("""
        - **🏆 Versatile Leader:** High skill, low variance. Reliable anchors for any project.
        - **🌟 Niche Specialist:** High skill, high variance. Deep experts in specific areas.
        - **🌱 Consistent Learner:** Lower skill, low variance. Dependable and ready for growth.
        - **🎯 Needs Support:** Lower skill, high variance. Require targeted guidance.
        """)
        
    with col2:
        st.subheader("Role Alignment Roster")
        st.caption("Filter the roster to find the right people for your project roles.")
        
        all_archetypes = ['All'] + sorted(person_summary['Archetype'].unique())
        selected_archetype = st.selectbox("Filter by Archetype:", options=all_archetypes)

        if selected_archetype == 'All':
            roster_df = person_summary
        else:
            roster_df = person_summary[person_summary['Archetype'] == selected_archetype]

        st.dataframe(
            roster_df.reset_index()[['Name', 'Archetype', 'Avg Score', 'Team Leader']],
            height=500, use_container_width=True, hide_index=True,
            column_config={"Avg Score": st.column_config.ProgressColumn("Avg Confidence", min_value=0, max_value=1)}
        )

def render_growth_trajectory_placeholder():
    st.header("📈 Growth Trajectory Dashboard")
    st.info("**Decision:** Are our training programs effective? Who deserves recognition or a stretch role based on their growth?")
    st.warning("📈 **Feature in Development:** This module requires historical data snapshots to track skill progress over time.")
    st.markdown("""
    When implemented, this dashboard will allow you to:
    - Visualize individual and team-wide skill growth month-over-month.
    - Identify the fastest learners and emerging leaders.
    - Measure the ROI of training initiatives.

    **To enable this, please save a version of `userData.csv` periodically (e.g., `userData_YYYY-MM.csv`).**
    """)
    st.image("https://storage.googleapis.com/s4a-prod-share-preview/default/st_app_screenshot_2024-03-01_12-25-05.png",
             caption="Example of what a future growth chart could look like.", use_column_width=True)

def render_team_resources_and_health(user_df):
    st.header("🔧 Team Resources & Operational Health")
    st.info("**Decision:** Do we have the right tools and support in place? Are there operational risks to address?")

    with st.container(border=True):
        st.subheader("📊 Affinity Software & Training Status")
        total_users = len(user_df)
        k1, k2, k3 = st.columns(3)
        active_licenses = user_df['Active License'].sum()
        trained_mck = user_df['Has received Affinity training of McK?'].sum()
        
        k1.metric("Total Team Members", f"{total_users}")
        k2.metric("Active Affinity Licenses", f"{active_licenses}", f"{active_licenses/total_users:.0%} of team")
        k3.metric("Received McK Training", f"{trained_mck}", f"{trained_mck/total_users:.0%} of team")

    with st.container(border=True):
        st.subheader("🚨 License Expiration Timeline")
        st.caption("Proactively manage license renewals to avoid disruption.")
        today = datetime.now()
        exp_df = user_df[user_df['License Expiration'].notna()].copy()
        if not exp_df.empty:
            exp_df['Days Left'] = (exp_df['License Expiration'] - today).dt.days
            exp_df_upcoming = exp_df[(exp_df['Days Left'] > 0) & (exp_df['Days Left'] <= 180)].sort_values('Days Left')
            if not exp_df_upcoming.empty:
                st.dataframe(exp_df_upcoming[['Name', 'License Expiration', 'Days Left']], use_container_width=True, hide_index=True)
            else:
                st.success("✅ No licenses expiring in the next 6 months.")
        else:
            st.info("No license expiration data found.")

    with st.container(border=True):
        st.subheader("🗣️ Team Feedback & Needs Analysis")
        st.caption("Understand common themes from team comments to guide support initiatives.")
        all_comments = user_df['Comments'].dropna().str.strip()
        all_comments = all_comments[all_comments != '']
        if not all_comments.empty:
            from analytics_engine import analyze_comment_themes
            theme_counts = analyze_comment_themes(all_comments)
            fig = px.bar(theme_counts, x='Mentions', y=theme_counts.index, orientation='h', text_auto=True, title="Common Themes in Comments")
            st.plotly_chart(fig, use_container_width=True)
            with st.expander("View Raw Comments"):
                st.dataframe(user_df[['Name', 'Comments']].drop_duplicates(), hide_index=True)
        else:
            st.success("No specific needs or comments provided by the team.")

def login_page():
    st.title("🔐 Team Skills Hub Login")
    with st.form("login_form"):
        username = st.text_input("Username").lower()
        password = st.text_input("PIN", type="password")
        submitted = st.form_submit_button("Log In")
        if submitted:
            try:
                correct_username = st.secrets["credentials"]["username"]
                correct_password = st.secrets["credentials"]["password"]
                if username == correct_username and password == correct_password:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Incorrect username or PIN. Try again.")
            except (KeyError, FileNotFoundError):
                 st.error("Secrets not configured for deployment. Contact administrator. If developing, check your .streamlit/secrets.toml file.")