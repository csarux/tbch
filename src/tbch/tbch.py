'''
tbch.py - Módulo de conversión y modificación de posiciones de láminas MLC en archivos DICOM RT Plan
-------------------------------------------------------------------------------
Autor:        Juan Calama, César Rodríguez
Versión:      1.0
Fecha:        09/07/2025
Descripción:  
    Este módulo proporciona funciones para convertir posiciones de láminas entre 
    colimadores multi-hoja (MLC) de tipo Millennium y HD, así como para modificar 
    archivos DICOM de planes de radioterapia (RT Plan) adaptando las posiciones 
    de las láminas y los metadatos del plan según el tipo de acelerador lineal 
    (TrueBeam2 o TrueBeam3). Incluye utilidades para asegurar la compatibilidad 
    de los campos y la integridad de los datos al migrar planes entre diferentes 
    configuraciones de hardware.
Requisitos:
    - pydicom
    - numpy
    - warnings
-------------------------------------------------------------------------------
Funciones
---------
convert_millennium_to_hd_positions(millennium_positions)
    Convierte las posiciones de las láminas de un MLC Millennium a las posiciones 
    equivalentes en un MLC HD.
    Parámetros
    ----------
    millennium_positions : list[float] o np.ndarray
        Lista o array de 120 posiciones de láminas correspondientes a un MLC Millennium.
    Retorna
    -------
    list[float]
        Lista de 120 posiciones de láminas adaptadas al formato del MLC HD.
    Notas
    -----
    La conversión se realiza según un mapeo específico de índices y reglas de 
    interpolación para asegurar la correspondencia física entre ambos tipos de MLC.

convert_hd_to_millennium_positions(hd_positions)
    Convierte las posiciones de las láminas de un MLC HD a las posiciones 
    equivalentes en un MLC Millennium, promediando posiciones cuando es necesario.
    Parámetros
    ----------
    hd_positions : list[float] o np.ndarray
        Lista o array de 120 posiciones de láminas correspondientes a un MLC HD.
    Retorna
    -------
    list[float]
        Lista de 120 posiciones de láminas adaptadas al formato del MLC Millennium.
    Notas
    -----
    Se realiza un ajuste para evitar que las láminas enfrentadas queden a menos 
    de 0.5 mm, previniendo advertencias o errores en la importación del plan.

modify_plan(dicom_file_name='RP.T3.dcm', output_file_name='modified_rt.plan.dcm')
    Modifica un archivo DICOM de planificación de radioterapia (RT Plan) 
    reasignando las posiciones de las láminas del MLC y adaptando los metadatos 
    del plan según el tipo de acelerador.
    Parámetros
    ----------
    dicom_file_name : str, opcional
        Nombre del archivo DICOM de entrada (por defecto 'RP.T3.dcm').
    output_file_name : str, opcional
        Nombre del archivo DICOM de salida modificado (por defecto 'modified_rt.plan.dcm').
    Excepciones
    -----------
    ValueError
        Si el archivo no es un RT Plan válido, si no se puede identificar el tipo 
        de MLC, o si las posiciones de las láminas no son compatibles con el 
        acelerador de destino.
    Notas
    -----
    - El tipo de MLC se identifica automáticamente y se realiza la conversión 
      correspondiente.
    - Se actualizan los identificadores DICOM para evitar conflictos en sistemas 
      de gestión como ARIA.
    - El archivo modificado se guarda en el directorio de trabajo actual.

plot_mlc_aperture(beam, cp_index, MLC_type=None, ax=None, alpha=1.0)
    Dibuja la apertura del colimador multiláminas (MLC) y las mordazas para un punto de control específico de un haz de radioterapia.

    Parameters
    ----------
    beam : pydicom.dataset.Dataset
        Objeto que representa el haz de radioterapia, debe contener la secuencia ControlPointSequence.
    cp_index : int
        Índice del punto de control dentro de la secuencia ControlPointSequence.
    MLC_type : str, optional
        Tipo de MLC utilizado en el haz. Debe ser 'Millenium' o 'HD'. Determina la geometría y el espaciado de las láminas.
    ax : matplotlib.axes.Axes, optional
        Eje de matplotlib sobre el que se dibuja la apertura. Si no se proporciona, se debe crear externamente.
    alpha : float, optional
        Transparencia de los polígonos que representan las láminas y mordazas. Valor entre 0 y 1.

    Raises
    ------
    ValueError
        Si el tipo de MLC no es reconocido.
    AssertionError
        Si el número de bordes de láminas no corresponde al esperado para el tipo de MLC.

    Notes
    -----
    La función dibuja las posiciones de las láminas de ambos bancos (A y B) y las mordazas X e Y como líneas delimitadoras.
    El eje debe estar preparado para visualizar correctamente la geometría del campo, con límites y aspecto igual.


-------------------------------------------------------------------------------
'''

