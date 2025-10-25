# =============================
# File: ui_components.py
# =============================

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
from typing import Dict, Any
import config  # Import the centralized configuration

# ==============================================================================
# STREAMLINED & ORIGINAL UI COMPONENTS
# ==============================================================================

def render_strategic_overview(
    df_merged: pd.DataFrame, 
    user_df: pd.DataFrame, 
    analytics: Dict[str, Any], 
    total_participants_in_file: int, 
    score_parsing_errors: int
):
    """Renders the high-level dashboard tab."""
    # --- EDIT: person_summary no longer needed here ---
    risk_radar: pd.DataFrame = analytics.get('risk_radar', pd.DataFrame())

    col1, col2 = st.columns(2, gap="large")
    with col1:
        with st.container(border=True):
            st.subheader("📊 Team Vital Signs")
            kpi1, kpi2, kpi3 = st.columns(3)
            active_participants_count = df_merged['Name'].nunique()
            kpi1.metric("People in File", total_participants_in_file)
            
            response_rate = active_participants_count / total_participants_in_file if total_participants_in_file > 0 else 0
            kpi2.metric("Active Participants", active_participants_count, f"{response_rate:.0%} Response Rate")
            
            avg_confidence = df_merged['Score'].mean() if not df_merged.empty else 0
            kpi3.metric("Average Confidence", f"{avg_confidence:.1%}")

            # --- EDIT: Moved Archetype Pie Chart to render_team_dna ---

    with col2:
        with st.container(border=True):
            st.subheader("🩺 Data Health Check")
            assessed_names = set(df_merged['Name'].unique())
            all_user_names = set(user_df['Name'].unique())
            pending_assessment_names = all_user_names - assessed_names

            st.metric("Self-Assessment Response", f"{len(assessed_names)} / {len(all_user_names)}", f"{len(pending_assessment_names)} pending")
            st.metric("Score Data Quality", f"{score_parsing_errors} invalid entries", "Found in file", delta_color="off")
            with st.expander(f"View {len(pending_assessment_names)} pending"):
                if pending_assessment_names:
                    pending_df = user_df[user_df['Name'].isin(pending_assessment_names)][['Name', 'Team Leader']]
                    st.dataframe(pending_df, hide_index=True)
                else:
                    st.info("All users completed the assessment.")

    st.divider()
    
    # --- EDIT: Removed the 2nd column (Comparative Risk Profile) ---
    with st.container(border=True):
        st.subheader("🚨 Skill Risk Radar")
        st.caption("Top 5 tasks with the highest risk (few experts, many beginners).")
        if not risk_radar.empty:
            for _, row in risk_radar.head(5).iterrows():
                st.metric(label=row.name, value=f"{row['Avg_Score']:.1%} Avg. Confidence", delta=f"Risk Index: {row['Risk Index']:.2f}", delta_color="inverse")
        else:
            st.info("No risk data available.")


