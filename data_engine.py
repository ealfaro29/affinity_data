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
    Uses st.warning for non-critical file reading errors.
    """

    # Read tasks.json -> tasks_df
    try:
        tasks_df = pd.read_json(tasks_json_path)['skills'].apply(pd.Series)
        tasks_df.rename(columns={'title': 'Task', 'id': 'task_id', 'category': 'Category'}, inplace=True)
    except FileNotFoundError:
        st.warning(f"Warning: tasks.json not found at path: {tasks_json_path}. Cannot validate task list.") # Use warning
        return None # Critical if tasks.json missing
    except Exception as e:
        st.warning(f"Warning: Could not read tasks.json: {e}. Cannot validate task list.") # Use warning
        return None # Critical if tasks.json unreadable

    if 'task_id' not in tasks_df.columns:
        st.warning("Warning: 'task_id' (from 'id') not found in tasks.json. Cannot process tasks.") # Use warning
        return None # Critical

    task_cols = [f'Task {i}' for i in tasks_df['task_id']]
    num_tasks = len(task_cols)

    # Read uploaded user_csv_file -> user_df
    try:
        user_df = pd.read_csv(user_csv_file, sep=';', encoding='utf-8-sig')

    except Exception as e:
        st.warning(f"Warning: Could not read uploaded CSV file: {e}. Please check the format.") # Use warning
        return None # Critical if CSV unreadable

    # Normalize headers and key columns
    user_df.columns = user_df.columns.str.strip()
    user_df.rename(columns={
        'BPS': 'Name',
        'Specific Needs': 'Comments',
        'Has received Affinity training of McK?': 'Has received Affinity training of McK?',
        'License Expiration ': 'License Expiration'
    }, inplace=True)

    if 'Name' not in user_df.columns:
         st.warning("Warning: Required column 'BPS' (renamed to 'Name') not found in the CSV.") # Use warning
         return None # Critical if Name is missing

    user_df.dropna(subset=['Name'], inplace=True)
    if user_df.empty:
        st.warning("Warning: No rows with valid 'Name' found in the CSV.") # Use warning
        # Allow processing to continue, might result in empty dashboard
        # return None

    yes_values = {'yes', 'si', 'sí', 'true', '1', 'y', 't'}
    for col in ['Active License', 'Has received Affinity training of McK?', 'Scheduler tag']:
        if col in user_df.columns:
            user_df[col] = user_df[col].astype(str).str.strip().str.lower().isin(yes_values)
        else:
            user_df[col] = False # Add missing boolean columns as False

    if 'License Expiration' in user_df.columns:
        user_df['License Expiration'] = pd.to_datetime(user_df['License Expiration'], errors='coerce', dayfirst=True)
    # else: # Handle missing date column if needed, maybe add as NaT
        # user_df['License Expiration'] = pd.NaT

    for col in user_df.select_dtypes(include=['object']).columns:
        user_df[col] = user_df[col].fillna('').astype(str).str.strip()

    # Unpivot Task 1..N into long format
    present_task_cols = []
    missing_task_cols_for_warning = []
    for col in task_cols:
        if col in user_df.columns:
            present_task_cols.append(col)
        else:
            missing_task_cols_for_warning.append(col) # Track missing Task columns

    if missing_task_cols_for_warning:
        st.info(f"Info: The following task columns expected from tasks.json were not found in the CSV and will be ignored: {', '.join(missing_task_cols_for_warning)}") # Use info

    id_vars = [c for c in user_df.columns if c not in task_cols]

    if not present_task_cols:
        st.warning("Warning: No 'Task X' columns found in the uploaded userData.csv.") # Use warning
        # Return minimal structure to avoid breaking app, but dashboard will show warnings
        return {
            'merged_df': pd.DataFrame(),
            'user_df': user_df,
            'total_count': user_df['Name'].nunique(),
            'parsing_errors': 0,
        }

    df_long = pd.melt(user_df, id_vars=id_vars, value_vars=present_task_cols, var_name='task_id_str', value_name='Score')

    # Extract numeric task_id and parse percentage scores
    df_long['task_id'] = df_long['task_id_str'].str.extract(r'(\d+)').astype(int)
    raw_scores = df_long['Score'].dropna()
    # Attempt conversion, coercing errors to NaN
    numeric_scores = pd.to_numeric(raw_scores.astype(str).str.replace('%', '', regex=False).str.strip(), errors='coerce')
    parsing_errors = int(numeric_scores.isnull().sum()) # Count how many failed

    # Convert valid scores, keep NaNs for invalid ones temporarily
    df_long['Score'] = pd.to_numeric(df_long['Score'].astype(str).str.replace('%', '', regex=False).str.strip(), errors='coerce') / 100
    # Drop rows where Score could NOT be converted (parsing errors)
    df_long.dropna(subset=['Score'], inplace=True)

    # Merge with tasks catalog
    # Use left merge to keep all user rows even if task_id is somehow invalid
    df_merged = pd.merge(df_long, tasks_df, on='task_id', how='left')

    # Handle potential merge issues if tasks.json was problematic
    if df_merged['Task'].isnull().any():
        st.warning("Warning: Some task scores could not be matched with task details from tasks.json. Check task IDs.")

    # Convenience columns - Check if merge columns exist before creating
    if 'Category' in df_merged.columns:
        df_merged['Skill'] = df_merged['Category']
    else:
        df_merged['Skill'] = 'Unknown'

    if 'Category' in df_merged.columns and 'Task' in df_merged.columns:
         df_merged['Task_Prefixed'] = '[' + df_merged['Category'].fillna('Unknown') + '] ' + df_merged['Task'].fillna('Unknown Task')
    elif 'Task' in df_merged.columns:
         df_merged['Task_Prefixed'] = df_merged['Task'].fillna('Unknown Task')
    else:
         df_merged['Task_Prefixed'] = 'Task ' + df_merged['task_id'].astype(str)


    # Align Comments naming across views
    if 'Comments' in df_merged.columns: # Check if 'Comments' survived the melt/merge
        df_merged.rename(columns={'Comments': 'Specific needs'}, inplace=True)

    total_names_in_file = user_df['Name'].nunique()

    return {
        'merged_df': df_merged,
        'user_df': user_df,
        'total_count': total_names_in_file,
        'parsing_errors': parsing_errors, # Report the count
    }

@st.cache_data
def generate_csv_template(tasks_json_path: str) -> str:
    """
    Generates a template CSV string (Emoji-Free).
    """
    try:
        tasks_df = pd.read_json(tasks_json_path)['skills'].apply(pd.Series)
        tasks_df.rename(columns={'id': 'task_id'}, inplace=True)
        task_cols = [f'Task {i}' for i in tasks_df['task_id']]
    except Exception as e:
        st.warning(f"Warning: Could not read tasks.json to generate template ({e}). Using 31 default tasks.") # Use warning
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

    # Create DataFrame from the single example row dictionary
    example_df = pd.DataFrame([example_row], columns=all_headers) # Ensure columns match template

    # Concatenate the empty template_df with the example_df
    template_df = pd.concat([template_df, example_df], ignore_index=True)


    return template_df.to_csv(sep=';', index=False, encoding='utf-8-sig')


@st.cache_data
def generate_task_guide(tasks_json_path: str) -> str:
    """
    Generates a simple text list of tasks (Emoji-Free).
    """
    try:
        tasks_df = pd.read_json(tasks_json_path)['skills'].apply(pd.Series)
        tasks_df.rename(columns={'id': 'task_id', 'title': 'Task'}, inplace=True)

        if 'task_id' not in tasks_df.columns or 'Task' not in tasks_df.columns:
            raise ValueError("Required columns 'id' or 'title' not found in tasks.json skills list.")

        tasks_df = tasks_df.sort_values(by='task_id')

        guide_lines = ["Team Skills Assessment - Task List\n", "="*35 + "\n"]
        for _, row in tasks_df.iterrows():
            guide_lines.append(f"Task {row['task_id']}: {row['Task']}\n")

        return "".join(guide_lines)

    except FileNotFoundError:
        return f"Warning: Could not find the task definition file at {tasks_json_path}." # Use warning
    except Exception as e:
        return f"Warning: Error reading or processing tasks.json: {e}" # Use warning