import pydicom
import numpy as np
import warnings
import os
import json

# Definir las constantes que identifican el tipo de MLC
Leaf0PositionBoundary_Millenium = -200.0
Leaf0PositionBoundary_HD = -110.0

# Variable global para el sistema de traducciones
_i18n = None

def set_i18n(i18n_instance):
    """Establece la instancia del sistema de traducciones"""
    global _i18n
    _i18n = i18n_instance

def get_error_message(error_key, **kwargs):
    """Obtiene un mensaje de error traducido"""
    if _i18n:
        return _i18n.get_text(f"tbch_errors.{error_key}", **kwargs)
    else:
        # Mensajes de fallback en español si no hay sistema de traducciones
        fallback_messages = {
            "invalid_rtplan": "El archivo DICOM no es un archivo de plan de radioterapia (RTPLAN)",
            "mlc_type_not_identified": "El archivo DICOM no permite identificar el tipo de MLC.",
            "field_doesnt_fit_tb3": "El campo no entra en el TrueBeam 3.\nDiscrepancia encontrada: lámina {leaf_index} no coincide con lámina {opposite_leaf} en el punto de control {cp_index} del haz {beam_number}",
            "no_mlc_in_bld_sequence": "No existe MLC en BeamLimitingDevicePositionSequence para el punto de control {cp}",
            "mlc_type_not_recognized": "Tipo de MLC no reconocido. Debe ser 'Millenium' o 'HD'.",
            "invalid_leaf_edges_count": "Debe haber 61 bordes para 60 láminas por banco"
        }
        message = fallback_messages.get(error_key, f"Error: {error_key}")
        try:
            return message.format(**kwargs)
        except (KeyError, ValueError):
            return message


def convert_millennium_to_hd_positions(millennium_positions):
    '''
    Función: convert_millennium_to_hd_positions(millennium_positions)
        Convierte las posiciones de las láminas de un MLC Millennium a las posiciones 
        equivalentes en un MLC HD.
        Parámetros
        ----------
        millennium_positions : list[float] o np.ndarray
            Lista o array de 120 posiciones de láminas correspondientes a un MLC Millennium.
        Retorna
        -------
        list[float]
            Lista de 120 posiciones de láminas adaptadas al formato del MLC HD.
        Notas
        -----
        La conversión se realiza según un mapeo específico de índices y reglas de 
        interpolación para asegurar la correspondencia física entre ambos tipos de MLC.
    '''
    num_leaves = 120
    hd_positions = np.zeros(num_leaves)

   # Definir las conversiones específicas para cada banco
    bank_b_mapping = {
        0: 9, 14: 22, 16: 23, 18: 24, 20: 25,
        22: 26, 24: 27, 26: 28, 28: 29, 30: 30,
        32: 31, 34: 32, 36: 33, 38: 34, 40: 35,
        42: 36, 44: 37, 58: 50
    }

    bank_a_mapping = {
        60: 69, 74: 82, 76: 83, 78: 84, 80: 85,
        82: 86, 84: 87, 86: 88, 88: 89, 90: 90,
        92: 91, 94: 92, 96: 93, 98: 94, 100: 95,
        102: 96, 104: 97, 118: 110
    }

    # Asignar las posiciones mapeadas en los bancos B y A
    for hd_idx, mil_idx in bank_b_mapping.items():
        hd_positions[hd_idx] = millennium_positions[mil_idx]
        hd_positions[hd_idx + 1] = millennium_positions[mil_idx]

    for hd_idx, mil_idx in bank_a_mapping.items():
        hd_positions[hd_idx] = millennium_positions[mil_idx]
        hd_positions[hd_idx + 1] = millennium_positions[mil_idx]

    # Asignar las posiciones restantes para el banco B
    for i in range(2, 14):
        hd_positions[i] = millennium_positions[i + 8]
    for i in range(46, 58):
        hd_positions[i] = millennium_positions[i - 8]

    # Asignar las posiciones restantes para el banco A
    for i in range(62, 74):
        hd_positions[i] = millennium_positions[i + 8]
    for i in range(106, 118):
        hd_positions[i] = millennium_positions[i - 8]

    # Redondeamos a un decimal para que no de un warning al importar
    # En este caso debería no ser necesario
    hd_positions = np.round(hd_positions, 1)

    return hd_positions.tolist()

