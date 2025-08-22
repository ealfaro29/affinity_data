# =============================
# File: ui_components.py
# =============================

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime


def render_strategic_overview(df_merged, user_df, analytics, total_participants_in_file, score_parsing_errors):
    person_summary = analytics.get('person_summary', pd.DataFrame())
    risk_radar = analytics.get('risk_radar', pd.DataFrame())

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
                fig_pie = px.pie(
                    archetype_counts,
                    values=archetype_counts.values,
                    names=archetype_counts.index,
                    hole=0.5,
                )
                fig_pie.update_layout(height=300, margin=dict(t=30, b=20, l=0, r=0), legend_orientation="h")
                st.plotly_chart(fig_pie, use_container_width=True)

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
                    st.dataframe(user_df[user_df['Name'].isin(pending_assessment_names)][['Name', 'Team Leader']], hide_index=True)
                else:
                    st.info("All users completed the assessment.")

    st.divider()
    col1, col2 = st.columns(2, gap="large")
    with col1:
        with st.container(border=True):
            st.subheader("🚨 Skill Risk Radar")
            st.caption("Top 5 tasks with the highest risk (few experts, many beginners).")
            if not risk_radar.empty:
                for _, row in risk_radar.head(5).iterrows():
                    st.metric(label=row.name, value=f"{row['Avg_Score']:.1%} Avg. Confidence", delta=f"Risk Index: {row['Risk Index']:.2f}", delta_color="inverse")
            else:
                st.info("No risk data available.")

    with col2:
        with st.container(border=True):
            st.subheader("📡 Comparative Risk Profile")
            if not risk_radar.empty:
                risk_data_head = risk_radar.head(5).reset_index()
                categories = ['Avg_Score', 'Risk Index', 'Expert_Count', 'Beginner_Count']
                valid_categories = [c for c in categories if c in risk_data_head.columns]
                normalized = risk_data_head[valid_categories].copy()
                for c in valid_categories:
                    rng = risk_radar[c].max() - risk_radar[c].min()
                    normalized[c] = (risk_data_head[c] - risk_radar[c].min()) / rng if rng > 0 else 0.5
                fig = go.Figure()
                for i, row in risk_data_head.iterrows():
                    fig.add_trace(go.Scatterpolar(
                        r=normalized.loc[i, valid_categories].values,
                        theta=[c.replace('_', ' ') for c in valid_categories],
                        fill='toself',
                        name=row['Task_Prefixed'][:40] + "...",
                        hovertemplate=f"<b>{row['Task_Prefixed']}</b><br>Risk Index: {row['Risk Index']:.2f}<br>Avg Score: {row['Avg_Score']:.1%}<extra></extra>",
                    ))
                fig.update_layout(polar=dict(radialaxis=dict(visible=False, range=[0, 1])), height=350, margin=dict(l=40, r=40, t=60, b=40))
                st.plotly_chart(fig, use_container_width=True)


def render_affinity_status(user_df):
    st.header("⭐ Affinity Status & Team Feedback")
    with st.container(border=True):
        st.subheader("📊 Overall Software Status")
        total_users = len(user_df)
        k1, k2 = st.columns(2)
        k1.metric("Active Affinity Licenses", f"{user_df['Active License'].sum()}", f"{user_df['Active License'].sum()/total_users:.0%} of team")
        k2.metric("Received McK Training", f"{user_df['Has received Affinity training of McK?'].sum()}", f"{user_df['Has received Affinity training of McK?'].sum()/total_users:.0%} of team")

    with st.container(border=True):
        st.subheader("🚨 License Expiration Timeline")
        today = datetime.now()
        exp_df = user_df[user_df['License Expiration'].notna()].copy()
        if not exp_df.empty:
            exp_df['Days Left'] = (exp_df['License Expiration'] - today).dt.days
            exp_df = exp_df[exp_df['Days Left'] > 0]
            if not exp_df.empty:
                exp_df['Start'] = today
                fig = px.timeline(exp_df, x_start="Start", x_end="License Expiration", y="Name", text="Days Left")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("✅ No upcoming license expirations.")
        else:
            st.success("✅ No license expiration data found.")

    with st.container(border=True):
        st.subheader("🗣️ Team Feedback Analysis")
        all_comments = user_df['Comments'].dropna()
        if not all_comments.empty and not all_comments.str.strip().eq('').all():
            from analytics_engine import analyze_comment_themes
            theme_counts = analyze_comment_themes(all_comments)
            fig = px.bar(theme_counts, x='Mentions', y=theme_counts.index, orientation='h', text_auto=True)
            st.plotly_chart(fig, use_container_width=True)
        st.dataframe(user_df[['Name', 'Comments']].drop_duplicates(), height=300, hide_index=True)


