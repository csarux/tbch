import streamlit as st

import sys
import os

# Agregar el directorio src al path para importar tbch
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../tbch')))

from tbch import modify_plan

st.set_page_config(page_title="Transformación de planes")

st.title("Transformación de planes entre True Beams")
st.subheader("Adaptación del MLC: Millenium <-> HD")

# Información de ayuda para los usuarios
with st.expander("ℹ️ ¿Cómo usar esta aplicación?"):
    st.markdown("""
    1. Exporta desde Eclipse el plan de tratamiento utilizando el filtro **DICOM Export Cambio Acelerador**
    1. Haz clic en **Sube un archivo DICOM RTPlan** y selecciona tu archivo `.dcm`.
    2. Espera a que la aplicación procese el archivo.
    3. Descarga el archivo modificado.
    3. Importa el plan en Eclipse utilizando el filtro **DICOM Import Cambio Acelerador**.
    3. Calcula la dosis y ajusta las UM para que la distribución coincida con la original.
    4. Si al procesar el archivo ocurre un error, revisa el mensaje mostrado y asegúrate de que el archivo sea un RTPlan válido.
    """)

uploaded_file = st.file_uploader(
    "Sube un archivo DICOM RTPlan",
    type=["dcm"]
)

if uploaded_file is not None:
    # Guardar el archivo subido temporalmente
    temp_input_path = "temp_rtplan.dcm"
    with open(temp_input_path, "wb") as f:
        f.write(uploaded_file.read())

    # Llamar a la función modify_plan
    modify_plan(dicom_file_name=temp_input_path)

    # Verificar que el archivo de salida existe
    output_file = "modified_rt.plan.dcm"
    if os.path.exists(output_file):
        st.success("El archivo modificado ha sido creado.")
        with open(output_file, "rb") as f:
            st.download_button(
                label="Descargar archivo modificado",
                data=f,
                file_name="modified_rt.plan.dcm",
                mime="application/dicom"
            )
    else:
        st.error("No se pudo crear el archivo modificado.")

    # Limpiar archivo temporal
    os.remove(temp_input_path)