"""
Módulo de internacionalización para la aplicación de transformación de planes MLC
"""
import json
import os
import streamlit as st


class I18n:
    def __init__(self, translations_file="translations.json", default_language="es"):
        self.default_language = default_language
        self.current_language = default_language
        self.translations = {}
        self.load_translations(translations_file)
    
    def load_translations(self, translations_file):
        """Carga las traducciones desde el archivo JSON"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            translations_path = os.path.join(current_dir, translations_file)
            
            with open(translations_path, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
        except FileNotFoundError:
            # Solo mostrar error si estamos en contexto de Streamlit
            print(f"Warning: Translation file not found: {translations_file}")
            self.translations = {}
        except json.JSONDecodeError:
            # Solo mostrar error si estamos en contexto de Streamlit
            print(f"Warning: Invalid JSON in translation file: {translations_file}")
            self.translations = {}
    
    def set_language(self, language):
        """Establece el idioma actual"""
        if language in ["es", "en"]:
            self.current_language = language
        else:
            self.current_language = self.default_language
    
    def get_text(self, key_path, **kwargs):
        """
        Obtiene el texto traducido para la clave dada
        
        Args:
            key_path (str): Ruta de la clave separada por puntos (ej: "main_interface.app_title")
            **kwargs: Variables para formatear el texto
            
        Returns:
            str: Texto traducido
        """
        keys = key_path.split('.')
        current = self.translations
        
        # Navegar por la estructura anidada
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return f"[MISSING: {key_path}]"
        
        # Obtener el texto en el idioma actual
        if isinstance(current, dict):
            text = current.get(self.current_language, current.get(self.default_language, f"[MISSING: {key_path}]"))
        else:
            text = current
        
        # Formatear el texto con las variables proporcionadas
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    
    def t(self, key_path, **kwargs):
        """Alias corto para get_text"""
        return self.get_text(key_path, **kwargs)


# Instancia global del sistema de traducciones
i18n = I18n()


def get_language_selector():
    """
    Crea un selector de idioma en la barra lateral de Streamlit
    
    Returns:
        str: Código del idioma seleccionado
    """
    # Inicializar el idioma en session_state si no existe
    if 'language' not in st.session_state:
        st.session_state.language = i18n.default_language
    
    language_options = {
        "🇪🇸 Español": "es",
        "🇺🇸 English": "en"
    }
    
    # Obtener el índice actual basado en el idioma en session_state
    current_index = 0 if st.session_state.language == "es" else 1
    
    selected_display = st.sidebar.selectbox(
        "Language / Idioma",
        options=list(language_options.keys()),
        index=current_index,
        key="language_selector"
    )
    
    selected_language = language_options[selected_display]
    
    # Solo actualizar si el idioma cambió
    if selected_language != st.session_state.language:
        st.session_state.language = selected_language
        i18n.set_language(selected_language)
        # Forzar rerun para actualizar toda la interfaz
        st.rerun()
    else:
        # Asegurar que el idioma esté configurado correctamente
        i18n.set_language(selected_language)
    
    return selected_language


def format_error_message(error_key, **kwargs):
    """
    Formatea un mensaje de error con las variables proporcionadas
    
    Args:
        error_key (str): Clave del error en el archivo de traducciones
        **kwargs: Variables para formatear el mensaje
        
    Returns:
        str: Mensaje de error formateado
    """
    return i18n.get_text(f"tbch_errors.{error_key}", **kwargs)
