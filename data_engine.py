# =============================
# File: data_engine.py
# =============================

import pandas as pd
from datetime import datetime
from pathlib import Path
import streamlit as st
from typing import Dict, Any, Optional, IO

# Make sure there are no syntax errors before this function definition
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
        st.error(f"Error Crítico: No se encontró tasks.json en la ruta: {tasks_json_path}")
        return None
    except Exception as e:
        st.error(f"Error Crítico al leer tasks.json: {e}")
        return None
        
    if 'task_id' not in tasks_df.columns:
        st.error("Error Crítico: 'task_id' (de 'id') no se encontró en tasks.json.")
        return None
        
    task_cols = [f'Task {i}' for i in tasks_df['task_id']]
    num_tasks = len(task_cols)

    # Read uploaded user_csv_file → user_df
    try:
        user_df = pd.read_csv(user_csv_file, sep=';', encoding='utf-8-sig')
        
    except Exception as e:
        st.error(f"Error Crítico al leer el userData.csv subido: {e}")
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
        st.error("No se encontraron columnas 'Task X' en el userData.csv subido.")
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

# --- Ensure this function definition has no errors ---
@st.cache_data
def generate_csv_template(tasks_json_path: str) -> str:
    """
    Genera un string CSV de plantilla basado en las columnas requeridas y las tareas de tasks.json.
    """
    try:
        tasks_df = pd.read_json(tasks_json_path)['skills'].apply(pd.Series)
        tasks_df.rename(columns={'id': 'task_id'}, inplace=True)
        task_cols = [f'Task {i}' for i in tasks_df['task_id']]
    except Exception as e:
        st.warning(f"No se pudo leer tasks.json para generar la plantilla ({e}). Usando 31 tareas por defecto.")
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
        'BPS': 'Nombre Apellido',
        'Team Leader': 'Nombre del Líder',
        'Active License': 'Yes',
        'License Expiration ': '25.10.2026',
        'Has received Affinity training of McK?': 'No',
        'Scheduler tag': 'No',
        'Specific Needs': 'Necesita ayuda con isométricos',
    }
    for col in task_cols:
        example_row[col] = '50%'

    template_df = pd.concat([template_df, pd.DataFrame([example_row])], ignore_index=True)
    
    return template_df.to_csv(sep=';', index=False, encoding='utf-8-sig')