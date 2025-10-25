# =============================
# File: data_engine.py
# =============================

import pandas as pd
from datetime import datetime
from pathlib import Path
import streamlit as st
from typing import Dict, Any, Optional, List

@st.cache_data
def load_and_process_data(user_csv_path: str, tasks_json_path: str) -> Optional[Dict[str, Any]]:
    """
    Load, clean, and merge the user skills CSV and the tasks catalog JSON.
    Filenames are intentionally fixed. Robust to missing columns and mixed value types.
    
    Returns:
        A dict with merged_df, user_df, total_count, parsing_errors, or None on failure.
    """
    
    # Read tasks.json → tasks_df
    try:
        tasks_df = pd.read_json(tasks_json_path)['skills'].apply(pd.Series)
        tasks_df.rename(columns={'title': 'Task', 'id': 'task_id', 'category': 'Category'}, inplace=True)
    except Exception as e:
        st.error(f"Critical error reading tasks.json: {e}")
        return None
        
    # --- DYNAMIC TASK LOADING (ENHANCEMENT) ---
    # Get the list of task IDs from tasks.json to dynamically build the column list
    # This avoids the hardcoded 'range(1, 32)'
    if 'task_id' not in tasks_df.columns:
        st.error("Critical error: 'task_id' (from 'id') not found in tasks.json.")
        return None
        
    task_cols = [f'Task {i}' for i in tasks_df['task_id']]
    num_tasks = len(task_cols)

    # Read userData.csv → user_df
    try:
        user_df = pd.read_csv(user_csv_path, sep=';', encoding='utf-8-sig')
    except Exception as e:
        st.error(f"Critical error reading userData.csv: {e}")
        return None

    # Normalize headers and key columns
    user_df.columns = user_df.columns.str.strip()
    user_df.rename(columns={
        'BPS': 'Name',
        'Specific Needs': 'Comments',
        'Has received Affinity training of McK?': 'Has received Affinity training of McK?',
        'License Expiration ': 'License Expiration'
    }, inplace=True)

    # Drop rows without Name
    user_df.dropna(subset=['Name'], inplace=True)

    # Robust boolean conversion for key flags
    yes_values = {'yes', 'si', 'sí', 'true', '1', 'y', 't'}
    for col in ['Active License', 'Has received Affinity training of McK?', 'Scheduler tag']:
        if col in user_df.columns:
            user_df[col] = user_df[col].astype(str).str.strip().str.lower().isin(yes_values)
        else:
            user_df[col] = False

    # Date parsing for License Expiration
    if 'License Expiration' in user_df.columns:
        user_df['License Expiration'] = pd.to_datetime(user_df['License Expiration'], errors='coerce', dayfirst=True)

    # Ensure all object columns are trimmed strings
    for col in user_df.select_dtypes(include=['object']).columns:
        user_df[col] = user_df[col].fillna('').astype(str).str.strip()

    # Unpivot Task 1..N into long format
    # Ensure all expected task columns exist, adding missing ones as empty if needed
    # This prevents errors if the CSV is missing task columns
    present_task_cols = []
    for col in task_cols:
        if col in user_df.columns:
            present_task_cols.append(col)
        
    id_vars = [c for c in user_df.columns if c not in task_cols]
    
    if not present_task_cols:
        st.error("No 'Task X' columns found in userData.csv.")
        return None
        
    df_long = pd.melt(user_df, id_vars=id_vars, value_vars=present_task_cols, var_name='task_id_str', value_name='Score')

    # Extract numeric task_id and parse percentage scores
    df_long['task_id'] = df_long['task_id_str'].str.extract(r'(\d+)').astype(int)
    raw_scores = df_long['Score'].dropna()
    numeric_scores = pd.to_numeric(raw_scores.astype(str).str.replace('%', '', regex=False).str.strip(), errors='coerce')
    parsing_errors = int(numeric_scores.isnull().sum())
    
    df_long['Score'] = pd.to_numeric(df_long['Score'].astype(str).str.replace('%', '', regex=False).str.strip(), errors='coerce') / 100
    df_long.dropna(subset=['Score'], inplace=True)

    # Merge with tasks catalog
    df_merged = pd.merge(df_long, tasks_df, on='task_id', how='left')

    # Convenience columns
    df_merged['Skill'] = df_merged['Category']
    df_merged['Task_Prefixed'] = '[' + df_merged['Category'] + '] ' + df_merged['Task']

    # Align Comments naming across views
    if 'Comments' in df_merged.columns:
        df_merged.rename(columns={'Comments': 'Specific needs'}, inplace=True)

    total_names_in_file = user_df['Name'].nunique()

    return {
        'merged_df': df_merged,
        'user_df': user_df,
        'total_count': total_names_in_file,
        'parsing_errors': parsing_errors,
    }