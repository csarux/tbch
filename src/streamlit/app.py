# Configuración de página debe ser la primera llamada a Streamlit
import streamlit as st
st.set_page_config(
    page_title="MLC Position Converter",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

import json
import sys
import os
from pathlib import Path

# Configuración simple de rutas
current_file = Path(__file__).resolve()
current_dir = current_file.parent

# Añadir rutas al path
sys.path.insert(0, str(current_dir))  # Para i18n
sys.path.insert(0, str(current_dir.parent))  # Para tbch desde src/

# Archivo de configuración
CONFIG_FILE = current_dir / "linac_config.json"

# Importar módulos necesarios
try:
    from tbch import modify_plan, plot_mlc_aperture, Leaf0PositionBoundary_Millenium, Leaf0PositionBoundary_HD, load_linac_config, save_linac_config, set_i18n
except ImportError as e:
    st.error(f"❌ Error importing tbch module: {e}")
    st.error(f"📁 Current working directory: {os.getcwd()}")
    st.error(f"📁 Current directory: {current_dir}")
    st.error(f"🐍 Python path (first 10):")
    for i, path in enumerate(sys.path[:10]):
        st.error(f"  {i}: {path}")
    st.stop()

try:
    from i18n import i18n, get_language_selector
except ImportError as e:
    st.error(f"❌ Error importing i18n module: {e}")
    st.error(f"📁 Current directory: {current_dir}")
    st.error(f"📄 Files in current directory: {list(current_dir.glob('*.py'))}")
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
    if uploaded_file is not None:
        try:
            # Llamar a la función modify_plan
            modify_plan(dicom_file_name=temp_input_path, config_path=CONFIG_FILE)

            # Verificar que el archivo de salida existe
            output_file = "modified_rt.plan.dcm"
            if os.path.exists(output_file):
                st.success(i18n.t("transformation_tab.success_message"))
                with open(output_file, "rb") as f:
                    st.download_button(
                        label=i18n.t("transformation_tab.download_button_label"),
                        data=f,
                        file_name="modified_rt.plan.dcm",
                        mime="application/dicom"
                    )
            else:
                st.error(i18n.t("transformation_tab.error_message"))
        except Exception as e:
            st.error(f"Error: {str(e)}")

with tab2:
    import pydicom
    import matplotlib.pyplot as plt

    fig = None
    fig, ax = plt.subplots(figsize=(10, 10), dpi=120)

    if uploaded_file is not None:
        try:
            # Leer el archivo DICOM
            ds = pydicom.dcmread(temp_input_path)
            # Identificar el tipo de MLC
            Leaf0PositionBoundary = float(ds.BeamSequence[0].BeamLimitingDeviceSequence[2].LeafPositionBoundaries[0])
            if Leaf0PositionBoundary == Leaf0PositionBoundary_Millenium:
                input_MLC_type = i18n.t("mlc_types.millenium")
                output_MLC_type = i18n.t("mlc_types.hd")
            elif Leaf0PositionBoundary == Leaf0PositionBoundary_HD:
                input_MLC_type = i18n.t("mlc_types.hd")
                output_MLC_type = i18n.t("mlc_types.millenium")
            else:
                input_MLC_type = i18n.t("mlc_types.unknown")

            # Obtener la lista de campos
            beams = ds.BeamSequence
            beam_display_indices = [f"{i18n.t('visualization_tab.beam_display_prefix')} {i+1}" for i in range(len(beams))]
            beam_index = st.selectbox(
                i18n.t("visualization_tab.beam_selector_label"), 
                range(len(beams)), 
                format_func=lambda i: beam_display_indices[i]
            )

            # Seleccionar el campo y su secuencia de puntos de control
            beam = beams[beam_index]
            cps = beam.ControlPointSequence
            num_cps = len(cps)

            # Slider para seleccionar punto de control
            cp_index = st.slider(i18n.t("visualization_tab.control_point_slider_label"), 1, num_cps, 1) - 1

            plot_mlc_aperture(beam, cp_index, MLC_type=input_MLC_type, ax=ax, alpha=0.7)

            output_file = "modified_rt.plan.dcm"
            if os.path.exists(output_file):
                output_ds = pydicom.dcmread(output_file)
                output_beams = output_ds.BeamSequence
                output_beam = output_beams[beam_index]
                plot_mlc_aperture(output_beam, cp_index, MLC_type=output_MLC_type, ax=ax, alpha=0.5)
            
            # Mostrar los índices seleccionados
            st.write(f"{i18n.t('visualization_tab.selected_beam_label')} {beam_index + 1}")
            st.write(f"{i18n.t('visualization_tab.selected_cp_label')} {cp_index + 1}")

            if fig is not None:
                st.pyplot(fig, clear_figure=False)
        except Exception as e:
            st.error(f"Error: {str(e)}")

with tab3:
    st.subheader(i18n.t("configuration_tab.title"))

    try:
        config = load_linac_config(config_path=CONFIG_FILE)

        # Guardaremos las modificaciones en un dict temporal
        new_config = {}

        for accelerator_type, params in config.items():
            st.markdown(f"### {accelerator_type}")
            col1, col2 = st.columns(2)

            with col1:
                device_serial = st.text_input(
                    f"{i18n.t('configuration_tab.device_serial_label')} ({accelerator_type})",
                    value=params.get("DeviceSerialNumber", ""),
                    key=f"serial_{accelerator_type}"
                )

            with col2:
                machine_name = st.text_input(
                    f"{i18n.t('configuration_tab.machine_name_label')} ({accelerator_type})",
                    value=params.get("TreatmentMachineName", ""),
                    key=f"machine_{accelerator_type}"
                )

            new_config[accelerator_type] = {
                "DeviceSerialNumber": device_serial,
                "TreatmentMachineName": machine_name
            }

        if st.button(i18n.t("configuration_tab.save_button")):
            save_linac_config(new_config, config_path=CONFIG_FILE)
            st.success(i18n.t("configuration_tab.save_success"))
    except Exception as e:
        st.error(f"Error: {str(e)}")

# Cleanup al final
import atexit
def cleanup_temp_file():
    if os.path.exists("./temp_rtplan.dcm"):
        try:
            os.remove("./temp_rtplan.dcm")
        except Exception:
            pass
atexit.register(cleanup_temp_file)