def convert_hd_to_millennium_positions(hd_positions):
    """
    Función: convert_hd_to_millennium_positions(hd_positions)
        Convierte las posiciones de las láminas de un MLC HD a las posiciones 
        equivalentes en un MLC Millennium, promediando posiciones cuando es necesario.
        Parámetros
        ----------
        hd_positions : list[float] o np.ndarray
            Lista o array de 120 posiciones de láminas correspondientes a un MLC HD.
        Retorna
        -------
        list[float]
            Lista de 120 posiciones de láminas adaptadas al formato del MLC Millennium.
        Notas
        -----
        Se realiza un ajuste para evitar que las láminas enfrentadas queden a menos 
        de 0.5 mm, previniendo advertencias o errores en la importación del plan.
    
    """
    num_leaves = 120
    millennium_positions = np.zeros(num_leaves)

    # Índices específicos para el banco B y A
    specific_indices_b = {9: 0, 22: 14, 23: 16, 24: 18, 25: 20, 26: 22, 27: 24, 28: 26, 29: 28, 30: 30, 31: 32, 32: 34, 33: 36, 34: 38, 35: 40, 36: 42, 37: 44, 50: 58}
    specific_indices_a = {69: 60, 82: 74, 83: 76, 84: 78, 85: 80, 86: 82, 87: 84, 88: 86, 89: 88, 90: 90, 91: 92, 92: 94, 93: 96, 94: 98, 95: 100, 96: 102, 97: 104, 110: 118}

    # Asignación para índices específicos en banco B
    for k, v in specific_indices_b.items():
        millennium_positions[k] = np.mean(hd_positions[v:v + 2])

    # Asignación para índices específicos en banco A
    for k, v in specific_indices_a.items():
        millennium_positions[k] = np.mean(hd_positions[v:v + 2])

    # Asignaciones por rango
    millennium_positions[:9] = hd_positions[0]
    millennium_positions[10:22] = hd_positions[2:14]
    millennium_positions[38:50] = hd_positions[46:58]
    millennium_positions[51:60] = hd_positions[59]
    millennium_positions[60:69] = hd_positions[60]
    millennium_positions[70:82] = hd_positions[62:74]
    millennium_positions[98:110] = hd_positions[106:118]
    millennium_positions[111:120] = hd_positions[119]

    # Verificar y ajustar las posiciones dinámicas enfrentadas para que no estén a menos de 0.5 mm
    # Ponemos 0.55 mm para evitar problemas con el redondeo posterior
    for i in range(60):
        leaf_b = millennium_positions[i]
        leaf_a = millennium_positions[60+ i]
        if leaf_a != leaf_b and abs(leaf_a - leaf_b) < 0.55:
            adjustment = (0.55 - abs(leaf_a - leaf_b)) / 2
            millennium_positions[i] -= adjustment
            millennium_positions[60+ i] += adjustment

    # Redondeamos a un decimal para que no de un warning al importar
    millennium_positions = np.round(millennium_positions, 1)

    return millennium_positions.tolist()