def render_action_playbook(df_merged, analytics):
    st.header("🗺️ Action Playbook")
    person_summary = analytics.get('person_summary', pd.DataFrame())
    risk_radar = analytics.get('risk_radar', pd.DataFrame())
    skill_corr = analytics.get('skill_correlation', pd.DataFrame())

    sub1, sub2, sub3 = st.tabs(["💡 Training Combo Generator", "👥 Group Builder", "🤝 Mentor Matchmaker"])

    with sub1:
        st.subheader("💡 Training Combo Generator")
        if not risk_radar.empty:
            primary_task = st.selectbox("Select a Primary Skill", options=risk_radar.index.tolist())
            primary_skill_series = df_merged[df_merged['Task_Prefixed'] == primary_task]['Skill']
            if not primary_skill_series.empty and not skill_corr.empty:
                primary_skill = primary_skill_series.iloc[0]
                if primary_skill in skill_corr.columns:
                    synergies = skill_corr[primary_skill].sort_values(ascending=False).drop(primary_skill).head(3)
                    st.success(f"Suggested Training Module for: {primary_skill}")
                    st.markdown(f"**1. Primary Focus:** `{primary_task}`")
                    st.markdown("**2. High-Synergy Skills:**")
                    for skill, corr in synergies.items():
                        st.markdown(f"- **{skill}** (Correlation: {corr:.2f})")

    with sub2:
        st.subheader("👥 Custom Training Group Builder")
        with st.form("group_builder_form"):
            all_categories = sorted(df_merged['Category'].unique())
            selected_categories = st.multiselect("Filter by Category", all_categories, default=all_categories[0] if all_categories else None)
            selected_tasks = []
            if selected_categories:
                selected_tasks = st.multiselect(
                    "Filter by Task (Optional)",
                    sorted(df_merged[df_merged['Category'].isin(selected_categories)]['Task_Prefixed'].unique())
                )
            g1, g2, g3 = st.columns(3)
            with g1:
                num_groups = st.number_input("Number of groups:", 1, 10, value=2)
            with g2:
                num_per_group = st.number_input("People per group:", 2, 10, value=4)
            with g3:
                add_mentors = st.checkbox("Assign mentor?", value=True)

            if st.form_submit_button("Generate Groups", type="primary", use_container_width=True):
                st.divider()
                st.subheader("✅ Generated Training Groups")
                filtered_df = df_merged.copy()
                if selected_categories:
                    filtered_df = filtered_df[filtered_df['Category'].isin(selected_categories)]
                if selected_tasks:
                    filtered_df = filtered_df[filtered_df['Task_Prefixed'].isin(selected_tasks)]
                if filtered_df.empty:
                    st.error("No participants found for the selected criteria.")
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

    with sub3:
        st.subheader("🤝 Mentor Matchmaker")
        person_summary = analytics.get('person_summary', pd.DataFrame())
        learners_list = sorted(person_summary[person_summary['Archetype'].isin(["🌱 Consistent Learner", "🎯 Needs Support"])].index.tolist())
        all_tasks = sorted(df_merged['Task_Prefixed'].unique())
        c1, c2 = st.columns(2)
        with c1:
            selected_learner = st.selectbox("Select a Learner", options=learners_list)
        with c2:
            skill_needed = st.selectbox("Select a Skill Needed", options=all_tasks)
        if st.button("Find Mentor", use_container_width=True, type="primary"):
            experts_df = df_merged[(df_merged['Task_Prefixed'] == skill_needed) & (df_merged['Name'] != selected_learner) & (df_merged['Score'] >= 0.8)]
            if experts_df.empty:
                st.error(f"No suitable mentors found for the skill: **{skill_needed}**.")
            else:
                st.success(f"Top Mentor Recommendations for **{selected_learner}** in **{skill_needed}**")
                recs = experts_df.sort_values(by="Score", ascending=False).head(3)
                recs = recs.merge(analytics.get('person_summary'), left_on='Name', right_index=True, how='left')
                st.dataframe(recs[['Name', 'Archetype', 'Score']], hide_index=True, use_container_width=True,
                             column_config={"Score": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1)})


