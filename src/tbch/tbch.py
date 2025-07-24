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

-------------------------------------------------------------------------------
'''

import pydicom
import numpy as np
import warnings

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

def modify_plan(dicom_file_name='RP.T3.dcm', output_file_name='modified_rt.plan.dcm'):
    """
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

    """
    
    # Definir las constantes que identifican el tipo de MLC
    Leaf0PositionBundary_Millenium = -200.0
    Leaf0PositionBundary_HD = -110.0
    
    # Archivos de entrada y de salida
    working_path ='./'
    dicom_file_path = working_path + dicom_file_name
    output_file_path = working_path + output_file_name
    
    # Leer el archivo DICOM
    ds = pydicom.dcmread(dicom_file_path)

    # Asegurarse de que el archivo es de tipo RT Plan
    if ds.Modality != 'RTPLAN':
        raise ValueError("El archivo DICOM no es un archivo de plan de radioterapia (RTPLAN)")
    
    # Identificar el tipo de MLC mediante el valor del PositionBoundary de la primera lámina del MLC (BeamLimitingDevice[2]) del primer campo
    Leaf0PositionBundary = float(ds.BeamSequence[0].BeamLimitingDeviceSequence[2].LeafPositionBoundaries[0])

    if Leaf0PositionBundary == Leaf0PositionBundary_Millenium:
        # Cambiar el nombre del plan
        if 'RTPlanLabel' in ds: 
            ds.RTPlanLabel = 'AdaptT3p'


        # Eliminar ReferencedRTPlanSequence si existe
        if hasattr(ds, 'ReferencedRTPlanSequence'):
            del ds.ReferencedRTPlanSequence
        # Navegar en la secuencia de haces (Beam Sequence)
        for beam in ds.BeamSequence:

            # Cambiar el nombre de la máquina y el número de serie
            beam.DeviceSerialNumber = '6119'
            beam.TreatmentMachineName = 'TrueBeam3'

            # Encontrar la secuencia del dispositivo de limitación de haz y modificar las "Leaf Position Boundaries"
            # Nuevos límites de posición de las láminas (TB3)
            new_boundaries = new_boundaries = np.arange(-110., -44.5, 5.).tolist() + np.arange(-40., 38.5, 2.5).tolist() + np.arange(40., 111., 5.).tolist()
            beam.BeamLimitingDeviceSequence[2].LeafPositionBoundaries = new_boundaries
            print(f"BeamLimitingDeviceSequence[2].LeafPositionBoundaries: {beam.BeamLimitingDeviceSequence[2].LeafPositionBoundaries}")

            control_point_sequence = beam.ControlPointSequence
            n_control_points = beam.NumberOfControlPoints

            if n_control_points == 2:
                n_control_points = 1  # campo estático

            for cp in range(n_control_points):
                cp_item = control_point_sequence[cp]

                # Eliminar posiciones de la mesa si existen
                for attr in ['TableTopLateralPosition', 'TableTopLongitudinalPosition', 'TableTopVerticalPosition']:
                    if hasattr(cp_item, attr):
                        setattr(cp_item, attr, None)

                bld_seq = cp_item.BeamLimitingDevicePositionSequence
                if len(bld_seq) >= 3:
                    mlc_item = bld_seq[2]
                    millennium_positions = mlc_item.LeafJawPositions

                    # Verificar si el campo entra en el MLC del TB3
                    for i in list(range(10)) + list(range(50, 60)):

                        mlc_tb3_error_message = (
                            f"El campo no entra en el TrueBeam 3.\n"
                            f"Discrepancia encontrada: lámina {i} no coincide con lámina {i+60} "
                            f"en el punto de control {cp_item.ControlPointIndex} del haz {beam.BeamNumber}"
                        )

                        if millennium_positions[i] != millennium_positions[i + 60]:
                            raise ValueError(mlc_tb3_error_message)

                    # Convertir posiciones de Millennium a HD
                    hd_positions = convert_millennium_to_hd_positions(millennium_positions)

                    # Asignar y guardar en la estructura DICOM
                    mlc_item.LeafJawPositions = hd_positions
                    cp_item.BeamLimitingDevicePositionSequence[2] = mlc_item
                    control_point_sequence[cp] = cp_item

                else:
                    warnings.warn(f"No existe MLC en BeamLimitingDevicePositionSequence para el punto de control {cp}")

            # Guardar la secuencia de control actualizada
            beam.ControlPointSequence = control_point_sequence

    elif Leaf0PositionBundary == Leaf0PositionBundary_HD:
        # Cambiar el nombre del plan
        if 'RTPlanLabel' in ds:
            ds.RTPlanLabel = 'AdaptT2p'

        # Navegar en la secuencia de haces (Beam Sequence)
        for beam in ds.BeamSequence:

            # Cambiar el nombre de la máquina y el número de serie
            beam.DeviceSerialNumber = '5785'
            beam.TreatmentMachineName = 'TrueBeam2'

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
                    warnings.warn(f'No existe MLC en BeamLimitingDevicePositionSequence para el punto de control {cp}')

            # Asignar la secuencia modificada
            beam.ControlPointSequence = control_point_sequence

    else:
        raise ValueError("El archivo DICOM no permite identificar el tipo de MLC.")
        
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