def load_linac_config(config_path=None):
    """
    Carga la configuración de aceleradores desde un archivo JSON.
    El archivo debe tener la estructura:
    {
        "Millenium": {
            "DeviceSerialNumber": "####",
            "TreatmentMachineName": "LinacName1"
        },
        "HD": {
            "DeviceSerialNumber": "####",
            "TreatmentMachineName": "LinacName2"
    }
    """
    if config_path is None:
        # Usar la ruta del archivo actual como base
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(current_dir, "..", "streamlit", "linac_config.json")
        config_path = os.path.normpath(config_path)
    
    if not os.path.exists(config_path):
        # Intentar rutas alternativas
        alternative_paths = [
            os.path.join(os.path.dirname(__file__), "linac_config.json"),
            os.path.join(os.getcwd(), "linac_config.json"),
            os.path.join(os.getcwd(), "src", "streamlit", "linac_config.json")
        ]
        
        for alt_path in alternative_paths:
            if os.path.exists(alt_path):
                config_path = alt_path
                break
        else:
            # Crear configuración por defecto
            default_config = {
                "Millenium": {
                    "DeviceSerialNumber": "5785",
                    "TreatmentMachineName": "TrueBeam2"
                },
                "HD": {
                    "DeviceSerialNumber": "6119",
                    "TreatmentMachineName": "TrueBeam3"
                }
            }
            # Intentar crear el archivo en la primera ruta posible
            for create_path in [config_path] + alternative_paths:
                try:
                    os.makedirs(os.path.dirname(create_path), exist_ok=True)
                    with open(create_path, "w", encoding="utf-8") as f:
                        json.dump(default_config, f, indent=4)
                    config_path = create_path
                    break
                except (OSError, PermissionError):
                    continue
            else:
                # Si no se puede crear, usar configuración por defecto
                return default_config
    
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)
    
def save_linac_config(config, config_path=None):
    """
    Guarda la configuración de aceleradores en un archivo JSON.
    Parámetros
    ----------
    config : dict
        Diccionario con la configuración de aceleradores.
    config_path : str, opcional
        Ruta del archivo donde se guardará la configuración (por defecto 'linac_config.json').
    """
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

