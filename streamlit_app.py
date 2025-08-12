# streamlit_app.py - Punto de entrada robusto para Streamlit Cloud
import sys
import os
from pathlib import Path

# Configurar rutas para Streamlit Cloud
current_dir = Path(__file__).parent

# Buscar la estructura del proyecto en diferentes ubicaciones posibles
project_paths = [
    current_dir,  # Si está en la raíz
    current_dir / "src",  # Si src está en la raíz  
    Path("/mount/src/CambioAcelerador"),  # Cloud mount específico
    Path("/mount/src/cambio-acelerador"),  # Cloud mount alternativo
]

src_path = None
app_path = None

# Buscar la aplicación
for base_path in project_paths:
    potential_app = base_path / "src" / "streamlit" / "app.py"
    if potential_app.exists():
        src_path = base_path / "src"
        app_path = potential_app
        break

if src_path and app_path:
    # Configurar rutas
    sys.path.insert(0, str(src_path))
    sys.path.insert(0, str(app_path.parent))
    
    # Cambiar al directorio de la aplicación
    os.chdir(app_path.parent)
    
    # Ejecutar la aplicación
    try:
        with open(app_path, "r", encoding="utf-8") as f:
            exec(f.read())
    except Exception as e:
        import streamlit as st
        st.error(f"❌ Error ejecutando la aplicación: {e}")
        st.error(f"📁 Directorio actual: {Path.cwd()}")
        st.error(f"📁 App path: {app_path}")
else:
    import streamlit as st
    st.error("❌ No se pudo encontrar la aplicación")
    st.error(f"📁 Directorio actual: {current_dir}")
    st.error("🔍 Rutas buscadas:")
    for path in project_paths:
        app_check = path / "src" / "streamlit" / "app.py"
        st.error(f"  - {app_check} (existe: {app_check.exists()})")
