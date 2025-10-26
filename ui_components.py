# =============================
# File: ui_components.py
# =============================

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
from typing import Dict, Any
import config

# --- Style Constants for Charts ---
GRAY_PALETTE = px.colors.sequential.Greys
PLOTLY_TEMPLATE = "plotly_white"
DARK_GRAY = "#4A4A4A"
MEDIUM_GRAY = "#7A7A7A"
LIGHT_GRAY = "#CCCCCC"

# ==============================================================================
# UI Rendering Functions (Minimalist Style with Containers)
# ==============================================================================

def render_strategic_overview(
    df_merged: pd.DataFrame,
    user_df: pd.DataFrame,
    analytics: Dict[str, Any],
    total_participants_in_file: int,
    score_parsing_errors: int
):
    """Renders the high-level dashboard tab (Minimalist with Containers)."""
    risk_radar: pd.DataFrame = analytics.get('risk_radar', pd.DataFrame())
    theme_counts: pd.DataFrame = analytics.get('comment_themes', pd.DataFrame())

    col1, col2 = st.columns(2, gap="large")
    with col1:
        # --- Re-added border=True ---
        with st.container(border=True):
            st.subheader("Team Vital Signs")
            kpi1, kpi2, kpi3 = st.columns(3)
            active_participants_count = df_merged['Name'].nunique()
            kpi1.metric("People in File", total_participants_in_file)
            response_rate = active_participants_count / total_participants_in_file if total_participants_in_file > 0 else 0
            kpi2.metric("Active Participants", active_participants_count, f"{response_rate:.0%} Response Rate")
            avg_confidence = df_merged['Score'].mean() if not df_merged.empty else 0
            kpi3.metric("Average Confidence", f"{avg_confidence:.1%}")

        # --- Re-added border=True ---
        with st.container(border=True):
            st.subheader("Skill Risk Radar")
            st.caption("Top 5 tasks with the highest risk (few experts, many beginners).")
            if not risk_radar.empty:
                risk_data_head = risk_radar.head(5)
                for skill_name, row in risk_data_head.iterrows():
                    avg_score = row.get('Avg_Score', 0)
                    risk_index = row.get('Risk Index', 0)
                    st.metric(label=skill_name, value=f"{avg_score:.1%} Avg. Confidence", delta=f"Risk Index: {risk_index:.2f}", delta_color="normal")
            else:
                st.info("No risk data available.")

    with col2:
        # --- Re-added border=True ---
        with st.container(border=True):
            st.subheader("Data Health Check")
            assessed_names = set(df_merged['Name'].unique())
            all_user_names = set(user_df['Name'].unique())
            pending_assessment_names = all_user_names - assessed_names

            st.metric("Self-Assessment Response", f"{len(assessed_names)} / {len(all_user_names)}", f"{len(pending_assessment_names)} pending")
            st.metric("Score Data Quality", f"{score_parsing_errors} invalid entries", delta_color="off")
            # Expander naturally has a background from the theme, doesn't need extra border
            with st.expander(f"View {len(pending_assessment_names)} pending"):
                if pending_assessment_names:
                    pending_df = user_df[user_df['Name'].isin(pending_assessment_names)][['Name', 'Team Leader']]
                    st.dataframe(pending_df, hide_index=True, use_container_width=True)
                else:
                    st.info("All users completed the assessment.")

        # --- Re-added border=True ---
        with st.container(border=True):
            st.subheader("Top Comment Themes")
            st.caption("Top themes from all user comments.")
            if not theme_counts.empty:
                fig_bar = px.bar(theme_counts.head(5), x='Mentions', y=theme_counts.head(5).index, orientation='h', text_auto=True,
                                 template=PLOTLY_TEMPLATE)
                fig_bar.update_traces(marker_color=DARK_GRAY)
                fig_bar.update_layout(height=300, margin=dict(t=20, b=20, l=0, r=0), yaxis_title=None, xaxis_title="Mentions")
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("No comment data found.")