def render_team_profiles(df_merged, user_df, analytics):
    st.header("👤 Team Profiles")
    person_summary = analytics.get('person_summary', pd.DataFrame())

    col1, col2 = st.columns([1, 2], gap="large")
    with col1:
        with st.container(border=True):
            st.subheader("📇 Team Roster")
            all_user_names_list = sorted(user_df['Name'].unique())
            selected_person = st.selectbox("Select a Team Member", all_user_names_list, label_visibility="collapsed")
            ranking_df = person_summary.reset_index().sort_values('Avg Score', ascending=False)
            ranking_df['Rank'] = ranking_df['Avg Score'].rank(method='min', ascending=False).astype(int)
            merged_ranking = user_df[['Name']].merge(ranking_df, on='Name', how='left')
            merged_ranking['Assessed'] = merged_ranking['Name'].isin(set(df_merged['Name'].unique()))
            st.dataframe(merged_ranking, height=750, hide_index=True,
                         column_config={"Assessed": st.column_config.CheckboxColumn("Assessed?", disabled=True),
                                        "Avg Score": st.column_config.ProgressColumn("Avg Score", format="%.1f%%", min_value=0, max_value=1)})

    with col2:
        with st.container(border=True):
            st.header(f"📇 Profile: {selected_person}")
            if selected_person not in set(df_merged['Name'].unique()):
                st.warning(f"**{selected_person} has not completed the self-assessment.**")
            else:
                person_stats = person_summary.loc[selected_person]
                person_data = df_merged[df_merged['Name'] == selected_person].copy()
                rank_val = person_summary.reset_index().sort_values('Avg Score', ascending=False).set_index('Name').index.get_loc(selected_person) + 1
                c1, c2, c3 = st.columns(3)
                c1.metric("Overall Rank", f"#{rank_val}")
                c2.metric("Average Score", f"{person_stats['Avg Score']:.1%}")
                c3.metric("Archetype", person_stats['Archetype'])
                st.divider()
                team_avg = df_merged.groupby('Category')['Score'].mean()
                person_avg = person_data.groupby('Category')['Score'].mean().reindex(team_avg.index, fill_value=0)
                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(r=person_avg.values, theta=person_avg.index, fill='toself', name=f'{selected_person}'))
                fig.add_trace(go.Scatterpolar(r=team_avg.values, theta=team_avg.index, fill='toself', name='Team Avg', opacity=0.6))
                st.plotly_chart(fig, use_container_width=True)
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

        with st.expander("📄 View Full Software & Feedback Details", expanded=False):
            user_info = user_df[user_df['Name'] == selected_person].iloc[0]
            st.markdown(f"**Team Leader:** {user_info.get('Team Leader', 'N/A')}  |  **Grid:** {user_info.get('Grid', 'N/A')}")
            st.markdown(f"**Scheduler Tag:** {'Yes' if user_info.get('Scheduler tag') else 'No'}")
            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Affinity Status**")
                st.markdown(f"- License Active: {'✅' if user_info.get('Active License') else '❌'}")
                if pd.notna(user_info.get('License Expiration')):
                    st.markdown(f"- Expires: {user_info.get('License Expiration').strftime('%d-%b-%Y')}")
                st.markdown(f"- McK Training: {'✅' if user_info.get('Has received Affinity training of McK?') else '❌'}")
            with c2:
                st.markdown("**Experience & Comments**")
                st.info(f"**Experience:** {user_info.get('Experience', 'N/A')}")
                st.info(f"**Confidence w/ MM:** {user_info.get('Confidence with MM', 'N/A')}")
                st.warning(f"**Comments:** {user_info.get('Comments', 'N/A')}")