def render_affinity_status(user_df: pd.DataFrame, analytics: Dict[str, Any]):
    """Renders the Affinity license and feedback tab."""
    st.header("⭐ Affinity Status & Team Feedback")
    
    with st.container(border=True):
        st.subheader("📊 Overall Software Status")
        total_users = len(user_df)
        if total_users > 0:
            k1, k2 = st.columns(2)
            active_pct = user_df['Active License'].sum() / total_users
            k1.metric("Active Affinity Licenses", f"{user_df['Active License'].sum()}", f"{active_pct:.0%} of team")
            
            trained_pct = user_df['Has received Affinity training of McK?'].sum() / total_users
            k2.metric("Received McK Training", f"{user_df['Has received Affinity training of McK?'].sum()}", f"{trained_pct:.0%} of team")
        else:
            st.info("No user data loaded.")

    with st.container(border=True):
        st.subheader("🚨 License Expiration Timeline")
        today = datetime.now()
        exp_df = user_df[user_df['License Expiration'].notna()].copy()
        if not exp_df.empty:
            exp_df['Days Left'] = (exp_df['License Expiration'] - today).dt.days
            exp_df = exp_df[exp_df['Days Left'] > 0]
            if not exp_df.empty:
                exp_df['Start'] = today
                fig = px.timeline(exp_df.sort_values('Days Left'), x_start="Start", x_end="License Expiration", y="Name", text="Days Left", title="Upcoming Expirations")
                fig.update_yaxes(categoryorder="total ascending")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("✅ No upcoming license expirations.")
        else:
            st.info("No license expiration data found.")

    with st.container(border=True):
        st.subheader("🗣️ Team Feedback Analysis")
        theme_counts: pd.DataFrame = analytics.get('comment_themes', pd.DataFrame())
        if not theme_counts.empty:
            fig = px.bar(theme_counts, x='Mentions', y=theme_counts.index, orientation='h', text_auto=True, title="Top Comment Themes")
            st.plotly_chart(fig, use_container_width=True)
        
        comments_df = user_df[['Name', 'Comments']].drop_duplicates()
        comments_df = comments_df[comments_df['Comments'] != '']
        if not comments_df.empty:
            st.dataframe(comments_df, height=300, hide_index=True)
        else:
            st.info("No comments provided in the data.")