def render_affinity_status(user_df: pd.DataFrame, analytics: Dict[str, Any]):
    """Renders the Affinity license and feedback tab (Minimalist with Containers)."""
    st.header("Affinity Status & Team Feedback")

    # --- Re-added border=True ---
    with st.container(border=True):
        st.subheader("Overall Software Status")
        total_users = len(user_df)
        if total_users > 0:
            k1, k2 = st.columns(2)
            active_pct = user_df['Active License'].sum() / total_users
            k1.metric("Active Affinity Licenses", f"{user_df['Active License'].sum()}", f"{active_pct:.0%} of team")
            trained_pct = user_df['Has received Affinity training of McK?'].sum() / total_users
            k2.metric("Received McK Training", f"{user_df['Has received Affinity training of McK?'].sum()}", f"{trained_pct:.0%} of team")
        else:
            st.info("No user data loaded.")

    # --- Re-added border=True ---
    with st.container(border=True):
        st.subheader("License Expiration Timeline")
        today = datetime.now()
        exp_df = user_df[user_df['License Expiration'].notna()].copy()
        if not exp_df.empty:
            exp_df['Days Left'] = (exp_df['License Expiration'] - today).dt.days
            exp_df = exp_df[exp_df['Days Left'] > 0]
            if not exp_df.empty:
                exp_df['Start'] = today

                def get_urgency_shade(days_left):
                    if days_left < 30: return 'Urgent (Dark Gray)'
                    elif days_left < 90: return 'Medium (Gray)'
                    else: return 'Low (Light Gray)'
                exp_df['Urgency'] = exp_df['Days Left'].apply(get_urgency_shade)

                fig = px.timeline(
                    exp_df.sort_values('Days Left'),
                    x_start="Start", x_end="License Expiration", y="Name", text="Days Left",
                    color="Urgency",
                    color_discrete_map={
                        'Urgent (Dark Gray)': DARK_GRAY,
                        'Medium (Gray)': MEDIUM_GRAY,
                        'Low (Light Gray)': LIGHT_GRAY
                    },
                    title="Upcoming Expirations",
                    template=PLOTLY_TEMPLATE
                )
                fig.update_yaxes(categoryorder="total ascending", title=None)
                fig.update_layout(legend_title_text='Urgency')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No upcoming license expirations.")
        else:
            st.info("No license expiration data found.")

    # --- Re-added border=True ---
    with st.container(border=True):
        st.subheader("All Team Feedback")
        st.caption("Unfiltered comments from the 'Specific Needs' column.")
        comments_df = user_df[['Name', 'Comments']].drop_duplicates()
        comments_df = comments_df[comments_df['Comments'] != '']
        if not comments_df.empty:
            st.dataframe(comments_df, height=300, hide_index=True, use_container_width=True)
        else:
            st.info("No comments provided in the data.")