def render_skill_analysis(df_merged, analytics):
    st.header("🧠 Skill Analysis")
    skill_corr_matrix = analytics.get('skill_correlation', pd.DataFrame())

    sub1, sub2, sub3 = st.tabs(["📊 Skill Distribution", "🏆 Talent Composition", "🕸️ Skill Correlation"])
    with sub1:
        st.subheader("Deep Dive by Skill or Category")
        analysis_type = st.radio("Analyze by:", ["Category", "Task"], horizontal=True)
        if analysis_type == "Task":
            options, label, filter_col = sorted(df_merged['Task_Prefixed'].unique()), "Select Task(s)", 'Task_Prefixed'
        else:
            options, label, filter_col = sorted(df_merged['Category'].unique()), "Select Category(s)", 'Category'
        selected = st.multiselect(label, options, default=options[0] if options else None)
        if not selected:
            st.warning(f"Please select at least one {analysis_type}.")
        else:
            skill_data = df_merged[df_merged[filter_col].isin(selected)]
            c1, c2, c3 = st.columns(3)
            c1.metric("Avg Confidence", f"{skill_data['Score'].mean():.1%}")
            c2.metric("Experts (≥80%)", skill_data[skill_data['Score'] >= 0.8]['Name'].nunique())
            c3.metric("Beginners (<40%)", skill_data[skill_data['Score'] < 0.4]['Name'].nunique())
            st.divider()
            s1, s2 = st.columns(2)
            with s1:
                st.markdown("**Skill Leaderboard**")
                st.dataframe(skill_data.groupby('Name')['Score'].mean().sort_values(ascending=False).reset_index(), hide_index=True,
                             column_config={"Score": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1)})
            with s2:
                st.markdown("**Score Distribution**")
                fig = px.histogram(skill_data, x='Score', nbins=10)
                fig.update_layout(height=350, margin=dict(t=20, b=20), showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

    with sub2:
        st.subheader("Talent Composition")
        hidden_stars = analytics.get('hidden_stars', pd.DataFrame())
        adjusted_ranking = analytics.get('adjusted_ranking', pd.DataFrame())
        c1, c2 = st.columns([1, 2], gap="large")
        with c1:
            with st.container(border=True):
                st.markdown("**🌟 Hidden Stars**")
                if hidden_stars.empty:
                    st.info("No 'Hidden Stars' found.")
                else:
                    st.dataframe(hidden_stars[['Name', 'Task_Prefixed', 'Score']], hide_index=True, height=300)
        with c2:
            with st.container(border=True):
                st.markdown("**🧗 Adjusted Difficulty Ranking**")
                st.dataframe(adjusted_ranking, hide_index=True, height=350,
                             column_config={"Adjusted Score": st.column_config.BarChartColumn("Adjusted Score", y_min=0)})

    with sub3:
        st.subheader("Skill Correlation Heatmap")
        if not skill_corr_matrix.empty:
            fig = px.imshow(skill_corr_matrix, text_auto=".2f", aspect="auto")
            fig.update_layout(height=600, title="Skill Correlation Matrix")
            st.plotly_chart(fig, use_container_width=True)


def render_team_dna(df_merged, analytics):
    st.header("🧬 Team DNA & Dynamics")
    st.info("Analysis of team composition and distinctive characteristics.")

    person_summary = analytics.get('person_summary', pd.DataFrame())

    st.subheader("🔬 Team Skill Fingerprint")
    all_teams = sorted([t for t in person_summary['Team Leader'].unique() if t])
    if all_teams:
        selected_team = st.selectbox("Select a Team Leader", all_teams)
        if selected_team:
            team_members = person_summary[person_summary['Team Leader'] == selected_team].index
            team_data = df_merged[df_merged['Name'].isin(team_members)]
            team_fingerprint = team_data.groupby('Category')['Score'].quantile(0.75)
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=team_fingerprint.values, theta=team_fingerprint.index, fill='toself', name='Advanced Competency (75th Percentile)'))
            fig.update_layout(title=f"Skill Fingerprint – {selected_team}", polar=dict(radialaxis=dict(visible=True, range=[0, 1])))
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No team leader data available.")

    st.divider()
    st.subheader("📊 Archetype Composition by Team")
    if 'Team Leader' in person_summary.columns and not person_summary['Team Leader'].isnull().all():
        archetype_dist = person_summary.groupby(['Team Leader', 'Archetype']).size().unstack(fill_value=0)
        archetype_dist_pct = archetype_dist.apply(lambda x: x * 100 / sum(x), axis=1)
        fig = px.bar(archetype_dist_pct, x=archetype_dist_pct.index, y=archetype_dist_pct.columns, title="Archetype Composition by Team (%)")
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("🏷️ 'Scheduler Tag' Analysis")
    col1, col2 = st.columns(2)
    scheduler_data = df_merged.copy()
    with col1:
        st.markdown("**Skill Profile (WITH Scheduler Tag)**")
        with_tag = scheduler_data[scheduler_data['Scheduler tag'] == True].groupby('Category')['Score'].mean()
        if not with_tag.empty:
            st.plotly_chart(px.bar(with_tag, orientation='h'), use_container_width=True)
        else:
            st.info("No data for people with 'Scheduler Tag'.")
    with col2:
        st.markdown("**Skill Profile (WITHOUT Scheduler Tag)**")
        without_tag = scheduler_data[scheduler_data['Scheduler tag'] == False].groupby('Category')['Score'].mean()
        if not without_tag.empty:
            st.plotly_chart(px.bar(without_tag, orientation='h'), use_container_width=True)
        else:
            st.info("No data for people without 'Scheduler Tag'.")