def render_action_playbook(df_merged: pd.DataFrame, analytics: Dict[str, Any]):
    """Renders the interactive playbook for managers."""
    st.header("🗺️ Action Playbook")
    
    person_summary: pd.DataFrame = analytics.get('person_summary', pd.DataFrame())
    risk_radar: pd.DataFrame = analytics.get('risk_radar', pd.DataFrame())
    skill_corr: pd.DataFrame = analytics.get('skill_correlation', pd.DataFrame())

    sub2, sub3, sub4 = st.tabs(["💡 Training Combos", "👥 Group Builder", "🤝 Mentor Matchmaker"])

    with sub2:
        st.subheader("💡 Training Combo Generator")
        if not risk_radar.empty and not skill_corr.empty:
            primary_task = st.selectbox("Select a Primary Skill", options=risk_radar.index.tolist())
            primary_skill_series = df_merged[df_merged['Task_Prefixed'] == primary_task]['Skill']
            
            if not primary_skill_series.empty:
                primary_skill = primary_skill_series.iloc[0]
                if primary_skill in skill_corr.columns:
                    synergies = skill_corr[primary_skill].sort_values(ascending=False).drop(primary_skill).head(3)
                    st.success(f"Suggested Training Module for: {primary_skill}")
                    st.markdown(f"**1. Primary Focus:** `{primary_task}`")
                    st.markdown("**2. High-Synergy Skills:**")
                    for skill, corr in synergies.items():
                        st.markdown(f"- **{skill}** (Correlation: {corr:.2f})")
                else:
                    st.warning(f"Skill '{primary_skill}' not found in correlation matrix.")
            else:
                 st.warning("No data found for the selected primary skill.")
        else:
            st.info("Risk or correlation data not available.")
            
    with sub3:
        st.subheader("👥 Custom Training Group Builder")
        with st.form("group_builder_form"):
            all_tasks = sorted(df_merged['Task_Prefixed'].unique())
            selected_task = st.selectbox(
                "Select a skill for the training session:",
                all_tasks, index=0 if all_tasks else None
            )
            g1, g2, g3 = st.columns(3)
            num_groups = g1.number_input("Number of groups:", 1, 10, value=2)
            num_per_group = g2.number_input("People per group:", 2, 10, value=4)
            add_mentors = g3.checkbox("Assign mentor?", value=True)

            if st.form_submit_button("Generate Groups", type="primary", use_container_width=True):
                if not selected_task:
                    st.error("Please select a skill.")
                else:
                    st.subheader(f"✅ Generated Groups for: {selected_task}")
                    filtered_df = df_merged[df_merged['Task_Prefixed'] == selected_task]
                    
                    if filtered_df.empty:
                        st.error("No participants found for the selected criteria.")
                    else:
                        group_scores = filtered_df.groupby('Name')['Score'].mean().sort_values()
                        mentors = group_scores[group_scores >= config.EXPERT_THRESHOLD].sort_values(ascending=False)
                        learners = group_scores[group_scores < config.EXPERT_THRESHOLD].sort_values(ascending=True)
                        
                        cols = st.columns(num_groups)
                        assigned = set()
                        
                        for i in range(num_groups):
                            with cols[i]:
                                with st.container(border=True):
                                    st.markdown(f"**Group {i+1}**")
                                    group_data = []
                                    
                                    # Assign mentor
                                    if add_mentors:
                                        available_mentors = mentors[~mentors.index.isin(assigned)]
                                        if not available_mentors.empty:
                                            m_name = available_mentors.index[0]
                                            group_data.append({'Role': '🏆 Mentor', 'Name': m_name, 'Score': f"{available_mentors.iloc[0]:.1%}"})
                                            assigned.add(m_name)
                                    
                                    # Assign learners
                                    needed = num_per_group - len(group_data)
                                    if needed > 0:
                                        group_learners = learners[~learners.index.isin(assigned)].head(needed)
                                        for name, score in group_learners.items():
                                            group_data.append({'Role': '🌱 Learner', 'Name': name, 'Score': f"{score:.1%}"})
                                            assigned.add(name)
                                    
                                    if group_data:
                                        st.dataframe(pd.DataFrame(group_data), hide_index=True, use_container_width=True)
                                    else:
                                        st.warning(f"Not enough people to form Group {i+1}.")
    with sub4:
        st.subheader("🤝 Mentor Matchmaker")
        if not person_summary.empty:
            learners_list = sorted(person_summary[person_summary['Archetype'].isin([
                config.ARCHETYPE_CONSISTENT_LEARNER, 
                config.ARCHETYPE_NEEDS_SUPPORT
            ])].index.tolist())
            
            all_tasks = sorted(df_merged['Task_Prefixed'].unique())
            
            c1, c2 = st.columns(2)
            selected_learner = c1.selectbox("Select a Learner", options=learners_list)
            skill_needed = c2.selectbox("Select a Skill Needed", options=all_tasks)
            
            if st.button("Find Mentor", use_container_width=True, type="primary"):
                if selected_learner and skill_needed:
                    experts_df = df_merged[
                        (df_merged['Task_Prefixed'] == skill_needed) & 
                        (df_merged['Name'] != selected_learner) & 
                        (df_merged['Score'] >= config.EXPERT_THRESHOLD)
                    ]
                    
                    if experts_df.empty:
                        st.error(f"No suitable mentors found for the skill: **{skill_needed}**.")
                    else:
                        st.success(f"Top Mentor Recommendations for **{selected_learner}** in **{skill_needed}**")
                        recs = experts_df.sort_values(by="Score", ascending=False).head(3)
                        recs = recs.merge(person_summary, left_on='Name', right_index=True, how='left')
                        st.dataframe(
                            recs[['Name', 'Archetype', 'Score']], 
                            hide_index=True, use_container_width=True,
                            column_config={"Score": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1)}
                        )
                else:
                    st.warning("Please select a learner and a skill.")
        else:
            st.info("Person summary data not available for matchmaker.")