def render_team_profiles(
    df_merged: pd.DataFrame,
    user_df: pd.DataFrame,
    analytics: Dict[str, Any]
):
    """Renders the deep-dive profile view (Minimalist with Containers)."""
    st.header("Team Profiles")
    person_summary: pd.DataFrame = analytics.get('person_summary', pd.DataFrame())

    col1, col2 = st.columns([1, 2], gap="large")

    if person_summary.empty:
        st.warning("No summary data available to display team profiles.")
        return

    with col1:
        # --- Re-added border=True ---
        with st.container(border=True):
            st.subheader("Team Roster")
            all_user_names_list = sorted(user_df['Name'].unique())

            ranking_df = person_summary.reset_index().sort_values('Avg Score', ascending=False)
            ranking_df['Rank'] = ranking_df['Avg Score'].rank(method='min', ascending=False).astype(int)
            merged_ranking = user_df[['Name']].drop_duplicates().merge(
                ranking_df[['Name', 'Rank', 'Avg Score', 'Archetype']], on='Name', how='left'
            )
            merged_ranking['Assessed'] = merged_ranking['Name'].isin(set(df_merged['Name'].unique()))
            merged_ranking.sort_values('Rank', ascending=True, na_position='last', inplace=True)
            selected_person = st.selectbox("Select a Team Member", all_user_names_list, label_visibility="collapsed")

            st.dataframe(
                merged_ranking, height=750, hide_index=True, use_container_width=True,
                column_config={
                    "Assessed": st.column_config.CheckboxColumn("Assessed?", disabled=True),
                    "Avg Score": st.column_config.ProgressColumn(
                        "Avg Score", format="%.1f%%", min_value=0, max_value=1
                    )
                 }
            )

    with col2:
        # --- Re-added border=True ---
        with st.container(border=True):
            st.subheader(f"Profile: {selected_person}")

            if selected_person not in set(df_merged['Name'].unique()):
                st.warning(f"**{selected_person}** has not completed the self-assessment.")
            elif selected_person not in person_summary.index:
                st.warning(f"Data for {selected_person} is missing from the person summary.")
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

                team_avg_scores = df_merged.groupby('Category')['Score'].mean()
                person_avg_scores = person_data.groupby('Category')['Score'].mean().reindex(team_avg_scores.index, fill_value=0)
                categories_ordered = sorted(team_avg_scores.index)
                team_avg_ordered = team_avg_scores.reindex(categories_ordered)
                person_avg_ordered = person_avg_scores.reindex(categories_ordered)

                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(r=person_avg_ordered.values, theta=categories_ordered, fill='toself', name=f'{selected_person}', line_color=DARK_GRAY, fillcolor=f'rgba({int(DARK_GRAY[1:3], 16)},{int(DARK_GRAY[3:5], 16)},{int(DARK_GRAY[5:7], 16)},0.3)'))
                fig_radar.add_trace(go.Scatterpolar(r=team_avg_ordered.values, theta=categories_ordered, fill='toself', name='Team Avg', line_color=LIGHT_GRAY, fillcolor=f'rgba({int(LIGHT_GRAY[1:3], 16)},{int(LIGHT_GRAY[3:5], 16)},{int(LIGHT_GRAY[5:7], 16)},0.3)'))
                fig_radar.update_layout(title="Confidence vs. Team Average by Category", template=PLOTLY_TEMPLATE, legend_title_text='')
                st.plotly_chart(fig_radar, use_container_width=True)

                st.markdown("**Strengths & Development Areas**")
                person_skills = person_data.set_index('Task_Prefixed')['Score'].sort_values(ascending=False)

                sc1, sc2 = st.columns(2)
                # Group skills/areas in bordered containers if desired, or leave flat
                with sc1:
                    st.markdown("##### Top 5 Skills")
                    top_5 = person_skills.head(5).reset_index()
                    fig_top = px.bar(
                        top_5, y='Task_Prefixed', x='Score', orientation='h', text='Score', height=250, title="Top 5 Skills",
                        template=PLOTLY_TEMPLATE
                    )
                    fig_top.update_traces(texttemplate='%{x:.0%}', textposition='outside', marker_color=DARK_GRAY)
                    fig_top.update_layout(xaxis_range=[0,1], yaxis_title=None, xaxis_title="Confidence", margin=dict(l=0,r=0,t=30,b=0))
                    st.plotly_chart(fig_top, use_container_width=True)

                with sc2:
                    st.markdown("##### Top 5 Improvement Areas")
                    bottom_5 = person_skills.tail(5).sort_values(ascending=True).reset_index()
                    fig_bottom = px.bar(
                        bottom_5, y='Task_Prefixed', x='Score', orientation='h', text='Score', height=250, title="Top 5 Improvement Areas",
                        template=PLOTLY_TEMPLATE
                    )
                    fig_bottom.update_traces(texttemplate='%{x:.0%}', textposition='outside', marker_color=MEDIUM_GRAY)
                    fig_bottom.update_layout(xaxis_range=[0,1], yaxis_title=None, xaxis_title="Confidence", margin=dict(l=0,r=0,t=30,b=0))
                    st.plotly_chart(fig_bottom, use_container_width=True)


