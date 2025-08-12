# streamlit_app.py - Punto de entrada para Streamlit Cloud
# Redirige a la aplicación principal en src/streamlit/app.py

import sys
import os
from pathlib import Path

# Configurar rutas antes de cualquier importación de Streamlit
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
streamlit_dir = src_dir / "streamlit"

# Agregar directorios al path
sys.path.insert(0, str(src_dir))
sys.path.insert(0, str(streamlit_dir))

# Cambiar al directorio de la aplicación
os.chdir(streamlit_dir)

# Importar y ejecutar los contenidos de app.py
import streamlit as st

# Configuración de página debe ser lo primero
st.set_page_config(
    page_title="MLC Position Converter",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

import json
from pathlib import Path

# Archivo de configuración con parámetros específicos del acelerador
CONFIG_FILE = streamlit_dir / "linac_config.json"

try:
    from tbch import modify_plan, plot_mlc_aperture, Leaf0PositionBoundary_Millenium, Leaf0PositionBoundary_HD, load_linac_config, save_linac_config, set_i18n
except ImportError as e:
    st.error(f"❌ Error importing tbch module: {e}")
    st.error(f"📁 Current working directory: {os.getcwd()}")
    st.error(f"🐍 Python path entries:")
    for i, path in enumerate(sys.path):
        st.error(f"  {i}: {path}")
    st.stop()

try:
    from i18n import i18n, get_language_selector
except ImportError as e:
    st.error(f"❌ Error importing i18n module: {e}")
    st.error(f"📁 Current directory: {streamlit_dir}")
    st.error(f"📄 Files in current directory: {list(streamlit_dir.glob('*.py'))}")
    st.stop()

# Configurar el sistema de traducciones en tbch
set_i18n(i18n)

# Selector de idioma en la barra lateral
selected_language = get_language_selector()

st.title(i18n.t("main_interface.app_title"))
st.subheader(i18n.t("main_interface.app_subtitle"))

# Información de ayuda para los usuarios
with st.expander(i18n.t("main_interface.help_expander_title")):
    st.markdown(i18n.t("main_interface.help_instructions"))

uploaded_file = st.file_uploader(
    i18n.t("main_interface.file_uploader_label"),
    type=["dcm"]
)

if uploaded_file is not None:
    # Guardar el archivo subido temporalmente
    temp_input_path = "./temp_rtplan.dcm"
    with open(temp_input_path, "wb") as f:
        f.write(uploaded_file.read())

    tab1, tab2, tab3 = st.tabs([
        i18n.t("tabs.transformation"),
        i18n.t("tabs.mlc_visualization"),
        i18n.t("tabs.configuration")
    ])

    with tab1:
        st.subheader(i18n.t("transformation.section_title"))
        
        conversion_type = st.radio(
            i18n.t("transformation.conversion_type_label"),
            [
                i18n.t("transformation.millennium_to_hd"),
                i18n.t("transformation.hd_to_millennium")
            ]
        )
        
        if st.button(i18n.t("transformation.transform_button"), type="primary", use_container_width=True):
            with st.spinner(i18n.t("transformation.processing_message")):
                try:
                    # Crear archivo de salida
                    output_path = "./transformed_plan.dcm"
                    
                    # Procesar el plan (la función detecta automáticamente el tipo de MLC)
                    modify_plan(temp_input_path, output_path, str(CONFIG_FILE))
                    
                    if os.path.exists(output_path):
                        st.success(i18n.t("transformation.success_message"))
                        
                        # Botón de descarga
                        with open(output_path, "rb") as file:
                            st.download_button(
                                label=i18n.t("transformation.download_button"),
                                data=file,
                                file_name=f"transformed_plan.dcm",
                                mime="application/octet-stream",
                                use_container_width=True
                            )
                        
                        # Mostrar información del resultado
                        st.info(i18n.t("transformation.result_info"))
                        
                    else:
                        st.error(i18n.t("transformation.error_processing"))
                        
                except Exception as e:
                    st.error(i18n.t("transformation.error_occurred").format(error=str(e)))

    with tab2:
        st.subheader(i18n.t("visualization.section_title"))
        
        control_point = st.slider(
            i18n.t("visualization.control_point_label"),
            min_value=0,
            max_value=100,
            value=0,
            help=i18n.t("visualization.control_point_help")
        )
        
        if st.button(i18n.t("visualization.generate_plot_button"), use_container_width=True):
            try:
                import pydicom
                import matplotlib.pyplot as plt
                
                # Cargar el plan DICOM
                ds = pydicom.dcmread(temp_input_path)
                
                # Detectar tipo de MLC
                Leaf0PositionBoundary = float(ds.BeamSequence[0].BeamLimitingDeviceSequence[2].LeafPositionBoundaries[0])
                if Leaf0PositionBoundary == Leaf0PositionBoundary_Millenium:
                    mlc_type = "Millenium"
                elif Leaf0PositionBoundary == Leaf0PositionBoundary_HD:
                    mlc_type = "HD"
                else:
                    mlc_type = "Unknown"
                
                # Crear figura
                fig, ax = plt.subplots(figsize=(10, 8))
                
                # Plotear apertura
                beam = ds.BeamSequence[0]  # Primer haz
                max_cp = len(beam.ControlPointSequence) - 1
                cp_to_plot = min(control_point, max_cp)
                
                plot_mlc_aperture(beam, cp_to_plot, mlc_type, ax)
                
                st.pyplot(fig)
                st.success(i18n.t("visualization.plot_generated"))
                    
            except Exception as e:
                st.error(i18n.t("visualization.error_generating_plot").format(error=str(e)))

    with tab3:
        st.subheader(i18n.t("configuration.section_title"))
        st.info(i18n.t("configuration.description"))
        
        if os.path.exists(CONFIG_FILE):
            config = load_linac_config(CONFIG_FILE)
            
            st.write(i18n.t("configuration.current_settings"))
            
            # Configuración para Millennium
            st.write("**Millennium MLC:**")
            millennium_serial = st.text_input(
                i18n.t("configuration.serial_number"),
                value=config.get("Millenium", {}).get("DeviceSerialNumber", ""),
                key="millennium_serial"
            )
            millennium_name = st.text_input(
                i18n.t("configuration.machine_name"),
                value=config.get("Millenium", {}).get("TreatmentMachineName", ""),
                key="millennium_name"
            )
            
            # Configuración para HD
            st.write("**HD MLC:**")
            hd_serial = st.text_input(
                i18n.t("configuration.serial_number"),
                value=config.get("HD", {}).get("DeviceSerialNumber", ""),
                key="hd_serial"
            )
            hd_name = st.text_input(
                i18n.t("configuration.machine_name"),
                value=config.get("HD", {}).get("TreatmentMachineName", ""),
                key="hd_name"
            )
            
            if st.button(i18n.t("configuration.save_button"), type="primary"):
                new_config = {
                    "Millenium": {
                        "DeviceSerialNumber": millennium_serial,
                        "TreatmentMachineName": millennium_name
                    },
                    "HD": {
                        "DeviceSerialNumber": hd_serial,
                        "TreatmentMachineName": hd_name
                    }
                }
                
                try:
                    save_linac_config(new_config, str(CONFIG_FILE))
                    st.success(i18n.t("configuration.save_success"))
                    st.rerun()
                except Exception as e:
                    st.error(i18n.t("configuration.save_error"))
        else:
            st.error(i18n.t("configuration.file_not_found"))
else:
    st.info(i18n.t("main_interface.upload_instructions"))
