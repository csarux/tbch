import json
import streamlit as st
from pathlib import Path

import sys
import os

# Archivo de configuración con parámetros específicos del acelerador
# Usar ruta absoluta basada en la ubicación del script
current_dir = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(current_dir, "linac_config.json")

# Agregar el directorio src al path para importar tbch
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../tbch')))

from tbch import modify_plan, plot_mlc_aperture, Leaf0PositionBoundary_Millenium, Leaf0PositionBoundary_HD, load_linac_config, save_linac_config

st.set_page_config(page_title="Transformación de planes")

st.title("Transformación de planes entre True Beams")
st.subheader("Adaptación del MLC: Millenium <-> HD")

# Información de ayuda para los usuarios
with st.expander("ℹ️ ¿Cómo usar esta aplicación?"):
    st.markdown("""
    1. Exporta desde Eclipse el plan de tratamiento utilizando el filtro **DICOM Export Cambio Acelerador**
    1. Haz clic en **Sube un archivo DICOM RTPlan** y selecciona tu archivo `.dcm`.
    2. Espera a que la aplicación procese el archivo. En la solapa `Visualización del MLC` podrás comprobar el resultado de la transformación. Si al procesar el archivo ocurre un error, revisa el mensaje mostrado y asegúrate de que el archivo sea un RTPlan válido.
    3. Descarga el archivo modificado.
    3. Importa el plan en Eclipse utilizando el filtro **DICOM Import Cambio Acelerador**.
    3. Calcula la dosis y ajusta las UM para que la distribución coincida con la original.
    """)

uploaded_file = st.file_uploader(
    "Sube un archivo DICOM RTPlan",
    type=["dcm"]
)

if uploaded_file is not None:
    # Guardar el archivo subido temporalmente
    temp_input_path = "./temp_rtplan.dcm"
    with open(temp_input_path, "wb") as f:
        f.write(uploaded_file.read())

tab1, tab2, tab3 = st.tabs(["Transformación", "Visualización del MLC", "Configuración"])

with tab1:
    if uploaded_file is not None:
        # Llamar a la función modify_plan
        modify_plan(dicom_file_name=temp_input_path, config_path=CONFIG_FILE)

        # Verificar que el archivo de salida existe
        output_file = "modified_rt.plan.dcm"
        if os.path.exists(output_file):
            st.success("El nuevo plan DICOM con el MLC adaptado ha sido creado.")
            with open(output_file, "rb") as f:
                st.download_button(
                    label="Descargar archivo modificado",
                    data=f,
                    file_name="modified_rt.plan.dcm",
                    mime="application/dicom"
                )
        else:
            st.error("No se pudo crear el archivo modificado.")

        # Nota: No eliminamos el archivo temporal aquí para que esté disponible en la pestaña de visualización.
        # La eliminación se realizará al final del script.
        # os.remove(temp_input_path)

with tab2:
    import pydicom
    import matplotlib.pyplot as plt

    fig = None
    fig, ax = plt.subplots(figsize=(10, 10), dpi=120)

    if uploaded_file is not None:
        # Leer el archivo DICOM
        ds = pydicom.dcmread(temp_input_path)
        # Identificar el tipo de MLC mediante el valor del PositionBoundary de la primera lámina del MLC (BeamLimitingDevice[2]) del primer campo
        Leaf0PositionBoundary = float(ds.BeamSequence[0].BeamLimitingDeviceSequence[2].LeafPositionBoundaries[0])
        if Leaf0PositionBoundary == Leaf0PositionBoundary_Millenium:
            input_MLC_type = "Millenium"
            output_MLC_type = "HD"
        elif Leaf0PositionBoundary == Leaf0PositionBoundary_HD:
            input_MLC_type = "HD"
            output_MLC_type = "Millenium"
        else:
            input_MLC_type = "Desconocido"

        # Obtener la lista de campos
        beams = ds.BeamSequence
        # Mostrar los índices desde 1 en el selectbox
        beam_display_indices = [f"Campo {i+1}" for i in range(len(beams))]
        beam_index = st.selectbox("Selecciona el campo", range(len(beams)), format_func=lambda i: beam_display_indices[i])

        # Seleccionar el campo y su secuencia de puntos de control
        beam = beams[beam_index]
        cps = beam.ControlPointSequence
        num_cps = len(cps)

        # Slider para seleccionar punto de control, mostrando desde 1
        cp_index = st.slider("Selecciona el punto de control", 1, num_cps, 1) - 1

        plot_mlc_aperture(beam, cp_index, MLC_type=input_MLC_type, ax=ax, alpha=0.7)

        if output_file is not None:
            output_ds = pydicom.dcmread(output_file)
            output_beams = output_ds.BeamSequence
            output_beam = output_beams[beam_index]
            plot_mlc_aperture(output_beam, cp_index, MLC_type=output_MLC_type, ax=ax, alpha=0.5)
        
        # Mostrar los índices seleccionados al usuario (contando desde 1)
        st.write(f"Campo seleccionado: {beam_index + 1}")
        st.write(f"Punto de control seleccionado: {cp_index + 1}")

        if fig is not None:
            st.pyplot(fig, clear_figure=False)

with tab3:
    st.subheader("Configuración de Aceleradores")

    config = load_linac_config(config_path=CONFIG_FILE)

    # Guardaremos las modificaciones en un dict temporal
    new_config = {}

    for accelerator_type, params in config.items():
        st.markdown(f"### {accelerator_type}")
        col1, col2 = st.columns(2)

        with col1:
            device_serial = st.text_input(
                f"DeviceSerialNumber ({accelerator_type})",
                value=params.get("DeviceSerialNumber", ""),
                key=f"serial_{accelerator_type}"
            )

        with col2:
            machine_name = st.text_input(
                f"TreatmentMachineName ({accelerator_type})",
                value=params.get("TreatmentMachineName", ""),
                key=f"machine_{accelerator_type}"
            )

        new_config[accelerator_type] = {
            "DeviceSerialNumber": device_serial,
            "TreatmentMachineName": machine_name
        }

    if st.button("💾 Guardar configuración"):
        save_linac_config(new_config, config_path=CONFIG_FILE)
        st.success("Archivo de configuración guardado correctamente.")

            
# Al final del script, eliminar el archivo temporal si existe
import atexit
def cleanup_temp_file():
    if os.path.exists("./temp_rtplan.dcm"):
        try:
            os.remove("./temp_rtplan.dcm")
        except Exception:
            pass
atexit.register(cleanup_temp_file)