def render_skill_analysis(df_merged: pd.DataFrame, analytics: Dict[str, Any]):
    """
    Renders the deep-dive analysis by skill/category (Minimalist with Containers).
    """
    st.header("Skill Analysis")

    # --- Re-added border=True ---
    with st.container(border=True):
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
            avg_score_selected = skill_data['Score'].mean()

            c1, c2, c3 = st.columns(3)
            c1.metric("Avg Confidence", f"{avg_score_selected:.1%}")
            c2.metric("Experts (>=80%)", skill_data[skill_data['Score'] >= config.EXPERT_THRESHOLD]['Name'].nunique())
            c3.metric("Beginners (<40%)", skill_data[skill_data['Score'] < config.BEGINNER_THRESHOLD]['Name'].nunique())
            st.divider()

            s1, s2 = st.columns(2)
            with s1:
                st.markdown("**Skill Leaderboard**")
                leaderboard = skill_data.groupby('Name')['Score'].mean().sort_values(ascending=False).reset_index()
                st.dataframe(
                    leaderboard, hide_index=True, use_container_width=True,
                    column_config={"Score": st.column_config.ProgressColumn(
                        "Confidence", format="%.1f%%", min_value=0, max_value=1
                        )}
                )
            with s2:
                st.markdown("**Score Distribution**")
                fig_hist = px.histogram(skill_data, x='Score', nbins=10, title="Confidence Score Distribution",
                                        template=PLOTLY_TEMPLATE)
                fig_hist.update_traces(marker_color=MEDIUM_GRAY)
                fig_hist.update_layout(height=350, margin=dict(t=30, b=20), showlegend=False, yaxis_title=None, xaxis_title="Confidence Score")

                fig_hist.add_vline(
                    x=avg_score_selected, line_width=2, line_dash="dash", line_color=DARK_GRAY,
                    annotation_text=f"Avg: {avg_score_selected:.1%}",
                    annotation_position="top left",
                    annotation_font_color=DARK_GRAY
                )
                st.plotly_chart(fig_hist, use_container_width=True)