def modify_plan(dicom_file_name='RP.T3.dcm', output_file_name='modified_rt.plan.dcm', config_path=None):
    """
    Modifica un archivo DICOM de planificación de radioterapia (RT Plan)
    reasignando las posiciones de las láminas del MLC y adaptando los metadatos
    del plan según el tipo de acelerador, usando parámetros desde un archivo de configuración.
    """
    # Cargar configuración de aceleradores
    config = load_linac_config(config_path)

    working_path = './'
    dicom_file_path = working_path + dicom_file_name
    output_file_path = working_path + output_file_name

    ds = pydicom.dcmread(dicom_file_path)

    if ds.Modality != 'RTPLAN':
        raise ValueError(get_error_message("invalid_rtplan"))

    Leaf0PositionBoundary = float(ds.BeamSequence[0].BeamLimitingDeviceSequence[2].LeafPositionBoundaries[0])

    if Leaf0PositionBoundary == Leaf0PositionBoundary_Millenium:
        accelerator_type = "HD"
        # Cambiar el nombre del plan
        if 'RTPlanLabel' in ds:
            ds.RTPlanLabel = 'AdaptM2HD'

        # Eliminar ReferencedRTPlanSequence si existe
        if hasattr(ds, 'ReferencedRTPlanSequence'):
            del ds.ReferencedRTPlanSequence

        for beam in ds.BeamSequence:
            # Usar parámetros del archivo de configuración
            beam.DeviceSerialNumber = config[accelerator_type]["DeviceSerialNumber"]
            beam.TreatmentMachineName = config[accelerator_type]["TreatmentMachineName"]

            new_boundaries = np.arange(-110., -44.5, 5.).tolist() + np.arange(-40., 38.5, 2.5).tolist() + np.arange(40., 111., 5.).tolist()
            beam.BeamLimitingDeviceSequence[2].LeafPositionBoundaries = new_boundaries

            control_point_sequence = beam.ControlPointSequence
            n_control_points = beam.NumberOfControlPoints
            if n_control_points == 2:
                n_control_points = 1

            for cp in range(n_control_points):
                cp_item = control_point_sequence[cp]
                for attr in ['TableTopLateralPosition', 'TableTopLongitudinalPosition', 'TableTopVerticalPosition']:
                    if hasattr(cp_item, attr):
                        setattr(cp_item, attr, None)

                bld_seq = cp_item.BeamLimitingDevicePositionSequence
                if len(bld_seq) >= 3:
                    mlc_item = bld_seq[2]
                    millennium_positions = mlc_item.LeafJawPositions

                    # Verificar si el campo entra en el MLC del TB3
                    for i in list(range(10)) + list(range(50, 60)):

                        if millennium_positions[i] != millennium_positions[i + 60]:
                            raise ValueError(get_error_message(
                                "field_doesnt_fit_tb3",
                                leaf_index=i,
                                opposite_leaf=i+60,
                                cp_index=cp_item.ControlPointIndex,
                                beam_number=beam.BeamNumber
                            ))

                    # Convertir posiciones de Millennium a HD
                    hd_positions = convert_millennium_to_hd_positions(millennium_positions)

                    # Asignar y guardar en la estructura DICOM
                    mlc_item.LeafJawPositions = hd_positions
                    cp_item.BeamLimitingDevicePositionSequence[2] = mlc_item
                    control_point_sequence[cp] = cp_item

                else:
                    warnings.warn(get_error_message("no_mlc_in_bld_sequence", cp=cp))

            # Guardar la secuencia de control actualizada
            beam.ControlPointSequence = control_point_sequence

    elif Leaf0PositionBoundary == Leaf0PositionBoundary_HD:
        accelerator_type = "Millenium"
       # Cambiar el nombre del plan
        if 'RTPlanLabel' in ds:
            ds.RTPlanLabel = 'AdaptHD2M'

        # Eliminar ReferencedRTPlanSequence si existe
        if hasattr(ds, 'ReferencedRTPlanSequence'):
            del ds.ReferencedRTPlanSequence

        # Navegar en la secuencia de haces (Beam Sequence)
        for beam in ds.BeamSequence:

            # Cambiar el nombre de la máquina y el número de serie
            beam.DeviceSerialNumber = config[accelerator_type]["DeviceSerialNumber"]
            beam.TreatmentMachineName = config[accelerator_type]["TreatmentMachineName"]

            # Nuevos límites de posición de las láminas
            new_boundaries = list(range(-200, -99, 10)) + list(range(-95, 96, 5)) + list(range(100, 201, 10))
            beam.BeamLimitingDeviceSequence[2].LeafPositionBoundaries = new_boundaries

            control_point_sequence = beam.ControlPointSequence
            n_control_points = beam.NumberOfControlPoints

            if n_control_points == 2:  # campo estático
                n_control_points = 1

            for cp in range(n_control_points):
                cp_item = control_point_sequence[cp]

                # Eliminar posiciones de la mesa si existen
                for attr in ['TableTopLateralPosition', 'TableTopLongitudinalPosition', 'TableTopVerticalPosition']:
                    if hasattr(cp_item, attr):
                        setattr(cp_item, attr, None)

                # Verificar existencia del MLC (Item_3)
                bld_seq = cp_item.BeamLimitingDevicePositionSequence
                if len(bld_seq) >= 3:
                    mlc_item = bld_seq[2]
                    hd_positions = mlc_item.LeafJawPositions

                    # Conversión de posiciones
                    millennium_positions = convert_hd_to_millennium_positions(hd_positions)

                    # Actualizar con nuevas posiciones
                    mlc_item.LeafJawPositions = millennium_positions
                    cp_item.BeamLimitingDevicePositionSequence[2] = mlc_item
                    control_point_sequence[cp] = cp_item

                else:
                    warnings.warn(get_error_message("no_mlc_in_bld_sequence", cp=cp))

            # Asignar la secuencia modificada
            beam.ControlPointSequence = control_point_sequence

    else:
        raise ValueError(get_error_message("mlc_type_not_identified"))
        
    # Cambiar estado del plan y limpiar revisión
    ds.ApprovalStatus = 'UNAPPROVED'
    for field in ['ReviewDate', 'ReviewTime', 'ReviewerName']:
        if hasattr(ds, field):
            setattr(ds, field, '')

    
    # Modificar los identificadores del archivo DICOM para que ARIA no lo interprete como un plan ya existente
    ds.SOPInstanceUID = pydicom.uid.generate_uid()
    ds.SeriesInstanceUID = pydicom.uid.generate_uid()
    ds.StudyInstanceUID = pydicom.uid.generate_uid()

    # Guardar el archivo DICOM modificado
    ds.save_as(output_file_path)