def render_team_profiles(
    df_merged: pd.DataFrame, 
    user_df: pd.DataFrame, 
    analytics: Dict[str, Any]
):
    """Renders the deep-dive profile view for each team member."""
    st.header("👤 Team Profiles")
    person_summary: pd.DataFrame = analytics.get('person_summary', pd.DataFrame())

    col1, col2 = st.columns([1, 2], gap="large")
    
    if person_summary.empty:
        st.warning("No summary data available to display team profiles.")
        return

    with col1:
        with st.container(border=True):
            st.subheader("📇 Team Roster")
            all_user_names_list = sorted(user_df['Name'].unique())
            
            ranking_df = person_summary.reset_index().sort_values('Avg Score', ascending=False)
            ranking_df['Rank'] = ranking_df['Avg Score'].rank(method='min', ascending=False).astype(int)
            
            merged_ranking = user_df[['Name']].drop_duplicates().merge(
                ranking_df[['Name', 'Rank', 'Avg Score', 'Archetype']], 
                on='Name', 
                how='left'
            )
            merged_ranking['Assessed'] = merged_ranking['Name'].isin(set(df_merged['Name'].unique()))
            merged_ranking.sort_values('Rank', ascending=True, na_position='last', inplace=True)
            
            selected_person = st.selectbox("Select a Team Member", all_user_names_list, label_visibility="collapsed")
            
            st.dataframe(
                merged_ranking, 
                height=750, 
                hide_index=True,
                column_config={
                    "Assessed": st.column_config.CheckboxColumn("Assessed?", disabled=True),
                    "Avg Score": st.column_config.ProgressColumn("Avg Score", format="%.1f%%", min_value=0, max_value=1)
                }
            )

    with col2:
        with st.container(border=True):
            st.header(f"📇 Profile: {selected_person}")
            
            if selected_person not in set(df_merged['Name'].unique()):
                st.warning(f"**{selected_person} has not completed the self-assessment.**")
            
            elif selected_person not in person_summary.index:
                st.error(f"Data for {selected_person} is missing from the person summary.")
            
            else:
                person_stats = person_summary.loc[selected_person]
                person_data = df_merged[df_merged['Name'] == selected_person].copy()
                
                rank_val = merged_ranking.loc[merged_ranking['Name'] == selected_person, 'Rank'].iloc[0]
                rank_display = f"#{int(rank_val)}" if pd.notna(rank_val) else "N/A"

                c1, c2, c3 = st.columns(3)
                c1.metric("Overall Rank", rank_display)
                c2.metric("Average Score", f"{person_stats['Avg Score']:.1%}")
                c3.metric("Archetype", person_stats['Archetype'])
                st.divider()

                # Radar chart
                team_avg = df_merged.groupby('Category')['Score'].mean()
                person_avg = person_data.groupby('Category')['Score'].mean().reindex(team_avg.index, fill_value=0)
                
                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(r=person_avg.values, theta=person_avg.index, fill='toself', name=f'{selected_person}'))
                fig.add_trace(go.Scatterpolar(r=team_avg.values, theta=team_avg.index, fill='toself', name='Team Avg', opacity=0.6))
                fig.update_layout(title="Confidence vs. Team Average by Category")
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("**Strengths & Development Areas**")
                person_skills = person_data.sort_values('Score', ascending=False).drop_duplicates(subset=['Task_Prefixed'])
                
                sc1, sc2 = st.columns(2)
                with sc1:
                    st.markdown("✅ **Top 5 Skills**")
                    st.dataframe(
                        person_skills.head(5)[['Task_Prefixed', 'Score']], 
                        hide_index=True,
                        column_config={"Score": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1)}
                    )
                with sc2:
                    st.markdown("🌱 **Top 5 Improvement Areas**")
                    st.dataframe(
                        person_skills.tail(5)[['Task_Prefixed', 'Score']].sort_values('Score', ascending=True), 
                        hide_index=True,
                        column_config={"Score": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1)}
                    )


