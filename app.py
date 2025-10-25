# =============================
# File: app.py
# =============================

import streamlit as st
import pandas as pd
from config import DEVELOPMENT_MODE
# --- Ensure this import matches the function name below ---
from data_engine import load_and_process_data, generate_csv_template
from analytics_engine import compute_analytics, analyze_comment_themes
from ui_components import (
    render_strategic_overview,
    render_affinity_status,
    render_team_profiles,
    render_skill_analysis,
    render_action_workbench,
    login_page
)
from typing import Dict, Any

# Page configuration
st.set_page_config(
    page_title="Team Skills Hub v3.1",
    layout="wide",
    initial_sidebar_state="expanded"
)

def upload_landing_page():
    """
    Renders the file upload screen. This page is shown after login
    but before data is loaded.
    """
    st.title("🚀 Welcome to the Team Skills Hub")
    st.markdown("Sigue los pasos para analizar los skills de tu equipo.")

    tasks_json_path = "tasks.json" 

    with st.container(border=True):
        st.subheader("Paso 1: Descarga la Plantilla (Opcional)")
        st.markdown("Si no tienes un archivo, descarga la plantilla para llenarla con tus datos. El archivo ya tiene las columnas y el formato correcto.")
        
        try:
            # --- Ensure this function call matches the name below ---
            template_csv = generate_csv_template(tasks_json_path)
            st.download_button(
                label="📥 Descargar Plantilla CSV",
                data=template_csv,
                file_name="skills_template.csv",
                mime="text/csv",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"No se pudo generar la plantilla: {e}")
            st.info("Asegúrate de que el archivo `tasks.json` esté presente en el directorio de la app.")

    with st.container(border=True):
        st.subheader("Paso 2: Sube tu Archivo de Datos")
        
        uploaded_csv = st.file_uploader(
            "Sube tu archivo `userData.csv` (o el que llenaste con la plantilla)", 
            type="csv",
            label_visibility="collapsed"
        )

    # --- AUTO-SUBMIT LOGIC ---
    if uploaded_csv is not None:
        if 'processed_data' not in st.session_state: 
            with st.spinner(f"Procesando '{uploaded_csv.name}'... Esto puede tardar un momento."):
                data = load_and_process_data(uploaded_csv, tasks_json_path)
            
            if data is not None and not data['merged_df'].empty:
                st.session_state.processed_data = data
                st.session_state.data_loaded = True
                st.success("¡Datos cargados con éxito! 🎉")
                st.rerun()
            elif data is not None and data['merged_df'].empty:
                st.error("Proceso completado, pero no se encontraron datos de skills válidos en el archivo. Revisa tu archivo y súbelo de nuevo.")
                st.session_state.data_loaded = False
            else:
                st.error("Hubo un error procesando tu archivo. Revisa el formato y los nombres de las columnas.")
                st.session_state.data_loaded = False
                if 'processed_data' in st.session_state:
                    del st.session_state.processed_data
        
        elif st.session_state.data_loaded:
            st.rerun()


def main_app():
    """Renders the main application interface."""
    
    if 'processed_data' not in st.session_state:
        st.error("Datos no encontrados. Por favor, súbelos de nuevo.")
        st.session_state.data_loaded = False
        st.rerun()
        return

    data = st.session_state.processed_data
    
    # --- Sidebar ---
    st.sidebar.title("🚀 Team Skills Hub")
    st.sidebar.info("Plataforma estratégica para inteligencia de talento y desarrollo de equipos.")
    
    if st.sidebar.button("Subir Nuevos Datos"):
        st.session_state.data_loaded = False
        if 'processed_data' in st.session_state:
            del st.session_state.processed_data
        st.rerun()

    # --- Extract data ---
    df_merged: pd.DataFrame = data['merged_df']
    user_df: pd.DataFrame = data['user_df']
    total_participants_in_file: int = data['total_count']
    score_parsing_errors: int = data['parsing_errors']

    if df_merged.empty:
        st.warning("No se encontraron participantes con puntuaciones válidas en el archivo subido.")
        st.stop()

    # --- Analytics Engine ---
    analytics: Dict[str, Any] = compute_analytics(df_merged, user_df)
    
    all_comments = user_df['Comments'].dropna().str.strip()
    all_comments = all_comments[all_comments != '']
    if not all_comments.empty:
        analytics['comment_themes'] = analyze_comment_themes(all_comments)
    else:
        analytics['comment_themes'] = pd.DataFrame(columns=['Mentions'])
    
    # --- UI Rendering ---
    st.title("🚀 Team Skills Hub v3.1")

    tabs = st.tabs([
        "📈 Resumen Estratégico",
        "⭐ Estatus de Affinity",
        "👤 Perfiles de Equipo",
        "🧠 Análisis de Skills",
        "🔭 Panel de Acción",
    ])

    with tabs[0]:
        render_strategic_overview(df_merged, user_df, analytics, total_participants_in_file, score_parsing_errors)
    with tabs[1]:
        render_affinity_status(user_df, analytics)
    with tabs[2]:
        render_team_profiles(df_merged, user_df, analytics)
    with tabs[3]:
        render_skill_analysis(df_merged, analytics)
    with tabs[4]:
        render_action_workbench(df_merged, analytics)


# --- Main execution (State Machine) ---
if __name__ == "__main__":
    
    if 'data_loaded' not in st.session_state:
        st.session_state.data_loaded = False
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        
    if DEVELOPMENT_MODE:
        st.session_state.logged_in = True 

    if not st.session_state.logged_in:
        login_page()
    elif not st.session_state.data_loaded:
        upload_landing_page()
    else:
        main_app()