def plot_mlc_aperture(beam, cp_index, MLC_type=None, ax=None, alpha=1.0):
    """
    Dibuja la apertura del colimador multiláminas (MLC) y las mordazas para un punto de control específico de un haz de radioterapia.

    Parameters
    ----------
    beam : pydicom.dataset.Dataset
        Objeto que representa el haz de radioterapia, debe contener la secuencia ControlPointSequence.
    cp_index : int
        Índice del punto de control dentro de la secuencia ControlPointSequence.
    MLC_type : str, optional
        Tipo de MLC utilizado en el haz. Debe ser 'Millenium' o 'HD'. Determina la geometría y el espaciado de las láminas.
    ax : matplotlib.axes.Axes, optional
        Eje de matplotlib sobre el que se dibuja la apertura. Si no se proporciona, se debe crear externamente.
    alpha : float, optional
        Transparencia de los polígonos que representan las láminas y mordazas. Valor entre 0 y 1.

    Raises
    ------
    ValueError
        Si el tipo de MLC no es reconocido.
    AssertionError
        Si el número de bordes de láminas no corresponde al esperado para el tipo de MLC.

    Notes
    -----
    La función dibuja las posiciones de las láminas de ambos bancos (A y B) y las mordazas X e Y como líneas delimitadoras.
    El eje debe estar preparado para visualizar correctamente la geometría del campo, con límites y aspecto igual.
    """
    cps = beam.ControlPointSequence

    # Inicializamos variables
    x_jaws = y_jaws = None
    leaf_positions = None
    # Extraer posiciones del MLC (MLCX) en el punto de control
    for device in cps[cp_index].BeamLimitingDevicePositionSequence:
        if device.RTBeamLimitingDeviceType == "MLCX":
            leaf_positions = device.LeafJawPositions
        elif device.RTBeamLimitingDeviceType == "ASYMX":
            x_jaws = device.LeafJawPositions
        elif device.RTBeamLimitingDeviceType == "ASYMY":
            y_jaws = device.LeafJawPositions

    if leaf_positions is not None:
        n_leaves = len(leaf_positions) // 2
        x1 = np.array(leaf_positions[:n_leaves])  # Banco A
        x2 = np.array(leaf_positions[n_leaves:])  # Banco B

        # Coordenadas reales de los bordes de las láminas (y-direction)
        if MLC_type == "Millenium":
            leaf_edges = list(range(-200, -99, 10)) + list(range(-95, 96, 5)) + list(range(100, 201, 10))
            leaf_colors = ['skyblue', 'lightgreen']
        elif MLC_type == "HD":
            leaf_edges = np.arange(-110., -44.5, 5.).tolist() + np.arange(-40., 38.5, 2.5).tolist() + np.arange(40., 111., 5.).tolist()
            leaf_colors = ['salmon', 'khaki']    
        else:
            raise ValueError(get_error_message("mlc_type_not_recognized"))
        assert len(leaf_edges) == 61, get_error_message("invalid_leaf_edges_count")
        y_bottoms = np.array(leaf_edges[:-1])
        y_tops = np.array(leaf_edges[1:])

        # Largo físico de las láminas (en X): 185 mm
        leaf_length = 185

        for i in range(n_leaves):
            # Banco A (superior en la visualización)
            ax.fill(
                [x1[i], x1[i] - leaf_length, x1[i] - leaf_length, x1[i]],
                [y_bottoms[i], y_bottoms[i], y_tops[i], y_tops[i]],
                color=leaf_colors[0] if i % 2 == 0 else leaf_colors[1],
                edgecolor='black',
                linewidth=0.5,
                alpha=alpha
            )

            # Banco B (inferior en la visualización)
            ax.fill(
                [x2[i] + leaf_length, x2[i], x2[i], x2[i] + leaf_length],
                [y_bottoms[i], y_bottoms[i], y_tops[i], y_tops[i]],
                color=leaf_colors[0] if i % 2 == 0 else leaf_colors[1],
                edgecolor='black',
                linewidth=0.5,
                alpha=alpha * 0.5
            )

        # Dibujar mordazas X como línea vertical delimitadora
        if x_jaws is not None:
            ax.axvline(x_jaws[0], color='red', linestyle='--', alpha=alpha, label='Jaw X')
            ax.axvline(x_jaws[1], color='red', linestyle='--', alpha=alpha)

        # Dibujar mordazas Y como línea horizontal delimitadora
        if y_jaws is not None:
            ax.axhline(y_jaws[0], color='red', linestyle='--', alpha=alpha, label='Jaw Y')
            ax.axhline(y_jaws[1], color='red', linestyle='--', alpha=alpha)

        ax.axvline(0, color='gray', linestyle='--')
        ax.set_title(f"Apertura MLC – Campo {beam.BeamNumber}, CP {cp_index+1}")
        ax.set_xlabel("Posición X (mm)")
        ax.set_ylabel("Posición Y (mm)")
        ax.set_xlim(-250, 250)
        ax.set_ylim(-210, 210)
        ax.set_aspect('equal')
        ax.grid(True)