def render_skill_analysis(df_merged: pd.DataFrame, analytics: Dict[str, Any]):
    """
    Renders the deep-dive analysis by skill/category.
    --- EDIT: This is now a single-page tool, not a tabbed one. ---
    """
    st.header("🧠 Skill Analysis")
    
    st.subheader("Deep Dive by Skill or Category")
    analysis_type = st.radio("Analyze by:", ["Category", "Task"], horizontal=True)
    
    if analysis_type == "Task":
        options = sorted(df_merged['Task_Prefixed'].unique())
        label, filter_col = "Select Task(s)", 'Task_Prefixed'
    else:
        options = sorted(df_merged['Category'].unique())
        label, filter_col = "Select Category(s)", 'Category'
        
    selected = st.multiselect(label, options, default=options[0] if options else None)
    
    if not selected:
        st.warning(f"Please select at least one {analysis_type}.")
    else:
        skill_data = df_merged[df_merged[filter_col].isin(selected)]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Avg Confidence", f"{skill_data['Score'].mean():.1%}")
        c2.metric("Experts (≥80%)", skill_data[skill_data['Score'] >= config.EXPERT_THRESHOLD]['Name'].nunique())
        c3.metric("Beginners (<40%)", skill_data[skill_data['Score'] < config.BEGINNER_THRESHOLD]['Name'].nunique())
        st.divider()
        
        s1, s2 = st.columns(2)
        with s1:
            st.markdown("**Skill Leaderboard**")
            leaderboard = skill_data.groupby('Name')['Score'].mean().sort_values(ascending=False).reset_index()
            st.dataframe(
                leaderboard, 
                hide_index=True,
                column_config={"Score": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1)}
            )
        with s2:
            st.markdown("**Score Distribution**")
            fig = px.histogram(skill_data, x='Score', nbins=10, title="Confidence Score Distribution")
            fig.update_layout(height=350, margin=dict(t=20, b=20), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    # --- EDIT: Removed 'Talent Composition' and 'Skill Correlation' sub-tabs ---


# ==============================================================================
# ENHANCED: Team DNA & Dynamics
# ==============================================================================
def render_team_dna(df_merged: pd.DataFrame, analytics: Dict[str, Any]):
    """Renders the team comparison tab."""
    st.header("🧬 Team DNA & Dynamics")
    st.info("Compare team compositions and skill shapes to make strategic staffing and development decisions.")

    person_summary: pd.DataFrame = analytics.get('person_summary', pd.DataFrame())
    if person_summary.empty or 'Team Leader' not in person_summary.columns:
        st.warning("Cannot render Team DNA: Person summary or 'Team Leader' column is missing.")
        return
        
    st.subheader("🔬 Comparative Team Analysis")
    st.markdown("Use this tool to compare teams. Is one team a creative powerhouse while another is an execution engine? This helps assign the right team to the right project.")

    all_teams = sorted([t for t in person_summary['Team Leader'].unique() if t and t != ''])
    if not all_teams or len(all_teams) < 1:
        st.warning("Not enough team data available for comparison.")
        return

    c1, c2 = st.columns(2)
    team1_name = c1.selectbox("Select Primary Team", all_teams, index=0)
    
    comparison_options = ["Overall Company Average"] + [t for t in all_teams if t != team1_name]
    team2_name = c2.selectbox("Compare Against", comparison_options, index=0)

    team1_members = person_summary[person_summary['Team Leader'] == team1_name].index
    team1_data = df_merged[df_merged['Name'].isin(team1_members)]
    
    if team1_data.empty:
        st.warning(f"No skill data found for Team {team1_name}.")
        return
        
    team1_fingerprint = team1_data.groupby('Category')['Score'].mean()

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=team1_fingerprint.values, theta=team1_fingerprint.index, fill='toself', name=f"Team: {team1_name}"
    ))

    if team2_name == "Overall Company Average":
        company_fingerprint = df_merged.groupby('Category')['Score'].mean()
        fig.add_trace(go.Scatterpolar(
            r=company_fingerprint.values, theta=company_fingerprint.index, fill='toself', name="Company Average", opacity=0.6
        ))
    else:
        team2_members = person_summary[person_summary['Team Leader'] == team2_name].index
        team2_data = df_merged[df_merged['Name'].isin(team2_members)]
        if not team2_data.empty:
            team2_fingerprint = team2_data.groupby('Category')['Score'].mean()
            fig.add_trace(go.Scatterpolar(
                r=team2_fingerprint.values, theta=team2_fingerprint.index, fill='toself', name=f"Team: {team2_name}", opacity=0.6
            ))

    fig.update_layout(title="Comparative Skill Fingerprint (Mean Confidence)", polar=dict(radialaxis=dict(visible=True, range=[0, 1])))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📊 Archetype Balance")
    st.markdown("Understand the persona mix of a team to identify potential imbalances.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Overall Distribution**")
        # --- EDIT: Added Archetype Pie Chart (from Overview) ---
        archetype_counts = person_summary['Archetype'].value_counts()
        if not archetype_counts.empty:
            fig_pie = px.pie(
                archetype_counts,
                values=archetype_counts.values,
                names=archetype_counts.index,
                hole=0.5,
            )
            fig_pie.update_layout(height=300, margin=dict(t=30, b=20, l=0, r=0), legend_orientation="h")
            st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        st.markdown(f"**Composition for Team {team1_name}**")
        team_archetypes = person_summary[person_summary['Team Leader'] == team1_name]['Archetype'].value_counts(normalize=True) * 100
        if not team_archetypes.empty:
            fig_bar = px.bar(team_archetypes, y=team_archetypes.index, x=team_archetypes.values, orientation='h', text_auto='.0f')
            fig_bar.update_layout(height=300, xaxis_title="Percentage of Team", yaxis_title="Archetype", margin=dict(t=30, b=20))
            st.plotly_chart(fig_bar, use_container_width=True)

    # Actionable insights based on archetypes
    if not team_archetypes.empty:
        if team_archetypes.get(config.ARCHETYPE_NICHE_SPECIALIST, 0) > 40:
            st.warning(f"**Insight:** Team {team1_name} is heavily specialized. **Action:** Ensure projects have a 'Versatile Leader' to connect the dots and manage overall scope.")
        if team_archetypes.get(config.ARCHETYPE_VERSATILE_LEADER, 0) < 10:
            st.warning(f"**Insight:** Team {team1_name} may lack leadership depth. **Action:** Identify a high-potential 'Consistent Learner' for leadership training.")
        if team_archetypes.get(config.ARCHETYPE_CONSISTENT_LEARNER, 0) > 50:
            st.success(f"**Insight:** Team {team1_name} has strong potential for growth. **Action:** Pair them with mentors and invest in targeted training programs.")


