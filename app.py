# --- app_final_v8.3_keyerror_fix_scheduler.py ---
# Versión 8.3: Corrige el KeyError de 'Scheduler tag' en la pestaña Team DNA.

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import re

# ==============================================================================
#                                  CONFIGURATION TOGGLE
# ==============================================================================
# Set to True to bypass the login screen for development.
# Set to False to enable the st.secrets login for production.
DEVELOPMENT_MODE = True

# ==============================================================================
#                                  PAGE CONFIG
# ==============================================================================
st.set_page_config(
    page_title="Team Skills Hub 8.3",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
#                                  DATA ENGINE
# ==============================================================================
@st.cache_data
def load_and_process_data(user_csv_path, tasks_json_path):
    # Carga de datos
    try:
        tasks_df = pd.read_json(tasks_json_path)['skills'].apply(pd.Series)
        tasks_df.rename(columns={'title': 'Task', 'id': 'task_id'}, inplace=True)
    except Exception as e:
        st.error(f"Error crítico al leer tasks.json: {e}"); return None

    try:
        user_df = pd.read_csv(user_csv_path, sep=';', encoding='utf-8-sig')
    except Exception as e:
        st.error(f"Error crítico al leer userData.csv: {e}"); return None

    # Limpieza y renombrado
    user_df.columns = user_df.columns.str.strip()
    user_df.rename(columns={
        'BPS': 'Name',
        'Specific Needs': 'Comments',
        'Has received Affinity training of McK?': 'Has received Affinity training of McK?',
        'License Expiration ': 'License Expiration'
    }, inplace=True)
    user_df.dropna(subset=['Name'], inplace=True)

    # Conversión de tipos robusta
    yes_values = ['yes', 'si', 'true', '1']
    for col in ['Active License', 'Has received Affinity training of McK?', 'Scheduler tag']:
        if col in user_df.columns:
            user_df[col] = user_df[col].astype(str).str.strip().str.lower().isin(yes_values)
        else:
            user_df[col] = False 
            
    if 'License Expiration' in user_df.columns:
        user_df['License Expiration'] = pd.to_datetime(user_df['License Expiration'], errors='coerce', dayfirst=True)

    for col in user_df.select_dtypes(include=['object']).columns:
        user_df[col] = user_df[col].fillna('').astype(str).str.strip()
        
    # Unpivot y procesamiento de scores
    task_cols = [f'Task {i}' for i in range(1, 32)]
    id_vars = [col for col in user_df.columns if col not in task_cols]
    df_long = pd.melt(user_df, id_vars=id_vars, value_vars=task_cols, var_name='task_id_str', value_name='Score')
    
    df_long['task_id'] = df_long['task_id_str'].str.extract(r'(\d+)').astype(int)
    original_scores = df_long['Score'].dropna()
    numeric_scores = pd.to_numeric(original_scores.astype(str).str.replace('%', '', regex=False).str.strip(), errors='coerce')
    parsing_errors = numeric_scores.isnull().sum()
    df_long['Score'] = numeric_scores / 100
    df_long.dropna(subset=['Score'], inplace=True)

    # Fusión y creación de columnas de compatibilidad
    df_merged = pd.merge(df_long, tasks_df, on='task_id', how='left')
    df_merged.rename(columns={'category': 'Category'}, inplace=True)
    df_merged['Skill'] = df_merged['Category']
    df_merged['Task_Prefixed'] = '[' + df_merged['Category'] + '] ' + df_merged['Task']
    if 'Comments' in df_merged.columns:
        df_merged.rename(columns={'Comments': 'Specific needs'}, inplace=True)

    total_names_in_file = user_df['Name'].nunique()

    return {
        'merged_df': df_merged,
        'user_df': user_df,
        'total_count': total_names_in_file,
        'parsing_errors': int(parsing_errors)
    }

# --- ANALYTICS ENGINE (CORREGIDO) ---
@st.cache_data
def compute_analytics(_df, _user_df):
    df = _df.copy()
    user_df = _user_df.copy()
    analytics = {}
    if df.empty: return analytics
    
    # Análisis de Personas (Arquetipos)
    person_summary = df.groupby('Name')['Score'].agg(['mean', 'std']).rename(columns={'mean': 'Avg Score', 'std': 'Volatility'})
    median_v, median_p = person_summary['Volatility'].median(), person_summary['Avg Score'].median()
    def get_archetype(row):
        if pd.isna(row['Volatility']): return "🎯 Needs Support"
        if row['Avg Score'] >= median_p and row['Volatility'] <= median_v: return "🏆 Versatile Leader"
        if row['Avg Score'] >= median_p and row['Volatility'] > median_v: return "🌟 Niche Specialist"
        if row['Avg Score'] < median_p and row['Volatility'] <= median_v: return "🌱 Consistent Learner"
        return "🎯 Needs Support"
    person_summary['Archetype'] = person_summary.apply(get_archetype, axis=1)
    
    person_summary = person_summary.join(user_df.set_index('Name')[['Team Leader', 'Scheduler tag']], how='left')
    analytics['person_summary'] = person_summary
    
    # Análisis de Tareas (Riesgo y Expertos)
    task_summary = df.groupby('Task_Prefixed').agg(
        Avg_Score=('Score', 'mean'),
        Expert_Count=('Score', lambda s: (s >= 0.8).sum()),
        Beginner_Count=('Score', lambda s: (s < 0.4).sum())
    )
    task_summary['Risk Index'] = (task_summary['Beginner_Count'] + 1) / (task_summary['Expert_Count'] + 1)
    task_summary['SPOF'] = task_summary['Expert_Count'] == 1
    analytics['risk_radar'] = task_summary.sort_values(by='Risk Index', ascending=False)
    
    # Mapeo de riesgo de expiración de licencia
    experts_df = df[df['Score'] >= 0.8][['Name', 'Task_Prefixed']]
    experts_with_exp = pd.merge(experts_df, user_df[['Name', 'License Expiration']], on='Name', how='left')
    ninety_days_from_now = datetime.now() + pd.Timedelta(days=90)
    expiring_experts = experts_with_exp[
        (experts_with_exp['License Expiration'].notna()) &
        (experts_with_exp['License Expiration'] < ninety_days_from_now)
    ]
    tasks_with_exp_risk = expiring_experts['Task_Prefixed'].unique()
    task_summary['Expiration Risk'] = task_summary.index.isin(tasks_with_exp_risk)
    analytics['risk_matrix'] = task_summary
    
    # Identificar "Talent Pipeline"
    critical_tasks = task_summary[task_summary['Avg_Score'] < 0.6].index
    pipeline_candidates = df[df['Task_Prefixed'].isin(critical_tasks) & df['Score'].between(0.6, 0.79)]
    pipeline_candidates = pd.merge(pipeline_candidates, person_summary.reset_index()[['Name', 'Archetype']], on='Name')
    analytics['talent_pipeline'] = pipeline_candidates[['Name', 'Archetype', 'Task_Prefixed', 'Score']].sort_values('Score', ascending=False)
    
    # Otros análisis
    task_avg = df.groupby('Task_Prefixed')['Score'].mean(); hard_tasks = task_avg[task_avg < 0.6].index
    mid_tier = person_summary[(person_summary['Avg Score'] >= 0.5) & (person_summary['Avg Score'] < 0.8)].index
    analytics['hidden_stars'] = df[(df['Name'].isin(mid_tier)) & (df['Task_Prefixed'].isin(hard_tasks)) & (df['Score'] >= 0.9)].copy()
    df_adj = df.copy(); df_adj['Difficulty Weight'] = df_adj['Task_Prefixed'].map(1 - task_avg); df_adj['Adjusted Score'] = df_adj['Score'] * df_adj['Difficulty Weight']
    analytics['adjusted_ranking'] = pd.DataFrame(df_adj.groupby('Name')['Adjusted Score'].sum().sort_values(ascending=False)).reset_index()
    skill_pivot = df.pivot_table(index='Name', columns='Skill', values='Score', aggfunc='mean').fillna(df['Score'].mean())
    analytics['skill_correlation'] = skill_pivot.corr()
    
    return analytics

@st.cache_data
def analyze_comment_themes(df_comments):
    themes = {
        'Training/Guidance': r'training|learn|course|session|refresher|guide|help|practice', 'Isometric Skills': r'isometric|iso',
        'Photo Editing': r'photo|background|remove|color|edit|retouch', 'Vector/Technical': r'vector|mask|clipping|rasterize|bezier|pen tool|illustrator',
        'Confidence/Experience': r'confident|beginner|expert|feel|experience|use it|long time', 'Tools/Software': r'tool|affinity|photoshop|version|update|install'
    }
    theme_counts = {theme: 0 for theme in themes}
    all_comments = ' '.join(df_comments.dropna().unique())
    for theme, pattern in themes.items(): theme_counts[theme] = len(re.findall(pattern, all_comments, re.IGNORECASE))
    return pd.DataFrame.from_dict(theme_counts, orient='index', columns=['Mentions']).sort_values('Mentions', ascending=False)


def main_app():
    st.sidebar.title("🚀 Team Skills Hub")
    st.sidebar.markdown("---")
    st.sidebar.info("A strategic platform for talent intelligence and team development.")
    st.sidebar.markdown("---")
    
    data_load_result = load_and_process_data("userData.csv", "tasks.json")
    if data_load_result is None: st.error("Dashboard cannot be loaded. Check data files."); st.stop()
    
    df_merged = data_load_result['merged_df']
    user_df = data_load_result['user_df']
    total_participants_in_file = data_load_result['total_count']
    score_parsing_errors = data_load_result['parsing_errors']
    active_participants_count = df_merged['Name'].nunique()
    
    if df_merged.empty: st.warning("No participants with valid scores were found."); st.stop()
    
    analytics = compute_analytics(df_merged, user_df)
    person_summary = analytics.get('person_summary', pd.DataFrame())
    risk_radar = analytics.get('risk_radar', pd.DataFrame())
    risk_matrix = analytics.get('risk_matrix', pd.DataFrame())
    talent_pipeline = analytics.get('talent_pipeline', pd.DataFrame())

    st.title("🚀 Team Skills & Affinity Hub")
    
    tab_list = [
        "📈 Strategic Overview", "⭐ Affinity Status", "🗺️ Action Playbook", 
        "👤 Team Profiles", "🧠 Skill Analysis", "🧬 Team DNA & Dynamics",
        "🔭 Risk & Opportunity Forecaster"
    ]
    tabs = st.tabs(tab_list)

    with tabs[0]: # Strategic Overview
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
                fig_pie.update_layout(height=300, margin=dict(t=30, b=20, l=0, r=0), legend_orientation="h"); st.plotly_chart(fig_pie, use_container_width=True)
        with col2:
             with st.container(border=True):
                st.subheader("🩺 Data Health Check")
                assessed_names = set(df_merged['Name'].unique())
                all_user_names = set(user_df['Name'].unique())
                pending_assessment_names = all_user_names - assessed_names
                
                st.metric("Self-Assessment Response Rate", f"{len(assessed_names)} / {len(all_user_names)}", f"{len(pending_assessment_names)} pending")
                st.metric("Score Data Quality", f"{score_parsing_errors} invalid entries", "Found in file", delta_color="off")
                with st.expander(f"View {len(pending_assessment_names)} people pending assessment"):
                    if pending_assessment_names: st.dataframe(user_df[user_df['Name'].isin(pending_assessment_names)][['Name', 'Team Leader']], hide_index=True)
                    else: st.info("All users have completed the assessment.")

        st.divider()
        col1, col2 = st.columns(2, gap="large")
        with col1:
            with st.container(border=True):
                st.subheader("🚨 Skill Risk Radar")
                st.caption("Top 5 tasks with the highest risk (few experts, many beginners).")
                for index, row in risk_radar.head(5).iterrows(): st.metric(label=row.name, value=f"{row['Avg_Score']:.1%} Avg. Confidence", delta=f"Risk Index: {row['Risk Index']:.2f}", delta_color="inverse")
        with col2:
            with st.container(border=True):
                st.subheader("📡 Comparative Risk Profile")
                st.caption("Compares top 5 risk areas across key metrics.")
                risk_data_head = risk_radar.head(5).reset_index()
                
                categories = ['Avg_Score', 'Risk Index', 'Expert_Count', 'Beginner_Count']
                category_labels = {'Avg_Score': 'Avg Score', 'Risk Index': 'Risk Index', 'Expert_Count': 'Experts (>=80%)', 'Beginner_Count': 'Beginners (<40%)'}
                
                valid_categories = [cat for cat in categories if cat in risk_data_head.columns]
                normalized_data = risk_data_head[valid_categories].copy()
                for cat in valid_categories:
                     if (risk_radar[cat].max() - risk_radar[cat].min()) > 0: normalized_data[cat] = (risk_data_head[cat] - risk_radar[cat].min()) / (risk_radar[cat].max() - risk_radar[cat].min())
                     else: normalized_data[cat] = 0.5
                
                fig_radar = go.Figure()
                for i, row in risk_data_head.iterrows():
                    fig_radar.add_trace(go.Scatterpolar(r=normalized_data.loc[i, valid_categories].values, theta=[category_labels.get(cat, cat) for cat in valid_categories], fill='toself', name=row['Task_Prefixed'][:40] + "...",
                        hovertemplate=f"<b>{row['Task_Prefixed']}</b><br>Risk Index: {row['Risk Index']:.2f}<br>Avg Score: {row['Avg_Score']:.1%}<extra></extra>"))
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=False, range=[0, 1])), showlegend=True, height=350, margin=dict(l=40, r=40, t=60, b=40)); st.plotly_chart(fig_radar, use_container_width=True)

    with tabs[1]: # Affinity Status
        st.header("⭐ Affinity Status & Team Feedback")
        with st.container(border=True):
            st.subheader("📊 Overall Software Status")
            kpi1, kpi2 = st.columns(2)
            total_users = len(user_df)
            kpi1.metric("Active Affinity Licenses", f"{user_df['Active License'].sum()}", f"{user_df['Active License'].sum()/total_users:.0%} of team")
            kpi2.metric("Received McK Training", f"{user_df['Has received Affinity training of McK?'].sum()}", f"{user_df['Has received Affinity training of McK?'].sum()/total_users:.0%} of team")
        
        with st.container(border=True):
            st.subheader("🚨 License Expiration Timeline")
            today = datetime.now()
            exp_df = user_df[user_df['License Expiration'].notna()].copy()
            if not exp_df.empty:
                exp_df['Days Left'] = (exp_df['License Expiration'] - today).dt.days
                exp_df = exp_df[exp_df['Days Left'] > 0]
                if not exp_df.empty:
                    exp_df['Start'] = today
                    fig_timeline = px.timeline(exp_df, x_start="Start", x_end="License Expiration", y="Name", text="Days Left")
                    st.plotly_chart(fig_timeline, use_container_width=True)
                else: st.success("✅ No upcoming license expirations found.")
            else: st.success("✅ No license expiration data found.")

        with st.container(border=True):
            st.subheader("🗣️ Team Feedback Analysis")
            comment_col1, comment_col2 = st.columns([2, 3])
            with comment_col1:
                st.markdown("**Key Themes & Word Cloud**")
                all_comments_df = user_df['Comments'].dropna()
                if not all_comments_df.empty and not all_comments_df.str.strip().eq('').all():
                    theme_counts = analyze_comment_themes(all_comments_df)
                    fig_themes = px.bar(theme_counts, x='Mentions', y=theme_counts.index, orientation='h', text_auto=True)
                    st.plotly_chart(fig_themes, use_container_width=True)
            with comment_col2:
                st.markdown("**Raw Comments**")
                st.dataframe(user_df[['Name', 'Comments']].drop_duplicates(), height=300, hide_index=True)

    with tabs[2]: # Action Playbook
        st.header("🗺️ Action Playbook")
        playbook_tab1, playbook_tab2, playbook_tab3 = st.tabs(["💡 Training Combo Generator", "👥 Group Builder", "🤝 Mentor Matchmaker"])
        with playbook_tab1:
            st.subheader("💡 Training Combo Generator"); st.markdown("Select a primary skill, and the system will suggest other highly correlated skills.")
            with st.container(border=True):
                primary_task = st.selectbox("Select a Primary Skill", options=risk_radar.index.tolist())
                primary_skill_series = df_merged[df_merged['Task_Prefixed'] == primary_task]['Skill']
                if not primary_skill_series.empty:
                    primary_skill = primary_skill_series.iloc[0]; skill_corr_matrix = analytics.get('skill_correlation', pd.DataFrame())
                    if not skill_corr_matrix.empty and primary_skill in skill_corr_matrix:
                        synergies = skill_corr_matrix[primary_skill].sort_values(ascending=False).drop(primary_skill).head(3)
                        st.success(f"**Suggested Training Module for: {primary_skill}**"); st.markdown(f"**1. Primary Focus:** `{primary_task}`"); st.markdown("**2. High-Synergy Skills:**")
                        for skill, corr in synergies.items(): st.markdown(f"- **{skill}** (Correlation: {corr:.2f})")
        with playbook_tab2:
            st.subheader("👥 Custom Training Group Builder"); st.markdown("Create groups by filtering for participants with specific development needs.")
            with st.form("group_builder_form"):
                st.markdown("**Step 1: Define the Target Skill Area**"); all_categories = sorted(df_merged['Category'].unique())
                selected_categories = st.multiselect("Filter by Category", all_categories, default=all_categories[0] if all_categories else None)
                if selected_categories: selected_tasks = st.multiselect("Filter by Task (Optional)", sorted(df_merged[df_merged['Category'].isin(selected_categories)]['Task_Prefixed'].unique()))
                else: selected_tasks = []
                st.markdown("**Step 2: Configure the Groups**"); g_col1, g_col2, g_col3 = st.columns(3)
                with g_col1: num_groups = st.number_input("Number of groups:", 1, 10, value=2)
                with g_col2: num_per_group = st.number_input("People per group:", 2, 10, value=4)
                with g_col3: add_mentors = st.checkbox("Assign mentor?", value=True)
                if submitted := st.form_submit_button("Generate Groups", type="primary", use_container_width=True):
                    st.divider(); st.subheader("✅ Generated Training Groups")
                    filtered_df = df_merged.copy()
                    if selected_categories: filtered_df = filtered_df[filtered_df['Category'].isin(selected_categories)]
                    if selected_tasks: filtered_df = filtered_df[filtered_df['Task_Prefixed'].isin(selected_tasks)]
                    if filtered_df.empty: st.error("No participants found for the selected criteria.")
                    else:
                        group_scores = filtered_df.groupby('Name')['Score'].mean().sort_values(); mentors = group_scores[group_scores >= 0.8].sort_values(ascending=False); learners = group_scores[group_scores < 0.8].sort_values(ascending=True)
                        cols = st.columns(num_groups); assigned_people = set()
                        for i in range(num_groups):
                            with cols[i]:
                                with st.container(border=True):
                                    st.markdown(f"**Group {i+1}**"); group_data = []
                                    if add_mentors and not (available_mentors := mentors[~mentors.index.isin(assigned_people)]).empty:
                                        mentor_name = available_mentors.index[0]; group_data.append({'Role': '🏆 Mentor', 'Name': mentor_name, 'Score': f"{available_mentors.iloc[0]:.1%}"}); assigned_people.add(mentor_name)
                                    learners_needed = num_per_group - len(group_data); group_learners = learners[~learners.index.isin(assigned_people)].head(learners_needed)
                                    for name, score in group_learners.items(): group_data.append({'Role': '🌱 Learner', 'Name': name, 'Score': f"{score:.1%}"}); assigned_people.add(name)
                                    if group_data: st.dataframe(pd.DataFrame(group_data), hide_index=True, use_container_width=True)
                                    else: st.warning(f"Not enough people to form Group {i+1}.")
        with playbook_tab3:
            st.subheader("🤝 Mentor Matchmaker"); st.markdown("Find the best mentor for a specific learner and skill.")
            with st.container(border=True):
                learners_list = sorted(person_summary[person_summary['Archetype'].isin(["🌱 Consistent Learner", "🎯 Needs Support"])].index.tolist())
                all_tasks = sorted(df_merged['Task_Prefixed'].unique()); col1, col2 = st.columns(2)
                with col1: selected_learner = st.selectbox("Select a Learner", options=learners_list)
                with col2: skill_needed = st.selectbox("Select a Skill Needed", options=all_tasks)
                if st.button("Find Mentor", use_container_width=True, type="primary"):
                    experts_df = df_merged[(df_merged['Task_Prefixed'] == skill_needed) & (df_merged['Name'] != selected_learner) & (df_merged['Score'] >= 0.8)]
                    if experts_df.empty: st.error(f"No suitable mentors found for the skill: **{skill_needed}**.")
                    else:
                        st.success(f"Top Mentor Recommendations for **{selected_learner}** in **{skill_needed}**"); recommendations = experts_df.sort_values(by="Score", ascending=False).head(3)
                        recommendations = pd.merge(recommendations[['Name', 'Score']], person_summary[['Archetype']], on='Name', how='left')
                        st.dataframe(recommendations[['Name', 'Archetype', 'Score']], hide_index=True, use_container_width=True, column_config={"Score": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1)})

    with tabs[3]: # Team Profiles
        st.header("👤 Team Profiles")
        col1, col2 = st.columns([1, 2], gap="large")
        with col1:
            with st.container(border=True):
                st.subheader("📇 Team Roster")
                all_user_names_list = sorted(list(user_df['Name'].unique()))
                selected_person = st.selectbox("Select a Team Member", all_user_names_list, label_visibility="collapsed")
                ranking_df = person_summary.reset_index().sort_values('Avg Score', ascending=False)
                ranking_df['Rank'] = ranking_df['Avg Score'].rank(method='min', ascending=False).astype(int)
                merged_ranking = pd.merge(user_df[['Name']], ranking_df, on='Name', how='left')
                merged_ranking['Assessed'] = merged_ranking['Name'].isin(set(df_merged['Name'].unique()))
                st.dataframe(merged_ranking, height=750, hide_index=True, column_config={"Assessed": st.column_config.CheckboxColumn("Assessed?", disabled=True), "Avg Score": st.column_config.ProgressColumn("Avg Score", format="%.1f%%", min_value=0, max_value=1)})
        with col2:
            with st.container(border=True):
                st.header(f"📇 Profile: {selected_person}")
                if selected_person not in set(df_merged['Name'].unique()): st.warning(f"**{selected_person} has not completed the self-assessment.**")
                else:
                    person_stats = person_summary.loc[selected_person]; person_data = df_merged[df_merged['Name'] == selected_person].copy()
                    rank_val = person_summary.reset_index().sort_values('Avg Score', ascending=False).set_index('Name').index.get_loc(selected_person) + 1
                    c1, c2, c3 = st.columns(3); c1.metric("Overall Rank", f"#{rank_val}"); c2.metric("Average Score", f"{person_stats['Avg Score']:.1%}"); c3.metric("Archetype", person_stats['Archetype'])
                    st.divider()
                    team_avg = df_merged.groupby('Category')['Score'].mean(); person_avg = person_data.groupby('Category')['Score'].mean().reindex(team_avg.index, fill_value=0)
                    fig_radar = go.Figure(); fig_radar.add_trace(go.Scatterpolar(r=person_avg.values, theta=person_avg.index, fill='toself', name=f'{selected_person}'))
                    fig_radar.add_trace(go.Scatterpolar(r=team_avg.values, theta=team_avg.index, fill='toself', name='Team Avg', opacity=0.6))
                    st.plotly_chart(fig_radar, use_container_width=True)
                    st.markdown("**Strengths & Development Areas**")
                    person_skills = person_data.sort_values('Score', ascending=False).drop_duplicates(subset=['Task_Prefixed'])
                    sub_col1, sub_col2 = st.columns(2)
                    with sub_col1: st.markdown("✅ **Top 5 Skills**"); st.dataframe(person_skills.head(5)[['Task_Prefixed', 'Score']], hide_index=True, column_config={"Score": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1)})
                    with sub_col2: st.markdown("🌱 **Top 5 Improvement Areas**"); st.dataframe(person_skills.tail(5)[['Task_Prefixed', 'Score']], hide_index=True, column_config={"Score": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1)})
            
            with st.expander("📄 View Full Software & Feedback Details", expanded=False):
                user_info = user_df[user_df['Name'] == selected_person].iloc[0]
                st.markdown(f"**Team Leader:** {user_info.get('Team Leader', 'N/A')}  |  **Grid:** {user_info.get('Grid', 'N/A')}")
                st.markdown(f"**Scheduler Tag:** {'Yes' if user_info.get('Scheduler tag') else 'No'}")
                st.divider()
                col1, col2 = st.columns(2)
                with col1: 
                    st.markdown("**Affinity Status**"); st.markdown(f"- License Active: {'✅' if user_info.get('Active License') else '❌'}")
                    if pd.notna(user_info.get('License Expiration')): st.markdown(f"- Expires: {user_info.get('License Expiration').strftime('%d-%b-%Y')}")
                    st.markdown(f"- McK Training: {'✅' if user_info.get('Has received Affinity training of McK?') else '❌'}")
                with col2:
                    st.markdown("**Experience & Comments**"); st.info(f"**Experience:** {user_info.get('Experience', 'N/A')}")
                    st.info(f"**Confidence w/ MM:** {user_info.get('Confidence with MM', 'N/A')}")
                    st.warning(f"**Comments:** {user_info.get('Comments', 'N/A')}")

    with tabs[4]: # Skill Analysis
        st.header("🧠 Skill Analysis")
        subtab1, subtab2, subtab3 = st.tabs(["📊 Skill Distribution", "🏆 Talent Composition", "🕸️ Skill Correlation"])
        with subtab1:
            st.subheader("Deep Dive by Skill or Category")
            with st.container(border=True):
                analysis_type = st.radio("Analyze by:", ["Category", "Task"], horizontal=True)
                if analysis_type == "Task": options, label, filter_col = sorted(df_merged['Task_Prefixed'].unique()), "Select Task(s)", 'Task_Prefixed'
                else: options, label, filter_col = sorted(df_merged['Category'].unique()), "Select Category(s)", 'Category'
                selected_items = st.multiselect(label, options, default=options[0] if options else None)
                if not selected_items: st.warning(f"Please select at least one {analysis_type}.")
                else:
                    skill_data = df_merged[df_merged[filter_col].isin(selected_items)]; st.markdown(f"#### Competency Profile for: {', '.join(selected_items)}")
                    c1,c2,c3=st.columns(3); c1.metric("Avg Confidence",f"{skill_data['Score'].mean():.1%}"); c2.metric("Experts (≥80%)",skill_data[skill_data['Score']>=0.8]['Name'].nunique()); c3.metric("Beginners (<40%)",skill_data[skill_data['Score']<0.4]['Name'].nunique())
                    st.divider(); c1_s,c2_s=st.columns(2)
                    with c1_s: st.markdown("**Skill Leaderboard**"); st.dataframe(skill_data.groupby('Name')['Score'].mean().sort_values(ascending=False).reset_index(),hide_index=True,column_config={"Score":st.column_config.ProgressColumn("Confidence",min_value=0,max_value=1)})
                    with c2_s: st.markdown("**Score Distribution**"); fig=px.histogram(skill_data,x='Score',nbins=10); fig.update_layout(height=350,margin=dict(t=20,b=20),showlegend=False); st.plotly_chart(fig,use_container_width=True)
        with subtab2:
            st.subheader("Talent Composition")
            col1, col2 = st.columns([1, 2], gap="large")
            with col1:
                with st.container(border=True):
                    st.markdown("**🌟 Hidden Stars**"); st.caption("Mid-tier performers who excel at hard tasks.")
                    hidden_stars = analytics.get('hidden_stars', pd.DataFrame())
                    if hidden_stars.empty: st.info("No 'Hidden Stars' found.")
                    else: st.dataframe(hidden_stars[['Name', 'Task_Prefixed', 'Score']], hide_index=True, height=300)
            with col2:
                with st.container(border=True):
                    st.markdown("**🧗 Adjusted Difficulty Ranking**"); st.caption("Identifies tough-problem solvers.")
                    adj_ranking = analytics.get('adjusted_ranking', pd.DataFrame())
                    st.dataframe(adj_ranking, hide_index=True, height=350, column_config={"Adjusted Score": st.column_config.BarChartColumn("Adjusted Score", y_min=0)})
        with subtab3:
            st.subheader("Skill Correlation Heatmap")
            with st.container(border=True):
                st.markdown("This heatmap shows which skills are most frequently learned together.")
                skill_corr_matrix = analytics.get('skill_correlation', pd.DataFrame())
                if not skill_corr_matrix.empty:
                    fig_heatmap = px.imshow(skill_corr_matrix, text_auto=".2f", aspect="auto", color_continuous_scale='RdYlBu'); fig_heatmap.update_layout(height=600, title="Skill Correlation Matrix")
                    st.plotly_chart(fig_heatmap, use_container_width=True)

    with tabs[5]: # Team DNA & Dynamics
        st.header("🧬 Team DNA & Dynamics")
        st.info("Análisis de la composición y características únicas de cada equipo.")

        st.subheader("🔬 Huella Digital de Habilidades por Equipo")
        all_teams = sorted([t for t in person_summary['Team Leader'].unique() if t])
        if all_teams:
            selected_team = st.selectbox("Seleccione un Líder de Equipo para analizar", all_teams)
            if selected_team:
                team_members = person_summary[person_summary['Team Leader'] == selected_team].index
                team_data = df_merged[df_merged['Name'].isin(team_members)]
                team_fingerprint = team_data.groupby('Category')['Score'].quantile(0.75)
                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(r=team_fingerprint.values, theta=team_fingerprint.index, fill='toself', name='Competencia Avanzada (Percentil 75)'))
                fig.update_layout(title=f"Huella Digital de Habilidades - Equipo de {selected_team}", polar=dict(radialaxis=dict(visible=True, range=[0, 1])))
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No hay datos de líderes de equipo para analizar.")

        st.divider()
        
        st.subheader("📊 Distribución de Arquetipos por Equipo")
        if 'Team Leader' in person_summary.columns and not person_summary['Team Leader'].isnull().all():
            archetype_dist = person_summary.groupby(['Team Leader', 'Archetype']).size().unstack(fill_value=0)
            archetype_dist_pct = archetype_dist.apply(lambda x: x*100/sum(x), axis=1)
            fig = px.bar(archetype_dist_pct, x=archetype_dist_pct.index, y=archetype_dist_pct.columns, title="Composición de Arquetipos por Equipo (%)", template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        
        st.subheader("🏷️ Análisis de 'Scheduler Tag'")
        col1, col2 = st.columns(2)
        
        # CORRECCIÓN APLICADA AQUÍ
        scheduler_data = df_merged.copy() 
        
        with col1:
            st.markdown("**Perfil de Habilidad (CON Scheduler Tag)**")
            with_tag_profile = scheduler_data[scheduler_data['Scheduler tag'] == True].groupby('Category')['Score'].mean()
            if not with_tag_profile.empty: st.plotly_chart(px.bar(with_tag_profile, orientation='h'), use_container_width=True)
            else: st.info("No hay datos para personas con 'Scheduler Tag'.")
        with col2:
            st.markdown("**Perfil de Habilidad (SIN Scheduler Tag)**")
            without_tag_profile = scheduler_data[scheduler_data['Scheduler tag'] == False].groupby('Category')['Score'].mean()
            if not without_tag_profile.empty: st.plotly_chart(px.bar(without_tag_profile, orientation='h'), use_container_width=True)
            else: st.info("No hay datos para personas sin 'Scheduler Tag'.")

    with tabs[6]: # Risk & Opportunity Forecaster
        st.header("🔭 Risk & Opportunity Forecaster")
        st.info("Identificación proactiva de riesgos de talento y oportunidades de desarrollo.")
        
        st.subheader("🚨 Matriz de Riesgo de Talento")
        def highlight_risks(row):
            styles = [''] * len(row)
            if row['SPOF']: styles[row.index.get_loc('Expert_Count')] = 'background-color: orange'
            if row['Expiration Risk']: styles[row.index.get_loc('Expiration Risk')] = 'background-color: red; color: white'
            return styles
        risk_df_display = risk_matrix.reset_index()[['Task_Prefixed', 'Avg_Score', 'Expert_Count', 'SPOF', 'Expiration Risk']]
        st.dataframe(risk_df_display.style.apply(highlight_risks, axis=1).format({'Avg_Score': "{:.1%}"}), use_container_width=True)
        st.caption("🔶 Naranja: Punto Único de Fallo (SPOF). 🔴 Rojo: El experto clave tiene una licencia que expira pronto.")
        
        st.divider()
        
        st.subheader("🌱 Cantera de Talento (Talent Pipeline)")
        st.caption("Personas con alto potencial en áreas críticas para el equipo. Son los candidatos ideales para formación de nivelación.")
        if not talent_pipeline.empty:
            st.dataframe(talent_pipeline, column_config={"Score": st.column_config.ProgressColumn("Confianza Actual", format="%.1f%%", min_value=0, max_value=1)}, use_container_width=True, hide_index=True)
        else:
            st.success("✅ No se han identificado candidatos para la cantera de talento en este momento.")


def login_page():
    st.title("🔐 Team Skills Hub Login")
    with st.form("login_form"):
        username = st.text_input("Username").lower()
        password = st.text_input("PIN", type="password")
        submitted = st.form_submit_button("Log In")
        if submitted:
            try:
                correct_username = st.secrets["credentials"]["username"]; correct_password = st.secrets["credentials"]["password"]
                if username == correct_username and password == correct_password:
                    st.session_state.logged_in = True; st.rerun()
                else: st.error("Incorrect username or PIN. Please try again.")
            except KeyError: st.error("Secrets not configured on the server. Please contact the administrator.")


# ==============================================================================
#                                  MAIN SCRIPT FLOW
# ==============================================================================
if DEVELOPMENT_MODE:
    main_app()
else:
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if st.session_state.logged_in:
        main_app()
    else:
        login_page()