def plot_mlc_aperture_closed(ax, MLC_type=None, alpha=1.0):
    """
    Dibuja el MLC completamente cerrado para mostrar cuando la transformación no es posible.
    
    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Eje de matplotlib sobre el que se dibuja la apertura.
    MLC_type : str
        Tipo de MLC. Debe ser 'Millenium' o 'HD'.
    alpha : float, optional
        Transparencia de los polígonos que representan las láminas.
    """
    if MLC_type == "Millenium":
        leaf_edges = list(range(-200, -99, 10)) + list(range(-95, 96, 5)) + list(range(100, 201, 10))
        leaf_colors = ['lightcoral', 'lightpink']  # Colores más suaves para indicar que está cerrado
    elif MLC_type == "HD":
        leaf_edges = np.arange(-110., -44.5, 5.).tolist() + np.arange(-40., 38.5, 2.5).tolist() + np.arange(40., 111., 5.).tolist()
        leaf_colors = ['lightcoral', 'lightpink']  # Colores más suaves para indicar que está cerrado
    else:
        raise ValueError(get_error_message("mlc_type_not_recognized"))
    
    assert len(leaf_edges) == 61, get_error_message("invalid_leaf_edges_count")
    y_bottoms = np.array(leaf_edges[:-1])
    y_tops = np.array(leaf_edges[1:])
    n_leaves = len(y_bottoms)
    
    # Largo físico de las láminas (en X): 185 mm
    leaf_length = 185
    
    # Posiciones cerradas: todas las láminas en posición 0
    closed_position = 0.0
    
    for i in range(n_leaves):
        # Banco A (todas las láminas en posición cerrada)
        ax.fill(
            [closed_position, closed_position - leaf_length, closed_position - leaf_length, closed_position],
            [y_bottoms[i], y_bottoms[i], y_tops[i], y_tops[i]],
            color=leaf_colors[0] if i % 2 == 0 else leaf_colors[1],
            edgecolor='red',
            linewidth=1.0,
            alpha=alpha,
            linestyle='--'
        )
        
        # Banco B (todas las láminas en posición cerrada)
        ax.fill(
            [closed_position + leaf_length, closed_position, closed_position, closed_position + leaf_length],
            [y_bottoms[i], y_bottoms[i], y_tops[i], y_tops[i]],
            color=leaf_colors[0] if i % 2 == 0 else leaf_colors[1],
            edgecolor='red',
            linewidth=1.0,
            alpha=alpha * 0.5,
            linestyle='--'
        )
    
    # Línea central de referencia
    ax.axvline(0, color='gray', linestyle='--')