# ==============================================================================
# ENHANCED: Risk & Opportunity Forecaster
# ==============================================================================
def render_risk_opportunity(analytics: Dict[str, Any]):
    """Renders the risk and opportunity workbench."""
    st.header("🔭 Risk & Opportunity Forecaster")
    st.info("Move from viewing data to making decisions. Use these workbenches to mitigate risks and deploy strengths.")

    risk_matrix: pd.DataFrame = analytics.get('risk_matrix', pd.DataFrame())
    opportunity_df: pd.DataFrame = analytics.get('opportunity_lens', pd.DataFrame())
    talent_pipeline: pd.DataFrame = analytics.get('talent_pipeline', pd.DataFrame())
    df_merged: pd.DataFrame = analytics.get('df_merged_for_lookup')

    if df_merged is None:
        st.error("Required data not available for this module.")
        return

    sub_tabs = st.tabs(["🚨 Risk Mitigation Workbench", "💡 Strength Deployment Planner"])

    with sub_tabs[0]:
        st.subheader("🚨 Risk Mitigation Workbench")
        st.markdown("**Goal:** Proactively solve your biggest talent risks.")

        if risk_matrix.empty:
            st.success("✅ No high-risk skills detected. The team is well-balanced.")
        else:
            high_risk_skills = risk_matrix.sort_values('Risk Index', ascending=False)
            selected_risk = st.selectbox(
                "Select a high-risk skill to solve:",
                options=high_risk_skills.index,
                format_func=lambda x: f"{x} (Risk Index: {high_risk_skills.loc[x, 'Risk Index']:.2f})"
            )
            
            if selected_risk:
                st.error(f"**Analysis for: {selected_risk}**")
                risk_info = high_risk_skills.loc[selected_risk]
                c1, c2, c3 = st.columns(3)
                c1.metric("Avg Confidence", f"{risk_info['Avg_Score']:.1%}")
                c2.metric("Experts (≥80%)", f"{int(risk_info['Expert_Count'])}")
                c3.metric("Beginners (<40%)", f"{int(risk_info['Beginner_Count'])}")

                st.markdown("---")
                st.subheader("Action Plan")
                
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("##### 🌱 **Upskill Talent Pipeline**")
                    st.caption("People with 60-79% confidence in this skill.")
                    pipeline_for_skill = talent_pipeline[talent_pipeline['Task_Prefixed'] == selected_risk]
                    if not pipeline_for_skill.empty:
                        st.dataframe(pipeline_for_skill[['Name', 'Archetype', 'Score']], hide_index=True, use_container_width=True)
                    else:
                        st.warning("No candidates in the immediate pipeline. Broaden search.")
                
                with c2:
                    st.markdown("##### 🤝 **Assign Mentors**")
                    st.caption("Experts (≥80%) available to mentor this skill.")
                    all_experts = df_merged[
                        (df_merged['Task_Prefixed'] == selected_risk) & 
                        (df_merged['Score'] >= config.EXPERT_THRESHOLD)
                    ]
                    if not all_experts.empty:
                        st.dataframe(all_experts[['Name', 'Score']].sort_values('Score', ascending=False), hide_index=True, use_container_width=True)
                    else:
                        st.error("No experts available to mentor this skill.")

    with sub_tabs[1]:
        st.subheader("💡 Strength Deployment Planner")
        st.markdown("**Goal:** Identify your champions and deploy them strategically.")
        
        if opportunity_df.empty:
            st.info("No significant team strengths identified to form a deployment plan.")
        else:
            selected_strength = st.selectbox(
                "Select a strategic strength to deploy:",
                options=opportunity_df.index,
                format_func=lambda x: f"{x} (Competency Score: {opportunity_df.loc[x, 'Competency_Score']:.2f})"
            )

            if selected_strength:
                st.success(f"**Deployment Plan for: {selected_strength}**")

                champions = df_merged[
                    (df_merged['Task_Prefixed'] == selected_strength) & 
                    (df_merged['Score'] >= config.EXPERT_THRESHOLD)
                ].sort_values('Score', ascending=False)
                
                c1, c2 = st.columns([1,2])
                with c1:
                    st.markdown("##### 🏆 **Your Champions**")
                    st.dataframe(champions[['Name', 'Score']], hide_index=True)

                with c2:
                    st.markdown("##### 🚀 **Deployment Actions**")
                    st.markdown("- **Lead Initiatives:** Assign these champions to lead new projects or client proposals leveraging this skill.")
                    st.markdown("- **Create Knowledge Base:** Task them with creating best-practice guides or holding a workshop for the team.")
                    st.markdown("- **Mentor Others:** Pair them with learners identified in the 'Risk Workbench' or 'Action Playbook'.")

# ==============================================================================
# LOGIN PAGE
# ==============================================================================
def login_page():
    """Displays the login form."""
    st.title("🔐 Team Skills Hub Login")
    with st.form("login_form"):
        username = st.text_input("Username").lower()
        password = st.text_input("PIN", type="password")
        submitted = st.form_submit_button("Log In")
        
        if submitted:
            try:
                # Check secrets
                correct_username = st.secrets["credentials"]["username"]
                correct_password = st.secrets["credentials"]["password"]
                
                if username == correct_username and password == correct_password:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Incorrect username or PIN. Try again.")
            except (KeyError, FileNotFoundError):
                 st.error("Secrets not configured for deployment. Contact administrator. If developing, check your .streamlit/secrets.toml file.")