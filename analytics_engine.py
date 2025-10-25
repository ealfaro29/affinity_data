# =============================
# File: analytics_engine.py
# =============================

import pandas as pd
from datetime import datetime
import re


def _build_person_archetypes(df: pd.DataFrame, user_df: pd.DataFrame) -> pd.DataFrame:
    summary = df.groupby('Name')['Score'].agg(['mean', 'std']).rename(columns={'mean': 'Avg Score', 'std': 'Volatility'})
    median_v = summary['Volatility'].median()
    median_p = summary['Avg Score'].median()

    def archetype(row):
        if pd.isna(row['Volatility']) or row['Avg Score'] == 0:
            return "🎯 Needs Support"
        if row['Avg Score'] >= median_p and row['Volatility'] <= median_v:
            return "🏆 Versatile Leader"
        if row['Avg Score'] >= median_p and row['Volatility'] > median_v:
            return "🌟 Niche Specialist"
        if row['Avg Score'] < median_p and row['Volatility'] <= median_v:
            return "🌱 Consistent Learner"
        return "🎯 Needs Support"

    summary['Archetype'] = summary.apply(archetype, axis=1)
    summary = summary.join(user_df.set_index('Name')[['Team Leader', 'Scheduler tag']], how='left')
    return summary


def compute_analytics(df: pd.DataFrame, user_df: pd.DataFrame) -> dict:
    analytics = {}
    if df.empty:
        return analytics

    # Pass the raw dataframe through for UI lookups (NEW)
    analytics['df_merged_for_lookup'] = df 

    # Personas / Archetypes
    person_summary = _build_person_archetypes(df, user_df)
    analytics['person_summary'] = person_summary

    # Task Summary with FULL Risk Analysis (Original + Enhancements)
    task_summary = df.groupby('Task_Prefixed').agg(
        Avg_Score=('Score', 'mean'),
        Expert_Count=('Score', lambda s: (s >= 0.8).sum()),
        Beginner_Count=('Score', lambda s: (s < 0.4).sum()),
    )
    task_summary['Risk Index'] = (task_summary['Beginner_Count'] + 1) / (task_summary['Expert_Count'] + 1)
    task_summary['SPOF'] = task_summary['Expert_Count'] == 1
    task_summary['Competency_Score'] = task_summary['Avg_Score'] * (task_summary['Expert_Count'] + 1)

    # License expiration risk overlay (from original)
    experts_df = df[df['Score'] >= 0.8][['Name', 'Task_Prefixed']]
    experts_with_exp = pd.merge(experts_df, user_df[['Name', 'License Expiration']], on='Name', how='left')
    ninety_days_from_now = datetime.now() + pd.Timedelta(days=90)
    expiring_experts = experts_with_exp[(experts_with_exp['License Expiration'].notna()) & (experts_with_exp['License Expiration'] < ninety_days_from_now)]
    tasks_with_exp_risk = set(expiring_experts['Task_Prefixed'].unique())
    task_summary['Expiration Risk'] = task_summary.index.isin(tasks_with_exp_risk)
    
    analytics['task_summary'] = task_summary
    analytics['risk_radar'] = task_summary.sort_values(by='Risk Index', ascending=False)
    analytics['risk_matrix'] = task_summary

    # Opportunity Lens: Identify over-strengths
    analytics['opportunity_lens'] = task_summary[task_summary['Avg_Score'] >= 0.75].sort_values('Competency_Score', ascending=False)

    # Talent pipeline: medium performers in critical tasks
    critical_tasks = task_summary[task_summary['Avg_Score'] < 0.6].index
    pipeline_candidates = df[df['Task_Prefixed'].isin(critical_tasks) & df['Score'].between(0.6, 0.79)]
    pipeline_candidates = pd.merge(pipeline_candidates, person_summary.reset_index()[['Name', 'Archetype']], on='Name')
    analytics['talent_pipeline'] = pipeline_candidates[['Name', 'Archetype', 'Task_Prefixed', 'Score']].sort_values('Score', ascending=False)

    # Hidden stars and adjusted ranking
    task_avg = df.groupby('Task_Prefixed')['Score'].mean()
    hard_tasks = task_avg[task_avg < 0.6].index
    mid_tier = person_summary[(person_summary['Avg Score'] >= 0.5) & (person_summary['Avg Score'] < 0.8)].index
    analytics['hidden_stars'] = df[(df['Name'].isin(mid_tier)) & (df['Task_Prefixed'].isin(hard_tasks)) & (df['Score'] >= 0.9)].copy()

    df_adj = df.copy()
    df_adj['Difficulty Weight'] = df_adj['Task_Prefixed'].map(1 - task_avg)
    df_adj['Adjusted Score'] = df_adj['Score'] * df_adj['Difficulty Weight']
    analytics['adjusted_ranking'] = pd.DataFrame(df_adj.groupby('Name')['Adjusted Score'].sum().sort_values(ascending=False)).reset_index()

    # Skill correlation
    skill_pivot = df.pivot_table(index='Name', columns='Skill', values='Score', aggfunc='mean').fillna(df['Score'].mean())
    analytics['skill_correlation'] = skill_pivot.corr()

    return analytics


def analyze_comment_themes(df_comments: pd.Series) -> pd.DataFrame:
    themes = {
        'Training/Guidance': r'training|learn|course|session|refresher|guide|help|practice',
        'Isometric Skills': r'isometric|iso',
        'Photo Editing': r'photo|background|remove|color|edit|retouch',
        'Vector/Technical': r'vector|mask|clipping|rasterize|bezier|pen tool|illustrator',
        'Confidence/Experience': r'confident|beginner|expert|feel|experience|use it|long time',
        'Tools/Software': r'tool|affinity|photoshop|version|update|install',
    }
    theme_counts = {theme: 0 for theme in themes}
    all_comments = ' '.join(df_comments.dropna().unique())
    for theme, pattern in themes.items():
        theme_counts[theme] = len(re.findall(pattern, all_comments, re.IGNORECASE))
    return pd.DataFrame.from_dict(theme_counts, orient='index', columns=['Mentions']).sort_values('Mentions', ascending=False)