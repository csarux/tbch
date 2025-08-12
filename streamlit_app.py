# streamlit_app.py - Punto de entrada directo para Streamlit Cloud
# Este archivo DEBE estar en la raíz del repositorio para que Streamlit Cloud lo detecte

import sys
import os
from pathlib import Path

# Configurar el entorno ANTES de cualquier importación de Streamlit
def setup_environment():
    """Configura el entorno para que funcione tanto en Cloud como localmente"""
    current_dir = Path(__file__).parent.absolute()
    
    # Añadir src al Python path
    src_path = current_dir / "src"
    if src_path.exists():
        sys.path.insert(0, str(src_path))
        sys.path.insert(0, str(src_path / "streamlit"))
        
        # Cambiar al directorio streamlit para que las rutas relativas funcionen
        streamlit_dir = src_path / "streamlit"
        if streamlit_dir.exists():
            os.chdir(streamlit_dir)
    
    return src_path.exists()

# Configurar entorno
if not setup_environment():
    # Si no encuentra src, mostrar error básico
    import streamlit as st
    st.error("❌ Error: No se puede encontrar la estructura del proyecto")
    st.error(f"Directorio actual: {Path(__file__).parent}")
    st.stop()

# Ahora importar y ejecutar la aplicación principal
try:
    # Importar directamente desde la estructura configurada
    from src.streamlit.app import *
except ImportError:
    try:
        # Fallback: ejecutar el contenido del archivo directamente
        app_file = Path(__file__).parent / "src" / "streamlit" / "app.py"
        if app_file.exists():
            with open(app_file, "r", encoding="utf-8") as f:
                exec(f.read())
        else:
            import streamlit as st
            st.error("❌ No se puede encontrar app.py")
            st.error(f"Buscando en: {app_file}")
    except Exception as e:
        import streamlit as st
        st.error(f"❌ Error ejecutando la aplicación: {e}")
        st.error(f"Directorio de trabajo: {os.getcwd()}")
        st.error(f"Python path: {sys.path[:5]}")  # Solo primeros 5 para no saturar
