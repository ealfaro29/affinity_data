# =============================
# File: analytics_engine.py
# =============================

import pandas as pd
from datetime import datetime
import re
from typing import Dict, Any
import config  # Import the centralized configuration

def _build_person_archetypes(df: pd.DataFrame, user_df: pd.DataFrame) -> pd.DataFrame:
    """Calculates Avg Score, Volatility, and defines a persona archetype for each person."""
    summary = df.groupby('Name')['Score'].agg(['mean', 'std']).rename(columns={'mean': 'Avg Score', 'std': 'Volatility'})
    median_v = summary['Volatility'].median()
    median_p = summary['Avg Score'].median()

    def archetype(row: pd.Series) -> str:
        """Assigns an archetype based on performance and volatility."""
        if pd.isna(row['Volatility']) or row['Avg Score'] == 0:
            return config.ARCHETYPE_NEEDS_SUPPORT
        if row['Avg Score'] >= median_p and row['Volatility'] <= median_v:
            return config.ARCHETYPE_VERSATILE_LEADER
        if row['Avg Score'] >= median_p and row['Volatility'] > median_v:
            return config.ARCHETYPE_NICHE_SPECIALIST
        if row['Avg Score'] < median_p and row['Volatility'] <= median_v:
            return config.ARCHETYPE_CONSISTENT_LEARNER
        return config.ARCHETYPE_NEEDS_SUPPORT

    summary['Archetype'] = summary.apply(archetype, axis=1)
    
    if 'Team Leader' in user_df.columns and 'Scheduler tag' in user_df.columns:
        summary = summary.join(user_df.set_index('Name')[['Team Leader', 'Scheduler tag']], how='left')
    
    return summary


def compute_analytics(df: pd.DataFrame, user_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes all advanced analytics for the dashboard.
    """
    analytics = {}
    if df.empty:
        return analytics

    analytics['df_merged_for_lookup'] = df 

    # 1. Personas / Archetypes
    person_summary = _build_person_archetypes(df, user_df)
    analytics['person_summary'] = person_summary

    # 2. Task Summary with FULL Risk Analysis
    task_summary = df.groupby('Task_Prefixed').agg(
        Avg_Score=('Score', 'mean'),
        Expert_Count=('Score', lambda s: (s >= config.EXPERT_THRESHOLD).sum()),
        Beginner_Count=('Score', lambda s: (s < config.BEGINNER_THRESHOLD).sum()),
    )
    task_summary['Risk Index'] = (task_summary['Beginner_Count'] + 1) / (task_summary['Expert_Count'] + 1)
    task_summary['SPOF'] = task_summary['Expert_Count'] == 1
    task_summary['Competency_Score'] = task_summary['Avg_Score'] * (task_summary['Expert_Count'] + 1)

    # 3. License expiration risk overlay (This is used in the `task_summary` logic, so it stays)
    experts_df = df[df['Score'] >= config.EXPERT_THRESHOLD][['Name', 'Task_Prefixed']]
    experts_with_exp = pd.merge(experts_df, user_df[['Name', 'License Expiration']], on='Name', how='left')
    
    expiration_window = datetime.now() + pd.Timedelta(days=config.LICENSE_EXPIRATION_WINDOW_DAYS)
    
    expiring_experts = experts_with_exp[
        (experts_with_exp['License Expiration'].notna()) & 
        (experts_with_exp['License Expiration'] < expiration_window)
    ]
    tasks_with_exp_risk = set(expiring_experts['Task_Prefixed'].unique())
    task_summary['Expiration Risk'] = task_summary.index.isin(tasks_with_exp_risk)
    
    analytics['task_summary'] = task_summary
    analytics['risk_radar'] = task_summary.sort_values(by='Risk Index', ascending=False)
    analytics['risk_matrix'] = task_summary[task_summary['Risk Index'] > config.HIGH_RISK_INDEX]

    # 4. Opportunity Lens: Identify over-strengths
    analytics['opportunity_lens'] = task_summary[
        task_summary['Avg_Score'] >= config.OPPORTUNITY_AVG_SCORE
    ].sort_values('Competency_Score', ascending=False)

    # 5. Talent pipeline: medium performers in critical tasks
    critical_tasks = task_summary[task_summary['Avg_Score'] < config.CRITICAL_AVG_SCORE].index
    pipeline_candidates = df[
        df['Task_Prefixed'].isin(critical_tasks) & 
        df['Score'].between(config.PIPELINE_MIN, config.PIPELINE_MAX)
    ]
    pipeline_candidates = pd.merge(pipeline_candidates, person_summary.reset_index()[['Name', 'Archetype']], on='Name')
    analytics['talent_pipeline'] = pipeline_candidates[['Name', 'Archetype', 'Task_Prefixed', 'Score']].sort_values('Score', ascending=False)

    # --- EDIT: Removed 'skill_correlation' calculation ---

    return analytics


def analyze_comment_themes(df_comments: pd.Series) -> pd.DataFrame:
    """Uses regex to find common themes in a Series of free-text comments."""
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