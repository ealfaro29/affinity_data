# =============================
# File: data_engine.py
# =============================

import pandas as pd
from datetime import datetime
from pathlib import Path
import streamlit as st
from typing import Dict, Any, Optional, IO

@st.cache_data
def load_and_process_data(user_csv_file: IO[Any], tasks_json_path: str) -> Optional[Dict[str, Any]]:
    """
    Load, clean, and merge the user skills CSV and the tasks catalog JSON.
    """
    
    # Read tasks.json → tasks_df
    try:
        tasks_df = pd.read_json(tasks_json_path)['skills'].apply(pd.Series)
        tasks_df.rename(columns={'title': 'Task', 'id': 'task_id', 'category': 'Category'}, inplace=True)
    except FileNotFoundError:
        st.error(f"Critical Error: tasks.json not found at path: {tasks_json_path}")
        return None
    except Exception as e:
        st.error(f"Critical Error reading tasks.json: {e}")
        return None
        
    if 'task_id' not in tasks_df.columns:
        st.error("Critical Error: 'task_id' (from 'id') not found in tasks.json.")
        return None
        
    task_cols = [f'Task {i}' for i in tasks_df['task_id']]
    num_tasks = len(task_cols)

    # Read uploaded user_csv_file → user_df
    try:
        user_df = pd.read_csv(user_csv_file, sep=';', encoding='utf-8-sig')
        
    except Exception as e:
        st.error(f"Critical Error reading uploaded userData.csv: {e}")
        return None

    # Normalize headers and key columns
    user_df.columns = user_df.columns.str.strip()
    user_df.rename(columns={
        'BPS': 'Name',
        'Specific Needs': 'Comments',
        'Has received Affinity training of McK?': 'Has received Affinity training of McK?',
        'License Expiration ': 'License Expiration'
    }, inplace=True)

    user_df.dropna(subset=['Name'], inplace=True)

    yes_values = {'yes', 'si', 'sí', 'true', '1', 'y', 't'}
    for col in ['Active License', 'Has received Affinity training of McK?', 'Scheduler tag']:
        if col in user_df.columns:
            user_df[col] = user_df[col].astype(str).str.strip().str.lower().isin(yes_values)
        else:
            user_df[col] = False

    if 'License Expiration' in user_df.columns:
        user_df['License Expiration'] = pd.to_datetime(user_df['License Expiration'], errors='coerce', dayfirst=True)

    for col in user_df.select_dtypes(include=['object']).columns:
        user_df[col] = user_df[col].fillna('').astype(str).str.strip()

    present_task_cols = []
    for col in task_cols:
        if col in user_df.columns:
            present_task_cols.append(col)
        
    id_vars = [c for c in user_df.columns if c not in task_cols]
    
    if not present_task_cols:
        st.error("No 'Task X' columns found in the uploaded userData.csv.")
        return None
        
    df_long = pd.melt(user_df, id_vars=id_vars, value_vars=present_task_cols, var_name='task_id_str', value_name='Score')

    df_long['task_id'] = df_long['task_id_str'].str.extract(r'(\d+)').astype(int)
    raw_scores = df_long['Score'].dropna()
    numeric_scores = pd.to_numeric(raw_scores.astype(str).str.replace('%', '', regex=False).str.strip(), errors='coerce')
    parsing_errors = int(numeric_scores.isnull().sum())
    
    df_long['Score'] = pd.to_numeric(df_long['Score'].astype(str).str.replace('%', '', regex=False).str.strip(), errors='coerce') / 100
    df_long.dropna(subset=['Score'], inplace=True)

    df_merged = pd.merge(df_long, tasks_df, on='task_id', how='left')

    df_merged['Skill'] = df_merged['Category']
    df_merged['Task_Prefixed'] = '[' + df_merged['Category'] + '] ' + df_merged['Task']

    if 'Comments' in df_merged.columns:
        df_merged.rename(columns={'Comments': 'Specific needs'}, inplace=True)

    total_names_in_file = user_df['Name'].nunique()

    return {
        'merged_df': df_merged,
        'user_df': user_df,
        'total_count': total_names_in_file,
        'parsing_errors': parsing_errors,
    }

@st.cache_data
def generate_csv_template(tasks_json_path: str) -> str:
    """
    Generates a template CSV string based on required columns and tasks from tasks.json.
    """
    try:
        tasks_df = pd.read_json(tasks_json_path)['skills'].apply(pd.Series)
        tasks_df.rename(columns={'id': 'task_id'}, inplace=True)
        task_cols = [f'Task {i}' for i in tasks_df['task_id']]
    except Exception as e:
        st.warning(f"Could not read tasks.json to generate template ({e}). Using 31 default tasks.")
        task_cols = [f'Task {i}' for i in range(1, 32)]

    base_headers = [
        'BPS', 
        'Team Leader', 
        'Active License', 
        'License Expiration ', 
        'Has received Affinity training of McK?', 
        'Scheduler tag', 
        'Specific Needs'
    ]
    
    all_headers = base_headers + task_cols
    
    template_df = pd.DataFrame(columns=all_headers)
    
    example_row = {
        'BPS': 'FirstName LastName',
        'Team Leader': 'Leader Name',
        'Active License': 'Yes',
        'License Expiration ': '25.10.2026',
        'Has received Affinity training of McK?': 'No',
        'Scheduler tag': 'No',
        'Specific Needs': 'Needs help with isometrics',
    }
    for col in task_cols:
        example_row[col] = '50%'

    template_df = pd.concat([template_df, pd.DataFrame([example_row])], ignore_index=True)
    
    return template_df.to_csv(sep=';', index=False, encoding='utf-8-sig')

# --- NEW FUNCTION ---
@st.cache_data
def generate_task_guide(tasks_json_path: str) -> str:
    """
    Generates a simple text list of tasks (ID and Title) from tasks.json.
    """
    try:
        tasks_df = pd.read_json(tasks_json_path)['skills'].apply(pd.Series)
        # Ensure correct columns exist after reading JSON
        tasks_df.rename(columns={'id': 'task_id', 'title': 'Task'}, inplace=True)
        
        if 'task_id' not in tasks_df.columns or 'Task' not in tasks_df.columns:
            raise ValueError("Required columns 'id' or 'title' not found in tasks.json skills list.")
        
        # Sort by task_id to ensure order
        tasks_df = tasks_df.sort_values(by='task_id')
        
        # Format the output string
        guide_lines = ["Team Skills Assessment - Task List\n", "="*35 + "\n"]
        for _, row in tasks_df.iterrows():
            guide_lines.append(f"Task {row['task_id']}: {row['Task']}\n")
            
        return "".join(guide_lines)

    except FileNotFoundError:
        return f"Error: Could not find the task definition file at {tasks_json_path}."
    except Exception as e:
        return f"Error reading or processing tasks.json: {e}"