# ==============================================================================
# STREAMLINED ACTION TAB (Minimalist Style with Containers)
# ==============================================================================
def render_action_workbench(df_merged: pd.DataFrame, analytics: Dict[str, Any]):
    """Renders the risk mitigation and group builder workbench (Minimalist with Containers)."""
    st.header("Action Workbench")
    st.caption("Use these tools to mitigate risks and build training groups.")

    risk_matrix: pd.DataFrame = analytics.get('risk_matrix', pd.DataFrame())
    talent_pipeline: pd.DataFrame = analytics.get('talent_pipeline', pd.DataFrame())
    df_merged_lookup: pd.DataFrame = analytics.get('df_merged_for_lookup')
    person_summary: pd.DataFrame = analytics.get('person_summary', pd.DataFrame())

    if df_merged_lookup is None or person_summary is None:
        st.warning("Required data not available for this module.")
        return

    sub_tabs = st.tabs(["Risk Mitigation", "Group Builder"])

    with sub_tabs[0]:
        # --- Re-added border=True ---
        with st.container(border=True):
            st.subheader("Risk Mitigation Workbench")
            st.markdown("**Goal:** Proactively solve your biggest talent risks.")

            if risk_matrix.empty:
                st.info("No high-risk skills detected.")
            else:
                high_risk_skills = risk_matrix.sort_values('Risk Index', ascending=False)
                selected_risk = st.selectbox(
                    "Select a high-risk skill to solve:",
                    options=high_risk_skills.index,
                    format_func=lambda x: f"{x} (Risk Index: {high_risk_skills.loc[x, 'Risk Index']:.2f})"
                )

                if selected_risk:
                    st.info(f"**Analysis for: {selected_risk}**")
                    risk_info = high_risk_skills.loc[selected_risk]
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Avg Confidence", f"{risk_info['Avg_Score']:.1%}")
                    c2.metric("Experts (>=80%)", f"{int(risk_info['Expert_Count'])}")
                    c3.metric("Beginners (<40%)", f"{int(risk_info['Beginner_Count'])}")

                    st.markdown("---")
                    st.subheader("Action Plan")

                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("##### Talent Pipeline")
                        st.caption("People with 60-79% confidence.")
                        pipeline_for_skill = talent_pipeline[talent_pipeline['Task_Prefixed'] == selected_risk]
                        if not pipeline_for_skill.empty:
                            st.dataframe(pipeline_for_skill[['Name', 'Archetype', 'Score']], hide_index=True, use_container_width=True)
                        else:
                            st.info("No candidates found in the pipeline.")

                    with c2:
                        st.markdown("##### Available Mentors")
                        st.caption("Experts (>=80%) for this skill.")
                        all_experts = df_merged_lookup[
                            (df_merged_lookup['Task_Prefixed'] == selected_risk) &
                            (df_merged_lookup['Score'] >= config.EXPERT_THRESHOLD)
                        ]
                        if not all_experts.empty:
                             experts_with_archetype = pd.merge(
                                all_experts[['Name', 'Score']].drop_duplicates(subset=['Name']),
                                person_summary[['Archetype']], left_on='Name', right_index=True, how='left'
                             )
                             st.dataframe(
                                experts_with_archetype[['Name', 'Archetype', 'Score']].sort_values('Score', ascending=False),
                                hide_index=True, use_container_width=True
                             )
                        else:
                             st.info("No experts available to mentor.")

    with sub_tabs[1]:
         # --- Re-added border=True ---
        with st.container(border=True):
            st.subheader("Custom Training Group Builder")
            st.markdown("**Goal:** Manually create training groups for any skill.")
            # Form naturally creates visual separation
            with st.form("group_builder_form"):
                all_tasks = sorted(df_merged_lookup['Task_Prefixed'].unique())
                selected_task = st.selectbox(
                    "Select a skill for the training session:", all_tasks, index=0 if all_tasks else None
                )
                g1, g2, g3 = st.columns(3)
                num_groups = g1.number_input("Number of groups:", 1, 10, value=2)
                num_per_group = g2.number_input("People per group:", 2, 10, value=4)
                add_mentors = g3.checkbox("Assign mentor?", value=True)

                submitted = st.form_submit_button("Generate Groups", type="primary", use_container_width=True)

            # Display generated groups outside the form
            if submitted: # Check if form was submitted in this run
                if not selected_task:
                    st.warning("Please select a skill.")
                else:
                    st.subheader(f"Generated Groups for: {selected_task}")
                    filtered_df = df_merged_lookup[df_merged_lookup['Task_Prefixed'] == selected_task]

                    if filtered_df.empty:
                        st.warning("No participants found for the selected criteria.")
                    else:
                        group_scores = filtered_df.groupby('Name')['Score'].mean().sort_values()
                        mentors = group_scores[group_scores >= config.EXPERT_THRESHOLD].sort_values(ascending=False)
                        learners = group_scores[group_scores < config.EXPERT_THRESHOLD].sort_values(ascending=True)
                        cols = st.columns(num_groups)
                        assigned = set()

                        for i in range(num_groups):
                            with cols[i]:
                                # Use border here to clearly separate each group
                                with st.container(border=True):
                                    st.markdown(f"**Group {i+1}**")
                                    group_data = []
                                    if add_mentors:
                                        available_mentors = mentors[~mentors.index.isin(assigned)]
                                        if not available_mentors.empty:
                                            m_name = available_mentors.index[0]
                                            group_data.append({'Role': 'Mentor', 'Name': m_name, 'Score': f"{available_mentors.iloc[0]:.1%}"})
                                            assigned.add(m_name)
                                    needed = num_per_group - len(group_data)
                                    if needed > 0:
                                        group_learners = learners[~learners.index.isin(assigned)].head(needed)
                                        for name, score in group_learners.items():
                                             group_data.append({'Role': 'Learner', 'Name': name, 'Score': f"{score:.1%}"})
                                             assigned.add(name)

                                    if group_data:
                                         st.dataframe(pd.DataFrame(group_data), hide_index=True, use_container_width=True)
                                    else:
                                         st.warning(f"Not enough people to form Group {i+1}.")