def render_risk_opportunity(analytics):
    st.header("🔭 Risk & Opportunity Forecaster")
    st.info("Proactive identification of talent risks and development opportunities.")

    risk_matrix = analytics.get('risk_matrix', pd.DataFrame())
    talent_pipeline = analytics.get('talent_pipeline', pd.DataFrame())

    st.subheader("🚨 Talent Risk Matrix")
    if not risk_matrix.empty:
        def highlight_risks(row):
            styles = [''] * len(row)
            if row['SPOF']:
                styles[row.index.get_loc('Expert_Count')] = 'background-color: orange'
            if row['Expiration Risk']:
                styles[row.index.get_loc('Expiration Risk')] = 'background-color: red; color: white'
            return styles
        risk_df_display = risk_matrix.reset_index()[['Task_Prefixed', 'Avg_Score', 'Expert_Count', 'SPOF', 'Expiration Risk']]
        st.dataframe(risk_df_display.style.apply(highlight_risks, axis=1).format({'Avg_Score': "{:.1%}"}), use_container_width=True)
        st.caption("🟧 Orange: Single Point of Failure (SPOF). 🔴 Red: Key expert license expires soon.")

    st.divider()
    st.subheader("🌱 Talent Pipeline")
    if not talent_pipeline.empty:
        st.dataframe(talent_pipeline, use_container_width=True, hide_index=True,
                     column_config={"Score": st.column_config.ProgressColumn("Current Confidence", format="%.1f%%", min_value=0, max_value=1)})
    else:
        st.success("✅ No current candidates identified for the pipeline.")


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
            except KeyError:
                st.error("Secrets not configured on the server. Contact the administrator.")
