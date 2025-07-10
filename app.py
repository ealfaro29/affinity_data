# --- app_final_english.py ---
# Version 6.5: Added a simple, secure login page.

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime, timedelta
from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt
import re

# ==============================================================================
#                                  PAGE CONFIG
# ==============================================================================
# This must be the first Streamlit command.
st.set_page_config(
    page_title="Team Skills Hub 6.5",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
#                                  DATA ENGINE
# ==============================================================================
@st.cache_data
def load_skills_data(csv_path):
    """
    Loads and processes skills data. This version contains the definitive fix
    for the AttributeError by iterating through columns to calculate parsing errors.
    """
    try:
        df = pd.read_csv(csv_path, sep=';', header=[0, 1, 2], index_col=[0, 1], encoding='utf-8', on_bad_lines='skip')
    except Exception:
        try:
             df = pd.read_csv(csv_path, sep=';', header=[0, 1, 2], index_col=[0, 1], encoding='latin-1', on_bad_lines='skip')
        except Exception as e:
            st.error(f"Error reading the skills file. Please check format and encoding. Error: {e}")
            return None

    cols_df = df.columns.to_frame(index=False)
    for col_name in cols_df.columns:
        cleaned_series = cols_df[col_name].astype(str).str.strip()
        cleaned_series = cleaned_series.ffill()
        cols_df[col_name] = cleaned_series
    df.columns = pd.MultiIndex.from_frame(cols_df)
    df.columns.names = ['Category', 'Skill', 'Task']
    
    df_check = df.copy()
    parsing_errors = 0
    for col in df_check.columns:
        series = df_check[col]
        series_non_null = series.dropna()
        if not series_non_null.empty:
            numeric_series = pd.to_numeric(
                series_non_null.astype(str).str.replace('%', '', regex=False).str.strip(),
                errors='coerce'
            )
            parsing_errors += numeric_series.isnull().sum()
    
    df_long = df.stack(level=['Category', 'Skill', 'Task'], dropna=False).reset_index()
    df_long.rename(columns={
        df_long.columns[0]: 'Name', 
        df_long.columns[1]: 'Specific needs', 
        df_long.columns[-1]: 'Score'
        }, inplace=True)

    df_long.dropna(subset=['Name'], inplace=True)
    df_long = df_long[df_long['Name'].str.strip() != '']
    total_names_in_file = df_long['Name'].nunique()
    df_long = df_long[df_long['Specific needs'] != 'waitlist']
    
    df_long['Score'] = pd.to_numeric(df_long['Score'].astype(str).str.replace('%', '', regex=False).str.strip(), errors='coerce') / 100
    df_long.dropna(subset=['Score'], inplace=True)

    for col in df_long.select_dtypes(include=['object']).columns:
        df_long[col] = df_long[col].fillna('')
        df_long[col] = df_long[col].str.strip()
        
    df_long['Task_Prefixed'] = '[' + df_long['Category'] + '] ' + df_long['Task']
    
    return {'data': df_long, 'total_count': total_names_in_file, 'parsing_errors': parsing_errors}

@st.cache_data
def load_user_data(csv_path):
    try: df = pd.read_csv(csv_path, sep=';', encoding='utf-8')
    except Exception:
        try: df = pd.read_csv(csv_path, sep=';', encoding='latin-1')
        except Exception as e: st.error(f"Error reading the user data file. Error: {e}"); return pd.DataFrame()
    df.rename(columns={'BPS': 'Name'}, inplace=True); df['Name'] = df['Name'].str.strip()
    bool_cols = ['Active License: Designer', 'Active License: Photo', 'Has received Affinity training of McK?', 'McK Presets installed', 'Latest Version Designer', 'Latest Version Photo']
    for col in bool_cols:
        if col in df.columns: df[col] = df[col].astype(str).str.strip().str.lower().isin(['yes', 'si', 'true', '1'])
    for col in ['Expiration Designer', 'Expiration Photo']: 
        if col in df.columns: df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
    df.fillna({'Comments': 'No comment provided.'}, inplace=True)
    return df.dropna(subset=['Name'])

@st.cache_data
def analyze_comment_themes(df_comments):
    themes = {
        'Training/Guidance': r'training|learn|course|session|refresher|guide|help|practice',
        'Isometric Skills': r'isometric|iso',
        'Photo Editing': r'photo|background|remove|color|edit|retouch',
        'Vector/Technical': r'vector|mask|clipping|rasterize|bezier|pen tool|illustrator',
        'Confidence/Experience': r'confident|beginner|expert|feel|experience|use it|long time',
        'Tools/Software': r'tool|affinity|photoshop|version|update|install'
    }
    theme_counts = {theme: 0 for theme in themes}
    all_comments = ' '.join(df_comments.dropna().unique())
    for theme, pattern in themes.items():
        theme_counts[theme] = len(re.findall(pattern, all_comments, re.IGNORECASE))
    
    return pd.DataFrame.from_dict(theme_counts, orient='index', columns=['Mentions']).sort_values('Mentions', ascending=False)


@st.cache_data
def compute_analytics(_df):
    df = _df.copy()
    if df.empty: return {}
    analytics = {}
    person_summary = df.groupby('Name')['Score'].agg(['mean', 'std']).rename(columns={'mean': 'Avg Score', 'std': 'Volatility'})
    person_summary['Rank'] = person_summary['Avg Score'].rank(ascending=False, method='min').astype(int)
    median_volatility = person_summary['Volatility'].median(); median_proficiency = person_summary['Avg Score'].median()
    def get_archetype(row):
        if pd.isna(row['Volatility']): return "🎯 Needs Support"
        if row['Avg Score'] >= median_proficiency and row['Volatility'] <= median_volatility: return "🏆 Versatile Leader"
        if row['Avg Score'] >= median_proficiency and row['Volatility'] > median_volatility: return "🌟 Niche Specialist"
        if row['Avg Score'] < median_proficiency and row['Volatility'] <= median_volatility: return "🌱 Consistent Learner"
        return "🎯 Needs Support"
    person_summary['Archetype'] = person_summary.apply(get_archetype, axis=1)
    analytics['person_summary'] = person_summary
    task_summary = df.groupby('Task_Prefixed')['Score'].agg(['mean', 'count']).rename(columns={'mean': 'Avg Score'})
    task_summary['Experts (>=80%)'] = df[df['Score'] >= 0.8].groupby('Task_Prefixed')['Name'].nunique()
    task_summary['Beginners (<40%)'] = df[df['Score'] < 0.4].groupby('Task_Prefixed')['Name'].nunique()
    task_summary.fillna(0, inplace=True); task_summary['Risk Index'] = (task_summary['Beginners (<40%)'] + 1) / (task_summary['Experts (>=80%)'] + 1)
    analytics['risk_radar'] = task_summary.sort_values(by='Risk Index', ascending=False)
    task_avg = df.groupby('Task_Prefixed')['Score'].mean(); hard_tasks = task_avg[task_avg < 0.6].index
    mid_tier_performers = person_summary[(person_summary['Avg Score'] >= 0.5) & (person_summary['Avg Score'] < 0.8)].index
    stars_df = df[(df['Name'].isin(mid_tier_performers)) & (df['Task_Prefixed'].isin(hard_tasks)) & (df['Score'] >= 0.9)].copy()
    analytics['hidden_stars'] = stars_df
    difficulty_weight = 1 - task_avg; df_adjusted = df.copy(); df_adjusted['Difficulty Weight'] = df_adjusted['Task_Prefixed'].map(difficulty_weight)
    df_adjusted['Adjusted Score'] = df_adjusted['Score'] * df_adjusted['Difficulty Weight']
    adjusted_ranking = df_adjusted.groupby('Name')['Adjusted Score'].sum().sort_values(ascending=False)
    analytics['adjusted_ranking'] = pd.DataFrame(adjusted_ranking).reset_index()
    analytics['adjusted_ranking']['Adjusted Rank'] = analytics['adjusted_ranking']['Adjusted Score'].rank(ascending=False, method='min').astype(int)
    skill_pivot = df.pivot_table(index='Name', columns='Skill', values='Score').fillna(df['Score'].mean())
    analytics['skill_correlation'] = skill_pivot.corr()
    return analytics

def main_app():
    """
    This function contains the entire Streamlit dashboard application.
    It is called only after a successful login.
    """
    # --- Sidebar (only shows after login) ---
    st.sidebar.title("🚀 Team Skills Hub")
    st.sidebar.markdown("---")
    st.sidebar.info("A strategic platform for talent intelligence and team development.")
    st.sidebar.markdown("---")
    
    # --- Main data loading and processing flow ---
    skills_file_path = Path(__file__).parent / "selfAssessment.csv"
    user_file_path = Path(__file__).parent / "userData.csv"
    skills_load_result = load_skills_data(skills_file_path)
    if skills_load_result is None: st.error("Dashboard cannot be loaded without the skills file."); st.stop()
    df_long = skills_load_result['data']
    total_participants_in_file = skills_load_result['total_count']
    score_parsing_errors = skills_load_result['parsing_errors']
    active_participants_count = df_long['Name'].nunique()
    user_df = load_user_data(user_file_path)
    if user_df.empty: st.warning("`userData.csv` could not be loaded. Some functionalities will be limited.");
    df_merged = pd.merge(df_long, user_df, on='Name', how='left') if not user_df.empty else df_long
    if df_merged.empty: st.warning("No participants with valid scores were found."); st.stop()
    analytics = compute_analytics(df_merged); person_summary = analytics.get('person_summary', pd.DataFrame()); risk_radar = analytics.get('risk_radar', pd.DataFrame())

    # ==============================================================================
    #                                  APP LAYOUT
    # ==============================================================================
    st.title("🚀 Team Skills & Affinity Hub")
    with st.expander("ℹ️ How to Use This Dashboard", expanded=False):
        st.markdown("""
            - **📈 Strategic Overview:** Quick diagnostic of the team's skill health, data quality, and key risks.
            - **⭐ Affinity Status:** Operational view of licenses, training, and software status.
            - **🗺️ Action Playbook:** Design high-impact training sessions and create smart groups.
            - **👤 Team Profiles:** Explore and compare the detailed profile of each team member.
            - **🧠 Skill Analysis:** Deep dive into talent composition and skill performance.
        """)

    # Reordered tabs based on user feedback for a more logical workflow
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Strategic Overview", "⭐ Affinity Status", "🗺️ Action Playbook", "👤 Team Profiles", "🧠 Skill Analysis"])

    # ========================== TAB 1: STRATEGIC OVERVIEW ==============================
    with tab1:
        st.header("📈 Strategic Overview")
        col1, col2 = st.columns(2, gap="large")
        with col1:
            with st.container(border=True):
                st.subheader("📊 Team Vital Signs")
                kpi1, kpi2, kpi3 = st.columns(3)
                kpi1.metric("People in File", total_participants_in_file)
                kpi2.metric("Active Participants", active_participants_count, f"{active_participants_count / total_participants_in_file:.0%} Response Rate")
                kpi3.metric("Average Confidence", f"{df_merged['Score'].mean():.1%}")
                
                st.markdown("**Talent Archetype Distribution**")
                archetype_counts = person_summary['Archetype'].value_counts()
                fig_pie = px.pie(archetype_counts, values=archetype_counts.values, names=archetype_counts.index, hole=0.5, color_discrete_map={"🏆 Versatile Leader": "#1f77b4", "🌟 Niche Specialist": "#ff7f0e", "🌱 Consistent Learner": "#2ca02c", "🎯 Needs Support": "#d62728"})
                fig_pie.update_traces(hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>')
                fig_pie.update_layout(height=300, margin=dict(t=30, b=20, l=0, r=0), legend_orientation="h"); st.plotly_chart(fig_pie, use_container_width=True)
        with col2:
             with st.container(border=True):
                st.subheader("🩺 Data Health Check")
                assessed_names = set(df_long['Name'].unique())
                all_user_names = set(user_df['Name'].unique()) if not user_df.empty else assessed_names
                pending_assessment_names = all_user_names - assessed_names
                
                st.metric("Self-Assessment Response Rate", f"{len(assessed_names)} / {len(all_user_names)}", f"{len(pending_assessment_names)} pending")
                st.metric("Score Data Quality", f"{score_parsing_errors} invalid entries", "Found in file", delta_color="off")
                with st.expander(f"View {len(pending_assessment_names)} people pending assessment"):
                    if pending_assessment_names:
                        st.dataframe(user_df[user_df['Name'].isin(pending_assessment_names)][['Name', 'Team Leader']], hide_index=True)
                    else:
                        st.info("All users have completed the assessment.")

        st.divider()

        col1, col2 = st.columns(2, gap="large")
        with col1:
            with st.container(border=True):
                st.subheader("🚨 Skill Risk Radar", help="Calculated as (Beginners + 1) / (Experts + 1). A higher index indicates a riskier skill with a knowledge gap.")
                st.caption("Top 5 tasks with the highest risk (few experts, many beginners).")
                for index, row in risk_radar.head(5).iterrows():
                    st.metric(label=row.name, value=f"{row['Avg Score']:.1%} Avg. Confidence", delta=f"Risk Index: {row['Risk Index']:.2f}", delta_color="inverse")

        with col2:
            with st.container(border=True):
                st.subheader("📡 Comparative Risk Profile")
                st.caption("Compares top 5 risk areas across key metrics.")
                risk_data_head = risk_radar.head(5).reset_index()
                fig_radar = go.Figure()
                
                categories = ['Avg Score', 'Risk Index', 'Experts (>=80%)', 'Beginners (<40%)']
                normalized_data = risk_data_head[categories].copy()
                for cat in categories:
                     if (risk_radar[cat].max() - risk_radar[cat].min()) > 0:
                        normalized_data[cat] = (risk_data_head[cat] - risk_radar[cat].min()) / (risk_radar[cat].max() - risk_radar[cat].min())
                     else:
                        normalized_data[cat] = 0.5

                for i, row in risk_data_head.iterrows():
                    fig_radar.add_trace(go.Scatterpolar(
                        r=normalized_data.loc[i, categories].values,
                        theta=categories,
                        fill='toself',
                        name=row['Task_Prefixed'][:40] + "...",
                        hovertemplate=f"<b>{row['Task_Prefixed']}</b><br>Risk Index: {row['Risk Index']:.2f}<br>Avg Score: {row['Avg Score']:.1%}<extra></extra>"
                    ))
                
                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=False, range=[0, 1])),
                    showlegend=True, height=350, margin=dict(l=40, r=40, t=60, b=40)
                )
                st.plotly_chart(fig_radar, use_container_width=True)

    # ========================== TAB 2: AFFINITY STATUS ==============================
    with tab2:
        st.header("⭐ Affinity Status & Team Feedback")
        if user_df.empty:
            st.error("This section requires the `userData.csv` file to be loaded correctly.")
        else:
            with st.container(border=True):
                st.subheader("📊 Overall Software Status")
                kpi1, kpi2, kpi3 = st.columns(3)
                total_users = len(user_df)
                kpi1.metric("Active Designer Licenses", f"{user_df['Active License: Designer'].sum()}", f"{user_df['Active License: Designer'].sum()/total_users:.0%} of team")
                kpi2.metric("Active Photo Licenses", f"{user_df['Active License: Photo'].sum()}", f"{user_df['Active License: Photo'].sum()/total_users:.0%} of team")
                kpi3.metric("Received McK Training", f"{user_df['Has received Affinity training of McK?'].sum()}", f"{user_df['Has received Affinity training of McK?'].sum()/total_users:.0%} of team")
            
            st.write("")
            with st.container(border=True):
                st.subheader("🚨 License Expiration Timeline")
                st.caption("Visual timeline of licenses expiring. Red indicates expiration within 30 days, yellow within 90 days.")
                today = datetime.now()
                exp_df = user_df[(user_df['Expiration Designer'].notna()) | (user_df['Expiration Photo'].notna())].copy()
                
                tasks = []
                for _, row in exp_df.iterrows():
                    if pd.notna(row['Expiration Designer']):
                        days_left = (row['Expiration Designer'] - today).days
                        color = "#d62728" if days_left < 30 else ("#ffdd57" if days_left < 90 else "#2ca02c")
                        tasks.append(dict(Task=row['Name'], Start=today, Finish=row['Expiration Designer'], Resource="Designer", Color=color))
                    if pd.notna(row['Expiration Photo']):
                        days_left = (row['Expiration Photo'] - today).days
                        color = "#d62728" if days_left < 30 else ("#ffdd57" if days_left < 90 else "#2ca02c")
                        tasks.append(dict(Task=row['Name'], Start=today, Finish=row['Expiration Photo'], Resource="Photo", Color=color))

                if not tasks:
                    st.success("✅ No license expiration data found.")
                else:
                    timeline_df = pd.DataFrame(tasks)
                    fig_timeline = px.timeline(timeline_df, x_start="Start", x_end="Finish", y="Task", color="Resource",
                                               color_discrete_map={"Designer":"#1f77b4", "Photo":"#ff7f0e"})
                    fig_timeline.update_traces(marker_color=timeline_df['Color'])
                    fig_timeline.update_layout(xaxis_title="Expiration Date", yaxis_title="Team Member", showlegend=True, height=400)
                    st.plotly_chart(fig_timeline, use_container_width=True)

            st.write("")
            with st.container(border=True):
                st.subheader("🗣️ Team Feedback Analysis")
                comment_col1, comment_col2 = st.columns([2, 3])
                with comment_col1:
                    st.markdown("**Key Themes from Comments**")
                    st.caption("Frequency of keywords related to common themes in all comments.")
                    all_comments_df = pd.concat([user_df['Comments'].dropna(), df_merged['Specific needs'].dropna()])
                    theme_counts = analyze_comment_themes(all_comments_df)
                    fig_themes = px.bar(theme_counts, x='Mentions', y=theme_counts.index, orientation='h', text_auto=True)
                    fig_themes.update_layout(showlegend=False, yaxis_title=None, height=300, margin=dict(t=20, b=20))
                    st.plotly_chart(fig_themes, use_container_width=True)
                with comment_col2:
                    st.markdown("**Comments & Specific Needs**")
                    st.dataframe(df_merged[['Name', 'Comments', 'Specific needs']].drop_duplicates(subset=['Name']), height=300, hide_index=True)


    # ======================= TAB 3: ACTION PLAYBOOK ========================
    with tab3:
        st.header("🗺️ Action Playbook")
        playbook_tab1, playbook_tab2, playbook_tab3 = st.tabs(["💡 Training Combo Generator", "👥 Group Builder", "🤝 Mentor Matchmaker"])
        with playbook_tab1:
            st.subheader("💡 Training Combo Generator")
            st.markdown("Select a primary skill, and the system will suggest other highly correlated skills to create powerful 'training combos'.")
            with st.container(border=True):
                primary_task = st.selectbox("Select a Primary Skill", options=risk_radar.index.tolist())
                primary_skill_series = df_merged[df_merged['Task_Prefixed'] == primary_task]['Skill']
                if not primary_skill_series.empty:
                    primary_skill = primary_skill_series.iloc[0]; skill_corr_matrix = analytics.get('skill_correlation', pd.DataFrame())
                    if not skill_corr_matrix.empty and primary_skill in skill_corr_matrix:
                        synergies = skill_corr_matrix[primary_skill].sort_values(ascending=False).drop(primary_skill).head(3)
                        st.success(f"**Suggested Training Module for: {primary_skill}**")
                        st.markdown(f"**1. Primary Focus:** `{primary_task}`")
                        st.markdown("**2. High-Synergy Skills:**")
                        for skill, corr in synergies.items(): st.markdown(f"- **{skill}** (Correlation: {corr:.2f})")
        with playbook_tab2:
            st.subheader("👥 Custom Training Group Builder")
            st.markdown("Create custom training groups by filtering for participants with specific development needs.")
            with st.form("group_builder_form"):
                st.markdown("**Step 1: Define the Target Skill Area (use multi-select)**")
                all_categories = sorted(df_merged['Category'].unique())
                selected_categories = st.multiselect("Filter by Category", all_categories, default=all_categories[0] if all_categories else None)
                
                if selected_categories:
                    task_options = sorted(df_merged[df_merged['Category'].isin(selected_categories)]['Task_Prefixed'].unique())
                    selected_tasks = st.multiselect("Filter by Task (Optional)", task_options)
                else:
                    selected_tasks = []
                    st.info("Select at least one category to see task options.")

                st.markdown("**Step 2: Configure the Groups**")
                g_col1, g_col2, g_col3 = st.columns(3)
                with g_col1: num_groups = st.number_input("Number of groups:", 1, 10, value=2)
                with g_col2: num_per_group = st.number_input("People per group:", 2, 10, value=4)
                with g_col3: add_mentors = st.checkbox("Assign mentor?", value=True, help="Assigns the highest-scorer as a mentor to each group.")
                
                if submitted := st.form_submit_button("Generate Groups", type="primary", use_container_width=True):
                    st.divider(); st.subheader("✅ Generated Training Groups")
                    filtered_df = df_merged.copy()
                    if selected_categories: filtered_df = filtered_df[filtered_df['Category'].isin(selected_categories)]
                    if selected_tasks: filtered_df = filtered_df[filtered_df['Task_Prefixed'].isin(selected_tasks)]
                    
                    if filtered_df.empty:
                        st.error("No participants found for the selected criteria. Please broaden your filters.")
                    else:
                        group_scores = filtered_df.groupby('Name')['Score'].mean().sort_values()
                        mentors = group_scores[group_scores >= 0.8].sort_values(ascending=False); learners = group_scores[group_scores < 0.8].sort_values(ascending=True)
                        cols = st.columns(num_groups); assigned_people = set()
                        for i in range(num_groups):
                            with cols[i]:
                                with st.container(border=True):
                                    st.markdown(f"**Group {i+1}**"); group_data = []
                                    if add_mentors and not (available_mentors := mentors[~mentors.index.isin(assigned_people)]).empty:
                                        mentor_name = available_mentors.index[0]; group_data.append({'Role': '🏆 Mentor', 'Name': mentor_name, 'Score': f"{available_mentors.iloc[0]:.1%}"}); assigned_people.add(mentor_name)
                                    learners_needed = num_per_group - len(group_data)
                                    group_learners = learners[~learners.index.isin(assigned_people)].head(learners_needed)
                                    for name, score in group_learners.items(): group_data.append({'Role': '🌱 Learner', 'Name': name, 'Score': f"{score:.1%}"}); assigned_people.add(name)
                                    if group_data: st.dataframe(pd.DataFrame(group_data), hide_index=True, use_container_width=True)
                                    else: st.warning(f"Not enough people to form Group {i+1}.")
        
        with playbook_tab3:
            st.subheader("🤝 Mentor Matchmaker")
            st.markdown("Find the best mentor for a specific learner and skill.")
            with st.container(border=True):
                learners_list = sorted(person_summary[person_summary['Archetype'].isin(["🌱 Consistent Learner", "🎯 Needs Support"])].index.tolist())
                all_tasks = sorted(df_merged['Task_Prefixed'].unique())
                
                col1, col2 = st.columns(2)
                with col1:
                    selected_learner = st.selectbox("Select a Learner", options=learners_list)
                with col2:
                    skill_needed = st.selectbox("Select a Skill Needed", options=all_tasks)

                if st.button("Find Mentor", use_container_width=True, type="primary"):
                    experts_df = df_merged[df_merged['Task_Prefixed'] == skill_needed].copy()
                    experts_df = experts_df[experts_df['Name'] != selected_learner]
                    experts_df = experts_df[experts_df['Score'] >= 0.8]
                    
                    if experts_df.empty:
                        st.error(f"No suitable mentors found for the skill: **{skill_needed}**.")
                    else:
                        st.success(f"Top Mentor Recommendations for **{selected_learner}** in **{skill_needed}**")
                        recommendations = experts_df.sort_values(by="Score", ascending=False).head(3)
                        recommendations = pd.merge(recommendations[['Name', 'Score']], person_summary[['Archetype']], on='Name', how='left')
                        st.dataframe(recommendations[['Name', 'Archetype', 'Score']], hide_index=True, use_container_width=True, column_config={"Score": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1)})


    # ========================== TAB 4: TEAM PROFILES ==============================
    with tab4:
        st.header("👤 Team Profiles")
        col1, col2 = st.columns([1, 2], gap="large")
        with col1:
            with st.container(border=True):
                st.subheader("📇 Team Roster")
                all_user_names_list = sorted(list(user_df['Name'].unique())) if not user_df.empty else sorted(list(df_long['Name'].unique()))
                selected_person = st.selectbox("Select a Team Member", all_user_names_list, label_visibility="collapsed")
                ranking_df = person_summary.sort_values('Rank').reset_index()
                merged_ranking = pd.merge(user_df[['Name']], ranking_df, on='Name', how='left') if not user_df.empty else ranking_df
                merged_ranking['Assessed'] = merged_ranking['Name'].isin(set(df_long['Name'].unique()))
                st.dataframe(merged_ranking, height=750, hide_index=True, column_config={"Assessed": st.column_config.CheckboxColumn("Assessed?", disabled=True), "Avg Score": st.column_config.ProgressColumn("Avg Score", format="%.1f%%", min_value=0, max_value=1)})
        
        with col2:
            with st.container(border=True):
                st.header(f"📇 Profile: {selected_person}")
                if selected_person not in set(df_long['Name'].unique()):
                    st.warning(f"**{selected_person} has not completed the self-assessment.** Skill analytics are not available.")
                else:
                    person_stats = person_summary.loc[selected_person]; person_data = df_merged[df_merged['Name'] == selected_person].copy()
                    c1, c2, c3 = st.columns(3); c1.metric("Overall Rank", f"#{int(person_stats['Rank'])}"); c2.metric("Average Score", f"{person_stats['Avg Score']:.1%}"); c3.metric("Archetype", person_stats['Archetype'])
                    st.divider()
                    team_avg = df_merged.groupby('Category')['Score'].mean(); person_avg = person_data.groupby('Category')['Score'].mean().reindex(team_avg.index, fill_value=0)
                    fig_radar = go.Figure(); fig_radar.add_trace(go.Scatterpolar(r=person_avg.values, theta=person_avg.index, fill='toself', name=f'{selected_person}'))
                    fig_radar.add_trace(go.Scatterpolar(r=team_avg.values, theta=team_avg.index, fill='toself', name='Team Avg', opacity=0.6))
                    fig_radar.update_layout(title="Performance vs. Team Average", height=350, margin=dict(l=40, r=40, t=60, b=40)); st.plotly_chart(fig_radar, use_container_width=True)
                    st.markdown("**Strengths & Development Areas**")
                    person_skills = person_data.sort_values('Score', ascending=False).drop_duplicates(subset=['Task_Prefixed'])
                    sub_col1, sub_col2 = st.columns(2)
                    with sub_col1:
                        st.markdown("✅ **Top 5 Skills**"); st.dataframe(person_skills.head(5)[['Task_Prefixed', 'Score']], hide_index=True, column_config={"Score": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1)})
                    with sub_col2:
                        st.markdown("🌱 **Top 5 Improvement Areas**"); st.dataframe(person_skills.tail(5)[['Task_Prefixed', 'Score']], hide_index=True, column_config={"Score": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1)})
            
            if not user_df.empty and selected_person in user_df['Name'].values:
                with st.expander("📄 View Full Software & Feedback Details", expanded=False):
                    user_info = user_df.loc[user_df['Name'] == selected_person].iloc[0]
                    st.markdown(f"**Team Leader:** {user_info.get('Team Leader', 'N/A')}  |  **Grid:** {user_info.get('Grid', 'N/A')}")
                    st.divider()
                    st.markdown("**License & Version Status**")
                    lic_col1, lic_col2 = st.columns(2)
                    with lic_col1: 
                        st.markdown(f"**Designer License:** {'✅ Active' if user_info.get('Active License: Designer', False) else '❌ Inactive'}")
                        st.markdown(f"**Latest Designer Version:** {'✅ Yes' if user_info.get('Latest Version Designer', False) else '❌ No'}")
                    with lic_col2:
                        st.markdown(f"**Photo License:** {'✅ Active' if user_info.get('Active License: Photo', False) else '❌ Inactive'}")
                        st.markdown(f"**Latest Photo Version:** {'✅ Yes' if user_info.get('Latest Version Photo', False) else '❌ No'}")
                    st.divider()
                    st.markdown("**Training & Setup Status**")
                    train_col1, train_col2 = st.columns(2)
                    with train_col1:
                        st.markdown(f"**McK Training:** {'✅ Received' if user_info.get('Has received Affinity training of McK?', False) else '❌ Not received'}")
                    with train_col2:
                        st.markdown(f"**McK Presets:** {'✅ Installed' if user_info.get('McK Presets installed', False) else '❌ Not installed'}")
                    if pd.notna(user_info.get('Other training')) and user_info.get('Other training', ''): st.info(f"**Other Training:** *{user_info.get('Other training', '').strip()}*")
                    if pd.notna(user_info.get('Comments')) and user_info.get('Comments', '').strip() not in ['No comment provided.', '']: st.info(f"**Personal Comment:** *\"{user_info.get('Comments', '').strip()}\"*")

    # ========================== TAB 5: SKILL ANALYSIS ==============================
    with tab5:
        st.header("🧠 Skill Analysis")
        subtab1, subtab2, subtab3 = st.tabs(["📊 Skill Distribution", "🏆 Talent Composition", "🕸️ Skill Correlation"])
        with subtab1:
            st.subheader("Deep Dive by Skill or Category")
            with st.container(border=True):
                analysis_type = st.radio("Analyze by:", ["Category", "Task"], horizontal=True)
                
                if analysis_type == "Task":
                    options = sorted(df_merged['Task_Prefixed'].unique())
                    label = "Select Task(s)"
                    filter_col = 'Task_Prefixed'
                else:
                    options = sorted(df_merged['Category'].unique())
                    label = "Select Category(s)"
                    filter_col = 'Category'

                selected_items = st.multiselect(label, options, default=options[0] if options else None)
                
                if not selected_items:
                    st.warning(f"Please select at least one {analysis_type}.")
                else:
                    skill_data = df_merged[df_merged[filter_col].isin(selected_items)]
                    st.markdown(f"#### Competency Profile for: {', '.join(selected_items)}")
                    c1, c2, c3 = st.columns(3); c1.metric("Avg Confidence", f"{skill_data['Score'].mean():.1%}")
                    c2.metric("Experts (≥80%)", skill_data[skill_data['Score'] >= 0.8]['Name'].nunique())
                    c3.metric("Beginners (<40%)", skill_data[skill_data['Score'] < 0.4]['Name'].nunique())
                    st.divider()
                    c1_s, c2_s = st.columns(2)
                    with c1_s:
                        st.markdown("**Skill Leaderboard**"); skill_ranking = skill_data.groupby('Name')['Score'].mean().sort_values(ascending=False).reset_index()
                        st.dataframe(skill_ranking, hide_index=True, column_config={"Score": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1)})
                    with c2_s:
                        st.markdown("**Score Distribution**"); fig = px.histogram(skill_data, x='Score', nbins=10)
                        fig.update_layout(height=350, margin=dict(t=20, b=20), showlegend=False); st.plotly_chart(fig, use_container_width=True)

        with subtab2:
            st.subheader("Talent Composition")
            col1, col2 = st.columns([1, 2], gap="large")
            with col1:
                with st.container(border=True):
                    st.markdown("**🌟 Hidden Stars**")
                    st.caption("Mid-tier performers who excel at the team's hardest tasks.")
                    hidden_stars = analytics.get('hidden_stars', pd.DataFrame())
                    if hidden_stars.empty: st.info("No 'Hidden Stars' found.")
                    else: st.dataframe(hidden_stars[['Name', 'Task_Prefixed', 'Score']], hide_index=True, height=300)
            with col2:
                with st.container(border=True):
                    st.markdown("**🧗 Adjusted Difficulty Ranking**", help="This ranking rewards performance on more difficult tasks (i.e., tasks where the team average is lower). It's calculated by weighting each person's score by the task's difficulty.")
                    st.caption("Identifies tough-problem solvers.")
                    adj_ranking = analytics.get('adjusted_ranking', pd.DataFrame())
                    st.dataframe(adj_ranking, hide_index=True, height=350, column_config={"Adjusted Score": st.column_config.BarChartColumn("Adjusted Score", y_min=0)})
        
        with subtab3:
            st.subheader("Skill Correlation Heatmap")
            with st.container(border=True):
                st.markdown("This heatmap shows which skills are most frequently learned together. Bright squares indicate a strong positive correlation, suggesting that people who are good at one skill are often good at the other. This is useful for creating 'training combos'.")
                skill_corr_matrix = analytics.get('skill_correlation', pd.DataFrame())
                if not skill_corr_matrix.empty:
                    fig_heatmap = px.imshow(skill_corr_matrix, text_auto=".2f", aspect="auto", color_continuous_scale='RdYlBu')
                    fig_heatmap.update_layout(height=600, title="Skill Correlation Matrix")
                    st.plotly_chart(fig_heatmap, use_container_width=True)

def login_page():
    """Displays the login page and handles authentication."""
    st.title("🔐 Team Skills Hub Login")
    
    with st.form("login_form"):
        username = st.text_input("Username").lower()
        password = st.text_input("PIN", type="password")
        submitted = st.form_submit_button("Log In")

        if submitted:
            if username == "admin" and password == "235412":
                st.session_state.logged_in = True
                st.rerun()  # Rerun the script to show the main app
            else:
                st.error("Incorrect username or PIN. Please try again.")

# ==============================================================================
#                                  MAIN SCRIPT FLOW
# ==============================================================================

# Initialize session state for login
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Check login status and display appropriate page
if st.session_state.logged_in:
    main_app()
else:
    login_page()